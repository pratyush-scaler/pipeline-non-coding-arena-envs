# Task flow: authoring hand-off to zip (B6 flow, paths updated for production/ on 2026-10-15)

The one-page runbook is `production/README.md`; this page is the command-level detail for the controller.

Run every command in **bash**. Quote every path, and never write `for x in $LIST`: zsh does not word-split.
Each tool that writes scratch makes its own `mktemp` dir, so parallel agents never share one. Never use a fixed
`scratch-<name>` folder and never glob `/tmp`. `b6ctl` exit codes: 0 ok, 1 failed, 2 nothing to act on or bad input,
3 refused or void, 124 timeout. **STOP** marks a point where a human or the audit decides.

Every path below comes from `production/tools/paths.py`: the repo root is the parent of `production/` (override with
`ARENA_ROOT`), task trees live in `envs-b6/` (`ARENA_TASKS`), campaign output in `pipeline-artifacts/b4/`, and the
ledger, gate reports, quarantined receipts and run ids in `production/state/` (`ARENA_STATE`, `ARENA_LEDGER`).

```bash
R="$(git rev-parse --show-toplevel)"         # the repo root
TOOLS="$R/production/tools"
B6="$TOOLS/b6ctl.py"
T="$R/envs-b6/<name>"                        # live tree; the author has already bumped task.toml [task] version
V=<version>                                  # that version
A="$R/pipeline-artifacts/b4/<name>-$V"       # campaign prefix: "$A-pilot-fable", "$A-final-astra-rerun<ts>", ...
SCR="${CLAUDE_SCRATCH:?set CLAUDE_SCRATCH}"  # parent dir for reader workspaces and staging copies
```

## Before any campaign

0. `python3 -I "$B6" author-check "$T"`: the author's own last gate (check with `design_lint --b8`, validate, tree
   hygiene). It prints READY or NOT READY with every failing item and its fix. **STOP** unless READY.
1. `python3 -I "$B6" check "$T"`: moves stale `verification/` receipts to `production/state/stale-receipts/<name>-<old>-<ts>/`
   and never deletes them. Then it runs design_lint (with additivity) and selftest on a mktemp copy.
   **STOP** on a non-zero exit: back to the author.
2. `python3 -I "$B6" validate "$T"`: the tree's own `authoring/validate.py`, with its arguments read from its usage
   line. It runs under py3.11 `-I -B` on a mktemp copy. **STOP** on a non-zero exit (the log path is printed).
3. `python3 -I "$B6" preflight`: prints `ANTHROPIC_API_KEY <code>` and `OPENAI_API_KEY <code>`.
   **STOP** on anything but 200: a human fixes `keys.env`. Never paste or print a key.

## Pilot (5 x 2 + oracle/nop)

4. `python3 -I "$B6" launch "$T" pilot [<your pool>]`: the preflight runs again, and the launch is refused on a
   non-200 (`--no-preflight` overrides; `--dry-run` only prints the measure.py command).
5. `python3 -I "$B6" wait "$T" pilot`: run it under the background runner, with no `&`. It exits 0 when done,
   3 when void (it prints the rerun-void command) and 124 at `--max`; if it times out, run it again.
6. On a void: `python3 -I "$B6" rerun-void "$T" pilot astra` (preflight first), then repeat step 5.
   Infra loss is re-run; scored runs never are.
7. `python3 -I "$B6" gate "$T" pilot`, then the verdict column of
   `"$R/.venv/bin/python" -B "$TOOLS/measure.py" table`.
   **STOP**:
   - PILOT HARD: go to step 8 (census), then the final (step 9).
   - near: harden. The author bumps the version and you return to step 0.
   - easy: tune or retire.
8. `python3 -I "$TOOLS/census_answers.py" --deep "$T" "$A-pilot-fable" "$A-pilot-astra"`. Add any `-rerun<ts>`
   dirs by name. **STOP** if a full-reward run differs from the reference: that is a grader defect, and the task
   goes back to the author.

## Final (fresh 10 x 2, same version)

9. Run `python3 -I "$B6" launch "$T" final`, then `wait "$T" final` and, on a void, `rerun-void "$T" final <model>`.
10. Run `gate "$T" final` and then census (step 8) on `"$A-final-fable" "$A-final-astra"`.
    **STOP**: FINAL HARD with a clean census goes to the blind reader and audit. Anything else is a human call.

## Blind reader and audit (after the final; after the pilot too when a trap was missed 5/5)

11. `python3 -I "$B6" blind-prep "$T" --out "$SCR"`. Paste the printed prompt into ONE Opus agent. For a
    multi-step task, use one fresh agent per step, in the printed order, on the same workspace.
12. `python3 -I "$B6" blind-grade "$T" "<WORKSPACE>"`: per step, the reward and failed checks. A step with no
    deliverable is "not present", not zero.
13. Audit: an independent auditor follows `production/briefs/AUDIT-BRIEF-B6.md`, using the step-11/12 result as its
    reader. **STOP**: the verdict is SHIP, SHIP-WITH-DISCLOSURE or WITHHOLD. On WITHHOLD the task goes back to the
    author. Only SHIP or SHIP-WITH-DISCLOSURE goes to packaging.

## Package

14. Freeze the measured version: `cp -R "$T" "$R/envs-b6/_versions/<name>-$V"`. Do not edit `_versions/` after this.
15. Run the harbor check on the frozen copy. It is an LLM trial of about 2.5 min on a pool:
    `env -u ANTHROPIC_AUTH_TOKEN "$R/.venv/bin/python" -B "$TOOLS/tc_path.py" launch "$R/envs-b6/_versions/<name>-$V" <your pool>`.
    Then `... tc_path.py pull "$R/envs-b6/_versions/<name>-$V" <your pool> <run>`, with the run id from
    `production/state/tc_path_runs.json`. Repeat the pull while it says "no receipt yet". The pull installs only a
    receipt bound to that tree's identity. **STOP** if the receipt fails: the human decides.
16. Stage a copy under its live name, in a fresh mktemp dir, and assemble from it:
    ```bash
    STAGE="$(mktemp -d "$SCR/stage-XXXXXX")"
    cp -R "$R/envs-b6/_versions/<name>-$V" "$STAGE/<name>"
    env -u ANTHROPIC_AUTH_TOKEN "$R/.venv/bin/python" -B "$TOOLS/assemble_b4_zip.py" "$STAGE/<name>" \
      --fable "$A-final-fable" --astra "$A-final-astra" --oracle "$A-pilot-oracle" --nop "$A-pilot-nop" -o "<zip dir>"
    ```
    Add `--fable/--astra "$A-final-<model>-rerun<ts>"` for each rerun. The assembler refuses on a mismatch and
    leaves `<name>.zip.invalid`. **STOP** on a refusal.
17. Inventory and report:
    - `ls -la "<zip dir>"`;
    - `python3 -I "$TOOLS/ledsum.py" --grep <name>`;
    - append the verdict line to the batch's genuineness log (`production/state/genuineness.md`).

    **STOP**: uploading to Drive or the tracking sheet needs the user's go-ahead.

## Tests

- `cd "$TOOLS" && python3 -I -m unittest`: the fast suites (design_lint B8 rules + author-check, plan_batch) on
  copies of `production/templates/reference-task-suitcase-2.6.0` and the synthetic library in
  `production/traps/fixtures/`. `cd "$R/production/traps" && python3 -I -m unittest` tests traplib.
- `python3 -I -B "$TOOLS/test_b6ctl.py" --out "$SCR"` exercises every b6ctl subcommand without pools. It runs the
  real preflight, works on copies of `envs-b6/_versions/a_f1_gst-workbook-answer-key-1.7.0` and a multi-step tree,
  and blocks any measure/coder/harbor/tc_path call in-process. Those trees and the ledger it reads must exist in
  this workspace (or point `ARENA_ROOT`, `ARENA_TASKS`, `ARENA_LEDGER` at one that has them; put `ARENA_STATE` in
  scratch). Under unittest it is opt-in: `B6CTL_FULL_TEST=1`.
