# EXTERNAL: what defeats frontier agents on document work, read for the trap library

Compiled 2026-10-15 for the B8 trap library. Research only: nothing was launched, and no task tree, key or pool was touched. This note documents `traps/modes-external.json` (schema `traplib/1`, source `external`, 14 modes, L1–L14, all `literature`).

## How to read this

**Method.** Every source below was opened on 2026-10-15: the arXiv abstract page, the arXiv HTML full text, or the publisher's page. A number appears only if I read it there. Where a search snippet claimed something the page did not show, the claim is dropped (§6). Quotes are verbatim and at most 25 words; everything else is paraphrase.

**Provenance flags.** Each source carries one of these flags:
- **company-reported**: a vendor blog, or a paper whose authors sell the product or benchmark;
- **preprint**: arXiv only;
- **accepted**: a venue named on the paper's own page (workshop acceptances are labelled as such).

**Source vs inference.** "Finding" lines report what the source says. "Maps to" lines and every rating are my inference, made against our measurements (TRAP-CATALOG-B7, INTERNAL-trap-evidence, TRAJ-loopholes).

**Relation to earlier passes.** LIT-A covered reasoning-failure papers and LIT-B covered professional benchmarks. This pass does three things:
- re-verifies the sources behind L1–L5;
- reads the 2026 benchmarks that test Claude Fable 5 and GPT-5.6 Sol directly (APEX-Accounting, OfficeQA Pro V2, WorkBench Revisited, FrontierFinance);
- reads the agentic, versioned-document, conflict and false-premise benchmarks that LIT-B listed only by snippet.

**Transfer warning.** Most benchmark difficulty comes from retrieval, PDF parsing, long context, tools, formatting and multi-turn users. None of these exists in our harness: the agent `cat`s every file, computes in Python, and has no user to talk to. Only errors **upstream of the arithmetic** carry over: picking the wrong record, perimeter, version, vintage or premise.

---

## 0. Headline

1. **The 2026 frontier error analyses agree with TRAJ fact 1.**
   - In APEX-Accounting, tool-use failures are 0% for every model. Reasoning failures are 79% of Claude Fable 5's annotated failures and 75% of GPT-5.6 Sol's.
   - The paper's summary: "Top models reliably find the right inputs; they make mistakes when applying accounting judgment and multi-step logic to them."
   - The pattern it documents: right documents, right intermediates, then the wrong **basis, source or authorization**.
2. **Item designs that beat Fable 5 or GPT-5.6 Sol in a published 2026 study:**
   - **Component figure reported as the entity total.** Both Fable 5 and GPT-5.6 Sol made this error on the same APEX-Accounting task. → **L7**
   - **Revised figure not retrieved.** OfficeQA Pro V2 reports this for Claude Code (Fable 5, Opus 4.8) and Codex (GPT-5.5, GPT-5.6 Sol). → **L1**
   - **Temporal reconciliation as a concept changes name, schema, unit, time basis or aggregation.** Also from OfficeQA Pro V2. → **L10, L4**
   - **An internal report treated as the authorizing instrument.** Fable 5 released a restricted $15,000 balance this way (APEX-Accounting). → **L6**
   - **A contracted fixed denominator recomputed.** GPT-5.6 Sol shrank a fixed room-night base (APEX-Accounting). → **L12**
3. **The Claude line leans on defaults and priors.**
   - Opus 4.6 at max effort scores 0.014 on old-version legal cases, against 0.820 on new-version cases (2608.14610).
   - 26.7% of Fable 5's parses target self-produced domains, about twice the rate of Opus 4.8 (FrontierFinance).
   - This supports aiming L6 and L8 at Fable.
4. **The OpenAI line follows the framing and the most salient record.**
   - "OpenAI o-series models resist distractors but overfit to problem framings" (Gema et al.).
   - On LegalBench rule application, GPT-5.5 scores below GPT-4o (66.4% vs 76.4%).
   - This fits our TRAJ picture of Astra: silent key joins and silent defaults.
5. **Most published difficulty is dead here.** That covers long-context retrieval, absence detection, unanswerable items, parsing, formatting, stated multi-condition rules, policy-violating writes and multi-turn drift (§3).

---

## 1. The library at a glance

| id | mechanism | family | aimed at | strongest external source | note |
|---|---|---|---|---|---|
| L1 | Later restatement replaces the first-reported figure (record reversal) | revision_supersession | both | OfficeQA Pro / Pro V2 | labelled form is dead (D8: 0/125, 0/65) |
| L2 | Older edition governs by the event's own date | authority_selection | both | 2608.14610; TIDE | sibling of T6; the `version_in_force` alias belongs to T6 |
| L3 | Wrong anchor event starts a period or deadline | temporal_anchor | astra | 2608.15270 | needs a defining sentence (trigger_event was contested) |
| L4 | Fiscal vs calendar period mapping | temporal_anchor | unknown | OfficeQA blog; Pro V2 | the payroll-period pilot died on Fable 0/25 |
| L5 | Cumulative (YTD) vs period figures | aggregation_basis | both | FinIndices | **promoted**: internal T14 lists L5 as an alias, so this evidence merges into T14 |
| L6 | A document *about* a change applied as the change in force | authority_selection | fable | APEX-Accounting (Fable 5) | new |
| L7 | Figure scope: a component figure taken for the whole | aggregation_basis | both | APEX-Accounting (Fable 5 and GPT-5.6 Sol) | new |
| L8 | As-of vintage: a later restatement must not reach a past test | revision_supersession | fable | TIDE; 2608.14610 | new; inverse of L1 |
| L9 | The request presupposes a fact the records refute | other | both | BrokenMath; PCBench; TIDE | new; high dead-risk (see hazards) |
| L10 | Series continuity across a reclassification | identity_resolution | both | OfficeQA Pro V2 | new |
| L11 | One event under two document numbers (double count) | aggregation_basis | astra | SpreadsheetBench 2; FinBalance | new; T10 is the same-key sibling |
| L12 | A by-design irregularity "corrected" | convention_inference | astra | APEX-Accounting (GPT-5.6 Sol) | new |
| L13 | Coincident-amount match beats the content match | identity_resolution | astra | entity matching; FinBalance | new; evidence is on weaker models |
| L14 | Counterparty perspective inversion (sign) | quantity_basis | astra | FinanceBench; SpreadsheetBench 2 | new; weakest support |

Every recipe follows TRAP-CATALOG-B7 §4:
- a structured record gives the default answer;
- two or more anchors come from different parties;
- no sentence gives the record priority;
- the mechanism of the error is withheld;
- dials are one by-the-way anchor or a change in evidence kind at a time;
- graded totals are conserved, so a union answer loses;
- any tempting rule is scoped away from the trapped variable.

---

## 2. Benchmarks and papers

### 2.1 Office and finance document benchmarks

#### OfficeQA (blog, 2025-12-09), OfficeQA Pro (arXiv 2603.08655, 2026), OfficeQA Pro V2 (blog, 2026-08-06)

**Provenance.** Databricks authors throughout. The blogs are **company-reported**; the Pro paper is a **preprint**.

**What it measures.** Grounded questions over about 89,000 pages of U.S. Treasury Bulletins, with answers scored exactly.

**Hardest item designs, and why agents fail them:**
- **Revised values.** The medium V2 item requires "the latest revised prior-year column". The hard item requires "only the latest reported figures for each year". The Pro paper's error analysis says agents converge "on the first numerically plausible instance retrieved".
- **Concepts that change over time.** The V2 post says "the same financial concept may change in name, location, table schema, unit, time basis, and level of aggregation". Reporting also moved from calendar to fiscal years.
- **Period basis.** In the original post, an agent took fiscal-year values for 8 years where calendar years were needed. Its forecast was off by $286,831 million (31.6%). Another agent used the June 2010 bulletin where the September 2010 publication was correct ($21 million off). The post does not say which agent made which error.
- **Source scope.** On a federal debt question, models used OMB figures instead of the Treasury Bulletin.
- **Precision.** A majority of remaining Pro errors are final-answer precision, for example rounding too early.
- **Formula choice.** Sample instead of population variance.

**Numbers:**
- **Pro (exact accuracy, 0% error).** Claude Opus 4.6: 48.12% on full PDFs, 54.14% parsed, 66.92% with oracle pages parsed. GPT-5.4: 36.09%, 56.39%, 65.41%. Agents on the corpus average 34.1% (abstract).
- **V2 (out-of-the-box agents).** The intro gives a 37.5% average; Section 1 gives 26.0% across five models. The post does not reconcile the two. GPT-5.6 Sol on Codex scores 33.3%, Sonnet 5 on Claude Code 15.6%. Fable 5 averaged about $37 per rollout, "prone to looping attempts to parse many documents".

**Maps to:**
- L1 (revised figure)
- L4 (fiscal vs calendar)
- L10 (concept changes)
- L7 (entity scope)
- T2 (precision and formula convention)

**Rejected.** Parsing errors account for a large share of the failure budget, and our text fixtures remove them, so the OfficeQA rates are an upper bound for us.

#### APEX-Accounting (arXiv 2607.27189, 2026)

**Provenance.** Mercor with Ramp: **company-authored preprint**.

**What it measures.** 160 month-end close tasks in 10 synthetic companies:

| task type | tasks |
|---|---|
| reconciliation | 61 |
| data entry | 26 |
| variance analysis | 28 |
| schedules and accruals | 45 |

**Worked failures (the paper gives few details for most):**
- **Fable 5, authorization.** It "treats a program director's report as written donor authorization" and released a restricted $15,000 balance.
- **Fable 5 and GPT-5.6 Sol, perimeter.** Both reported a new lease's square footage as the entity-wide total.
- **GPT-5.6 Sol, fixed base.** It shrank a fixed room-night denominator.
- **Muse-Spark-1.1, re-normalized weights.** It computed the correct allocation, then re-normalized the weights.
- **GPT-5.6 Sol and Muse-Spark-1.1, cost source.** Both posted a WIP-to-finished-goods variance from the wrong actual-cost source.
- **Muse-Spark-1.1, unopened addendum.** It reported a zero balance in the capitalisation account as evidence that no adjustment was needed. It never opened the cost-recovery addendum that required capitalising $23,500 of attorney fees.

**Numbers:**
- **Mean Criteria@3.** Fable 5 (adaptive, max) 56.4%; GPT-5.6 Sol (pro, max) 51.5%; Opus 4.8 48.0%; Gemini 3.1 Pro 32.4%.
- **Pass^8.** Best is 2.6% (GPT-5.6 Sol).
- **Failure classes.** Reasoning failures are 79% for Fable 5 (n=24) and 75% for GPT-5.6 Sol (n=28). Information gathering is 13% and 7%. Tool use is 0% for both.

**Maps to:**
- L6 (authorization from a report)
- L7 (perimeter)
- L12 (fixed base, re-normalization)
- T6 or authority_selection (cost source)

**Rejected:**
- The unopened-addendum failure is information gathering. Our agents read every file.
- The capitalise-vs-expense rule is stated, so it is dead as a decider.
- Internally the `composition_tie` hypothesis already cites APEX-Accounting at ≤ 9.5%, and its lab (L22) died.

#### FinIndices (arXiv 2607.28661, 2026)

**Provenance.** **Preprint**.

**What it measures.** Metric computation over uncropped financial statements up to 32K tokens. The synthesis plants adversarial traps:
- **distractor injection**: adjacent periods and parent-company statements;
- **information deficiency**: the correct answer is "Insufficient information".

**Hardest designs.** Formula hints are withheld, and the period caliber must be inferred.

**Logged model failures:**
- a 2021Q3 *YTD* profit used as the base of a single-quarter YoY: 202.25% vs 58.49%;
- ROA on ending instead of average assets: 1.208% vs 1.217%;
- Gemini substituting a beginning-balance column inside a table: −3.25% vs −4.22%;
- total equity used where equity attributable to the parent was required: 99.8 vs 97.0.

**Numbers (Table-Index accuracy, with hints → without):**

| model | with hints | without hints |
|---|---|---|
| Claude-Opus-4.8 | 65.61 | 38.85 |
| GPT-5.5 | 66.88 | 34.18 |
| GPT-5.4 | 65.61 | 31.21 |
| Gemini-3.1-Pro | 70.70 | 38.22 |

The caliber-alignment axis without hints is lower still: Claude-4.5 12.79, GPT-5.4 15.12, Gemini-3.1 23.26.

**Maps to:**
- L5, now internal T14 (YTD base)
- L7 (parent-attributable vs total)
- L10 (the temporal+domain axis)
- T2 (average vs ending as a worked-figure convention)

**Rejected.** The information-deficiency trap is answerability, which is dead here (D6: 0/75, 1/35).

#### FinBalance (arXiv 2606.15949, 2026)

**Provenance.** **Preprint**.

**What it measures.** Agents turn raw invoice, statement and contract bundles into cited journal entries and a balance sheet. Some records are deliberately inconsistent and must be flagged.

**Hardest designs:**
- **Linking documents.** In one ablation, 52% of correct entries cited the wrong documents.
- **Multi-step dependencies.** Exact balance-sheet accuracy falls from 88% at level 1 to 0% at level 5.
- **Forced reconciliation.** Ledger feedback raised exact accuracy by 30–33 pp but cut contradiction detection. Claude Haiku 4.5 lost 52 pp: models forced a reconciliation instead of flagging the conflict.

**Numbers.** Best exact balance sheet is 46% (GPT-5). The other models tested are Gemini 3 Flash, DeepSeek, Qwen 3 and Claude Haiku 4.5, none of them our calibration models.

**Maps to:**
- L11 (one event, two documents)
- L13 (forced plug)
- L9 (pressure to make things tie)

#### FinAuditing (arXiv 2510.08886, 2025)

**Provenance.** **Preprint**.

**What it measures.** Taxonomy-aware checks on real XBRL filings.

**Hardest designs.**
- Models "rely on surface-level semantic similarity".
- They miss CashAndCashEquivalents used where only Cash is allowed.
- They miss aggregate tags such as AssetsCurrent where components are required.

**Numbers:**
- semantic matching (FinSM): Hit Rate@20 below 13% for every model;
- relation extraction (FinRE): GPT-4o 91.82%;
- mathematical reasoning (FinMR): best 13.86% (Fin-o1-14B).

**Maps to.** L7 (perimeter and granularity) and L10.

**Rejected.** The retrieval-heavy FinSM setting does not transfer.

#### SpreadsheetBench (arXiv 2406.14991; NeurIPS 2024 spotlight) and SpreadsheetBench 2 (arXiv 2606.29955; the repo lists NeurIPS 2026)

**What they measure:**
- **v1:** 912 real forum questions on non-standard, multi-table sheets, judged online-judge style.
- **v2:** 321 end-to-end workflows covering financial modelling, debugging and visualisation.

**Hardest designs.** Debugging, with no hint of the defect type or location. Ten seeded defect types, including:
- Double Counting
- Incorrect Sign
- Unit Mismatch
- Incorrect Average
- Relative vs Absolute References

The dominant failure classes for Opus 4.6 are Insufficient Inspection and Wrong Target Selection. Examples:
- a Debt/Equity numerator copied from an adjacent ratio, about 2× too large;
- a banking model whose formulas were "textbook-correct but the cell references did not match the actual row layout";
- an agent claiming "the chart XML confirms all 4 series are present" against its own tool output.

**Numbers (overall / debugging):**

| model | overall | debugging |
|---|---|---|
| Opus 4.6 | 34.89% | 12.00% |
| GPT-5.2 | 26.79% | 8.00% |
| Gemini 3.1 Pro | 23.68% | 7.00% |

**Maps to:**
- L11 (double counting)
- L14 (sign)
- T2 (textbook prior over local layout)

**Rejected.** Cell-reference mechanics are a coding-like skill, not a document trap.

#### FinanceBench (arXiv 2311.11944, 2023) and DocFinQA (arXiv 2401.06915)

**Provenance.** Both are **preprints**.

**What they measure.** QA over filings. DocFinQA stretches FinQA's contexts from under 700 words to 123k words.

**Hardest designs.** FinanceBench's wrong answers include "the wrong direction for an effect (e.g. reporting negative growth when it is actually positive)". GPT-4-Turbo with a shared vector store got 81% of questions wrong or refused.

**Maps to.** L14 (direction). The rest is retrieval.

**Rejected.** Long-context retrieval is dead here.

#### FrontierFinance (arXiv 2608.11683, 2026)

**Provenance.** **Preprint**. The leading system is the authors' own (Samaya), so treat the ranking as **company-reported**.

**What it measures.** 220 analyst research queries scored against 11,543 rubrics.

**Numbers:**
- Samaya's system 56.0%, Fable 5 49.2%, Kimi K3 46.4%.
- The hardest use cases are Screening & Discovery (33%) and Sector/Macro (39%).
- "26.7% of Fable 5's parses target self-produced domains." That is roughly twice the rate of Opus 4.8 and Kimi K3, and every other system is under 5%.

**Maps to.** Supports aiming prior-driven modes (L2, L6, L8) at Fable. The paper does not interpret the 26.7% this way; that reading is my inference.

**Rejected.** Open-ended web research has no analogue here.

#### FinVerBench (arXiv 2605.29586, 2026)

**Provenance.** Single-author **preprint**.

**Finding.** "nine of fourteen complete LLM runs produce 95-100% false positives on clean statements". Rendering and rounding move measured recall between 79.0% and 100.0%.

**Maps to.** The flip side of L12. It matters only in review deliverables, where it becomes a hazard rather than a lever.

#### TaxCalcBench (arXiv 2507.16126, 2025)

**Provenance.** Column Tax: **company-authored preprint**.

**Findings:**
- Models use bracket arithmetic where the Tax Table lookup is mandatory, in roughly 15–20% of cases.
- **Strict vs lenient correct returns:** Gemini 2.5 Pro 32.35% vs 51.96%; Claude Opus 4 (high) 27.45% vs 42.65%.
- **Effect of thinking.** Opus 4's strict score rose from 7.84% with thinking off to 25.00% at "ultrathink"; its peak, 27.45%, is at "high".
- **Wrong reference year.** Gemini 2.5 Flash used a $15,060 Federal Poverty Level where $14,580 was correct.

**Maps to.** T2 (table vs formula) and L2 (wrong reference year).

### 2.2 Agentic workplace benchmarks

#### GDPval (arXiv 2510.04374, 2025)

**Provenance.** OpenAI: **company-authored preprint**.

**Findings (Section 3.3):**
- "experts most often preferred the human deliverable because models failed to fully follow instructions".
- GPT-5 (high) lost mainly on formatting.
- Gemini and Grok "ignored reference data".
- Roughly 29% of GPT-5's ratings were bad or catastrophic, about 3% catastrophic.

The win-or-tie headline (Claude Opus 4.1, 47.6%) is quoted from LIT-B and secondary pages; I did not re-read it on the paper.

**Rejected.** These are contract failures (capped at 30%), not difficulty.

#### TheAgentCompany (arXiv 2412.14161)

**Provenance.** **Preprint**.

**Findings:**
- The best model is Gemini-2.5-Pro: 30.3% success, 39.3% score.
- Data science, admin and finance tasks are the lowest.
- Failure classes: social skills, browsing popups, and "deceiving oneself". When stuck, an agent "decides to create a shortcut solution by renaming another user to the name of the intended user".

**Maps to.** Substitution when the right object is missing would be L9-adjacent.

**Rejected.** In our harness the equivalent is answerability (dead) and browsing (absent).

#### APEX-Agents (arXiv 2601.14242, 2026)

**Provenance.** Mercor: **company-authored preprint**.

**Findings.** 480 banking, consulting and legal tasks. The best pass@1 is 24.0% (Gemini 3 Flash, Thinking=High). The page gives no error analysis.

**Rejected.** Without an error taxonomy there is no item design to extract.

#### WorkBench Revisited (arXiv 2606.13715, 2026)

**Provenance.** **Preprint**.

**Numbers.** Task completion: Fable 5 97.7%, Opus 4.8 96.2%, GPT-5.5 94.9%. GPT-4 completed 43% in 2024.

**Residual frontier failures:**
- A percent growth compared against a raw duration: "The engaged users grew by 0%, which is not more than the average session duration".
- A due-today task treated as overdue.
- A search capped at five results trusted as complete: "the model assumes it has seen them all and stops".

**Maps to.** The percent-vs-raw comparison is T3 (unlike bases).

**Rejected.**
- The capped search needs a truncating tool; our folders are read whole.
- The due-today case is date semantics, which is dead.

#### τ-bench (arXiv 2406.12045), τ²-bench (arXiv 2506.07982) and 2026 follow-ups

**Provenance.** τ-bench is from Sierra (**company-authored preprint**); τ²-bench is a **preprint**. The follow-ups are independent preprints.

**τ-bench, retail.**
- gpt-4o scores 61.2 pass^1, and pass^8 falls below 25%.
- Wrong argument or information causes about 55% of failures, wrong decision 25%, and partial resolution of a compound request 19%.

**τ²-bench.** "Significant performance drops" from no-user to dual control (abstract only).

**Follow-up: false success (2606.09863, ICML 2026 FAGEN workshop).**
- 9,876 τ²-bench trajectories over Claude Opus 4.5, Claude Sonnet 4.5, GPT-5.2, Gemini 3 Pro and others.
- Claimed-but-absent completion is 44–52% of failures in single-control domains (45–48% in the abstract), but 3% in telecom dual control.
- The paper says "Reasoning models offer no protection"; Qwen3-Max-Thinking's false-success rate is 79%.

**Follow-up: silent policy-violating writes (2607.07405).**
- These are 78% of observed failures on the budget agent.
- Deterministic gates lift gpt-4o-mini from 29.6% to 42.0%.

**Follow-up: CAPE-Bench (2610.17301).**
- Tasks where "one fact decides whether an action is authorized".
- Retroactive "permission laundering" precedes a false report in 70% of 1,081 informed violations, mainly on open-weight families.

**Maps to.** L6, but only its "document status" half (see hazards).

**Rejected.**
- Authority as a decider is discouraged internally: Arena called such traps ambiguous, and unauthorized-request authority measured Fable 1/90.
- Writes, users and policies are stated rules, which are dead.

#### CRMArena-Pro (arXiv 2505.18878, 2025)

**Provenance.** Salesforce: **company-authored preprint**.

**What it measures.** 19 tasks in four skills: workflow execution, policy compliance, text reasoning and database querying.

**Findings:**
- **Text reasoning is the weakest skill** (single-turn, B2B / B2C): o1 23.4 / 29.5; gemini-2.5-pro 34.7 / 36.2. It includes Wrong Stage Rectification, Named Entity Disambiguation and Activity Priority Understanding.
- **Workflow execution is the strongest**: above 83%.
- **Overall**: about 58% single-turn and about 35% multi-turn.
- **Confidentiality**: awareness is 0.4% with the standard prompt.

**Maps to.** Wrong Stage Rectification is a CRM record reversed by call transcripts, which is T1/T5 territory. This is external support for the record-reversal family.

**Rejected.** Policy-compliance tasks are stated rules; multi-turn and confidentiality have no analogue here.

#### Toolathlon (arXiv 2510.25726; ICLR 2026)

**Findings.** 108 tasks over 32 apps and 604 tools. The best is Claude-4.5-Sonnet at 38.6%; the best open-weight model is DeepSeek-V3.2-Exp at 20.1%. The abstract page gives no failure taxonomy.

**Rejected.** Tool orchestration has no analogue here.

#### DABstep (arXiv 2506.23719, 2025)

**Provenance.** Adyen with Hugging Face: **company-authored**.

**Findings.**
- o4-mini scores 14.55% on hard and 76.39% on easy tasks; Claude 3.7 Sonnet 13.76% and 75.00%.
- Claude 3.7 returned a superset of applicable fees because it never computed the monthly statistics needed to filter them.

**Rejected.** These are stated multi-condition rules: stated rules (D1) and stacked rules (D2) are dead.

#### Vending-Bench (arXiv 2502.15840, 2025)

**Provenance.** Andon Labs: **company-authored**.

**Findings.** o3-mini "mistakenly assumes that items have been delivered when they in fact are in transit". The paper finds no clear correlation between failures and the context window filling.

**Maps to.** The inverse of T4 (in transit treated as in hand).

**Rejected as a new mode.** Built as a first-hand fact against a record, it is D10 (gap filler, dead). Use it only as a T4-style reversal.

### 2.3 Legal, versioned-document and temporal

#### When Do LLMs Apply the Wrong Law? (arXiv 2608.14610, 2026)

**Provenance.** **Preprint**.

**Findings.** All models ran at their highest effort. Old-version vs new-version accuracy:

| model | old-version | new-version |
|---|---|---|
| Claude Opus 4.6 (max) | 0.014 | 0.820 |
| GPT-5.4 (high) | 0.237 | 0.701 |
| Gemini 3.1 Pro (high) | 0.135 | 0.843 |

- Old→new errors are 0.69–0.94 of each model's errors.
- A strong hint raises GPT-5.4 only to 0.457.
- In more than half the LLMs, reasoning configurations do worse.
- The paper does not say whether statute texts are in the prompt, so this is mainly a parametric default.

**Maps to.** L2, L6 and L8 (aim at Fable).

#### TIDE, "Time Present and Time Past" (arXiv 2608.08512, 2026)

**Provenance.** **Preprint**.

**What it measures.** 3,050 QA pairs over 644 Bangladeshi customs instruments, 1969–2025. Nine models, with thinking enabled.

**Findings:**
- **Version in force from an implicit date:** 59.7%.
- **Detecting that a supplied version does not govern:** 26.7%.
- **"Models trust a confident false premise over the authoritative text."**

**Numbers (strict accuracy, gold context):**

| task | GPT-5.2 | Claude-Sonnet-4.5 | note |
|---|---|---|---|
| value in force on a date | 75.29 | 64.06 | |
| context misalignment | 26.73 | 14.71 | best model 27.62 |
| relative-time QA | 59.66 | 68.03 | |

**Maps to.** L2, L8, L6 (the version does not govern), L9 (confident false preamble) and L3 (relative time).

#### Asking For An Old Friend (arXiv 2605.23497; ICAIL 2026)

**Findings.** Two temporal failures: applying superseded rules, and preferring newer provisions when an older one governs. Web search shows "a marked recency bias on historically anchored tasks". Five models from OpenAI, Anthropic and DeepSeek were tested. The abstract gives no numbers.

**Maps to.** L2 and L8.

#### Time as Structure: deadline computation (arXiv 2608.15270; AACL-IJCNLP 2026 Student Research Workshop)

**Findings:**
- gpt-5.4 gets 3 of 6 computable deadlines exact, with a mean absolute error of 50.5 days, and 3 of 7 verdicts right.
- On contracts, "the errors are almost never in the arithmetic, but in choosing which event the period starts from".
- One edge counted 21 days from a letter instead of the entry into force.
- Across three GPT models, 6 of 21 verdicts contradict their own working.
- gpt-5.4 applies the minus-one-day convention correctly 7 of 7 times.

**Maps to.** L3.

**Rejected.** Calendar conventions themselves (they are solved).

#### LegalBench (arXiv 2308.11462) and condition trees (ICML 2026 AI for Law workshop)

**What it measures.** LegalBench: 162 tasks across six types of legal reasoning.

**Condition-trees findings.**
- Over 14 rule-application tasks, the GPT-5.5 baseline is 66.4%, below GPT-4o's 76.4%.
- One-condition-per-call decomposition lifts them to 88.6% and 87.3%.
- The authors' term for the failure is "condition-evaluation shortcutting".

**Maps to.** Weak support for aiming framing-driven modes at Astra.

**Rejected.** The rules are stated, and stacked rules are dead here.

### 2.4 Search and long-context

| source | finding | why rejected |
|---|---|---|
| BrowseComp (arXiv 2504.12516; OpenAI) | "Inverted" questions are hard to find and easy to verify. GPT-4o 0.6%, GPT-4.5 0.9%, o1 9.9%, Deep Research 51.5% | Search persistence; our anchors are all in the folder. Its unique-conjunction design is our *dial toward solvable*, not a trap |
| BrowseComp-Plus (arXiv 2508.06600) | Fixed corpus with hard negatives. GPT-5 55.9%, rising to 70.1% with a better retriever | Retrieval |
| MMLongBench-Doc (arXiv 2407.01523; NeurIPS 2024 D&B) | 1,062 questions over PDFs averaging 49.4 pages; 22.8% unanswerable; 33.2% cross-page; GPT-4o F1 42.7% | Parsing, length and answerability: all dead |
| LongBench v2 (arXiv 2412.15204) | 503 questions; experts 53.7%; best direct answer 50.1%; o1-preview 57.7% | Volume and breadth (D16) |
| Loong (arXiv 2406.17419; EMNLP 2024) | Multi-document QA where every document matters (spotlight, comparison, clustering, chain) | Volume and breadth |
| NoLiMa (arXiv 2502.05167; ICML 2025) | With no keyword overlap, GPT-4o falls from 99.3 to 69.7 at 32K; 11 of 13 models fall below half their baseline; reasoning models still struggle | The long-context part is dead. Its *latent identity* lesson supports T1 and L11 |
| AbsenceBench (arXiv 2506.11440; NeurIPS 2025) | Omission detection: Claude-3.7-Sonnet (thinking) F1 69.6, o3-mini 60.7, DeepSeek-R1 30.4; a placeholder marker helps a lot | A diff script solves it; coverage omissions are dead (D7: 0/125, 0/60) |

### 2.5 Knowledge conflict, false premise, sycophancy, recency

| source | finding | maps to |
|---|---|---|
| BrokenMath (arXiv 2510.04721; NeurIPS 2025 listing) | GPT-5 produces sycophantic proofs of perturbed false statements 29% of the time; mitigations reduce but do not remove it | L9 |
| PCBench (arXiv 2505.23715; EMNLP 2025 Findings) | "Most models rely heavily on explicit prompts to detect errors"; reasoning ability does not predict premise critique | L9 |
| AbstentionBench (arXiv 2506.09038) | Reasoning fine-tuning degrades abstention by about 24%; 20 frontier LLMs | Rejected: answerability is dead (D6) |
| Recency in reranking (arXiv 2509.11353) | Injected dates reverse pairwise preferences by up to 25%; "Although larger models attenuate the effect, none eliminate it." | L2, L8 |
| Evidence arbitration (arXiv 2608.20116) | Models follow temporal recency more consistently than explicit reliability cues (open-weight models) | L6, L8 |
| In-context knowledge updates (arXiv 2603.12271) | With many in-context updates, earliest-state accuracy stays high while latest-state accuracy drops | L1 |
| KC-Bench (arXiv 2609.03588) | 238 agent tasks; "no model handles factual correction, identity consistency checking, and temporal conflict resolution reliably" | General support; no per-model numbers read |
| DRAGged into Conflicts (arXiv 2506.08500) | LLMs often fail to resolve conflicting sources; prompting them to reason about conflicts helps (abstract only) | Not used: no numbers read |

### 2.6 Reasoning-failure papers on reasoning models

| source | finding | maps to |
|---|---|---|
| Inverse Scaling in Test-Time Compute (arXiv 2507.14417; Anthropic-affiliated authors; TMLR 2025) | "OpenAI o-series models resist distractors but overfit to problem framings"; Claude models get more distracted with longer reasoning | L9 (framing). Distractors are dead here |
| RoR-Bench (arXiv 2504.00509; AACL-IJCNLP 2025) | o1 and DeepSeek-R1 lose up to 60% when one phrase of an elementary problem changes | T4 generalisation (LIT-A #4); not a new mode |
| LLMs Get Lost in Multi-Turn Conversation (arXiv 2505.06120) | 39% average drop when requirements arrive across turns; early assumptions are never recovered | Rejected: no user turns; the cross-step lab (L23) died |
| AgentNoiseBench (arXiv 2602.11348) | 20.8% average drop under tool and user noise; thinking models build "complex but incorrect logical chains" from noise | Rejected: no tools |
| Entity matching with LLMs (arXiv 2310.11244; EDBT 2025) | GPT-4 false positives are mostly "Overemphasis on Matching Attributes" (23 of 26) | L13, L11 (pre-reasoning model) |

---

## 3. Rejected because the mechanism is dead in our harness

| idea | external source | internal evidence that kills it |
|---|---|---|
| Abstain when no source governs; unanswerable items | AbstentionBench; MMLongBench-Doc; FinIndices deficiency trap; TIDE rejection | D6 answerability: 0/75 Fable, 1/35 Astra; lab L24 dead. LIT-A #6 is therefore **not** added as an L mode |
| Absence or omission detection | AbsenceBench | D7 coverage: 0/125, 0/60; a script diffs it |
| Truncated listing trusted as complete | WorkBench Revisited B.3 | Needs a capped tool; adjacent to D7 |
| Multi-condition rule shortcutting; superset filters | Condition trees; DABstep | D1 stated rules (0/810, 0/720); D2 stacked rules |
| Unauthorized actor or request | τ²-bench follow-ups; CAPE-Bench | authority_delegation discouraged; unauthorized-request authority Fable 1/90 |
| Long-context, needle and multi-document retrieval | LongBench v2; Loong; MMLongBench-Doc; DocFinQA; BrowseComp | D16 breadth/volume; models read everything (TRAJ: 519 of 521) |
| Distractors, irrelevant clauses | Inverse scaling (Claude distraction) | Decoys and pointers are on the TRAP-CATALOG-B7 §5 dead list |
| Formatting and instruction following | GDPval | Contract failures, capped at 30% |
| Parametric constant from the wrong year | TaxCalcBench FPL; FrontierFinance | Context-vs-memory conflicts are solved (LIT-A, ClashEval); usable only inside L2/T6 |
| Date arithmetic, day-count conventions | 2608.15270 (gpt-5.4 7/7 on minus-one-day) | Dead per TRAP-CATALOG-B7 §6 |
| Multi-turn drift, tool noise | Lost in conversation; AgentNoiseBench; τ²-bench | No user, no tool noise; cross-step lab L23 dead |
| In transit treated as in hand | Vending-Bench | D10 gap filler (4/215, 3/105) unless built as a T4-style reversal |
| Over-flagging clean items | FinVerBench | Only in review deliverables; kept as an L12 hazard |
| A misleading label or a repeated wrong figure | (TIDE context misalignment would suggest it) | misleading_label 0/295 Fable, 0/300 Astra; self-consistent wrong figure replications 0/215 Fable. L9 is built so the agent must **act on** the presupposition |

---

## 4. Verification notes and corrections to LIT-A and LIT-B

- **FinIndices.** LIT-A's numbers check out against Table 3 and Appendix Tables 11–12, including the 202.25% vs 58.49% YTD-base failure. The paper's own text gives Gemini's with-hint figure as 70.07%, against 70.70% in its table.
- **2608.14610.** LIT-A's table is correct. The paper confirms that all models ran at their highest effort. The base prompt in the HTML is a placeholder, so whether statutes were supplied is still unknown.
- **TaxCalcBench.** LIT-A says there is "no gain at higher thinking". That holds only between "high" (27.45%) and "ultrathink" (25.00%). With thinking off, Opus 4 scored 7.84% strict, so thinking helped it a lot overall.
- **OfficeQA Pro V2.** The 37.5% vs 26.0% averages are inconsistent inside the post itself (LIT-B noted this). The calendar-to-fiscal shift and the "name, location, table schema, unit, time basis, and level of aggregation" sentence are confirmed.
- **TIDE.** All per-model numbers in LIT-A were confirmed. The headline figures are 68.5% best macro accuracy, 59.7% implicit-date resolution and 26.7% rejection of a non-governing version.
- **2608.15270.** Confirmed: gpt-5.4 3/6, MAE 50.5, 6 of 21 contradicting verdicts. The paper does not report the s.207B pause result for gpt-5.4 specifically.
- **FrontierFinance's 26.7%.** Confirmed in the HTML. The "Claude leans on priors" reading is LIT-B's inference and mine, not the paper's.
- **Entity-matching error classes** (LIT-B #5). Confirmed in Table 12 of 2310.11244.

---

## 5. Most likely to bite Fable 5.1 and Astra

This ranking is my judgment. No mode here has a measured row in our harness. Pilot each one 5×2, then run blind readers on any 5/5 miss (TRAP-CATALOG-B7 §8).

### 1. L7: figure scope (component taken for the whole). Fable likely; Astra uncertain.
- It is the only 2026 design that beat **both** Fable 5 and GPT-5.6 Sol on the same task (APEX-Accounting).
- It is a pure L-record shape: the figure's label matches the deliverable field, so the default lifts it.
- The perimeter can be made *impossible* (not merely unlikely) by a conserved total from a third party.
- Internally, Fable misses attributes carried only by incidental remarks (T13: Fable 57/65, Astra 0/65).
- Risk: Astra is strong on attribute and quantity semantics (it passes profile P6/P7 20/20), so the Astra bite is the uncertain half.

### 2. L6: a document about a change applied as the change in force. Fable.
- APEX-Accounting's Fable 5 failure has this shape.
- Claude-family models show the most extreme newest-version default (0.014).
- In TRAJ, Fable says it follows "the explicit statement" (suitcase P5) and cites governing documents (L-shield). The newer document *is* the explicit statement.
- Astra's T6 analogue bit 90–100%, so it may bite both.
- Risk: authority-flavoured traps were ruled ambiguous before. The status must come from conduct anchors, never from who had authority.

### 3. L11: one event under two document numbers. Astra.
- Astra's misses are 58% silent key joins.
- It credits both readings (F-union) when it notices: cnc 10/10, ats 5/10.
- Grading the payable balance against the supplier statement turns that union into a miss.
- External support is moderate: SpreadsheetBench 2 seeds this defect class (frontier debugging accuracy 8–12%), and FinBalance's commonest error is linking the wrong documents.
- Risk: near-twins are dead, so the two documents must not look alike.

### 4. L10: series continuity across a reclassification. Both.
- Astra joins on codes silently.
- Fable is likely to cite a "compare like-for-like codes" rule (a scoped shield).
- OfficeQA Pro V2 reports this exact residual for the Claude Code and Codex agents.
- The worked comparative figure is a single-discriminator design, which our T2 data shows is Astra's weak spot (one discriminating figure gives about 100% Astra misses).

### 5. L12: a by-design irregularity "corrected". Astra.
- GPT-5.6 Sol's fixed-denominator failure (APEX-Accounting) plus Astra's silent-default class (D, 25% of its misses) point here.
- Use exactly two discriminating worked figures, placed outside the entry that defines the graded rate (T2 dial lessons).

### Lower confidence
- **L8.** A real mechanism, but it risks ambiguity over the deliverable's purpose.
- **L9.** It sits next to two dead shapes (misleading labels, repeated wrong figures).
- **L13.** Close to near-twins, and the evidence is from older models.
- **L14.** Thin evidence.
- **L1–L4.** Keep as before. **L5** is now T14.

**Interlocks worth piloting:**
- **L7 + T3.** A perimeter slip on a tax-inclusive figure.
- **L6 + L2.** A proposal priced on the newer edition while acceptance predates it.
- **L11 + T1.** The re-issued invoice is also keyed to the wrong PO.

Route several checks through each interlock, because pass@1 counts full success.

---

## 6. Sources: verified and dropped

**Verified by opening the page on 2026-10-15** (arXiv abstract or HTML unless noted):
- 2603.08655
- the Databricks OfficeQA post (2025-12-09) and OfficeQA Pro V2 post (2026-08-06)
- 2607.27189
- 2607.28661 (Table 3 and Appendix Tables 11–12)
- 2606.15949
- 2510.08886 (HTML)
- 2406.14991
- 2606.29955 (HTML)
- 2311.11944 (HTML)
- 2401.06915
- 2608.11683 (HTML)
- 2605.29586
- 2507.16126 (HTML)
- 2510.04374 (HTML)
- 2412.14161 (HTML)
- 2601.14242
- 2606.13715 (HTML)
- 2406.12045 (HTML)
- 2506.07982
- 2606.09863 (HTML)
- 2607.07405
- 2610.17301
- 2505.18878 (HTML)
- 2510.25726
- 2506.23719 (HTML)
- 2502.15840 (HTML)
- 2608.14610 (HTML)
- 2608.08512 (HTML)
- 2605.23497
- 2608.15270 (HTML)
- 2308.11462
- the ICML 2026 condition-trees page (icml.cc/virtual/2026/80604)
- 2504.12516 (HTML)
- 2508.06600
- 2407.01523
- 2412.15204
- 2406.17419
- 2502.05167
- 2506.11440 (HTML)
- 2510.04721
- 2505.23715
- 2506.09038
- 2509.11353
- 2608.20116
- 2603.12271
- 2609.03588
- 2506.08500
- 2507.14417
- 2504.00509
- 2505.06120
- 2602.11348 (alphaxiv listing)
- 2310.11244 (HTML)
- 2603.25092 and 2606.26437 (read; not used: web-domain authority, and no numbers)

**Dropped or not used:**
- **AccountingBench (Penrose).** The page renders only its title, so "pulled unrelated transactions to force reconciliation" could not be verified.
- **A search-snippet claim that 26% of τ²-bench write actions came with a false justification.** It is not on the 2610.17301 page.
- **Daloopa, DualEntry and Modern Treasury.** Vendor pages, not re-verified.
- **HELEA.** Unverified in LIT-A; not used.
- **No benchmark was found on contract versions or execution status** (draft vs executed, order of precedence). L6's support is indirect: one APEX-Accounting trajectory plus the version-recency literature.
