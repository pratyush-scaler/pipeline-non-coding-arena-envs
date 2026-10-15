"""`arena tasks-check` must load keys.env before Harbor's evaluator starts.

Harbor's `check` evaluator is a Claude Code agent. Run from `arena tasks-check`
with no keys in the environment it answered "Not logged in" and every delivered
copy came back `unverified` (2026-09-29)."""
import argparse
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from pipeline import cli


class TasksCheckLoadsKeys(unittest.TestCase):
    def test_keys_are_loaded_before_the_first_check(self):
        order = []
        with tempfile.TemporaryDirectory() as tmp:
            bundle = Path(tmp) / "a-001-x"
            bundle.mkdir()
            with mock.patch.object(cli, "load_keys", side_effect=lambda *a, **k: order.append("keys")), \
                 mock.patch.object(cli, "_bundles", return_value=[bundle]), \
                 mock.patch("pipeline.benchmark.tasks_check.run",
                            side_effect=lambda b: order.append("check") or {"status": "pass"}):
                code = cli.cmd_tasks_check(argparse.Namespace(root=tmp))
        self.assertEqual(code, 0)
        self.assertEqual(order, ["keys", "check"])


if __name__ == "__main__":
    unittest.main()
