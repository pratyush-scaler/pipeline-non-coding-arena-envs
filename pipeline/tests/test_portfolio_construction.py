"""Portfolio planning is private; its declared depth is not measured hardness."""
from copy import deepcopy
from pathlib import Path
from types import SimpleNamespace
import tempfile
import unittest

from pipeline.author import agent_designer, challenge, portfolio


def arguments():
    return {"workflow": "contract_applicability", "source_fit": "Audit the source matter's remaining closing obligations.",
        "records": [{"id": "agreement-one", "decision": "first-obligation", "sources": ["one.md", "deal.md"],
            "checks": ["one-trigger", "one-notice"], "discriminators": ["entity", "transaction", "exception"]},
            {"id": "agreement-two", "decision": "second-obligation", "sources": ["two.md", "deal.md"],
            "checks": ["two-obligation"], "discriminators": ["entity", "threshold", "waiver-scope"]},
            {"id": "agreement-three", "decision": "third-obligation", "sources": ["three.md"],
            "checks": ["three-obligation"], "discriminators": ["entity", "period"]}],
        "shared_inputs": [{"id": "closing", "sources": ["deal.md"],
            "records": ["agreement-one", "agreement-two"], "public_convention": "Committed closing, not a projected postponement."}],
        "wrong_policies": [{"id": "consent-is-notice", "records": ["agreement-one", "agreement-two"]}]}


class PortfolioConstruction(unittest.TestCase):
    def test_source_grounded_outline_supplies_no_answer_or_hardness_certificate(self):
        result = portfolio.plan_portfolio(**arguments())
        self.assertEqual(result["declared_decision_groups"], 3)
        self.assertEqual(len(result["source_control_outlines"]), 5)
        self.assertTrue(result["private_authoring_only"])
        for flag in ("source_fit_established", "independence_established", "predicts_model_failure",
                     "creates_validity_blockers", "adds_or_refunds_attempts", "writes_public_or_reference_files"):
            self.assertFalse(result[flag])
        self.assertTrue(result["grading_outline"]["no_llm_judge"])
        self.assertTrue(result["grading_outline"]["unchanged_objective_band_limits"])

    def test_related_fields_and_repeated_records_do_not_multiply_judgment_groups(self):
        request = arguments()
        request["records"][1]["decision"] = "first-obligation"
        result = portfolio.plan_portfolio(**request)
        self.assertEqual(result["declared_decision_groups"], 2)
        first = result["decision_groups"][0]
        self.assertEqual(first["checks"], ["one-notice", "one-trigger", "two-obligation"])
        self.assertEqual(first["records"], ["agreement-one", "agreement-two"])
        self.assertTrue(result["grading_outline"]["no_per_field_independence_claim"])

    def test_shared_input_rechecks_all_consumers_and_preserves_the_others(self):
        result = portfolio.plan_portfolio(**arguments())
        control = result["shared_input_controls"][0]
        self.assertEqual(control["recompute_records"], ["agreement-one", "agreement-two"])
        self.assertEqual(control["preserve_records"], ["agreement-three"])
        self.assertTrue(control["answers_may_remain_unchanged"])
        self.assertTrue(control["one_upstream_error_is_one_failure_cause"])

    def test_one_source_intervention_cannot_assume_all_other_decisions_are_unaffected(self):
        controls = portfolio.plan_portfolio(**arguments())["source_control_outlines"]
        self.assertTrue(all(control["isolate_decision_or_declare_shared_cascade"] for control in controls))
        self.assertTrue(all(control["preserve_only_causally_unaffected_decisions"] for control in controls))

    def test_wrong_policy_is_applied_to_its_whole_record_set_at_every_affected_step(self):
        result = portfolio.plan_portfolio(**arguments())
        control = result["wrong_policy_controls"][0]
        self.assertEqual(control["apply_consistently_to_records"], ["agreement-one", "agreement-two"])
        self.assertTrue(control["apply_at_every_affected_step"])
        self.assertTrue(control["observed_failures_required"])

    def test_every_discriminator_requires_witness_promotion_and_invariance(self):
        result = portfolio.plan_portfolio(**arguments())
        for record, outline in zip(arguments()["records"], result["record_near_miss_outlines"]):
            self.assertEqual(outline["discriminators_requiring_public_witnesses"], record["discriminators"])
            self.assertTrue(outline["promotion_and_invariance_controls_required"])

    def test_planning_never_mutates_inputs_or_shares_recipe_lists(self):
        request = arguments()
        before = deepcopy(request)
        result = portfolio.plan_portfolio(**request)
        result["decision_groups"][0]["records"].append("unrelated")
        result["shared_input_controls"][0]["sources"].clear()
        result["recipe"]["distinctions"].clear()
        self.assertEqual(request, before)
        self.assertTrue(portfolio.plan_portfolio(**request)["recipe"]["distinctions"])

    def test_no_eight_record_or_eight_decision_validity_quota_is_added(self):
        request = arguments()
        request["records"] = request["records"][:2]
        request["records"][1]["decision"] = "first-obligation"
        result = portfolio.plan_portfolio(**request)
        self.assertEqual(result["declared_decision_groups"], 1)
        self.assertFalse(result["creates_validity_blockers"])

    def test_supported_nonlegal_workflows_do_not_force_contract_semantics(self):
        for workflow in ("portfolio_reconciliation", "dependency_readiness"):
            request = arguments()
            request["workflow"] = workflow
            result = portfolio.plan_portfolio(**request)
            self.assertEqual(result["workflow"], workflow)
            self.assertNotIn("assignment versus change of control", result["recipe"]["distinctions"])

    def test_absent_or_empty_shared_inputs_and_policies_are_static_portfolios(self):
        request = arguments()
        for value in (None, []):
            request.update(shared_inputs=value, wrong_policies=value)
            result = portfolio.plan_portfolio(**request)
            self.assertEqual(result["shared_input_controls"], [])
            self.assertEqual(result["wrong_policy_controls"], [])

    def test_invalid_workflow_or_missing_source_fit_cannot_invent_an_engagement(self):
        for key, value in (("workflow", "unknown"), ("workflow", []), ("source_fit", " "), ("source_fit", None)):
            request = arguments()
            request[key] = value
            with self.subTest(key=key, value=value), self.assertRaises(ValueError):
                portfolio.plan_portfolio(**request)

    def test_missing_extra_answer_or_malformed_record_fields_are_rejected(self):
        for change in (lambda record: record.pop("decision"), lambda record: record.update(answer=True),
                       lambda record: record.update(sources=[]), lambda record: record.update(checks=["one", "ONE"]),
                       lambda record: record.update(discriminators=[None]), lambda record: record.update(decision=[])):
            request = arguments()
            change(request["records"][0])
            with self.subTest(change=change), self.assertRaises(ValueError):
                portfolio.plan_portfolio(**request)

    def test_repeated_normalized_record_ids_are_not_extra_cases(self):
        for identifier in ("agreement-one", "AGREEMENT-ONE", " agreement-one "):
            request = arguments()
            request["records"][1]["id"] = identifier
            with self.subTest(identifier=identifier), self.assertRaises(ValueError):
                portfolio.plan_portfolio(**request)

    def test_one_check_cannot_be_claimed_by_two_judgment_groups(self):
        request = arguments()
        request["records"][1]["checks"].append("ONE-TRIGGER")
        with self.assertRaisesRegex(ValueError, "two independent"):
            portfolio.plan_portfolio(**request)

    def test_ambiguous_spellings_cannot_split_one_group_into_two(self):
        request = arguments()
        request["records"][1]["decision"] = "FIRST-OBLIGATION"
        with self.assertRaisesRegex(ValueError, "unambiguous spelling"):
            portfolio.plan_portfolio(**request)

    def test_shared_inputs_need_known_consumers_and_a_public_convention(self):
        for changes in ({"records": ["missing"]}, {"records": []}, {"public_convention": " "},
                        {"sources": ["missing.md"]}, {"sources": ["one.md"]}):
            request = arguments()
            request["shared_inputs"][0].update(changes)
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                portfolio.plan_portfolio(**request)

    def test_duplicate_shared_inputs_and_unknown_wrong_policy_scope_are_rejected(self):
        request = arguments()
        request["shared_inputs"].append(deepcopy(request["shared_inputs"][0]))
        with self.assertRaises(ValueError):
            portfolio.plan_portfolio(**request)
        request = arguments()
        request["wrong_policies"][0]["records"] = ["unknown"]
        with self.assertRaises(ValueError):
            portfolio.plan_portfolio(**request)

    def test_tool_is_registered_and_uses_the_staged_stretch_profile_without_writes(self):
        tools = {tool["name"]: tool for tool in agent_designer._tools(0)}
        self.assertIn("plan_portfolio", tools)
        with tempfile.TemporaryDirectory() as temporary:
            bundle = Path(temporary)
            handlers = agent_designer._handlers(bundle, SimpleNamespace(moments=[]), {"messages": []})
            before = {path.relative_to(bundle).as_posix(): path.read_bytes() for path in bundle.rglob("*") if path.is_file()}
            result = handlers["plan_portfolio"](**arguments())
            after = {path.relative_to(bundle).as_posix(): path.read_bytes() for path in bundle.rglob("*") if path.is_file()}
        self.assertEqual(before, after)
        from pipeline.policy import BAND_LIMITS     # v2: widened, read from policy
        self.assertEqual(result["stretch_checks"]["maximum"], BAND_LIMITS["stretch"][1])
        self.assertFalse(result["writes_public_or_reference_files"])

    def test_first_author_and_manual_hardening_share_the_same_source_fit_rules(self):
        for text in (agent_designer.SYSTEM, challenge.redesign_brief({})):
            self.assertIn("plan_portfolio", text)
            self.assertIn("assignment from change of control", text)
            self.assertIn("independent errors", text)
            self.assertIn("REPAIR-ONLY brief takes precedence", text)

    def test_diagnostics_link_declarations_without_reading_or_leaking_answers(self):
        request = arguments()
        spec = {"quality": {"portfolio_plan": request, "decisions": [{"id": record["decision"], "checks": record["checks"]}
            for record in request["records"]], "solver_trajectory": "secret trajectory", "reference_answers": "secret answer"}}
        result = challenge.construction_diagnostics(spec)["portfolio"]
        self.assertTrue(result["checks_linked_to_declared_decisions"])
        self.assertEqual(result["declared_decision_groups"], 3)
        self.assertFalse(result["independence_established"])
        self.assertNotIn("secret", str(result))

    def test_malformed_or_unlinked_optional_profile_is_advisory_not_a_validity_gate(self):
        for declaration in (False, [], {"workflow": "unknown"}):
            spec = {"quality": {"portfolio_plan": declaration}}
            result = portfolio.construction_diagnostics(spec)
            self.assertIn("planning_advisory", result)
            self.assertFalse(result["creates_validity_blockers"])
        for decisions in (None, [], [{"id": "first-obligation", "checks": [{}]}]):
            result = portfolio.construction_diagnostics({"quality": {"portfolio_plan": arguments(), "decisions": decisions}})
            self.assertFalse(result["checks_linked_to_declared_decisions"])

    def test_absent_profile_creates_no_required_work(self):
        result = portfolio.construction_diagnostics({})
        self.assertFalse(result["declared"])
        self.assertFalse(result["creates_validity_blockers"])


if __name__ == "__main__":
    unittest.main()
