"""Stress records prove discrimination and causal scope, never model weakness."""
import copy
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from pipeline.author import adversarial, capability
from pipeline.author.agent_designer import _handlers, _construction_version
from pipeline.artifacts import atomic_json
from pipeline.corpus import source_briefs
from pipeline.source_controls import run as source_controls
from pipeline.tests.test_production import synthetic_bundle


RULE = "Use matching entity, authorized scope and effective reporting time together."
CANDIDATES = ["Record One matches entity, scope and effective reporting time.",
              "Record Two matches entity and reporting time but not the authorized scope.",
              "Record Three matches entity and scope but is not effective at reporting time."]


def stress_spec():
    identifiers = ["eligibility", "scope", "measure", "allocation"]
    checks = [{"id": identifier, "kind": "objective", "band": "core", "step": "01-audit"}
              for identifier in identifiers]
    cases = [{"id": identifier, "changes": [identifier, "allocation"] if identifier == "eligibility" else [identifier],
              "source_patches": [{"file": "records.txt", "before": "pending", "after": "approved"}],
              "patches": [{"file": "answer.json", "path": identifier, "value": "corrected"}]}
             for identifier in identifiers]
    examples = [{"id": identifier, "fails": case["changes"],
                 "patches": [{"file": "answer.json", "path": identifier, "value": "plausible wrong reading"}]}
                for identifier, case in zip(identifiers, cases)]
    decisions = [{"id": identifier, "checks": [identifier], "question": "Resolve the professional " + identifier}
                 for identifier in identifiers]
    witness = [{"file": "rules.txt", "quote": RULE}]
    collision = {"id": "scope-and-time", "trap": "eligibility-trap", "decision": "eligibility",
                 "predicates": [{"id": identifier, "rule_sources": witness} for identifier in ("entity", "scope", "time")],
                 "candidates": [{"id": "full", "evidence": [{"file": "records.txt", "quote": CANDIDATES[0]}],
                                  "satisfies": ["entity", "scope", "time"], "violates": []},
                                 {"id": "scope-miss", "evidence": [{"file": "records.txt", "quote": CANDIDATES[1]}],
                                  "satisfies": ["entity", "time"], "violates": ["scope"]},
                                 {"id": "time-miss", "evidence": [{"file": "records.txt", "quote": CANDIDATES[2]}],
                                  "satisfies": ["entity", "scope"], "violates": ["time"]}],
                 "counterexample": "eligibility", "source_case": "eligibility", "invariant_case": "decoy-strength"}
    plan = {"version": 2,
            "mechanisms": [{"id": identifier, "kind": "authority_time" if identifier != "allocation" else "coupled_decisions",
                            "decisions": [identifier], "traps": [identifier + "-trap"], "source_cases": [identifier],
                            "shortcuts": [{"policy": "trust_summary", "counterexample": identifier}],
                            "tool_resistance": "The authority and applicability still need substantive professional interpretation."}
                           for identifier in identifiers],
            "decision_dependencies": {"eligibility": [], "scope": [], "measure": [], "allocation": ["eligibility"]},
            "bottlenecks": [{"decision": identifier, "source_case": identifier,
                             "reason": "This intervention isolates a distinct professional interpretation and its causal descendants."}
                            for identifier in identifiers],
            "collisions": [collision],
            "couplings": [{"id": "authorization-to-allocation", "decisions": ["eligibility", "allocation"],
                           "source_case": "eligibility", "counterexample": "eligibility", "rule_sources": witness}],
            "tool_baselines": [{"id": "retrieval", "kind": "retrieval", "counterexample": "eligibility",
                                "method": "Inspect all files but adopt the professional applicability asserted by the draft summary."},
                               {"id": "computation", "kind": "computation", "counterexample": "allocation",
                                "method": "Calculate all quantities exactly but apply independent allocation before scoped authorization."}]}
    return {"checks": checks, "traps": [{"id": identifier + "-trap", "checks": [identifier]} for identifier in identifiers],
            "steps": [{"name": "01-audit", "instruction": "Audit the complete public records and preserve unrelated decisions."}],
            "quality": {"semantic_checks": identifiers, "decisions": decisions, "counterexamples": examples,
                        "source_cases": cases, "source_invariants": [{"id": "decoy-strength"}], "capability_plan": plan}}


class AdversarialDesign(unittest.TestCase):
    def test_complete_stress_design_links_live_controls_without_claiming_hardness(self):
        self.assertEqual(capability.plan_problems(stress_spec()), [])

    def test_legacy_designs_remain_valid_but_do_not_satisfy_fresh_staging(self):
        from pipeline.tests.test_capability_construction import planned_spec
        capability.require_staged_plan(planned_spec())
        with self.assertRaisesRegex(ValueError, "version:2"):
            capability.require_staged_plan(planned_spec(), minimum_version=2)

    def test_fresh_handlers_report_a_legacy_outline_without_vetoing_scenario_tools(self):
        from pipeline.tests.test_capability_construction import planned_spec
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            handlers = _handlers(root, SimpleNamespace(moments=[], session_id="s-legacy", seed_index=0), {"messages": []}, category="F2", capability_version=2)
            handlers["stage_spec"](["quality"], planned_spec()["quality"])
            with patch("pipeline.author.scenario.write", return_value={"created": True}) as write:
                self.assertEqual(handlers["write_scenario"](), {"created": True})
                write.assert_called_once()
            self.assertFalse(handlers["check_spec"](planned_spec())["clean"])
            self.assertEqual(list((root / "environment/files").rglob("*")), [])

    def test_stalled_continuation_and_repairs_cannot_downgrade_new_construction(self):
        from pipeline.tests.test_capability_construction import planned_spec
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            extraction = SimpleNamespace(session_id="source-one", seed_index=4)
            # v2 (user, 2026-10-02): the construction plan is optional guidance,
            # so a NEW session is no longer forced onto version 2 ...
            self.assertEqual(_construction_version(root, extraction), 1)
            self.assertFalse((root / "verification/construction-protocol.json").exists())
            # ... but a design already bound to version 2 is never downgraded.
            (root / "verification").mkdir(parents=True, exist_ok=True)
            (root / "verification/construction-protocol.json").write_text(json.dumps(
                {"schema": "arena-pipeline/construction-protocol/1",
                 "source": {"session_id": "source-one", "seed_index": 4}, "minimum_version": 2}))
            self.assertEqual(_construction_version(root, extraction), 2)
            self.assertEqual(_construction_version(root, extraction, planned_spec()), 2)
            self.assertEqual(_construction_version(root, extraction, planned_spec(), {"config": {}}), 2)
            with self.assertRaisesRegex(ValueError, "different source"):
                _construction_version(root, SimpleNamespace(session_id="source-two", seed_index=4), planned_spec())

    def test_legacy_validity_repair_does_not_require_migration(self):
        from pipeline.tests.test_capability_construction import planned_spec
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            self.assertEqual(_construction_version(root, SimpleNamespace(session_id="source-one", seed_index=4), planned_spec()), 1)
            self.assertFalse((root / "verification/construction-protocol.json").exists())

    def test_no_volume_only_or_single_criterion_collision(self):
        spec = stress_spec()
        collision = spec["quality"]["capability_plan"]["collisions"][0]
        collision["candidates"][2]["violates"] = ["scope"]
        collision["candidates"][2]["satisfies"] = ["entity", "time"]
        self.assertTrue(any("different criteria" in error for error in adversarial.problems(spec)))
        collision["candidates"][2] = copy.deepcopy(collision["candidates"][1])
        collision["candidates"][2]["id"] = "same-evidence"
        self.assertTrue(any("same entire evidence" in error for error in adversarial.problems(spec)))

    def test_all_criteria_must_be_classified_without_overlapping_polarity(self):
        spec = stress_spec()
        candidate = spec["quality"]["capability_plan"]["collisions"][0]["candidates"][1]
        candidate["violates"] = ["scope", "entity"]
        self.assertTrue(any("exactly once" in error for error in adversarial.problems(spec)))

    def test_dependent_fields_cannot_reuse_one_intervention_as_four_bottlenecks(self):
        spec = stress_spec()
        for entry in spec["quality"]["capability_plan"]["bottlenecks"]:
            entry["source_case"] = "eligibility"
        self.assertTrue(any("distinct decision and intervention" in error for error in adversarial.problems(spec)))

    def test_intervention_cannot_modify_upstream_or_unrelated_judgments(self):
        spec = stress_spec()
        spec["quality"]["source_cases"][1]["changes"].append("measure")
        self.assertTrue(any("unrelated or upstream" in error for error in adversarial.problems(spec)))

    def test_causal_cycle_is_not_accepted(self):
        spec = stress_spec()
        spec["quality"]["capability_plan"]["decision_dependencies"]["eligibility"] = ["allocation"]
        self.assertTrue(any("acyclic" in error for error in adversarial.problems(spec)))

    def test_coupling_needs_a_joint_causal_control_and_sustained_wrong_reading(self):
        spec = stress_spec()
        spec["quality"]["capability_plan"]["couplings"][0].update(source_case="scope", counterexample="scope")
        errors = adversarial.problems(spec)
        self.assertTrue(any("change every named decision" in error for error in errors))
        self.assertTrue(any("failing every named decision" in error for error in errors))

    def test_decoy_must_have_an_executable_whole_answer_invariant(self):
        spec = stress_spec()
        spec["quality"]["capability_plan"]["collisions"][0]["invariant_case"] = "missing"
        self.assertTrue(any("without changing any answer" in error for error in adversarial.problems(spec)))

    def test_both_tool_aware_baselines_are_required(self):
        spec = stress_spec()
        spec["quality"]["capability_plan"]["tool_baselines"] = spec["quality"]["capability_plan"]["tool_baselines"][:1]
        self.assertTrue(any("both competent" in error for error in adversarial.problems(spec)))

    def test_private_nonverbatim_and_future_evidence_cannot_discriminate_candidates(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            fixture = root / "environment/files"
            fixture.mkdir(parents=True)
            (fixture / "rules.txt").write_text(RULE)
            (fixture / "records.txt").write_text("\n".join(CANDIDATES))
            spec = stress_spec()
            self.assertEqual(adversarial.problems(spec, root), [])
            predicate = spec["quality"]["capability_plan"]["collisions"][0]["predicates"][0]
            predicate["rule_sources"][0]["quote"] = "An invented rule that is not actually stated anywhere."
            self.assertTrue(any("not verbatim" in error for error in adversarial.problems(spec, root)))
            predicate["rule_sources"][0].update(file="../private.txt", quote=RULE)
            self.assertTrue(any("not readable" in error for error in adversarial.problems(spec, root)))
            predicate["rule_sources"][0].update(file="rules.txt", quote=RULE)
            spec["steps"].append({"name": "02-revision", "instruction": "Revise after the new rules become available."})
            spec["step_files"] = {"02-revision": ["rules.txt"]}
            self.assertTrue(any("unavailable" in error for error in adversarial.problems(spec, root)))

    def test_malformed_stress_metadata_yields_diagnostics_not_exceptions(self):
        for field in ("decision_dependencies", "bottlenecks", "collisions", "couplings", "tool_baselines"):
            for value in (None, True, "wrong", {}, [None], [{}]):
                with self.subTest(field=field, value=value):
                    spec = stress_spec()
                    spec["quality"]["capability_plan"][field] = value
                    self.assertTrue(capability.plan_problems(spec))
        spec = stress_spec()
        spec["quality"]["capability_plan"]["bottlenecks"][0]["source_case"] = []
        self.assertTrue(adversarial.problems(spec))


class ExactInterventionScope(unittest.TestCase):
    def test_unreported_downstream_change_cannot_masquerade_as_independence(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            bundle = synthetic_bundle(root)
            spec = json.loads((bundle / "authoring/spec.json").read_text())
            spec["quality"] = {"semantic_checks": ["open_ids", "open_count", "total_effort"],
                               "capability_plan": {"version": 2}, "source_cases": [{
                "id": "status-change", "reason": "Opening a ticket changes membership and every related total.",
                "changes": ["open_ids", "total_effort"],
                "source_patches": [{"file": "tickets.csv", "before": "R-22,closed,8", "after": "R-22,open,8"}],
                "submission": {"summary.json": {"open_ids": ["R-21", "R-22", "R-23"], "open_count": 3, "total_effort": 16}}}]}
            result = source_controls(bundle, spec, spec["solution"], {check["id"]: check for check in spec["checks"]}, root / "controls")
            self.assertTrue(any("not its declared exact scope" in error for error in result["errors"]), result)
            self.assertEqual(result["results"]["status-change"]["observed_semantic_changes"], ["open_count", "open_ids", "total_effort"])
            spec["quality"]["source_cases"][0]["changes"].append("open_count")
            corrected = source_controls(bundle, spec, spec["solution"], {check["id"]: check for check in spec["checks"]}, root / "complete-controls")
            self.assertEqual(corrected["errors"], [], corrected)


class SourceFamilyPreflight(unittest.TestCase):
    def test_same_session_questions_are_visible_before_generation_without_gold(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            peer = synthetic_bundle(root / "envs-test")
            spec = json.loads((peer / "authoring/spec.json").read_text())
            spec["quality"] = {"decisions": [{"question": "Which scoped authorizations govern recognition?"}]}
            spec["novelty"] = "A professional authorization decision."
            atomic_json(peer / "authoring/spec.json", spec)
            result = source_briefs(spec["source"]["session_id"], root / "new-task", workspace=root)
            self.assertEqual(result["same_session_designs"], 1)
            self.assertEqual(result["peers"][0]["questions"], ["Which scoped authorizations govern recognition?"])
            self.assertNotIn("solution", json.dumps(result))
            self.assertNotIn("target", json.dumps(result))
            self.assertEqual(source_briefs("other-session", root / "new-task", workspace=root)["peers"], [])
            self.assertEqual(source_briefs(spec["source"]["session_id"], peer, workspace=root)["peers"], [])


if __name__ == "__main__":
    unittest.main()
