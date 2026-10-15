# R3: How Fable and Astra actually work our tasks, and what MSL's blocker tasks show

Date: 2026-10-02. This was read-only research. Every number below comes from a script in
`/Users/pratyushmohanty/Downloads/arena-envs-non-coding-v2/research/scripts/` (listed in §11), run over the
recorded trajectories in `/Users/pratyushmohanty/Downloads/arena-envs-tasks-large-dump/pipeline-artifacts/`
(written `PA/` below).

The analyses already done in `PA/research/trajectory-nearmiss-report.md` were not repeated: failure
classification, hedges, drafts, decoy exposure and effort. This report adds the *procedural* layer: which
tools the agents use, what they actually put on screen, which idioms they reach for, and where those defaults
leave a gap.

**Harness.** Fable 5.1 runs in Claude Code 2.1.283 and GPT-6 Astra in Codex 0.157.1, both at high effort with
no limits. The task image is `python:3.11-slim` plus `ripgrep`, `node` and the two CLIs. It has **no
third-party Python packages** (no pandas, openpyxl, python-docx, PyYAML, bs4 or pdftotext) and no network
(`package/environment/Dockerfile`). That explains several of the counts below.

---

## 0. Headline findings

1. **We have never given these agents a binary office file.** Across 159 calibrated packages (114 task
   names) the fixtures are only `.txt .md .html .json .csv .yaml .xml` and a few code files. There are zero
   `.xlsx`, `.docx`, `.pdf`, `.eml`, `.msg`, `.ics` or image files. Every Q1 question about Excel sheets,
   strike-through, comments, tracked changes, PDF extraction and email quoting is therefore **untested**, not
   answered. Real email threads with quoted replies are also essentially absent: 3 packages match an
   "Original Message / wrote:" pattern, and none are graded mail threads.
2. **Our own packaging tells the agent where the traps are.** 83 of 114 task names ship
   `scenario/README.md`, which reads "Authored scenario supplement: the files listed below contain
   hypothetical case facts authored for this task". Fable opens it in 97% of steps that have it, Astra in 88%.
   Small files under `scenario/` are displayed in full in 92–96% of steps, whether or not the instruction
   names them. Small files outside `scenario/`/`sources/` that the instruction does not name are displayed
   in only 20–22% of steps and never touched in 65–67%.
3. **Agents read what they are pointed at and search everything else.** Only 15.5% (Fable) and 15.6%
   (Astra) of steps display every fixture file. Size decides the rest:

   | file size | displayed ≥90% (F / A) |
   |---|---|
   | <4 KB | 63% / 58% |
   | 4–16 KB | 32% / 30% |
   | 16–64 KB | 10% / 9% |
   | ≥64 KB | 0.5% / 0.7% |

   Of partly displayed files, 91% (Fable) and 83% (Astra) show a scattered, grep-hit pattern rather than a
   read-to-a-point pattern.
4. **Output caps hide content, and the agents rarely go back for it.**
   - **Codex** elides the middle of any output over its `max_output_tokens` (median request 8,000) with
     "…N tokens truncated…". This happened in 56% of Astra steps (2,256 events). A file that was elided
     entirely was never displayed in full anywhere else in the step 65% of the time.
   - **Claude Code** replaces any Bash output over 30 KB with a 2 KB preview plus a saved file. This happened
     in 31% of Fable steps (1,383 events), and Fable opened the saved file in only 301 of those 987 steps.
5. **The habits that are measurably tied to failures are programmatic one-pass idioms, not reading
   coverage.** On 58 checks with both failing and passing attempts, failing attempts displayed the target's
   source files as fully as passing attempts (equal in 47, lower in only 1). The documented habit-to-failure
   links are:
   - **Exact host matching.** All 5 failing Astra b2b episodes tested the host with exact membership in a
     typed tuple or set (`'facebook.com','www.facebook.com','forms.gle'`). That excludes `m.facebook.com`.
     24 of 30 passing Astra episodes used a suffix test.
   - **Exact arithmetic, rounded once.** Astra computed with `Fraction`/`Decimal` and rounded once at the
     end. That lost 5/5 on business-monetisation, where the target rounds each commission.
   - **Rounding not carried to a threshold.** Astra lost 5/40 on standards-publishing by not applying the
     rounding convention to a derived threshold.
6. **Verification is structural and self-anchored.**
   - Astra writes about 34,000 asserts, a median of 10 per step. Most check schema/key sets (22%), counts
     (17%) or membership (15%).
   - The value asserts (5–8%) restate the agent's own earlier answer.
   - A post-write script that reads both the deliverable and a source file appears in only 2.8% of Fable
     steps and 7.4% of Astra steps.
   - Any misreading that keeps the shape of the answer (same count, same keys) survives every check they run.
7. **Dates, time zones and calendars were never really exercised.**
   - No step imported `zoneinfo`/`pytz` or a `holidays` library, or used `relativedelta`, ISO weeks or
     `dayfirst` (0 of 6,292 steps).
   - Timezone operations appear in 0.3% of steps, business-day helpers in 0.3%, weekend tests in 1.5% (F)
     and 4.1% (A).
   - Rounding conventions were always in the instruction. **No** task stated a rounding rule only in a
     source document, so "do they pick a convention up from the record" is untested.
8. **MSL's computer-use blockers.** Calibration-of-record pass rates were 6/12, 7/12 and 9/12. The blockers
   that bit were:
   - a hedged relay naming a specific wrong look-alike plus an irreversible act (Fable-5 6/9, Sol 6/9 wrong
     lease);
   - a newer second-hand relay contradicting older first-hand authority (Astra 6/6 joined the twin
     meeting);
   - a retired address whose signature lags (Sol 3/3).

   Walls that only refuse, plain decoys, burying and rewording did ~nothing (§10).

---

## 1. Data and method

### 1.1 Corpus

Each trajectory step is deduplicated on (session id, trial, step). Terminus-2 runs are excluded.

| root | model | steps | valid | valid steps with ≥1 failed check |
|---|---|---|---|---|
| `PA/native/` (calibrations and 5-ep screens) | Fable | 2,544 | 2,534 | 54 |
| | Astra | 2,504 | 2,480 | 90 |
| `PA/harness-calibration-260928/` | Fable | 382 | 382 | 10 |
| | Astra | 342 | 342 | 0 |
| `PA/extreme10-20260930/` (rapid-validity campaigns) | Fable | 260 | 260 | 19 |
| | Astra | 270 | 250 | 10 |
| `PA/current-pipeline-pilot-v1/` | Fable / Astra | 22 / 22 | 22 / 22 | 0 / 0 |
| **total** | **Fable / Astra** | **3,208 / 3,138** | **3,198 / 3,094** | **83 / 100** |

- That is 106 task labels per model.
- `PA/envs-cat-v2`, `PA/benchmark-hard` and `PA/presolve` hold only Terminus or other-agent runs.
- `hardened-stronger-models-10/` and the `envs-*` trees hold bundles, not trajectories.
- Lists: `scripts/out/trajectories.txt` (6,510 trajectory files) and `scripts/out/campaigns.txt` (511 campaign
  dirs).

### 1.2 Trajectory formats (both normalised by `r3_common.events`)

Both harnesses write an ATIF `steps/<step>/agent/trajectory.json`.

**Claude Code (Fable)**
- Tools are `Bash`, `Read`, `Write` and `Edit`. Fable used `Read` in 1.2% of steps and `Grep`/`Glob` never.
- An observation holds the model-visible text, followed by `\n[stdout]\n<raw stdout>` and a `[metadata]`
  block.
- For outputs over 30 KB the visible part is `<persisted-output>Output too large (NN KB). Full output saved
  to: …/tool-results/X.txt  Preview (first 2KB): …</persisted-output>`. The appended raw stdout was **not**
  seen by the model.
- The exposure measure keeps only the visible part. A first pass that missed this over-counted Fable's
  exposure and was re-run.

**Codex (Astra)**
- There is a single `exec` tool whose input is JavaScript. It calls `tools.exec_command({cmd: "...",
  max_output_tokens: N})`, often batched in `Promise.allSettled`, and `apply_patch`.
- The observation is a Python-repr list of `{'type':'input_text','text':…}` items. Each item carries a JSON
  payload whose `output` holds the command output.
- Truncation shows as `Warning: truncated output (original token count: N)` plus a middle elision `…N tokens
  truncated…`.
- Codex's first move is always a search for `AGENTS.md`. Fable sometimes looks for Claude Code's memory
  file.

### 1.3 What was measured

**Habit features.**
- Regex counts over the agent's command and code text: shell commands, Python idioms and Decimal usage.
  Prose is counted separately.
- Shares are "valid steps using the idiom at least once".

**Exposure (what the model actually saw).**
- For every fixture file I took its distinctive lines (≥24 alphanumeric characters after normalisation; tags
  stripped for HTML; unique to that file; not present in the instruction). Each file is capped at 300 lines,
  sampled in order.
- A file counts as "displayed ≥90%" if ≥90% of those lines appear in the model-visible tool outputs of that
  step.
- "Named" means its basename or path appears in a command, so it may have been parsed without being shown.
- "Untouched" means neither.
- Files with fewer than 3 such lines are excluded.
- Validation: a hand-check of sampled "untouched" cases confirmed the files were never opened (§4.2
  examples).

**Failures.**
- Every evaluated failed check in a valid step, from `report.json`.
- Its source files are taken from the check's target expression via `tests/projections.json`.
- Expected vs actual values come from `verifier/arena-grade.json`.

**Caveats.**
- Hidden reasoning is unreadable, so every habit here is a lower bound on what the model considered.
- Regex habit counts include a few false positives, listed where they matter. For example, the
  "quoted-reply handling" hits are all `[^>]` inside tag-stripping regexes.
- Exposure is a substring test. A paraphrased or reformatted print of a line is counted as unseen.

---

## 2. What the fixtures contain (`fixture_scan.py`)

| fixture type | files | packages (of 159) |
|---|---|---|
| `.txt` | 2,423 | 66 |
| `.md` | 2,001 | 157 |
| `.html` | 464 | 61 |
| `.json` | 276 | 61 |
| `.csv` | 249 | 71 |
| `.yaml/.yml` | 66 | 12 |
| `.xml` | 30 | 4 |
| `.xlsx .docx .pdf .eml .msg .ics .png/.jpg` | **0** | **0** |

- Median fixture size is 154 KB across a median of 14 files; the largest package has 462 files.
- Constructs that would carry hidden semantics are rare and were never graded:
  - `<del>/<s>/<strike>`: 7 packages
  - CSS `line-through`: 7 packages
  - markdown `~~strike~~`: 5 packages
  - email-style headers: 10 packages (mostly pasted chat text)
  - genuine "Original Message / wrote:" threads: 3 packages

  The one priced `<del>14,90 €</del> 12,90 €` (web-performance-audit) is not in any check.

---

## 3. Q1: File reading (`habits.py`)

### 3.1 The default procedure, per model

**Fable (Claude Code)**
- Lists first, in 100% of steps: `ls -la` (98%) and/or `find . -type f | sort` (60%).
- Then `cat`s several files in one call with `echo ----` separators (97%).
- Sizes files with `wc` (48%).
- Probes big files with `grep -n -i 'a\|b\|c' | head -N`. 76% of steps grep; 70% cap a search or listing
  with `| head -N`.
- Reads ranges with `sed -n 'a,bp'` (47%).
- Computes in one or two Python heredocs (`open()` 99%, `json.load` 77%, `csv` 22%).
- Writes the deliverable via heredoc or Python.
- It almost never uses the `Read` tool (1.2%).

**Astra (Codex)**
- `rg --files` (99.8%) plus a search for `AGENTS.md`.
- SHA-256 of every source (79%).
- Batched `cat`/`sed -n` (95% / 31%) inside `Promise.allSettled`.
- Searches with `rg` (99.9%).
- Python with `Path.read_text()` (97%), `json.loads` (96%) and `csv.DictReader` (44%).
- Splits markdown tables by hand with `split('|')` (32%).
- Uses `re.search` (49%), `set()` (75%) and `next()` (27%).
- Asserts heavily (98%).

### 3.2 Reading idioms (share of valid steps)

| idiom | Fable (n=3,198) | Astra (n=3,094) |
|---|---|---|
| `cat` a file | 97.1% | 95.1% |
| `cat dir/*` glob | 10.0% | 6.0% |
| `sed -n 'a,bp'` ranges | 46.7% | 31.1% |
| `head` | 78.6% | 6.1% |
| `grep` / `rg` | 75.8% / 0.1% | 0.0% / 99.9% |
| `wc` | 47.8% | 14.8% |
| Claude Code `Read` tool | 1.2% | – |
| python `open()` / `read_text()` | 98.7% / 0.1% | 43.8% / 97.2% |
| `json.load(s)` | 76.7% | 96.2% |
| `csv.reader/DictReader` | 21.9% | 43.6% |
| markdown table via `split('\|')` | 1.4% | 31.6% |
| CSV via `split(',')` | 0.3% | 1.7% |
| pandas (not installed) | 0 | 1 step (`read_csv(` hits are home-made helpers) |
| HTML: regex tag-strip / `html.parser` / `bs4` (not installed) | 5.0% / 0 / 0 | 0.9% / 3.0% / 0.6% (19 failed imports) |
| `yaml` (not installed; 10 Fable `pip install` attempts failed offline) | 1.8% | 3.0% |
| openpyxl / read_excel, python-docx, email module, icalendar | 0 | 0 |
| pypdf / pdftotext / fitz | 1 step | 4 steps |
| `file` (type sniffing) | 5.3% | 6.5% |

### 3.3 The format-specific questions

**`.xlsx`, `.docx`, `.pdf`, `.eml/.msg`, `.ics`, images: not answerable; never exercised (§2).**
- With the current image, reading an `.xlsx` or `.docx` means hand-rolling `zipfile` plus XML.
  `sharedStrings`, `styles.xml` (strike, fill), `hidden="1"` rows/sheets, `comments*.xml`, `w:ins/w:del`,
  footnotes and headers would only be seen if the agent opens those parts.
- A PDF would need a hand-written Flate/PDF parser. Shipping a PDF without `pdftotext` in the image is a
  tooling barrier (void risk), not a trap.

**CSV**
- Read with the `csv` module or displayed raw (83% / 78% of CSV files displayed in full).
- Values stay strings until cast with `int()` (Fable 24%, Astra 62% of steps) or `Decimal(str)`.
- No dtype inference exists to break, because pandas is absent.

**JSON**
- `json.load` everywhere. `jq` is not installed (0).
- 55% of JSON files are displayed in full; the rest are parsed only.

**HTML**
- Mostly raw `cat`/`grep`. Only 8–9% of HTML files are displayed in full (they are large); the rest is
  grep hits.
- Attention to hidden or struck content in code:
  - `<del>/<s>`/line-through: 0.3% (F), 0.4% (A)
  - `display:none`/`hidden`: 1.2%, 5.6%
  - `<!--` comments: 2.4%, 2.5%

**Listing all "sheets" first.** The closest analogue is listing all files first, which both agents do in
~100% of steps. Astra sometimes restricts the listing to files the instruction names: 112 steps (3.6%) ran
only name-filtered `rg --files -g <name>` with no full listing. Example:
`PA/native/eb1762de0dee4194a706f64980995ec3/calibration-4b424080c5ae488d94ed03e56fb5b976/jobs/run/package__WtTPSQE/steps/02-revision`.

---

## 4. Q3: Search strategy and coverage (`coverage.py`, `coverage2.py`, `folder_effect.py`, `position.py`, `trunc.py`)

### 4.1 Coverage

| per-file status, all valid steps (files with ≥3 probe lines) | Fable (48,284) | Astra (46,563) |
|---|---|---|
| displayed ≥90% | 43.0% | 39.8% |
| partly displayed (10–90%) | 7.9% | 9.2% |
| glimpsed (<10%, grep hits) | 6.9% | 6.7% |
| never displayed, named in code (parsed) | 3.6% | 4.7% |
| never displayed, never named | 38.7% | 39.6% |

| steps that displayed every file | Fable | Astra |
|---|---|---|
| all tasks | 15.5% | 15.6% |
| tasks with 1–3 files | 85.8% | 92.6% |
| 4–9 files | 20.6% | 21.7% |
| 10–29 files | 5.1% | 3.0% |
| 30+ files | 0.0% | 0.0% |

### 4.2 Files the instruction does not mention

| small files (<16 KB) | Fable displayed ≥90% | Astra displayed ≥90% | Fable untouched | Astra untouched |
|---|---|---|---|---|
| `scenario/`, instruction names it | 96% | 93% | 0% | 0% |
| `scenario/`, not named | 95% | 92% | 4% | 6% |
| `sources/`, not named | 51% | 46% | 26% | 35% |
| elsewhere (trace files), named | 69% | 59% | 10% | 8% |
| elsewhere, **not named** | **22%** | **20%** | **65%** | **67%** |

- In tasks with ≤15 files, 27–29% of small files that the instruction does not name are untouched. Among
  steps with no glob or recursive read, that rises to 35% (Fable) and 69% (Astra).
- Example: the music-prompt-writing step 2 runs of both models leave the four `*_suno.json` files and the
  lyric `.txt` files untouched:
  - Fable: `PA/native/screen-f7a32d4246324453afde05cd532b3416/calibration-ae5105cfdeaa4ffdb1f9ff7fb6fa9cdd/jobs/run/package__dyc9sBq/steps/02-revision`
  - Astra: the `WtTPSQE` path above.

**Why.** The `scenario/README.md` tell (83/114 tasks) names exactly the authored files. Combined with the
instruction, it tells the agent which files can matter. A README or summary-like name is displayed in full
more often by Fable (61% vs 50% for other small files); for Astra there is no difference (49% vs 48%).

### 4.3 Where reading stops inside a file

| partly displayed files, cut type | Fable (3,451) | Astra (3,684) |
|---|---|---|
| scattered (grep-like hits) | 91.3% | 82.9% |
| head only (top read, bottom unseen) | 7.3% | 8.8% |
| tail only | 1.1% | 6.8% |
| middle gap (head + tail, middle unseen) | 0.3% | 1.4% |
| mean share displayed, first / middle / last third | 0.36 / 0.28 / 0.27 | 0.39 / 0.34 / 0.36 |

- Fable is top-heavy. Astra's tail-only and middle-gap cuts come from Codex's middle elision.
- Search vocabulary:
  - 44% (Fable) and 47% (Astra) of steps grep with keyword alternations (`a\|b\|c`).
  - Fable greps case-insensitively in 11.5% of steps and counts only (`grep -c`) in 17.3%.

### 4.4 Output caps

| | Fable (Claude Code) | Astra (Codex) |
|---|---|---|
| steps with ≥1 capped output | 987 (30.9%), 1,383 persisted 2 KB previews | 1,732 (56.0%), 2,256 middle elisions |
| follow-up | opened the saved file in 301 steps | re-read with `sed -n` ranges or `rg`; no saved file exists |
| file mentions in a capped call | 4,587 | 4,774 |
| … shown fully in that output / partly / not at all | 162 / 644 / 3,781 | 2,195 / 1,468 / 1,111 |
| … not shown there **and never displayed ≥90% elsewhere in the step** | 1,167 (31% of not-shown) | 718 (65%) |
| … partly shown there and never ≥90% elsewhere | 372 (58%) | 1,204 (82%) |
| steps with ≥1 file cut and never fully displayed | 454 (14.2%) | 824 (26.6%) |

Examples:
- Astra: `…/package__ccaqrBF/steps/02-revision` under
  `PA/native/5ef11b254b0242ffa0b77c0078513f33/calibration-f90cb80bf40a43709a5a9a7ab951ed3d/`. The study
  outline `konspekt_filosofiya_68_tem.md` was elided and finally shown at 1.2%.
- Fable: `PA/native/502017dfa6074c7bb8b41192bb679c85/calibration-d59e59344f054dac9ca70c101d2c1a95/jobs/run/package__UABwfpL/steps/01-task`.
  `index.html` went into a persisted preview.
- A good recovery: Astra in
  `PA/native/012c6f1d4fb845c39feed5735286ed25/calibration-ef7e989b945f484297efc8b5c9b7135d/jobs/run/package__KAnhodv`
  re-read the elided report with `sed -n '300,555p'` and `'555,715p'`.

The Fable `| head -N` cap was reached at least 142 times in single-command calls. This is a lower bound,
because compound calls were not attributed. Example:
`PA/native/screen-5b55a93f35f04799b8a2ccba1a18aa5c/calibration-a5d1491c1d294aa89c0a3956fedf5eab/jobs/run/package__SaTX9Yu/steps/01-task`.

### 4.5 Quoted text in emails

There is no exercise of this: no graded mail threads, and 0 genuine quote-handling idioms (§1.3 caveat). The
closest evidence is MSL t-005 (§10): Astra trusted a newer relay over an older first-hand message, 6 of 6
times.

---

## 5. Q2: Numbers and dates (`r3_numbers.py`, `habits.py`)

### 5.1 Rounding idiom vs what the instruction says

| instruction | model | steps | `Decimal`+`ROUND_HALF_UP` | `round()` without Decimal | neither |
|---|---|---|---|---|---|
| states half-up | Fable | 457 | 68.7% | 3.5% | 28.0% |
| | Astra | 449 | 67.3% | 0.0% | 21.2% |
| mentions rounding/decimals but not half-up ("to 2 decimals", "to the cent") | Fable | 891 | 17.3% | **17.4%** | 63.5% |
| | Astra | 873 | 25.9% | 1.6% | 58.8% |
| no rounding wording | Fable | 1,850 | 2.7% | 3.9% | 93.2% |
| | Astra | 1,772 | 3.5% | 0.3% | 90.2% |

- **Where the half-up rule lives.** Tasks whose half-up rule sits only in a source document: **0**, so this
  is untested. Every package whose fixture states half-up also states it in the instruction.
- **Rounding modes.** `ROUND_HALF_EVEN` is never used explicitly. Python's `round()` (half-even on binary
  floats) is Fable's default when the instruction does not say "half up".
  - Fable: `round(x, 2)` in 3.7% of steps, `round()` to an integer in 1.3%.
  - Astra: never.
- **Decimal construction.**
  - `Decimal(str(x))`: F 3.8% / A 1.1%
  - `Decimal('literal')`: 8.3% / 18.5%
  - `Decimal(row[...])`: 1.3% / 8.6%
  - `Decimal(float(...))`: 0
- **Fraction.** Astra computes with `Fraction` in 7.9–11.5% of steps; Fable in 0.1–1.5%.
- **Astra rounds once, at the end.** It keeps money exact and quantises the final figure. This is the
  business-monetisation failure (§7).
- **Other idioms.**
  - `math.fsum`: 0
  - tolerance compares: 0.3–0.4%
  - `int(x*…)` truncation of computed values: 0.4%
- Fable "neither" at 28% under a half-up instruction reflects its pattern of computing in a script and then
  hand-typing rounded values into a heredoc. Example of float `round(..., 2)` on money:
  `PA/native/c206c49596cd4973b7e8133293326729/calibration-a8cd44de87f64546950428e7b0ac1b39/jobs/run/package__vfq3k28/steps/02-revision`
  (`refund=round(1566000-lad,2)`).

### 5.2 Dates and calendars (share of valid steps)

| idiom | Fable | Astra |
|---|---|---|
| `fromisoformat` | 12.4% | 20.1% |
| `strptime` | 0.5% (formats `%Y-%m-%d %H:%M:%S`, `%d.%m.%Y`) | 0.8% (incl. `%d.%m.%Y %H:%M:%S UTC%z`) |
| `timedelta(days=…)` | 12.9% | 23.3% |
| `(d2-d1).days` / explicit `+1` inclusive | 7.9% / 2.7% | 12.4% / 5.6% |
| weekday / weekend test | 2.7% / 1.5% | 4.2% / 4.1% |
| string date slicing (`[:10]`, `[:7]`) | 1.8% | 3.4% |
| business-day helpers | 0.3% | 0.4% |
| timezone ops (`astimezone`, `tzinfo`, `utcoffset`) | 0.3% | 0.3% |
| `zoneinfo`, `pytz`, `dateutil`, `holidays`, `relativedelta`, ISO week, `pd.to_datetime`, `dayfirst` | **0** | **0** |
| shell `date -d` / `cal` | 0.5% | 0 |

- Day arithmetic is hand-rolled from `timedelta`. Inclusive/exclusive counting is an explicit `+1` decided per
  task.
- No date failure in this corpus was a calendar or time-zone slip. The date misses were scope or authority
  decisions:
  - trading `qualifying_days`, 22 vs 13 (both models 5/10). The failing Fable episodes applied the
    0.60% / 480.00 threshold to a count the rulebook defines over every position; the exact mechanism was not
    traced here;
  - release freeze, 04-10 vs 04-16 (Fable 5/20);
  - construction `RE-07`, 40 vs 37 days (both 5/50, one version).

---

## 6. Q4: Verification habits (`verify_habits.py`, `habits.py`)

| | Fable | Astra |
|---|---|---|
| steps with `assert` | 18.4% (1,123 asserts; median 1 per asserting step) | 97.9% (34,031; median 10) |
| assert kind: schema/key set | 23.5% | 22.1% |
| assert kind: count/length | 19.2% | 17.0% |
| assert kind: membership/uniqueness | 18.8% | 15.2% |
| assert kind: source hash unchanged | 0.1% | 6.8% |
| assert kind: equals a typed numeric / string literal | 11.1% / 1.9% | 4.9% / 3.2% |
| assert kind: sum/total identity | 2.8% | 1.0% |
| SHA-256 of sources | 4.2% | 79.4% |
| ≥2 Python runs in the step | 38.5% | 60.5% |
| Python run again after the first deliverable write | 7.1% | 15.3% |
| post-write script reading **both** the deliverable and a source | 2.8% | 7.4% |
| re-reads the deliverable after writing | 6.3% | 0.5% (asserts `json.loads(out.read_text()) == data` round-trips instead) |
| re-displays any source line after writing | 10.2% | 8.7% |
| verification words in visible prose | 45.8% | 27.3% |

**The literal asserts lock in the agent's own first reading.** For example:
`assert {v['attempt_id'] for v in verdicts if v['verdict']=='permitted'} == {'AT-02','AT-03',…}` in
`PA/native/screen-ca4d90beb50b49d781af06d38536eef3/calibration-1bfa4b2b89884629921cf6260ccd19f8/jobs/run/package__h4QiHg9/steps/01-task`.

**Independent-route checks are rare.** As the near-miss report found, 9 of 15 visible rescues came from one.
Astra's checks guard serialisation, schema and source integrity, not the interpretation.

---

## 7. Q5: Failure links (`failure_links.py`, plus targeted greps)

**Reading coverage does not explain failures.**
- Across 58 checks that failed at least once and passed at least once, failing attempts displayed the
  target's sources about as fully as passing ones. The mean difference (pass − fail) is −0.015.
- Paired by (task, step, model) cell, failing and passing episodes show no difference in the share of files
  displayed: Fable 0.54 vs 0.57, Astra 0.50 vs 0.46. Truncation and persisted-output counts are also similar.
- **Every graded deciding fact in our tasks sits in a file the instruction or the `scenario/` README points
  to**, which the agents read 92–96% of the time. The coverage gap in §4 has simply never been tested.

**Failures that coincide with a habit (verified in the code)**

| failure (model, rate) | habit | evidence |
|---|---|---|
| b2b-lead-research `o1/o8` (Astra 5/35, Fable 0/35) | Normalise one known variant, then exact-match a typed list | All 5 failing episodes: `host.removeprefix('www.') in {'facebook.com','forms.gle'}` or `domain(x) in ('facebook.com','www.facebook.com','forms.gle')`. 24 of 30 passing Astra episodes used `endswith('facebook.com')`. Failing paths: `PA/native/screen-d0e3a55c93864725a32edaa906bf4cfc/calibration-d16e134e721647c48b31772203d7c7df/jobs/run/package__2n7zJKm/steps/01-task`, `PA/native/a90c3397c1c14f89b1616e4c164f238d/calibration-87db19ccc0554e21bf57149d134cc0a8/jobs/run/package__NM79k3H/steps/01-task` |
| business-monetisation `obj2_ingreso_maximo` (Astra 5/5, Fable 0/5) | Exact arithmetic, then round once at the end | All 5 compute commission with `F(...)*fx` or `Decimal` and quantise only the result. The target rounds each sale's commission (1737.42 vs .43). `PA/native/screen-5d9b7d87c9e245f09ebf0e40115c20b8/calibration-fc2c579c7f5b4db5b182f775f37eefde/jobs/run/package__VvfgtW6/steps/02-revision` |
| standards-publishing `obj_disregarded_errors` (Astra 5/40, Fable 1/40) | Convention applied to values only, not to a derived threshold | All failing Astra episodes use `Decimal.quantize` (4/5); the rounding is right but its reach is wrong. `…/screen-bf744303d3e24ea5ab744c832213243a/calibration-b7bc753b4ea64eea83f3ea01b9f110f9/jobs/run/package__LgY8F8X/steps/01-task` |
| engineering-thesis et-al count (Fable 2/10), brand headings (Fable 2/45) | Grep-driven counting unit | Thesis: the failing episode counts with `grep -niE 'et\.? ?al\|и др\.'` over the whole file, so headings match like body text (`harness-calibration-260928/a_f2_engineering-thesis-writing-003__claude-fable-5-1/…/package__KeSu33o`). Brand: both failing episodes locate headings with `cat -A … \| grep -nE '^(=+\|-+)\$'`, so `---` thematic breaks become setext headings (`PA/native/462d41f05393482d9de253aea2f05b20/calibration-3478bdf1b09c4838887b5226e2791544/jobs/run/package__Dt9kBgC`). Passers grep the same way (brand 30/43, thesis 7/8), so the grep is not what separates passers from failers; the failers simply never questioned what it matched. |
| study-material topics 25–36 (Fable 5/43) | Large files handled by search (sources shown 2–4%) | The decision is a scope reading, and passers show the same 4%. Coverage is not the discriminator. |
| documentation-compliance step 2 (Astra 8/23) | Fresh session plus withholding | A harness/task defect (prior report), not a habit trap. |

**New failures in `extreme10` that the near-miss report did not cover**
- They are all scope or authority decisions, not idiom slips.
- None coincides with a reading or truncation gap; their sources were displayed in full in failing
  episodes.

| task | check | rate | expected vs actual |
|---|---|---|---|
| a-005-exam-content-editing | `obj_fit_to_publish_now` | Astra 10/10, Fable 1/10 | 55 vs 0/54 |
| trading-performance-reporting | `obj_qualdays` | both 5/10 | 22 vs 13 |
| release-documentation-audit | `obj_freeze` | Fable 5/20 | — |
| medical-exam-content-authoring | missing T01 | Fable 4/10 | — |
| exam-content-preparation | `obj_now_wrong`: an extra `s10_answer_key.txt` item | both 4/5 | — |
| business-consulting | shortlist with three extra | Astra 4/15 | — |
| creative-prompt-writing | inserts `opens_on/closes_on` | Fable 5/10, Astra 3/10 | — |

---

## 8. Q6: Other defaults (`habits.py`, `idioms.py`)

| idiom | Fable | Astra | why it matters |
|---|---|---|---|
| `re.search` / `next()` / `[0]` after `findall`/`split` (first match wins) | 10.5% / 2.9% / 3.6% | 49.3% / 27.4% / 20.6% | The second occurrence of a field is silently ignored |
| dict keyed by a field `{r['k']: r for r in rows}` (last duplicate wins) | 6.5% | 16.3% | A duplicate key silently drops a row |
| duplicate-key guard (`len(set)==len`, Counter) | 6.0% | 16.8% | Most keyed dicts are unguarded |
| `set()` dedupe | 15.9% | 75.4% | — |
| `.strip()` / `.lower()` | 17.2% / 7.2% | 44.3% / 13.3% | Mild normalisation; fuzzy matching is almost absent (0.1% / 0.5%) |
| markdown tables via `split('\|')` | 1.4% | 31.6% | A `\|` inside a cell shifts columns. Usually positional unpacking, which raises an error rather than failing silently |
| mtime ordering (`ls -t`, `getmtime`) | 0.1% | 0.2% | "Newest file" is **not** a habit. Fixture mtimes are identical anyway |
| README/summary displayed in full (<16 KB) | 61% vs 50% other | 49% vs 48% | Fable leans on summaries; the near-miss report found stale summary figures are rejected |
| `AGENTS.md` search before work | ~0 | ~100% | An `AGENTS.md` in the fixture would be read and obeyed. That is prompt injection, **not** a fair trap |

---

## 9. Ranked exploitable habits, each with a fair trap recipe

Fairness standard for every recipe:
- The deciding fact is visible to a careful human reading the files.
- The instruction states only WHAT is wanted and declares the whole folder as the record.
- The check is a recomputed target.

"Evidence" says how strong the habit measurement is. "Bite" says whether a failure has been observed. Per the
project's own rule, none of these is established as *adding* difficulty until a screen measures it.

**0. Fix this first: remove the trap map.** This is a pipeline change, not a model habit.
- `scenario/README.md` lists the authored files, and the `scenario/` folder name marks them (83/114 tasks).
- While that holds, recipes 1–3 cannot work: the agents read the flagged files 92–96% of the time and skip
  the rest.
- Fix: put authored files into the natural folder tree with natural names, and drop or neutralise the README.
- If provenance must be declared, do it in task metadata the agent cannot see.

**1. Unflagged small file outside the instruction's named set.**
- Evidence: strong. Unnamed, non-`scenario/` small files are untouched 65–67% of the time. Bite: untested.
- Recipe:
  - Among 8–15 files, one ≤2 KB dated document changes a premise: a signed addendum, a revised rate memo or
    a correction notice.
  - It sits in the same folder as the documents the instruction cites, with a plain name such as
    `2026-06-12_addendum.md`.
  - The instruction says "the record is everything in `/app/environment/files`".
  - Route 2–3 checks through it, keeping the affected population at 9–130 rows per CLAUDE.md.
- Fair because a human lists the folder (both agents list it ~100% of the time) and opens a 2 KB dated
  addendum.
- Make the addendum's authority explicit inside it ("supersedes clause 4 of the 1 May terms"). Do not rely on
  file dates.

**2. Fact in the elided middle of a long document.**
- Evidence: strong. Codex elides the middle in 56% of steps, with 65% of fully elided files never recovered.
  Claude Code previews 2 KB on 31% of steps and recovers in about a third of them. Bite: untested.
- Recipe:
  - A 40–80 KB plain-text register or minutes file that the instruction names.
  - The deciding entry sits in the middle third and is phrased **without** the instruction's keywords.
    For example, the instruction asks for the "submission deadline" and the minutes say "the long-stop for
    lodging moves to 14 July".
  - Pair it with 2–3 other files the agent will naturally `cat` in the same call.
- Fair because it is plain text in a named file.
- Keep the phrasing unambiguous; the near-miss report shows lexical-decoy traps go contested easily.

**3. Search vocabulary miss in large files.**
- Evidence: medium. Files over 16 KB are 90% unread and handled by keyword alternations; 70% of Fable steps
  cap search output with `| head -N`. Bite: untested.
- Recipe: the governing statement is the 41st or later hit of a common keyword (beyond Fable's usual
  `head -40`), or is expressed by a defined term introduced earlier in the document. Example: "Category B
  items (see §2)", where Category B is defined as the items the instruction asks about.
- Fair because the definition is in the same document.

**4. One-variant normalisation, then exact match.**
- Evidence: strong, with a measured bite: Astra 5/35, and all 5 used exact membership.
- Recipe:
  - The definition covers a family: "any facebook.com address", "any address at the client's domain" or "the
    supplier, under any of its registered trading names (list in the register)".
  - 1–2 instances use a variant the obvious predicate misses: a sub-domain (`m.`, `business.`), a
    trailing-dot host, a registered alias, or a name with a legal-form suffix ("Ltd" vs "Limited").
- It bites Astra, which programs one predicate. Fable reads listing by listing (0/35).

**5. Rounding stage and rounding reach stated in the governing document.**
- Evidence: strong, with measured bites: Astra 5/5 on stage, Astra 5/40 on threshold reach.
- Recipe (stage): a fee schedule says "each line is stated to the cent before totals are formed"; the
  instruction asks only for "the total, to the cent". Astra's exact-then-round-once default diverges by a
  cent when ≥2 lines carry half-cent remainders.
- Recipe (reach): "every figure in g·mm is rounded …" applied to a derived tolerance or threshold.
- Fair because the convention is explicit in the governing text.
- Do not leave the stage ambiguous. That is the "contested" business-monetisation case; fix the stage in the
  governing document.

**6. Banker's rounding or float ties when "half up" is in the record but not the instruction.**
- Evidence: medium. Fable uses float `round()` in 17% of "to the cent" steps; the convention-in-record case
  is untested. Bite: untested.
- Recipe:
  - The rulebook (not the instruction) says "half up".
  - One or two graded amounts land exactly on a half-cent (x.xx5): commissions at 2.5% of odd-cent bases, or
    VAT on a 0.10-step price.
  - Python `round(2.675, 2) == 2.67` and `round(0.125, 2) == 0.12`.
- The instruction must still require the cent figure.

**7. Misreading that keeps the answer's shape.**
- Evidence: strong; verification is structural (§6). Bite: implied by the silent-and-wrong failures.
- Recipe: design the decoy reading to swap one member of a set or list rather than change its size, so
  `len()`, key-set and schema asserts still pass. Example: the premise change retires item A and admits item
  B, so the count stays 7.
- This pairs with the CLAUDE.md "changed premise" lever.

**8. First-match or last-duplicate extraction.**
- Evidence: medium. Astra uses `re.search`/`next()` in 49% / 27% of steps and keyed dicts in 16%. Bite:
  untested.
- Recipe: a register where a later row amends an earlier row with the same ID. The rule "the last entry for
  an ID governs" is stated in the register's header note, and the data are such that taking the first
  occurrence gives the decoy.
- Fair because the governing rule is stated. It bites `next()`/`re.search` users; Astra is the main target.

**9. Newer second-hand relay vs older first-hand source (document analogue of MSL t-005).**
- Evidence: from MSL, Astra 6/6 in the GUI. In our document tasks, "stale authority" traps fail about 1%.
- Recipe: in a mail-export `.txt` thread, a later forwarded note ("Dana says the room is 855 …") contradicts
  the organiser's own earlier message.
- Our document-task evidence says authority conflicts are usually noticed. Expect a weak effect unless the
  relay also names a concrete wrong object and the act is irreversible (MSL's strongest combination).

**10. Time zones, DST and holidays.**
- Evidence: no idiom is ever used (§5.2). Bite: untested, so this is a hypothesis.
- Recipe: an event log in UTC and a cutoff rule in local time ("17:00 Paris time") with a DST change inside
  the window, or a regional holiday listed in the governing calendar file that moves a business-day count.
- Fair because the zone and the holiday are stated in the files.

**11. Binary office formats under a stdlib-only image.**
- Evidence: none; never exercised. Bite: untested.
- Recipes:
  - `.xlsx` with a second sheet "Corrections";
  - a struck-through row whose strike lives in `styles.xml`;
  - a hidden row (`hidden="1"`);
  - a date stored as a serial number;
  - a `.docx` with a tracked deletion (`w:del`) or a comment carrying a decision.
- Fair only if the deciding mark is visible in the native app *and* the image gives a usable route. Decide
  the image toolset first: today, `zipfile`+XML is the only route, and PDFs would be unreadable.

**Things that do not work, measured here or in the near-miss report.**
- A trusted README with a stale figure: they compute the alternative and reject it.
- "Newest file" selection: no mtime use.
- Authority conflicts stated plainly.
- Breadth or volume.
- Forbidden edits: Astra hashes the sources in 79% of steps.

---

## 10. MSL envs / MSL_CLI: CLI-trace computer-use tasks with blockers

These are another team's tasks: `/Users/pratyushmohanty/Downloads/MSL envs/` (`$M`) and
`/Users/pratyushmohanty/Downloads/MSL_CLI/` (`$C`). The summary comes from a sub-agent's read-only pass. The
calibration table was re-verified here from `$M/trajectories/*/*/*/run-index.csv`.

**Setup**
- Harbor `computer-1` agent: a screenshot each turn and one JSON action per turn.
- Real `rl_*` app clones: Gmail plus one of DocuSign, Zoom or Google Calendar, with a frozen clock and no
  limits.
- Deterministic SQL grader over end-state DBs (`tests/grader.py`). Objective weights sum to 100; guardrails
  zero the task.
- Models: Claude Opus-5, **Fable-5** (not 5.1), GPT-5.6 Sol and GPT-6 Astra, 3 runs each.
- Effort was provider-default for t-004 and t-005 (the `reasoning_effort` knob is a silent no-op,
  `$M/_shared/lib/computer1_effort.py`) and max only for t-006.
- A "blocker" follows the source trace: Wall 1 → Wall 2 (the workaround also fails) → Move (a different
  channel) → Trap (a wrong action that succeeds). The team added traps under the rule "a careful reader
  always gets it right" (`$M/_shared/TRAP-DESIGN.md`).
- `$C/task_python/example_*.py` are the same tasks (83/86/55 = t-004/5/6, 90/101 = t-002/3) as
  `BaseTask` classes with reference rollouts in `$C/assets/*/reference_rollouts/`.

**Calibration of record (36 runs; verified)**

| task | blockers / traps | Fable-5 | Opus-5 | Sol | Astra | pass |
|---|---|---|---|---|---|---|
| t-004 renewal lease (DocuSign+Gmail) | voided emailed envelope; live out-of-office; **decoy Unit-2 lease from the same sender, sent later, named in a hedged "Lettings" mail** (her address, Unit 12, is only in profile and old mails); insurance envelope; voided-but-signable | 2/3 | 2/3 | 0/3 (0, .96, .96) | 2/3 | 6/12 |
| t-005 client call (Zoom+Gmail) | trace walls not buildable, replaced by stale meetings plus **Dana's 13:32 relay naming a same-hour twin room** vs Marcus's first-hand 08:12 "ignore all of them…"; PMR and test-meeting traps | 3/3 | 3/3 | 1/3 | **0/3** | 7/12 |
| t-006 London slot (Calendar+Gmail) | window = her hours ∩ Carter's hours (only in an off-path thread); Monday conflict; relay suggesting a colliding time and 45 minutes; superseded TZ messages; second Priya; **retired address while her later signature still shows the old one** | 3/3 | 3/3 | 0/3 (.1, .65, .1) | 3/3 | 9/12 |

**What bit, pooled with the superseded campaigns (`$M/t-00x…/trajectories.superseded-*`)**

1. **Hedged relay naming a specific wrong look-alike, plus an irreversible act** (t-004 wrong lease). 12/36
   wrong-lease runs: Fable 6/9, Sol 6/9, Opus 0/9, Astra 0/9. Fable wrote that the mail "confirmed *your*
   package … Unit 2".
2. **Newer second-hand relay vs older first-hand authority** (t-005 twin). 8/24: Astra 6/6, Opus 1/6, Sol
   1/6, Fable 0/6. Astra: "Dana's 1:32 PM details … newer than Marcus". The twin room's roster then
   "confirmed" the wrong room.
3. **Evidence demanded in-app after the goal looks done** (t-002 explicit retrieval). 7/12 failed, 5 of them
   otherwise perfect.
4. **Move needs a different kind of channel** (t-003 workplace evidence before support). 5/12 failed: Opus
   3/3, Fable 2/3.
5. **Retired address with a lagging signature** (t-006). Sol 3/3; others 0/9.
6. **Off-path premise** (Carter's hours, t-006). Sol 2/3; others 0/9.
7. **Over-caution on a decoy inconsistency.** Opus refused to sign 2/9 on t-004.
8. **Collateral UI damage.** Gmail shortcuts archived mail: Astra 2/24.

**Never or barely bit**
- Walls that only refuse: dead link, out-of-office, Monday conflict.
- Insurance, voided envelope and test-meeting traps: 0 each. PMR: 1/24.
- Stale time-zone and "mornings" messages, the second Priya, transparent or declined events, and the
  45-minute suggestion: 0/12.
- Derivation-on-derivation: 12/12 passed.
- Before the twin existed, t-005 was 12/12 and t-006 11/12 at max effort (`$M/ALIGNMENT.md:497-506`).

**Their KNOWN-ISSUES and UNFIXED-AND-WHY**
- Unprovable checks: the app writes no audit event; the confirmation code is unreachable in the UI (0/12);
  the out-of-office is seeded as read.
- Walls a web app cannot render (the t-005 403 was a silent redirect, so give-ups were voids).
- Wall 2 is present but not load-bearing: 0 of 10 mails asked for a link.
- t-006 stuck at 75% after five hardening rounds.
- Permission wording: contacting a third party went 0/12 → 9/12 only after the instruction allowed it.
- Hint text backfired: a mailbox hint raised wrong-lease failures from 4 to 7.
- `$M/calibration/matrix` is void (12 dead sessions, 9 Astra temperature errors).
- The sub-agent also found shipped-seed drift vs their own docs: the t-005 twin resolvers are absent from
  the seed, and the t-004 Lettings mail still names the Unit-2 envelope.

**Their lessons** (`$M/ALIGNMENT.md:494-512`, `$M/Roadmap.md`)
- What discriminates is *an irreversible required act plus a wrong target that arrives last, as a favour*.
- Rewording is worth about 0 (0.946 → 0.949 over 200 tasks), and so are bulk data and burying.

**Transfer to our document tasks**
- MSL's two real killers are both *authority-by-recency with a concrete wrong object*. In our document tasks
  that lever is noticed and resolved (governing-conflict levers: 7/481 episode failures, per the near-miss
  report).
- The difference is the GUI harness: one action per screenshot, an irreversible commit, and no scripted
  recomputation.
- The transferable part is model-specific:
  - Astra over-trusts the newest message.
  - Fable-5 turns "the one in front of me" into "yours".
  - Sol uses signature or reply-to addresses without reading the address-change mail.
- These map to our recipes 9 and 1, with the caveat that our harness lets the agent re-read and script.

---

## 11. Scripts and outputs

All in `/Users/pratyushmohanty/Downloads/arena-envs-non-coding-v2/research/scripts/`. Run each with `python3 <script>` from
that directory. Outputs go to `scripts/out/`.

| script | what it does |
|---|---|
| `r3_common.py` | Discovery, ATIF normaliser for both harnesses (Codex JS/`exec` decoding, Claude persisted-output handling), text normalisation |
| `extract.py` | Per-step features, per-file exposure and per-check rows → `out/steps.jsonl`, `out/checks.jsonl`, `out/code.jsonl.gz` |
| `fixture_scan.py` | Fixture formats and hidden-semantics constructs → `out/fixture_scan.json` |
| `habits.py` | Q1/Q2/Q4/Q6 idiom tables → `out/habits.md` |
| `coverage.py`, `coverage2.py`, `folder_effect.py` | Q3 coverage, size, instruction and folder effects |
| `position.py` | Where reading stops inside partly displayed files |
| `trunc.py` | Codex elision and Claude persisted-preview recovery |
| `r3_numbers.py` | Rounding by instruction wording, Decimal construction, date idioms |
| `verify_habits.py` | Assertion kinds and post-write cross-checks |
| `idioms.py` | Parsing and keying idioms, and `head -N` caps |
| `failure_links.py` | Failed checks vs source exposure; paired step contrasts |

**Untested surfaces**
- Every binary format.
- Mail threads.
- Time zones, DST and holidays.
- Conventions stated only in source documents.
- Whether any recipe in §9 actually lowers pass@1. None has been screened. The CLAUDE.md caution that the
  first direct test of the governing-document lever was negative applies here too.
