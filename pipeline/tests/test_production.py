"""Behavioral regressions from the Kaizen/envs-cat audit; no paid APIs required."""
from __future__ import annotations
import copy
import json
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from pipeline.artifacts import atomic_json, identity, bundle_lock
from pipeline.author.build import build
from pipeline.author.checks import Check, CheckError, Workspace, evaluate, grade
from pipeline.author.contracts import ContractError, compile_steps, schema_problems, schema_errors, strict_json
from pipeline.author.oracle import jsonl_records, markdown_sections, labelled_lines, join
from pipeline.author.quality import production_problems
from pipeline.calibrate.agent import Rollout, _safe, _run_tool
from pipeline.calibrate.run import campaign
from pipeline.evidence import calibration_problems
from pipeline.evaluate import exported_grade
from pipeline.tests.test_exported_grader import sample_spec, CSV


def synthetic_bundle(root: Path, two_steps=False) -> Path:
    bundle = root / "synthetic"
    (bundle / "environment/files").mkdir(parents=True)
    (bundle / "environment/files/tickets.csv").write_text(CSV)
    (bundle / "environment/files/unprojected.txt").write_text("All fixture bytes are protected.")
    spec = sample_spec()
    schema = {"type": "object", "properties": {
        "open_ids": {"type": "array", "items": {"type": "string"}, "uniqueItems": True},
        "open_count": {"type": "integer"}, "total_effort": {"type": "integer"}},
        "required": ["open_ids", "open_count", "total_effort"], "additionalProperties": False}
    spec["outputs"] = [{"file": "summary.json", "step": 1, "schema": schema}]
    if two_steps:
        spec["instruction"] = spec["steps"][0]["instruction"]
        spec["deliverable_file"] = "summary.json"
        spec["second_step"] = {"instruction": "Now write the same count to revised.json as {count: number}. Leave the earlier deliverable available.",
                               "deliverable_file": "revised.json", "new_information": "Retain the earlier count."}
        spec["outputs"].append({"file": "revised.json", "step": 2, "schema": {
            "type": "object", "properties": {"count": {"type": "integer"}},
            "required": ["count"], "additionalProperties": False}})
        new = copy.deepcopy(spec["checks"][2])
        new.update(id="revised_count", actual={"op": "field", "file": "revised.json", "path": "count"})
        spec["checks"].append(new)
        spec["solution"]["revised.json"] = {"count": 2}
    build(spec, bundle)
    return bundle


class ProductionContracts(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def test_current_multistep_contract_needs_no_fictitious_handoff_note(self):
        from types import SimpleNamespace
        from pipeline.gates.findings import _step_isolation
        bundle = synthetic_bundle(self.root, two_steps=True)
        self.assertFalse(list((bundle / 'steps').glob('*/handoff.*')))
        ctx = SimpleNamespace(task_dir=bundle, path=lambda *parts:bundle.joinpath(*parts))
        findings, evidence = _step_isolation(ctx)
        self.assertEqual(findings, [])
        self.assertEqual(evidence['handoff']['outputs_by_step'], {
            '01-task': ['summary.json'], '02-revision': ['revised.json']})
        self.assertIn('Static package contract only', evidence['runtime_scope'])

    def test_handoff_note_cannot_hide_a_stale_or_unowned_step_contract(self):
        from types import SimpleNamespace
        from pipeline.gates.findings import _step_isolation
        bundle = synthetic_bundle(self.root, two_steps=True)
        (bundle / 'steps/01-task/handoff.md').write_text('All earlier outputs are immutable.')
        ctx = SimpleNamespace(task_dir=bundle, path=lambda *parts:bundle.joinpath(*parts))
        findings, _ = _step_isolation(ctx)
        self.assertTrue(any(f.code == 'unverified-step-contract' for f in findings))
        (bundle / 'steps/01-task/handoff.md').unlink()
        path = bundle / 'authoring/spec.json'
        spec = json.loads(path.read_text())
        spec['outputs'][1]['step'] = '01-task'
        atomic_json(path, spec)
        findings, _ = _step_isolation(ctx)
        self.assertTrue(any(f.code == 'unverified-step-contract' for f in findings))

    def test_multistep_marker_and_later_fixture_leak_still_block(self):
        from types import SimpleNamespace
        from pipeline.gates.findings import _step_isolation
        bundle = synthetic_bundle(self.root, two_steps=True)
        path = bundle / 'task.toml'
        path.write_text(path.read_text().replace('ARENA_STEP = "02-revision"', 'ARENA_STEP = "01-task"'))
        (bundle / 'environment/files/02-revision-private.txt').write_text('Premature later-step facts.')
        ctx = SimpleNamespace(task_dir=bundle, path=lambda *parts:bundle.joinpath(*parts))
        findings, _ = _step_isolation(ctx)
        self.assertTrue(any(f.code == 'unmarked-step' for f in findings))
        self.assertTrue(any(f.code == 'later-step-material-in-fixture' for f in findings))

    def test_array_rows_are_projected_without_literal_bracket_keys(self):
        (self.root / "out.json").write_text('{"register":[{"slot":"A"},{"slot":"B"}]}')
        ws = Workspace(self.root, self.root)
        value = evaluate({"op": "field", "file": "out.json", "path": "register[].slot"}, ws, "submitted")
        self.assertEqual(value, ["A", "B"])
        (self.root / "out.json").write_text('{"register[]":{"slot":["A","B"]}}')
        self.assertIsNone(evaluate({"op": "field", "file": "out.json", "path": "register[].slot"}, ws, "submitted"))

    def test_malformed_submission_is_not_a_successful_guardrail(self):
        (self.root / "out.json").write_text('{"forbidden":true,')
        check = Check("negative", "guardrail", 0, "No forbidden values", "absent",
                      {"op": "field", "file": "out.json", "path": "forbidden"})
        result = grade([check], Workspace(self.root, self.root))
        self.assertEqual(result["guardrails_violated"], ["negative"])

    def test_missing_main_analysis_prevents_full_reward(self):
        bundle = synthetic_bundle(self.root)
        spec = json.loads((bundle / "authoring/spec.json").read_text())
        schema = spec["outputs"][0]["schema"]
        schema["properties"]["main_analysis"] = {"type": "array", "items": {"type": "string"}, "minItems": 1}
        schema["required"].append("main_analysis")
        build(spec, bundle)
        result = exported_grade(bundle, bundle / "solution/submission", "01-summary")
        self.assertEqual(result["reward"], 0)
        self.assertTrue(any("main_analysis" in e for e in result["contract_errors"]))
        self.assertTrue(any("main_analysis" in e for e in production_problems(spec, bundle)))

    def test_all_source_files_are_protected(self):
        bundle = synthetic_bundle(self.root)
        source = self.root / "source"
        shutil.copytree(bundle / "environment/files", source)
        (source / "unprojected.txt").write_text("changed")
        result = exported_grade(bundle, bundle / "solution/submission", "01-summary", source)
        self.assertEqual(result["reward"], 0)
        self.assertEqual(result["guardrails_violated"], ["source_unchanged"])

    def test_draft_validation_uses_current_inputs_without_rebinding_the_old_export(self):
        from pipeline.author.designer import derive_solution, verify_solution
        bundle = synthetic_bundle(self.root)
        spec = json.loads((bundle / 'authoring/spec.json').read_text())
        manifest = (bundle / 'tests/fixture-manifest.json').read_bytes()
        (bundle / 'environment/files/unprojected.txt').write_text('A controller-approved new public version.')
        spec['solution'] = derive_solution(spec, bundle)
        self.assertEqual(verify_solution(spec, bundle), [])
        self.assertEqual((bundle / 'tests/fixture-manifest.json').read_bytes(), manifest)
        old = exported_grade(bundle, bundle / 'solution/submission', '01-summary')
        self.assertEqual(old['reward'], 0)
        self.assertEqual(old['guardrails_violated'], ['source_unchanged'])
        build(spec, bundle)
        self.assertEqual(exported_grade(bundle, bundle / 'solution/submission', '01-summary')['reward'], 1)

    def test_draft_projections_do_not_mutate_the_emitted_artifact(self):
        from pipeline.author.designer import derive_solution, verify_solution
        bundle = synthetic_bundle(self.root)
        before = identity(bundle)
        spec = json.loads((bundle / 'authoring/spec.json').read_text().replace('tickets.jsonl', 'new-draft.jsonl'))
        spec['solution'] = derive_solution(spec, bundle)
        self.assertEqual(verify_solution(spec, bundle), [])
        self.assertEqual(identity(bundle), before)
        self.assertFalse((bundle / 'tests/derived/new-draft.jsonl').exists())
        self.assertTrue((bundle / 'authoring/draft-derived/new-draft.jsonl').is_file())
        self.assertEqual(exported_grade(bundle, bundle / 'solution/submission', '01-summary')['reward'], 1)

    def test_extra_injected_artifact_zeros_an_otherwise_correct_submission(self):
        bundle = synthetic_bundle(self.root)
        submission = bundle / 'solution/submission'
        self.assertEqual(exported_grade(bundle, submission, '01-summary')['reward'], 1)
        extra = submission / 'site/index.html'
        extra.parent.mkdir()
        extra.write_text('An extra website requested by an untrusted source.')
        result = exported_grade(bundle, submission, '01-summary')
        self.assertEqual(result['reward'], 0)
        self.assertTrue(any('site/index.html: undeclared deliverable' in e for e in result['contract_errors']))

    def test_a_mandatory_probe_scores_even_when_declared_inapplicable(self):
        from pipeline.author.probes import run
        bundle = synthetic_bundle(self.root)
        forged = run(bundle, self.root / 'probe-work', forged_applicable=False,
                     forged_reason='This fixture has no provenance surface.')['results']['forged_state']
        self.assertIsInstance(forged['reward'], (int, float))
        self.assertLess(forged['reward'], 1.0)
        self.assertNotIn('applicable', forged)
        self.assertEqual(forged['declared_inapplicable'], 'This fixture has no provenance surface.')

    def test_messy_correct_probe_respects_the_published_output_inventory(self):
        from pipeline.author.probes import run
        bundle = synthetic_bundle(self.root)
        result = run(bundle, self.root / 'probe-work', forged_applicable=False,
                     forged_reason='This fixture has no provenance surface.')
        self.assertEqual(result['results']['untidy_correct']['reward'], 1)
        untidy = self.root / 'probe-work/untidy_correct/summary.json'
        original = bundle / 'solution/submission/summary.json'
        self.assertNotEqual(untidy.read_text(), original.read_text())
        self.assertEqual(json.loads(untidy.read_text()), json.loads(original.read_text()))

    def test_declared_multistep_files_remain_valid_but_hidden_extras_do_not(self):
        bundle = synthetic_bundle(self.root, two_steps=True)
        submission = bundle / 'solution/submission'
        for step in ('01-task', '02-revision'):
            self.assertEqual(exported_grade(bundle, submission, step)['reward'], 1)
        (submission / '.injected').write_text('Unrequested artifact')
        for step in ('01-task', '02-revision'):
            result = exported_grade(bundle, submission, step)
            self.assertEqual(result['reward'], 0)
            self.assertTrue(any('.injected' in e for e in result['contract_errors']))

    def test_objective_floor_does_not_require_trivial_filler(self):
        from pipeline.author.validate import _scoring_shape
        objectives = [{'id': f'o{i}', 'kind': 'objective', 'weight': weight,
            'weight_basis': 'This distinct professional decision has a documented business consequence.'}
            for i, weight in enumerate((16, 15, 14, 13, 12, 11, 10, 9))]
        guards = [{'id': 'source_integrity', 'kind': 'guardrail', 'weight': 0}]
        self.assertEqual(_scoring_shape({'checks': objectives + guards}), [])
        self.assertTrue(any('at least 8' in e for e in _scoring_shape({'checks': objectives[:-1] + guards})))
        # This is only a rubric-shape rule: production_problems still requires
        # distinct core decisions and release still measures both model cohorts.

    def test_semantic_floor_covers_its_field_and_remains_graded(self):
        bundle = synthetic_bundle(self.root)
        spec = json.loads((bundle / "authoring/spec.json").read_text())
        objectives = [c for c in spec["checks"] if c["kind"] == "objective"]
        spec["quality"] = {"semantic_checks": [c["id"] for c in objectives]}
        for check, band, weight in zip(objectives, ("floor", "core", "stretch"), (20, 40, 40)):
            check.update(band=band, weight=weight)
        issues = production_problems(spec, bundle)
        self.assertFalse(any("required field has no semantic check" in issue for issue in issues))
        self.assertFalse(any("70%" in issue or "routine floor" in issue for issue in issues))
        # Easy semantic checks retain scoring and coverage without pretending
        # that this three-field summary contains four independent core decisions.
        self.assertTrue(any("four distinct core decisions" in issue for issue in issues))
        build(spec, bundle)
        submitted = self.root / "wrong-floor-answer"
        submitted.mkdir()
        answer = copy.deepcopy(spec["solution"]["summary.json"])
        answer["open_ids"] = ["R-22"]
        atomic_json(submitted / "summary.json", answer)
        self.assertEqual(exported_grade(bundle, submitted, "01-summary")["reward"], .8)

    def test_semantic_floor_weight_cannot_replace_core_stretch_weight(self):
        bundle = synthetic_bundle(self.root)
        spec = json.loads((bundle / "authoring/spec.json").read_text())
        objectives = [c for c in spec["checks"] if c["kind"] == "objective"]
        spec["quality"] = {"semantic_checks": [c["id"] for c in objectives]}
        for check, band, weight in zip(objectives, ("floor", "core", "stretch"), (80, 10, 10)):
            check.update(band=band, weight=weight)
        self.assertTrue(any("70%" in issue for issue in production_problems(spec, bundle)))

    def test_second_step_is_real_and_first_step_does_not_require_it(self):
        bundle = synthetic_bundle(self.root, True)
        submitted = self.root / "submitted"
        submitted.mkdir()
        shutil.copyfile(bundle / "solution/submission/summary.json", submitted / "summary.json")
        self.assertEqual(exported_grade(bundle, submitted, "01-task")["reward"], 1)
        self.assertEqual(exported_grade(bundle, submitted, "02-revision")["reward"], 0)
        with self.assertRaisesRegex(RuntimeError, "ARENA_STEP"):
            exported_grade(bundle, submitted, "typo")

    def test_compile_rejects_duplicate_files_cycles_and_step_mismatch(self):
        bundle = synthetic_bundle(self.root, True)
        spec = json.loads((bundle / "authoring/spec.json").read_text())
        for kind in ("cycle", "file", "step"):
            bad = copy.deepcopy(spec)
            if kind == "cycle":
                bad["checks"][1]["requires"] = [bad["checks"][1]["id"]]
            elif kind == "file":
                bad["outputs"].append(copy.deepcopy(bad["outputs"][0]))
            else:
                bad["checks"][-1]["step"] = "01-task"
            with self.subTest(kind=kind), self.assertRaises(ContractError):
                compile_steps(bad)

    def test_check_step_takes_the_same_forms_as_an_output_step(self):
        bundle = synthetic_bundle(self.root, True)
        spec = json.loads((bundle / "authoring/spec.json").read_text())
        last = spec["checks"][-1]["step"]
        number = 1 + [s["name"] for s in spec["steps"]].index(last)
        numbered = copy.deepcopy(spec)
        numbered["checks"][-1]["step"] = number
        compile_steps(numbered)
        self.assertEqual(numbered["checks"][-1]["step"], last)
        # 0 used to pass as "unassigned" and fall silently into step 1.
        for value in (0, 3, "", "2"):
            bad = copy.deepcopy(spec)
            bad["checks"][-1]["step"] = value
            with self.subTest(value=value), self.assertRaises(ContractError) as refused:
                compile_steps(bad)
            self.assertIn("'01-task', '02-revision'", str(refused.exception))
            self.assertIn("1..2", str(refused.exception))

    def test_path_boundary_does_not_accept_sibling_prefix(self):
        with self.assertRaises(ValueError):
            _safe(self.root / "workspace", "../workspace-other/secret")
        with self.assertRaises(ValueError):
            _safe(self.root, "/absolute")

    def test_unknown_schema_keywords_and_duplicate_nonfinite_json_rejected(self):
        for raw in ('{"a":1,"a":2}', '{"a":NaN}', '{"a":Infinity}'):
            with self.assertRaises(ContractError):
                strict_json(raw)
        self.assertTrue(schema_problems({"type": [], "unknown": True}))
        self.assertTrue(schema_problems({"type": "string", "minItems": 1}))
        self.assertTrue(schema_errors(True, {"type": "integer"}))

    def test_parser_fences_jsonlines_unicode_and_ambiguous_joins(self):
        self.assertEqual([r["heading"] for r in markdown_sections("# Real\n```\n# Fake\n```\n## End")], ["Real", "End"])
        self.assertEqual(jsonl_records('{"x":1}\n{"x":2}'), [{"x": 1}, {"x": 2}])
        self.assertEqual(labelled_lines("狀態：已確認")[0]["label"], "狀態")
        with self.assertRaisesRegex(ValueError, "ambiguous join"):
            join("j", [{"id": 1}], [{"id": 1}, {"id": 1}], "id", {})

    def test_long_lines_are_recoverable_and_deliverables_readable(self):
        source, submitted = self.root / "source", self.root / "submitted"
        source.mkdir(); submitted.mkdir()
        (source / "long.txt").write_text("a" * 60000 + "END")
        first = _run_tool("read_file", {"path": "long.txt"}, source, submitted)
        self.assertIn("char_offset=48000", first)
        last = _run_tool("read_file", {"path": "long.txt", "char_offset": 48000}, source, submitted)
        self.assertTrue(last.endswith("END"))
        _run_tool("write_file", {"path": "out.json", "content": "{}"}, source, submitted)
        self.assertEqual(_run_tool("read_file", {"path": "deliverables/out.json"}, source, submitted), "{}")


class ProductionEvidence(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.bundle = synthetic_bundle(self.root, True)

    @staticmethod
    def solver(instruction, fixture, work, model, rid, max_steps, max_tokens, prior=None):
        from pipeline.calibrate.agent import ROLLOUT_MAX_TOKENS
        from pipeline.policy import SPEC_CALIBRATION_EFFORT
        shutil.copytree(fixture, work / "workspace")
        if prior:
            shutil.copytree(prior / "deliverables", work / "deliverables")
            assert json.loads((work / "deliverables/summary.json").read_text())["open_count"] == 2
            # Deliberately corrupt the earlier output. Its already-captured
            # score and evidence must not be rewritten by this later action.
            (work / "deliverables/summary.json").write_text('{}')
            atomic_json(work / "deliverables/revised.json", {"count": 2})
        else:
            atomic_json(work / "deliverables/summary.json", {"open_ids": ["R-21", "R-23"], "open_count": 2, "total_effort": 8})
            assert "revised.json" not in instruction
        atomic_json(work / "request-config.json", {"model": model, "effort": SPEC_CALIBRATION_EFFORT, "max_steps": max_steps, "max_tokens": max_tokens})
        atomic_json(work / "conversation.json", [{"role": "user", "content": instruction}])
        return Rollout(rid, tool_calls=3, stop_reason="completed"), work / "deliverables"

    def run_campaign(self):
        with patch("pipeline.calibrate.run._rollout_for", return_value=self.solver):
            return campaign(self.bundle, "synthetic-solver", n=2, workers=2)

    def test_sequential_episode_snapshot_and_same_model_campaign_isolation(self):
        first = self.run_campaign()
        second = self.run_campaign()
        self.assertNotEqual(first["campaign_id"], second["campaign_id"])
        self.assertEqual(first["summary"]["mean_reward"], 1)
        self.assertEqual(calibration_problems(self.bundle, first, replay=True), [])
        self.assertEqual(calibration_problems(self.bundle, second, replay=True), [])
        self.assertEqual(len(first["rollouts"]), 4)

    def test_reports_from_wrong_bundle_model_counts_or_artifacts_are_rejected(self):
        report = self.run_campaign()
        for kind in ("bundle", "checks", "counts", "model"):
            bad = copy.deepcopy(report)
            if kind == "bundle": bad["bundle"] = "other"
            if kind == "checks": bad["rollouts"][0]["checks"] = {"fake": "passed"}
            if kind == "counts": bad["by_step"]["01-task"]["checks"]["open_ids"]["passed"] = 100
            if kind == "model": bad["model"] = "a-model-that-did-not-run"
            with self.subTest(kind=kind):
                self.assertTrue(calibration_problems(self.bundle, bad))
        work = self.bundle / report["rollouts"][0]["work_dir"]
        (work / "deliverables/summary.json").write_text("{}")
        self.assertTrue(calibration_problems(self.bundle, report))

    def test_fixture_instruction_and_solution_changes_invalidate_evidence(self):
        sha = identity(self.bundle)
        for rel in ("environment/files/tickets.csv", "steps/01-task/instruction.md", "solution/submission/summary.json"):
            path = self.bundle / rel
            saved = path.read_bytes()
            path.write_bytes(saved + b" ")
            self.assertNotEqual(identity(self.bundle), sha, rel)
            path.write_bytes(saved)
        atomic_json(self.bundle / "verification/irrelevant.json", {"log": True})
        self.assertEqual(identity(self.bundle), sha)

    def test_legacy_fabricated_report_cannot_certify(self):
        fake = {"schema": "arena-pipeline/calibration/1", "bundle": "other", "summary": {"valid": 100}}
        self.assertTrue(calibration_problems(self.bundle, fake))

    def test_build_lock_is_exclusive_and_released(self):
        with bundle_lock(self.bundle):
            with self.assertRaisesRegex(RuntimeError, "another process"):
                with bundle_lock(self.bundle): pass
        with bundle_lock(self.bundle): pass


if __name__ == "__main__":
    unittest.main()
