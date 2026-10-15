# Pitfalls: the 20 most expensive lessons

Each one cost a batch, a night or a shipped task. One line of symptom, one line of fix. The measurements behind the
design lessons are in `briefs/AUTHOR-BRIEF-B8.md` §1 and `traps/TRAP-LIBRARY.md`.

## Running campaigns

1. **API key dies mid-run.**
   Symptom: a model's runs come back `void-auth` (401, invalid key); a void looks like missing data in the table.
   Fix: `b6ctl preflight` before every launch (`run` does it). Re-run voids once (`rerun-void`). Never re-run a
   scored run. A 401 means a human replaces the key in `keys.env`; never print or paste a key.

2. **An inherited session token reaches the campaign.**
   Symptom: Fable runs use the Claude Code session's own `ANTHROPIC_AUTH_TOKEN` (it beats `keys.env`), then 401 when
   it expires.
   Fix: launch every pool-touching command as `env -u ANTHROPIC_AUTH_TOKEN ...`.

3. **zsh does not word-split.**
   Symptom: `for n in $LIST` runs once with the whole list; an empty derived path once turned `rsync -a $b/ dest/`
   into a copy of `/`.
   Fix: use bash. Use arrays (`"${NAMES[@]}"`), quote every path, and stop if a derived path is empty.

4. **Globbing /tmp destroys other work.**
   Symptom: a test that wrote "every report under /tmp" followed symlinks and overwrote about 59,000 task JSON files
   in another workspace (2026-09-27).
   Fix: `mktemp -d` for all scratch; remove only what you made; never `glob('/tmp/**')` or `rm` by pattern.

5. **Coder autostop wipes the pool's runtime.**
   Symptom: after the 12-hour autostop the pool restarts with an empty disk, and launches refuse ("runtime is not
   proven ready").
   Fix: check `./arena coder status` before a launch. Restarting and re-preparing a pool needs the user's approval.

6. **Editing `pipeline/` while campaigns run.**
   Symptom: the pools refuse the next campaign (changed code hash), and release receipts stop matching.
   Fix: no `pipeline/` edits while anything runs. Ask before any `pipeline/` edit at all.

6b. **Two checkouts sharing one pool.**
   Symptom: campaigns are refused or a pool's code is overwritten mid-run, because a pool holds one code hash.
   Fix: every teammate calibrates on their own Coder workspaces (`export ARENA_POOLS=...`); never point at a pool
   another checkout is using.

7. **Calibrating from several processes.**
   Symptom: parallel launch processes wiped each other's code on the pool; 21 episodes were void (2026-09-28).
   Fix: one controller process per pool. Go wider by raising its concurrency, not by adding processes.

8. **A 5-run pilot is noise.**
   Symptom: the same task text measured 2/5 on one pilot and 5/5 on the next.
   Fix: pilots only triage. Decide on a fresh 10 x 2 final.

## Designing traps

9. **Stated rules never bite.**
   Symptom: premises settled by a stated rule were missed 0 of 1,530 premise-runs (Fable 0/810, Astra 0/720).
   Fix: the decisive fact is inferred from at least 2 routine anchors in at least 2 files of different parties.

10. **Hiding, volume and decoys do nothing.**
    Symptom: both models read every file; in 519 of 521 failing premise-runs the deciding line was already in the
    model's own tool output.
    Fix: build reconciliation failures: a record the anchors make impossible, with nothing giving it priority.

11. **A clock trap as the primary failure.**
    Symptom: Arena's 2026-10-13 review found 34 of 37 delivered tasks hinged on one hidden clock offset, with mostly
    flat scores, and asked for varied decisive traps.
    Fix: no clock premise is the heaviest of its step; no trap family leads more than about 25% of a batch.

12. **A new trap rarely lands in band.**
    Symptom: 0 of 7 newly authored lead traps landed at 20-80% on Fable (stated forms 0/5, inferred forms 5/5); the
    T2 template transferred to 1 of 7 new tasks.
    Fix: pilot every new trap, budget 3-4 variants, and prefer modes the library marks proven (T1, T3, T5, T12).

13. **Fixing ambiguity with a stated rule kills the trap.**
    Symptom: one stated definition took a premise from 10/10 missed to 0/10 on both models.
    Fix: repair ambiguity with a fact anchor, never a definition or a rule. Keep every scope and exclusion sentence:
    deleting them made 0 of 10 hardening attempts legitimately harder.

## Grading and auditing

14. **A blind reader's 1.0 shows reachability, not uniqueness.**
    Symptom: two withheld tasks had a 1.0 reader and still had a real second reading.
    Fix: the §14 audit adjudicates line by line: name each alternative reading and quote the line that contradicts
    it.

15. **An unaudited 100% miss is presumed unfair.**
    Symptom: "inferred" traps missed 5/5 were missed by the Opus blind readers too, so they were invalid, not hard.
    Fix: a blind reader and the §14 audit before calling a 100% miss genuine, and before any dial.

16. **Double-charge and cascade.**
    Symptom: one miss loses unrelated checks (a sequence check graded against the reference's mapping instead of the
    agent's own).
    Fix: one decision = one check; downstream fields are graded against the agent's own upstream answer; design_lint
    executes additivity over every subset of premises.

17. **A graded value in an instruction example.**
    Symptom: "IDs such as H01" put a graded answer in the instruction; the audit withheld the task.
    Fix: examples carry no number, no ID and no fixture value.

18. **Changing a measured tree silently voids its measurement.**
    Symptom: writing `provenance/replacement.json` after a screen changed the task's identity, and the screen no
    longer counted; any edit to `task.toml`, `provenance/` or the files does the same.
    Fix: freeze before measuring. Any change is a new version with its own pilot and final.

19. **The verifier's Python 3.11 rounds differently from the host.**
    Symptom: a task measured 0.00 / 0.00, yet every episode gave the reference answer: the grader's float sum flipped
    a half-up rounding on 3.11 but not on 3.12.
    Fix: run controls and validate.py with the verifier's 3.11 (`paths.PY311`), and census the answers against the
    reference before believing any 0/0.

20. **Step 2 is a fresh session in both harnesses.**
    Symptom: a model passed step 1 everywhere and then failed step 2 asking for facts that only step 1's instruction
    stated.
    Fix: every step's instruction restates everything that step relies on.

## When you are stuck

- `python3 -I production/tools/b6ctl.py doctor`: every prerequisite, with its fix.
- `python3 -I production/tools/b6ctl.py next <tree>`: the current stage and the exact next command.
- `production/tools/README-FLOW.md`: the command-level flow.
