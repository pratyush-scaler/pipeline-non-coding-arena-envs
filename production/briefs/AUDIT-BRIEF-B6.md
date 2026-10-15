# Batch 6 clean-gate audit (one task; 40-minute box)

> **Paths (2026-10-15).** Still in use for the §14 audit. In this repo: `production/tools/design_lint.py` and `production/tools/signal_gate.py`, campaigns under `pipeline-artifacts/b4/`, the design brief is `production/briefs/AUTHOR-BRIEF-B8.md`, trap modes are in `production/traps/TRAP-LIBRARY.md`, and the verdict log is `production/state/genuineness.md`; `$W/...` paths below are the old workspace layout.

You are the independent auditor of ONE batch-6 task. You did not author it. $W = `~/Downloads/arena-envs-non-coding-v2`; `$PY` = `/Users/pratyushmohanty/.local/share/uv/python/cpython-3.11-macos-aarch64-none/bin/python3.11 -I -B`.

Read first:
- the design: `$W/research/batch4/b6/AUTHOR-BRIEF-B6.md`;
- the task tree (named in your prompt), including `authoring/traps.json`, `VALIDATION.md`, `REWARD-HACKING.md`;
- the campaign dirs `$W/pipeline-artifacts/b4/<task>-<version>-{pilot,final}-{fable,astra,oracle,nop}/`.

**Edit nothing.** Work on `mktemp -d` copies. Return your report as TEXT in your final message: subagent file writes are refused, and the controller saves it.

## Check and report

1. **Gates.** Re-run both and quote their verdict lines:
   - `$PY $W/research/batch4/b6/tools/design_lint.py <task>`
   - `python3 -I $W/research/batch4/b6/tools/signal_gate.py <task> --fable <final-fable> --astra <final-astra>`
2. **Genuineness (every failing premise).** For every failing episode of the final, and the pilot:
   - which premises it missed;
   - what it wrote on the deciding item, quoted from its messages or code;
   - silent miss, or voiced-and-rejected.

   Classify each premise GENUINE / AMBIGUOUS / DEFECT. Count voids, and confirm none is infrastructure-caused (auth, timeout, missing transcript).
2b. **Dominant-miss adjudication (doctrine §14; mandatory).** For every check that a model missed with the SAME wrong value in ≥ 70% of its runs, read 2–3 of those trajectories and quote the model's stated rationale for that value. Then adjudicate the rationale on its own terms:
   - Is there a rule or fact in the materials that makes it defensible?
   - Does any rule apply to that item while one of its inputs is missing from the files (a clearance, a date, a unit, a party)?

   A blind reader reaching the reference does NOT settle this. In niche 1.1 the reader scored 1.0 while 9/10 Fable runs gave a defensible not_determinable. Any defensible rationale makes that premise AMBIGUOUS.
3. **G1 leniency.** Regrade at least 10 rule-breaking variants with the shipped grader; each must lose exactly its own checks. Comparisons are exact. Benign variants keep 1.0.
4. **G2 single reading, per premise.** Give the strongest competing reading and the text that defeats it. A premise whose settling fact needs world knowledge, intent guessing or a single soft anchor is AMBIGUOUS.
5. **G4 leaks and hacking.**
   - Grep graded values and trap words in the fixture and the instructions.
   - Check every trajectory for access to /tests, /solution or the grader.
   - Confirm the Dockerfile copies only `files/`.
6. **Arena classes.** One line each for the 261008 classes (8) and the 261011 classes (13 + no graded value in examples). Plus:
   - premise independence: one decision = one check; downstream fields graded against the agent's own upstream answer;
   - free share ≤ 35%;
   - a distinct family per premise.
7. **Blind reader.** Spawn ONE opus reader (Agent tool) with only a mktemp copy of `environment/files` and the instruction(s). For multi-turn tasks, run the steps in order with fresh context per step. Grade its deliverable with the shipped grader and report its score and misses. If its misses are on a premise, say whether that is a model miss or a text that does not determine the answer, and quote the text.
8. **Learning signal.** From the signal gate:
   - per-model distinct scores and SD;
   - per-premise miss rates per model;
   - constant premises;
   - phi.

   Say plainly whether the task gives a within-model mix.

## Verdict

- **SHIP:** gates pass, every failing premise GENUINE, no leak/defect/void issue.
- **SHIP-WITH-DISCLOSURE:** as SHIP, plus named disclosures.
- **WITHHOLD:** name the defect, its exact location and the minimal fix.

Limits:
- No pipeline/pool/arena/harbor/benchmark/coder commands.
- Never glob /tmp.
- Never read `keys.env` or rclone config.
- No attribution lines.
- The only subagent allowed is the one blind reader.
