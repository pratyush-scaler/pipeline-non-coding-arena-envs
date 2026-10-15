from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest

from pipeline.author.designer import verify_solution
from pipeline.tests.test_production import synthetic_bundle


class ReferenceProjectionRefreshTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.bundle = synthetic_bundle(Path(temporary.name) / 'task')
        self.spec = json.loads((self.bundle / 'authoring/spec.json').read_text())
        self.derived = self.bundle / 'authoring/draft-derived'

    def test_reference_validation_builds_missing_draft_projections(self):
        problems = verify_solution(self.spec, self.bundle)
        self.assertFalse(any('source file not found' in item for item in problems), problems)
        self.assertTrue((self.derived / 'tickets.jsonl').exists())

    def test_reference_validation_does_not_reuse_an_obsolete_projection(self):
        self.derived.mkdir(parents=True, exist_ok=True)
        (self.derived / 'tickets.jsonl').write_text('{"id":"STALE","status":"open","effort":999}\n')
        (self.derived / 'retired.jsonl').write_text('{}\n')
        problems = verify_solution(self.spec, self.bundle)
        self.assertFalse(any('STALE' in item for item in problems), problems)
        self.assertNotIn('STALE', (self.derived / 'tickets.jsonl').read_text())
        self.assertFalse((self.derived / 'retired.jsonl').exists())

    def test_current_fixture_not_old_projection_drives_validation(self):
        verify_solution(self.spec, self.bundle)
        fixture = self.bundle / 'environment/files/tickets.csv'
        fixture.write_text(fixture.read_text().replace('R-22,closed,8', 'R-22,open,8'))
        problems = verify_solution(self.spec, self.bundle)
        self.assertTrue(problems)
        self.assertIn('R-22', (self.derived / 'tickets.jsonl').read_text())

    def test_projection_symlink_is_not_followed_or_removed(self):
        outside = self.bundle.parent / 'outside'
        outside.mkdir()
        self.derived.parent.mkdir(parents=True, exist_ok=True)
        self.derived.symlink_to(outside, target_is_directory=True)
        with self.assertRaisesRegex(ValueError, 'symlink'):
            verify_solution(self.spec, self.bundle)
        self.assertTrue(self.derived.is_symlink())


if __name__ == '__main__':
    unittest.main()
