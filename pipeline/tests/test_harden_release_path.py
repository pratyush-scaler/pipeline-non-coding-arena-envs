"""The harden -> release path: a repair sees the failing gate's own message, and
a rebuilt revision carries its level and its original's task name
(a-053 hardened/v2 and a-055 hardened/v4, 2026-09-28)."""
import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from pipeline.harden import _gate_findings
from pipeline import repair


class GateFindings(unittest.TestCase):
    def test_green_has_no_findings(self):
        self.assertEqual(_gate_findings({"verdict": "green", "results": []}), [])

    def test_a_blocked_chain_names_each_failing_gate_blocker(self):
        gates = {"verdict": "blocked", "results": [
            {"gate": "env.step_isolation", "status": "fail",
             "blockers": [{"message": "index.html is readable during step '01-task' but carries a later-step answer"}]},
            {"gate": "grader.reference", "status": "pass", "blockers": []}]}
        self.assertEqual(_gate_findings(gates), [
            "env.step_isolation: index.html is readable during step '01-task' but carries a later-step answer"])

    def test_one_blocker_is_one_finding_so_a_repair_can_shrink_the_set(self):
        # a-104 (2026-09-29): two routing findings fixed, one new blocker -> must count 1, not 2
        gates = {"verdict": "blocked", "results": [
            {"gate": "env.step_isolation", "status": "fail", "blockers": [{"message": "x.md is readable too early"}]}]}
        self.assertEqual(len(_gate_findings(gates)), 1)

    def test_an_unverified_gate_reports_its_error(self):
        gates = {"verdict": "unverified", "results": [
            {"gate": "grader.contract_probe", "status": "error", "blockers": [], "error": "TimeoutError: probe"}]}
        self.assertEqual(_gate_findings(gates), ["grader.contract_probe: could not verify: TimeoutError: probe"])

    def test_no_reason_anywhere_falls_back_to_the_verdict(self):
        self.assertEqual(_gate_findings({"verdict": "blocked", "results": []}), ["gate chain is blocked"])


class RebuildLedgerNamesTheRevision(unittest.TestCase):
    def bundle(self, root: Path, *parts: str) -> Path:
        b = root.joinpath(*parts)
        (b / "authoring").mkdir(parents=True)
        (b / "authoring/spec.json").write_text(json.dumps({"source": {"session_id": "s", "seed_index": 0}}))
        (b / "task.toml").write_text('[task]\nname = "arena/' + b.name + '"\nversion = "1.0.0"\n\n[[steps]]\nname = "01-task"\n')
        return b

    def rebuild(self, bundle: Path) -> dict:
        with mock.patch("pipeline.ledger.faithfulness.build", return_value={"measured": 1}), \
             mock.patch("pipeline.ledger.faithfulness.with_level",
                        side_effect=lambda b, ledger: {**ledger, "faithfulness_level": "F2"}):
            return repair.rebuild_ledger(bundle, {"category": "F2", "category_inputs": {"x": 1}})

    def test_a_hardened_revision_keeps_its_originals_name_and_gets_a_level(self):
        with tempfile.TemporaryDirectory() as tmp:
            rev = self.bundle(Path(tmp), "a-055-publishing-qa", "hardened", "v4")
            ledger = self.rebuild(rev)
            self.assertEqual(ledger["faithfulness_level"], "F2")
            self.assertEqual(ledger["category"], "F2")
            text = (rev / "task.toml").read_text()
            self.assertIn('name = "arena/a_f2_publishing-qa"', text)
            self.assertIn('name = "01-task"', text)          # step names untouched
            self.assertEqual(json.loads((rev / "provenance/ledger.json").read_text())["faithfulness_level"], "F2")

    def test_an_original_bundle_is_named_after_itself(self):
        with tempfile.TemporaryDirectory() as tmp:
            b = self.bundle(Path(tmp), "a-001-technical-documentation-qa")
            self.rebuild(b)
            self.assertIn('name = "arena/a_f2_technical-documentation-qa"', (b / "task.toml").read_text())


if __name__ == "__main__":
    unittest.main()
