# arena-envs-tasks-large-dump

Building non-coding professional knowledge-work RL environments from Arena agent
traces, at batch scale. Deliverables are documents, registers, schedules and
analyses a careful reader can check **without executing anything**.

## v2 (2026-10-02) -- read this first

This checkout is `arena-envs-non-coding-v2`: a clean start on the 9/29 dump
(`datasets/accepted_500_traces`, metadata for all 500 sessions plus files <= 2 MB
of the 282 non-coding sessions). User brief: 20 extremely hard non-coding envs,
both models should genuinely fail most of the time, as many genuine traps,
checks and near-miss decoys as needed, dense tasks, instructions that give the
WHAT and never the HOW, and blockers/repairs only for REQUIRED checks.

What changed against v1 (all in this tree; v1 lives in arena-envs-tasks-large-dump):
- `pipeline/advisory.py`: quotas, bands, weight shapes, construction plans, the
  difficulty self-audit's shape, trap counts and answer-shape heuristics are
  ADVISORIES (shown to the designer, recorded, never blocking, never a repair).
  Unknown findings stay blocking. Validity, reward-hacking, leak, privacy,
  provenance, contract and attribution checks are unchanged and still block.
- `policy.BAND_LIMITS` core 4-24 / floor 0-4 / stretch 1-16 (min 8 objectives kept).
- `validate._hidden_rules` witness mode (`policy.HIDDEN_RULE_MODE`): a filter
  cites a verbatim rule sentence from the instruction OR a fixture document;
  tested values must be findable; lexical co-occurrence is advisory.
- Authored documents at natural paths; the disclosure notice moved to
  `provenance/scenario-notice.md` (v1's in-fixture `scenario/README.md` listed
  every authored trap file and was opened in 97%/88% of steps -- research/R3).
  Limits 256 KiB/file, 2 MiB total, text formats incl. .eml .ics .tsv .log.
- `pipeline/author/levers.py`: the V2 DIFFICULTY DOCTRINE leads the designer's
  system prompt -- lever catalogue from research/R1-R5, density arithmetic,
  WHAT-not-HOW template, `quality.fragility_budget` audited (advisory) by check_draft.
- Designer/classifier `claude-opus-5-5` at xhigh, 220 turns; reviewer gpt-6-astra.
- Gate verdict: a gate SKIPPED only behind a FAILED prerequisite is `blocked`
  (repairable), not `unverified`.
- Coder pool: this checkout owns `arena-calib-3` (user-approved 2026-10-02).
- NOT changed (classifier-blocked as security-test removal): the contract-probe
  gate still raises when the reference does not score 1.

## Before designing anything

| doc | when |
|---|---|
| `pipeline/POLICY.md` | **authoritative.** Every acceptance threshold, the five phases, what each may reject. Thresholds live in `pipeline/policy.py`, never in prose |
| `rulesets/ANTI_REWARD_HACKING.md` | **before writing the question.** §0 — the answer must be derived, never stored — cannot be retrofitted |
| `rulesets/PLAYBOOK_GENERAL.md` | difficulty levers, check model |
| `ref_files/[Scaler__Arena] RL Environments Spec - Updated 9_21.docx` | Arena's requirements. The deliverable format is not negotiable |
| `ref_files/Feedback for Scaler…docx` | the nine defects delivery 1 shipped |
| `pipeline/README.md` | stage detail. Historical on thresholds — POLICY.md wins |

## The five phases

```
1 select    traces -> classified into target levels F3 Replay / F2 Scenario /
            F1 Pattern / F0 Inspired BEFORE authoring; no level blocks authoring
2 author    full trace visibility -> complete env, EXTREMELY hard on the first
            pass: genuine traps authored in (F3-bound: aligned to the trace's
            corrections; below F3: any relevant trap type). A difficulty
            self-audit (quality.difficulty_case: one misreading per trap, each
            encoded by an executed counterexample) is required to submit
3 grade     validity only: static gates, probes, controls, naming, harbor
            tasks-check, semantic review. >= 8 graded checks per task, weights
            summing to 100 in every task. NO difficulty check of a single task:
            the semantic review blocks on validity and novelty only; its
            difficulty judgments are `difficulty_advisories` (user 2026-09-26),
            shown in the screen report and fed to hardening
   -- barrier: the whole requested batch is built --
4 calibrate screen: 3 episodes x 2 models per task (user 2026-10-16) -> pass@1, mean
            reward, attribution, hardening outlook. THE PIPELINE STOPS HERE
5 harden    MANUAL ONLY -- nothing automatic may call it. At most 3 redesign
            attempts per task, ever (attempt 1 = the full extremely-hard
            redesign; 2-3 repair or tighten). Every valid revision gets a 3 x 2
            screen; stops on target met / budget spent / measured no progress /
            repeated finding, never on an unclean screen. Only a task whose screen measured cleanly (valid
            episodes, attributable failures, no unresolved reward hacking) AND met the target (pass@1 <= 0.5
            on both models; policy.QUALIFY_REQUIRES_SCREEN_TARGET, user 2026-10-16) may take the
            10 x 2 calibration of record (`arena qualify`); a missed screen is hardened, never qualified

pass@1 < 0.5 on both models is the STRICT TARGET and never a blocker
(`policy.DIFFICULTY_GATES_RELEASE = False`, user 2026-09-25): authoring aims at
it, every screen reports against it, hardening stops once it is met, and
nothing -- build, screen, qualify, release -- rejects or holds a task for
missing it. Validity (grader defects, leaks, voids, attribution, reward hacking)
still blocks.
```

Presolve (a one-episode screen after every draft) and the in-build difficulty
pilot were removed on 2026-09-25: difficulty is authored into the first draft
and measured once, for the whole batch, by the screen. `./arena build` runs
phases 1-4 and prints the table; `./arena screen <tree>` re-screens or
(`--report-only`) reprints it.

## Scope

Non-coding only. A seed whose correctness can only be judged by running it is
rejected as `requires_execution`, however interesting its failure. Writing a
document *about* code — a review, an audit, a specification, a migration plan —
is in scope.
The original request must support that non-coding deliverable. Do not invent a
code audit to rescue a request to implement or debug software. File extensions,
workspace byte share, delivery markers and version counts do not prove scope,
acceptance, correctness or difficulty; inspect the original requirements and
source material through the complete evidence catalog.

This is not a preference, it decides the funnel. Keyed on manifests, test files
and source extensions, the non-coding share of one 500-session dump collapsed to
8 candidates of 102, one of which survived. Re-keyed on deliverable bytes the
same corpus gave 21 and 8.

## Standing rules

- **Verify by execution.** Claims about what an environment does or refuses are
  worth nothing without the command and its output.
- **Never claim a task is complete, flawless or fully hardened.** State what is
  verified and what is untested; bundles declare `untested_surfaces`.
- **`SKIPPED` and `ERROR` are never green.** A pipeline that treats "could not
  check" as "nothing wrong" is the whole problem.
- **`gated_out` is not `failed`.** A criterion never attempted says nothing
  about ability; compute rates over reachable attempts only.
- **Every zero is classified** as model failure or void before it reaches a
  table. A void is worse than a missing data point — it is indistinguishable
  from a result.
- **Freeze fixture, instruction and grader together.** Changing one without the
  others is how a task silently regresses.
- **Difficulty is a changed premise, not breadth.** ~~Difficulty is measurement
  breadth~~ — the breadth claim rested on 24 tasks at *one cold episode each* and
  is **falsified**. Re-measured over every check with real calibration data (369
  checks, n≥4 episodes, both models): checks that NEVER fail average 6.2 record
  members, 2.7 source documents and 2532 rows scanned; checks that ALWAYS fail
  average 5.0, 2.1 and 41. Breadth, source count and volume are *anti*-correlated
  with difficulty — `c_rework_census` (14 members over 14 documents) fails 0/4,
  `c_claims` (30 members) 0/10, while three checks with two members over one file
  fail 100%. A large enumeration is mechanical and a frontier model grinds it out.
  What difficulty tracks is **a premise that changes, or a conflict over which
  document governs, that silently invalidates a result the model already
  computed** — a revised threshold applied to items already counted, a governing
  document that is not the obvious one, or a residue of something declared
  retired. Keep the affected population small (every measured killer sits between
  9 and 130 rows) and route several checks through the one premise, since pass@1
  counts FULL success. Exactness (no tolerance) and cascade survive from the old
  rule; breadth does not. `rulesets/PLAYBOOK_GENERAL.md` carries this as the
  seventh lever with the sixth marked superseded. NOTE: `check_difficulty.py` and
  `pipeline/breadth.py` still implement the falsified breadth screen — treat a
  green from them as no evidence of difficulty.
  **First direct test was negative**: a governing-document conflict added to
  a-321 moved pass@1 from 0.88 to 0.80 on one model and not at all on the other.
  Whether the revised-threshold variant transfers to an easy bundle is still
  being measured. Do not treat this rule as established for *adding* difficulty;
  it is established only as a description of the bundles that are already hard.
- **A hard task is the goal, not a defect.** An all-fail task is admissible.
  What must be proved is that the failures are the model's: voids leave every
  denominator, contract failures are capped at 30%, and every check no episode
  passed needs an executed source counterfactual and a passing reworded answer.
  Never make a task easier because attempts failed it.
- **Deliver in Arena's shape.** `arena deliver` files a working tree into
  faithfulness folders (`F3-replay/`, `F2-scenario/`, `F1-pattern/`) and names
  tasks `a_f<level>_<task-name>`. The working tree stays filed by source
  category, because the level is only measurable after the build. The batch
  ships a batch report, trace accounting covering 100% of shared sessions, and
  a reward-hacking note per environment.
  The reference solution is a script that *derives* the answer — a stored answer
  fails both the spec and Harbor's own `hardcoded_solution` criterion.
- **Repair is bounded and monotone.** Two passes; the finding set must strictly
  shrink within a grading stage (gates, then semantic review); a repeated finding is terminal. Discarding a candidate that carried an
  actionable finding is how 47 of 86 were lost.
- **Infra loss is re-run; results are not.** Five top-up episodes per task per
  model, replacing voids only. Re-running a scored episode until the number
  improves makes every difficulty figure a lower bound on how many times we tried.
- **A threshold with no reader is decoration.** Four mechanisms this session were
  built, tested and wired to nothing. `EveryPolicyConstantIsRead` fails the build
  on an orphaned `policy.py` constant; add a reader or mark it declarative.
- **Graders are data, not code.** Checks live in `tests/checks.json`; targets are
  expressions recomputed from the fixture at grade time. There is nowhere to type
  an expected value, which is why the 26-vs-27 answer-key defect is not available
  in this shape.

## Gotchas

- `keys.env` is gitignored and lives per workspace. `./arena keys` prompts and
  writes it at mode 600.
- `claude-opus-5` rejects `temperature`; determinism comes from strict output
  schemas and the content-addressed classification cache.
- Calibration is **Fable 5.1** (`anthropic/claude-fable-5-1`) in **Claude Code**
  and **GPT 6 Astra** (`openai/gpt-6-astra`) in **Codex** (user, 2026-09-26),
  both at **high** effort, with **no turn or time limits**. The CLIs are pinned
  and baked into the task image; the agent phase may reach only its own model
  API host (Harbor egress allowlist), and the verifier stays offline. Egress
  control needs `CONFIG_NFT_FIB_INET`, which Docker Desktop's kernel lacks, so
  harness campaigns run on the Coder pool. `gpt-5.6-sol` and `claude-opus-5` are
  retired from calibration. Harness, effort and limits are part of the
  measurement: report them with every rate.
- The dump path has no default. `./arena dump --set <path>`.
- Tier boundaries (0.53 / 0.40 / 0.28) were fitted to the first 500-session
  corpus and are absolute, so a richer dump correctly produces a larger tier 1.
  Re-derive them only deliberately — recomputing per corpus hides the
  improvement you want to detect.
- Build categories ARE Arena's faithfulness levels (user, 2026-09-26): every
  trace is classified into the level it can reach -- F3 Replay, F2 Scenario, F1
  Pattern, F0 Inspired -- before authoring (`select/categories.py`), and the
  working tree files bundles under `target-F3-replay/` ... `target-F0-inspired/`.
  That is a TARGET: the level measured after the build decides delivery (a
  target-F3 seed whose fixture was reconstructed ships as F2), and "no F0" is
  enforced on the measured level at delivery, never at classification. The
  retired A–D categories map A→F3, B/C/D→F2; bundles in old `rich/`-style
  folders are still found. Source tiers 1–4 still order candidates internally.
- `harbor tasks-check` is spelled `harbor check <dir>` in 0.22.0, and it is an
  **LLM agent trial** (~2.5 min, needs Docker and model auth), not a static
  lint. Budget it.
- `F1`/`F2`/`F3` used to name pipeline *stages* here. They are faithfulness
  levels now; anything reading them that way goes through `ledger/levels.py`.
