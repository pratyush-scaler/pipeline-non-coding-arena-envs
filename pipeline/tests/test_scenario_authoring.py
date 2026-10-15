"""Scenario synthesis never edits recovered evidence or earns source credit."""
import json
import os
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from pipeline.artifacts import atomic_json
from pipeline.author.scenario import MANIFEST, MAX_FILE_BYTES, NOTICE, verify, write, remove
from pipeline.ledger.faithfulness import build


class ScenarioAuthoring(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        self.bundle = self.root / 'task'
        self.fixture = self.bundle / 'environment/files'
        self.fixture.mkdir(parents=True)
        self.quote = 'An item may be allocated to only one confirmed order.'
        self.original = (self.quote + '\n') * 400
        (self.fixture / 'policy.md').write_text(self.original)
        self.args = dict(path='scenario/orders.json', content='{"orders":[{"id":"A","quantity":3}]}',
                         reason='Apply the recovered allocation rule to a hypothetical order book.',
                         source_evidence=[{'file': 'policy.md', 'quote': self.quote}], category='A')

    def test_recovered_sources_survive_creation_and_revision_with_public_disclosure(self):
        report = write(self.bundle, **self.args)
        self.assertEqual(report['source_credit'], 0)
        self.assertEqual((self.fixture / 'policy.md').read_text(), self.original)
        self.assertIn('not recovered trace documents', (self.bundle / NOTICE).read_text())
        self.assertEqual(set(verify(self.bundle)), {'scenario/orders.json'})
        write(self.bundle, **{**self.args, 'content': '{"orders":[{"id":"B","quantity":4}]}'})
        self.assertEqual(json.loads((self.fixture / 'scenario/orders.json').read_text())['orders'][0]['id'], 'B')
        self.assertEqual((self.fixture / 'policy.md').read_text(), self.original)

    def test_remove_owned_supplement_updates_disclosure_and_preserves_other_files(self):
        write(self.bundle, **self.args)
        write(self.bundle, **{**self.args, 'path': 'scenario/other.json', 'content': '{"quantity":5}'})
        other = (self.fixture / 'scenario/other.json').read_bytes()
        result = remove(self.bundle, path=self.args['path'], reason='Remove an obsolete authored register without altering the recovered evidence.')
        self.assertEqual(result['remaining_supplements'], ['scenario/other.json'])
        self.assertFalse((self.fixture / self.args['path']).exists())
        self.assertNotIn('scenario/orders.json', (self.bundle / NOTICE).read_text())
        self.assertEqual(set(verify(self.bundle)), {'scenario/other.json'})
        self.assertEqual((self.fixture / 'scenario/other.json').read_bytes(), other)
        self.assertEqual((self.fixture / 'policy.md').read_text(), self.original)

    def test_remove_last_supplement_restores_base_and_allows_a_new_scenario(self):
        write(self.bundle, **self.args)
        remove(self.bundle, path=self.args['path'], reason='Remove the final authored case before choosing a new professional decision.')
        self.assertEqual(verify(self.bundle), {})
        self.assertFalse((self.bundle / NOTICE).exists())
        self.assertFalse((self.bundle / MANIFEST).exists())
        self.assertEqual({p.relative_to(self.fixture).as_posix(): p.read_text()
                          for p in self.fixture.rglob('*') if p.is_file()}, {'policy.md': self.original})
        write(self.bundle, **self.args)
        self.assertTrue(verify(self.bundle))

    def test_removal_refuses_sources_unknown_files_and_changed_evidence(self):
        write(self.bundle, **self.args)
        reason = 'Remove an obsolete scenario while preserving recovered source documents.'
        for path in ('policy.md', '../policy.md', NOTICE, 'scenario/unowned.json'):
            with self.subTest(path=path), self.assertRaises(ValueError):
                remove(self.bundle, path=path, reason=reason)
        target = self.fixture / self.args['path']
        original = target.read_bytes()
        target.write_text('{"unregistered":"change"}')
        with self.assertRaisesRegex(ValueError, 'bytes differ'):
            remove(self.bundle, path=self.args['path'], reason=reason)
        self.assertTrue(target.exists())
        self.assertEqual((self.fixture / 'policy.md').read_text(), self.original)
        target.write_bytes(original)
        self.assertTrue(verify(self.bundle))

    def test_removal_handler_rolls_back_after_receipt_failure(self):
        from pipeline.author.agent_designer import _handlers, _tools
        write(self.bundle, **self.args)
        write(self.bundle, **{**self.args, 'path': 'scenario/other.json', 'content': '{}'})
        files = [self.fixture / self.args['path'], self.bundle / NOTICE, self.bundle / MANIFEST]
        before = {p: p.read_bytes() for p in files}
        handler = _handlers(self.bundle, SimpleNamespace(moments=[]), {'messages': []})['remove_scenario']
        self.assertIn('remove_scenario', {t['name'] for t in _tools(0)})
        with patch('pipeline.artifacts.atomic_json', side_effect=OSError('disk fault')):
            with self.assertRaisesRegex(OSError, 'disk fault'):
                handler(path=self.args['path'], reason='Remove an obsolete authored register from this revised assignment.')
        self.assertEqual({p: p.read_bytes() for p in files}, before)
        self.assertTrue(verify(self.bundle))

    def test_traversal_source_overwrite_and_symlink_escape_are_refused(self):
        for name in ('policy.md', '../private.json', 'scenario/../policy.md', 'provenance/README.md',
                     'scenario/bad\nname.json', 'scenario/run.py'):
            with self.subTest(name=name), self.assertRaises(ValueError):
                write(self.bundle, **{**self.args, 'path': name})
        (self.fixture / 'scenario').symlink_to(self.root, target_is_directory=True)
        with self.assertRaises(ValueError):
            write(self.bundle, **self.args)
        self.assertFalse((self.root / 'orders.json').exists())
        self.assertEqual((self.fixture / 'policy.md').read_text(), self.original)

    def test_grounding_cannot_use_private_or_invented_evidence(self):
        for evidence in ([{'file': 'policy.md', 'quote': 'This sentence was never in the source.'}],
                         [{'file': '../../authoring/answer.md', 'quote': self.quote}]):
            with self.subTest(evidence=evidence), self.assertRaises(ValueError):
                write(self.bundle, **{**self.args, 'source_evidence': evidence})
        write(self.bundle, **self.args)
        with self.assertRaises(ValueError):
            write(self.bundle, **{**self.args, 'source_evidence': [
                {'file': 'scenario/orders.json', 'quote': self.args['content']}]})

    def test_tampering_with_scenario_source_or_disclosure_invalidates_receipt(self):
        write(self.bundle, **self.args)
        for name in ('policy.md', 'scenario/orders.json', NOTICE):
            path = (self.bundle if name == NOTICE else self.fixture) / name
            original = path.read_bytes()
            path.write_bytes(original + b'changed')
            with self.subTest(name=name), self.assertRaises(ValueError):
                verify(self.bundle)
            path.write_bytes(original)
        self.assertTrue(verify(self.bundle))

    def test_privacy_and_fidelity_limits_fail_before_mutating_the_fixture(self):
        cases = [('fidelity allowance', {'path': 'scenario/orders.txt', 'content': 'facts ' * 800}),
                 (f'{MAX_FILE_BYTES // 1024} KiB', {'content': 'x' * (MAX_FILE_BYTES + 1)}),  # v2: limit from policy
                 ('private data', {'path': 'scenario/orders.txt', 'content': 'Contact person@company.test'})]
        for message, changes in cases:
            with self.subTest(message=message), self.assertRaisesRegex(ValueError, message):
                write(self.bundle, **{**self.args, **changes})
            self.assertFalse((self.bundle / MANIFEST).exists())
            self.assertFalse((self.bundle / NOTICE).exists())
            self.assertEqual((self.fixture / 'policy.md').read_text(), self.original)

    def test_authored_copy_cannot_launder_source_credit(self):
        trace = {'session_id': 'source', 'messages': [{'role': 'assistant', 'content': [
            {'type': 'tool-write_file', 'input': {'path': 'policy.md', 'content': self.original}}]}]}
        atomic_json(self.root / 'dump/sessions/source/data.json', {'traces': [trace]})
        self.enterContext(patch.dict(os.environ, ARENA_DUMP=str(self.root / 'dump')))
        write(self.bundle, **{**self.args, 'path': 'scenario/copy.md', 'content': self.original, 'category': None})
        ledger = build(self.bundle, 'source', 0)
        origins = {r['path']: r['origin'] for r in ledger['entries']}
        self.assertEqual(origins, {'policy.md': 'lifted', 'scenario/copy.md': 'authored'})  # v2: the notice lives in provenance/, outside the fixture
        # v2: without the in-fixture notice the authored copy is exactly half the
        # bytes; it still earns no source credit.
        self.assertLessEqual(ledger['faithfulness_by_bytes'], .5)
        self.assertEqual(ledger['exact_copy_by_bytes'], ledger['faithfulness_by_bytes'])

    def test_handler_preserves_category_allowance_and_failed_write_rolls_back(self):
        from pipeline.author.agent_designer import _handlers
        from pipeline.tests.test_capability_construction import planned_spec
        handlers = _handlers(self.bundle, SimpleNamespace(moments=[]), {'messages': []}, category='A')
        handlers['stage_spec'](['quality'], planned_spec()['quality'])
        handler = handlers['write_scenario']
        args = {k:v for k,v in self.args.items() if k != 'category'}
        with self.assertRaisesRegex(ValueError, 'fidelity allowance'):
            handler(**{**args, 'path': 'scenario/orders.txt', 'content': 'facts ' * 800})
        handler(**args)
        before = {p: p.read_bytes() for p in (self.fixture / 'scenario/orders.json', self.bundle / NOTICE, self.bundle / MANIFEST)}
        with patch('pipeline.artifacts.atomic_json', side_effect=OSError('disk fault')):
            with self.assertRaisesRegex(OSError, 'disk fault'):
                handler(**{**args, 'content': '{"orders":[]}'})
        self.assertEqual({p:p.read_bytes() for p in before}, before)
        self.assertTrue(verify(self.bundle))

    def test_precalibration_ledger_gate_rejects_forged_source_credit(self):
        from pipeline.gates.bundle import _ledger_shape
        trace = {'session_id': 'source', 'messages': [{'role': 'assistant', 'content': [
            {'type': 'tool-write_file', 'input': {'path': 'policy.md', 'content': self.original}}]}]}
        atomic_json(self.root / 'dump/sessions/source/data.json', {'traces': [trace]})
        self.enterContext(patch.dict(os.environ, ARENA_DUMP=str(self.root / 'dump')))
        write(self.bundle, **self.args)
        ledger = build(self.bundle, 'source', 0)
        ledger['category'] = 'A'
        for entry in ledger['entries']:
            entry.update(origin='lifted', citation='source::msg0::policy.md')
        ledger['counts'] = {'lifted': len(ledger['entries']), 'anonymized': 0, 'derived': 0, 'authored': 0}
        ledger['bytes'] = {'lifted': sum(e['bytes'] for e in ledger['entries']), 'anonymized': 0, 'derived': 0, 'authored': 0}
        for field in ('faithfulness_by_file', 'faithfulness_by_bytes', 'exact_copy_by_file', 'exact_copy_by_bytes'):
            ledger[field] = 1.0
        atomic_json(self.bundle / 'provenance/ledger.json', ledger)
        atomic_json(self.bundle / 'authoring/traps.json', {'source_tier': 4})
        ctx = SimpleNamespace(task_dir=self.bundle, path=lambda *parts:self.bundle.joinpath(*parts), extras={})
        findings, _ = _ledger_shape(ctx)
        self.assertTrue(any('unverified-authored-scenario' in str(f) for f in findings), findings)

    def test_exported_grader_protects_added_scenario_bytes_and_reproduces(self):
        import shutil
        from pipeline.tests.test_production import synthetic_bundle
        from pipeline.author.build import build as export
        from pipeline.assurance import generated_problems
        from pipeline.evaluate import exported_grade
        bundle = synthetic_bundle(self.root / 'export')
        (bundle / 'environment/files/policy.md').write_text(self.original)
        write(bundle, **self.args)
        spec = json.loads((bundle / 'authoring/spec.json').read_text())
        export(spec, bundle)
        self.assertEqual(generated_problems(bundle), [])
        self.assertEqual(exported_grade(bundle, bundle / 'solution/submission', '01-summary')['reward'], 1)
        changed = self.root / 'changed-source'
        shutil.copytree(bundle / 'environment/files', changed)
        (changed / 'scenario/orders.json').write_text('{"orders":[]}')
        result = exported_grade(bundle, bundle / 'solution/submission', '01-summary', changed)
        self.assertEqual(result['reward'], 0)
        self.assertIn('source_unchanged', result['guardrails_violated'])
        remove(bundle, path=self.args['path'], reason='The revised task no longer needs this authored order supplement.')
        self.assertEqual(exported_grade(bundle, bundle / 'solution/submission', '01-summary')['reward'], 0)
        export(spec, bundle)
        self.assertEqual(generated_problems(bundle), [])
        self.assertEqual(exported_grade(bundle, bundle / 'solution/submission', '01-summary')['reward'], 1)
