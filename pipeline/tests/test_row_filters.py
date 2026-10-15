"""Malformed predicates are contract errors, never match-all decisions."""
import json
from pathlib import Path
import tempfile
import unittest

from pipeline.author.checks import CheckError, Workspace, evaluate
from pipeline.author.validate import _walk


class RowFilterContracts(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        (self.root / 'rows.json').write_text(json.dumps([
            {'id': 'A', 'status': 'approved', 'amount': '10', 'flag': True},
            {'id': 'B', 'status': 'rejected', 'amount': 20, 'flag': False}]))
        (self.root / 'empty.json').write_text('[]')
        self.ws = Workspace(self.root, self.root)

    def rows(self, where, file='rows.json'):
        return {'op': 'rows', 'file': file, 'where': where}

    def issues(self, expression):
        errors = []
        _walk(expression, 'check.target', {'rows.json', 'empty.json'}, errors)
        return errors

    def evaluate(self, expression):
        return evaluate(expression, self.ws, 'source')

    def test_comparison_without_field_cannot_become_match_all(self):
        expression = self.rows({'eq': 'approved'})
        self.assertTrue(self.issues(expression))
        with self.assertRaisesRegex(CheckError, 'field'):
            self.evaluate(expression)

    def test_field_without_predicate_is_not_a_presence_check(self):
        expression = self.rows({'field': 'status'})
        self.assertTrue(self.issues(expression))
        with self.assertRaisesRegex(CheckError, 'predicate'):
            self.evaluate(expression)

    def test_groups_cannot_silently_discard_each_other_or_a_field(self):
        for where in [
            {'all': [{'field': 'status', 'eq': 'approved'}],
             'any': [{'field': 'status', 'eq': 'rejected'}]},
            {'all': [], 'field': 'status', 'eq': 'approved'},
            {'any': [], 'field': 'status', 'eq': 'rejected'},
        ]:
            with self.subTest(where=where):
                self.assertTrue(self.issues(self.rows(where)))
                with self.assertRaises(CheckError):
                    self.evaluate(self.rows(where))

    def test_invalid_predicate_is_rejected_even_without_source_rows(self):
        for expression in [self.rows({'eq': 'approved'}, 'empty.json'),
            {'op': 'filter', 'of': {'op': 'rows', 'file': 'empty.json'}, 'where': {'eq': 'approved'}}]:
            with self.subTest(expression=expression), self.assertRaises(CheckError):
                self.evaluate(expression)

    def test_hidden_invalid_branch_is_checked_before_short_circuiting(self):
        for where in [
            {'all': [{'field': 'status', 'eq': 'nonexistent'}, {'eq': 'approved'}]},
            {'any': [{}, {'unknown': 'ignored'}]},
        ]:
            with self.subTest(where=where):
                self.assertTrue(self.issues(self.rows(where)))
                with self.assertRaises(CheckError):
                    self.evaluate(self.rows(where))

    def test_nested_groups_validate_and_select_the_correct_row(self):
        expression = self.rows({'all': [
            {'any': [{'field': 'status', 'eq': 'approved'}, {'field': 'amount', 'gt': 25}]},
            {'field': 'amount', 'gte': 10, 'lte': 15}]})
        self.assertEqual(self.issues(expression), [])
        self.assertEqual([r['id'] for r in self.evaluate(expression)], ['A'])

    def test_row_if_uses_the_same_static_and_runtime_contract(self):
        expression = {'op': 'derive_rows', 'of': {'op': 'rows', 'file': 'rows.json'},
            'fields': {'eligible': {'op': 'if', 'where': {'eq': 'approved'},
                'then': {'op': 'literal', 'value': True, 'why': 'Eligible outcome.'},
                'else': {'op': 'literal', 'value': False, 'why': 'Ineligible outcome.'}}}}
        self.assertTrue(self.issues(expression))
        with self.assertRaises(CheckError):
            self.evaluate(expression)
        expression['fields']['eligible']['where'] = {'field': 'status', 'eq': 'approved'}
        self.assertEqual(self.issues(expression), [])
        self.assertEqual(self.evaluate(expression), [{'eligible': True}, {'eligible': False}])

    def test_only_objects_and_list_valued_groups_are_accepted(self):
        for where in [None, False, 0, '', [], {'all': None}, {'any': {}},
                      {'all': [None]}, {'field': 3, 'eq': 'approved'},
                      {'field': '', 'eq': 'approved'}, {'op': 'eq', 'field': 'status', 'value': 'approved'}]:
            with self.subTest(where=where):
                self.assertTrue(self.issues(self.rows(where)))
                with self.assertRaises(CheckError):
                    self.evaluate(self.rows(where))

    def test_presence_and_regex_parameters_have_explicit_types(self):
        for where in [{'field': 'status', 'present': 'false'},
                      {'field': 'status', 'present': 1},
                      {'field': 'status', 'matches': 1},
                      {'field': 'status', 'matches': '['}]:
            with self.subTest(where=where):
                self.assertTrue(self.issues(self.rows(where)))
                with self.assertRaises(CheckError):
                    self.evaluate(self.rows(where))

    def test_non_numeric_thresholds_are_rejected_on_empty_data_too(self):
        for threshold in [True, None, 'tomorrow', float('inf')]:
            expression = self.rows({'field': 'amount', 'gt': threshold}, 'empty.json')
            with self.subTest(threshold=threshold):
                self.assertTrue(self.issues(expression))
                with self.assertRaises(CheckError):
                    self.evaluate(expression)

    def test_documented_identity_predicates_keep_their_boolean_meaning(self):
        self.assertEqual(len(self.evaluate({'op': 'rows', 'file': 'rows.json'})), 2)
        for where, expected in [({}, 2), ({'all': []}, 2), ({'any': []}, 0)]:
            with self.subTest(where=where):
                self.assertEqual(self.issues(self.rows(where)), [])
                self.assertEqual(len(self.evaluate(self.rows(where))), expected)

    def test_valid_normalization_membership_presence_and_ranges_are_preserved(self):
        for where, ids in [
            ({'field': 'status', 'in': ['APPROVED']}, ['A']),
            ({'field': 'status', 'not_in': ['approved']}, ['B']),
            ({'field': 'missing', 'present': False}, ['A', 'B']),
            ({'field': 'status', 'matches': '^app'}, ['A']),
            ({'field': 'amount', 'gte': '10', 'lt': 20}, ['A']),
            ({'field': 'flag', 'eq': True}, ['A']),
            ({'field': 'flag', 'eq': 1}, []),
        ]:
            with self.subTest(where=where):
                self.assertEqual(self.issues(self.rows(where)), [])
                self.assertEqual([r['id'] for r in self.evaluate(self.rows(where))], ids)


if __name__ == '__main__':
    unittest.main()
