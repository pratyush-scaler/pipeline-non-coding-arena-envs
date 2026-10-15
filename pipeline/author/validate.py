"""Static validation of a design spec, before anything executes it.

Generation fails in a characteristic way: not by producing nonsense, but by
producing something well-formed that refers to things which do not exist. Across
the first orchestrator runs every failure was of that kind -- a `stem_overlap`
naming source `t09` where the projection is `t09.jsonl`, a parse step reading a
fixture file that was never lifted, a `difference` missing its `a` operand.

Those surface as a `KeyError` three stages later, inside the probe runner, where
the message names a dictionary key and not the mistake. So references are
resolved here instead, against the fixture and against the spec's own
declarations, and every problem is reported at once in language the designer can
act on -- which is what makes a single repair round-trip worth attempting rather
than re-rolling the whole design.

This is not a quality judgment. A spec can pass every check here and still be a
bad task; that is what the gate chain and calibration are for. This only
establishes that the spec is internally consistent enough to run.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

from . import oracle
from .checks import ASSERTIONS, SCALAR_OPS, rounding_problems, binding_problems, comparison_problems, row_filter_problems
from .traps import Trap

#: Probes that are required to score exactly the reference, so a trap pointed
#: at one of them can never be shown to catch anything.
UNDEMONSTRATING_PROBES = frozenset({"golden", "untidy_correct"})

#: Assertions whose target is a PATTERN or a bound rather than an expected
#: answer. A literal is the natural form there and needs no justification --
#: demanding one sends the designer round a repair loop over a regex.
_VALUE_ASSERTIONS = ("equals", "numeric_within", "set_equals", "multiset_equals", "subset_of",
                     "superset_of", "row_count", "optimal_path", "optimal_subset")
_PATTERN_TARGETS: set[str] = set()

#: Required operands per expression op. `literal` is absent on purpose: it is
#: checked separately, because it needs a justification rather than an operand.
OPERANDS = {
    "rows": ("file",), "field": ("file",), "text": ("file",), "exists": ("file",),
    "count": ("of",), "sum": ("of", "field"), "pluck": ("of", "field"),
    "min": ("of",), "max": ("of",),
    "set": ("of",), "unique": ("of",), "round": ("of",),
    "difference": ("a", "b"), "intersection": ("a", "b"),
    "divide": ("a", "b"), "multiply": ("a", "b"), "subtract": ("a", "b"),
    "select": ("of", "fields"), "filter": ("of", "where"),
    "latest": ("of", "by", "order_by", "value_type"),
    "derive_rows": ("of", "fields"), "bind_rows": ("of", "fields"),
    "record": ("fields",), "add": ("a", "b"),
    "only": ("of",), "extract": ("of", "pattern"), "number": ("of",),
    "range_bound": ("of", "bound"), "parse_date": ("of", "format"),
    "date_add": ("date", "days"), "days_between": ("start", "end"),
    "compare": ("a", "b", "value_type", "comparison"),
}


def _walk_row(expr, where: str, problems: list[str]) -> None:
    if not isinstance(expr, dict):
        problems.append(f"{where}: row operand must be an expression")
        return
    op = expr.get("op")
    if op == 'round':
        problems.extend(f'{where}: {error}' for error in rounding_problems(expr))
    if op == 'compare':
        problems.extend(f'{where}: {error}' for error in comparison_problems(expr))
    allowed = {"field", "literal", "if", "add", "subtract", "multiply", "divide", "round"} | SCALAR_OPS
    if op not in allowed:
        problems.append(f"{where}: unsupported row operation {op!r}")
        return
    required = {"field": ("path",), "literal": ("value", "why"),
                "if": ("where", "then", "else")}.get(op, OPERANDS.get(op, ()))
    for key in required:
        if key not in expr:
            problems.append(f"{where}: row operation {op!r} needs '{key}'")
    if "where" in expr:
        problems.extend(f"{where}.where: {error}" for error in row_filter_problems(expr["where"]))
    if "file" in expr:
        problems.append(f"{where}: row fields read the current row, never a separate file")
    for key in ("of", "a", "b", "then", "else", "date", "days", "start", "end"):
        if key in expr:
            _walk_row(expr[key], f"{where}.{key}", problems)


def _walk(expr, where: str, readable: set[str], problems: list[str]) -> None:
    if not isinstance(expr, dict):
        problems.append(f"{where}: expected an expression object, got {expr!r}")
        return
    op = expr.get("op")
    if op == 'round':
        problems.extend(f'{where}: {error}' for error in rounding_problems(expr))
    if op == 'compare':
        problems.extend(f'{where}: {error}' for error in comparison_problems(expr))
    if op is None:
        problems.append(f"{where}: expression has no 'op'")
        return
    if op == "literal":
        if "value" not in expr:
            problems.append(f"{where}: literal has no 'value'")
        # A literal TARGET is a hand-typed expected value, which is how an answer
        # key comes to say 26 when the truth is 27. Allowed only with a stated
        # reason it cannot be derived -- and the evaluator refuses it otherwise,
        # so catching it here turns a crash three stages later into a repair.
        if (where.endswith(".target") and where not in _PATTERN_TARGETS
                and not (expr.get("why") or "").strip()):
            problems.append(
                f"{where}: literal target with no 'why'. Derive it from the "
                "projections, or state why it cannot be derived")
        return
    if op not in OPERANDS:
        problems.append(f"{where}: unknown op {op!r}; available: "
                        f"{', '.join(sorted(OPERANDS))}")
        return
    for operand in OPERANDS[op]:
        if operand not in expr:
            problems.append(f"{where}: op {op!r} needs '{operand}'")
    if "where" in expr:
        problems.extend(f"{where}.where: {error}" for error in row_filter_problems(expr["where"]))
    if "file" in expr and expr["file"] not in readable:
        hint = ""
        if where.endswith((".target",)) or ".target." in where:
            hint = (" If this is the deliverable the agent writes, it belongs in "
                    "`actual`, not `target` -- it does not exist when the target "
                    "is computed.")
        problems.append(
            f"{where}: reads {expr['file']!r}, which is neither a declared "
            f"projection nor a fixture file.{hint} Readable here: "
            f"{', '.join(sorted(readable))}")
    # Projections are JSON Lines. `field` json.loads()s the whole file, so it
    # fails on the second line with a message about column 1.
    if op == "field" and str(expr.get("file", "")).endswith(".jsonl"):
        problems.append(
            f"{where}: op 'field' cannot read {expr['file']!r} -- projections are "
            "JSON Lines. Use 'rows' (optionally with 'where'), then 'pluck', "
            "'count' or 'sum'")
    if op == 'bind_rows':
        problems.extend(f'{where}: {error}' for error in binding_problems(expr))
    if op in {"derive_rows", "bind_rows", "record"}:
        fields = expr.get("fields")
        if not isinstance(fields, dict) or not fields:
            problems.append(f"{where}: {op} needs named field expressions")
        else:
            for key, value in fields.items():
                if op == "derive_rows":
                    _walk_row(value, f"{where}.fields.{key}", problems)
                else:
                    _walk(value, f"{where}.fields.{key}", readable, problems)
    if op in {"min", "max"} and "fields" in expr:
        fields = expr["fields"]
        if not isinstance(fields, list) or not fields or any(not isinstance(f, str) or not f for f in fields):
            problems.append(f"{where}: numeric extrema fields must name source row fields")
    for operand in ("of", "a", "b", "date", "days", "start", "end"):
        if operand in expr:
            _walk(expr[operand], f"{where}.{operand}", readable, problems)


def canonical_step_refs(spec: dict) -> int:
    """Rewrite a check's bare step NUMBER to the declared step it counts.

    Measured 2026-10-02: a-011's first hardening attempt was spent on 510
    findings, all "check ... is assigned to step 1, which is not declared
    (steps: ['01-task', '02-revision'])" -- the designer wrote steps as 1 and 2.
    Step N (an int or a digit string, 1-based) is unambiguous when N steps are
    declared, so it is a serialisation artefact, not a design error. Anything
    else is left for `_second_step` to report. Returns how many were rewritten.
    """
    names = [s.get("name") for s in (spec.get("steps") or [])
             if isinstance(s, dict) and s.get("name")]
    if not names:
        return 0
    rewritten = 0
    for check in spec.get("checks") or []:
        if not isinstance(check, dict):
            continue
        named = check.get("step")
        if isinstance(named, bool) or named in names:
            continue
        if isinstance(named, int) or (isinstance(named, str) and named.strip().isdigit()):
            index = int(named) - 1
            if 0 <= index < len(names):
                check["step"] = names[index]
                rewritten += 1
    return rewritten


def parse_stringified_expressions(spec: dict) -> int:
    """Turn expression objects that arrived as JSON TEXT back into objects.

    Measured 2026-10-02: a-049's hardening attempt was spent on 29 findings,
    each "expected an expression object, got '{"op": "subtract", ...}'" -- the
    designer's tool call carried nested expressions inside `fields` as strings.
    Like a top-level array returned as its JSON text (see `objects` below), that
    is a serialisation artefact: a string that parses to an object with an `op`
    is that object. Only check `target`/`actual` trees are walked. Returns how
    many strings were replaced.
    """
    replaced = 0

    def fix(node):
        nonlocal replaced
        if isinstance(node, str):
            text = node.strip()
            if text.startswith("{") and '"op"' in text:
                try:
                    value = json.loads(text)
                except (json.JSONDecodeError, RecursionError):
                    return node
                if isinstance(value, dict) and isinstance(value.get("op"), str):
                    replaced += 1
                    return fix(value)
            return node
        if isinstance(node, dict):
            for key, value in list(node.items()):
                node[key] = fix(value)
        elif isinstance(node, list):
            for index, value in enumerate(node):
                node[index] = fix(value)
        return node

    for check in spec.get("checks") or []:
        if isinstance(check, dict):
            for key in ("target", "actual"):
                if key in check:
                    check[key] = fix(check[key])
    return replaced


def validate(spec: dict, bundle: Path) -> list[str]:
    """Every problem, in one pass. Empty list means the spec will at least run."""
    problems: list[str] = []
    canonical_step_refs(spec)
    parse_stringified_expressions(spec)

    # Normalise once. A generated spec occasionally puts a bare string where a
    # list of objects belongs, and guarding every loop individually means the one
    # loop that was missed raises AttributeError from inside the validator --
    # which escapes the repair loop and kills the task instead of repairing it.
    def objects(key: str) -> list[dict]:
        raw = spec.get(key) or []
        # Tool-use occasionally returns an array field as its JSON text. That is
        # a serialisation artefact, not a design error, so parse it rather than
        # spending a repair round-trip on it.
        if isinstance(raw, str):
            try:
                raw = json.loads(raw)
                spec[key] = raw
            except json.JSONDecodeError:
                pass
        if not isinstance(raw, list):
            problems.append(f"'{key}' must be a list, got {type(raw).__name__}")
            return []
        out = []
        for i, item in enumerate(raw):
            if isinstance(item, dict):
                out.append(item)
            else:
                problems.append(f"{key}[{i}]: must be an object, got "
                                f"{type(item).__name__}: {str(item)[:60]!r}")
        return out

    spec = dict(spec)
    spec["projections"] = objects("projections")
    spec["checks"] = objects("checks")
    spec["traps"] = objects("traps")

    fixture = bundle / "environment" / "files"
    files = {str(p.relative_to(fixture)) for p in fixture.rglob("*") if p.is_file()}

    # --- projections ---
    declared: set[str] = set()
    for i, proj in enumerate(spec.get("projections") or []):
        name = proj.get("as")
        if not name:
            problems.append(f"projection[{i}]: no 'as' name")
            continue
        if name in declared:
            problems.append(f"projection {name!r}: declared twice")
        op = proj.get("op", "parse")
        if op in ("parse", None):
            if proj.get("file") not in files:
                problems.append(
                    f"projection {name!r}: reads fixture file {proj.get('file')!r}, "
                    f"which does not exist. Fixture holds: {', '.join(sorted(files))}")
            if proj.get("parser") not in oracle.REGISTRY:
                problems.append(
                    f"projection {name!r}: unknown parser {proj.get('parser')!r}; "
                    f"registered: {', '.join(sorted(oracle.REGISTRY))}")
        elif op == "concat":
            if not proj.get("sources"):
                problems.append(f"projection {name!r}: concat needs 'sources'")
            for key in (proj.get("sources") or {}):
                if key not in declared and f"{key}.jsonl" not in declared:
                    problems.append(
                        f"projection {name!r}: source {key!r} is not a projection "
                        f"declared before it. Declared so far: "
                        f"{', '.join(sorted(declared)) or 'none'}")
        elif op == "join":
            for side in ("left", "right"):
                if proj.get(side) not in declared:
                    problems.append(
                        f"projection {name!r}: {side}={proj.get(side)!r} is not a "
                        f"projection declared before it. Declared so far: "
                        f"{', '.join(sorted(declared)) or 'none'}")
            if not proj.get("on"):
                problems.append(f"projection {name!r}: join needs 'on'")
            for alias, ref in (proj.get("fields") or {}).items():
                if "." not in str(ref) or str(ref).split(".", 1)[0] not in (
                        "left", "right"):
                    problems.append(
                        f"projection {name!r}: field {alias!r} maps to {ref!r}; "
                        "it must be 'left.<field>' or 'right.<field>'")
        elif op == "stem_overlap":
            if proj.get("paper") not in declared:
                problems.append(
                    f"projection {name!r}: paper={proj.get('paper')!r} is not a "
                    f"projection declared before it")
            for key, label in (proj.get("sources") or {}).items():
                if key not in declared and f"{key}.jsonl" not in declared:
                    problems.append(
                        f"projection {name!r}: source key {key!r} is not a declared "
                        f"projection (names end in .jsonl)")
                if label not in files:
                    problems.append(
                        f"projection {name!r}: source label {label!r} is not a "
                        "fixture filename")
        else:
            problems.append(f"projection {name!r}: unknown op {op!r}")
        declared.add(name)

    # Run the parse projections for real. They are cheap, and it is the only way
    # to know whether a join key or a `where` field actually exists -- a join on
    # a field the parser never emits fails as KeyError('item') deep inside the
    # build, which names the key and not the mistake.
    produced: dict[str, set[str]] = {}
    if not problems:
        try:
            rows = oracle.project(fixture, spec.get("projections") or [])
            produced = {name: set(r[0]) if (r := list(v[:1])) else set()
                        for name, v in rows.items()}
        except Exception as exc:
            problems.append(f"projections do not run: {type(exc).__name__}: {exc}")

    # A parse that yields nothing is not a projection, it is a parser that does
    # not fit the document -- and every target reading it silently evaluates to
    # an empty set, which grades as a wrong answer rather than a broken task.
    for name, fields in produced.items():
        if not fields:
            problems.append(
                f"projection {name!r} produces no rows: the parser does not fit "
                f"that document. Available parsers: "
                f"{', '.join(sorted(oracle.REGISTRY))}")

    for proj in spec.get("projections") or []:
        if proj.get("op") != "join":
            continue
        key = proj.get("on")
        keys = list(key) if isinstance(key, (list, tuple)) else [key]
        for side in ("left", "right"):
            ref = proj.get(side)
            missing = [k for k in keys if k and isinstance(k, str) and k not in produced.get(ref, ())]
            if ref in produced and key and missing:
                problems.append(
                    f"projection {proj.get('as')!r}: joins on {key!r}, which "
                    f"{ref!r} does not produce. It has: "
                    f"{', '.join(sorted(produced[ref])) or '(no rows)'}")

    readable = declared | files

    # --- checks ---
    ids: set[str] = set()
    deliverables: set[str] = set()
    for check in spec.get("checks") or []:
        cid = check.get("id", "<unnamed>")
        if cid in ids:
            problems.append(f"check {cid!r}: declared twice")
        ids.add(cid)
        if check.get("assertion") not in ASSERTIONS:
            problems.append(f"check {cid!r}: unknown assertion "
                            f"{check.get('assertion')!r}")
        if not (check.get("basis") or "").strip():
            problems.append(f"check {cid!r}: no public wording in 'basis'")
        if check.get("kind") == "guardrail" and check.get("requires"):
            problems.append(f"check {cid!r}: guardrails are never gated")
        if check.get("assertion") == "fixture_intact":
            continue
        actual = check.get("actual")
        if not isinstance(actual, dict):
            problems.append(f"check {cid!r}: no 'actual' expression")
        else:
            if actual.get("op") == "field" and actual.get("file"):
                deliverables.add(actual["file"])
            for operand in ("of", "a", "b"):
                if operand in actual:
                    _walk(actual[operand], f"check {cid}.actual.{operand}",
                          deliverables | {actual.get("file", "")}, problems)
            if actual.get("op") not in OPERANDS and actual.get("op") != "literal":
                problems.append(f"check {cid!r}: actual has unknown op "
                                f"{actual.get('op')!r}")
            # The reference solution is computed by writing each target into its
            # check's `actual` location, which only works for a field read. Any
            # other shape produces a solution that silently omits the check, and
            # the bundle then fails its own golden probe.
            elif check.get("kind") == "objective" and actual.get("op") != "field":
                problems.append(
                    f"check {cid!r}: an objective's `actual` must be "
                    "{op: field, file, path} -- a read of one field from the "
                    "deliverable. Aggregate inside `target` instead.")
            elif check.get("kind") == "objective" and not actual.get("path"):
                problems.append(f"check {cid!r}: actual needs a 'path' into the "
                                "deliverable")
        if check.get("assertion") == "matches":
            import re as _re
            pattern = (check.get("target") or {}).get("value")
            if isinstance(pattern, str):
                try:
                    _re.compile(pattern)
                except _re.error as exc:
                    problems.append(
                        f"check {cid!r}: `matches` target is not a valid regular "
                        f"expression ({exc}). Escape any literal brackets.")
        if check.get("target") is not None:
            if check.get("assertion") not in _VALUE_ASSERTIONS:
                _PATTERN_TARGETS.add(f"check {cid}.target")
            _walk(check["target"], f"check {cid}.target", readable, problems)
            _PATTERN_TARGETS.discard(f"check {cid}.target")
        elif check.get("assertion") not in ("present", "absent"):
            problems.append(f"check {cid!r}: assertion "
                            f"{check.get('assertion')!r} needs a target")

    # Two checks writing to overlapping paths in the same deliverable silently
    # clobber each other when the reference solution is assembled: a check on
    # `a` overwrites the object a check on `a.b` just built, and the second
    # check then fails against a solution that looked correct when written.
    written: dict[tuple[str, str], str] = {}
    for check in spec.get("checks") or []:
        actual = check.get("actual") or {}
        if actual.get("op") != "field" or check.get("kind") != "objective":
            continue
        key = (actual.get("file", ""), actual.get("path", ""))
        if key in written:
            problems.append(
                f"check {check.get('id')!r} writes the same field as "
                f"{written[key]!r} ({key[0]}:{key[1]}); give each check its own "
                "field")
        written[key] = check.get("id", "?")
    paths = sorted(written, key=lambda k: (k[0], k[1]))
    for i, (file_a, path_a) in enumerate(paths):
        for file_b, path_b in paths[i + 1:]:
            if file_a != file_b or not path_a or not path_b:
                continue
            if path_b.startswith(path_a + "."):
                problems.append(
                    f"check {written[(file_a, path_a)]!r} writes {path_a!r} and "
                    f"{written[(file_b, path_b)]!r} writes {path_b!r} in "
                    f"{file_a}; the shorter path overwrites the longer one. Use "
                    "sibling fields, not nested ones.")

    for check in spec.get("checks") or []:
        for dep in check.get("requires") or []:
            if dep not in ids:
                problems.append(
                    f"check {check.get('id')!r}: requires {dep!r}, which is not a "
                    "declared check")

    if not any(c.get("kind") == "guardrail" for c in spec.get("checks") or []):
        problems.append("no guardrail declared; a task with no negative space "
                        "measures only what the agent does, never what it breaks")

    # --- traps ---
    # The schema marks `traps` required, but a tool call can still come back
    # without it, and `build` then raises KeyError('traps') three stages later
    # -- an opaque crash where a repairable design problem belongs. A task with
    # no traps also passes `trap.faithful` and `trap.beatable` vacuously, which
    # is the "unprobed surface reads as a clean one" failure this pipeline
    # exists to prevent.
    if not (spec.get("traps") or []):
        problems.append(
            "no traps declared. Every task needs at least one trap: the "
            "specific wrong turn a competent practitioner would take here, "
            "grounded in the trace or in a fixture surface. Without one the "
            "trap gates pass by having nothing to check.")

    # `golden` is the reference; `untidy_correct` is the reference reformatted
    # and must also score 1.0, or the grader is punishing formatting.
    for raw in spec.get("traps") or []:
        try:
            problems.extend(Trap(**{k: v for k, v in raw.items()
                                    if k in Trap.__dataclass_fields__}).validate())
        except TypeError as exc:
            problems.append(f"trap {raw.get('id')!r}: malformed ({exc})")
    for trap in spec.get("traps") or []:
        tid = trap.get("id", "<unnamed>")
        for cid in trap.get("checks") or []:
            if cid not in ids:
                problems.append(
                    f"trap {tid!r}: drives check {cid!r}, which is not declared")
        if not trap.get("checks"):
            problems.append(f"trap {tid!r}: drives no check, so it cannot affect "
                            "a score")
        # A trap is demonstrated by a probe that scores BELOW the reference.
        # Two of the standard probes structurally cannot: `golden` is the
        # reference itself, and `untidy_correct` is the reference reformatted,
        # which the grader is required to accept. Naming either one means the
        # trap can never be shown to catch anything -- `trap.beatable` blocks
        # it after the bundle is built, which costs a whole rebuild. Caught
        # here it costs one repair round-trip.
        if trap.get("probe") in UNDEMONSTRATING_PROBES:
            problems.append(
                f"trap {tid!r}: probe {trap.get('probe')!r} always scores the "
                "same as the reference, so it can never demonstrate this trap. "
                "Use 'plausible_wrong', 'destructive', 'answer_lookup', or a "
                "trap-specific probe.")
        if trap.get("provenance") == "authored":
            if trap.get("grounded_in") not in files:
                problems.append(
                    f"trap {tid!r}: grounded_in {trap.get('grounded_in')!r} is not "
                    "a fixture file")
            if not (trap.get("grounding") or "").strip():
                problems.append(f"trap {tid!r}: authored trap needs 'grounding'")
        elif trap.get("provenance") == "trace_derived":
            if not (trap.get("derived_from") or "").strip():
                problems.append(f"trap {tid!r}: trace_derived trap needs a "
                                "'derived_from' citation")
            if not (trap.get("quote") or "").strip():
                problems.append(f"trap {tid!r}: trace_derived trap needs the "
                                "user's words in 'quote'")

    # --- instruction ---
    # Each deliverable must be named by the instruction of the step that owns
    # it. Step 2's file belongs in step 2's instruction: requiring it in step
    # 1's would force every two-step task to reveal its second step early.
    second = spec.get("second_step") if isinstance(spec.get("second_step"), dict) else {}
    owners = {s.get("deliverable_file"): s.get("instruction") or ""
              for s in spec.get("steps") or [] if isinstance(s, dict) and s.get("deliverable_file")}
    if spec.get("deliverable_file"):
        owners[spec["deliverable_file"]] = spec.get("instruction") or ""
    if second.get("deliverable_file"):
        owners[second["deliverable_file"]] = second.get("instruction") or ""
    every = " ".join([spec.get("instruction") or "", second.get("instruction") or "",
                      *(s.get("instruction") or "" for s in spec.get("steps") or [] if isinstance(s, dict))])
    for name in deliverables:
        if name not in owners.get(name, every):
            problems.append(
                f"instruction never names the deliverable {name!r} that checks "
                "read; the agent cannot know where to write")
    problems.extend(_gating_concentration(spec))
    problems.extend(_scoring_shape(spec))
    problems.extend(_second_step(spec))
    # The published contract: fields defined, references real, rules stated.
    # Only production specs (with output schemas) carry a contract to check.
    if isinstance(spec.get("outputs"), list) and spec.get("outputs"):
        problems.extend(_field_definitions(spec, bundle))
        problems.extend(_references(spec, bundle))
        problems.extend(_hidden_rules(spec, bundle))
        problems.extend(_order_rules(spec))
        problems.extend(_unordered_contract(spec))
        problems.extend(_guard_shape(spec))
        problems.extend(_history_references(spec))
        problems.extend(_literal_consistency(spec, bundle))
    # The premise map (Arena 261013 / spec 10_12, `author.premises`): a map that
    # misstates the grader blocks ("premise map: ..."); the conjunctive design
    # targets -- premise count and share, free share, family distinctness, the
    # timestamp cap -- are advisories ("premise shape: ..."). A production spec
    # with no map gets one advisory, so older bundles validate as before.
    from . import premises
    if (isinstance(spec.get("outputs"), list) and spec.get("outputs")) or premises.raw_map(spec) is not None:
        problems.extend(premises.problems(spec, bundle))
    return problems


def _second_step(spec: dict) -> list[str]:
    """A second graded step must be a second DECISION, not more of the same.

    Two steps over one set of documents is the cheapest way to build a harder
    task -- but only when step 2 introduces something step 1 could not have
    known and asks whether the earlier decision survives it. A step 2 that
    repeats step 1's work doubles the cost and measures the same thing twice.
    """
    # A `step` naming no declared step is silently folded into step 1 by the
    # build, so a question the agent has not been asked yet gets graded against
    # the first attempt. Check this whether or not a second step was declared.
    declared = {s.get("name") for s in (spec.get("steps") or []) if s.get("name")}
    problems = []
    if declared:
        for c in spec.get("checks") or []:
            if not isinstance(c, dict):
                continue
            named = c.get("step")
            if named and named not in declared:
                problems.append(
                    f"check {c.get('id')!r} is assigned to step {named!r}, "
                    f"which is not declared (steps: {sorted(declared)}). It "
                    "would be graded in the first step instead.")

    second = spec.get("second_step")
    # Batch step shape (user 2026-10-05: ~15% of a batch two-step, the rest
    # single-step). The operator sets ARENA_STEP_SHAPE per build shard; unset
    # leaves the designer free, as before.
    shape = os.environ.get("ARENA_STEP_SHAPE", "").strip().lower()
    multi = bool(second) or len(declared) >= 2
    if shape == "single" and multi:
        problems.append(
            "this batch slot is SINGLE-STEP (ARENA_STEP_SHAPE=single): remove "
            "second_step and any second entry in `steps`; put every graded "
            "decision in the one step")
    elif shape == "two" and not multi:
        problems.append(
            "this batch slot is TWO-STEP (ARENA_STEP_SHAPE=two): declare "
            "second_step (or a two-entry `steps` contract) with its own "
            "deliverable and graded checks")
    if not second:
        return problems                 # optional; most seeds carry only one
    if not isinstance(second, dict):
        return ["second_step must be an object with instruction, "
                "deliverable_file and new_information"]

    instruction = (second.get("instruction") or "").strip()
    deliverable = (second.get("deliverable_file") or "").strip()
    revealed = (second.get("new_information") or "").strip()

    if len(instruction) < 80:
        problems.append("second_step.instruction is too short to state new "
                        "information and what to do with it")
    if not deliverable:
        problems.append("second_step needs its own deliverable_file")
    elif deliverable == (spec.get("deliverable_file") or "").strip():
        problems.append(
            f"second_step writes to {deliverable!r}, the same file as step 1. "
            "Step 2 records what CHANGED; overwriting step 1's answer destroys "
            "the evidence that the decision was revised.")
    if len(revealed) < 30:
        problems.append(
            "second_step.new_information must say, in a sentence, what step 2 "
            "reveals that step 1 could not have known and which earlier "
            "decision it puts in doubt. Without that this is a longer task, "
            "not a harder one.")

    # Step 2 has to be scored, or it is unassessed prose.
    steps = [s.get("name") for s in (spec.get("steps") or [])]
    if len(steps) >= 2:
        second_name = steps[1]
        scored = [c for c in (spec.get("checks") or [])
                  if isinstance(c, dict) and c.get("kind") == "objective"
                  and c.get("step") == second_name]
        if not scored:
            problems.append(
                f"no objective check is assigned to step {second_name!r}; a "
                "graded step with no checks is not graded. Set `step` on the "
                "checks that score the revision.")
    return problems


#: The objective floor is `policy.MIN_OBJECTIVES` (8 since 2026-09-25): every
#: task carries at least that many graded checks, each one demonstrably able to
#: fail a plausible wrong answer. Guardrail quotas still encourage copying
#: filler and cannot establish informativeness, so they have no floor here.
from ..policy import MIN_OBJECTIVES

#: No single scored check may exceed this share. Above it the task is mostly
#: one question wearing a rubric.
MAX_SINGLE_WEIGHT_SHARE = 0.35


def _scoring_shape(spec: dict) -> list[str]:
    """Enough checks, weights that differ, and every weight argued for."""
    checks = [c for c in (spec.get("checks") or []) if isinstance(c, dict)]
    scored = [c for c in checks if c.get("kind") == "objective"]
    problems = []

    if len(scored) < MIN_OBJECTIVES:
        problems.append(
            f"{len(scored)} objective checks; at least {MIN_OBJECTIVES} are "
            "required per task, every one a genuine check a plausible wrong "
            "answer fails. Extra output fields do not establish independent "
            "decisions, and a check that cannot fail is not a check.")
    total = sum(c.get("weight", 0) or 0 for c in scored)
    if total <= 0:
        return problems

    # Uniform weights assert that every check matters equally, which is almost
    # never true and is how an incidental detail comes to outweigh the answer.
    distinct = {c.get("weight") for c in scored}
    if len(scored) >= 3 and len(distinct) == 1:
        problems.append(
            f"every objective carries weight {distinct.pop()}; weights must "
            "reflect importance. Rank the checks by what the practitioner "
            "actually cared about and size them accordingly.")
    elif len(scored) >= 6 and len(distinct) < 3:
        problems.append(
            f"{len(scored)} objectives share only {len(distinct)} distinct "
            "weights; that is not a ranking, it is two buckets.")

    # The share that counts is the one the grader applies: per step, then the
    # step mean. A lone heavy check in a small second step carries far more of
    # the task than its raw weight suggests.
    effective = _effective_shares(spec) or {}
    for c in scored:
        cid = c.get("id", "<unnamed>")
        share = effective.get(cid, (c.get("weight", 0) or 0) / total)
        if share > MAX_SINGLE_WEIGHT_SHARE:
            problems.append(
                f"check {cid!r} carries {share:.0%} of the task reward as graded, above "
                f"{MAX_SINGLE_WEIGHT_SHARE:.0%}. One check deciding a third of "
                "the score makes the rest decorative.")
        reason = (c.get("weight_basis") or "").strip()
        if len(reason) < 25:
            problems.append(
                f"check {cid!r}: weight {c.get('weight')} has no reasoned basis. "
                "Give one sentence citing the evidence -- the correction it "
                "comes from, the share of the deliverable it covers, or what "
                "breaks if it is wrong. A weight nobody can defend is a weight "
                "nobody can review.")
        elif reason.lower().strip(" .") in {"important", "very important",
                                            "this is important", "key check"}:
            problems.append(
                f"check {cid!r}: 'important' is not a justification for a weight.")

    # Guardrails protect; they do not score. A weighted guardrail double-counts.
    for c in checks:
        if c.get("kind") == "guardrail" and (c.get("weight", 0) or 0) > 0:
            problems.append(
                f"guardrail {c.get('id')!r} carries weight {c.get('weight')}; "
                "guardrails must be weight 0 -- they gate the task, they are not "
                "part of the score.")
    return problems


#: Most weight one check may gate, itself included. Above this the task has a
#: single point of collapse: everyone clears it and that weight is free, or
#: everyone misses it and the weight cannot be attempted at all. Either way the
#: reported rate is computed over a small reachable set and two models look
#: identical. Measured on this batch: kw-a006 concentrates 51% behind one check
#: and kw-a011 40%, and both calibrated to an inter-model spread of exactly
#: 0.000; the new kw-a010 concentrates 31% and left 4 of 14 checks never
#: attempted at a mean of 0.033.
MAX_GATED_WEIGHT_SHARE = 0.30


def _gating_concentration(spec: dict) -> list[str]:
    """Refuse a `requires` graph that puts too much of the score on one check."""
    checks = [c for c in (spec.get("checks") or []) if isinstance(c, dict)]
    total = sum(c.get("weight", 0) or 0 for c in checks)
    if total <= 0:
        return []
    weight = {c.get("id"): (c.get("weight", 0) or 0) for c in checks}

    def dependants(root: str) -> set:
        seen, frontier = set(), [root]
        while frontier:
            current = frontier.pop()
            for c in checks:
                cid = c.get("id")
                if cid in seen or cid == root:
                    continue
                if current in (c.get("requires") or []):
                    seen.add(cid); frontier.append(cid)
        return seen

    problems = []
    effective = _effective_shares(spec)
    for c in checks:
        cid = c.get("id")
        if not cid:
            continue
        blocked = dependants(cid)
        if not blocked:
            # Nothing depends on it, so it gates nothing. A single heavy check
            # is a weight-concentration question, not a `requires` one, and
            # conflating them flags every well-formed two-check task.
            continue
        if effective:
            share = sum(effective.get(d, 0.0) for d in blocked | {cid})
        else:
            share = (sum(weight.get(d, 0) for d in blocked) + weight.get(cid, 0)) / total
        if share > MAX_GATED_WEIGHT_SHARE:
            problems.append(
                f"check {cid!r} gates {share:.0%} of the task weight through "
                f"`requires` ({sorted(blocked)}) -- above "
                f"{MAX_GATED_WEIGHT_SHARE:.0%}, one check decides most of the "
                "score and the task stops separating attempts. Shorten the "
                "chain or move weight off it.")
    return problems


# --------------------------------------------------------------------------
# The published task contract (Arena spec, Tasks: "Define the objective, inputs,
# output paths, schemas, field meanings ... Verify that every referenced path
# and command exists. ... Any special handling that affects grading must be
# explained in the instructions."). Each rule below reads only the spec and the
# fixture, so a draft is refused before anything is built or paid for.
# --------------------------------------------------------------------------

import re as _re
from copy import deepcopy as _deepcopy

try:                                    # stdlib regex parser; 3.11+ spelling
    import re._parser as _sre           # type: ignore[import-not-found]
except ImportError:                     # pragma: no cover - older interpreters
    import sre_parse as _sre            # type: ignore[no-redef]

_STOP = frozenset("""
a an the and or but if then than that this those these is are was were be been being
of in on at to for from with without by as it its into over under no not must may can
each every all any some one two other same only also do does did have has had nothing
else exactly their there which who what when where how here per you your write
""".split())
_WORD = _re.compile(r"[^\W\d_]{3,}")
_CJK = _re.compile(r"[぀-ヿ㐀-鿿가-힯豈-﫿]")

#: Content words a definition needs beyond the field's own name (a CJK
#: character counts half). "`stage` (the 序 value as an integer)" clears it;
#: "`start_slip`, `milestone_and_buffer_readiness` -- and nothing else" does not.
MIN_DEFINITION_WORDS = 2


def _compiled(spec: dict):
    """(steps, outputs, checks) with step names resolved, or None if the step
    contract itself is invalid (production_problems reports that)."""
    from .contracts import ContractError, compile_steps
    copy = _deepcopy(spec)
    try:
        steps = compile_steps(copy)
    except (ContractError, KeyError, TypeError, AttributeError, ValueError):
        return None
    return steps, [o for o in copy.get("outputs") or [] if isinstance(o, dict)], \
        [c for c in copy.get("checks") or [] if isinstance(c, dict)]


def _schema_fields(schema, trail: str = ""):
    """(name, path, is_leaf, schema) for every declared property at any depth."""
    if not isinstance(schema, dict):
        return
    if schema.get("type") == "object":
        for key, sub in (schema.get("properties") or {}).items():
            path = f"{trail}.{key}" if trail else key
            sub = sub if isinstance(sub, dict) else {}
            kind = sub.get("type")
            container = kind == "object" or (
                kind == "array" and (sub.get("items") or {}).get("type") == "object")
            yield key, path, not container, sub
            yield from _schema_fields(sub, path)
    elif schema.get("type") == "array":
        yield from _schema_fields(schema.get("items"), trail + "[]")


def _meaning(text: str, names: set[str]) -> float:
    """Content-word weight of `text`, ignoring other field names."""
    text = _re.sub(r"`([^`\n]*)`", lambda m: " " if m.group(1) in names else f" {m.group(1)} ", text)
    cjk = len(_CJK.findall(text))
    words = [w for w in _WORD.findall(_CJK.sub(" ", text).lower()) if w not in _STOP]
    return len(words) + cjk / 2


def _occurrences(text: str, name: str) -> list[tuple[int, int]]:
    """Where the instruction names a field: in backticks (alone or as a dotted
    segment), in double quotes, or bare when the name cannot be a common word."""
    spans = []
    for m in _re.finditer(r"`([^`\n]{1,160})`", text):
        if name in _re.split(r"[.\[\]\s]+", m.group(1)):
            spans.append((m.start(), m.end()))
    for m in _re.finditer(r'"' + _re.escape(name) + r'"', text):
        spans.append((m.start(), m.end()))
    if _re.search(r"[_\d]|[^\x00-\x7f]", name):
        for m in _re.finditer(r"(?<![\w`\"])" + _re.escape(name) + r"(?![\w`\"])", text):
            spans.append((m.start(), m.end()))
    return sorted(set(spans))


_GROUP_GAP = _re.compile(r"^[\s,/&、|]*(?:(?:and|or|и|или|及|和|與|或)[\s,/&、|]*)?$", _re.I)


def _starts_definition(text: str, start: int) -> bool:
    """Whether a backticked field name at `start` opens a new definition."""
    before = text[max(0, start - 6):start]
    stripped = text[:start].rstrip(" \t")
    if not stripped or stripped.endswith("\n"):
        return True
    return bool(_re.search(r"(?:^|\n)\s*(?:[-*\u2022]|\d+[.)])\s*$", text[max(0, start - 12):start])
                or _re.search(r"[.;:!?]\s*$", before))


def _definition_windows(text: str, name: str, names: set[str]) -> list[tuple[str, str]]:
    """(window, paragraph) for each occurrence of `name` followed by a meaning.

    The window runs from the name to the next field name, paragraph break or
    400 characters, whichever comes first -- so a list of keys defines nothing,
    and each field has to earn its own words. A group that shares one
    definition ("`start` and `end` (the two dates of the window)") is read as
    one: the gap between grouped names may hold only separators, never a full
    stop, so "`workdays`. `elapsed_days` is ..." does not lend `workdays` the
    next field's meaning."""
    stops = [(m.start(), m.end()) for m in _re.finditer(r"`[^`\n]*`", text)
             if set(_re.split(r"[.\[\]\s]+", m.group(0).strip("`"))) & names]
    out = []
    for start, end in _occurrences(text, name):
        cursor = end
        for _ in range(8):
            nxt = next(((s, e) for s, e in stops if s >= cursor), None)
            if nxt is None or not _GROUP_GAP.match(text[cursor:nxt[0]]):
                break
            cursor = nxt[1]
        brk = _re.search(r"\n\s*\n", text[cursor:])
        limit = min(cursor + 400, cursor + brk.start() if brk else len(text))
        # Another field's name ends this definition only where a NEW definition
        # starts -- a line or bullet start, or after a sentence break. A name
        # referenced mid-sentence ("a list of `pedido` values ...") is part of
        # this field's meaning (a-032, 2026-10-02).
        nxt = next((s for s, _ in stops if s >= cursor and _starts_definition(text, s)), None)
        if nxt is not None:
            limit = min(limit, nxt)
        window = text[cursor:limit]
        if _meaning(window, names) >= MIN_DEFINITION_WORDS:
            para_start = max(text.rfind("\n\n", 0, start), 0)
            para_brk = _re.search(r"\n\s*\n", text[cursor:])
            para_end = cursor + para_brk.start() if para_brk else len(text)
            out.append((window, text[para_start:para_end]))
    return out


def _fixture_entities(bundle: Path) -> tuple[set[str], str]:
    """(file names and stems, concatenated text) of the fixture: a schema key
    that IS one of these is an entity key (one entry per document, per token),
    defined by its parent's definition rather than individually."""
    fixture = bundle / "environment" / "files"
    names: set[str] = set()
    chunks: list[str] = []
    if fixture.is_dir():
        for path in sorted(fixture.rglob("*")):
            if not path.is_file():
                continue
            names.update({path.name, path.stem})
            if path.stat().st_size <= 2_000_000:
                try:
                    chunks.append(path.read_text(errors="replace"))
                except OSError:
                    continue
    return names, "\n".join(chunks)


def _step_text(steps: list[dict]) -> dict[str, str]:
    return {s["name"]: s.get("instruction") or "" for s in steps}


def _field_definitions(spec: dict, bundle: Path | None = None) -> list[str]:
    """[T1] Every field a step's schema requires is named, and every leaf is
    given a meaning, in that step's own instruction.

    Arena's kw006 handover required `occurrence` without defining how to compute
    it. A schema says a field exists and what type it is; only the instruction
    can say what it means, and the agent is graded on the meaning."""
    compiled = _compiled(spec)
    if compiled is None:
        return []
    steps, outputs, _ = compiled
    texts = _step_text(steps)
    entity_names, entity_text = _fixture_entities(bundle) if bundle else (set(), "")
    problems = []
    for output in outputs:
        step, schema = output.get("step"), output.get("schema")
        text = texts.get(step, "")
        fields = list(_schema_fields(schema))
        names = {name for name, *_ in fields}
        seen: set[str] = set()
        for name, path, leaf, sub in fields:
            if name in seen:
                continue
            seen.add(name)
            described = _meaning(str(sub.get("description") or ""), names) >= MIN_DEFINITION_WORDS
            if not _occurrences(text, name) and not described:
                problems.append(
                    f"{output.get('file')}: field {path!r} is never named in step {step!r}'s "
                    "instruction. Name every field the schema requires, in backticks, and say "
                    "what it holds -- the agent cannot produce a field it was never told about")
            elif leaf and not described and not _definition_windows(text, name, names) \
                    and not _entity_key(name, path, text, names, entity_names, entity_text):
                problems.append(
                    f"{output.get('file')}: field {path!r} is named but never defined in step "
                    f"{step!r}'s instruction. Follow the name with what the value IS and its exact "
                    "format (Arena kw006: a required field without semantics is ambiguous)")
    return problems


def _entity_key(name: str, path: str, text: str, names: set[str],
                entity_names: set[str], entity_text: str) -> bool:
    """A key named after a fixture entity -- a document stem, a palette token --
    whose parent object the instruction defines. Its meaning is the parent's
    ("per document, the ..."), so it needs no sentence of its own."""
    parent = _re.split(r"[.\[\]]+", path.rsplit(".", 1)[0])[-1] if "." in path else ""
    if not parent or parent == name:
        return False
    variants = {name, name.replace("_", " "), name.replace("_", "-")}
    if not (variants & entity_names or any(v in entity_text for v in variants)):
        return False
    return bool(_definition_windows(text, parent, names))


# --- [T2] referenced files and commands ---------------------------------------

_EXTENSIONS = ("md", "markdown", "json", "jsonl", "csv", "tsv", "txt", "xlsx", "xlsm", "xls",
               "docx", "doc", "pdf", "pptx", "ppt", "png", "jpg", "jpeg", "gif", "svg", "html",
               "htm", "xml", "yaml", "yml", "toml", "sh", "py", "js", "ts", "zip", "sql",
               "ipynb", "log", "odt", "ods", "rtf", "epub", "tex", "bib")
_FILE_LIKE = _re.compile(r"^[^\s*?<>|]+\.(?:" + "|".join(_EXTENSIONS) + r")$", _re.I)

#: What `python:3.x-slim-bookworm` (every generated agent image) carries.
BASE_IMAGE_TOOLS = frozenset("""
python python3 pip pip3 bash sh dash ls cat grep egrep fgrep sed awk mawk head tail sort
uniq wc cut tr find xargs diff cmp cp mv rm mkdir rmdir touch echo printf test env tee
date du df tar gzip gunzip zcat sha256sum md5sum comm join paste split csplit expand fold
fmt nl od basename dirname realpath readlink stat chmod pwd true false sleep seq iconv perl
more which cd export
""".split())

#: Names that read as a command when they open a backticked span. A span
#: naming one of these that the image does not install is a tool the agent
#: will reach for and not find.
KNOWN_TOOLS = BASE_IMAGE_TOOLS | frozenset("""
jq yq pandoc pdftotext pdfinfo pdftoppm soffice libreoffice sqlite3 psql mysql docker make
gcc java javac ruby Rscript convert magick identify ffmpeg ffprobe tesseract unzip zip
xmllint rg bc csvlook csvcut csvgrep csvstat in2csv xlsx2csv harbor pytest pipx uv go cargo
node npm npx git curl wget tmux latex pdflatex xelatex lualatex bibtex biber vale aspell
hunspell markdownlint
""".split())

_PACKAGE_BINARIES = {
    "poppler-utils": ("pdftotext", "pdfinfo", "pdftoppm"), "libreoffice": ("soffice", "libreoffice"),
    "libreoffice-core": ("soffice",), "libreoffice-writer": ("soffice",),
    "libreoffice-calc": ("soffice",), "imagemagick": ("convert", "magick", "identify"),
    "ripgrep": ("rg",), "libxml2-utils": ("xmllint",), "tesseract-ocr": ("tesseract",),
    "ffmpeg": ("ffmpeg", "ffprobe"), "nodejs": ("node",), "npm": ("npm", "npx"),
    "csvkit": ("csvlook", "csvcut", "csvgrep", "csvstat", "in2csv"),
    "texlive": ("latex", "pdflatex"), "texlive-xetex": ("xelatex",), "sqlite3": ("sqlite3",),
}


def image_tools(bundle: Path) -> set[str]:
    """Commands the agent image provides: the slim base plus what its
    Dockerfile installs with apt-get or pip."""
    tools = set(BASE_IMAGE_TOOLS)
    dockerfile = bundle / "environment" / "Dockerfile"
    try:
        text = dockerfile.read_text()
    except OSError:
        return tools
    for m in _re.finditer(r"(?:apt-get|apt)\s+install([^&;\n]*)", text):
        for token in m.group(1).split():
            if token.startswith("-"):
                continue
            package = token.split("=", 1)[0]
            tools.add(package)
            tools.update(_PACKAGE_BINARIES.get(package, ()))
    for m in _re.finditer(r"pip3?\s+install([^&;\n]*)", text):
        for token in m.group(1).split():
            if not token.startswith("-"):
                package = _re.split(r"[=<>\[]", token, maxsplit=1)[0].lower()
                tools.update(_PACKAGE_BINARIES.get(package, (package,)))
    return tools


def _references(spec: dict, bundle: Path) -> list[str]:
    """[T2] Every file or command an instruction names exists for the agent.

    A backticked span that looks like a file must be a fixture file or a
    declared deliverable; an absolute path must sit under the input or output
    root; a command must be installed in the agent image. An instruction that
    sends the agent to a quote sheet that was never lifted, or tells it to run
    a validator nobody shipped, manufactures a failure the agent cannot avoid."""
    from .contracts import INPUT_ROOT, OUTPUT_ROOT
    compiled = _compiled(spec)
    if compiled is None:
        return []
    steps, outputs, _ = compiled
    fixture = bundle / "environment" / "files"
    files = {p.relative_to(fixture).as_posix() for p in fixture.rglob("*") if p.is_file()} \
        if fixture.is_dir() else set()
    dirs = {p.relative_to(fixture).as_posix() for p in fixture.rglob("*") if p.is_dir()} \
        if fixture.is_dir() else set()
    basenames = {Path(f).name for f in files}
    declared = {o.get("file") for o in outputs if o.get("file")}
    fields = {name for o in outputs for name, *_ in _schema_fields(o.get("schema"))}
    tools = image_tools(bundle)
    problems: list[str] = []

    def path_problem(ref: str) -> str | None:
        ref = ref.rstrip("/.,;:")
        if _re.search(r"[<>{}*]", ref):
            return None             # a placeholder such as /app/deliverables/<file>
        for root in (INPUT_ROOT, "environment/files"):
            if ref == root:
                return None
            if ref.startswith(root + "/"):
                rel = ref[len(root) + 1:]
                return None if rel in files or rel in dirs else f"{ref!r} is not in the fixture"
        if ref == OUTPUT_ROOT or ref == "/app" or ref == "/tmp" or ref.startswith("/tmp/"):
            return None
        if ref.startswith(OUTPUT_ROOT + "/"):
            rel = ref[len(OUTPUT_ROOT) + 1:]
            return None if rel in declared else f"{ref!r} is not a declared deliverable"
        if ref.startswith("/"):
            return f"{ref!r} does not exist in the agent image"
        rel = ref[2:] if ref.startswith("./") else ref
        if rel in files or rel in declared or rel in dirs or Path(rel).name in basenames \
                or Path(rel).name in declared:
            return None
        return f"{ref!r} is neither a fixture file nor a declared deliverable"

    for step in steps:
        text = step.get("instruction") or ""
        found: list[str] = []
        for m in _re.finditer(r"`([^`\n]{1,200})`", text):
            span = m.group(1).strip()
            # Patterns, not references: globs, placeholders, bare punctuation
            # (`/`, `//`), and suffixes such as `-clean.md` or `.md`.
            if (not span or "*" in span or "<" in span or "{" in span
                    or not _re.search(r"\w", span)
                    or (span[0] in "-." and not span.startswith(("./", "../")))):
                continue
            words = span.split()
            head = words[0]
            if len(words) > 1:
                if head.startswith(("./", "/")) or head in KNOWN_TOOLS:
                    if head.startswith(("./", "/")):
                        issue = path_problem(head)
                        if issue:
                            found.append(f"command `{span}`: {issue}")
                    elif head not in tools:
                        found.append(f"command `{span}`: {head!r} is not installed in the agent image")
                    for arg in words[1:]:
                        if _FILE_LIKE.match(arg) or arg.startswith(("./", "/app/")):
                            issue = path_problem(arg)
                            if issue:
                                found.append(f"command `{span}`: {issue}")
                continue
            if span in fields:
                continue
            if _FILE_LIKE.match(span) or span.startswith(("/", "./", "../")):
                issue = path_problem(span)
                if issue:
                    found.append(issue)
            elif span in KNOWN_TOOLS and span not in tools and len(span) > 2:
                found.append(f"tool `{span}` is not installed in the agent image")
        for m in _re.finditer(r"(?<![\w`/])(/app(?:/[^\s`'\"),;]*)?)", text):
            issue = path_problem(m.group(1))
            if issue:
                found.append(issue)
        for issue in dict.fromkeys(found):
            problems.append(
                f"step {step['name']!r} instruction references {issue}. Every referenced path "
                "and command must exist (Arena spec, Tasks): lift the file into the fixture, "
                "install the tool in environment/Dockerfile, or stop referring to it")
    return problems


# --- [T3/G3] no hidden rules --------------------------------------------------

#: Row fields that select WHICH table or section a projection row came from.
#: The instruction identifies the table in prose ("the table in chapter 二"),
#: never by the parser's index, so these clauses need no quote.
STRUCTURAL_FIELDS = frozenset({"_table", "level", "index", "svg_index", "empty"})
#: Parser-emitted field names (see `oracle`). The name is an artefact and need
#: not be quoted, but any value or pattern the clause tests still must be.
METADATA_FIELDS = frozenset({"_row", "_file", "heading", "section_heading", "text", "number",
                             "line", "label", "value", "item", "answer", "stem", "options",
                             "words", "row", "source", "stems", "shared", "tag", "attributes",
                             "ancestors"})
MIN_RULE_QUOTE = 12
#: A quote is a sentence or a bullet, not the instruction. Longer quotes make a
#: coincidental co-occurrence of a field name and a literal cheap to find.
MAX_RULE_QUOTE = 600


def _norm(text: str) -> str:
    return " ".join(str(text).replace("’", "'").split()).lower()


def _regex_literals(pattern: str) -> tuple[list[str], list[str]]:
    """(required, excluded) word literals of a regex: the words it looks for,
    and the words a negative lookahead rules out. Character-class ranges and
    escapes are not literals."""
    try:
        tree = _sre.parse(pattern)
    except Exception:
        return [], []
    runs: list[tuple[str, bool]] = []
    current: list[str] = []

    def flush(negated):
        if current:
            runs.append(("".join(current), negated))
            current.clear()

    def walk(seq, negated):
        for op, av in seq:
            name = str(op)
            if name == "LITERAL":
                current.append(chr(av))
                continue
            flush(negated)
            if name == "IN":
                runs.extend((chr(v), negated) for o, v in av if str(o) == "LITERAL")
            elif name == "SUBPATTERN":
                walk(av[-1], negated)
            elif name in ("MAX_REPEAT", "MIN_REPEAT", "POSSESSIVE_REPEAT"):
                walk(av[2], negated)
            elif name == "BRANCH":
                for alternative in av[1]:
                    walk(alternative, negated)
                    flush(negated)
            elif name == "ASSERT":
                walk(av[1], negated)
            elif name == "ASSERT_NOT":
                walk(av[1], True)
            elif name == "ATOMIC_GROUP":
                walk(av, negated)
            flush(negated)
        flush(negated)

    walk(getattr(tree, "data", tree), False)
    required = [w for run, neg in runs if not neg for w in _re.findall(r"\w+", run)]
    excluded = [w for run, neg in runs if neg for w in _re.findall(r"\w+", run)]
    return required, excluded


def _literal_in(value: str, quote: str) -> bool:
    value = _norm(_re.sub(r"[*_`#]+", " ", str(value)))
    quote = _norm(_re.sub(r"[*_`#]+", " ", quote))
    if not value:
        return True
    if _re.fullmatch(r"[a-z0-9]+", value):
        return bool(_re.search(r"(?<![a-z0-9])" + _re.escape(value) + r"(?![a-z0-9])", quote))
    if value in quote:
        return True
    # A long label (a section heading, a row caption) is stated when most of
    # its words are: the instruction says "the Why This Rebrand? section" or
    # "why this rebrand", not the exact bytes. Short values must be verbatim.
    words = [w for w in _re.findall(r"\w+", value) if len(w) > 1 or _CJK.match(w)]
    if len(words) >= 3:
        found = sum(1 for w in words if _re.search(r"(?<!\w)" + _re.escape(w) + r"(?!\w)", quote))
        return found / len(words) >= 0.6
    return False


def _filter_clauses(expr, trail: str = "target"):
    """(where, clause) for every leaf clause of every row filter, every regex
    an expression applies, anywhere in a target."""
    if isinstance(expr, list):
        for i, item in enumerate(expr):
            yield from _filter_clauses(item, f"{trail}[{i}]")
        return
    if not isinstance(expr, dict):
        return
    for key, value in expr.items():
        if key == "where":
            yield from _leaf_clauses(value, f"{trail}.where")
        elif isinstance(value, (dict, list)):
            yield from _filter_clauses(value, f"{trail}.{key}")
    if expr.get("op") == "extract" and isinstance(expr.get("pattern"), str):
        # v2 witness mode: an `extract` pattern PARSES a value out of a
        # document (a number, a date, a label); it is not a grading rule, and
        # demanding a quoted sentence for it is what pushed parsing details
        # into the instruction (R4 B6). The co-occurrence mode keeps v1.
        from ..policy import HIDDEN_RULE_MODE
        if HIDDEN_RULE_MODE != "witness":
            yield trail, {"field": None, "matches": expr["pattern"]}


def _leaf_clauses(where, trail):
    if not isinstance(where, dict):
        return
    for group in ("all", "any"):
        if isinstance(where.get(group), list):
            for i, clause in enumerate(where[group]):
                yield from _leaf_clauses(clause, f"{trail}.{group}[{i}]")
            return
    if where:
        yield trail, where


def _computed_names(expr, out: set[str] | None = None) -> set[str]:
    """Row fields a target computes itself (derive_rows / bind_rows / record
    keys) and the label columns its concat projections add. Internal names:
    the agent is never told them, so only their literals need a quote."""
    out = set() if out is None else out
    if isinstance(expr, dict):
        if expr.get("op") in ("derive_rows", "bind_rows", "record") and isinstance(expr.get("fields"), dict):
            out.update(str(k) for k in expr["fields"])
        for value in expr.values():
            _computed_names(value, out)
    elif isinstance(expr, list):
        for value in expr:
            _computed_names(value, out)
    return out


def _clause_needs(clause: dict, internal: frozenset[str] | set[str] = frozenset(),
                  visible: str | None = None) -> tuple[str | None, list[str], list[str]]:
    """(column that must be named or None, literals that must all be stated,
    regex words of which most must be stated).

    A column must be named only when the agent can see it: a header or label
    that occurs in the fixture. A name the oracle invents (a parser field, a
    join alias, a computed flag) is invisible, so only the values the clause
    tests are the rule. Values a filter compares against, and words a
    negative lookahead excludes, are the rule itself and must all be stated;
    the words a positive regex looks for locate a value and must mostly be."""
    field = clause.get("field")
    if field in STRUCTURAL_FIELDS:
        return None, [], []
    name = None
    if (isinstance(field, str) and field not in METADATA_FIELDS and field not in internal
            and not field.startswith("_")):
        name = field.split(".")[-1]
        if visible is not None and name not in visible:
            name = None
    literals: list[str] = []
    located: list[str] = []
    for op, value in clause.items():
        if op == "field":
            continue
        if op == "matches" and isinstance(value, str):
            required, excluded = _regex_literals(value)
            literals += excluded
            located += required
        elif op in ("eq", "ne", "in", "not_in", "gt", "gte", "lt", "lte"):
            for item in (value if isinstance(value, list) else [value]):
                if isinstance(item, bool) or item is None:
                    continue
                if isinstance(item, (int, float)):
                    if item == 0 and op in ("gt", "gte", "lt", "lte"):
                        continue          # sign rules read as "positive"/"negative"
                    item = int(item) if float(item).is_integer() else item
                literals.append(str(item))
    return name, literals, located


def _matchers(terms: dict):
    def alias(token, q):
        words = terms.get(token)
        return isinstance(words, str) and len(_norm(words)) >= 3 and _norm(words) in q

    def named(field, q):
        return field is None or _norm(field) in q or alias(field, q)

    def stated(literal, q):
        return _literal_in(literal, q) or alias(literal, q)
    return named, stated


def clause_covered(name, literals, located, quote: str, terms: dict | None = None) -> bool:
    """Does one normalised quoted sentence state this clause?"""
    named, stated = _matchers(terms or {})
    q = _norm(quote)
    return (named(name, q) and all(stated(l, q) for l in literals)
            and _located(located, q, stated))


def _located(words: list[str], quote: str, stated) -> bool:
    words = list(dict.fromkeys(w for w in words if len(w) > 1 or _CJK.match(w)))
    if not words:
        return True
    return sum(1 for w in words if stated(w, quote)) * 2 >= len(words)


def _source_rule_quotes(check: dict, spec: dict, bundle: Path | None,
                        steps: list[dict]) -> tuple[list[str], list[str]]:
    """Exact public rule witnesses, excluding evidence locked in future steps."""
    from .contracts import contained
    from .step_files import withheld_from

    raw = check.get("rule_sources")
    if raw is None:
        return [], []
    where = f"check {check.get('id')!r}: rule_sources"
    if not isinstance(raw, list) or not raw:
        return [], [f"{where} must list fixture file/quote witnesses"]
    if bundle is None:
        return [], [f"{where} needs the fixture to verify public evidence"]
    withheld = set(withheld_from(spec, check.get("step"), [step["name"] for step in steps]))
    quotes, problems = [], []
    for index, entry in enumerate(raw):
        at = f"{where}[{index}]"
        if (not isinstance(entry, dict) or not isinstance(entry.get("file"), str)
                or not isinstance(entry.get("quote"), str)):
            problems.append(f"{at} needs a fixture file and exact quote")
            continue
        try:
            path = contained(bundle / "environment/files", entry["file"])
            relative = path.relative_to((bundle / "environment/files").resolve()).as_posix()
            text = path.read_text()
        except (OSError, ValueError, UnicodeError) as exc:
            problems.append(f"{at}: fixture rule is not readable ({exc})")
            continue
        quote = entry["quote"]
        normalized = _norm(quote)
        if relative in withheld:
            problems.append(f"{at}: {relative!r} is unavailable at step {check.get('step')!r}")
        elif not MIN_RULE_QUOTE <= len(normalized) <= MAX_RULE_QUOTE:
            problems.append(f"{at}: quote one rule sentence ({MIN_RULE_QUOTE}..{MAX_RULE_QUOTE} characters)")
        elif quote not in text:
            problems.append(f"{at}: quote is not verbatim in {relative!r}")
        else:
            quotes.append(normalized)
    return quotes, problems


def _hidden_rules(spec: dict, bundle: Path | None = None) -> list[str]:
    """[T3/G3] A row filter or regex in a target is a grading rule. It must be
    one the instruction or a step-available fixture states.

    Arena's kw006 grader used an unpublished page-existence rule to classify
    D0386; a `where` clause is exactly where such a rule lives in this shape.
    So every check whose target filters rows or applies a regex carries
    `rule_quote`: sentences copied from its step's instruction, or `rule_sources`:
    exact file/quote witnesses in step-available fixture documents. In either case
    each clause's field and every literal it tests (an `eq` value, the words a
    regex requires) must appear together in one of those sentences. A filter
    nobody can quote is a hidden rule.

    Lexical, like every published-rule check here: it proves the rule's words
    are in the instruction next to each other, not that they say the same
    thing. The quotes are written to basis.toml for the reviewer who decides."""
    compiled = _compiled(spec)
    if compiled is None:
        return []
    steps, _, checks = compiled
    texts = {name: _norm(text) for name, text in _step_text(steps).items()}
    # Names projections invent: a concat's document-label column and a join's
    # field aliases. Like computed fields, the agent never sees them.
    labels = {str(p.get("field", "source")) for p in spec.get("projections") or []
              if isinstance(p, dict) and p.get("op") == "concat"}
    labels |= {str(k) for p in spec.get("projections") or []
               if isinstance(p, dict) and p.get("op") == "join" and isinstance(p.get("fields"), dict)
               for k in p["fields"]}
    visible = _fixture_entities(bundle)[1] if bundle is not None else None
    visible_text = visible
    problems: list[str] = []
    for check in checks:
        cid = check.get("id", "<unnamed>")
        clauses = list(_filter_clauses(check.get("target")))
        if check.get("assertion") == "matches":
            pattern = (check.get("target") or {}).get("value")
            if isinstance(pattern, str):
                clauses.append(("target", {"field": None, "matches": pattern}))
        internal = _computed_names(check.get("target")) | labels
        needs = [(where, clause, *_clause_needs(clause, internal, visible)) for where, clause in clauses]
        needs = [n for n in needs if n[2] or n[3] or n[4]]
        source_quotes, source_problems = _source_rule_quotes(check, spec, bundle, steps)
        problems.extend(source_problems)
        if not needs:
            continue
        raw = check.get("rule_quote")
        quotes = [raw] if isinstance(raw, str) else [q for q in raw or [] if isinstance(q, str)] \
            if isinstance(raw, list) else []
        step = check.get("step")
        text = texts.get(step, "")
        if not quotes and not source_quotes:
            where, clause, *_ = needs[0]
            problems.append(
                f"check {cid!r}: its target applies a rule the agent must be told "
                f"({json.dumps(clause, ensure_ascii=False)[:120]} at {where}) but carries no "
                f"`rule_quote` or valid `rule_sources`. Quote, verbatim from step {step!r}'s instruction "
                "or an accessible fixture document, the sentence "
                "that states each filter and pattern; if no sentence states it, the rule is "
                "hidden (Arena kw006) -- publish it or drop it")
            continue
        # `rule_terms` maps a fixture token to the words the instruction uses
        # for it when it does not repeat the token -- "its status cell" for the
        # 狀態 column, "still to do" for 待辦. The words must be in the quoted
        # sentence, and every mapping is published to basis.toml for review, so
        # a translation is declared rather than assumed. It cannot make an
        # unquoted rule public: the sentence still has to say it.
        terms = check.get("rule_terms") if isinstance(check.get("rule_terms"), dict) else {}
        valid = list(source_quotes)
        for quote in quotes:
            q = _norm(quote)
            if len(q) < MIN_RULE_QUOTE:
                problems.append(f"check {cid!r}: rule_quote {quote!r} is too short to state a rule")
            elif len(q) > MAX_RULE_QUOTE:
                problems.append(
                    f"check {cid!r}: rule_quote {quote[:60]!r}... is {len(q)} characters; quote "
                    f"the sentence that states the rule (at most {MAX_RULE_QUOTE}), not a section")
            elif q not in text:
                problems.append(
                    f"check {cid!r}: rule_quote {quote[:80]!r} is not verbatim in step "
                    f"{step!r}'s instruction; a rule is public only where the agent reads it")
            else:
                valid.append(q)
        if not valid:
            continue
        named, stated = _matchers(terms)
        from ..policy import HIDDEN_RULE_MODE
        witness_mode = HIDDEN_RULE_MODE == "witness"
        surface = _norm(text + "\n" + (visible_text or "")) if witness_mode else ""
        for where, clause, name, literals, located in needs:
            if any(clause_covered(name, literals, located, q, terms) for q in valid):
                continue
            if witness_mode:
                # v2 (user, 2026-10-02: "only giving visibility on what of task
                # and not how"): the rule is public when a verbatim witness
                # from the instruction OR an accessible document is cited and
                # every value the filter tests can be found by a reader of the
                # step's instruction and files. Whether the cited sentence also
                # names the column and each value together is reviewed
                # semantically and reported as an advisory below.
                hidden = [l for l in literals if not stated(l, surface)]
                if hidden:
                    problems.append(
                        f"check {cid!r}: {json.dumps(clause, ensure_ascii=False)[:120]} at {where} "
                        f"tests {hidden}, which is not discoverable in any agent-readable surface "
                        "(the step instruction or a fixture document). A value no reader can find "
                        "is a hidden grading rule (Arena kw006)")
                    continue
            # A membership list is often published as a list -- one member per
            # line or bullet -- so its members may be spread over the quotes;
            # the column must still be named in one of them.
            if (set(clause) & {"in", "not_in"} and any(named(name, q) for q in valid)
                    and all(any(stated(l, q) for q in valid) for l in literals)):
                continue
            missing = ([name] if name and not any(named(name, q) for q in valid) else []) + \
                [l for l in literals if not any(stated(l, q) for q in valid)] + \
                ([f"most of {located}"] if not any(_located(located, q, stated) for q in valid) else [])
            problems.append(
                f"check {cid!r}: {json.dumps(clause, ensure_ascii=False)[:120]} at {where} is not "
                f"stated by any rule_quote (no quoted sentence names {missing or [name, *literals]} "
                "together). A filter no public rule states is a hidden grading rule")
    return problems


_UNORDERED = _re.compile(
    r"order (?:does not|doesn't|do not|don't|is not|isn't) (?:matter|significant|important)"
    r"|in any order|any order|order is (?:ignored|irrelevant|not significant)|unordered"
    r"|regardless of (?:their |the )?order|order-insensitive"
    r"|順不同|(?:順序|並び順)(?:は|を)問わない|任意の順(?:序)?"
    r"|(?:順序|並び順)(?:は|に)(?:意味がない|意味を持たない|影響しない|評価しない|比較しない)", _re.I)
_JAPANESE_ORDER = (
    r"(?:並び順|順序)(?:に|には)(?:意味がある|意味を持つ)"
    r"|(?:掲載|記載|表示|登場|処理|作成日時|時刻|時系列|受付|流す)(?:の)?順(?:序)?(?:に|で|とする|どおり|のとおり)"
    r"|(?:昇順|降順)(?:に|で|とする)|先頭から末尾(?:へ|に)")
_ORDERED = _re.compile(
    r"\b(?:order|ordered|sort|sorted|ascending|descending|chronologic\w*|sequence|sequential"
    r"|rank|ranked|earliest|oldest|newest|first to last|top to bottom|as they appear)\b"
    r"|" + _JAPANESE_ORDER, _re.I)


def _array_paths(schema, trail: str = ""):
    """(relative path, schema) of arrays reachable through object keys only --
    the paths `unordered_paths` can address -- and, separately, arrays nested
    inside array items, which every assertion compares in order."""
    if not isinstance(schema, dict):
        return
    if schema.get("type") == "array":
        yield trail, schema, False
        yield from ((f"{trail}[].{p}" if p else f"{trail}[]", s, True)
                    for p, s, _ in _array_paths(schema.get("items") or {}, ""))
    elif schema.get("type") == "object":
        for key, sub in (schema.get("properties") or {}).items():
            path = f"{trail}.{key}" if trail else key
            for p, s, nested in _array_paths(sub, path):
                yield p, s, nested


def _order_rules(spec: dict) -> list[str]:
    """[T3] Array order is graded only where it is published.

    An ordered `equals` on an array the instruction or schema calls unordered
    fails every correct answer in a different order; an ordered `equals` on an
    array whose order nobody stated grades a hidden ordering rule. The schema
    marks an unordered array with `"unordered": true`; `equals` honours it
    through `unordered_paths` (nested) or by using multiset_equals (top level)."""
    from .contracts import schema_at
    compiled = _compiled(spec)
    if compiled is None:
        return []
    steps, outputs, checks = compiled
    texts = _step_text(steps)
    by_file = {o.get("file"): o for o in outputs}
    problems: list[str] = []
    for check in checks:
        actual = check.get("actual") or {}
        output = by_file.get(actual.get("file"))
        if check.get("kind") != "objective" or output is None or actual.get("op") != "field":
            continue
        base = actual.get("path") or ""
        field_schema = schema_at(output.get("schema") or {}, base) if base else output.get("schema")
        if not isinstance(field_schema, dict):
            continue
        text = texts.get(output.get("step"), "")
        names = {n for n, *_ in _schema_fields(output.get("schema"))}
        declared = set(check.get("unordered_paths") or [])
        for rel, schema, nested in _array_paths(field_schema):
            full = ".".join(p for p in (base, rel) if p)
            field = next((p for p in reversed(_re.split(r"[.\[\]]+", full)) if p), "")
            paragraphs = " ".join(p for _, p in _definition_windows(text, field, names))
            # Field-level, shared with T3b and the grader probe: the field's own
            # description outranks a neighbour's "row order is immaterial".
            declaration = order_declaration(spec, output.get("file"), full)[0]
            unordered = declaration == "unordered"
            ordered_stated = declaration == "ordered" or bool(_ORDERED.search(paragraphs))
            where = f"{output.get('file')}:{full or '(root)'}"
            if check.get("assertion") == "equals":
                honoured = not nested and rel and rel in declared
                if unordered and not honoured:
                    problems.append(
                        f"check {check.get('id')!r}: `equals` compares {where} in order, but the "
                        "instruction or schema says its order does not matter. Use multiset_equals "
                        "for a top-level array or list the path in `unordered_paths`")
                elif not unordered and not honoured and not ordered_stated:
                    problems.append(
                        f"check {check.get('id')!r}: `equals` compares {where} in order, but the "
                        "instruction never states an order for it -- a hidden ordering rule. State "
                        "the order, or compare it without order")
            elif nested and unordered:
                problems.append(
                    f"check {check.get('id')!r}: {where} is nested inside compared rows, where "
                    "order always counts, but the instruction or schema says its order does not "
                    "matter. Flatten it into keyed rows or make its order part of the rule")
    return problems


# A list order the instruction publishes for the answer, as opposed to the
# ordinary words (`newest`, `first`) _ORDERED also accepts as licence.
_LIST_ORDER = _re.compile(
    r"\b(?:document|running|reading|file|register|queue|worksheet|table|source|listing|"
    r"printed|appearance|pauta|chronological)\s+order\b|\bin the order\b|\bin order of\b"
    r"|\b(?:ordered|sorted|listed) by\b|\bas they appear\b|\bfirst to last\b|\btop to bottom\b"
    r"|\b(?:ascending|descending)\b[^.\n]{0,30}\border\b|" + _JAPANESE_ORDER, _re.I)


# Wordings T3's _UNORDERED misses: "the order of the array is not graded".
_UNORDERED_MORE = _re.compile(
    r"\border\b[^.\n]{0,80}\b(?:is|are)\s+(?:not\s+(?:graded|scored|checked|compared|significant)|immaterial|irrelevant)\b"
    r"|\border\b[^.\n]{0,80}\bdoes(?:n't| not) matter\b|\bmay be (?:listed |given |written )?in any order\b", _re.I)


def order_declaration(spec: dict, file: str, path: str) -> tuple[str, str]:
    """How the published contract orders the array at `file`:`path`:
    ("unordered", why), ("ordered", why) or ("unstated", "").

    The contract says array order is compared as written unless the schema
    says `"unordered": true` or the assignment says the order does not matter,
    so both count, and only the field's own definition (and, for a nested
    array, its parent's) speaks for it. Shared by T3b and the grader probe so
    the static rule and the executed one cannot disagree."""
    from .contracts import schema_at
    compiled = _compiled(spec)
    if compiled is None:
        return "unstated", ""
    steps, outputs, _ = compiled
    output = next((o for o in outputs if o.get("file") == file), None)
    if output is None:
        return "unstated", ""
    schema = schema_at(output.get("schema") or {}, path) if path else output.get("schema")
    if not isinstance(schema, dict):
        return "unstated", ""
    text = _step_text(steps).get(output.get("step"), "")
    names = {n for n, *_ in _schema_fields(output.get("schema"))}
    parts = [p for p in _re.split(r"[.\[\]]+", path) if p]

    def read(words: str):
        words = " ".join(words.split())
        return _UNORDERED.search(words) or _UNORDERED_MORE.search(words), _LIST_ORDER.search(words)

    # The field's own schema description speaks first; then its definition;
    # then, for a nested list, its parent's definition ("the order of the
    # names inside each list does not matter"). A neighbour's paragraph that
    # merely mentions the name must not outvote the field's own words.
    sources = [schema.get("description") or "",
               *(" ".join(p for _, p in _definition_windows(text, field, names)) for field in reversed(parts[-2:]))]
    for words in sources:
        unordered, stated = read(words)
        if unordered or stated:
            break
    if schema.get("unordered") is True:
        if stated and not unordered:
            return "conflict", (f"its schema declares \"unordered\": true but its definition "
                                f"publishes {stated.group(0)!r}")
        return "unordered", "schema declares \"unordered\": true"
    if unordered:
        return "unordered", f"the instruction says {unordered.group(0)!r}"
    if stated:
        return "ordered", f"the instruction publishes {stated.group(0)!r}"
    return "unstated", ""


def _unordered_contract(spec: dict) -> list[str]:
    """[T3b] An array graded without order must be published without order.

    Arena's 260927 feedback: five lists the instruction ordered ("in document
    order", "in running order") were graded with set_equals, so a reversed list
    earned full credit, and set_equals let a repeated heading through. T3 only
    looks at `equals`; this is the other direction. The published contract says
    array order is compared as written unless the schema says `"unordered":
    true` or the assignment says the order does not matter; `order_declaration`
    reads both, and a definition that publishes an order contradicts either."""
    from .contracts import schema_at
    compiled = _compiled(spec)
    if compiled is None:
        return []
    _, outputs, checks = compiled
    by_file = {o.get("file"): o for o in outputs}
    problems: list[str] = []
    for check in checks:
        actual = check.get("actual") or {}
        output = by_file.get(actual.get("file"))
        if output is None or actual.get("op") != "field":
            continue
        base = actual.get("path") or ""
        schema = schema_at(output.get("schema") or {}, base) if base else output.get("schema")
        if not isinstance(schema, dict):
            continue
        where = f"{output.get('file')}:{base or '(root)'}"
        if check.get("assertion") == "equals":
            for rel in check.get("unordered_paths") or []:
                if not isinstance(rel, str) or not rel:
                    continue
                full = f"{base}.{rel}" if base else rel
                kind, _ = order_declaration(spec, output.get("file"), full)
                if kind != "unordered":
                    problems.append(
                        f"check {check.get('id')!r}: {where}.{rel} is compared without order "
                        "(unordered_paths) but neither its schema (\"unordered\": true) nor its "
                        "definition says so, and the published contract says array order is compared "
                        "as written")
            continue
        if check.get("assertion") not in ("set_equals", "multiset_equals") or schema.get("type") != "array":
            continue
        kind, why = order_declaration(spec, output.get("file"), base)
        if kind in ("ordered", "conflict"):
            problems.append(
                f"check {check.get('id')!r}: {check['assertion']} ignores the order of {where}, but "
                f"{why}; a reversed list would earn full credit. Compare it with `equals`, or drop "
                "the order from the instruction")
        elif kind == "unstated":
            problems.append(
                f"check {check.get('id')!r}: {check['assertion']} ignores the order of {where}, but "
                "neither its schema (\"unordered\": true) nor its definition says the order does not "
                "matter, and the published contract says array order is compared as written")
        if check["assertion"] == "set_equals" and schema.get("uniqueItems") is not True:
            problems.append(
                f"check {check.get('id')!r}: set_equals gives full credit to {where} with an entry "
                "repeated. Declare \"uniqueItems\": true or compare with multiset_equals")
    return problems


def _guard_shape(spec: dict) -> list[str]:
    """[T4] A guardrail tests restraint or preservation, never correctness.

    Arena's 260927 feedback: a guard meant to stop step 2 re-editing step 1's
    record compared that record with the recomputed answer and ran in step 1,
    so a one-day error in one field zeroed the whole step while no edit had
    happened. Guards gate the step, so a guard that a wrong answer can fail
    turns one objective's miss into a zero."""
    compiled = _compiled(spec)
    if compiled is None:
        return []
    _, outputs, checks = compiled
    written = {o.get("file"): o.get("step") for o in outputs}
    problems: list[str] = []
    for check in checks:
        if check.get("kind") != "guardrail" or check.get("assertion") not in ("equals", "set_equals", "multiset_equals"):
            continue
        actual, target = check.get("actual") or {}, check.get("target") or {}
        if actual.get("op") == "field" and target.get("op") not in ("literal", "fixture"):
            problems.append(
                f"guardrail {check.get('id')!r} compares {actual.get('file')} with a value derived from "
                "the sources, so a wrong answer fails it and gates the step. A guardrail must test "
                "restraint or preservation; grade correctness with an objective")
        if actual.get("op") == "field" and written.get(actual.get("file")) == check.get("step"):
            problems.append(
                f"guardrail {check.get('id')!r} guards {actual.get('file')} in {check.get('step')}, the "
                "step that writes it: nothing can have edited it yet")
    return problems


_OWN_HISTORY = _re.compile(
    r"\byour (?:own )?(?:step[- ]?(?:1|one)|first[- ]step|earlier|previous|prior)\b[^.\n]{0,40}"
    r"\b(?:plan|answer|record|report|audit|submission|file|list|figures?|values?|results?|assessment)\b"
    r"|\b(?:you|the solver) (?:filed|submitted|wrote|reported|recorded|gave) (?:in|at|for) step[- ]?(?:1|one)\b", _re.I)
_NOT_GRADED_HISTORY = _re.compile(
    r"\b(?:stays?|leave|left|unchanged|not (?:be )?corrected|not be edited|must not be|as you filed it"
    r"|do not (?:carry|filter|re-?rank|subtract|restate|edit|correct)|not (?:a valid basis|carried forward)"
    r"|measured again|even if)\b", _re.I)


def _history_references(spec: dict) -> list[str]:
    """[T5] A later step's answer is defined by the rules, not by the solver's
    own earlier submission.

    Arena's 260927 feedback: step 2 asked for "each placement in your step-1
    plan", the grader recomputed the canonical plan, and a revision that
    faithfully reconciled a different step-1 answer scored 0.84. The grader
    never sees the earlier submission, so a field defined by it is graded
    against something the solver was not asked for."""
    compiled = _compiled(spec)
    if compiled is None:
        return []
    steps, outputs, _ = compiled
    problems: list[str] = []
    for step in steps[1:]:
        keys = {n.split(".")[-1] for o in outputs if o.get("step") == step["name"]
                for n, *_ in _schema_fields(o.get("schema"))}
        keys = {k for k in keys if "_" in k or len(k) > 12}
        for sentence in _re.split(r"(?<=[.;])\s+|\n\s*[-*]\s+", step.get("instruction") or ""):
            said = _OWN_HISTORY.search(sentence)
            if not said or _NOT_GRADED_HISTORY.search(sentence):
                continue
            named = sorted(k for k in keys if _re.search(r"(?<![\w])%s(?![\w])" % _re.escape(k), sentence))
            if named:
                problems.append(
                    f"step {step['name']!r} defines {named[:3]} by the solver's own earlier submission "
                    f"({said.group(0)!r}); the grader recomputes the rule-derived answer instead. Define "
                    "them by the earlier step's rules, and say so")
    return problems


def _accent_fold(text: str) -> str:
    import unicodedata
    return "".join(c for c in unicodedata.normalize("NFKD", text) if not unicodedata.combining(c)).casefold()


def _literal_consistency(spec: dict, bundle: Path | None = None) -> list[str]:
    """[T6] A literal the instruction quotes is spelled one way, the way the
    files spell it.

    Arena's 260927 feedback: the instruction quoted both `não declarada` and
    "exactly `nao declarada`"; the files write the first, and a solver who
    followed the second literally scored 0.74. The equality rules fold case and
    whitespace, not accents, so an accent variant is a different answer."""
    compiled = _compiled(spec)
    if compiled is None:
        return []
    steps, _, _ = compiled
    problems: list[str] = []
    forms: dict[str, set[str]] = {}
    for step in steps:
        prose = _re.sub(r"```.*?```", "", step.get("instruction") or "", flags=_re.S)
        for m in _re.finditer(r"`([^`\n]{2,80})`", prose):
            forms.setdefault(_accent_fold(" ".join(m.group(1).split())), set()).add(" ".join(m.group(1).split()))
    for variants in forms.values():
        if len({v.casefold() for v in variants}) > 1:
            problems.append(f"the instruction spells one literal {len(variants)} ways: "
                            f"{sorted(variants)}; the grader does not fold accents")
    files = bundle / "environment/files" if bundle is not None else None
    if files is not None and files.is_dir():
        corpus = "\n".join(p.read_text(errors="ignore") for p in sorted(files.rglob("*"))
                           if p.is_file() and p.stat().st_size < 2_000_000).casefold()
        folded = _accent_fold(corpus)
        for step in steps:
            for m in _re.finditer(r"exactly `([^`\n]{2,80})`", step.get("instruction") or ""):
                literal = m.group(1)
                if literal.casefold() not in corpus and _accent_fold(literal) in folded:
                    problems.append(f"step {step['name']!r} requires exactly `{literal}`, which no file "
                                    "writes; the files write an accented variant of it")
    return problems


def _effective_shares(spec: dict) -> dict[str, float] | None:
    """Each objective's share of the task reward as graded: per-step
    `weight / step total`, averaged over steps (Harbor's `mean`)."""
    compiled = _compiled(spec)
    if compiled is None:
        return None
    steps, _, checks = compiled
    objectives = [c for c in checks if c.get("kind") == "objective"]
    totals: dict[str, float] = {}
    for c in objectives:
        totals[c.get("step")] = totals.get(c.get("step"), 0) + (c.get("weight", 0) or 0)
    n = len(steps) or 1
    return {c.get("id"): ((c.get("weight", 0) or 0) / totals[c.get("step")] / n
                          if totals.get(c.get("step")) else 0.0) for c in objectives}
