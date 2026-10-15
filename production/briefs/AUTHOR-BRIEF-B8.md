# B8 author brief: extremely hard, clean, non-coding tasks built from the trap library (2026-10-15)

**This brief is authoritative.** It consolidates, and replaces as instructions, `AUTHOR-BRIEF-B6.md`,
`HARD-DOCTRINE-B6v2.md`, `TUNE-BRIEF-B6v6-proven.md`, `UNBLOCK-BRIEF-B7.md` and `TRAP-CATALOG-B7.md` §1, §4 and §7.
Those files stay in `production/briefs/` as history: read them for the measurements behind a rule, never for the rule.
Trap modes come from **`production/traps/TRAP-LIBRARY.md`** (built from `library.json`; `traplib.py show <id>`), not
from the catalogue. Where the library and an older brief disagree, the library wins.

You build **ONE** task (or retune one). It must be **extremely hard** for both calibration models, **clean** (every
failure is the model's own), and **learnable** (a model's runs score differently). Paths below are relative to the
repo root. Python for everything you execute in a task: `python3.11 -I -B` (the verifier's version; `paths.PY311`).

## 0. The bar you are measured against

| | Arena's bar (user, 2026-10-15) |
|---|---|
| difficulty | task pass@1 **<= 0.5 on BOTH** Fable 5.1 (Claude Code) and GPT-6 Astra (Codex), high effort, no limits, on a fresh 10 x 2 final. **Aim at 0.1-0.3.** Do not chase <= 0.2: it pushes tasks to the flat 0/10 shape Arena criticised |
| learning signal | a within-model pass/fail mix (each model fully passes some runs); varied failures: >= 3 distinct scores and reward SD >= 0.08 per model x step (`signal_gate.py` SPREAD; its EXTREME flag still uses the older 0.30 line) |
| free points | free share <= 0.40: decisive premises carry >= 60 of each step's 100 points; >= 8 graded checks summing to 100 |
| trap spread | no clock trap as the primary failure; no family heaviest in more than ~20-25% of a batch (`plan_batch.py`, `batch_diversity.py`) |
| validity | every failing premise GENUINE under the §14 audit; a blind reader reaches the reference |

A miss rate from 5 runs is noise (the same text measured 2/5, then 5/5): pilots triage, finals decide. Treat any
unaudited 100% miss as ambiguity until a blind reader and the §14 audit say otherwise.

## 1. What decides trap design (measured: 1,129 premise units, 12,685 premise-runs; `research/`)

1. **Models read everything.** In 519 of 521 failing premise-runs the deciding line was already in the model's own tool
   output. Failures are reconciliation failures. Hiding, burying, volume, decoys and breadth do nothing.
2. **Stated rules never bite** (Fable 0/810, Astra 0/720). A trap works only through an inferred trigger fact.
3. **Filling a gap dies; reversing a record bites.** Fable fills gaps correctly but will not overrule a record.
4. **The models fail differently.** Fable notices the conflict and overrules the evidence (43% of its misses), hedging
   "if X then Y" and often citing a real rule that does not cover the case (the *rule shield*). Astra is silent in 83%
   of its misses: it joins on the key or applies a default convention; when it notices, it credits both readings
   (*union*) or answers "not determinable".
5. **A careful blind reader separates genuine from unfair.** If a printed current form or governing table states the
   opposite of the answer, the blind reader misses too: unfair. If no sentence gives the record priority, readers reverse it.
6. **Agents investigate whatever does not reconcile.** A trap whose default answer leaves an anomaly (an unmatched row,
   a ratio, a duplicate, a total that does not tie) is solved by the model's own script.

## 2. Your inputs

- The seed: session id, domain, and the plan brief `plan_batch.py` wrote for it (3-5 library modes with roles and
  suggested weights, and a `traps.json` skeleton). Plan modes are **targets**: build each one only where the seed's
  material supports it naturally. If one does not fit, swap in another library mode of a different family and say why.
- For every mode you build: its `TRAP-LIBRARY.md` section (summary, recipe, proof obligations, hazards, what killed it,
  example) and, for measured modes, the source premises its evidence rows name. Open the source task's `VALIDATION.md`,
  `DIAL.md` and fixture lines (`envs-b6/_versions/...`): copy the **ingredients**, never the wording.
- Status rules: `proven` and `promising` may be decisive. `literature`, `trace-derived` and `bimodal` are "pilot first":
  at most one per task, never the heaviest, and a pilot decides whether it stays. `dead` is refused by the lint, and
  so is every `D` id (the dead list), even one whose small sample computes as `promising`.

## 3. Build

1. Copy `production/templates/skeleton/` to `envs-b6/a_f<level>_<slug>/`, version `1.0.0` (a retune copies the base
   tree named in your prompt to the place named there, bumps to the version named there and drops any `verification/`
   receipt; never edit `_versions/`). The skeleton's runtime carries every 261011 fix: never
   replace it. Follow the authoring-script pattern of `production/templates/reference-task-suitcase-2.6.0/authoring/`:
   `make_fixture.py` -> `make_checks.py` -> `make_contract.py` -> `build_tests.py` -> `validate.py`, with a
   byte-identical rebuild. That task met the bar; read its `VALIDATION.md`, `DIAL.md` and `traps.json` first.
2. **Fixture** (`environment/files/`): a realistic professional workspace (policies, exports, drafts, correspondence),
   grounded in the seed's real material and corrections, moderate in size. Fictionalise real people, brands, schools,
   minors, judgments and statutes; keep the professional substance.
3. **Instruction** (`steps/<step>/instruction.md`): WHAT is wanted, never HOW to find a trap. State the as-of date,
   every field and its meaning, the deliverable path, and the published contract sentence from
   `tests/_arena_runtime/contracts.py` `public_contract`. Field names and descriptions are schema-only ("the code for
   each slip"), never the rule's nouns ("under the guidelines", "checked against"). No 5-word run shared with a rule
   quote or anchor. **Examples carry no number, no ID and no fixture value** ("IDs such as H01" leaked a graded value
   in an earlier batch).
4. **Grader as data:** `tests/checks.json`, `outputs.json` (schema), `rubric.json` (check ids per step), `basis.toml`
   (public wording per check), `reward.toml`.
5. **Reference** (`steps/<step>/solution/solve.py`) DERIVES every answer from the fixture, with no stored answers, and
   honours `ARENA_MISREAD="P2,P4"`: it writes what a solver who misread exactly those premises would write.
6. **Premise map** `authoring/traps.json`, schema `b8/premises/1` (§4), and `task.toml [metadata] trap_families`
   = the set of premise `family` values.
7. `authoring/DIAL.md` lists every dial sentence (§6.8); `VALIDATION.md`, `REWARD-HACKING.md` and the `task.toml`
   `difficulty_explanation` per §8. No `verification/` folder in the tree.

## 4. `authoring/traps.json` (schema `b8/premises/1`)

```json
{"schema": "b8/premises/1",
 "premises": [
  {"id": "P1", "decisive": true, "template": "T2", "aimed_at": "astra",
   "family": "house_convention_numeric", "mechanism": "EXEMPLAR", "step": "01-task", "checks": ["obj_share_pct"],
   "target_q": 0.4,
   "resolving_quote": {"file": "guides/style.md", "text": "the positive rule, verbatim"},
   "anchors": [{"file": "letters/a.md", "text": "a by-the-way line, verbatim"},
               {"file": "logs/b.csv", "text": "a second party's routine line, verbatim"}],
   "default_technique": "round(100 * a / b): the parser/sort/join/rounding that produces the wrong answer",
   "interlocks_with": [], "misreading": "the realistic wrong reading and the value it gives",
   "salience": "where the anchors sit and which sentence is the dial", "grounded_in": "<session>::msg<n> '...'"}
 ],
 "coverage_checks": ["obj_field_a"],
 "leak_allow": [{"value": "2026-10-12", "reason": "the as-of date the instruction must state"}]}
```

| field | rule |
|---|---|
| `decisive` | `true` on every premise that carries the task's difficulty; fillers omit it |
| `template` | a library id or alias (`traplib.py resolve <x>`); required on every decisive premise |
| `aimed_at` | starts with `fable`, `astra` or `both` (a note may follow); if it does not, `target_model`, then the mode's own `aimed_at` is used |
| `family` | the B6 premise family (design_lint's catalogue, e.g. `governing_vs_filing_key`); distinct within a step. The library family comes from `template` |
| `mechanism` | a code from §6.1 (`EVENT ACTUAL TWIN STORE ATTR BASELINE SCALE PARSE CLOCK REVISED EXEMPLAR AGGREGATE`, or `HALF`/`STATED` for fillers only) |
| `anchors` | verbatim, from files other than the resolving quote's, from different parties |
| `interlocks_with` / `masked_by` + `masked_reason` | exactly one reciprocal interlocked pair per task; `masked_by` only names an interlocked premise whose misreading makes this one unobservable |

## 5. Composition rules (design_lint enforces them; `b6ctl author-check` requires them)

| rule | why |
|---|---|
| >= 3 decisive premises, each built from a library mode | conjunction: three independent traps each missed ~45% give pass@1 ~ 0.17; four or five at q 0.30-0.45 give 0.08-0.18 (HARD-DOCTRINE §6) |
| decisive modes span >= 2 library families (plan for 3) | one family failing alone flips the whole task |
| >= 1 decisive premise aimed at Fable and >= 1 at Astra | a trap aimed at one model is usually solved by the other |
| each decisive premise: >= 2 verbatim anchors in >= 2 files other than the resolving quote's file | an inferred fact needs two routine anchors from different parties; a single soft anchor is ambiguity |
| no clock premise is the heaviest of its step | Arena 261013: nearly every task of the reviewed batch hinged on the same clock trap |
| projected free share (100 - decisive weight) <= 40 per step | Arena's free-points bar |
| no decisive premise with mechanism `STATED` | stated rules measured 0/1530 |
| template neither `dead` nor a `D` id; `literature` / `trace-derived` / `bimodal` warn "pilot first" | the library's status rules and dead list |
| no number, ID or fixture value inside an instruction example | graded values leaked through examples |
| plus every B6v2 rule: premise <= 25% of a step, premises >= 55%, coverage <= 35%; single-step >= 4 premises with >= 3 hard mechanisms, >= 2 Fable-type and >= 2 Astra-type; one interlocked pair; executed additivity; verbatim quotes; no instruction echo; runtime patches; leak scan | unchanged from B6/B6v2 |

**Weights:** decisive 25 / 21 / 17 (unequal, >= 60 together; a fourth decisive premise about 12); fillers <= 5 points
each; >= 8 graded checks summing to 100. **Batch spread** (the controller's `plan_batch.py` / `batch_diversity.py`):
no lead mode and no lead family in more than 25% of the batch; the keying slip (T1) leads most shipped tasks, so new
tasks should lead with another mode where the material allows.

## 6. Building a decisive premise that bites and stays genuine

### 6.1 The decisive fact is inferred, never stated
The fact that triggers the rule is entailed by >= 2 routine anchors in >= 2 files of different parties, each doing
another job. The agent's default technique (sort the printed stamps, key by the printed label, take the routine
record's date, round half-up, take the first plausible figure) produces a confident wrong answer; the right answer
needs a column, line or side channel the default drops. Rules are positive and general: never their rationale, never
the misreading, never an advance warning of an exception. Keep every scope, exclusion and edge-case sentence: they
are meaning, not leaks. Close every escape with a structural fact, never by stating the answer. The anchors must agree,
and the answer must hold under every reading they allow, with a wide margin.

### 6.2 The recipe: make the model reverse a record (passing runs used an impossibility, a mechanism for the error,
a unique content match and a third witnessing anchor)
- **Record:** a structured, official-looking record (key, filing, log entry, export row) gives the default answer.
- **Anchors:** two or more anchors from different parties make the record impossible, not merely unlikely; each sits
  in a document read for another purpose.
- **Withheld:** no sentence gives the record priority and none states the error's mechanism; the model supplies it.
- **Dials:** each by-the-way anchor that witnesses the event, or a unique content match, is one notch toward
  solvable. For Astra, change the KIND of evidence (a receipt line), not the amount.
- **Conservation:** when an item could be credited to two places, grade both sides against a conserved total so a
  union answer loses.
- **Shields:** if a tempting rule exists, scope it explicitly away from the trapped variable; Fable will cite it.
- **Never** a printed form, legend or governing table that states the opposite of the answer.

### 6.3 Ask for the outcome, never the discrepancy
No field may list errors, mismatches, wrong items or conflicts a premise produces. Ask for the final register, total,
schedule, verdict or corrected value; the premise changes it through a step the model does without deliberating
(ordering, joining, assuming a unit, assigning a period or version, counting a population, picking the rate). If the
task audits X, the trap lives in Y, the step done silently on the way to X. **Anchors never read as corrections**: no
"actually", "the correct figure is", "corrects", "should be", "please update".

### 6.4 No anomaly under the default; semantic, lexically disjoint anchors
Apply your `ARENA_MISREAD`: the deliverable must look complete and consistent (no unmatched rows, no visible duplicate,
no stated total, header count or checksum only the correct reading reconciles, every value plausible). Prefer a false
merge to a missed merge. Anchors need their meaning read (a relayed event, a remark about what happened, a structural
statement), never a value a script can join, diff, hash or ratio. An anchor shares no identifier token with the record
it settles: it names the item by description or nickname, so grepping the identifier never finds it.

### 6.5 Convention from worked figures (T2 / EXEMPLAR)
The governing rule states the requirement and leaves the dimension open without contradicting it ("whole number",
"whole roubles"; never "to the cent" or "multiply exactly"). The worked figures sit in the governing document or a
signed/filed record that document binds; figures from another module, year or older rule set are ambiguity. No
pointer: no precedent clause, no "see the example", no method name anywhere (a template that prints the method's output
counts). Astra flips on the count of discriminating figures: **exactly one** discriminating figure for an Astra-aimed
T2 (a second one took Astra from 10/10 to 0/5), every other worked figure non-discriminating; for Fable, move the single
figure closer to where the figure is reported. Record which alternative conventions fail which figure.

### 6.6 Keying slip (T1)
A record keyed, filed or labelled under the wrong identifier, complete and self-consistent under that key (it fills a
blank, dates stay in sequence, the topic matches). Two routine anchors, each locally explained and naming the item only
by paraphrase, together prove the true owner. Grade a downstream consequence (a date, a code, a membership), never a
field that prints the slipped row's own content. The governing text states the true rule on the real-world fact ("the
date the lesson was held"); any record-practice sentence is descriptive, never binding the printed key. Check every
dated note on the slipped item: none may support the printed label. Killed by a corrective or exclusive anchor, a
pointer, a binding sentence, or a clash with another structured field. Dial: one by-the-way anchor per notch; a
too-specific anchor overshoots.

### 6.7 Shapes audits rejected (do not build)
- the rule text itself supports the default ("multiply ... to the cent" against a rounding exemplar);
- exemplars from another module, year or older rule set;
- a stated rule against a third-party fact with nothing saying which governs (scope the rule so the fact decides);
- text that binds the printed key; an anti-inference clause forbidding the evidence that settles identity;
- a rule applying to an item while one of its inputs (a clearance, a date, a unit, a party) is missing from the files;
- a "rule governs X" sentence asked to decide Y; any cascade (a downstream check graded against the reference's
  upstream answer instead of the agent's own).

### 6.8 Model targeting and dials
Fable reliably misses record reversals with 2+ parties and an impossibility, a tax-inclusive or per-pack basis cued on
the record itself, already-in-hand via a technical bridge, and scale shown only by incidental remarks. Astra reliably
misses cross-document identity chains, a filed column copied without deliberation, a line transposition settled by
first-hand descriptions, and (sometimes) a single discriminating worked figure. Pick one setting per version at the
level you expect to land at 40-60% per premise on its target model, list every dial sentence in `authoring/DIAL.md`,
and change one notch at a time after measurement (keep Astra-aimed figures fixed). Same-family anchors go in different
files: a new note next to an existing anchor primes it.

## 7. Grader shape

- **One decision = one check.** Every objective check belongs to exactly one premise or to `coverage_checks`. Never
  let one premise fail another's checks; give "no extras" its own check.
- **No cascade:** a downstream field (verdict, total, count, share) is graded against the agent's OWN upstream answer.
- **Attribution:** every check an inferred decision touches is set- or text-valued, graded order-free and
  case/space-insensitively; a number or boolean may depend on an inferred decision only if that premise also has its
  own set/text check. Grade one committed value per item: hedged multi-answers fail.
- **Additivity, executed:** for every subset of a step's premises, the misread deliverable fails exactly those
  premises' checks and scores exactly 1 - their weight share (`design_lint` runs it).
- **Field coverage:** every field and per-item record asked for is graded; coverage checks exist but are capped.

## 8. Prove it (VALIDATION.md + validate.py, all executed on `mktemp -d` copies)

`validate.py` (usage line `validate.py <task> <scratch>`) covers: reference 1.0 and an empty workspace 0.0; every
misreading alone and combined; >= 15 rule-breaking variants lose credit and >= 3 benign variants keep 1.0; a leak grep;
a byte-identical rebuild; no `__pycache__`; and, **per decisive premise, its mode's `proof_obligations`** at least:
- **uniqueness:** which alternative readings/conventions fail which anchor or figure;
- **anchor ablation:** delete one anchor (still settled by the other, or no longer determinable: say which), flip one
  (the reference flips), delete both (the default's answer results);
- **an executed counterfactual:** change the settling fact in a copy; the derived answer flips and the grader follows;
- **a census of plausible wrong answers**, each losing only its own check.

`VALIDATION.md` holds the premise table (id, mode, family, checks, weight share, aimed at, resolving quote, misreading,
dial, grounding), every validation output, one line of evidence per 261008 class (precision at stated decimals, every
field graded, exact sets, a precedence rule per conflict, explicit as-of date, no premise over 25%, counting by the
stated rule, no instruction/fixture conflict) and per 261011 class (uniqueness by the grader's equality, lstat
inventory, deep/huge/non-UTF-8/NaN -> zero record, carrier roles, figures graded against the solver's selections,
every stated limit graded, no hidden acceptance list, fixture adds no claim, frozen copy obeys its limits, no lexical
guard on harmless text, everything referenced exists, empty vs missing distinguished, no graded value in examples),
plus per premise: the strongest competing reading and the sentence that defeats it; the answers to "would a careful
agent that reads every file but never asks this premise's question get it wrong? does the instruction or a field name
make it ask? does any anchor read as a correction?" (must be yes / no / no); the misread deliverable's consistency
check; and that `grep -i <identifier>` over the fixture does not return the anchor.

`REWARD-HACKING.md`: what was probed (empty, forged, answer lookup, fixture tamper, FIFO, deep JSON) and the results.
`difficulty_explanation`: the premises truthfully, no pass rates, ending with the calibration-of-record sentence of
`production/templates/reference-task-suitcase-2.6.0/task.toml`.

## 9. Multi-step tasks (only if your plan says so; >= 3 steps)

Each step is a FRESH session in both harnesses: its instruction restates everything it relies on. Each step has its
own deliverable and >= 2 hard premises (distinct families within the step, >= 5 families across the task), and the
B8 free-share rule applies per step. A later step carries the seed's real follow-up as a re-decision lever (an identity
restated "by the identifier each source carries", a backdated authority that re-validates what step 1 voided). Grade
step N against the step-N truth and never double-penalise a step-1 miss. `task.toml`: one `[[steps]]` per step with
`env = { ARENA_STEP = "<step>" }`, `multi_step_reward_strategy = "mean"`.

## 10. Faithfulness and provenance

Set `[metadata] faithfulness`, `source_trace`, `source_seeds`, `source_intent` (the user's real words with message
indices). Target F1 (the trace's failure mode preserved) or F2 (scenario, failure mode and grading from the trace) where
the seed's corrections ground your premises, else F0; the controller decides the final label from the measurements.
Lift real files where possible and record origins in `provenance/ledger.json`, with carrier roles for duplicates.

## 11. Your gate: `author-check`

```bash
python3 -I production/tools/b6ctl.py author-check envs-b6/<task>
```

It runs `check` (stale-receipt quarantine, `design_lint --b8` with executed additivity and the example scan,
`selftest`), then your `validate.py` on a copy, then tree hygiene (`traps.json` schema `b8/premises/1`, no
`verification/`, the Dockerfile copies only `files/`). It ends with **READY** or **NOT READY** and every failing item
with its fix. Hand back only on READY; if you are out of time, hand back the NOT READY list verbatim.

## 12. Hand-back (<= 20 lines)

The path and version; per decisive premise: mode id, documents used, the default wrong answer, weight and expected
miss rate per model; the dial sentences; the expected free share; the `author-check` verdict line; the faithfulness
target with its evidence; any plan mode you swapped and why; anything uncertain.

## Limits

- Never touch `pipeline/`, other tasks, `_versions/`, the Coder pools, or any arena / harbor / benchmark / coder /
  measure command (the controller launches).
- Never read or print `keys.env` or any credential; never glob `/tmp`; use `mktemp -d` and remove only what you made.
- No subagents and no blind readers (the controller runs them). No Co-Authored-By or other attribution lines.
- Time box: 80 minutes for a new task, 75 for a retune. If `author-check` is still NOT READY at 70 minutes, hand back.
