"""Evidence-linked difficulty construction; calibration establishes hardness."""
from __future__ import annotations

from collections import Counter

from .. import policy


MECHANISMS = {
    "authority_time": "Resolve authority, scope, effective time and publication time together.",
    "artifact_repair": "Diagnose and repair plausible substantive errors in a completed artifact.",
    "semantic_collision": "Distinguish partial-match evidence using the complete professional meaning.",
    "coupled_decisions": "Resolve decisions sharing eligibility, resources or conservation constraints.",
    "revision_cascade": "Propagate new evidence while preserving unaffected conclusions and artifacts.",
}
SHORTCUTS = {
    "latest_wins", "majority_agreement", "trust_summary", "single_source",
    "keyword_match", "independent_rows", "local_patch_only", "greedy_choice",
    "zero_means_absent", "add_overlaps",
}

CAPABILITY_PROMPT = f"""
CAPABILITY-FIRST CONSTRUCTION, BEFORE WRITING THE TASK.
The targets are {policy.SPEC_PRIMARY_MODEL} in Claude Code and
{policy.SPEC_SECONDARY_MODEL} in Codex, both at high effort with unrestricted
native tools. Assume they can grep every file, script joins and calculations,
and inspect the whole workspace. Do not assume vendor-specific weaknesses.
Public benchmark failures motivate constructions, not predictions about these
exact models. Only retained native calibration measures their difficulty.

Stage quality.capability_plan before the instruction and scenario supplements.
If no starting artifact survives, use initialize_scenario with an exact source
user-request witness for an F0/F1/F2 target. Its public context is labelled
synthetic and earns zero recovered-source credit; never fabricate an artifact
or a citation merely to unlock write_scenario.
Build a coherent world, then derive its decision register and independent
reference answer. Distinguish independent semantic bottlenecks from dependent
answer fields. A short balance recurrence plus threshold scans is not made
extreme by scoring its totals, dates and revisions separately. Likewise a table
already printed in the required order does not test sorting or tie-breaking.
Challenge the construction with competent retrieval and a simple scripted
baseline before finalizing it. Strengthen the professional judgments that such
tools do not settle, within the source's faithfulness allowance; do not add
irrelevant volume or hide the necessary rule. These are construction diagnostics,
not native measurements or guarantees of hardness.
Select source-supported mechanisms, not a quota of traps:
- authority_time: distinguish issuer authority, entity/scope, issued-at,
  effective-at and reporting cutoff. A newer document is sometimes applicable
  and sometimes not; the public rules uniquely settle each case.
- artifact_repair: seed plausible wrong classifications, references, allocations
  or double counts in a professional draft. Preserve correct material. A draft
  is evidence to audit, never the reference solution or a labelled error map.
- semantic_collision: construct coherent alternatives matching different subsets
  of entity, measure, jurisdiction, eligibility and time. Every alternative has
  a public discriminator; irrelevant filler and obscure filenames do not count.
- coupled_decisions: a locally attractive answer conflicts with a public shared
  constraint. Grade all valid feasible or optimal answers, not one private path.
  Use only supported reviewed assertions; do not invent executable graders.
- revision_cascade: new evidence changes an upstream professional judgment and
  dependent outputs, but not all records. Keep affected and unaffected decisions
  independently scorable. Do not conceal rules behind future-step evidence.

New quality.capability_plan records use version:2 (version:1 is retained for
existing drafts) and mechanisms:[{{id,kind,
decisions:[quality.decisions IDs],traps:[trap IDs],
shortcuts:[{{policy,counterexample:quality.counterexamples ID}}],
source_cases:[quality.source_cases IDs],tool_resistance}}]. kind is one of
{', '.join(MECHANISMS)}. policy is one of {', '.join(sorted(SHORTCUTS))}.
tool_resistance explains the semantic judgment that remains AFTER competent
retrieval and computation, not why the solver supposedly misses a file.
Each mechanism links its own substantive, schema-valid wrong answer and a
coherent source-change control affecting its decisions. Existing controls EXECUTE
those answers through the shipped grader. Cover every objective-driving trap.
Do not mislabel arbitrary corrupted outputs as implementations of a shortcut.
Propagate a sustained wrong reading through every affected step and dependent
output; if it is only a one-step mistake, say so. A local-patch counterexample
may intentionally leave dependencies unchanged, but another named policy must
not silently acquire that extra error. Source-change controls must update all
authoritative representations and dependent examples, or publish an unambiguous
revision-precedence rule; agreement of two private calculators does not make
contradictory public evidence coherent. Check that each named shortcut really
produces its linked answer under the public world's current authority and time.
The independent reviewer checks the causal claim; a linked plan alone proves
neither model temptation nor a capability limitation.

RULES AND FAILURE INTEGRITY.
All decisive evidence and conventions must be accessible at the step using
them. Give meaningful field definitions, rounding, uncertainty, tie and error
semantics. Never privately assume away an unresolved prerequisite, null policy
or missing authorization to make a task nontrivial. Respect the published stop
or uncertainty outcome, or supply an explicitly authored, source-compatible
public ruling where the faithfulness allowance permits it. Do not conflate
folders, populations or process stages without a public equivalence rule.
Publish rules in accessible documents without supplying their
application or announcing trap locations. Never exploit invalid JSON, an
unavailable package, parsing loss, hidden tests, unknown professional standards,
unnecessary output volume, refusal or an artificial time/turn limit. Failures
from those causes are defects or voids, not evidence of model incapability.
One upstream mistake is one failure cause even when several fields depend on
it. Preserve partial-credit diagnostics and independently valid alternatives.
Official pass@1 includes clean contract failures. The separate conservative
capability diagnostic treats those as successes: malformed or missing outputs
must not be the reason a task is described as capability-hard.
Vary failure and delivery patterns across the batch, not merely names or domains.

TRACE ALIGNMENT (September 28, 2026 specification).
quality.trace_alignment maps roles to {{citation:'<actual_session_prefix>::msgN',quote,
preserved,checks:[objective IDs]}}. Always provide goal and capability: quote
the actual user request and explain which goal and ability the task preserves.
Copy the actual cite returned by read_trace or list_corrections: use this
source's first eight session-ID characters (or full ID) and its real message
index, never the literal word 'session' or the placeholder above. Quotations
must be exact USER-message text, not assistant prose or feedback annotations.
For a Scenario/F2 claim also provide scenario, failure_mode and grading_criteria
with specific source evidence. A fully synthetic fixture is permitted; a byte
ratio does not establish scenario or grading alignment. Pattern/F1 additionally
requires native calibration reproducing the trace failure. Inspired/F0 is valid
when a concrete source goal and capability survive; Unrelated/F-1 is not.
These are private authoring records, never solver-visible answers. The citation
checker verifies source text; independent review verifies its claimed meaning.
"""


def _records(value, where, problems):
    if not isinstance(value, list):
        problems.append(f"{where}: expected a list")
        return {}
    records = {}
    for entry in value:
        if not isinstance(entry, dict) or not isinstance(entry.get("id"), str) or not entry["id"].strip():
            problems.append(f"{where}: every entry needs a nonempty id")
        elif entry["id"] in records:
            problems.append(f"{where}: duplicate id {entry['id']!r}")
        else:
            records[entry["id"]] = entry
    return records


def _references(entry, field, records, where, problems):
    values = entry.get(field)
    if (not isinstance(values, list) or not values
            or any(not isinstance(value, str) or value not in records for value in values)
            or len(set(values)) != len(values)):
        problems.append(f"{where}.{field}: name distinct existing {field} ids")
        return []
    return values


def _ids(value):
    return {item for item in value if isinstance(item, str)} if isinstance(value, list) else set()


def require_staged_plan(spec: dict, minimum_version: int = 1) -> None:
    """Require a concrete mechanism outline before mutating the scenario."""
    quality = spec.get("quality")
    plan = quality.get("capability_plan") if isinstance(quality, dict) else None
    if (not isinstance(plan, dict) or type(plan.get("version")) is not int
            or plan["version"] not in (1, 2) or plan["version"] < minimum_version):
        raise ValueError(f"stage quality.capability_plan with version:{minimum_version} before writing scenario data")
    mechanisms = plan.get("mechanisms")
    if (not isinstance(mechanisms, list) or not mechanisms
            or any(not isinstance(entry, dict) or not isinstance(entry.get("id"), str)
                   or not entry["id"].strip() or not isinstance(entry.get("kind"), str)
                   or entry["kind"] not in MECHANISMS for entry in mechanisms)):
        raise ValueError("stage quality.capability_plan with named, supported mechanisms before writing scenario data")


def plan_problems(spec: dict, required: bool = False, bundle=None) -> list[str]:
    """Check behavioral-control links, never infer hardness from plan structure."""
    quality = spec.get("quality") or {}
    if not isinstance(quality, dict):
        return ["quality: expected an object"]
    plan = quality.get("capability_plan")
    where = "quality.capability_plan"
    if plan is None and not required:
        return []
    if (not isinstance(plan, dict) or type(plan.get("version")) is not int
            or plan["version"] not in (1, 2)):
        return [f"{where}: provide version:1 or version:2 and evidence-linked mechanisms"]
    problems = []
    mechanisms = _records(plan.get("mechanisms"), where + ".mechanisms", problems)
    decisions = _records(quality.get("decisions"), "quality.decisions", problems)
    traps = _records(spec.get("traps"), "traps", problems)
    examples = _records(quality.get("counterexamples"), "quality.counterexamples", problems)
    controls = _records(quality.get("source_cases"), "quality.source_cases", problems)
    objectives = {check.get("id") for check in spec.get("checks", [])
                  if isinstance(check, dict) and check.get("kind") == "objective"}
    covered = set()
    if not mechanisms:
        problems.append(f"{where}: at least one grounded mechanism is required")
    for identifier, entry in mechanisms.items():
        at = f"{where}.mechanisms[{identifier}]"
        if not isinstance(entry.get("kind"), str) or entry["kind"] not in MECHANISMS:
            problems.append(f"{at}.kind: choose a supported capability mechanism")
        selected = _references(entry, "decisions", decisions, at, problems)
        named_traps = _references(entry, "traps", traps, at, problems)
        named_controls = _references(entry, "source_cases", controls, at, problems)
        checks = set().union(*(_ids(decisions[name].get("checks")) for name in selected)) & objectives
        if not checks:
            problems.append(f"{at}: its decisions must drive substantive objectives")
        for name in named_traps:
            if not _ids(traps[name].get("checks")) & checks:
                problems.append(f"{at}: trap {name!r} drives none of its decisions")
            else:
                covered.add(name)
        resistance = entry.get("tool_resistance")
        if not isinstance(resistance, str) or not resistance.strip():
            problems.append(f"{at}.tool_resistance: explain the judgment remaining after tool use")
        shortcuts = entry.get("shortcuts")
        if not isinstance(shortcuts, list) or not shortcuts:
            problems.append(f"{at}.shortcuts: link an executable substantive wrong answer")
            shortcuts = []
        for shortcut in shortcuts:
            if (not isinstance(shortcut, dict) or not isinstance(shortcut.get("policy"), str)
                    or shortcut["policy"] not in SHORTCUTS):
                problems.append(f"{at}.shortcuts: choose a supported shortcut policy")
                continue
            reference = shortcut.get("counterexample")
            example = examples.get(reference) if isinstance(reference, str) else None
            if (not example or not (example.get("submission") or example.get("patches"))
                    or not _ids(example.get("fails")) & checks):
                problems.append(f"{at}: shortcut {shortcut['policy']!r} needs a wrong answer failing its decisions")
        for name in named_controls:
            control = controls[name]
            if (not isinstance(control.get("source_patches"), list) or not control["source_patches"]
                    or not _ids(control.get("changes")) & checks):
                problems.append(f"{at}: source case {name!r} must change evidence and affect its decisions")
    missing = sorted(name for name, trap in traps.items()
                     if _ids(trap.get("checks")) & objectives and name not in covered)
    if missing:
        problems.append(f"{where}: objective-driving traps not covered: {missing}")
    if plan["version"] == 2:
        from .adversarial import problems as stress_problems
        problems.extend(stress_problems(spec, bundle))
    return problems


def signature(spec: dict) -> dict:
    """Declared construction patterns, not observed model failure attribution."""
    quality = spec.get("quality") if isinstance(spec.get("quality"), dict) else {}
    plan = quality.get("capability_plan")
    plan = plan if isinstance(plan, dict) else {}
    mechanisms = plan.get("mechanisms")
    mechanisms = mechanisms if isinstance(mechanisms, list) else []
    kinds = sorted({entry.get("kind") for entry in mechanisms
                    if isinstance(entry, dict) and isinstance(entry.get("kind"), str)
                    and entry["kind"] in MECHANISMS})
    shortcuts = sorted({shortcut.get("policy") for entry in mechanisms if isinstance(entry, dict)
                        for shortcut in (entry.get("shortcuts") if isinstance(entry.get("shortcuts"), list) else [])
                        if isinstance(shortcut, dict) and isinstance(shortcut.get("policy"), str)
                        and shortcut["policy"] in SHORTCUTS})
    traps = spec.get("traps")
    traps = traps if isinstance(traps, list) else []
    trap_types = sorted({trap.get("type") for trap in traps
                         if isinstance(trap, dict) and isinstance(trap.get("type"), str)})
    return {"mechanisms": kinds, "shortcuts": shortcuts, "trap_types": trap_types,
            "construction_version": plan.get("version"),
            "basis": "declared construction; observed failures require native attribution"}


def batch_diversity(tasks: list[dict]) -> dict:
    """Report repetitions without inventing a numeric acceptance threshold."""
    counts = Counter()
    patterns = Counter()
    missing = []
    for task in tasks:
        declared = task.get("capability_signature") or {}
        kinds = declared.get("mechanisms") or declared.get("trap_types") or []
        if kinds:
            counts[" + ".join(sorted(kinds))] += 1
        else:
            missing.append(task.get("short_name") or task.get("bundle"))
        patterns["multi-turn" if task.get("multi_turn") else "single-turn"] += 1
    return {"construction_signatures": dict(sorted(counts.items())),
            "delivery_patterns": dict(sorted(patterns.items())),
            "unprofiled_tasks": missing,
            "review_required": bool(missing or any(count > 1 for count in counts.values())),
            "basis": "review repeated mechanisms and delivery patterns; not measured capability failures"}
