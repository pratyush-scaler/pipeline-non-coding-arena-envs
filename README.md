# arena-envs-tasks-large-dump

> **New here? Start with [production/START-HERE.md](production/START-HERE.md).** One screen: setup, your first
> task, the bar, and what to do when stuck. Then read [production/PITFALLS.md](production/PITFALLS.md) and pick a
> seed from the starter batch in [production/starter/README.md](production/starter/README.md).

Workspace for building non-coding professional knowledge-work RL environments
from Arena agent traces, at batch scale.

Production qualification and operating instructions are in
[pipeline/PRODUCTION.md](pipeline/PRODUCTION.md). `build` authors and grades a
batch, then screens every validated task (5 episodes on each calibration model)
and stops with a pass@1 / pass@4 / mean-reward table and a hardening outlook.
Hardening is manual; `qualify` runs the ten-episode, two-model calibration of
record for any task whose screen measured cleanly -- pass@1 < 0.5 is the strict
target and blocks nothing. Only a current accepted
release receipt qualifies a task. Legacy `envs-cat` bundles require rebuilding
and remeasurement.

Separate from `arena-envs` on purpose: that workspace holds the first delivery
(kw-001…kw-006) and the artifacts of a smaller run. This one starts clean, works
on its own dump, and shares only the pipeline code and the rulesets.

## Start here

```bash
./arena keys                 # reads keys.env, or prompts and writes it (mode 600)
./arena dump --set /path/to/dump
./arena status               # what is configured, selected and built
```

Then the pipeline:

```bash
./arena select               # index -> screen -> tier -> classify -> shortlist
./arena build -n 3           # author + grade the batch, then screen it (5 x 2) and stop
./arena build -n 3 --no-calibrate            # author + grade only; no solver episodes
./arena screen envs          # (re-)screen a tree; --report-only reprints the table
./arena gate envs/<slug>     # re-run the gate chain over one bundle
./arena harden envs/<slug> --apply           # manual: revise, then screen the revision
./arena qualify envs/<slug>  # 10 x 2 calibration of record -- after a clean screen
```

For a new batch with ten **qualified** tasks in each category, use the
[category batch controller](CATEGORY_BATCH.md):

```bash
.venv/bin/python category_batch.py --out envs-cat-v2 \
  --work pipeline-artifacts/envs-cat-v2 --per-category 10
```

It excludes prior source families, preserves unsuccessful candidates separately,
and reports live counts in `envs-cat-v2/STATUS.md`. A frozen pipeline snapshot
allows it to run alongside an existing repair. The batch closes only after
every task passes qualification and review against the complete new corpus.

`arena dump` reads `ARENA_DUMP`, then `workspace.toml`, then fails with
instructions. There is deliberately no default: a pipeline that quietly indexes
last month's corpus produces results that look entirely normal.

## Layout

```
pipeline/            the pipeline itself (see pipeline/README.md)
rulesets/            authoring rules -- read before designing anything
ref_files/           Arena's spec, Arena's feedback on delivery 1, benchmark sheets
reference/
  kw-007-…/          a bundle that passes all 15 gates -- the worked example
  prior-delivery/    what the first delivery measured and what came back
  automationbench-pipeline/   the earlier gate runner and atlas, for reference
envs/                built environments (gitignored)
pipeline-artifacts/  index, tiers, classifications, batch reports (gitignored)
```

## Read before authoring

| file | why |
|---|---|
| `rulesets/ANTI_REWARD_HACKING.md` | §0 is a design decision that cannot be retrofitted |
| `rulesets/PLAYBOOK_GENERAL.md` | the nine stages, levers, check model, bands |
| `ref_files/Feedback for Scaler…docx` | the nine defects delivery 1 shipped; seven are now gates |
| `reference/prior-delivery/TRACE-ASSESSMENT.md` | what this corpus actually contains |

The reference corpora are for learning how tasks are built. Never fork, re-skin
or renumber one: every task in them is already shipped, and a re-skin adds no
signal because a model that can do the original can do the copy.

## What this workspace enforces

Two faithfulness floors, both tier-scaled, both gated:

| tier | fixture source fidelity | trace corrections used |
|---|---:|---:|
| 1 replay-ready | ≥ 95% | ≥ 70% |
| 2 largely lifted | ≥ 90% | ≥ 55% |
| 3 lifted with support | ≥ 85% | ≥ 40% |
| 4 minimum viable | ≥ 80% | ≥ 30% |

Below 80% source fidelity a trace is discarded rather than synthesised. Exact
copies and mechanically verified calendar anonymization receive full source
credit; other derived files receive half credit and authored files receive none.
Exact-copy reuse is reported separately. Anonymization also requires independent
privacy and calendar-semantic review; see [the policy](pipeline/PRODUCTION.md#verified-calendar-anonymization).

Traps scale with the trace — floor of 5, expectation
`0.5·surfaces + 0.5·corrections + 0.25·objectives` — and every trap must drive a
declared check and have a probe that scores strictly below the reference.

Seventeen gates run before any rollout budget is spent, because all nine defects
returned on the first delivery were pre-calibration defects that no number of
rollouts would have found.
