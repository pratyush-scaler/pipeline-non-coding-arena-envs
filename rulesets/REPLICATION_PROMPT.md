# Replication prompt — benchmark task-authoring system

Paste everything below the line into Claude Code (or work it by hand) from a directory
containing `ref_files/`. It reproduces the full analysis and build.

Findings are stated with their expected values. **If your numbers differ, stop and
reconcile before continuing** — the downstream design decisions all rest on them.

---

## Role and goal

You are setting up a system for authoring high-quality hard tasks for computer-use agent
benchmarks. You will read three reference corpora, extract what makes tasks
discriminative, build the grading tooling, and write the authoring playbook.

**Standing rule:** the reference corpora are for *learning how tasks are built and how
environments couple*. They are already-shipped tasks. Never fork, re-skin, renumber or
port one onto different data. Everything we author is new.

Do not use subagents or workflows. Do the reading yourself.

## Inputs

```
ref_files/
  BrowseComp Benchmark Tasks (1).xlsx        ~30 KB
  OS World v2 Benchmark Tasks (1).xlsx       ~107 KB
  BrowserComp_T02 (1).zip                    ~2.6 GB  (mostly screenshots)
```

Also useful if present: any prior shipped Harbor bundle, e.g.
`01_tax_practitioner-earliest-lapsing-cert-invoice_*/`.

---

## Phase 1 — Ingest the reference corpora

### 1a. Read the spreadsheets

`openpyxl` and `pandas` are **not** installed and `pip install` will prompt. Write a
stdlib XLSX reader instead — an `.xlsx` is a zip of XML:

```python
# scratch/xlsx.py
import sys, zipfile, re
from xml.etree import ElementTree as ET
NS = {'m':'http://schemas.openxmlformats.org/spreadsheetml/2006/main',
      'r':'http://schemas.openxmlformats.org/officeDocument/2006/relationships'}
def col_idx(ref):
    m = re.match(r'([A-Z]+)', ref); n = 0
    for ch in m.group(1): n = n*26 + ord(ch) - 64
    return n - 1
def read(path):
    z = zipfile.ZipFile(path); shared = []
    if 'xl/sharedStrings.xml' in z.namelist():
        for si in ET.fromstring(z.read('xl/sharedStrings.xml')).findall('m:si', NS):
            shared.append(''.join(t.text or '' for t in si.iter('{%s}t' % NS['m'])))
    wb = ET.fromstring(z.read('xl/workbook.xml'))
    relmap = {r.get('Id'): r.get('Target')
              for r in ET.fromstring(z.read('xl/_rels/workbook.xml.rels'))}
    out = {}
    for sh in wb.find('m:sheets', NS):
        tgt = relmap[sh.get('{%s}id' % NS['r'])]
        if not tgt.startswith('xl/'): tgt = 'xl/' + tgt.lstrip('/')
        rows = []
        for row in ET.fromstring(z.read(tgt)).iter('{%s}row' % NS['m']):
            cells = {}
            for c in row.findall('m:c', NS):
                v = c.find('m:v', NS); t = c.get('t'); val = ''
                if t == 'inlineStr':
                    isx = c.find('m:is', NS)
                    val = ''.join(x.text or '' for x in isx.iter('{%s}t' % NS['m'])) if isx is not None else ''
                elif v is not None:
                    val = shared[int(v.text)] if t == 's' else (v.text or '')
                if val: cells[col_idx(c.get('r'))] = val
            rows.append([cells.get(i, '') for i in range(max(cells)+1)] if cells else [])
        out[sh.get('name')] = rows
    return out
```

Dump every sheet of both workbooks. Expect:

- **BrowseComp**: sheets `Tasks` (10 tasks, T01–T10) and `Runs` (12 runs per task).
- **OSWorld v2**: sheets `Copy of Tasks`, `Hosted Environments` (14 app URLs), `Sheet3`,
  `Tasks`. `Copy of Tasks` and `Sheet3` contain **overlapping task IDs with different
  instructions and rubrics** — that overlap is the most important thing in the corpus.

### 1b. Extract only the task definition from the 2.6 GB zip

Never unzip it whole. Pull the small files:

```bash
unzip -o -q "ref_files/BrowserComp_T02 (1).zip" \
  "T02-work-across-teams/README.md" \
  "T02-work-across-teams/cross-team-poster-started-item/*" \
  "T02-work-across-teams/results.csv" \
  "T02-work-across-teams/runs/T02-GPT-01/config.json" \
  "T02-work-across-teams/runs/T02-GPT-01/result.json" \
  "T02-work-across-teams/runs/T02-GPT-01/verifier/*" \
  -d scratch/t02
```

Read `instruction.md`, `operating-notes.md`, `task.toml`, `tests/grader.py`,
`tests/grader_kit.py`, `tests/auxiliary_data.json`, and a `reward-breakdown.json`.
This is the Harbor package template.

**Note in `grader.py`'s docstring:** *"Verified against the untouched seed: no seeded
record satisfies this, so the check cannot pass before the agent acts."* That discipline
becomes Stage 6 of the playbook.

---

## Phase 2 — Analysis (the part that matters)

Answer these five questions from the data. Expected values given.

### Q1. What does each benchmark measure?

Three orthogonal axes, one loaded per corpus:

| Axis | Corpus | Score shape |
|---|---|---|
| Inference — can it *find* the answer | BrowseComp | binary 0/1 |
| Execution — can it carry a dependent chain | OSWorld 2.0 | weighted, chain-gated |
| Restraint — can it avoid breaking things | AutomationBench | objectives, zeroed by guardrail |

### Q2. Did the OSWorld rewrite help or hurt?

Compare shared task IDs between `Copy of Tasks` and `Sheet3`, scoring **mean absolute
spread** between Opus 5 and GPT 5.6 average reward.

| | Mean Opus | Mean GPT | **Mean spread** |
|---|---|---|---|
| `Copy of Tasks` | 0.471 | 0.279 | **0.225** |
| `Sheet3` | 0.194 | 0.163 | **0.049** |

A **4.6× loss of discriminative power.** Georgia mid-month rate-change (`092be9d8`)
appears in both: **0.875 / 0.25 → 0.125 / 0.125**. All five Tax Accountant tasks in
Sheet3 score exactly **0.125 / 0.125** — 1 of 8 checks, both models.

### Q3. Why?

In each of those five, the never-cleared first gate is a **verbatim stamp**. Regex the
`enter exactly` / `put exactly` strings out of both instruction columns and compare the
dash characters:

```
Swayam: "GA state rate change effective 2026-07-16 — July recomputed…"   (em dash U+2014)
Mahek:  "GA state rate change effective 2026-07-16 - July recomputed…"   (hyphen)
```

Same divergence in the GL tie-out, FL late-remittance and GA order-ledger stamps.

Treat the dash as the **leading hypothesis, not proven** — two things changed at once
(wording and gating structure). The structural lesson holds either way: **a check no
rollout clears must never be a prefix gate.**

### Q4. Does app count drive difficulty?

No — the opposite.

- ≤3 apps: mean spread **0.413** (n=3) — Georgia 0.625, Blocked-sender purge 0.519
- 7 apps: mean spread **0.126** (n=6) — Team Management Refresh **0.000**

Small n, so directional. But the 2-app Blocked-sender purge out-discriminates every
7-app trail. **Coupling carries difficulty; breadth does not.**

### Q5. What makes a task discriminative?

Grade by **per-check failure rate**, never rubric mean. A check at 0–30% failure is a
floor; 70–100% is dead weight; only **30–70%** carries signal. The 0.125 tasks are 1
floor check plus 7 dead ones, and the mean hides both defects at once.

Also derive the five difficulty levers by reading the task summaries: **Join**
(intersection of two apps), **Arbitration** (conflicting sources, one authoritative),
**Carry** (value read in A, written in B, recomputed live at grade time), **Restraint**
(negative space), **Sequence** (creation-time order — brittle, use sparingly).

---

## Phase 3 — AutomationBench

### 3a. Do not trust the summaries

`artificialanalysis.ai/evaluations/automationbench-aa` shows one-line task descriptions.
**Those are summaries, not prompts.** An earlier pass took them literally and wrote a
"15–40 word" rule into the playbook that is wrong by a factor of two.

### 3b. Get the real repo

```bash
curl -sL "https://api.github.com/repos/zapier/AutomationBench/git/trees/HEAD?recursive=1" -o tree.json
for d in finance hr marketing operations sales support simple; do
  curl -sL "https://raw.githubusercontent.com/zapier/AutomationBench/main/automationbench/domains/$d/tasks.py" -o "ab/$d.py"
done
```

Six domains × 100 tasks (sales has 106) = **606**, plus a public `simple` domain of 200
baseline tasks excluded from the headline score.

### 3c. Parse with AST, and watch the trap

Schema: `example_id`, `task`, `prompt`, `answer`, `info{zapier_tools, initial_state,
assertions}`.

**Trap:** `ast.literal_eval` on the whole `prompt` list **fails silently** — the system
turn references the `SYSTEM_PROMPT` name, not a literal. You get 0-word prompts and may
not notice. Walk the list elements and `literal_eval` only the user turn's `content`.

Guardrails are plain **negative assertions**: `google_sheets_row_not_exists`,
`gmail_message_not_sent_to`, `*_not_contains`. Count any assertion type containing
`not_exists`/`not_sent`/`not_contains`/`absent` as a guardrail.

### 3d. Expected corpus statistics

| | Words | Apps | Objectives | Guardrails |
|---|---|---|---|---|
| min | 11 | 2 | 1 | 0 |
| **median** | **66** | **4** | **7** | **5** |
| max | 192 | 8 | 47 | 38 |

Guardrail-to-objective ratio **0.65**. Only **12 of 606** tasks have no guardrail.

Per domain, median words: finance 70, hr 61, marketing 62, operations 111, sales 42,
support 64. Mean apps 3.0–4.7 — **never 7**, corroborating Q4.

### 3e. The finding that governs the house voice

Read the extremes:

> **11 words / 14 objectives:** Tag the Project Alpha emails for the PM, same as usual.

> **192 words / 7 objectives:** Review the backup generator inventory (ss_generators,
> ws_units) and schedule load testing… 'Monthly' generators are due if Last Load Test is
> more than 30 days ago… Generators with Status 'Under Repair' cannot be tested — skip
> these…

**Length is an output, not a target.** State the rules the agent could not reasonably
discover; push everything else into the seed. "Same as usual" works at 11 words because
precedent carries the spec; the generator task needs 192 because its rules are arbitrary
policy existing nowhere else.

**And the 192-word prompt still names no cell address.** Business rules yes, UI
coordinates never. That is the real line against the OSWorld tax specs, which dictate
A34/B36/C36. It is also why their tasks can't be voided by a dash character.

---

## Phase 4 — Build the tooling

Three files under `lib/`.

### `grader_kit.py` — hybrid runner

Extends the reference `grader_kit` with two things it cannot express:

1. **Guardrails** (`kind: "guardrail"`) pass by default; any violation sets reward to
   `0.0`. Never gated — a rule is broken whether or not the chain reached that far. A
   guardrail that *errors* is treated as intact, so an evaluation fault can't manufacture
   a zero the agent didn't earn.
2. **Prefix gating** (`requires: [id]`) resolved centrally, so a gated criterion reports
   **`gated_out`, not `failed`**.

That second point is the whole reason for the module. A criterion never reachable says
nothing about whether a model could have cleared it; averaging it in as a failure is what
makes an over-gated task look uniformly hard instead of broken.

Also: coerce reward to `float` before returning. A string in `reward.json` silently voids
a Harbor trial.

**Verify with a synthetic harness** — stub eval functions, four cases:

| Case | Expect |
|---|---|
| all objectives pass, guardrail intact | reward 1.0 |
| gate fails | downstream `gated_out` with `gated_by` populated, not `failed` |
| guardrail violated, all objectives pass | **reward 0.0**, `zeroed_by_guardrail: true` |
| floor only | reproduces the Sheet3 shape — low reward, 2 gated out |

### `calibrate.py`
Reads N `reward-breakdown.json` files. Per check: passed / failed / gated_out, pass rate
over **reachable attempts only**, and a band verdict (FLOOR / GOOD / WEAK / DEAD).
Flags non-numeric rewards rather than coercing them.

### `seed_zero.py`
Loads a task's `grader.py`, runs it against a pristine `/api/state` dump, asserts **every
objective scores 0 and every guardrail scores 1**. Non-zero exit on any violation.

---

## Phase 5 — Write the playbook

`docs/PLAYBOOK.md`, ten sections: what we measure (3 axes) · personas · five levers ·
check model · **AutomationBench voice** · the nine stages · package layout ·
anti-patterns · operational gotchas · definition of done.

### The nine stages

| | Stage | Out |
|---|---|---|
| 0 | Persona + stack | app list |
| 1 | Scenario brief + **novelty line** | `brief.md` |
| 2 | **Seed design — before any prose** | `seed.md` |
| 3 | **Check list — before any prose** | `auxiliary_data.json`, `rubric.md` |
| 4 | Write the instruction | `instruction.md`, `operating-notes.md` |
| 5 | Implement grader | `grader.py` |
| 6 | Seed-zero verification | pass/fail |
| 7 | Calibration, 3 rollouts × 2 models | per-check rates |
| 8 | Rebalance bands and gates | revised rubric |
| 9 | Freeze seed + instruction + grader together | sheet row |

2 → 3 → 4 in that order, never reversed. 6 → 7 → 8 loops until the bands are right.
Stage 8 is what the OSWorld rewrite skipped.

**Novelty line (Stage 1):** one sentence stating what this task asks that no reference
task asks. If the honest answer is "the same question on different data", change the
*lever*, not the numbers. Reusing the **world** (org, people, calendar) is fine and
cheap; reusing the **question** is not.

### Budgets

- ≤2 floor, 4–6 core, 1–2 stretch checks
- guardrails protect genuine negative obligations with actual enforcement; no count ratio
- gates **only** on checks measured in the 30–70% band
- never gate a verbatim-string check or a sequence check
- ≥1 check `cross_app: 1`, recomputing its target live from the source app

## Phase 6 — Generate the example library

`docs/example_tasks.md`: ≥25 tasks per domain (150 total) with prompt verbatim, app list,
objective/guardrail split, word count. **Sample evenly through each file** — the modules
are grouped thematically, so the first 25 all land in one or two themes.

Include the corpus statistics table and a domain→persona map. Ours covers Finance
(Tax Accountant, Financial Analyst) and Support (Technical Support Engineer); **HR,
Marketing and Sales are uncovered.**

## Phase 7 — First task

Author one new task through Stages 1–3 minimum. Persona chosen here: **Tax Accountant**
(Excel, NetSuite, TaxJar, Gmail, Word) — best measured discrimination in the corpus at a
0.625 spread, and arbitration already seeded.

Because fixtures live on S3 and aren't local, write `seed.md` as **fixture requirements**
— what the seed must contain — not as assumptions about what it holds. That is the
correct Stage 2 ordering anyway.

---

## Verification checklist

You have replicated this correctly if you independently reproduce:

- [ ] mean spread `Copy of Tasks` 0.225 vs `Sheet3` 0.049
- [ ] Georgia `092be9d8` at 0.875/0.25 and 0.125/0.125
- [ ] all five Sheet3 tax tasks at exactly 0.125/0.125
- [ ] the em-dash / hyphen divergence in the stamp strings
- [ ] ≤3 apps spread 0.413 vs 7 apps 0.126
- [ ] 606 AutomationBench tasks; words 11/66/192; guardrail ratio 0.65; 12 with none
- [ ] grader_kit: guardrail violation → 0.0 with all objectives passing
- [ ] grader_kit: gate failure → `gated_out`, not `failed`

## Traps that cost time here

1. `openpyxl`/`pandas` absent — write the stdlib reader.
2. The T02 zip is 2.6 GB — selective `unzip` only.
3. `literal_eval` on the AutomationBench `prompt` list fails silently → 0-word prompts.
4. The Artificial Analysis page shows summaries, not prompts. Go to the repo.
5. When transcribing corpus min/median/max into a table, re-verify — max values are easy
   to transpose between columns.
6. `memory_mb = 16384`, not 8192: the verifier parses a ~850 MB combined `/api/state`,
   peak RSS ~4.5 GB. At 8 GB it is OOM-killed with no exception, no output and no
   `reward.json`, *after* the agent has run.

---

## Decisions already made

| Decision | Choice |
|---|---|
| Grader shape | Hybrid — chain-gated weighted objectives **plus** zeroing guardrails |
| First persona | Tax Accountant (Excel, NetSuite, TaxJar, Gmail, Word) |
| Existing broken tasks | Leave them; author new rather than repair |
| Reference corpora | Learn from, never clone |
