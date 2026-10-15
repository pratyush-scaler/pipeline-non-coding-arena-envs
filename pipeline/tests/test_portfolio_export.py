"""Small supported portfolio expressions work through the shipped grader, not a judge."""
from copy import deepcopy
import json
from pathlib import Path
import tempfile
import unittest

from pipeline.artifacts import atomic_json
from pipeline.author.build import build
from pipeline.evaluate import exported_grade
from pipeline.tests.test_production import synthetic_bundle
from pipeline.verify_shipped import run_reference


def row_field(path):
    return {"op": "field", "path": path}


def sentinel(value):
    return {"op": "literal", "value": value, "why": "The public report contract fixes this boolean or non-applicable null."}


def portfolio_target():
    bound = {"op": "bind_rows", "of": {"op": "rows", "file": "clauses.json"}, "fields": {
        "equity": {"op": "field", "file": "deal.json", "path": "equity"},
        "closing": {"op": "field", "file": "deal.json", "path": "closing"}}}
    triggers = {"op": "derive_rows", "of": bound, "fields": {
        "id": row_field("id"), "waived": row_field("waived"), "closing": row_field("closing"),
        "notice_offset": row_field("notice_offset"), "triggered": {"op": "compare", "value_type": "number",
            "comparison": "gt", "a": row_field("equity"), "b": row_field("threshold")}}}
    return {"op": "derive_rows", "of": triggers, "fields": {
        "id": row_field("id"), "triggered": row_field("triggered"),
        "consent_required": {"op": "if", "where": {"field": "triggered", "eq": False}, "then": sentinel(False),
            "else": {"op": "if", "where": {"field": "waived", "eq": True}, "then": sentinel(False), "else": sentinel(True)}},
        "notice_deadline": {"op": "if", "where": {"field": "triggered", "eq": False}, "then": sentinel(None),
            "else": {"op": "date_add", "date": row_field("closing"), "days": row_field("notice_offset")}}}}


def conclusions():
    return [{"id": "Alpha", "triggered": True, "consent_required": True, "notice_deadline": "2026-12-01"},
        {"id": "Beta", "triggered": False, "consent_required": False, "notice_deadline": None},
        {"id": "Gamma", "triggered": True, "consent_required": False, "notice_deadline": "2026-12-26"}]


class PortfolioExport(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.bundle = synthetic_bundle(self.root)
        self.clauses = [{"id": "Alpha", "threshold": 50, "notice_offset": -30, "waived": False},
            {"id": "Beta", "threshold": 60, "notice_offset": -10, "waived": False},
            {"id": "Gamma", "threshold": 35, "notice_offset": -5, "waived": True}]
        atomic_json(self.bundle / "environment/files/clauses.json", self.clauses)
        atomic_json(self.bundle / "environment/files/deal.json", {"equity": 55, "closing": "2026-12-31"})
        self.spec = json.loads((self.bundle / "authoring/spec.json").read_text())
        instruction = ("Under this fictional contractual rule, equity must strictly exceed each threshold to trigger. "
            "A triggered agreement requires consent unless its waiver is true. Triggered agreements require notice "
            "even when consent is waived. notice_offset is a signed number of calendar days from committed closing; "
            "negative means before closing. The calendar date is obtained by adding that signed offset, with no "
            "business-day adjustment. If not triggered, consent_required is false and notice_deadline is null. "
            "Write audit.json with conclusions, one row per clause ID, in any order, each containing "
            "id, triggered, consent_required and notice_deadline. Leave all fixture files unchanged.")
        self.spec["steps"] = [{"name": "01-audit", "instruction": instruction}]
        self.spec["projections"] = []
        self.spec["checks"] = [self.spec["checks"][0], {"id": "obligations", "kind": "objective", "weight": 1,
            "basis": instruction, "weight_basis": "Joint contractual conclusions, not a separate point for each dependent field.",
            "assertion": "multiset_equals", "actual": {"op": "field", "file": "audit.json", "path": "conclusions"},
            "target": portfolio_target()}]
        self.spec["checks"][0]["step"] = "01-audit"
        row_schema = {"type": "object", "properties": {"id": {"type": "string"}, "triggered": {"type": "boolean"},
            "consent_required": {"type": "boolean"}, "notice_deadline": {"type": ["string", "null"]}},
            "required": ["id", "triggered", "consent_required", "notice_deadline"], "additionalProperties": False}
        self.spec["outputs"] = [{"file": "audit.json", "step": 1, "schema": {"type": "object",
            "properties": {"conclusions": {"type": "array", "items": row_schema}},
            "required": ["conclusions"], "additionalProperties": False}}]
        self.spec["solution"] = {"audit.json": {"conclusions": conclusions()}}
        build(self.spec, self.bundle)

    def grade(self, rows):
        submitted = self.root / "submitted"
        atomic_json(submitted / "audit.json", {"conclusions": rows})
        return exported_grade(self.bundle, submitted, "01-audit")["reward"]

    def test_correct_reordered_answers_pass_and_untouched_workspace_gets_zero(self):
        self.assertEqual(self.grade(conclusions()), 1)
        self.assertEqual(self.grade(list(reversed(conclusions()))), 1)
        empty = self.root / "empty"
        empty.mkdir()
        self.assertEqual(exported_grade(self.bundle, empty, "01-audit")["reward"], 0)
        self.assertEqual(run_reference(self.bundle)["problems"], [])

    def test_duplicate_rows_and_exchange_of_deadlines_are_substantive_failures(self):
        duplicated = conclusions()
        duplicated.append(deepcopy(duplicated[0]))
        self.assertEqual(self.grade(duplicated), 0)
        exchanged = conclusions()
        exchanged[0]["notice_deadline"], exchanged[2]["notice_deadline"] = exchanged[2]["notice_deadline"], exchanged[0]["notice_deadline"]
        self.assertEqual(self.grade(exchanged), 0)

    def test_consent_waiver_does_not_silently_erase_a_notice_obligation(self):
        wrong = conclusions()
        wrong[2]["notice_deadline"] = None
        self.assertEqual(self.grade(wrong), 0)

    def test_scoped_clause_amendment_changes_only_its_own_record(self):
        self.clauses[0]["threshold"] = 60
        atomic_json(self.bundle / "environment/files/clauses.json", self.clauses)
        build(self.spec, self.bundle)
        corrected = conclusions()
        corrected[0].update(triggered=False, consent_required=False, notice_deadline=None)
        self.assertEqual(self.grade(conclusions()), 0)
        self.assertEqual(self.grade(corrected), 1)
        self.assertEqual(run_reference(self.bundle)["problems"], [])

    def test_shared_closing_revision_recomputes_all_triggered_deadlines_but_not_nonissues(self):
        atomic_json(self.bundle / "environment/files/deal.json", {"equity": 55, "closing": "2027-01-05"})
        build(self.spec, self.bundle)
        partial = conclusions()
        partial[0]["notice_deadline"] = "2026-12-06"
        self.assertEqual(self.grade(partial), 0)
        corrected = deepcopy(partial)
        corrected[2]["notice_deadline"] = "2026-12-31"
        self.assertEqual(corrected[1], conclusions()[1])
        self.assertEqual(self.grade(corrected), 1)
        self.assertEqual(run_reference(self.bundle)["problems"], [])

    def test_strict_boundary_uses_each_contract_threshold_not_one_uniform_policy(self):
        atomic_json(self.bundle / "environment/files/deal.json", {"equity": 50, "closing": "2026-12-31"})
        build(self.spec, self.bundle)
        corrected = conclusions()
        corrected[0].update(triggered=False, consent_required=False, notice_deadline=None)
        self.assertEqual(self.grade(corrected), 1)
        wrong = deepcopy(corrected)
        wrong[2].update(triggered=False, consent_required=False, notice_deadline=None)
        self.assertEqual(self.grade(wrong), 0)


if __name__ == "__main__":
    unittest.main()
