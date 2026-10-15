"""Tests for the selection and gate chain.

Each test names the defect it defends against. Several are regressions against
bugs found by running the gates over shipped bundles -- those are marked, because
a heuristic gate that was never run against real material is a guess.
"""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from pipeline import config
from pipeline.dump import recover, signals
from pipeline.author import traps as T
from pipeline.gates import difficulty as D
from pipeline.gates import findings as F
from pipeline.gates import integrity as I
from pipeline.gates.base import (Finding, FunctionGate, GateContext, Severity,
                                 Status, green, run_gates)
from pipeline.ledger import faithfulness
from pipeline.select import priority, score, shortlist


def _ok(_ctx):
    return [], {}


def _fail(_ctx):
    return [Finding(Severity.BLOCKER, "x", "boom")], {}


def _boom(_ctx):
    raise ValueError("cannot check")


class GateRunner(unittest.TestCase):
    def test_error_is_not_failure(self):
        """An exception means we could not check, which is not a verdict."""
        r = FunctionGate("g", _boom).run(GateContext(Path("."), Path(".")))
        self.assertIs(r.status, Status.ERROR)
        self.assertIn("cannot check", r.error)

    def test_dependent_of_failed_gate_is_skipped_not_failed(self):
        gates = [FunctionGate("a", _fail), FunctionGate("b", _ok, requires=("a",))]
        results = run_gates(gates, GateContext(Path("."), Path(".")))
        self.assertIs(results[0].status, Status.FAIL)
        self.assertIs(results[1].status, Status.SKIPPED)

    def test_skipped_is_not_green(self):
        """'Could not check' must never read as 'nothing wrong'."""
        gates = [FunctionGate("a", _fail), FunctionGate("b", _ok, requires=("a",))]
        self.assertFalse(green(run_gates(gates, GateContext(Path("."), Path(".")))))

    def test_gate_cannot_pass_while_holding_a_blocker(self):
        r = FunctionGate("g", lambda c: ([Finding(Severity.BLOCKER, "c", "m")], {})).run(
            GateContext(Path("."), Path(".")))
        self.assertIs(r.status, Status.FAIL)


class Selection(unittest.TestCase):
    def _row(self, **over):
        row = dict(session_id="s", seed_index=0, n_turns=8, corrections=3,
                   rec_paths=9, rec_bytes=90_000, rec_versions=3,
                   deliv_paths=8, deliv_bytes=90_000, deliv_versions=3,
                   structured_paths=2, code_bytes=2_000, deliv_share=0.98,
                   kw_tagged=True, categories=["document_creation"],
                   steer_fail=2, outcome_fail=1, longest_run=3, model_tier="frontier",
                   trail_paths=10, trail_covered=6, manifests=[], tests=0,
                   bash_total=100, bash_truncated=1, binary_refs=0,
                   slices=["knowledge_work"])
        row.update(over)
        return row

    def test_aesthetic_only_session_is_dropped(self):
        v = score.kill_filters(self._row(categories=["image_video_generation"]))
        self.assertFalse(v.kept)
        self.assertIn("K1", v.reason)

    def test_session_mixing_aesthetics_and_knowledge_work_is_kept(self):
        """Dropping the whole session would lose the document work alongside it."""
        self.assertTrue(score.kill_filters(
            self._row(categories=["image_video_generation", "document_creation"])).kept)

    def test_code_dominant_seed_is_out_of_scope(self):
        """Scope is non-coding professional knowledge work. Categories are
        session-level and cannot decide this; the byte split can."""
        v = score.kill_filters(self._row(deliv_share=0.2))
        self.assertFalse(v.kept)
        self.assertIn("K6", v.reason)

    def test_seed_without_a_knowledge_work_category_is_dropped(self):
        v = score.kill_filters(self._row(categories=["code_writing"], kw_tagged=False))
        self.assertFalse(v.kept)
        self.assertIn("K7", v.reason)

    def test_deliverable_recovery_not_source_recovery_decides(self):
        """A seed with plenty of recovered SOURCE but no documents is not a
        knowledge-work candidate, however rich the repo.

        This used to be caught by K4 (no fixture). Category D admits seeds with
        no liftable fixture -- that is what D IS -- so the guarantee now rests
        where it always belonged: the byte split. No recovered deliverable
        alongside half a megabyte of source means a deliverable share of zero,
        and K6 refuses it. The scope rule is what keeps code out, not the
        fixture floor.
        """
        v = score.kill_filters(self._row(rec_paths=40, rec_bytes=500_000,
                                         deliv_paths=0, deliv_bytes=0,
                                         code_bytes=500_000, deliv_share=0.0))
        self.assertFalse(v.kept)
        self.assertIn("K6", v.reason)

    def test_one_correction_is_admitted_but_ranks_low(self):
        """It used to be killed. Killing it threw away everything batch two
        would have been built from; a thin trace is a worse starting point, not
        an inadmissible one."""
        self.assertTrue(score.kill_filters(self._row(corrections=1)).kept)
        thin = priority.evidence(dict(self._row(), corrections=1, longest_run=1,
                                      undone=0, steer_fail=1, complaint_fail=0,
                                      outcome_fail=0, steer_ok=0, outcome_ok=0))
        self.assertGreater(priority.tier_of(thin), 1)

    def test_zero_corrections_is_admissible_only_as_a_fixture_led_seed(self):
        """A dispute is what categories A and B are built from. C and D are not.

        "Reconcile these thirty-two documents" is a real question whether or
        not anyone argued about it, so a correction signal is required of the
        dispute-led categories and not of the others. Applying the A/B bar to
        all four collapsed this corpus from 360 in-scope seeds to 110.
        """
        self.assertTrue(score.kill_filters(self._row(corrections=0)).kept)

    def test_no_correction_and_no_fixture_is_still_within_scope_only(self):
        """Category D needs a scenario; it does not need documents.

        What it still needs is to be non-coding knowledge work, and that is
        checked by K6/K7 exactly as before.
        """
        self.assertTrue(score.kill_filters(
            self._row(corrections=0, deliv_paths=1, deliv_bytes=500)).kept)
        for out_of_scope in (dict(deliv_share=0.1, code_bytes=90_000),
                             dict(kw_tagged=False, categories=[])):
            with self.subTest(**out_of_scope):
                v = score.kill_filters(self._row(
                    corrections=0, deliv_paths=1, deliv_bytes=500, **out_of_scope))
                self.assertFalse(v.kept, "the non-coding scope rule must still bite")

    def test_replay_readiness_is_bounded(self):
        for row in (self._row(), self._row(rec_paths=999, rec_bytes=10**9,
                                           rec_versions=99, trail_covered=99),
                    self._row(rec_paths=3, rec_bytes=20_000, rec_versions=0,
                              trail_covered=0, manifests=[], tests=0, binary_refs=50)):
            value, parts = score.replay_readiness(row)
            self.assertGreaterEqual(value, 0.0)
            self.assertLessEqual(value, 1.0)
            self.assertTrue(all(0.0 <= v <= 1.0 for v in parts.values()))

    def test_rank_is_multiplicative_so_taste_sinks_a_recoverable_seed(self):
        """A perfect workspace whose every correction is taste must not rank.

        This is the failure the mechanical score cannot see on its own, and the
        reason Stage D exists: ranked by corrections alone, the top of the corpus
        is "make my dress the same colour".
        """
        base = self._row()
        base.update(replay_readiness=1.0, dispute=0.9,
                    classification={"usable_ratio": 0.0, "truth_source": "none",
                                    "classes": {}})
        self.assertEqual(shortlist.rank(base), 0.0)

    def test_empty_slot_is_never_backfilled(self):
        rows = [dict(self._row(), session_id="a", replay_readiness=0.9, dispute=0.8,
                     session_candidate_seeds=1,
                     classification={"survives": True, "usable_ratio": 1.0,
                                     "truth_source": "numeric_tolerance",
                                     "classes": {}})]
        out = shortlist.compose(rows, size=3)
        filled = [s for s in out["slots"] if s["filled"]]
        self.assertEqual(len(filled), 1)
        self.assertEqual(len(out["batch"]), 1)


class Priority(unittest.TestCase):
    def _row(self, **over):
        row = dict(session_id="s", seed_index=0, deliv_paths=8, deliv_bytes=120_000,
                   deliv_versions=3, files_ok=6, ws_snapshots=30,
                   trail_paths=10, trail_covered=8, corrections=6, longest_run=4,
                   undone=3, steer_fail=4, complaint_fail=2, outcome_fail=2,
                   steer_ok=3, outcome_ok=3, model_tier="frontier")
        row.update(over)
        return row

    def test_axes_are_bounded(self):
        for row in (self._row(), self._row(deliv_paths=999, corrections=99,
                                           steer_fail=99, files_ok=99),
                    self._row(deliv_paths=0, deliv_bytes=0, corrections=0,
                              longest_run=0, undone=0, steer_fail=0,
                              complaint_fail=0, outcome_fail=0, steer_ok=0,
                              outcome_ok=0, files_ok=0, ws_snapshots=0,
                              trail_covered=0)):
            ev = priority.evidence(row)
            for v in (ev.attachments, ev.corrections, ev.signals, ev.total):
                self.assertGreaterEqual(v, 0.0)
                self.assertLessEqual(v, 1.0)

    def test_one_empty_axis_cannot_reach_tier_one(self):
        """Two strong axes and a bare one is a tier-2 trace with a known gap."""
        rich = self._row()
        self.assertEqual(priority.tier_of(priority.evidence(rich)), 1)
        gutted = self._row(corrections=0, longest_run=0, undone=0)
        self.assertGreater(priority.tier_of(priority.evidence(gutted)), 1)

    def test_tier_always_beats_rank(self):
        """A rich tier-2 trace must not outrank a thin tier-1 one, or the
        priority order is decorative."""
        rows = [
            dict(self._row(session_id="thin-t1"), tier=1,
                 replay_readiness=0.6, dispute=0.4,
                 classification={"survives": True, "usable_ratio": 0.6,
                                 "truth_source": "numeric_tolerance",
                                 "classes": {}}),
            dict(self._row(session_id="rich-t2"), tier=2,
                 replay_readiness=0.99, dispute=0.99,
                 classification={"survives": True, "usable_ratio": 1.0,
                                 "truth_source": "numeric_tolerance",
                                 "classes": {}}),
        ]
        out = shortlist.compose(rows, size=1)
        self.assertEqual(out["batch"][0]["session_id"], "thin-t1")
        self.assertEqual(out["deepest_tier_drawn"], 1)

    def test_deeper_tiers_carry_a_lower_faithfulness_floor(self):
        floors = priority.TIER_TRACE_FLOOR
        self.assertEqual(sorted(floors, reverse=True),
                         [k for k, _ in sorted(floors.items(), key=lambda kv: kv[1])])
        self.assertGreater(floors[1], floors[4])

    def test_batch_two_does_not_repick_batch_one(self):
        rows = [dict(self._row(session_id=f"s{i}"), tier=1,
                     replay_readiness=0.8, dispute=0.6,
                     classification={"survives": True, "usable_ratio": 1.0,
                                     "truth_source": "numeric_tolerance",
                                     "classes": {}})
                for i in range(2)]
        first = shortlist.compose(rows, size=1)
        picked = first["batch"][0]["session_id"]
        second = shortlist.compose(rows, size=1, taken={picked})
        self.assertNotEqual(second["batch"][0]["session_id"], picked)


class RecoveryAndSignals(unittest.TestCase):
    def _trace(self):
        return {"session_id": "sess", "messages": [
            {"role": "user", "node_ids": ["n0"], "content": [{"type": "text", "text": "fix it"}]},
            {"role": "assistant", "node_ids": ["n1"], "content": [
                {"type": "tool-write_file",
                 "input": {"path": "a.py", "content": "print(1)\n"}},
                {"type": "tool-bash", "input": {"command": "pytest"},
                 "output": {"exit_code": 1, "stdout_truncated": False,
                            "stderr_truncated": True}}]},
            {"role": "user", "node_ids": ["n2"],
             "content": [{"type": "text", "text": "still broken"}]},
            {"role": "assistant", "node_ids": ["n3"], "content": [
                {"type": "tool-edit_file", "input": {"path": "a.py"},
                 "output": {"content": "print(2)\n"}}]},
        ], "tasks": [{"task_index": 0, "task_key": "k", "n_turns": 4,
                      "turn_ids": ["n0", "n1", "n2", "n3"]}]}

    def test_edit_file_output_is_the_whole_body(self):
        """The richest recovery channel: output.content is the post-edit file."""
        ws = recover.recover(self._trace())
        self.assertEqual(sorted(r.content for r in ws.history("a.py")),
                         ["print(1)\n", "print(2)\n"])

    def test_workspace_at_returns_an_intermediate_state(self):
        ws = recover.recover(self._trace())
        self.assertEqual(ws.at(2)["a.py"].content, "print(1)\n")
        self.assertEqual(ws.at(99)["a.py"].content, "print(2)\n")

    def test_truncation_is_read_not_guessed(self):
        """A regex for 'truncat' matches the `stdout_truncated` key itself and
        reports ~100% on a corpus whose measured rate is 1.27%."""
        self.assertEqual(recover.bash_health(self._trace()),
                         {"total": 1, "truncated": 1, "failed": 1})

    def test_dead_signal_is_never_counted(self):
        outcomes = {"outcomes": [
            {"signal_name": "tool_hallucination", "outcome": "failure",
             "annotating_node_id": "n2"},
            {"signal_name": "steerability", "outcome": "failure",
             "annotating_node_id": "n2"}]}
        seed = signals.build_seeds(self._trace(), outcomes)[0]
        self.assertEqual(seed.corrections, 1)
        self.assertEqual(seed.moments[0].user_text, "still broken")


class FindingsGates(unittest.TestCase):
    """One test per Arena finding class, on a synthetic minimal bundle."""

    def _bundle(self, grader: str = "", key: dict | None = None,
                instruction: str = "do the thing", fixture: dict | None = None) -> Path:
        root = Path(tempfile.mkdtemp())
        (root / "tests").mkdir()
        (root / "steps" / "01-x").mkdir(parents=True)
        (root / "environment" / "files").mkdir(parents=True)
        (root / "steps" / "01-x" / "instruction.md").write_text(instruction)
        (root / "tests" / "criteria.py").write_text(grader or "x = 1\n")
        (root / "tests" / "basis.toml").write_text('[checks]\nc = "do the thing"\n')
        if key is not None:
            (root / "tests" / "key").mkdir()
            for name, doc in key.items():
                (root / "tests" / "key" / f"{name}.json").write_text(json.dumps(doc))
        for name, text in (fixture or {}).items():
            (root / "environment" / "files" / name).write_text(text)
        self.addCleanup(lambda: None)
        return root

    def _ctx(self, root: Path) -> GateContext:
        return GateContext(task_dir=root, repo_root=root)

    def test_kw002_type_name_comparison_is_caught(self):
        """Regression: the shipped kw-002 defect is `type(item).__name__` in a
        Counter key, which an isinstance-only detector misses entirely. Found by
        running the gate against the real bundle."""
        root = self._bundle(grader="def f(v):\n    return [(type(i).__name__, i) for i in v]\n")
        r = F.normalisation_gate.run(self._ctx(root))
        self.assertIs(r.status, Status.FAIL)
        self.assertTrue(any(f.code == "type-sensitive-compare" for f in r.blockers))

    def test_float_equality_blocks(self):
        root = self._bundle(grader="def f(x):\n    return x == 1.5\n")
        r = F.normalisation_gate.run(self._ctx(root))
        self.assertTrue(any(f.code == "float-equality" for f in r.blockers))

    def test_kw006_named_accept_list_is_caught(self):
        root = self._bundle(key={"allowed-references": ["D0001", "D0002", "D0003",
                                                        "D0004", "D0005"]})
        r = F.enumeration_gate.run(self._ctx(root))
        self.assertIs(r.status, Status.FAIL)
        self.assertTrue(any(f.code == "hidden-enumeration" for f in r.blockers))

    def test_answer_values_are_not_an_accept_list(self):
        """Regression: keying on 'unpublished' alone fired on 216 fields in one
        shipped bundle, all of them simply the answer."""
        root = self._bundle(key={"audit": {"selected": ["D0001", "D0002", "D0003"]}})
        r = F.enumeration_gate.run(self._ctx(root))
        self.assertIs(r.status, Status.PASS)

    def test_declared_set_is_not_hidden(self):
        root = self._bundle(
            key={"allowed-references": ["D0001", "D0002", "D0003", "D0004"]},
            fixture={"RULES.md": "Acceptable: D0001 D0002 D0003 D0004\n"})
        r = F.enumeration_gate.run(self._ctx(root))
        self.assertIs(r.status, Status.PASS)

    def test_kw003_literal_answer_key_is_caught(self):
        root = self._bundle(key={"audit": {"count": 26}})
        r = F.oracle_gate.run(self._ctx(root))
        self.assertTrue(any(f.code == "literal-answer-key" for f in r.blockers))

    def test_recomputed_key_passes(self):
        root = self._bundle(key={"audit": {"count": 27,
                                           "derivation": "len(register.removals())"}})
        self.assertIs(F.oracle_gate.run(self._ctx(root)).status, Status.PASS)

    def test_rule_published_in_the_fixture_counts_as_published(self):
        """Regression: reading only instruction.md reported a correctly-built
        task as riddled with unpublished rules. The playbook pushes rules INTO
        the fixture on purpose."""
        root = self._bundle(instruction="Follow the desk reference.",
                            fixture={"DESK.md": "do the thing exactly as written"})
        self.assertIs(F.completeness_gate.run(self._ctx(root)).status, Status.PASS)

    def test_digest_in_fixture_blocks_but_vocabulary_does_not(self):
        digest = "9f7a74c5fc4b78763a501496927d18d05ff545d5"
        root = self._bundle(key={"a": {"sha": digest, "status": "contested"}},
                            fixture={"m.json": json.dumps({"sha": digest}),
                                     "v.md": "status may be contested"})
        r = I.derivation_gate.run(self._ctx(root))
        codes = {f.code for f in r.blockers}
        self.assertIn("computed-value-stored", codes)
        self.assertTrue(all("contested" not in f.message for f in r.blockers))

    def test_grading_artefact_in_fixture_blocks(self):
        root = self._bundle(fixture={"criteria.py": "cheat"})
        r = I.leak_gate.run(self._ctx(root))
        self.assertTrue(any(f.code == "grading-artefact-in-fixture" for f in r.blockers))


class AbsentSemantics(unittest.TestCase):
    def test_absent_passes_when_nothing_was_submitted(self):
        """An `absent` guardrail asks that something not be there. A missing
        submission satisfies it -- treating the missing file as a failure made
        every such guardrail fail on the untouched fixture and blocked the
        bundle for a violation that had not happened."""
        from pipeline.author.checks import Check, Workspace, run_check
        root = Path(tempfile.mkdtemp())
        (root / "src").mkdir()
        (root / "sub").mkdir()
        check = Check(id="g", kind="guardrail", weight=0,
                      basis="Do not reopen concepts.", assertion="absent",
                      actual={"op": "field", "file": "report.json",
                              "path": "concepts"},
                      target={"op": "literal", "value": "x", "why": "t"})
        out = run_check(check, Workspace(source=root / "src",
                                         submitted=root / "sub"))
        self.assertTrue(out["passed"])

    def test_any_guardrail_holds_when_nothing_was_submitted(self):
        """A guardrail asserts the agent did not do something; doing nothing
        satisfies it whatever the assertion."""
        from pipeline.author.checks import Check, Workspace, run_check
        root = Path(tempfile.mkdtemp())
        (root / "src").mkdir()
        (root / "sub").mkdir()
        check = Check(id="g", kind="guardrail", weight=0,
                      basis="Do not list French-only labels.",
                      assertion="subset_of",
                      actual={"op": "field", "file": "r.json", "path": "labels"},
                      target={"op": "literal", "value": ["a"], "why": "t"})
        self.assertTrue(run_check(check, Workspace(source=root / "src",
                                                   submitted=root / "sub"))["passed"])

    def test_present_cannot_be_a_guardrail(self):
        from pipeline.author.checks import Check
        problems = Check(id="g", kind="guardrail", weight=0, basis="b",
                         assertion="present",
                         actual={"op": "field", "file": "r.json", "path": "x"}
                         ).validate()
        self.assertTrue(any("cannot assert 'present'" in p for p in problems))

    def test_other_assertions_still_fail_on_a_missing_submission(self):
        from pipeline.author.checks import Check, Workspace, run_check
        root = Path(tempfile.mkdtemp())
        (root / "src").mkdir()
        (root / "sub").mkdir()
        check = Check(id="o", kind="objective", weight=1,
                      basis="Report the count.", assertion="equals",
                      actual={"op": "field", "file": "report.json",
                              "path": "n"},
                      target={"op": "literal", "value": 3, "why": "t"})
        out = run_check(check, Workspace(source=root / "src",
                                         submitted=root / "sub"))
        self.assertFalse(out["passed"])


class CalibrationGates(unittest.TestCase):
    def _ctx(self, report):
        root = Path(tempfile.mkdtemp())
        return GateContext(task_dir=root, repo_root=root, extras={"calibration": report})

    def test_missing_calibration_errors_rather_than_passes(self):
        root = Path(tempfile.mkdtemp())
        r = I.bands_gate.run(GateContext(task_dir=root, repo_root=root))
        self.assertIs(r.status, Status.ERROR)

    def test_gate_on_a_check_nobody_clears_blocks(self):
        """The disaster case: a gate on an unclearable prerequisite makes every
        criterion behind it unreachable, which reads as difficulty."""
        report = {"checks": {
            "a": {"passed": 1, "failed": 9, "kind": "objective"},
            "b": {"passed": 5, "failed": 5, "kind": "objective"},
            "c": {"passed": 4, "failed": 6, "kind": "objective"},
            "d": {"passed": 3, "failed": 7, "kind": "objective"},
            "e": {"passed": 6, "failed": 4, "kind": "objective"}},
            "gates": {"b": ["a"]}}
        r = I.bands_gate.run(self._ctx(report))
        self.assertTrue(any(f.code == "gate-below-band" for f in r.blockers))

    def test_gate_on_a_near_certain_check_warns_but_does_not_block(self):
        """Gating every objective on "did you submit the file" carries no risk --
        it makes nothing unreachable -- but it is structure the scores do not
        show, so it is reported."""
        report = {"checks": {
            "a": {"passed": 10, "failed": 0, "kind": "objective"},
            "b": {"passed": 5, "failed": 5, "kind": "objective"},
            "c": {"passed": 4, "failed": 6, "kind": "objective"},
            "d": {"passed": 3, "failed": 7, "kind": "objective"},
            "e": {"passed": 6, "failed": 4, "kind": "objective"}},
            "gates": {"b": ["a"]}}
        r = I.bands_gate.run(self._ctx(report))
        self.assertFalse([f for f in r.blockers if f.code.startswith("gate-")])
        self.assertTrue(any(f.code == "gate-never-fires" for f in r.warnings))

    def test_gated_out_is_not_counted_as_failed(self):
        report = {"checks": {"a": {"passed": 3, "failed": 3, "gated_out": 20,
                                   "kind": "objective"}}}
        r = I.bands_gate.run(self._ctx(report))
        self.assertEqual(r.evidence["rates"]["a"], 0.5)

    def test_unreachable_check_blocks(self):
        report = {"checks": {"a": {"passed": 0, "failed": 0, "gated_out": 10,
                                   "kind": "objective"}}}
        r = I.bands_gate.run(self._ctx(report))
        self.assertTrue(any(f.code == "dead-check" for f in r.blockers))

    def test_unclassified_zero_blocks(self):
        report = {"rollouts": [{"id": "r1", "reward": 0.0}, {"id": "r2", "reward": 0.5}]}
        r = I.validity_gate.run(self._ctx(report))
        self.assertTrue(any(f.code == "unclassified-zero" for f in r.blockers))

    def test_no_variance_blocks(self):
        report = {"rollouts": [{"id": f"r{i}", "reward": 1.0} for i in range(5)]}
        r = I.validity_gate.run(self._ctx(report))
        self.assertTrue(any(f.code == "no-variance" for f in r.blockers))

    def test_string_reward_blocks(self):
        report = {"rollouts": [{"id": "r1", "reward": "0.5"},
                               {"id": "r2", "reward": 0.5}]}
        r = I.validity_gate.run(self._ctx(report))
        self.assertTrue(any(f.code == "non-numeric-reward" for f in r.blockers))


class Ledger(unittest.TestCase):
    def test_classification(self):
        ws = recover.Workspace("s", [
            recover.Revision("a.py", 1, "print(1)\n" * 20, "write_file", "input")])
        origin, citation, _ = faithfulness.classify("print(1)\n" * 20, ws, "s")
        self.assertEqual(origin, "lifted")
        self.assertIn("msg1", citation)

        origin, citation, sim = faithfulness.classify(
            "print(1)\n" * 19 + "print(2)\n", ws, "s")
        self.assertEqual(origin, "derived")
        self.assertGreaterEqual(sim, faithfulness.DERIVED_FLOOR)

        origin, citation, _ = faithfulness.classify("wholly different\n", ws, "s")
        self.assertEqual(origin, "authored")
        self.assertIsNone(citation)


class Traps(unittest.TestCase):
    def _trap(self, **over):
        base = dict(id="t1", type="forbidden_edit", surface="config.yml",
                    beatable_by="step3", probe="destructive",
                    provenance="trace_derived", derived_from="s::msg4",
                    correction_class="constraint_assertion",
                    quote="keep the PKGBUILD as is", checks=["c1"])
        base.update(over)
        return T.Trap(**base)

    def test_trace_derived_trap_needs_a_citation(self):
        self.assertTrue(any("cites no moment" in p
                            for p in self._trap(derived_from="").validate()))

    def test_correction_class_must_match_the_trap_type(self):
        """A `forbidden_edit` cannot be derived from a taste complaint."""
        problems = self._trap(correction_class="taste").validate()
        self.assertTrue(any("may be derived from" in p for p in problems))

    def test_authored_trap_is_allowed_with_grounding(self):
        trap = self._trap(provenance="authored", derived_from="", quote="",
                          correction_class="",
                          grounding="a print vendor would plausibly send a revised "
                                    "quote after the deadline",
                          grounded_in="QUOTES.md")
        self.assertEqual(trap.validate(), [])

    def test_authored_trap_without_grounding_is_rejected(self):
        trap = self._trap(provenance="authored", derived_from="", quote="",
                          correction_class="")
        self.assertEqual(len(trap.validate()), 2)

    def test_trap_must_drive_a_check(self):
        self.assertTrue(any("drives no check" in p
                            for p in self._trap(checks=[]).validate()))

    def test_trap_must_have_a_probe(self):
        """Without one, nothing shows the trap catches the sloppy answer."""
        self.assertTrue(any("no adversarial probe" in p
                            for p in self._trap(probe="").validate()))

    def test_trace_derived_share(self):
        traps = [self._trap(id="a"), self._trap(id="b", provenance="authored",
                                                derived_from="", quote="",
                                                correction_class="",
                                                grounding="g", grounded_in="f.md")]
        self.assertEqual(T.trace_derived_share(traps), 0.5)

    def test_adding_grounded_traps_does_not_reduce_exploitation(self):
        """The metric asks whether the trace was used, not whether we refrained
        from adding. Measuring derived/total made every good authored trap lower
        the score, which pushed thin traces toward using LESS of their material."""
        derived = [self._trap(id=f"d{i}", derived_from=f"s::m{i}") for i in range(4)]
        self.assertEqual(T.trace_exploitation(derived, 4), 1.0)
        padded = derived + [self._trap(id=f"a{i}", provenance="authored",
                                       derived_from="", quote="",
                                       correction_class="", grounding="g",
                                       grounded_in="f.md") for i in range(6)]
        self.assertEqual(T.trace_exploitation(padded, 4), 1.0)
        self.assertLess(T.trace_derived_share(padded), 0.5)

    def test_exploitation_falls_when_corrections_go_unused(self):
        traps = [self._trap(id="d1", derived_from="s::m1")]
        self.assertEqual(T.trace_exploitation(traps, 5), 0.2)

    def test_trap_floor_is_above_four(self):
        from pipeline.config import MIN_TRAPS, expected_traps
        self.assertGreater(MIN_TRAPS, 4)
        self.assertEqual(expected_traps(1, 1, 1), MIN_TRAPS)
        self.assertGreater(expected_traps(20, 12, 14), expected_traps(3, 5, 8))

    def test_suggest_maps_corrections_to_legitimate_traps(self):
        keys = {t.key for t in T.suggest("constraint_assertion")}
        self.assertIn("forbidden_edit", keys)
        self.assertNotIn("plausible_decoy", keys)

    def test_unsatisfiable_is_the_graded_form_of_giving_up(self):
        spec = T.TAXONOMY["unsatisfiable"]
        self.assertIn("reports that", spec.summary)
        self.assertIn("fabricates", spec.proof)


class HackResistance(unittest.TestCase):
    def _ctx(self, probes, traps=None):
        root = Path(tempfile.mkdtemp())
        (root / "verification").mkdir()
        (root / "authoring").mkdir()
        (root / "verification" / "probes.json").write_text(json.dumps(probes))
        (root / "authoring" / "traps.json").write_text(json.dumps({"traps": traps or []}))
        # The gates re-run the probes; a logic test hands them the report instead.
        return GateContext(task_dir=root, repo_root=root, extras={"probe_report": probes})

    def _full(self, **over):
        results = {k: {"reward": 0.2} for k in D.REQUIRED_PROBES}
        results["golden"] = {"reward": 1.0}
        results["untidy_correct"] = {"reward": 1.0}
        results["seed_zero"] = {"objectives": {"a": 0.0}, "guardrails": {"g": 1.0}}
        results.update(over)
        return {"results": results, "untested_surfaces": ["javascript: URIs"]}

    def test_missing_probe_file_errors_rather_than_passes(self):
        root = Path(tempfile.mkdtemp())
        r = D.hack_gate.run(GateContext(task_dir=root, repo_root=root))
        self.assertIs(r.status, Status.ERROR)

    def test_successful_forgery_blocks(self):
        r = D.hack_gate.run(self._ctx(self._full(forged_state={"reward": 1.0})))
        self.assertTrue(any(f.code == "reward-hack-succeeds" for f in r.blockers))

    def test_answer_lookup_succeeding_blocks(self):
        r = D.hack_gate.run(self._ctx(self._full(answer_lookup={"reward": 1.0})))
        self.assertTrue(any(f.code == "reward-hack-succeeds" for f in r.blockers))

    def test_partial_hack_warns(self):
        r = D.hack_gate.run(self._ctx(self._full(forged_state={"reward": 0.8})))
        self.assertTrue(any(f.code == "reward-hack-partial" for f in r.warnings))

    def test_objective_passing_on_pristine_fixture_blocks(self):
        probes = self._full(seed_zero={"objectives": {"a": 0.5},
                                       "guardrails": {"g": 1.0}})
        r = D.hack_gate.run(self._ctx(probes))
        self.assertTrue(any(f.code == "seed-zero-objective" for f in r.blockers))

    def test_guardrail_failing_on_pristine_fixture_blocks(self):
        probes = self._full(seed_zero={"objectives": {"a": 0.0},
                                       "guardrails": {"g": 0.0}})
        r = D.hack_gate.run(self._ctx(probes))
        self.assertTrue(any(f.code == "seed-zero-guardrail" for f in r.blockers))

    def test_undeclared_untested_surfaces_blocks(self):
        probes = self._full(); probes.pop("untested_surfaces")
        r = D.hack_gate.run(self._ctx(probes))
        self.assertTrue(any(f.code == "no-untested-declaration" for f in r.blockers))

    def test_trap_the_reference_cannot_beat_blocks(self):
        traps = [dict(id="t1", type="forbidden_edit", surface="s",
                      beatable_by="x", probe="destructive",
                      provenance="trace_derived", derived_from="s::m1",
                      correction_class="constraint_assertion", quote="q",
                      checks=["c1"])]
        probes = self._full(golden={"reward": 0.6})
        r = D.trap_beatable_gate.run(self._ctx(probes, traps))
        self.assertTrue(any(f.code == "golden-below-one" for f in r.blockers))

    def test_trap_that_catches_nothing_blocks(self):
        traps = [dict(id="t1", type="forbidden_edit", surface="s",
                      beatable_by="x", probe="destructive",
                      provenance="trace_derived", derived_from="s::m1",
                      correction_class="constraint_assertion", quote="q",
                      checks=["c1"])]
        probes = self._full(destructive={"reward": 1.0})
        r = D.trap_beatable_gate.run(self._ctx(probes, traps))
        # v2 (user, 2026-10-02): trap bookkeeping is advisory; dead checks are
        # still caught by the executed counterexample controls (quality.controls).
        self.assertTrue(any(f.code == "trap-not-discriminating" for f in r.warnings))
        self.assertFalse(any(f.code == "trap-not-discriminating" for f in r.blockers))

    def test_single_axis_advises_and_never_blocks(self):
        # Phase 3 is validity only; trap-axis coverage is a difficulty judgment.
        traps = [dict(id=f"t{i}", type="forbidden_edit", surface="s",
                      beatable_by="x", probe="destructive",
                      provenance="trace_derived", derived_from="s::m1",
                      correction_class="constraint_assertion", quote="q",
                      checks=["c1"]) for i in range(2)]
        r = D.axes_gate.run(self._ctx(self._full(), traps))
        self.assertTrue(any(f.code == "one-axis" for f in r.warnings))
        self.assertFalse(any(f.code in {"one-axis", "carry-only"} for f in r.blockers))

    def test_ignoring_the_traces_corrections_blocks(self):
        """Every trap authored, none derived: the trace supplied five real
        failure modes and the bundle used none of them."""
        traps = [dict(id=f"t{i}", type="forbidden_edit", surface="s",
                      beatable_by="x", probe="destructive", provenance="authored",
                      grounding="g", grounded_in="F.md", checks=["c1"])
                 for i in range(6)]
        root = Path(tempfile.mkdtemp())
        for sub in ("verification", "authoring"):
            (root / sub).mkdir()
        (root / "environment" / "files").mkdir(parents=True)
        (root / "environment" / "files" / "F.md").write_text("x")
        (root / "tests").mkdir()
        (root / "tests" / "checks.json").write_text(json.dumps(
            {"checks": [{"id": "c1", "kind": "objective"}]}))
        (root / "verification" / "probes.json").write_text(json.dumps(self._full()))
        (root / "authoring" / "traps.json").write_text(json.dumps(
            {"traps": traps, "source_tier": 1, "usable_corrections": 5}))
        r = D.trap_faithful_gate.run(GateContext(task_dir=root, repo_root=root))
        # v2: the trace-exploitation floor is reported, never blocking.
        self.assertTrue(any(f.code == "trace-underused" for f in r.warnings))
        self.assertFalse(any(f.code == "trace-underused" for f in r.blockers))


class Config(unittest.TestCase):
    def test_tiering(self):
        self.assertEqual(config.tier("claude-opus-5-high-vertex"), "frontier")
        self.assertEqual(config.tier("gemma-4-31b-it"), "other")
        self.assertEqual(config.tier(None), "other")

    def test_scope_is_knowledge_work(self):
        self.assertEqual(config.SCOPE, "knowledge_work")
        self.assertNotIn("held_out_tests", config.KNOWLEDGE_WORK_TRUTH)
        self.assertNotIn("build_or_compile", config.KNOWLEDGE_WORK_TRUTH)

    def test_rr_weights_sum_to_one(self):
        self.assertAlmostEqual(sum(config.RR_WEIGHTS.values()), 1.0, places=6)

    def test_tool_hallucination_is_excluded(self):
        """1 failure in 72,398 annotations. It discriminates nothing."""
        self.assertIn("tool_hallucination", config.DEAD_SIGNALS)


if __name__ == "__main__":
    unittest.main()
