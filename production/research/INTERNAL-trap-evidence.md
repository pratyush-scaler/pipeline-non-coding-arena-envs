# Internal trap evidence: which mechanisms actually bit, per model

Built 2026-10-15 from our own calibration campaigns. Harness: **Fable 5.1** (`anthropic/claude-fable-5-1`) in Claude Code and **GPT-6 Astra** (`openai/gpt-6-astra`) in Codex, both at high effort with no turn or time limits. Read-only: nothing was launched.

- **Scope:** 1129 task-version-premise units across 45 tasks. All have a `premises[]` premise map, so they are batch 6 (B6v1 to B6v5). Fable was measured on all 1129 units and Astra on 606. Astra is missing on 523 units because those campaigns voided (revoked keys on 10-12/10-13 and again in the v5 round 2).
- **Runs:** 7805 Fable premise-runs and 4880 Astra premise-runs, from valid trials only. A premise-run is one valid trial scored on one premise.
- **Machine-readable copy:** `INTERNAL-trap-evidence.csv` (same folder), one row per (task, version, premise, model).

## Key findings

1. **Stated rules never bite.** Premises whose rule and trigger are stated outright were missed **0/810** times by Fable and **0/720** times by Astra. These are the B6v1 premises plus every premise coded STATED. Every bite in this table comes from an inferred trigger fact.
2. **Two mechanisms meet the strict both-model bar.**
   - **Keying slip, true owner only by description:** missed by at least 30% on both models in 10 audited-genuine tasks.
   - **Rounding convention from worked figures:** the same, but in only 2 audited tasks, one of them GENUINE-soft.
   - Even these are fragile:
     - The audited both-model slips were often **flat**: 10 of the 19 audited units were missed at least 90% by Fable, 5 of them at least 90% by both models.
     - Small route edits flip a slip from about 90-100% to 0% (cnc P3, gst P4); an ambiguity fix did the same to probation P4.
     - On Astra, the rounding convention flips on the number and placement of discriminating figures (profile-copy P5, deck P4).
3. **Fable-only mechanisms (one audited task each):**
   - tax-inclusive price shown only by an indirect cue (gst P3: Fable 52/80 missed, Astra 0/75);
   - item already in hand, inferred from two incidental remarks (cnc P5: Fable 24/40, Astra 0/40);
   - unit scale shown only by incidental remarks (profile-copy P7: Fable 57/65, Astra 0/65);
   - rounding conventions whose figures sit in non-governing documents (suitcase P2, billiard P4, spice P4).
4. **Astra-only mechanisms:**
   - a truncation convention shown only by one or two worked figures outside the rule being applied (brightwater P4: Astra 13/15, Fable 1/15; gst P2 1.7.0: Astra 10/15, Fable 0/15);
   - a slip whose filed column is copied without deliberation (deck N8: Astra 60/60 over 6 measured versions 2.2-2.7, Fable 5/60);
   - a line transposition settled by first-hand descriptions (melody P2: Astra 14/15, Fable 1/15).
5. **Dead mechanisms (at most 5% missed by both models over 20+ runs each):**
   - event-date keying, population reshaping, caption-only rules, near-twin identities, stored-vs-derived figures, coverage omissions;
   - restated figures, first-hand fact over record, answerability, baselines, stacked-rule order, and changed premises.
   - Every one is under 5% on both models.
6. **Many high miss rates were ambiguity.** Removing an ambiguity took a 100% or 80% bite to 0% six times:
   - niche P1 Fable 15/15 to 0/5; probation P4 Astra 5/5 to 0/5; melody P3 12/15 to 0/5;
   - moot P10 5/5 to 0/5; kibo P4 5/5 to 0/5; profile-copy P8 10/10 to 0/10.
   - Any unaudited 100% should be presumed ambiguous until a section-14 audit or a blind reader says otherwise.
7. **The dial is not monotone at n=5.** The same premise text, unchanged between versions, measured very differently on Fable:
   - home-bp P3: 2/5 vs 5/5;
   - timesheet P4: 7/15 vs 5/5;
   - pathway P2: 10/15 vs 2/5;
   - profile-copy P6: 3/5, 2/5 and 5/5.
   - Unrelated edits elsewhere in a task can move a premise: gst P1 fell from 6/10 to 0-1/5 when a new note was placed beside its anchor.

## 1. Headline lists

These rules apply to every list:
- A unit is one (task, version, premise).
- "Both-model" needs at least 5 valid runs on each model.
- A rate is a miss rate (share of valid runs that failed any check of the premise).
- A unit with fewer than 10 runs on a model is **provisional**.
- Verdicts come from `research/batch4/b6/genuineness.md`:
  - GENUINE and GENUINE-soft are section-14 audits.
  - BLIND-1.0 means an Opus blind reader reached the reference with the shipped grader, but no audit was recorded. Treat it as provisional genuine.
  - AMBIGUOUS and DEFECT units are excluded from every claim of genuineness.

### (a) At least 30% missed on BOTH models in 2 or more tasks, audited genuine

**ID.slip: Keying slip: record filed under the wrong ID, true owner only by description.** 10 audited tasks: ats-embedded-screening-register, cafe-kitchen-schedule-revisions, cnc-router-bom-reconcile, coloring-book-retitle-audit, gst-workbook-answer-key, home-bp-diary-summary, kibo-budget-cap-review, pathway-choice-audit, suitcase-cover-matrix-check, timesheet-overtime-review.

- ats-embedded-screening-register 1.1.0 P2: F 15/15, A 15/15, GENUINE
- coloring-book-retitle-audit 2.3.0 P2: F 13/15, A 9/15, GENUINE
- coloring-book-retitle-audit 2.3.0 P5: F 7/15, A 9/15, GENUINE
- coloring-book-retitle-audit 2.3.0 P8: F 8/15, A 5/15, GENUINE
- gst-workbook-answer-key 1.3.0 P1: F 12/15, A 11/15, GENUINE
- gst-workbook-answer-key 1.4.0 P1: F 11/15, A 12/15, GENUINE
- gst-workbook-answer-key 1.4.0 P4: F 12/15, A 10/15, GENUINE-soft
- gst-workbook-answer-key 1.4.1 P1: F 11/15, A 8/15, GENUINE
- gst-workbook-answer-key 1.4.1 P4: F 13/15, A 5/15, GENUINE-soft
- home-bp-diary-summary 2.2.0 P3: F 15/15, A 12/15, GENUINE
- home-bp-diary-summary 2.2.1 P3: F 15/15, A 11/15, GENUINE
- kibo-budget-cap-review 2.3.0 P3: F 15/15, A 13/15, GENUINE
- kibo-budget-cap-review 2.3.1 P3: F 15/15, A 11/15, GENUINE
- suitcase-cover-matrix-check 2.1.0 P5: F 14/15, A 15/15, GENUINE
- suitcase-cover-matrix-check 2.1.1 P5: F 14/15, A 14/15, GENUINE
- timesheet-overtime-review 2.2.0 P4: F 12/15, A 15/15, GENUINE
- cafe-kitchen-schedule-revisions 2.1.1 P10: F 15/15, A 11/15, GENUINE
- cnc-router-bom-reconcile 2.3.0 P3: F 15/15, A 15/15, GENUINE
- pathway-choice-audit 2.0.0 P2: F 15/15, A 15/15, GENUINE
- Blind-reader-only (provisional): moisturiser-price-screen 2.2.0 P4: F 12/15, A 5/15, BLIND-1.0; mustangs-tryout-roster 2.1.0 P10: F 3/5, A 5/5, BLIND-1.0 (provisional); mustangs-tryout-roster 2.1.0 P11: F 3/5, A 5/5, BLIND-1.0 (provisional); psychopathy-evidence-screen 2.3.0 P4: F 6/15, A 11/15, BLIND-1.0
- Excluded as AMBIGUOUS or DEFECT: coloring-book-retitle-audit 2.2.0 P2: F 15/15, A 15/15, AMBIGUOUS; coloring-book-retitle-audit 2.2.0 P5: F 15/15, A 15/15, AMBIGUOUS; coloring-book-retitle-audit 2.2.0 P8: F 15/15, A 15/15, AMBIGUOUS; line-colour-census 1.0.0 P2: F 5/15, A 9/15, DEFECT; probation-answer-key 2.2.0 P4: F 10/15, A 15/15, AMBIGUOUS; cafe-kitchen-schedule-revisions 2.1.0 P10: F 15/15, A 13/15, AMBIGUOUS

**CV.round: Rounding convention (cut vs half-up) from worked or filed figures.** 2 audited tasks: deck-preread-review, profile-copy-claims-audit.

- profile-copy-claims-audit 2.1.0 P5: F 14/15, A 15/15, GENUINE-soft
- profile-copy-claims-audit 2.2.0 P5: F 14/15, A 14/15, GENUINE-soft
- profile-copy-claims-audit 2.3.0 P5: F 12/15, A 12/15, GENUINE-soft
- profile-copy-claims-audit 2.4.0 P5: F 14/15, A 14/15, GENUINE-soft
- deck-preread-review 2.2.0 P4: F 12/15, A 15/15, GENUINE
- deck-preread-review 2.3.0 P4: F 10/15, A 15/15, GENUINE
- Blind-reader-only (provisional): lassa-kap-results-sheet 1.1.0 P4: F 8/15, A 6/15, BLIND-1.0

How to read (a):
- **Keying slip.** Of the 19 audited both-model units, 10 were missed at least 90% by Fable, and 5 at least 90% by both models. Only these 6 were in the 30-80% band on both models:
  - coloring 2.3.0 P5;
  - coloring 2.3.0 P8;
  - gst 1.3.0 P1;
  - gst 1.4.0 P1;
  - gst 1.4.0 P4;
  - gst 1.4.1 P1;
  - The mechanism bites both models, but often as a flat lever at 90% or more.
- **Rounding convention.** Only 2 tasks qualify:
  - deck P4 is GENUINE;
  - profile-copy P5 is GENUINE-soft: "one decimal place" plausibly reads as ordinary rounding.
  - lassa P4 (Fable 8/15, Astra 6/15) has only a blind reader.
  - Treat the mechanism as **weakly established**.

Single-task both-model mechanisms. Promising, but they fail the 2-task bar:
- **T.edition: Which edition or version applies, by the real receipt / effective date.** cafe-kitchen-schedule-revisions 2.1.0 P1: F 15/15, A 15/15, GENUINE; cafe-kitchen-schedule-revisions 2.1.0 P6: F 15/15, A 15/15, GENUINE; cafe-kitchen-schedule-revisions 2.1.1 P1: F 15/15, A 15/15, GENUINE; cafe-kitchen-schedule-revisions 2.1.1 P6: F 15/15, A 15/15, GENUINE.
- **Q.pack: Per-pack / per-pair pricing or box composition.** cnc-router-bom-reconcile 2.3.0 P4: F 15/15, A 15/15, GENUINE-soft; cnc-router-bom-reconcile 2.6.0 P4: F 14/15, A 11/15, GENUINE; cnc-router-bom-reconcile 2.6.1 P4: F 15/15, A 9/15, GENUINE.
  - cafe P1/P6 is the "which edition by real receipt date" trap. The edition was decided by a brief dated only through a frame-replacement remark.
  - cnc P4 is per-pair pricing: one price covers two bearings or supports, shown only by filed order lists and a receipt tally.
- **ID.swap (pupil P2 1.1.0):** Fable 9/15, Astra 7/15, blind reader only.

### (b) Fable-only mechanisms

Criteria: Fable missed at least 30%, Astra at most 10%, both measured at the same version.

| mechanism | audited Fable-only evidence | other evidence | strength |
|---|---|---|---|
| Q.taxincl: tax-inclusive basis, indirect cue | gst P3 1.3.0-1.7.0: F 46/60, A 0/60 (GENUINE) | suitcase P7 2.4/2.5 (VAT-inclusive matrix price): F 10/10, Astra unmeasured, UNCONFIRMED (every miss noticed the cue and rejected it). student P3 (tax-exclusive quote): F 0/15, A 0/10 | 1 audited task |
| S.inhand: already in hand, inferred | cnc P5 2.6.0/2.6.1 (controller kit already raising Bayu's FluidNC network): F 19/30, A 0/30 (GENUINE) | kibo P5 (commander already owned): Fable 0/15 in both stated and inferred forms. blockprint P2 (stock in the lock-up): 0/10 | 1 audited task; dead in the other 2 |
| Q.scale: scale only from incidental remarks | profile-copy P7 2.4.0 (plays in thousands): F 15/15, A 0/15 (GENUINE). 2.2/2.3 were AMBIGUOUS | melody P3 (pre-test out of 20) was AMBIGUOUS. deck P1 (thousands of birr): 0/30 both in every form. ats P3, coop P4 and current-affairs P3: 0 | 1 audited task |
| CV.round, figures outside the governing text | suitcase P2 2.1.x: F 11/30, A 0/30 (GENUINE). home-bp P4 2.2.x: F 7/30, A 0/30 (GENUINE, below 30%) | billiard P4: F 6/10, A 0/10 (blind). spice P4 2.2/2.3: F 7/10, A 0/10. killzone P4 1.2.0: F 5/5, A 0/5. okra P6 and eco P3 2.3.0: F 3/5, A 0/5 | many tasks, mostly provisional |
| ID.slip, Fable-only shapes | profile-copy P6 (client film keyed into the show's playlist): F 44/45, A 0/45 (GENUINE). cnc P3 2.6.x (dispatch line vs first-hand log): F 28/30, A 2/30 (GENUINE) | spice P3: F 6/10, A 0/10 | 2 audited tasks |
| CV.method: HSV saturation from filed examples | line-colour P1 1.0.0: F 14/15, A 1/15 (blind only); 1.2.0: F 5/5, A 0/5 (section-14 audit still needed) | moot heading-number word counts: AMBIGUOUS | provisional |
| T.clock: unzoned chat clock | killzone P1: F 6/10, A 0/10 (blind only). hammamet P3 2.2.0: F 3/5, A 0/5 | timesheet P2 0/75 and kibo P2 0/100 (both models) | provisional; mostly dead |
| E.actual: first-hand fact over record | billiard P3 (table actually free at 15:27): F 4/10, A 0/10 (blind only) | 28 of the 30 E.actual Fable units are 0 (the other two are billiard P3) | provisional |
| T.changed | cafe P8 (door now opens outward): F 7/30, A 0/30 (GENUINE, below 30%) | 37 of 41 Fable units: 0 | weak |

### (c) Astra-only mechanisms

Criteria: Astra missed at least 30%, Fable at most 10%, both measured.

| mechanism | audited Astra-only evidence | other evidence | strength |
|---|---|---|---|
| CV.round: truncation fixed by 1-2 discriminating figures, at least one outside the governing rule | brightwater P4 1.3.0: A 13/15, F 1/15 (GENUINE). gst P2 1.7.0 (one discriminating figure): A 10/15, F 0/15 (GENUINE) | gst P2 1.5.0/1.6.0: A 5/10. deck P4 2.4.0 (one figure in the standard): A 5/5, F 1/5; with two figures (2.5.0) A 3/15. profile-copy P5: A 14/15 with two figures, **0/5 once a third figure sat inside the governing entry** | 2 audited tasks |
| ID.slip: filed column copied without deliberation | deck P2 (N8 filed under S-25): A 60/60 over 2.2-2.7, F 5/60 (GENUINE at 2.2/2.3) | niche P3 1.1.0: A 10/15, F 1/15. student P2 2.2.0: A 4/5, F 0/5. ethics P1: A 3/5, F 0/5. refurb P5 1.4.0: A 4/5, F 0/5. gst P1 1.7.0: A 12/15, F 3/15 (GENUINE-soft; Astra "escapes" through not_determinable) | 1 audited task plus several provisional |
| ID.swap: transposed lines settled by first-hand descriptions | melody P2 1.1.0: A 14/15, F 1/15 (GENUINE) | melody 1.2.0: A 5/5, F 1/5 | 1 audited task |
| Q.scale | (none audited) | niche P1 1.3.0 (inches, after its ambiguity was fixed): A 4/5, F 0/5 | provisional |
| CV.method: clarification-only footnotes excluded | moot P13/P15 2.1.0: A 8/10, F 0/10 (blind only) | moot P15 2.2.0: A 2/5 | provisional |

### (d) Dead mechanisms

Criteria: pooled miss rate at most 5% on both models, with at least 20 runs on each model. The pooled rates include every version.

| mechanism | Fable | Astra | units that bit anyway (at least 30%) |
|---|---|---|---|
| CV.order: Stacked rules applied in the wrong order | 0/25 (0%) | 0/20 (0%) | - |
| CV.stated: Rule or convention stated outright | 0/115 (0%) | 0/55 (0%) | - |
| E.stored: Stored or repeated figure vs the derivation the rules require | 0/115 (0%) | 1/90 (1%) | - |
| ID.twin: Near-twin identities (namesakes, same-titled items; false merge/split) | 0/245 (0%) | 1/150 (1%) | - |
| Q.aggregate: Aggregate / composition totals that tie but are wrong (provisional: Astra n<20) | 0/45 (0%) | 0/10 (0%) | - |
| S.answer: Determinable vs not determinable | 0/75 (0%) | 1/35 (3%) | - |
| S.coverage: Counting unit / coverage (what counts as one item; silent omissions) | 0/125 (0%) | 0/60 (0%) | - |
| T.revised: Restated figure supersedes the first issue | 0/125 (0%) | 0/65 (0%) | - |
| T.event: Event date = when it really happened, not the record or upload date | 3/405 (1%) | 2/185 (1%) | council P1 1.1.0 F 2/5 (no Astra) |
| E.actual: First-hand actual fact overrides the filed record | 4/215 (2%) | 3/105 (3%) | billiard P3 F 4/10, A 0/10 (blind reader only); refurb P6 1.4.0 A 3/5, F 0/5 |
| S.population: Population reshaped by an incidental fact (who or what is in scope) | 13/515 (3%) | 10/280 (4%) | profile-copy P8 2.5/2.6 F 10/10 A 10/10 (AMBIGUOUS as built; 0/10 on each model after the 2.7 fix); mustangs P7 2.0.0 F 3/5 (AMBIGUOUS) |
| S.baseline: Baseline / comparison-period choice | 6/230 (3%) | 0/185 (0%) | deck P1 2.0/2.1 F 6/10 (2.1.0 AMBIGUOUS; 0/30 both after the fix) |
| CV.caption: Rule that lives only in a caption, table note or footnote | 8/255 (3%) | 0/195 (0%) | deck P5 2.5.0 (N9 note via caption): F 5/15, A 0/15 |
| T.changed: Changed premise mid-stream invalidates an earlier status | 12/260 (5%) | 0/140 (0%) | cafe P8 2.2.0 F 3/5 |
| CV.method: other conventions from examples (dead **once AMBIGUOUS units are excluded**) | 76/995 (8%); clean 30/940 (3%) | 47/630 (7%); clean 24/585 (4%) | line-colour P1 HSV (Fable-only, blind); moot P13/P15 (Astra-only, blind) |
| T.clock: clock offset (near-dead) | 11/195 (6%) | 16/105 (15%); clean 1/90 (1%) | killzone P1, hammamet P3 (Fable) |

Also dead:
- **Every stated premise:** Fable 0/810 and Astra 0/720, consistent with the B6 note "stated rules dead 650/650".
- **Most new trap designs in the v5 rounds:**
  - kibo P5 scope: Fable 0/15;
  - ats P5 scope: Fable 0/15;
  - timesheet P5 payroll period: Fable 0/25;
  - pathway P4 and P5: Fable 0/25 and 0/25;
  - deck P1 thousands: 0/30 on both models;
  - coloring spine with one figure: Fable 0/25.

### (e) Bimodal mechanisms

Mechanisms whose units sit at 0% or 100% far more often than in the 20-80% band (units with at least 5 runs):

| mechanism | Fable units: 0% / in band / 100% | Astra units: 0% / in band / 100% |
|---|---|---|
| Q.pack: Per-pack / per-pair pricing or box composition | 5 / 1 / 4 of 11 | 3 / 2 / 3 of 8 |
| Q.taxincl: Tax-inclusive (or exclusive) basis with an indirect cue | 7 / 4 / 3 of 15 | 9 / 0 / 0 of 9 |
| T.edition: Which edition or version applies, by the real receipt / effective date | 26 / 2 / 4 of 32 | 8 / 0 / 2 of 10 |
| ID.slip: Keying slip: record filed under the wrong ID, true owner only by description | 67 / 46 / 28 of 150 | 36 / 25 / 17 of 84 |
| S.inhand: Scope: already in hand / owned / in stock | 5 / 4 / 0 of 9 | 4 / 0 / 0 of 4 |
| Q.scale: Unit / scale / number format (thousands, raw marks, h.mm, inches) | 53 / 7 / 4 of 64 | 34 / 1 / 1 of 36 |
| CV.round: Rounding convention (cut vs half-up) from worked or filed figures | 93 / 46 / 3 of 150 | 67 / 10 / 4 of 85 |

Dial-driven flips: the same premise, only a dial sentence changed, and the rate jumped by at least 0.8.
- **profile-copy P5, Astra:** 14/15 (2.4.0) to 0/5 (2.5.0) after one worked figure was added inside the entry that defines the graded rate. It never came back in 2.6-2.8 (0/15).
- **cnc P3, both models:** 15/15 (2.3.0) to 0/5 (2.4.0/2.5.0), from one descriptor ("tergulung diikat kawat").
  - With a weaker route (2.6.0, "gantung di kait") it went to Fable 14/15 and Astra 1/15.
- **home-bp P5, Fable:** 0/10 when the reprint was dated (2.4.0/2.5.0), then 5/5 and 5/5 when it was inferred (2.6.0/2.7.0).
  - The blind reader also missed it. The printed form rule beat the incidental facts.
- **suitcase P7 VAT, Fable:** 0/10 with the caption (2.2.0/2.3.0), then 5/5 and 5/5 when inferred (2.4.0/2.5.0).
  - Every miss noticed the cue and rejected it.
- **gst P4, Fable:** 13/15 (1.4.1) to 0/5 (1.5.0), from one "lorry up from Hubballi" note.
- **gst P1, Fable:** 11/15 (1.4.1) to 0/5 (1.5.0) with **byte-identical P1 text**. It was primed by the new P4 note placed next to its anchor.
- **gst P3, Fable:** 10/15 (1.4.1) to 1/5 and 0/5 (1.5.0/1.6.0, "a single figure on each line"), then back to 11/15 (1.7.0, "same rates as our counter board").
- **deck P4, Astra:** 5/5 with one figure in the standard (2.4.0), 3/15 with two (2.5.0).
- **Astra flips more completely than Fable.**
  - Units at exactly 0% or 100%: Astra 53 of 84 keying-slip units and 71 of 85 rounding units; Fable 95 of 150 and 96 of 150.
  - In the dial pilots, Astra was 0/5 or 5/5 almost every time.

## 2. Mechanism rollup

Each premise is grouped by what the misreading is, not by its `family` label: family labels were reused loosely. The two misses columns pool every version and stage. "Clean" drops units with an AMBIGUOUS or DEFECT verdict. The band and constant columns count task-version units with at least 5 runs on that model; premises of the same mechanism in one task-version are pooled. Tasks columns list distinct tasks with a verdict of that kind for a premise of this mechanism.

| mechanism | tasks | premise-versions | Fable misses | Astra misses | Fable clean | Astra clean | Fable units in 20-80% band | Fable units at 0% / 100% | Astra units in 20-80% band | Astra units at 0% / 100% | GENUINE(-soft) tasks | BLIND-1.0 only | AMBIGUOUS / DEFECT tasks |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| **ID.slip** Keying slip: record filed under the wrong ID, true owner only by description | 41 | 194 | 655/1520 (43%) | 475/1045 (45%) | 40% | 41% | 46/150 (31%) | 67 / 28 | 25/84 (30%) | 36 / 17 | 12: ats-embedded-screening-register, cafe-kitchen-schedule-revisions, cnc-router-bom-reconcile, coloring-book-retitle-audit, deck-preread-review, gst-workbook-answer-key, home-bp-diary-summary, kibo-budget-cap-review, pathway-choice-audit, profile-copy-claims-audit, suitcase-cover-matrix-check, timesheet-overtime-review | 5 | 8 |
| **CV.round** Rounding convention (cut vs half-up) from worked or filed figures | 38 | 170 | 216/1260 (17%) | 143/830 (17%) | 16% | 16% | 46/150 (31%) | 93 / 3 | 10/85 (12%) | 67 / 4 | 7: brightwater-spec-qa, cafe-kitchen-schedule-revisions, deck-preread-review, gst-workbook-answer-key, home-bp-diary-summary, profile-copy-claims-audit, suitcase-cover-matrix-check | 5 | 4 |
| **CV.method** Other method convention from worked or filed examples | 29 | 139 | 76/995 (8%) | 47/630 (7%) | 3% | 4% | 9/90 (10%) | 79 / 1 | 5/41 (12%) | 33 / 1 | 0 | 3 | 4 |
| **T.event** Event date = when it really happened, not the record or upload date | 25 | 65 | 3/405 (1%) | 2/185 (1%) | 1% | 1% | 2/64 (3%) | 62 / 0 | 0/22 (0%) | 20 / 0 | 0 | 1 | 0 |
| **S.population** Population reshaped by an incidental fact (who or what is in scope) | 23 | 79 | 13/515 (3%) | 10/280 (4%) | 1% | 2% | 1/66 (2%) | 63 / 2 | 0/34 (0%) | 32 / 2 | 0 | 3 | 2 |
| **CV.caption** Rule that lives only in a caption, table note or footnote | 21 | 41 | 8/255 (3%) | 0/195 (0%) | 3% | 0% | 4/38 (11%) | 34 / 0 | 0/28 (0%) | 28 / 0 | 0 | 1 | 0 |
| **Q.scale** Unit / scale / number format (thousands, raw marks, h.mm, inches) | 19 | 66 | 89/480 (19%) | 19/320 (6%) | 7% | 2% | 7/64 (11%) | 53 / 4 | 1/36 (3%) | 34 / 1 | 1: profile-copy-claims-audit | 0 | 3 |
| **T.changed** Changed premise mid-stream invalidates an earlier status | 17 | 44 | 12/260 (5%) | 0/140 (0%) | 5% | 0% | 3/41 (7%) | 37 / 0 | 0/19 (0%) | 19 / 0 | 1: cafe-kitchen-schedule-revisions | 0 | 0 |
| **ID.twin** Near-twin identities (namesakes, same-titled items; false merge/split) | 16 | 45 | 0/245 (0%) | 1/150 (1%) | 0% | 1% | 0/34 (0%) | 34 / 0 | 0/19 (0%) | 18 / 0 | 0 | 1 | 0 |
| **E.stored** Stored or repeated figure vs the derivation the rules require | 14 | 23 | 0/115 (0%) | 1/90 (1%) | 0% | 1% | 0/20 (0%) | 20 / 0 | 1/15 (7%) | 14 / 0 | 0 | 0 | 0 |
| **S.coverage** Counting unit / coverage (what counts as one item; silent omissions) | 14 | 25 | 0/125 (0%) | 0/60 (0%) | 0% | 0% | 0/22 (0%) | 22 / 0 | 0/11 (0%) | 11 / 0 | 0 | 0 | 0 |
| **CV.stated** Rule or convention stated outright | 13 | 21 | 0/115 (0%) | 0/55 (0%) | 0% | 0% | 0/21 (0%) | 21 / 0 | 0/9 (0%) | 9 / 0 | 0 | 0 | 0 |
| **T.edition** Which edition or version applies, by the real receipt / effective date | 12 | 38 | 89/270 (33%) | 60/115 (52%) | 33% | 52% | 2/32 (6%) | 26 / 4 | 0/10 (0%) | 8 / 2 | 1: cafe-kitchen-schedule-revisions | 0 | 0 |
| **T.revised** Restated figure supersedes the first issue | 12 | 17 | 0/125 (0%) | 0/65 (0%) | 0% | 0% | 0/17 (0%) | 17 / 0 | 0/5 (0%) | 5 / 0 | 0 | 0 | 0 |
| **E.actual** First-hand actual fact overrides the filed record | 11 | 33 | 4/215 (2%) | 3/105 (3%) | 2% | 3% | 2/30 (7%) | 28 / 0 | 1/13 (8%) | 12 / 0 | 0 | 1 | 0 |
| **S.answer** Determinable vs not determinable | 8 | 15 | 0/75 (0%) | 1/35 (3%) | 0% | 3% | 0/13 (0%) | 13 / 0 | 1/5 (20%) | 4 / 0 | 0 | 0 | 0 |
| **S.baseline** Baseline / comparison-period choice | 6 | 28 | 6/230 (3%) | 0/185 (0%) | 1% | 0% | 2/28 (7%) | 26 / 0 | 0/19 (0%) | 19 / 0 | 0 | 0 | 1 |
| **T.clock** Clock or time-zone offset between sources | 6 | 27 | 11/195 (6%) | 16/105 (15%) | 6% | 1% | 5/27 (19%) | 22 / 0 | 1/11 (9%) | 9 / 1 | 0 | 1 | 1 |
| **Q.aggregate** Aggregate / composition totals that tie but are wrong | 5 | 9 | 0/45 (0%) | 0/10 (0%) | 0% | 0% | 0/9 (0%) | 9 / 0 | 0/2 (0%) | 2 / 0 | 0 | 0 | 0 |
| **CV.order** Stacked rules applied in the wrong order | 4 | 5 | 0/25 (0%) | 0/20 (0%) | 0% | 0% | 0/5 (0%) | 5 / 0 | 0/4 (0%) | 4 / 0 | 0 | 0 | 0 |
| **ID.swap** Row or cell transposition between two records | 4 | 10 | 13/70 (19%) | 26/65 (40%) | 19% | 40% | 2/7 (29%) | 3 / 0 | 2/6 (33%) | 3 / 0 | 1: melody-lesson-results | 1 | 0 |
| **Q.pack** Per-pack / per-pair pricing or box composition | 3 | 11 | 55/85 (65%) | 45/70 (64%) | 65% | 64% | 1/11 (9%) | 5 / 4 | 2/8 (25%) | 3 / 3 | 1: cnc-router-bom-reconcile | 0 | 0 |
| **Q.taxincl** Tax-inclusive (or exclusive) basis with an indirect cue | 3 | 15 | 62/115 (54%) | 0/85 (0%) | 54% | 0% | 4/15 (27%) | 7 / 3 | 0/9 (0%) | 9 / 0 | 1: gst-workbook-answer-key | 0 | 0 |
| **S.inhand** Scope: already in hand / owned / in stock | 3 | 9 | 24/65 (37%) | 0/40 (0%) | 37% | 0% | 4/9 (44%) | 5 / 0 | 0/4 (0%) | 4 / 0 | 1: cnc-router-bom-reconcile | 0 | 0 |

### 2.1 Sub-splits

**Stated vs inferred.** A premise counts as stated if it was coded STATED or written under the B6v1 doctrine. It counts as inferred if it carries incidental anchors.

| class | Fable | Astra |
|---|---|---|
| stated | 0/810 (0.0%) | 0/720 (0.0%) |
| inferred | 1336/6995 (19.1%) | 849/4160 (20.4%) |

**Rounding convention by number of discriminating worked figures.** The counts are hints taken from the authors' salience and DIAL notes; they are approximate. Placement matters as much as the count:
- A figure inside the governing entry kills the trap (profile-copy P5 2.5.0: Astra 0/5).
- A figure inside sentences that illustrate another rule keeps it alive (profile-copy 2.1-2.4: about 90% on both models).

| discriminating figures | premise-versions | Fable | Astra |
|---|---|---|---|
| 1 | 28 | 18/200 (9%) | 15/65 (23%) |
| 2 | 42 | 79/380 (21%) | 85/335 (25%) |
| 3 or more | 10 | 17/60 (28%) | 0/50 (0%) |
| not recorded | 90 | 102/620 (16%) | 43/380 (11%) |

In short:
- With **one** figure, Fable almost never misses (18/200). Astra misses when the figure sits outside the rule's own text (gst P2 1.7.0: 10/15).
- With **two**, results range from 0/30 (coloring spine; the figure was one division away) to about 90% on both models (profile-copy).
- The figure count alone does not predict the rate.

**Keying slip by number of authored anchors.** More routes did not lower the pooled rate:

| anchors | premise-versions | Fable | Astra |
|---|---|---|---|
| 0 | 1 | 0/5 (0%) | 0/5 (0%) |
| 2 | 34 | 124/280 (44%) | 45/200 (22%) |
| 3 | 53 | 176/415 (42%) | 178/340 (52%) |
| 4 | 52 | 167/390 (43%) | 102/270 (38%) |
| 5+ | 54 | 188/430 (44%) | 150/230 (65%) |

What moved slips was what the route says, not how many routes there are:
- A descriptor that only the true owner has (cnc "coiled, wire-tied") took cnc P3 to 0/5 on both models.
- A first-hand sign-off naming the scene (coloring "little crow") took coloring P8 to 0/15 on Fable.
- More oblique routes did not move the rate (kibo P3: 4/5, 4/5, 5/5 across A/B/C; ats P2: 5/5 throughout).

## 3. Dial evidence

Sources:
- Each task's `authoring/DIAL.md`, the frozen trees in `envs-b6/_versions`, and `_v5b`/`_v5c`/`_v5d`.
- The genuineness log.

How to read this section:
- Rates are misses out of valid runs. F is Fable, A is Astra, and "-" means the Astra campaign voided.
- Except where marked as a validity fix, each change below was the only edit to that premise between the versions compared.
- **Caution:** most v5 dials were measured with 5 Fable runs and no Astra. A 5-run pilot moves in steps of 20 points, and identical text gave 2/5 one time and 5/5 the next (home-bp P3, profile-copy P6).

**gst-workbook-answer-key (P1 slip, P3 tax-inclusive, P4 slip, P2 rounding)**

- P3 tax-inclusive: Fable 10/15 (1.4.1), 1/5 (A, adds "a single figure on each line"), 0/5 (B, adds a second "nothing to add on" note), 11/15 (C 1.7.0, only "same rates as our counter board"). Astra 0 throughout (0/75). The weakest oblique cue restored the Fable bite.
- P4 slip: Fable 13/15, A 5/15 (1.4.1), then 0/5 / 2/5 (A, "lorry up from Hubballi"), 1/5 / 0/5 (B), 0/15 / 3/15 (C, petty-cash row "on the road all night"). One origin remark killed the Fable bite and C did not restore it.
- P1 slip, byte-identical across 1.4.1 to 1.7.0: Fable 11/15 to 0/5 (A), 1/5 (B), 3/15 (C); Astra 8/15 to 5/5 (A), 4/5 (B), 12/15 (C). The A/B note placed beside P1's anchor primed a destination check on every record (DIAL.md).
- P2 paise rounding, one discriminating figure (1.5.0 onward): Astra 2/5, 3/5, 10/15; Fable 0/25. With two figures (1.2.0-1.4.1) Astra was 1/5, 10/15 (the 1.3.0 DEFECT cascade), 0/15 and 0/15.

**cnc-router-bom-reconcile (P3 dispatch slip, P4 pair pricing, P5 in hand)**

- P3: both 15/15 (2.3.0). A and B ("isinya 6 biji, yang empat masih tergulung diikat kawat") went to 0/5 on both models. C ("yang empat aku gantung di kait samping rak") gave Fable 14/15 and Astra 1/15 in 2.6.0 and 2.6.1.
- P4: both 15/15 (2.3.0). Two filed purpose-line lists (A, B; same kind) left it at 5/5 and 5/5: every run read every filed list and none applied it. C switched to a received-goods tally ("1 motor, 2 as, 4 bearing, 4 dudukan as") and gave Fable 29/30 and Astra 20/30 over 2.6.x. **Changing the kind of evidence moved Astra; adding more of the same kind did not.**
- P5 (new in 2.4.0, never dialled): Fable 2/5, 3/5, 10/15, 9/15; Astra 0/40.

**profile-copy-claims-audit (P5 rounding, P6 slip, P7 scale, P8 booking scope)**

- P5: both about 90% at 2.1-2.4 (two figures, both inside sentences illustrating other rules).
  - A 2.5.0 adds one cut figure inside the widget-rate entry: Astra 0/5, Fable 1/5.
  - B 2.6.0 also adds the reach figure: Fable 4/5, Astra 0/5. C 2.7.0 (same dials): Fable 4/5, Astra 0/5.
  - D 2.8.0 removes the widget figure again: Fable 1/5, Astra 0/5. The single 10.4 figure kept Astra at 0.
  - Conclusion: any extra figure in a governed entry ends Astra's miss; without one, both models miss about 90%.
- P6 (Fable-only slip): 15/15 (2.4.0); with the "wine vaults" descriptor 5/5 (A); with B's second month route 3/5 (B), 2/5 (C, same text as B), 5/5 (D, same text as B). Astra 0/65 throughout.
- P7 (Fable-only scale): 15/15 (2.4.0); 4/5 (A), 3/5 (B, decision-log route), 4/5 (C), 1/5 (D, adds a fourth party's "close on ten thousand times"). Astra 0/65 across 2.2-2.8.
- P8 (booking = reserved ahead): 5/5 on both models in A and B. It was AMBIGUOUS: no sentence said what a booking is. C added the definition and it went to 0/5 on both models, an example of a stated rule dying.

**deck-preread-review (P2 N8 slip, P4 truncation, P1 thousands)**

- P2: Astra 15/15 at 2.2.0 and 2.3.0, then 5/5 (A, "Yonas will open by taking the committee through the three messages"), 15/15 (B, also "Built for the August pack at the CFO's request"), 5/5 (C), 5/5 (D). Astra never moved. Fable rose from 0/30 to 2/5 and 3/15.
- P4: Astra 15/15 (2.3.0), then 5/5 (A, one extra worked title in standard 3.3), 3/15 (B, a second in 4.1), 1/5 (C), 2/5 (D). Fable 10/15, then 1/5 and 4/15.
- P1 (thousands of birr): "knock three noughts off" stated the unit (A-C): 0/25 on each model. A cross-reference ("deposits up 1,488,600") replaced it in D: 0/5 on each model. Dead in both forms.

**suitcase-cover-matrix-check (P5 licence slip, P7 VAT, P2 truncation)**

- P5: Fable 14/15, Astra 14/15 (2.1.1), then 5/5 (A, process line), 4/5 (B, "notified 25.09"), 4/5 (C, "конверты" regret), 2/5 (D). A slow decline on Fable; Astra unmeasured since 2.1.1.
- P7 VAT basis: stated caption next to the bounds ("руб. без НДС (ставка 22 %)", A/B) gave Fable 0/10. Inferred from a 1790 showcase cover (C) gave 5/5, and C plus an in-population figure (D) gave 5/5. **Bimodal**: every miss noticed the cue and rejected it, and the blind reader also missed. Inference from non-governing documents is a section 15.2 risk.
- P2 (not dialled): Fable 6/15, 5/15, 2/5, 1/5, 3/5, 3/5 across 2.1.0-2.5.0. Steady in band on Fable, 0/30 on Astra.

**home-bp-diary-summary (P3 slip, P5 sheet edition)**

- P3: Fable 15/15, Astra 11-12/15 at 2.2.x. Fable then 5/5 (A, "still in my ski boots"), 5/5 (B, "straight off the long loop"), 2/5 (C, adds the GP letter's 133/79 evening reading), 5/5 (D, P3 byte-identical to C).
- P5: the reprint date was stated (A/B) and Fable went 0/10. In C the reprint is inferred (a 15-row master vs "finished now" at 10:01 on 6 Sep) and Fable went 5/5. D adds "nine of the fourteen rows filled in": 5/5. Parked as bimodal: a printed rule on the current form beats incidental contrary facts.

**cafe-kitchen-schedule-revisions (P1/P6 edition by brief receipt date, P10 shelf slip)**

- P1/P6: both models 15/15 at 2.1.x. Fable 3/5 and 2/5 (A, "when I came by last week ... recording what she wants"), then 6/15 and 8/15 (B, "on Thursday"). The one temporal trap that a single oblique sentence moved into the band; Astra unmeasured.
- P10: Fable 15/15, Astra 11/15 (2.1.1). The validity fix (clause 2.2 now says "the dimensioned figure governs") and "shelf" (A) gave Fable 5/5. "shelf on the wall" (B) gave Fable 10/15.

**coloring-book-retitle-audit (P2/P5/P8 slip re-decided per step, P3/P6 spine)**

- Slip: Fable 13/15, 7/15, 8/15 (2.3.0, steps 1-3). With "the little bird under my title" (A): 4/5, 4/5, 5/5. With "little crow" (B): 2/15, 4/15, 0/15. C (B plus a spine change): 0/5, 1/5, 0/5. The specific first-hand noun overshot.
- Spine rounding: two figures gave 0/30 on both models. One printed pair gave Fable 0/20. One figure inferred from the template width (17.13 in) gave 0/5. Dead in every form: Fable found the pair "one division away".

**pathway-choice-audit (P2 slip, P4/P5 new traps)**

- P2: 15/15 on both models (2.0.0), then Fable 5/5 (A, "Geography club visit to the airstrip"), 10/15 (B, "who wants to fly"), 2/5 (C, same P2 text as B).
- P4 (transfer) and P5 (slip held at 2 pm): Fable 0/20 when stated (A/B). Rebuilt as two-anchor inferences (C): 0/5 and 0/5. Dead.

**timesheet-overtime-review (P4 strips slip, P3 quarter-hour, P5 payroll period)**

- P4: Fable 12/15, Astra 15/15 (2.2.0). The 2.3.0 signal tune added other premises; Fable 0/5, Astra 5/5. A "the decimals sheet" gave Fable 7/15, B "the L2 decimals sheet" 4/5, C (A's text) 5/5.
- P3: one discriminating figure gave Fable 0/25. P5: a stated mapping gave 0/20 (5 of 10 runs paraphrased the rule); inferred from two payroll dates, 0/5.

**kibo-budget-cap-review (P3 Cinder Glade slip, P5 commander scope, P4 whole reais)**

- P3: Fable 15/15, Astra 11/15 (2.3.1), then Fable 4/5 (A, "Japanese foil of our finisher"), 4/5 (B, "the mana-sink land"), 5/5 (C, a fourth route in the review). **Did not move**: Fable reads the identity correctly and still "prices it under the name the file gives".
- P5 (commander already owned): Fable 0/10 when stated, 0/5 when inferred ("the prerelease pull stays at the helm"). Dead.
- P4 (one-figure exemplar): Fable 1/5, 1/5, 0/5; Astra 0/5 at 2.4.0.

**ats-embedded-screening-register (P2 Lumen slip, P4 truncation, P5 training-batch scope)**

- P2: 15/15 on both models (1.1.0), then Fable 5/5 in each of A ("down south"), B ("in Chennai") and C (plus the panel-conflict remark and a guide reword). Did not move.
- P4: four discriminating figures gave 0/15 on each model (1.1.0). Two gave Fable 0/5 (A); one gave 1/5 (B) and 0/5 (C). Astra unmeasured at one figure.
- P5: stated in the chat ("the six-month batch he taught"), Fable 0/10; inferred (C), 0/5.

**Validity fixes that collapsed a bite.** In each case the high rate was an ambiguity, not the mechanism:

| task, premise | before | after | fix |
|---|---|---|---|
| niche P1 (inches) | Fable 15/15, Astra 15/15 (1.1.0) | Fable 0/5, Astra 4/5 (1.3.0) | clearance stated in catalogue units |
| probation P4 (birth-certificate slip) | Fable 10/15, Astra 15/15 (2.2.0) | 0/5 both (2.4.0) | provenance of the Задача column, by-the-way exclusion |
| melody P3 (pre-test scale) | Fable 12/15 (1.1.0) | Fable 0/5 (1.2.0) | null pre-test for late sitters settled |
| moot P10 (heading-number words) | Fable 5/5 (2.1.0) | Fable 0/5 (2.2.0) | spaced em dash replaced by a comma |
| kibo P4 (whole reais) | Fable 5/5 (2.0.0) | Fable 0/5 (2.1.0) | general precedent clause |
| profile-copy P8 (booking) | 10/10 both (2.5/2.6) | 0/10 both (2.7/2.8) | governing definition added |
| coloring slip | 15/15 both, every step (2.2.0) | Fable 13/7/8, Astra 9/9/5 of 15 (2.3.0) | wing remark added; this one survived as a genuine stochastic bite |

## 4. Lever lab (W/lab, L01-L29)

Source: `pipeline/author/lever_evidence.json`, generated 2026-10-02. Same harness, 5 episodes per model (L13 Astra 10). Passes are full-task passes: a pass means the lever did NOT bite.

| lab | levers | shape | mechanism | Fable passes | Astra passes |
|---|---|---|---|---|---|
| L01 | lexical_proxy, unflagged_document | single | 240 free-text notes judged semantically; keyword proxies over- and under-select | 5/5 | 5/5 |
| L02 | rounding_tie_betrayal | single | per-line VAT half-up on binary ties (2.625 -> 2.63) | 5/5 | 5/5 |
| L03 | trigger_inferred | single | trigger fact established across two documents, never labelled | 5/5 | 5/5 |
| L04 | salient_decoy_two_rules | single | salient purpose-labelled decoy that loses once a rule in a second document applies | 5/5 | 5/5 |
| L05 | convention_reach | single | empty cell means 'all' per a header note (null wildcard) | 5/5 | 5/5 |
| L06 | rules_stack_not_first_match | single | fee rules stack; first match is wrong | 5/5 | 5/5 |
| L07 | surface_variant_identity, near_twin_negative | single | one entity under several surface forms; near-twin kept separate | 5/5 | 5/5 |
| L09 | change_set_counterfactual | single | affected = answer changes, not 'has matching rows' | 5/5 | 5/5 |
| L10 | execution_order_dependency | single | order of application set in another document | 5/5 | 5/5 |
| L11 | rounding_stage | single | round each line before summing | 5/5 | 5/5 |
| L12 | fill_the_gap | single | carrier pricing method inferred from historical invoices | 5/5 | 5/5 |
| L13 | fill_the_gap, revision_scope | single | unstated rate change inferred from paid statements | 5/5 | 10/10 |
| L14 | fill_the_gap | single | marginal vs flat tiers inferred from 18 statements | 5/5 | 5/5 |
| L15 | unflagged_document, lexical_proxy | incidental | 23 give-backs in varied memo wording inside a 1,400-line ledger | 5/5 | 5/5 |
| L16 | surface_variant_identity, near_twin_negative | incidental | unlisted spacing variants and a near-twin inside a rebate run | 5/5 | 5/5 |
| L17 | execution_order_dependency | single | allocation in true UTC order across office time zones | 5/5 | 5/5 |
| L18 | lexical_proxy, nested_exception | scale | 60 composite warranty judgments, all must be right | 5/5 | 5/5 |
| L19 | stacked | stacked | 12 independent silent traps in one commission run | 5/5 | 5/5 |
| L20 | masking_pair | combined | conspicuous problem plus silent interacting fact on one item (Fable 0/5 was an AMBIGUITY: policy 3.2 card-statement reading, identical across episodes -- not a bite) | 0/5 | 5/5 |
| L21 | cascade_premise | combined | identity -> qualifying volume -> revised threshold -> cap order -> cut-off | 5/5 | 5/5 |
| L22 | control_total_blind | combined | reallocations invisible to the control total, plus an offsetting pair | 5/5 | 5/5 |
| L23 | cross_step_premise | combined | step-2 correction cascades; near-twin re-decided in a fresh session | 5/5 | 5/5 |
| L24 | withhold_vs_resolve, fill_the_gap | combined | opposite abstention traps on one population | 5/5 | 5/5 |
| L25 | implicit_constraint_plan | combined | unique optimum under 8-12 constraints scattered across genres | 5/5 | 5/5 |
| L26 | multi_lever_item | combined | 3-4 levers on every graded item | 5/5 | 5/5 |
| L27 | deep_in_long_document, cascade_premise | combined | decisive rules mid-manual in non-matching vocabulary, cascading | 5/5 | 5/5 |
| L28 | lexical_proxy, unflagged_document | scale | 360 remediation cases, 1.66 MB, beyond one context | 5/5 | 5/5 |
| L29 | surface_variant_identity, revision_scope, counting_unit_boundary | stacked | six historically measured near-misses in one two-step task | 5/5 | 5/5 |

Every lever was solved by both models, apart from L20, where Fable's 0/5 was recorded as an ambiguity in the policy's card statement. That is 27 of 28 labs at 5/5 on both models. Combined and stacked shapes (L19-L29) fared no better than single levers, and P30/P31 have no recorded results. `lever_evidence.json` also carries a family-level history from earlier batches, quoted as written:

- **repeated_wrong_figure** (measured once): a-040 Fable missed 22/26, Astra 0/24; replications failed (A1 self-consistent wrong figure: 18 tasks, Fable 0/215)
- **changed_premise** (measured, mixed): a-031 Fable missed 6/15, Astra 0/15; census 5/43. Bites only when the revision flips an item through an attribute the model does not re-read
- **later_exclusion_aggregate** (measured, borderline): a-013 Fable missed 15/15, Astra 0/15 (identical every run -- never reviewed for ambiguity)
- **version_in_force** (hypothesis): weak or dead internally; external evidence (OfficeQA Pro); an Arena example
- **near_twin_identity** (measured): Astra a-108 missed 5/15 unnamed vs 0/15 named; b2b 5/35; Fable a-043 3/10; ZWNJ variant Fable ~30%. Naming the variant kills it; a key in the data is required
- **governing_key** (measured once, then failed): Astra solved 10/10 in batch 4; A15 filing-key join about 0/400 missed
- **house_number_convention** (measured): exact non-binary half on a band edge (a-037): Fable missed 3-4/10, Astra 3-5/10 -- the one stochastic both-model lever; rounding reach Astra 5/40. Dead: house day-count 0/90, A3 lossy rounding 0/50
- **caption_only_rule** (measured, one lineage): higher-education 10x2: Fable missed 7/10, Astra 2/10
- **coverage_omission** (measured weak, leans Fable): models detect omissions 6-7x less often than inclusions (external)
- **scope_compliant_twins** (hypothesis): unadjudicated over-inclusion signals 4/5, 5/10, 4/15
- **answerability** (hypothesis): lab L24 dead; external (DABstep)
- **composition_tie** (hypothesis): lab L22 dead; external (APEX-Accounting <= 9.5%)
- **stacked_rules** (hypothesis): labs dead; external (tau2, DABstep)
- **clean_baseline** (measured): a-031 Fable missed 3/10 and 3/5, Astra 0/15
- **trigger_event** (measured, contested): 9 of 11 blind readers took the other reading without a defining sentence
- **timestamp_ordering** (measured, CAPPED): every rate 0-100% depending on anchor salience (moderate in 8% of Fable / 13% of Astra finals); store/outage with casual wording Fable 53-100%, Astra 0-93%, dead when the window is stated precisely. 36 of 37 shipped tasks rested on it: at most one per task, about 10% of a batch
- **authority_delegation** (discouraged as a decider): Arena called these ambiguous; Astra solved every batch-4 instance; unauthorized-request authority Fable 1/90
- **inferred_exclusion** (discouraged as a decider): the second-reading shape: clarification took seven moderate bites to 0% (a-005, a-114, exam-prep, core-banking, trip, a-034, a-088)

## 5. Legacy trap maps (batch-4 era `traps[]` schema)

Seven batch-4 tasks in the ledger carry an older `traps[]` map: exam-study-planning (two variants), e-commerce-listing-localisation, exam-preparation-analytics, sports-science-coaching, higher-education-publishing and m-e-survey-reporting. There are 168 traps with types such as misleading_label, stale_authority, derived_answer and plausible_decoy.

These traps cannot be attributed reliably:
- In those maps, many traps point at the same aggregate checks. Only 21 of 168 traps have a check of their own.
- Their "any check missed" rates (34-72%) therefore mostly count other traps' failures.

On checks owned by a single trap, the result is clear:
- **The only attributable bites are clock offsets:**
  - exam-preparation-analytics `clock_offset_pair_order`: Fable 45/45, Astra 43/45;
  - m-e-survey `t_server_clock`: Fable 15/15, Astra 14/15.
- misleading_label (9 traps with own checks) and stale_authority (8): 0/295 and 0/220 on Fable, 0/300 and 0/225 on Astra.
- The independent clean-gate final-genuineness audits of these tasks (`research/batch4/cleangate-261011-*-final-genuineness.md`) found the failing sessions lost exactly the clock-ordered checks.
  - Example: sports-science, "All 49 failing step-sessions lose exactly `s?_pm_noneval` and `s?_pm_verdict`".
  - Classified GENUINE.
- This matches Arena's 261013 feedback: 34 of 37 tasks shared the clock trap, flat 0/10.

Three more fb/fb2 lineages (indentation-probe-selection, scholarship-eligibility and small-business-tax, in both a_f0 and a_f1 variants) carry a per-check list of trap descriptions instead of a trap-to-check map. They cannot be attributed to premises and are left out.

The other 470 batch-4 campaigns in the ledger (`envs-b4`, no premise map) and the v2/v3/fb screens (`traps[]` maps, check-level aggregates only, no per-trial vectors in the ledger) are **not** in the premise tables.

## 6. Method and caveats

**Data.**
- Source: `research/batch4/ledger.json`, 569 entries. 1,023 campaigns have valid trials: 561 Fable, 462 Astra.
- Each campaign's `report.json` was read for valid trials only; voids never count. The 38 artifact folders the ledger does not point to (superseded void attempts and two oracle/nop probes) hold no valid model trials.
- Per-trial premise outcome follows `signal_gate.py`: a premise is missed if any of its checks scores below 1.0 in the premise's step.
- Gated-out checks are excluded from misses. In practice no model run in scope had a gated-out premise check.
- **Cross-check:** recomputed from the raw reports, the counts agree with all 1,572 per-campaign premise counts in `research/batch4/b6/gates/*.json`, with 0 disagreements.

**Premise maps.**
- Each campaign was joined to the `authoring/traps.json` of its own version: the ledger's tree, or else the frozen `_versions`/`_v5b`/`_v5c`/`_v5d` copy with the same `task.toml` version.
- Two b6 versions have no frozen map: brightwater 1.0.0, taken from its gates JSON (all 0/5), and refurb 1.0.0 (dropped; Fable 5 runs).

**Retired models.** No campaign in the ledger and none of the 720 older screen files was run on `claude-opus-5` or `gpt-5.6-sol`, so the retired-model section is empty. Every rate here is Fable 5.1 (Claude Code) or GPT-6 Astra (Codex), at high effort with no limits.

**Mechanism labels.**
- Labels were assigned by keyword rules over each premise's `misreading`, then reviewed by hand for all 531 distinct premise texts (123 overrides).
- They are judgement calls. The CSV keeps the original `family` and `mechanism` code beside the label, so any regrouping can be redone.
- **Re-decisions:** a premise that re-decides an earlier step's trap in a fresh session (coloring P5/P8, cafe P6, moot P12-P15, mustangs P4/P9/P11) is flagged `redecide_fresh_step`. These count as separate runs, but they are correlated with the first decision.

**Verdicts.**
- Transcribed by hand from `genuineness.md`; the latest entry for a task-version-premise wins.
- Where the log says a patched version regrades identically (gst 1.4.1, kibo 2.3.1, home-bp 2.2.1, suitcase 2.1.1, cnc 2.6.1), the audit verdict is carried over and the note says so.
- Units with no verdict are unaudited, not genuine.

**Coverage gaps.**
- Astra is missing on 523 of 1129 units, including every v5 round-2 variant. Fable-only rates there say nothing about Astra.
- 913 of 1129 units (81%) have fewer than 10 runs on both models (5-run pilots), so those rates are provisional.
- Stage is recorded per row: pilot 5x2, final 10x2. Pooled rates add pilot and final runs of the same version.

**Confounds.**
- Some premises share checks; the `shares_checks_with` column flags them.
- Two cascades inflated a second premise's misses:
  - deck 2.2.0 P3 (Astra 15/15): DEFECT, the reference-graded `c_sequence_pair`;
  - gst 1.3.0 P2 (Astra 10/15): DEFECT, a head cascade.
- Both are marked DEFECT and excluded from the clean rates.

## 7. Full evidence table (both models side by side)

Grouped by mechanism.

Column key:
- **F** and **A**: misses / valid runs, all stages pooled. "-" means not measured (void).
- **stages**: per model, `p` = pilot and `f` = final.
- **S/I**: stated (`st`, `st-v1` for the B6v1 doctrine) or inferred (`inf-N`, with N authored anchors).
- **re**: the premise re-decides an earlier step's trap in a fresh session.
- **misreading**: the premise's misreading, truncated.

The CSV has the per-model rows, checks, check sharing, figure hints and full premise-map paths.

### ID.slip: Keying slip: record filed under the wrong ID, true owner only by description

| task | ver | P | F | A | stages | verdict | S/I | re | misreading |
|---|---|---|---|---|---|---|---|---|---|
| ats-embedded-screening-register | 1.0.0 | P2 | 0/5 | - | F p 0/5 |  | inf-2 |  | keeps the misfiled Sutlej Embedded Labs role (Jun 2019 - May 2023) on C-302: experience 88 (or 86) months and  |
| ats-embedded-screening-register | 1.1.0 | P2 | 15/15 | 15/15 | A f 10/10; p 5/5; F f 10/10; p 5/5 | GENUINE | inf-3 |  | keeps the Lumen Wireless line on C-304 (84 months instead of 54) and leaves it off C-306 (55 instead of 85); e |
| ats-embedded-screening-register | 1.2.0 | P2 | 5/5 | - | F p 5/5 |  | inf-4 |  | keeps the Lumen Wireless line on C-304 (84 months instead of 54) and leaves it off C-306 (55 instead of 85); e |
| ats-embedded-screening-register | 1.3.0 | P2 | 5/5 | - | F p 5/5 |  | inf-4 |  | keeps the Lumen Wireless line on C-304 (84 months instead of 54) and leaves it off C-306 (55 instead of 85); e |
| ats-embedded-screening-register | 1.4.0 | P2 | 5/5 | - | F p 5/5 |  | inf-5 |  | keeps the Lumen Wireless line on C-304 (84 months instead of 54) and leaves it off C-306 (55 instead of 85); e |
| billiard-shift-audit | 2.1.0 | P5 | 0/5 | 0/5 | A p 0/5; F p 0/5 |  | inf-2 |  | keeps the October champion's card КК-0388 on the bar-only check where the POS printed it (discount 0) and bill |
| billiard-shift-audit | 2.1.0 | P6 | 0/5 | 0/5 | A p 0/5; F p 0/5 |  | inf-3 |  | restores the bottle of the novelty to 3110-06 (3630) and leaves 3110-08 at 950; the entry's party is the coupl |
| blockprint-winter-close | 1.0.0 | P5 | 0/5 | - | F p 0/5 |  | inf-3 |  | writes the 15 border-block kurtas as IMP-07 Kurta (a false merge on the printed name) instead of IMP-22 Kurta |
| blockprint-winter-close | 1.1.0 | P5 | 1/5 | - | F p 1/5 |  | inf-4 |  | writes the 15 border-print kurtas counted on the white-ground print's till line as IMP-07 Kurta 15 (a keying s |
| blockprint-winter-close | 1.2.0 | P5 | 1/5 | 0/5 | A p 0/5; F p 1/5 |  | inf-4 |  | writes the 15 border-print kurtas Yanis wrote up as 'Indigo Leaf' as IMP-07 Kurta 15 instead of IMP-22 Kurta 1 |
| brightwater-spec-qa | 1.1.0 | P1 | 0/5 | - | F p 0/5 |  | inf-3 |  | keeps hpblex.ma on the Casablanca desk lines C-041 and C-042 (taken for the partner's), so their domain is the |
| brightwater-spec-qa | 1.2.0 | P1 | 0/5 | - | F p 0/5 |  | inf-3 |  | keeps hpblex.ma on the Casablanca desk lines C-041 and C-042 (taken for the partner's reception, like C-037),  |
| brightwater-spec-qa | 1.3.0 | P1 | 0/15 | 0/15 | A f 0/10; p 0/5; F f 0/10; p 0/5 |  | inf-2 |  | leaves ALT-04 ('HPB Lex team members at the Casablanca meeting table') out of name_strings, taking it for the  |
| cafe-kitchen-schedule-revisions | 2.1.0 | P10 | 15/15 | 13/15 | A f 8/10; p 5/5; F f 10/10; p 5/5 | AMBIGUOUS | inf-2 |  | sets SH-2 from the work table: 140, listed as moved. The supplier's lid remark puts a board over the chilled c |
| cafe-kitchen-schedule-revisions | 2.1.0 | P4 | 0/15 | 0/15 | A f 0/10; p 0/5; F f 0/10; p 0/5 |  | inf-2 |  | takes the log's key: prices HW-1 (1 basin, 1 knee tap). The owner's purchase is the sink her sister picked (he |
| cafe-kitchen-schedule-revisions | 2.1.1 | P10 | 15/15 | 11/15 | A f 9/10; p 2/5; F f 10/10; p 5/5 | GENUINE | inf-2 |  | sets SH-2 from the work table: 140, listed as moved. The supplier's lid remark puts a board over the chilled c |
| cafe-kitchen-schedule-revisions | 2.1.1 | P4 | 0/15 | 1/15 | A f 1/10; p 0/5; F f 0/10; p 0/5 |  | inf-2 |  | takes the log's key: prices HW-1 (1 basin, 1 knee tap). The owner's purchase is the sink her sister picked (he |
| cafe-kitchen-schedule-revisions | 2.2.0 | P10 | 5/5 | - | F p 5/5 |  | inf-2 |  | sets SH-2 from the work table: 140 (and lists it as moved, which s3_shelf_moved grades on the deliverable's ow |
| cafe-kitchen-schedule-revisions | 2.2.0 | P4 | 0/5 | - | F p 0/5 |  | inf-2 |  | takes the log's key: prices HW-1 (1 basin, 1 knee tap). The owner's purchase is the sink her sister picked (he |
| cafe-kitchen-schedule-revisions | 2.3.0 | P10 | 10/15 | - | F f 7/10; p 3/5 | BLIND-1.0 | inf-2 |  | sets SH-2 from the work table: 140 (and lists it as moved, which s3_shelf_moved grades on the deliverable's ow |
| cafe-kitchen-schedule-revisions | 2.3.0 | P4 | 0/15 | - | F f 0/10; p 0/5 |  | inf-2 |  | takes the log's key: prices HW-1 (1 basin, 1 knee tap). The owner's purchase is the sink her sister picked (he |
| cnc-router-bom-reconcile | 2.0.0 | P2 | 0/5 | - | F p 0/5 |  | inf-3 |  | resolves 'mini grinder Kenzo' to the register's T06 'Gerinda mini Kenzo' (KMG-180, collet 3 mm, on loan to Dim |
| cnc-router-bom-reconcile | 2.1.0 | P2 | 0/5 | - | F p 0/5 |  | inf-4 |  | keys the tool on the loan row's tag T06 (KMG-180, collet 3 mm) and orders EM-3000; T06, the small grinder Dima |
| cnc-router-bom-reconcile | 2.2.0 | P2 | 0/5 | - | F p 0/5 |  | inf-4 |  | keys the tool on the loan row's tag T06 (KMG-180, collet 3 mm) and orders EM-3000; the tool on Bayu's CNC is t |
| cnc-router-bom-reconcile | 2.3.0 | P2 | 0/15 | 0/15 | A f 0/10; p 0/5; F f 0/10; p 0/5 |  | inf-4 |  | keys the tool on the loan row's tag T06 (KMG-180, collet 3 mm) and orders EM-3000; the tool on Bayu's CNC is t |
| cnc-router-bom-reconcile | 2.3.0 | P3 | 15/15 | 15/15 | A f 10/10; p 5/5; F f 10/10; p 5/5 | GENUINE | inf-4 |  | takes the received consignment's 4-line at its printed code CPL-0508, so the store covers the couplers and Bay |
| cnc-router-bom-reconcile | 2.4.0 | P2 | 0/5 | 0/5 | A p 0/5; F p 0/5 |  | inf-4 |  | keys the tool on the loan row's tag T06 (KMG-180, collet 3 mm) and orders EM-3000; the tool on Bayu's CNC is t |
| cnc-router-bom-reconcile | 2.4.0 | P3 | 0/5 | 0/5 | A p 0/5; F p 0/5 |  | inf-4 |  | takes the received consignment's 4-line at its printed code CPL-0508, so the store covers the couplers and Bay |
| cnc-router-bom-reconcile | 2.5.0 | P2 | 0/5 | 0/5 | A p 0/5; F p 0/5 |  | inf-4 |  | keys the tool on the loan row's tag T06 (KMG-180, collet 3 mm) and orders EM-3000; the tool on Bayu's CNC is t |
| cnc-router-bom-reconcile | 2.5.0 | P3 | 0/5 | 0/5 | A p 0/5; F p 0/5 |  | inf-5 |  | takes the received consignment's 4-line at its printed code CPL-0508, so the store covers the couplers and Bay |
| cnc-router-bom-reconcile | 2.6.0 | P2 | 0/15 | 0/15 | A f 0/10; p 0/5; F f 0/10; p 0/5 |  | inf-4 |  | keys the tool on the loan row's tag T06 (KMG-180, collet 3 mm) and orders EM-3000; the tool on Bayu's CNC is t |
| cnc-router-bom-reconcile | 2.6.0 | P3 | 14/15 | 1/15 | A f 1/10; p 0/5; F f 9/10; p 5/5 | GENUINE | inf-4 |  | takes the received consignment's 4-line at its printed code CPL-0508, so the store covers the couplers and Bay |
| cnc-router-bom-reconcile | 2.6.1 | P2 | 0/15 | 0/15 | A f 0/10; p 0/5; F f 0/10; p 0/5 |  | inf-4 |  | keys the tool on the loan row's tag T06 (KMG-180, collet 3 mm) and orders EM-3000; the tool on Bayu's CNC is t |
| cnc-router-bom-reconcile | 2.6.1 | P3 | 14/15 | 1/15 | A f 0/10; p 1/5; F f 9/10; p 5/5 | GENUINE | inf-4 |  | takes the received consignment's 4-line at its printed code CPL-0508, so the store covers the couplers and Bay |
| coloring-book-retitle-audit | 2.1.0 | P2 | 0/5 | - | F p 0/5 |  | inf-5 |  | keying slip: the art log files the lettered re-supply under D16 (Moon Cookie Baking, a tray of cookies); the c |
| coloring-book-retitle-audit | 2.1.0 | P5 | 0/5 | - | F p 0/5 |  | inf-5 | re | re-decision of the step-1 keying slip in a fresh session: the book's title is lettered on the shop sign of the |
| coloring-book-retitle-audit | 2.1.0 | P8 | 0/5 | - | F p 0/5 |  | inf-5 | re | re-decision of the keying slip in a second fresh session: the lettered inside page is the crow design's page 6 |
| coloring-book-retitle-audit | 2.2.0 | P2 | 15/15 | 15/15 | A f 10/10; p 5/5; F f 10/10; p 5/5 | AMBIGUOUS | inf-6 |  | keying slip: the art log files the lettered re-supply under D16 (a cookie shop under its shop sign, which fits |
| coloring-book-retitle-audit | 2.2.0 | P5 | 15/15 | 15/15 | A f 10/10; p 5/5; F f 10/10; p 5/5 | AMBIGUOUS | inf-6 | re | re-decision of the step-1 keying slip in a fresh session: the book's title is lettered on the shop sign of the |
| coloring-book-retitle-audit | 2.2.0 | P8 | 15/15 | 15/15 | A f 10/10; p 5/5; F f 10/10; p 5/5 | AMBIGUOUS | inf-6 | re | re-decision of the keying slip in a second fresh session: the lettered inside page is the bird design's page 6 |
| coloring-book-retitle-audit | 2.3.0 | P2 | 13/15 | 9/15 | A f 5/10; p 4/5; F f 8/10; p 5/5 | GENUINE | inf-6 |  | keying slip: the art log files the lettered re-supply under D16 (a cookie shop under its shop sign, which fits |
| coloring-book-retitle-audit | 2.3.0 | P5 | 7/15 | 9/15 | A f 4/10; p 5/5; F f 5/10; p 2/5 | GENUINE | inf-6 | re | re-decision of the step-1 keying slip in a fresh session: the book's title is lettered on the shop sign of the |
| coloring-book-retitle-audit | 2.3.0 | P8 | 8/15 | 5/15 | A f 2/10; p 3/5; F f 6/10; p 2/5 | GENUINE | inf-6 | re | re-decision of the keying slip in a second fresh session: the lettered inside page is the bird design's page 6 |
| coloring-book-retitle-audit | 2.4.0 | P2 | 4/5 | - | F p 4/5 |  | inf-7 |  | keying slip: the art log files the lettered re-supply under D16 (a cookie shop under its shop sign, which fits |
| coloring-book-retitle-audit | 2.4.0 | P5 | 4/5 | - | F p 4/5 |  | inf-7 | re | re-decision of the step-1 keying slip in a fresh session: the book's title is lettered on the shop sign of the |
| coloring-book-retitle-audit | 2.4.0 | P8 | 5/5 | - | F p 5/5 |  | inf-7 | re | re-decision of the keying slip in a second fresh session: the lettered inside page is the bird design's page 6 |
| coloring-book-retitle-audit | 2.5.0 | P2 | 2/15 | - | F f 0/10; p 2/5 | BLIND-1.0 | inf-7 |  | keying slip: the art log files the lettered re-supply under D16 (a cookie shop under its shop sign, which fits |
| coloring-book-retitle-audit | 2.5.0 | P5 | 4/15 | - | F f 3/10; p 1/5 | BLIND-1.0 | inf-7 | re | re-decision of the step-1 keying slip in a fresh session: the book's title is lettered on the shop sign of the |
| coloring-book-retitle-audit | 2.5.0 | P8 | 0/15 | - | F f 0/10; p 0/5 | BLIND-1.0 | inf-7 | re | re-decision of the keying slip in a second fresh session: the lettered inside page is the bird design's page 6 |
| coloring-book-retitle-audit | 2.6.0 | P2 | 0/5 | - | F p 0/5 |  | inf-7 |  | keying slip: the art log files the lettered re-supply under D16 (a cookie shop under its shop sign, which fits |
| coloring-book-retitle-audit | 2.6.0 | P5 | 1/5 | - | F p 1/5 |  | inf-7 | re | re-decision of the step-1 keying slip in a fresh session: the book's title is lettered on the shop sign of the |
| coloring-book-retitle-audit | 2.6.0 | P8 | 0/5 | - | F p 0/5 |  | inf-7 | re | re-decision of the keying slip in a second fresh session: the lettered inside page is the bird design's page 6 |
| coop-bp-prefill-sheet | 1.0.0 | P1 | 0/5 | - | F p 0/5 |  | inf-2 |  | keeps PJ-064 under C04: with the house campaign it falls outside Tagadirt's 2025 financial year and vanishes,  |
| coop-bp-prefill-sheet | 1.1.0 | P1 | 0/5 | 0/5 | A p 0/5; F p 0/5 |  | inf-2 |  | keeps PJ-064 under C04: Tagadirt's figure carries it and Tamount's lacks it (Tamount 138 100 instead of 164 50 |
| council-video-index | 1.1.0 | P3 | 0/5 | - | F p 0/5 |  | inf-3 |  | gives the session's one budget resolution to the item the register prints (6a, the playground change, which fe |
| council-video-index | 1.2.0 | P3 | 0/15 | 0/15 | A f 0/10; p 0/5; F f 0/10; p 0/5 |  | inf-3 |  | gives the session's one budget resolution to the item the register prints (6a, the playground change, which fe |
| council-video-index | 1.3.0 | P3 | 0/5 | 0/5 | A p 0/5; F p 0/5 |  | inf-4 |  | gives the session's one budget resolution, XXXI/250/2026, to the item the register prints (6f, the resurfacing |
| current-affairs-booklet-plan | 1.1.0 | P2 | 0/5 | - | F p 0/5 |  | inf-4 |  | merges the park block with FB-0405 (a park at Bandhwari already opened by early January, reported in the neigh |
| current-affairs-booklet-plan | 1.2.0 | P2 | 0/5 | 0/5 | A p 0/5; F p 0/5 |  | inf-3 |  | keys the river-meadow row (3-5 March, 12,10,300) to Rang Utsav, its printed fair: Rang Utsav 126.3 and the cat |
| deck-preread-review | 2.1.0 | P2 | 0/5 | - | F p 0/5 |  | inf-3 |  | N8 S-25 (as filed) instead of S-24: the momentum slide sits where the CFO wants it (Hana, after the review day |
| deck-preread-review | 2.2.0 | P2 | 0/15 | 15/15 | A f 10/10; p 5/5; F f 0/10; p 0/5 | GENUINE | inf-3 |  | N8 S-25 (as filed) instead of S-24: the momentum slide sits where the CFO wants it (Hana, after the review day |
| deck-preread-review | 2.3.0 | P2 | 0/15 | 15/15 | A f 10/10; p 5/5; F f 0/10; p 0/5 | GENUINE | inf-3 |  | N8 S-25 (as filed) instead of S-24: the momentum slide sits where the CFO wants it (Hana, after the review day |
| deck-preread-review | 2.4.0 | P2 | 2/5 | 5/5 | A p 5/5; F p 2/5 |  | inf-4 |  | N8 S-25 (as filed) instead of S-24: the momentum slide sits where the CFO wants it (Hana, after the review day |
| deck-preread-review | 2.5.0 | P2 | 3/15 | 15/15 | A f 10/10; p 5/5; F f 1/10; p 2/5 | BLIND-1.0 | inf-5 |  | N8 S-25 (as filed) instead of S-24: the momentum slide sits where the CFO wants it (Hana, after the review day |
| deck-preread-review | 2.6.0 | P2 | 0/5 | 5/5 | A p 5/5; F p 0/5 |  | inf-5 |  | N8 S-25 (as filed) instead of S-24: the momentum slide sits where the CFO wants it (Hana, after the review day |
| deck-preread-review | 2.7.0 | P2 | 0/5 | 5/5 | A p 5/5; F p 0/5 |  | inf-5 |  | N8 S-25 (as filed) instead of S-24: the momentum slide sits where the CFO wants it (Hana, after the review day |
| earth-guide-answer-claims | 1.0.0 | P1 | 0/5 | - | F p 0/5 |  | inf-3 |  | credits LA-11 (Evolution of the Himalayas, 16 marks) to F04, Prof. S. Raghavan Rao, as keyed; Prof. Rao retire |
| earth-guide-answer-claims | 1.1.0 | P1 | 0/5 | 0/5 | A p 0/5; F p 0/5 |  | inf-5 |  | pays the two-panel plate with the petroleum answer as filed: LA-05 3 diagrams instead of 2 (and LA-09 1 instea |
| eco-guard-errata-review | 2.1.0 | P2 | 0/5 | - | F p 0/5 |  | inf-4 |  | keeps C-4 as one leaf: the baseline false-positive rate stays 4 of 40 (0.10) instead of 3 of 39 (0.08), becaus |
| eco-guard-errata-review | 2.2.0 | P2 | 0/5 | - | F p 0/5 |  | inf-4 |  | keeps C-4 as one leaf: the baseline false-positive rate stays 4 of 40 (0.10) instead of 3 of 39 (0.08), becaus |
| eco-guard-errata-review | 2.3.0 | P1 | 0/5 | 0/5 | A p 0/5; F p 0/5 |  | inf-2 |  | fills the three Appendix A.3 losses from the 10 October runs (the analyst's weekend runs of the step-size note |
| eco-guard-errata-review | 2.3.0 | P2 | 0/5 | 0/5 | A p 0/5; F p 0/5 |  | inf-2 |  | keeps the card filed under slot C-4 as a healthy papaya sprayed: 4 of 40 (0.10) instead of 3 of 39 (0.08). The |
| ethics-report-mark-release | 1.0.0 | P1 | 0/5 | - | F p 0/5 |  | inf-3 |  | applies EXT-2691 to Maya because it carries her student number: late_deduction 0 instead of 10. The register h |
| ethics-report-mark-release | 1.1.0 | P1 | 0/5 | 3/5 | A p 3/5; F p 0/5 |  | inf-3 |  | applies EXT-2691 to Maya because it carries her student number: late_deduction 0 instead of 10. Student Servic |
| feast-sharing-runsheet | 1.1.0 | P3 | 5/5 | - | F p 5/5 | AMBIGUOUS | inf-3 |  | gives 8A the six groups of the sheet written 8A and 8B four groups of six; the sheet's class must go across to |
| gst-workbook-answer-key | 1.0.0 | P1 | 0/5 | - | F p 0/5 |  | inf-4 |  | S-104 'CGST+SGST' and S-108 'IGST' (the state of the billing address). Truth: S-104's 66 cartons went by lorry |
| gst-workbook-answer-key | 1.0.0 | P4 | 0/5 | - | F p 0/5 |  | inf-3 |  | P-204 'CGST+SGST' (828/828/0). Truth: the reams delivered on 18 Jul came by lorry receipt TT/0918 from wholesa |
| gst-workbook-answer-key | 1.1.0 | P1 | 0/5 | - | F p 0/5 |  | inf-4 |  | S-104 'CGST+SGST' and S-108 'IGST' (the state of the billing address). Truth: S-104's 66 cartons went by lorry |
| gst-workbook-answer-key | 1.1.0 | P4 | 0/5 | - | F p 0/5 |  | inf-3 |  | P-204 'CGST+SGST' (828/828/0). Truth: the reams and the boxed guillotine unloaded on 18 Jul, P-204's date (pet |
| gst-workbook-answer-key | 1.2.0 | P1 | 0/5 | 0/5 | A p 0/5; F p 0/5 |  | inf-4 |  | S-104 'CGST+SGST' and S-108 'IGST' (the state of the billing address). Truth: S-104's 66 cartons went by lorry |
| gst-workbook-answer-key | 1.2.0 | P4 | 5/5 | 0/5 | A p 0/5; F p 5/5 |  | inf-3 |  | P-204 'CGST+SGST' (828/828/0). Truth: the firm's guillotine was crated by Malaprabha Paper Traders (its after- |
| gst-workbook-answer-key | 1.3.0 | P1 | 12/15 | 11/15 | A f 8/10; p 3/5; F f 8/10; p 4/5 | GENUINE | inf-6 |  | S-104 'CGST+SGST', S-106 'CGST+SGST' and S-108 'IGST' (the bills as keyed). Truth: S-104's cartons went by lor |
| gst-workbook-answer-key | 1.3.0 | P4 | 13/15 | 4/15 | A f 2/10; p 2/5; F f 9/10; p 4/5 | GENUINE-soft | inf-3 |  | P-204 'CGST+SGST' (828/828/0). Truth: the firm's guillotine was crated by Malaprabha Paper Traders (its after- |
| gst-workbook-answer-key | 1.4.0 | P1 | 11/15 | 12/15 | A f 9/10; p 3/5; F f 9/10; p 2/5 | GENUINE | inf-6 |  | S-104 'CGST+SGST', S-106 'CGST+SGST' and S-108 'IGST' (the bills as keyed). Truth: S-104's cartons went by lor |
| gst-workbook-answer-key | 1.4.0 | P4 | 12/15 | 10/15 | A f 8/10; p 2/5; F f 9/10; p 3/5 | GENUINE-soft | inf-3 |  | P-204 'CGST+SGST' (828/828/0). Truth: the firm's guillotine was crated by Malaprabha Paper Traders (its after- |
| gst-workbook-answer-key | 1.4.1 | P1 | 11/15 | 8/15 | A f 6/10; p 2/5; F f 6/10; p 5/5 | GENUINE | inf-6 |  | S-104 'CGST+SGST', S-106 'CGST+SGST' and S-108 'IGST' (the bills as keyed). Truth: S-104's cartons went by lor |
| gst-workbook-answer-key | 1.4.1 | P4 | 13/15 | 5/15 | A f 4/10; p 1/5; F f 8/10; p 5/5 | GENUINE-soft | inf-3 |  | P-204 'CGST+SGST' (828/828/0). Truth: the firm's guillotine was crated by Malaprabha Paper Traders (its after- |
| gst-workbook-answer-key | 1.5.0 | P1 | 0/5 | 5/5 | A p 5/5; F p 0/5 |  | inf-6 |  | S-104 'CGST+SGST', S-106 'CGST+SGST' and S-108 'IGST' (the bills as keyed). Truth: S-104's cartons went by lor |
| gst-workbook-answer-key | 1.5.0 | P4 | 0/5 | 2/5 | A p 2/5; F p 0/5 |  | inf-4 |  | P-204 'CGST+SGST' (828/828/0). Truth: the firm's guillotine was crated by Malaprabha Paper Traders (its after- |
| gst-workbook-answer-key | 1.6.0 | P1 | 1/5 | 4/5 | A p 4/5; F p 1/5 |  | inf-6 |  | S-104 'CGST+SGST', S-106 'CGST+SGST' and S-108 'IGST' (the bills as keyed). Truth: S-104's cartons went by lor |
| gst-workbook-answer-key | 1.6.0 | P4 | 1/5 | 0/5 | A p 0/5; F p 1/5 |  | inf-4 |  | P-204 'CGST+SGST' (828/828/0). Truth: the firm's guillotine was crated by Malaprabha Paper Traders (its after- |
| gst-workbook-answer-key | 1.7.0 | P1 | 3/15 | 12/15 | A f 7/10; p 5/5; F f 1/10; p 2/5 | GENUINE-soft | inf-6 |  | S-104 'CGST+SGST', S-106 'CGST+SGST' and S-108 'IGST' (the bills as keyed). Truth: S-104's cartons went by lor |
| gst-workbook-answer-key | 1.7.0 | P4 | 0/15 | 3/15 | A f 2/10; p 1/5; F f 0/10; p 0/5 | GENUINE-soft | inf-4 |  | P-204 'CGST+SGST' (828/828/0). Truth: the firm's guillotine was crated by Malaprabha Paper Traders (its after- |
| hammamet-voucher-reissue | 2.1.0 | P4 | 0/5 | - | F p 0/5 |  | inf-3 |  | room_1.checkout_time 16:00 and room_2.checkout_time 12:00 (the clerk's room number) instead of 12:00 and 16:00 |
| hammamet-voucher-reissue | 2.2.0 | P4 | 0/5 | 0/5 | A p 0/5; F p 0/5 |  | inf-4 |  | room_1.checkout_time 16:00 and room_2.checkout_time 12:00 (the room the clerk typed) instead of 12:00 and 16:0 |
| home-bp-diary-summary | 2.1.0 | P3 | 0/5 | - | F p 0/5 |  | inf-4 |  | reports 170/90 (the left arm, higher at the misfiled March health check of another Mr P. Sedov) instead of the |
| home-bp-diary-summary | 2.2.0 | P3 | 15/15 | 12/15 | A f 9/10; p 3/5; F f 10/10; p 5/5 | GENUINE | inf-3 |  | keeps the evening session on the 27 August row in the baseline; it holds the 26 August readings taken 20 minut |
| home-bp-diary-summary | 2.2.1 | P3 | 15/15 | 11/15 | A f 7/10; p 4/5; F f 10/10; p 5/5 | GENUINE | inf-3 |  | keeps the evening session on the 27 August row in the baseline; it holds the 26 August readings taken 20 minut |
| home-bp-diary-summary | 2.3.0 | P3 | 5/5 | 2/5 | A p 2/5; F p 5/5 |  | inf-3 |  | keeps the evening session on the 27 August row in the baseline; it holds the 26 August readings taken 20 minut |
| home-bp-diary-summary | 2.4.0 | P3 | 5/5 | - | F p 5/5 |  | inf-4 |  | keeps the evening session on the 27 August row in the baseline; it holds the 26 August readings taken 20 minut |
| home-bp-diary-summary | 2.5.0 | P3 | 5/5 | - | F p 5/5 |  | inf-4 |  | keeps the evening session on the 27 August row in the baseline; it holds the 26 August readings taken 20 minut |
| home-bp-diary-summary | 2.6.0 | P3 | 2/5 | - | F p 2/5 |  | inf-5 |  | keeps the evening session on the 27 August row in the baseline; it holds the 26 August readings taken 20 minut |
| home-bp-diary-summary | 2.7.0 | P3 | 5/5 | - | F p 5/5 |  | inf-5 |  | keeps the evening session on the 27 August row in the baseline; it holds the 26 August readings taken 20 minut |
| insurance-secrecy-register | 1.1.0 | P1 | 2/5 | - | F p 2/5 |  | inf-3 |  | enters C05 as included (2019 edition, 1,000,000) and C01 as not determinable; the writ names Mila Orn, whom Ha |
| insurance-secrecy-register | 1.2.0 | P1 | 1/5 | 0/5 | A p 0/5; F p 1/5 |  | inf-3 |  | enters C05 as included (2019 edition, 1,000,000, share 100) and C01 as not determinable; the writ names Mila O |
| insurance-secrecy-register | 1.2.0 | P4 | 1/5 | 1/5 | A p 1/5; F p 1/5 |  | inf-3 |  | excludes C02 and enters C07 as included (2019, 500,000, share 100); the drive is 'the claims clerk's' and hold |
| kibo-budget-cap-review | 2.3.0 | P3 | 15/15 | 13/15 | A f 8/10; p 5/5; F f 10/10; p 5/5 | GENUINE | inf-4 |  | prices Cinder Glade at 0.70 (the misfiled Japanese foil) instead of 1.30 and Kessig Wolf Run at 0.95 instead o |
| kibo-budget-cap-review | 2.3.1 | P3 | 15/15 | 11/15 | A f 8/10; p 3/5; F f 10/10; p 5/5 | GENUINE | inf-4 |  | prices Cinder Glade at 0.70 (the misfiled Japanese foil) instead of 1.30 and Kessig Wolf Run at 0.95 instead o |
| kibo-budget-cap-review | 2.4.0 | P3 | 5/5 | 4/5 | A p 4/5; F p 5/5 |  | inf-4 |  | prices Cinder Glade at 0.70 (the misfiled Japanese foil) instead of 1.30 and Kessig Wolf Run at 0.95 instead o |
| kibo-budget-cap-review | 2.5.0 | P3 | 4/5 | - | F p 4/5 |  | inf-5 |  | prices Cinder Glade at 0.70 (the misfiled Japanese foil) instead of 1.30 and Kessig Wolf Run at 0.95 instead o |
| kibo-budget-cap-review | 2.6.0 | P3 | 4/5 | - | F p 4/5 |  | inf-5 |  | prices Cinder Glade at 0.70 (the misfiled Japanese foil) instead of 1.30 and Kessig Wolf Run at 0.95 instead o |
| kibo-budget-cap-review | 2.7.0 | P3 | 5/5 | - | F p 5/5 |  | inf-6 |  | prices Cinder Glade at 0.70 (the misfiled Japanese foil) instead of 1.30 and Kessig Wolf Run at 0.95 instead o |
| killzone-journal-review | 1.1.0 | P2 | 1/5 | 0/5 | A p 0/5; F p 1/5 | BLIND-1.0 | inf-3 |  | 61807240 r = 3.5 ((101.50 + 341.50) / 125) instead of 0.8, and 61807420 r = 0.4 (first half only, 146.50 / 300 |
| killzone-journal-review | 1.2.0 | P2 | 0/5 | 0/5 | A p 0/5; F p 0/5 |  | inf-3 |  | 61807240 r = 3.5 ((101.50 + 341.50) / 125) instead of 0.8, and 61807420 r = 0.4 (first half only, 146.50 / 300 |
| killzone-journal-review | 1.2.0 | P3 | 0/5 | 0/5 | A p 0/5; F p 0/5 |  | inf-3 |  | call_agenda ['61808650'] instead of ['61814733']: the write-up Nadia heard on the 25 Oct call ('his write-up f |
| ktp-lesson-plan-alignment | 2.1.0 | P2 | 5/5 | - | F p 5/5 | AMBIGUOUS | inf-5 |  | L07 dated 2026-10-13 with topic 7 and L08 dated 2026-10-20 with topic 8 (the journal's keys); in the week of 1 |
| ktp-lesson-plan-alignment | 2.2.0 | P2 | 0/5 | - | F p 0/5 |  | inf-7 |  | L07 dated 2026-10-13 with topic 7 and L08 dated 2026-10-20 with topic 8 (the journal's keys); in the week of 1 |
| ktp-lesson-plan-alignment | 2.3.0 | P2 | 0/5 | 0/5 | A p 0/5; F p 0/5 |  | inf-4 |  | L07 dated 2026-10-13 with topic 7 and L08 dated 2026-10-20 with topic 8 (the journal's links). Truth: the fire |
| lassa-kap-results-sheet | 1.1.0 | P1 | 0/15 | 0/15 | A f 0/10; p 0/5; F f 0/10; p 0/5 | BLIND-1.0 | inf-3 |  | Faculty of Sciences 130 and Faculty of Early Childhood and Primary Education 30 (the keyed batches) instead of |
| lassa-kap-results-sheet | 1.2.0 | P1 | 0/5 | 0/5 | A p 0/5; F p 0/5 |  | inf-4 |  | Faculty of Sciences 130 and Faculty of Early Childhood and Primary Education 30 (the keyed batches) instead of |
| line-colour-census | 1.0.0 | P2 | 5/15 | 9/15 | A f 6/10; p 3/5; F f 4/10; p 1/5 | DEFECT | inf-4 |  | a false merge: the hub row keyed NBR 5 is folded into Northbridge's harbour line, so Southbridge keeps lines 1 |
| line-colour-census | 1.2.0 | P2 | 0/5 | 0/5 | A p 0/5; F p 0/5 |  | inf-4 |  | a false merge: the hub row keyed NBR 5 is folded into Northbridge's harbour line, so Southbridge keeps lines 1 |
| line-colour-census | 1.2.0 | P5 | 5/5 | 2/5 | A p 2/5; F p 5/5 |  | inf-4 |  | a keying slip read on its printed key: the April 2017 colour change the studio entered under line 5 is applied |
| line-reference-belegliste | 1.0.0 | P3 | 0/5 | - | F p 0/5 |  | inf-2 |  | cites C12 as B Z. 9 (Anton knocking at the neighbour's door) instead of C Z. 5 |
| line-reference-belegliste | 1.1.0 | P3 | 0/5 | - | F p 0/5 |  | inf-3 |  | keying slip followed: C12 cited as B Z. 9 (Anton knocking at the neighbour's door) instead of C Z. 5-6 (the na |
| line-reference-belegliste | 1.2.0 | P3 | 0/5 | 0/5 | A p 0/5; F p 0/5 |  | inf-2 |  | keying slip followed: C12 cited as B Z. 9 (Anton knocking at the neighbour's door) instead of C Z. 5-6 (the na |
| manhole-excavation-valuation | 1.1.0 | P4 | 1/5 | - | F p 1/5 |  | inf-3 |  | A03 at issue 1's 11.367 (11.55, IV-04's figure) and A04 at 11.197 (9.30) instead of A03 12.22 and A04 9.55; th |
| manhole-excavation-valuation | 1.2.0 | P4 | 0/5 | 0/5 | A p 0/5; F p 0/5 |  | inf-3 |  | A03 at issue 1's 11.367 (11.55, IV-04's figure) and A04 at 11.357 (8.80) instead of A03 11.59 and A04 8.83; th |
| moisturiser-price-screen | 2.2.0 | P4 | 12/15 | 5/15 | A f 3/10; p 2/5; F f 9/10; p 3/5 | BLIND-1.0 | inf-3 |  | BN-2109 (Revivo gel cream) shortlisted on a brand answer that was about the jelly, and BN-2105 (the one petrol |
| moisturiser-price-screen | 2.3.0 | P4 | 2/5 | 1/5 | A p 1/5; F p 2/5 |  | inf-3 |  | BN-2109 (Revivo gel cream) shortlisted on a brand answer that was about the jelly, and BN-2105 (the one petrol |
| mustangs-tryout-roster | 2.1.0 | P10 | 3/5 | 5/5 | A p 5/5; F p 3/5 | BLIND-1.0 | inf-3 |  | MU-115 (the parent's older boy) expected at the third session and not noticed; the Bronx Zoo overnight change, |
| mustangs-tryout-roster | 2.1.0 | P11 | 3/5 | 5/5 | A p 5/5; F p 3/5 | BLIND-1.0 | inf-3 | re | MU-115 left off the attendance-notice list in step 3 |
| mustangs-tryout-roster | 2.2.0 | P10 | 1/5 | 5/5 | A p 5/5; F p 1/5 |  | inf-3 |  | MU-115 (the parent's older boy) expected at the third session and not noticed; the Bronx Zoo overnight change, |
| mustangs-tryout-roster | 2.2.0 | P11 | 2/5 | 5/5 | A p 5/5; F p 2/5 |  | inf-3 | re | MU-115 left off the attendance-notice list in step 3 |
| niche-shelving-screen | 1.0.0 | P3 | 0/5 | 0/5 | A p 0/5; F p 0/5 |  | inf-3 |  | applies the reply to WE-2710 by its printed code, so the bamboo corner shelf WE-2170 stays not_determinable in |
| niche-shelving-screen | 1.1.0 | P3 | 1/15 | 10/15 | A f 6/10; p 4/5; F f 0/10; p 1/5 |  | inf-3 |  | a false merge: attaches the reply to WE-2710 by its printed name, so the telescopic bamboo shelf WE-2170 stays |
| niche-shelving-screen | 1.3.0 | P3 | 0/5 | 0/5 | A p 0/5; F p 0/5 |  | inf-3 |  | a false merge: attaches the reply to WE-2710 by its printed name, so the telescopic bamboo shelf WE-2170 stays |
| niche-shelving-screen | 1.3.0 | P6 | 0/5 | 1/5 | A p 1/5; F p 0/5 |  | inf-4 |  | a keying slip followed: the wall fixing goes to TORNBY HV-1035 (excluded not_free_standing instead of height)  |
| pathway-choice-audit | 1.0.0 | P2 | 0/5 | 0/5 | A p 0/5; F p 0/5 |  | st-v1 |  | records each choice under the code written on the slip (S03 as ST2075, S22 as SS1061) and marks a slip whose w |
| pathway-choice-audit | 2.0.0 | P2 | 15/15 | 15/15 | A f 10/10; p 5/5; F f 10/10; p 5/5 | GENUINE | inf-3 |  | keys S13 to G9-009 (Isaac Kamau, Arts & Sports Science), so its STEM combination is another pathway's (NONE) a |
| pathway-choice-audit | 2.1.0 | P2 | 5/5 | 5/5 | A p 5/5; F p 5/5 |  | inf-3 |  | keys S13 to G9-009 (Isaac Kamau, Arts & Sports Science), so its STEM combination is another pathway's (NONE) a |
| pathway-choice-audit | 2.2.0 | P2 | 5/5 | - | F p 5/5 |  | inf-4 |  | keys S13 to G9-009 (Isaac Kamau, Arts & Sports Science), so its STEM combination is another pathway's (NONE).  |
| pathway-choice-audit | 2.3.0 | P2 | 10/15 | - | F f 7/10; p 3/5 | BLIND-1.0 | inf-4 |  | keys S13 to G9-009 (Isaac Kamau, Arts & Sports Science), so its STEM combination is another pathway's (NONE).  |
| pathway-choice-audit | 2.4.0 | P2 | 2/5 | - | F p 2/5 |  | inf-4 |  | keys S13 to G9-009 (Isaac Kamau, Arts & Sports Science), so its STEM combination is another pathway's (NONE).  |
| posting-month-close | 1.0.0 | P5 | 0/5 | - | F p 0/5 |  | inf-2 |  | gives the bakery's order (tracker 'Nova', logo + menu card for a home bakery) the source LinkedIn instead of I |
| posting-month-close | 1.1.0 | P5 | 0/5 | - | F p 0/5 |  | inf-4 |  | keying slip: gives the menu-card order (tracker 'Nova', logo + menu card, delivered 19 September) the source F |
| posting-month-close | 1.2.0 | P1 | 0/5 | 0/5 | A p 0/5; F p 0/5 |  | inf-3 |  | keying slip: gives the menu-card order (tracker client 'Nova', logo + menu card, delivered 19 September) the s |
| probation-answer-key | 2.2.0 | P4 | 10/15 | 15/15 | A f 10/10; p 5/5; F f 6/10; p 4/5 | AMBIGUOUS | inf-2 |  | case 8 'незаконно' (contract 14.09.2026 -> 2026 text, a daughter born 11.02.2025 is under three) and case 6 'з |
| probation-answer-key | 2.3.0 | P4 | 3/5 | 5/5 | A p 5/5; F p 3/5 |  | inf-2 |  | case 8 'незаконно' (contract 14.09.2026 -> 2026 text, a daughter born 11.02.2025 is under three) and case 6 'з |
| probation-answer-key | 2.4.0 | P4 | 0/5 | 0/5 | A p 0/5; F p 0/5 |  | inf-3 |  | case 8 'незаконно' (contract 14.09.2026 -> 2026 text, a daughter born 11.02.2025 is under three) and case 6 'з |
| profile-copy-claims-audit | 2.1.0 | P4 | 0/15 | 0/15 | A f 0/10; p 0/5; F f 0/10; p 0/5 |  | inf-5 |  | a false merge: joins the google_maps row to the guest route its label names, although the Reserve button was o |
| profile-copy-claims-audit | 2.2.0 | P6 | 15/15 | 0/15 | A f 0/10; p 0/5; F f 10/10; p 5/5 | GENUINE | inf-2 |  | a false merge on the printed playlist key: counts the February 2026 upload 'A cellar's worth of stories' (the  |
| profile-copy-claims-audit | 2.3.0 | P6 | 14/15 | 0/15 | A f 0/10; p 0/5; F f 9/10; p 5/5 | GENUINE | inf-2 |  | a false merge on the printed playlist key: counts the February 2026 upload 'A cellar's worth of stories' (the  |
| profile-copy-claims-audit | 2.4.0 | P6 | 15/15 | 0/15 | A f 0/10; p 0/5; F f 10/10; p 5/5 | GENUINE | inf-2 |  | a false merge on the printed playlist key: counts the February 2026 upload 'A cellar's worth of stories' (the  |
| profile-copy-claims-audit | 2.5.0 | P6 | 5/5 | 0/5 | A p 0/5; F p 5/5 |  | inf-2 |  | counts every upload in the show's playlist as an episode (33); the February client film keyed into the show's  |
| profile-copy-claims-audit | 2.6.0 | P6 | 3/5 | 0/5 | A p 0/5; F p 3/5 |  | inf-2 |  | counts every upload in the show's playlist as an episode (33); the February client film keyed into the show's  |
| profile-copy-claims-audit | 2.7.0 | P6 | 2/5 | 0/5 | A p 0/5; F p 2/5 |  | inf-2 |  | counts every upload in the show's playlist as an episode (33); the February client film keyed into the show's  |
| profile-copy-claims-audit | 2.8.0 | P6 | 5/5 | 0/5 | A p 0/5; F p 5/5 |  | inf-2 |  | counts every upload in the show's playlist as an episode (33); the February client film keyed into the show's  |
| psychopathy-evidence-screen | 2.1.0 | P4 | 5/5 | - | F p 5/5 | AMBIGUOUS | inf-4 |  | R11 qualifies with n 98 on the clinic row filed under it, and R09 is not determinable; the row was raised and  |
| psychopathy-evidence-screen | 2.2.0 | P4 | 0/5 | - | F p 0/5 |  | inf-4 |  | R11 qualifies with n 98 on the clinic row filed under it, and R09 is not determinable; the row was raised and  |
| psychopathy-evidence-screen | 2.3.0 | P4 | 6/15 | 11/15 | A f 7/10; p 4/5; F f 4/10; p 2/5 | BLIND-1.0 | inf-4 |  | R11 qualifies with n 98 on the row filed under it, and R09 is not determinable; the row quotes a full text on  |
| refurb-laptop-screen | 1.1.0 | P5 | 0/5 | - | F p 0/5 |  | inf-2 |  | title keyword: BW-106 financed and passed at £172.36 (truth £164.00 fail), BW-111 refused the stretch and fail |
| refurb-laptop-screen | 1.2.0 | P5 | 5/5 | - | F p 5/5 | AMBIGUOUS | inf-4 |  | a false merge: Jamie's report keyed to the row it is jotted on: BW-113 financed and passed at £178.67 (truth £ |
| refurb-laptop-screen | 1.3.0 | P5 | 0/5 | - | F p 0/5 |  | inf-5 |  | a false merge: Jamie's report keyed to the row it is jotted on: BW-113 financed and passed at £178.67 (truth:  |
| refurb-laptop-screen | 1.4.0 | P5 | 0/5 | 4/5 | A p 4/5; F p 0/5 |  | inf-4 |  | a false merge: Jamie's report keyed to the row it is jotted on: BW-113 financed and passed at £178.67 (truth:  |
| sandwich-image-audit | 1.3.0 | P2 | 0/5 | 0/5 | A p 0/5; F p 0/5 |  | inf-3 |  | the bread-less file is left out of download_register and ZK-218 is needs_photo (live when P3 is also missed) |
| spice-pitch-deck-qa | 2.0.0 | P1 | 1/5 | - | F p 1/5 |  | inf-2 |  | counts the conversion slide (NV-16) as showing a kit asset because its colour strip was placed under the kit p |
| spice-pitch-deck-qa | 2.1.0 | P1 | 0/5 | - | F p 0/5 |  | inf-2 |  | counts the conversion slide (NV-16) as showing a kit asset because its colour strip was placed under the kit p |
| spice-pitch-deck-qa | 2.1.0 | P3 | 0/5 | - | F p 0/5 |  | inf-2 |  | records row 12 ('Four lines crowd the cart. Drop the Turmeric Powder line and show three.') against NV-15, the |
| spice-pitch-deck-qa | 2.2.0 | P1 | 0/5 | 0/5 | A p 0/5; F p 0/5 |  | inf-2 |  | counts the conversion slide (NV-16) as showing a kit asset because its colour strip was placed under the kit p |
| spice-pitch-deck-qa | 2.2.0 | P3 | 3/5 | 0/5 | A p 0/5; F p 3/5 |  | inf-2 |  | lists the phone slide (NV-15, the ID printed beside the cart note) as a REWORK slide and leaves the conversion |
| spice-pitch-deck-qa | 2.3.0 | P1 | 0/5 | 0/5 | A p 0/5; F p 0/5 |  | inf-3 |  | leaves the pillars slide NV-05 out of credit_slides: the register files the icon set under the moodboard's ID, |
| spice-pitch-deck-qa | 2.3.0 | P3 | 3/5 | 0/5 | A p 0/5; F p 3/5 |  | inf-2 |  | lists the phone slide (NV-15, the ID printed beside the cart note) as a REWORK slide and leaves the conversion |
| station-register-consolidation | 2.0.0 | P1 | 0/5 | - | F p 0/5 |  | inf-6 |  | matches Table 2-2 by printed station name and river: 47-942 gets 0.141 instead of 0.219 and 47-125 gets null i |
| station-register-consolidation | 2.1.0 | P1 | 0/5 | - | F p 0/5 |  | inf-6 |  | matches Table 2-2 by printed station name and river: 47-942 gets 0.141 instead of 0.219 and 47-125 gets null i |
| station-register-consolidation | 2.1.0 | P2 | 0/5 | - | F p 0/5 |  | inf-6 |  | closes 47-942 on the strength of the depot's 2024 intake from 'the upper Rameh gauge' (a false merge with the  |
| station-register-consolidation | 2.2.0 | P1 | 0/5 | - | F p 0/5 |  | inf-6 |  | matches Table 2-2 by printed station name and river: 47-942 gets 0.141 instead of 0.219 and 47-125 gets null i |
| station-register-consolidation | 2.2.0 | P2 | 2/5 | - | F p 2/5 |  | inf-7 |  | closes 47-942 because the depot's 2024 flood intake is keyed under its code; Garmsar's active hydrometric list |
| station-register-consolidation | 2.3.0 | P1 | 0/5 | 0/5 | A p 0/5; F p 0/5 |  | inf-5 |  | closes 47-005 because the store's 2022 return is keyed under its code; Firuzkuh's active hydrometric list lose |
| station-register-consolidation | 2.3.0 | P2 | 0/5 | 0/5 | A p 0/5; F p 0/5 |  | inf-7 |  | closes 47-942 because the depot's 2024 flood intake is keyed under its code; Garmsar's active hydrometric list |
| student-laptop-shortlist | 2.1.0 | P2 | 0/5 | - | F p 0/5 |  | inf-5 |  | a keying slip followed: L-404 out_of_stock and L-413 shortlisted (pick L-413), instead of L-413 out_of_stock ( |
| student-laptop-shortlist | 2.2.0 | P2 | 0/5 | 4/5 | A p 4/5; F p 0/5 |  | inf-5 |  | the keying slip followed: L-404 out_of_stock and L-413 shortlisted (pick L-413), instead of L-413 out_of_stock |
| student-laptop-shortlist | 2.3.0 | P2 | 0/5 | 1/5 | A p 1/5; F p 0/5 |  | inf-5 |  | the keying slip followed: L-404 out_of_stock and L-413 shortlisted (pick L-413), instead of L-413 out_of_stock |
| suitcase-cover-matrix-check | 2.1.0 | P5 | 14/15 | 15/15 | A f 10/10; p 5/5; F f 10/10; p 4/5 | GENUINE | inf-3 |  | 25 designs: the 24 prints plus 'Воздушные шары', with 'Ретро-марки' kept. Truth: the drawing that cannot be us |
| suitcase-cover-matrix-check | 2.1.1 | P5 | 14/15 | 14/15 | A f 9/10; p 5/5; F f 9/10; p 5/5 | GENUINE | inf-3 |  | 25 designs: the 24 prints plus 'Воздушные шары', with 'Ретро-марки' kept. Truth: the drawing that cannot be us |
| suitcase-cover-matrix-check | 2.2.0 | P5 | 5/5 | - | F p 5/5 |  | inf-4 |  | 25 designs: the 24 prints plus 'Воздушные шары', with 'Ретро-марки' kept. Truth: the drawing that cannot be us |
| suitcase-cover-matrix-check | 2.3.0 | P5 | 4/5 | - | F p 4/5 |  | inf-4 |  | 25 designs: the 24 prints plus 'Воздушные шары', with 'Ретро-марки' kept. Truth: the drawing that cannot be us |
| suitcase-cover-matrix-check | 2.4.0 | P5 | 4/5 | - | F p 4/5 |  | inf-5 |  | 25 designs: the 24 prints plus 'Воздушные шары', with 'Ретро-марки' kept. Truth: the drawing that cannot be us |
| suitcase-cover-matrix-check | 2.5.0 | P5 | 2/5 | - | F p 2/5 |  | inf-5 |  | 25 designs: the 24 prints plus 'Воздушные шары', with 'Ретро-марки' kept. Truth: the drawing that cannot be us |
| timesheet-overtime-review | 2.2.0 | P4 | 12/15 | 15/15 | A f 10/10; p 5/5; F f 7/10; p 5/5 | GENUINE | inf-4 |  | keeps Sunday's number-line-strips block (105 min) on the LO6 task 5512 it is keyed under: LO6 405 and L2 105 i |
| timesheet-overtime-review | 2.3.0 | P4 | 0/5 | 5/5 | A p 5/5; F p 0/5 |  | inf-4 |  | keeps Sunday's number-line-strips block (105 min) on the LO6 task 5512 it is keyed under: LO6 405 and L2 105 i |
| timesheet-overtime-review | 2.4.0 | P4 | 7/15 | - | F f 4/10; p 3/5 | BLIND-1.0 | inf-5 |  | keeps Sunday's number-line-strips block (105 min) on the LO6 task 5512 it is keyed under: LO6 405 and L2 105 i |
| timesheet-overtime-review | 2.5.0 | P4 | 4/5 | - | F p 4/5 |  | inf-5 |  | keeps Sunday's number-line-strips block (105 min) on the LO6 task 5512 it is keyed under: LO6 405 and L2 105 i |
| timesheet-overtime-review | 2.6.0 | P4 | 5/5 | - | F p 5/5 |  | inf-5 |  | keeps Sunday's number-line-strips block (105 min) on the LO6 task 5512 it is keyed under: LO6 405 and L2 105 i |

### CV.round: Rounding convention (cut vs half-up) from worked or filed figures

| task | ver | P | F | A | stages | verdict | S/I | re | misreading |
|---|---|---|---|---|---|---|---|---|---|
| ats-embedded-screening-register | 1.1.0 | P4 | 0/15 | 0/15 | A f 0/10; p 0/5; F f 0/10; p 0/5 |  | inf-4 |  | rounds the in-house results half-up: C-301 72.7 and C-305 64.7 instead of 72.6 and 64.6 (C-302 81.3 either way |
| ats-embedded-screening-register | 1.2.0 | P4 | 0/5 | - | F p 0/5 |  | inf-2 |  | rounds the in-house results half-up: C-301 72.7 and C-305 64.7 instead of 72.6 and 64.6 (C-302 81.3 either way |
| ats-embedded-screening-register | 1.3.0 | P4 | 1/5 | - | F p 1/5 |  | inf-2 |  | rounds the in-house results half-up: C-301 72.7 and C-305 64.7 instead of 72.6 and 64.6 (C-302 81.3 either way |
| ats-embedded-screening-register | 1.4.0 | P4 | 0/5 | - | F p 0/5 |  | inf-2 |  | rounds the in-house results half-up: C-301 72.7 and C-305 64.7 instead of 72.6 and 64.6 (C-302 81.3 either way |
| billiard-shift-audit | 1.0.0 | P5 | 0/5 | 0/5 | A p 0/5; F p 0/5 |  | st-v1 |  | rounds the 15% club discount on 750 (112,50) half to even, as Python's round() does, to 112 (the POS figure) i |
| billiard-shift-audit | 2.0.0 | P4 | 3/5 | 0/5 | A p 0/5; F p 3/5 | BLIND-1.0 | inf-2 |  | takes 15% of the whole play amount and rounds once (225); both filed exemplars (1 200 -> 181, 1 350 -> 204) on |
| billiard-shift-audit | 2.1.0 | P4 | 3/5 | 0/5 | A p 0/5; F p 3/5 |  | inf-2 |  | takes 15% of the whole play amount and rounds once (225); both filed exemplars (1 200 -> 181, 1 350 -> 204) on |
| blockprint-winter-close | 1.1.0 | P3 | 0/5 | - | F p 0/5 |  | inf-4 |  | R-1214 73.50 and R-0308 44.50 (exact half) or 74 and 45 (half-up) instead of 73 and 44; hotel total 367.00 or  |
| blockprint-winter-close | 1.2.0 | P3 | 0/5 | 0/5 | A p 0/5; F p 0/5 |  | inf-4 |  | R-1214 73.50 and R-0308 44.50 (exact half) or 74 and 45 (half-up) instead of 73 and 44; hotel total 367.00 or  |
| brightwater-spec-qa | 1.2.0 | P4 | 1/5 | - | F p 1/5 |  | inf-4 |  | states 11.2 million TEU (rounded) on every throughput string instead of the house truncation's 11.1 |
| brightwater-spec-qa | 1.3.0 | P4 | 1/15 | 13/15 | A f 9/10; p 4/5; F f 0/10; p 1/5 | GENUINE | inf-5 |  | states 11.2 million TEU (rounded) on every throughput string instead of the house truncation's 11.1 |
| cafe-kitchen-schedule-revisions | 2.0.0 | P5 | 0/5 | - | F p 0/5 |  | inf-3 |  | writes the exact sum 5.22 m; the filed BOQ (163 + 92 + 204 = 459 cm written as 4.80 m) takes each top up to th |
| cafe-kitchen-schedule-revisions | 2.1.0 | P11 | 5/15 | 2/15 | A f 0/10; p 2/5; F f 3/10; p 2/5 | GENUINE | inf-2 |  | builds at the floor (87): rack 127 / 157, moved. The standard's 6.1 figure (78 + 3 = 81 built at 85) and the f |
| cafe-kitchen-schedule-revisions | 2.1.0 | P3 | 0/15 | 0/15 | A f 0/10; p 0/5; F f 0/10; p 0/5 |  | inf-2 |  | rounds the half centimetre: 239 / 200 / 438. The standard's 3.2 figure (155.5 written 155) and the filed TC-25 |
| cafe-kitchen-schedule-revisions | 2.1.0 | P5 | 0/15 | 0/15 | A f 0/10; p 0/5; F f 0/10; p 0/5 |  | inf-2 |  | writes 5.2 (or 5.22, or 5.3 taking the total up); the standard's 5.3 figure (163 -> 1.7; 92 + 204 -> 3.1) and  |
| cafe-kitchen-schedule-revisions | 2.1.1 | P11 | 3/15 | 0/15 | A f 0/10; p 0/5; F f 2/10; p 1/5 | GENUINE | inf-2 |  | builds at the floor (87): rack 127 / 157, moved. The standard's 6.1 figure (78 + 3 = 81 built at 85) and the f |
| cafe-kitchen-schedule-revisions | 2.1.1 | P3 | 0/15 | 0/15 | A f 0/10; p 0/5; F f 0/10; p 0/5 |  | inf-2 |  | rounds the half centimetre: 239 / 200 / 438. The standard's 3.2 figure (155.5 written 155) and the filed TC-25 |
| cafe-kitchen-schedule-revisions | 2.1.1 | P5 | 1/15 | 0/15 | A f 0/10; p 0/5; F f 0/10; p 1/5 |  | inf-2 |  | writes 5.2 (or 5.22, or 5.3 taking the total up); the standard's 5.3 figure (163 -> 1.7; 92 + 204 -> 3.1) and  |
| cafe-kitchen-schedule-revisions | 2.2.0 | P11 | 2/5 | - | F p 2/5 |  | inf-2 |  | builds at the floor (87): rack 127 / 157, moved. The standard's 6.1 figure (78 + 3 = 81 built at 85) and the f |
| cafe-kitchen-schedule-revisions | 2.2.0 | P3 | 0/5 | - | F p 0/5 |  | inf-2 |  | rounds the half centimetre: 239 / 200 / 438. The standard's 3.2 figure (155.5 written 155) and the filed TC-25 |
| cafe-kitchen-schedule-revisions | 2.2.0 | P5 | 0/5 | - | F p 0/5 |  | inf-2 |  | writes 5.2 (or 5.22, or 5.3 taking the total up); the standard's 5.3 figure (163 -> 1.7; 92 + 204 -> 3.1) and  |
| cafe-kitchen-schedule-revisions | 2.3.0 | P11 | 4/15 | - | F f 4/10; p 0/5 | BLIND-1.0 | inf-2 |  | builds at the floor (87): rack 127 / 157, moved. The standard's 6.1 figure (78 + 3 = 81 built at 85) and the f |
| cafe-kitchen-schedule-revisions | 2.3.0 | P3 | 0/15 | - | F f 0/10; p 0/5 |  | inf-2 |  | rounds the half centimetre: 239 / 200 / 438. The standard's 3.2 figure (155.5 written 155) and the filed TC-25 |
| cafe-kitchen-schedule-revisions | 2.3.0 | P5 | 3/15 | - | F f 2/10; p 1/5 |  | inf-2 |  | writes 5.2 (or 5.22, or 5.3 taking the total up); the standard's 5.3 figure (163 -> 1.7; 92 + 204 -> 3.1) and  |
| coloring-book-retitle-audit | 2.1.0 | P3 | 0/5 | - | F p 0/5 |  | inf-2 |  | rounds 0.1486 in to 0.15; the rule's two worked figures (150 pages 0.3378 -> 0.33, 222 pages 0.4999 -> 0.49) f |
| coloring-book-retitle-audit | 2.2.0 | P3 | 0/15 | 0/15 | A f 0/10; p 0/5; F f 0/10; p 0/5 |  | inf-3 |  | rounds 0.1486 in to 0.15; the rules sheet's two worked spine figures, each doing another job (rule 4.2's odd-p |
| coloring-book-retitle-audit | 2.2.0 | P6 | 0/15 | 0/15 | A f 0/10; p 0/5; F f 0/10; p 0/5 |  | inf-3 | re | re-decision of the spine convention in a fresh session (the retitled cover needs its template): half-up gives  |
| coloring-book-retitle-audit | 2.3.0 | P3 | 0/15 | 0/15 | A f 0/10; p 0/5; F f 0/10; p 0/5 |  | inf-3 |  | rounds 0.1486 in to 0.15; the rules sheet's two worked spine figures, each doing another job (rule 4.2's odd-p |
| coloring-book-retitle-audit | 2.3.0 | P6 | 0/15 | 0/15 | A f 0/10; p 0/5; F f 0/10; p 0/5 |  | inf-3 | re | re-decision of the spine convention in a fresh session (the retitled cover needs its template): half-up gives  |
| coloring-book-retitle-audit | 2.4.0 | P3 | 0/5 | - | F p 0/5 |  | inf-3 |  | rounds 0.1486 in half-up to 0.15. Rule 4.2's odd-page example (210 pages -> 0.47292 -> 0.47) fits half-up AND  |
| coloring-book-retitle-audit | 2.4.0 | P6 | 0/5 | - | F p 0/5 |  | inf-3 | re | re-decision of the spine convention in a fresh session (the retitled cover needs its template): half-up gives  |
| coloring-book-retitle-audit | 2.5.0 | P3 | 0/15 | - | F f 0/10; p 0/5 |  | inf-3 |  | rounds 0.1486 in half-up to 0.15. Rule 4.2's odd-page example (210 pages -> 0.47292 -> 0.47) fits half-up AND  |
| coloring-book-retitle-audit | 2.5.0 | P6 | 0/15 | - | F f 0/10; p 0/5 |  | inf-3 | re | re-decision of the spine convention in a fresh session (the retitled cover needs its template): half-up gives  |
| coloring-book-retitle-audit | 2.6.0 | P3 | 0/5 | - | F p 0/5 |  | inf-4 |  | rounds 0.148632 in half-up to 0.15. Rule 4.2's odd-page example (210 pages -> 0.47292 -> 0.47) fits half-up AN |
| coloring-book-retitle-audit | 2.6.0 | P6 | 0/5 | - | F p 0/5 |  | inf-4 | re | re-decision in a fresh session for the retitled cover's template: half-up gives 0.15, which rule 4.2's 210-pag |
| coop-bp-prefill-sheet | 1.0.0 | P2 | 0/5 | - | F p 0/5 |  | inf-2 |  | monthly fixed costs 5 607 / 4 074 / 5 586 / 6 006 for C01 / C02 / C03 / C05 instead of 5 562 / 4 042 / 5 528 / |
| coop-bp-prefill-sheet | 1.1.0 | P2 | 0/5 | 0/5 | A p 0/5; F p 0/5 |  | inf-2 |  | monthly fixed costs 5 530 / 4 081 / 5 380 / 5 925 for C01 / C02 / C03 / C05 instead of 5 531 / 4 082 / 5 381 / |
| current-affairs-booklet-plan | 1.1.0 | P1 | 1/5 | - | F p 1/5 |  | inf-4 |  | rounds the lakh figure half-up to one decimal (271.7, 114.6) instead of writing it the way the desk's own work |
| current-affairs-booklet-plan | 1.2.0 | P1 | 0/5 | 0/5 | A p 0/5; F p 0/5 |  | inf-3 |  | rounds the Snan Mela's lakh figure half-up (271.7) instead of writing it as the desk's worked figures do, with |
| deck-preread-review | 1.0.0 | P5 | 0/5 | 0/5 | A p 0/5; F p 0/5 |  | st-v1 |  | works the bank achievement (42,128.3 / 39,800.0) in binary floating point and rounds it the default way: 105.8 |
| deck-preread-review | 2.1.0 | P4 | 3/5 | - | F p 3/5 |  | inf-3 |  | S-02 105.9, S-03 88.9, S-11 -1.6, S-15 8.8, S-19 7.2 instead of 105.8, 88.8, -1.5, 8.7, 7.1 (19.975 shown as 1 |
| deck-preread-review | 2.2.0 | P4 | 12/15 | 15/15 | A f 10/10; p 5/5; F f 8/10; p 4/5 | GENUINE | inf-3 |  | S-02 105.9, S-03 88.9, S-11 -1.6, S-15 8.8, S-19 7.2 instead of 105.8, 88.8, -1.5, 8.7, 7.1 (19.975 shown as 1 |
| deck-preread-review | 2.3.0 | P4 | 10/15 | 15/15 | A f 10/10; p 5/5; F f 7/10; p 3/5 | GENUINE | inf-3 |  | S-02 105.9, S-03 88.9, S-11 -1.6, S-15 8.8, S-19 7.2 instead of 105.8, 88.8, -1.5, 8.7, 7.1 (19.975 shown as 1 |
| deck-preread-review | 2.4.0 | P4 | 1/5 | 5/5 | A p 5/5; F p 1/5 |  | inf-4 |  | S-02 105.9, S-03 88.9, S-11 -1.6, S-15 8.8, S-19 7.2 instead of 105.8, 88.8, -1.5, 8.7, 7.1 (19.975 shown as 1 |
| deck-preread-review | 2.5.0 | P4 | 4/15 | 3/15 | A f 3/10; p 0/5; F f 2/10; p 2/5 |  | inf-5 |  | S-02 105.9, S-03 88.9, S-11 -1.6, S-15 8.8, S-19 7.2 instead of 105.8, 88.8, -1.5, 8.7, 7.1 (19.975 shown as 1 |
| deck-preread-review | 2.6.0 | P4 | 1/5 | 1/5 | A p 1/5; F p 1/5 |  | inf-5 |  | S-02 105.9, S-03 88.9, S-11 -1.6, S-15 8.8, S-19 7.2 instead of 105.8, 88.8, -1.5, 8.7, 7.1 (19.975 shown as 1 |
| deck-preread-review | 2.7.0 | P4 | 1/5 | 2/5 | A p 2/5; F p 1/5 |  | inf-5 |  | S-02 105.9, S-03 88.9, S-11 -1.6, S-15 8.8, S-19 7.2 instead of 105.8, 88.8, -1.5, 8.7, 7.1 (19.975 shown as 1 |
| earth-guide-answer-claims | 1.0.0 | P2 | 0/5 | - | F p 0/5 |  | inf-3 |  | rounds to the nearest page, so LA-01 (118 lines), LA-04 (132), LA-05 (254), LA-08 (166), LA-10 (113) and LA-11 |
| earth-guide-answer-claims | 1.1.0 | P2 | 0/5 | 0/5 | A p 0/5; F p 0/5 |  | inf-3 |  | rounds to the nearest tenth: LA-01 2.7, LA-03 3.4, LA-05 5.7, LA-07 5.5, LA-08 3.7, LA-12 2.1 instead of 2.6,  |
| eco-guard-errata-review | 1.0.0 | P5 | 0/5 | 0/5 | A p 0/5; F p 0/5 |  | st-v1 |  | checks the printed rates with binary-float rounding: round(3/40, 2) gives 0.07, so the misprinted FPR 0.07 'ch |
| eco-guard-errata-review | 2.0.0 | P3 | 0/5 | - | F p 0/5 |  | inf-3 |  | rounds exact halves the default way (binary/half-even): the cautious-run false-negative rate stays 0.62 and th |
| eco-guard-errata-review | 2.1.0 | P3 | 5/5 | - | F p 5/5 | AMBIGUOUS | inf-3 |  | writes the A.1 sample size as the next whole number above the bound (2125) where both filed sample sizes of th |
| eco-guard-errata-review | 2.2.0 | P3 | 2/5 | - | F p 2/5 |  | inf-3 |  | writes the A.1 sample size as the next whole number above the bound (2125) where both worked sample sizes in t |
| eco-guard-errata-review | 2.3.0 | P3 | 3/5 | 0/5 | A p 0/5; F p 3/5 |  | inf-3 |  | writes the A.1 sample size as the next whole number above the bound (2125) where both worked sample sizes in t |
| ethics-report-mark-release | 1.0.0 | P2 | 0/5 | - | F p 0/5 |  | inf-3 |  | takes completed hundreds: 1 mark for 2,140 counted words instead of 2. The rule leaves the whole-mark step ope |
| ethics-report-mark-release | 1.1.0 | P2 | 0/5 | 0/5 | A p 0/5; F p 0/5 |  | inf-3 |  | rounds the deduction half-up: 4 instead of 3 for 6% of 65. Graded on the solver's own over_limit_percent and c |
| ethics-report-mark-release | 1.1.0 | P4 | 0/5 | 0/5 | A p 0/5; F p 0/5 |  | inf-3 |  | rounds the excess half-up: over_limit_percent 7 instead of 6. Graded on the solver's own word_count |
| feast-sharing-runsheet | 1.0.0 | P5 | 0/5 | - | F p 0/5 |  | inf-2 |  | adds part-minute segments at their exact value, so the two run-sheets with 2½/1½ and 2½/3½ entries come to 40  |
| feast-sharing-runsheet | 1.1.0 | P5 | 4/5 | - | F p 4/5 | AMBIGUOUS | inf-2 |  | adds part-minute segments at their exact value, so the two run-sheets with 2½/1½ and 2½/3½ entries come to 40  |
| gst-workbook-answer-key | 1.0.0 | P2 | 0/5 | - | F p 0/5 |  | inf-4 |  | S-103 total 802 (truth 804: 2 x (113 + 109 + 180)), S-104 total 3,805 (truth 3,804: 2,564 + 896 + 344), S-105  |
| gst-workbook-answer-key | 1.1.0 | P2 | 0/5 | - | F p 0/5 |  | inf-5 |  | S-103 total 802 (truth 804: 2 x (113 + 109 + 180)), S-104 total 3,805 (truth 3,804: 2,564 + 896 + 344), S-105  |
| gst-workbook-answer-key | 1.2.0 | P2 | 0/5 | 1/5 | A p 1/5; F p 0/5 |  | inf-3 |  | per-line half-up: S-103 total 804 (truth 800 = 2 x (112 + 108 + 180)), S-104 3,803 (truth 3,802 = 2,562 + 896  |
| gst-workbook-answer-key | 1.3.0 | P2 | 0/15 | 10/15 | A f 6/10; p 4/5; F f 0/10; p 0/5 | DEFECT | inf-3 |  | per-line half-up: S-103 total 804 (truth 800 = 2 x (112 + 108 + 180)), S-104 3,803 (truth 3,802 = 2,562 + 896  |
| gst-workbook-answer-key | 1.4.0 | P2 | 0/15 | 0/15 | A f 0/10; p 0/5; F f 0/10; p 0/5 |  | inf-3 |  | per-line half-up: S-103 total 804 (truth 800 = 2 x (112 + 108 + 180)), S-104 3,803 (truth 3,802 = 2,562 + 896  |
| gst-workbook-answer-key | 1.4.1 | P2 | 0/15 | 0/15 | A f 0/10; p 0/5; F f 0/10; p 0/5 |  | inf-3 |  | per-line half-up: S-103 total 804 (truth 800 = 2 x (112 + 108 + 180)), S-104 3,803 (truth 3,802 = 2,562 + 896  |
| gst-workbook-answer-key | 1.5.0 | P2 | 0/5 | 2/5 | A p 2/5; F p 0/5 |  | inf-4 |  | per-line paise dropped: S-103 800 (truth 802 = 2 x floor(401.10)), S-104 3,802 (truth 3,803 = floor(3,803.40)) |
| gst-workbook-answer-key | 1.6.0 | P2 | 0/5 | 3/5 | A p 3/5; F p 0/5 |  | inf-4 |  | per-line paise dropped: S-103 800 (truth 802 = 2 x floor(401.10)), S-104 3,802 (truth 3,803 = floor(3,803.40)) |
| gst-workbook-answer-key | 1.7.0 | P2 | 0/15 | 10/15 | A f 8/10; p 2/5; F f 0/10; p 0/5 | GENUINE | inf-4 |  | per-line paise dropped: S-103 800 (truth 802 = 2 x floor(401.10)), S-104 3,802 (truth 3,803 = floor(3,803.40)) |
| hammamet-voucher-reissue | 2.1.0 | P5 | 0/5 | - | F p 0/5 |  | inf-2 |  | Nabil 23, Sonia 46, Karim 20, Ines 20 (total 109) instead of 21, 49, 18, 18 (total 106): each night's 3,300 /  |
| hammamet-voucher-reissue | 2.2.0 | P5 | 0/5 | 0/5 | A p 0/5; F p 0/5 |  | inf-2 |  | Nabil 23, Sonia 46, Karim 20, Ines 20 (total 109) instead of 21, 42, 18, 18 (total 99): the millimes of each n |
| home-bp-diary-summary | 1.0.0 | P5 | 0/5 | 0/5 | A p 0/5; F p 0/5 |  | st-v1 |  | rounds the R-7 systolic mean (exactly 134.95, stored by a binary float just below) with Python's round() or a  |
| home-bp-diary-summary | 2.1.0 | P4 | 0/5 | - | F p 0/5 |  | inf-3 |  | rounds the gap half-up (24) instead of dropping the fraction (23); graded on the solver's own office and basel |
| home-bp-diary-summary | 2.2.0 | P4 | 4/15 | 0/15 | A f 0/10; p 0/5; F f 3/10; p 1/5 | GENUINE | inf-3 |  | rounds the gap half-up (24) instead of dropping the fraction (23); graded on the solver's own office and basel |
| home-bp-diary-summary | 2.2.1 | P4 | 3/15 | 0/15 | A f 0/10; p 0/5; F f 2/10; p 1/5 | GENUINE | inf-3 |  | rounds the gap half-up (24) instead of dropping the fraction (23); graded on the solver's own office and basel |
| home-bp-diary-summary | 2.3.0 | P4 | 2/5 | 0/5 | A p 0/5; F p 2/5 |  | inf-3 |  | rounds the gap half-up (24) instead of dropping the fraction (23); graded on the solver's own office and basel |
| home-bp-diary-summary | 2.4.0 | P4 | 0/5 | - | F p 0/5 |  | inf-3 |  | rounds the gap half-up (24) instead of dropping the fraction (23); graded on the solver's own office and basel |
| home-bp-diary-summary | 2.5.0 | P4 | 0/5 | - | F p 0/5 |  | inf-3 |  | rounds the gap half-up (24) instead of dropping the fraction (23); graded on the solver's own office and basel |
| home-bp-diary-summary | 2.6.0 | P4 | 1/5 | - | F p 1/5 |  | inf-3 |  | rounds the gap half-up (24) instead of dropping the fraction (23); graded on the solver's own office and basel |
| home-bp-diary-summary | 2.7.0 | P4 | 1/5 | - | F p 1/5 |  | inf-3 |  | rounds the gap half-up (24) instead of dropping the fraction (23); graded on the solver's own office and basel |
| insurance-secrecy-register | 1.0.0 | P5 | 0/5 | - | F p 0/5 |  | inf-3 |  | gives C08 (CC 212(1) and CC 212(3), 2025 edition) a top fine of 5,000,000 (the higher ceiling) instead of 6,50 |
| insurance-secrecy-register | 1.1.0 | P5 | 0/5 | - | F p 0/5 |  | inf-4 |  | gives C08 (CC 212(1) and CC 212(3), 2025 edition) a top fine of 5,000,000 (the higher ceiling) instead of 6,50 |
| insurance-secrecy-register | 1.2.0 | P5 | 0/5 | 0/5 | A p 0/5; F p 0/5 |  | inf-4 |  | writes C03's share as 70 and C11's as 80 (the nearest whole number of 69.7 and 79.8) instead of 69 and 79; the |
| kibo-budget-cap-review | 2.0.0 | P4 | 5/5 | - | F p 5/5 | AMBIGUOUS | inf-3 |  | writes Kibo 115.05, Hardened Scales 23.10 and Maskwood Nexus 14.80 instead of 115.00, 23.00 and 15.00 |
| kibo-budget-cap-review | 2.1.0 | P4 | 0/5 | - | F p 0/5 |  | inf-3 |  | writes Kibo 115.05, Hardened Scales 23.10 and Maskwood Nexus 14.80 instead of 115.00, 23.00 and 15.00 |
| kibo-budget-cap-review | 2.2.0 | P4 | 0/5 | - | F p 0/5 |  | inf-4 |  | bare product: Kibo 115.05, Hardened Scales 23.30, Maskwood Nexus 14.60 instead of 115.00, 23.50, 14.50; whole  |
| kibo-budget-cap-review | 2.3.0 | P4 | 0/15 | 0/15 | A f 0/10; p 0/5; F f 0/10; p 0/5 |  | inf-4 |  | bare product: Kibo 115.05, Hardened Scales 23.30, Maskwood Nexus 14.60 instead of 115.00, 23.50, 14.50; whole  |
| kibo-budget-cap-review | 2.3.1 | P4 | 0/15 | 0/15 | A f 0/10; p 0/5; F f 0/10; p 0/5 |  | inf-4 |  | bare product: Kibo 115.05, Hardened Scales 23.30, Maskwood Nexus 14.60 instead of 115.00, 23.50, 14.50; whole  |
| kibo-budget-cap-review | 2.4.0 | P4 | 0/5 | 0/5 | A p 0/5; F p 0/5 |  | inf-4 |  | nearest whole real: Branching Evolution 30 and Maskwood Nexus 15 instead of 29 and 14 (Kibo 115 and Hardened S |
| kibo-budget-cap-review | 2.5.0 | P4 | 1/5 | - | F p 1/5 |  | inf-4 |  | whole reais: Branching Evolution 30, Hardened Scales 23, Maskwood Nexus 15 instead of 29.50, 23.50, 14.50; bar |
| kibo-budget-cap-review | 2.6.0 | P4 | 1/5 | - | F p 1/5 |  | inf-4 |  | whole reais: Branching Evolution 30, Hardened Scales 23, Maskwood Nexus 15 instead of 29.50, 23.50, 14.50; bar |
| kibo-budget-cap-review | 2.7.0 | P4 | 0/5 | - | F p 0/5 |  | inf-4 |  | whole reais: Branching Evolution 30, Hardened Scales 23, Maskwood Nexus 15 instead of 29.50, 23.50, 14.50; bar |
| killzone-journal-review | 1.1.0 | P4 | 0/5 | 0/5 | A p 0/5; F p 0/5 |  | inf-5 |  | half-up R: 61804215 1.5 (not 1.4), 61805102 2.3 (2.2), 61810274 0.4 (0.3), 61812870 1.7 (1.6), 61815402 1.1 (1 |
| killzone-journal-review | 1.2.0 | P4 | 5/5 | 0/5 | A p 0/5; F p 5/5 |  | inf-3 |  | half-up R: 61804215 1.5 (not 1.4), 61805102 2.3 (2.2), 61810274 0.4 (0.3), 61812870 1.7 (1.6), 61815402 1.1 (1 |
| ktp-lesson-plan-alignment | 2.1.0 | P4 | 1/5 | - | F p 1/5 | BLIND-1.0 | inf-3 |  | term1_coverage 83 (10 of 12 = 83.3 % in ordinary whole per cent); both worked figures (13/15 = 86.7 -> 85, 8/9 |
| ktp-lesson-plan-alignment | 2.2.0 | P4 | 0/5 | - | F p 0/5 |  | inf-3 |  | term1_coverage 83 (10 of 12 = 83.3 % in ordinary whole per cent); both worked figures (13/15 = 86.7 -> 85, 8/9 |
| ktp-lesson-plan-alignment | 2.3.0 | P4 | 0/5 | 0/5 | A p 0/5; F p 0/5 |  | inf-4 |  | term1_coverage 92 (half-up). Both worked figures truncate: the regulation's own specimen review writes 13 of 1 |
| lassa-kap-results-sheet | 1.0.0 | P4 | 2/5 | - | F p 2/5 |  | inf-2 |  | sample_size 390 (nearest) instead of 391 (up), on either population total |
| lassa-kap-results-sheet | 1.1.0 | P4 | 8/15 | 6/15 | A f 3/10; p 3/5; F f 5/10; p 3/5 | BLIND-1.0 | inf-2 |  | sample_size 390 (nearest) instead of 391 (up), on either population total |
| lassa-kap-results-sheet | 1.2.0 | P4 | 2/5 | 0/5 | A p 0/5; F p 2/5 |  | inf-2 |  | sample_size 390 (nearest) instead of 391 (up), on either population total |
| lassa-kap-results-sheet | 1.2.0 | P5 | 0/5 | 0/5 | A p 0/5; F p 0/5 |  | inf-6 |  | rf_mean 5.38 (half-up or half-even) instead of 5.37 (cut); pp_mean 5.63 either way |
| manhole-excavation-valuation | 1.0.0 | P3 | 0/5 | - | F p 0/5 |  | inf-2 |  | raw depths: A06 9.84 (truth 9.83), A10 10.17 (truth 10.18), A09 12.72 (truth 12.73) |
| manhole-excavation-valuation | 1.1.0 | P3 | 0/5 | - | F p 0/5 |  | inf-2 |  | raw depths: A06 9.84 (truth 9.83), A10 10.17 (truth 10.18), A09 12.72 (truth 12.73) |
| manhole-excavation-valuation | 1.2.0 | P3 | 0/5 | 0/5 | A p 0/5; F p 0/5 |  | inf-3 |  | nearest-centimetre depths: A06 9.83, A10 10.18 (raw depths: 9.82, 10.17) instead of truncated depths: A06 9.80 |
| manhole-excavation-valuation | 1.2.0 | P5 | 0/5 | 0/5 | A p 0/5; F p 0/5 |  | inf-3 |  | A09 at the nearest-centimetre depth, 12.73 (raw 12.72), instead of the truncated depth, 12.69 |
| melody-lesson-results | 1.0.0 | P1 | 0/5 | 0/5 | A p 0/5; F p 0/5 |  | inf-4 |  | writes each lesson score as pooled points (Mika 9 and 24 -> 82.50) instead of the mean of the two percentages  |
| melody-lesson-results | 1.1.0 | P1 | 0/15 | 0/15 | A f 0/10; p 0/5; F f 0/10; p 0/5 |  | inf-5 |  | writes each lesson score rounded half-up (Lance 7 and 19 -> 66.67; Trisha 9 and 25 -> 86.67) instead of with t |
| melody-lesson-results | 1.2.0 | P1 | 0/5 | 0/5 | A p 0/5; F p 0/5 |  | inf-5 |  | writes each lesson score rounded half-up (Lance 7 and 19 -> 66.67; Trisha 9 and 25 -> 86.67) instead of with t |
| moisturiser-price-screen | 1.0.0 | P2 | 0/5 | 0/5 | A p 0/5; F p 0/5 |  | st-v1 |  | rounds the marked-down price with the default half-to-even rounding (Python round / binary float) or leaves it |
| moisturiser-price-screen | 2.0.0 | P5 | 0/5 | - | F p 0/5 |  | inf-3 |  | rounds BN-2110 (317,050) and BN-2115 (281,450) half-to-even: 317,000 and 281,400, 100 toman low |
| moisturiser-price-screen | 2.1.0 | P5 | 0/5 | - | F p 0/5 |  | inf-3 |  | writes BN-2110 317,600 and BN-2115 282,000 (nearest hundred) instead of 317,500 and 281,900; leaving the compu |
| moisturiser-price-screen | 2.2.0 | P5 | 0/15 | 0/15 | A f 0/10; p 0/5; F f 0/10; p 0/5 | BLIND-1.0 | inf-3 |  | writes BN-2110 317,600 and BN-2115 282,000 (nearest hundred) instead of 317,500 and 281,900; leaving the compu |
| moisturiser-price-screen | 2.3.0 | P7 | 0/5 | 0/5 | A p 0/5; F p 0/5 |  | inf-2 |  | BN-2118 422,700 and BN-2119 306,100 (the whole listing at once) instead of 422,600 and 306,000; the nearest hu |
| niche-shelving-screen | 1.1.0 | P4 | 0/15 | 0/15 | A f 0/10; p 0/5; F f 0/10; p 0/5 |  | inf-4 |  | rounds heights to one decimal instead of cutting them as both filed screenings do, so every pole and cut-to-or |
| niche-shelving-screen | 1.3.0 | P4 | 0/5 | 0/5 | A p 0/5; F p 0/5 |  | inf-4 |  | rounds heights to one decimal instead of cutting them as both filed screenings do, so every pole and cut-to-or |
| okra-manuscript-revision | 1.0.0 | P7 | 0/5 | 0/5 | A p 0/5; F p 0/5 |  | st-v1 |  | rounds M0NPK0's exact B:C of 2.125 (120,768 / 56,832) with binary or half-even rounding to 2.12 instead of 2.1 |
| okra-manuscript-revision | 2.0.0 | P6 | 2/5 | - | F p 2/5 |  | inf-2 |  | reports gross income in whole rupees (e.g. 1,97,335.80 -> 1,97,336) instead of to the nearest Rs 10 as the gro |
| okra-manuscript-revision | 2.0.0 | P8 | 0/5 | - | F p 0/5 |  | inf-2 |  | reports M0NPK0's exact half 2.125 as 2.12 instead of 2.13 (halves up, as the exemplars show) |
| okra-manuscript-revision | 2.1.0 | P6 | 0/5 | - | F p 0/5 |  | inf-3 |  | reports gross income in whole rupees (e.g. 85.93 x 2,220 = 1,90,764.60 -> 1,90,765) instead of to the nearest  |
| okra-manuscript-revision | 2.1.0 | P8 | 0/5 | - | F p 0/5 |  | inf-2 |  | reports M2NPK1's exact half 2.635 as 2.63 instead of 2.64 (halves up, as the exemplars show) |
| okra-manuscript-revision | 2.2.0 | P6 | 3/5 | 0/5 | A p 0/5; F p 3/5 |  | inf-3 |  | reports gross income in whole rupees (e.g. 85.93 x 2,205 = 1,89,475.65 -> 1,89,476) instead of to the nearest  |
| okra-manuscript-revision | 2.2.0 | P8 | 1/5 | 0/5 | A p 0/5; F p 1/5 |  | inf-2 |  | rounds B:C to 2 decimals instead of truncating, so M0NPK1, M1NPK0, M1NPK1 and M2NPK0 read 2.33, 2.75, 3.14 and |
| pathway-choice-audit | 2.1.0 | P6 | 0/5 | 0/5 | A p 0/5; F p 0/5 |  | inf-3 |  | states the STEM share as 77.8 (14 of 18 = 77.78 at the nearest tenth) instead of 77.7; the Arts & Sports Scien |
| posting-month-close | 1.2.0 | P2 | 0/5 | 0/5 | A p 0/5; F p 0/5 |  | inf-4 |  | pays a Reel exactly 487.5 and rounds the month once (half up), instead of paying each Reel the whole-rupee 488 |
| posting-month-close | 1.2.0 | P3 | 0/5 | 0/5 | A p 0/5; F p 0/5 |  | inf-5 |  | rounds the September rupee order (ORD-139, Rs 98,500 at 280.65 = 350.97) to the nearest dollar (351) instead o |
| profile-copy-claims-audit | 1.0.0 | P2 | 0/5 | 0/5 | A p 0/5; F p 0/5 |  | st-v1 |  | computes 1253/2000 with binary floats and rounds with round()/format (half-even on a value binary stores just  |
| profile-copy-claims-audit | 2.1.0 | P5 | 14/15 | 15/15 | A f 10/10; p 5/5; F f 10/10; p 4/5 | GENUINE-soft | inf-2 |  | states the widget rate and both shares at the nearest one decimal (66.7, 42.8, 61.2 on the reference selection |
| profile-copy-claims-audit | 2.2.0 | P5 | 14/15 | 14/15 | A f 9/10; p 5/5; F f 9/10; p 5/5 | GENUINE-soft | inf-2 |  | states the widget rate and both shares at the nearest one decimal (66.7, 42.8, 61.2 on the reference selection |
| profile-copy-claims-audit | 2.3.0 | P5 | 12/15 | 12/15 | A f 9/10; p 3/5; F f 7/10; p 5/5 | GENUINE-soft | inf-2 |  | states the widget rate and both shares at the nearest one decimal (66.7, 42.8, 61.2 on the reference selection |
| profile-copy-claims-audit | 2.4.0 | P5 | 14/15 | 14/15 | A f 10/10; p 4/5; F f 10/10; p 4/5 | GENUINE-soft | inf-2 |  | states the widget rate and both shares at the nearest one decimal (66.7, 42.8, 61.2 on the reference selection |
| profile-copy-claims-audit | 2.5.0 | P5 | 1/5 | 0/5 | A p 0/5; F p 1/5 |  | inf-3 |  | states the widget rate and both shares at the nearest one decimal (66.7, 46.6, 65.7 on the reference selection |
| profile-copy-claims-audit | 2.6.0 | P5 | 4/5 | 0/5 | A p 0/5; F p 4/5 | BLIND-1.0 | inf-4 |  | states the widget rate and both shares at the nearest one decimal (66.7, 46.6, 65.7 on the reference selection |
| profile-copy-claims-audit | 2.7.0 | P5 | 4/5 | 0/5 | A p 0/5; F p 4/5 |  | inf-4 |  | states the widget rate and both shares at the nearest one decimal (66.7, 46.6, 65.7 on the reference selection |
| profile-copy-claims-audit | 2.8.0 | P5 | 1/5 | 0/5 | A p 0/5; F p 1/5 |  | inf-3 |  | states the widget rate and both shares at the nearest one decimal (66.7, 46.6, 65.7 on the reference selection |
| psychopathy-evidence-screen | 2.3.0 | P5 | 0/15 | 0/15 | A f 0/10; p 0/5; F f 0/10; p 0/5 | BLIND-1.0 | inf-3 |  | enters R07 with 179 (178.75 rounded to nearest) instead of 178; both illustrations drop the fraction (154.66 - |
| pupil-tracker-term-summary | 1.2.0 | P5 | 2/5 | 0/5 | A p 0/5; F p 2/5 |  | inf-4 |  | writes every rate as the nearest whole number: on the 12 graded lines (off the slip lines and the leaver, wher |
| refurb-laptop-screen | 1.1.0 | P2 | 0/5 | - | F p 0/5 |  | inf-1 |  | BW-104's fee £8.92, total £183.92 (truth £8.93, £183.93; fail either way) |
| refurb-laptop-screen | 1.2.0 | P2 | 0/5 | - | F p 0/5 |  | inf-3 |  | works the fee to the nearest penny: BW-104 £8.92 -> £183.82 fail (truth £8.91, £183.81 fail), BW-112 £8.57 ->  |
| refurb-laptop-screen | 1.3.0 | P2 | 1/5 | - | F p 1/5 |  | inf-3 |  | works the fee to the nearest penny: BW-104 £8.92 -> £183.82 fail (truth £8.91, £183.81 fail), BW-112 £8.57 ->  |
| refurb-laptop-screen | 1.4.0 | P2 | 0/5 | 0/5 | A p 0/5; F p 0/5 |  | inf-3 |  | works the fee to the nearest penny: BW-104 £8.92 -> £183.82 fail (truth £8.91, £183.81 fail), BW-112 £8.57 ->  |
| sandwich-image-audit | 1.3.0 | P4 | 0/5 | 0/5 | A p 0/5; F p 0/5 |  | inf-3 |  | studio_fee_egp = the total rounded once (round half up of n x 51.3) for the solver's own needs_photo count |
| spice-pitch-deck-qa | 1.0.0 | P5 | 0/5 | 0/5 | A p 0/5; F p 0/5 |  | st-v1 |  | computes 5% of the 1,170 rupee subtotal (58.5) and rounds it with binary round() / default Decimal quantize, w |
| spice-pitch-deck-qa | 2.0.0 | P4 | 0/5 | - | F p 0/5 |  | inf-2 |  | takes 5% of the trimmed subtotal 1,018 and rounds once (51) instead of summing the per-line rounded savings (5 |
| spice-pitch-deck-qa | 2.1.0 | P4 | 0/5 | - | F p 0/5 |  | inf-3 |  | takes 5% of the trimmed subtotal 1,035 and rounds once (52) instead of summing the per-line rounded savings (2 |
| spice-pitch-deck-qa | 2.2.0 | P4 | 3/5 | 0/5 | A p 0/5; F p 3/5 |  | inf-3 |  | takes 5% of the trimmed subtotal 1,035 and rounds once (52) instead of summing the per-line rounded savings (2 |
| spice-pitch-deck-qa | 2.3.0 | P4 | 4/5 | 0/5 | A p 0/5; F p 4/5 |  | inf-3 |  | takes 5% of the trimmed subtotal 1,035 and rounds once (52) instead of summing the per-line rounded savings (2 |
| station-register-consolidation | 1.0.0 | P4 | 0/5 | 0/5 | A p 0/5; F p 0/5 |  | st-v1 |  | converts D-M-S with binary floats and Python round(): 52-43-39 = 52.7275 exactly, whose binary value lies belo |
| station-register-consolidation | 2.1.0 | P4 | 0/5 | - | F p 0/5 |  | inf-5 |  | rounds the converted positions half up to three decimals: six longitudes (47-011, 47-013, 47-942, 47-003, 47-0 |
| station-register-consolidation | 2.2.0 | P4 | 0/5 | - | F p 0/5 |  | inf-7 |  | rounds the converted positions half up to three decimals: six longitudes (47-011, 47-013, 47-942, 47-003, 47-0 |
| station-register-consolidation | 2.3.0 | P4 | 1/5 | 0/5 | A p 0/5; F p 1/5 |  | inf-6 |  | rounds the converted positions half up to three decimals: six longitudes (47-011, 47-013, 47-942, 47-003, 47-0 |
| student-laptop-shortlist | 1.0.0 | P5 | 0/5 | 0/5 | A p 0/5; F p 0/5 |  | st-v1 |  | rounds the 7.5%-discounted price half-to-even (Python round, or 0.925 * price in binary float then round) or t |
| student-laptop-shortlist | 2.0.0 | P4 | 0/5 | - | F p 0/5 |  | inf-2 |  | rounds the discounted total half up: L-405 78,597 instead of 78,598 and L-406 67,497 instead of 67,498 (7.5% o |
| student-laptop-shortlist | 2.1.0 | P4 | 0/5 | - | F p 0/5 |  | inf-4 |  | rounds the payable to the nearest rupee (or floors the discount): L-405 78,616 instead of 78,615 and L-406 67, |
| student-laptop-shortlist | 2.2.0 | P4 | 1/5 | 0/5 | A p 0/5; F p 1/5 |  | inf-3 |  | rounds the payable to the nearest rupee (flooring it gives the same): L-405 78,153 instead of 78,154 and L-406 |
| student-laptop-shortlist | 2.3.0 | P4 | 0/5 | 0/5 | A p 0/5; F p 0/5 |  | inf-3 |  | rounds the payable to the nearest rupee (flooring it gives the same): L-405 78,153 instead of 78,154 and L-406 |
| suitcase-cover-matrix-check | 1.0.0 | P5 | 0/5 | 0/5 | A p 0/5; F p 0/5 |  | st-v1 |  | 34 of 272 is exactly 12.5%; Python round(), f'{x:.0f}' and Decimal's default context round the tie to even and |
| suitcase-cover-matrix-check | 2.0.0 | P2 | 4/5 | 0/5 | A p 0/5; F p 4/5 | BLIND-1.0 | inf-2 |  | writes the share rounded to the nearest whole percent: 34 of 264 = 12.88 % gives 13 (34 of 270 = 12.59 % also  |
| suitcase-cover-matrix-check | 2.1.0 | P2 | 6/15 | 0/15 | A f 0/10; p 0/5; F f 5/10; p 1/5 | GENUINE | inf-2 |  | writes the share rounded to the nearest whole percent: 34 of 264 = 12.88 % gives 13 (34 of 270 = 12.59 % also  |
| suitcase-cover-matrix-check | 2.1.1 | P2 | 5/15 | 0/15 | A f 0/10; p 0/5; F f 3/10; p 2/5 | GENUINE | inf-2 |  | writes the share rounded to the nearest whole percent: 34 of 264 = 12.88 % gives 13 (34 of 270 = 12.59 % also  |
| suitcase-cover-matrix-check | 2.2.0 | P2 | 2/5 | - | F p 2/5 |  | inf-2 |  | writes the share rounded to the nearest whole percent: 34 of 264 = 12.88 % gives 13 (34 of 270 = 12.59 % also  |
| suitcase-cover-matrix-check | 2.3.0 | P2 | 1/5 | - | F p 1/5 |  | inf-2 |  | writes the share rounded to the nearest whole percent: 34 of 264 = 12.88 % gives 13 (34 of 270 = 12.59 % also  |
| suitcase-cover-matrix-check | 2.4.0 | P2 | 3/5 | - | F p 3/5 |  | inf-2 |  | writes the share rounded to the nearest whole percent: 34 of 264 = 12.88 % gives 13 (34 of 270 = 12.59 % also  |
| suitcase-cover-matrix-check | 2.5.0 | P2 | 3/5 | - | F p 3/5 |  | inf-2 |  | writes the share rounded to the nearest whole percent: 34 of 264 = 12.88 % gives 13 (34 of 270 = 12.59 % also  |
| timesheet-overtime-review | 1.0.0 | P1 | 0/5 | 0/5 | A p 0/5; F p 0/5 |  | st-v1 |  | rounds the raw overtime (an exact half quarter: 9450 s = 10.5 quarter hours) with the language default round-h |
| timesheet-overtime-review | 2.0.0 | P3 | 0/5 | - | F p 0/5 |  | inf-4 |  | claims the nearest quarter hour of its own raw overtime (02:00 for 7185 s) instead of the completed quarter ho |
| timesheet-overtime-review | 2.1.0 | P3 | 0/5 | - | F p 0/5 |  | inf-2 |  | claims the nearest quarter hour of its own raw overtime (02:15 for 8040 s, or for 7704 s after a P1 miss) inst |
| timesheet-overtime-review | 2.2.0 | P3 | 0/15 | 0/15 | A f 0/10; p 0/5; F f 0/10; p 0/5 |  | inf-3 |  | claims the nearest (or the completed) quarter hour of its own raw overtime: 02:00 for 7440 s, instead of every |
| timesheet-overtime-review | 2.3.0 | P3 | 0/5 | 0/5 | A p 0/5; F p 0/5 |  | inf-3 |  | claims the nearest (or the completed) quarter hour of its own raw overtime: 02:00 for 7440 s, instead of every |
| timesheet-overtime-review | 2.4.0 | P3 | 0/15 | - | F f 0/10; p 0/5 |  | inf-3 |  | claims the nearest (or the completed) quarter hour of its own raw overtime: 02:00 for 7440 s, instead of every |
| timesheet-overtime-review | 2.5.0 | P3 | 0/5 | - | F p 0/5 |  | inf-3 |  | claims the nearest (or the completed) quarter hour of its own raw overtime: 02:00 for 7440 s, instead of every |
| timesheet-overtime-review | 2.6.0 | P3 | 0/5 | - | F p 0/5 |  | inf-3 |  | claims the nearest (or the completed) quarter hour of its own raw overtime: 02:00 for 7440 s, instead of every |

### CV.method: Other method convention from worked or filed examples

| task | ver | P | F | A | stages | verdict | S/I | re | misreading |
|---|---|---|---|---|---|---|---|---|---|
| ats-embedded-screening-register | 1.0.0 | P1 | 0/5 | - | F p 0/5 |  | inf-4 |  | counts each role as end minus start, so every applicant is short one month per role (C-301 46 not 48, C-303 61 |
| ats-embedded-screening-register | 1.1.0 | P1 | 0/15 | 0/15 | A f 0/10; p 0/5; F f 0/10; p 0/5 |  | inf-4 |  | counts a current role through October 2026: one month too many for every applicant (C-301 48 not 47, C-302 40  |
| ats-embedded-screening-register | 1.2.0 | P1 | 0/5 | - | F p 0/5 |  | inf-4 |  | counts a current role through October 2026: one month too many for every graded applicant (C-302 40 not 39, C- |
| ats-embedded-screening-register | 1.3.0 | P1 | 0/5 | - | F p 0/5 |  | inf-4 |  | counts a current role through October 2026: one month too many for every graded applicant (C-302 40 not 39, C- |
| ats-embedded-screening-register | 1.4.0 | P1 | 0/5 | - | F p 0/5 |  | inf-4 |  | counts a current role through October 2026: one month too many for every graded applicant (C-302 40 not 39, C- |
| blockprint-winter-close | 1.0.0 | P4 | 0/5 | - | F p 0/5 |  | inf-5 |  | R-1214 148.00 (truth 74.00) and R-0308 89.00 (truth 44.50); hotel total 485.00 instead of 366.50 |
| brightwater-spec-qa | 1.2.0 | P3 | 0/5 | - | F p 0/5 |  | inf-4 |  | gives one business day for C-009, C-031, C-035 and C-036; the house count (arrival day counted: same day = one |
| brightwater-spec-qa | 1.3.0 | P3 | 15/15 | 15/15 | A f 10/10; p 5/5; F f 10/10; p 5/5 | AMBIGUOUS | inf-4 |  | gives one business day for C-009, C-031, C-035 and C-036; the client's own count (arrival day counted: second  |
| cafe-kitchen-schedule-revisions | 2.0.0 | P9 | 0/5 | - | F p 0/5 |  | inf-2 |  | draws elevation C in plan order (MP-1 left, CO-1 right); the issued S-01, looking south, has the west-wall bas |
| cafe-kitchen-schedule-revisions | 2.1.0 | P2 | 0/15 | 0/15 | A f 0/10; p 0/5; F f 0/10; p 0/5 |  | inf-2 |  | treats a near edge exactly on the zone's end as outside: C3 opens. The standard's 4.2 figure (60 + 4 + 5 = 69, |
| cafe-kitchen-schedule-revisions | 2.1.0 | P7 | 0/15 | 0/15 | A f 0/10; p 0/5; F f 0/10; p 0/5 |  | inf-2 | re | as P2 in rev 1: C3 opens; it is a corner conflict |
| cafe-kitchen-schedule-revisions | 2.1.1 | P2 | 0/15 | 0/15 | A f 0/10; p 0/5; F f 0/10; p 0/5 |  | inf-2 |  | treats a near edge exactly on the zone's end as outside: C3 opens. The standard's 4.2 figure (60 + 4 + 5 = 69, |
| cafe-kitchen-schedule-revisions | 2.1.1 | P7 | 0/15 | 0/15 | A f 0/10; p 0/5; F f 0/10; p 0/5 |  | inf-2 | re | as P2 in rev 1: C3 opens; it is a corner conflict |
| cafe-kitchen-schedule-revisions | 2.2.0 | P2 | 0/5 | - | F p 0/5 |  | inf-2 |  | treats a near edge exactly on the zone's end as outside: C3 opens. The standard's 4.2 figure (60 + 4 + 5 = 69, |
| cafe-kitchen-schedule-revisions | 2.2.0 | P7 | 0/5 | - | F p 0/5 |  | inf-2 | re | as P2 in rev 1: C3 opens; it is a corner conflict |
| cafe-kitchen-schedule-revisions | 2.3.0 | P2 | 0/15 | - | F f 0/10; p 0/5 |  | inf-2 |  | treats a near edge exactly on the zone's end as outside: C3 opens. The standard's 4.2 figure (60 + 4 + 5 = 69, |
| cafe-kitchen-schedule-revisions | 2.3.0 | P7 | 0/15 | - | F f 0/10; p 0/5 |  | inf-2 | re | as P2 in rev 1: C3 opens; it is a corner conflict |
| coloring-book-retitle-audit | 1.0.0 | P10 | 0/5 | 0/5 | A p 0/5; F p 0/5 |  | st-v1 |  | treats a live class-16 mark that appears inside the term (S-5001 COZY WITCHY LIFE inside T4 COMFY & COZY WITCH |
| coloring-book-retitle-audit | 1.0.0 | P5 | 0/5 | 0/5 | A p 0/5; F p 0/5 |  | st-v1 |  | matches title words as substrings, so box 1 ('little witch gift idea': witch inside Witchy) and box 3 ('woodla |
| coloring-book-retitle-audit | 1.0.0 | P8 | 0/5 | 0/5 | A p 0/5; F p 0/5 |  | st-v1 |  | compares the term and the mark as written, so T1 'COMFY & COZY' does not match S-1001 'COMFY AND COZY' (live,  |
| coloring-book-retitle-audit | 2.0.0 | P6 | 0/5 | - | F p 0/5 |  | inf-2 |  | keeps box 5: the listing carries the client's series (v1.1 print details), which the client profile names Hear |
| coloring-book-retitle-audit | 2.1.0 | P4 | 0/5 | - | F p 0/5 |  | inf-2 |  | keeps box 5: the sample listing sends back 'bird feeder' (Birds) and 'visitor log' (Visitors) but lets 'friend |
| coloring-book-retitle-audit | 2.1.0 | P6 | 0/5 | - | F p 0/5 |  | inf-2 |  | types 'Comfy &amp; Cozy' into the Title field (secondary premise; measured dead as a mechanism) |
| coloring-book-retitle-audit | 2.1.0 | P7 | 0/5 | - | F p 0/5 |  | inf-4 |  | reads '&' as AND; the rights desk's filed clearances recorded SALT AND PEPPER and BREAD & BUTTER (live, coveri |
| coloring-book-retitle-audit | 2.2.0 | P4 | 0/15 | 0/15 | A f 0/10; p 0/5; F f 0/10; p 0/5 |  | inf-2 |  | keeps boxes 1, 5 and 7 (identical words only) or 1 and 7 (plural/singular only); the support desk's listing se |
| coloring-book-retitle-audit | 2.2.0 | P7 | 0/15 | 0/15 | A f 0/10; p 0/5; F f 0/10; p 0/5 |  | inf-3 |  | treats '&' as a sign to set aside (or a different word); the rights desk's signed clearances under the current |
| coloring-book-retitle-audit | 2.2.0 | P9 | 0/15 | 0/15 | A f 0/10; p 0/5; F f 0/10; p 0/5 |  | inf-2 | re | re-decision of the keyword-form convention in a fresh session (the second title has the same words): only boxe |
| coloring-book-retitle-audit | 2.3.0 | P4 | 0/15 | 0/15 | A f 0/10; p 0/5; F f 0/10; p 0/5 |  | inf-2 |  | keeps boxes 1, 5 and 7 (identical words only) or 1 and 7 (plural/singular only); the support desk's listing se |
| coloring-book-retitle-audit | 2.3.0 | P7 | 0/15 | 0/15 | A f 0/10; p 0/5; F f 0/10; p 0/5 |  | inf-3 |  | treats '&' as a sign to set aside (or a different word); the rights desk's signed clearances under the current |
| coloring-book-retitle-audit | 2.3.0 | P9 | 0/15 | 0/15 | A f 0/10; p 0/5; F f 0/10; p 0/5 |  | inf-2 | re | re-decision of the keyword-form convention in a fresh session (the second title has the same words): only boxe |
| coloring-book-retitle-audit | 2.4.0 | P4 | 0/5 | - | F p 0/5 |  | inf-2 |  | keeps boxes 1, 5 and 7 (identical words only) or 1 and 7 (plural/singular only); the support desk's listing se |
| coloring-book-retitle-audit | 2.4.0 | P7 | 0/5 | - | F p 0/5 |  | inf-3 |  | treats '&' as a sign to set aside (or a different word); the rights desk's signed clearances under the current |
| coloring-book-retitle-audit | 2.4.0 | P9 | 0/5 | - | F p 0/5 |  | inf-2 | re | re-decision of the keyword-form convention in a fresh session (the second title has the same words): only boxe |
| coloring-book-retitle-audit | 2.5.0 | P4 | 0/15 | - | F f 0/10; p 0/5 |  | inf-2 |  | keeps boxes 1, 5 and 7 (identical words only) or 1 and 7 (plural/singular only); the support desk's listing se |
| coloring-book-retitle-audit | 2.5.0 | P7 | 0/15 | - | F f 0/10; p 0/5 |  | inf-3 |  | treats '&' as a sign to set aside (or a different word); the rights desk's signed clearances under the current |
| coloring-book-retitle-audit | 2.5.0 | P9 | 0/15 | - | F f 0/10; p 0/5 |  | inf-2 | re | re-decision of the keyword-form convention in a fresh session (the second title has the same words): only boxe |
| coloring-book-retitle-audit | 2.6.0 | P4 | 0/5 | - | F p 0/5 |  | inf-2 |  | keeps boxes 1, 5 and 7 (identical words only) or 1 and 7 (plural/singular only); the support desk's listing se |
| coloring-book-retitle-audit | 2.6.0 | P7 | 0/5 | - | F p 0/5 |  | inf-3 |  | treats '&' as a sign to set aside (or a different word); the rights desk's signed clearances under the current |
| coloring-book-retitle-audit | 2.6.0 | P9 | 0/5 | - | F p 0/5 |  | inf-2 | re | re-decision of the keyword-form convention in a fresh session (the second title has the same words): only boxe |
| coop-bp-prefill-sheet | 1.0.0 | P3 | 0/5 | - | F p 0/5 |  | inf-3 |  | takes September 2025 - August 2026 for all six: drops PJ-004, PJ-022, PJ-061, PJ-082, PJ-102 and adds PJ-007,  |
| coop-bp-prefill-sheet | 1.1.0 | P3 | 0/5 | 1/5 | A p 1/5; F p 0/5 |  | inf-4 |  | takes each cooperative's own financial year: adds PJ-004, PJ-022, PJ-061, PJ-082, PJ-102 and drops PJ-007, PJ- |
| council-video-index | 1.0.0 | P5 | 2/5 | - | F p 2/5 |  | inf-3 |  | counts each chapter exactly at the opening moment; the published indexes start every chapter 15 seconds before |
| council-video-index | 1.1.0 | P4 | 0/5 | - | F p 0/5 |  | inf-6 |  | counts positions on the clock from the first frame; the published XXX index counts playing time (items 4 and 5 |
| council-video-index | 1.1.0 | P5 | 5/5 | - | F p 5/5 | AMBIGUOUS | inf-3 |  | counts each chapter exactly at the opening moment; the published indexes start every chapter 15 seconds before |
| council-video-index | 1.2.0 | P4 | 0/15 | 0/15 | A f 0/10; p 0/5; F f 0/10; p 0/5 |  | inf-6 |  | counts positions on the clock from the first frame; the published XXX index counts playing time (items 4 and 5 |
| council-video-index | 1.2.0 | P5 | 14/15 | 8/15 | A f 5/10; p 3/5; F f 9/10; p 5/5 | AMBIGUOUS | inf-3 |  | counts each chapter exactly at the opening moment; the published indexes start every chapter 15 seconds before |
| council-video-index | 1.3.0 | P2 | 0/5 | 0/5 | A p 0/5; F p 0/5 |  | inf-4 |  | works each support figure out of the councillors present (14); the office's worked figures on session XXIX (12 |
| council-video-index | 1.3.0 | P4 | 0/5 | 0/5 | A p 0/5; F p 0/5 |  | inf-6 |  | counts positions on the clock from the first frame; the published XXX index counts playing time (items 4 and 5 |
| council-video-index | 1.3.0 | P5 | 5/5 | 3/5 | A p 3/5; F p 5/5 |  | inf-3 |  | counts each chapter exactly at the opening moment; the published indexes start every chapter 15 seconds before |
| current-affairs-booklet-plan | 1.2.0 | P4 | 0/5 | 0/5 | A p 0/5; F p 0/5 |  | inf-4 |  | files the cattle fair (27 February to 5 March, on the March page) under March instead of February, the month i |
| earth-guide-answer-claims | 1.0.0 | P3 | 0/5 | - | F p 0/5 |  | inf-3 |  | counts each image file, so LA-02 (2.1 a, 2.1 b, 2.2), LA-04 (4.1 a-c), LA-07 (7.1, 7.2 a, 7.2 b) and LA-10 (10 |
| earth-guide-answer-claims | 1.1.0 | P3 | 0/5 | 0/5 | A p 0/5; F p 0/5 |  | inf-3 |  | counts each panel: LA-02 3, LA-04 3, LA-07 3, LA-10 2 (and the basins answer 3 once the plate is moved) instea |
| feast-sharing-runsheet | 1.0.0 | P4 | 0/5 | - | F p 0/5 |  | inf-2 |  | times the speakers-times-time sharing segment as the bare product (12 and 9 minutes), so the class Br. Yosef t |
| feast-sharing-runsheet | 1.1.0 | P4 | 4/5 | - | F p 4/5 | AMBIGUOUS | inf-2 |  | times the speakers-times-time sharing segment as the bare product (12 and 9 minutes), so the class Br. Yosef t |
| hammamet-voucher-reissue | 1.0.0 | P5 | 0/5 | 0/5 | A p 0/5; F p 0/5 |  | st-v1 |  | writes the departure-day lunch note under 'Remarques' (the free-text zone), as the session's assistant first d |
| hammamet-voucher-reissue | 2.2.0 | P6 | 0/5 | 0/5 | A p 0/5; F p 0/5 |  | inf-2 |  | park_entries 4 (one per guest) instead of 2 (one per room): 16 DT at 8 DT a ticket is 2 tickets for two couple |
| home-bp-diary-summary | 2.0.0 | P2 | 0/5 | - | F p 0/5 |  | inf-3 |  | averages the individual readings (baseline 136.6/82.8 instead of 136.9/83.2; R-7 134.9/81.6, AT_TARGET, instea |
| home-bp-diary-summary | 2.1.0 | P2 | 0/5 | - | F p 0/5 |  | inf-4 |  | averages the individual readings (baseline 136.3/82.8 instead of 136.4/83.2; R-7 134.9/81.6, AT_TARGET, instea |
| home-bp-diary-summary | 2.2.0 | P2 | 0/15 | 0/15 | A f 0/10; p 0/5; F f 0/10; p 0/5 |  | inf-4 |  | averages the individual readings (baseline 136.3/82.8 instead of 136.4/83.2; R-7 134.9/81.6, AT_TARGET, instea |
| home-bp-diary-summary | 2.2.1 | P2 | 0/15 | 0/15 | A f 0/10; p 0/5; F f 0/10; p 0/5 |  | inf-4 |  | averages the individual readings (baseline 136.3/82.8 instead of 136.4/83.2; R-7 134.9/81.6, AT_TARGET, instea |
| home-bp-diary-summary | 2.3.0 | P2 | 0/5 | 0/5 | A p 0/5; F p 0/5 |  | inf-4 |  | averages the individual readings (baseline 136.4/82.9 instead of 136.4/83.3; R-7 135.0/81.7 instead of 135.3/8 |
| home-bp-diary-summary | 2.4.0 | P2 | 0/5 | - | F p 0/5 |  | inf-4 |  | averages the individual readings (baseline 136.4/83.0 instead of 136.4/83.4 on the reference list; R-7 134.9/8 |
| home-bp-diary-summary | 2.5.0 | P2 | 0/5 | - | F p 0/5 |  | inf-4 |  | averages the individual readings (baseline 136.4/83.0 instead of 136.4/83.4 on the reference list; R-7 134.9/8 |
| home-bp-diary-summary | 2.6.0 | P2 | 0/5 | - | F p 0/5 |  | inf-4 |  | averages the individual readings (baseline 136.4/83.0 instead of 136.4/83.4 on the reference list; R-7 134.9/8 |
| home-bp-diary-summary | 2.7.0 | P2 | 0/5 | - | F p 0/5 |  | inf-4 |  | averages the individual readings (baseline 136.4/83.0 instead of 136.4/83.4 on the reference list; R-7 134.9/8 |
| insurance-secrecy-register | 1.0.0 | P2 | 0/5 | - | F p 0/5 |  | inf-2 |  | dates C11 by its first episode (2025-03-14) and puts it on the 2019 edition (top fine 500,000) instead of its  |
| insurance-secrecy-register | 1.1.0 | P3 | 0/5 | - | F p 0/5 |  | inf-4 |  | dates C11 by its first episode (2025-03-14) and puts it on the 2019 edition (top fine 500,000) instead of its  |
| killzone-journal-review | 1.0.0 | P3 | 0/5 | - | F p 0/5 |  | inf-4 |  | price-ratio R: 61804388 2.1 (not 2.0), 61807911 1.3 (1.2), 61811540 3.1 (3.0), 61814016 1.0 (0.9), 61816844 1. |
| ktp-lesson-plan-alignment | 2.3.0 | P5 | 0/5 | 0/5 | A p 0/5; F p 0/5 |  | inf-4 |  | term1_review_rate 12 (met over all plans). The two filed reviews of this term fix the base: 6-A has 3 met, 2 n |
| lassa-kap-results-sheet | 1.0.0 | P2 | 0/5 | - | F p 0/5 |  | inf-2 |  | h01 chi-square 4.037 and REJECT (Pearson) instead of 3.536 and DO_NOT_REJECT; h02 likewise uncorrected |
| lassa-kap-results-sheet | 1.1.0 | P2 | 0/15 | 0/15 | A f 0/10; p 0/5; F f 0/10; p 0/5 | BLIND-1.0 | inf-4 |  | h01 chi-square 4.037 and REJECT (Pearson) instead of 3.536 and DO_NOT_REJECT; h02 likewise uncorrected |
| line-colour-census | 1.0.0 | P1 | 14/15 | 1/15 | A f 0/10; p 1/5; F f 9/10; p 5/5 | BLIND-1.0 | inf-2 |  | tests the method's 15 % saturation on HSL S: Elmhurst 6 (#DCE3E9) goes to Blue and the graphite lines (#363C42 |
| line-colour-census | 1.0.0 | P4 | 0/15 | 0/15 | A f 0/10; p 0/5; F f 0/10; p 0/5 |  | inf-3 |  | computes the shares on all 32 lines; the 2025 figures (Pink 2 of 44 lines with 5 Neutral shown as 5.1 %, Teal  |
| line-colour-census | 1.2.0 | P1 | 5/5 | 0/5 | A p 0/5; F p 5/5 |  | inf-2 |  | tests the method's 15 % saturation on HSL S: Elmhurst 6 (#DCE3E9) goes to Blue and the graphite lines (#363C42 |
| line-colour-census | 1.2.0 | P4 | 0/5 | 0/5 | A p 0/5; F p 0/5 |  | inf-3 |  | computes the shares on all 32 lines; the 2025 figures (Pink 2 of 44 lines with 5 Neutral shown as 5.1 %, Teal  |
| line-reference-belegliste | 1.0.0 | P1 | 0/5 | - | F p 0/5 |  | inf-3 |  | marks C02 ('Tür' for the first edition's 'Thür') and C03 ('Teil' for 'Theil') as not word-for-word |
| line-reference-belegliste | 1.1.0 | P1 | 0/5 | - | F p 0/5 |  | inf-3 |  | gives every extract-A citation one line too many: C01 Z. 10, C02 Z. 8, C03 Z. 12, C04 Z. 6 instead of 9, 7, 11 |
| line-reference-belegliste | 1.1.0 | P4 | 0/5 | - | F p 0/5 |  | inf-3 |  | marks C02 ('Tür' for the first edition's 'Thür') and C03 ('Teil' for 'Theil') as not word-for-word |
| line-reference-belegliste | 1.2.0 | P1 | 0/5 | 0/5 | A p 0/5; F p 0/5 |  | inf-2 |  | gives every extract-A citation one line too many: C01 Z. 10, C02 Z. 8, C03 Z. 12, C04 Z. 6, C11 Z. 5 instead o |
| line-reference-belegliste | 1.2.0 | P4 | 0/5 | 0/5 | A p 0/5; F p 0/5 |  | inf-2 |  | marks C02 ('Tür' for the first edition's 'Thür') and C03 ('Teil' for 'Theil') as not word-for-word |
| moot-issue3-memorial-audit | 1.0.0 | P3 | 0/5 | 0/5 | A p 0/5; F p 0/5 |  | st-v1 |  | applies Annex C's 'cross-references to the Moot Proposition are not counted' to every footnote that mentions t |
| moot-issue3-memorial-audit | 1.0.0 | P9 | 0/5 | 0/5 | A p 0/5; F p 0/5 |  | st-v1 |  | takes counsel's 'two broad arguments for issue two' literally and reports Issue 2 |
| moot-issue3-memorial-audit | 2.0.0 | P1 | 0/5 | - | F p 0/5 |  | inf-4 |  | counts the seven Id. footnotes that run back to a proposition-only footnote (9, 10, 17-20, 34) as citing somet |
| moot-issue3-memorial-audit | 2.1.0 | P1 | 0/5 | 0/5 | A p 0/5; F p 0/5 |  | inf-4 |  | counts the seven Id. footnotes that run back to a proposition-only footnote (9, 10, 17-20, 34) as citing somet |
| moot-issue3-memorial-audit | 2.1.0 | P10 | 5/5 | 0/5 | A p 0/5; F p 5/5 | AMBIGUOUS | inf-5 |  | counts each of draft v1's ten heading numbers as a word, so every heading's paragraph_words entry and words_co |
| moot-issue3-memorial-audit | 2.1.0 | P11 | 0/5 | 1/5 | A p 1/5; F p 0/5 | BLIND-1.0 | inf-4 |  | counts draft v1's two footnotes that cite only an Organising Committee Clarification |
| moot-issue3-memorial-audit | 2.1.0 | P12 | 3/5 | 0/5 | A p 0/5; F p 3/5 | AMBIGUOUS | inf-5 | re | counts each of draft v2's ten heading numbers as a word, so every heading's paragraph_words entry and words_co |
| moot-issue3-memorial-audit | 2.1.0 | P13 | 0/5 | 3/5 | A p 3/5; F p 0/5 | BLIND-1.0 | inf-4 | re | counts draft v2's two footnotes that cite only an Organising Committee Clarification |
| moot-issue3-memorial-audit | 2.1.0 | P14 | 0/5 | 0/5 | A p 0/5; F p 0/5 | AMBIGUOUS | inf-5 | re | counts each of draft v3's ten heading numbers as a word, so every heading's paragraph_words entry and words_co |
| moot-issue3-memorial-audit | 2.1.0 | P15 | 0/5 | 5/5 | A p 5/5; F p 0/5 | BLIND-1.0 | inf-4 | re | counts draft v3's two footnotes that cite only an Organising Committee Clarification |
| moot-issue3-memorial-audit | 2.2.0 | P1 | 0/5 | 0/5 | A p 0/5; F p 0/5 |  | inf-4 |  | counts the seven Id. footnotes that run back to a proposition-only footnote (9, 10, 17-20, 34) as citing somet |
| moot-issue3-memorial-audit | 2.2.0 | P10 | 0/5 | 0/5 | A p 0/5; F p 0/5 |  | inf-5 |  | counts each of draft v1's ten heading numbers as a word, so every heading's paragraph_words entry and words_co |
| moot-issue3-memorial-audit | 2.2.0 | P11 | 0/5 | 1/5 | A p 1/5; F p 0/5 |  | inf-4 |  | counts draft v1's two footnotes that cite only an Organising Committee Clarification |
| moot-issue3-memorial-audit | 2.2.0 | P12 | 0/5 | 0/5 | A p 0/5; F p 0/5 |  | inf-5 | re | counts each of draft v2's ten heading numbers as a word, so every heading's paragraph_words entry and words_co |
| moot-issue3-memorial-audit | 2.2.0 | P13 | 0/5 | 0/5 | A p 0/5; F p 0/5 |  | inf-4 | re | counts draft v2's two footnotes that cite only an Organising Committee Clarification |
| moot-issue3-memorial-audit | 2.2.0 | P14 | 1/5 | 0/5 | A p 0/5; F p 1/5 |  | inf-5 | re | counts each of draft v3's ten heading numbers as a word, so every heading's paragraph_words entry and words_co |
| moot-issue3-memorial-audit | 2.2.0 | P15 | 0/5 | 2/5 | A p 2/5; F p 0/5 |  | inf-4 | re | counts draft v3's two footnotes that cite only an Organising Committee Clarification |
| moot-issue3-memorial-audit | 2.2.0 | P16 | 0/5 | 0/5 | A p 0/5; F p 0/5 |  | inf-3 |  | counts draft v1's fn 40 ('List of Dates, entry 9.', cited for the dossier timings of the 12 February meeting ( |
| moot-issue3-memorial-audit | 2.2.0 | P17 | 0/5 | 0/5 | A p 0/5; F p 0/5 |  | inf-3 | re | counts draft v2's fn 16 ('List of Dates, entry 9.', cited for the pass-over-the-panel fact closing 3.1.2's app |
| moot-issue3-memorial-audit | 2.2.0 | P18 | 0/5 | 0/5 | A p 0/5; F p 0/5 |  | inf-3 | re | counts draft v3's fn 20 ('List of Dates, entry 9.', cited for the pass-over-the-panel fact in 3.1.2's applicat |
| mustangs-tryout-roster | 1.0.0 | P1 | 0/5 | 0/5 | A p 0/5; F p 0/5 |  | st-v1 |  | parses the certificate log's dates month-first, the registration form's convention (or reads 'between' as excl |
| mustangs-tryout-roster | 1.0.0 | P9 | 0/5 | 0/5 | A p 0/5; F p 0/5 |  | st-v1 |  | counts any arrival after the start (or exactly 10 minutes) as late: MU-118 (Fridays: gets to the field at 5:40 |
| mustangs-tryout-roster | 2.0.0 | P5 | 0/5 | - | F p 0/5 |  | inf-2 |  | keeps MU-101 (Fridays: gets to the field at 6:20 pm, 40 of 90 minutes) expected on both Fridays and sends no n |
| mustangs-tryout-roster | 2.0.0 | P8 | 0/5 | - | F p 0/5 |  | inf-2 |  | lists MU-118 (Fridays: gets to the field at 5:40 pm, exactly 10 minutes after 5:30 pm) as late |
| mustangs-tryout-roster | 2.1.0 | P5 | 0/5 | 0/5 | A p 0/5; F p 0/5 |  | inf-4 |  | keeps MU-101 (Fridays: gets to the field at 6:20 pm, 40 of 90 minutes) expected on both Fridays and sends no n |
| mustangs-tryout-roster | 2.1.0 | P8 | 0/5 | 0/5 | A p 0/5; F p 0/5 |  | inf-4 |  | lists MU-118 (Fridays: gets to the field at 5:40 pm, exactly 10 minutes after 5:30 pm) as late |
| mustangs-tryout-roster | 2.2.0 | P12 | 0/5 | 0/5 | A p 0/5; F p 0/5 |  | inf-4 |  | lists MU-101 ('Fridays: his mom works until 6:05 pm') as expected (late) at all three Friday sessions; with th |
| mustangs-tryout-roster | 2.2.0 | P13 | 0/5 | 0/5 | A p 0/5; F p 0/5 |  | inf-4 | re | P12 re-decided in a fresh session: MU-101 kept on both Friday sessions (expected - late) and sent no notice |
| mustangs-tryout-roster | 2.2.0 | P14 | 0/5 | 0/5 | A p 0/5; F p 0/5 |  | inf-5 | re | P12 re-decided: MU-101 listed as a late arrival and not noticed; MU-121 ('brother's practice until 5:30 pm', a |
| mustangs-tryout-roster | 2.2.0 | P8 | 0/5 | 0/5 | A p 0/5; F p 0/5 |  | inf-4 |  | lists MU-118 (Fridays: gets to the field at 5:40 pm, exactly 10 minutes after 5:30 pm) as late |
| okra-manuscript-revision | 1.0.0 | P3 | 0/5 | 0/5 | A p 0/5; F p 0/5 |  | st-v1 |  | follows Rohit's checklist ('replace the old yield numbers') and leaves out GY-33-3, whose 87.1% out-yield perc |
| okra-manuscript-revision | 2.0.0 | P7 | 0/5 | - | F p 0/5 |  | inf-2 |  | computes B:C as gross income / cost of cultivation (one higher in every row) |
| okra-manuscript-revision | 2.1.0 | P7 | 0/5 | - | F p 0/5 |  | inf-3 |  | computes B:C as gross income / cost of cultivation (one higher in every row) |
| okra-manuscript-revision | 2.2.0 | P7 | 0/5 | 0/5 | A p 0/5; F p 0/5 |  | inf-2 |  | computes B:C as gross income / cost of cultivation (one higher in every row) |
| posting-month-close | 1.0.0 | P2 | 0/5 | - | F p 0/5 |  | inf-3 |  | pays every post Rs 400 (20,400 on the correct list) instead of 400 for a day's first two posts and 250 for eac |
| posting-month-close | 1.1.0 | P2 | 0/5 | - | F p 0/5 |  | inf-3 |  | pays every post Rs 400 (20,400 on the correct list) instead of 400 for a day's first two posts and 250 for eac |
| probation-answer-key | 2.1.0 | P2 | 0/5 | - | F p 0/5 |  | inf-3 |  | case 9 'законно' (probation 12.01 + two months read as ending on 12.03, so the dismissal of 12.03 falls on its |
| probation-answer-key | 2.2.0 | P2 | 0/15 | 0/15 | A f 0/10; p 0/5; F f 0/10; p 0/5 |  | inf-3 |  | case 9 'законно' (probation 12.01 + two months read as ending on 12.03, so the dismissal of 12.03 falls on its |
| probation-answer-key | 2.3.0 | P5 | 0/5 | 0/5 | A p 0/5; F p 0/5 |  | inf-2 |  | case 9 'незаконно' (probation 12.01 + two months read as ending on 11.03, so the dismissal of 12.03 came after |
| probation-answer-key | 2.4.0 | P5 | 0/5 | 0/5 | A p 0/5; F p 0/5 |  | inf-2 |  | case 9 'незаконно' (probation 12.01 + two months read as ending on 11.03, so the dismissal of 12.03 came after |
| profile-copy-claims-audit | 2.0.0 | P3 | 0/5 | - | F p 0/5 |  | inf-3 |  | counts every line break once: ABOUT 2,594 (fits) instead of 2,608 (over by 8), EXP_STUDIO 1,176 instead of 1,1 |
| profile-copy-claims-audit | 2.1.0 | P3 | 0/15 | 0/15 | A f 0/10; p 0/5; F f 0/10; p 0/5 |  | inf-4 |  | counts every line break once: ABOUT 2,594 (fits) instead of 2,608 (over by 8), EXP_STUDIO 1,176 instead of 1,1 |
| psychopathy-evidence-screen | 2.1.0 | P3 | 0/5 | - | F p 0/5 |  | inf-4 |  | enters R05 with the table's n 188 (both members of each couple) instead of 94 (one member per couple, the man  |
| psychopathy-evidence-screen | 2.2.0 | P3 | 0/5 | - | F p 0/5 |  | inf-4 |  | enters R05 with the table's n 188 (both members of each couple) instead of 94 (one member per couple, the man  |
| psychopathy-evidence-screen | 2.3.0 | P3 | 3/15 | 7/15 | A f 4/10; p 3/5; F f 2/10; p 1/5 | UNCONFIRMED | inf-3 |  | enters R05 with the table's n 188 (both members of each couple) instead of 94 (one per pair), the unit the fil |
| pupil-tracker-term-summary | 1.0.0 | P1 | 0/5 | - | F p 0/5 |  | inf-3 |  | leaves absences out of the base of the rate (19 of 34 lines get a higher rate; tiers still follow those rates) |
| pupil-tracker-term-summary | 1.0.0 | P5 | 0/5 | - | F p 0/5 |  | inf-3 |  | treats a run as broken by the weekend and by the change of sheet (lines 7 and 22 tiered by rate, Tier 2) |
| pupil-tracker-term-summary | 1.1.0 | P1 | 0/15 | 0/15 | A f 0/10; p 0/5; F f 0/10; p 0/5 |  | inf-3 |  | puts absences in the base of the rate (every line with an A gets a lower rate; tiers still follow those rates) |
| refurb-laptop-screen | 1.2.0 | P3 | 0/5 | - | F p 0/5 |  | inf-4 |  | BW-105 Buyer Protection £5.94 -> £144.69 pass (truth £6.25 -> £145.00 pass) |
| refurb-laptop-screen | 1.3.0 | P3 | 0/5 | - | F p 0/5 |  | inf-4 |  | BW-105 Buyer Protection £5.94 -> £144.69 pass (truth £6.25 -> £145.00 pass) |
| refurb-laptop-screen | 1.4.0 | P3 | 0/5 | 0/5 | A p 0/5; F p 0/5 |  | inf-4 |  | BW-105 Buyer Protection £5.94 -> £144.69 pass (truth £6.25 -> £145.00 pass) |
| student-laptop-shortlist | 2.3.0 | P5 | 0/5 | 0/5 | A p 0/5; F p 0/5 |  | inf-4 |  | screens on 500 GB (a quarter of the list on top): L-402 shortlisted at 67,990 instead of failing storage, L-41 |
| suitcase-cover-matrix-check | 2.0.0 | P3 | 0/5 | 0/5 | A p 0/5; F p 0/5 |  | inf-2 |  | lists the 28 position names ('Карта мира / чёрный' and 'Карта мира / молоко' as two designs) instead of the 24 |
| suitcase-cover-matrix-check | 2.1.0 | P6 | 0/15 | 0/15 | A f 0/10; p 0/5; F f 0/10; p 0/5 |  | inf-2 |  | S 13 / M 23 / L 19 / XL 5 (ЧХ-30150 52–58 in S, ЧХ-30134 62–68 in M, ЧХ-30153 72–78 in L) instead of S 12 / M  |
| suitcase-cover-matrix-check | 2.1.1 | P6 | 0/15 | 0/15 | A f 0/10; p 0/5; F f 0/10; p 0/5 |  | inf-2 |  | S 13 / M 23 / L 19 / XL 5 (ЧХ-30150 52–58 in S, ЧХ-30134 62–68 in M, ЧХ-30153 72–78 in L) instead of S 12 / M  |
| suitcase-cover-matrix-check | 2.2.0 | P6 | 0/5 | - | F p 0/5 |  | inf-2 |  | S 13 / M 23 / L 19 / XL 5 (ЧХ-30150 52–58 in S, ЧХ-30134 62–68 in M, ЧХ-30153 72–78 in L) instead of S 12 / M  |
| suitcase-cover-matrix-check | 2.3.0 | P6 | 0/5 | - | F p 0/5 |  | inf-2 |  | S 13 / M 23 / L 19 / XL 5 (ЧХ-30150 52–58 in S, ЧХ-30134 62–68 in M, ЧХ-30153 72–78 in L) instead of S 12 / M  |
| suitcase-cover-matrix-check | 2.4.0 | P6 | 0/5 | - | F p 0/5 |  | inf-2 |  | S 13 / M 23 / L 19 / XL 5 (ЧХ-30150 52–58 in S, ЧХ-30134 62–68 in M, ЧХ-30153 72–78 in L) instead of S 12 / M  |
| suitcase-cover-matrix-check | 2.5.0 | P6 | 0/5 | - | F p 0/5 |  | inf-2 |  | S 13 / M 23 / L 19 / XL 5 (ЧХ-30150 52–58 in S, ЧХ-30134 62–68 in M, ЧХ-30153 72–78 in L) instead of S 12 / M  |

### T.event: Event date = when it really happened, not the record or upload date

| task | ver | P | F | A | stages | verdict | S/I | re | misreading |
|---|---|---|---|---|---|---|---|---|---|
| ats-embedded-screening-register | 1.0.0 | P4 | 0/5 | - | F p 0/5 |  | inf-2 |  | counts C-305's 90 days from the screening date (2027-01-11) instead of from the resignation on 1 October (2026 |
| billiard-shift-audit | 2.0.0 | P2 | 0/5 | 0/5 | A p 0/5; F p 0/5 |  | inf-2 |  | costs the off-list cream ale from UPD 1203 for the 31.10 shift too (290 instead of 270), treating the shipping |
| blockprint-winter-close | 1.0.0 | P1 | 0/5 | - | F p 0/5 |  | inf-5 |  | books by bill date: drops KB-0924 (billed Wednesday 24 September, crates collectable from Monday 6 October, so |
| blockprint-winter-close | 1.1.0 | P1 | 0/5 | - | F p 0/5 |  | inf-5 |  | books by bill date: drops KB-0924 (billed Wednesday 24 September, crates collectable from Monday 6 October, so |
| blockprint-winter-close | 1.2.0 | P1 | 0/5 | 0/5 | A p 0/5; F p 0/5 |  | inf-5 |  | books by bill date: drops KB-0924 (billed Wednesday 24 September, crates collectable from Monday 6 October, so |
| brightwater-spec-qa | 1.0.0 | P5 | 0/5 | 0/5 | A p 0/5; F p 0/5 |  | st-v1 |  | (premise text not preserved; family from the signal_gate output) |
| brightwater-spec-qa | 1.1.0 | P5 | 0/5 | - | F p 0/5 |  | inf-4 |  | keeps 2004 for C-008 and C-039 (the signature year); the agreement's first day is 1 January 2006 |
| brightwater-spec-qa | 1.2.0 | P5 | 0/5 | - | F p 0/5 |  | inf-4 |  | keeps 2004 for C-008 and C-039 (the signature year); the agreement's first day is 1 January 2006 |
| cnc-router-bom-reconcile | 2.0.0 | P1 | 0/5 | - | F p 0/5 |  | inf-4 |  | keys the store on the dispatch date and counts both consignments of restock MJ-0929 as received, so the 2 moto |
| cnc-router-bom-reconcile | 2.1.0 | P1 | 0/5 | - | F p 0/5 |  | inf-4 |  | keys the store on the dispatch date and counts both consignments of restock MJ-0929 as received, so the 2 moto |
| cnc-router-bom-reconcile | 2.2.0 | P1 | 0/5 | - | F p 0/5 |  | inf-4 |  | keys the store on the dispatch date and counts both consignments of restock MJ-0929 as received, so the 2 moto |
| cnc-router-bom-reconcile | 2.3.0 | P1 | 0/15 | 0/15 | A f 0/10; p 0/5; F f 0/10; p 0/5 |  | inf-4 |  | keys the store on the dispatch date and counts both consignments of restock MJ-0929 as received, so the 2 moto |
| cnc-router-bom-reconcile | 2.4.0 | P1 | 0/5 | 0/5 | A p 0/5; F p 0/5 |  | inf-4 |  | keys the store on the dispatch date and counts both consignments of restock MJ-0929 as received, so the 2 moto |
| cnc-router-bom-reconcile | 2.5.0 | P1 | 0/5 | 0/5 | A p 0/5; F p 0/5 |  | inf-4 |  | keys the store on the dispatch date and counts both consignments of restock MJ-0929 as received, so the 2 moto |
| cnc-router-bom-reconcile | 2.6.0 | P1 | 0/15 | 1/15 | A f 0/10; p 1/5; F f 0/10; p 0/5 |  | inf-4 |  | keys the store on the dispatch date and counts both consignments of restock MJ-0929 as received, so the 2 moto |
| cnc-router-bom-reconcile | 2.6.1 | P1 | 0/15 | 1/15 | A f 1/10; p 0/5; F f 0/10; p 0/5 |  | inf-4 |  | keys the store on the dispatch date and counts both consignments of restock MJ-0929 as received, so the 2 moto |
| coloring-book-retitle-audit | 2.0.0 | P8 | 0/5 | - | F p 0/5 |  | inf-2 |  | keeps the export's PUBLISHED status; the firm whose record covers sticker books had its registration issued on |
| coloring-book-retitle-audit | 2.1.0 | P10 | 0/5 | - | F p 0/5 |  | inf-2 |  | keeps the export's PUBLISHED status (secondary premise, solved 5/5 by Fable in 2.0.0) |
| council-video-index | 1.0.0 | P1 | 0/5 | - | F p 0/5 |  | inf-2 |  | takes the time the export shows against an item as the moment the item opened; it is the moment the operator m |
| council-video-index | 1.1.0 | P1 | 2/5 | - | F p 2/5 |  | inf-2 |  | takes the time the export shows against an item as the moment the item opened; it is the moment the operator m |
| council-video-index | 1.2.0 | P1 | 0/15 | 0/15 | A f 0/10; p 0/5; F f 0/10; p 0/5 |  | inf-2 |  | takes the time the export shows against an item as the moment the item opened; it is the moment the operator m |
| council-video-index | 1.3.0 | P1 | 1/5 | 0/5 | A p 0/5; F p 1/5 |  | inf-2 |  | takes the time the export shows against an item as the moment the item opened; it is the moment the operator m |
| current-affairs-booklet-plan | 1.0.0 | P2 | 0/5 | - | F p 0/5 |  | inf-5 |  | files every placed point under its page heading: the award point (page 6, point 1) goes to May instead of June |
| current-affairs-booklet-plan | 1.1.0 | P4 | 0/5 | - | F p 0/5 |  | inf-3 |  | files the award point (page 6, point 1) under May, its page heading, instead of June; a wrongly merged park po |
| earth-guide-answer-claims | 1.0.0 | P4 | 0/5 | - | F p 0/5 |  | inf-4 |  | bills LA-06 (uploaded 30 Sep, accepted Fri 2 Oct 'this morning') and LA-11 (uploaded 29 Sep, accepted Thu 1 Oc |
| earth-guide-answer-claims | 1.1.0 | P4 | 0/5 | 0/5 | A p 0/5; F p 0/5 |  | inf-3 |  | bills LA-06 and LA-11 in 2026-09 (their upload and return month) instead of 2026-10 (accepted 2 and 1 October) |
| hammamet-voucher-reissue | 2.0.0 | P1 | 0/5 | - | F p 0/5 |  | inf-4 |  | room 2: first_meal 'lunch' and one lunch more than nights (7 for 6 nights) instead of 'dinner' and as many lun |
| hammamet-voucher-reissue | 2.1.0 | P1 | 0/5 | - | F p 0/5 |  | inf-4 |  | room 2: first_meal 'lunch' and one lunch more than nights (7 for 6 nights) instead of 'dinner' and as many lun |
| home-bp-diary-summary | 2.3.0 | P5 | 0/5 | 0/5 | A p 0/5; F p 0/5 |  | inf-3 |  | keeps the 4 October evening session (1004P) in treatment_sessions; the box ran out with the 2 October breakfas |
| killzone-journal-review | 1.0.0 | P2 | 0/5 | - | F p 0/5 |  | inf-6 |  | 61805102 (euro buy limit sent 01:40 New York, filled at the London open 03:00) -> none instead of london; 6181 |
| ktp-lesson-plan-alignment | 1.0.0 | P2 | 0/5 | - | F p 0/5 |  | st-v1 |  | joins each plan to the KTP row with its printed lesson number (Lesson No. 6 -> row 6), which after the lost 6  |
| ktp-lesson-plan-alignment | 2.0.0 | P2 | 0/5 | - | F p 0/5 |  | inf-2 |  | L06-L08 get topics 6, 7, 8 (the topics the plans teach) instead of 7, 8, 9: the 6 October lesson was lost to t |
| manhole-excavation-valuation | 1.0.0 | P1 | 0/5 | - | F p 0/5 |  | inf-2 |  | leaves A09 out (rings set 2026-09-29): 9 records, total 94.86 instead of 10 records, 107.59 |
| manhole-excavation-valuation | 1.1.0 | P1 | 0/5 | - | F p 0/5 |  | inf-2 |  | leaves A09 out (rings set 2026-09-29): 9 records, total 94.94 instead of 10 records, 107.67 |
| manhole-excavation-valuation | 1.2.0 | P1 | 0/5 | 0/5 | A p 0/5; F p 0/5 |  | inf-2 |  | leaves A09 out (rings set 2026-09-29): 9 records, total 94.94 instead of 10 records, 107.67 |
| mustangs-tryout-roster | 2.0.0 | P1 | 0/5 | - | F p 0/5 |  | inf-3 |  | takes the received stamp as the signing date: MU-124 and MU-125 (paper forms signed at the Saturday 5 Septembe |
| mustangs-tryout-roster | 2.1.0 | P1 | 0/5 | 0/5 | A p 0/5; F p 0/5 |  | inf-3 |  | takes the received stamp as the signing date: MU-124 and MU-125 (paper forms signed at the Saturday 5 Septembe |
| pathway-choice-audit | 2.0.0 | P5 | 0/15 | 0/15 | A f 0/10; p 0/5; F f 0/10; p 0/5 |  | inf-3 |  | treats S04 (Brenda, ST1048) and S15 (Joy, AS2039) as late because they were keyed on Friday morning (or, ignor |
| pathway-choice-audit | 2.1.0 | P5 | 0/5 | 0/5 | A p 0/5; F p 0/5 |  | inf-3 |  | treats S04 (Brenda, ST1048) and S15 (Joy, AS2039) as late because they were keyed on Friday morning (or, ignor |
| pathway-choice-audit | 2.2.0 | P5 | 0/5 | - | F p 0/5 |  | inf-5 |  | treats S04 (Brenda, ST1048) and S15 (Joy, AS2039) as late because they were keyed on Friday morning: nothing i |
| pathway-choice-audit | 2.3.0 | P5 | 0/15 | - | F f 0/10; p 0/5 |  | inf-5 |  | treats S04 (Brenda, ST1048) and S15 (Joy, AS2039) as late because they were keyed on Friday morning: nothing i |
| pathway-choice-audit | 2.4.0 | P5 | 0/5 | - | F p 0/5 |  | inf-5 |  | treats S04 (Brenda, ST1048) and S15 (Joy, AS2039) as late because they were keyed on Friday morning: nothing s |
| posting-month-close | 1.0.0 | P3 | 0/5 | - | F p 0/5 |  | inf-4 |  | counts the dental clinic's order (paid 28 August, delivered 3 September) and drops the Calgary realtor's (paid |
| posting-month-close | 1.1.0 | P3 | 0/5 | - | F p 0/5 |  | inf-4 |  | counts the dental clinic's order (paid 28 August, delivered 3 September) and drops the Calgary realtor's (paid |
| probation-answer-key | 2.3.0 | P6 | 0/5 | 0/5 | A p 0/5; F p 0/5 |  | inf-2 |  | case 7 'незаконно' (window from the diploma handover 14.09.2023 still open on 01.09.2026). Truth: studies ende |
| probation-answer-key | 2.4.0 | P6 | 0/5 | 0/5 | A p 0/5; F p 0/5 |  | inf-2 |  | case 7 'незаконно' (window from the diploma handover 14.09.2023 still open on 01.09.2026). Truth: studies ende |
| psychopathy-evidence-screen | 2.0.0 | P3 | 0/5 | - | F p 0/5 |  | inf-3 |  | reads age_band as the age at assessment: R05 (16-44 at enrolment, assessed 36 months later, so 19 or older) is |
| pupil-tracker-term-summary | 1.0.0 | P4 | 0/5 | - | F p 0/5 |  | inf-4 |  | leaves out the calendar's announced Monday 17 Nov instead of Tuesday 18 Nov (lines 9 and 25 lose a ! instead o |
| pupil-tracker-term-summary | 1.1.0 | P3 | 0/15 | 0/15 | A f 0/10; p 0/5; F f 0/10; p 0/5 | BLIND-1.0 | inf-3 |  | counts the two A days (Sun 21, Mon 22 Sep) on line 34 (absences 2 instead of 0) |
| pupil-tracker-term-summary | 1.1.0 | P4 | 0/15 | 0/15 | A f 0/10; p 0/5; F f 0/10; p 0/5 | BLIND-1.0 | inf-3 |  | leaves out the calendar's announced Monday 17 Nov instead of Tuesday 18 Nov (lines 9 and 25 lose a ! instead o |
| pupil-tracker-term-summary | 1.2.0 | P4 | 0/5 | 0/5 | A p 0/5; F p 0/5 |  | inf-3 |  | leaves out the calendar's announced Monday 17 Nov instead of Tuesday 18 Nov (lines 9 and 25 lose a ! instead o |
| refurb-laptop-screen | 1.1.0 | P1 | 0/5 | - | F p 0/5 |  | inf-4 |  | prices the stick at £14.00: BW-102 £143.99 pass (truth £152.49 fail), BW-103 £123.99 (truth £132.49), and BW-1 |
| refurb-laptop-screen | 1.2.0 | P1 | 0/5 | - | F p 0/5 |  | inf-4 |  | prices the stick at £14.00: BW-102 £143.99 pass (truth £152.49 fail), BW-103 £123.99 (truth £132.49), and BW-1 |
| refurb-laptop-screen | 1.3.0 | P1 | 0/5 | - | F p 0/5 |  | inf-4 |  | prices the stick at £14.00: BW-102 £143.99 pass (truth £152.49 fail), BW-103 £123.99 (truth £132.49), and BW-1 |
| sandwich-image-audit | 1.0.0 | P3 | 0/5 | - | F p 0/5 |  | inf-4 |  | ZK-231 and ZK-235 count as live on Wasla (covered) |
| sandwich-image-audit | 1.1.0 | P2 | 0/5 | - | F p 0/5 |  | inf-3 |  | ZK-231 (and ZK-235 when P3 is also missed) counted live on Wasla |
| sandwich-image-audit | 1.2.0 | P3 | 0/5 | - | F p 0/5 |  | inf-3 |  | ZK-231 (and ZK-235 when P4 is also missed) counted live on Wasla |
| station-register-consolidation | 2.0.0 | P3 | 0/5 | - | F p 0/5 |  | inf-3 |  | takes the circular's announced closure date as the status, so meteorological 47-007 is dropped from Firuzkuh's |
| station-register-consolidation | 2.1.0 | P3 | 0/5 | - | F p 0/5 |  | inf-3 |  | takes the circular's announced closure date as the status, so meteorological 47-007 is dropped from Firuzkuh's |
| station-register-consolidation | 2.2.0 | P3 | 0/5 | - | F p 0/5 |  | inf-3 |  | takes the circular's announced closure date as the status, so meteorological 47-007 is dropped from Firuzkuh's |
| student-laptop-shortlist | 2.0.0 | P1 | 0/5 | - | F p 0/5 |  | inf-4 |  | prices on the screening day: L-404 77,490 instead of 73,490; L-407 91,791 out_of_budget instead of 89,991 shor |
| student-laptop-shortlist | 2.1.0 | P1 | 0/5 | - | F p 0/5 |  | inf-4 |  | prices on the screening day: L-404 77,490 instead of 73,490; L-407 91,791 out_of_budget instead of 89,991 shor |
| student-laptop-shortlist | 2.2.0 | P1 | 0/5 | 0/5 | A p 0/5; F p 0/5 |  | inf-4 |  | prices on the screening day: L-404 77,490 instead of 73,490; L-407 91,791 out_of_budget instead of 89,991 shor |
| student-laptop-shortlist | 2.3.0 | P1 | 0/5 | 0/5 | A p 0/5; F p 0/5 |  | inf-4 |  | prices on the screening day: L-404 77,490 instead of 73,490; L-407 91,791 out_of_budget instead of 89,991 shor |
| timesheet-overtime-review | 2.0.0 | P1 | 0/5 | - | F p 0/5 |  | inf-2 |  | counts Monday's overtime from the required leave time (19:00, or 20:00 after a P2 miss) instead of from nine h |

### S.population: Population reshaped by an incidental fact (who or what is in scope)

| task | ver | P | F | A | stages | verdict | S/I | re | misreading |
|---|---|---|---|---|---|---|---|---|---|
| ats-embedded-screening-register | 1.2.0 | P5 | 0/5 | - | F p 0/5 |  | inf-4 |  | C-301 earliest employer 'Kodexa Systems' instead of 'Pixelsense Embedded' (and six more months on her total, w |
| ats-embedded-screening-register | 1.3.0 | P5 | 0/5 | - | F p 0/5 |  | inf-4 |  | C-301 earliest employer 'Kodexa Systems' instead of 'Pixelsense Embedded' (and six more months on her total, w |
| ats-embedded-screening-register | 1.4.0 | P5 | 0/5 | - | F p 0/5 |  | inf-2 |  | C-301 earliest employer 'Kodexa Systems' instead of 'Pixelsense Embedded' (and six more months on her total, w |
| brightwater-spec-qa | 1.0.0 | P4 | 0/5 | 0/5 | A p 0/5; F p 0/5 |  | st-v1 |  | (premise text not preserved; family from the signal_gate output) |
| brightwater-spec-qa | 1.1.0 | P2 | 0/5 | - | F p 0/5 |  | inf-4 |  | publishes the case-studies string C-043: lists it in name_strings (it carries {{BRAND}}) and in throughput (it |
| brightwater-spec-qa | 1.2.0 | P2 | 0/5 | - | F p 0/5 |  | inf-4 |  | publishes the case-studies string C-043: lists it in name_strings (it carries {{BRAND}}) and in throughput (it |
| brightwater-spec-qa | 1.3.0 | P2 | 0/15 | 0/15 | A f 0/10; p 0/5; F f 0/10; p 0/5 |  | inf-4 |  | publishes the case-studies string C-043: lists it in throughput (it states the 2025 figure) |
| cafe-kitchen-schedule-revisions | 1.0.0 | P5 | 0/5 | 0/5 | A p 0/5; F p 0/5 |  | st-v1 |  | treats every row that serves the pass as part of the change: adds the heat lamp LP-1, the ticket rail RP-1 and |
| cafe-kitchen-schedule-revisions | 1.0.0 | P8 | 0/5 | 0/5 | A p 0/5; F p 0/5 |  | st-v1 |  | follows the hand-over's restatement 'everything that is at 90 comes down to 85' and adds the EQ rows at 90 (GR |
| cafe-kitchen-schedule-revisions | 2.0.0 | P8 | 0/5 | - | F p 0/5 |  | inf-3 |  | moves the shelf over the refrigerated prep table with the worktops (140, listed as moved); the chilled counter |
| council-video-index | 1.0.0 | P2 | 0/5 | - | F p 0/5 |  | inf-3 |  | indexes every item of the published order, so the lease item the Council took off at the Wojt's request gets a |
| council-video-index | 1.1.0 | P2 | 0/5 | - | F p 0/5 |  | inf-3 |  | indexes every item of the published order, so the lease item the Council took off at the Wojt's request gets a |
| council-video-index | 1.2.0 | P2 | 0/15 | 0/15 | A f 0/10; p 0/5; F f 0/10; p 0/5 |  | inf-3 |  | indexes every item of the published order, so the lease item the Council took off at the Wojt's request gets a |
| deck-preread-review | 1.0.0 | P4 | 0/5 | 0/5 | A p 0/5; F p 0/5 |  | st-v1 |  | counts every comment that moves, swaps or adds something as a sequence request: the swap of a pie and its lege |
| eco-guard-errata-review | 1.0.0 | P1 | 0/5 | 0/5 | A p 0/5; F p 0/5 |  | st-v1 |  | applies the final note's correction to every location that repeats its wording (the Figure 4.1 caption and the |
| feast-sharing-runsheet | 1.0.0 | P2 | 0/5 | - | F p 0/5 |  | inf-2 |  | forms groups from the whole roll, leaving in the room the singers who are on the choir bus to the cathedral fo |
| feast-sharing-runsheet | 1.1.0 | P2 | 0/5 | - | F p 0/5 |  | inf-2 |  | forms groups from the whole roll, leaving in the room the singers who are on the choir bus to the cathedral fo |
| home-bp-diary-summary | 1.0.0 | P3 | 0/5 | 0/5 | A p 0/5; F p 0/5 |  | st-v1 |  | measures the 30 minutes from the workout's logged start (or never cross-references the training export), so th |
| ktp-lesson-plan-alignment | 1.0.0 | P3 | 0/5 | - | F p 0/5 |  | st-v1 |  | lists 5.2.4 as uncovered: it belongs to term 1 topic 6 and no plan lists it, but the district moved it to term |
| ktp-lesson-plan-alignment | 1.0.0 | P4 | 0/5 | - | F p 0/5 |  | st-v1 |  | credits L04 (review in the summary) and L08 (review in the practice stage) because they do review the previous |
| ktp-lesson-plan-alignment | 2.0.0 | P4 | 0/5 | - | F p 0/5 |  | inf-2 |  | 5.2.4 (topic 6; no plan lists it) appears in term1_outcomes as 'not addressed'; the district moved it to term  |
| line-reference-belegliste | 1.0.0 | P2 | 0/5 | - | F p 0/5 |  | inf-2 |  | drops B (as announced) and keeps C, so B's citations are kept=false and C's kept=true |
| line-reference-belegliste | 1.1.0 | P2 | 0/5 | - | F p 0/5 |  | inf-2 |  | drops B (as announced) and keeps C, so B's citations are kept=false and C's kept=true |
| line-reference-belegliste | 1.2.0 | P2 | 0/5 | 0/5 | A p 0/5; F p 0/5 |  | inf-2 |  | drops B (as announced) and keeps C, so B's citations are kept=false and C's kept=true |
| moisturiser-price-screen | 2.0.0 | P2 | 0/5 | - | F p 0/5 |  | inf-2 |  | applies MEHR120 to BN-2104 (Tabriz) and BN-2107 (Mashhad): BN-2104 drops to 984,000 and joins the shortlist, B |
| moisturiser-price-screen | 2.0.0 | P4 | 0/5 | - | F p 0/5 |  | inf-2 |  | reads BN-2108's declaration as 'Petrolatum' alone and adds it to pure_petrolatum |
| moisturiser-price-screen | 2.1.0 | P2 | 0/5 | - | F p 0/5 |  | inf-2 |  | applies MEHR120 to BN-2104 (Tabriz) and BN-2107 (Mashhad): BN-2104 drops to 984,000 and joins the shortlist, B |
| moisturiser-price-screen | 2.1.0 | P4 | 0/5 | - | F p 0/5 |  | inf-2 |  | reads BN-2108's declaration as 'Petrolatum' alone and adds it to pure_petrolatum |
| moisturiser-price-screen | 2.2.0 | P2 | 0/15 | 0/15 | A f 0/10; p 0/5; F f 0/10; p 0/5 | BLIND-1.0 | inf-2 |  | applies MEHR120 to BN-2104 (Tabriz) and BN-2107 (Mashhad): BN-2104 drops to 984,000 and joins the shortlist, B |
| moisturiser-price-screen | 2.3.0 | P2 | 0/5 | 0/5 | A p 0/5; F p 0/5 |  | inf-2 |  | applies MEHR120 to BN-2104 (Tabriz) and BN-2107 (Mashhad): BN-2104 drops to 984,000 and joins the shortlist, B |
| moot-issue3-memorial-audit | 1.0.0 | P4 | 0/5 | 0/5 | A p 0/5; F p 0/5 |  | st-v1 |  | moves every paragraph that mentions Article 14 or the basic structure, including the two that only state Kavit |
| moot-issue3-memorial-audit | 2.0.0 | P4 | 0/5 | - | F p 0/5 |  | inf-2 |  | keeps P11 (an unequal-treatment argument that never names Article 14) in Issue 3 |
| moot-issue3-memorial-audit | 2.1.0 | P4 | 0/5 | 0/5 | A p 0/5; F p 0/5 |  | inf-2 |  | keeps P11 (an unequal-treatment argument that never names Article 14) in Issue 3 |
| moot-issue3-memorial-audit | 2.2.0 | P4 | 0/5 | 0/5 | A p 0/5; F p 0/5 |  | inf-2 |  | keeps P11 (an unequal-treatment argument that never names Article 14) in Issue 3 |
| mustangs-tryout-roster | 1.0.0 | P7 | 0/5 | 0/5 | A p 0/5; F p 0/5 |  | st-v1 |  | applies 'Weekdays: can't be at the field before 5:00 pm' to the new 4:00 pm Sunday session: MU-115 is counted  |
| mustangs-tryout-roster | 2.0.0 | P7 | 3/5 | - | F p 3/5 | AMBIGUOUS | inf-2 |  | applies the religious-ed arrival on 20 September: MU-117 listed late (4:12 pm, 12 minutes after a 4:00 pm star |
| mustangs-tryout-roster | 2.1.0 | P7 | 0/5 | 0/5 | A p 0/5; F p 0/5 | BLIND-1.0 | inf-3 |  | applies the religious-ed arrival on 20 September although the note names only the Sundays class meets: MU-117  |
| mustangs-tryout-roster | 2.2.0 | P7 | 0/5 | 0/5 | A p 0/5; F p 0/5 |  | inf-3 |  | applies the religious-ed arrival on 20 September although the note names only the Sundays class meets: MU-117  |
| okra-manuscript-revision | 1.0.0 | P2 | 0/5 | 0/5 | A p 0/5; F p 0/5 |  | st-v1 |  | also lists the abstract, conclusion and section-3.4 statements and Table 4 because they repeat the old yields  |
| pathway-choice-audit | 1.0.0 | P3 | 0/5 | 0/5 | A p 0/5; F p 0/5 |  | st-v1 |  | changes every line naming the teacher and every byline/footer line: adds the STEM 'Queries' line (literal sear |
| pathway-choice-audit | 2.0.0 | P1 | 0/15 | 0/15 | A f 0/10; p 0/5; F f 0/10; p 0/5 |  | inf-2 |  | counts every combination printed on the learner's list as offered, so S08 (ST3082) and S11 (ST3015), both on t |
| pathway-choice-audit | 2.0.0 | P3 | 0/15 | 0/15 | A f 0/10; p 0/5; F f 0/10; p 0/5 |  | inf-3 |  | gives the STEM lines as [3, 19, 32]: the page-3 footer credits the list to 'the head of science' (Tr. Wekesa r |
| pathway-choice-audit | 2.0.0 | P4 | 0/15 | 0/15 | A f 0/10; p 0/5; F f 0/10; p 0/5 |  | inf-2 |  | follows up G9-009 (Isaac Kamau) and G9-022 (Wycliffe Ouma), who return no slip because they left on 5 October |
| pathway-choice-audit | 2.1.0 | P4 | 0/5 | 0/5 | A p 0/5; F p 0/5 |  | inf-2 |  | follows up G9-009 (Isaac Kamau) and G9-022 (Wycliffe Ouma), who return no slip because they left on 5 October |
| pathway-choice-audit | 2.2.0 | P1 | 0/5 | - | F p 0/5 |  | inf-2 |  | counts every combination printed on the learner's list as offered, so S08 (ST3082) and S11 (ST3015), both on t |
| pathway-choice-audit | 2.2.0 | P3 | 0/5 | - | F p 0/5 |  | inf-3 |  | gives the STEM lines as [3, 19, 32]: the page-3 footer credits the list to 'the head of science' (Tr. Wekesa r |
| pathway-choice-audit | 2.2.0 | P4 | 0/5 | - | F p 0/5 |  | inf-3 |  | follows up G9-022 (Wycliffe Ouma, 9 West, no slip): the NEMIS line names only Kamau, and the second transfer t |
| pathway-choice-audit | 2.3.0 | P1 | 0/15 | - | F f 0/10; p 0/5 |  | inf-2 |  | counts every combination printed on the learner's list as offered, so S08 (ST3082) and S11 (ST3015), both on t |
| pathway-choice-audit | 2.3.0 | P3 | 0/15 | - | F f 0/10; p 0/5 |  | inf-3 |  | gives the STEM lines as [3, 19, 32]: the page-3 footer credits the list to 'the head of science' (Tr. Wekesa r |
| pathway-choice-audit | 2.3.0 | P4 | 0/15 | - | F f 0/10; p 0/5 |  | inf-3 |  | follows up G9-022 (Wycliffe Ouma, 9 West, no slip): the NEMIS line names only Kamau, and the second transfer t |
| pathway-choice-audit | 2.4.0 | P1 | 0/5 | - | F p 0/5 |  | inf-2 |  | counts every combination printed on the learner's list as offered, so S08 (ST3082) and S11 (ST3015), both on t |
| pathway-choice-audit | 2.4.0 | P3 | 0/5 | - | F p 0/5 |  | inf-3 |  | gives the STEM lines as [3, 19, 32]: the page-3 footer credits the list to 'the head of science' (Tr. Wekesa r |
| pathway-choice-audit | 2.4.0 | P4 | 0/5 | - | F p 0/5 |  | inf-4 |  | follows up G9-022 (Wycliffe Ouma, 9 West, no slip): the NEMIS line names only Kamau, and nothing says Wycliffe |
| probation-answer-key | 1.0.0 | P4 | 0/5 | 0/5 | A p 0/5; F p 0/5 |  | st-v1 |  | applies art. 331.3 (no probation for teaching staff in their first job within two years of graduation) to case |
| profile-copy-claims-audit | 1.0.0 | P1 | 0/5 | 0/5 | A p 0/5; F p 0/5 |  | st-v1 |  | takes the widget completion rate from the GA4 export's Grand total row (75 of 115, the 65.2% repeated in the d |
| profile-copy-claims-audit | 1.0.0 | P3 | 0/5 | 0/5 | A p 0/5; F p 0/5 |  | st-v1 |  | follows the checklist's broader restatement ('No place names in the profile copy') and lists every section nam |
| profile-copy-claims-audit | 2.0.0 | P4 | 0/5 | - | F p 0/5 |  | inf-3 |  | counts the (none) sessions, which can only be the host-stand tablet's bookmark where the manager keys phone bo |
| profile-copy-claims-audit | 2.5.0 | P8 | 5/5 | 5/5 | A p 5/5; F p 5/5 |  | inf-4 |  | takes every month's all_bookings from TableHop's `all` row, counting the house row's walk-in tables as booking |
| profile-copy-claims-audit | 2.6.0 | P8 | 5/5 | 5/5 | A p 5/5; F p 5/5 | AMBIGUOUS | inf-4 |  | takes every month's all_bookings from TableHop's `all` row, counting the house row's walk-in tables as booking |
| profile-copy-claims-audit | 2.7.0 | P8 | 0/5 | 0/5 | A p 0/5; F p 0/5 |  | inf-4 |  | takes every month's all_bookings from TableHop's `all` row, counting the house row's walk-in tables as booking |
| profile-copy-claims-audit | 2.8.0 | P8 | 0/5 | 0/5 | A p 0/5; F p 0/5 |  | inf-4 |  | takes every month's all_bookings from TableHop's `all` row, counting the house row's walk-in tables as booking |
| psychopathy-evidence-screen | 1.0.0 | P1 | 0/5 | 0/5 | A p 0/5; F p 0/5 |  | st-v1 |  | screens under the protocol and amendment 1 only and misses the PI's e-mail exclusion: the prison (R04) and sec |
| psychopathy-evidence-screen | 2.0.0 | P1 | 0/5 | - | F p 0/5 |  | inf-3 |  | takes custody from the setting code only: Marta's first cohort (R13, COM in the table) is not excluded; with P |
| psychopathy-evidence-screen | 2.1.0 | P1 | 0/5 | - | F p 0/5 |  | inf-3 |  | takes custody from the setting code only: Marta's first cohort (R13, COM in the table) is not excluded; with P |
| psychopathy-evidence-screen | 2.2.0 | P1 | 0/5 | - | F p 0/5 |  | inf-3 |  | takes custody from the setting code only: Marta's first cohort (R13, COM in the table) is not excluded; with P |
| psychopathy-evidence-screen | 2.3.0 | P1 | 0/15 | 0/15 | A f 0/10; p 0/5; F f 0/10; p 0/5 | BLIND-1.0 | inf-3 |  | takes custody from the setting code only: Marta's first cohort (R13, COM in the table) is not excluded; with P |
| pupil-tracker-term-summary | 1.2.0 | P6 | 0/5 | 0/5 | A p 0/5; F p 0/5 |  | inf-3 |  | keeps a record for line 32 (the boy who left on the last day of term), 34 records instead of 33 |
| sandwich-image-audit | 1.0.0 | P2 | 0/5 | - | F p 0/5 |  | inf-3 |  | off_menu_skus = the four small-fino fries SKUs only; ZK-233 and ZK-235 stay on sale |
| station-register-consolidation | 1.0.0 | P2 | 0/5 | 0/5 | A p 0/5; F p 0/5 |  | st-v1 |  | takes the active hydrometric set from the Remarks of Table 2-1 alone and misses the operator's later out-of-se |
| station-register-consolidation | 2.0.0 | P2 | 0/5 | - | F p 0/5 |  | inf-3 |  | builds Garmsar's active hydrometric set from Table 2-1's Remarks alone, so 47-942 stays active |
| student-laptop-shortlist | 1.0.0 | P3 | 0/5 | 0/5 | A p 0/5; F p 0/5 |  | st-v1 |  | takes stock from the export's 02:00 snapshot only, so L-404 (the only Relay Digital listing, the draft's top p |
| student-laptop-shortlist | 2.0.0 | P2 | 0/5 | - | F p 0/5 |  | inf-2 |  | keeps L-404 (the only Relay Digital listing) in stock: shortlisted at its price, and with the same desk score  |
| suitcase-cover-matrix-check | 2.0.0 | P1 | 0/5 | 0/5 | A p 0/5; F p 0/5 |  | inf-3 |  | keeps the six Indian-supplier luggage scales the 9 October export lists as active: luggage_scales 46 instead o |
| suitcase-cover-matrix-check | 2.1.0 | P1 | 0/15 | 0/15 | A f 0/10; p 0/5; F f 0/10; p 0/5 |  | inf-3 |  | keeps the six Indian-supplier luggage scales the 9 October export lists as active: luggage_scales 46 instead o |
| suitcase-cover-matrix-check | 2.1.1 | P1 | 0/15 | 0/15 | A f 0/10; p 0/5; F f 0/10; p 0/5 |  | inf-3 |  | keeps the six Indian-supplier luggage scales the 9 October export lists as active: luggage_scales 46 instead o |
| suitcase-cover-matrix-check | 2.2.0 | P1 | 0/5 | - | F p 0/5 |  | inf-3 |  | keeps the six Indian-supplier luggage scales the 9 October export lists as active: luggage_scales 46 instead o |
| suitcase-cover-matrix-check | 2.3.0 | P1 | 0/5 | - | F p 0/5 |  | inf-3 |  | keeps the six Indian-supplier luggage scales the 9 October export lists as active: luggage_scales 46 instead o |
| suitcase-cover-matrix-check | 2.4.0 | P1 | 0/5 | - | F p 0/5 |  | inf-3 |  | keeps the six Indian-supplier luggage scales the 9 October export lists as active: luggage_scales 46 instead o |
| suitcase-cover-matrix-check | 2.5.0 | P1 | 0/5 | - | F p 0/5 |  | inf-3 |  | keeps the six Indian-supplier luggage scales the 9 October export lists as active: luggage_scales 46 instead o |

### CV.caption: Rule that lives only in a caption, table note or footnote

| task | ver | P | F | A | stages | verdict | S/I | re | misreading |
|---|---|---|---|---|---|---|---|---|---|
| billiard-shift-audit | 1.0.0 | P1 | 0/5 | 0/5 | A p 0/5; F p 0/5 |  | st-v1 |  | bills the Tuesday 4 November shift on the weekday tariffs (450 per hour before 17:00) because the POS prints ' |
| brightwater-spec-qa | 1.0.0 | P2 | 0/5 | 0/5 | A p 0/5; F p 0/5 |  | st-v1 |  | (premise text not preserved; family from the signal_gate output) |
| cafe-kitchen-schedule-revisions | 1.0.0 | P2 | 0/5 | 0/5 | A p 0/5; F p 0/5 |  | st-v1 |  | reads pos_cm as the start face for every row and takes each appliance's centre as pos_cm + length_cm/2, giving |
| cafe-kitchen-schedule-revisions | 1.0.0 | P9 | 0/5 | 0/5 | A p 0/5; F p 0/5 |  | st-v1 |  | reads elevation C in plan order (west to east, left to right), giving MP-1 at the left end and CO-1 at the rig |
| cafe-kitchen-schedule-revisions | 2.0.0 | P3 | 0/5 | - | F p 0/5 |  | inf-2 |  | reads the sink's pos_cm (120) from the north run's origin: legs 308 / 130 / 438 instead of 238 / 200 / 438, an |
| cafe-kitchen-schedule-revisions | 2.1.0 | P12 | 0/15 | 0/15 | A f 0/10; p 0/5; F f 0/10; p 0/5 |  | inf-2 |  | draws elevation C in plan order (MP-1 left, CO-1 right); seen from inside facing south, west is on the right:  |
| cafe-kitchen-schedule-revisions | 2.1.1 | P12 | 0/15 | 0/15 | A f 0/10; p 0/5; F f 0/10; p 0/5 |  | inf-2 |  | draws elevation C in plan order (MP-1 left, CO-1 right); seen from inside facing south, west is on the right:  |
| cafe-kitchen-schedule-revisions | 2.2.0 | P12 | 0/5 | - | F p 0/5 |  | inf-2 |  | draws elevation C in plan order (MP-1 left, CO-1 right); seen from inside facing south, west is on the right:  |
| cafe-kitchen-schedule-revisions | 2.3.0 | P12 | 0/15 | - | F f 0/10; p 0/5 |  | inf-2 |  | draws elevation C in plan order (MP-1 left, CO-1 right); seen from inside facing south, west is on the right:  |
| coloring-book-retitle-audit | 1.0.0 | P1 | 0/5 | 0/5 | A p 0/5; F p 0/5 |  | st-v1 |  | applies only the keyword rules of the main text (title/subtitle words, 50-character limit) and misses the bran |
| coloring-book-retitle-audit | 1.0.0 | P9 | 0/5 | 0/5 | A p 0/5; F p 0/5 |  | st-v1 |  | takes every live class-16 registration as covering the book (Table 1's body) and misses the goods limit in the |
| deck-preread-review | 1.0.0 | P1 | 0/5 | 0/5 | A p 0/5; F p 0/5 |  | st-v1 |  | reads every district page's Movement figure as the August movement, so the 'Up X% in August' titles whose perc |
| deck-preread-review | 2.4.0 | P5 | 1/5 | 0/5 | A p 0/5; F p 1/5 |  | inf-2 |  | N9 on S-25 instead of S-24 (the last page, which carries the three messages) |
| deck-preread-review | 2.5.0 | P5 | 5/15 | 0/15 | A f 0/10; p 0/5; F f 4/10; p 1/5 |  | inf-2 |  | N9 on S-25 instead of S-24 (the last page, which carries the three messages) |
| deck-preread-review | 2.6.0 | P5 | 1/5 | 0/5 | A p 0/5; F p 1/5 |  | inf-2 |  | N9 on S-25 instead of S-24 (the last page, which carries the three messages) |
| deck-preread-review | 2.7.0 | P5 | 1/5 | 0/5 | A p 0/5; F p 1/5 |  | inf-2 |  | N9 on S-25 instead of S-24 (the last page, which carries the three messages) |
| eco-guard-errata-review | 1.0.0 | P3 | 0/5 | 0/5 | A p 0/5; F p 0/5 |  | st-v1 |  | classes 'the loss can diverge (J -> infinity)' as an overstatement, judging divergence for gradient descent in |
| hammamet-voucher-reissue | 1.0.0 | P2 | 0/5 | 0/5 | A p 0/5; F p 0/5 |  | st-v1 |  | takes the voucher's 'Carthagia Park et Aqua Splash gratuit*' at face value: one free entry per guest to each o |
| home-bp-diary-summary | 1.0.0 | P2 | 0/5 | 0/5 | A p 0/5; F p 0/5 |  | st-v1 |  | averages the shaded day 1 (23 August), because the protocol text lists only the workout exclusion and never na |
| ktp-lesson-plan-alignment | 1.0.0 | P5 | 0/5 | - | F p 0/5 |  | st-v1 |  | lists L07 (the practical-work lesson, whose stage 1 is a safety briefing without a review) because section 4.2 |
| ktp-lesson-plan-alignment | 2.0.0 | P3 | 0/5 | - | F p 0/5 |  | inf-3 |  | L06 (week 7, a practical-work row; its plan opens with a hook and no review) answered 'not met', and L07 and L |
| ktp-lesson-plan-alignment | 2.1.0 | P3 | 0/5 | - | F p 0/5 |  | inf-4 |  | L02 (week-2 row typed practical work; its plan prints 'new material' and opens its hook with a review) answere |
| ktp-lesson-plan-alignment | 2.2.0 | P3 | 0/5 | - | F p 0/5 |  | inf-4 |  | L02 (week-2 row typed practical work; its plan prints 'new material' and opens its hook with a review) answere |
| ktp-lesson-plan-alignment | 2.3.0 | P3 | 0/5 | 0/5 | A p 0/5; F p 0/5 |  | inf-4 |  | L02 (week-2 row typed practical work; its plan prints 'new material' and opens its hook with a review) answere |
| lassa-kap-results-sheet | 1.0.0 | P3 | 0/5 | - | F p 0/5 |  | inf-2 |  | h01_table 63/15/269/53 and h02_table 66/12/276/46 (score 5-7 good) instead of 39/39/121/201 and 44/34/178/144  |
| lassa-kap-results-sheet | 1.1.0 | P3 | 0/15 | 0/15 | A f 0/10; p 0/5; F f 0/10; p 0/5 | BLIND-1.0 | inf-2 |  | h01_table 63/15/269/53 and h02_table 66/12/276/46 (score 5-7 good) instead of 39/39/121/201 and 44/34/178/144  |
| lassa-kap-results-sheet | 1.2.0 | P3 | 0/5 | 0/5 | A p 0/5; F p 0/5 |  | inf-2 |  | h01_table 63/15/269/53 and h02_table 66/12/276/46 (score 5-7 good) instead of 39/39/121/201 and 44/34/178/144  |
| moisturiser-price-screen | 1.0.0 | P3 | 0/5 | 0/5 | A p 0/5; F p 0/5 |  | st-v1 |  | takes size_ml as the listing's volume, so the two-item Cicalm balm (BN-2111) is reported as 50 ml instead of 1 |
| moot-issue3-memorial-audit | 1.0.0 | P1 | 0/5 | 0/5 | A p 0/5; F p 0/5 |  | st-v1 |  | counts only the prose paragraphs (roadmap, law, In casu, conclusion) and drops the issue title and every headi |
| moot-issue3-memorial-audit | 1.0.0 | P8 | 0/5 | 0/5 | A p 0/5; F p 0/5 |  | st-v1 |  | applies no roadmap requirement (Rule 6 does not state one) and reports an empty list |
| moot-issue3-memorial-audit | 2.0.0 | P9 | 0/5 | - | F p 0/5 |  | inf-3 |  | lists 3.1 as compliant because a roadmap row follows it, though it names only 3.1.1 and 3.1.2 |
| moot-issue3-memorial-audit | 2.1.0 | P9 | 0/5 | 0/5 | A p 0/5; F p 0/5 |  | inf-3 |  | lists 3.1 as compliant because a roadmap row follows it, though it names only 3.1.1 and 3.1.2 |
| mustangs-tryout-roster | 1.0.0 | P6 | 0/5 | 0/5 | A p 0/5; F p 0/5 |  | st-v1 |  | plans around the tentative conflict 'Tent. - may be away Fri Sept 18 - Sun Sept 20': MU-112 is taken off the s |
| okra-manuscript-revision | 1.0.0 | P8 | 0/5 | 0/5 | A p 0/5; F p 0/5 |  | st-v1 |  | computes B:C as gross income / cost of cultivation, the formula and example in the journal's author guidelines |
| probation-answer-key | 1.0.0 | P5 | 0/5 | 0/5 | A p 0/5; F p 0/5 |  | st-v1 |  | counts case 2's three-month probation from 02.02.2026 without excluding the sick leave 16.03-27.03 (12 days),  |
| profile-copy-claims-audit | 1.0.0 | P5 | 0/5 | 0/5 | A p 0/5; F p 0/5 |  | st-v1 |  | copies the CMS counter (stored_chars) or takes len() of the stored text, counting each `&amp;` as 5 characters |
| psychopathy-evidence-screen | 1.0.0 | P5 | 0/5 | 0/5 | A p 0/5; F p 0/5 |  | st-v1 |  | reads Table 2's body without its note: B-Scan is listed as informant-rated (colleagues and supervisors), so R1 |
| refurb-laptop-screen | 1.1.0 | P3 | 0/5 | - | F p 0/5 |  | inf-2 |  | BW-105 (EliteNote 840 G2, launched 2015) passes at £126.49 with a stick (truth: the stick does not go in a 201 |
| spice-pitch-deck-qa | 1.0.0 | P3 | 0/5 | 0/5 | A p 0/5; F p 0/5 |  | st-v1 |  | applies handbook 4.2 as written to the Design Direction slide NV-10, whose title and asset labels call the kit |
| station-register-consolidation | 1.0.0 | P1 | 0/5 | 0/5 | A p 0/5; F p 0/5 |  | st-v1 |  | reads Garmsar's Table 1-1 as data rows and never applies its footnote, so the two starred stations (47-017, 47 |
| timesheet-overtime-review | 1.0.0 | P3 | 0/5 | 0/5 | A p 0/5; F p 0/5 |  | st-v1 |  | takes the required leave time as start + 8 h 30 (her Monday notes show no break), as the trace's assistant did |

### Q.scale: Unit / scale / number format (thousands, raw marks, h.mm, inches)

| task | ver | P | F | A | stages | verdict | S/I | re | misreading |
|---|---|---|---|---|---|---|---|---|---|
| ats-embedded-screening-register | 1.0.0 | P3 | 0/5 | - | F p 0/5 |  | inf-3 |  | records the test centre's raw marks as per cent: C-303 90.0, C-304 84.0, C-306 93.0 instead of 75.0, 70.0 and  |
| ats-embedded-screening-register | 1.1.0 | P3 | 0/15 | 0/15 | A f 0/10; p 0/5; F f 0/10; p 0/5 |  | inf-3 |  | records the test centre's raw marks as per cent: C-303 90.0, C-304 84.0, C-306 93.0 instead of 75.0, 70.0 and  |
| ats-embedded-screening-register | 1.2.0 | P3 | 0/5 | - | F p 0/5 |  | inf-3 |  | records the test centre's raw marks as per cent: C-303 90.0, C-304 84.0, C-306 93.0 instead of 75.0, 70.0 and  |
| ats-embedded-screening-register | 1.3.0 | P3 | 0/5 | - | F p 0/5 |  | inf-3 |  | records the test centre's raw marks as per cent: C-303 90.0, C-304 84.0, C-306 93.0 instead of 75.0, 70.0 and  |
| ats-embedded-screening-register | 1.4.0 | P3 | 0/5 | - | F p 0/5 |  | inf-3 |  | records the test centre's raw marks as per cent: C-303 90.0, C-304 84.0, C-306 93.0 instead of 75.0, 70.0 and  |
| blockprint-winter-close | 1.2.0 | P2 | 0/5 | 0/5 | A p 0/5; F p 0/5 |  | inf-2 |  | transport 372.70 (tolls 27.60 plus the export's winter fill-ups 345.10 as printed) instead of 441.72 (27.60 +  |
| coloring-book-retitle-audit | 2.0.0 | P1 | 0/5 | - | F p 0/5 |  | inf-3 |  | takes the requested 300 dpi for both placed PNGs; the test color page was left at the illustrator's 400 ppi ma |
| coloring-book-retitle-audit | 2.1.0 | P1 | 0/5 | - | F p 0/5 |  | inf-3 |  | takes the bare insets as inches; the name plate's frame lines up with the tea party page (D01, 0.44 in) only a |
| coloring-book-retitle-audit | 2.2.0 | P1 | 0/15 | 0/15 | A f 0/10; p 0/5; F f 0/10; p 0/5 |  | inf-4 |  | reads the export-note insets as page insets; they are measured on the 9 in canvas and both images are scaled t |
| coloring-book-retitle-audit | 2.3.0 | P1 | 0/15 | 0/15 | A f 0/10; p 0/5; F f 0/10; p 0/5 |  | inf-4 |  | reads the export-note insets as page insets; they are measured on the 9 in canvas and both images are scaled t |
| coloring-book-retitle-audit | 2.4.0 | P1 | 0/5 | - | F p 0/5 |  | inf-4 |  | reads the export-note insets as page insets; they are measured on the 9 in canvas and both images are scaled t |
| coloring-book-retitle-audit | 2.5.0 | P1 | 0/15 | - | F f 0/10; p 0/5 |  | inf-4 |  | reads the export-note insets as page insets; they are measured on the 9 in canvas and both images are scaled t |
| coloring-book-retitle-audit | 2.6.0 | P1 | 0/5 | - | F p 0/5 |  | inf-4 |  | reads the export-note insets as page insets; they are measured on the 9 in canvas and both images are scaled t |
| coop-bp-prefill-sheet | 1.0.0 | P4 | 0/5 | - | F p 0/5 |  | inf-2 |  | Tagadirt's monthly fixed costs 8 568 instead of 714 (8 160 / 12 = 680, plus 34) |
| coop-bp-prefill-sheet | 1.1.0 | P4 | 0/5 | 0/5 | A p 0/5; F p 0/5 |  | inf-3 |  | Tagadirt's monthly fixed costs 4 410 instead of 1 470 (4 200 / 3 = 1 400, plus 70) |
| current-affairs-booklet-plan | 1.1.0 | P3 | 0/5 | - | F p 0/5 |  | inf-2 |  | prints the Kesarganj mela at 92.3 lakh instead of 0.9 (92.3 thousand = 0.923 lakh) |
| current-affairs-booklet-plan | 1.2.0 | P3 | 0/5 | 0/5 | A p 0/5; F p 0/5 |  | inf-2 |  | prints the Kesarganj mela at 92.3 lakh instead of 0.9 (92.3 thousand = 0.923 lakh) |
| deck-preread-review | 2.4.0 | P1 | 0/5 | 0/5 | A p 0/5; F p 0/5 |  | inf-4 |  | 175,000 read as birr: S-16 9.5 and S-20 1.7 (9.6 / 1.8 half up) instead of S-16 5.6 and S-20 3.3 (3.4 half up; |
| deck-preread-review | 2.5.0 | P1 | 0/15 | 0/15 | A f 0/10; p 0/5; F f 0/10; p 0/5 |  | inf-4 |  | 175,000 read as birr: S-16 9.5 and S-20 1.7 (9.6 / 1.8 half up) instead of S-16 5.6 and S-20 3.3 (3.4 half up; |
| deck-preread-review | 2.6.0 | P1 | 0/5 | 0/5 | A p 0/5; F p 0/5 |  | inf-4 |  | 175,000 read as birr: S-16 9.5 and S-20 1.7 (9.6 / 1.8 half up) instead of S-16 5.6 and S-20 3.3 (3.4 half up; |
| deck-preread-review | 2.7.0 | P1 | 0/5 | 0/5 | A p 0/5; F p 0/5 |  | inf-6 |  | 175,000 read as birr: S-16 9.5 and S-20 1.7 (9.6 / 1.8 half up) instead of S-16 5.6 and S-20 3.3 (3.4 half up; |
| ethics-report-mark-release | 1.0.0 | P3 | 0/5 | - | F p 0/5 |  | inf-3 |  | content_mark 28 instead of 70. The gradebook item holds each mark's contribution to the unit (out of A2's 40%  |
| ethics-report-mark-release | 1.1.0 | P3 | 0/5 | 0/5 | A p 0/5; F p 0/5 |  | inf-3 |  | content_mark 26 instead of 65. The gradebook item holds each mark's contribution to the unit (out of A2's 40%  |
| kibo-budget-cap-review | 2.0.0 | P1 | 0/5 | - | F p 0/5 |  | inf-2 |  | prices the four Sunday cards at 1.15, 1.10, 1.05 and 2.40 USD instead of 0.23, 0.22, 0.21 and 0.48: nonland 38 |
| kibo-budget-cap-review | 2.1.0 | P1 | 0/5 | - | F p 0/5 |  | inf-2 |  | prices the four Sunday cards at 1.15, 1.10, 1.05 and 2.40 USD instead of 0.23, 0.22, 0.21 and 0.48: nonland 38 |
| kibo-budget-cap-review | 2.2.0 | P1 | 0/5 | - | F p 0/5 |  | inf-2 |  | prices the four Sunday cards at 1.15, 1.10, 1.05 and 2.40 USD instead of 0.23, 0.22, 0.21 and 0.48: nonland 38 |
| kibo-budget-cap-review | 2.3.0 | P1 | 0/15 | 0/15 | A f 0/10; p 0/5; F f 0/10; p 0/5 |  | inf-2 |  | prices the four Sunday cards at 1.15, 1.10, 1.05 and 2.40 USD instead of 0.23, 0.22, 0.21 and 0.48: nonland 38 |
| kibo-budget-cap-review | 2.3.1 | P1 | 0/15 | 0/15 | A f 0/10; p 0/5; F f 0/10; p 0/5 |  | inf-2 |  | prices the four Sunday cards at 1.15, 1.10, 1.05 and 2.40 USD instead of 0.23, 0.22, 0.21 and 0.48: nonland 38 |
| kibo-budget-cap-review | 2.4.0 | P1 | 0/5 | 0/5 | A p 0/5; F p 0/5 |  | inf-3 |  | prices the four Sunday cards at the levy-inclusive 0.24, 0.30, 0.36 and 1.38 USD instead of the listing prices |
| kibo-budget-cap-review | 2.5.0 | P1 | 0/5 | - | F p 0/5 |  | inf-2 |  | prices the four Sunday cards at 1.15, 1.10, 1.05 and 2.40 USD instead of 0.23, 0.22, 0.21 and 0.48: nonland 38 |
| kibo-budget-cap-review | 2.6.0 | P1 | 0/5 | - | F p 0/5 |  | inf-2 |  | prices the four Sunday cards at 1.15, 1.10, 1.05 and 2.40 USD instead of 0.23, 0.22, 0.21 and 0.48: nonland 38 |
| kibo-budget-cap-review | 2.7.0 | P1 | 1/5 | - | F p 1/5 |  | inf-2 |  | prices the four Sunday cards at 1.15, 1.10, 1.05 and 2.40 USD instead of 0.23, 0.22, 0.21 and 0.48: nonland 38 |
| killzone-journal-review | 1.1.0 | P3 | 0/5 | 0/5 | A p 0/5; F p 0/5 |  | inf-4 |  | euro trades of 26 Oct onwards read as dollars: 61810988 2.0 (not 2.3), 61812205 0.5 (0.6), 61814016 0.8 (0.9), |
| line-colour-census | 1.0.0 | P3 | 0/15 | 0/15 | A f 0/10; p 0/5; F f 0/10; p 0/5 |  | inf-3 |  | Westport's H is printed in per cent of a full turn: the infirmary line (58) is the sky-blue hospital line, the |
| melody-lesson-results | 1.0.0 | P3 | 4/5 | 0/5 | A p 0/5; F p 4/5 | AMBIGUOUS | inf-3 |  | writes each pre-test percentage out of 10 (Mika 5 -> 50) instead of out of the 20-item division diagnostic (25 |
| melody-lesson-results | 1.1.0 | P3 | 12/15 | 0/15 | A f 0/10; p 0/5; F f 8/10; p 4/5 | AMBIGUOUS | inf-3 |  | writes each pre-test percentage out of 10 (Mika 5 -> 50) instead of out of the 20-item division diagnostic (25 |
| melody-lesson-results | 1.2.0 | P3 | 0/5 | 0/5 | A p 0/5; F p 0/5 |  | inf-3 |  | writes each pre-test percentage out of 10 (Mika 5 -> 50) instead of out of the 20-item division diagnostic (25 |
| niche-shelving-screen | 1.0.0 | P1 | 0/5 | 0/5 | A p 0/5; F p 0/5 |  | inf-4 |  | reads the importer's bare figures as centimetres, so the pole shelf NG-0415 (15 x 7.5, 84-104) fails test 4 as |
| niche-shelving-screen | 1.1.0 | P1 | 15/15 | 15/15 | A f 10/10; p 5/5; F f 10/10; p 5/5 | AMBIGUOUS | inf-3 |  | reads the importer's bare sizes as centimetres, so the tiered shelf NG-0415 is excluded for height (95.5 cm) i |
| niche-shelving-screen | 1.3.0 | P1 | 0/5 | 4/5 | A p 4/5; F p 0/5 |  | inf-3 |  | reads the importer's bare sizes as centimetres, so the tiered shelf NG-0415 is excluded for height (95.5 cm) i |
| okra-manuscript-revision | 2.0.0 | P1 | 0/5 | - | F p 0/5 |  | inf-2 |  | converts on the printed bed area (6.75 m2), so every q/ha (and every main-effect mean) is half the true value: |
| okra-manuscript-revision | 2.1.0 | P1 | 0/5 | - | F p 0/5 |  | inf-2 |  | converts on the printed bed area (6.75 m2), so every q/ha (and every main-effect mean) is half the true value, |
| okra-manuscript-revision | 2.2.0 | P1 | 0/5 | 0/5 | A p 0/5; F p 0/5 |  | inf-2 |  | converts on the printed bed area (6.75 m2), so every q/ha (and every main-effect mean) is half the true value  |
| okra-manuscript-revision | 2.2.0 | P12 | 0/5 | 0/5 | A p 0/5; F p 0/5 |  | inf-2 |  | on the printed bed area every revised yield is half the true value, so the seven combinations not touched by t |
| okra-manuscript-revision | 2.2.0 | P2 | 0/5 | 0/5 | A p 0/5; F p 0/5 |  | inf-2 |  | divides every plot mean by the printed 52 plants of the whole bed instead of the 26 in the two centre rows, so |
| pathway-choice-audit | 2.1.0 | P7 | 0/5 | 0/5 | A p 0/5; F p 0/5 |  | inf-3 |  | invites G9-002 (35), G9-003 (29), G9-004 (24), G9-005 (38) and G9-007 (33) instead of G9-003 and G9-004; on a  |
| posting-month-close | 1.0.0 | P4 | 0/5 | - | F p 0/5 |  | inf-2 |  | values the three September Fiverr orders at 76, 52 and 116 (the Earnings-page figures) instead of 95, 65 and 1 |
| posting-month-close | 1.1.0 | P4 | 0/5 | - | F p 0/5 |  | inf-3 |  | values the three September Fiverr orders at 60, 40 and 120 (the Earnings-page figures) instead of 75, 50 and 1 |
| posting-month-close | 1.2.0 | P4 | 0/5 | 0/5 | A p 0/5; F p 0/5 |  | inf-3 |  | values the three September Fiverr orders at 60, 40 and 120 (the Earnings-page figures) instead of 75, 50 and 1 |
| profile-copy-claims-audit | 2.2.0 | P7 | 15/15 | 0/15 | A f 0/10; p 0/5; F f 10/10; p 5/5 | AMBIGUOUS | inf-3 |  | reads Podwave's season-one figures as plain plays (146 in all) instead of thousands (146,000): podcast_views 3 |
| profile-copy-claims-audit | 2.3.0 | P7 | 15/15 | 0/15 | A f 0/10; p 0/5; F f 10/10; p 5/5 | AMBIGUOUS | inf-3 |  | reads Podwave's season-one figures as plain plays (146 in all) instead of thousands (146,000): podcast_views 3 |
| profile-copy-claims-audit | 2.4.0 | P7 | 15/15 | 0/15 | A f 0/10; p 0/5; F f 10/10; p 5/5 | GENUINE | inf-3 |  | reads Podwave's season-one figures as plain plays (146 in all) instead of thousands (146,000): podcast_views 3 |
| profile-copy-claims-audit | 2.5.0 | P7 | 4/5 | 0/5 | A p 0/5; F p 4/5 |  | inf-4 |  | reads Podwave's season-one figures as plain plays (146 in all) instead of thousands (146,000): podcast_views 3 |
| profile-copy-claims-audit | 2.6.0 | P7 | 3/5 | 0/5 | A p 0/5; F p 3/5 |  | inf-4 |  | reads Podwave's season-one figures as plain plays (146 in all) instead of thousands (146,000): podcast_views 3 |
| profile-copy-claims-audit | 2.7.0 | P7 | 4/5 | 0/5 | A p 0/5; F p 4/5 |  | inf-4 |  | reads Podwave's season-one figures as plain plays (146 in all) instead of thousands (146,000): podcast_views 3 |
| profile-copy-claims-audit | 2.8.0 | P7 | 1/5 | 0/5 | A p 0/5; F p 1/5 |  | inf-6 |  | reads Podwave's season-one figures as plain plays (146 in all) instead of thousands (146,000): podcast_views 3 |
| sandwich-image-audit | 1.0.0 | P5 | 0/5 | - | F p 0/5 |  | inf-3 |  | ZK-220 counts as covered and its file is kept |
| sandwich-image-audit | 1.2.0 | P1 | 0/5 | - | F p 0/5 |  | inf-3 |  | SI megabyte: ZK-215 needs_photo and its file left out of download_register (binary megabyte instead: ZK-220 in |
| sandwich-image-audit | 1.3.0 | P1 | 0/5 | 0/5 | A p 0/5; F p 0/5 |  | inf-3 |  | SI megabyte: ZK-215 needs_photo and its file left out of download_register |
| spice-pitch-deck-qa | 2.3.0 | P5 | 0/5 | 0/5 | A p 0/5; F p 0/5 |  | inf-3 |  | ₹10,50,000 (840 effort units priced as hours) instead of ₹84,00,000: 4 people full-time for a 10-month build i |
| timesheet-overtime-review | 2.1.0 | P1 | 0/5 | - | F p 0/5 |  | inf-5 |  | reads Rana's Monday 'Hours Inside' 11.14 as decimal hours (11 h 08 min 24 s), so the raw overtime is 7704 s in |
| timesheet-overtime-review | 2.2.0 | P1 | 0/15 | 0/15 | A f 0/10; p 0/5; F f 0/10; p 0/5 |  | inf-5 |  | reads Rana's Monday 'Hours Inside' 11.04 as decimal hours (11 h 02 min 24 s), so the raw overtime is 7344 s in |
| timesheet-overtime-review | 2.3.0 | P1 | 0/5 | 0/5 | A p 0/5; F p 0/5 |  | inf-6 |  | reads Rana's Monday 'Hours Inside' 11.04 as decimal hours (11 h 02 min 24 s), so the raw overtime is 7344 s in |
| timesheet-overtime-review | 2.4.0 | P1 | 0/15 | - | F f 0/10; p 0/5 |  | inf-5 |  | reads Rana's Monday 'Hours Inside' 11.04 as decimal hours (11 h 02 min 24 s), so the raw overtime is 7344 s in |
| timesheet-overtime-review | 2.5.0 | P1 | 0/5 | - | F p 0/5 |  | inf-5 |  | reads Rana's Monday 'Hours Inside' 11.04 as decimal hours (11 h 02 min 24 s), so the raw overtime is 7344 s in |
| timesheet-overtime-review | 2.6.0 | P1 | 0/5 | - | F p 0/5 |  | inf-5 |  | reads Rana's Monday 'Hours Inside' 11.04 as decimal hours (11 h 02 min 24 s), so the raw overtime is 7344 s in |

### T.changed: Changed premise mid-stream invalidates an earlier status

| task | ver | P | F | A | stages | verdict | S/I | re | misreading |
|---|---|---|---|---|---|---|---|---|---|
| cafe-kitchen-schedule-revisions | 1.0.0 | P4 | 0/5 | 0/5 | A p 0/5; F p 0/5 |  | st-v1 |  | carries the rev 0 BOQ quantities into rev 1 (or recounts hinges over every front of the fronts table, which ha |
| cafe-kitchen-schedule-revisions | 1.0.0 | P7 | 0/5 | 0/5 | A p 0/5; F p 0/5 |  | st-v1 |  | lowers only the worktops and re-issues the C-03 wall-element heights as listed (computed on the 90 cm worktop) |
| cafe-kitchen-schedule-revisions | 2.0.0 | P4 | 0/5 | - | F p 0/5 |  | inf-3 |  | keeps the 100 cm clear distance to the room door's leaf for C4 and D8, so C4 (and D8 under edition 4) fail cle |
| cafe-kitchen-schedule-revisions | 2.1.0 | P8 | 4/15 | 0/15 | A f 0/10; p 0/5; F f 3/10; p 1/5 | GENUINE | inf-2 |  | keeps the 90 cm clear distance to the room door's leaf: C4 and D8 fail clearance in rev 1; with the door openi |
| cafe-kitchen-schedule-revisions | 2.1.1 | P8 | 3/15 | 0/15 | A f 0/10; p 0/5; F f 2/10; p 1/5 | GENUINE | inf-2 |  | keeps the 90 cm clear distance to the room door's leaf: C4 and D8 fail clearance in rev 1; with the door openi |
| cafe-kitchen-schedule-revisions | 2.2.0 | P8 | 3/5 | - | F p 3/5 |  | inf-2 |  | keeps the 90 cm clear distance to the room door's leaf: C4 and D8 fail clearance in rev 1; with the door openi |
| cafe-kitchen-schedule-revisions | 2.3.0 | P8 | 2/15 | - | F f 2/10; p 0/5 | BLIND-1.0 | inf-2 |  | keeps the 90 cm clear distance to the room door's leaf: C4 and D8 fail clearance in rev 1; with the door openi |
| cnc-router-bom-reconcile | 1.0.0 | P3 | 0/5 | 0/5 | A p 0/5; F p 0/5 |  | st-v1 |  | keeps the dual-Y result already worked out (A cloned to Y, as the desk's own first reply in the chat had it):  |
| cnc-router-bom-reconcile | 2.0.0 | P3 | 0/5 | - | F p 0/5 |  | inf-3 |  | keeps one coupler per motor (4) although the rotary headstock motor's 5 mm shaft enters the chuck's 5 mm hub d |
| cnc-router-bom-reconcile | 2.1.0 | P3 | 0/5 | - | F p 0/5 |  | inf-3 |  | keeps one coupler per motor (4) although the rotary headstock motor's 5 mm shaft enters the chuck's 5 mm hub d |
| cnc-router-bom-reconcile | 2.2.0 | P3 | 0/5 | - | F p 0/5 |  | inf-3 |  | keeps one coupler per motor (4) although the rotary headstock motor's 5 mm shaft enters the chuck's 5 mm hub d |
| coloring-book-retitle-audit | 1.0.0 | P4 | 0/5 | 0/5 | A p 0/5; F p 0/5 |  | st-v1 |  | keeps the verdicts the v1.1 boxes earned under the old title, so box 4 ('comfy cottagecore art for women') and |
| coloring-book-retitle-audit | 2.0.0 | P5 | 0/5 | - | F p 0/5 |  | inf-2 |  | leaves out page 3: the hand-off says the front page other than the swatch sheet (the brief ties the swatch she |
| eco-guard-errata-review | 1.0.0 | P4 | 0/5 | 0/5 | A p 0/5; F p 0/5 |  | st-v1 |  | keeps the appendix update w = 0.5400, which was worked out with the gradient before v3 added the sigmoid slope |
| eco-guard-errata-review | 2.0.0 | P1 | 0/5 | - | F p 0/5 |  | inf-3 |  | fills the large-step A.3 loss from the latest export row (the 10 October re-run of the notebook as issued, gra |
| eco-guard-errata-review | 2.1.0 | P1 | 0/5 | - | F p 0/5 |  | inf-3 |  | fills the large-step A.3 loss from the latest export row (the 10 October re-run of the notebook as issued, gra |
| eco-guard-errata-review | 2.2.0 | P1 | 0/5 | - | F p 0/5 |  | inf-3 |  | fills the large-step A.3 loss from the latest export row (the 10 October re-run of the notebook as issued, gra |
| feast-sharing-runsheet | 1.0.0 | P1 | 0/5 | - | F p 0/5 |  | inf-3 |  | names the roster's facilitator, Sr. Clara Ningsih, for the Year 8 class she has asked Br. Yosef to take while  |
| feast-sharing-runsheet | 1.1.0 | P1 | 0/5 | - | F p 0/5 |  | inf-3 |  | names the roster's facilitator, Sr. Clara Ningsih, for the Year 8 class she has asked Br. Yosef to take while  |
| hammamet-voucher-reissue | 1.0.0 | P4 | 0/5 | 0/5 | A p 0/5; F p 0/5 |  | st-v1 |  | keeps the voucher's printed 10/09-17/09 (7 nights) for room 2: departure 17/09/2026, 7 nights and 7 nights of  |
| kibo-budget-cap-review | 1.0.0 | P2 | 0/5 | 0/5 | A p 0/5; F p 0/5 |  | st-v1 |  | keeps the single-card ceiling at the method's 10% of the cap (2.50 USD), as the working notes already computed |
| kibo-budget-cap-review | 2.0.0 | P3 | 0/5 | - | F p 0/5 |  | inf-2 |  | prices three lands at their cheaper Japanese printings (Kessig Wolf Run 0.80, Cinder Glade 1.05, Karplusan For |
| kibo-budget-cap-review | 2.1.0 | P3 | 0/5 | - | F p 0/5 |  | inf-2 |  | prices three lands at their cheaper Japanese printings (Kessig Wolf Run 0.80, Cinder Glade 1.05, Karplusan For |
| kibo-budget-cap-review | 2.2.0 | P3 | 0/5 | - | F p 0/5 |  | inf-2 |  | prices three lands at their cheaper Japanese printings (Kessig Wolf Run 0.80, Cinder Glade 1.05, Karplusan For |
| manhole-excavation-valuation | 1.0.0 | P2 | 0/5 | - | F p 0/5 |  | inf-2 |  | A07 measured as a 1.00 m chamber (pit 2.00 m): 9.77 instead of 12.26 (pit 2.24 m) |
| manhole-excavation-valuation | 1.1.0 | P2 | 0/5 | - | F p 0/5 |  | inf-2 |  | A07 measured as a 1.00 m chamber (pit 2.00 m): 9.77 instead of 12.26 (pit 2.24 m) |
| manhole-excavation-valuation | 1.2.0 | P2 | 0/5 | 0/5 | A p 0/5; F p 0/5 |  | inf-2 |  | A07 measured as a 1.00 m chamber (pit 2.00 m): 9.77 instead of 12.26 (pit 2.24 m) |
| moisturiser-price-screen | 1.0.0 | P4 | 0/5 | 0/5 | A p 0/5; F p 0/5 |  | st-v1 |  | keeps the requirement-4 judgement made for cheeks and forehead (as the earlier draft did), so BN-2102 (caution |
| moisturiser-price-screen | 2.0.0 | P1 | 0/5 | - | F p 0/5 |  | inf-2 |  | judges label cautions against cheeks and forehead: BN-2102 (avoid lips, mouth, chin) and BN-2116 (cheeks, fore |
| moisturiser-price-screen | 2.1.0 | P1 | 0/5 | - | F p 0/5 |  | inf-2 |  | judges label cautions against cheeks and forehead: BN-2102 (avoid lips, mouth, chin) and BN-2116 (cheeks, fore |
| moisturiser-price-screen | 2.2.0 | P1 | 0/15 | 0/15 | A f 0/10; p 0/5; F f 0/10; p 0/5 |  | inf-2 |  | judges label cautions against cheeks and forehead: BN-2102 (avoid lips, mouth, chin) and BN-2116 (cheeks, fore |
| moot-issue3-memorial-audit | 1.0.0 | P7 | 0/5 | 0/5 | A p 0/5; F p 0/5 |  | st-v1 |  | audits v3 against the 8 September structure sheet (three arguments, two sub-arguments each): reports 3.3.2 mis |
| mustangs-tryout-roster | 1.0.0 | P4 | 0/5 | 0/5 | A p 0/5; F p 0/5 |  | st-v1 |  | keeps the step-1 roster after the series becomes travel-only: the two cleared house-only registrants (MU-109,  |
| mustangs-tryout-roster | 1.0.0 | P5 | 0/5 | 0/5 | A p 0/5; F p 0/5 |  | st-v1 |  | plans the second session on the old Friday 18 September availability (or carries the step-1 sheet over): the t |
| mustangs-tryout-roster | 1.0.0 | P8 | 0/5 | 0/5 | A p 0/5; F p 0/5 |  | st-v1 |  | keeps the Sunday plan of the 5:30 pm slot (the step-2 sheet in /app/deliverables): MU-116 (gets to the field a |
| niche-shelving-screen | 1.0.0 | P2 | 0/5 | 0/5 | A p 0/5; F p 0/5 |  | inf-3 |  | keeps the draft's pass for the Railo upright kit RL-0200 (code FW) and lets the two-leg Klampa frame KL-0402 ( |
| okra-manuscript-revision | 1.0.0 | P5 | 0/5 | 0/5 | A p 0/5; F p 0/5 |  | st-v1 |  | keeps the cost of cultivation printed in Table 4 (and carried in draft v2), which was built at the old yields, |
| pathway-choice-audit | 1.0.0 | P5 | 0/5 | 0/5 | A p 0/5; F p 0/5 |  | st-v1 |  | validates S05 (ST2096) and S11 (ST2010) against the printed STEM list, where both are listed, and keeps them a |
| station-register-consolidation | 2.0.0 | P4 | 0/5 | - | F p 0/5 |  | inf-4 |  | keeps Garmsar's meteorological status from Table 1-1 and its footnote alone: 47-020 (2283 m) and 47-022 (2321  |
| student-laptop-shortlist | 1.0.0 | P2 | 0/5 | 0/5 | A p 0/5; F p 0/5 |  | st-v1 |  | screens on the first brief's '512 GB SSD minimum', as the draft did, so L-402 stays shortlisted (instead of fa |
| student-laptop-shortlist | 2.0.0 | P5 | 0/5 | - | F p 0/5 |  | inf-2 |  | screens on 512 GB: L-402 shortlisted instead of failing storage, L-410 67,491 without its in-order upgrade ins |
| student-laptop-shortlist | 2.1.0 | P5 | 0/5 | - | F p 0/5 |  | inf-2 |  | screens on 512 GB: L-402 shortlisted instead of failing storage, L-410 67,491 without its in-order upgrade ins |
| student-laptop-shortlist | 2.2.0 | P5 | 0/5 | 0/5 | A p 0/5; F p 0/5 |  | inf-2 |  | screens on 512 GB: L-402 shortlisted instead of failing storage, L-410 67,491 without its in-order upgrade ins |
| timesheet-overtime-review | 1.0.0 | P2 | 0/5 | 0/5 | A p 0/5; F p 0/5 |  | st-v1 |  | keeps the Thursday roster's 12:30 start for Monday (handbook 3.2: starting work early does not move the day) a |

### ID.twin: Near-twin identities (namesakes, same-titled items; false merge/split)

| task | ver | P | F | A | stages | verdict | S/I | re | misreading |
|---|---|---|---|---|---|---|---|---|---|
| billiard-shift-audit | 1.0.0 | P2 | 0/5 | 0/5 | A p 0/5; F p 0/5 |  | st-v1 |  | prices bar lines by their printed name, first matching menu row: line ЧЛ-05 'Эрл Грей' at the bagged 90 instea |
| brightwater-spec-qa | 1.0.0 | P1 | 0/5 | 0/5 | A p 0/5; F p 0/5 |  | st-v1 |  | (premise text not preserved; family from the signal_gate output) |
| cnc-router-bom-reconcile | 1.0.0 | P2 | 0/5 | 0/5 | A p 0/5; F p 0/5 |  | st-v1 |  | keeps the v1 3,0 mm endmill (EM-3000): treats 'mini grinder Kenzo' as a name change, never resolving it to the |
| coloring-book-retitle-audit | 2.0.0 | P7 | 0/5 | - | F p 0/5 |  | inf-3 |  | applies the 2026-09-01 cancellation to the class 16 WITCHY LIFE record and marks T2 CLEAR; the export of 2026- |
| coloring-book-retitle-audit | 2.1.0 | P9 | 0/5 | - | F p 0/5 |  | inf-3 |  | applies the 2026-09-01 cancellation to the class 16 WITCHY LIFE record and marks T2 CLEAR (secondary premise,  |
| council-video-index | 1.0.0 | P3 | 0/5 | - | F p 0/5 |  | inf-2 |  | gives the session's one budget resolution to the first of the two identically titled budget items; it belongs  |
| melody-lesson-results | 1.0.0 | P2 | 0/5 | 0/5 | A p 0/5; F p 0/5 |  | inf-3 |  | a false merge: gives pupil 13 (Angel Reyes) the make-up tally's 6, although she was in Tagbilaran from Saturda |
| moisturiser-price-screen | 1.0.0 | P5 | 0/5 | 0/5 | A p 0/5; F p 0/5 |  | st-v1 |  | joins the label sheet to the listings on the barcode text as printed, so the 14-digit GTIN row matches no list |
| moisturiser-price-screen | 2.0.0 | P3 | 0/5 | - | F p 0/5 |  | inf-2 |  | treats BN-2107 (the Mashhad partner's jar, printing the genuine barcode) as the declared product and lists it  |
| moisturiser-price-screen | 2.1.0 | P3 | 0/5 | - | F p 0/5 |  | inf-2 |  | treats BN-2107 (the Mashhad partner's jar, printing the genuine barcode) as the declared product and lists it  |
| moisturiser-price-screen | 2.2.0 | P3 | 0/15 | 0/15 | A f 0/10; p 0/5; F f 0/10; p 0/5 |  | inf-2 |  | treats BN-2107 (the Mashhad partner's jar, printing the genuine barcode) as the declared product and lists it  |
| moisturiser-price-screen | 2.3.0 | P3 | 0/5 | 0/5 | A p 0/5; F p 0/5 |  | inf-2 |  | treats BN-2107 (the Mashhad partner's jar, printing the genuine barcode) as the declared product and lists it  |
| moot-issue3-memorial-audit | 1.0.0 | P6 | 0/5 | 0/5 | A p 0/5; F p 0/5 |  | st-v1 |  | treats both Tribunals Bar Association judgments as one and checks every pinpoint in the 2025 judgment: accepts |
| moot-issue3-memorial-audit | 2.0.0 | P5 | 0/5 | - | F p 0/5 |  | inf-4 |  | confirms fn 10, reading it against the 2025 judgment, though its supra note leads to the 2021 judgment, which  |
| moot-issue3-memorial-audit | 2.0.0 | P7 | 0/5 | - | F p 0/5 |  | inf-3 |  | treats the 2021 Tribunals Bar Association judgment as the index's 2025 entry of the same name and adds nothing |
| moot-issue3-memorial-audit | 2.0.0 | P8 | 0/5 | - | F p 0/5 |  | inf-3 |  | treats the 2023 Himgiri judgment as the index's Northern Hydro entry (a 2019 judgment against the Union, liste |
| moot-issue3-memorial-audit | 2.1.0 | P5 | 0/5 | 0/5 | A p 0/5; F p 0/5 |  | inf-4 |  | confirms fn 10, reading it against the 2025 judgment, though its supra note leads to the 2021 judgment, which  |
| moot-issue3-memorial-audit | 2.1.0 | P7 | 0/5 | 0/5 | A p 0/5; F p 0/5 |  | inf-3 |  | treats the 2021 Tribunals Bar Association judgment as the index's 2025 entry of the same name and adds nothing |
| moot-issue3-memorial-audit | 2.1.0 | P8 | 0/5 | 0/5 | A p 0/5; F p 0/5 |  | inf-3 |  | treats the 2023 Himgiri judgment as the index's Northern Hydro entry (a 2019 judgment against the Union, liste |
| moot-issue3-memorial-audit | 2.2.0 | P5 | 0/5 | 0/5 | A p 0/5; F p 0/5 |  | inf-4 |  | confirms fn 10, reading it against the 2025 judgment, though its supra note leads to the 2021 judgment, which  |
| moot-issue3-memorial-audit | 2.2.0 | P7 | 0/5 | 0/5 | A p 0/5; F p 0/5 |  | inf-3 |  | treats the 2021 Tribunals Bar Association judgment as the index's 2025 entry of the same name and adds nothing |
| moot-issue3-memorial-audit | 2.2.0 | P8 | 0/5 | 0/5 | A p 0/5; F p 0/5 |  | inf-3 |  | treats the 2023 Himgiri judgment as the index's Northern Hydro entry (a 2019 judgment against the Union, liste |
| mustangs-tryout-roster | 1.0.0 | P3 | 0/5 | 0/5 | A p 0/5; F p 0/5 |  | st-v1 |  | counts every registration as a child (or de-duplicates on the exact name): 'Jaxon Pirelli' (MU-106, mother's f |
| mustangs-tryout-roster | 2.0.0 | P2 | 0/5 | - | F p 0/5 |  | inf-2 |  | false merge of two cousins named for their grandfather: MU-107 cleared on his cousin's certificate, MU-113 voi |
| mustangs-tryout-roster | 2.0.0 | P4 | 0/5 | - | F p 0/5 |  | inf-2 | re | re-merges the cousins in the fresh step: MU-107 (Both, 'No Sundays (travel soccer)') on the roster, off sessio |
| mustangs-tryout-roster | 2.0.0 | P9 | 0/5 | - | F p 0/5 |  | inf-2 | re | re-merges the cousins: MU-113 missing from sunday_attendance, MU-107 noticed |
| mustangs-tryout-roster | 2.1.0 | P2 | 0/5 | 0/5 | A p 0/5; F p 0/5 | BLIND-1.0 | inf-2 |  | false merge of two cousins named for their grandfather: MU-107 cleared on his cousin's certificate, MU-113 voi |
| mustangs-tryout-roster | 2.1.0 | P4 | 0/5 | 0/5 | A p 0/5; F p 0/5 |  | inf-2 | re | re-merges the cousins in the fresh step: MU-107 (Both, 'No Sundays (travel soccer)') on the roster, off sessio |
| mustangs-tryout-roster | 2.1.0 | P9 | 0/5 | 0/5 | A p 0/5; F p 0/5 |  | inf-2 | re | re-merges the cousins: MU-113 missing from sunday_attendance, MU-107 noticed |
| mustangs-tryout-roster | 2.2.0 | P2 | 0/5 | 0/5 | A p 0/5; F p 0/5 |  | inf-2 |  | false merge of two cousins named for their grandfather: MU-107 cleared on his cousin's certificate, MU-113 voi |
| mustangs-tryout-roster | 2.2.0 | P4 | 0/5 | 0/5 | A p 0/5; F p 0/5 |  | inf-2 | re | re-merges the cousins in the fresh step: MU-107 (Both, 'No Sundays (travel soccer)') on the roster, off sessio |
| okra-manuscript-revision | 1.0.0 | P1 | 0/5 | 0/5 | A p 0/5; F p 0/5 |  | st-v1 |  | keys paper 2 on the upload named 'okra paper 2' (a byte-identical copy of paper 1, manuscript PA-25-0871) and  |
| psychopathy-evidence-screen | 1.0.0 | P3 | 0/5 | 0/5 | A p 0/5; F p 0/5 |  | st-v1 |  | identifies a study by first author and year instead of dataset_id: Lindqvist-Hart 2021 (R13) and Hart 2022 (R1 |
| psychopathy-evidence-screen | 2.0.0 | P2 | 0/5 | - | F p 0/5 |  | inf-3 |  | identifies a sample by its dataset label: R13 (2021) is coded X3 as an earlier report of R14 (2022); with P1 r |
| psychopathy-evidence-screen | 2.1.0 | P2 | 0/5 | - | F p 0/5 |  | inf-3 |  | identifies a sample by its dataset label: R13 (2021) is coded X3 as an earlier report of R14 (2022); with P1 r |
| psychopathy-evidence-screen | 2.2.0 | P2 | 0/5 | - | F p 0/5 |  | inf-3 |  | identifies a sample by its dataset label: R13 (2021) is coded X3 as an earlier report of R14 (2022); with P1 r |
| psychopathy-evidence-screen | 2.3.0 | P2 | 0/15 | 1/15 | A f 1/10; p 0/5; F f 0/10; p 0/5 |  | inf-3 |  | identifies a sample by its dataset label: R13 (2021) is coded X3 as an earlier report of R14 (2022); with P1 r |
| pupil-tracker-term-summary | 1.0.0 | P2 | 0/5 | - | F p 0/5 |  | inf-2 |  | merges the leaver's weeks 1-8 into line 14 (counts over 75 days; with P5 applied, the leaver's Thursday X plus |
| sandwich-image-audit | 1.0.0 | P1 | 0/5 | - | F p 0/5 |  | inf-3 |  | lists ZK-212 and ZK-214 without a valid image and deletes the two renamed files (which are their valid images) |
| sandwich-image-audit | 1.1.0 | P1 | 0/5 | - | F p 0/5 |  | inf-3 |  | ZK-208 needs_photo and its re-shot file left out of download_register (FALSE MERGE of two different files that |
| sandwich-image-audit | 1.2.0 | P2 | 0/5 | - | F p 0/5 |  | inf-3 |  | ZK-208 needs_photo and its re-shot file left out of download_register (FALSE MERGE of two different files that |
| spice-pitch-deck-qa | 1.0.0 | P2 | 0/5 | 0/5 | A p 0/5; F p 0/5 |  | st-v1 |  | decides whose asset it is from the designer-typed asset_name: the kit palette IDK-03 placed on NV-08 as 'Navra |
| station-register-consolidation | 1.0.0 | P3 | 0/5 | 0/5 | A p 0/5; F p 0/5 |  | st-v1 |  | joins Table 2-2 to the coded stations on the station name alone and takes the first row with that name, so 47- |
| timesheet-overtime-review | 1.0.0 | P5 | 0/5 | 0/5 | A p 0/5; F p 0/5 |  | st-v1 |  | groups Monday's blocks by the task code as written: task 5512 noted first as OMN_MA_B1_G4_T1_SB_U4_L1_L06_ACT  |
| timesheet-overtime-review | 2.1.0 | P4 | 0/5 | - | F p 0/5 |  | inf-2 |  | merges the proofreading-room desk on the third floor with Rana's fourth-floor desk and takes the dead-screen h |

### E.stored: Stored or repeated figure vs the derivation the rules require

| task | ver | P | F | A | stages | verdict | S/I | re | misreading |
|---|---|---|---|---|---|---|---|---|---|
| billiard-shift-audit | 1.0.0 | P4 | 0/5 | 0/5 | A p 0/5; F p 0/5 |  | st-v1 |  | prices the new cream ale at the 300 that the POS card, the chalkboard, the layout draft and the chat all repea |
| brightwater-spec-qa | 1.0.0 | P3 | 0/5 | 0/5 | A p 0/5; F p 0/5 |  | st-v1 |  | (premise text not preserved; family from the signal_gate output) |
| cafe-kitchen-schedule-revisions | 1.0.0 | P6 | 0/5 | 0/5 | A p 0/5; F p 0/5 |  | st-v1 |  | takes the 76 cm quoted in the PM note (and repeated as 0.76 m in the memo draft) instead of the west jamb deri |
| cnc-router-bom-reconcile | 1.0.0 | P1 | 0/5 | 0/5 | A p 0/5; F p 0/5 |  | st-v1 |  | takes the notes' typed '± Rp793.000' (repeated by Bayu in the chat as '793rb', with its self-consistent '±207r |
| eco-guard-errata-review | 2.0.0 | P4 | 0/5 | - | F p 0/5 |  | inf-2 |  | keeps the realisable bound (199 leaves) because the summary prints 1.00, although two laboratory leaves with i |
| eco-guard-errata-review | 2.1.0 | P4 | 0/5 | - | F p 0/5 |  | inf-2 |  | keeps the realisable bound (199 leaves) because the summary prints 1.00, although two laboratory leaves with i |
| eco-guard-errata-review | 2.2.0 | P4 | 0/5 | - | F p 0/5 |  | inf-2 |  | keeps the realisable bound (199 leaves) because the summary prints 1.00, although two laboratory leaves with i |
| eco-guard-errata-review | 2.3.0 | P4 | 0/5 | 1/5 | A p 1/5; F p 0/5 |  | inf-2 |  | keeps the realisable bound (199 leaves) because the summary prints 1.00, although two laboratory leaves with i |
| hammamet-voucher-reissue | 1.0.0 | P3 | 0/5 | 0/5 | A p 0/5; F p 0/5 |  | st-v1 |  | sorts guests into tax categories by the rooming list's 'pays' (the address country) instead of the nationality |
| home-bp-diary-summary | 1.0.0 | P4 | 0/5 | 0/5 | A p 0/5; F p 0/5 |  | st-v1 |  | copies the office BP 165/90 that the consultation note's summary line, the referral letter and the summary tem |
| home-bp-diary-summary | 2.0.0 | P3 | 0/5 | - | F p 0/5 |  | inf-3 |  | reports 170/90 (the consultation's larger, left-arm reading) instead of the right arm's 160/90 |
| moot-issue3-memorial-audit | 1.0.0 | P5 | 0/5 | 0/5 | A p 0/5; F p 0/5 |  | st-v1 |  | takes the tracker's and counsel's 'colourable passage = Kavita Rao para 219' as settled: accepts fn 31 (para 2 |
| moot-issue3-memorial-audit | 2.0.0 | P6 | 0/5 | - | F p 0/5 |  | inf-3 |  | leaves fn 6 and fn 27 unconfirmed because their quotations carry an ellipsis (fn 27 then agrees with the track |
| moot-issue3-memorial-audit | 2.1.0 | P6 | 0/5 | 0/5 | A p 0/5; F p 0/5 |  | inf-3 |  | leaves fn 6 and fn 27 unconfirmed because their quotations carry an ellipsis (fn 27 then agrees with the track |
| niche-shelving-screen | 1.0.0 | P4 | 0/5 | 0/5 | A p 0/5; F p 0/5 |  | inf-3 |  | screens heights against 260.0 cm, so the Lift Tall WE-2180 (259-300 cm), the HOGA column HV-1063 (259 cm) and  |
| okra-manuscript-revision | 1.0.0 | P4 | 0/5 | 0/5 | A p 0/5; F p 0/5 |  | st-v1 |  | uses Rs 2,250, the middle of Rohit's remembered 2,000-2,500, which the chat and the checklist both repeat; the |
| okra-manuscript-revision | 1.0.0 | P9 | 0/5 | 0/5 | A p 0/5; F p 0/5 |  | st-v1 |  | trusts the B:C of 3.87 that the abstract, section 3.4 and the conclusion all repeat for M1NPK2 (a gross-based  |
| pathway-choice-audit | 1.0.0 | P1 | 0/5 | 0/5 | A p 0/5; F p 0/5 |  | st-v1 |  | reports the Social Sciences header's 16 (repeated by the HOD checklist and the parents' circular, and equal to |
| spice-pitch-deck-qa | 1.0.0 | P1 | 0/5 | 0/5 | A p 0/5; F p 0/5 |  | st-v1 |  | sees 'Rajkot' on the signed fact sheet (it is the registered office in the company table), finds the team's de |
| student-laptop-shortlist | 1.0.0 | P1 | 0/5 | 0/5 | A p 0/5; F p 0/5 |  | st-v1 |  | prices L-401 (the only brand-store listing, whose price-list row carries no price) at the 74,990 the roundup r |
| suitcase-cover-matrix-check | 1.0.0 | P1 | 0/5 | 0/5 | A p 0/5; F p 0/5 |  | st-v1 |  | reports the deck's '28 дизайнов' (slide 7 and its speaker notes), which the matrix seems to confirm with 28 di |
| suitcase-cover-matrix-check | 1.0.0 | P2 | 0/5 | 0/5 | A p 0/5; F p 0/5 |  | st-v1 |  | takes the colour cluster from the matrix's 'Коллекция' column (Urban Dark / Soft Nude / Pop Bright read as dar |
| suitcase-cover-matrix-check | 1.0.0 | P3 | 0/5 | 0/5 | A p 0/5; F p 0/5 |  | st-v1 |  | counts sizes from the matrix's 'Размер (этикетка поставщика)' column, as the deck's size split does (S 13 / M  |

### S.coverage: Counting unit / coverage (what counts as one item; silent omissions)

| task | ver | P | F | A | stages | verdict | S/I | re | misreading |
|---|---|---|---|---|---|---|---|---|---|
| cnc-router-bom-reconcile | 1.0.0 | P4 | 0/5 | 0/5 | A p 0/5; F p 0/5 |  | st-v1 |  | builds the order from the v1 shopping section alone and never cross-checks the assembly steps (rule 1.1): no m |
| cnc-router-bom-reconcile | 2.0.0 | P4 | 0/5 | - | F p 0/5 |  | inf-2 |  | orders one extension per motor (4), although the rotary kit carries the headstock motor's own 1,5 m lead to th |
| cnc-router-bom-reconcile | 2.1.0 | P4 | 0/5 | - | F p 0/5 |  | inf-2 |  | orders one extension per motor (4), although the rotary kit carries the headstock motor's own 1,5 m lead to th |
| cnc-router-bom-reconcile | 2.2.0 | P4 | 0/5 | - | F p 0/5 |  | inf-2 |  | orders one extension per motor (4), although the rotary kit carries the headstock motor's own 1,5 m lead to th |
| coloring-book-retitle-audit | 1.0.0 | P2 | 0/5 | 0/5 | A p 0/5; F p 0/5 |  | st-v1 |  | audits margins only where the preflight export prints a min_margin_in value, so the two placed front pages (3  |
| coloring-book-retitle-audit | 1.0.0 | P6 | 0/5 | 0/5 | A p 0/5; F p 0/5 |  | st-v1 |  | regenerates only the pages whose preflight content line shows the title (page 1) and silently omits the copyri |
| coloring-book-retitle-audit | 2.0.0 | P2 | 0/5 | - | F p 0/5 |  | inf-4 |  | treats the preflight's frame-layer margin as the page's margin; the signature on the 'stirring one' (D05, page |
| coloring-book-retitle-audit | 2.0.0 | P4 | 0/5 | - | F p 0/5 |  | inf-2 |  | lists only the pages where the old title is printed literally (page 1); page 2's text is the {title} field fil |
| coloring-book-retitle-audit | 2.0.0 | P9 | 0/5 | - | F p 0/5 |  | inf-2 |  | reads the goods cell as one list under the class column; the books in it belong to the appended class 9 (downl |
| current-affairs-booklet-plan | 1.0.0 | P1 | 0/5 | - | F p 0/5 |  | inf-3 |  | treats each transcription block as one point, so the point the teacher wrote on the same line as the one befor |
| eco-guard-errata-review | 1.0.0 | P2 | 0/5 | 0/5 | A p 0/5; F p 0/5 |  | st-v1 |  | logs only the locations a correction note names; the summary line that still says deployment error always exce |
| ethics-report-mark-release | 1.0.0 | P4 | 0/5 | - | F p 0/5 |  | inf-3 |  | counts section 8 as body: word_count 2,370 instead of 2,140. The attribute that decides is the section's posit |
| hammamet-voucher-reissue | 1.0.0 | P1 | 0/5 | 0/5 | A p 0/5; F p 0/5 |  | st-v1 |  | counts lunches by nights (board from the arrival-day dinner, the standard 14h00 check-in) and adds only the de |
| kibo-budget-cap-review | 1.0.0 | P1 | 0/5 | 0/5 | A p 0/5; F p 0/5 |  | st-v1 |  | checks the keep list on its first card column only (one card per row), so the two 'Kept together with' cards t |
| killzone-journal-review | 1.0.0 | P4 | 0/5 | - | F p 0/5 |  | inf-3 |  | 61807420 r = 0.5 (first half's P/L over the position's risk) instead of 1.8 (both halves); with P3 also misrea |
| line-reference-belegliste | 1.0.0 | P4 | 0/5 | - | F p 0/5 |  | inf-2 |  | C06 not word-for-word and cited as Z. 6 only |
| moot-issue3-memorial-audit | 1.0.0 | P2 | 0/5 | 0/5 | A p 0/5; F p 0/5 |  | st-v1 |  | audits CLFAC per argument, so the In casu filed under argument 3.2 is taken to cover sub-argument 3.2.1; only  |
| moot-issue3-memorial-audit | 2.0.0 | P2 | 0/5 | - | F p 0/5 |  | inf-3 |  | lists 3.3.2 as compliant because a row tagged in_casu sits under it, though that row states law and never open |
| moot-issue3-memorial-audit | 2.1.0 | P2 | 0/5 | 0/5 | A p 0/5; F p 0/5 |  | inf-3 |  | lists 3.3.2 as compliant because a row tagged in_casu sits under it, though that row states law and never open |
| moot-issue3-memorial-audit | 2.2.0 | P2 | 0/5 | 0/5 | A p 0/5; F p 0/5 |  | inf-3 |  | lists 3.3.2 as compliant because a row tagged in_casu sits under it, though that row states law and never open |
| mustangs-tryout-roster | 1.0.0 | P2 | 0/5 | 0/5 | A p 0/5; F p 0/5 |  | st-v1 |  | reads one child per form row (the player_1 columns) or treats a form as covered once one of its children is lo |
| pathway-choice-audit | 1.0.0 | P4 | 0/5 | 0/5 | A p 0/5; F p 0/5 |  | st-v1 |  | builds the follow-up list from the slip export only, so the two register learners who returned no slip (G9-009 |
| probation-answer-key | 2.0.0 | P4 | 0/5 | - | F p 0/5 |  | inf-3 |  | questions of cases 1 and 7 reduced to their first sentence (a complete-looking question), so they are not the  |
| probation-answer-key | 2.1.0 | P4 | 0/5 | - | F p 0/5 |  | inf-3 |  | questions of cases 1 and 7 reduced to their first sentence (a complete-looking question), so they are not the  |
| psychopathy-evidence-screen | 1.0.0 | P4 | 0/5 | 0/5 | A p 0/5; F p 0/5 |  | st-v1 |  | screens the multi-sample record R07 as one unit: its record-level age band 15-64 includes under-18s, so the wh |

### CV.stated: Rule or convention stated outright

| task | ver | P | F | A | stages | verdict | S/I | re | misreading |
|---|---|---|---|---|---|---|---|---|---|
| coloring-book-retitle-audit | 1.0.0 | P3 | 0/5 | 0/5 | A p 0/5; F p 0/5 |  | st |  | counts the rows of the preflight export (65, rule 1.3) and reports the file's odd page count instead of the bo |
| coloring-book-retitle-audit | 2.0.0 | P3 | 0/5 | - | F p 0/5 |  | st |  | reports the 65 pages of the file instead of the 66 Quillmark counts after rule 4.2's added blank page (filler  |
| deck-preread-review | 2.0.0 | P4 | 0/5 | - | F p 0/5 |  | st |  | adds N1 (pie/legend swap), N5 (added summary slide) and N7 (takeaway above the chart) to sequence_notes |
| hammamet-voucher-reissue | 2.0.0 | P5 | 0/5 | - | F p 0/5 |  | st |  | writes the departure-day lunch note under 'Remarques' |
| home-bp-diary-summary | 2.0.0 | P4 | 0/5 | - | F p 0/5 |  | st |  | measures the 30 minutes from the workout's logged start, so the 26 August evening and 1 September morning sess |
| insurance-secrecy-register | 1.2.0 | P3 | 0/5 | 0/5 | A p 0/5; F p 0/5 |  | st |  | dates C11 by its first episode (2025-03-14) and puts it on the 2019 edition (500,000) instead of its last epis |
| kibo-budget-cap-review | 1.0.0 | P3 | 0/5 | 0/5 | A p 0/5; F p 0/5 |  | st |  | prices each card at the first row listed for its name (the export is filed per printing, in set-code order), e |
| moot-issue3-memorial-audit | 2.0.0 | P3 | 0/5 | - | F p 0/5 |  | st |  | leaves the two mixed footnotes (28, 40) out of the counted register, following Annex C's summary |
| moot-issue3-memorial-audit | 2.1.0 | P3 | 0/5 | 0/5 | A p 0/5; F p 0/5 |  | st |  | leaves the two mixed footnotes (28, 40) out of the counted register, following Annex C's summary |
| mustangs-tryout-roster | 2.0.0 | P6 | 0/5 | - | F p 0/5 |  | st |  | keeps the house-only MU-109 and MU-122 on the travel roster; both are then noticed (away 25 Sept; no Sundays) |
| mustangs-tryout-roster | 2.1.0 | P6 | 0/5 | 0/5 | A p 0/5; F p 0/5 |  | st |  | keeps the house-only MU-109 and MU-122 on the travel roster; both are then noticed (away 25 Sept; no Sundays) |
| mustangs-tryout-roster | 2.2.0 | P6 | 0/5 | 0/5 | A p 0/5; F p 0/5 |  | st |  | keeps the house-only MU-109 and MU-122 on the travel roster; both are then noticed (away 25 Sept; no Sundays) |
| niche-shelving-screen | 1.0.0 | P5 | 0/5 | 0/5 | A p 0/5; F p 0/5 |  | st |  | excludes the four-leg Klampa KL-0404 (rail underside 12 cm) and the raised-base Polcar PC-0311 (11 cm) as base |
| niche-shelving-screen | 1.1.0 | P5 | 0/15 | 0/15 | A f 0/10; p 0/5; F f 0/10; p 0/5 |  | st |  | excludes the four-leg Klampa KL-0404 (rail underside 12 cm) and the raised-base Polcár PC-0311 (11 cm) as base |
| okra-manuscript-revision | 2.0.0 | P3 | 0/5 | - | F p 0/5 |  | st |  | also lists the abstract, conclusion and section-3.4 statements and Table 4 because they repeat the old yields |
| okra-manuscript-revision | 2.1.0 | P3 | 0/5 | - | F p 0/5 |  | st |  | also lists the abstract, conclusion and section-3.4 statements and Table 4 because they repeat the old yields |
| probation-answer-key | 2.0.0 | P5 | 0/5 | - | F p 0/5 |  | st |  | case 6 'незаконно' (art. 331.3 applied to a lab assistant who conducts lab classes on instruction); the lab as |
| probation-answer-key | 2.1.0 | P5 | 0/5 | - | F p 0/5 |  | st |  | case 6 'незаконно' (art. 331.3 applied to a lab assistant who conducts lab classes on instruction); the lab as |
| sandwich-image-audit | 1.0.0 | P4 | 0/5 | - | F p 0/5 |  | st |  | ZK-213 (C) and ZK-217 (B) without a valid image; their files deleted |
| sandwich-image-audit | 1.1.0 | P4 | 0/5 | - | F p 0/5 |  | st |  | ZK-213 (C) and ZK-217 (B) needs_photo; their files left out of download_register |
| suitcase-cover-matrix-check | 2.0.0 | P4 | 0/5 | 0/5 | A p 0/5; F p 0/5 |  | st |  | sizes from the supplier label: two 'M' covers fit 66-70 cm suitcases and one 'L' cover fits 76-80 cm, so the g |

### T.edition: Which edition or version applies, by the real receipt / effective date

| task | ver | P | F | A | stages | verdict | S/I | re | misreading |
|---|---|---|---|---|---|---|---|---|---|
| brightwater-spec-qa | 1.1.0 | P3 | 0/5 | - | F p 0/5 |  | inf-3 |  | gives two business days for C-009, C-031, C-035 and C-036; version 1 (one business day) still applies at launc |
| cafe-kitchen-schedule-revisions | 1.0.0 | P3 | 0/5 | 0/5 | A p 0/5; F p 0/5 |  | st-v1 |  | applies edition 4 because it is the newest edition 'in force' on the as-of date, so the 60 cm operator space a |
| cafe-kitchen-schedule-revisions | 2.0.0 | P1 | 0/5 | - | F p 0/5 |  | inf-3 |  | applies edition 3 because the job was opened on 2026-08-20, so D8 (40 + 4 + 50 = 94 <= 100) opens; under editi |
| cafe-kitchen-schedule-revisions | 2.1.0 | P1 | 15/15 | 15/15 | A f 10/10; p 5/5; F f 10/10; p 5/5 | GENUINE | inf-3 |  | keeps the job-keyed inbox row (2026-08-24): edition 3, D7 needs 58 + 0 + 50 = 108 <= 115 and opens; the brief  |
| cafe-kitchen-schedule-revisions | 2.1.0 | P6 | 15/15 | 15/15 | A f 10/10; p 5/5; F f 10/10; p 5/5 | GENUINE | inf-3 | re | as P1 in rev 1 (a fresh session re-decides it): D7 opens under edition 3; under edition 4 it fails clearance |
| cafe-kitchen-schedule-revisions | 2.1.1 | P1 | 15/15 | 15/15 | A f 10/10; p 5/5; F f 10/10; p 5/5 | GENUINE | inf-3 |  | keeps the job-keyed inbox row (2026-08-24): edition 3, D7 needs 58 + 0 + 50 = 108 <= 115 and opens; the brief  |
| cafe-kitchen-schedule-revisions | 2.1.1 | P6 | 15/15 | 15/15 | A f 10/10; p 5/5; F f 10/10; p 5/5 | GENUINE | inf-3 | re | as P1 in rev 1 (a fresh session re-decides it): D7 opens under edition 3; under edition 4 it fails clearance |
| cafe-kitchen-schedule-revisions | 2.2.0 | P1 | 3/5 | - | F p 3/5 |  | inf-4 |  | keeps the job-keyed inbox row (2026-08-24): edition 3, D7 needs 58 + 0 + 50 = 108 <= 115 and opens; the brief  |
| cafe-kitchen-schedule-revisions | 2.2.0 | P6 | 2/5 | - | F p 2/5 |  | inf-4 | re | as P1 in rev 1 (a fresh session re-decides it): D7 opens under edition 3; under edition 4 it fails clearance |
| cafe-kitchen-schedule-revisions | 2.3.0 | P1 | 6/15 | - | F f 5/10; p 1/5 | BLIND-1.0 | inf-4 |  | keeps the job-keyed inbox row (2026-08-24): edition 3, D7 needs 58 + 0 + 50 = 108 <= 115 and opens; the brief  |
| cafe-kitchen-schedule-revisions | 2.3.0 | P6 | 8/15 | - | F f 5/10; p 3/5 | BLIND-1.0 | inf-4 | re | as P1 in rev 1 (a fresh session re-decides it): D7 opens under edition 3; under edition 4 it fails clearance |
| coloring-book-retitle-audit | 1.0.0 | P7 | 0/5 | 0/5 | A p 0/5; F p 0/5 |  | st-v1 |  | treats S-2001 WITCHY LIFE as dead because its latest register event is 'CANCELLATION RECORDED' (2026-08-28), a |
| deck-preread-review | 1.0.0 | P3 | 0/5 | 0/5 | A p 0/5; F p 0/5 |  | st-v1 |  | maps each comment's page number onto the current v3 deck, so the five comments from v2 page 6 on land one slid |
| deck-preread-review | 2.0.0 | P2 | 0/5 | - | F p 0/5 |  | inf-5 |  | maps the pre-read page onto the v3 page: N3 S-08, N4 S-20, N6 S-11, N7 S-25, N8 S-23 |
| hammamet-voucher-reissue | 2.0.0 | P4 | 0/5 | - | F p 0/5 |  | inf-2 |  | 4 free entries (one per person, the June-August row) instead of 2 (one per room, the September row that holds  |
| home-bp-diary-summary | 2.4.0 | P5 | 0/5 | - | F p 0/5 |  | inf-3 |  | leaves both 23 August sessions (day 1) out of the baseline as the master copy's shaded practice day; Pavel's s |
| home-bp-diary-summary | 2.5.0 | P5 | 0/5 | - | F p 0/5 |  | inf-3 |  | leaves both 23 August sessions (day 1) out of the baseline as the master copy's shaded practice day; Pavel's s |
| home-bp-diary-summary | 2.6.0 | P5 | 5/5 | - | F p 5/5 | UNCONFIRMED | inf-3 |  | leaves both 23 August sessions (day 1) out of the baseline as the master's grey practice row; his diary is com |
| home-bp-diary-summary | 2.7.0 | P5 | 5/5 | - | F p 5/5 | UNCONFIRMED | inf-4 |  | leaves both 23 August sessions (day 1) out of the baseline as the master's grey practice row; his diary is com |
| insurance-secrecy-register | 1.0.0 | P1 | 0/5 | - | F p 0/5 |  | inf-2 |  | puts C04 (act 6 June 2025) and C09 (last date 10 June 2025) on the 2025 edition with its tripled top fines, al |
| insurance-secrecy-register | 1.1.0 | P2 | 0/5 | - | F p 0/5 |  | inf-2 |  | puts C04 (act 6 June 2025) and C09 (last date 10 June 2025) on the 2025 edition with its tripled top fines, al |
| insurance-secrecy-register | 1.2.0 | P2 | 0/5 | 0/5 | A p 0/5; F p 0/5 |  | inf-2 |  | puts C04 (act 6 June 2025) and C09 (last date 10 June 2025) on the 2025 edition with its tripled top fines, al |
| ktp-lesson-plan-alignment | 1.0.0 | P1 | 0/5 | - | F p 0/5 |  | st-v1 |  | applies the KTP revision from the date it carries (14 September, in its file name and cover note, which asks t |
| ktp-lesson-plan-alignment | 2.0.0 | P1 | 0/5 | - | F p 0/5 |  | inf-4 |  | L04 and L05 keep the approved KTP's topics 4 and 5 (the topics their plans teach) instead of the revision's 5  |
| ktp-lesson-plan-alignment | 2.1.0 | P1 | 0/5 | - | F p 0/5 |  | inf-4 |  | L04 and L05 keep the approved KTP's topics 4 and 5 (the topics their plans teach) instead of the revision's 5  |
| ktp-lesson-plan-alignment | 2.2.0 | P1 | 0/5 | - | F p 0/5 |  | inf-4 |  | L04 and L05 keep the approved KTP's topics 4 and 5 (the topics their plans teach) instead of the revision's 5  |
| probation-answer-key | 1.0.0 | P1 | 0/5 | 0/5 | A p 0/5; F p 0/5 |  | st-v1 |  | takes the norm table's bare 'В силу с 01.09.2026' for the art. 71 warning change (ignores art. 2(2) of Law No. |
| probation-answer-key | 1.0.0 | P2 | 0/5 | 0/5 | A p 0/5; F p 0/5 |  | st-v1 |  | reports the article number printed in the collection ('ст. 331.1 КоТ', 2024 numbering) for cases 6 and 7; in t |
| probation-answer-key | 2.0.0 | P1 | 0/5 | - | F p 0/5 |  | inf-5 |  | case 5 'незаконно' (start of work 01.09.2026 read as the contract date -> 2026 text, a son of two is under the |
| probation-answer-key | 2.0.0 | P2 | 0/5 | - | F p 0/5 |  | inf-4 |  | reports '331.1' for cases 6 and 7 (the collection's own 2024 numbering); the table article containing the desc |
| probation-answer-key | 2.1.0 | P1 | 0/5 | - | F p 0/5 |  | inf-5 |  | case 5 'незаконно' (start of work 01.09.2026 read as the contract date -> 2026 text, a son of two is under the |
| probation-answer-key | 2.2.0 | P1 | 0/15 | 0/15 | A f 0/10; p 0/5; F f 0/10; p 0/5 |  | inf-5 |  | case 5 'незаконно' (start of work 01.09.2026 read as the contract date -> 2026 text, a son of two is under the |
| spice-pitch-deck-qa | 1.0.0 | P4 | 0/5 | 0/5 | A p 0/5; F p 0/5 |  | st-v1 |  | reads Arjun's bare priority numbers 4, 6, 8, 14, 19 as positions in the current v3 deck; NV-25 was inserted at |
| spice-pitch-deck-qa | 2.0.0 | P3 | 0/5 | - | F p 0/5 |  | inf-3 |  | reads Arjun's numbers as v3 positions: rows 10-17 shift one slide back (row 10 lands on the new NV-25, row 13' |
| student-laptop-shortlist | 1.0.0 | P4 | 0/5 | 0/5 | A p 0/5; F p 0/5 |  | st-v1 |  | takes the last row filed for each listing (last row wins; equally, the latest row announced on or before the s |
| timesheet-overtime-review | 2.4.0 | P5 | 0/15 | - | F f 0/10; p 0/5 |  | inf-3 |  | values Monday's claim at the 2025/26 content-developer hour (148.00): 333.00 for 02:15 instead of 369.00 (164. |
| timesheet-overtime-review | 2.5.0 | P5 | 0/5 | - | F p 0/5 |  | inf-3 |  | values Monday's claim at the 2025/26 content-developer hour (148.00): 333.00 for 02:15 instead of 369.00 (164. |
| timesheet-overtime-review | 2.6.0 | P5 | 0/5 | - | F p 0/5 |  | inf-3 |  | values Monday's claim at the 2025/26 content-developer hour (148.00): 333.00 for 02:15 instead of 369.00 (164. |

### T.revised: Restated figure supersedes the first issue

| task | ver | P | F | A | stages | verdict | S/I | re | misreading |
|---|---|---|---|---|---|---|---|---|---|
| blockprint-winter-close | 1.0.0 | P3 | 0/5 | - | F p 0/5 |  | inf-3 |  | carries issue 1 forward: winter_opening_units 139 instead of 151, and, when the boxed rows are included, IMP-0 |
| brightwater-spec-qa | 1.1.0 | P4 | 0/5 | - | F p 0/5 |  | inf-3 |  | keeps 11.1 million TEU (the January issue repeated by D-02, the README and the ticked QA line) instead of the  |
| current-affairs-booklet-plan | 1.0.0 | P3 | 0/5 | - | F p 0/5 |  | inf-3 |  | prints the Saryu Snan Mela count as the point and release 3/2026 give it (2.86) instead of as release 4/2026 r |
| eco-guard-errata-review | 2.0.0 | P2 | 0/5 | - | F p 0/5 |  | inf-3 |  | keeps the first-reported baseline count (4 healthy leaves sprayed, issue 1 and the review copy) instead of the |
| feast-sharing-runsheet | 1.0.0 | P3 | 0/5 | - | F p 0/5 |  | inf-3 |  | keeps the first-published 14 September roll (31 and 24) for the two classes whose roll the 23 September issue  |
| lassa-kap-results-sheet | 1.0.0 | P1 | 0/5 | - | F p 0/5 |  | inf-3 |  | Faculty of Social Sciences male head count 1,382 (first issue / Table 1 / abstract) instead of the restated 1, |
| manhole-excavation-valuation | 1.0.0 | P4 | 0/5 | - | F p 0/5 |  | inf-2 |  | A03 at the issue-1 invert 11.367: 11.55 (IV-04's figure) instead of 12.14 |
| okra-manuscript-revision | 2.0.0 | P4 | 0/5 | - | F p 0/5 |  | inf-2 |  | takes the first-reported weekly export for every picking week, so W37 and W39 carry 2,250 and 2,330 instead of |
| okra-manuscript-revision | 2.1.0 | P4 | 0/5 | - | F p 0/5 |  | inf-2 |  | takes the first-reported weekly export for every picking week, so W37 and W39 carry 2,250 and 2,330 instead of |
| profile-copy-claims-audit | 2.0.0 | P1 | 0/5 | - | F p 0/5 |  | inf-4 |  | takes December 2025 (492 direct) and July 2026 (628 direct) from their own first-run reports instead of the ne |
| profile-copy-claims-audit | 2.1.0 | P1 | 0/15 | 0/15 | A f 0/10; p 0/5; F f 0/10; p 0/5 |  | inf-4 |  | takes December 2025 (491 direct) and July 2026 (628 direct) from their own first-run reports instead of the ne |
| profile-copy-claims-audit | 2.2.0 | P1 | 0/15 | 0/15 | A f 0/10; p 0/5; F f 0/10; p 0/5 |  | inf-4 |  | takes December 2025 (491 direct) and July 2026 (628 direct) from their own first-run reports instead of the ne |
| profile-copy-claims-audit | 2.3.0 | P1 | 0/15 | 0/15 | A f 0/10; p 0/5; F f 0/10; p 0/5 |  | inf-4 |  | takes December 2025 (491 direct) and July 2026 (628 direct) from their own first-run reports instead of the ne |
| profile-copy-claims-audit | 2.4.0 | P1 | 0/15 | 0/15 | A f 0/10; p 0/5; F f 0/10; p 0/5 |  | inf-4 |  | takes December 2025 (491 direct) and July 2026 (628 direct) from their own first-run reports instead of the ne |
| pupil-tracker-term-summary | 1.0.0 | P3 | 0/5 | - | F p 0/5 |  | inf-3 |  | takes lines 31-34's weeks 1-8 counts from the grid as first issued (lines 32 and 33 each one tick short, one ! |
| station-register-consolidation | 2.3.0 | P3 | 0/5 | 0/5 | A p 0/5; F p 0/5 |  | inf-4 |  | takes the first-issued circular's date for the Firuzkuh rain gauge's closure, so meteorological 47-005 is drop |
| student-laptop-shortlist | 2.0.0 | P3 | 0/5 | - | F p 0/5 |  | inf-2 |  | prices L-413 at the first-filed 83,960 (77,663 instead of 76,738) and L-414 at 124,990 (121,990 instead of 119 |

### E.actual: First-hand actual fact overrides the filed record

| task | ver | P | F | A | stages | verdict | S/I | re | misreading |
|---|---|---|---|---|---|---|---|---|---|
| billiard-shift-audit | 2.0.0 | P3 | 2/5 | 0/5 | A p 0/5; F p 2/5 | BLIND-1.0 | inf-2 |  | bills the 31.10 afternoon check on table 3 (3110-03) for three started hours from the POS stamps; the table wa |
| billiard-shift-audit | 2.1.0 | P3 | 2/5 | 0/5 | A p 0/5; F p 2/5 |  | inf-2 |  | bills the 31.10 afternoon check on table 3 (3110-03) for three started hours from the POS stamps; the table wa |
| blockprint-winter-close | 1.1.0 | P4 | 0/5 | - | F p 0/5 |  | inf-4 |  | shares R-0222 (Hôtel des Remparts, Avignon fair), where Farid slept at his sister's this year: 86 instead of 1 |
| blockprint-winter-close | 1.2.0 | P4 | 0/5 | 0/5 | A p 0/5; F p 0/5 |  | inf-4 |  | shares R-0222 (Hôtel des Remparts, Avignon fair), where Farid slept at his sister's this year: 86 instead of 1 |
| cafe-kitchen-schedule-revisions | 2.0.0 | P6 | 0/5 | - | F p 0/5 |  | inf-2 |  | keeps the hand-wash counter's basin and knee tap in the rev 1 BOQ: rows HW-1 + TJ-1, 2 bowls, 3 taps instead o |
| cafe-kitchen-schedule-revisions | 2.0.0 | P7 | 0/5 | - | F p 0/5 |  | inf-4 |  | builds the dishwasher counter at 85 and sets the plate rack from it (125 / 155); the confirmed warewasher is 8 |
| cafe-kitchen-schedule-revisions | 2.1.0 | P9 | 0/15 | 0/15 | A f 0/10; p 0/5; F f 0/10; p 0/5 |  | inf-2 |  | lists DS-1 at 85; the confirmed warewasher is 84 with its feet down, so the counter's floor is 87 and DS-1 is  |
| cafe-kitchen-schedule-revisions | 2.1.1 | P9 | 0/15 | 0/15 | A f 0/10; p 0/5; F f 0/10; p 0/5 |  | inf-2 |  | lists DS-1 at 85; the confirmed warewasher is 84 with its feet down, so the counter's floor is 87 and DS-1 is  |
| cafe-kitchen-schedule-revisions | 2.2.0 | P9 | 0/5 | - | F p 0/5 |  | inf-2 |  | lists DS-1 at 85; the confirmed warewasher is 84 with its feet down, so the counter's floor is 87 and DS-1 is  |
| cafe-kitchen-schedule-revisions | 2.3.0 | P9 | 0/15 | - | F f 0/10; p 0/5 |  | inf-2 |  | lists DS-1 at 85; the confirmed warewasher is 84 with its feet down, so the counter's floor is 87 and DS-1 is  |
| hammamet-voucher-reissue | 2.0.0 | P2 | 0/5 | - | F p 0/5 |  | inf-3 |  | Ines Ferchichi: etranger (the French CNI on file) instead of maghrebin (the Tunisian passport she registered o |
| hammamet-voucher-reissue | 2.1.0 | P2 | 0/5 | - | F p 0/5 |  | inf-3 |  | Ines Ferchichi: etranger (the French CNI on file) instead of maghrebin (the Tunisian passport she registered o |
| niche-shelving-screen | 1.1.0 | P2 | 0/15 | 0/15 | A f 0/10; p 0/5; F f 0/10; p 0/5 |  | inf-3 |  | passes the HÖGA shelving tower HV-1063 through test 1 on its 'floor-standing' mounting, so it qualifies at 248 |
| niche-shelving-screen | 1.3.0 | P2 | 0/5 | 0/5 | A p 0/5; F p 0/5 |  | inf-3 |  | passes the HÖGA shelving tower HV-1063 through test 1 on its 'floor-standing' mounting, so it qualifies at 248 |
| okra-manuscript-revision | 2.0.0 | P2 | 0/5 | - | F p 0/5 |  | inf-2 |  | divides every plot by the printed 25 plants, so the three straw-mulched treatments, M2 and the three NPK main  |
| okra-manuscript-revision | 2.0.0 | P5 | 0/5 | - | F p 0/5 |  | inf-2 |  | charges two spray rounds (the schedule), so the six sprayed treatments' costs miss one round (Rs 625 or Rs 1,2 |
| okra-manuscript-revision | 2.1.0 | P2 | 0/5 | - | F p 0/5 |  | inf-2 |  | divides every plot by the printed 25 plants, so the three straw-mulched treatments, M2 and the three NPK main  |
| okra-manuscript-revision | 2.1.0 | P5 | 0/5 | - | F p 0/5 |  | inf-2 |  | charges two spray rounds (the schedule), so the six sprayed treatments' costs miss one round (Rs 625 or Rs 1,2 |
| posting-month-close | 1.0.0 | P1 | 0/5 | - | F p 0/5 |  | inf-3 |  | pays Hira for the 48 weekday posts only; the three posts of Saturday 26 September, which she published while Z |
| posting-month-close | 1.1.0 | P1 | 0/5 | - | F p 0/5 |  | inf-3 |  | pays Hira for the 48 weekday posts only; the three posts of Saturday 26 September, which she published while Z |
| probation-answer-key | 2.0.0 | P3 | 0/5 | - | F p 0/5 |  | inf-4 |  | case 2 'незаконно' (dismissal 14.05 after the announced-term end 11.05) and case 3 'законно' (dismissal 13.07  |
| probation-answer-key | 2.1.0 | P3 | 0/5 | - | F p 0/5 |  | inf-4 |  | case 2 'незаконно' (dismissal 14.05 after the announced-term end 11.05) and case 3 'законно' (dismissal 13.07  |
| probation-answer-key | 2.2.0 | P3 | 0/15 | 0/15 | A f 0/10; p 0/5; F f 0/10; p 0/5 |  | inf-4 |  | case 2 'незаконно' (dismissal 14.05 after the announced-term end 11.05) and case 3 'законно' (dismissal 13.07  |
| probation-answer-key | 2.3.0 | P3 | 0/5 | 0/5 | A p 0/5; F p 0/5 |  | inf-4 |  | case 2 'незаконно' (dismissal 14.05 after the announced-term end 11.05) and case 3 'законно' (dismissal 13.07  |
| probation-answer-key | 2.4.0 | P3 | 0/5 | 0/5 | A p 0/5; F p 0/5 |  | inf-4 |  | case 2 'незаконно' (dismissal 14.05 after the announced-term end 11.05) and case 3 'законно' (dismissal 13.07  |
| psychopathy-evidence-screen | 2.0.0 | P4 | 0/5 | - | F p 0/5 |  | inf-2 |  | takes the probation setting code at face value: R08 qualifies with n 127 instead of X6 (its men were held at B |
| psychopathy-evidence-screen | 2.1.0 | P5 | 0/5 | - | F p 0/5 |  | inf-2 |  | takes the probation setting code at face value: R08 qualifies with n 127 instead of X6 (its men were held at B |
| psychopathy-evidence-screen | 2.2.0 | P5 | 0/5 | - | F p 0/5 |  | inf-2 |  | takes the probation setting code at face value: R08 qualifies with n 127 instead of X6 (its men were held at B |
| refurb-laptop-screen | 1.4.0 | P6 | 0/5 | 3/5 | A p 3/5; F p 0/5 |  | inf-3 |  | BW-103 passed at £123.99 with a stick (truth: the 2019 run with the i5-8350U has no free slot, so it cannot re |
| spice-pitch-deck-qa | 2.0.0 | P2 | 0/5 | - | F p 0/5 |  | inf-3 |  | gives the plant's town (Sanand) as the dispatch point because the switch was announced for 1 September; two Se |
| spice-pitch-deck-qa | 2.1.0 | P2 | 0/5 | - | F p 0/5 |  | inf-3 |  | gives the plant's town (Sanand) as the dispatch point because the switch was announced for 1 September; two Se |
| spice-pitch-deck-qa | 2.2.0 | P2 | 0/5 | 0/5 | A p 0/5; F p 0/5 |  | inf-3 |  | gives the plant's town (Sanand) as the dispatch point because the switch was announced for 1 September; the cl |
| spice-pitch-deck-qa | 2.3.0 | P2 | 0/5 | 0/5 | A p 0/5; F p 0/5 |  | inf-3 |  | gives the plant's town (Sanand) as the dispatch point because the switch was announced for 1 September; the cl |

### S.answer: Determinable vs not determinable

| task | ver | P | F | A | stages | verdict | S/I | re | misreading |
|---|---|---|---|---|---|---|---|---|---|
| council-video-index | 1.0.0 | P4 | 0/5 | - | F p 0/5 |  | inf-2 |  | takes resolution numbers from the register only, so the asbestos programme item (adopted, signed, sent to the  |
| current-affairs-booklet-plan | 1.0.0 | P4 | 0/5 | - | F p 0/5 |  | inf-2 |  | sends both illegible blocks to the Verify box, although the fact bank holds a checked reading of the park poin |
| gst-workbook-answer-key | 1.0.0 | P3 | 0/5 | - | F p 0/5 |  | inf-2 |  | S-106 'not determinable', 0/0/0. Truth: the carton went by the Kaveri Roadways parcel counter on the invoice d |
| insurance-secrecy-register | 1.0.0 | P4 | 0/5 | - | F p 0/5 |  | inf-3 |  | enters C05 as not determinable with null edition and fine, although the bailiffs opened a criminal-fine procee |
| mustangs-tryout-roster | 2.0.0 | P3 | 0/5 | - | F p 0/5 |  | inf-2 |  | clears MU-106, whose log row records a hospital birth record, instead of listing him pending |
| mustangs-tryout-roster | 2.1.0 | P3 | 0/5 | 0/5 | A p 0/5; F p 0/5 |  | inf-2 |  | clears MU-106, whose log row records a hospital birth record, instead of listing him pending |
| mustangs-tryout-roster | 2.2.0 | P15 | 0/5 | 0/5 | A p 0/5; F p 0/5 |  | inf-2 |  | clears MU-106 on his 22 August log row instead of listing him pending: his mother wrote on 5 September that th |
| mustangs-tryout-roster | 2.2.0 | P16 | 0/5 | 0/5 | A p 0/5; F p 0/5 |  | inf-2 | re | P15 re-decided: MU-106 put on the travel roster and expected on Sunday |
| mustangs-tryout-roster | 2.2.0 | P17 | 0/5 | 0/5 | A p 0/5; F p 0/5 |  | inf-2 | re | P15 re-decided: MU-106 on the Sunday list |
| probation-answer-key | 1.0.0 | P3 | 0/5 | 0/5 | A p 0/5; F p 0/5 |  | st-v1 |  | decides case 8 on the merits ('законно'), reading 'матерью двоих детей' with unstated ages as 'no child under  |
| psychopathy-evidence-screen | 1.0.0 | P2 | 0/5 | 0/5 | A p 0/5; F p 0/5 |  | st-v1 |  | reads the setting from the evidence table alone: the blank setting cell of R09 makes it not determinable, alth |
| refurb-laptop-screen | 1.1.0 | P4 | 0/5 | - | F p 0/5 |  | inf-3 |  | BW-101 not_determinable with a null total (truth: Meridian 3590 with a free DDR4 slot, pass at £108.50, the ch |
| refurb-laptop-screen | 1.2.0 | P4 | 0/5 | - | F p 0/5 |  | inf-3 |  | BW-101 not_determinable with a null total (truth: Meridian 3590 with a free DDR4 slot, pass at £108.50, the ch |
| refurb-laptop-screen | 1.3.0 | P4 | 0/5 | - | F p 0/5 |  | inf-3 |  | BW-101 not_determinable with a null total (truth: Meridian 3590 with a free DDR4 slot, pass at £108.50, the ch |
| refurb-laptop-screen | 1.4.0 | P4 | 0/5 | 1/5 | A p 1/5; F p 0/5 |  | inf-3 |  | BW-101 not_determinable with a null total (truth: an ex-council Delmar 15.6-inch i5-8265U, every such run in t |

### S.baseline: Baseline / comparison-period choice

| task | ver | P | F | A | stages | verdict | S/I | re | misreading |
|---|---|---|---|---|---|---|---|---|---|
| deck-preread-review | 2.0.0 | P1 | 2/5 | - | F p 2/5 |  | inf-3 |  | keeps the as-booked July close for West Addis and East Addis: S-20 1.8 and S-16 9.6 (the titles' and strips' o |
| deck-preread-review | 2.1.0 | P1 | 4/5 | - | F p 4/5 | AMBIGUOUS | inf-3 |  | keeps the as-booked July close for West Addis and East Addis: S-20 1.7 and S-16 9.5 (1.8 and 9.6 half up) inst |
| deck-preread-review | 2.2.0 | P1 | 0/15 | 0/15 | A f 0/10; p 0/5; F f 0/10; p 0/5 |  | inf-3 |  | keeps the as-booked July close for West Addis and East Addis: S-20 1.7 and S-16 9.5 (1.8 and 9.6 half up) inst |
| deck-preread-review | 2.3.0 | P1 | 0/15 | 0/15 | A f 0/10; p 0/5; F f 0/10; p 0/5 |  | inf-3 |  | keeps the as-booked July close for West Addis and East Addis: S-20 1.7 and S-16 9.5 (1.8 and 9.6 half up) inst |
| home-bp-diary-summary | 1.0.0 | P1 | 0/5 | 0/5 | A p 0/5; F p 0/5 |  | st-v1 |  | takes the consultation's planned start (from Sunday 6 September, once the D-14 diary is complete) as the first |
| home-bp-diary-summary | 2.0.0 | P1 | 0/5 | - | F p 0/5 |  | inf-2 |  | uses the planned start (6 September) as the first dose, so the two 5 September sessions (day 14, the day the f |
| home-bp-diary-summary | 2.1.0 | P1 | 0/5 | - | F p 0/5 |  | inf-3 |  | uses the planned start (6 September) as the day of the first tablet, so the two 5 September sessions stay in t |
| home-bp-diary-summary | 2.2.0 | P1 | 0/15 | 0/15 | A f 0/10; p 0/5; F f 0/10; p 0/5 |  | inf-3 |  | uses the planned start (6 September) as the day of the first tablet, so the two 5 September sessions stay in t |
| home-bp-diary-summary | 2.2.1 | P1 | 0/15 | 0/15 | A f 0/10; p 0/5; F f 0/10; p 0/5 |  | inf-3 |  | uses the planned start (6 September) as the day of the first tablet, so the two 5 September sessions stay in t |
| home-bp-diary-summary | 2.4.0 | P1 | 0/5 | - | F p 0/5 |  | inf-3 |  | uses the planned start (6 September) as the day of the first tablet, so the two 5 September sessions stay in t |
| home-bp-diary-summary | 2.5.0 | P1 | 0/5 | - | F p 0/5 |  | inf-3 |  | uses the planned start (6 September) as the day of the first tablet, so the two 5 September sessions stay in t |
| home-bp-diary-summary | 2.6.0 | P1 | 0/5 | - | F p 0/5 |  | inf-3 |  | uses the planned start (6 September) as the day of the first tablet, so the two 5 September sessions stay in t |
| home-bp-diary-summary | 2.7.0 | P1 | 0/5 | - | F p 0/5 |  | inf-3 |  | uses the planned start (6 September) as the day of the first tablet, so the two 5 September sessions stay in t |
| melody-lesson-results | 1.0.0 | P4 | 0/5 | 0/5 | A p 0/5; F p 0/5 |  | inf-4 |  | records a gain for Joy Dizon (4) and Marco Ramos (12), whose pre-test papers were sat on Tuesday 6 October, af |
| melody-lesson-results | 1.1.0 | P4 | 0/15 | 0/15 | A f 0/10; p 0/5; F f 0/10; p 0/5 |  | inf-4 |  | records a gain for Joy Dizon (4) and Marco Ramos (12), whose pre-test papers were sat on Tuesday 6 October, af |
| melody-lesson-results | 1.2.0 | P4 | 0/5 | 0/5 | A p 0/5; F p 0/5 |  | inf-4 |  | records a gain for Joy Dizon (4) and Marco Ramos (12), whose pre-test papers were sat on Tuesday 6 October, af |
| okra-manuscript-revision | 1.0.0 | P6 | 0/5 | 0/5 | A p 0/5; F p 0/5 |  | st-v1 |  | takes the register's published values from working draft v2 (the latest table, already carrying the new yields |
| profile-copy-claims-audit | 1.0.0 | P4 | 0/5 | 0/5 | A p 0/5; F p 0/5 |  | st-v1 |  | takes the quarter before the pilot started (April-June, the dashboard's 'Q2 2026, the quarter before the pilot |
| profile-copy-claims-audit | 2.0.0 | P2 | 0/5 | - | F p 0/5 |  | inf-3 |  | lists April-June 2026 as the before months (47.9%, the deck's and dashboard's figure) although the rebuilt bio |
| profile-copy-claims-audit | 2.1.0 | P2 | 0/15 | 0/15 | A f 0/10; p 0/5; F f 0/10; p 0/5 |  | inf-3 |  | lists April-June 2026 as the before months (the deck's and dashboard's quarter) although the rebuilt bio link  |
| profile-copy-claims-audit | 2.2.0 | P2 | 0/15 | 0/15 | A f 0/10; p 0/5; F f 0/10; p 0/5 |  | inf-3 |  | lists April-June 2026 as the before months (the deck's and dashboard's quarter) although the rebuilt bio link  |
| profile-copy-claims-audit | 2.3.0 | P2 | 0/15 | 0/15 | A f 0/10; p 0/5; F f 0/10; p 0/5 |  | inf-3 |  | lists April-June 2026 as the before months (the deck's and dashboard's quarter) although the rebuilt bio link  |
| profile-copy-claims-audit | 2.4.0 | P2 | 0/15 | 0/15 | A f 0/10; p 0/5; F f 0/10; p 0/5 |  | inf-3 |  | lists April-June 2026 as the before months (the deck's and dashboard's quarter) although the rebuilt bio link  |
| profile-copy-claims-audit | 2.5.0 | P2 | 0/5 | 0/5 | A p 0/5; F p 0/5 |  | inf-3 |  | lists April-June 2026 as the before months (the deck's and dashboard's quarter) although the rebuilt bio link  |
| profile-copy-claims-audit | 2.6.0 | P2 | 0/5 | 0/5 | A p 0/5; F p 0/5 |  | inf-3 |  | lists April-June 2026 as the before months (the deck's and dashboard's quarter) although the rebuilt bio link  |
| profile-copy-claims-audit | 2.7.0 | P2 | 0/5 | 0/5 | A p 0/5; F p 0/5 |  | inf-3 |  | lists April-June 2026 as the before months (the deck's and dashboard's quarter) although the rebuilt bio link  |
| profile-copy-claims-audit | 2.8.0 | P2 | 0/5 | 0/5 | A p 0/5; F p 0/5 |  | inf-3 |  | lists April-June 2026 as the before months (the deck's and dashboard's quarter) although the rebuilt bio link  |
| suitcase-cover-matrix-check | 1.0.0 | P4 | 0/5 | 0/5 | A p 0/5; F p 0/5 |  | st-v1 |  | takes 'before' from the first export in the folder (15 July, 232 active SKUs, which the deck's 'было' repeats) |

### T.clock: Clock or time-zone offset between sources

| task | ver | P | F | A | stages | verdict | S/I | re | misreading |
|---|---|---|---|---|---|---|---|---|---|
| deck-preread-review | 2.0.0 | P3 | 0/5 | - | F p 0/5 |  | inf-4 |  | takes N9 as Yonas's latest comment on the closing slide: sequence_notes holds N9 instead of N8 |
| deck-preread-review | 2.1.0 | P3 | 0/5 | - | F p 0/5 |  | inf-4 |  | takes N9 as Yonas's latest comment on the closing slide: sequence_notes holds N9 instead of N8 |
| deck-preread-review | 2.2.0 | P3 | 0/15 | 15/15 | A f 10/10; p 5/5; F f 0/10; p 0/5 | DEFECT | inf-4 |  | takes N9 as Yonas's latest comment on the closing slide: sequence_notes holds N9 instead of N8 |
| deck-preread-review | 2.3.0 | P3 | 0/15 | 0/15 | A f 0/10; p 0/5; F f 0/10; p 0/5 |  | inf-4 |  | takes N9 as Yonas's latest comment on the closing slide: sequence_notes holds N9 instead of N8 |
| hammamet-voucher-reissue | 2.0.0 | P3 | 1/5 | - | F p 1/5 |  | inf-7 |  | room 2: departure 15/09/2026 and 5 nights (tax 30 DT a head for Maghrebi guests) instead of 16/09/2026, 6 nigh |
| hammamet-voucher-reissue | 2.1.0 | P3 | 0/5 | - | F p 0/5 |  | inf-7 |  | room 2: departure 15/09/2026 and 5 nights instead of 16/09/2026 and 6 nights |
| hammamet-voucher-reissue | 2.2.0 | P3 | 3/5 | 0/5 | A p 0/5; F p 3/5 |  | inf-7 |  | room 2: departure 15/09/2026 and 5 nights instead of 16/09/2026 and 6 nights |
| kibo-budget-cap-review | 2.0.0 | P2 | 0/5 | - | F p 0/5 |  | inf-5 |  | takes the chat's 3% as the latest limit: ceiling 0.75 instead of 1.00, so Kessig Wolf Run (0.95), Solidarity o |
| kibo-budget-cap-review | 2.1.0 | P2 | 0/5 | - | F p 0/5 |  | inf-5 |  | takes the chat's 3% as the latest limit: ceiling 0.75 instead of 1.00, so Kessig Wolf Run (0.95), Solidarity o |
| kibo-budget-cap-review | 2.2.0 | P2 | 0/5 | - | F p 0/5 |  | inf-5 |  | takes the chat's 3% as the latest limit: ceiling 0.75 instead of 1.00, so Kessig Wolf Run (0.95), Solidarity o |
| kibo-budget-cap-review | 2.3.0 | P2 | 0/15 | 0/15 | A f 0/10; p 0/5; F f 0/10; p 0/5 |  | inf-5 |  | takes the chat's 3% as the latest limit: ceiling 0.75 instead of 1.00, so Titania's Song (0.82) and Solidarity |
| kibo-budget-cap-review | 2.3.1 | P2 | 0/15 | 0/15 | A f 0/10; p 0/5; F f 0/10; p 0/5 |  | inf-5 |  | takes the chat's 3% as the latest limit: ceiling 0.75 instead of 1.00, so Titania's Song (0.82) and Solidarity |
| kibo-budget-cap-review | 2.4.0 | P2 | 0/5 | 0/5 | A p 0/5; F p 0/5 |  | inf-5 |  | takes the chat's 3% as the latest limit: ceiling 0.75 instead of 1.00, so Titania's Song (0.82) and Solidarity |
| kibo-budget-cap-review | 2.5.0 | P2 | 0/5 | - | F p 0/5 |  | inf-5 |  | takes the chat's 3% as the latest limit: ceiling 0.75 instead of 1.00, so Titania's Song (0.82) and Solidarity |
| kibo-budget-cap-review | 2.6.0 | P2 | 0/5 | - | F p 0/5 |  | inf-5 |  | takes the chat's 3% as the latest limit: ceiling 0.75 instead of 1.00, so Titania's Song (0.82) and Solidarity |
| kibo-budget-cap-review | 2.7.0 | P2 | 0/5 | - | F p 0/5 |  | inf-5 |  | takes the chat's 3% as the latest limit: ceiling 0.75 instead of 1.00, so Titania's Song (0.82) and Solidarity |
| killzone-journal-review | 1.0.0 | P1 | 0/5 | - | F p 0/5 |  | inf-5 |  | keeps ny_am in the plan for the week of 9 November (chat stamps read as Tehran time, 15:52 = 12:22 UTC, before |
| killzone-journal-review | 1.1.0 | P1 | 3/5 | 0/5 | A p 0/5; F p 3/5 | BLIND-1.0 | inf-5 |  | keeps ny_am in the plan for the week of 9 November (chat stamps read as Tehran time, 15:52 = 12:22 UTC, before |
| killzone-journal-review | 1.2.0 | P1 | 3/5 | 0/5 | A p 0/5; F p 3/5 |  | inf-5 |  | keeps ny_am in the plan for the week of 9 November (chat stamps read as Tehran time, 15:52 = 12:22 UTC, before |
| sandwich-image-audit | 1.3.0 | P3 | 1/5 | 1/5 | A p 1/5; F p 1/5 |  | inf-4 |  | ZK-231 and ZK-235 counted live (and ZK-218 too when P2 is also missed) |
| timesheet-overtime-review | 2.0.0 | P2 | 0/5 | - | F p 0/5 |  | inf-4 |  | reads the unzoned chat as Cairo time, so Khaled's 11:00 e-mail (15:40 +0300 = 12:40 UTC) looks later than his  |
| timesheet-overtime-review | 2.1.0 | P2 | 0/5 | - | F p 0/5 |  | inf-4 |  | reads the unzoned chat as Cairo time, so Khaled's 11:00 e-mail (15:40 +0300 = 12:40 UTC) looks later than his  |
| timesheet-overtime-review | 2.2.0 | P2 | 0/15 | 0/15 | A f 0/10; p 0/5; F f 0/10; p 0/5 |  | inf-4 |  | reads the unzoned chat as Cairo time, so Khaled's 11:00 e-mail (15:40 +0300 = 12:40 UTC) looks later than his  |
| timesheet-overtime-review | 2.3.0 | P2 | 0/5 | 0/5 | A p 0/5; F p 0/5 |  | inf-5 |  | reads the unzoned chat as Cairo time, so Khaled's 11:00 e-mail (15:40 +0300) looks later than his 10:00 chat l |
| timesheet-overtime-review | 2.4.0 | P2 | 0/15 | - | F f 0/10; p 0/5 |  | inf-4 |  | reads the unzoned chat as Cairo time, so Khaled's 11:00 e-mail (15:40 +0300 = 12:40 UTC) looks later than his  |
| timesheet-overtime-review | 2.5.0 | P2 | 0/5 | - | F p 0/5 |  | inf-4 |  | reads the unzoned chat as Cairo time, so Khaled's 11:00 e-mail (15:40 +0300 = 12:40 UTC) looks later than his  |
| timesheet-overtime-review | 2.6.0 | P2 | 0/5 | - | F p 0/5 |  | inf-4 |  | reads the unzoned chat as Cairo time, so Khaled's 11:00 e-mail (15:40 +0300 = 12:40 UTC) looks later than his  |

### Q.aggregate: Aggregate / composition totals that tie but are wrong

| task | ver | P | F | A | stages | verdict | S/I | re | misreading |
|---|---|---|---|---|---|---|---|---|---|
| billiard-shift-audit | 2.0.0 | P1 | 0/5 | 0/5 | A p 0/5; F p 0/5 |  | inf-3 |  | keeps the composition as the POS line export shows it now; the bottle of the Tver novelty taken out of the nig |
| insurance-secrecy-register | 1.0.0 | P3 | 0/5 | - | F p 0/5 |  | inf-2 |  | keeps C07 (tagged insurance) in the register under the 2019 edition with a 500,000 top fine, although its driv |
| insurance-secrecy-register | 1.1.0 | P4 | 0/5 | - | F p 0/5 |  | inf-2 |  | keeps C07 (tagged insurance) in the register under the 2019 edition with a 500,000 top fine, although its driv |
| okra-manuscript-revision | 2.0.0 | P9 | 0/5 | - | F p 0/5 |  | inf-2 |  | lists M1NPK2, M1NPK1 and M0NPK2 (the names 3.4 prints) instead of the five combinations above the revised mean |
| okra-manuscript-revision | 2.1.0 | P9 | 0/5 | - | F p 0/5 |  | inf-2 |  | lists M1NPK2, M1NPK1 and M0NPK2 (the names 3.4 prints) instead of the five combinations above the revised mean |
| sandwich-image-audit | 1.1.0 | P3 | 0/5 | - | F p 0/5 |  | inf-3 |  | ZK-233 and ZK-235 stay on sale (ZK-233 live, ZK-235 needs_photo or live) |
| sandwich-image-audit | 1.2.0 | P4 | 0/5 | - | F p 0/5 |  | inf-3 |  | ZK-233 and ZK-235 stay on sale (ZK-233 live, ZK-235 needs_photo or live) |
| timesheet-overtime-review | 1.0.0 | P4 | 0/5 | 0/5 | A p 0/5; F p 0/5 |  | st-v1 |  | takes Sunday's lines from the coordinator's draft ('I drafted Sunday from your notes'), whose total ties to th |
| timesheet-overtime-review | 2.0.0 | P4 | 0/5 | - | F p 0/5 |  | inf-2 |  | books the whole 6:45-8:30 Sunday block on task 5512 (405 minutes) instead of 375, leaving the 19:10-19:40 dead |

### CV.order: Stacked rules applied in the wrong order

| task | ver | P | F | A | stages | verdict | S/I | re | misreading |
|---|---|---|---|---|---|---|---|---|---|
| billiard-shift-audit | 1.0.0 | P3 | 0/5 | 0/5 | A p 0/5; F p 0/5 |  | st-v1 |  | bills every started hour at the tariff in force when the session started (started hours x start-band rate), as |
| cafe-kitchen-schedule-revisions | 1.0.0 | P1 | 0/5 | 0/5 | A p 0/5; F p 0/5 |  | st-v1 |  | takes the corner zone as the depth of the perpendicular module alone (70 cm), without stacking its front proje |
| cafe-kitchen-schedule-revisions | 2.0.0 | P2 | 0/5 | - | F p 0/5 |  | st |  | takes the corner zone as the depth of the neutral corner table alone (70), so drawer C3 (near edge 72) is test |
| kibo-budget-cap-review | 1.0.0 | P4 | 0/5 | 0/5 | A p 0/5; F p 0/5 |  | st-v1 |  | looks the Table 2 band up on the USD price before conversion, so the 1.48-2.95 USD cards fall below the first  |
| moisturiser-price-screen | 1.0.0 | P1 | 0/5 | 0/5 | A p 0/5; F p 0/5 |  | st-v1 |  | applies the markdown first and takes the code's 120,000 toman off the marked-down price (the usual checkout or |

### ID.swap: Row or cell transposition between two records

| task | ver | P | F | A | stages | verdict | S/I | re | misreading |
|---|---|---|---|---|---|---|---|---|---|
| deck-preread-review | 1.0.0 | P2 | 0/5 | 0/5 | A p 0/5; F p 0/5 |  | st-v1 |  | reconciles the mix chart on its centre-label total and its four-product share (88.9%), both of which tie to th |
| melody-lesson-results | 1.1.0 | P2 | 1/15 | 14/15 | A f 9/10; p 5/5; F f 1/10; p 0/5 | GENUINE | inf-5 |  | keeps the printed lines: pupil 3 (Jasmine) 7 and pupil 4 (Joy) 10, instead of Jasmine 10 (her paper carries th |
| melody-lesson-results | 1.2.0 | P2 | 1/5 | 5/5 | A p 5/5; F p 1/5 |  | inf-5 |  | keeps the printed lines: pupil 3 (Jasmine) 7 and pupil 4 (Joy) 10, instead of Jasmine 10 (her paper carries th |
| melody-lesson-results | 1.2.0 | P5 | 0/5 | 0/5 | A p 0/5; F p 0/5 |  | inf-7 |  | keeps pupil 9 (Bea Lim) at the E / E / E printed on her line (30 points) instead of the E / NI / E she was giv |
| okra-manuscript-revision | 2.1.0 | P10 | 0/5 | - | F p 0/5 |  | inf-2 |  | keys rep 2's cells on the printed treatment row, so M0NPK0's plot mean is 2.70 kg instead of 2.80 and M0NPK1's |
| okra-manuscript-revision | 2.2.0 | P10 | 0/5 | 0/5 | A p 0/5; F p 0/5 |  | inf-4 |  | keys rep 2's cells on the printed treatment row, so M0NPK0's plot mean is 2.70 kg instead of 2.80 and M0NPK1's |
| okra-manuscript-revision | 2.2.0 | P11 | 0/5 | 0/5 | A p 0/5; F p 0/5 |  | inf-4 | re | round 2 is a fresh session that must work the yields again (the instruction no longer restates them); keyed on |
| okra-manuscript-revision | 2.2.0 | P13 | 0/5 | 0/5 | A p 0/5; F p 0/5 |  | inf-4 |  | round 3 works Table 4 through again from the sheet (the instruction restates the area basis, the price and the |
| pupil-tracker-term-summary | 1.1.0 | P2 | 9/15 | 7/15 | A f 4/10; p 3/5; F f 6/10; p 3/5 | BLIND-1.0 | inf-4 |  | keeps week 12 where it was printed: line 18 gets five A and loses its X ! ✓ ! X week (rate 90, Tier 1 instead  |
| pupil-tracker-term-summary | 1.2.0 | P2 | 2/5 | 0/5 | A p 0/5; F p 2/5 |  | inf-4 |  | keeps week 12 where it was printed: line 18 gets five A and loses its X ! ✓ ! X week (rate 90, Tier 1 instead  |

### Q.pack: Per-pack / per-pair pricing or box composition

| task | ver | P | F | A | stages | verdict | S/I | re | misreading |
|---|---|---|---|---|---|---|---|---|---|
| cnc-router-bom-reconcile | 1.0.0 | P5 | 0/5 | 0/5 | A p 0/5; F p 0/5 |  | st-v1 |  | reads the LM8UU (20000) and SK8 (28000) list prices as per piece and orders the v1 counts (12 each) at those p |
| cnc-router-bom-reconcile | 2.0.0 | P5 | 0/5 | - | F p 0/5 |  | inf-2 |  | orders 12 LM8UU and 12 SK8 at the list price, reading the unit as a piece; the price list sells both per 'pak' |
| cnc-router-bom-reconcile | 2.1.0 | P5 | 0/5 | - | F p 0/5 |  | inf-3 |  | orders 12 sets of LM8UU and 12 of SK8; rule 2.3 sends what the rules and the supplier's papers leave open (her |
| cnc-router-bom-reconcile | 2.2.0 | P5 | 0/5 | - | F p 0/5 |  | inf-5 |  | orders 12 sets of LM8UU and 12 of SK8; the price list sells both per set and prices one set ('harga berlaku un |
| cnc-router-bom-reconcile | 2.3.0 | P4 | 15/15 | 15/15 | A f 10/10; p 5/5; F f 10/10; p 5/5 | GENUINE-soft | inf-4 |  | orders LM8UU and SK8 one per piece (12 each); the desk's own filed lists, kept as payment records of two other |
| cnc-router-bom-reconcile | 2.4.0 | P4 | 5/5 | 5/5 | A p 5/5; F p 5/5 |  | inf-6 |  | orders LM8UU and SK8 one per piece (12 each); the desk's own filed lists, kept as payment records of two other |
| cnc-router-bom-reconcile | 2.5.0 | P4 | 5/5 | 5/5 | A p 5/5; F p 5/5 |  | inf-8 |  | orders LM8UU and SK8 one per piece (12 each); the desk's own filed lists, kept as payment records of two other |
| cnc-router-bom-reconcile | 2.6.0 | P4 | 14/15 | 11/15 | A f 7/10; p 4/5; F f 9/10; p 5/5 | GENUINE | inf-7 |  | orders LM8UU and SK8 one per piece (12 each); the desk's own filed lists, kept as payment records of two other |
| cnc-router-bom-reconcile | 2.6.1 | P4 | 15/15 | 9/15 | A f 6/10; p 3/5; F f 10/10; p 5/5 | GENUINE | inf-7 |  | orders LM8UU and SK8 one per piece (12 each); the desk's own filed lists, kept as payment records of two other |
| kibo-budget-cap-review | 1.0.0 | P5 | 0/5 | 0/5 | A p 0/5; F p 0/5 |  | st-v1 |  | takes a b10 row's price_usd as the price of one basic land, so 14 Forest and 12 Mountain cost ten times too mu |
| moisturiser-price-screen | 2.3.0 | P6 | 1/5 | 0/5 | A p 0/5; F p 1/5 |  | inf-3 |  | BN-2117 volume_ml 15 and price_per_100ml 1,240,000 instead of 45 (one card of three 15 ml tubes) and 413,333 |

### Q.taxincl: Tax-inclusive (or exclusive) basis with an indirect cue

| task | ver | P | F | A | stages | verdict | S/I | re | misreading |
|---|---|---|---|---|---|---|---|---|---|
| gst-workbook-answer-key | 1.1.0 | P3 | 0/5 | - | F p 0/5 |  | inf-2 |  | P-205 total 2,470 (CGST 1,235 / SGST 1,235). Truth: Deccan Bags' figures already contain the GST (its contact  |
| gst-workbook-answer-key | 1.2.0 | P3 | 5/5 | 0/5 | A p 0/5; F p 5/5 |  | inf-2 |  | P-205 total 2,470 (CGST 1,235 / SGST 1,235). Truth: Deccan Bags' figures already contain the GST, so each line |
| gst-workbook-answer-key | 1.3.0 | P3 | 14/15 | 0/15 | A f 0/10; p 0/5; F f 10/10; p 4/5 | GENUINE | inf-2 |  | P-205 total 2,470 (CGST 1,235 / SGST 1,235). Truth: Deccan Bags' figures already contain the GST, so each line |
| gst-workbook-answer-key | 1.4.0 | P3 | 11/15 | 0/15 | A f 0/10; p 0/5; F f 7/10; p 4/5 | GENUINE | inf-2 |  | P-205 total 2,470 (CGST 1,235 / SGST 1,235). Truth: Deccan Bags' figures already contain the GST, so each line |
| gst-workbook-answer-key | 1.4.1 | P3 | 10/15 | 0/15 | A f 0/10; p 0/5; F f 8/10; p 2/5 | GENUINE | inf-2 |  | P-205 total 2,470 (CGST 1,235 / SGST 1,235). Truth: Deccan Bags' figures already contain the GST, so each line |
| gst-workbook-answer-key | 1.5.0 | P3 | 1/5 | 0/5 | A p 0/5; F p 1/5 |  | inf-3 |  | P-205 total 2,470 (CGST 1,235 / SGST 1,235). Truth: Deccan Bags' figures already contain the GST, so each line |
| gst-workbook-answer-key | 1.6.0 | P3 | 0/5 | 0/5 | A p 0/5; F p 0/5 |  | inf-4 |  | P-205 total 2,470 (CGST 1,235 / SGST 1,235). Truth: Deccan Bags' figures already contain the GST, so each line |
| gst-workbook-answer-key | 1.7.0 | P3 | 11/15 | 0/15 | A f 0/10; p 0/5; F f 8/10; p 3/5 | GENUINE | inf-3 |  | P-205 total 2,470 (CGST 1,235 / SGST 1,235). Truth: Deccan Bags' figures already contain the GST, so each line |
| student-laptop-shortlist | 2.1.0 | P3 | 0/5 | - | F p 0/5 |  | inf-4 |  | prices L-401 at the quoted figure: 80,100 shortlisted instead of 94,518 out_of_budget (89,000 plus the 18% tax |
| student-laptop-shortlist | 2.2.0 | P3 | 0/5 | 0/5 | A p 0/5; F p 0/5 |  | inf-4 |  | prices L-401 at the quoted figure: 80,100 shortlisted instead of 94,518 out_of_budget (89,000 plus the 18% tax |
| student-laptop-shortlist | 2.3.0 | P3 | 0/5 | 0/5 | A p 0/5; F p 0/5 |  | inf-4 |  | prices L-401 at the quoted figure: 80,100 shortlisted instead of 94,518 out_of_budget (89,000 plus the 18% tax |
| suitcase-cover-matrix-check | 2.2.0 | P7 | 0/5 | - | F p 0/5 |  | inf-2 |  | bands the printed price: base 4 / mid 17 / top 39. Truth: the matrix price is the buyer's price on the card (V |
| suitcase-cover-matrix-check | 2.3.0 | P7 | 0/5 | - | F p 0/5 |  | inf-2 |  | bands the printed price: base 4 / mid 17 / top 39. Truth: the matrix price is the buyer's price on the card (V |
| suitcase-cover-matrix-check | 2.4.0 | P7 | 5/5 | - | F p 5/5 | UNCONFIRMED | inf-4 |  | bands the printed price: base 4 / mid 17 / top 39. Truth: the minutes' catalogue cover at 1790 is средний, whi |
| suitcase-cover-matrix-check | 2.5.0 | P7 | 5/5 | - | F p 5/5 | UNCONFIRMED | inf-5 |  | bands the printed price: base 4 / mid 17 / top 39. Truth: the minutes' catalogue cover at 1790 and store 12's  |

### S.inhand: Scope: already in hand / owned / in stock

| task | ver | P | F | A | stages | verdict | S/I | re | misreading |
|---|---|---|---|---|---|---|---|---|---|
| blockprint-winter-close | 1.0.0 | P2 | 0/5 | - | F p 0/5 |  | inf-3 |  | omits the five Camp rows that still sit in the lock-up (IMP-01 11, IMP-03 18, IMP-05 26, IMP-07 6, IMP-11 9):  |
| blockprint-winter-close | 1.1.0 | P2 | 0/5 | - | F p 0/5 |  | inf-3 |  | omits the five Camp rows that still sit in the lock-up (IMP-01 11, IMP-03 18, IMP-05 14, IMP-07 6, IMP-11 9):  |
| cnc-router-bom-reconcile | 2.4.0 | P5 | 2/5 | 0/5 | A p 0/5; F p 2/5 |  | inf-4 |  | orders the controller kit (KIT-ESP4 x1, Rp359.000) from the notes' line; on Saturday 10 Oct another member's p |
| cnc-router-bom-reconcile | 2.5.0 | P5 | 3/5 | 0/5 | A p 0/5; F p 3/5 |  | inf-4 |  | orders the controller kit (KIT-ESP4 x1, Rp359.000) from the notes' line; on Saturday 10 Oct another member's p |
| cnc-router-bom-reconcile | 2.6.0 | P5 | 10/15 | 0/15 | A f 0/10; p 0/5; F f 7/10; p 3/5 | GENUINE | inf-4 |  | orders the controller kit (KIT-ESP4 x1, Rp359.000) from the notes' line; on Saturday 10 Oct another member's p |
| cnc-router-bom-reconcile | 2.6.1 | P5 | 9/15 | 0/15 | A f 0/10; p 0/5; F f 6/10; p 3/5 | GENUINE | inf-4 |  | orders the controller kit (KIT-ESP4 x1, Rp359.000) from the notes' line; on Saturday 10 Oct another member's p |
| kibo-budget-cap-review | 2.5.0 | P5 | 0/5 | - | F p 0/5 |  | inf-2 |  | lists Kibo, Uktabi Prince (7.67 USD, the draft's priciest card) in over_ceiling. The ceiling in method section |
| kibo-budget-cap-review | 2.6.0 | P5 | 0/5 | - | F p 0/5 |  | inf-2 |  | lists Kibo, Uktabi Prince (7.67 USD, the draft's priciest card) in over_ceiling. The ceiling in method section |
| kibo-budget-cap-review | 2.7.0 | P5 | 0/5 | - | F p 0/5 |  | inf-2 |  | lists Kibo, Uktabi Prince (7.67 USD, the draft's priciest card) in over_ceiling. The ceiling in method section |

