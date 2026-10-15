# Arena environment pipeline

The September 28, 2026 specification is mapped requirement-by-requirement in
[`SPECIFICATION.md`](SPECIFICATION.md); executable thresholds live in `policy.py`.
New authoring drafts require evidence-linked `quality.capability_plan` and exact
`quality.trace_alignment` witnesses. Rules may be cited from step-available
fixture documents via `rule_sources`. Inspired/F0 is allowed; Unrelated/F-1 is not.
These construction controls establish validity, not guaranteed model difficulty.

Authoring uses the supported 128,000-token output allowance. Truncated responses
never authorize tools, but their completed signed thinking/text blocks remain in
the continuation so expensive planning is not silently restarted. A resumed
legacy session may increase its output allowance without resetting its retained
conversation or remaining response/repair budgets; changed instructions, tools,
models, or a decreased allowance still invalidate conversation reuse.

### Credentials and throttling

`keys.env` accepts `OPENAI_API_KEY` or numbered aliases such as
`OPEN_AI_API_KEY1`, `OPEN_AI_API_KEY2` and `OPEN_AI_API_KEY3`. The CLI normalizes
aliases in memory without rewriting or printing secrets. Direct Responses API
calls reload configured credentials and rotate after temporary HTTP or streamed
rate-limit errors, preserving the request body, model and retry budget. Server
retry delays still apply; authentication, billing and exhausted-quota errors do
not authorize retries. Keys sharing a project or organization can share limits.

This does not hot-swap credentials in already running native solver episodes or
retrofit frozen campaign code. Those runs retain their original evidence; new
cold runs must load the updated credentials. Infrastructure loss never counts
as a task failure or permits replaying a scored episode.

> **Thresholds in this file are historical.** The authoritative acceptance
> policy is [POLICY.md](POLICY.md), and every threshold is a named constant in
> [`policy.py`](policy.py). Where this document and POLICY.md disagree, POLICY.md
> is right. In particular the blind-solve solvability gate and the band-composition
> release gate described below were **removed on 2026-09-23**; see POLICY.md.

### First-draft adversarial construction

New designs and manual hardness redesigns use capability-plan **version 2**. The controller records the minimum
version before authoring; stalled continuations and repairs cannot downgrade it.
Existing version-1 drafts can receive validity repairs without being relabelled
as new first-draft successes or being forced into a new construction protocol.
Manual redesign upgrades only its working copy; the measured baseline remains
unchanged. Its later validity repairs retain the upgraded construction version.

- **Independent judgments:** a causal decision DAG and at least four distinct
  core bottlenecks, each with its own source intervention. Changes may propagate
  to real descendants, not unrelated judgments. Dependent fields are not breadth.
- **Confusing but resolvable evidence:** a private criterion/candidate matrix
  binds near-misses to exact, step-available public evidence. At least one full
  match and two partial matches failing different criteria must coexist; all
  legitimate matches remain valid. No winner labels or error maps enter the fixture.
- **Active controls:** a coherent applicability-changing case must change the
  answer; strengthening an inapplicable decoy must preserve the entire answer.
  Version-2 interventions execute every semantic check and verify the exact
  change set, so an unreported downstream failure cannot fake independence.
- **Cross-decision coupling:** one coherent intervention and one sustained wrong
  reading must affect multiple professional decisions under a quoted public rule.
- **Honest tool baselines:** retrieval/computation procedures may supply complete
  `submission` outputs and a `fails` list, including `[]`. All steps execute against
  the exported grader and observed failures must match exactly. A competent baseline
  may solve the task; that is difficulty feedback, not invalidity. Independent
  review still audits whether the output actually follows the stated procedure.
  Legacy linked wrong-answer baselines remain supported but cannot manufacture
  failure by omitting public rules, evidence, exceptions or correct arithmetic.
- **Early novelty:** same-session professional questions are supplied before
  scenario construction, without sibling gold, target expressions or trajectories.

`optimal_subset` adds a reviewed finite allocation grader: eligibility, companion
requirements, mutual exclusions, signed metric bounds and ordered lexicographic
objectives. It accepts every globally optimal selection and tie, not a private
fixed answer. It uses exact arithmetic and at most 18 binary items without an
external solver. See `author/quality.py` for the public contract and bounds.
An allocation remains one planning decision; enumeration size is not difficulty.
The shipped reference script solves path/selection problems from source instead
of copying the unsolved problem into the answer. Changed source evidence produces
a newly derived optimum; exact decimal-string schemas remain supported.

These are executable **construction/validity controls**, not evidence that a
model is incapable. Five-run/model screens and separate ten-run/model native
qualification still establish observed difficulty on the two exact high-effort
targets. Preserve every first version, rejection and easy result; selected
survivors do not measure unconditional first-draft yield.
Research motivation: [structured distractors and constraint dependencies](https://arxiv.org/abs/2606.01815),
[fixed-corpus hard negatives and retrieval sensitivity](https://arxiv.org/abs/2508.06600).
Transfer to Fable 5.1/GPT-6 Astra is a hypothesis requiring native measurement.

See [PRODUCTION.md](PRODUCTION.md) for the current acceptance policy, supported
runtime, recovery procedure and verification limits. Historical gate/calibration
results below describe development drafts; they are not release certificates.

The default production path is **inspect source → build the complete environment
→ automated checks and independent semantic review → five-episode native
screens on both models**. `build` stops after the screen; the ten-episode
calibration of record (`qualify`) and publication are separate commands.
Authors do not wait for preliminary plan approval. Validity findings may receive
up to `policy.MAX_REPAIR_PASSES` bounded automatic repairs (currently two);
`ARENA_GATE_REPAIRS=0` disables them. Repairs retain their consumed allowances
and require shrinking, nonrepeated findings. A rejected review's substantive
summary rows are rejection findings, not a transport failure or permission to
reroll the reviewer. Hardness feedback never triggers automatic validity repair;
post-screen hardening requires an explicit manual trigger. Failed
drafts retain their findings while the category batch advances other sources.
For an extreme collection, `arena harden <bundle> --apply --max-pass-at-1 0.2`
binds a stricter inclusive maximum for both official and conservative
capability-adjusted rates on both exact high-effort models. The goal survives
resumes; meeting the general `<0.5` goal does not stop this lineage early. The
three-attempt budget is unchanged. A spent/terminal lineage cannot be reopened
or retrospectively retargeted, and an unreadable ledger never refunds attempts.
`submit_draft` durably retains the candidate without a local quality veto.
Mandatory post-submission validation derives and verifies the reference before
export; controls, independent semantic review and native qualification are still
required. Optional `check_draft` results are explicitly local and never release
certificates. Direct build, repair and hardening callers cannot bypass validation.
Within one build or qualification preflight, the just-executed control gate's
successful proof may replace a duplicate control-suite execution only when both
the complete artifact and implementation hashes still match. Stored receipts,
missing evidence, skipped or failed gates and changed artifacts never bypass a
fresh control run. Export reproduction and independent review remain mandatory.
Batch reporting separates one-design-attempt counts from first-pass validation;
validity repairs and fresh allowances for stalled authors are not first-pass
successes. Neither count certifies model difficulty.
`verification/checkpoint.json` retains progress and consumed repair allowances;
normal restarts reuse the verified boundary. Authored traps are allowed when
legitimate, grounded in the trace scenario and resolvable from public evidence.
The detailed stage descriptions below include optional diagnostic tools; pilots
are disabled by default and never substitute for production qualification.

Category batches execute CPU-heavy draft and qualification checks in separate
Python processes (`--local-workers`), keeping model requests responsive while
using multiple cores. `--eager-selected --selected-only` starts remaining selected
initial drafts while other candidates qualify; publication still enforces each
category's quota. Native campaigns share their own bounded episode pool.

Turns a dump of real agent sessions into replay-ready, machine-graded RL
environments, in small batches, with a gate chain that runs before any rollout
budget is spent.

**Scope: non-coding professional knowledge work** — finance, business,
consulting, publishing, editorial, legal, medical, research. The deliverable is
a document, register, schedule, plan or analysis that a careful reader with the
same sources can check *without executing anything*. A seed whose correctness can
only be judged by running it is rejected as `requires_execution`, however
interesting its failure. Writing a document *about* code — a review, an audit, a
specification, a migration plan — is in scope.

Use `uv sync` to install the pinned reader dependency, then `./arena`; the entry
point uses the project environment when present. Coder installs the identical
hash-pinned `requirements-evidence.lock` beside its native harness dependencies.

Native trial concurrency is bounded by both the per-campaign setting and the
workspace's assigned lane. Reducing a lane never reduces the requested episode
count. Each campaign verifies that the remote checkout and pinned runtime still
exist; a stale sync marker cannot hide a missing checkout, and restoration never
replaces code while another campaign owns slots.

Selection and authoring share the complete trace evidence catalog. It includes
ordinary user requests, structured clarifications, uploads, captured page chunks,
tool observations, delivery records, workspace text/binary versions and recovery
gaps. `list_evidence` searches and paginates the inventory; `read_evidence` returns
continuation offsets and archive members; `view_evidence_image` supplies retained
images. Neither retrieval nor inspection executes recovered programs or fetches
external URLs. Private reasoning bodies remain excluded.
Oversized images use labelled bounded previews; the original bytes and hashes
remain unchanged. Image inspection supports exact original-pixel regions and
animation frames, so resizing is not evidence removal.

The classifier must cite evidence it inspected, including the non-coding request
and supporting material. New index rows defer scope to content review rather
than rejecting by extension, byte share or session tags. A programming request
cannot be relabelled an audit to pass. Old-format indices retain their historical
screening behavior and should be rebuilt before selection.

Both production author routes expose the same evidence tools. `stage_evidence`
can explicitly copy inspected earlier evidence into `sources/`, preserving
context citations, chunk/failure state and source hashes. It refuses overwritten
files, unsafe paths, undone or future evidence and unanchored blobs. Archive
member bytes are replayed from the parent archive. Converted document text is
labelled a derived view and receives derived provenance credit, including after
privacy minimization. A later draft is available for private inspection; it is
not automatically a public fixture, correct answer or accepted revision.

DOCX/PPTX text, XLSX cell/formula XML, bounded ZIP/TAR/GZIP members and PDF text
are inspectable. PDF parsing runs in an isolated process with size, CPU and time
bounds; scans without extractable text remain explicitly unreadable as text.
Office layout, OCR, unsupported binary formats, oversized archives and images
over the inspection limit are reported as limitations. Available bytes are
never silently replaced with empty documents. Document conversion is not proof
of visual/layout fidelity. See the [evidence repair audit](../pipeline-artifacts/trace-evidence-20260921/REPORT.md).

```
Stage A  index      500 sessions -> 2,045 task seeds                  (mechanical)
Stage B  screen     hard floors only -- admissibility, not order      (mechanical)
Stage C  prioritise tier 1-4 on attachments / corrections / signals   (mechanical)
Stage D  classify   inspect requirements + full evidence, tier order  (bounded tool loop)
Stage D2 categories A Rich / B Strong / C Fixture-led / D Thin        (mechanical)
Stage E  compose    fill slots from the highest tier that can         (mechanical)
Stage F  author     9 stages, fixture before prose                    (agent + LLM)
Stage F2 repair     a gate blocker is fed back as a redesign          (LLM)
Stage F3 validity   short probe: can this task be MEASURED at all     (rollouts)
Stage G  gate       18 gates; must be green BEFORE calibration        (mechanical)
Stage H  calibrate  10 rollouts x named model, per-check bands
Stage I  ledger     faithfulness, measured per fixture file           (mechanical)
Stage I2 audit      the gates' assertions re-derived from artefacts   (mechanical)
Stage I3 verify     each grader run exactly as the container gets it  (mechanical)
Stage J  benchmark  the bundle through Harbor, in Docker              (mechanical)

Stage H2 harden     raise a chosen task's difficulty     (MANUAL -- never automatic)
```

THREE ROUTES TO A GRADABLE SEED. A seed needs one of them, and the scope rules
bind all three equally.

  dispute-led    two corrections a script could check. The checks come from
                 what the user objected to.
  fixture-led    documents that already support a determinate question --
                 "which sections do all six drafts share" is a real question
                 whether or not anyone argued about it.
  scenario-led   a determinate question and a fixture we AUTHOR, grounded in
                 the scenario the trace describes. Category D, and the reason
                 the document count cannot be the test: a D seed has almost no
                 recovered workspace, which is what makes it D.

Applying the dispute-led bar to all four categories is what collapsed the first
corpus from 360 admissible seeds to 14 viable. With all three it is 91: 13
dispute-led, 50 fixture-led, 28 scenario-led. Nothing about scope was relaxed --
`gradable`, a non-executing truth source and a non-code deliverable are checked
BEFORE the route is consulted, and the faithfulness floor per category is what
keeps the authoring honest:

    A Rich         90-100%      B Strong       90-100%
    C Fixture-led   80-90%      D Thin fixture  60-80%

Bundles are written into a folder named for their category -- `rich/`,
`strong/`, `fixture-led/`, `thin/` -- so a reader can see what kind of task it
is without opening a ledger. Tools find both that layout and the flat one, so
archived batches still sweep.

The historical stage label **F2** here denotes validity repair, not Scenario/F2
faithfulness. Its current default allowance is `policy.MAX_REPAIR_PASSES` (two),
with `ARENA_GATE_REPAIRS=0` opting out. F3 is an optional diagnostic. **F2** hands a gate blocker back to the designer
as explicit feedback, because the designer already repairs concrete named
defects and simply never saw these -- the gates run after the bundle is built.
**F3** is a validity probe, not the calibration of record: a few rollouts asking
whether the task can be measured at all -- no void rollouts, no check nothing
can reach, no near-miss betraying a convention the instruction never states. It
does not label a low score as a defect. Validity and usefulness for the target
cohort are separate: a valid all-fail task belongs in the stretch collection,
while production admission requires informative core decisions.
The current pipeline does not automatically use pilot or screen difficulty
feedback to redesign a task. It screens the whole graded batch, retains easy and
failed candidates in accounting, and stops. Hardening is manual and separately
versioned; native qualification remains the release requirement.

**H2 never runs by itself.** Nothing in `build` or `orchestrate` calls it and no
environment variable turns it on. You choose the task; it refuses to act without
a versioned, verified baseline and offers objectives passing at least 90% on
each measured model. With complete verified cohorts, it also targets mixed-model
objectives passing at least 90% on every model tied for the highest conservative
capability-adjusted pass@1. The reported all-model floor remains unchanged;
unreachable checks and checks hard on any binding model remain protected, and
targeted weights cannot decrease. Candidate ranking includes the weight of these
binding-model targets, and report mode lists them separately from the all-model
floor. Compare a fresh revision with `arena harden REVISION --compare ORIGINAL`.
Acceptance requires lower official and conservative capability-adjusted pass@1
on each model not already at zero, matching cohorts and harness settings, and
verified validity and failure attribution. Lower mean reward alone is insufficient;
a valid all-fail revision remains admissible. Full production qualification is
still separate.

`arena diagnose envs-cat -o inventory.json` produces one unique check inventory
from retained episodes. It separates objectives from guardrails and validity
from observed difficulty, reports void/missing episodes and uncertainty, and
never pools model rates into a synthetic core band. All reports use stretch
below 30%, core 30–70%, transition above 70% and below 90%, floor at least 90%.
Transition checks are allowed; their presence alone does not reject a task or
request a revision. They do not count toward the required core/stretch mix.
This diagnostic recount cannot certify semantic correctness or native execution.

## Run it

```bash
python3 -m pipeline.dump.index                     # A  ~2s over 6.2 GB
python3 -m pipeline.select.score --include-inspiration   # B
python3 -m pipeline.select.priority                     # C  -> tiered.json
set -a; . ./keys.env; set +a
python3 -m pipeline.select.classify --need 6 -j 8       # D  descends only as far as needed
python3 -m pipeline.select.shortlist                    # E  -> prints the shortlist

# batch two, without re-picking batch one's material
python3 -m pipeline.select.shortlist --exclude-sessions 019f9901,019e7532,01a000d5

python3 -m pipeline.run envs/<slug>                # G  pre-calibration
python3 -m pipeline.ledger.faithfulness envs/<slug> --session <id>
python3 -m pipeline.run envs/<slug> --calibration report.json   # G  post-calibration

python3 -m unittest discover -s pipeline/tests -t .

./arena categories                                 # D2 sort seeds A/B/C/D
./arena build --category A -n 3 -o envs-a          # F  build one category
./arena audit                                      # I2 the second reader
./arena audit envs-new -o report.json              # ... over any bundle tree
./arena verify                                     # I3 the grader as it ships
./arena harden --candidates                        # H2 what is hardenable
./arena harden envs/<slug>                         # H2 report; writes nothing
./arena harden envs/<slug> --apply                 # H2 write hardened/vN

# build chosen seeds rather than the top -n. Rank is 1-based over the survivors
# sorted by (tier, -dispute) -- the same order `arena status` prints -- and the
# bundle is named for its rank, so kw-a004 is always rank 4. Taking a prefix is
# how the rank-12 seed once shipped as kw-a004.
./arena build --ranks 4,10,13 -o envs-new          # F  the seeds a prefix skipped
./arena build --ranks 5,7 -o envs-redesign         # F  redesign, same seeds
```

Two builds can run at once: each output tree gets its own
`pipeline-artifacts/batch-build-<tree>.json` (`envs/` keeps the plain name).

## Two designers

`author/designer.py` is one forced tool call against a brief: the first fourteen
lines of each fixture document, the corrections, the constraints. Measured on
kw-a005 that brief carried 7,229 of the fixture's 28,896 characters, and the
model designed a ten-document reconciliation having seen a quarter of it.

`author/agent_designer.py`, the only designer, gets tools instead: it reads
whole documents, reads the trace, runs parsers to see real rows, **evaluates its
own target expressions to see the answers they compute**, and runs the validator
suite on a draft — all before emitting. The emission is still the same
`SPEC_TOOL` schema, so there is still nowhere to type an expected value.

`evaluate` is the one that earns its place: it reports when an answer is empty,
full of nulls, or mostly repeats. Every degeneracy defect in the first batch was
knowable that way and none of it was knowable from the brief.

File access is restricted to `environment/files/` **by resolved path**. The
bundle also holds `authoring/extraction/after/`, a later candidate repair. It
may leak a proposed answer; it is not proof of correctness or user acceptance.

The default agent designer can also use `write_scenario` for explicitly authored
case data grounded in exact recovered public quotations. It writes only owned
text/data files below `scenario/`, preserves every recovered file, and creates a
public disclosure plus a hash-bound provenance receipt. Additions receive zero
source credit, including copied supplemental material, and must fit the existing
category fidelity allowance (32 KiB per file, 128 KiB total). They cannot contain
answer keys or silently revise source facts. `remove_scenario` can remove a
verified owned supplement and update its disclosure; it cannot remove recovered
or unowned evidence. Failed removals restore the prior files and receipt. The
draft, ledger and exported grader must be rebuilt after a source change.
Independent review, causal controls
and fresh calibration still decide whether the resulting task is sound and useful.

Exit codes: `0` green, `1` blocked (a finding about the bundle), `2` unverified
(a finding about our ability to check it). `SKIPPED` and `ERROR` are never green.

`--legacy` runs the chain as a diagnostic over bundles that predate its
conventions. It reports; it does not certify.

## Why the stages are in this order

**Gradability before difficulty.** At a target of two or three environments you
can screen on failure signals. At ten you cannot: most high-signal sessions are
ungradable. So the kill filters run first and the signals rank *within* them.

**Classification after screening, before authoring.** The mechanical score cannot
tell a capability gap from a change of mind. Ranked by correction count, the top
of this corpus is *"make my dress the same colour"* and *"the font is too big,
not attractive"* — perfectly recoverable workspaces, many corrections, nothing a
grader could check. Measured: of 334 correction moments in the candidate pool,
**40% are unusable** (117 `other`, 8 `taste`, 5 `impatience`, 3 `infrastructure`).
That matches the previous dump's hand triage, which expected about half.

**Gates before calibration.** All nine defects Arena returned on the first
delivery were pre-calibration defects. None would have shown as an anomalous
score. Rollouts would never have found them.

## Where the content actually is

Recovery combines tool bodies, `workspaces/*.json` inline text and referenced
`files/` blobs. A manifest can use an explicit `file` reference or an implicit
`files/<hash>` reference. The 21 September inventory found 9,878 workspace
snapshots and 31,065 physical blobs across the 500 sessions. The earlier claim
that workspaces supplied almost no content omitted these channels.

Snapshots are joined to messages or unambiguous manifest nodes. `Workspace.at`
represents the observed state at that boundary, including removed/unavailable
paths; `Workspace.span` measures material recovered during a span, including
earlier drafts that were later deleted. Unanchored snapshots are quarantined.
The ledger binds actual supplied manifest/blob bytes. Exporter hashes may
predate declared upstream privacy masking; a matching original checksum is
never claimed when it differs. Retained binaries can receive byte-identical
source credit, while authoring still reports format support separately.

The original numerical funnel below is historical. Current recovery findings,
definitions and limitations are recorded in
[`workspace-recovery-20260921`](../pipeline-artifacts/workspace-recovery-20260921/).

`bash` output declares `stdout_truncated`/`stderr_truncated`, so truncation is
read rather than guessed: **1.27%** corpus-wide. Do not regex for `truncat`; it
matches those keys and reports ~100%.

## The funnel, measured

```
2,045 seeds / 500 sessions
  →    21  past the kill filters
  →    16  replay-ready (rr ≥ 0.55)   — 12 sessions, 8 frontier
  →     8  survive classification     —  6 sessions, 3 chainable
```

Dominant drop reasons: 962 seeds with fewer than two corrections, 686 seeds
under three turns, 251 with fewer than three recoverable deliverable paths.

**Non-coding knowledge work is genuinely scarce in this dump, and that is a
finding worth sending back.** Of five classified rejections, all were
`requires_execution`. If Arena wants this domain, the traces to send are
sessions where a professional produced a *document* under real constraints and
disputed its content at least once — that pair is what every yielding trace in
the previous delivery had.

### A bias worth recording

The first build of this funnel was tuned for code without anyone deciding it
should be: it counted source extensions, and scored a `package.json` or a test
file at 0.12 as "scaffolding". Under it the non-coding share of the candidate
pool was **8 seeds out of 102, one of which survived**. The corpus had not
changed — the thresholds had. Re-keyed on deliverable bytes (documents,
registers, tables) the same corpus yields 21 candidates and 8 survivors.

A second assumption died the same way: `structured_data` was weighted 0.14 on
the belief that a gradable task needs gradable source material. Measured, 19 of
21 candidates score zero — the traces carry prose. The output contract is
something we *impose* (kw-006 turned a document-structuring session into
`audit.json` + `pagination.csv`); what the trace must supply is the situation,
the documents and the corrections. Weight dropped to 0.06.

## Priority order: richest traces first

The pipeline used to draw one hard line and discard everything below it. That is
the wrong shape for a batched programme — wasteful at the top (a trace with 12
corrections and 27 retained files ranked beside one with 2 and 0) and fatal at
the bottom (a surviving pool of 6 sessions: enough for one batch and nothing
after it).

So the thresholds split in two:

- **Hard floors** — properties we cannot author around. A single-turn seed
  cannot be multi-step; a seed with no recoverable deliverable has no fixture;
  a code deliverable is out of scope; zero corrections means no failure mode.
  These still kill.
- **Tier boundaries** — properties that make a trace a better or worse starting
  point. These no longer kill, they *order*.

Relaxing the floors took the admissible pool from 21 seeds to **110**.

Three independent kinds of evidence set the tier, deliberately not blended until
the end, because a trace can be rich in one and empty in another and the remedy
differs:

| axis | what it measures | what it governs |
|---|---|---|
| **attachments** | retained files, recoverable documents, before/after pairs, workspace coverage | how much fixture we lift vs author |
| **corrections** | volume, persistence run, rollbacks | how many traps come from the trace vs from us |
| **signals** | steerability / complaint / explicit-outcome failures, plus endorsements | triage confidence |

`Evidence.total` is 60% mean and 40% *minimum* — a trace empty on any one axis
must not be lifted into a high tier by the other two, which a plain mean does.

| tier | seeds | sessions | trace-derived floor | meaning |
|---|---:|---:|---:|---|
| 1 | 6 | 5 | 70% | rich on all three axes — lift most of the fixture |
| 2 | 8 | 7 | 55% | strong on two — some authored traps |
| 3 | 28 | 21 | 40% | thin but workable — majority authored, grounded in the scenario |
| 4 | 68 | 46 | 30% | inspiration, not replay — and the ledger says so |

Boundaries (0.53 / 0.40 / 0.28) are the pool's own p95 / p85 / p60, **not
intuition** — set by intuition first, they put a single seed in tier 1, which is
a hard cut with extra steps rather than a priority order. They are absolute
rather than recomputed per corpus, so a tier means the same thing across dumps
and a better dump correctly produces a *larger* tier 1.

**Descending costs fidelity, and the cost is booked rather than absorbed.** Each
tier carries its own trace-derived trap floor, and `trap.faithful` reads the
bundle's `source_tier` instead of applying one flat number. A tier-3 trace held
to a tier-1 floor would only produce a bundle that lies about where its traps
came from.

Two consequences worth naming:

- **Classification descends only as far as it must.** Tier 4 is 68 of the 110
  candidates and the least likely to yield. Filling a batch of three took 14
  classifications instead of 110 — tier 1 gave 3 survivors, tier 2 gave 4, and
  the stage stopped. The depth it reached is recorded, and a batch that has to
  dig is itself the signal that the corpus is running out.
- **Tier always beats rank.** A rich tier-2 trace must not outrank a thin tier-1
  one, or the ordering is decorative. `compose` sorts on `(tier, -rank)` and
  reports `deepest_tier_drawn`, so a slot reaching down is visible.

## Difficulty, traps, and "the model should give up"

Wanting a model to hit a wall is the right instinct aimed at the wrong target. A
task every model fails carries exactly as much information as one every model
passes: none. One corpus here holds a task both models scored 0.00 on and another
both scored 1.00 on; neither taught anything.

There is a legitimate version, and it is the `unsatisfiable` trap: part of the
request cannot be met, and the correct answer *reports that* with its reason and
completes the rest. Then giving up is the graded behaviour — checkable, and the
models that fail it fail by **inventing** an answer. That is a real capability
gap and a common one in this corpus.

The other place strong models reliably break is **restraint**: they over-act. A
guardrail enforces an explicit public constraint and is usually what
separates frontier models, because capable agents "helpfully" fix the adjacent
thing they were told to leave alone.

Nine trap types, each declaring its axis, lever, proof obligation, and how it
fails when done badly:

| trap | axis | catches |
|---|---|---|
| `misleading_label` | inference | trusting the label over the content |
| `stale_authority` | inference | copying a source instead of arbitrating |
| `unreadable_source` | execution | giving up on a recoverable input |
| `unsatisfiable` | inference | fabricating rather than reporting |
| `forbidden_edit` | restraint | violating the user's stated prohibition |
| `scope_creep_bait` | restraint | fixing the adjacent broken thing |
| `regression_bait` | execution | a fix for A that silently breaks B |
| `plausible_decoy` | inference | the structurally identical wrong answer |
| `derived_answer` | inference | reading rather than computing (§0) |

**Traps may be invented.** The spec allows it — *"you can add extra cases beyond
what the original trace used… as long as the environment stays grounded in the
domain and situation of the source trace"* — and some of the sharpest traps
cannot come from a trace, because the user never hit that case.

So a trap declares its provenance:

- `trace_derived` — cites the moment, quotes the user's words, and its type must
  be one the classifier's correction class can legitimately become (a
  `forbidden_edit` cannot be derived from a taste complaint).
- `authored` — cites no moment, and instead names **a fixture surface that
  exists** plus why a practitioner in this scenario would plausibly meet the
  case.

The gate enforces a floor (≥50% trace-derived) rather than demanding 100%. The
difficulty can be invented; the world it happens in cannot.

## Reward hacking

Nine probes are mandatory and recorded in `verification/probes.json`. Three of
them are the floor and have no exemption:

- `forged_state` — write the expected end state without doing the work
- `answer_lookup` — read every fixture file and return what it says
- `empty_deliverable` — create the deliverable and write nothing into it. Added
  after two bundles scored 0.49 and 0.69 on it while passing every other gate:
  an objective whose correct answer is an empty collection is earned by
  declining to answer, and `seed_zero` cannot see it because it omits the
  deliverable entirely, so everything fails there for the wrong reason.

Both must score below 1.0, and a score above 0.5 warns: *a hack that earns most
of the reward is still a hack.* The others are `surface_leverage` (empty each document in turn; which ones
move a scored answer), `seed_zero` (every objective
0.0, every guardrail 1.0 on the untouched fixture), `golden`, `untidy_correct`,
`plausible_wrong` and `destructive`.

A missing probe file is an **ERROR**, not a pass — "not yet probed" is not
"probed and clean". And the bundle must declare `untested_surfaces`: every time
this stack was called closed, another surface turned up.

## The gate chain

Eighteen gates. Seven map one-to-one onto Arena's findings of 2026-09-10:

| their finding | gate | verified against |
|---|---|---|
| kw002 rejects the string `"1960"` | `grader.normalisation` | fires on kw-002 `criteria_hs.py:189` |
| kw003 rollback runs before cleanup is graded | `env.step_isolation` | fires on kw-002/3/6 |
| kw003 key says 26, truth is 27 | `grader.oracle` | fires on all four |
| kw003b client demands a forbidden fix | `env.policy_consistency` | no counterparty in these bundles |
| kw006 missing edge-case rule (×2) | `contract.completeness` | fires on kw-001 only |
| kw006 ambiguous verdict categories (×2) | `contract.ambiguity` | fires on kw-003 |
| kw006 hidden evidence whitelist | `contract.enumeration` | fires on kw-006 `allowed-references.json` |

Plus `bundle.structure`, `bundle.ledger`, `answer.derivation`, `leak.sweep`,
`trap.faithful`, `trap.beatable`, `difficulty.axes`, `hacking.resistance`,
`grader.reference`, and two post-calibration gates (`calibration.bands`,
`calibration.validity`).

`grader.reference` is the one that reads the reference answer itself, and it
exists because nothing else did. Every defect below shipped GREEN through the
other seventeen, because the grader is self-consistent with its own key however
nonsensical that key is — `golden` is 1.0 and `seed_zero` is 0.0 either way:

| defect | measured on |
|---|---|
| a null in the answer (the parser cannot read the plucked field) | a004: `[None] × 15` |
| an answer that is mostly repeats | a003: 250 entries, 57 distinct |
| one value dominating an answer | a010: `'Setting'` × 15 of 29 |
| a hand-typed literal list **at any depth** | a005: 67% of weight, nested inside `difference` |
| objective weights that do not sum to 100 | the batch ran 84–128 |

The depth matters: the first version of the literal check looked only at the
top-level `op`, and the next design wrapped the same hand-typed list inside a
`difference` and passed. A scalar sentinel is legitimate anywhere; a list is an
answer key wherever it appears.

## Known limits

Research-informed construction aids and the cohort-specific redesign hypotheses
are documented in `HARDENING_RESEARCH.md`. They reach first-pass authoring and
manual hardening, preserve the three-attempt cap, and are not measured hardness
or additional validity gates. Existing frozen campaigns remain unchanged.
The private `plan_challenge` author tool constructs criterion-specific and selected
interacting near-misses, promotion/invariance outlines and selective revision
recomputation scopes. It writes no public fixtures or reference answers; authors
still need real witnesses, independently derived controls and native measurement.
The private `plan_portfolio` tool adds LAB-inspired matter-room planning where the
source engagement fits: substantive judgment groups, source-specific controls,
shared-input revisions and sustained wrong policies. See `LAB_PORTFOLIO_RESEARCH.md`.
It imports no LLM judge or answer key and does not increase objective or attempt limits.
Solver autonomy means a complete assignment without task-specific solution coaching.
Private `solver_brief` diagnostics flag common reading-order, algorithm, trap-warning,
solver-code and authoring-reference hints in staged instructions. Independent review
also inspects public fixture documentation, comments, metadata and attachments.
These advisory heuristics never remove source evidence, normative rules or tool access,
never certify a leak-free task and never change an active frozen campaign.
The unscaffolded-task constraint is enforced separately: independent review must
return a cited `solver_autonomy` assessment covering the trusted visibility inventory.
Missing or incomplete sign-off is unverified; unresolved solution coaching holds the
candidate for the existing repair loop and cannot pass validation or release. The
private inventory includes public sources/instructions and package exposure boundaries;
it is not shipped to the solver. This neither grants extra attempts nor proves hardness.
Transport recovery retains saved author drafts, conversations and remaining
response budgets; it refuses changed or incomplete boundaries instead of rerolling.

Stated because this repository's history is a series of holes found only by
probing something already declared closed.

- **`contract.completeness` is lexical.** A rule stated in different words scores
  low and is not a defect; a coincidental word match scores high and is. It
  blocks only at *zero* overlap and hands the 0–45% band over as a reading queue.
- **`answer.derivation` lower-bounds leakage.** It proves a stored digest or a
  reproduced answer document. It cannot decide whether the *mapping* is stored —
  a task whose answer is "which page is contested" draws its values from a
  published vocabulary by construction. Only a human reading the fixture rules
  that out.
- **`contract.enumeration` keys on the name.** An accept-list under a neutral
  name is invisible. The full inventory ships as evidence for sign-off.
- **`env.policy_consistency` has never fired.** No shipped bundle has a scripted
  counterparty, so it is untested against a real defect.
- **The ledger understates faithfulness.** Recovery is partial, so a file whose
  content came from the session but which the trace never revealed is recorded
  as `authored`.
- **"Flawless" is not something this chain can certify.** It can prove the
  bundle parses, the reference solution scores 1.0, seed-zero is clean, the
  named hacks fail, every trap is beatable and discriminating, and every scored
  rule is published. It cannot prove there is no *unknown* defect — that is what
  `untested_surfaces` is for, and why the chain reports `unverified` rather than
  green whenever it could not actually check something.
- **Stage D is one model's judgment.** Determinism comes from the strict schema
  and the content-addressed cache, not from `temperature` — which this model
  rejects. Deleting the cache is a deliberate act.

## Batch discipline

Three environments per batch, composed rather than skimmed — and the slots span
the three **difficulty axes**, not three domains:

| slot | axis | picked for |
|---|---|---|
| `derived_answer` | inference | the target is recomputed from the sources at grade time, so it cannot be matched from a contract or copied from a record |
| `chained` | execution | two graded steps, exercising the step-isolation gate — the defect kw-003 shipped with |
| `restraint` | restraint | the user stated prohibitions the agent broke, which become guardrails — where capable models over-act |

Three document tasks that all load inference teach us about inference three
times. One per axis tells us which axis our authoring actually handles. An
unfillable slot is reported empty, never backfilled.

A batch closes when every bundle is green, 4–6 core checks across each task sit
in the 30–70% band for each model, every scored step retains substantive work,
no prerequisite gate rests outside the core band, every zero is classified model-failure or void,
and the ledger is emitted. Then the next batch starts, and Stage B/E thresholds
are re-fit on what batch N actually taught us.

## Deliverable zips (per step)

Arena receives each environment as one zip per step, `<task>__<step>.zip` (reference: batch 32's
`a_f2_worldbuilding-design-canon__01-task.zip` / `__02-revision.zip`). Every zip is the COMPLETE native
Harbor task root at the zip root (all steps, tests and solution, unchanged) plus the 10x2 calibration of
record sliced to that step:

    CALIBRATION-MANIFEST.json   task "<task>/<step>", source session, level, package name,
                                steps_tests_solution_sha256, task-level metrics per model
    calibration/runs.csv        model,run,trial_id,step_score,checks_passed,checks_total,turns,
                                prompt_tokens,completion_tokens,failed_checks  (valid runs only)
    calibration/trajectories/<model>/<trial>/{agent/trajectory.json, artifacts/, verifier/*}
    README.md                   task, task-level and this-step tables, where points were lost
    REWARD-HACKING.md, verification/{controls,delivery,harbor-tasks-check,probes}.json

Order of operations: `arena qualify` (accepted) -> `arena deliver --accepted-only` -> `harbor tasks-check`
on the DELIVERED copy -> `arena deliverable` (writes REWARD-HACKING.md) -> `arena stepzips <delivery> -o <dir>`.
`stepzips` checks every zip it writes (structure, manifest, one row and trajectory per valid run, the
re-computed steps/tests/solution hash, a passing tasks-check receipt bound to the packaged identity, and the
shipped reference solution scoring 1.0 on every step through the shipped grader); `--check-only` re-checks
a directory of zips.
