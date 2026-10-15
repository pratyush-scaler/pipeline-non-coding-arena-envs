# v2 difficulty synthesis (2026-10-02)

Five research passes fed the v2 pipeline. Full reports sit next to this file.

| report | scope | size |
|---|---|---|
| R1-new-difficulty-techniques.md | web: techniques beyond the v1 catalogue, with executed checks of tool behaviour | 66 sources |
| R2-observed-cli-tasks.md | web: ~250 public non-coding agent tasks from 30 benchmarks, per-task appendix | 163 rows |
| R3-agent-habits-and-cli-tasks.md | our 6,292 recorded Claude Code / Codex steps; MSL CLI tasks | measured |
| R4-pipeline-map.md | every blocker, repair rule and difficulty hook in this pipeline | file:line |
| R5-decoys-whatnothow-density-families.md | decoys, what-not-how, density arithmetic, model-family skews, validity | 87 sources |

Nothing in them is measured on Fable 5.1 in Claude Code or GPT-6 Astra in Codex on
our task shape except R3's habits. Every lever below is a hypothesis for the 5x2 screen.

## What the evidence says, in one page

1. **Why v1 tasks scored 1.00/1.00.** Both models list every file, script every stated
   rule, compute a decoy value beside the right one and reject it, and apply any
   instruction-stated rule literally. ~1% of 2,557 episodes had genuine errors.
2. **Density arithmetic.** pass@1 ~ (1-q)^n for n independent decisions. At q ~ 1% a task
   needs ~69 decisions to drop below 0.5; at q ~ 10-15% it needs 10-16 per model family.
   Harvey LAB behaves like ~30 independent criteria (Fable 5.1 86.6% of criteria, 6.7% of
   tasks). Correlated decisions do not multiply.
3. **What the agents actually do (R3).**
   - Only 15.5% of steps display every file.
   - Unnamed small files are never opened in 65-67% of steps.
   - Files over 16 KB are grepped, not read.
   - Codex cuts the middle of long outputs in 56% of Astra steps.
   - Verification is structural, so a misreading that keeps the answer's shape survives.
   - v1 shipped `scenario/README.md` naming every authored trap file; it was opened in 97%
     (Fable) / 88% (Astra) of steps.
4. **Decoys bite as population members, not rival values (R5).** TrustDABench: marked
   non-observation rows were the most damaging perturbation for every model with Python.
   Near-twins differing in one attribute; one entity under surface variants.
5. **Rules in documents, procedure withheld, definitions kept (R2, R5).** WorkArena++ 3% ->
   0% when steps are withheld (humans 93.9%). The hardest public tasks write outcome-only
   instructions (Harvey median 39 words) and keep every rule in the files. Deleting
   *definitions* only creates ambiguity.
6. **Faithful-implementation betrayal (R1).** A fully stated house rule that the default
   numeric stack violates on specific values:
   - `round(2.625, 2) = 2.62`;
   - `3 * 0.145` gives 0.43, not 0.44, even via `Decimal(str())`;
   - same-zone datetime subtraction across a clock change gives 8 h, not 9.
   Astra computes exactly but rounds once at the end (5/5 failures on a per-line rule).
7. **Family skews (R2, R5).**
   - *Fable:* over-attempts (72.6% of questions it gets wrong); credits unverifiable
     authority; copies stated figures; falls for a salient purpose-labelled decoy that loses
     only once two rules stack (tau2 task_075, 0/4); takes the first matching rule where the
     rules say they stack (DABstep: Opus 5 fails 90-100%); doesn't extend a general
     wildcard clause to a boolean field (80-100%).
   - *Astra:* programs one predicate; takes the first match; misses surface variants;
     withholds on resolvable conflicts; fails execution-order dependencies set in another
     document (task_060, 0/4); fails change-set counterfactuals (65%).
8. **Validity is the binding constraint.** 70% of TB2 tasks under 0.3 solve rate were later
   fixed as defects; 46% of sampled HLE items are defective; every v1 "bite" that failed both
   families was an ambiguity. Hard is only worth anything if it is genuine.

## What v2 implemented (commit 70993bf onward)

- `pipeline/advisory.py`: only required findings block or repair; quotas, bands, weight
  shapes, construction plans, self-audit shape, trap counts and answer-shape heuristics
  are advisories. Unknown findings fail safe (blocking).
- Witness-mode hidden-rule check: a rule cited verbatim from any accessible document
  counts as published; lexical co-occurrence is advisory; `extract` patterns are exempt.
- Authored documents at natural paths, up to 256 KiB/file and 2 MiB total, in more text
  formats; the disclosure notice moved out of the fixture into `provenance/`.
- `pipeline/author/levers.py`: 36 catalogued levers (each tagged by target family, with its
  evidence and a recipe), the dead-lever list, a hint lexicon and the fragility-budget
  audit. The doctrine leads the designer's system prompt; check_draft reports it
  (advisory).
- Bands widened to core 4-24 / floor 0-4 / stretch 1-16 (min 8 objectives kept).
- Gate cascade fix (skipped behind a failure is blocked, not unverified); repair-stage fix.
- The review prompt reads dense tasks correctly and is strict on genuineness: strongest
  counter-reading, every field defined for every case, no world knowledge.
- Designer and classifier: claude-opus-5-5 at xhigh, 220 turns.

## Not done, and why

- **Contract-probe gate.** It still raises (not repairable) when the reference doesn't
  score 1; the permission classifier blocked editing it as security-test removal.
- **Grader support for .ics recurrence (R1 T5) and xlsx/docx format semantics (R1 T2/T3).**
  Not implemented: the task image is stdlib-only and the grader has no RFC 5545 expander
  or OOXML parser. Recipes that need them are excluded from the doctrine for now.
- **In-authoring solver probe.** Not re-added: the user removed presolve on 2026-09-25, and
  a no-tools probe mis-predicts tool-using agents.
