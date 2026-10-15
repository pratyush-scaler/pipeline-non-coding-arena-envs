"""Hardening must improve substantive failures, not merely invalid-output rates."""
from __future__ import annotations

from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from pipeline import harden, policy
from pipeline.author import capability
from pipeline.tests.test_capability_construction import planned_spec
from pipeline.tests.test_measurement import measured


class CapabilityHardening(unittest.TestCase):
    def test_contract_only_improvement_is_not_capability_hardening(self):
        before, after = measured([6] * 8), measured([4] * 8)
        for report in after["by_model"].values():
            report["capability_difficulty"]["capability_adjusted_pass_at_1"] = 0.6
        result = harden.acceptance(before, after, True, True, [])
        self.assertFalse(result["accept"])
        self.assertFalse(result["harder"])
        self.assertEqual(result["capability_pass_at_1"]["one"], {"before": 0.6, "after": 0.6})
        self.assertTrue(any("contract failures" in reason for reason in result["reasons"]))

    def test_clean_capability_improvement_is_accepted(self):
        result = harden.acceptance(measured([6] * 8), measured([4] * 8), True, True, [])
        self.assertTrue(result["accept"], result)
        self.assertEqual(result["pass_at_1"]["one"], {"before": 0.6, "after": 0.4})

    def test_missing_capability_evidence_cannot_certify_improvement(self):
        before, after = measured([6] * 8), measured([4] * 8)
        for report in (before, after):
            for model in report["by_model"].values():
                model.pop("capability_difficulty")
        result = harden.acceptance(before, after, True, True, [])
        self.assertFalse(result["accept"])
        self.assertFalse(result["harder"])

    def test_progress_rates_use_capability_adjusted_not_official_rates(self):
        report = measured([4] * 8)
        for model in report["by_model"].values():
            model["capability_difficulty"]["capability_adjusted_pass_at_1"] = 0.6
        with patch("pipeline.harden.hardenable", return_value=report):
            self.assertEqual(harden._pass_at_1(Path("unused")), {"one": 0.6, "two": 0.6})

    def test_resumed_revision_stops_only_when_every_step_meets_the_step_goal(self):
        # User, 2026-10-02: every step <= policy.STEP_PASS_RATE_MAX on both models;
        # a whole-task target met by one hard step leaves the lineage open.
        fable, astra = policy.resolve_calibration_models()
        for rates, expected in (({fable: {"01": 0.4, "02": 1.0}, astra: {"01": 0.2, "02": 0.2}}, "open"),
                                ({fable: {"01": 0.6, "02": 0.6}, astra: {"01": 0.8, "02": 0.0}}, "open"),
                                ({fable: {"01": 0.6, "02": 0.4}}, "open"),
                                (None, "open"),
                                ({fable: {"01": 0.6, "02": 0.6}, astra: {"01": 0.4, "02": 0.0}}, "target-met")):
            with self.subTest(rates=rates):
                record = {"measurement_complete": True, "meets_target": True,
                          "shippable": True, "meets_capability_target": True}
                # The training-signal target (2026-10-13) is tested on its own;
                # here it is met so only the per-step goal decides.
                with patch("pipeline.screen.current", return_value=record), \
                        patch("pipeline.harden._signal_verdict", return_value={"target_met": True}), \
                        patch("pipeline.harden.step_pass_rates", return_value=rates):
                    status = harden._judge_revision(Path("/tmp/task"), Path("/tmp/task/hardened/v2"),
                                                    {"attempts": [], "screens": []})
                self.assertEqual(status, expected)

    def test_step_rates_come_from_campaign_reports_and_leave_voids_out(self):
        import json, tempfile
        fable, astra = policy.resolve_calibration_models()

        def trial(valid, *steps):
            return {"valid": valid, "steps": [{"name": n, "valid": v, "reward": r} for n, v, r in steps]}

        with tempfile.TemporaryDirectory() as temporary:
            record = {"per_model": {}, "index": {}}
            for model, trials in ((fable, [trial(True, ("01", True, 1.0), ("02", True, 1.0))] * 3
                                   + [trial(True, ("01", True, 1.0), ("02", True, 0.5))] * 2
                                   + [trial(False, ("01", False, 0.0), ("02", True, 0.0))] * 4),
                                  (astra, [trial(True, ("01", True, 0.0), ("02", True, 1.0))] * 5)):
                campaign = Path(temporary) / model.replace("/", "_")
                campaign.mkdir()
                (campaign / "report.json").write_text(json.dumps({"trials": trials}))
                record["per_model"][model] = {"campaign": str(campaign), "topups": []}
            self.assertEqual(harden.step_pass_rates(record), {fable: {"01": 1.0, "02": 0.6},
                                                              astra: {"01": 0.0, "02": 1.0}})
            self.assertEqual(harden.steps_too_easy(record), {fable: ["01"], astra: ["02"]})
            record["per_model"][astra]["topups"] = [str(Path(temporary) / "missing")]
            self.assertIsNone(harden.step_pass_rates(record))

    def test_capability_target_needs_both_models(self):
        from pipeline.tests.test_spec_acceptance import TheScreenReportsWhatArenaAsked, _measured

        screens = TheScreenReportsWhatArenaAsked()
        clean = screens._eps({0: [1], 1: [1], 2: [1]})
        record = screens._summarize(clean, clean)
        self.assertTrue(record["meets_target"])
        self.assertTrue(record["meets_capability_target"])
        def with_contract_failure(model, episodes):
            report = _measured(model, episodes)
            if model == screens.SECONDARY:
                report["rollouts"][0]["contract_errors"] = ["malformed output"]
            return report

        with patch("pipeline.tests.test_spec_acceptance._measured", side_effect=with_contract_failure):
            record = screens._summarize(clean, clean)
        self.assertTrue(record["meets_target"])
        self.assertFalse(record["meets_capability_target"])
        self.assertNotEqual(record["outlook"]["verdict"], "meets-target")
        self.assertEqual(record["outlook"]["signals"]["above_target"], [screens.SECONDARY])


class ScenarioPlanOrdering(unittest.TestCase):
    def test_empty_unknown_and_malformed_outlines_cannot_unlock_scenario_writes(self):
        for plan in ({}, {"version": 1, "mechanisms": []},
                     {"version": True, "mechanisms": [{"id": "authority", "kind": "authority_time"}]},
                     {"version": 1, "mechanisms": [{"id": "authority", "kind": []}]},
                     {"version": 1, "mechanisms": [{"id": "authority", "kind": "busywork"}]}):
            with self.subTest(plan=plan):
                with self.assertRaisesRegex(ValueError, "capability_plan"):
                    capability.require_staged_plan({"quality": {"capability_plan": plan}})
        capability.require_staged_plan(planned_spec())

    def test_supplement_tool_retains_source_safeguards_without_a_plan_permission_gate(self):
        from pipeline.author.agent_designer import _handlers

        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            handlers = _handlers(root, SimpleNamespace(moments=[]), {"messages": []}, category="F2")
            with patch("pipeline.author.scenario.write", return_value={"written": True}) as write:
                self.assertEqual(handlers["write_scenario"](), {"written": True})
                write.assert_called_once_with(root, category="F2")
            self.assertEqual(list((root / "environment/files").rglob("*")), [])


if __name__ == "__main__":
    unittest.main()
