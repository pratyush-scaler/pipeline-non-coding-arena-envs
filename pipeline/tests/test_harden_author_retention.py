from copy import deepcopy
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from pipeline import checkpoint, harden
from pipeline.artifacts import atomic_json, identity
from pipeline.tests import test_guards


class InterruptedHardening(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.bundle = Path(temporary.name) / "a-001-task"
        self.bundle.mkdir()
        (self.bundle / "task.toml").write_text("")
        atomic_json(self.bundle / "tests/checks.json", [])

    def interrupt(self, current, target, *arguments, **options):
        atomic_json(target / "verification/design-sessions/retained/draft.json", {"trap": "retained"})
        checkpoint.update(target, stage="authoring", authoring_session={"session": "retained", "remaining_steps": 17})
        raise harden.DesignerUnavailable("transport interrupted")

    def run_loop(self, attempt):
        with patch("pipeline.harden.attempt", side_effect=attempt):
            return harden.run_lineage(self.bundle, test_guards.HardeningAttemptBudget.REPORT, [], screen=False)

    def test_transport_failure_retains_draft_without_spending_or_refunding(self):
        self.assertEqual(self.run_loop(self.interrupt), 2)
        ledger = harden.read_ledger(self.bundle)
        self.assertEqual(ledger["attempts"], [])
        self.assertEqual(harden.attempts_left(ledger), 3)
        interruption = ledger["interruptions"][0]
        self.assertTrue(interruption["draft_retained"])
        self.assertEqual(interruption["phase"], "authoring")
        self.assertEqual(interruption["source_artifact_sha256"], identity(self.bundle))
        self.assertTrue((self.bundle / interruption["revision"] / "verification/design-sessions/retained/draft.json").is_file())

    def test_restart_uses_same_target_and_attempt_number(self):
        self.run_loop(self.interrupt)
        target = self.bundle / "hardened/v2"
        state = checkpoint.read(target)
        with patch("pipeline.checkpoint.resumable", return_value=state), \
             patch("pipeline.harden._next_revision") as allocate, \
             patch("pipeline.harden.attempt", return_value=[]) as attempt:
            code = harden.run_lineage(self.bundle, test_guards.HardeningAttemptBudget.REPORT, [], screen=False)
        self.assertEqual(code, 0)
        allocate.assert_not_called()
        self.assertEqual(attempt.call_args.args[1], target.resolve())
        self.assertEqual(attempt.call_args.kwargs["number"], 1)
        self.assertEqual(len(harden.read_ledger(self.bundle)["attempts"]), 1)

    def test_changed_source_cannot_reroll_retained_author(self):
        self.run_loop(self.interrupt)
        (self.bundle / "task.toml").write_text("changed")
        with patch("pipeline.harden.attempt") as attempt, self.assertRaisesRegex(ValueError, "source changed"):
            harden.run_lineage(self.bundle, test_guards.HardeningAttemptBudget.REPORT, [], screen=False)
        attempt.assert_not_called()

    def test_incomplete_boundary_is_retained_for_inspection_not_restart(self):
        self.run_loop(self.interrupt)
        with patch("pipeline.checkpoint.resumable", return_value=None), \
             patch("pipeline.harden._next_revision") as allocate, \
             self.assertRaisesRegex(ValueError, "complete author boundary"):
            harden.run_lineage(self.bundle, test_guards.HardeningAttemptBudget.REPORT, [], screen=False)
        allocate.assert_not_called()
        self.assertEqual(len(harden.read_ledger(self.bundle)["attempts"]), 0)

    def test_repair_findings_and_repeated_findings_survive_interruption(self):
        def interrupted_repair(current, target, *arguments, **options):
            if options["kind"] == "harden":
                return ["first finding", "second finding"]
            return self.interrupt(current, target, *arguments, **options)

        self.run_loop(interrupted_repair)
        pending = harden.read_ledger(self.bundle)["interruptions"][0]
        self.assertEqual(pending["kind"], "repair")
        self.assertEqual(pending["findings"], ["first finding", "second finding"])
        self.assertEqual(set(pending["seen_findings"]), set(pending["findings"]))
        with patch("pipeline.checkpoint.resumable", return_value=checkpoint.read(self.bundle / "hardened/v2")), \
             patch("pipeline.harden.attempt", return_value=["first finding"]) as attempt:
            code = harden.run_lineage(self.bundle, test_guards.HardeningAttemptBudget.REPORT, [], screen=False)
        self.assertEqual(code, 1)
        self.assertEqual(attempt.call_args.kwargs["kind"], "repair")
        self.assertEqual(attempt.call_args.kwargs["number"], 2)
        self.assertEqual(harden.read_ledger(self.bundle)["status"], "stopped")

    def test_propose_resumes_only_retained_budget_and_conversation(self):
        atomic_json(self.bundle / "authoring/spec.json", {})
        session = {"session": "retained", "remaining_steps": 17}
        checkpoint.update(self.bundle, stage="authoring", authoring_session=session)
        spec = {"source": {"session_id": "source", "seed_index": 0}, "checks": [], "traps": []}
        with patch("pipeline.repair.design_inputs", return_value=(spec, {}, {})), \
             patch("pipeline.harden.faithfulness_budget", return_value={}), \
             patch("pipeline.harden._budget_text", return_value="existing"), \
             patch("pipeline.checkpoint.resumable", return_value=checkpoint.read(self.bundle)), \
             patch("pipeline.author.extract.extract", return_value=object()), \
             patch("pipeline.author.agent_designer.design", return_value=deepcopy(spec)) as design:
            harden.propose(self.bundle, [], kind="repair", findings=["retained finding"])
        self.assertEqual(design.call_args.kwargs["max_steps"], 17)
        self.assertEqual(design.call_args.kwargs["resume_session"], session)
        self.assertNotIn("initial_spec", design.call_args.kwargs)

    def measured_revision(self):
        revision = self.bundle / "hardened/v2"
        revision.mkdir(parents=True)
        (revision / "task.toml").write_text("")
        atomic_json(revision / "tests/checks.json", [])
        harden._save(self.bundle, {"status": "open", "max_attempts": 3,
            "attempts": [{"attempt": 1, "outcome": "valid", "revision": "hardened/v2", "from": "."}],
            "screens": [], "interruptions": []})
        return revision

    def test_old_no_progress_screen_does_not_discard_an_author_already_in_flight(self):
        revision = self.measured_revision()
        report = test_guards.HardeningAttemptBudget.REPORT
        with patch("pipeline.harden._judge_revision", return_value="open"), \
             patch("pipeline.harden.attempt", side_effect=self.interrupt):
            self.assertEqual(harden.run_lineage(revision, report, [], screen=False), 2)
        target = self.bundle / "hardened/v3"
        with patch("pipeline.checkpoint.resumable", return_value=checkpoint.read(target)), \
             patch("pipeline.harden._judge_revision", return_value="no-progress"), \
             patch("pipeline.harden._next_revision") as allocate, \
             patch("pipeline.harden.attempt", return_value=[]) as attempt:
            self.assertEqual(harden.run_lineage(revision, report, [], screen=False), 0)
        allocate.assert_not_called()
        self.assertEqual(attempt.call_args.args[1], target.resolve())
        self.assertEqual(attempt.call_args.kwargs["number"], 2)
        self.assertEqual(len(harden.read_ledger(self.bundle)["attempts"]), 2)

    def test_no_progress_without_retained_author_still_stops(self):
        revision = self.measured_revision()
        with patch("pipeline.harden._judge_revision", return_value="no-progress"), \
             patch("pipeline.harden.attempt") as attempt:
            self.assertEqual(harden.run_lineage(revision, test_guards.HardeningAttemptBudget.REPORT, [], screen=False), 1)
        attempt.assert_not_called()
        self.assertEqual(harden.read_ledger(self.bundle)["status"], "no-progress")

    def test_target_met_still_stops_with_retained_author(self):
        revision = self.measured_revision()
        report = test_guards.HardeningAttemptBudget.REPORT
        with patch("pipeline.harden._judge_revision", return_value="open"), \
             patch("pipeline.harden.attempt", side_effect=self.interrupt):
            self.assertEqual(harden.run_lineage(revision, report, [], screen=False), 2)
        with patch("pipeline.checkpoint.resumable", return_value=checkpoint.read(self.bundle / "hardened/v3")), \
             patch("pipeline.harden._judge_revision", return_value="target-met"), \
             patch("pipeline.harden.attempt") as attempt:
            self.assertEqual(harden.run_lineage(revision, report, [], screen=False), 0)
        attempt.assert_not_called()
        self.assertEqual(harden.read_ledger(self.bundle)["status"], "target-met")


if __name__ == "__main__":
    unittest.main()
