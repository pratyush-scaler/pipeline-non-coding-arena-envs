# Non-coding Arena environments: production pipeline

This repo builds **extremely hard, clean, non-coding RL tasks** for Arena from Arena's agent traces. Examples are
registers, reconciliations, answer keys, schedules and reviews over a folder of documents. Each task is graded by
deterministic checks and calibrated on two frontier agents:

- **Fable 5.1** in Claude Code;
- **GPT-6 Astra** in Codex.

Both run at high effort, with no turn or time limits.

A task ships only when all of these hold:

- it is hard on both models;
- every failure is the model's own;
- the grader is clean;
- the package matches Arena's requirements.

The production line in `production/` takes you from a trace to a shipped zip with a handful of commands.

---

## 1. Set up (once per machine)

Use **bash** (not zsh), and run everything from the repo root.

```bash
bash production/setup.sh                        # uv sync, Python 3.11, ./arena keys if missing, trap library, doctor
./arena dump --set <path to the Arena trace dump>
export ARENA_POOLS=<your-coder-ws>[,<ws>...]    # YOUR OWN Coder workspaces, never another person's
python3 -I production/tools/b6ctl.py doctor     # repeat until it reports no FAIL; every FAIL line prints its fix
```

- **Keys** live in `keys.env` (mode 600), written by `./arena keys`. Never print or paste a key.
- **Launch commands:** prefix every command that touches a pool with `env -u ANTHROPIC_AUTH_TOKEN`. An inherited
  session token overrides `keys.env`.
- **Pools:** a Coder pool holds one code hash, so two checkouts sharing a pool refuse each other's campaigns. Use your
  own.

---

## 2. Make one task: the whole flow

```bash
export CLAUDE_SCRATCH="$(mktemp -d)"
SEED=<session id>; SLUG=<short-slug>; T="envs-b6/a_f1_$SLUG"
B="python3 -I production/tools/b6ctl.py"
```

| # | step | command | done when |
|---|---|---|---|
| 1 | Scaffold the task | `$B new "$SLUG" --level f1 --seed "$SEED" --plan production/starter/plan/briefs/$SEED.md` | the task folder exists at 1.0.0 |
| 2 | Author it (agent) | `$B prompt author "$T"`, then paste the prompt into a **fresh** Claude Code session | the author hands back |
| 3 | Pre-check | `$B author-check "$T"` | it prints **READY**; otherwise each item comes with its fix |
| 4 | Pilot, 3 x 2 | `env -u ANTHROPIC_AUTH_TOKEN $B run "$T" pilot` | **PILOT HARD** (pass@1 <= 0.5 on both, clean controls and census; nothing else earns a final); if near or easy, tune: `$B prompt tune "$T"` -> back to step 3 |
| 5 | Final, 10 x 2 (only after PILOT HARD) | `env -u ANTHROPIC_AUTH_TOKEN $B run "$T" final` | **FINAL HARD** with a clean census |
| 6 | Blind reader (agent) | `$B prompt blind "$T" --out "$CLAUDE_SCRATCH"`, then `$B blind-grade "$T" <workspace>` | the reader reaches the reference, or every miss is shown to be the reader's |
| 7 | §14 audit (agent) | `$B prompt audit "$T"`, run in another **fresh** session | `production/state/audits/<task>-<version>.md` ends `VERDICT …: SHIP` or `SHIP-WITH-DISCLOSURE` |
| 8 | Ship | `env -u ANTHROPIC_AUTH_TOKEN $B ship "$T" --audit production/state/audits/<task>-<version>.md` | harbor passes and the zips are written |

**Lost?** Run `$B next "$T"`. It prints the task's current stage and the exact next command.

**Agents:**
- Each agent step runs in its own **fresh** session.
- The blind reader and the auditor must never have seen the authoring.
- On a multi-step task, `prompt blind` prints one prompt per step. Run them in order, each in a fresh session, on the
  same workspace.

---

## 3. The bar (Arena's requirements)

| requirement | how we measure it |
|---|---|
| Hard | task pass@1 **<= 0.5 on both** models on a fresh 10 x 2 final; we aim for **0.1-0.3** |
| Varied failures | per model and step: >= 3 distinct scores and reward SD >= 0.08 (not FLAT); ideally some full passes too |
| Low free points | free share **<= 0.40**: checks no run ever misses carry at most 40 of 100 points |
| Trap diversity | no trap family leads more than about 25% of a batch; **no clock trap as the primary failure** |
| Clean | no grader defect, no double charge, no leak in the instruction, no reward-hacking route, no voids counted |
| Honest docs | task.toml, `tools.json` and the docs describe the shipped package exactly |
| Multi-step | later steps' files are hidden until their step starts (`steps/<step>/workdir/`); every step's instruction is self-contained |
| Faithfulness | **F1** only if the trace's own correction is something the models then fail; otherwise **F0** |

---

## 4. Traps: what makes a task hard

**Read `production/traps/TRAP-LIBRARY.md`.** It lists 44 trap modes. Each one's status is *computed* from our
measured runs, not asserted.

```bash
python3 -I production/traps/traplib.py list --status proven       # what reliably bites
python3 -I production/traps/traplib.py show T1                    # recipe, proof obligations, known hazards
```

**What we measured:**

- **Models read every file.** Hiding facts, adding volume or planting decoys does nothing.
- **Stated rules never bite.** They were missed 0 of 1,530 times.
- **What works** is a record the model must *reverse* from evidence:
  - a keying slip;
  - a misfiled note;
  - a convention fixed by one worked figure;
  - a tax or pack basis cued on the record itself;
  - a rule over-applied beyond its scope.
- **Proven modes:** T1, T3, T5 and T12.
- **Pilot first:** literature (L) and trace-derived (R) modes have no runs in our harness yet.
- **Combine traps:** use >= 3 decisive traps from >= 2 families, with at least one aimed at each model. One trap
  alone gives flat scores.
- **Prove every trap** in the task's `authoring/validate.py`:
  - **uniqueness:** only one answer fits the files;
  - **ablation:** remove an anchor and the answer becomes undetermined;
  - **counterfactual:** flip the fact and the answer flips;
  - **census:** each wrong reading loses only its own checks.

**Derive traps from the trace.** A frontier model's real reconciliation error, which the user then corrected, is the
best seed.

```bash
python3 -I production/tools/trace_traps.py scan --list ids.json --exclude production/starter/used_session_ids.json --out "$CLAUDE_SCRATCH/scan"
python3 -I production/tools/trace_traps.py report "$CLAUDE_SCRATCH/scan"
python3 -I production/tools/plan_batch.py seeds.json --out "$CLAUDE_SCRATCH/plan"   # 3-5 trap modes per seed, diversity quotas
```

**Read every seed yourself.** The miner's score finds candidates, but it does not predict difficulty.

A ready-made **starter batch** of 16 planned seeds from the Oct-13 dump is in `production/starter/`.

---

## 5. Rules that save hours

The full list is in [`production/PITFALLS.md`](production/PITFALLS.md).

1. **Run `$B doctor` first.** It catches dead keys (401), a missing Python 3.11, an unset `ARENA_POOLS`, a missing
   dump and the inherited-token trap.
2. **Decide on 10 x 2 finals, not 3-run pilots.** A pilot is triage only, and only a pilot that meets the bar earns a final (user, 2026-10-16).
3. **Re-run void runs, never scored runs.** Infrastructure loss is re-run with `$B rerun-void`. Re-running a scored
   run until the number improves is not allowed.
4. **Any change to `task.toml`, `environment/` or `tests/` changes the task's identity.** It then needs a fresh final,
   an audit and harbor.
5. **Keep graded values and IDs out of instruction examples**, including anything after "such as" or "e.g.".
6. **Make `tools.json` declare the real deliverables.** `author-check` enforces this; fix with
   `python3 -I production/tools/fix_tools_json.py "$T"`.
7. **Treat an unaudited 100% miss as unfair until a blind reader and the audit say otherwise.**
8. **Never edit `pipeline/` while campaigns run.** Never glob `/tmp`, and never use zsh loops.

---

## 6. Where things live

```
production/
  START-HERE.md        one screen: setup, first task, the bar
  README.md            the runbook in more detail; tools/README-FLOW.md has every command
  PITFALLS.md          the most expensive mistakes, each with its fix
  briefs/              AUTHOR-BRIEF-B8.md (authoritative), AUDIT-BRIEF-B6.md, REAUDIT-BRIEF-B7.md
  prompts/             agent prompt templates (author, tune, audit, blind), filled by `b6ctl prompt`
  traps/               trap library (library.json, TRAP-LIBRARY.md), traplib.py, build_evidence.py
  tools/               b6ctl.py (the controller), design_lint, trace_traps, plan_batch, fix_tools_json, measure
  templates/           skeleton/ (new tasks) and reference-task-suitcase-2.6.0/ (a shipped task that met the bar)
  starter/             16 planned seeds from the Oct-13 dump, plus the session ids already used
  research/            the evidence behind the trap library (internal, external, trace yield)
  state/               your local ledger, gates, audits and deliveries (gitignored)
pipeline/              the underlying pipeline and Harbor integration (the `./arena` CLI)
rulesets/              authoring rules, incl. ANTI_REWARD_HACKING.md
envs-b6/               your task trees (gitignored); envs-b6/_versions/ holds frozen shipped versions
pipeline-artifacts/b4/ calibration campaigns (gitignored)
```

---

## 7. Tests

```bash
(cd production/tools && python3 -I -B -m unittest discover -s .)    # controller, lint, planner, miner, workflow
(cd production/traps && python3 -I -B -m unittest discover -s .)    # trap library and evidence builder
.venv/bin/python -B -m unittest discover -s pipeline/tests -t .      # the underlying pipeline
```

---

## 8. Under the hood: the `./arena` CLI

The production line drives the pipeline in `pipeline/`. You rarely call it directly.

| command | what it does |
|---|---|
| `./arena keys` | write `keys.env` |
| `./arena dump --set <path>` | point at a trace dump (there is deliberately no default) |
| `./arena status` | show what is configured |
| `./arena coder prepare <ws> --no-data` | prepare your own calibration pool (needs the workspace owner's go-ahead) |

The pipeline's own documentation: `pipeline/README.md` and `pipeline/PRODUCTION.md`.
