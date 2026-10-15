"""Recovered evidence can be staged after supplements without hiding tampering."""
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from pipeline.artifacts import atomic_json
from pipeline.author.scenario import MANIFEST, NOTICE, remove, verify, write
from pipeline.dump.evidence import Catalog
from pipeline.dump.recover import recover
from pipeline.ledger.faithfulness import build


class ScenarioStaging(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name).resolve()
        self.bundle = self.root / 'bundle'
        self.fixture = self.bundle / 'environment/files'
        self.fixture.mkdir(parents=True)
        self.source_root = self.root / 'sessions'
        self.quote = 'Only confirmed orders may receive an allocation from this inventory.'
        self.policy = (self.quote + '\n') * 300
        (self.fixture / 'policy.md').write_text(self.policy)
        self.trace = {'session_id': 'source', 'messages': [
            {'role': 'assistant', 'content': [{'type': 'tool-write_file',
                'input': {'path': 'policy.md', 'content': self.policy}}]},
            {'role': 'user', 'content': [{'type': 'text',
                'text': 'For this order book reserve five units before allocating confirmed orders.'}]},
            {'role': 'user', 'content': [{'type': 'text',
                'text': 'Use ssh analyst@10.8.0.2 to inspect the retained allocation document.'}]}]}
        atomic_json(self.source_root / 'source/data.json', {'traces': [self.trace]})
        self.catalog = Catalog(self.trace, recover(self.trace, self.source_root), self.source_root)
        self.args = dict(path='scenario/orders.json', content='{"orders":[{"id":"A","quantity":3}]}',
            reason='Apply the recovered allocation rule to a hypothetical order book.',
            source_evidence=[{'file': 'policy.md', 'quote': self.quote}], category='A')
        write(self.bundle, **self.args)

    def stage(self, evidence_id='m1-b0'):
        self.catalog.read(evidence_id)
        return self.catalog.stage(self.bundle, evidence_id, 'sources/reserve.json',
            'This retained instruction supplies the allocation reserve constraint.')

    def inventory(self):
        return {p.relative_to(self.bundle).as_posix(): p.read_bytes()
            for p in self.bundle.rglob('*') if p.is_file()}

    def test_staged_source_preserves_edits_removal_and_independent_source_credit(self):
        before = json.loads((self.bundle / MANIFEST).read_text())
        self.stage()
        self.assertTrue(verify(self.bundle))
        after = json.loads((self.bundle / MANIFEST).read_text())
        self.assertEqual(after['files'], before['files'])
        self.assertEqual(after['notice'], before['notice'])
        self.assertEqual(after['base']['policy.md'], before['base']['policy.md'])
        ledger = build(self.bundle, 'source', root=self.source_root)
        origins = {row['path']: row['origin'] for row in ledger['entries']}
        self.assertEqual(origins, {'policy.md': 'lifted', 'sources/reserve.json': 'lifted',
            'scenario/orders.json': 'authored'})  # v2: notice in provenance/, outside the fixture
        write(self.bundle, **{**self.args, 'content': '{"orders":[]}'})
        write(self.bundle, **{**self.args, 'path': 'scenario/reserve.txt', 'content': 'Hypothetical reserve: 5.',
            'source_evidence': [{'file': 'sources/reserve.json',
                'quote': self.trace['messages'][1]['content'][0]['text']}]})
        for path in ('scenario/orders.json', 'scenario/reserve.txt'):
            remove(self.bundle, path=path, reason='Remove this hypothetical register while retaining every recovered source.')
        self.assertFalse((self.bundle / MANIFEST).exists())
        self.assertTrue((self.fixture / 'sources/reserve.json').exists())
        self.assertEqual((self.fixture / 'policy.md').read_text(), self.policy)

    def test_existing_tampering_is_rejected_before_any_new_source_is_written(self):
        for name in ('policy.md', 'scenario/orders.json', NOTICE, 'sources/unregistered.txt'):
            with self.subTest(name=name):
                target = self.fixture / name
                original = target.read_bytes() if target.exists() else None
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes((original or b'') + b'undocumented change')
                before = self.inventory()
                with self.assertRaisesRegex(ValueError, 'bytes differ'):
                    self.stage()
                self.assertEqual(self.inventory(), before)
                if original is None:
                    target.unlink()
                else:
                    target.write_bytes(original)

    def test_scenario_receipt_failure_rolls_back_source_and_both_receipts(self):
        for existing_selection in (False, True):
            with self.subTest(existing_selection=existing_selection):
                selection = self.bundle / 'provenance/evidence-selection.json'
                if existing_selection:
                    atomic_json(selection, {'schema': 'arena-pipeline/evidence/1', 'selections': []})
                before = self.inventory()
                def fail_receipt(path, value):
                    if path == self.bundle / MANIFEST:
                        raise OSError('scenario receipt disk fault')
                    return atomic_json(path, value)
                with patch('pipeline.artifacts.atomic_json', side_effect=fail_receipt):
                    with self.assertRaisesRegex(OSError, 'disk fault'):
                        self.stage()
                self.assertEqual(self.inventory(), before)
                self.assertTrue(verify(self.bundle))

    def test_privacy_transformed_addition_binds_public_bytes_and_retains_source_proof(self):
        record = self.stage('m2-b0')
        public = (self.fixture / 'sources/reserve.json').read_bytes()
        self.assertNotIn(b'analyst@10.8.0.2', public)
        doc = json.loads((self.bundle / MANIFEST).read_text())
        self.assertEqual(doc['base']['sources/reserve.json'],
            {'sha256': hashlib.sha256(public).hexdigest(), 'bytes': len(public)})
        self.assertNotEqual(record['staged_sha256'], hashlib.sha256(public).hexdigest())
        self.assertTrue(verify(self.bundle))
        ledger = build(self.bundle, 'source', root=self.source_root)
        self.assertEqual(next(row['origin'] for row in ledger['entries']
            if row['path'] == 'sources/reserve.json'), 'anonymized')

    def test_failed_receipt_after_privacy_pass_rolls_back_redaction_as_well(self):
        before = self.inventory()
        def fail_receipt(path, value):
            if path == self.bundle / MANIFEST:
                raise OSError('scenario receipt disk fault')
            return atomic_json(path, value)
        with patch('pipeline.artifacts.atomic_json', side_effect=fail_receipt):
            with self.assertRaisesRegex(OSError, 'disk fault'):
                self.stage('m2-b0')
        self.assertEqual(self.inventory(), before)
        self.assertTrue(verify(self.bundle))

    def test_partial_source_write_rolls_back_without_invalidating_existing_scenario(self):
        before = self.inventory()
        original_write = Path.write_bytes
        def partial_write(path, data):
            if path == self.fixture / 'sources/reserve.json':
                original_write(path, data[:20])
                raise OSError('partial fixture write')
            return original_write(path, data)
        with patch.object(Path, 'write_bytes', partial_write):
            with self.assertRaisesRegex(OSError, 'partial fixture write'):
                self.stage()
        self.assertEqual(self.inventory(), before)
        self.assertTrue(verify(self.bundle))


if __name__ == '__main__':
    unittest.main()
