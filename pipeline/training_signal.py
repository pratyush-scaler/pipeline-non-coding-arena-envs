"""The training-signal shape of a calibration: spread, gradient, independence.

Arena's 261013 review and spec 10_12. A group-relative policy gradient learns
from the DIFFERENCE between runs of the same task: a group whose rewards are all
equal has zero advantage and teaches nothing, and a task that only one of two
models ever passes sorts the models without producing "sometimes-pass" cases.
So besides pass@1, every screen now reports, per model and per step:

  full passes, pass rate      the difficulty, against the extreme band
                              (`policy.EXTREME_PASS_AT_1_MAX` on both models)
  distinct scores, reward SD  the spread a group of runs carries
  per-check fail rates        which decisions actually discriminate
  per-premise fail rates      when the authoring premise map exists
  pairwise phi                whether two premises fail in the same runs
  free share                  objective weight no run of any model failed
  constant premises           a premise no run ever resolved: zero signal
  model sorting               one model passes nearly all, the other nearly none

and classifies the shape (`policy.SIGNAL_SHAPES`, first raised flag wins):

  SORTING            one model >= MODEL_SORTING_HIGH while the other <= _LOW
  TOO_EASY           a model's full-success rate above the extreme band
  CONSTANT_PREMISE   a premise (or, with no map, an objective) never resolved
  FLAT               a model's step scores take < MIN_DISTINCT_SCORES values
                     or their SD is < MIN_RUN_REWARD_SD
  IN_BAND            none of the above

`target_met` (in band AND spread ok) is what ends a hardening lineage as
target-met (`harden._target_met`). Nothing here gates release
(`policy.SIGNAL_GATES_RELEASE`). Advisory flags -- FREE_HEAVY, PREMISES_LINKED,
CHECKS_LINKED, DEAD_PREMISE, PREMISE_RATE_OUT_OF_BAND, NO_FULL_PASS,
PRIMARY_NOT_HARD, PREMISE_MAP_ABSENT -- are reported and fed to hardening.

Inputs are the campaigns' own per-run check states (a campaign `report.json`,
or the verified `rollouts` a screen measures). Voids leave every denominator;
a check gated out of a run was not attempted there (`gated_out` is not failed).
Five runs per model is a screen: rates move in steps of 0.2 and phi is noisy.
"""
from __future__ import annotations

import json
import math
import statistics
from itertools import combinations
from pathlib import Path

from . import policy

SCHEMA = "arena-pipeline/signal/1"

#: A step or task reward at or above 1 - EPSILON is a full pass.
EPSILON = 1e-9

#: Flags that decide `spread_ok` (with TOO_EASY deciding `in_band`).
SPREAD_FLAGS = ("SORTING", "CONSTANT_PREMISE", "FLAT")

#: Reported and fed to hardening; never part of `target_met`.
ADVISORY_FLAGS = ("FREE_HEAVY", "PREMISES_LINKED", "CHECKS_LINKED", "DEAD_PREMISE",
                  "PREMISE_RATE_OUT_OF_BAND", "NO_FULL_PASS", "PRIMARY_NOT_HARD",
                  "PREMISE_MAP_ABSENT")


# ---------------------------------------------------------------------------
# Inputs
# ---------------------------------------------------------------------------

def _number(value) -> bool:
    return type(value) in (int, float) and math.isfinite(value)


def _state(row: dict) -> str:
    if row.get("gated_out"):
        return "gated_out"
    return "passed" if row.get("value") == 1 else "failed"


def runs_from_report(report: dict, tag: str = "") -> list[dict]:
    """A campaign report's VALID, complete trials as runs.

    A run is {"episode", "steps": {step: {"reward", "checks": {id: state}}}}.
    A trial that is invalid, or missing a step, or carrying an invalid step,
    measured nothing and is dropped -- never scored as a zero.
    """
    names = [n for n in report.get("step_names") or [] if isinstance(n, str)]
    runs = []
    for number, trial in enumerate(report.get("trials") or [], 1):
        if not isinstance(trial, dict) or trial.get("valid") is not True:
            continue
        steps = {s.get("name"): s for s in trial.get("steps") or [] if isinstance(s, dict)}
        wanted = names or [n for n in steps if isinstance(n, str)]
        if not wanted or any(n not in steps or steps[n].get("valid") is not True
                             or not _number(steps[n].get("reward")) for n in wanted):
            continue
        runs.append({"episode": f"{tag}{trial.get('id') or number}",
                     "steps": {n: {"reward": float(steps[n]["reward"]),
                                   "checks": {str(cid).removeprefix("reward/"): _state(row)
                                              for cid, row in (steps[n].get("checks") or {}).items()
                                              if isinstance(row, dict)}}
                               for n in wanted}})
    return runs


def runs_from_rollouts(measured: dict) -> list[dict]:
    """A verified measurement's `rollouts` (`release.calibration_measurement`) as runs.

    An episode with a void, errored or missing step is dropped, as
    `metrics.episode_rewards` drops it.
    """
    rows = [r for r in measured.get("rollouts") or [] if isinstance(r, dict)]
    names = [n for n in measured.get("step_names") or [] if isinstance(n, str)] or \
        list(dict.fromkeys(r.get("step") for r in rows))
    grouped: dict = {}
    for row in rows:
        grouped.setdefault(row.get("episode"), []).append(row)
    runs = []
    for episode, members in grouped.items():
        by_step = {r.get("step"): r for r in members}
        if set(by_step) != set(names) or len(members) != len(names):
            continue
        if any(r.get("zero_class") == "void" or r.get("error") or not _number(r.get("reward"))
               for r in members):
            continue
        runs.append({"episode": str(episode),
                     "steps": {n: {"reward": float(by_step[n]["reward"]),
                                   "checks": {str(k): str(v) for k, v in (by_step[n].get("checks") or {}).items()}}
                               for n in names}})
    return runs


def runs_from_campaigns(paths) -> list[dict]:
    """Every valid run of a campaign and its top-ups (`<campaign>/report.json`).

    Raises OSError/ValueError when a cited campaign cannot be read: an
    unreadable campaign is missing evidence, never an empty one.
    """
    runs = []
    for index, path in enumerate(dict.fromkeys(str(p) for p in paths if p)):
        report = json.loads((Path(path) / "report.json").read_text())
        if not isinstance(report, dict):
            raise ValueError(f"{path}: report.json is not an object")
        runs += runs_from_report(report, tag=f"c{index}:")
    return runs


def check_weights(bundle: Path | None) -> tuple[dict, set[str]]:
    """((step, id) -> objective weight, guardrail ids) from tests/checks.json.

    A check with no step is keyed (None, id) and applies to every step.
    """
    weights, guards = {}, set()
    if bundle is None:
        return weights, guards
    try:
        data = json.loads((Path(bundle) / "tests/checks.json").read_text())
    except (OSError, ValueError):
        return weights, guards
    raw = data.get("checks") if isinstance(data, dict) else None
    for check in raw if isinstance(raw, list) else []:
        if not isinstance(check, dict) or not isinstance(check.get("id"), str):
            continue
        if check.get("kind") == "guardrail":
            guards.add(check["id"])
        elif check.get("kind") in (None, "objective") and _number(check.get("weight")):
            weights[(check.get("step"), check["id"])] = float(check["weight"])
    return weights, guards


def premise_map(bundle: Path | None) -> list[dict] | None:
    """The authoring premise map (`authoring/spec.json` quality.premise_map), or
    None when the bundle has none -- reported as "premise map absent"."""
    if bundle is None:
        return None
    try:
        spec = json.loads((Path(bundle) / "authoring/spec.json").read_text())
    except (OSError, ValueError):
        return None
    from .author import premises
    if not isinstance(premises.raw_map(spec), list):
        return None
    return premises.entries(spec)


# ---------------------------------------------------------------------------
# Metrics
# ---------------------------------------------------------------------------

def _round(value, places: int = 4):
    return None if value is None else round(value, places)


def wilson(passes: int, n: int, z: float = 1.645) -> tuple[float, float] | None:
    """A 90% Wilson interval for passes/n (proposal 3.3.5: report intervals)."""
    if n <= 0:
        return None
    p = passes / n
    den = 1 + z * z / n
    centre = (p + z * z / (2 * n)) / den
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / den
    return (round(max(0.0, centre - half), 3), round(min(1.0, centre + half), 3))


def phi(x: list[int], y: list[int]) -> float | None:
    """Phi coefficient of two binary failure vectors; None when a margin is empty."""
    n11 = sum(1 for a, b in zip(x, y) if a and b)
    n00 = sum(1 for a, b in zip(x, y) if not a and not b)
    n10 = sum(1 for a, b in zip(x, y) if a and not b)
    n01 = sum(1 for a, b in zip(x, y) if not a and b)
    margins = (n11 + n10) * (n01 + n00) * (n11 + n01) * (n10 + n00)
    if margins == 0:
        return None
    return (n11 * n00 - n10 * n01) / math.sqrt(margins)


def _spread(scores: list[float]) -> dict:
    full = sum(1 for s in scores if s >= 1.0 - EPSILON)
    n = len(scores)
    return {"episodes": n, "passes": full, "pass_rate": _round(full / n) if n else None,
            "distinct_scores": len({round(s, 4) for s in scores}),
            "reward_sd": _round(statistics.pstdev(scores)) if n > 1 else (0.0 if n else None),
            "mean_reward": _round(sum(scores) / n) if n else None,
            # Aggregates only: per-episode rewards are never repair feedback
            # (policy.REPAIR_FEEDBACK_EXCLUDES), and hardening reads this.
            "min_reward": _round(min(scores)) if n else None,
            "max_reward": _round(max(scores)) if n else None}


def _weight(weights: dict, step: str, cid: str):
    return weights.get((step, cid), weights.get((None, cid)))


def measure(per_model_runs: dict[str, list[dict]], *, weights: dict | None = None,
            guardrails=(), premises: list[dict] | None = None,
            models: list[str] | None = None, min_episodes: int | None = None,
            maximum_pass_at_1: float | None = None) -> dict:
    """Every spread metric over the runs, and the shape it classifies to."""
    weights = weights or {}
    guards = set(guardrails or ())
    models = list(models or per_model_runs)
    minimum = policy.SCREEN_EPISODES_PER_MODEL if min_episodes is None else min_episodes
    band = policy.EXTREME_PASS_AT_1_MAX if maximum_pass_at_1 is None else min(
        policy.EXTREME_PASS_AT_1_MAX, maximum_pass_at_1)
    steps = sorted({s for runs in per_model_runs.values() for run in runs for s in run["steps"]})
    known = {cid for (_, cid) in weights}

    def objective(cid: str) -> bool:
        return cid not in guards and (not known or cid in known)

    out: dict = {"schema": SCHEMA, "models": models, "steps": {}, "per_model": {},
                 "premise_map": "present" if premises is not None else "absent",
                 "premises": [p["id"] for p in premises or []],
                 "limits": {"extreme_pass_at_1_max": band,
                            "primary_preferred": policy.EXTREME_PRIMARY_PASS_AT_1_PREFERRED,
                            "min_distinct_scores": policy.MIN_DISTINCT_SCORES_PER_MODEL,
                            "min_reward_sd": policy.MIN_RUN_REWARD_SD,
                            "max_free_share": policy.MAX_FREE_SHARE,
                            "max_premise_phi": policy.MAX_PREMISE_PHI,
                            "premise_miss_rate_band": list(policy.PREMISE_MISS_RATE_BAND),
                            "sorting": [policy.MODEL_SORTING_HIGH_PASS_AT_1,
                                        policy.MODEL_SORTING_LOW_PASS_AT_1],
                            "min_episodes": minimum}}
    # Per model: task-level and step-level spread, per-check and per-premise rates.
    indicators: dict[str, dict[str, list]] = {}       # model -> premise -> per-run 0/1/None
    for model in models:
        runs = per_model_runs.get(model) or []
        task_scores = [sum(r["steps"][s]["reward"] for s in r["steps"]) / len(r["steps"])
                       for r in runs if r["steps"]]
        row = {**_spread(task_scores), "steps": {}, "check_fail_rates": {}}
        row["pass_at_1"] = row.pop("pass_rate")
        row["pass_at_1_wilson90"] = wilson(row["passes"], row["episodes"])
        for step in steps:
            scores = [r["steps"][step]["reward"] for r in runs if step in r["steps"]]
            srow = _spread(scores)
            patterns = {tuple(sorted(c for c, st in r["steps"][step]["checks"].items()
                                     if st == "failed" and objective(c)))
                        for r in runs if step in r["steps"]}
            srow["failure_patterns"] = len([p for p in patterns if p])
            row["steps"][step] = srow
            tally: dict[str, list[int]] = {}
            for r in runs:
                for cid, state in (r["steps"].get(step) or {}).get("checks", {}).items():
                    if objective(cid) and state in ("passed", "failed"):
                        tally.setdefault(cid, [0, 0])[state == "failed"] += 1
            for cid, (ok, bad) in sorted(tally.items()):
                row["check_fail_rates"][f"{step}/{cid}"] = _round(bad / (ok + bad))
        if premises is not None:
            per_premise = {}
            for premise in premises:
                vector = []
                for r in runs:
                    states = [st for s in r["steps"].values() for c, st in s["checks"].items()
                              if c in premise["checks"] and st in ("passed", "failed")]
                    vector.append(None if not states else int("failed" in states))
                per_premise[premise["id"]] = vector
            indicators[model] = per_premise
            row["premise_fail_rates"] = {
                pid: (_round(sum(v for v in vec if v is not None) / len([v for v in vec if v is not None]))
                      if any(v is not None for v in vec) else None)
                for pid, vec in per_premise.items()}
            pairs = {}
            for a, b in combinations(sorted(per_premise), 2):
                both = [(x, y) for x, y in zip(per_premise[a], per_premise[b]) if x is not None and y is not None]
                value = phi([x for x, _ in both], [y for _, y in both]) if both else None
                pairs[f"{a}~{b}"] = _round(value, 3)
            row["premise_phi"] = pairs
        else:
            row["premise_fail_rates"] = None
            row["premise_phi"] = None
        out["per_model"][model] = row

    # Across models, per step: free share, constant and linked checks.
    for step in steps:
        states: dict[str, list[str]] = {}
        runsets: dict[str, set] = {}
        for model in models:
            for r in per_model_runs.get(model) or []:
                for cid, state in (r["steps"].get(step) or {}).get("checks", {}).items():
                    if not objective(cid):
                        continue
                    states.setdefault(cid, []).append(state)
                    if state == "failed":
                        runsets.setdefault(cid, set()).add((model, r["episode"]))
        attempted = {c: [s for s in v if s in ("passed", "failed")] for c, v in states.items()}
        free = sorted(c for c, v in attempted.items() if v and "failed" not in v)
        constant = sorted(c for c, v in attempted.items() if v and "passed" not in v)
        never = sorted(c for c, v in attempted.items() if not v)
        groups: dict[frozenset, list[str]] = {}
        for cid, members in runsets.items():
            groups.setdefault(frozenset(members), []).append(cid)
        total = sum(w for c in states if (w := _weight(weights, step, c)) is not None)
        free_weight = sum(_weight(weights, step, c) or 0 for c in free)
        out["steps"][step] = {
            "free_checks": free, "constant_checks": constant, "never_attempted": never,
            "free_share": _round(free_weight / total) if total else None,
            "weights_known": bool(total),
            "failure_groups": len(groups),
            "linked_check_groups": sorted(sorted(g) for g in groups.values() if len(g) > 1),
            "failing_checks_linked": len(groups) == 1 and len(runsets) > 1,
        }
    free_shares = [row["free_share"] for row in out["steps"].values() if row["free_share"] is not None]
    out["free_share"] = max(free_shares) if free_shares else None
    out["constant_checks"] = sorted(f"{s}/{c}" for s, row in out["steps"].items() for c in row["constant_checks"])

    # Premises across models.
    if premises is not None:
        pooled = {}
        for premise in premises:
            values = [v for m in models for v in indicators.get(m, {}).get(premise["id"], []) if v is not None]
            pooled[premise["id"]] = (_round(sum(values) / len(values)) if values else None)
        out["premise_fail_rates"] = pooled
        out["constant_premises"] = sorted(pid for pid, rate in pooled.items() if rate == 1.0)
        out["dead_premises"] = sorted(pid for pid, rate in pooled.items() if rate == 0.0)
        out["unmeasured_premises"] = sorted(pid for pid, rate in pooled.items() if rate is None)
        phis = [v for m in models for v in (out["per_model"][m]["premise_phi"] or {}).values() if v is not None]
        out["max_premise_phi"] = max(phis) if phis else None
        out_of_band = []
        low, high = policy.PREMISE_MISS_RATE_BAND
        for premise in premises:
            targets = _target_models(premise.get("targets"), models)
            for model in targets:
                rate = (out["per_model"][model]["premise_fail_rates"] or {}).get(premise["id"])
                if rate is not None and not low <= rate <= high:
                    out_of_band.append(f"{premise['id']} on {model.split('/')[-1]}: {rate:.2f}")
        out["premise_rates_out_of_band"] = out_of_band
    else:
        out["premise_fail_rates"] = None
        out["constant_premises"] = []
        out["dead_premises"] = []
        out["unmeasured_premises"] = []
        out["max_premise_phi"] = None
        out["premise_rates_out_of_band"] = []

    out.update(classify(out, minimum=minimum, band=band))
    return out


def _target_models(targets, models: list[str]) -> list[str]:
    if targets in (None, "both"):
        return list(models)
    want = {"fable": "fable", "astra": "astra"}.get(str(targets).lower())
    picked = [m for m in models if want and want in m.lower()]
    return picked or list(models)


def classify(sig: dict, *, minimum: int | None = None, band: float | None = None) -> dict:
    """The shape verdict, its flags and the reasons, from a `measure` result."""
    minimum = policy.SCREEN_EPISODES_PER_MODEL if minimum is None else minimum
    band = policy.EXTREME_PASS_AT_1_MAX if band is None else band
    models = sig.get("models") or []
    per_model = sig.get("per_model") or {}
    reasons, flags, unassessable = [], [], []
    if len(set(models)) < 2:
        unassessable.append(f"needs two calibration models; got {models}")
    for model in models:
        n = (per_model.get(model) or {}).get("episodes", 0)
        if n < minimum:
            unassessable.append(f"{model}: {n} valid run(s), below {minimum}")
    if unassessable:
        return {"assessable": False, "shape": None, "flags": [], "advisory_flags": [],
                "in_band": False, "spread_ok": False, "target_met": False,
                "hard_primary": None, "reasons": unassessable}
    short = {m: m.split("/")[-1] for m in models}

    # TOO_EASY: full-success rate above the band, on the task or any step.
    easy = []
    for model in models:
        row = per_model[model]
        if row["pass_at_1"] is not None and row["pass_at_1"] > band:
            easy.append(f"{short[model]} task {row['pass_at_1']:.2f}")
        for step, srow in row["steps"].items():
            if len(row["steps"]) > 1 and srow["pass_rate"] is not None and srow["pass_rate"] > band:
                easy.append(f"{short[model]} {step} {srow['pass_rate']:.2f}")
    if easy:
        flags.append("TOO_EASY")
        reasons.append(f"TOO_EASY: full-success rate above {band:.2f} -- " + ", ".join(easy))

    # SORTING: one model nearly always passes while another nearly never does.
    high, low = policy.MODEL_SORTING_HIGH_PASS_AT_1, policy.MODEL_SORTING_LOW_PASS_AT_1
    scopes = [("task", {m: per_model[m]["pass_at_1"] for m in models})]
    scopes += [(step, {m: per_model[m]["steps"].get(step, {}).get("pass_rate") for m in models})
               for step in sig.get("steps") or {}]
    sorting = []
    for scope, rates in scopes:
        known = {m: r for m, r in rates.items() if r is not None}
        tops = [m for m, r in known.items() if r >= high]
        bottoms = [m for m, r in known.items() if r <= low]
        if tops and bottoms and set(tops) != set(bottoms):
            sorting.append(f"{scope}: {', '.join(short[m] for m in tops)} >= {high:.2f}, "
                           f"{', '.join(short[m] for m in bottoms)} <= {low:.2f}")
    if sorting:
        flags.append("SORTING")
        reasons.append("SORTING: one model passes nearly every run while the other fails nearly every "
                       "run -- " + "; ".join(sorting))

    # CONSTANT_PREMISE: never resolved by any run of any model.
    if sig.get("premise_map") == "present":
        constant = sig.get("constant_premises") or []
        basis = "premise"
    else:
        constant = sig.get("constant_checks") or []
        basis = "objective check (premise map absent)"
    if constant:
        flags.append("CONSTANT_PREMISE")
        reasons.append(f"CONSTANT_PREMISE: {basis} never resolved in any run of either model -- "
                       + ", ".join(constant[:8]) + "; a constant decision carries no learning signal and "
                       "is the ambiguity signature until a feasibility proof says otherwise")

    # FLAT: a model's step scores barely vary.
    flat = []
    for model in models:
        for step, srow in per_model[model]["steps"].items():
            if (srow["distinct_scores"] < policy.MIN_DISTINCT_SCORES_PER_MODEL
                    or (srow["reward_sd"] or 0.0) < policy.MIN_RUN_REWARD_SD):
                flat.append(f"{short[model]} {step}: {srow['distinct_scores']} distinct, "
                            f"SD {srow['reward_sd'] or 0:.3f}")
    if flat:
        flags.append("FLAT")
        reasons.append(f"FLAT: fewer than {policy.MIN_DISTINCT_SCORES_PER_MODEL} distinct scores or SD below "
                       f"{policy.MIN_RUN_REWARD_SD} -- " + "; ".join(flat))

    advisory = []
    if sig.get("free_share") is not None and sig["free_share"] > policy.MAX_FREE_SHARE:
        advisory.append("FREE_HEAVY")
        reasons.append(f"FREE_HEAVY: {sig['free_share']:.0%} of a step's objective weight was passed by "
                       f"every run of every model (above {policy.MAX_FREE_SHARE:.0%})")
    if sig.get("max_premise_phi") is not None and sig["max_premise_phi"] > policy.MAX_PREMISE_PHI:
        advisory.append("PREMISES_LINKED")
        reasons.append(f"PREMISES_LINKED: two premises fail in the same runs (phi "
                       f"{sig['max_premise_phi']:.2f} > {policy.MAX_PREMISE_PHI})")
    if any(row.get("failing_checks_linked") for row in (sig.get("steps") or {}).values()):
        advisory.append("CHECKS_LINKED")
        reasons.append("CHECKS_LINKED: in a step, every failing check fails in exactly the same runs -- "
                       "one decision wearing several checks")
    if sig.get("dead_premises"):
        advisory.append("DEAD_PREMISE")
        reasons.append("DEAD_PREMISE: never missed by any run -- " + ", ".join(sig["dead_premises"]))
    if sig.get("premise_rates_out_of_band"):
        advisory.append("PREMISE_RATE_OUT_OF_BAND")
        low_q, high_q = policy.PREMISE_MISS_RATE_BAND
        reasons.append(f"PREMISE_RATE_OUT_OF_BAND: miss rate outside {low_q}-{high_q} on the targeted model -- "
                       + "; ".join(sig["premise_rates_out_of_band"][:6]))
    if all(per_model[m]["passes"] == 0 for m in models):
        advisory.append("NO_FULL_PASS")
        reasons.append("NO_FULL_PASS: no run of either model passed fully; the gradient comes only from "
                       "partial scores (a full pass in some run is preferred)")
    primary = next((m for m in models if "fable" in m.lower()), models[0])
    hard = (per_model[primary]["pass_at_1"] is not None
            and per_model[primary]["pass_at_1"] <= policy.EXTREME_PRIMARY_PASS_AT_1_PREFERRED)
    if not hard:
        advisory.append("PRIMARY_NOT_HARD")
    if sig.get("premise_map") != "present":
        advisory.append("PREMISE_MAP_ABSENT")
        reasons.append("PREMISE_MAP_ABSENT: no authoring premise map; per-premise rates, phi and constant "
                       "premises fall back to per-check evidence")
    shape = next((s for s in policy.SIGNAL_SHAPES if s in flags), "IN_BAND")
    in_band = "TOO_EASY" not in flags
    spread_ok = not any(f in flags for f in SPREAD_FLAGS)
    return {"assessable": True, "shape": shape, "flags": flags, "advisory_flags": advisory,
            "in_band": in_band, "spread_ok": spread_ok, "target_met": in_band and spread_ok,
            "hard_primary": hard, "reasons": reasons}


# ---------------------------------------------------------------------------
# Entry points
# ---------------------------------------------------------------------------

def from_runs(bundle: Path | None, per_model_runs: dict[str, list[dict]],
              models: list[str] | None = None, **kwargs) -> dict:
    weights, guards = check_weights(bundle)
    return measure(per_model_runs, weights=weights, guardrails=guards,
                   premises=premise_map(bundle), models=models, **kwargs)


def from_measurements(bundle: Path | None, measured: dict[str, dict],
                      models: list[str] | None = None, **kwargs) -> dict:
    """From the verified measurements a screen summarises (`screen.summarize`)."""
    return from_runs(bundle, {m: runs_from_rollouts(v) for m, v in measured.items()}, models, **kwargs)


def from_screen_record(record: dict, **kwargs) -> dict | None:
    """Re-derived from the campaign reports a screen receipt cites.

    None when a cited campaign cannot be read: an unreadable signal never meets
    a target. The bundle (weights, premise map) is the record's own.
    """
    per_model = {}
    index_topups = (record.get("index") or {}).get("topups") or {}
    for model, result in (record.get("per_model") or {}).items():
        if not isinstance(result, dict) or not isinstance(result.get("campaign"), str):
            return None
        cited = [result["campaign"], *(result.get("topups") or []),
                 *(index_topups.get(result["campaign"]) or [])]
        try:
            per_model[model] = runs_from_campaigns(c for c in cited if isinstance(c, str))
        except (OSError, ValueError, TypeError):
            return None
    if not per_model:
        return None
    bundle = Path(record["bundle_path"]) if isinstance(record.get("bundle_path"), str) else None
    return from_runs(bundle, per_model, list(record.get("models") or per_model), **kwargs)


def improved(before: dict | None, after: dict | None) -> bool | None:
    """Did a revision clear a shape flag without raising a new one?

    None when either side is unassessable (no evidence either way).
    """
    if not (isinstance(before, dict) and isinstance(after, dict)
            and before.get("assessable") and after.get("assessable")):
        return None
    old = set(before.get("flags") or [])
    new = set(after.get("flags") or [])
    return bool(new < old)


def decisive_family(sig: dict | None, premises: list[dict] | None, weights: dict[str, float] | None) -> str | None:
    """The family of a task's decisive premise: the most-failed one when measured,
    else the heaviest by weight."""
    if not premises:
        return None
    rates = (sig or {}).get("premise_fail_rates") or {}
    weights = weights or {}
    measured = [p for p in premises if rates.get(p["id"]) is not None]
    pool = measured or premises
    best = max(pool, key=lambda p: ((rates.get(p["id"]) or 0.0) if measured else 0.0,
                                    weights.get(p["id"], 0.0), p["id"]))
    return best.get("family")


def batch_family_quotas(tasks: list[dict]) -> dict:
    """Trap-family diversity across a batch (spec 10_12 rule 1). Advisory.

    `tasks`: [{"bundle", "families": [...] | None, "decisive": family | None}].
    A task with no premise map is listed, not counted: an unknown family is not
    a diverse one, and it is not a repeated one either.
    """
    mapped = [t for t in tasks if t.get("families")]
    absent = sorted(t.get("bundle") or "?" for t in tasks if not t.get("families"))
    n = len(mapped)
    presence, decisive = {}, {}
    for task in mapped:
        for family in set(task["families"]):
            presence[family] = presence.get(family, 0) + 1
        if task.get("decisive"):
            decisive[task["decisive"]] = decisive.get(task["decisive"], 0) + 1
    flags = []
    if n:
        for family, count in sorted(decisive.items()):
            if count / n > policy.MAX_FAMILY_HEAVIEST_SHARE:
                flags.append(f"{family} is the decisive premise in {count}/{n} tasks "
                             f"({count / n:.0%} > {policy.MAX_FAMILY_HEAVIEST_SHARE:.0%})")
        for family, count in sorted(presence.items()):
            if count / n > policy.MAX_FAMILY_PRESENCE_SHARE:
                flags.append(f"{family} appears in {count}/{n} tasks "
                             f"({count / n:.0%} > {policy.MAX_FAMILY_PRESENCE_SHARE:.0%})")
        stamps = presence.get(policy.TIMESTAMP_FAMILY, 0)
        if stamps / n > policy.MAX_TIMESTAMP_TASK_SHARE:
            flags.append(f"timestamp ordering appears in {stamps}/{n} tasks "
                         f"({stamps / n:.0%} > {policy.MAX_TIMESTAMP_TASK_SHARE:.0%})")
        if len(presence) < policy.MIN_BATCH_FAMILIES:
            flags.append(f"{len(presence)} distinct famil{'y' if len(presence) == 1 else 'ies'} across "
                         f"{n} task(s); a batch carries at least {policy.MIN_BATCH_FAMILIES}")
    return {"tasks_with_map": n, "tasks_without_map": absent,
            "presence": {f: round(c / n, 3) for f, c in sorted(presence.items())} if n else {},
            "decisive": {f: round(c / n, 3) for f, c in sorted(decisive.items())} if n else {},
            "families": len(presence), "flags": flags,
            "limits": {"max_decisive_share": policy.MAX_FAMILY_HEAVIEST_SHARE,
                       "max_presence_share": policy.MAX_FAMILY_PRESENCE_SHARE,
                       "min_families": policy.MIN_BATCH_FAMILIES,
                       "max_timestamp_share": policy.MAX_TIMESTAMP_TASK_SHARE},
            "basis": "advisory: spec 10_12 asks for a varied decisive trap; nothing is held for it"}


def task_families(bundle: Path, sig: dict | None = None) -> dict:
    """{"families", "decisive"} for one bundle, from its premise map (None when absent)."""
    try:
        spec = json.loads((Path(bundle) / "authoring/spec.json").read_text())
    except (OSError, ValueError):
        return {"families": None, "decisive": None}
    from .author import premises
    if not isinstance(premises.raw_map(spec), list):
        return {"families": None, "decisive": None}
    shape = premises.design_shape(spec)
    entries = premises.entries(spec)
    return {"families": [f for f in shape["families"] if isinstance(f, str)],
            "decisive": decisive_family(sig, entries, shape["premise_weights"])}


# ---------------------------------------------------------------------------
# Rendering
# ---------------------------------------------------------------------------

def summary(sig: dict | None) -> dict:
    """The compact per-task row a batch report carries."""
    if not isinstance(sig, dict):
        return {"assessable": False, "shape": None}
    keep = ("assessable", "shape", "flags", "advisory_flags", "in_band", "spread_ok", "target_met",
            "hard_primary", "free_share", "constant_premises", "constant_checks", "dead_premises",
            "max_premise_phi", "premise_map", "reasons")
    row = {k: sig.get(k) for k in keep}
    row["models"] = {m: {k: (r or {}).get(k) for k in ("episodes", "passes", "pass_at_1", "distinct_scores",
                                                       "reward_sd", "pass_at_1_wilson90")}
                     for m, r in (sig.get("per_model") or {}).items()}
    row["steps"] = {m: {s: {k: v.get(k) for k in ("passes", "episodes", "distinct_scores", "reward_sd")}
                        for s, v in ((r or {}).get("steps") or {}).items()}
                    for m, r in (sig.get("per_model") or {}).items()}
    return row


#: What each shape needs from a hardening revision (fed to the designer).
HARDENING_NEEDS = {
    "TOO_EASY": "add an INDEPENDENT premise from a family this task does not use yet (its own item, "
                "its own document, its own atomic checks, at most the premise-share cap of its step), or "
                "raise a live premise's miss rate through salience. Never route existing checks through "
                "one premise.",
    "SORTING": "one model resolves nearly everything: add a premise aimed at THAT model (its measured "
               "tendencies are in your instructions) and keep the other model's premises at moderate miss "
               "rates -- the aim is that the same model passes some runs and fails others.",
    "CONSTANT_PREMISE": "a premise (or check) no run of either model resolved: either its resolving "
                        "sentence leaves a second defensible reading (fix the documents) or it is buried "
                        "past finding. Make it resolvable in some runs by raising its salience; never "
                        "leave a decision at 0 -- it carries no learning signal.",
    "FLAT": "runs score alike: failures arrive together or not at all. Put linked checks under separate "
            "premises, remove downstream restatements of graded decisions, and add independent premises "
            "with moderate miss rates so different runs miss different premises.",
    "FREE_HEAVY": "too much weight is passed by every run: re-aim free checks beyond the cap into NEW "
                  "premises, one family each.",
    "PREMISES_LINKED": "two premises fail in the same runs: move them onto different items and documents, "
                       "or merge them and add a genuinely independent one.",
    "CHECKS_LINKED": "every failing check in a step fails in the same runs: it is one decision wearing "
                     "several checks -- split it by the premise that decides each member.",
    "DEAD_PREMISE": "a premise no run missed: lower its salience or replace it with another family.",
    "PREMISE_RATE_OUT_OF_BAND": "tune each premise toward a 20-60% miss rate on the model it targets.",
    "PREMISE_MAP_ABSENT": "record quality.premise_map (id, family, checks, targets, resolving_quote) for "
                          "every premise so the next screen can measure each one.",
}


def hardening_text(sig: dict | None) -> str:
    """The training-signal section of a hardening brief: aggregates and needs only."""
    head = ["TRAINING SIGNAL OF THE VERSION YOU ARE REVISING (Arena 261013 / spec 10_12; aggregates "
            "only -- never solver answers or per-episode rewards):"]
    body = lines(sig)
    needs = []
    if isinstance(sig, dict) and sig.get("assessable"):
        for flag in [*(sig.get("flags") or []), *(sig.get("advisory_flags") or [])]:
            if flag in HARDENING_NEEDS:
                needs.append(f"  {flag}: {HARDENING_NEEDS[flag]}")
        if sig.get("target_met"):
            needs.append("  The band and the spread are met: keep them -- do not push any premise toward "
                         "0 or 100%.")
    else:
        needs.append("  Not assessable: design to the V4 band and spread targets and record the premise map.")
    return "\n".join(head + body + (["What this shape needs:"] + needs if needs else []))


def lines(sig: dict | None) -> list[str]:
    """Readable lines for a report or a hardening brief."""
    if not isinstance(sig, dict):
        return ["training signal: not measured"]
    if not sig.get("assessable"):
        return ["training signal: not assessable -- " + "; ".join(sig.get("reasons") or [])[:400]]
    out = [f"training signal: {sig['shape']} (in band: {'yes' if sig['in_band'] else 'no'}; spread ok: "
           f"{'yes' if sig['spread_ok'] else 'no'}; premise map {sig.get('premise_map')})"]
    for model, row in (sig.get("per_model") or {}).items():
        ci = row.get("pass_at_1_wilson90")
        out.append(f"  {model.split('/')[-1]}: full {row['passes']}/{row['episodes']}"
                   + (f" (90% CI {ci[0]:.2f}-{ci[1]:.2f})" if ci else "")
                   + f", {row['distinct_scores']} distinct, SD {row['reward_sd'] or 0:.3f}")
        if len(row.get("steps") or {}) > 1:
            for step, srow in row["steps"].items():
                out.append(f"    {step}: full {srow['passes']}/{srow['episodes']}, "
                           f"{srow['distinct_scores']} distinct, SD {srow['reward_sd'] or 0:.3f}")
        if row.get("premise_fail_rates"):
            out.append("    premise miss rates: " + ", ".join(
                f"{p} {r:.2f}" if r is not None else f"{p} --" for p, r in row["premise_fail_rates"].items()))
    if sig.get("free_share") is not None:
        out.append(f"  observed free share (max over steps): {sig['free_share']:.0%}")
    if sig.get("max_premise_phi") is not None:
        out.append(f"  max pairwise premise phi: {sig['max_premise_phi']:.2f}")
    out += [f"  - {reason}" for reason in sig.get("reasons") or []]
    return out
