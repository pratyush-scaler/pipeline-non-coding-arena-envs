# R4: Pipeline map — blockers & repairs, difficulty hooks, how to run a build

Repository: `/Users/pratyushmohanty/Downloads/arena-envs-non-coding-v2`, HEAD `de81e15`
("v2 baseline: pipeline sources as of 2026-10-02 working tree"). Read-only analysis,
2026-10-02. All `file:line` references are to this checkout. Nothing in `pipeline/` was edited.

**What was executed (and what was only read).**

| executed | result |
|---|---|
| `.venv/bin/python -m pytest pipeline/tests -x -q` | **fails immediately: `No module named pytest`** (the venv has no pytest; the suite is `unittest`-based) |
| `.venv/bin/python -m unittest discover -s pipeline/tests -t . -f -q` (equivalent, fail-fast) | **`Ran 1893 tests in 389.502s — OK (skipped=1)`** |
| in-memory gate-runner demo (`gates.base.run_gates` + `run.verdict`) | a FAILing prerequisite gate makes its dependants SKIPPED and the chain verdict `unverified` (see §1.6 B1) |
| in-memory `dump.index.index_session` + `select.score.screen` + `select.categories.categorise` over the configured 1.8.0 dump (no files written) | 500/500 sessions read, 1260 seeds, 0 errors, 143 s; target levels F3 5 / F2 297 / F1 167 / F0 492 (§3.2) |
| read-only survey of `datasets/accepted_500_traces` (data.json, outcomes.json, workspaces, manifest.json, inventory.json, source zip listing) | 11,052 of 26,773 inventory files are absent on disk (§3.2) |
| prompt-size measurement by importing the modules | designer system prompt = 85,974 chars / 12,209 words (§2.2) |

Everything else below is from reading code; where a claim rests only on reading, it says so.

---

## 0. The findings that matter most

1. **A trap-count or trap-provenance blocker is never repaired.** `trap.beatable` and
   `difficulty.axes` declare `requires=("trap.faithful",)` (`gates/difficulty.py:615-619`). When
   `trap.faithful` FAILs (e.g. `below-trap-floor`, `MIN_TRAPS=5`, or `trace-underused`), its
   dependants are SKIPPED (`gates/base.py:152-157`), and `run.verdict` maps any SKIPPED to
   `unverified` before it looks at FAIL (`run.py:58-65`). `orchestrate._build_one` returns an
   `unverified` gate verdict without spending a repair (`orchestrate.py:593-595`). Executed
   demo: `[('trap.faithful','fail'),('trap.beatable','skipped'),('difficulty.axes','skipped')] -> ('unverified', 2)`.
   Draft validation does not catch it first, because `validate` only requires ≥1 trap
   (`author/validate.py:404-409`). The 5-trap floor exists only in the gate
   (`gates/difficulty.py:117-122`, `config.py:280`). The same cascade happens when `bundle.structure` fails.
2. **The single strongest HOW-forcing rule is `validate._hidden_rules`** (`author/validate.py:1291-1391`).
   Every `where` clause, `matches` regex **and every `extract` parsing pattern** (`:1148-1149`) inside a
   check target must be quoted. The quote must contain the clause's column (if the header is visible
   in the fixture) and *every* literal it tests, together in one sentence of 12–600 characters
   (`:1057-1060`). The sentence comes either verbatim from the step instruction (`rule_quote`) or
   verbatim from a step-available fixture file (`rule_sources`). This contradicts the designer prompt's
   "Name no columns, filters, joins or operations in the instruction" (`author/agent_designer.py:744-746`).
   The hardening brief makes it worse: it tells the author to publish each new filter **in the step
   instruction** and put the sentence in `rule_quote`, and it never mentions `rule_sources`
   (`harden.py:437-444`). Parsing a number out of prose with `extract` is implementation, not a grading
   rule, yet it triggers the same requirement.
3. **Dense tasks are capped at 12 objectives and lean tasks are padded to 8.** `BAND_LIMITS = core 4–6,
   floor 0–2, stretch 1–4` (`author/quality.py:19`, enforced `:394-399`) and `MIN_OBJECTIVES = 8`
   (`policy.py:393`; enforced `author/validate.py:575-580` and `gates/integrity.py:701-706`). Other
   NOT-REQUIRED shape rules sit on top:
   - ≥4 distinct core decisions (`quality.py:400-403`, plus `adversarial.py:239-240`)
   - ≥70% of weight on "semantic core/stretch", at task level and per step (`quality.py:364-368, 404-410`)
   - ≤35% of reward per check (`validate.py:566, 601-609`)
   - ≤30% of weight gated behind one check (`validate.py:641, 644-687`)
   - non-uniform weights (≥3 distinct weights when there are ≥6 objectives) (`validate.py:587-596`)
   - a 25-character `weight_basis` (`validate.py:610-621`)
   - ≤50% "read-off" weight (`author/designer.py:816-828`)
4. **The difficulty self-audit and the v2 "adversarial" construction plan block, but no Arena rule
   requires them.**
   - `difficulty_case`: ≥8 pitfalls, 60/40-character fields, one counterexample per trap
     (`quality.py:525-693`).
   - Its executed form inside `quality.controls`: a misreading counterexample may fail only the checks
     its trap drives, ≤50% of objectives, and ≥1 objective must pass (`assurance.py:217-260`).
   - `capability_plan` v2: 4 independent bottlenecks with exact-scope interventions, a ≥3-predicate
     collision with 1 full + 2 partial matches, a coupling, and both kinds of tool baseline
     (`adversarial.py:159-322`, `source_controls.py:119-138`).
   - Every new authoring session is forced onto v2 (`agent_designer.py:1480-1503`).
5. **Several difficulty-ish heuristics still block, although POLICY says phase 3 is validity only.**
   - `quality.axes` ≥2 and `levers` beyond Carry block (`quality.py:355-358`), even though the
     equivalent trap-derived `difficulty.axes` gate was demoted to WARN for exactly that reason
     (`gates/difficulty.py:574-602`).
   - The 50% read-off rejection (`designer.py:816-828`).
   - Trap floors: `below-trap-floor`, plus `trace-underused` at 70/55/40/30% by source tier
     (`gates/difficulty.py:194-201`, `select/priority.py:109`).
6. **The repair loop is fragile at scale.**
   - There are 2 passes in total across draft validation, gates and review (`policy.py:523`).
     `ARENA_GATE_REPAIRS` cannot raise this, because `repair.admissible` caps at
     `policy.MAX_REPAIR_PASSES` (`repair.py:241-243`).
   - Any finding whose normalised text, numbers included, recurs from an earlier pass is terminal
     (`repair.py:255-263`), and the finding *count* must strictly shrink within a stage (`:271-280`).
   - With dozens of lexical validator findings per draft, one unfixed nit ends the candidate.
   - Solver-autonomy review findings are rendered `Solver autonomy …` and classified as stage `gates`
     rather than `semantic-review` (`repair.py:285-297`, `author/brief.py:219-231`). The "did not
     shrink" comparison against an earlier gate pass, which the stage split was written to avoid
     (`repair.py:265-270`), can therefore return.
7. **A target-F3 seed that drops below 90% fixture fidelity is blocked rather than demoted to F2.**
   `bundle.ledger` applies `CATEGORY_FIXTURE_FLOOR[ledger.category]`, and the build sets `category`
   to the *target* level (`orchestrate.py:542`, `gates/bundle.py:216-230`, `policy.py:480-485`).
   CLAUDE.md says such a task "ships as F2".
8. **The 1.8.0 dump reads without error, but the local copy is partial.**
   - Only 15,721 of 26,773 inventory files are on disk. The extraction looks deliberate: all files
     ≥2 MB in the 282 `noncode_sids.txt` sessions are missing (958 files, 4.75 GB, mostly PNG/PDF,
     plus 72 JSON, 24 CSV and 242 HTML snapshot entries). The other 218 sessions mostly have no blobs.
   - Effect: 134,103 `missing_or_unsafe_snapshot_body` omissions.
   - The 1.8.0 outcomes carry almost no `steerability|failure` (8 in 500 sessions). As a result
     970/1260 seeds have 0 corrections and only 39 have ≥2. The existing `pipeline-artifacts/tiered.json`
     has tier counts {2: 1, 3: 38, 4: 922} and no tier 1. Only 5 seeds target F3.
   - Nothing checks the dump's `schema_version` (§3.2).
9. **Things the docs say happen in the build that do not.**
   - `arena build` never runs `harbor check`. Only `release` reads a retained receipt
     (`release.py:494-501`), so `./arena tasks-check <tree>` must be run by hand.
   - The post-calibration gates (`calibration.bands`, `calibration.validity`, including the
     `no-variance` blocker that would reject an all-fail task, `gates/integrity.py:517-520`) are wired
     only to `arena gate --calibration` (`run.py:52-55, 83-85`).
10. **A malformed reviewer receipt holds the task without retry.** A bad quote, a missing field or a
    stale prompt hash makes the review `unverified`, which is held without repair or re-review
    (`orchestrate.py:268-278, 612-614`; `review.py:526-631`).

---

## 1. Blocker and repair map

### 1.1 Where a candidate can stop (build path, `orchestrate._build_one`, `orchestrate.py:391-653`)

```
select (classify.survives)                 -> not a row in classified.json at all
extract + ledger.redaction.minimize        -> raise  => status "error"           orchestrate.py:438-441
design (agent_designer.design)
   privacy.scan(fixture) raise             -> status "error"                    agent_designer.py:1743-1745
   reject_seed                             -> status "reserve"                  agent_designer.py:1866-1877, orchestrate.py:635-640
   140 tool turns / 6 failed turns         -> status "unverified" (stalled)     agent_designer.py:209-210,1799-1923; orchestrate.py:629-634
draft validation (validate_submission)     -> findings "Draft validation: ..."  orchestrate.py:503-519
   validation_unverified (OSError etc.)    -> status "unverified", no repair
   otherwise                               -> repair pass (admit_repair) or "blocked"
build/ledger/naming/probes exception       -> status "error"                    orchestrate.py:530-569, 641-646
gate chain (run_bundle, PRE_CALIBRATION)   -> verdict green | blocked | unverified   orchestrate.py:571-600
   + exported controls after gates         -> appended as blocked                orchestrate.py:573-581
   blocked                                 -> repair pass or "blocked"
   unverified (ERROR or SKIPPED anywhere)  -> status "unverified", NO repair     orchestrate.py:593-595
semantic review (_review_candidate)        -> green | blocked | unverified       orchestrate.py:606-621
   blocked (semantic rejection)            -> repair pass or "blocked"
   unverified (receipt/model problems)     -> status "unverified", NO repair
repair budget exhausted                    -> "blocked"                          orchestrate.py:623-626
validated                                  -> screened by calibrate_batch        orchestrate.py:766-801
```

Only `validated` tasks are screened (`orchestrate.py:781-786`). `arena screen` separately re-runs the
gate chain and skips any bundle that is not green unless `--include-unvalidated` is passed
(`screen.py:809-829`). Nothing is deleted; every stop leaves its receipts on disk.

### 1.2 Repair mechanics

| rule | where | value / behaviour |
|---|---|---|
| Budget | `policy.MAX_REPAIR_PASSES` `policy.py:523`; `orchestrate.GATE_REPAIRS` `orchestrate.py:175-177` | **2 passes per candidate, shared** by draft validation, the gate chain and semantic review. `ARENA_GATE_REPAIRS=0` disables repair. A larger value is still capped at 2 by `repair.admissible` (`repair.py:241-243`) and `checkpoint.repair_budget` (`checkpoint.py:85-98`) |
| One design attempt | `orchestrate.DESIGN_ATTEMPTS = 1` `orchestrate.py:180` | each repair is a full designer session (`revision=True`, up to 140 tool turns) seeded with the previous spec plus the findings (`orchestrate.py:474-482`) |
| Citation | `policy.REQUIRE_FINDING_CITATION` `policy.py:535`; `repair.cites_location` `repair.py:208-217` | refused only if **no** finding cites a path, file, gate code, `Semantic review <id>:`, step or `chk_` (`repair.py:234-239`) |
| Repeated finding | `repair.admissible` `repair.py:250-263`; `fingerprint` `:171-181` | a fingerprint (lowercased, whitespace-collapsed, first 400 chars, **numbers kept**) seen in **any** earlier pass is terminal |
| Monotone shrink | `repair.py:265-280`; `finding_stage` `:285-297` | the finding count must strictly drop relative to the last earlier pass of the same stage (`draft-validation`, `gates` or `semantic-review`). The stage comes from a prefix: `Semantic review ` → review; `Draft validation:` / `source changes do not exercise` → draft; **everything else → gates**, which includes `Solver autonomy …` |
| Disposition | `repair.disposition` `repair.py:336-356`; `orchestrate._repair_refused` `orchestrate.py:376-389` | writes `verification/repair-disposition.json` (`repairable: false`); status `blocked`; kept on disk |
| Never fed back | `policy.REPAIR_FEEDBACK_EXCLUDES` `policy.py:561`; `repair.feedback` `repair.py:11-49` | solver answers and per-episode rewards are never passed back |
| Re-check after a validator fix | `arena build --revalidate-blocked REASON` (`orchestrate.py:825-827`) | re-runs blocked, unchanged artifacts and keeps the remaining allowance |
| Stalled design | `--continue-stalled` (`orchestrate.py:822-824, 415-452`) | one fresh session seeded with the stalled draft; never automatic |

**What a repeated finding does:** `admit_repair` returns `(False, reason)`, then
`_repair_refused` → status `blocked`, `repair-disposition.json`, no further passes, not screened.

**Findings that "discard" a candidate** (it stays on disk and is not screened or delivered):
`reserve` (reject_seed); `error` (privacy preflight, minimisation, build/ledger/probe exceptions);
`unverified` (stall, gate ERROR **or SKIPPED cascade**, unverifiable draft validation, unverifiable
review); `blocked` (repeated finding, no shrink, uncited, budget spent).

### 1.3 Inventory

Columns: **file:line · code · trigger · effect · class**. Class: **REQ** means validity or safety that
Arena's spec or anti-reward-hacking needs (plumbing included). **NOT** means style, quota, band,
difficulty heuristic, a HOW-forcing implementation, a redundant duplicate, or a known
false-positive heuristic. A qualifier follows where needed. "repair" means the finding enters the
repair loop.

#### A. Selection (`./arena select`, before authoring)

| file:line | code | trigger | effect | class |
|---|---|---|---|---|
| `select/score.py:36-92` | K1–K7 kill filters | K2: `n_turns < 2` (299 of 1260 seeds in the 1.8.0 dump). K3/K4/K5: env toggles `ARENA_FIXTURE_LED` / `ARENA_AUTHORED_FIXTURES` (both default on, `:95-104`). K1/K6/K7 apply only to pre-evidence indexes | seed dropped | REQ (plumbing) |
| `select/classify.py:89-93, 143-145` | `requires_execution` | the LLM classifier decides the work can only be judged by running it | `survives=False` | REQ (CLAUDE.md scope) |
| `select/classify.py:396-413` | record refused | gradable verdict without inspected user request plus supporting material, or citing unread evidence | the classifier must re-read (32 turns) | REQ (evidence honesty) |
| `select/classify.py:485-490, 301-332` | `survives` | gradable ∧ non-coding ∧ truth source ∈ `KNOWLEDGE_WORK_TRUTH` ∧ deliverable not code/none ∧ a route (≥2 usable corrections, or `fixture_task` with ≥2 verified evidence hashes) | not built | REQ (scope); the route rule is local |
| `select/classify.py:510-542`, `cli.py:554-557` | `--need` | classification stops descending tiers after N survivors (**default 6**) | builds starve if `-n > need` | operational |
| `orchestrate.py:842-845` | stale classification | a surviving row's `evidence_schema` ≠ `arena-pipeline/evidence/1` | build exits | REQ (plumbing) |
| `select/categories.py:83-93` | target level | rr ≥0.64 ∧ corrections ≥2 → F3; corrections ≥2 ∨ rr ≥0.52 → F2; corrections ≥1 → F1; else F0 | no level blocks authoring | n/a |

#### B. Authoring-time hard stops (`author/agent_designer.py`)

| file:line | code | trigger | effect | class |
|---|---|---|---|---|
| `ledger/redaction.py:532-589` (called `orchestrate.py:440-441`) | minimisation refusals | unsupported or overlapping privacy repair, or private material left after minimisation | status error | REQ (privacy) |
| `agent_designer.py:1743-1745` | privacy preflight | `privacy.scan(environment/files)` finds credentials, email or SSH endpoints | raise → error | REQ |
| `agent_designer.py:1480-1503` | construction protocol v2 | new sessions write `verification/construction-protocol.json` with `minimum_version: 2`; `check_spec` then requires a staged v2 plan (`:1373-1377`) | locks in all of D3 below | NOT (construction quota) |
| `agent_designer.py:209-210, 1919-1923` | stall | 140 response turns, or 6 consecutive turns in which every tool call failed | unverified; draft retained | REQ (plumbing) |
| `agent_designer.py:1930-1970` | reject_seed receipt | reason <200 chars or no verbatim fixture quote | the call is refused (not final) | REQ (plumbing) |
| `author/scenario.py` (via the `write_scenario` description, `agent_designer.py:865-873`) | supplement limits | ≤32 KiB per file, ≤128 KiB total, inside the category fidelity allowance; recovered files immutable | tool error | REQ (provenance) |

#### C. Mandatory draft validation — `validate_submission` → `check_spec` (`agent_designer.py:1370-1445, 1470-1477`)

Order inside `check_spec`:
1. `production_problems(draft, bundle, authoring=True)` and `validate(draft, bundle)` (`:1407`)
2. `citation_problems` (`:1408-1409`)
3. `alignment_problems(required=True)` (`:1410-1411`)
4. only if clean: `derive_solution` + `verify_solution` (`:1419-1427`)

Every problem becomes `Draft validation: <problem> [authoring/spec.json]` and goes to repair
(`orchestrate.py:507-519`). The same `production_problems` (with `authoring=False`) and `validate`
re-run in the gate chain as `quality.production` (`quality.py:696-708`), where each is a BLOCKER coded
`production-contract`.

**C1. `author/quality.py::production_problems`** (`:320-510`)

| line | rule | class |
|---|---|---|
| 325-344 | step contract compiles; outputs exist, are contained, are `.json`; supported JSON-schema subset (`contracts.schema_problems`) | REQ |
| 349-353 | duplicate objective fingerprint (same actual/target/assertion/tolerance) | NOT (quality; duplicates `designer.py:769-793`) |
| 355-356 | `quality.axes` must list ≥2 of inference/execution/restraint | **NOT** (difficulty self-declaration; the gate equivalent is WARN-only, `gates/difficulty.py:579-583`) |
| 357-358 | `quality.levers` needs a lever other than carry | **NOT** (same) |
| 359-360 | `novelty` ≥30 chars | NOT (style) |
| 361-363 | `semantic_checks` ⊆ objectives | plumbing |
| 364-368 | ≥70% of objective weight on semantic, non-floor checks | **NOT** (quality heuristic; hard-coded `.7`, while `policy.MIN_SEMANTIC_WEIGHT_SHARE` is marked declarative, `tests/test_spec_acceptance.py:1785`) |
| 369-371 | `present/contains/matches/subset_of/superset_of/row_count` or literal targets cannot be semantic | NOT (feeds the 70% rule) |
| 372-391 | decisions: distinct ids, question + shortcut + sources, each source a fixture file; every semantic check in exactly one decision | NOT (construction bookkeeping) |
| 392-393 | `source_controls.problems` (below, C5) | mixed |
| 394-399 | **BAND_LIMITS** core 4–6, floor 0–2, stretch 1–4 per task (max 12 objectives; stretch mandatory) | **NOT** (band quota; rejects dense tasks) |
| 400-403 | ≥4 distinct core decisions | **NOT** |
| 404-410 | each step ≥70% substantive core/stretch weight | **NOT** |
| 411-412 | each step has an output contract | REQ |
| 413-418 | `requires` only on objective core non-literal, non-presence checks | NOT (gating style) |
| 419-425 | `actual` addresses a declared JSON field | REQ (plumbing) |
| 426-433 | `unordered_paths` must address an array | REQ (plumbing) |
| 434-436 | column-only `[]` comparisons with equals/set/multiset/subset/superset | REQ (lost row associations = shortcut credit) |
| 437-440 | record arrays may not use `set_equals` | REQ (a repeated row must lose credit; Arena 260927) |
| 441-450 | every required schema leaf has a semantic check or a ≥30-char "presentation only" rationale | NOT (coverage style) |
| 451-476 | `source_evidence` quotes ≥15 chars verbatim, with role; ≥2 cited files | NOT (bookkeeping) |
| 477-485 | every decision source cited, and exercised by a source case | NOT (deferrable; see C5) |
| 486-488 | ≥2 counterexamples, ≥1 alternative | REQ (alternatives prove a correct answer phrased differently passes) |
| 489-502 | counterexample shape; **every objective and every non-integrity guardrail is failed by some counterexample** | REQ (dead-check prevention) |
| 503-504 | `untested_surfaces` declared | REQ (standing rule) |
| 505-506 | solution keys == output files | REQ (plumbing) |
| 507-508 | (authoring only) `difficulty_case_problems` (C4) | **NOT** |
| 509 | `capability.plan_problems` (C3) | **NOT** |

**C2. `author/validate.py::validate`** (`:160-488`)

| line | rule | class |
|---|---|---|
| 199-293 | projections: name, file exists, parser registered, concat/join/stem_overlap sources declared, parse runs, produces rows, join key exists | REQ (grader runs) |
| 297-356 | checks: unique id, known assertion, non-empty `basis`, guardrails ungated, `actual` present, objective `actual` is `{op: field, path}`, valid `matches` regex, target present, literal target has `why` (`_walk` `:100-109`) | REQ |
| 358-384 | two objectives write the same or nested path | REQ (reference assembly) |
| 386-391 | `requires` references a declared check | REQ (plumbing) |
| 393-395 | ≥1 guardrail | REQ in effect, because controls require a `fixture_intact` guard to fire on tampering (`assurance.py:139-146`) and targets are recomputed from the fixture |
| 404-409 | ≥1 trap | NOT (local; Arena asks for traps but sets no count) |
| 413-418 | `Trap.validate` (`traps.py:222-268`): trace_derived needs citation, allowed correction class and quote; authored needs grounding and `grounded_in`; `beatable_by`, `probe`, `checks` | REQ for provenance honesty; the rest NOT |
| 419-427 | trap checks declared | plumbing |
| 435-440 | a trap's probe may not be `golden`/`untidy_correct` | plumbing |
| 441-454 | authored `grounded_in` is a fixture file; trace_derived has `derived_from` and `quote` | NOT (local) |
| 456-473 | each deliverable is named in its owning step's instruction | REQ (clear output path) |
| 474 → 644-687 | `_gating_concentration`: one check gates >30% of reward through `requires` (`MAX_GATED_WEIGHT_SHARE`, `:641`) | **NOT** (rubric shape; unreachability is caught later by attribution) |
| 475 → 569-630 | `_scoring_shape`: <8 objectives (`:575-580`); all weights equal (`:587-592`); ≥6 objectives with <3 distinct weights (`:593-596`); share >35% (`MAX_SINGLE_WEIGHT_SHARE`, `:566, 601-609`); `weight_basis` <25 chars or "important" (`:610-621`); weighted guardrail (`:624-629`) | **NOT** except the guardrail-weight rule (REQ plumbing) |
| 476 → 491-555 | `_second_step`: check assigned to an undeclared step (REQ); step-2 instruction <80 chars (NOT); own deliverable file (REQ); `new_information` <30 chars (NOT); step 2 has ≥1 objective (REQ) | mixed |
| 480 → 835-871 | **[T1] `_field_definitions`**: every schema field named in backticks in its step's instruction, and every leaf followed by ≥2 content words (`MIN_DEFINITION_WORDS`, `:718`), unless the schema `description` has ≥2 content words | REQ (Arena: field meanings); WHAT, not HOW; the escape is schema descriptions |
| 481 → 951-1042 | [T2] `_references`: every backticked path or command exists (fixture, deliverable, or tool installed in the image) | REQ (Arena: referenced paths exist) |
| 482 → 1291-1391 | **[T3/G3] `_hidden_rules`** — see §1.4 | REQ intent / **NOT as implemented (HOW-forcing)** |
| 483 → 1427-1482 | [T3] `_order_rules`: ordered `equals` on an array needs a published order, or must be unordered-aware | REQ |
| 484 → 1550-1607 | [T3b] `_unordered_contract`: set/multiset comparison needs the array declared unordered; `set_equals` needs `uniqueItems` | REQ (Arena 260927) |
| 485 → 1610-1637 | [T4] `_guard_shape`: a guardrail may not compare against derived values or guard a file written in the same step | REQ (Arena 260927) |
| 486 → 1650-1678 | [T5] `_history_references`: a step-2 field may not be defined by "your step-1 answer" | REQ (Arena 260927) |
| 487 → 1686-1719 | [T6] `_literal_consistency`: one spelling per backticked literal; `exactly \`x\`` matches the files' accents | REQ (Arena 260927) |

**C3. `author/capability.py::plan_problems`** (`:168-235`; `required=True` when authoring)

- v1: mechanisms with decisions, traps, shortcuts (policy ∈ `SHORTCUTS`) linked to failing
  counterexamples, source cases, and `tool_resistance` text; every objective-driving trap covered (`:189-231`).
- v2: `adversarial.problems` (`adversarial.py:159-322`):
  - a decision DAG covering every decision, acyclic (`:181-194`)
  - ≥4 bottlenecks with distinct, descendant-only interventions (`:216-240`)
  - ≥1 collision with ≥3 witnessed predicates, a full match, two partial matches with different
    violated sets, a counterexample, a source case and an invariant case (`:242-283`)
  - ≥1 coupling across 2 decisions (`:285-295`)
  - retrieval and computation tool baselines with complete outputs (`:297-321`)
- **Class: NOT** (local construction requirements; POLICY.md itself says "not new specification acceptance thresholds").

**C4. `author/quality.py::difficulty_case_problems`** (`:525-645`) and `_pitfall_problems` (`:648-693`)

- `hardest_decision`, `first_try_verdict` and `script_test`, each ≥60 chars (`:563-566`)
- one misreading per objective-driving trap (`:639-644`)
- misreading/why_plausible ≥40 chars, `diverges_on` ≥10 (`:586-589`)
- the named counterexample exists (`:590-595`), fails ≥1 driven objective (`:596-601`), fails nothing
  undriven (`:606-610`), does not fail every objective (`:614-618`), and fails ≤50% of objectives (`:619-623`)
- counterexamples are unique per trap, with no identical submissions (`:624-637`)
- pitfall hunt: ≥8 entries (`MIN_PITFALLS_CONSIDERED`, `:522, 652`); pitfall text ≥30 chars, `where`
  is a fixture file, planted names a trap, rejected has a reason ≥20 chars, every trap planted (`:660-692`)
- **Class: NOT** (process self-audit). Its executed twin lives in controls (E, `quality.controls`).

**C5. `source_controls.problems`** (`source_controls.py:17-58`, via `quality.py:392-393`)

- Each source case/invariant has a unique id, a reason, semantic `changes`, a corrected submission or
  patches, and `source_patches` that each replace exactly one existing span (`:24-55`): **REQ** when
  declared (a counterfactual must be coherent).
- `source changes do not exercise semantic checks [...]` — every semantic check needs a source case
  (`:56-57`): **NOT at build time**. Arena needs a source counterfactual only for a check no episode
  passes (`attribution.all_fail_problems`, `attribution.py:409-431`), so this could be deferred to
  the screen.

**C6. Citations and grounding**

| file:line | rule | class |
|---|---|---|
| `ledger/faithfulness.py:79-113` | trace_derived trap citation must be `<session>::msgN` and quote the next **user** message verbatim; one anchor per correction | REQ (provenance honesty) |
| `ledger/grounding.py:12-62` | `quality.trace_alignment` must contain `goal` + `capability` (required at authoring, `:27-28`); each role quotes a user message verbatim, explains `preserved`, links existing objectives | REQ (Arena: F0 needs goal/capability grounding; F-1 rejected) |

**C7. `author/designer.py::verify_solution`** (`:620-959`, runs once C1–C6 are clean)

| line | rule | class |
|---|---|---|
| 665-685 | every target evaluates | REQ |
| 690-703 | the derived reference passes every check and the contract | REQ (grader sanity) |
| 716-726 | no literal list targets (hand-typed answer set) | REQ (§0) |
| 736-761 | if a check plucks headings, the instruction must contain a scope keyword ("heading level", "any level", "top-level", "h1", "h2", "depth"…) | REQ intent (ambiguity); keyword-based, injects a canned "RULES OF SCOPE" block |
| 769-793 | two objectives with identical ≥3-member answers | NOT (quality duplicate) |
| 816-828 | ≥50% of derivable weight is "single-surface read-off" (no `difference/intersection/latest/sum/…/compare/if`, no filtered `rows/filter`, no join projection) | **NOT** (difficulty heuristic; §0 is measured separately by `answer_lookup`). **It also pushes authors into `where` filters, which trigger `_hidden_rules`** |
| 838-860 | nulls in the reference | REQ (unanswerable task) |
| 869-896 | ≥8-entry lists <50% distinct, or one value ≥25% | NOT (heuristic; false positive on legitimate label lists; duplicated by `grader.reference`) |
| 906-947 | empty deliverable (requires removed) scores >0.34 | REQ (reward hacking) |
| 948-958 | builds in scratch and runs `assurance.controls` (E, `quality.controls`) | mixed |

#### D. Build exceptions (no repair, status `error`)

`author/build.py:328-355`: `Check.validate` (`author/checks.py:1011-1056`) catches invalid band/kind,
non-positive tolerance and similar; symlinks; a deferred validation that fails. Normally already caught
by C7, which builds in scratch. Class: REQ (plumbing).

#### E. Gate chain — `run.PRE_CALIBRATION` (`run.py:31-50`) + `quality.production` (`run.py:74-76`)

Verdict logic: any ERROR → unverified; else any SKIPPED → unverified; else any FAIL → blocked
(`run.py:58-65`). Dependants of a non-PASS gate are SKIPPED (`gates/base.py:152-157`).

| gate (file) | BLOCKER codes (line) | class |
|---|---|---|
| `bundle.structure` (`gates/bundle.py:32-113`) | missing-file (38), schema-version ≠"1.4" (49-52), no-provenance (55-59), tool-schema (63-66), network ≠no-network (69-72), shared-verifier (75-79), rubric-step-mismatch (93-97), no-reward (101-104), missing-dimension (108-112). WARN: memory (82-87) | REQ (Harbor format, offline, separate verifier) |
| `bundle.ledger` (`gates/bundle.py:116-268`) | empty-ledger (128), bad-origin (139), uncited (145-148), unverified-anonymization (163-164), unverified-authored-scenario (173-174), unlabelled-synthetic (184-191), **below-fixture-floor (216-230)**, ledger-inventory (238-239), ledger-bytes (248-249), ledger-ratio (253-254), ledger-exact-copy (255-259), unledgered-fixture (260-265). WARN: no-source-tier (204-208) | REQ, **except below-fixture-floor on a target-level category = NOT** (should demote F3→F2, §0.7) |
| `contract.completeness` (`gates/findings.py:187-243`) | no-basis (202), no-instruction (208), empty-basis (219), unpublished-rule = **zero** lexical overlap (225-230). WARN: thin-publication <45% (231-235) | REQ (low false-positive rate: zero overlap only) |
| `contract.enumeration` (`findings.py:319-405`) | grader-syntax (330), hidden-enumeration (346-352, 392-397). WARN: possible-accept-list (399-404) | REQ (kw006) |
| `contract.ambiguity` (`findings.py:482-581`) | undefined-category (<4 definition words, 533-541); overlapping-categories (Jaccard ≥0.5 with no lexical precedence word; WARN if non-English or polarity contrast, 565-579) | REQ intent / **heuristic with a recorded false-positive history** (comments at 512-518); demote candidate (the review checks ambiguity semantically) |
| `grader.normalisation` (`findings.py:696-745`) | type-sensitive-compare (733-738), float-equality (739-744). WARN: numeric-only-type-check, exact-string-compare. Applies only to custom grader code; the shared runtime is exempt (155-173) | REQ (kw002) |
| `grader.oracle` (`findings.py:752-826`) | unjustified-literal-target (787-791), no-derived-targets (797-801), no-oracle (805), literal-answer-key (821-824). WARN: literal-target | REQ (§0) |
| `grader.contract_probe` (`gates/contract.py:161-247`) | guard-fails-on-wrong-answer (223-227), unordered-list-graded-in-order (232-236), order/repeat/omission-not-graded (237-245); **reference ≠1 raises → ERROR → unverified, no repair** (184-186). WARN: unscored-section (147-151), agreement-claim (153-157) | REQ (Arena 260927) |
| `env.step_isolation` (`findings.py:845-964`) | unmarked-step (868), unverified-step-contract (895), later-step-material-in-fixture (927-930, 950-954; heuristics: only a later step uses the file, later answer values, ≥2 later-only identifiers, `:994-1184`), unverified-step-content (943). WARN: possible-forward-reference | REQ intent (step N+1 unreachable during N); heuristics with documented false-positive repairs |
| `env.policy_consistency` (`findings.py:1191-1223`) | counterparty-without-policy (1210) | REQ (applies only to scripted-counterparty modules) |
| `quality.controls` (`findings.py:1241-1274` → `assurance.controls` `assurance.py:103-279`) | controls-unrunnable (1260); control-failed per error. REQ errors: reference=1 per step (124-125); untouched 0 and guardrails pass (126-130); deleting an output fails the contract (132-138); tampering fires the integrity guard (139-146); counterexamples fail their declared checks (168-173); wrong solution not full reward (174-175); alternative ≠ reference and scores 1 (163-166); row controls (`row_controls.py:63-94`); source cases: corrected=1, stale fails (`source_controls.py:115-133`). **NOT errors**: misreading twin / passes no objective / >50% / stray fails (`assurance.py:229-260`); tool-baseline declared fails must equal observed exactly (197-203); strict v2 exact intervention scope (`source_controls.py:134-138`) | mixed (see list) |
| `answer.derivation` (`gates/integrity.py:69-250`) | no-lookup-probe (107-111), answer-stored lookup ≥1.0 (112-117), answer-stored-in-fixture (122-128). WARN: answer-partly-stored >0.5 | REQ (§0) |
| `leak.sweep` (`integrity.py:252-286`) | grading-artefact-in-fixture (267). WARN: dockerignore, answer-value-in-instruction (356) | REQ |
| `grader.reference` (`integrity.py:605-746`) | no-reference-answer (625), reference-unreadable (637), reference-null (647, 656), **reference-mostly-repeats (670)**, **reference-value-dominates (678)**, **objective-count <8 (703-706)**, weight-budget ≠100 (707-713), hand-typed-answer-set (716-725), zero-weight-objective (727-731); points-undocumented / points-drift / points-unverifiable (749-833) | REQ, except mostly-repeats / value-dominates = NOT (heuristic) and objective-count = **NOT** (user-local floor). weight-budget and points are local standing rules, auto-satisfied by `build.normalise_weights` (`author/build.py:200-258`) |
| `trap.faithful` (`gates/difficulty.py:77-224`) | no-traps (86-89), **below-trap-floor <5 (117-122)**, invalid-trap (136-139), ungrounded-trap (144-151), no-source-tier (160-164), bad-source-tier (166-170), **trace-underused (194-201)**. WARN: unknown-correction-count, below-scaled-trap-budget, no-corrections-to-exploit. **A FAIL here makes the chain `unverified` (SKIPPED dependants) → no repair** | **NOT** (trap quota and trace-exploitation floor 0.70/0.55/0.40/0.30 by tier, `policy.py:479`, `select/priority.py:109`); plumbing parts REQ |
| `trap.beatable` (requires trap.faithful) (`difficulty.py:227-345`) | no-golden (236), golden-below-one (240-244) = REQ; trap-unprobed (259-264), trap-drives-nothing (267-274), probe-no-score (275-278), **trap-not-discriminating (279-284)** = NOT (redundant with counterexample coverage in controls); plausible-wrong-no-score (309-313), plausible-wrong-scores-reference (324-330), untidy-correct-penalised (332-341) = REQ | mixed |
| `difficulty.axes` (requires trap.faithful) (`difficulty.py:561-610`) | WARN only: one-axis, no-restraint-axis, carry-only, sequence-lever | advisory |
| `hacking.resistance` (`difficulty.py:348-558`) | probe binding: missing/unbound/stale/diverges (363-365, `probes.py:1032-1055`), probe-missing (367-373), inapplicable-without-reason (378-385), seed-zero-objective (396-401), seed-zero-guardrail (402-407), destructive-no-score (419-422), destructive-survives (423-429), hack-probe-no-score (446-449), reward-hack-succeeds ≥1.0 (450-457), **answer-readable-in-fixture (471-482)**, empty-probe-missing (490-496), empty-probe-no-score (499-503), empty-deliverable-scores >0.34 (504-511), no-untested-declaration (550-556). WARN: reward-hack-partial, destructive-unprotected-target, empty-deliverable-partial, leverage-unmeasured, fixture-mostly-inert | REQ; **answer-readable-in-fixture has a false-positive class**: any distinctive scalar answer (string ≥4 chars, any non-integral float, |int| ≥1000; `probes.py:545-576`), such as a derived date, an entity ID chosen among candidates, or a total, that appears as a token anywhere in the fixture blocks, even though the agent still has to pick it (`probes.py:461-542`) |
| `quality.production` (`quality.py:696-708`) | production-contract = C1 (`authoring=False`) + C2 + `published_paths` [T1] (`:711-739`: input root + "read-only" + absolute output path in the built instruction) | per C1/C2; published_paths REQ (auto-generated) |

#### F. Semantic review (`orchestrate._review_candidate` `:249-289`, `review.review_problems` `review.py:526-631`)

The reviewer model is `ARENA_REVIEW_MODEL`, or `gpt-6-astra` unless the author is a `gpt-` model, in
which case it is Fable (`orchestrate.py:265-267`). The default author is `claude-opus-5`
(`config.py:195`), so **the reviewer defaults to GPT 6 Astra, a calibration model**. The review runs up
to 60 steps (`review.py:668`).

| line | code | effect | class |
|---|---|---|---|
| 557-558 | `verdict != pass` | blocked → repair | REQ (validity) |
| 559-561 | any of ambiguities / substantive_gaps / shortcut_risks / privacy_findings non-empty | blocked → repair | REQ |
| 556; `brief.py:172-216` | solver_autonomy missing, incomplete, `revise`, or any surface classified `task_specific_coaching` / `answer_or_grader_leak` | blocked → repair (`Solver autonomy …` findings, stage mislabelled as gates) | user-required design constraint (anti-HOW; keep) |
| 567-593 | calendar assessment when calendar edits exist | blocked/unverified | REQ (privacy/anonymisation) |
| 599-630 | every check row passes with reason ≥40 chars; passing objectives cite a verbatim fixture quote ≥15 chars; citation errors | `invalid review citation` → **unverified, no repair** | REQ for semantics; **holding the task on the reviewer's own receipt defects is NOT required** (re-run the review instead) |
| 528-552 | stale/foreign receipt, same model as author, harness/prompt changed, evidence hash changed | unverified (re-review) | REQ (plumbing) |
| 565-566 | `difficulty_advisories` must be a list; content never blocks | advisory | — |

The review prompt (`review.py:14-190`) already routes "too easy / recipe-driven / trap the instruction
solves" to `difficulty_advisories` (`:151-166`).

#### G. Screen (`screen.py`)

- `shippable_problems` (`:76-101`) and `summarize` (`:400-418`) hold the 10×2 qualification when any
  of these fail:
  - two models measured, with ≥5 valid episodes each after voids
  - effort `high`, `no_limits`
  - evidence problems (`release.calibration_measurement`)
  - attribution (`attribution.attribute` `attribution.py:181-247`: unattributed >0, contract share
    >30%, too few valid after voids)
  - all-fail obligations (`attribution.py:376-440`: source counterfactual, phrasing alternative,
    near-miss, unreachable checks)
  - trajectory hacks (`attribution.py:1005-1100`)
- **All REQ.** pass@1 never blocks (`screen.py:420-429`; `policy.DIFFICULTY_GATES_RELEASE=False`, `policy.py:194`).
- `arena screen` eligibility (`screen.py:809-829`): gate chain green; otherwise "not screened".

#### H. Qualify / release (`release.py`)

- `_qualify` (`:607-660`) refuses unless the screen is shippable (`:639-644`), the review model differs
  from the author (`:645-647`), and preflight passes (`:563-581`: gates green, privacy, provenance,
  novelty, reproducible export, controls, Harbor doctor).
- `_evaluate` checks (`:328-555`):

| check | lines | class |
|---|---|---|
| gates green | 350-355 | REQ |
| privacy | 356-357 | REQ |
| provenance | 358 | REQ |
| **novelty**: blocks if a released task shares the `session_id` or ≥80% fixture bytes (`corpus.py:33-47`) | 359-360 | **NOT** (one released task per source session is local) |
| runtime | 361-371 | REQ |
| reproducible export | 372 | REQ |
| controls | 373 | REQ |
| calibration: 10 valid per model, attribution, hacks, spec model set, effort/output/limits | 375-470 | REQ |
| blind solve: integrity only, no gate (`:295-325`) | 487-491 | — |
| harbor tasks-check retained receipt (`benchmark/tasks_check.py:254-264`) | 494-501 | REQ (receipt must exist; not produced by build) |
| faithfulness level F-1 + naming `a_f<level>_` (`ledger/levels.py:289-295`, `naming.py:78-111`) | 503-518 | REQ |
| reference solution is a deriving script, executed (`author/solution.py:316-348`) | 522-525 | REQ |
| semantic review | 526 | REQ |
| native oracle=1 / nop=0 | 528-540 | REQ |

#### I. Delivery / batch (`deliverable.py`, `deliver.py`)

- `acceptance_problems` (`deliverable.py:420-520`): the release receipt is accepted and bound;
  "release was decided under another policy version" (`:449-450`, `artifacts.policy_identity`
  `artifacts.py:82-92` hashes all `pipeline/*.py`, `*.md`, `rulesets/*.md`, CLAUDE.md and the
  lockfiles). Class: NOT Arena; local freshness hygiene (any pipeline edit un-accepts receipts).
- `batch_acceptance` (`:552-639`): Arena's six criteria. The batch-level "Task quality ≥90% under 0.5"
  sets `ok=False` (exit 1, `:1326`). REQ (Arena's batch criterion). It reports; it does not delete.

#### J. Hardening-only refusals (`harden.py`)

| rule | lines | class |
|---|---|---|
| ≤3 redesign attempts per lineage | `policy.py:547` | user rule |
| untargeted checks unchanged, checks not removed, `requires` unchanged, targeted weights not lowered, step inventory unchanged | 921-947 | NOT (measurement hygiene; reasonable) |
| faithfulness level may not fall | 1051-1053 | NOT |
| authored-trap / scenario-byte budget, trace-derived traps not dropped | 588-608 | NOT (faithfulness budget) |
| **new trap drives ≥2 objectives** (`MIN_CHECKS_PER_NEW_TRAP`) | 614-630 | NOT |
| plus the full validate + gate chain | 1028, 1072-1075 | as above |
| acceptance requires both official and capability pass@1 to fall on every model | 1099-1162 | progress rule, not validity |

#### K. Post-calibration gates — wired only to `arena gate --calibration` (`run.py:52-55, 83-85`; not in build/screen/release)

`calibration.bands` (`integrity.py:367-461`): dead-check, gate-below-band (BLOCK); too-few-core is WARN
because `BANDS_GATE_RELEASE=False`. `calibration.validity` (`:464-575`): invalid-evidence,
unclassified-zero, grader-changed-mid-campaign, **no-variance (517-520: every valid rollout the same
reward → BLOCK, contradicting "an all-fail task is admissible")**, non-numeric-reward,
right-answer-scored-zero.

### 1.4 HOW-forcing rules (instruction must reveal procedure)

| # | rule | file:line | what it forces | escape hatches | verdict |
|---|---|---|---|---|---|
| H1 | **`_hidden_rules`** | `author/validate.py:1291-1391` (quotes `:1249-1288`, lengths `:1057-1060`, clause needs `:1180-1218`, coverage `:1234-1246`) | For every `where` leaf clause, `matches` target and **`extract` regex** (`:1134-1150`): one quoted sentence (12–600 chars) containing (a) the column name, if that header occurs anywhere in the fixture text; (b) **every** compared literal (`eq/ne/in/not_in/gt/gte/lt/lte` values, except boolean, null and zero-thresholds); (c) words excluded by negative lookaheads; (d) ≥50% of the words a positive regex requires. Quotes must be verbatim in the step's instruction (`rule_quote`) or in a step-available fixture file (`rule_sources`) | `rule_sources` (fixture witness); `rule_terms` alias map (`:1350-1356`); computed/derived field names exempt (`:1164-1177`); parser metadata and structural fields exempt (`:1050-1056`); `in` lists may span several quotes (`:1381-1383`) | REQ intent (Arena kw006: no hidden grading rule). **NOT as implemented**: lexical; forces column+value co-occurrence; treats parsing regexes as rules; numbers must appear as digits ("5000", not "five thousand", unless aliased); pushes authors to restate filters in the instruction. Should become a semantic-review item, or accept any accessible-document witness without token co-occurrence |
| H2 | Hardening brief: publish every new filter in the instruction | `harden.py:437-444` | "Every filter a trap adds … is a rule the validator requires in that step's instruction: publish it there AS YOU INSTALL IT … put the exact sentence in the check's rule_quote" | none mentioned (omits `rule_sources`) | NOT (contradicts `agent_designer.py:402-416` "RULES LIVE IN THE WORLD") |
| H3 | Read-off share ≥50% rejects | `author/designer.py:816-828` | the author adds `where` filters or arithmetic so targets "derive", and each `where` then triggers H1 | sentinels excluded (`:811-817`) | NOT (difficulty heuristic) |
| H4 | `_field_definitions` | `author/validate.py:835-871` | every schema field named in backticks in its step's instruction, plus a ≥2-word meaning | schema `description` | REQ (WHAT, not HOW), but it inflates instruction length on dense schemas |
| H5 | Heading-scope keywords | `author/designer.py:736-761` | a "RULES OF SCOPE" block with one of the listed keywords when headings are graded | none | REQ intent; canned text |
| H6 | Order declarations | `validate.py:1427-1482, 1500-1607` | order or "any order" per graded array, in schema or definition | schema `"unordered": true` | REQ (WHAT) |
| H7 | Step-2 restatement | `validate.py:1650-1678`; prompt `agent_designer.py:820-825` | step 2 must restate the step-1 facts and definitions it needs (fresh session) | — | REQ (harness reality) |
| H8 | `contract.completeness` | `gates/findings.py:187-243` | each check's `basis` shares ≥1 content word with agent-visible text | fixture text counts | REQ (weak; fine) |
| H9 | Text minimums | `validate.py:526-541` (80 / 30 chars), `quality.py:359-360` (novelty 30), `validate.py:610-621` (weight_basis 25) | prose padding | — | NOT (style) |

Counter-pressure (keep): the solver-autonomy review blocks task-specific coaching, reading orders,
join/filter recipes and decoy labels on any solver-visible surface (`author/brief.py:52-108,
172-216`). It pulls in the opposite direction from H1/H2. The designer prompt's WHAT-not-HOW rules
are at `agent_designer.py:376-400, 742-759`.

### 1.5 Count, band, weight and trap-floor rules

| rule | value | file:line | blocks? | class |
|---|---|---|---|---|
| `MIN_OBJECTIVES` | ≥8 objectives / task | `policy.py:393`; `validate.py:575-580`; `integrity.py:701-706`; prompts `agent_designer.py:719-723, 828` | yes (draft + gate) | NOT (user-local, 2026-09-25) |
| `BAND_LIMITS` | core 4–6, floor 0–2, stretch 1–4 ⇒ **max 12**, stretch ≥1 | `quality.py:19, 394-399`; prompt `quality.py:182-189` | yes | NOT |
| distinct core decisions | ≥4 | `quality.py:400-403`; `adversarial.py:239-240` | yes | NOT |
| semantic weight | ≥70% task and per step | `quality.py:364-368, 404-410` | yes | NOT |
| `WEIGHT_TOTAL` | objectives sum to 100 (equal per step) | `policy.py:384`; `build.py:182-258`; `integrity.py:707-713` | auto-normalised | local standing rule |
| `MAX_SINGLE_WEIGHT_SHARE` | ≤35% task reward per check | `validate.py:566, 601-609` | yes | NOT |
| `MAX_GATED_WEIGHT_SHARE` | ≤30% behind one `requires` root | `validate.py:641, 644-687` | yes | NOT |
| weight diversity | not all equal; ≥3 distinct when ≥6 | `validate.py:587-596` | yes | NOT |
| `MIN_TRAPS` | ≥5 traps | `config.py:280`; `difficulty.py:117-122` | yes (and cascades to unverified) | NOT |
| scaled trap budget | `max(5, 0.5·docs + 0.5·corrections + 0.25·objectives)` | `config.py:290-298`; `difficulty.py:123-134` | WARN | advisory |
| trace exploitation | distinct cited corrections / usable ≥0.70/0.55/0.40/0.30 (tier 1–4) | `difficulty.py:194-201`; `policy.py:479`; `priority.py:109` | yes | NOT |
| F3 trap share | ≥70% trace-derived | `policy.py:468`; `ledger/levels.py:120-125` | measures level only | — |
| F3 fixture fidelity | ≥90% | `policy.py:465, 480-485`; `bundle.py:216-230` | **blocks a target-F3** | NOT |
| `MIN_PITFALLS_CONSIDERED` | ≥8 | `quality.py:522, 652` | yes | NOT |
| `MISREADING_MAX_OBJECTIVE_SHARE` | ≤50% objectives lost per misreading; ≥1 passes | `policy.py:556`; `quality.py:614-623`; `assurance.py:238-251` | yes | NOT |
| new-trap routing (harden) | ≥2 objectives per new trap | `harden.py:614-630` | yes | NOT |
| contract share | ≤30% of valid episodes | `policy.py:343`; `attribution.py:219-228` | screen/release | REQ |
| unreachable checks | 0 | `policy.py:347`; `attribution.py:433-439` | screen/release | REQ |

**Dense tasks are rejected by:** BAND_LIMITS (12 max; core ≤6), the 70% semantic-weight rule (floor
checks crowd it), MAX_SINGLE/GATED shares, one counterexample per trap with exact-only failures
(`quality.py:606-610`, `assurance.py:252-260`), a source case for every semantic check
(`source_controls.py:56-57`), a ≥30-char rationale for every ungraded schema leaf
(`quality.py:441-450`), and `_field_definitions` for every field.

### 1.6 Bugs and inconsistencies found

- **B1 (executed) SKIPPED cascade ⇒ unverified ⇒ no repair.** `run.py:58-65` +
  `gates/base.py:152-157` + `orchestrate.py:593-595`. It affects every `trap.faithful` FAIL (5-trap
  floor, trace-underused, invalid/ungrounded trap) and `bundle.structure` FAIL. A minimal fix: treat a
  SKIPPED gate whose blocker is a FAILed prerequisite as `blocked`, or drop the `trap.faithful`
  prerequisite from `trap.beatable` and `difficulty.axes`.
- **B2 Solver-autonomy findings have the wrong repair stage.** `brief.repair_findings` (`brief.py:219-231`)
  emits `Solver autonomy …`, and `repair.finding_stage` (`repair.py:285-297`) maps it to `gates`.
  Mixed with `Semantic review …` findings, the shrink check compares against the earlier gate pass's count.
- **B3 F3-target fidelity floor blocks instead of demoting** (§0.7).
- **B4 Declared-axes rule still blocks** (`quality.py:355-358`), while the gate version was demoted
  (`difficulty.py:574-578`).
- **B5 Thresholds live outside `policy.py`.** BAND_LIMITS (`quality.py:19`), the 0.7 semantic share
  (`quality.py:367, 409`, against declarative `policy.MIN_SEMANTIC_WEIGHT_SHARE`), MAX_SINGLE/GATED
  (`validate.py:566, 641`), MIN_TRAPS (`config.py:280`), MIN_PITFALLS (`quality.py:522`),
  MIN_CHECKS_PER_NEW_TRAP (`harden.py:614`), read-off 0.5 (`designer.py:823`), empty-deliverable 0.34
  (`designer.py:932`, `difficulty.py:504`). POLICY.md claims "a threshold lives here or it does not exist".
- **B6 `extract` patterns are treated as grading rules** (`validate.py:1148-1149`), H1.
- **B7 Hardening brief omits `rule_sources`** (H2).
- **B8 `contract_probe` raises instead of finding** when the reference ≠1 (`contract.py:184-186`) →
  ERROR → unverified → no repair.
- **B9 `harbor check` never runs in the build.** CLAUDE.md lists it as phase 3; the code runs it only via
  `arena tasks-check` (`cli.py:470-487`), and release just reads the receipt.
- **B10 Post-calibration `no-variance` blocker** (`integrity.py:517-520`) contradicts all-fail
  admissibility. It is not wired into the automatic path.
- **B11 PRODUCTION.md concurrency defaults are stale.** It says `ARENA_PROVIDER_CONCURRENCY` 8 and
  `ARENA_MAX_API_REQUESTS` 2,500 (`pipeline/PRODUCTION.md:355-356`); the code uses 20 and 20,000
  (`config.py:321, 329`; `provider.py:66-67`).
- **B12 One unfixed lexical finding ends a candidate.** The repeat rule combined with long lexical
  finding lists (C1+C2 typically produce many) makes this likely (§0.6).

### 1.7 Minimal-blocker proposal (for discussion, nothing changed)

**Keep as blockers (REQ):**
- bundle.structure
- ledger integrity and synthetic labelling (not the target-level floor)
- schema / contract / step-contract plumbing
- T1 field meanings, T2 references, T3/T3b order, T4 guards, T5 history, T6 literals
- grader.oracle, normalisation, contract_probe, controls core (reference/untouched/missing-output/
  tamper/counterexample coverage/alternatives/row/source-case coherence)
- answer.derivation, leak.sweep, hacking.resistance (with the answer-lookup false-positive class narrowed)
- step isolation, privacy, provenance citations, trace_alignment goal/capability
- the review's validity arrays; screen attribution, all-fail obligations, unreachable, contract share, hacks
- release harbor receipt, deriving solution script, naming/F-1, native oracle/nop

**Demote to WARN or advisory (NOT):**
- MIN_OBJECTIVES, BAND_LIMITS, ≥4 core decisions, 70% semantic weight (task/step)
- MAX_SINGLE / MAX_GATED shares, weight diversity / weight_basis / text-length minimums
- declared axes/levers
- duplicate-answer and repeat/dominance heuristics
- the read-off 50% rule
- MIN_TRAPS, trace-underused, trap-not-discriminating
- difficulty_case (all of it, including the executed misreading-shape rules in controls)
- capability_plan v1/v2 and exact-scope source interventions
- source case per semantic check (defer to all-fail adjudication)
- ungraded-leaf rationale
- target-level fixture floor (demote the level instead)
- release one-task-per-session novelty
- reviewer receipt defects (re-run the review instead of holding the task)

**Rework H1** into a semantic-review question, or accept a document witness without token co-occurrence.

Any of these edits changes `policy_identity` and un-accepts every retained release receipt
(`artifacts.py:82-92`; see memory "Pipeline edits un-accept release receipts"). Unit tests assert many
of these blockers.

---

## 2. Difficulty hooks

### 2.1 Who authors and reviews

| role | model | effort / budget | source |
|---|---|---|---|
| Designer (author, repair, harden) | `claude-opus-5` (`ARENA_DESIGNER_MODEL` overrides) | `output_config.effort = "xhigh"`; ≤140 response turns; 128k max output; adaptive thinking on | `author/designer.py:38`; `config.py:195, 207`; `agent_designer.py:209-211, 1748-1750, 1832-1835` |
| Classifier | `claude-opus-5` (`ARENA_CLASSIFIER_MODEL`) at xhigh | ≤32 turns, 8192 tokens per turn | `select/classify.py:49, 382-384` |
| Semantic reviewer | `gpt-6-astra` by default (author ≠ gpt) | 60 steps | `orchestrate.py:265-267`; `review.py:668` |
| Calibration | Fable 5.1 in Claude Code, GPT 6 Astra in Codex, at `high`, no limits | 5×2 screen, 10×2 record | `policy.py:28-60, 98, 217, 230` |

### 2.2 Prompt assembly (the order the model sees it)

**System prompt** (`agent_designer.py:1748-1750`, `:1833`): `SYSTEM + "\n" + QUALITY_PROMPT`, 85,974
chars / 12,209 words (measured). Composition (sizes measured):

1. `SYSTEM` body `agent_designer.py:214-453`, with `{first_pass}` replaced by `FIRST_PASS_TRAPS`
   (`:458-792`, 22,534 chars) at `:794-796`.
2. `+ CAPABILITY_PROMPT` `author/capability.py:22-121` (7,149 chars) at `:797`.
3. `+ ADVERSARIAL_PROMPT` `author/adversarial.py:13-88` (5,208) at `:798`.
4. `+ CHALLENGE_PROMPT` `author/challenge.py:20-106`, plus `portfolio.PROMPT` `author/portfolio.py:13-71`,
   plus `brief.PROMPT` `author/brief.py:11-50` (12,664 together) at `:799`.
5. `+` GRADED FOLLOW-UP / SHAPE OF THE RUBRIC block `agent_designer.py:805-837`.
6. `+ QUALITY_PROMPT` `author/quality.py:21-294` (20,657; bands interpolated `:296-305`).

**Opening user message** (`agent_designer.py:1709-1746`), final order:

1. (repair/harden only) feedback block "Design or revise using the constraints and findings below…" (`:1734-1742`)
2. `AUTHORING_MANDATE` (`:95-117`) — or `REVISION_MANDATE` (`:124-132`) when `revision=True` (`:1733`)
3. `designer.CATEGORY_GUIDANCE[level]` (`author/designer.py:500-531`) (`:1724-1728`)
4. `_opening` (`:1506-1547`): session, domain, classifier failure mode, evidence inventory, counts,
   "BUDGET AND FLOORS" (≥5 traps, typical count, distinct-citation need by tier, ≥1 guardrail incl.
   `fixture_intact`, no twin answers, no literal lists, majority derived)
5. `TRAP_GUIDANCE` (`:64-71`) + `CONSTRUCTION_INTEGRITY` (`:73-90`)
6. SOURCE-FAMILY NOVELTY PREFLIGHT with peer briefs (`:1710-1716`)
7. capability-plan version note (`:1717`)
8. `TRAP_POLICY[level]` (`:140-199`)
9. stage_spec/submit_draft note (`:1720-1723`)

**Hardening** adds `HARDENING_BRIEF` (`harden.py:329-491`, 10,775 chars) plus one of `FIRST_ATTEMPT`
(`:503-520`), `TIGHTEN_ATTEMPT` (`:522-536`) or `REPAIR_ATTEMPT` (`:538-547`), assembled in
`harden.propose` (`:733-830`) and passed as designer feedback with `revision=True` (`repair.py:122-123`
uses the same path for qualification repair).

### 2.3 Key prompt sections to rewrite (quotes abbreviated; full text at the lines)

| section | file:line | gist / quote |
|---|---|---|
| Mandate | `agent_designer.py:95-117` | "design a task that is BOTH of EXCELLENT QUALITY and EXTREMELY HARD … pass@1 below 0.5 … aim for 0.2 … Do not count on anything making this task harder after you submit … run the TRAP HUNT … across all sixteen pitfall families" |
| How hard | `:220-230` | "EXTREMELY CHALLENGING, NOT UNPASSABLE … at most 2 times in 10 … an expert practitioner given ONLY the published evidence must be able to get every answer right" |
| Measured retrieval critique | `:232-248` | operator counts (pluck 492, filter 436 …); "If your target expressions are mostly pluck/filter/extract you have written a search query" |
| Worked example (easy vs hard) | `:250-266` | renovation tracker: stale deadlines, coupled shipments, unsatisfiable items |
| Volume is not difficulty | `:268-273` | "Put the trap where the computation happens" |
| Tools usage | `:275-317` | read every document fully, read_trace/list_corrections, run_parser, **evaluate every target**, check_spec, write_scenario |
| What makes a task good | `:319-374` | derived never stored; never hand-type; ≥2 axes; no guardrail quota; distinct decisions; counting conventions; weights relative per step |
| **WHAT not HOW** | `:376-400` | "Be exact about WHAT and silent about HOW … does NOT … name fixture files … say or hint that any document is revised, stale … restate a precedence rule, threshold or rate that a fixture document already states … list steps, joins, checks … MUST keep every sentence that decides a field's SCOPE, an EXCLUSION, a BOUNDARY or an EDGE-CASE CONVENTION" |
| **Rules live in the world** | `:402-416` | "Leave every precedence rule, threshold, exception and scope definition in the fixture document … Apply it in the grader from the document: bind the threshold … with `bind_rows` and `compare`, choose the governing revision with `latest` … A filter's public rule may be witnessed by `rule_sources` … or by `rule_quote` from the STEP INSTRUCTION. State it as a criterion in the domain's terms, never as a column test" |
| **Instruction is the contract** | `:418-449` | field definitions; references exist; **NO HIDDEN RULES** (`:433-445`: "Every clause's column and every literal it tests … must appear together in one quoted sentence … `rule_terms` …"); ORDER IS A RULE (`:446-449`) |
| First-pass framing + ARENA QUALITY BAR | `:458-530` | "THE FIRST PASS IS THE ONLY PASS … Nothing screens this draft for difficulty after you submit it" |
| What defeats a frontier model | `:532-571` | premise change, governing conflict, residue, plausible misreading, vary types, populations 9–130 rows, one added trap does not move an easy task, implicit invalidation, near-miss decoys |
| **Trap hunt (16 families)** | `:572-633` | revised premise … vocabulary variance; family→type mapping `:627-633` |
| Make traps confusing, never unfair | `:635-696` | near-miss decoys, decisive qualifier placement, vocabulary variance, expert-only errors, interaction/mix (≤2 per family), small populations, implicit cascade, long means deep, full-success arithmetic, every failure traces to a trap, safeguard territory |
| Every trap genuine | `:698-717` | resolvable / live / failable / passable / reachable / zero on untouched |
| Rubric size & weight | `:719-723` | "at least 8 objective checks … sum to exactly 100" |
| Reviewer rejects as not hard | `:725-740` | fully specified census; trap the instruction solves; one calculation as several decisions |
| **Criteria, not recipes** | `:742-759` | "Name no columns, filters, joins or operations in the instruction … No pre-judged evidence … Step 2 changes a JUDGMENT" |
| Self-audit spec | `:761-792` | hardest_decision / first_try_verdict / script_test / misreadings / pitfalls_considered |
| Rubric shape (mechanical) | `:827-837` | 8 objectives, guardrails weight 0, ≤35%, weight_basis, ≤30% gated, ≥5 traps |
| Production contract (assertions, bands, 70%) | `quality.py:21-294`, esp. `:163-216` | optimal_subset/path semantics; grade every substantive field; bands "Per TASK … 4-6 core, at most 2 floor, 1-4 stretch"; "the instruction never announces which document is stale or which wins" (`:204-206`) |
| Capability-first construction | `capability.py:22-121` | mechanisms authority_time / artifact_repair / semantic_collision / coupled_decisions / revision_cascade; trace alignment instructions |
| Adversarial v2 | `adversarial.py:13-88` | decision DAG, ≥4 bottlenecks, collisions, couplings, honest tool baselines |
| Challenge construction | `challenge.py:20-106` | global feasibility, near-miss lattice, inverse identification, non-monotonic revision, ablation, stretch checks |
| Portfolio | `portfolio.py:13-71` | matter-room / contract applicability distinctions |
| Solver autonomy | `brief.py:11-50` | complete assignment, not walkthrough |
| Trap policy by level | `agent_designer.py:140-199` | F3: corrections first, ≤3 authored per 7 trace-derived; F2/F1/F0: invent freely within the scenario |
| Hardening brief | `harden.py:329-491` | de-leak (remove analysis, never meaning, `:341-363`); premise traps (`:370-402`); route several checks (`:404-423`); deceptive evidence, published rules, **filters must be published in the instruction** (`:425-444`); genuine traps (`:446-457`); faithfulness budget (`:459-466`); do-nots (`:468-480`) |

### 2.4 Designer tools (`agent_designer._tools` `:840-943`, handlers `:1092-1467`)

`list_evidence`, `read_evidence`, `view_evidence_image` (`dump/evidence.py:445-460`); `plan_challenge`
(`challenge.py:112-123`); `plan_portfolio` (`portfolio.py:94-…`); `stage_evidence`; `list_fixture`;
`read_fixture`; `initialize_scenario`; `write_scenario`; `remove_scenario`; `list_corrections`;
`read_trace`; `read_signals`; `run_parser`; `evaluate`; `check_spec`; `stage_spec`; `read_draft`;
`check_draft` (= `check_spec` on the staged draft, **optional, no veto**); `submit_draft` (call alone;
validation is deferred to mandatory downstream validation); `reject_seed` (final); `design` (`SPEC_TOOL`,
`designer.py:40-…`). A designer that submits without `check_draft` spends a repair pass on the
draft-validation findings.

### 2.5 How instruction text is constrained

- **Production contract.** C1 + C2 are run in `check_spec` and again as the `quality.production` gate.
- **`rule_quote` / `rule_sources` / `rule_terms`.** H1 (`validate.py:1291-1391`). `rule_terms` maps a
  fixture token to the words used in the quote, and the words must be in the quote (`:1350-1356`).
  `rule_sources` entries are `{file, quote}` verbatim, available at that step (not withheld,
  `:1263, 1280-1281`).
- **Field definitions.** Backticked name plus meaning, or a schema description (H4).
- **WHAT vs HOW.** Prompt rules (`agent_designer.py:376-400, 742-759`) and the solver-autonomy review
  (`brief.py:52-108`) vs the H1/H2/H3 lexical requirements.
- **Published paths.** The build writes the contract section; checked at `quality.py:711-739`.
- **Instruction length.** The prompt says "Write the length of a real handover"
  (`agent_designer.py:396-400`), but T1 and H1 together push length up.

### 2.6 Lever catalogues

- **PLAYBOOK levers** (`rulesets/PLAYBOOK_GENERAL.md`): Join / Arbitration / Carry / Restraint /
  Sequence (`:36-79`); breadth superseded (`:80-141`); **the seventh lever, premise change**
  (`:142-210`: revision, governing conflict, residue; populations 9–130; rules published);
  instruction specificity (`:354-385`); `_hidden_rules` history (`:631-648`).
- **First-pass 16 families**: `agent_designer.py:578-617`.
- **Trap TAXONOMY**: 9 types with axis/lever (`author/traps.py:84-~200`). Family→type map at
  `agent_designer.py:627-633`.
- **Capability MECHANISMS** (5) and **SHORTCUTS** (10): `capability.py:9-20`.
- **Challenge mechanisms 1–6** (`challenge.py:28-105`); portfolio RECIPES (`portfolio.py:73-93`).
- **Hardening premise set**: `harden.py:378-394`.

---

## 3. How to run a build

### 3.1 Prerequisites

- `keys.env` exists (mode 600). `./arena keys --check` reports ANTHROPIC_AUTH_TOKEN or API key
  (required) and OPENAI_API_KEY (needed for the GPT reviewer and Astra calibration) (`cli.py:34-115`).
- `.venv` (pypdf, Pillow present). Harbor CLI for `tasks-check`/doctor (`benchmark/tasks_check.py:193-203`).
  `coder` CLI on PATH or `ARENA_CODER_BIN` for any screen or qualify (`benchmark/coder.py:154-158`).
- Do not edit `pipeline/` while a build runs (memory: lazy imports mix versions; any edit changes `policy_identity`).

### 3.2 Dump: setting it, and what the reader expects (1.8.0 compatibility)

```bash
cd /Users/pratyushmohanty/Downloads/arena-envs-non-coding-v2
./arena dump --set /abs/path/to/accepted_500_traces   # needs <dump>/sessions/ (cli.py:117-130)
./arena dump                                          # shows root, source (ARENA_DUMP or workspace.toml), session count
```

Resolution order is `ARENA_DUMP`, then `workspace.toml [workspace].dump`, then failure (`config.py:32-55`).
The v2 `workspace.toml` already points at `datasets/accepted_500_traces`.

**Reader expectations** (`dump/recover.py:117-207`, `dump/snapshots.py:42-177`, `dump/evidence.py:41-…`,
`dump/signals.py:84-142`, `dump/index.py:121-299`):

- `sessions/<sid>/data.json` with `traces[0]`:
  - `session_id`, `model_name`, `title`
  - `messages[].{role, content[], node_ids, manifest_node_id, workspace:"workspaces/<id>.json", undone, feedback}`
  - content types: `text`, `reasoning` (body excluded), `file` (`url: files/<hash>`), `tool-*` with
    `input`/`output`, `tool-ask_user`
  - `tasks[].{task_index, task_key, turn_ids, n_turns}`; `metadata.{categories, slice_categories, dropped_*}`; `pii_tags.redacted`
  - top-level `metadata.{files_index, pii_redaction.applied}`
- `sessions/<sid>/outcomes.json` `outcomes[].{signal_name, outcome, terminal_node_id, annotating_node_id}`.
  `tool_hallucination` is ignored (`config.py:81`). Corrections = steerability + praise_complaint +
  task_outcome_explicit failures (`signals.py:51-58`).
- `sessions/<sid>/workspaces/*.json` `files[].{path, hash (43-char base64url sha256), size, status ok|redacted, file:"files/<x>" | inlineText}`.
  Other statuses are omissions. A hash/size mismatch is tolerated only when upstream redaction is declared.
- Optional root files `inventory.json`, `cohort_manifest.json`, `dump_schema.py` are **hashed only** (`index.py:278-289`).

**Measured on the configured 1.8.0 dump (in memory, nothing written):**

| item | result |
|---|---|
| sessions read / seeds / index errors | 500 / 1260 / 0 (143 s, sequential) |
| `metadata.schema_version` | `1.8.0` on all 500. **No code reads it**: no version gate, no warning |
| snapshot statuses / hash format / pointer shape | all `ok` / all 43-char b64url / all `files/<hash>` (compatible) |
| content types seen | text, tool-bash, tool-edit_file, read_file, web_search, write_file, present_file, reasoning, fetch_page, generate_image, file, tool-ask_user, start/get/stop_process, image_search (handled generically) |
| roles | user, assistant, **compaction** (165; tolerated, treated as non-user) |
| `repo` / patchsets (1.7.0) | 0 sessions (ignored by the reader; fine for non-coding) |
| per-session `manifest.json` | present in all 500; **not read** by the pipeline |
| outcome labels | steerability failure **8** vs success 693; praise_complaint failure 240; task_outcome_explicit failure 83; tool_hallucination 44,625 (ignored); no `steering_burden` rows |
| corrections per seed | 0: 970, 1: 251, 2: 38, 3: 1 |
| kill filters | 961 / 1260 pass (K2 min-turns drops 299) |
| target levels (`categorise`) | **F3 5, F2 297, F1 167, F0 492** |
| existing `pipeline-artifacts/tiered.json` (built 2026-10-02 06:26 from this dump) | tiers {2: 1, 3: 38, 4: 922}, **no tier 1**; `classified.json` absent |
| missing bodies | omissions `missing_or_unsafe_snapshot_body` 134,103; `missing_or_unsafe_upload` 273; `truncated_body` 5 |
| local copy vs source zip | inventory lists 26,773 files; **11,052 absent on disk**. The zip `[Scaler]Updated_500_traces_9_29.zip` has 26,774 entries (12.1 GB uncompressed); the local copy is 3.5 GB. In the 282 `noncode_sids.txt` sessions, 13,014 present / 958 absent (all ≥2 MB: PNG, PDF, plus 72 JSON, 24 CSV, 242 HTML, 106 PPTX, 31 DOCX snapshot entries). The other sessions: 2,706 present / 10,094 absent |

**What would break or degrade:**

1. **Selective extraction (deliberate ≥2 MB cut).** Large PDFs, decks, data files and images are
   invisible to the classifier, the designer (`view_evidence_image` and `read_evidence` fail) and the
   ledger. Fixtures are thinner, `replay_readiness` is lower, and F3/F2 targets are fewer.
   Re-extract fully if those sessions matter. The coding sessions will be indexed and classified (at
   cost) even though their blobs are missing; nothing reads `noncode_sids.txt`.
2. **No schema-version check.** A future schema change fails silently, through `.get()` defaults.
3. **Correction signal collapse.** 1.8.0 ships only judged steerability outcomes (schema docstring),
   so `corrections`, `dispute`, tiers and target levels drop sharply. F3 is nearly unreachable (5 seeds).
4. **`steering_burden` rows** (documented in 1.8.0, absent here). If present, their `failure` rows would
   become `Moment`s, because `DEAD_SIGNALS` only drops `tool_hallucination` (`signals.py:104-134`). This
   inflates the "discovery signals" in the classifier and designer prompts; `corrections` is unaffected.
5. **`./arena build` fails** until `classified.json` exists. It is read at `orchestrate.py:841`, and an
   absent file gives a FileNotFoundError traceback. Run `./arena select` first (LLM classification, network).

### 3.3 Selection and classification into levels

```bash
./arena select --need 40 -j 8
#   == index ==      pipeline.dump.index            -> pipeline-artifacts/index.json      (index.py:302-318)
#   == score ==      pipeline.select.score --include-inspiration -> candidates.json     (score.py:205-238)
#   == priority ==   pipeline.select.priority       -> tiered.json (source tiers 1-4)   (priority.py:265-266)
#   == classify ==   pipeline.select.classify --need N -j W -> classified.json (LLM, cached in classify-cache/)  (classify.py:545-596)
#   == shortlist ==  pipeline.select.shortlist      (report only; the build does not read it)
./arena categories            # optional: F3/F2/F1/F0 counts from tiered.json -> categorised.json (view only)
```

`--need` defaults to **6** (`cli.py:555-556`). Classification walks tiers in order and stops once N
seeds survive (`classify.py:510-542`). Set `--need` ≥ the batch size you will build. Target levels are
assigned at build start (`orchestrate.py:851-859`, `select/categories.py:83-93`). Artifacts go to
`ARENA_PIPELINE_ARTIFACTS` (default `pipeline-artifacts/`, `config.py:70-72`).

### 3.4 Build (phases 1–4)

```bash
./arena build -n 20 -o envs-v2 \
  [--category F3,F2] [--ranks 1,2,5] [--max-tier 4] \
  [--task-workers 10] [--rollout-budget 20] [--screen-workers 10] \
  [--no-calibrate] [--continue-stalled] [--revalidate-blocked REASON]
```

(`cli.py:560-582`, `orchestrate.py:810-959`.) Seeds are `survives` rows with tier ≤ max-tier, sorted by
(tier, −dispute). `-n` takes the top N, or `--ranks` picks 1-based ranks. Then
`batch()` authors and grades concurrently, and `calibrate_batch()` screens every `validated` task (5×2)
and stops.

**Concurrency knobs:**

| setting | default | where |
|---|---|---|
| `--task-workers` | 10 (`MAX_TASK_WORKERS` = POOL_CAMPAIGNS//2) | `config.py:312-317` |
| `--rollout-budget` (batch semaphore for designer calls) | 20 | `config.py:319`; `orchestrate.py:699` |
| `--screen-workers` | 10 | `config.py:315` |
| `ARENA_PROVIDER_CONCURRENCY` / `ARENA_MAX_API_REQUESTS` | 20 / 20,000 | `provider.py:66-67` |
| `ARENA_REVIEW_CONCURRENCY` | 6 | `orchestrate.py:245-246`; `config.py:326` |
| `ARENA_GATE_REPAIRS` | 2 (0 = one-shot; capped at 2) | `orchestrate.py:175-177` |
| `ARENA_NATIVE_CONCURRENCY` | 16 (local backend only) | `benchmark/capacity.py:46` |
| `ARENA_LOCAL_WORKERS` / `ARENA_LOCAL_CONCURRENCY` | off / min(32, CPUs) | `local_work.py:15-18` |
| model overrides | `ARENA_DESIGNER_MODEL`, `ARENA_CLASSIFIER_MODEL`, `ARENA_REVIEW_MODEL` | `designer.py:38`; `classify.py:49`; `orchestrate.py:266` |
| `ARENA_FIXTURE_LED`, `ARENA_AUTHORED_FIXTURES` | on | `select/score.py:95-104` |
| timeouts | `ARENA_READ_TIMEOUT_S` (120), `ARENA_CALL_DEADLINE_S` | `designer.py:294-299` |

**Outputs:**

- Working tree `-o` (default `envs`): `target-F3-replay/ target-F2-scenario/ target-F1-pattern/
  target-F0-inspired/` (`policy.py:639-640`), each holding `a-NNN-<slug>/` with `task.toml`, `steps/`,
  `tests/`, `solution/`, `environment/files/`, `authoring/`, `provenance/ledger.json` and
  `verification/*.json`. The receipts include `state.json`, `spec-validation.json`, `probes.json`,
  `controls.json`, `semantic-review.json`, `repair-log.json`, `repair-disposition.json`, `screen.json`
  and `design-sessions/`.
- Batch report: `pipeline-artifacts/batch-build.json` (for `envs`) or `batch-build-<out>.json`, plus a
  uuid copy (`orchestrate.py:927-932`).
- Screen report: `pipeline-artifacts/screen-report-<out>.json` and `.md` (`orchestrate.py:945-951`).
- Native campaigns: `pipeline-artifacts/native/screen-<uuid>/` (`screen.py:205, 787`).
- Task names are rewritten to `arena/a_f<level>_<slug>` after the ledger (`orchestrate.py:557-558`, `naming.py:114-146`).

### 3.5 Screening on the Coder pool

The screen always uses Coder (`_default_backend` returns `coder` outside tests, `benchmark/coder.py:691-699`).
`workspace.toml [coder]` (`Settings`, `coder.py:90-131`; unknown keys raise, `:134-148`):

| key | meaning | v2 value |
|---|---|---|
| `url` | deployment for `coder login` | `<your Coder deployment URL>` |
| `template` | workspace template (required) | `<template>` |
| `copy_parameters_from` (or a `[coder.parameters]` table) | spec source | `<a workspace built at max specs>` |
| `tasks_per_instance` | concurrent campaign slots on the one workspace (default 20) | 20 |
| `trials_per_task` | Harbor trials per campaign (≤ tasks_per_instance) | 10 |
| `stop_after` | workspace autostop | `12h` |
| `name` | the pool's own workspace (created on first use, paused when idle) | `arena-calib-3` |
| `workspace` | an existing shared workspace (never created or stopped); must differ from `name` | unset |
| `min_cpus` / `min_memory_gib` / `min_disk_gib` | refuse a smaller workspace | 32 / 120 / 190 |
| `idle_stop_after` | seconds idle before pausing (0 = never) | 1800 |

Capacity math: each screen campaign asks for `workers = episodes = 5` (`screen.py:162`). The slots are
`min(5, trials_per_task, tasks_per_instance)` = 5 (`coder.py:659-672`). With 2 models per task that is
10 slots, so **two tasks screen at once on a 20-slot workspace**; others queue (`coder.py:541-575`).

```bash
./arena coder login|status|stop|delete     # cli.py:743-745
./arena benchmark --doctor                 # Harbor/Docker check (local)
./arena screen envs-v2                     # gate chain must be green; --include-unvalidated overrides
./arena screen envs-v2 --report-only       # reprint from receipts
./arena screen --relaunch-incomplete <bundle>   # operator override when the void top-up budget is spent
```

Memory cautions: the Coder 12h autostop can wipe the runtime (re-bootstrap before a 10×2). Two
checkouts sharing a pool name refuse each other. Run calibrations from one process.

### 3.6 After the screen (manual)

```bash
./arena harden <bundle> --apply     # ≤3 attempts per lineage; each valid revision gets a 5×2 screen
./arena tasks-check <tree>          # harbor check (LLM trial, about 2.5 min per task); writes the receipt release needs
./arena qualify <bundle>            # 10×2; requires a shippable screen of this exact version
./arena release <bundle>            # the acceptance decision
./arena deliver <tree> -o <out> [--accepted-only]     # F-level folders, a_f<n>_ names
./arena deliverable <out> --sessions all-sessions.json [--excluded auto]
```

### 3.7 Pre-build checklist for the 1.8.0 dump

1. Decide whether the ≥2 MB blobs matter. If yes, re-extract the zip completely (11,052 files missing).
2. `./arena select --need <≥ batch size>`. Expect few F3 (about 5) and many F0/F1 targets.
3. Expect `trace-underused` mostly not to apply (most seeds have 0 usable corrections, so it is a WARN).
   But the 5-trap floor still cascades to `unverified` (B1).
4. Run `./arena tasks-check` yourself before `release`.
5. Expect heavy draft-validation findings from H1/C1/C2. The repair budget is 2 passes in total.

---

## 4. Test suite

- `pytest` is not installed in `.venv` (`No module named pytest`).
- `python -m unittest discover -s pipeline/tests -t . -f -q`: **Ran 1893 tests in 389.502s, OK (skipped=1).**
  The output includes expected noise from tests that exercise CLI refusals (e.g. `invalid choice: 'presolve'`).
