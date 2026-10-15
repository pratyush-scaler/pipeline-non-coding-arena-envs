from copy import deepcopy
from contextlib import ExitStack
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch
from pipeline.artifacts import atomic_json
from pipeline.author import agent_designer as agent

class ValidationReuse(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.bundle = Path(temp.name)
        self.fixture = self.bundle / 'environment/files'
        self.fixture.mkdir(parents=True)
        self.source = self.fixture / 'source.txt'
        self.source.write_text('Approved source facts.')
        self.trace = {'messages': []}
        self.handlers = agent._handlers(self.bundle, SimpleNamespace(session_id='source', seed_index=0), self.trace)
        self.spec = {'instruction': 'A professional assignment.', 'checks': [{'id': 'core'}]}
        stack = ExitStack()
        self.addCleanup(stack.close)
        self.production = stack.enter_context(patch('pipeline.author.quality.production_problems', return_value=[]))
        self.validate = stack.enter_context(patch.object(agent, 'validate', return_value=[]))
        stack.enter_context(patch('pipeline.ledger.faithfulness.citation_problems', return_value=[]))
        stack.enter_context(patch('pipeline.ledger.grounding.alignment_problems', return_value=[]))
        self.derive = stack.enter_context(patch.object(agent, 'derive_solution', return_value={'answer.json': {'rows': [1]}}))
        stack.enter_context(patch.object(agent, 'verify_solution', return_value=[]))
        self.policy = stack.enter_context(patch('pipeline.artifacts.policy_identity', return_value='policy-v1'))

    def check(self, spec=None):
        return self.handlers['check_spec'](self.spec if spec is None else spec)

    def test_identical_submit_uses_clean_result_and_copies_nested_reference(self):
        result = self.check()
        result['reference_answer']['answer.json']['rows'].append('corrupted caller object')
        emitted = deepcopy(self.spec)
        emitted['source'] = {'session_id': 'source', 'seed_index': 0, 'tier': 4}
        again = self.check(emitted)
        self.assertTrue(again['reused_exact_validation'])
        self.assertEqual(again['reference_answer']['answer.json']['rows'], [1])
        self.assertEqual(self.derive.call_count, 1)
        self.assertEqual(self.validate.call_count, 1)

    def test_source_spec_provenance_trace_and_policy_each_invalidate(self):
        self.check()
        changes = [lambda: self.spec['checks'][0].update(id='different'),
                   lambda: self.source.write_text('Different source facts.'),
                   lambda: atomic_json(self.bundle / 'provenance/source.json', {'new': True}),
                   lambda: self.trace['messages'].append({'role': 'user', 'content': 'new evidence'}),
                   lambda: setattr(self.policy, 'return_value', 'policy-v2')]
        for index, change in enumerate(changes, 2):
            change()
            result = self.check()
            self.assertTrue(result['clean'])
            self.assertFalse(result.get('reused_exact_validation', False))
            self.assertEqual(self.validate.call_count, index)

    def test_failed_validation_is_not_cached(self):
        self.validate.return_value = ['missing professional obligation']
        self.assertFalse(self.check()['clean'])
        self.validate.return_value = []
        self.assertTrue(self.check()['clean'])
        self.assertEqual(self.validate.call_count, 2)

    def test_restart_reuses_only_unchanged_successful_validation(self):
        self.assertTrue(self.check()['clean'])
        def restart():
            self.handlers = agent._handlers(self.bundle,
                SimpleNamespace(session_id='source', seed_index=0), self.trace)
        restart()
        self.assertTrue(self.check()['reused_exact_validation'])
        self.assertEqual(self.validate.call_count, 1)
        (self.bundle / 'verification/spec-validation.json').write_text('{"clean": true, "problems": []}')
        restart()
        self.assertTrue(self.check()['clean'])
        self.assertEqual(self.validate.call_count, 2)
        self.source.write_text('A changed source invalidates the retained validation')
        restart()
        self.assertTrue(self.check()['clean'])
        self.assertEqual(self.validate.call_count, 3)

    def test_validator_mutations_do_not_change_staged_draft(self):
        before = deepcopy(self.spec)
        def compile_in_place(draft, bundle):
            draft['checks'][0]['compiled'] = True
            return []
        self.validate.side_effect = compile_in_place
        self.assertTrue(self.check()['clean'])
        self.assertEqual(self.spec, before)
        self.assertTrue(self.check()['reused_exact_validation'])

    def test_source_change_during_validation_is_not_clean_or_cached(self):
        def change_source(*args):
            self.source.write_text(f'Concurrent changed source {self.validate.call_count}.')
            return []
        self.validate.side_effect = change_source
        result = self.check()
        self.assertFalse(result['clean'])
        self.assertIn('changed during execution', ' '.join(result['problems']))
        self.validate.side_effect = None
        self.assertTrue(self.check()['clean'])
        # A change on every pass is reported after one re-check (two passes), then a clean pass.
        self.assertEqual(self.validate.call_count, 3)

    def test_one_policy_change_during_validation_is_rechecked_not_reported(self):
        # 2026-10-02: a pipeline sync mid-submit ended a-016's lineage on this finding.
        calls = []
        def sync_once(*args):
            calls.append(1)
            if len(calls) == 1:
                self.policy.return_value = 'policy-v2'
            return []
        self.validate.side_effect = sync_once
        result = self.check()
        self.assertTrue(result['clean'], result['problems'])
        self.assertEqual(self.validate.call_count, 2)
