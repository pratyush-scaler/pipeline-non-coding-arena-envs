"""Selection witnesses work through the exported grader and causal controls."""
import copy
import json
from pathlib import Path
import tempfile
import unittest

from pipeline.artifacts import atomic_json
from pipeline.author.build import build
from pipeline.author.checks import Check, CheckError, Workspace, run_check
from pipeline.author.probes import _stored_path_witness
from pipeline.evaluate import exported_grade
from pipeline.source_controls import run as source_controls
from pipeline.verify_shipped import run_reference
from pipeline.tests.test_production import synthetic_bundle
from pipeline.tests.test_subset_witness import problem, item, answer


class SubsetWitnessExport(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.bundle = synthetic_bundle(self.root)
        self.public = problem()
        atomic_json(self.bundle / "environment/files/allocation.json", self.public)
        self.spec = json.loads((self.bundle / "authoring/spec.json").read_text())
        guard = self.spec["checks"][0]
        self.check = {"id": "allocation", "kind": "objective", "weight": 1,
                      "basis": "Maximize gain then minimize cost subject to all public constraints; accept all optimal ties.",
                      "assertion": "optimal_subset", "actual": {"op": "field", "file": "plan.json", "path": "plan"},
                      "target": {"op": "field", "file": "allocation.json", "path": ""}}
        self.spec["checks"] = [guard, self.check]
        self.spec["projections"] = []
        self.spec["solution"] = {"plan.json": {"plan": answer(["Beta", "Gamma"], 16, 10)}}
        plan_schema = {"type": "object", "properties": {
            "feasible": {"type": "boolean"}, "selected": {"type": "array", "items": {"type": "string"}, "maxItems": 18},
            "totals": {"type": "object", "properties": {"gain": {"type": "number"}, "cost": {"type": "number"}},
                       "required": ["gain", "cost"], "additionalProperties": False}},
            "required": ["feasible", "selected"], "additionalProperties": False}
        self.spec["outputs"] = [{"file": "plan.json", "step": 1, "schema": {
            "type": "object", "properties": {"plan": plan_schema}, "required": ["plan"], "additionalProperties": False}}]
        self.spec["quality"] = {"semantic_checks": ["allocation"], "source_cases": [{
            "id": "different-eligibility", "reason": "The public exclusion of Beta makes Alpha the optimal eligible choice.",
            "changes": ["allocation"], "source_patches": [{"file": "allocation.json",
              "before": '"id": "Beta",\n      "eligible": true', "after": '"id": "Beta",\n      "eligible": false'}],
            "patches": [{"file": "plan.json", "path": "plan", "value": answer(["Alpha"], 9, 6)}]}]}
        build(self.spec, self.bundle)

    def grade(self, value):
        submitted = self.root / "submitted"
        atomic_json(submitted / "plan.json", {"plan": value})
        return exported_grade(self.bundle, submitted, "01-summary")

    def test_exported_reference_full_mark_empty_zero_and_greedy_zero(self):
        self.assertEqual(self.grade(answer(["Beta", "Gamma"], 16, 10))["reward"], 1)
        self.assertEqual(self.grade(answer(["Alpha"], 9, 6))["reward"], 0)
        empty = self.root / "empty"
        empty.mkdir()
        self.assertEqual(exported_grade(self.bundle, empty, "01-summary")["reward"], 0)

    def test_shipped_reference_script_solves_the_problem_and_adapts_to_new_evidence(self):
        self.assertEqual(run_reference(self.bundle)["problems"], [])
        self.public["items"][1]["eligible"] = False
        atomic_json(self.bundle / "environment/files/allocation.json", self.public)
        build(self.spec, self.bundle)
        self.assertEqual(run_reference(self.bundle)["problems"], [])

    def test_export_accepts_every_optimal_tie_without_a_private_path(self):
        self.public["items"] = [item("Alpha", 8, 5), item("Beta", 8, 5), item("Gamma", 8, 5)]
        atomic_json(self.bundle / "environment/files/allocation.json", self.public)
        build(self.spec, self.bundle)
        for selected in (["Alpha", "Beta"], ["Gamma", "Beta"], ["Alpha", "Gamma"]):
            self.assertEqual(self.grade(answer(selected, 16, 10))["reward"], 1)

    def test_submitted_problem_cannot_override_source_eligibility(self):
        changed = copy.deepcopy(self.public)
        changed["items"][0]["values"]["gain"] = 1000
        atomic_json(self.root / "submitted/allocation.json", changed)
        self.assertEqual(self.grade(answer(["Alpha"], 1000, 6))["reward"], 0)

    def test_infeasible_control_does_not_require_an_illegal_totals_field(self):
        self.public["constraints"][0]["min"] = 10
        self.public["constraints"][0]["max"] = 10
        for row in self.public["items"]:
            row["eligible"] = False
        atomic_json(self.bundle / "environment/files/allocation.json", self.public)
        self.spec["solution"]["plan.json"]["plan"] = {"feasible": False, "selected": []}
        build(self.spec, self.bundle)
        self.assertEqual(self.grade({"feasible": False, "selected": []})["reward"], 1)

    def test_eligibility_intervention_changes_the_globally_correct_answer(self):
        checks = {record["id"]: record for record in self.spec["checks"]}
        result = source_controls(self.bundle, self.spec, self.spec["solution"], checks, self.root / "controls")
        self.assertEqual(result["errors"], [], result)
        self.assertEqual(result["results"]["different-eligibility"]["observed_semantic_changes"], ["allocation"])

    def test_grader_fault_is_raised_even_when_no_submission_exists(self):
        self.public["items"][0]["requires"] = ["missing"]
        atomic_json(self.bundle / "environment/files/allocation.json", self.public)
        with self.assertRaisesRegex(CheckError, "invalid optimal_subset source"):
            run_check(Check(**self.check), Workspace(self.bundle / "environment/files", self.root / "missing"))

    def test_complete_copied_solution_is_detected_including_an_optimal_tie(self):
        fixture = self.bundle / "environment/files"
        self.assertIsNone(_stored_path_witness(self.public, fixture, "optimal_subset"))
        atomic_json(fixture / "draft.json", {"nested": answer(["Gamma", "Beta"], 16, 10)})
        self.assertIsNotNone(_stored_path_witness(self.public, fixture, "optimal_subset"))

    def test_unreviewed_selection_runtime_cannot_execute_on_the_host(self):
        marker = self.root / "must-not-exist"
        runtime = self.bundle / "tests/_arena_runtime/subset_witness.py"
        runtime.write_text(f'from pathlib import Path\nPath({str(marker)!r}).write_text("bad")\n')
        with self.assertRaisesRegex(RuntimeError, "unaudited or stale host evaluator"):
            self.grade(answer(["Beta", "Gamma"], 16, 10))
        self.assertFalse(marker.exists())


if __name__ == "__main__":
    unittest.main()
