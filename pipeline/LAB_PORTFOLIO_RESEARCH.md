# LAB-inspired deterministic portfolio tasks

## Verified sources and limits

Research date: 1 October 2026. The inspected upstream revision is
`harveyai/harvey-labs@f93ae2ac2831e65892fea83094cfb50149bc2e59`.
The focused inspection covers README, license, architecture, tutorial, evaluation
methodology, score-impact changelog, scoring and judge implementations, and the
change-of-control task's rubric and all 19 DOCX matter documents. Documents were
read as data, including comments, footnotes and tracked-deletion markers; no
upstream setup script, agent or judge was executed. This is not an audit of every
task or proof that the public corpus has no defects.

- [Harvey announcement](https://www.harvey.ai/blog/introducing-harveys-legal-agent-benchmark):
  the original release has over 1,200 tasks, 24 practice areas and 75,000 criteria.
- [Vals' primary model comparison](https://www.vals.ai/comparisons/anthropic_claude-fable-5-1-vs-openai_gpt-6-astra)
  directly reports LAB scores of 6.67% for Fable 5.1 and 5.42% for GPT-6 Astra,
  each with reported ±1.17 percentage-point standard error. These are Vals
  results, not our native episodes or a prediction for a transformed task.
- [Evaluation methodology](https://github.com/harveyai/harvey-labs/blob/main/docs/eval-strategies.md)
  grades each criterion semantically with two LLM judges and averages their
  binary all-pass task results. Our deterministic grader must not import this
  judge, subjective prose requirements or equal-weight scoring.
- [Change-of-control task](https://github.com/harveyai/harvey-labs/tree/main/tasks/corporate-ma/analyze-change-of-control-provisions-across-targets-material-contracts)
  has 57 criteria in the inspected revision and 19 matter files. Eight material
  contracts are mentioned in the rubric; this is not 57 independent decisions.
  The portfolio mixes trigger interpretation, economic consequences, exceptions,
  deadlines, outstanding actions and cross-contract synthesis.
- [Tutorial](https://github.com/harveyai/harvey-labs/blob/main/docs/tutorial.md)
  uses a different red-flag task with 60 documents and 68 criteria and explicitly
  warns that its lawyer-guided synthetic documents can contain imperfections.
- [Score-impact changelog](https://github.com/harveyai/harvey-labs/blob/main/CHANGELOG.md)
  records judge, extraction, harness and adapter changes that affect comparability.
  For example, changing from one judge to two changes the reported all-pass score.

The two inspected deal memos describe different target businesses, not merely
two competing dates for the same matter. Bind the requested matter and entities
before applying a published authority rule. Blindly picking the latest memo or
inventing a precedence rule can turn a retrieval trap into an invalid task.

Public issues such as [the buyer-name inconsistency report](https://github.com/harveyai/harvey-labs/issues/129)
are additional reasons to rederive conclusions and obtain independent review,
not evidence that every low score is an incapability failure. Public rubrics and
documents are research references only. Do not copy them into a supposedly
private benchmark, call them source-trace evidence, or treat them as held-out.

## What transfers

Design a compact complete work product whose correctness requires resolving
several genuine professional judgments across a distributed matter file.
For a source-supported acquisition audit, a useful structure is:

1. Identify the requested matter, exact entity, instrument and transaction steps.
2. Reconcile scoped executed amendments and effective-time authority.
3. Distinguish assignment, ownership change, merger and asset transfer under the
   actual public clauses; do not silently import external legal doctrine.
4. Apply thresholds, direct/indirect ownership and all exception conditions.
5. Determine remaining consent and notice duties after scoped waivers.
6. Separate termination, loss of exclusivity, repayment and contingent payout.
7. Derive deadlines and disjoint economic exposures with public counting rules.
8. Assess source-supported joint closing readiness and genuine non-issues.
9. Revise the affected portfolio after new deal evidence, preserving other work.

These are design directions, not a mandatory nine-check rubric. A source that
cannot support them must retain its own engagement. A deadline derived from a
trigger is not automatically an independent bottleneck. Prefer 8–10 genuine
judgment groups only where supported and within the existing 4–6 core, 0–2 floor,
1–4 stretch bands. Adding sixty small fields, increasing weights or requiring
exact prose does not establish difficulty. One upstream mistake remains one
failure cause even if it propagates into many records.

Require bounded structured outcomes only where a public rule actually settles
them: `triggered`, `not_triggered` or a justified `undetermined`; remaining
obligations; applicable consequences; and deadlines or legitimate non-applicable
nulls. Keep materiality, competition, uncertain law, severity and discretionary
recommendations unscored unless accessible rules and independent domain review
support the exact finite decision. Accept every permitted interpretation,
equivalent conclusion and presentation ordering.

## Pipeline implementation

`pipeline/author/portfolio.py` exposes `plan_portfolio` to initial authoring and
manual hardening through the shared challenge prompt. It creates private
decision-group, per-source intervention, criterion-witness, shared-input revision
and sustained-wrong-policy outlines. It writes no fixture, reference answer or
grader. Source fit and independence remain unestablished until reviewed.
The tool also reads the staged draft's existing stretch capacity.

Example tool arguments, adapted to an actual source engagement:

```json
{
  "workflow": "contract_applicability",
  "source_fit": "Audit the source matter's remaining closing obligations.",
  "records": [
    {"id": "instrument-a", "decision": "obligation-a",
     "sources": ["agreements/a.md", "deal/committed-close.md"],
     "checks": ["obj_a"], "discriminators": ["entity", "trigger", "waiver-scope"]},
    {"id": "instrument-b", "decision": "obligation-b",
     "sources": ["agreements/b.md", "deal/committed-close.md"],
     "checks": ["obj_b"], "discriminators": ["entity", "threshold", "exception"]}
  ],
  "shared_inputs": [
    {"id": "closing-date", "sources": ["deal/committed-close.md"],
     "records": ["instrument-a", "instrument-b"],
     "public_convention": "Use the committed close, not a projected postponement."}
  ],
  "wrong_policies": [
    {"id": "notice-equals-consent", "records": ["instrument-a", "instrument-b"]}
  ]
}
```

Optionally retain these arguments as `quality.portfolio_plan`; diagnostics check
their declared linkage to `quality.decisions` without adding a validity veto.
Each actual target still derives from evidence using existing expressions such
as `bind_rows`, `derive_rows`, `compare`, `latest` and calendar-day `date_add`.
Whole unordered record collections use `multiset_equals`, preserving duplicates
and accepting reorderings. Do not pretend calendar-day addition implements a
business-day calendar. Unsupported calendar or open-ended legal semantics need
a supported public derivation or a different task, not an approximate grader.

`test_portfolio_export.py` exercises this existing deterministic grading path:
correct/reordered answers, duplicate and exchanged rows, a waiver that does not
waive notice, scoped amendments, shared closing-date changes and strict threshold
boundaries. This small parameterized example is a regression fixture, not an
extremely hard task, a production-valid environment or native benchmark evidence.

## Acceptance and statistical claims

Keep source fidelity, explicit public rules, coherent source controls, independently
phrased legitimate alternatives, honest whole-evidence tool baselines and fresh
independent review. Apply each wrong policy throughout its true scope and inspect
its actual graded failures. Counterfactual control success establishes particular
validity properties, not that a frontier model will make the mistake.

A 90% marginal criterion pass rate does not determine all-pass: errors are
correlated. `0.9**60` assumes identical independent criterion outcomes, and
`0.9**10` would still be roughly 35%, not below the campaign's 20% target.
Do not use either calculation as measured difficulty. Average criteria scores,
LLM-judge scores and native task pass@1 are different quantities.

Retain the three-attempt lineage cap and all spent attempts. The campaign still
needs five development episodes and ten independent qualification episodes per
exact model, both official and conservative capability-adjusted pass@1 <=0.2;
Medical also needs both steps separately. No new sampling scheme or fourth
attempt is authorized. Existing active snapshots, tasks, trajectories and scores
remain unchanged; freeze future authoring at a settled boundary and measure any
changed artifact under its own policy identity. No honest design can guarantee
that either model will fail almost always before that measurement.
