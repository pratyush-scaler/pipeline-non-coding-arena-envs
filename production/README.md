# Production line: extremely hard, clean, non-coding tasks from the trap library

> **New here? Start with [START-HERE.md](START-HERE.md).** One screen: setup, your first task, the bar, and what to
> do when stuck. Then [PITFALLS.md](PITFALLS.md), the agent prompts in [prompts/](prompts/), and the starter batch
> in [starter/README.md](starter/README.md).

One page for a teammate running a batch. Command-level detail: `tools/README-FLOW.md`. What to build and how:
`briefs/AUTHOR-BRIEF-B8.md` (authoritative; the other briefs are history). Which traps exist and how well each one
bites: `traps/TRAP-LIBRARY.md`.

## The bar (Arena, user 2026-10-15)

- task **pass@1 <= 0.5 on both** Fable 5.1 (Claude Code) and GPT-6 Astra (Codex), high effort, no limits, on a fresh
  10 x 2 final; **aim at 0.1-0.3** (a flat 0/10 is not the goal);
- a **within-model pass/fail mix** and **varied failures** (several distinct scores per model, SD >= 0.08);
- **free share <= 0.40** (decisive premises carry >= 60 of each step's 100 points);
- **no clock trap as the primary failure**; **no trap family heaviest in more than ~20-25% of a batch**;
- every failure the model's own: blind reader + §14 audit before anything ships.

## Setup (once per machine / worktree)

```bash
cd "$(git rev-parse --show-toplevel)"
./arena keys                                    # prompts, writes keys.env at mode 600; never print or paste a key
uv sync                                         # .venv from uv.lock: measure.py and the pool tools run under it
uv python install 3.11                          # the verifier's python3.11 (or set ARENA_PY311=/path/to/python3.11)
python3 -I production/tools/b6ctl.py preflight  # ANTHROPIC_API_KEY 200 and OPENAI_API_KEY 200, nothing else
python3 -I production/traps/traplib.py build    # library.json + TRAP-LIBRARY.md from traps/modes-*.json
```

- **Pools** are Coder workspaces, and each teammate uses **their own**: `export ARENA_POOLS=<ws>[,<ws>...]`.
  Prepare one once with `./arena coder prepare <ws> --no-data`; that needs the workspace owner's go-ahead.
  Never share a pool with another checkout: a pool holds one code hash, so two checkouts refuse each other's
  campaigns. `doctor` FAILs while `ARENA_POOLS` is unset, and `run` will not auto-pick a pool without it. Launch every pool-touching command as `env -u ANTHROPIC_AUTH_TOKEN ...`: an inherited session
  token beats `keys.env` and has reached campaigns before. Never edit `pipeline/` while campaigns run (the pools refuse
  a changed code hash), and calibrate from one process.
- Paths come from `tools/paths.py`. Task trees: `envs-b6/`; campaigns: `pipeline-artifacts/b4/`; ledger, gate reports,
  quarantined receipts, run ids and plans: `production/state/` (per workspace, never committed). Override with
  `ARENA_ROOT`, `ARENA_TASKS`, `ARENA_STATE`, `ARENA_LEDGER`, `ARENA_LIBRARY`, `ARENA_PY311`.
- The library: `traps/build_evidence.py` regenerates `modes-internal.json` from campaigns and audits; research writes
  `modes-external.json`, `tools/trace_traps.py` mining writes `modes-trace.json`; `traplib.py build` validates and merges
  them (a schema error refuses the build). Read a mode with `traplib.py show T1`, filter with
  `traplib.py list --status proven --aimed-at astra`.

## Flow for one batch (bash, never zsh; quote every path; `mktemp -d` scratch; never glob /tmp)

| # | step | command (from the repo root; `T=envs-b6/<task>`) | stop unless |
|---|---|---|---|
| 1 | pick traces | unused sessions of the current dump (`./arena dump --set <dump>`), non-coding deliverables only | the request supports a document a reader can check |
| 2 | mine trap signals | `python3 -I production/tools/trace_traps.py scan --list ids.json --out production/state/trace/<batch>` then `... report production/state/trace/<batch>` | seeds with several corrections or a mid-session requirement change |
| 3 | plan the batch | `seeds.json` = `[{"seed", "domain", "trace_traps": "<.../sessions/<id>.json>"}]`; `python3 -I production/tools/plan_batch.py seeds.json --out production/state/plans/<batch>` | `PLAN OK` (exit 1 = a seed unplanned or a lead quota relaxed: change the seed list) |
| 4 | author | one author per seed with `briefs/AUTHOR-BRIEF-B8.md` + `production/state/plans/<batch>/briefs/<seed>.md` | the author hands back READY |
| 5 | author-check | `python3 -I production/tools/b6ctl.py author-check "$T"` | **READY** (every failing item comes with its fix) |
| 6 | pilot 3 x 2 | `b6ctl.py launch "$T" pilot`, `wait "$T" pilot`, `gate "$T" pilot`, `tools/census_answers.py --deep "$T" <pilot dirs>` | PILOT HARD (both pass@1 <= 0.5: at most 1 of 3 full per model; clean controls) and a clean census: only then a final (`b6ctl` refuses one otherwise; user 2026-10-16). A trap missed 3/3 gets a blind reader before any dial |
| 7 | final 10 x 2 | `b6ctl.py launch "$T" final`, `wait`, `gate "$T" final`, census | FINAL HARD (pass@1 <= 0.5 both) with a mix and a clean census |
| 8 | blind reader | `b6ctl.py blind-prep "$T" --out "$SCR"` -> one fresh Opus reader per step -> `b6ctl.py blind-grade "$T" <ws>` | the reader reaches the reference, or each miss is shown to be the reader's |
| 9 | §14 audit | an independent auditor with `briefs/AUDIT-BRIEF-B6.md` (and `REAUDIT-BRIEF-B7.md` on a disputed verdict) | SHIP or SHIP-WITH-DISCLOSURE |
| 10 | harbor | freeze `cp -R "$T" envs-b6/_versions/<task>-<v>`; `env -u ANTHROPIC_AUTH_TOKEN .venv/bin/python -B production/tools/tc_path.py launch|pull ...` | the receipt is installed and passes |
| 11 | zip | stage a copy, `env -u ANTHROPIC_AUTH_TOKEN .venv/bin/python -B production/tools/assemble_b4_zip.py ...`; `python3 -I production/tools/batch_diversity.py envs-b6/_versions/<shipped>...` | a `.zip`, not `.zip.invalid`; BATCH DIVERSITY PASS |

Voids (`wait` exit 3) are infrastructure loss: `b6ctl.py rerun-void "$T" <stage> <model>` re-runs them. A scored run is
never re-run. A near miss at the pilot goes back to the author for one dial notch and a new version (back to step 5).
Uploading zips to Drive or the tracking sheet needs the user's go-ahead.

## Tests

```bash
(cd production/tools && python3 -I -m unittest)   # design_lint B8 + author-check, plan_batch (about a minute)
(cd production/traps && python3 -I -m unittest)   # traplib
python3 -I -B production/tools/test_b6ctl.py --out "$SCR"   # every b6ctl subcommand, no pools; needs envs-b6/_versions
```
