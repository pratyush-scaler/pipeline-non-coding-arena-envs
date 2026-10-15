# Acceptance policy

**Authoritative.** Where this file and any other document disagree about a
threshold, this one is right and the other is stale. Every number here is a
named constant in [`pipeline/policy.py`](policy.py) — prose does not hold
thresholds, because prose cannot be imported and drifts silently.

Revised against the Arena *RL Environments Quality Spec*, updated 2026-09-28.
Complete requirement/acceptance mapping: [SPECIFICATION.md](SPECIFICATION.md).
Pipeline simplified 2026-09-25 (user): presolve and the in-build difficulty
pilot removed; difficulty is authored in and measured once per batch.

---

## The five phases

```
1  select      traces -> target levels F3/F2/F1/F0, before authoring mechanical
2  author      full trace visibility -> complete, EXTREMELY hard   agent
               environment: genuine traps authored in on the first pass
3  grade       validity only: gates, probes, controls, naming,     mixed
               tasks-check, semantic review. Never a difficulty check
   -- barrier: the whole requested batch is authored and graded --
4  calibrate   SCREEN: 5 episodes x 2 models per task -> pass@1,   native
               pass@4, mean reward, attribution, hardening outlook
   -- the automatic pipeline STOPS here --
5  harden      MANUAL ONLY; every round ends in another 5 x 2 screen
   record      10 x 2 calibration of record, after a clean screen  native, manual
```

Authoring is told, at the top of both its system prompt and its opening
message, that the first pass is the only pass for difficulty, and it must
submit a **difficulty self-audit** (`quality.difficulty_case`): the hardest
decision, why a strong model will not get every answer right first time, and one
misreading per objective-driving trap, each encoded by a counterexample that
fails a check the trap drives. Mandatory downstream validation reports a missing
self-audit (`author/quality.difficulty_case_problems`); optional `check_draft`
provides the same local diagnostics, but cannot veto candidate submission.
The controls execute every
counterexample, so a dormant trap is caught before the build finishes. The bundle
gate does not require it, so bundles built before it are not re-blocked. It
checks completeness and linkage, never whether the task is actually hard -- the
screen measures that.

No phase asks whether a single task is hard before the batch exists. The
one-episode presolve that ended phase 2 fed "too easy" back into authoring one
task at a time; the designer is now told the first pass is the only pass for
difficulty (`author/agent_designer.FIRST_PASS_TRAPS`) and the batch is measured
together.

| stage | cost/task | decides |
|---|---:|---|
| static gates, probes, controls | ~$0 | grader defects, leaks, weight drift, dead checks |
| semantic review | ~$3 | incorrect graders, unsupported answers, unenforced rules, incoherent controls, hidden rules, ambiguity, privacy, duplication. **Never difficulty**: "too easy / recipe-driven / too little judgment" is a `difficulty_advisory` (user, 2026-09-26) -- recorded, shown in the screen report, read by hardening; the screen measures it |
| `harbor tasks-check` | ~$1 | malformed packages |
| **screen (5 x 2)** | **~$20** | **measured difficulty, attribution, hardening outlook -- reported, never a rejection** |
| calibration of record (10 x 2) | ~$39 | what ships; needs a clean screen, never a pass@1 |

### The screen and the calibration of record

| | screen | calibration of record |
|---|---|---|
| Episodes per model | `SCREEN_EPISODES_PER_MODEL` = 5 | `SPEC_EPISODES_PER_MODEL` = 10 (spec) |
| When | once per batch, after every task is built; after every hardening round | once the current screen measured cleanly |
| Target | pass@1 < `CALIBRATION_TARGET_PASS_AT_1` (0.5) on BOTH models | release bound below |
| Command | `arena build` (automatic), `arena screen` | `arena qualify` (manual) |

A screen is **shippable** (ready for the calibration of record) when both spec
models were measured on this exact task version with at least 5 valid episodes
each, at `high` effort with no limits, every failure is attributable (no
unattributed episode, contract share ≤ 30%, every all-fail check proved, no
unreachable check), and no trajectory shows unresolved reward hacking.
`release._qualify` refuses to start a ten-episode campaign otherwise
(`screen.shippable_problems`). **pass@1 is not part of it.**

### Difficulty is a strict target, never a blocker

pass@1 < `CALIBRATION_TARGET_PASS_AT_1` (0.5) on both models is the target
(user, 2026-09-25). Authoring aims at it; every screen and calibration reports
against it (`meets_target`, `target_gap`). Hardening also requires improvement
in capability-adjusted pass@1 and stops at the target only when both the official
and capability-adjusted rates meet it on both models. Nothing rejects or holds
a task for missing it: not the build, the screen,
`qualify`, or release (`DIFFICULTY_GATES_RELEASE = False`; `RELEASE_PASS_AT_1_MAX`
is reported only). Arena's own batch criterion -- ≥ 90% of tasks under 0.5 -- is
still computed and reported, honestly, by the batch report. Results
are not re-run: a screen of this version is reused, and only voids are topped
up.

### Training signal: the extreme band with a gradient (Arena 261013, spec 10_12)

User, 2026-10-13: tasks must be EXTREMELY hard **and** carry a training signal.
Spec 10_12 added four requirements -- a varied decisive trap across a batch,
every inference resolvable from the materials, difficulty spread over checks
that fail on their own, and reward spread (the same model passes some runs and
fails others, with partial scores; neither "every run alike" nor "one model
passes everything while the other fails everything"). The shipped batch before
it: 36 of 37 tasks on one trap family, median free share 0.72, linked failing
checks in 32 of 41 steps, within-model SD 0 in 29 of 41 Fable steps.

Every screen computes (`pipeline/training_signal.py`, from the campaigns' per-run check
states; voids excluded, `gated_out` not failed), per model and per step: full
passes and a 90% Wilson interval, distinct scores, reward SD, per-check fail
rates, per-premise fail rates and pairwise phi (when the authoring premise map
exists -- "premise map absent" otherwise), observed free share, constant
premises (checks, without a map) and model sorting, and classifies the shape:

| shape | raised when | constant |
|---|---|---|
| `SORTING` | one model ≥ 0.8 while the other ≤ 0.2, task or any step | `MODEL_SORTING_HIGH_PASS_AT_1`, `MODEL_SORTING_LOW_PASS_AT_1` |
| `TOO_EASY` | a model's full-success rate above 0.3, task or any step | `EXTREME_PASS_AT_1_MAX` |
| `CONSTANT_PREMISE` | a premise (an objective, without a map) no run of either model resolved | -- |
| `FLAT` | a model's step scores take < 3 values or SD < 0.08 | `MIN_DISTINCT_SCORES_PER_MODEL`, `MIN_RUN_REWARD_SD` |
| `IN_BAND` | none of the above (`SIGNAL_SHAPES` order decides the name) | `SIGNAL_SHAPES` |

Advisory flags, reported and fed to hardening: `FREE_HEAVY` (> `MAX_FREE_SHARE`
0.35), `PREMISES_LINKED` (phi > `MAX_PREMISE_PHI` 0.3), `CHECKS_LINKED`,
`DEAD_PREMISE`, `PREMISE_RATE_OUT_OF_BAND` (`PREMISE_MISS_RATE_BAND` 0.2-0.6 on
the targeted model), `NO_FULL_PASS`, `PRIMARY_NOT_HARD`
(`EXTREME_PRIMARY_PASS_AT_1_PREFERRED` = `SPEC_HARD_MAX` 0.2, preferred only),
`PREMISE_MAP_ABSENT`.

**What blocks, what advises, what is a target.**

| | rule | where |
|---|---|---|
| **blocks** (validity) | a premise map that misstates the grader: a check id that is not a declared objective, one check claimed by two premises (a compound criterion), an unknown family, a resolving quote absent from the instruction and the fixture | `author/premises.problems` via `author/validate` -- "premise map: ..." findings |
| advises | ≥ `MIN_INDEPENDENT_PREMISES` (4) premises in a single-step task; ≥ `MIN_PREMISES_PER_STEP_MULTI_TURN` (2) per step and ≥ `MIN_PREMISES_MULTI_TURN_TOTAL` (5) overall in a multi-turn task; no premise > `MAX_PREMISE_SHARE` (0.25) of a step; designed free share ≤ `MAX_FREE_SHARE` (0.35); one premise per family; ≤ `MAX_TIMESTAMP_PREMISES_PER_TASK` (1) timestamp premise; `DISCOURAGED_DECIDER_FAMILIES`; a missing map | "premise shape: ..." findings (`pipeline.advisory`) |
| advises (batch) | no family decisive in > `MAX_FAMILY_HEAVIEST_SHARE` (0.20) of tasks or present in > `MAX_FAMILY_PRESENCE_SHARE` (0.35); ≥ `MIN_BATCH_FAMILIES` (6) families; timestamp ordering in ≤ `MAX_TIMESTAMP_TASK_SHARE` (0.10) of tasks | `signal.batch_family_quotas`, every batch screen report |
| **target** | pass@1 ≤ `EXTREME_PASS_AT_1_MAX` on both models and every step, and spread ok (not `FLAT`, `SORTING` or `CONSTANT_PREMISE`) | `signal.measure` `target_met`; the only way a hardening lineage ends target-met (`harden._target_met`) |

Nothing here rejects or holds a task (`SIGNAL_GATES_RELEASE = False`), exactly
like pass@1 (`DIFFICULTY_GATES_RELEASE`). Arena's general target -- pass@1 < 0.5
on both models -- is unchanged, still `meets_target` in every screen, and still
what the batch report scores; the band and the spread are what authoring and
hardening aim at. Why the map blocks: the screen's per-premise rates, the cover
sheet's trap families and the hardening brief all read it, so a map that lies
corrupts every number built on it, and an unquotable premise is an inference
the materials do not settle (spec rule 2). A spec with no map raises one
advisory and validates as before; a screen of a bundle with no map reports
"premise map absent" and falls back to per-check evidence.

The designer's doctrine (`author/levers.CONJUNCTIVE_PROMPT`, leading the system
prompt; `harden.CONJUNCTIVE_HARDENING`, leading every HARDEN/TIGHTEN brief):
4-5 independent premises from different families, each on its own atomic exact
checks; one decision = one check (a downstream total or verdict is not graded as
another decision of the same premise -- the grader cannot read the agent's own
upstream answer inside a target, so such fields stay light and inside the
premise's share); additivity of misreadings; noticing traps settled by explicit
text; salience as the dial; no graded value in instruction examples. It retires
the "root check plus cascade carrying ≥ 50% of weight" rule
(`rulesets/PLAYBOOK_GENERAL.md`, eighth lever) and the routing rule that a new
trap must drive two objectives (`harden.MIN_CHECKS_PER_NEW_TRAP` is now 1).

The screen's **hardening outlook** (`strong-candidate` / `weak-candidate` /
`poor-candidate`, or `meets-target` / `not-assessable`) is a heuristic over the
screen -- live capability edges on each model above target, checks that never
failed and can be routed through a premise, unused trace corrections, and the
faithfulness budget. It is not validated against hardening outcomes and has no
power to reject anything.

---

## Task acceptance

| Requirement | Threshold | Source |
|---|---|---|
| Grader sanity | reference = 1.0, untouched = 0.0 | spec |
| Solvability | the **reference trajectory** scores 1.0 | spec |
| Difficulty | target pass@1 < 0.5 on both models -- reported, **never blocks** | spec (a target) + user 2026-09-25 |
| Valid episodes | ≥ 10 per model, **after** voids excluded | spec |
| Attribution | 100% of failures classified; zero `defect`, zero `unattributed` | spec |
| Contract failures | ≤ 30% of valid episodes | local |
| Dead / unreachable checks | 0 | local |
| Graded checks | ≥ `MIN_OBJECTIVES` (8) objectives per task, each failed by an executed counterexample | local (user, 2026-09-25) |
| Misreadings | every objective-driving trap has its OWN counterexample (no shared answer), executed: fails only what the trap drives, passes ≥ 1 objective, loses ≤ `MISREADING_MAX_OBJECTIVE_SHARE` (50%); the semantic reviewer checks it encodes the stated reading | local (review, 2026-09-26) |
| Reward hacking | 0 attack probes at full credit | spec |
| Contract consistency | 0 findings: a list the instruction orders is graded in order, a list graded without order is declared unordered, a repeat or an omission loses credit, a guardrail tests restraint (a wrong value never trips it), a later step is defined by the rules not by "your step-1 answer", a quoted literal has one spelling -- static (`validate` T3b-T6) and executed on mutated reference answers (`grader.contract_probe`) | Arena feedback 2026-09-27 |
| Static | `harbor tasks-check` passes | spec |
| Faithfulness | F0–F3; Inspired/F0 allowed with goal/capability grounding; Unrelated/F-1 rejected | spec updated 2026-09-28 |
| Naming | `a_f<level>_<task-name>`, level agreeing with the ledger | local |
| Weights | objective weights sum to 100 in every task -- an identical grader total | local |
| Reference solution | a **script that derives** the answer, not a stored one | spec |

### Two gates that were removed

Both closed the funnel at opposite ends. In `envs-cat-v2`, 468 candidates were
classified, 86 attempted and **nothing shipped**.

**Blind-solve solvability.** `release.py` required one of three blind model
episodes to score 1.0 on every step *before* difficulty was measured — pass@3 =
1.0 as an admission requirement. The harder a task was, the less likely it
survived its own solvability gate. All 12 tasks that reached calibration
measured 0.93–1.00 mean reward, because the gate had removed everything else.
The spec asks far less: *"At least one calibration run **or reference
trajectory** scores 1.0."*

**Band composition.** Release required 4–6 objectives at 30–70% per model and at
most two below 30%. A genuinely hard task has *most* checks below 30% by
construction, so the rule forbade the thing the programme exists to produce.
Bands survive as diagnosis (`arena analyse`) with no release power.

`policy.BLIND_SOLVE_GATES_RELEASE` and `policy.BANDS_GATE_RELEASE` are both
`False` — named, so their absence is greppable rather than implied.

---

## Failure attribution

> *"Check failed runs to confirm the cause is model capability, not ambiguous
> instructions or an environment or grader bug."* — spec

With the blind-solve gate gone, an all-fail task is admissible. This is what
carries the burden instead.

| verdict | meaning | counts as |
|---|---|---|
| `capability` | clean run, well-formed output, wrong on a decision | a model failure — the kind we want |
| `contract` | clean run, deliverable missing or malformed | adjudicated, capped at 30% of episodes |
| `void` | container error, stall, turn cap, truncation | **nothing** — leaves every denominator, re-run |
| `unattributed` | unclassified | always blocks |

**Every check no episode passed must earn it.** A hard task has many; each needs

1. an executed **source counterfactual** — perturb the source, the old answer
   fails and an independently recomputed answer passes
2. an **independently phrased correct alternative** that passes, with a graded
   value that differs from the reference's wherever a correct answer can be
   written differently (text; a list whose order the check may ignore). A
   boolean, a null or a number at its published precision has one spelling:
   there the executed alternative must pass it AND a blind genuineness
   adjudication bound to the task version must be on file
   (`verification/all-fail-adjudication.json`; `attribution._rephrasable`)
3. **reachability** — attempted in at least one episode
4. no outstanding **near-miss** adjudication (≥80% overlap scoring zero)

All four → a capability wall, ships. Any missing → suspected defect, blocks.

---

## Batch acceptance

All six from the spec. Computed by `arena deliverable`, which refuses a batch
that fails rather than letting Arena discover it.

| Criterion | Threshold |
|---|---|
| Reviewable | 100%: `tasks-check` pass, calibration runs, provenance |
| Task quality | ≥90% meet grader sanity, solvability and pass@1 < **0.5** |
| Reward hacking | 0 confirmed or unresolved |
| Faithfulness mix | no F-1; F0 allowed; aim at ≥50% F1+ and ≥15% F2+ |
| Trace accounting | 100% dispositioned |
| Multi-turn | ≥10% of environments |

Difficulty never blocks an individual task (above). The batch report still
computes Arena's Task-quality share -- ≥90% under the spec's **0.5** -- and
reports it as met or not, so a batch that misses Arena's criterion says so
rather than letting Arena discover it.

### Yield

Denominator is **every session Arena shared, unfiltered** — not the ones we
chose to attempt.

| Metric | Definition |
|---|---|
| Environment yield | sessions producing ≥1 environment, any level |
| Difficulty yield | sessions producing ≥1 accepted env with a hard task at F1+ |
| Hard-task yield | sessions producing ≥1 accepted env with a hard task at F2+ |

---

## Faithfulness (F0–F3)

Arena's taxonomy, and the **only** environment taxonomy the spec defines. The
delivery folder *is* the level, so a batch's mix is legible from a directory
listing.

| Level | Source | Delivered to | Assigned when |
|---|---|---|---|
| F3 | Replay | `F3-replay/` | fidelity ≥ 90% **and** ≥70% of traps cite a real correction |
| F2 | Scenario | `F2-scenario/` | verified goal/capability/scenario/failure/grading trace alignment; reconstruction allowed |
| F1 | Pattern | `F1-pattern/` | synthetic world, failure mode preserved **and** calibration reproduces it |
| F0 | Inspired | `F0-inspired/` | verified concrete source goal and capability exercised by synthetic task |
| F-1 | Unrelated | — | no qualifying recoverable grounding; **rejected** |

**Build categories are target levels** (user, 2026-09-26). Before authoring,
every trace is classified into the level it can reach, on the same two signals
and absolute boundaries the retired A–D categories used (`select/categories.py`):

| Target | Source signal | Retired category |
|---|---|---|
| F3 Replay | liftable fixture (readiness ≥ 0.64) **and** ≥ 2 corrections | A |
| F2 Scenario | ≥ 2 corrections, **or** a liftable fixture (readiness ≥ 0.52) | B, C |
| F1 Pattern | thin fixture, exactly 1 correction (a recoverable pattern) | D (part) |
| F0 Inspired | thin fixture, no correction | D (part) |

No target level blocks authoring: an F0-target seed is still built, and the table
above (measured) decides delivery. Trap policy and designer guidance are keyed by
target level. Source tiers 1–4 still order candidates internally.

New drafts require `quality.capability_plan`: source-supported authority/time,
artifact repair, semantic collisions, coupled decisions or revision cascades,
linked to existing decisions, executable shortcut answers and source controls.
Scenario-writing tools retain grounding, path and source-immutability safeguards;
mechanism outlines and full decision/control links are checked in mandatory
post-submission validation, not as pre-mutation or submission permission.
No mechanism count certifies difficulty; the native screen measures it.
New author sessions and manual hardness redesigns require capability-plan version 2: an acyclic
decision-dependency graph, four separately intervenable core judgments, a public
evidence-backed joint-applicability collision, whole-answer decoy invariance,
cross-decision coupling and competent retrieval/computation baselines. Complete
baseline `submission` outputs execute across all steps; their `fails` list must
match the observed semantic failures exactly and may be empty. Honest success is
a difficulty advisory, not a validity defect. Legacy linked wrong-answer baselines
remain auditable, but may not omit applicable public rules to manufacture failure.
The controller binds the minimum construction version to the source/seed and
retains it across stalls and repairs. Legacy version-1 validity repairs remain
permitted. Version-2 source interventions execute every semantic check and verify
their exact change scope, not merely a claimed subset of failures. Independent
review checks the semantic meaning of every matrix and procedure.
These are stricter local construction requirements, not new specification
acceptance thresholds or proof of model incapability. `optimal_subset` grades
bounded, source-derived shared allocations, accepting all optimal ties; it is
one planning decision regardless of how many constraints or totals are reported.
`quality.trace_alignment` cites actual user turns; fresh ledgers verify quotations
and independent review verifies their semantic relationship to the task.
When no fixture survives, `initialize_scenario` can create a disclosed synthetic
context from a verified source request. It earns zero recovered-source credit,
cannot overwrite recovered files and is re-verified against the source trace.
New F2/F1/F0 fixtures may be synthetic without a recovered-byte quota; bounded
scenario size, disclosure, privacy and validity controls still apply. F3 retains
its conservative floors. `rule_sources` can witness public rules in accessible
fixture documents without repeating a solution recipe in the assignment.
Solver autonomy keeps task-specific solution coaching private, not acceptance
criteria or source evidence. The public brief defines the professional goal,
deliverables, field meanings and edge cases; all normative rules remain accessible
at the relevant step. Private instructional-hint diagnostics are advisory only.
Independent review checks every solver-visible surface for relocated walkthroughs
and distinguishes difficulty hints from actual answer/private-grader leakage.
The user additionally requires unscaffolded-task acceptance: every new independent
review must return a cited, per-surface `solver_autonomy` assessment covering the
controller's hash-bound visibility inventory exactly. Missing, stale or incomplete
review evidence is unverified; unresolved task-specific solution coaching prevents
acceptance and enters existing repair rounds. This is a design constraint, not a
new definition of model incapability or an empirical difficulty prediction. Required
rules, real source procedures and generic environment help remain public. Regex
flags alone never reject or rewrite a task. Native tools, evidence access, attempt
budgets and deterministic task grading remain unchanged; frozen campaigns stay pinned.

The capability difficulty diagnostic treats contract failures as successes and
excludes voids, so missing/malformed submissions cannot establish a semantic
capability gap. It also drives hardening progress and target-stop decisions.
Official pass@1 and release/batch acceptance criteria remain unchanged.

`F1`/`F2`/`F3` previously also named pipeline *stages* in this codebase. They no
longer do; anything reading them as faithfulness comes through
`ledger/levels.py`.

---

## Repair

One budget, one invariant. Policy was previously one design attempt and a repair
budget of zero, so a correct review finding was terminal: **47 of 86 candidates
were discarded holding findings that named the exact file and the exact line.**

| Rule | Value |
|---|---|
| Passes per candidate | 2 (`policy.MAX_REPAIR_PASSES`, and `orchestrate.GATE_REPAIRS` reads it) |
| Monotone | the finding set must strictly shrink **within a grading stage** (draft validation / gate chain / semantic review): later stages run only after earlier checks pass, so newly exposed findings are not measured against an earlier stage's count. A finding that returns from any earlier pass is terminal; the shared pass allowance never increases |
| Repeated finding | terminal — the author cannot see what the reviewer sees |
| Citation required | a finding must name a file, check or step |
| Never fed back | solver answers, per-episode rewards |

`ARENA_GATE_REPAIRS=0` restores one-shot authoring for a run that wants it. The
default was 0 until 2026-09-23, which discarded 47 of 86 candidates. Repair in
the build is validity repair only (gate, control and review findings);
difficulty is never a build-time repair finding.

A candidate the governor stops keeps its findings in
`verification/repair-disposition.json`. It is a disposition with evidence, not a
silent discard — `gated_out` is not `failed`.

Validator defects are not task defects. Lexically similar categories with a
matching predicate of opposite polarity require independent semantic review,
not a forced rewrite merely to reduce word overlap. After fixing a validator,
`arena build --revalidate-blocked REASON` explicitly rechecks the unchanged
blocked artifact. It archives the previous verification receipts, verifies the
submitted design and workspace, and preserves the shared repair ledger and
remaining allowance. It grants no acceptance and is never a first-pass success.

---

## Hardening

Manual only, and bounded so it cannot become a loop of redesigning the same
task (user, 2026-09-25).

| Rule | Value |
|---|---|
| Redesign attempts per task | `MAX_HARDENING_ATTEMPTS` = 3, over the whole lineage (original + every revision), across invocations, never reset |
| What counts | every designer call that returns a revision -- validity repairs included. A call that returned nothing (transport, provider) spends nothing |
| Attempt 1 | the full brief, told it is the one attempt that must make the task extremely hard; nothing held back |
| Later attempts | REPAIR an invalid revision (fix the cited findings only), or TIGHTEN a valid, screened one still short of the target -- the brief carries its training-signal shape and what that shape needs (add an independent premise, re-tune a constant one, split linked checks); never push one premise toward 0/10 |
| After each valid revision | a 5 x 2 screen and a comparison with the version it revised |
| Ends when | a screen meets the target -- every step ≤ `STEP_PASS_RATE_MAX`, any bound lineage goal, AND the training-signal target (pass@1 ≤ `EXTREME_PASS_AT_1_MAX` on both models and every step, no `FLAT`, `SORTING` or `CONSTANT_PREMISE`; re-derived from the screen's campaign reports, an unreadable signal never meets it); the budget is spent; a validity finding repeats or the finding set does not shrink; a screened revision moved pass@1 on neither model **measured on both sides** and cleared no training-signal flag (a parent with no measurement is "not comparable" and ends nothing); the designer rejects the source |
| Never ends on | a screen that did not measure cleanly (voids, unattributable failures, an unresolved hack flag) -- the lineage stays open on that revision |
| Resuming | `arena harden <vN> --apply`, or `arena harden <original> --apply`, which continues from the latest valid revision whose screen measured cleanly (and refuses while that revision is unmeasured) instead of restarting the redesign |
| A stalled design | its unfinished draft is kept (`verification/hardening-draft.json`) and the next REPAIR continues from it |
| Record | `<original>/hardened/hardening.json`; revisions are siblings `<original>/hardened/vN` |

An ended lineage is refused by `arena harden` and reported with its
measurements. The original task is never written to.

---

## Top-up

Infrastructure loss is re-run; results are not.

| | |
|---|---|
| Budget | 5 extra episodes per task per model |
| Replaces | `void` only — container error, stall, truncation, adapter stall |
| Never replaces | `capability`, `contract`, `pass` |
| Receipt | `verification/topup-<model>.json` (screen: `screen-topup-<model>.json`), recording what it spent |
| Spent | summed from each top-up campaign's own `report.json` (`summary.requested`); an unreadable one counts as the whole budget |

A screen campaign retained from an earlier run that verified but is still
short of valid episodes is **continued**, never relaunched: its scored episodes
stand and only the missing ones are requested, within what is left of the same
budget. Once that budget is spent the campaign is kept short (and the screen is
not shippable); `arena screen --relaunch-incomplete` replaces it with a fresh
campaign -- which re-runs scored episodes, so it is an operator decision and the
receipt names every campaign discarded (`relaunched_incomplete`,
`discarded_campaigns`). A screen in that state says so (`topup_exhausted`,
`remedy`, first in `shippable_problems`); harden prints the flagged command, and
category_batch parks the task as `screen-needs-operator` instead of retrying it
on every restart.

Every scored episode of the original campaign is kept. A retry runs only as
many new episodes as are still missing, never more than the budget left, and
its valid episodes are merged with the retained ones (`topups` in
`native-calibrations.json`). A retry fires only when voids are the sole
problem, and `policy.topup_problems()` refuses one that lost a recorded outcome
or grew the scored outcomes by more than it launched. Re-running a *scored* episode until the number improves would make
every difficulty figure a lower bound on how many times we tried.

This matches the retained cost model: "10 attempts plus 5 reruns per model",
measured at $39.52 per task. The screen uses the same void-only top-up, with its
own receipt (`verification/screen-topup-<model>.json`).

---

## Why a threshold here must have a reader

Four mechanisms in one session were built, documented, unit-tested — and read by
nothing. Each passed its own tests while doing nothing in production:

| mechanism | was inert because |
|---|---|
| `presolve` (since removed) | no build path called it |
| `MAX_REPAIR_PASSES` | `orchestrate` read its own env var, defaulting to 0 |
| `calibration_problems()` | nothing called it, so retired models were never refused |
| `MAX_UNREACHABLE_CHECKS` | `attribution` inlined the bound as `> 0` |

`pipeline/tests/test_spec_acceptance.py::EveryPolicyConstantIsRead` fails the
build if a public constant in `policy.py` has no reader outside it. A constant
proves nothing about behaviour until a call site consults it, and a unit test
that exercises a module in isolation will happily confirm an unwired mechanism
works perfectly.

---

## Commands

```bash
./arena build -n 1 -o envs-fresh     # phases 1-4: author, grade, screen the batch, stop
./arena build -n 1 --no-calibrate    # phases 1-3 only; no solver episodes
./arena screen envs-fresh            # phase 4 alone (--report-only reprints the table)
./arena tasks-check <tree>           # harbor's validator, spec-required
./arena qualify <bundle> ...         # 10 x 2 calibration of record -- after a clean screen
./arena analyse <bundle>             # attribution, dead and unreachable checks
./arena release <bundle>             # the only acceptance decision
./arena deliver envs-fresh -o batch  # file into F-level folders, a_f<n>_ names
./arena deliverable batch --sessions all-sessions.json    # the batch report
./arena harden <bundle> [--apply]    # MANUAL -- each round ends in a 5 x 2 screen
```

### Two trees

The working tree is filed by **target level**, which is known before authoring
starts. The delivery tree is filed by **measured faithfulness**, which is only
knowable afterwards.

```
working    envs-fresh/target-F3-replay/a-001-wordpress-site-audit
delivery   F2-scenario/a_f2_wordpress-site-audit
```

A build cannot create the delivery folder directly — it has to name the
directory before it has a ledger to measure, and a bundle filed as `F3-replay/`
that then measures F2 would be a directory lying about its contents. `arena
deliver` does the filing once the evidence exists, and is also where colliding
names are disambiguated: `a-002-brand-consulting` and `a-003-brand-consulting`
both reduce to `a_f2_brand-consulting`, and two tasks cannot share a Harbor
package name.

---

## Calibration models

| | model | routing | harness (user, 2026-09-26) |
|---|---|---|---|
| Primary | **Fable 5.1** | `anthropic/claude-fable-5-1` | **Claude Code** 2.1.283 |
| Secondary | **GPT 6 Astra** | `openai/gpt-6-astra` | **Codex** 0.157.1 |

**The harness is part of the measurement**, like effort: a pass@1 is "Fable 5.1
in Claude Code at high". Protocol `arena-harbor-harness/4-step-history`
(`policy.CALIBRATION_HARNESS`, `HARNESS_VERSIONS`, `HARNESS_API_HOSTS`):

- Both CLIs run **inside** the task container, pinned and baked into the agent
  image (with Node 22 from a digest-pinned image), so Harbor never installs
  anything at trial time.
- The **agent phase only** may reach the model's own API host
  (`api.anthropic.com` / `api.openai.com`), enforced by Harbor's egress-control
  sidecar. Setup and the separate verifiers stay offline. An allowlist is
  refused, never widened, where egress control is unavailable (Docker Desktop's
  LinuxKit kernel lacks `CONFIG_NFT_FIB_INET`; the Linux Coder pool is where
  calibration runs).
- Each step is a fresh harness session over the persisted workspace, as before.
- A harness step with no ATIF transcript is **void**, never a zero. The
  reward-hacking scan reads harness file tools (Read/Write/Edit, `apply_patch`)
  and argv-list commands as the shell commands they are equivalent to.
- Terminus-2 campaigns (protocol 3) are not comparable and no longer certify
  release. A documented substitute model runs in its provider's harness.

**Reasoning effort: `high`, on both.** Effort is part of the measurement, not a
runtime detail — a pass@1 is "Fable 5.1 at high", not "Fable 5.1", and a figure
taken at another effort is not comparable. `release.py` already refuses to mix
efforts across a task's two campaigns. Note the direction of the risk: higher
effort makes capable models act *more*, and the restraint guardrails are exactly
the checks that catch over-acting, so effort moves guardrail rates too.

**No turn cap and no campaign deadline.** A run stopped on `step_cap` or
`max_tokens` wrote no deliverable and is recorded VOID — it measured nothing.
Measured on a008: all ten rollouts stopped on `max_tokens` with an empty
deliverables directory and were recorded as ten model failures at mean 0.00.
That is a void wearing a result's clothes. A cap destroys data rather than
measuring difficulty, and in the direction that makes a task look *harder* than
it is. The provider's own limits and the transport read timeout remain the real
bound; fault detection is unaffected.

`gpt-5.6-sol` and `claude-opus-5` are **retired from calibration**
(`policy.RETIRED_CALIBRATION_MODELS`); `policy.calibration_problems()` refuses a
campaign aimed at either. They were argparse defaults in six places, which is
how a batch gets measured on a model nobody chose.

---

## What this policy cannot do

- It cannot certify a task is *good*. These are admissibility bounds.
- `contract.completeness` is lexical; it blocks only at zero overlap.
- `answer.derivation` lower-bounds leakage — it cannot decide whether the
  *mapping* is stored.
- `env.policy_consistency` has never fired against a real defect.
- `grader.contract_probe` only *warns* on a section that asks for work no field
  records and on a claim that two sources agree. Both need a reader: the
  semantic review must settle them, and a green chain does not mean it did.
- Ten episodes is a qualification minimum, not a precise estimate. Difficulty
  bands are observed rates.
- A model critic is not a domain expert.
- **"Flawless" is not something this chain can certify.** Every bundle declares
  `untested_surfaces`, and the chain reports `unverified` rather than green
  whenever it could not actually check something. `SKIPPED` and `ERROR` are
  never green.
