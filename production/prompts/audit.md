# §14 audit of one task (independent auditor)

You are the independent auditor of ONE task. You did not author or tune it, and you have not seen its authoring
session. Work from the repo root and use bash.

- Repo root: {REPO}
- Task tree: {TASK_DIR}
- Task name and version under audit: {TASK} {VERSION}
- Campaigns (pilot and final, reruns included), gate reports, census logs, the blind reader's result and the
  controller's notes: at the end of this prompt
- Write your report to: {AUDIT_REPORT}
- Scratch parent for every temporary directory you make: {SCRATCH}

Everything except {AUDIT_REPORT} is read-only for you. Run every executed check on a `mktemp -d` copy under
{SCRATCH}, with the verifier's Python 3.11 for anything the verifier would run. Resolve it once from the repo root:

    PY311="$(python3 -I -c 'import runpy; print(runpy.run_path("production/tools/paths.py")["PY311"])')"

## Read first

1. `production/briefs/AUDIT-BRIEF-B6.md`: the method. Ignore its old `$W` paths. Two of its lines are replaced
   here: you write the report to {AUDIT_REPORT} instead of returning it as text, and you do NOT spawn a blind reader
   (it was run separately; its result is listed at the end of this prompt).
2. `production/briefs/REAUDIT-BRIEF-B7.md`: the ambiguity bar. Apply it exactly, neither stricter nor looser.
3. `production/briefs/AUTHOR-BRIEF-B8.md` §0, §6 and §7: what a valid premise and a valid grader look like.
4. The tree: every `steps/*/instruction.md`, `environment/files/` (read the governing documents in full),
   `authoring/traps.json`, `VALIDATION.md`, `REWARD-HACKING.md`, `tests/checks.json`, `tests/rubric.json`.
5. The failing runs' reasoning in the final campaigns. Extract windows with `python3 -I`; never cat whole
   trajectory files.

## The bar for a premise

GENUINE: a careful professional reading only the files reaches ONE answer, and every alternative reading
contradicts at least one sentence or figure in the files. It need not be easy or stated.
AMBIGUOUS: an alternative reading is consistent with EVERY sentence and figure in the files and with the governing
text's scope. "Could have been clearer", "the models found it hard" and "the reading is unusual" are not ambiguity.
GENUINE-soft: defensible only by ignoring one specific anchor (name it).
DEFECT: the grader, reference or fixture is wrong.

A blind reader reaching the reference shows the answer is REACHABLE, not that it is UNIQUE. An unaudited 100% miss
is presumed unfair until this audit says otherwise.

## Report sections, in this order

1. **Gates, re-run.** Quote the verdict lines of the design lint, run on a copy:

       C="$(mktemp -d "{SCRATCH}/lint-XXXXXX")"; cp -R "{TASK_DIR}" "$C/{TASK}"
       "$PY311" -I -B production/tools/design_lint.py "$C/{TASK}" --b8

   and of `python3 -I production/tools/b6ctl.py gate {TASK_DIR} final`. Note that signal_gate's EXTREME flag still
   uses the old 0.30 line; the bar is pass@1 at most 0.5 on both models.
2. **Voids.** Count them. Confirm none is infrastructure-caused: auth errors (401, invalid key), timeouts, missing
   transcripts, provider refusals or empty-reply loops. A void is never a model failure.
3. **Genuineness, every failing run** of the final and the pilot: a table of run id, score, premises missed, what
   the model wrote on the deciding item (quoted from its messages or code), and silent miss or voiced-and-rejected.
4. **Dominant-miss adjudication (mandatory).** For every check a model missed with the SAME wrong value in at least
   70% of its runs, and every premise a model missed in at least 90% of its runs: read 2-3 of those trajectories and
   quote the model's own stated rationale. Then adjudicate it on its own terms:
   - Is there a rule or fact in the files that makes that value defensible?
   - Does a rule apply to that item while one of its inputs (a clearance, a date, a unit, a party) is missing?
   - For each alternative reading: its strongest textual support, and the line(s) that contradict it, quoted with
     file and line number. Or "none found", which makes the premise AMBIGUOUS.
5. **Cascade and double-charge.** Confirm that each missed premise loses only its own checks in every failing run.
   Regrade at least 10 rule-breaking variants and at least 3 benign variants with the shipped grader on mktemp
   copies: each rule-breaking variant loses exactly its own checks, each benign one keeps 1.0. Any downstream check
   graded against the reference's upstream answer instead of the agent's own is a DEFECT.
6. **Clock-primary check.** Rank the failing premises by points lost across all final runs. If the heaviest is a
   clock, time-zone or timestamp-offset premise, the task cannot ship (Arena 261013).
7. **Leaks and hacking.** Grep every graded value and ID in the instruction(s), including every example and the
   contract sentence; grep trap words in the fixture; check every trajectory for access to `/tests`, `/solution` or
   the grader; confirm the Dockerfile copies only `files/`.
8. **Arena classes.** One line each for the 261008 classes (8) and the 261011 classes (13, plus no graded value in
   examples). Then: one decision = one check; free share at most 0.40 per step (the older brief says 35%; report
   both numbers); a distinct family per premise in a step; the task's heaviest trap family.
9. **Blind reader.** From the listing or the notes: the reader's score and misses with the shipped grader. For each
   reader miss on a premise, say whether it is the reader's miss or text that does not determine the answer, and
   quote the text. If there is no blind-reader result for this version, say so: the verdict cannot then be SHIP or
   SHIP-WITH-DISCLOSURE.
10. **Learning signal.** Per model: full passes, distinct scores, reward SD, per-premise miss rates, constant
    premises, max |phi|, pass@1. Say plainly whether each model shows a within-model pass/fail mix.

## Verdict

- SHIP: gates pass; every failing premise GENUINE; no leak, defect, cascade or void issue; final pass@1 at most 0.5
  on both models; the primary failure is not a clock premise; the blind reader reached the reference or each reader
  miss is shown to be the reader's.
- SHIP-WITH-DISCLOSURE: as SHIP, plus named disclosures (for example a FLAT model, a GENUINE-soft premise, a
  constant premise, free share above 0.35).
- WITHHOLD: name the defect, its exact location (file and line) and the minimal fix. A fix for ambiguity is a FACT
  anchor, never a stated rule or definition: a stated rule kills the trap.

The report's LAST line must be exactly one of these three lines, with nothing after it (`b6ctl ship` reads it):

    VERDICT {TASK} {VERSION}: SHIP
    VERDICT {TASK} {VERSION}: SHIP-WITH-DISCLOSURE
    VERDICT {TASK} {VERSION}: WITHHOLD

## Limits

- Read-only on the tree, the campaigns and the tools. Write only {AUDIT_REPORT} and `mktemp -d` directories under
  {SCRATCH}; remove only what you made.
- No launches: no `b6ctl run`, `launch`, `rerun-void` or `ship`, and no arena, harbor, coder, measure or benchmark
  command. No sub-agents.
- Never read or print `keys.env` or any credential. Never glob `/tmp`. Use bash, not zsh. No attribution lines.
- Time box: 60 minutes.

## Hand back (at most 12 lines)

The verdict line; each premise's classification (GENUINE, GENUINE-soft, AMBIGUOUS, DEFECT) with its miss rate per
model; the disclosures or the WITHHOLD fix; the report path {AUDIT_REPORT}.

## Campaigns, gate reports, census logs and the blind reader of {TASK} {VERSION}

{CAMPAIGNS}

## Controller notes

{NOTES}
