"""Withhold solution coaching, never the rules needed for a fair assignment."""
from copy import deepcopy
import json
from pathlib import Path
import tempfile
import unittest

from pipeline import review
from pipeline.author import agent_designer, brief, challenge
from pipeline.author.build import build
from pipeline.author.contracts import public_contract
from pipeline.tests.test_production import synthetic_bundle


def diagnose(instruction):
    return brief.construction_diagnostics({"steps": [{"name": "01-audit", "instruction": instruction}]})


def synthetic_autonomy_assessment(workspace):
    manifest = json.loads((workspace / "solver-visibility.json").read_text())
    return {"schema": "arena-pipeline/solver-autonomy-review/1", "verdict": "pass",
        "reason": "Synthetic review fixture exercises bound surface coverage and citations; this is not a real semantic sign-off or hardness measurement.",
        "requirements_preserved": True, "evidence_access_preserved": True, "native_tools_preserved": True,
        "surfaces": [{"file": name, "classification": "requirements_or_evidence",
            "reason": "Synthetic surface assessment solely for testing the verified review receipt contract.",
            "quote": (workspace / name).read_text()[:80]} for name in manifest["surfaces"]]}


class SolverAutonomyBrief(unittest.TestCase):
    def test_complete_public_requirements_are_not_solution_hints(self):
        instruction = ("Audit the acquisition obligations using the supplied matter files. Write audit.json. "
            "consent_required means a remaining consent duty; notice_deadline is an ISO date or null when "
            "inapplicable. The executed governing agreement applies. Ownership strictly exceeding 50% triggers "
            "the duty. Add the published signed calendar-day offset to closing for the deadline. "
            "Only executed waivers effective before closing count. Records may be in any order. "
            "If the evidence cannot determine a conclusion, report undetermined. Do not edit the source files.")
        result = diagnose(instruction)
        self.assertEqual(result["instructions_scanned"], 1)
        self.assertEqual(result["possible_scaffolding"], [])
        self.assertTrue(result["normative_rules_must_remain_public"])
        self.assertFalse(result["establishes_leak_free"])

    def test_algorithm_and_reading_order_are_review_candidates_not_blockers(self):
        result = diagnose("Start by reading deal.md. Then join the clauses to the owner table. Next filter inactive rows.")
        self.assertEqual({entry["category"] for entry in result["possible_scaffolding"]}, {"reading_order", "solution_recipe"})
        self.assertFalse(result["creates_validity_blockers"])
        self.assertFalse(result["predicts_model_failure"])

    def test_warning_that_identifies_a_trap_is_flagged(self):
        result = diagnose("Watch out for the stale memo; the decoys are contracts B and C.")
        self.assertEqual(len(result["possible_scaffolding"]), 2)
        self.assertEqual({entry["category"] for entry in result["possible_scaffolding"]}, {"trap_warning"})

    def test_executable_solution_code_is_flagged(self):
        for language in ("python", "javascript", "typescript", "bash", "sh", "sql"):
            with self.subTest(language=language):
                result = diagnose(f"Solution walkthrough:\n```{language}\nsolver()\n```")
                self.assertEqual({entry["category"] for entry in result["possible_scaffolding"]}, {"solution_recipe", "solver_code"})

    def test_output_schema_and_generic_tool_help_remain_available(self):
        instruction = ('Write audit.json with {"id": "string", "consent_required": "boolean"}.\n'
            '```json\n{"type":"object","properties":{"id":{"type":"string"}}}\n```\n'
            "Inputs live in /app/environment/files. Use the native tools to read and write files.")
        self.assertEqual(diagnose(instruction)["possible_scaffolding"], [])

    def test_private_authoring_references_require_review(self):
        for reference in ("plan_challenge", "plan_portfolio", "check_draft", "evaluate_target",
                          "candidate-spec.json", "quality.capability_plan", "authoring/spec.json",
                          "tests/checks.json", "solution/submission/answer.json"):
            with self.subTest(reference=reference):
                flags = diagnose(f"Consult {reference}.")["possible_scaffolding"]
                self.assertEqual(len(flags), 1)
                self.assertEqual(flags[0]["category"], "private_authoring_reference")

    def test_private_plans_and_answers_are_not_public_diagnostic_inputs(self):
        spec = {"steps": [{"name": "01-audit", "instruction": "Audit the supplied contracts."}],
            "solution_notes": "SECRET-HOW: First join everything.",
            "quality": {"capability_plan": {"tool_baselines": "SECRET-BASELINE"}},
            "solution": {"audit.json": {"answer": "SECRET-ANSWER"}}}
        result = brief.construction_diagnostics(spec)
        self.assertEqual(result["possible_scaffolding"], [])
        self.assertNotIn("SECRET", str(result))

    def test_diagnostics_do_not_mutate_or_rewrite_the_assignment(self):
        spec = {"steps": [{"name": "01-audit", "instruction": "First read the policy. Then join records."}]}
        original = deepcopy(spec)
        result = brief.construction_diagnostics(spec)
        self.assertEqual(spec, original)
        self.assertTrue(result["private_authoring_only"])
        self.assertFalse(result["writes_public_or_reference_files"])
        self.assertTrue(result["generic_tools_and_file_access_unchanged"])

    def test_canonical_steps_are_scanned_at_their_own_boundaries(self):
        result = brief.construction_diagnostics({"steps": [
            {"name": "01-audit", "instruction": "Audit the contracts."},
            {"name": "02-revision", "instruction": "Update the report.\nThen compute the total."}]})
        self.assertEqual(result["instructions_scanned"], 2)
        self.assertEqual(result["possible_scaffolding"], [{"step": "02-revision", "category": "solution_recipe",
            "line": 2, "matched_text": "Then compute"}])

    def test_legacy_instructions_follow_the_builders_precedence(self):
        result = brief.construction_diagnostics({"instruction": "Audit the records.",
            "second_step": {"instruction": "Then join the revised records."},
            "steps": [{"name": "stale", "instruction": "First compute an old answer."}]})
        self.assertEqual(result["instructions_scanned"], 2)
        self.assertEqual([entry["step"] for entry in result["possible_scaffolding"]], ["02-revision"])

    def test_empty_and_malformed_optional_inputs_do_not_add_a_gate(self):
        for spec in ({}, {"steps": None}, {"steps": "invalid"}, {"steps": [None, {"instruction": 7}]},
                     {"instruction": "Audit the records.", "second_step": "invalid"}):
            with self.subTest(spec=spec):
                result = brief.construction_diagnostics(spec)
                self.assertFalse(result["creates_validity_blockers"])

    def test_legacy_revision_name_matches_the_compiled_public_step(self):
        result = brief.construction_diagnostics({"instruction": "Audit the records.",
            "second_step": {"name": "02-update", "instruction": "Then join the revised records."}})
        self.assertEqual(result["possible_scaffolding"][0]["step"], "02-update")

    def test_every_match_has_a_line_and_patterns_ignore_case(self):
        flags = diagnose("Audit the records.\nFIRST OPENING the summary.\nTHEN COMPARE totals.")["possible_scaffolding"]
        self.assertEqual({entry["line"] for entry in flags}, {2, 3})

    def test_silence_is_not_a_leak_free_or_semantic_certificate(self):
        result = diagnose("Examine the dossier and supply the required report.")
        self.assertFalse(result["establishes_leak_free"])
        self.assertIn("independent review", result["surface"])
        self.assertIn("English-language", result["basis"])

    def test_first_authoring_and_hardening_share_the_autonomy_guidance(self):
        for prompt in (agent_designer.SYSTEM, challenge.redesign_brief({})):
            self.assertIn("SOLVER AUTONOMY: A COMPLETE ASSIGNMENT", prompt)
            self.assertIn("The solver must know WHAT", prompt)
            self.assertIn("A REPAIR-ONLY brief still governs changes", prompt)
            self.assertIn("Changing the public brief changes the artifact", prompt)

    def test_check_draft_diagnostics_include_the_brief_profile(self):
        spec = {"steps": [{"name": "01-audit", "instruction": "Then join the evidence."}]}
        result = challenge.construction_diagnostics(spec)
        self.assertEqual(result["solver_brief"]["possible_scaffolding"][0]["category"], "solution_recipe")
        self.assertFalse(result["creates_validity_blockers"])

    def test_review_covers_fixture_walkthroughs_without_hiding_required_rules(self):
        for phrase in ("SOLVER AUTONOMY REVIEW", "all agent-visible surfaces", "walkthrough relocated",
                       "governing authority must remain public", "Naming a required governing document",
                       "unnecessary procedural hint is a difficulty", "existing validity rules",
                       "native affordances unchanged"):
            self.assertIn(phrase, review.PROMPT)


class ExportedBriefVisibility(unittest.TestCase):
    def test_export_keeps_author_plans_and_reference_notes_off_public_surfaces(self):
        with tempfile.TemporaryDirectory() as temporary:
            bundle = synthetic_bundle(Path(temporary))
            spec = json.loads((bundle / "authoring/spec.json").read_text())
            spec["solution_notes"] = "PRIVATE-SOLUTION-HOW: use this exact script."
            spec["difficulty"] = "PRIVATE-DIFFICULTY-HOW: the stale record is a decoy."
            spec["quality"] = {"private_plan": "PRIVATE-PLAN-HOW: First join records."}
            fixtures = {path.relative_to(bundle): path.read_bytes()
                for path in (bundle / "environment/files").rglob("*") if path.is_file()}
            build(spec, bundle)
            public_text = "\n".join(path.read_text() for path in (bundle / "steps").glob("*/instruction.md"))
            public_text += "\n" + "\n".join(path.read_text() for path in (bundle / "environment/files").rglob("*") if path.is_file())
            self.assertNotIn("PRIVATE-", public_text)
            self.assertIn("PRIVATE-SOLUTION-HOW", (bundle / "solution/README.md").read_text())
            self.assertIn("PRIVATE-PLAN-HOW", (bundle / "authoring/spec.json").read_text())
            self.assertIn("COPY files/ /app/environment/files/", (bundle / "environment/Dockerfile").read_text())
            self.assertEqual((bundle / "environment/.dockerignore").read_text(), "*\n!Dockerfile\n!files/\n!files/**\n")
            for path, content in fixtures.items():
                self.assertEqual((bundle / path).read_bytes(), content)

    def test_export_still_publishes_the_full_output_and_access_contract(self):
        schema = {"type": "object", "properties": {"consent_required": {"type": "boolean"}},
            "required": ["consent_required"], "additionalProperties": False}
        contract = public_contract([{"file": "audit.json", "step": "01-audit", "schema": schema}], "01-audit")
        for text in ("/app/environment/files", "/app/deliverables/audit.json", "consent_required",
                     "Duplicate keys", "Array order", '"type": "boolean"'):
            self.assertIn(text, contract)
        self.assertEqual(diagnose(contract)["possible_scaffolding"], [])


if __name__ == "__main__":
    unittest.main()
