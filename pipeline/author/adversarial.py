"""First-draft stress designs, bound to executable controls and public evidence.

These construction requirements are not measurements of model difficulty.
"""
from __future__ import annotations

from pathlib import Path

from .contracts import compile_steps, contained
from .step_files import withheld_from


PROMPT = """
FIRST-DRAFT ADVERSARIAL DESIGN (capability_plan version:2).
Do this before committing the scenario, not after observing solver failures.
Retained version:1 drafts may be repaired without upgrading or resetting budgets.
Keep the existing mechanisms and add the following private construction records:

decision_dependencies: {decision_id:[immediate upstream decision IDs]}.
Include every semantic decision; use [] for an independent input judgment.
This is a causal DAG, not the grader's requires graph. A downstream calculation,
date or total is NOT a new semantic bottleneck. Decisions may share sources.
bottlenecks: [{decision,source_case,reason}]. Name at least four distinct core
professional judgments with DISTINCT intervention cases. Each case changes that
judgment and optionally its causal descendants, but no unrelated or upstream
decision. Explain the NEW semantic judgment, not another output of a recurrence.
The complete independently corrected answer must preserve all other decisions.
The controller executes the stale answer on EVERY semantic check and verifies
the exact declared change set. Do not invent independence by renaming fields.

collisions: [{id,trap,decision,
  predicates:[{id,rule_sources:[{file,quote}]}],
  candidates:[{id,evidence:[{file,quote}],satisfies:[predicate IDs],
               violates:[predicate IDs]}],
  counterexample,source_case,invariant_case}].
Construct at least one source-supported, joint-applicability collision with
three or more REAL public criteria: e.g. same entity and metric but different
scope/effective date/authorization, or same treatment but a different exception.
Every candidate classifies ALL criteria; list at least one full match and two
plausible partial matches with DIFFERENT violated-criterion sets. Accept every
full match if the professional question permits multiple answers. Near-misses
must be substantive evidence, never instructions addressed to the solver.
Quote the public criterion and each candidate's actual evidence exactly.
counterexample is a complete schema-valid wrong reading in quality.counterexamples;
source_case is a coherent quality.source_cases control that changes applicability
and its answer; invariant_case names quality.source_invariants that strengthens
an INAPPLICABLE decoy (e.g. newer date or another non-authoritative endorsement)
while leaving the ENTIRE correct answer unchanged. Preserve every authoritative
copy and the public precedence rule. A privately ignored contradiction is invalid.
Do not annotate public files with the private matrix, winners, error locations
or words like 'trap'/'decoy'. Disclose invented context, not the answer.

couplings: [{id,decisions:[IDs],source_case,counterexample,
             rule_sources:[{file,quote}]}].
At least one genuine coupling must span two professional judgments: eligibility
changes a shared allocation, recognition changes a conserved reconciliation,
or a scoped revision invalidates downstream recommendations but preserves other
work. Its one coherent intervention must change BOTH decisions, and its one
sustained wrong reading must fail BOTH. Editing two unrelated inputs is not
coupling. Repeating a single balance recurrence across many fields is not coupling
of independent judgments. A local/greedy answer must genuinely lose to a globally
feasible one under public constraints; accept all valid alternatives and ties.
Use supported reviewed graders, never private executable code or a fixed private
solution path. Plain arithmetic may be necessary but cannot supply four judgments.

tool_baselines: [{id,kind:'retrieval'|'computation',method,
                  submission:{output_file:complete_JSON_value},fails:[objective IDs]}].
Provide both an honest retrieval procedure and an honest computation procedure,
with their COMPLETE outputs at every step. Retrieval inspects ALL public files
and discriminators; computation gets correct parsed data and arithmetic.
Apply every available public rule, including exceptions and revised premises.
The fails list records the actual failed objectives and may be EMPTY: a competent
baseline is ALLOWED to solve the task. Never invent a limitation, withhold a rule
or force a wrong answer to satisfy a construction requirement. A successful
baseline is a difficulty advisory, not a validity defect or a submission veto.
Strengthen supported professional judgments when possible, but retain the honest
control and submit the candidate for independent validation and calibration.
Legacy counterexample links remain supported; their named procedures must still
actually produce the linked outputs. Wrong-policy ablations belong in shortcut
counterexamples, not under falsely competent baseline labels. Executed outputs
do not establish that the claimed method is honest: independent review audits
that claim. Neither procedure is a native model measurement or proof of incapability.

Use varied, interacting mistakes rather than more filenames, rows, weights or
chains. All rules, rounding, boundaries, uncertainty and valid alternatives stay
public at the step that uses them. Confusing evidence is allowed; an ambiguous
correct answer, hidden convention or arbitrary output wording is not.
"""


def _records(value, where, errors):
    if not isinstance(value, list):
        errors.append(f"{where}: expected a list")
        return {}
    records = {}
    for entry in value:
        identifier = entry.get("id") if isinstance(entry, dict) else None
        if not isinstance(identifier, str) or not identifier.strip() or identifier in records:
            errors.append(f"{where}: entries need distinct nonempty ids")
        else:
            records[identifier] = entry
    return records


def _references(value, allowed, where, errors, minimum=1):
    if (not isinstance(value, list) or len(value) < minimum
            or any(not isinstance(item, str) or item not in allowed for item in value)
            or len(set(value)) != len(value)):
        errors.append(f"{where}: name at least {minimum} distinct existing ids")
        return set()
    return set(value)


def _text(value, where, errors):
    if not isinstance(value, str) or len(value.strip()) < 40:
        errors.append(f"{where}: explain this substantive judgment or procedure")


def _ids(value):
    return {item for item in value if isinstance(item, str)} if isinstance(value, list) else set()


def _witnesses(value, spec, bundle, checks, where, errors):
    if not isinstance(value, list) or not value:
        errors.append(f"{where}: supply exact public file/quote witnesses")
        return
    unavailable = set()
    if bundle is not None:
        try:
            order = [step["name"] for step in compile_steps(spec)]
            for check in checks:
                unavailable.update(withheld_from(spec, check.get("step"), order))
        except (KeyError, TypeError, ValueError) as exc:
            errors.append(f"{where}: cannot establish step availability: {exc}")
    seen = set()
    for witness in value:
        if (not isinstance(witness, dict) or not isinstance(witness.get("file"), str)
                or not isinstance(witness.get("quote"), str) or len(witness["quote"].strip()) < 15):
            errors.append(f"{where}: witnesses need a fixture file and verbatim quote of at least 15 characters")
            continue
        key = (witness["file"], witness["quote"])
        if key in seen:
            errors.append(f"{where}: duplicate evidence witness")
        seen.add(key)
        if bundle is None:
            continue
        try:
            fixture = bundle / "environment/files"
            document = contained(fixture, witness["file"])
            relative = document.relative_to(fixture.resolve()).as_posix()
            if relative in unavailable:
                errors.append(f"{where}: {relative!r} is unavailable at an affected step")
            elif witness["quote"] not in document.read_text():
                errors.append(f"{where}: quote is not verbatim in {relative!r}")
        except (OSError, ValueError, UnicodeError) as exc:
            errors.append(f"{where}: public evidence is not readable: {exc}")


def problems(spec: dict, bundle: Path | None = None) -> list[str]:
    """Validate a version-2 design; semantic truth still needs independent review."""
    errors = []
    quality = spec.get("quality", {})
    plan = quality.get("capability_plan", {})
    prefix = "quality.capability_plan"
    decisions = _records(quality.get("decisions"), "quality.decisions", errors)
    controls = _records(quality.get("source_cases"), "quality.source_cases", errors)
    invariants = _records(quality.get("source_invariants"), "quality.source_invariants", errors)
    examples = _records(quality.get("counterexamples"), "quality.counterexamples", errors)
    traps = _records(spec.get("traps"), "traps", errors)
    checks = {check["id"]: check for check in spec.get("checks", [])
              if isinstance(check, dict) and isinstance(check.get("id"), str)}
    owners = {}
    semantic = _ids(quality.get("semantic_checks")) & set(checks)
    for identifier, decision in decisions.items():
        for check in _references(decision.get("checks"), semantic,
                                 f"decision {identifier}.checks", errors):
            if check in owners:
                errors.append(f"decision {identifier}: repeated check ownership {check!r}")
            owners[check] = identifier

    graph = plan.get("decision_dependencies")
    if not isinstance(graph, dict) or set(graph) != set(decisions):
        errors.append(f"{prefix}.decision_dependencies: include every decision exactly once")
        graph = {}
    parents = {identifier: _references(value, decisions,
               f"{prefix}.decision_dependencies[{identifier}]", errors, minimum=0)
               for identifier, value in graph.items()}
    descendants = {identifier: {identifier} for identifier in decisions}
    for unused in range(len(decisions)):
        for child, upstream in parents.items():
            for parent in upstream:
                descendants[parent].update(descendants[child])
    if any(identifier in descendants[child] for child, upstream in parents.items() for identifier in upstream):
        errors.append(f"{prefix}.decision_dependencies: causal graph must be acyclic")

    def affected(case):
        raw = case.get("changes") if isinstance(case, dict) else None
        return {owners[check] for check in raw if isinstance(check, str) and check in owners} if isinstance(raw, list) else set()

    def control(entry, selected, at):
        identifier = entry.get("source_case")
        case = controls.get(identifier) if isinstance(identifier, str) else None
        if case is None or not selected <= affected(case):
            errors.append(f"{at}.source_case: change every named decision with an executable source control")
        return case

    def counterexample(entry, selected, at):
        identifier = entry.get("counterexample")
        example = examples.get(identifier) if isinstance(identifier, str) else None
        failures = example.get("fails") if isinstance(example, dict) else None
        failed = {owners[check] for check in failures if isinstance(check, str) and check in owners} if isinstance(failures, list) else set()
        if (not example or not (example.get("submission") or example.get("patches"))
                or not selected <= failed):
            errors.append(f"{at}.counterexample: supply one substantive wrong reading failing every named decision")

    bottlenecks = plan.get("bottlenecks")
    if not isinstance(bottlenecks, list):
        errors.append(f"{prefix}.bottlenecks: supply independently intervenable core judgments")
        bottlenecks = []
    isolated, used_cases = set(), set()
    core = {owners[identifier] for identifier, check in checks.items()
            if check.get("kind") == "objective" and check.get("band") == "core" and identifier in owners}
    for index, entry in enumerate(bottlenecks):
        at = f"{prefix}.bottlenecks[{index}]"
        if not isinstance(entry, dict) or not isinstance(entry.get("decision"), str) or entry["decision"] not in core:
            errors.append(f"{at}: name a substantive core decision")
            continue
        selected = entry["decision"]
        case = control(entry, {selected}, at)
        identifier = entry.get("source_case")
        if selected in isolated or isinstance(identifier, str) and identifier in used_cases:
            errors.append(f"{at}: each bottleneck needs a distinct decision and intervention")
        isolated.add(selected)
        if isinstance(identifier, str):
            used_cases.add(identifier)
        if case and affected(case) - descendants[selected]:
            errors.append(f"{at}: intervention changes unrelated or upstream judgments; not independent")
        _text(entry.get("reason"), at + ".reason", errors)
    if len(isolated) < 4:
        errors.append(f"{prefix}.bottlenecks: need four distinct core judgments, not derived fields")

    collisions = _records(plan.get("collisions"), prefix + ".collisions", errors)
    if not collisions:
        errors.append(f"{prefix}.collisions: construct a source-supported joint-applicability collision")
    for identifier, entry in collisions.items():
        at = f"{prefix}.collisions[{identifier}]"
        selected = _references([entry.get("decision")], decisions, at + ".decision", errors)
        trap = traps.get(entry.get("trap")) if isinstance(entry.get("trap"), str) else None
        if not trap or not _ids(trap.get("checks")) & {check for check, owner in owners.items() if owner in selected}:
            errors.append(f"{at}.trap: link an objective-driving trap for its decision")
        applicable = [check for check, record in checks.items() if owners.get(check) in selected]
        public_checks = [checks[check] for check in applicable]
        predicates = _records(entry.get("predicates"), at + ".predicates", errors)
        if len(predicates) < 3:
            errors.append(f"{at}.predicates: need three meaningful public applicability criteria")
        for predicate in predicates.values():
            _witnesses(predicate.get("rule_sources"), spec, bundle, public_checks, at + ".predicates.rule_sources", errors)
        candidates = _records(entry.get("candidates"), at + ".candidates", errors)
        negatives, positives, evidence_sets = set(), 0, set()
        for candidate in candidates.values():
            matches = _references(candidate.get("satisfies"), predicates, at + ".satisfies", errors, minimum=0)
            misses = _references(candidate.get("violates"), predicates, at + ".violates", errors, minimum=0)
            if matches & misses or matches | misses != set(predicates):
                errors.append(f"{at}: each candidate must classify every criterion exactly once")
            if matches and misses:
                negatives.add(tuple(sorted(misses)))
            elif matches and not misses:
                positives += 1
            _witnesses(candidate.get("evidence"), spec, bundle, public_checks, at + ".candidates.evidence", errors)
            evidence = candidate.get("evidence")
            if isinstance(evidence, list) and all(isinstance(row, dict) and isinstance(row.get("file"), str)
                                                and isinstance(row.get("quote"), str) for row in evidence):
                key = tuple(sorted((row["file"], row["quote"]) for row in evidence))
                if key in evidence_sets:
                    errors.append(f"{at}: different candidates cannot reuse the same entire evidence witness")
                evidence_sets.add(key)
        if not positives or len(negatives) < 2:
            errors.append(f"{at}: need a full match and two partial matches failing different criteria")
        control(entry, selected, at)
        counterexample(entry, selected, at)
        invariant = entry.get("invariant_case")
        if not isinstance(invariant, str) or invariant not in invariants:
            errors.append(f"{at}.invariant_case: strengthen an inapplicable decoy without changing any answer")

    couplings = _records(plan.get("couplings"), prefix + ".couplings", errors)
    if not couplings:
        errors.append(f"{prefix}.couplings: exercise interacting professional judgments")
    for identifier, entry in couplings.items():
        at = f"{prefix}.couplings[{identifier}]"
        selected = _references(entry.get("decisions"), decisions, at + ".decisions", errors, minimum=2)
        control(entry, selected, at)
        counterexample(entry, selected, at)
        _witnesses(entry.get("rule_sources"), spec, bundle,
                   [checks[check] for check, owner in owners.items() if owner in selected],
                   at + ".rule_sources", errors)

    baselines = _records(plan.get("tool_baselines"), prefix + ".tool_baselines", errors)
    kinds = set()
    for identifier, entry in baselines.items():
        at = f"{prefix}.tool_baselines[{identifier}]"
        kind = entry.get("kind")
        if isinstance(kind, str) and kind in {"retrieval", "computation"}:
            kinds.add(kind)
        else:
            errors.append(f"{at}.kind: choose retrieval or computation")
        _text(entry.get("method"), at + ".method", errors)
        if "submission" in entry:
            if not isinstance(entry["submission"], dict) or not entry["submission"]:
                errors.append(f"{at}.submission: provide complete outputs for every step")
            if "counterexample" in entry or "patches" in entry:
                errors.append(f"{at}: complete baseline outputs must not also inherit a counterexample or reference patch")
            _references(entry.get("fails"), {identifier for identifier, check in checks.items()
                        if check.get("kind") == "objective"}, at + ".fails", errors, minimum=0)
            continue
        reference = entry.get("counterexample")
        example = examples.get(reference) if isinstance(reference, str) else None
        if (not example or not (example.get("submission") or example.get("patches"))
                or not _ids(example.get("fails")) & set(owners)):
            errors.append(f"{at}.counterexample: provide a schema-valid semantic wrong-answer baseline")
    if kinds != {"retrieval", "computation"}:
        errors.append(f"{prefix}.tool_baselines: challenge both competent retrieval and computation")
    return errors
