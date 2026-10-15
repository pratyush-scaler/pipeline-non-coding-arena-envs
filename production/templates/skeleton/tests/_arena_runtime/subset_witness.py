"""Verify every optimal selection under a bounded public constraint problem.

Enumeration is exact and bounded; no source program or submitted code executes.
Selection optimality never depends on an arbitrary tie-break or report tolerance.
"""
from __future__ import annotations

from fractions import Fraction
import hashlib
import math
import re

from .path_witness import InvalidProblem, _id, _number as _tolerance, _reported

MAX_ITEMS = 18
MAX_METRICS = 12


def _number(value, maximum=10**12):
    if type(value) not in (str, int, float) or len(str(value)) > 80:
        raise InvalidProblem("selection values must be finite exact decimal numbers")
    text = str(value).strip()
    if not re.fullmatch(r"[+-]?(?:[0-9]+(?:\.[0-9]*)?|\.[0-9]+)(?:[eE][+-]?[0-9]{1,3})?", text):
        raise InvalidProblem("selection values must be finite exact decimal numbers")
    number = Fraction(text)
    if abs(number) > maximum or (number * 10**12).denominator != 1:
        raise InvalidProblem("selection number exceeds the exact decimal bounds")
    return number


def _identifiers(value, known):
    if not isinstance(value, list):
        raise InvalidProblem("requires and excludes must be identifier lists")
    identifiers = [_id(item) for item in value]
    if len(set(identifiers)) != len(identifiers) or set(identifiers) - known:
        raise InvalidProblem("requires and excludes must name distinct declared items")
    return identifiers


def prepare(problem):
    """Validate source first, then solve a finite binary-selection problem."""
    if not isinstance(problem, dict) or set(problem) != {"items", "constraints", "objectives"}:
        raise InvalidProblem("selection problem requires items, constraints and objectives")
    rows, restrictions, objectives = problem["items"], problem["constraints"], problem["objectives"]
    if not isinstance(rows, list) or len(rows) > MAX_ITEMS:
        raise InvalidProblem(f"selection problem permits 0..{MAX_ITEMS} items")
    if not isinstance(restrictions, list) or len(restrictions) > 24:
        raise InvalidProblem("selection problem permits at most 24 constraints")
    if not isinstance(objectives, list) or not 1 <= len(objectives) <= 4:
        raise InvalidProblem("selection problem needs 1..4 lexicographic objectives")
    metrics, priorities, bounds = set(), [], []
    for objective in objectives:
        if not isinstance(objective, dict) or set(objective) != {"metric", "direction"}:
            raise InvalidProblem("each objective requires metric and direction")
        metric = _id(objective["metric"])
        if objective["direction"] not in ("max", "min") or metric in {name for name, direction in priorities}:
            raise InvalidProblem("objectives must name distinct metrics and max/min directions")
        priorities.append((metric, objective["direction"]))
        metrics.add(metric)
    for restriction in restrictions:
        if not isinstance(restriction, dict) or set(restriction) != {"metric", "min", "max"}:
            raise InvalidProblem("each constraint requires metric, min and max")
        metric = _id(restriction["metric"])
        lower = None if restriction["min"] is None else _number(restriction["min"], MAX_ITEMS * 10**12)
        upper = None if restriction["max"] is None else _number(restriction["max"], MAX_ITEMS * 10**12)
        if lower is None and upper is None or lower is not None and upper is not None and lower > upper:
            raise InvalidProblem("constraint needs at least one bound, with min <= max")
        bounds.append((metric, lower, upper))
        metrics.add(metric)
    if len(metrics) > MAX_METRICS:
        raise InvalidProblem(f"selection problem permits at most {MAX_METRICS} metrics")
    items = {}
    for row in rows:
        if not isinstance(row, dict) or set(row) != {"id", "eligible", "values", "requires", "excludes"}:
            raise InvalidProblem("each item requires id, eligible, values, requires and excludes")
        identifier = _id(row["id"])
        if identifier in items or type(row["eligible"]) is not bool or not isinstance(row["values"], dict):
            raise InvalidProblem("item ids must be unique and eligibility must be boolean")
        values = {}
        for name, value in row["values"].items():
            metric = _id(name)
            if metric not in metrics or metric in values:
                raise InvalidProblem("item values must name distinct declared metrics")
            values[metric] = _number(value)
        items[identifier] = {"eligible": row["eligible"], "values": values,
                             "requires": row["requires"], "excludes": row["excludes"]}
    known = set(items)
    for identifier, row in items.items():
        row["requires"] = _identifiers(row["requires"], known)
        row["excludes"] = _identifiers(row["excludes"], known)
        if identifier in row["excludes"] or set(row["requires"]) & set(row["excludes"]):
            raise InvalidProblem("an item cannot exclude itself or a required companion")
    names, metric_names = sorted(items), sorted(metrics)
    positions = {name: index for index, name in enumerate(names)}
    metric_positions = {name: index for index, name in enumerate(metric_names)}
    scales = [math.lcm(*(row["values"].get(metric, Fraction(0)).denominator for row in items.values()),
                       *(value.denominator for name, lower, upper in bounds if name == metric
                         for value in (lower, upper) if value is not None))
              for metric in metric_names]
    vectors = [[int(items[name]["values"].get(metric, Fraction(0)) * scale)
                for metric, scale in zip(metric_names, scales)] for name in names]
    dependencies = []
    blocked = 0
    for name in names:
        bit = 1 << positions[name]
        row = items[name]
        if not row["eligible"]:
            blocked |= bit
        required = sum(1 << positions[other] for other in row["requires"])
        excluded = sum(1 << positions[other] for other in row["excludes"])
        if required or excluded:
            dependencies.append((bit, required, excluded))
    numeric_bounds = [(metric_positions[metric], int(lower * scales[metric_positions[metric]]) if lower is not None else None,
                       int(upper * scales[metric_positions[metric]]) if upper is not None else None)
                      for metric, lower, upper in bounds]
    ranking = [(metric_positions[metric], 1 if direction == "max" else -1) for metric, direction in priorities]
    totals = [0] * len(metric_names)
    previous, best, optimum = 0, None, None
    reference_selection = []
    accepted = 0
    witness_count = 0
    for index in range(1 << len(names)):
        mask = index ^ (index >> 1)
        changed = previous ^ mask
        if changed:
            position = changed.bit_length() - 1
            sign = 1 if mask & changed else -1
            totals = [total + sign * value for total, value in zip(totals, vectors[position])]
        previous = mask
        if mask & blocked:
            continue
        if any(mask & bit and (mask & required != required or mask & excluded)
               for bit, required, excluded in dependencies):
            continue
        if any(lower is not None and totals[position] < lower or upper is not None and totals[position] > upper
               for position, lower, upper in numeric_bounds):
            continue
        score = tuple(sign * totals[position] for position, sign in ranking)
        if best is not None and score < best:
            continue
        if best is None or score > best:
            best = score
            optimum = tuple(Fraction(totals[metric_positions[metric]], scales[metric_positions[metric]])
                            for metric, direction in priorities)
            accepted, witness_count = 0, 0
            reference_selection = [name for position, name in enumerate(names) if mask & (1 << position)]
        selected = tuple(name for position, name in enumerate(names) if mask & (1 << position))
        values = tuple(str(Fraction(total, scale)) for total, scale in zip(totals, scales))
        accepted = (accepted + int.from_bytes(hashlib.sha256(repr((selected, values)).encode()).digest(), "big")) % (1 << 256)
        witness_count += 1
    return {"items": items, "metrics": metric_names, "bounds": bounds, "objectives": priorities,
            "optimum": optimum, "accepted_witnesses_sha256": hashlib.sha256(repr((accepted, witness_count)).encode()).hexdigest(),
            "optimal_witness_count": witness_count, "reference_selection": reference_selection}


def reference_witness(prepared, schema=None):
    """Derive a feasible optimal witness and every total from the public inputs."""
    if prepared["optimum"] is None:
        return {"feasible": False, "selected": []}
    selected = prepared["reference_selection"]
    properties = schema.get("properties", {}) if isinstance(schema, dict) else {}
    total_schema = properties.get("totals", {}).get("properties", {})
    totals = {metric: _reported(sum((prepared["items"][identifier]["values"].get(metric, Fraction(0))
                                   for identifier in selected), Fraction(0)), total_schema.get(metric))
              for metric in prepared["metrics"]}
    return {"feasible": True, "selected": list(selected), "totals": totals}


def decision_signature(prepared):
    """Fingerprint every accepted selection and its totals, not one preferred tie."""
    return {"feasible": prepared["optimum"] is not None,
            "metrics": prepared["metrics"],
            "optimum": [str(value) for value in prepared["optimum"]] if prepared["optimum"] is not None else None,
            "accepted_witnesses_sha256": prepared["accepted_witnesses_sha256"],
            "optimal_witness_count": prepared["optimal_witness_count"]}


def check_witness(prepared, answer, tolerance=0):
    """Check a submission without treating a malformed witness as a source fault."""
    tolerance = _tolerance(tolerance)
    if not isinstance(answer, dict) or type(answer.get("feasible")) is not bool:
        return False, "answer requires a feasible boolean"
    if prepared["optimum"] is None:
        passed = set(answer) == {"feasible", "selected"} and answer["feasible"] is False and answer["selected"] == []
        return passed, "" if passed else "no selection satisfies the public constraints"
    if set(answer) != {"feasible", "selected", "totals"} or answer["feasible"] is not True:
        return False, "a feasible answer requires selected items and every metric total"
    selected, claimed = answer["selected"], answer["totals"]
    if not isinstance(selected, list) or len(selected) > MAX_ITEMS:
        return False, "selected must be a bounded identifier list"
    try:
        selected = [_id(value) for value in selected]
        if not isinstance(claimed, dict) or set(claimed) != set(prepared["metrics"]):
            return False, "totals must report every declared metric exactly once"
        claimed = {metric: _number(value, MAX_ITEMS * 10**12) for metric, value in claimed.items()}
    except InvalidProblem:
        return False, "invalid item identifier or reported total"
    chosen = set(selected)
    if len(chosen) != len(selected) or chosen - set(prepared["items"]):
        return False, "selected must name distinct declared items"
    for identifier in chosen:
        row = prepared["items"][identifier]
        if not row["eligible"] or set(row["requires"]) - chosen or set(row["excludes"]) & chosen:
            return False, "selection violates eligibility, required companions or exclusions"
    totals = {metric: sum((prepared["items"][identifier]["values"].get(metric, Fraction(0))
                          for identifier in chosen), Fraction(0)) for metric in prepared["metrics"]}
    if any(lower is not None and totals[metric] < lower or upper is not None and totals[metric] > upper
           for metric, lower, upper in prepared["bounds"]):
        return False, "selection violates a public metric bound"
    if tuple(totals[metric] for metric, direction in prepared["objectives"]) != prepared["optimum"]:
        return False, "selection is not globally optimal under the public lexicographic objectives"
    if any(abs(claimed[metric] - total) > tolerance for metric, total in totals.items()):
        return False, "reported totals do not describe the submitted selection"
    return True, ""
