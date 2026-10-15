"""Stage F2b -- design an environment as a bounded agent instead of one shot.

The one-shot designer in `designer.py` is handed a brief: the first fourteen
lines of each fixture document, the corrections, and the constraints. Measured
on kw-a005 that brief carried 7,229 of the fixture's 28,896 characters -- the
model designed a reconciliation across ten documents having seen a quarter of
them. Nearly every defect this batch produced traces back to that blindness:

    a004  chose a parser that yields no rows for its document
    a005  wrote four answers as hand-typed literal lists
    a007  made 69% of the weight a single-surface read-off
    5 bundles  shipped pairs of checks resolving to the same answer

Every one of those is knowable before emitting a spec, and none of them was
knowable from the brief. So this designer gets tools instead of a summary: it
reads whole documents, reads the trace the task is lifted from, runs parsers to
see real rows, EVALUATES its own target expressions to see the answers they
compute, and runs the whole validator suite against a draft -- all before
committing. What it cannot do is invent an answer, because the emission is the
same `SPEC_TOOL` schema with nowhere to type one.

Two boundaries are load-bearing.

**The agent under test never sees any of this.** These tools read the authoring
side; the task's own workspace is `environment/files/` alone. The designer
seeing the trace is not a leak -- the designer is on our side of the fence --
but anything it copies into the instruction or fixture is, which is what
`leak.sweep` and `answer.derivation` exist to catch afterwards.

**The bundle's own answer stays out of reach.** `authoring/extraction/after/`
holds a later candidate repair, not proof of user acceptance; `solution/` holds the reference answer of
any previous design, and `tests/derived/` holds computed projections. A designer
that reads those can write a task it has already been told the answer to. File
access is therefore restricted to the fixture root, checked by resolved path.
Authored supplements use a separate bounded writer, which cannot overwrite any
recovered document and records zero source credit with a public disclosure.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Callable

from . import oracle
from .checks import Workspace, evaluate
from .designer import (MODEL, SPEC_TOOL, _call, derive_solution, verify_solution)
from .validate import (MAX_GATED_WEIGHT_SHARE, MAX_SINGLE_WEIGHT_SHARE,
                       MIN_OBJECTIVES, validate)
from .outcomes import AuthoringStalled, SeedRejected
from ..config import ARENA_EFFORT, MIN_TRAPS
from ..policy import (CALIBRATION_TARGET_PASS_AT_1, FAITHFULNESS_TRACE_DERIVED_FLOOR,
                      MISREADING_MAX_OBJECTIVE_SHARE, SCREEN_EPISODES_PER_MODEL,
                      SPEC_HARD_MAX, WEIGHT_TOTAL)
from .quality import MIN_PITFALLS_CONSIDERED
from .capability import CAPABILITY_PROMPT
from .adversarial import PROMPT as ADVERSARIAL_PROMPT
from .challenge import (PROMPT as CHALLENGE_PROMPT, TOOL as CHALLENGE_TOOL,
                        construction_diagnostics, plan_challenge, stretch_check_outlines)
from .portfolio import TOOL as PORTFOLIO_TOOL, plan_portfolio
from ..privacy import redact_excerpt

TRAP_GUIDANCE = (
    "Mark every trap's provenance truthfully: trace_derived only with the user's verbatim "
    "correction, otherwise authored with the fixture file it is grounded in and the "
    "plausible professional mistake it tempts. Make the correct resolution possible from "
    "public evidence and rules. Do not invent hidden policies, ambiguous answer "
    "conventions or unrelated distractions. Disclose authored source additions, retain "
    "their zero recovered-source credit and respect category fidelity limits. Demonstrate "
    "each trap with a substantive wrong-answer probe and a valid solution.")

CONSTRUCTION_INTEGRITY = (
    "PROOF-FIRST CONSTRUCTION AND REPAIR: preserve the actual user's professional "
    "goal and capability, not just its vocabulary. Do not turn software development "
    "into an unrelated reconciliation audit. Cite witnesses that semantically support "
    "the engagement and report the faithfulness level actually supported. Publish all "
    "rules, operands, exceptions, scope and authority precedence needed to solve it. "
    "For each counterexample, apply its ONE named mistaken policy consistently to "
    "every record and both steps; recompute all causal descendants while preserving "
    "unrelated outputs. For each source intervention, independently derive the changed "
    "answer from the changed evidence and audit the complete declared divergence set. "
    "Execute complete honest retrieval and computation baselines with every applicable "
    "public rule; a successful baseline is valid and may have fails: []. Strengthen "
    "genuine semantic discrimination and coupled decisions, never cripple the method "
    "or invent a failure. During repair, address EVERY reported defect with a finite "
    "rule/artifact/executed-check checklist. Change defective task content or controls, "
    "not merely their labels, disclaimers or claims. Local checks do not prove semantic "
    "validity or frontier-model incapability; only independent review and native "
    "measurement can establish those separately.")

#: The first words of every authoring conversation (user, 2026-09-25/26). The
#: user turn is what a model weighs most, and it used to open with floors and
#: budgets and say nothing about quality or difficulty. Both are required.
AUTHORING_MANDATE = (
    "YOUR MANDATE: on this first attempt, design a task that is BOTH of EXCELLENT "
    "QUALITY and EXTREMELY HARD. Quality means it meets every requirement of Arena's "
    "RL Environments Quality Spec (the ARENA QUALITY BAR in your instructions): clear "
    "and complete requirements, grounded in this trace's domain and situation, a "
    "deterministic grader that grades only stated requirements and cannot be read or "
    "gamed, a reference solution that scores full marks and an untouched workspace "
    "that scores zero. Hard means the strict target of pass@1 below "
    f"{CALIBRATION_TARGET_PASS_AT_1} on BOTH calibration models -- aim for "
    f"{SPEC_HARD_MAX} or lower. Neither substitutes for the other: a task that is hard "
    "only because it is unclear or unfair is broken, and a flawless task a frontier "
    "model solves misses the goal. Do not count on anything making this task harder "
    "after you submit: validity findings may come back for repair, but difficulty "
    "feedback will not, and later hardening is manual, limited and not guaranteed. "
    "V4 LEADS (user, 2026-10-13; Arena 261013 review, spec 10_12): follow the V4 CONJUNCTIVE "
    "DOCTRINE at the very top of your instructions -- 4-5 INDEPENDENT premises from different "
    "trap families, each on its own atomic exact checks, each missed in some careful runs and "
    "not in all, no premise above its share cap, free weight capped, at most one timestamp-ordering "
    "premise, every premise settled by an explicit quotable sentence -- and record "
    "quality.premise_map. Hard now means full success rare AND a reward gradient: the same model "
    "passes some runs and fails others, with partial scores. Where the V2.1/V3 text below "
    "conflicts with V4, V4 wins. "
    "V2.1 TARGET (user, 2026-10-02): BOTH models should genuinely fail MOST episodes. "
    "Wave 1 measured that NOTICING traps never bite (0 failures in 1,220 lever-episodes): "
    "follow the V2.1 DIFFICULTY DOCTRINE at the top of your instructions. Every fragile "
    "decision rides route b, c, d or e, passes the admission test -- the executed idiomatic "
    "baseline (counterexample baseline_...) gets a graded member wrong, and the trap member "
    "carries no label -- and is backed by discriminating data. Rules are stated once, never "
    "naming their decoys, never in a hub file with the others, with applicability evidence "
    "in a different document. The instruction and its field definitions state WHAT, never "
    "HOW. Every trap stays genuine: one defensible answer, executed counterexample, field "
    "definitions pinned for every case. Build every genuine trap this source "
    "supports into the reasoning itself, keep every rule published and every check "
    "failable, passable and reachable, record quality.premise_map and quality.fragility_budget and complete the difficulty self-audit "
    "(quality.difficulty_case) before you submit. Think deeply first: run the TRAP HUNT in your instructions across all "
    "sixteen pitfall families and the doctrine's lever catalogue against these documents, plant every genuine pitfall that "
    "survives, and red-team your own draft before submitting. Difficulty hypotheses "
    "and local check results do not veto submission. Record limitations honestly; "
    "never invent baseline failures to meet a quota. Reject only when the source "
    "cannot support a fair substantive task, not merely because hardness is unmeasured.")

#: The mandate for a session that REVISES an existing draft -- a gate or review
#: repair, or a hardening attempt -- instead of designing it. The first-pass
#: mandate ("build every genuine trap", "no difficulty feedback") contradicted a
#: REPAIR brief that says "do not add traps" and a TIGHTEN brief that carries
#: real measured rates; and a reject_seed during a repair ends the lineage.
REVISION_MANDATE = (
    "YOUR MANDATE FOR THIS SESSION: revise the staged draft exactly as the brief above "
    "directs -- the brief governs this session wherever it is more specific than your "
    "general instructions. Keep the task at EXCELLENT QUALITY (every line of the ARENA "
    "QUALITY BAR) and keep every genuine trap it already has. Add or change traps only as "
    "the brief allows. Measured pass rates in the brief are real measurements of the "
    "previous version; use them. Complete quality.difficulty_case for the revised draft. "
    "Call reject_seed only if the source cannot support the task at all -- never because a "
    "repair is difficult.")

#: What traps each TARGET LEVEL may use, keyed like `designer.CATEGORY_GUIDANCE`.
#: A seed is classified into the faithfulness level it can reach before
#: authoring (`select/categories.py`, user 2026-09-26); the level itself is
#: measured after the build (`ledger/levels.py`). User, 2026-09-25: an F3-bound
#: task's traps align to the trace; below F3 any trap type relevant to the
#: environment is allowed.
TRAP_POLICY = {
    "F3": ("TRAPS FOR THIS TASK -- target level F3 Replay: FROM THE TRACE FIRST, THEN "
           "MORE THAT ALIGN WITH IT.\n"
           "  1. Turn every usable user correction into a trap, cited with the user's verbatim "
           "words: the premise the user changed, the document the user said governs, the item "
           "the user said was retired but survived. These are the replay; leave none unused.\n"
           "  2. Then PLANT ADDITIONAL traps wherever the recovered documents and the trace's "
           "scenario genuinely support another pitfall of the kind this user was fighting: the "
           "same documents, the same role, the same class of mistake -- a second figure revised "
           "later in the same pack, a further superseded version, another item that looks in "
           "scope and is not, another conflict the published precedence rule settles. Mark them "
           "authored and ground each in the fixture file it lives in. Never invent a dispute, a "
           "document or a rule the scenario does not contain.\n"
           f"  3. F3 arithmetic: at least {FAITHFULNESS_TRACE_DERIVED_FLOOR['F3']:.0%} of all traps "
           "must cite a real correction, so for every 7 trace-derived traps you may add up to 3 "
           "authored ones; beyond that the task measures F2. Prefer authored traps built on "
           "surfaces the recovered documents already contain -- supplement bytes dilute the 90% "
           "fixture fidelity F3 also needs.\n"
           "  4. Provenance is never stretched to reach F3. Label a trap trace_derived only when "
           "the cited user words genuinely establish THAT pitfall. If this trace has too few "
           "corrections for the traps the task needs, the task measures F2 -- an acceptable, honest "
           "outcome; a mislabelled trap is a quality defect."),
    "F2": ("TRAPS FOR THIS TASK -- target level F2 Scenario: TRACE CORRECTIONS FIRST, THEN "
           "INVENT FREELY INSIDE THE SCENARIO.\n"
           "  1. Where the user pushed back, those corrections are the strongest material: turn "
           "them into traps first (your brief states how many distinct corrections you must cite).\n"
           "  2. Then invent as many further traps as the recovered or reconstructed documents "
           "genuinely support -- any pitfall relevant to this environment and aligned to this "
           "task, from the trap-hunt families in the system prompt. Mark them authored and ground "
           "each in the fixture file it lives in; never attribute an invented trap to the user.\n"
           "  3. Plant traps in the documents' own content -- a revision, a conflict, a residue, "
           "an exception whose conditions fail. Do not manufacture an argument between people "
           "the trace does not contain.\n"
           "  4. Cite quality.trace_alignment for the source scenario, failure mode and "
           "grading criteria. F2 permits reconstructed fixtures and authored traps; neither "
           "a fixture byte ratio nor a trap percentage proves this semantic alignment."),
    "F1": ("TRAPS FOR THIS TASK -- target level F1 Pattern: A SYNTHETIC WORLD THAT REPRODUCES "
           "THE TRACE'S FAILURE MODE.\n"
           "  1. Too little of the workspace survived to rebuild the scenario, so you author the "
           "fixture and may invent traps freely: any pitfall relevant to this domain and aligned "
           "to this task, written into documents that belong to the situation the trace "
           "describes (same role, same artefacts, same conventions).\n"
           "  2. The trace's recoverable correction pattern is what makes this F1: at least one "
           "trap must reproduce the mistake the user corrected, and calibration must show models "
           "failing that same way. Cite the correction it comes from.\n"
           "  3. Where the source supports it, preserve the scenario and grading criteria "
           "as well, with verified trace_alignment witnesses; that supports an F2 claim."),
    "F0": ("TRAPS FOR THIS TASK -- target level F0 Inspired: NOTHING RECOVERABLE BEYOND THE "
           "SITUATION; BUILD TOWARD F1 OR ABOVE.\n"
           "  1. Neither the workspace nor a user correction survived, so you author the whole "
           "fixture and invent traps freely: any pitfall relevant to this domain and aligned to "
           "this task, inside the situation the trace describes (same domain, same role, same "
           "artefacts, same conventions).\n"
           "  2. Arena accepts F0 with exact source goal and capability witnesses; preserve everything the trace does "
           "offer: reproduce any failure the trace's model actually made (that is F1's claim, "
           "confirmed by calibration), and ground every document in the trace's scenario (that "
           "is F2's). The level is measured from what the built task preserves.\n"
           "  3. Never pass an invented trap off as the user's: mark every trap authored and ground "
           "it in the fixture file it lives in."),
}

#: Tool calls one design may make before it must emit. Generous, because the
#: work is reading -- a ten-document fixture costs ten reads before any thinking
#: -- and cheap, because every call but the last is local computation.
#: Tool calls the designer may spend before it must emit. Reading a large
#: fixture properly costs more than sixty: kw-a010's fixture is 885,761
#: characters across 25 files, and a designer that runs out of budget mid-read
#: emits against a partial picture -- which is the failure the one-shot
#: designer was retired for.
#: v2 (2026-10-02): dense tasks author long documents (handbooks, threads,
#: registers) and many checks; 140 turns ended designs mid-construction.
MAX_STEPS = 220
#: v2: exploratory evaluate() calls fail often while a designer learns the
#: expression language; six in a row stalled a-009 after 27 turns.
MAX_CONSECUTIVE_TOOL_ERRORS = 12
MAX_OUTPUT_TOKENS = 128_000
TRUNCATION_FEEDBACK = "The response was truncated; no tools from it were executed. Stage smaller sections with stage_spec, validate with check_draft, then submit_draft without repeating the full spec."

#: v2 (2026-10-02): the expression language at a glance, appended to evaluate()
#: errors. Two designs stalled after guessing signatures from bare KeyErrors
#: ("KeyError: 'of'") and probing for operation names.
EXPRESSION_REFERENCE = """EXPRESSION REFERENCE (targets are evaluated over projections):
rows {file, where?}   field {file, path}   text {file}   exists {file}   literal {value, why}
count {of}   sum {of, field}   min|max {of, fields?}   pluck {of, field}   select {of, fields:{alias:path}}
filter {of, where}   bind_rows {of, fields:{name: scalar-expr}}   derive_rows {of, fields:{name: row-expr}}
latest {of, by:[fields], order_by, value_type: datetime|number|string}   set|unique {of}
difference|intersection {a, b}   add|subtract|multiply|divide {a, b}   record {fields:{k: expr}}
round {of, places, mode: half_up|half_even}  (exact fractions; use for money)
scalar: only {of}  extract {of, pattern, group?}  number {of}  range_bound {of, bound: lower|upper}
        parse_date {of, format?, year?}  date_add {date, days}  days_between {start, end}
        compare {a, b, value_type: number|date|string, comparison: eq|ne|lt|lte|gt|gte, mode?: exact}
row-expr (inside derive_rows): field {path}  literal {value, why}  if {where, then, else}
        add|subtract|multiply|divide {a, b}  round  and the scalar operations
where: {field, eq|ne|in|not_in|gt|gte|lt|lte|matches|present: value} or {all:[...]} / {any:[...]}
projections: {as, file, parser} | {as, op: join, left, right, on: key or [keys], fields:{alias: "left.f"|"right.f"}}
             | {as, op: concat, sources:{projection: label}, field}
There is no median/mean/group-by op: derive per-row values, then count/sum/divide."""

SYSTEM = """\
You design non-coding professional knowledge-work benchmark environments from \
real agent-session material, and you VERIFY your design before emitting it.

{first_pass}

HOW HARD, EXACTLY. The strict target is pass@1 below {target} on BOTH \
calibration models. Aim well past it -- EXTREMELY CHALLENGING, NOT UNPASSABLE: a \
frontier model working carefully should complete the whole task at most 2 times \
in 10 (pass@1 <= {hard}, what Arena calls hard), and should fail the rest \
of the time because the REASONING defeated it, never because it could not tell \
what was being asked.

The bar that keeps that honest: an expert practitioner given ONLY the published \
evidence must be able to get every answer right. If they could not, the task is \
broken, not hard. Publish every convention; hide nothing; then make the \
thinking hard.

MEASURED ACROSS THE FIRST 32 TASKS THIS PIPELINE BUILT, three runs: the \
operators used were `pluck` 492, `filter` 436, `only` 314, `extract` 288 -- a \
RETRIEVAL pipeline, find the rows matching a predicate -- while `date_add`, \
`days_between` and `parse_date` existed, were reviewed, and were used ZERO \
times on a corpus whose richest fixtures are renovation schedules, ordering \
deadlines, lead times and installation milestones. Eight freshly authored tasks \
were then solved PERFECTLY by a frontier model on a single cold attempt. The \
current corpus derives far more (`derive_rows` 431, `days_between` 87, \
`date_add` 46 across 18 tasks) and tasks from it have still screened at pass@1 \
1.00 on both models: derivation is necessary and not sufficient, and retrieval \
still dominates (`field` 2866, `filter` 684, `pluck` 492).

If your target expressions are mostly pluck/filter/extract you have written a \
search query and called it a task, and the model will run your search \
flawlessly. DERIVE something: a date from a milestone minus a lead time, a \
quantity from a rate and a duration, a threshold crossing, a value that \
depends on another value you also had to derive.

WORKED EXAMPLE, same fixture, easy versus hard. A renovation ordering tracker: \
items with lead times, consolidation shipments, installation milestones, and a \
banner saying the scope was expanded after the document was written.
  EASY (what was actually built, scored 1.00): list the distinct headings in \
  each document and count occurrences. Every answer is READ OFF the page.
  HARD: give each item's recomputed order deadline. The solver must notice the \
  stated deadlines predate the scope expansion the document itself flags, so \
  they are stale and must not be copied; derive each deadline from the \
  milestone it serves minus production lead minus shipping window; recognise \
  that items sharing a shipment are COUPLED, so a batch orders by its earliest \
  member and assigning an item changes other items' answers; and report the \
  items whose recomputed deadline falls before the re-measurement the new \
  scope requires, because those cannot be ordered in time and the correct \
  answer says so rather than inventing a date.
  Same documents, nothing hidden. The difference is that the hard answer is \
  COMPUTED THROUGH A CHAIN where an early mistake propagates and cannot be \
  recovered by reading more carefully.

Do not buy difficulty with volume: more documents, more output fields, more \
rows or more UNRELATED decoys (a near-miss decoy is a different thing; see MAKE \
THE TRAPS CONFUSING). The easy version already had nine trap types including unsatisfiable, \
forbidden_edit and scope_creep_bait; they did not help, because the traps sat \
BESIDE an answer that was read off rather than INSIDE the reasoning that \
produced it. Put the trap where the computation happens.

You have tools. Use them; do not design from assumption. In particular:

- `list_evidence` searches ALL recovered channels and versions; `read_evidence`
  reads them with continuation offsets and `view_evidence_image` shows retained
  uploads/assets. Read the ordinary user requests, answered clarifications,
  cited page chunks, delivery records and relevant earlier versions. File counts
  and extensions do not establish scope or usefulness. Keep the deliverable
  non-coding; do not turn a coding request into an invented audit just to admit it.
- `stage_evidence` explicitly copies selected, inspected evidence into the
  fixture with provenance. Later/undone/unanchored evidence cannot be staged.
  A delivery is not acceptance; a revision is not a verified correction; shell
  output and fetched chunks may be partial. Assistant claims are context, not
  authority. Private reasoning bodies are unavailable. More versions do not
  establish difficulty; require a substantive source-dependent decision.

- `read_fixture` every document you intend to project. Not the head of it -- the \
whole thing. A task that reconciles documents you have skimmed is a task built \
on a guess.
- `read_trace` and `list_corrections` to see what the user actually disputed. \
The transcript shows the user's per-turn FEEDBACK on every response (approve, \
edit, disapprove, escape) and every tool call's input and output: a response \
the user edited or disapproved is where the model failed, so read those first; \
`list_corrections` lists them with what the user said next. `read_signals` \
adds Arena's outcome signals -- a steerability failure is a correction the \
model did not apply -- to point you at more failures to read. \
The corrections are the failure modes a real professional hit: a trap derived \
from one is the strongest evidence of faithfulness, and for a task aiming at F3 \
they come first. Below F3, genuine invented traps are equally welcome.
- `run_parser` before declaring any projection. A parser that does not fit its \
document yields no rows and the spec is refused.
- `evaluate` EVERY target expression you write, and read what comes back. This \
is the single most valuable tool here. It tells you whether your answer is \
empty, whether it is the whole population, whether it is full of nulls, whether \
two checks resolve to the same set, and whether the question is worth asking. \
A designer who evaluates cannot ship a degenerate answer by accident.
- `check_spec` on a complete draft. It runs the full validator suite and \
returns concrete problems. Fix and re-check until it returns clean, THEN emit.
- `write_scenario` may add explicitly hypothetical case data grounded in \
recovered public documents. It cannot edit those documents. Use it only when \
applying their rules to an authored case serves the original professional \
scenario; never add an answer key or contradict source facts to force difficulty. \
Additions receive zero source-fidelity credit and must fit the category floor. \
The public supplement notice distinguishes them from recovered evidence.

WHAT MAKES A TASK GOOD HERE

THE PROFESSIONAL CONCLUSION IS DERIVED, NEVER STORED. First identify the \
decision a practitioner must make and the evidence needed to make it. Then \
design its verifier. Applying conditions, resolving evidence or revising a plan \
can require reasoning; joins, intersections and arithmetic do not establish \
difficulty by themselves. Required source facts may receive limited floor \
credit, but copying them cannot supply the substantive core decisions. Use \
`evaluate` to check what each expression actually measures.

NEVER HAND-TYPE AN ANSWER. Scalar literals can express published parameters or \
output labels within a source-derived decision. A fixed sentinel is not a core \
conclusion, and a list of privately selected answers is refused. If a result \
depends on whether evidence is present, derive that condition from the relevant \
evidence; do not always emit a missing-data label. Cite the source rule for each \
condition and test a coherent case in which the conclusion changes.

LOAD AT LEAST TWO AXES: inference (can it work the answer out), execution (can \
it carry a dependent chain), restraint (can it avoid touching what it \
shouldn't). Restraint must protect something the professional assignment \
actually requires. State every restraint in the public assignment; whether it \
discriminates between model capabilities remains an empirical question.

There is no total-check or guardrail-count quota. Do not add copied registers,
repeated correct conclusions or invented prohibitions merely to create guards.
Ordinary answer accuracy is positive work, even when labelled preservation.
Protect real negative obligations with actual enforcement; retained historical
submissions do not by themselves protect the live copies in a solver workspace.

GRADED UNCERTAINTY WHEN RELEVANT. If the professional decision depends on \
missing or conflicting evidence, check the affected scope and justified \
conclusion. Publish the reporting convention and accept equivalent valid \
answers. Do not invent an unanswerable subquestion just to require abstention, \
or use a fixed token as a substitute for evaluating the decision.

DESIGN DISTINCT DECISIONS. A join, intersection, count or long output is not \
evidence of difficulty. Several intermediates of one reconciliation remain one \
professional decision; splitting them cannot satisfy the distinct-core budget. \
Simple source reads may earn the limited floor credit when the deliverable needs \
them. Core and stretch labels are hypotheses until fresh per-model measurement \
confirms them. Test plausible wrong decisions, not just malformed answers. If \
these sources cannot support substantive work, use reject_seed rather than \
relabeling routine extraction or adding volume.

STATE THE COUNTING CONVENTION for any set of headings or sections: which \
depths count, whether the document's own title counts, and whether a heading is \
recorded as its text or as written with its markup. Leaving it out is how a \
correct answer scores zero -- four checks in one bundle scored 0 across ten \
rollouts on submissions that were the reference answer differing only by a \
markdown '#'.

WEIGHTS ARE RELATIVE WITHIN A STEP. The build gives every graded step an equal \
share of 100 points (the task reward is the mean of the step rewards) and \
rescales each step's objectives to its share; reward.toml documents each \
check's true task share. Guardrails carry 0: they zero the score on violation \
rather than earning any of it.

THE INSTRUCTION STATES THE ASSIGNMENT, NOT THE ANALYSIS. Be exact about WHAT \
and silent about HOW. The instruction gives the business goal in the \
requester's words, the deliverable path and schema, what every field MEANS and \
its exact format, and the output convention for edge cases (what to report when \
a value cannot be determined). It does NOT:
  - name fixture files beyond pointing at the workspace, unless the requester \
would naturally name one (the pack they were handed, the register they own);
  - say or hint that any document is revised, stale, superseded, conflicting, \
duplicated or retired, or that two sources disagree;
  - restate a precedence rule, threshold or rate that a fixture document \
already states;
  - list steps, joins, checks, cross-references or things to watch for;
  - name a trap family or describe a misreading.
It MUST keep every sentence that decides a field's SCOPE, an EXCLUSION, a \
BOUNDARY or an EDGE-CASE CONVENTION -- which items a field counts, what a value \
means when a condition holds, what is in the requester's remit. That is the \
field's MEANING, not the analysis: removing it does not harden the task, it \
makes a second reading defensible, and the review reverses the drop (measured \
on hardened a-055 and a-047, 2026-09-28: single-model pass@1 drops with every \
failing episode on the same alternative reading).
Write it the way a colleague hands work over, not as a specification of the \
analysis. A trap the instruction alerts the solver to is a dead trap: in the \
last batch the reviewer found every planted trap neutralised by numbered rules \
in the instruction, and instructions ran 16,000 to 29,000 characters, three to \
twelve times their schema. Write the length of a real handover.

RULES LIVE IN THE WORLD. A professional finds the governing rules in the \
organisation's documents, not in the request. Leave every precedence rule, \
threshold, exception and scope definition in the fixture document where it \
naturally lives -- a contract clause, a policy memo, a rate sheet's notes, a \
defined-terms section -- and point the instruction at the workspace generally. \
A rule stated there as a criterion is PUBLISHED (RESOLVABLE above). Apply it in \
the grader from the document: bind the threshold or rate with `bind_rows` and \
`compare`, choose the governing revision with `latest`, so the instruction never \
restates it. Only if the recovered documents lack a rule the task needs, add it \
with `write_scenario`, grounded in a verbatim quote from a recovered file and \
labelled synthetic (supplements dilute F3 fidelity). A filter's public rule may \
be witnessed by `rule_sources` with an exact fixture file and quote available \
at this step, or by `rule_quote` from the STEP INSTRUCTION. State it as a \
criterion in the domain's terms, never as a column test, and prefer deriving \
the condition from a document-bound value so there is nothing to restate.

THE INSTRUCTION IS THE CONTRACT, checked mechanically on every draft:
  - DEFINE EVERY FIELD BY MEANING AND FORMAT. Each field a step's output schema \
requires is named in that step's own instruction, in backticks, followed by \
what the value IS in the domain and its exact format: units, decimal places, \
date format, order or "any order", and the null convention (v2.1: the \
rounding MODE and STAGE belong to the policy document that states them) \
("`slip_days` -- the calendar days the handover ran past its committed date, an \
integer, 0 when on time"). Never how to compute it, which document to read, or \
which rule decides it. A list of key names defines nothing. A schema `enum` is \
a closed vocabulary: define each value by its meaning; where two could apply, a \
published rule in the instruction or a fixture document decides, and the \
instruction does not say which wins.
  - REFERENCE ONLY WHAT EXISTS. Every backticked file name or path must be a \
fixture file or a declared deliverable; every command must be installed in the \
agent image. Inputs live in /app/environment/files (read-only) and deliverables \
in /app/deliverables/<file>; the build states both in each step's contract.
  - NO HIDDEN RULES (v2 witness rule). Any check whose target filters rows \
(`where`) or tests a regex cites where its rule is PUBLISHED: `rule_sources`: \
[{file,quote}] copied verbatim from the fixture document that states it (the \
normal case -- rules live in the documents), or `rule_quote` from its step's \
instruction. Every value a clause tests must be findable in the files or the \
instruction. The quoted sentence need NOT repeat the column name or every \
value: a policy saying "lines marked MEMO in the ledger legend are not \
postings" witnesses a filter on code `MEMO`. Never restate a document's rule in \
the instruction to satisfy this -- a rule placed in the instruction is coded \
literally and the trap dies. If a document words a fixture token differently, \
you may declare it in `rule_terms`. `extract` patterns only PARSE values and \
need no witness.
  - ORDER IS A RULE TOO. Compare an array with `equals` only if the instruction \
states its order. If order does not matter, say so, mark the array \
`"unordered": true` in the schema, and compare it with multiset_equals / \
set_equals (or list a nested path in `unordered_paths`).

Do not enumerate affected records or private grading objectives in the instruction. \
Publish deliverable filenames and schemas; avoid navigation coordinates and \
answer-revealing source locations. State rules, and let the fixture carry the rest."""

#: The first pass is the only pass for difficulty (user, 2026-09-25): no draft
#: is screened for difficulty on its own. Thresholds interpolated from policy
#: so the text cannot drift from what is enforced and measured.
FIRST_PASS_TRAPS = f"""
THE FIRST PASS IS THE ONLY PASS: ONE ATTEMPT, TWO NON-NEGOTIABLE REQUIREMENTS.
THIS IS YOUR ONE CHANCE.

This draft must be BOTH:
  1. EXCELLENT QUALITY -- it meets every requirement of Arena's quality spec
     (the ARENA QUALITY BAR below): clear, grounded, deterministic, fairly
     graded, leak-free, and fully solvable by an expert from the workspace alone.
  2. EXTREMELY HARD -- a frontier model working carefully fails it most of the
     time, because the REASONING defeats it.
Neither substitutes for the other. A hard task that breaks the quality bar is a
broken task: its failures are not the model's, it teaches nothing, and it is
rejected. A high-quality task that a frontier model solves misses the goal.
Difficulty must come from genuine reasoning demands -- never from ambiguity,
hidden rules, missing information, busy work or grader quirks.

ARENA QUALITY BAR -- what Arena's RL Environments Quality Spec requires of every
environment and task. Meet every line; the gates, executed controls and an
independent reviewer check them:
  ENVIRONMENT
  - Self-contained and reproducible: every input the task needs is in the
    workspace; nothing depends on live internet, Arena, or anything outside it.
    The starting files never contain the completed solution or any answer.
  - Instructions live inside the environment, and a later step is reached only
    after the earlier one is completed and graded: step 2 never leaks into step 1.
  - The agent writes only its declared deliverables; nothing it does can write
    to the grader or leave stray files that affect grading.
  TASKS
  - Clear requirements: define the objective, the inputs, every output path, the
    schema, what every field MEANS, error handling and edge cases; every path and
    command you reference exists. A field's meaning is what the value IS in the
    domain ("plugins whose assets the rendered page actually loads"), never how
    to compute it ("rows of index.csv where contexte = script_src"). Working out
    the procedure is the task.
  - Hidden checks may test unseen cases of STATED requirements only; any special
    handling that affects grading is explained in the instruction.
  - Grounded: the task stays in the source session's domain and situation; tools
    or cases you add serve that situation. Invented data is labelled synthetic
    (write_scenario does this for supplements).
  - Tasks a strong current model finds genuinely hard -- not busy work.
  GRADER
  - Verifiable and deterministic; never an LLM judge. Each turn has its own rubric.
  - Grades only stated requirements, and is readable for review: documented
    checks, recomputed answer keys, point totals that sum to {WEIGHT_TOTAL}.
  - The agent cannot access or infer the grading logic or the expected answers
    by any route the system allows -- no answer in the fixture, the instruction
    or the file names.
  ACCEPTANCE
  - Grader sanity: the reference solution scores full marks and an untouched
    workspace scores zero, on every step.
  - Solvability: the reference trajectory scores 1.0, derived by a script from
    the fixture -- never a stored answer.
  - General difficulty: pass@1 below {CALIBRATION_TARGET_PASS_AT_1} on both
    calibration models; "hard" is at most {SPEC_HARD_MAX} on the primary.
  - Reward hacking: zero. No shortcut earns credit without doing the work.
  - Faithfulness: as much of the trace preserved as the target level allows -- F2
    or F3 wherever possible; F0 requires a concrete source goal and capability,
    while F-1 is forbidden. Vary failure modes and delivery patterns across the
    batch. A graded second step (multi-turn) where
    the scenario genuinely supports one.

Nothing screens this draft for difficulty after you submit it: no cold solve and
no difficulty feedback. The task is checked for QUALITY (gates, probes, controls,
independent review) -- quality findings may come back to you for repair -- and
then calibrated together with the rest of its batch -- {SCREEN_EPISODES_PER_MODEL}
episodes on each of two frontier models -- against the strict target of pass@1
below {CALIBRATION_TARGET_PASS_AT_1} on BOTH. A task that comes out easy is reported as
easy; any later hardening is manual, limited to a few attempts and not
guaranteed. Design as if this is the only chance to make it hard. So make it EXTREMELY hard now, at full quality. Build in every genuine trap the
source supports, of the kinds your target level allows (stated in your brief), before
you write a single output field. Do not submit a draft you expect a strong model
to solve; submit only once you can name, for every trap, the wrong reading a
careful frontier model would plausibly adopt.

WHAT DEFEATS A FRONTIER MODEL, measured over 369 calibrated checks (both models,
at least four episodes each):
  - SIZE ALONE DID NOT. Large enumerations, many documents and long derivations
    were ground out correctly in those measurements. Additional coherent
    candidates or evidence may introduce genuine constraints; arbitrary padding
    or extra output fields do not. This is not a guarantee about newer models.
  - A PREMISE THAT CHANGES does: a threshold, scope or definition revised after a
    first result is computed, so items already judged must be judged again.
  - A GOVERNING CONFLICT does: two documents disagree and the published rule says
    the less obvious one governs.
  - A RESIDUE does: something declared retired or done is still present in the
    very document that declares it done.
  - The traps that bit hardest were a PLAUSIBLE MISREADING -- two related
    concepts merged into one -- that agrees with the correct answer on almost
    every item and diverges on a very few, flipping an item the model already
    judged through an attribute it has no reason to re-read. A trap that changes
    something visible (a number, a range, list membership) was usually caught.
  - Same-type traps are correlated: a model that sees the principle once applies
    it everywhere. Vary the trap types.
  - Keep each trap's affected population small (every measured killer sat
    between 9 and 130 rows): no mechanical grind to hide behind.
  - ADDING ONE TRAP TO AN EASY TASK DOES NOT: the first direct test added a
    governing conflict to a task at pass@1 0.88 and moved it to 0.80 on one
    model and not at all on the other. A trap beside read-off answers is
    noticed and handled; a trap inside a chain that several answers depend on
    is the shape that failed -- and that chain is also why every failing check
    then failed in the same runs, flattening the reward (Arena 261013). V4
    composes several INDEPENDENT premises instead of one chain.
  - IMPLICIT INVALIDATION does (the STALE benchmark's "implicit conflict"): a
    later fact overturns an earlier conclusion without negating it, and the
    conclusions that depended on it must be re-judged. Models patch the one
    visibly affected item and miss the cascade.
  - NEAR-MISS DECOYS cost the model; unrelated filler does not. The wrong
    document that is nearly right -- one revision older, a sibling entity's
    policy -- is the decoy that worked.
EACH PREMISE ON ITS OWN CHECKS (V4, 2026-10-13; this replaces "make each premise
bear on several decisions", which made every failing check fail in the same runs).
pass@1 counts only FULL success, so lower it by adding INDEPENDENT premises --
different family, item and document, each graded by its own atomic exact
check(s) -- never by routing several checks through one premise, and never by
splitting one calculation into several checks to multiply its weight.
Grade the published semantics, including legitimate equivalents, rounding and
tolerances. Extra exactness is not a semantic trap.

THE TRAP HUNT -- think deeply, BEFORE you write a single check.
Most drafts fail here: they plant the first pitfall they notice. Search this
scenario exhaustively for every place a careful professional -- or a strong model
reading quickly -- would go wrong, then plant the best ones. Work through every
family below against THESE documents, and record what you find in
quality.difficulty_case.pitfalls_considered:
  1. REVISED PREMISE: a threshold, scope, rate or definition changed later in the
     same pack, so items already judged must be judged again.
  2. GOVERNING CONFLICT: two sources disagree and the published precedence rule
     makes the less obvious one govern (the fuller, newer-looking or official-
     looking record is the decoy).
  3. RESIDUE: something declared removed, retired or done is still present.
  4. MERGED CONCEPTS: two related fields or terms that agree on most rows and
     differ on a few -- gross/net, billed/paid, scheduled/actual, created/
     modified, calendar/business days, cap/requirement -- and, sharpest of all,
     a real professional convention a competent generalist merges and only an
     expert separates: retention versus payable, accrual versus cash, practical
     completion versus handover, gross floor area versus net lettable.
  5. EXCEPTION THAT DOES NOT APPLY: a rule with an exception whose conditions
     look met and fail for a few items.
  6. BOUNDARY: inclusive vs exclusive ends, "within N days", fiscal vs calendar
     year, week start, time-zone date rollover.
  7. UNIT OR SCALE: thousands vs units, per-unit vs total, percent vs percentage
     points, a currency or measure that changes mid-pack.
  8. ENTITY IDENTITY: near-duplicate names or IDs, a renamed entity, one entity
     listed twice, two entities sharing a name.
  9. COUPLING: items that share a batch, dependency or budget, so fixing one
     changes another's answer.
 10. STALE DERIVED VALUE: a total, subtotal or status the document computed
     before a change -- it must be recomputed, not copied.
 11. SCOPE BAIT: an item whose label says in scope and whose published criterion
     says it is not.
 12. UNSATISFIABLE ASK: something requested that the evidence cannot produce; the
     correct answer says so instead of inventing it.
 13. RESTRAINT: an adjacent thing the assignment says to leave alone that a
     helpful model will be tempted to fix.
 14. NEAR-MISS DECOY: a record or document that is nearly right -- the prior
     revision of the same document, a sibling entity's policy, the same defined
     term in a different scope, a superseded rate sheet -- differing on the one
     attribute the decision turns on. Unrelated filler is not a decoy.
 15. IMPLICIT INVALIDATION: a later fact overturns an earlier conclusion without
     naming it (a memo changes a definition, not the list of affected items),
     and that conclusion feeds other decisions that must be re-judged.
 16. VOCABULARY VARIANCE: the request, the governing rule and the data name one
     concept differently, linked by a definition published in the fixture (a
     defined-terms clause, a glossary), never by a private convention.
For each candidate, ask: is it genuinely supported by THIS scenario (never a
contrivance)? Does a published rule settle it? Would a strong model plausibly
adopt the wrong reading -- ideally one that agrees with the right answer on most
items? Does the wrong reading change a graded answer (EVALUATE it)? Plant the
ones that pass, and keep them INDEPENDENT (V4): different items, different
documents, different checks, so a run that misses one premise loses exactly that
premise's weight. Reject the rest, with the reason. Then red-team your own draft: answer it the way a
strong model would on a first quick pass; if that answer earns full marks on any
step, the task is not done.
Record each candidate's family in pitfalls_considered.family. A trap's `type`
is the nearest of the nine schema types: near-miss decoy -> plausible_decoy;
revised premise, governing conflict, implicit invalidation and residue ->
stale_authority; merged concepts, vocabulary variance, entity identity and
scope bait -> misleading_label; coupling -> regression_bait; unsatisfiable ask
-> unsatisfiable; restraint -> forbidden_edit or scope_creep_bait; boundary,
unit or scale and stale derived value -> derived_answer.

MAKE THE TRAPS CONFUSING, NEVER UNFAIR. Every trap is a reading a competent
generalist adopts and an expert rejects from the published evidence alone:
  NEAR-MISS DECOYS. Every wrong candidate is nearly right: the prior revision of
    the same document, a sibling entity's policy, the same defined term in a
    different scope, a superseded rate sheet, the parent entity's record. Plant
    every near-miss the scenario genuinely supports -- each one LIVE (evaluate
    the decoy's answer and confirm it diverges from the target on a few items),
    each with its own misreading and its own counterexample. Unrelated filler is
    never a decoy: it costs the model nothing and dilutes fidelity. At F3 a
    decoy must already be among the recovered documents (90% fixture fidelity);
    below F3 write it with write_scenario, grounded in a verbatim quote from a
    recovered file.
  THE DECISIVE QUALIFIER SITS WHERE A PROFESSIONAL LOOKS AND A SKIMMER DOES NOT:
    a footnote, a revision note, an exception clause, a rate sheet's notes, a
    definition several pages from the item it governs. Documents are dense in
    MEANING, not in rows.
  VOCABULARY VARIANCE. The request, the governing rule and the data may each
    name one concept differently, as real organisations do, linked by a
    definition published in the fixture -- never by a private convention, and
    never by rule_terms alone.
  EXPERT-ONLY ERRORS. Build merged-concept traps on real professional
    conventions where the generalist reading is wrong and only an expert
    notices; the misreading you record is the generalist's.
  INDEPENDENCE AND MIX (V4; replaces "put two pitfalls on the same items" and
    "a trap whose counterexample fails checks in two distinct decisions"). Each
    premise on its own item and its own checks; two premises' counterexamples
    never fail the same check. One premise per family; a model that sees a
    principle once applies it everywhere.
  SMALL POPULATIONS. Each misreading diverges on a small share of the items its
    checks span and agrees with the correct answer on the rest.
  INVALIDATE IMPLICITLY. The strongest new fact overturns an earlier conclusion
    without naming it -- a later memo changes a definition; it does not list
    which items are now out of scope -- so patching the one visibly affected
    item is still wrong. Use this for step 2, and inside step 1 when a later
    document in the pack revises a premise that earlier-judged items depend on.
    Grade the re-judged items as THAT premise's own check(s); do not add
    downstream totals or verdicts that merely restate them (V4: no cascade).
  LONG MEANS DEEP, NOT BIG. Solvers script any enumeration and thinking models
    sustain long mechanical chains; extra rows, documents, pages and steps add
    cost and timeouts, not difficulty. Make the task long in DEPENDENCY: each
    link a judgment whose error propagates into the next.
  FULL-SUCCESS ARITHMETIC. pass@1 counts only complete success. Put every
    substantive decision under a genuine, resolvable challenge. Independent
    premises (different family, item, document, own checks) measured nearly
    multiplicative (+0.05 over the product of per-premise pass rates, 13
    pools); several fields downstream of one premise are correlated and are not
    separate capability failures. Never invent per-trap failure probabilities. Distinct means a different professional judgment,
    never one calculation split into checks. Counterexamples prove that a
    reading loses credit, not that either target model will adopt it. Only
    native complete-episode measurement establishes pass@1.
  EVERY FAILURE MUST TRACE TO A NAMED TRAP. A calibration failure no declared
    trap explains says nothing about the model and is the first thing suspected
    of being an ambiguity defect. Drive every objective through a trap and give
    every trap its own executed counterexample, so every failure calibration
    produces is one you predicted.
  STARTING HYPOTHESES ON THE TWO CALIBRATION MODELS -- UNVERIFIED. They come
    from public evidence about task families, not verified weaknesses of
    these exact model versions. measured calibration data overrides them.
    Design the same substantive professional challenge for BOTH native
    harnesses; never assume one vendor cannot retrieve, code, revise or reason.
    Underspecification is never a lever.
  AVOID SAFEGUARD TERRITORY. Content near cybersecurity exploitation,
    biological or chemical weapons, or other refusal-prone areas makes a
    calibration model refuse or get blocked by a safety classifier; that voids
    the run and measures nothing. Choose another decision or reject_seed.

EVERY TRAP GENUINE, NO CHECK DEAD OR VOID. Checked before the task is calibrated
-- by the gates and the executed controls, and, for whether a rule is truly
published and unambiguous, by the independent reviewer. A failure of any of these
is a defect, not difficulty:
  - RESOLVABLE: the rule that settles each trap is stated -- as a criterion, not
    a procedure -- in the instruction or a fixture document. An expert with only the workspace gets every answer
    right. A failure caused by a hidden rule, an unstated convention or an
    ambiguous definition is not the model's.
  - LIVE: the public case really distinguishes the correct reading from the
    misreading. EVALUATE the shortcut's answer and confirm it differs from the
    target on at least one item; a dormant trap is a dead check.
  - FAILABLE: every objective check -- all of them, floor checks included -- is
    failed by at least one substantive counterexample in quality.counterexamples,
    executed through the shipped grader.
  - PASSABLE: the reference solution and an independently phrased correct
    alternative both pass; a correct answer written differently never loses
    credit.
  - REACHABLE: no `requires` chain hides a check behind something most attempts
    fail. A check nobody reaches is void weight, not difficulty.
  - ZERO on an untouched workspace: no check passes on work nobody did.

RUBRIC SIZE AND WEIGHT: at least {MIN_OBJECTIVES} objective checks per task, each an
independent decision that can discriminate between attempts. Objective weights
sum to exactly {WEIGHT_TOTAL} in every task -- the build splits them equally between
steps and normalises -- so every task in the batch carries an identical grader
total.

WHAT THE INDEPENDENT REVIEWER REJECTS AS "NOT HARD" -- avoid every one:
  - A fully specified census. If a short script of filters, substring tests,
    emptiness tests and arithmetic reproduces every graded answer without
    reading what the documents MEAN, the task is routine execution, however
    many traps it lists.
  - A trap the instruction already solves. Publish the RULE, never its RESULT:
    state the criterion that decides which document governs or which items are
    in scope -- in the fixture document where it lives, or in the instruction
    only when no document can carry it -- never which file wins or which items
    qualify, and never that a revision, conflict or residue exists. If the
    instruction tells the solver the answer to the trap, the trap measures nothing.
  - One calculation dressed as several decisions: a count, its threshold flag
    and its delta are one decision, not three.
  - A rule whose literal test contradicts its stated meaning (a keyword list
    standing in for "is an account question"). The reviewer calls that a grader
    defect, and it is one.

CRITERIA, NOT RECIPES. Publish every rule as a CRITERION in the domain's terms;
the solver decides which evidence meets it.
  - Name no columns, filters, joins or operations in the instruction. "Count the
    processes that cannot start until an unresolved setting is decided" -- never
    "count rows of register.csv whose status is 停止する".
  - No pre-judged evidence. The fixture never carries the judgment you grade: no
    index, register or summary whose column already says which items qualify,
    which document governs, or what an item is. Judgments are made from primary
    evidence -- the documents, raw captures, logs. An authored supplement is raw
    evidence, never a classification of it.
  - No extraction credit in core or stretch. A value read from one place, a lookup
    keyed by a prefix the instruction supplies, or a deduplicated column is floor
    work at most.
  - Step 2 changes a JUDGMENT. Its new information overturns or confirms a
    conclusion step 1 reached, and every step-2 objective depends on that
    re-judgment -- none is computable from the fixture plus the new fact alone.
  - Criteria still settle every case. If a criterion leaves an item undecidable
    from the workspace, sharpen the criterion; never fall back to a recipe.

THE DIFFICULTY SELF-AUDIT belongs in quality.difficulty_case. It is reviewed
after submission; check_draft provides optional local diagnostics, not permission
to submit or evidence of semantic validity or model difficulty:
  hardest_decision   the one decision a frontier model is most likely to get
                     wrong, and exactly why
  first_try_verdict  why a strong model working carefully will NOT get every
                     graded answer right on its first attempt. If you cannot
                     write this honestly, the draft is not done: make it harder
                     now -- do not count on a later attempt
  script_test        the shortest program that would score full marks, in a few
                     lines of pseudo-code, and why it cannot be written without
                     reading what the documents MEAN. If it only filters or sums
                     named columns with operations the instruction names, the
                     task is scaffolded: redesign it now
  misreadings        one entry per trap that drives an objective:
                     {{trap, misreading, why_plausible, diverges_on, counterexample}}
                     -- the wrong reading, why a careful model adopts it (it
                     should agree with the correct answer on most items), the
                     items where it diverges, and the id of the
                     quality.counterexamples entry that encodes it. That
                     counterexample is this trap's OWN (no other trap's
                     counterexample may submit the same answer), it fails checks
                     the trap drives and nothing else, and it loses at most
                     {MISREADING_MAX_OBJECTIVE_SHARE:.0%} of the objectives (at least one always passes) --
                     executed through the grader, so a dormant or merely
                     all-wrong trap is caught.
  pitfalls_considered  the trap hunt: at least {MIN_PITFALLS_CONSIDERED} candidates you
                     examined, each {{pitfall, family, where, decision, trap|reason}}
                     -- `where` a fixture file it lives in, `decision` "planted"
                     (naming the trap id) or "rejected" (with the reason: not
                     genuinely supported, unresolvable from published rules, or
                     not live). Every trap must appear as planted."""

SYSTEM = (SYSTEM.replace("{first_pass}", FIRST_PASS_TRAPS)
          .replace("{target}", str(CALIBRATION_TARGET_PASS_AT_1))
          .replace("{hard}", str(SPEC_HARD_MAX)))
# v2 (user, 2026-10-02): the difficulty doctrine leads -- the model weighs the
# start of its instructions most -- and the first-draft construction plan
# (ADVERSARIAL_PROMPT) is no longer part of the prompt: its findings are
# advisories and its quotas competed with the doctrine for the same attention.
from .levers import PROMPT as LEVERS_PROMPT
SYSTEM = LEVERS_PROMPT + "\n" + SYSTEM
SYSTEM += "\n" + CAPABILITY_PROMPT
SYSTEM += "\n" + CHALLENGE_PROMPT

#: Rules the validator enforces on every draft. They were stated only in the
#: deleted one-shot designer's prompt, so the route production actually uses
#: was held to them without being told -- each one a repair round at best.
#: Thresholds are interpolated from `validate`, so the text cannot drift.
SYSTEM += f"""

GRADED FOLLOW-UP WHEN SUPPORTED. A later step is useful when new evidence
requires a substantive revision. Adding a step does not itself make a task
harder. Declare it with `second_step` or the explicit `steps` contract,
including its own output. The second step is not more work; it is a
second DECISION: it introduces information step 1 could not have had and asks whether
the step-1 conclusion survives it. Step 2 writes its own NEW deliverable
recording what CHANGED and why; its checks read that file. Do NOT tell the agent
to leave step 1's file untouched or forbid editing it: step 1 is graded at its
own boundary and nothing grades that file in step 2, so the prohibition is an
unenforced rule -- the most common semantic-review rejection in the 2026-09-26
batch. Set `step` on every check; a check
left unassigned falls into step 1. Naming a check `obj2_...` does NOT assign it
to step 2; only the `step` field does. Step 2's instruction must be answerable
from ITSELF plus the files on disk: a calibration harness may start step 2 in a
fresh session that never saw step 1's prompt (Codex does -- a-034, 2026-09-27,
failed step 2 in every GPT episode because the rehearsal sequence it needed was
stated only in step 1). Step 1's deliverable and the fixture carry over; step
1's prompt does not. Restate in step 2 every fact, sequence or definition from
step 1's instruction that step 2 depends on.

SHAPE OF THE RUBRIC (v2, user 2026-10-02: blockers only for required checks):
  REQUIRED: at least {MIN_OBJECTIVES} objective checks; guardrails weight exactly 0;
  every objective failed by some substantive counterexample; reference = 1,
  untouched = 0. ADVISORY (reported by check_draft, never blocking): bands,
  weight shares (no single objective above {MAX_SINGLE_WEIGHT_SHARE:.0%} is still wise), `weight_basis`
  sentences, `requires` concentration (keep under {MAX_GATED_WEIGHT_SHARE:.0%}), trap counts (aim
  for {MIN_TRAPS} or more -- dense tasks carry many), the difficulty self-audit's shape,
  capability_plan, decisions bookkeeping. Dense is welcome: 15-30 objectives;
  every trap that drives an
    objective has its own misreading."""

# Batch step shape (user 2026-10-05: ~15% two-step, the rest single-step);
# `validate._second_step` enforces the same variable.
_STEP_SHAPE = os.environ.get("ARENA_STEP_SHAPE", "").strip().lower()
if _STEP_SHAPE == "single":
    SYSTEM += """

STEP SHAPE FOR THIS TASK: SINGLE STEP. Build exactly one graded step: no
`second_step`, no second entry in `steps`. Ignore the follow-up guidance above.
Every difficulty mechanism must live inside the one step; any premise change
arrives inside the fixture (a later document revising an earlier one), not as
a second instruction."""
elif _STEP_SHAPE == "two":
    SYSTEM += """

STEP SHAPE FOR THIS TASK: TWO STEPS. Declare `second_step` (or a two-entry
`steps` contract) with its own deliverable and graded checks, built on the
guidance above. Step 2 must be answerable from its own instruction plus the
files on disk (a fresh session)."""


def _tools(n_msgs: int) -> list[dict]:
    from ..dump.evidence import TOOLS
    return TOOLS + [
        CHALLENGE_TOOL,
        PORTFOLIO_TOOL,
        {'name':'stage_evidence', 'description':'Copy an inspected source into sources/ without overwriting files. Only anchored evidence at/before the pivot is allowed. Context requires a .json record preserving citations and completeness. Source-bound privacy policy runs before publication.',
         'input_schema':{'type':'object','properties':{'evidence_id':{'type':'string'},'path':{'type':'string'},
             'reason':{'type':'string'},'member':{'type':'string'},'text_view':{'type':'boolean'}},'required':['evidence_id','path','reason']}},
        {"name": "list_fixture",
         "description": "Every fixture document with its size and the parsers "
                        "that actually yield rows for it, measured.",
         "input_schema": {"type": "object", "properties": {}, "required": []}},
        {"name": "read_fixture",
         "description": "Read a fixture document in full, or a line range of a "
                        "long one.",
         "input_schema": {"type": "object", "properties": {
             "path": {"type": "string"},
             "offset": {"type": "integer", "description": "first line, 1-based"},
             "limit": {"type": "integer"}, "char_offset": {"type": "integer"}}, "required": ["path"]}},
        {"name": "initialize_scenario",
         "description": "Only when no fixture artifact survives, initialize a disclosed synthetic starting context for an F0/F1/F2 target. Cite an exact source user request. The context receives zero recovered-source credit. Stage the capability plan first; then use write_scenario for grounded data.",
         "input_schema": {"type": "object", "properties": {
             "context": {"type": "string"}, "reason": {"type": "string"},
             "citation": {"type": "string"}, "quote": {"type": "string"}},
             "required": ["context", "reason", "citation", "quote"], "additionalProperties": False}},
        {"name": "write_scenario",
         "description": "Create or revise an authored text/data document at a NATURAL relative path in the fixture (e.g. correspondence/2026-03-04 re rates.eml, policies/expenses-handbook.md, exports/ledger_q3.csv) -- never a folder or name that flags it as authored or important. Extensions: .md .txt .csv .tsv .json .jsonl .eml .ics .log .html .xml .yaml .yml. provenance/ is reserved; disclosure is recorded in provenance/, not in the fixture. Recovered files are immutable. Ground it in exact recovered public evidence, never an answer key. Maximum 256 KiB per file, 2 MiB total, within the category fidelity allowance. Publication, semantic review and source-derived grading requirements still apply.",
         "input_schema": {"type": "object", "properties": {
             "path": {"type": "string"}, "content": {"type": "string"},
             "reason": {"type": "string"}, "source_evidence": {"type": "array", "minItems": 1,
                 "items": {"type": "object", "properties": {
                     "file": {"type": "string"}, "quote": {"type": "string"}},
                     "required": ["file", "quote"], "additionalProperties": False}}},
             "required": ["path", "content", "reason", "source_evidence"], "additionalProperties": False}},
        {"name": "remove_scenario",
         "description": "Remove a previously authored scenario supplement and update its public disclosure. Recovered, unowned and modified files cannot be removed. Use this for obsolete or answer-revealing case material; update all draft references, then validate again. Do not replace a removed file with a withdrawal notice.",
         "input_schema": {"type": "object", "properties": {
             "path": {"type": "string"}, "reason": {"type": "string"}},
             "required": ["path", "reason"], "additionalProperties": False}},
        {"name": "list_corrections",
         "description": "The seed's correction moments verbatim -- what the "
                        "user actually disputed, with message citations to use "
                        "as trap provenance -- and every response the user "
                        "EDITED, DISAPPROVED or ESCAPED (per-turn feedback), with "
                        "what the user said next.",
         "input_schema": {"type": "object", "properties": {}, "required": []}},
        {"name": "read_trace",
         "description": f"Read the session transcript (0..{n_msgs - 1}). The "
                        "situation the task is lifted from. Each message shows the "
                        "user's per-turn feedback on it (approve / edit / disapprove "
                        "/ escape), undo and error markers, and every tool call with "
                        "its input and output (clipped inline; full bodies via "
                        "read_evidence). Long messages page with char_offset.",
         "input_schema": {"type": "object", "properties": {
             "start": {"type": "integer"}, "end": {"type": "integer"},
             "char_offset": {"type": "integer"}},
             "required": ["start", "end"]}},
        {"name": "read_signals",
         "description": "Arena's evaluation signals for this session (outcomes.json: "
                        "steerability, task_outcome_explicit, praise_complaint, "
                        "bash_recovery_steps, tool_hallucination) mapped to message "
                        "indices, the user's per-turn feedback counts, session stats and "
                        "the task split. Discovery aids for finding failure modes -- "
                        "never a quote, never the reward.",
         "input_schema": {"type": "object", "properties": {}, "required": []}},
        {"name": "run_parser",
         "description": "Run one registry parser over one fixture document and "
                        "return the rows it yields, so a projection is chosen "
                        "from evidence rather than guessed.",
         "input_schema": {"type": "object", "properties": {
             "parser": {"type": "string"}, "path": {"type": "string"},
             "limit": {"type": "integer"}}, "required": ["parser", "path"]}},
        {"name": "evaluate",
         "description": "Evaluate a target expression against the fixture and "
                        "return the answer it computes. Declare the projections "
                        "it needs. Use this on every target before emitting.",
         "input_schema": {"type": "object", "properties": {
             "projections": {"type": "array", "items": {"type": "object"}},
             "target": {"type": "object"}},
             "required": ["projections", "target"]}},
        {"name": "check_spec",
         "description": "Run the full validator suite over a draft spec and "
                        "return local diagnostics. Optional: findings do not prevent submission; downstream validation remains mandatory.",
         "input_schema": {"type": "object", "properties": {
             "spec": {"type": "object"}}, "required": ["spec"]}},
        {"name": "stage_spec", "description": "Assemble a large spec incrementally. Set a nested field by its key/index path. Use append=true to extend an existing array or update an object. Start with top-level sections, then fix individual fields. No validation is bypassed.",
         "input_schema": {"type": "object", "properties": {
             "path": {"type": "array", "items": {}, "description": "Keys or integer array indexes, e.g. ['checks',0,'actual','op']. Empty path replaces the root."},
             "value": {}, "append": {"type": "boolean"}}, "required": ["path", "value"]}},
        {"name": "read_draft", "description": "Read a section of your own staged draft. Empty path lists top-level sections; use deeper paths for large sections.",
         "input_schema": {"type": "object", "properties": {"path": {"type": "array", "items": {}}}, "required": []}},
        {"name": "check_draft", "description": "Validate the complete assembled draft and reference solution without retransmitting it.",
         "input_schema": {"type": "object", "properties": {}, "required": []}},
        {"name": "submit_draft", "description": "Retain the assembled candidate without a local quality veto. Mandatory validation, controls and independent review run downstream. Call this tool alone.",
         "input_schema": {"type": "object", "properties": {}, "required": []}},
        {"name": "reject_seed", "description": "Stop this design when the available sources cannot support a fair, substantive task. FINAL: the first valid call ends the design, so never send a trial call. `reason` argues the missing capacity (at least 200 characters); `source_evidence` lists each supporting passage as {file, quote}, the quote copied verbatim from that fixture file -- evidence written inside `reason` does not count. This is a legitimate outcome; do not manufacture hard checks. Call alone.",
         "input_schema": {"type": "object", "properties": {
             "reason": {"type": "string"},
             "source_evidence": {"type": "array", "minItems": 1, "items": {"type": "object",
                 "properties": {"file": {"type": "string"}, "quote": {"type": "string"}},
                 "required": ["file", "quote"], "additionalProperties": False}}},
             "required": ["reason", "source_evidence"], "additionalProperties": False}},
        SPEC_TOOL,
    ]


class _Sandbox:
    """Read access to the fixture, and to nothing else in the bundle.

    `authoring/extraction/after/` contains a later candidate repair, which may
    leak the dispute's proposed answer without establishing correctness or user
    acceptance. `solution/` is the reference answer of
    any earlier design, `tests/derived/` the computed projections. A designer
    that reads those writes a task it has been told the answer to, and no gate
    downstream can tell the difference, because the grader agrees with itself
    either way.

    Paths are resolved before the check, so `../authoring/extraction/after/x.md`
    and a symlink both fail. Denying on the raw string would not.
    """

    def __init__(self, fixture: Path) -> None:
        self.root = fixture.resolve()

    def resolve(self, rel: str) -> Path:
        from .contracts import contained, ContractError
        try:
            target = contained(self.root, rel)
        except ContractError:
            raise PermissionError(
                f"{rel!r} is outside the fixture. Only environment/files/ is "
                "readable: the bundle's own answer lives beside it and a design "
                "that reads it is worthless.")
        if not target.is_file():
            raise FileNotFoundError(f"{rel!r} is not a fixture file")
        return target


def _parser_fit(text: str) -> dict[str, int]:
    out = {}
    for name, parser in sorted(oracle.REGISTRY.items()):
        try:
            rows = parser(text)
        except Exception:
            continue
        if rows:
            out[name] = len(rows)
    return out


#: Characters of one trace message the designer may see. 1400 cut corrections
#: mid-sentence, and a trap has to quote the user verbatim -- a truncated quote
#: cannot be cited faithfully, and the surrounding reasoning is exactly the
#: material a hard task is built from.
TRACE_MESSAGE_CHARS = 6000


#: Characters of each tool call's input and of its output shown inline in the
#: transcript. The full bodies stay one `read_evidence` call away.
TOOL_IO_CHARS = 900


def _compact(value) -> str:
    if value is None:
        return ""
    text = value if isinstance(value, str) else json.dumps(value, ensure_ascii=False, default=str)
    return " ".join(text.split())


def _clip(text: str, limit: int = TOOL_IO_CHARS) -> str:
    return text if len(text) <= limit else text[:limit] + f" ...[{len(text) - limit} more chars]"


def _render_message(msg: dict, limit: int = TRACE_MESSAGE_CHARS) -> str:
    """One trace message as the designer reads it: everything a practitioner
    reviewing the session would see.

    It used to render text blocks only, and matched tool calls as type
    `tool-call` while this dump writes `tool-bash`, `tool-read_file`, ... -- so
    every tool call rendered as nothing. Nor did it show the user's per-turn
    feedback (approve / edit / disapprove / escape, present in 496 of 500
    sessions), undo markers or errors: the designer could not see which
    responses the user rejected, which are exactly where traps come from.
    """
    from ..privacy import redact_excerpt
    parts = []
    feedback = msg.get("feedback")
    if isinstance(feedback, dict) and feedback:
        parts.append("[USER FEEDBACK on this response: "
                     + ", ".join(f"{k}={v}" for k, v in feedback.items()) + "]")
    if msg.get("undone") is True:
        parts.append("[UNDONE: the user undid this message]")
    if msg.get("error"):
        error = msg["error"]
        detail = (error.get("friendlyMessage") or error.get("errorCategory")
                  if isinstance(error, dict) else error)
        parts.append(f"[ERROR on this message: {detail}]")
    content = msg.get("content")
    if isinstance(content, str):
        parts.append(content)
    for block in content if isinstance(content, list) else []:
        if not isinstance(block, dict):
            continue
        kind = str(block.get("type") or "")
        if kind == "text":
            parts.append(str(block.get("text") or ""))
        elif kind == "tool-call":
            parts.append(f"[tool {block.get('toolName')}]")
        elif kind.startswith("tool-"):
            parts.append(f"[tool {kind[5:]} ({block.get('state') or 'no state'}) "
                         f"input: {_clip(_compact(block.get('input')))} | "
                         f"output: {_clip(_compact(block.get('output')))}]")
        elif kind in ("file", "image"):
            parts.append(f"[{kind} {block.get('filename') or block.get('mediaType') or ''}]")
    return redact_excerpt(" ".join(p for p in parts if p))[:limit]


#: Per-turn verdicts that mark a response the user did not accept as written.
REJECTING_FEEDBACK = ("edit", "disapprove", "escape")


def _require_shape(value, schema: dict, where: str) -> None:
    """Check structural types only; semantic validation still runs in full.

    Tool schemas may contain open objects and unconstrained values, unlike
    the deliberately closed schemas for solver deliverables.
    """
    kind = schema.get('type')
    types = {'object': isinstance(value, dict), 'array': isinstance(value, list),
             'string': isinstance(value, str), 'boolean': type(value) is bool,
             'integer': type(value) is int, 'number': type(value) in (int, float),
             'null': value is None}
    if kind in types and not types[kind]:
        hint = ' Pass the object or array directly, not a JSON-encoded string.' if isinstance(value, str) and kind in {'object', 'array'} else ''
        raise ValueError(f'{where}: expected JSON {kind}, got {type(value).__name__}.{hint}')
    if isinstance(value, dict):
        for key, item_schema in schema.get('properties', {}).items():
            if key in value:
                _require_shape(value[key], item_schema, f'{where}.{key}')
    elif isinstance(value, list):
        for index, item in enumerate(value):
            _require_shape(item, schema.get('items', {}), f'{where}[{index}]')


def _draft_field_schema(path: list) -> dict:
    schema = SPEC_TOOL['input_schema']
    for key in path:
        schema = (schema.get('items', {}) if type(key) is int
                  else schema.get('properties', {}).get(key, {}))
    return schema


def _handlers(bundle: Path, extraction, trace: dict, draft_path: Path | None = None,
              category: str | None = None, capability_version: int = 1) -> dict[str, Callable]:
    fixture = bundle / "environment" / "files"
    box = _Sandbox(fixture)
    messages = trace.get("messages", [])
    catalog = None
    def evidence():
        nonlocal catalog
        if catalog is None:
            from ..dump.recover import recover
            from ..dump.evidence import Catalog
            root = getattr(extraction, 'source_root', None)
            if root is None:
                from ..config import sessions_root
                root = sessions_root()
            catalog = Catalog(trace, recover(trace, root), root, extraction.span, extraction.pivot)
        return catalog
    import copy
    from ..checkpoint import digest, WORKSPACE
    from ..artifacts import evidence_inventory
    def workspace_inventory(root):
        return evidence_inventory(root, WORKSPACE)
    checked = None
    def isolated(action, arguments):
        from ..local_work import run
        return run(action, {'bundle': str(bundle.resolve()),
            'extraction': {'session_id': extraction.session_id, 'seed_index': extraction.seed_index},
            'trace': trace if action == 'check_spec' else {}, 'category': category,
            'arguments': arguments})
    draft = {}
    if draft_path and draft_path.is_file():
        draft = json.loads(draft_path.read_text())

    def draft_spec():
        return copy.deepcopy(draft)

    def read_draft(path=None, **_):
        if not path:
            return {"sections": list(draft)}
        cur = draft
        for key in path:
            if type(key) not in (str, int):
                raise ValueError("draft paths contain only keys and integer indexes")
            cur = cur[key]
        return copy.deepcopy(cur)

    def stage_spec(path, value, append=False, **_):
        nonlocal draft
        changed = copy.deepcopy(draft)
        if not isinstance(path, list) or any(type(k) not in (str, int) for k in path):
            raise ValueError("draft path must be a list of keys or integer indexes")
        _require_shape(value, _draft_field_schema(path), 'draft' + ''.join(f'[{k!r}]' for k in path))
        if not path:
            if not isinstance(value, dict):
                raise ValueError("spec root must be an object")
            changed = copy.deepcopy(value)
        else:
            cur = changed
            for key in path[:-1]:
                cur = cur[key]
            key = path[-1]
            if append:
                if isinstance(cur[key], list) and isinstance(value, list):
                    cur[key].extend(copy.deepcopy(value))
                elif isinstance(cur[key], dict) and isinstance(value, dict):
                    cur[key].update(copy.deepcopy(value))
                else:
                    raise ValueError("append requires matching arrays or objects")
            else:
                cur[key] = copy.deepcopy(value)
        if draft_path:
            from ..artifacts import atomic_json
            atomic_json(draft_path, changed)
        draft = changed
        return {"stored": path, "sections": list(draft)}

    def list_fixture(**_):
        rows = []
        for path in sorted(fixture.rglob("*")):
            if not path.is_file():
                continue
            from ..dump.formats import inspect_body
            view = inspect_body(path.read_bytes(), path.name)
            text = view.get('text')
            if text is None:
                rows.append({'path':str(path.relative_to(fixture)), 'bytes':path.stat().st_size,
                             'format':view.get('format'), 'parsers_that_fit':{}, 'readability':view.get('readability')})
                continue
            rows.append({"path": str(path.relative_to(fixture)),
                         "chars": len(text), "lines": text.count("\n") + 1,
                         "parsers_that_fit": _parser_fit(text)})
        return {"documents": rows,
                "note": "parsers_that_fit is measured by running each parser, "
                        "not guessed. A projection naming a parser absent from "
                        "a document's list yields no rows and is refused."}

    def write_scenario(**kwargs):
        from .scenario import write
        return write(bundle, category=category, **kwargs)

    def initialize_scenario(**kwargs):
        from .scenario import initialize
        return initialize(bundle, trace=trace, session_id=extraction.session_id,
                          category=category, **kwargs)

    def remove_scenario(**kwargs):
        from .scenario import remove
        return remove(bundle, **kwargs)

    def read_fixture(path: str, offset: int = 1, limit: int = 4000, char_offset=None, **_):
        from ..dump.formats import inspect_body
        view = inspect_body(box.resolve(path).read_bytes(), path)
        text = view.get('text')
        if text is None:
            return view
        lines = text.splitlines(keepends=True)
        start = max(int(offset) - 1, 0)
        begin = max(0, int(char_offset)) if char_offset is not None else sum(map(len, lines[:start]))
        end = min(len(text), begin + 40000)
        if char_offset is None:
            end = min(end, begin + sum(map(len, lines[start:start + max(1, int(limit))])))
        return {"path": path, "total_lines": len(lines),
                "showing_characters": [begin, end], "truncated": end < len(text),
                "next_char_offset": end if end < len(text) else None,
                "text": text[begin:end]}

    def user_feedback():
        """Every response the user edited, disapproved or escaped, with what
        the user said next -- the rejected turns are where traps come from."""
        lo, hi = getattr(extraction, "span", (0, len(messages) - 1)) or (0, len(messages) - 1)
        rows = []
        for i, msg in enumerate(messages):
            verdict = (msg.get("feedback") or {}).get("check_in") if isinstance(msg.get("feedback"), dict) else None
            if verdict not in REJECTING_FEEDBACK:
                continue
            reply = next((m for m in messages[i + 1:] if m.get("role") == "user"), None)
            rows.append({"msg": i, "cite": f"{extraction.session_id[:8]}::msg{i}",
                         "user_verdict": verdict, "in_seed_span": lo <= i <= hi,
                         "response_excerpt": _render_message(msg, limit=900),
                         "user_said_next": _render_message(reply, limit=2400) if reply else None})
        return rows

    def list_corrections(**_):
        return {"user_feedback": user_feedback(), "corrections": [
            {"cite": f"{extraction.session_id[:8]}::msg{m['msg']}",
             "signal": m.get("signal"),
             "user": redact_excerpt(m.get("user") or ""),
             # The wrong turn the user objected to IS the trap. 400 words
             # truncated it away in the longer sessions.
             "agent_had_just_said": " ".join(
                 redact_excerpt(m.get("prior_assistant") or "").split())[:2400]}
            for m in extraction.moments],
            "note": "A trace_derived trap needs an exact citation to a substantive "
                    "user correction or constraint read in the trace. These "
                    "discovery signals are candidates, not proof of corrections; "
                    "an empty outcome record supplies no user quotation. A trap "
                    "type must be one the actual exchange could have produced. "
                    "The signal is a coarse discovery "
                    "annotation, not correction_class. Classify the actual "
                    "exchange using the trap taxonomy's allowed classes; do "
                    "not use steerability or praise_complaint as a class. "
                    "Private access data is masked; cite only unchanged user "
                    "words, never a redaction marker as an original quote. "
                    "user_feedback lists every response the user EDITED, "
                    "DISAPPROVED or ESCAPED, with what the user said next: "
                    "those rejected turns are the model's failures in this "
                    "session and the richest trap material. A trace_derived "
                    "trap still quotes the user's own words, never a verdict."}

    def read_signals(**_):
        from ..dump import signals as sig
        node_to_msg = {n: i for i, m in enumerate(messages) for n in (m.get("node_ids") or [])}
        try:
            outcomes = sig.load_outcomes(extraction.session_id, getattr(extraction, "source_root", None))
        except (OSError, ValueError) as exc:
            outcomes = {"outcomes": [], "error": f"{type(exc).__name__}: {exc}"}
        grouped = {}
        for row in outcomes.get("outcomes") or []:
            name = row.get("signal_name")
            entry = grouped.setdefault(name, {"counts": {}, "rows": []})
            entry["counts"][row.get("outcome")] = entry["counts"].get(row.get("outcome"), 0) + 1
            # Routine successes of the high-volume signal carry nothing to design from.
            if name == "tool_hallucination" and row.get("outcome") == "success":
                continue
            node = str(row.get("observation_id") or row.get("annotating_node_id") or "").split("::")[0]
            detail = {k: v for k, v in row.items() if k not in {
                "session_id", "terminal_node_id", "annotating_node_id", "observation_id",
                "signal_name", "observation_ts"}}
            if len(entry["rows"]) < 60:
                entry["rows"].append({"msg": node_to_msg.get(node), **detail})
        feedback = {}
        for msg in messages:
            verdict = (msg.get("feedback") or {}).get("check_in") if isinstance(msg.get("feedback"), dict) else None
            if verdict:
                feedback[verdict] = feedback.get(verdict, 0) + 1
        tasks = [{"task_index": t.get("task_index"), "n_turns": t.get("n_turns"),
                  "messages": sorted({node_to_msg[n] for n in (t.get("turn_ids") or []) if n in node_to_msg})}
                 for t in trace.get("tasks") or []]
        return json.loads(redact_excerpt(json.dumps({
            "signals": grouped, "outcomes_error": outcomes.get("error"),
            "user_feedback_counts": feedback, "session_stats": trace.get("stats"),
            "tasks": tasks, "seed_span": list(getattr(extraction, "span", []) or []),
            "note": "Arena's five evaluation signals (outcomes.json): bash_recovery_steps, "
                    "tool_hallucination, task_outcome_explicit, praise_complaint, steerability. "
                    "Individually noisy: use them to FIND failure modes and material -- a "
                    "steerability failure is a correction the model did not apply, an explicit "
                    "failure or complaint marks a bad outcome -- then read those messages. "
                    "Never quote a signal as a user correction and never use it as the reward."},
            ensure_ascii=False)))

    def read_trace(start: int, end: int, char_offset: int = 0, **_):
        lo = max(int(start), 0)
        hi = min(int(end), len(messages), lo + 3)
        offset = max(0, int(char_offset))
        def entry(i):
            text = _render_message(messages[i], limit=None)
            stop = min(len(text), offset + 14000)
            return {"i": i, "cite": f"{extraction.session_id[:8]}::msg{i}",
                    "role": messages[i].get("role"), "text": text[offset:stop],
                    "next_char_offset": stop if stop < len(text) else None}
        return {"messages": [
            entry(i) for i in range(lo, hi)], "next_message": hi if hi < len(messages) else None,
            "total_messages": len(messages),
            "seed_span": list(extraction.span), "pivot": extraction.pivot}

    def run_parser(parser: str, path: str, limit: int = 60, **_):
        from ..local_work import enabled
        if enabled():
            return isolated('run_parser', {'parser': parser, 'path': path, 'limit': limit})
        if parser not in oracle.REGISTRY:
            return {"error": f"no parser {parser!r}",
                    "available": sorted(oracle.REGISTRY)}
        text = box.resolve(path).read_text(errors="replace")
        try:
            rows = oracle.REGISTRY[parser](text)
        except Exception as exc:
            return {"error": f"{type(exc).__name__}: {exc}", "rows": 0}
        # Fields from EVERY row: a column that appears only in row 200 is
        # exactly the sort of thing a check should turn on, and sampling the
        # first fifty hid it. The sample stays bounded; the schema does not.
        return {"parser": parser, "path": path, "rows": len(rows),
                "fields": sorted({k for r in rows for k in r}),
                "sample": rows[:int(limit)]}

    def evaluate_target(projections: list, target: dict, **_):
        from ..local_work import enabled
        if enabled():
            return isolated('evaluate', {'projections': projections, 'target': target})
        work = bundle / "authoring" / "agent-probe"
        try:
            _require_shape(projections, {'type': 'array', 'items': {'type': 'object'}}, 'projections')
            _require_shape(target, {'type': 'object'}, 'target')
            rows = oracle.project(fixture, projections)
            oracle.write(rows, work)
            ws = Workspace(source=fixture, submitted=fixture, derived=work,
                           projections=projections)
            value = evaluate(target, ws, "source")
        except Exception as exc:
            error = {"error": f"{type(exc).__name__}: {exc}"}
            if isinstance(exc, (KeyError, TypeError)) or "unknown operation" in str(exc) \
                    or "unsupported" in str(exc) or "not an expression" in str(exc):
                error["reference"] = EXPRESSION_REFERENCE
            return error
        note = None
        if isinstance(value, (list, set, tuple)):
            members = list(value)
            uniq = len({str(v).casefold() for v in members})
            if not members:
                note = ("EMPTY. An agent that writes nothing scores this. Either "
                        "the projection matched nothing, or the question has no "
                        "answer in this fixture.")
            elif any(v is None for v in members):
                note = ("CONTAINS NULLS. The parser yields rows but cannot read "
                        "the field being plucked. Unanswerable as written.")
            elif len(members) >= 8 and uniq / len(members) < 0.5:
                note = (f"MOSTLY REPEATS ({uniq} distinct of {len(members)}). "
                        "This field does not identify anything.")
            return {"kind": "set", "size": len(members), "distinct": uniq,
                    "value": members[:40],
                    "truncated": len(members) > 40, "warning": note}
        return {"kind": "scalar", "value": value}

    def check_spec(spec: dict, **_):
        nonlocal checked
        from .capability import require_staged_plan
        # v2: the capability plan is a construction aid. Hardening stages it at
        # version 2, and its bookkeeping ("decision X.checks: name at least 1
        # distinct existing ids") returned here BEFORE the advisory split, so it
        # vetoed a-035's otherwise valid repair (2026-10-02). Its findings are
        # advisories like every other construction aid's.
        plan_advisories: list[str] = []
        if capability_version > 1:
            try:
                require_staged_plan(spec, minimum_version=capability_version)
            except ValueError as exc:
                plan_advisories.append(f"capability plan (advisory construction aid): {exc}")
        from ..local_work import enabled
        if enabled():
            return isolated('check_spec', {'spec': spec})
        from .quality import production_problems
        from ..artifacts import policy_identity
        # Validators compile contracts in place. Never mutate a staged draft or
        # trust a clean result after any validation input has changed.
        draft = copy.deepcopy(spec)
        draft.setdefault("source", {"session_id": extraction.session_id,
                                    "seed_index": extraction.seed_index,
                                    "tier": 4})
        submitted = copy.deepcopy(draft)
        def input_key():
            return digest({"spec": submitted, "trace": trace,
                           "workspace": workspace_inventory(bundle), "policy": policy_identity()})
        key = input_key()
        if checked is None:
            from .. import checkpoint as progress
            cached = progress.read(bundle).get('validation', {})
            path = bundle / 'verification/spec-validation.json'
            if cached.get('input_sha256') == key and path.is_file():
                import hashlib
                if hashlib.sha256(path.read_bytes()).hexdigest() == cached.get('result_sha256'):
                    saved = json.loads(path.read_text())
                    if saved.get('clean') is True and saved.get('problems') == []:
                        checked = (key, saved)
        if checked and checked[0] == key:
            return {**copy.deepcopy(checked[1]), "reused_exact_validation": True}
        try:
            problems = production_problems(draft, bundle, authoring=True) + validate(draft, bundle)
            from ..ledger.faithfulness import citation_problems
            problems += citation_problems(draft, trace, extraction.session_id)
            from ..ledger.grounding import alignment_problems
            problems += alignment_problems(draft, trace, extraction.session_id, required=True)
        except Exception as exc:
            return {"clean": False,
                    "validation_unverified": isinstance(exc, (OSError, RecursionError)),
                    "validation_scope": "local-draft-only", "release_ready": False,
                    "problems": [f"the spec could not be validated: "
                                 f"{type(exc).__name__}: {exc}"]}
        validation_unverified = False
        # v2 (user, 2026-10-02): only required findings block or repair; the
        # rest are advisories the designer still sees (`pipeline.advisory`).
        from ..advisory import split as split_advisories
        problems, advisories = split_advisories(problems)
        advisories = plan_advisories + advisories
        if not problems:
            try:
                draft.pop("_validation_deferred", None)
                draft["solution"] = derive_solution(draft, bundle)
                problems, more = split_advisories(verify_solution(draft, bundle))
                advisories += more
            except Exception as exc:
                validation_unverified = isinstance(exc, (OSError, RecursionError))
                problems = [f"deriving the reference solution raised "
                            f"{type(exc).__name__}: {exc}"]
        if not problems and input_key() != key:
            # Measured 2026-10-02: a pipeline sync during a-016's final submit
            # changed policy_identity mid-check and ended its lineage on this
            # finding. A clean result under stale inputs is re-checked once
            # against the current ones; only a second change is reported.
            if not _.get("_revalidated"):
                return check_spec(spec, _revalidated=True)
            problems = ["Validation inputs changed during execution; validate the current draft and evidence again."]
            validation_unverified = True
        try:
            from .levers import diagnostics as lever_diagnostics
            difficulty = lever_diagnostics(draft, bundle)
        except Exception as exc:                     # noqa: BLE001  advisory only
            difficulty = {"error": f"{type(exc).__name__}: {exc}"}
        result = {"clean": not problems, "problems": problems,
                  "advisories": advisories, "difficulty_doctrine": difficulty,
                  "validation_unverified": validation_unverified,
                  "validation_scope": "local-draft-only", "release_ready": False,
                  "construction_diagnostics": construction_diagnostics(draft),
                  "reference_answer": draft.get("solution") if not problems else None}
        if not problems:
            checked = (key, copy.deepcopy(result))
            from .. import checkpoint as progress
            from ..artifacts import atomic_json
            import hashlib
            path = bundle / 'verification/spec-validation.json'
            atomic_json(path, result)
            progress.update(bundle, validation={'input_sha256': key,
                'result_sha256': hashlib.sha256(path.read_bytes()).hexdigest()})
        return result

    def plan_challenge_with_draft(**arguments):
        return {**plan_challenge(**arguments), "stretch_checks": stretch_check_outlines(draft_spec())}

    def plan_portfolio_with_draft(**arguments):
        return {**plan_portfolio(**arguments), "stretch_checks": stretch_check_outlines(draft_spec())}

    return {"list_fixture": list_fixture, "read_fixture": read_fixture,
            'list_evidence': lambda **kw: evidence().list(**kw),
            'read_evidence': lambda **kw: evidence().read(**kw),
            'view_evidence_image': lambda **kw: evidence().image(**kw),
            'stage_evidence': lambda **kw: evidence().stage(bundle, **kw),
            "initialize_scenario": initialize_scenario,
            "write_scenario": write_scenario, "remove_scenario": remove_scenario,
            "list_corrections": list_corrections, "read_trace": read_trace,
            "read_signals": read_signals,
            "run_parser": run_parser, "evaluate": evaluate_target,
            "plan_challenge": plan_challenge_with_draft,
            "plan_portfolio": plan_portfolio_with_draft,
            "check_spec": check_spec, "stage_spec": stage_spec,
            "read_draft": read_draft, "draft_spec": draft_spec,
            "check_draft": lambda **_: check_spec(draft_spec())}


def validate_submission(spec: dict, row: dict, extraction, bundle: Path) -> dict:
    from ..dump import recover
    from ..policy import target_level
    trace = recover.load_trace(extraction.session_id, getattr(extraction, "source_root", None))
    receipt = bundle / "verification/construction-protocol.json"
    version = json.loads(receipt.read_text())["minimum_version"] if receipt.exists() else 1
    return _handlers(bundle, extraction, trace, category=target_level(row.get("category")),
                     capability_version=version)["check_spec"](spec)


def _construction_version(bundle: Path, extraction, initial_spec=None, retained=None) -> int:
    from ..artifacts import atomic_json
    receipt = bundle / "verification/construction-protocol.json"
    # v2 (user, 2026-10-02): the construction plan is optional guidance; its
    # findings are advisories. New sessions are no longer forced onto version 2.
    version = 1
    if isinstance(initial_spec, dict):
        quality = initial_spec.get("quality")
        plan = quality.get("capability_plan") if isinstance(quality, dict) else None
        if isinstance(plan, dict) and type(plan.get("version")) is int and plan["version"] == 2:
            version = 2
    if retained and retained.get("config", {}).get("capability_version") == 2:
        version = 2
    source = {"session_id": extraction.session_id, "seed_index": extraction.seed_index}
    if receipt.is_file():
        saved = json.loads(receipt.read_text())
        if (saved.get("schema") != "arena-pipeline/construction-protocol/1"
                or saved.get("source") != source or type(saved.get("minimum_version")) is not int
                or saved["minimum_version"] != 2):
            raise ValueError("construction protocol is invalid or belongs to a different source")
        version = 2
    if version == 2 and not receipt.exists():
        atomic_json(receipt, {"schema": "arena-pipeline/construction-protocol/1",
                              "source": source, "minimum_version": 2,
                              "basis": "first-draft construction requirements; not measured hardness"})
    return version


def _opening(row: dict, extraction, bundle: Path) -> str:
    from ..config import expected_traps
    from ..select.priority import TIER_TRACE_FLOOR
    from .extract import usable_correction_count
    fixture = bundle / "environment" / "files"
    n_docs = sum(1 for p in fixture.rglob("*") if p.is_file())
    tier = row.get("tier", 4)
    floor = TIER_TRACE_FLOOR.get(tier, 0.3)
    usable = usable_correction_count(row, extraction)
    want = expected_traps(n_docs, usable, 9)
    need = -(-int(floor * 100) * usable // 100)
    cls = row.get("classification", {})
    return redact_excerpt("\n".join([
        f"SESSION {extraction.session_id[:8]} seed {extraction.seed_index} "
        f"(tier {tier}, model under test {row.get('model')})",
        f"DOMAIN: {cls.get('domain')}",
        f"FAILURE MODE the classifier saw: {cls.get('failure_mode')}",
        'Full trace evidence inventory: ' + json.dumps(getattr(extraction, 'evidence_summary', {})),
        'Use list_evidence/search and read_evidence to inspect all relevant sources beyond the initial fixture. Context and later versions are private unless explicitly eligible and staged.',
        "",
        f"The fixture holds {n_docs} documents. The seed carries "
        f"{len(extraction.moments)} discovery signals and {usable} usable corrections. "
        "An empty outcome signal is not a correction to quote. Start by listing "
        "the fixture and reading the trace; do not design before you have read the "
        "documents you intend to project.",
        "",
        "TARGETS (v2: reported by check_draft as advisories, never blocking):",
        f"  - at least 5 traps; about {want} is typical for a fixture this size -- a target "
        "for genuine traps, never a quota to pad. Every trap needs a real misreading and a "
        "counterexample that proves it costs credit",
        f"  - trace_derived traps are counted by DISTINCT citation, and a "
        f"tier-{tier} source must reach {int(floor * 100)}% of its "
        f"{usable} usable corrections: cite at least {need} different "
        "ones. When usable is zero, no trace quotation is required; ground authored traps in the fixture",
        "  - at least one guardrail, including one `fixture_intact`",
        "  - no two objectives may resolve to the same answer",
        "  - a literal target may hold a scalar sentinel, never a list",
        "  - the majority of objective weight must be derived, not read off a "
        "single surface",
        "",
        "Complete the candidate and call `submit_draft`; optional `check_draft` findings do not veto submission. Clean means only local checks passed, not independent semantic validity or measured hardness. Retain honest all-evidence baselines even when they solve the task; do not invent a failure. Mandatory downstream validation decides acceptance.",
    ]))


def _cutoff_content(response: dict) -> list[dict]:
    return [block for block in response.get("content", [])
            if block.get("type") in {"thinking", "redacted_thinking", "text"}]


def restore_design_session(bundle: Path, checkpoint: dict) -> dict:
    """Resume an authentication-interrupted conversation with its original budget."""
    from ..artifacts import evidence_inventory
    from .contracts import contained, strict_json
    session = contained(bundle, checkpoint["session"])
    if evidence_inventory(bundle, [checkpoint["session"]]) != checkpoint["session_files"]:
        raise ValueError("Retained authoring conversation changed after recovery was recorded")
    if evidence_inventory(bundle, ["environment/files", "provenance"]) != checkpoint["workspace_files"]:
        raise ValueError("Retained authoring workspace changed after recovery was recorded")
    config = strict_json((session / "request-config.json").read_text())
    responses = sorted(session.glob("response-*.json"))
    if [p.name for p in responses] != [f"response-{i:03d}.json" for i in range(1, len(responses) + 1)]:
        raise ValueError("Retained authoring response sequence is incomplete")
    remaining = config["max_steps"] - len(responses)
    if not 0 < remaining <= MAX_STEPS or remaining != checkpoint["remaining_steps"]:
        raise ValueError("Retained authoring budget is invalid")
    messages = strict_json((session / "conversation.json").read_text())
    if not isinstance(messages, list) or not messages or messages[-1].get("role") != "user":
        raise ValueError("Retained authoring conversation has no complete request boundary")
    cutoff_restored = False
    if responses and messages[-1].get("content") == TRUNCATION_FEEDBACK:
        response = strict_json(responses[-1].read_text())
        blocks = _cutoff_content(response) if response.get("stop_reason") == "max_tokens" else []
        assistant = {"role": "assistant", "content": blocks}
        if blocks and (len(messages) < 2 or messages[-2] != assistant):
            messages.insert(len(messages) - 1, assistant)
            cutoff_restored = True
    draft = session / "draft.json"
    if checkpoint.get('pending_review_response') or checkpoint.get('warm_review'):
        raise ValueError('Legacy plan-review checkpoints must be migrated before authoring')
    return {"messages": messages, "config": config, "remaining_steps": remaining,
            "cutoff_restored": cutoff_restored,
            "draft": strict_json(draft.read_text()) if draft.exists() else None}


#: Prompt-cache breakpoints for the design loop.
#:
#: Every step re-sends the tool schemas, the system prompt and the whole
#: conversation. Measured over the 78 environments of the 2026-09-26/27 trees:
#: a median of 172 requests per environment (mean 236, max 754), re-sending a
#: median of 26M tokens of unchanged prefix at the full input rate because no
#: request carried `cache_control`. About 85% of authoring spend was that
#: re-sent prefix -- roughly $157 per environment at the median against $24
#: with the prefix served from cache (Opus 5: cache reads cost a tenth of
#: input, a cache write a quarter more; the markers cost nothing themselves).
#:
#: Two explicit markers, of the four the API allows per request:
#:   - the system block. Tools render before system, so this one marker caches
#:     tools and system together, and they are the same bytes for every
#:     request of every session;
#:   - the newest cacheable block of the conversation. Each request then reads
#:     everything before that block from cache and writes only what follows
#:     it. Earlier breakpoints remain valid read points (the API looks back up
#:     to twenty positions; a design turn adds fewer than five), so hits
#:     accrue as the conversation grows. A plain-string message (the opening,
#:     "Continue.", the budget nudge) is left exactly as it is and the marker
#:     lands on the block before it, so those few short messages are billed
#:     as input once and everything ahead of them is still read from cache.
#:
#: What this must never change is the prompt. `cache_control` is a serving
#: hint, not content: the model reads byte-identical tools, system and
#: messages at the same effort, so authoring output -- and with it the
#: difficulty of the task -- is unaffected by construction; the tests strip
#: the markers and check equality. The markers are applied to a per-request
#: COPY: `request-config.json`, which decides whether a stalled session may
#: resume, and `conversation.json`, from which every step is rebuilt, keep
#: their shape and never carry a marker, so nothing accumulates across turns
#: and every retained session resumes intact.
CACHE_MARK = {"type": "ephemeral"}

#: Block types the API accepts a marker on. A `thinking` block is not one, and
#: a marker placed on it is a 400 that would end the design, so the tail marker
#: walks back to the nearest cacheable block and is omitted if there is none.
CACHEABLE_BLOCKS = frozenset({"text", "image", "tool_use", "tool_result", "document"})


def _marked_tail(messages: list) -> list:
    """`messages` with a marker on the newest cacheable block, or unchanged.

    Walks back from the last message; string-content messages are skipped,
    never rewritten. The returned list, the one message and the one block
    that carry the marker are copies; everything else is shared.
    """
    for m_index in range(len(messages) - 1, -1, -1):
        message = messages[m_index]
        content = message.get("content") if isinstance(message, dict) else None
        if not isinstance(content, list):
            continue
        for b_index in range(len(content) - 1, -1, -1):
            block = content[b_index]
            if isinstance(block, dict) and block.get("type") in CACHEABLE_BLOCKS:
                blocks = list(content)
                blocks[b_index] = {**block, "cache_control": dict(CACHE_MARK)}
                marked = list(messages)
                marked[m_index] = {**message, "content": blocks}
                return marked
    return messages



#: v2 (2026-10-02): the request budget, in serialized characters, for the
#: designer's conversation. A dense design that read a long constitution and
#: its analyses reached 2.85M characters and the provider refused it (HTTP 400,
#: a-018). Old tool-result bodies are elided from the REQUEST only -- the stored
#: conversation keeps them, so resume and audit see everything.
REQUEST_CHAR_BUDGET = 1_800_000
ELIDED_RESULT = ("[elided from this request to fit the context window; the call and "
                 "its arguments are above -- re-read the source with read_fixture, "
                 "read_trace or read_evidence if you need it again]")
KEEP_RECENT_MESSAGES = 24


def within_context_budget(messages: list, budget: int = REQUEST_CHAR_BUDGET) -> list:
    """A copy of `messages` whose old tool results are elided until it fits."""
    import json as _json
    size = len(_json.dumps(messages, ensure_ascii=False))
    if size <= budget:
        return messages
    out = [dict(m) for m in messages]
    cutoff = max(0, len(out) - KEEP_RECENT_MESSAGES)
    for index in range(cutoff):
        if size <= int(budget * 0.75):
            break
        content = out[index].get("content")
        if out[index].get("role") != "user" or not isinstance(content, list):
            continue
        new_content = []
        for block in content:
            if isinstance(block, dict) and block.get("type") == "tool_result":
                before = len(_json.dumps(block.get("content"), ensure_ascii=False))
                if before > len(ELIDED_RESULT) + 200:
                    block = {**block, "content": ELIDED_RESULT}
                    size -= before - len(_json.dumps(ELIDED_RESULT))
            new_content.append(block)
        out[index]["content"] = new_content
    return out

def with_cache_breakpoints(body: dict) -> dict:
    """`body` with cache markers on its stable prefix; a new dict, never a mutation.

    The system prompt may be a string or a list of text blocks; anything else
    is refused rather than guessed at, because the system prompt is the
    design's own contract. Tools are passed through untouched -- they render
    ahead of the system prompt, so its marker already covers them.
    """
    system = body.get("system")
    if isinstance(system, str) and system:
        cached_system = [{"type": "text", "text": system, "cache_control": dict(CACHE_MARK)}]
    elif (isinstance(system, list) and system
            and all(isinstance(block, dict) and block.get("type") == "text" for block in system)):
        cached_system = [*system[:-1], {**system[-1], "cache_control": dict(CACHE_MARK)}]
    else:
        raise ValueError("cache breakpoints need a text system prompt")
    out = {**body, "system": cached_system}
    if isinstance(body.get("messages"), list):
        out["messages"] = _marked_tail(body["messages"])
    return out


def design(row: dict, extraction, bundle: Path,
           max_steps: int = MAX_STEPS, budget=None,
           feedback: list[str] | None = None, initial_spec: dict | None = None,
           resume_session: dict | None = None, revision: bool = False) -> dict:
    """Design by exploration, then emit. Returns the same spec shape as F2.

    `budget`, when given, is the batch-wide semaphore. Design used to sit
    outside it because a one-shot call was 1-12 requests; an agent is 20-60, and
    six of those in parallel is the uncontrolled fan-out the semaphore exists to
    prevent.
    """
    from ..dump import recover as rec

    # `load_trace` resolves the dump itself when no root is given; resolving it
    # here as well made every caller depend on the local workspace.toml.
    trace = rec.load_trace(extraction.session_id, getattr(extraction, 'source_root', None))
    import uuid
    from ..artifacts import atomic_json
    from .. import checkpoint as progress
    log = bundle / "verification/design-sessions" / uuid.uuid4().hex
    retained = restore_design_session(bundle, resume_session) if resume_session else None
    if retained:
        if initial_spec is not None or max_steps != retained["remaining_steps"]:
            raise ValueError("Continuation must use only the retained draft and remaining budget")
        initial_spec = retained["draft"]
    if initial_spec is not None:
        atomic_json(log / "draft.json", initial_spec)
    from ..policy import target_level
    level = target_level(row.get('category'))
    capability_version = _construction_version(bundle, extraction, initial_spec, retained)
    handlers = _handlers(bundle, extraction, trace, log / "draft.json", category=level,
                         capability_version=capability_version)
    tools = _tools(len(trace.get("messages", [])))
    opening = _opening(row, extraction, bundle) + "\n\n" + TRAP_GUIDANCE + "\n\n" + CONSTRUCTION_INTEGRITY
    from ..corpus import source_briefs
    peers = source_briefs(extraction.session_id, bundle)
    atomic_json(log / "source-peer-briefs.json", peers)
    opening += ("\n\nSOURCE-FAMILY NOVELTY PREFLIGHT: " + json.dumps(peers, ensure_ascii=False)
                + "\nThese are existing professional questions, NOT answer keys or inspiration evidence. "
                "Do not reconstruct the same task with additional figures, names or decoys. "
                "Use the actual trace to support genuinely different judgments; independent review still decides novelty.")
    opening += ("\nquality.capability_plan is optional guidance (its findings are advisories). "
                "Record quality.premise_map per the V4 CONJUNCTIVE DOCTRINE (check_draft validates it: a map "
                "that misstates the grader blocks; the count/share/family targets are advisories) and "
                "quality.fragility_budget per the V2 DIFFICULTY DOCTRINE; check_draft audits it.")
    if level in TRAP_POLICY:
        opening += "\n\n" + TRAP_POLICY[level]
    opening += ("\nUse stage_spec to build the draft in sections and finish with submit_draft. check_draft is optional local feedback, not a submission gate. "
                "Do not retransmit the complete large specification to repair one field. A cutoff response is not a submitted draft.")
    if initial_spec is not None:
        opening += "\nAn earlier draft is staged. Use read_draft and check_draft to inspect and repair it against the source."
    from .designer import CATEGORY_GUIDANCE
    if level in CATEGORY_GUIDANCE:
        # The category decides what the fixture may honestly be built from, so
        # the agent needs it before it starts reading, not after.
        opening = CATEGORY_GUIDANCE[level] + "\n\n" + opening
    # First, before anything else the author reads: a first design must be
    # extremely hard at full quality; a revision follows its brief. Decided by
    # the caller (`revision`), never by whether feedback text was passed:
    # category_batch sends a design brief as feedback on every first design.
    opening = (REVISION_MANDATE if revision else AUTHORING_MANDATE) + "\n\n" + opening
    if feedback:
        # A gate blocker is a concrete named defect, so
        # the redesign starts from the objection instead of rediscovering it.
        opening = ("Design or revise using the constraints and findings below. "
                   "Confirm which findings apply against the actual source. "
                   "If the source is inadequate or cannot be used fairly, reject "
                   "the seed instead of disguising a source defect as difficulty.\n\n"
                   + "\n".join(f"  - {line}" for line in feedback)
                   + "\n\n" + opening)
    from ..privacy import scan
    if findings := scan(bundle / "environment/files"):
        raise ValueError(f"redact flagged source material before authoring: {findings}")
    messages: list[dict[str, Any]] = [{"role": "user", "content": opening}]
    from .quality import QUALITY_PROMPT
    request_config = {"model": MODEL, "effort": ARENA_EFFORT,
                "max_steps": max_steps, "max_tokens": MAX_OUTPUT_TOKENS, "tools": tools,
                "system": SYSTEM + "\n" + QUALITY_PROMPT}
    if capability_version == 2:
        request_config["capability_version"] = 2
    if retained:
        original = retained["config"]
        tools_removed = (original.get("tools") != tools and
            [tool for tool in original.get("tools", []) if tool["name"] != "review_design"] == tools)
        allowed = {**request_config, "tools": original.get("tools")} if tools_removed else request_config
        output_raised = (type(original.get("max_tokens")) is int
                         and 0 < original["max_tokens"] < MAX_OUTPUT_TOKENS)
        if output_raised:
            allowed = {**allowed, "max_tokens": original["max_tokens"]}
        changed = sorted(key for key, value in allowed.items()
                         if key != "max_steps" and original.get(key) != value)
        if changed:
            # The instructions, tools or model changed since this session began
            # (any prompt edit does it). Replaying the old conversation under
            # new instructions is refused, and failing the task threw its work
            # away. Continue instead as a FRESH session seeded with the retained
            # draft and only the remaining budget -- the budget never resets.
            atomic_json(log / "continuation-invalidated.json", {
                "from": resume_session, "changed": changed, "remaining_steps": max_steps,
                "draft_retained": retained.get("draft") is not None, "budget_reset": False})
        else:
            messages = retained["messages"]
            if output_raised or retained["cutoff_restored"]:
                atomic_json(log / "output-allowance-upgrade.json", {
                    "from": resume_session, "previous_max_tokens": original.get("max_tokens"),
                    "max_tokens": MAX_OUTPUT_TOKENS,
                    "cutoff_content_restored": retained["cutoff_restored"],
                    "remaining_steps": max_steps, "budget_reset": False})
        if tools_removed and not changed:
            messages.append({"role": "user", "content":
                "The pipeline now reviews the completed environment once it is built. "
                "The preliminary review_design tool and plan approval requirement have been removed. "
                "Use your existing source evidence, draft and review findings to finish the complete "
                "two-step environment with stage_spec, check_draft and submit_draft. "
                "Do not request another plan review. Source fidelity, independent final review, "
                "sound grading and native difficulty measurement remain required. "
                "Your conversation and remaining response/repair allowances are preserved."})
            atomic_json(log / "workflow-upgrade.json", {
                "from": resume_session, "removed_tool": "review_design",
                "remaining_steps": max_steps, "repair_budget_reset": False})
        atomic_json(log / "continuation.json", resume_session)
    atomic_json(log / "request-config.json", request_config)
    atomic_json(log / 'conversation.json', messages)
    checked_clean = False
    consecutive_errors = 0

    def stop_stalled(reason: str, steps: int):
        import hashlib
        draft = log / 'draft.json'
        report = {'status': 'authoring-stalled', 'reason': reason, 'steps': steps,
                  'max_steps': max_steps, 'consecutive_tool_errors': consecutive_errors,
                  'session': str(log.relative_to(bundle)), 'release_ready': False,
                  'draft_sha256': hashlib.sha256(draft.read_bytes()).hexdigest() if draft.exists() else None}
        atomic_json(log / 'conversation.json', messages)
        atomic_json(log / 'stalled.json', report)
        progress.author_boundary(bundle, log, stage='stalled')
        raise AuthoringStalled(report)

    for step in range(max_steps):
        if step == max_steps - 3:
            messages.append({"role": "user", "content":
                "Three response turns remain in this design budget. Complete validation and submit a clean draft, or reject_seed with grounded reasons if the source cannot support the task. Preserve completed work; do not open new scope."})
        atomic_json(log / "conversation.json", messages)
        progress.author_boundary(bundle, log)
        # Effort is the programme-wide setting (config.ARENA_EFFORT). A design flaw
        # is not a bad answer, it is a whole environment that reads as hard and
        # measures nothing -- and this batch produced several. `high` is the
        # default and what every design so far has run at.
        #
        # Thinking is adaptive and ON by default on this model; it is NOT
        # configured here because `budget_tokens` is rejected with a 400 on
        # Opus 5 and `{type: "disabled"}` is the wrong direction. The assistant
        # blocks -- thinking included -- are appended back unchanged below,
        # which is what lets reasoning carry across tool results instead of
        # restarting on every turn.
        from .quality import QUALITY_PROMPT
        # The cache markers go on a per-request copy (`with_cache_breakpoints`):
        # the prompt the model reads is unchanged, and neither the stored
        # request config nor `conversation.json` ever carries a marker.
        body = with_cache_breakpoints({
            "model": MODEL, "max_tokens": MAX_OUTPUT_TOKENS, "system": SYSTEM + "\n" + QUALITY_PROMPT,
            "output_config": {"effort": ARENA_EFFORT},
            "tools": tools, "messages": within_context_budget(messages)})
        if budget is not None:
            with budget:
                response = _call(body)
        else:
            response = _call(body)
        progress.update(bundle, stage="authoring-tools")
        atomic_json(log / f"response-{step + 1:03d}.json", response)
        if response.get("stop_reason") == "max_tokens":
            if blocks := _cutoff_content(response):
                messages.append({"role": "assistant", "content": blocks})
            messages.append({"role": "user", "content": TRUNCATION_FEEDBACK})
            continue

        blocks = response.get("content", [])
        calls = [b for b in blocks if b.get("type") == "tool_use"]
        if not calls:
            messages.append({"role": "assistant", "content": blocks})
            messages.append({"role": "user", "content":
                             "Continue. Use stage_spec, check_draft, then submit_draft, or reject_seed with grounded source-capacity reasons."})
            continue

        emit = next((b for b in calls if b["name"] in {"design", "submit_draft", "reject_seed"}), None)
        if emit is not None and len(calls) > 1:
            messages.append({"role": "assistant", "content": blocks})
            messages.append({"role": "user", "content": [{"type": "tool_result",
                "tool_use_id": call["id"], "is_error": True,
                "content": "Emit design alone, after completing all exploration and validation calls."}
                for call in calls]})
            continue
        if emit is not None:
            if emit["name"] == "reject_seed":
                try:
                    report = _rejection(bundle, emit["input"])
                except (ValueError, KeyError, TypeError, OSError) as exc:
                    messages.extend([{"role": "assistant", "content": blocks}, {"role": "user", "content": [{
                        "type": "tool_result", "tool_use_id": emit["id"], "is_error": True,
                        "content": f"Invalid source-capacity receipt: {exc}"}]}])
                    continue
                report.update(model=MODEL, effort=ARENA_EFFORT, steps=step + 1)
                atomic_json(log / "source-rejection.json", report)
                progress.update(bundle, stage="rejected", authoring_session=None)
                raise SeedRejected(report)
            spec = handlers["draft_spec"]() if emit["name"] == "submit_draft" else emit["input"]
            spec.setdefault("source", {"session_id": extraction.session_id,
                                       "seed_index": extraction.seed_index,
                                       "tier": row.get("tier", 4)})
            spec["_agent"] = {"steps": step + 1, "self_checked": checked_clean,
                              "validation_deferred": True}
            spec["_producer"] = {"model": MODEL, "effort": ARENA_EFFORT}
            spec["_validation_deferred"] = True
            progress.submitted(bundle, log, spec)
            return spec

        # The streak counts TURNS in which every call failed, not calls: one
        # misread convention repeated across four parallel stage_evidence calls
        # is one mistake, and counting it four times stalled a design at step
        # 8 of 140 (build 2026-09-26, a-031). Any success in a turn resets it.
        results = []
        turn_failed = True
        for call in calls:
            fn = handlers.get(call["name"])
            try:
                out = fn(**call["input"]) if fn else {"error": "no such tool"}
            except Exception as exc:
                out = {"error": f"{type(exc).__name__}: {exc}"}
            failed = isinstance(out, dict) and bool(out.get('error'))
            turn_failed = turn_failed and failed
            if call["name"] in {"check_spec", "check_draft"} and out.get("clean"):
                checked_clean = True
            from ..dump.evidence import tool_content
            encoded = tool_content(out)
            if isinstance(encoded, list):
                results.append({'type':'tool_result','tool_use_id':call['id'],'content':encoded})
                continue
            if len(encoded) > 60000 and call["name"] in {"check_spec", "check_draft"}:
                encoded = json.dumps({k: v for k, v in out.items() if k != "reference_answer"})
            if len(encoded) > 60000:
                encoded = json.dumps({"error": "Response exceeds the tool window. Request fewer rows, or use read_fixture/read_trace char_offset to read slices.", "truncated": True})
            results.append({"type": "tool_result", "tool_use_id": call["id"],
                            "content": encoded, **({'is_error': True} if failed else {})})
        consecutive_errors = consecutive_errors + 1 if turn_failed else 0
        messages.append({"role": "assistant", "content": blocks})
        messages.append({"role": "user", "content": results})
        if consecutive_errors >= MAX_CONSECUTIVE_TOOL_ERRORS:
            stop_stalled(f'{consecutive_errors} consecutive turns in which every tool call failed; '
                         'inspect and repair the retained draft before retrying.', step + 1)

    stop_stalled(f'agent designer reached {max_steps} steps without a validated submission; retain this draft instead of restarting automatically.', max_steps)


#: A seed rejection is terminal, so its receipt must carry the actual argument.
#: A short "test" call used to be accepted as final: in an e2e build
#: (2026-09-26) four substantive rejections were refused for a missing field the
#: error message never named, and a 119-character probe became the record.
REJECTION_REASON_MIN = 200

#: Required shape, quoted in every refusal so the designer can fix it at once.
_REJECTION_SHAPE = ('{"reason": "<the source limitation, argued>", "source_evidence": '
                    '[{"file": "<fixture path>", "quote": "<text copied verbatim from that file>"}]}')


def _rejection(bundle: Path, data: dict) -> dict:
    from ..artifacts import evidence_inventory
    if not isinstance(data, dict):
        raise ValueError(f"reject_seed takes an object shaped {_REJECTION_SHAPE}")
    missing = sorted({"reason", "source_evidence"} - set(data))
    extra = sorted(set(data) - {"reason", "source_evidence"})
    if missing or extra:
        raise ValueError("reject_seed receipt is incomplete: "
                         + (f"missing {missing}" if missing else "")
                         + ("; " if missing and extra else "")
                         + (f"unexpected {extra}" if extra else "")
                         + f". Resend it shaped {_REJECTION_SHAPE}. Put the argument in "
                         "`reason` and each cited passage as its own `source_evidence` "
                         "entry -- evidence quoted inside `reason` does not count. Nothing "
                         "has been rejected yet.")
    if not isinstance(data['reason'], str) or len(data['reason'].strip()) < REJECTION_REASON_MIN:
        raise ValueError(f"`reason` must argue the source limitation in at least "
                         f"{REJECTION_REASON_MIN} characters: which decisions the sources cannot "
                         "support and why. A rejection is final -- the first valid call ends "
                         "this design -- so never send a trial or format test. Nothing has "
                         "been rejected yet.")
    evidence = data['source_evidence']
    if not isinstance(evidence, list) or not evidence:
        raise ValueError(f"`source_evidence` must list at least one passage, shaped {_REJECTION_SHAPE}")
    sandbox = _Sandbox(bundle / 'environment/files')
    for row in evidence:
        if not isinstance(row, dict) or set(row) != {'file', 'quote'}:
            raise ValueError("source evidence requires file and quote")
        if not isinstance(row['quote'], str) or not row['quote'].strip():
            raise ValueError("source quote must be nonempty")
        if row['quote'] not in sandbox.resolve(row['file']).read_text():
            raise ValueError("source-capacity quote is absent from the cited file")
    return {'status': 'source-rejected', 'release_ready': False,
            'source_inventory': evidence_inventory(bundle, ('environment/files',)), **data}


def _step_name(category: str | None) -> str:
    from .designer import _step_name as base
    return base(category)
