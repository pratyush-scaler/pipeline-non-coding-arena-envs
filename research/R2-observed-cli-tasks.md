# R2: Observed non-coding agent tasks — the traps that make frontier models fail

Compiled 2026-10-02. This report covers public tasks where an agent works in a terminal or over a set of files and delivers a document, a data answer, a register, a schedule or an analysis.

## 0. Scope and method

**What was inspected.** About 250 individual tasks from 30 public sources (163 rows in Appendix A). For each one I read the real artefacts wherever they were public: the instruction, the fixture files, the grader or tests, and the gold answer. Where trajectory data was public, I also read the trajectories.

**Who did the work.**
- I (the main author) inspected:
  - Terminal-Bench 2.0 and 1.0
  - Harbor Index
  - Spider 2.0-lite
  - KramaBench
  - SkillsBench
- Six parallel research agents covered:
  - GDPval
  - DABstep / OfficeQA / FinanceBench / TAT-QA / FinQA / BizBench
  - spreadsheet and office benchmarks
  - τ-bench / TheAgentCompany / WorkArena / CRMArena
  - APEX / Harvey LAB / TaxCalcBench / Vals
  - Toolathlon / GAIA / DSBench / Finch / MCPMark / QRData

Every agent followed the same rules. They used only generic web queries. They sent no local content to any web service. They worked in scratch directories that were deleted afterwards.

**Evidence tags.**
- **[V]** = verified. The fact was read in task files, a grader, a paper or a leaderboard, or recomputed with code that was actually run.
- **[I]** = inferred.
- **[V-summ]** = a number that came from a web summariser reading a paper. It was not independently checked.

**The single most useful dataset.** This was the public Terminal-Bench 2.0 trajectory dump (`huggingface.co/datasets/yoonholee/terminalbench-trajectories`). It holds 52,104 trials and every one has a reward. I computed per-task solve rates from it for three groups:
- frontier configurations: Opus 4.5/4.6, GPT-5.2/5.3-codex, Gemini 3/3.1 Pro, about 155 trials per task;
- **Claude Code + Opus 4.6**, 5 trials per task;
- **Codex + GPT-5.2/5.3-codex**, 10 trials per task.

The harness is the same one the team calibrates on, though the models are a generation older. Table §2.1 shows the results.

**Harness caveat.** Almost no public number was measured on Fable 5.1 in Claude Code or GPT-6 Astra in Codex, at high effort with no limits. Every rate below is a proxy. The few public results that do name those models or harnesses are collected in §9.

---

## 1. Executive summary

1. **Most public "all-fail" tasks are broken, not hard.** This is the strongest finding in the data.
   - Terminal-Bench 2.0: 14 of the 20 tasks with frontier solve rate below 0.3 (70%) were later fixed for misspecification, environment drift, resource limits or grader bugs. Only 2 of the 26 tasks at 0.9 or above (8%) were. **[V]** (computed; §2.2)
   - τ2-airline: all six tasks that scored 0/16 are on the τ³ fix list. **[V]**
   - τ2-banking: at least 8 of the 25 tasks no frontier model solved are grader voids. **[V]**
   - TheAgentCompany: the clearest example is "303 vs 306" days. Two models computed 306, a recomputation also gives 306, and the key says 303. **[V]**
   - TaxCalcBench: at least 7 of the 12 TY25 cases no top model solved come from ±$1 table conventions or conflicting inputs. **[V]**
   - DABstep: 3 of the 6 templates with pool failure ≥ 0.84 rest on golds nobody can reproduce. **[V]**
   - GDPval: in 4 of the 28 tasks inspected, the expert's own gold contradicts its rubric. **[V]**
   - **Implication:** a low pass rate is evidence of a defect until proven otherwise. The team's "every zero is classified" rule is exactly the right instinct.
2. **Genuine, tool-surviving difficulty concentrates in a few mechanisms.** All of them are a changed or contested premise. None is breadth.
   - The house definition loses to the familiar convention.
   - A later instrument overrides the base document.
   - An authoritative artefact is wrong and only primary records refute it.
   - Totals tie but the composition is wrong.
   - Two rules from two documents must be stacked, and a salient decoy wins if either is missed.
   - An execution order is forced by a dependency that lives in a different document.
   - Two readings agree on easy data and diverge on discriminating data.

   This independently matches the team's own finding that "difficulty is a changed premise, not breadth".
3. **Stating the rule does not prevent the error.** That is the property that makes these traps fair and still hard.
   - Toolathlon `ab-testing` defines "overall" as the mean of per-scenario rates. Claude-4.5-Sonnet still wrote the pooled ratio and failed. **[V]**
   - OfficeQA reports that agents converge on the first plausible figure "even when explicitly instructed" to use the latest revision. **[V]**
4. **Harder public tasks are short and outcome-only, and their rules live inside the documents.**
   - Harvey LAB instructions have a median length of 39 words. **[V]**
   - SpreadsheetBench 2 Debugging uses one generic "audit and fix" sentence for all 100 tasks and scores 8–12%. **[V]**
   - τ2-banking personas state only the goal. The blocking rule sits in the document for a *different* product. **[V]**
   - Pinning *conventions* is not the same as giving *procedure*. Harbor Index removes ambiguity by adding "Analysis constraints (otherwise several defensible models disagree)" and stays hard. **[V]**
5. **Near-miss decoys work only in narrow forms.** Decoys that are merely present are dead: lexical look-alikes, volume, emphasised filters, similar names. This matches the team's census.

   The forms that work:
   - **Salient purpose-labelled candidates that lose only after two rules are stacked.** τ2-banking task_075: Fable 5 0/4, Opus 5 1/4, GPT-5.6-sol 4/4. **[V]**
   - **Same-key twins of a different document type.** In TB2 `financial-document-processor`, Gemini 3 Pro classified the purchase order for order 10248 as an invoice. **[V]**
   - **Plausible wrong values already computed inside the artefact.** SB2 seeded errors; BlueFin stale latched caches. **[V]**
   - **Readings that coincide on the visible data.** TB2 `sparql-university`. **[V]**, recomputed.
6. **Claude and GPT fail on different traps.**
   - τ2-banking: GPT-5.6-sol falls for order-dependence (task_060, 0/4), while Fable 5 solves it. Fable 5 falls for the salient decoy (task_075, 0/4), while GPT solves it. **[V]**
   - TB2 non-coding tasks: Claude Code + Opus 4.6 scored well below Codex + GPT-5.x on `sparql-university` (0.2 vs 1.0), `financial-document-processor` (0.4 vs 1.0), `chess-best-move` (0.0 vs 0.7) and `mteb-*` (0.0 vs 0.4). **[V]**
   - DABstep, bare harnesses: Claude Code + Opus 5 scored 48.7% on hard against 65.3% for Codex + GPT-5.6-sol. The gap is two Claude-side priors:
     - a general "null = applies to all" clause not extended to a boolean field (fail rate 80–100% vs 15%);
     - first-match vs cumulative rule stacking (90–100% vs 0%).
     
     GPT fails the change-set counterfactual more often (65% vs 15%). **[V]**
   - Getting pass@1 below 0.5 on *both* models probably needs one trap of each kind in the same task. **[I]**, untested.
7. **Things that look hard and are not, for an agent with a shell:**
   - complex-sounding scheduling (TB2 `constraints-scheduling`: 1.00 on every frontier configuration) **[V]**
   - layout traps (SpreadsheetBench Verified top score 99.25%) **[V]**
   - lexical string traps (TB2 `log-summary-date-ranges` 0.92, `regex-log` 0.99) **[V]**
   - large enumerations (τ2-banking task_074 with 22 fee errors: Fable 5 4/4) **[V]**
   - explicit filters, and long policies with persuasion pressure

---

## 2. Terminal-Bench 2.0 (and 1.0, 2.1, Harbor Index): what the frontier actually fails

### 2.1 Per-task solve rates for the non-SWE tasks **[V]** (computed from the 52k-trial dump)

"Frontier" pools Opus 4.5/4.6, GPT-5.2/5.3-codex, Gemini 3 Pro / 3.1 Pro across all public harnesses, about 155 trials per task. CC = Claude Code + Opus 4.6 (n=5). Codex = codex/simple_codex + GPT-5.2/5.3-codex (n=10).

| task | category | frontier | CC Opus 4.6 | Codex GPT-5.x | genuine or defect? |
|---|---|---|---|---|---|
| raman-fitting | sci. data | 0.04 | 0.4 | 0.0 | **defect**: Lorentzian form, gamma = HWHM, decimal-comma format and the 1e7/x conversion were all unstated. Z.AI added them to the instruction. |
| extract-moves-from-video | file/video | 0.09 | 0.0 | 0.0 | perceptual; fixed in 2.1 (video hosting) |
| mteb-retrieve | data | 0.15 | 0.0 | 0.4 | **defect**: the test needs mteb's query-prompt prefix; the instruction said only "you have mteb installed". Fixed in 2.1. |
| mteb-leaderboard | data | 0.19 | 0.0 | 0.4 | **defect**: hidden filter "only models with results on all 28 tasks"; also internet drift. Fixed in 2.1. |
| dna-insert | science | 0.22 | 0.0 | 0.44 | **defect**: the test misattributed reverse-primer bases. Z.AI fix. |
| db-wal-recovery | file/data | 0.23 | 0.0 | 0.1 | **genuine** (see below) |
| gcode-to-text | file | 0.23 | 0.2 | 0.6 | genuine but perceptual (render plus OCR of rotated 3-D text) |
| dna-assembly | science | 0.26 | 0.2 | 0.4 | genuine; many coupled constraints plus vendor domain rules (BsaI) |
| chess-best-move | image | 0.44 | 0.0 | 0.7 | perceptual (board from PNG) |
| query-optimize | SQL | 0.50 | 0.4 | 0.6 | **defect**: tests expected Spark SQL, the instruction said PostgreSQL/SQLite; a bit-identical DB hash was required |
| protein-assembly | science | 0.53 | 0.4 | 0.9 | external API drift (fixed) |
| financial-document-processor | doc / finance | 0.68 | 0.4 | 1.0 | genuine-ish: OCR, a same-order PO twin, VAT rate vs amount, all-or-nothing over 17 files (see below) |
| sparql-university | data query | 0.73 | 0.2 | 1.0 | **genuine** (see below) |
| count-dataset-tokens | data | 0.75 | 0.6 | 1.0 | mostly **ambiguity**: 79,566 vs 79,586 depending on tokenising concatenated vs separate fields (see below) |
| overfull-hbox | document | 0.79 | 1.0 | 0.6 | combinatorial edit; changed in 2.1 |
| large-scale-text-editing | text | 0.86 | 1.0 | 0.7 | mechanical |
| log-summary-date-ranges | logs / report | 0.92 | 1.0 | 1.0 | lexical decoy "Next attempt will ERROR" in a WARNING line: **dead** |
| bn-fit-modify | stats | 0.93 | 0.8 | 1.0 | solved |
| regex-log | logs | 0.99 | 1.0 | 1.0 | near-miss dates and IPs: **dead** |
| sqlite-db-truncate / reshard-c4-data | data | 0.99 | 1.0 | 1.0 | solved |
| **constraints-scheduling** | personal assistant | **1.00** | 1.0 | 1.0 | 3 ICS calendars, preferences, buffers, minute granularity: **solved by everyone** |
| **multi-source-data-merger** | ETL | **1.00** | 1.0 | 1.0 | schema mapping plus priority conflict resolution: solved (lenient tests) |

**Leaderboard context [V].**
- TB2 paper (arXiv 2601.11868): Codex CLI + GPT-5.2 63%; Terminus 2 + Opus 4.5 58%.
- TB 2.1 blog (tbench.ai/news/terminal-bench-2-1): GPT-5.3-Codex (Codex CLI) 79.1%; GPT-5.4 (Codex) 77.3%; Opus 4.6 (Claude Code) 70.1%, up from 58.0% on 2.0 once the 28 defective tasks were fixed.
- After the 2.1 fixes, "no task is unsolved". **[V]**

### 2.2 Low solve rate is mostly defects **[V]** (computed)

I cross-referenced the per-task frontier rate with the 28 tasks changed in TB 2.1 (PR harbor-framework/terminal-bench-2#53) and the 6 tasks Z.AI fixed (`zai-org/terminal-bench-2-verified`):

| frontier solve rate | tasks | later found defective |
|---|---|---|
| < 0.3 | 20 | **14 (70%)** |
| 0.3–0.6 | 14 | 6 (43%) |
| 0.6–0.9 | 29 | 9 (31%) |
| ≥ 0.9 | 26 | 2 (8%) |

The defect classes named in PR #53 and the Z.AI notes:
- **The instruction is underspecified relative to the test.** Examples: a hidden 28/28-task filter, a prompt prefix, a function signature, preprocessing conventions, an argument style.
- **The tests over-specify.** Examples: a lowercase-only `[atcg]+` regex in `dna-assembly`; `os.listdir == ["main.c"]`; a bit-identical DB hash.
- **The tests let anything pass.**
- **Resources and network drift.**

Z.AI's TB2 Verified fixes moved Opus 4.5 from 52.4% to 61.8%. **[V]**

**Lesson for the team.** A task that fails "because the model didn't know the convention" is measuring ambiguity. TB2's own maintainers spent a release removing exactly that.

### 2.3 Genuine mechanisms observed in TB2 trajectories **[V]**

**`sparql-university`: independent existential conditions, plus a held-out fixture.**
- The task: list full professors who (2) work in at least one department of an EU-located university and (3) "Among all departments they work in, at least one has more than 10 students currently enrolled". Return `GROUP_CONCAT` of "all countries where the professor currently works in".
- The test runs the agent's query against a **held-out graph** (`tests/university_graph_test.ttl`), not the visible one.
- I ran the reference query and a "same-department" reading on both graphs. The same-department reading requires the EU department itself to have more than 10 students.
  - On the visible graph both readings return the same 3 professors.
  - On the hidden graph the conflated reading drops `Alex Dimakis`. His only EU department (UPM, ES) is small; his US department (Berkeley) has more than 10 students. **[V]**, executed with rdflib.
- Opus 4.5 trajectories state the conflated reading verbatim: "work in at least one EU department with >10 currently enrolled students". The answers were correct on the visible data and failed on the hidden data.
- Other errors seen in captured queries:
  - returning only EU countries instead of *all* the professor's countries (output scope);
  - counting graduated students as "currently enrolled", which wrongly includes Marie Dubois (temporal status);
  - a dangling `uni:Bio10` course IRI in the data (data noise).
- **Bare-environment effect.** The container has no python and no SPARQL engine. CC + Opus 4.6 could not find a runtime and submitted an untested query (0.2). Codex models installed tooling (1.0).
- **Transferable core:** two conditions with separate quantifiers, and a fixture where *only some* members separate the readings.

**`db-wal-recovery`: a destructive first action, then fabrication.**
- Running `sqlite3` on the database first makes SQLite discard the invalid (XOR-encrypted) WAL. Opus 4.5 trajectories say so explicitly: "I accidentally destroyed the WAL file by running sqlite3 before examining it".
- The agents then **fabricated** six records by continuing the visible pattern: alphabetical fruits, values +100.
- The real WAL contains *updates* to existing rows (id 1 → 150, id 2 → 250) that break the pattern. A guess built from the visible pattern is therefore wrong. **[V]**
- Offline analogue: a fixture whose obvious default parse is lossy (see §4, P14).

**`financial-document-processor`: a same-key twin and rate-vs-amount confusion.**
- 17 documents, all-or-nothing scoring. Order 10248 appears three times:
  - as an *invoice* (`TotalPrice 440.0`);
  - as a *purchase order* with identical line items (12×14 + 10×9.8 + 5×34.8 = 440);
  - as a shipping document.
- Two Gemini 3 Pro runs classified the purchase order as an invoice: an 11-row summary at 440 or 168. Another wrote the VAT *rate* (10.0) as the VAT amount on three invoices. **[V]** (trajectory outputs, plus PDFs read)

**`count-dataset-tokens`: an ambiguity, not a trap.**
- "Science" must be mapped to {physics, chemistry, biology} from the README. Every frontier run did that.
- The failures split 79,566 (fields tokenised concatenated) against the key's 79,586 (tokenised separately). Opus 4.5 computed 79,586, then "corrected" itself to 79,566. GPT-5-codex counted `deepseek_reasoning` only (63,841), which *is* a genuine field-scope error. **[V]**
- **Lesson:** two defensible procedures that differ by 0.03%, graded at exact match, produce noise and not signal.

**Harbor Index** (harbor-framework/harbor-index): 80 tasks distilled from more than 6,000 by repeated model runs, broken-task identification, human audits and reward-hacking supervision. GPT-5.6 Terra (Codex, max effort) scores 35.0% (2026-07-14). **[V]**

The non-SWE survivors include five BixBench analysis tasks, two SkillsBench office tasks, GAIA and GAIA2 items, LAB-Bench FigQA and WideSearch. Their adaptation notes are a model of how to remove ambiguity without giving away the method:
- `bix-ordinal-logit-covid` pins "**all** adverse events… **one outcome per subject**… `patients_seen_cat` as an ordinal score" so the accepted OR band "0.74–0.77 is uniquely intended".
- `bix-diff-expr-mirna` pins the exclusions, the scale and the test ("Welch t-test… p ≤ 0.05").

**[V]** These are *convention pins*, not procedures. The agent still has to find, join and compute.

**Terminal-Bench 1.0 tasks of note [V]**
- **`bank-trans-filter`.** Entity resolution under typos. A row belongs if it has "the same name or the same account number". The gold includes:
  - "NWCG Inc. Pty. Ltd." (abbreviation, linked only by BUS-30001)
  - "Incoporated" (typo, different account BUS-30999)
  - BUS-30g01 (typo'd account, correct name)
  - BUS-35001 (correct name, different account)
  
  Rated easy. Included because it is the cleanest public example of a **two-key identity link**.
- **`html-finance-verify`.** "Exactly one financial metric in the html file is incorrect": find line 7329, value 73.4, an internal-consistency audit of an earnings release.
- **`recover-accuracy-log`.** Every rule is spelled out (procedure given): split by timestamp rank, error markers, round half up. Easy.

---

## 3. Source-by-source findings

### 3.1 GDPval (OpenAI, 2025) and GDPval-AA
**Corpus [V]** (`openai/gdpval` gold subset; 220 tasks; 28 tasks inspected in depth, including every reference file, the rubric and the expert deliverable):
- 125 tasks ship reference files: 2.1 per task on average, at most 17.
- Rubrics average 47.5 items. Only about 350 of 10,453 items name an explicit numeric target, so GDPval is mostly a structure and presentation benchmark with a thin layer of exact numbers.
- 44 prompts require outside knowledge through web URLs.
- 40 reference-file names carry "edit", "Fix", "v2" or "scrub" suffixes.

**Leaderboards**
- Paper (arXiv 2510.04374), win-or-tie against experts: Claude Opus 4.1 47.6% (best); GPT-5-high 39.0%; o3 35.2%. **[V-web]**
- OpenAI's later model claims: GPT-5.5 84.9% (2026-04-23). **[V-web]**
- Artificial Analysis GDPval-AA, a model-judged Elo (read 2026-10-02):
  - Opus 5.5 max 1846
  - **Fable 5.1 max 1735 (#4)**
  - GPT-5.6 Sol max 1588
  - **GPT-6 Astra max 1542 (#36)** **[V-web]**
- In the paper Claude leads on formatting and aesthetics, and GPT-5 leads on accuracy and instruction following.

**Authors' failure analysis [V-web].** Expert justifications fall into instruction-following, formatting, accuracy, hallucinated data and miscalculation.
- "Across models, experts most often preferred the human deliverable because models failed to fully follow instructions."
- Prompts cut to 42% of their length made GPT-5 worse ("struggled to figure out requisite context").

**The fair, hard mechanisms found in the files [V]:**
- **Row 139, `c3525d4d`, floor-stand budget revision.** This is the best changed-premise task in the corpus.
  - Store keys are integers in the original list and zero-padded text in the final list. A raw join gives 647 added and 618 removed; normalised, it gives 31 added and 2 removed.
  - A "CAPITAL PLAN" note marks 26 rows. Only 17 of them are new, and 14 new stores carry no note.
  - "+$0.25 per shelf strip" means ×4 strips per unit.
  - The overage rounding (1,289.4 → 1,289) has to be read off a worked figure in an email ($22,802.41).
- **Row 2, `7d7fc9a7`, prepaid amortisation.** The insurer bills one month ahead, which is buried in "first payment due 1/15 … 2/1 coverage". The stated GL balances act as a self-check: they validate the answer without revealing the method.
- **Row 48, `87da214f`, identity-theft claims.** The policy definition ("did not approve") excludes 41 of 50 "encouraged by 3rd party" claims ($185,980 of $229,829). The sample file leaks the answer in a totals row.
- **Row 66, `5f6c57dd`, branch profitability.** An 11th "Corporate" pseudo-branch carries costs. "Orders" ($) sits next to "Orders (Units)".
- **Row 75, `6dcae3f5`, residency 2-SD flags.** First-name identity across yearly sheets collides (two Michelles in one year). The research agent ran 8 convention variants and got 8 different flag sets, none equal to the rubric's. The expert's own gold falls into the near-twin trap.
- **Row 138, `1137e2bb`, case-pack audit.** The rule applies only to CASE lines, and 12 EA lines are decoys. The rule is stated, so this is solved.
- **Row 136, `f841ddcf`, PO slip definition.** "Slipped" is defined literally (5 orders, $13,300). An overlap reading gives 16 orders, $43,634. Also solved once the definition is stated.

**GDPval's own defects are the most important lesson [V].**
- **Gold contradicts rubric in 4 tasks** (rows 0, 28, 69, 75).
  - Row 28: the rubric says to flag at 75% elapsed, unrounded, by days, which gives **53** awards. The gold lists **76**, because it classified on 2-decimal rounded percentages.
  - Row 69: every numeric rubric item uses rates $1.00 higher than the reference document.
- **Rubric targets unreachable from the files in 3 tasks.**
  - Row 4: `AP_TB-1.xlsx` is referenced but not shipped.
  - Row 137: store counts are one higher than the rows in the file.
  - Row 213: none of the received items exists in the location file.
- **The prompt names entities and columns the data lacks.**
  - Row 0: "CB Cash Italy" and "metrics A1 and C1".
  - Row 137: the prompt describes an "out-of-stock percentage" column that does not exist.
- **Unstated conventions graded as obvious:** day count, rounding, SD type, compounding order, quarter definition.

GDPval keeps the right *style* (the files hold the rule, the instruction holds the goal) but fails at pinning conventions and keeping fixture and grader frozen together.

### 3.2 DABstep, OfficeQA / OfficeQA Pro, DAB, FinanceBench, TAT-QA / FinQA, BizBench
**DABstep** (adyen/DABstep: manual.md, fees.json with about 1,000 rules, payments.csv with 138k rows; 450 test tasks).

The research agent built a fee engine and checked it against the public per-task score files, from which every task's accepted answer can be recovered. The engine reproduced the dev answers exactly (1681, 1753, 1871) and the test answers for 1748, 1810, 2536, 1273, 1305 and the 10 MCC tasks. **[V]**

**Scoring [V].** `scorer.py` rounds both sides to the *fewest* decimals present, uses 1e-4 tolerance, drops the minus sign, and lets a single-word answer pass if it is a subset of the gold ("E" passes against "E:13.57").

**Leaderboard [V]** (hard split, recomputed from task_scores; single unvalidated runs, 2026-08-12):
- **Bare Claude Code + Opus 5 High: 48.7%**
- **Bare Codex CLI + GPT-5.6-sol High: 65.3%**
- Two independent Opus 5 agents (2026-09-23): 43.4% and 40.2%
- Validated #1: Claude Haiku 4.5 custom agent, 89.9%
- About 12 entries at 100% are leakage: an "oracle" built from the public score files.

**Fair traps (the rule is written in the documents) [V]:**

| ID | trap | evidence |
|---|---|---|
| D1 | A general clause applied to an unexpected field type. manual.md: *"If a field is set to null it means that it applies to all possible values of that field."* Rules with `is_credit: null` therefore apply to credit transactions. Opus-family agents matched `is_credit == True` only; their answers equal True-only values to every digit. | Opus 5 fail rate 0.80–1.00 across three independent runs; GPT-5.6-sol 0.15 |
| D2 | Per-transaction matching on derived per-merchant monthly statistics: volume, fraud level by EUR *volume*, `capture_delay` buckets, `intracountry`. Skipping a statistic returns a superset of fee IDs (Opus 5 on 1810: 11 extra rules). | Opus 0.30–0.40; GPT 0.00 |
| D3 | A definition in another section. manual §7: *"Fraud is defined as the ratio of fraudulent volume over total volume"*. By count the leader is SwiftCharge; by volume it is TransactPlus (the gold). | both bare CLIs failed task 18 |
| D4 | Undefined concept, so the answer is "Not Applicable" ("excessive fraud threshold"). | both CLIs invented a threshold; 0/2 each |

**Counterfactual-scope traps [V]:**
- **D5, "steer traffic to scheme X".** The gold reprices the merchant's *whole* population as if routed to X. GPT answered with only the existing X traffic. Pool fail rate 0.85; Opus 0.97–1.00; GPT 0.53.
- **D6, "which merchants would be affected".** This means the change set, and it can be empty. GPT answered with the merchants who would still pay. GPT 0.65 vs Opus 0.15.

**Unstated-convention cascade (not fair as written) [V]:**
- **D9 / D10.** When several rules match one transaction, the gold **sums them all**. The manual never says rules stack.
  - Opus answered with the first matching rule (9.48 vs gold 12.91 on task 1712; 5012.90 vs 26210.61 on 2536).
  - Opus fails 90–100% of these; GPT fails 0%.
  - About 92 of bare Opus 5's 194 hard failures come from this one convention.
  - **This is the clearest public case of Claude and GPT holding opposite priors on an unstated rule.** Written into the documents, it becomes a fair and powerful lever (see P16).

**Defects [V].** Three of the six templates with pool failure ≥ 0.84 are mis-specified:
- D11: only one of 20 conventions fits, and it contradicts D1.
- D12: no convention reproduces 13.57; the guideline asks for a card scheme where the answer is an ACI.
- D13: test golds are off from the engine by about 0.01–0.02.

**OfficeQA / OfficeQA Pro** (databricks/officeqa; questions over U.S. Treasury Bulletin PDFs; exact match at 0.0% relative error). The question CSV sits behind a click-through, so the research agent respected it and used only the published examples.

Leaderboard (agent harnesses, July–August 2026) **[V]**, OfficeQA Pro:
- Opus 5 60.9; Fable 5 60.9; GPT-5.6 Sol 60.2; GPT-5.5 57.1; Opus 4.6 51.1.
- With oracle pages, PDF only, at 0% error: GPT-5.6 Sol 71.4, Fable 5 67.7.
- Pro V2: see §3.6.

Traps documented by the authors **[V]**:
- **Revised values.** Agents used the June 2010 bulletin where the September 2010 issue had revised figures. Agents were "prematurely converging on the first numerically plausible instance retrieved, even when explicitly instructed to identify the most recently published figures".
- **Fiscal vs calendar year.** Retrieving FY values for 8 years changed a cubic-regression input series.
- **Near-miss line items.** "Total Public Debt Securities" vs "Total interest-bearing Public Debt".
- **Sample vs population variance.**
- Moving from 5% to 0% tolerance costs 11–17 points even with oracle pages.

OfficeQA's construction rule is worth copying. Questions that both Opus 4.5 and GPT-5.1 agents failed became "Pro". Wherever an alternative answer was equally correct, the question was rewritten; where the alternative was right, the gold was fixed.

**DAB / DataAgentBench** (ucbepic/DataAgentBench) **[V]**
- Top entries use benchmark-tuned prompts and hints: Camber v2 (Opus 5) 0.954; DVIndex (GPT-6-Astra high) 0.877; plain Claude Opus 4.6 0.555. Paper baselines: Gemini-3-Pro 38% pass@1.
- Failure split: incorrect implementation 45%, incorrect plan 40%, wrong data selection 15%.
- Validity problems: the README footnotes admit answer keys that "the question alone does not say" (ICD-O codes; a 3-README gold where agents find about 100). Some validators accept any float that rounds right, or reward over-listing.

**FinanceBench, TAT-QA, FinQA, BizBench** **[V]**
- Mostly mechanical once a formula is given (FinanceBench 06655 DPO; TAT-QA scale and sign).
- The residual "hard" items are often **label errors**:
  - FinanceBench 00585: Boeing effective tax-rate signs are wrong.
  - FinanceBench 01911: MGM coverage is "zero" despite positive operating income.
  - FinQA CME/2017: the "annualized return" gold is 1.6% where the correct CAGR is 15.8%.
  - BizBench SEC-NUM: "87" vs "approximately 87 million shares".
- Two fair traps remain:
  - fiscal-year labels with off-calendar year ends (Walmart FY ends Jan 31);
  - the organic column vs the total-change column (3M: two segments tie at −3.9% in total, while organic separates them).

### 3.3 Spreadsheet and office: SpreadsheetBench (v1 Verified, v2), SheetCopilot, OfficeBench, OSWorld, BlueFin, Vals EMB

**Leaderboards [V unless marked]**
- **SpreadsheetBench v1 Verified** top 99.25 (2026-09-10): **saturated**.
- **SpreadsheetBench 2** (321 tasks, SWE-agent with a 50-turn cap):
  - Overall: arito 54.51; Claude Opus 4.6 34.89; GPT-5.2 26.79.
  - Debugging: **Opus 4.6 12% / GPT-5.2 8%**.
  - Financial Modeling: 34 / 33.
  - Template: 52.6 / 35.1.
- **OSWorld-Verified:** claude-fable-5 85.96 overall, calc 95.7, multi_apps 79.3 (2026-08-01).
- **Vals Excel Modeling Benchmark** (2026-09-29) [V-summ]:
  - Fable 5.1 76.7; GPT-6 Astra 67.3.
  - Leaders pass 89% of formula checks and only **64% of numerical checks**.
- **BlueFin** [V-summ]: GPT-5.5 49.6; Opus 4.7 49.2. Perturbation criteria pass only 15–37%.

**What is still hard:**
- **Row-consistent seeded semantic errors in large linked models.**
  - Examples: an 11-of-12-month SOFR average window; an INDEX range offset one column from its MATCH; a prior-year MATCH; 4 instead of 0.04; a sign flip; a running total double-counted; a rounded hardcode (14.2 vs the linked 14.2034).
  - These errors are consistent across every period, so R1C1 consistency scans miss them.
  - SB2's regression check (≥99.8% of untouched cells must stay unchanged) penalises over-fixing.
- **Changed-premise what-ifs through a model whose cached values are stale or latched.**
  - BlueFin 0122: `=IF($B$3=1,'Returns Analysis'!K31,Summary!D10)` latches the summary, so cached values for non-selected cases are wrong.
- BlueFin's top failure causes [V-summ]:
  - sign on outflows;
  - date-axis misalignment (Q1-2024 vs Q1-2025);
  - **rate vs amount (5.0 vs 0.05)**;
  - end- vs beginning-of-period discounting;
  - overwriting formulas with constants.

**What is defective even in "Verified" sets [V]:**
- SB-V 43436: the golden uses `closed > EOMONTH`, which contradicts the instruction's own definition of "open".
- OSWorld 881deb30: the golden matches only the "Computing Science & IT" row, a hidden discipline filter.
- OfficeBench 1-5/2: a 365-day year in a leap year, unstated.
- OfficeBench 2-48/0: counts a "nap" as sleep, unstated.
- OSWorld 4e6fcf72: `TODAY()` is evaluated at grading time.
- SB-V 146-49: the example orientation is reversed.

### 3.4 Policy and enterprise agents: τ / τ2 / τ-Knowledge, TheAgentCompany, WorkArena++, CRMArena(-Pro)

**Leaderboards [V]**
- **τ2 banking_knowledge** (v1.0.1, 4 trials, pass^1 / pass^4):

  | Model | pass^1 | pass^4 |
  |---|---|---|
  | Qwen 3.8 Max | 55.2 | 35.1 |
  | Claude Opus 5 | 48.7 | 32.0 |
  | GPT-5.6-sol | 46.9 | 27.8 |
  | Claude Fable 5 | 39.7 | 28.9 |
  | Opus 4.6 | 27.3 | 11.3 |

- **τ2 airline / retail / telecom** (2026-02-26, after the τ³ fixes): Opus 4.5 84.0 / 79.6 / 92.3; GPT-5.2 83.0 / 81.6 / 89.7.
- **TheAgentCompany:** paper v3 best full completion is Gemini-2.5-Pro at 30.3%. Admin, Finance and DS are the lowest categories.
- **WorkArena++:** L3 0% for every model (2024); infeasible tasks 0%.
- **CRMArena-Pro:** Gemini-2.5-pro single-turn B2B 54.1; policy compliance 41.0%.

**Genuine traps that survive an offline shell [V]**
- **Salient decoy vs a stacked-rule optimum.** task_075: "BOTH the out-of-network ATM fee AND the foreign ATM withdrawal fee apply". The Purple Account is marketed for travel and costs $45. The Green Fee-Free account costs $0 on both fees. Fable 5 opened Purple 4/4.
- **Cross-document dependency forcing an order.**
  - task_054: a dispute or replacement-card order auto-blocks a credit-line increase, so the CLI must go first and be capped at 50%. Fable 0/4.
  - task_060: savings requires a checking account at least 14 days old. GPT-5.6-sol closed the old account first, 4/4 times.
  - Retail: modifying items locks the order, so the address must be changed first. 0.19 on older models.
- **Expired vs active promotion document.** The "as of" date is in the header. Tasks 070 and 071 score about 1/4.
- **Requester assertions vs the record.** task_102 (false referral date and tier), task_085 (misremembered amounts), task_046 (a claimed "no disputes" while one is pending).
- **Scope overreach.** In retail 112, both GPT-5.2 and Opus 4.5 moved the address on a sibling order that was not requested.
- **Per-transaction caps forcing restructuring.** Airline 23: "at most one travel certificate" per reservation means splitting one trip into three bookings.

**Independent re-check [V].** I downloaded the public τ2 trajectories (`sierra-tau-bench-public` S3, banking_knowledge, 4 trials each) and confirmed:

| task | Fable 5 | GPT-5.6-sol |
|---|---|---|
| task_075 | 0/4 (opened `account_class: "Purple Account"`) | 4/4 |
| task_054 | 0/4 | 0/4 |
| task_060 | 0/4 | 0/4 |
| task_059 | 0/4 | 2/4 |
| task_070 | 1/4 | 0/4 |
| task_074 | 4/4 | 1/4 |
| task_043 / task_044 | 0/4 each | 4/4 each |

**Voids and defects [V]**
- 35 trials across banking 053/060–067 matched every gold write and still scored 0, because the free-text `closure_reason` is hashed into the DB.
- TAC finance-substantial-presence-test: key 303, while models and the recomputation give 306.
- TAC hr-check-attendance: the column and filename names contradict the grader.
- CRMArena-Pro quote_approval: one constant answer ID in 80% of rows.

### 3.5 Legal, finance and accounting: APEX-Agents, APEX-Accounting, Harvey LAB, TaxCalcBench, Vals, LAB-Bench

**Leaderboards [V]**
- **APEX-Agents v1.1** pass@1 (2026-10-02): Gemini 4 Argon 82.2; Opus 5.5 Max 73.5; **Fable 5.1 Max 68.6**. Corporate-law subset: GPT-6 Astra 73.4, Fable 5.1 71.9.
- **APEX-Accounting:**
  - Mean criteria@3: Opus 5.5 61.8; **Fable 5.1 61.0**; **GPT-6 Astra 57.9**.
  - Paper strict Pass@1 is ≤ 9.5%.
  - Pass^8 ≤ 2.6% for every model.
  - 58% of tasks were never fully solved by any model.
- **Harvey LAB** (Vals, all-criteria pass; LLM judges) [V-secondary]: top 25.4; **Fable 5.1 6.67%**; **GPT-6 Astra 5.42%**. The per-criterion pass rate is 92–95%, so the low score is driven by conjunction over a median of 58 criteria.
- **TaxCalcBench TY25** (single LLM call with PDFs, no code execution), strict pass:

  | Model | no tools | with web search |
  |---|---|---|
  | Fable 5.1 | 40% | 48% |
  | GPT-6 Astra | 38% | 62% |

**Genuine traps [V]**
- **Authoritative but wrong memo.** APEX-Accounting world 9 task 5: a self-interested acting Controller's memo asserts that a $2,197.80 reclass "IS NOT AN ERROR… auditors agreed" and gives "audit-blessed final balances". The per-employee workpaper falsifies it ($4,450.55 actual).
- **Totals tie, composition wrong.**
  - Task 17: "I didn't go back to the per-employee detail… since the aggregate passed all balance checks."
  - Task 14: account 1300 nets to $0 but hides a $45,000 debit and its offset.
- **A memo that changes the population after the first pass.** Task 23 adds one check that hits the bank in January to December and removes one returned check. The ">15%" flag set and the top mover both flip.
- **A later instrument changes a parameter, with a binding-leg switch.** Harvey compliance certificate:
  - The Second Amendment raises the add-back cap to the lesser of $7.5M or 15% of pre-add-back EBITDA, so $8.0M claimed is $500k over.
  - The leverage covenant moves from 3.75x to 4.00x.
  - Corrected FCCR is 1.511x against the reported 1.562x.
- **Precedence inside documents.** The SPA body beats an exhibit (April 15 vs 14). A side letter changes the catch-up for one LP. An underlying contract's 45-day consent window is shorter than the SPA's 60.
- **Calendar quirks.** The earn-out notice is "3 days past the 90-day deadline… accounting for 2024 being a leap year". Good-standing certificates have different business-day windows per jurisdiction.
- **Near-miss twins graded as must-not-flag.**
  - "Does NOT flag Texas good standing certificate" (6 business days against a 10-day window), while Delaware (9 against 5) must be flagged.
  - A patent filing dated February 29, 2016 must *not* be flagged as an impossible date. **[V]**, I re-read both criteria in `harveyai/harvey-labs`.

**Ambiguous zeros, not to copy [V]**
- TaxCalcBench us-003: two conflicting IRA value sets, `di` vs `ui`, with no governing rule.
- Contradictory eligibility flags.
- VA joint-1099 allocation convention.
- APEX-Agents world223 (3M buyback): "the score outcome here turns on an assumption the task's rubric never states" (fee and tender premium vs gross proceeds at market).

### 3.6 Toolathlon, GAIA, DSBench (ModelOff), Finch, MCPMark, QRData, InfiAgent-DABench

**Leaderboards [V]**
- **Toolathlon-Verified** (2026-06-30) pass@1: Opus 4.8 76.2; GPT-5.5 73.5. Original Toolathlon (Oct 2025): Claude-4.5-Sonnet 38.6; GPT-5 30.6.
- **OfficeQA Pro V2** with harnesses labelled Claude Code vs Codex: Opus 5 54.4; **Fable 5 45.6**; GPT-5.5 38.9; **GPT-5.6 Sol 33.3**. **[V]** I read these off the README figure `officeqa_pro_v2_agent_harness_performance.png`.
  - Scoring is exact match with 0.0% tolerance, over 90 questions and a median of 5.5 source documents per question.
  - Databricks names the failure modes as "parsing fidelity, incorrect temporal reconciliation as accounting conventions change over time, and misinterpretation of entity scope or category granularity". **[V]**
  - This is the closest public analogue to the team's calibration pair.
- **GAIA test:** 0.93, saturated.
- **DSBench** best 34% (2024 agents).
- **Finch:** GPT-5.1 Pro 38–42%; Sonnet 4.5 25–29%.

**Genuine traps with direct failure evidence** (one Claude-4.5-Sonnet run per task) **[V]**
- **`ab-testing`.** The instruction defines overall = mean of per-scenario rates (73.840%). Claude wrote the pooled ratio, 73.900%, and failed the ±0.05 tolerance.
- **`excel-data-transformation`.** A duplicate "Accumulated Growth(%)" block carries 2025 months outside the requested window. Claude produced 204 rows against 198 while claiming it had obeyed the window.
- **`course-schedule`.** A course-PDF note says an English score ≥70 exempts the student. `memory.json` buries "Scored 88…". Claude enrolled in English.
- **`travel-expense-reimbursement`.** "Assess accommodation separately for each night… Unused allowance… must not offset". Caps are tiered by employee level. Claude flagged 13 claims against 8 and found only 1 of 3 form errors.
- **`excel-market-research`.** A methodology cell says a segment is N/A if *any* component's growth is missing. Renormalising the weights instead changes 31 of 100 cells. **[V]**, recomputed.

**Passed despite decoys [V]:** 1,000 interference invoices (`payable-invoice-checker`); a same-name date decoy (`sales-accounting`); a bold "**Only** taxi" filter.

### 3.7 Spider 2.0-lite, KramaBench, SkillsBench (inspected by the main author)

**Spider 2.0-lite** (xlang-ai/Spider2). 547 tasks; 135 run on local SQLite, 13 of those with an "external knowledge" markdown document. **[V]**
- **The definition documents invert defaults.** `RFM.md` says "A lower R score (e.g., R = 1) indicates a very recent purchase… F = 1 signifies… very frequently… M = 1 indicates higher overall spending". The segment rules then use F+M sums, for example "Champions: Recency = 1 and Frequency + Monetary score between 1 and 4".
- `projection_calculation.md` fixes a non-obvious formula: `(((S2020 − S2019)/S2019) × S2020) + S2020`, with "If specific rates are not available, use a default rate of 1". A model that substitutes a CAGR or a linear trend is refuted by the document.
- **The benchmark itself admits ambiguity through multiple golds.** `local344` (F1 overtake classification, where pit-exit depends on "less than a typical pit stop duration") ships two accepted results: P 37,398 / T 13,402 and P 37,423 / T 13,431. `local003` (RFM) ships four. **[V]**
- **Lesson:** where the definition document leaves latitude ("typical pit stop duration"), the benchmark must accept several answers. A single-answer task has to close that latitude in the document.
- Leaderboard (spider2-sql.github.io, fetched 2026-10-02):
  - Spider 2.0-Snow: top 96.7%; best Claude entry Sonnet 4.5 90.5%.
  - Spider 2.0-Lite: top 76.2%.
  - Spider 2.0-DBT: top 65.6%.

**KramaBench** (mitdbg/KramaBench). Data-lake questions with exact numeric, string or list answers. **[V]**
- The legal-hard questions force entity-name normalisation across sources ("use only the city and state portion of the name, ignoring suffixes like 'Metropolitan Statistical Area'"). Population for 2023 is linearly interpolated between a census figure and an estimate.
- **Its own questions disagree on a boundary.**
  - environment-hard-8 and -11: "meets the standard if it contains fewer than **or equal to** 104 counts".
  - environment-hard-9, -12 and -13: "fewer than 104".
  
  This is a cautionary example. Boundary inclusivity must be stated once, consistently, *and* the data must contain values exactly at the boundary for it to matter.
- 2025 results: best system (o3, self-correcting) 22.08% overall. These are old models.

**SkillsBench** (benchflow-ai/skillsbench, 87 tasks with skills). Office and finance tasks inspected:
- `invoice-fraud-detection`: a 5-reason precedence cascade with fuzzy vendor matching. The fuzzy threshold is unstated, which is an ambiguity risk.
- `xlsx-recover-data`: recover "???" cells from cross-sheet relationships.
- `reserves-at-risk-calc`: a procedural step list with web data.
- `financial-modeling-qa`, `lab-unit-harmonization`, `exam-block-sequencing`.

Two of these survived Harbor Index's 6,000-task distillation as hard:
- `skillsbench-ocr-receipts-to-excel`: 22 receipt images, exact row-by-row match, and the instruction even *gives* the keyword priority list.
- `skillsbench-model-investment-shock-gdp`: web data plus an HP filter in Excel.

Both are hard for reasons the team should not copy: OCR exactness, and web vintages with a 40% tolerance. **[V]**, from the task files and README.

---

## 4. Catalogue of trap patterns

### 4.1 How the list was built and ranked

**Inclusion.** A pattern is listed only if all three hold:
- it appears in tasks with low frontier solve rates or direct failure evidence;
- the failure would survive an agent with a shell and Python, offline;
- a fair version can be graded deterministically.

**Ranking.** Patterns are ordered by how often they appear among the *genuine* (non-defect) low-solve observations across all sources. "Obs." counts the distinct tasks or clusters where the pattern was the identified failure mechanism. It is approximate. P1–P3 are effectively tied. P16–P18 come from a single source (DABstep) but carry the strongest per-model failure rates in the corpus.

### 4.2 Summary table

| rank | pattern | obs. | strongest evidence | survives tools? |
|---|---|---|---|---|
| P1 | Authoritative artefact is wrong; primary records refute it | ~14 | APEX-Acc t5 (memo), t13 (draft), Harvey H1 (certificate), H2 (GP model vs LPA), τ2 102/085/046 (requester claims), SB2 debugging (8–12%), BlueFin stale cache, html-finance-verify | yes |
| P2 | Later or superseding instrument changes a governing parameter | ~12 | Harvey 2nd amendment / side letter / SPA-over-exhibit; OfficeQA revisions ("even when explicitly instructed"); τ2 070/071 expired promo (~1/4); APEX-Acc t23 memo; Spider2 documents | yes |
| P3 | House definition vs familiar convention, including a general clause applied to an unexpected field type | ~14 | **DABstep D1** (`null` = applies to all, extended to a boolean; Opus 5 fails 80–100% vs GPT 15%); DABstep D3 (fraud by volume, not count); Toolathlon ab-testing; Vals FinAgent (average vs ending inventory, OTM converts); OfficeQA (sample vs population variance); Spider2 RFM inverted scores; Toolathlon excel-market-research (no renormalising) | yes |
| P4 | Two rules from two documents must stack; a salient decoy wins otherwise | ~9 | τ2 075 (Fable 0/4), 059; Toolathlon travel per-night cap × level; Harvey dual lesser-of cap; DSBench merit-order flip | yes |
| P5 | Totals tie or aggregate checks pass; composition is wrong | ~8 | APEX-Acc t17, t14; SB2 double counting; Finch #25 sign; AccountingBench plugs | yes |
| P6 | Quantifier, scope or aggregation-level conflation that easy data does not discriminate | ~8 | TB2 sparql-university (held-out graph); CRMArena "first-assigned agent only"; Toolathlon flagged-transactions per-client vs pooled; Harvey per-jurisdiction windows; SB-V 52575 global vs run-local key | yes |
| P7 | Cross-document dependency forces an execution order | ~6 | τ2 054 (Fable 0/4), 060 (GPT 0/4), 062; retail modify-items lock | yes |
| P8 | Scattered eligibility or exemption rule; the qualifying fact is buried | ~6 | Toolathlon course-schedule; APEX-Acc t14 addendum; τ2 banking; GDPval (see §3.1) | yes |
| P9 | Changed premise propagated through an existing computed artefact | ~6 | BlueFin what-ifs (latched cache); SB2 financial-model cascade; DSBench find-that-error cascade; Harvey binding leg switching after correction | yes |
| P10 | Calendar or boundary arithmetic with a stated quirk | ~6 | Harvey leap-year 90-day; business-day windows; DSBench inclusive cross-year shutdown; SB-V 59129 boundary day; KramaBench ≤104 vs <104 | yes, if stated |
| P11 | Identity across renames, variants or near-twins | ~6 | TB2 financial-document-processor (PO twin); TB1 bank-trans-filter; OSWorld HKIEd→EdUHK; KramaBench MSA normalisation; MCPMark carried-over comments; the team's own a-005 near-twin result | yes |
| P12 | Over-helpfulness / false-positive guards | ~6 | Harvey "Does NOT flag Texas"; APEX "no more than one JE", "no more than five flags"; OSWorld empty decoy columns; SB2 regression check; τ2 retail 112 scope overreach | yes |
| P13 | Duplicate block with matching headers, or a layout-encoded category | ~5 | Toolathlon duplicate growth block; GAIA section-header formats; Finch continuation rows | partly |
| P14 | Lossy default read (evidence lost or never seen), then fabrication | ~3 | TB2 db-wal-recovery; Toolathlon external-link formula with cached value; SB2 inputs with no cached values; BlueFin latched values | partly |
| P15 | Precedence ladder with tie fall-through | ~3 | WorkArena expense ladder; SkillsBench invoice-fraud first-match; τ2 retail fallback ladder (38) | yes |
| P16 | Overlapping rules stack (cumulative) vs first match; Claude and GPT hold **opposite priors** | ~3 templates, 45+ tasks | DABstep D9/D10: Opus 5 fails 90–100% (first match), GPT-5.6-sol 0% (sums). The rule is unstated in DABstep, so this is only fair if written into the documents | yes |
| P17 | Counterfactual scope: reprice the whole population; the change set can be empty | ~3 | DABstep D5 "steer traffic" (pool fail rate 0.85); D6 "which merchants affected" (GPT 0.65 vs Opus 0.15; one gold is empty) | yes |
| P18 | Answerability: a concept is mentioned but never quantified, so the answer is "Not Applicable" | ~2 | DABstep D4 (both CLIs invented thresholds); WorkArena infeasible (0%) | yes |

### 4.3 Detailed patterns, with examples and a fair reproduction recipe

Every recipe assumes a single defensible answer and that every rule can be found in the files. "Route" means making several graded checks depend on the same trap.

**P1. Authoritative artefact is wrong, and primary records refute it.**

Examples:
1. APEX-Accounting t5: a memo from the interested Controller asserts an "intentional reclass… auditors agreed" with final balances. The per-employee workpaper shows $4,450.55 against the claimed $2,197.80, so the reclass is a posting error.
2. Harvey: a borrower compliance certificate overstates EBITDA by $500k because the amended cap binds.
3. τ2 task_102: the customer's "last referral 3 weeks ago" is false in the record.

Recipe:
- Ship a memo, draft, certificate or prior-period workpaper from a named party. It asserts specific figures and explanations.
- The primary register falsifies the assertion in exactly one place.
- A policy document in the fixture states the hierarchy: "figures in memoranda must be agreed to the ledger; the ledger governs".
- Never say "verify the memo". Say "prepare the corrected balances".
- Route: the corrected balance, the size of the error, the downstream ratio or flag, and a boolean `memo_figure_accepted`.
- Include true assertions in the same memo, so blanket distrust also fails.

Evidence it bites: APEX-Accounting strict Pass@1 is ≤ 9.5% with Fable 5 / GPT-5.6. Per-trap rates are not published. **[V/I]**

**P2. A later or superseding instrument changes the governing parameter.**

Examples:
1. Harvey: the Second Amendment cap and covenant change, and the SPA body beats Exhibit D.
2. OfficeQA: a revised figure in a later bulletin governs.
3. τ2 070: an expired promotion vs the active one, with the as-of date in the header (about 1/4).

Recipe:
- Write a base document with threshold T0.
- Add an amendment *dated later* that sets T1 and applies to periods the agent will already have computed.
- Include a precedence clause ("this Amendment controls; capitalised terms otherwise as defined").
- Keep the affected population small: 9 to 130 rows, matching the team's own killers.
- Route 3–4 checks through T1: the capped item, the adjusted total, the ratio, the compliance flag.
- Put the as-of date in a different file from the instruments.

**P3. House definition vs familiar convention.**

Examples:
1. DABstep D1: the manual's general clause "If a field is set to null it means that it applies to all possible values of that field" also covers boolean `is_credit`. Three independent Opus 5 runs matched credit as `True` only, failing 80–100%. GPT-5.6-sol failed 15%. **[V]**
2. Toolathlon ab-testing: overall = mean of per-scenario rates, not the pooled ratio. Claude failed.
3. Vals Finance Agent: inventory turnover on *average* inventory, and dilution "including out-of-the-money converts".
4. Spider2 RFM: score 1 = best, which inverts the common 5 = best.

Recipe:
- A methodology memo defines a metric that differs from the textbook default. Examples: mean of rates; average of opening and closing balances; customer-weighted ARPU; per-night caps without offset; "N/A if any component is missing, do not renormalise".
- Build the data so the conventional formula misses an exact-match target by a small but certain margin.
- Route 2–3 checks through the metric.
- Proof of fairness: the definition sentence. Proof of a genuine trap: executing the conventional formula yields a different value.

**P4. Two rules from two documents must stack, and a salient decoy wins if either is missed.**

Examples:
1. τ2 task_075: the travel-branded account loses once *both* the out-of-network and the foreign fee apply. Fable 5 0/4.
2. Toolathlon travel: the per-night cap times the level tier.
3. Harvey: the lesser-of cap (a fixed amount vs a percentage of a base that itself excludes the add-backs).

Recipe:
- Offer 6–10 candidates. One candidate's own document markets it for the user's exact purpose.
- The true cost needs at least two fee or eligibility components defined in *separate* documents, plus 1–2 eligibility exclusions.
- Make the decoy lose by a margin no rounding convention can close.
- Grade `{choice, total_cost}` exactly.

**P5. Totals tie, composition is wrong.**

Examples:
1. APEX-Acc t17: the allocation "passed all balance checks". Per-employee recomputation exposes $2,197.80 and $9.15 entries.
2. APEX-Acc t14: account 1300 nets to $0 but carries a $45,000 debit and its offset.
3. SB2: a running total double-counted inside an annual sum.

Recipe:
- Seed two offsetting row-level misallocations of equal size, so every control total, and the check the agent naturally runs, stays green.
- Ask for per-group totals (which move) and the correcting entry.
- Leave the firm-wide total check in the deliverable. It is the check the model stops at.

**P6. Quantifier, scope or aggregation level conflated, where easy data does not discriminate.**

Examples:
1. TB2 sparql-university: "works in an EU department" and "some department has more than 10 students" are separate existentials. They are identical on the visible graph and diverge on the held-out graph.
2. Toolathlon flagged-transactions: mean + 3σ "for each client" (59 rows) vs pooled (12).
3. CRMArena: handle time counts only the first-assigned agent and excludes transferred cases.

Recipe:
- Write the criterion with two independently quantified conditions ("among all of its sites, at least one…") or an explicit aggregation level.
- Build the population so most members satisfy both readings identically.
- Make 2–4 members separate the readings, and put those members in the graded answer set.
- The team cannot hide a test fixture, but **step 2** can play the role of TB2's held-out graph. Step 2 presents a revised fixture in which the separating members now appear, and the step-1 reading must be re-applied in a fresh session. **[I]**

**P7. A cross-document dependency forces the execution order.**

Examples:
1. τ2 054: a dispute blocks the CLI, so the CLI goes first and is capped. Fable 0/4.
2. τ2 060: the savings account needs a checking account at least 14 days old, so do not close first. GPT 0/4.
3. Retail: modifying items locks the order.

Recipe:
- A request memo lists 3–4 actions in a fatal order and emphasises the wrong one.
- The blocking rule lives in the document for a *different* product.
- The deliverable is `{ordered_actions[], outcome_per_request[]}`. The grader simulates the plan against rule tables in the fixture, so nothing is stored.
- Prove that exactly one order completes every request, or state the tie-break.

**P8. Scattered eligibility or exemption rule.**

Examples:
1. Toolathlon course-schedule: the exemption note is in the course PDF; the qualifying fact is one line in a memory file.
2. APEX-Acc t14: a contract addendum makes $23,500 reimbursable.
3. GDPval row 2: the insurer's one-month payment lead is buried in a due-date sentence. GDPval row 154: a mandatory 10% admin fee appears only in the rate card.

Recipe:
- Put the rule in a footnote or note of document A.
- Put the triggering fact once, among unrelated facts, in document B.
- The instruction does not mention either.
- Exactly one item flips. Downstream counts, sums and sorts cascade from it.

**P9. A changed premise propagated through an existing computed artefact.**

Examples:
1. BlueFin: a what-if on a model whose summary latches stale values.
2. SB2 financial model: upstream errors cascade into regression cells.
3. Harvey: after the EBITDA correction, the binding leg of the cap switches.

Recipe:
- Supply a worked schedule (register, allocation or covenant test) whose cached results reflect the *old* premise.
- A dated change notice alters one input.
- Ask for 3–5 outputs that must be recomputed.
- Cached values must be plausible and wrong. Route several checks through the one premise.

**P10. Calendar or boundary arithmetic with a stated quirk.**

Examples:
1. Harvey: the 90-day deadline crosses Feb 29, 2024, so the notice is 3 days late, and it is the Company's *own* notice.
2. Harvey: business-day windows differ by jurisdiction.
3. DSBench: an inclusive shutdown from 15 Dec to 3 Jan crosses a year boundary.

Recipe:
- Ship a holiday calendar and an explicit inclusivity rule.
- Place 2–3 items exactly at the boundary.
- Make the party that is late the one the instruction does not ask about.
- On its own this is a weak lever with Python available. Its value is that it compounds with P2 and P9. **[I]**

**P11. Identity across renames, variants or near-twins.**

Examples:
1. TB2 financial-document-processor: a PO and an invoice share an order ID and line items.
2. TB1 bank-trans-filter: name OR account number, with typos and an abbreviation.
3. OSWorld: an institution renamed mid-series.

Recipe:
- A data dictionary states the identity rule, e.g. "the same entity if the registration number matches, regardless of name".
- Include one rename (documented in a footnote), one abbreviation linked only by key, and one twin of a different document type that shares the key but is excluded by a scope sentence.
- The team's own result (a-005: a near-twin identity re-decided in fresh step 2) is consistent with this. **[I]**

**P12. Over-helpfulness and false-positive guards.**

Examples:
1. Harvey: "Does NOT flag Texas" (6 business days against a 10-day window).
2. APEX: "no more than one JE".
3. OSWorld: empty "Net Sales" columns must stay empty.
4. τ2 retail 112: a sibling order must be left unchanged.

Recipe:
- Pair each true exception with a twin that looks identical but sits under a different window or rule.
- Grade the exception list as an exact set, so flagging the twin fails.
- This is the deterministic equivalent of a near-miss decoy, and it is the only decoy form with grader-level enforcement.

**P13. Duplicate block or layout-encoded category.**

Examples:
1. Toolathlon: a duplicate growth block carries out-of-window months.
2. GAIA: Blu-Ray vs DVD is encoded only by section header rows.
3. Finch: continuation rows in the key column.

Recipe:
- Use a *semantic* duplicate, not a formatting one: same header, extra periods. The window rule must exclude it.
- Pure layout traps are solved by tool-using agents (SB-Verified 99%). Use this pattern only combined with a scope rule.

**P14. Lossy default read, then fabrication.**

Examples:
1. TB2 db-wal-recovery: opening the database discards the WAL, and the agent then invents the "pattern".
2. Toolathlon: an external-link formula whose only value is the cached one.
3. BlueFin: latched cells.

Recipe (read-only analogue):
- Information is carried in a channel that default parsers drop, *and* the fixture documents that channel. Examples: tracked deletions in a docx, a "superseded" strike-through convention stated in the register's legend, a hidden sheet named in the index, comments that carry corrections.
- The visible pattern must not predict the hidden values.
- This is not needed for the step-1/step-2 split, and it is weaker if the instruction names the channel. **[I]**

**P15. Precedence ladder with tie fall-through.**

Examples:
1. WorkArena: keep the expenses linked to tasks; if all or none are linked, keep the oldest; if dates tie, keep the most expensive.
2. SkillsBench: "If multiple apply, pick the first one in the order listed".

Recipe:
- Make each rung decide at least one group.
- Include a group where rung 1 is a tie, so it falls through to rung 2.
- On its own this is weak. Frontier models execute explicit ladders well. **[I]** (TB2 constraints-scheduling, with tie-breakers, scored 1.00.)

**P16. Overlapping rules stack.**

Example: DABstep D9 and D10. When several fee rules match one transaction, the gold charges all of them. Opus 5 charges only the first match (task 1712: 9.48 vs 12.91), GPT-5.6-sol sums them. About 92 of bare Opus 5's 194 hard failures trace to this. **[V]** In DABstep the rule is *unstated*, so the zero there measures a prior, not a misreading.

Recipe:
- State the stacking rule once, away from the formula, e.g. in an FAQ or amendment: "every rule whose conditions a transaction satisfies is charged; charges are cumulative".
- Make 15–30% of items match two or more rules.
- Route totals, deltas and counterfactuals through the rule.
- The mirror rule ("only the most specific matching rule applies; ties go to the lower rule ID") exploits the GPT prior instead. The team could use one in step 1 and the other in a step-2 amendment. **[I]**

**P17. Counterfactual scope.**

Examples:
1. DABstep "steer traffic to X": reprice the *whole* population as if routed to X.
2. DABstep "which merchants would be affected if fee 384 applied only to type F": the answer is the change set, and for fee 17 it is empty.

Recipe:
- Ask for the change set, plus at least one counterfactual whose change set is empty.
- A glossary defines "affected" as "whose charge changes".
- Grade sets exactly.

**P18. Answerability.**

Example: DABstep "excessive fraud threshold" is never quantified, so the gold is "Not Applicable".

Recipe:
- The schema allows `null` or "not determinable" for one field.
- The documents mention the concept without quantifying it.
- Keep it to a minority of fields so a constant-N/A strategy fails. CRMArena-Pro's 77–80% answer priors show what goes wrong otherwise.

---

## 5. How the hardest tasks write their instructions

1. **Outcome only, short, no file list.** **[V]**
   - Harvey LAB has a median of 39 words. Example: "Review the earnout calculation notice… and prepare a comprehensive issues memo identifying errors, disputes, and risks."
   - APEX-Accounting: prompts "do not explain methods a competent accountant would already know, and name files only when they are unintuitive"; "the agent receives no file list".
   - SB2 Debugging: one sentence shared by all 100 tasks.
2. **Requirements are scattered, and precedence is decided inside the documents.** **[V]**
   - Amendments, side letters, addenda, a methodology cell, a footnote in a course PDF, the document for a *different* product (τ2 054).
   - The instruction never repeats a rule. Harder tasks also put the "as-of" date in a separate file (τ2 070).
3. **"What not how" without ambiguity: pin conventions, not steps.** **[V]**
   - Harbor Index: "Analysis constraints (otherwise several defensible models disagree): build the outcome from **all** adverse events… **one outcome per subject**… enter `patients_seen_cat` as an ordinal score".
   - TB 2.1 made the same move: the 28/28-task filter, "must use the installed mteb package", "do not modify the database file".
   - DSBench removes exactly one ambiguity with one clause: "you should not take the absolute value of the differences".
   - These pins state *what* the answer means. They do not say how to compute it.
4. **The governing document is named neutrally.** "Check the memo that has been shared by the acting Controller" (APEX-Acc t5). The task is "prepare the corrected balances", never "verify the memo". **[V]**
5. **The request emphasises the wrong thing or uses the fatal order.** τ2 060: the closure is mentioned "first and in more detail". The airline user insists they are "Gold" when the record says Silver. **[V]**
6. **Single-answer enforcement.**
   - APEX v1.1 scores hedged "scattergun" answers as zero. **[V]**
   - The c06 pilot proposes "primary-answer scoring": values that appear only in sensitivity lines do not count. **[V]**
   - The team's JSON schema should accept one value per field and no alternatives.
7. **Revealing procedure makes tasks easy.** **[V]**
   - TheAgentCompany "round up their total work hours… not each individual day" is mostly solved.
   - InfiAgent-DABench constraints fix every step and are mechanical.
   - TB1 recover-accuracy-log spells out every rule and is easy.
   - WorkArena: going from L2 (steps given) to L3 (protocol named only) took GPT-4o from 3% to 0%. Withholding procedure matters only when the protocol is non-trivial. **[V]**
8. **The hidden grader convention is the anti-pattern.**
   - TAC's "flag every Partial" convention.
   - OSWorld's hidden discipline filter.
   - mteb-leaderboard's 28/28 filter.
   - APEX world223's unstated fee and premium.

   Each produced a "hard" task that measured mind-reading, and several were later fixed. **[V]**

## 6. Near-miss decoy designs, and evidence that they work or don't

**Work** (direct failure evidence on frontier or near-frontier models):

| design | evidence |
|---|---|
| A purpose-labelled salient candidate that loses only when two rules stack | τ2 task_075: Fable 5 0/4, Opus 5 1/4 (GPT-5.6-sol 4/4); task_059 EcoCard bonus: Fable 0/4. **[V]** |
| A same-key twin of a different document type (PO vs invoice for order 10248, identical items and total) | TB2 financial-document-processor: Gemini 3 Pro included the PO in failing runs. **[V]** |
| A plausible wrong value already *inside* the artefact (seeded formula error, stale latched cache, interested memo) | SB2 Debugging 8–12%; BlueFin perturbation 15–37%; APEX-Acc Pass@1 ≤ 9.5%. **[V]**, aggregate only |
| A duplicate block with a matching header carrying out-of-window periods | Toolathlon excel-data-transformation: Claude-4.5-Sonnet failed. **[V]**, 1 run |
| Readings that coincide on most members and diverge on a few | TB2 sparql-university: conflated reading correct on the visible data, wrong on the held-out data; CC Opus 4.6 0.2. **[V]** |
| An exception twin under a different window, graded "must NOT flag" | Harvey H4 Texas vs Delaware. Exists, but no per-criterion rates are published. **[V]** design, **untested** effect |

**Dead** (present in the files, did not bite):

| design | evidence |
|---|---|
| A lexical look-alike (the word "ERROR" inside a WARNING line; date-like `1134-12-1234`) | TB2 log-summary 0.92; regex-log 0.99. **[V]** |
| Volume (1,000 interference invoices; 4,200 messy cells) | Toolathlon payable-invoice-checker passed; Toolathlon's "Hard" third is no harder than "Medium". **[V]** |
| An emphasised explicit filter ("**Only** taxi", "not this week") | Toolathlon reimbursement-form-filler and sales-accounting passed. **[V]** |
| A rank or label decoy ("Assistant Professor" vs "Professor") | All captured sparql failures excluded assistant professors correctly. **[V]** |
| A decoy folder or near-name source (grf/ vs ecs/) | Cheap for tool users. **[V]** (OSWorld); matches the team's census ("decoy docs/rows dead") |

**Rule of thumb.** A decoy works when choosing it is the *natural conclusion of a correct-looking computation* that skipped one premise. It does not work when the decoy is merely present and can be excluded by reading carefully. **[I]**, consistent with every row above.

## 7. Patterns that look hard but are solved by agents with tools

| looks hard | evidence it is solved |
|---|---|
| Multi-party scheduling with preferences, buffers, minute granularity, tie-breakers | TB2 constraints-scheduling 1.00 / 1.00 / 1.00 **[V]** |
| Multi-source ETL with schema mapping and priority conflicts | TB2 multi-source-data-merger 1.00 **[V]** |
| Log analysis with date windows and decoy strings | TB2 log-summary 0.92; regex-log 0.99 **[V]** |
| Spreadsheet layout: merged cells, multi-table sheets, header offsets, text dates, wildcards | SB v1 Verified top score 99.25%; OSWorld calc 95.7% (Fable 5) **[V]** |
| Large enumerations and recomputations | τ2 banking task_074 (22 errors over 4 accounts): Fable 5 4/4; Harvey per-criterion pass ≈95% **[V]** |
| Long policies with user persuasion pressure | τ2 airline: Opus 4.5 84% **[V]** |
| Procedure-specified analytics (seed, split, encoding given) | InfiAgent-DABench **[I]** |
| Single-file lookups | GAIA test 0.93 **[V]** |
| Arithmetic and formula knowledge (CAGR, interpolation, bracket tables), once the table is in the files | TaxCalcBench failures cluster on missing tables and rounding conventions **[V/I]** |
| Tool or transport failures (paged MCP output, Excel-MCP header writes, missing runtime) | Disappear with direct file I/O **[V]** (Toolathlon T11, T1) |

**Hard for reasons the team should avoid:**
- perception: OCR, chess PNGs, rotated G-code text, video;
- live web and API drift;
- outside knowledge: World Bank regions, Whyte notation, EU membership "as of" a date (this one is fair only if a list is shipped);
- unstated conventions and hidden filters;
- LLM-judge conjunction over dozens of criteria.

## 8. Recipes: assembling a task that both models should fail

**Measurement caveat.** This combination is **untested** in the team's harness. The two TB2 per-harness splits and the τ2 per-model splits suggest the Claude and GPT families fail different traps. The τ2 splits are task_060 vs 075 and the 043–047 skipped checks; the TB2 splits are in §2.1. **[V]** So each task should carry at least one trap from each column:

| tends to catch Claude (Fable / Opus) | tends to catch GPT (5.x) |
|---|---|
| A salient purpose-labelled decoy that requires two stacked rules (P4; τ2 075, 059) | An execution-order dependency in another product's document (P7; τ2 060) |
| Bare-environment verification: the agent must build its own check, and submits unverified (TB2 sparql, CC) | Scope overreach on sibling records (P12; τ2 retail 112, both families) |
| Skipping mandated eligibility reads when the outcome looks obvious (τ2 043–047) | Field-scope omission (TB2 count-dataset-tokens: deepseek_reasoning only) |
| A general wildcard clause applied to a boolean field (DABstep D1: Opus 5 80–100% fail vs GPT 15%) | The change-set counterfactual ("which merchants are affected", including an empty set; DABstep D6: GPT 65% fail vs Opus 15%) |
| A first-match prior where documents say rules stack (DABstep D9/D10: Opus 90–100% fail vs GPT 0%) | The mirror case: a sum prior where documents say only the most specific rule applies (**[I]**, untested) |

**Skeleton A: amended premise plus interested memo.** P2 + P1 + P9 + P12.
- *Step 1:* compute a covenant or allocation schedule from a base agreement, a ledger extract, and a borrower or Controller memo that asserts a figure.
- *Step 2*, in a fresh session: an amendment dated after period-end changes one cap (lesser-of, where the binding leg switches) and applies retroactively to a population of 9–130 items. The step-2 instruction repeats only the deliverable, not the change.
- Checks to route through the premise:
  - the corrected capped item;
  - the adjusted total;
  - the ratio;
  - the compliance flag;
  - the exact set of exceptions, with a twin that must not be flagged;
  - `memo_figure_accepted: false`.

**Skeleton B: house metric plus independent quantifiers.** P3 + P6 + P11.
- A methodology note defines the metric (mean of rates, no renormalising) and an eligibility rule with two separate existentials across an entity's sites.
- The identity rule (key over name) links one renamed entity.
- Most entities satisfy both readings identically. Three entities separate them.

**Skeleton C: request in the fatal order plus a salient product.** P7 + P4 + P1.
- A client letter asks for 4 actions in the order that fails, and makes 2 true and 2 false claims about its own record.
- The product documents carry the blocking rule (in another product's document) and the fee components (in two documents).
- The deliverable is `{ordered_actions, chosen_product, total_cost, per_request_outcome}`. The grader simulates the plan from the rule tables.

**Fairness checks the team already runs, sharpened by this evidence.** For every trap, the bundle should carry three things:
- the *sentence* in the fixture that refutes the trap answer;
- an executed counterfactual showing that the convention, conflated or decoy answer differs from the target;
- proof that no second defensible reading exists. Spider2's multi-gold, TaxCalcBench us-003, count-dataset-tokens (79,566 vs 79,586) and TB2's hidden filters all failed that third test.

## 9. Public numbers closest to the team's calibration pair

These figures come from different harnesses and graders, and none is a substitute for the team's own screen.

| benchmark | Claude | GPT | notes |
|---|---|---|---|
| OfficeQA Pro V2 ("Claude Code" vs "Codex") | Fable 5 45.6, Opus 5 54.4 | GPT-5.6 Sol 33.3, GPT-5.5 38.9 | exact-match document QA; both below 50% **[V]** |
| Harvey LAB (all-pass, LLM judge) | Fable 5.1 6.67% | GPT-6 Astra 5.42% | conjunction over ~58 criteria; per-criterion ~95% **[V-secondary]** |
| APEX-Agents v1.1 pass@1 | Fable 5.1 68.6% | GPT-6 Astra 73.4% (law subset) | **[V]** |
| APEX-Accounting mean criteria@3 | Fable 5.1 61.0% | GPT-6 Astra 57.9% | strict Pass@1 ≤ 9.5% in the paper **[V]** |
| TaxCalcBench TY25 strict, no tools / web | Fable 5.1 40 / 48% | GPT-6 Astra 38 / 62% | single call, no code execution **[V]** |
| Vals Excel Modeling | Fable 5.1 76.7 | GPT-6 Astra 67.3 | numerical checks 64% for leaders **[V-summ]** |
| τ2 banking_knowledge pass^1 / pass^4 | Fable 5 39.7 / 28.9; Opus 5 48.7 / 32.0 | GPT-5.6-sol 46.9 / 27.8 | **[V]** |
| TB2 non-SWE (Claude Code vs Codex) | Opus 4.6 (see §2.1) | GPT-5.2/5.3-codex | Codex ≥ CC on most non-SWE tasks **[V]** |
| DABstep hard (bare Claude Code vs bare Codex CLI, single run) | Opus 5 High 48.7% | GPT-5.6-sol High 65.3% | the gap is two Claude priors (D1, D9/D10) **[V]** |
| OfficeQA Pro (agent harnesses) | Fable 5 60.9; Opus 5 60.9 | GPT-5.6 Sol 60.2 | exact match **[V]** |
| GDPval-AA (model-judged Elo) | Fable 5.1 max 1735 | GPT-6 Astra max 1542 | rubric and format-heavy **[V-web]** |

---

## Appendix A: per-task table

Column key:
- **Proc.** = is the procedure revealed? Y yes, P partly, N no.
- **Tools?** = does the failure survive an agent with a shell and Python? Y, P, N.
- **Solve evidence** = public rate or direct failure evidence.
- **Tag** = V (verified) or I (inferred).

| # | Source | Task / ID | Deliverable | Trap / difficulty mechanism | Grading | Proc. | Tools? | Solve evidence | Tag |
|---|---|---|---|---|---|---|---|---|---|
| 1 | Terminal-Bench 2.0 | sparql-university | SPARQL query file | two independent existentials (EU dept; any dept >10 *current* students) conflated; output = ALL countries; graduated students excluded; graded on held-out graph that alone separates readings; bare env (no python) | query run on hidden TTL, set equality | N | Y | frontier 0.73; CC Opus4.6 0.2; Codex 1.0 | V |
| 2 | Terminal-Bench 2.0 | db-wal-recovery | recovered.json (11 rows) | opening DB with sqlite3 discards XOR-encrypted WAL; agents then fabricate rows from visible pattern; real WAL has UPDATEs (150, 250) breaking the pattern | exact values | N | P | frontier 0.23; CC 0.0; Codex 0.1 | V |
| 3 | Terminal-Bench 2.0 | financial-document-processor | sort docs + summary.csv | OCR of JPG invoices; PO and shipping doc for same order 10248 as invoice (same items, 440); VAT rate (10%) vs amount; "Total" beats "Amount Due"; all-or-nothing over 17 files | file hashes + ±0.01 values | P | P | frontier 0.68; CC 0.4; Codex 1.0; Gemini failures inspected | V |
| 4 | Terminal-Bench 2.0 | count-dataset-tokens | integer | "science" = physics+chemistry+biology (README); "deepseek tokens" = reasoning+solution; 79,566 vs 79,586 by concatenation choice (ambiguity) | substring exact | P | P | frontier 0.75; CC 0.6; Codex 1.0 | V |
| 5 | Terminal-Bench 2.0 | constraints-scheduling | ICS meeting file | 3 calendars, hard constraints, buffers, minute granularity, tie-breakers | brute-force earliest-slot check | P | N | frontier 1.00 (solved) | V |
| 6 | Terminal-Bench 2.0 | multi-source-data-merger | parquet + conflicts.json | schema mapping, priority conflicts | lenient value checks | Y | N | 1.00 | V |
| 7 | Terminal-Bench 2.0 | log-summary-date-ranges | summary.csv | date windows (today/7/30/MTD); WARNING lines containing "ERROR" (decoy) | exact counts | P | N | 0.92 | V |
| 8 | Terminal-Bench 2.0 | regex-log | regex | last date on lines with valid IPv4; look-alike tokens | findall exact | Y | N | 0.99 | V |
| 9 | Terminal-Bench 2.0 | mteb-retrieve | one line | mteb applies query prompt prefix; SentenceTransformer directly gives different rank (unstated until 2.1) | exact | N | P | 0.15 (defect, fixed) | V |
| 10 | Terminal-Bench 2.0 | mteb-leaderboard | model id | hidden "28/28 tasks" filter; internet | exact | N | N | 0.19 (defect, fixed) | V |
| 11 | Terminal-Bench 2.0 | raman-fitting | results.json | unstated Lorentzian/HWHM, decimal comma, 1e7/x conversion | tolerance | N | P | 0.04 (defect; Z.AI fix) | V |
| 12 | Terminal-Bench 2.0 | gcode-to-text | flag text | text printed on existing object: filter Z / object labels, rotate 3-D, OCR | exact | N | P | 0.23 | V |
| 13 | Terminal-Bench 2.0 | chess-best-move | moves | read board from PNG | exact set | N | N (perceptual) | 0.44; CC 0.0; Codex 0.7 | V |
| 14 | Terminal-Bench 2.0 | dna-assembly | primers.fasta | coupled Tm/length/overhang constraints, vendor BsaI rules, minimum pairs; lowercase-only regex in tests | tests | P | Y | 0.26 | V |
| 15 | Terminal-Bench 2.0 | dna-insert | primers.fasta | Q5 SDM insertion design | tests (grader bug fixed) | P | Y | 0.22 (defect) | V |
| 16 | Terminal-Bench 2.0 | protein-assembly | gBlock | many coupled bio constraints + API data | tests | Y | P | 0.53 (API drift) | V |
| 17 | Terminal-Bench 2.0 | query-optimize | sol.sql | equivalence + performance; dialect/test misalignment | tests | P | P | 0.50 (defect) | V |
| 18 | Terminal-Bench 2.0 | overfull-hbox | edited .tex | synonym substitution to remove overfull boxes | compile | Y | N | 0.79 | V |
| 19 | Terminal-Bench 2.0 | large-scale-text-editing | vim script | keystroke-limited macros over 1M rows | byte-exact | Y | N | 0.86 | V |
| 20 | Terminal-Bench 2.0 | bn-fit-modify | DAG + samples | structure learning with tie rule given | tests | Y | N | 0.93 | V |
| 21 | Terminal-Bench 1.0 | bank-trans-filter | output.json | identity by name OR account; abbreviation linked only by account; typo'd names/accounts | exact list | P | P | rated easy | V |
| 22 | Terminal-Bench 1.0 | html-finance-verify | line,value | exactly one inconsistent metric in a 10-K HTML | exact | N | Y | rated medium | V |
| 23 | Terminal-Bench 1.0 | recover-accuracy-log | 7 files | every rule spelled out (rank split, error markers, round-half-up) | exact | Y | N | easy | V |
| 24 | Terminal-Bench 1.0 | heterogeneous-dates | number | mixed date formats across two CSVs | exact | N | N | easy | V |
| 25 | Terminal-Bench 1.0 | schedule-vacation / organization-json-generator / form-filling | files | tool-use and schema following | tests | Y | N | easy/medium | V |
| 26 | Harbor Index | bix-ordinal-logit-covid | number | modeling choices pinned ("all AEs", "one outcome per subject", ordinal covariate) to make OR band unique | range 0.74–0.77 | P (conventions pinned) | Y | survived 6k→80 distillation | V |
| 27 | Harbor Index | bix-diff-expr-mirna | percentage | exclusions + log2(Ct) + Welch test pinned | range | P | Y | survived distillation | V |
| 28 | Harbor Index | bix-filter-chip-variants / bix-cpg-density-jackdaw | number | domain filtering definitions (intronic/intergenic/UTR; methylation thresholds) | range 40–60 | N | Y | survived distillation | V |
| 29 | Harbor Index | skillsbench-ocr-receipts-to-excel | xlsx | 22 receipts, exact row match, keyword priority *given* | exact workbook | Y | N (OCR) | survived distillation | V |
| 30 | Harbor Index | skillsbench-model-investment-shock-gdp | formula workbook | web data vintages + HP filter; 40% tolerance on ECB-derived cells | structural/range | Y | N (web) | survived distillation | V |
| 31 | Harbor Index | gaia2-ambiguous | actions + message | must surface ambiguity while executing 4 chores | action DAG judge | N | N | survived distillation | V |
| 32 | Harbor Index | labbench-count-deg-in-pathway | MCQ letter | read figure panel | exact | N | N (vision) | survived distillation | V |
| 33 | Harbor Index | widesearch-list-bri-projects-2025 | table | web breadth, ensemble judge >0.6 | judge | N | N (web) | survived distillation | V |
| 34 | Spider 2.0-lite | local003 (RFM) | result table | RFM doc inverts default (1 = best) and uses F+M sum bands | gold CSVs (4 accepted) | P | Y | multi-gold = admitted ambiguity | V |
| 35 | Spider 2.0-lite | local344 / local336 (F1 overtakes) | counts by type | precedence-ordered classification R/P/S/T; "typical pit stop duration" vague | 2 accepted golds (P 37,398 vs 37,423) | P | Y | multi-gold | V |
| 36 | Spider 2.0-lite | local061 / local050 (projection) | number | document fixes non-obvious growth-projection formula + default FX rate 1 | gold CSV | P | Y | — | V |
| 37 | Spider 2.0-lite | local009 / local010 (haversine) | number | formula doc; city-pair dedupe and bucket edges | gold CSV | P | Y | — | V |
| 38 | Spider 2.0-lite | local258 / local259 (IPL bowling) | table | domain definitions (bowler-attributed wickets, extras excluded from economy) | condition cols | P | Y | — | V |
| 39 | Spider 2.0-lite | local275 / local277 (seasonality) | products / number | centred moving average + weighted regression per doc | gold | P | Y | — | V |
| 40 | KramaBench | legal-hard-1/2 | number / name | MSA name normalisation across sources; 2023 population by interpolation | numeric_exact | P (hints) | Y | best 2025 system 22% overall | V |
| 41 | KramaBench | environment-hard-8/9/11/12/13 | numbers / names | boundary stated inconsistently across questions (≤104 vs <104) | exact | P | Y | (authoring defect) | V |
| 42 | KramaBench | environment-hard-14 | label | regional rainfall mapping + median imputation spelled out | exact | Y | Y | — | V |
| 43 | SkillsBench | invoice-fraud-detection | fraud_report.json | 5-reason precedence, fuzzy vendor match (threshold unstated) | exact | Y | P | — | V |
| 44 | SkillsBench | xlsx-recover-data | workbook | recover "???" from cross-sheet relationships | groundtruth | N | Y | — | V |
| 45 | SkillsBench | reserves-at-risk-calc / financial-modeling-qa / lab-unit-harmonization / exam-block-sequencing | workbook / answers | procedural steps with web data; unit harmonisation; MIP timetabling | tests | Y/P | P | — | V |
| 46 | Terminal-Bench 2.0 | sqlite-db-truncate / password-recovery / git-leak-recovery | recovered rows / password / secret | forensic recovery from truncated DB, deleted file, rewritten git history (format hints given) | exact | P | N | 0.99 / 0.88 / 0.97 (solved) | V |
| 47 | Terminal-Bench 2.0 | tune-mjcf / video-processing / mcmc-sampling-stan / distribution-search | artefacts (code-heavy) | numeric tuning; video event detection; Stan model spelled out; KL target search | tests | Y/P | P | 0.71 / 0.15 / 0.83 / 0.98 | V |
| 48 | Harvey LAB | intellectual-property/extract-filing-dates-from-patent-schedule | report | Feb 29, 2016 filing date must NOT be flagged as invalid (leap-year near-miss) | binary criterion | N | Y | — | V |
| 49 | GDPval | row 139 c3525d4d (order clerk) | revised budget | int vs zero-padded store keys (647/618 raw vs 31/2 true); partial "CAPITAL PLAN" decoy note; per-strip price ×4; rounding read from worked email figure | rubric, ~20 exact values | N | Y | expert-graded; fair changed-premise | V |
| 50 | GDPval | row 2 7d7fc9a7 (accountant) | prepaid amortisation schedule | BCBS one-month payment lead buried in a due-date sentence; GL balances as self-check; PDF layout variants | 56 items incl. exact balances | P | P | — | V |
| 51 | GDPval | row 48 87da214f (insurance) | policy-alignment memo | "did not approve" definition excludes 41/50 "encouraged by 3rd party" claims ($185,980); answer leaked in sample totals row | 59 items | N | Y | — | V |
| 52 | GDPval | row 66 5f6c57dd (finance mgr) | branch profitability package | "Corporate" pseudo-branch with costs; Orders ($) vs Orders (Units) | 137 structural items | Y | Y | — | V |
| 53 | GDPval | row 75 6dcae3f5 (residency) | 2-SD flag list | first-name identity collisions across yearly sheets; SD type/≤ vs < unstated (8 variants → 8 sets ≠ rubric); expert gold also wrong | 45 items | P | Y (ambiguous) | — | V |
| 54 | GDPval | row 28 dfb4e0cd (compliance) | fast/slow spending set | day-count convention at 75% boundary (24 awards at 0.7493 vs 0.75); gold (76) contradicts rubric (53) | exact set ±0.1pp | P | Y (ambiguous) | gold≠rubric | V |
| 55 | GDPval | row 69 4520f882 (finance mgr) | weekly payroll | compounding order of premiums unstated; rubric rates +$1.00 vs document | ~45 numeric items | N | Y (defect) | key corrupted | V |
| 56 | GDPval | row 0 83d10b06 (auditor) | sample-size workbook | Q3 column before Q2; entity aliases exist only in rubric; div-by-zero rows; set cover | 38 items | P | P (defect) | — | V |
| 57 | GDPval | row 1 7b08cd4d (accountant) | tour P&L | "Other Costs" split into Tour vs Travel with no rule in files | 59 items | P | Y (ambiguous) | — | V |
| 58 | GDPval | row 4 ee09d943 (accountant) | month-end close | referenced AP_TB-1.xlsx missing; trailing-minus TB; duplicate account numbers across companies | 44 items | N | P (defect) | — | V |
| 59 | GDPval | row 3 43dc9778 (tax preparer) | Form 1040 | excess SS withholding, Medicare/NIIT, QBI on 199A dividends, educator cap — IRS rules not in files | 67 exact lines | N | Y (outside knowledge) | — | V |
| 60 | GDPval | row 9 c44e9b62 (admin mgr) | FTE reduction | per-box 10% reductions + attrition; org chart visual-only | 44 items | Y | P | — | V |
| 61 | GDPval | row 18 24d1e93f (buyer) | NPV vendor comparison | volume exactly 100,000 vs "<100000/>100000" tiers; unit of price unstated | 52 structural | Y | Y (ambiguous) | — | V |
| 62 | GDPval | row 29 4c18ebae (bank investigator) | SAR | "suspicious amount" = sum of all transactions (undefined); "NY " vs "NY"; name drift | 50 items | P | Y (undefined target) | — | V |
| 63 | GDPval | row 67 b39a5aa7 (finance mgr) | orchestra cost model | overscale "includes principal pay" (double count); capped payroll tax front-loaded by quarter | 32 structural | P | Y | — | V |
| 64 | GDPval | row 78 40a8c4b1 (med-ed admin) | 52-week schedule | ~25 priority rules in 3 files; rotation typo silently fixed by rubric | 72 constraint checks | P | Y | — | V |
| 65 | GDPval | row 136 f841ddcf (order clerk) | shipments recap | literal "slipped" definition (5 vs 16 orders) | 59 items | Y | N | solvable | V |
| 66 | GDPval | row 137 47ef842d (order clerk) | weeks of supply | prompt names non-existent column; leading zeros; rubric counts +1 vs file | exact | P | P (defect) | — | V |
| 67 | GDPval | row 138 1137e2bb (order clerk) | price/case-pack audit | case-pack rule applies only to CASE UoM (22 vs 10 errors) | exact | Y | N | solvable | V |
| 68 | GDPval | row 144 c657103b (financial advisor) | Roth conversion model | prompt says RMD at 72; rubric requires 75 (current law via link) | items | P | Y (outside rule) | — | V |
| 69 | GDPval | row 154 a079d38f (producer) | shoot estimate | excluded rate-card items score −5; mandatory 10% fee only in rate card; kit double count | items | P | P | — | V |
| 70 | GDPval | row 157 / 163 / 191 / 212 / 213 / 214 / 47 | trackers, PIP, sales, incident, location, manifest, summary | registry gaps; rolling-90-day vs calendar quarter; gendered fit names; totals rows in data; broken referential integrity; band gaps | various | P | P | mostly solvable or defective | V |
| 71 | APEX-Accounting | world 9 task 5 | variances + GL balances | interested Controller memo asserts reclass "IS NOT AN ERROR… auditors agreed" + balances; per-employee workpaper falsifies ($4,450.55 vs $2,197.80); noise items | 4 numeric ±$0.01 (judge) | N | Y | dev mean criteria ~62–68%; strict Pass@1 ≤9.5% (paper) | V |
| 72 | APEX-Accounting | world 9 task 17 | group totals + JEs | prior allocation "passed all balance checks"; per-employee recompute reveals $2,197.80 and $9.15 entries | 6 numeric | N | Y | — | V |
| 73 | APEX-Accounting | world 9 task 23 | collections by class/month + flags | informal memo adds a January-deposited check to December and removes a returned check; flips >15% flags and top mover; "no more than five" guard | 16 criteria | N | Y | — | V |
| 74 | APEX-Accounting | world 9 task 13 | AR reconciliation judgments | staff draft with wrong variances is the anchor; misclassified write-off | 12 criteria | P | Y | — | V |
| 75 | APEX-Accounting | world 9 task 14 | ledger vs GL + JE | 1300 nets to $0 hiding $45k Dr/Cr; addendum makes $23,500 reimbursable; IOLTA-paid costs excluded; "no more than three" relabels | 24 criteria | P | Y | — | V |
| 76 | APEX-Accounting | world 9 task 4 / 6 / 7 / 26 / 30 | single JE; payroll JEs; WIP roll-forward; comp true-up; AR aging % | suppress already-posted entries ("no more than one JE"); equity vs expense; status-memo write-downs | 2–many criteria | P | Y | — | V |
| 77 | Harvey LAB | banking-finance/compare-compliance-certificate… | deviation memo | 2nd Amendment: lesser-of $7.5M or 15% cap binds ($500k overstatement); covenant 3.75x→4.00x; omitted principal payment; expired add-back | 49 binary criteria, 2 LLM judges, all-pass | N | Y | Fable 5.1 6.67% / GPT-6 Astra 5.42% (benchmark-level) | V |
| 78 | Harvey LAB | corporate-ma/draft-distribution-waterfall-memorandum | waterfall memo | GP model compounds quarterly vs LPA annual 8%; side letter changes one LP's catch-up; fee offset steps; DISTRACTOR: don't deduct placement fee | 52 criteria | N | Y | — | V |
| 79 | Harvey LAB | corporate-ma/identify-earnout-issues | issues memo | ineligible customer revenue; non-recurring revenue; unconsented rev-rec change; oral side deal barred; Company's own notice 3 days late (leap year); per-period cap | 42 criteria | N | Y | — | V |
| 80 | Harvey LAB | corporate-ma/compare-closing-documents… | closing checklist | Delaware certificate 9 business days vs 5 allowed (flag) vs Texas 6 vs 10 (must NOT flag) | 40 criteria | N | Y | — | V |
| 81 | Harvey LAB | corporate-ma/extract-post-closing-obligations | obligations list | SPA body beats Exhibit D (Apr 15 vs 14); checklist 45 vs SPA 30 days; underlying contract 45-day consent shorter than SPA 60 | 63 criteria | N | Y | — | V |
| 82 | Harvey LAB | corporate-ma/analyze-qoe-reconciliation | memo + 3 workbooks | DTL in pass-through asset purchase; inventory write-down reversal add-back disallowed; lease-expiry rent normalisation | 131 criteria | N | Y | conjunction-driven | V |
| 83 | APEX-Agents 1.1 | world223-smn-05 (3M buyback) | 4 values | template defaults (1% fee, 15% tender premium) vs rubric's gross-proceeds-at-market — unstated | judge per criterion | N | Y (ambiguous) | Fable 5.1 0/4 on complete task | V |
| 84 | APEX-Agents 1.1 | world-221-hy-05 / world-129-cy-task-3 | value bridge / pricing % | model default account (2024 vs TTM); missing tier-segment mapping table; midpoint convention | judge | N | Y (partly ambiguous) | Fable 0.6 / 0.0 | V |
| 85 | TaxCalcBench TY25 | ty25-us-003 | Form 8606 lines | two conflicting IRA value sets (di vs ui), no governing rule | exact per line | N | Y (ambiguous) | 0/30 across top models | V |
| 86 | TaxCalcBench | ty24 single-senior-blind / eic-non-dependent-child | lines | contradictory flags vs amounts; questionable key | exact | N | — (unfair) | 0/17 | V |
| 87 | TaxCalcBench TY25 | ny-002/ny-009/va-002/us-006 | lines | ±$1 table/rounding conventions cascade | exact | N | N if table in files | 0–1/30 | V |
| 88 | TaxCalcBench TY25 | va-005/006/007; ca-007/008; il-008 | lines | joint-1099 allocation convention; negative taxable income; long tail of obscure CA items; checkbox only in PDF | exact | N | P | 0/30 | V |
| 89 | Vals Finance Agent | public 50 (inventory turnover, Snap converts, TJX guidance, TSM) | answers | average vs ending inventory; include OTM converts; both ends of guidance; FX conversion then multi-year averages | LLM judge rubric | N | Y (definitional) | Opus 4.7 64.4% | V |
| 90 | LAB-Bench | ProtocolQA / CloningScenarios | MCQ | one seeded protocol error (0.085 vs 0.85 g); reverse-complement and off-by-few distractors | exact letter | N | P | — | V |
| 91 | AccountingBench (Penrose) | monthly closes (not public) | ledger | models plug unrelated transactions to force reconciliation; error cascades | vs ground truth | N | Y | >15% drift later months | V-secondary |
| 92 | Toolathlon | excel-market-research | growth workbook | methodology prose cell: N/A if ANY component missing (no renormalising: 31/100 cells differ); external-link formula cached value; mixed units | cell-wise exact | P (in workbook) | Y | Claude-4.5-Sonnet failed | V |
| 93 | Toolathlon | excel-data-transformation | long-format xlsx | duplicate "Accumulated Growth(%)" block with out-of-window 2025 months; label normalisation; fraction→% | shape (198,6) + values | P | Y | Claude 204 rows → fail | V |
| 94 | Toolathlon | course-schedule | exam_schedule.jsonl | English exemption (score ≥70) in course PDF note; "Scored 88" buried in memory.json; section naming mismatch | normalized equality | N | Y | Claude enrolled in English → fail | V |
| 95 | Toolathlon | detect-revised-terms | CSV of revised clauses | unchanged carry-overs, number-only citations, court mis-citation, one-to-many mappings, small substantive change | multiset (key changed 5→9 rows) | P | Y | Claude 17 rows → fail | V |
| 96 | Toolathlon | travel-expense-reimbursement | DB rows + emails | per-night / per-date caps, no offset; level tiers; 1.5× meals only; form errors | exact row set | P | Y | Claude flagged 13 vs 8 → fail | V |
| 97 | Toolathlon | ab-testing | record.csv | "overall" defined as mean of per-scenario rates (73.840) vs pooled (73.904) | ±0.1pp (±0.05 then) | Y (definition) | Y | Claude used pooled → fail | V |
| 98 | Toolathlon | sales-accounting / reimbursement-form-filler / flagged-transactions / payable-invoice-checker | ledger rows / form / anomalies / DB | "last week and week before" date decoy; "Only taxi" filter; per-client 3σ; 1,000 interference invoices | exact | P | N | Claude passed all four | V |
| 99 | Toolathlon | gdp-cr5-analysis / academic-warning | CR5 table / list | outside region knowledge; MCP paging copy errors | exact | — | N (unfair / tooling) | Claude 80/100; 23/30 | V |
| 100 | GAIA (validation) | 32102e3e / 4d0aa727 / 54612da3 / 076c8171 | title / odds / count / type | category encoded only by section-header rows; Whyte notation (outside knowledge) | exact | N | P | test set 0.93 (saturated) | V |
| 101 | GAIA (validation) | bfcd99e1 | count (17) | corrupted "JavaSFortranript" contains qualifying token (substring → 19); "3+" misread → 11 | exact | N | Y | — | V |
| 102 | GAIA (validation) | 4d51c4bf / e9a2c537 | counts | inverted inference (odd = east-facing, awning at back → sunset); "Checked Out" + "Overdue" both off-shelf | exact | N | Y | — | V |
| 103 | DSBench (ModelOff) | 00000001 chip-off-the-old-block | MCQ / values | inclusive cross-year shutdown; April–March prices to calendar quarters; step inflation; cap/floor inflating differently; supplier merit order flips in 2024; XNPV; adjacent-integer options | exact | P (brief) | Y | best agent 34% (2024) | V |
| 104 | DSBench (ModelOff) | 00000013 late-again / 00000043 find-that-error | timetable answers / audit | messy cell codes, one band breaks pattern; progressive fix cascade | exact | N | Y | 13–17% on 2014–17 sets | V |
| 105 | Finch | #119 / #116 / #25 | count / counts / memo | continuation rows ('NEW','Phase 2') → 85 vs 114 vs 98; exact ties belong to "neither"; totals reconcile but sign inconsistent | GPT judge | N | Y | GPT-5.1 Pro ~40%; Sonnet 4.5 ~27% | V |
| 106 | QRData | ucla_textbooks_f18 / causal items | SE / letter | unstated paired design (1.63 vs 9.89); method-dependent causal answers (unfair) | ±3% / exact | N | Y / unfair | — | V |
| 107 | MCPMark | legal_document/dispute_review / solution_tracing | counts / proposer list | bracket placeholders vs [name:content] comments; carried-over comments; first proposer vs authoritative voice; grader accepts "5 or 6" | exact | P | Y | GPT-5.2 57.5 vs Opus 4.5 42.3 (legacy) | V |
| 108 | OfficeQA Pro | UID0013 / UID0005 | numbers | revised figures in later bulletins must govern; fiscal vs calendar; nominal vs real | exact 0.0% | P | Y | Fable 5 45.6 / GPT-5.6 Sol 33.3 (V2, CC vs Codex) | V |
| 109 | InfiAgent-DABench | ids 7, 30, 39 | metrics | every step specified (seed, split, encoding) | format tokens | Y | N | mechanical | V |
| 110 | SpreadsheetBench Verified | 43436 | I2:K6 values | golden uses header label ("by end of May") contradicting instruction's definition of "open" | cell compare | P | Y (defect) | survived "Verified" | V |
| 111 | SpreadsheetBench Verified | 52575 | y/blank flags | recurring week key in non-contiguous runs; global vs run-local grouping; case "Sick day" vs "Sick Day" | case-sensitive cells | P | P | — | V |
| 112 | SpreadsheetBench Verified | 22-47 | F2:H10 | late sentence overrides 6-sentence procedure; stacked blocks with repeated headers | cells | P (decoy procedure) | Y | — | V |
| 113 | SpreadsheetBench Verified | 13-1 | LISTS!A3:D32 | text vs real dates across blocks; group/sort/TOTAL | type-exact cells | P | N | — | V |
| 114 | SpreadsheetBench Verified | 59129 / 9448 / 146-49 / 547-18 / 32902 / 50683 cluster | various | boundary-day strict >; sparse year header with ' '; reversed example orientation; '*' wildcard + sheet-name case; tier example covers only band 1; worked answers in prompt | cells | P/Y | mostly N | top 99.25% (saturated) | V |
| 115 | SpreadsheetBench 2 | Debugging family 01 (01_01–01_10) | repaired 14-sheet LBO/M&A workbook | row-consistent seeded errors: 11-of-12-month average, INDEX offset from MATCH, prior-year MATCH, sign flips, 4 vs 0.04, running-total double count, rounded hardcodes | all modification cells + ≥99.8% regression cells | N | Y | Debugging: Opus 4.6 12% / GPT-5.2 8% | V |
| 116 | SpreadsheetBench 2 | Debugging family 02 (DCF/WACC/merger) | repaired workbook | 4 bad cells among thousands; extra "fixes" break regression check | as above | N | Y | — | V |
| 117 | SpreadsheetBench 2 | Financial_Model 01_01 | 82 formula cells | implicit period count (RRI 5); mirror adjacent-row conventions; cascades | as above | P | Y | FM: 34 / 33 | V |
| 118 | SpreadsheetBench 2 | Template 01_02 (OID bond) | B2:I36 | sign convention for deferred tax unstated | as above | N | Y (ambiguous) | Template 52.6 / 35.1 | V |
| 119 | SheetCopilot | PricingTable #6 / EntireShippingCosts #1 / ExpenseReport #2 | sheet edits | stated boundary dates; min-charge floor; SUMIF | property match vs refs | Y | N | easy | V |
| 120 | OfficeBench | 1-5/2, 2-48/0, 1-2/0, 3-8/0 | files | 365-day year in leap year (unstated); "nap" counts as sleep (unstated); grader checks only keywords/one cell | keyword / cell | P | — (defective) | GPT-4o 47% (2024) | V |
| 121 | OSWorld | 035f41ba | gross-profit sheet | empty decoy columns must stay empty; whole-sheet equality punishes fill-in | DataFrame.equals | P | Y | calc 95.7% (Fable 5) | V |
| 122 | OSWorld | 357ef137 / 4e6fcf72 / d681960f / bc2b57f3 | sheets | h:mm × 24; TODAY() at grade time (non-deterministic); approx VLOOKUP; spec in reminder.docx | sheet compare | P | mostly N | — | V |
| 123 | OSWorld | 881deb30 (multi_apps) | pass-rate table from 9 PDFs | institution rename HKIEd→EdUHK; decoy grf/ folder; hidden discipline filter in gold | sheet_data | P | Y (hidden filter = defect) | multi_apps 79.3 (Fable 5) | V |
| 124 | BlueFin | interrogation 0122 | short answers | what-if through 13-sheet model with self-latching summary formulas → stale cached values | 1% tolerance | N | Y | Opus 4.7 44.4 / GPT-5.5 50.0 | V / V-summ |
| 125 | BlueFin | manipulation 2aac5a2a / 95d3752e / e13c5e9d | new tabs | long specs; Swiss vs non-Swiss pricing exception; perturbation checks | 34–47 judged items | Y | Y | perturbation 15–37% | V-summ |
| 126 | τ2-bench airline | 39 | set of cancellations | 7 reservations filtered by flown legs, 24h, business, insurance+reason | DB hash + NL assertions | N | Y | 0/4 Opus 4.5 & GPT-5.2; residual label issue (MSJ4OA) | V |
| 127 | τ2-bench airline | 44 | cancellations + upgrades | ">4h flights" vs per-leg/per-trip incl. layover; healthy user can't cancel insured economy | DB + judge | N | Y | 0/4 both; GPT cancelled S61CZX 2/4 | V |
| 128 | τ2-bench airline | 14 / 23 | bookings + payment split | per-reservation caps (≤1 certificate, ≤1 card, ≤3 gift cards) force splitting a trip into 3 reservations | DB + COMMUNICATE | N | Y | 23: 0/4 both (in fix list) | V |
| 129 | τ2-bench airline | 7 / 3 / 10 / 12 / 33 | actions / number | upgrade-then-cancel composition; user claims Gold, record Silver; cabin all-or-nothing | DB + COMMUNICATE | N | Y | 7: Opus 1/4, GPT 0/4 | V |
| 130 | τ2-bench retail | 41 / 109 / 71 / 72 | address + item changes | modifying items locks the order → change address first although user mentions items first | DB hash | N | Y | 0.19 (older models) | V |
| 131 | τ2-bench retail | 82 / 112 / 38 | return / modification / cancel | refund only to original method; scope overreach to sibling order; fallback ladder ending in cancel | DB hash | N | Y | 112: GPT-5.2 & Opus 4.5 0/4 | V |
| 132 | τ2 banking_knowledge | task_075 | account opened | "BOTH out-of-network AND foreign ATM fee apply"; travel-branded Purple ($45) vs Green Fee-Free ($0); age exclusions | DB | N | Y | Fable 5 0/4, Opus 5 1/4, GPT-5.6-sol 4/4 | V |
| 133 | τ2 banking_knowledge | task_054 | ordered actions | dispute/replacement auto-blocks CLI → CLI first, capped at 50% | DB | N | Y | Fable/Opus/GPT 0/4 | V |
| 134 | τ2 banking_knowledge | task_060 / 062 | ordered actions | savings needs checking ≥14 days; business checking needs no CLOSED accounts | DB | N | Y | GPT closed first 4/4 (060); Claude correct order but voided (closure_reason) | V |
| 135 | τ2 banking_knowledge | task_070 / 071 | product choice | expired vs active promotion; as-of date in header | DB | N | Y | ~1/4 each model | V |
| 136 | τ2 banking_knowledge | task_059 / 058 | product choice | small-deposit tier flip ($5k: EcoCard bonus − $50 fee < Green 4.45%); $20k variant easy | DB | N | Y | 059: Fable 0/4; 058: 4/4 all | V |
| 137 | τ2 banking_knowledge | task_102 / 085 / 046 | eligibility outcomes | requester claims contradict record (referral date, tier, amounts, "no disputes") | DB | N | Y | 0–2/4 | V |
| 138 | τ2 banking_knowledge | task_074 / 097 / 043–047 | fee refunds / interest / closures | 22-error recompute (breadth); non-stacking bonuses (period convention unstated); skipped mandated reads | DB incl. read allowlist | N | Y / P | 074 Fable 4/4; 097 0 all; 043–047 Fable 0/4 | V |
| 139 | τ2 banking_knowledge | 053/060–067 voids | — | free-text closure_reason hashed into DB; product-name variants | DB hash | — | — (void) | 35 trials matched gold writes, scored 0 | V |
| 140 | TheAgentCompany | finance-substantial-presence-test | day count | key 303; models and recomputation 306 | substring | P | — (key defect) | all runs 1/2 | V |
| 141 | TheAgentCompany | finance-invoice-matching | flagged_payments.xlsx | grader flags every "(Partial)" payment (hidden convention); exact order | .equals | N | — (hidden convention) | 0/5 most runs | V |
| 142 | TheAgentCompany | finance-budget-variance / finance-check-attendance-payroll | flags / payroll | >10% AND >$5k; "round up total not each day" (procedure leaked); ungraded "seasonal" instruction | exact list | Y | N | mostly solved | V |
| 143 | TheAgentCompany | hr-check-attendance-multiple-days-department / finance-revenue-reconciliation / hr-salary-analysis | xlsx / report | column/filename/path contradictions between task and grader | checkpoints | — | — (defects) | 0–2/4 | V |
| 144 | TheAgentCompany | admin-make-spreadsheet / admin-employee-info-reconciliation / admin-get-best-vendor-quote / finance-apply-tax-credit | sheets / forms | PDF layout (line break); name typo Chan→Chen; requirements via chat; Form 6765 fields needing asked-for facts | checkpoints | P | P | 0–3/8 typical | V |
| 145 | WorkArena++ | expense_management (L2/L3) | deletions | precedence ladder with tie fall-through; hashtag-sharing distractors | API state | L2 Y / L3 N | Y | L3 0% (2024 models) | V |
| 146 | WorkArena++ | change-request scheduling / maximize investment return / infeasible dash-do | schedule / value / refusal | inverted ordinal codes (impact 1 = highest); knapsack; fabricated field must be declared infeasible | validators / substring | P | Y | infeasible 0% | V |
| 147 | CRMArena | handle_time / transfer_count | agent ID | scoped definitions: first-assigned agent only; transferred cases excluded; "Winter 2021" = Dec–Feb | exact | P | Y | — | V |
| 148 | CRMArena-Pro | policy_violation / quote_approval / invalid_config / lead_qualification | KB id or None | answer priors: quote_approval constant ID in 80% of rows; policy_violation 77% None | exact | P | — (validity problem) | Gemini-2.5-pro 54.1 B2B | V |
| 149 | DABstep | D1: 1273 / 1274 / 1281 / 1287 (20 tasks) | average fee (6 dp) | `is_credit: null` rules apply to credit ("null… applies to all possible values"); Opus matches True only | rounded-to-fewest-decimals, 1e-4 | N | Y | Opus 5 fail 0.80–1.00; GPT-5.6-sol 0.15 | V |
| 150 | DABstep | D2: 1810 / 1763 / 1789 / 1681 / 1753 (40 tasks) | fee-ID list | per-merchant monthly volume and fraud-by-volume buckets, capture_delay ">5", intracountry; skipping stats → superset | order-insensitive list | N | Y | Opus 0.30–0.40; GPT 0.00 | V |
| 151 | DABstep | D3: easy 18 / 19 | scheme / % | fraud defined by volume in §7 (TransactPlus) vs count (SwiftCharge) | exact | N | Y | both bare CLIs fail 18 | V |
| 152 | DABstep | D4: 70 / 71 | yes/no/N/A | "excessive fraud threshold" undefined → Not Applicable | exact | N | Y | 0/2 both CLIs | V |
| 153 | DABstep | D5: 2644 / 2691 / 2761 (30 tasks) | scheme:fee | "steer traffic" = reprice whole population under each scheme | exact | N | Y | pool 0.85; Opus 0.97–1.00; GPT 0.53 | V |
| 154 | DABstep | D6: 2562 / 2566 (20 tasks) | merchant list (may be empty) | "affected" = change set (those who lose the fee); one gold empty | list | N | Y | GPT 0.65; Opus 0.15 | V |
| 155 | DABstep | D7 / D8: 1305; 1433–1442 | avg fee / MCC | empty list `[]` = wildcard (not in manual; maintainer-confirmed); manual's illustrative MCC example wrong (5812) | exact | N | P (partly ambiguous) | D8 0.30–0.40 both | V |
| 156 | DABstep | D9 / D10: 1712 / 1738 / 1748; 2536 / 2550 / 2529 (65 tasks) | totals / deltas | multiple matching rules are summed by gold; manual never says rules stack (Opus first-match prior vs GPT sum prior) | exact | N | Y (unstated convention) | Opus 0.90–1.00; GPT 0.00; pool ~0.80 | V |
| 157 | DABstep | D11 / D12 / D13: 1450…; dev 2697; 2520 / 2480 / 2397 | ACI / ACI:fee / delta | inconsistent convention; irreproducible 13.57; ±0.01–0.02 gold drift | lenient scorer | N | — (defects) | pool 0.85–1.00 | V |
| 158 | DABstep | D14: easy 49 | option | highest fraud *rate* (BE) vs largest absolute fraud (NL) | exact | N | P | both CLIs answered NL | V |
| 159 | OfficeQA Pro | UID0013 / UID0005 / Pro sample / blog example | numbers / triple | which line item; fiscal vs calendar; latest revision governs; CPI source; "Treat 1990 as year 0" pinned | 0.0% rel. error | P (conventions pinned) | Y (revision, FY/CY) | Pro: Fable 5 60.9, GPT-5.6 Sol 60.2 | V |
| 160 | OfficeQA (paper) | revision / FY-vs-CY / near-miss line-item cases | numbers | June vs September 2010 revised bulletin; FY values pulled for 8 years; "Total Public Debt Securities" vs "Total interest-bearing" | exact | P | Y | 0%→5% tolerance +11–17 pts | V |
| 161 | DAB (DataAgentBench) | GITHUB_REPOS q1 / PANCANCER q1 / PATENTS q1 / agnews q3 | proportion / codes / CPC list / average | hidden key conventions (3 READMEs vs ~100; ICD-O codes); natural-language dates; over-listing accepted; re-embedded categories | lenient validators | N | P (ambiguous) | Gemini-3-Pro 38% pass@1 (paper); tuned Opus 5 0.95 | V |
| 162 | FinanceBench | 06655 / 00585 / 01911 / 04784 / 00216 / 01865 | ratios / answers | formula given (mechanical); wrong-sign gold; dubious zero coverage; FY ends Jan 31 and pp vs % change; unstated quick-ratio definition; organic vs total column tie | judge / exact | Y/P | P | label errors dominate residual | V |
| 163 | TAT-QA / FinQA / BizBench | eb787966; CME/2017 p40; AON/2015 p96; SEC-NUM | numbers | scale from header and sign; wrong "annualized return" gold (1.6% vs 15.8%); program/answer mismatch; "87" vs 87 million | EM/F1 | Y | N | mostly label noise | V |

Rows that list several IDs are tight clusters of near-identical tasks. The 163 rows cover about 250 individual tasks.

## Appendix B: primary sources

**Terminal-Bench**
- Tasks: github.com/harbor-framework/terminal-bench-2; github.com/laude-institute/terminal-bench (`original-tasks/`).
- Paper: arXiv 2601.11868.
- 2.1 changes: tbench.ai/news/terminal-bench-2-1, and PR harbor-framework/terminal-bench-2#53.
- Z.AI fixes: huggingface.co/datasets/zai-org/terminal-bench-2-verified.
- Trajectories: huggingface.co/datasets/yoonholee/terminalbench-trajectories.

**Harbor Index:** github.com/harbor-framework/harbor-index (tasks/*/README.md, ADAPTATIONS.md, leaderboard/submissions).

**GDPval**
- Data: huggingface.co/datasets/openai/gdpval.
- Paper: arXiv 2510.04374.
- Artificial Analysis board: artificialanalysis.ai/evaluations/gdpval-aa.

**DABstep:** huggingface.co/datasets/adyen/DABstep (`data/task_scores`, `scorer.py` in the leaderboard Space).

**OfficeQA**
- Repo: github.com/databricks/officeqa (README and figures).
- Paper: arXiv 2603.08655.
- Blog: databricks.com/blog/introducing-officeqa-pro-v2-new-benchmark-enterprise-grounded-reasoning.

**DAB:** github.com/ucbepic/DataAgentBench; arXiv 2603.20576.

**Finance QA sets:** huggingface.co/datasets/PatronusAI/financebench; TAT-QA; FinQA; BizBench.

**Spreadsheet and office**
- SpreadsheetBench: github.com/RUCKBReasoning/SpreadsheetBench and SpreadsheetBench-2; spreadsheetbench.github.io leaderboard JSON; arXiv 2606.29955.
- github.com/BraveGroup/SheetCopilot; github.com/zlwang-cs/OfficeBench.
- OSWorld: github.com/xlang-ai/OSWorld (evaluation_examples); osworld-verified results file.
- BlueFin: huggingface.co/datasets/Longitude-Labs/bluefin-release; arXiv 2605.30907.

**Policy and enterprise agents**
- τ2: github.com/sierra-research/tau2-bench (domains, CHANGELOG, leaderboard submissions); trajectories in S3 bucket `sierra-tau-bench-public`.
- τ-bench arXiv 2406.12045; τ-Knowledge arXiv 2603.04370; τ³ fixes taubench.com/blog/tau3-task-fixes.html.
- TheAgentCompany: github.com/TheAgentCompany/TheAgentCompany and /experiments; arXiv 2412.14161.
- WorkArena: github.com/ServiceNow/WorkArena; arXiv 2407.05291.
- CRMArena: huggingface.co/datasets/Salesforce/CRMArena and /CRMArenaPro; arXiv 2505.18878.

**Legal, finance and accounting**
- APEX-Accounting: huggingface.co/datasets/mercor/apex-accounting; arXiv 2607.27189.
- APEX-Agents: arXiv 2601.14242; mercor.com/apex/apex-agents-leaderboard; github.com/human-vc/mercor-c06-pilot.
- Harvey LAB: github.com/harveyai/harvey-labs; vals.ai/benchmarks/hlab.
- TaxCalcBench: github.com/column-tax/tax-calc-bench; arXiv 2507.16126.
- Vals Finance Agent: github.com/vals-ai/finance-agent.
- LAB-Bench: huggingface.co/datasets/futurehouse/lab-bench.

**Tool-use and data-analysis benchmarks**
- Toolathlon: github.com/hkust-nlp/toolathlon (tasks/finalpool); toolathlon-traj.xyz; arXiv 2510.25726.
- GAIA validation mirror: smolagents/GAIA-annotated.
- DSBench: huggingface.co/datasets/liqiang888/DSBench.
- Finch: huggingface.co/datasets/FinWorkBench/Finch.
- MCPMark: github.com/eval-sys/mcpmark.
- QRData: github.com/xxxiaol/QRData.
- InfiAgent-DABench.

**Other main-author sources**
- Spider 2.0: github.com/xlang-ai/Spider2 (spider2-lite, resource/documents, evaluation_suite/gold); spider2-sql.github.io.
- KramaBench: github.com/mitdbg/KramaBench (workload/*.json).
- SkillsBench: github.com/benchflow-ai/skillsbench.

## Appendix C: what is verified and what is not

**Verified by execution in this research:**
- TB2 per-task solve rates and the defect cross-tabulation, computed from the 52,104-trial dump.
- The two sparql-university readings, run with rdflib on the visible and held-out graphs.
- The financial-document-processor twin documents, from PDF text plus trajectory outputs.
- The db-wal-recovery and count-dataset-tokens failure narratives, from trajectory text.
- τ2-banking per-task rewards for Fable 5 and GPT-5.6-sol, and Fable's Purple-Account choice on task_075, from public trajectories.
- Two Harvey LAB criteria texts.
- The APEX-Accounting task-5 memo and rubric.
- The OfficeQA Pro V2 per-model bars, read from the README figure.
- Spider2 multi-gold files.
- KramaBench's inconsistent boundary wording.
- The research agents' own recomputations, as tagged in their sections: the DABstep fee engine, the GDPval convention variants, the Toolathlon key recomputations, the SB2 error diffs.

**Not verified:**
- Any transfer of these traps to Fable 5.1 in Claude Code or GPT-6 Astra in Codex at high effort with no limits.
- The [V-summ] and [V-secondary] leaderboard numbers.
- Per-trap failure rates on Harvey LAB and APEX. These are not published; only aggregate rates exist.

**Untested:** the §8 skeletons and the "one trap per model family" stacking hypothesis.

