"""Production authoring policy. Heuristics never substitute for semantic review."""
from __future__ import annotations

import json
from pathlib import Path
from .contracts import ContractError, compile_steps, contained, schema_at, schema_problems
from .capability import plan_problems

#: Objective count per band a production spec must carry, (low, high)
#: inclusive. The one definition: `breadth.BANDS` reads it.
#:
#: Stretch widened 2026-09-25 when the per-task floor rose to
#: `policy.MIN_OBJECTIVES` (8). With stretch capped at two, an eight-check task
#: had exactly one shape without floor checks (6 core + 2 stretch), and floor
#: is the band every attempt passes. Core stays at 4-6 on purpose: padding the
#: core with more members is what the calibration data says does NOT make a
#: task hard. Stretch -- the checks expected to defeat most attempts -- is
#: where an extremely hard first draft puts its extra checks.
#: v2 (user, 2026-10-02): widened for dense tasks and read from policy; a
#: band outside these limits is an advisory (`pipeline.advisory`).
from ..policy import BAND_LIMITS

QUALITY_PROMPT = """
PRODUCTION CONTRACT (required in every emitted spec):
- For a grounded finite shared-allocation problem, optimal_subset accepts ANY
  globally optimal selection. Derive its target from public evidence as
  {items:[{id,eligible,values:{metric:decimal},requires:[ids],excludes:[ids]}],
   constraints:[{metric,min:decimal|null,max:decimal|null}],
   objectives:[{metric,direction:'max'|'min'}]}.
  Select each item at most once. Ineligible items cannot be selected; required
  companions must be selected and exclusions cannot coexist. Missing item metric
  values are zero; totals sum the selected items' exact signed values. Every
  constraint is inclusive and must hold. Optimize the objectives in their
  stated order lexicographically, NOT a weighted sum. ALL tied optimal subsets
  and ALL item orders are accepted. No arbitrary private tie-break is allowed.
  Actual addresses {feasible,selected,totals:{EVERY metric:decimal}}. If no feasible
  subset exists, the ONLY valid result is {feasible:false,selected:[]} with totals
  omitted. An empty subset is feasible when the constraints allow it; a zero
  objective is not infeasibility. Publish every rule and every input, including
  these edge semantics and reporting tolerance. Eligibility, values and links
  must derive from the actual public professional rules, not a solved table.
  There are 0..18 items, <=12 distinct metrics, <=24 constraints, and 1..4
  objectives naming distinct metrics. IDs use the optimal_path ASCII convention;
  case and surrounding whitespace are immaterial. Values are finite exact
  decimals with magnitude <=1e12 and at most 12 fractional decimal places; totals and bounds may
  reach 18e12. Each constraint has at least one non-null bound with min<=max.
  Unknown/duplicate IDs and inconsistent required/excluded companions are source
  defects. Reporting tolerance affects totals ONLY, never selection feasibility
  or optimality. Cyclic companion requirements are allowed as joint groups.
  This assertion needs no external optimizer. It is ONE planning decision, not
  an independent judgment per item, constraint, total or objective. It supplies
  grading capability, not proof of difficulty. Do not turn unrelated source
  requests into optimization puzzles merely to use this assertion.
- For a source-supported finite acyclic planning problem, optimal_path verifies
  ANY optimal complete path, without a private tie-break. Its source target is
  a derived object {nodes:[{id,capacity,cost}],edges:[{from,to,capacity,cost}],
  start,end}; actual addresses {feasible,path,bottleneck,cost} in the submission.
  Maximize the minimum capacity across ALL nodes and edges, then minimize the
  sum of ALL node and edge costs at that optimal capacity. Publish these
  semantics, every input, and any reporting tolerance in the assignment.
  All optimal ties are accepted. An infeasible answer is valid only when no
  start-to-end path exists, with path:[] and both metric fields omitted. Declare
  both metric fields optional in the schema; they are required by this assertion
  when feasible is true. A zero-capacity
  reachable path is feasible. One-node start=end includes that node's metrics.
  Node identifiers are ASCII letters followed by letters/digits/_.:- (max 128);
  case and surrounding whitespace are immaterial. There are 1..256 nodes and
  at most 16384 edges; parallel edges and cycles are rejected. Capacities/costs
  are nonnegative exact finite decimals, at most 1e12 and at most 12 decimal
  places. A cost total may exceed a single input's maximum. Reporting tolerance
  applies only to the two reported metrics, never to path optimality. Explicit
  source constraints belong in graph construction, never in a hidden grader
  rule. Every substantive rule needs source controls. This is one professional
  decision, regardless of path length or number of reported metrics. Using this
  assertion establishes no difficulty band; independent review and measurement
  remain necessary. Do not use it for continuous geometry, cyclic graphs or
  additional constraints the two-objective graph does not represent.
- outputs: [{file: 'answer.json', step: 1, schema: {...}}]. Use the supported JSON
  schema subset: explicit type, properties, required, additionalProperties:false,
  items, minItems/maxItems, uniqueItems, enum, minLength/maxLength, minimum/maximum,
  pattern, description. A scalar may explicitly allow null via type:["number",
  "null"] (also integer, boolean or string, in either order). Null is distinct
  from an omitted required field, zero, false and the string "null". Constraints
  on the scalar still apply to non-null values; enum also restricts null when
  present. No other type unions are supported. Derive every uncertainty branch
  from source evidence and test a coherent counterfactual; nullable types never
  establish that an answer is underdetermined. Publish exact output semantics in the instruction. No
  Markdown deliverable parsed as JSON. Revisions own a separate output file.
- solution: map every output filename to a COMPLETE JSON value. Include every
  required field, evidence and substantive analysis. It is checked against both
  the schemas and derived checks; filling targets alone is not a solution.
- quality: {axes:[at least two of inference,execution,restraint],
  levers:[at least one substantive lever other than carry],
  source_evidence:[{file,quote,role}], semantic_checks:[objective IDs],
  unscored_fields:{'file.json:path.to.field':'why this is presentation only'},
  untested_surfaces:[specific remaining limitations],
  counterexamples:[{id,reason,submission:{file:JSON value},fails:[check IDs]}],
  alternatives:[{id,reason,submission:{file:JSON value}}],
  decisions:[{id,question,checks:[semantic IDs],sources:[fixture filenames],shortcut}],
  source_cases:[{id,reason,changes:[semantic IDs],
    source_patches:[{file,before,after}],patches:[{file,path,value}]}],
  difficulty_case:{hardest_decision, first_try_verdict, script_test,
    misreadings:[{trap,misreading,why_plausible,diverges_on,counterexample}],
    pitfalls_considered:[{pitfall,family,where,decision,trap|reason}]}}.
  difficulty_case is the required self-audit (see the system prompt): one
  misreading per trap that drives an objective, each naming its own
  counterexample (never another trap's answer under a new id) that fails a check
  that trap drives, nothing it does not drive, and at most {misreading_share} of
  the objectives; and the trap hunt, at
  least eight grounded candidates, every trap among the planted ones.
  Design the professional decisions before the output fields. Each semantic
  check belongs to one decision. Explain the tempting wrong shortcut and cite
  its load-bearing sources. Several fields derived from one decision do not
  count as independent core decisions. Reject a seed that cannot support the
  required decisions; do not invent undocumented rules or merely add volume.
  Source cases run only in private scratch: replace one unique evidence span,
  give the independently calculated corrected output via patches/submission,
  and list which decisions the old answer must now fail. Cover all semantic
  checks. A counterfactual must remain a coherent instance of the published
  assignment: update every representation of a renamed entity and every
  causally dependent fact, preserve row positions where order matters, and do
  not leave a changed heading contradicted by its body. When parallel editions
  disagree, their public precedence rule must determine the changed answer.
  A corrected answer passing the grader does not establish these semantics;
  justify the changed answer independently from the patched source.
  Private source-change controls establish causal validity, not live task
  difficulty. If an objective's rationale claims that a particular conflict or
  boundary must be resolved, the public case must actually distinguish the
  correct decision from that shortcut. Do not claim a dormant branch as a
  measured reasoning demand. A single mistake propagating into several outputs
  is not evidence of several independent reasoning failures.
  The controller also appends a final newline to text fixtures; that
  irrelevant formatting change must preserve every answer. These controls do
  not authorize changing the published source fixture or its provenance.
  Fixed public parameters remain fixed when unrelated evidence changes. Do not
  borrow another document's row count, IDs or values merely because they happen
  to equal a public constant or domain. A source dependency must reflect the
  professional rule, not provide a convenient substitute for a literal.
  Parser observations are not semantic gold. In particular, mcq_paper exposes
  printed options and visual_cues, never whether artwork is actually missing or
  a question is answerable. Do not recreate a hidden phrase list to infer those
  conclusions. Use explicit, independently reviewed evidence and a published
  operational rule, or choose a decision the available evidence can support.
  transcript_answers returns all printed blocks, including repeated IDs in
  plain, bold and headed forms. Distinct source coverage requires an ID union;
  adding projection row counts is not deduplication.
  Quote exact fixture evidence for the decision rules. Cite at least two files.
  Include at least two defensible-looking wrong solutions with different errors
  and one independently phrased correct solution; cover EVERY objective check
  (semantic or floor) and every guardrail except fixture integrity across the
  counterexamples -- a check no wrong solution fails is a dead check. No empty
  or malformed counterexample may stand in for a substantive reasoning error.
  To avoid repeating large tables, a case may replace submission with
  patches:[{file:'answer.json',path:'rows.0.conclusion',value:'plausible mistake'}].
  These replace existing fields in the complete reference. Each case starts from
  a fresh reference; numeric path components index arrays from zero.
  Calculated totals, corrected ranges, deadlines and abstention explanations are
  substantive; never mark them presentation-only to evade grading. Include a
  counterexample that changes a claimed computed result while leaving copied
  source labels correct. Either check a required professional conclusion or
  redesign the requested output so its actual meaning is objectively verified.
  A prose guard that matches words such as 'cannot' does not verify an abstention
  claim. Prefer structured claims with checked scope, affected IDs and reasons;
  any optional presentation prose must add no separate ungraded obligation.
- Grade every substantive required field. For arrays of objects, compare whole
  rows (including identifiers and conclusions) so shuffling conclusions between
  rows fails. This also applies to preservation guardrails: comparing a column
  of copied cells cannot protect which record each cell belongs to. Keep source
  evidence rows separate from derived conclusions when their guardrails differ.
  Mere field presence, fixed labels, heading sets, subset/superset
  inclusion or sentinel tokens cannot carry core credit. Use exact coverage for
  exhaustively requested sets; subset_of accepts empty sets and superset_of
  accepts listing everything. At least 70% of objective weight must evaluate
  substantive core/stretch decisions, not counts of headings or labels. A
  substantive floor check may cover a required field and belong to a decision,
  but cannot supply this weight threshold or a distinct core decision. Do not
  relabel an easy check as core merely to satisfy semantic field coverage.
  Use multiset_equals for unordered row collections when every selected row
  must appear exactly once: it preserves multiplicity after normalization.
  set_equals deliberately ignores duplicates and is only for mathematical sets.
  Arrays of records require multiset_equals (or ordered equals), including in
  guardrails. The controller independently tests row duplication, deletion,
  reordering and exchanges of cells between records through the exported grader.
- Per TASK, across all steps: {core} declared core objectives, at most {floor_max} floor,
  and {stretch} stretch -- at least {min_objectives} objectives in total. There is no
  guardrail-count quota. At least four
  distinct core decisions are required across the task. A follow-up may revise
  one decision; do not split its arithmetic into extra core checks. Each scored
  step still needs substantive work, with at least 70% of its objective weight
  on semantic core/stretch decisions. Only core objectives can gate other
  objectives. Avoid dependencies on literal strings or mere file existence.
- Guardrails protect genuine negative obligations, such as unchanged source
  documents or prohibited records. Do not add copied registers, repeated
  conclusions or invented prohibitions to fill a guardrail budget. A required
  correct calculation or transcription is positive work; if it is useful,
  score it at its measured difficulty or omit it. Never convert an easy
  objective to a zeroing guard merely to improve the apparent difficulty mix.
  A history snapshot preserves a prior recorded submission, not the current
  copy in the solver workspace. Do not promise a live-file preservation rule
  unless the verifier actually compares it with trusted prior bytes. Remove
  unnecessary restrictions that the task cannot enforce.
- Difficulty must arise from genuine reasoning demands -- conflicting evidence,
  revised premises, dependencies, temporal reasoning, justified restraint, or
  any other trap-hunt family the scenario genuinely supports. Publish the
  precedence rule, uncertainty convention and relevant scope in the fixture
  document where a professional would find it, or in the instruction only when
  no document can carry it; the instruction never announces which document is
  stale or which wins. Do not invent
  arbitrary hidden business rules to make a task hard. Every load-bearing source
  needs an exact evidence citation. Release requires ten valid episodes per
  model on both calibration models, grader sanity and executed controls; the
  measured pass@1 is reported against the target, and never blocks release.
  Do not infer action completion from a mentioned milestone or keyword: a status
  audit needs an as-of date and completion evidence. Distinguish independent
  worst-end stress scenarios from correlated planning ranges, and a delivery
  buffer from a contradiction. Any narrowed scope must still answer the stated
  professional question; explicitly disclose what the available evidence cannot
  establish. Numeric inaccuracy alone is not proof of a prohibited action.
- Row-preserving derivation: {op:'select',of:EXPRESSION,fields:{output_key:'row_field'}}
  selects whole keyed conclusions; {op:'filter',of:EXPRESSION,where:CLAUSE} filters
  rows; {op:'latest',of:EXPRESSION,by:['business_key'],order_by:'timestamp',
  value_type:'datetime'} chooses latest ISO revisions per key, rejecting conflicting
  ties. Number and string ordering are also available when the public rule says so.
  Prefer these to independently plucked column sets that lose associations.
  CLAUSE/FILTER has no op key: use {field:'status',eq:'approved'}, or nested
  {all:[CLAUSE,...]} / {any:[CLAUSE,...]}. Never put all and any in the same
  object or mix a group with a field. A field clause needs one or more of
  eq/ne/in/not_in/gt/gte/lt/lte/present/matches; present takes a boolean,
  matches a regex string, and numeric comparisons require numeric operands.
  Use compare for expression-to-expression comparisons. The explicit empty
  predicate {} matches all rows; empty all/any groups retain logical true/false.
- bind_rows attaches source-derived scalar policy values before row evaluation:
  {op:'bind_rows',of:ROWS,fields:{policy_min_pct:SOURCE_EXPRESSION}}. Bindings
  use the same source/read role as the collection, are evaluated once, preserve
  row order and multiplicity, and may not overwrite existing fields. Names must
  be simple identifiers. Read the bound values with field/path in derive_rows;
  compare row amounts with the bound policy value instead of hard-coding a
  threshold from another document. Use compare to derive an eligibility boolean,
  then filter or branch on that boolean. Binding accepts scalars, not arrays or
  records, and does not by itself make a decision substantive.
- derive_rows evaluates business decisions per keyed source row:
  {op:'derive_rows',of:ROWS,fields:{id:{op:'field',path:'id'},net:{op:'subtract',
    a:{op:'field',path:'approved'},b:{op:'field',path:'paid'}}}}.
  All field expressions read the incoming row; a sibling field you are defining
  is not visible yet. Nest derive_rows stages to use a newly computed value, and
  explicitly carry forward identifiers or fields needed by the next stage.
  Within fields, use field/path, scalar literal/value/why (public rules only),
  add/subtract/multiply/divide with a,b, round/of/places, or
  {op:'if',where:FILTER,then:EXPRESSION,else:EXPRESSION} for justified uncertainty.
  date_add/date/days uses ISO dates and integer calendar days; days_between/start/end
  computes end minus start. Publish calendar/rounding/precedence rules explicitly.
  For decimal financial rounding, round accepts mode:'half_up' or 'half_even'
  with integer places (-308 through 308). Use the mode stated in the public
  instruction; omitting mode retains legacy Python rounding. Explicit modes
  evaluate nested add/subtract/multiply/divide (and top-level sums) exactly over
  decimal operand values before rounding. Already-derived fields retain their
  numeric values; this is not a change to all evaluator arithmetic. Compare eligibility to
  unrounded amounts unless the public business rule says to use rounded values.
  Source scalar parsing is available both at top level and inside derive_rows:
  only/of requires a one-element list; extract/of/pattern/group requires exactly
  one regex match (group defaults to 0); number/of parses one formatted decimal;
  range_bound/of/bound ('lower' or 'upper') parses a numeric range such as
  '+$8,000–15,000'. Currency prefixes and Markdown emphasis are formatting, never
  exchange-rate conversion. Extra prose, mixed currencies and ambiguous values
  are rejected. parse_date/of/format supports '%Y-%m-%d', '%Y/%m/%d', '%m/%d';
  the last requires an explicit year in the expression AND public instruction.
  compare/a/b/value_type ('number','date','string')/comparison ('eq','ne','lt',
  'lte','gt','gte') compares derived operands.
  Numeric compare optionally accepts mode:'exact'. It evaluates nested
  add/subtract/multiply/divide, and top-level sums, as rational arithmetic over
  decimal operands. Explicit number/range parsing preserves all digits of
  source text; already parsed numeric values and previously derived fields
  retain their decimal values. It does not recover precision lost in an earlier
  calculation or JSON-number parse. With no mode, legacy comparisons remain
  unchanged. Compare original quantities under the source rule; reporting
  rounding never establishes mathematical equality of distinct inputs.
  record/fields assembles a whole
  object from top-level expressions, so one check can compare a derived interval
  or decision with its business key. Do not substitute keyword matches for the
  arithmetic, temporal comparisons or cross-source decisions you promise.
  An equals check over an object may declare unordered_paths:['lines'] for named
  nested arrays; publish that row order is immaterial. Whole-row associations
  and multiplicity remain enforced. Other arrays remain order-sensitive.
  svg_elements projects declared SVG attributes, Markdown section headings and
  ancestor attributes; it does not render, apply transforms/CSS, or infer defaults.
  min/max over of:VALUES compute numeric extrema; optional fields:['cx','cy']
  takes extrema across those named row fields. Empty/nonnumeric evidence is an
  error. Read the business quantity from its actual source attributes, not a
  different quantity that happens to match. Parser table/row ordinals are not
  semantic identities unless the public rule explicitly depends on position.
  quality.source_invariants may contain id/reason/source_patches for changes
  that must preserve the complete answer, such as unrelated table insertion.
  They never count as source-change coverage and cannot provide output patches.
  Derive decisions, reconciled amounts and deadlines rather than copying source
  labels or awarding multiple objectives for the same inferred fact.
"""

# The band text is interpolated from BAND_LIMITS and the policy floor, so the
# prompt cannot drift from what production_problems and validate enforce.
from ..policy import MIN_OBJECTIVES as _MIN_OBJECTIVES
from ..policy import MISREADING_MAX_OBJECTIVE_SHARE as _MISREADING_SHARE
QUALITY_PROMPT = (QUALITY_PROMPT
                  .replace("{core}", "%d-%d" % BAND_LIMITS["core"])
                  .replace("{floor_max}", str(BAND_LIMITS["floor"][1]))
                  .replace("{stretch}", "%d-%d" % BAND_LIMITS["stretch"])
                  .replace("{min_objectives}", str(_MIN_OBJECTIVES))
                  .replace("{misreading_share}", f"{_MISREADING_SHARE:.0%}"))


def _leaves(schema, prefix=""):
    if schema.get("type") == "object":
        for key in schema.get("required", []):
            path = f"{prefix}.{key}" if prefix else key
            yield from _leaves(schema["properties"][key], path)
    elif schema.get("type") == "array" and schema.get("items", {}).get("type") == "object":
        # Whole rows must be checked: independent column sets lose associations.
        yield prefix
    else:
        yield prefix


def production_problems(spec: dict, bundle: Path, authoring: bool = False) -> list[str]:
    """The production contract. `authoring=True` (the designer's own check)
    also requires the difficulty self-audit, `difficulty_case_problems`; the
    bundle gate does not, so bundles built before it existed are not re-blocked."""
    problems = []
    try:
        steps = compile_steps(spec)
    except (ContractError, KeyError, TypeError, AttributeError) as exc:
        return [f"step contract: {exc}"]
    outputs = spec.get("outputs")
    if not isinstance(outputs, list) or not outputs:
        return ["production requires public outputs schemas; legacy bundles are diagnostic only"]
    by_file = {}
    for output in outputs:
        file = output["file"]
        try:
            contained(bundle, file)
        except ContractError as exc:
            problems.append(str(exc))
        if not file.endswith(".json"):
            problems.append(f"{file}: production output must be JSON with a .json extension")
        problems += schema_problems(output.get("schema"), file)
        by_file[file] = output
    if problems:
        return problems
    checks = spec.get("checks", [])
    ids = {c["id"] for c in checks}
    objectives = [c for c in checks if c.get("kind") == "objective"]
    fingerprints = set()
    for check in objectives:
        key = json.dumps({k: check.get(k) for k in ("actual", "target", "assertion", "tolerance")}, sort_keys=True)
        if key in fingerprints:
            problems.append(f"{check['id']}: duplicate objective cannot add independent difficulty signal")
        fingerprints.add(key)
    quality = spec.get("quality") or {}
    if len(set(quality.get("axes", [])) & {"inference", "execution", "restraint"}) < 2:
        problems.append("quality.axes needs at least two independent difficulty axes")
    if not [v for v in quality.get("levers", []) if str(v).strip().lower() not in ("", "carry")]:
        problems.append("quality.levers needs a substantive lever beyond Carry")
    if len(str(spec.get("novelty", "")).strip()) < 30:
        problems.append("novelty must explain the distinct reasoning problem")
    semantic = set(quality.get("semantic_checks", []))
    if semantic - {c["id"] for c in objectives}:
        problems.append("semantic_checks names missing or non-objective checks")
    total = sum(c.get("weight", 0) for c in objectives)
    strong = [c for c in objectives if c["id"] in semantic]
    discriminative = [c for c in strong if c.get("band") != "floor"]
    if not total or sum(c.get("weight", 0) for c in discriminative) / total < .7:
        problems.append("at least 70% of objective weight must cover substantive core/stretch decisions")
    for c in strong:
        if c.get("assertion") in {"present", "contains", "matches", "subset_of", "superset_of", "row_count"} or (c.get("target") or {}).get("op") == "literal":
            problems.append(f"{c['id']}: weak assertion or literal cannot count as a semantic objective")
    decisions, decision_ids = {}, set()
    for decision in quality.get("decisions", []):
        did = decision.get("id")
        if not isinstance(did, str) or not did or did in decision_ids:
            problems.append("decisions need distinct nonempty IDs")
        decision_ids.add(did)
        if not decision.get("question") or not decision.get("shortcut") or not decision.get("sources"):
            problems.append(f"decision {did}: needs a professional question, shortcut and load-bearing sources")
        for file in decision.get("sources", []):
            try:
                if not contained(bundle / "environment/files", file).is_file():
                    raise ValueError("missing source")
            except (ValueError, TypeError) as exc:
                problems.append(f"decision {did}: invalid source {file}: {exc}")
        for cid in decision.get("checks", []):
            if cid not in semantic or cid in decisions:
                problems.append(f"decision {did}: unknown or repeated semantic check {cid}")
            decisions[cid] = did
    if set(decisions) != semantic:
        problems.append("every semantic check must belong to exactly one substantive decision")
    from ..source_controls import problems as source_problems
    problems.extend(source_problems(spec, bundle))
    bands = {b: sum(c.get('band', 'core') == b for c in objectives)
             for b in BAND_LIMITS}
    if any(not low <= bands[b] <= high for b, (low, high) in BAND_LIMITS.items()):
        problems.append("task: require " + ", ".join(
            f"{low}-{high} {b}" for b, (low, high) in BAND_LIMITS.items())
            + f" objectives across all steps; got {bands}")
    distinct = {decisions[c['id']] for c in objectives
                if c.get('band') == 'core' and c['id'] in decisions}
    if len(distinct) < 4:
        problems.append('task: need at least four distinct core decisions, not multiple fields or steps of one decision')
    for step in steps:
        owned = [c for c in objectives if c["step"] == step["name"]]
        weight = sum(c.get('weight', 0) for c in owned)
        substantive = sum(c.get('weight', 0) for c in owned
                          if c['id'] in semantic and c.get('band') in {'core', 'stretch'})
        if not weight or substantive / weight < .7:
            problems.append(f"{step['name']}: each scored step needs at least 70% substantive core/stretch weight; carry or floor-only revisions do not qualify")
        if not any(o["step"] == step["name"] for o in outputs):
            problems.append(f"{step['name']}: no output contract")
    by_id = {c["id"]: c for c in checks}
    for c in checks:
        for dep in c.get("requires", []):
            gate = by_id[dep]
            if gate.get("kind") != "objective" or gate.get("band") != "core" or (gate.get("target") or {}).get("op") == "literal" or gate.get("assertion") in {"present", "matches", "contains"}:
                problems.append(f"{c['id']}: only substantive core checks may be prerequisites")
        actual = c.get("actual") or {}
        if c.get("assertion") == "fixture_intact":
            continue
        output = by_file.get(actual.get("file"))
        if output is None or actual.get("op") != "field" or schema_at(output["schema"], actual.get("path", "")) is None:
            problems.append(f"{c['id']}: actual must address a declared JSON field")
            continue
        path = actual.get("path", "")
        field_schema = schema_at(output["schema"], path)
        for nested in (c.get("unordered_paths") or []) if isinstance(c.get("unordered_paths", []), list) else []:
            if not isinstance(nested, str):
                continue  # Check.validate reports malformed path declarations.
            nested_schema = schema_at(field_schema, nested)
            if not nested_schema or nested_schema.get("type") != "array":
                problems.append(f"{c['id']}: unordered path {nested!r} must address a declared array")
        if "[]" in path and c.get("assertion") in {
                "equals", "set_equals", "multiset_equals", "subset_of", "superset_of"}:
            problems.append(f"{c['id']}: column-only comparisons lose record associations; compare complete keyed rows")
        if (field_schema.get("type") == "array"
                and field_schema.get("items", {}).get("type") == "object"
                and c.get("assertion") == "set_equals"):
            problems.append(f"{c['id']}: record collections must preserve multiplicity; use multiset_equals or ordered equals")
    unscored = quality.get("unscored_fields") or {}
    for file, output in by_file.items():
        paths = [(c.get("actual") or {}).get("path", "") for c in strong
                 if (c.get("actual") or {}).get("file") == file]
        for leaf in _leaves(output["schema"]):
            if any(p == "" or leaf == p or leaf.startswith(p + ".") for p in paths):
                continue
            reason = unscored.get(f"{file}:{leaf}", "")
            if not isinstance(reason, str) or len(reason.strip()) < 30:
                problems.append(f"{file}:{leaf}: required field has no semantic check or reviewable presentation-only rationale")
    cited = set()
    for index, evidence in enumerate(quality.get("source_evidence", [])):
        # Name the item and the exact failure: "invalid source evidence" alone,
        # repeated 53 times, cost a designer dozens of steps to locate.
        where = f"quality.source_evidence[{index}]"
        if not isinstance(evidence, dict) or not isinstance(evidence.get("file"), str):
            problems.append(f"invalid source evidence {where}: needs a fixture `file`")
            continue
        where += f" ({evidence['file']})"
        try:
            text = contained(bundle / "environment/files", evidence["file"]).read_text()
        except (OSError, ValueError) as exc:
            problems.append(f"invalid source evidence {where}: file not readable in the fixture ({exc})")
            continue
        quote = evidence.get("quote", "")
        if not isinstance(quote, str) or len(quote.strip()) < 15:
            problems.append(f"invalid source evidence {where}: quote shorter than 15 characters")
        elif quote not in text:
            problems.append(f"invalid source evidence {where}: quote {quote[:60]!r} is not verbatim in the file "
                            "(copy it exactly; whitespace and punctuation count)")
        elif not evidence.get("role"):
            problems.append(f"invalid source evidence {where}: `role` must say what the quote establishes")
        else:
            cited.add(evidence["file"])
    if len(cited) < 2:
        problems.append("at least two distinct fixture files need exact decision-rule citations")
    for decision in quality.get("decisions", []):
        for file in decision.get("sources", []):
            if file not in cited:
                problems.append(f"decision {decision.get('id')}: load-bearing source {file} needs an exact evidence citation")
            exercised = any(file in {p.get("file") for p in case.get("source_patches", [])}
                            and set(case.get("changes", [])) & set(decision.get("checks", []))
                            for case in quality.get("source_cases", []))
            if not exercised:
                problems.append(f"decision {decision.get('id')}: no source-change control demonstrates the role of {file}")
    examples = quality.get("counterexamples", [])
    if len(examples) < 2 or len(quality.get("alternatives", [])) < 1:
        problems.append("supply at least two substantive counterexamples and one correct alternative")
    covered = set()
    for case in examples:
        fails = set(case.get("fails", []))
        if not fails or fails - ids or not case.get("reason") or not (case.get("submission") or case.get("patches")):
            problems.append("counterexample needs reason, complete submission, and valid failed check IDs")
        covered |= fails
    # EVERY objective, not only the semantic ones: a floor check no plausible
    # wrong answer can fail discriminates nothing and is weight nobody earns by
    # reasoning (user, 2026-09-25: every check genuine and discriminating).
    required = ({c["id"] for c in objectives} | semantic
                | {c["id"] for c in checks if c.get("kind") == "guardrail" and c.get("assertion") != "fixture_intact"})
    if required - covered:
        problems.append(f"counterexamples do not cover {sorted(required - covered)}; every objective "
                        "check must be failed by at least one substantive wrong solution")
    if not isinstance(quality.get("untested_surfaces"), list) or not quality["untested_surfaces"]:
        problems.append("declare remaining untested_surfaces explicitly")
    if set(spec.get("solution", {})) != set(by_file):
        problems.append("solution must contain exactly every contracted output file")
    if authoring:
        problems.extend(difficulty_case_problems(spec, bundle))
    problems.extend(plan_problems(spec, required=False, bundle=bundle))
    return problems


#: Minimum length of each reasoned field in the difficulty self-audit. Long
#: enough to hold a specific claim about THIS task, short of an essay.
_CASE_TEXT_MIN = 60
_MISREADING_TEXT_MIN = 40

#: The trap hunt (user, 2026-09-25): candidates the author must have examined
#: and dispositioned before submitting. It forces a search wider than the first
#: pitfall noticed; every planted trap is one of them. A process requirement,
#: not a difficulty claim -- the screen measures difficulty.
MIN_PITFALLS_CONSIDERED = 8


def difficulty_case_problems(spec: dict, bundle: Path | None = None) -> list[str]:
    """The difficulty self-audit every draft must carry before it is submitted.

    User, 2026-09-25: the first authoring pass is the only pass for difficulty,
    so the author must make, and argue, the case that THIS draft is extremely
    hard before submitting it -- not leave it to calibration to discover.

    `quality.difficulty_case`:
      hardest_decision   the decision a frontier model is most likely to get
                         wrong, and why
      first_try_verdict  why a strong model working carefully will NOT get every
                         graded answer right on its first attempt
      misreadings        one per trap that drives an objective: the plausible
                         wrong reading, why a careful model adopts it, where it
                         diverges from the correct answer, and the id of the
                         quality.counterexample that encodes it
      pitfalls_considered  the trap hunt: at least MIN_PITFALLS_CONSIDERED
                         candidates, each grounded in a fixture file and either
                         planted (naming its trap) or rejected (with a reason);
                         every trap appears as planted

    What is checked here is the case's COMPLETENESS and its LINKS, not its
    truth: every objective-driving trap has a misreading; each names a real
    counterexample, and that counterexample fails at least one check the trap
    claims to drive. The controls then EXECUTE every counterexample through the
    shipped grader (`assurance.controls`), so a misreading that fails nothing is
    refused at build time -- the trap is live, not dormant. Whether the task is
    actually hard is measured by the calibration screen, never asserted here.
    """
    quality = spec.get("quality") or {}
    case = quality.get("difficulty_case")
    where = "quality.difficulty_case"
    if not isinstance(case, dict):
        return [f"{where} is missing: before submitting, make the case that this draft is "
                "extremely hard -- hardest_decision, first_try_verdict, script_test, and one misreadings "
                "entry per trap that drives an objective (trap, misreading, why_plausible, "
                "diverges_on, counterexample). The first pass is the only pass for difficulty"]
    problems = []
    for field in ("hardest_decision", "first_try_verdict", "script_test"):
        if len(str(case.get(field, "")).strip()) < _CASE_TEXT_MIN:
            problems.append(f"{where}.{field} needs a specific, reasoned claim about this task "
                            f"(at least {_CASE_TEXT_MIN} characters)")
    objectives = {c.get("id") for c in spec.get("checks") or []
                  if isinstance(c, dict) and c.get("kind") == "objective"}
    traps = {t.get("id"): t for t in spec.get("traps") or [] if isinstance(t, dict)}
    examples = {c.get("id"): c for c in quality.get("counterexamples") or [] if isinstance(c, dict)}
    entries = case.get("misreadings")
    if not isinstance(entries, list) or not entries:
        return problems + [f"{where}.misreadings must list the plausible wrong reading behind "
                           "each trap -- a trap with no misreading is decoration"]
    covered, used, bodies = set(), {}, {}
    for index, entry in enumerate(entries):
        at = f"{where}.misreadings[{index}]"
        if not isinstance(entry, dict):
            problems.append(f"{at} must be an object")
            continue
        trap = traps.get(entry.get("trap"))
        if trap is None:
            problems.append(f"{at}.trap {entry.get('trap')!r} is not a declared trap id")
            continue
        covered.add(trap.get("id"))
        for field, least in (("misreading", _MISREADING_TEXT_MIN), ("why_plausible", _MISREADING_TEXT_MIN),
                             ("diverges_on", 10)):
            if len(str(entry.get(field, "")).strip()) < least:
                problems.append(f"{at}.{field} is missing or too thin (at least {least} characters)")
        example = examples.get(entry.get("counterexample"))
        if example is None:
            problems.append(f"{at}.counterexample {entry.get('counterexample')!r} is not a "
                            "quality.counterexamples id; encode the misreading as a wrong "
                            "solution so it is executed through the grader")
            continue
        driven = set(trap.get("checks") or []) & objectives
        fails = set(example.get("fails") or []) & objectives
        if driven and not (fails & driven):
            problems.append(f"{at}: counterexample {example.get('id')!r} fails none of the "
                            f"objectives trap {trap.get('id')!r} drives ({sorted(driven)}); a "
                            "misreading that costs nothing makes the trap dormant")
        # One all-wrong counterexample named by every misreading proved nothing
        # about any single trap (review, 2026-09-26). Each trap's misreading is
        # its own wrong answer, and it may fail only what that trap drives --
        # which the controls then EXECUTE (assurance: other objectives must pass).
        if fails - driven:
            problems.append(f"{at}: counterexample {example.get('id')!r} also fails "
                            f"{sorted(fails - driven)}, which trap {trap.get('id')!r} does not "
                            "drive. Encode ONLY this misreading, or add those checks to the "
                            "trap's `checks` if the trap genuinely drives them")
        # A misreading that loses EVERY objective is an all-wrong answer, not a
        # reading that agrees with the right one almost everywhere -- and the
        # latter is what measurably defeats frontier models.
        if objectives and fails >= objectives:
            problems.append(f"{at}: counterexample {example.get('id')!r} fails every objective; "
                            "a misreading diverges on the decisions its trap drives and agrees "
                            "with the correct answer on the rest, so at least one objective "
                            "must pass")
        elif objectives and len(fails) > _MISREADING_SHARE * len(objectives):
            problems.append(f"{at}: counterexample {example.get('id')!r} fails {len(fails)} of "
                            f"{len(objectives)} objectives; a misreading may lose at most "
                            f"{_MISREADING_SHARE:.0%} of them. Encode the plausible reading that "
                            "agrees with the correct answer almost everywhere, or split the trap")
        if example.get("id") in used and used[example["id"]] != trap.get("id"):
            problems.append(f"{at}: counterexample {example.get('id')!r} already encodes trap "
                            f"{used[example['id']]!r}'s misreading; every trap needs its own")
        # Renaming one wrong answer is not a second misreading.
        body = (json.dumps(example["submission"], sort_keys=True, default=str)
                if example.get("submission") else None)   # a missing one is reported elsewhere
        twin = next((other for other, (tid, text) in bodies.items()
                     if body is not None and text == body and other != example.get("id")
                     and tid != trap.get("id")), None)
        if twin is not None:
            problems.append(f"{at}: counterexample {example.get('id')!r} submits exactly what "
                            f"{twin!r} (trap {bodies[twin][0]!r}) submits; two traps cannot "
                            "share one wrong answer")
        bodies.setdefault(example.get("id"), (trap.get("id"), body))
        used.setdefault(example.get("id"), trap.get("id"))
    missing = sorted(tid for tid, t in traps.items()
                     if set(t.get("checks") or []) & objectives and tid not in covered)
    if missing:
        problems.append(f"{where}.misreadings has no entry for trap(s) {missing}; every trap that "
                        "drives an objective must show the wrong reading it tempts and prove, "
                        "through a counterexample, that the reading loses credit")
    return problems + _pitfall_problems(case, traps, bundle)


def _pitfall_problems(case: dict, traps: dict, bundle: Path | None) -> list[str]:
    """The trap hunt: a wide, grounded search, every trap one of its finds."""
    where = "quality.difficulty_case.pitfalls_considered"
    found = case.get("pitfalls_considered")
    if not isinstance(found, list) or len(found) < MIN_PITFALLS_CONSIDERED:
        return [f"{where} needs at least {MIN_PITFALLS_CONSIDERED} candidate pitfalls you examined "
                "in these documents (have: "
                f"{len(found) if isinstance(found, list) else 0}). Run the trap hunt across every "
                "pitfall family in the system prompt; plant the genuine ones, reject the rest "
                "with the reason"]
    problems, planted = [], set()
    fixture = Path(bundle) / "environment/files" if bundle else None
    for index, item in enumerate(found):
        at = f"{where}[{index}]"
        if not isinstance(item, dict):
            problems.append(f"{at} must be an object")
            continue
        if len(str(item.get("pitfall", "")).strip()) < 30:
            problems.append(f"{at}.pitfall must describe the specific pitfall (at least 30 characters)")
        rel = item.get("where")
        if not isinstance(rel, str) or not rel.strip():
            problems.append(f"{at}.where must name the fixture file the pitfall lives in")
        elif fixture is not None:
            try:
                if not contained(fixture, rel).is_file():
                    raise ValueError("not a file")
            except (ValueError, TypeError, OSError):
                problems.append(f"{at}.where {rel!r} is not a fixture file; ground every "
                                "candidate in the documents")
        decision = item.get("decision")
        if decision == "planted":
            if item.get("trap") not in traps:
                problems.append(f"{at}: planted pitfall names {item.get('trap')!r}, not a declared trap id")
            else:
                planted.add(item["trap"])
        elif decision == "rejected":
            if len(str(item.get("reason", "")).strip()) < 20:
                problems.append(f"{at}: a rejected pitfall needs its reason (not genuinely supported, "
                                "not resolvable from published rules, or not live)")
        else:
            problems.append(f"{at}.decision must be 'planted' or 'rejected'")
    unplanted = sorted(set(traps) - planted)
    if unplanted:
        problems.append(f"{where}: trap(s) {unplanted} are not recorded as planted pitfalls; every "
                        "trap must come out of the hunt")
    return problems


def gate(ctx):
    from .contracts import strict_json
    from ..gates.base import Finding, Severity
    from .validate import validate
    path = ctx.path("authoring/spec.json")
    spec = strict_json(path.read_text())
    # The same contract the designer's check_draft holds a draft to. Without
    # validate here a built task could be gate-green while its spec had traps
    # citing checks it never declared.
    problems = production_problems(spec, ctx.task_dir) + validate(spec, ctx.task_dir)
    problems += published_paths(spec, ctx.task_dir)
    # v2 (user, 2026-10-02): non-required findings are advisories, never blockers.
    from ..advisory import classify
    return [Finding(Severity.WARN if classify(p) else Severity.BLOCKER,
                    "production-advisory" if classify(p) else "production-contract",
                    p, "authoring/spec.json")
            for p in dict.fromkeys(problems)], {}


def published_paths(spec: dict, bundle: Path) -> list[str]:
    """[T1] Each built step instruction states, as absolute paths, where the
    inputs are (read-only) and where each of its deliverables goes. Checked on
    the built instruction.md -- what the agent actually reads -- not the spec."""
    from .contracts import INPUT_ROOT, OUTPUT_ROOT
    try:
        steps = compile_steps(json.loads(json.dumps(spec)))
    except (ContractError, KeyError, TypeError, AttributeError):
        return []
    outputs = [o for o in spec.get("outputs") or [] if isinstance(o, dict)]
    names = [s["name"] for s in steps]
    problems = []
    for index, step in enumerate(steps):
        path = bundle / "steps" / step["name"] / "instruction.md"
        try:
            text = path.read_text()
        except OSError:
            problems.append(f"{step['name']}: no built instruction.md to publish the task contract")
            continue
        if INPUT_ROOT not in text or "read-only" not in text:
            problems.append(f"{step['name']}: instruction.md never states the input directory "
                            f"{INPUT_ROOT} and that it is read-only")
        for output in outputs:
            owner = output.get("step")
            owner = names[owner - 1] if type(owner) is int and 1 <= owner <= len(names) else owner
            if owner == step["name"] and f"{OUTPUT_ROOT}/{output.get('file')}" not in text:
                problems.append(f"{step['name']}: instruction.md never states the absolute output "
                                f"path {OUTPUT_ROOT}/{output.get('file')}")
    return problems
