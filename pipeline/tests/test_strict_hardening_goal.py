from copy import deepcopy
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from pipeline import harden, policy
from pipeline.tests import test_guards


class StrictHardeningGoalTests(unittest.TestCase):
    def setUp(self):
        # Every step under the per-step goal: these tests are about the pass@1 bound.
        rates = {model: {"01-task": 0.4, "02-revision": 0.4} for model in policy.resolve_calibration_models()}
        patcher = patch("pipeline.harden.step_pass_rates", return_value=rates)
        patcher.start()
        self.addCleanup(patcher.stop)
        # ...and the training-signal target (2026-10-13) met; it is tested on its own.
        signal = patch("pipeline.harden._signal_verdict", return_value={"target_met": True})
        signal.start()
        self.addCleanup(signal.stop)

    def screen(self, rate):
        return {"meets_target": True, "meets_capability_target": True,
                "measurement_complete": True, "shippable": True,
                "per_model": {model: {"effort": "high", "episodes_valid": 5, "pass_at_1": rate,
                    "capability_difficulty": {"episodes_valid": 5, "capability_adjusted_pass_at_1": rate}}
                    for model in policy.resolve_calibration_models()}}

    def test_general_target_does_not_end_a_stricter_lineage(self):
        self.assertTrue(harden._target_met(self.screen(0.4)))
        self.assertFalse(harden._target_met(self.screen(0.4), 0.2))
        self.assertTrue(harden._target_met(self.screen(0.2), 0.2))

    def test_contract_failures_cannot_supply_the_strict_goal(self):
        record = self.screen(0)
        record["per_model"][policy.resolve_calibration_models()[1]]["capability_difficulty"]["capability_adjusted_pass_at_1"] = 0.8
        self.assertFalse(harden._target_met(record, 0.2))

    def test_exact_models_effort_and_valid_episode_counts_are_required(self):
        original = self.screen(0.2)
        model = policy.resolve_calibration_models()[0]
        for field, value in (("effort", "low"), ("episodes_valid", policy.SCREEN_EPISODES_PER_MODEL - 1), ("episodes_valid", True),
                             ("episodes_valid", float("nan")), ("pass_at_1", None), ("pass_at_1", True)):
            record = deepcopy(original)
            record["per_model"][model][field] = value
            self.assertFalse(harden._target_met(record, 0.2))
        original["per_model"].pop(model)
        self.assertFalse(harden._target_met(original, 0.2))

    def test_goal_is_retained_and_cannot_be_changed_or_refunded(self):
        ledger = {"attempts": [], "screens": []}
        self.assertEqual(harden._bind_goal(ledger, 0.2), 0.2)
        ledger["attempts"].append({"attempt": 1})
        self.assertEqual(harden._bind_goal(ledger, None), 0.2)
        for replacement in (0.1, 0.4):
            with self.assertRaisesRegex(RuntimeError, "differs from"):
                harden._bind_goal(ledger, replacement)
        self.assertEqual(len(ledger["attempts"]), 1)

    def test_legacy_spent_attempts_cannot_be_retargeted(self):
        ledger = {"attempts": [{"attempt": 1}], "screens": []}
        with self.assertRaisesRegex(RuntimeError, "before the first"):
            harden._bind_goal(ledger, 0.2)
        self.assertNotIn("maximum_pass_at_1", ledger)

    def test_invalid_goals_are_refused(self):
        for goal in (True, -0.1, 0.5, 1, float("nan"), float("inf"), "0.2"):
            with self.subTest(goal=goal), self.assertRaises(RuntimeError):
                harden._bind_goal({"attempts": [], "screens": []}, goal)

    def test_unreadable_ledger_does_not_create_a_new_budget(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            path = root / harden.LEDGER
            path.parent.mkdir()
            path.write_text("{broken")
            with self.assertRaisesRegex(RuntimeError, "no allowance was reset"):
                harden.read_ledger(root)
            self.assertEqual(path.read_text(), "{broken")

    def test_public_cli_forwards_the_strict_goal_without_changing_it(self):
        from pipeline import cli
        arguments = cli.build_parser().parse_args(["harden", "task", "--apply", "--max-pass-at-1", "0.2"])
        with patch("pipeline.cli.load_keys"), patch("pipeline.cli._run", return_value=0) as run:
            self.assertEqual(cli.cmd_harden(arguments), 0)
        self.assertEqual(run.call_args.args, ("pipeline.harden", "task", "--apply", "--max-pass-at-1", "0.2"))

    def test_hardening_continues_past_point_four_to_the_bound_point_two(self):
        with tempfile.TemporaryDirectory() as temporary:
            bundle = Path(temporary) / "task"
            bundle.mkdir()
            (bundle / "task.toml").write_text("")
            outcomes = [{"record": self.screen(rate), "progress": True,
                         "summary": {"meets_target": True}} for rate in (0.4, 0.2)]
            with patch("pipeline.harden.hardenable", return_value=test_guards.HardeningAttemptBudget.REPORT), \
                    patch("pipeline.harden.attempt", side_effect=[[], []]) as attempt, \
                    patch("pipeline.harden.screen_round", side_effect=outcomes):
                result = harden.main([str(bundle), "--apply", "--max-pass-at-1", "0.2"])
            ledger = harden.read_ledger(bundle)
            self.assertEqual(result, 0)
            self.assertEqual(attempt.call_count, 2)
            self.assertEqual(ledger["status"], "target-met")
            self.assertEqual(ledger["maximum_pass_at_1"], 0.2)
            with self.assertRaisesRegex(RuntimeError, "hardening has ended"):
                harden.run_lineage(bundle, test_guards.HardeningAttemptBudget.REPORT, [], maximum_pass_at_1=0.1)
            self.assertEqual(len(harden.read_ledger(bundle)["attempts"]), 2)

    def test_resumed_revision_is_judged_against_its_retained_goal(self):
        ledger = {"attempts": [], "screens": [], "maximum_pass_at_1": 0.2}
        with patch("pipeline.screen.current", return_value=self.screen(0.4)):
            self.assertEqual(harden._judge_revision(Path("/tmp/task"), Path("/tmp/task/hardened/v2"), ledger), "open")
        with patch("pipeline.screen.current", return_value=self.screen(0.2)):
            self.assertEqual(harden._judge_revision(Path("/tmp/task"), Path("/tmp/task/hardened/v2"), ledger), "target-met")


if __name__ == "__main__":
    unittest.main()
