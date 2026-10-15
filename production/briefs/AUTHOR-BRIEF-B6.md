# Batch 6 author brief: conjunctive-hard, clean, learnable non-coding tasks (2026-10-13)

> **History (2026-10-15).** Superseded as instructions by `AUTHOR-BRIEF-B8.md`; kept for the measurements and reasoning behind its rules. Paths below are the old workspace layout (`$W/research/batch4/...`): in this repo the tools are in `production/tools/`, the briefs in `production/briefs/`, the templates in `production/templates/`, and trap modes come from `production/traps/TRAP-LIBRARY.md`.

You build **ONE** task. It must be **extremely hard**, **clean** (every failure is the model's own), and **learnable** (a model's 10 runs score differently, so it can learn from its failures).

- Workspace: `~/Downloads/arena-envs-non-coding-v2` ($W).
- Python for everything: `$PY` = `/Users/pratyushmohanty/.local/share/uv/python/cpython-3.11-macos-aarch64-none/bin/python3.11 -I -B`, which is the verifier's version.
- Your seed (session id, concept, planned trap families) is in your prompt. Background on why this design: `$W/research/batch4/fb261013/PROPOSAL.md`.

## 0. The target, and why the old design fails it

Arena's 261013 review and spec 10_12 found our last batch near-useless for training:
- 36 of 37 tasks hinged on one trap (timestamp ordering);
- about 72% of points were free;
- the trap sat in two linked checks, so every run scored about 0.72 or 1.0;
- most models scored the same in all 10 runs.

A group-relative RL learner gets zero gradient from 10 identical scores.

**Batch 6 gets hardness from conjunction.** Each task carries **4–5 independent difficulty premises**, each from a different trap family, each failing on its own checks. With each premise missed in about 30–45% of runs, full success stays rare: about 0.05–0.15, so 0–2 of 10 runs. Partial scores still spread: about 4 distinct values per 10 runs.

**Calibration target, measured later by the controller with `research/batch4/b6/tools/signal_gate.py`:**
- task pass@1 ≤ 0.30 on BOTH Fable 5.1 and GPT-6 Astra, with Fable ≤ 0.20 preferred;
- every model × step gives ≥ 3 distinct scores and reward SD ≥ 0.08;
- every premise is missed in some runs and passed in others;
- premises are not correlated;
- ideally each model fully passes 1–2 of 10 runs.

**Do not aim at "nobody ever gets premise X".** A premise missed 100% of the time teaches nothing and usually means ambiguity: 14 of 15 such cases were.

## 1. Build

1. Copy `$W/research/batch4/skeleton/` to `$W/envs-b6/a_f<level>_<slug>/`. The level is your faithfulness target (section 6). Version 1.0.0.
   - The skeleton's runtime carries every 261011 fix; never replace it.
   - Reuse the authoring-script pattern of `$W/envs-b4/a_f0_funnel-go-live-review/authoring/`: `make_fixture.py` → `make_checks.py` → `make_contract.py` → `build_tests.py` → `validate.py`, with a byte-identical rebuild.
2. **Write the fixture** (`environment/files/`). Make it a realistic professional workspace: policies/handbooks, exports, drafts, correspondence. Ground it in the seed session's real material and user corrections. Keep it moderate in size (breadth is anti-correlated with difficulty).
3. **Write the instruction** (`steps/<step>/instruction.md`). It states WHAT is wanted, never HOW to find the traps:
   - the as-of date;
   - every field and its meaning;
   - the deliverable path;
   - the published contract sentence, copied from `skeleton/tests/_arena_runtime/contracts.py` `public_contract`.

   Never name a trap, a variant or a governing record, and never put a graded value in an example.
4. **Write `tests/checks.json`** (data, not code), plus `outputs.json` (schema), `rubric.json` (check ids per step), `basis.toml` (public wording per check) and `reward.toml`.
5. **Write the reference** (`steps/<step>/solution/solve.py`). It DERIVES every answer from the fixture, with no stored answers, and honours `ARENA_MISREAD`:
   - when `ARENA_MISREAD="P2,P4"`, solve.py writes the deliverable a solver would write if it misread exactly those premises, and handles everything else correctly;
   - each misreading is the realistic wrong reading you documented, e.g. "orders the pair on printed stamps" or "takes the first matching row".

   `design_lint.py` runs every subset of misreadings.
6. **Write `authoring/traps.json`** (the premise map), and put `trap_families = [...]` into `task.toml` `[metadata]`:

```json
{
  "schema": "b6/premises/1",
  "premises": [
    {"id": "P1", "family": "changed_premise", "step": "01-task", "checks": ["obj_items_changed"],
     "aimed_at": "fable", "target_q": 0.4,
     "resolving_quote": {"file": "policies/handbook.md", "text": "exact sentence that settles it"},
     "misreading": "keeps the pre-revision verdict for items already counted",
     "salience": "the revision arrives as a by-the-way line in an unrelated thread; knobs: move it into the main thread (more salient) or into a forwarded attachment (less)",
     "grounded_in": "01a077a4-...::msg11 'it was 2000-2500 at that time'"}
  ],
  "coverage_checks": ["obj_field_a", "obj_field_b"],
  "leak_allow": [{"value": "2026-10-12", "reason": "the as-of date the instruction must state"}]
}
```

## 2. Design rules (enforced by `design_lint.py`; violating any one is a hard fail)

- **Premise count.**
  - Single-step tasks: ≥ 4 premises, each from a different family.
  - Multi-turn tasks: ≥ 2 premises per step (distinct families within a step) and ≥ 5 distinct families across the task.
  - At most 1 timestamp-ordering premise per task, and only if your seed plan lists it.
- **One decision = one check.** Every objective check belongs to exactly one premise or is a coverage check.
  - A downstream field (verdict, total, count, byte length) is graded against the agent's OWN upstream answer, never against the reference's. This is Arena 261011 R18/R29.
  - Never let one premise fail another premise's checks. Split sets by deciding premise; give "no extras" its own check.
- **Weights, per step:**
  - each premise ≤ 25% of the step's points (aim 12–20%);
  - premises together ≥ 55%;
  - coverage (free) checks ≤ 35%.
- **Field coverage.** Every field and per-item record asked for is graded (261008 class 2). Coverage checks still exist; they are just capped.
- **Additivity, executed.** For every subset of a step's premises, the misread deliverable fails exactly those premises' checks and scores exactly 1 − their weight share.
- **Resolvable.** Each premise's `resolving_quote` appears verbatim in a fixture file. A careful reader can settle the premise from the materials alone. No hidden facts, no world knowledge, no "intent" guessing.
- **No leaks.** No reference value appears in any instruction, except enum options and justified `leak_allow` items. The skeleton keeps tests and the solution out of the agent image; never move them.

## 3. Choosing and building premises: "noticing" traps that survive review

Measured over 8,000+ episodes (`$W/research/batch4/fb261013/HISTORY-NOTE.md`):
- **What survives clean gates at moderate rates is noticing misses.** The settling fact is in the files, and the model never cross-references it.
- **Any premise with a second defensible reading gets contested, and clarifying it kills the bite** (7 of 7 cases).
- **A premise aimed at one model is often solved by the other**, so aim at least one premise at each model:
  - **Fable** overrides stated rules for apparent intent or fidelity, carries its own earlier corrections too far, copies its earlier output, and misses casual facts.
  - **Astra** works code-first and literally: first match, last row wins, printed labels, default conventions, `(d2-d1).days`.

**Families** (catalogue: `$W/research/batch4/fb261013/TRAP-CATALOGUE-NOTE.md`). Use your seed's planned families. Construction notes:

- **changed_premise:** a stated revision flips items ALREADY judged, through an attribute the solver has no reason to re-read (backdated authority, a revised price behind a ratio). Don't name the affected record. Grade "items whose outcome changed" plus one recomputed value on another item. Measured: Fable 32–60%, Astra low; pair it with an Astra-aimed premise.
- **clean_baseline:** a before/after comparison where a later change must not leak into "before". Measured: Fable 6/15, Astra 0/15.
- **house_convention_numeric:** a stated house rule (e.g. half-up at 2 dp on an exact decimal half that binary cannot represent, sitting on a band edge) that float or default handling gets wrong. This is the only measured stochastic two-model lever (~40% each). The grader and solve.py must use `Fraction`/`Decimal`.
- **caption_only_rule:** a rule that lives only in a table caption, legend, footnote or code table, not in the main policy text. Measured: Fable 67%, Astra 27%. Give it ≥ 12% weight.
- **identity_variants_twins:** one entity under two spellings that MUST merge (a key in the data proves it), and a near-twin that must stay apart. Never name the variant: naming killed it (5/15 → 0/15). Use two checks on different populations.
- **coverage_counting_unit:** "every requirement X is covered" where coverage counts by the governing unit, and 1–2 are silently skipped. Models catch over-inclusions 6–7× more often than omissions. Grade the exact set of uncovered IDs.
- **scope_compliant_twins:** the change applies to a scope; near-twins that look in scope but are excluded by the scope sentence must stay out. Grade with a no-false-positive check keyed to the twins.
- **wrong_figure_vs_derivation:** a figure repeated in a summary, a checklist and a memo disagrees with the governing derivation, and a sentence says the derivation wins. Make the wrong figure self-consistent, not a visible rival.
- **literal_overreading:** a rule restated in a summary more broadly or narrowly than its governing text. The governing text decides (Astra 47%).
- **version_in_force:** derive the effective version from structural dates ("from the first payroll after publication"), never from a bare "in force on" line.
- **population_reshaped, stacked_rules_order, composition_totals_tie, answerability, precedent_rule, governing_vs_filing_key, event_key_mismatch:** usable when the seed grounds them. Each must be settled by an explicit sentence.
- **timestamp_ordering:** clock offset or backup store. At most 1 per task, only where planned, and the doctrine of `$W/research/batch4/AUTHOR-BRIEF-B5.md` applies: 3 anchors, one direct stamp tie, no cross-posts, a wide margin.

**Salience is the dial.**
- More hidden: an incidental placement, another day, a reply doing another job, no cue words.
- More visible: the same thread, adjacent text, a summary that restates it.

Aim each premise at about 0.3–0.5 miss, and record the knob in `salience`, so the controller can tune it after the pilot without rewriting the task.

**Never** use:
- authority/delegation conflicts;
- inferred generic exclusions;
- identity with no key;
- trigger-event rules without a defining sentence;
- breadth or decoy rows/documents;
- forbidden-edit traps;
- deleting scope or exclusion sentences ("de-leaking");
- single-soft-anchor inferences;
- rules placed in the instruction.

## 4. Multi-turn tasks (only if your prompt says so; ≥ 3 turns)

- `steps/01-task`, `02-…`, `03-…`, each with its own deliverable file and its own premises.
- Each step is a FRESH session in both harnesses (it sees files, not the conversation). So each step's instruction restates everything it relies on, and must make sense by itself.
- Later steps carry the seed's real follow-ups (a revision, a further correction). These are natural changed-premise and scope premises.
- Every step's checks are independent of earlier steps' answers. Grade step N against the step-N truth, and never double-penalise a step-1 miss.
- `task.toml` has one `[[steps]]` entry per step with `env = { ARENA_STEP = "<step>" }`, and `multi_step_reward_strategy = "mean"`.

## 5. Mandatory quality classes (all must pass; write one line of evidence each in VALIDATION.md)

**261008:**
1. precision is graded at the stated decimals;
2. every field is graded;
3. collections are exact sets with no extras;
4. every conflict has a stated precedence rule;
5. an explicit as-of date;
6. no premise over 50% (batch 6: 25%);
7. counting follows the stated rule;
8. no instruction/fixture conflict.

**261011:**
- uniqueness by the grader's own equality;
- lstat inventory;
- deep/huge/non-UTF-8/NaN inputs → the zero record;
- carrier roles in `provenance/ledger.json` if any session file is carried twice;
- figures graded against the solver's own selections;
- every stated limit graded;
- no hidden acceptance list (citations accept every supporting section);
- fixture adds no claim the source lacks;
- frozen copy obeys its own limits;
- no lexical guard on harmless text;
- everything referenced exists;
- empty vs missing distinguished;
- no graded value in examples.

**No second reading:** for every graded field, write the strongest competing reading and the sentence that defeats it into VALIDATION.md.

## 6. Faithfulness and provenance

- Set `[metadata] faithfulness`, `source_trace`, `source_seeds` and `source_intent`. `source_intent` quotes the user's real words with message indices.
- Target F1 or F2 where the seed's corrections ground your premises:
  - F1 = the trace's failure mode is preserved (calibration must later show models failing that way);
  - F2 = scenario, failure mode and grading criteria come from the trace.
- Otherwise use F0 (the trace's goal and capability). The controller decides the final label from the measured evidence.
- Lift real files where possible, and record origins in `provenance/ledger.json`, with carrier roles for duplicates.

## 7. Validate (all executed; `mktemp -d` copies; `$PY`)

```
$PY $W/research/batch4/b6/tools/design_lint.py <task>        # must print DESIGN GATE: PASS
$PY $W/research/batch4/fix261011/selftest.py <mktemp copy>    # every line ok or --
$PY <task>/authoring/validate.py <abs task> <mktemp scratch>  # your own suite
```

`validate.py` covers:
- reference 1.0 and an empty workspace 0.0;
- every premise's misreading alone, and combined (design_lint does all subsets);
- ≥ 15 rule-breaking variants lose credit, and ≥ 3 benign variants (reordering, whitespace, an equivalent number spelling) keep 1.0;
- one counterfactual per premise: change the settling fact in a scratch copy, the derived answer flips, and the grader follows (old answer fails, new answer passes);
- a leak grep;
- a byte-identical rebuild;
- no `__pycache__`.

## 8. Write and hand back

- **`VALIDATION.md`:** the premise table (id, family, checks, weight share, aimed at, resolving quote, misreading, salience knob, grounding), every validation output, the 261008/261011 lines, and the second-reading table.
- **`REWARD-HACKING.md`:** what was probed (empty, forged, answer lookup, fixture tamper, FIFO, deep JSON) and the results.
- **The `task.toml` `difficulty_explanation`:**
  - describes the 4–5 premises truthfully, with no pass rates;
  - ends with: "Calibration of record: the delivered package's `calibration/` folder (one row per valid run in `calibration/runs.csv`, trajectories under `calibration/trajectories/`): a fresh 10x2 on Fable 5.1 in Claude Code and GPT-6 Astra in Codex, run after a 5x2 pilot of the same version. The Harbor `tasks-check` receipt for this version ships as `verification/harbor-tasks-check.json`."
- **No `verification/` folder** in the tree.

**Hand-back, under 25 lines:**
- the path;
- the premise table (id, family, weight share, aimed at, target miss rate);
- the design_lint and selftest results;
- the validation summary;
- the faithfulness target with its evidence;
- anything uncertain.

## Limits

- Never touch `$W/pipeline/`, other tasks, the Coder pools, or any arena/harbor/benchmark/coder command.
- Never glob /tmp.
- Never read `keys.env` or rclone config.
- Never write Co-Authored-By/Anthropic attribution.
- Spawn no subagents, and no blind readers (the controller runs them).
- **Time box: 80 minutes.** If the gate still fails at 70 minutes, hand back with the exact failures.

## Appendix: seed plan family codes → `traps.json` family names

`seeds-b6.json` numbers families as follows:

| code | family name |
|---|---|
| 1 | wrong_figure_vs_derivation |
| 2 | changed_premise |
| 3 | population_reshaped |
| 4 | version_in_force |
| 5 | identity_variants_twins |
| 6 | governing_vs_filing_key |
| 7 | house_convention_numeric |
| 8 | caption_only_rule |
| 9 | coverage_counting_unit |
| 10 | scope_compliant_twins |
| 11 | answerability |
| 12 | composition_totals_tie |
| 13 | stacked_rules_order |
| 14 | clean_baseline |
| 15 | event_key_mismatch |
| T | timestamp_ordering |

You may also use the extra families literal_overreading and precedent_rule. You may swap one planned family for another if the material grounds it better; say so in the hand-back. Quotas are rechecked per batch.

Fictionalise real names: people, brands, schools, minors, court judgments and statutes. Keep the professional substance.
