"""Training signal (Arena 261013 review, spec 10_12; user-approved design 2026-10-13).

Covers `pipeline/training_signal.py` (spread metrics and shape), `pipeline/author/premises.py`
(the static premise-map validation), the policy constants' readers, and the
screen/hardening wiring. Every fixture lives in a TemporaryDirectory.
"""
from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from pipeline import advisory, policy
from pipeline import training_signal as signal
from pipeline.author import premises

FABLE, ASTRA = "anthropic/claude-fable-5-1", "openai/gpt-6-astra"


def run(episode, reward, checks, step="01-task"):
    return {"episode": str(episode), "steps": {step: {"reward": reward, "checks": checks}}}


def conjunctive_runs(fail_sets, n_free=2, weight=15):
    """One run per entry of `fail_sets` (the premise checks it missed); four
    premise checks c0..c3 at `weight` each plus free checks f*."""
    out = []
    for e, missed in enumerate(fail_sets):
        checks = {f"c{i}": ("failed" if i in missed else "passed") for i in range(4)}
        checks.update({f"f{j}": "passed" for j in range(n_free)})
        checks["g"] = "passed"
        out.append(run(e, round(1 - weight * len(missed) / 100, 4), checks))
    return out


PREMISES = [{"id": f"P{i}", "family": fam, "checks": [f"c{i}"], "targets": "both"}
            for i, fam in enumerate(("changed_premise", "caption_only_rule",
                                     "near_twin_identity", "clean_baseline"))]
WEIGHTS = {**{(None, f"c{i}"): 15.0 for i in range(4)}, (None, "f0"): 20.0, (None, "f1"): 20.0}


class SpreadMetrics(unittest.TestCase):
    def test_independent_premises_in_band_meet_the_target(self):
        fable = conjunctive_runs([[], [0], [1, 2], [3], [0, 1]])
        astra = conjunctive_runs([[2], [], [0, 3], [1], [2, 3]])
        sig = signal.measure({FABLE: fable, ASTRA: astra}, weights=WEIGHTS, guardrails={"g"},
                             premises=PREMISES)
        self.assertTrue(sig["assessable"])
        self.assertEqual(sig["shape"], "IN_BAND", sig["reasons"])
        self.assertTrue(sig["target_met"])
        row = sig["per_model"][FABLE]
        self.assertEqual((row["passes"], row["episodes"]), (1, 5))
        self.assertEqual(row["pass_at_1"], 0.2)
        self.assertGreaterEqual(row["distinct_scores"], policy.MIN_DISTINCT_SCORES_PER_MODEL)
        self.assertGreaterEqual(row["reward_sd"], policy.MIN_RUN_REWARD_SD)
        self.assertEqual(row["premise_fail_rates"]["P0"], 0.4)
        self.assertEqual(sig["premise_fail_rates"]["P0"], 0.3)    # pooled 3 of 10
        self.assertIsNotNone(sig["max_premise_phi"])
        self.assertEqual(sig["free_share"], 0.4)                    # f0+f1 = 40 of 100
        self.assertIn("FREE_HEAVY", sig["advisory_flags"])
        self.assertNotIn("FREE_HEAVY", sig["flags"])                # advisory, not the target
        self.assertTrue(sig["hard_primary"])
        self.assertNotIn("scores", row)                             # aggregates only

    def test_identical_runs_are_flat(self):
        same = conjunctive_runs([[0, 1]] * 5)
        other = conjunctive_runs([[2], [], [0, 3], [1], [2, 3]])
        sig = signal.measure({FABLE: same, ASTRA: other}, weights=WEIGHTS, premises=PREMISES)
        self.assertEqual(sig["shape"], "FLAT")
        self.assertFalse(sig["spread_ok"])
        self.assertFalse(sig["target_met"])
        self.assertTrue(sig["in_band"])

    def test_model_sorting_outranks_too_easy(self):
        always = conjunctive_runs([[]] * 5)
        never = conjunctive_runs([[0], [0, 1], [2], [0, 3], [1, 2]])
        sig = signal.measure({FABLE: never, ASTRA: always}, weights=WEIGHTS, premises=PREMISES)
        self.assertIn("SORTING", sig["flags"])
        self.assertIn("TOO_EASY", sig["flags"])
        self.assertEqual(sig["shape"], "SORTING")
        self.assertFalse(sig["target_met"])

    def test_too_easy_with_spread(self):
        easy = conjunctive_runs([[], [], [], [1], [0, 2]])
        sig = signal.measure({FABLE: easy, ASTRA: easy}, weights=WEIGHTS, premises=PREMISES)
        self.assertEqual(sig["shape"], "TOO_EASY")
        self.assertFalse(sig["in_band"])

    def test_a_premise_nobody_resolves_is_constant(self):
        fable = conjunctive_runs([[3], [0, 3], [1, 3], [2, 3], [3]])
        astra = conjunctive_runs([[3, 1], [3], [0, 3], [3, 2], [3, 0, 1]])
        sig = signal.measure({FABLE: fable, ASTRA: astra}, weights=WEIGHTS, premises=PREMISES)
        self.assertEqual(sig["constant_premises"], ["P3"])
        self.assertEqual(sig["shape"], "CONSTANT_PREMISE")
        self.assertIn("NO_FULL_PASS", sig["advisory_flags"])
        # Without a map the never-passed objective is the constant unit.
        bare = signal.measure({FABLE: fable, ASTRA: astra}, weights=WEIGHTS)
        self.assertEqual(bare["premise_map"], "absent")
        self.assertEqual(bare["constant_checks"], ["01-task/c3"])
        self.assertIn("CONSTANT_PREMISE", bare["flags"])
        self.assertIn("PREMISE_MAP_ABSENT", bare["advisory_flags"])
        self.assertIsNone(bare["premise_fail_rates"])

    def test_too_few_runs_is_not_assessable(self):
        sig = signal.measure({FABLE: conjunctive_runs([[], [0]]),  # below the 3-episode screen floor
                              ASTRA: conjunctive_runs([[2], [], [0], [1], [3]])}, weights=WEIGHTS)
        self.assertFalse(sig["assessable"])
        self.assertIsNone(sig["shape"])
        self.assertFalse(sig["target_met"])
        one_model = signal.measure({FABLE: conjunctive_runs([[]] * 5)}, weights=WEIGHTS)
        self.assertFalse(one_model["assessable"])

    def test_every_step_is_measured_on_its_own(self):
        def two_step(e, r1, r2):
            return {"episode": str(e), "steps": {
                "01-task": {"reward": r1, "checks": {"a": "passed" if r1 == 1 else "failed"}},
                "02-revision": {"reward": r2, "checks": {"b": "passed" if r2 == 1 else "failed"}}}}
        # Step 1 fully passed in 4 of 5 runs although the task passes in 1 of 5.
        runs = [two_step(0, 1.0, 1.0), two_step(1, 1.0, 0.6), two_step(2, 1.0, 0.8),
                two_step(3, 1.0, 0.4), two_step(4, 0.7, 0.6)]
        sig = signal.measure({FABLE: runs, ASTRA: runs})
        self.assertEqual(sig["per_model"][FABLE]["pass_at_1"], 0.2)
        self.assertEqual(sig["per_model"][FABLE]["steps"]["01-task"]["pass_rate"], 0.8)
        self.assertIn("TOO_EASY", sig["flags"])
        self.assertTrue(any("01-task 0.80" in r for r in sig["reasons"]))
        self.assertIn("FLAT", sig["flags"])                         # step 1: two distinct scores

    def test_gated_out_is_not_failed(self):
        runs = [run(e, 1.0 if e else 0.9, {"x": "gated_out" if e < 3 else "failed", "y": "passed"})
                for e in range(5)]
        sig = signal.measure({FABLE: runs, ASTRA: runs})
        self.assertEqual(sig["per_model"][FABLE]["check_fail_rates"]["01-task/x"], 1.0)
        self.assertEqual(sig["steps"]["01-task"]["constant_checks"], ["x"])

    def test_linked_checks_are_reported(self):
        runs = [run(e, 0.7 if e % 2 else 1.0, {"a": "failed" if e % 2 else "passed",
                                               "b": "failed" if e % 2 else "passed"}) for e in range(5)]
        sig = signal.measure({FABLE: runs, ASTRA: runs})
        self.assertTrue(sig["steps"]["01-task"]["failing_checks_linked"])
        self.assertIn("CHECKS_LINKED", sig["advisory_flags"])

    def test_phi_and_wilson(self):
        self.assertEqual(signal.phi([1, 0, 1, 0], [1, 0, 1, 0]), 1.0)
        self.assertEqual(signal.phi([1, 0, 1, 0], [0, 1, 0, 1]), -1.0)
        self.assertIsNone(signal.phi([1, 1, 1], [0, 1, 0]))
        low, high = signal.wilson(0, 10)
        self.assertEqual(low, 0.0)
        self.assertLess(high, 0.25)
        self.assertIsNone(signal.wilson(0, 0))

    def test_the_policy_constants_are_read_at_call_time(self):
        runs = conjunctive_runs([[], [0], [1, 2], [3], [0, 1]])
        base = signal.measure({FABLE: runs, ASTRA: runs}, weights=WEIGHTS, premises=PREMISES)
        self.assertNotIn("FLAT", base["flags"])
        with patch.object(policy, "MIN_DISTINCT_SCORES_PER_MODEL", 9):
            self.assertIn("FLAT", signal.measure({FABLE: runs, ASTRA: runs}, weights=WEIGHTS)["flags"])
        with patch.object(policy, "MIN_RUN_REWARD_SD", 0.5):
            self.assertIn("FLAT", signal.measure({FABLE: runs, ASTRA: runs}, weights=WEIGHTS)["flags"])
        with patch.object(policy, "EXTREME_PASS_AT_1_MAX", 0.1):
            self.assertIn("TOO_EASY", signal.measure({FABLE: runs, ASTRA: runs}, weights=WEIGHTS)["flags"])
        with patch.object(policy, "MAX_FREE_SHARE", 0.5):
            self.assertNotIn("FREE_HEAVY", signal.measure({FABLE: runs, ASTRA: runs}, weights=WEIGHTS)
                             ["advisory_flags"])
        with patch.object(policy, "MODEL_SORTING_HIGH_PASS_AT_1", 0.2), \
                patch.object(policy, "MODEL_SORTING_LOW_PASS_AT_1", 0.2):
            other = conjunctive_runs([[0], [1], [2], [3], [0, 1]])
            self.assertIn("SORTING", signal.measure({FABLE: runs, ASTRA: other}, weights=WEIGHTS)["flags"])
        with patch.object(policy, "MAX_PREMISE_PHI", -1.0):
            self.assertIn("PREMISES_LINKED", signal.measure({FABLE: runs, ASTRA: runs}, weights=WEIGHTS,
                                                            premises=PREMISES)["advisory_flags"])
        with patch.object(policy, "PREMISE_MISS_RATE_BAND", (0.9, 1.0)):
            self.assertIn("PREMISE_RATE_OUT_OF_BAND", signal.measure(
                {FABLE: runs, ASTRA: runs}, weights=WEIGHTS, premises=PREMISES)["advisory_flags"])
        with patch.object(policy, "SIGNAL_SHAPES", ("FLAT", "SORTING", "TOO_EASY", "CONSTANT_PREMISE", "IN_BAND")):
            flat_and_easy = signal.measure({FABLE: conjunctive_runs([[]] * 4 + [[0]]),
                                            ASTRA: conjunctive_runs([[]] * 4 + [[0]])}, weights=WEIGHTS)
            self.assertEqual(flat_and_easy["shape"], "FLAT")

    def test_improvement_needs_a_cleared_flag_and_no_new_one(self):
        flat = {"assessable": True, "flags": ["FLAT", "TOO_EASY"]}
        self.assertTrue(signal.improved(flat, {"assessable": True, "flags": ["TOO_EASY"]}))
        self.assertFalse(signal.improved(flat, {"assessable": True, "flags": ["FLAT", "TOO_EASY"]}))
        self.assertFalse(signal.improved(flat, {"assessable": True, "flags": ["CONSTANT_PREMISE"]}))
        self.assertIsNone(signal.improved(None, flat))
        self.assertIsNone(signal.improved(flat, {"assessable": False}))


class CampaignReports(unittest.TestCase):
    def _report(self, rewards, model=FABLE):
        trials = []
        for i, (valid, reward, missed) in enumerate(rewards):
            checks = {f"reward/c{k}": {"value": 0.0 if k in missed else 1.0, "gated_out": False}
                      for k in range(4)}
            checks["reward/g"] = {"value": 1.0, "gated_out": False}
            trials.append({"id": f"t{i}", "valid": valid, "reward": reward,
                           "steps": [{"name": "01-task", "valid": valid, "reward": reward, "checks": checks}]})
        return {"model": model, "step_names": ["01-task"], "trials": trials}

    def test_void_trials_leave_and_prefixes_are_stripped(self):
        runs = signal.runs_from_report(self._report([(True, 1.0, []), (False, 0.0, [0, 1, 2, 3]),
                                                     (True, 0.85, [1])]))
        self.assertEqual(len(runs), 2)
        self.assertEqual(runs[1]["steps"]["01-task"]["checks"]["c1"], "failed")
        self.assertIn("g", runs[0]["steps"]["01-task"]["checks"])

    def test_from_screen_record_reads_the_cited_campaigns_and_the_premise_map(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            bundle = root / "a-001-task"
            (bundle / "tests").mkdir(parents=True)
            (bundle / "authoring").mkdir()
            checks = [{"id": f"c{i}", "kind": "objective", "weight": 15} for i in range(4)]
            checks += [{"id": "g", "kind": "guardrail", "weight": 0}]
            (bundle / "tests/checks.json").write_text(json.dumps({"checks": checks}))
            (bundle / "authoring/spec.json").write_text(json.dumps({"quality": {"premise_map": PREMISES}}))
            record = {"bundle_path": str(bundle), "models": [FABLE, ASTRA], "per_model": {}, "index": {}}
            plans = {FABLE: [(True, 1.0, []), (True, 0.85, [0]), (True, 0.7, [1, 2]), (True, 0.85, [3]),
                             (True, 0.7, [0, 1])],
                     ASTRA: [(True, 0.85, [2]), (True, 1.0, []), (True, 0.7, [0, 3]), (True, 0.85, [1]),
                             (True, 0.7, [2, 3])]}
            for model, plan in plans.items():
                campaign = root / model.split("/")[-1]
                campaign.mkdir()
                (campaign / "report.json").write_text(json.dumps(self._report(plan, model)))
                record["per_model"][model] = {"campaign": str(campaign), "topups": []}
            sig = signal.from_screen_record(record)
            self.assertEqual(sig["premise_map"], "present")
            self.assertEqual(sig["shape"], "IN_BAND", sig["reasons"])
            self.assertEqual(sig["free_share"], 0.0)
            fams = signal.task_families(bundle, sig)
            self.assertEqual(len(fams["families"]), 4)
            self.assertIn(fams["decisive"], {p["family"] for p in PREMISES})
            # A receipt from before the signal existed is re-derived for the report.
            from pipeline import screen
            doc = screen.report([dict(record, bundle=bundle.name)])
            self.assertEqual(doc["rows"][0]["signal"]["shape"], "IN_BAND")
            self.assertEqual(doc["family_quotas"]["tasks_with_map"], 1)
            # An unreadable cited campaign is missing evidence, never an empty one.
            record["per_model"][ASTRA]["topups"] = [str(root / "missing")]
            self.assertIsNone(signal.from_screen_record(record))


class BatchFamilyQuotas(unittest.TestCase):
    def test_quotas_flag_overuse_and_count_only_mapped_tasks(self):
        tasks = [{"bundle": f"t{i}", "families": ["timestamp_ordering", "changed_premise"],
                  "decisive": "timestamp_ordering"} for i in range(3)]
        tasks += [{"bundle": "t9", "families": None, "decisive": None}]
        quotas = signal.batch_family_quotas(tasks)
        self.assertEqual(quotas["tasks_with_map"], 3)
        self.assertEqual(quotas["tasks_without_map"], ["t9"])
        text = " ".join(quotas["flags"])
        self.assertIn("timestamp_ordering is the decisive premise in 3/3", text)
        self.assertIn("changed_premise appears in 3/3", text)
        self.assertIn("timestamp ordering appears in 3/3", text)
        self.assertIn(f"a batch carries at least {policy.MIN_BATCH_FAMILIES}", text)

    def test_a_diverse_batch_is_within_quota(self):
        families = sorted(policy.TRAP_FAMILIES)[:12]
        tasks = [{"bundle": f"t{i}", "families": [families[i], families[(i + 6) % 12]],
                  "decisive": families[i]} for i in range(12)]
        with patch.object(policy, "MAX_FAMILY_PRESENCE_SHARE", 0.35):
            self.assertEqual(signal.batch_family_quotas(tasks)["flags"], [])

    def test_decisive_family_prefers_the_measured_premise(self):
        weights = {"P0": 30.0, "P1": 10.0}
        entries = [{"id": "P0", "family": "a"}, {"id": "P1", "family": "b"}]
        self.assertEqual(signal.decisive_family(None, entries, weights), "a")
        self.assertEqual(signal.decisive_family({"premise_fail_rates": {"P0": 0.1, "P1": 0.6}},
                                                entries, weights), "b")
        self.assertIsNone(signal.decisive_family(None, [], {}))


def spec(premise_map=None, checks=None, steps=None, instruction="Write the review to out.json."):
    checks = checks or ([{"id": f"c{i}", "kind": "objective", "weight": 15, "step": "01-task"} for i in range(4)]
                        + [{"id": "f0", "kind": "objective", "weight": 40, "step": "01-task"},
                           {"id": "g", "kind": "guardrail", "weight": 0, "step": "01-task"}])
    out = {"steps": steps or [{"name": "01-task", "instruction": instruction}], "checks": checks,
           "outputs": [{"file": "out.json", "step": "01-task"}], "quality": {}}
    if premise_map is not None:
        out["quality"]["premise_map"] = premise_map
    return out


def entry(pid, family, checks, file="policies/rules.md", quote="Invoices dated after the cut-off are excluded."):
    return {"id": pid, "family": family, "checks": checks, "targets": "both",
            "resolving_quote": {"file": file, "quote": quote}}


class PremiseMapValidation(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.bundle = Path(self.tmp.name) / "b"
        files = self.bundle / "environment/files/policies"
        files.mkdir(parents=True)
        for name, text in (("rules.md", "Invoices dated after the cut-off are excluded.\n"),
                           ("caption.md", "Figures in grey are provisional and do not count.\n"),
                           ("twins.md", "Supplier identity is the registry number, never the trading name.\n"),
                           ("baseline.md", "The before column is the audited figure at the start of the year.\n")):
            (files / name).write_text(text)

    def good_map(self):
        return [entry("P0", "changed_premise", ["c0"]),
                entry("P1", "caption_only_rule", ["c1"], "policies/caption.md",
                      "Figures in grey are provisional and do not count."),
                entry("P2", "near_twin_identity", ["c2"], "policies/twins.md",
                      "Supplier identity is the registry number, never the trading name."),
                entry("P3", "clean_baseline", ["c3"], "policies/baseline.md",
                      "The before column is the audited figure at the start of the year.")]

    def split(self, s):
        return advisory.split(premises.problems(s, self.bundle))

    def test_absent_map_is_one_advisory(self):
        blocking, advised = self.split(spec())
        self.assertEqual(blocking, [])
        self.assertEqual(len(advised), 1)
        self.assertIn("premise map absent", advised[0])

    def test_a_good_map_has_no_blocking_finding(self):
        s = spec(self.good_map())
        blocking, advised = self.split(s)
        self.assertEqual(blocking, [])
        # f0 is 40 of 100 free: above the 35% cap, an advisory only.
        self.assertTrue(any("on checks no premise decides" in a for a in advised), advised)
        shape = premises.design_shape(s)
        self.assertEqual(shape["premises"], 4)
        self.assertEqual(shape["max_premise_share"], 0.15)
        self.assertEqual(shape["max_free_share"], 0.4)

    def test_one_check_in_two_premises_blocks(self):
        bad = self.good_map()
        bad[1]["checks"] = ["c1", "c0"]
        blocking, _ = self.split(spec(bad))
        self.assertTrue(any("claimed by premises 'P0' and 'P1'" in b for b in blocking), blocking)

    def test_unknown_and_guardrail_checks_and_families_block(self):
        bad = self.good_map()
        bad[0]["checks"] = ["nope"]
        bad[1]["checks"] = ["g"]
        bad[2]["family"] = "clock_vibes"
        blocking, _ = self.split(spec(bad))
        text = " ".join(blocking)
        self.assertIn("'nope', which is not a declared check", text)
        self.assertIn("'g', which is a guardrail or ungraded check", text)
        self.assertIn("family 'clock_vibes' is not a catalogued family", text)

    def test_resolving_quotes_must_be_in_the_materials(self):
        bad = self.good_map()
        bad[0]["resolving_quote"]["quote"] = "Invoices dated before the cut-off are excluded."
        bad[1]["resolving_quote"] = {"file": "../secret.md", "quote": "Figures in grey are provisional."}
        bad[2]["resolving_quote"] = {"file": "policies/none.md", "quote": "Supplier identity is the registry."}
        del bad[3]["resolving_quote"]
        blocking, _ = self.split(spec(bad))
        text = " ".join(blocking)
        self.assertIn("is not verbatim in 'policies/rules.md'", text)
        self.assertIn("escapes the fixture", text)
        self.assertIn("'policies/none.md' is not a fixture file", text)
        self.assertIn("needs resolving_quote", text)
        ok = self.good_map()
        ok[0]["resolving_quote"] = {"file": "instruction", "quote": "write the review to OUT.json"}
        self.assertEqual(self.split(spec(ok))[0], [])

    def test_quotes_are_found_in_withheld_step_files(self):
        overlay = self.bundle / "environment/step-files/02-revision/policies"
        overlay.mkdir(parents=True)
        (overlay / "memo.md").write_text("The revised threshold applies to every open claim.\n")
        m = self.good_map()
        m[0]["resolving_quote"] = {"file": "policies/memo.md",
                                   "quote": "The revised threshold applies to every open claim."}
        self.assertEqual(self.split(spec(m))[0], [])

    def test_design_targets_are_advisories(self):
        heavy = [{"id": "c0", "kind": "objective", "weight": 60, "step": "01-task"},
                 {"id": "c1", "kind": "objective", "weight": 20, "step": "01-task"},
                 {"id": "c2", "kind": "objective", "weight": 20, "step": "01-task"}]
        m = [entry("P0", "timestamp_ordering", ["c0"]),
             entry("P1", "timestamp_ordering", ["c1"], "policies/caption.md",
                   "Figures in grey are provisional and do not count."),
             {**entry("P2", "authority_delegation", ["c2"]), "targets": "nobody"}]
        blocking, advised = self.split(spec(m, checks=heavy))
        self.assertEqual(blocking, [])
        text = " ".join(advised)
        self.assertIn("3 independent premise(s); a single-step task carries at least 4", text)
        self.assertIn("premise 'P0' carries 60%", text)
        self.assertIn("share family 'timestamp_ordering'", text)
        self.assertIn("2 timestamp-ordering premises", text)
        self.assertIn("discouraged family 'authority_delegation'", text)
        self.assertIn("targets 'nobody'", text)
        self.assertIn("are both settled by 'policies/rules.md'", text)
        with patch.object(policy, "MAX_PREMISE_SHARE", 0.7), patch.object(policy, "MIN_INDEPENDENT_PREMISES", 3), \
                patch.object(policy, "MAX_TIMESTAMP_PREMISES_PER_TASK", 2):
            relaxed = " ".join(self.split(spec(m, checks=heavy))[1])
        self.assertNotIn("carries 60%", relaxed)
        self.assertNotIn("a single-step task carries at least", relaxed)
        self.assertNotIn("timestamp-ordering premises", relaxed)

    def test_multi_turn_counts_per_step(self):
        checks = [{"id": f"a{i}", "kind": "objective", "weight": 10, "step": "01-task"} for i in range(5)]
        checks += [{"id": f"b{i}", "kind": "objective", "weight": 10, "step": "02-revision"} for i in range(5)]
        steps = [{"name": "01-task", "instruction": "Write out.json."},
                 {"name": "02-revision", "instruction": "Write out2.json."}]
        families = ["changed_premise", "caption_only_rule", "near_twin_identity", "clean_baseline"]
        m = [entry(f"P{i}", fam, [f"a{i}"]) for i, fam in enumerate(families)]
        m = [{**e, "resolving_quote": {"file": "instruction", "quote": "Write out.json."}} for e in m]
        text = " ".join(advisory.split(premises.problems(spec(m, checks=checks, steps=steps), self.bundle))[1])
        self.assertIn("4 independent premise(s) across 2 steps", text)
        self.assertIn("step '02-revision' carries 0 premise(s)", text)

    def test_validate_reports_the_map_on_production_specs_only(self):
        from pipeline.author.validate import validate
        legacy = {"checks": [{"id": "c0", "kind": "objective", "weight": 10, "assertion": "equals",
                              "basis": "b", "actual": {"op": "field", "file": "o.json", "path": "x"},
                              "target": {"op": "literal", "value": 1, "why": "w"}}], "traps": []}
        self.assertFalse(any("premise" in p for p in validate(legacy, self.bundle)))
        bad = dict(legacy, quality={"premise_map": "P1"})
        self.assertTrue(any(p.startswith("premise map: quality.premise_map must be a list")
                            for p in validate(bad, self.bundle)))


class ScreenAndHardeningWiring(unittest.TestCase):
    def _measured(self, model, rewards_and_fails):
        rows, stats = [], {}
        for number, (reward, missed) in enumerate(rewards_and_fails, 1):
            states = {f"c{i}": ("failed" if i in missed else "passed") for i in range(8)}
            rows.append({"episode": number, "step": "01-task", "id": f"t{number}/01-task", "reward": reward,
                         "zero_class": None, "error": None, "stop_reason": "completed", "tool_calls": 9,
                         "checks": states})
            for cid, state in states.items():
                rec = stats.setdefault(cid, {"passed": 0, "failed": 0, "gated_out": 0,
                                             "kind": "objective", "weight": 12})
                rec[state] += 1
        return {"model": model, "by_step": {"01-task": {"checks": stats}}, "rollouts": rows, "trials": [],
                "step_names": ["01-task"], "effort": policy.SPEC_CALIBRATION_EFFORT, "protocol": "native",
                "voids_excluded": 0, "limits": {"no_limits": policy.SPEC_NO_LIMITS}}

    def _summarize(self, fable, astra):
        from pipeline import screen
        from pipeline.tests.test_spec_acceptance import _screen_bundle
        measured = {"p": self._measured(FABLE, fable), "s": self._measured(ASTRA, astra)}
        with tempfile.TemporaryDirectory() as tmp:
            bundle = _screen_bundle(Path(tmp))
            with patch("pipeline.release.calibration_measurement",
                       side_effect=lambda b, i, path, n: ([], measured[path])), \
                    patch("pipeline.attribution.all_fail_problems", return_value=[]), \
                    patch("pipeline.attribution.trajectory_hacks", return_value=[]):
                return screen.summarize(bundle, {"campaigns": ["p", "s"], "topups": {}}, 5,
                                        list(policy.resolve_calibration_models()))

    SPREAD_F = [(1.0, []), (0.88, [1]), (0.76, [2, 3]), (0.88, [4]), (0.76, [1, 5])]
    SPREAD_A = [(0.88, [2]), (1.0, []), (0.76, [0, 3]), (0.88, [6]), (0.64, [2, 3, 7])]

    def test_every_screen_carries_the_signal_and_the_report_prints_it(self):
        from pipeline import screen
        record = self._summarize(self.SPREAD_F, self.SPREAD_A)
        self.assertEqual(record["signal"]["shape"], "IN_BAND", record["signal"]["reasons"])
        self.assertEqual(record["signal"]["premise_map"], "absent")
        self.assertEqual(record["premise_families"], {"families": None, "decisive": None})
        doc = screen.report([record])
        self.assertEqual(doc["signal_shapes"], {"IN_BAND": 1})
        self.assertEqual(doc["family_quotas"]["tasks_without_map"], ["a-001-screened"])
        text = screen.markdown(doc)
        self.assertIn("## Training signal", text)
        self.assertIn("| IN_BAND |", text)
        self.assertIn("premise map absent", text)
        self.assertIn("### Trap-family diversity (batch)", text)
        self.assertIn("IN_BAND", screen._one_line(record))

    def test_a_flat_screen_is_reported_but_still_shippable(self):
        flat = [(0.88, [i]) for i in range(1, 6)]           # alike scores, no constant check
        record = self._summarize(flat, flat)
        self.assertEqual(record["signal"]["shape"], "FLAT")
        self.assertTrue(record["shippable"], record["shippable_problems"])
        with patch.object(policy, "SIGNAL_GATES_RELEASE", True):
            gated = self._summarize(flat, flat)
        self.assertFalse(gated["shippable"])
        self.assertTrue(any("training-signal shape FLAT" in p for p in gated["shippable_problems"]))

    def test_target_met_needs_the_signal(self):
        from pipeline import harden
        record = {"measurement_complete": True, "shippable": True}
        steps_ok = {m: [] for m in policy.resolve_calibration_models()}
        with patch("pipeline.harden.steps_too_easy", return_value=steps_ok):
            with patch("pipeline.harden._signal_verdict", return_value={"target_met": False, "shape": "FLAT"}):
                self.assertFalse(harden._target_met(record))
            with patch("pipeline.harden._signal_verdict", return_value=None):
                self.assertFalse(harden._target_met(record))
            with patch("pipeline.harden._signal_verdict", return_value={"target_met": True}):
                self.assertTrue(harden._target_met(record))

    def test_signal_verdict_is_rederived_from_campaigns(self):
        from pipeline import harden
        self.assertIsNone(harden._signal_verdict({"per_model": {FABLE: {"campaign": None}}}))
        self.assertIsNone(harden._signal_verdict({}))
        with patch("pipeline.training_signal.from_screen_record", return_value={"target_met": True}) as derive:
            self.assertEqual(harden._signal_verdict({"signal": {"target_met": False}, "x": 1}),
                             {"target_met": True})
        derive.assert_called_once()

    def test_a_cleared_spread_flag_is_progress(self):
        from pipeline import harden
        root, revision = Path("/nonexistent/task"), Path("/nonexistent/task/hardened/v2")
        parent_record = {"tag": "parent", "measurement_complete": True}
        rev_record = {"tag": "rev", "measurement_complete": True, "shippable": True}
        verdicts = {"parent": {"assessable": True, "flags": ["FLAT"]},
                    "rev": {"assessable": True, "flags": [], "shape": "IN_BAND", "target_met": True}}
        too_easy = {m: ["01-task"] for m in policy.resolve_calibration_models()}

        def judge(rev_flags):
            verdicts["rev"]["flags"] = rev_flags
            ledger = {"attempts": [{"from": ".", "revision": "hardened/v2", "outcome": "valid"}], "screens": []}
            with patch("pipeline.screen.current",
                       side_effect=lambda path: parent_record if Path(path) == root else rev_record), \
                    patch("pipeline.harden._pass_at_1", return_value={FABLE: 0.6, ASTRA: 0.6}), \
                    patch("pipeline.harden._signal_verdict",
                          side_effect=lambda record: verdicts[(record or {}).get("tag", "rev")]), \
                    patch("pipeline.harden.steps_too_easy", return_value=too_easy), \
                    patch("pipeline.harden.step_pass_rates", return_value=None):
                status = harden._judge_revision(root, revision, ledger)
            return status, ledger["screens"][-1]

        status, screen_row = judge([])
        self.assertEqual(status, "open")
        self.assertTrue(screen_row["progress"])
        self.assertEqual(screen_row["signal_shape"], "IN_BAND")
        self.assertEqual(judge(["FLAT"])[0], "no-progress")

    def test_the_hardening_brief_leads_with_the_conjunctive_design(self):
        from pipeline import harden
        text = harden.CONJUNCTIVE_HARDENING
        self.assertIn("THE TARGET IS A BAND WITH A GRADIENT, NOT ZERO", text)
        self.assertIn(f"{policy.EXTREME_PASS_AT_1_MAX:.0%}", text)
        self.assertIn("NEVER route an existing check through another premise", text)
        self.assertNotIn("ROUTE SEVERAL CHECKS THROUGH EACH PREMISE", harden.HARDENING_BRIEF)
        self.assertIn("SUPERSEDED IN PART by the V4", harden.HARDENING_BRIEF)
        brief = signal.hardening_text({"assessable": True, "shape": "FLAT", "flags": ["FLAT"],
                                       "advisory_flags": ["PREMISE_MAP_ABSENT"], "in_band": True,
                                       "spread_ok": False, "target_met": False, "per_model": {},
                                       "reasons": ["FLAT: x"]})
        self.assertIn("TRAINING SIGNAL OF THE VERSION YOU ARE REVISING", brief)
        self.assertIn("FLAT: runs score alike", brief)
        self.assertIn("record quality.premise_map", brief)
        with tempfile.TemporaryDirectory() as tmp:
            self.assertIn("Not assessable", harden._signal_text(Path(tmp)))


class DesignerDoctrine(unittest.TestCase):
    def test_the_conjunctive_doctrine_leads_the_system_prompt(self):
        from pipeline.author import agent_designer as a
        from pipeline.author import levers
        self.assertLess(levers.PROMPT.index("V4 CONJUNCTIVE DOCTRINE"), levers.PROMPT.index("V3 DOCTRINE"))
        self.assertLess(levers.PROMPT.index("V4 CONJUNCTIVE DOCTRINE"), 200)
        self.assertLess(a.SYSTEM.index("V4 CONJUNCTIVE DOCTRINE"), a.SYSTEM.index("V3 DOCTRINE"))
        self.assertIn("quality.premise_map", a.SYSTEM)
        for family in policy.TRAP_FAMILIES:
            self.assertIn(f" - {family}", levers.PROMPT)
        self.assertIn("COMPOSITION -- SUPERSEDED BY THE V4 CONJUNCTIVE DOCTRINE", levers.PROMPT)
        self.assertNotIn("Each bite feeds 2-3 SEPARATE objective checks", levers.PROMPT)
        self.assertNotIn("MAKE EACH PREMISE BEAR ON SEVERAL DECISIONS", a.SYSTEM)
        self.assertIn("record quality.premise_map", a.AUTHORING_MANDATE)

    def test_family_evidence_covers_the_taxonomy(self):
        from pipeline.author import levers
        evidence = levers.measured_evidence().get("families") or {}
        self.assertEqual(set(evidence), set(policy.TRAP_FAMILIES))
        self.assertIn(policy.TIMESTAMP_FAMILY, policy.TRAP_FAMILIES)
        self.assertTrue(set(policy.DISCOURAGED_DECIDER_FAMILIES) <= set(policy.TRAP_FAMILIES))

    def test_the_playbook_retires_the_cascade_weight_rule(self):
        text = (Path(__file__).resolve().parents[2] / "rulesets/PLAYBOOK_GENERAL.md").read_text()
        self.assertIn("### The eighth lever — conjunction of independent premises", text)
        self.assertIn("~~**The target is\nweight concentration, not check count:** root check plus cascade "
                      "carrying ≥50%\nof total weight.~~ **SUPERSEDED 2026-10-13", text)
        self.assertIn("~~**Cascade.**~~ **SUPERSEDED 2026-10-13", text)


class PolicyReaders(unittest.TestCase):
    NEW = ("SIGNAL_GATES_RELEASE", "EXTREME_PASS_AT_1_MAX", "EXTREME_PRIMARY_PASS_AT_1_PREFERRED",
           "MIN_DISTINCT_SCORES_PER_MODEL", "MIN_RUN_REWARD_SD", "MAX_FREE_SHARE", "MAX_PREMISE_SHARE",
           "MIN_INDEPENDENT_PREMISES", "MIN_PREMISES_PER_STEP_MULTI_TURN", "MIN_PREMISES_MULTI_TURN_TOTAL",
           "MAX_TIMESTAMP_PREMISES_PER_TASK", "MAX_PREMISE_PHI", "PREMISE_MISS_RATE_BAND",
           "MODEL_SORTING_HIGH_PASS_AT_1", "MODEL_SORTING_LOW_PASS_AT_1", "SIGNAL_SHAPES",
           "MAX_FAMILY_HEAVIEST_SHARE", "MAX_FAMILY_PRESENCE_SHARE", "MIN_BATCH_FAMILIES",
           "MAX_TIMESTAMP_TASK_SHARE", "TRAP_FAMILIES", "TIMESTAMP_FAMILY", "DISCOURAGED_DECIDER_FAMILIES")

    def test_every_new_constant_has_a_reader_outside_policy(self):
        import re
        root = Path(__file__).resolve().parents[1]
        body = "\n".join(p.read_text() for p in root.rglob("*.py")
                         if p.name != "policy.py" and "tests" not in p.parts)
        for name in self.NEW:
            self.assertTrue(hasattr(policy, name), name)
            self.assertRegex(body, rf"\b{re.escape(name)}\b", f"{name} has no reader")

    def test_the_values_are_the_approved_ones(self):
        self.assertEqual(policy.EXTREME_PASS_AT_1_MAX, 0.3)
        self.assertEqual(policy.EXTREME_PRIMARY_PASS_AT_1_PREFERRED, policy.SPEC_HARD_MAX)
        self.assertEqual(policy.MIN_DISTINCT_SCORES_PER_MODEL, 3)
        self.assertEqual(policy.MAX_FREE_SHARE, 0.35)
        self.assertEqual(policy.MAX_PREMISE_SHARE, 0.25)
        self.assertEqual((policy.MIN_INDEPENDENT_PREMISES, policy.MIN_PREMISES_PER_STEP_MULTI_TURN,
                          policy.MIN_PREMISES_MULTI_TURN_TOTAL), (4, 2, 5))
        self.assertEqual(policy.MAX_TIMESTAMP_PREMISES_PER_TASK, 1)
        self.assertEqual((policy.MAX_FAMILY_HEAVIEST_SHARE, policy.MAX_FAMILY_PRESENCE_SHARE), (0.20, 0.35))
        self.assertIs(policy.SIGNAL_GATES_RELEASE, False)
        self.assertIs(policy.DIFFICULTY_GATES_RELEASE, False)
        self.assertEqual(policy.CALIBRATION_TARGET_PASS_AT_1, 0.5)       # Arena's general target unchanged
        self.assertEqual(policy.SIGNAL_SHAPES[-1], "IN_BAND")


if __name__ == "__main__":
    unittest.main()
