"""Recovered professional text must not be labelled as authored binary data."""
import json
from pathlib import Path
import tempfile
import unittest

from pipeline.dump import recover
from pipeline.ledger import faithfulness


class DocumentRecovery(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)
        self.text = {
            'formulas.tex': '\\section{Capacity}\n$E = P \\Delta t$\n',
            'report.rst': 'Capacity\n========\nA recovered calculation.\n',
            'records.jsonl': '{"item":"R1","amount":12}\n',
            'measurements.tsv': 'item\tamount\nR1\t12\n',
        }
        self.trace = {'session_id': 'session', 'messages': [
            {'role': 'assistant', 'content': [
                {'type': 'tool-write_file', 'input': {'path': name, 'content': text}}
                for name, text in self.text.items()]}]}
        folder = self.root / 'sessions/session'
        folder.mkdir(parents=True)
        (folder / 'data.json').write_text(json.dumps({'traces': [self.trace]}))

    def test_professional_text_is_materialised_and_counted_as_recovered_source(self):
        ws = recover.recover(self.trace)
        self.assertEqual({p: r.content for p, r in ws.at(0).items()}, self.text)
        self.assertEqual(ws.source_paths(), set(self.text))
        self.assertEqual(ws.bytes_recovered(), sum(len(s.encode()) for s in self.text.values()))

    def test_source_credit_requires_exact_trace_content_not_a_document_extension(self):
        bundle = self.root / 'bundle'
        fixture = bundle / 'environment/files'
        fixture.mkdir(parents=True)
        for name, content in self.text.items():
            (fixture / name).write_text(content)
        (fixture / 'new.tex').write_text('Entirely new document with no trace ancestor.\n')
        (fixture / 'image.png').write_bytes(b'\x89PNG\r\n\x1a\n')
        ledger = faithfulness.build(bundle, 'session', 0, root=self.root / 'sessions')
        entries = {e['path']: e for e in ledger['entries']}
        for name in self.text:
            self.assertEqual(entries[name]['origin'], 'lifted')
            self.assertEqual(entries[name]['citation'], 'session::msg0::' + name)
        for name in ('new.tex', 'image.png'):
            self.assertEqual(entries[name]['origin'], 'authored')
            self.assertIsNone(entries[name]['citation'])


if __name__ == '__main__':
    unittest.main()
