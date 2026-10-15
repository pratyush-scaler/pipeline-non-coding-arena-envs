"""Private checks for unscaffolded assignments, never concealment of public rules."""
from __future__ import annotations

import hashlib
import re
from pathlib import Path

from .contracts import contained


PROMPT = """
8. SOLVER AUTONOMY: A COMPLETE ASSIGNMENT, NOT A SOLUTION WALKTHROUGH.
The solver must know WHAT to deliver and discover HOW to do the substantive
work. Give the professional goal, required deliverables, field meanings,
permitted alternatives, negative obligations and edge-case conventions. Keep
all load-bearing evidence and normative rules discoverable at the relevant
step, in the documents where a professional would find them. A required scope,
threshold, formula, counting convention or named governing authority is not a
solution hint merely because it helps settle the answer. Preserve it.

Do not publish a task-specific reading order, join/filter sequence, worked
solution, executable solver, answer-bearing example, resolved conflict list,
decoy labels or a warning that identifies the planted mistake. Keep author
plans, tool baselines, grader expressions, counterexamples and reference answers
private. Ordinary workspace locations, file inventories, output schemas and
generic tool documentation remain available; discovering a solution does not
mean guessing how to access the environment or what an output field means.

Audit ALL solver-visible surfaces, including operating notes, fixture comments,
metadata and attachments, not just the assignment. Do not relocate a solution
walkthrough from the instruction into a public README. Do not erase a recovered
business procedure or real source evidence simply to manufacture difficulty:
retain source fidelity, record any existing scaffold honestly, and redesign only
within the current authorization. Never hide a public acceptance criterion,
remove tools, restrict evidence access or alter the model's native affordances.

check_draft returns solver_brief diagnostics for common instructional hints.
These are private, English-language heuristics, not a completeness, leak-free
or hardness certificate and not new validity blockers. Independently review
every flagged passage: remove non-normative coaching, preserve required meaning
and publicly accessible authority. A REPAIR-ONLY brief still governs changes.
Independent review must now return a complete solver_autonomy assessment over
the controller's solver-visibility.json inventory. Missing assessment prevents
acceptance; unresolved task-specific coaching enters the existing repair loop.
This is an explicit user-required design constraint, not measured hardness or
a reason to remove a genuine business rule or source procedure. No automatic
regex-based deletion or new attempt allowance is permitted.
Changing the public brief changes the artifact; retain old scores and measure
the revised artifact afresh rather than claiming its prior score transfers.
"""

REVIEW_PROMPT = """
SOLVER AUTONOMY REVIEW. Inspect the assignment AND all agent-visible surfaces,
including operating notes, fixture READMEs, comments, metadata and attachments.
The solver should receive the complete professional goal and output contract,
not a task-specific reading order, solution script, worked answer, join/filter
recipe, resolved conflict list or labels identifying which records are decoys.
Check for a walkthrough relocated into the fixture. Distinguish such coaching
from genuine source evidence, a recovered business procedure, generic tool
documentation, ordinary file inventories and normative business rules.
Required field meanings, exclusions, formulas, boundary/counting conventions
and governing authority must remain public and accessible at the proper step.
Naming a required governing document is not automatically solution leakage.
Missing those requirements is a validity defect; never recommend removing them
to make the solver guess. An unnecessary procedural hint is a difficulty
concern, not automatically a semantic validity defect. It still fails the
user-required unscaffolded-task acceptance below. Actual answers/private grading
information or credit without doing the stated work violate existing validity rules.
Cite the concrete surface and explain the distinction; do not
infer incapability from a short brief or claim that heuristic silence proves
the task is leak-free. Keep all solver tools and native affordances unchanged.

MANDATORY UNSCAFFOLDED-TASK ACCEPTANCE. The user explicitly requires this
design constraint, separately from validity and empirical difficulty. A task
may be otherwise valid yet fail this constraint; report that distinction.
Read solver-visibility.json, the controller's private inventory of public
surfaces and build/interface exposure surfaces, and assess EVERY listed file.
The inventory is not an answer key and must not be copied to the solver.
Add this object to review.json:
"solver_autonomy": {
  "schema": "arena-pipeline/solver-autonomy-review/1",
  "verdict": "pass" or "revise",
  "reason": "at least 80 characters of specific semantic reasoning",
  "requirements_preserved": true or false,
  "evidence_access_preserved": true or false,
  "native_tools_preserved": true or false,
  "surfaces": [{
    "file": "exact path from solver-visibility.json",
    "classification": "requirements_or_evidence" or "generic_environment_help"
                      or "task_specific_coaching" or "answer_or_grader_leak",
    "reason": "at least 40 characters explaining the actual content",
    "quote": "one exact contiguous passage of at least 15 characters"
  }]
}
For a file shorter than 15 characters or containing only whitespace, quote its
complete exact content instead.
Assess the whole surface, not just the quoted passage. If coaching or answer
leakage occurs anywhere in a file, use that classification even when the rest
is legitimate evidence. Genuine recovered business procedures and normative
formulas remain requirements_or_evidence; explain why, rather than erase them.
Use revise for unresolved task-specific coaching or lost requirements, evidence
or tools. Do not hide coaching solely in difficulty_advisories: the pipeline
holds it for repair under this user-required design constraint. Otherwise retain
the existing separation of validity findings and difficulty advisories.
An unknown or uninspectable surface is unverified, not proof of a clean task.
No assessment or citation is a mathematical guarantee of semantic completeness
or frontier-model failure; report concrete limitations honestly.
"""

_HINTS = {
    "solution_recipe": re.compile(r"\b(?:solution (?:recipe|walkthrough)|recommended (?:solution|algorithm)|"
        r"to (?:solve|complete) (?:this|the) task|(?:first|then|next),?\s+(?:join|filter|group|compute|calculate|compare)\b)", re.I),
    "reading_order": re.compile(r"\b(?:start by|begin by|first)\s+(?:reading|opening|inspecting)\b", re.I),
    "trap_warning": re.compile(r"\b(?:beware of|watch out for|do not be fooled by|the trap is|"
        r"decoys? (?:is|are|include))\b", re.I),
    "solver_code": re.compile(r"```[ \t]*(?:python|javascript|typescript|bash|sh|sql)\b", re.I),
    "private_authoring_reference": re.compile(r"\b(?:plan_challenge|plan_portfolio|check_draft|evaluate_target|"
        r"candidate-spec\.json|quality\.capability_plan)\b|"
        r"(?:authoring/spec\.json|tests/checks\.json|solution/submission/)", re.I),
}


def construction_diagnostics(spec: dict) -> dict:
    steps = spec.get("steps")
    if spec.get("instruction"):
        second = spec.get("second_step")
        steps = [{"name": "01-task", "instruction": spec.get("instruction")},
            {"name": second.get("name", "02-revision") if isinstance(second, dict) else "02-revision",
             "instruction": second.get("instruction") if isinstance(second, dict) else None}]
    if not isinstance(steps, list):
        steps = []
    flags, scanned = [], 0
    for number, step in enumerate(steps, 1):
        if not isinstance(step, dict) or not isinstance(step.get("instruction"), str):
            continue
        instruction = step["instruction"]
        scanned += 1
        for category, pattern in _HINTS.items():
            for match in pattern.finditer(instruction):
                flags.append({"step": step.get("name") or f"step-{number}", "category": category,
                    "line": instruction.count("\n", 0, match.start()) + 1, "matched_text": match.group()})
    return {"schema": "arena-pipeline/solver-brief-diagnostics/1", "private_authoring_only": True,
        "surface": "staged step instructions only; independent review must inspect all public surfaces",
        "basis": "English-language patterns requiring semantic review, not proof of a hint or leak",
        "instructions_scanned": scanned, "possible_scaffolding": flags,
        "normative_rules_must_remain_public": True, "generic_tools_and_file_access_unchanged": True,
        "writes_public_or_reference_files": False, "creates_validity_blockers": False,
        "establishes_leak_free": False, "predicts_model_failure": False}


def visibility_manifest(bundle: Path) -> dict:
    bundle = Path(bundle)
    surfaces = {}
    fixture = bundle / "environment/files"
    paths = [(path, "fixture/" + path.relative_to(fixture).as_posix())
        for path in sorted(fixture.rglob("*")) if path.is_file()]
    for pattern in ("steps/*/instruction.md", "steps/*/operating-notes.md"):
        paths.extend((path, path.relative_to(bundle).as_posix()) for path in sorted(bundle.glob(pattern)))
    environment = bundle / "environment"
    paths.extend((path, "package-layout/" + path.relative_to(environment).as_posix())
        for path in sorted(environment.rglob("*")) if path.is_file()
        and path.relative_to(environment).parts[0] != "files")
    for path, name in paths:
        checked = contained(bundle, path.relative_to(bundle).as_posix())
        if path.is_symlink() or not checked.is_file():
            raise ValueError("Solver visibility requires regular contained files")
        surfaces[name] = hashlib.sha256(checked.read_bytes()).hexdigest()
    return {"schema": "arena-pipeline/solver-visibility/1", "surfaces": surfaces,
        "scope": "public task/source surfaces plus build/interface exposure boundaries; private review only"}


def assessment_problems(bundle: Path, workspace: Path, assessment: dict | None) -> list[str]:
    if (not isinstance(assessment, dict)
            or assessment.get("schema") != "arena-pipeline/solver-autonomy-review/1"
            or assessment.get("verdict") not in ("pass", "revise")):
        return ["solver autonomy lacks a mandatory independent assessment"]
    errors = []
    if not isinstance(assessment.get("reason"), str) or len(assessment["reason"].strip()) < 80:
        errors.append("solver autonomy assessment lacks specific semantic reasoning")
    safeguards = ("requirements_preserved", "evidence_access_preserved", "native_tools_preserved")
    if any(type(assessment.get(field)) is not bool for field in safeguards):
        errors.append("solver autonomy must explicitly assess requirements, evidence access and native tools")
    rows = assessment.get("surfaces")
    if (not isinstance(rows, list) or any(not isinstance(row, dict) or not isinstance(row.get("file"), str) for row in rows)):
        return [*errors, "solver autonomy needs per-surface assessments"]
    expected = visibility_manifest(bundle)["surfaces"]
    names = [row["file"] for row in rows]
    if len(names) != len(set(names)) or set(names) != set(expected):
        errors.append("solver autonomy must cover every inventoried surface exactly once")
    classifications = ("requirements_or_evidence", "generic_environment_help", "task_specific_coaching", "answer_or_grader_leak")
    for row in rows:
        name = row["file"]
        if row.get("classification") not in classifications:
            errors.append(f"solver autonomy {name}: unknown surface classification")
        if not isinstance(row.get("reason"), str) or len(row["reason"].strip()) < 40:
            errors.append(f"solver autonomy {name}: missing specific surface reasoning")
        try:
            if name not in expected:
                raise ValueError("citation must identify an inventoried public/exposure surface")
            path = contained(workspace, name)
            if hashlib.sha256(path.read_bytes()).hexdigest() != expected[name]:
                raise ValueError("surface differs from the candidate")
            content = path.read_text()
            quote = row.get("quote")
            full_quote_needed = len(content) < 15 or not content.strip()
            if (not isinstance(quote, str) or quote not in content
                    or (full_quote_needed and quote != content)
                    or (not full_quote_needed and len(quote.strip()) < 15)):
                raise ValueError("quote absent, too short or not the complete tiny file")
        except (OSError, UnicodeError, ValueError, TypeError) as error:
            errors.append(f"invalid solver autonomy citation {name} ({error})")
    if not errors and (assessment["verdict"] == "revise"
            or any(assessment[field] is False for field in safeguards)
            or any(row["classification"] in {"task_specific_coaching", "answer_or_grader_leak"} for row in rows)):
        errors.append("unresolved review findings: solver_autonomy")
    return errors


def repair_findings(doc: dict) -> list[str]:
    assessment = doc.get("solver_autonomy")
    if not isinstance(assessment, dict):
        return []
    safeguards = ("requirements_preserved", "evidence_access_preserved", "native_tools_preserved")
    findings = []
    if assessment.get("verdict") == "revise" or any(assessment.get(field) is False for field in safeguards):
        findings.append(f"Solver autonomy: {assessment.get('reason', '')}")
    rows = assessment.get("surfaces")
    for row in rows if isinstance(rows, list) else []:
        if isinstance(row, dict) and row.get("classification") in ("task_specific_coaching", "answer_or_grader_leak"):
            findings.append(f"Solver autonomy {row.get('file')}: {row.get('reason')}")
    return findings
