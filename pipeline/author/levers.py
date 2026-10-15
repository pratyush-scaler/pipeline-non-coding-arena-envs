"""The v2 difficulty doctrine: levers that measurably bite, and an advisory audit.

User, 2026-10-02: "the task should be genuinely hard for both the models and
both the models should genuinely fail most of the times ... as many traps and
checks as required ... completely genuine ... very dense ... only giving
visibility on what of task and not how ... add as many near miss decoys as
required."

Evidence (research/R1-R5 in this checkout, 2026-10-02):
  R1  new techniques: tool-betrayal of stated rules, format semantics,
      latent bases, density arithmetic, omission-type misreadings.
  R2  concrete public non-coding agent tasks and their trap patterns.
  R3  how Fable 5.1 (Claude Code) and GPT-6 Astra (Codex) actually work, from
      6,292 recorded steps: what they open, grep, truncate, round, assert.
  R4  this pipeline's blockers (the v2 advisory demotions follow it).
  R5  decoys that bite tool users, what-not-how, density, family skews.
  internal: 2,557-episode near-miss census; 369-check difficulty census.

Nothing here is a blocker. `diagnostics` reports to the designer through
check_draft and to the screen report; the screen measures difficulty.

V4 (2026-10-13, Arena 261013 review + spec 10_12) leads the prompt:
`CONJUNCTIVE_PROMPT` -- independent premises from different families, each on
its own checks, free share and premise share capped, a premise map recorded
(`author.premises` validates it). The V3/V2.x blocks stay below it for their
recipes; where they conflict, V4 wins and the conflicting lines are marked.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

from ..policy import MIN_FRAGILE_DECISIONS_PER_FAMILY, MIN_LEVER_MECHANISMS
from ..policy import (EXTREME_PASS_AT_1_MAX, MAX_FAMILY_HEAVIEST_SHARE, MAX_FAMILY_PRESENCE_SHARE,
                      MAX_FREE_SHARE, MAX_PREMISE_PHI, MAX_PREMISE_SHARE, MAX_TIMESTAMP_PREMISES_PER_TASK,
                      MIN_BATCH_FAMILIES, MIN_DISTINCT_SCORES_PER_MODEL, MIN_INDEPENDENT_PREMISES,
                      MIN_PREMISES_MULTI_TURN_TOTAL, MIN_PREMISES_PER_STEP_MULTI_TURN, MIN_RUN_REWARD_SD,
                      MODEL_SORTING_HIGH_PASS_AT_1, MODEL_SORTING_LOW_PASS_AT_1, PREMISE_MISS_RATE_BAND)

#: The lever catalogue. `targets`: which calibration family the evidence says
#: it bites ("astra", "fable", "both"). `evidence`: where the claim comes from.
LEVERS: dict[str, dict] = {
    "unflagged_document": {
        "targets": "both",
        "evidence": "R3: unnamed small files never opened in 65-67% of steps; only 15.5% of steps display every file",
        "recipe": "The decisive clause, exception, effective date or definition lives in a document the "
                  "instruction never names, filed under an ordinary name where a real matter file keeps it.",
    },
    "deep_in_long_document": {
        "targets": "both",
        "evidence": "R3: files >16 KB fully displayed <=10%; >64 KB <1%; Codex drops the middle of long outputs "
                    "in 56% of Astra steps; Claude Code previews 2 KB of >30 KB outputs in 31% of Fable steps",
        "recipe": "Put the operative sentence mid-way through a realistic 40-150 KB handbook, policy, minutes "
                  "or thread, phrased WITHOUT the instruction's vocabulary so a grep for the task's words misses it.",
    },
    "non_observation_rows": {
        "targets": "both",
        "evidence": "R5/TrustDABench: marked non-observation rows were the most damaging perturbation for all 8 models with Python",
        "recipe": "A ledger/register with 2-4 rows that are reversals, memo lines, brought-forward balances, "
                  "pro-forma or reference copies, marked by a code defined ONLY in a legend in another file.",
    },
    "near_twin_negative": {
        "targets": "both",
        "evidence": "R5: hard negatives agree on brand/name/description and differ in one attribute",
        "recipe": "Two entities/items/clauses identical in name and almost everything else, differing in one "
                  "decisive attribute (variant, region, legal entity, version, signatory) printed on every record.",
    },
    "surface_variant_identity": {
        "targets": "astra",
        "evidence": "internal: Astra 8/70 m.facebook.com, 5/5 S08 vs 508; R3: exact-membership host lists in all 5 failing episodes",
        "recipe": "One entity named 2-4 ways across files (prefix letter, zero padding, trade vs legal name, "
                  "host variant, transliteration); identity defined by a general registry rule in the files. Never name the variant.",
    },
    "lexical_proxy": {
        "targets": "both",
        "evidence": "DAB 2026: every agent regexes free text and never recovers; R3: files >16 KB are searched with keyword alternations",
        "recipe": "Keyword-bearing items that fail one clause (negated, hypothetical, quoted, wrong actor/object, "
                  "template boilerplate) plus in-scope items phrased WITHOUT the keyword. The grep set is the trap answer.",
    },
    "rounding_tie_betrayal": {
        "targets": "both",
        "evidence": "R1 [X]: round(2.625,2)=2.62; 3*0.145 -> Decimal(str()) gives 0.43 not 0.44; R3: Fable float round() in 17% of to-the-cent steps",
        "recipe": "A policy document states the house rounding (to the cent, halves away from zero, per line, "
                  "then summed). 5-7 lines are exact half-cent ties, some on binary float edges. Grader computes exactly.",
    },
    "rounding_stage": {
        "targets": "astra",
        "evidence": "R3: business-monetisation Astra 5/5 computed exactly and rounded once at the end where the target rounds each commission",
        "recipe": "The rounding STAGE (per line / per invoice / per period) is stated once in a document, not the "
                  "instruction; the per-line and once-at-end answers differ on 2-4 items.",
    },
    "convention_reach": {
        "targets": "astra",
        "evidence": "census rank 2: Astra 5/40 left a threshold unrounded; Fable hedged the same",
        "recipe": "A stated convention (rounding, unit, inclusive counting) also governs a derived threshold, "
                  "margin or difference the model does not think of as 'a value of that kind'.",
    },
    "counting_unit_boundary": {
        "targets": "fable",
        "evidence": "census rank 5: Fable 9 failures, Astra 0 (heading vs body, label vs description)",
        "recipe": "A counted quantity whose unit boundary has a tempting visible variant: headings or separators "
                  "inside a body count, label vs description, row vs record, visits vs visit-days.",
    },
    "revision_scope": {
        "targets": "both",
        "evidence": "census rank 1: population scope of a rule or revision (34 failed decisions); a-117 RB-04",
        "recipe": "A revision or compound condition reaches an already-judged item through an attribute the model "
                  "has no reason to re-read; the item's prior status is the decoy. Small population (1-4 items).",
    },
    "nested_exception": {
        "targets": "both",
        "evidence": "exception-chain paper: flat rules 100%, nested chains collapse; carve-back gaps over-applied by both families",
        "recipe": "Base rule, exemption, a carve-back in a footnote, a later 'notwithstanding' override. One item "
                  "qualifies ONLY via the override; one loses its exemption to the carve-back.",
    },
    "unverifiable_authority": {
        "targets": "fable",
        "evidence": "Fable 5.1 card: accepts unverifiable claims of authorization more readily; Fable over-attempts 72.6%",
        "recipe": "A forwarded note claims an approval ('the CFO OK'd it verbally') that the authority matrix in the "
                  "files does not recognise; the item stays out.",
    },
    "withhold_vs_resolve": {
        "targets": "astra",
        "evidence": "OpenAI GPT-6 guide: more likely to pause/ask on conflicting guidance; R3: Astra refused in 8/23 runs when context was missing",
        "recipe": "Two documents disagree on a field; a precedence clause in a THIRD document settles it. The right "
                  "output is the resolved value, not 'cannot determine'.",
    },
    "fill_the_gap": {
        "targets": "fable",
        "evidence": "AA-Omniscience: Fable 5.1 answers 72.6% of questions it gets wrong; Fable infers from its own step-1 file",
        "recipe": "One item's required input is genuinely absent; the output contract defines NOT_DETERMINABLE for "
                  "exactly that case. A plausible value is available from priors or a neighbouring item.",
    },
    "recency_over_firsthand": {
        "targets": "astra",
        "evidence": "R3/MSL: a newer second-hand relay over an older first-hand message sent Astra to the twin 6/6",
        "recipe": "A newer second-hand relay ('Sam says it moved to Thursday') vs an older first-hand record (the "
                  "organiser's own update); a records rule in the files makes the first-hand record govern.",
    },
    "retired_identifier_residue": {
        "targets": "both",
        "evidence": "R3/MSL: a retired address still shown in a later signature caught Sol 3/3; internal residue 10-20%",
        "recipe": "Something declared retired (address, code, account, rate) still appears in a later document's "
                  "footer, signature or template, where it is not operative.",
    },
    "copied_figure": {
        "targets": "fable",
        "evidence": "SocSci-Repro: Claude Code copies a reported figure (100% -> 63.3%) where Codex re-derives (90%)",
        "recipe": "A colleague's memo quotes a total at a different grain built on an input the files later supersede; "
                  "the memo's figure cannot be compared side by side, only re-derived.",
    },
    "attribute_not_in_step1": {
        "targets": "both",
        "evidence": "R5 S-1; Fable re-uses its step-1 file in 94% of step-2 runs; PASB saved claims 45% -> 72% failure",
        "recipe": "Step 2's notice revises a clause that applies to items with an attribute stated only in the "
                  "sources (not in the step-1 schema), touching 2-3 step-1 members.",
    },
    "readmission": {
        "targets": "both",
        "evidence": "R5 S-4",
        "recipe": "One step-2 change removes a step-1 member AND re-admits an item step 1 excluded under the clause "
                  "now removed. Diffing the step-1 list only removes.",
    },
    "aggregate_propagation": {
        "targets": "fable",
        "evidence": "R1 T9 / StateMemBench: derived value not recomputed after input changes",
        "recipe": "Step 1 classifies against a population statistic; step 2 restates one subgroup; items in OTHER "
                  "subgroups flip although their own rows did not change; one restated item does not flip.",
    },
    "implicit_constraint_plan": {
        "targets": "both",
        "evidence": "R1 T8: DeepPlanning implicit constraints; COMPASS feasibility 70-90% vs optimality 20-50%",
        "recipe": "A plan/allocation whose constraints are FACTS in documents (capacity changed in an email, leave "
                  "under a nickname, a site closed on a local holiday); grade with optimal_subset; accept every optimum.",
    },
    "omission_bias": {
        "targets": "both",
        "evidence": "R1 D2: self-review detects planted over-inclusions 6-7x more often than omissions",
        "recipe": "Design each trap so the tempting reading DROPS a member (an in-scope paraphrase, a variant name, "
                  "an item only the override admits) rather than adding one.",
    },
    "house_definition_vs_convention": {
        "targets": "fable",
        "evidence": "R2 P3: DABstep D1 general 'null = applies to all' clause extended to a boolean field, Opus 5 fails 80-100% vs GPT 15%; "
                    "Vals FinAgent average vs ending inventory; OfficeQA sample vs population variance",
        "recipe": "A data dictionary or methodology note defines a house convention that differs from the familiar one "
                  "(empty/null means 'applies to all', including for a yes/no field; mean of rates not pooled ratio; "
                  "ending not average balance) and it decides 2-4 items.",
    },
    "rules_stack_not_first_match": {
        "targets": "fable",
        "evidence": "R2 P16: DABstep D9/D10, when several rules match the gold applies ALL; Opus 5 charges the first match (fails 90-100%), GPT sums",
        "recipe": "The rule book says every matching rule applies cumulatively (fees, surcharges, holds, notices); 2-4 "
                  "items match more than one rule. State the stacking once, in the rule book's preamble.",
    },
    "most_specific_rule_only": {
        "targets": "astra",
        "evidence": "R2 P16 mirror (hypothesis): GPT's prior is to sum overlapping rules",
        "recipe": "The rule book says only the most specific matching rule applies; 2-4 items match a general and a "
                  "specific rule. Pair it with rules_stack_not_first_match only across different rule books.",
    },
    "salient_decoy_two_rules": {
        "targets": "fable",
        "evidence": "R2 P4: tau2-banking task_075, the purpose-labelled travel account loses once two fee rules from two documents both apply; Fable 5 0/4, GPT 4/4",
        "recipe": "One option is labelled for exactly the requester's purpose; it loses only after two rules from two "
                  "different documents are combined. The plain option wins on the stacked cost.",
    },
    "execution_order_dependency": {
        "targets": "astra",
        "evidence": "R2 P7: tau2 task_060 GPT-5.6-sol 0/4 (Fable solved): a rule in ANOTHER product's document forces the order",
        "recipe": "The deliverable includes an ordered sequence of actions; a rule in a different document (not the "
                  "one the request is about) makes the requester's stated order fail.",
    },
    "change_set_counterfactual": {
        "targets": "astra",
        "evidence": "R2 P17: DABstep D6 'which merchants are affected', GPT fails 65% vs Opus 15%; one gold is empty",
        "recipe": "Ask which items a hypothetical or announced change AFFECTS (their outcome changes), not which match "
                  "its subject; recompute the whole population; the affected set is small and may differ sharply from the matching set.",
    },
    "offsetting_errors": {
        "targets": "both",
        "evidence": "R2 P5: APEX-Accounting t14/t17 strict pass <=9.5%; SpreadsheetBench 2 debugging 8-12%",
        "recipe": "Two row-level misallocations of equal size offset, so every control total and the agent's natural "
                  "reconciliation stays green; only per-row composition is wrong.",
    },
    "interested_artifact_refuted": {
        "targets": "fable",
        "evidence": "R2 P1: an interested memo/draft/certificate disproved by the ledger (APEX-Accounting, Harvey LAB, tau2 requester claims)",
        "recipe": "A controller's memo, counterparty certificate or requester's summary asserts figures or statuses; the "
                  "primary records (ledger, register, signed instrument) disprove 1-3 of them. The task asks for the correct figures, never 'verify the memo'.",
    },
    "answerability_not_applicable": {
        "targets": "both",
        "evidence": "R2 P18: DABstep D4, both CLIs invented thresholds for a concept never quantified",
        "recipe": "A requested measure depends on a concept the documents mention but never quantify for one segment; "
                  "the contract's NOT_APPLICABLE / NOT_DETERMINABLE value is correct there and only there.",
    },
    "must_not_flag_twin": {
        "targets": "both",
        "evidence": "R2 P12: Harvey 'Does NOT flag Texas' (6 vs 10 days), Feb-29 dates; SpreadsheetBench 2 regression checks",
        "recipe": "An exact-set finding list where 2-3 near-twins of real findings are compliant and must NOT be "
                  "listed; each twin differs in the one attribute the rule turns on.",
    },
    "quantifier_scope_conflation": {
        "targets": "both",
        "evidence": "R2 P6: TB2 sparql-university (conflated conditions right on easy data, wrong on held-out); per-client vs pooled; first-assigned only",
        "recipe": "Two readings of a quantifier or aggregation level (any site vs every site; per-client vs pooled; "
                  "first-assigned vs any) agree on most entities and diverge on 2-3; the document pins one.",
    },
    "first_match": {
        "targets": "astra",
        "evidence": "R3: Astra takes the first match (re.search 49% of steps, next() 27%); dict keyed on a field, last duplicate wins (16%)",
        "recipe": "The governing occurrence is NOT the first one a scan meets (an amended clause later in the "
                  "document, a corrected row below the original), stated by the document's own rule.",
    },
    # --- v2.2 COMBINATIONS (user, 2026-10-02: "combine multiple levers"). Every
    # single mechanism above measured dead as the sole puzzle of a task (lever lab
    # L01-L17, 160/160 episodes solved); these interlock several on ONE decision.
    "masking_pair": {
        "targets": "both",
        "evidence": "satisfaction of search (radiology: a found abnormality lowers detection of a second); lab L20",
        "recipe": "One item carries a CONSPICUOUS problem A the agent will find (duplicate, over-cap amount, missing "
                  "approval reference, over-distance claim) AND a SILENT fact B in a different document that interacts "
                  "with A, so the graded value is right only when A and B are resolved together. A-only, B-only and "
                  "neither each give a DIFFERENT wrong value. Some A's are false alarms that B dissolves (an approval "
                  "from a delegate named only in an out-of-office reply). Mix in A's with no B so no pattern is learnable.",
    },
    "cascade_premise": {
        "targets": "both",
        "evidence": "369-check census: hard checks share a premise that changes and invalidates computed results; lab L21",
        "recipe": "Chain 3-5 links where resolving each changes the PREMISE of the next: identity/aggregation -> "
                  "qualifying amount (free-text credits) -> a revision stated once in ordinary correspondence (quoted "
                  "older messages restate the old figure) -> an order-dependent allocation (cap, queue, budget) -> who "
                  "is cut off or paid partially. 'Found the revision but patched only the named items without re-running "
                  "the order' must change at least two graded fields. Keep the moving population to 3-6 entities.",
    },
    "control_total_blind": {
        "targets": "both",
        "evidence": "R3: agent self-verification is structural (totals, schemas, counts); lab L22",
        "recipe": "Where the task legitimately demands a reconciliation (totals agree with invoices, bank, ledger), "
                  "make the traps REALLOCATIONS between graded buckets (entity, cost centre, period, partner) that leave "
                  "the control total unchanged, plus one offsetting pair whose two natural misreadings move equal and "
                  "opposite amounts so an intermediate subtotal still ties to a real artefact with another purpose.",
    },
    "cross_step_premise": {
        "targets": "both",
        "evidence": "the one task ever measured genuinely <0.5 (a-005): a near-twin identity re-decided in a fresh step 2; lab L23",
        "recipe": "Step 2 brings a correction as raw facts that invalidates part of step 1's deliverable AND cascades "
                  "(a novation moves spend between entities, a threshold flips, a flag list changes); the correct step-2 "
                  "answer also needs a step-1-era identity decision (a near-twin kept separate) that the fresh session "
                  "must reconstruct from the sources, not copy from the step-1 file.",
    },
    "opposite_skew_population": {
        "targets": "both",
        "evidence": "R2/R5: Fable over-attempts (answers 72.6% of questions it gets wrong) and credits unverifiable "
                    "authority; Astra withholds on resolvable conflicts; lab L24",
        "recipe": "One population with a three-way status (resolve one way / the other / hold). Some items look "
                  "resolvable through tempting but impermissible evidence (confident second-hand email, later note) and "
                  "must be HELD; others show a visible conflict that the procedure's precedence resolves and must NOT be "
                  "held. The over-attempting baseline and the cautious baseline each get several members wrong, on "
                  "different items.",
    },
    "multi_lever_item": {
        "targets": "both",
        "evidence": "pass@1 counts FULL success; per-item interlocks compound; lab L26",
        "recipe": "Every graded item needs 3-4 DIFFERENT levers at once (a surface variant with a near-twin, a revision "
                  "effective by a date in another zone/format, non-observation rows in a messy export, per-line rounding, "
                  "a free-text give-back, a cap in date order, a distinct-unit threshold), with different combinations on "
                  "different items. Resolving all but one lever of an item gives a wrong value for that item.",
    },
}

#: Measured outcomes of the lever lab (research/scripts/lab_ledger.py writes it;
#: copied here so the policy identity covers the evidence the designer reads).
EVIDENCE_PATH = Path(__file__).with_name("lever_evidence.json")


def measured_evidence() -> dict:
    try:
        return json.loads(EVIDENCE_PATH.read_text())
    except (OSError, ValueError):
        return {}


def _evidence_table() -> str:
    data = measured_evidence()
    labs = data.get("labs") or {}
    if not labs:
        return "(no lever-lab measurements recorded)"
    lines = []
    for lab, row in labs.items():
        cells = row.get("per_model") or {}
        result = ", ".join(f"{model.split('/')[-1]} {c['passes']}/{c['valid']} solved"
                           for model, c in cells.items() if c.get("valid")) or "not yet measured"
        lines.append(f" - {lab} [{row.get('shape')}] {row.get('mechanism')}: {result}")
    return "\n".join(lines)

#: Measured dead against these agents. Spending budget here adds nothing.
DEAD = (
    "breadth or volume of one mechanical rule (369-check census: anti-correlated with failure)",
    "a decoy NUMBER beside the right one (computed side by side and rejected, 448 hits)",
    "stated precedence or 'document A governs' (governing_precedence 0/90)",
    "forbidden-edit traps (0 failures in 5,210 attempts)",
    "trap labels, 'note that', worked examples on a trap item, any warned-about decoy (30/30 found)",
    "rules placed in the instruction (coded literally)",
    "non-English text as such; mechanical arithmetic; narrative claims about a computable fact",
    "NOTICING traps of any kind -- a plainly stated rule the agent reads in full and transcribes "
    "(v2 wave 1: 0 failures in 1,220 lever-episodes over 5 dense tasks, research/R6)",
    "a rule that names its own exception, decoy or wrong method ('not added up and divided by four', "
    "'the X total plays no part', 'the latest M price')",
    "trap rows that carry a label, kind/scope column, capitalised marker or explanatory note",
    "partner or colleague messages that state the right amounts or the right conclusion",
    "legacy reports or drafts in the fixture that print correct intermediate results",
    "hub files that hold most of the rules: one read neutralises the whole budget",
)

#: Words that announce a trap or hand over the procedure (R5 V16). Advisory.
HINT_LEXICON = (
    r"\bnote that\b", r"\bbe careful\b", r"\bwatch (?:out )?for\b", r"\bbeware\b",
    r"\bcareful(?:ly)?\b", r"\bverify\b", r"\bdouble[- ]check\b", r"\bcross[- ]check\b",
    r"\breconcile\b", r"\bincluding (?:any )?variants?\b", r"\bnotwithstanding\b",
    r"\bsuperseded?\b", r"\bstale\b", r"\boutdated\b", r"\bdecoy\b", r"\btrap\b",
    r"\btricky\b", r"\bgotcha\b", r"\bdon'?t forget\b", r"\bmake sure\b",
    r"\bjoin\b", r"\bfilter\b", r"\bgrep\b", r"\bregex\b", r"\bstep \d+:",
)

PROMPT = f"""
================================================================================
V2.1 DIFFICULTY DOCTRINE (2026-10-02) -- READ FIRST. Where anything later in this
prompt conflicts with this block, THIS BLOCK WINS.
================================================================================
GOAL. Both calibration models -- Fable 5.1 in Claude Code and GPT-6 Astra in
Codex, high effort, unlimited turns, a shell and stdlib Python (python:3.11-slim
+ ripgrep; no pandas, openpyxl or office/PDF libraries) -- should FAIL MOST
EPISODES, and every failure must be the model's: one defensible answer that a
careful expert reading every file would reach.

V2.2 -- INTERLOCKS, NEVER SINGLE TRAPS (user, 2026-10-02: "combine multiple
difficulty/hardening levers to make the tasks extremely extremely hard").
MEASURED in the lever lab (one micro-task per mechanism, 5 episodes per model,
this exact harness):
{_evidence_table()}
Every SINGLE mechanism was solved in every episode once it was the puzzle --
inferred methods, refunds hidden in a 1,400-line ledger's memos, unlisted
supplier spellings, time-zone traversal order, stacked rules, rounding stage.
A decision that turns on one lever has q ~ 0 for these agents however it is
hidden. THEREFORE a premise may stack two or more levers on ITS item, from
different documents, such that resolving all but one of them still gives a
WRONG graded value. Build those from the combination recipes in the catalogue
(masking_pair, cascade_premise, control_total_blind, cross_step_premise,
opposite_skew_population, multi_lever_item), using the single levers as their
parts. SUPERSEDED BY V4 (2026-10-13, Arena 261013): "route several checks
through each interlock" and "several levers on every graded item" -- an
interlock is ONE premise on its own checks; different premises stay on
different items so their failures stay independent. Each interlock is still
fully genuine: every rule published once, every fact in the files, one
defensible answer, nothing labelled or announced.

WHAT WAVE 1 MEASURED (research/R6). Five dense v2 tasks -- 8-32 objectives,
14-23 budgeted levers each -- scored pass@1 1.00 on BOTH models, 0 lever
failures in 1,220 lever-episodes. 96 of 122 levers were neutralised by their own
text: each deciding rule was a plain sentence in a small file both models read in
full before writing code, often naming its own exception or decoy, and trap rows
were labelled in the data. Both models hard-code literal sets after reading small
populations, rebuild step 2 from the sources, and transcribe every rule they read
into one correct line of code. NOTICING IS FREE FOR THESE AGENTS. A trap that only
asks the agent to find and transcribe a rule has q ~ 0, so density built from
noticing traps cannot move pass@1. Five real fragile decisions are worth more than
thirty nominal ones. DEAD, do not spend budget on: {'; '.join(DEAD)}.

THE ADMISSION TEST (a fragility entry counts ONLY if both hold):
 (i) DEFAULT-WRONG. Write the IDIOMATIC BASELINE: the script a careful agent
     writes after reading EVERY file, transcribing each published rule as worded,
     with the idioms these agents actually use -- exact equality and slug joins,
     dict last-wins / file order, `>` or `//` as worded, Decimal with one quantize
     at the end, `.lower()`, literal sets hard-coded after reading a small
     population, a full before/after recompute in step 2. It must get at least
     one graded member WRONG for this entry. Record it as a counterexample whose
     id starts with `baseline_` (the controls execute it); name in the entry the
     member it gets wrong and why.
 (ii) UNLABELLED. The trap member carries no note, status code named by the
     rule, comment, capitalised marker or adjacent explanation. Its deciding
     attribute is an ordinary-looking value of a field every row has, or a fact
     established in ANOTHER document with no shared distinctive term.
An entry failing either test is a noticing trap: it counts as zero.

THE FOUR ROUTES THAT KEEP EVERY RULE PUBLISHED AND STILL CAN BITE. The rule is
plain; the EVIDENCE decides whom it reaches. Build every fragile decision on one:
 (b) MIS-SCOPED APPLICATION ON UNLABELLED, VARIABLY FORMED EVIDENCE. The rule is
     general ("any listing on a Facebook property", "every complaint in which the
     customer says the delivery actually arrived late"); the evidence that
     satisfies it varies in form: host variants, prefixes and zero padding, trade
     vs legal names, paraphrases that qualify WITHOUT the rule's keyword, keyword
     hits that are negated, hypothetical, quoted or about someone else. SEMANTIC
     JUDGMENT AT SCALE: 150-400 short free-text records (notes, tickets, chat
     lines, comments), 40-120 KB, where membership is decided by meaning; the
     agent can read them all, but a keyword grep -- the idiomatic baseline --
     gets several wrong. Grade it as an exact set derived from the fixture (e.g.
     derive_rows with an `if` over the record text matching the exact planted
     positive phrasings, or a structured field elsewhere that only a reader can
     link). Measured: Astra 5/5 exact-host failures (R3); DAB agents regex free
     text and never recover.
 (c) A DEFAULT NUMERIC OR TIME IDIOM BETRAYS A CORRECTLY TRANSCRIBED RULE. A
     policy (not the instruction) states the convention; the data contains real
     binary-edge ties (2.675, 3 x 0.145 -> 0.435, 7 x 1.245) where float half-up,
     Python round() and Decimal(str(float)) disagree with exact half-up; a
     per-line rounding stage where once-at-the-end differs on 2-4 items (Astra
     5/5, R3); shift hours across a stated clock change. Grade with exact
     {{"op": "round", "mode": ...}}.
 (d) A TRIGGER FACT ESTABLISHED BY INFERENCE ACROSS DOCUMENTS. The clause says
     what happens when X holds; nothing says X holds. The agent must establish X
     from evidence elsewhere: a newer second-hand relay versus an older
     first-hand record under a records rule (Astra 6/6, MSL); a person's role
     inferred from a signature block in an unrelated thread; a product's variant
     from its SKU structure defined in a catalogue.
 (e) TWO RULES FROM TWO DOCUMENTS, COMPOSED, WITH NO LEXICAL BRIDGE. Neither
     sentence names the item; each alone gives a confident wrong answer (tau2
     task_075, Fable 5 0/4: the travel-branded account loses once two fee rules
     from two documents both apply). Rules-stack-not-first-match and a general
     wildcard clause extended to an unexpected field type (DABstep: Opus 5 fails
     80-100%) are this route.

DISCRIMINATING DATA. For every compound or boundary rule include at least one
graded member on which each plausible coding differs: AND vs OR, `>` vs `>=`,
per-line vs once-at-end, float vs exact half-up on a real edge, first vs latest
occurrence, one date field vs another. Take the alternative codings from how
these agents write code (above), and encode each as a counterexample that
changes a graded value. A rule the data never separates from its misreading is
not a lever (a-011: Astra coded AND for OR and still passed).

HOW AUTHORED MATERIAL MUST LOOK.
 - A rule states its positive criterion ONCE, in general form. It never names its
   decoy column, the wrong method, the code to keep, or the item it excludes.
 - At most two decisive rules per document; no "rule dump" message. A rule's
   applicability evidence lives in a different document from the rule, with no
   shared distinctive term.
 - No colleague message, legacy report or draft states a correct amount, verdict
   or intermediate result. Recovered trace files that print correct answers
   must not be decisive -- route the graded decision around them.
 - Long background-looking documents (over 30 KB, unnamed, not referenced by a
   hub file) are the only material these agents skim; put a decisive fact there
   only with no duplicate elsewhere and only where a careful expert would still
   regard the document as authoritative.

WHAT, NEVER HOW -- INCLUDING THE OUTPUT CONTRACT. The instruction is a
requester's message (who, what deliverable, why; 100-250 words of prose)
followed by the output contract. Field definitions give MEANING and FORMAT only:
 - Never restate a rule, threshold, baseline, trigger or rounding convention a
   document states ("`stop` when the 20-dirham rule in my plan says stop selling",
   never "< 20 / >= 20"). Units, places and date format are format; the rounding
   MODE and STAGE belong to the policy document.
 - Step 2 asks for the AFTER-state, not a diff defined as two applications of
   the rules; its news arrives as raw facts in the requester's or a third party's
   words and never reuses the vocabulary of the clause it triggers.
 - Name no governing document or edition; do not enumerate source classes.
 - check_draft flags instruction sentences that echo a rule_sources quote.
Keep every field's scope, exclusions and edge cases pinned: deleting a definition
creates ambiguity, not difficulty.

STEP 2 IS REBUILT FROM SCRATCH. Both models re-derive the before and after states
from the sources and use their step-1 file only as a check. A revision lever
survives only through routes (b)-(e): the event's consequence must be inferred
from unlabelled evidence, never announced in the clause's words.

GENUINENESS (non-negotiable; every past fake "bite" was an ambiguity):
 - For each trap write the strongest argument for the wrong reading. If a
   careful expert could defend it, fix the DOCUMENTS until they could not.
 - Each misreading has an executed counterexample carried coherently through
   every output it touches; a reworded or reordered correct answer passes; a
   source counterfactual moves the target. No world knowledge: any convention
   needed (a clock change, a holiday, a code meaning) is in the files.

NEAR-MISS DECOYS: as many as the scenario supports, but as POPULATION MEMBERS --
rows, entities, clauses, messages -- that the idiomatic baseline admits or drops,
differing from the right answer in an attribute it never reads. Never a second
candidate value for the same field, never labelled.

RULE WITNESSES. A filter's rule is witnessed by `rule_sources` ({{file, quote}}
verbatim from the document that states it); the instruction does not restate it.
FILES. Authored documents at natural paths (correspondence/, policies/,
exports/ ...); no scenario/ folder; text formats .md .txt .csv .tsv .json .jsonl
.eml .ics .log .html .xml .yaml up to 256 KiB per file, 2 MiB total. All graded
facts derivable by the grader; money via exact `round` with a mode.

LEVER CATALOGUE (each must still pass the admission test):
{chr(10).join(f' - {name} [{meta["targets"]}]: {meta["recipe"]}' for name, meta in LEVERS.items())}

FRAGILITY BUDGET (check_draft audits it, advisory):
 quality.fragility_budget = [{{"id": "...", "lever": "<a combination recipe or lever name above>",
   "levers": ["<two or more lever names interlocked on this decision>"],
   "partial_counterexamples": ["<baseline_partial_... ids: one per lever missed in turn>"],
   "route": "b|c|d|e", "targets": "fable|astra|both", "files": ["<fixture paths>"],
   "rule_file": "<file stating the rule>", "evidence_file": "<file deciding who it reaches>",
   "trigger": "what would make an agent notice it",
   "baseline_wrong_member": "the member the idiomatic baseline gets wrong, and why",
   "unlabelled": "why no label, note or marker gives it away",
   "checks": ["<objective ids>"], "counterexample": "<baseline_... counterexample id>"}}]
================================================================================
"""

#: V3 (user 2026-10-05: 40 tasks, pass@1 <= 0.5 on BOTH models, every failure
#: genuine). Evidence: research/R7-measured-bites.md -- the only genuine
#: failures ever measured in this harness. Plain string: no f-string braces.
MEASURED_BITES_PROMPT = """
================================================================================
V3 DOCTRINE: MEASURED BITES (2026-10-05). READ THIS FIRST. Where the V2.x
doctrine further down conflicts with this block, this block wins.
================================================================================
WHAT V2 MEASURED:
- About 24 dense v2 tasks scored pass@1 1.00/1.00, and so did lever labs L01-L29.
  Those covered interlocks, stacked silent traps, cascades, 360-case corpora, and
  rules hidden mid-manual.
- Noticing is free for these agents. A rule they read, they code correctly.
- Genuine failures came ONLY from the mechanisms below (research/R7). Each was
  measured in a real dense task. Build every task around them.

THE TWO MODELS FAIL DIFFERENTLY.
- FABLE reads every file and sees the decisive fact. It then OVERRIDES a rule the
  files state plainly, in favour of something that looks more sensible:
  - the author's apparent intent;
  - fidelity to an exact source value;
  - a figure repeated by several agreeing summaries;
  - the order in which rules were stated;
  - "the list as originally set".
  It usually calls this a "judgment call" in its final message.
- ASTRA is code-first and literal. It almost never deliberates, so it passes
  every rule it can transcribe. It fails when the key it reaches for literally
  is not the one the files declare:
  - the printed label rather than the declared identity;
  - the everyday category word rather than a defined term;
  - the reported event rather than the triggering event;
  - float or Decimal division where only exact rational arithmetic is right
    at a band edge.

COMPOSITION -- SUPERSEDED BY THE V4 CONJUNCTIVE DOCTRINE ABOVE (2026-10-13).
The recipes below stay as premise candidates; compose them by the V4 rules:
independent premises from DIFFERENT families, on DIFFERENT items, each on its
own atomic exact checks, both models targeted. Retired from this block: "at
least 3 Fable and 3 Astra bites" as the count rule, and "each bite feeds 2-3
separate checks (its own value, a downstream total, a verdict it moves)" --
that cascade made every failing check fail in the same runs (Arena 261013).
Still in force:
- Use DIFFERENT items for different bites.
- NEVER put two bites inside one exact-equality check (double-counting).
- Use 12-24 objective checks in total.

FABLE RECIPES (measured miss rate):
 F-G1 SELF-CONSISTENT WRONG FIGURE (a-040: 22/26).
   - Instructions or primary records determine a number by simple arithmetic.
   - A narrative line, an explainer box and a checklist all state the same
     WRONG result and agree with each other.
   - A governing document says descriptions lose whenever they disagree with
     what the instructions or records produce.
   - Put the wrong figure in one clause of a statement the agent must judge,
     beside a more conspicuous clause that holds.
   - The instruction asks whether each statement is true, judging "only what
     the quoted words themselves assert". Never mention the number.
 F-G2 AGGREGATE SHRUNK BY A LATER RULE (a-013: 15/15).
   - Rule 1: "qualifies if above the average of the items on our list".
   - Rule 2, stated later: "anything below k is not on the list at all".
   - Exactly one item falls below k, and only after a derivation (A + B - overlap).
   - Dropping that item moves the average across exactly one borderline item.
   - Add one item exactly at k.
   - Never mention the average, the exclusion or the order of operations.
 F-G3 STATED RULE WHOSE LITERAL OUTPUT LOOKS LOSSY (a-063: 9/10).
   - A house rule is mechanical, e.g. "figures quoted without cents are
     whole dollars".
   - 1-2 targets have small exact true values, e.g. $1.31 -> 1.
   - Restate the exact value a few lines from the target.
   - The field definition repeats the rule as a checkable trigger.
   - No notes field and no alternative-value field.
 F-G4 UNLABELLED CLOCK SKEW DECIDES "LATEST" (a-054: 8/10). FAMILY
   timestamp_ordering -- CAPPED (V4): at most one per task, never the default
   lever, about 10% of a batch; 36 of 37 shipped tasks rested on it.
   - Two exports of overlapping conversations; one uses an unlabelled
     different timezone.
   - On the raw stamps, two contradictory statements appear in the wrong order.
   - A fixture rule says the latest statement governs.
   - HARD anchors fix the offset, e.g. "it just opened" against a published
     10:00 start. Never soft cues.
   - The answer must hold for every offset the anchors allow.
 F-G7 AMENDMENT KEYED ON A DIFFERENT EVENT (a-049: F 10/10, A 4/10; bites BOTH).
   - A rate or rule change applies to work FINISHED (or signed, or shipped)
     from a date.
   - The correspondence reports only pick-up and payment on that date.
   - Later material reveals the true finish date.
   - Keep the two event verbs unmistakably distinct and both defined.
 F-G9 MAXIMISE GOAL AGAINST A NON-ENUMERATED EXCLUSION (a-005: 7/15).
   - The instruction's goal favours a high-value candidate.
   - A general clause ("not misleading for the product") bars it.
   - The barring fact sits in another document and must be EXPLICIT there.
 F-G5 (two-step tasks, step 2 only) A SILENT BACKDATE THAT RE-VALIDATES (a-031: 6/15).
   - Step-2 news moves an authority's effective date, e.g. "took effect the
     day after X stood down; my message only announced it".
   - A record step 1 correctly voided becomes valid.
   - Never name the record.

ASTRA RECIPES:
 A-G8 EXACT HALF ON A BAND EDGE (a-037: both models 30-50%).
   - A published ratio is built from chained divisions whose exact value is
     x.x5 and sits on a band threshold.
   - A document states half-up rounding of the published figure, comparison of
     the published figure against the band, and no intermediate rounding.
   - Float or Decimal division gives x.x4999..., so only exact rational
     arithmetic is right.
   - Use 2-3 such items across different bands. Exact binary values such as
     2.625 bite nobody.
 A-G7 the F-G7 recipe above, which bites both models.
 A-LABEL EVERYDAY LABEL VS DEFINED TERM (a-013 porterage: 10-30%; stronger
 when the deciding value is an unnamed intermediate).
   - A rate card defines a category ("large" = girth + length over 300 cm).
   - The data carries an everyday word, "Large", that disagrees on 2-3 items.
   - Those items need a two-field computation to classify.
 A-KEY DECLARED IDENTITY KEY VS PRINTED LABEL.
   - Records carry a printed label that differs by one token from the
     identity a document declares, e.g. "Model Set 508" vs "S08".
   - Some rows are filed under a sibling's lookup key.
   - The declared key is a field or file named in a document.
   - Identity must ALWAYS be decidable from a key in the data. Never ask for
     identity inferred from amounts or dates alone.
 A-G6 (two-step tasks, step 2 only) NEAR-TWIN RE-DECIDED IN A FRESH SESSION (Astra 10/10).
   - Step 2 changes something unrelated and asks for a from-scratch recount
     "by the identifier each record carries".
   - The variant-labelled source carries most of the coverage.
   - Never write a sentence equating the two labels.

GENUINE, NOT AMBIGUOUS. A failure counts as a bite only when:
- a blind, careful reader pointed at the item reaches your answer from the files
  alone; and
- the failing model's wrong answer contradicts a sentence that the files
  state.
Treat these as AMBIGUITY, not difficulty:
- both models giving the same wrong answer;
- identity with no key in the data;
- "does this answer cover the question" judgments;
- soft clock cues;
- world knowledge;
- order words not tied to a list position.
For each bite, write the strongest argument for the wrong reading. Then make
sure a specific sentence in the files defeats it, without that sentence naming
the item, the trap or the wrong method.

ADMISSION TEST, AMENDED.
- An ASTRA bite needs a `baseline_...` counterexample: the idiomatic literal
  code, e.g. float division, the printed label, the everyday word, or the
  reported-event date.
- A FABLE bite needs a `fable_override_...` counterexample: the
  intent/fidelity/stated-order override, carried coherently through every
  check it touches. The literal baseline gets Fable bites RIGHT, and that is
  expected.
- In quality.fragility_budget, set lever = the recipe id (e.g. "F-G1", "A-G8")
  and targets = fable|astra|both.

KEEP from V2: WHAT-not-HOW instructions, rules in documents at natural paths, no
labels or announcements on trap items, no answer-bearing drafts, and exact
rounding with a stated mode. The V2 dead list still applies, EXCEPT that F-G3
deliberately repeats its rule in the field definition.
================================================================================
"""


def _family_table() -> str:
    """The trap-family catalogue with its measured evidence (lever_evidence.json)."""
    from ..policy import DISCOURAGED_DECIDER_FAMILIES, TRAP_FAMILIES
    evidence = measured_evidence().get("families") or {}
    rows = []
    for family, meaning in TRAP_FAMILIES.items():
        entry = evidence.get(family) or {}
        tag = " [DISCOURAGED as a decider]" if family in DISCOURAGED_DECIDER_FAMILIES else ""
        detail = "; ".join(x for x in (entry.get("status"), entry.get("evidence"),
                                       f"grade as: {entry['grade']}" if entry.get("grade") not in (None, "-") else None)
                           if x)
        rows.append(f" - {family}{tag}: {meaning}" + (f" -- {detail}" if detail else ""))
    return "\n".join(rows)


#: V4 (user 2026-10-13, Arena 261013 review + spec 10_12): hardness from
#: conjunction, not from one trick. Leads the designer's system prompt.
CONJUNCTIVE_PROMPT = f"""
================================================================================
V4 CONJUNCTIVE DOCTRINE (2026-10-13; Arena 261013 review, spec 10_12). READ
FIRST. Where ANYTHING later in this prompt conflicts with this block -- the V3
measured-bites composition, the V2.x interlock doctrine, the first-pass trap
guidance -- THIS BLOCK WINS. It retires: "each bite feeds 2-3 separate checks
(its value, a downstream total, a verdict)", "route several checks through each
premise / interlock", "make each premise bear on several decisions", "let it
cascade", and the clock-skew carrier as the default lever.
================================================================================
WHY. Arena reviewed the last batch. 36 of 37 tasks hinged on one trap family
(timestamp ordering). The median step gave 72% of its points free. In 32 of 41
steps every failing check failed in exactly the same runs, and within-model
reward SD was 0 in 29 of 41 Fable steps. A group of runs that all score the same
teaches nothing. Spec 10_12 now requires: (1) a VARIED decisive trap across a
batch; (2) every inference RESOLVABLE from the instructions and files; (3)
difficulty SPREAD over checks that fail on their own, so partial progress earns
partial reward; (4) the SAME model passing some runs and failing others, with
partial scores -- not every run alike, not one model always passing while the
other always fails.

THE DESIGN -- HARDNESS FROM CONJUNCTION:
 - {MIN_INDEPENDENT_PREMISES}-5 INDEPENDENT PREMISES in a single-step task; in a multi-turn task at
   least {MIN_PREMISES_PER_STEP_MULTI_TURN} in EVERY step and at least {MIN_PREMISES_MULTI_TURN_TOTAL} across the task. Each premise is
   from a DIFFERENT family in the catalogue below, decided by a different item,
   settled in a different document. Each should be missed in roughly
   {PREMISE_MISS_RATE_BAND[0]:.0%}-{PREMISE_MISS_RATE_BAND[1]:.0%} of careful runs on the model it targets -- NOT 100%. Measured: independent
   premises multiply (clean runs exceed the product of per-premise pass rates by
   only +0.05 over 13 pools), so 4-5 premises at that rate keep full success at
   1-3 in 10 while every group of runs spreads over several distinct scores. A
   premise no run ever gets right is constant: zero learning signal, and the
   signature of an ambiguity (14 of 15 identical 10/10 misses were ambiguities or
   defects).
 - ONE DECISION = ONE CHECK. Each premise sits on its OWN atomic, exact
   check(s). Never put two premises inside one exact-equality check; split a set
   by the premise that decides each member; give "no extras" its own check. A
   check belongs to at most one premise.
 - NO CASCADE THROUGH DOWNSTREAM FIELDS. A total, verdict, rank or byte count
   that is a pure function of a graded decision is not another decision:
   graded against the reference, it fails in exactly the runs the upstream
   decision fails and turns the reward into a step function. The grader cannot
   read the agent's own answer inside a target, so do not request a purely
   derived field as a separate heavy objective; where the contract needs one,
   keep its weight small and inside the SAME premise (it counts against that
   premise's cap).
 - WEIGHTS PER STEP. Premise checks carry most of each step's objective weight;
   NO premise above {MAX_PREMISE_SHARE:.0%}; FREE weight (checks no premise decides -- field
   presence, plain rule application) at most {MAX_FREE_SHARE:.0%}. Every requested field is
   still graded.
 - ADDITIVITY. A deliverable carrying misreadings i and j must score exactly
   1 - w_i - w_j. Encode each premise's misreading as its own counterexample;
   two premises' counterexamples never fail the same check.
 - DIVERSITY. At most {MAX_TIMESTAMP_PREMISES_PER_TASK} timestamp-ordering premise per task (clock offset,
   store/outage windows, impossible stamps, outage-ordered letters are ONE
   family), and it is never the default. Across a batch, no family is the
   decisive premise in more than {MAX_FAMILY_HEAVIEST_SHARE:.0%} of tasks or present in more than
   {MAX_FAMILY_PRESENCE_SHARE:.0%}, and at least {MIN_BATCH_FAMILIES} families appear. Prefer families grounded in this
   trace's real corrections: changed premise, clean before-baseline, house
   number convention (exact non-binary half), near-twin identity WITH a key,
   coverage omission, caption-only rule, repeated wrong figure, scope with
   compliant twins.
 - RESOLVABLE BY EXPLICIT TEXT. What survives review at moderate rates is the
   NOTICING miss: the fact is stated in the materials and the model never
   cross-references it to the item. (Not the V2.1 "noticing trap" listed dead
   below -- a rule the agent reads in full and transcribes, q ~ 0 -- but a fact
   in another place the model never connects to the decision.) Every premise names one resolving sentence that a blind
   reader pointed at the item would use to reach your answer. Never a premise
   whose wrong reading a careful expert could defend (seven moderate bites went
   to 0% once the second reading was clarified), no world knowledge, no single
   soft anchor, identity always decidable from a key in the data.
 - SALIENCE IS THE DIAL. An anchor in the same thread, or posted verbatim in two
   places, is noticed; one on another day or deep in a long background document,
   with no reply cue, is missed. Vary salience across premises so different runs
   -- and the two models -- miss different premises. Fable and Astra per-task
   rates barely correlate (r = 0.22): give each model premises that bite it.
 - NO GRADED VALUE IN INSTRUCTION EXAMPLES. Examples in the instruction or the
   field definitions never contain an ID, number or spelling that is graded
   (two leaks: "IDs such as H01", "91 and 91.0").

THE PREMISE MAP (REQUIRED; check_draft validates it):
 quality.premise_map = [{{"id": "P1", "family": "<family id below>",
   "checks": ["<objective ids this premise alone decides>"],
   "targets": "fable|astra|both",
   "resolving_quote": {{"file": "<fixture path, or 'instruction'>", "quote": "<the verbatim sentence that settles it>"}},
   "misreading": "<the wrong reading a careful model adopts>",
   "counterexample": "<the quality.counterexamples id encoding it>",
   "salience": "<why some runs miss it and others do not>"}}]
 Checks in no premise are FREE weight. A map that misstates the grader BLOCKS
 (an unknown or non-objective check, a check in two premises, an unknown family,
 a quote the files do not contain): the screen, the cover sheet and hardening
 all read it. Premise count, share, free share, family distinctness and the
 timestamp cap are ADVISORIES the screen then measures.

WHAT THE SCREEN MEASURES (every 5 x 2 screen, per model and step): full passes,
distinct scores (target >= {MIN_DISTINCT_SCORES_PER_MODEL}), reward SD (target >= {MIN_RUN_REWARD_SD}), per-premise miss rates,
pairwise phi between premises (target < {MAX_PREMISE_PHI}), observed free share, constant
premises and model sorting (one model >= {MODEL_SORTING_HIGH_PASS_AT_1:.0%} while the other <= {MODEL_SORTING_LOW_PASS_AT_1:.0%}). Hardening
aims at pass@1 <= {EXTREME_PASS_AT_1_MAX} on both models WITH that spread; Arena's general target
stays pass@1 below 0.5.

FAMILY CATALOGUE (id: what it is -- measured evidence; "missed" = runs that got it wrong):
{_family_table()}
AVOID AS DECIDERS: authority/delegation conflicts, inferred generic exclusions,
identity with no key in the data, a trigger event without a defining sentence,
breadth, decoy numbers, forbidden edits, de-leaked scope sentences and
single-anchor inferences.
================================================================================
"""
PROMPT = CONJUNCTIVE_PROMPT + MEASURED_BITES_PROMPT + PROMPT


def _instruction_texts(spec: dict) -> list[tuple[str, str]]:
    out = []
    for index, step in enumerate(spec.get("steps") or []):
        if isinstance(step, dict):
            out.append((str(step.get("name") or f"step{index + 1}"), str(step.get("instruction") or "")))
    second = spec.get("second_step")
    if isinstance(second, dict) and second.get("instruction"):
        out.append(("second_step", str(second["instruction"])))
    if not out and spec.get("instruction"):
        out.append(("instruction", str(spec["instruction"])))
    return out


def diagnostics(spec: dict, bundle: Path | None = None) -> dict:
    """Advisory audit of a draft against the doctrine. Never a blocker."""
    advisories: list[str] = []
    quality = spec.get("quality") if isinstance(spec.get("quality"), dict) else {}
    budget = quality.get("fragility_budget")
    checks = {c.get("id"): c for c in spec.get("checks") or [] if isinstance(c, dict)}
    objectives = [cid for cid, c in checks.items() if c.get("kind") == "objective"]
    examples = {e.get("id") for e in quality.get("counterexamples") or [] if isinstance(e, dict)}
    fixture = (bundle / "environment/files") if bundle is not None else None
    files = set()
    if fixture is not None and fixture.is_dir():
        files = {p.relative_to(fixture).as_posix() for p in fixture.rglob("*") if p.is_file()}

    per_family = {"fable": 0, "astra": 0}
    mechanisms, triggers = set(), []
    if not isinstance(budget, list) or not budget:
        advisories.append("quality.fragility_budget is missing: list every fragile decision "
                          "(lever, targets, files, trigger, checks, counterexample)")
        budget = []
    for index, entry in enumerate(budget):
        at = f"quality.fragility_budget[{index}]"
        if not isinstance(entry, dict):
            advisories.append(f"{at} must be an object")
            continue
        lever = entry.get("lever")
        if lever not in LEVERS:
            advisories.append(f"{at}.lever {lever!r} is not a catalogued lever")
        else:
            mechanisms.add(lever)
        targets = str(entry.get("targets") or LEVERS.get(lever, {}).get("targets", "both")).lower()
        for family in per_family:
            if targets in (family, "both"):
                per_family[family] += 1
        trigger = str(entry.get("trigger") or "").strip().lower()
        if trigger:
            triggers.append(trigger)
        for cid in entry.get("checks") or []:
            if cid not in checks:
                advisories.append(f"{at}: check {cid!r} is not declared")
        if not entry.get("checks"):
            advisories.append(f"{at}: drives no check")
        ce = entry.get("counterexample")
        if ce and ce not in examples:
            advisories.append(f"{at}: counterexample {ce!r} is not in quality.counterexamples")
        for file in entry.get("files") or []:
            if files and file not in files:
                advisories.append(f"{at}: file {file!r} is not in the fixture")
    for family, count in per_family.items():
        if count < MIN_FRAGILE_DECISIONS_PER_FAMILY:
            advisories.append(f"{count} fragile decisions aim at {family}; the doctrine asks for "
                              f">= {MIN_FRAGILE_DECISIONS_PER_FAMILY} (pass@1 ~ (1-q)^n)")
    if len(mechanisms) < MIN_LEVER_MECHANISMS:
        advisories.append(f"{len(mechanisms)} distinct lever mechanisms; the doctrine asks for "
                          f">= {MIN_LEVER_MECHANISMS} so one insight cannot solve several decisions")
    if len(triggers) != len(set(triggers)):
        advisories.append("two fragile decisions share a noticing trigger, so they are not independent")

    named_files, hints = set(), []
    for name, text in _instruction_texts(spec):
        lowered = text.lower()
        for pattern in HINT_LEXICON:
            for match in re.finditer(pattern, lowered):
                hints.append(f"{name}: '{match.group(0)}'")
        for file in files:
            base = file.rsplit("/", 1)[-1].lower()
            if len(base) >= 6 and (file.lower() in lowered or base in lowered):
                named_files.add(file)
        words = len(re.findall(r"\w+", text))
        if words > 900:
            advisories.append(f"{name}: instruction is {words} words; a requester's message plus the "
                              "output contract rarely needs more -- is it carrying the HOW?")
    if hints:
        advisories.append("instruction uses announcing or procedural words (they turn traps into "
                          "checklists): " + ", ".join(sorted(set(hints))[:12]))
    # --- v2.1 admission and mechanism audit (research/R6) -------------------
    from collections import Counter
    instruction_text = " ".join(text for _, text in _instruction_texts(spec)).lower()
    for index, entry in enumerate(budget):
        if not isinstance(entry, dict):
            continue
        at = f"quality.fragility_budget[{index}] ({entry.get('lever')})"
        if entry.get("route") not in ("b", "c", "d", "e"):
            advisories.append(f"{at}: no route b|c|d|e -- a lever outside the four routes is a noticing trap (q ~ 0)")
        if len(str(entry.get("baseline_wrong_member") or "").strip()) < 15:
            advisories.append(f"{at}: name the member the idiomatic baseline gets wrong (admission test i)")
        if len(str(entry.get("unlabelled") or "").strip()) < 15:
            advisories.append(f"{at}: say why no label, note or marker gives the trap member away (admission test ii)")
        ce = str(entry.get("counterexample") or "")
        if not ce.startswith("baseline_"):
            advisories.append(f"{at}: its counterexample should be the executed idiomatic baseline (id baseline_...)")
        rule_file, evidence_file = entry.get("rule_file"), entry.get("evidence_file")
        if entry.get("route") in ("d", "e") and rule_file and rule_file == evidence_file:
            advisories.append(f"{at}: route {entry.get('route')} needs the rule and its applicability evidence in different documents")
        lever = entry.get("lever")
        if lever == "deep_in_long_document" and fixture is not None:
            sizes = [(fixture / f).stat().st_size for f in entry.get("files") or [] if (fixture / f).is_file()]
            if not sizes or max(sizes) < 30 * 1024:
                advisories.append(f"{at}: deep_in_long_document needs a decisive file of at least 30 KB")
        if lever == "unflagged_document":
            for file in entry.get("files") or []:
                if file.lower() in instruction_text or file.rsplit("/", 1)[-1].lower() in instruction_text:
                    advisories.append(f"{at}: {file} is named in the instruction, so it is not unflagged")
    per_file = Counter(str(entry.get("rule_file") or (entry.get("files") or [""])[0])
                       for entry in budget if isinstance(entry, dict))
    hubs = sorted(f for f, n in per_file.items() if f and n > 2)
    if hubs:
        advisories.append(f"hub file(s) {hubs} hold more than two decisive rules: one read neutralises them all")
    baselines = [e for e in (quality.get("counterexamples") or []) if isinstance(e, dict)
                 and str(e.get("id", "")).startswith("baseline_")]
    if not baselines:
        advisories.append("no executed idiomatic baseline (counterexample id baseline_...): nothing shows a "
                          "literal transcription of the published rules gets any graded member wrong")
    negation = re.compile(r"\b(?:not|never|no other|do not|does not|is not treated as|plays? no part|excluded?|"
                          r"ignore[ds]?|disregard(?:ed)?)\b", re.I)
    for check in spec.get("checks") or []:
        for witness in (check.get("rule_sources") or []) if isinstance(check, dict) else []:
            quote = str(witness.get("quote") or "") if isinstance(witness, dict) else ""
            if negation.search(quote):
                advisories.append(f"check {check.get('id')}: its rule witness negates something "
                                  f"({quote[:80]!r}) -- does the rule name its own exception or decoy?")
                break
    for check in spec.get("checks") or []:
        for witness in (check.get("rule_sources") or []) if isinstance(check, dict) else []:
            words = re.findall(r"[^\W\d_]{3,}", str(witness.get("quote") or "").lower()) if isinstance(witness, dict) else []
            grams = {" ".join(words[i:i + 4]) for i in range(max(0, len(words) - 3))}
            echoed = sorted(g for g in grams if g and g in instruction_text)
            if echoed:
                advisories.append(f"check {check.get('id')}: the instruction echoes its rule witness "
                                  f"({echoed[0]!r}) -- the contract is carrying the HOW")
                break
    # --- v2.2 interlock audit: single mechanisms measured dead (lever lab) ----
    interlocks = 0
    for index, entry in enumerate(budget):
        if not isinstance(entry, dict):
            continue
        at = f"quality.fragility_budget[{index}] ({entry.get('lever')})"
        parts = [p for p in entry.get("levers") or [] if isinstance(p, str)]
        unknown = [p for p in parts if p not in LEVERS]
        if unknown:
            advisories.append(f"{at}: levers {unknown} are not catalogued")
        if len(set(parts)) < 2:
            advisories.append(f"{at}: a single-mechanism decision (measured dead: every single lever was "
                              "solved 10/10 in the lever lab) -- interlock two or more levers on this item")
            continue
        interlocks += 1
        partial = [p for p in entry.get("partial_counterexamples") or [] if isinstance(p, str)]
        missing = [p for p in partial if p not in examples]
        if len(partial) < len(set(parts)):
            advisories.append(f"{at}: {len(partial)} partial-resolution counterexample(s) for "
                              f"{len(set(parts))} interlocked levers -- show each lever missed in turn "
                              "still gives a wrong graded value")
        if missing:
            advisories.append(f"{at}: partial counterexamples {missing} are not in quality.counterexamples")
    if budget and interlocks * 2 < len([e for e in budget if isinstance(e, dict)]):
        advisories.append(f"only {interlocks} of {len(budget)} fragile decisions are interlocks; route most "
                          "graded decisions through two or more levers acting on the same item")
    decisive = {f for entry in budget if isinstance(entry, dict) for f in entry.get("files") or []}
    flagged = sorted(decisive & named_files)
    if flagged:
        advisories.append(f"the instruction names decisive file(s) {flagged}; a deciding fact in a "
                          "file the requester points at is read every time")
    large = 0
    if fixture is not None and fixture.is_dir():
        large = sum(1 for p in fixture.rglob("*") if p.is_file() and p.stat().st_size > 16 * 1024)
    try:
        from .premises import design_shape
        premise_design = design_shape(spec)
    except Exception as exc:                         # noqa: BLE001 -- advisory only
        premise_design = {"error": f"{type(exc).__name__}: {exc}"}
    return {
        "doctrine": "v2.2-2026-10-02",
        "conjunctive_doctrine": "v4-2026-10-13",
        "premise_design": premise_design,
        "interlocks": interlocks,
        "objectives": len(objectives),
        "fragile_decisions": len(budget),
        "per_family": per_family,
        "mechanisms": sorted(mechanisms),
        "files": len(files),
        "files_over_16k": large,
        "instruction_named_files": sorted(named_files),
        "advisories": advisories,
        "note": "advisory only: the 5x2 screen measures difficulty; nothing here blocks",
    }


def as_json(spec: dict, bundle: Path | None = None) -> str:
    return json.dumps(diagnostics(spec, bundle), indent=1, ensure_ascii=False)
