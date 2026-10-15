# Start here

One screen to your first task. Read [PITFALLS.md](PITFALLS.md) once. Runbook: [README.md](README.md); every
command: [tools/README-FLOW.md](tools/README-FLOW.md). Run everything from the repo root, in **bash** (not zsh).

## 1. Set up (once per machine)

```bash
cd "$(git rev-parse --show-toplevel)"
bash production/setup.sh                      # uv sync, Python 3.11, ./arena keys if missing, trap library, doctor
./arena dump --set <path to the trace dump>   # the Arena trace export you author from
export ARENA_POOLS=<your-coder-ws>[,<ws>...]  # YOUR OWN Coder workspaces; never one another checkout uses
python3 -I production/tools/b6ctl.py doctor   # repeat until it reports no FAIL; each FAIL prints its fix
```

## 2. Make your first task

Pick an unclaimed seed from [starter/README.md](starter/README.md). An "agent" step means: run the command, copy
the prompt it prints (macOS: append `| pbcopy`), open a **fresh** Claude Code session at the repo root, paste it.

```bash
export CLAUDE_SCRATCH="$(mktemp -d)"; SEED=<session id>; SLUG=<slug>; T="envs-b6/a_f1_$SLUG"
```

1. Scaffold: `python3 -I production/tools/b6ctl.py new "$SLUG" --level f1 --seed "$SEED" --plan "production/starter/plan/briefs/$SEED.md"`
   (`--level f0` if the seed's corrections do not ground your traps; then `T="envs-b6/a_f0_$SLUG"`).
2. Author (agent): `python3 -I production/tools/b6ctl.py prompt author "$T"`. Wait for its hand-back.
3. Check: `python3 -I production/tools/b6ctl.py author-check "$T"` must print READY. If not, paste the list into
   the author's session.
4. Pilot 5 x 2: `env -u ANTHROPIC_AUTH_TOKEN python3 -I production/tools/b6ctl.py run "$T" pilot` (launch, wait,
   voids re-run once, gate, census; one VERDICT line). Near miss or easy: tune (agent) with
   `python3 -I production/tools/b6ctl.py prompt tune "$T"` (it carries the measurements), then back to step 3.
5. Final 10 x 2: `env -u ANTHROPIC_AUTH_TOKEN python3 -I production/tools/b6ctl.py run "$T" final`.
6. Blind reader (agent, a FRESH session that never saw the authoring): `python3 -I production/tools/b6ctl.py prompt blind "$T" --out "$CLAUDE_SCRATCH"`.
   A multi-step task prints one prompt per step: one fresh session per step, in order. Then run the `blind-grade`
   command it printed.
7. Audit (agent, another FRESH session): `python3 -I production/tools/b6ctl.py prompt audit "$T"` (it carries the
   campaigns, gates, census and blind result). The auditor writes `production/state/audits/<task>-<version>.md`,
   ending in a `VERDICT` line.
8. Ship: `env -u ANTHROPIC_AUTH_TOKEN python3 -I production/tools/b6ctl.py ship "$T" --audit production/state/audits/<task>-<version>.md`
   (`next` prints it with the path filled in).
   It refuses without a SHIP or SHIP-WITH-DISCLOSURE verdict and a hard final. Uploading anywhere needs the user's go-ahead.

Lost at any point: `python3 -I production/tools/b6ctl.py next "$T"` prints the stage and the exact next command.
`run` and `ship` use one of your pools: the least busy in `$ARENA_POOLS`, or the one you name as the last argument.
Starting a stopped pool needs the workspace owner's approval.

## 3. The bar (Arena, 2026-10-15)

- task pass@1 **<= 0.5 on both** Fable 5.1 (Claude Code) and GPT-6 Astra (Codex), high effort, no limits, on a
  fresh 10 x 2 final; **aim at 0.1-0.3**, not a flat 0/10;
- a within-model pass/fail mix and varied failures (per model: >= 3 distinct scores, reward SD >= 0.08);
- free share **<= 0.40** (decisive premises carry >= 60 of each step's 100 points);
- no clock trap as the primary failure; no trap family leading more than about 25% of a batch;
- a blind reader and a §14 audit (SHIP or SHIP-WITH-DISCLOSURE) before anything ships.

## 4. When stuck

1. `python3 -I production/tools/b6ctl.py doctor`: fix every FAIL first.
2. `python3 -I production/tools/b6ctl.py next "$T"`: where you are and what to run.
3. [PITFALLS.md](PITFALLS.md): the 20 mistakes that cost the most.
4. Never: edit `pipeline/` while campaigns run, print a key, glob `/tmp`, loop in zsh, re-run a scored run.
