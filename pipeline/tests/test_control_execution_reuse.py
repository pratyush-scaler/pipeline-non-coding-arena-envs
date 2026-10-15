from copy import deepcopy
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from pipeline import assurance
from pipeline.artifacts import atomic_json, identity, policy_identity
from pipeline.gates import findings
from pipeline.gates.base import GateContext
from pipeline.tests.test_production import synthetic_bundle


class FreshControlProofTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.bundle = synthetic_bundle(Path(temporary.name))
        self.report = {"schema": "arena-pipeline/controls/1", "artifact_sha256": identity(self.bundle),
                       "ok": True, "errors": []}
        context = GateContext(task_dir=self.bundle, repo_root=self.bundle.parent)
        with patch.object(assurance, "controls", return_value=self.report):
            issues, evidence = findings._controls(context)
        self.assertEqual(issues, [])
        self.gates = {"schema": "arena-pipeline/gate-report/1", "verdict": "green", "results": [{
            "gate": "quality.controls", "status": "pass", "blockers": [], "error": None,
            "evidence": evidence}]}

    def test_just_executed_unchanged_gate_avoids_a_duplicate_suite(self):
        with patch.object(assurance, "controls") as rerun:
            self.assertEqual(assurance.control_problems_after_gates(self.bundle, self.gates), [])
        rerun.assert_not_called()
        self.assertEqual(self.gates["results"][0]["evidence"]["policy_sha256"], policy_identity())

    def test_changed_artifact_requires_fresh_execution(self):
        (self.bundle / "environment/files/new-evidence.txt").write_text("An actual source revision.")
        with patch.object(assurance, "controls", return_value=self.report) as rerun:
            assurance.control_problems_after_gates(self.bundle, self.gates)
        rerun.assert_called_once_with(self.bundle)

    def test_changed_implementation_requires_fresh_execution(self):
        self.gates["results"][0]["evidence"]["policy_sha256"] = "old implementation"
        with patch.object(assurance, "controls", return_value=self.report) as rerun:
            assurance.control_problems_after_gates(self.bundle, self.gates)
        rerun.assert_called_once_with(self.bundle)

    def test_stored_receipts_alone_cannot_skip_the_suite(self):
        atomic_json(self.bundle / "verification/controls.json", self.report)
        with patch.object(assurance, "controls", return_value=self.report) as rerun:
            assurance.control_problems_after_gates(self.bundle, {})
        rerun.assert_called_once_with(self.bundle)

    def test_missing_failed_skipped_and_duplicated_gate_proofs_rerun(self):
        reports = [deepcopy(self.gates) for unused in range(7)]
        reports[0]["results"][0]["status"] = "skipped"
        reports[1]["results"][0]["evidence"].pop("artifact_sha256")
        reports[2]["results"][0]["evidence"]["errors"] = 1
        reports[3]["results"].append(deepcopy(reports[3]["results"][0]))
        reports[4]["verdict"] = "blocked"
        reports[5]["results"][0]["blockers"] = [{"code": "control-failed"}]
        reports[6]["results"][0]["error"] = "execution failed"
        for gates in reports:
            with self.subTest(gates=gates), patch.object(assurance, "controls", return_value=self.report) as rerun:
                assurance.control_problems_after_gates(self.bundle, gates)
                rerun.assert_called_once_with(self.bundle)

    def test_failed_fresh_execution_without_findings_is_not_a_pass(self):
        with patch.object(assurance, "controls", return_value={"ok": False, "errors": []}):
            self.assertTrue(assurance.control_problems_after_gates(self.bundle, {}))

    def test_fresh_findings_remain_actionable(self):
        with patch.object(assurance, "controls", return_value={"ok": False, "errors": ["unsupported causal case"]}):
            self.assertEqual(assurance.control_problems_after_gates(self.bundle, {}), ["unsupported causal case"])


if __name__ == "__main__":
    unittest.main()
