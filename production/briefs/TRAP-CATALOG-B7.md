# B7 trap catalogue: what actually defeats Fable 5.1 and GPT-6 Astra (2026-10-15)

> **History (2026-10-15).** Superseded as instructions by `AUTHOR-BRIEF-B8.md` (its §1, §4 and §7) and, for the templates, by the trap library; kept for the measurements and reasoning behind its rules. Paths below are the old workspace layout (`$W/research/batch4/...`): in this repo the tools are in `production/tools/`, the briefs in `production/briefs/`, the templates in `production/templates/`, and trap modes come from `production/traps/TRAP-LIBRARY.md`.

This catalogue is binding for every new or retuned b6/b7 task. A decisive trap must be built from a template below and declared in `authoring/traps.json` as `"template": "T1".."T8"` (or `"L1".."L5"`, see §6). `design_lint.py` enforces this.

**Evidence base**
- `research/INTERNAL-trap-evidence.md`: 1,129 premise units across 45 tasks; 7,805 Fable and 4,880 Astra premise-runs.
- `research/TRAJ-loopholes.md`: 521 failing premise-runs classified from the models' own words.
- `research/LIT-A-reasoning-failures.md` and `research/LIT-B-professional-benchmarks.md`: published evidence, 2023–2026.
- The v5/v6 dial rounds, logged in `research/batch4/b6/genuineness.md`.

## 1. Seven facts that decide trap design

1. **Models read everything.** In 519 of 521 failing premise-runs the deciding anchor was in the model's own tool output before it wrote the deliverable. Failures are reconciliation failures. Hiding, burying and volume do nothing.
2. **Stated rules never bite:** Fable 0/810, Astra 0/720. A trap works only through an inferred trigger fact.
3. **Inferring to fill a gap dies; reversing a record bites.** Fable infers freely and fills gaps correctly, but it will not overrule a record. Every round-2 trap that only narrowed a scope or filled a gap was 0/5 (kibo, ats, timesheet and pathway scope or temporal traps).
4. **The two models fail differently.**
   - **Fable** notices the conflict and overrules the evidence in 43% of its misses. It flags the conflict, writes an "If X, then Y" hedge, and commits to the record, often citing a real rule that does not cover the case (the rule shield).
   - **Astra** is silent in 83% of its misses: it joins on the key, or applies a default convention without mentioning the evidence. When it does notice, it credits both readings (union) or answers "not determinable".
5. **A careful blind reader separates genuine traps from unfair ones.**
   - When a printed current form or governing table states the opposite of the answer, the blind reader misses too, so the trap is unfair. Examples: home-bp P5 and suitcase P7, both at 2.4–2.7.
   - When no sentence gives the record priority, blind readers reverse it.
6. **A miss rate from 5 runs is noise.** The same unchanged premise text measured 2/5 and then 5/5 (home-bp P3, profile-copy P6). Use pilots only to triage; decide on 10×2 finals.
7. **Treat any unaudited 100% as ambiguity until a blind reader says otherwise.** Six validity fixes took a 80–100% bite to 0%.

## 2. Proven templates (measured here, audited genuine)

Rates are pooled finals unless marked. "Band" means 20–80%. Read each template's source premise (VALIDATION.md, DIAL.md, the fixture lines) before you build it.

| ID | Mechanism | Fable | Astra | Band behaviour | Sources |
|---|---|---|---|---|---|
| **T1** | Keying slip: a record keyed under an ID it does not belong to; the true owner appears only by description in 2+ documents from different parties | 60–100% (10 audited tasks) | 60–100% | Often flat (10 of 19 units ≥ 90%). One by-the-way anchor per dial notch. | ats 1.1.0 P2, pathway 2.3.0 P2, gst 1.7.0 P1, cnc 2.6.1 P3, kibo 2.3.1 P3 |
| **T2** | Convention set only by worked figures in the governing document (truncate vs half-up, per-bill vs per-line, which end of a range) | 0–70% | 80–100% with one discriminating figure | Astra flips on figure count: one figure gives ~100%; two can give anywhere from 3/15 (deck P4) to 14/15 (profile P5) depending on placement; a figure inside the entry that defines the graded rate gives 0 | gst 1.7.0 P2, deck 2.3.0 P4, brightwater P4, profile 2.4.0 P5 |
| **T3** | Quantity basis cued only ON or ABOUT the record: tax-inclusive bill, price per pair or pack set against a received tally | tax 65% (52/80); pack 100% | tax 0%; pack 60% with a tally | Bimodal; the cue must sit on the record itself, never in a caption next to the figures | gst 1.7.0 P3, cnc 2.6.1 P4 |
| **T4** | Already in hand: a "still needed" rule, with possession shown by a technical bridge in a first-hand record | 60% (24/40) | 0% | Dies if possession is stated (kibo) | cnc 2.6.1 P5 |
| **T5** | Misfiled note: filed under one item, its content can only be about another | 40% (deck); ats 1.5.0 pilot 0/5 | 0% (deck); ats 1.5.0 pilot 2/5 | Under test in v6 (ats, pathway, timesheet) | deck 2.5.0 P5 |
| **T6** | Which edition or rate applies, by the real date; two sources of SIMILAR authority disagree, and first-hand dated records resolve it | 50% per step | 90–100% (cafe 2.3.0) | Dies when a mapping rule is stated (timesheet); unfair as an informal remark against an official form (home-bp) | cafe 2.3.0 P1/P6 |
| **T7** | Convention from two worked figures supplied by different parties | 40% | 10% | | cafe P11 |
| **T8** | Changed premise received before issue | 20% | 0% | Filler only | cafe P8 |

**T9 Rule-scope shield (added 2026-10-15 from the melody re-audit).**
- A real rule governs a NEIGHBOURING value, e.g. guide §4 governs the gain.
- The default over-applies it to the graded value, e.g. a late pupil's pre-test is left out.
- Three or more lines (handover, record sheet, instruction) show the graded value stands.
- Measured on melody 1.1.0: Fable 8/10, Astra 0/15, GENUINE per the re-audit.
- What kills it: a stated clarification ("only the gain leaves it out"). In 1.2.0 Fable dropped to 1/5.
- This is the "L-shield" loophole from TRAJ.

**Astra-only shapes worth reusing:**
- A filed column copied without deliberation: deck N8, Astra 60/60, Fable 5/60.
- A line transposition settled by first-hand descriptions: melody P2, Astra 14/15.

**Fable-only shapes:**
- Units or scale shown only by incidental remarks: profile P7, Fable 57/65, Astra 0/65.

## 3. The loopholes behind the templates (TRAJ §3)

| Loophole | What the model does | Fable | Astra | Exploited by |
|---|---|---|---|---|
| **L-record** | The key or record beats the remark | 211/330 misses | 143/210 misses | T1, T3, T5, T6 |
| **L-join** | Two anomalies are reported but never joined (an orphan record plus a missing record) | pathway 19/19 | 10/10 | T1 |
| **L-shield** | Cites a real rule that does not cover the case | 50 of 142 voiced misses | rare | Place a tempting rule and scope it away from the trapped variable |
| **L-default** | Half-up rounding, per-piece prices, the floor of a rule | some | most of its misses | T2, T3 |
| **L-absorb** | Makes the anchor fit the default ("still leaves the half metre") | some | some | Pair a constraint anchor with an identity anchor the default cannot satisfy |
| **L-threshold** | Wants an explicit statement before inferring | keeps the record | abstains | Grade "not determinable" as wrong only when the files settle it |
| **L-union** | Credits both readings; no conservation check | rare | cnc 10/10, ats 5/10 | Grade the removal side against a conserved total |

## 4. The recipe: make the model reverse a record

What separates passing runs from failing ones (TRAJ §4) also tells you how to build a trap that stays genuine.

**Passing runs used:**
- an impossibility, not just a likelihood;
- a mechanism for the error;
- a unique match on content;
- a third anchor that witnesses the event.

**Recipe:**
- **The record:** a structured, official-looking record (key, filing, log entry, export row) gives the default answer.
- **The anchors:** two or more anchors from different parties make the record impossible, not merely unlikely. Each anchor sits in a document read for another purpose.
- **Withheld:** no sentence gives the record priority, and no sentence states the error's mechanism (no visible transposition, no "page-number slip"). The model has to supply the mechanism itself.
- **Dials:** each by-the-way anchor that witnesses the event, or a unique content match, is one notch toward solvable. For Astra, change the KIND of evidence (e.g. a receipt line), not the amount.
- **Conservation:** when an item could be credited to two places, grade both sides against a conserved total, so a union answer loses.
- **Shields:** if a tempting rule exists, scope it explicitly away from the trapped variable. Fable will cite it, and the audit can show the citation is a misreading.
- **Never use** a printed current form, legend or governing table that states the opposite of the answer. That is unfair, and blind readers miss it too.

## 5. Do not use as a decisive trap

**Dead: at most 5% missed by both models over 20+ runs each.**
- stated rules or conventions (0/115, 0/55);
- stacked-rule order;
- stored vs derived figure;
- near-twin identities (0/245, 1/150);
- aggregate totals that tie;
- answerability;
- coverage and counting unit;
- restated figure supersedes the first issue (0/125, 0/65), in its labelled form;
- event-date keying (3/405, 2/185);
- first-hand fact over record, as a gap filler;
- population reshaping (13/515, 10/280);
- baseline choice;
- caption-only rules;
- changed premise as a decisive trap;
- clock offset (overused, and near-dead once made determinate);
- breadth or volume;
- decoys and pointers.

**Dead in the v5 rounds:** scope "already owned" stated outright, a training course listed as a job, a payroll cycle, a leaver inferred from returned kit, a slip handed in before the close, and figures in thousands with a cross-reference.

**Bimodal: missed either never or always, avoid as a lead trap:**
- T3 tax or pack cues placed in non-governing documents;
- any hidden fact that contradicts an official form;
- a convention with figures outside the population ("not in the matrix, so I ignored it").

## 6. Literature-backed candidates (L-templates): untested here, so pilot first

Each must follow the §4 recipe. `design_lint` warns on an L-template until it is promoted.

| ID | Mechanism | External evidence | Note for our harness |
|---|---|---|---|
| **L1** | A later restatement of a figure replaces the first-reported value; agents stop at "the first numerically plausible instance" | OfficeQA Pro (Databricks 2026, company-reported): Claude Fable 5 and GPT-5.5/5.6 in Claude Code and Codex average 37.5% | The labelled form is dead here (0/125). Build it as a record reversal: the first instance is an official-looking table, and the revision appears only in a later dated source of similar authority |
| **L2** | An older edition governs by the event's own date (the model defaults to the newest version) | arXiv 2608.14610: Opus 4.6 at max effort scores 0.014 when the older version governs; TIDE (2608.08512) misses 25–36% | Our home-bp P5 was unfair because a current printed form stated the opposite. Use authority parity (T6) |
| **L3** | Wrong anchor event starts a period or deadline | arXiv 2608.15270: gpt-5.4 got 3 of 6 deadlines exact; errors "from choosing which event the period starts from" | Two candidate start events, each recorded by a different party |
| **L4** | Fiscal vs calendar period mapping | OfficeQA, where an agent read 8 fiscal years as calendar years | A source labelled only "FY" figures, with the fiscal-year start shown by a worked figure |
| **L5** | Cumulative (year-to-date) vs period figures | FinIndices (2607.28661): Claude-4.5 12.79, GPT-5.4 15.12 with no hint | Under test: deck 2.8.0 P6 |

Reasoning models now solve these, per the literature and our lab: irrelevant "NoOp" clauses, context vs memory conflicts, literal retrieval, two-hop and reversal curses, premise order, long aggregation, date arithmetic and anchoring.

## 7. Task composition rule (B6v6 / B7)

- **Three decisive traps from different families:**
  - one Astra-proven template (T2, a T1 copied-column shape, or T3 pack with a tally);
  - one Fable-proven template (T3 tax, T4, T5, T6, or a T1 shape Fable misses);
  - a T1 slip dialled to about 40–60%.
- Fillers carry at most 5 points each. Free share is at most 0.40, with at least 8 graded checks summing to 100.
- No cascade: downstream checks grade the agent's own upstream answer.
- Same-family anchors go in different files. A new note next to an existing anchor primes it: gst P1 went from 11/15 to 0/5 with byte-identical text.
- **Batch spread:** no lead template above about 25% of the batch. T1 currently leads most shipped tasks, so new tasks should lead with T2, T3, T4, T5 or T6.

## 8. Measurement protocol

1. Run the pilot (5×2) only after the `b6ctl preflight` key check passes. It filters out dead keys; it does not estimate miss rates.
2. Run a blind reader (`b6ctl blind-prep` and `blind-grade`) on every trap missed 5/5 by either model, before any dial.
3. Run the final (10×2) for any version whose pilot shows at least 1 pass and at least 1 trap in band on some model.
4. Apply one dial notch at a time, and keep Astra-aimed figures fixed.
5. Run the §14 audit, then harbor, then the zip. The order is in `research/batch4/b6/tools/README-FLOW.md`.
