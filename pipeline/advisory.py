"""Advisory findings: reported, never blocking (user, 2026-10-02).

"Blockers and repairs should only be for required checks." Required means
validity and safety -- the grader runs and derives every target, the reference
scores 1 and an untouched workspace 0, no stored or leaked answer, no reward
hack, every output field defined, referenced paths exist, no grading rule that
no agent-readable surface states, step isolation, privacy, provenance honesty,
Harbor format and failure attribution.

Everything below is construction bookkeeping, a quota, a band, a weight shape
or a difficulty heuristic. Each was useful as a prompt to the designer and each
cost candidates when it blocked: a repeated finding is terminal, and the repair
budget is two passes shared by every stage. They are now advisories: the
designer still sees them (`check_draft`), the bundle records them
(`verification/advisories.json`), and the screen report prints them. Nothing
here can block a task or start a repair.

Fail-safe direction: a finding no pattern names stays BLOCKING. Adding a
pattern here demotes a finding; forgetting one keeps the v1 behaviour.
"""
from __future__ import annotations

import re

from . import policy

#: (pattern, why it is advisory). Patterns match the finding text as the
#: validators phrase it, case-insensitively, anywhere in the message (the
#: designer path prefixes "Draft validation: ").
ADVISORY_PATTERNS: tuple[tuple[str, str], ...] = (
    # --- author/quality.production_problems: construction bookkeeping ---------
    (r"duplicate objective cannot add independent difficulty signal", "rubric quality"),
    (r"quality\.axes needs at least two", "difficulty self-declaration"),
    (r"quality\.levers needs a substantive lever", "difficulty self-declaration"),
    (r"novelty must explain the distinct reasoning problem", "prose minimum"),
    (r"semantic_checks names missing or non-objective checks", "bookkeeping"),
    (r"at least 70% of objective weight must cover substantive", "weight quota"),
    (r"weak assertion or literal cannot count as a semantic objective", "weight quota"),
    (r"decisions need distinct nonempty IDs", "bookkeeping"),
    (r"decision [^:]*: needs a professional question", "bookkeeping"),
    (r"decision [^:]*: invalid source", "bookkeeping"),
    (r"decision [^:]*: unknown or repeated semantic check", "bookkeeping"),
    (r"every semantic check must belong to exactly one substantive decision", "bookkeeping"),
    (r"source changes do not exercise semantic checks", "deferred to all-fail attribution"),
    (r"objectives across all steps; got", "band quota"),
    (r"need at least four distinct core decisions", "decision quota"),
    (r"each scored step needs at least 70% substantive", "weight quota"),
    (r"only substantive core checks may be prerequisites", "rubric shape"),
    (r"required field has no semantic check or reviewable presentation-only rationale", "coverage prose"),
    (r"invalid source evidence quality\.source_evidence", "bookkeeping"),
    (r"at least two distinct fixture files need exact decision-rule citations", "bookkeeping"),
    (r"load-bearing source .* needs an exact evidence citation", "bookkeeping"),
    (r"no source-change control demonstrates the role of", "deferred to all-fail attribution"),
    (r"quality\.difficulty_case", "process self-audit"),
    (r"quality\.capability_plan", "construction plan"),
    (r"stage quality\.capability_plan", "construction plan"),
    (r"decision [^:]*: repeated check ownership", "construction plan"),
    # --- author/validate.validate: scoring shape and prose minimums -----------
    (r"weights must reflect importance", "weight shape"),
    (r"share only \d+ distinct weights", "weight shape"),
    (r"of the task reward as graded, above", "weight shape"),
    (r"has no reasoned basis\. Give one sentence", "prose minimum"),
    (r"'important' is not a justification for a weight", "prose minimum"),
    (r"gates? .*% of (the )?(task )?reward through", "rubric shape"),
    (r"concentrates .* behind one check", "rubric shape"),
    (r"second_step\.instruction is too short", "prose minimum"),
    (r"second_step\.new_information must say", "prose minimum"),
    (r"no traps declared", "trap quota"),
    (r"trap '[^']*': drives no check", "trap bookkeeping"),
    (r"trap '[^']*': grounded_in", "trap bookkeeping"),
    (r"trap '[^']*': authored trap needs 'grounding'", "trap bookkeeping"),
    (r"trap '[^']*': probe '[^']*' always scores the same", "trap bookkeeping"),
    # --- harden.revision_problems: pass@1 counts FULL success, so a weight never
    # moves it; a lowered weight only shifts mean reward (a-006 attempt 1, 2026-10-02).
    (r"reducing a targeted check's weight cannot supply difficulty", "weight shape (pass@1 is weight-free)"),
    # --- harden.routing_problems: a routing quota, not validity ----------------
    (r"^new trap \S+ drives \d+ graded objective\(s\); route at least", "trap routing quota"),
    # --- author/validate._hidden_rules (witness mode): lexical co-occurrence --
    (r"is not stated by any rule_quote \(no quoted sentence names", "lexical co-occurrence (witness mode)"),
    # --- author/designer.verify_solution: heuristics --------------------------
    (r"of the objective weight is a single-surface read-off", "difficulty heuristic"),
    (r"these objectives resolve to the SAME answer", "rubric quality"),
    (r"the reference answer is mostly repeats", "answer-shape heuristic"),
    # --- author/premises: the conjunctive design's targets (Arena 261013) ------
    # Premise count and share, free share, family distinctness, the timestamp
    # cap and discouraged families are design targets the screen measures. The
    # map's integrity ("premise map: ...") is not listed, so it stays blocking.
    (r"premise shape: ", "conjunctive design target (premise count/share/families)"),
    # --- assurance.controls: misreading-shape rules (not validity) -------------
    (r"^(Draft validation: )?misreading of trap ", "process self-audit"),
    (r"control-failed: misreading of trap ", "process self-audit"),
    (r"tool baselines? ", "construction plan"),
    (r"exact intervention scope|declared change set", "construction plan"),
)

_COMPILED = tuple((re.compile(p, re.I), why) for p, why in ADVISORY_PATTERNS)

#: Findings that must stay blocking even when an advisory pattern matches
#: (a validity property phrased with a word above).
_ALWAYS_BLOCKING = tuple(re.compile(p, re.I) for p in (
    r"reference (solution|answer)? ?(scores|scored|does not score)",
    r"answer[- ]stored|stored answer|literal-answer-key|hand-typed answer",
    r"counterexamples do not cover",
    r"not verbatim in step .*instruction",       # an invalid witness is not a witness
    r"carries no `rule_quote` or valid `rule_sources`",
    r"is not discoverable in any agent-readable",
))


def classify(finding: str) -> str | None:
    """The advisory reason for a finding, or None when it blocks."""
    if not policy.ADVISORY_FINDINGS:
        return None
    text = str(finding)
    if any(p.search(text) for p in _ALWAYS_BLOCKING):
        return None
    for pattern, why in _COMPILED:
        if pattern.search(text):
            return why
    return None


def split(findings) -> tuple[list, list]:
    """(blocking, advisory) -- order preserved within each list."""
    blocking, advisory = [], []
    for finding in findings or []:
        (advisory if classify(finding) else blocking).append(finding)
    return blocking, advisory


def annotate(findings) -> list[dict]:
    """Advisories as {finding, reason} records for receipts and reports."""
    return [{"finding": f, "reason": classify(f)} for f in findings or [] if classify(f)]
