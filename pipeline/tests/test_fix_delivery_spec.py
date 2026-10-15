"""Spec gaps in the delivered shape (Arena spec 2026-09-21).

E4 tool schema, E5/P1 allowlisted and privacy-checked delivery, D4/C5 runs and
the reward-hacking note, B1 Reviewable, B4 unlevelled, B5 trace accounting, B6
multi-turn, M4 task-level faithfulness tag, T4 tasks per environment, A3
general difficulty, T6 synthetic labelling. Each test fails on the behaviour it
replaces. No model calls, no Docker.
"""
from __future__ import annotations

import hashlib
import json
import tempfile
import tomllib
import unittest
from pathlib import Path
from pipeline.tests.test_capability_construction import alignment_witnesses
from unittest import mock

POLICY = "0" * 64
PRIMARY, SECONDARY = "anthropic/claude-fable-5-1", "openai/gpt-6-astra"

TASK_TOML = '''schema_version = "1.4"

[task]
name = "arena/{name}"
description = "d"

[metadata]
category = "c"
source_trace = "s1"
source_seeds = ["s1::0"]
difficulty_explanation = """
multi
line
"""

[agent]
network_mode = "no-network"

[verifier]
environment_mode = "separate"

[[steps]]
name = "01-task"

[[steps]]
name = "02-revision"
'''


def _write(path: Path, text: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)
    return path


def _bundle(root: Path, name: str = "a-001-editorial-review", *, checks=None) -> Path:
    b = root / "work" / "rich" / name
    _write(b / "task.toml", TASK_TOML.format(name=name))
    _write(b / "tests/checks.json", json.dumps({"checks": checks or [
        {"id": "o1", "kind": "objective", "weight": 1, "step": "01-task"},
        {"id": "o2", "kind": "objective", "weight": 1, "step": "02-revision"}]}))
    _write(b / "environment/files/brief.md", "a plain brief\n")
    _write(b / "provenance/ledger.json", json.dumps(
        {"faithfulness_by_bytes": 0.95, "entries": [],
         "trace_alignment": alignment_witnesses()}, indent=1) + "\n")
    authored = [{"id": f"a{i}", "provenance": "authored", "checks": ["o2"]} for i in range(4)]
    for n in ("traps.json", "spec.json"):
        _write(b / "authoring" / n, json.dumps({"traps": authored}))
    return b


def _accept(bundle: Path) -> None:
    from pipeline.artifacts import identity
    _write(bundle / "verification/release.json", json.dumps(
        {"schema": "arena-pipeline/release/1", "status": "accepted", "errors": [],
         "artifact_sha256": identity(bundle), "policy_sha256": POLICY, "evidence": {}}))


class _Tmp(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        patcher = mock.patch("pipeline.artifacts.policy_identity", return_value=POLICY)
        patcher.start()
        self.addCleanup(patcher.stop)


# --------------------------------------------------------------------- E4 --

class ToolSchema(_Tmp):
    """Spec E4: tools and actions defined with machine-readable schemas."""

    def _gate(self, bundle):
        from pipeline.gates.base import GateContext
        from pipeline.gates.bundle import structure_gate
        result = structure_gate.run(GateContext(task_dir=bundle, repo_root=self.root))
        return [f for f in result.findings if f.code == "tool-schema"]

    def _package(self):
        b = _bundle(self.root)
        for rel in ("tests/criteria.py", "tests/reward.toml", "tests/basis.toml"):
            _write(b / rel, "")
        _write(b / "tests/rubric.json", json.dumps({"01-task": {}, "02-revision": {}}))
        return b

    def test_write_native_emits_a_valid_schema_referenced_from_task_toml(self):
        from pipeline.author import native_package
        b = self._package()
        native_package.write_native({"steps": [], "outputs": [
            {"step": "01-task", "file": "audit.json"}]}, b)
        doc = json.loads((b / "environment/tools.json").read_text())
        self.assertEqual(native_package.tool_schema_problems(b), [])
        self.assertEqual(tomllib.loads((b / "task.toml").read_text())["metadata"]["tool_schema"],
                         "environment/tools.json")
        # User, 2026-09-26: Fable 5.1 in Claude Code, GPT 6 Astra in Codex, each
        # at its pinned version and high effort, the agent phase limited to its
        # own model API host.
        harnesses = {t["model"]: t for t in doc["tools"]}
        self.assertEqual({m: (t["agent"], t["version"], t["reasoning_effort"]) for m, t in harnesses.items()},
                         {"claude-fable-5-1": ("claude-code", "2.1.283", "high"),
                          "gpt-6-astra": ("codex", "0.157.1", "high")})
        self.assertEqual(harnesses["claude-fable-5-1"]["agent_phase_network"],
                         {"mode": "allowlist", "hosts": ["api.anthropic.com"]})
        self.assertEqual(harnesses["gpt-6-astra"]["agent_phase_network"],
                         {"mode": "allowlist", "hosts": ["api.openai.com"]})
        # The agent image bakes in the pinned Node and both CLIs.
        self.assertEqual(native_package.harness_dockerfile_problems(b), [])
        dockerfile = (b / "environment/Dockerfile").read_text()
        self.assertIn("@anthropic-ai/claude-code@2.1.283 @openai/codex@0.157.1", dockerfile)
        self.assertIn(native_package.NODE_IMAGE, dockerfile)
        self.assertEqual(doc["workspace"]["read_only"], ["/app/environment/files"])
        self.assertEqual(doc["workspace"]["writable"], ["/app/deliverables"])
        self.assertEqual(doc["workspace"]["outputs"],
                         [{"step": "01-task", "path": "/app/deliverables/audit.json"}])
        # The build context still admits only the Dockerfile and the fixture.
        self.assertEqual((b / "environment/.dockerignore").read_text(),
                         "*\n!Dockerfile\n!files/\n!files/**\n")
        self.assertEqual(self._gate(b), [])

    def test_structure_refuses_a_package_without_or_with_a_wrong_schema(self):
        from pipeline.author import native_package
        b = self._package()
        self.assertTrue(self._gate(b), "a package with no tools.json passed structure")
        native_package.write_native({"steps": []}, b)
        doc = json.loads((b / "environment/tools.json").read_text())
        doc["workspace"]["writable"].append("/app/environment/files")
        _write(b / "environment/tools.json", json.dumps(doc))
        self.assertTrue(self._gate(b))


# --------------------------------------------------------------- E5 / P1 --

class AllowlistedDelivery(_Tmp):
    """Spec E5/P1: leftover files removed; no personal data shipped."""

    def _deliver(self, bundle):
        from pipeline import deliver
        return deliver.deliver(self.root / "work", self.root / "out")

    def test_only_the_package_and_reviewer_receipts_are_delivered(self):
        b = _bundle(self.root)
        scratch = ["authoring/agent-probe/answer.json", "authoring/solution-check/x.json",
                   "authoring/empty-check/y.json", "authoring/extraction/doc.md",
                   "verification/orchestrator-error.txt", "verification/probe-work/p.json",
                   "verification/campaigns/c1/transcript.json", "verification/state.json",
                   "verification/qualification-revisions/r1/task/task.toml",
                   "runs/stale/index.json", "REWARD-HACKING.md", "notes.txt"]
        for rel in scratch:
            _write(b / rel, "scratch\n")
        kept = ["verification/probes.json", "verification/controls.json",
                "verification/native-controls.json", "verification/harbor-tasks-check.json",
                "verification/repair-disposition.json",
                "verification/qualification-revisions/r1/feedback.json"]
        for rel in kept:
            _write(b / rel, "{}\n")
        _accept(b)
        record = self._deliver(b)
        out = self.root / "out/F2-scenario/a_f2_editorial-review"
        self.assertEqual(len(record["delivered"]), 1, record["held"])
        shipped = {p.relative_to(out).as_posix() for p in out.rglob("*") if p.is_file()}
        self.assertFalse(shipped & set(scratch), shipped & set(scratch))
        self.assertTrue(set(kept) <= shipped)
        self.assertIn("verification/release.json", shipped)
        self.assertIn("environment/files/brief.md", shipped)

    def test_the_tasks_check_receipt_name_is_harbors(self):
        from pipeline import deliver
        from pipeline.benchmark import tasks_check
        self.assertIn(tasks_check.RECEIPT, deliver.RECEIPTS)

    def test_personal_data_anywhere_refuses_the_task_without_quoting_it(self):
        from pipeline import deliver
        b = _bundle(self.root)
        # Outside the fixture, where release's own scan never looks.
        _write(b / "solution/submission/notes.md", "connect: ssh root@8.8.8.8 -p 2222\n")
        _accept(b)
        record = self._deliver(b)
        self.assertEqual(record["delivered"], [])
        self.assertFalse((self.root / "out/F2-scenario/a_f2_editorial-review").exists())
        held = record["held"][0]
        self.assertIn("solution/submission/notes.md (ssh-access-metadata)", held["held_because"])
        self.assertNotIn("8.8.8.8", json.dumps(record))
        self.assertEqual(deliver.main([str(self.root / "work"), "-o", str(self.root / "out2")]), 1)

    def test_deliverable_reports_privacy_as_a_batch_blocker(self):
        from pipeline import deliverable
        b = _bundle(self.root)
        _write(b / "runs/model/jobs/run/t1/agent.txt", "ssh admin@8.8.4.4\n")
        findings = deliverable.open_privacy(b)
        self.assertEqual(findings, [{"file": "runs/model/jobs/run/t1/agent.txt",
                                     "kind": "ssh-access-metadata"}])
        verdict = deliverable.batch_acceptance(
            [{"bundle": "x", "short_name": "a_f2_x", "privacy_unresolved": findings}],
            {"ok": True})
        self.assertFalse(verdict["ok"])
        self.assertTrue(any(p.startswith("privacy: a_f2_x") for p in verdict["problems"]))


# --------------------------------------------------------------- D4 / C5 --

def _campaign(root: Path, trials: list[str]) -> Path:
    camp = root / "campaigns" / "calibration-1"
    for t in trials:
        _write(camp / "jobs/run" / t / "result.json", "{}")
        _write(camp / "jobs/run" / t / "agent/trajectory.json", "[]")
    return camp


def _measured(camp: Path, rewards: dict[str, float], model: str = PRIMARY) -> dict:
    trials = [{"id": t, "valid": True, "reward": r,
               "result_file": str(camp / "jobs/run" / t / "result.json")}
              for t, r in rewards.items()]
    return {"model": model, "step_names": ["01-task"], "trials": trials, "by_step": {},
            "rollouts": [{"episode": n, "step": "01-task", "reward": r, "id": f"{t}/01-task",
                          "zero_class": None, "stop_reason": "completed"}
                         for n, (t, r) in enumerate(rewards.items(), 1)]}


class RunsAndResults(_Tmp):
    """Spec D4: >=1 successful trajectory; C5: tested, found AND fixed."""

    def setUp(self):
        super().setUp()
        from pipeline.artifacts import identity
        self.bundle = _bundle(self.root)
        self.camp = _campaign(self.root, ["trial-zzz", "trial-abc"])
        _write(self.bundle / "verification/native-calibrations.json", json.dumps(
            {"artifact_sha256": identity(self.bundle), "campaigns": [str(self.camp)]}))

    def _export(self, rewards, hacks=None):
        from pipeline import attribution, deliverable
        measured = _measured(self.camp, rewards)
        scan = (mock.patch.object(attribution, "trajectory_hacks", None) if hacks is None
                else mock.patch.object(attribution, "trajectory_hacks", return_value=hacks))
        with mock.patch("pipeline.release.calibration_measurement",
                        return_value=([], measured)), scan:
            return deliverable.export_runs(self.bundle, self.bundle / "runs")

    def test_a_successful_trajectory_is_named_by_its_real_trial_id(self):
        runs = self._export({"trial-zzz": 0.0, "trial-abc": 1.0}, hacks=[])
        best = runs["successful_trajectory"]
        self.assertEqual(best["trial_id"], "trial-abc")
        self.assertEqual(best["path"], "anthropic-claude-fable-5-1/jobs/run/trial-abc")
        self.assertTrue((self.bundle / "runs" / best["path"]).is_dir())
        self.assertEqual(runs["campaigns"][0]["trials"], {"1": "trial-zzz", "2": "trial-abc"})
        self.assertIsNone(runs["reference_trajectory"])

    def test_with_no_passing_episode_the_oracle_reference_is_exported(self):
        from pipeline.artifacts import identity
        oracle = self.root / "native/oracle"
        _write(oracle / "jobs/run/oracle-trial-1/result.json", "{}")
        _write(oracle / "package/task.toml", "not shipped")
        _write(self.bundle / "verification/native-controls.json", json.dumps(
            {"artifact_sha256": identity(self.bundle), "oracle": str(oracle), "nop": "n"}))
        controls = {"trials": [{"id": "oracle-trial-1", "valid": True, "reward": 1.0,
                                "result_file": str(oracle / "jobs/run/oracle-trial-1/result.json")}]}
        with mock.patch("pipeline.evidence.native_evidence", return_value=([], controls)):
            runs = self._export({"trial-zzz": 0.0, "trial-abc": 0.5}, hacks=[])
        self.assertIsNone(runs["successful_trajectory"])
        ref = runs["reference_trajectory"]
        self.assertEqual((ref["trial_id"], ref["path"]),
                         ("oracle-trial-1", "reference/jobs/run/oracle-trial-1"))
        self.assertTrue((self.bundle / "runs/reference/jobs/run/oracle-trial-1").is_dir())
        self.assertFalse((self.bundle / "runs/reference/package").exists())
        self.assertIn("runs/reference/", runs["note"])

    def test_trajectory_findings_and_repairs_reach_the_note(self):
        from pipeline import deliverable
        hit = {"trial": "trial-abc", "step": "01-task", "kind": "test_access",
               "evidence": "turn 3: cat /tests/checks.json"}
        runs = self._export({"trial-zzz": 0.0, "trial-abc": 1.0}, hacks=[hit])
        self.assertEqual(runs["trajectory_scan"]["status"], "inspected")
        _write(self.bundle / "verification/qualification-revisions/r1/feedback.json",
               json.dumps({"findings": ["primary passed 9/10: too easy"]}))
        _write(self.bundle / "verification/repair-disposition.json",
               json.dumps({"reason": "finding repeated", "outstanding_findings": ["o2 leaks"]}))
        note = deliverable.reward_hacking_note(
            {"bundle": "b", "probes": {}}, deliverable.repair_history(self.bundle),
            runs["trajectory_scan"])
        self.assertIn("trial-abc", note)
        self.assertIn("test_access", note)
        self.assertIn("rebuilt from 1 finding(s): primary passed 9/10: too easy", note)
        self.assertIn("Repair stopped: finding repeated", note)

    def test_exported_copies_carry_no_email_and_the_campaign_is_untouched(self):
        # envs-final-2, 2026-09-27: every harness transcript carried an address
        # from the harness's own system prompt, and the batch privacy scan
        # refused all eight exported run folders.
        line = '{"text": "mail jane.doe@mail.co.uk or test@example.com"}\n'
        _write(self.camp / "jobs/run/trial-abc/agent/session.jsonl", line)
        runs = self._export({"trial-zzz": 0.0, "trial-abc": 1.0}, hacks=[])
        self.assertEqual(runs["redacted"], {"files": 1, "email": 1})
        copy = (self.bundle / "runs/anthropic-claude-fable-5-1/jobs/run/trial-abc/agent/"
                "session.jsonl").read_text()
        self.assertEqual(copy, '{"text": "mail [REDACTED_EMAIL] or test@example.com"}\n')
        json.loads(copy)
        self.assertEqual((self.camp / "jobs/run/trial-abc/agent/session.jsonl").read_text(), line)

    def test_an_absent_scan_says_trajectories_were_not_inspected(self):
        from pipeline import deliverable
        runs = self._export({"trial-abc": 1.0})
        self.assertEqual(runs["trajectory_scan"]["status"], "not inspected")
        note = deliverable.reward_hacking_note({"bundle": "b"}, None, runs["trajectory_scan"])
        self.assertIn("Trajectories not inspected", note)
        self.assertIn("Trajectories not inspected", deliverable.reward_hacking_note({"bundle": "b"}))


# --------------------------------------------------------------------- B1 --

def _task(**over) -> dict:
    task = {"bundle": "b", "short_name": "a_f2_x", "task_name": "arena/a_f2_x",
            "session_id": "s1", "faithfulness_level": "F2", "accepted": True,
            "multi_turn": True, "harbor_tasks_check": "pass", "provenance_included": True,
            "runs": {"exported": True}, "reward_hacking_findings": [],
            "per_model": {PRIMARY: {"model": PRIMARY, "pass_at_1": 0.1},
                          SECONDARY: {"model": SECONDARY, "pass_at_1": 0.2}},
            "hardness": {"hard": True, "meets_spec_general_difficulty": True}}
    task.update(over)
    return task


class Reviewable(unittest.TestCase):
    """Spec B1: tasks-check pass, calibration runs + provenance included."""

    def _reviewable(self, task):
        from pipeline import deliverable
        verdict = deliverable.batch_acceptance([task], {"ok": True})
        return next(c for c in verdict["criteria"] if c["criterion"] == "Reviewable")["ok"]

    def test_everything_present_is_reviewable(self):
        self.assertTrue(self._reviewable(_task()))

    def test_one_calibration_model_is_not_enough(self):
        self.assertFalse(self._reviewable(_task(per_model={PRIMARY: {"model": PRIMARY}})))

    def test_runs_must_actually_be_exported(self):
        self.assertFalse(self._reviewable(_task(runs={"exported": False})))
        self.assertFalse(self._reviewable(_task(runs=None)))

    def test_the_provenance_ledger_must_be_present(self):
        self.assertFalse(self._reviewable(_task(provenance_included=False)))

    def test_runs_are_exported_before_the_batch_is_judged(self):
        from pipeline import deliverable
        root = Path(tempfile.mkdtemp())
        _bundle(root)
        seen = []
        real = deliverable.batch_acceptance

        def spy(tasks, accounting):
            seen.extend(t.get("runs") for t in tasks)
            return real(tasks, accounting)
        with mock.patch.object(deliverable, "batch_acceptance", spy):
            deliverable.build(root / "work", ["s1"], index=None)
        self.assertTrue(seen and all(isinstance(r, dict) and "exported" in r for r in seen), seen)


# ---------------------------------------------------------------- B4 / B5 --

class UnlevelledAndAccounting(unittest.TestCase):

    def test_a_level_outside_f0_f3_is_unlevelled(self):
        from pipeline import deliverable
        from pipeline.ledger import levels
        mix = levels.batch_mix([{"level": "F2"}, {"level": "F9"}])
        self.assertEqual(mix["counts"]["unlevelled"], 1)
        self.assertFalse(mix["ok"])
        verdict = deliverable.batch_acceptance([_task(faithfulness_level="F5")], {"ok": True})
        row = next(c for c in verdict["criteria"] if c["criterion"] == "Faithfulness mix")
        self.assertFalse(row["ok"])

    def test_the_mix_table_has_an_unlevelled_row(self):
        from pipeline import deliverable
        report = {"generated_at": "now", "environments": 1,
                  "acceptance": {"criteria": [], "problems": [], "ok": False},
                  "yield": {}, "faithfulness": {"counts": {"unlevelled": 2}},
                  "trace_accounting": {"sessions_shared": 1, "converted": 0,
                                       "excluded": 0, "undispositioned": 1},
                  "tasks": []}
        self.assertIn("| unlevelled | missing or not F0-F3 | 2 |",
                      deliverable.render_markdown(report))

    def test_an_empty_shared_list_is_a_problem(self):
        from pipeline import deliverable
        self.assertFalse(deliverable.trace_accounting([], {}, {})["ok"])

    def test_a_converted_session_missing_from_the_shared_list_is_a_problem(self):
        from pipeline import deliverable
        record = deliverable.trace_accounting(["s1"], {"s1": ["a"], "s9": ["b"]}, {})
        self.assertFalse(record["ok"])
        self.assertTrue(any("s9" in p for p in record["problems"]))

    def test_a_missing_index_is_a_problem_not_a_pass(self):
        from pipeline import deliverable
        root = Path(tempfile.mkdtemp())
        _bundle(root)
        report = deliverable.build(root / "work", ["s1"], index=None)
        self.assertFalse(report["trace_accounting"]["ok"])
        self.assertTrue(any("dump index" in p for p in report["trace_accounting"]["problems"]))


# --------------------------------------------------------------------- B6 --

class MultiTurn(_Tmp):
    """Spec B6 + "give each turn its own rubric"."""

    def test_two_steps_each_with_an_objective_is_multi_turn(self):
        from pipeline import deliverable
        self.assertTrue(deliverable.task_record(_bundle(self.root))["multi_turn"])

    def test_a_step_with_no_objective_is_not_a_turn(self):
        from pipeline import deliverable
        b = _bundle(self.root, checks=[
            {"id": "o1", "kind": "objective", "weight": 1, "step": "01-task"},
            {"id": "g1", "kind": "guardrail", "weight": 0, "step": "02-revision"}])
        record = deliverable.task_record(b)
        self.assertFalse(record["multi_turn"])
        self.assertEqual(record["objectives_by_step"], {"01-task": 1, "02-revision": 0})


# --------------------------------------------------------------------- M4 --

class TaskLevelTag(_Tmp):
    """Spec M4: the faithfulness tag per environment AND per task."""

    def test_delivery_stamps_the_level_and_stays_accepted(self):
        from pipeline import deliver, deliverable
        b = _bundle(self.root)
        _accept(b)
        deliver.deliver(self.root / "work", self.root / "out")
        out = self.root / "out/F2-scenario/a_f2_editorial-review"
        meta = tomllib.loads((out / "task.toml").read_text())["metadata"]
        self.assertEqual(meta["faithfulness_level"], "F2")
        self.assertEqual(meta["difficulty_explanation"], "multi\nline\n")
        self.assertEqual(deliverable.acceptance_problems(out), [])
        text = (out / "task.toml").read_text()
        (out / "task.toml").write_text(text.replace('faithfulness_level = "F2"',
                                                    'faithfulness_level = "F3"'))
        self.assertTrue(deliverable.acceptance_problems(out))

    def test_set_metadata_changes_exactly_one_key(self):
        from pipeline import naming
        text = TASK_TOML.format(name="x")
        once = naming.set_metadata(text, "faithfulness_level", "F2")
        twice = naming.set_metadata(once, "faithfulness_level", "F1")
        before, after = tomllib.loads(text), tomllib.loads(twice)
        self.assertEqual(after["metadata"].pop("faithfulness_level"), "F1")
        self.assertEqual(before, after)
        bare = naming.set_metadata('[task]\nname = "arena/x"\n', "faithfulness_level", "F3")
        self.assertEqual(tomllib.loads(bare)["metadata"], {"faithfulness_level": "F3"})


# ----------------------------------------------------------------- T4 / A3 --

class DifficultyAndShape(unittest.TestCase):

    def test_pass_at_1_at_half_on_either_model_fails_general_difficulty(self):
        from pipeline import deliverable
        task = _task(per_model={PRIMARY: {"model": PRIMARY, "pass_at_1": 0.1},
                                SECONDARY: {"model": SECONDARY, "pass_at_1": 0.5}})
        self.assertIs(deliverable.general_difficulty(task), False)
        self.assertIn("FAILS", deliverable._general_label(task))
        verdict = deliverable.batch_acceptance([task], {"ok": True})
        quality = next(c for c in verdict["criteria"] if c["criterion"] == "Task quality")
        self.assertFalse(quality["ok"])
        self.assertIs(deliverable.general_difficulty(_task()), True)

    def test_tasks_per_environment_is_reported(self):
        from pipeline import deliverable
        shape = deliverable.tasks_per_environment([
            {"bundle": "a", "short_name": "a", "session_id": "s1"},
            {"bundle": "b", "short_name": "b", "session_id": "s1"},
            {"bundle": "c", "short_name": "c", "session_id": "s2"}])
        self.assertEqual((shape["environments"], shape["tasks"], shape["max"],
                          shape["multi_task_environments"]), (2, 3, 2, 1))
        self.assertEqual(shape["by_environment"]["s1"], ["a", "b"])


# --------------------------------------------------------------------- T6 --

class SyntheticIsLabelled(unittest.TestCase):
    """Spec T6: invented data labelled synthetic."""

    def _ledger_codes(self, declared):
        from pipeline.gates.base import GateContext
        from pipeline.gates.bundle import ledger_gate
        root = Path(tempfile.mkdtemp())
        raw = b"invented case facts\n"
        _write(root / "environment/files/case.md", raw.decode())
        _write(root / "provenance/ledger.json", json.dumps({"entries": [
            {"path": "case.md", "origin": "authored", "bytes": len(raw),
             "sha256": hashlib.sha256(raw).hexdigest()}], "faithfulness_by_bytes": 0.0}))
        with mock.patch("pipeline.author.scenario.verify", return_value=declared):
            result = ledger_gate.run(GateContext(task_dir=root, repo_root=root))
        return {f.code for f in result.findings}

    def test_an_undeclared_authored_file_is_blocked(self):
        self.assertIn("unlabelled-synthetic", self._ledger_codes({}))

    def test_a_declared_authored_file_carries_its_notice(self):
        self.assertNotIn("unlabelled-synthetic", self._ledger_codes({"case.md": {}}))


if __name__ == "__main__":
    unittest.main()
