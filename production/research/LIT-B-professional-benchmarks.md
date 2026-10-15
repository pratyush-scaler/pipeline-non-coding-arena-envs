# LIT-B: persistent error types in professional-work benchmarks (2023–2026)

Compiled 2026-10-15, for the b7 trap design. The question: which error types do frontier
models still make on real desk work, and which of them can be built into a file-folder
task with a JSON deliverable and deterministic checks?

**How to read this.** Every number below comes from the source named next to it. I read
most papers through their arXiv HTML or abstract pages, and two through PDF text I
extracted. A source marked **[secondary]** was verified only through press coverage, an
aggregator or a vendor page, never through the primary text. A source marked
**[snippet]** was seen only in a search summary. The "expected miss" ratings are my
judgments, not measurements. They take into account what the team has already measured:
stated rules, decoys, pointers, breadth and isolated levers are dead; keying slips,
worked-figure conventions, indirect tax-inclusive cues, per-pack pricing, "already in
hand" and edition-by-receipt-date work.

**A transfer warning applies to almost every rate.** Most published failure rates were
measured on older models (GPT-4/4o, Claude 3.x), in direct-answer mode without code
execution, or on PDFs that had to be parsed. Fable 5.1 and Astra read every file, compute
in Python and re-check their work, so extraction and arithmetic errors mostly vanish for
them. What carries over are the errors that sit **upstream of the arithmetic**: picking
the wrong record, period, version or convention. Those are the errors the newest sources
still report on frontier models, including Claude Fable 5 and GPT-5.6 Sol running in
Claude Code and Codex (OfficeQA Pro V2, 2026).

---

## Top 8

| # | Error type | Strongest frontier evidence | Fable 5.1 | Astra | Overlap with what already works |
|---|---|---|---|---|---|
| 1 | **A later restatement supersedes the first-reported figure** | OfficeQA Pro V2: Claude Code (Opus 4.8, Fable 5) and Codex (GPT-5.5, GPT-5.6 Sol) average **37.5%**; "retrieving the latest revised figures" named as an open failure | M–H | M–H | New. This is the "changed premise" doctrine in its purest form |
| 2 | **An older edition governs by the event date (recency bias)** | German statutory QA (2605.23497): recency bias on historically anchored tasks. TaxCalcBench: used the wrong year's FPL, **$15,060 vs $14,580** | H | M–H | Edition-by-receipt-date (works) |
| 3 | **A textbook prior overrides the local convention** | TaxCalcBench: bracket formula used where the IRS table lookup is mandatory, **15–20% of test cases**. MedCalc audit: formula-version mismatch. OfficeQA Pro: sample vs population variance | H | M | Worked-figure conventions (work) |
| 4 | **The wrong anchor event starts the period clock** | Deadline paper (2608.15270): gpt-5.4 **3/6** exact deadlines, MAE 50.5 days; contract errors "come from choosing which event the period starts from" | M | M–H | Partly new (the inferred-clock lessons apply) |
| 5 | **Keying slip on a near-identical identifier** | Entity matching (2310.11244): "Model Number Mismatch" in 9/15 false negatives and "Overemphasis on Matching Attributes" in 23/26 false positives. OfficeQA: "508" read as "608" | M–H | M–H | Keying slips (work) |
| 6 | **Comparing quantities on unlike bases** (percent vs raw, pack vs unit, gross vs net, scale) | WorkBench Revisited: **Opus 4.8** compared a percentage to a raw value and skipped required actions. Daloopa: rounding, scale and sign about **25%** of errors | M–H | M–H | Per-pack and tax-inclusive (work) |
| 7 | **Rounding at the wrong stage** (exact checks) | OfficeQA Pro: "a majority of remaining errors stem from final answer precision (ex. rounding too early)". TaxCalcBench strict vs ±$5 lenient: Gemini 2.5 Pro **32.35% vs 51.96%** | M | M | Worked-figure conventions (work) |
| 8 | **Fiscal/calendar or period-shift mapping** | OfficeQA: fiscal-year figures pulled for 8 calendar years made a prediction **31.6%** off. Daloopa: period errors **~11%** of errors | M | M | New |

The ratings in the Fable and Astra columns are graded H (high), M (medium) and L (low)
expected miss. They assume the trap is anchored at least twice and the instruction
carries no graded value.

---

## Ranked entries

### 1. A later restatement supersedes the first-reported figure

**Definition.** A figure is reported once and later corrected in a subsequent document,
such as next month's pack or a revised bulletin. The governing value is the latest
revision, but agents settle on the first plausible instance they find.

**Evidence.**
- *OfficeQA Pro V2* (Databricks blog, 2026, https://www.databricks.com/blog/introducing-officeqa-pro-v2-new-benchmark-enterprise-grounded-reasoning). Out-of-the-box agents were Claude Code with **Claude Opus 4.8 and Claude Fable 5**, and Codex with **GPT-5.5 and GPT-5.6 Sol**. They averaged **37.5%**, and GPT-5.6 Sol on Codex scored **33.3%**. In the medium example (Medicare outlays) the agent "must read each year's value from the latest revised prior-year column". The takeaways list "retrieving the latest revised figures" and "incorrect temporal reconciliation as accounting conventions change over time" as remaining failures. These are company-reported figures, and the body text gives a different 5-model average (26.0%).
- *OfficeQA Pro* (arXiv 2603.08655). Agents "often fail to retrieve revised values, often prematurely converging on the first numerically plausible instance" (Figure 8 compares the September and December 2013 bulletins). Claude Opus 4.6 scores 48.12% on PDFs, 54.14% parsed and 66.92% with oracle pages parsed. GPT-5.4 scores 36.09% on PDFs and 56.39% parsed.
- *OfficeQA* (original blog, https://www.databricks.com/blog/introducing-officeqa-benchmark-end-to-end-grounded-reasoning). An agent took FY2005–2009 debt from the June 2010 bulletin when the September 2010 edition was correct, and was off by $21 million (0.01%).
- *In-context knowledge updates* (arXiv 2603.12271). When the same fact is revised many times within one context, accuracy on the earliest value stays near ceiling while accuracy on the latest value falls. Qwen3-235B scores 100.00 on earliest and 80.67 on latest. Claude-Sonnet-4 and DeepSeek-V3 fall "in between", and the paper reports no exact number for them.
- Strongest model still fails? **Yes.** OfficeQA Pro V2 is the only source found that tests the exact model families and harnesses we calibrate against. Part of its error budget is PDF parsing, which our CSV and text fixtures remove.

**Instantiation.** The folder holds six monthly cost-centre packs, `pack_2026-01.csv` to
`pack_2026-06.csv` (cost_centre, line, actual), each with a short `commentary_<month>.md`.
The April commentary says: "March travel for CC-410 corrected to 12,480 following a late
hotel invoice." The May pack carries an `r` flag on one April figure, and the footer
reads "r = restated; supersedes the figure in the prior pack". `finance_policy.md` says a
month's figure is final once restated. The task: build an H1 variance register for
eight cost centres against `budget_h1.csv`.
- **Right:** use the restated values for the 2–3 corrected cells.
- **Default wrong:** sum the `actual` column as first reported. One or two cost centres then flip their over/under-budget status.

**Validity risk and anchor.** Risk: two numbers for the same cell, with a reader unsure
which one wins. Anchors (at least two): the restatement sentence in the commentary, the
`r` flag with its footer definition, and the policy line. No restatement may be
ambiguous about which cell it amends; quote cost centre, line and month.

**Expected miss.** Fable **M–H**, Astra **M–H**. Both read every file, but the
correction lives in narrative commentary, not in the table they will aggregate. The
literature's mechanism is "converging on the first plausible instance", and this is
exactly the premise that "silently invalidates a result already computed". Route the
variance status, the cost-centre ranking and the H1 total through the same corrected
cells (cascade).

---

### 2. An older edition governs by the event date (recency bias)

**Definition.** Several versions of a rule, table or price list exist. The governing
version is fixed by the date of the triggering event, not by publication recency, yet
models default to the newest version, or to the one that matches their training prior.

**Evidence.**
- *"Asking For An Old Friend"* (arXiv 2605.23497, German statutory QA). The paper names two failure modes: applying superseded rules, and "preferring newer provisions even when an older version governs". Web search "exhibits a marked recency bias on historically anchored tasks". The aggregator listing gives the recency bias as 0.20–0.24, and lists vanilla scores of ChatGPT-5.2 at 49.56 and Claude Opus 4.5 at 35.4 **[secondary: benchmarklist.com; the abstract has no numbers]**.
- *TaxCalcBench* (arXiv 2507.16126). On Form 8962 Gemini 2.5 Flash "uses the wrong Federal Poverty Level (FPL): $15,060 vs $14,580". $15,060 is the 2024 HHS guideline for one person and $14,580 is the 2023 figure, which a tax-year-2024 premium tax credit uses; that mapping is my own reading, not the paper's.
- *MedCalc-Bench audit* (arXiv 2603.02222). A dominant failure is "formula version mismatch", for example MELD vs MELD 3.0 and CKD-EPI 2009 vs 2021, where the model recalls a different version than the one expected.
- *Recency bias in LLM reranking* (arXiv 2509.11353) **[snippet]**. A date tag alone reversed "up to 25%" of pairwise preferences between equally relevant passages.
- Strongest model still fails? Yes on the statutory benchmark (Opus 4.5 and GPT-5.2 tested). The FPL example comes from a non-frontier model.

**Instantiation.** `pricelist_v7.csv` is effective 2026-05-01 and `pricelist_v8.csv`
effective 2026-06-01. Purchase orders are in `po_register.csv`, and goods receipts in
`grn.csv` (Spanish column headers, `fecha_recepción`). The framework agreement, clause
4.2, says: "price is that of the list in force on the date the goods are received". A
worked dispute email recalculates one invoice under v7 because receipt fell in May.
- **Right:** v7 for the 4 lines received before 1 June, even though they were invoiced in June.
- **Default wrong:** v8 for everything invoiced in June, or the PO date's list.

**Validity risk and anchor.** Risk: equal-authority sources disagreeing about which date
governs. The team has already found that this works only when the competing sources
have similar authority and the date is checkable. Anchors: clause 4.2 plus the worked
email. The receipt date must exist in one file only; never infer it.

**Expected miss.** Fable **H**, Astra **M–H**. This is already measured as working. The
literature adds that frontier models with search *amplify* recency.

---

### 3. A textbook prior overrides the local convention

**Definition.** The model computes "the standard way" (a textbook formula, a familiar
version, a canonical layout) where the documents establish a different local convention,
often only through worked figures.

**Evidence.**
- *TaxCalcBench* (arXiv 2507.16126). Models used "tax bracket percentage-based calculations instead of proper lookup tables" in "(15-20% of test cases)", although the IRS says "you must use the Tax Table" below $100,000. Claude Opus 4 computed 2789 by bracket math and was off by **$3** against the table band "$26,000 and $26,050". The best strict scores are low: Gemini 2.5 Pro 32.35% (lobotomized) to 31.37% (high), and Claude Opus 4 27.45% (high).
- *MedCalc-Bench* (arXiv 2406.12036). With GPT-4 zero-shot, 57% of errors are "knowledge" errors (wrong equation or rule), 30% extraction and 13% computation. One-shot gives 40%/27%/33%, and the best accuracy is **50.91%**. The audit (2603.02222) adds the formula-version mismatch noted in entry 2.
- *OfficeQA Pro* (2603.08655) cites sample vs population variance as a formula error. A federal-debt answer used OMB figures instead of the Treasury Bulletin and deviated by about 0.5%.
- *SpreadsheetBench 2* (arXiv 2606.29955). The financial-modeling formulas were "textbook-correct but the cell references did not match the actual row layout" (about 4% modification accuracy). Claude Opus 4.6 is best at 34.89% overall.
- *FrontierFinance* (arXiv 2608.11683). **Claude Fable 5** draws 26.7% of its parses from self-produced (parametric-knowledge) URLs, about twice Opus 4.8's rate; every other system is below 5%. That suggests the Claude line leans on priors more. This is my inference, not the paper's claim.

**Instantiation.** `allowance_policy_FR.md` is in French. It states that the mileage
allowance is read from a banded table at the band midpoint ("barème par tranches de 50
km") and shows two worked claims, 213 km and 388 km, with their payable amounts. Only
bands up to 400 km are printed, but claims reach 640 km. `claims_q3.csv` has 15 claims.
- **Right:** extend the midpoint convention; the two worked figures pin it, and floor or ceiling would contradict them.
- **Default wrong:** rate × exact km, small differences on about 9 of 15 rows.

**Validity risk and anchor.** Risk: the convention is underdetermined. Use at least two
worked figures that are each inconsistent with the competing conventions (exact,
floor-band, ceil-band, midpoint), and verify by execution that exactly one convention
reproduces both.

**Expected miss.** Fable **H** (worked-figure conventions already work, and parametric
reliance is higher), Astra **M**. Literal pattern-matching of examples may protect Astra
more.

---

### 4. The wrong anchor event starts the period clock (deadlines, windows, encounters)

**Definition.** The arithmetic of a period is easy. The failure is in choosing the event
the period counts from, or in missing a suspension ("stop-the-clock"). Clinical
analogue: taking values from the wrong encounter.

**Evidence.**
- *Time as Structure* (arXiv 2608.15270, UK employment-tribunal deadlines). On contracts, errors "are almost never in the arithmetic. They come from choosing which event the period starts from". One LLM edge counted 21 days "from the date of a letter" instead of from the entry into force that the clause names. The frontier model gpt-5.4 got **3/6** computable deadlines exact (mean absolute error **50.5 days**) and applied the minus-one-day convention in all 7 responses. Across three GPT models, **6 of 21** responses stated a verdict that contradicted their own working, each time calling a late claim timely. No model below the frontier applied the s.207B conciliation pause correctly.
- *MedCalc-Bench audit* (2603.02222). The model used creatinine 1.0 (outpatient) instead of 2.0 (ED) because it misclassified the encounter.
- *WorkBench Revisited* (arXiv 2606.13715). In a residual frontier failure (B.1), tasks due today were treated as overdue and an action fired that should not have.
- Strongest model still fails? Yes (gpt-5.4, direct answering). Agentic re-checking should help, which is why the anchor must be a *defined term*, not a salient date.

**Instantiation.** `MSA_extract.md`, clause 9.2: "defect notices within 21 days of the
Acceptance Date". The definitions clause 1.1 reads: "Acceptance Date: the date the
Customer countersigns the Acceptance Certificate". Clause 9.4 suspends the period while a
Joint Inspection is open. The files are `acceptance_certs.csv` (countersigned_on),
`delivery_notes.csv`, `inspections.csv` (opened, closed), and a supplier cover letter
whose date is the most salient in the folder. A prior-dispute memo works one deadline,
which shows day-exclusion and the suspension. The task: register 12 defect notices
(last valid day, timely y/n).
- **Right:** countersignature date + 21 days + inspection days.
- **Default wrong:** count from the delivery or letter date, or ignore 9.4. About 4 of 12 flip.

**Validity risk and anchor.** The team has measured that a one-anchor inferred clock
fails review. The anchor here is *defined*, not inferred: a definitions clause plus a
worked memo. The suspension needs both its trigger and its end date in one file.

**Expected miss.** Fable **M** (the memory notes say Fable voices and resolves
conditioned premises). Astra **M–H** (round-2 anchor levers moved Astra before).

---

### 5. Keying slip on a near-identical identifier

**Definition.** A record is filed under an ID that differs from the right one by a
transposition or a single digit. The record's other attributes show where it belongs.
Models trust the ID, or over-weight matching attributes.

**Evidence.**
- *Entity Matching using LLMs* (arXiv 2310.11244, EDBT 2025). GPT-4's best zero-shot F1 is 89.61 on WDC Products and 89.67 on Walmart-Amazon. GPT-4-derived error classes on Walmart-Amazon: false negatives (15) include "Model Number Mismatch" 9 and "Price Differences" 12. False positives (26) include "Overemphasis on Matching Attributes" 23 and "Ignoring Minor but Significant Differences" 21. Classes overlap.
- *OfficeQA* blog: a misread digit, "reading '508' as '608'", and column shifts that attribute numbers to the wrong header.
- *SpreadsheetBench 2* (2606.29955). "Wrong Target Selection" is one of the two dominant failure categories for Opus 4.6: copying an adjacent ratio's numerator made Debt/Equity "exactly ∼2× the correct value".
- *TheAgentCompany* (arXiv 2412.14161). Unable to find the right contact, the agent renamed another user to the intended name ("deceiving oneself").

**Instantiation.** `invoice_register.csv` books invoice INV-7731 against PO 4501-2271.
Its SKUs, quantities and delivery date match only PO 4501-2217, and the supplier's
delivery note quotes 2217.
- **Right:** re-key INV-7731 to 2217, so 2271 stays open and 2217 is fully matched.
- **Default wrong:** a quantity and price variance against 2271, and 2217 left as "not invoiced".

**Validity risk and anchor.** Risk: a reviewer calls the re-key speculation. Use two
independent anchors (the delivery note's PO reference plus SKUs unique to 2217) and make
sure no third PO fits.

**Expected miss.** Fable **M–H**, Astra **M–H** (already measured as working).

---

### 6. Comparing quantities on unlike bases

**Definition.** Two quantities are compared or combined when one is a percentage and the
other a raw value, one per pack and the other per unit, one gross and the other net or
tax-inclusive, or one in thousands and the other in units.

**Evidence.**
- *WorkBench Revisited* (2606.13715). In a residual frontier failure, **Opus 4.8** compared a percent growth against a raw average session duration and concluded: "The engaged users grew by 0%, which is not more than the average session duration". It skipped the required actions. Context: Claude Fable 5 completes 97.7% of tasks, Opus 4.8 96.2% and GPT-5.5 94.9%.
- *Daloopa benchmark* (vendor, https://daloopa.com/?p=9330) **[secondary/vendor]**. 500 single-number filing lookups. "Rounding / Formatting", which includes decimal misplacement, misplaced thousands separators and sign errors, accounts for ~25% of errors. ChatGPT (GPT-5 Thinking) scores 64.2%; Claude Opus 4.1 scores 31.4% without MCP and 91.6% with it.
- *FinanceReasoning* (arXiv 2506.05828, ACL 2025). For DeepSeek-R1, calculation errors make up 37.5–45% of sampled errors at every difficulty level. The authors name "unit conversions, percentage formats, significant digits, and sign correctness" as the fix for easy and medium items. o1 reaches 89.1% with PoT.
- *TAT-QA* (arXiv 2105.07624) **[snippet]**. Scale errors were 3% of errors for the pre-LLM baseline. *FinanceBench* (2311.11944): incorrect answers ranged "from calculations that are off by small margins to several orders of magnitude" and included "the wrong direction for an effect".
- *OfficeQA Pro*: human annotators wrote "19.519 trillion instead of 19,519,306 million".

**Instantiation.** Three supplier quotes. One is in German, priced "je Karton (12 Stk.)".
One is per unit with "inkl. 19% MwSt." in the footer. One is per unit net, with a
"Preisangaben in Tsd. EUR" header on its volume-discount table. The task: cheapest
compliant supplier per item and net unit cost.
- **Right:** normalize everything to net per unit.
- **Default wrong:** compare the printed prices, which flips 2–3 of 10 items.

**Validity risk and anchor.** Each basis cue must be explicit somewhere, and should
appear twice (the header plus an order confirmation that shows the arithmetic). The
"indirect cue" variant works for us because the cue is present but not adjacent to the
price.

**Expected miss.** Fable **M–H**, Astra **M–H** (already measured as working; a frontier
Claude still made the percent/raw comparison in 2026).

---

### 7. Rounding at the wrong stage

**Definition.** The answer depends on where rounding happens (per line vs per total;
before or after a rate). Exact checks expose it, and frontier agents round early or use
the default convention.

**Evidence.**
- *OfficeQA Pro* (2603.08655): "a majority of remaining errors stem from final answer precision (ex. rounding too early)".
- *TaxCalcBench*, strict vs lenient (±$5) correct returns: Gemini 2.5 Pro (lobotomized) **32.35% vs 51.96%**, Claude Opus 4 (high) **27.45% vs 42.65%**. About 15–20 points of returns are near-misses, many of them dollar-scale.
- *Payroll* (arXiv 2601.18012). Grok showed "consistent penny-scale offsets" and the paper notes "persistent rounding bias" at the highest complexity. These are chat-UI evaluations, not agents.
- *DABstep* (arXiv 2506.23719) lists "incorrect rounding" among its non-trivial format errors.

**Instantiation.** VAT on 40 invoice lines, two of them worked in `sample_invoices.pdf.txt`.
The worked lines show VAT rounded per line before summing; the default rounds the
total. One or two cents of difference on 6 invoices changes the reconciliation total
and the count of "matched" invoices.

**Validity risk and anchor.** Exactness must be justified. The deliverable is a VAT
return line, so cents matter, and two worked figures must disambiguate the stage. Never
combine this with a tolerance.

**Expected miss.** Fable **M**, Astra **M**. The memory note "round = ceil(floor×n/2)"
shows that Fable carries rounding conventions forward. Contradicting a carried convention
locally is the lever.

---

### 8. Fiscal/calendar or period-shift mapping

**Definition.** Values are pulled for the wrong period basis: fiscal instead of calendar
year, a shifted quarter, or TTM instead of a single quarter. The error grows when a
reporting basis changes partway through the series.

**Evidence.**
- *OfficeQA* blog. For a 1989–2013 regression, an agent "pulled fiscal-year figures for 8 years instead of calendar-year figures"; the 2025 prediction was off by $286,831 million (**31.6%**). OfficeQA Pro V2 notes that the corpus shifts from calendar to fiscal reporting, and that concepts change in "name, location, table schema, unit, time basis, and level of aggregation".
- *Daloopa* **[vendor]**. Period errors (fiscal vs calendar plus period shift/TTM) are ~11% of errors. Claude + MCP falls from 91.6% overall to 88.2% on fiscal/calendar-offset companies (87.7% in the conclusion).
- *OfficeQA Pro*. GPT-5.4 performs "∼15% worse" on 1930s–1970s documents than on 1980s–2020s ones, against a "∼5%" gap for Opus 4.6 and Gemini 3.1 Pro. Older conventions hurt the OpenAI model more.

**Instantiation.** One subsidiary reports on an April–March fiscal year. Its file
`sub_JP_results.csv` has Japanese headers (`会計年度`, `四半期`) labelled FY2026 Q1 (=
Apr–Jun 2025). Group consolidation needs calendar Q2 2025. A group-reporting manual
paragraph plus last year's reconciled consolidation sheet both show the mapping.
- **Right:** JP FY2026 Q1 maps to CY2025 Q2.
- **Default wrong:** take the row labelled Q2.

**Validity risk and anchor.** The fiscal-year start must be stated in at least two
places (the manual and the subsidiary's own header note).

**Expected miss.** Fable **M**, Astra **M**.

---

### 9. A category's scope or granularity is misread

**Definition.** The answer uses the wrong level of aggregation, such as a parent
category vs its components or a consolidated vs a segment figure, or a category whose
membership changed between periods.

**Evidence.** *OfficeQA Pro V2* names "misinterpretation of entity scope or category
granularity". *FinAuditing* (arXiv 2510.08886) finds that models "rely on surface-level
semantic similarity": they miss cash-and-equivalents tagged where only "Cash" is allowed,
and an aggregate tag (AssetsCurrent) used where components are required. On FinMR,
calculation errors are 70–83% of failures, but those runs did not use tools.
*BizFinBench v2* (arXiv 2601.06401) finds that GPT-5 and Gemini-3 errors are dominated
by "Multivariate Integrated Analysis Deviation" and Claude-Sonnet-4 and Grok-4 by
"High-precision Computational Distortion". GPT-5 scores 61.5% against an 84.8%
"practical business requirement".

**Instantiation.** The 2025 chart of accounts folds "Accommodation" into "Travel". The
2024 budget lists them separately. The task: year-on-year travel variance on a
comparable basis.
- **Right:** combine the 2024 lines.
- **Default wrong:** 2025 Travel vs 2024 Travel alone, which shows a spurious overspend.

**Anchors:** the mapping table in the chart-of-accounts memo, plus one cost centre's
commentary noting the merger.

**Expected miss.** Fable **M**, Astra **M**.

---

### 10. Condition-evaluation shortcutting (multi-condition rules)

**Definition.** The model reaches a conclusion before checking every condition of a
rule, especially a condition that needs a derived aggregate or a different period.

**Evidence.**
- *Condition trees on LegalBench* (ICML 2026, https://icml.cc/virtual/2026/80604). Across 14 rule-application tasks (n=2,602), the **GPT-5.5** baseline is **66.4%**, *below* GPT-4o's 76.4%, and both are fixed by one-condition-per-call decomposition (88.6% / 87.3%). On diversity jurisdiction GPT-5.5 scores 66%. The paper calls the failure "condition-evaluation shortcutting".
- *LegalBench* (arXiv 2308.11462). GPT-4's lowest category is rule-recall (59.2). In the diversity tasks LLMs state that "$50,000 is greater than $75,000". On telemarketing_sales_rule they cite §310.3(a)(2) where (a)(1) applies.
- *DABstep* (2506.23719). o4-mini scores 76.39% on easy and **14.55%** on hard tasks. Claude 3.7 Sonnet returned a superset of the applicable fees because it never computed the monthly statistics needed to filter them.
- *τ-bench* (arXiv 2406.12045, gpt-4o retail). Of agent failures, 25% are "incorrect decision-making" (rule following), about 55% wrong argument or information (the figure renders garbled in the HTML), and 19% partial resolution of compound requests.
- *TaxCalcBench*: models "reliably fail" the Child Tax Credit and EITC because of complex eligibility.
- *SARA via logic programs* (arXiv 2508.21051). On 100 numeric tax cases, direct accuracy is GPT-5 76/100 and o3 56/100. Cases 91 and 83 ("hiring overlapping groups of people over different periods") were missed by every approach.

**Instantiation.** A rebate tier applies if quarterly volume ≥ X AND the on-time payment
ratio in the *previous* quarter ≥ 95%. "Paid" is defined as the bank value date
(`bank_statement.csv`), not the AP run date (`ap_export.csv`).
- **Right:** 2 of 8 suppliers fail the second condition once value dates are used.
- **Default wrong:** grant the tier on volume, or use AP dates.

**Validity risk and anchor.** Every condition is stated, and the team's measurements say
stated rules are dead. The lever is the interlock: the previous-quarter window plus the
definition of "paid" in a second document.

**Expected miss.** Fable **L–M**, Astra **M**. The GPT-5.5 regression is suggestive for
the OpenAI line, but it was measured single-call without tools.

---

### 11. In-transit treated as in hand

**Definition.** Stock, cash or documents that are expected or in transit are treated as
available.

**Evidence.** *Vending-Bench* (arXiv 2502.15840). Claude 3.5 Sonnet "mistakenly
believ[ed] its orders have arrived before they actually have", and o3-mini "assumes that
items have been delivered when they in fact are in transit". The failures are not
explained by context filling (Pearson r = 0.167 between days until sales stop and days
until memory is full).

**Instantiation.** A reorder plan nets on-hand plus open POs whose ETA has passed. A
carrier email says one shipment is "held at customs pending documents".
- **Right:** exclude it from available stock.
- **Default wrong:** count it because its ETA has passed.

**Expected miss.** Fable **M**, Astra **M** (already measured as working).

---

### 12. Forcing a reconciliation to balance

**Definition.** Faced with a genuine residual, the model matches it to the
nearest-looking item, or fabricates a verification, instead of reporting it as
unexplained.

**Evidence.** *AccountingBench* (Penrose, July 2025; accounting.penrose.com did not render
for me) **[secondary: GIGAZINE, threadreaderapp]**. Claude 4 and Grok 4 stayed above 95%
for several months. Claude fell below 85% by year-end, and Grok dropped sharply in month
5. Gemini 2.5 Pro, o3 and o4-mini "failed to complete a single month". When balances did
not match, Claude and Grok "pulled unrelated transactions" to force reconciliation.
*SpreadsheetBench 2*: after failed checks, an agent claimed "the chart XML confirms all
4 series are present", contradicting its own tool output.

**Instantiation.** A bank reconciliation leaves a 1,240.00 residual. A ledger entry of
1,240.00 exists, but on bank account 1020 and dated after the statement period. A bank
email confirms a duplicate direct debit to be reversed.
- **Right:** classify the residual as a bank error.
- **Default wrong:** match the 1020 entry.

**Anchors:** the account number, the date window and the bank email.

**Expected miss.** Fable **L–M**, Astra **L–M**. Our models re-check, but the "near-amount
plug" interlocks well with keying slips (entry 5).

---

### 13. Over-flagging clean items in verification

**Evidence.** *FinVerBench* (arXiv 2605.29586). With a guided-checklist prompt on
unrounded data, **9 of 14** runs had **95–100%** false positives on clean statements.
Rendering and rounding choices moved recall from 79.0% (rounded) to 100.0% (unrounded)
for the calibrated model.

**Use.** In a review deliverable, include clean rows that look odd but reconcile under the
documents' own rounding convention, and grade false flags. **Validity risk: high.** The
rounding convention must be explicit, or the flag is defensible.

**Expected miss.** Fable **L–M**, Astra **L–M**.

---

### 14. A verdict that contradicts the model's own working

**Evidence.** Deadline paper: 6 of 21 GPT responses (2 of 7 for gpt-5.4) stated a
verdict that contradicted their own correct arithmetic.

**Use.** A secondary check that the status field agrees with the computed date. It is
cheap, but probably low-yield for Python-computing agents.

**Expected miss.** Fable **L**, Astra **L**.

---

### 15. Partial resolution of compound requests and truncated listings

**Evidence.** τ-bench: 19% of gpt-4o retail failures. WorkBench Revisited B.3: a search
capped at 5 results was trusted as complete, which "still occasionally trips up frontier
LLMs". OfficeBench (arXiv 2407.19056): GPT-4o scores 64.52% on single-app, 60.00% on
two-app and 21.43% on three-app tasks (47.00% overall).

**Expected miss.** Fable **L**, Astra **L** in a file-based task where every file is
read. Pointer-style variants are already dead.

---

### 16. Long-horizon drift and inconsistency

**Evidence.** *APEX-Agents* (arXiv 2601.14242). Pass@1: Gemini 3 Flash 24.0%, GPT-5.2
23.0%, Claude Opus 4.5 18.4%. Pass^8 tops out at 13.4%, and "all agents score zero in
at least 40% of their runs". *τ²-bench* (arXiv 2506.07982): telecom pass^1 drops about
18–25% from No-User to dual-control mode, and success falls "close to zero for >7
actions". *AccountingBench*: month-on-month drift.

**Use.** Mostly relevant to two-step tasks: carry a premise from step 1 that step 2's
documents silently revise. The memory notes confirm step 2 runs as a fresh session.

**Expected miss.** Fable **L** and Astra **L** on single-step tasks.

---

### Not a valid difficulty source (listed so nobody builds on it)

- **Formatting and instruction following.** *GDPval* (arXiv 2510.04374): Claude Opus 4.1 wins or ties 47.6%. Claude, Grok and Gemini most often lost on instruction following, and GPT-5 (high) "mainly to formatting errors". About 29% of GPT-5's ratings were "bad" or "catastrophic" (about 3% catastrophic). Gemini and Grok "ignored reference data". These are contract failures, capped at 30% under the team's rules.
- **Ambiguity.** In *Daloopa*, ~50% of errors were "Ambiguous Question Handling". An ambiguous trap is invalid by construction.
- **Policy-legal workarounds.** Claude Opus 4.5 on τ²-bench airline upgraded basic economy and then modified the flight, which the policy did not forbid **[secondary: LessWrong repost; Anthropic system card not read]**. This is a validity warning: frontier models find routes the author did not close.

---

## Where in the workflow do frontier agents fail?

| Stage | What the sources show | Status for Fable 5.1 / Astra in our harness |
|---|---|---|
| **Reading / extraction** | Near-solved on clean digital text. Claude + MCP 91.6% on single-number lookups (Daloopa, vendor). DeepSeek-R1 extraction errors only 5–15% of errors (FinanceReasoning). Payroll simple tiers at 100% for every model (2601.18012). FrontierFinance: "existing finance benchmarks focus on data extraction, which current models have largely mastered". Still fails on hard layouts: OfficeQA Pro "40–50% failure rate attributable to parsing errors" on PDFs; FinSheet-Bench (2603.07316) best model about one error per six questions, falling to a 48.6% average on the largest file; SpreadsheetBench 2 "Insufficient Inspection" | **Not where they fail** on CSV/MD fixtures. The exceptions are multi-line headers, locale number and date formats, and narrative text that amends a table (entry 1) |
| **Joining records** | Residual errors on near-identical keys and target selection (2310.11244; SpreadsheetBench 2 "Wrong Target Selection"); DABstep superset joins | **A live failure point** when an identifier is wrong but attributes are right (keying slips, entry 5) |
| **Choosing which document, version, period or event governs** | The dominant residue in the newest frontier studies: OfficeQA Pro V2 (Fable 5, GPT-5.6 Sol) on revised figures and temporal reconciliation; deadline anchor selection; MedCalc wrong encounter; statutory recency bias; TaxCalcBench FPL year; Daloopa period errors; OfficeQA's first-plausible-instance convergence | **The primary failure point.** Entries 1, 2, 4 and 8 all sit here. It matches the CLAUDE.md doctrine (a premise that changes, or a conflict over which document governs) |
| **Applying a rule** | Condition shortcutting persists in single-call settings (GPT-5.5 66.4% on LegalBench rule application). Eligibility (TaxCalcBench). The textbook prior beats the local convention (TaxCalcBench tables, MedCalc version mismatch, SpreadsheetBench 2 textbook formulas) | Stated rules are dead (650/650). **Implied local conventions are alive** (entry 3); stated multi-condition rules only as interlocks (entry 10) |
| **Arithmetic** | Fails only without tools (FinAuditing CER 70–83%; MedCalc computation 13–33%; LegalBench "$50,000 > $75,000"). With computation: "errors are almost never in the arithmetic" (2608.15270). The residue is **precision and rounding stage** (OfficeQA Pro "majority of remaining errors") | Arithmetic is dead. **Rounding stage under exact checks is alive** (entry 7) |
| **Final formatting** | GDPval (GPT-5 lost mainly on formatting); DABstep ("conversational text instead of outputting a number"); SpreadsheetBench 2 "Format/Output Error" | Real but **invalid as difficulty** (contract failures) |

**Synthesis.** The recent frontier error analyses (OfficeQA Pro and V2, WorkBench
Revisited, SpreadsheetBench 2, the deadline study, the MedCalc audit) agree. Errors that
survive at the frontier come **before** the computation: binding the right
record/period/version/anchor, and keeping a local convention over a familiar prior. Once
the inputs are bound correctly, the frontier model computes correctly. Two recurring
mechanisms explain this:
1. **Premature convergence on the first plausible binding.** OfficeQA: "prematurely converging on the first numerically plausible instance". WorkBench: a capped search result trusted as complete. DABstep: memory "ingested ... in step 1" but overlooked later.
2. **Prior over local.** TaxCalcBench brackets vs tables, MedCalc formula versions, SpreadsheetBench 2 "textbook-correct" formulas, Fable 5's 26.7% parametric parses.

The strongest designs from this survey make **one changed premise feed several checks**:
a restatement in narrative text, an edition fixed by event date, or a defined anchor
plus a suspension. Each is anchored twice and leaves arithmetic and formatting
untouched.

**Validity lessons from the same literature.** Many "hard residues" turn out to be
benchmark defects:
- MedCalc audit: after GPT-5.2-Thinking, **19 of 58** residual errors were ground-truth or evaluation issues and 10 were ambiguous.
- WorkBench fixes touched 56 tasks (8%) directly, or 90–95 (about 14%) with broader fixes.
- τ-airline pass^5 was "under-elicited by nearly 50%" (2605.08545).
- 27–78% of τ-bench "successes" were procedurally corrupt (2603.03116).

This supports the standing rule: every check that no episode passes needs an executed
counterfactual and a reworded-answer pass.

---

## Sources read, with verification status

**Primary, read in HTML, abstract or PDF text:** 2510.04374 (GDPval), 2412.14161
(TheAgentCompany), 2407.19056 (OfficeBench), 2406.14991 (SpreadsheetBench), 2606.29955
(SpreadsheetBench 2), 2305.19308 (SheetCopilot; per-model failure proportions only in a
figure), 2311.11944 (FinanceBench), 2508.00828 (Finance Agent Benchmark; no error
taxonomy), 2507.16126 (TaxCalcBench), 2506.05828 (FinanceReasoning), 2601.06401
(BizFinBench v2), 2510.08886 (FinAuditing), 2605.29586 (FinVerBench), 2603.07316
(FinSheet-Bench), 2608.11683 (FrontierFinance; no error taxonomy in the visible text),
2603.08655 (OfficeQA Pro), 2308.11462 (LegalBench), 2508.03080 (ContractEval), 2508.21051
(SARA via logic programs), 2406.12036 and 2603.02222 (MedCalc-Bench and audit),
2406.12045 (τ-bench), 2506.07982 (τ²-bench), 2502.15840 (Vending-Bench), 2506.23719
(DABstep), 2310.11244 (entity matching), 2601.14242 (APEX-Agents), 2606.13715 (WorkBench
Revisited), 2608.15270 (deadline computation), 2603.12271 (in-context updates),
2605.23497 (German statutory; abstract only), 2601.18012 (payroll), 2607.10059
(AgentAbstain: best paired accuracy 59.5%, Gemini 3.1 Pro), 2603.03116 and 2605.08545
(abstracts), the ICML 2026 condition-trees page, both Databricks OfficeQA blogs, and the
Andon Labs Opus 4.6 Vending-Bench post.

**Secondary, snippet or vendor only:**
- AccountingBench (Penrose page did not render).
- Daloopa (vendor).
- German statutory numbers (aggregator).
- TAT-QA 3% scale errors and FinQA unit-conversion note (snippets of 2105.07624 and 2109.00122).
- MultiHiertt GPT-4 figures (blog only; not used).
- Recency-rerank 25% (2509.11353, snippet).
- DRAGged into Conflicts (2506.08500, snippet: Gemini Flash 2.5 Thinking 74.2 rising to 78.8 on freshness/misinformation conflicts).
- CRMArena-Pro (2505.18878, snippet: ~58% single-turn, ~35% multi-turn, near-zero confidentiality awareness).
- OdysseyBench (2508.09124, snippet).
- Gaia2 (2509.17158, snippet: GPT-5 high 42% pass@1, "fails on time-sensitive tasks").
- Project Vend and the Opus 4.5 τ² loophole (press coverage only).

**Not found:** a published benchmark for invoice three-way matching, procurement
unit-of-measure or VAT-inclusive pricing errors (only vendor pages); a frontier error
breakdown for TAT-DQA, DocFinQA or MultiHiertt; FinSearchComp per-error analysis (the
abstract has none); GDPval per-category loss percentages (they exist only in its Figure
8 image); and an amendment-tracking (superseded-clause) benchmark.
