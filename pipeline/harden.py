#!/usr/bin/env python3
"""Stage H -- make a measured task genuinely harder, on purpose, by hand.

This is the one stage that never runs itself. `arena build` does not call it,
no environment variable turns it on, and it refuses a bundle that has not first
been calibrated. You pick the task; it revises a copy and proves the copy is
still legitimate. The original is never written to.

How a revision is made. The agent designer -- the same author that built the
task, with the whole fixture, the whole trace and its own evaluator in reach --
is handed the task's retained spec, the checks every model already passes, and
the hardening brief below. It adds traps grounded in the trace's scenario and
re-aims the free checks. New trap material can only enter as disclosed scenario
supplements (`author/scenario.py`), which earn no source credit and are bounded
by the category's fidelity allowance; the recovered documents stay immutable.

Each attempt must then clear, in cost order:

  validation and the no-weakening rules   free
  faithfulness level no lower than before free (ledger re-measured)
  probes, gate chain, shipped grader      free

and a revision that clears them is then MEASURED: the calibration screen
(`screen.py`) -- `policy.SCREEN_EPISODES_PER_MODEL` episodes on each of the two
calibration models -- and a comparison against the version it revised. Only
its aggregate per-check pass rates reach the next attempt, never solver answers
or per-episode rewards. Any revision whose screen measured cleanly may take the
ten-episode calibration of record (`arena qualify`).

Faithfulness is budgeted, not hoped for. Before designing, the task's room is
computed from its ledger and traps (`faithfulness_budget`): how many authored
traps keep the trace-derived share at the level's floor, and how many authored
bytes keep fidelity at the level's and the category's floor. The brief states
it, and an attempt that spends more -- or drops a trap from a real correction,
or lowers the level -- is refused.

THE ATTEMPT BUDGET. A task gets at most `policy.MAX_HARDENING_ATTEMPTS` (3)
redesigns over its whole lineage -- the original and every revision built from
it, across every invocation -- recorded in `<original>/hardened/hardening.json`
and never reset. Every designer call that returns a revision counts, validity
repairs included. There is no incremental loop:

  attempt 1  HARDEN   the full brief, told it is the one attempt that must make
                      the task extremely hard; nothing held back for later
  then       validity checks; a valid revision is screened (5 x 2)
  attempt 2+ REPAIR   an invalid revision: fix exactly the cited findings
             TIGHTEN  a valid but still-easy or badly-shaped revision: tune each
                      premise's miss rate and add independent premises where
                      its training-signal shape says so (`pipeline.training_signal`)

The lineage stops -- and `arena harden` then refuses it -- when a screen meets
the target, when the budget is spent, when a validity finding repeats or the
finding set fails to shrink, when a screened revision made no progress (pass@1
fell on neither model and no training-signal flag cleared), or when the designer
rejects the source. The target (user, 2026-10-13; Arena 261013, spec 10_12) is a
band with a gradient: every step at or under policy.STEP_PASS_RATE_MAX, pass@1 at
or under policy.EXTREME_PASS_AT_1_MAX on both models and every step, reward
spread on every model and step, no model sorting and no constant premise
(`_target_met`). Solver answers
and per-episode rewards are never fed back; per-check pass rates are, as they
always were.

What it may not change, each for a measured reason:

  the scenario or source  a fixture that drifts produces a task about nothing
  a check's existence     deleting a check raises the mean and teaches less
  `requires` chains       43% of kw-a010's weight sat behind checks nobody
                          reached; gating is not difficulty, it is unreachability

A built revision is a candidate, not a result. It is accepted only by the
comparison after its own two-model screen, and only when pass@1 falls with
every failure attributed to the model (`attribution.problems`).

Usage:
    ./arena harden --candidates          rank tasks by how much is hardenable
    ./arena harden <bundle>              report only; writes nothing
    ./arena harden <bundle> --apply      harden within the 3-attempt budget: revise,
                                         screen each valid revision (5 x 2), stop at
                                         target met / exhausted / no progress
                                         (--no-screen: build the revision only)
    ./arena harden <bundle> --apply --trap "IDEA" [--trap ...] [--traps ideas.json]
                                         ...also build the traps you ask for, each
                                         held to the same legitimacy rules and to
                                         the task's faithfulness budget (report
                                         mode prints that budget)
    ./arena harden <rev> --compare <bundle>   accept or reject a calibrated revision
"""
from __future__ import annotations

import contextlib
import json
import re
import shutil
import time
from pathlib import Path

from . import policy
from .config import bundle_paths

ROOT = Path(__file__).resolve().parent.parent
LEVEL_RANK = {"F-1": -1, "F0": 0, "F1": 1, "F2": 2, "F3": 3}


def _calibrations(bundle: Path) -> list[Path]:
    return sorted((bundle / "verification").glob("calibration-*.json"))


def baseline(bundle: Path) -> dict:
    """Verify current evidence and retain each model/step as a separate cohort."""
    from .artifacts import identity
    from .author.contracts import strict_json
    from .evidence import calibration_problems
    from .measurement import profile
    from .metrics import task_metrics
    reports, errors = [], []
    try:
        fingerprint = identity(bundle)
    except ValueError as exc:
        return {"ok": False, "errors": [str(exc)], "models": [], "by_model": {},
                "reports": {}, "checks": {}, "means": []}
    index = bundle / "verification/native-calibrations.json"
    from . import screen
    screened = screen.current(bundle)
    if screened and not (index.is_file() and _index_current(index, fingerprint)):
        # The calibration screen of this exact version: what every freshly
        # built batch and every hardening round is measured by.
        from .release import calibration_measurement
        manifest = screened.get("index") or {}
        for path in manifest.get("campaigns", []):
            try:
                problems, measured = calibration_measurement(bundle, manifest, path, 1)
            except (OSError, ValueError, KeyError, TypeError) as exc:
                errors.append(str(exc))
                continue
            errors.extend(problems)
            reports.append(measured)
    elif index.is_file():
        try:
            manifest = strict_json(index.read_text())
            if manifest.get("artifact_sha256") != identity(bundle):
                raise ValueError("native calibration index belongs to a stale task version")
            from .release import calibration_measurement
            for path in manifest.get("campaigns", []):
                problems, measured = calibration_measurement(bundle, manifest, path, 1)
                errors.extend(problems)
                reports.append(measured)
        except (OSError, ValueError, KeyError, TypeError) as exc:
            errors.append(str(exc))
    else:
        for file in _calibrations(bundle):
            try:
                report = strict_json(file.read_text())
                errors.extend(calibration_problems(bundle, report))
                reports.append(report)
            except (OSError, ValueError, KeyError, TypeError) as exc:
                errors.append(f"{file.name}: {exc}")
    if not reports:
        errors.append("no calibration on record. Measure a frozen baseline first.")
    models, raw, checks, means = {}, {}, {}, []
    for report in reports:
        model = report.get("model")
        if not model or model in models:
            errors.append("missing or repeated model campaign; select one frozen campaign per model")
            continue
        steps = {step: profile(row["checks"]) for step, row in report.get("by_step", {}).items()}
        if not steps:
            errors.append(f"{model}: missing per-step counts")
        rates = task_metrics(report)
        from .attribution import attribute
        from .metrics import capability_difficulty
        try:
            diagnostic = capability_difficulty(attribute(bundle, report)["counts"],
                                               policy.SCREEN_EPISODES_PER_MODEL)
        except (OSError, ValueError, KeyError, TypeError) as exc:
            errors.append(f"{model}: capability attribution could not run: {exc}")
            diagnostic = capability_difficulty({"unattributed": 1})
        models[model] = {"steps": steps, "protocol": report.get("protocol"),
                         "effort": report.get("effort"),
                         "limits": report.get("limits", {"max_steps": report.get("max_steps"),
                                                         "max_tokens": report.get("max_tokens")}),
                         "pass_at_1": rates["pass_at_1"],
                         "capability_difficulty": diagnostic,
                         "episodes_valid": rates["episodes_valid"]}
        raw[model] = report
        means.append(report.get("summary", {}).get("mean_reward"))
        for step, data in steps.items():
            for cid, rec in data["checks"].items():
                if rec.get("kind") == "guardrail":
                    continue
                key = f"{step}/{cid}"
                row = checks.setdefault(key, {"id": cid, "step": step, "weight": rec.get("weight", 0), "by_model": {}})
                row["by_model"][model] = rec
    return {"ok": not errors, "errors": errors, "models": list(models),
            "by_model": models, "reports": raw, "means": means, "checks": checks,
            "artifact_sha256": fingerprint}


def _index_current(index: Path, fingerprint: str) -> bool:
    from .author.contracts import strict_json
    try:
        return strict_json(index.read_text()).get("artifact_sha256") == fingerprint
    except (OSError, ValueError):
        return False


def hardenable(bundle: Path) -> dict:
    """Select objectives easy on every measured model; never infer pooled core."""
    base = baseline(bundle)
    groups = {k: [] for k in ("floor", "already_hard", "in_band", "unreachable", "transition", "mixed_models")}
    for key, rec in sorted(base.get("checks", {}).items()):
        rows = rec["by_model"]
        bands = {r["band"] for r in rows.values()}
        if len(rows) != len(base["models"]) or "unreachable" in bands:
            groups["unreachable"].append(key)
        elif bands == {"floor"}:
            groups["floor"].append({"id": rec["id"], "step": rec["step"], "weight": rec["weight"],
                                    "rate": min(r["rate"] for r in rows.values())})
        else:
            group = ({"core": "in_band", "stretch": "already_hard", "transition": "transition"}
                     .get(next(iter(bands))) if len(bands) == 1 else "mixed_models")
            groups[group].append(key)
    return {**base, **groups, "free_weight": sum(c["weight"] for c in groups["floor"])}


def hardening_targets(report: dict) -> list[dict]:
    """Re-aim verified objectives easy on every conservative binding model."""
    import math
    from .benchmark.harbor import resolve_model
    from .measurement import FLOOR_LO

    def score(value):
        return type(value) in (int, float) and math.isfinite(value) and 0 <= value <= 1

    if (report.get("ok") is not True or report.get("errors")
            or report.get("measurement_complete") is False or report.get("stale") is True):
        return []
    floors = report.get("floor") or []
    unreachable = set(report.get("unreachable") or [])
    if "checks" not in report and not report.get("by_model"):
        return [dict(target) for target in floors if isinstance(target, dict)
                and target.get("kind") in (None, "objective")
                and f"{target.get('step')}/{target.get('id')}" not in unreachable
                and score(target.get("rate")) and target["rate"] >= FLOOR_LO]
    cohorts, checks = report.get("by_model"), report.get("checks")
    if (not isinstance(cohorts, dict) or not isinstance(checks, dict)
            or not isinstance(report.get("models"), list) or not all(isinstance(model, str) for model in report["models"])
            or set(report["models"]) != set(cohorts) or len(report["models"]) != len(cohorts)
            or report.get("measurement_complete") is False or report.get("stale") is True):
        return []
    try:
        required = set(map(resolve_model, policy.resolve_calibration_models()))
        resolved = {model: resolve_model(model) for model in cohorts}
    except (TypeError, ValueError):
        return []
    if len(required) != 2 or set(resolved.values()) != required or len(resolved) != len(required):
        return []
    rates = {}
    for model, cohort in cohorts.items():
        if not isinstance(cohort, dict):
            return []
        diagnostic = cohort.get("capability_difficulty") or {}
        if not isinstance(diagnostic, dict):
            return []
        adjusted = diagnostic.get("capability_adjusted_pass_at_1")
        count = cohort.get("episodes_valid")
        if (not score(cohort.get("pass_at_1")) or not score(adjusted)
                or adjusted < cohort["pass_at_1"] or type(count) is not int
                or count < policy.SCREEN_EPISODES_PER_MODEL
                or type(diagnostic.get("episodes_valid")) is not int or diagnostic["episodes_valid"] != count
                or cohort.get("effort") != policy.SPEC_CALIBRATION_EFFORT
                or not isinstance(cohort.get("limits"), dict) or cohort["limits"].get("no_limits") is not True
                or not isinstance(cohort.get("steps"), dict)):
            return []
        rates[model] = adjusted
    highest = max(rates.values())
    binding = sorted(model for model, rate in rates.items() if rate == highest)
    existing = {f"{target['step']}/{target['id']}": target for target in floors
                if isinstance(target, dict) and "step" in target and "id" in target}
    selected = []
    for key, check in sorted(checks.items()):
        if not isinstance(check, dict) or check.get("kind") not in (None, "objective") or key in unreachable:
            continue
        rows = check.get("by_model")
        if (not isinstance(rows, dict) or set(rows) != set(cohorts)
                or not isinstance(check.get("id"), str) or not check["id"]
                or not isinstance(check.get("step"), str) or not check["step"]
                or key != f"{check['step']}/{check['id']}"
                or type(check.get("weight")) not in (int, float)
                or not math.isfinite(check["weight"]) or check["weight"] <= 0):
            continue
        observed = {}
        for model, row in rows.items():
            step = cohorts[model]["steps"].get(check["step"])
            step_checks = step.get("checks") if isinstance(step, dict) else None
            if (not isinstance(row, dict) or row.get("kind") != "objective"
                    or not isinstance(step_checks, dict) or step_checks.get(check["id"]) != row
                    or type(row.get("weight")) not in (int, float) or row["weight"] != check["weight"]
                    or any(type(row.get(name)) is not int or row[name] < 0 for name in ("passed", "failed", "gated_out"))
                    or row["gated_out"] != 0 or row["passed"] + row["failed"] != cohorts[model]["episodes_valid"]
                    or not score(row.get("rate"))
                    or row["rate"] != row["passed"] / (row["passed"] + row["failed"])):
                break
            observed[model] = row["rate"]
        if len(observed) != len(cohorts) or any(observed[model] < FLOOR_LO or rows[model].get("band") != "floor" for model in binding):
            continue
        if key in existing and all(rate >= FLOOR_LO for rate in observed.values()):
            selected.append(dict(existing[key]))
        else:
            selected.append({"id": check["id"], "step": check["step"], "weight": check["weight"],
                             "rate": min(observed[model] for model in binding),
                             "binding_models": [resolved[model] for model in binding]})
    return selected


def candidates(root: Path) -> list[dict]:
    """Rank built tasks by how much of their score is currently a free point."""
    rows = []
    for bundle in bundle_paths(root):
        report = hardenable(bundle)
        targets = hardening_targets(report)
        rows.append({"bundle": bundle.name,
                     "ok": report["ok"],
                     "errors": report["errors"],
                     "target_checks": len(targets),
                     "target_weight": sum(target["weight"] for target in targets),
                     "floor_checks": len(report["floor"]),
                     "free_weight": report["free_weight"],
                     "in_band": len(report.get("in_band", [])),
                     "already_hard": len(report.get("already_hard", [])),
                     "means": report.get("means", [])})
    rows.sort(key=lambda row: (-row["target_weight"], -row["free_weight"], -row["floor_checks"]))
    return rows


HARDENING_BRIEF = """\
V2.2 INTERLOCKS (user, 2026-10-02: "combine multiple difficulty/hardening levers to
make the tasks extremely extremely hard") -- SUPERSEDED IN PART by the V4
conjunctive block above (Arena 261013): levers may still be stacked on ONE
premise's item to set that premise's miss rate, but each premise keeps its own
checks and different premises stay on different items, so their failures stay
independent. (Retired here: "re-aim every never-failed check through an
interlock", "a cascade through a changed premise", "several levers on every
graded item".) Every single mechanism was solved in every episode of the lever
lab once it was the puzzle (the measured table is in your instructions), which
is why no single premise may carry the task. Good ways to set one premise's miss
rate: masking pairs (a conspicuous problem plus a silent interacting fact, some
conspicuous problems being false alarms), reallocations the control total cannot
see, opposite-skew populations (some items must be held although they look
resolvable, others resolved although they look conflicted). Record each in
quality.fragility_budget with `levers` and one executed `baseline_partial_...`
counterexample per lever missed in turn, and every premise in
quality.premise_map. Nothing is labelled, announced or explained in any
agent-visible file; every rule stays published once and every answer stays the
one a careful expert would defend.

V2.1 FIRST (research/R6): this task was measured with noticing traps, which these
agents defeat for free. Before anything else, audit every fragile decision against the
V2.1 admission test in your instructions and REBUILD the ones that fail it on routes
b-e: strip rule text that names its own decoy or exception, remove labels/notes from
trap rows, move applicability evidence out of the rule's document, make the step-2
news raw facts in a third party's words, take procedure out of the field definitions,
add discriminating data for every compound rule, and ship the idiomatic baseline as
an executed counterexample (id baseline_...) that fails each rebuilt check. Read the
review's difficulty advisories below: they predicted the measured result.

HARDEN THIS TASK. The staged draft is a working, calibrated task that frontier
models find too easy. Make it genuinely hard, so that a strong model fails it
for its own reasons and never for ours.

Checks every measured model already passes -- the free points you MUST re-aim
(V4: into NEW independent premises of their own; free weight up to the cap may
stay free):
{targets}

Calibration of the version you are revising -- per-check pass rates, the model
that binds, and the traps that never cost a point:
{breadth}

1. DE-LEAK THE INSTRUCTION FIRST, before adding anything -- and de-leak means
   REMOVE THE ANALYSIS, NEVER THE MEANING. The last batch's reviewer found
   every planted trap neutralised by numbered rules in the public instruction.
   A LEAK is answer-side commentary identifying the winning items or walking
   through a solved conflict, revision or residue. Remove that commentary, not
   a normative rule. Naming a governing document is NOT automatically a leak:
   preserve it when the public contract specifies that authority. Precedence,
   effective-time and original-versus-projected conventions must remain public.
   A sentence that decides a field's
   SCOPE, an EXCLUSION, a BOUNDARY or an EDGE-CASE CONVENTION -- which items a
   field counts, what a value means when a condition holds, what is "ours to
   edit", which exports carry no date -- is the field's MEANING and MUST STAY:
   removing it does not harden the task, it makes a second reading defensible,
   and the qualify review then reverses the drop. Measured 2026-09-28: of ten
   hardened lineages none measured legitimately harder, and the two apparent
   wins (a-055, a-047) were deleted scope sentences, each a single-model drop
   with every failing episode on the same alternative reading. Two more
   limits: a sentence that is the rule_quote of a measured check you may not
   change stays, and every field the schema requires stays defined by meaning
   and exact format. For EVERY sentence you remove, say in
   quality.difficulty_case.first_try_verdict why it was a leak and not a scope
   rule; the pipeline diffs the instruction and lists removed scope sentences
   for review before the screen.

2. UNDERSTAND FIRST. Read every fixture document, the original request and every
   user correction (read_fixture, read_trace, list_corrections) before changing
   anything. The traps must belong to this scenario and this domain: the
   mistakes a practitioner in this situation would actually make.

3. SOURCE-SUPPORTED DIFFICULTY HYPOTHESES -- earlier measurements motivate
   candidates, not guarantees about the exact models now being tested. More
   enumeration alone has not reliably hardened this corpus. Test a PREMISE THAT CHANGES,
   or a conflict over which
   document governs, that silently invalidates a result the model has already
   computed, and a PLAUSIBLE MISREADING that agrees with the right answer on
   most items. Plant from this set, inside small populations (every measured
   killer lives in 9-130 rows), with the trap where the computation happens:
   - REVISED PREMISE: a threshold, scope or definition moves after a first
     result is computed, so every item already judged must be judged again.
   - GOVERNING CONFLICT: two documents state a number, name or status
     differently, and a published precedence criterion (in the fixture where a
     professional would find it; in the instruction only when no document can
     carry it) makes the less obvious document govern. The criterion is
     published; which document meets it is never stated.
   - RESIDUE: something declared done or retired is still present in the very
     document that declares it done.
   - MERGED CONCEPTS: two related terms that agree on most rows and differ on a
     few, built on a real professional convention a generalist merges and an
     expert separates (retention versus payable, accrual versus cash).
   - NEAR-MISS DECOY: the wrong candidate is nearly right -- the prior revision,
     a sibling entity's policy, the same term in another scope -- and differs on
     the one attribute the decision turns on. Unrelated filler is not a decoy.
   - IMPLICIT INVALIDATION: a later fact overturns an earlier conclusion without
     naming it, and the decisions that depended on it must be re-judged.
   Preserve the published equivalence, rounding and tolerance contract. More
   coherent candidates and evidence are allowed within source-fidelity and
   scenario budgets when they add a genuine discriminator or interaction;
   arbitrary length and output bulk are not difficulty. Do not add derivation depth
   for its own sake: depth with no premise inside it has measured 1.00. Depth
   that carries a premise is different -- a deadline derived from a milestone
   the revision moved, a total whose included items the governing conflict
   decides. Put the premise where the computation happens.

4. INDEPENDENT PREMISES, EACH ON ITS OWN CHECKS (V4, Arena 261013; this
   replaces the V2 rule "route several checks through each premise", which made
   every failing check fail in the same runs and flattened the reward). Every
   independent premise a run must resolve is another chance to slip, and pass@1
   counts only full success -- so add premises, not checks per premise: one
   premise, one decision, its own atomic exact check(s); never two premises
   inside one exact-equality check; never a downstream restatement of a graded
   decision as an extra check. Free weight stays at or under the cap: re-aim
   EVERY free check beyond it into a NEW premise of its own, from a family this
   task does not use yet, and name it in quality.premise_map and in that
   premise's misreading in quality.difficulty_case. Never split one calculation
   into several checks to multiply its weight. One premise per family per task
   (same-family premises fail together), at most one timestamp-ordering premise,
   and each premise on a different item and document from the others, so fixing
   one and missing another loses exactly the missed premise's weight. Their kind follows the task's faithfulness level: at
   F3, from the trace first -- a revision the user actually made, a document
   the user said governs, something the user said was retired -- plus
   additional traps aligned with the trace's scenario; below F3, genuine
   invented traps relevant to the task are equally welcome. Supporting traps
   (a superseded revision, a misleading label, a near-duplicate, an item that
   looks in scope and is not, a requirement nothing can satisfy) belong INSIDE
   their premise's population, not beside it. Harden first against the BINDING
   MODEL named above: the band is pass@1 at or below <<EXTREME>> on BOTH models,
   so the model that passes more often decides whether the task is hard -- but
   never by making one premise unresolvable for both.

   Make each trap as deceptive as the EVIDENCE legitimately allows -- the
   requirements themselves stay perfectly clear. The wrong reading should be the
   natural one: the decoy is the fuller, more recent or more official-looking
   record; the governing rule is plain and easy to skim past; two rules interact
   so that applying either alone gives a confident wrong answer. Deceptive
   evidence is not unfairness -- the rule that settles it must be PUBLISHED
   where a professional finds it: the fixture document that carries the
   precedence, the revised threshold or the retirement (a contract clause, a
   policy memo, a rate sheet's notes), or the instruction only when no document
   can carry it. Do not announce the solved source-selection answer, but retain
   explicit normative authority and revision conventions in the public contract.
   Answer-side hints neutralise a trap; normative rules define a fair task. The model
   must fail at APPLYING a rule it was given, never at guessing one. Every
   filter a trap adds cites where its rule is published: `rule_sources` with
   the verbatim sentence from the fixture document that states it (v2: the
   normal case -- do NOT move a document's rule into the instruction, which
   makes the trap dead), or `rule_quote` from the instruction only when no
   document can carry it. Every value the filter tests must be findable in the
   files; prefer deriving the condition from a document-bound value (bind_rows,
   compare, latest). A trap whose rule is published nowhere is refused
   (hidden-rule gate), and a failure it causes is not the model's.

5. EVERY TRAP MUST BE GENUINE:
   - grounded: trace_derived with the user's verbatim words, or authored with
     grounded_in naming a fixture file and a practitioner's reason
   - resolvable: the rule that settles it is stated in the instruction or in a
     fixture document. No hidden rules, unstated conventions or overlapping
     category definitions -- Arena rejected all three in the first delivery
   - beatable: the reference solution resolves it with the given tools, and a
     correct answer written differently still passes
   - graded: it drives at least one declared check of its own -- no check
     another premise already decides (one decision = one check)
   A trap in the never-bit list above is not yet genuine: every check it drives
   passed every attempt, so it cost nothing. Re-aim it or replace it.

{requested}6. KEEP FAITHFULNESS. Recovered documents are immutable. New trap material goes
   only into write_scenario supplements: disclosed, synthetic, no source
   credit, capped by the category's fidelity allowance. Prefer traps built from
   surfaces the recovered documents already contain and from real corrections;
   a revision that lowers the task's faithfulness level is refused.

   Your budget for this task, measured from its ledger and traps:
{budget}

7. DO NOT: delete, weaken or REGENERATE a check: copy every untargeted check,
   guardrails included, verbatim from the staged draft -- the validator compares
   every graded field, and a fixture guard rebuilt from scratch (fixture swapped
   for fixture_files, target dropped, dimension renamed) is a changed check, not
   the same one; add `requires` chains (unreachable is not
   hard); change the scenario or source; add tolerance; enlarge an answer set
   for its own sake (Answer size does not predict difficulty: 16-40 item
   answers passed at 75%, 4-7 item answers at 33%); tune the answer key or the
   evidence to a solver's particular output -- you receive per-check pass rates
   and the trap audit above, never solver answers, and a trap is genuine only
   when a careful professional could make the same mistake. The band limits
   still hold (<<BANDS>>): add a check only where a band has room, otherwise
   pay for a new premise's check by re-aiming a free one.

WHAT THE SCREEN DOES WITH THIS REVISION. It is measured on both models. A check
that fails every episode is admitted only with its executed source
counterfactual and a passing reworded answer, and every failed episode is
classified capability, contract or void; a failure no declared trap explains is
a defect to repair, not difficulty. Predict every failure you expect: one
misreading per trap, each encoded by its own counterexample.

If this source cannot support genuine hard traps, call reject_seed with the
evidence. That is a legitimate outcome; inventing hidden rules is not.
"""


def _bands_text() -> str:
    from .author.quality import BAND_LIMITS
    return ", ".join(f"{band} {low}-{high}" for band, (low, high) in BAND_LIMITS.items())


HARDENING_BRIEF = (HARDENING_BRIEF.replace("<<BANDS>>", _bands_text())
                   .replace("<<EXTREME>>", str(policy.EXTREME_PASS_AT_1_MAX)))

#: The V4 conjunctive hardening block (Arena 261013 review, spec 10_12; the user
#: approved the design 2026-10-13). It leads every HARDEN/TIGHTEN brief, ahead of
#: HARDENING_BRIEF, and wins where the older text conflicts.
CONJUNCTIVE_HARDENING = f"""\
V4 CONJUNCTIVE HARDENING (Arena 261013 review, spec 10_12; approved 2026-10-13).
THIS BLOCK WINS over anything below it that conflicts -- including "V2.2
INTERLOCKS" and any older wording about routing checks through a premise.

THE TARGET IS A BAND WITH A GRADIENT, NOT ZERO. This lineage ends as target-met
only when BOTH models fully pass at most {policy.EXTREME_PASS_AT_1_MAX:.0%} of runs, on the task and on
every step, AND every model's scores on every step take at least
{policy.MIN_DISTINCT_SCORES_PER_MODEL} distinct values with SD >= {policy.MIN_RUN_REWARD_SD}, no model passes >= {policy.MODEL_SORTING_HIGH_PASS_AT_1:.0%} while
the other passes <= {policy.MODEL_SORTING_LOW_PASS_AT_1:.0%}, and no premise goes unresolved in every run. A
revision that drives the task to 0/10 through one premise nobody resolves has
made it WORSE: a constant decision teaches nothing and is the ambiguity
signature. "Hard" on the primary (<= {policy.EXTREME_PRIMARY_PASS_AT_1_PREFERRED:.0%}) is preferred, not required.

HOW TO HARDEN:
 - Lower full success by ADDING INDEPENDENT PREMISES: a family this task does not
   use yet, on a different item and document, graded by its OWN atomic exact
   checks (one decision = one check), each premise at most {policy.MAX_PREMISE_SHARE:.0%} of its step's
   objective weight. Aim at {policy.MIN_INDEPENDENT_PREMISES}-5 premises in a single-step task, or at least
   {policy.MIN_PREMISES_PER_STEP_MULTI_TURN} per step and {policy.MIN_PREMISES_MULTI_TURN_TOTAL} overall in a multi-turn task, each missed in roughly
   {policy.PREMISE_MISS_RATE_BAND[0]:.0%}-{policy.PREMISE_MISS_RATE_BAND[1]:.0%} of careful runs on the model it targets.
 - Tune a premise's miss rate with SALIENCE, never with ambiguity: an anchor
   moved out of the thread or into a long background document is missed more;
   one cross-posted or placed beside the item is noticed more. Every premise
   keeps one explicit resolving sentence in the files (spec 10_12: every
   inference resolvable from the materials).
 - NEVER route an existing check through another premise and never add a check
   that restates an upstream decision (a total of a graded set, a verdict from a
   graded count): that links failures and flattens the reward.
 - FREE weight (checks no premise decides) at most {policy.MAX_FREE_SHARE:.0%} of each step; re-aim
   free checks beyond that into NEW premises, one family each.
 - At most {policy.MAX_TIMESTAMP_PREMISES_PER_TASK} timestamp-ordering premise per task (clock offsets, store/outage
   windows, impossible stamps are ONE family); it is never the default lever.
 - Keep quality.premise_map current for every premise you add or change; the
   next screen measures each premise from it.
The TRAINING SIGNAL section at the end of this brief says which shape the
measured version has and what that shape needs.
"""

#: What the designer is told about WHICH attempt this is. The first is the one
#: that must do the work (user, 2026-09-25): no incremental hardening.
FIRST_ATTEMPT = """\
ATTEMPT {n} OF {of} -- THE ONE THAT MUST MAKE THIS TASK EXTREMELY HARD.
There is no incremental hardening loop. This task gets at most {of} redesigns,
ever ({left} left after this one), and any after this exist only to repair what
this revision breaks or to tighten what its measurement shows it missed.
Hold nothing back for a later round: de-leak the instruction first (brief
step 1), then install the INDEPENDENT premises the V4 block asks for NOW -- each
from a different family, on its own item, document and checks, free weight at
or under the cap -- and set each one's miss rate through the EVIDENCE (salience),
never the requirements, which stay perfectly clear -- while the task keeps
meeting every requirement of
the ARENA QUALITY BAR (system prompt): every rule published, every check
failable, passable and reachable, nothing leaked, grounded in the trace's
situation. A revision that is merely harder than the original has wasted most of
the budget; one that trades quality for difficulty is broken. Run the TRAP HUNT again across every
pitfall family (system prompt) for this revision, and rewrite
quality.difficulty_case: one misreading per trap, each encoded by a
counterexample, and pitfalls_considered covering every trap.
"""

TIGHTEN_ATTEMPT = """\
ATTEMPT {n} OF {of} -- TIGHTEN, DO NOT START OVER. The staged revision is valid
and was measured on both calibration models: it is still too easy. The per-check
pass rates below are REAL measurements of it -- use them. Keep every trap and
every check it has. You may change ONLY the objectives listed below: they are
floor checks on every measured model, or on ALL models tied for the highest
conservative capability-adjusted pass@1. A listed mixed-model objective need not
be easy on the other model. Do not reduce its weight. You may add checks where
a band has room; every other check stays
exactly as it is (a changed measured check is refused). Read the TRAINING
SIGNAL section and fix its shape: set each premise's miss rate through the
fixture evidence (write_scenario, within the budget) -- salience up for a dead
premise, down for one no run resolves; re-aim or replace every trap in the
never-bit list; turn listed free checks beyond the free cap into NEW independent
premises (own family, own checks) rather than routing them through an existing
premise. You may also de-leak the instruction (brief step 1): it touches no
check. Attempts left after this one: {left}.
"""

REPAIR_ATTEMPT = """\
ATTEMPT {n} OF {of} -- REPAIR ONLY. The staged revision failed the validity
checks listed after this message. Fix exactly those findings. Where a finding
prints the original check, restore it exactly as printed. Do not redesign,
do not add traps, and do not remove or weaken a trap or a check that is valid:
the difficulty this revision installed is the point. A finding that comes back
unchanged ends hardening for this task. Attempts left after this one: {left}.
Your faithfulness budget, measured from the ORIGINAL task:
{budget}
"""


def faithfulness_budget(bundle: Path, ledger: dict) -> dict:
    """How many authored traps and authored bytes this task can take and keep its level.

    F3 retains recovered-byte and correction-share floors. F2 instead requires
    semantic source alignment; no trap-share or recovered-byte quota establishes
    it. Category limits and the bounded scenario writer still constrain bytes.
    Every revision's final level is independently re-measured.
    """
    import math
    from .author import scenario
    from .ledger import levels
    record = levels.assign(bundle, ledger)
    level, measured = record["level"], record["measured"]
    total, derived = measured["traps_total"] or 0, measured["traps_trace_derived"] or 0
    fidelity = ledger.get("faithfulness_by_bytes") or 0.0
    size = sum((ledger.get("bytes") or {}).values())
    weighted = fidelity * size
    # Fidelity may not fall below the level's floor nor the source category's
    # (the scenario writer enforces the latter too), so authored bytes are
    # capped by the stricter of the two.
    floors = [f for f in (policy.FAITHFULNESS_FIDELITY_FLOOR.get(level),
                          policy.CATEGORY_FIXTURE_FLOOR.get(ledger.get("category"))) if f]
    bytes_ = min((math.floor(weighted / f - size) for f in floors), default=None)
    # F3 retains its correction share; F2 semantic grounding is not a trap quota.
    share_floor = policy.FAITHFULNESS_TRACE_DERIVED_FLOOR.get(level)
    traps = (max(0, math.floor(derived / share_floor + 1e-9) - total)
             if share_floor else None)          # None: no share floor at this level
    used = 0
    manifest = bundle / scenario.MANIFEST
    if manifest.is_file():
        used = sum(r.get("bytes", 0) for r in json.loads(manifest.read_text()).get("files", {}).values())
    cap = scenario.MAX_TOTAL_BYTES - used
    bytes_ = cap if bytes_ is None else min(bytes_, cap)
    return {"level": level, "traps_total": total, "traps_trace_derived": derived,
            "fidelity": fidelity, "authored_traps_left": traps,
            "authored_bytes_left": max(0, bytes_), "scenario_bytes_used": used}


def budget_problems(budget: dict, before: list[dict], after: list[dict],
                    bytes_added: int) -> list[str]:
    """Did a revision spend more faithfulness than the original task had to spare?"""
    def authored(traps):
        return sum(1 for t in traps if t.get("provenance") == "authored")
    problems = []
    added = authored(after) - authored(before)
    left = budget["authored_traps_left"]
    if left is not None and added > left:
        problems.append(f"the revision adds {added} authored trap(s); this {budget['level']} "
                        f"task has room for {left} before its trace-derived share falls "
                        "below the level's floor. Use real corrections instead")
    derived_before = {t.get("id") for t in before if t.get("provenance") == "trace_derived"}
    dropped = derived_before - {t.get("id") for t in after if t.get("provenance") == "trace_derived"}
    if dropped:
        problems.append(f"the revision removes or relabels trace-derived trap(s) {sorted(dropped)}; "
                        "a trap from a real correction is the task's faithfulness")
    if bytes_added > budget["authored_bytes_left"]:
        problems.append(f"the revision adds {bytes_added} authored scenario bytes; the "
                        f"budget is {budget['authored_bytes_left']}")
    return problems


#: A new trap must drive at least this many graded objectives. Was 2 ("a
#: premise that poisons one check barely moves pass@1; the measured killers each
#: took down three or more") until 2026-10-13: Arena 261013 showed that routing
#: several checks through one premise makes them fail in the same runs and
#: flattens the reward, so the conjunctive design gives each premise its OWN
#: check(s) -- one is enough -- and lowers full success by adding premises.
MIN_CHECKS_PER_NEW_TRAP = 1


def routing_problems(before: list[dict], after: list[dict], checks: list[dict]) -> list[str]:
    """Every trap the revision adds must read through several graded objectives."""
    objectives = {c.get("id") for c in checks if c.get("kind") == "objective"}
    known = {t.get("id") for t in before}
    out = []
    for trap in after:
        if trap.get("id") in known:
            continue
        driven = [c for c in trap.get("checks") or [] if c in objectives]
        if len(driven) < MIN_CHECKS_PER_NEW_TRAP:
            out.append(f"new trap {trap.get('id')} drives {len(driven)} graded objective(s); route "
                       f"at least {MIN_CHECKS_PER_NEW_TRAP} through it -- a trap that decides no graded "
                       "objective cannot cost a run anything")
    return out


def _budget_text(budget: dict) -> str:
    traps = budget["authored_traps_left"]
    lines = [f"     level {budget['level']}; {budget['traps_trace_derived']} of "
             f"{budget['traps_total']} traps cite a real correction; fixture fidelity "
             f"{budget['fidelity']:.0%}",
             "     authored traps you may add: "
             + ("no ceiling from this level" if traps is None else str(traps))
             + ". Traps citing a real user correction do not count against this -- "
               "prefer them.",
             f"     authored scenario bytes you may add: {budget['authored_bytes_left']}"]
    if traps == 0:
        lines.append("     You have NO room for authored traps: make the existing trace-"
                     "derived traps harder, or add traps that cite real corrections.")
    return "\n".join(lines)


def _requested_text(requested: list[str]) -> str:
    if not requested:
        return ""
    items = "\n".join(f"   - {idea}" for idea in requested)
    return ("4b. TRAPS THE OPERATOR ASKED FOR. Build each one if this source genuinely\n"
            "   supports it, under every rule in 4 and within the budget in 5. If one\n"
            "   cannot be made legitimate here, leave it out; never bend a rule for it.\n"
            f"{items}\n\n")


#: A trap whose every driven check passed at least this share of attempts on
#: every measured model cost nothing: it is dead until re-aimed or replaced.
DEAD_TRAP_PASS_RATE = 0.9


def _breadth_summary(bundle: Path, checks: list[dict], traps: list[dict] | None = None) -> str:
    """Per-check calibration pass rates, the binding model and the dead traps.

    (Named for its history: it used to print the measurement-breadth screen,
    whose lever the per-check calibration data has since superseded.)

    The binding model is the one with the higher pass@1: the target is below
    0.5 on BOTH, so it decides. A dead trap is one whose every driven check
    passed at least `DEAD_TRAP_PASS_RATE` of attempts on every model -- it is
    listed so the revision re-aims it instead of adding beside it. Only
    aggregates reach the designer: never solver answers or per-episode rewards.
    """
    report = hardenable(bundle)
    lines = []
    for key, rec in sorted(report.get("checks", {}).items()):
        rates = [r.get("rate") for r in rec["by_model"].values() if r.get("rate") is not None]
        if rates:
            lines.append(f"  {key}: passed by {min(rates):.0%}-{max(rates):.0%} of attempts "
                         f"(weight {rec.get('weight')})")
    if not lines:
        return "  no per-check calibration on record"
    rates = {m: (v.get("capability_difficulty") or {}).get("capability_adjusted_pass_at_1", v.get("pass_at_1"))
             for m, v in (report.get("by_model") or {}).items()
             if isinstance(v, dict) and v.get("pass_at_1") is not None}
    rates = {model: rate for model, rate in rates.items() if rate is not None}
    if any(isinstance(cohort, dict) and (cohort.get("capability_difficulty") or {}).get("capability_adjusted_pass_at_1") is not None
           for cohort in (report.get("by_model") or {}).values()):
        lines.append("  Binding comparison uses conservative capability-adjusted pass@1, not official rates.")
    if len(rates) >= 2:
        top = max(rates.values())
        leaders = sorted(m for m, r in rates.items() if r == top)
        if len(leaders) > 1:
            lines.append(f"  BINDING MODEL: tie at pass@1 {top:.2f} ({', '.join(leaders)}); "
                         "harden against both")
        else:
            binding = leaders[0]
            others = ", ".join(f"{m} {r:.2f}" for m, r in sorted(rates.items()) if m != binding)
            lines.append(f"  BINDING MODEL: {binding} (pass@1 {rates[binding]:.2f}; {others})")
    elif rates:
        (m, r), = rates.items()
        lines.append(f"  pass@1 on record for one model only: {m} {r:.2f}")
    by_id: dict[str, list[float]] = {}
    for rec in report.get("checks", {}).values():
        found = [r.get("rate") for r in rec["by_model"].values() if r.get("rate") is not None]
        if found:
            by_id.setdefault(rec["id"], []).append(min(found))
    dead, unmeasured = [], []
    for trap in traps or []:
        driven = [c for c in trap.get("checks") or [] if c in by_id]
        if not driven:
            unmeasured.append(str(trap.get("id")))
        elif all(min(by_id[c]) >= DEAD_TRAP_PASS_RATE for c in driven):
            dead.append(f"{trap.get('id')} (drives {', '.join(driven)})")
    if traps is not None:
        lines.append("  TRAPS THAT NEVER BIT (every check they drive passed by >= "
                     f"{DEAD_TRAP_PASS_RATE:.0%} of attempts on every model): "
                     + ("; ".join(dead) if dead else "none -- every trap cost some attempt a point"))
        if unmeasured:
            lines.append("  traps driving no measured check: " + ", ".join(unmeasured))
    return "\n".join(lines)


#: The last spec the designer returned for a working copy, kept whether or not
#: it validated. A REPAIR attempt continues from it: continuing from the copy's
#: authoring/spec.json -- the pre-revision spec when validation rejected the
#: revision before it was built -- threw the new traps away.
HARDENING_DRAFT = "verification/hardening-draft.json"


def _step_target_text(version: Path) -> str:
    """The per-step goal and the measured per-step rates of the version being revised."""
    from . import screen
    record = screen.current(version)
    if record is None:              # e.g. a provenance file added after the screen
        try:
            record = json.loads((Path(version) / screen.RECEIPT).read_text())
        except (OSError, ValueError):
            record = {}
    rates = step_pass_rates(record) or {}
    limit = policy.STEP_PASS_RATE_MAX
    band = policy.EXTREME_PASS_AT_1_MAX
    lines = [f"\n\nPER-STEP GOAL (user, 2026-10-02): EVERY step must be fully passed by at most "
             f"{limit:.0%} of episodes on BOTH calibration models; the V4 band (2026-10-13) is "
             f"{band:.0%}, with reward spread on every step. A whole-task pass@1 carried by "
             "one hard step does not count; each step is measured on its own."]
    if rates:
        steps = sorted({s for model in rates.values() for s in model})
        for step in steps:
            cells = ", ".join(f"{model.split('/')[-1]} {rates[model].get(step, 0):.0%}" for model in sorted(rates))
            easy = any(rates[model].get(step, 0) > band for model in rates)
            lines.append(f"  {step}: {cells}"
                         f"{'   <-- TOO EASY: needs another independent premise of its own' if easy else ''}")
    lines.append("For every step above the band, give that step at least one more INDEPENDENT premise "
                 "on checks OF THAT STEP: a step-1 trap does not make step 2 hard, and a step-2 trap does not make step 1 "
                 "hard. Each later step runs in a FRESH session that rereads the workspace and its "
                 "instruction, so its trap must bite a careful fresh reader: a revised premise, a "
                 "later note or an earlier record that silently invalidates a value the previous step "
                 "computed (measured: revision reach into an already-counted item, a later note "
                 "reinstating a cancelled item, a first-record rule over a later claim). Every such "
                 "trap stays determinate from the documents -- one answer, quoted governing text.")
    return "\n".join(lines)


def _signal_text(version: Path) -> str:
    """The training-signal shape of the version being revised, and what it needs.

    Aggregates only (full passes, distinct scores, SD, per-premise miss rates):
    never solver answers or per-episode rewards (policy.REPAIR_FEEDBACK_EXCLUDES).
    """
    from . import screen
    from . import training_signal as signal
    record = screen.current(version)
    if record is None:
        try:
            record = json.loads((Path(version) / screen.RECEIPT).read_text())
        except (OSError, ValueError):
            record = None
    return "\n\n" + signal.hardening_text(_signal_verdict(record))


def propose(bundle: Path, targets: list[dict], findings: list[str] | None = None,
            requested: list[str] | None = None, *, number: int = 1,
            of: int = policy.MAX_HARDENING_ATTEMPTS, kind: str = "harden",
            measured: Path | None = None, left: int = 0, tighten: bool = False) -> dict:
    """Ask the agent designer for a harder version of THIS spec, inside `bundle`.

    `bundle` is the working copy: scenario supplements the designer writes land
    there, never in the original. The source and category are carried across
    verbatim rather than trusted to come back unchanged.

    `kind` decides the brief: "harden" (the full brief -- the extremely-hard
    redesign, or with `tighten` a tightening of a measured revision) or
    "repair" (fix the cited validity findings only, continuing from the last
    returned draft). `measured` is the version whose calibration the per-check
    table is read from -- the working copy has none of its own.
    """
    from .author import agent_designer, extract
    from .repair import design_inputs

    if not (bundle / "authoring" / "spec.json").is_file():
        raise FileNotFoundError(
            f"{bundle / 'authoring' / 'spec.json'} is absent, so there is no design "
            "to revise. Bundles built before the spec was retained cannot be "
            "hardened; rebuild the task first.")
    spec, ledger, row = design_inputs(bundle)
    staged = spec
    draft = Path(bundle) / HARDENING_DRAFT
    if kind == "repair" and draft.is_file():
        from .author.contracts import strict_json
        staged = strict_json(draft.read_text())
    if kind == "repair":
        brief = REPAIR_ATTEMPT.format(n=number, of=of, left=left,
                                      budget=_budget_text(faithfulness_budget(
                                          measured or bundle, design_inputs(measured or bundle)[1])))
    else:
        from copy import deepcopy
        staged = deepcopy(staged)
        quality = staged.setdefault("quality", {})
        plan = quality.setdefault("capability_plan", {"mechanisms": []})
        plan["version"] = 2
        rendered = "\n".join(
            f"  {target['id']}  (weight {target['weight']}, passed by {target['rate']:.0%} of attempts"
            + (f" on binding models {', '.join(target['binding_models'])}" if target.get("binding_models") else " on every measured model") + ")"
            for target in targets) or "  none"
        header = (TIGHTEN_ATTEMPT.format(n=number, of=of, left=left) if tighten
                  else FIRST_ATTEMPT.format(n=number, of=of, left=left))
        brief = header + "\n" + CONJUNCTIVE_HARDENING + "\n" + HARDENING_BRIEF.format(
            targets=rendered,
            breadth=_breadth_summary(measured or bundle, spec.get("checks", []),
                                     traps=spec.get("traps") or []),
            requested=_requested_text(requested or []),
            budget=_budget_text(faithfulness_budget(bundle, ledger)))
        brief += ("\nThis is a manual hardness redesign: complete capability_plan version:2, "
                  "including independent interventions, joint-applicability hard negatives, "
                  "whole-answer decoy invariance, genuine coupling and competent tool baselines. "
                  "Do not relabel dependent fields or invent unsupported rules to satisfy this profile.")
        from .author.challenge import redesign_brief
        brief += "\n" + redesign_brief(spec, hardenable(measured or bundle))
        # v2.2: how the agents actually beat the measured version, from their
        # trajectories (files read, greps, their own notes), so each interlock is
        # routed around the real method rather than a guessed one.
        from .trajectory_digest import for_bundle
        solved = for_bundle(measured or bundle)
        if solved:
            brief += "\n\n" + solved
        # The independent reviewer's difficulty advisories are advisory for
        # admission but exactly the input a hardening redesign should use.
        from .review import review_advisories
        advisories = review_advisories(measured or bundle)
        if advisories:
            brief += ("\n\nTHE INDEPENDENT REVIEWER'S DIFFICULTY ADVISORIES -- where it judged "
                      "this task easier or less substantive than claimed; address these first:\n"
                      + "\n".join(f"  - {text[:500]}" for text in advisories[:8]))
    if kind != "repair":
        brief += _step_target_text(measured or bundle)
        brief += _signal_text(measured or bundle)
    maximum = read_ledger(lineage_root(bundle)).get("maximum_pass_at_1")
    if maximum is not None:
        brief += (f"\nBOUND LINEAGE GOAL: stop only when BOTH exact high-effort models "
                  f"have official AND conservative capability-adjusted pass@1 <= {maximum}. "
                  "Meeting the general <0.5 threshold is insufficient for this lineage. "
                  "Keep every public rule and honest successful tool baseline; do not "
                  "manufacture contract errors or source defects to reach this goal.")
    source = spec["source"]
    from . import checkpoint
    state = checkpoint.read(bundle)
    continuation = {}
    if state.get("stage") == "authoring":
        state = checkpoint.resumable(bundle)
        session = state["authoring_session"]
        continuation = {"resume_session": session, "max_steps": session["remaining_steps"]}
    else:
        continuation = {"initial_spec": staged}
    revised = agent_designer.design(
        row, extract.extract(source["session_id"], source["seed_index"]), bundle,
        feedback=[brief, *(findings or [])], revision=True, **continuation)
    for field in ("source", "category"):
        if field in spec:
            revised[field] = spec[field]
    return revised


#: A check's prose -- why it exists and why it weighs what it does -- is not what
#: the screen measured. A revision that adds fixture files rightly re-describes
#: the corpus a `fixture_intact` guard protects; that edit changed a-055's
#: guard's `weight_basis` only and was refused twice as "changed an untargeted
#: check", ending the lineage on a false finding (2026-09-28).
#: Words that mark a sentence as deciding scope, an exclusion or an edge case.
#: Lexical on purpose: it lists candidates for a human to read, it decides nothing.
_SCOPE_WORDS = re.compile(
    r"\b(unless|except|excluding|excluded|exclude|only|before|after|until|no longer|"
    r"does not|do not|is not|are not|never|counts?|treated as|regardless|whether)\b", re.I)
_SENTENCE_SPLIT = re.compile(r"(?<=[.!?])\s+|\n+")


def _instruction_texts(spec: dict) -> dict[str, str]:
    texts: dict[str, str] = {}
    if isinstance(spec.get("instruction"), str):
        texts["step 1"] = spec["instruction"]
    for i, step in enumerate(spec.get("steps") or [], 1):
        if isinstance(step, dict) and isinstance(step.get("instruction"), str):
            texts[str(step.get("name") or f"step {i}")] = step["instruction"]
    second = spec.get("second_step")
    if isinstance(second, dict) and isinstance(second.get("instruction"), str):
        texts["step 2"] = second["instruction"]
    return texts


def _squash(text: str) -> str:
    return " ".join(text.split()).lower()


_WORD = re.compile(r"[a-z0-9`_]+")

#: A removed sentence sharing at least this share of its words with some
#: sentence of the revised instruction was reworded, not dropped.
REWORDED_OVERLAP = 0.6


def _tokens(sentence: str) -> set[str]:
    return set(_WORD.findall(sentence.lower())) - {"the", "a", "an", "of", "to", "and", "or", "in", "is", "it"}


def removed_scope_sentences(before: dict, after: dict) -> list[str]:
    """Sentences a revision dropped from an instruction that decided a field's
    scope, an exclusion or an edge case, with no counterpart in the revision.
    Reported for review, never blocking.

    Measured 2026-09-28 (peer session, 10 hardened lineages): the only two
    pass@1 drops came from deleted scope sentences -- a-055 lost "ours to
    edit", a-047 lost the exclusion for designs exported before a moment -- and
    the qualify review reversed both. The designer cannot tell a leak from a
    scope rule reliably, so every dropped sentence with a backticked field or a
    scope word is listed for a human before the revision is screened.

    A verbatim diff drowned the signal on a heavy rewrite (a-061 hardened/v2:
    66 lines, one of them real), so a sentence that shares at least
    `REWORDED_OVERLAP` of its words with some sentence of the revision counts as
    reworded and is only counted, never listed. Whether a reworded rule still
    holds is a semantic question for the reviewer, not this function.
    """
    return scope_sentence_diff(before, after)["removed"]


def scope_sentence_diff(before: dict, after: dict) -> dict:
    """{"removed": [...], "reworded": n}: see `removed_scope_sentences`."""
    after_sentences = [s.strip() for text in _instruction_texts(after).values()
                       for s in _SENTENCE_SPLIT.split(text) if s.strip()]
    after_text = " ".join(_squash(s) for s in after_sentences)
    after_tokens = [_tokens(s) for s in after_sentences]
    removed, reworded = [], 0
    for step, text in _instruction_texts(before).items():
        for sentence in _SENTENCE_SPLIT.split(text):
            s = sentence.strip()
            if len(s) < 25 or _squash(s) in after_text:
                continue
            if not ("`" in s or _SCOPE_WORDS.search(s)):
                continue
            mine = _tokens(s)
            if mine and any(len(mine & other) / len(mine) >= REWORDED_OVERLAP for other in after_tokens):
                reworded += 1
                continue
            removed.append(f"{step}: {s[:240]}")
    return {"removed": removed, "reworded": reworded}


#: The revision's removed scope sentences, written beside the draft for the
#: reviewer and the compare step.
INSTRUCTION_DIFF = "verification/hardening-instruction-diff.json"


_CHECK_PROSE = ("basis", "weight_basis")


def _graded(check: dict) -> dict:
    return {k: v for k, v in check.items() if k not in _CHECK_PROSE}


def revision_problems(before: dict, after: dict, targets: list[dict]) -> list[str]:
    """Keep measured control checks fixed while re-aiming easy objectives."""
    errors = []
    old = {c["id"]: c for c in before.get("checks", [])}
    new = {c["id"]: c for c in after.get("checks", [])}
    allowed = {c["id"] for c in targets}
    if not set(old) <= set(new):
        errors.append(f"revision removes measured checks {sorted(set(old) - set(new))}; "
                      "removing work raises the mean and measures less")
    for cid, check in new.items():
        if cid in old and cid not in allowed and _graded(check) != _graded(old[cid]):
            # Name what changed and print the original, so a REPAIR can put it
            # back verbatim: three lineages ended on a repeat of the bare
            # message after the designer regenerated a fixture guard (a-032,
            # a-097, a-034; 2026-09-29).
            before, after = _graded(old[cid]), _graded(check)
            fields = sorted(k for k in set(before) | set(after) if before.get(k) != after.get(k))
            errors.append(f"{cid}: revision changed an untargeted check (fields: {', '.join(fields)}) "
                          f"-- restore it exactly as: {json.dumps(old[cid], ensure_ascii=False, sort_keys=True)}")
        if check.get("requires", []) != old.get(cid, {}).get("requires", []):
            errors.append(f"{cid}: changing dependency chains cannot supply difficulty")
        if (cid in allowed and cid in old and type(check.get("weight")) in (int, float)
                and type(old[cid].get("weight")) in (int, float) and check["weight"] < old[cid]["weight"]):
            errors.append(f"{cid}: reducing a targeted check's weight cannot supply difficulty")
    if [s.get("name") for s in before.get("steps", [])] != [s.get("name") for s in after.get("steps", [])]:
        errors.append("revision changed the step inventory")
    return errors


def level(bundle: Path, ledger: dict) -> str:
    """Faithfulness from fixture and traps alone, for comparing a revision.

    Calibration evidence is deliberately left out on both sides: the revision
    cannot have been calibrated yet, so an F1 original would always read as a
    drop. The revision's own measured level is assigned at delivery.
    """
    from .ledger import levels
    return levels.assign(bundle, ledger)["level"]


def diff_checks(before: dict, after: dict) -> dict:
    """What the revision actually did, so a human can review it in one screen."""
    old_by_id = {c["id"]: c for c in before.get("checks", [])}
    new_by_id = {c["id"]: c for c in after.get("checks", [])}
    changed = [cid for cid in old_by_id.keys() & new_by_id.keys()
               if json.dumps(old_by_id[cid], sort_keys=True)
               != json.dumps(new_by_id[cid], sort_keys=True)]
    return {"added": sorted(new_by_id.keys() - old_by_id.keys()),
            "removed": sorted(old_by_id.keys() - new_by_id.keys()),
            "changed": sorted(changed),
            "unchanged": sorted((old_by_id.keys() & new_by_id.keys())
                                - set(changed))}


class DesignerUnavailable(RuntimeError):
    """The designer returned no revision (transport, provider, deadline).

    Nothing was designed, so no hardening attempt was spent. The invocation
    stops rather than retrying: infrastructure loss is re-run by the operator.
    """


def attempt(original: Path, target: Path, targets: list[dict], findings: list[str],
            requested: list[str] | None = None, *, number: int = 1,
            of: int = policy.MAX_HARDENING_ATTEMPTS, kind: str = "harden",
            left: int = 0, tighten: bool = False, on_proposed=None) -> list[str]:
    """One revision of `target`, then every free validity check. Returns findings.

    Validity only. Whether the revision is HARDER is measured afterwards by the
    round's calibration screen. Raises `DesignerUnavailable` when the designer
    returned nothing (no attempt spent); `SeedRejected` and `AuthoringStalled`
    pass through for the caller to record.
    """
    from .artifacts import atomic_json
    from .author import build as build_stage
    from .author import probes as probe_stage
    from .author.contracts import strict_json
    from .author.validate import validate
    from .repair import design_inputs, rebuild_ledger
    from .run import run_bundle
    from .verify_shipped import verify as verify_shipped

    from .author.outcomes import AuthoringStalled, SeedRejected
    before, before_ledger, row = design_inputs(original)
    try:
        revised = propose(target, targets, findings, requested, number=number, of=of,
                          kind=kind, measured=original, left=left, tighten=tighten)
    except AuthoringStalled as exc:
        # The stalled session's draft is the work this attempt did: keep it as
        # the draft the next REPAIR continues from, instead of the pre-revision
        # spec -- the new traps are in it, unfinished or not.
        stalled = target / str(exc.report.get("session") or "") / "draft.json"
        if exc.report.get("session") and stalled.is_file():
            try:
                atomic_json(target / HARDENING_DRAFT, strict_json(stalled.read_text()))
            except ValueError:
                pass  # an unreadable draft is no draft; the stall is still raised
        raise
    except SeedRejected:
        raise
    except Exception as exc:
        raise DesignerUnavailable(f"{type(exc).__name__}: {exc}") from exc
    # A revision now exists: the attempt is spent from here on, whatever
    # happens to the checks below -- including an interruption.
    atomic_json(target / HARDENING_DRAFT, revised)
    if on_proposed is not None:
        on_proposed()
    # v2: only required findings block. The designer's check_draft already shows
    # advisories as advisories; re-raising them here spent a-049's first attempt
    # on 323 lexical co-occurrence findings and fed them back as "repairs"
    # (2026-10-02). Advisories are kept beside the revision for the screen report.
    from . import advisory
    blocking, advised = advisory.split(validate(revised, target)
                                       + revision_problems(before, revised, targets))
    if advised:
        atomic_json(target / "verification" / "advisories.json",
                    {"stage": "hardening-validate", "advisories": advised})
        print(f"  {len(advised)} advisory finding(s) recorded (not blocking)")
    if blocking:
        return blocking
    diff = scope_sentence_diff(before, revised)
    if diff["removed"] or diff["reworded"]:
        # Reported, never a finding: a human decides whether a removed sentence
        # was a leak or the field's meaning (a-055, a-047). Reworded sentences
        # are counted, not listed: whether a reworded rule still holds is the
        # reviewer's question.
        from .artifacts import atomic_json
        print(f"  REVIEW BEFORE SCREENING: {len(diff['removed'])} scope sentence(s) removed with no "
              f"counterpart, {diff['reworded']} reworded:")
        for line in diff["removed"][:12]:
            print(f"    - {line[:200]}")
        atomic_json(target / INSTRUCTION_DIFF, {"removed_scope_sentences": diff["removed"],
                                                "reworded_scope_sentences": diff["reworded"]})
    build_stage.build(revised, target)
    traps = strict_json((target / "authoring/traps.json").read_text())
    traps["usable_corrections"] = row["classification"]["usable_moments"]
    atomic_json(target / "authoring/traps.json", traps)
    ledger = rebuild_ledger(target, before_ledger)
    was, now = level(original, before_ledger), level(target, ledger)
    print(f"  faithfulness: {was} -> {now}, fidelity "
          f"{before_ledger.get('faithfulness_by_bytes')} -> {ledger.get('faithfulness_by_bytes')}")
    if LEVEL_RANK[now] < LEVEL_RANK[was]:
        return [f"faithfulness level fell from {was} to {now}; traps must come from the "
                "trace and the recovered documents, not replace them"]
    # The budget is the ORIGINAL task's: a second attempt may not spend what the
    # first attempt already spent, and nothing is measured against the copy.
    budget = faithfulness_budget(original, before_ledger)
    old_traps = strict_json((original / "authoring/traps.json").read_text()).get("traps", [])
    new_traps = traps.get("traps", [])
    added = faithfulness_budget(target, ledger)["scenario_bytes_used"] - budget["scenario_bytes_used"]
    known = {t.get("id") for t in old_traps}
    for t in new_traps:
        if t.get("id") not in known:
            print(f"  + trap {t.get('id')} [{t.get('type')}, {t.get('provenance')}] "
                  + (t.get("derived_from") or f"grounded in {t.get('grounded_in')}"))
    blocking, advised = advisory.split(budget_problems(budget, old_traps, new_traps, max(0, added))
                                       + routing_problems(old_traps, new_traps, revised.get("checks", [])))
    if advised:
        print(f"  {len(advised)} trap-bookkeeping advisory finding(s) (not blocking)")
    if blocking:
        return blocking
    probes = probe_stage.run(target, target / "verification" / "probe-work",
                             forged_applicable=revised.get("forged_applicable", False),
                             forged_reason=revised.get("forged_reason", ""))
    atomic_json(target / "verification" / "probes.json", probes)
    gates, grader = run_bundle(target, Path.cwd()), verify_shipped(target)
    print(f"  gates: {gates['verdict']}   shipped grader: {'ok' if grader['ok'] else 'FAILED'}")
    return _gate_findings(gates) \
        + ([] if grader["ok"] else ["the reference no longer scores 1.0; that is a defect, not difficulty"])


def _gate_findings(gates: dict) -> list[str]:
    """What a REPAIR needs to fix: each failing gate's blockers, or the error of a
    gate that could not verify. "gate chain is blocked" alone gave a-053
    hardened/v2's designer nothing to fix (2026-09-28). The bare verdict is kept
    only when no gate says why: listing it beside the blockers made one blocker
    count as two findings, and a-104's repair -- which cleared both of its
    earlier findings and hit one new blocker -- was stopped as "did not shrink"."""
    if gates["verdict"] == "green":
        return []
    why = []
    for r in gates.get("results") or []:
        if not isinstance(r, dict) or r.get("status") in ("pass", "skipped"):
            continue
        messages = [b.get("message") for b in r.get("blockers") or []
                    if isinstance(b, dict) and b.get("message")]
        if not messages and r.get("error"):
            messages = [f"could not verify: {r['error']}"]
        why += [f"{r.get('gate')}: {m}"[:600] for m in messages]
    return why or [f"gate chain is {gates['verdict']}"]


def acceptance(before: dict, after: dict, gates_green: bool,
               grader_ok: bool, suspect: list[str]) -> dict:
    """Accept a calibrated revision that is harder on the same cohorts, validly.

    Harder means official and capability-adjusted pass@1 fell on every model
    not already at zero. Contract failures cannot supply the improvement. An all-fail
    revision is admissible (POLICY.md): the burden sits on `suspect`, which
    carries every attribution problem, so a zero that is not the model's blocks.
    This is a candidate comparison, never release authorization.
    """
    invalid = list(suspect)
    if not gates_green:
        invalid.append("the gate chain no longer passes")
    if not grader_ok:
        invalid.append("the reference no longer scores 1.0; this is a defect, not difficulty")
    for label, report in (("baseline", before), ("revision", after)):
        if report.get("ok") is not True:
            invalid.append(f"{label} lacks verified current evidence: {report.get('errors', [])}")
    reasons = list(invalid)
    old, new = before.get("by_model", {}), after.get("by_model", {})
    if set(old) != set(new) or len(new) < 2:
        reasons.append("comparison needs the same two or more named model cohorts")
    rates, capability_rates = {}, {}
    for model, measured in new.items():
        previous = old.get(model, {})
        if any(previous.get(k) != measured.get(k) for k in ("protocol", "effort", "limits")):
            reasons.append(f"{model}: protocol, effort or budgets changed")
        if set(previous.get("steps", {})) != set(measured.get("steps", {})):
            reasons.append(f"{model}: step inventory changed")
        for step, current in measured.get("steps", {}).items():
            if not set(previous.get("steps", {}).get(step, {}).get("checks", {})) <= set(current["checks"]):
                reasons.append(f"{model}/{step}: removed checks cannot demonstrate improvement")
        if (measured.get("episodes_valid") or 0) < policy.SCREEN_EPISODES_PER_MODEL:
            reasons.append(f"{model}: {measured.get('episodes_valid')} valid episodes; a "
                           f"hardening round is compared on a screen of "
                           f"{policy.SCREEN_EPISODES_PER_MODEL} after voids")
        p0, p1 = previous.get("pass_at_1"), measured.get("pass_at_1")
        rates[model] = {"before": p0, "after": p1}
        if p0 is None or p1 is None:
            reasons.append(f"{model}: pass@1 unmeasured")
        elif p1 >= p0 and p0 > 0:
            reasons.append(f"{model}: pass@1 did not fall ({p0:.2f} -> {p1:.2f}); models are "
                           "never pooled, and a lower mean reward alone is not a harder task")
        c0 = (previous.get("capability_difficulty") or {}).get("capability_adjusted_pass_at_1")
        c1 = (measured.get("capability_difficulty") or {}).get("capability_adjusted_pass_at_1")
        capability_rates[model] = {"before": c0, "after": c1}
        if c0 is None or c1 is None:
            reasons.append(f"{model}: capability-adjusted pass@1 unmeasured")
        elif c1 >= c0 and c0 > 0:
            reasons.append(f"{model}: capability-adjusted pass@1 did not fall ({c0:.2f} -> {c1:.2f}); "
                           "contract failures cannot demonstrate capability hardening")
    harder = bool(rates) and all(r["after"] is not None and r["before"] is not None
                                 and (r["after"] < r["before"] or r["before"] == 0)
                                 for compared in (rates, capability_rates) for r in compared.values())
    worst = max((r["after"] for r in rates.values() if r["after"] is not None), default=None)
    disposition = ("invalid" if invalid else "not_harder" if not harder else
                   "unmeasured" if worst is None else
                   "hard" if worst <= policy.SPEC_HARD_MAX else
                   "meets_difficulty" if worst <= policy.SPEC_GENERAL_DIFFICULTY_MAX else
                   "harder_but_easy")
    return {"accept": not reasons, "valid": not invalid, "disposition": disposition,
            "pass_at_1": rates, "capability_pass_at_1": capability_rates,
            "reasons": reasons, "harder": harder,
            "release_ready": False}


def requested_traps(ideas: list[str], path: str | None) -> list[str]:
    """Operator trap ideas from --trap and --traps, as brief lines."""
    out = [i.strip() for i in ideas if i and i.strip()]
    if path:
        for item in json.loads(Path(path).read_text()):
            if isinstance(item, str):
                out.append(item.strip())
            elif isinstance(item, dict) and str(item.get("idea", "")).strip():
                grounding = str(item.get("grounding", "")).strip()
                out.append(item["idea"].strip() + (f" (grounding: {grounding})" if grounding else ""))
            else:
                raise ValueError(f"{path}: each trap is a string or {{'idea': ...}}")
    return out


def main(argv: list[str] | None = None) -> int:
    import argparse
    ap = argparse.ArgumentParser(
        description="Raise a chosen task's difficulty, by hand, with evidence")
    ap.add_argument("bundle", nargs="?", help="the bundle to harden")
    ap.add_argument("--candidates", action="store_true",
                    help="rank built tasks by how much is hardenable")
    ap.add_argument("--root", default=str(ROOT / "envs"),
                    help="where to look for bundles (with --candidates)")
    ap.add_argument("--compare", help="compare this measured revision to its original bundle")
    ap.add_argument("--apply", action="store_true",
                    help="write the hardened version; default reports only")
    ap.add_argument("--trap", action="append", default=[], metavar="IDEA",
                    help="a trap you want added (repeatable); held to every legitimacy "
                         "and faithfulness rule, left out if the source cannot support it")
    ap.add_argument("--traps", metavar="FILE",
                    help="JSON list of trap ideas: strings, or objects with 'idea' "
                         "and optional 'grounding'")
    ap.add_argument("--no-screen", action="store_true",
                    help="build the revision only; skip the round's 5 x 2 calibration "
                         "screen (run `arena screen <revision>` later)")
    ap.add_argument("--max-pass-at-1", type=float,
                    help="optional stricter inclusive official/capability maximum on both models; "
                         "bind before the first attempt and retain across resumes")
    ns = ap.parse_args(argv)
    if ns.max_pass_at_1 is not None:
        import math
        if not math.isfinite(ns.max_pass_at_1) or not 0 <= ns.max_pass_at_1 < policy.CALIBRATION_TARGET_PASS_AT_1:
            ap.error("--max-pass-at-1 must be finite, nonnegative and stricter than the general target")

    if ns.candidates:
        rows = candidates(Path(ns.root))
        if not rows:
            print(f"no bundles under {ns.root}")
            return 2
        print(f"{'bundle':44s} {'target wt':>9s} {'free wt':>8s} {'floor':>6s} {'in band':>8s} "
              f"{'hard':>5s}   means")
        for r in rows:
            if not r["ok"]:
                print(f"{r['bundle']:44s} {'--':>8s}   {r['errors'][0][:60]}")
                continue
            print(f"{r['bundle']:44s} {r['target_weight']:9} {r['free_weight']:8} {r['floor_checks']:6} "
                  f"{r['in_band']:8} {r['already_hard']:5}   "
                  + ", ".join(f"{m:.2f}" for m in r["means"] if m is not None))
        print("\n'Target wt' includes verified objectives easy on all binding models; "
              "'free wt' is score currently sitting in checks every attempt "
              "passes.\nPick from the top and run:\n  ./arena harden <bundle>")
        return 0

    if not ns.bundle:
        ap.error("give a bundle, or --candidates to see what is available")
    bundle = Path(ns.bundle)
    if not (bundle / "task.toml").is_file():
        print(f"{bundle} is not a built bundle")
        return 2

    report = hardenable(bundle)
    if ns.compare:
        from .artifacts import atomic_json
        from .attribution import problems as attribution_problems
        from .run import run_bundle
        from .verify_shipped import verify
        suspect = list(report.get("unreachable", []))
        for model, measured in report.get("reports", {}).items():
            suspect += [f"{model}: {p}" for p in attribution_problems(
                bundle, measured, policy.SCREEN_EPISODES_PER_MODEL)]
        result = acceptance(hardenable(Path(ns.compare)), report,
                            run_bundle(bundle, Path.cwd())["verdict"] == "green",
                            verify(bundle)["ok"], suspect)
        atomic_json(bundle / "verification/hardening-comparison.json", result)
        print(json.dumps(result, indent=2))
        return 0 if result["accept"] else 1

    print(f"=== {bundle.name}")
    if not report["ok"]:
        for e in report["errors"]:
            print(f"  REFUSED: {e}")
        return 1
    print(f"  calibrated against: {', '.join(report['models'])}")
    print("  pass@1: " + ", ".join(f"{m} {r['pass_at_1']:.2f}" for m, r in report["by_model"].items()
                                   if r["pass_at_1"] is not None))
    print(f"\n  free points -- {len(report['floor'])} check(s) every attempt passes, "
          f"{report['free_weight']}% of the score:")
    for c in report["floor"]:
        print(f"    {c['id']:32s} weight {c['weight']:3}  pass {c['rate']:.0%}")
    binding_targets = [target for target in hardening_targets(report) if target.get("binding_models")]
    if binding_targets:
        print(f"\n  additional binding-model targets -- {len(binding_targets)} check(s):")
        for target in binding_targets:
            print(f"    {target['step']}/{target['id']}: weight {target['weight']}, "
                  f"pass {target['rate']:.0%} on {', '.join(target['binding_models'])}")
    print(f"\n  leave alone: {len(report['in_band'])} discriminating, "
          f"{len(report['already_hard'])} already hard")
    if report["unreachable"]:
        print(f"  unreachable (fix the `requires` chain first): {', '.join(report['unreachable'])}")
        return 1
    ledger_path = bundle / "provenance/ledger.json"
    if ledger_path.is_file():
        print("\n  faithfulness budget for new traps:")
        print(_budget_text(faithfulness_budget(bundle, json.loads(ledger_path.read_text()))))
    try:
        lineage = read_ledger(lineage_root(bundle))
    except RuntimeError as exc:
        print(f"  REFUSED: {exc}")
        return 1
    print(f"\n  hardening attempts left: {attempts_left(lineage)} of "
          f"{policy.MAX_HARDENING_ATTEMPTS}; lineage {lineage.get('status', 'open')}"
          + (f" -- {TERMINAL[lineage['status']]}" if lineage.get("status") in TERMINAL else ""))
    if not ns.apply:
        print("\n  (report only -- pass --apply to build a harder version)")
        return 0

    requested = requested_traps(ns.trap, ns.traps)
    try:
        options = {"maximum_pass_at_1": ns.max_pass_at_1} if ns.max_pass_at_1 is not None else {}
        return run_lineage(bundle, report, requested, screen=not ns.no_screen, **options)
    except RuntimeError as exc:
        print(f"  REFUSED: {exc}")
        return 1


# ---------------------------------------------------------------------------
# The attempt budget
# ---------------------------------------------------------------------------

#: Where a lineage's attempts are recorded: inside `<original>/hardened/`,
#: beside the revisions, so the original task is never written to.
LEDGER = "hardened/hardening.json"

#: Lineage states that end hardening for good. `open` is the only live one.
TERMINAL = {"target-met": "every step of a screened revision is passed by <= 60% of episodes on both models",
            "exhausted": "its hardening attempts are spent",
            "no-progress": "a screened revision made no progress on either model",
            "stopped": "a validity finding repeated or the finding set did not shrink",
            "source-rejected": "the designer found the source cannot support genuine hard traps"}


def lineage_root(bundle: Path) -> Path:
    """The original task a revision descends from (`<root>/hardened/vN/...`)."""
    root = Path(bundle).resolve()
    while root.parent.name == "hardened":
        root = root.parent.parent
    return root


def read_ledger(root: Path) -> dict:
    from .author.contracts import strict_json
    path = Path(root) / LEDGER
    try:
        return strict_json(path.read_text())
    except FileNotFoundError:
        return {"schema": "arena-pipeline/hardening/1", "status": "open",
                "max_attempts": policy.MAX_HARDENING_ATTEMPTS, "attempts": [], "screens": [],
                "interruptions": []}
    except (OSError, ValueError) as exc:
        raise RuntimeError("Cannot read the retained hardening ledger; no allowance was reset") from exc


def max_attempts(ledger: dict) -> int:
    """The lineage's attempt budget: the policy cap, unless the user raised it.

    User, 2026-10-02: lineages that spent all three attempts may get more ("Raise
    the cap for them"). The override lives in the ledger beside its reason
    (`raise_attempt_cap`), never in policy, so every report shows it."""
    override = ledger.get("operator_max_attempts")
    if type(override) is int and override > policy.MAX_HARDENING_ATTEMPTS:
        return override
    return policy.MAX_HARDENING_ATTEMPTS


def attempts_left(ledger: dict) -> int:
    return max(0, max_attempts(ledger) - len(spent_attempts(ledger)))


#: Lineage endings an operator cap raise reopens: the budget, a repeated finding
#: or a measured no-progress ended them -- none says the task cannot be hardened.
REOPENABLE = ("exhausted", "stopped", "no-progress")


def raise_attempt_cap(root: Path, maximum: int, reason: str) -> dict:
    """Record a user-approved higher attempt cap for one lineage and reopen it."""
    if type(maximum) is not int or maximum <= policy.MAX_HARDENING_ATTEMPTS or len(reason.strip()) < 20:
        raise ValueError("a raised cap must exceed the policy cap and carry the user's reason")
    with _lineage_lock(Path(root)):
        ledger = read_ledger(Path(root))
        before = ledger.get("status", "open")
        ledger["operator_max_attempts"] = max(maximum, ledger.get("operator_max_attempts") or 0)
        ledger.setdefault("overrides", []).append({"at": time.time(), "operator_max_attempts": maximum,
                                                   "status_before": before, "reason": reason.strip()})
        if before in REOPENABLE and attempts_left(ledger):
            ledger["status"] = "open"
        _save(Path(root), ledger)
        return ledger


def spent_attempts(ledger: dict) -> list[dict]:
    """Attempts that count against the budget.

    An attempt a PIPELINE DEFECT invalidated measured nothing about the task --
    the attempt-budget analogue of a void episode. 2026-10-02: a-011 lost attempt
    1 to step numbers the validator refused and a-049 to 323 advisories the
    hardening path re-raised as blockers; both defects are fixed. Such a row keeps
    its findings and gains `voided_by_pipeline_defect` ({reason, fixed_by}), set
    only by `void_attempt`; it stays in the ledger and in every report.
    """
    return [a for a in ledger.get("attempts", [])
            if not (isinstance(a, dict) and a.get("voided_by_pipeline_defect"))]


def void_attempt(root: Path, number: int, reason: str, fixed_by: str) -> dict:
    """Mark attempt `number` of a lineage as invalidated by a fixed pipeline defect.

    Only an attempt whose outcome is `invalid` (it never reached a screen) can be
    voided: a screened attempt measured the task, and re-running a scored
    measurement until it improves is exactly what the budget forbids."""
    if len(reason.strip()) < 20 or len(fixed_by.strip()) < 7:
        raise ValueError("a voided attempt needs the defect and the commit that fixed it")
    with _lineage_lock(Path(root)):
        ledger = read_ledger(Path(root))
        rows = [a for a in ledger.get("attempts", []) if a.get("attempt") == number]
        if len(rows) != 1:
            raise ValueError(f"no single attempt {number} in this lineage")
        row = rows[0]
        if row.get("outcome") != "invalid":
            raise ValueError(f"attempt {number} is {row.get('outcome')!r}; only an invalid, "
                             "unscreened attempt can be voided")
        if any(s.get("revision") == row.get("revision") for s in ledger.get("screens", [])):
            raise ValueError(f"attempt {number}'s revision was screened; it measured the task")
        row["voided_by_pipeline_defect"] = {"reason": reason.strip(), "fixed_by": fixed_by.strip(),
                                            "at": time.time()}
        if ledger.get("status") == "exhausted" and attempts_left(ledger):
            ledger["status"] = "open"
        _save(Path(root), ledger)
        return row


def _save(root: Path, ledger: dict) -> None:
    from .artifacts import atomic_json
    atomic_json(Path(root) / LEDGER, ledger)


@contextlib.contextmanager
def _lineage_lock(root: Path):
    """One hardening process per lineage: two would both spend the budget."""
    import fcntl
    path = Path(root) / "hardened" / ".lock"
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a+") as handle:
        try:
            fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            raise RuntimeError(f"another hardening run owns {root.name}") from exc
        try:
            yield
        finally:
            fcntl.flock(handle, fcntl.LOCK_UN)


def _next_revision(root: Path, source: Path) -> Path:
    """A fresh sibling under the ORIGINAL's `hardened/`, copied from `source`.

    Numbered past every revision on disk AND every one the ledger recorded: a
    recorded revision whose directory was deleted must never lend its name --
    and its "valid" row -- to a new, unscreened copy.
    """
    root = Path(root)
    taken = [int(p.name[1:]) for p in (root / "hardened").glob("v*") if p.name[1:].isdigit()]
    ledger = read_ledger(root)
    for row in ledger.get("attempts", []) + ledger.get("screens", []):
        name = Path(str(row.get("revision") or "")).name
        if name[:1] == "v" and name[1:].isdigit():
            taken.append(int(name[1:]))
    target = root / "hardened" / f"v{max(taken, default=1) + 1}"
    shutil.copytree(source, target, ignore=shutil.ignore_patterns(
        "hardened", "verification", "__pycache__", "*.pyc"))
    return target


def _rel(root: Path, path: Path) -> str:
    try:
        return Path(path).resolve().relative_to(Path(root).resolve()).as_posix() or "."
    except ValueError:
        return str(path)


def _pending_author(root: Path, source: Path, ledger: dict) -> dict | None:
    from . import checkpoint
    from .artifacts import identity
    from .author.contracts import contained
    number = len(ledger.get("attempts", [])) + 1
    pending = next((row for row in reversed(ledger.get("interruptions", []))
                    if row.get("phase") == "authoring" and row.get("attempt") == number), None)
    if pending is None:
        return None
    if (pending.get("from") != _rel(root, source)
            or pending.get("source_artifact_sha256") != identity(source)):
        raise ValueError("Interrupted hardening source changed; inspect the retained draft instead of restarting")
    target = contained(root, pending["revision"])
    if target.parent != (root / "hardened").resolve() or not target.is_dir():
        raise ValueError("Interrupted hardening revision is missing or outside its lineage")
    state = checkpoint.resumable(target)
    if not state or state.get("stage") != "authoring":
        raise ValueError("Interrupted hardening has no complete author boundary; retain it for inspection")
    return {**pending, "target": target}


def _pass_at_1(bundle: Path) -> dict:
    """Capability-adjusted pass@1 for progress, not the official reported rate."""
    report = hardenable(bundle)
    return {m: (r.get("capability_difficulty") or {}).get("capability_adjusted_pass_at_1")
            for m, r in report.get("by_model", {}).items()} if report.get("ok") else {}


def step_pass_rates(record: dict) -> dict[str, dict[str, float]] | None:
    """model -> step -> share of valid episodes that fully passed that step.

    Read from the screen's own campaign reports (its record keeps only per-check
    marginals, and a step can fail on a different check in every episode). None
    when a cited campaign cannot be read or a model has fewer valid episodes than
    the screen floor -- an unreadable rate never meets a target.
    """
    out = {}
    index_topups = (record.get("index") or {}).get("topups") or {}
    for model, result in (record.get("per_model") or {}).items():
        if not isinstance(result, dict) or not result.get("campaign"):
            return None
        cited = [result["campaign"], *(result.get("topups") or []), *(index_topups.get(model) or [])]
        trials = []
        for campaign in dict.fromkeys(c for c in cited if isinstance(c, str)):
            try:
                report = json.loads((Path(campaign) / "report.json").read_text())
            except (OSError, ValueError):
                return None
            trials += [t for t in report.get("trials") or [] if isinstance(t, dict) and t.get("valid") is True]
        if len(trials) < policy.SCREEN_EPISODES_PER_MODEL:
            return None
        names = sorted({s.get("name") for t in trials for s in t.get("steps") or [] if s.get("name")})
        out[model] = {name: round(sum(1 for t in trials if any(
            s.get("name") == name and s.get("valid") is True and isinstance(s.get("reward"), (int, float))
            and s["reward"] >= 1.0 - 1e-9 for s in t.get("steps") or [])) / len(trials), 3) for name in names}
    return out or None


def steps_too_easy(record: dict) -> dict[str, list[str]] | None:
    """model -> steps above policy.STEP_PASS_RATE_MAX; None when unreadable."""
    from .benchmark.harbor import resolve_model
    rates = step_pass_rates(record)
    try:
        required = set(map(resolve_model, policy.resolve_calibration_models()))
        if rates is None or {resolve_model(model) for model in rates} != required or len(rates) != len(required):
            return None
    except (TypeError, ValueError):
        return None
    return {model: [step for step, rate in sorted(steps.items()) if rate > policy.STEP_PASS_RATE_MAX]
            for model, steps in rates.items()}


def _signal_verdict(record: dict | None) -> dict | None:
    """The training-signal shape of a screen, re-derived from its campaign reports.

    Like `step_pass_rates`, never read from the receipt's own verdict: a receipt
    edited by hand proves nothing. None when the campaigns cannot be read -- an
    unreadable signal never meets a target.
    """
    from . import training_signal as signal
    if not isinstance(record, dict) or not record:
        return None
    try:
        return signal.from_screen_record(record)
    except Exception:                                # noqa: BLE001 -- unreadable is not met
        return None


def _target_met(record: dict, maximum_pass_at_1: float | None = None) -> bool:
    # User, 2026-10-02: every step at or under STEP_PASS_RATE_MAX on both models.
    easy = steps_too_easy(record)
    if easy is None or any(easy.values()):
        return False
    # User, 2026-10-13 (Arena 261013, spec 10_12): the band AND the gradient.
    # pass@1 at or below policy.EXTREME_PASS_AT_1_MAX on both models and every
    # step, with reward spread on every model and step, no model sorting and no
    # constant premise (`pipeline.training_signal`). A task pushed to 0/10 through one
    # premise nobody resolves is CONSTANT_PREMISE, not target-met.
    verdict = _signal_verdict(record)
    if not isinstance(verdict, dict) or verdict.get("target_met") is not True:
        return False
    if maximum_pass_at_1 is None:
        return record.get("measurement_complete") is True and record.get("shippable") is True
    import math
    models = policy.resolve_calibration_models()
    measured = record.get("per_model") or {}
    if (record.get("measurement_complete") is not True or record.get("shippable") is not True
            or not isinstance(measured, dict) or set(measured) != set(models)):
        return False
    for model in models:
        result = measured[model]
        if not isinstance(result, dict) or not isinstance(result.get("capability_difficulty"), dict):
            return False
        diagnostic = result["capability_difficulty"]
        if result.get("effort") != policy.SPEC_CALIBRATION_EFFORT:
            return False
        for count in (result.get("episodes_valid"), diagnostic.get("episodes_valid")):
            if type(count) is not int or count < policy.SCREEN_EPISODES_PER_MODEL:
                return False
        for rate in (result.get("pass_at_1"), diagnostic.get("capability_adjusted_pass_at_1")):
            if type(rate) not in (int, float) or not math.isfinite(rate) or not 0 <= rate <= maximum_pass_at_1:
                return False
    return True


def _bind_goal(ledger: dict, requested: float | None) -> float | None:
    import math
    saved = ledger.get("maximum_pass_at_1")
    for value in (saved, requested):
        if value is not None and (type(value) not in (int, float) or not math.isfinite(value)
                                  or not 0 <= value < policy.CALIBRATION_TARGET_PASS_AT_1):
            raise RuntimeError("Invalid retained or requested hardening goal; no allowance was reset")
    if saved is not None:
        if requested is not None and requested != saved:
            raise RuntimeError("Hardening goal differs from the retained lineage; do not reset or retarget it")
        return saved
    if requested is not None:
        if ledger.get("attempts") or ledger.get("screens"):
            raise RuntimeError("A stricter goal must be bound before the first hardening attempt")
        ledger["maximum_pass_at_1"] = requested
    return requested


def _signal_improved(before: dict | None, after: dict | None) -> bool | None:
    from . import training_signal as signal
    return signal.improved(before, after)


def _made_progress(before: dict, after: dict) -> bool | None:
    """pass@1 fell on at least one model measured on both sides.

    "No progress" ends a lineage for good, so False needs proof: every model is
    measured on both sides and at least one of them could have fallen (a parent
    already at 0 cannot). Anything less is None -- not comparable -- because an
    unmeasured parent, or a model compared only where it could not move, is no
    evidence the revision made no progress.
    """
    models = {m for side in (before, after) for m, rate in side.items() if rate is not None}
    both = [m for m in models if before.get(m) is not None and after.get(m) is not None]
    if any(after[m] < before[m] for m in both):
        return True
    if not both or len(both) < len(models) or not any(before[m] > 0 for m in both):
        return None
    return False


def _resume_point(root: Path, ledger: dict) -> Path | None:
    """The lineage's latest valid revision, when hardening is asked of the original.

    None when no attempt produced a valid revision (the original is then the
    right starting point). Raises when the latest valid revision has no clean
    screen: continuing from an older one, or from the original, would discard
    it, so it has to be measured first.
    """
    from . import screen
    latest = next((a for a in reversed(ledger.get("attempts", []))
                   if a.get("outcome") == "valid" and (Path(root) / a.get("revision", "")).is_dir()
                   and a.get("revision") not in (None, ".")), None)
    if latest is None:
        return None
    revision = Path(root) / latest["revision"]
    record = screen.current(revision)
    if record is None or not record.get("measurement_complete"):
        raise RuntimeError(
            f"{latest['revision']} is this lineage's latest valid revision and has no clean "
            f"screen; measure it before hardening further:\n"
            f"    {screen.rescreen_command(revision, record)}\n    ./arena harden {revision} --apply")
    return revision


def _judge_revision(root: Path, revision: Path, ledger: dict) -> str | None:
    """Apply the stop rules to a revision the operator resumes from.

    Resuming with `arena harden <vN> --apply` used to spend the next attempt
    without ever reading vN's screen: a revision that had already met the target
    was redesigned, and one that made no progress was tightened anyway. Returns
    a terminal status, "open", or None when vN has no screen to judge (its
    measurement then comes from its calibration index, as for an original).
    Raises when vN's screen exists but did not measure cleanly.
    """
    from . import screen
    record = screen.current(revision)
    if record is None:
        return None
    if not record.get("measurement_complete"):
        raise RuntimeError(f"{revision.name}'s screen did not measure cleanly "
                           f"({'; '.join(record.get('shippable_problems', [])[:2])}); "
                           f"re-screen it (`{screen.rescreen_command(revision, record)}`) "
                           "before hardening further")
    rel = _rel(root, revision)
    parent = next((a.get("from") for a in reversed(ledger.get("attempts", []))
                   if a.get("revision") == rel), None)
    progress = (_made_progress(_pass_at_1(root if parent in (None, ".") else root / parent),
                               _pass_at_1(revision)) if parent is not None else True)
    verdict = _signal_verdict(record)
    if progress is False:
        # Arena 261013: clearing a spread flag (FLAT, SORTING, a constant premise)
        # without raising another is progress toward the target, even at an
        # unchanged pass@1.
        before = screen.current(root if parent in (None, ".") else root / parent)
        if _signal_improved(_signal_verdict(before), verdict):
            progress = True
    if not any(sc.get("revision") == rel for sc in ledger.get("screens", [])):
        ledger["screens"].append({"revision": rel, "meets_target": bool(record.get("meets_target")),
                                  "signal_shape": (verdict or {}).get("shape"),
                                  "signal_target_met": bool((verdict or {}).get("target_met")),
                                  "step_pass_rates": step_pass_rates(record),
                                  "meets_capability_target": bool(record.get("meets_capability_target")),
                                  "shippable": bool(record.get("shippable")), "progress": progress,
                                  "outlook": (record.get("outlook") or {}).get("verdict")})
    if _target_met(record, ledger.get("maximum_pass_at_1")):
        return "target-met"
    if progress is False:
        # A user-approved cap raise after a measured no-progress ending is the
        # instruction to keep hardening from this revision (user, 2026-10-02).
        if any(o.get("status_before") == "no-progress" for o in ledger.get("overrides", [])):
            return "open"
        return "no-progress"
    return "open"                   # progressed, or not comparable (None)


def run_lineage(bundle: Path, report: dict, requested: list[str], screen: bool = True,
                maximum_pass_at_1: float | None = None) -> int:
    """Harden `bundle` within its lineage's attempt budget. The one loop.

    Each iteration is one designer call. An attempt is recorded the moment the
    designer returns a revision -- before building or checking it -- so an
    interruption can never hand back an attempt that was spent. The loop cannot
    outlive the budget, stops on anything that says another redesign would
    repeat the last one, and never ends a lineage on a measurement that did not
    measure cleanly.
    """
    from .author.outcomes import AuthoringStalled, SeedRejected
    root = lineage_root(bundle)
    with _lineage_lock(root):
        ledger = read_ledger(root)
        if ledger.get("status", "open") != "open":
            raise RuntimeError(f"{root.name}: hardening has ended -- "
                               f"{TERMINAL.get(ledger['status'], ledger['status'])}")
        maximum = _bind_goal(ledger, maximum_pass_at_1)
        if maximum is not None:
            _save(root, ledger)
            print(f"  bound official and capability-adjusted pass@1 maximum: {maximum} on both models")
        current, targets = Path(bundle).resolve(), hardening_targets(report)
        if current == root and (resume := _resume_point(root, ledger)) is not None:
            # `arena harden <original> --apply` on a lineage that already has a
            # measured revision continues from that revision. Starting again
            # from the original threw the measured progress away and spent an
            # attempt redoing the extremely-hard redesign.
            measured = hardenable(resume)
            if not measured.get("ok"):
                raise RuntimeError(f"{_rel(root, resume)} is the lineage's latest measured "
                                   f"revision but its screen cannot be read: "
                                   f"{'; '.join(measured.get('errors', [])[:2])}")
            print(f"  continuing from {_rel(root, resume)}, the lineage's latest measured "
                  f"revision (not from the original)")
            current, targets = resume.resolve(), hardening_targets(measured)
        # A resumed revision is judged by the same rules as one screened inside
        # the loop, before any budget is spent on it.
        pending_author = _pending_author(root, current, ledger)
        verdict = _judge_revision(root, current, ledger) if current != root else None
        if verdict == "no-progress" and pending_author is not None:
            verdict = "open"
        if verdict not in (None, "open"):
            ledger["status"] = verdict
            _save(root, ledger)
            _final_words(root, current, ledger)
            return 0 if verdict == "target-met" else 1
        if not attempts_left(ledger):
            ledger["status"] = "exhausted"
            _save(root, ledger)
            raise RuntimeError(f"{root.name}: all {max_attempts(ledger)} hardening "
                               "attempts are spent")
        # TIGHTEN only when the version being revised was actually measured as
        # a revision; otherwise this is the full extremely-hard redesign.
        tighten = current != root
        target = pending_author["target"] if pending_author else _next_revision(root, current)
        fresh = pending_author is None
        kind = pending_author.get("kind", "harden") if pending_author else "harden"
        findings = pending_author.get("findings", []) if pending_author else []
        seen = set(pending_author.get("seen_findings", [])) if pending_author else set()
        print(f"\n  {attempts_left(ledger)} of {max_attempts(ledger)} hardening "
              f"attempts left for {root.name}")
        while attempts_left(ledger):
            number = len(ledger["attempts"]) + 1
            left = attempts_left(ledger) - 1
            print(f"\n  attempt {number}/{max_attempts(ledger)} "
                  f"[{'tighten' if kind == 'harden' and tighten else kind}] "
                  f"{_rel(root, current)} -> {_rel(root, target)}", flush=True)
            row = {"attempt": number, "kind": kind, "tighten": tighten and kind == "harden",
                   "from": _rel(root, current), "revision": _rel(root, target),
                   "started_at": time.time()}

            def spent(row=row):
                # Called the moment the designer returns a revision.
                ledger["attempts"].append({**row, "outcome": "in-progress"})
                _save(root, ledger)

            try:
                new = attempt(current, target, targets, findings, requested,
                              number=number, of=max_attempts(ledger),
                              kind=kind, left=left, tighten=tighten, on_proposed=spent)
            except DesignerUnavailable as exc:
                from . import checkpoint
                from .artifacts import identity
                state = checkpoint.read(target)
                retained = bool(state.get("authoring_session") or
                                list((target / "verification/design-sessions").glob("*")))
                interruption = {**row, "error": str(exc)[:500], "draft_retained": retained}
                if retained:
                    interruption.update(phase="authoring", source_artifact_sha256=identity(current),
                                        findings=findings, seen_findings=sorted(seen))
                ledger.setdefault("interruptions", []).append(interruption)
                _save(root, ledger)
                if fresh and not retained:
                    shutil.rmtree(target, ignore_errors=True)
                print(f"  INTERRUPTED (no attempt spent): {str(exc)[:200]}\n"
                      "  Re-run the same command once the designer is reachable; any author draft\n"
                      "  and its original remaining budget are retained, not rerolled.")
                return 2
            except SeedRejected as exc:
                ledger["attempts"].append({**row, "outcome": "source-rejected",
                                           "reason": str(exc.report.get("reason", ""))[:500]})
                ledger["status"] = "source-rejected"
                _save(root, ledger)
                print(f"  STOPPED: the designer rejected the source -- {exc.report.get('reason', '')[:200]}")
                return 1
            except AuthoringStalled as exc:
                new = [f"the design stalled before submitting: {exc.report.get('reason', '')}"]
            except Exception as exc:                             # noqa: BLE001
                # A revision was proposed and checking it failed: that is a finding.
                new = [f"{type(exc).__name__}: {exc}"]
            outcome_row = {**row, "outcome": "invalid" if new else "valid",
                           "findings": [f[:300] for f in new[:12]]}
            pending = next((i for i, a in enumerate(ledger["attempts"])
                            if a.get("attempt") == number and a.get("outcome") == "in-progress"), None)
            if pending is None:
                ledger["attempts"].append(outcome_row)
            else:
                ledger["attempts"][pending] = outcome_row
            _save(root, ledger)
            fresh = False

            if new:
                print(f"  {len(new)} validity finding(s):")
                for line in new[:6]:
                    print(f"    - {line[:160]}")
                repeated = seen & set(new)
                if repeated or (findings and len(new) >= len(findings)):
                    ledger["status"] = "stopped"
                    _save(root, ledger)
                    print(f"  STOPPED: {'a finding repeated' if repeated else 'the finding set did not shrink'}"
                          f". The revision is kept at {target} for review; the original is untouched.")
                    return 1
                seen |= set(new)
                findings, kind = new, "repair"
                continue

            print(f"  valid revision at {target}. The original is untouched.")
            print("  NOT yet accepted: a revision is a candidate until its own screen says otherwise.")
            if not screen:
                print("  NOT yet measured (--no-screen). Screen it, then continue hardening:")
                print(f"    ./arena screen {target}")
                print(f"    ./arena harden {target} --apply")
                return 0
            try:
                outcome = screen_round(current, target)
            except Exception as exc:                             # noqa: BLE001
                # The revision is valid and its attempt is spent; only its
                # measurement failed. Measure THAT revision -- re-running harden
                # on the original would spend another attempt on a new design.
                ledger.setdefault("interruptions", []).append(
                    {"revision": _rel(root, target), "error": f"screen: {exc}"[:500]})
                _save(root, ledger)
                from . import screen as _screen
                print(f"  SCREEN FAILED (the valid revision is kept): {str(exc)[:200]}\n"
                      f"    {_screen.rescreen_command(target, _screen.current(target))}\n"
                      f"    ./arena harden {target} --apply     # continues from it")
                return 2
            if not outcome["record"].get("measurement_complete"):
                # Voids, unattributable failures or an unresolved hack flag: the
                # screen says nothing reliable about difficulty, so it may end
                # nothing. The lineage stays open on this revision.
                ledger.setdefault("interruptions", []).append(
                    {"revision": _rel(root, target), "error": "screen did not measure cleanly: "
                     + "; ".join(outcome["record"].get("shippable_problems", [])[:3])[:450]})
                _save(root, ledger)
                print("  SCREEN DID NOT MEASURE CLEANLY -- nothing is decided from it:")
                for line in outcome["record"].get("shippable_problems", [])[:4]:
                    print(f"    - {line[:300]}")
                from .screen import rescreen_command
                print(f"    {rescreen_command(target, outcome['record'])}\n"
                      f"    ./arena harden {target} --apply     # continues from it")
                return 2
            ledger["screens"].append({"revision": _rel(root, target), **outcome["summary"],
                                      "step_pass_rates": step_pass_rates(outcome["record"])})
            if _target_met(outcome["record"], maximum):
                ledger["status"] = "target-met"
            elif outcome["progress"] is False:
                # Only a measured "no" ends the lineage; None (nothing to compare
                # against) keeps it open on the budget.
                ledger["status"] = "no-progress"
            elif not attempts_left(ledger):
                ledger["status"] = "exhausted"
            _save(root, ledger)
            if ledger["status"] != "open":
                _final_words(root, target, ledger)
                return 0 if ledger["status"] == "target-met" else 1
            # Still too easy, measurably better, and budget left: tighten the
            # measured revision. Its own screen says which checks are still free.
            current = target
            measured = hardenable(current)
            if not measured["ok"]:
                ledger["status"] = "stopped"
                _save(root, ledger)
                print(f"  STOPPED: the revision's screen cannot be read: {measured['errors'][:2]}")
                return 1
            targets = hardening_targets(measured)
            target = _next_revision(root, current)
            fresh, kind, findings, seen, tighten = True, "harden", [], set(), True
        # Budget spent on validity repairs without a valid revision.
        ledger["status"] = "exhausted"
        _save(root, ledger)
        print(f"  STOPPED: all {policy.MAX_HARDENING_ATTEMPTS} attempts spent without a valid, "
              f"measured revision. The last is kept at {target} for review.")
        return 1


def _final_words(root: Path, revision: Path, ledger: dict) -> None:
    status = ledger["status"]
    spent = len(spent_attempts(ledger))
    voided = len(ledger.get("attempts", [])) - spent
    print(f"\n  hardening of {root.name} ended after {spent}/{policy.MAX_HARDENING_ATTEMPTS} "
          f"attempt(s)" + (f" (+{voided} voided by fixed pipeline defects)" if voided else "")
          + f": {TERMINAL[status]}")
    if status != "target-met":
        print("  It will not be redesigned again; its measurements stand as reported.")
    # The target never blocks: any revision whose screen measured cleanly may
    # take the calibration of record, met or not.
    print(f"  calibration of record (runs if the last screen measured cleanly):\n"
          f"    ./arena qualify {revision}")


def screen_round(original: Path, revision: Path) -> dict:
    """Measure a valid revision: screen it and compare it with what it revised.

    The screen is `policy.SCREEN_EPISODES_PER_MODEL` episodes on each model;
    the comparison is `acceptance` against the version it was revised from.
    `progress` is whether capability-adjusted pass@1 fell on at least one model -- a revision that
    moved neither is the signature of a redesign loop, and ends the lineage.
    """
    from . import screen
    from .artifacts import atomic_json
    from .attribution import problems as attribution_problems
    from .config import ARTIFACTS
    from .run import run_bundle
    from .verify_shipped import verify
    print(f"\n  screening the revision: {policy.SCREEN_EPISODES_PER_MODEL} episodes x "
          f"{len(policy.resolve_calibration_models())} models", flush=True)
    record = screen.run(revision, native_root=ARTIFACTS / "native",
                        label=f"hardening {revision.name}")
    report = hardenable(revision)
    suspect = list(report.get("unreachable", []))
    for model, measured in report.get("reports", {}).items():
        suspect += [f"{model}: {p}" for p in
                    attribution_problems(revision, measured, policy.SCREEN_EPISODES_PER_MODEL)]
    result = acceptance(hardenable(original), report,
                        run_bundle(revision, Path.cwd())["verdict"] == "green",
                        verify(revision)["ok"], suspect)
    atomic_json(revision / "verification/hardening-comparison.json", result)
    screen.print_table(screen.report([record]))
    progress = _made_progress({m: r.get("before") for m, r in result["capability_pass_at_1"].items()},
                              {m: r.get("after") for m, r in result["capability_pass_at_1"].items()})
    # Arena 261013: the target is a band with a gradient, so a revision that
    # clears a spread flag (FLAT, SORTING, a constant premise) without raising a
    # new one has progressed even where pass@1 did not move.
    after_signal = _signal_verdict(record)
    signal_progress = _signal_improved(_signal_verdict(screen.current(original)), after_signal)
    if progress is not True and signal_progress:
        progress = True
    print(f"  comparison: {result['disposition']}; progress on at least one model: "
          f"{ {True: 'yes', False: 'no', None: 'not comparable (the parent has no measurement)'}[progress] }"
          + ("" if result["accept"] else f" -- {'; '.join(result['reasons'][:3])}"))
    from .training_signal import lines as signal_lines
    print("  " + "\n  ".join(signal_lines(after_signal)))
    summary = {"pass_at_1": result["pass_at_1"], "meets_target": bool(record.get("meets_target")),
               "signal_shape": (after_signal or {}).get("shape"),
               "signal_target_met": bool((after_signal or {}).get("target_met")),
               "signal_progress": signal_progress,
               "capability_pass_at_1": result["capability_pass_at_1"],
               "meets_capability_target": bool(record.get("meets_capability_target")),
               "measurement_complete": bool(record.get("measurement_complete")),
               "shippable": bool(record.get("shippable")),
               "outlook": (record.get("outlook") or {}).get("verdict"),
               "disposition": result["disposition"], "progress": progress}
    return {"record": record, "comparison": result, "progress": progress, "summary": summary}


if __name__ == "__main__":
    raise SystemExit(main())
