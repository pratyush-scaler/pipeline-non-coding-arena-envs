import copy
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from pipeline.artifacts import identity
from pipeline.author.build import build
from pipeline.calibrate.run import _miss_shape, campaign
from pipeline.harden import acceptance, hardenable
from pipeline.measurement import band, observation, profile
from pipeline.source_controls import problems, run
from pipeline.tests.test_production import synthetic_bundle
from pipeline.diagnose import recount, audit


def measured(rates, models=("one", "two"), pass_at_1=None):
    """Aligned unit-test episodes; all non-passes are clean capability failures."""
    checks = {f"c{i}": {"kind": "objective", "passed": n, "failed": 10 - n}
              for i, n in enumerate(rates)}
    return {"ok": True, "errors": [], "by_model": {m: {
        "protocol": "native", "effort": "xhigh", "limits": {},
        "pass_at_1": min(rates) / 10 if pass_at_1 is None else pass_at_1,
        "capability_difficulty": {
            "capability_adjusted_pass_at_1": min(rates) / 10 if pass_at_1 is None else pass_at_1},
        "episodes_valid": 10,
        "steps": {"step": profile(checks)}} for m in models}}


class MeasurementPolicy(unittest.TestCase):
    def test_calibration_reports_guard_counts_without_demanding_padding(self):
        from types import SimpleNamespace
        from pipeline.gates.integrity import _bands
        for guard_count in (1, 8):
            checks = {f'core-{i}': {'kind': 'objective', 'passed': 5, 'failed': 5}
                      for i in range(4)}
            checks['stretch'] = {'kind': 'objective', 'passed': 1, 'failed': 9}
            checks.update({f'guard-{i}': {'kind': 'guardrail', 'passed': 10, 'failed': 0}
                           for i in range(guard_count)})
            findings, evidence = _bands(SimpleNamespace(extras={'calibration': {'checks': checks}}))
            self.assertEqual(findings, [])
            self.assertEqual(evidence['guardrail_ratio'], guard_count / 5)
            self.assertEqual(evidence['counts'], {'core': 4, 'stretch': 1})

    def test_all_boundaries_and_transition_are_consistent(self):
        from pipeline.orchestrate import check_bands
        for rate, expected in ((0, "stretch"), (.29, "stretch"), (.3, "core"),
                               (.7, "core"), (.71, "transition"), (.89, "transition"),
                               (.9, "floor"), (1, "floor"), (None, "unreachable")):
            self.assertEqual(band(rate), expected)
            n = 0 if rate is None else round(rate * 100)
            rec = {"passed": n, "failed": 0 if rate is None else 100 - n}
            self.assertEqual(check_bands({"checks": {"c": rec}})[expected][0][0], "c")

    def test_transition_checks_are_allowed_without_inflating_core(self):
        from types import SimpleNamespace
        from pipeline.gates.integrity import _bands
        checks = {f"c{i}": {"kind": "objective", "passed": n, "failed": 100 - n}
                  for i, n in enumerate((30, 50, 60, 70, 10, 71, 80, 89, 90))}
        result = profile(checks)
        self.assertEqual(result["status"], "target_mix")
        self.assertEqual(result["bands"], {"core": 4, "stretch": 1, "transition": 3, "floor": 1})
        findings, evidence = _bands(SimpleNamespace(extras={"calibration": {"checks": checks}}))
        self.assertEqual(findings, [])
        self.assertEqual(evidence["counts"], result["bands"])

        checks["c0"].update(passed=80, failed=20)
        self.assertEqual(profile(checks)["status"], "needs_redesign")
        findings, _ = _bands(SimpleNamespace(extras={"calibration": {"checks": checks}}))
        self.assertTrue(any(f.code == "too-few-core-checks" for f in findings))

    def test_guards_gates_and_uncertainty_do_not_inflate_core(self):
        p = profile({"guard": {"kind": "guardrail", "passed": 5, "failed": 5},
                     "decision": {"kind": "objective", "passed": 3, "failed": 2, "gated_out": 5}})
        self.assertEqual(p["objective_count"], 1)
        self.assertEqual(p["guardrail_count"], 1)
        self.assertEqual(p["checks"]["decision"]["rate"], .6)
        self.assertTrue(p["checks"]["decision"]["provisional"])
        self.assertTrue(p["checks"]["decision"]["boundary_uncertain"])
        for value in (-1, True, .5, "1"):
            with self.assertRaises(ValueError):
                observation({"passed": value})

    def test_duplicate_records_are_not_diagnosed_as_equivalent(self):
        self.assertNotEqual(_miss_shape([{"id": "A"}], [{"id": "A"}, {"id": "A"}]), "equal_normalised")

    def test_all_fail_is_admissible_and_unchanged_is_not(self):
        # POLICY.md: a hard task is the goal. Attribution carries the burden.
        before = measured([10] * 6)
        zero = acceptance(before, measured([0] * 6), True, True, [])
        self.assertTrue(zero["accept"])
        self.assertEqual(zero["disposition"], "hard")
        self.assertFalse(acceptance(before, before, True, True, [])["accept"])
        accepted = acceptance(before, measured([5, 5, 5, 5, 10, 1]), True, True, [])
        self.assertTrue(accepted["accept"])
        self.assertFalse(accepted["release_ready"])

    def test_model_or_protocol_change_invalidates_comparison(self):
        before = measured([10] * 6)
        after = measured([5, 5, 5, 5, 10, 1], ("one", "other"))
        self.assertFalse(acceptance(before, after, True, True, [])["accept"])
        after = measured([5, 5, 5, 5, 10, 1])
        after["by_model"]["one"]["effort"] = "low"
        self.assertFalse(acceptance(before, after, True, True, [])["accept"])

    def test_pooled_half_success_is_not_core(self):
        base = {"ok": True, "models": ["a", "b"], "checks": {"s/c": {
            "id": "c", "step": "s", "weight": 100,
            "by_model": {"a": observation({"passed": 10}), "b": observation({"failed": 10})}}}}
        with patch("pipeline.harden.baseline", return_value=base):
            report = hardenable(Path("unused"))
        self.assertEqual(report["in_band"], [])
        self.assertEqual(report["mixed_models"], ["s/c"])

    def test_stale_grader_fails_before_solver(self):
        with tempfile.TemporaryDirectory() as tmp:
            bundle = synthetic_bundle(Path(tmp))
            (bundle / "tests/criteria.py").write_text("raise RuntimeError('stale')")
            with patch("pipeline.calibrate.run._rollout_for") as solver:
                with self.assertRaisesRegex(RuntimeError, "stale host evaluator"):
                    campaign(bundle, "unused", 1)
                solver.assert_not_called()

    def test_revision_preserves_control_checks_and_dependencies(self):
        from pipeline.harden import revision_problems
        before = {"steps": [{"name": "one", "instruction": "old question"}], "checks": [
            {"id": "easy", "target": 1}, {"id": "core", "target": 2}]}
        after = copy.deepcopy(before)
        after["steps"][0]["instruction"] = "clearer revised question"
        after["checks"][0]["target"] = 3
        self.assertEqual(revision_problems(before, after, [{"id": "easy"}]), [])
        after["checks"][1]["target"] = 0
        after["checks"][0]["requires"] = ["core"]
        self.assertEqual(len(revision_problems(before, after, [{"id": "easy"}])), 2)

    # The build-time pilot and its difficulty redesign loop were removed on
    # 2026-09-25: a build never measures difficulty. The batch screen does,
    # once every task exists, and nothing it measures is fed back into design.

    def test_semantic_repair_is_reviewed_before_spending_solver_attempts(self):
        from pipeline import orchestrate
        from pipeline.tests.test_guards import GateRepairLoop
        events = []
        bad = {"verdict": "blocked", "findings": ["Semantic review o1_authority: The public source authority is ambiguous"]}
        good = {"verdict": "green", "findings": []}
        with patch.object(orchestrate, "GATE_REPAIRS", 1):
            result, calls = GateRepairLoop()._patched_build_one(["green", "green"], [bad, good], events)
        self.assertEqual(result.status, "validated", result.error)
        self.assertEqual(calls[1], bad["findings"])
        # No solver episode anywhere in the build, even after the repair.
        self.assertEqual(events, ["design", "review", "design", "review"])

    def test_semantic_review_error_stops_without_redesign_or_calibration(self):
        from pipeline.tests.test_guards import GateRepairLoop
        events = []
        result, calls = GateRepairLoop()._patched_build_one(["green"], [
            {"verdict": "unverified", "findings": ["review transport incomplete"]}], events)
        self.assertEqual(result.status, "unverified")
        self.assertEqual(result.stage_reached, "semantic-review")
        self.assertEqual(events, ["design", "review"])

    def test_repeated_semantic_rejection_exhausts_design_budget_without_solving(self):
        from pipeline import orchestrate
        from pipeline.tests.test_guards import GateRepairLoop
        events = []
        bad = {"verdict": "blocked", "findings": ["Semantic review o2_answer: source does not establish the answer"]}
        with patch.object(orchestrate, "GATE_REPAIRS", 1):
            result, calls = GateRepairLoop()._patched_build_one(["green", "green"], [bad, bad], events)
        self.assertEqual(result.status, "blocked")
        self.assertEqual(events, ["design", "review", "design", "review"])
        self.assertEqual(len(calls), 2)


class SourceControls(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)
        self.bundle = synthetic_bundle(self.root)
        self.spec = json.loads((self.bundle / "authoring/spec.json").read_text())
        self.spec["quality"] = {"semantic_checks": ["open_ids", "open_count", "total_effort"],
            "source_cases": [{"id": "closed-ticket-reopened", "reason": "A formerly closed job now contributes work",
                "changes": ["open_ids", "open_count", "total_effort"],
                "source_patches": [{"file": "tickets.csv", "before": "R-22,closed,8", "after": "R-22,open,8"}],
                "patches": [{"file": "summary.json", "path": "open_ids", "value": ["R-21", "R-22", "R-23"]},
                            {"file": "summary.json", "path": "open_count", "value": 3},
                            {"file": "summary.json", "path": "total_effort", "value": 16}]}]}
        build(self.spec, self.bundle)

    def execute(self):
        return run(self.bundle, self.spec, self.spec["solution"],
                   {c["id"]: c for c in self.spec["checks"]}, self.root / "controls")

    def test_evidence_changes_decisions_and_formatting_does_not(self):
        before = identity(self.bundle)
        result = self.execute()
        self.assertEqual(result["errors"], [])
        self.assertIn("controller-final-newline", result["results"])
        self.assertEqual(identity(self.bundle), before)

    def test_wrong_counterfactual_cannot_pass(self):
        self.spec["quality"]["source_cases"][0]["patches"][-1]["value"] = 999
        self.assertTrue(any("must score 1" in e for e in self.execute()["errors"]))

    def test_inert_source_cannot_be_claimed_as_decisive(self):
        case = self.spec["quality"]["source_cases"][0]
        case["source_patches"] = [{"file": "unprojected.txt", "before": "All fixture bytes are protected.", "after": "Still protected."}]
        self.assertTrue(any("stale answer must fail" in e for e in self.execute()["errors"]))

    def test_missing_ambiguous_and_escaping_source_patches_reject(self):
        case = self.spec["quality"]["source_cases"][0]
        for file, before in (("../secret", "x"), ("tickets.csv", "open"), ("tickets.csv", "absent")):
            case["source_patches"] = [{"file": file, "before": before, "after": "new"}]
            self.assertTrue(problems(self.spec, self.bundle))

    def test_reserved_invariance_cannot_bypass_source_changes(self):
        self.spec["quality"]["source_cases"][0]["invariant"] = True
        self.assertTrue(problems(self.spec, self.bundle))


class InventoryAccounting(unittest.TestCase):
    def row(self, episode, step, checks, **extra):
        return {"episode": episode, "step": step, "checks": checks, "reward": 1,
                "stop_reason": "completed", "tool_calls": 2, **extra}

    def report(self, rows, requested=1, valid=1, by_step=None):
        return {"rollouts": rows, "summary": {"requested": requested, "valid": valid, "void": requested - valid},
                "by_step": by_step or {}}

    def test_partial_episode_never_contributes_earlier_success(self):
        rubric = {"first": ["c"], "second": ["d"]}
        rows = [self.row(1, "first", {"c": "passed"}),
                self.row(1, "second", {}, zero_class="void", reward=None)]
        counts, summary, _ = recount(self.report(rows, valid=0), rubric)
        self.assertEqual(summary["valid"], 0)
        self.assertEqual(counts["first"]["c"]["passed"], 0)
        self.assertEqual(counts["second"]["d"]["failed"], 0)

    def test_missing_episode_is_not_a_failure(self):
        counts, summary, _ = recount(self.report([self.row(1, "s", {"c": "failed"})], requested=2), {"s": ["c"]})
        self.assertEqual(summary["void_or_missing"], 1)
        self.assertEqual(counts["s"]["c"]["failed"], 1)

    def test_repeated_step_and_false_summary_are_detected(self):
        rows = [self.row(1, "s", {"c": "passed"}), self.row(1, "s", {"c": "passed"})]
        counts, summary, errors = recount(self.report(rows), {"s": ["c"]})
        self.assertEqual(summary["valid"], 0)
        self.assertEqual(counts["s"]["c"]["passed"], 0)
        self.assertTrue(any("summary disagrees" in e for e in errors))

    def test_shared_guardrail_is_counted_once_in_inventory(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            bundle = synthetic_bundle(root, True)
            result = audit(root)
            checks = json.loads((bundle / "tests/checks.json").read_text())["checks"]
            self.assertEqual(result["summary"]["unique_checks"], len(checks))
            self.assertEqual(result["summary"]["by_kind"]["guardrail"], 1)
            self.assertEqual(result["summary"]["by_validity"], {"unmeasured": len(checks)})


if __name__ == "__main__":
    unittest.main()
