"""Source-grounded matter-room planning, not imported benchmark grading."""
from __future__ import annotations

from copy import deepcopy


RESEARCH = {
    "lab": "https://github.com/harveyai/harvey-labs",
    "methodology": "https://github.com/harveyai/harvey-labs/blob/main/docs/eval-strategies.md",
    "model_comparison": "https://www.vals.ai/comparisons/anthropic_claude-fable-5-1-vs-openai_gpt-6-astra",
}

PROMPT = """
7. MATTER-ROOM / PORTFOLIO SYNTHESIS (LAB-INSPIRED, DETERMINISTIC).
Use plan_portfolio when the actual source engagement supports a multi-record
audit, reconciliation or readiness decision. Preserve that engagement; do not
turn medical, historical or unrelated requests into legal diligence puzzles.
The tool supplies a private control schedule, not a task, answer key or grader.

Bind the requested matter, legal entity, instrument and transaction before
resolving authority. A similarly named agreement or another deal's memo is not
an amendment to this matter. Two documents disagreeing does not authorize a
hidden latest-wins rule. Publish scope, executed/draft status, amendment priority,
effective time and any original-versus-projected conventions that settle a case.
Use distributed load-bearing evidence, scoped amendments, partial waivers and
genuine non-issues, not an answer-bearing normalized conclusions table.

For contract applicability, distinguish assignment from change of control,
consent from notice, mandatory repayment from a permission right, loss of
exclusivity from termination, and a double trigger from unconditional payment.
Use threshold, actor, direct/indirect ownership, survival, scope and effective-time
differences only when they actually change a public-case decision. Apply every
exception's conditions together. Resolve each affected clause under the public
record; missing evidence is not proof that a consent or waiver does not exist.
Publish a legitimate undetermined branch when the record cannot settle it.

A useful portfolio may support 8–10 distinct substantive judgment groups within
the EXISTING objective and band limits. This is a construction hypothesis, not
a new quota or validity gate. Related trigger/consent/deadline/exposure fields,
or the same judgment repeated across two steps, do not establish independence.
Keep economically distinct exposures separate; never double-count a contingent
amount simply because several rubric criteria mention it. More rows, filenames,
criteria or conjunctive grading alone cannot establish incapability.

Use bounded structured conclusions with source-derived targets through existing
reviewed expressions and assertions. Accept every legitimate equivalent, record
order and supported alternative. Do not port LAB's LLM judges, equal-weight
rubrics, private qualitative severity preferences or exact prose/citation style.
Calendar-day date_add does NOT implement business-day notice rules: use an
explicit public calendar with a supported derivation or choose a supported case;
never silently approximate the law or impose private holidays or counting rules.
External legal doctrine, contested interpretation and subjective drafting need
explicit accessible authority and independent domain review; otherwise do not
score them as a unique finite conclusion. A lawyer-reviewed benchmark is not
evidence that every public task, document or rubric is defect-free.

Control each claimed judgment with coherent source interventions, including each
load-bearing file. When shared deal facts change, recompute ALL their affected
records and preserve the others; rechecking need not change every answer. Apply
each plausible wrong policy across its whole applicable record set and both
steps, then observe its actual failures through the shipped grader. Grade all
work at the relevant step boundary; do not use another field as artificial gating.

Public LAB tasks and answer rubrics are research references, not source trace
evidence or private held-out tasks. Author new source-grounded instances; retain
provenance and all prior budgets and scores. LAB all-pass averages two judges'
binary results, unlike our deterministic native measurement. A roughly 90%
criterion rate does not imply independent errors or predict joint success.
Never infer 0.9**N or transfer 6.67%/5.42% into this pipeline. Independent
review and fresh exact-model calibration must establish genuine failures here.
"""

RECIPES = {
    "contract_applicability": {
        "focus": "Scope each instrument's trigger, exception, amendment and remaining obligation to the actual transaction",
        "distinctions": ["assignment versus change of control", "consent versus notice",
            "prepayment versus permission", "exclusivity loss versus termination", "single versus double trigger"],
    },
    "portfolio_reconciliation": {
        "focus": "Reconcile entities, periods, populations and classifications before aggregating disjoint contributions",
        "distinctions": ["gross versus net", "recurring versus exceptional", "committed versus projected",
            "original versus revised", "distinct exposure versus duplicated contribution"],
    },
    "dependency_readiness": {
        "focus": "Determine joint readiness from scoped prerequisites, outstanding obligations and permitted alternatives",
        "distinctions": ["necessary versus sufficient", "fulfilled versus waived", "conditional versus unconditional",
            "local compliance versus global feasibility", "affected versus preserved revision scope"],
    },
}

_STRING_LIST = {"type": "array", "minItems": 1, "uniqueItems": True,
    "items": {"type": "string", "minLength": 1}}

TOOL = {
    "name": "plan_portfolio",
    "description": "Private LAB-inspired matter-room planner: group related fields into substantive judgments, outline per-source controls and complete shared-input revision scopes. Reads the staged stretch profile. Writes no task, fixture, answer or grader; establishes no semantic validity, independence or measured hardness.",
    "input_schema": {"type": "object", "properties": {
        "workflow": {"type": "string", "enum": list(RECIPES)},
        "source_fit": {"type": "string", "minLength": 1},
        "records": {"type": "array", "minItems": 2, "items": {
            "type": "object", "properties": {"id": {"type": "string", "minLength": 1},
                "decision": {"type": "string", "minLength": 1}, "sources": deepcopy(_STRING_LIST),
                "checks": deepcopy(_STRING_LIST), "discriminators": deepcopy(_STRING_LIST)},
            "required": ["id", "decision", "sources", "checks", "discriminators"], "additionalProperties": False}},
        "shared_inputs": {"type": "array", "items": {"type": "object", "properties": {
            "id": {"type": "string", "minLength": 1}, "sources": deepcopy(_STRING_LIST),
            "records": deepcopy(_STRING_LIST), "public_convention": {"type": "string", "minLength": 1}},
            "required": ["id", "sources", "records", "public_convention"], "additionalProperties": False}},
        "wrong_policies": {"type": "array", "items": {"type": "object", "properties": {
            "id": {"type": "string", "minLength": 1}, "records": deepcopy(_STRING_LIST)},
            "required": ["id", "records"], "additionalProperties": False}}},
        "required": ["workflow", "source_fit", "records"], "additionalProperties": False},
}


def _names(value, field):
    if (not isinstance(value, list) or not value
            or any(not isinstance(name, str) or not name.strip() for name in value)
            or len({name.strip().casefold() for name in value}) != len(value)):
        raise ValueError(f"{field} needs distinct nonempty names")
    return list(value)


def _entries(value, required, field):
    if not isinstance(value, list):
        raise ValueError(f"{field} must be a list")
    if any(not isinstance(entry, dict) or set(entry) != required for entry in value):
        raise ValueError(f"{field} entries need exactly {sorted(required)}; no reference answers")
    if value:
        _names([entry["id"] for entry in value], field + ".id")
    return value


def plan_portfolio(workflow: str, source_fit: str, records: list[dict],
                   shared_inputs: list[dict] | None = None, wrong_policies: list[dict] | None = None) -> dict:
    if not isinstance(workflow, str) or workflow not in RECIPES:
        raise ValueError("Choose a supported portfolio workflow")
    if not isinstance(source_fit, str) or not source_fit.strip():
        raise ValueError("Explain how this workflow preserves the actual source engagement")
    records = _entries(records, {"id", "decision", "sources", "checks", "discriminators"}, "records")
    if len(records) < 2:
        raise ValueError("A portfolio needs at least two declared records")
    groups, check_owners, decision_spellings = {}, {}, {}
    for record in records:
        decision = record["decision"]
        _names([decision], "record.decision")
        canonical = decision.strip().casefold()
        if canonical in decision_spellings and decision_spellings[canonical] != decision:
            raise ValueError("Use one unambiguous spelling for each decision group")
        decision_spellings[canonical] = decision
        for field in ("sources", "checks", "discriminators"):
            _names(record[field], "record." + field)
        group = groups.setdefault(decision, {"records": [], "sources": set(), "checks": set()})
        group["records"].append(record["id"])
        group["sources"].update(record["sources"])
        group["checks"].update(record["checks"])
        for check in record["checks"]:
            key = check.strip().casefold()
            if key in check_owners and check_owners[key] != decision:
                raise ValueError("One semantic check cannot establish two independent decisions")
            check_owners[key] = decision
    record_ids = {record["id"] for record in records}
    shared_inputs = _entries([] if shared_inputs is None else shared_inputs,
        {"id", "sources", "records", "public_convention"}, "shared_inputs")
    wrong_policies = _entries([] if wrong_policies is None else wrong_policies,
        {"id", "records"}, "wrong_policies")
    for entry in [*shared_inputs, *wrong_policies]:
        selected = _names(entry["records"], "affected records")
        if set(selected) - record_ids:
            raise ValueError("Shared inputs and wrong policies must name existing records")
    for entry in shared_inputs:
        _names(entry["sources"], "shared input sources")
        if not isinstance(entry["public_convention"], str) or not entry["public_convention"].strip():
            raise ValueError("A shared input needs an explicit public meaning or precedence convention")
        affected = [record for record in records if record["id"] in entry["records"]]
        if any(set(entry["sources"]) - set(record["sources"]) for record in affected):
            raise ValueError("Shared-input sources must be load-bearing sources of their affected records")
    return {"schema": "arena-pipeline/portfolio-outline/1", "workflow": workflow,
        "source_fit": source_fit, "recipe": deepcopy(RECIPES[workflow]),
        "record_ids": [record["id"] for record in records], "declared_decision_groups": len(groups),
        "decision_groups": [{"id": decision, "records": list(group["records"]),
            "checks": sorted(group["checks"]), "sources": sorted(group["sources"])} for decision, group in groups.items()],
        "source_control_outlines": [{"decision": decision, "source": source,
            "recheck_records": list(group["records"]), "must_independently_rederive_whole_answer": True,
            "isolate_decision_or_declare_shared_cascade": True,
            "preserve_only_causally_unaffected_decisions": True} for decision, group in groups.items() for source in sorted(group["sources"])],
        "record_near_miss_outlines": [{"record": record["id"], "decision": record["decision"],
            "discriminators_requiring_public_witnesses": list(record["discriminators"]),
            "promotion_and_invariance_controls_required": True} for record in records],
        "shared_input_controls": [{"id": entry["id"], "sources": list(entry["sources"]),
            "recompute_records": sorted(entry["records"]), "preserve_records": sorted(record_ids - set(entry["records"])),
            "answers_may_remain_unchanged": True, "one_upstream_error_is_one_failure_cause": True} for entry in shared_inputs],
        "wrong_policy_controls": [{"id": entry["id"], "apply_consistently_to_records": list(entry["records"]),
            "apply_at_every_affected_step": True, "observed_failures_required": True} for entry in wrong_policies],
        "grading_outline": {"existing_assertions_only": True, "source_derived_targets_only": True,
            "preserve_multiplicity": True, "accept_legitimate_orderings_and_alternatives": True,
            "no_per_field_independence_claim": True, "no_llm_judge": True, "unchanged_objective_band_limits": True},
        "private_authoring_only": True, "source_fit_established": False, "independence_established": False,
        "predicts_model_failure": False, "creates_validity_blockers": False,
        "adds_or_refunds_attempts": False, "writes_public_or_reference_files": False}


def construction_diagnostics(spec: dict) -> dict:
    quality = spec.get("quality") if isinstance(spec.get("quality"), dict) else {}
    declared = quality.get("portfolio_plan")
    result = {"declared": declared is not None, "research": RESEARCH,
        "basis": "private planning declarations only; not semantic validity or native difficulty",
        "predicts_model_failure": False, "creates_validity_blockers": False}
    if declared is None:
        return result
    try:
        if not isinstance(declared, dict):
            raise ValueError("portfolio_plan must be an object")
        outline = plan_portfolio(**declared)
    except (TypeError, ValueError) as error:
        return {**result, "planning_advisory": str(error)}
    declared_decisions = quality.get("decisions")
    decisions = {entry["id"]: {check for check in entry["checks"] if isinstance(check, str)}
        for entry in (declared_decisions if isinstance(declared_decisions, list) else [])
        if isinstance(entry, dict) and isinstance(entry.get("id"), str) and isinstance(entry.get("checks"), list)}
    linked = all(group["id"] in decisions and set(group["checks"]) <= decisions[group["id"]]
        for group in outline["decision_groups"])
    return {**result, "workflow": outline["workflow"], "declared_records": len(outline["record_ids"]),
        "declared_decision_groups": outline["declared_decision_groups"], "checks_linked_to_declared_decisions": linked,
        "declared_shared_inputs": len(outline["shared_input_controls"]),
        "declared_wrong_policies": len(outline["wrong_policy_controls"]), "independence_established": False}
