# R1: New difficulty techniques for non-coding document tasks (beyond the catalogue)

Compiled 2026-10-02 (session date). Read-only with respect to both repositories; this file is the only
file written. Local tool behaviour was checked by executing small scripts in throw-away temporary
directories, which were deleted afterwards (section 6). No local file content or repository detail
was sent to any web service; every web query was generic.

## How to read this

- **Tags.**
  - `[V]`: the number or sentence comes from the source's full text (HTML or PDF), read through a
    fetch tool.
  - `[V,q]`: as `[V]`, and the figure was re-queried as a verbatim quote because a decision depends
    on it.
  - `[A]`: abstract or landing page only.
  - `[S]`: secondary report.
  - `[X]`: executed locally during this research. Command and output are in section 6.
  - *Internal*: the team's own screens, as given in the three local research files.
- **Settings.** `{tools}` means an agent with a shell, code execution or tool APIs. `{no-tools}`
  means a single call or long-context evaluation.
- **Caveat on `[V]`.** The fetch tool returns a summary produced by a model, and the previous
  catalogue found such summaries misstating numbers. Treat any `[V]` figure without `q` as needing a
  second look before it goes into a deliverable.
- **No direct measurement of our pair.** No public source measures Fable 5.1 in Claude Code or
  GPT-6 Astra in Codex on fair, deterministically graded document tasks of this shape. Every
  "expected bite" below is a hypothesis for a 5 x 2 screen, not a result. The team's own memory
  note applies: six earlier briefs were falsified after forks had built on them.
- **What is not repeated.** The 13 modes in `frontier-agent-failure-modes.md` are not repeated
  here. Where a technique overlaps one of them, the overlap is named and only the new part is
  argued.

---

## 0. Bottom line

1. **Three failure sites in the 2026 literature that the catalogue does not cover.**
   - **The file-format layer.** What the agent's parser shows differs from what a human sees in the
     application: strike-through, tracked changes, formulas against cached values, PDF layout.
   - **Faithful implementation of a stated rule.** The numeric or temporal stack silently deviates
     from a rule that is stated in full, and only on specific values.
   - **Auditing an existing artifact.** Finding defects in a workbook is a different task from
     building a new deliverable.

   Evidence for the three sites:
   - SpreadsheetBench 2: the best agent scores 34.89% overall but only 12.00% on debugging
     `[V,q]{tools}`.
   - A 2026 parser benchmark on redlined contracts: about two thirds of the questions can only be
     answered if struck text is recognised. The baseline with strikes dropped is 28.8% against a
     ceiling of 91.9% `[V]`.
   - Finch: models "typically prioritize cell values and under-use formulas" `[V]`.
2. **Why this suits the team's constraints.** The deciding rule can be published in full, with no
   ambiguity, and the failure can still happen: the agent follows the rule and its tool breaks it.
   The internal screens never tested this shape. Every internal "stated rule" could be implemented
   correctly by the obvious code, which is why "published rules are followed almost perfectly".
3. **Global-constraint search is not a lever once the agent can write code.** On TravelPlanner, an
   LLM with a solver reaches 93.9% against 10% for o1-preview alone `[A]`. What survives is
   formalization: implicit constraints found in documents, and the definition of the objective.
   Such tasks need validator graders, not answer comparison: answer sets written by models admit
   only 19–42% of correct solutions `[V]`.
4. **Density arithmetic.** pass@1 ≈ Π(1 − e_i) over independent decisions.
   - Harvey LAB-AA, Fable 5: 93.6% of criteria pass but only 14.2% of tasks `[V]`. That implies about
     30 effectively independent criteria at about 6% error each.
   - At the internal error rate of about 1% per decision, a task needs about 69 independent
     decisions to fall below 0.5. At 5% error it needs 14.
   - So density works only when it is built from decisions whose error rate is at least 5%. Adding
     more of the decisions the models already get right does nothing.
5. **Family skews exist and point in different directions.** Pair an Astra-skewed lever with a
   Fable-skewed lever in every bundle.
   - GPT-family agents lose more on raw-PDF text extraction. In OfficeQA Pro, pre-parsing gives
     GPT-5.4 +20.30 points against +6.02 for Opus 4.6 `[V]`. Reading struck text in text PDFs (as a
     parser), GPT-6 Astra scores 63.3% against 89.1% for Fable 5.1 `[V]`.
   - GPT-6 Astra takes fewer turns: 24 per task at max effort, against about 60 for Claude models
     `[V]`.
   - In Claude Code, the Read tool hands PDFs to Claude as documents and renders page ranges as
     images `[V]`.
   - With longer reasoning, Claude models become more distractible, while o-series models overfit to
     problem framings they recognise `[V]`.

---

## 1. Ranked techniques not in the catalogue

Rank is the expected bite against Claude Code or Codex agents at high effort. It weighs:
- evidence that the failure occurs with tools;
- whether the rule can be stated so that exactly one answer is defensible;
- whether a deterministic grader that derives its targets at grade time is feasible;
- whether the obvious self-check would expose the error (if it would, the bite is lower).

Bite: H = likely to fail more than half of episodes, M = 20–50%, L = under 20%. All are hypotheses.

| # | Technique | One-line mechanism | Strongest external evidence | Bite F / A (hyp.) | Catalogue overlap |
|---|---|---|---|---|---|
| T1 | **Stated rule, silent numeric or temporal betrayal** | A half-away-from-zero cent rule on ties that sit on binary edges; shift hours across a clock change. The rule is published; Python's defaults violate it on specific values | Python docs; `[X]` executions; LAB rounding imprecision (243 criteria flipped); internal arithmetic-convention misses | M / M+ | none (near-miss rank 2 concerns the *reach* of a rule, not its implementation) |
| T2 | **Format-layer semantics invisible to text extraction** | Strike-through in redline PDFs; tracked changes accepted or rejected by author in DOCX. pandoc, python-docx and pdfplumber each choose a reading for the agent | Openbenchmarks redline parsers: baseline 28.8%, Astra 63.3% vs Fable 89.1% on text PDFs; `[X]` python-docx and pdfplumber | L–M (PDF), M (DOCX) / H–M | partial (#6 version in force) |
| T3 | **Spreadsheet model audit** | List the formula defects in a workbook whose cached values are self-consistent, so recomputing values confirms the error | SpreadsheetBench 2 debugging: 12.00% (Opus 4.6), 8.00% (GPT-5.2) | M / M | none |
| T4 | **Latent house basis in prior-period formulas** | "Same basis as Q1–Q2". The basis departs from the textbook only on rows that first appear in Q3, so reproducing the prior quarters cannot reveal it | SpreadsheetBench 2 Case 4 (textbook formulas, 4.11%); Finch; EnterpriseClawBench; KramaBench obscured inputs (62.81% → 12.77%) | L–M / M | partial (#8 local conventions) |
| T5 | **Offline iCalendar semantics** | RRULE plus EXDATE, RECURRENCE-ID overrides, line folding, TZID across a DST change. No pip install is possible offline | `[X]`: naive parsing yields 6 meetings where the true count is 4; RFC 5545; EmailBench calendar-read 8.3% | M / M | none |
| T6 | **Corpus-scale search under vocabulary mismatch** | Thousands of files that cannot all be read; 3–5 decisive facts phrased without the query's words | Agora: 54.7–59.4% for frontier agents with deterministic answers; AA-Briefcase: Fable 5 passes all criteria on 3% of tasks | M / M–H | partial (#1, #10), but a different regime |
| T7 | **PDF table cell migration** | An empty cell beside a wrapped cell lets a clause number ("4.2") land in the amount column | `[X]` pypdf and pdfplumber; OfficeQA Pro parse asymmetry (+20.3 vs +6.0 points) | L / M | none |
| T8 | **Implicit constraints in a global plan, graded by a validator** | Constraints that exist as facts in files (capacity, leave, closures); objective ties resolved by construction | DeepPlanning: global optimization accounts for ~40% of Opus failures; COMPASS: feasibility 70–90% vs optimality 20–50% | L–M / M | none |
| T9 | **Propagation through an aggregate** | A step-2 restatement in one subgroup moves a population statistic, which flips items in *other* subgroups | StateMemBench sequence mode; drift is 44.4% of failures even with perfect retrieval | M / L | extends #2 |
| T10 | **Parser defaults that coerce legitimate codes** | Region "NA" read as NaN; "0123" and "00123" collide; "1.234" read as 1.234; YAML NO read as False | `[X]`; pandas docs; KramaBench missed the "M" missing-value code | L / L–M | none |
| T11 | **Dense policy library with near-duplicate scoped rules** | The deciding rule is one of hundreds; neighbouring rules differ only in scope | CHI-Bench: 13.2% of failures are literal misreadings of a criterion; utilisation-management pass rate falls from 32.0% to 17.3% without the handbook | L–M / L–M | partial (#3 RuleArena) |
| T12 | **Anchoring on an inherited deliverable** (hypothesis, probably weak) | A colleague's register carries one now-wrong derived line forward | Upstream-override study: 94% of harmful cases are copying; auditors recover the origin in 4.1% of cases from reports vs 60.3% from raw documents | L / L | contradicted by internal "narrative about computable fact = dead" |

There are also four design rules that are not traps but change the odds:
- D1, decision-density arithmetic;
- D2, prefer misreadings that produce omissions;
- D3, validator graders with an optimum derived at grade time and a gate of known-correct probes;
- D4, pair the family skews.

They are in section 3.

---

## 2. The techniques

### T1. A stated arithmetic or temporal rule that the default numeric stack silently violates

**Mechanism.** The agent understands the rule correctly. The code it would naturally write returns
a plausible value that is wrong only on specific inputs:
- Python `round()` (half to even), or a float representation that sits just below a tie;
- `Decimal(float)`, or `Decimal(str(float_product))`;
- subtracting two aware datetimes that share one `tzinfo`.

Every self-check re-runs the same arithmetic and agrees with it. This is catalogue #7, the amplifier,
but here the misreading belongs to the tool, not the model. The rescue route the internal census
found, a second independent script, does not help when both scripts share the float path.

**Evidence.**
- Python documentation `[V]`:
  - `round()`: "if two multiples are equally close, rounding is done toward the even choice";
    "`round(2.675, 2)` gives `2.67` instead of the expected `2.68`".
  - Aware datetimes: "If both are aware and have the same tzinfo attribute, the tzinfo attributes
    are ignored ... No time zone adjustments are done in this case."
- `[X]` (section 6, E1–E3):
  - `round(2.625,2)=2.62` and `round(2.675,2)=2.67`, while `pandas.Series.round` gives 2.68 for
    2.675. The two common APIs disagree on the same value.
  - `3*0.145 = 0.43499999999999994`, so even `Decimal(str(x)).quantize(..., ROUND_HALF_UP)` returns
    0.43. The exact answer is 0.44.
  - `7*1.245`: `round` and `Decimal(float)` both give 8.71. The exact answer is 8.72.
  - A London shift from 22:00 on 25 Oct 2025 to 06:00 on 26 Oct 2025: naive subtraction gives 8:00
    and subtraction with the same `ZoneInfo` on both ends also gives 8:00. Converting to UTC gives
    9:00, and pandas `tz_localize` gives 9h.
- Exactness is what professional graders punish:
  - Applied Compute's Harvey LAB case study `[V]`: a base model "often rounding figures during math
    (like 1.9 to 2) ... punished by legal graders"; fixing it "flips 243 criteria".
  - OfficeQA Pro `[V]`: "intermediate rounding that results in cascading imprecision".
- **Internal.** Arithmetic convention is rank 2 of the fragile decision types: 13 failed decisions,
  8 of them fair, 10 of the 13 by Astra. Rescues came from an independent recomputation.
- **Published rate for frontier agents on float ties or DST arithmetic: none found.**

**Expected bite.** Medium for both; somewhat higher for Astra.
- Astra writes the deliverable from Python in 92% of steps and asserts invariants in 98%. Those
  assertions run on the same arithmetic.
- Fable computes in Python and then transcribes the values, so its transcription inherits the
  float result.
- The trap is binary per strategy. An agent that does Decimal arithmetic from the source strings end
  to end passes every tie; any float path fails several. Expect bimodal outcomes, and combine T1
  with an independent lever.

**Recipe A: cent rounding.**
- *Files.*
  - `billing_policy.md`: one paragraph, written as the business would state it. "VAT is calculated
    on each invoice line and rounded to the nearest cent; an exact half cent is rounded away from
    zero. Invoice VAT is the sum of the rounded line VAT."
  - `price_list.csv`: unit prices to 3 decimals, stored as text.
  - `orders.csv`: about 40 lines with quantities.
  - `vat_rates.csv`.
  - Optionally, last month's register as a format exemplar, containing no tie lines.
- *Tie lines (5–7).* The exact decimal line VAT or line net ends in a half cent:
  - 2 lines that are exact binary ties (such as 2.625): half-to-even fails;
  - 2 lines whose float product lands just below the tie (such as 3 × 0.145): `Decimal(str(x))`
    fails;
  - 1 line whose float lands just above the tie: a control that naive code passes;
  - 1 tie where half-even and half-up coincide: a control.
  - Search (quantity, price, rate) triples programmatically to find these.
- *Instruction (WHAT only).* "Prepare March's VAT register under our billing policy: each invoice's
  net, VAT and gross, and the VAT total per rate." Never mention floating point, Decimal or
  "careful rounding".
- *Grader.* Recompute with Python `Decimal` from the fixture's text fields at grade time. Exact to
  the cent: no tolerance and no floats.
- *Proof of one defensible answer.* The policy fixes the unit (cent), the tie direction (away from
  zero), the stage (line) and the aggregation (sum of rounded lines). Inputs are exact decimals.
  Executed counterexamples, each producing a different register on at least one line:
  - `round()`;
  - `Decimal(float)`;
  - `Decimal(str(float product))`;
  - invoice-level rounding;
  - half-even.

  A reworded or reordered correct answer passes. Flipping one quantity moves the target.
- *Checks routed through the ties.* Per-invoice VAT for the affected invoices, VAT total per rate,
  grand gross, and the count of invoices over a VAT threshold (place one tie at the threshold).

**Recipe B: hours across a clock change.**
- *Files.*
  - A roster with local wall times; the header says "All times are UK local time".
  - The company calendar, which among bank holidays includes "Clocks go back (26 Oct)" and
    "Clocks go forward (30 Mar)".
  - A pay policy: "Pay is for hours actually worked; hours beyond 8 in a shift are overtime at 1.5x."
- *Affected population.* 2–4 shifts span a transition. A 22:00–06:00 shift over the autumn change is
  9 h; over the spring change it is 7 h. No clock-in falls inside the repeated or the missing hour.
- *Instruction.* "Prepare October's hours and pay register."
- *Grader.* Convert with `zoneinfo` to UTC. Counterexamples: naive subtraction, and subtraction of
  two aware datetimes with the same zone (both 8 h, `[X]`).

**Failure risks.**
- Negative ties: −2.625 under "half up" differs from "away from zero". Use the "away from zero"
  wording, or keep ties positive.
- The rounding *stage* must be pinned. The internal business-monetisation case, where the stage
  was not pinned, was contested.
- A grader written with floats would reproduce the trap. Lint the grader.
- Anything that sounds like a hint ("note: banker's rounding") announces the trap.
- DST counts as world knowledge only if the zone is stated and a calendar entry names the change.
  Keep both.

### T2. Format-layer semantics that text extraction cannot see

**Mechanism.** In real professional documents, some of the meaning is carried by formatting that
does not exist as text:
- strike-through in a comparison or redline PDF is a drawn line, not a character attribute;
- in DOCX, tracked insertions and deletions carry an author and are accepted or rejected per party;
- comments carry rulings.

The default extractors decide the reading for the agent, and each decides differently:
- pdfplumber and pypdf emit struck words as live text (`[X]` E9: "shall give ten three five
  business days' notice").
- python-docx 1.2.0 drops every run inside `w:ins` *and* `w:del` (`[X]` E7: "Payment is due within
  days of invoice.").
- pandoc accepts all changes by default and ignores comments (pandoc manual `[V]`: `accept`
  "(default) processes all the insertions and deletions"; "Both accept and reject ignore
  comments").
- Anthropic's public docx skill tells Claude to read with `pandoc -t markdown file.docx` `[V]`. If the
  harness exposes that skill, the accept-all view is the default.

**Evidence.**
- Openbenchmarks, "Parsers on Redlined Contracts" (updated 2026-09-27) `[V]`: 94 contracts and 1,500
  questions, one question per edit.
  - Baseline with "every character unmarked" (the strike dropped): 28.8%. Best case: 91.9%.
  - Text PDFs: Claude Fable 5.1 89.1% (95.5% of the gap closed); **GPT-6 Astra 63.3% (54.6%)**.
  - Scanned PDFs: GPT-6 Astra 91.3%; Fable 5.1 not reported.
  - The benchmark's own example: "the notice period was negotiated down from ten days, then to three,
    and settled at five, each earlier number struck in place".
  - Setting: models used as parsers, not as agents.
- Claude Code tools reference `[V]`: "Claude reads short `.pdf` files whole. For PDFs longer than 10
  pages, it reads in ranges ... Page-range reads render pages with `pdftoppm`." Fable therefore
  usually *sees* strike-through in PDFs. Claude Code has no native DOCX renderer.
- **Published agent-level rate: none found.** The evidence is at parser level, plus the executed
  mechanisms.

**Expected bite.**
- Struck text in PDFs: high to medium for Astra in Codex, through its text-extraction path (whether
  Codex renders PDF pages is not publicly documented; check the trajectories). Low for Fable.
- Per-author DOCX changes: medium for both. There is no visual path, and every default reading is
  wrong for some clause.

**Recipe A: redline PDF (Astra-skewed).**
- *Files.*
  - `fee_schedule_v4_compare.pdf`: a comparison PDF with the standard legend on its cover
    ("Insertion" underlined; "Deletion" struck). It contains:
    - 2 fee rows struck whole;
    - 1 struck *trailing* exception ("five business days~~, or ten for Saturday deliveries~~");
    - 1 multi-round value.
  - An email: "v4 is the agreed position."
  - An order log of 30 rows to be priced.
- *Avoid garbling.* Prefer deletions with no replacement text (struck rows and struck trailing
  clauses). They read fluently when extracted, so no visible garble invites a second look. The
  internal census shows that alternatives a model can name side by side are enumerated and rejected.
- *Instruction.* "Price April's orders under the agreed fee schedule and list the fees that apply to
  each order."
- *Grader (derived).* At grade time, find the characters overlapped by horizontal line objects at
  x-height in the PDF (pdfplumber geometry), derive the live text, and parse the schedule from it
  with fixed anchors.

**Recipe B: per-author tracked changes (both families).**
- *Files.*
  - `msa_redline.docx`, with tracked changes by people from two parties.
  - `who_is_who.md`, mapping people to parties.
  - An email: "We have accepted all of Halden's changes; Halden rejected ours to 9.2 and 14.1."
- *Effect on each default reading.*
  - python-docx omits Halden's insertions.
  - pandoc's default accept view keeps our rejected insertion and drops our rejected deletion.
  - Reading every `w:t` element is the same as accepting everything.
- *Instruction.* "Build the obligations register for the agreement as it will be signed: each
  obligation, its owner, the deadline in days, and the liability cap that applies."
- *Step 2.* A new email: "Halden has now accepted our change to 14.1". This moves one or two
  register lines.
- *Grader.* Parse the OOXML at grade time, apply acceptance by `w:author` → party, then extract the
  fields with fixed anchors.

**Proof of one defensible answer.**
- The legend defines the notation.
- The acceptance email is the only record of acceptance.
- Each changed clause has exactly one operative reading.
- Executed counterexamples: `extract_text`, python-docx text, pandoc accept, pandoc reject, and
  all-`w:t`. Each fails at least one check. A rendered human view yields the target.

**Failure risks.**
- Visible garble ("ten three five") invites rendering and lowers the bite. Use deletions without
  replacements.
- Scanned PDFs remove the Astra skew (Astra scores 91.3% on scanned).
- Comments may decide nothing unless an email makes them the record.
- Do not make "which version is in force" the question as well. Keep catalogue #6 separate, or the
  two levers will be confounded.

### T3. Spreadsheet model audit: formula-level defects behind self-consistent cached values

**Mechanism.** The deliverable is a list of defects in an existing workbook.
- The workbook is saved by LibreOffice after the defects are introduced, so cached values are
  consistent with the formulas. Every footing ties and value-level recomputation confirms the
  numbers.
- Each defect is visible only by reading the formula's meaning against the row labels and the
  model's written conventions.
- pandas reads cached values only (`[X]` E6). Agents "prioritize cell values and under-use formulas"
  (Finch).
- The obvious check, "does the model recalculate cleanly?", passes. Anthropic's own xlsx skill warns
  that "A green recalc proves your formulas *evaluate*, not that they are *right*" `[V]`.

**Evidence.**
- **SpreadsheetBench 2** (2026, arXiv 2606.29955) `[V,q]{tools: SWE-agent, bash, view_xlsx, openpyxl,
  pandas, LibreOffice; at most 50 turns}`. Debugging, as modification / accuracy:
  - Claude Opus 4.6: **50.38 / 12.00**;
  - GPT-5.2: **39.07 / 8.00**;
  - overall best: 77.20 / 34.89.
  - The 10 defect classes `[V]`: double counting, embedded hardcodes, error values, inconsistent
    colour, incorrect average range, broken cross-sheet references, misaligned INDEX-MATCH,
    incorrect sign, relative vs absolute references, unit mismatch.
  - Dominant failure categories: "Insufficient Inspection and Wrong Target Selection".
  - Case 1: the agent "correctly identified three bugs" but "explicitly deprioritized Bug C".
- **Finch** (FinWorkBench, rev. 2026-04) `[V]{tools}`. Error taxonomy for Claude Sonnet 4.5:
  formula reasoning 35%, data retrieval 25%, code generation 25%, task misunderstanding 10%,
  rendering 5%.
- **FLARE** (EuSpRIG 2025) `[A]`: models produce "plausible yet incorrect outputs" on multi-step
  spreadsheet logic.

**Expected bite.** Medium for both.
- Our harness has no turn limit and the workbook is smaller than SpreadsheetBench 2's average of
  21.1 sheets, so expect less bite than 12%.
- Astra takes fewer turns (AA: 24 per task), which suggests less inspection.

**Recipe.**
- *Files.*
  - `forecast_model.xlsx`, 7–9 sheets: Assumptions, Revenue, Costs, Headcount, P&L, Cash, Summary.
  - `model_conventions.md`:
    - costs are negative;
    - all sheets are in EUR thousands except Headcount (FTE);
    - every input lives on Assumptions;
    - the only literals allowed in formulas are the listed constants;
    - the defect classes are a **closed list**: double count, hard-coded input, wrong range, drifting
      reference, unit mismatch, sign error, wrong feeder.
- *Defects.* Plant 6–8, spread across classes, each touching one contiguous range. Example: a
  copied formula whose relative reference drifts to the wrong rate row from month 7 onwards.
- *Decoys.* 4–6 cells that look wrong but are documented: an allowed constant; a refund line with an
  intentional sign; a hardcode that the note lists.
- *Instruction (WHAT).* "Before the board sees the forecast, list every formula defect, with the
  cells it affects and which convention it breaks, and give FY2026 EBITDA and closing cash as they
  should be."
- *Grader.*
  - Exact set equality on defect IDs. A reported cell maps to a defect if it lies inside the
    defect's range, and the class label must match.
  - The corrected figures come from an independent implementation of the documented model logic,
    run from the Assumptions inputs at grade time.
  - Optionally, a count per class.
- *Proof of one defensible answer.* Run a structural linter over every formula:
  - row-pattern consistency across columns;
  - every literal is in the allowed list;
  - cross-sheet references point only to the permitted feeder;
  - a sign map by row type;
  - a unit map by sheet.

  It must flag exactly the planted ranges and pass the documented decoys. Each misreading's
  counterexample (missing a defect, flagging a decoy) fails the defect set and moves the corrected
  EBITDA.

**Failure risks.**
- Unintended anomalies, the main risk. The linter is the guard.
- Granularity disputes. Match on ranges, not on single cells.
- "Fix" against "list": ask only for the list and the corrected figures, never for edits.
- The class list must be closed, or "is this a defect?" becomes a judgment call.

### T4. Latent house basis encoded only in prior-period formulas

**Mechanism.** The instruction says what a manager would say: "Complete Q3 on the same basis as
Q1 and Q2".
- The house basis departs from the textbook definition. Examples: net debt counts long-term
  borrowings only; EBITDA excludes general-ledger rows tagged `NR`, through
  `SUMIFS(..., "<>NR")` or a named range `NonRecurring_Excl`.
- The departure is **inactive in Q1–Q2**: there are no `NR` rows and no short-term borrowings. The
  textbook formula therefore reproduces the prior quarters exactly, and an agent that checks itself
  against the known quarters is reassured. This removes the rescue the internal census observed
  (asserting that the chosen unit reproduces a known figure).
- Q3 has 1–3 affected rows.
- The basis is explicit in the formulas and nowhere in prose. pandas never shows it.

**Evidence.**
- SpreadsheetBench 2, Case 4 `[V]`: the agent "derived formulas from general financial knowledge
  rather than examining how similar rows in the same workbook compute their values", scoring 4.11%
  modification accuracy.
- SpreadsheetBench 2, Case 3 `[V]`: the agent copied a numerator pattern "without any explicit
  reasoning". This is the copying direction, so both directions occur.
- Finch `[V]`: "Formulas encoding latent logic ... models typically prioritize cell values and
  under-use formulas".
- EnterpriseClawBench `[V]{Claude Code, Codex}`: marketing and finance tasks "combine heavy document
  comprehension ... with company-specific scenarios and conventions. These tasks are less common in
  public data, which may partly explain their lower scores."
- KramaBench `[V]{tools}`: with identifiers obscured, the Claude Reflexion baseline falls "from
  62.81% to 12.77%". Systems lean on what they already know.
- Harness-IF `[A]{coding agents, 12 frontier models}`: against-prior rules score 3.6–7.4 points lower
  (mean 5.81). A rule that is *stated* loses only a little to the prior, consistent with the
  internal data.
- "Thinking Fast, Thinking Wrong" `[A]`: chain-of-thought helps much less on counter-intuitive cases
  (OR = 0.278).
- Inverse Scaling in Test-Time Compute `[V]`: o-series models "attempt to apply complex solutions"
  when a task resembles a well-known one. This is the GPT side of the prior trap.

**Expected bite.** Low to medium for Fable, which reads formulas once told "same basis". Medium for
Astra, which programs from values.

**Recipe.**
- *Files.*
  - `kpi_pack.xlsx`: Q1 and Q2 columns computed by formulas that embody the house basis; a cover cell
    reading "Prepared on the group basis"; an Adjustments sheet recording "Q2 only: one-off audit
    true-up of 140", hard-coded in Q2. That hardcode is the trap for agents that copy everything.
  - `gl_export_q3.csv`: Q3 raw lines, including the `NR` rows.
- *Instruction.* "Complete Q3 on the same basis as Q1 and Q2 and give net leverage and adjusted
  EBITDA for the quarter."
- *Grader.* Apply the formula structure of the Q1–Q2 cells to the Q3 inputs at grade time, without
  carrying the Q2 adjustment.
- *Proof of one defensible answer.* The formulas are unambiguous and identical in Q1 and Q2. The
  textbook reading agrees with every Q1–Q2 value and differs only in Q3. The Q2 adjustment is
  documented as Q2-only.

**Failure risks.**
- If the house basis could be read as an error to fix, the task becomes ambiguous. Make it plainly
  intentional (a named range, the "group basis" note) without stating the rule in prose. Stating it
  in prose turns this into catalogue #8, which is solved.

### T5. Offline iCalendar semantics

**Mechanism.** A calendar export (`.ics`) carries five things a naive reading gets wrong:
- RRULE expansion;
- EXDATE exclusions, often folded over two lines;
- RECURRENCE-ID overrides that move or cancel one instance;
- TZID with a VTIMEZONE across a DST change;
- RFC 5545 line folding.

The agent works offline and cannot install a correct expander. Depending on the image, it may not
have `icalendar` at all and must hand-roll RFC 5545.

**Evidence.**
- `[X]` E10:
  - a naive line reader truncates a folded EXDATE to `20250324T09000`;
  - `dateutil.rrule` alone yields 6 occurrences, including an excluded one and the original slot of
    a moved one;
  - a full expander (`recurring_ical_events`) yields 4, with the UTC offset changing after 30 Mar.
- RFC 5545 `[V]`: lines over 75 octets "SHOULD be split"; unfolding removes "the CRLF and the linear
  white-space character that immediately follows"; RECURRENCE-ID identifies a specific instance.
- EmailBench (2026) `[V]{tool APIs}`: Claude Sonnet 4.5 scores 8.3% on calendar-read and 16.7% on
  calendar-write, against 80–89% on filters and folders. 99.7% of its API calls were valid, but only
  33.5% of scenarios passed.
- **No published rate for frontier code agents expanding raw ICS.**

**Expected bite.** Medium for both; higher if the task image lacks `recurring_ical_events`. Check
the image.

**Recipe.**
- *Files.*
  - `team_calendar.ics`, a realistic export with VTIMEZONE: 3–4 recurring series. One has a folded
    multi-value EXDATE; one has a RECURRENCE-ID override moving an instance into a leave day; one
    has an override with `STATUS:CANCELLED`; one has TZID America/New_York while attendees are in
    London across the 9–30 Mar window when the UK and US offsets differ.
  - `approved_leave.csv`.
  - `room_bookings.xlsx`.
- *Instruction.* "For Q1, list every steering-group session that clashes with a member's approved
  leave, and each member's total steering-group hours."
- *Grader.* A vendored RFC 5545 expander, run at grade time. At build time, prove that it agrees
  with a second, independent implementation on this fixture.
- *Proof of one defensible answer.* RFC semantics, plus what any calendar application displays.
- *Avoid.* `RANGE=THISANDFUTURE`, duplicate master components for one UID, floating times. These are
  edges where implementations disagree.

**Failure risks.** Library disagreement makes the grader invalid. The two-implementation agreement
check at build time is mandatory.

### T6. Corpus-scale search under vocabulary mismatch (a regime change)

**Mechanism.** The folder holds more text than any agent will read: thousands of emails, chat
messages and memos. The 3–5 decisive facts are phrased without the question's vocabulary, so grep
fails (catalogue #1 covers the lexical proxy). Unlike the internal fixtures, exhaustive reading is
impossible, so "incomplete inspection" becomes reachable.

The internal finding that breadth is anti-correlated with difficulty was measured on fixtures the
agent could read in full; it does not test this regime.

**Evidence.**
- **Agora** (2026-06) `[V]{bash-only mini-swe-agent, maximum reasoning, deterministic numeric
  answers}`: 362 questions over 9,664 documents (372M tokens).
  - Gemini 3.1 Pro 59.39%, GPT-5.5 54.70%.
  - Errors are "dominated by the three evidence-grounded categories (II, EM, INF)": incomplete
    inspection, evidence misidentification, instruction non-following. "the bottleneck lies in
    locating and applying evidence rather than in computation".
  - GPT-5.5 hits resource exhaustion in 24.59% of runs.
- **AA-Briefcase** (2026-06-18) `[V]`: about 2,000 source files, including 3,500 emails and 25,000
  Slack messages. Fable 5 "satisfies all criteria correctly on only 3% of tasks". More capable models
  "fail to fulfill all task requirements, including those embedded in the original task or hidden
  across source files".
- **Workspace-Bench 1.0** (2026-05) `[V]`: best configuration about 60% against 80.7% for humans;
  "lineage tracing" is the bottleneck.
- OfficeQA Pro (catalogued): an 89,000-page corpus.

**Expected bite.** Medium for Fable; medium to high for Astra (fewer turns, resource exhaustion).

**Recipe.**
- Generate a corpus of 2,000–5,000 items with controlled facts.
- The decisive facts are paraphrased, carry no keyword, and some sit in attachments or another
  language (combine with catalogue #11).
- Add near-duplicate decoys that differ in scope.
- The answer is deterministic and numeric.
- *Grader.* Uses per-record attributes held only in grader data (catalogue rule R9).
- *Uniqueness.* The generator writes no other mention of the decisive entities. Prove this with a
  fuzzy search over the corpus at build time.

**Failure risks.**
- Authoring cost and image size.
- Proving that no stray document changes the answer.
- Measurement time grows.

### T7. PDF table cell migration

**Mechanism.** In a PDF table without ruling lines, an empty cell next to a wrapped cell makes text
extraction attach the wrapped cell's trailing token to the wrong column.

**Evidence.**
- `[X]` E8: pypdf and pdfplumber `extract_text` both place "4.2" (from "Disputed – see clause 4.2")
  on the row of an invoice whose amount cell is empty ("INV-105 Storage 4.2"). `extract_tables`
  returns `[]`.
- OfficeQA Pro `[V]`: parsing failures include "shifted or missing rows and columns". Parser choice
  alone moves accuracy by up to 22 points. Pre-parsing helps GPT-5.4 by +20.30 points and Opus 4.6
  by +6.02.

**Expected bite.** Low for Fable, which reads short PDFs visually. Medium for Astra.

**Recipe.**
- *Files.* A supplier statement PDF of 25–40 rows. Three rows have an empty amount next to a wrapped
  cell containing a number-like token (a clause reference, "14 units", "12.05").
- *Instruction.* "Reconcile the statement to our ledger: the undisputed balance and the items not
  in our ledger."
- *Grader.* Derive the column assignment at grade time from the PDF's header x-ranges.
- *Uniqueness.* The visual layout is unambiguous.

**Failure risks.** An agent that renders the pages passes. This is an Astra-side lever only.

### T8. Implicit constraints in a global plan, graded by a validator against an optimum derived at grade time

**Mechanism.** Search is solved once a coding agent has formalized the problem. What remains is
*formalization*:
- constraints that exist as facts in documents (a room's capacity changed in a facilities email;
  leave recorded under a different name form; a site closed on a local holiday listed in a
  handbook);
- the exact objective.

**Evidence.**
- DeepPlanning (Qwen, ACL 2026) `[V]{tool APIs, no free code}`:
  - Travel case accuracy: GPT-5.2-high 35.0%, with a commonsense score of 88.5; Claude Opus 4.5
    (reasoning) 22.7%.
  - Across 140 Opus failures: information acquisition about 25%, local reasoning about 35% (the
    implicit-constraint subcategory had 86 travel and 21 shopping instances), global optimization
    about 40%.
  - Construction: "candidates in databases are automatically adjusted so that exactly one optimal
    solution exists".
  - Implicit constraints are "discoverable only through tool use".
- COMPASS (2025-10, v2) `[V,q]`: feasibility 70–90% against optimality 20–50% for closed models.
  Claude Sonnet 4.6's OR-10% "increased from 57% to 66% when given code execution tools"; "Writing
  code does not make the problem trivial".
- LLM with formal verification on TravelPlanner `[A]`: 93.9% against o1-preview's 10%.
- SCHEDBench (EMNLP Findings 2026) `[A]`: surface-form variation alone reduces feasibility; reordering
  constraints shows "the clearest above-noise sensitivity".

**Expected bite.** Low to medium for both. The internal "rules held as data" design was solved in
small folders, so the facts must not be presented as rules.

**Recipe.**
- *Task.* A timetable or roster for 6–10 sessions, people and rooms.
- *Instruction (WHAT).* "A valid timetable respects room capacity, people's approved leave and site
  opening days; among valid timetables, use the fewest travel days."
- *Facts.* 3–4 implicit facts in the files, each a fact rather than a rule.
- *Grader.*
  - A validator checks each constraint against the files.
  - The objective must equal the optimum, which the grader computes by exhaustive search from the
    fixture at grade time.
  - Every optimal plan passes. Uniqueness is optional, enforced by DeepPlanning-style adjustment
    if a single reported plan is wanted.
- *Uniqueness proof.* Exhaustive enumeration at build time.

**Failure risks.**
- If any fact is stated as a rule ("note that Room B now seats 8"), the lever is dead.
- An objective with ties needs explicit tie-breaking or acceptance of every optimal plan.

### T9. Propagation through an aggregate (extends catalogue #2)

**Mechanism.** Step 1 classifies items against a threshold *relative to the population*: "suppliers
more than 10 points below the portfolio on-time rate". Step 2 restates one subgroup's rows. The
portfolio rate moves, and items in *other* subgroups flip, although their own rows did not change.
An agent that patches only the restated rows misses the flips.

**Evidence.**
- StateMemBench (2026-08) `[V]{memory systems, small and medium models}`: its "sequence" mechanism is
  "derived value not recomputed after input changes". Even with perfect retrieval (the LongMemEval
  oracle), 44.4% of DeepSeek-V4-Flash's failures are state drift.
- AvalancheBench `[A]`: "early analytical mistakes propagate into later conclusions".
- Internal: Fable reads its step-1 file in 94% of step-2 runs and has fitted rules to its own wrong
  step-1 figure (thesis-002).

**Expected bite.** Medium for Fable; low for Astra, which re-runs its whole pipeline.

**Recipe.**
- Keep it small: 2–3 flips outside the restated subgroup, and 1 item inside it that does *not*
  flip (the anti-trap).
- The step-2 instruction restates the threshold definition (required, since step 2 is a fresh
  session) but not the cascade.
- *Grader.* Recompute from the files.

**Failure risks.** The restated definition may cue a full recomputation.

### T10. Parser defaults that coerce legitimate codes

**Mechanism and evidence.** `[X]` E4, E12; pandas docs `[V]`.
- `read_csv` turns "NA", "N/A", "NULL" and similar values into NaN, and `groupby` silently drops NaN
  keys: a North America row worth 250 vanishes from the per-region table (total 400; groups sum
  to 150).
- Codes "0123" and "00123" both become 123, and a lookup dict keeps the last ("Prepaid rent").
- German-format "1.234" and "12.500" are read as 1.234 and 12.5.
- PyYAML reads `NO` as False, `off` as False, `1.10` as 1.1 and `0123` as 83 (octal).
- KramaBench `[V]`: systems failed to identify missing values encoded as "M".

**Expected bite.** Low for Fable; low to medium for Astra. The natural assertion that "the region
sum equals the total" exposes the NA drop. Prefer designs where the natural invariant still passes:
a filter that returns an empty set; a dict collision; a column where every value is a valid number.

**Recipe.**
- *Files.* A region code list in a separate document that defines `NA` as North America; a chart of
  accounts with both codes listed as different accounts; a German-format supplier export whose
  header names the currency and which contains one "1.234.567" value to disambiguate the format.
- *Grader.* Parse everything as strings.

**Failure risks.** "NA" must be impossible to read as "not available". The region list settles it.

### T11. Dense policy library with near-duplicate scoped rules

**Evidence.**
- CHI-Bench (rev. 2026-09-30) `[V]{Claude Code, Codex and others; 87 MCP tools; a handbook of more
  than 1,290 documents}`:
  - best pass@1 28.0% (Claude Code + Opus 4.6);
  - strict pass^3 18.7% (Claude Code + Opus 4.6) against 9.3% (Codex + GPT-5.5);
  - failures: policy compliance ("literal misreading of criterion text") 13.2%, skipped required
    steps 18.7%;
  - removing the handbook drops utilisation management from 32.0% to 17.3%.
- RuleArena is catalogued.

**Expected bite.** Low to medium. Grep finds rules by keyword; the bite needs scope-only
differences, which is catalogue #1 and #3 territory.

**Recipe.** A handbook of 150–300 rules in which 3–4 clusters of near-duplicates differ only by
region, product or effective date. 10–15 cases each fall under exactly one rule of a cluster. The
grader applies the per-case rule IDs held in grader data.

### T12. Anchoring on an inherited deliverable (hypothesis, probably weak)

**Evidence.**
- "When Upstream Messages Override Correct Answers" (2026-09-29) `[A]`: wrong upstream messages
  flipped correct downstream answers in up to 32% of cases; 94% of those were direct copying.
- "Audit Without Verification" (2026-09-07) `[A]`: an auditor reading filed reports recovers the
  fault's origin in 4.1% of cases, against 60.3% from the raw documentation.
- "The Illusion of Diminishing Returns" (ICLR 2026) `[A]`: models err more often when their earlier
  errors are in context.
- **Internal evidence against it.** A narrative or self-claim about a computable fact is re-derived
  from raw data. Expect a low bite unless the inherited value cannot be recomputed without a
  judgment (then combine with catalogue #1 or #2).

---

## 3. Design rules that change the odds

**D1. Decision-density arithmetic (all-pass scoring).** With independent decisions,
pass@1 ≈ Π(1 − e_i).
- Harvey LAB-AA, Fable 5: 93.6% criteria, 14.2% tasks `[V]`. ln 0.142 / ln 0.936 ≈ 29.5 effectively
  independent criteria at about 6.4% error.
- DeepPlanning, GPT-5.2-high: commonsense score 88.5 against 35.0% of cases correct `[V]`, about 8.6
  effective constraints.
- With the internal per-decision error of about 1%: n ≥ 69 decisions for pass@1 < 0.5. At 5%:
  n ≥ 14. At 10%: n ≥ 7.
- Consequences:
  - (a) Spend the budget on decision types whose per-attempt error can reach 5% or more: T1–T5,
    catalogue #1–#3, and the near-miss ranks 1–5.
  - (b) Correlated decisions (one misreading feeding several checks) do *not* multiply. They turn
    one failure into several failed checks, which pass@1 counts once.
  - (c) The step-2 premise change adds an independent decision only if it uses a different
    mechanism from step 1.

**D2. Prefer misreadings that cause omissions.**
- "Judging Is Not Enumerating" (2026-08) `[V]`: models "detect planted over-inclusions 6–7x more often
  than planted omissions".
- The capable-model failures in the dense benchmarks are omissions:
  - AA-Briefcase: requirements "hidden across source files" `[V]`;
  - Workspace-Bench: "Missing Content" is the largest category `[V]`;
  - CHI-Bench: 18.7% skipped required steps `[V]`.
- Design each trap so the tempting reading drops a member (python-docx dropping an insertion; a
  struck exception kept as live text that *removes* an order from the set), rather than adding one,
  which a self-review is more likely to notice.

**D3. Graders for tasks with several valid solutions: validate, never compare against an authored
set.**
- Authored acceptable sets admit only 19–42% of correct solutions, and 70% of their failures are
  invented requirements `[V]`.
- Use per-constraint validators plus an objective optimum derived at grade time (T8). Construct a
  unique optimum (DeepPlanning) or accept every optimal plan.
- Gate every grader with at least 3 *distinct* known-correct probe solutions. The same paper's gate
  cut false rejection from 58–92% to at most 5%.
- For extraction-style traps (T2, T7), derive the target from the fixture's geometry or OOXML at
  grade time, not from the author's notes. That keeps the team's rule that answers are derived,
  never stored.

**D4. Pair the family skews in every bundle.**

| Lever | Evidence of skew | Likely victim |
|---|---|---|
| Raw-PDF text extraction (T2-PDF, T7) | OfficeQA Pro pre-parsing gain +20.3 (GPT-5.4) vs +6.0 (Opus 4.6) `[V]`; struck text in text PDFs 63.3 (Astra) vs 89.1 (Fable 5.1) `[V]`; Claude Code renders PDFs `[V]` | Astra |
| One-pass programmatic predicate, few turns (T1, T10, T6) | AA: Astra 24 turns per task vs about 60 for Claude `[V]`; internal: Astra writes from code in 92% of steps and fails exact-host predicates 8/70 | Astra |
| DOCX with no renderer (T2-DOCX) | Claude Code has no DOCX viewer; pandoc and python-docx defaults `[V][X]` | both |
| Silent unit or scope boundary, counter-intuitive basis (T4, T9, catalogue #1) | Inverse scaling: Claude distracted by irrelevant information as reasoning lengthens `[V]`; internal: only scoped semantic judgments bit Fable (4/10) | Fable |
| Familiar framing with one altered premise (T4) | o-series models overfit to familiar problem framings `[V]` | Astra |
| Strict consistency across repeats | CHI-Bench pass^3: Codex + GPT-5.5 9.3% vs Claude Code + Opus 4.6 18.7% `[V]` | Astra (weak evidence) |

---

## 4. Short answers to the seven research questions

1. **Tool betrayal.**
   - **Mechanisms verified by execution** (section 6):
     - round-half-even and float ties;
     - pandas `round` disagreeing with built-in `round`;
     - `format="mixed"` parsing each element independently (it read "03/04/2025" month-first and
       "13/04/2025" day-first in the same column);
     - two-digit years: dateutil 2068 and 2069, strptime 2068 and 1969;
     - Excel serial origin;
     - `read_excel` reading only the first sheet;
     - stale cached formula values; `data_only` returning None on openpyxl-written files;
     - hidden rows, strike-through, comments and number formats invisible to pandas;
     - python-docx dropping `w:ins` and `w:del`;
     - PDF strike-through and cell migration;
     - ICS folding, EXDATE and RECURRENCE-ID;
     - same-zone datetime subtraction;
     - NA, leading-zero and European-format coercion;
     - YAML 1.1 booleans and octal;
     - JSON duplicate keys (last wins).
   - **Published evidence that frontier agents fall for any of them specifically: none found.**
   - Nearest evidence:
     - format-level: redlined-contract parsing (28.8% baseline; Astra 63.3% as a parser on text
       PDFs);
     - spreadsheet-level: SpreadsheetBench 2 (12.00% / 8.00% on debugging), Finch (formula reasoning
       35% of errors; values preferred over formulas), BlueFin (sign, date-axis and rate-vs-amount
       errors);
     - tool-output level: ToolMaze, implicit semantic failures cut recovery by 37.15 points against
       explicit ones, "systemic over-trust in corrupted outputs" `[V]`.
   - The ones that are both fair and silent are T1, T2, T5 and T7. Hidden rows and sheets, stale
     caches and display rounding are fair only if a document pins their meaning, which announces
     them (section 5).
2. **What-not-how.**
   - GDPval's "under-contextualized" variant removed "where to locate specific data within reference
     files, how to approach the problem", and models "struggled" `[V]`; numbers are not given in the
     text.
   - Capable models miss requirements "embedded in the original task or hidden across source files"
     (AA-Briefcase `[V]`).
   - Insufficient inspection is the top SpreadsheetBench 2 failure `[V]`.
   - "Understanding & Approach" accounts for about 75% of failures on Agents' Last Exam
     (Claude Code + Opus 4.7) `[V]`.
   - KramaBench: 24% of failures assume a clarification will come `[V]`.
   - The lever is real *when the method has to be discovered from the artifacts*: formulas (T3, T4),
     format (T2), or volume (T6). Small folders whose rules are held as data were solved
     internally.
3. **Global constraints.**
   - Coding with a solver closes search (93.9% against 10%).
   - What survives is formalization and the objective: DeepPlanning attributes about 40% of Opus 4.5
     failures to global optimization (tool APIs only); COMPASS optimality reaches only 66% with code.
   - Grader: validators plus a grade-time optimum plus known-correct probes (D3).
4. **Multi-hop state propagation.**
   - Spreadsheet agents "struggle to maintain cross-cell consistency" (SpreadsheetBench 2 `[V]`).
   - Finch composite workflows fall from 44.3% (at most 2 tasks) to 23.5% (more than 2) for GPT-5.1
     Pro `[V]`.
   - EmailBench: 37.7% single-domain against 14.3% four-domain `[V]`.
   - State drift is 44.4% of oracle-retrieval failures (StateMemBench `[V]`).
   - Self-conditioning on one's own errors (ICLR 2026 `[A]`).
   - New shape: T9, propagation through an aggregate.
5. **Counter-prior content.**
   - Context still loses to priors at the margin, most when the conflicting convention is *implicit*:
     SpreadsheetBench 2 Case 4 (textbook over workbook); KramaBench obscured inputs, 62.81% → 12.77%.
   - When it is *stated*, the loss is only 3.6–7.4 points (Harness-IF `[A]`), consistent with the
     internal finding that published rules are followed.
   - Use counter-prior content in formulas or exemplars (T4), never in a prose rule alone.
6. **Dense tasks.** The 90%-per-criterion, 5–20%-per-task profile comes from:
   - 20–190 criteria per task (LAB: more than 75,000 criteria over more than 1,200 tasks `[A]`);
   - all-pass scoring (APEX, with only about 4 criteria per task, still reaches only 24.0% pass@1
     because its criteria are hard);
   - must-pass subsets (Tax Agent Bench: about 40% must-pass `[V]`).

   Which criteria fail most:
   - precedence and authority analysis (Tax Agent Bench: "Forms & Filings and Controversy &
     Precedence Analysis are the hardest categories, with no model above 74%"; "Numbers &
     Calculations is the easiest category for nearly every model");
   - imprecise numbers and premature rounding (LAB/Applied Compute);
   - omissions (Workspace-Bench, CHI-Bench).

   See D1 for what this implies at the internal error rate.
7. **Other 2025–2026 evidence and family skews.**
   - Agents' Last Exam `[V]{Claude Code with Fable 5; Codex with GPT-5.5}`: near-term tier 34.3% and
     38.1%; full-spectrum 20.9% and 22.7%; last-exam tier 0.0% and 0.0%. Deterministic verification;
     "domain knowledge rather than execution capability" is the bottleneck.
   - EnterpriseClawBench `[V]`: the best result on the audited Lite set is 0.663 (Codex + GPT-5.5).
     Claude models "rely on active environment probing, script execution, and multi-step repair".
     Sonnet 4.6 scores 0.62–0.64 in Claude Code against 0.458 in Hermes.
   - AA on GPT-6 Astra `[V]`: about −45 Elo against GPT-5.6 Sol on GDPval-AA v2, attributed to fewer
     turns; Terminal-Bench v4.0 59% against Fable 5.1's 52%.
   - Vals Tax Agent Bench `[V]`: Fable 5.1 77.64%.
   - METR `[V]`: models do worse on messier tasks after controlling for length, with no plateau
     specific to messy tasks.

---

## 5. Measured dead or weak against tool-using agents (new evidence)

| Idea | Verdict | Evidence |
|---|---|---|
| Difficulty from global search or optimization, once the problem is formalized | Dead with code | LLM with formal verification on TravelPlanner 93.9% vs 10% `[A]`; COMPASS optimality 57% → 66% with code `[V,q]`; the fixture is on disk, so brute force is available |
| Pure computation | Dead | Tax Agent Bench: "Numbers & Calculations is the easiest category for nearly every model (top score 88.88%)" `[V]`; Agora: the bottleneck is "not computation" `[V]` |
| Tool-call mechanics as difficulty | Dead | COMPASS: frontier tool-error rate under 1% `[V]`; EmailBench: 99.7% valid API calls against 33.5% task success `[V]` |
| Hallucination or fabrication as the failure to trigger | Weak | Agora: frontier hallucination under 12% `[V]`; CHI-Bench 0.8% `[V]` |
| JSON duplicate keys | Unfair | RFC 8259: "the behavior of software that receives such an object is unpredictable" `[V]`. There is no single defensible answer |
| Hidden rows or sheets, stale cached values, display-rounded number formats in xlsx | Weak, or unfair | The human view hides them too, or the operative value is ambiguous. Once a document pins the meaning, agents switch to openpyxl (internal: stated rules are followed). `[X]` confirms pandas cannot see them, but that is not enough |
| Strike-through or comments *in xlsx* with a legend | Weak | The legend names the property, so agents switch tools; the PDF version (T2) has no text-level property to switch to |
| CSV quoted newlines; day-first dates with any day above 12 | Dead | `[X]`: csv and pandas parse quoted newlines correctly; pandas 2.x *raises* on mixed day-first dates, which is loud. Only `format="mixed"` is silently inconsistent (weak) |
| Unicode look-alikes, NBSP, NFC vs NFD in names | Weak and risky | Merging (same vendor?) against keeping apart (fraud?) is ambiguous without a rule, and a rule announces it. `[X]`: NFKC plus strip merges NBSP and space but not Cyrillic А |
| YAML 1.1 coercion (NO → False) | Weak | Fair and silent (`[X]`), but YAML is rare in business folders, and an agent reading it as text is unaffected |
| Transcription pressure (many exact values typed by hand) | Weak | The 0% perfect transcription at 300 values comes from open-weight models `[V]`; Astra writes from code in 92% of steps (internal) |
| A corrupted derived column in a system export whose raw inputs are present | Weak | ToolMaze's over-trust (`[V]`) occurs when recomputation is impossible, which here would be unfair; with raw inputs present, agents recompute (internal) |
| "Requirements hidden across files" in a small folder | Dead internally | Playbook §6 rules held as data measured 1.00/1.00. AA-Briefcase's bite needs thousands of files (T6) |
| Large constraint sets restated in other words | Weak alone | SCHEDBench and "When Words Change the Model" `[A]`: rewording hurts formalization, but in free-response settings without a grader-visible fixture |

---

## 6. Executed verification log

All checks ran in `mktemp -d` directories that were removed afterwards. No repository file was
touched.
- E1–E6 and E11 used `/usr/local/bin/python3` (3.12.1, pandas 2.2.3, openpyxl 3.1.5).
- E7–E10 and E12 used `uv run --no-project --with <pkg>`, which fetched public packages from PyPI by
  name only: python-docx 1.2.0, plus icalendar, recurring-ical-events, python-dateutil, reportlab,
  pypdf, pdfplumber and PyYAML at their latest versions (not recorded).

**E1. Rounding.**

| value | `round(x,2)` | `Decimal(float)` half-up | `Decimal(str)` half-up | `pd.Series.round(2)` | `f"{x:.2f}"` |
|---|---|---|---|---|---|
| 2.625 | 2.62 | 2.63 | 2.63 | 2.62 | 2.62 |
| 2.675 | 2.67 | 2.67 | 2.68 | 2.68 | 2.67 |
| 1.005 | 1.0 | 1.00 | 1.01 | 1.0 | 1.00 |
| 0.125 | 0.12 | 0.13 | 0.13 | 0.12 | 0.12 |
| 1.115 | 1.11 | 1.11 | 1.12 | 1.12 | 1.11 |

**E2. Float products at ties.**
- `3*0.145 = 0.43499999999999994`: `Decimal(str(x))` half-up gives 0.43. The exact answer is 0.44.
- `7*1.245 = 8.715` in float: `round` gives 8.71 and `Decimal(float)` gives 8.71; `Decimal(str(x))`
  gives 8.72 (exact 8.72).
- `5*0.535 = 2.6750000000000003`: every path gives 2.68 by luck. This is why tie values must be
  searched for, not guessed.

**E3. Clock change.** A shift from 22:00 on 25 Oct 2025 to 06:00 on 26 Oct 2025, Europe/London:

| method | result |
|---|---|
| naive | 8:00:00 |
| same-`ZoneInfo` aware subtraction | 8:00:00 |
| via UTC | 9:00:00 |
| pandas `tz_localize` diff | 9h |

Mixed-offset strings parse to `object` dtype with a FutureWarning.

**E4. pandas coercion.**
- `00123,1.234,50,...`: the id column becomes float64 (123.0; "1E5" became 100000.0).
- `"NA"` becomes NaN: `groupby` gives {'APAC': 50, 'EMEA': 100} against a total of 400.
  `keep_default_na=False` restores NA: 250.
- A chart of accounts with 0123 and 00123 becomes the dict {123: 'Prepaid rent'}.
- German "1.234", "12.500", "980" become [1.234, 12.5, 980.0].

**E5. Dates.**
- `to_datetime("03/04/2025")` gives 2025-03-04 (month first).
- A series containing "13/04/2025" raises ValueError.
- `format="mixed"` gives [2025-03-04, 2025-04-13]: two conventions in one column.
- dateutil reads "01/05/68" as 2068 and "69" as 2069; `strptime("%y")` reads 68 as 2068 and 69 as
  1969.
- Serial 45000 with origin 1899-12-30 gives 2023-03-15; without an origin it becomes a Unix
  nanosecond timestamp.

**E6. xlsx.**
- `read_excel` default returns only the first sheet.
- A SUM formula with a stale cached value of 500 (its live value is 600.4) is returned as 500 by both
  pandas and `data_only=True`.
- A file written by openpyxl gives `data_only` → None.
- A hidden row is included by pandas.
- Strike-through and a comment are visible only through openpyxl.
- A value of 300.4 with format `#,##0` displays as 300.
- A hidden sheet is listed by `sheet_name=None` with no flag.

**E7. docx.** Built by hand: a `w:del` "30" plus `w:ins` "60", a footnote, and a comment.
- python-docx `paragraph.text`: `'Payment is due within  days of invoice.'`
- The footnote and the comment are absent.
- All `w:t` elements: "...within 60 days..." (the accept view).
- `w:t` plus `w:delText`: "3060".

**E8. PDF table.** An empty Net cell next to a wrapped Status cell.
- pypdf puts "4.2" on its own line after "Disputed - see clause".
- pdfplumber `extract_text`: `INV-105 Storage 4.2`.
- `extract_tables()`: `[]`.

**E9. PDF strike-through.** Drawn with `canvas.line` over "ten" and "three".
- pdfplumber `extract_text`: `... shall give ten three five business days' notice.`
- `page.lines`: 2.

**E10. ICS.** A weekly series of 6 (COUNT=6) from 10 Mar 2025 09:00 Europe/London, with a folded
EXDATE for 17 and 24 Mar and a RECURRENCE-ID moving 31 Mar to 1 Apr 14:00.
- A naive line read gives `EXDATE;TZID=Europe/London:20250317T090000,20250324T09000` (truncated).
- `recurring_ical_events` gives 4 occurrences: 10 Mar (+00:00), 1 Apr moved (+01:00), 7 Apr and
  14 Apr (+01:00).
- `dateutil.rrule` alone gives 6.

**E11. Other parsers.**
- `json.loads` with a duplicate "limit" key: the last value wins.
- CSV with a quoted embedded newline: 2 rows via `csv`, 3 via naive splitting.
- NFC and NFD forms are unequal.
- `groupby` keeps "Acme Ltd", "Acme\xa0Ltd", "Acme Ltd " and "Аcme Ltd" (Cyrillic) apart. NFKC plus
  strip merges the first three but not the Cyrillic one.

**E12. PyYAML `safe_load`.** `[GB, NO, SE, DK]` becomes `['GB', False, 'SE', 'DK']`; `off` becomes
False; `1.10` becomes 1.1; `0123` becomes 83.

These scripts can serve directly as the "executed counterexample per misreading" that the
`quality.difficulty_case` self-audit requires: each obvious-tool path is one counterexample.

---

## 7. Sources

| # | Source | Date | URL | Tag |
|---|---|---|---|---|
| 1 | SpreadsheetBench 2: Evaluating Agents on End-to-End Business Spreadsheet Workflows | 2026 (v1) | https://arxiv.org/abs/2606.29955 | V,q |
| 2 | SpreadsheetBench V2 leaderboard (Fable 5 34.7% from launch post; GPT-5.6 Sol 32.4%) | upd. 2026-08-26 | https://benchmarklist.com/benchmarks/spreadsheetbench_v2/ | S |
| 3 | Finch / FinWorkBench: finance and accounting spreadsheet workflows | 2025-12-15, rev. 2026-04-15 | https://arxiv.org/abs/2512.13168 | V |
| 4 | BlueFin: Benchmarking LLM Agents on Financial Spreadsheets | 2026-05 | https://arxiv.org/abs/2605.30907 | V |
| 5 | FLARE: LLMs for Spreadsheets (EuSpRIG 2025) | 2025-06-19 | https://arxiv.org/abs/2506.17330 | A |
| 6 | Beyond Rows to Reasoning (BRTR), agentic spreadsheet retrieval | 2026-03-06 | https://arxiv.org/abs/2603.06503 | V |
| 7 | KramaBench: data-to-insight pipelines over data lakes | 2025-06, v3 | https://arxiv.org/abs/2506.06541 | V |
| 8 | AvalancheBench: enterprise data agents via latent world recovery | 2026-05-22 | https://arxiv.org/abs/2605.24183 | A |
| 9 | ToolMaze: dynamic replanning and anomaly recovery ("When Tools Fail") | 2026-06-04 | https://arxiv.org/abs/2606.05806 | V |
| 10 | DeepPlanning: long-horizon agentic planning with verifiable constraints (ACL 2026) | 2026-01-26 | https://arxiv.org/abs/2601.18137 ; https://aclanthology.org/2026.acl-long.335/ | V |
| 11 | COMPASS: constrained optimization in LLM agents | 2025-10 (v2) | https://arxiv.org/abs/2510.07043 | V,q |
| 12 | SCHEDBench: constraint faithfulness in NL scheduling (EMNLP Findings 2026) | 2026-08-02 | https://arxiv.org/abs/2608.00991 | A |
| 13 | LLMs Can Solve Real-World Planning Rigorously with Formal Verification Tools (NAACL 2025) | 2024-04, rev. 2025-01 | https://arxiv.org/abs/2404.11891 | A |
| 14 | CP-Bench / DCP-Bench-Open: LLMs for constraint modelling | 2025-06 (ECAI 2025) | https://arxiv.org/abs/2506.06052 | A |
| 15 | When Words Change the Model: sensitivity of LLMs for CP modelling | 2025-11-18 | https://arxiv.org/abs/2511.14334 | A |
| 16 | The Illusion of Diminishing Returns: long-horizon execution (ICLR 2026) | 2025-09-11, rev. 2026-03 | https://arxiv.org/abs/2509.09677 | A |
| 17 | Can Agent Memory Systems Track Evolving State? (StateMemBench) | 2026-08 | https://arxiv.org/abs/2608.19652 | V |
| 18 | Inverse Scaling in Test-Time Compute | 2025-07-19, rev. 2025-12 | https://arxiv.org/abs/2507.14417 | V |
| 19 | Can LLMs Reconcile Knowledge Conflicts in Counterfactual Reasoning? | 2025-06, rev. 2026-02 | https://arxiv.org/abs/2506.15732 | A |
| 20 | Task Matters: knowledge requirements shape responses to context-memory conflict | 2025-06, rev. 2026-04 | https://arxiv.org/abs/2506.06485 | A |
| 21 | Thinking Fast, Thinking Wrong: intuitiveness and counterfactual policy reasoning | 2026-04-12 | https://arxiv.org/abs/2604.10511 | A |
| 22 | Harness-IF: instruction following across instruction surfaces in coding agents | 2026-08-12 | https://arxiv.org/abs/2608.11727 | A |
| 23 | Reasoning or Reciting? Counterfactual tasks (NAACL 2024) | 2023-07, 2024 | https://arxiv.org/abs/2307.02477 | A |
| 24 | APEX-Agents | 2026-01-20 | https://arxiv.org/abs/2601.14242 | V |
| 25 | Harvey, Legal Agent Benchmark initial results | 2026-05-26 | https://www.harvey.ai/blog/legal-agent-benchmark-initial-results | V |
| 26 | Harvey, Introducing the Legal Agent Benchmark | 2026-05 | https://www.harvey.ai/blog/introducing-harveys-legal-agent-benchmark | A |
| 27 | Applied Compute, Training a state-of-the-art legal agent with Harvey | 2026-06-22 | https://www.appliedcompute.com/case-studies/harvey | V |
| 28 | Artificial Analysis, Harvey LAB-AA | 2026-07-07 | https://artificialanalysis.ai/articles/harvey-lab-aa | V |
| 29 | Artificial Analysis, Benchmarking GPT-6 Astra | 2026-09-09 | https://artificialanalysis.ai/articles/benchmarking-gpt-6-astra | V |
| 30 | Artificial Analysis, AA-Briefcase | 2026-06 | https://artificialanalysis.ai/articles/aa-briefcase | V |
| 31 | GDPval (incl. A.2.7 "Under-contextualized GDPval") | 2025-10-05 | https://arxiv.org/abs/2510.04374 | V |
| 32 | TheAgentCompany (NeurIPS 2025 D&B) | 2024-12, upd. | https://arxiv.org/abs/2412.14161 | V |
| 33 | Agora: archive-grounded benchmark for agentic workplace document reasoning | 2026-06 | https://arxiv.org/abs/2606.24526 | V |
| 34 | Workspace-Bench 1.0 | 2026-05 | https://arxiv.org/abs/2605.03596 | V |
| 35 | EnterpriseClawBench: agents from real workplace sessions | 2026-06 | https://arxiv.org/abs/2606.23654 | V |
| 36 | Agents' Last Exam | 2026-06-03, rev. 2026-06-11 | https://arxiv.org/abs/2606.05405 | V |
| 37 | CHI-Bench: policy-rich healthcare workflows | 2026-05-15, rev. 2026-09-30 | https://arxiv.org/abs/2605.16679 | V |
| 38 | EmailBench: LLM agents on enterprise email and productivity | 2026-09 | https://arxiv.org/abs/2609.31906 | V |
| 39 | When Upstream Messages Override Correct Answers (multi-agent) | 2026-09-29 | https://arxiv.org/abs/2609.36855 | A |
| 40 | Audit Without Verification: accountability layers relay rather than check | 2026-09-07 | https://arxiv.org/abs/2609.07680 | A |
| 41 | Judging Is Not Enumerating: silent omissions in LLM-authored acceptable sets | 2026-08 | https://arxiv.org/abs/2608.01000 | V |
| 42 | Vals AI, Tax Agent Bench | upd. 2026-09-29 | https://www.vals.ai/benchmarks/tax_agent_bench | V |
| 43 | Vals AI, benchmark index (Excel Modeling, Tax Agent, Finance Agent v2 rankings) | upd. 2026-09-29 | https://www.vals.ai/benchmarks | V |
| 44 | Openbenchmarks, Document Processing Benchmark: Parsers on Redlined Contracts | upd. 2026-09-27 | https://openbenchmarks.com/document-processing | V |
| 45 | OfficeQA Pro (parse-quality results) | 2026-03 | https://arxiv.org/abs/2603.08655 | V |
| 46 | Databricks, Why your agents can't read enterprise documents | 2026 | https://www.databricks.com/blog/why-frontier-agents-cant-read-documents-and-how-were-fixing-it | V |
| 47 | Anthropic skills, xlsx SKILL.md | 2026 | https://github.com/anthropics/skills/blob/main/skills/xlsx/SKILL.md | V |
| 48 | Anthropic skills, docx SKILL.md | 2026 | https://github.com/anthropics/skills/blob/main/skills/docx/SKILL.md | V |
| 49 | Claude Code tools reference (Read tool: PDFs, images) | 2026 | https://code.claude.com/docs/en/tools-reference | V |
| 50 | Python docs, `round()` | current | https://docs.python.org/3/library/functions.html#round | V |
| 51 | Python docs, `datetime` aware subtraction | current | https://docs.python.org/3/library/datetime.html | V |
| 52 | pandas `read_csv` reference (na_values, dtype, decimal, date_format "mixed") | current | https://pandas.pydata.org/docs/reference/api/pandas.read_csv.html | V |
| 53 | pandoc manual, `--track-changes` | current | https://pandoc.org/MANUAL.html | V |
| 54 | RFC 5545 iCalendar | 2009 | https://www.rfc-editor.org/rfc/rfc5545 | V |
| 55 | RFC 8259 JSON | 2017 | https://www.rfc-editor.org/rfc/rfc8259 | V |
| 56 | τ²-Bench: dual-control conversational agents | 2025-06-09 | https://arxiv.org/abs/2506.07982 | A |
| 57 | WorkArena++ | 2024-07, rev. 2025-02 | https://arxiv.org/abs/2407.05291 | A |
| 58 | METR, Measuring AI Ability to Complete Long Tasks (messiness analysis) | 2025-03 | https://arxiv.org/abs/2503.14499 | V (partial) |
| 59 | PRBench (Scale AI) | 2025-11 | https://arxiv.org/abs/2511.11562 | A |
| 60 | ProfBench (NVIDIA, ICLR 2026) | 2025-10 | https://arxiv.org/abs/2510.18941 | A |
| 61 | Verbatim Data Transcription Failures in LLM Code Generation | 2026-01-07 | https://arxiv.org/abs/2601.03640 | V |
| 62 | NATURAL PLAN | 2024-06 | https://arxiv.org/abs/2406.04520 | A |
| 63 | ARE / Gaia2 (Meta) | 2025-09-21 | https://arxiv.org/abs/2509.17158 | A |
| 64 | OmegaUse-OfficeVal (no frontier Claude/GPT evaluated) | 2026-07 | https://arxiv.org/abs/2607.27155 | V |
| 65 | Can LLM Coding Agents Reason About Time Series? | 2026-06-15 | https://arxiv.org/abs/2606.16545 | A |
| 66 | Remote Labor Index (July 2026 update via secondary reports) | 2025-10 / 2026-07 | https://labs.scale.com/papers/rli | S |

Catalogued sources are not repeated (OfficeQA Pro and RuleArena are cited above only for new figures).
Local inputs read: `frontier-agent-failure-modes.md`, `trajectory-nearmiss-report.md`,
`EXTREME-HARDENING-PLAYBOOK.md`, `HARDENING-RESULTS-2026-09-29.md`.

---

## 8. What this document does not establish

- No source measures Fable 5.1 in Claude Code or GPT-6 Astra in Codex on fair, deterministic
  document tasks of this shape. Every bite estimate is a hypothesis.
- The tool-betrayal mechanisms (T1, T2, T5, T7, T10) are verified only *as tool behaviour*. Whether
  these agents use those default paths is unmeasured. Two cheap pre-checks before building:
  - (a) Inventory the task image: is `icalendar`, `recurring_ical_events`, `python-docx`,
    `pdfplumber`, `pandoc` or `pdftoppm` present? Claude Code's page-range PDF reads need `pdftoppm`.
  - (b) Grep existing trajectories for `round(`, `Decimal(`, `read_excel(`, `python-docx`/`docx.`,
    `pdfplumber`, `extract_text`, `tz_localize` and `zoneinfo`, to see which paths each family
    actually takes.
- Several key external numbers come from model-summarised full-text views. Only those marked `q`
  were re-queried verbatim.
- Family skews come from different snapshots and harnesses (Opus 4.6, GPT-5.4 and 5.5, Fable 5 and
  5.1, GPT-6 Astra as a parser). The exception-chain paper in the catalogue shows such cells can
  close within a month under the same model alias.
- T6 (corpus scale) changes the measurement regime and authoring cost. It has not been costed here.
