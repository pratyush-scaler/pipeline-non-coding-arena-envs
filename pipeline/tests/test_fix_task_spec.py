"""Task-contract regressions: every Arena spec requirement the audit reproduced
as a gap is now refused by the pipeline. No API calls; each test builds a small
synthetic bundle and runs the real validator, generator and gates.

  T1  fields defined; absolute input/output paths in each step's contract
  T2  referenced files and commands exist
  T3  row filters, regexes and array order are published rules
  G4  documented points equal what the grader pays
  G5  probe evidence is bound and re-run; structured answers in the fixture found
  kw003  later-step material detected by content, not only by file name
  kw006  overlapping / undefined output-schema enum values
"""
from __future__ import annotations

import copy
import json
import tempfile
import tomllib
import unittest
from pathlib import Path
from types import SimpleNamespace

from pipeline.author.build import build
from pipeline.author.contracts import schema_problems
from pipeline.author.validate import validate
from pipeline.gates.base import GateContext
from pipeline.tests.test_exported_grader import CSV

INSTRUCTION = (
    "Leave tickets.csv unchanged. Write `summary.json` with `open_ids` -- the ticket "
    "IDs of every row whose status is open, in any order; `open_count` -- the number "
    "of rows whose status is open; and `total_effort` -- the sum of the effort column "
    "over the rows whose status is open.")
RULE = "the ticket IDs of every row whose status is open, in any order"
SCHEMA = {"type": "object", "additionalProperties": False,
          "required": ["open_ids", "open_count", "total_effort"],
          "properties": {"open_ids": {"type": "array", "items": {"type": "string"}},
                         "open_count": {"type": "integer"},
                         "total_effort": {"type": "integer"}}}


def spec(two_steps: bool = False) -> dict:
    rows = {"op": "rows", "file": "tickets.jsonl", "where": {"field": "status", "eq": "open"}}
    targets = {"open_ids": ("set_equals", {"op": "pluck", "of": rows, "field": "ticket"}, 5),
               "open_count": ("equals", {"op": "count", "of": rows}, 3),
               "total_effort": ("equals", {"op": "sum", "of": rows, "field": "effort"}, 2)}
    checks = [{"id": "source_unchanged", "kind": "guardrail", "weight": 0,
               "basis": "Leave tickets.csv unchanged.", "assertion": "fixture_intact",
               "actual": {"op": "literal", "value": True}}]
    for key, (assertion, target, weight) in targets.items():
        checks.append({"id": key, "kind": "objective", "weight": weight, "basis": INSTRUCTION,
                       "assertion": assertion, "rule_quote": [RULE],
                       "actual": {"op": "field", "file": "summary.json", "path": key},
                       "target": target})
    out = {"name": "Open tickets", "description": "Summarise open work.",
           "source": {"session_id": "synthetic-public-example", "seed_index": 0},
           "instruction": INSTRUCTION, "deliverable_file": "summary.json",
           "projections": [{"file": "tickets.csv", "parser": "csv_table", "as": "tickets.jsonl"}],
           "outputs": [{"file": "summary.json", "step": 1, "schema": copy.deepcopy(SCHEMA)}],
           "checks": checks, "traps": [],
           "solution": {"summary.json": {"open_ids": ["R-21", "R-23"], "open_count": 2,
                                         "total_effort": 8}}}
    if two_steps:
        out["second_step"] = {
            "instruction": "The client now asks for a recount. Write `revised.json` with "
                           "`count` -- the number of rows in tickets.csv whose status is open, "
                           "counted again from the file rather than copied from step one.",
            "deliverable_file": "revised.json",
            "new_information": "The client doubts the earlier count and asks for a recount."}
        out["outputs"].append({"file": "revised.json", "step": 2, "schema": {
            "type": "object", "additionalProperties": False, "required": ["count"],
            "properties": {"count": {"type": "integer"}}}})
        out["checks"].append({"id": "revised_count", "kind": "objective", "weight": 1,
                              "basis": "recount", "assertion": "equals", "step": "02-revision",
                              "rule_quote": ["the number of rows in tickets.csv whose status is open"],
                              "actual": {"op": "field", "file": "revised.json", "path": "count"},
                              "target": {"op": "count", "of": rows}})
        out["solution"]["revised.json"] = {"count": 2}
    return out


class Bundle(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def make(self, s: dict | None = None, name: str = "b", extra: dict | None = None) -> Path:
        bundle = self.root / name
        (bundle / "environment/files").mkdir(parents=True)
        (bundle / "environment/files/tickets.csv").write_text(CSV)
        for rel, text in (extra or {}).items():
            (bundle / "environment/files" / rel).write_text(text)
        build(s or spec(), bundle)
        return bundle

    def problems(self, s: dict, bundle: Path | None = None) -> list[str]:
        bundle = bundle or self.make(copy.deepcopy(s), name=f"v{len(list(self.root.iterdir()))}")
        return validate(s, bundle)

    @staticmethod
    def ctx(bundle: Path) -> GateContext:
        return GateContext(task_dir=bundle, repo_root=Path("."))


class T1FieldsAndPaths(Bundle):
    def test_a_compliant_spec_raises_no_contract_problem(self):
        found = [p for p in self.problems(spec(two_steps=True))
                 if any(k in p for k in ("never named", "never defined", "references",
                                         "rule_quote", "`equals`"))]
        self.assertEqual(found, [])

    def test_a_named_but_undefined_field_is_refused(self):
        s = spec()
        s["instruction"] = INSTRUCTION.replace(
            "`total_effort` -- the sum of the effort column over the rows whose status is open.",
            "`total_effort`.")
        self.assertTrue(any("'total_effort' is named but never defined" in p
                            for p in self.problems(s)))

    def test_a_field_never_named_is_refused(self):
        s = spec()
        s["outputs"][0]["schema"]["properties"]["owner_note"] = {"type": "string"}
        s["outputs"][0]["schema"]["required"].append("owner_note")
        self.assertTrue(any("'owner_note' is never named" in p for p in self.problems(s)))

    def test_contract_states_absolute_input_and_output_paths(self):
        text = (self.make() / "steps/01-task/instruction.md").read_text()
        self.assertIn("/app/environment/files (read-only)", text)
        self.assertIn("/app/deliverables/summary.json", text)


class T2References(Bundle):
    def test_missing_file_and_uninstalled_command_are_refused(self):
        s = spec()
        s["instruction"] += (" Cross-check against `rates.xlsx`, run `./check.sh` and "
                             "summarise with `jq '.open_count' summary.json`.")
        found = [p for p in self.problems(s) if "references" in p]
        self.assertTrue(any("'rates.xlsx'" in p for p in found), found)
        self.assertTrue(any("'./check.sh'" in p for p in found), found)
        self.assertTrue(any("'jq' is not installed" in p for p in found), found)

    def test_fixture_files_deliverables_and_base_tools_pass(self):
        s = spec()
        s["instruction"] += " You may inspect `tickets.csv` with `python3 -c 'print(1)'`."
        self.assertEqual([p for p in self.problems(s) if "references" in p], [])


class T3HiddenRules(Bundle):
    def test_a_filter_without_rule_quote_is_refused(self):
        s = spec()
        for c in s["checks"]:
            c.pop("rule_quote", None)
        self.assertTrue(any("carries no `rule_quote`" in p for p in self.problems(s)))

    def test_a_quote_not_in_the_instruction_is_refused(self):
        s = spec()
        s["checks"][1]["rule_quote"] = ["rows whose status is open are counted"]
        self.assertTrue(any("not verbatim" in p for p in self.problems(s)))

    def test_an_unpublished_extra_clause_is_refused(self):
        """audit hidden_rule_c2: a clause dropping rows by an unstated value."""
        s = spec()
        rows = s["checks"][1]["target"]["of"]
        rows["where"] = {"all": [rows["where"], {"field": "effort", "matches": "^(?!8$)"}]}
        self.assertTrue(any("is not stated by any rule_quote" in p for p in self.problems(s)))

    def test_rule_terms_count_only_when_their_words_are_in_the_quote(self):
        s = spec()
        rows = {"op": "rows", "file": "tickets.jsonl", "where": {"field": "status", "eq": "closed"}}
        s["checks"][2]["target"] = {"op": "count", "of": rows}
        s["instruction"] += " A shut ticket is one whose status is closed."
        self.assertTrue(any("is not stated" in p for p in self.problems(s)))
        s["checks"][2]["rule_terms"] = {"closed": "shut tickets"}      # words not in the quote
        self.assertTrue(any("is not stated" in p for p in self.problems(s)))
        s["checks"][2]["rule_quote"] = [RULE, "A shut ticket is one whose status is closed."]
        self.assertFalse(any("is not stated" in p for p in self.problems(s)))

    def test_ordered_equals_on_an_unordered_array_is_refused(self):
        """audit hidden_order_c: multiset -> equals while the text says any order."""
        s = spec()
        s["checks"][1]["assertion"] = "equals"
        self.assertTrue(any("says its order does not matter" in p for p in self.problems(s)))

    def test_schema_marked_unordered_array_needs_an_unordered_assertion(self):
        s = spec()
        s["instruction"] = s["instruction"].replace(", in any order", "")
        s["checks"][1]["rule_quote"] = ["the ticket IDs of every row whose status is open"]
        s["outputs"][0]["schema"]["properties"]["open_ids"]["unordered"] = True
        s["checks"][1]["assertion"] = "equals"
        self.assertTrue(any("says its order does not matter" in p for p in self.problems(s)))

    def test_ordered_equals_with_no_stated_order_is_a_hidden_rule(self):
        s = spec()
        s["instruction"] = s["instruction"].replace(", in any order", "")
        s["checks"][1]["rule_quote"] = ["the ticket IDs of every row whose status is open"]
        s["checks"][1]["assertion"] = "equals"
        self.assertTrue(any("never states an order" in p for p in self.problems(s)))

    def test_unordered_is_a_boolean_array_keyword(self):
        self.assertEqual(schema_problems({"type": "array", "items": {"type": "string"},
                                          "unordered": True}), [])
        self.assertTrue(schema_problems({"type": "string", "unordered": True}))


class G4DocumentedPoints(Bundle):
    def shares(self, bundle: Path) -> dict[str, float]:
        checks = json.loads((bundle / "tests/checks.json").read_text())["checks"]
        rubric = json.loads((bundle / "tests/rubric.json").read_text())
        by_id = {c["id"]: c for c in checks}
        out = {}
        for step, ids in rubric.items():
            owned = [by_id[i] for i in ids if by_id[i]["kind"] == "objective"]
            total = sum(c["weight"] for c in owned)
            for c in owned:
                out[c["id"]] = c["weight"] / total / len(rubric)
        return out

    def test_reward_toml_documents_what_the_grader_pays(self):
        bundle = self.make(spec(two_steps=True))
        documented = tomllib.loads((bundle / "tests/reward.toml").read_text()).get("shares", {})
        for cid, share in self.shares(bundle).items():
            self.assertAlmostEqual(documented[cid]["task_share"], share, places=5, msg=cid)
        checks = json.loads((bundle / "tests/checks.json").read_text())["checks"]
        per_step = {}
        for c in checks:
            if c["kind"] == "objective":
                per_step[c["step"]] = per_step.get(c["step"], 0) + c["weight"]
        self.assertEqual(per_step, {"01-task": 50, "02-revision": 50})

    def test_the_gate_blocks_documented_points_that_drift(self):
        from pipeline.gates.integrity import _reference_answer
        bundle = self.make(spec(two_steps=True))
        codes = {f.code for f in _reference_answer(self.ctx(bundle))[0]}
        self.assertFalse(codes & {"points-drift", "points-undocumented"}, codes)
        path = bundle / "tests/reward.toml"
        path.write_text(path.read_text().replace("task_share = 0.5 }", "task_share = 0.05 }", 1))
        codes = {f.code for f in _reference_answer(self.ctx(bundle))[0]}
        self.assertIn("points-drift", codes)


class G5ProbeEvidence(Bundle):
    def record(self, bundle: Path) -> dict:
        from pipeline.author.probes import run
        # the flags the spec declares, as orchestrate records them
        report = run(bundle, self.root / f"work-{bundle.name}", forged_applicable=False,
                     forged_reason="")
        (bundle / "verification").mkdir(exist_ok=True)
        (bundle / "verification/probes.json").write_text(json.dumps(report))
        return report

    def test_structured_answer_in_a_fixture_note_is_found_and_blocks(self):
        from pipeline.author.probes import run
        from pipeline.gates.integrity import _derivation
        note = "# Notes\n```json\n" + json.dumps({"open_ids": ["R-21", "R-23"]}) + "\n```\n"
        bundle = self.make(extra={"notes.md": note})
        report = run(bundle, self.root / "work", forged_applicable=False, forged_reason="x" * 50)
        self.assertIn("open_ids", report["results"]["answer_lookup"]["stored_structured"])
        codes = [f.code for f in _derivation(self.ctx(bundle))[0]]
        self.assertIn("answer-stored-in-fixture", codes)

    def test_a_stored_report_is_bound_to_its_bundle_and_rerun(self):
        from pipeline.gates.difficulty import _hack_resistance
        bundle = self.make()
        report = self.record(bundle)
        self.assertIn("probe_inputs_sha256", report["binding"])
        codes = {f.code for f in _hack_resistance(self.ctx(bundle))[0]}
        self.assertFalse(codes & {"probe-evidence-stale", "probe-evidence-unbound",
                                  "probe-evidence-diverges"}, codes)
        # the fixture changes after the probes ran: the old report no longer certifies
        (bundle / "environment/files/tickets.csv").write_text(CSV + "R-24,open,1\n")
        codes = {f.code for f in _hack_resistance(self.ctx(bundle))[0]}
        self.assertIn("probe-evidence-stale", codes)

    def test_a_forged_report_cannot_certify(self):
        from pipeline.gates.difficulty import _hack_resistance
        bundle = self.make()
        report = self.record(bundle)
        report.pop("binding")
        report["results"]["answer_lookup"]["reward"] = 0.0
        (bundle / "verification/probes.json").write_text(json.dumps(report))
        codes = {f.code for f in _hack_resistance(self.ctx(bundle))[0]}
        self.assertIn("probe-evidence-unbound", codes)


class Kw003StepContent(Bundle):
    def isolation(self, bundle: Path):
        from pipeline.gates.findings import _step_isolation
        ctx = SimpleNamespace(task_dir=bundle, path=lambda *parts: bundle.joinpath(*parts))
        return [f for f in _step_isolation(ctx)[0] if f.code == "later-step-material-in-fixture"]

    def test_neutrally_named_file_mentioning_the_later_step_is_a_leak(self):
        bundle = self.make(spec(two_steps=True), extra={
            "rollback_notes.md": "Restore version 27; the answer for step two is a recount of 2."})
        self.assertTrue(any("rollback_notes.md" in f.message for f in self.isolation(bundle)))

    def test_file_only_the_later_step_uses_is_a_leak(self):
        s = spec(two_steps=True)
        s["projections"].append({"file": "recount.csv", "parser": "csv_table", "as": "recount.jsonl"})
        s["second_step"]["instruction"] += " Use `recount.csv`, the client's recount sheet."
        s["checks"][-1]["target"] = {"op": "count", "of": {"op": "rows", "file": "recount.jsonl"}}
        s["checks"][-1].pop("rule_quote")
        bundle = self.make(s, extra={"recount.csv": "ticket,status\nR-21,open\nR-23,open\n"})
        found = self.isolation(bundle)
        self.assertTrue(any("recount.csv" in f.message and "only a later step" in f.message
                            for f in found), found)

    def test_shared_documents_are_not_a_leak(self):
        self.assertEqual(self.isolation(self.make(spec(two_steps=True))), [])

    def test_a_generic_next_step_in_an_unused_file_warns_but_does_not_block(self):
        # e2e build, 2026-09-26: a recovered README's "## Recommended next step --
        # ask me to continue again" blocked a task; the designer cannot edit
        # recovered files, so the finding survived its repair and ended it.
        from pipeline.gates.findings import _step_isolation
        bundle = self.make(spec(two_steps=True), extra={
            "README.md": "Lines 20-24 remain pending.\n## Recommended next step\nAsk me to continue again."})
        self.assertEqual(self.isolation(bundle), [])
        ctx = SimpleNamespace(task_dir=bundle, path=lambda *parts: bundle.joinpath(*parts))
        warned = [f for f in _step_isolation(ctx)[0] if f.code == "possible-forward-reference"]
        self.assertTrue(any("README.md" in f.message and "next step" in f.message for f in warned), warned)

    def test_an_explicit_step_two_reference_still_blocks(self):
        bundle = self.make(spec(two_steps=True), extra={
            "handover.md": "For step two, recount the open tickets after the revision."})
        self.assertTrue(any("handover.md" in f.message for f in self.isolation(bundle)))

    def test_a_lifted_file_numbering_its_own_steps_warns_but_does_not_block(self):
        # a-005 (build 2026-09-26): a rescue README recovered verbatim from the
        # trace said "STEP 2"; it predates the task and cannot be edited.
        from pipeline.gates.findings import _step_isolation
        text = "STEP 1: stop the service.\nSTEP 2: restore the backup, then restart."
        bundle = self.make(spec(two_steps=True), extra={"rescue.md": text})
        (bundle / "provenance").mkdir(exist_ok=True)
        (bundle / "provenance/ledger.json").write_text(json.dumps(
            {"entries": [{"path": "rescue.md", "origin": "lifted"}]}))
        self.assertEqual(self.isolation(bundle), [])
        ctx = SimpleNamespace(task_dir=bundle, path=lambda *parts: bundle.joinpath(*parts))
        warned = [f for f in _step_isolation(ctx)[0] if f.code == "possible-forward-reference"]
        self.assertTrue(any("rescue.md" in f.message for f in warned), warned)
        # ...the same words in an authored file still block.
        (bundle / "provenance/ledger.json").write_text(json.dumps(
            {"entries": [{"path": "rescue.md", "origin": "authored"}]}))
        self.assertTrue(any("rescue.md" in f.message for f in self.isolation(bundle)))

    def test_later_step_words_in_a_lifted_file_warn_but_do_not_block(self):
        # a-024 (build 2026-09-26): lifted CRM pages contain the ordinary words
        # step 2 used as output field names.
        s = spec(two_steps=True)
        s["second_step"]["instruction"] += " Apply `HOLD-2024` under clause `ZX-9001`."
        bundle = self.make(s, extra={"background.md": "Policy HOLD-2024 invokes clause ZX-9001."})
        (bundle / "provenance").mkdir(exist_ok=True)
        (bundle / "provenance/ledger.json").write_text(json.dumps(
            {"entries": [{"path": "background.md", "origin": "lifted"}]}))
        self.assertEqual(self.isolation(bundle), [])

    def test_vocabulary_step_one_already_reads_is_not_later_step_material(self):
        # e2e build, 2026-09-26: step 2 named an existing rule and process that
        # step 1's own documents carry; every background spec file was flagged.
        s = spec(two_steps=True)
        s["second_step"]["instruction"] += " Apply `HOLD-2024` to ticket `R-21`."
        bundle = self.make(s, extra={"background.md": "Policy HOLD-2024 covers R-21 and R-23."})
        self.assertEqual(self.isolation(bundle), [])

    def test_identifiers_only_the_later_step_knows_still_leak(self):
        s = spec(two_steps=True)
        s["second_step"]["instruction"] += " Apply `HOLD-2024` under clause `ZX-9001`."
        bundle = self.make(s, extra={"background.md": "Policy HOLD-2024 invokes clause ZX-9001."})
        found = self.isolation(bundle)
        self.assertTrue(any("background.md" in f.message and "identifiers only a later" in f.message
                            for f in found), found)

    def test_bare_numbers_are_not_identifiers(self):
        # a-066 (build 2026-09-26): years in the step-2 instruction flagged an
        # unused chapter that happened to mention the same years.
        s = spec(two_steps=True)
        s["second_step"]["instruction"] += " The 2025 revision replaces the 2024 rules."
        bundle = self.make(s, extra={"chapter.md": "Drafted in 2024, revised in 2025."})
        self.assertEqual(self.isolation(bundle), [])
        # ...but a backticked number is the author naming it on purpose.
        s["second_step"]["instruction"] += " Apply `4471` and `9902`."
        bundle = self.make(s, name="ticked", extra={"chapter.md": "Codes 4471 and 9902 apply."})
        self.assertTrue(any("chapter.md" in f.message for f in self.isolation(bundle)))


class Kw006SchemaEnums(Bundle):
    def ambiguity(self, s: dict):
        from pipeline.gates.findings import _ambiguity
        bundle = self.make(s, name=f"a{len(list(self.root.iterdir()))}")
        ctx = SimpleNamespace(task_dir=bundle, path=lambda *parts: bundle.joinpath(*parts))
        return {f.code for f in _ambiguity(ctx)[0]}

    def with_verdict(self, prose: str) -> dict:
        s = spec()
        schema = s["outputs"][0]["schema"]
        schema["properties"]["verdict"] = {"type": "string",
                                           "enum": ["incorrect", "unsupported", "contested"]}
        schema["required"].append("verdict")
        s["instruction"] += " " + prose
        s["solution"]["summary.json"]["verdict"] = "contested"
        return s

    def test_undefined_schema_enum_values_are_caught(self):
        codes = self.ambiguity(self.with_verdict(
            "Also record `verdict` for the summary, one of the values in the schema."))
        self.assertIn("undefined-category", codes)

    def test_overlapping_schema_enum_values_are_caught(self):
        codes = self.ambiguity(self.with_verdict(
            "Record `verdict` for the summary. Use incorrect when the open rows are not "
            "supported by the stated ticket status in the file. Use unsupported when the "
            "open rows are not supported by the stated ticket status in the sheet. Use "
            "contested when two different people dispute the recorded owner of a ticket."))
        self.assertIn("overlapping-categories", codes)

    def with_priority(self, prose: str) -> dict:
        s = spec()
        s["instruction"] += " Tag the summary `urgent`, `normal` or `low`. " + prose
        return s

    def test_prose_values_defined_side_by_side_are_not_one_definition(self):
        # a-051 (build 2026-09-26): four roles, each defined in its own clause
        # of one sentence, were credited with the whole sentence and blocked.
        codes = self.ambiguity(self.with_priority(
            "`urgent` is a ticket whose customer has already escalated twice; `normal` "
            "is a ticket opened this week with no escalation; `low` is a ticket the "
            "customer marked as a question rather than a fault."))
        self.assertNotIn("overlapping-categories", codes)

    def test_prose_values_with_the_same_definition_still_overlap(self):
        codes = self.ambiguity(self.with_priority(
            "Use `urgent` when the open rows are not supported by the stated ticket status "
            "in the file. Use `normal` when the open rows are not supported by the stated "
            "ticket status in the sheet. Use `low` when two different people dispute the "
            "recorded owner of a ticket."))
        self.assertIn("overlapping-categories", codes)

    def test_a_definition_in_russian_is_a_definition(self):
        # a-031 (build 2026-09-26): `vhodit` was defined in Russian prose and
        # reported undefined, because the gate read ASCII words only.
        codes = self.ambiguity(self.with_verdict(
            "Поле `verdict` равно `incorrect`, если открытые строки противоречат статусу "
            "заявки в таблице. Значение `unsupported` ставится, когда подтверждающего "
            "документа нет вовсе. Значение `contested` означает, что два разных человека "
            "оспаривают владельца заявки."))
        self.assertNotIn("undefined-category", codes)

    def test_a_non_english_overlap_advises_because_precedence_cannot_be_read(self):
        from pipeline.gates.findings import _ambiguity
        s = self.with_verdict(
            "Значение `incorrect` ставится, когда открытые строки не подтверждены указанным "
            "статусом заявки в файле. Значение `unsupported` ставится, когда открытые строки "
            "не подтверждены указанным статусом заявки в таблице. Значение `contested` "
            "означает, что два разных человека оспаривают записанного владельца заявки.")
        bundle = self.make(s, name="ru-overlap")
        ctx = SimpleNamespace(task_dir=bundle, path=lambda *parts: bundle.joinpath(*parts))
        found = [f for f in _ambiguity(ctx)[0] if f.code == "overlapping-categories"]
        self.assertTrue(found)
        self.assertTrue(all(f.severity.name == "WARN" for f in found), found)

    def test_portuguese_opposite_registry_predicates_require_review_not_repair(self):
        from pipeline.gates.findings import _ambiguity
        task = spec()
        task["outputs"][0]["schema"]["properties"]["motivo"] = {
            "type": "string", "enum": ["ok", "fora_do_registro"]}
        task["instruction"] += (
            " `ok` — a habilidade ativada faz parte do registro em vigor "
            "e os requisitos estão cumpridos; "
            "`fora_do_registro` — a habilidade ativada não faz parte do registro em vigor.")
        bundle = self.make(task, name="pt-opposites")
        found, evidence = _ambiguity(self.ctx(bundle))
        overlaps = [finding for finding in found if finding.code == "overlapping-categories"]
        self.assertTrue(overlaps)
        self.assertTrue(all(finding.severity.name == "WARN" for finding in overlaps))
        self.assertTrue(any(row["polarity_contrast"] for row in evidence["overlaps"]))
        self.assertFalse(any(finding.severity.name == "BLOCKER" for finding in found))

    def test_english_opposite_predicates_do_not_lose_negation_as_stopwords(self):
        from pipeline.gates.findings import _ambiguity
        task = self.with_priority(
            "Use `urgent` when the customer request is supported by the signed agreement. "
            "Use `normal` when the customer request is not supported by the signed agreement. "
            "Use `low` when two different people dispute the recorded owner of a ticket.")
        bundle = self.make(task, name="en-opposites")
        found, evidence = _ambiguity(self.ctx(bundle))
        overlaps = [finding for finding in found if finding.code == "overlapping-categories"]
        self.assertTrue(overlaps)
        self.assertTrue(all(finding.severity.name == "WARN" for finding in overlaps))
        self.assertTrue(any(row["polarity_contrast"] for row in evidence["overlaps"]))

    def test_unrelated_negation_does_not_excuse_overlapping_predicates(self):
        from pipeline.gates.findings import _ambiguity
        task = self.with_priority(
            "Use `urgent` when the customer request is supported by the signed agreement; "
            "do not edit the supplied file. Use `normal` when the customer request is "
            "supported by the signed agreement. Use `low` when two different people "
            "dispute the recorded owner of a ticket.")
        bundle = self.make(task, name="unrelated-negation")
        found, evidence = _ambiguity(self.ctx(bundle))
        self.assertTrue(any(finding.code == "overlapping-categories"
                            and finding.severity.name == "BLOCKER" for finding in found))
        self.assertFalse(any(row["polarity_contrast"] for row in evidence["overlaps"]))

    def test_identical_negated_predicates_still_block(self):
        from pipeline.gates.findings import _ambiguity
        task = self.with_priority(
            "Use `urgent` when the customer request is not supported by the signed agreement. "
            "Use `normal` when the customer request is not supported by the signed agreement. "
            "Use `low` when two different people dispute the recorded owner of a ticket.")
        bundle = self.make(task, name="same-negation")
        found, evidence = _ambiguity(self.ctx(bundle))
        self.assertTrue(any(finding.code == "overlapping-categories"
                            and finding.severity.name == "BLOCKER" for finding in found))
        self.assertFalse(any(row["polarity_contrast"] for row in evidence["overlaps"]))

    def test_chinese_sentences_split_at_full_width_stops(self):
        codes = self.ambiguity(self.with_verdict(
            "`verdict` 字段：`incorrect` 表示未关闭的行与表格中的工单状态相互矛盾。"
            "`unsupported` 表示完全找不到任何佐证文件。"
            "`contested` 表示有两个不同的人对工单负责人存在争议。"))
        self.assertNotIn("undefined-category", codes)



class CompletenessInAnyScript(unittest.TestCase):
    """a-036 (build 2026-09-26): a basis line written in Chinese had no ASCII
    tokens, was reported as "no public wording", survived its repair and
    blocked the task. Russian failed the same way."""

    def codes(self, instruction: str, basis: dict[str, str]) -> dict[str, set[str]]:
        from pipeline.gates.findings import _completeness
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "steps/01-task").mkdir(parents=True)
            (root / "steps/01-task/instruction.md").write_text(instruction)
            (root / "tests").mkdir()
            (root / "tests/basis.toml").write_text("[checks]\n" + "".join(
                f"{json.dumps(k)} = {json.dumps(v, ensure_ascii=False)}\n" for k, v in basis.items()))
            ctx = SimpleNamespace(task_dir=root, path=lambda *parts: root.joinpath(*parts))
            found: dict[str, set[str]] = {}
            for f in _completeness(ctx)[0]:
                found.setdefault(f.code, set()).add(f.message)
            return found

    def test_chinese_and_russian_wording_counts_as_public(self):
        zh = "这一轮只出质检记录：不要重新生成讲稿，也不要修改或删除工作区里的任何现有文件。"
        ru = "Не изменяйте исходные файлы клиента; запишите план публикаций отдельно."
        found = self.codes(zh + "\n" + ru, {"guard_zh": zh, "guard_ru": ru})
        self.assertNotIn("empty-basis", found)
        self.assertNotIn("unpublished-rule", found)

    def test_wording_absent_from_every_visible_document_is_still_unpublished(self):
        found = self.codes("只出质检记录。", {"guard_zh": "按照内部评分表扣分"})
        self.assertIn("unpublished-rule", found)
        self.assertIn("empty-basis", self.codes("Anything.", {"blank": "  "}))


if __name__ == "__main__":
    unittest.main()


class V2PartialOverlapIsAdvisory(Kw006SchemaEnums):
    """v2 (2026-10-02, a-003): two DIFFERENT predicates that share wording are a
    lexical resemblance, not an ambiguity; only a contained predicate blocks."""

    def test_different_predicates_sharing_words_only_warn(self):
        from pipeline.gates.findings import _ambiguity
        task = self.with_priority(
            "Use `urgent` when the pages of the handout are printed in black and white. "
            "Use `normal` when the pages of the handout are printed in full colour. "
            "Use `low` when two different people dispute the recorded owner of a ticket.")
        found, _ = _ambiguity(self.ctx(self.make(task, name="partial-overlap")))
        overlaps = [f for f in found if f.code == "overlapping-categories"]
        self.assertTrue(all(f.severity.name == "WARN" for f in overlaps), overlaps)
