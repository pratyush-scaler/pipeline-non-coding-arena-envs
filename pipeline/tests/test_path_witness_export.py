"""A path witness works through the shipped grader and source controls."""
import json
from pathlib import Path
import tempfile
import unittest

from pipeline.artifacts import atomic_json
from pipeline.author.build import build
from pipeline.author.checks import Check, CheckError, Workspace, run_check
from pipeline.author.designer import verify_solution
from pipeline.author.validate import validate
from pipeline.evaluate import exported_grade
from pipeline.verify_shipped import run_reference
from pipeline.source_controls import run as source_controls
from pipeline.tests.test_path_witness import graph, node, edge, answer
from pipeline.tests.test_production import synthetic_bundle


class PathWitnessExport(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.bundle = synthetic_bundle(self.root / 'bundle')
        self.problem = graph([node('s'), node('a', '.31', '4.2'), node('b', '.24', '3.05'),
                              node('m'), node('t', '.2')],
                             [edge('s', 'a'), edge('s', 'b'), edge('a', 'm'),
                              edge('b', 'm'), edge('m', 't')])
        atomic_json(self.bundle / 'environment/files/graph.json', self.problem)
        self.spec = json.loads((self.bundle / 'authoring/spec.json').read_text())
        guard = self.spec['checks'][0]
        self.check = {'id': 'plan', 'kind': 'objective', 'weight': 1,
                      'basis': 'Maximize minimum capacity, then minimize total node and edge cost; accept every tied optimum.',
                      'assertion': 'optimal_path',
                      'actual': {'op': 'field', 'file': 'plan.json', 'path': 'plan'},
                      'target': {'op': 'field', 'file': 'graph.json', 'path': ''}}
        self.spec['checks'] = [guard, self.check]
        self.spec['projections'] = []
        self.spec['solution'] = {'plan.json': {'plan': answer(['s', 'b', 'm', 't'], .2, 3.05)}}
        plan_schema = {'type': 'object', 'properties': {
            'feasible': {'type': 'boolean'},
            'path': {'type': 'array', 'items': {'type': 'string'}, 'maxItems': 256},
            'bottleneck': {'type': 'number'}, 'cost': {'type': 'number'}},
            'required': ['feasible', 'path'], 'additionalProperties': False}
        self.spec['outputs'] = [{'file': 'plan.json', 'step': 1, 'schema': {
            'type': 'object', 'properties': {'plan': plan_schema},
            'required': ['plan'], 'additionalProperties': False}}]
        self.spec['quality'] = {'semantic_checks': ['plan'], 'source_cases': [{
            'id': 'cheaper-alternative', 'reason': 'The public cost change makes the other complete path optimal.',
            'changes': ['plan'], 'source_patches': [{
                'file': 'graph.json', 'before': '"cost": "4.2"', 'after': '"cost": "1.05"'}],
            'patches': [{'file': 'plan.json', 'path': 'plan.path', 'value': ['s', 'a', 'm', 't']},
                        {'file': 'plan.json', 'path': 'plan.cost', 'value': 1.05}]}]}
        build(self.spec, self.bundle)

    def grade(self, value):
        submitted = self.root / 'submitted'
        atomic_json(submitted / 'plan.json', {'plan': value})
        return exported_grade(self.bundle, submitted, '01-summary')

    def test_reference_and_alternative_optimal_witnesses_through_export(self):
        self.assertEqual(self.grade(answer(['s', 'b', 'm', 't'], .2, 3.05))['reward'], 1)
        self.problem['nodes'][1]['cost'] = '3.05'
        atomic_json(self.bundle / 'environment/files/graph.json', self.problem)
        build(self.spec, self.bundle)
        for middle in ('a', 'b'):
            self.assertEqual(self.grade(answer(['s', middle, 'm', 't'], .2, 3.05))['reward'], 1)

    def test_shipped_reference_derives_a_path_not_the_unsolved_graph(self):
        self.assertEqual(run_reference(self.bundle)['problems'], [])
        self.problem['nodes'][1]['cost'] = '1.05'
        atomic_json(self.bundle / 'environment/files/graph.json', self.problem)
        build(self.spec, self.bundle)
        self.assertEqual(run_reference(self.bundle)['problems'], [])

    def test_wrong_routes_and_claims_fail_their_own_decision(self):
        for value in (answer(['s', 'a', 'm', 't'], .2, 4.2),
                      answer(['s', 'b', 't'], .2, 3.05),
                      answer(['s', 'b', 'm', 't'], .2, 0),
                      {'feasible': False, 'path': []}, {'feasible': True, 'path': []}):
            with self.subTest(value=value):
                result = self.grade(value)
                self.assertEqual(result['reward'], 0)
                self.assertFalse(result['checks']['plan']['passed'])
                self.assertFalse(result['guardrails_violated'])

    def test_missing_submission_does_not_pass(self):
        submitted = self.root / 'nothing'
        submitted.mkdir()
        self.assertEqual(exported_grade(self.bundle, submitted, '01-summary')['reward'], 0)

    def test_no_path_uses_the_existing_optional_field_contract(self):
        self.problem['edges'] = []
        atomic_json(self.bundle / 'environment/files/graph.json', self.problem)
        self.spec['solution'] = {'plan.json': {'plan': {'feasible': False, 'path': []}}}
        build(self.spec, self.bundle)
        result = self.grade({'feasible': False, 'path': []})
        self.assertEqual(result['reward'], 1)
        self.assertFalse(result['contract_errors'])

    def test_submitted_graph_cannot_override_the_source(self):
        fake = json.loads(json.dumps(self.problem))
        fake['nodes'][1]['cost'] = '1.05'
        atomic_json(self.root / 'submitted/graph.json', fake)
        self.assertEqual(self.grade(answer(['s', 'a', 'm', 't'], .2, 1.05))['reward'], 0)

    def test_tampered_witness_runtime_cannot_execute_on_the_host(self):
        marker = self.root / 'must-not-exist'
        runtime = self.bundle / 'tests/_arena_runtime/path_witness.py'
        runtime.write_text(f'from pathlib import Path\nPath({str(marker)!r}).touch()\n')
        with self.assertRaisesRegex(RuntimeError, 'unaudited'):
            self.grade(answer(['s', 'b', 'm', 't'], .2, 3.05))
        self.assertFalse(marker.exists())

    def test_bad_source_raises_before_missing_answer_is_scored(self):
        self.problem['edges'].append(edge('t', 's'))
        atomic_json(self.bundle / 'environment/files/graph.json', self.problem)
        with self.assertRaisesRegex(CheckError, 'acyclic'):
            run_check(Check(**self.check), Workspace(self.bundle / 'environment/files', self.root / 'missing'))

    def test_exported_source_control_rejects_the_stale_plan(self):
        checks = {c['id']: c for c in json.loads((self.bundle / 'tests/checks.json').read_text())['checks']}
        result = source_controls(self.bundle, self.spec, self.spec['solution'], checks, self.root / 'controls')
        self.assertEqual(result['errors'], [])
        case = result['results']['cheaper-alternative']
        self.assertEqual(case['corrected']['01-summary']['reward'], 1)
        self.assertFalse(case['stale']['01-summary']['checks']['plan']['passed'])

    def test_assertion_validates_and_does_not_invent_an_expected_path(self):
        self.assertEqual(Check(**self.check).validate(), [])
        self.assertNotIn('single-surface read-off', ' '.join(verify_solution(self.spec, self.bundle)))
        errors = validate(self.spec, self.bundle)
        self.assertFalse(any('unknown assertion' in error or 'target' in error for error in errors), errors)

    def test_copied_witness_probe_recognizes_any_optimal_tie(self):
        from pipeline.author.probes import _answer_lookup
        self.problem['nodes'][1]['cost'] = '3.05'
        source = self.bundle / 'environment/files'
        atomic_json(source / 'graph.json', self.problem)
        alternative = answer(['s', 'a', 'm', 't'], .2, 3.05)
        (source / 'leaked.md').write_text('```json\n' + json.dumps({'example': alternative}) + '\n```\n')
        probe = self.root / 'lookup'
        report = _answer_lookup(probe, [Check(**self.check)], Workspace(source, probe), source)
        self.assertEqual(report['readable_from_fixture']['plan']['value'], alternative)
        self.assertEqual(json.loads((probe / 'plan.json').read_text())['plan'], alternative)

    def test_a_stored_wrong_route_does_not_count_as_a_copied_answer(self):
        from pipeline.author.probes import _answer_lookup
        source = self.bundle / 'environment/files'
        atomic_json(source / 'claim.json', answer(['s', 'a', 'm', 't'], .2, 4.2))
        probe = self.root / 'lookup'
        report = _answer_lookup(probe, [Check(**self.check)], Workspace(source, probe), source)
        self.assertEqual(report['readable_from_fixture'], {})
        self.assertEqual(report['not_readable'], ['plan'])


if __name__ == '__main__':
    unittest.main(verbosity=2)
