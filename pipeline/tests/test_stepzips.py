"""Per-step deliverable zips (pipeline.stepzips): shape and checks on a synthetic delivered task."""
import csv
import io
import json
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch

from pipeline import stepzips


def _write(path: Path, text: str):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)


def _delivered(tmp: Path) -> Path:
    task = tmp / "F2-scenario" / "a_f2_demo-task"
    _write(task / "task.toml", '[task]\nname = "arena/a_f2_demo-task"\ndescription = "Do a thing. More."\n'
                               '[metadata]\nsource_trace = "sess-1"\n')
    for rel in ("tests/checks.json", "tests/criteria.py", "steps/01-task/instruction.md", "steps/02-revision/instruction.md",
                "solution/README.md", "authoring/spec.json", "authoring/traps.json", "environment/files/a.md", ".dockerignore",
                "REWARD-HACKING.md", "verification/probes.json", "verification/delivery.json", "authoring/extra.json",
                "verification/release.json"):
        _write(task / rel, "{}")
    _write(task / "verification/harbor-tasks-check.json", json.dumps({"status": "pass", "artifact_sha256": "x"}))
    campaign = tmp / "campaign"
    trials = []
    for i in range(10):
        tid = f"package__t{i}"
        steps = []
        for step, reward in (("01-task", 1.0), ("02-revision", 0.0 if i < 4 else 1.0)):
            base = campaign / "jobs/run" / tid / "steps" / step
            checks = {"g": {"passed": True}, "c": {"passed": reward == 1.0}}
            _write(base / "verifier/arena-grade.json", json.dumps({"checks": checks}))
            _write(base / "verifier/reward-details.json", "{}")
            _write(base / "verifier/reward.json", "{}")
            _write(base / "agent/trajectory.json", json.dumps({"steps": [{"source": "user"}, {"source": "agent"}],
                                                                "final_metrics": {"total_prompt_tokens": 10, "total_completion_tokens": 2}}))
            _write(base / "artifacts/app/deliverables/answer.json", "{}")
            steps.append({"name": step, "valid": True, "reward": reward})
        trials.append({"id": tid, "valid": True, "steps": steps})
    trials.append({"id": "package__void", "valid": False, "steps": []})
    _write(campaign / "report.json", json.dumps({"model": "anthropic/claude-fable-5-1", "effort": "high",
                                                 "harness": {"agent": "claude-code", "version": "1"},
                                                 "limits": {"max_output_tokens": 128000}, "trials": trials}))
    _write(task / "verification/native-calibrations.json", json.dumps({"campaigns": [str(campaign)], "topups": {}}))
    return task


class StepZips(unittest.TestCase):
    def test_one_zip_per_step_with_the_full_root_and_this_steps_slice(self):
        with tempfile.TemporaryDirectory() as tmp:
            task = _delivered(Path(tmp))
            zips = stepzips.build(task, Path(tmp) / "out")
            self.assertEqual([z.name for z in zips], ["a_f2_demo-task__01-task.zip", "a_f2_demo-task__02-revision.zip"])
            with zipfile.ZipFile(zips[1]) as z:
                names = set(z.namelist())
                self.assertIn("steps/01-task/instruction.md", names)          # the whole task ships in every zip
                self.assertIn("verification/harbor-tasks-check.json", names)
                self.assertNotIn("verification/release.json", names)
                self.assertNotIn("authoring/extra.json", names)
                manifest = json.loads(z.read("CALIBRATION-MANIFEST.json"))
                self.assertEqual(manifest["task"], "a_f2_demo-task/02-revision")
                metrics = manifest["task_level_metrics"]["claude-fable-5-1"]
                self.assertEqual((metrics["episodes_valid"], metrics["passes"], metrics["pass_at_1"]), (10, 6, 0.6))
                rows = list(csv.DictReader(io.StringIO(z.read("calibration/runs.csv").decode())))
                self.assertEqual(len(rows), 10)                                # the void episode is excluded
                self.assertEqual(sum(r["step_score"] == "0.0" for r in rows), 4)
                self.assertEqual(rows[0]["failed_checks"], "c")
                self.assertIn("calibration/trajectories/claude-fable-5-1/package__t0/artifacts/answer.json", names)

    def test_check_zip_refuses_a_failed_tasks_check_receipt_and_a_short_calibration(self):
        with tempfile.TemporaryDirectory() as tmp:
            task = _delivered(Path(tmp))
            _write(task / "verification/harbor-tasks-check.json", json.dumps({"status": "unverified"}))
            z = stepzips.build(task, Path(tmp) / "out")[0]
            with patch("pipeline.verify_shipped.verify", return_value={"ok": True}):
                problems = stepzips.check_zip(z)
            self.assertTrue(any("tasks-check receipt status" in p for p in problems), problems)


if __name__ == "__main__":
    unittest.main()
