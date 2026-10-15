from copy import deepcopy
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from pipeline import harden
from pipeline.author import agent_designer, challenge
from pipeline.tests.test_adversarial_construction import stress_spec
from pipeline.tests.test_harden_traps import bundle_with


class ChallengeConstruction(unittest.TestCase):
    def test_lattice_is_full_match_plus_every_distinct_single_criterion_miss(self):
        criteria = ["entity", "scope", "time", "consent"]
        rows = challenge.near_miss_lattice(criteria)
        self.assertEqual(len(rows), 5)
        self.assertEqual(rows[0]["satisfies"], criteria)
        self.assertEqual(rows[0]["violates"], [])
        self.assertEqual({tuple(row["violates"]) for row in rows[1:]}, {(criterion,) for criterion in criteria})
        for row in rows:
            self.assertEqual(set(row["satisfies"]) | set(row["violates"]), set(criteria))
            self.assertFalse(set(row["satisfies"]) & set(row["violates"]))

    def test_lattice_does_not_mutate_criteria(self):
        criteria = ["scope", "time"]
        rows = challenge.near_miss_lattice(criteria)
        rows[0]["satisfies"].append("unrelated")
        self.assertEqual(criteria, ["scope", "time"])

    def test_interacting_misses_are_explicit_and_classify_every_criterion(self):
        criteria = ["entity", "scope", "time", "consent"]
        requested = [["time", "scope"], ["entity", "consent"]]
        before = deepcopy((criteria, requested))
        rows = challenge.near_miss_lattice(criteria, requested)
        self.assertEqual(len(rows), 7)
        self.assertEqual(rows[-2]["violates"], ["scope", "time"])
        self.assertEqual(rows[-1]["satisfies"], ["scope", "time"])
        self.assertEqual(len({row["id"] for row in rows}), len(rows))
        for row in rows:
            self.assertEqual(set(row["satisfies"]) | set(row["violates"]), set(criteria))
            self.assertFalse(set(row["satisfies"]) & set(row["violates"]))
        self.assertEqual((criteria, requested), before)

    def test_interacting_misses_reject_duplicates_unknown_or_missing_criteria(self):
        for requested in ("scope", [[]], [["scope"]], [["scope", "scope"]], [["scope", "missing"]],
                          [["scope", 2]], [["scope", "time"], ["time", "scope"]]):
            with self.subTest(requested=requested), self.assertRaises(ValueError):
                challenge.near_miss_lattice(["entity", "scope", "time"], requested)

    def test_tool_does_not_automatically_generate_an_exponential_decoy_set(self):
        result = challenge.plan_challenge([f"criterion-{index}" for index in range(24)])
        self.assertEqual(len(result["candidates"]), 25)
        self.assertEqual(len(result["control_outlines"]), 24)
        self.assertFalse(result["predicts_model_failure"])
        self.assertFalse(result["creates_validity_blockers"])
        self.assertFalse(result["adds_or_refunds_attempts"])
        self.assertFalse(result["writes_public_or_reference_files"])

    def test_revision_scope_recomputes_shared_descendants_and_preserves_unrelated_inputs(self):
        graph = {"eligibility": [], "scope": [], "allocation": ["eligibility", "scope"],
            "recommendation": ["allocation"], "unrelated": []}
        before = deepcopy(graph)
        result = challenge.revision_cascade_outline(graph, ["eligibility"])
        self.assertEqual(result["recompute_decisions"], ["allocation", "eligibility", "recommendation"])
        self.assertEqual(result["preserve_decisions"], ["scope", "unrelated"])
        self.assertTrue(result["descendant_answers_may_remain_unchanged"])
        self.assertEqual(graph, before)

    def test_multiple_revision_roots_do_not_duplicate_shared_descendants(self):
        graph = {"one": [], "two": [], "shared": ["one", "two"]}
        result = challenge.revision_cascade_outline(graph, ["one", "two"])
        self.assertEqual(result["recompute_decisions"], ["one", "shared", "two"])
        self.assertEqual(result["preserve_decisions"], [])

    def test_no_revision_preserves_all_declared_decisions(self):
        result = challenge.revision_cascade_outline({"one": [], "two": ["one"]}, [])
        self.assertEqual(result["recompute_decisions"], [])
        self.assertEqual(result["preserve_decisions"], ["one", "two"])

    def test_deep_valid_graphs_do_not_require_python_recursion(self):
        graph = {f"decision-{index}": [f"decision-{index - 1}"] if index else [] for index in range(1500)}
        result = challenge.revision_cascade_outline(graph, ["decision-0"])
        self.assertEqual(result["declared_causal_depth"], 1499)
        self.assertEqual(len(result["recompute_decisions"]), 1500)

    def test_invalid_graph_or_unknown_revision_root_cannot_invent_a_cascade(self):
        for graph, roots in (({"one": ["two"], "two": ["one"]}, ["one"]),
                             ({"one": ["missing"]}, ["one"]), ({"one": []}, ["missing"]),
                             ({"one": []}, ["one", "one"]), ({"one": []}, None),
                             ({"one": [], "two": ["one", "one"]}, ["one"]), ({"": []}, [])):
            with self.subTest(graph=graph, roots=roots), self.assertRaises(ValueError):
                challenge.revision_cascade_outline(graph, roots)
        with self.assertRaisesRegex(ValueError, "dependency graph"):
            challenge.plan_challenge(["scope", "time"], changed_decisions=["unknown"])

    def test_author_tool_is_registered_and_plans_without_writing_a_fixture_or_draft(self):
        tools = {tool["name"]: tool for tool in agent_designer._tools(0)}
        self.assertIn("plan_challenge", tools)
        self.assertEqual(tools["plan_challenge"]["input_schema"]["required"], ["criteria"])
        with tempfile.TemporaryDirectory() as temporary:
            bundle = Path(temporary)
            handlers = agent_designer._handlers(bundle, SimpleNamespace(moments=[]), {"messages": []})
            before = {path.relative_to(bundle).as_posix(): path.read_bytes() for path in bundle.rglob("*") if path.is_file()}
            result = handlers["plan_challenge"](criteria=["scope", "time"], joint_misses=[["scope", "time"]],
                decision_dependencies={"eligibility": [], "allocation": ["eligibility"]}, changed_decisions=["eligibility"])
            after = {path.relative_to(bundle).as_posix(): path.read_bytes() for path in bundle.rglob("*") if path.is_file()}
        self.assertEqual(before, after)
        self.assertTrue(result["private_authoring_only"])
        self.assertTrue(all(control["promotion_requires_independently_rederived_answer"] for control in result["control_outlines"]))
        self.assertEqual(result["revision_cascade"]["recompute_decisions"], ["allocation", "eligibility"])

    def test_diagnostics_report_interactions_without_treating_them_as_measured_hardness(self):
        spec = stress_spec()
        collision = spec["quality"]["capability_plan"]["collisions"][0]
        collision["candidates"] = challenge.near_miss_lattice(["entity", "scope", "time"], [["scope", "time"]])
        result = challenge.construction_diagnostics(spec)
        self.assertEqual(result["collisions"][0]["interacting_near_misses_declared"], [["scope", "time"]])
        self.assertFalse(result["predicts_model_failure"])

    def test_stretch_capacity_obeys_existing_band_policy(self):
        spec = stress_spec()
        for check in spec["checks"][:2]:
            check["band"] = "stretch"
        before = deepcopy(spec)
        result = challenge.stretch_check_outlines(spec, {"floor": [{"id": "eligibility"}, {"id": "measure"}]})
        self.assertEqual(result["declared_count"], 2)
        from pipeline.policy import BAND_LIMITS     # v2: widened, read from policy
        self.assertEqual(result["additional_slots"], BAND_LIMITS["stretch"][1] - 2)
        self.assertEqual(result["fully_passing_stretch_checks"], ["eligibility"])
        self.assertEqual(spec, before)
        self.assertFalse(result["predicts_model_failure"])
        self.assertFalse(result["creates_validity_blockers"])

    def test_full_stretch_band_recommends_strengthening_not_unbounded_checks(self):
        spec = stress_spec()
        from pipeline.policy import BAND_LIMITS     # v2: widened, read from policy
        template = next(c for c in spec["checks"] if c.get("kind") == "objective")
        while sum(c.get("kind") == "objective" for c in spec["checks"]) < BAND_LIMITS["stretch"][1]:
            spec["checks"].append({**deepcopy(template), "id": f"extra_{len(spec['checks'])}"})
        for check in spec["checks"]:
            check["band"] = "stretch"
        result = challenge.stretch_check_outlines(spec)
        self.assertEqual(result["additional_slots"], 0)
        self.assertIn("Strengthen existing eligible checks", result["when_full"])
        self.assertTrue(result["one_causal_mistake_is_not_multiple_independent_failures"])

    def test_stretch_recipes_only_extend_declared_professional_mechanisms(self):
        spec = stress_spec()
        result = challenge.stretch_check_outlines(spec)
        self.assertEqual(len(result["recipes"]), 4)
        for recipe in result["recipes"]:
            self.assertEqual(len(recipe["decisions"]), 1)
            self.assertEqual(recipe["existing_checks"], recipe["decisions"])
            self.assertEqual(recipe["declared_source_cases"], recipe["decisions"])
            self.assertEqual(len(recipe["required_controls"]), 4)
        self.assertIn("global_consistency", {recipe["recipe"] for recipe in result["recipes"]})

    def test_unsupported_or_malformed_mechanisms_do_not_invent_stretch_demands(self):
        spec = stress_spec()
        spec["quality"]["capability_plan"]["mechanisms"] = [
            {"kind": "unknown", "decisions": ["eligibility"]},
            {"kind": {"wrong": True}, "decisions": ["eligibility"]},
            {"kind": "authority_time", "decisions": ["missing"]}, None]
        self.assertEqual(challenge.stretch_check_outlines(spec)["recipes"], [])

    def test_minimal_repair_and_optimality_are_not_hidden_requirements(self):
        spec = stress_spec()
        spec["quality"]["capability_plan"]["mechanisms"][0]["kind"] = "artifact_repair"
        recipe = challenge.stretch_check_outlines(spec)["recipes"][0]
        self.assertIn("only when the public professional goal calls for it", recipe["demand"])
        self.assertTrue(challenge.stretch_check_outlines(spec)["requires_public_requirement_and_executed_controls"])

    def test_staged_author_tool_and_hardening_diagnostics_share_stretch_profile(self):
        spec = stress_spec()
        with tempfile.TemporaryDirectory() as temporary:
            bundle = Path(temporary)
            handlers = agent_designer._handlers(bundle, SimpleNamespace(moments=[]), {"messages": []})
            handlers["stage_spec"](["checks"], spec["checks"])
            handlers["stage_spec"](["quality"], spec["quality"])
            result = handlers["plan_challenge"](criteria=["scope", "time"])
        self.assertEqual(result["stretch_checks"], challenge.construction_diagnostics(spec)["stretch_checks"])

    def test_lattice_refuses_ambiguous_or_malformed_criteria(self):
        for criteria in (None, [], ["scope"], ["scope", "scope"], ["scope", ""], ["scope", 2]):
            with self.subTest(criteria=criteria), self.assertRaises(ValueError):
                challenge.near_miss_lattice(criteria)

    def test_missing_discriminator_is_advisory_not_a_validity_gate(self):
        result = challenge.construction_diagnostics(stress_spec())
        collision = result["collisions"][0]
        self.assertEqual(collision["criteria_without_a_one_criterion_near_miss"], ["entity"])
        self.assertEqual(collision["one_criterion_near_misses"], ["scope", "time"])
        self.assertFalse(result["creates_validity_blockers"])
        self.assertFalse(result["predicts_model_failure"])
        self.assertFalse(result["adds_or_refunds_attempts"])

    def test_every_discriminator_can_be_exercised_without_a_trap_count_quota(self):
        spec = stress_spec()
        collision = spec["quality"]["capability_plan"]["collisions"][0]
        collision["candidates"] = challenge.near_miss_lattice([entry["id"] for entry in collision["predicates"]])
        result = challenge.construction_diagnostics(spec)
        self.assertEqual(result["collisions"][0]["criteria_without_a_one_criterion_near_miss"], [])

    def test_blank_declarations_do_not_turn_advisories_into_a_new_validity_blocker(self):
        spec = stress_spec()
        collision = spec["quality"]["capability_plan"]["collisions"][0]
        collision["predicates"].append({"id": ""})
        self.assertFalse(challenge.construction_diagnostics(spec)["creates_validity_blockers"])

    def test_partial_or_contradictory_classification_is_not_a_full_match(self):
        spec = stress_spec()
        collision = spec["quality"]["capability_plan"]["collisions"][0]
        collision["candidates"] = [{"satisfies": ["entity", "scope", "time"], "violates": ["time"]}]
        result = challenge.construction_diagnostics(spec)["collisions"][0]
        self.assertEqual(result["full_matches_declared"], 0)
        self.assertEqual(result["unresolved_candidates"], 1)

    def test_dependency_depth_counts_edges_not_output_fields(self):
        spec = stress_spec()
        profile = challenge.construction_diagnostics(spec)
        self.assertEqual(profile["declared_causal_depth"], 1)
        spec["quality"]["capability_plan"]["decision_dependencies"]["allocation"] = ["scope"]
        spec["quality"]["capability_plan"]["decision_dependencies"]["scope"] = ["eligibility"]
        self.assertEqual(challenge.construction_diagnostics(spec)["declared_causal_depth"], 2)

    def test_cyclic_or_unknown_dependencies_do_not_crash_advisory_diagnostics(self):
        for graph in ({"one": ["two"], "two": ["one"]}, {"one": ["missing"]}, {"one": [2]}):
            spec = {"quality": {"capability_plan": {"decision_dependencies": graph}}}
            self.assertIsNone(challenge.construction_diagnostics(spec)["declared_causal_depth"])

    def test_honest_successful_baseline_is_retained_not_rejected(self):
        spec = stress_spec()
        spec["quality"]["capability_plan"]["tool_baselines"] = [
            {"id": "honest", "kind": "computation", "submission": {"answer.json": {}}, "fails": []}]
        before = deepcopy(spec)
        result = challenge.construction_diagnostics(spec)
        self.assertEqual(result["successful_declared_tool_baselines"], ["honest"])
        self.assertFalse(result["creates_validity_blockers"])
        self.assertEqual(spec, before)

    def test_only_valid_aggregate_model_saturation_is_reported(self):
        measured = {"by_model": {
            "fully-passing": {"pass_at_1": 1, "episodes_valid": 5,
                "capability_difficulty": {"capability_adjusted_pass_at_1": 1}},
            "unmeasured": {"pass_at_1": 1, "episodes_valid": 0,
                "capability_difficulty": {"capability_adjusted_pass_at_1": 1}}},
            "reports": {"trajectory": "secret solver answer"}}
        result = challenge.redesign_brief(stress_spec(), measured)
        self.assertIn("screens are saturated on ['fully-passing']", result)
        self.assertNotIn("secret solver answer", result)
        self.assertNotIn("trajectory", json.dumps(challenge.construction_diagnostics(stress_spec(), measured)))

    def test_diagnostics_tolerate_incomplete_drafts_without_claiming_validity(self):
        for spec in ({}, {"quality": []}, {"quality": {"capability_plan": []}}):
            result = challenge.construction_diagnostics(spec, {"by_model": []})
            self.assertFalse(result["predicts_model_failure"])
            self.assertFalse(result["creates_validity_blockers"])

    def test_research_brief_reaches_first_design_without_removing_repair_priority(self):
        self.assertIn("GLOBAL FEASIBILITY", agent_designer.SYSTEM)
        self.assertIn("PRIVATE PLANNING TOOL: plan_challenge", agent_designer.SYSTEM)
        self.assertIn("SUBSTANTIVE STRETCH CHECKS", agent_designer.SYSTEM)
        self.assertIn("REPAIR-ONLY brief takes precedence", agent_designer.SYSTEM)
        self.assertNotIn("Grade exactly -- no tolerance", agent_designer.SYSTEM)

    def test_research_diagnostics_reach_hardening_without_changing_attempt_budget(self):
        spec = {"source": {"session_id": "s", "seed_index": 0}, "checks": []}
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            ledger = bundle_with(root, 10, 1)
            with patch("pipeline.repair.design_inputs", return_value=(spec, ledger, {})), \
                    patch("pipeline.author.extract.extract", return_value=object()), \
                    patch("pipeline.harden._breadth_summary", return_value="aggregate rates"), \
                    patch("pipeline.harden.hardenable", return_value={"by_model": {}}), \
                    patch("pipeline.author.agent_designer.design", return_value=dict(spec)) as designer:
                harden.propose(root, [])
        brief = designer.call_args.kwargs["feedback"][0]
        self.assertIn("PRIVATE CONSTRUCTION DIAGNOSTICS", brief)
        self.assertIn("PRIVATE PLANNING TOOL: plan_challenge", brief)
        self.assertIn("SUBSTANTIVE STRETCH CHECKS", brief)
        # V4 (2026-10-13, Arena 261013): one premise per family per task replaces
        # "no per-family count quota"; the conjunctive block and the measured
        # training-signal section reach every hardening brief.
        self.assertIn("One premise per family per task", brief)
        self.assertNotIn("no per-family count quota", brief)
        self.assertIn("V4 CONJUNCTIVE HARDENING", brief)
        self.assertIn("TRAINING SIGNAL OF THE VERSION YOU ARE REVISING", brief)
        self.assertNotIn("at most two from one family", brief)
        self.assertNotIn("Grade exactly, no tolerance", brief)
        self.assertEqual(harden.policy.MAX_HARDENING_ATTEMPTS, 3)


if __name__ == "__main__":
    unittest.main()
