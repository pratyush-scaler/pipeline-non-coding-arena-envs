# Batch 6 v2: inferred, interlocked traps (2026-10-13; overrides the premise rules of AUTHOR-BRIEF-B6)

> **History (2026-10-15).** Superseded as instructions by `AUTHOR-BRIEF-B8.md`; kept for the measurements and reasoning behind its rules. Paths below are the old workspace layout (`$W/research/batch4/...`): in this repo the tools are in `production/tools/`, the briefs in `production/briefs/`, the templates in `production/templates/`, and trap modes come from `production/traps/TRAP-LIBRARY.md`.

Every other rule of `AUTHOR-BRIEF-B6.md` still holds:
- grader shape and weights (premise ≤ 25%, premises ≥ 55%, free ≤ 35%);
- one decision = one check, executed additivity, `ARENA_MISREAD`;
- the 261008/261011 classes, faithfulness, validation and limits.

This document replaces HOW a premise is built. `traps.json` moves to schema `b6/premises/2`, and `design_lint.py` enforces it.

## 0. What is measured dead

13 b6 pilots: 65 premises × 10 runs = 650 premise-runs, **0 misses**, with every answer identical to the reference. Forensics (2 tasks, 15 transcripts) found why:
1. **Both models `cat` the whole fixture before reasoning** (12–19 KB in under 15 s). Salience by placement ("second message", "while I remember", another file) does nothing.
2. **Every trap was a one-step decision on the same record**, so no earlier result was invalidated. Astra spent 92–271 reasoning tokens; Fable typed one answer by hand.
3. **Rules named their own misreading or announced the exception**, e.g. "the code on a slip is a filing aid only, because learners often miscopy", "the date a revision carries is the date it was drafted", "a review in a later stage does not count".
4. **The instruction mapped one field to each trap in the rule's own words**, e.g. "the code under which that choice is recorded under the department's guidelines", `missing_review_hook`, "checked against under the regulation".
5. **The wrong answer took more effort than the right one.** A code-regex parser drops a code-less carried-over row for free, and a register loop includes no-slip learners for free.

Also dead from earlier census work: decoy rows and documents, near-copy documents, stated precedence conflicts, residue, rules placed in the instruction, breadth, and de-leaking by deleting scope sentences.

## 1. What bites (measured in this harness, audited genuine)

They share one shape. **The decisive fact is never stated.** It follows from at least two routine facts in documents of different parties. The agent's default technique (sort printed stamps, key by the printed label, take the routine record's date, take the announced schedule) produces a confident wrong answer. Failing models read the anchor line and never used it.

| code | mechanism | measured |
|---|---|---|
| EVENT | A rule is keyed on event E1 (work finished, goods delivered, form signed). The routine record reports a different event E2 (pick-up, invoicing, filing) for each item. A later incidental message reveals the actual E1 date for 1–3 items. Keep the two event verbs unmistakably distinct. | a-049: Fable 10/10 missed, Astra 4/10 |
| ACTUAL | The deliverable is keyed on what actually happened. A schedule announces; incidental lines elsewhere reveal the deviation, e.g. "thanks for covering my Tuesday group" in a thread about something else. | Fable misses (a-110, a-031) |
| TWIN | One entity appears under two labels differing by one token ("508" vs "S08"; a zero-width joiner vs a space). Identity is resolvable only through a side channel: the same handle, phone, file hash or content. NEVER write a sentence equating them. The default regex keys on the printed label. | a-005: Astra 10/10 (strongest in a fresh step) |
| STORE | A store or register admits only items with property X, stated routinely in an ops or IT note. An item's presence there entails X, contradicting a stale main record. A non-temporal analogue of the store/outage bite. | analogue of a-099: 0/10 both |
| ATTR | A revision is keyed on an attribute the agent's parser drops (a Track column, a category code, a unit field), flipping items it has already judged. | a-031 family: Fable 6/15 |
| BASELINE | A before/after comparison whose "before" period is contaminated by an early start, inferable only from a log entry. | a-031: Fable 3/10, Astra 0/15 |
| SCALE | One export is in thousands, VAT-inclusive, or in another unit. This is never stated, but it is provable because ≥3 items appear in both sources at an exact ratio. | hypothesis (style-A analogue) |
| PARSE | The wrong answer is what the natural parser produces. The right answer needs data the parser throws away: a continuation row carrying the code, a split cell, a second sample on one line. | hypothesis (forensics) |
| CLOCK | Timestamp ordering, at most 1 per task and never the task's heaviest premise. Style A is two unzoned exports (catches Astra); style B is an unzoned chat against zoned e-mail or invite headers (catches Fable). Both use relayed-event anchors ("just posted", "call's in ten"), ≥2 anchors, at least one before and one after the disputed pair, and the neutral sentence "each export's times are the sending system's own clock, which was not re-set during the period". Store/outage counts here too. | a-092 v4 10×2: Fable 0.3, Astra 0.2 |
| HALF | House half-up rounding on an exact half that float AND `Decimal(str(float))` both get wrong, so it needs Fraction or integer arithmetic. Stochastic; give it ≤ 14%. | a-037: 3–5/10 both |
| STATED | A plain stated rule. Allowed only as filler (≤ 1 per task); measured dead. | 0/650 |

## 2. Construction rules (every premise)

1. **Positive, general rules.** A rule states what governs ("the subjects written on a slip decide its code"). Never:
   - its rationale ("because learners often miscopy");
   - the misreading ("not the printed date");
   - an advance warning that an exception exists.

   Keep every scope, exclusion and edge-case sentence. They are meaning, not leaks.
2. **Inferred trigger fact.** The fact that triggers the rule is not stated anywhere as such.
   - It is entailed by ≥ 2 anchors in ≥ 2 different files belonging to different parties.
   - Each anchor is routine and is doing another job.
   - Close every escape with a structural fact ("the tablets had a connection all morning"), never by stating the answer.
   - The anchors must agree, and the answer must hold under every reading they allow, with a wide margin.
   - No single soft anchor. Reviewers rejected "a remark about leaving a hall does not establish an offset" and "an e-mail's send time is not its receipt time".
3. **The default technique fails.** For each premise, name the parser, sort, join or regex the agent will naturally write, and make it produce the wrong answer. The right answer needs a column, line or side channel the default drops.
4. **Neutral instruction.**
   - Field names and descriptions are schema-only: "the code for each slip", "the total for each list", `review_requirement_not_met`.
   - Never "under the guidelines", "as the regulation requires", "checked against", or the rule's own nouns and verbs.
   - No hints in chats or e-mails ("eight plans for nine rows").
   - `design_lint` fails any 5-word run shared between the instruction and a rule quote or anchor.
5. **Interlock (user 2026-10-13: "use a combination of multiple traps").** At least one pair of premises must touch the SAME items, so that resolving one changes the population or record the other works on. Example: the TWIN merge decides which record the EVENT date applies to. Each premise keeps its own independent set- or text-valued check, so partial credit still spreads. An optional combined check may span the pair (it counts toward both premises' shares).
6. **Mix.**
   - Single-step tasks need ≥ 4 premises (5 preferred), at least 3 of them from EVENT / ACTUAL / TWIN / STORE / ATTR / BASELINE / SCALE / PARSE / CLOCK.
   - At least 2 are aimed at Fable-type misses (EVENT, ACTUAL, BASELINE, ATTR, style-B CLOCK) and at least 2 at Astra-type misses (TWIN, STORE, style-A CLOCK, SCALE, PARSE).
   - Each premise comes from a different `family` (the §-list in AUTHOR-BRIEF-B6).
   - Multi-turn tasks need ≥ 2 hard mechanisms per step, and step 2 or 3 carries a re-decision lever: a TWIN restated "by the identifier each source carries", or a backdated authority that silently re-validates a record step 1 voided. Each step's instruction is self-contained (fresh session).
7. **Attribution.** Every check that an inferred decision touches is set- or text-valued, graded order-free or case/space-insensitively. A number or boolean may depend on an inferred decision only if that premise also has its own set/text check.
8. **Determinacy before difficulty.**
   - Write the strongest counter-reading of every premise in VALIDATION.md, with the sentence that defeats it.
   - The clean-gate blind reader must reach the answer.
   - An identical 10/10 miss is treated as ambiguity until a blind reading says otherwise.

## 3. `traps.json` schema `b6/premises/2` (per premise; new fields in bold)

`id, family, step, checks, aimed_at, target_q, resolving_quote{file,text}` (the positive rule), **`mechanism`** (a code from §1), **`anchors`** `[{file,text}, …]` (verbatim, ≥ 2 files for every mechanism except STATED and HALF), **`default_technique`** (the parser/sort/regex that produces the wrong answer), **`interlocks_with`** `[ids]`, `misreading, grounded_in`. Plus `coverage_checks` and `leak_allow`.

`design_lint` checks:
- the mechanism mix and anchor files;
- ≥ 1 reciprocal interlock;
- CLOCK at most once and never heaviest;
- the instruction-echo n-gram test;
- everything it checked before.

## 4. Hardening an existing b6 task (TUNE v2)

1. Keep the scenario, grounding and coverage.
2. Replace every premise that measured 0/10 with a §1 mechanism, unless rewriting its rule positively AND breaking its default technique makes it qualify (then it counts with mechanism PARSE or ATTR).
3. Neutralise the instruction.
4. Build the interlock.
5. Bump to **2.0.0**, archive 1.0.0 to `envs-b6/_versions/`, and re-run design_lint (schema 2), selftest and validate.py.
6. Check the forensics for the task you are hardening: read 2 Fable and 2 Astra pilot transcripts (`pipeline-artifacts/b4/<task>-1.0.0-pilot-<model>/jobs/run/package__*/steps/*/agent/trajectory.json`). Quote, per premise, the line where it was resolved, and say what removes that route.

## 5. Addendum (18:59, measured): ask for the outcome, hide the inference in a silent sub-step

The first v2 pilot (brightwater-spec-qa: TWIN, TWIN, ACTUAL, EVENT, STATED) scored **1.00/1.00, 0/50 misses**. Its deliverable asked for lists of "wrong domain", "wrong figure" and "wrong date", so both models audited exactly the trap. Every anchor read as a correction:
- Fable: "The client's message gives the actual 2025 record as 11,106,164 TEU", "The customs adviser states it entered into force on 1 January 2006", "whose front-desk number matches the partners register";
- Astra: "The client's later message corrects the 2025 port total".

The clock bites of batches 3–4 worked for the opposite reason. The deliverable asked "which instruction governs / what is the final schedule", and the ordering was a sub-step nobody questions. Binding from now on:

1. **Ask for the outcome, never the discrepancy.** No field may be a list of errors, mismatches, wrong items or conflicts that a premise produces. Ask instead for the final register, the total, the schedule, the verdict per item, or the corrected value. The premise must change that outcome through a step the model performs without deliberating:
   - ordering (which statement is later);
   - joining or de-duplicating (which records are one);
   - assuming a unit or scale;
   - assigning an item to a period or version;
   - counting members of a population;
   - picking the price, rule or version that applies.
2. **Anchors never read as corrections.** No anchor may say "actually", "the correct figure is", "states it entered into force", "corrects", "should be", "please update", or an equivalent. An anchor is a side remark doing another job, from which the fact follows by one further inference: arithmetic, a structural constraint, or a relayed event. Measured: failing models read such lines and never use them. Models DO use a line that looks like a correction.
3. **The audited dimension and the trap dimension differ.** If the task is a QA or audit of X (brand names, figures), the premise lives in Y: which version of the spec is current, which strings are in scope, which records are the same entity, which unit a column is in. Y is the step the model does silently on the way to X.
4. **Self-check, written into VALIDATION.md for every premise:**
   - Would a careful agent that reads every file but never asks the question this premise hides get it wrong?
   - Does the instruction or any field name make it ask that question?
   - Does any anchor read as a correction?

   If the answers are not "yes", "no" and "no", redesign.

## 6. Addendum (21:50): external evidence, including our harness class (web research, 2026-10-13)

Three more mechanism codes count as hard. Each is in both the Fable-type and the Astra-type set.

| code | mechanism | evidence |
|---|---|---|
| REVISED | The same series appears in several issues. A LATER document's prior-period column silently restates an earlier figure, e.g. a revised Q2 in the Q3 report. The first-reported figure is repeated elsewhere. Anchor the revision twice: the later issue date plus an "r" flag or the column header. Never write "the latest figure governs" as a hint, though a general convention that the most recent issue governs is fine. | OfficeQA Pro V2, run on Claude Code and Codex with Fable 5 and GPT-5.6: 37.5% at zero tolerance. The named failure is "incorrect temporal reconciliation"; agents "prematurely converge on the first numerically plausible instance". |
| EXEMPLAR | A local convention is evidenced by worked exemplars (prior invoices, last term's sheet, a filed example), never declared. Examples: a mandated lookup table where a formula would be expected; round each line, then sum; banded rates. The model's default formula is off by a small exact amount. | TaxCalcBench: a 15–20 point strict-vs-lenient gap from using a formula instead of the mandated table. RoR-Bench and MATH-Perturb: models "blindly apply learned skills". |
| AGGREGATE | A rule's criterion is a DERIVED aggregate over the item's period or population, never a printed field, e.g. "a merchant whose monthly refund rate exceeds 2%". The default reads a printed status column instead. | DABstep hard split: 13–15% for frontier models; failures concentrate on implicit, derived criteria. |

Also from the research, binding:
- **Design to per-check miss rates.** A simulation of our grader shape gives K = 4–5 independent traps with q 0.30–0.45 and trap weight 0.60–0.70. That yields pass@1 ≈ 0.08–0.18, mean ≈ 0.72–0.81 and about 4 distinct scores per 10 runs.
- **Interlocks cost independence.** At ρ = 0.3, pass@1 rises from 0.18 to 0.28. Keep exactly ONE interlocked pair; every other premise must be independent.
- **Anchor ablation goes in VALIDATION.md for each inferred premise.**
  - Delete one anchor: a blind reader can no longer determine the answer, or the other anchor still settles it alone; state which.
  - Flip an anchor: the reference answer flips.
  - Delete both anchors: the default technique's answer results.
- **No template tells across the batch.** Never reuse a stock sentence. The clock-stability sentence must be reworded per task.
- **Grade one committed value per item.** Hedged multi-answers fail.

## 7. Addendum (22:00, measured on 3 v2 pilots): no anomaly under the default; semantic anchors only

Three v2 pilots: brightwater 1.00/1.00, niche-shelving 1.00/1.00, sandwich-image Fable 4/5 (the miss was on a coverage check; every premise was solved). In each case the model found the trap through an ANOMALY its own script surfaced:
- a phone number that joined two records;
- the same product listed in two extracts at exactly ×2.54;
- drive files with no register row until joined by md5;
- a count that disagreed with a stated header.

Agents investigate whatever does not reconcile. The clock bites left NOTHING to reconcile: sorting by printed stamps gives a clean, complete, consistent wrong answer, and the anchors are remarks ("just posted the link") that no script can compare. Binding:

1. **No anomaly under the default.** Apply the misreading (your `ARENA_MISREAD` path). The resulting deliverable must look complete and internally consistent:
   - no unmatched or leftover rows;
   - no duplicate the default would notice;
   - no stated total, header count, checksum or cross-listing that only the correct reading reconciles;
   - every value in a plausible range.

   Prefer a FALSE MERGE to a missed merge: two different entities the default joins on a shared printed name or code leave nothing visible, while two records of one entity left unjoined leave a visible duplicate. A SCALE whose wrong reading is implausible (a 15 cm wardrobe) is an anomaly; use a scale where both readings are plausible (ex- vs inc-VAT ×1.2, per pack vs per unit).
2. **Anchors are semantic, not mechanical.** An anchor must need its meaning read: a relayed event, a remark about what happened, a structural statement about what a store holds. It must not be a value a script can join, diff, hash or ratio against another file (the same phone, md5, EAN, or a ×2.54 duplicate row). Mechanical links are what scripts surface for free.
3. **Lexically disjoint.** An anchor shares no identifier token (item ID, SKU, code, name as printed in the record) with the record it settles. It names the item by description or by a nickname that a second routine fact ties to the record ("the blue sample for the Mombasa client"; "Ali's order"), so grepping the identifier never finds it. This is also NoLiMa's measured lever: no lexical overlap between question and fact (GPT-4o 99.3 → 69.7 at 32K).
4. **Self-check additions in VALIDATION.md, per premise:**
   - Paste the misread deliverable's consistency check: nothing unmatched, totals tie, values plausible.
   - Show that `grep -i <identifier>` over the fixture does not return the anchor.

## 8. Addendum (22:40, measured): Fable census of §5–§7 v2 pilots

Per mechanism: Fable misses over runs. A premise counts as missed in a run if any of its checks failed. Astra is unmeasured: the OpenAI key was revoked at 22:06.

| mechanism | Fable miss | where it bit |
|---|---|---|
| EXEMPLAR | 12/60 = 0.20 | kibo 5/5 (R$0.50 step shown only in a filed review); suitcase 4/5 (truncation shown only by two worked examples; the guide says just "an integer"); billiard 3/5 (per-hour half-up shown by a leaflet and a filed audit). 0/5 in 9 other instances |
| BASELINE | 2/15 = 0.13 | deck 2/5 |
| TWIN (false merge) | 6/75 = 0.08 | pathway 5/5 (genuineness under audit); spice 1/5 |
| CLOCK (style B) | 1/20 = 0.05 | hammamet 1/5 |
| ACTUAL | 2/70 = 0.03 | billiard 2/5 |
| EVENT, PARSE, ATTR, STORE, REVISED, AGGREGATE, SCALE, HALF, STATED | 0 | 0/10 to 0/65 each |

Tasks with Fable ≤ 0.4 so far: kibo 0/5 and pathway 0/5 (both constant, under audit), suitcase 1/5, billiard 1/5. deck is at 3/5, hammamet and spice at 4/5. Every other task is 5/5.

**Guidance, with small samples, corrected after the 22:45 genuineness audit:**
1. **EXEMPLAR must be BINDING but not POINTED.** Audit of kibo P4: 4/5 Fable runs SAW the R$0.50 step in the filed review and rejected it: "the method documents no such rounding". The method's rule text ("multiply … by the band factor") supported the exact product, so the miss is AMBIGUOUS, not genuine.
   - A half-specified rule plus a non-binding exemplar is an ambiguity recipe. Never build that.
   - Do build: one GENERAL precedent clause in the governing document that names no dimension, e.g. "Where this method does not settle how a figure is worked or written, a new review follows the filed reviews." Then show the specific convention (step, truncation, unit, base) only in a filed example used for something else.
   - That makes the convention binding, with no fair second reading. It also does not point the model at rounding.
   - Close the competing reading explicitly: no rule text may fix the dimension the exemplar governs. Avoid "multiply … to the cent" style rules that already settle it.
2. **Vary the convention domain across tasks** so EXEMPLAR does not become one trap family: rounding step or truncation, the counting unit, the tie-break order, period or week assignment, the base a percentage is computed on.
3. **Pair it with a BASELINE or a false-merge TWIN in the same task.** The aim is several independent ~0.3–0.5 bites, so pass@1 multiplies down.
4. **Pathway P2 (false-merge TWIN) audited GENUINE-leaning.** All 5 runs quoted both anchors and never joined them; four facts defeat the competing reading; a blind reader is pending. This is the "voiced but not joined" pattern: anchors that each look locally explained, but whose join is the answer.
5. **EVENT / STORE / ATTR / PARSE / REVISED / AGGREGATE have bitten Fable 0 times so far.** Keep them as secondary premises, or Astra-aimed until Astra is measured.

## 9. Addendum (23:10, measured): the EXEMPLAR recipe that bites and stays genuine

- kibo 2.1.0 added the general precedent clause ("Where this method does not settle how a figure is worked or written, a new review follows the filed reviews"). Fable then went **5/5**: it read the clause and checked the filed reviews. A clause that sends the reader to the exemplars is still pointing.
- The two EXEMPLAR bites that blind readers confirmed genuine (each scored 1.0 with the grader) had **no precedent clause**:
  - **suitcase:** guide rule 5 says only "percentages as whole numbers". The guide's own worked example (43/331 shown as "12 %") and a filed sample (47/262 as "17 %") fix truncation. Fable missed it 4/5.
  - **billiard:** the rule says "15%, whole roubles". The club-card booklet (1 200 → 181) and the manager's signed 24.10 reconciliation (1 350 → 204) fit only per-hour half-up. Fable missed it 3/5.

**Recipe:**
1. The governing rule states the requirement, but leaves the convention's dimension OPEN without contradicting it: "whole number", "whole roubles", "to the nearest step". Never "to the cent" or "multiply exactly".
2. At least 2 authoritative worked figures fit ONLY the house convention. They must sit inside the governing document itself or in a signed or filed record of the same office. Check that no other convention reproduces both.
3. NO pointer: no precedent clause, no "see the example", no "as in the filed sheets".
4. The blind reader must reach it. Record the uniqueness check, i.e. which alternative conventions fail which example, in VALIDATION.md.

## 10. Addendum (23:25, measured): the keying slip is the strongest lever

Fable census update, all v2 at §5–§9:
- **Keying-slip / false-merge TWIN (pathway pattern):** pathway 2.0.0 5/5 missed, blind-reader confirmed genuine; psychopathy 2.1.0 5/5 missed, a query-log row filed under R11 that belongs to R09, blind read pending.
- **§9 EXEMPLAR:** stochastic, roughly 40% per run. suitcase 4/5, billiard 3/5, lassa 2/5, council 2/5. 0/5 wherever a clause pointed at the exemplar.
- **niche SCALE** (unit provable only from semantic remarks): 5/5 missed, blind-reader confirmed.

**Composition for a hard task:** one keying-slip TWIN plus one or two §9 EXEMPLARs plus a niche SCALE where the domain allows. The keying slip alone puts Fable near 0, and the EXEMPLARs add stochastic spread for partial credit.

**Keying-slip recipe:**
- A record is keyed, filed or labelled under the WRONG identifier: the wrong ID, the wrong reference, the wrong row.
- Two routine anchors, each locally explained and each naming the item only by description, together prove whose it really is.
- The default join on the printed key gives a complete, consistent answer, with no strays and no unmatched rows.

## 11. Addendum (23:45, measured): three ambiguity shapes that blind readers and audits rejected

Each produced Fable "misses" that were NOT genuine:
1. **The rule text supports the default** (kibo 2.0.0). "Multiply … to the cent" defeats a rounding exemplar.
2. **Exemplars from another module or an older rule set** (eco-guard 2.1.0). The blind reader rejected sheets that "predate Procedure v2.1, are from another year or module".
3. **A stated rule against a third-party fact, with no governing statement** (mustangs 2.0.0 P7). Handbook 3.1 says "plan from the availability notes"; the bulletin says class is cancelled. Nothing says which governs, so 5/5 runs saw both and split.

**Rule:** where a premise sets a stated rule or note against inferred facts, the stated text must itself be scoped so that the inferred fact decides it. Example: "on Sundays when class meets", not "Sundays". Never rely on the reader preferring the inference.

## 12. Addendum (23:55, forensics on 5 keying slips): what makes a slip bite, and what keeps it clean

**Bit** (pathway, psychopathy, ktp) vs **solved** (laptop, ats):
- **Solved slips clashed visibly with another structured field.** The ats row overlapped the education export; laptop's sentence contradicted itself.
- **Bitten slips fit their wrong key:** the row fills a blank, dates stay in sequence, the topic matches.
- **Solved anchors were corrective or exclusive:** "straight from campus", "its only one in the city". Bitten anchors were by-the-way remarks naming items by paraphrase.
- **Solved slips graded a field that prints the slipped row's own content.** Bitten ones graded a downstream consequence: a date, a code, follow-up membership.
- **The wrong owner had a rule-sanctioned disposition** (follow-up, not_determinable) and a legitimate peer showing the same surface anomaly.

**VALIDITY WARNING, under adjudication (23:55):** in psychopathy and ktp, Fable explicitly deferred to a governing sentence that makes the filing record look authoritative ("a code entered … for that record is the setting"; "the class journal records each lesson on the day it takes place"). If that sentence literally binds the printed key, Fable's reading is FAIR and the bite is ambiguity (§11 shape 1).

**Rule:** the governing text must state the true rule on the real-world fact, e.g. "the date the lesson was held" or "the setting reported in the study's own full text". Any record-practice sentence must be descriptive, never binding the printed key over the real fact. No anti-inference clause may forbid the evidence that settles identity.

## 13. Addendum (2026-10-14 00:55, measured): cleaned slips and the confirmed set

- **psychopathy and ktp, after the binding sentence was fixed (2.2.0): Fable 5/5 solved both.** Their 2.1 bites were the ambiguity named in §12, not difficulty. A clean slip has to bite through the subtlety of its anchors, never through text that binds the printed key.
- **feast 1.1.0: two independent Opus readers kept the printed "Class: 8A" label.** One cited a later dated note consistent with it. Before shipping, check every dated note on the slipped item; none may support the printed label. The same task's exemplar failed §9.1: the rule "the time all the segments take together" supports the default.
- **Confirmed genuine on Fable (blind reader 1.0):** pathway 2.0, niche 1.1, suitcase 2.0, billiard 2.0, melody 1.0, killzone 1.1, line-colour 1.0, moot 2.1 (multi-turn), kibo 2.3, lassa 1.1, profile-copy 2.1. Astra is unmeasured on all of them as of 00:48 (OpenAI key restored; reruns in flight).
- **New Fable misses awaiting a blind reader:** home-bp 2.2 0/5, probation 2.2 1/5, moisturiser 2.2 2/5, pupil-tracker 1.1 2/5 (all keying slips), council 1.2 0/5 (lead offset).

## 14. Addendum (2026-10-14 02:15): a blind reader's 1.0 is necessary, not sufficient

niche 1.1: the blind reader scored 1.0, but 9/10 Fable final runs gave the same wrong verdict for a STATED reason. A fixed element covered by a clearance rule had no clearance on file. The reason was defensible, so the miss was ambiguity. **Rule:** for every check missed identically in ≥ 70% of a model's runs, read the dominant wrong answer's stated rationale in the trajectories and adjudicate it on its own terms. Whether some reader reached the reference does not settle it. Every rule that applies to a product (clearance, fixed parts, dimensions) needs its inputs on file for every product it can touch.

## 15. Addendum (2026-10-14 03:10): audits with §14 knock out most "both-hard" results

Six audits so far: niche, line-colour, deck, brightwater, melody and the first pass over the record list. Most "Fable-hard" results were NOT the planned trap.
- **niche:** a missing floor-pipe clearance. With it fixed, Fable went 5/5.
- **line-colour:** a line label that is in no file.
- **brightwater:** a "within" exemplar outside the rule's scope.
- **melody:** an unscoped late-pre-test decision.
- **deck:** a grader cascade (P2 → P3).

**Genuine bites confirmed so far:**
- Astra misses keying slips whose row fits its key (deck N8, melody Joy) and truncation exemplars (deck, brightwater P4).
- Fable misses only a few keying slips: kibo, pathway, home-bp, probation and timesheet, all pending audit.

**Rules:**
1. Every graded decision needs a governing sentence that scopes it. A "rule governs X" sentence does not decide Y.
2. Exemplars must sit in documents the rule binds.
3. Every downstream check must use the agent's own upstream answer.
4. Run the §14 audit BEFORE calling a task both-hard.

