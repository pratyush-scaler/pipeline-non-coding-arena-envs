"""Research-informed construction aids, never evidence of model incapability."""
from __future__ import annotations

import json

from .portfolio import PROMPT as PORTFOLIO_PROMPT, construction_diagnostics as portfolio_diagnostics
from .brief import PROMPT as BRIEF_PROMPT, construction_diagnostics as brief_diagnostics


RESEARCH = {
    "global_planning": "https://arxiv.org/abs/2601.18137",
    "compositional_state": "https://arxiv.org/abs/2506.07982",
    "semantic_retrieval": "https://arxiv.org/abs/2502.05167",
    "inverse_identification": "https://openai.com/index/browsecomp/",
    "offline_hard_negatives": "https://aclanthology.org/2026.acl-long.1023/",
    "reasoning_retrieval": "https://arxiv.org/abs/2407.12883",
    "stateful_applicability": "https://arxiv.org/abs/2408.04682",
}

PROMPT = """
RESEARCH-INFORMED CHALLENGE CONSTRUCTION, NOT A HARDNESS GUARANTEE.
Use this for initial design and explicitly permitted hardness redesigns. A
REPAIR-ONLY brief takes precedence: fix its defects without adding new traps.
Assume BOTH exact native models can read all evidence, write scripts, solve
joins and arithmetic, and verify their work. Older benchmark failures are
hypotheses to test, not evidence that Fable 5.1 or GPT-6 Astra will fail.

1. GLOBAL FEASIBILITY BEFORE LOCAL ATTRACTIVENESS. Where the source supports
planning, build interacting resource, eligibility, timing and compatibility
constraints. A locally best choice should consume something another legitimate
choice needs, or make another requirement infeasible. Construct a feasible
solution first, independently verify the optimum or feasibility certificate,
then derive plausible greedy and independent-row mistakes. Do not create an
unsatisfiable task, invent unrelated constraints, or require a private solver
path. Accept every valid plan and every optimal tie allowed by the public task.

2. NEAR-MISS LATTICE, NOT MORE RANDOM DISTRACTORS. Start from the actual public
conjunction that makes a record eligible. Build coherent alternatives that
satisfy all but ONE different decisive criterion, and selected interacting
two-criterion misses. Use equivalent professional terms rather than repeating
the query's literal labels everywhere. Each candidate needs accessible evidence
that uniquely settles EVERY criterion. A synonymous valid candidate must still
pass. Never infer a non-match from missing evidence without a public null rule.
There is no per-family trap-count quota. Additional traps must contribute a
distinct justified discriminator or interaction, not rename the same mistake.

3. INVERSE IDENTIFICATION WITH AN ACCESSIBLE WITNESS. Ask which artifact,
combination or minimal repair satisfies a distributed set of requirements,
rather than copying an already identified winner's properties. The answer may
be compact while finding it needs evidence reconciliation. Independently verify
all candidates, including multiple matches and no-match outcomes. Do not hide
the evidence, require external facts, or put a labelled answer map in the pack.

4. STATE AND NON-MONOTONIC REVISION. Where professionally justified, combine
effective-time precedence, exceptions and shared state. A new fact may change
eligibility, invalidate an earlier allocation, or make an old optimum infeasible.
Use the existing two substantive steps; recompute the exact causal descendants
and preserve unrelated decisions. Intermediate numerical fields are not new
independent bottlenecks. Publish original versus revised field semantics, event
order, cutoff, rounding, tie, uncertainty and stop rules before they are needed.

5. ABLATE THE CLAIMED DIFFICULTY. Reuse coherent source_cases and source_invariants:
promote each important near-miss by changing its failing criterion; strengthen
an inapplicable decoy without changing the answer; isolate each independent
judgment; revise an upstream premise and check the complete downstream cascade.
Apply each named wrong policy consistently across all records and steps. Honest
all-evidence retrieval and computation baselines may succeed; retain that result.
Neither hand-written wrong outputs nor linked controls prove model temptation.

More source-supported candidates or documents are permitted within provenance,
privacy, source-fidelity and scenario-byte budgets. Arbitrary padding, secret
rules, answer ambiguity, extra formatting precision, safety refusals, unavailable
tools and time/turn restrictions are NOT hardening. A trap count, DAG depth or
construction profile is NEVER a pass@1 prediction or a release veto. Preserve
all prior attempts and scores; only fresh native measurement of a validated
revision establishes whether either exact model genuinely fails it.
Removing answer-side commentary never licenses removing normative authority,
field meanings, effective-time rules or original-versus-projected conventions.
A named governing document is not a leak when the public contract requires it.

PRIVATE PLANNING TOOL: plan_challenge constructs one-criterion near-misses,
explicitly selected interacting misses, promotion/invariance control outlines
and selective revision recomputation scopes. Use it where the source supports
these mechanisms, before committing scenario data. It does NOT supply evidence,
expected answers or model-failure predictions. Populate real public witnesses
and independently derive executable controls. A causal descendant may require
recomputation without its answer changing; never fabricate changes or new
independent bottlenecks just to fill the outline. The tool writes no fixture or
reference files and never adds a repair, hardening attempt or validity gate.

6. SUBSTANTIVE STRETCH CHECKS, NOT A LABEL CHANGE. Use the staged draft's stretch
capacity and source-linked recipes returned by plan_challenge or check_draft.
Strengthen a measured, fully passing stretch check first; add new stretch
objectives only where the existing band policy has room and the source supports
an additional substantive demand. Test joint applicability, globally feasible
choices, scoped exception precedence, complete corrective repair or selective
non-monotonic revision. Require minimum-change repair only when that objective
is actually public and professionally justified. Use existing reviewed assertions
such as optimal_subset or optimal_path only for engagements they genuinely fit;
accept every legitimate feasible/optimal alternative and tie. Each objective
needs its own public rule, coherent source intervention and schema-valid wrong
reading. Do not count descendant fields as new independent judgments or add
grader gating, a hidden bonus requirement, exact prose or formatting penalties.
The stretch label is a construction hypothesis until both exact models are
measured; more checks or weight alone do not demonstrate greater incapability.
"""

PROMPT += PORTFOLIO_PROMPT
PROMPT += BRIEF_PROMPT


TOOL = {
    "name": "plan_challenge",
    "description": "Private construction aid: outline criterion-specific and interacting near-misses, promotion/invariance controls and selective revision recomputation. Also reads the staged draft's stretch capacity and source-linked stretch recipes. Supplies no public evidence, reference answer or hardness certificate; writes nothing. Downstream validation remains mandatory.",
    "input_schema": {"type": "object", "properties": {
        "criteria": {"type": "array", "minItems": 2, "uniqueItems": True, "items": {"type": "string", "minLength": 1}},
        "joint_misses": {"type": "array", "items": {"type": "array", "minItems": 2, "uniqueItems": True,
            "items": {"type": "string", "minLength": 1}}, "description": "Explicit criterion combinations with genuine interactions; do not generate an exponential set of padding cases."},
        "decision_dependencies": {"type": "object", "additionalProperties": {"type": "array", "uniqueItems": True,
            "items": {"type": "string", "minLength": 1}}},
        "changed_decisions": {"type": "array", "uniqueItems": True, "items": {"type": "string", "minLength": 1}}},
        "required": ["criteria"], "additionalProperties": False},
}


def near_miss_lattice(criteria: list[str], joint_misses: list[list[str]] | None = None) -> list[dict]:
    """Private collision outline; the author must supply real public witnesses."""
    if (not isinstance(criteria, list) or len(criteria) < 2
            or any(not isinstance(criterion, str) or not criterion.strip() for criterion in criteria)
            or len(set(criteria)) != len(criteria)):
        raise ValueError("A collision outline needs distinct nonempty public criteria")
    rows = [{"id": "full-match", "satisfies": list(criteria), "violates": []}, *[
        {"id": f"miss-{criterion}", "satisfies": [other for other in criteria if other != criterion],
         "violates": [criterion]} for criterion in criteria]]
    if joint_misses is None:
        return rows
    if not isinstance(joint_misses, list):
        raise ValueError("Interacting misses must be explicit lists of public criteria")
    seen = set()
    for missed in joint_misses:
        if (not isinstance(missed, list) or len(missed) < 2
                or any(not isinstance(criterion, str) or criterion not in criteria for criterion in missed)
                or len(set(missed)) != len(missed)):
            raise ValueError("Each interacting miss needs at least two distinct existing criteria")
        selected = frozenset(missed)
        if selected in seen:
            raise ValueError("Repeated interacting misses are not distinct challenges")
        seen.add(selected)
        rows.append({"id": f"joint-miss-{len(seen)}",
            "satisfies": [criterion for criterion in criteria if criterion not in selected],
            "violates": [criterion for criterion in criteria if criterion in selected]})
    return rows


def _records(value):
    return [record for record in value if isinstance(record, dict)] if isinstance(value, list) else []


def _identifiers(value):
    return {identifier for identifier in value if isinstance(identifier, str)} if isinstance(value, list) else set()


def _dependency_depth(dependencies):
    if not isinstance(dependencies, dict) or any(not isinstance(decision, str) or not decision.strip()
            for decision in dependencies) or any(not isinstance(upstream, list)
            or any(not isinstance(parent, str) or parent not in dependencies for parent in upstream)
            or len(set(upstream)) != len(upstream)
            for upstream in dependencies.values()):
        return None
    pending = {decision: set(upstream) for decision, upstream in dependencies.items()}
    children = {decision: set() for decision in dependencies}
    for child, upstream in pending.items():
        for parent in upstream:
            children[parent].add(child)
    ready = [decision for decision, upstream in pending.items() if not upstream]
    depths, visited = {decision: 0 for decision in dependencies}, 0
    while ready:
        decision = ready.pop()
        visited += 1
        for child in children[decision]:
            depths[child] = max(depths[child], depths[decision] + 1)
            pending[child].remove(decision)
            if not pending[child]:
                ready.append(child)
    return max(depths.values(), default=0) if visited == len(dependencies) else None


def revision_cascade_outline(dependencies: dict, changed_decisions: list[str]) -> dict:
    depth = _dependency_depth(dependencies)
    if depth is None:
        raise ValueError("Revision planning needs an acyclic graph of distinct existing decision IDs")
    if (not isinstance(changed_decisions, list)
            or any(not isinstance(decision, str) or decision not in dependencies for decision in changed_decisions)
            or len(set(changed_decisions)) != len(changed_decisions)):
        raise ValueError("Changed decisions must name distinct existing decision IDs")
    children = {decision: set() for decision in dependencies}
    for child, upstream in dependencies.items():
        for parent in upstream:
            children[parent].add(child)
    recompute, pending = set(changed_decisions), list(changed_decisions)
    while pending:
        decision = pending.pop()
        for child in children[decision] - recompute:
            recompute.add(child)
            pending.append(child)
    return {"changed_inputs": sorted(changed_decisions), "recompute_decisions": sorted(recompute),
        "preserve_decisions": sorted(set(dependencies) - recompute), "declared_causal_depth": depth,
        "descendant_answers_may_remain_unchanged": True,
        "basis": "Declared causal scope only; independently rederive the actual changed answers from coherent public evidence"}


def plan_challenge(criteria: list[str], joint_misses: list[list[str]] | None = None,
                   decision_dependencies: dict | None = None, changed_decisions: list[str] | None = None) -> dict:
    candidates = near_miss_lattice(criteria, joint_misses)
    if decision_dependencies is None and changed_decisions is not None:
        raise ValueError("Changed decisions need a declared dependency graph")
    cascade = (revision_cascade_outline(decision_dependencies, changed_decisions if changed_decisions is not None else [])
               if decision_dependencies is not None else None)
    return {"schema": "arena-pipeline/challenge-outline/1", "private_authoring_only": True,
        "candidates": candidates, "revision_cascade": cascade,
        "control_outlines": [{"candidate": candidate["id"], "promotion_restore_criteria": list(candidate["violates"]),
            "promotion_requires_independently_rederived_answer": True,
            "invariance": "Strengthen nondiscriminating attributes while retaining a genuine exclusion; verify that the whole answer is unchanged",
            "public_witnesses_required_for_every_criterion": list(criteria)} for candidate in candidates if candidate["violates"]],
        "creates_validity_blockers": False, "predicts_model_failure": False,
        "adds_or_refunds_attempts": False, "writes_public_or_reference_files": False}


_STRETCH_RECIPES = {
    "authority_time": ("scoped_exception_precedence", "Reconcile authority, scope, effective time and applicable exceptions under explicit public conventions"),
    "semantic_collision": ("joint_applicability", "Identify every legitimate match across interacting public criteria while rejecting coherent near-misses"),
    "coupled_decisions": ("global_consistency", "Verify source-supported shared feasibility or optimality rather than independent local choices; accept all valid alternatives and optimal ties"),
    "artifact_repair": ("complete_corrective_repair", "Correct all genuine errors while preserving valid work; impose minimum-change optimality only when the public professional goal calls for it"),
    "revision_cascade": ("selective_nonmonotonic_revision", "Recheck the full causal downstream scope after a legitimate revision and preserve unrelated decisions; rechecking need not change every answer"),
}


def stretch_check_outlines(spec: dict, measured: dict | None = None) -> dict:
    from .quality import BAND_LIMITS
    minimum, maximum = BAND_LIMITS["stretch"]
    checks = [check for check in _records(spec.get("checks")) if check.get("kind") == "objective"]
    stretch = [check for check in checks if check.get("band") == "stretch"]
    stretch_ids = {check["id"] for check in stretch if isinstance(check.get("id"), str)}
    free_ids = {check["id"] for check in _records((measured or {}).get("floor")) if isinstance(check.get("id"), str)}
    quality = spec.get("quality") if isinstance(spec.get("quality"), dict) else {}
    plan = quality.get("capability_plan") if isinstance(quality.get("capability_plan"), dict) else {}
    decisions = {decision["id"]: _identifiers(decision.get("checks")) for decision in _records(quality.get("decisions"))
        if isinstance(decision.get("id"), str) and decision["id"].strip()}
    recipes = []
    for mechanism in _records(plan.get("mechanisms")):
        kind = mechanism.get("kind")
        selected = _identifiers(mechanism.get("decisions")) & set(decisions)
        if not isinstance(kind, str) or kind not in _STRETCH_RECIPES or not selected:
            continue
        recipe, demand = _STRETCH_RECIPES[kind]
        recipes.append({"mechanism": mechanism.get("id"), "recipe": recipe,
            "decisions": sorted(selected), "existing_checks": sorted(set().union(*(decisions[decision] for decision in selected))),
            "demand": demand, "declared_source_cases": sorted(_identifiers(mechanism.get("source_cases"))),
            "required_controls": ["Published source-grounded rule and all legitimate answers",
                "Coherent intervention with independently rederived answer",
                "Schema-valid sustained wrong reading with exact observed failures",
                "Whole-answer invariance for irrelevant evidence changes"]})
    return {"basis": "Declared construction and retained aggregate evidence only; recipes are not ready-to-grade checks",
        "band": "stretch", "minimum": minimum, "maximum": maximum, "declared_count": len(stretch),
        "additional_slots": max(0, maximum - len(stretch)), "fully_passing_stretch_checks": sorted(stretch_ids & free_ids),
        "when_full": "Strengthen existing eligible checks; do not reset budgets, relabel solved objectives or exceed the band policy",
        "recipes": recipes, "requires_public_requirement_and_executed_controls": True,
        "one_causal_mistake_is_not_multiple_independent_failures": True,
        "predicts_model_failure": False, "creates_validity_blockers": False}


def construction_diagnostics(spec: dict, measured: dict | None = None) -> dict:
    """Summarize declarations and model aggregates, excluding answers/trajectories."""
    quality = spec.get("quality") if isinstance(spec.get("quality"), dict) else {}
    plan = quality.get("capability_plan") if isinstance(quality.get("capability_plan"), dict) else {}
    dependencies = plan.get("decision_dependencies")
    dependencies = dependencies if isinstance(dependencies, dict) else {}
    collisions, advisories = [], []
    for collision in _records(plan.get("collisions")):
        criteria = {entry["id"] for entry in _records(collision.get("predicates"))
            if isinstance(entry.get("id"), str) and entry["id"].strip()}
        tested, full_matches, unresolved, interactions = set(), 0, 0, set()
        for candidate in _records(collision.get("candidates")):
            satisfied, violated = _identifiers(candidate.get("satisfies")), _identifiers(candidate.get("violates"))
            if not criteria or satisfied & violated or satisfied | violated != criteria:
                unresolved += 1
            elif not violated:
                full_matches += 1
            elif len(violated) == 1:
                tested.update(violated)
            else:
                interactions.add(tuple(sorted(violated)))
        missing = sorted(criteria - tested)
        collisions.append({"id": collision.get("id"), "criteria": sorted(criteria),
            "full_matches_declared": full_matches, "one_criterion_near_misses": sorted(tested),
            "criteria_without_a_one_criterion_near_miss": missing, "unresolved_candidates": unresolved,
            "interacting_near_misses_declared": [list(interaction) for interaction in sorted(interactions)],
            "private_outline_needs_public_witnesses": near_miss_lattice(sorted(criteria)) if len(criteria) >= 2 else []})
        if missing:
            advisories.append(f"Collision {collision.get('id')}: consider coherent near-misses isolating {missing}; unrelated decoys do not exercise these discriminators.")
    baseline_successes = [entry.get("id") for entry in _records(plan.get("tool_baselines"))
        if isinstance(entry.get("submission"), dict) and entry["submission"] and entry.get("fails") == []]
    if baseline_successes:
        advisories.append("Complete declared tool baselines succeed. Preserve their outputs and strengthen source-supported judgments rather than falsifying baseline failures.")
    depth = _dependency_depth(dependencies)
    if not dependencies:
        advisories.append("No causal decision graph is declared; assess distributed identification and genuine global coupling instead of adding answer fields.")
    elif depth == 0:
        advisories.append("All declared decisions are independent. Consider source-supported shared constraints or a selective revision cascade; depth alone is not difficulty.")
    aggregates = {}
    by_model = (measured or {}).get("by_model")
    for model, record in (by_model if isinstance(by_model, dict) else {}).items():
        if not isinstance(record, dict):
            continue
        diagnostic = record.get("capability_difficulty")
        diagnostic = diagnostic if isinstance(diagnostic, dict) else {}
        aggregates[model] = {"episodes_valid": record.get("episodes_valid"),
            "official_pass_at_1": record.get("pass_at_1"),
            "capability_adjusted_pass_at_1": diagnostic.get("capability_adjusted_pass_at_1")}
    saturated = [model for model, record in aggregates.items()
        if record["official_pass_at_1"] == 1 and record["capability_adjusted_pass_at_1"] == 1
        and isinstance(record["episodes_valid"], int) and record["episodes_valid"] >= 5]
    if saturated:
        advisories.append(f"Retained aggregate screens are saturated on {sorted(saturated)}. Do not multiply weights or repeat solved trap families; change the substantive search or interaction structure within the permitted redesign.")
    return {"schema": "arena-pipeline/challenge-diagnostics/1", "basis": "declared construction and aggregate evidence only; not semantic proof or measured hardness",
        "research": RESEARCH, "declared_decisions": len(_records(quality.get("decisions"))),
        "declared_causal_depth": depth, "collisions": collisions,
        "declared_couplings": len(_records(plan.get("couplings"))),
        "successful_declared_tool_baselines": baseline_successes, "model_aggregates": aggregates,
        "stretch_checks": stretch_check_outlines(spec, measured),
        "portfolio": portfolio_diagnostics(spec),
        "solver_brief": brief_diagnostics(spec),
        "difficulty_advisories": advisories, "creates_validity_blockers": False,
        "predicts_model_failure": False, "adds_or_refunds_attempts": False}


def redesign_brief(spec: dict, measured: dict | None = None) -> str:
    return PROMPT + "\nPRIVATE CONSTRUCTION DIAGNOSTICS:\n" + json.dumps(
        construction_diagnostics(spec, measured), ensure_ascii=False, sort_keys=True)
