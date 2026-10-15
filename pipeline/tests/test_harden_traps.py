"""Hardening may add traps -- the operator's and the designer's -- but never
at the cost of the task's faithfulness level or its trace-derived share."""
import json
import tempfile
import unittest
from pathlib import Path
from pipeline.tests.test_capability_construction import alignment_witnesses
from unittest.mock import patch

from pipeline.harden import (HARDENING_BRIEF, budget_problems, faithfulness_budget,
                             propose, requested_traps)


def trap(i, provenance):
    row = {"id": f"t{i}", "type": "plausible_decoy", "provenance": provenance,
           "surface": "s", "beatable_by": "b", "probe": "plausible_wrong", "checks": ["c1"]}
    if provenance == "trace_derived":
        row.update(derived_from=f"sess1234::msg{i}", quote="the user's words")
    else:
        row.update(grounded_in="doc.md", grounding="a practitioner meets this")
    return row


def bundle_with(root, derived, authored, fidelity=1.0, size=90_000, category="A"):
    traps = [trap(i, "trace_derived") for i in range(derived)] + \
            [trap(100 + i, "authored") for i in range(authored)]
    (root / "authoring").mkdir(parents=True)
    (root / "authoring/traps.json").write_text(json.dumps({"traps": traps}))
    (root / "authoring/spec.json").write_text(json.dumps(
        {"traps": traps, "source": {"session_id": "sess1234", "moments": [1] * derived}}))
    return {"faithfulness_by_bytes": fidelity, "bytes": {"lifted": size}, "category": category,
            "trace_alignment": alignment_witnesses()}


class FaithfulnessBudget(unittest.TestCase):
    def budget(self, *args, **kw):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            return faithfulness_budget(root, bundle_with(root, *args, **kw))

    def test_f3_room_is_what_keeps_the_trace_derived_share_at_70_percent(self):
        b = self.budget(10, 1)                 # 10/11 today; 10/14 = 71% still F3
        self.assertEqual((b["level"], b["authored_traps_left"]), ("F3", 3))

    def test_f3_bytes_keep_fidelity_at_its_floor(self):
        b = self.budget(10, 1, size=90_000)    # 90,000 / (90,000 + 10,000) = 0.90
        self.assertEqual(b["authored_bytes_left"], 10_000)

    def test_f2_traps_are_not_limited_by_a_recovered_share_quota(self):
        b = self.budget(3, 7)
        self.assertEqual((b["level"], b["authored_traps_left"]), ("F2", None))

    def test_category_floor_caps_f2_bytes(self):
        loose = self.budget(3, 7, category="D")   # D floor 0.60
        tight = self.budget(3, 7, category="A")   # A floor 0.90
        self.assertLess(tight["authored_bytes_left"], loose["authored_bytes_left"])


class BudgetIsEnforced(unittest.TestCase):
    budget = {"level": "F3", "authored_traps_left": 1, "authored_bytes_left": 500}
    before = [trap(0, "trace_derived"), trap(1, "trace_derived")]

    def test_within_budget_passes(self):
        self.assertEqual(budget_problems(self.budget, self.before,
                                         self.before + [trap(100, "authored")], 400), [])

    def test_too_many_authored_traps_are_refused(self):
        after = self.before + [trap(100, "authored"), trap(101, "authored")]
        self.assertTrue(any("room for 1" in p for p in budget_problems(self.budget, self.before, after, 0)))

    def test_a_real_correction_cannot_be_dropped_or_relabelled(self):
        relabelled = [trap(0, "trace_derived"), {**trap(1, "authored"), "id": "t1"}]
        self.assertTrue(any("t1" in p for p in budget_problems(self.budget, self.before, relabelled, 0)))

    def test_too_many_bytes_are_refused(self):
        self.assertTrue(budget_problems(self.budget, self.before, self.before, 501))


class OperatorTraps(unittest.TestCase):
    def test_ideas_come_from_flags_and_a_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "traps.json"
            path.write_text(json.dumps(["a superseded quote", {"idea": "a decoy vendor", "grounding": "invoice.csv"}]))
            self.assertEqual(requested_traps([" a retracted figure "], str(path)),
                             ["a retracted figure", "a superseded quote",
                              "a decoy vendor (grounding: invoice.csv)"])
            path.write_text(json.dumps([{"no": "idea"}]))
            with self.assertRaises(ValueError):
                requested_traps([], str(path))

    def test_the_brief_carries_the_ideas_the_budget_and_the_legitimacy_rules(self):
        spec = {"source": {"session_id": "s", "seed_index": 0}, "checks": []}
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            ledger = bundle_with(root, 10, 1)
            with patch("pipeline.repair.design_inputs", return_value=(spec, ledger, {})), \
                 patch("pipeline.author.extract.extract", return_value=object()), \
                 patch("pipeline.harden._breadth_summary", return_value="  -"), \
                 patch("pipeline.author.agent_designer.design", return_value=dict(spec)) as design:
                propose(root, [], requested=["a decoy that is correct under the superseded rule"])
        brief = design.call_args.kwargs["feedback"][0]
        self.assertIn("a decoy that is correct under the superseded rule", brief)
        self.assertIn("authored traps you may add: 3", brief)
        self.assertEqual(design.call_args.kwargs["initial_spec"]["quality"]["capability_plan"]["version"], 2)
        self.assertNotIn("quality", spec)
        for rule in ("grounded", "resolvable", "beatable", "No hidden rules", "as deceptive as the EVIDENCE",
                     "requirements themselves stay perfectly clear"):
            self.assertIn(rule, brief)

    def test_legacy_validity_repair_does_not_force_a_hardness_redesign(self):
        spec = {"source": {"session_id": "s", "seed_index": 0}, "checks": [],
                "quality": {"capability_plan": {"version": 1, "mechanisms": []}}}
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            ledger = bundle_with(root, 10, 1)
            with patch("pipeline.repair.design_inputs", return_value=(spec, ledger, {})), \
                 patch("pipeline.author.extract.extract", return_value=object()), \
                 patch("pipeline.author.agent_designer.design", return_value=dict(spec)) as design:
                propose(root, [], kind="repair", findings=["Correct only the published unit definition."])
        self.assertEqual(design.call_args.kwargs["initial_spec"]["quality"]["capability_plan"]["version"], 1)

    def test_without_requests_the_brief_has_no_empty_section(self):
        self.assertNotIn("{requested}", HARDENING_BRIEF.format(
            targets="", breadth="", requested="", budget=""))


class CliForwardsTrapOptions(unittest.TestCase):
    def test_every_harden_option_reaches_the_module(self):
        from pipeline import cli
        with patch.object(cli, "_run", return_value=0) as run, patch.object(cli, "load_keys"):
            import argparse
            args = argparse.Namespace(candidates=False, root=None, bundle="b", apply=True,
                                      compare=None, trap=["x", "y"], traps="t.json", no_screen=True)
            cli.cmd_harden(args)
        forwarded = run.call_args.args[1:]
        self.assertEqual(forwarded.count("--trap"), 2)
        self.assertIn("x", forwarded)
        self.assertIn("--traps", forwarded)
        self.assertIn("--no-screen", forwarded)


class TwoStepDeliverables(unittest.TestCase):
    """Step 2's file is named in step 2, never leaked into step 1."""

    def problems(self, first, second):
        from pipeline.author.validate import validate
        spec = {"instruction": first, "deliverable_file": "a.json",
                "second_step": {"instruction": second, "deliverable_file": "b.json"},
                "checks": [{"id": "c1", "kind": "objective", "assertion": "equals", "basis": "x",
                            "actual": {"op": "field", "file": "a.json", "path": "x"}},
                           {"id": "c2", "kind": "objective", "assertion": "equals", "basis": "x",
                            "actual": {"op": "field", "file": "b.json", "path": "y"}}]}
        with tempfile.TemporaryDirectory() as tmp:
            return [p for p in validate(spec, Path(tmp)) if "never names the deliverable" in p]

    def test_each_step_names_its_own_file(self):
        self.assertEqual(self.problems("Write a.json.", "Now write b.json."), [])

    def test_a_file_named_nowhere_is_still_refused(self):
        self.assertTrue(self.problems("Write a.json.", "Now write the revision."))


class NewTrapsDecideAGradedCheck(unittest.TestCase):
    # V4 (2026-10-13, Arena 261013): a premise sits on its OWN check(s); one is
    # enough. Routing several checks through one premise linked their failures,
    # so the old two-objective routing rule is retired (MIN_CHECKS_PER_NEW_TRAP = 1).
    def test_a_trap_that_moves_no_objective_is_flagged_and_one_is_enough(self):
        from pipeline.harden import MIN_CHECKS_PER_NEW_TRAP, routing_problems
        self.assertEqual(MIN_CHECKS_PER_NEW_TRAP, 1)
        checks = [{"id": "c1", "kind": "objective"}, {"id": "c2", "kind": "objective"},
                  {"id": "g1", "kind": "guardrail"}]
        old = [trap(0, "trace_derived")]
        idle = {**trap(100, "authored"), "checks": ["g1"]}              # a guardrail only
        single = {**trap(101, "authored"), "checks": ["c1"]}
        self.assertTrue(routing_problems(old, old + [idle], checks))
        self.assertEqual(routing_problems(old, old + [single], checks), [])
        self.assertEqual(routing_problems(old, old, checks), [])       # existing traps untouched
