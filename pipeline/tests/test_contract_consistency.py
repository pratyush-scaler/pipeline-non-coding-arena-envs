"""The published contract and the grader must agree.

Arena's 260927 feedback on the 40-task batch found eight tasks where they did
not: lists the instruction ordered were graded as sets (a reversed list earned
full credit), a set check let a repeated heading through, a guardrail zeroed a
step for a one-day error, step 2 defined a field by "your step-1 plan" while
grading the canonical plan, and one sentinel was quoted with and without its
accent. Each test below is one of those, reduced to its smallest form, plus the
correct form that must stay quiet.
"""
from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from pipeline.author import validate
from pipeline.gates.base import GateContext, Status
from pipeline.gates.contract import _contract_probe, contract_probe_gate

DEFINE = ("- `headings`: array of strings. The heading of every section whose own body holds "
          "fewer than fifty words, written exactly as the file writes it{order}.")


def _spec(field: dict, assertion: str = "set_equals", order: str = "", extra: str = "",
          second: str | None = None, checks: list | None = None) -> dict:
    spec = {
        "instruction": "Audit the specification.\n\n" + DEFINE.format(order=order) + "\n" + extra,
        "deliverable_file": "a.json",
        "outputs": [{"file": "a.json", "step": 1, "schema": {
            "type": "object", "properties": {"headings": field, "count": {"type": "integer"}}}}],
        "checks": checks if checks is not None else [
            {"id": "c_headings", "kind": "objective", "weight": 1, "step": "01-task", "dimension": "core",
             "assertion": assertion, "actual": {"op": "field", "file": "a.json", "path": "headings"},
             "target": {"op": "literal", "value": ["A", "B", "C"]}}],
    }
    if second is not None:
        spec["second_step"] = {"instruction": second, "deliverable_file": "b.json"}
        spec["outputs"].append({"file": "b.json", "step": 2, "schema": {
            "type": "object", "properties": {"superseded_placements": {"type": "array", "items": {"type": "string"}}}}})
    return spec


ARRAY = {"type": "array", "items": {"type": "string"}}


class OrderIsPublishedOnce(unittest.TestCase):
    """[T3b] technical-writing, thesis-002/003, content-writing, creative-video."""

    def test_a_set_check_on_a_list_the_instruction_orders_is_rejected(self):
        problems = validate._unordered_contract(_spec(ARRAY, order=", in document order"))
        self.assertTrue(any("reversed list would earn full credit" in p for p in problems), problems)

    def test_a_set_check_on_a_list_nobody_declared_unordered_is_rejected(self):
        problems = validate._unordered_contract(_spec(ARRAY, assertion="multiset_equals"))
        self.assertTrue(any("compared as written" in p for p in problems), problems)

    def test_a_declared_unordered_list_may_be_compared_as_a_multiset(self):
        spec = _spec({**ARRAY, "unordered": True}, assertion="multiset_equals")
        self.assertEqual(validate._unordered_contract(spec), [])

    def test_the_definition_itself_may_declare_the_list_unordered(self):
        spec = _spec(ARRAY, assertion="multiset_equals", order="; the order of the array is not graded")
        self.assertEqual(validate._unordered_contract(spec), [])

    def test_a_schema_flag_does_not_excuse_a_definition_that_orders_the_list(self):
        spec = _spec({**ARRAY, "unordered": True}, assertion="multiset_equals", order=", in running order")
        problems = validate._unordered_contract(spec)
        self.assertTrue(any("definition publishes" in p for p in problems), problems)

    def test_set_equals_without_unique_items_lets_a_repeat_through(self):
        spec = _spec({**ARRAY, "unordered": True}, assertion="set_equals")
        self.assertTrue(any("repeated" in p for p in validate._unordered_contract(spec)))
        spec = _spec({**ARRAY, "unordered": True, "uniqueItems": True}, assertion="set_equals")
        self.assertEqual(validate._unordered_contract(spec), [])

    def test_unordered_paths_must_be_published_too(self):
        nested = {"type": "object", "properties": {"names": ARRAY}}
        check = {"id": "c_rows", "kind": "objective", "weight": 1, "step": "01-task", "dimension": "core",
                 "assertion": "equals", "unordered_paths": ["names"],
                 "actual": {"op": "field", "file": "a.json", "path": "headings"},
                 "target": {"op": "literal", "value": {"names": ["A"]}}}
        problems = validate._unordered_contract(_spec(nested, checks=[check]))
        self.assertTrue(any("unordered_paths" in p for p in problems), problems)
        declared = {"type": "object", "properties": {"names": {**ARRAY, "unordered": True}}}
        self.assertEqual(validate._unordered_contract(_spec(declared, checks=[check])), [])

    def test_the_field_description_outranks_a_neighbours_paragraph(self):
        field = {**ARRAY, "description": "Chapters to edit, in ascending chapter order."}
        spec = _spec(field, extra="\n- `count`: how many rows. Row order is immaterial.")
        self.assertEqual(validate.order_declaration(spec, "a.json", "headings")[0], "ordered")

    def test_explicit_japanese_order_uses_the_shared_contract(self):
        for words in ("流す順に並べる。", "並び順に意味がある。", "作成日時の昇順に記載する。"):
            with self.subTest(words=words):
                spec = _spec(ARRAY, assertion="equals", order=". " + words)
                self.assertEqual(validate.order_declaration(spec, "a.json", "headings")[0], "ordered")
                self.assertEqual(validate._order_rules(spec), [])
                spec["checks"][0]["assertion"] = "multiset_equals"
                self.assertTrue(validate._unordered_contract(spec))

    def test_explicit_japanese_disorder_cannot_be_graded_in_order(self):
        for words in ("順不同。", "順序は問わない。", "並び順に意味がない。"):
            with self.subTest(words=words):
                spec = _spec(ARRAY, assertion="equals", order=". " + words)
                self.assertEqual(validate.order_declaration(spec, "a.json", "headings")[0], "unordered")
                self.assertTrue(validate._order_rules(spec))
                spec["checks"][0]["assertion"] = "multiset_equals"
                self.assertEqual(validate._unordered_contract(spec), [])

    def test_japanese_field_name_alone_does_not_publish_an_order(self):
        spec = _spec({**ARRAY, "description": "処理順"}, assertion="equals")
        self.assertEqual(validate.order_declaration(spec, "a.json", "headings")[0], "unstated")
        self.assertTrue(validate._order_rules(spec))

    def test_japanese_schema_order_outranks_a_neighbours_disorder(self):
        field = {**ARRAY, "description": "並び順に意味がある。"}
        spec = _spec(field, assertion="equals", extra="\n- `count`: 行数。順序は問わない。")
        self.assertEqual(validate.order_declaration(spec, "a.json", "headings")[0], "ordered")
        self.assertEqual(validate._order_rules(spec), [])

    def test_english_schema_order_is_honoured_by_both_static_checks(self):
        spec = _spec({**ARRAY, "description": "Chapters in ascending chapter order."}, assertion="equals")
        self.assertEqual(validate.order_declaration(spec, "a.json", "headings")[0], "ordered")
        self.assertEqual(validate._order_rules(spec), [])


class EqualsHonoursPublishedDisorder(unittest.TestCase):
    """[T3] larp-rules-writing: "Order is immaterial within each list", graded with `equals`.

    Found by the grader probe, not by Arena: T3's own wordings missed
    "immaterial", so a correct answer listed in another order lost credit."""

    NESTED = {"type": "object", "properties": {"names": ARRAY, "dates": ARRAY}}

    def _check(self, **over):
        return {"id": "c_rows", "kind": "objective", "weight": 1, "step": "01-task", "dimension": "core",
                "assertion": "equals", "actual": {"op": "field", "file": "a.json", "path": "headings"},
                "target": {"op": "literal", "value": {"names": [], "dates": []}}, **over}

    def test_equals_on_lists_the_instruction_calls_immaterial_is_rejected(self):
        spec = _spec(self.NESTED, checks=[self._check()],
                     extra="\n`headings`:\n- `names`: the headings of every clan that states it has no drive.\n"
                           "- `dates`: the dates each clan entry was revised in the capture. "
                           "Order is immaterial within each list; an empty list is written `[]`.")
        problems = validate._order_rules(spec)
        self.assertTrue(any("headings.dates" in p and "does not matter" in p for p in problems), problems)

    def test_a_fields_own_ascending_order_outranks_a_neighbours_disorder(self):
        field = {"type": "object", "properties": {"chapters": {
            **ARRAY, "description": "Chapters the repair must edit, in ascending chapter order."}}}
        spec = _spec(field, checks=[self._check(target={"op": "literal", "value": {"chapters": []}})],
                     extra="\n- `count`: one entry for each chapter that disagrees. Row order is immaterial.")
        self.assertEqual([p for p in validate._order_rules(spec) if "chapters" in p and "does not matter" in p], [])


class GuardsGuardRestraint(unittest.TestCase):
    """[T4] mobile-code-audit's step-1 record guard."""

    def _guard(self, **over):
        return {"id": "g_record", "kind": "guardrail", "weight": 0, "step": "01-task", "dimension": "core",
                "assertion": "equals", "actual": {"op": "field", "file": "a.json", "path": "count"},
                "target": {"op": "count", "of": {"op": "rows", "file": "x.jsonl"}}, **over}

    def test_a_guard_that_recomputes_the_answer_is_rejected(self):
        problems = validate._guard_shape(_spec(ARRAY, checks=[self._guard()]))
        self.assertTrue(any("derived from the sources" in p for p in problems), problems)
        self.assertTrue(any("the step that writes it" in p for p in problems), problems)

    def test_a_fixture_guard_is_fine(self):
        guard = self._guard(assertion="fixture_intact", actual={"op": "fixture"}, target={"op": "fixture"})
        self.assertEqual(validate._guard_shape(_spec(ARRAY, checks=[guard])), [])


class LaterStepsAreDefinedByTheRules(unittest.TestCase):
    """[T5] curriculum-design step 2."""

    def test_a_field_defined_by_the_solvers_own_plan_is_rejected(self):
        spec = _spec(ARRAY, second="Revise the plan.\n- `superseded_placements`: one object for each "
                                   "placement in your step-1 plan that falls inside a declared window.")
        problems = validate._history_references(spec)
        self.assertTrue(any("superseded_placements" in p for p in problems), problems)

    def test_asking_the_solver_to_leave_its_file_alone_is_fine(self):
        spec = _spec(ARRAY, second="Revise the plan. Your first-step file stays exactly as you filed it.\n"
                                   "- `superseded_placements`: every placement the step-1 rules give inside a window.")
        self.assertEqual(validate._history_references(spec), [])


class LiteralsAreSpelledOnce(unittest.TestCase):
    """[T6] content-marketing's `não declarada` / `nao declarada`."""

    def test_one_literal_quoted_with_and_without_its_accent_is_rejected(self):
        spec = _spec(ARRAY, extra="A piece declares nothing when it says `não declarada`.\n"
                                  "List pieces whose column is anything but exactly `nao declarada`.")
        self.assertTrue(any("2 ways" in p for p in validate._literal_consistency(spec)))

    def test_an_exact_literal_the_files_spell_differently_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            files = Path(tmp) / "environment/files"
            files.mkdir(parents=True)
            (files / "pauta.csv").write_text("P1,não declarada\n")
            spec = _spec(ARRAY, extra="List pieces whose column is anything but exactly `nao declarada`.")
            problems = validate._literal_consistency(spec, Path(tmp))
            self.assertTrue(any("no file writes" in p for p in problems), problems)

    def test_case_is_not_a_second_spelling(self):
        spec = _spec(ARRAY, extra="Report `Draft` for a draft; `draft` rows are drafts too.")
        self.assertEqual(validate._literal_consistency(spec), [])


class ProbeGradesWhatTheContractSays(unittest.TestCase):
    """The executed side: mutate the reference answer, grade it, compare with the contract."""

    REFERENCE = {"headings": ["A", "B", "C"], "count": 3}

    def _bundle(self, tmp: Path, spec: dict, guard: bool = False) -> Path:
        (tmp / "authoring").mkdir()
        (tmp / "authoring/spec.json").write_text(json.dumps(spec))
        (tmp / "tests").mkdir()
        checks = [{"id": "c_headings", "kind": "objective", "step": "01-task",
                   "actual": {"op": "field", "file": "a.json", "path": "headings"}},
                  {"id": "c_count", "kind": "objective", "step": "01-task",
                   "actual": {"op": "field", "file": "a.json", "path": "count"}}]
        if guard:
            checks.append({"id": "g_record", "kind": "guardrail", "step": "01-task",
                           "actual": {"op": "field", "file": "a.json", "path": "count"}})
        (tmp / "tests/checks.json").write_text(json.dumps({"checks": checks}))
        (tmp / "tests/rubric.json").write_text(json.dumps({"01-task": [c["id"] for c in checks]}))
        (tmp / "solution/submission").mkdir(parents=True)
        (tmp / "solution/submission/a.json").write_text(json.dumps(self.REFERENCE))
        return tmp

    @staticmethod
    def _grader(ordered: bool, unique: bool = True, guard_checks_value: bool = False):
        """A stand-in for the exported grader with the semantics under test."""
        def grade(bundle, root, step):
            got = json.loads((Path(root) / "a.json").read_text())
            ref = ProbeGradesWhatTheContractSays.REFERENCE
            if unique and len(set(got["headings"])) != len(got["headings"]):
                return {"reward": 0.0, "checks": {}}            # schema rejects the file
            same = got["headings"] == ref["headings"] if ordered else set(got["headings"]) == set(ref["headings"])
            checks = {"c_headings": {"passed": same}, "c_count": {"passed": got["count"] == ref["count"]}}
            if guard_checks_value:
                checks["g_record"] = {"passed": got["count"] == ref["count"]}
            guards_ok = all(v["passed"] for k, v in checks.items() if k.startswith("g_"))
            objectives = [v["passed"] for k, v in checks.items() if k.startswith("c_")]
            return {"reward": (sum(objectives) / len(objectives)) if guards_ok else 0.0, "checks": checks}
        return grade

    def _run(self, spec, grader, guard=False):
        with tempfile.TemporaryDirectory() as tmp:
            bundle = self._bundle(Path(tmp), spec, guard)
            with mock.patch("pipeline.evaluate.exported_grade", grader):
                findings, _ = _contract_probe(GateContext(task_dir=bundle, repo_root=bundle))
        return {f.code for f in findings if f.severity.value == "blocker"}, findings

    def test_a_list_the_instruction_orders_must_be_graded_in_order(self):
        codes, _ = self._run(_spec(ARRAY, order=", in document order"), self._grader(ordered=False))
        self.assertIn("order-not-graded", codes)
        codes, _ = self._run(_spec(ARRAY, order=", in document order"), self._grader(ordered=True))
        self.assertEqual(codes, set())

    def test_a_declared_unordered_list_must_accept_any_order(self):
        spec = _spec({**ARRAY, "unordered": True})
        self.assertEqual(self._run(spec, self._grader(ordered=False))[0], set())
        self.assertIn("unordered-list-graded-in-order", self._run(spec, self._grader(ordered=True))[0])

    def test_a_repeated_entry_must_lose_credit(self):
        spec = _spec({**ARRAY, "unordered": True})
        self.assertIn("repeat-not-graded", self._run(spec, self._grader(ordered=False, unique=False))[0])

    def test_a_guard_must_not_fail_on_a_wrong_value(self):
        spec = _spec(ARRAY, order=", in document order")
        codes, _ = self._run(spec, self._grader(ordered=True, guard_checks_value=True), guard=True)
        self.assertIn("guard-fails-on-wrong-answer", codes)

    def test_a_reference_that_does_not_score_one_is_an_error_not_a_pass(self):
        def broken(bundle, root, step):
            return {"reward": 0.5, "checks": {}}
        with tempfile.TemporaryDirectory() as tmp:
            bundle = self._bundle(Path(tmp), _spec(ARRAY, order=", in document order"))
            with mock.patch("pipeline.evaluate.exported_grade", broken):
                result = contract_probe_gate.run(GateContext(task_dir=bundle, repo_root=bundle))
        self.assertIs(result.status, Status.ERROR)

    def test_unscored_work_and_agreement_claims_are_raised_for_review(self):
        spec = _spec(ARRAY, order=", in document order",
                     extra="\nBRIEFING DEPTH. Measure every section the compiled brief prints.\n\n"
                           "The two later copies agree on every count below.")
        _, findings = self._run(spec, self._grader(ordered=True))
        warned = {f.code for f in findings if f.severity.value == "warn"}
        self.assertEqual(warned, {"unscored-section", "agreement-claim"})


if __name__ == "__main__":
    unittest.main()
