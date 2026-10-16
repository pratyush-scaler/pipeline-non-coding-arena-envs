# B9 pilot forensics: four B8 tasks, 3 x 2 pilots (2026-10-16)

Tasks (all 1.0.0, trees under `envs-b6/`): `a_f1_labour-code-entitlements`, `a_f1_repair-returns-sla-log`,
`a_f1_working-capital-answer-key`, `a_f1_maize-input-schedule`. Harness: Fable 5.1 (`claude-fable-5-1`) in Claude Code
and GPT-6 Astra (`openai/gpt-6-astra`) in Codex, high effort, no turn or time limits, 3 runs per model per task
(campaigns `pipeline-artifacts/b4/<task>-1.0.0-pilot-{fable,astra}/`). n = 3 per premise per model: every rate here is
pilot triage (B8 §0), not a calibration figure.

## Sources and method

- **Per-check results**: `steps/01-task/verifier/reward-details.json`. The `verifier/test-stdout.txt` files are empty
  (0 bytes) in all 24 runs, so they could not be used.
- **Model reasoning**: Fable's thinking in `agent/claude-code.txt` is redacted (empty `thinking` text plus a
  signature). Only the short thinking summaries in `trajectory.json` (`reasoning_content`) are readable. The Codex logs
  carry no reasoning items, only agent messages and command executions. Every quote below therefore comes from a
  summary, an agent message, a script line or comment, or the final report.
- **Anchors seen (a)**: a script substring-matched every anchor and resolving quote in each premise of `traps.json`
  (54 strings across the 16 premises, whitespace-normalised) against the run's own tool output. For Fable that is the
  observations in `trajectory.json`; for Astra it is `aggregated_output` in `codex.txt`. **Result: 24/24 runs, every
  string present.** Both models print the whole folder in 1-3 commands before computing. Column (a) of the table is
  "yes" everywhere and is not repeated per cell.
- Modes: **silent** (the premise is never mentioned), **voiced-and-resolved** (the model names the conflict or
  convention and adopts a reading; the reading can be wrong), **voiced-and-rejected** (the model names the evidence and
  keeps the printed record or its own default against it).

## Headline numbers

| task | Fable pass@1 | Astra pass@1 | substantive premise misses (F / A) |
|---|---|---|---|
| labour-code-entitlements | 1.00 | 1.00 | none |
| repair-returns-sla-log | 1.00 | 1.00 | none |
| working-capital-answer-key | 1.00 | 0.33 | P1: 0/3 / 2/3 |
| maize-input-schedule | 0.00 | 0.33 | P2: 3/3 / 2/3; P3: 3/3 / 0/3; P4: 0/3 / 0/3 (graded 1/3 / 1/3, cascade) |

- 96 premise-runs (16 premises x 6 runs). Substantively solved: 86. Real misses: 10. Graded misses: 12.
- **Maize P4 was never misread.** All 6 runs wrote `urea_bags_in_shed` = 24, the true figure. The two graded P4 zeros
  (Fable `6bsoNtr`, Astra `UwJJmMm`) come from P2: `obj_urea_in_shed` requires shed = (own lifts total) - (one lift).
  Both runs wrote the printed lifts 10/24/32 (66 bags), so 66 - 32 = 34, which is not 24. The gate's v5 labels "P4
  stochastic" and "fable: 1 premise in the 20-80% band" come from this cascade. P4 is constant (0/6) in substance.
- All 10 real misses were **voiced**: 7 voiced-and-rejected and 3 voiced-and-resolved wrongly. None was silent.

## 1. Premise table

Quotes are the model's own words, at most 20 words. "assert" means the model executed the convention as a test in
its script.

| task | premise | mode | Fable outcome + mechanism | Astra outcome + mechanism | why solved / why it bit |
|---|---|---|---|---|---|
| labour | P1 leave allowance survives gross misconduct | T9 ATTR, aimed Fable | solved 3/3, voiced-and-resolved: "strips notice pay, severance and bonus for gross misconduct but not the compensatory leave allowance" (3CEinM5) | solved 3/3, voiced-and-resolved: "Moussa retains his unused-leave payout despite the gross-misconduct dismissal" (T9kavYi) | The shield is a closed list ("no notice pay, no severance indemnity and no pro-rata share of the year-end bonus") and Art. 153.4 is explicit. The default ledger lookup gives the truth for free; the trap needs the model to over-extend, and neither model does |
| labour | P2 hourly rate truncated | T2 EXEMPLAR, aimed Astra | solved 3/3, voiced-and-resolved: "Hourly rates are truncated, not rounded. The payroll procedure's own worked example gives 14,134" (3CEinM5); asserted the figure in 2/3 (`assert math.floor(2450000/173.33)==14134`) | solved 3/3, voiced-and-resolved: "truncate hourly rates to whole francs as the payroll procedure's example indicates" (5jwDCN2) | One worked figure, with its input (2,450,000 -> 14,134), sits in the governing PP-04; dividing once settles it. The neutral rule ("in whole francs") gives no default to cite. Possible cue (guess): the field text "as the final account prints it" |
| labour | P3 seniority includes the CDD year | L3 EVENT, aimed Astra | solved 3/3, voiced-and-resolved: "His customs card dates from January 2025 ... Article 171.3 counts that period" (3CEinM5) | solved 3/3, voiced-and-resolved: "Alpha's earlier fixed-term service also counts toward severance eligibility" (5jwDCN2) | Art. 171.3 states the rule. The card list repeats the full name "BANGOURA Alpha" with a first-issue date (2025-01-06) one year before the register's entry (2026-01-06). It is the only mismatch among the four declarants, so a name join finds it |
| labour | P4 crew-chief / forklift rows transposed | T12 TWIN, aimed both | solved 3/3, voiced-and-resolved: "Soumah's resignation letter says he has led the stuffing crew ... Sekou Camara is the forklift driver" (3CEinM5) | solved 3/3, voiced-and-resolved: "Ibrahima leads the crew and Sekou works as a driver" (5jwDCN2) | The anchors carry the register's own first names (letter signed "Ibrahima Soumah"; "Sekou's forklift ticket") plus the role words of the transposed Position column. That makes them direct contradictions keyed by name |
| repair | P1 "10 days" = 10 plant working days | T2 EXEMPLAR, aimed both | solved 3/3, voiced-and-resolved: "The SOP's own tracker example only reconciles if Sundays are skipped" (jfoLM5G); assert 3/3 (`assert add_wd(D("2026-09-05"),10,PLANT)==D("2026-09-17")`) | solved 3/3, voiced-and-resolved: "The SOP's example establishes that the 10-day inventory SLA uses plant working days" (24iSnqK); assert 3/3 | The dated worked example separates the three calendars (calendar 09-15, store 09-19, plant 09-17), so both models write it as an assert. "10 days" is the one SLA row without "working", a visible gap |
| repair | P2 Narmada expects 10 locks, not 5 | T3 SCALE, aimed Fable | solved 3/3, voiced-and-resolved: "The ticket's quantity of 5 counts tanker sets" (kujLuN8) | solved 3/3, voiced-and-resolved: "Narmada's five sets mean 10 expected locks" (ynVLVqG); code `expected['SR-0914-03'] *= 2` (jMQgfgx) | The unit is printed on the record itself (item "Tanker lid lock set"), and the request mail states the arithmetic ("five of our tankers, the manhole lid and the outlet valve on each"). The field asks "how many locks" |
| repair | P3 bench-sheet dates of two Sahyadri locks transposed | T12 TWIN, aimed Astra | solved 3/3, voiced-and-resolved: "KS-28833 was in the drying cabinet until Friday 18 Sep per the hand-over notes" (jfoLM5G) | solved 3/3, voiced-and-resolved: "the fogged-display lock was inspected late, while the stuck-shackle lock was inspected on time" (jMQgfgx) | The anchors' weekday names ("until Friday morning"; "yesterday, Wednesday") equal the twin rows' printed `Inspection day` values. Fault-to-Lock-ID is one join through `customer_details` |
| repair | P4 gate walk-in KS-30977 is Konkan's | T1 ATTR, aimed both | solved 3/3, voiced-and-resolved: "Konkan's driver left their third lock at the gate on Monday 21 Sep, and Narmada says nothing left them" (jfoLM5G) | solved 3/3, voiced-and-resolved: "the mail identifies the gate-delivered lock as Konkan's third unit" (ynVLVqG) | "the gate on Monday" matches the log's only `Gate walk-in,...,Mon` row, a unique content match. The default also leaves an anomaly: Konkan has 2 of 3, and Narmada shows 5 against a 4-piece carton |
| working-capital | P1 2025 receivables / inventories transposed | T12 TWIN, aimed both | solved 3/3, voiced-and-resolved: "The chairman reports the fullest warehouse in the company's history, yet the statement shows inventories falling" (8L68Lxh) | **missed 2/3, voiced-and-rejected**: "the narrative comments provide no explicit corrections to those balances" (zeUUbss); "despite conflicting narrative claims" (799tPLw). Solved 1/3: "indicate that the 2025 receivables and inventory figures were transposed" (RANnpVm) | **Solved by Fable**: each qualitative remark maps to one line and can be tested against the printed 2024 column (inventories 720k -> 460k against "fullest warehouse"; receivables share of sales 10% / 18% / 10% swapped). **Bit Astra**: the record is the primary statement, the anchors name no line or figure, and the swap keeps every total. Astra's own tie-out asserts (`cash + receivables + inventory == ca`) passed |
| working-capital | P2 fixed assets at cost | T2 EXEMPLAR, aimed Astra | solved 3/3, voiced-and-resolved: "The formula sheet's Company S illustration gives 3.60, which only works with property at cost" (4KjjFfr) | solved 3/3, voiced-and-resolved: "The formula sheet's worked example uses fixed assets at cost" (799tPLw) | The illustration prints both candidate bases (at cost 500,000; net 360,000) next to the 3.60, so the back-solve is one division. The instruction sends the solver to the sheet ("Use the course formula sheet's definitions") |
| working-capital | P3 returns on reported net income | T9 ATTR, aimed Fable | solved 3/3, voiced-and-resolved: "Return on assets and equity use reported net income, as the formula sheet specifies" (4KjjFfr) | solved 3/3, voiced-and-resolved: "it adjusts only net profit margin for the one-off gain" (799tPLw) | The exclusion opens with its scope ("For the net profit margin, ..."), so a literal reading is the truth. The bank letter ("on the year's net income as reported") confirms it |
| working-capital | P4 2025 notes are supplier bills, not bank credit | T3 ACTUAL, aimed Fable | solved 3/3, voiced-and-resolved: "the 2025 notes are the Izmir supplier's accepted bills, which are trade credit" (4KjjFfr) | solved 3/3, voiced-and-resolved: "the 2025 short-term notes are supplier bills, so they do not reduce net liquidity" (zeUUbss) | The definition names the class ("short-term bank credit ... whatever form the borrowing takes"), so both models classify the notes line. The letters then state its nature outright ("stood undrawn since you repaid it in March 2025"; "paid ... with ninety-day accepted bills") |
| maize | P1 seed rate is per two-packet unit | T3 SCALE, aimed both | solved 3/3, voiced-and-resolved: "The seed price on Kadam's list carries no unit. Last year's bill charged quantity 6 at 2,800 for 12 packets" (6bsoNtr) | solved 3/3, voiced-and-resolved: "The old bill and godown register show that Kadam's seed rate covers 8 kg" (UwJJmMm) | The missing unit is a visible gap that the model fills (B8 §1.3). The godown line cross-references the bill ("from Kadam (cash bill of today)"), and "same packing as last season" points straight back. Possible cue (guess): "graded as your own seed_cost_rupees per kilogram" |
| maize | P2 app "Bags" are running totals (true lifts 10/14/8) | T14 AGGREGATE, aimed Fable | **missed 3/3**. r1 voiced-and-rejected: kept 10/24/32, "The 7 October app entry shows 24 bags but only 14 reached the shed". r2 and r3 voiced-and-resolved wrongly, 10/14/32: "I took 24 as a copying slip"; "treated the app figure as a POS entry error" | **missed 2/3**. 3svfPJi voiced-and-resolved wrongly, 10/14/32: "support 14 bags bought on 7 October, despite the app showing 24". UwJJmMm voiced-and-rejected, 10/24/32 (plain `csv.DictReader`). Solved 1/3: "the app's urea figures are running totals: the purchases were 10, 14 and 8 bags" (gDvYssv) | **Bit**: all 6 runs saw the anomaly, but it is confined to one row. The cash book (3,731 = 14 bags) and diary (2 x 7) contradict only 07-10, and the cheapest explanation is a slip in that row. The row carrying most of the graded error (09-10, printed 32, true 8) has no count witness, so only the column-level reading recovers it. 5/6 kept 32 |
| maize | P3 whole bags = nearest bag below (from two worked figures) | T7 EXEMPLAR, aimed Fable | **missed 3/3**, voiced-and-rejected: "Vikram's diary says 24 bags for the knee-high dressing, but 1,098 kg at 45 kg a bag needs 25 bags" (ZNGFWZZ). Same remark in 3/3; the card's own "420 kg: 8 bags" is never cited; "rounded up ... as the card's buying rule requires" | solved 3/3, voiced-and-resolved: "The dose card and Vikram's notes use nearest-whole-bag rounding" (UwJJmMm); `ROUND_HALF_UP` or `round()` | **Bit Fable**: "whole bags; nobody opens a bag at the dealer's" reads as the rationale for rounding up (a rule shield) in a domain where buyers round up. Fable checked the second party's figure against its own convention and declared it a slip. **Astra**: solved, but half-up agrees with the truth on every graded figure (fractions .2-.4), so its solve is overdetermined |
| maize | P4 the 9 Oct purchase was Mama's | T1 TWIN, aimed both | solved in substance 3/3 (shed 24 in every run), voiced-and-resolved: "The 9 October load was Datta Mama's, bought on Vikram's thumb and unloaded at Mama's yard" (6bsoNtr). Graded 2/3: 6bsoNtr failed through P2 | solved in substance 3/3 (shed 24). 3svfPJi voiced-and-resolved: "the 32 delivered to Datta Mama are recorded against Vikram's ID". UwJJmMm silent on Mama: `shed_bags = 10 + 2 * 7`, asserted equal to the cash-book bag count. Graded 2/3: UwJJmMm failed through P2 | **Easy two ways**: (1) the diary line "09.10 (Fri) ... unloaded straight at Mama's yard" maps to the only 2026-10-09 row. (2) Bypass: P2's cash-book anchor counts the shed directly (2,665 + 3,731 = 24 bags at 266.50), so the ownership question never has to be asked. **Graded zeros are a cascade**: the check grades the shed against the solver's own lifts, and both failing runs wrote the true shed beside the printed lifts |

Per-run maize values (from `artifacts/.../basal_trip_order.json`; the oracle run gives 10/14/8, shed 24):

| run | lifts (03 / 07 / 09 Oct) | shed | basal bags MOP / Zn / S | P2 | P3 | P4 graded |
|---|---|---|---|---|---|---|
| Fable 6bsoNtr | 10 / 24 / 32 | 24 | 24 / 15 / 17 | 0 | 0 | 0 (cascade) |
| Fable 7KHE4Aq | 10 / 14 / 32 | 24 | 24 / 15 / 17 | 0 | 0 | 1 |
| Fable ZNGFWZZ | 10 / 14 / 32 | 24 | 24 / 15 / 17 | 0 | 0 | 1 |
| Astra 3svfPJi | 10 / 14 / 32 | 24 | 23 / 14 / 16 | 0 | 1 | 1 |
| Astra UwJJmMm | 10 / 24 / 32 | 24 | 23 / 14 / 16 | 0 | 1 | 0 (cascade) |
| Astra gDvYssv | 10 / 14 / 8 | 24 | 23 / 14 / 16 | 1 | 1 | 1 |

## 2. What bit

### Maize P2 (T14): one witnessed row gets a row repair, not a new reading of the column

**Build features that bit**

- The default answer does leave an anomaly, and all 6 runs saw it. The cash book's 3,731.00 at 266.50 is 14 bags
  and the diary has "two rounds ... seven bags a round", both against the printed 24 for 07-10.
- The anomaly touches **one row only**. 03-10 is witnessed too, but its printed 10 is right under both readings. The
  09-10 row carries the largest graded error (32 against 8) and has no count witness at all: the cash book has no
  9 October payment (Mama settles later) and the diary gives no count.
- The cheapest explanation that clears the visible anomaly is therefore a slip in that one row. Runs used three
  variants: "I took 24 as a copying slip" (Fable r2), "a POS entry error" (Fable r3, Astra 3svfPJi in effect), and
  "extra 10 bags on Vikram's ID" kept as recorded (Fable r1). None of these explanations touches 09-10.
- The record looks complete and per-purchase. The column is titled `Bags`, the rows rise as purchases would, and the
  instruction defines `bags` as "the number of bags bought in that purchase", which is the real-world quantity.
  Fable r1 kept the app's figures. My inference, which Fable does not state, is that this is because the field reads
  "each purchase of urea entered on Vikram's farmer ID in the Krushi Khata app".
- The only bridge to the true reading is arithmetic nobody was prompted to do: printed 24 = 10 + witnessed 14. One
  run (Astra gDvYssv) did it: `{'bags': 24 - 10}`, `{'bags': 32 - 24}`.

**Reusable rules**

- When the default leaves an anomaly in a single row, models repair that row and keep the rest (5/6 here). To make a
  column-level premise bite, witness exactly one row's true value. Put the graded error on rows that no anchor counts,
  so that only the column-level reading recovers them.
- Adding witnesses to the row that is already witnessed should not move this premise: 4/6 runs already wrote or
  stated 14 for 07-10. This is a guess from the same data, untested. It means the DIAL's "too hard" notch (a Kadam
  line about the second lift's two trolley rounds) targets the wrong row. A notch more likely to move it, also a
  guess: a second witnessed row whose printed value equals the running sum, so that the row-slip story needs two
  coincidences.
- For the §14 audit, my reading of the fixture is that a third route also entails 8 for 09-10. The diary records one
  trip that day, and a round carries about 7-10 bags (03.10 "one round" = 10; 07.10 "seven bags a round"), so 32
  bags is implausible for a single trip. No model used this route.

### Maize P3 (T7): Fable corrects the exemplar instead of its convention

**Build features that bit Fable (3/3)**

- The governing sentence, "Inputs are bought, carried and spread in whole bags; nobody opens a bag at the dealer's",
  reads as the rationale for rounding up. Fable cites it as if it were the rule: "rounded up to whole 50 kg bags ...
  as the card's buying rule requires" (ZNGFWZZ). This is the rule-shield pattern of B8 §1.4.
- The domain carries a strong prior for the default: when buying inputs, you round up so that you do not run short.
- The second worked figure is a second party's planning line (Vikram: "1,098 kg, so 24 bags go out to the field").
  Fable recomputed it under its own convention and declared Vikram wrong in all three runs ("needs 25 bags").
- The agronomist's own figure ("420 kg: 8 bags", in the same paragraph as the rule) was never mentioned by Fable in
  any run. It was in Fable's tool output 3/3.

**Astra (0/3 missed)** cited the examples every time ("Using the dose card's whole-bag examples"). However, its
half-up rounding agrees with the truth on every graded figure (the fractions are .2-.4), so this premise did not test
Astra.

**Reusable rules**

- An exemplar bites Fable when three conditions hold together:
  - the governing sentence can be read as the rationale for the default convention, without stating it;
  - the domain justifies that default;
  - one discriminating figure sits in a second party's plan line, which Fable can call an arithmetic slip.

  The three single-figure T2 builds whose rule gave no citable default ("in whole francs", "10 days from inspection",
  "net sales / fixed assets") were 0/9 on Fable.
- To aim an exemplar at Astra, choose fractions where the exemplar's convention and half-up disagree (for example,
  floor with fractions of .5 or more). This is a guess, untested here.

### Maize P4 (T1): not a bite. A bypass and a cascade

- **Bypass.** P2's cash-book anchor states P4's answer directly: the two payments buy exactly the 24 bags in the
  shed. Astra UwJJmMm wrote `shed_bags = 10 + 2 * 7` and asserted it equal to `int(2665/266.50) + int(3731/266.50)`.
  It never mentioned Mama and still had the right number.
- **Cascade.** `obj_urea_in_shed` grades the shed against the solver's own lifts (shed = total - one lift). That is
  B8 §7's "own upstream" rule, but a solver who takes the shed from its own physical witness while keeping the printed
  lifts fails P4 as well as P2. Both graded P4 zeros wrote the true shed. Executed additivity did not catch this
  because `ARENA_MISREAD="P2"` derives the shed from the misread lifts (34). The models never did that: 6/6 took the
  shed from the cash book or the diary.
- **Reusable rules**
  - A decisive premise's answer must not be readable off another premise's anchor.
  - When a downstream quantity has its own witness in the files, do not grade it against the solver's upstream list.
    Grade the premise's decision as its own set (here, the dates of the purchases whose bags are in the shed).
  - Add a "downstream computed from its own witness" variant to the additivity census.

### Working-capital P1 for Astra (T12): qualitative anchors against a primary statement whose totals tie

**Build features that bit Astra (2/3)**

- The record is the company's primary statement of financial position.
- The anchors are remarks by the chairman and the credit insurer that name neither line nor any figure.
- The swap keeps every subtotal and total. Astra's own validation asserts passed on the printed figures
  (`assert cash + receivables + inventory == ca`, `assert assets == value('Total liabilities') + equity`, in
  799tPLw), so its script reported a clean, tied answer.
- Astra stated its criterion outright: it overrules a primary record only on an "explicit correction" ("the
  narrative comments provide no explicit corrections to those balances"). This is voiced-and-rejected, not silent.

**Why Fable solved it (3/3)**: each remark maps to one line by meaning and can be tested against the printed 2024
column. Fable ran the test: "yet the statement shows inventories falling"; and the receivables "same share of a year's
sales ... only holds if receivables are 460,000" (8L68Lxh).

**Reusable rules**

- A transposition settled by qualitative remarks, with every total tying, is an Astra-side trap.
- To also beat Fable, no anchor may be testable against a printed comparative or prior-period figure. This is a
  guess, untested.

## 3. What got solved and how (86 solved premise-runs, ranked by frequency)

| rank | solve path | premise-runs | premises | build feature that enabled it | fix |
|---|---|---|---|---|---|
| 1 | **The anchor shares a token with a record cell**, so the reversal becomes a join | 30 | labour P3, labour P4, repair P3, repair P4, maize P4 (5 runs by the dated diary line; Astra UwJJmMm by the cash-book bypass of §2) | First names that appear in the register's name column; a full name repeated in a second table; weekday names equal to a printed day column; "gate ... Monday" equal to the only `Gate walk-in,Mon` row; a diary date equal to the only row of that date | B8 §6.4 already forbids identifier tokens, but these builds leaked through *non-key* columns. Grep every anchor's names, weekdays, dates, routes and fault words against **every** column of the record. Refer by role or event only, and prove a blind reader still reaches the answer |
| 2 | **The worked figure is executed** (assert or printed check) | 21 | labour P2, repair P1, WC P2, maize P3 (Astra) | The figure's inputs are printed beside its result, there are 2-3 candidate conventions, and nothing in the rule supports the default. Fable executed it in 6/9 runs, Astra in 3/9 (repair 3/3) | Do not make a single-figure T2 decisive. "Exactly one discriminating figure" held Astra 0/9. Use the maize P3 shape instead (a citable default sentence, a domain-justified default, a second party's figure) |
| 3 | **The unit is visibly missing, or printed on the record** | 12 | maize P1, repair P2 | A rate list with no unit ("carries no unit"); a ticket item named "lock set"; an SLA row lacking the word "working" | Give the record a plausible unit of its own, and let routine anchors imply the true basis. Never leave the unit blank; never print "set", "pair" or "pack of two" on the record. A printed unit that the default misreads (for example "per pack") is the T3 shape B8 §6.8 says bites Fable; that is untested here (guess) |
| 4 | **The rule's scope is stated**, so a literal reading is the truth | 12 | labour P1, WC P3 | A scope phrase leading the sentence ("For the net profit margin, ..."); a closed list of what gross misconduct forfeits | Treat these T9 shapes as STATED (0/12). Do not spend a decisive slot on them |
| 5 | **A definition names the class and a letter states the fact** | 6 | WC P4 | "short-term bank credit (... whatever form the borrowing takes)" makes both models classify the notes line; "stood undrawn since you repaid it" and "paid ... with ninety-day accepted bills" answer it | The line's nature must follow from routine facts in two files (dates, counterparties, amounts), never from a sentence that says what the line is |
| 6 | **A qualitative remark turned into arithmetic** against a printed comparative | 4 | WC P1 (Fable 3, Astra 1) | Each remark maps to one line by meaning, and the 2024 column turns it into a ratio test | For a Fable-aimed T12, deny the comparative (guess). For Astra, keep it qualitative |
| 7 | **The column semantics inferred** from the arithmetic | 1 | maize P2 (Astra gDvYssv) | printed 24 = 10 + witnessed 14 | Keep this as the only route (it is what makes P2 hard) |

### Claims in B8 that this pilot contradicts (n = 3 per premise per model; flag, do not overwrite)

- **B8 §1.3, "Fable ... will not overrule a record."** Fable reversed the printed record in 15/15 runs of the five
  record-reversal premises whose anchors map to a single row or line (labour P4, repair P3, repair P4, maize P4,
  WC P1). It also reversed maize P2's 07-10 row in 2/3 runs. What Fable did not do here: generalise one row to a whole
  column (maize P2), or accept an exemplar against a rule it could cite (maize P3).
- **B8 §1.4, "Astra is silent in 83% of its misses."** Astra voiced all 4 of its real misses: maize P2 x2 and WC P1 x2.
- **B8 §6.5, "exactly one discriminating figure" for Astra.** Astra went 0/9 across labour P2, repair P1 and WC P2.
- **Library T14 pooled Fable 1/15.** This maize build bit Fable 3/3 and Astra 2/3: the single-witnessed-row shape is
  new evidence for T14.
- **Library T9 pooled Fable 46%.** These two builds were 0/6 on Fable. The cause given in section 3 (the scope is
  stated) is my reading; I did not compare these builds against the melody wording.

## 4. AUTHOR ADDENDUM B9

1. **Assume every file is read.** In 24/24 runs, every anchor and resolving quote of all 16 premises was in the
   model's own tool output (both models print the whole folder in 1-3 commands). Burying a line, file count and
   position buy nothing. Only the interpretation a line demands matters. (all four tasks)
2. **An anchor that shares any token with a record cell is a join, not an inference** (30/30 solved; one maize P4
   run went by the bypass of item 6).
   - labour P4: first names "Ibrahima" and "Sekou" in the register's name column;
   - labour P3: the card list repeats "BANGOURA Alpha";
   - repair P3: "Friday" and "Wednesday" equal the printed day column;
   - repair P4: "gate ... Monday" equals the only `Gate walk-in,Mon` row;
   - maize P4: diary "09.10 (Fri)" equals the only 9 October row.

   Grep each anchor's names, weekdays, dates and route words against every column, not only the key.
3. **A worked figure printed with its inputs is executed, not read** (labour P2, repair P1, WC P2: 0/18 misses).
   Fable ran it as an assert or check in 6/9 runs (repair: `assert add_wd(D("2026-09-05"),10,PLANT)==D("2026-09-17")`)
   and Astra in 3/9. "Exactly one discriminating figure" held Astra on 0/9. Never make a single-figure T2 decisive.
   Guess: the field text "as the final account prints it" (labour P2) also pointed at the convention.
4. **An exemplar bites Fable only against a default it can cite a sentence for.** In maize P3, "whole bags; nobody
   opens a bag" led Fable to round up "as the card's buying rule requires". It called Vikram's 1,098 kg -> 24 bags a
   slip ("needs 25 bags") in 3/3 runs and never cited the card's own "420 kg: 8 bags". T2s with no citable default
   sentence were 0/9 on Fable. Build T7 from three parts: a sentence that reads as the default's rationale without
   stating it, a domain-justified default, and one figure in a second party's plan line.
5. **One witnessed row gets a row repair, not a new reading of the column.** In maize P2, 6/6 runs saw that the cash
   book (14 bags) and diary (2 x 7) contradict the 07-10 "24". 5/6 explained it locally ("I took 24 as a copying
   slip"; "a POS entry error") and kept 09-10 at 32, against a true 8. Witness exactly one row. Put the graded error
   on rows no anchor counts, and prove for the audit that the column reading is the only route. Guess: more witnesses
   on the already-witnessed row will not move it.
6. **No premise's answer may be readable off another premise's anchor.** In maize P4, the cash book that settles P2
   also counts the shed (2,665 + 3,731 = 24 bags), so 6/6 runs wrote the true 24. Astra UwJJmMm never mentions the
   real owner (`shed_bags = 10 + 2 * 7`, asserted equal to the cash-book count). Census each premise as "solve it
   with only the other premises' anchors"; any hit is a bypass.
7. **Do not grade a downstream number against the solver's own upstream when the files witness it directly.** Maize
   P4's two graded zeros (Fable 6bsoNtr, Astra UwJJmMm) both wrote the true shed of 24. The check demanded own lifts
   minus one lift (66 - 32 = 34). Give the premise its own set-valued check (the dates whose bags are in the shed).
   Add "downstream computed from its own witness" to the executed additivity census.
8. **A blank unit is a visible gap, and a unit word on the record is the answer** (12/12 solved). Maize P1: "The seed
   price on Kadam's list carries no unit". Repair P2: item "Tanker lid lock set" ("The ticket's quantity of 5 counts
   tanker sets"). Give the record a plausible unit of its own and carry the true basis in routine anchors. Guess: a
   printed unit the default misreads is the T3 shape that bites Fable (B8 §6.8); it is untested here.
9. **A rule scoped by a leading "For the X," or a closed list is a stated rule: T9 went 0/12.** WC P3 opens "For the
   net profit margin, ..."; labour P1's PP-04 s6 reads "no notice pay, no severance indemnity and no pro-rata share of
   the year-end bonus". Both models quoted the scope back ("only net profit margin excludes the after-tax property
   gain"). Do not make T9 decisive in this shape.
10. **Qualitative anchors with every total tying beat Astra, not Fable.** In WC P1, Astra 2/3 was voiced-and-rejected
    ("the narrative comments provide no explicit corrections to those balances") after its own tie-out asserts
    passed. Fable 3/3 tested each remark on the printed 2024 column ("the statement shows inventories falling"). Aim
    this shape at Astra. Guess: for Fable, no anchor may be testable against a printed prior-period figure.
11. **A definition that names a class makes both models classify every candidate line.** A letter that states the
    line's nature then settles it: WC P4 6/6 ("short-term bank credit ... whatever form the borrowing takes", then
    "stood undrawn since you repaid it in March 2025" and "paid ... with ninety-day accepted bills"). The nature must
    follow from routine facts in two files, never from a sentence saying what the line is.
12. **Expect voiced misses, so trap what a model does after it voices the conflict.** All 10 real misses were voiced
    (7 rejected, 3 resolved wrongly) and none was silent; Astra voiced 4/4, against B8 §1.4's 83% silent. Fable
    reversed records 15/15 where anchors map to one row (labour P4, repair P3, repair P4, maize P4, WC P1), against
    B8 §1.3. Fable failed only by not generalising one row to a column (maize P2) and by overruling an exemplar with a
    rule it could cite (maize P3): aim Fable traps there. n = 3 per premise per model.

## Verified and untested

- **Verified by execution**: the per-check outcomes, the per-run maize deliverable values, the empty `test-stdout.txt`
  files, the 100% anchor-seen result, and the quoted strings (read from each run's trajectory or Codex log).
- **Not verified**:
  - the reasons inside redacted Fable thinking and unlogged Astra reasoning;
  - whether the instruction-text cues marked "guess" had any causal effect;
  - every rule marked "guess";
  - whether any of these miss rates survive a 10 x 2 final.

  No §14 audit or blind reader was run for maize P2 or P3, so both remain unaudited bites (B8 §0: treat an unaudited
  100% miss as possible ambiguity).
