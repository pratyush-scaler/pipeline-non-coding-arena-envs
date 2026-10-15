"""Reproduce the record guardrail bypass and accidental stale-package launch."""
import json
import shutil
import tempfile
import threading
from types import SimpleNamespace
import unittest
from pathlib import Path
from unittest.mock import patch

from pipeline.artifacts import freeze
from pipeline.author.build import build
from pipeline.author.quality import production_problems
from pipeline.benchmark.harbor import run_campaign
from pipeline.benchmark.preflight import validate_task
from pipeline.row_controls import run as row_controls
from pipeline.tests.test_production import synthetic_bundle


class ReadinessRepairs(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name).resolve()
        self.bundle = synthetic_bundle(self.root)

    def records(self, assertion="multiset_equals"):
        spec = json.loads((self.bundle / "authoring/spec.json").read_text())
        schema = spec["outputs"][0]["schema"]
        schema["properties"]["records"] = {"type": "array", "items": {
            "type": "object", "properties": {"id": {"type": "string"}, "effort": {"type": "integer"}},
            "required": ["id", "effort"], "additionalProperties": False}}
        schema["required"].append("records")
        spec["solution"]["summary.json"]["records"] = [{"id": "R-21", "effort": 3}, {"id": "R-23", "effort": 5}]
        spec["checks"].append({"id": "preserved_records", "kind": "guardrail", "weight": 0,
            "assertion": assertion, "basis": "Preserve the ID and effort of every open ticket, in any order.",
            "actual": {"op": "field", "file": "summary.json", "path": "records"},
            "target": {"op": "select", "of": {"op": "rows", "file": "tickets.jsonl",
                "where": {"field": "status", "eq": "open"}}, "fields": {"id": "ticket", "effort": "effort"}}})
        build(spec, self.bundle)
        return spec

    def probe(self, spec):
        checks = {c["id"]: c for c in json.loads((self.bundle / "tests/checks.json").read_text())["checks"]}
        return row_controls(self.bundle, spec, spec["solution"], checks, self.root / "probes")

    def test_automatic_probes_catch_duplicate_acceptance_without_authored_cases(self):
        report = self.probe(self.records("set_equals"))
        self.assertTrue(any("append-duplicate" in e for e in report["errors"]))

    def test_swapped_cells_trigger_zero_and_whole_row_reordering_keeps_full_credit(self):
        report = self.probe(self.records())
        self.assertEqual(report["errors"], [])
        for key in ("exchange-id", "exchange-effort", "replace-with-duplicate", "drop-row"):
            result = report["results"]["preserved_records/" + key]
            self.assertEqual(result["contract_errors"], [])
            self.assertEqual(result["reward"], 0)
            self.assertIn("preserved_records", result["guardrails_violated"])
        self.assertEqual(report["results"]["preserved_records/allowed-row-reordering"]["reward"], 1)

    def test_column_guard_cannot_claim_record_preservation(self):
        spec = self.records()
        check = spec["checks"][-1]
        check["actual"]["path"] = "records[].effort"
        check["target"] = {"op": "pluck", "of": check["target"]["of"], "field": "effort"}
        check["assertion"] = "set_equals"
        issues = production_problems(spec, self.bundle)
        self.assertTrue(any("preserved_records: column-only" in e for e in issues))

    def test_unordered_preservation_does_not_override_a_separate_ordering_requirement(self):
        spec = self.records()
        import copy
        ordered = copy.deepcopy(spec["checks"][-1])
        ordered.update(id="records_in_source_order", kind="objective", weight=1, assertion="equals")
        spec["checks"].append(ordered)
        build(spec, self.bundle)
        report = self.probe(spec)
        self.assertEqual(report["errors"], [])
        self.assertNotIn("preserved_records/allowed-row-reordering", report["results"])

    def test_current_export_and_renamed_snapshot_pass_preflight(self):
        receipt = validate_task(self.bundle)
        self.assertTrue(receipt["current_generator_verified"])
        self.assertFalse(receipt["release_qualified"])
        snapshot = self.root / "arbitrary-storage-name"
        freeze(self.bundle, snapshot)
        self.assertEqual(validate_task(snapshot)["artifact_sha256"], receipt["artifact_sha256"])

    def test_stale_grader_rejected_before_runtime_or_output_creation(self):
        (self.bundle / "tests/_arena_runtime/checks_runtime.py").write_text("# stale evaluator\n")
        output = self.root / "must-not-launch"
        with patch("pipeline.benchmark.harbor.doctor") as doctor:
            with self.assertRaisesRegex(ValueError, "current generator"):
                run_campaign(self.bundle, output, agent="nop", dry_run=True)
            doctor.assert_not_called()
        self.assertFalse(output.exists())

    def test_legacy_requires_explicit_opt_in_and_is_labelled(self):
        (self.bundle / "authoring/spec.json").unlink()
        with self.assertRaisesRegex(ValueError, "legacy"):
            validate_task(self.bundle)
        report = run_campaign(self.bundle, self.root / "legacy-plan", agent="nop",
                              legacy_diagnostic=True, dry_run=True)
        self.assertEqual(report["task_validation"]["mode"], "legacy-diagnostic")
        self.assertFalse(report["task_validation"]["release_qualified"])

    def test_cli_dry_run_needs_neither_provider_credentials_nor_docker(self):
        import contextlib
        import io
        from pipeline.cli import build_parser, cmd_benchmark
        # Built through the REAL parser, not a hand-rolled namespace: a stub
        # goes stale the moment a subcommand grows a flag, and the command then
        # raises AttributeError in production while the test still passes.
        args = build_parser().parse_args([
            "benchmark", str(self.bundle), "--dry-run", "--agent", "nop",
            "--out", str(self.root / "offline-plan"),
            "--rollouts", "1", "--workers", "1", "--effort", "xhigh", "--no-limits"])
        with patch("pipeline.cli.load_keys") as keys, patch("pipeline.benchmark.harbor.doctor") as doctor, \
             contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(cmd_benchmark(args), 0)
        keys.assert_not_called()
        doctor.assert_not_called()
        report = json.loads((self.root / "offline-plan/report.json").read_text())
        self.assertEqual(report["status"], "planned")
        self.assertFalse(report["task_validation"]["release_qualified"])

    def test_pre_cancelled_campaign_does_no_preflight_work(self):
        stop = threading.Event()
        stop.set()
        with patch("pipeline.benchmark.harbor.inspect_package") as inspect:
            report = run_campaign(self.root / "missing", self.root / "not-created", agent="nop", stop_event=stop)
            inspect.assert_not_called()
        self.assertTrue(report["cancelled"])
        self.assertFalse((self.root / "not-created").exists())

    def test_native_snapshot_excludes_mutable_review_evidence(self):
        from pipeline.artifacts import inventory
        from pipeline.benchmark.harbor import file_modes
        from pipeline.benchmark.support import fingerprint
        before = fingerprint(self.bundle, task_only=True)
        modes = file_modes(self.bundle)
        evidence = self.bundle / "verification/reviews/attempt"
        evidence.mkdir(parents=True)
        (evidence / "review.json").write_text('{"verdict":"revise"}')
        (evidence / "docker-compose.yaml").write_text("services: {}\n")
        (evidence / "review.json").chmod(0o600)
        self.assertEqual(fingerprint(self.bundle, task_only=True), before)
        self.assertEqual(file_modes(self.bundle), modes)
        output = self.root / "with-review-evidence"
        report = run_campaign(self.bundle, output, agent="nop", dry_run=True)
        self.assertEqual(report["status"], "planned")
        self.assertFalse((output / "package/verification").exists())
        self.assertEqual(inventory(output / "package"), inventory(self.bundle))

    def test_native_task_hashes_still_detect_bytes_permissions_and_symlinks(self):
        from pipeline.benchmark.harbor import file_modes, inspect_package
        from pipeline.benchmark.support import fingerprint
        before = fingerprint(self.bundle, task_only=True)
        modes = file_modes(self.bundle)
        fixture = self.bundle / "environment/files/tickets.csv"
        fixture.write_text(fixture.read_text() + "R-99,open,100\n")
        self.assertNotEqual(fingerprint(self.bundle, task_only=True), before)
        fixture.chmod(0o600)
        self.assertNotEqual(file_modes(self.bundle), modes)
        link = self.bundle / "environment/files/alias.csv"
        link.symlink_to(fixture)
        with self.assertRaisesRegex(ValueError, "Symlinks"):
            inspect_package(self.bundle)

    def test_native_compose_override_rejection_still_covers_task_surfaces(self):
        from pipeline.benchmark.harbor import inspect_package
        for relative in ("docker-compose.yaml", "environment/docker-compose.yml",
                         "tests/docker-compose.yaml", "environment/files-other/docker-compose.yml"):
            path = self.bundle / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("services: {}\n")
            with self.subTest(relative=relative), self.assertRaisesRegex(ValueError, "Compose overrides"):
                inspect_package(self.bundle)
            path.unlink()

    def test_native_compose_source_documents_remain_inert_and_preserved(self):
        from pipeline.benchmark.harbor import inspect_package
        from pipeline.benchmark.support import fingerprint
        before = fingerprint(self.bundle, task_only=True)
        relative = "environment/files/recovered-project/docker-compose.yml"
        fixture = self.bundle / relative
        fixture.parent.mkdir(parents=True)
        fixture.write_text("services:\n  source_example:\n    network_mode: host\n")
        build(json.loads((self.bundle / "authoring/spec.json").read_text()), self.bundle)
        inspect_package(self.bundle)
        self.assertNotEqual(fingerprint(self.bundle, task_only=True), before)
        output = self.root / "with-compose-source"
        report = run_campaign(self.bundle, output, agent="nop", dry_run=True)
        self.assertEqual(report["status"], "planned")
        self.assertEqual((output / "package" / relative).read_bytes(), fixture.read_bytes())
        override = self.bundle / "environment/docker-compose.yaml"
        override.symlink_to(fixture)
        with self.assertRaisesRegex(ValueError, "Symlinks"):
            inspect_package(self.bundle)

    def test_build_rejects_a_reproducible_but_exploitable_grader_before_calibration(self):
        from pipeline import orchestrate
        spec = self.records("set_equals")
        def fixture(_extraction, bundle):
            shutil.copytree(self.bundle / "environment/files", bundle / "environment/files")
        with patch.object(orchestrate.extract_stage, "extract", return_value=SimpleNamespace(moments=[])), \
             patch.object(orchestrate.extract_stage, "write", side_effect=fixture), \
             patch.object(orchestrate.faithfulness, "build", return_value={"faithfulness_by_bytes": 1}), \
             patch.object(orchestrate, "run_bundle", return_value={"verdict": "green", "results": []}), \
             patch.object(orchestrate, "GATE_REPAIRS", 0), \
             patch("pipeline.calibrate.run.campaign") as campaign:
            result = orchestrate.build_one({"session_id": "synthetic", "seed_index": 0,
                "classification": {"domain": "records"}}, 1, self.root / "factory",
                lambda *_args, **_kwargs: spec, orchestrate.Budget(1))
        self.assertEqual(result.status, "blocked", result.error)
        campaign.assert_not_called()
        report = json.loads((self.root / "factory/a-001-records/verification/controls.json").read_text())
        self.assertTrue(any("append-duplicate" in e for e in report["independent_row_controls"]["errors"]))

    def test_critic_sees_real_build_context_and_layout_citations_bind_to_candidate(self):
        import hashlib
        import os
        from pipeline.artifacts import atomic_json
        from pipeline.ledger.faithfulness import build as ledger
        from pipeline.review import review, review_problems
        spec = json.loads((self.bundle / "authoring/spec.json").read_text())
        spec["_producer"] = {"model": "author"}
        build(spec, self.bundle)
        session = spec["source"]["session_id"]
        trace = {"session_id": session, "messages": [{"role": "assistant", "content": [
            {"type": "tool-write_file", "input": {"path": p.name, "content": p.read_text()}}
            for p in (self.bundle / "environment/files").iterdir()]}]}
        atomic_json(self.root / "dump/sessions" / session / "data.json", {"traces": [trace]})
        self.enterContext(patch.dict(os.environ, ARENA_DUMP=str(self.root / "dump")))
        atomic_json(self.bundle / "provenance/ledger.json", ledger(self.bundle, session, 0))
        def critic(_prompt, public, work, model, _tag, max_steps):
            self.assertEqual((public / "package-layout/files/tickets.csv").read_bytes(),
                             (public / "fixture/tickets.csv").read_bytes())
            receipt = json.loads((public / "source-provenance.json").read_text())
            self.assertTrue(all(f["origin"] == "lifted" for f in receipt["files"]))
            self.assertFalse((public / "package-layout/files/source-provenance.json").exists())
            shutil.copytree(public, work / "workspace")
            (work / "deliverables").mkdir()
            (work / "conversation.json").write_text("[]")
            (work / "request-config.json").write_text(json.dumps({"model": model, "max_steps": max_steps}))
            doc = {"verdict": "pass", "checks": [{"id": c["id"], "verdict": "pass",
                "reason": "The published source supports the specific criterion and its output semantics.",
                "citations": [{"file": "fixture/tickets.csv", "quote": "ticket,status,effort\nR-21,open,3"},
                              {"file": "package-layout/Dockerfile", "quote": "COPY files/ /app/environment/files/"},
                              {"file": "source-provenance.json", "quote": '"origin": "lifted"'}]} for c in spec["checks"]],
                "ambiguities": [], "substantive_gaps": [], "shortcut_risks": [], "privacy_findings": [],
                "difficulty_assessment": "Synthetic fixture for exercising review evidence, not empirical difficulty assurance.",
                "novelty_assessment": "Synthetic fixture for exercising the supplied comparison context and review bindings.",
                "untested_surfaces": ["No empirical model calibration in this unit test."]}
            from pipeline.tests.test_solver_brief import synthetic_autonomy_assessment
            doc["solver_autonomy"] = synthetic_autonomy_assessment(public)
            (work / "deliverables/review.json").write_text(json.dumps(doc))
            return SimpleNamespace(error=None, stop_reason="completed", tool_calls=1), None
        with patch("pipeline.calibrate.run._rollout_for", return_value=critic), \
             patch("pipeline.corpus.review_context", return_value={"peers": [], "peers_considered": 0}):
            report = review(self.bundle, "critic")
            self.assertEqual(report["errors"], [])
            work = self.bundle / report["work_dir"]
            rel = "workspace/package-layout/files/tickets.csv"
            original = (work / rel).read_bytes()
            (work / rel).write_text("A different fixture supplied only to the critic")
            report["artifacts"][rel] = hashlib.sha256((work / rel).read_bytes()).hexdigest()
            self.assertIn("reviewer inputs differ from the released task", review_problems(self.bundle, report))
            (work / rel).write_bytes(original)
            report["artifacts"][rel] = hashlib.sha256(original).hexdigest()
            rel = "workspace/source-provenance.json"
            path = work / rel
            changed = json.loads(path.read_text())
            changed["files"][0]["origin"] = "authored"
            atomic_json(path, changed)
            report["artifacts"][rel] = hashlib.sha256(path.read_bytes()).hexdigest()
            self.assertIn("reviewer provenance differs from the verified source ledger",
                          review_problems(self.bundle, report))
            path.unlink()
            report["artifacts"].pop(rel)
            self.assertIn("reviewer provenance differs from the verified source ledger",
                          review_problems(self.bundle, report))


if __name__ == "__main__":
    unittest.main()
