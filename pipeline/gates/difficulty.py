"""Gates on difficulty, trap validity, and demonstrated hack-resistance.

Three things this module refuses to accept on assertion:

1. **That a trap is beatable.** The spec requires a reference solution proving
   it. So every trap names the solution step that defeats it, and the recorded
   run of that solution must score 1.0.
2. **That a trap is fair.** A trap must catch faulty reasoning, not a correct
   answer written differently -- so every trap also names an adversarial probe,
   and that probe must score *strictly less* than the reference. A trap nothing
   fails is decoration; a trap the reference fails is a broken task.
3. **That the environment resists reward hacking.** "We removed the obvious
   surfaces" is worth nothing without the probe and its output. Two probes are
   mandatory and they are the ones that matter: an agent that writes the
   expected end state without doing the work, and an agent that reads every file
   and returns what it finds. Both must fail.

`verification/probes.json` carries the recorded results. A missing file is an
ERROR -- "not yet probed" is not "probed and clean".
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from ..config import MIN_TRAPS, expected_traps
from ..author.traps import (TAXONOMY, TRACE_DERIVED_FLOOR, Trap,
                            trace_derived_share, trace_exploitation)
from ..select.priority import TIER_TRACE_FLOOR
from .base import Finding, FunctionGate, GateContext, Severity

#: Probes every bundle must record. The first five are correctness; the last two
#: are the reward-hacking floor and have no exemption.
REQUIRED_PROBES = {
    "seed_zero": "pristine fixture: every objective 0.0, every guardrail 1.0",
    "golden": "reference solution scores 1.0",
    "untidy_correct": "correct but messy work still scores 1.0",
    "plausible_wrong": "a defensible-looking wrong answer scores < 1.0",
    "destructive": "breaking a protected surface zeroes the task",
    "forged_state": "writing the expected end state without doing the work "
                    "must NOT score 1.0",
    "answer_lookup": "reading every fixture file and returning what it says "
                     "must NOT score 1.0",
}


def _probes(ctx: GateContext) -> dict:
    """The probe results the gates decide on: re-run now, offline, against the
    bundle as it stands. A stored `verification/probes.json` is checked against
    this run by `hacking.resistance`; it is never trusted in its place."""
    from ..author.probes import gate_report
    try:
        fresh, _ = gate_report(ctx.task_dir, getattr(ctx, "extras", None))
    except (OSError, ValueError, KeyError, TypeError) as exc:
        raise RuntimeError(f"the probe suite cannot run against this bundle: {exc}") from exc
    return fresh


def _load(ctx: GateContext, rel: str) -> Any:
    if rel == "verification/probes.json":
        return _probes(ctx)
    path = ctx.path(rel)
    if not path.exists():
        raise RuntimeError(f"{rel} is absent; this gate cannot report on an "
                           "unprobed bundle")
    return json.loads(path.read_text())


def _traps(ctx: GateContext) -> list[Trap]:
    raw = _load(ctx, "authoring/traps.json")
    return [Trap(**t) for t in raw.get("traps", [])]


def _trap_faithful(ctx: GateContext) -> tuple[list[Finding], dict]:
    """Traps may be invented, but the world they happen in may not be.

    A trace-derived trap cites the moment and quotes the user. An authored trap
    names the fixture surface it rests on and why a practitioner here would
    plausibly meet it. The bundle as a whole must stay majority trace-derived.
    """
    traps = _traps(ctx)
    findings: list[Finding] = []
    if not traps:
        return [Finding(Severity.WARN, "no-traps",
                        "the bundle declares no traps; the spec asks for realistic "
                        "traps that catch sloppy work", "authoring/traps.json")], {}

    # Floor, then a scaled expectation. The floor is absolute; the expectation
    # rises with what the trace can actually support, so a thin seed is not
    # pushed into inventing difficulty and a rich one is not let off lightly.
    raw_doc = json.loads(ctx.path("authoring/traps.json").read_text())
    fixture_dir = next((ctx.path("environment", n) for n in ("files", "fixtures")
                        if ctx.path("environment", n).is_dir()), None)
    surfaces = len([p for p in fixture_dir.rglob("*") if p.is_file()]) \
        if fixture_dir else 0
    objectives = sum(1 for c in json.loads(
        ctx.path("tests/checks.json").read_text())["checks"]
        if c.get("kind") == "objective") if ctx.path("tests/checks.json").exists() else 0
    # An absent correction count is UNKNOWN, not `len(traps)`. Defaulting it to
    # the trap count made the budget track its own input: adding a trap raised
    # the expectation, so the gate could never be satisfied by adding traps.
    # A trace with one real correction had seven invented for it.
    usable = raw_doc.get("usable_corrections")
    if usable is None:
        findings.append(Finding(
            Severity.WARN, "unknown-correction-count",
            "authoring/traps.json carries no usable_corrections, so the scaled "
            "trap budget is computed from surfaces and objectives alone. Set it "
            "from the classification rather than leaving it null",
            "authoring/traps.json"))
        usable = 0
    want = expected_traps(surfaces, usable, objectives)

    if len(traps) < MIN_TRAPS:
        findings.append(Finding(
            Severity.WARN, "below-trap-floor",
            f"{len(traps)} traps, floor is {MIN_TRAPS}. A task with four or fewer "
            "traps is a long instruction with a couple of hazards in it",
            "authoring/traps.json"))
    elif len(traps) < want:
        # Advisory since 2026-09-26. A size-scaled quota pushed authors to pad
        # with traps the source does not support -- or, on an F3 task with few
        # corrections, to label invented traps trace-derived to keep the 70%
        # share. Every trap now carries a linked, executed misreading
        # (`difficulty_case`), and the floor above still blocks.
        findings.append(Finding(
            Severity.WARN, "below-scaled-trap-budget",
            f"{len(traps)} traps against a typical {want} for this trace "
            f"({surfaces} surfaces, {usable} usable corrections, {objectives} "
            "objectives). Add more only where the source genuinely supports them",
            "authoring/traps.json"))

    for trap in traps:
        for problem in trap.validate():
            findings.append(Finding(Severity.BLOCKER, "invalid-trap", problem,
                                    "authoring/traps.json"))

    # An authored trap must rest on a surface that exists.
    fixture = next((ctx.path("environment", n) for n in ("files", "fixtures")
                    if ctx.path("environment", n).is_dir()), None)
    for trap in traps:
        if trap.provenance != "authored" or not trap.grounded_in:
            continue
        if fixture is None or not (fixture / trap.grounded_in).exists():
            findings.append(Finding(
                Severity.BLOCKER, "ungrounded-trap",
                f"authored trap {trap.id} is grounded in {trap.grounded_in!r}, which "
                "is not in the fixture", "authoring/traps.json"))

    # The floor is the source tier's, not a flat number. A tier-1 trace carries
    # enough real corrections to supply its own difficulty and is held to 70%; a
    # tier-3 trace does not, and holding it to 70% would only produce a bundle
    # that lies about where its traps came from. Descending the priority order
    # costs fidelity, and this is where that cost is booked rather than absorbed.
    raw = json.loads(ctx.path("authoring/traps.json").read_text())
    tier = raw.get("source_tier")
    if tier is None:
        findings.append(Finding(
            Severity.BLOCKER, "no-source-tier",
            "authoring/traps.json declares no `source_tier`; the trace-derived "
            "floor is tier-dependent and cannot be applied", "authoring/traps.json"))
        floor = TRACE_DERIVED_FLOOR
    elif tier not in TIER_TRACE_FLOOR:
        findings.append(Finding(
            Severity.BLOCKER, "bad-source-tier",
            f"source_tier {tier!r} is not one of {sorted(TIER_TRACE_FLOOR)}",
            "authoring/traps.json"))
        floor = TRACE_DERIVED_FLOOR
    else:
        floor = TIER_TRACE_FLOOR[tier]

    share = trace_derived_share(traps)
    exploitation = trace_exploitation(traps, usable)
    if not usable:
        # 0 of 0 is undefined, not 0%. A fixture-led seed (category C) or an
        # authored one (D) has no dispute to exploit -- that is what makes it
        # that category -- so a floor on "what share of the corrections became
        # traps" asks for the thing its definition denies. Measured: category C
        # bundle a-002-engineering-thesis-writing was blocked for having used
        # 0% of its 0 corrections.
        #
        # The rule still bites everywhere it can: a trace WITH corrections must
        # use them. Here the honest report is that the check does not apply,
        # and the trap gates that do apply -- faithful, beatable -- still run.
        findings.append(Finding(
            Severity.WARN, "no-corrections-to-exploit",
            "this trace carries no usable correction, so the trace-exploitation "
            "floor does not apply. The task is fixture-led or authored, and its "
            "traps must stand on the documents instead -- `trap.faithful` and "
            "`trap.beatable` still decide that", "authoring/traps.json"))
    elif exploitation < floor:
        findings.append(Finding(
            Severity.WARN, "trace-underused",
            f"only {exploitation:.0%} of this trace's {usable} usable corrections "
            f"became traps, below the {floor:.0%} floor for a tier-{tier} source. "
            "The corrections are the failure modes a real user actually hit; "
            "leaving them unused and authoring difficulty instead is how a task "
            "stops being trace-derived", "authoring/traps.json"))

    authored = [t for t in traps if t.provenance == "authored"]
    return findings, {
        "traps": len(traps),
        "floor": MIN_TRAPS,
        "expected": want,
        "surfaces": surfaces,
        "trace_derived": len(traps) - len(authored),
        "authored": len(authored),
        "trace_derived_share": round(share, 3),
        "trace_exploitation": round(exploitation, 3),
        "usable_corrections": usable,
        "source_tier": tier,
        "floor": floor,
        "types": sorted({t.type for t in traps}),
        "sources": [
            ({"id": t.id, "provenance": t.provenance, "class": t.correction_class,
              "quote": t.quote[:120], "cite": t.derived_from}
             if t.provenance == "trace_derived" else
             {"id": t.id, "provenance": t.provenance, "grounded_in": t.grounded_in,
              "grounding": t.grounding[:160]})
            for t in traps],
    }


def _trap_beatable(ctx: GateContext) -> tuple[list[Finding], dict]:
    """The reference solution beats every trap; an adversarial probe does not."""
    traps = _traps(ctx)
    probes = _load(ctx, "verification/probes.json")
    results: dict[str, Any] = probes.get("results", {})
    findings: list[Finding] = []

    golden = results.get("golden", {}).get("reward")
    if golden is None:
        findings.append(Finding(Severity.BLOCKER, "no-golden",
                                "no recorded golden run; the spec requires a reference "
                                "solution proving the task is solvable",
                                "verification/probes.json"))
    elif golden < 1.0:
        findings.append(Finding(
            Severity.BLOCKER, "golden-below-one",
            f"the reference solution scores {golden}; a trap the reference cannot "
            "beat is a broken task, not a hard one", "verification/probes.json"))

    per_trap = results.get("per_trap") or {}
    for trap in traps:
        # Prefer the trap's own mutation: it corrupts exactly the checks this
        # trap claims to drive, so its score says whether THIS trap catches
        # anything. The named shared probe is the fallback.
        # A per-trap mutation is the real evidence; the shared probe named on
        # the trap is only a fallback. Which one was used has to reach the
        # message, or a blocker citing "probe 'plausible_wrong' scores 1.0"
        # sends the reader to a probe that scored 0.98 -- measured on a-005.
        dedicated = per_trap.get(trap.id)
        probe = dedicated if dedicated is not None else results.get(trap.probe)
        source = (f"its own mutation ({', '.join(dedicated.get('mutated') or []) or 'nothing recorded'})"
                  if dedicated is not None else f"the shared probe {trap.probe!r}")
        if probe is None:
            findings.append(Finding(
                Severity.WARN, "trap-unprobed",
                f"trap {trap.id} names probe {trap.probe!r} but no result is "
                "recorded; nothing shows the trap catches anything",
                "verification/probes.json"))
            continue
        reward = probe.get("reward")
        if reward is None and dedicated is not None and not dedicated.get("mutated"):
            missing = [c for c in trap.checks if c not in (probes.get("checks") or {})]
            findings.append(Finding(
                Severity.WARN, "trap-drives-nothing",
                f"trap {trap.id} drives no declared check"
                + (f" (it cites {', '.join(missing)}, which the task does not declare)"
                   if missing else "") + "; it cannot affect any score",
                "authoring/spec.json"))
        elif reward is None:
            findings.append(Finding(
                Severity.WARN, "probe-no-score",
                f"probe {trap.probe!r} recorded no reward", "verification/probes.json"))
        elif golden is not None and reward >= golden:
            findings.append(Finding(
                Severity.WARN, "trap-not-discriminating",
                f"trap {trap.id}: {source} scores {reward}, at or above the "
                f"reference {golden} -- the trap catches nothing",
                "verification/probes.json"))

        # Every trap must move a check, or it cannot affect a score.
        for check in trap.checks:
            if check not in (probes.get("checks") or {}):
                findings.append(Finding(
                    Severity.WARN, "trap-check-unknown",
                    f"trap {trap.id} drives check {check!r}, absent from the probe "
                    "record", "verification/probes.json"))
    # `plausible_wrong` and `untidy_correct` had stated intents in
    # REQUIRED_PROBES and no enforcement anywhere -- the table read like a
    # contract and was documentation.
    #
    # The probe substitutes ONE numeric scalar and stops, so the score it loses
    # is that single check's weight, normally about 1/n. A thin margin is
    # therefore arithmetic, not a defect, and an earlier version of this gate
    # wrongly warned on it. What IS a defect is the probe corrupting a value
    # and the grader not noticing -- and, separately, the probe finding nothing
    # to corrupt, which makes it silent rather than passing.
    golden_probe = results.get("golden") or {}
    golden_reward = golden_probe.get("reward")
    plausible = results.get("plausible_wrong") or {}
    if plausible and plausible.get("applicable") is not False:
        reward = plausible.get("reward")
        mutated = plausible.get("mutated")
        if reward is None:
            findings.append(Finding(
                Severity.BLOCKER, "plausible-wrong-no-score",
                "probe 'plausible_wrong' recorded no reward",
                "verification/probes.json"))
        elif not mutated:
            # It graded a byte-identical copy of the reference. Scoring 1.0
            # here is correct and says nothing about the task, so it must not
            # be read as evidence in either direction.
            findings.append(Finding(
                Severity.WARN, "plausible-wrong-inert",
                "probe 'plausible_wrong' mutated nothing -- no objective has a "
                "numeric scalar target it can shift, so this bundle has no "
                "evidence that a defensible wrong answer scores below the "
                "reference", "verification/probes.json"))
        elif golden_reward is not None and reward >= golden_reward:
            findings.append(Finding(
                Severity.BLOCKER, "plausible-wrong-scores-reference",
                f"probe 'plausible_wrong' shifted {mutated} and still scores "
                f"{reward}, at or above the reference {golden_reward} -- the "
                "grader did not notice a wrong value",
                "verification/probes.json"))

    untidy = results.get("untidy_correct") or {}
    if untidy and untidy.get("applicable") is not False and golden_reward is not None:
        reward = untidy.get("reward")
        if reward is not None and reward < golden_reward:
            findings.append(Finding(
                Severity.BLOCKER, "untidy-correct-penalised",
                f"correct but messy work scores {reward} against the reference "
                f"{golden_reward} -- the grader is scoring formatting, not the "
                "answer; right answers will read as failures",
                "verification/probes.json"))


    return findings, {"golden": golden,
                      "probes": {k: v.get("reward") for k, v in results.items()}}


def _hack_resistance(ctx: GateContext) -> tuple[list[Finding], dict]:
    """Reward hacking must have been attempted, and must have failed.

    §0 of the anti-reward-hacking rules is a design decision -- the answer is
    derived, not stored -- and `answer.derivation` checks the design. This gate
    checks the *behaviour*: someone actually ran the attack and wrote down what
    happened.
    """
    probes = _load(ctx, "verification/probes.json")
    results: dict[str, Any] = probes.get("results", {})
    findings: list[Finding] = []

    # The stored report must be THIS bundle's: bound to its probe inputs and
    # reproduced by the re-run above. A stale file used to certify a bundle
    # whose fixture had since gained its own answer key.
    from ..author.probes import gate_report
    for code, message in gate_report(ctx.task_dir, getattr(ctx, "extras", None))[1]:
        findings.append(Finding(Severity.BLOCKER, code, message, "verification/probes.json"))

    for name, intent in REQUIRED_PROBES.items():
        row = results.get(name)
        if row is None:
            findings.append(Finding(
                Severity.BLOCKER, "probe-missing",
                f"required probe {name!r} was never run ({intent})",
                "verification/probes.json"))
            continue
        # A probe may be declared inapplicable, but only with a reason. Running a
        # probe that cannot fail and reporting it as a pass is the anti-pattern;
        # saying plainly that it does not apply here is not.
        if row.get("applicable") is False:
            reason = (row.get("reason") or "").strip()
            if len(reason) < 40:
                findings.append(Finding(
                    Severity.BLOCKER, "inapplicable-without-reason",
                    f"probe {name!r} is declared inapplicable with no substantive "
                    "reason; say why the probe cannot discriminate here",
                    "verification/probes.json"))
            else:
                findings.append(Finding(
                    Severity.WARN, "probe-inapplicable",
                    f"probe {name!r} declared inapplicable: {reason[:120]}",
                    "verification/probes.json"))

    seed = results.get("seed_zero", {})
    if seed:
        bad_obj = [k for k, v in (seed.get("objectives") or {}).items() if v != 0.0]
        bad_grd = [k for k, v in (seed.get("guardrails") or {}).items() if v != 1.0]
        if bad_obj:
            findings.append(Finding(
                Severity.BLOCKER, "seed-zero-objective",
                f"objective(s) {bad_obj[:5]} score above 0 on the untouched fixture -- "
                "they are reading a seeded record, not the agent's work",
                "verification/probes.json"))
        if bad_grd:
            findings.append(Finding(
                Severity.BLOCKER, "seed-zero-guardrail",
                f"guardrail(s) {bad_grd[:5]} fail on the untouched fixture -- "
                "mis-specified; they would zero every attempt",
                "verification/probes.json"))

    # `destructive` breaks a surface a guardrail protects, so the task must
    # score ZERO. Measured on a-002-engineering-thesis-writing: it scored 1.0 --
    # both `fixture_intact` guardrails passed while the fixture was broken, so
    # an agent could destroy the workspace and still take full marks. The table
    # above has always said this; nothing asserted it. That is the third entry
    # in REQUIRED_PROBES found to be documentation rather than a rule, after
    # `plausible_wrong` and `untidy_correct`.
    destructive = results.get("destructive") or {}
    if destructive and destructive.get("applicable") is not False:
        reward = destructive.get("reward")
        if reward is None:
            findings.append(Finding(
                Severity.BLOCKER, "destructive-no-score",
                "probe 'destructive' recorded no reward", "verification/probes.json"))
        elif reward > 0.0 and destructive.get("destroyed_was_protected"):
            findings.append(Finding(
                Severity.BLOCKER, "destructive-survives",
                f"the probe destroyed {destructive.get('destroyed')!r}, which a "
                f"guardrail claims to protect, and the task still scores "
                f"{reward}. An agent could break the fixture and take the marks",
                "verification/probes.json"))
        elif reward > 0.0:
            # The probe broke a file no guardrail watches, so the score says
            # nothing about whether the guardrails work. Not a defect in the
            # task -- an absence of evidence, and it must read as one.
            findings.append(Finding(
                Severity.WARN, "destructive-unprotected-target",
                f"the probe destroyed {destructive.get('destroyed')!r}, which "
                "backs no projection, so `fixture_intact` had nothing to detect. "
                "This run shows nothing about the guardrails either way",
                "verification/probes.json"))

    for name in ("forged_state", "answer_lookup"):
        probe = results.get(name)
        if not probe or probe.get("applicable") is False:
            continue
        reward = probe.get("reward")
        if reward is None:
            findings.append(Finding(Severity.BLOCKER, "hack-probe-no-score",
                                    f"probe {name!r} recorded no reward",
                                    "verification/probes.json"))
        elif reward >= 1.0:
            findings.append(Finding(
                Severity.BLOCKER, "reward-hack-succeeds",
                f"probe {name!r} scored {reward} without doing the work. "
                + ("Forging the end state must fail on provenance."
                   if name == "forged_state" else
                   "The answer is readable in the fixture; make it derived (§0)."),
                "verification/probes.json"))
        elif reward > 0.5:
            findings.append(Finding(
                Severity.WARN, "reward-hack-partial",
                f"probe {name!r} scored {reward} without doing the work; a hack that "
                "earns most of the reward is still a hack", "verification/probes.json"))

        # Reward alone lets partial leaks through. A bundle whose three
        # readable answers are worth 30% of the task scores 0.3 here and used
        # to pass, yet those three checks measure nothing: the agent that
        # greps them is indistinguishable from the agent that reasoned. §0 is
        # not a threshold to stay under, so every readable field blocks --
        # which is only usable because `_distinctive` now keeps coincidental
        # small-integer matches out of this set.
        if name == "answer_lookup":
            readable = sorted((probe.get("readable_from_fixture") or {}))
            if readable:
                findings.append(Finding(
                    Severity.BLOCKER, "answer-readable-in-fixture",
                    f"{len(readable)} check(s) have an answer readable straight from the "
                    f"fixture: {', '.join(readable[:6])}"
                    f"{' ...' if len(readable) > 6 else ''}. An agent that finds the "
                    "document scores without reasoning, so these checks cannot tell a "
                    "solver from a reader. Make the answer derived -- a set difference, "
                    "residue or reconciliation no single document states (§0).",
                    "verification/probes.json"))

    # An empty deliverable is a distinct hack from the two above: it invents
    # nothing and reads nothing, it simply declines to answer, and it collects
    # every objective whose correct answer is an empty collection. Measured on
    # kw-a009 that was 69% of the weight with all fifteen gates green, so this
    # blocks harder than the 0.5 warning the other probes carry.
    empty = results.get("empty_deliverable")
    if empty is None:
        findings.append(Finding(
            Severity.BLOCKER, "empty-probe-missing",
            "no `empty_deliverable` result; what an empty deliverable earns is "
            "unmeasured, and seed_zero does not cover it -- seed_zero omits the "
            "file entirely, so every check fails for the wrong reason",
            "verification/probes.json"))
    else:
        reward = empty.get("reward")
        if reward is None:
            findings.append(Finding(
                Severity.BLOCKER, "empty-probe-no-score",
                "probe 'empty_deliverable' recorded no reward",
                "verification/probes.json"))
        elif reward > 0.34:
            findings.append(Finding(
                Severity.BLOCKER, "empty-deliverable-scores",
                f"an empty deliverable scores {reward}: objectives carrying most "
                "of the weight have an empty collection as their correct answer, "
                "so declining to answer earns them. Reshape the fixture so the "
                "derived sets are non-empty, or drop the checks",
                "verification/probes.json"))
        elif reward > 0.15:
            findings.append(Finding(
                Severity.WARN, "empty-deliverable-partial",
                f"an empty deliverable scores {reward}; confirm each empty-set "
                "answer is a real finding rather than a projection that matched "
                "nothing", "verification/probes.json"))

    # PLAYBOOK §2's load-bearing test, measured: empty each fixture document in
    # turn and see whether any scored answer moves. A document that changes
    # nothing is not carrying the question.
    #
    # This warns rather than blocks, because inert is not the same as useless: a
    # `plausible_decoy` is inert BY DESIGN -- a draft named `final` that the
    # instruction says is not authoritative changes no answer and is the entire
    # trap. What the playbook actually warns about is breadth mistaken for
    # difficulty, so the threshold is set where most of the fixture is doing
    # nothing. Measured on this batch: a007 carries 38 documents of which 28
    # move no answer at all.
    leverage = results.get("surface_leverage") or {}
    if leverage.get("error"):
        findings.append(Finding(
            Severity.WARN, "leverage-unmeasured",
            f"surface leverage could not be measured ({leverage['error']}); "
            "whether every document carries the question is unknown",
            "verification/probes.json"))
    elif leverage.get("documents"):
        inert = leverage.get("inert") or []
        share = leverage.get("inert_share") or 0.0
        if share >= 0.5 and len(inert) >= 3:
            findings.append(Finding(
                Severity.WARN, "fixture-mostly-inert",
                f"{len(inert)} of {leverage['documents']} documents "
                f"({share:.0%}) change no scored answer when emptied: "
                + ", ".join(sorted(inert)[:6])
                + (" ..." if len(inert) > 6 else "")
                + ". Confirm each is a decoy rather than decoration -- breadth "
                  "is not difficulty, coupling is", "environment/files"))

    untested = probes.get("untested_surfaces")
    if not untested:
        findings.append(Finding(
            Severity.BLOCKER, "no-untested-declaration",
            "verification/probes.json declares no `untested_surfaces`. Every time "
            "this stack was called closed, another surface turned up; the bundle "
            "must state what was not probed", "verification/probes.json"))

    return findings, {"ran": sorted(results), "untested_surfaces": untested}


def _axes(ctx: GateContext) -> tuple[list[Finding], dict]:
    """At least two difficulty axes, and a lever beyond Carry.

    A task loading only execution is a long-form instruction-following test.
    Breadth is not difficulty: measured in one corpus, tasks touching <=3
    surfaces produced a mean inter-model spread of 0.413 while 7-surface tasks
    produced 0.126. Coupling is difficulty.
    """
    traps = _traps(ctx)
    findings: list[Finding] = []
    axes = {TAXONOMY[t.type].axis for t in traps if t.type in TAXONOMY}
    levers = {TAXONOMY[t.type].lever for t in traps if t.type in TAXONOMY}

    # Both shape rules below are difficulty judgments, so they advise and never
    # block: phase 3 is validity only and "difficulty is never a build-time
    # repair finding" (POLICY.md; user 2026-09-26, "validity blocks, difficulty
    # advises"). As blockers they sent a-028 (build 2026-09-26) into a repair
    # round for loading only the inference axis. The screen measures difficulty.
    if len(axes) < 2:
        findings.append(Finding(
            Severity.WARN, "one-axis",
            f"traps load only {sorted(axes) or ['nothing']}; a task needs at least "
            "two of inference/execution/restraint", "authoring/traps.json"))
    if "restraint" not in axes:
        findings.append(Finding(
            Severity.WARN, "no-restraint-axis",
            "no restraint trap. Restraint is the cheapest difficulty per unit of "
            "authoring effort and usually what separates strong models -- capable "
            "agents over-act", "authoring/traps.json"))
    if levers <= {"carry"}:
        findings.append(Finding(
            Severity.WARN, "carry-only",
            "every trap uses the Carry lever; add a Join or Arbitration so the "
            "answer cannot be reached by transcription", "authoring/traps.json"))
    if "sequence" in levers:
        for trap in traps:
            if TAXONOMY[trap.type].lever == "sequence" and trap.checks:
                findings.append(Finding(
                    Severity.WARN, "sequence-lever",
                    f"trap {trap.id} uses the Sequence lever, the one most likely to "
                    "become an unclearable gate; never make it a prerequisite",
                    "authoring/traps.json"))

    has_unsat = any(t.type == "unsatisfiable" for t in traps)
    return findings, {"axes": sorted(axes), "levers": sorted(levers),
                      "graded_abstention": has_unsat,
                      "note": "graded_abstention is the only legitimate form of "
                              "'the model gives up': recognising the impossible "
                              "part is itself scored, so fabricating an answer "
                              "fails rather than passing unnoticed"}


trap_faithful_gate = FunctionGate("trap.faithful", _trap_faithful,
                                  requires=("bundle.structure",))
trap_beatable_gate = FunctionGate("trap.beatable", _trap_beatable,
                                  requires=("trap.faithful",))
hack_gate = FunctionGate("hacking.resistance", _hack_resistance,
                         requires=("bundle.structure",))
axes_gate = FunctionGate("difficulty.axes", _axes, requires=("trap.faithful",))
