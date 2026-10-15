"""Shape inventories preserve associations without grading harmless row order."""
import copy
import json
from pathlib import Path
import tempfile
import unittest

from pipeline.author.build import build
from pipeline.author.checks import Check, CheckError, Workspace, evaluate
from pipeline.author.oracle import svg_elements
from pipeline.evaluate import exported_grade
from pipeline.row_controls import run
from pipeline.source_controls import run as source_controls, problems as source_problems
from pipeline.tests.test_production import synthetic_bundle


class StructuredGeometry(unittest.TestCase):
    def test_extrema_use_all_named_source_attributes(self):
        ws = Workspace(Path('.'), Path('.'))
        source = {'op': 'literal', 'value': [{'point': {'x': 20, 'y': 10}}, {'point': {'x': 80, 'y': 90}}],
                  'why': 'Synthetic input for the operator regression.'}
        self.assertEqual(evaluate({'op': 'min', 'of': source, 'fields': ['point.x', 'point.y']}, ws, 'source'), 10)
        self.assertEqual(evaluate({'op': 'max', 'of': source, 'fields': ['point.x', 'point.y']}, ws, 'source'), 90)

    def test_extrema_do_not_invent_defaults_for_missing_or_nonnumeric_evidence(self):
        ws = Workspace(Path('.'), Path('.'))
        for values in ([], [False], ['missing'], [None]):
            with self.subTest(values=values), self.assertRaises(CheckError):
                evaluate({'op': 'min', 'of': {'op': 'literal', 'value': values, 'why': 'Synthetic invalid evidence.'}}, ws, 'source')

    def test_source_invariants_preserve_the_whole_answer_without_causal_credit(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            bundle = synthetic_bundle(root)
            spec = json.loads((bundle / 'authoring/spec.json').read_text())
            spec['quality'] = {'semantic_checks': ['open_count'], 'source_cases': [{
                'id': 'reopened', 'reason': 'A closed ticket is reopened.', 'changes': ['open_count'],
                'source_patches': [{'file': 'tickets.csv', 'before': 'R-22,closed,8', 'after': 'R-22,open,8'}],
                'patches': [{'file': 'summary.json', 'path': 'open_ids', 'value': ['R-21', 'R-22', 'R-23']},
                            {'file': 'summary.json', 'path': 'open_count', 'value': 3},
                            {'file': 'summary.json', 'path': 'total_effort', 'value': 16}]}],
                'source_invariants': [{'id': 'closed-effort', 'reason': 'The amount of closed work does not affect the open-work report.',
                    'source_patches': [{'file': 'tickets.csv', 'before': 'R-22,closed,8', 'after': 'R-22,closed,900'}]}]}
            build(spec, bundle)
            spec = json.loads((bundle / 'authoring/spec.json').read_text())
            checks = {c['id']: c for c in spec['checks']}
            result = source_controls(bundle, spec, spec['solution'], checks, root / 'valid')
            self.assertEqual(result['errors'], [])
            self.assertTrue(result['results']['closed-effort']['invariant'])
            spec['quality']['source_invariants'][0]['source_patches'][0] = {
                'file': 'tickets.csv', 'before': 'R-21,open,3', 'after': 'R-21,open,9'}
            result = source_controls(bundle, spec, spec['solution'], checks, root / 'invalid')
            self.assertTrue(any('closed-effort: corrected source variant must score 1' in e for e in result['errors']))
            spec['quality']['source_cases'] = []
            self.assertTrue(any('do not exercise' in e for e in source_problems(spec, bundle)))

    def test_svg_projection_retains_attributes_duplicates_and_ancestor_transforms(self):
        text = ('## Definitive\n```svg\n<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100">'
            '<g transform="translate(10,20)"><line y1="2" x1="1" x2="3" y2="4"/>'
            '<line y1="2" x1="1" x2="3" y2="4"/></g></svg>\n```\n'
            '## Other\n<svg><circle r="5"/></svg>')
        rows = svg_elements(text)
        lines = [r for r in rows if r['tag'] == 'line']
        self.assertEqual(len(lines), 2)
        self.assertEqual(lines[0], lines[1])
        self.assertEqual(lines[0]['section_heading'], 'Definitive')
        self.assertEqual(lines[0]['attributes']['x1'], '1')  # no invented transform application
        self.assertEqual(lines[0]['ancestors'][-1]['attributes']['transform'], 'translate(10,20)')
        self.assertEqual(rows[-1]['section_heading'], 'Other')
        self.assertEqual(rows[-1]['svg_index'], 2)

    def test_svg_parser_refuses_malformed_or_unsupported_markup(self):
        for text in ('<svg><line></svg>', '<svg>', '<svg><svg></svg></svg>',
                     '<!DOCTYPE svg [<!ENTITY value "secret">]><svg/>'):
            with self.subTest(text=text), self.assertRaises(ValueError):
                svg_elements(text)

    def test_nested_unordered_records_preserve_multiplicity_and_other_sequence_order(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            bundle = synthetic_bundle(root)
            spec = json.loads((bundle / 'authoring/spec.json').read_text())
            shape = {'lines': [{'x1': 2, 'y1': 4, 'x2': 8, 'y2': 4},
                               {'x1': 3, 'y1': 4, 'x2': 9, 'y2': 9}], 'ordered': [1, 2]}
            row = {'type': 'object', 'properties': {k: {'type': 'integer'} for k in shape['lines'][0]},
                   'required': list(shape['lines'][0]), 'additionalProperties': False}
            schema = {'type': 'object', 'properties': {
                'lines': {'type': 'array', 'items': row},
                'ordered': {'type': 'array', 'items': {'type': 'integer'}}},
                'required': ['lines', 'ordered'], 'additionalProperties': False}
            spec['outputs'][0]['schema']['properties']['shape'] = schema
            spec['outputs'][0]['schema']['required'].append('shape')
            spec['solution']['summary.json']['shape'] = shape
            (bundle / 'environment/files/shape.json').write_text(json.dumps(shape))
            check = {'id': 'shape', 'kind': 'objective', 'weight': 10, 'basis': 'Keep complete lines; line order is irrelevant, ordered remains ordered.',
                'assertion': 'equals', 'actual': {'op': 'field', 'file': 'summary.json', 'path': 'shape'},
                'target': {'op': 'field', 'file': 'shape.json', 'path': ''}, 'unordered_paths': ['lines']}
            spec['checks'].append(check)
            build(spec, bundle)
            built = json.loads((bundle / 'authoring/spec.json').read_text())
            report = run(bundle, built, built['solution'], {c['id']: c for c in built['checks']}, root / 'controls')
            self.assertEqual(report['errors'], [])
            self.assertEqual(report['results']['shape.lines/allowed-row-reordering']['reward'], 1)
            for name in ('drop-row', 'append-duplicate', 'exchange-y2'):
                self.assertFalse(report['results']['shape.lines/' + name]['check']['passed'])
            path = bundle / 'solution/submission/summary.json'
            value = copy.deepcopy(built['solution']['summary.json'])
            value['shape']['ordered'].reverse()
            path.write_text(json.dumps(value))
            self.assertFalse(exported_grade(bundle, path.parent, '01-summary')['checks']['shape']['passed'])

    def test_unordered_paths_are_explicit_and_only_apply_to_equality(self):
        for paths in ('lines', [''], ['lines', 'lines'], [None]):
            check = Check('x', 'objective', 1, 'Public rule', 'equals', {}, {}, unordered_paths=paths)
            self.assertTrue(check.validate())
        check = Check('x', 'objective', 1, 'Public rule', 'multiset_equals', {}, {}, unordered_paths=['lines'])
        self.assertTrue(check.validate())
