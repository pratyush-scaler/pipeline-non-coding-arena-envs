"""Public-contract fixtures and clean, repository-free grader executions.

Expected answers below are calculated directly from the three public CSV rows.
They do not use the builder's reference solution or oracle to decide correctness.
"""

from __future__ import annotations

import copy
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from pipeline.author import oracle
from pipeline.author.build import build
from pipeline.author.checks import CheckError, Workspace, grade, load


CSV = "ticket,status,effort\nR-21,open,3\nR-22,closed,8\nR-23,open,5\n"
INSTRUCTION = (
    "Leave tickets.csv unchanged. Write summary.json with open_ids, the ticket "
    "IDs for every open row in any order; open_count, the number of open rows; "
    "and total_effort, the sum of effort for open rows only."
)


def sample_spec() -> dict:
    open_rows = {"op": "rows", "file": "tickets.jsonl",
                 "where": {"field": "status", "eq": "open"}}
    targets = {
        "open_ids": {"op": "pluck", "of": open_rows, "field": "ticket"},
        "open_count": {"op": "count", "of": open_rows},
        "total_effort": {"op": "sum", "of": open_rows, "field": "effort"},
    }
    checks = [{"id": "source_unchanged", "kind": "guardrail", "weight": 0,
               "basis": "Leave tickets.csv unchanged.",
               "assertion": "fixture_intact", "actual": {"op": "literal",
                                                          "value": True}}]
    for key, target in targets.items():
        checks.append({
            "id": key, "kind": "objective", "weight": 1,
            "basis": INSTRUCTION, "assertion": (
                "set_equals" if key == "open_ids" else "equals"),
            "actual": {"op": "field", "file": "summary.json", "path": key},
            "target": target,
        })
    return {
        "name": "Open ticket summary", "description": "Summarise open work.",
        "source": {"session_id": "synthetic-public-example", "seed_index": 0},
        "steps": [{"name": "01-summary", "instruction": INSTRUCTION}],
        "projections": [{"file": "tickets.csv", "parser": "csv_table",
                         "as": "tickets.jsonl"}],
        "checks": checks, "traps": [],
        "solution": {"summary.json": {"open_ids": ["R-21", "R-23"],
                                      "open_count": 2, "total_effort": 8}},
    }


class ExportedGrader(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.bundle = self.root / "built"
        self.fixture = self.bundle / "environment" / "files"
        self.fixture.mkdir(parents=True)
        (self.fixture / "tickets.csv").write_text(CSV)
        self.spec = sample_spec()
        build(self.spec, self.bundle)
        self.submitted = self.root / "submitted"
        self.submitted.mkdir()
        self.cwd = self.root / "unrelated-cwd"
        self.cwd.mkdir()

    def submit(self, value: dict):
        (self.submitted / "summary.json").write_text(json.dumps(value))

    def local(self, bundle: Path | None = None) -> dict:
        bundle = bundle or self.bundle
        pfile = bundle / "tests" / "projections.json"
        projections = (json.loads(pfile.read_text())["projections"]
                       if pfile.is_file() else None)
        derived = bundle / "tests" / "derived"
        return grade(load(bundle / "tests" / "checks.json"), Workspace(
            source=bundle / "environment" / "files", submitted=self.submitted,
            derived=derived if derived.is_dir() else None,
            projections=projections))

    def exported(self, bundle: Path | None = None) -> subprocess.CompletedProcess:
        bundle = bundle or self.bundle
        reward = self.root / "reward.json"
        reward.unlink(missing_ok=True)
        env = {key: value for key, value in os.environ.items()
               if key not in {"PYTHONPATH", "PYTHONHOME"}}
        env.update(ARENA_SOURCE=str(bundle / "environment" / "files"),
                   ARENA_SUBMITTED=str(self.submitted), ARENA_REWARD=str(reward))
        return subprocess.run(
            [sys.executable, "-I", str(bundle / "tests" / "criteria.py")],
            cwd=self.cwd, env=env, text=True, capture_output=True, timeout=15)

    def assert_parity(self, expected: float, bundle: Path | None = None) -> dict:
        result = self.exported(bundle)
        self.assertEqual(result.returncode, 0, result.stderr)
        exported = json.loads(result.stdout)
        self.assertEqual(exported, self.local(bundle))
        self.assertEqual(exported["reward"], expected)
        self.assertEqual(json.loads((self.root / "reward.json").read_text()),
                         {"reward": expected})
        return exported

    def test_correct_independent_submission_and_clean_delivery(self):
        self.submit({"open_ids": ["R-21", "R-23"],
                     "open_count": 2, "total_effort": 8})
        # A delivery has no pipeline checkout, authoring files or solution.
        delivery = self.root / "delivery"
        shutil.copytree(self.bundle / "tests", delivery / "tests")
        shutil.copytree(self.bundle / "environment", delivery / "environment")
        result = self.assert_parity(1.0, delivery)
        self.assertTrue(all(row["passed"] for row in result["checks"].values()))

    def test_generated_reference_also_works_in_standalone_grader(self):
        shutil.copyfile(self.bundle / "solution" / "submission" / "summary.json",
                        self.submitted / "summary.json")
        self.assert_parity(1.0)

    def test_equivalent_allowed_answer_is_accepted(self):
        # Public instructions allow either ID order and do not require strict
        # numeric JSON types. This answer is independent of the stored solution.
        self.submit({"open_ids": ["R-23", "R-21"],
                     "open_count": " 2 ", "total_effort": "8"})
        self.assert_parity(1.0)

    def test_numbered_markdown_evidence_passes_objective_and_guardrail(self):
        self.spec["checks"].append({
            "id": "no_invented_ids", "kind": "guardrail", "weight": 0,
            "basis": "Every submitted ticket ID must occur in the source.",
            "assertion": "subset_of",
            "actual": {"op": "field", "file": "summary.json", "path": "open_ids"},
            "target": {"op": "pluck", "of": {"op": "rows", "file": "tickets.jsonl"}, "field": "ticket"}})
        build(self.spec, self.bundle)
        self.submit({"open_ids": ["4. R-21", "5) R-23"], "open_count": 2, "total_effort": 8})
        self.assert_parity(1.0)
        self.submit({"open_ids": ["4. R-21", "5) R-99"], "open_count": 2, "total_effort": 8})
        result = self.assert_parity(0.0)
        self.assertIn("no_invented_ids", result["guardrails_violated"])

    def test_list_normalization_preserves_decimal_values_and_nonlist_identifiers(self):
        from pipeline.author.checks import normalise
        for value in ("4.5 hours", "4.R-21", "5)R-23", "1234567890. Report"):
            with self.subTest(value=value):
                self.assertEqual(normalise(value), value.casefold())

    def test_plausible_wrong_submission_fails(self):
        # Counting closed work is a substantive error, even if JSON is valid.
        self.submit({"open_ids": ["R-21", "R-22", "R-23"],
                     "open_count": 3, "total_effort": 16})
        result = self.assert_parity(0.0)
        self.assertTrue(result["checks"]["source_unchanged"]["passed"])
        self.assertTrue(all(not result["checks"][key]["passed"] for key in
                            ("open_ids", "open_count", "total_effort")))

    def test_empty_submission_fails_objectives_without_fault(self):
        self.assert_parity(0.0)

    def test_invalid_submission_json_fails_objectives_without_fault(self):
        (self.submitted / "summary.json").write_text("this is not JSON")
        self.assert_parity(0.0)

    def test_fixture_changes_trigger_delivered_guardrail(self):
        self.submit({"open_ids": ["R-21", "R-23"],
                     "open_count": 2, "total_effort": 8})
        (self.fixture / "tickets.csv").write_text(CSV.replace("R-21,open,3",
                                                              "R-21,closed,3"))
        result = self.assert_parity(0.0)
        self.assertEqual(result["guardrails_violated"], ["source_unchanged"])

    def test_missing_projection_metadata_is_an_error_not_a_score(self):
        (self.bundle / "tests" / "projections.json").unlink()
        result = self.exported()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("projections metadata", result.stderr)
        self.assertFalse((self.root / "reward.json").exists())

    def test_missing_oracle_dependency_cannot_silently_pass(self):
        (self.bundle / "tests" / "_arena_runtime" / "oracle.py").unlink()
        result = self.exported()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("ModuleNotFoundError", result.stderr)
        self.assertFalse((self.root / "reward.json").exists())

    def test_nonprojected_package_needs_no_projection_metadata(self):
        # Removing the projection must remain valid for source CSV expressions.
        spec = copy.deepcopy(self.spec)
        spec["projections"] = []
        spec["checks"] = spec["checks"][1:]
        for check in spec["checks"]:
            check["target"]["of"]["file"] = "tickets.csv"
        build(spec, self.bundle)
        self.submit({"open_ids": ["R-21", "R-23"],
                     "open_count": 2, "total_effort": 8})
        self.assert_parity(1.0)
        self.assertFalse((self.bundle / "tests" / "derived").exists())
        self.assertFalse((self.bundle / "tests" / "projections.json").exists())

    def test_ordered_public_requirement_uses_ordered_comparison(self):
        spec = copy.deepcopy(self.spec)
        spec["steps"][0]["instruction"] = INSTRUCTION.replace(
            "in any order", "in their CSV order")
        spec["checks"][1]["assertion"] = "equals"
        spec["checks"][1]["basis"] = spec["steps"][0]["instruction"]
        build(spec, self.bundle)
        self.submit({"open_ids": ["R-23", "R-21"],
                     "open_count": 2, "total_effort": 8})
        # Largest-remainder weights make IDs worth 34 of the 100 points.
        self.assert_parity(0.66)

    def test_unordered_exact_rows_reject_duplicates_without_rejecting_reordering(self):
        spec = copy.deepcopy(self.spec)
        spec["checks"][1]["assertion"] = "multiset_equals"
        build(spec, self.bundle)
        for ids, reward in [
            (["R-23", "R-21"], 1.0),
            (["R-21", "R-23", "R-21"], 0.66),
            (["R-21", "R-23", " r-21 "], 0.66),
            (["R-21", "R-21"], 0.66),
            ("R-21", 0.66),
        ]:
            with self.subTest(ids=ids):
                self.submit({"open_ids": ids, "open_count": 2, "total_effort": 8})
                self.assert_parity(reward)

    def test_unordered_rows_preserve_source_multiplicity_and_keyed_values(self):
        (self.fixture / "tickets.csv").write_text(CSV + "R-21,open,3\n")
        spec = copy.deepcopy(self.spec)
        check = spec["checks"][1]
        check["assertion"] = "multiset_equals"
        check["target"] = {"op": "select", "of": check["target"]["of"],
                           "fields": {"id": "ticket", "hours": "effort"}}
        a, b = {"id": "R-21", "hours": 3}, {"id": "R-23", "hours": 5}
        spec["solution"]["summary.json"] = {
            "open_ids": [a, b, a], "open_count": 3, "total_effort": 11}
        build(spec, self.bundle)
        for rows, reward in [
            ([b, {"id": " r-21 ", "hours": "3"}, a], 1.0),
            ([a, b], 0.66),
            ([a, b, b], 0.66),
            ([a, {"id": "R-21", "hours": 5}, {"id": "R-23", "hours": 3}], 0.66),
        ]:
            with self.subTest(rows=rows):
                self.submit({"open_ids": rows, "open_count": 3, "total_effort": 11})
                self.assert_parity(reward)

    def test_rebuild_removes_retired_projections_and_same_step_handoff(self):
        spec = copy.deepcopy(self.spec)
        spec["steps"][0]["handoff"] = {"mode": "carry_files"}
        build(spec, self.bundle)
        derived = self.bundle / "tests" / "derived"
        handoff = self.bundle / "steps" / "01-summary" / "handoff.json"
        self.assertTrue(handoff.is_file())
        (derived / "retired.jsonl").write_text('{"old": true}\n')
        # User-owned extraction and original source content must survive.
        extraction = self.bundle / "authoring" / "extraction"
        extraction.mkdir()
        (extraction / "source.md").write_text("Original extraction")
        build(self.spec, self.bundle)
        self.assertFalse(handoff.exists())
        self.assertFalse((derived / "retired.jsonl").exists())
        self.assertTrue((derived / "tickets.jsonl").is_file())
        self.assertEqual((self.fixture / "tickets.csv").read_text(), CSV)
        self.assertEqual((extraction / "source.md").read_text(),
                         "Original extraction")

    def test_rebuild_with_changed_dimensions_matches_a_fresh_export(self):
        from pipeline.assurance import generated_problems
        from pipeline.artifacts import inventory
        spec = copy.deepcopy(self.spec)
        for check in spec["checks"]:
            if check["kind"] == "objective":
                check["dimension"] = "work_summary"
        self.assertTrue((self.bundle / "tests/core/README.md").is_file())
        build(spec, self.bundle)
        self.assertFalse((self.bundle / "tests/core").exists())
        self.assertTrue((self.bundle / "tests/work_summary/README.md").is_file())
        self.assertEqual(generated_problems(self.bundle), [])
        before = inventory(self.bundle)
        build(spec, self.bundle)
        self.assertEqual(inventory(self.bundle), before)

    def test_a_delivered_task_toml_still_reproduces_exactly(self):
        # Regression: `deliver` renames the task and stamps its level, and the
        # export check compared that against a plain rebuild -- so every
        # delivered bundle failed its own gate chain. Any OTHER edit must still fail.
        from pipeline import naming
        from pipeline.assurance import generated_problems
        import tomllib
        toml = self.bundle / "task.toml"
        name = tomllib.loads(toml.read_text())["task"]["name"]
        toml.write_text(naming.delivered_toml(toml.read_text(), name, "F3"))
        self.assertEqual(generated_problems(self.bundle), [])
        toml.write_text(toml.read_text().replace('"F3"', '"F3"\nextra = "edit"', 1))
        self.assertEqual(generated_problems(self.bundle),
                         ["export differs from reviewed spec/generator: task.toml"])

    def test_retiring_a_dimension_preserves_unrecognised_files_for_review(self):
        from pipeline.assurance import generated_problems
        notes = self.bundle / "tests/core/audit-notes.txt"
        notes.write_text("Retained evidence")
        custom = self.bundle / "tests/custom-review/README.md"
        custom.parent.mkdir()
        custom.write_text("Independent review")
        spec = copy.deepcopy(self.spec)
        for check in spec["checks"]:
            if check["kind"] == "objective":
                check["dimension"] = "work_summary"
        build(spec, self.bundle)
        self.assertFalse((self.bundle / "tests/core/README.md").exists())
        self.assertEqual(notes.read_text(), "Retained evidence")
        self.assertEqual(custom.read_text(), "Independent review")
        self.assertEqual(generated_problems(self.bundle), [
            "export differs from reviewed spec/generator: tests/core/audit-notes.txt",
            "export differs from reviewed spec/generator: tests/custom-review/README.md",
        ])

    def test_rebuild_does_not_follow_derived_directory_symlink(self):
        derived = self.bundle / "tests" / "derived"
        shutil.rmtree(derived)
        outside = self.root / "outside-derived"
        outside.mkdir()
        (outside / "keep.jsonl").write_text("keep me")
        derived.symlink_to(outside, target_is_directory=True)
        with self.assertRaisesRegex(ValueError, "symlinks"):
            build(self.spec, self.bundle)
        self.assertTrue(derived.is_symlink())
        self.assertEqual((outside / "keep.jsonl").read_text(), "keep me")


class FileBoundaries(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.files = self.root / "data"
        self.files.mkdir()
        self.sibling = self.root / "database"
        self.sibling.mkdir()
        (self.files / "allowed.txt").write_text("public")
        (self.sibling / "secret.txt").write_text("private")
        self.ws = Workspace(source=self.files, submitted=self.files)

    def test_only_canonical_regular_internal_paths_are_readable(self):
        (self.files / "nested").mkdir()
        (self.files / "inside.txt").symlink_to(self.files / "allowed.txt")
        self.assertEqual(self.ws.read("allowed.txt", "submitted"), "public")
        for file in ("nested/../allowed.txt", "inside.txt"):
            with self.subTest(file=file):
                with self.assertRaises(CheckError):
                    self.ws.read(file, "submitted")

    def test_sibling_prefix_and_parent_traversal_are_rejected(self):
        for file in ("../database/secret.txt", "../../secret.txt",
                     str(self.sibling / "secret.txt")):
            for role in ("source", "submitted"):
                with self.subTest(file=file, role=role):
                    with self.assertRaisesRegex(CheckError, "path escapes"):
                        self.ws.read(file, role)

    def test_symlink_escape_is_rejected(self):
        (self.files / "shortcut").symlink_to(self.sibling,
                                            target_is_directory=True)
        for role in ("source", "submitted"):
            with self.subTest(role=role):
                with self.assertRaisesRegex(CheckError, "path escapes"):
                    self.ws.read("shortcut/secret.txt", role)

    def test_derived_root_enforces_its_own_boundary(self):
        derived = self.root / "derived"
        derived.mkdir()
        (derived / "secret.txt").symlink_to(self.sibling / "secret.txt")
        ws = Workspace(source=self.files, submitted=self.files, derived=derived)
        with self.assertRaisesRegex(CheckError, "path escapes"):
            ws.read("secret.txt", "source")

    def test_projection_cannot_read_outside_fixture(self):
        (self.files / "shortcut").symlink_to(self.sibling,
                                            target_is_directory=True)
        for file in ("../database/secret.txt", "shortcut/secret.txt"):
            with self.subTest(file=file):
                with self.assertRaises(ValueError):
                    oracle.project(self.files, [{"file": file,
                                   "as": "rows.jsonl", "parser": "labelled_lines"}])

    def test_projection_cannot_write_outside_derived(self):
        with self.assertRaises(ValueError):
            oracle.write({"../database/new.jsonl": [{"private": True}]}, self.files)
        self.assertFalse((self.sibling / "new.jsonl").exists())


if __name__ == "__main__":
    unittest.main()
