"""Capability plans, trace alignment and public rule witnesses are structural controls."""
from __future__ import annotations

import copy
import json
import os
import tempfile
import tomllib
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from pipeline import deliverable, metrics, policy
from pipeline.author import capability, validate
from pipeline.author.build import build
from pipeline.author import scenario
from pipeline.ledger import grounding, levels
from pipeline.tests.test_exported_grader import CSV, sample_spec


def planned_spec():
    return {
        "checks": [{"id": "eligibility", "kind": "objective"},
                   {"id": "allocation", "kind": "objective"}],
        "traps": [{"id": "authorization", "type": "stale_authority", "checks": ["eligibility"]},
                  {"id": "shared_cap", "type": "plausible_decoy", "checks": ["allocation"]}],
        "quality": {
            "decisions": [{"id": "eligible", "checks": ["eligibility"]},
                          {"id": "allocate", "checks": ["allocation"]}],
            "counterexamples": [{"id": "summary", "submission": {"answer.json": {"amount": 200}},
                                 "fails": ["eligibility"]},
                                {"id": "independent", "submission": {"answer.json": {"amount": 150}},
                                 "fails": ["allocation"]}],
            "source_cases": [{"id": "approval", "changes": ["eligibility"],
                              "source_patches": [{"file": "approval.txt", "before": "pending", "after": "approved"}]},
                             {"id": "budget", "changes": ["allocation"],
                              "source_patches": [{"file": "cap.txt", "before": "100", "after": "80"}]}],
            "capability_plan": {"version": 1, "mechanisms": [
                {"id": "authority", "kind": "authority_time", "decisions": ["eligible"],
                 "traps": ["authorization"], "source_cases": ["approval"],
                 "shortcuts": [{"policy": "trust_summary", "counterexample": "summary"}],
                 "tool_resistance": "The operational summary does not establish delegated authorization."},
                {"id": "capacity", "kind": "coupled_decisions", "decisions": ["allocate"],
                 "traps": ["shared_cap"], "source_cases": ["budget"],
                 "shortcuts": [{"policy": "independent_rows", "counterexample": "independent"}],
                 "tool_resistance": "Individually eligible allocations still compete for the same cap."}]}}}


def alignment_witnesses(roles=grounding.ROLES):
    witness = {"citation": "session1::msg0", "quote": "Reconcile the donor ledger",
               "preserved": "Reconciliation of independently evidenced eligibility.", "checks": ["o1"]}
    return {role: copy.deepcopy(witness) for role in roles}


class CapabilityPlans(unittest.TestCase):
    def test_live_control_links_pass_without_claiming_model_difficulty(self):
        self.assertEqual(capability.plan_problems(planned_spec(), required=True), [])

    def test_existing_bundles_are_not_required_to_have_a_new_plan(self):
        self.assertEqual(capability.plan_problems({}), [])
        self.assertTrue(capability.plan_problems({}, required=True))

    def test_dead_shortcut_and_inert_source_change_are_rejected(self):
        spec = planned_spec()
        spec["quality"]["counterexamples"][0]["fails"] = ["allocation"]
        spec["quality"]["source_cases"][0]["changes"] = []
        problems = capability.plan_problems(spec)
        self.assertTrue(any("wrong answer failing" in problem for problem in problems), problems)
        self.assertTrue(any("change evidence" in problem for problem in problems), problems)

    def test_renaming_a_mechanism_does_not_cover_an_unrelated_trap(self):
        spec = planned_spec()
        spec["quality"]["capability_plan"]["mechanisms"][0]["traps"] = ["shared_cap"]
        problems = capability.plan_problems(spec)
        self.assertTrue(any("drives none" in problem for problem in problems), problems)
        self.assertTrue(any("not covered" in problem for problem in problems), problems)

    def test_malformed_model_authored_values_produce_diagnostics(self):
        for field, value in (("kind", []), ("shortcuts", [{"policy": []}]),
                             ("decisions", [{}]), ("source_cases", ["missing"])):
            with self.subTest(field=field):
                spec = planned_spec()
                spec["quality"]["capability_plan"]["mechanisms"][0][field] = value
                self.assertTrue(capability.plan_problems(spec))

    def test_batch_patterns_are_reported_as_declarations_not_observed_failures(self):
        task = {"capability_signature": capability.signature(planned_spec()), "multi_turn": True}
        report = capability.batch_diversity([task, copy.deepcopy(task)])
        self.assertTrue(report["review_required"])
        self.assertEqual(report["delivery_patterns"], {"multi-turn": 2})
        self.assertIn("not measured", report["basis"])

    def test_signature_tolerates_malformed_private_authoring_metadata(self):
        specs = [{"quality": []}, {"quality": {"capability_plan": []}},
                 {"quality": {"capability_plan": {"mechanisms": 3}}, "traps": 3}]
        for field, value in (("kind", []), ("shortcuts", 3),
                             ("shortcuts", [{"policy": []}])):
            spec = planned_spec()
            spec["quality"]["capability_plan"]["mechanisms"][0][field] = value
            specs.append(spec)
        for spec in specs:
            with self.subTest(spec=spec):
                self.assertIsInstance(capability.signature(spec)["mechanisms"], list)


class TraceAlignment(unittest.TestCase):
    def setUp(self):
        self.trace = {"messages": [{"role": "user", "content": "Reconcile the donor ledger against approved grants."},
                                   {"role": "assistant", "content": "Every completion report authorizes payment."}]}
        witness = {"citation": "session1::msg0", "quote": "Reconcile the donor ledger",
                   "preserved": "Reconciliation of independently evidenced eligibility.", "checks": ["eligibility"]}
        self.spec = planned_spec()
        self.spec["quality"]["trace_alignment"] = {role: copy.deepcopy(witness) for role in grounding.ROLES}

    def test_exact_source_goal_and_decision_links_verify(self):
        self.assertEqual(grounding.alignment_problems(self.spec, self.trace, "session1", required=True), [])
        self.assertEqual(set(grounding.verified_alignment(self.spec, self.trace, "session1")), grounding.ROLES)

    def test_placeholder_citation_diagnostic_names_the_actual_source_prefix(self):
        self.spec["quality"]["trace_alignment"]["goal"]["citation"] = "session::msg0"
        problems = grounding.alignment_problems(self.spec, self.trace, "session1", required=True)
        self.assertTrue(any("session1::msgN" in problem for problem in problems), problems)
        self.assertEqual(grounding.verified_alignment(self.spec, self.trace, "session1"), {})

    def test_trace_reader_returns_real_citations_for_each_window(self):
        from pipeline.author.agent_designer import _handlers
        extraction = SimpleNamespace(session_id="source-session", seed_index=0, span=(0, 1), moments=[], pivot=0)
        with tempfile.TemporaryDirectory() as temporary:
            handlers = _handlers(Path(temporary), extraction, self.trace, category="F2")
            rows = handlers["read_trace"](0, 2)["messages"]
            self.assertEqual([row["cite"] for row in rows], ["source-s::msg0", "source-s::msg1"])
            self.assertEqual(handlers["read_trace"](0, 1, char_offset=5)["messages"][0]["cite"], rows[0]["cite"])

    def test_authoring_prompt_requires_actual_user_witnesses_and_coherent_controls(self):
        self.assertNotIn("citation:'session::msgN'", capability.CAPABILITY_PROMPT)
        for requirement in ("actual cite returned by read_trace", "exact USER-message text",
                            "unresolved prerequisite", "authoritative representations",
                            "every affected step", "independent semantic bottlenecks"):
            self.assertIn(requirement, capability.CAPABILITY_PROMPT)

    def test_malformed_authoring_metadata_receives_no_source_credit(self):
        for spec in ({"quality": 3}, {"quality": []},
                     {"quality": self.spec["quality"], "checks": [{"kind": "objective", "id": []}]}):
            with self.subTest(spec=spec):
                self.assertTrue(grounding.alignment_problems(spec, self.trace, "session1", required=True))
                self.assertEqual(grounding.verified_alignment(spec, self.trace, "session1"), {})

    def test_shared_authoring_guidance_allows_grounded_f0(self):
        from pipeline.author.designer import CATEGORY_GUIDANCE

        self.assertIn("Arena allows F0", CATEGORY_GUIDANCE["F0"])
        self.assertIn("concrete source user goal", CATEGORY_GUIDANCE["F0"])
        self.assertNotIn("accepts no F0", CATEGORY_GUIDANCE["F0"])

    def test_wrong_session_assistant_prose_and_invented_quotations_receive_no_credit(self):
        for changes in ({"citation": "other::msg0"}, {"citation": "session1::msg1", "quote": "Every completion"},
                        {"quote": "The user demanded this artificial trap"}, {"checks": ["missing"]}):
            with self.subTest(changes=changes):
                spec = copy.deepcopy(self.spec)
                spec["quality"]["trace_alignment"]["goal"].update(changes)
                self.assertEqual(grounding.verified_alignment(spec, self.trace, "session1"), {})

    def test_missing_source_goal_cannot_be_called_inspired(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            record = levels.assign(root, {"faithfulness_by_bytes": 0.0})
        self.assertEqual(record["level"], "F-1")
        self.assertTrue(levels.problems(record))

    def test_synthetic_world_can_be_f0_or_f2_with_verified_source_alignment(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            alignment = grounding.verified_alignment(self.spec, self.trace, "session1")
            inspired = levels.assign(root, {"faithfulness_by_bytes": 0.0,
                                           "trace_alignment": {role: alignment[role] for role in grounding.INSPIRED_ROLES}})
            scenario = levels.assign(root, {"faithfulness_by_bytes": 0.0, "trace_alignment": alignment})
        self.assertEqual(inspired["level"], "F0")
        self.assertEqual(levels.problems(inspired), [])
        self.assertEqual(scenario["level"], "F2")


class PublicRuleWitnesses(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.fixture = self.root / "environment/files"
        self.fixture.mkdir(parents=True)
        (self.fixture / "tickets.csv").write_text(CSV)
        self.rule = "Only records whose status is open are included in this report."
        (self.fixture / "policy.txt").write_text(self.rule)
        self.spec = sample_spec()
        self.spec["steps"][0]["instruction"] = "Prepare the report under the workspace policy."
        for check in self.spec["checks"][1:]:
            check["rule_sources"] = [{"file": "policy.txt", "quote": self.rule}]

    def test_fixture_rule_does_not_have_to_be_repeated_in_the_assignment(self):
        self.assertEqual(validate._hidden_rules(self.spec, self.root), [])

    def test_hidden_future_rule_and_path_traversal_are_rejected(self):
        for path in ("../private.txt", "/etc/passwd"):
            spec = copy.deepcopy(self.spec)
            spec["checks"][1]["rule_sources"][0]["file"] = path
            self.assertTrue(validate._hidden_rules(spec, self.root))
        self.spec["steps"].append({"name": "02-revision", "instruction": "Revise the report."})
        self.spec["step_files"] = {"02-revision": ["policy.txt"]}
        problems = validate._hidden_rules(self.spec, self.root)
        self.assertTrue(any("unavailable" in problem for problem in problems), problems)

    def test_nonverbatim_rule_and_unstated_filter_value_are_rejected(self):
        self.spec["checks"][1]["rule_sources"][0]["quote"] = "Only open records qualify."
        self.assertTrue(validate._hidden_rules(self.spec, self.root))
        self.spec["checks"][1]["rule_sources"][0]["quote"] = self.rule
        self.spec["checks"][1]["target"]["of"]["where"]["eq"] = "closed"
        self.assertTrue(validate._hidden_rules(self.spec, self.root))

    def test_export_preserves_review_witnesses_but_not_runtime_grader_metadata(self):
        build(self.spec, self.root)
        basis = tomllib.loads((self.root / "tests/basis.toml").read_text())
        self.assertEqual(basis["rule_sources"]["open_count"], [{"file": "policy.txt", "quote": self.rule}])
        exported = json.loads((self.root / "tests/checks.json").read_text())
        self.assertTrue(all("rule_sources" not in check for check in exported["checks"]))


class UpdatedSpecMetrics(unittest.TestCase):
    def test_an_all_pass_campaign_reports_zero_capability_failures(self):
        diagnostic = metrics.capability_difficulty({"pass": 10})
        self.assertEqual(diagnostic["capability_failures"], 0)
        self.assertEqual(diagnostic["capability_adjusted_pass_at_1"], 1)
        self.assertFalse(diagnostic["meets_target"])

    def test_contract_failures_cannot_establish_capability_hardness(self):
        diagnostic = metrics.capability_difficulty({"pass": 4, "capability": 2, "contract": 4})
        self.assertEqual(diagnostic["capability_adjusted_pass_at_1"], 0.8)
        self.assertFalse(diagnostic["meets_target"])
        genuine = metrics.capability_difficulty({"pass": 4, "capability": 6, "void": 3})
        self.assertAlmostEqual(genuine["capability_adjusted_pass_at_1"], 0.4)
        self.assertEqual(genuine["episodes_valid"], 10)
        self.assertTrue(genuine["meets_target"])
        self.assertIsNone(metrics.capability_difficulty({"unattributed": 1})["capability_adjusted_pass_at_1"])

    def test_mix_uses_both_new_thresholds_and_all_tasks_in_the_denominator(self):
        records = ([{"level": "F2"}] * 3 + [{"level": "F1"}] * 7 + [{"level": "F0"}] * 10)
        mix = levels.batch_mix(records)
        self.assertTrue(mix["ok"], mix)
        self.assertEqual(mix["f1_plus_share"], 0.5)
        self.assertEqual(mix["f2_plus_share"], 0.15)
        self.assertFalse(levels.batch_mix(records + [{"level": "F-1"}])["ok"])
        self.assertFalse(levels.batch_mix(records + [{"level": None}])["ok"])

    def test_yields_use_half_threshold_f0_plus_and_f1_plus_not_hard_label(self):
        tasks = [{"session_id": "inspired", "faithfulness_level": "F0", "accepted": True,
                  "hardness": {"primary_pass_at_1": 0.5, "hard": False}},
                 {"session_id": "pattern", "faithfulness_level": "F1", "accepted": True,
                  "hardness": {"primary_pass_at_1": 0.4, "hard": False}},
                 {"session_id": "easy", "faithfulness_level": "F2", "accepted": True,
                  "hardness": {"primary_pass_at_1": 0.6, "hard": False}}]
        report = deliverable.yield_metrics(["inspired", "pattern", "easy", "excluded"], tasks)
        self.assertEqual(report["difficulty_yield"], 0.5)
        self.assertEqual(report["hard_task_yield"], 0.25)
        self.assertEqual(policy.resolve_calibration_models(), ("claude-fable-5-1", "gpt-6-astra"))


class SyntheticStartingContext(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.trace = {"session_id": "session1", "messages": [{"role": "user", "content": [
            {"type": "text", "text": "Reconcile the donor ledger against approved grants."}]}]}
        self.arguments = {"context": "A synthetic charity closes its books under documented donor restrictions.",
                          "reason": "Preserve the source reconciliation goal in a disclosed synthetic world.",
                          "citation": "session1::msg0", "quote": "Reconcile the donor ledger",
                          "trace": self.trace, "session_id": "session1", "category": "F0"}

    def test_no_artifact_is_needed_but_context_keeps_zero_source_credit(self):
        result = scenario.initialize(self.root, **self.arguments)
        self.assertEqual(result["recovered_source_credit"], 0)
        self.assertIn(scenario.CONTEXT, scenario.verify(self.root))
        scenario.write(self.root, path="scenario/ledger.csv", content="id,amount\nG-1,100\n",
                       reason="Create a disclosed ledger for source-grounded reconciliation.",
                       source_evidence=[{"file": scenario.CONTEXT, "quote": self.arguments["context"]}], category="F0")
        self.assertEqual(set(scenario.verify(self.root)),
                         {scenario.CONTEXT, "scenario/ledger.csv"})  # v2: notice in provenance/

    def test_bootstrap_cannot_overwrite_recovered_files_or_use_invented_source_evidence(self):
        fixture = self.root / "environment/files"
        fixture.mkdir(parents=True)
        (fixture / "recovered.txt").write_text("Preserve these recovered bytes.")
        with self.assertRaisesRegex(ValueError, "empty fixture"):
            scenario.initialize(self.root, **self.arguments)
        (fixture / "recovered.txt").unlink()
        self.arguments["quote"] = "The source requires these fictional errors"
        with self.assertRaisesRegex(ValueError, "exact cited"):
            scenario.initialize(self.root, **self.arguments)
        self.assertFalse((self.root / scenario.BOOTSTRAP).exists())

    def test_fresh_source_verification_and_context_hash_detect_tampering(self):
        scenario.initialize(self.root, **self.arguments)
        changed = {"messages": [{"role": "user", "content": "A different task."}]}
        with self.assertRaisesRegex(ValueError, "exact cited"):
            scenario.verify_bootstrap(self.root, changed, "session1")
        (self.root / "environment/files" / scenario.CONTEXT).write_text("Changed synthetic context.")
        with self.assertRaisesRegex(ValueError, "differs"):
            scenario.verify(self.root)

    def test_plan_advice_does_not_block_starting_a_grounded_synthetic_world(self):
        from pipeline.author.agent_designer import _handlers, _tools
        handlers = _handlers(self.root, SimpleNamespace(session_id="session1", seed_index=0),
                             self.trace, category="F0")
        public = {key: self.arguments[key] for key in ("context", "reason", "citation", "quote")}
        handlers["initialize_scenario"](**public)
        self.assertTrue((self.root / "environment/files" / scenario.CONTEXT).exists())
        self.assertIn("initialize_scenario", {tool["name"] for tool in _tools(1)})

    def test_fresh_ledger_assigns_zero_credit_and_reverifies_the_actual_source_request(self):
        from pipeline.artifacts import atomic_json
        from pipeline.ledger.faithfulness import build as build_ledger
        scenario.initialize(self.root, **self.arguments)
        atomic_json(self.root / "dump/sessions/session1/data.json", {"traces": [self.trace]})
        with patch.dict(os.environ, ARENA_DUMP=str(self.root / "dump")):
            ledger = build_ledger(self.root, "session1", 0)
            self.assertEqual(ledger["faithfulness_by_bytes"], 0.0)
            self.assertEqual(ledger["entries"][0]["origin"], "authored")
            changed = {"session_id": "session1", "messages": [{"role": "user", "content": [
                {"type": "text", "text": "A different task."}]}]}
            atomic_json(self.root / "dump/sessions/session1/data.json", {"traces": [changed]})
            with self.assertRaisesRegex(ValueError, "exact cited"):
                build_ledger(self.root, "session1", 0)


if __name__ == "__main__":
    unittest.main()
