"""Every acceptance threshold in the programme, in one place, with its source.

Before this module the thresholds lived in prose across five documents and in
constants across a dozen modules, and two of them contradicted each other badly
enough to close the funnel at both ends: `release.py` required a model to solve
a task perfectly blind *before* difficulty was measured, and the band gate then
required most checks to sit at 30-70%. A genuinely hard task could satisfy
neither. Of 86 candidates in `envs-cat-v2`, 47 died on unrepairable findings and
the 12 that reached calibration scored 0.93-1.00 mean reward. Nothing shipped.

So: a threshold lives here or it does not exist. Each carries the clause of the
Arena spec (RL Environments Quality Spec, 2026-09-21) it implements, or an
explicit note that it is ours. `SPEC_*` names are Arena's numbers and change
only when Arena changes them; anything else is a local decision and says so.

Nothing here decides whether a task is *good*. These are admissibility bounds.
"""
from __future__ import annotations

# ---------------------------------------------------------------------------
# Calibration models
# ---------------------------------------------------------------------------

#: Spec, "Calibration and results": primary Fable 5.1, secondary Astra. The
#: difficulty thresholds below were set by Arena against these models, so
#: substituting one is a deviation the batch report must declare rather than a
#: free choice -- a pass@1 measured on a different model is not the same number.
SPEC_PRIMARY_MODEL = "claude-fable-5-1"

#: GPT 6 Astra, OpenAI. `resolve_model` routes a bare `gpt-` id to `openai/`.
SPEC_SECONDARY_MODEL = "gpt-6-astra"

#: Reasoning effort for BOTH calibration models, set by the user on
#: 2026-09-23. It is part of the measurement, not a runtime detail: a pass@1 is
#: "Fable 5.1 at high", not "Fable 5.1", and a figure taken at another effort is
#: not comparable. `release.py` already refuses to mix efforts across a task's
#: two campaigns; this makes the level itself explicit and reportable.
#:
#: Note the direction of the risk. Higher effort makes capable models act more,
#: and the restraint guardrails are exactly the checks that catch over-acting,
#: so effort moves guardrail rates as well as objective rates.
SPEC_CALIBRATION_EFFORT = "high"

#: The agent harness each calibration model runs in (user, 2026-09-26): Fable
#: 5.1 in Claude Code, GPT 6 Astra in Codex, both at SPEC_CALIBRATION_EFFORT.
#: Like effort, the harness is part of the measurement -- "Fable 5.1 in Claude
#: Code at high" -- and a campaign under any other harness is not comparable.
#: Both run INSIDE the task container (Terminus-2 drove it from outside), so
#: each gets its CLI pre-baked into the task image at a pinned version and, for
#: the agent phase only, network egress to its own model API host and nothing
#: else. The separate verifier stays offline.
CALIBRATION_HARNESS = {SPEC_PRIMARY_MODEL: "claude-code", SPEC_SECONDARY_MODEL: "codex"}

#: Pinned CLI versions (npm, resolved 2026-09-26). An update is an explicit
#: change: it alters the task image and therefore every artifact hash.
HARNESS_VERSIONS = {"claude-code": "2.1.283", "codex": "0.157.1"}

#: The only hosts each harness may reach during the agent phase. A configured
#: provider base URL (ANTHROPIC_BASE_URL / OPENAI_BASE_URL) adds its host.
HARNESS_API_HOSTS = {"claude-code": ("api.anthropic.com",), "codex": ("api.openai.com",)}


#: A documented substitute model (CALIBRATION_SUBSTITUTIONS) runs in its
#: provider's harness: Claude models in Claude Code, OpenAI models in Codex.
PROVIDER_HARNESS = {"anthropic": "claude-code", "openai": "codex"}


def harness_for(model) -> str:
    """The agent harness a calibration model runs in (Claude Code / Codex)."""
    text = str(model or "")
    bare = text.split("/")[-1].lower()
    harness = next((h for m, h in CALIBRATION_HARNESS.items() if m.lower() == bare), None)
    if harness is None:
        provider = (text.split("/", 1)[0].lower() if "/" in text else
                    "anthropic" if bare.startswith("claude-") else
                    "openai" if bare.startswith("gpt-") else None)
        harness = PROVIDER_HARNESS.get(provider)
    if harness is None:
        raise ValueError(f"{model}: no calibration harness is assigned to this model "
                         f"(assigned: {CALIBRATION_HARNESS}; by provider: {PROVIDER_HARNESS})")
    return harness


#: No turn cap, no wall-clock deadline on a calibration episode (user,
#: 2026-09-23). This is a measurement decision, not a convenience.
#:
#: A run stopped on `step_cap` or `max_tokens` wrote no deliverable and is
#: recorded VOID -- it measured nothing. Measured on a008: all ten rollouts
#: stopped on `max_tokens` with an empty deliverables directory and were
#: recorded as ten model failures at mean 0.00. That is a void wearing a
#: result's clothes. A tight cap therefore destroys data rather than measuring
#: difficulty, and it does so in the direction that makes a task look harder
#: than it is.
#:
#: Removing the caps means a hard task fails because the model could not do it,
#: not because it ran out of turns. The provider's own limits and the transport
#: read timeout remain the real bound; fault detection is unaffected.
SPEC_NO_LIMITS = True

#: Operator decision, 2026-09-24: the output allowance per request for each
#: calibration model -- 128k for both models, within their published output
#: limits. Applied by default to every native and file-workspace campaign, and
#: required by release. A turn cut off by the allowance wrote no deliverable
#: and is VOID, so too small an allowance destroys data rather than measuring.
SPEC_MAX_OUTPUT_TOKENS = {SPEC_PRIMARY_MODEL: 128_000, SPEC_SECONDARY_MODEL: 128_000}


def output_tokens_for(model) -> int | None:
    """The spec output allowance for a calibration model, or None if it has none."""
    bare = str(model or "").split("/")[-1].lower()
    return next((v for k, v in SPEC_MAX_OUTPUT_TOKENS.items() if k.lower() == bare), None)

#: Models this programme must NOT calibrate on, with the reason. A stale default
#: buried in three argparse declarations is how a batch gets measured on a model
#: nobody chose.
RETIRED_CALIBRATION_MODELS = {
    "gpt-5.6-sol": "superseded by GPT 6 Astra for calibration (user, 2026-09-23)",
    "claude-opus-5": "superseded by Fable 5.1 as the primary calibration model",
}


def calibration_problems(models) -> list[str]:
    """Refuse a campaign aimed at a retired calibration model.

    Matched on the bare model id, case-insensitively: `Claude-Opus-5` and
    `anthropic/CLAUDE-OPUS-5` are the same retired model, and a guard that an
    upper-case letter walks past is not a guard.
    """
    retired = {name.casefold(): reason for name, reason in RETIRED_CALIBRATION_MODELS.items()}
    issues = []
    for model in models or []:
        bare = str(model).strip().split("/")[-1].casefold()
        if bare in retired:
            issues.append(f"{model}: {retired[bare]}")
    return issues


def refuse_retired(model) -> None:
    """Raise before any campaign is launched on a retired calibration model.

    Every launcher calls this (`benchmark.harbor.run_campaign` for Terminus-2,
    `calibrate.run.campaign`, and through them the calibration screen, the
    benchmark CLI and category_batch), so a stale default cannot spend money on
    a model nobody chose and only be caught at release.
    """
    issues = calibration_problems([model])
    if issues:
        raise ValueError("retired calibration model: " + "; ".join(issues))

#: Substitutions actually used, when the spec models are unavailable. Every
#: entry lands in the batch report's deviations section. An empty mapping means
#: the batch was measured exactly as specified.
MODEL_SUBSTITUTIONS: dict[str, str] = {}


def resolve_calibration_models() -> tuple[str, str]:
    """(primary, secondary) after substitution, in spec order."""
    return (MODEL_SUBSTITUTIONS.get(SPEC_PRIMARY_MODEL, SPEC_PRIMARY_MODEL),
            MODEL_SUBSTITUTIONS.get(SPEC_SECONDARY_MODEL, SPEC_SECONDARY_MODEL))


def model_deviations() -> list[dict]:
    """What the batch report must disclose about the models measured."""
    return [{"spec_model": spec, "measured_model": actual,
             "effect": "difficulty thresholds were calibrated by Arena against "
                       f"{spec}; rates measured on {actual} are not directly "
                       "comparable to the spec's bands"}
            for spec, actual in sorted(MODEL_SUBSTITUTIONS.items())]


# ---------------------------------------------------------------------------
# Difficulty
# ---------------------------------------------------------------------------

#: Spec, "Task-Level checks": "Target pass@1 below 0.5 on both calibration
#: models for every task."
SPEC_GENERAL_DIFFICULTY_MAX = 0.5

#: Spec, same section: "A task qualifies as 'hard' when the primary calibration
#: model passes no more than 2 of 10 runs, equivalent to pass@1 <= 0.2."
SPEC_HARD_MAX = 0.2
SPEC_YIELD_DIFFICULTY_MAX = 0.5

RELEASE_PASS_AT_1_MAX = SPEC_GENERAL_DIFFICULTY_MAX

#: User, 2026-09-25: "We should not have any blockers in task creation ... pass@1
#: < 0.5 should be our strict target." Difficulty never blocks a task anywhere
#: in the pipeline -- not the build, not the screen, not the calibration of
#: record, not release. It is measured, reported against the target and driven
#: down by authoring and hardening. What still blocks is VALIDITY: a grader
#: defect, a leak, void or unattributable episodes, unresolved reward hacking.
#: Arena's own batch criterion (>= 90% of tasks under 0.5) is still reported,
#: honestly, by the batch report. Named so the absence is greppable.
DIFFICULTY_GATES_RELEASE = False

#: Local decision: what authoring aims for. Not a gate -- a task measured at 0.4
#: is a good task. This is the number the batch report drives up over time.
AUTHOR_TARGET_PASS_AT_1 = SPEC_HARD_MAX

#: User, 2026-09-25: the STRICT TARGET -- pass@1 strictly below this on BOTH
#: calibration models. Arena's general difficulty number. Authoring aims at it,
#: every screen and calibration reports against it, and hardening stops once a
#: revision meets it. It blocks nothing (`DIFFICULTY_GATES_RELEASE`): a task
#: above it is reported with its hardening outlook, never discarded or held.
#: User, 2026-10-02: "Below or equal to 0.5 is considered hard." The target is
#: met at pass@1 <= this value on both models (it was strict < before).
CALIBRATION_TARGET_PASS_AT_1 = SPEC_GENERAL_DIFFICULTY_MAX

#: User, 2026-10-02: "We need to make all the steps hard and below or equal to 0.6
#: score." Per step, the share of valid episodes whose step reward is 1.0 must be
#: <= this on each calibration model. A hardening lineage meets its target only
#: when every step of a screened revision is at or under it on BOTH models (a
#: whole-task pass@1 <= 0.5 carried by one hard step no longer ends a lineage);
#: the shipping bar reads the same per-step rate on Fable. Not a release gate
#: (`DIFFICULTY_GATES_RELEASE`).
STEP_PASS_RATE_MAX = 0.6

#: Spec, "Batch-Level acceptance criteria", Task quality: "At least 90% of tasks
#: meet the grader sanity, solvability, and general difficulty checks." General
#: difficulty is the strict 0.5 target above.
BATCH_UNDER_SPEC_DIFFICULTY_MIN = 0.90

#: Spec, "Calibration and results": "Run each task 10 times with each model."
#: This is a floor on *valid* episodes. Voids do not count toward it, which is
#: the whole point of counting them separately. It is the calibration OF RECORD
#: -- what ships -- and it runs once a screen of the version measured cleanly
#: AND met the target (user, 2026-10-16: QUALIFY_REQUIRES_SCREEN_TARGET; release
#: itself is still never conditioned on pass@1: `DIFFICULTY_GATES_RELEASE`).
SPEC_EPISODES_PER_MODEL = 10

#: User, 2026-09-25: episodes per model in a calibration SCREEN. Two screens
#: exist and both use this width: the first calibration of a freshly authored
#: batch (run once every task in the batch is built, never per task), and the
#: re-measure after every manual hardening round. The SPEC_EPISODES_PER_MODEL
#: campaign runs only on a task whose current screen measured cleanly (valid
#: episodes, attributable failures, no unresolved reward hacking) -- never
#: conditioned on its pass@1. Five episodes is enough to report pass@1, pass@4 (k <= n) and mean
#: reward per model; it is not a precise estimate, and the report says so.
#:
#: This replaced the one-episode presolve screen, which ran after every draft on
#: one model and fed its verdict back into the design loop.
#:
#: User, 2026-10-16: "the pilot calibration to be 3 attempts per model instead of
#: 5 attempts. Only if the pilot calibration meets the criteria then only run the
#: full calibration" -- for that batch "and also moving forward". Three episodes
#: per model: pass@1 moves in steps of 1/3, so the target (<= 0.5) is met by at
#: most one full pass of three per model, and pass@4 is not reported for a screen
#: (k > n; `metrics.pass_at_k` returns None). See QUALIFY_REQUIRES_SCREEN_TARGET.
SCREEN_EPISODES_PER_MODEL = 3

#: User, 2026-10-16 (same instruction): the SPEC_EPISODES_PER_MODEL calibration of
#: record is bought only for a task version whose screen MET the target --
#: pass@1 <= CALIBRATION_TARGET_PASS_AT_1 on BOTH calibration models -- on top of
#: measuring cleanly (`screen.shippable_problems`). This is a COST gate on
#: launching the ten-episode campaign (`screen.qualify_problems`, read by
#: `release.qualify`), not a release gate: DIFFICULTY_GATES_RELEASE stays False,
#: and a task whose calibration of record already exists is not re-gated. A task
#: whose screen misses the target is hardened (a new version, a new screen) or
#: reported as measured; it never gets a ten-episode campaign on a missed screen.
QUALIFY_REQUIRES_SCREEN_TARGET = True

#: Spec, "Task-Level checks": "Report pass@1, pass@4, and average reward per
#: task." pass@k needs at least k episodes to mean anything.
SPEC_REPORTED_K = (1, 4)

#: Extra episodes per task per model, to replace ones lost to INFRASTRUCTURE
#: (user, 2026-09-23). Matches the retained cost model, which budgets "10
#: attempts plus 5 reruns per model" at a measured $39.52 per task.
#:
#: A void episode measured nothing -- container error, transport stall,
#: truncation, adapter stall -- so it leaves every denominator. Without a top-up
#: a campaign that loses two episodes to a flaky container reports a rate over
#: eight, or fails the ten-episode floor and wastes the eight that worked.
MAX_TOPUP_ATTEMPTS = 5

#: What may be topped up. This list is the whole safety property: only outcomes
#: that measured NOTHING are replaceable. A capability failure and a contract
#: failure are results -- re-running either until the number improves is
#: shopping for a score, and it would make every difficulty figure a lower bound
#: on how many times we tried.
TOPUP_REPLACES = ("void",)

#: Never. Named so the prohibition is greppable rather than implied.
TOPUP_NEVER_REPLACES = ("capability", "contract", "pass")


def topup_problems(before: dict, after: dict, replaced: int | None = None) -> list[str]:
    """Refuse a top-up that changed anything but the void count.

    `before` and `after` are attribution count maps over the *merged*
    measurement (the retained scored episodes plus the replacements), with
    `void` the voids of the latest launch. A top-up may only convert voids into
    real outcomes; if the number of episodes that actually produced a result
    went *down*, or a previously recorded result disappeared, the campaign was
    replaced rather than topped up. `replaced`, when given, is how many
    episodes the top-up launched: scored outcomes may grow by at most that.
    """
    issues = []
    if replaced is not None:
        grew = sum(after.get(k, 0) - before.get(k, 0) for k in TOPUP_NEVER_REPLACES)
        if grew > replaced:
            issues.append(
                f"top-up added {grew} scored episodes but launched only {replaced}; "
                "scored episodes were re-run rather than voids replaced")
    lost = [name for name in TOPUP_NEVER_REPLACES
            if after.get(name, 0) < before.get(name, 0)]
    if lost:
        issues.append(
            f"top-up lost recorded outcomes ({', '.join(sorted(lost))}); only "
            "void episodes may be replaced, because re-running a scored episode "
            "until the number improves is shopping for a result")
    if after.get("void", 0) > before.get("void", 0):
        issues.append("top-up produced more voids than it replaced; the "
                      "infrastructure fault is not transient")
    return issues


# ---------------------------------------------------------------------------
# Solvability
# ---------------------------------------------------------------------------

#: Spec, "Task-Level checks", Grader sanity: "Run the reference solution and an
#: untouched workspace through the grader. They must score full marks and zero,
#: respectively."
SPEC_REFERENCE_REWARD = 1.0
SPEC_UNTOUCHED_REWARD = 0.0

#: Spec, "Task-Level checks", Solvability: "At least one calibration run OR
#: reference trajectory scores 1.0." The reference trajectory alone satisfies
#: it.
#:
#: This constant exists to record a removal. Until 2026-09-23 `release.py`
#: required one of three blind model episodes to score reward 1.0 on every step
#: before a task could reach difficulty measurement -- effectively pass@3 == 1.0
#: as an admission requirement. That is strictly stronger than the spec and it
#: inverts the objective: the harder a task is, the less likely it survives.
#: Every task that reached calibration under it scored 0.93-1.00 mean reward,
#: because the gate had already removed everything else.
#:
#: The blind solve may still be *run* -- it is useful evidence -- but it cannot
#: gate. See `attribution.py` for what replaced it.
BLIND_SOLVE_GATES_RELEASE = False


# ---------------------------------------------------------------------------
# Failure attribution
# ---------------------------------------------------------------------------
# Spec, "Calibration and results": "Check failed runs to confirm the cause is
# model capability, not ambiguous instructions or an environment or grader bug."
#
# With the blind-solve gate gone, this is what stands between "extremely hard"
# and "quietly broken". A task where every episode fails is now admissible, so
# the burden moves onto proving the failures are the model's.

#: Every failed episode must carry one of these. `unattributed` blocks release:
#: an unclassified failure is indistinguishable from a defect.
EPISODE_VERDICTS = ("capability", "contract", "void", "unattributed")

#: Verdicts that count as evidence a model could not do the task.
CAPABILITY_VERDICTS = ("capability",)

#: Verdicts excluded from the pass@1 denominator entirely. A void measures
#: nothing; averaging it in produces a difficulty number that is partly a
#: record of our own infrastructure.
EXCLUDED_FROM_DENOMINATOR = ("void",)

#: Local decision: share of episodes that may die on a malformed or missing
#: deliverable before the output contract itself is suspect. A model that cannot
#: emit the declared schema might be failing on capability, or the schema might
#: be underspecified, and past this share the second explanation is likelier
#: than the first. Contract deaths look exactly like difficulty in a results
#: table, which is why this has a ceiling at all.
MAX_CONTRACT_FAILURE_SHARE = 0.30

#: Local decision: a check that no episode ever reached measured nothing. Its
#: weight is unreachable, not hard. `gated_out` is not `failed`.
MAX_UNREACHABLE_CHECKS = 0

#: Local decision: proof obligations a check must satisfy before an all-fail
#: result counts as a capability wall rather than a suspected defect. A hard
#: task is expected to have many all-fail checks; each one has to earn it.
ALL_FAIL_PROOF_OBLIGATIONS = (
    # perturb the source: the old answer must fail and an independently
    # recomputed answer must pass. Proves the check reads the fixture rather
    # than comparing against something stored.
    "source_counterfactual",
    # a correct answer phrased differently must still pass. Proves a zero is a
    # wrong answer and not a normalisation artefact.
    "phrasing_alternative",
    # the check was attempted in at least one episode.
    "reachable",
    # no outstanding near-miss adjudication (a submission carrying the
    # reference answer verbatim, or >=80% of it, that still scored zero).
    "near_miss_adjudicated",
)

#: Near-miss threshold, from the existing `suspect_zeros` heuristic. Overlap at
#: or above this on a zero-scoring submission needs a human verdict before the
#: zero can be called the model's.
NEAR_MISS_OVERLAP = 0.80


# ---------------------------------------------------------------------------
# Grader shape
# ---------------------------------------------------------------------------

#: Local decision, and the reason a weight reads as a percentage. Objective
#: weights across the whole bundle -- every task, every step -- sum to exactly
#: this, so every task in a batch carries the IDENTICAL grader total (user,
#: 2026-09-25). Before it was enforced the batch ran totals from 84 to 128,
#: which made `weight: 20` worth 24% of one task and 16% of another. The build
#: normalises to it (`author.build.normalise_weights`) and the `weight-budget`
#: gate refuses a built `tests/checks.json` that does not sum to it.
WEIGHT_TOTAL = 100

#: User, 2026-09-25: minimum objective (graded) checks per task. Was 5. Every
#: task carries at least this many, and every one of them must be demonstrably
#: failable by a plausible wrong answer (`assurance.controls`) and passable by a
#: differently phrased correct one -- a check that cannot discriminate between
#: attempts is not counted as difficulty, it is a defect. Read by
#: `author.validate` (the designer's own check), the designer prompt, and the
#: `objective-count` gate on the built `tests/checks.json`.
MIN_OBJECTIVES = 8

#: Local decision: share of objective weight that must rest on semantic work --
#: a professional decision -- rather than on presence, inclusion or literal
#: matching. Floor checks may cover required fields; they cannot supply this.
MIN_SEMANTIC_WEIGHT_SHARE = 0.70


# ---------------------------------------------------------------------------
# Per-check bands: DIAGNOSTIC ONLY
# ---------------------------------------------------------------------------
# These describe where a check sat. Until 2026-09-23 they also gated release --
# 4-6 checks at 30-70% per model, at most 2 below 30%. A genuinely hard task has
# *most* checks below 30%, so the rule forbade by construction the thing the
# programme exists to produce. They now feed the calibration analysis, which
# finds dead and void checks, and they have no release power.

CORE_LO, CORE_HI, FLOOR_LO = 0.30, 0.70, 0.90
BANDS = ("stretch", "core", "transition", "floor", "unreachable")

#: Whether band composition can reject a task. Kept as a named constant so the
#: answer is greppable rather than implied by the absence of a call.
BANDS_GATE_RELEASE = False


# ---------------------------------------------------------------------------
# Faithfulness (F0-F3)
# ---------------------------------------------------------------------------
# Spec, "Monitoring metrics", Faithfulness. This taxonomy is Arena's and is
# reported per environment AND per task.
#
# Note the collision this resolves: `F1`/`F2`/`F3` were already used in this
# codebase as *stage* names (F1 extract, F2 design, F3 build). Those are
# unrelated to faithfulness levels and are being renamed; anything reading
# `F2` as a faithfulness level must come through here.

FAITHFULNESS_LEVELS = {
    "F3": {"source": "Replay",
           "definition": "Enough session content survives to build the task "
                         "directly; fixture and answer key are similar or "
                         "identical to trace files, grading from what the user "
                         "actually corrected."},
    "F2": {"source": "Scenario",
           "definition": "Original files were unavailable, so the fixture is "
                         "reconstructed or invented, but scenario, failure mode "
                         "and grading criteria still come from the trace."},
    "F1": {"source": "Pattern",
           "definition": "Fully synthetic world. Only the trace's failure mode "
                         "is preserved, and calibration runs must show models "
                         "failing the same way."},
    "F0": {"source": "Inspired",
           "definition": "A concrete user goal and the capability needed to "
                         "complete it are recoverable. A synthetic scenario "
                         "and verifier exercise that same goal and capability, "
                         "with evidence of the specific source inspiration."},
    "F-1": {"source": "Unrelated",
            "definition": "Nothing recoverable from the trace; the task "
                          "needs to be invented whole."},
}

#: Spec updated September 28, 2026: aim at >=50% F1+ and >=15% F2+.
SPEC_VERSION = "2026-09-28"
SPEC_F1_PLUS_MIN = 0.50
SPEC_F2_PLUS_MIN = 0.15

#: The updated spec allows Inspired/F0 and excludes Unrelated/F-1.
SPEC_F0_ALLOWED = True

#: Local decision: the measured source-fidelity share each level requires. The
#: level is a claim about provenance; this is the arithmetic that has to back
#: it. Exact copies and mechanically verified anonymization earn full credit,
#: derived files half, authored files none.
FAITHFULNESS_FIDELITY_FLOOR = {"F3": 0.90, "F2": 0.0, "F1": 0.0, "F0": 0.0}

#: F3 preserves a correction-share floor; F2 uses semantic trace alignment.
FAITHFULNESS_TRACE_DERIVED_FLOOR = {"F3": 0.70, "F2": 0.0}

#: Local decision, unchanged from the prior tier scheme: below this the trace is
#: discarded rather than synthesised into an F1 task, because an F1 task must
#: still reproduce the trace's failure mode under calibration and a trace this
#: thin cannot demonstrate one.
FIXTURE_FLOOR_MIN = 0.80

#: Local decision: trace-derived share of traps, by category. Difficulty may be
#: invented; the world it happens in may not.
TRACE_DERIVED_TRAP_FLOOR = 0.50
CATEGORY_TRACE_FLOOR = {"A": 0.70, "B": 0.55, "C": 0.40, "D": 0.30}
CATEGORY_FIXTURE_FLOOR = {"A": 0.90, "B": 0.90, "C": 0.80, "D": 0.60,
                          # Build categories are target levels since 2026-09-26.
                          # F2/F1/F0 permit synthetic fixtures under the updated
                          # spec; semantic trace alignment establishes their level. The
                          # letters stay so bundles built before then keep theirs.
                          "F3": 0.90, "F2": 0.0, "F1": 0.0, "F0": 0.0}


# ---------------------------------------------------------------------------
# Batch-level acceptance
# ---------------------------------------------------------------------------
# Spec, "Batch-Level acceptance criteria". All six, verbatim thresholds.

#: "Reviewable - 100% of tasks: harbor tasks-check pass, calibration runs +
#: provenance included."
SPEC_REVIEWABLE_MIN = 1.00

#: "Reward hacking - 0 confirmed or unresolved cases."
SPEC_MAX_REWARD_HACKING = 0

#: "Trace accounting - 100% of shared traces dispositioned (converted -> env
#: IDs, or excluded -> reason)."
SPEC_TRACE_ACCOUNTING_MIN = 1.00

#: "Multi-turn - >=10% of environments include a multi-turn task."
SPEC_MULTI_TURN_MIN = 0.10


# ---------------------------------------------------------------------------
# Repair
# ---------------------------------------------------------------------------
# The other half of why nothing shipped. Policy was one design attempt and a
# default repair budget of zero, so a correct review finding was a death
# sentence: 47 of 86 candidates were discarded carrying findings that named the
# exact file and the exact line to change. The corpus was being burned instead
# of the work being finished.
#
# The opposite failure is a loop that never terminates. The invariant below is
# what makes bounded repair safe: progress or stop.

#: Local decision: repair passes per candidate, across every source of findings.
#: One budget, not the three that existed before (gate, qualification,
#: difficulty) plus an ad-hoc authorization layer.
MAX_REPAIR_PASSES = 2

#: The anti-doom-loop invariant. A repair pass is admissible only if the finding
#: set strictly shrinks: every finding resolved stays resolved, and no pass may
#: return the same finding twice. A repeated finding is terminal -- it means the
#: author cannot see what the reviewer sees, and another pass will not change
#: that.
REQUIRE_MONOTONE_REPAIR = True

#: Local decision: a finding must cite a concrete artifact location to be
#: actionable. "The task is too easy" is not repairable; "checks.json line 40
#: omits the journaling ceiling" is.
REQUIRE_FINDING_CITATION = True

#: User, 2026-09-25: redesign attempts a task may receive from hardening, over
#: its WHOLE lineage (the original and every revision built from it), across
#: every `arena harden` invocation. Every call to the designer that returns a
#: revision counts -- validity repairs included -- so hardening cannot become a
#: loop of redesigning the same task again and again. Attempt 1 carries the
#: whole hardening brief and must make the task extremely hard in one go;
#: attempts 2 and 3 repair what it broke or close what its screen showed it
#: missed. Never reset: a task that has not met the target by then is reported
#: with its measurements, not redesigned again. A designer call that failed to
#: return (transport, provider) spent nothing and is not counted.
MAX_HARDENING_ATTEMPTS = 3

#: The largest share of a task's objectives one trap's misreading may lose.
#: Measured (369 checks): what defeats frontier models is a plausible reading
#: that agrees with the right answer almost everywhere and diverges on a few
#: decisions. A "misreading" that fails most objectives is a wrong answer with
#: a trap's name on it, and proves nothing about that trap (review, 2026-09-26).
#: Read by the authoring self-audit (quality.difficulty_case_problems) and by
#: the executed controls (assurance.controls).
MISREADING_MAX_OBJECTIVE_SHARE = 0.5

#: Calibration scores and individual solver answers are never repair feedback.
#: Handing an author the answers its solvers gave is how a task gets tuned to
#: its own calibration run.
REPAIR_FEEDBACK_EXCLUDES = ("solver_answers", "per_episode_rewards")


# ---------------------------------------------------------------------------
# Reward hacking
# ---------------------------------------------------------------------------

#: Spec, "Calibration and results": "Inspect passing runs for reward hacking:
#: test access, fake output files, files dumped into graded directories, reused
#: caches, symlink tricks, and parser or exit-code exploits."
SPEC_PROBES = ("forged_state", "answer_lookup", "empty_deliverable",
               "surface_leverage", "seed_zero", "golden", "untidy_correct",
               "plausible_wrong", "destructive")

#: Local decision: probes with no exemption under any circumstance.
MANDATORY_PROBES = ("forged_state", "answer_lookup", "empty_deliverable")

#: Probes that model an ATTACK. Full credit on any of these is a confirmed
#: reward-hacking case and is what the spec's "0 confirmed or unresolved cases"
#: counts.
HACK_PROBES = ("forged_state", "answer_lookup", "empty_deliverable",
               "plausible_wrong", "destructive")

#: Probes that model LEGITIMATE work and are *supposed* to earn full credit.
#: `golden` is the reference solution and `untidy_correct` is a correct answer
#: formatted differently -- the spec requires that "traps should catch faulty
#: reasoning, not a correct answer that's simply written differently". Counting
#: these as exploits inverts their meaning; failing them is the defect.
EXPECT_FULL_CREDIT = ("golden", "untidy_correct")

#: The untouched fixture. Every objective must score zero and every guardrail
#: one, or an objective is passing on work nobody did.
EXPECT_ZERO = ("seed_zero",)

#: Diagnostic rather than pass/fail: it reports which documents move a scored
#: answer, which is read, not thresholded.
DIAGNOSTIC_PROBES = ("surface_leverage",)

#: Local decision: a probe scoring above this warns even when it fails outright.
#: A hack that earns most of the reward is still a hack.
PROBE_WARN_ABOVE = 0.5
PROBE_MAX = 1.0

#: Probes that DO the work and get one value wrong. Partial credit on them is the
#: shape the misreading rule requires -- a misreading may lose at most
#: MISREADING_MAX_OBJECTIVE_SHARE of the objectives, so a one-value-wrong answer
#: keeps at least half -- and is reported, never counted as a hack; full credit
#: on them still is (the grader cannot tell the wrong answer from the right one).
#: The work-free attacks keep PROBE_WARN_ABOVE: earning most of the reward
#: without doing the work IS a hack (envs-final-2, 2026-09-27: all eight tasks
#: scored 0.92-0.97 here and the batch counted each as unresolved).
PARTIAL_CREDIT_PROBES = ("plausible_wrong",)


# ---------------------------------------------------------------------------
# Selection
# ---------------------------------------------------------------------------

#: Local decision. Fitted to the first 500-session corpus and absolute rather
#: than recomputed per corpus, so a category means the same thing across dumps
#: and a richer dump correctly produces a larger category A. Re-derive only
#: deliberately: recomputing per corpus hides the improvement you want to see.
#:
#: These order *candidates* -- which trace to attempt first. They are an input
#: property of the trace and they are not what gets delivered. See below.
CATEGORY_BOUNDARIES = (0.53, 0.40, 0.28)
CATEGORIES = ("A", "B", "C", "D")
SOURCE_TIER_NAMES = {"A": "rich", "B": "strong", "C": "fixture-led", "D": "thin"}

#: User, 2026-09-26: a seed's build category IS the Arena faithfulness level it
#: can reach -- classified from the trace before authoring, in the spec's own
#: terms (F3 Replay / F2 Scenario / F1 Pattern / F0 Inspired). It is a TARGET:
#: the level measured from the built bundle (`ledger/levels.py`) stays the one
#: delivered. F0 targets remain eligible; measured Unrelated/F-1 cannot ship.
TARGET_LEVELS = ("F3", "F2", "F1", "F0")

#: Working-tree folder per target level. Distinct from DELIVERY_DIRS on purpose:
#: those name a MEASURED level, these the level a seed was selected to aim at.
TARGET_LEVEL_DIRS = {"F3": "target-F3-replay", "F2": "target-F2-scenario",
                     "F1": "target-F1-pattern", "F0": "target-F0-inspired"}

#: The retired A-D build categories, as the level each aimed at (the trap
#: policies then said: A F3; B, C and D F2). Read from ledgers and trees built
#: before 2026-09-26 only; nothing new is classified into a letter. Those trees
#: are filed under SOURCE_TIER_NAMES (rich/strong/fixture-led/thin).
LEGACY_CATEGORY_LEVEL = {"A": "F3", "B": "F2", "C": "F2", "D": "F2"}


def target_level(category: str | None) -> str | None:
    """A build category as its target level: F-levels as-is, legacy letters mapped."""
    if category in TARGET_LEVELS:
        return category
    return LEGACY_CATEGORY_LEVEL.get(category)


# ---------------------------------------------------------------------------
# Delivery layout
# ---------------------------------------------------------------------------

#: Delivered environments are filed under Arena's faithfulness levels, not under
#: our source tiers. The spec defines exactly one environment taxonomy --
#: F3 Replay / F2 Scenario / F1 Pattern / F0 Inspired -- and keys two batch
#: criteria and two of three yield metrics on it. `rich/strong/fixture-led/thin`
#: were ours, described the source trace rather than the delivered task, and
#: told Arena nothing it asked for.
#:
#: The folder is the faithfulness claim, so the batch's mix is legible from a
#: directory listing. Inspired/F0 ships; Unrelated/F-1 has no delivery folder.
DELIVERY_DIRS = {"F3": "F3-replay", "F2": "F2-scenario", "F1": "F1-pattern",
                 "F0": "F0-inspired"}

#: Source tiers still exist and are still recorded per task -- they say how much
#: material the author had to work with, which is what makes a low-fidelity
#: outcome forgivable or not. They are metadata, not a directory.
RECORD_SOURCE_TIER = True


# ---------------------------------------------------------------------------
# v2: minimal blockers, dense tasks, rules in the documents (user, 2026-10-02)
# ---------------------------------------------------------------------------
# User, 2026-10-02: "ensure there should be as minimal blockers ... blockers and
# repairs should only be for required checks", and "we have the flexibility of
# adding as many traps and checks as required ... the task should be very dense
# and also only giving visibility on what of task and not how".
#
# Required = validity and safety: the grader runs and derives every target, the
# reference scores 1 and an untouched workspace 0, no stored or leaked answer,
# no reward hack, every output field defined, referenced paths exist, no
# grading rule hidden from every agent-readable surface, step isolation,
# privacy, provenance honesty, Harbor format, attribution of failures.
# Everything else -- quotas, bands, weight shapes, construction plans, the
# difficulty self-audit's shape, trap counts, duplicate/dominance heuristics --
# is reported as an ADVISORY: shown to the designer, recorded with the bundle,
# printed in the screen report, never a blocker and never a repair trigger.
# `pipeline.advisory` holds the classification; a finding it does not name
# stays blocking, so an unknown finding fails safe.

#: Whether non-required findings are demoted to advisories. Read by
#: `pipeline.advisory.split`.
ADVISORY_FINDINGS = True

#: Objective count per band, per task, (low, high) inclusive. Widened from core
#: 4-6 / floor 0-2 / stretch 1-4 (max 12): a dense task carries many genuinely
#: fragile decisions, and pass@1 counts full success. Outside these limits is
#: an advisory, never a blocker (`author.quality.BAND_LIMITS` reads this).
BAND_LIMITS = {"core": (4, 24), "floor": (0, 4), "stretch": (1, 16)}

#: Authored scenario supplement limits (`author.scenario`). Raised from 32 KiB
#: per file / 128 KiB total so a dense, realistic document set (handbooks,
#: ledgers, threads, registers) fits. Privacy, provenance and the faithfulness
#: ledger still apply to every byte.
SCENARIO_MAX_FILE_BYTES = 256 * 1024
SCENARIO_MAX_TOTAL_BYTES = 2 * 1024 * 1024

#: Text formats an authored supplement may use. Realistic carriers of the
#: operative rules: email (.eml), calendars (.ics), logs, registers (.tsv),
#: markup exports (.html, .xml, .yaml).
SCENARIO_EXTENSIONS = (".md", ".txt", ".csv", ".json", ".tsv", ".eml", ".ics",
                       ".log", ".html", ".xml", ".yaml", ".yml", ".jsonl")

#: How `author.validate._hidden_rules` treats a filter's public rule.
#: "witness" (v2): the check must cite a verbatim rule sentence from its step's
#: instruction OR from a step-available fixture document, and every literal the
#: filter compares must be discoverable in agent-readable text; whether the
#: cited sentence also names the column and each literal together is an
#: advisory. "cooccurrence" is the v1 rule (column and every literal in one
#: quoted sentence), which pushed authors to restate document rules -- the HOW
#: -- in the instruction.
HIDDEN_RULE_MODE = "witness"

#: The difficulty doctrine the designer is held to (`author.levers`): at least
#: this many independent fragile decisions per calibration family, of at least
#: MIN_LEVER_MECHANISMS distinct mechanisms. A target for authors and an
#: advisory diagnostic; never a blocker.
MIN_FRAGILE_DECISIONS_PER_FAMILY = 10
MIN_LEVER_MECHANISMS = 5


# ---------------------------------------------------------------------------
# Training signal: conjunctive hardness, reward spread, trap diversity
# (Arena 261013 review + spec 10_12; design approved by the user 2026-10-13)
# ---------------------------------------------------------------------------
# Spec 10_12 added four requirements: vary the decisive trap across a batch;
# every inference resolvable from the materials; spread difficulty over checks
# that fail on their own, so partial progress earns partial reward; and reward
# spread -- the same model passes some runs and fails others, with partial
# scores, and neither shape "every run scores about the same" nor "one model
# passes everything while the other fails everything". Measured on the 37 tasks
# shipped before it (research/batch4/fb261013): 36 rested on one trap family
# (timestamp ordering), the median step had 72% free points, in 32 of 41 steps
# every failing check failed in exactly the same runs, and within-model reward
# SD was 0 in 29 of 41 Fable steps.
#
# What BLOCKS and what ADVISES (POLICY.md, "Training signal"):
#   blocks   a premise map that misstates the grader (dangling or non-objective
#            check ids, a check claimed by two premises, an unknown family, a
#            resolving quote absent from the materials) -- the screen, the cover
#            sheet and hardening all read it, so a false map is a validity
#            defect (`author.premises.problems`)
#   advises  premise count, premise share, free share, family distinctness, the
#            timestamp cap and the batch family quotas (`author.premises`,
#            `signal.batch_family_quotas`) -- design targets, shown to the
#            designer and printed by every screen
#   targets  the extreme pass@1 band and the spread metrics (`signal.measure`):
#            reported by every screen, and the ONLY thing that ends a hardening
#            lineage as target-met (`harden._target_met`). Never a release gate.

#: Whether any spread or diversity metric can reject or hold a task. Like
#: DIFFICULTY_GATES_RELEASE: named so the absence is greppable.
SIGNAL_GATES_RELEASE = False

#: User, 2026-10-13: EXTREMELY hard. Hardening's band: full-success rate at or
#: below this on BOTH models, on the task and on every step. Arena's general
#: target (CALIBRATION_TARGET_PASS_AT_1, 0.5) is unchanged and still reported;
#: this is the stricter band hardening aims at. No lower bound: a 0/10 task with
#: a real reward gradient is admissible, a 0/10 task carried by one premise no
#: run ever resolves is CONSTANT_PREMISE, not in band.
EXTREME_PASS_AT_1_MAX = 0.3

#: Preferred on the primary model: Arena's "hard" monitoring label (<= 2 of 10).
#: Reported (`signal` `hard_primary`), never required to end a lineage.
EXTREME_PRIMARY_PASS_AT_1_PREFERRED = SPEC_HARD_MAX

#: Reward spread per model per step: at least this many distinct step scores
#: over the valid runs. Measured: steps with one failure pattern averaged 1.3
#: distinct scores; with three or more, 4.7.
MIN_DISTINCT_SCORES_PER_MODEL = 3

#: Reward spread per model per step: population SD of the step scores. The
#: shipped linked-check shape measured 0.022; four independent premises missed
#: 30-45% of the time simulate at 0.13-0.16.
MIN_RUN_REWARD_SD = 0.08

#: Free share: objective weight no premise drives (designed, from the premise
#: map) or that no valid run of any model failed (observed, from the screen),
#: as a share of the step's objective weight. Shipped median: 0.72.
MAX_FREE_SHARE = 0.35

#: No single premise may carry more than this share of a step's objective
#: weight. Replaces the retired "root check plus cascade carrying >= 50%".
MAX_PREMISE_SHARE = 0.25

#: Independent premises per task: a single-step task carries at least
#: MIN_INDEPENDENT_PREMISES; a multi-turn task at least
#: MIN_PREMISES_PER_STEP_MULTI_TURN in EVERY step and
#: MIN_PREMISES_MULTI_TURN_TOTAL across the task. Independent = a different
#: family, a different item and its own checks.
MIN_INDEPENDENT_PREMISES = 4
MIN_PREMISES_PER_STEP_MULTI_TURN = 2
MIN_PREMISES_MULTI_TURN_TOTAL = 5

#: Timestamp ordering (clock offset, store/outage windows, impossible stamps,
#: outage-ordered letters) is ONE family; at most this many premises from it in
#: one task.
MAX_TIMESTAMP_PREMISES_PER_TASK = 1

#: Pairwise failure correlation (phi) between two premises above which they are
#: reported as linked: their failures move together and the gradient collapses
#: back to one step function. Advisory (five runs make phi noisy).
MAX_PREMISE_PHI = 0.3

#: Per-premise miss rate wanted on the model it targets, (low, high). Outside
#: it a premise is reported, never refused: below, it barely moves full success;
#: above, it is close to constant.
PREMISE_MISS_RATE_BAND = (0.2, 0.6)

#: Model sorting (spec 10_12 bad shape 2): one model at or above HIGH while the
#: other is at or below LOW, on the task or on any step.
MODEL_SORTING_HIGH_PASS_AT_1 = 0.8
MODEL_SORTING_LOW_PASS_AT_1 = 0.2

#: Shape verdicts of `signal.measure`, in precedence order (the first raised
#: flag names the shape; IN_BAND when none is raised).
SIGNAL_SHAPES = ("SORTING", "TOO_EASY", "CONSTANT_PREMISE", "FLAT", "IN_BAND")

#: Batch quotas (spec 10_12 rule 1), computed by `signal.batch_family_quotas`
#: and printed by every batch screen report; advisory. The decisive family of a
#: task is its most-failed premise when measured, else its heaviest.
MAX_FAMILY_HEAVIEST_SHARE = 0.20
MAX_FAMILY_PRESENCE_SHARE = 0.35
MIN_BATCH_FAMILIES = 6
MAX_TIMESTAMP_TASK_SHARE = 0.10

#: The trap-family taxonomy (research/batch4/fb261013/TRAP-CATALOGUE-NOTE.md):
#: the fifteen catalogue families, timestamp ordering as ONE family, and two
#: families kept only so a map can name them honestly (DISCOURAGED below).
TRAP_FAMILIES = {
    "repeated_wrong_figure": "a figure repeated by agreeing summaries vs the governing derivation",
    "changed_premise": "a changed premise silently invalidates results already worked out",
    "later_exclusion_aggregate": "a later exclusion reshapes the population behind an aggregate",
    "version_in_force": "the version in force at the as-of date",
    "near_twin_identity": "one entity under several names / near-twins kept apart by a key in the data",
    "governing_key": "the governing key vs the filing key",
    "house_number_convention": "a house convention vs default number or date handling (exact arithmetic)",
    "caption_only_rule": "a rule carried only by a caption or legend",
    "coverage_omission": "a coverage audit with a counting-unit boundary (omissions)",
    "scope_compliant_twins": "scope of change: compliant twins stay out",
    "answerability": "not determinable vs resolvable from the materials",
    "composition_tie": "composition wrong although the totals tie",
    "stacked_rules": "stacked rules / order-dependent allocation",
    "clean_baseline": "a clean 'before' baseline in a before/after comparison",
    "trigger_event": "a rule keyed on one event while records report another (defining sentence required)",
    "timestamp_ordering": "timestamp ordering: clock offset, store/outage windows, impossible stamps (ONE family)",
    "authority_delegation": "an authority or delegation conflict",
    "inferred_exclusion": "an exclusion inferred from a generic clause",
}

#: The timestamp-ordering family id (capped per task and per batch).
TIMESTAMP_FAMILY = "timestamp_ordering"

#: Families not to use as deciders: Arena called authority conflicts ambiguous
#: and Astra solved every batch-4 instance; inferred generic exclusions are the
#: second-reading shape that clarification killed seven times. Advisory.
DISCOURAGED_DECIDER_FAMILIES = ("authority_delegation", "inferred_exclusion")
