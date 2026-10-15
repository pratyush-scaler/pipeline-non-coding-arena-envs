"""Shared source policies remain live in row decisions and exported controls."""
import copy
import json
from pathlib import Path
import tempfile
import unittest

from pipeline.artifacts import atomic_json
from pipeline.author.build import build
from pipeline.author.checks import CheckError, Workspace, evaluate
from pipeline.author.designer import _expression_nodes
from pipeline.author.validate import _walk
from pipeline.source_controls import run as source_controls
from pipeline.tests.test_production import synthetic_bundle


def bound_orders():
    return {'op': 'bind_rows', 'of': {'op': 'rows', 'file': 'orders.json'},
            'fields': {'policy_min_pct': {'op': 'field', 'file': 'policy.json', 'path': 'minimum'}}}


def decisions():
    return {'op': 'derive_rows', 'of': bound_orders(), 'fields': {
        'id': {'op': 'field', 'path': 'id'},
        'eligible': {'op': 'compare', 'value_type': 'number', 'comparison': 'gte',
            'a': {'op': 'multiply', 'a': {'op': 'field', 'path': 'received'},
                  'b': {'op': 'literal', 'value': 100, 'why': 'Percentage scale.'}},
            'b': {'op': 'multiply', 'a': {'op': 'field', 'path': 'price'},
                  'b': {'op': 'field', 'path': 'policy_min_pct'}}}}}


class SourcePolicyBindings(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.orders = [{'id': 'A', 'received': 6500, 'price': 10000},
                       {'id': 'B', 'received': 7000, 'price': 10000}]

    def stage(self, root, minimum=70, orders=None):
        atomic_json(root / 'policy.json', {'minimum': minimum})
        atomic_json(root / 'orders.json', self.orders if orders is None else orders)

    def test_policy_change_moves_decisions_without_changing_order_data(self):
        self.stage(self.root, orders=[*self.orders,
            {'id': 'near', 'received': 6995, 'price': 10000}, self.orders[0]])
        ws = Workspace(self.root, self.root)
        before = evaluate(decisions(), ws, 'source')
        self.assertEqual(before, [{'id': 'A', 'eligible': False}, {'id': 'B', 'eligible': True},
                                  {'id': 'near', 'eligible': False}, {'id': 'A', 'eligible': False}])
        atomic_json(self.root / 'policy.json', {'minimum': 60})
        after = evaluate(decisions(), ws, 'source')
        self.assertEqual([r['id'] for r in after], ['A', 'B', 'near', 'A'])
        self.assertTrue(all(r['eligible'] for r in after))
        self.assertNotIn('policy_min_pct', json.loads((self.root / 'orders.json').read_text())[0])

    def test_bindings_keep_the_callers_read_role(self):
        source, submitted = self.root / 'source', self.root / 'submitted'
        self.stage(source, minimum=60)
        self.stage(submitted, minimum=80)
        ws = Workspace(source, submitted)
        self.assertTrue(all(r['eligible'] for r in evaluate(decisions(), ws, 'source')))
        self.assertFalse(any(r['eligible'] for r in evaluate(decisions(), ws, 'submitted')))

    def test_collisions_and_invalid_binding_shapes_fail(self):
        self.stage(self.root)
        ws = Workspace(self.root, self.root)
        expression = bound_orders()
        expression['fields'] = {'id': expression['fields']['policy_min_pct']}
        with self.assertRaisesRegex(CheckError, 'overwrite'):
            evaluate(expression, ws, 'source')
        for fields in [{}, {'bad.name': {'op': 'field', 'file': 'policy.json', 'path': 'minimum'}}]:
            expression['fields'] = fields
            errors = []
            _walk(expression, 'target', {'orders.json', 'policy.json'}, errors)
            self.assertTrue(errors)
            with self.assertRaises(CheckError):
                evaluate(expression, ws, 'source')
        atomic_json(self.root / 'policy.json', {'minimum': [60, 70]})
        with self.assertRaisesRegex(CheckError, 'scalars'):
            evaluate(bound_orders(), ws, 'source')
        atomic_json(self.root / 'orders.json', [1, 2])
        with self.assertRaises((CheckError, ValueError)):
            evaluate(bound_orders(), ws, 'source')

    def test_preflight_walks_bound_source_expressions_including_empty_input(self):
        expression = bound_orders()
        expression['fields']['policy_min_pct']['file'] = 'undeclared.json'
        errors = []
        _walk(expression, 'target', {'orders.json', 'policy.json'}, errors)
        self.assertTrue(any('undeclared.json' in e for e in errors))
        self.assertTrue(any(n.get('file') == 'undeclared.json' for n in _expression_nodes(expression)))
        self.stage(self.root, orders=[])
        with self.assertRaises(CheckError):
            evaluate(expression, Workspace(self.root, self.root), 'source')

    def test_exported_source_counterfactual_rejects_stale_eligibility(self):
        bundle = synthetic_bundle(self.root / 'bundle')
        self.stage(bundle / 'environment/files')
        spec = json.loads((bundle / 'authoring/spec.json').read_text())
        schema = spec['outputs'][0]['schema']
        schema['required'].append('eligibility')
        schema['properties']['eligibility'] = {'type': 'array', 'items': {
            'type': 'object', 'properties': {'id': {'type': 'string'}, 'eligible': {'type': 'boolean'}},
            'required': ['id', 'eligible'], 'additionalProperties': False}}
        spec['solution']['summary.json']['eligibility'] = [
            {'id': 'A', 'eligible': False}, {'id': 'B', 'eligible': True}]
        spec['checks'].append({'id': 'eligibility', 'kind': 'objective', 'weight': 1,
            'basis': 'Apply the current policy minimum to the unrounded payment amounts.',
            'assertion': 'multiset_equals', 'actual': {
                'op': 'field', 'file': 'summary.json', 'path': 'eligibility'}, 'target': decisions()})
        spec['quality'] = {'semantic_checks': ['eligibility'], 'source_cases': [{
            'id': 'lower-policy', 'reason': 'At a 60% minimum, both existing payments qualify.',
            'changes': ['eligibility'],
            'source_patches': [{'file': 'policy.json', 'before': '70', 'after': '60'}],
            'patches': [{'file': 'summary.json', 'path': 'eligibility.0.eligible', 'value': True}]}]}
        build(spec, bundle)
        checks = {c['id']: c for c in json.loads((bundle / 'tests/checks.json').read_text())['checks']}
        result = source_controls(bundle, spec, copy.deepcopy(spec['solution']), checks, self.root / 'controls')
        self.assertEqual(result['errors'], [])
        stale = next(iter(result['results']['lower-policy']['stale'].values()))
        self.assertFalse(stale['checks']['eligibility']['passed'])
        self.assertFalse(stale['checks']['eligibility'].get('gated_out', False))
        self.assertEqual(stale['guardrails_violated'], [])


if __name__ == '__main__':
    unittest.main()
