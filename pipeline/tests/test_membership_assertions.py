"""contains / absent / present compare values, not Python reprs of values.

Found by review against delivered bundles: a `$` path read a key literally
named "$" so its guardrail could never fire; `absent` compared whole row
objects against strings so it never matched; `contains` compared list reprs,
failing a correct superset or a reordering.
"""
import unittest

from pipeline.author.checks import _dig, _found, _members


def contains(target, actual):
    return all(_found(m, actual) for m in _members(target))


def absent(target, actual):
    return not any(_found(m, actual) for m in _members(target))


class MembershipAssertions(unittest.TestCase):
    def test_dollar_is_the_document_root(self):
        doc = {"a": 1}
        self.assertEqual(_dig(doc, "$"), doc)
        self.assertEqual(_dig({"x": {"y": 2}}, "$.x.y"), 2)

    def test_absent_searches_inside_row_objects(self):
        rows = [{"item": "8/15 submit the application", "status": "done"}]
        self.assertFalse(absent(["8/15 submit the application"], rows))
        self.assertTrue(absent(["something else"], rows))

    def test_contains_accepts_order_and_supersets(self):
        target = ["alpha 2020", "beta 2021"]
        for actual in (["beta 2021", "alpha 2020"], ["zeta", "alpha 2020", "beta 2021"]):
            self.assertTrue(contains(target, actual), actual)
        self.assertFalse(contains(target, ["alpha 2020"]))

    def test_numbers_match_as_whole_numbers(self):
        self.assertTrue(absent("5", "15 rooms"))
        self.assertFalse(contains("0", ["batch 1", "batch 10"]))
        self.assertTrue(contains("1,250", "Total due: 1,250 HKD"))
        self.assertTrue(contains(7, [7]))


class NumeralsFollowTheTargetsType(unittest.TestCase):
    """A number written differently matches; text that looks numeric does not."""

    def eq(self, actual, target):
        from pipeline.author.checks import _as_target_type, _hashable, normalise
        return _hashable(_as_target_type(normalise(actual), target)) == _hashable(normalise(target))

    def test_numbers_written_differently_match(self):
        self.assertTrue(self.eq("12.50", 12.5))
        self.assertTrue(self.eq("1,250", 1250))
        self.assertTrue(self.eq(["2.0", "3"], [2, 3]))
        self.assertTrue(self.eq("1960", 1960))

    def test_section_numbers_stay_distinct(self):
        self.assertFalse(self.eq("3.10", "3.1"))


class ViolatedGuardrailSettlesTheScore(unittest.TestCase):
    """A target that cannot be computed after a guardrail fired is not a crash."""

    def test_reward_is_zero_not_a_grader_error(self):
        from unittest.mock import patch
        from pipeline.author import checks as c
        guard = c.Check(id="g", kind="guardrail", weight=0, basis="b", assertion="fixture_intact", actual={})
        objective = c.Check(id="o", kind="objective", weight=10, basis="b", assertion="equals", actual={})

        def fake(check, ws):
            if check.kind == "guardrail":
                return {"id": check.id, "passed": False}
            raise c.CheckError("target unreadable over a damaged fixture")
        ws = type("W", (), {"outputs": None, "derived": None, "submitted": None, "step": None})()
        with patch.object(c, "run_check", side_effect=fake):
            out = c.grade([guard, objective], ws)
        self.assertEqual(out["reward"], 0.0)
        with patch.object(c, "run_check", side_effect=lambda check, ws: (_ for _ in ()).throw(c.CheckError("x"))
                          if check.kind == "objective" else {"id": check.id, "passed": True}):
            with self.assertRaises(c.CheckError):       # no guardrail fired: still a grader error
                c.grade([guard, objective], ws)
