"""Production boundaries: malformed evidence, semantic controls and restart safety."""
import copy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from pipeline import policy
from pipeline.artifacts import atomic_json, identity, evidence_inventory
from pipeline.assurance import case_values, controls, generated_problems
from pipeline.author.build import build
from pipeline.author.checks import Workspace, CheckError, SubmissionInvalid, evaluate, normalise, row_value
from pipeline.author.contracts import schema_errors
from pipeline.author.oracle import markdown_tables, stem_overlap
from pipeline.corpus import signature, related, register
from pipeline.provider import RequestBudget
from pipeline.tests.test_production import synthetic_bundle


class ReleaseBoundaries(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        # The calibration of record is gated on a shippable screen; that gate
        # has its own tests (test_spec_acceptance). These test qualification.
        screened = patch("pipeline.screen.shippable_problems", return_value=[])
        screened.start()
        self.addCleanup(screened.stop)
        self.root = Path(temp.name).resolve()

    def test_wrong_and_alternative_controls_execute_exported_grader(self):
        bundle = synthetic_bundle(self.root)
        spec = json.loads((bundle / "authoring/spec.json").read_text())
        ids = [c["id"] for c in spec["checks"] if c["kind"] == "objective"]
        spec["quality"] = {"semantic_checks": ids,
            "counterexamples": [{"id": "closed-work-included", "reason": "Includes a closed record",
                "patches": [{"file": "summary.json", "path": "open_ids", "value": ["R-21", "R-22", "R-23"]},
                            {"file": "summary.json", "path": "open_count", "value": 3},
                            {"file": "summary.json", "path": "total_effort", "value": 16}], "fails": ids}],
            "alternatives": [{"id": "different-order", "reason": "Order is explicitly irrelevant",
                "patches": [{"file": "summary.json", "path": "open_ids", "value": ["R-23", "R-21"]}]}]}
        spec["quality"]["source_cases"] = [{"id": "reopened-job", "reason": "Closed job becomes open",
            "changes": ids, "source_patches": [{"file": "tickets.csv", "before": "R-22,closed,8", "after": "R-22,open,8"}],
            "patches": copy.deepcopy(spec["quality"]["counterexamples"][0]["patches"])}]
        build(spec, bundle)
        self.assertEqual(controls(bundle)["errors"], [])
        spec["quality"]["counterexamples"][0]["patches"][1]["value"] = 2
        build(spec, bundle)
        self.assertTrue(any("did not fail open_count" in e for e in controls(bundle)["errors"]))

    def test_a_misreading_counterexample_must_fail_only_what_its_trap_drives(self):
        # Review: an all-wrong counterexample named by a misreading "proved" the
        # trap. The controls now EXECUTE the claim: every objective the trap does
        # not drive must pass when that counterexample is graded.
        bundle = synthetic_bundle(self.root)
        spec = json.loads((bundle / "authoring/spec.json").read_text())
        ids = [c["id"] for c in spec["checks"] if c["kind"] == "objective"]
        everything = [{"file": "summary.json", "path": "open_ids", "value": ["R-21", "R-22", "R-23"]},
                      {"file": "summary.json", "path": "open_count", "value": 3},
                      {"file": "summary.json", "path": "total_effort", "value": 16}]
        spec["traps"] = [{"id": "t_count", "type": "misleading_label", "surface": "tickets.csv",
                          "beatable_by": "count open rows", "probe": "count-only",
                          "provenance": "authored", "grounding": "status column", "grounded_in": "tickets.csv",
                          "checks": ["open_count"]}]
        spec["quality"] = {"semantic_checks": ids,
            "counterexamples": [
                {"id": "all-wrong", "reason": "Includes a closed record", "patches": everything, "fails": ids},
                {"id": "count-only", "reason": "Miscounts the open rows",
                 "patches": [{"file": "summary.json", "path": "open_count", "value": 3}], "fails": ["open_count"]}],
            "alternatives": [{"id": "different-order", "reason": "Order is explicitly irrelevant",
                "patches": [{"file": "summary.json", "path": "open_ids", "value": ["R-23", "R-21"]}]}],
            "difficulty_case": {"misreadings": [{"trap": "t_count", "counterexample": "all-wrong"}]}}
        build(spec, bundle)
        errors = controls(bundle)["advisories"]   # v2 (2026-10-02): misreading shape is advisory
        self.assertTrue(any("misreading of trap t_count" in e and "total_effort" in e for e in errors), errors)
        spec["quality"]["difficulty_case"]["misreadings"][0]["counterexample"] = "count-only"
        build(spec, bundle)
        report = controls(bundle)
        self.assertFalse(any("misreading of trap" in e for e in report["errors"] + report["advisories"]))

    def test_a_misreading_must_leave_an_objective_passing_and_be_its_own_answer(self):
        # Re-review: a trap that claims every objective let an all-wrong answer
        # stand as its misreading, and two traps could share one wrong answer
        # under two ids. Both are now EXECUTED through the exported grader.
        bundle = synthetic_bundle(self.root)
        spec = json.loads((bundle / "authoring/spec.json").read_text())
        ids = [c["id"] for c in spec["checks"] if c["kind"] == "objective"]
        everything = [{"file": "summary.json", "path": "open_ids", "value": ["R-21", "R-22", "R-23"]},
                      {"file": "summary.json", "path": "open_count", "value": 3},
                      {"file": "summary.json", "path": "total_effort", "value": 16}]
        count_only = [{"file": "summary.json", "path": "open_count", "value": 3}]
        trap = {"type": "misleading_label", "surface": "tickets.csv", "beatable_by": "count open rows",
                "probe": "count-only", "provenance": "authored", "grounding": "status column",
                "grounded_in": "tickets.csv"}
        spec["traps"] = [{**trap, "id": "t_all", "checks": ids}]
        spec["quality"] = {"semantic_checks": ids,
            "counterexamples": [
                {"id": "all-wrong", "reason": "Includes a closed record", "patches": everything, "fails": ids},
                {"id": "count-only", "reason": "Miscounts the open rows", "patches": count_only,
                 "fails": ["open_count"]},
                {"id": "count-again", "reason": "Miscounts the open rows (renamed)",
                 "patches": copy.deepcopy(count_only), "fails": ["open_count"]}],
            "alternatives": [{"id": "different-order", "reason": "Order is explicitly irrelevant",
                "patches": [{"file": "summary.json", "path": "open_ids", "value": ["R-23", "R-21"]}]}],
            "difficulty_case": {"misreadings": [{"trap": "t_all", "counterexample": "all-wrong"}]}}
        build(spec, bundle)
        errors = controls(bundle)["advisories"]   # v2 (2026-10-02): misreading shape is advisory
        self.assertTrue(any("misreading of trap t_all" in e and "passes no objective" in e
                            for e in errors), errors)
        # Losing two of three objectives passes one, and is still too many.
        two = everything[:2]
        spec["traps"] = [{**trap, "id": "t_two", "checks": ["open_ids", "open_count"]}]
        spec["quality"]["counterexamples"].append({"id": "two-wrong", "reason": "Includes a closed record",
                                                   "patches": two, "fails": ["open_ids", "open_count"]})
        spec["quality"]["difficulty_case"]["misreadings"] = [{"trap": "t_two", "counterexample": "two-wrong"}]
        build(spec, bundle)
        errors = controls(bundle)["advisories"]   # v2: misreading shape is advisory
        self.assertTrue(any("misreading of trap t_two" in e and "fails 2 of 3 objectives" in e
                            for e in errors), errors)
        spec["quality"]["counterexamples"].pop()
        spec["traps"] = [{**trap, "id": "t_count", "checks": ["open_count"]},
                         {**trap, "id": "t_recount", "checks": ["open_count"]}]
        spec["quality"]["difficulty_case"]["misreadings"] = [
            {"trap": "t_count", "counterexample": "count-only"},
            {"trap": "t_recount", "counterexample": "count-again"}]
        build(spec, bundle)
        errors = controls(bundle)["advisories"]   # v2: misreading shape is advisory
        self.assertTrue(any("t_recount" in e and "grades the same submission as count-only" in e
                            for e in errors), errors)
        self.assertFalse(any("passes no objective" in e for e in errors), errors)
        spec["traps"] = spec["traps"][:1]
        spec["quality"]["difficulty_case"]["misreadings"] = spec["quality"]["difficulty_case"]["misreadings"][:1]
        build(spec, bundle)
        report = controls(bundle)
        self.assertFalse(any("misreading of trap" in e for e in report["errors"] + report["advisories"]))

    def test_export_reproduction_catches_schema_grader_or_container_drift(self):
        bundle = synthetic_bundle(self.root)
        self.assertEqual(generated_problems(bundle), [])
        for rel in ("tests/checks.json", "environment/Dockerfile", "steps/01-summary/instruction.md"):
            path = bundle / rel
            before = path.read_bytes()
            path.write_bytes(before + b"\nchanged")
            self.assertTrue(any(rel in e for e in generated_problems(bundle)))
            path.write_bytes(before)

    def test_custom_grader_cannot_execute_on_controller(self):
        from pipeline.evaluate import exported_grade
        bundle = synthetic_bundle(self.root)
        marker = self.root / "should-not-exist"
        (bundle / "tests/criteria.py").write_text(f"from pathlib import Path\nPath({str(marker)!r}).touch()\n")
        with self.assertRaisesRegex(RuntimeError, "unaudited"):
            exported_grade(bundle, bundle / "solution/submission", "01-summary")
        self.assertFalse(marker.exists())

    def test_published_schema_runtime_is_exempt_only_when_exactly_reviewed(self):
        from pipeline.gates.findings import normalisation_gate
        from pipeline.gates.base import GateContext, Status
        bundle = synthetic_bundle(self.root)
        ctx = GateContext(task_dir=bundle, repo_root=self.root)
        self.assertIs(normalisation_gate.run(ctx).status, Status.PASS)
        path = bundle / "tests/_arena_runtime/contracts.py"
        path.write_text(path.read_text() + '\ndef custom(v):\n    return type(v) is int\n')
        self.assertIs(normalisation_gate.run(ctx).status, Status.FAIL)

    def test_a_qualification_repair_is_screened_before_it_is_remeasured(self):
        # A revision is a new task version. It is never accepted unmeasured, and
        # never sent straight into another ten-episode campaign: it waits for
        # its own 5 x 2 screen.
        from pipeline.release import qualify
        bundle = synthetic_bundle(self.root)
        blocked = {"artifact_sha256": identity(bundle), "status": "blocked", "release_ready": False,
                   "errors": ["semantic review: semantic reviewer requested revision"]}
        with patch("pipeline.release._qualify", side_effect=[copy.deepcopy(blocked), copy.deepcopy(blocked)]) as measured, \
             patch("pipeline.repair.feedback", return_value=["steps/01-summary/instruction.md: public ambiguity"]), \
             patch("pipeline.repair.revise", return_value={"archive": "retained"}) as revise:
            result = qualify(bundle, ["one", "two"], "critic", "solver", self.root / "native", repair_attempts=1)
        self.assertEqual(measured.call_count, 1)
        self.assertEqual(revise.call_count, 1)
        self.assertFalse(result["release_ready"])
        self.assertEqual(result["status"], "awaiting-screen")
        self.assertEqual(len(result["qualification_revisions"]), 1)

    def test_infrastructure_failure_does_not_rewrite_candidate(self):
        from pipeline.repair import feedback
        bundle = synthetic_bundle(self.root)
        with patch("pipeline.run.run_bundle", return_value={"verdict": "unverified"}):
            self.assertEqual(feedback(bundle, {"artifact_sha256": identity(bundle), "release_ready": False}), [])

    def test_qualification_does_not_retry_a_valid_rejection_of_the_same_task(self):
        from contextlib import ExitStack
        from pipeline.release import _qualify
        bundle = synthetic_bundle(self.root)
        spec = json.loads((bundle / "authoring/spec.json").read_text())
        spec["_producer"] = {"model": "author"}
        build(spec, bundle)
        sha = identity(bundle)
        atomic_json(bundle / "verification/semantic-review.json", {"artifact_sha256": sha, "model": "critic"})
        atomic_json(bundle / "verification/native-controls.json", {"artifact_sha256": sha,
            "oracle": str(self.root / "oracle"), "nop": str(self.root / "nop")})
        rejection = ["semantic reviewer requested revision", "unresolved review findings: privacy_findings"]
        with ExitStack() as stack:
            for name, value in {
                "pipeline.run.run_bundle": {"verdict": "green"},
                "pipeline.release._provenance_problems": [],
                "pipeline.corpus.problems": [],
                "pipeline.assurance.generated_problems": [],
                "pipeline.assurance.controls": {"ok": True},
                "pipeline.benchmark.harbor.doctor": {"ok": True},
                "pipeline.review.review_problems": rejection,
                "pipeline.release._evaluate": {"release_ready": False},
            }.items():
                stack.enter_context(patch(name, return_value=value))
            stack.enter_context(patch("pipeline.evidence.native_evidence", side_effect=lambda _b, _p, role, _minimum=1:
                ([], {"trials": [{"reward": 1 if role == "oracle" else 0}]})))
            critic = stack.enter_context(patch("pipeline.review.review"))
            solver = stack.enter_context(patch("pipeline.calibrate.run.campaign"))
            native = stack.enter_context(patch("pipeline.benchmark.harbor.run_campaign"))
            result = _qualify(bundle, ["one", "two"], "critic", "solver", self.root / "native")
        self.assertFalse(result["release_ready"])
        critic.assert_not_called()
        solver.assert_not_called()
        native.assert_not_called()

    def test_stale_or_invalid_review_is_not_a_retained_semantic_rejection(self):
        from pipeline.review import semantic_rejection
        self.assertTrue(semantic_rejection(["semantic reviewer requested revision"]))
        for problems in ([], ["semantic review is missing, stale or belongs to another task"],
                         ["semantic reviewer requested revision", "X: invalid review citation (quote absent or too short)"]):
            with self.subTest(problems=problems):
                self.assertFalse(semantic_rejection(problems))

    def test_a_requested_revision_survives_a_receipt_shape_defect(self):
        # e2e build, 2026-09-26: a "revise" whose `checks` carried extra meta
        # rows was classified "unverified", which the build does not repair.
        from pipeline.review import semantic_rejection
        self.assertTrue(semantic_rejection([
            "semantic reviewer requested revision", "unresolved review findings: substantive_gaps",
            "review must cover every check exactly once", "obj_a: check not independently justified"]))
        # ...but an incomplete receipt never stands in for a rejection on its own,
        # and never excuses an untrustworthy one.
        self.assertFalse(semantic_rejection(["review must cover every check exactly once"]))
        self.assertFalse(semantic_rejection(["semantic reviewer requested revision",
                                             "review must cover every check exactly once",
                                             "X: invalid review citation (quote absent or too short)"]))

    def test_a_quote_from_a_json_file_may_carry_its_escaping_undone(self):
        # a-069 (build 2026-09-26): quoting a grader regex from checks.json, the
        # reviewer wrote one backslash where the file stores two.
        from pipeline.review import _quoted
        stored = '"matches": "Кого\\\\s+помнить"'          # file bytes: Кого\\s+
        quote = '"matches": "Кого\\s+помнить"'             # as read:    Кого\s+
        self.assertTrue(_quoted(quote, stored, "private-grader/checks.json"))
        self.assertFalse(_quoted(quote, stored, "fixture/notes.md"))
        self.assertFalse(_quoted('"matches": "Кого\\s+забыть"', stored, "private-grader/checks.json"))

    def test_failed_summary_rows_preserve_a_verified_requested_revision(self):
        from pipeline.review import semantic_rejection
        for row in ("quality_difficulty_case_and_capability_plan", "quality_counterexamples", "semantic_novelty"):
            with self.subTest(row=row):
                problems = ["semantic reviewer requested revision",
                            "unresolved review findings: substantive_gaps",
                            f"{row}: review summary row did not pass"]
                self.assertTrue(semantic_rejection(problems))
                self.assertFalse(semantic_rejection(problems + [
                    "X: invalid review citation (quote absent or too short)"]))
                self.assertFalse(semantic_rejection(problems + [
                    "semantic review is missing, stale or belongs to another task"]))
                self.assertFalse(semantic_rejection(problems[2:]))

    def test_passing_summary_rows_do_not_void_a_complete_review(self):
        # Build 2026-09-26: five approved reviews appended summary rows such as
        # `review_semantic_novelty` and were read as unverified.
        from pipeline.review import _check_rows
        expected = {"obj_a": {}, "obj_b": {}}
        rows = [{"id": "obj_a", "verdict": "pass"}, {"id": "obj_b", "verdict": "pass"},
                {"id": "review_semantic_novelty", "verdict": "pass"}]
        errors, kept = _check_rows(rows, expected)
        self.assertEqual(errors, [])
        self.assertEqual([r["id"] for r in kept], ["obj_a", "obj_b"])
        # ...a failing summary row, a missing check or a duplicate still counts.
        self.assertIn("review_privacy: review summary row did not pass",
                      _check_rows(rows + [{"id": "review_privacy", "verdict": "fail"}], expected)[0])
        self.assertIn("review must cover every check exactly once", _check_rows(rows[1:], expected)[0])
        self.assertIn("review must cover every check exactly once", _check_rows(rows + rows[:1], expected)[0])

    def test_build_preserves_a_valid_semantic_rejection_without_rerolling(self):
        from pipeline.orchestrate import _review_candidate, Budget
        bundle = synthetic_bundle(self.root)
        work = "verification/reviews/retained/attempt"
        atomic_json(bundle / "verification/semantic-review.json", {"work_dir": work})
        atomic_json(bundle / work / "deliverables/review.json", {
            "checks": [{"id": "claim", "verdict": "revise", "reason": "unclear authority"}],
            "ambiguities": ["two conflicting editions"]})
        with patch("pipeline.review.review_problems", return_value=[
                "semantic reviewer requested revision", "quality_counterexamples: review summary row did not pass"]), \
             patch("pipeline.review.review") as critic:
            result = _review_candidate(bundle, Budget(1))
        self.assertEqual(result["verdict"], "blocked")
        self.assertIn("Semantic review claim: unclear authority", result["findings"])
        critic.assert_not_called()

    def test_build_critic_transport_failure_is_unverified_and_releases_budget(self):
        from pipeline.orchestrate import _review_candidate, Budget
        bundle = synthetic_bundle(self.root)
        spec = json.loads((bundle / "authoring/spec.json").read_text())
        spec["_producer"] = {"model": "claude-opus-5"}
        build(spec, bundle)
        budget = Budget(1)
        with patch.dict("os.environ", {"ARENA_REVIEW_MODEL": "gpt-5.6-sol"}), \
             patch("pipeline.review.review", side_effect=RuntimeError("provider unavailable")) as critic:
            result = _review_candidate(bundle, budget)
        self.assertEqual(result["verdict"], "unverified")
        self.assertIn("provider unavailable", result["findings"][0])
        self.assertEqual(budget.in_flight, 0)
        critic.assert_called_once_with(bundle, "gpt-5.6-sol")

    def test_wrong_native_oracle_reward_stops_before_paid_solver(self):
        from pipeline.release import _qualify
        from contextlib import ExitStack
        bundle = synthetic_bundle(self.root)
        spec = json.loads((bundle / "authoring/spec.json").read_text())
        spec["_producer"] = {"model": "author"}
        build(spec, bundle)
        with ExitStack() as stack:
            for name, value in {
                "pipeline.run.run_bundle": {"verdict": "green"},
                "pipeline.release._provenance_problems": [],
                "pipeline.corpus.problems": [],
                "pipeline.assurance.generated_problems": [],
                "pipeline.assurance.controls": {"ok": True},
                "pipeline.benchmark.harbor.doctor": {"ok": True},
                "pipeline.evidence.native_evidence": ([], {"trials": [{"reward": 0}]}),
                "pipeline.release._evaluate": {"release_ready": False},
            }.items():
                stack.enter_context(patch(name, return_value=value))
            native = stack.enter_context(patch("pipeline.benchmark.harbor.run_campaign", return_value={"ok": True}))
            solver = stack.enter_context(patch("pipeline.calibrate.run.campaign"))
            result = _qualify(bundle, ["one", "two"], "critic", "solver", self.root / "native")
        self.assertFalse(result["release_ready"])
        self.assertEqual(native.call_count, 1)
        solver.assert_not_called()
        self.assertIn("oracle", json.loads((bundle / "verification/native-controls.json").read_text()))

    def test_case_patches_do_not_mutate_reference_or_invent_fields(self):
        ref = {"out.json": {"rows": [{"x": 1}]}}
        case = {"patches": [{"file": "out.json", "path": "rows.0.x", "value": 2}]}
        self.assertEqual(case_values(case, ref)["out.json"]["rows"][0]["x"], 2)
        self.assertEqual(ref["out.json"]["rows"][0]["x"], 1)
        case["patches"][0]["path"] = "rows.0.missing"
        with self.assertRaises(KeyError):
            case_values(case, ref)

    def test_incremental_draft_persists_and_requires_complete_validation(self):
        from pipeline.author.agent_designer import _handlers
        from types import SimpleNamespace
        extraction = SimpleNamespace(session_id="synthetic", seed_index=0)
        path = self.root / "draft.json"
        handlers = _handlers(self.root, extraction, {}, path)
        handlers["stage_spec"](["checks"], [{"id": "first"}])
        handlers["stage_spec"](["checks"], [{"id": "second"}], append=True)
        handlers["stage_spec"](["checks", 0, "actual"], {"op": "field"})
        self.assertEqual(handlers["read_draft"](["checks", 0, "actual"]), {"op": "field"})
        self.assertFalse(handlers["check_draft"]()["clean"])
        reloaded = _handlers(self.root, extraction, {}, path)
        self.assertEqual(len(reloaded["read_draft"](["checks"])), 2)
        before = path.read_bytes()
        with self.assertRaises(ValueError):
            handlers["stage_spec"](["checks"], "bad append", append=True)
        self.assertEqual(path.read_bytes(), before)

    def test_latest_select_preserves_business_keys_and_rejects_ties(self):
        rows = [{"id": "B", "rev": 1, "amount": 90}, {"id": "A", "rev": 2, "amount": 40},
                {"id": "A", "rev": 1, "amount": 10}]
        path = self.root / "source.json"
        atomic_json(path, rows)
        source = {"op": "latest", "of": {"op": "rows", "file": path.name},
                  "by": ["id"], "order_by": "rev", "value_type": "number"}
        expr = {"op": "select", "of": source, "fields": {"account": "id", "approved": "amount"}}
        ws = Workspace(self.root, self.root)
        self.assertEqual(evaluate(expr, ws, "source"), [{"account": "B", "approved": 90}, {"account": "A", "approved": 40}])
        atomic_json(path, rows + [{"id": "A", "rev": 2, "amount": 400}])
        with self.assertRaisesRegex(CheckError, "tied"):
            evaluate(expr, ws, "source")

    def test_row_derivation_keeps_conclusions_attached_to_evidence(self):
        atomic_json(self.root / "accounts.json", [{"id": "B", "approved": 100, "paid": 40},
                                                  {"id": "A", "approved": 30, "paid": 20}])
        expr = {"op": "derive_rows", "of": {"op": "rows", "file": "accounts.json"},
                "fields": {"id": {"op": "field", "path": "id"}, "balance": {"op": "subtract",
                    "a": {"op": "field", "path": "approved"}, "b": {"op": "field", "path": "paid"}}}}
        self.assertEqual(evaluate(expr, Workspace(self.root, self.root), "source"),
                         [{"id": "B", "balance": 60}, {"id": "A", "balance": 10}])
        conditional = {"op": "if", "where": {"field": "signed", "eq": True},
            "then": {"op": "field", "path": "amount"},
            "else": {"op": "literal", "value": "unresolved", "why": "Public rule requires signed approval"}}
        self.assertEqual(row_value(conditional, {"signed": False}), "unresolved")
        with self.assertRaises(CheckError):
            row_value(conditional, {"signed": True})
        deadline = {"op": "date_add", "date": {"op": "field", "path": "start"},
                    "days": {"op": "field", "path": "days"}}
        self.assertEqual(row_value(deadline, {"start": "2024-02-28", "days": 2}), "2024-03-01")

    def test_derivation_detection_uses_operations_not_names_or_justifications(self):
        from pipeline.author.designer import _target_has_derivation, _target_reads_headings
        copied = {"op": "pluck", "field": "heading", "of": {"op": "rows", "file": "join_difference.jsonl"}}
        self.assertFalse(_target_has_derivation(copied, []))
        self.assertTrue(_target_reads_headings(copied))
        copied["field"] = "text"
        copied["basis"] = "Explain this section; compare every heading."
        self.assertFalse(_target_reads_headings(copied))
        derived = {"op": "derive_rows", "of": copied["of"], "fields": {
            "balance": {"op": "subtract", "a": {"op": "field", "path": "approved"},
                        "b": {"op": "field", "path": "paid"}}}}
        self.assertTrue(_target_has_derivation(derived, []))
        derived["fields"]["balance"] = {"op": "field", "path": "approved"}
        self.assertFalse(_target_has_derivation(derived, []))
        self.assertTrue(_target_has_derivation(copied, [{"as": "join_difference.jsonl", "op": "join"}]))

    def test_formatted_source_amounts_produce_graded_subtotals(self):
        from pipeline.evaluate import exported_grade
        bundle = synthetic_bundle(self.root)
        atomic_json(bundle / "environment/files/costs.json", [
            {"item": "base", "range": "$30,000–40,000"},
            {"item": "addition", "range": "+$8,000–15,000"}])
        rows = {"op": "derive_rows", "of": {"op": "rows", "file": "costs.json"}, "fields": {
            bound: {"op": "range_bound", "of": {"op": "field", "path": "range"}, "bound": bound}
            for bound in ("lower", "upper")}}
        target = {"op": "record", "fields": {bound: {"op": "sum", "of": rows, "field": bound}
                                                for bound in ("lower", "upper")}}
        from pipeline.author.validate import _walk
        problems = []
        _walk(target, "subtotal.target", {"costs.json"}, problems)
        self.assertEqual(problems, [])
        spec = json.loads((bundle / "authoring/spec.json").read_text())
        schema = spec["outputs"][0]["schema"]
        schema["properties"]["subtotal"] = {"type": "object", "properties": {
            "lower": {"type": "integer"}, "upper": {"type": "integer"}},
            "required": ["lower", "upper"], "additionalProperties": False}
        schema["required"].append("subtotal")
        spec["solution"]["summary.json"]["subtotal"] = {"lower": 38000, "upper": 55000}
        spec["checks"].append({"id": "subtotal", "kind": "objective", "weight": 1,
            "basis": "Sum both endpoints of all cost ranges, including the addition.", "assertion": "equals",
            "actual": {"op": "field", "file": "summary.json", "path": "subtotal"}, "target": target})
        build(spec, bundle)
        submitted = self.root / "answer"
        atomic_json(submitted / "summary.json", spec["solution"]["summary.json"])
        self.assertEqual(exported_grade(bundle, submitted, "01-summary")["reward"], 1)
        spec["solution"]["summary.json"]["subtotal"]["lower"] = 1
        atomic_json(submitted / "summary.json", spec["solution"]["summary.json"])
        grade = exported_grade(bundle, submitted, "01-summary")
        self.assertLess(grade["reward"], 1)
        self.assertFalse(grade["checks"]["subtotal"]["passed"])
        self.assertTrue(grade["checks"]["open_ids"]["passed"])

    def test_scalar_parsing_refuses_ambiguous_amounts_and_dates(self):
        for text in ("$1 or $2", "$1–RMB2", "1,23", "$20–10", "Infinity"):
            with self.assertRaises(CheckError):
                row_value({"op": "range_bound", "of": {"op": "field", "path": "value"}, "bound": "lower"}, {"value": text})
        self.assertEqual(row_value({"op": "number", "of": {"op": "field", "path": "value"}},
                                   {"value": "HK$1,234.50"}), 1234.5)
        extract = {"op": "extract", "of": {"op": "field", "path": "note"}, "pattern": r"\d{1,2}/\d{1,2}"}
        date = {"op": "parse_date", "of": extract, "format": "%m/%d", "year": 2025}
        self.assertEqual(row_value(date, {"note": "9/7鋪磚前"}), "2025-09-07")
        with self.assertRaises(CheckError):
            row_value(date, {"note": "9/7 or 9/8"})
        del date["year"]
        with self.assertRaisesRegex(CheckError, "year"):
            row_value(date, {"note": "9/7鋪磚前"})
        compare = {"op": "compare", "a": {"op": "field", "path": "appointment"},
            "b": {"op": "field", "path": "completion"}, "value_type": "date", "comparison": "lt"}
        self.assertTrue(row_value(compare, {"appointment": "2025-08-09", "completion": "2025-08-14"}))
        self.assertFalse(row_value(compare, {"appointment": "2025-08-19", "completion": "2025-08-14"}))

    def test_row_parser_does_not_drop_invalid_or_ambiguous_evidence(self):
        ws = Workspace(self.root, self.root)
        for name, raw in (("rows.json", '[{"a":1},null]'), ("rows.jsonl", '{"a":1,"a":2}'),
                          ("rows.csv", "a,a\n1,2\n"), ("rows.csv", "a,b\n1\n"),
                          ("rows.json", '{"one":[],"two":[]}')):
            (self.root / name).write_text(raw)
            with self.assertRaises(SubmissionInvalid):
                evaluate({"op": "rows", "file": name}, ws, "submitted")
            with self.assertRaises(CheckError):
                evaluate({"op": "rows", "file": name}, ws, "source")

    def test_set_operations_preserve_objects_and_boolean_types(self):
        ws = Workspace(self.root, self.root)
        atomic_json(self.root / "a.json", [{"id": "a", "approved": True}, {"id": "b", "approved": False}])
        atomic_json(self.root / "b.json", [{"id": "a", "approved": 1}])
        expr = {"op": "difference", "a": {"op": "rows", "file": "a.json"},
                "b": {"op": "rows", "file": "b.json"}}
        result = evaluate(expr, ws, "source")
        self.assertCountEqual(result, [{"id": "a", "approved": True}, {"id": "b", "approved": False}])
        self.assertTrue(all(isinstance(r, dict) for r in result))

    def test_set_operations_keep_the_published_case(self):
        # a-067: `difference` handed back "t12" for the fixture's "T12", the
        # derived reference wrote it, and the output pattern ^T[0-9]+$ refused
        # it. Membership still ignores case; the value keeps its spelling.
        ws = Workspace(self.root, self.root)
        atomic_json(self.root / "a.json", [{"code": c} for c in ("T2", "T12", "t12", " T9 ", "1,200", "T3")])
        atomic_json(self.root / "b.json", [{"code": "t3"}])
        atomic_json(self.root / "c.json", [{"Code": "T1"}, {"code": "t1"}])
        a = {"op": "pluck", "field": "code", "of": {"op": "rows", "file": "a.json"}}
        b = {"op": "pluck", "field": "code", "of": {"op": "rows", "file": "b.json"}}
        drop = {"op": "difference", "a": a, "b": b}
        self.assertEqual(evaluate(drop, ws, "source"), [1200, "T12", "T2", "T9"])
        keep = {"op": "intersection", "a": a, "b": b}
        self.assertEqual(evaluate(keep, ws, "source"), ["T3"])
        rows = {"op": "unique", "of": {"op": "rows", "file": "c.json"}}
        self.assertEqual(evaluate(rows, ws, "source"), [{"Code": "T1"}])

    def test_markdown_tables_preserve_cells_ignore_fences_and_reject_bad_rows(self):
        rows = markdown_tables('```\n| hidden |\n|---|\n| fake |\n```\n| ID | Meaning |\n|---|---|\n| A | one\\|two |\n')
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["Meaning"], "one|two")
        with self.assertRaises(ValueError):
            markdown_tables("| A | B |\n|---|---|\n| bad |\n")

    def test_stem_matching_keeps_unicode_and_full_stems(self):
        rows = stem_overlap([{"stem": "如何審核最新版本？"}, {"stem": "a" * 65 + " right"}],
                            {"source": [{"stem": "如何審核最新版本？"}, {"stem": "a" * 65 + " wrong"}]})
        self.assertEqual(rows[0]["shared"], 1)

    def test_large_integers_and_nonfinite_text_do_not_alias(self):
        value = 2**100 + 1
        self.assertEqual(normalise(str(value)), value)
        self.assertNotEqual(normalise(value), normalise(value - 1))
        self.assertEqual(normalise("Infinity"), "infinity")
        self.assertEqual(schema_errors(10**1000, {"type": "number"}), [])

    def test_provider_budget_releases_slot_after_exception_and_stops(self):
        budget = RequestBudget(concurrency=1, max_requests=2)
        with self.assertRaises(ValueError):
            with budget.slot():
                raise ValueError("transport fault")
        with budget.slot():
            pass
        from pipeline.provider import ProviderBudgetExhausted
        with self.assertRaisesRegex(ProviderBudgetExhausted, "budget exhausted"):
            with budget.slot():
                pass

    def test_privacy_redacts_trace_excerpts_without_printing_values(self):
        from pipeline.privacy import redact_excerpt, scan
        text = "person@company.test sk-proj-" + "x" * 30
        self.assertNotIn("person@", redact_excerpt(text))
        self.assertNotIn("sk-proj-", redact_excerpt(text))
        (self.root / "source.txt").write_text(text)
        self.assertEqual({f["kind"] for f in scan(self.root)}, {"credential", "email"})
        self.assertNotIn(text, json.dumps(scan(self.root)))

    def test_trace_citations_require_the_actual_user_and_quote(self):
        from pipeline.ledger.faithfulness import citation_problems
        trace = {"messages": [{"role": "assistant", "content": "Assistant-only invented constraint."},
                              {"role": "user", "content": "Keep the approved scope unchanged."}]}
        trap = {"id": "scope", "provenance": "trace_derived", "derived_from": "session1::msg1",
                "quote": "Keep the approved scope unchanged."}
        self.assertEqual(citation_problems({"traps": [trap]}, trace, "session1"), [])
        trap["derived_from"] = "session1::msg0"
        self.assertEqual(citation_problems({"traps": [trap]}, trace, "session1"), [])
        trap["quote"] = "Assistant-only invented constraint."
        self.assertTrue(citation_problems({"traps": [trap]}, trace, "session1"))
        trap["derived_from"] = "different::msg1"
        self.assertTrue(citation_problems({"traps": [trap]}, trace, "session1"))

    def test_source_identity_cannot_disagree_with_verified_ledger(self):
        from pipeline.release import _provenance_problems
        bundle = synthetic_bundle(self.root)
        atomic_json(bundle / "provenance/ledger.json", {"source": {"session_id": "different", "seed_index": 0}})
        self.assertEqual(_provenance_problems(bundle), ["authoring source and provenance ledger identify different source seeds"])

    def test_release_catalog_rejects_reskin_and_accepts_idempotent_registration(self):
        bundle = synthetic_bundle(self.root / "one")
        release = {"release_ready": True, "artifact_sha256": identity(bundle), "policy_sha256": "test-policy"}
        root = self.root / "catalog"
        self.assertEqual(register(bundle, release, root), [])
        self.assertEqual(register(bundle, release, root), [])
        other = synthetic_bundle(self.root / "two")
        (other / "steps/01-summary/instruction.md").write_text("Renamed task with identical evidence.")
        self.assertTrue(related(signature(bundle), signature(other)))
        release["artifact_sha256"] = identity(other)
        self.assertTrue(register(other, release, root))

    def test_replacement_review_distinguishes_baseline_from_competing_peer(self):
        from pipeline.corpus import review_context
        baseline = synthetic_bundle(self.root / 'envs-old')
        peer = synthetic_bundle(self.root / 'envs-peer')
        (peer / 'steps/01-summary/instruction.md').write_text('Another task over the same source.')
        candidate = synthetic_bundle(self.root / 'draft')
        atomic_json(candidate / 'provenance/replacement.json', {
            'schema': 'arena-pipeline/replacement/1', 'predecessors': [identity(baseline)],
            'reason': 'Rebuild the old task to repair grading defects.'})
        context = review_context(candidate, self.root)
        self.assertEqual(context['design_mode'], 'replacement')
        self.assertEqual({r['artifact_sha256']: r['relationship'] for r in context['peers']}, {
            identity(baseline): 'predecessor', identity(peer): 'peer'})
        # Declaring lineage is not permission to register both versions.
        catalog = self.root / 'catalog'
        release = {'release_ready': True, 'artifact_sha256': identity(baseline), 'policy_sha256': 'test'}
        self.assertEqual(register(baseline, release, catalog), [])
        release['artifact_sha256'] = identity(candidate)
        self.assertTrue(register(candidate, release, catalog))

    def test_missing_or_unrelated_replacement_baseline_is_not_exempted(self):
        from pipeline.corpus import review_context
        candidate = synthetic_bundle(self.root / 'draft')
        declaration = {'schema': 'arena-pipeline/replacement/1',
                       'predecessors': ['0' * 64], 'reason': 'Rebuild.'}
        atomic_json(candidate / 'provenance/replacement.json', declaration)
        with self.assertRaisesRegex(ValueError, 'missing or changed'):
            review_context(candidate, self.root)
        baseline = synthetic_bundle(self.root / 'envs-old')
        spec_path = baseline / 'authoring/spec.json'
        spec = json.loads(spec_path.read_text())
        spec['source'] = {'session_id': 'unrelated-session', 'seed_index': 0}
        atomic_json(spec_path, spec)
        (baseline / 'environment/files/tickets.csv').write_text('different,source\n1,2\n')
        (baseline / 'environment/files/unprojected.txt').write_text('unrelated')
        declaration['predecessors'] = [identity(baseline)]
        atomic_json(candidate / 'provenance/replacement.json', declaration)
        with self.assertRaisesRegex(ValueError, 'unrelated source family'):
            review_context(candidate, self.root)

    def test_identical_staged_candidate_and_peer_copies_do_not_change_review_context(self):
        import shutil
        from pipeline.corpus import review_context
        candidate = synthetic_bundle(self.root / 'draft')
        peer = synthetic_bundle(self.root / 'envs-peer')
        (peer / 'steps/01-summary/instruction.md').write_text('Different task using shared data.')
        before = review_context(candidate, self.root)
        shutil.copytree(candidate, self.root / 'envs-staged' / candidate.name)
        shutil.copytree(peer, self.root / 'reference' / peer.name)
        self.assertEqual(review_context(candidate, self.root), before)

    def test_a_tasks_own_delivered_copy_is_not_a_same_source_peer(self):
        # envs-final-2, 2026-09-27: delivery renames the package inside the
        # identity, so re-releasing each source saw its own delivered copy as
        # an unreviewed same-source peer and blocked all eight.
        import shutil
        from pipeline.artifacts import inventory
        from pipeline.corpus import review_context
        candidate = synthetic_bundle(self.root / 'draft')
        before = review_context(candidate, self.root)
        copy = self.root / 'envs-final-t' / 'F2-scenario' / 'a_f2_synthetic'
        shutil.copytree(candidate, copy)
        toml = (copy / 'task.toml').read_text()
        (copy / 'task.toml').write_text(toml.replace('name = "', 'name = "arena/a_f2_', 1))
        atomic_json(copy / 'verification/delivery.json',
                    {"source_inventory": inventory(candidate)})
        self.assertNotEqual(identity(copy), identity(candidate))
        self.assertEqual(review_context(candidate, self.root), before)
        # Any change beyond the two sanctioned rewrites makes it a real peer.
        (copy / 'steps/01-summary/instruction.md').write_text('A different task on the same data.')
        names = [p['name'] for p in review_context(candidate, self.root)['peers']]
        self.assertIn('a_f2_synthetic', names)

    def test_missing_release_evidence_never_accepts_a_working_reference(self):
        from pipeline.release import evaluate as release
        bundle = synthetic_bundle(self.root)
        report = release(bundle)
        self.assertFalse(report["release_ready"])
        self.assertEqual(report["status"], "blocked")
        for stage in ("calibration:", "semantic review:", "native:"):
            self.assertTrue(any(e.startswith(stage) for e in report["errors"]), report["errors"])
        # The blind solve is optional diagnostic evidence (policy.BLIND_SOLVE_GATES_RELEASE).
        self.assertFalse(any(e.startswith("blind solve:") for e in report["errors"]), report["errors"])

    def test_manifest_detects_removal_and_new_files(self):
        (self.root / "jobs").mkdir()
        p = self.root / "jobs/result.json"
        p.write_text('{}')
        old = evidence_inventory(self.root, ("jobs",))
        p.unlink()
        self.assertNotEqual(evidence_inventory(self.root, ("jobs",)), old)
        p.write_text('{}')
        (self.root / "jobs/extra.json").write_text('{}')
        self.assertNotEqual(evidence_inventory(self.root, ("jobs",)), old)

    def test_native_capped_zero_is_void_before_aggregation(self):
        from pipeline.benchmark.harbor import parse_trial, summarize
        folder = self.root / "trial"
        details = {"reward": {"kind": "programmatic", "score": 0, "criteria": [
            {"name": "c", "value": 0, "status": "evaluated", "gated_out": False}]}}
        atomic_json(folder / "steps/01-task/verifier/reward-details.json", details)
        step = {"step_name": "01-task", "agent_result": {"metadata": {
            "n_episodes": 2, "all_messages": [{"role": "assistant", "content": "attempted"}]}},
            "verifier_result": {"rewards": {"reward": 0}}}
        data = {"step_results": [step], "verifier_result": {"rewards": {"reward": 0}}}
        path = folder / "result.json"
        atomic_json(path, data)
        trial = parse_trial(path, ["01-task"], solver=True)
        self.assertTrue(trial["valid"], trial)
        self.assertEqual(trial["zero_class"], "model_failure")
        step["agent_result"]["metadata"]["n_episodes"] = 40
        atomic_json(path, data)
        trial = parse_trial(path, ["01-task"], solver=True)
        self.assertEqual(trial["zero_class"], "void")
        self.assertEqual(summarize([trial], 1)["valid"], 0)

    def test_a_validated_build_spends_no_solver_episode(self):
        # The in-build difficulty repair is gone: a green build is validated in
        # one design, and nothing measures it until the batch screen.
        from pipeline.tests.test_guards import GateRepairLoop
        result, calls = GateRepairLoop()._patched_build_one(["green"])
        self.assertEqual(len(calls), 1)
        self.assertEqual(result.status, "validated")

    def test_rebuild_refuses_existing_symlink_output(self):
        bundle = synthetic_bundle(self.root)
        target = self.root / "untouched"
        target.write_text("keep")
        path = bundle / "steps/01-summary/instruction.md"
        path.unlink()
        path.symlink_to(target)
        with self.assertRaises(ValueError):
            build(json.loads((bundle / "authoring/spec.json").read_text()), bundle)
        self.assertEqual(target.read_text(), "keep")


if __name__ == "__main__":
    unittest.main()


class NativeEvidenceFeedsMetrics(unittest.TestCase):
    """Native campaigns carry `trials`; metrics and attribution read `rollouts`.

    Without the adapter every native campaign measured 0 valid episodes: pass@1
    None, attribution empty, and release blaming voids that did not exist.
    """

    def trial(self, tid, value, valid=True):
        return {"id": tid, "valid": valid, "errors": [] if valid else ["stalled"], "steps": [
            {"name": "01-task", "valid": valid, "reward": float(value), "errors": [],
             "agent_result": {"metadata": {"n_episodes": 7}},
             "checks": {"reward/o1": {"value": value, "gated_out": False}}}]}

    def test_passes_failures_and_voids_reach_the_rates(self):
        from pipeline.evidence import rollouts
        from pipeline.metrics import task_metrics
        from pipeline.attribution import attribute
        trials = [self.trial(f"t{i}", 1 if i < 3 else 0) for i in range(10)]
        trials.append(self.trial("t10", 0, valid=False))
        report = {"model": "m", "step_names": ["01-task"], "rollouts": rollouts(trials, ["01-task"])}
        metrics = task_metrics(report)
        self.assertEqual((metrics["episodes_valid"], metrics["episodes_void"], metrics["passes"]), (10, 1, 3))
        self.assertAlmostEqual(metrics["pass_at_1"], 0.3)
        with unittest.mock.patch("pipeline.attribution.contract_check_ids", return_value=set()):
            counts = attribute(Path("unused"), report)["counts"]
        self.assertEqual(counts, {"pass": 3, "capability": 7, "void": 1})


class CalibrationCannotBeShopped(unittest.TestCase):
    """Release takes one frozen campaign per spec model, and refuses the rest."""

    def evaluate(self, camps, reject=()):
        from contextlib import ExitStack
        from pipeline.release import _evaluate
        from pipeline.tests.test_production import synthetic_bundle

        def measured(model, passes, tokens=None):
            rows = [{"episode": i, "step": "01-task", "reward": 1.0 if i < passes else 0.3,
                     "zero_class": None, "stop_reason": "end_turn", "tool_calls": 3, "checks": {}}
                    for i in range(10)]
            return {"model": model, "rollouts": rows, "step_names": ["01-task"], "by_step": {},
                    "effort": "high", "protocol": "p",
                    "limits": {"no_limits": True,
                               "max_output_tokens": tokens or policy.output_tokens_for(model)}}
        fake = {name: measured(*spec) for name, spec in camps.items()}
        with tempfile.TemporaryDirectory() as tmp, ExitStack() as stack:
            bundle = synthetic_bundle(Path(tmp))
            atomic_json(bundle / "verification/native-calibrations.json",
                        {"artifact_sha256": identity(bundle), "campaigns": list(fake)})
            stack.enter_context(patch("pipeline.evidence.native_evidence",
                                      side_effect=lambda b, p, a, minimum=1: ([], fake[str(p)])))
            stack.enter_context(patch("pipeline.attribution.problems",
                                      side_effect=lambda b, m: ["unclassified"] if any(m is fake[r] for r in reject) else []))
            errors = _evaluate(bundle)["errors"]
        return [e for e in errors if e.startswith("calibration")]

    def test_retired_model_is_refused(self):
        errors = self.evaluate({"a": ("anthropic/claude-fable-5-1", 1), "b": ("openai/gpt-5.6-sol", 1)})
        self.assertTrue(any("gpt-5.6-sol" in e for e in errors), errors)

    def test_a_better_rerun_cannot_replace_a_worse_campaign(self):
        errors = self.evaluate({"a": ("anthropic/claude-fable-5-1", 9), "b": ("anthropic/claude-fable-5-1", 2),
                                "c": ("openai/gpt-6-astra", 1)})
        self.assertTrue(any("more than one campaign" in e for e in errors), errors)

    def test_a_rejected_campaign_blocks_rather_than_disappears(self):
        errors = self.evaluate({"a": ("anthropic/claude-fable-5-1", 1), "b": ("openai/gpt-6-astra", 1),
                                "c": ("openai/gpt-4o", 1)}, reject=("a",))
        self.assertTrue(any("rejected campaign" in e for e in errors), errors)

    def test_a_clean_spec_pair_is_not_refused_here(self):
        self.assertEqual(self.evaluate({"a": ("anthropic/claude-fable-5-1", 1),
                                        "b": ("openai/gpt-6-astra", 1)}), [])
