# Production qualification

> **Thresholds in this file are historical.** The authoritative acceptance
> policy is [POLICY.md](POLICY.md), and every threshold is a named constant in
> [`policy.py`](policy.py). Where this document and POLICY.md disagree, POLICY.md
> is right. In particular the blind-solve solvability gate and the band-composition
> release gate described below were **removed on 2026-09-23**; see POLICY.md.

`build` produces a **validated draft**. Only `release.evaluate` can mark an exact
task version **accepted**. A passing reference solution, a green structural gate,
or a successful model call is insufficient. Old `envs-cat` bundles are not
grandfathered into acceptance.

The default path is source inspection → complete environment → automated checks
and independent semantic review → five-run native development screen.
There is one initial design attempt. The preliminary plan-review gate is removed;
authors build the complete fixture, instructions and grader before semantic review.
Up to two bounded validity-only repairs may follow actionable semantic findings;
they cannot consume difficulty feedback. Difficulty hardening is manual and
lineage-bounded. A clean eligible screen permits separate ten-run/model native
qualification and release evaluation; a screen alone never qualifies a task.
Release requires native reference/empty controls and the current acceptance
policy, not the removed blind-solve gate. Existing successful semantic/native evidence is
reused only when its artifact, harness and relevant review inputs still match.

Each environment uses `verification/checkpoint.json` for author progress and
remaining gate/qualification repair allowances. Normal restarts resume saved
conversations or submitted designs through the build controller. A response with
several tool calls consumes one response turn. An unfinished local mutation or
changed source fails recovery rather than granting a new attempt. Qualification
repairs are charged before authoring and resume within their retained allowance
only when explicitly requested; an automatic restart cannot trigger a revision.
Successful draft validation is retained across restarts only for the same draft,
source/provenance, trace and pipeline policy; changed receipts are revalidated.

Authors may add traps that did not occur as observed corrections in the trace.
Mark them `authored`, ground them in the trace's professional scenario and cite
the supporting fixture. Public evidence and rules must let a careful solver
resolve them. A stale revision, plausible competing record or inapplicable
exception can qualify when the scenario supports it; hidden rules, arbitrary
ambiguity and unrelated distractions cannot. Demonstrate a substantive wrong
answer and a valid solution. Authored additions remain disclosed, receive no
recovered-source credit and stay within the category's fidelity allowance.

## Run

Python 3.11+ runs the stdlib pipeline. The native worker uses Python 3.13,
Harbor 0.22.0 and LiteLLM 1.99.0, installed from the hash-locked dependency set:

```sh
python3.13 -m venv .venv-harbor
.venv-harbor/bin/pip install --require-hashes -r requirements-native.lock
./arena dump --set /path/to/kaizen_dump
./arena keys
./arena benchmark --doctor
python3 -m unittest discover -s pipeline/tests -v
.venv-harbor/bin/python -m pipeline.tests.native_smoke --out /absolute/fresh/smoke
```

Docker must be running. Image construction downloads packages from a dated Debian
snapshot; task execution has no network. Agent and verifier images use a pinned
multi-platform Python image digest. Update dependencies and image pins through
review, then repeat native verification; do not silently float versions.

```sh
# Author and grade a batch, then screen every validated task (5 episodes on each
# calibration model) and stop with the pass@1 / pass@4 / mean-reward table.
./arena build -n 1 -o envs-production

# Harden by hand; every round ends in another 5 x 2 screen of the revision.
./arena harden envs-production/strong/a-001-example --apply

# The 10 x 2 calibration of record -- needs a clean screen of this version
# (valid episodes, attributable failures, no unresolved reward hacking).
# pass@1 < 0.5 is the strict target and never blocks it.
./arena qualify envs-production/strong/a-001-example \
  --models claude-fable-5-1 gpt-6-astra --rollouts 10 --workers 2

# Revalidate retained evidence without making model calls.
./arena release envs-production/strong/a-001-example
```

`qualify` requires configured credentials and incurs model charges. It refuses
to start a new ten-episode campaign unless the task's current screen is
clean (`screen.shippable_problems`; pass@1 is never a reason), and stops at a
failed validity stage.
`build` never qualifies: the automatic pipeline stops after the screen.
Standalone qualification changes task content only with `--repair-attempts 1..3`.
Each revised version repeats qualification; exhausted budgets, provider faults
and missing evidence cannot turn a rejection into acceptance. Repairs receive
critic findings and aggregate criterion counts, never individual solver answers.
The author's default model is Claude; the semantic reviewer must
use a different named model. Models and effort are recorded, not inferred from
filenames. `arena calibrate` runs a **diagnostic file-workspace protocol**;
production difficulty is measured through native Harbor terminal episodes.
The two native models are measured concurrently after validity checks and the
blind solve. `ARENA_NATIVE_CONCURRENCY` bounds the combined native trial slots
across every task and model; `--workers` is the per-model requested share.
The native output root must be outside the source bundle.

For a multistep task, `env.step_isolation` checks matching `ARENA_STEP` markers,
unique output ownership for every step, and reproduction by the current exporter.
A checked-in handoff note is not evidence that submissions are immutable. The
file-workspace runner commits completed-step outputs, and native Harbor retains
controller-owned prior-step artifacts for the separate verifier. Release checks
must still verify the actual execution/history receipts; the static gate does
not establish that a task has run successfully.

## Acceptance requirements

| Requirement | Enforcement |
| --- | --- |
| Non-coding professional scope, source fidelity, explicit traps and public criteria | Selection and existing gate chain; source ledger recomputed from the configured dump |
| Every revision is a real step | Shared compiler assigns outputs and criteria to named manifest steps; native step history preserves original earlier submissions |
| Complete deliverables | Published strict JSON schemas and file inventory; missing, malformed, incomplete or undeclared outputs earn zero; declared files from other steps may coexist |
| Substantive grading | At least 70% objective weight covers semantic core/stretch decisions; semantic floor checks can cover required fields but cannot supply this weight threshold or a core decision; weak presence, inclusion and literal-answer checks do not qualify; required fields need coverage or an explicit presentation-only rationale |
| Real reasoning | Source-derived targets, keyed whole-row comparisons, temporal precedence, arithmetic and explicit uncertainty; independent semantic critic reviews each check |
| Counterexamples | At least two plausible wrong cases; executed failures cover semantic checks and non-integrity guardrails; independently phrased correct alternative must pass |
| Record integrity | Controller-generated deletion, duplication and cell-exchange probes run through the exported grader; allowed whole-row reordering must retain full credit |
| Source dependence | Every semantic check has a source counterfactual with an independently calculated corrected answer; the old answer must fail the changed decision and the corrected answer must pass. Controller newline invariance must preserve full credit |
| Independent decisions | `quality.decisions` groups semantic checks by professional decision, load-bearing sources and tempting shortcut; at least four distinct core decisions across the whole task. Every claimed source needs a cited, executed counterfactual |
| Solvability | Complete reference passes each step; retained independent blind episode earns full credit on all steps |
| Native controls | Oracle scores 1 and no-op scores 0 on every step; actual Docker isolation receipts, artifacts, grades and transcripts retained |
| Hardness | At least 10 complete native episodes on each of two named models; the whole task has 4–6 core checks at 30–70%, at most two floor checks at >=90%, and 1–2 stretch checks below 30%. Each scored step must retain a measured core or stretch objective; a focused follow-up does not need four new decisions |
| Fair dependencies | Only measured core objectives may gate other checks; `gated_out` is excluded from pass-rate denominators |
| No false green | Missing, error, skipped, stalled, capped and incomplete evidence blocks acceptance; voids never count as model failures |
| Version identity | Full hashes cover instructions, fixtures, schemas, graders, reference artifacts and provenance; harness and policy versions are recorded separately |
| Novelty | Critic sees related/similar current corpus tasks; local release catalog refuses source-family duplicates |
| Privacy | Credential/email, explicit SSH access and exam-attempt screening before author/review requests; supported source-bound minimization runs before authoring; critic assesses contextual privacy |

Difficulty bands use observed rates, not statistically precise estimates. Ten
episodes is a qualification minimum. Increase repeated measurements for important
releases, especially checks with few reachable attempts. Low reward alone does
not demonstrate high quality, and a model critic is not a domain expert.
The rubric budget applies once per task, as specified in the playbook. Each
objective is counted once using its owning step's reachable observations, and
each model must qualify separately. Every scored step must still put at least
70% of its objective weight on declared semantic core/stretch work; splitting
one arithmetic chain across steps cannot manufacture independent decisions.

Decimal rounding must match the published convention. The `round` expression
supports explicit `mode: "half_up"` and `mode: "half_even"` for both scalar and
row targets. Omitting the mode retains legacy Python rounding for replay.
Explicit modes evaluate nested basic arithmetic and sums exactly over decimal
operand values before rounding. Already-derived fields retain their numeric
values; the rest of the evaluator is unchanged. Eligibility comparisons
must use unrounded amounts unless the public rule explicitly says otherwise.
For a policy shared by many records, `bind_rows` evaluates named scalar source
expressions once and attaches their values to each row before `derive_rows`.
This permits a deposit threshold to come from the governing document while
order amounts come from the order book. It preserves order and duplicates,
rejects field collisions, and keeps reads within the expression's existing
source or submission role. Binding a policy does not demonstrate difficulty;
source counterfactuals must still exercise the resulting decisions.
Reports also retain the transition band (>70%, <90%). These checks are allowed
and do not reject an otherwise qualifying task. They are neither core nor
stretch and do not replace the required measured core/stretch checks.
Guardrails never contribute to capability-band totals. Diagnostic
inventories include Wilson 95% intervals, reachable sample sizes and boundary
uncertainty, separately for each model. These estimates do not establish that
a check discriminates ability. The build runs no difficulty pilot (removed
2026-09-25); the five-episode screen reports bands per model for the whole
batch, and never feeds them back into a design. It does not qualify the task
for release. Release still requires fresh frozen-version native qualification with
ten episodes per model and the complete validity and measured-band checks. Stretch-only candidates
remain valid reserve tasks and do not qualify as informative core tasks.

The designer must specify professional decisions before serialization fields.
The rubric has at least eight objectives (`policy.MIN_OBJECTIVES`), each failed
by at least one executed counterexample. There is no total-check minimum or
guardrail ratio: each guard must enforce a genuine negative obligation or
protected state. Copying registers and repeating correct answers cannot become
guards. The independent-decision and measured-band requirements still apply. Cosmetic
probes reorder keys and change whitespace within the declared output contract;
an extra artifact in a restricted deliverable folder is a contract violation.

Whole-object equality checks can declare `unordered_paths` for nested arrays
whose row order the public assignment makes immaterial. Complete records and
their multiplicity remain graded; controller probes exercise row deletion,
duplication, cell exchange and permitted reordering. Other arrays retain their
declared order semantics. The generic `svg_elements` parser exposes source
attributes and ancestors, including duplicate elements, without rendering,
applying transforms/CSS, or inferring defaults. It rejects unsupported or
malformed XML instead of silently producing an incomplete inventory.

If the evidence cannot support those decisions, `reject_seed` ends authoring
with exact source citations and a hashed fixture inventory. The orchestrator
records a reserve/source-rejected outcome and does not retry that source or run
calibration. This is an author assessment of source capacity, not empirical
difficulty evidence or a release. A different source must be selected explicitly.
`quality.source_cases` contains `{id, reason, changes, source_patches, patches}`:
`changes` names affected semantic check IDs; each source patch is
`{file, before, after}` replacing exactly one unique existing span; output
`patches` use the same `{file, path, value}` replacement format as counterexamples.
An entire corrected `submission` can replace output patches. All variants run
in private scratch, with the exported grader rebuilt to bind the changed source
hashes. Contract failures, integrity violations and gated-out checks do not
demonstrate changed reasoning. These synthetic controls do not alter the
published fixtures, their provenance, or the reference task's identity.

`quality.source_invariants` contains `{id, reason, source_patches}` for changes
that must preserve the complete answer, such as adding an unrelated table.
These cases cannot supply corrected outputs or causal coverage. Their unchanged
reference must still score 1 after the scratch fixture is rebound. They
complement, and never replace, answer-changing source counterfactuals.

Authoring projections live under `authoring/draft-derived`, separate from the
last exported grader. Draft reference validation binds the current fixture
inventory in memory; it does not overwrite a prior version's integrity
manifest. A privacy repair can therefore be validated as a new draft while the
old exported grader continues to reject changes to its frozen inputs.

Semantic review precedes model calibration. Missing empirical difficulty data
is an untested surface at that stage; it does not create a circular rejection
that prevents calibration. Concrete semantic defects and superficial decisions
still block the pilot, and final release still requires the native measurements.
The batch builder applies this order to automatic difficulty pilots too. An
intact semantic rejection is retained until the candidate changes and consumes
the bounded design-repair budget; unavailable or invalid review evidence stops
as unverified without rewriting the task or launching solver attempts. Reviews
share the batch's model-call budget and use a model different from the author.

## Ruleset applicability

The authority is `CLAUDE.md`, `rulesets/PLAYBOOK_GENERAL.md`,
`rulesets/ANTI_REWARD_HACKING.md`, and the task specification/feedback under
`ref_files/`. The quality policy adds executable obligations; it does not replace
the source rules. Mechanical checks cannot prove all semantic requirements.

Browser/CUA-specific requirements in historical AutomationBench material apply
to browser tasks. They do not require coordinates or browser evidence for this
file-workspace protocol. Local deliverable filenames are part of the public
professional assignment. Network isolation, no answer leakage, deterministic
grading, evidence integrity and justified uncertainty apply to both protocols.

Later trace revisions may supply scenario augmentation, but a later revision is
not proof of correctness or user acceptance. Recovery omits explicitly failed
or truncated tool bodies. The ledger records omissions, full UTF-8 byte hashes,
source trace identity, and whole-session augmentation policy. Derived similarity
is an ordered-text estimate, not a semantic fidelity proof.
Trace-derived traps must quote an actual user correction. Kaizen feedback can
anchor the assistant turn immediately before that correction; the validator
resolves the next user turn and rejects multiple anchors that inflate the count
of distinct corrections.

## Verified privacy transformations

Ledger schema 3 distinguishes `lifted`, `anonymized`, `derived` and `authored`.
Source-fidelity credit is respectively 1, 1, 0.5 and 0 per published file byte.
The existing category/tier floors are unchanged. `exact_copy_by_bytes` and
`exact_copy_by_file` count only whole files copied exactly (`lifted`); they are
not estimates of the fraction of unchanged characters inside edited files.
Schema 2 remains readable for tasks without privacy transformation claims.

`provenance/privacy-redaction.json` uses policy `arena-pipeline/privacy-redaction/1`.
Each file supplies `path`, recovered `citation`, `source_sha256`, `public_sha256`
and `kinds`. Authors cannot supply replacement text or offsets. The controller
computes every edit from the recovered source and verifies the complete public
bytes. Supported kinds are explicit SSH IPv4 access commands (replaced with a
documentation endpoint) and recognized exam-attempt metadata (personal header,
question performance and student responses). Exam questions, options and
published correct answers remain intact; any explicit header paper total is
preserved separately. Unrecognized forms require review, not arbitrary deletion.
The build runs these policies before authoring and stops on unsupported private
data. Reviewers receive a source-bound audit with the removed values omitted.
This proves transformation lineage; the independent review must still assess
whether the resulting task is meaningful, fair and sufficiently minimized.
Overlapping calendar/redaction transformations require an explicit composition
policy and cannot silently acquire fidelity credit.

The exam parser exposes printed facts and lexical `visual_cues`, not a private
answerability classification. Existing graders using the retired
`figure_dependent` or `verifiable` fields must be redesigned and requalified.
`transcript_answers` includes every plain, bold and headed block, retaining
duplicate IDs; a coverage decision must compute an explicit distinct union.

The private `provenance/calendar-anonymization.json` must use policy
`arena-pipeline/calendar-anonymization/1`, kind `fixed-day-shift`, a nonzero integer
`days` (at most 36,600 in magnitude), a two-date ISO `source_window` shorter than
one year, and a nonempty `files` list. Each file identifies its canonical fixture
`path`, exact recovered `citation`, `source_sha256`, `public_sha256`, and `edits`.
Each edit contains `start`/`end` character offsets into the original Unicode text,
an absolute ISO `date`, and a supported `format`: `iso-date`, `slash-date`,
`dot-date`, `iso-month`, `zh-month`, or `en-month`. Slash/dot dates use unpadded
month/day. Month edits use the first day and must preserve the entire month's
interval under the same day shift. The window disambiguates yearless tokens.
Unsupported formats require a reviewed policy extension, never arbitrary
replacement strings or executable transformation code.

The validator recovers the cited original from the configured trace dump,
checks its hash, computes every replacement, and requires the entire result to
equal the published file bytes and hash. All other content, ordering and spacing
must remain unchanged. Missing sources, malformed manifests, overlapping spans,
unrelated edits and unverified claims block qualification. The standalone ledger
gate and release evaluator both recompute the proof. Manifest identity is frozen
with the task and bound into the ledger; changing it invalidates task evidence.

This proves source lineage and calendar-day intervals, not contextual privacy or
business-calendar equivalence. Before release, the independent critic receives
private `calendar-audit.json` evidence reconstructed from the trusted source.
It must return a cited `calendar_assessment`, checking that tokens are dates,
amounts and durations are unchanged, related dates remain consistent, and the
shift preserves answer logic and difficulty. Weekdays, holidays, workday
arithmetic, seasonality and remaining privacy exposure require explicit review.
A mathematical proof alone cannot approve the task. Originals and the reversible
mapping stay outside the solver's Docker context. Native controls, blind solving
and difficulty calibration must still qualify the new artifact normally.

## Operations and recovery

One local worker process owns a bundle through an OS lock shared by building and
qualification. Atomic receipts survive interrupted writes. Each design attempt
and calibration campaign receives a fresh directory; reusing a rollout ID cannot
overwrite earlier evidence. Qualification resumes only after validating retained
files, task identity, budgets and protocol. Failed or stale campaigns run again
in fresh directories. The original failed attempts remain available for audit.
Native snapshots and their byte/permission checks cover the published task
surfaces. Mutable review and verification evidence stays outside those snapshots,
so writing a review during a native run cannot invalidate an unchanged task.
Task files, permissions, symlinks and task-supplied Compose overrides still receive
the same validation. A remote reviewer must have the same comparison corpus as
the releasing workspace; an empty worker corpus cannot substitute for local peers.
A current, intact semantic rejection is retained when qualification restarts.
Repair the task before requesting a new verdict; stale or invalid review evidence
can be rerun, but an unchanged task cannot clear a finding by retrying the critic.
Rebuilding a revised specification removes obsolete generated dimension
descriptions from `tests/`, so renamed grading dimensions match a fresh export.
Unrecognised files are retained and still block reproducibility checks; review
them before moving them into the verification archive.
Use `multiset_equals` for unordered output rows whose occurrence counts matter.
It compares complete normalized rows and preserves duplicates; `set_equals`
intentionally ignores duplicates. Publish whether row order and repetition matter.
Production comparisons over record arrays cannot use `set_equals` or independently
projected columns. Keep evidence rows separate from derived conclusions when a
preservation guardrail needs to protect different fields from an objective.
The controller generates record probes independently of the author's examples.
Their receipt distinguishes schema rejection from a demonstrated grader failure;
it also states the sampled coverage rather than claiming exhaustive validation.
The agent author stages large specifications in small sections, with an atomic
`draft.json` checkpoint in its design-session directory. Checking or submitting
a staged draft runs the same full validators as a single-call specification.
Token-truncated tool calls cannot commit a design. A retained draft can seed a
fresh authoring attempt through `agent_designer.design(initial_spec=...)`.

`verification/state.json` records build state. `qualification.json` records the
current release stage or interruption. `release.json` records the decision and
specific blockers. `arena status` labels legacy and stale evidence explicitly.
Re-run `arena release` for a fresh decision; a cached receipt is not a live check
of Docker, external evidence storage or source-dump availability.

Useful limits:

| Setting | Default / scope |
| --- | --- |
| `ARENA_PROVIDER_CONCURRENCY` | 8 simultaneous HTTP requests within a process |
| `ARENA_MAX_API_REQUESTS` | 2,500 attempts, including retries, within a process |
| Native agent budget | No artificial turn or time cap; capped diagnostics cannot certify release |
| Native resource ceilings | `ARENA_HARBOR_MEM=2g`, `ARENA_HARBOR_CPUS=4` |
| `ARENA_RELEASE_REGISTRY` | Defaults to `pipeline-artifacts/releases` |

These are local worker limits, not a fleet-wide rate limiter or dollar cap. Use
provider spending controls for monetary limits. Native Harbor jobs are separate
processes governed by their episode, turn, timeout and worker limits; the local
HTTP request counter does not meter LiteLLM inside those jobs.

For explicitly requested uncapped diagnostic runs, `arena benchmark --no-limits`
uses an unbounded Terminus-2 turn iterator and removes campaign, agent, step,
setup, image-build and verifier phase deadlines. Transport and health-check
fault detection remain separate. `--max-output-tokens` sets the actual provider
request allowance; `--context-limit` sets the agent's context accounting. Model
APIs still determine what they accept. These overrides and adapter hashes are
recorded with each campaign. Use the same settings for both sides of a comparison.
Legacy bundles are diagnostics only; launching one requires the explicit `--legacy-diagnostic` flag (or
`legacy_diagnostic=True` in the Python API). Every ordinary native launch checks
that its schemas, instructions, reference, grader and container export reproduce
under the current generator before creating a run or contacting a model.
Reports label this `current-draft`, which is not a production acceptance claim.
Legacy diagnostics are explicitly rejected as release evidence. A stop request
received before launch returns immediately without package inspection or staging.
Evidence validation honors recorded uncapped execution and token/context settings;
it does not silently reinstate the default 40-turn criterion. Model comparisons
must use the same turn, time, context and reasoning settings; output allowances
may differ between providers.

An existing task must be re-authored when it lacks public schemas or has semantic
defects. Adding Docker files or copying a newer runtime does not perform that
migration. Preserve the original and its scores, write a new revision, and repeat
all qualification stages for the new artifact hash. A mechanical build or current
generator check cannot transfer acceptance from an earlier version.

Restrict this worker to trusted
operators and one protected artifact store; the catalog and receipts are not
cryptographically signed attestations against a malicious host administrator.
Separate agent/verifier contexts and a non-root offline agent protect grading
from task submissions. The controller, model providers and Docker host remain
trusted components.

Back up the entire qualification output, including native campaigns stored
outside the bundle, the source dump, lockfile and release catalog. Losing any
required evidence blocks revalidation. Do not prune active run directories.
Cleanup targets owned Docker projects only; no global Docker prune runs.
Replacing a released source family requires an explicit catalog retirement or
supersession process; changing a slug does not create a new task family.

For a rebuild, retain its exact baseline in the review corpus and write
`provenance/replacement.json` with schema `arena-pipeline/replacement/1`, a
nonempty `reason`, and `predecessors` containing the baseline artifact hashes.
The reviewer distinguishes those verified source-related predecessors from
competing peers: preserving sound requirements is legitimate repair, while
routine work still fails quality or empirical selection. Unknown, changed or
unrelated predecessors are rejected. This declaration does not retire a release
or bypass duplicate detection. Identical staged copies are not competing tasks.

Authored scenario supplements are supported through `write_scenario`. Recovered
documents remain immutable; additions are public hypothetical case facts, never
recovered history. The private receipt binds their bytes and exact source
grounding, while the public README discloses their status. The ledger always
charges them as authored material with zero source and exact-copy reuse credit;
copying source text into a supplement cannot inflate fidelity. Both the ledger
gate and release verification independently check this receipt. The writer's
category allowance is an upper bound; final measured fidelity and all quality
requirements still apply. Tool size limits do not establish task difficulty.

## Verification scope

The CI workflow runs the stdlib suite on Python 3.11–3.13 and offline two-step
native controls on Python 3.13. Live provider smoke tests are opt-in and use only
synthetic public data:

```sh
python3 -m pipeline.tests.live_smoke --out /absolute/fresh/live
python3 -m pipeline.tests.review_smoke --out /absolute/fresh/critic
.venv-harbor/bin/python -m pipeline.tests.native_smoke \
  --out /absolute/fresh/native-live --models claude-fable-5-1 gpt-6-astra
```

Transport smoke tests are deliberately easy. Passing them verifies execution
and evidence handling, not professional task quality or hardness. A newly
generated real task must independently satisfy every acceptance requirement.
No production acceptance is claimed merely because unit tests pass.
