from copy import deepcopy
from contextlib import redirect_stdout
from pathlib import Path
import ast
import io
import math
import tempfile
import unittest
from unittest.mock import patch

from pipeline import harden, policy
from pipeline.benchmark.harbor import resolve_model
from pipeline.measurement import profile


class BindingModelHardeningTests(unittest.TestCase):
    def setUp(self):
        self.models = list(map(resolve_model, policy.resolve_calibration_models()))
        self.primary, self.secondary = self.models
        self.step = "01-task"
        checks = {}
        cohorts = {}
        counts = {self.primary: (2, 10, 10), self.secondary: (10, 10, 8)}
        for model, adjusted in ((self.primary, 0.2), (self.secondary, 0.8)):
            rows = profile({identifier: {"kind": "objective", "weight": 20, "passed": passed,
                "failed": 10 - passed, "gated_out": 0} for identifier, passed in
                zip(("astra-easy", "both-easy", "fable-easy"), counts[model])})
            cohorts[model] = {"protocol": "native", "effort": "high", "limits": {"no_limits": True},
                "episodes_valid": 10, "pass_at_1": adjusted,
                "capability_difficulty": {"episodes_valid": 10, "capability_adjusted_pass_at_1": adjusted},
                "steps": {self.step: rows}}
            for identifier, row in rows["checks"].items():
                check = checks.setdefault(f"{self.step}/{identifier}", {"id": identifier,
                    "step": self.step, "weight": 20, "by_model": {}})
                check["by_model"][model] = row
        base = {"ok": True, "errors": [], "artifact_sha256": "a" * 64, "models": self.models,
            "by_model": cohorts, "checks": checks}
        with patch("pipeline.harden.baseline", return_value=base):
            self.report = harden.hardenable(Path("unused"))

    def selected(self, report=None):
        return harden.hardening_targets(report or self.report)

    def ids(self, report=None):
        return [target["id"] for target in self.selected(report)]

    def test_medical_pattern_selects_astra_easy_objective_without_changing_floor(self):
        original = deepcopy(self.report)
        self.assertEqual([target["id"] for target in self.report["floor"]], ["both-easy"])
        self.assertEqual(self.ids(), ["astra-easy", "both-easy"])
        self.assertEqual(self.selected()[0]["binding_models"], [self.secondary])
        self.assertEqual(self.selected()[0]["rate"], 1)
        self.assertEqual(self.report, original)

    def test_candidate_ranking_accounts_for_binding_model_targets(self):
        mixed = Path("mixed-model")
        floor_only = Path("all-model-floor")
        weaker = deepcopy(self.report)
        row = weaker["checks"][f"{self.step}/astra-easy"]["by_model"][self.secondary]
        row.update(passed=8, failed=2, rate=0.8, band="transition")
        reports = {mixed: self.report, floor_only: weaker}
        with patch("pipeline.harden.bundle_paths", return_value=[floor_only, mixed]), \
                patch("pipeline.harden.hardenable", side_effect=lambda bundle: reports[bundle]):
            ranked = harden.candidates(Path("unused"))
        self.assertEqual([record["bundle"] for record in ranked], [mixed.name, floor_only.name])
        self.assertEqual([record["free_weight"] for record in ranked], [20, 20])
        self.assertEqual([record["target_weight"] for record in ranked], [40, 20])
        self.assertEqual([record["target_checks"] for record in ranked], [2, 1])

    def test_report_lists_binding_targets_without_spending_an_attempt(self):
        with tempfile.TemporaryDirectory() as temporary:
            bundle = Path(temporary)
            (bundle / "task.toml").write_text("")
            output = io.StringIO()
            with patch("pipeline.harden.hardenable", return_value=self.report), \
                    patch("pipeline.harden.run_lineage") as redesign, redirect_stdout(output):
                result = harden.main([str(bundle)])
            self.assertEqual(result, 0)
            redesign.assert_not_called()
            self.assertFalse((bundle / harden.LEDGER).exists())
        self.assertIn("additional binding-model targets -- 1 check(s)", output.getvalue())
        self.assertIn(f"{self.step}/astra-easy", output.getvalue())
        self.assertIn(self.secondary, output.getvalue())

    def test_tied_binding_models_must_both_be_floor(self):
        for cohort in self.report["by_model"].values():
            cohort["capability_difficulty"]["capability_adjusted_pass_at_1"] = 1
        self.assertEqual(self.ids(), ["both-easy"])

    def test_conservative_contract_adjusted_binding_not_raw_pass_rate(self):
        self.report["by_model"][self.primary]["pass_at_1"] = 0.2
        self.report["by_model"][self.primary]["capability_difficulty"]["capability_adjusted_pass_at_1"] = 0.2
        self.report["by_model"][self.secondary]["pass_at_1"] = 0.1
        self.report["by_model"][self.secondary]["capability_difficulty"]["capability_adjusted_pass_at_1"] = 1
        self.assertEqual(self.ids(), ["astra-easy", "both-easy"])

    def test_binding_hard_objective_is_never_unfrozen(self):
        self.assertNotIn("fable-easy", self.ids())
        for target in self.selected():
            self.assertEqual(target["weight"], 20)

    def test_unverified_stale_or_incomplete_cohorts_refuse_expansion(self):
        defects = [{"ok": False}, {"errors": ["stale artifact"]}, {"stale": True},
            {"measurement_complete": False}, {"models": self.models[:1]}, {"by_model": {}}]
        for defect in defects:
            with self.subTest(defect=defect):
                self.assertEqual(self.selected({**self.report, **defect}), [])

    def test_exact_required_model_set_and_distinct_cohorts_required(self):
        report = deepcopy(self.report)
        report["by_model"]["openai/different-model"] = report["by_model"].pop(self.secondary)
        report["models"] = list(report["by_model"])
        self.assertEqual(self.selected(report), [])
        self.report["models"].append(self.primary)
        self.assertEqual(self.selected(), [])

    def test_malformed_model_inventory_is_not_a_verified_cohort(self):
        self.report["models"] = [self.primary, []]
        self.assertEqual(self.selected(), [])

    def test_high_unlimited_complete_finite_model_evidence_required(self):
        defects = [{"effort": "low"}, {"limits": {"no_limits": False}}, {"episodes_valid": 0},
            {"episodes_valid": True}, {"pass_at_1": math.nan}, {"pass_at_1": True},
            {"pass_at_1": 1.1}, {"capability_difficulty": {}},
            {"capability_difficulty": {"episodes_valid": 9, "capability_adjusted_pass_at_1": 1}},
            {"capability_difficulty": {"episodes_valid": 10, "capability_adjusted_pass_at_1": math.inf}}]
        for defect in defects:
            with self.subTest(defect=defect):
                report = deepcopy(self.report)
                report["by_model"][self.primary].update(defect)
                self.assertEqual(self.selected(report), [])

    def test_conservative_score_cannot_be_below_official_score(self):
        self.report["by_model"][self.secondary]["capability_difficulty"]["capability_adjusted_pass_at_1"] = 0.1
        self.assertEqual(self.selected(), [])

    def test_guard_gated_missing_and_incomplete_check_counts_are_never_selected(self):
        key = f"{self.step}/astra-easy"
        defects = [{"kind": "guardrail"}, {"passed": 9}, {"gated_out": 1}, {"passed": True},
            {"failed": -1}, {"weight": 0}, {"rate": 0.9}, {"band": "stretch"}]
        for defect in defects:
            with self.subTest(defect=defect):
                report = deepcopy(self.report)
                report["checks"][key]["by_model"][self.secondary].update(defect)
                self.assertNotIn("astra-easy", self.ids(report))
        report = deepcopy(self.report)
        del report["checks"][key]["by_model"][self.primary]
        self.assertNotIn("astra-easy", self.ids(report))
        report = deepcopy(self.report)
        del report["by_model"][self.primary]["steps"][self.step]["checks"]["astra-easy"]
        self.assertNotIn("astra-easy", self.ids(report))

    def test_explicit_unreachable_and_invalid_check_metadata_excluded(self):
        self.report["unreachable"] = [f"{self.step}/astra-easy"]
        self.assertEqual(self.ids(), ["both-easy"])
        self.report["checks"][f"{self.step}/both-easy"]["weight"] = math.nan
        self.assertEqual(self.ids(), [])

    def test_guard_metadata_excludes_objective_looking_aggregate(self):
        self.report["checks"][f"{self.step}/astra-easy"]["kind"] = "guardrail"
        self.assertEqual(self.ids(), ["both-easy"])

    def test_reachable_ninety_percent_is_floor_but_not_every_attempt(self):
        row = self.report["checks"][f"{self.step}/astra-easy"]["by_model"][self.secondary]
        row.update(passed=9, failed=1, rate=0.9)
        self.assertIn("astra-easy", self.ids())
        self.assertEqual(self.selected()[0]["rate"], 0.9)

    def test_legacy_floor_only_report_is_preserved_without_mixed_expansion(self):
        floor = [{"id": "old-floor", "step": self.step, "weight": 10, "rate": 1}]
        report = {"ok": True, "errors": [], "floor": floor, "by_model": {}, "mixed_models": ["unsafe"]}
        self.assertEqual(self.selected(report), floor)
        self.assertIsNot(self.selected(report)[0], floor[0])
        report["ok"] = False
        self.assertEqual(self.selected(report), [])

    def test_binding_brief_uses_conservative_rates(self):
        self.report["by_model"][self.primary]["pass_at_1"] = 0.2
        self.report["by_model"][self.secondary]["pass_at_1"] = 0.1
        self.report["by_model"][self.secondary]["capability_difficulty"]["capability_adjusted_pass_at_1"] = 1
        with patch("pipeline.harden.hardenable", return_value=self.report):
            brief = harden._breadth_summary(Path("unused"), [])
        self.assertIn(f"BINDING MODEL: {self.secondary}", brief)
        self.assertNotIn("by every attempt", harden.TIGHTEN_ATTEMPT)

    def test_targeted_reaiming_keeps_untargeted_protectors_requires_and_weights(self):
        before = {"steps": [{"name": self.step}], "checks": [
            {"id": identifier, "kind": "objective", "step": self.step, "weight": 20,
             "requires": [], "target": {"value": 1}} for identifier in ("astra-easy", "fable-easy")]}
        after = deepcopy(before)
        after["checks"][0]["target"] = {"value": 2}
        self.assertEqual(harden.revision_problems(before, after, self.selected()), [])
        after["checks"][1]["target"] = {"value": 2}
        self.assertTrue(any("untargeted" in problem for problem in harden.revision_problems(before, after, self.selected())))
        after = deepcopy(before)
        after["checks"][0]["requires"] = ["fable-easy"]
        self.assertTrue(any("dependency chains" in problem for problem in harden.revision_problems(before, after, self.selected())))
        after = deepcopy(before)
        after["checks"][0]["weight"] = 10
        self.assertTrue(any("reducing" in problem for problem in harden.revision_problems(before, after, self.selected())))

    def test_expanded_targets_do_not_relax_two_model_acceptance(self):
        after = deepcopy(self.report)
        after["by_model"][self.secondary]["pass_at_1"] = 0.4
        after["by_model"][self.secondary]["capability_difficulty"]["capability_adjusted_pass_at_1"] = 0.4
        result = harden.acceptance(self.report, after, True, True, [])
        self.assertFalse(result["accept"])
        self.assertFalse(result["harder"])
        self.assertTrue(any(self.primary in reason and "did not fall" in reason for reason in result["reasons"]))

    def test_all_three_lineage_target_assignments_use_selector(self):
        tree = ast.parse(Path(harden.__file__).read_text())
        lineage = next(node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == "run_lineage")
        calls = [node for node in ast.walk(lineage) if isinstance(node, ast.Call)
                 and isinstance(node.func, ast.Name) and node.func.id == "hardening_targets"]
        self.assertEqual(len(calls), 3)

    def test_lineage_initial_targets_reach_author_without_spending_extra_attempts(self):
        with tempfile.TemporaryDirectory() as temporary:
            bundle = Path(temporary)
            (bundle / "task.toml").write_text("")
            with patch("pipeline.harden._resume_point", return_value=None), \
                    patch("pipeline.harden.attempt", return_value=[]) as attempt:
                result = harden.run_lineage(bundle, self.report, [], screen=False)
            self.assertEqual(result, 0)
            self.assertEqual(attempt.call_count, 1)
            self.assertEqual([target["id"] for target in attempt.call_args.args[2]], self.ids())
            self.assertEqual(harden.read_ledger(bundle)["max_attempts"], 3)


if __name__ == "__main__":
    unittest.main()
