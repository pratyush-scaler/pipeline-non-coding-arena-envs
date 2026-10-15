# Arena specification coverage — September 28, 2026

The requested `Unconfirmed 467900.crdownload` no longer exists. The matching
completed download used here is
`/Users/pratyushmohanty/Downloads/[Scaler__Arena] RL Environments Spec - Updated 9_28.docx`.
SHA-256: `463f25c50a5cc8344c25eb3663ccc542a927a7c9eb9dff73af03b2498e04722a`.
If this is not the intended completed download, reconcile this mapping against
that document. Executable thresholds live in `policy.py`; `POLICY.md` separates
spec requirements from stricter local controls. Coverage is not a claim that
an unexecuted task or batch has passed.

## Complete requirement map

| Specification requirement | Enforcement / retained evidence |
| --- | --- |
| Real agent-mode sessions: source schema, inventory, data, outcomes, manifests, artifacts | `dump/`, `select/`, source session and seed IDs, provenance ledger |
| Multiple tasks may come from a source session | Seed identity and `deliverable.tasks_per_environment` |
| Five noisy outcome signals identify material, never determine rewards | `dump/signals.py`, selection; deterministic assertion library supplies rewards |
| Weekly 500–1,000 traces, one-week turnaround | Operational cadence; trace accounting and unfiltered yield expose throughput, not a per-task scoring rule |
| Training hack monitoring and downstream performance gains | Exported runs, hacking notes and metrics support monitoring; actual training/leaderboard improvement is external and not certified by creation |
| Runnable environment, tools, data, pinned dependencies | `author/build.py`, setup/image, native oracle and empty controls |
| Tasks: instructions, starting state, inputs, expected outputs | Compiled steps, public schemas, private source-derived targets |
| Harbor format, tasks-check before sending, end-to-end execution | `benchmark/tasks_check.py`, current-version receipts and actual native controls/calibration; unit tests alone do not satisfy this |
| Source Arena session ID per task | Task metadata, source citations and ledger; Reviewable and trace accounting |
| Genuinely hard for strong models, not busy work | Capability plans and exact-model native measurement, never a prompt or trap-count certificate |
| Self-contained, reproducible, same isolated clean state, no live internet/Arena | Setup, snapshots, native isolation/network configuration, security gates |
| Starting setup excludes completed solutions | Leak, answer-derivation and grader-isolation gates |
| Preinstalled tools/packages/language versions | Pinned requirements, generated image, native setup/control execution |
| Machine-readable tools/actions | Harness/authoring tool schemas, public output schemas, tasks-check |
| Remove leftovers; tests do not write into graded folder | Build cleanup, private grader outputs, workspace and isolation checks |
| In-environment instructions; later steps unlock after earlier completion/grading | `author/contracts.py`, `author/step_files.py`, native step protocol |
| Open-ended domains, slight professional/knowledge-work preference | Selection and review; no invented restriction on other domains |
| Varied failure modes and delivery patterns; avoid repetitive re-skins | Semantic novelty comparison, capability signatures and batch diversity report; declarations are not observed failure attribution |
| Objective, inputs, paths, schemas, meanings, errors, edge cases clear | Production contract, contract consistency checks, independent semantic review |
| Referenced commands/paths exist | `author/validate.py`, published-path checks and native image execution |
| Hidden tests check stated rules; grading special handling public | Exact public-rule witnesses and review; future-step rules cannot settle an earlier check |
| Multiple tasks testing different abilities where useful | Seed/novelty review and tasks-per-environment report; not a fabricated numeric minimum |
| Any source starting point, added tools/cases, grounded domain/situation | Source citations, semantic trace alignment and scenario manifest |
| Invented data labelled synthetic | `author/scenario.py`, disclosure, zero recovered-source credit |
| Deterministic verifiable rubrics; never LLM-as-judge scoring | Reviewed offline assertion library; LLM semantic review checks validity, never rewards |
| Own rubric for every multi-turn turn | Compiled check ownership and per-step native grading |
| Grade only stated work; readable grader/docs/keys/totals | Exported checks, basis/rubric documents, source-derived solution and semantic coverage |
| Prevent accessing/inferring grader logic and expected answers | Private grader isolation, leak/lookup controls, cache/symlink/parser/exit-code probes |
| Scripted full-mark reference included | Source-derived solution verified by delivered grader/native oracle, never merely copying a stored answer |
| All calibration runs and scores, full traces | Native manifests, identity verification and `deliverable.export_runs` |
| At least one successful trajectory: prompts, turns, tools, artifacts, model, rubric rewards | Verified successful calibration or native reference trajectory exported with package |
| Failed runs checked for capability vs ambiguity/environment/grader issues | Source controls, semantic review, native attribution and all-fail assurance; defects/unattributed failures block; voids excluded |
| Passing runs inspected for hacking; repair issues and tested/found/fixed note | Attack probes, trajectory scan, unresolved-hack blockers and `REWARD-HACKING.md` |
| Batch report with every task/batch metric | `deliverable.py`, `batch-report.json`, `BATCH_REPORT.md`, trace accounting and yield |

## Spec 10_12 additions (mapped 2026-10-13)

The four highlighted additions of the 10_12 spec, after Arena's 261013 review.
Thresholds are `policy.py` constants; POLICY.md, "Training signal", says which
block and which advise.

| Specification requirement | Enforcement / retained evidence |
| --- | --- |
| Vary the decisive trap across a batch; no single trap type (e.g. out-of-sync clock offsets) as the decider in many tasks | `quality.premise_map` families (`policy.TRAP_FAMILIES`, timestamp ordering one family, at most one per task); `signal.batch_family_quotas` in every batch screen report (decisive share, presence share, family count, timestamp share) -- advisory |
| Every inference the answer depends on resolvable from the instructions and files | each premise's `resolving_quote` must be verbatim in an instruction or fixture file (`author/premises.py`, blocking); blind reader and semantic review unchanged |
| Spread difficulty over checks that fail on their own; partial progress earns partial reward | premise map: one check per premise, premise share and free share caps (`author/premises.py`, advisory); observed free share, linked-check groups and pairwise premise phi in every screen (`pipeline/training_signal.py`) |
| Reward spread: the same model passes some runs and fails others, with partial scores; avoid flat and model-sorting shapes | `signal.measure` per model per step: distinct scores, SD, sorting, constant premises -> shape `FLAT` / `SORTING` / `CONSTANT_PREMISE` / `TOO_EASY` / `IN_BAND`; hardening's target-met requires `IN_BAND` (`harden._target_met`); never a release gate (`SIGNAL_GATES_RELEASE`) |

## Acceptance and monitoring

| Scope | Requirement | Executable threshold |
| --- | --- | --- |
| Task | Grader sanity | Reference 1.0; untouched workspace 0.0 |
| Task | Solvability | A verified calibration OR reference trajectory scores 1.0 |
| Task | General difficulty | Strict pass@1 `<0.5` on BOTH models |
| Task monitoring | Hard label | Primary at most 2/10 passes, `<=0.2`; not a universal admission bar |
| Task | Calibration of record | 10 valid runs/model: `claude-fable-5-1`, high, Claude Code; `gpt-6-astra`, high, Codex |
| Task metrics | Report | pass@1, pass@4, average reward per model, void counts and attribution |
| Batch | Reviewable | 100% tasks-check pass, calibration runs and provenance included |
| Batch | Task quality | At least 90% meet sanity, solvability and strict general difficulty |
| Batch | Reward hacking | Zero confirmed or unresolved cases |
| Batch | Faithfulness | No F-1; F0 allowed; aim at >=50% F1+ and >=15% F2+ |
| Batch | Trace accounting | 100% shared traces converted to env IDs or excluded with a reason |
| Batch | Multi-turn | >=10% environments include independently graded multi-turn tasks |
| Monitoring | Environment yield | Shared sessions producing an environment / ALL shared sessions |
| Monitoring | Difficulty yield | Shared sessions with an accepted task, primary `<=0.5`, F0+ / ALL shared sessions |
| Monitoring | Hard-task yield | Same yield difficulty cutoff, but F1+ / ALL shared sessions |

The yield table calls primary `<=0.5` “hard difficulty”; the task hard label is
`<=0.2`. Keep those named metrics distinct. Hard-task yield uses “hard difficulty”
by reference to the yield table plus its explicit F1+ requirement. The report
records this interpretation, rather than silently reusing the `<=0.2` label.
Five-run development screens are not ten-run calibration of record. Easy valid
tasks remain visible, but `arena deliverable` rejects nonqualifying batches.

## Faithfulness evidence

- F3 Replay retains conservative local 90% fixture and 70% trace-derived trap
  floors. Review must also verify fixture/key similarity to source; byte share
  is not proof of answer-key similarity.
- F2 Scenario permits invented/reconstructed fixtures, with verified source
  goal, capability, scenario, failure mode and grading-criteria witnesses.
  Byte share and trap percentages alone cannot establish those meanings.
- F1 Pattern requires a trace correction and native reproduction on its
  failure-mode checks. A check failure is a candidate pattern match, not proof
  of identical internal reasoning; inspect the actual failure before claiming
  semantic equivalence.
- F0 Inspired requires a concrete source goal and capability exercised by the
  synthetic task, with exact inspiration evidence. It is delivered in `F0-inspired`.
- F-1 Unrelated has no qualifying recoverable grounding; never accepted/delivered.

`quality.trace_alignment` quotes actual user turns and links substantive checks.
Fresh ledger regeneration verifies source quotations. Independent review checks
the claimed preservation; merely quoting the trace is not sufficient semantics.
`initialize_scenario` handles an empty starting fixture with a source-verified,
explicitly synthetic context. It cannot overwrite recovered files; context and
supplements both earn zero recovered-source credit.

## Capability construction

Fresh author sessions now use capability-plan version 2. In addition to the
mechanisms below, they provide independently intervenable core judgments and
a causal DAG; a candidate/criterion matrix with verbatim step-available evidence;
applicability-changing and whole-answer-invariant decoy controls; cross-decision
coupling; and competent retrieval/computation baselines, including complete
successful outputs with an empty `fails` list. They must follow every applicable
public rule; success is not a validity defect or incapability evidence. The controller
records the minimum version before authoring and preserves it across stalls.
Legacy version-1 repairs retain their old version and consumed budgets.
Every version-2 source intervention checks all semantic objectives and its exact
change scope through the exported grader. Review checks meaning, not just links.
The reviewed `optimal_subset` assertion enables public globally constrained
allocations with exact arithmetic and all valid optimal ties accepted.
These stricter local construction controls do not change specification thresholds
or establish empirical hardness. No synthetic first-draft-yield claim follows.

Stage `quality.capability_plan` before the instruction and scenario supplements.
The scenario tools enforce a nonempty supported outline before fixture mutation;
full mechanism/decision/control links are validated on the completed draft.
Each mechanism links decisions, objective-driving traps, executable genuine
shortcut counterexamples, coherent source-change controls and the judgment
remaining after competent retrieval/computation:

1. Authority/time: issuer, authorization, scope, effective time and reporting
   cutoff interact; newest/majority/summary shortcuts are sometimes wrong.
2. Artifact repair: plausible classification, dependency or double-count errors
   in a professional draft; preserve correct work and never expose an error map.
3. Semantic collisions: coherent near-misses satisfy different subsets of the
   entity, measure, eligibility and time criteria; every discriminator is public.
4. Coupled decisions: local choices interact through published shared constraints;
   use reviewed bounded assertions and accept all valid alternatives/optimal ties.
5. Revision cascades: real new evidence changes an upstream judgment and its
   consequences while unaffected decisions remain independently correct.

Controls prove discrimination/causal validity, not that models will make the
mistake. Review checks each counterexample implements its named shortcut.
Native calibration measures both exact targets, with partial-credit diagnosis
and failure attribution. Never claim guaranteed hardness from model stereotypes,
trap counts, chain length, decoy volume, refusal, invalid output, missing tools,
parsing loss, hidden standards or artificial time/turn limits.
The separate capability diagnostic counts contract failures as successes while
excluding voids, so malformed submissions cannot make that diagnostic pass.
Hardening comparisons and progress use the diagnostic too. A raw target hit alone
cannot end a lineage as `target-met`; both model capability diagnostics must agree.
Official pass@1 and the specification's acceptance metrics remain unchanged.

Rules may use `rule_sources:[{file,quote}]` in step-available fixture documents.
Exact text and availability are validated; witnesses go into private review
basis and are stripped from runtime checks. Future evidence, traversal,
unstated filter values and nonverbatim rules are rejected.

### Research rationale and transfer limits

- APEX-Accounting, arXiv `2607.27189` (July 2026), motivates coherent semantic
  judgment worlds. Its low pass@1 followed selection from 599 initially easy
  candidates, not a demonstrated magic first-generation recipe.
- SpreadsheetBench 2, arXiv `2606.29955` (June 2026), motivates controlled
  professional-artifact repair; its limited scaffold differs from these uncapped runs.
- OfficeQA Pro, arXiv `2603.08655` (March 2026), motivates measure-definition and
  revision-vintage challenges. Accessible parsed data must remain available.
- BrowseComp-Plus, arXiv `2508.06600` (August 2025), motivates partial-match hard
  negatives; stronger retrieval improves results, so more decoys is not a guarantee.

Freeze and retain first versions before measurement. Report easy candidates as
well as survivors. Do not report selected tasks as unconditional first-draft yield.
Neither this document nor adding generation rules implicitly launches paid runs.
