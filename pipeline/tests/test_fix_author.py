"""Regression tests for six authoring defects fixed 2026-09-24.

Each test fails on the behaviour it replaces:

1. normalisation folded wrong answers into right ones (`3.10` -> 3.1, `1,2,3`
   -> 123, `- 1,200` -> 1200, `1_000` -> 1000.0)
2. `[]` paths were undeliverable, the shipped solve.py was never executed, and
   it wrote its derived rows into /solution
3. two runtime file lists, two staging helpers, no identity gate
4. breadth named a nonexistent assertion and copied quality's band literals
5. the one-shot designer path
6. a fault reading the agent's submission raised (void) instead of scoring 0
"""
from __future__ import annotations

import copy
import json
import stat
import tempfile
import unittest
from pathlib import Path

from pipeline.author import checks, runtime, solution
from pipeline.author.build import build
from pipeline.author.checks import (Check, CheckError, PathUnassignable, Workspace,
                                    _as_set, _dig, assign_path, grade, normalise,
                                    run_check)

CSV = "ticket,status,effort\nR-21,open,3\nR-22,closed,8\nR-23,open,5\n"
INSTRUCTION = ("Leave tickets.csv unchanged. Write summary.json with open, one "
               "object per open ticket carrying its ticket ID and effort, and "
               "total_effort, the sum of effort for open rows.")


def row_spec() -> dict:
    """A spec whose scored fields sit behind `[]` paths."""
    open_rows = {"op": "rows", "file": "tickets.jsonl",
                 "where": {"field": "status", "eq": "open"}}
    objective = lambda cid, path, target, assertion="equals": {
        "id": cid, "kind": "objective", "weight": 1, "basis": INSTRUCTION,
        "assertion": assertion, "target": target,
        "actual": {"op": "field", "file": "summary.json", "path": path}}
    return {
        "name": "Open ticket rows", "description": "List open work.",
        "source": {"session_id": "synthetic-public-example", "seed_index": 0},
        "steps": [{"name": "01-summary", "instruction": INSTRUCTION}],
        "projections": [{"file": "tickets.csv", "parser": "csv_table",
                         "as": "tickets.jsonl"}],
        "checks": [
            {"id": "source_unchanged", "kind": "guardrail", "weight": 0,
             "basis": "Leave tickets.csv unchanged.", "assertion": "fixture_intact",
             "actual": {"op": "literal", "value": True}},
            objective("open_ids", "open[].ticket",
                      {"op": "pluck", "of": open_rows, "field": "ticket"}, "set_equals"),
            objective("open_effort", "open[].effort",
                      {"op": "pluck", "of": open_rows, "field": "effort"}),
            objective("total_effort", "total_effort",
                      {"op": "sum", "of": open_rows, "field": "effort"}),
        ],
        "traps": [],
        "solution": {"summary.json": {
            "open": [{"ticket": "R-21", "effort": "3"}, {"ticket": "R-23", "effort": "5"}],
            "total_effort": 8}},
    }


class NormalisationOnlyFoldsCanonicalNumbers(unittest.TestCase):
    def test_distinct_spellings_stay_distinct(self):
        for text, wrong in (("3.10", 3.1), ("007", 7), ("1,2,3", 123),
                            ("12,34", 1234), ("1_000", 1000), ("- 1,200", 1200)):
            with self.subTest(text=text):
                self.assertNotEqual(normalise(text), wrong)

    def test_section_sets_do_not_collapse(self):
        self.assertNotEqual(_as_set(["3.1", "3.10"]), _as_set(["3.1"]))

    def test_the_published_folds_still_hold(self):
        self.assertEqual(normalise("1960"), 1960)          # kw-002
        self.assertEqual(normalise(json.loads('"1960"')), normalise(1960))
        self.assertEqual(normalise(" 1,250 "), 1250)       # thousands separator
        self.assertEqual(normalise("-1,200.5"), -1200.5)
        self.assertEqual(normalise("0.5"), 0.5)
        self.assertEqual(normalise("0"), 0)
        self.assertEqual(normalise("## 5. PHYSICAL"), normalise("5. PHYSICAL"))
        self.assertEqual(normalise("- item"), "item")

    def test_arithmetic_still_reads_spelled_numbers(self):
        self.assertEqual(checks._num(normalise("1.50")), 1.5)
        self.assertEqual(checks._num(normalise("007")), 7)
        with self.assertRaises(CheckError):
            checks._num(normalise("1_000"))


class OnePathAssignerInvertsTheReader(unittest.TestCase):
    CASES = [("a", 3), ("a.b.c", "x"), ("$.a.b", [1, 2]), ("rows[].id", ["r1", "r2"]),
             ("outer.rows[].tags", [["x"], []]), ("g[].items[].n", [[1, 2], [3]]),
             ("list.1", "second")]

    def test_round_trip(self):
        for path, value in self.CASES:
            with self.subTest(path=path):
                start = {"list": ["first", None]} if path.startswith("list") else {}
                self.assertEqual(_dig(assign_path(start, path, value), path), value)

    def test_sibling_fields_fill_the_same_rows(self):
        doc = assign_path({}, "rows[].id", ["a", "b"])
        doc = assign_path(doc, "rows[].n", [1, 2])
        self.assertEqual(doc, {"rows": [{"id": "a", "n": 1}, {"id": "b", "n": 2}]})
        self.assertNotIn("rows[]", doc)

    def test_a_list_path_refuses_a_scalar(self):
        with self.assertRaises(PathUnassignable):
            assign_path({}, "rows[].id", "a")

    def test_the_plan_delivers_list_paths(self):
        plan = solution.plan(row_spec(), "01-summary")
        self.assertEqual(plan["undeliverable"], [])
        self.assertEqual({o["path"] for o in plan["objectives"]},
                         {"open[].ticket", "open[].effort", "total_effort"})


class ShippedReferenceIsExecuted(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.bundle = Path(self.temp.name) / "built"
        fixture = self.bundle / "environment" / "files"
        fixture.mkdir(parents=True)
        (fixture / "tickets.csv").write_text(CSV)
        build(row_spec(), self.bundle)

    def test_the_generated_solve_py_scores_full_marks_offline(self):
        from pipeline.verify_shipped import run_reference
        result = run_reference(self.bundle)
        self.assertEqual(result["problems"], [])
        self.assertEqual(result["steps"], {"01-summary": 1.0})

    def test_solve_py_never_writes_into_its_own_directory(self):
        source = solution.SOLVE_PY
        self.assertIn("tempfile.TemporaryDirectory", source)
        self.assertNotIn('HERE / "derived"', source)
        # run_reference executes from a read-only copy; the pass above proves it.

    def test_a_reference_that_does_not_score_is_blocked(self):
        from pipeline.verify_shipped import run_reference
        plan_file = self.bundle / "steps/01-summary/solution/solution-plan.json"
        plan = json.loads(plan_file.read_text())
        plan["objectives"] = [o for o in plan["objectives"] if o["id"] != "open_ids"]
        plan_file.write_text(json.dumps(plan))
        result = run_reference(self.bundle)
        self.assertTrue(any("not 1.0" in p and "open_ids" in p for p in result["problems"]),
                        result)
        self.assertTrue(any("not 1.0" in p for p in solution.problems(self.bundle)))

    def test_a_crashing_reference_is_blocked_not_skipped(self):
        from pipeline.verify_shipped import run_reference
        solve = self.bundle / "steps/01-summary/solution/solve.py"
        solve.write_text(solve.read_text().replace("def main() -> int:\n",
                                                   "def main() -> int:\n    raise SystemExit(3)\n"))
        self.assertTrue(any("exited 3" in p for p in run_reference(self.bundle)["problems"]))


class RuntimeCopiesAreOneGenerator(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.bundle = Path(self.temp.name) / "built"
        fixture = self.bundle / "environment" / "files"
        fixture.mkdir(parents=True)
        (fixture / "tickets.csv").write_text(CSV)
        build(row_spec(), self.bundle)

    def test_both_copies_are_identical_after_build(self):
        self.assertEqual(runtime.problems(self.bundle), [])
        tests = self.bundle / "tests/_arena_runtime"
        sol = self.bundle / "steps/01-summary/solution/_arena_runtime"
        for rel in runtime.expected():
            self.assertEqual((tests / rel).read_bytes(), (sol / rel).read_bytes(), rel)

    def test_a_drifted_solution_copy_is_reported(self):
        (self.bundle / "steps/01-summary/solution/_arena_runtime/oracle.py").write_text("# stale\n")
        issues = runtime.problems(self.bundle)
        self.assertTrue(any("solution/_arena_runtime/oracle.py differs" in i for i in issues), issues)
        self.assertTrue(any("differs" in i for i in solution.problems(self.bundle)))

    def test_there_is_one_file_list(self):
        self.assertIs(solution.RUNTIME, runtime.FILES)


class BreadthReadsItsConstantsFromTheirOwners(unittest.TestCase):
    def test_exact_assertions_exist(self):
        from pipeline import breadth
        self.assertLessEqual(set(breadth.EXACT_ASSERTIONS), set(checks.ASSERTIONS))

    def test_bands_are_quality_bands(self):
        from pipeline import breadth
        from pipeline.author import quality
        self.assertIs(breadth.BANDS, quality.BAND_LIMITS)


class OneShotDesignerIsGone(unittest.TestCase):
    def test_removed_names(self):
        from pipeline.author import designer
        for name in ("SYSTEM", "_brief", "MAX_REPAIRS"):
            self.assertFalse(hasattr(designer, name), name)

    def test_shared_names_still_import(self):
        from pipeline.author.designer import (CALL_DEADLINE_S, CATEGORY_GUIDANCE, MODEL,  # noqa: F401
                                              SPEC_TOOL, _call, _consume_stream, _step_name,
                                              derive_solution, design, request_slot,
                                              verify_solution)

    def test_derive_solution_no_longer_assembles_targets(self):
        from pipeline.author.designer import derive_solution
        spec = copy.deepcopy(row_spec())
        with tempfile.TemporaryDirectory() as tmp:
            bundle = Path(tmp)
            (bundle / "environment/files").mkdir(parents=True)
            (bundle / "environment/files/tickets.csv").write_text(CSV)
            with self.assertRaises(ValueError):
                derive_solution(spec, bundle)


class SubmissionFaultsScoreZero(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        root = Path(self.temp.name)
        self.source, self.submitted = root / "source", root / "submitted"
        self.source.mkdir()
        self.submitted.mkdir()
        (self.source / "rows.json").write_text(json.dumps([{"n": 1}, {"n": 2}]))
        self.ws = Workspace(source=self.source, submitted=self.submitted)

    def check(self, **overrides) -> Check:
        base = dict(id="total", kind="objective", weight=1, basis="Report the total.",
                    assertion="equals",
                    target={"op": "sum", "of": {"op": "rows", "file": "rows.json"}, "field": "n"},
                    actual={"op": "sum", "of": {"op": "rows", "file": "rows.json"}, "field": "n"})
        base.update(overrides)
        return Check(**base)

    def test_unsummable_submission_is_a_failed_check(self):
        (self.submitted / "rows.json").write_text(json.dumps([{"n": "lots"}]))
        result = run_check(self.check(), self.ws)
        self.assertFalse(result["passed"])
        self.assertTrue(result["submission_error"])
        self.assertIn("submission error", result["reason"])
        self.assertEqual(grade([self.check()], self.ws)["reward"], 0.0)

    def test_scalar_where_rows_were_needed_is_a_failed_check(self):
        (self.submitted / "rows.json").write_text(json.dumps({"n": 3}))
        self.assertFalse(run_check(self.check(), self.ws)["passed"])

    def test_a_target_fault_is_still_a_grader_error(self):
        (self.submitted / "rows.json").write_text(json.dumps([{"n": 3}]))
        (self.source / "rows.json").write_text(json.dumps([{"n": "lots"}]))
        with self.assertRaises(CheckError):
            run_check(self.check(), self.ws)


if __name__ == "__main__":
    unittest.main()
