"""Global selection grading accepts all legitimate optima and rejects shortcuts."""
import copy
from fractions import Fraction
import itertools
import random
import unittest

from pipeline.author.subset_witness import InvalidProblem, prepare, check_witness, decision_signature, reference_witness


def item(identifier, gain, cost, *, eligible=True, requires=None, excludes=None):
    return {"id": identifier, "eligible": eligible, "values": {"gain": gain, "cost": cost},
            "requires": requires or [], "excludes": excludes or []}


def problem(rows=None):
    return {"items": rows if rows is not None else [item("Alpha", 9, 6), item("Beta", 8, 5), item("Gamma", 8, 5)],
            "constraints": [{"metric": "cost", "min": None, "max": 10}],
            "objectives": [{"metric": "gain", "direction": "max"}, {"metric": "cost", "direction": "min"}]}


def answer(selected, gain, cost):
    return {"feasible": True, "selected": selected, "totals": {"gain": gain, "cost": cost}}


class SubsetWitness(unittest.TestCase):
    def test_locally_attractive_greedy_choice_loses_to_joint_selection(self):
        prepared = prepare(problem())
        self.assertEqual(prepared["optimum"], (16, 10))
        self.assertTrue(check_witness(prepared, answer(["Beta", "Gamma"], 16, 10))[0])
        self.assertFalse(check_witness(prepared, answer(["Alpha"], 9, 6))[0])
        self.assertFalse(check_witness(prepared, answer(["Alpha"], 16, 10), tolerance=10**12)[0])

    def test_all_optimal_ties_and_submission_orders_are_accepted(self):
        prepared = prepare(problem([item("Alpha", 8, 5), item("Beta", 8, 5), item("Gamma", 8, 5)]))
        self.assertEqual(prepared["optimal_witness_count"], 3)
        for selected in itertools.permutations(["Alpha", "Beta", "Gamma"], 2):
            self.assertTrue(check_witness(prepared, answer(list(selected), 16, 10))[0])
        self.assertTrue(check_witness(prepared, answer([" BETA ", "gamma"], 16, 10))[0])

    def test_secondary_objective_is_not_a_weighted_sum(self):
        prepared = prepare(problem([item("Alpha", 10, 10), item("Beta", 9, 0)]))
        self.assertTrue(check_witness(prepared, answer(["Alpha", "Beta"], 19, 10))[0])
        self.assertFalse(check_witness(prepared, answer(["Beta"], 9, 0))[0])

    def test_eligibility_companions_exclusions_and_signed_values(self):
        public = problem([item("Alpha", 9, 6, requires=["Gamma"]),
                          item("Beta", 8, 5, excludes=["Gamma"]), item("Gamma", 2, -1),
                          item("Delta", 100, 1, eligible=False)])
        prepared = prepare(public)
        self.assertTrue(check_witness(prepared, answer(["Alpha", "Gamma"], 11, 5))[0])
        for selected, gain, cost in [(["Alpha"], 9, 6), (["Beta", "Gamma"], 10, 4), (["Delta"], 100, 1)]:
            self.assertFalse(check_witness(prepared, answer(selected, gain, cost))[0])

    def test_cyclic_companion_requirements_form_a_legitimate_joint_group(self):
        prepared = prepare(problem([item("Alpha", 3, 2, requires=["Beta"]),
                                    item("Beta", 4, 3, requires=["Alpha"])]))
        self.assertTrue(check_witness(prepared, answer(["Alpha", "Beta"], 7, 5))[0])

    def test_exact_decimals_and_inclusive_bounds(self):
        public = problem([item("Alpha", ".1", ".1"), item("Beta", ".2", ".2")])
        public["constraints"][0]["max"] = ".3"
        prepared = prepare(public)
        self.assertEqual(prepared["optimum"], (Fraction(3, 10), Fraction(3, 10)))
        self.assertTrue(check_witness(prepared, answer(["Alpha", "Beta"], ".3", ".3"))[0])
        self.assertFalse(check_witness(prepared, answer(["Alpha", "Beta"], ".31", ".3"))[0])
        self.assertTrue(check_witness(prepared, answer(["Alpha", "Beta"], ".31", ".3"), tolerance=.01)[0])

    def test_missing_metric_contributes_zero(self):
        public = problem([item("Alpha", 4, 0)])
        del public["items"][0]["values"]["cost"]
        self.assertTrue(check_witness(prepare(public), answer(["Alpha"], 4, 0))[0])

    def test_empty_feasible_subset_is_not_infeasibility(self):
        prepared = prepare(problem([]))
        self.assertTrue(check_witness(prepared, answer([], 0, 0))[0])
        self.assertFalse(check_witness(prepared, {"feasible": False, "selected": []})[0])
        public = problem([item("Alpha", -2, 1)])
        self.assertTrue(check_witness(prepare(public), answer([], 0, 0))[0])

    def test_infeasible_result_omits_totals(self):
        public = problem([])
        public["constraints"][0]["min"] = 1
        prepared = prepare(public)
        self.assertIsNone(prepared["optimum"])
        self.assertTrue(check_witness(prepared, {"feasible": False, "selected": []})[0])
        self.assertFalse(check_witness(prepared, {"feasible": False, "selected": [], "totals": {}})[0])

    def test_signature_detects_changed_tie_without_false_dependency_on_row_order(self):
        public = problem([item("Alpha", 8, 5), item("Beta", 8, 5), item("Gamma", 8, 5)])
        original = decision_signature(prepare(public))
        public["items"].reverse()
        self.assertEqual(decision_signature(prepare(public)), original)
        public["items"][0]["eligible"] = False
        changed = decision_signature(prepare(public))
        self.assertEqual(changed["optimum"], original["optimum"])
        self.assertNotEqual(changed["accepted_witnesses_sha256"], original["accepted_witnesses_sha256"])

    def test_inert_ineligible_item_does_not_change_the_answer_set(self):
        public = problem()
        original = decision_signature(prepare(public))
        public["items"].append(item("Aardvark", 100, 1, eligible=False))
        self.assertEqual(decision_signature(prepare(public)), original)

    def test_malformed_submissions_fail_instead_of_raising_source_errors(self):
        prepared = prepare(problem())
        invalid = [None, [], {}, {"feasible": 1}, answer(["Beta", "Beta"], 16, 10),
                   answer([{}], 16, 10), answer(["unknown"], 16, 10),
                   answer(["Beta", "Gamma"], True, 10), answer(["Beta", "Gamma"], "nan", 10),
                   {"feasible": True, "selected": [], "totals": []}]
        for value in invalid:
            with self.subTest(value=value):
                self.assertFalse(check_witness(prepared, value)[0])

    def test_invalid_sources_are_rejected_before_any_submission_is_read(self):
        mutations = [lambda value: value["items"].append(copy.deepcopy(value["items"][0])),
                     lambda value: value["items"][0].update(eligible=1),
                     lambda value: value["items"][0].update(requires=["unknown"]),
                     lambda value: value["items"][0].update(excludes=["Alpha"]),
                     lambda value: value["items"][0].update(requires=["Beta"], excludes=["Beta"]),
                     lambda value: value["items"][0]["values"].update(gain="Infinity"),
                     lambda value: value["items"][0]["values"].update(gain=True),
                     lambda value: value["items"][0]["values"].update(gain="1e-13"),
                     lambda value: value["constraints"][0].update(min=11),
                     lambda value: value["constraints"][0].update(max=None),
                     lambda value: value.update(objectives=[]),
                     lambda value: value.update(items=[item(f"Item{index}", 1, 1) for index in range(19)])]
        for mutate in mutations:
            public = problem()
            mutate(public)
            with self.subTest(public=public):
                with self.assertRaises(InvalidProblem):
                    prepare(public)

    def test_solver_matches_an_independent_exhaustive_baseline(self):
        generator = random.Random(91203)
        for iteration in range(100):
            rows = [item(f"Item{index}", generator.randint(-4, 10), generator.randint(-2, 8),
                         eligible=generator.choice([True, True, False])) for index in range(generator.randint(0, 7))]
            public = problem(rows)
            public["constraints"][0].update(min=generator.randint(-2, 2), max=generator.randint(3, 12))
            if iteration % 2:
                public["objectives"][0]["direction"] = "min"
            if len(rows) >= 2:
                rows[0]["requires"] = [rows[1]["id"]]
                rows[1]["excludes"] = [rows[-1]["id"]] if len(rows) >= 3 else []
            feasible = []
            for choices in itertools.product([False, True], repeat=len(rows)):
                selected = {row["id"] for row, chosen in zip(rows, choices) if chosen}
                chosen_rows = [row for row in rows if row["id"] in selected]
                if any(not row["eligible"] or set(row["requires"]) - selected or set(row["excludes"]) & selected for row in chosen_rows):
                    continue
                gain, cost = sum(row["values"]["gain"] for row in chosen_rows), sum(row["values"]["cost"] for row in chosen_rows)
                if not public["constraints"][0]["min"] <= cost <= public["constraints"][0]["max"]:
                    continue
                rank = (gain if public["objectives"][0]["direction"] == "max" else -gain, -cost)
                feasible.append((rank, answer(sorted(selected), gain, cost)))
            prepared = prepare(public)
            self.assertTrue(check_witness(prepared, reference_witness(prepared))[0])
            if not feasible:
                self.assertIsNone(prepared["optimum"])
                continue
            optimum = max(rank for rank, witness in feasible)
            self.assertEqual(prepared["optimal_witness_count"], sum(rank == optimum for rank, witness in feasible))
            for rank, witness in feasible:
                self.assertEqual(check_witness(prepared, witness)[0], rank == optimum)

    def test_exact_decimal_string_contract_can_represent_large_precise_totals(self):
        public = problem([item("Alpha", "1000000000000", 0), item("Beta", ".000000000001", 0)])
        prepared = prepare(public)
        schema = {"properties": {"totals": {"properties": {"gain": {"type": "string"}, "cost": {"type": "string"}}}}}
        witness = reference_witness(prepared, schema)
        self.assertEqual(witness["totals"]["gain"], "1000000000000.000000000001")
        self.assertTrue(check_witness(prepared, witness)[0])

    def test_input_precision_bound_is_decimal_places_not_denominator_size(self):
        public = problem([item("Alpha", "0.000000000001818989403545856475830078125", 0)])
        with self.assertRaises(InvalidProblem):
            prepare(public)


if __name__ == "__main__":
    unittest.main()
