# Re-audit brief (2026-10-15): genuine ambiguity, or an overly strict audit?

> **Paths (2026-10-15).** Still in use for the §14 audit. In this repo: `production/tools/design_lint.py` and `production/tools/signal_gate.py`, campaigns under `pipeline-artifacts/b4/`, the design brief is `production/briefs/AUTHOR-BRIEF-B8.md`, trap modes are in `production/traps/TRAP-LIBRARY.md`, and the verdict log is `production/state/genuineness.md`; `$W/...` paths below are the old workspace layout.

Several §14 audits WITHHELD tasks or flagged a premise AMBIGUOUS while an Opus blind reader reached the reference (1.0). The user asks whether those audits were genuine or overly strict. You are a neutral senior reviewer re-adjudicating ONE task.

## Read
- `AUDIT-BRIEF-B6.md` (the §14 method and its bar).
- The audit verdict for your task in `genuineness.md` (grep the task name; read every line, including the blind-reader entries).
- The task tree at the version named in your prompt: `instruction.md`, `environment/files/`, `authoring/traps.json`, `VALIDATION.md`, `tests/checks.json`. Read the governing documents in full.
- The failing runs' reasoning, from the final campaigns named in your prompt (`W/pipeline-artifacts/b4/<task>-<ver>-final-{fable,astra}/jobs/run/package__*/steps/01-task/agent/`, `trajectory.json` / `codex.txt`). Use Python to extract windows; never cat whole files.

## The bar (apply it exactly; neither stricter nor looser)
A premise is **GENUINE** when a careful professional, reading only the files, reaches ONE answer, and every alternative reading contradicts at least one sentence or figure in the files. It need not be easy or stated.

A premise is **AMBIGUOUS** only when an alternative reading is consistent with EVERY sentence and figure in the files, and with the governing text's scope. "The instruction could have been clearer", "the models found it hard" or "the reading is unusual" are NOT ambiguity.

Watch for both audit errors:
- **Too strict:** calling a reading defensible when a specific line contradicts it.
- **Too lenient:** missing a genuine second reading that the governing text supports.

## Output, in `W/research/batch4/b7/reaudit/<task>.md`
1. The audit's claim, quoted.
2. Each alternative reading. For each, the strongest textual support, and the line(s) that contradict it, quoted with file and line. Or "none found".
3. What the failing runs actually argued: quotes and counts. Are their reasons the audit's alternative, or something else?
4. **Verdict:** GENUINE / AMBIGUOUS / GENUINE-soft (defensible only by ignoring one specific anchor), with one paragraph of reasoning. State plainly whether the original audit was correct, too strict or too lenient.
5. If AMBIGUOUS: the smallest FACT-anchor fix (never a stated definition or rule; stated rules kill the trap) that removes the alternative while keeping the trap missable. Also give any other validity issue you noticed.

Hand back ≤ 12 lines. Read-only on every tree, campaign and tool. No launches, no subagents, never read keys.env, never glob /tmp.
