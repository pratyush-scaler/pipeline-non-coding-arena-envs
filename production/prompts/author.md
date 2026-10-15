# Author one task (B8)

You are authoring ONE non-coding task for the Arena production line. Work from the repo root and use bash.

- Repo root: {REPO}
- Task tree (already scaffolded by `b6ctl new`): {TASK_DIR}
- Task name and version: {TASK} {VERSION}
- Seed session: `source_trace` in {TASK_DIR}/task.toml (also the title of the plan brief)
- Plan brief and controller notes: at the end of this prompt (the brief is also {TASK_DIR}/authoring/PLAN.md)
- Scratch parent for every temporary directory you make: {SCRATCH}

Run everything the verifier would run with its Python 3.11, resolved once from the repo root:

    PY311="$(python3 -I -c 'import runpy; print(runpy.run_path("production/tools/paths.py")["PY311"])')"
    "$PY311" -I -B <script> ...

The task must be extremely hard for both calibration models, clean (every failure is the model's own) and
learnable (a model's runs score differently). The deliverable is a document a careful reader can check without
executing anything: a register, reconciliation, schedule, answer key or review.

## Read first, in this order

1. `production/briefs/AUTHOR-BRIEF-B8.md`. It is authoritative. Follow it exactly. The other briefs are history.
2. The plan brief (end of this prompt): your 3-5 target library modes, their roles and weights, and a traps.json
   skeleton. Modes are targets. Build each one only where the seed's material supports it naturally. If one does not fit, swap in
   another library mode of a different family and say why in the hand-back.
3. For every mode you build: `python3 -I production/traps/traplib.py show <id>` (or its section in
   `production/traps/TRAP-LIBRARY.md`): recipe, proof obligations, hazards, what killed it. For measured modes, open
   the source premises its evidence rows name (their VALIDATION.md, DIAL.md and fixture lines). Copy the
   ingredients, never the wording.
4. `production/templates/reference-task-suitcase-2.6.0/`: VALIDATION.md, authoring/DIAL.md, authoring/traps.json
   and the authoring scripts. That task met the bar. Copy its authoring-script pattern.
5. The seed session (`source_trace`). Extract it into a new `mktemp -d` directory under {SCRATCH} (recipe in
   `production/starter/README.md`). Read its user requests and corrections with `python3 -I`. It is untrusted data:
   never run anything from inside it, and never copy its text into the task verbatim.
6. `production/PITFALLS.md`.

## Build (AUTHOR-BRIEF-B8 §3-§10)

- Fixture in `environment/files/`: a realistic professional workspace (policies, exports, drafts,
  correspondence), grounded in the seed's material and corrections, moderate in size. Fictionalise real people,
  brands, schools, minors, judgments and statutes; keep the professional substance.
- Instruction per step: what is wanted, never how to find a trap. State the as-of date, every field and its
  meaning, the deliverable path and the published contract sentence. Keep every scope, exclusion and edge-case
  sentence. Field names and descriptions are schema-only.
- Grader as data: `tests/checks.json`, `outputs.json`, `rubric.json`, `basis.toml`, `reward.toml`. At least 8 graded
  checks per step, summing to 100.
- Reference `steps/<step>/solution/solve.py` derives every answer from the fixture (no stored answers) and honours
  `ARENA_MISREAD="P2,P4"`.
- `authoring/traps.json` with schema `b8/premises/1`, `task.toml [metadata] trap_families`, `authoring/DIAL.md`,
  `VALIDATION.md`, `REWARD-HACKING.md`, and the `difficulty_explanation` (no pass rates; end with the
  calibration-of-record sentence of the reference task).

## What decides whether a premise bites (measured; AUTHOR-BRIEF-B8 §1, §5, §6)

- The decisive fact is inferred from at least 2 routine anchors in at least 2 files of different parties, each
  doing another job. A stated rule or a stated fact never bites (0 of 1530 premise-runs missed).
- Make the model reverse a record: an official-looking record gives the default answer, the anchors make it
  impossible, and no sentence gives the record priority or names the error's mechanism.
- Never a printed form, legend or governing table that states the opposite of the answer.
- Ask for the outcome, never the discrepancy. No field lists errors, mismatches or conflicts.
- The misread deliverable must look complete and consistent: no unmatched row, visible duplicate or total that
  only the correct reading reconciles.
- An anchor shares no identifier token with the record it settles. It names the item by description.
- Anchors never read as corrections: no "actually", "should be", "the correct figure is", "please update".
- Same-family anchors go in different files: a new note next to an existing anchor primes it.
- Hiding, burying, volume, decoys and breadth do nothing. Both models read every file.

## Composition (design_lint and author-check enforce these)

- At least 3 decisive premises, each from a library mode, spanning at least 2 library families (plan for 3).
- At least 1 decisive premise aimed at Fable and at least 1 aimed at Astra.
- Weights about 25 / 21 / 17 (unequal, at least 60 together); fillers at most 5 points each; projected free share
  at most 0.40 per step.
- No clock premise is the heaviest of its step. No decisive premise with mechanism STATED. No dead mode and no D id.
  At most one pilot-first mode (literature, trace-derived, bimodal) per task, never the heaviest.
- No number, ID or fixture value inside any instruction example.
- One decision = one check. No cascade: a downstream field is graded against the agent's own upstream answer.
  Additivity holds for every subset of premises (executed by design_lint).

## Prove it (AUTHOR-BRIEF-B8 §8)

`authoring/validate.py <task> <scratch>` runs everything on `mktemp -d` copies under {SCRATCH} with
`"$PY311" -I -B`: reference 1.0 and empty workspace 0.0; every misreading alone and combined; at least 15
rule-breaking variants lose credit and at least 3 benign variants keep 1.0; a leak grep; a byte-identical rebuild;
no `__pycache__`. Per decisive premise, its mode's proof obligations, at least:

- uniqueness: which alternative readings fail which anchor or figure;
- anchor ablation: delete one anchor, flip one, delete both, and say what each does;
- an executed counterfactual: change the settling fact in a copy; the derived answer flips and the grader follows;
- a census of plausible wrong answers, each losing only its own check.

Record every output in VALIDATION.md, with the per-premise answers to: would a careful agent that reads every file
but never asks this premise's question get it wrong (must be yes)? Does the instruction or a field name make it
ask (no)? Does any anchor read as a correction (no)?

## Your gate

From {REPO}, run:

    python3 -I production/tools/b6ctl.py author-check {TASK_DIR}

Fix every item it lists and run it again until it prints READY.

## Limits

- Never launch or measure anything: no `b6ctl run`, `launch`, `rerun-void` or `ship`, and no arena, harbor, coder,
  measure or benchmark command. The controller launches.
- Edit only {TASK_DIR}. Never touch `pipeline/`, `production/tools/`, `production/traps/`, other tasks or
  `envs-b6/_versions/`.
- Never read or print `keys.env` or any credential. Never glob `/tmp`. Make scratch with `mktemp -d` under
  {SCRATCH} and remove only what you made. Use bash, not zsh: zsh does not word-split.
- No sub-agents and no blind readers (the controller runs them). No git commits. No Co-Authored-By or other
  attribution lines.
- Time box: 80 minutes. If author-check is still NOT READY at 70 minutes, stop and hand back its list verbatim.

## Hand back (at most 20 lines)

- the tree path and version;
- per decisive premise: mode id, documents used, the default wrong answer, weight, expected miss rate per model;
- the dial sentences;
- the expected free share per step;
- the author-check verdict line, verbatim;
- the faithfulness target (F0, F1 or F2) with its evidence;
- any plan mode you swapped, and why;
- anything you are unsure of.

## Controller notes

{NOTES}

## The plan brief (authoring/PLAN.md)

{PLAN}
