# Tune one task by one notch (B8)

You are retuning ONE task after a measurement. Work from the repo root and use bash.

- Repo root: {REPO}
- Task tree: {TASK_DIR}
- Task name and measured version: {TASK} {VERSION}
- The measurements (campaigns, gate reports, census logs) and the controller's notes: at the end of this prompt
- The plan brief, if any: {TASK_DIR}/authoring/PLAN.md
- Scratch parent for every temporary directory you make: {SCRATCH}

Run the authoring scripts and validate.py with the verifier's Python 3.11, resolved once from the repo root:

    PY311="$(python3 -I -c 'import runpy; print(runpy.run_path("production/tools/paths.py")["PY311"])')"

The goal is Arena's bar on a fresh 10 x 2 final: task pass@1 at most 0.5 on BOTH models, aiming at 0.1-0.3, with a
within-model pass/fail mix, at least 3 distinct scores per model and reward SD at least 0.08, free share at most
0.40, and no clock premise as the primary failure. You make ONE change per version, chosen from the measurement.

## Read first

1. `production/briefs/AUTHOR-BRIEF-B8.md`, especially §0, §5, §6.1-§6.8 (dials) and §8 (proofs).
2. The measurements and notes at the end of this prompt: open the gate reports and census logs they list. Work
   out, per premise and per model, the miss rate and whether misses were silent or voiced-and-rejected.
3. The task's `authoring/traps.json`, `authoring/DIAL.md`, `VALIDATION.md`, `REWARD-HACKING.md`.
4. The library entry of every premise you touch: `python3 -I production/traps/traplib.py show <id>`.
5. `production/PITFALLS.md`.

## Decide (write the reasoning at the top of DIAL.md)

- A premise missed in every pilot (3/3) or final (10/10) run of a model, with no blind reader or audit that reached it: STOP. Hand back "needs a
  blind reader before any dial". An unaudited 100% miss is presumed unfair.
- Pass@1 above 0.5 on a model: one notch harder on a decisive premise aimed at that model. For Fable, remove one
  by-the-way anchor (the measured dial is one anchor per notch). For Astra, change the KIND of evidence (a receipt
  line instead of a remark), not the amount.
- Flat (one score, or no full pass on a model): one notch easier on the constant premise. Add one by-the-way anchor
  that witnesses the event, in a file that no same-family anchor uses; for a Fable-aimed worked-figure convention,
  move the single figure closer to where the figure is reported. A too-specific anchor overshoots.
- A dead premise (0 misses on both models in the final): lower it to a filler (at most 5 points), or replace it with
  one library mode of a different family. A new trap is "pilot first": its first build rarely lands in band.
- Keep every Astra-aimed figure fixed unless the notes say Astra is the problem. One added discriminating worked
  figure has flipped an Astra-aimed convention from 10/10 missed to 0/5 missed.
- Never fix an ambiguity with a stated rule or definition. Fix it with a fact anchor. A stated rule kills the trap.
- Never delete a scope, exclusion or edge-case sentence to make the task harder. That produces ambiguity.

Make exactly ONE change: one dial notch, or one new or replaced trap.

## Build

- Edit {TASK_DIR} in place. Bump `task.toml [task] version` to the next minor version (never reuse a measured
  version number). Delete any `verification/` folder. The measured version's package stays in its campaign
  directories; never edit `envs-b6/_versions/`.
- Regenerate through the authoring scripts (byte-identical rebuild).
- Re-prove the changed premise in `authoring/validate.py` and `VALIDATION.md`: uniqueness, anchor ablation, an
  executed counterfactual, and a census of plausible wrong answers, each losing only its own check.
- Update `authoring/DIAL.md` (which sentence moved, from which notch to which, expected miss rate per model), the
  `difficulty_explanation` and, if the change touches the grader, `REWARD-HACKING.md`.

## Your gate

From {REPO}, run:

    python3 -I production/tools/b6ctl.py author-check {TASK_DIR}

Fix every item it lists and run it again until it prints READY.

## Limits

- Never launch or measure anything: no `b6ctl run`, `launch`, `rerun-void` or `ship`, and no arena, harbor, coder,
  measure or benchmark command.
- Edit only {TASK_DIR}. Never touch `pipeline/`, `production/tools/`, `production/traps/`, other tasks, campaign
  directories or `envs-b6/_versions/`.
- Never read or print `keys.env` or any credential. Never glob `/tmp`. Make scratch with `mktemp -d` under
  {SCRATCH} and remove only what you made. Use bash, not zsh.
- No sub-agents, no blind readers, no git commits, no attribution lines.
- Time box: 75 minutes. If author-check is still NOT READY at 65 minutes, stop and hand back its list verbatim.

## Hand back (at most 14 lines)

- the new version;
- the one change: file, the sentence or figure before and after, the premise and mode it belongs to;
- the expected miss rate per model for that premise, and the expected task pass@1 per model;
- why this change, citing the measured numbers;
- the author-check verdict line, verbatim;
- any risk (ambiguity, a priming anchor, a cascade).

## Measurements of {TASK} {VERSION}

{CAMPAIGNS}

## Controller notes

{NOTES}
