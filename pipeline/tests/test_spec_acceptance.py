"""The acceptance policy rewritten on 2026-09-23, tested against its reasons.

Each test here names the defect it exists to prevent. Two of them are the gate
inversions that closed the funnel at both ends in `envs-cat-v2`: a solvability
gate that required a model to solve the task perfectly before difficulty was
measured, and a band gate that forbade the band composition a hard task has.
"""
from __future__ import annotations

import json
import tempfile
import types
import unittest
import unittest.mock
from pathlib import Path

from pipeline import attribution, metrics, naming, policy, repair
from pipeline.ledger import levels
from pipeline.tests.test_capability_construction import alignment_witnesses


def rollouts(rewards, steps=("01-task",), **overrides):
    """Build campaign rollout rows: one entry per (episode, step)."""
    rows = []
    for episode, value in enumerate(rewards, start=1):
        for step in steps:
            row = {"id": f"{step}-{episode:02d}", "episode": episode, "step": step,
                   "reward": value, "stop_reason": "end_turn", "tool_calls": 5,
                   "zero_class": None if value else "model_failure",
                   "error": "", "checks": {}}
            row.update(overrides)
            rows.append(row)
    return rows


class PassAtK(unittest.TestCase):
    """pass@1/pass@4 are the spec's difficulty language and were never computed."""

    def test_unbiased_estimator_differs_from_the_naive_form(self):
        # 1 - (1-c/n)^k assumes sampling with replacement and is optimistic at
        # the n=10 the spec asks for. The gap straddles a reporting band, so
        # the wrong form would misreport difficulty.
        self.assertAlmostEqual(metrics.pass_at_k(10, 1, 4), 0.4)
        self.assertNotAlmostEqual(1 - (1 - 0.1) ** 4, 0.4, places=2)

    def test_k_greater_than_n_is_undefined_not_certain(self):
        self.assertIsNone(metrics.pass_at_k(3, 1, 4))

    def test_no_passes_is_zero_and_all_passes_is_one(self):
        self.assertEqual(metrics.pass_at_k(10, 0, 4), 0.0)
        self.assertEqual(metrics.pass_at_k(10, 10, 1), 1.0)

    def test_partial_reward_is_not_a_partial_pass(self):
        # The spec defines hard as "passes no more than 2 of 10 runs"; a run
        # either passed or it did not.
        report = {"model": "m", "step_names": ["01-task"],
                  "rollouts": rollouts([1.0, 0.99, 0.5, 0.0])}
        out = metrics.task_metrics(report)
        self.assertEqual(out["passes"], 1)
        self.assertAlmostEqual(out["pass_at_1"], 0.25)


class VoidsAreNotDifficulty(unittest.TestCase):
    """A void measures nothing; averaging it in makes our infrastructure look
    like model incapability."""

    def test_void_episodes_leave_the_denominator(self):
        report = {"model": "m", "step_names": ["01-task"],
                  "rollouts": rollouts([1.0, 1.0]) + rollouts([0.0])}
        report["rollouts"][-1].update(zero_class="void", reward=None)
        report["rollouts"][-1]["episode"] = 3
        out = metrics.task_metrics(report)
        self.assertEqual(out["episodes_valid"], 2)
        self.assertEqual(out["episodes_void"], 1)
        self.assertEqual(out["pass_at_1"], 1.0)      # not 2/3

    def test_truncation_is_void_not_a_zero(self):
        rows = rollouts([0.0])
        rows[0]["stop_reason"] = "max_tokens"
        verdict = attribution.episode_verdict(rows, contract_checks=set())
        self.assertEqual(verdict["verdict"], "void")

    def test_a_short_campaign_blocks_rather_than_reporting_a_rate(self):
        primary = metrics.task_metrics({"model": "m", "step_names": ["01-task"],
                                        "rollouts": rollouts([0.0] * 4)})
        issues = metrics.difficulty_problems(primary, primary)
        self.assertTrue(any("valid episodes" in i for i in issues), issues)


class DifficultyAdmission(unittest.TestCase):
    """The band gate forbade hard tasks by construction. pass@1 replaces it."""

    def test_an_all_fail_task_is_admissible(self):
        report = {"model": "m", "step_names": ["01-task"],
                  "rollouts": rollouts([0.0] * 10)}
        primary = metrics.task_metrics(report)
        self.assertEqual(primary["pass_at_1"], 0.0)
        self.assertEqual(metrics.difficulty_problems(primary, primary), [])
        self.assertTrue(metrics.hardness(primary, primary)["hard"])

    def test_an_easy_task_is_reported_never_refused(self):
        # User, 2026-09-25: pass@1 < 0.5 is the strict target and never a
        # blocker. An easy task is measured and labelled, not refused, and the
        # next task is never held behind it.
        self.assertFalse(policy.DIFFICULTY_GATES_RELEASE)
        report = {"model": "m", "step_names": ["01-task"],
                  "rollouts": rollouts([1.0] * 10)}
        primary = metrics.task_metrics(report)
        self.assertEqual(metrics.difficulty_problems(primary, primary), [])
        verdict = metrics.hardness(primary, primary)
        self.assertFalse(verdict["meets_spec_general_difficulty"])
        self.assertEqual(verdict["worst_pass_at_1"], 1.0)

    def test_the_valid_episode_floor_still_blocks(self):
        # The MEASUREMENT must be complete even though its value never blocks.
        report = {"model": "m", "step_names": ["01-task"], "rollouts": rollouts([1.0] * 4)}
        primary = metrics.task_metrics(report)
        self.assertTrue(any("valid episodes" in i for i in metrics.difficulty_problems(primary, primary)))

    def test_the_reported_bound_matches_the_strict_spec_target(self):
        report = {"model": "m", "step_names": ["01-task"],
                  "rollouts": rollouts([1.0] * 5 + [0.0] * 5)}
        primary = metrics.task_metrics(report)
        verdict = metrics.hardness(primary, primary)
        self.assertEqual(primary["pass_at_1"], 0.5)
        self.assertFalse(verdict["meets_release_bound"])
        # User 2026-10-02: "Below or equal to 0.5 is considered hard."
        self.assertTrue(verdict["meets_spec_general_difficulty"])

    def test_batch_closer_enforces_the_spec_share(self):
        marginal = {"hardness": {"worst_pass_at_1": 0.55, "hard": False,
                                 "meets_spec_general_difficulty": False}}
        good = {"hardness": {"worst_pass_at_1": 0.1, "hard": True,
                             "meets_spec_general_difficulty": True}}
        verdict = metrics.batch_difficulty([marginal] * 3 + [good] * 7)
        self.assertFalse(verdict["ok"])
        self.assertTrue(any("batch criterion" in p for p in verdict["problems"]))

    def test_a_batch_with_no_hard_task_is_flagged(self):
        row = {"hardness": {"worst_pass_at_1": 0.4, "hard": False,
                            "meets_spec_general_difficulty": True}}
        verdict = metrics.batch_difficulty([row] * 10)
        self.assertTrue(any("no task in this batch is hard" in p
                            for p in verdict["problems"]), verdict)


class FailureAttribution(unittest.TestCase):
    """Spec: confirm failures are capability, not ambiguity or a bug."""

    def test_a_wrong_answer_is_a_capability_failure(self):
        rows = rollouts([0.2])
        rows[0]["checks"] = {"present": "passed", "decision": "failed"}
        verdict = attribution.episode_verdict(rows, contract_checks={"present"})
        self.assertEqual(verdict["verdict"], "capability")

    def test_a_malformed_deliverable_is_a_contract_failure(self):
        rows = rollouts([0.0])
        rows[0]["checks"] = {"present": "failed", "decision": "failed"}
        verdict = attribution.episode_verdict(rows, contract_checks={"present"})
        self.assertEqual(verdict["verdict"], "contract")

    def test_an_adapter_stall_is_void_not_incapability(self):
        rows = rollouts([0.0])
        rows[0]["tool_calls"] = 0
        self.assertEqual(
            attribution.episode_verdict(rows, set())["verdict"], "void")

    def test_contract_deaths_above_the_ceiling_are_suspicious(self):
        # Contract failures look exactly like difficulty in a results table.
        checks = {"present": "failed"}
        rows = []
        for episode in range(1, 11):
            rows.append({"id": f"r{episode}", "episode": episode, "step": "01-task",
                         "reward": 0.0, "stop_reason": "end_turn", "tool_calls": 3,
                         "zero_class": "model_failure", "error": "",
                         "checks": checks})
        report = {"model": "m", "step_names": ["01-task"], "rollouts": rows}
        with tempfile.TemporaryDirectory() as tmp:
            bundle = Path(tmp)
            (bundle / "tests").mkdir()
            (bundle / "tests/checks.json").write_text(json.dumps({"checks": [
                {"id": "present", "kind": "objective", "weight": 100,
                 "band_declared": "floor", "target": {"op": "present"}}]}))
            record = attribution.attribute(bundle, report)
        self.assertEqual(record["contract_failures"], 10)
        self.assertTrue(any("output contract" in p for p in record["problems"]))


class AllFailChecksMustEarnIt(unittest.TestCase):
    """A hard task has many all-fail checks; each needs evidence it is real."""

    def _bundle(self, tmp, quality):
        bundle = Path(tmp)
        (bundle / "tests").mkdir(parents=True)
        (bundle / "authoring").mkdir(parents=True)
        (bundle / "tests/checks.json").write_text(json.dumps({"checks": [
            {"id": "decision", "kind": "objective", "weight": 100,
             "target": {"op": "rows"}}]}))
        (bundle / "authoring/spec.json").write_text(
            json.dumps({"quality": quality}))
        return bundle

    def test_all_fail_without_a_counterfactual_blocks(self):
        report = {"model": "m", "by_step": {
            "01-task": {"checks": {"decision": {"passed": 0, "failed": 10,
                                                "gated_out": 0}}}}}
        with tempfile.TemporaryDirectory() as tmp:
            bundle = self._bundle(tmp, {})
            issues = attribution.all_fail_problems(bundle, report)
        self.assertTrue(any("source counterfactual" in i for i in issues), issues)

    def test_declared_but_unexecuted_proof_is_not_credited(self):
        # Declaring a source case or an alternative proves nothing; only the
        # executed controls receipt can (see test_fix_attribution, which
        # accepts an all-fail check on executed proof).
        report = {"model": "m", "by_step": {
            "01-task": {"checks": {"decision": {"passed": 0, "failed": 10,
                                                "gated_out": 0}}}}}
        quality = {"source_cases": [{"id": "sc1", "changes": ["decision"]}],
                   "alternatives": [{"checks": ["decision"]}]}
        with tempfile.TemporaryDirectory() as tmp:
            bundle = self._bundle(tmp, quality)
            issues = attribution.all_fail_problems(bundle, report)
        self.assertTrue(any("no executed controls" in i for i in issues), issues)

    def test_a_check_nothing_reached_is_unreachable_not_hard(self):
        report = {"model": "m", "by_step": {
            "01-task": {"checks": {"decision": {"passed": 0, "failed": 0,
                                                "gated_out": 10}}}}}
        with tempfile.TemporaryDirectory() as tmp:
            bundle = self._bundle(tmp, {})
            issues = attribution.all_fail_problems(bundle, report)
        self.assertTrue(any("never attempted" in i for i in issues), issues)


class FaithfulnessLevels(unittest.TestCase):
    """Arena's taxonomy, which two batch criteria and two yield metrics key on."""

    def test_f1_plus_and_f2_plus_shares_are_the_updated_batch_criterion(self):
        records = [{"level": "F3"}, {"level": "F2"}] + [{"level": "F1"}] * 3
        mix = levels.batch_mix(records)
        self.assertAlmostEqual(mix["f2_plus_share"], 0.4)
        self.assertTrue(mix["ok"])
        self.assertEqual(mix["f1_plus_share"], 1.0)

    def test_f0_is_allowed_and_unrelated_is_rejected(self):
        self.assertEqual(levels.problems({"level": "F0"}), [])
        self.assertTrue(levels.problems({"level": "F-1"}))
        self.assertEqual(levels.problems({"level": "F2"}), [])

    def test_every_level_has_a_definition_and_only_unrelated_lacks_a_folder(self):
        for level in ("F3", "F2", "F1", "F0", "F-1"):
            self.assertIn(level, policy.FAITHFULNESS_LEVELS)
        self.assertEqual(policy.DELIVERY_DIRS.get("F0"), "F0-inspired")
        self.assertIsNone(policy.DELIVERY_DIRS.get("F-1"))
        self.assertEqual(set(policy.DELIVERY_DIRS), {"F3", "F2", "F1", "F0"})


class NamingConvention(unittest.TestCase):
    """a_f3_<task-name>, and it has to survive `harbor tasks-check`."""

    def test_short_name_carries_the_level(self):
        self.assertEqual(naming.short_name("F3", "a-123-content-marketing"),
                         "a_f3_content-marketing")

    def test_package_name_matches_harbors_org_pattern(self):
        import re
        pattern = re.compile(
            r"^[a-zA-Z0-9][a-zA-Z0-9._-]*/[a-zA-Z0-9][a-zA-Z0-9._-]*$")
        for level in ("F1", "F2", "F3"):
            name = naming.package_name(level, "some-editorial-task")
            self.assertRegex(name, pattern)
            self.assertEqual(naming.parse(name)["level"], level)

    def test_a_name_that_disagrees_with_the_ledger_is_a_defect(self):
        with tempfile.TemporaryDirectory() as tmp:
            bundle = Path(tmp) / "a_f3_thing"
            bundle.mkdir()
            (bundle / "task.toml").write_text(
                '[task]\nname = "arena/a_f3_thing"\n')
            self.assertEqual(naming.problems(bundle, "F3"), [])
            issues = naming.problems(bundle, "F1")
        self.assertTrue(any("claims faithfulness" in i for i in issues), issues)


class RepairTerminates(unittest.TestCase):
    """47 of 86 candidates were discarded holding actionable findings. The fix
    is bounded repair; the invariant is what keeps it bounded."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.bundle = Path(self.tmp.name)
        (self.bundle / "verification").mkdir()
        self.finding = "checks.json chk_window omits the journaling ceiling"

    def tearDown(self):
        self.tmp.cleanup()

    def test_a_first_cited_finding_is_repairable(self):
        ok, why = repair.admissible(self.bundle, [self.finding])
        self.assertTrue(ok, why)

    def test_a_finding_that_survives_its_own_repair_is_terminal(self):
        repair.record_pass(self.bundle, [self.finding], "revised")
        ok, why = repair.admissible(self.bundle, [self.finding])
        self.assertFalse(ok)
        self.assertIn("survived a repair pass", why)

    def test_churn_that_does_not_shrink_is_terminal(self):
        repair.record_pass(self.bundle, ["checks.json a", "checks.json b"],
                           "revised")
        ok, why = repair.admissible(self.bundle, ["checks.json c", "checks.json d"])
        self.assertFalse(ok)
        self.assertIn("did not shrink", why)

    def test_a_first_semantic_review_is_not_measured_against_the_gates(self):
        # e2e build, 2026-09-26: 12 gate findings, all fixed by the repair; the
        # semantic review then ran for the first time with 13 findings, and the
        # governor refused the budgeted repair as "did not shrink (12 -> 13)".
        repair.record_pass(self.bundle, [f"contract.completeness: empty-basis: check c{i} [tests/basis.toml]"
                                         for i in range(12)], "charged")
        review = [f"Semantic review obj_{i}: count-only check [tests/checks.json]" for i in range(13)]
        ok, why = repair.admissible(self.bundle, review)
        self.assertTrue(ok, why)

    def test_first_exported_gates_are_not_compared_with_pre_export_validation(self):
        for finding in ["Draft validation: missing source intervention [authoring/spec.json]",
                        "source changes do not exercise s1_folio and s2_folio [authoring/spec.json]"]:
            with self.subTest(finding=finding):
                path = self.bundle / repair.LOG
                if path.exists():
                    path.unlink()
                repair.record_pass(self.bundle, [finding], "charged")
                gates = [f"env.step_isolation: scope for file {number} [environment/files]" for number in range(4)]
                admitted, reason = repair.admissible(self.bundle, gates)
                self.assertTrue(admitted, reason)

    def test_draft_validation_churn_still_stops(self):
        repair.record_pass(self.bundle, ["Draft validation: old rule [authoring/spec.json]"], "charged")
        admitted, reason = repair.admissible(self.bundle, ["Draft validation: new rule [authoring/spec.json]"])
        self.assertFalse(admitted)
        self.assertIn("did not shrink", reason)
        self.assertIn("draft-validation", reason)

    def test_new_stage_never_refunds_the_shared_pass_budget(self):
        repair.record_pass(self.bundle, ["Draft validation: first rule [authoring/spec.json]"], "charged")
        repair.record_pass(self.bundle, ["Draft validation: second rule [authoring/spec.json]"], "charged")
        admitted, reason = repair.admissible(self.bundle, ["env.step_isolation: scope [environment/files]"])
        self.assertFalse(admitted)
        self.assertIn("budget exhausted", reason)

    def test_shrinking_is_still_required_within_a_stage(self):
        repair.record_pass(self.bundle, ["Semantic review obj_a: x [tests/checks.json]",
                                         "Semantic review obj_b: y [tests/checks.json]"], "charged")
        ok, why = repair.admissible(self.bundle, ["Semantic review obj_c: z [tests/checks.json]",
                                                  "Semantic review obj_d: w [tests/checks.json]"])
        self.assertFalse(ok)
        self.assertIn("did not shrink", why)
        self.assertIn("semantic-review", why)

    def test_a_finding_repeated_from_any_earlier_stage_is_terminal(self):
        repair.record_pass(self.bundle, ["checks.json chk_window omits the ceiling",
                                         "checks.json other"], "charged")
        ok, why = repair.admissible(self.bundle, ["Semantic review obj_a: new [tests/checks.json]",
                                                  "checks.json chk_window omits the ceiling"])
        self.assertFalse(ok)
        self.assertIn("survived a repair pass", why)

    def test_real_progress_is_allowed(self):
        repair.record_pass(self.bundle, ["checks.json a", "checks.json b"],
                           "revised")
        ok, why = repair.admissible(self.bundle, ["checks.json c"])
        self.assertTrue(ok, why)

    def test_the_budget_is_finite(self):
        for i in range(policy.MAX_REPAIR_PASSES):
            repair.record_pass(self.bundle, [f"checks.json f{i}"], "revised")
        ok, why = repair.admissible(self.bundle, ["checks.json final"])
        self.assertFalse(ok)
        self.assertIn("budget exhausted", why)

    def test_an_uncitable_finding_is_not_actionable(self):
        ok, why = repair.admissible(self.bundle, ["the task is too easy"])
        self.assertFalse(ok)
        self.assertIn("concrete artifact location", why)

    def test_a_terminal_candidate_keeps_its_findings(self):
        record = repair.disposition(self.bundle, [self.finding], "repeated")
        self.assertFalse(record["repairable"])
        self.assertEqual(record["outstanding_findings"], [self.finding])
        self.assertTrue((self.bundle / "verification/repair-disposition.json").is_file())


class ReferenceSolutionDerives(unittest.TestCase):
    """Harbor's `hardcoded_solution` criterion, and the spec's 'scripted'."""

    def test_a_copying_oracle_is_reported(self):
        from pipeline.author import solution
        with tempfile.TemporaryDirectory() as tmp:
            bundle = Path(tmp)
            step = bundle / "steps/01-task/solution"
            step.mkdir(parents=True)
            (step / "solve.sh").write_text(
                "#!/bin/sh\ncp -R /solution/submission/. /app/deliverables/\n")
            issues = solution.problems(bundle)
        self.assertTrue(any("copies a stored answer" in i for i in issues), issues)

    def test_a_deriving_oracle_is_not_called_copying_but_must_still_score(self):
        from pipeline.author import solution
        with tempfile.TemporaryDirectory() as tmp:
            bundle = Path(tmp)
            step = bundle / "steps/01-task/solution"
            step.mkdir(parents=True)
            (step / "solve.sh").write_text("#!/bin/sh\npython3 /solution/solve.py\n")
            (step / "solve.py").write_text("# derives\n")
            issues = solution.problems(bundle)
            self.assertFalse(any("copies a stored answer" in i for i in issues), issues)
            # Looking like a derivation is not scoring like one: a script that
            # has not been executed through the grader is not a pass.
            self.assertTrue(issues)

    def test_a_missing_reference_is_not_a_pass(self):
        from pipeline.author import solution
        with tempfile.TemporaryDirectory() as tmp:
            self.assertTrue(solution.problems(Path(tmp)))

    def test_the_plan_excludes_guardrails_and_names_where_answers_go(self):
        from pipeline.author import solution
        spec = {"checks": [
            {"id": "a", "kind": "objective", "step": "01-task",
             "actual": {"op": "field", "file": "answer.json", "path": "rows"},
             "target": {"op": "rows"}},
            {"id": "g", "kind": "guardrail", "step": "01-task",
             "actual": {"op": "fixture"}, "target": {"op": "rows"}}]}
        plan = solution.plan(spec, "01-task")
        self.assertEqual([o["id"] for o in plan["objectives"]], ["a"])
        self.assertIn("answer.json", plan["documents"])


class InversionsAreRecorded(unittest.TestCase):
    """Both removed gates are named constants, so their absence is greppable
    rather than implied by a missing call."""

    def test_the_blind_solve_no_longer_gates(self):
        self.assertFalse(policy.BLIND_SOLVE_GATES_RELEASE)

    def test_bands_no_longer_gate(self):
        self.assertFalse(policy.BANDS_GATE_RELEASE)

    def test_release_source_no_longer_requires_a_perfect_blind_episode(self):
        source = (Path(__file__).resolve().parents[1] / "release.py").read_text()
        self.assertNotIn("no independently solved complete episode scores 1 "
                         "on every step\")\n        return issues", source)

    def test_the_spec_thresholds_are_the_specs(self):
        self.assertEqual(policy.SPEC_GENERAL_DIFFICULTY_MAX, 0.5)
        self.assertEqual(policy.SPEC_HARD_MAX, 0.2)
        self.assertEqual(policy.SPEC_EPISODES_PER_MODEL, 10)
        self.assertEqual(policy.SPEC_F1_PLUS_MIN, 0.50)
        self.assertEqual(policy.SPEC_F2_PLUS_MIN, 0.15)
        self.assertEqual(policy.SPEC_MULTI_TURN_MIN, 0.10)
        self.assertEqual(policy.SPEC_MAX_REWARD_HACKING, 0)


if __name__ == "__main__":
    unittest.main()


class LevelLadderMatchesArenasDefinitions(unittest.TestCase):
    """Regression: a 96.7%-lifted fixture was being classified F0.

    Measured on `a-123-content-marketing-planning`, whose ledger records
    faithfulness_by_bytes 0.967 with nine authored traps. An earlier rule keyed
    F2 on trace-derived traps alone and called it F0 -- "nothing recoverable
    from the trace" -- when the documents and the scenario were the session's
    and only the difficulty had been invented, which the spec permits.

    The decisive reading is F1's own wording: "fully synthetic world". A largely
    lifted fixture is not one, so it cannot sit below F2.
    """

    def _bundle(self, tmp, traps):
        bundle = Path(tmp)
        (bundle / "authoring").mkdir(parents=True)
        (bundle / "authoring/traps.json").write_text(json.dumps({"traps": traps}))
        (bundle / "authoring/spec.json").write_text(json.dumps({"traps": traps}))
        return bundle

    def test_a_lifted_fixture_with_authored_traps_and_verified_alignment_is_f2(self):
        authored = [{"provenance": "authored"} for _ in range(9)]
        with tempfile.TemporaryDirectory() as tmp:
            bundle = self._bundle(tmp, authored)
            record = levels.assign(bundle, {"faithfulness_by_bytes": 0.967,
                                             "trace_alignment": alignment_witnesses()})
        self.assertEqual(record["level"], "F2")
        self.assertEqual(record["delivery_dir"], "F2-scenario")
        self.assertEqual(levels.problems(record), [])

    def test_a_lifted_fixture_with_trace_derived_traps_is_f3(self):
        traps = [{"provenance": "trace_derived", "derived_from": f"s::msg{i}"}
                 for i in range(8)] + [{"provenance": "authored"}]
        with tempfile.TemporaryDirectory() as tmp:
            bundle = self._bundle(tmp, traps)
            record = levels.assign(bundle, {"faithfulness_by_bytes": 0.97})
        self.assertEqual(record["level"], "F3")

    def test_a_synthetic_world_needs_calibration_evidence_for_f1(self):
        # Fully synthetic world (fidelity below the scenario floor) preserving
        # only a failure mode: one trace-derived trap among nine authored ones,
        # so the grading criteria are not substantially the trace's either.
        # Arena's F1 makes the empirical clause a requirement -- "calibration
        # runs must show models failing the same way" -- so without that
        # evidence the task is F0, not F1.
        traps = ([{"provenance": "trace_derived", "derived_from": "s::msg1"}]
                 + [{"provenance": "authored"} for _ in range(9)])
        with tempfile.TemporaryDirectory() as tmp:
            bundle = self._bundle(tmp, traps)
            unproven = levels.assign(bundle, {"faithfulness_by_bytes": 0.05,
                                               "trace_alignment": alignment_witnesses({"goal", "capability"})})
            proven = levels.assign(bundle, {"faithfulness_by_bytes": 0.05},
                                   calibration_reproduces_failure=True)
        self.assertEqual(unproven["level"], "F0")
        self.assertTrue(any("failing the same way" in r
                            for r in unproven["why_not_higher"]))
        self.assertEqual(proven["level"], "F1")
        self.assertEqual(proven["delivery_dir"], "F1-pattern")

    def test_a_cited_correction_alone_does_not_lift_a_synthetic_world_to_f2(self):
        # F1 is defined as preserving the failure mode ALONE. If a cited
        # correction were enough for F2, F1 could never be reached.
        traps = ([{"provenance": "trace_derived", "derived_from": "s::msg1"}]
                 + [{"provenance": "authored"} for _ in range(9)])
        with tempfile.TemporaryDirectory() as tmp:
            bundle = self._bundle(tmp, traps)
            record = levels.assign(bundle, {"faithfulness_by_bytes": 0.01},
                                   calibration_reproduces_failure=True)
        self.assertEqual(record["level"], "F1")

    def test_nothing_recoverable_is_unrelated_and_blocks(self):
        with tempfile.TemporaryDirectory() as tmp:
            bundle = self._bundle(tmp, [{"provenance": "authored"}])
            record = levels.assign(bundle, {"faithfulness_by_bytes": 0.0})
        self.assertEqual(record["level"], "F-1")
        self.assertTrue(levels.problems(record))
        self.assertIsNone(record["delivery_dir"])

    def test_why_not_higher_is_always_explained(self):
        with tempfile.TemporaryDirectory() as tmp:
            bundle = self._bundle(tmp, [{"provenance": "authored"}])
            record = levels.assign(bundle, {"faithfulness_by_bytes": 0.5,
                                             "trace_alignment": alignment_witnesses()})
        self.assertEqual(record["level"], "F2")
        self.assertTrue(record["why_not_higher"],
                        "a level below F3 must say what it is missing")


class BatchDeliverable(unittest.TestCase):
    """The three deliverables that were computable and never assembled."""

    def setUp(self):
        from pipeline import deliverable
        self.d = deliverable

    def test_an_undispositioned_session_fails_trace_accounting(self):
        record = self.d.trace_accounting(["s1", "s2"], {"s1": ["a_f2_x"]}, {})
        self.assertFalse(record["ok"])
        self.assertEqual(record["undispositioned"], 1)

    def test_an_empty_exclusion_reason_is_not_a_disposition(self):
        record = self.d.trace_accounting(["s1"], {}, {"s1": "   "})
        self.assertFalse(record["ok"])

    def test_full_disposition_passes(self):
        record = self.d.trace_accounting(
            ["s1", "s2"], {"s1": ["a_f2_x"]}, {"s2": "requires_execution"})
        self.assertTrue(record["ok"])
        self.assertEqual(record["dispositioned_share"], 1.0)

    def test_yield_denominator_is_every_shared_session(self):
        tasks = [{"session_id": "s1", "faithfulness_level": "F2",
                  "accepted": True, "hardness": {"hard": True}}]
        out = self.d.yield_metrics(["s1", "s2", "s3", "s4"], tasks)
        self.assertEqual(out["environment_yield"], 0.25)
        self.assertEqual(out["hard_task_yield"], 0.25)

    def test_an_unaccepted_hard_task_does_not_count_toward_difficulty_yield(self):
        tasks = [{"session_id": "s1", "faithfulness_level": "F2",
                  "accepted": False, "hardness": {"hard": True}}]
        out = self.d.yield_metrics(["s1", "s2"], tasks)
        self.assertEqual(out["environment_yield"], 0.5)
        self.assertEqual(out["difficulty_yield"], 0.0)

    def test_an_f1_hard_task_counts_for_both_updated_yields(self):
        tasks = [{"session_id": "s1", "faithfulness_level": "F1",
                  "accepted": True, "hardness": {"hard": True}}]
        out = self.d.yield_metrics(["s1"], tasks)
        self.assertEqual(out["difficulty_yield"], 1.0)
        self.assertEqual(out["hard_task_yield"], 1.0)

    def test_golden_and_untidy_correct_are_not_reward_hacking(self):
        # Regression, measured on the real candidate corpus: counting every
        # probe at 1.0 as an exploit reported 81 cases across 38 bundles, all
        # of them the reference solution and a correctly reworded answer doing
        # exactly what they are supposed to do. The real count was 5.
        self.assertIn("golden", policy.EXPECT_FULL_CREDIT)
        self.assertIn("untidy_correct", policy.EXPECT_FULL_CREDIT)
        for name in policy.EXPECT_FULL_CREDIT:
            self.assertNotIn(name, policy.HACK_PROBES)

    def test_a_plausible_wrong_answer_scoring_full_marks_is_a_finding(self):
        self.assertIn("plausible_wrong", policy.HACK_PROBES)

    def test_the_six_batch_criteria_are_all_reported(self):
        acct = self.d.trace_accounting(["s1"], {"s1": ["a_f2_x"]}, {})
        # Reviewable (spec B1) needs both resolved calibration models, the runs
        # exported and the provenance ledger -- not merely a non-empty per_model.
        from pipeline import policy
        tasks = [{"session_id": "s1", "faithfulness_level": "F2",
                  "accepted": True, "multi_turn": True,
                  "harbor_tasks_check": "pass",
                  "per_model": {m: {"model": m, "pass_at_1": 0.1}
                                for m in policy.resolve_calibration_models()},
                  "runs": {"exported": True}, "provenance_included": True,
                  "reward_hacking_findings": [],
                  "hardness": {"hard": True,
                               "meets_spec_general_difficulty": True}}]
        verdict = self.d.batch_acceptance(tasks, acct)
        names = [c["criterion"] for c in verdict["criteria"]]
        self.assertEqual(names, ["Reviewable", "Task quality", "Reward hacking",
                                 "Faithfulness mix", "Trace accounting",
                                 "Multi-turn"])
        self.assertTrue(verdict["ok"], verdict["problems"])

    def test_a_task_without_tasks_check_is_not_reviewable(self):
        acct = self.d.trace_accounting(["s1"], {"s1": ["a_f2_x"]}, {})
        tasks = [{"session_id": "s1", "faithfulness_level": "F2",
                  "accepted": True, "multi_turn": True,
                  "harbor_tasks_check": None, "per_model": {"m": {}},
                  "reward_hacking_findings": [],
                  "hardness": {"hard": True,
                               "meets_spec_general_difficulty": True}}]
        verdict = self.d.batch_acceptance(tasks, acct)
        reviewable = next(c for c in verdict["criteria"]
                          if c["criterion"] == "Reviewable")
        self.assertFalse(reviewable["ok"])

    def test_the_markdown_report_renders_without_measurements(self):
        # A batch report has to be legible for a batch that failed, which is
        # exactly when it is read.
        report = {"generated_at": "now", "environments": 1,
                  "acceptance": {"criteria": [], "problems": ["x"], "ok": False},
                  "yield": {}, "faithfulness": {"counts": {}},
                  "trace_accounting": {"sessions_shared": 1, "converted": 0,
                                       "excluded": 0, "undispositioned": 1},
                  "tasks": [{"bundle": "b", "problems": ["no receipt"]}],
                  "deviations": []}
        text = self.d.render_markdown(report)
        self.assertIn("Batch blockers", text)
        self.assertIn("Not accepted", text)


class DeliveryLayout(unittest.TestCase):
    """The working tree is filed by source category; the delivery tree by
    measured faithfulness. They are different questions and different answers."""

    def setUp(self):
        from pipeline import deliver
        self.deliver = deliver
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def _bundle(self, category, name, fidelity, traps):
        b = self.root / "work" / category / name
        (b / "provenance").mkdir(parents=True)
        (b / "authoring").mkdir(parents=True)
        (b / "task.toml").write_text(f'[task]\nname = "arena/{name}"\n')
        (b / "provenance/ledger.json").write_text(
            json.dumps({"faithfulness_by_bytes": fidelity,
                        "trace_alignment": alignment_witnesses() if fidelity >= 0.2 else {}}))
        (b / "authoring/traps.json").write_text(json.dumps({"traps": traps}))
        (b / "authoring/spec.json").write_text(json.dumps({"traps": traps}))
        return b

    def test_delivery_folder_is_the_measured_level_not_the_source_category(self):
        derived = [{"provenance": "trace_derived", "derived_from": f"s::m{i}"}
                   for i in range(8)] + [{"provenance": "authored"}]
        # Filed under `thin/` by source category, but measures F3.
        self._bundle("thin", "a-001-example", 0.97, derived)
        document = self.deliver.plan(self.root / "work")
        row = document["rows"][0]
        self.assertEqual(row["level"], "F3")
        self.assertEqual(row["destination"], "F3-replay/a_f3_example")

    def test_colliding_names_are_disambiguated(self):
        authored = [{"provenance": "authored"} for _ in range(4)]
        self._bundle("rich", "a-002-brand-consulting", 0.95, authored)
        self._bundle("rich", "a-003-brand-consulting", 0.95, authored)
        document = self.deliver.plan(self.root / "work")
        names = sorted(r["short_name"] for r in document["rows"])
        self.assertEqual(names, ["a_f2_brand-consulting-002",
                                 "a_f2_brand-consulting-003"])
        self.assertIn("a_f2_brand-consulting", document["collisions"])

    def test_an_unrelated_task_is_held_not_delivered(self):
        self._bundle("thin", "a-009-invented", 0.0,
                     [{"provenance": "authored"}])
        record = self.deliver.deliver(self.root / "work", self.root / "out")
        self.assertEqual(record["delivered"], [])
        self.assertEqual(len(record["held"]), 1)
        self.assertIn("F-1", record["held"][0]["held_because"])

    def test_delivering_renames_the_package_and_records_the_level(self):
        authored = [{"provenance": "authored"} for _ in range(4)]
        self._bundle("rich", "a-001-editorial-review", 0.95, authored)
        record = self.deliver.deliver(self.root / "work", self.root / "out")
        self.assertEqual(len(record["delivered"]), 1)
        out = self.root / "out/F2-scenario/a_f2_editorial-review"
        self.assertTrue(out.is_dir())
        self.assertIn('arena/a_f2_editorial-review', (out / "task.toml").read_text())
        ledger = json.loads((out / "provenance/ledger.json").read_text())
        self.assertEqual(ledger["faithfulness_level"], "F2")


def _screen_bundle(root: Path, n_checks: int = 8) -> Path:
    """A minimal bundle a screen can be summarised against."""
    bundle = root / "a-001-screened"
    (bundle / "tests").mkdir(parents=True)
    (bundle / "task.toml").write_text('[task]\nname = "arena/a-001-screened"\n')
    checks = [{"id": f"c{i}", "kind": "objective", "weight": 100 // n_checks,
               "band": "core", "assertion": "equals"} for i in range(n_checks)]
    checks.append({"id": "g_intact", "kind": "guardrail", "weight": 0,
                   "assertion": "fixture_intact"})
    (bundle / "tests/checks.json").write_text(json.dumps({"checks": checks}))
    (bundle / "authoring").mkdir()
    (bundle / "authoring/spec.json").write_text(json.dumps({"_producer": {}}))
    return bundle


def _measured(model: str, episodes: list[dict], step: str = "01-task") -> dict:
    """A verified-shaped measurement: `episodes` maps check id -> passed?"""
    rows, stats = [], {}
    for number, outcome in enumerate(episodes, start=1):
        states = {cid: ("passed" if ok else "failed") for cid, ok in outcome.items()}
        reward = 1.0 if all(outcome.values()) else 0.5
        rows.append({"episode": number, "step": step, "id": f"t{number}/{step}",
                     "reward": reward, "zero_class": None, "error": None,
                     "stop_reason": "completed", "tool_calls": 9, "checks": states})
        for cid, ok in outcome.items():
            rec = stats.setdefault(cid, {"passed": 0, "failed": 0, "gated_out": 0,
                                         "kind": "objective", "weight": 12})
            rec["passed" if ok else "failed"] += 1
    return {"model": model, "by_step": {step: {"checks": stats}}, "rollouts": rows,
            "trials": [], "step_names": [step], "effort": policy.SPEC_CALIBRATION_EFFORT,
            "protocol": "native", "voids_excluded": 0,
            "limits": {"no_limits": policy.SPEC_NO_LIMITS}}


class TheBuildNeverScreensDifficulty(unittest.TestCase):
    """User, 2026-09-25: no hardness check after a single task is created.

    The one-episode presolve used to run after every draft and feed "too easy"
    back into the design loop, and an in-build pilot could spend rollouts per
    task. Both are gone: a task is authored to be hard on its first pass and
    measured with its whole batch once the batch exists.
    """

    ROOT = Path(__file__).resolve().parents[1]

    def test_the_presolve_module_is_gone(self):
        import importlib
        self.assertFalse((self.ROOT / "presolve.py").exists())
        with self.assertRaises(ModuleNotFoundError):
            importlib.import_module("pipeline.presolve")

    def test_no_build_path_reaches_a_solver(self):
        source = (self.ROOT / "orchestrate.py").read_text()
        for gone in ("presolve_stage", "presolve_enabled", "PRESOLVE_", "DIFFICULTY_REPAIRS",
                     "pilot_selection", "calibrate_stage", "--qualify", "--calibrate"):
            self.assertNotIn(gone, source, f"{gone} is back in the build")

    def test_the_cli_has_no_presolve_command_or_flag(self):
        from pipeline.cli import build_parser
        parser = build_parser()
        with self.assertRaises(SystemExit):
            parser.parse_args(["presolve", "x"])
        with self.assertRaises(SystemExit):
            parser.parse_args(["harden", "x", "--no-presolve"])
        self.assertTrue(parser.parse_args(["harden", "x", "--no-screen"]).no_screen)

    def test_the_screen_runs_once_after_the_whole_batch_is_built(self):
        import inspect
        from pipeline import orchestrate
        source = inspect.getsource(orchestrate.main)
        self.assertLess(source.index("report = batch("), source.index("calibrate_batch("),
                        "the screen must start only after every task is authored")
        body = inspect.getsource(orchestrate._build_one)
        for call in ("screen.run", "run_many(", "campaign(", "_calibrate_model", "native_runner"):
            self.assertNotIn(call, body, f"a single task's build reaches a solver via {call}")

    def test_the_screen_width_is_three_per_model_and_the_record_is_ten(self):
        self.assertEqual(policy.SCREEN_EPISODES_PER_MODEL, 3)  # user, 2026-10-16
        self.assertEqual(policy.SPEC_EPISODES_PER_MODEL, 10)
        self.assertEqual(policy.CALIBRATION_TARGET_PASS_AT_1, 0.5)

    def test_a_calibrated_batch_stops_and_reports(self):
        # `calibrate_batch` screens validated tasks only and lists the rest.
        from pipeline import orchestrate
        rows = [{"session_id": "s", "seed_index": 0, "category": None,
                 "classification": {"domain": "ok"}},
                {"session_id": "t", "seed_index": 0, "category": None,
                 "classification": {"domain": "bad"}}]
        report = {"results": [
            {"slug": orchestrate._slug(rows[0], 1), "status": "validated"},
            {"slug": orchestrate._slug(rows[1], 2), "status": "blocked",
             "stage_reached": "gate", "error": "", "blockers": ["weight-budget"]}]}
        with tempfile.TemporaryDirectory() as tmp, \
                unittest.mock.patch("pipeline.screen.run_many", return_value=[]) as run_many:
            doc = orchestrate.calibrate_batch(report, rows, Path(tmp))
        screened = run_many.call_args.args[0]
        self.assertEqual([b.name for b in screened], [orchestrate._slug(rows[0], 1)])
        self.assertEqual(doc["not_screened"][0]["status"], "blocked")


class FirstPassDifficultyIsForced(unittest.TestCase):
    """User, 2026-09-25: the author must build an extremely hard task on the first
    attempt. Said at the top of both the system prompt and the opening message,
    and enforced at authoring time by a required, linked self-audit."""

    @staticmethod
    def _spec(case=True):
        spec = {
            "checks": [{"id": "o1", "kind": "objective"}, {"id": "o2", "kind": "objective"},
                       {"id": "g1", "kind": "guardrail"}],
            "traps": [{"id": "t_premise", "checks": ["o1", "o2"]},
                      {"id": "t_guard", "checks": ["g1"]}],
            "quality": {"counterexamples": [
                {"id": "ce_premise", "fails": ["o2"]}, {"id": "ce_other", "fails": ["o9"]}]}}
        if case:
            spec["quality"]["difficulty_case"] = {
                "hardest_decision": "Re-judging the already-cleared items once the scope revision lands " * 2,
                "first_try_verdict": "The revision changes one column the model has no reason to reread " * 2,
                "script_test": ("for b in briefs: if cap_met(b) and crown_met(b): n += 1 -- but cap_met and "
                                "crown_met need reading each brief's meaning; no column states them"),
                "misreadings": [{"trap": "t_premise",
                                 "misreading": "Treats the cap and the crown as the same requirement",
                                 "why_plausible": "Both readings agree on every brief except crownless ranks",
                                 "diverges_on": "RB-04 only", "counterexample": "ce_premise"}],
                "pitfalls_considered": [
                    {"pitfall": "The cap and the crown are separate requirements on every brief",
                     "family": "merged concepts", "where": "briefs.md", "decision": "planted",
                     "trap": "t_premise"},
                    {"pitfall": "Source files must stay byte-identical while being read",
                     "family": "restraint", "where": "briefs.md", "decision": "planted",
                     "trap": "t_guard"}] + [
                    {"pitfall": f"Candidate pitfall number {i} considered in the brief pack",
                     "family": "boundary", "where": "briefs.md", "decision": "rejected",
                     "reason": "no published rule settles it, so it would be a hidden rule"}
                    for i in range(6)]}
        return spec

    def test_a_complete_linked_case_passes(self):
        from pipeline.author.quality import difficulty_case_problems
        self.assertEqual(difficulty_case_problems(self._spec()), [])

    def test_the_script_test_is_required(self):
        # Scaffolding fix, 2026-09-26: the author must write out the shortest
        # full-marks program and say why it needs the documents' meaning.
        from pipeline.author.quality import difficulty_case_problems
        spec = self._spec()
        del spec["quality"]["difficulty_case"]["script_test"]
        self.assertTrue(any("script_test" in p for p in difficulty_case_problems(spec)))

    def test_the_prompt_asks_for_criteria_not_recipes(self):
        from pipeline.author import agent_designer as a
        from pipeline.author.quality import QUALITY_PROMPT
        self.assertIn("CRITERIA, NOT RECIPES", a.SYSTEM)
        self.assertIn("No pre-judged evidence", a.SYSTEM)
        self.assertIn("Step 2 changes a JUDGMENT", a.SYSTEM)
        self.assertIn("as a criterion, not\n    a procedure", a.SYSTEM)
        self.assertIn("script_test", a.SYSTEM)
        self.assertIn("script_test", QUALITY_PROMPT)
        # Arena's spec asks for field MEANINGS; the recipe wording is gone.
        self.assertNotIn("what every field means and how it is computed", a.SYSTEM)

    def test_a_draft_without_the_case_is_refused(self):
        from pipeline.author.quality import difficulty_case_problems
        found = difficulty_case_problems(self._spec(case=False))
        self.assertTrue(found and "first pass is the only pass" in found[0])

    def test_a_dormant_misreading_is_refused(self):
        from pipeline.author.quality import difficulty_case_problems
        spec = self._spec()
        spec["quality"]["difficulty_case"]["misreadings"][0]["counterexample"] = "ce_other"
        self.assertTrue(any("dormant" in p for p in difficulty_case_problems(spec)))

    def test_every_objective_driving_trap_needs_a_misreading(self):
        from pipeline.author.quality import difficulty_case_problems
        spec = self._spec()
        spec["traps"].append({"id": "t_second", "checks": ["o1"]})
        found = difficulty_case_problems(spec)
        self.assertTrue(any("t_second" in p for p in found), found)
        # A guardrail-only trap is shown live by the destructive probe instead.
        self.assertFalse(any("t_guard" in p for p in found))

    def test_the_trap_hunt_must_be_wide_grounded_and_cover_every_trap(self):
        from pipeline.author.quality import MIN_PITFALLS_CONSIDERED, difficulty_case_problems
        self.assertEqual(MIN_PITFALLS_CONSIDERED, 8)
        spec = self._spec()
        spec["quality"]["difficulty_case"]["pitfalls_considered"] = \
            spec["quality"]["difficulty_case"]["pitfalls_considered"][:5]
        self.assertTrue(any("at least 8" in p for p in difficulty_case_problems(spec)))
        spec = self._spec()
        spec["quality"]["difficulty_case"]["pitfalls_considered"][1]["decision"] = "rejected"
        spec["quality"]["difficulty_case"]["pitfalls_considered"][1]["reason"] = "x" * 30
        self.assertTrue(any("t_guard" in p and "planted" in p for p in difficulty_case_problems(spec)))
        spec = self._spec()
        spec["quality"]["difficulty_case"]["pitfalls_considered"][2]["reason"] = "too thin"
        self.assertTrue(any("rejected pitfall needs its reason" in p for p in difficulty_case_problems(spec)))

    def test_every_candidate_is_grounded_in_a_real_fixture_file(self):
        from pipeline.author.quality import difficulty_case_problems
        with tempfile.TemporaryDirectory() as tmp:
            bundle = Path(tmp)
            (bundle / "environment/files").mkdir(parents=True)
            (bundle / "environment/files/briefs.md").write_text("briefs")
            self.assertEqual(difficulty_case_problems(self._spec(), bundle), [])
            spec = self._spec()
            spec["quality"]["difficulty_case"]["pitfalls_considered"][0]["where"] = "invented.md"
            self.assertTrue(any("not a fixture file" in p for p in difficulty_case_problems(spec, bundle)))

    def test_trap_policy_follows_the_faithfulness_level(self):
        from pipeline.author import agent_designer as a
        # F3-bound: trace first, then ADDITIONAL traps aligned with the scenario,
        # inside the 70% trace-derived share F3 needs.
        # The categories are the spec's target levels (user, 2026-09-26).
        self.assertEqual(set(a.TRAP_POLICY), {"F3", "F2", "F1", "F0"})
        self.assertIn("PLANT ADDITIONAL traps", a.TRAP_POLICY["F3"])
        self.assertIn("for every 7 trace-derived traps you may add up to 3", a.TRAP_POLICY["F3"])
        self.assertIn("Never invent a dispute", a.TRAP_POLICY["F3"])
        # Below F3: invented freely, relevant and aligned to the task.
        for level in ("F2", "F1", "F0"):
            self.assertRegex(a.TRAP_POLICY[level], "(?i)invent (traps )?freely")
            self.assertIn("aligned to this task", a.TRAP_POLICY[level])
        self.assertIn("calibration must show models failing that same way", a.TRAP_POLICY["F1"])
        self.assertIn("Arena accepts F0 with exact source goal and capability witnesses", a.TRAP_POLICY["F0"])

    def test_the_prompt_demands_a_deep_trap_hunt(self):
        from pipeline.author import agent_designer as a
        self.assertIn("THE TRAP HUNT -- think deeply", a.SYSTEM)
        for family in ("REVISED PREMISE", "GOVERNING CONFLICT", "RESIDUE", "MERGED CONCEPTS",
                       "EXCEPTION THAT DOES NOT APPLY", "BOUNDARY", "UNIT OR SCALE",
                       "ENTITY IDENTITY", "COUPLING", "STALE DERIVED VALUE", "SCOPE BAIT",
                       "UNSATISFIABLE ASK", "RESTRAINT"):
            self.assertIn(family, a.SYSTEM)
        self.assertIn("red-team your own draft", a.SYSTEM)
        self.assertIn("TRAP HUNT", a.AUTHORING_MANDATE)

    def test_one_all_wrong_counterexample_cannot_prove_every_trap(self):
        # Review: one counterexample named by every misreading passed the audit.
        from pipeline.author.quality import difficulty_case_problems
        spec = self._spec()
        spec["checks"].append({"id": "o3", "kind": "objective"})
        spec["traps"].append({"id": "t_other", "checks": ["o3"]})
        spec["quality"]["counterexamples"].append({"id": "ce_everything", "fails": ["o1", "o2", "o3"]})
        case = spec["quality"]["difficulty_case"]
        case["misreadings"] = [dict(case["misreadings"][0], counterexample="ce_everything"),
                               dict(case["misreadings"][0], trap="t_other", counterexample="ce_everything")]
        case["pitfalls_considered"][0]["trap"] = "t_premise"
        case["pitfalls_considered"].append(dict(case["pitfalls_considered"][0], trap="t_other"))
        found = difficulty_case_problems(spec)
        self.assertTrue(any("also fails" in p for p in found), found)
        self.assertTrue(any("already encodes" in p for p in found), found)

    def test_a_misreading_that_loses_every_objective_is_refused(self):
        # Re-review: a trap claiming every objective let an all-wrong answer
        # pass the "fails only what the trap drives" rule.
        from pipeline.author.quality import difficulty_case_problems
        spec = self._spec()
        spec["quality"]["counterexamples"][0]["fails"] = ["o1", "o2"]
        found = difficulty_case_problems(spec)
        self.assertTrue(any("fails every objective" in p for p in found), found)
        self.assertEqual(difficulty_case_problems(self._spec()), [])

    def test_a_misreading_may_lose_at_most_the_policy_share_of_objectives(self):
        # Re-review: a trap claiming all but one objective, with a distinct
        # near-all-wrong answer, passed every rule.
        from pipeline.author.quality import difficulty_case_problems
        self.assertEqual(policy.MISREADING_MAX_OBJECTIVE_SHARE, 0.5)
        spec = self._spec()
        spec["checks"] += [{"id": f"o{i}", "kind": "objective"} for i in range(3, 6)]
        spec["traps"][0]["checks"] = ["o1", "o2", "o3", "o4"]
        spec["quality"]["counterexamples"][0]["fails"] = ["o1", "o2", "o3", "o4"]
        found = difficulty_case_problems(spec)
        self.assertTrue(any("fails 4 of 5 objectives" in p and "at most 50%" in p for p in found), found)
        spec["quality"]["counterexamples"][0]["fails"] = ["o1", "o2"]
        self.assertFalse(any("objectives; a misreading may lose" in p for p in difficulty_case_problems(spec)))

    def test_the_reviewer_ties_each_counterexample_to_its_misreading(self):
        from pipeline import review
        self.assertIn("quality.difficulty_case", review.PROMPT)
        self.assertIn("what that reading would\nactually produce", review.PROMPT)

    def test_two_traps_cannot_share_one_wrong_answer_under_two_names(self):
        from pipeline.author.quality import difficulty_case_problems
        spec = self._spec()
        spec["checks"].append({"id": "o3", "kind": "objective"})
        spec["traps"].append({"id": "t_second", "checks": ["o1"]})
        wrong = {"answer.json": {"total": 7}}
        spec["quality"]["counterexamples"][0].update(fails=["o1"], submission=wrong)
        spec["quality"]["counterexamples"].append({"id": "ce_second", "fails": ["o1"],
                                                   "submission": dict(wrong)})
        case = spec["quality"]["difficulty_case"]
        case["misreadings"].append(dict(case["misreadings"][0], trap="t_second", counterexample="ce_second"))
        case["pitfalls_considered"].append(dict(case["pitfalls_considered"][0], trap="t_second"))
        found = difficulty_case_problems(spec)
        self.assertTrue(any("submits exactly what 'ce_premise'" in p for p in found), found)
        spec["quality"]["counterexamples"][-1]["submission"] = {"answer.json": {"total": 9}}
        self.assertFalse(any("submits exactly" in p for p in difficulty_case_problems(spec)))

    def test_the_prompt_states_what_is_enforced(self):
        from pipeline.author import agent_designer as a
        from pipeline.config import MIN_TRAPS
        # v2 (user, 2026-10-02): the trap count is an advisory target, stated as such.
        self.assertIn(f"for {MIN_TRAPS} or more", a.SYSTEM)
        self.assertIn("ADVISORY (reported by check_draft, never blocking)", a.SYSTEM)
        self.assertNotIn("At least one trap.", a.SYSTEM)
        # Only traps that drive an objective need a misreading; a guardrail-only
        # trap is shown live by the destructive probe.
        self.assertIn("every trap that drives an\n    objective has its own misreading", a.SYSTEM)
        self.assertNotIn("each a genuine pitfall with its own misreading", a.SYSTEM)
        self.assertIn("at most 2 times in 10 (pass@1 <= 0.2", a.SYSTEM)
        self.assertIn("this trap's OWN", a.SYSTEM)

    def test_a_revision_session_is_governed_by_its_brief(self):
        # Review: the first-pass mandate ("build every genuine trap") was sent
        # with REPAIR briefs saying "do not add traps".
        import inspect
        from pipeline.author import agent_designer as a
        self.assertIn("revise the staged draft exactly as the brief above", a.REVISION_MANDATE)
        self.assertIn("never because a repair is difficult", a.REVISION_MANDATE)
        self.assertIn("(REVISION_MANDATE if revision else AUTHORING_MANDATE)", inspect.getsource(a.design))

    def test_it_binds_authoring_not_already_built_bundles(self):
        import inspect
        from pipeline.author import agent_designer, quality
        self.assertIn("production_problems(draft, bundle, authoring=True)",
                      inspect.getsource(agent_designer))
        gate = inspect.getsource(quality.gate)
        self.assertIn("production_problems(spec, ctx.task_dir)", gate)
        self.assertNotIn("authoring=True", gate)

    def test_the_mandate_opens_both_the_system_prompt_and_the_conversation(self):
        import inspect
        from pipeline.author import agent_designer as a
        self.assertLess(a.SYSTEM.index("THE FIRST PASS IS THE ONLY PASS"),
                        a.SYSTEM.index("HOW HARD, EXACTLY"))
        for text in ("THIS IS YOUR ONE CHANCE", "TWO NON-NEGOTIABLE REQUIREMENTS", "EXCELLENT QUALITY",
                     "EXTREMELY HARD", "ARENA QUALITY BAR", "WHAT THE INDEPENDENT REVIEWER REJECTS",
                     "Publish the RULE, never its RESULT", "THE DIFFICULTY SELF-AUDIT",
                     "quality.difficulty_case"):
            self.assertIn(text, a.SYSTEM)
        # One target, stated consistently: strict < 0.5, aim for <= 0.2.
        self.assertNotIn("read this before anything else", a.SYSTEM)
        self.assertIn(f"pass@1 below {policy.CALIBRATION_TARGET_PASS_AT_1} on BOTH", a.SYSTEM)
        self.assertIn(f"pass@1 <= {policy.SPEC_HARD_MAX}", a.SYSTEM)
        self.assertTrue(a.AUTHORING_MANDATE.startswith(
            "YOUR MANDATE: on this first attempt, design a task that is BOTH of EXCELLENT "
            "QUALITY and EXTREMELY HARD"))
        # Quality is never framed as secondary to difficulty.
        self.assertNotIn("Your job is not to produce a valid task", a.SYSTEM)
        self.assertNotIn("a failed design", a.AUTHORING_MANDATE)
        body = inspect.getsource(a.design)
        # Prepended last among the brief's parts, so it is the first thing read
        # (repair feedback, when present, is placed ahead of it on purpose).
        self.assertIn('opening = (REVISION_MANDATE if revision else AUTHORING_MANDATE) + "\\n\\n" + opening', body)
        self.assertLess(body.index("CATEGORY_GUIDANCE[level]"),
                        body.index("opening = (REVISION_MANDATE if revision else AUTHORING_MANDATE)"))

    def test_the_arena_quality_bar_is_stated_clause_by_clause(self):
        from pipeline.author import agent_designer as a
        bar = a.SYSTEM[a.SYSTEM.index("ARENA QUALITY BAR"):a.SYSTEM.index("Nothing screens this draft")]
        for clause in ("Self-contained and reproducible", "never contain the completed solution",
                       "reached only\n    after the earlier one is completed and graded",
                       "Clear requirements", "Hidden checks may test unseen cases of STATED requirements",
                       "labelled synthetic", "not busy work", "never an LLM judge",
                       "Each turn has its own rubric", "Grades only stated requirements",
                       "cannot access or infer the grading logic", "Grader sanity", "Solvability",
                       "General difficulty", "Reward hacking: zero", "F-1 is forbidden"):
            self.assertIn(clause, bar)
        self.assertIn(f"sum to {policy.WEIGHT_TOTAL}", bar)


class ThePromptNeverUnderminesQuality(unittest.TestCase):
    """User, 2026-09-26: quality is co-equal with difficulty, and the prompt must
    not contradict the Arena spec, itself or the pipeline. Each phrase below was
    found in the prompt and removed; this keeps it out."""

    FORBIDDEN = {
        "Your job is not to produce a valid task": "ranks quality below difficulty",
        "as confusing as": "conflicts with the spec's clear-requirements rule",
        "nobody will make it harder": "false: manual hardening exists",
        "no later attempt": "false: validity repair and hardening exist",
        "Calibrated bands and a blind solve are required for release": "stale: neither gates release",
        "worth more than a trap you invented": "undercuts invention below F3",
        "call `design` with that same spec": "contradicts check_draft/submit_draft",
        "one wrong premise must cost several graded checks": "wrong pass@1 rationale",
        "Checked mechanically before the task\nis calibrated": "overclaims mechanical checking",
        "Confusing is not unfair": "conflicts with clear requirements",
    }

    def _texts(self):
        from pipeline import harden
        from pipeline.author import agent_designer as a
        from pipeline.author.quality import QUALITY_PROMPT
        import inspect
        return {"system": a.SYSTEM + QUALITY_PROMPT, "mandate": a.AUTHORING_MANDATE,
                "opening": inspect.getsource(a._opening), "trap_policy": " ".join(a.TRAP_POLICY.values()),
                "harden": harden.HARDENING_BRIEF + harden.FIRST_ATTEMPT + harden.TIGHTEN_ATTEMPT
                          + harden.REPAIR_ATTEMPT}

    def test_no_quality_undermining_or_stale_phrase_remains(self):
        for where, text in self._texts().items():
            for phrase, why in self.FORBIDDEN.items():
                with self.subTest(where=where, phrase=phrase):
                    self.assertNotIn(phrase, text, why)

    def test_the_trap_count_is_a_target_not_a_quota(self):
        import inspect
        from pipeline.author import agent_designer as a
        from pipeline.gates import difficulty
        self.assertIn("never a quota to pad", inspect.getsource(a._opening))
        source = inspect.getsource(difficulty)
        self.assertIn('Severity.WARN, "below-scaled-trap-budget"', source)
        # v2 (user, 2026-10-02): the trap floor is an advisory, not a blocker.
        self.assertIn('Severity.WARN, "below-trap-floor"', source)

    def test_f3_provenance_is_never_stretched(self):
        from pipeline.author import agent_designer as a
        self.assertIn("Provenance is never stretched to reach F3", a.TRAP_POLICY["F3"])
        self.assertIn("a mislabelled trap is a quality defect", a.TRAP_POLICY["F3"])


class DesignerSeesTheWholeTrace(unittest.TestCase):
    """User, 2026-09-26: the designer must see all the important trace information.

    Measured on session 01a014c3: `read_trace` rendered text blocks only; tool
    calls (typed `tool-bash`, ... not `tool-call`) rendered as nothing, and the
    user's per-turn feedback -- in 496 of 500 sessions -- was read by nothing in
    the pipeline. outcomes.json was never exposed to the designer.
    """

    MESSAGES = [
        {"role": "user", "content": [{"type": "text", "text": "Merge every html I sent."}], "node_ids": ["n0"]},
        {"role": "assistant", "node_ids": ["n1"], "feedback": {"check_in": "disapprove"},
         "error": {"friendlyMessage": "This request couldn't be processed."},
         "content": [{"type": "text", "text": "Done, I kept a summary."},
                     {"type": "tool-bash", "state": "output-available",
                      "input": {"command": "wc -c uploads/*"}, "output": {"stdout": "910K total"}}]},
        {"role": "user", "content": [{"type": "text", "text": "No -- keep ALL the content, not a summary."}],
         "node_ids": ["n2"], "undone": True},
    ]

    def test_the_transcript_shows_feedback_tools_errors_and_undo(self):
        from pipeline.author.agent_designer import _render_message
        rendered = _render_message(self.MESSAGES[1], limit=None)
        self.assertIn("[USER FEEDBACK on this response: check_in=disapprove]", rendered)
        self.assertIn("[tool bash (output-available) input:", rendered)
        self.assertIn("wc -c uploads/*", rendered)
        self.assertIn("910K total", rendered)
        self.assertIn("[ERROR on this message: This request couldn't be processed.]", rendered)
        self.assertIn("[UNDONE", _render_message(self.MESSAGES[2], limit=None))

    def _handlers(self, outcomes):
        from types import SimpleNamespace
        from pipeline.author import agent_designer as a
        trace = {"messages": self.MESSAGES, "stats": {"disapproves": 1},
                 "tasks": [{"task_index": 0, "n_turns": 2, "turn_ids": ["n1", "n2"]}]}
        extraction = SimpleNamespace(session_id="sess0001", seed_index=0, span=(0, 2), moments=[])
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / "environment/files").mkdir(parents=True)
            handlers = a._handlers(Path(tmp), extraction, trace)
            with unittest.mock.patch("pipeline.dump.signals.load_outcomes", return_value=outcomes):
                return handlers["list_corrections"](), handlers["read_signals"]()

    def test_rejected_turns_are_listed_with_what_the_user_said_next(self):
        corrections, _ = self._handlers({"outcomes": []})
        rows = corrections["user_feedback"]
        self.assertEqual([(r["msg"], r["user_verdict"]) for r in rows], [(1, "disapprove")])
        self.assertIn("keep ALL the content", rows[0]["user_said_next"])
        self.assertTrue(rows[0]["in_seed_span"])

    def test_arena_signals_reach_the_designer_mapped_to_messages(self):
        outcomes = {"outcomes": [
            {"signal_name": "steerability", "outcome": "failure", "observation_id": "n1::3::c"},
            {"signal_name": "tool_hallucination", "outcome": "success", "observation_id": "n1::4::c"}]}
        _, signals = self._handlers(outcomes)
        self.assertEqual(signals["signals"]["steerability"]["rows"][0]["msg"], 1)
        self.assertEqual(signals["signals"]["tool_hallucination"]["counts"], {"success": 1})
        self.assertEqual(signals["signals"]["tool_hallucination"]["rows"], [])
        self.assertEqual(signals["user_feedback_counts"], {"disapprove": 1})
        self.assertEqual(signals["tasks"][0]["messages"], [1, 2])
        self.assertIn("never use it as the reward", signals["note"])

    def test_read_evidence_can_search_inside_a_large_file_body(self):
        from pipeline.dump.evidence import Catalog, FIND_MAX_MATCHES
        body = ("x" * 50_000 + "NEEDLE-ROW ") * 3
        catalog = Catalog.__new__(Catalog)
        catalog.records = {"file-0": {"id": "file-0", "kind": "file_version", "path": "big.json",
                                      "text": body}}
        catalog.inspected, catalog.inspected_members = set(), set()
        found = catalog.read("file-0", find="needle-row")
        self.assertEqual(found["match_count"], 3)
        self.assertEqual([m["char_offset"] for m in found["matches"]],
                         [50_000, 100_011, 150_022])
        self.assertIn("NEEDLE-ROW", found["matches"][0]["excerpt"])
        self.assertNotIn("text", found, "a search returns matches, not a page")
        self.assertGreaterEqual(FIND_MAX_MATCHES, 20)

    def test_find_offsets_are_exact_where_casefolding_changes_length(self):
        from pipeline.dump.evidence import Catalog
        text = "Straße Maß -- NEEDLE"
        catalog = Catalog.__new__(Catalog)
        catalog.records = {"f": {"id": "f", "kind": "file_version", "path": "a.txt", "text": text}}
        catalog.inspected, catalog.inspected_members = set(), set()
        found = catalog.read("f", find="needle")
        self.assertEqual(found["matches"][0]["char_offset"], text.index("NEEDLE"))

    def test_the_tools_are_offered_and_described(self):
        from pipeline.author import agent_designer as a
        tools = {t["name"]: t["description"] for t in a._tools(3)}
        self.assertIn("read_signals", tools)
        self.assertIn("per-turn feedback", tools["read_trace"])
        self.assertIn("EDITED, DISAPPROVED or ESCAPED", tools["list_corrections"])
        self.assertIn("`find`", tools["read_evidence"])
        self.assertIn("workspace file version", tools["read_evidence"])


class ScreenAndRunFollowTheRules(unittest.TestCase):

    SHORT_PRIOR = {"episodes_per_model": 5, "artifact_sha256": "sha",
                   "index": {"topups": {"short-fable": ["fable-topup-1"]}},
                   "per_model": {
                       "anthropic/claude-fable-5-1": {"campaign": "short-fable", "episodes_valid": 3,
                           "evidence_problems": ["need >= 5 valid native episodes; 3 valid after 2 void episode(s) were excluded"]},
                       "openai/gpt-6-astra": {"campaign": "broken-astra", "episodes_valid": 5,
                           "evidence_problems": ["native runner changed"]}}}

    def _screen(self, spent, **options):
        from pipeline import screen
        launched, continued = [], {}

        def calibrate(b, s, r, m, n, w, rc, existing=None):
            if existing:
                continued[m] = list(existing)
                return existing[0], [*existing[1:], "fable-topup-2"], True
            launched.append(m)
            return f"new-{m}", [], True
        with tempfile.TemporaryDirectory() as tmp, \
                unittest.mock.patch("pipeline.release._calibrate_model", side_effect=calibrate), \
                unittest.mock.patch("pipeline.release.topup_spent", return_value=spent), \
                unittest.mock.patch("pipeline.artifacts.freeze", return_value="sha"), \
                unittest.mock.patch("pipeline.artifacts.bundle_lock"), \
                unittest.mock.patch("pipeline.screen.current", return_value=self.SHORT_PRIOR), \
                unittest.mock.patch("pipeline.screen.summarize", side_effect=lambda b, index, n, m: {
                    "artifact_sha256": "sha", "created_at": 0, "index": index}), \
                unittest.mock.patch("pipeline.screen._write"):
            record = screen.run(Path(tmp) / "b", native_root=Path(tmp), **options)
        return record, launched, continued

    def test_a_short_but_verified_campaign_is_topped_up_not_rerun(self):
        # Review: a campaign still short after its void top-ups was thrown away
        # and relaunched, re-running episodes that were already scored. Then
        # (re-review) it was kept short for ever, so the task could never ship.
        record, launched, continued = self._screen(spent=2)
        self.assertEqual(launched, ["gpt-6-astra"], "only the campaign whose evidence failed is replaced")
        self.assertEqual(list(continued.values()), [["short-fable", "fable-topup-1"]],
                         "the short campaign is continued with its scored parts, not relaunched")
        self.assertIn("short-fable", record["index"]["campaigns"])
        self.assertNotIn("new-claude-fable-5-1", record["index"]["campaigns"])
        self.assertEqual(record["index"]["topups"]["short-fable"], ["fable-topup-1", "fable-topup-2"])
        self.assertEqual(record["topped_up_models"], ["anthropic/claude-fable-5-1"])
        self.assertEqual(record["relaunched_incomplete"], [])

    def test_a_short_campaign_with_its_budget_spent_is_kept_not_relaunched(self):
        record, launched, continued = self._screen(spent=policy.MAX_TOPUP_ATTEMPTS)
        self.assertEqual((launched, continued), (["gpt-6-astra"], {}))
        self.assertIn("short-fable", record["index"]["campaigns"])
        self.assertEqual(record["topped_up_models"], [])

    def test_relaunching_an_incomplete_campaign_is_an_operator_decision_on_record(self):
        record, launched, continued = self._screen(spent=policy.MAX_TOPUP_ATTEMPTS,
                                                   relaunch_incomplete=True)
        self.assertEqual(sorted(launched), ["claude-fable-5-1", "gpt-6-astra"])
        self.assertEqual(continued, {})
        self.assertNotIn("short-fable", record["index"]["campaigns"])
        self.assertEqual(record["relaunched_incomplete"], ["anthropic/claude-fable-5-1"])
        self.assertEqual(record["discarded_campaigns"]["anthropic/claude-fable-5-1"],
                         ["short-fable", "fable-topup-1"])

    def test_a_screen_that_only_an_operator_can_complete_says_so(self):
        # Re-review: with the void budget spent, re-running `arena screen`
        # changes nothing, and nothing said which command would.
        from pipeline import screen
        prior = {"episodes_per_model": 5, "artifact_sha256": "sha", "index": {"topups": {}},
                 "per_model": {}}
        short_row = {"campaign": "short-fable", "evidence_problems": [
            "need >= 5 valid native episodes; 3 valid after 2 void episode(s) were excluded"]}
        summary = lambda b, index, n, m: {"artifact_sha256": "sha", "created_at": 0, "index": index,
                                          "shippable_problems": ["anthropic/claude-fable-5-1: need >= 5"],
                                          "per_model": {"anthropic/claude-fable-5-1": short_row}}
        with tempfile.TemporaryDirectory() as tmp, \
                unittest.mock.patch("pipeline.release._calibrate_model", return_value=("short-fable", [], True)), \
                unittest.mock.patch("pipeline.release.topup_spent", return_value=policy.MAX_TOPUP_ATTEMPTS), \
                unittest.mock.patch("pipeline.artifacts.freeze", return_value="sha"), \
                unittest.mock.patch("pipeline.artifacts.bundle_lock"), \
                unittest.mock.patch("pipeline.screen.current", return_value=prior), \
                unittest.mock.patch("pipeline.screen.summarize", side_effect=summary), \
                unittest.mock.patch("pipeline.screen._write"):
            record = screen.run(Path(tmp) / "b", native_root=Path(tmp))
        self.assertEqual(record["topup_exhausted"], ["anthropic/claude-fable-5-1"])
        self.assertIn("--relaunch-incomplete", record["remedy"])
        self.assertEqual(record["shippable_problems"][0], record["remedy"])
        self.assertIn("--relaunch-incomplete", screen.rescreen_command(Path("b"), record))
        self.assertNotIn("--relaunch-incomplete", screen.rescreen_command(Path("b"), None))

    def test_harden_and_category_batch_point_at_the_operator_step(self):
        import inspect
        import category_batch
        from pipeline import harden
        for fn in (harden.run_lineage, harden._judge_revision, harden._resume_point):
            self.assertIn("rescreen_command(", inspect.getsource(fn), fn.__name__)
        source = inspect.getsource(category_batch)
        self.assertIn('"screen-needs-operator" if stuck else "screen-incomplete"', source)
        # Unparked only when the current screen no longer says the budget is
        # spent -- never reset blindly, which would spin on every restart.
        self.assertIn('record.get("stage") == "screen-needs-operator"', source)
        self.assertIn('.get("topup_exhausted"):\n                    record["stage"] = "validated"', source)

    def test_the_flag_reaches_the_screen_from_the_cli(self):
        import inspect
        from pipeline import cli, screen
        self.assertIn("--relaunch-incomplete", inspect.getsource(cli.cmd_screen))
        self.assertIn("relaunch_incomplete=args.relaunch_incomplete", inspect.getsource(screen.main))

    def test_the_topup_continuation_requests_only_what_is_missing_within_budget(self):
        from pipeline import release
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for name, requested in (("primary", 5), ("t1", 2)):
                (root / name).mkdir()
                (root / name / "report.json").write_text(json.dumps({"summary": {"requested": requested}}))
            parts = [str(root / "primary"), str(root / "t1")]
            self.assertEqual(release.topup_spent(parts), 2, "the primary is not a top-up")
            (root / "t1" / "report.json").write_text("{")
            self.assertEqual(release.topup_spent(parts), policy.MAX_TOPUP_ATTEMPTS,
                             "an unreadable top-up counts as the whole budget")
            (root / "t1" / "report.json").write_text(json.dumps({"summary": {"requested": 2}}))
            runs = []
            campaign = lambda snapshot, output, **kw: runs.append(kw["rollouts"]) or {}
            short = (["need >= 5 valid native episodes; 3 valid after 2 void episode(s) were excluded"],
                     {"trials": [{}] * 3, "voids_excluded": 2, "part_voids": [2, 0]})
            full = ([], {"trials": [{}] * 5, "voids_excluded": 2, "part_voids": [2, 0, 0]})
            capacity = unittest.mock.MagicMock()
            with unittest.mock.patch("pipeline.benchmark.coder.native_runner", return_value=(campaign, capacity)), \
                    unittest.mock.patch("pipeline.release._merged_measurement", side_effect=[short, full]), \
                    unittest.mock.patch("pipeline.attribution.attribute", return_value={"counts": {}}), \
                    unittest.mock.patch("pipeline.attribution.problems", return_value=[]), \
                    unittest.mock.patch("pipeline.release.atomic_json"):
                primary, extra, ok = release._calibrate_model(root, root, root, "gpt-6-astra", 5, 5,
                                                              "screen-topup", existing=parts)
            self.assertEqual(runs, [2], "only the two missing episodes are requested")
            self.assertEqual((primary, extra[:1], len(extra), ok), (parts[0], parts[1:], 2, True))
            runs.clear()
            (root / "t1" / "report.json").write_text(json.dumps({"summary": {"requested": 5}}))
            with unittest.mock.patch("pipeline.benchmark.coder.native_runner", return_value=(campaign, capacity)), \
                    unittest.mock.patch("pipeline.release._merged_measurement", side_effect=[short]), \
                    unittest.mock.patch("pipeline.attribution.attribute", return_value={"counts": {}}), \
                    unittest.mock.patch("pipeline.attribution.problems", return_value=[]), \
                    unittest.mock.patch("pipeline.release.atomic_json"):
                primary, extra, ok = release._calibrate_model(root, root, root, "gpt-6-astra", 5, 5,
                                                              "screen-topup", existing=parts)
            self.assertEqual(runs, [], "a spent budget launches nothing")
            self.assertEqual((extra, ok), (parts[1:], False))

    def test_phases_run_uses_the_current_phases(self):
        from pipeline import phases
        ok = phases.PhaseResult("grade", ok=True)
        with tempfile.TemporaryDirectory() as tmp, \
                unittest.mock.patch("pipeline.phases.grade", return_value=ok) as grade, \
                unittest.mock.patch("pipeline.phases.calibrate",
                                    return_value=phases.PhaseResult("calibrate", ok=True)) as calibrate, \
                unittest.mock.patch("pipeline.phases.analyse", return_value={}):
            result = phases.run(Path(tmp), native_root=Path(tmp), review_model="gpt-6-astra")
        self.assertTrue(result["ok"])
        grade.assert_called_once()
        self.assertEqual(calibrate.call_args.args[0], [Path(tmp)])
        self.assertFalse(hasattr(phases, "author"))


class QualificationRequiresAShippableScreen(unittest.TestCase):
    """The ten-episode calibration of record is spent only once a screen earns it."""

    def test_an_unscreened_task_is_refused_before_anything_is_spent(self):
        from pipeline import release
        with tempfile.TemporaryDirectory() as tmp:
            bundle = _screen_bundle(Path(tmp))
            with unittest.mock.patch("pipeline.release._preflight") as preflight, \
                    self.assertRaisesRegex(ValueError, "does not admit"):
                release._qualify(bundle, list(policy.resolve_calibration_models()),
                                 "gpt-6-astra", "gpt-6-astra", Path(tmp) / "native")
            preflight.assert_not_called()

    def test_a_shippable_screen_lets_qualification_proceed(self):
        from pipeline import release
        with tempfile.TemporaryDirectory() as tmp:
            bundle = _screen_bundle(Path(tmp))
            with unittest.mock.patch("pipeline.screen._verified",
                                     return_value=([], {"meets_target": True})), \
                    self.assertRaisesRegex(ValueError, "identified author"):
                # Past the screen gate, the next refusal is the author check.
                release._qualify(bundle, list(policy.resolve_calibration_models()),
                                 "gpt-6-astra", "gpt-6-astra", Path(tmp) / "native")

    def test_a_clean_screen_that_missed_the_target_buys_no_calibration_of_record(self):
        # User, 2026-10-16: the 10 x 2 runs only on a screen that met the target.
        from pipeline import release, screen
        fresh = {"meets_target": False, "per_model": {"m": {"pass_at_1": 1.0}}}
        with tempfile.TemporaryDirectory() as tmp:
            bundle = _screen_bundle(Path(tmp))
            with unittest.mock.patch("pipeline.screen._verified", return_value=([], fresh)), \
                    unittest.mock.patch("pipeline.release._preflight") as preflight:
                with self.assertRaisesRegex(ValueError, "did not meet the target"):
                    release._qualify(bundle, list(policy.resolve_calibration_models()),
                                     "gpt-6-astra", "gpt-6-astra", Path(tmp) / "native")
                preflight.assert_not_called()
                with unittest.mock.patch.object(policy, "QUALIFY_REQUIRES_SCREEN_TARGET", False):
                    self.assertEqual(screen.qualify_problems(bundle), [])

    def test_an_unusable_calibration_of_record_does_not_skip_the_screen_gate(self):
        # Review finding: an index naming both models used to count as
        # "already calibrated" without checking its evidence, so a void-short
        # or evidence-less campaign skipped the gate and a fresh ten-episode
        # campaign started anyway. Reuse now needs the test `measure` applies.
        from pipeline import release
        from pipeline.artifacts import identity
        with tempfile.TemporaryDirectory() as tmp:
            bundle = _screen_bundle(Path(tmp))
            (bundle / "verification").mkdir()
            (bundle / "verification/native-calibrations.json").write_text(json.dumps(
                {"artifact_sha256": identity(bundle), "campaigns": ["p", "s"]}))
            models = list(policy.resolve_calibration_models())
            short = {"p": {"model": "anthropic/claude-fable-5-1"}, "s": {"model": "openai/gpt-6-astra"}}
            with unittest.mock.patch("pipeline.release.calibration_measurement",
                                     side_effect=lambda b, i, path, n: (["need >= 10 valid"], short[path])):
                self.assertFalse(release._calibrated(bundle, models, 10))
                with self.assertRaisesRegex(ValueError, "does not admit"):
                    release._qualify(bundle, models, "gpt-6-astra", "gpt-6-astra", Path(tmp) / "n")
            with unittest.mock.patch("pipeline.release.calibration_measurement",
                                     side_effect=lambda b, i, path, n: ([], short[path])):
                self.assertTrue(release._calibrated(bundle, models, 10))

    def test_a_receipt_cannot_lower_the_floor_or_drop_a_model(self):
        from pipeline import screen
        with tempfile.TemporaryDirectory() as tmp:
            bundle = _screen_bundle(Path(tmp))
            forged = {"artifact_sha256": "x", "episodes_per_model": 1,
                      "models": ["anthropic/claude-fable-5-1"], "index": {"campaigns": []}}
            with unittest.mock.patch("pipeline.screen.current", return_value=forged), \
                    unittest.mock.patch("pipeline.screen.summarize",
                                        return_value={"shippable_problems": []}) as summarize:
                screen.shippable_problems(bundle)
            _, _, episodes, models = summarize.call_args.args
            self.assertEqual(episodes, policy.SCREEN_EPISODES_PER_MODEL)
            self.assertEqual(sorted(models), sorted(policy.resolve_calibration_models()))

    def test_a_revision_during_qualification_awaits_a_screen(self):
        # Review finding: revise() makes a new, unscreened version, so looping
        # back into _qualify raised and erased the revision record.
        from pipeline import release
        with tempfile.TemporaryDirectory() as tmp:
            bundle = _screen_bundle(Path(tmp))
            (bundle / "verification").mkdir()
            blocked = {"release_ready": False, "status": "blocked", "errors": ["x"]}
            with unittest.mock.patch("pipeline.release._qualify", return_value=blocked) as q, \
                    unittest.mock.patch("pipeline.repair.feedback", return_value=["tests/checks.json c1: x"]), \
                    unittest.mock.patch("pipeline.checkpoint.admit_repair", return_value=(True, "", 0)), \
                    unittest.mock.patch("pipeline.checkpoint.repair_budget", return_value=1), \
                    unittest.mock.patch("pipeline.repair.revise", return_value={"revision": 1}):
                result = release.qualify(bundle, list(policy.resolve_calibration_models()),
                                         "gpt-6-astra", "gpt-6-astra", Path(tmp) / "n",
                                         repair_attempts=1)
            self.assertEqual(q.call_count, 1)
            self.assertEqual(result["status"], "awaiting-screen")
            self.assertEqual(result["qualification_revisions"], [{"revision": 1}])

    def test_no_current_screen_is_a_refusal_not_a_pass(self):
        from pipeline import screen
        with tempfile.TemporaryDirectory() as tmp:
            problems = screen.shippable_problems(_screen_bundle(Path(tmp)))
        self.assertTrue(problems)
        self.assertIn("arena screen", problems[0])


class TheScreenReportsWhatArenaAsked(unittest.TestCase):
    """pass@1, pass@4 and mean reward per task per model, every zero classified."""

    PRIMARY, SECONDARY = "anthropic/claude-fable-5-1", "openai/gpt-6-astra"

    def _summarize(self, primary_eps, secondary_eps, n_checks=8):
        from pipeline import screen
        measured = {"p": _measured(self.PRIMARY, primary_eps),
                    "s": _measured(self.SECONDARY, secondary_eps)}
        with tempfile.TemporaryDirectory() as tmp:
            bundle = _screen_bundle(Path(tmp), n_checks)
            with unittest.mock.patch("pipeline.release.calibration_measurement",
                                     side_effect=lambda b, i, path, n: ([], measured[path])), \
                    unittest.mock.patch("pipeline.attribution.all_fail_problems", return_value=[]), \
                    unittest.mock.patch("pipeline.attribution.trajectory_hacks", return_value=[]):
                return screen.summarize(bundle, {"campaigns": ["p", "s"], "topups": {}},
                                        5, list(policy.resolve_calibration_models()))

    @staticmethod
    def _eps(fails: dict[int, list[int]], n_checks=8, episodes=5):
        """episode index -> the checks it failed."""
        return [{f"c{i}": i not in fails.get(e, []) for i in range(n_checks)}
                for e in range(episodes)]

    def test_rates_are_per_model_and_use_the_unbiased_estimator(self):
        record = self._summarize(self._eps({0: [1], 1: [1], 2: [1]}), self._eps({}))
        fable = record["per_model"][self.PRIMARY]
        self.assertEqual(fable["pass_at_1"], 0.4)
        self.assertAlmostEqual(fable["pass_at_4"], metrics.pass_at_k(5, 2, 4))
        self.assertAlmostEqual(fable["mean_reward"], (2 * 1.0 + 3 * 0.5) / 5)
        self.assertEqual(record["per_model"][self.SECONDARY]["pass_at_1"], 1.0)
        self.assertEqual(fable["attribution"], {"pass": 2, "capability": 3})
        self.assertFalse(record["meets_target"], "the target is BOTH models below 0.5")
        # Missing the target blocks nothing: a clean screen is ready for the
        # calibration of record whatever it scored; the gap is reported.
        self.assertTrue(record["shippable"], record["shippable_problems"])
        self.assertTrue(record["target_gap"])
        self.assertFalse(any("pass@1" in p for p in record["shippable_problems"]))

    def test_both_models_below_the_target_is_shippable(self):
        hard = self._eps({0: [1], 1: [1], 2: [2], 3: [2]})
        record = self._summarize(hard, hard)
        self.assertTrue(record["meets_target"])
        self.assertTrue(record["shippable"], record["shippable_problems"])
        self.assertEqual(record["outlook"]["verdict"], "meets-target")

    def test_a_short_screen_is_not_shippable_whatever_it_scored(self):
        record = self._summarize(self._eps({e: [1] for e in range(3)}, episodes=3),
                                 self._eps({e: [1] for e in range(5)}))
        self.assertFalse(record["shippable"])
        self.assertTrue(any("3 valid episodes of 5" in p for p in record["shippable_problems"]))
        self.assertEqual(record["outlook"]["verdict"], "not-assessable")

    def test_checks_that_measured_nothing_are_named(self):
        record = self._summarize(self._eps({0: [1]}), self._eps({1: [1]}))
        self.assertIn("01-task/c0", record["census"]["never_failed"])
        self.assertNotIn("01-task/c1", record["census"]["never_failed"])

    def test_a_live_edge_on_every_model_above_target_is_a_strong_candidate(self):
        with unittest.mock.patch("pipeline.screen._trap_material", return_value={
                "usable_corrections": 3, "corrections_used": 1, "unused_corrections": 2,
                "authored_traps_left": None, "authored_bytes_left": 1000,
                "objectives": 8, "objective_room": 4}):
            record = self._summarize(self._eps({0: [1], 1: [2]}), self._eps({0: [3]}))
        self.assertEqual(record["outlook"]["verdict"], "strong-candidate",
                         record["outlook"]["reasons"])

    def test_a_task_nobody_failed_is_at_best_weak(self):
        with unittest.mock.patch("pipeline.screen._trap_material", return_value={
                "usable_corrections": 3, "corrections_used": 1, "unused_corrections": 2,
                "authored_traps_left": None, "authored_bytes_left": 1000,
                "objectives": 8, "objective_room": 4}):
            record = self._summarize(self._eps({}), self._eps({}))
        self.assertEqual(record["outlook"]["verdict"], "weak-candidate")

    def test_an_f3_task_with_no_authored_room_or_unused_correction_is_poor(self):
        with unittest.mock.patch("pipeline.screen._trap_material", return_value={
                "usable_corrections": 2, "corrections_used": 2, "unused_corrections": 0,
                "authored_traps_left": 0, "authored_bytes_left": 1000,
                "objectives": 8, "objective_room": 4}), \
                unittest.mock.patch("pipeline.screen._level", return_value="F3"):
            record = self._summarize(self._eps({0: [1]}), self._eps({0: [1]}))
        self.assertEqual(record["outlook"]["verdict"], "poor-candidate")

    def test_a_pending_hack_flag_caveats_the_outlook_but_never_ships(self):
        with unittest.mock.patch("pipeline.attribution.trajectory_hacks", return_value=[
                {"trial": "t1", "step": "01-task", "kind": "tamper", "evidence": "turn 8: exit_code"}]):
            from pipeline import screen
            measured = {"p": _measured(self.PRIMARY, self._eps({})),
                        "s": _measured(self.SECONDARY, self._eps({}))}
            with tempfile.TemporaryDirectory() as tmp:
                bundle = _screen_bundle(Path(tmp))
                with unittest.mock.patch("pipeline.release.calibration_measurement",
                                         side_effect=lambda b, i, path, n: ([], measured[path])), \
                        unittest.mock.patch("pipeline.attribution.all_fail_problems", return_value=[]):
                    record = screen.summarize(bundle, {"campaigns": ["p", "s"]}, 5,
                                              list(policy.resolve_calibration_models()))
        self.assertFalse(record["shippable"])
        self.assertNotEqual(record["outlook"]["verdict"], "not-assessable")
        self.assertTrue(any("awaiting adjudication" in r for r in record["outlook"]["reasons"]))

    def test_arena_screen_skips_a_task_whose_gate_chain_is_not_green(self):
        # Review finding: `arena screen <tree>` spent ten episodes on blocked
        # tasks. A grader that fails its own gates is not measured.
        from pipeline import screen
        with tempfile.TemporaryDirectory() as tmp:
            bundle = _screen_bundle(Path(tmp))
            blocked = {"verdict": "blocked", "results": [
                {"gate": "grader.reference", "blockers": [{"code": "objective-count"}]}]}
            with unittest.mock.patch("pipeline.run.run_bundle", return_value=blocked), \
                    unittest.mock.patch("pipeline.screen.run_many", return_value=[]) as run_many, \
                    unittest.mock.patch("pipeline.screen.write_report"), \
                    unittest.mock.patch("pipeline.screen.print_table"):
                screen.main([str(bundle), "-o", str(Path(tmp) / "r.json")])
            self.assertEqual(run_many.call_args.args[0], [])

    def test_the_report_carries_every_task_and_both_models(self):
        from pipeline import screen
        record = self._summarize(self._eps({0: [1]}), self._eps({}))
        doc = screen.report([record])
        text = screen.markdown(doc)
        self.assertIn("claude-fable-5-1 p@1", text)
        self.assertIn("gpt-6-astra p@4", text)
        self.assertIn("a-001-screened", text)
        self.assertEqual(doc["measurement"]["episodes_per_model"], 5)  # the width these records ran at
        self.assertEqual(screen.report([])["measurement"]["episodes_per_model"],
                         policy.SCREEN_EPISODES_PER_MODEL)
        self.assertEqual(doc["measurement"]["effort"], "high")


class PhaseContract(unittest.TestCase):
    """The five phases, and the one that must never run automatically."""

    def test_the_five_phases_are_named_and_ordered(self):
        from pipeline import phases
        self.assertEqual(phases.PHASES,
                         ("select", "author", "grade", "calibrate", "harden"))

    def test_hardening_is_excluded_from_automatic_runs_by_construction(self):
        from pipeline import phases
        self.assertNotIn("harden", phases.AUTOMATIC)
        # Not merely absent from a list -- calling it raises, so a future caller
        # wiring hardening into a batch has to delete a statement saying not to.
        with self.assertRaises(RuntimeError):
            phases.harden()

    def test_an_unverified_stage_is_not_a_rejection(self):
        from pipeline import phases
        result = phases.PhaseResult("grade", ok=False, unverified=True,
                                    findings=["provider unavailable"])
        self.assertTrue(result.unverified)
        self.assertIn("unverified", result.as_dict())

    def test_select_reports_unfilled_slots_rather_than_backfilling(self):
        from pipeline import phases
        with tempfile.TemporaryDirectory() as tmp:
            missing = Path(tmp) / "nope.json"
            result = phases.select(3, classified=missing)
        self.assertFalse(result.ok)
        self.assertTrue(result.unverified,
                        "a missing input is about our ability to check, not the candidate")

    def test_calibrate_and_qualify_require_an_explicit_native_root(self):
        import inspect
        from pipeline import phases
        self.assertTrue(inspect.signature(phases.calibrate).parameters["native_root"].default
                        is inspect.Parameter.empty)
        params = inspect.signature(phases.qualify).parameters
        for name in ("native_root", "review_model"):
            self.assertTrue(params[name].default is inspect.Parameter.empty,
                            f"{name} must be explicit; a None default reached "
                            "qualify() and failed at runtime")

    def test_qualification_is_not_an_automatic_phase(self):
        from pipeline import phases
        self.assertNotIn("qualify", phases.AUTOMATIC)


class CalibrationConfiguration(unittest.TestCase):
    """Models, effort and limits are part of the measurement, not runtime detail."""

    def test_the_two_spec_models_route_to_their_providers(self):
        from pipeline.benchmark.harbor import resolve_model
        primary, secondary = policy.resolve_calibration_models()
        self.assertEqual(resolve_model(primary), "anthropic/claude-fable-5-1")
        self.assertEqual(resolve_model(secondary), "openai/gpt-6-astra")

    def test_retired_models_are_refused(self):
        self.assertTrue(policy.calibration_problems(["gpt-5.6-sol"]))
        self.assertTrue(policy.calibration_problems(["claude-opus-5"]))
        self.assertEqual(policy.calibration_problems(
            list(policy.resolve_calibration_models())), [])

    def test_effort_is_high_and_explicit(self):
        self.assertEqual(policy.SPEC_CALIBRATION_EFFORT, "high")

    def test_calibration_runs_without_turn_or_time_limits(self):
        self.assertTrue(policy.SPEC_NO_LIMITS)
        source = (Path(__file__).resolve().parents[1] / "release.py").read_text()
        self.assertIn("no_limits=policy.SPEC_NO_LIMITS", source,
                      "a capped run writes no deliverable and is recorded VOID")

    def test_no_retired_model_remains_a_default(self):
        root = Path(__file__).resolve().parents[1]
        for name in ("cli.py", "release.py", "orchestrate.py", "harden.py"):
            body = (root / name).read_text()
            self.assertNotIn('"gpt-5.6-sol"', body, f"{name} still defaults to a retired model")


class TopUpReplacesInfrastructureLossOnly(unittest.TestCase):
    """Re-run episodes lost to infrastructure; never re-roll a result.

    A void measured nothing, so a campaign that loses two episodes to a flaky
    container otherwise reports a rate over eight -- or fails the ten-episode
    floor and discards the eight that worked. The danger is the mirror image:
    a retry that replaces a *scored* episode makes every difficulty figure a
    lower bound on how many times we tried.
    """

    def test_the_budget_is_five_per_task_per_model(self):
        self.assertEqual(policy.MAX_TOPUP_ATTEMPTS, 5)

    def test_only_voids_are_replaceable(self):
        self.assertEqual(policy.TOPUP_REPLACES, ("void",))
        for verdict in ("capability", "contract", "pass"):
            self.assertIn(verdict, policy.TOPUP_NEVER_REPLACES)

    def test_a_topup_that_loses_a_pass_is_refused(self):
        issues = policy.topup_problems({"pass": 3, "capability": 5, "void": 2},
                                       {"pass": 2, "capability": 8, "void": 0})
        self.assertTrue(issues)
        self.assertIn("shopping for a result", issues[0])

    def test_a_topup_that_loses_a_capability_failure_is_refused(self):
        issues = policy.topup_problems({"capability": 7, "void": 3},
                                       {"capability": 5, "void": 0})
        self.assertTrue(issues)

    def test_a_clean_topup_is_allowed(self):
        self.assertEqual(
            policy.topup_problems({"pass": 3, "capability": 5, "void": 2},
                                  {"pass": 3, "capability": 7, "void": 0}), [])

    def test_a_worsening_fault_is_not_transient(self):
        issues = policy.topup_problems({"pass": 3, "void": 1},
                                       {"pass": 3, "void": 4})
        self.assertTrue(any("not transient" in i for i in issues))

    def test_the_calibration_path_retries_and_records_the_budget(self):
        source = (Path(__file__).resolve().parents[1] / "release.py").read_text()
        self.assertIn("policy.MAX_TOPUP_ATTEMPTS", source)
        self.assertIn("policy.topup_problems", source)
        self.assertIn("arena-pipeline/topup/1", source,
                      "every top-up must leave a receipt saying what it spent")

    def test_voids_still_leave_the_denominator_after_a_topup(self):
        # Topping up does not make a void count; it replaces it. The rate is
        # always over valid episodes.
        report = {"model": "m", "step_names": ["01-task"],
                  "rollouts": rollouts([1.0] * 10)}
        report["rollouts"].append({"id": "x", "episode": 11, "step": "01-task",
                                   "reward": None, "stop_reason": "max_tokens",
                                   "tool_calls": 2, "zero_class": "void",
                                   "error": "", "checks": {}})
        out = metrics.task_metrics(report)
        self.assertEqual(out["episodes_valid"], 10)
        self.assertEqual(out["episodes_void"], 1)


class EveryPolicyConstantIsRead(unittest.TestCase):
    """A threshold that nothing reads is decoration.

    Twice in one session a mechanism was built, documented and unit-tested, and
    was inert because no call site consulted it:

      - `presolve` existed as a module and a CLI command and ran in neither
        build path, so the difficulty screen never fired.
      - `policy.MAX_REPAIR_PASSES = 2` existed while `orchestrate.GATE_REPAIRS`
        defaulted to 0 from its own env var, so the repair budget was zero and
        easy drafts were discarded instead of redesigned.

    Both were caught by running the pipeline, not by reading it. This test
    closes the class: every public threshold in `policy.py` must be referenced
    somewhere outside `policy.py` itself.
    """

    #: Names that are intentionally declarative -- documentation of Arena's
    #: taxonomy, or reporting vocabulary -- rather than behavioural switches.
    DECLARATIVE = {
        "SPEC_REPORTED_K",          # reported via metrics.task_metrics' literals
        "RECORD_SOURCE_TIER",
        "AUTHOR_TARGET_PASS_AT_1",  # a target for authors, not a gate
        "EPISODE_VERDICTS",
        "CAPABILITY_VERDICTS",
        "EXCLUDED_FROM_DENOMINATOR",
        "ALL_FAIL_PROOF_OBLIGATIONS",
        "SPEC_PROBES",
        "MANDATORY_PROBES",
        "DIAGNOSTIC_PROBES",
        "EXPECT_ZERO",
        "MIN_SEMANTIC_WEIGHT_SHARE",
        "SPEC_REFERENCE_REWARD",
        "SPEC_UNTOUCHED_REWARD",
        "TOPUP_REPLACES",
        "REPAIR_FEEDBACK_EXCLUDES",
        "MODEL_SUBSTITUTIONS",
        "TRACE_DERIVED_TRAP_FLOOR",
        "BANDS",
        "CORE_LO", "CORE_HI", "FLOOR_LO",
        # Consumed by policy.py's own exported helpers, which external call
        # sites do use: resolve_calibration_models(), calibration_problems(),
        # topup_problems(). Reading them directly would bypass the substitution
        # and deviation bookkeeping.
        "SPEC_PRIMARY_MODEL",
        "SPEC_SECONDARY_MODEL",
        "RETIRED_CALIBRATION_MODELS",
        "TOPUP_NEVER_REPLACES",
    }

    def test_no_policy_constant_is_orphaned(self):
        import re
        from pipeline import policy

        root = Path(__file__).resolve().parents[1]
        sources = {p: p.read_text() for p in root.rglob("*.py")
                   if p.name != "policy.py" and "tests" not in p.parts}
        extra = root.parent / "category_batch.py"
        if extra.is_file():
            sources[extra] = extra.read_text()
        body = "\n".join(sources.values())

        names = [n for n in dir(policy)
                 if n.isupper() and not n.startswith("_")]
        orphans = [n for n in names
                   if n not in self.DECLARATIVE
                   and not re.search(rf"\b{re.escape(n)}\b", body)]
        self.assertEqual(orphans, [],
                         f"policy constants nothing reads: {orphans}. Either wire "
                         "them into a call site or mark them DECLARATIVE with a "
                         "reason -- an unread threshold is decoration, and this "
                         "is exactly how presolve and the repair budget shipped "
                         "inert")

    def test_the_known_inert_mechanisms_are_now_wired(self):
        from pipeline import orchestrate, policy

        # The repair budget reaches the build loop.
        self.assertEqual(orchestrate.GATE_REPAIRS, policy.MAX_REPAIR_PASSES)
        root = Path(__file__).resolve().parents[1]
        # The calibration screen is reachable from the build, after the batch.
        source = (root / "orchestrate.py").read_text()
        self.assertIn("calibrate_batch(report, rows", source)
        self.assertIn("screen.run_many(", source)
        # The shippable verdict actually gates the calibration of record.
        self.assertIn("qualify_problems(bundle, models)", (root / "release.py").read_text())
        # Every hardening round ends in a screen.
        self.assertIn("screen.run(revision", (root / "harden.py").read_text())


class DifficultyGuidanceReachesTheModelActuallyUsed(unittest.TestCase):
    """The guidance must live in the prompt the ACTIVE designer sends.

    Measured: the difficulty target, the worked example and the operator
    evidence were all written into `designer._brief()` -- the one-shot
    designer. Production runs with ARENA_AGENT_DESIGN=1, which uses
    `agent_designer.SYSTEM` and imports only CATEGORY_GUIDANCE from that
    module. Three runs were launched before anyone checked whether the text
    reached the model. None of it did.

    Same failure as presolve, the repair budget, the retired-model guard and
    MAX_UNREACHABLE_CHECKS: edited in one place, read in another.
    """

    MARKERS = ("NOT UNPASSABLE", "expert practitioner given ONLY",
               "ZERO times", "search query and called it a task",
               "WORKED EXAMPLE", "COUPLED")

    def test_the_agent_designer_system_prompt_carries_it(self):
        from pipeline.author import agent_designer
        for marker in self.MARKERS:
            self.assertIn(marker, agent_designer.SYSTEM,
                          f"{marker!r} missing from the prompt production uses")

    def test_the_retired_band_target_is_gone_from_both(self):
        import inspect
        from pipeline.author import agent_designer, designer
        stale = "Aim for 4-6 checks measured in the 30-70% band"
        self.assertNotIn(stale, inspect.getsource(designer))
        self.assertNotIn(stale, agent_designer.SYSTEM)

    def test_derivation_operators_are_named_so_they_can_be_used(self):
        from pipeline.author import agent_designer
        for op in ("date_add", "days_between", "parse_date"):
            self.assertIn(op, agent_designer.SYSTEM,
                          "an operator the designer has never used must be "
                          "named in the prompt if we expect it to be used")


class ScreeningRunsConcurrently(unittest.TestCase):
    """A batch screen one task at a time is the difference between an hour and a day.

    Qualification used to run as a plain `for` loop in `orchestrate.main`; the
    batch screen that replaced it in the build is pooled from the start.
    """

    def test_the_screen_loop_is_pooled(self):
        import inspect
        from pipeline import screen
        source = inspect.getsource(screen.run_many)
        self.assertIn("ThreadPoolExecutor(max_workers=", source)
        self.assertIn("as_completed", source)
        # Both models of one task run at once.
        self.assertIn("ThreadPoolExecutor(max_workers=len(pending) + len(topping))", inspect.getsource(screen.run))

    def test_worker_count_is_configurable(self):
        import inspect
        from pipeline import orchestrate
        self.assertIn("--screen-workers", inspect.getsource(orchestrate.main))

    def test_native_capacity_still_bounds_episodes_globally(self):
        # The pool decides how many TASKS are in flight; it must not decide how
        # many native episodes run, or concurrency would oversubscribe Docker.
        from pipeline.benchmark.capacity import NATIVE_CAPACITY
        self.assertGreaterEqual(NATIVE_CAPACITY.limit, 1)
        import inspect
        from pipeline import release
        self.assertIn("NATIVE_CAPACITY.reserve", inspect.getsource(release))


class AnIncoherentZeroIsOursNotTheModels(unittest.TestCase):
    """reward 0 while every scored check passed is a defect, never difficulty.

    Measured on a_f2_engineering-thesis-writing-002: step 02-revision scored
    0.0 with its only objective passing (target=12, actual=12), because
    `reward.toml` aggregates a weighted mean over DIMENSIONS while grading runs
    PER STEP -- that step had no `execution` check, so the dimension scored
    nothing and collapsed the mean. `exported_grade` returned 1.0 for the same
    step, so two grading paths disagreed on identical outcomes.

    It surfaced as the single non-1.00 screen in eighteen and was nearly read
    as the one task a frontier model found hard.
    """

    def _rollout(self, reward, checks):
        from pipeline.calibrate.agent import Rollout
        r = Rollout(id="x", step="s") if hasattr(Rollout, "__dataclass_fields__") else None
        return r

    def test_zero_with_all_checks_passing_and_no_cause_is_void(self):
        from pipeline.calibrate.run import classify_zero
        from types import SimpleNamespace
        rec = SimpleNamespace(error="", tool_calls=5, stop_reason="end_turn",
                              reward=0.0, grade={},
                              checks={"a": "passed", "b": "passed"})
        self.assertEqual(classify_zero(rec), "void")

    def test_a_contract_violation_is_a_real_result_not_a_void(self):
        """Measured: Fable 5.1 answered step 2 correctly (earned 14 of 14) and
        scored 0 for writing one undeclared file. That is a fact about the
        model's restraint. Erasing it as a void would hide real signal; my
        first version of this guard did exactly that."""
        from pipeline.calibrate.run import classify_zero
        from types import SimpleNamespace
        rec = SimpleNamespace(error="", tool_calls=5, stop_reason="end_turn",
                              reward=0.0,
                              grade={"contract_errors": ["output/x.json: undeclared"]},
                              checks={"a": "passed"})
        self.assertEqual(classify_zero(rec), "model_failure")

    def test_zero_with_a_real_failure_is_still_a_model_failure(self):
        from pipeline.calibrate.run import classify_zero
        from types import SimpleNamespace
        rec = SimpleNamespace(error="", tool_calls=5, stop_reason="end_turn",
                              reward=0.0, grade={},
                              checks={"a": "passed", "b": "failed"})
        self.assertEqual(classify_zero(rec), "model_failure")

    def test_gated_out_checks_do_not_make_a_zero_coherent(self):
        from pipeline.calibrate.run import classify_zero
        from types import SimpleNamespace
        rec = SimpleNamespace(error="", tool_calls=5, stop_reason="end_turn",
                              reward=0.0, grade={},
                              checks={"a": "passed", "b": "gated_out"})
        self.assertEqual(classify_zero(rec), "void")


class TrapBudgetIsNotAMovingGoalpost(unittest.TestCase):
    """`usable_corrections` must survive a rebuild and must never be inferred.

    `build.build()` regenerated traps.json without the field and
    `gates/difficulty.py` defaulted the absent value to `len(traps)`. The
    expectation therefore tracked its own input: adding a trap to satisfy the
    budget RAISED the budget. Measured on brand-consulting-002, one added trap
    moved the target from 11 to 12. Real counts were 3, 1 and 0 against the
    11, 7 and 7 the gate inferred, and four independent authors hit it.
    """

    def test_expected_traps_grows_with_the_correction_count(self):
        from pipeline.config import expected_traps
        # If usable were len(traps), this monotonicity would make the gate
        # unsatisfiable by adding traps.
        self.assertLess(expected_traps(10, 1, 8), expected_traps(10, 12, 8))

    def test_the_gate_no_longer_defaults_to_the_trap_count(self):
        source = (Path(__file__).resolve().parents[1] / "gates/difficulty.py").read_text()
        self.assertNotIn('raw_doc.get("usable_corrections", len(traps))', source)
        self.assertIn('raw_doc.get("usable_corrections")', source)

    def test_an_unknown_count_warns_rather_than_inventing_one(self):
        source = (Path(__file__).resolve().parents[1] / "gates/difficulty.py").read_text()
        self.assertIn("unknown-correction-count", source)

    def test_the_builder_preserves_the_field(self):
        import json, tempfile
        from pathlib import Path as P
        source = (P(__file__).resolve().parents[1] / "author/build.py").read_text()
        self.assertIn("usable_corrections", source,
                      "a rebuild must not silently drop the real count")
        self.assertIn("retained", source)


class EverySharedSessionCarriesADisposition(unittest.TestCase):
    """Arena: "100% of shared traces dispositioned". Silence is not one.

    The batch report derives `converted` from the delivered tree, so the only
    way it reaches 100% is if every remaining session carries a reason. These
    reasons must be *derived* -- a hand-written exclusion map drifts from what
    the funnel did, and nothing would catch it.
    """

    def setUp(self):
        self.artifacts = Path(tempfile.mkdtemp())
        (self.artifacts / "index.json").write_text(json.dumps({"rows": [
            # one-turn seed: fails the K2 floor outright
            {"session_id": "s-kill", "seed_index": 0, "n_turns": 1,
             "corrections": 0, "deliv_paths": 0, "deliv_bytes": 0,
             "deliv_share": 0.0, "categories": []},
            # viable but never classified
            {"session_id": "s-deep", "seed_index": 0, "n_turns": 9,
             "corrections": 3, "deliv_paths": 8, "deliv_bytes": 90_000,
             "deliv_share": 0.9, "categories": ["planning_brainstorm"]},
            {"session_id": "s-reject", "seed_index": 0, "n_turns": 9,
             "corrections": 3, "deliv_paths": 8, "deliv_bytes": 90_000,
             "deliv_share": 0.9, "categories": ["planning_brainstorm"]},
            {"session_id": "s-ok", "seed_index": 0, "n_turns": 9,
             "corrections": 3, "deliv_paths": 8, "deliv_bytes": 90_000,
             "deliv_share": 0.9, "categories": ["planning_brainstorm"]},
        ]}))
        (self.artifacts / "classified.json").write_text(json.dumps({"rows": [
            {"session_id": "s-reject", "seed_key": "s-reject::0",
             "classification": {"survives": False,
                                "truth_source": "requires_execution",
                                "why_not": "only a running build settles it"}},
            {"session_id": "s-ok", "seed_key": "s-ok::0",
             "classification": {"survives": True, "truth_source": "register_reconciliation"}},
        ]}))
        self.sessions = ["s-kill", "s-deep", "s-reject", "s-ok", "s-absent"]

    def codes(self):
        from pipeline import accounting
        return {s: r["code"] for s, r in
                accounting.exclusions(self.sessions, self.artifacts).items()}

    def test_every_shared_session_gets_a_reason(self):
        from pipeline import accounting
        derived = accounting.reasons(self.sessions, self.artifacts)
        self.assertEqual(set(derived), set(self.sessions))
        for session, reason in derived.items():
            self.assertTrue(reason.strip(), f"{session} carries an empty reason")

    def test_a_structural_floor_is_not_reported_as_a_budget_limit(self):
        self.assertEqual(self.codes()["s-kill"], "kill_filter")

    def test_never_looked_at_is_not_reported_as_unusable(self):
        """The distinction the report exists to make.

        237 of this corpus's 500 sessions were never classified. Calling that
        "no checkable truth source" would report our budget as a property of
        Arena's traces.
        """
        from pipeline import accounting
        codes = self.codes()
        self.assertEqual(codes["s-deep"], "below_classification_depth")
        self.assertIn(codes["s-deep"], accounting.OURS_NOT_THEIRS)
        self.assertNotIn(codes["s-kill"], accounting.OURS_NOT_THEIRS)
        self.assertNotIn(codes["s-reject"], accounting.OURS_NOT_THEIRS)

    def test_the_classifiers_own_reason_is_carried_through(self):
        from pipeline import accounting
        reason = accounting.reasons(self.sessions, self.artifacts)["s-reject"]
        self.assertIn("requires_execution", reason)
        self.assertIn("only a running build settles it", reason)

    def test_qualified_but_unbuilt_is_ours_not_theirs(self):
        """A session that qualified and shipped nothing is a capacity story."""
        from pipeline import accounting
        codes = self.codes()
        self.assertEqual(codes["s-ok"], "qualified_not_built")
        self.assertIn(codes["s-ok"], accounting.OURS_NOT_THEIRS)

    def test_a_session_with_no_seed_at_all_still_gets_a_reason(self):
        self.assertEqual(self.codes()["s-absent"], "no_seed_extracted")

    def test_accounting_closes_the_report_blocker(self):
        """The derived map must actually satisfy `trace_accounting`."""
        from pipeline import accounting, deliverable
        derived = accounting.reasons(self.sessions, self.artifacts)
        report = deliverable.trace_accounting(self.sessions, {}, derived)
        self.assertEqual(report["undispositioned"], 0)
        self.assertEqual(report["dispositioned_share"], 1.0)
        self.assertTrue(report["ok"], report["problems"])

    def test_capacity_share_is_reported_not_hidden(self):
        from pipeline import accounting
        summary = accounting.summary(self.sessions, self.artifacts)
        self.assertEqual(summary["sessions"], len(self.sessions))
        self.assertEqual(summary["capacity_limited"], 2)  # s-deep, s-ok
        self.assertAlmostEqual(summary["capacity_limited_share"], 0.4)

    def test_an_unscorable_index_row_is_not_reported_as_excluded(self):
        """"Could not check" is never "nothing wrong" -- standing rule."""
        from pipeline import accounting, deliverable
        (self.artifacts / "index.json").write_text(json.dumps({"rows": [
            {"session_id": "s-broken", "seed_index": 0},  # missing every field
        ]}))
        derived = accounting.exclusions(["s-broken"], self.artifacts)["s-broken"]
        self.assertEqual(derived["code"], accounting.UNASSESSED)
        self.assertIn("NOT ASSESSED", derived["reason"])
        # ...and it reaches the report as undispositioned, not as a reason.
        report = deliverable.trace_accounting(
            ["s-broken"], {}, accounting.reasons(["s-broken"], self.artifacts))
        self.assertEqual(report["undispositioned"], 1)
        self.assertFalse(report["ok"])

    def test_a_seed_the_classifier_failed_on_is_unassessed(self):
        from pipeline import accounting
        self.assertEqual(accounting._classified_reason(
            [{"classification": {"truth_source": "none"}},
             {"classification": {"error": "timeout"}}])[0], accounting.UNASSESSED)


class MeasurementBreadthPredictsDifficulty(unittest.TestCase):
    """The sixth difficulty hypothesis, and the first checked against data.

    Five predecessors were built on and falsified. This one separates the
    screened corpus exactly -- it flags the three tasks that scored below 1.00
    and none of the nine that scored 1.00 -- so these tests pin the property
    that made it work, not the wording of the brief that described it.
    """

    def check(self, cid, assertion="set_equals", field="words", op="lt",
              file="trail.jsonl", weight=20):
        return {"id": cid, "kind": "objective", "weight": weight,
                "assertion": assertion, "step": "01-task",
                "target": {"op": "pluck", "field": "heading",
                           "of": {"op": "filter",
                                  "of": {"op": "rows", "file": file},
                                  "where": {"field": field, op: 120}}}}

    def test_a_word_count_threshold_is_a_root_check(self):
        from pipeline import breadth
        roots = breadth.root_checks([self.check("c_short")],
                                    sizes={"trail.jsonl": 40})
        self.assertEqual([r["id"] for r in roots], ["c_short"])
        self.assertTrue(roots[0]["counts_itself"])

    def test_a_threshold_over_a_stated_number_is_not(self):
        """Reading a printed figure is not measuring anything.

        This is what nine 1.00 tasks did: a census over table rows, however
        subtle the membership rule.
        """
        from pipeline import breadth
        stated = self.check("c_budget", field="amount")
        self.assertEqual(breadth.root_checks([stated], sizes={"trail.jsonl": 40}), [])

    def test_breadth_is_the_lever_not_the_shape(self):
        """The right construct over eight rows is not a hard task."""
        from pipeline import breadth
        narrow = breadth.root_checks([self.check("c_short")],
                                     sizes={"trail.jsonl": 8})
        self.assertEqual(narrow[0]["broad_enough"], False)
        found = breadth.report([self.check("c_short")])
        self.assertIsNone(found["root_checks"][0]["broad_enough"],
                          "unmeasured breadth must read unknown, never True")

    def test_a_pairwise_judgement_over_many_records_is_a_root_check(self):
        """The construct behind the hardest task in the batch (0.18).

        The model returned an empty set where the reference held 19, while
        getting the bounded parts of the same submission exactly right.
        """
        from pipeline import breadth
        disputed = {"id": "c_disputed", "kind": "objective", "weight": 20,
                    "assertion": "set_equals", "step": "01-task",
                    "target": {"op": "pluck", "field": "item",
                               "of": {"op": "filter",
                                      "of": {"op": "rows", "file": "review.jsonl"},
                                      "where": {"field": "agrees", "eq": False}}}}
        roots = breadth.root_checks([disputed],
                                    pairwise={"review.jsonl": {"agrees"}},
                                    sizes={"review.jsonl": 100})
        self.assertEqual([r["id"] for r in roots], ["c_disputed"])
        self.assertTrue(roots[0]["pairwise"])
        self.assertTrue(roots[0]["broad_enough"])

    def test_a_tolerance_is_reported_as_a_defect(self):
        """A tolerance wide enough to absorb a mis-measured item measures nothing."""
        from pipeline import breadth
        loose = dict(self.check("c_deficit", assertion="equals"), tolerance=0.1)
        found = breadth.problems([self.check("c_short"), loose],
                                 bundle=None)
        self.assertTrue(any("tolerance" in p for p in found), found)

    def test_a_task_with_no_root_check_is_flagged(self):
        from pipeline import breadth
        stated = self.check("c_budget", field="amount")
        found = breadth.problems([stated])
        self.assertTrue(found)
        self.assertIn("count for itself", found[0])

    def test_a_root_with_no_cascade_is_weaker_than_it_looks(self):
        """One error taking down one check is not what produced 0.18."""
        from pipeline import breadth
        root = self.check("c_short", weight=10)
        other = {"id": "c_elsewhere", "kind": "objective", "weight": 90,
                 "assertion": "equals", "step": "01-task",
                 "target": {"op": "count", "of": {"op": "rows", "file": "other.jsonl"}}}
        found = breadth.problems([root, other], bundle=None)
        self.assertTrue(any("weight at risk" in p for p in found), found)

    def band_legal(self, *extra):
        """A check set the band gate accepts, so band noise cannot mask the rest."""
        return [dict(self.check("c_root", weight=40), band="core"),
                *(dict(c, band="core") for c in extra),
                *(dict(self.check(f"c_core{i}", field="amount", weight=10),
                       band="core") for i in range(3 - len(extra))),
                dict(self.check("c_stretch", field="amount", weight=10),
                     band="stretch")]

    def test_the_screen_never_claims_a_task_is_hard(self):
        """It is one-sided: it can only let an easy task through to measurement."""
        from pipeline import breadth
        clean = self.band_legal()
        self.assertEqual(breadth.problems(clean, bundle=None), [])
        # ...and saying nothing is not saying it is hard.
        self.assertNotIn("hard", json.dumps(breadth.report(clean)))

    def test_band_noise_does_not_mask_a_missing_root_check(self):
        """A band-legal task with no root check must still be flagged."""
        from pipeline import breadth
        legal = [dict(self.check(f"c{i}", field="amount"), band="core")
                 for i in range(4)] + [
                 dict(self.check("c_s", field="amount"), band="stretch")]
        self.assertTrue(breadth.bands(legal)["in_band"])
        found = breadth.problems(legal)
        self.assertTrue(any("count for itself" in p for p in found), found)

    def test_the_static_screen_is_advisory_and_never_blocks_a_build(self):
        """Superseded by the two-model calibration data (the seventh lever).

        The breadth screen rested on 24 tasks at one cold episode each. Re-run
        over every check with >=4 scored episodes on both models, size predicts
        nothing, and blocking on it refused premise-trap tasks for the wrong
        reason. It stays a free report (check_difficulty.py); the batch
        calibration screen measures difficulty.
        """
        source = Path("pipeline/orchestrate.py").read_text()
        self.assertNotIn("breadth.problems(", source)
        # No difficulty screen of any kind runs inside the build any more; the
        # batch calibration screen measures difficulty after the batch exists.
        self.assertNotIn("presolve_stage", source)
        self.assertTrue(Path("check_difficulty.py").read_text().count("breadth"))

    def test_a_full_band_is_reported_as_the_blocker_it_is(self):
        """A root check cannot be ADDED to a full set -- the gate refuses it.

        `quality.py` caps a task at twelve objectives (core stays at six), so
        the construct is paid for by removing transcription checks. Three bundles in this batch reached
        room 0 before anyone noticed.
        """
        from pipeline import breadth
        # v2 (user, 2026-10-02): limits widened for dense tasks; read from policy.
        core, floor, stretch = (breadth.BANDS[b][1] for b in ("core", "floor", "stretch"))
        full = ([dict(self.check(f"c_core{i}", field="amount"), band="core")
                 for i in range(core)]
                + [dict(self.check(f"c_floor{i}", field="amount"), band="floor")
                   for i in range(floor)]
                + [dict(self.check(f"c_str{i}", field="amount"), band="stretch")
                   for i in range(stretch)])
        found = breadth.bands(full)
        self.assertEqual(found["room_total"], 0)
        self.assertTrue(found["in_band"])
        self.assertTrue(any("paid for by removing" in p
                            for p in breadth.problems(full)), "must say what to do")

    def test_an_out_of_band_task_is_refused_whatever_its_difficulty(self):
        from pipeline import breadth
        over = [dict(self.check(f"c{i}", field="amount"), band="core")
                for i in range(8)]
        found = breadth.bands(over)
        self.assertFalse(found["in_band"])
        self.assertTrue(any("gate" in p for p in breadth.problems(over)))

    def test_the_hardest_tasks_sit_at_the_core_minimum(self):
        """Band limits and the difficulty finding agree, they do not trade off.

        Guards against a future edit "relaxing" the cap to make room for more
        checks, which is the opposite of what the measurement says.
        """
        # v2 (user, 2026-10-02: "as many traps and checks as required"): the
        # core cap is widened and bands are advisory; the core MINIMUM stays 4.
        from pipeline import breadth, policy
        self.assertEqual(breadth.BANDS["core"][0], 4)
        self.assertEqual(breadth.BANDS, policy.BAND_LIMITS)
        from pipeline.author import quality
        self.assertIs(breadth.BANDS, quality.BAND_LIMITS,
                      "breadth.BANDS must be the gate's own limits, not a copy")
        from pipeline.advisory import classify
        self.assertIsNotNone(classify("task: require 4-24 core objectives across all steps; got {}"))


class PlausibleWrongMustActuallyBeWrong(unittest.TestCase):
    """A probe that mutated nothing proves nothing -- standing rule.

    Four bundles reached the object case, mutated nothing, graded a
    byte-identical copy of the reference, scored 1.0, and were reported as
    confirmed reward hacking. The batch criterion is "0 cases", so an inert
    probe blocks delivery while saying nothing about the grader.
    """

    def test_a_numeric_leaf_inside_an_object_is_shifted(self):
        from pipeline.author.probes import _shift_numeric_leaf
        answer = {"guide": {"thin_sections": ["a", "b"], "sections": 42}}
        moved = _shift_numeric_leaf(answer)
        self.assertIsNotNone(moved, "the measurement construct's answer shape")
        where, before, after = moved
        self.assertEqual((before, after), (42, 43))
        self.assertEqual(answer["guide"]["sections"], 43)

    def test_a_boolean_is_not_treated_as_a_number(self):
        """`isinstance(True, int)` is True, and `True + 1` is 2 -- a type
        error, not a plausible wrong answer."""
        from pipeline.author.probes import _shift_numeric_leaf
        answer = {"conforms": True, "count": 7}
        where, before, after = _shift_numeric_leaf(answer)
        self.assertEqual((before, after), (7, 8))
        self.assertIs(answer["conforms"], True)

    def test_a_numeric_leaf_inside_a_nested_list_is_found(self):
        from pipeline.author.probes import _shift_numeric_leaf
        answer = {"docs": [{"name": "a", "words": 60}]}
        self.assertIsNotNone(_shift_numeric_leaf(answer))
        self.assertEqual(answer["docs"][0]["words"], 61)

    def test_an_answer_with_no_number_anywhere_returns_none(self):
        """Honest silence: the caller records that nothing was mutated rather
        than reporting a byte-identical copy as a caught wrong answer."""
        from pipeline.author.probes import _shift_numeric_leaf
        self.assertIsNone(_shift_numeric_leaf({"a": "x", "b": [{"c": "y"}]}))

    def test_the_object_fallback_runs_after_scalar_and_list(self):
        """Order matters: an off-by-one on a scored scalar is the sharper
        probe, and dropping a set member is the next sharpest."""
        source = Path("pipeline/author/probes.py").read_text()
        body = source[source.index("def _plausible_wrong"):
                      source.index("def _shift_numeric_leaf")]
        self.assertLess(body.index("target + 1"), body.index("value[:-1]"))
        self.assertLess(body.index("value[:-1]"), body.index("_shift_numeric_leaf"))


class ControlSuiteRunsBeforeCalibration(unittest.TestCase):
    """`assurance.controls` had exactly one reader, and it came too late.

    It ran only in `release.py`, which is reached after native calibration at
    ~$39.52 a task. So a bundle could pass `./arena gate` GREEN while shipping a
    counterexample that patches a field to the reference's own value, and source
    cases naming checks their corrected answer never moves. One shipped that way
    in this batch and was caught by hand, not by the pipeline.
    """

    def test_the_gate_chain_runs_the_control_suite(self):
        from pipeline.run import PRE_CALIBRATION
        names = [g.name for g in PRE_CALIBRATION]
        self.assertIn("quality.controls", names)

    def test_it_runs_before_anything_that_costs_money(self):
        """Controls are local and free; calibration is not."""
        from pipeline.run import PRE_CALIBRATION
        names = [g.name for g in PRE_CALIBRATION]
        self.assertIn("quality.controls", names,
                      "a free check belongs in the free stage")

    def test_a_control_suite_that_cannot_run_blocks(self):
        """'Could not check' is never 'nothing wrong' -- standing rule."""
        from pipeline.gates import findings
        from pipeline.gates.base import Severity

        class Ctx:
            task_dir = Path("/nonexistent-bundle-for-this-test")

        found, evidence = findings._controls(Ctx())
        self.assertTrue(found)
        self.assertEqual(found[0].severity, Severity.BLOCKER)
        self.assertIn("could not check", found[0].message.lower())

    def test_a_control_failure_is_a_blocker_not_a_warning(self):
        from pipeline.gates import findings
        from pipeline.gates.base import Severity

        class Ctx:
            task_dir = Path(".")

        with unittest.mock.patch("pipeline.assurance.controls",
                                 return_value={"ok": False,
                                               "errors": ["CE3 patches a field to "
                                                          "the reference's own value"]}):
            found, evidence = findings._controls(Ctx())
        self.assertEqual(len(found), 1)
        self.assertEqual(found[0].severity, Severity.BLOCKER)
        self.assertFalse(evidence["ok"])

    def test_a_clean_control_suite_reports_its_scope(self):
        from pipeline.gates import findings

        class Ctx:
            task_dir = Path(".")

        with unittest.mock.patch("pipeline.assurance.controls",
                                 return_value={"ok": True, "errors": []}):
            found, evidence = findings._controls(Ctx())
        self.assertEqual(found, [])
        self.assertTrue(evidence["ok"])
        self.assertIn("source cases", evidence["scope"])


class NormalisationKeepsItsPromise(unittest.TestCase):
    """Instructions promise equality ignores leading Markdown markers, PLURAL.

    A single strip broke that the moment two stacked: `## 5. PHYSICAL` folded to
    `5. physical` while `5. PHYSICAL` folded to `physical`, so a model copying
    the whole heading line scored 0.13 on a correct answer. Punishing a correct
    answer written differently is a broken task, not a hard one.
    """

    def folds_same(self, *variants):
        from pipeline.author.checks import normalise
        folded = {normalise(v) for v in variants}
        self.assertEqual(len(folded), 1,
                         f"variants folded apart: {[(v, normalise(v)) for v in variants]}")

    def test_a_stacked_heading_and_number_fold_together(self):
        self.folds_same("5. PHYSICAL + ONLINE", "## 5. PHYSICAL + ONLINE",
                        "### 5. physical + online")

    def test_a_quote_before_a_heading_folds(self):
        self.folds_same("1. Baz", "> ## 1. Baz", "> 1. Baz")

    def test_a_bullet_before_a_number_folds(self):
        self.folds_same("2. Bar", "- 2. Bar", "* 2. Bar")

    def test_markers_inside_the_text_are_left_alone(self):
        """Only LEADING markers are markup; a number mid-sentence is content."""
        from pipeline.author.checks import normalise
        self.assertEqual(normalise("Some text 1. not leading"),
                         "some text 1. not leading")

    def test_a_plain_heading_still_folds_to_its_text(self):
        from pipeline.author.checks import normalise
        self.assertEqual(normalise("## Plain Heading"), "plain heading")

    def test_numeric_folding_is_unaffected(self):
        """The kw-002 fix must survive: "1960" and 1960 still compare equal."""
        from pipeline.author.checks import normalise
        self.assertEqual(normalise("1960"), normalise(1960))
        self.assertEqual(normalise("1,960"), 1960)


class HarborReceiptMustSerialise(unittest.TestCase):
    """The receipt referred to itself, so it could never be written.

    `record = attempt` aliased an element of `attempts`, then
    `record["attempts"] = attempts` put the list back on the record. `json.dump`
    raised "Circular reference detected" AFTER the validator had already run --
    so the work was done, the receipt was never written, and the Reviewable
    criterion read 0 of 42 with Harbor installed and working the whole time.
    """

    def test_a_result_record_is_json_serialisable(self):
        attempts = [{"status": "pass", "spelling": "check", "output": "ok"}]
        record = dict(attempts[0])
        record["attempts"] = attempts
        record["harbor_bin"] = "/path/to/harbor"
        json.dumps(record)          # must not raise

    def test_run_copies_the_attempt_rather_than_aliasing_it(self):
        source = Path("pipeline/benchmark/tasks_check.py").read_text()
        body = source[source.index("def run("):source.index("def retained(")]
        self.assertIn("record = dict(attempt)", body,
                      "aliasing the attempt makes the receipt self-referential")
        self.assertNotIn("record = attempt\n", body)

    def test_the_binary_path_is_stringified(self):
        """A Path is not JSON-serialisable either."""
        source = Path("pipeline/benchmark/tasks_check.py").read_text()
        self.assertIn('record["harbor_bin"] = str(exe)', source)

    def test_an_unrun_check_is_not_a_pass(self):
        """"Could not check" is never "nothing wrong" -- standing rule."""
        from pipeline.benchmark import tasks_check
        with tempfile.TemporaryDirectory() as tmp:
            self.assertTrue(tasks_check.problems(Path(tmp)),
                            "a task with no receipt must report a problem")


class TasksCheckIsAnAgentTrialNotALint(unittest.TestCase):
    """`harbor check` in 0.22.0 runs an LLM agent against a rubric.

    Two settings were wrong on the assumption it was a static validator, and
    both surfaced as task defects rather than harness limits:
      - a 300s timeout, which the batch's SMALLEST bundle exceeded
      - the default `claude-code` evaluator, which passes the trial instruction
        as an environment variable and then fails `exec /usr/bin/bash:
        argument list too long` on a package with a 75KB checks.json
    """

    def test_the_timeout_allows_for_an_agent_trial(self):
        from pipeline.benchmark import tasks_check
        self.assertGreaterEqual(tasks_check.TIMEOUT_SECONDS, 600,
                                "a 4KB-instruction task exceeded 280s unfinished")

    def test_the_evaluator_agent_is_overridable(self):
        """A package too large for the env-var agent must still be checkable."""
        import importlib
        import os
        from pipeline.benchmark import tasks_check
        with unittest.mock.patch.dict(os.environ,
                                      {"ARENA_TASKS_CHECK_AGENT": "swe-agent"}):
            importlib.reload(tasks_check)
            self.assertEqual(tasks_check.AGENT, "swe-agent")
            source = Path("pipeline/benchmark/tasks_check.py").read_text()
            self.assertIn('argv += ["--agent", AGENT]', source)
        importlib.reload(tasks_check)

    def test_a_timeout_is_not_recorded_as_a_pass(self):
        """"Could not check" is never "nothing wrong" -- standing rule."""
        source = Path("pipeline/benchmark/tasks_check.py").read_text()
        self.assertIn('"status": "timeout"', source)
        self.assertNotIn('"status": "pass"  # timeout', source)


class AnUnmeasurableRateIsNoneNotAnError(unittest.TestCase):
    """pass@k over zero complete episodes is unknown, and must say so.

    In this batch a model returned 10 voids; `pass_at_k` gave None, `round`
    raised `TypeError: NoneType doesn't define __round__`, and the handler was
    around the WHOLE bundle -- so the other model's ten completed episodes were
    discarded with it. Seven bundles produced no data that way.
    """

    def test_pass_at_k_is_none_when_there_are_no_episodes(self):
        self.assertIsNone(metrics.pass_at_k(0, 0, 1))

    def test_pass_at_k_is_none_when_k_exceeds_the_sample(self):
        """Asking pass@4 of two episodes is not answerable."""
        self.assertIsNone(metrics.pass_at_k(2, 1, 4))

    def test_a_failing_model_does_not_discard_the_other(self):
        source = Path(
            "/Users/pratyushmohanty/.claude/jobs/bffe81c7/tmp/calibrate_batch.py")
        if not source.is_file():
            self.skipTest("calibration harness not present in this checkout")
        body = source.read_text()
        body = body[body.index("def one_bundle("):body.index("def main(")]
        self.assertIn("for model in policy.resolve_calibration_models():", body)
        # the try must sit INSIDE the per-model loop
        self.assertLess(body.index("for model in"), body.index("try:"),
                        "the handler must wrap one model, not the whole bundle")

    def test_a_void_run_never_reports_a_rate(self):
        """A void leaves every denominator -- it is not a zero."""
        rewards = {"1": None, "2": None}
        complete = [r for r in rewards.values() if r is not None]
        self.assertEqual(complete, [])
        self.assertIsNone(metrics.pass_at_k(len(complete), 0, 1))


class HarborChecksTheTaskNotOurRecords(unittest.TestCase):
    """Calibration artefacts crowded the task out of Harbor's own prompt.

    Harbor embeds the package's complete file tree in the evaluator's prompt,
    delivered as a single environment string. Calibration writes a directory per
    episode under `verification/`, so one fully calibrated bundle reached 32,068
    files and a 3.9MB tree against a 128KB limit. The exec failed
    `[Errno 7] Argument list too long`, which reads as a broken task rather than
    as our own measurement records crowding it out.
    """

    def test_verification_is_excluded_from_the_checked_package(self):
        from pipeline.benchmark import tasks_check
        self.assertIn("verification", tasks_check.NOT_THE_TASK)
        self.assertIn("jobs", tasks_check.NOT_THE_TASK)

    def test_staging_drops_our_records_and_keeps_the_task(self):
        from pipeline.benchmark import tasks_check
        with tempfile.TemporaryDirectory() as tmp:
            src = Path(tmp) / "bundle"
            (src / "tests").mkdir(parents=True)
            (src / "verification" / "campaigns" / "x" / "episode-001").mkdir(parents=True)
            (src / "task.toml").write_text("[task]\nname='arena/x'\n")
            (src / "tests" / "checks.json").write_text('{"checks": []}')
            (src / "verification" / "campaigns" / "x" / "episode-001" / "r.json").write_text("{}")
            dest, scratch = tasks_check.staged(src)
            try:
                kept = {p.relative_to(dest).as_posix()
                        for p in dest.rglob("*") if p.is_file()}
                self.assertIn("task.toml", kept)
                self.assertIn("tests/checks.json", kept)
                self.assertFalse([k for k in kept if k.startswith("verification/")],
                                 "our measurement records must not reach Harbor")
            finally:
                import shutil
                shutil.rmtree(scratch, ignore_errors=True)

    def test_the_receipt_records_what_was_checked(self):
        """A receipt that does not say it checked a subset would mislead."""
        source = Path("pipeline/benchmark/tasks_check.py").read_text()
        self.assertIn('record["checked"]', source)


class AVoidMustSayWhyItIsAVoid(unittest.TestCase):
    """A provider error with no code still has to classify itself.

    `rate_limit_exceeded` is infra loss and the episode is re-run; a real model
    limit is a result and must not be. When the provider sends no code the two
    arrive at the table looking identical, which is the exact shape of the rule
    that "could not check" must never render as "nothing wrong". The descriptor
    is built from the envelope's FIELD NAMES, never its values, so it carries no
    prompt material.
    """

    def token(self, event):
        from pipeline.calibrate.agent_openai import _error_token
        return _error_token(event)

    def test_a_structured_code_is_preferred_and_returned_verbatim(self):
        self.assertEqual(
            self.token({"type": "error", "error": {"code": "rate_limit_exceeded"}}),
            "rate_limit_exceeded")
        self.assertEqual(
            self.token({"type": "error", "error": {"code": "context_length_exceeded"}}),
            "context_length_exceeded")

    def test_a_codeless_error_names_its_fields_rather_than_going_silent(self):
        # The shape that produced 112 unclassifiable voids in the batch32 run.
        self.assertEqual(
            self.token({"type": "error", "error": {"message": "something failed"}}),
            "no-code(message)")

    def test_the_descriptor_never_carries_the_providers_message(self):
        secret = "the user's private prompt text"
        token = self.token({"type": "error", "error": {"message": secret, "param": None}})
        self.assertNotIn(secret, token)
        self.assertNotIn("private", token)
        self.assertEqual(token, "no-code(message,param)")

    def test_an_error_that_is_not_an_object_still_classifies(self):
        # `error` is not a dict, so the envelope itself is described instead.
        self.assertEqual(self.token({"type": "error", "error": "boom"}),
                         "no-code(error,type)")

    def test_a_void_is_never_described_as_an_empty_string(self):
        # An empty token renders as a bare "provider error" with nothing to act
        # on, which is what made the batch32 voids unreadable.
        for event in ({"type": "error", "error": {}},
                      {"type": "error", "error": {"message": "x"}},
                      {"type": "error"}):
            self.assertNotEqual(self.token(event), "", msg=f"silent on {event!r}")


class ARateMustSayWhichAgentProducedIt(unittest.TestCase):
    """A screening rate and a calibration rate are not comparable.

    `pipeline/calibrate` hands the model three file tools; the shipped package
    declares Terminus-2, which drives a shell. Both are legitimate, but a
    `pass@1` that does not record which one ran invites exactly the mistake this
    batch made: six a-554 episodes refused the task as impossible with
    "read/write-only tools", and that was read as an infeasible task rather than
    as a property of the screen. A shell agent would have run one `awk`.
    """

    def surface(self, tools, declared=None, unreadable=False):
        import json
        import tempfile
        from pipeline.tool_surface import reconcile
        root = Path(tempfile.mkdtemp())
        (root / "environment").mkdir()
        if unreadable:
            (root / "environment/tools.json").write_text("{not json")
        elif declared is not None:
            (root / "environment/tools.json").write_text(json.dumps(
                {"harness": {"agent": "terminus-2"},
                 "tools": [{"name": n} for n in declared]}))
        return reconcile(root, tools)

    def test_the_screening_surface_never_matches_the_shipped_one(self):
        from pipeline.calibrate.agent import TOOLS
        surface = self.surface(TOOLS, declared=["terminus_2_keystrokes"])
        self.assertFalse(surface["matches"])
        self.assertIn("SCREENING", surface["warning"])
        self.assertEqual(surface["measured"], ["list_files", "read_file", "write_file"])
        self.assertEqual(surface["declared"], ["terminus_2_keystrokes"])

    def test_identical_surfaces_agree_and_carry_no_warning(self):
        surface = self.surface([{"name": "terminus_2_keystrokes"}],
                               declared=["terminus_2_keystrokes"])
        self.assertTrue(surface["matches"])
        self.assertNotIn("warning", surface)

    def test_a_missing_schema_is_not_agreement(self):
        # "could not check" must never render as "nothing wrong".
        surface = self.surface([{"name": "terminus_2_keystrokes"}], declared=None)
        self.assertFalse(surface["matches"])
        self.assertIn("missing", surface["warning"])

    def test_an_unreadable_schema_is_not_agreement(self):
        surface = self.surface([{"name": "terminus_2_keystrokes"}], unreadable=True)
        self.assertFalse(surface["matches"])
        self.assertIn("unreadable", surface["warning"])

    def test_a_run_with_no_tools_never_claims_to_match(self):
        self.assertFalse(self.surface([], declared=[])["matches"])

    def test_order_does_not_decide_agreement(self):
        surface = self.surface([{"name": "b"}, {"name": "a"}], declared=["a", "b"])
        self.assertTrue(surface["matches"])

    def test_the_campaign_records_the_surface_on_every_rollout(self):
        """Wired, not merely available -- a field nothing writes is decoration."""
        source = Path("pipeline/calibrate/run.py").read_text()
        self.assertIn('"tool_surface": surface', source)
        self.assertIn("from ..tool_surface import reconcile", source)


class NoTaskMayShipWithAReadableAnswer(unittest.TestCase):
    """§0 is not a threshold to stay under.

    `answer_lookup` used to block only when reading the fixture scored the WHOLE
    task. A bundle whose three readable answers were worth 30% scored 0.3 and
    passed -- while those three checks measured nothing, because an agent that
    greps them is indistinguishable from one that reasoned. Every readable field
    now blocks.

    That is only usable because the probe stopped reporting coincidences: a-442's
    answers were 3 and 2, "found" in `Platform1.java` because it contains
    `Platform2`, `rect[2]` and `rect[3]`. Acting on that would have meant editing
    an audited source file to satisfy noise.
    """

    def test_a_small_integer_match_is_not_evidence(self):
        from pipeline.author.probes import _distinctive
        for value in (0, 1, 2, 3, 42, 999, -7, "2", "ok", True, False, None):
            self.assertFalse(_distinctive(value), msg=f"{value!r} must not count")

    def test_a_value_that_cannot_be_coincidence_is_evidence(self):
        from pipeline.author.probes import _distinctive
        for value in (0.977255, 198.14, 1000, 6879, "1250000", "withdraw", "live"):
            self.assertTrue(_distinctive(value), msg=f"{value!r} must count")

    def test_every_readable_answer_blocks_not_just_a_whole_task(self):
        source = Path("pipeline/gates/difficulty.py").read_text()
        self.assertIn("answer-readable-in-fixture", source)
        self.assertIn('readable = sorted((probe.get("readable_from_fixture") or {}))', source)
        # It must be a BLOCKER; a warning here is how the leaks survived.
        window = source[source.index("answer-readable-in-fixture") - 200:
                        source.index("answer-readable-in-fixture") + 80]
        self.assertIn("Severity.BLOCKER", window)

    def test_a_coincidental_match_is_recorded_rather_than_discarded(self):
        # Dropping it silently is the same sin as reporting it: a reviewer must
        # be able to see the probe considered the value and rejected it.
        source = Path("pipeline/author/probes.py").read_text()
        self.assertIn('"coincidental": coincidental', source)


class AnAnswerPrintedInTheInstructionIsALeak(unittest.TestCase):
    """The probes search the fixture and are blind to the instruction.

    Publishing the rules a grader applies -- which fairness requires -- means
    writing sentences full of the answer's own vocabulary, and a computed figure
    can ride in unnoticed. Nothing looked at all before this.
    """

    def run_check(self, solution, instruction, second=None):
        from pipeline.gates.integrity import _answers_spoken_in_the_instruction
        spec = {"solution": solution, "instruction": instruction}
        if second is not None:
            spec["second_step"] = {"instruction": second}
        ctx = types.SimpleNamespace(spec=spec)
        findings, evidence = _answers_spoken_in_the_instruction(ctx)
        return findings, evidence["answer_values_in_instruction"]

    def test_a_computed_decimal_in_the_instruction_is_reported(self):
        findings, spoken = self.run_check(
            {"ratio": 0.977255}, "Report the ratio. The observed ratio is 0.977255.")
        self.assertEqual(spoken, ["0.977255"])
        self.assertTrue(findings)

    def test_a_small_count_is_not_reported(self):
        # "3" appears in any prose; flagging it would bury the real hits.
        _, spoken = self.run_check({"count": 3}, "Report the count of 3 kinds of defect.")
        self.assertEqual(spoken, [])

    def test_the_second_step_instruction_is_searched_too(self):
        # Step 2 has its own text and is never concatenated with step 1's, so a
        # leak there would otherwise go unseen.
        _, spoken = self.run_check({"total": 42900}, "Step one.", second="The total is 42900.")
        self.assertEqual(spoken, ["42900"])

    def test_an_answer_absent_from_the_instruction_reports_nothing(self):
        findings, spoken = self.run_check({"total": 42900}, "Work out the total yourself.")
        self.assertEqual((findings, spoken), ([], []))

    def test_it_reports_rather_than_blocks(self):
        # A published threshold legitimately appears in both places; only a
        # reader can separate that from a leak, so this must not hard-fail.
        findings, _ = self.run_check({"floor": 1000.5}, "The published floor is 1000.5.")
        self.assertTrue(findings)
        self.assertEqual(findings[0].severity.name, "WARN")


class AStepMayWithholdItsOwnEvidence(unittest.TestCase):
    """Step 2's reveal must not sit in step 1's workspace.

    Every bundle shipped one fixture copied whole at every step, so a-293's
    step 2 announced that "the build log you were given was not the last run"
    while the later run's log had been on disk since step 1 began. Neither that
    bundle nor a-206 could be repaired by editing them: there was nowhere else
    to put the file. `env.step_isolation` even advised "unlock it with the step
    that needs it", for an unlock that did not exist.
    """

    def spec(self, paths=("sources/later.json",)):
        return {"step_files": {"02-revision": list(paths)}}

    def test_a_later_steps_file_is_withheld_from_the_first_step(self):
        from pipeline.author.step_files import withheld_from
        order = ["01-task", "02-revision"]
        self.assertEqual(withheld_from(self.spec(), "01-task", order), ["sources/later.json"])

    def test_the_releasing_step_sees_it(self):
        from pipeline.author.step_files import withheld_from
        order = ["01-task", "02-revision"]
        self.assertEqual(withheld_from(self.spec(), "02-revision", order), [])

    def test_materialising_omits_only_the_withheld_path(self):
        from pipeline.author.step_files import materialise
        root = Path(tempfile.mkdtemp())
        fixture = root / "files"
        (fixture / "sources").mkdir(parents=True)
        (fixture / "keep.txt").write_text("step one")
        (fixture / "sources" / "later.json").write_text("step two reveal")
        omitted = materialise(fixture, root / "ws", ["sources/later.json"])
        present = sorted(p.relative_to(root / "ws").as_posix()
                         for p in (root / "ws").rglob("*") if p.is_file())
        self.assertEqual(omitted, ["sources/later.json"])
        self.assertEqual(present, ["keep.txt"])

    def test_the_grader_still_sees_the_whole_fixture(self):
        # Withholding is a promise about VISIBILITY, not about grading: a check
        # over a withheld document must keep working, so nothing may be moved
        # out of environment/files/.
        source = Path("pipeline/author/step_files.py").read_text()
        self.assertIn("ignore=ignore", source)
        self.assertNotIn("shutil.move", source)

    def test_a_traversal_path_is_refused(self):
        # `lstrip("./")` strips any leading "." or "/" character, so it turns
        # "../evil" into "evil"; a traversal check placed after it never fires.
        from pipeline.author.step_files import declared
        for bad in ("../evil", "/etc/passwd", "a/../../b", ""):
            self.assertEqual(declared({"step_files": {"s": [bad]}}), {},
                             msg=f"{bad!r} must be refused")
        self.assertEqual(declared({"step_files": {"s": ["./ok.json"]}}), {"s": ["ok.json"]})

    def test_both_transports_understand_withholding(self):
        """A step must present the same workspace whichever model measures it.

        Passing the parameter to only one transport broke every GPT-6 Astra
        episode, because the OpenAI rollout did not accept the keyword.
        """
        import inspect
        from pipeline.calibrate import agent, agent_openai
        for module in (agent, agent_openai):
            self.assertIn("withhold", inspect.signature(module.rollout).parameters,
                          msg=f"{module.__name__}.rollout must accept withhold")

    def test_a_task_that_withholds_nothing_is_untouched(self):
        # The kwarg is only passed when the set is non-empty, so a rollout
        # implementation that never heard of the feature keeps working.
        source = Path("pipeline/calibrate/run.py").read_text()
        self.assertIn("if hidden:", source)
        self.assertIn('kwargs["withhold"] = hidden', source)

    def test_the_isolation_gate_stops_flagging_a_withheld_file(self):
        source = Path("pipeline/gates/findings.py").read_text()
        self.assertIn("withheld_from_first_step", source)
        self.assertIn("if rel in withheld:", source)


class AStaticGapMayNotSuppressTheExecutedControls(unittest.TestCase):
    """A control that does not run cannot prove the check it exists to prove.

    `source_controls.run` used to return as soon as the STATIC coverage check
    found a gap, so one undeclared semantic check silenced every counterfactual
    in the bundle -- and the gate reported only the static complaint, so nothing
    said the controls had not executed.

    Measured on a-439: `SC2` had never once run in that bundle's history. It
    executed only after an unrelated fix cleared the pre-check, and then turned
    out to rest on a premise a later design change had invalidated. Bundles
    behind a static gap were reporting their checks proven while the proof never
    ran.
    """

    def test_run_does_not_return_before_the_per_case_loop(self):
        source = Path("pipeline/source_controls.py").read_text()
        body = source[source.index("def run("):]
        head = body[:body.index("for index, case in enumerate(cases)")]
        self.assertNotIn("return {\"errors\": errors, \"results\": results}", head,
                         msg="run() returns before executing any control; a static "
                             "declaration gap must not suppress execution")

    def test_the_static_findings_are_still_reported(self):
        # Removing the short-circuit must not drop the static check itself --
        # it still blocks, it just no longer decides whether the rest runs.
        source = Path("pipeline/source_controls.py").read_text()
        body = source[source.index("def run("):]
        self.assertIn("errors = problems(spec, bundle)", body)

    def test_a_per_case_failure_is_recorded_not_raised(self):
        # Each case is individually guarded, which is what makes running them
        # all safe even when the bundle is in a partly-broken state.
        source = Path("pipeline/source_controls.py").read_text()
        body = source[source.index("for index, case in enumerate(cases)"):]
        self.assertIn("except (ValueError, KeyError, TypeError, OSError, RuntimeError)", body)
        self.assertIn("source control failed", body)
