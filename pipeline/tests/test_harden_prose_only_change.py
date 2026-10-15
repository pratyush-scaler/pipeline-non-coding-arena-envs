"""An untargeted check whose grading is unchanged may have its prose re-worded
(a-055, 2026-09-28: a fixture_intact guard's weight_basis named the new files)."""
import unittest

from pipeline.harden import revision_problems

GUARD = {"id": "guard", "kind": "guardrail", "step": "01-task", "weight": 0, "assertion": "fixture_intact",
         "actual": {"op": "fixture_intact"}, "basis": "Do not modify the sources.",
         "weight_basis": "Protects the manuscript and the manual."}
OBJ = {"id": "obj", "kind": "objective", "step": "01-task", "weight": 100, "assertion": "equals",
       "actual": {"op": "field", "file": "a.json", "path": "x"}, "target": {"op": "literal", "value": 1}}


class ProseOnly(unittest.TestCase):
    def spec(self, guard):
        return {"checks": [guard, OBJ], "steps": [{"name": "01-task"}]}

    def test_prose_only_edit_to_an_untargeted_check_is_allowed(self):
        after = {**GUARD, "weight_basis": "Protects the manuscript, the manual and the batch captures."}
        self.assertEqual(revision_problems(self.spec(GUARD), self.spec(after), [OBJ]), [])

    def test_a_graded_change_to_an_untargeted_check_is_still_refused(self):
        for field, value in (("weight", 5), ("actual", {"op": "field", "path": "y"}), ("step", "02-revision")):
            with self.subTest(field=field):
                after = {**GUARD, field: value}
                problems = revision_problems(self.spec(GUARD), self.spec(after), [OBJ])
                self.assertEqual(len(problems), 1)
                self.assertTrue(problems[0].startswith(
                    f"guard: revision changed an untargeted check (fields: {field})"))

    def test_the_finding_prints_the_original_check_for_a_verbatim_restore(self):
        import json
        after = {**GUARD, "actual": {"op": "fixture_files"}, "dimension": "renamed"}
        [problem] = revision_problems(self.spec(GUARD), self.spec(after), [OBJ])
        self.assertIn("(fields: actual, dimension)", problem)
        printed = json.loads(problem.split("-- restore it exactly as: ", 1)[1])
        self.assertEqual(printed, GUARD)


if __name__ == "__main__":
    unittest.main()
