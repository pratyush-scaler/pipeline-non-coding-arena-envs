# Task templates

Canonical components every task bundle copies. Keep one source of truth here rather than
hand-editing per task — drift between task copies is how harness rules quietly diverge.

## `operating-notes.md`

**Byte-exact copy of the shipped BrowseComp `T02` version.** Do not reword it.

It is shown to the agent alongside `instruction.md` and states the harness contract:

- the agent works a **virtual desktop** via computer-use tools (screenshot / move / click /
  type / scroll), not an API
- screenshot before acting and after any state-changing action
- drive the app through its own on-screen UI — **no internal HTTP/API calls, database edits
  or backend shell commands**
- read relevant records before changing anything
- state what changed when done

### Why this file governs task design

The no-API rule means **every value a task needs must be reachable on screen**. A figure
that exists in the database but is not rendered anywhere in the app's UI makes a task
unanswerable, no matter how clean the grader is. Confirm UI reachability during Stage 2
(fixture design), not after the grader is written.

It also means the word budget for `instruction.md` covers task content only. These harness
rules ship separately and don't count against it.

## The answer-recording appendix

Pure-lookup tasks need somewhere to put an answer that grading can see, since the grader
never reads the agent's chat. The shipped `T02` task put that convention in
`instruction.md`, not here:

```markdown
## Recording your answer

Grading never sees this chat, so the answer has to land in the environment. When you have
it, create a new document in Word whose title is exactly:

    ANSWER: <your answer>

The title is the answer field; leave the document body blank. Add that one document and
change nothing else: every other record in these apps should be left as you found it.
```

Append that to `instruction.md` **only for lookup tasks**. A task whose end state is real
work — rows written, mail sent, records updated — is graded on that end state and needs no
answer surface.

## Files a task bundle contains

| File | Source | Agent sees it |
|---|---|---|
| `brief.md` | authored (Stage 1) | no |
| `seed.md` | authored (Stage 2) | no |
| `rubric.md` | authored (Stage 3) | no |
| `instruction.md` | authored (Stage 4) | **yes** |
| `operating-notes.md` | **copied from here** | **yes** |
| `task.toml` | copied + edited | no |
| `tests/auxiliary_data.json` | authored (Stage 3) | no |
| `tests/grader.py` | authored (Stage 5) | no |
