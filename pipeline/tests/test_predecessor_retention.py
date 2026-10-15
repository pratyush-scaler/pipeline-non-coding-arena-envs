from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from pipeline.artifacts import atomic_json, identity
from pipeline.corpus import review_context
from pipeline.tests.test_production import synthetic_bundle


class ExactPredecessorRetentionTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name).resolve()
        self.archive = synthetic_bundle(self.root / 'campaign/candidates/previous/hardened/v3')
        self.candidate = synthetic_bundle(self.root / 'draft')
        self.fingerprint = identity(self.archive)
        atomic_json(self.candidate / 'provenance/replacement.json', {
            'schema': 'arena-pipeline/replacement/1',
            'predecessors': [self.fingerprint], 'reason': 'Repair the retained task.'})
        self.receipt = {'schema': 'arena-pipeline/predecessor-retention/1',
                        'retained_artifacts': [self.fingerprint],
                        'retained_paths': {self.fingerprint: str(self.archive)}}
        self.save()

    def save(self):
        atomic_json(self.candidate / 'provenance/retained-ancestry.json', self.receipt)

    def test_nested_exact_archive_is_discovered_without_aliases(self):
        context = review_context(self.candidate, self.root)
        self.assertEqual(context['design_mode'], 'replacement')
        self.assertEqual([(peer['artifact_sha256'], peer['relationship'])
                          for peer in context['peers']], [(self.fingerprint, 'predecessor')])

    def test_changed_archive_cannot_be_used(self):
        (self.archive / 'steps/01-summary/instruction.md').write_text('Changed.')
        with self.assertRaisesRegex(ValueError, 'missing or changed'):
            review_context(self.candidate, self.root)

    def test_missing_archive_cannot_be_used(self):
        self.receipt['retained_paths'][self.fingerprint] = str(self.root / 'missing')
        self.save()
        with self.assertRaisesRegex(ValueError, 'missing or changed'):
            review_context(self.candidate, self.root)

    def test_relative_archive_path_is_rejected(self):
        self.receipt['retained_paths'][self.fingerprint] = 'campaign/candidates/previous'
        self.save()
        with self.assertRaisesRegex(ValueError, 'absolute archive path'):
            review_context(self.candidate, self.root)

    def test_retention_receipt_must_cover_declared_predecessors(self):
        self.receipt['retained_artifacts'] = []
        self.receipt['retained_paths'] = {}
        self.save()
        with self.assertRaisesRegex(ValueError, 'retention receipt'):
            review_context(self.candidate, self.root)

    def test_unrelated_archive_is_not_exempted(self):
        path = self.archive / 'authoring/spec.json'
        spec = json.loads(path.read_text())
        spec['source']['session_id'] = 'different-session'
        atomic_json(path, spec)
        (self.archive / 'environment/files/tickets.csv').write_text('unrelated,records\n')
        (self.archive / 'environment/files/unprojected.txt').write_text('different')
        fingerprint = identity(self.archive)
        atomic_json(self.candidate / 'provenance/replacement.json', {
            'schema': 'arena-pipeline/replacement/1', 'predecessors': [fingerprint],
            'reason': 'Invalid unrelated replacement.'})
        self.receipt['retained_artifacts'] = [fingerprint]
        self.receipt['retained_paths'] = {fingerprint: str(self.archive)}
        self.save()
        with self.assertRaisesRegex(ValueError, 'unrelated source family'):
            review_context(self.candidate, self.root)

    def test_alias_and_retained_path_do_not_duplicate_predecessor(self):
        aliases = self.root / 'envs-exact-archives'
        aliases.mkdir()
        (aliases / self.fingerprint).symlink_to(self.archive, target_is_directory=True)
        self.assertEqual(len(review_context(self.candidate, self.root)['peers']), 1)


if __name__ == '__main__':
    unittest.main()
