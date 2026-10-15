# automationBench_tasks

Authoring environment for computer-use agent benchmark tasks. Harness: **harbor 0.22.0**
+ `computer_1` (agent `computer1_effort:Computer1Effort`), apps served as a composed
multi-RL container, graded programmatically from end state.

---

## Read before authoring or modifying a task

| Doc | When |
|---|---|
| **`docs/ANTI_REWARD_HACKING.md`** | **before designing the question.** Its §0 is a design decision that cannot be retrofitted. |
| `docs/PLAYBOOK.md` | the nine-stage method, personas, levers, check model, calibration |
| `docs/example_tasks.md` | 150 AutomationBench tasks — register and objective/guardrail balance. Reference only. |
| `docs/PLAYBOOK_GENERAL.md` | the same method with no domain assumptions |

**The reference corpora (`ref_files/`, `docs/example_tasks.md`) are for learning how tasks
are built. Never fork, re-skin or renumber one.** Every task in them is already shipped; a
re-skin adds no signal, because a model that can do the original can do the copy.

---

## Designing the question

**Make the answer derived, never stored.** If it exists in no record, full database access
still doesn't hand it over. This is the single highest-leverage rule and it is free. Before
writing the instruction: *if the model could read every table, would it know the answer?*

**Load at least two difficulty axes** — inference (can it work it out), execution (can it
carry a dependent chain), restraint (can it avoid breaking things). A task loading only
execution is a long-form instruction-following test.

**Levers, in order of signal per unit of effort:** Join (answer exists only in an
intersection) · Arbitration (sources conflict, one is authoritative) · Carry (value read in
A, written in B, grader recomputes from A live) · Restraint (negative space → guardrails) ·
Sequence (brittle — never gate on it).

**The load-bearing test:** for every app, remove it and see whether the answer changes. If
it doesn't, it's decoration. Measured in this repo: ≤3 apps gave a mean inter-model spread
of **0.413**; 7-app tasks gave **0.126**. Coupling is difficulty; breadth is not. The
AutomationBench corpus median is 4 apps.

**Novelty line** in `brief.md`: what does this ask that no existing task asks? If the
honest answer is "the same question on different data", change the lever, not the numbers.

---

## Writing the instruction

Register is AutomationBench's: measured over its 606 tasks, prompts run **11–192 words,
median 66**; apps 2/4/8; objectives 1/7/47; guardrails 0/5/38.

> **State the rules the agent could not reasonably discover. Push everything else into the
> fixture.** Length is an output of that decision, not a target.

**Business rules yes, UI coordinates never.** Even the 192-word corpus prompt names no cell
address. Dictating A34/B36/C36 converts judgment into transcription and makes the task
voidable by a typo.

Never enumerate the objectives — the rubric owns those. Say *that* some records are stale,
never *which*.

---

## Grading

**Check model.** Objectives are weighted and may be prefix-gated; guardrails pass by
default and **zero** the task on violation. Guardrails are never gated. The observed
corpus ratio of 0.65 is descriptive, not a quota. Every guard must enforce a genuine
negative obligation or protected state; never add copying work to fill a count.

**Bands:** ≤2 floor (~100% pass), 4–6 core (**30–70%**), 1–2 stretch (<30%).
**Only a check measured in the 30–70% band may gate anything.**

**Grade by per-check pass rate, never the rubric mean** — a mean hides both a check nobody
fails and a check nobody passes. Compute over *reachable* attempts: `gated_out` is not
`failed`, because a criterion that was never attempted says nothing about ability.

**Two mandatory gates before calibration:**
- **seed-zero** — every objective 0.0, every guardrail 1.0 on the untouched fixture
- **golden solution** — a correct end state scores 1.0

Plus adversarial cases: plausible-but-wrong outcomes must drop below 1.0, and correct-but-
untidy ones (a scratch tab, a renamed tab, unformatted numbers) must still score 1.0.

**Beware a saturated seed.** A realistic fixture contains years of the content your checks
look for — this repo's Gmail fixture holds 2,488 sent messages to the graded contact, 886
mentioning the task's subject and 51 naming the answer. Content matching cannot tell the
agent's work from the history. Use a **novelty predicate** (row id above the seed's
maximum), and record that maximum as a seed fact.

---

## Validity — every failure must be the model's

A zero caused by infrastructure, environment, grader defect, ambiguity or non-determinism
is a measurement error, and it is worse than a missing data point because it is
indistinguishable from a real result.

- A run with no `reward.json`, a state-fetch error, or an incomplete app set **did not
  score 0** — it produced no score. Void it, re-run it, record why.
- **Refuse before you run.** Check apps are reachable in `grader_fn`, *before* the criterion
  runner — `run_evaluation_criteria` catches per-criterion exceptions and records them as
  0.0, silently converting a refusal into the thing it was written to prevent.
- A guardrail that raises is treated as **intact**, not violated.
- `reward.json` must contain **numbers only**. A string or nested object is rejected
  downstream as a ValidationError and voids the trial — after the agent has run and been paid for.

---

## Harness facts

- **Agent tools:** screenshot, click, key, type, scroll, wait. `bash` is opt-in and OFF.
  That default protects nothing — the surface is the desktop, not the tool list.
- **Effort:** stock computer-1's `reasoning_effort` is a **no-op** on native CUA providers.
  Use `computer1_effort:Computer1Effort`, which injects `output_config={"effort":E}`
  (Anthropic) / `reasoning={"effort":E}` (OpenAI) and logs each injection.
- **Output tokens:** Anthropic `effort_max_tokens` default **128000** — a server hard wall
  (128001 → 400) that needs streaming, since the SDK refuses non-streaming above 21,333.
  OpenAI `openai_max_output_tokens` default **256000**.
- **Uncapped runs:** remove `agent.timeout_sec` from `task.toml` and pass `--step-cap 0`.
  A truncation reaching `reward.json` is indistinguishable from a task failure.
- **`task.toml` needs `schema_version = "1.4"`**, `[task].version` + `authors`,
  `[environment.healthcheck]`, and `[agent] user = "root"`. A 1.2 file resolves to no
  tasks and harbor dies with "Either datasets or tasks must be provided."

---

## Operational gotchas

- **`memory_mb = 16384`, not 8192.** The verifier parses the combined `/api/state`
  (~75 MB here); peak RSS runs several times the document. At 8 GB it is OOM-killed with
  no exception, no output and no `reward.json`.
- **`imagemagick` is required in the CUA image** — computer-1 shells out to `import` for
  every screenshot. Without it every trial dies on its first action with
  `Runtime action 'screenshot' failed (127)`.
- **Pin images by digest**, never a mutable tag, or runs from different weeks aren't
  comparable. Where the image is built per-host, pin the **fixture** by checksum instead.
- **Never clean up containers by image or with `docker ps -q`** — this box runs concurrent
  jobs. Kill by name, or by the campaign's own label.
- **Strip macOS AppleDouble files before shipping source to Linux.** `._*` files reach
  ESLint as TypeScript and fail the build with "Parsing error: Invalid character".
- **Two `keys.env` exist** (repo root and the box's `$HOME`) and they drift. Test the
  provider before launching; an expired token burns every retry and reports invalid trials
  rather than results.
- **`keys.env` is gitignored.** The repo root is inside a git repo covering all of
  `~/Downloads`; check what a commit would stage.

---

## Standing rules

- **Verify by execution.** Claims about what an environment does or refuses are worth
  nothing without the command and its output. This repo's history is a series of holes
  found only by probing something already declared closed.
- **Never claim a task is complete, flawless or fully hardened.** State what is verified
  and what is untested.
- **Run one smoke trial before any campaign.** A task that has never had a rollout can
  fail on something structural; find it on one trial, not twenty-four.
- **Freeze fixture + instruction + grader together.** Changing one without the others is
  how a task silently regresses: moving a gate onto an unclearable check took one task
  from 0.875/0.25 to 0.125/0.125.
