# Unblock-and-harden brief (2026-10-15)

> **History (2026-10-15).** Superseded as instructions by `AUTHOR-BRIEF-B8.md`; kept for the measurements and reasoning behind its rules. Paths below are the old workspace layout (`$W/research/batch4/...`): in this repo the tools are in `production/tools/`, the briefs in `production/briefs/`, the templates in `production/templates/`, and trap modes come from `production/traps/TRAP-LIBRARY.md`.

Your task is BLOCKED: it was never shipped, because a tune failed (one model solves it) or an audit withheld it. The user wants it unblocked, fixed and made **extremely hard for BOTH models**, while staying clean.

Read first, all binding:
1. `W/research/batch4/b7/TRAP-CATALOG-B7.md`: templates T1–T8, the §4 "reverse a record" recipe, the dead and bimodal lists, the measurement protocol.
2. `W/research/batch4/b6/TUNE-BRIEF-B6v6-proven.md` (round 3) and `TUNE-BRIEF-B6v5-stochastic.md` with its addenda: validity rules, gates, DIAL.md.
3. `W/research/batch4/b7/research/TRAJ-loopholes.md` §3–§7: how each model fails, in its own words.
4. Every line about your task in `W/research/batch4/b6/genuineness.md`, plus its latest gate files in `W/research/batch4/b6/gates/<task>-<ver>-<stage>.json`.

## Steps
1. **Diagnose.** Work out which premises bit which model, which were dead, and why the task was blocked. Check any premise missed 100% by a model against the "presumed ambiguous until a blind reader says otherwise" rule. If one can be argued, fix it with a FACT anchor (never a stated definition or rule) before hardening.
2. **Harden.**
   - Target, measured 10×2 (ARENA'S BAR, user 2026-10-15): pass@1 ≤ 0.5 on BOTH models, aiming at 0.1–0.3, with at least two decisive traps biting each model, some passing runs and varied failure patterns. Do NOT chase ≤ 0.2: it pushes tasks toward the flat 0/10 shape Arena criticised. Free share ≤ 0.40.
   - Build each new trap from a catalogue template, re-instantiated in this task's own material with the source's ingredients.
   - **Fable** reliably misses: record reversal (T1 with 2+ parties plus an impossibility), T3 tax-inclusive or per-pack with a tally on the record, T4 already-in-hand via a technical bridge.
   - **Astra** reliably misses: cross-document identity chains (T1), a filed column copied without deliberation, a line transposition settled by first-hand descriptions, and sometimes a T2 single discriminating figure. T2 transferred to only 1 of 7 new tasks in round 3, so do not rely on it alone.
   - Keep traps genuine:
     - no printed form or table may state the opposite of the answer;
     - no sentence may give the record priority;
     - grade the removal side against a conserved total, so a union answer loses.
3. **Prove** each new or changed trap in `VALIDATION.md` and `validate.py`: uniqueness, anchor ablation, an executed counterfactual, and a census of plausible wrong answers, each losing only its own check.
4. **Gates.**
   - `python3 -I W/research/batch4/b6/tools/b6ctl.py check <tree>`: DESIGN GATE PASS (traps.json premises carry `"decisive": true` and a catalogue `"template"`) and selftest 0 BAD.
   - `python3 -I W/research/batch4/b6/tools/b6ctl.py validate <tree>`: exit 0.
   - No `__pycache__` and no `verification/`.
   - DIAL.md lists every dial sentence.
   - REWARD-HACKING.md and the task.toml difficulty_explanation are updated.

## Where
- Copy the base tree named in your prompt to `W/envs-b6/_v6/<task>` and bump to the version named in your prompt.
- Never edit `_versions/` or the live tree.

## Hand back (≤ 14 lines)
- per decisive trap: the template, the documents, the default wrong answer, the weight and the expected miss rate per model;
- what you fixed for validity;
- the expected free share;
- the gate results;
- any risk.

## Limits
- No launches of any kind; no pool, arena, harbor, coder or measure commands.
- Never read keys.env.
- Never glob /tmp; use `mktemp -d` and remove only what you created.
- No subagents and no attribution lines.
- zsh does not word-split, so use bash scripts or Python.
