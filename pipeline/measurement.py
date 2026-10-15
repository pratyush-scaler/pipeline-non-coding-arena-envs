"""Shared descriptive measurement policy; validity is independent of difficulty.

An observed band is not proof of a sound check or of ability discrimination.
Never pool model rates to qualify a task. Uncertainty is reported, not hidden.
"""
from __future__ import annotations

import math
from collections import Counter

CORE_LO, CORE_HI, FLOOR_LO = .30, .70, .90
BANDS = ("stretch", "core", "transition", "floor", "unreachable")


def band(rate: float | None) -> str:
    if rate is None:
        return "unreachable"
    if not math.isfinite(rate) or not 0 <= rate <= 1:
        raise ValueError("pass rate must be finite and between zero and one")
    return ("stretch" if rate < CORE_LO else "core" if rate <= CORE_HI
            else "transition" if rate < FLOOR_LO else "floor")


def observation(rec: dict) -> dict:
    counts = {k: rec.get(k, 0) for k in ("passed", "failed", "gated_out")}
    if any(type(v) is not int or v < 0 for v in counts.values()):
        raise ValueError("check counts must be nonnegative integers")
    n = counts["passed"] + counts["failed"]
    rate = counts["passed"] / n if n else None
    interval = None
    if n:
        z = 1.959963984540054
        denominator = 1 + z * z / n
        center = (rate + z * z / (2 * n)) / denominator
        half = z * math.sqrt(rate * (1 - rate) / n + z * z / (4 * n * n)) / denominator
        interval = [max(0., center - half), min(1., center + half)]
    return {**counts, "attempted": n, "rate": rate, "band": band(rate),
            "wilson_95": interval, "provisional": n < 10,
            "boundary_uncertain": bool(interval and any(interval[0] < b < interval[1]
                                                        for b in (CORE_LO, CORE_HI, FLOOR_LO)))}


def objective_bands(checks: dict) -> dict:
    result = {name: [] for name in BANDS}
    for cid, rec in checks.items():
        if rec.get("kind") == "guardrail":
            continue
        measured = observation(rec)
        result[measured["band"]].append((cid, measured["rate"]))
    return result


def profile(checks: dict) -> dict:
    """Per-model descriptive profile, with guardrails outside capability totals."""
    rows = {cid: {**rec, **observation(rec)} for cid, rec in checks.items()}
    objectives = {cid: r for cid, r in rows.items() if r.get("kind") != "guardrail"}
    counts = dict(Counter(r["band"] for r in objectives.values()))
    if not objectives:
        status = "unmeasured"
    elif counts.get("unreachable"):
        status = "unreachable"
    elif all(r["rate"] < CORE_LO for r in objectives.values()):
        status = "stretch_only"
    elif all(r["rate"] > CORE_HI for r in objectives.values()):
        status = "easy"
    elif (4 <= counts.get("core", 0) <= 6 and counts.get("floor", 0) <= 2
          and 1 <= counts.get("stretch", 0) <= 2):
        status = "target_mix"
    else:
        status = "needs_redesign"
    return {"status": status, "objective_count": len(objectives),
            "guardrail_count": len(rows) - len(objectives), "bands": counts,
            "checks": rows, "qualification": "descriptive only; requires verified evidence and semantic review"}


def task_profile(steps: dict) -> dict:
    """Apply the task rubric budget without pooling rates or duplicating checks.

    Input is the step records for ONE model, either raw or already profiled.
    Each objective retains its own reachable observations. Guard outcomes remain
    in the step records; a shared integrity guard is counted once in the task.
    """
    objectives, guards, empty_steps = {}, set(), []
    for step, data in steps.items():
        informative = False
        for cid, row in data['checks'].items():
            if row.get('kind') == 'guardrail':
                guards.add(cid)
                continue
            if cid in objectives:
                raise ValueError(f'{cid}: an objective cannot be counted in multiple steps')
            objectives[cid] = row
            informative |= observation(row)['band'] in {'core', 'stretch'}
        if not informative:
            empty_steps.append(step)
    result = profile(objectives)
    if result['status'] == 'target_mix' and empty_steps:
        result['status'] = 'needs_redesign'
    return {**result, 'guardrail_count': len(guards), 'uninformative_steps': empty_steps,
            'scope': 'whole task for one model; criterion rates remain separate'}
