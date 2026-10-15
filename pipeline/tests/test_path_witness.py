"""Independent exhaustive comparison and counterexamples for the prototype."""
from copy import deepcopy
from fractions import Fraction
import random
import unittest

from pipeline.author.path_witness import InvalidProblem, prepare, check_witness, decision_signature


def node(key, capacity=1, cost=0):
    return {'id': key, 'capacity': capacity, 'cost': cost}


def edge(src, dst, capacity=1, cost=0):
    return {'from': src, 'to': dst, 'capacity': capacity, 'cost': cost}


def graph(nodes, edges, start='s', end='t'):
    return dict(nodes=nodes, edges=edges, start=start, end=end)


def answer(path, capacity, cost):
    return {'feasible': True, 'path': path, 'bottleneck': capacity, 'cost': cost}


def exhaustive(problem):
    """Enumerate every path, independently of the two-pass implementation."""
    by_id = {n['id']: n for n in problem['nodes']}
    solutions = []
    def walk(path, capacity, cost):
        if path[-1] == problem['end']:
            solutions.append((tuple(path), capacity, cost))
            return
        for link in problem['edges']:
            if link['from'] != path[-1]:
                continue
            nxt = by_id[link['to']]
            walk([*path, nxt['id']],
                 min(capacity, Fraction(str(link['capacity'])), Fraction(str(nxt['capacity']))),
                 cost + Fraction(str(link['cost'])) + Fraction(str(nxt['cost'])))
    first = by_id[problem['start']]
    walk([problem['start']], Fraction(str(first['capacity'])), Fraction(str(first['cost'])))
    return solutions


class PathWitnessTests(unittest.TestCase):
    def bottleneck_problem(self):
        return graph([node('s'), node('a', '.31', '4.2'), node('b', '.24', '3.05'),
                      node('m'), node('t', '.2')],
                     [edge('s', 'a'), edge('s', 'b'), edge('a', 'm'),
                      edge('b', 'm'), edge('m', 't')])

    def test_later_bottleneck_erases_early_advantage(self):
        p = prepare(self.bottleneck_problem())
        self.assertEqual(p['optimum'], (Fraction('.2'), Fraction('3.05')))
        self.assertTrue(check_witness(p, answer(['s', 'b', 'm', 't'], '.2', '3.05'))[0])
        self.assertFalse(check_witness(p, answer(['s', 'a', 'm', 't'], '.2', '4.2'))[0])

    def test_all_equal_optima_are_accepted(self):
        g = self.bottleneck_problem()
        g['nodes'][1]['cost'] = '3.05'
        p = prepare(g)
        for middle in ('a', 'b'):
            self.assertTrue(check_witness(p, answer(['s', middle, 'm', 't'], '.2', '3.05'))[0])

    def test_exact_decimal_ties(self):
        g = graph([node('s'), node('a', cost='.1'), node('b', cost='.3'), node('t')],
                  [edge('s', 'a', cost='.2'), edge('a', 't'), edge('s', 'b'), edge('b', 't')])
        p = prepare(g)
        for middle in ('a', 'b'):
            self.assertTrue(check_witness(p, answer(['s', middle, 't'], 1, '.3'))[0])

    def test_topology_not_source_row_order_controls_the_answer(self):
        g = self.bottleneck_problem()
        expected = prepare(g)['optimum']
        g['nodes'].reverse()
        g['edges'].reverse()
        self.assertEqual(prepare(g)['optimum'], expected)

    def test_both_edge_and_node_metrics_count(self):
        g = graph([node('s', '.8', 1), node('t', '.6', 2)], [edge('s', 't', '.4', 3)])
        p = prepare(g)
        self.assertEqual(p['optimum'], (Fraction('.4'), Fraction(6)))
        self.assertTrue(check_witness(p, answer(['s', 't'], '.4', 6))[0])

    def test_unreachable_is_distinct_from_zero_capacity(self):
        g = graph([node('s'), node('t')], [])
        no = {'feasible': False, 'path': []}
        self.assertTrue(check_witness(prepare(g), no)[0])
        g['edges'] = [edge('s', 't', 0)]
        p = prepare(g)
        self.assertFalse(check_witness(p, no)[0])
        self.assertTrue(check_witness(p, answer(['s', 't'], 0, 0))[0])

    def test_start_equals_end_includes_its_node_metrics(self):
        p = prepare(graph([node('s', '.7', 2)], [], end='s'))
        self.assertTrue(check_witness(p, answer(['s'], '.7', 2))[0])

    def test_suboptimal_path_cannot_use_a_tolerance_to_pass(self):
        p = prepare(self.bottleneck_problem())
        self.assertFalse(check_witness(p, answer(['s', 'a', 'm', 't'], '.2', '3.05'), 100)[0])

    def test_reporting_tolerance_does_not_change_path_optimization(self):
        p = prepare(self.bottleneck_problem())
        a = answer(['s', 'b', 'm', 't'], '.20001', '3.05001')
        self.assertFalse(check_witness(p, a)[0])
        self.assertTrue(check_witness(p, a, '.0001')[0])

    def test_bad_submissions_are_failures(self):
        p = prepare(self.bottleneck_problem())
        bad = [None, {}, [], True,
               answer([], '.2', '3.05'), answer(['s', 't'], '.2', '3.05'),
               answer(['s', 'b', 'm', 'b', 't'], '.2', '3.05'),
               answer(['s', 'b', 'absent', 't'], '.2', '3.05'),
               answer(['s', 'b', 'm', 't'], True, '3.05'),
               answer(['s', 'b', 'm', 't'], '.2', float('nan')),
               answer(['s', 'b', 'm', 't'], '.2', 0)]
        for a in bad:
            with self.subTest(answer=a):
                self.assertFalse(check_witness(p, a)[0])

    def test_case_and_surrounding_space_are_accepted(self):
        p = prepare(self.bottleneck_problem())
        self.assertTrue(check_witness(p, answer([' S ', 'B', 'M', 'T'], '.2', '3.05'))[0])

    def test_bad_source_graphs_raise_instead_of_scoring(self):
        original = self.bottleneck_problem()
        variants = []
        for change in (
            lambda g: g['nodes'].append(node('S')),
            lambda g: g['edges'].append(edge('t', 's')),
            lambda g: g['edges'].append(edge('s', 'a')),
            lambda g: g['edges'].append(edge('s', 'missing')),
            lambda g: g['nodes'][0].update(capacity=-1),
            lambda g: g['nodes'][0].update(cost=float('inf')),
            lambda g: g['nodes'][0].update(cost=True),
            lambda g: g.update(start='missing'),
            lambda g: g['nodes'][0].update(extra='unread assumption'),
        ):
            g = deepcopy(original); change(g); variants.append(g)
        variants.extend([{}, None, graph([], []), graph([node('s')], 'edges')])
        for g in variants:
            with self.subTest(graph=g), self.assertRaises(InvalidProblem):
                prepare(g)

    def test_disconnected_cycle_is_invalid_source(self):
        g = graph([node('s'), node('t'), node('x'), node('y')],
                  [edge('s', 't'), edge('x', 'y'), edge('y', 'x')])
        with self.assertRaises(InvalidProblem): prepare(g)

    def test_limits_fail_explicitly(self):
        with self.assertRaises(InvalidProblem):
            prepare(graph([node('n' + str(i)) for i in range(257)], [], 'n0', 'n256'))
        for value in ('1e-13', '1e13', '1/3', '1e999', 'NaN', 'Infinity'):
            with self.subTest(value=value), self.assertRaises(InvalidProblem):
                prepare(graph([node('s', value)], [], end='s'))

    def test_sum_can_exceed_single_input_bound(self):
        p = prepare(graph([node('s', cost=10**12), node('t', cost=10**12)],
                          [edge('s', 't', cost=10**12)]))
        self.assertTrue(check_witness(p, answer(['s', 't'], 1, 3 * 10**12))[0])

    def test_dependency_signature_ignores_unused_data_but_tracks_optimal_ties(self):
        g = self.bottleneck_problem()
        original = decision_signature(prepare(g))
        g['nodes'].append(node('unused', 0, 999))
        g['nodes'][1]['cost'] = 999
        self.assertEqual(decision_signature(prepare(g)), original)
        g['nodes'][1]['cost'] = '3.05'
        tied = decision_signature(prepare(g))
        self.assertEqual((tied['bottleneck'], tied['cost']), (original['bottleneck'], original['cost']))
        self.assertNotEqual(tied, original)

    def test_against_exhaustive_paths_in_300_independent_graphs(self):
        rng = random.Random(64379)
        for trial in range(300):
            size = rng.randrange(2, 9)
            g = graph([node('n' + str(i), str(rng.randrange(11) / 10),
                                  str(rng.randrange(20) / 10)) for i in range(size)],
                      [edge('n' + str(i), 'n' + str(j), str(rng.randrange(11) / 10),
                            str(rng.randrange(20) / 10))
                       for i in range(size) for j in range(i + 1, size) if rng.random() < .5],
                      'n0', 'n' + str(size - 1))
            choices = exhaustive(g)
            best = max(((capacity, -cost) for _, capacity, cost in choices), default=None)
            p = prepare(g)
            with self.subTest(trial=trial):
                self.assertEqual(p['optimum'], None if best is None else (best[0], -best[1]))
                signature = decision_signature(p)
                expected_edges = {link for path, capacity, cost in choices
                                  if (capacity, -cost) == best for link in zip(path, path[1:])}
                self.assertEqual({tuple(link) for link in signature.get('edges', [])}, expected_edges)
                for path, capacity, cost in choices:
                    valid = (capacity, -cost) == best
                    submission = answer(list(path), float(capacity), float(cost))
                    self.assertEqual(check_witness(p, submission)[0], valid)


if __name__ == '__main__':
    unittest.main(verbosity=2)
