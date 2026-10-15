from contextlib import ExitStack
from copy import deepcopy
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

from pipeline import checkpoint, orchestrate, repair
from pipeline.artifacts import atomic_json
from pipeline.author import agent_designer as author
from pipeline.author.build import build
from pipeline.evaluate import exported_grade
from pipeline.tests.test_production import synthetic_bundle


class SubmissionBoundaryTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.bundle = Path(self.temporary.name) / "candidate"
        (self.bundle / "environment/files").mkdir(parents=True)
        (self.bundle / "environment/files/source.txt").write_text("Public professional evidence.")
        atomic_json(self.bundle / "authoring/extraction/extraction.json", {})
        self.extraction = SimpleNamespace(session_id="source", seed_index=0)

    def test_submit_retains_candidate_without_running_optional_local_checks(self):
        diagnostic = Mock(return_value={"clean": False, "problems": ["Quality needs work"]})
        response = {"stop_reason": "tool_use", "content": [{"type": "tool_use", "id": "submit",
                    "name": "submit_draft", "input": {}}]}
        with patch("pipeline.dump.recover.load_trace", return_value={"messages": []}), \
                patch("pipeline.privacy.scan", return_value=[]), \
                patch("pipeline.corpus.source_briefs", return_value={}), \
                patch.object(author, "_opening", return_value="Read the source"), \
                patch.object(author, "_tools", return_value=[]), \
                patch.object(author, "_handlers", return_value={"draft_spec": lambda: {"name": "unfinished"},
                                                               "check_spec": diagnostic}), \
                patch.object(author, "_call", return_value=response) as call:
            submitted = author.design({}, self.extraction, self.bundle, max_steps=1)
        self.assertEqual(call.call_count, 1)
        diagnostic.assert_not_called()
        self.assertTrue(submitted["_validation_deferred"])
        self.assertNotIn("solution", submitted)
        saved = checkpoint.resumable(self.bundle)
        self.assertEqual(saved["stage"], "submitted")
        self.assertEqual(checkpoint.submitted_spec(self.bundle), submitted)
        self.assertFalse(saved["release_ready"])

    def test_direct_export_cannot_bypass_downstream_validation(self):
        spec = {"source": {"session_id": "source", "seed_index": 0}, "_validation_deferred": True}
        with patch("pipeline.author.extract.extract", return_value=self.extraction), \
                patch.object(author, "validate_submission", return_value={"clean": False,
                    "problems": ["Unpublished professional rule"]}):
            with self.assertRaisesRegex(ValueError, "mandatory downstream validation"):
                build(spec, self.bundle)
        self.assertFalse((self.bundle / "task.toml").exists())
        self.assertTrue(spec["_validation_deferred"])

    def exported_validation_fixture(self):
        bundle = synthetic_bundle(self.bundle.parent)
        spec = json.loads((bundle / "authoring/spec.json").read_text())
        spec["quality"] = {"semantic_checks": [], "counterexamples": [{
            "id": "ignore-status", "fails": ["open_ids", "open_count", "total_effort"],
            "submission": {"summary.json": {"open_ids": ["R-21", "R-22", "R-23"],
                                             "open_count": 3, "total_effort": 16}}}]}
        spec["_validation_deferred"] = True
        extraction = SimpleNamespace(**spec["source"])
        stack = ExitStack()
        self.addCleanup(stack.close)
        stack.enter_context(patch("pipeline.dump.recover.load_trace", return_value={"messages": []}))
        stack.enter_context(patch("pipeline.author.extract.extract", return_value=extraction))
        stack.enter_context(patch("pipeline.author.quality.production_problems", return_value=[]))
        stack.enter_context(patch.object(author, "validate", return_value=[]))
        stack.enter_context(patch("pipeline.ledger.faithfulness.citation_problems", return_value=[]))
        stack.enter_context(patch("pipeline.ledger.grounding.alignment_problems", return_value=[]))
        return bundle, spec, extraction

    def test_deferred_validation_runs_real_reference_export_and_controls_once(self):
        bundle, spec, extraction = self.exported_validation_fixture()
        submitted = deepcopy(spec)
        verdict = author.validate_submission(spec, spec["source"], extraction, bundle)
        self.assertTrue(verdict["clean"], verdict["problems"])
        self.assertEqual(verdict["reference_answer"], spec["solution"])
        self.assertEqual(spec, submitted)
        self.assertFalse(verdict["release_ready"])
        repeated = author.validate_submission(spec, spec["source"], extraction, bundle)
        self.assertTrue(repeated["reused_exact_validation"])

    def test_direct_deferred_export_runs_real_validation_before_writing(self):
        bundle, spec, extraction = self.exported_validation_fixture()
        build(spec, bundle)
        self.assertNotIn("_validation_deferred", spec)
        result = exported_grade(bundle, bundle / "solution/submission", "01-summary")
        self.assertEqual(result["reward"], 1)
        saved = json.loads((bundle / "authoring/spec.json").read_text())
        self.assertNotIn("_validation_deferred", saved)

    def test_failed_reference_cannot_remove_external_deferred_validation_marker(self):
        bundle, spec, extraction = self.exported_validation_fixture()
        spec["solution"]["summary.json"]["open_count"] = 99
        submitted = deepcopy(spec)
        verdict = author.validate_submission(spec, spec["source"], extraction, bundle)
        self.assertFalse(verdict["clean"])
        self.assertTrue(any("open_count" in problem for problem in verdict["problems"]))
        self.assertEqual(spec, submitted)
        with self.assertRaisesRegex(ValueError, "mandatory downstream validation"):
            build(spec, bundle)
        self.assertEqual(spec, submitted)

    def test_recursion_is_a_pipeline_failure_not_a_task_repair_finding(self):
        bundle, spec, extraction = self.exported_validation_fixture()
        with patch.object(author, "derive_solution", side_effect=RecursionError("pipeline recursion")):
            verdict = author.validate_submission(spec, spec["source"], extraction, bundle)
        self.assertFalse(verdict["clean"])
        self.assertTrue(verdict["validation_unverified"])
        self.assertTrue(spec["_validation_deferred"])

    def run_rejected_submission(self, problems, repair_limit):
        spec = {"name": "submitted", "source": {"session_id": "source", "seed_index": 0},
                "_validation_deferred": True}
        row = spec["source"]
        with patch.object(orchestrate, "_bundle_for", return_value=self.bundle), \
                patch.object(orchestrate.extract_stage, "extract", return_value=self.extraction), \
                patch.object(author, "validate_submission", side_effect=[{"clean": False, "problems": findings}
                                                                         for findings in problems]), \
                patch.object(orchestrate.build_stage, "build") as exported:
            designer = Mock(side_effect=lambda *arguments, **options: deepcopy(spec))
            result = orchestrate._build_one(row, 1, self.bundle.parent, designer,
                                            orchestrate.Budget(1), gate_repairs=repair_limit, preserve_workspace=True)
        exported.assert_not_called()
        return result, designer

    def test_rejected_post_submission_is_retained_and_never_benchmarked(self):
        result, designer = self.run_rejected_submission([["Unsupported source capability"]], 0)
        self.assertEqual(result.status, "blocked")
        self.assertEqual(result.stage_reached, "draft-validation")
        self.assertEqual(designer.call_count, 1)
        self.assertEqual(repair.passes_used(self.bundle), 0)
        self.assertTrue(list((self.bundle / "verification/design-attempts").glob("*.json")))
        self.assertEqual(checkpoint.read(self.bundle)["stage"], "blocked")

    def test_unverified_local_execution_does_not_charge_a_task_repair(self):
        spec = {"name": "submitted", "source": {"session_id": "source", "seed_index": 0},
                "_validation_deferred": True}
        with patch.object(orchestrate, "_bundle_for", return_value=self.bundle), \
                patch.object(orchestrate.extract_stage, "extract", return_value=self.extraction), \
                patch.object(author, "validate_submission", return_value={"clean": False,
                    "validation_unverified": True, "problems": ["OSError: local worker unavailable"]}), \
                patch.object(orchestrate.build_stage, "build") as exported:
            designer = Mock(return_value=spec)
            result = orchestrate._build_one(spec["source"], 1, self.bundle.parent, designer,
                                            orchestrate.Budget(1), gate_repairs=2, preserve_workspace=True)
        self.assertEqual(result.status, "unverified")
        self.assertEqual(designer.call_count, 1)
        self.assertEqual(repair.passes_used(self.bundle), 0)
        self.assertEqual(checkpoint.read(self.bundle)["stage"], "submitted")
        exported.assert_not_called()

    def test_post_submission_defects_use_the_existing_shared_repair_budget(self):
        result, designer = self.run_rejected_submission([["Bad source quote", "Missing public rounding rule"],
                                                         ["Missing public rounding rule"]], 1)
        self.assertEqual(result.status, "blocked")
        self.assertEqual(designer.call_count, 2)
        self.assertTrue(designer.call_args.kwargs["revision"])
        self.assertEqual(repair.passes_used(self.bundle), 1)
        self.assertEqual(checkpoint.read(self.bundle)["gate_repairs_remaining"], 0)


if __name__ == "__main__":
    unittest.main()
