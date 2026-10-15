"""Unscaffolded-task acceptance requires a current independent surface review."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import shutil
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from pipeline import orchestrate, repair, review
from pipeline.artifacts import atomic_json, identity
from pipeline.author import brief
from pipeline.author.build import build
from pipeline.tests.test_production import synthetic_bundle
from pipeline.tests.test_solver_brief import synthetic_autonomy_assessment


class SolverAutonomyAcceptance(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.bundle = synthetic_bundle(self.root)
        self.spec = json.loads((self.bundle / "authoring/spec.json").read_text())
        self.spec["_producer"] = {"model": "author"}
        build(self.spec, self.bundle)
        self.enterContext(patch("pipeline.review.source_provenance", return_value={}))
        self.enterContext(patch("pipeline.corpus.review_context", return_value={"peers": []}))
        self.mutate = lambda doc: None
        self.calls = 0

    def critic(self, _prompt, public, work, model, _tag, max_steps):
        self.calls += 1
        self.assertIn("MANDATORY UNSCAFFOLDED-TASK ACCEPTANCE", _prompt)
        self.assertTrue((public / "solver-visibility.json").is_file())
        self.assertFalse((self.bundle / "environment/files/solver-visibility.json").exists())
        shutil.copytree(public, work / "workspace")
        atomic_json(work / "conversation.json", [])
        atomic_json(work / "request-config.json", {"model": model, "max_steps": max_steps})
        doc = {"verdict": "pass", "checks": [{"id": check["id"], "verdict": "pass",
            "reason": "Synthetic fixture verifies exact independent review binding, not real semantic correctness.",
            "citations": [{"file": "fixture/tickets.csv", "quote": "ticket,status,effort\nR-21,open,3"}]}
            for check in self.spec["checks"]], "ambiguities": [], "substantive_gaps": [], "shortcut_risks": [],
            "privacy_findings": [], "difficulty_advisories": [],
            "difficulty_assessment": "Synthetic regression fixture; no native difficulty or model incapability is being measured.",
            "novelty_assessment": "Synthetic regression fixture; no production novelty or human semantic review is being asserted.",
            "untested_surfaces": ["No real semantic review or native calibration occurs in this regression fixture."],
            "solver_autonomy": synthetic_autonomy_assessment(public)}
        self.mutate(doc)
        atomic_json(work / "deliverables/review.json", doc)
        return SimpleNamespace(error=None, stop_reason="completed", tool_calls=1), None

    def run_review(self):
        with patch("pipeline.calibrate.run._rollout_for", return_value=self.critic):
            return review.review(self.bundle, "critic")

    def staged_assessment(self):
        workspace = self.root / "staged"
        shutil.copytree(self.bundle / "environment/files", workspace / "fixture", dirs_exist_ok=True)
        shutil.copytree(self.bundle / "environment", workspace / "package-layout", dirs_exist_ok=True)
        shutil.copytree(self.bundle / "steps", workspace / "steps", dirs_exist_ok=True)
        atomic_json(workspace / "solver-visibility.json", brief.visibility_manifest(self.bundle))
        return workspace, synthetic_autonomy_assessment(workspace)

    def coaching(self, doc):
        assessment = doc["solver_autonomy"]
        assessment["verdict"] = "revise"
        row = next(row for row in assessment["surfaces"] if row["file"] == "fixture/guide.md")
        row["classification"] = "task_specific_coaching"
        row["reason"] = "The authored guide prescribes the task's exact join and filtering path instead of giving a business requirement."

    def add_guide(self):
        (self.bundle / "environment/files/guide.md").write_text("First join the ticket register to the answer map; then filter the resolved rows.")

    def test_complete_bound_assessment_is_required_for_acceptance(self):
        report = self.run_review()
        self.assertEqual(report["errors"], [])
        self.assertTrue(report["ok"])
        self.assertEqual(review.review_problems(self.bundle, report), [])

    def test_missing_assessment_is_unverified_not_a_model_failure(self):
        self.mutate = lambda doc: doc.pop("solver_autonomy")
        report = self.run_review()
        self.assertFalse(report["ok"])
        self.assertIn("solver autonomy lacks a mandatory independent assessment", report["errors"])
        self.assertFalse(review.semantic_rejection(report["errors"]))

    def test_author_cannot_opt_out_of_the_mandatory_assessment(self):
        self.spec["quality"] = {"solver_autonomy_required": False}
        build(self.spec, self.bundle)
        self.mutate = lambda doc: doc.pop("solver_autonomy")
        report = self.run_review()
        self.assertFalse(report["ok"])
        self.assertIn("solver autonomy lacks a mandatory independent assessment", report["errors"])

    def test_author_self_certification_cannot_replace_independent_review(self):
        report = self.run_review()
        work = self.bundle / report["work_dir"]
        config = work / "request-config.json"
        atomic_json(config, {"model": "author", "max_steps": 60})
        report["model"] = "author"
        report["artifacts"]["request-config.json"] = hashlib.sha256(config.read_bytes()).hexdigest()
        self.assertIn("semantic reviewer must be identified and use a different model from the author",
            review.review_problems(self.bundle, report))

    def test_omitting_an_entire_fixture_is_not_a_passing_review(self):
        self.mutate = lambda doc: doc["solver_autonomy"]["surfaces"].pop()
        report = self.run_review()
        self.assertIn("solver autonomy must cover every inventoried surface exactly once", report["errors"])

    def test_duplicate_surface_cannot_stand_in_for_missing_coverage(self):
        workspace, assessment = self.staged_assessment()
        assessment["surfaces"].append(deepcopy(assessment["surfaces"][0]))
        self.assertIn("solver autonomy must cover every inventoried surface exactly once",
            brief.assessment_problems(self.bundle, workspace, assessment))

    def test_invented_private_path_cannot_prove_public_visibility(self):
        workspace, assessment = self.staged_assessment()
        assessment["surfaces"][0]["file"] = "../solution/submission/summary.json"
        errors = brief.assessment_problems(self.bundle, workspace, assessment)
        self.assertTrue(any("inventoried public/exposure surface" in error for error in errors))

    def test_fabricated_or_short_quotes_are_unverified(self):
        workspace, original = self.staged_assessment()
        for quote in (None, "not present in this file", "ticket", ""):
            with self.subTest(quote=quote):
                assessment = deepcopy(original)
                assessment["surfaces"][0]["quote"] = quote
                self.assertTrue(any("invalid solver autonomy citation" in error
                    for error in brief.assessment_problems(self.bundle, workspace, assessment)))

    def test_unknown_classification_or_unreasoned_assessment_does_not_pass(self):
        workspace, original = self.staged_assessment()
        for mutation in (lambda assessment: assessment.update(reason="okay"),
                         lambda assessment: assessment["surfaces"][0].update(classification=[]),
                         lambda assessment: assessment["surfaces"][0].update(reason="okay")):
            assessment = deepcopy(original)
            mutation(assessment)
            self.assertTrue(brief.assessment_problems(self.bundle, workspace, assessment))

    def test_safeguards_are_explicit_booleans_not_truthy_strings(self):
        workspace, original = self.staged_assessment()
        for field in ("requirements_preserved", "evidence_access_preserved", "native_tools_preserved"):
            assessment = deepcopy(original)
            assessment[field] = "true"
            self.assertTrue(any("explicitly assess" in error
                for error in brief.assessment_problems(self.bundle, workspace, assessment)))

    def test_lost_requirements_evidence_or_tools_hold_acceptance(self):
        workspace, original = self.staged_assessment()
        for field in ("requirements_preserved", "evidence_access_preserved", "native_tools_preserved"):
            assessment = deepcopy(original)
            assessment[field] = False
            errors = brief.assessment_problems(self.bundle, workspace, assessment)
            self.assertEqual(errors, ["unresolved review findings: solver_autonomy"])
            self.assertTrue(review.semantic_rejection(errors))

    def test_coaching_cannot_be_downgraded_to_a_nonblocking_difficulty_advisory(self):
        self.add_guide()
        def mutate(doc):
            self.coaching(doc)
            doc["solver_autonomy"]["verdict"] = "pass"
            doc["difficulty_advisories"] = ["The guide makes the task easy."]
        self.mutate = mutate
        report = self.run_review()
        self.assertFalse(report["ok"])
        self.assertEqual(report["errors"], ["unresolved review findings: solver_autonomy"])

    def test_answer_or_grader_leak_cannot_pass_even_when_global_verdict_says_pass(self):
        workspace, assessment = self.staged_assessment()
        assessment["surfaces"][0]["classification"] = "answer_or_grader_leak"
        self.assertEqual(brief.assessment_problems(self.bundle, workspace, assessment),
            ["unresolved review findings: solver_autonomy"])

    def test_verified_coaching_rejection_enters_build_repair_with_actionable_feedback(self):
        self.add_guide()
        self.mutate = self.coaching
        self.run_review()
        with patch("pipeline.review.review") as reroll:
            result = orchestrate._review_candidate(self.bundle, orchestrate.Budget(1))
        self.assertEqual(result["verdict"], "blocked")
        self.assertTrue(any("Solver autonomy fixture/guide.md" in finding for finding in result["findings"]))
        reroll.assert_not_called()
        self.assertEqual(self.calls, 1)

    def test_qualification_repair_receives_coaching_findings_without_solver_answers(self):
        self.add_guide()
        self.mutate = self.coaching
        self.run_review()
        with patch("pipeline.run.run_bundle", return_value={"verdict": "green", "results": []}):
            findings = repair.feedback(self.bundle, {"artifact_sha256": identity(self.bundle), "release_ready": False})
        self.assertTrue(any("Solver autonomy fixture/guide.md" in finding for finding in findings))

    def test_tampering_with_inventory_is_detected_even_if_artifact_hash_is_resealed(self):
        report = self.run_review()
        work = self.bundle / report["work_dir"]
        path = work / "workspace/solver-visibility.json"
        manifest = json.loads(path.read_text())
        manifest["surfaces"].pop(next(iter(manifest["surfaces"])))
        atomic_json(path, manifest)
        report["artifacts"]["workspace/solver-visibility.json"] = hashlib.sha256(path.read_bytes()).hexdigest()
        self.assertIn("solver visibility inventory differs from the trusted candidate",
            review.review_problems(self.bundle, report))

    def test_surface_tampering_cannot_be_hidden_by_resealing_execution_artifacts(self):
        report = self.run_review()
        path = self.bundle / report["work_dir"] / "workspace/fixture/tickets.csv"
        path.write_text(path.read_text() + "\nWorked solution: copy the published answer map.\n")
        report["artifacts"]["workspace/fixture/tickets.csv"] = hashlib.sha256(path.read_bytes()).hexdigest()
        self.assertTrue(any("surface differs from the candidate" in error
            for error in review.review_problems(self.bundle, report)))

    def test_new_public_note_changes_the_artifact_and_cannot_reuse_an_old_signoff(self):
        report = self.run_review()
        self.add_guide()
        self.assertEqual(review.review_problems(self.bundle, report),
            ["semantic review is missing, stale or belongs to another task"])

    def test_instruction_metadata_and_comment_surfaces_are_inventoried_not_private_plans(self):
        (self.bundle / "environment/files/records.csv").write_text("id,note\nA,task-specific comment\n")
        (self.bundle / "environment/files/metadata.json").write_text('{"description":"task-specific metadata"}')
        notes = self.bundle / "steps/01-summary/operating-notes.md"
        notes.write_text("Native generic file access is available without a solution walkthrough.")
        manifest = brief.visibility_manifest(self.bundle)
        for name in ("fixture/records.csv", "fixture/metadata.json", "steps/01-summary/instruction.md",
                     "steps/01-summary/operating-notes.md", "package-layout/Dockerfile"):
            self.assertIn(name, manifest["surfaces"])
        self.assertFalse(any(name.startswith(("authoring/", "solution/", "private-grader/")) for name in manifest["surfaces"]))

    def test_normative_formula_can_pass_after_semantic_review_even_if_regex_flags_it(self):
        self.spec["steps"][0]["instruction"] += " Then compute fees under the published annual-rate formula; this is a binding domain definition."
        build(self.spec, self.bundle)
        self.assertTrue(brief.construction_diagnostics(self.spec)["possible_scaffolding"])
        self.assertTrue(self.run_review()["ok"])

    def test_empty_tiny_and_whitespace_only_sources_do_not_require_fake_quotes(self):
        for name, content in (("empty.txt", ""), ("tiny.txt", "x\n"), ("spaces.txt", " " * 30)):
            (self.bundle / "environment/files" / name).write_text(content)
        workspace, assessment = self.staged_assessment()
        self.assertEqual(brief.assessment_problems(self.bundle, workspace, assessment), [])

    def test_uninspectable_binary_surface_is_unverified_not_certified_clean(self):
        (self.bundle / "environment/files/opaque.bin").write_bytes(b"\xff\xfe\x00")
        workspace, _ = self.staged_assessment_without_binary_read()
        assessment = {"schema": "arena-pipeline/solver-autonomy-review/1", "verdict": "pass",
            "reason": "Synthetic malformed fixture cannot establish absence of coaching in an opaque binary public source.",
            "requirements_preserved": True, "evidence_access_preserved": True, "native_tools_preserved": True,
            "surfaces": [{"file": name, "classification": "requirements_or_evidence",
                "reason": "Synthetic attempt to pass an uninspectable surface must remain unverified.", "quote": "unreadable"}
                for name in brief.visibility_manifest(self.bundle)["surfaces"]]}
        errors = brief.assessment_problems(self.bundle, workspace, assessment)
        self.assertTrue(any("opaque.bin" in error for error in errors))

    def staged_assessment_without_binary_read(self):
        workspace = self.root / "binary-staged"
        shutil.copytree(self.bundle / "environment/files", workspace / "fixture")
        shutil.copytree(self.bundle / "environment", workspace / "package-layout")
        shutil.copytree(self.bundle / "steps", workspace / "steps")
        return workspace, brief.visibility_manifest(self.bundle)

    def test_malformed_assessment_and_surface_lists_fail_closed_without_shape_crashes(self):
        workspace, original = self.staged_assessment()
        for value in (None, [], {}, {**original, "verdict": []}, {**original, "surfaces": None},
                      {**original, "surfaces": [None]}, {**original, "surfaces": [{"file": 7}]}):
            with self.subTest(value=value):
                self.assertTrue(brief.assessment_problems(self.bundle, workspace, value))

    def test_visibility_inventory_is_read_only_and_does_not_refund_budgets(self):
        previous = identity(self.bundle)
        self.run_review()
        self.assertEqual(identity(self.bundle), previous)
        self.assertEqual(brief.repair_findings({"solver_autonomy": {"surfaces": None}}), [])
        self.assertFalse((self.bundle / "verification/construction-protocol.json").exists())

    def test_release_evaluation_holds_a_verified_coaching_rejection(self):
        from pipeline import release
        self.add_guide()
        self.mutate = self.coaching
        self.run_review()
        with patch("pipeline.run.run_bundle", return_value={"verdict": "green", "results": []}), \
             patch("pipeline.assurance.generated_problems", return_value=[]), \
             patch("pipeline.assurance.control_problems_after_gates", return_value=[]):
            result = release._evaluate(self.bundle, replay=False)
        self.assertFalse(result["release_ready"])
        self.assertIn("semantic review: unresolved review findings: solver_autonomy", result["errors"])


if __name__ == "__main__":
    unittest.main()
