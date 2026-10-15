"""The batch report must not pass on missing evidence or a padded denominator."""
import unittest
from pathlib import Path
import tempfile
from unittest.mock import patch

from pipeline.deliverable import batch_acceptance, yield_metrics


class BatchReportHonesty(unittest.TestCase):
    def test_failed_or_repaired_drafts_are_not_first_pass_successes(self):
        from pipeline.orchestrate import batch, TaskResult
        tasks = [TaskResult("failed", "failed", 0, status="unverified", gate_rounds=1),
                 TaskResult("blocked", "blocked", 0, status="blocked", gate_rounds=1),
                 TaskResult("repaired", "repaired", 0, status="validated", gate_rounds=2),
                 TaskResult("continued", "continued", 0, status="validated", gate_rounds=1,
                            authoring_continued=True),
                 TaskResult("revalidated", "revalidated", 0, status="validated", gate_rounds=1,
                            validity_revalidated=True),
                 TaskResult("first", "first", 0, status="validated", gate_rounds=1)]
        with tempfile.TemporaryDirectory() as temporary, patch("pipeline.orchestrate.build_one", side_effect=tasks):
            report = batch([{}] * len(tasks), Path(temporary), None, task_workers=1)
        self.assertEqual(report["design"]["one_design_attempt"], 6)
        self.assertEqual(report["design"]["first_pass"], 1)
        self.assertIn("not a hardness result", report["design"]["first_pass_basis"])

    def test_yield_counts_each_shared_session_once_and_only_shared_ones(self):
        tasks = [{"session_id": "X"}, {"session_id": "A"}]
        self.assertEqual(yield_metrics(["A", "B"], tasks[:1])["environment_yield"], 0.0)
        result = yield_metrics(["A", "A", "B", "B"], tasks)
        self.assertEqual((result["sessions_shared"], result["environment_yield"]), (2, 0.5))

    def test_missing_or_warning_probes_are_unresolved_hacking(self):
        task = {"task_name": "t", "faithfulness_level": "F2", "reward_hacking_findings": [],
                "reward_hacking_unresolved": ["forged_state"]}
        rows = {c["criterion"]: c for c in batch_acceptance([task], {"ok": True})["criteria"]}
        self.assertFalse(rows["Reward hacking"]["ok"])
        task["reward_hacking_unresolved"] = []
        rows = {c["criterion"]: c for c in batch_acceptance([task], {"ok": True})["criteria"]}
        self.assertTrue(rows["Reward hacking"]["ok"])

    def test_hacking_is_counted_by_policy_not_by_partial_credit(self):
        # envs-final-2, 2026-09-27: a one-value-wrong answer kept 0.92-0.97 on
        # every task -- the shape the misreading rule requires -- and the batch
        # counted it, with an unscored forged_state, as 16 unresolved cases.
        from pipeline.deliverable import probe_verdicts
        clean = {"golden": 1.0, "untidy_correct": 1.0, "seed_zero": 0.0,
                 "plausible_wrong": 0.95, "destructive": 0.0, "answer_lookup": 0.0,
                 "empty_deliverable": 0.0, "forged_state": 0.0}
        verdict = probe_verdicts(clean)
        self.assertEqual((verdict["reward_hacking_findings"],
                          verdict["reward_hacking_unresolved"]), ([], []))
        self.assertEqual(verdict["partial_credit_probes"], ["plausible_wrong"])
        # full credit on a wrong answer is still a confirmed hack
        self.assertIn("plausible_wrong",
                      probe_verdicts({**clean, "plausible_wrong": 1.0})["reward_hacking_findings"])
        # a work-free attack earning most of the reward is still unresolved
        self.assertEqual(probe_verdicts({**clean, "answer_lookup": 0.6})["reward_hacking_unresolved"],
                         ["answer_lookup"])
        # a mandatory probe with no score is still unresolved
        self.assertEqual(probe_verdicts({**clean, "forged_state": None})["reward_hacking_unresolved"],
                         ["forged_state"])
