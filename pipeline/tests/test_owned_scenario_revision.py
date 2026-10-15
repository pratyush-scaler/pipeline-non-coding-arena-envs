from __future__ import annotations

import json
from pathlib import Path
import shutil
import tempfile
import unittest
from unittest.mock import patch

from pipeline.author.scenario import MANIFEST, NOTICE, reconcile_owned_revision, verify, write


class OwnedScenarioRevisionTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.source = self.root / 'source'
        fixture = self.source / 'environment/files'
        fixture.mkdir(parents=True)
        self.quote = 'Each confirmed order receives one allocation under the published policy.'
        (fixture / 'policy.md').write_text((self.quote + '\n') * 400)
        self.arguments = {'path': 'scenario/orders.json', 'content': '{"quantity":3}',
                          'reason': 'Apply the recovered rule to an explicitly hypothetical order.',
                          'source_evidence': [{'file': 'policy.md', 'quote': self.quote}]}
        write(self.source, **self.arguments)
        self.bundle = self.root / 'working'
        shutil.copytree(self.source, self.bundle)
        self.target = self.bundle / 'environment/files/scenario/orders.json'
        self.reason = 'Repair the public order condition without altering any recovered evidence.'

    def reconcile(self):
        return reconcile_owned_revision(self.source, self.bundle, reason=self.reason)

    def test_owned_edit_gets_a_valid_grounded_receipt_without_source_credit(self):
        original = (self.source / MANIFEST).read_bytes()
        self.target.write_text('{"quantity":4}')
        receipt = self.reconcile()
        self.assertEqual(receipt['recovered_source_credit'], 0)
        self.assertEqual(receipt['owned_changes'][0]['file'], 'scenario/orders.json')
        self.assertEqual(set(verify(self.bundle)), {'scenario/orders.json'})  # v2: notice in provenance/
        self.assertEqual((self.source / MANIFEST).read_bytes(), original)
        self.assertEqual((self.source / 'environment/files/scenario/orders.json').read_text(), '{"quantity":3}')

    def test_changed_recovered_file_is_not_restamped(self):
        (self.bundle / 'environment/files/policy.md').write_text('Changed recovered evidence.')
        with self.assertRaisesRegex(ValueError, 'recovered evidence'):
            self.reconcile()

    def test_unowned_new_file_is_not_silently_disclosed(self):
        (self.bundle / 'environment/files/scenario/extra.json').write_text('{}')
        with self.assertRaisesRegex(ValueError, 'undisclosed files'):
            self.reconcile()

    def test_existing_writer_receipt_remains_valid(self):
        write(self.bundle, **{**self.arguments, 'content': '{"quantity":5}'})
        self.assertTrue(self.reconcile()['receipt_already_verified'])
        self.assertTrue(verify(self.bundle))

    def test_failure_restores_the_working_copy_not_the_immutable_source(self):
        self.target.write_text('{"quantity":4}')
        paths = [self.target, self.bundle / MANIFEST, self.bundle / NOTICE]
        before = {path: path.read_bytes() for path in paths}
        with patch('pipeline.author.scenario.write', side_effect=OSError('disk fault')):
            with self.assertRaisesRegex(OSError, 'disk fault'):
                self.reconcile()
        self.assertEqual({path: path.read_bytes() for path in paths}, before)
        self.assertTrue(verify(self.source))

    def test_invalid_json_edit_is_not_accepted(self):
        self.target.write_text('{broken')
        with self.assertRaises(ValueError):
            self.reconcile()
        self.assertEqual(self.target.read_text(), '{broken')

    def test_manifest_cannot_reclassify_recovered_evidence(self):
        path = self.bundle / MANIFEST
        document = json.loads(path.read_text())
        del document['base']['policy.md']
        path.write_text(json.dumps(document))
        with self.assertRaisesRegex(ValueError, 'reclassify recovered evidence'):
            self.reconcile()

    def test_source_and_working_copy_must_be_disjoint(self):
        with self.assertRaisesRegex(ValueError, 'disjoint'):
            reconcile_owned_revision(self.source, self.source, reason=self.reason)


if __name__ == '__main__':
    unittest.main()
