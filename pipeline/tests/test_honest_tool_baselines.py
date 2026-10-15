from copy import deepcopy
import json
from pathlib import Path
import tempfile
import unittest

from pipeline.artifacts import atomic_json
from pipeline.assurance import controls
from pipeline.author.adversarial import problems
from pipeline.tests.test_adversarial_construction import stress_spec
from pipeline.tests.test_production import synthetic_bundle


class HonestToolBaselineTests(unittest.TestCase):
    def test_successful_competent_baseline_is_a_valid_construction_record(self):
        spec = stress_spec()
        for baseline in spec["quality"]["capability_plan"]["tool_baselines"]:
            baseline.pop("counterexample")
            baseline.update(submission={"answer.json": {"complete": "correct public-policy output"}}, fails=[])
        self.assertEqual(problems(spec), [])

    def test_baseline_cannot_both_claim_complete_outputs_and_inherit_a_wrong_case(self):
        spec = stress_spec()
        spec["quality"]["capability_plan"]["tool_baselines"][0].update(submission={"answer.json": {}}, fails=[])
        self.assertTrue(any("must not also inherit" in problem for problem in problems(spec)))

    def fixture(self, folder):
        bundle = synthetic_bundle(Path(folder))
        spec = json.loads((bundle / "authoring/spec.json").read_text())
        baseline = {"id": "complete-computation", "kind": "computation",
                    "method": "Read every public status record, select every open record and correctly sum its effort.",
                    "submission": deepcopy(spec["solution"]), "fails": []}
        spec["quality"] = {"capability_plan": {"version": 2, "tool_baselines": [baseline]}}
        return bundle, spec, baseline

    def test_full_score_baseline_is_executed_not_rejected_or_called_a_model_failure(self):
        with tempfile.TemporaryDirectory() as folder:
            bundle, spec, baseline = self.fixture(folder)
            atomic_json(bundle / "authoring/spec.json", spec)
            report = controls(bundle)
        result = report["tool_baselines"][baseline["id"]]
        self.assertTrue(result["passes_all_steps"])
        self.assertEqual(result["observed_failures"], [])
        self.assertFalse(result["native_model_measurement"])
        self.assertTrue(result["method_requires_independent_review"])
        self.assertFalse(any("tool baseline" in error for error in report["errors"]))

    def test_declared_failure_set_must_match_the_complete_executed_answer(self):
        with tempfile.TemporaryDirectory() as folder:
            bundle, spec, baseline = self.fixture(folder)
            baseline["submission"]["summary.json"]["open_count"] = 99
            atomic_json(bundle / "authoring/spec.json", spec)
            report = controls(bundle)
            self.assertTrue(any("declared failures do not match" in error for error in report["advisories"]))  # v2: advisory
            self.assertEqual(report["tool_baselines"][baseline["id"]]["observed_failures"], ["open_count"])
            baseline["fails"] = ["open_count"]
            atomic_json(bundle / "authoring/spec.json", spec)
            corrected = controls(bundle)
            self.assertFalse(any("tool baseline" in error for error in corrected["errors"] + corrected["advisories"]))

    def test_incomplete_or_malformed_baseline_is_not_capability_evidence(self):
        with tempfile.TemporaryDirectory() as folder:
            bundle, spec, baseline = self.fixture(folder)
            baseline["submission"] = {}
            atomic_json(bundle / "authoring/spec.json", spec)
            report = controls(bundle)
            self.assertTrue(any("complete public outputs" in error for error in report["advisories"]))  # v2: advisory
            baseline["submission"] = {"summary.json": {"open_ids": "not an array"}}
            atomic_json(bundle / "authoring/spec.json", spec)
            report = controls(bundle)
            self.assertTrue(any("serialization is not a capability failure" in error for error in report["advisories"]))  # v2: advisory
            self.assertEqual(report["tool_baselines"], {})


if __name__ == "__main__":
    unittest.main()
