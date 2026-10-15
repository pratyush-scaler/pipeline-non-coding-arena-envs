"""Typed uncertainty remains distinct from missing or malformed submissions."""
import json
from pathlib import Path
import tempfile
import unittest

from pipeline.artifacts import atomic_json
from pipeline.author.build import build
from pipeline.author.contracts import ContractError, schema_errors, schema_problems, schema_at
from pipeline.author.designer import verify_solution
from pipeline.evaluate import exported_grade
from pipeline.tests.test_production import synthetic_bundle


class NullableScalarContracts(unittest.TestCase):
    def test_each_scalar_accepts_null_and_its_own_values(self):
        for kind, value in [('number', 1.25), ('integer', 2), ('boolean', False), ('string', 'known')]:
            for order in ([kind, 'null'], ['null', kind]):
                with self.subTest(kind=order):
                    schema = {'type': order}
                    self.assertEqual(schema_problems(schema), [])
                    self.assertEqual(schema_errors(value, schema), [])
                    self.assertEqual(schema_errors(None, schema), [])

    def test_numeric_nullable_types_reject_bool_text_and_nonfinite_values(self):
        for kind in ('integer', 'number'):
            for value in (True, False, 'null', '', '3', float('nan'), float('inf'), [], {}):
                with self.subTest(kind=kind, value=value):
                    self.assertTrue(schema_errors(value, {'type': [kind, 'null']}))

    def test_non_null_constraints_remain_enforced(self):
        numeric = {'type': ['number', 'null'], 'minimum': 0, 'maximum': 1}
        string = {'type': ['null', 'string'], 'minLength': 2, 'pattern': '^A'}
        self.assertTrue(schema_errors(-1, numeric))
        self.assertTrue(schema_errors(2, numeric))
        self.assertTrue(schema_errors('A', string))
        self.assertTrue(schema_errors('BA', string))
        self.assertEqual(schema_errors(None, numeric), [])
        self.assertEqual(schema_errors(None, string), [])
        self.assertEqual(schema_errors('AB', string), [])

    def test_enum_can_exclude_or_include_null(self):
        schema = {'type': ['boolean', 'null'], 'enum': [False]}
        self.assertTrue(schema_errors(None, schema))
        self.assertTrue(schema_errors(True, schema))
        self.assertEqual(schema_errors(False, schema), [])
        schema['enum'].append(None)
        self.assertEqual(schema_errors(None, schema), [])

    def test_other_unions_stay_unsupported(self):
        for union in ([], ['number'], ['null', 'null'], ['number', 'string'],
                      ['null', 'number', 'string'], ['object', 'null'], ['array', 'null'],
                      [None, 'null'], [['number'], 'null']):
            with self.subTest(union=union):
                self.assertTrue(schema_problems({'type': union}))
                with self.assertRaises(ContractError):
                    schema_errors(None, {'type': union})

    def test_invalid_keywords_and_bounds_still_fail_schema_validation(self):
        for extra in ({'minimum': float('nan')}, {'minimum': 3, 'maximum': 2},
                      {'properties': {}}, {'unsupported': True}):
            with self.subTest(extra=extra):
                self.assertTrue(schema_problems({'type': ['number', 'null'], **extra}))

    def test_required_null_is_not_a_missing_field(self):
        schema = {'type': 'object', 'properties': {'value': {'type': ['number', 'null']}},
                  'required': ['value'], 'additionalProperties': False}
        self.assertEqual(schema_errors({'value': None}, schema), [])
        self.assertTrue(schema_errors({}, schema))
        self.assertEqual(schema_at(schema, 'value'), schema['properties']['value'])


class NullableScalarExport(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.bundle = synthetic_bundle(self.root)
        self.spec = json.loads((self.bundle / 'authoring/spec.json').read_text())
        atomic_json(self.bundle / 'environment/files/evidence.json', [
            {'id': 'known', 'confirmed': True, 'value': 3},
            {'id': 'unknown', 'confirmed': False, 'value': 4}])
        self.spec['outputs'][0]['schema']['properties']['estimates'] = {
            'type': 'array', 'items': {'type': 'object', 'properties': {
                'id': {'type': 'string'}, 'estimate': {'type': ['number', 'null']}},
                'required': ['id', 'estimate'], 'additionalProperties': False}}
        self.spec['outputs'][0]['schema']['required'].append('estimates')
        self.spec['solution']['summary.json']['estimates'] = [
            {'id': 'known', 'estimate': 3}, {'id': 'unknown', 'estimate': None}]
        self.spec['checks'].append({'id': 'estimates', 'kind': 'objective', 'weight': 1,
            'basis': 'Report each confirmed source value; report explicit null when evidence is unconfirmed.',
            'assertion': 'multiset_equals', 'actual': {'op': 'field', 'file': 'summary.json', 'path': 'estimates'},
            'target': {'op': 'derive_rows', 'of': {'op': 'rows', 'file': 'evidence.json'}, 'fields': {
                'id': {'op': 'field', 'path': 'id'}, 'estimate': {'op': 'if',
                    'where': {'field': 'confirmed', 'eq': True},
                    'then': {'op': 'field', 'path': 'value'},
                    'else': {'op': 'literal', 'value': None, 'why': 'The public contract requires null for unconfirmed evidence.'}}}}})
        build(self.spec, self.bundle)

    def grade(self, estimates):
        value = dict(self.spec['solution']['summary.json'], estimates=estimates)
        submitted = self.root / 'submitted'
        atomic_json(submitted / 'summary.json', value)
        return exported_grade(self.bundle, submitted, '01-summary')

    def test_export_accepts_source_derived_explicit_null(self):
        result = self.grade(self.spec['solution']['summary.json']['estimates'])
        self.assertEqual(result['reward'], 1)
        self.assertFalse(result['contract_errors'])

    def test_wrong_uncertainty_is_not_excused_by_nullable_schema(self):
        for estimates in ([{'id': 'known', 'estimate': None}, {'id': 'unknown', 'estimate': None}],
                          [{'id': 'known', 'estimate': 3}, {'id': 'unknown', 'estimate': 4}]):
            result = self.grade(estimates)
            self.assertFalse(result['contract_errors'])
            self.assertFalse(result['checks']['estimates']['passed'])

    def test_text_null_or_omission_fails_the_output_contract(self):
        for row in ({'id': 'unknown', 'estimate': 'null'}, {'id': 'unknown'}):
            result = self.grade([{'id': 'known', 'estimate': 3}, row])
            self.assertTrue(result['contract_errors'])

    def test_source_change_changes_the_uncertainty_decision(self):
        atomic_json(self.bundle / 'environment/files/evidence.json', [
            {'id': 'known', 'confirmed': True, 'value': 3},
            {'id': 'unknown', 'confirmed': True, 'value': 4}])
        build(self.spec, self.bundle)
        self.assertFalse(self.grade(self.spec['solution']['summary.json']['estimates'])['checks']['estimates']['passed'])
        self.assertEqual(self.grade([{'id': 'known', 'estimate': 3}, {'id': 'unknown', 'estimate': 4}])['reward'], 1)

    def test_author_reference_accepts_declared_scalar_uncertainty(self):
        from pipeline.author import oracle
        oracle.write(oracle.project(self.bundle / 'environment/files', self.spec['projections']),
                     self.bundle / 'authoring/draft-derived')
        schema = self.spec['outputs'][0]['schema']
        schema['properties']['unconfirmed_estimate'] = {'type': ['number', 'null']}
        schema['required'].append('unconfirmed_estimate')
        self.spec['solution']['summary.json']['unconfirmed_estimate'] = None
        self.spec['checks'].append({'id': 'unconfirmed_estimate', 'kind': 'objective', 'weight': .1,
            'basis': 'An unconfirmed estimate must be null under the public uncertainty rule.',
            'assertion': 'equals',
            'actual': {'op': 'field', 'file': 'summary.json', 'path': 'unconfirmed_estimate'},
            'target': {'op': 'only', 'of': {'op': 'pluck',
                'of': {'op': 'filter', 'of': self.spec['checks'][-1]['target'],
                       'where': {'field': 'id', 'eq': 'unknown'}}, 'field': 'estimate'}}})
        self.assertEqual(verify_solution(self.spec, self.bundle), [])
        # Without an explicit output contract, a null may still be a missing
        # projection. Preserve the old rejection for legacy untyped references.
        self.spec.pop('outputs')
        self.assertTrue(any('contains nulls' in e for e in verify_solution(self.spec, self.bundle)))


if __name__ == '__main__':
    unittest.main(verbosity=2)
