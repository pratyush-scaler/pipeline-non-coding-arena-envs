"""Public decimal rounding conventions survive row evaluation and export."""
import json
from pathlib import Path
import tempfile
import unittest

from pipeline.artifacts import atomic_json
from pipeline.author.build import build
from pipeline.author.checks import CheckError, Workspace, evaluate, row_value
from pipeline.author.validate import _walk, _walk_row
from pipeline.evaluate import exported_grade
from pipeline.tests.test_production import synthetic_bundle


class DecimalRounding(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)

    def test_half_ties_follow_the_published_mode_in_both_evaluators(self):
        cases = [(63.05, 1, 63.1, 63), (-63.05, 1, -63.1, -63),
                 (2.675, 2, 2.68, 2.68), (2.685, 2, 2.69, 2.68),
                 (1250, -2, 1300, 1200)]
        for value, places, up, even in cases:
            for mode, expected in [('half_up', up), ('half_even', even)]:
                with self.subTest(value=value, mode=mode):
                    expression = {'op': 'round', 'places': places, 'mode': mode,
                                  'of': {'op': 'field', 'path': 'amount'}}
                    self.assertEqual(row_value(expression, {'amount': value}), expected)
                    atomic_json(self.root / 'amount.json', {'amount': value})
                    expression['of']['file'] = 'amount.json'
                    self.assertEqual(evaluate(expression, Workspace(self.root, self.root), 'source'), expected)

    def test_legacy_rounding_is_not_silently_reinterpreted(self):
        expression = {'op': 'round', 'places': 2, 'of': {'op': 'field', 'path': 'amount'}}
        self.assertEqual(row_value(expression, {'amount': 2.675}), round(2.675, 2))

    def test_rounding_a_ratio_does_not_lose_a_tie_to_binary_arithmetic(self):
        expression = {'op': 'round', 'places': 1, 'mode': 'half_up', 'of': {
            'op': 'multiply', 'a': {'op': 'divide',
                'a': {'op': 'field', 'path': 'received'}, 'b': {'op': 'field', 'path': 'price'}},
            'b': {'op': 'literal', 'value': 100, 'why': 'Report the ratio as a percentage.'}}}
        self.assertEqual(row_value(expression, {'received': 9, 'price': 2000}), .5)
        with self.assertRaisesRegex(CheckError, 'division by zero'):
            row_value(expression, {'received': 9, 'price': 0})
        atomic_json(self.root / 'parts.json', [{'amount': .1}, {'amount': .2}, {'amount': -.25}])
        expression['of'] = {'op': 'sum', 'of': {'op': 'rows', 'file': 'parts.json'}, 'field': 'amount'}
        expression['mode'] = 'half_even'
        self.assertEqual(evaluate(expression, Workspace(self.root, self.root), 'source'), 0)

    def test_unknown_modes_and_invalid_precision_fail_preflight_and_runtime(self):
        for extra in [{'mode': 'up'}, {'mode': None}, {'mode': 'half_up', 'places': True},
                      {'mode': 'half_up', 'places': '2'}, {'mode': 'half_up', 'places': 309}]:
            expression = {'op': 'round', 'of': {'op': 'field', 'path': 'amount'}, **extra}
            errors = []
            _walk_row(expression, 'row', errors)
            self.assertTrue(errors)
            with self.assertRaises(CheckError):
                row_value(expression, {'amount': 63.05})
            expression['of']['file'] = 'amount.json'
            errors = []
            _walk(expression, 'target', {'amount.json'}, errors)
            self.assertTrue(errors)

    def test_exported_grader_distinguishes_correct_and_wrong_tie_results(self):
        bundle = synthetic_bundle(self.root / 'bundle')
        atomic_json(bundle / 'environment/files/amount.json', {'received': 9, 'price': 2000})
        spec = json.loads((bundle / 'authoring/spec.json').read_text())
        schema = spec['outputs'][0]['schema']
        schema['properties']['rounded_amount'] = {'type': 'number'}
        schema['required'].append('rounded_amount')
        spec['solution']['summary.json']['rounded_amount'] = .5
        spec['checks'].append({'id': 'rounded_amount', 'kind': 'objective', 'weight': 1,
            'basis': 'Report received/price as a percentage, rounded to one decimal place, half up.', 'assertion': 'equals',
            'actual': {'op': 'field', 'file': 'summary.json', 'path': 'rounded_amount'},
            'target': {'op': 'round', 'mode': 'half_up', 'places': 1,
                       'of': {'op': 'multiply', 'a': {'op': 'divide',
                           'a': {'op': 'field', 'file': 'amount.json', 'path': 'received'},
                           'b': {'op': 'field', 'file': 'amount.json', 'path': 'price'}},
                           'b': {'op': 'literal', 'value': 100, 'why': 'Convert the ratio to percent.'}}}})
        build(spec, bundle)
        output = self.root / 'submitted'
        atomic_json(output / 'summary.json', spec['solution']['summary.json'])
        self.assertEqual(exported_grade(bundle, output, '01-summary')['reward'], 1)
        spec['solution']['summary.json']['rounded_amount'] = .4
        atomic_json(output / 'summary.json', spec['solution']['summary.json'])
        grade = exported_grade(bundle, output, '01-summary')
        self.assertFalse(grade['checks']['rounded_amount']['passed'])
        self.assertTrue(grade['checks']['open_ids']['passed'])
