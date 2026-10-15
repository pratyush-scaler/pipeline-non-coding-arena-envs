"""Reporting precision cannot replace a source-defined numeric equality."""
import copy
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


def literal(value):
    return {'op': 'literal', 'value': value, 'why': 'Public numerical parameter for the test instance.'}


def number(value):
    return {'op': 'number', 'of': value}


def operation(op, a, b):
    return {'op': op, 'a': a, 'b': b}


def compare(a, b, comparison='eq', exact=True):
    expr = {'op': 'compare', 'a': a, 'b': b, 'comparison': comparison, 'value_type': 'number'}
    if exact:
        expr['mode'] = 'exact'
    return expr


def product(values):
    result = values[0]
    for value in values[1:]:
        result = operation('multiply', result, value)
    return result


class ExactComparisons(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.ws = Workspace(self.root, self.root)

    def test_nested_decimal_arithmetic_and_legacy_behavior(self):
        left = operation('add', literal(.1), literal(.2))
        self.assertTrue(evaluate(compare(left, literal(.3)), self.ws, 'source'))
        self.assertFalse(evaluate(compare(left, literal(.3), exact=False), self.ws, 'source'))

    def test_number_wrapper_does_not_round_nested_arithmetic(self):
        left = number(number(operation('add', literal(.1), literal(.2))))
        self.assertTrue(evaluate(compare(left, literal(.3)), self.ws, 'source'))

    def test_text_precision_survives_explicit_number_parsing(self):
        a = number(literal('1.00000000000000000001'))
        b = number(literal('1.00000000000000000000'))
        self.assertTrue(evaluate(compare(a, b, 'gt'), self.ws, 'source'))
        self.assertTrue(evaluate(compare(a, b, exact=False), self.ws, 'source'))

    def test_dimensionless_equality_differs_from_equal_rounded_reports(self):
        field = lambda key: number({'op': 'field', 'path': key})
        # Cross-multiply rho*v*L/eta against the model's same expression.
        left = product([field('rho'), field('v'), field('length'), literal(.001)])
        right = product([literal(1000), literal(2), literal(.1), field('eta')])
        expr = compare(left, right)
        row = {'rho': '1.2', 'v': '5', 'length': '0.6', 'eta': '0.000018'}
        self.assertTrue(row_value(expr, row))
        row['eta'] = '0.000018000009'
        self.assertFalse(row_value(expr, row))
        self.assertEqual(round(1.2 * 5 * .6 / float(row['eta'])), 200000)

    def test_rational_division_and_all_six_comparisons(self):
        third = operation('divide', literal(1), literal(3))
        larger = number(literal('0.3333333333333333333334'))
        expected = {'eq': False, 'ne': True, 'lt': True, 'lte': True, 'gt': False, 'gte': False}
        for relation, result in expected.items():
            self.assertEqual(evaluate(compare(third, larger, relation), self.ws, 'source'), result)

    def test_exact_top_level_sum_preserves_source_digits(self):
        atomic_json(self.root / 'rows.json', [{'value': '0.1'}, {'value': '0.2'}])
        total = {'op': 'sum', 'of': {'op': 'rows', 'file': 'rows.json'}, 'field': 'value'}
        self.assertTrue(evaluate(compare(total, literal(.3)), self.ws, 'source'))
        atomic_json(self.root / 'rows.json', [{'value': '0.1'}, {'value': '0.20000000000000000001'}])
        self.assertTrue(evaluate(compare(total, literal(.3), 'gt'), self.ws, 'source'))

    def test_formatted_source_decimals_and_ranges_remain_explicit(self):
        a = number(literal('USD 1,000.00000000000000000001'))
        self.assertTrue(evaluate(compare(a, literal(1000), 'gt'), self.ws, 'source'))
        lower = {'op': 'range_bound', 'of': literal('0.10000000000000000001-0.2'), 'bound': 'lower'}
        self.assertTrue(evaluate(compare(lower, literal(.1), 'gt'), self.ws, 'source'))

    def test_bad_inputs_and_division_by_zero_remain_grader_faults(self):
        for value in (True, None, float('inf'), 'NaN', '3 or 4', '2 metres'):
            with self.subTest(value=value), self.assertRaises(CheckError):
                evaluate(compare(literal(value), literal(1)), self.ws, 'source')
        with self.assertRaisesRegex(CheckError, 'division by zero'):
            evaluate(compare(operation('divide', literal(1), literal(0)), literal(1)), self.ws, 'source')

    def test_invalid_modes_fail_static_and_runtime_validation(self):
        for edits in ({'mode': 'approximate'}, {'mode': 'exact', 'value_type': 'date'},
                      {'mode': 'exact', 'value_type': 'string'}):
            expr = {**compare(literal(1), literal(1)), **edits}
            errors = []; _walk(expr, 'target', set(), errors); self.assertTrue(errors)
            errors = []; _walk_row(expr, 'row', errors); self.assertTrue(errors)
            with self.assertRaises(CheckError): evaluate(expr, self.ws, 'source')

    def test_previously_computed_values_are_not_silently_reinterpreted(self):
        expr = compare({'op': 'field', 'path': 'already_computed'}, literal(.3))
        self.assertFalse(row_value(expr, {'already_computed': .1 + .2}))

    def test_intentional_rounding_inside_comparison_keeps_its_meaning(self):
        rounded = {'op': 'round', 'mode': 'half_up', 'places': 0,
                   'of': operation('divide', literal(1999999), literal(10))}
        self.assertTrue(evaluate(compare(rounded, literal(200000)), self.ws, 'source'))

    def test_exported_comparison_and_source_change(self):
        bundle = synthetic_bundle(self.root / 'bundle')
        atomic_json(bundle / 'environment/files/decimals.json', {'a': '0.1', 'b': '0.2', 'c': '0.3'})
        spec = json.loads((bundle / 'authoring/spec.json').read_text())
        source = lambda key: number({'op': 'field', 'file': 'decimals.json', 'path': key})
        expr = compare(operation('add', source('a'), source('b')), source('c'))
        schema = spec['outputs'][0]['schema']
        schema['properties']['equal'] = {'type': 'boolean'}; schema['required'].append('equal')
        spec['solution']['summary.json']['equal'] = True
        spec['checks'].append({'id': 'exact_equality', 'kind': 'objective', 'weight': 1,
            'basis': 'Compare the exact declared decimal sum with c; do not round to report equality.',
            'assertion': 'equals', 'target': expr,
            'actual': {'op': 'field', 'file': 'summary.json', 'path': 'equal'}})
        build(spec, bundle)
        submitted = self.root / 'submitted'
        atomic_json(submitted / 'summary.json', spec['solution']['summary.json'])
        self.assertEqual(exported_grade(bundle, submitted, '01-summary')['reward'], 1)
        atomic_json(bundle / 'environment/files/decimals.json', {'a': '0.1', 'b': '0.2', 'c': '0.30000000000000000001'})
        build(spec, bundle)
        stale = exported_grade(bundle, submitted, '01-summary')
        self.assertFalse(stale['checks']['exact_equality']['passed'])
        self.assertFalse(stale['guardrails_violated'])
        corrected = copy.deepcopy(spec['solution']['summary.json']); corrected['equal'] = False
        atomic_json(submitted / 'summary.json', corrected)
        self.assertEqual(exported_grade(bundle, submitted, '01-summary')['reward'], 1)


if __name__ == '__main__':
    unittest.main(verbosity=2)
