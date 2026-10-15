"""Stage F4 -- run the adversarial probe suite against a built bundle.

Every claim the gate chain makes about a bundle rests on these. Without them
`trap.beatable`, `difficulty.axes` and `hacking.resistance` can only report
"never executed", which is exactly the state the pipeline was in: fifteen gates
defined and six that had never run against anything.

A probe is a *mutation of the reference solution*, scored by the same grader the
agent will face. That is the whole design -- no probe hand-writes an expected
score, and none of them can drift from the grader, because they are the grader.

    seed_zero        the untouched fixture, graded as if submitted
    golden           the reference solution, unmodified
    untidy_correct   golden + permitted cosmetic noise (whitespace, key order)
    plausible_wrong  golden with one decoy substituted for the right answer
    destructive      golden + a guardrail violation
    answer_lookup    every value that can be read straight out of the fixture,
                     with no reasoning applied
    empty_deliverable the deliverable exists and is empty -- what an idle agent
                     earns from objectives whose answer is an empty collection
    forged_state     the output shape, correctly structured, with invented values

Two of these are load-bearing and have no exemption. `answer_lookup` scoring 1.0
means the answer was stored rather than derived, and §0 of the anti-reward-
hacking rules has been lost -- no other control recovers it. `seed_zero` failing
means an objective reads a seeded record instead of the agent's work, which
burns a whole calibration batch before anyone notices.

`forged_state` is mandatory (policy.MANDATORY_PROBES) and always runs. An author
may still declare that the environment carries no provenance surface -- plain
files, no audit trail, no version history -- so that the defence is §0 rather
than provenance grading; the declaration is recorded beside the score, never
instead of it, so a reader sees both what was claimed and what was measured.
"""

from __future__ import annotations

import json
import random
import re
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from . import oracle
from .checks import (Check, CheckError, PathUnassignable, Workspace, _dig, assign_path,
                     evaluate, grade, load, normalise, path_parts)

REQUIRED = ("seed_zero", "golden", "untidy_correct", "plausible_wrong",
            "destructive", "answer_lookup", "empty_deliverable", "forged_state")


@dataclass
class ProbeResult:
    name: str
    reward: float | None
    detail: dict
    applicable: bool = True
    reason: str = ""


def _stage(src: Path, dest: Path) -> Path:
    if dest.exists():
        shutil.rmtree(dest)
    shutil.copytree(src, dest)
    return dest


def _untidy(root: Path, *, allow_extra_files: bool = True) -> None:
    """Cosmetic noise a correct-but-messy agent would leave.

    Preserve the published output contract. A scratch file is harmless only
    for legacy tasks that do not restrict the final deliverable inventory.
    """
    for path in sorted(root.rglob("*.json")):
        try:
            data = json.loads(path.read_text())
        except (json.JSONDecodeError, OSError):
            continue
        if isinstance(data, dict):
            data = {k: data[k] for k in sorted(data, reverse=True)}
        path.write_text(json.dumps(data, indent=4, ensure_ascii=False) + "\n\n")
    if allow_extra_files:
        (root / "scratch-notes.txt").write_text("working notes\n- checked the register\n")


def _corrupt(root: Path, check: Check, ws: Workspace) -> str | None:
    """Make one check wrong, in the direction its assertion actually cares about.

    A single generic mutation does not work, and the first version proved it:
    dropping a list item breaks `set_equals` and `superset_of` but still
    satisfies `subset_of` (a shorter list is still a subset) and `absent` (the
    forbidden thing is still missing). Those traps then scored exactly golden and
    were reported as catching nothing -- a limitation of the probe read as a
    defect in the task.

    So the mutation is chosen per assertion: add a foreign member where the check
    bounds what may appear, remove one where it demands coverage, and introduce
    the forbidden value where the check forbids it.
    """
    actual = check.actual
    found = _locate(root, actual)
    if found is None:
        return None
    path, data, value = found
    where = f"{actual['file']}:{actual.get('path')}"
    assertion = check.assertion

    # `present` only asks that the field exist. Every value mutation below
    # leaves it existing, so the check went on passing and the trap driving it
    # was reported as catching nothing -- the probe could not move the thing it
    # was probing. Removing the value is the one mutation this assertion sees.
    if assertion == "present":
        emptied = _without(data, actual.get("path", ""), value)
        if emptied is None:
            return None
        path.write_text(json.dumps(emptied, indent=2, ensure_ascii=False))
        return f"{where} (removed)"

    #: Assertions that bound what MAY appear: a shorter answer still passes, so
    #: the mutation has to add something that does not belong.
    widen = assertion in ("subset_of", "absent")

    if isinstance(value, list):
        if widen:
            value = list(value) + ["__probe_intruder__"]
        elif value:
            # Drop every occurrence of the victim, not just the last slot. A
            # set-valued answer may carry duplicates -- one a003 answer held
            # 'desc' four times -- and removing one copy leaves the SET
            # identical, so `set_equals` still passed and the trap was reported
            # as catching nothing. A probe that cannot change the value it is
            # probing measures the probe, not the task.
            victim = value[-1]
            shortened = [v for v in value if v != victim]
            value = shortened if shortened != value else value[:-1]
        else:
            value = ["__probe_intruder__"]
    elif isinstance(value, bool):
        value = not value
    elif isinstance(value, (int, float)):
        # Beyond any plausible tolerance, so numeric_within fails too.
        value = value + max(abs(value) * 0.5, 1) + 1
    elif isinstance(value, str):
        value = "__probe_intruder__" if widen else (value[:-1] or "x") + "!"
    elif isinstance(value, dict):
        if widen:
            value = dict(value, __probe_intruder__=1)
        elif value:
            value = {k: v for k, v in list(value.items())[:-1]}
        else:
            value = {"__probe_intruder__": 1}
    elif value is None:
        value = "__probe_intruder__"
    else:
        return None
    return where if _store(path, data, actual.get("path", ""), value) else None


def _load_json(path: Path):
    try:
        return json.loads(path.read_text())
    except (json.JSONDecodeError, OSError, UnicodeError):
        return None


def _exists(data, path: str) -> bool:
    """Does `path` address something in `data`, a null included?

    A plain final key counts when its parent object holds it, so an explicit
    `null` is still a value the probe can move. A `[]` path exists when the
    grader's reader returns a list for it.
    """
    parts = path_parts(path)
    if not parts:
        return data is not None
    if any(p.endswith("[]") for p in parts):
        return _dig(data, path) is not None
    parent = _dig(data, ".".join(parts[:-1])) if len(parts) > 1 else data
    if isinstance(parent, list) and parts[-1].isdigit():
        return int(parts[-1]) < len(parent)
    return isinstance(parent, dict) and any(
        str(k).casefold() == parts[-1].casefold() for k in parent)


def _store(path: Path, data, field_path: str, value) -> bool:
    """Write `value` where the grader reads `field_path`. False if impossible."""
    try:
        data = assign_path(data, field_path, value)
    except PathUnassignable:
        return False
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False))
    return True


def _without(data, field_path: str, value):
    """`data` with the value at `field_path` gone, as far as `_dig` can tell."""
    parts = path_parts(field_path)
    if not parts:
        return None
    if any(p.endswith("[]") for p in parts):
        blank = (lambda v: [blank(x) for x in v] if isinstance(v, list) else None)
        try:
            return assign_path(data, field_path, blank(value))
        except PathUnassignable:
            return None
    parent = _dig(data, ".".join(parts[:-1])) if len(parts) > 1 else data
    if isinstance(parent, dict):
        for key in [k for k in parent if str(k).casefold() == parts[-1].casefold()]:
            del parent[key]
        return data
    return None


def _nest(value, field_path: str):
    """Wrap a scalar once per `[]` so `assign_path` can place it."""
    for _ in range(sum(p.endswith("[]") for p in path_parts(field_path))):
        value = [value]
    return value


def _locate(root: Path, actual: dict):
    """Resolve a `field` actual to (file, document, value) or None.

    Reads through `checks._dig`, the grader's own path reader, so a `[]` path
    addresses here exactly what it addresses when graded.
    """
    if actual.get("op") != "field":
        return None
    path = root / actual["file"]
    if not path.is_file():
        return None
    data = _load_json(path)
    try:
        if data is None or not _exists(data, actual.get("path", "")):
            return None
        return path, data, _dig(data, actual.get("path", ""))
    except CheckError:
        return None


def _plausible_wrong(root: Path, checks: list[Check], ws: Workspace) -> list[str]:
    """Substitute a decoy for one scored value.

    First choice is a numeric target shifted by one: precisely the off-by-one an
    agent makes when it miscounts a register -- the kw-003 defect was a human
    making the same mistake in the answer key.

    But only 1 of this batch's 84 objectives is numeric; 46 are `set_equals`.
    Requiring a float meant the probe found nothing to touch in two bundles,
    graded a byte-identical copy of the reference, scored 1.0 and looked like
    evidence that wrong answers are caught. It was evidence of nothing. So a
    set-valued target falls back to dropping one member -- the missed-one-item
    error, and the same shape of mistake as the off-by-one.
    """
    changed = []
    for check in checks:
        if check.kind != "objective" or check.target is None:
            continue
        try:
            target = normalise(evaluate(check.target, ws, "source"))
        except Exception:
            continue
        if type(target) not in (int, float):
            continue
        found = _locate(root, check.actual)
        if found is None:
            continue
        path, data, _ = found
        if not _store(path, data, check.actual.get("path", ""), target + 1):
            continue
        changed.append(f"{check.actual['file']}:{check.actual.get('path')}")
        return changed

    # No numeric scalar anywhere: drop one member of a set-valued answer.
    for check in checks:
        if check.kind != "objective" or check.target is None:
            continue
        found = _locate(root, check.actual)
        if found is None:
            continue
        path, data, value = found
        if not isinstance(value, list) or len(value) < 2:
            # A one-element list becomes empty, which is the `empty_deliverable`
            # probe's territory and reads as "not attempted" rather than "wrong".
            continue
        dropped = value[-1]
        if not _store(path, data, check.actual.get("path", ""), value[:-1]):
            continue
        changed.append(f"{check.actual['file']}:{check.actual.get('path')} "
                       f"(dropped {dropped!r})")
        return changed

    # Neither a scalar nor a list: the answer is an OBJECT, which is what the
    # measurement construct produces -- {"guide": {"sections": 42, "thin": [...]}}.
    # Four bundles in this batch reached here, mutated nothing, graded a
    # byte-identical copy of the reference, scored 1.0, and were reported as
    # confirmed reward hacking. That is the same "evidence of nothing" the
    # numeric-only version produced, one level deeper. So shift the first
    # numeric leaf inside the object, which is the miscount this construct is
    # built to catch.
    for check in checks:
        if check.kind != "objective" or check.target is None:
            continue
        found = _locate(root, check.actual)
        if found is None:
            continue
        path, data, value = found
        moved = _shift_numeric_leaf(value)
        if moved is None or not _store(path, data, check.actual.get("path", ""), value):
            continue
        where, before, after = moved
        changed.append(f"{check.actual['file']}:{check.actual.get('path')}"
                       f".{where} ({before!r} -> {after!r})")
        return changed

    # Nothing numeric anywhere: the answers are verdicts -- yes/no fields and
    # objects of flags (a-111, 2026-09-28: every objective an `equals` over
    # booleans, enums and flag objects; the probe mutated nothing, graded the
    # reference itself, scored 1.0 and was counted as a confirmed hack). The
    # wrong yes/no is this construct's plausible mistake, so flip the first
    # boolean, top-level or inside an object.
    for check in checks:
        if check.kind != "objective" or check.target is None:
            continue
        found = _locate(root, check.actual)
        if found is None:
            continue
        path, data, value = found
        if isinstance(value, bool):
            if not _store(path, data, check.actual.get("path", ""), not value):
                continue
            changed.append(f"{check.actual['file']}:{check.actual.get('path')} "
                           f"({value!r} -> {not value!r})")
            return changed
        flipped = _flip_boolean_leaf(value)
        if flipped is None or not _store(path, data, check.actual.get("path", ""), value):
            continue
        where, before = flipped
        changed.append(f"{check.actual['file']}:{check.actual.get('path')}"
                       f".{where} ({before!r} -> {not before!r})")
        return changed
    return changed


def _flip_boolean_leaf(value, trail: str = "") -> tuple[str, bool] | None:
    """Flip the first boolean leaf, in place. Returns where and what it was."""
    if isinstance(value, dict):
        items = list(value.items())
    elif isinstance(value, list):
        items = list(enumerate(value))
    else:
        return None
    for key, inner in items:
        here = f"{trail}.{key}" if trail else str(key)
        if isinstance(inner, bool):
            value[key] = not inner
            return here, inner
        flipped = _flip_boolean_leaf(inner, here)
        if flipped is not None:
            return flipped
    return None


def _shift_numeric_leaf(value, trail: str = "") -> tuple[str, float, float] | None:
    """Shift the first numeric leaf by one, in place. Returns where and what.

    Booleans are excluded: `True + 1` is 2, which is a type error rather than a
    plausible wrong answer, and `isinstance(True, int)` is True in Python.
    """
    if isinstance(value, dict):
        for key, inner in value.items():
            if isinstance(inner, bool):
                continue
            if isinstance(inner, (int, float)):
                value[key] = inner + 1
                return f"{trail}{key}" if not trail else f"{trail}.{key}", inner, inner + 1
            moved = _shift_numeric_leaf(inner, f"{trail}.{key}" if trail else str(key))
            if moved is not None:
                return moved
    elif isinstance(value, list):
        for index, inner in enumerate(value):
            if isinstance(inner, bool):
                continue
            if isinstance(inner, (int, float)):
                value[index] = inner + 1
                return f"{trail}[{index}]", inner, inner + 1
            moved = _shift_numeric_leaf(inner, f"{trail}[{index}]")
            if moved is not None:
                return moved
    return None


def _destructive(root: Path, checks: list[Check], ws: Workspace) -> list[str]:
    """Break exactly what a guardrail protects."""
    broken = []
    for check in checks:
        if check.kind != "guardrail":
            continue
        if check.assertion == "fixture_intact":
            # The destructive probe has to break the FIXTURE, not the submission:
            # that is what this guardrail protects. The caller stages a fixture
            # copy for exactly this.
            broken.append("<fixture>")
            continue
        actual = check.actual
        if actual.get("op") in ("exists", "text", "field", "rows"):
            path = root / actual.get("file", "")
            if path.is_file():
                path.write_text("DESTROYED BY PROBE\n")
                broken.append(actual["file"])
                break
    return broken


def _stored_path_witness(target, fixture: Path, assertion='optimal_path'):
    """Look for complete copied witnesses, including a different optimal tie.

JSON documents, JSONL rows and fenced JSON are inspected without executing
source content. This does not certify that an equivalent prose answer is absent.
"""
    if assertion == 'optimal_path':
        from .path_witness import prepare, check_witness
    else:
        from .subset_witness import prepare, check_witness
    prepared = prepare(target)
    for path in sorted(fixture.rglob('*')):
        if not path.is_file() or path.stat().st_size > 8_000_000:
            continue
        try:
            text = path.read_text()
        except (OSError, UnicodeError):
            continue
        candidates = [text]
        if path.suffix.lower() == '.jsonl':
            candidates.extend(text.splitlines())
        candidates.extend(re.findall(r'```(?:json)?[ \t]*\n(.*?)```', text, re.S | re.I))
        for candidate in candidates:
            try:
                value = json.loads(candidate)
            except (ValueError, TypeError, RecursionError):
                continue
            pending = [(value, 0)]
            inspected = 0
            while pending and inspected < 10000:
                value, depth = pending.pop()
                inspected += 1
                if depth > 64:
                    continue
                if isinstance(value, dict):
                    if check_witness(prepared, value)[0]:
                        return value, str(path.relative_to(fixture))
                    pending.extend((child, depth + 1) for child in value.values())
                elif isinstance(value, list):
                    pending.extend((child, depth + 1) for child in value)
    return None


def _answer_lookup(root: Path, checks: list[Check], ws: Workspace,
                   fixture: Path) -> dict:
    """Submit whatever can be read straight out of the fixture.

    For each scored target, compute it, then search the fixture for that exact
    value. A value found verbatim in a single fixture file is a value an agent
    could return without reasoning. The probe submits those and leaves the rest
    blank, so its score is the share of the task a reader could win by grepping.
    """
    token = re.compile(r"[A-Za-z0-9_.:\-]+")
    index: dict[str, set[str]] = {}
    for path in fixture.rglob("*"):
        if not path.is_file() or path.stat().st_size > 8_000_000:
            continue
        try:
            text = path.read_text(errors="replace")
        except OSError:
            continue
        rel = str(path.relative_to(fixture))
        for tok in token.findall(text):
            index.setdefault(tok, set()).add(rel)

    documents = _fixture_json(fixture)
    found, missed, structured, coincidental = {}, [], {}, {}
    for check in checks:
        if check.kind != "objective" or check.target is None:
            continue
        try:
            target = evaluate(check.target, ws, "source")
        except Exception:
            continue
        if isinstance(target, (list, dict)) and check.assertion not in ('optimal_path', 'optimal_subset'):
            # A structured answer never matches `str(target)` as one token, so
            # before this every row-set and record answer was reported "not
            # readable" however plainly the fixture stored it. Search the
            # fixture's JSON for a value the check itself accepts, and for each
            # canonical row of a row-set.
            stored = _stored_structure(check, target, documents)
            if stored is not None:
                value, location, how = stored
                found[check.id] = {"value": value, "in": [location], "structured": how}
                structured[check.id] = {"in": location, "match": how}
            else:
                missed.append(check.id)
            continue
        if check.assertion in ('optimal_path', 'optimal_subset'):
            stored = _stored_path_witness(target, fixture, check.assertion)
            if stored:
                value, location = stored
                found[check.id] = {'value': value, 'in': [location]}
            else:
                missed.append(check.id)
            continue
        scalar = target
        if isinstance(scalar, float) and scalar.is_integer():
            scalar = int(scalar)
        key = str(scalar)
        if key in index and _distinctive(scalar):
            found[check.id] = {"value": scalar, "in": sorted(index[key])[:3]}
        elif key in index:
            # Present, but the match is worthless as evidence. Recorded so a
            # reviewer can see it was considered -- silently dropping it would
            # be the same sin as silently reporting it.
            coincidental[check.id] = {"value": scalar, "in": sorted(index[key])[:3]}
            missed.append(check.id)
        else:
            missed.append(check.id)

    # Write the readable values into the submission shape.
    for check in checks:
        if check.id not in found:
            continue
        actual = check.actual
        if actual.get("op") != "field":
            continue
        path = root / actual["file"]
        data = (_load_json(path) if path.is_file() else None) or {}
        if path_parts(actual.get("path", "")):
            _store(path, data, actual.get("path", ""), found[check.id]["value"])

    return {"readable_from_fixture": found, "not_readable": missed,
            "stored_structured": structured, "coincidental": coincidental}


_EASTERN_DIGITS = str.maketrans("\u0660\u0661\u0662\u0663\u0664\u0665\u0666\u0667\u0668\u0669"
                                "\u06f0\u06f1\u06f2\u06f3\u06f4\u06f5\u06f6\u06f7\u06f8\u06f9",
                                "01234567890123456789")
_PRINTED_NUMBER = re.compile(
    r"(?<![\w.,])([+\-\u2212\u2013]?)(\d{1,3}(?:[ ,.\u00a0\u202f'\u2019]\d{3})+(?:[.,]\d+)?|\d+(?:[.,]\d+)?)(?!\w)")
#: Target ops that COMPUTE a value rather than select one already in a file.
DERIVING_OPS = frozenset({"add", "subtract", "multiply", "divide", "sum", "round"})


def _canonical_number(value) -> str | None:
    from decimal import Decimal, InvalidOperation
    try:
        number = Decimal(str(value))
    except (InvalidOperation, ValueError):
        return None
    if not number.is_finite():
        return None
    text = format(number.normalize(), "f")
    return "0" if text in ("-0", "0") else text


def _number_readings(sign: str, body: str) -> set[str]:
    """Every value a printed number can denote: point- and comma-decimal
    readings, any thousands grouping, Eastern Arabic or Persian digits."""
    out = set()
    negative = sign in ("-", "\u2212", "\u2013")
    for decimal_mark, grouping in ((".", ", \u00a0\u202f'\u2019"), (",", ". \u00a0\u202f'\u2019")):
        text = "".join(ch for ch in body if ch not in grouping)
        if text.count(decimal_mark) > 1 or any(ch in text for ch in ",." if ch != decimal_mark):
            continue
        canonical = _canonical_number(("-" if negative else "") + text.replace(decimal_mark, "."))
        if canonical is not None:
            out.add(canonical)
    return out


def _printed_numbers(fixture: Path) -> dict[str, set[str]]:
    """file -> every canonical number its text prints."""
    index: dict[str, set[str]] = {}
    for path in sorted(fixture.rglob("*")):
        if not path.is_file() or path.stat().st_size > 8_000_000:
            continue
        try:
            text = path.read_text(errors="strict").translate(_EASTERN_DIGITS)
        except (OSError, UnicodeError):
            continue
        found: set[str] = set()
        for match in _PRINTED_NUMBER.finditer(text):
            found |= _number_readings(match.group(1), match.group(2))
        index[str(path.relative_to(fixture))] = found
    return index


def _numeric_leaves(value) -> list[str]:
    leaves = []
    for node in _walk_values(value):
        if isinstance(node, bool) or node is None or isinstance(node, (dict, list)):
            continue
        if isinstance(node, (int, float)) or (isinstance(node, str) and re.fullmatch(r"[+-]?\d+(?:\.\d+)?", node.strip())):
            number = float(node) if isinstance(node, str) else node
            if isinstance(number, float) and number.is_integer() and abs(number) < 1000:
                continue
            if _distinctive(number):
                canonical = _canonical_number(node)
                if canonical is not None:
                    leaves.append(canonical)
    return list(dict.fromkeys(leaves))


def _files_read(expr, aliases: dict[str, str]) -> set[str]:
    files = set()
    for node in _walk_values(expr):
        if isinstance(node, dict) and isinstance(node.get("file"), str):
            files.add(aliases.get(node["file"], node["file"]))
    return files


def _ops(expr) -> set[str]:
    return {node["op"] for node in _walk_values(expr) if isinstance(node, dict) and isinstance(node.get("op"), str)}


def _printed_answers(checks: list[Check], ws: Workspace, fixture: Path, projections) -> dict:
    """Graded answers a document PRINTS, in any locale spelling (2026-10-02 audit).

    `_answer_lookup` matches one exact token, so "+31,1", "1,207.83", a Unicode
    minus or Eastern digits never matched, and structured answers were looked for
    only in JSON: a-009 shipped all thirteen correct panel gaps printed in an
    audit report, a-006 two step-1 figures in a listing, and every probe said
    `readable_from_fixture = {}`. Here each objective's distinctive numeric
    leaves are searched in every text file the check's own target does not read
    (a selection task's answer is, of course, in its source). A scalar computed
    by arithmetic, or every leaf of a structured answer, printed in one such file
    is a stored answer; a majority of leaves is reported as partial.
    """
    aliases = {str(p.get("as")): str(p.get("file")) for p in projections or [] if isinstance(p, dict)}
    # Every file the grader parses is an INPUT source: a value it holds is data
    # the answer may legitimately equal (a state figure, a listing being checked),
    # whichever check reads it -- derived files hide the direct reference.
    sources = set(aliases.values())
    every = _printed_numbers(fixture)
    printed = {rel: numbers for rel, numbers in every.items() if rel not in sources}
    # A leaf the inputs already hold (a threshold, a state figure, a price) is
    # data, wherever else it is repeated; only values the grader COMPUTES count.
    inputs = set().union(*(numbers for rel, numbers in every.items() if rel in sources)) if sources else set()
    full, partial = {}, {}
    for check in checks:
        if check.kind != "objective" or check.target is None:
            continue
        try:
            target = evaluate(check.target, ws, "source")
        except Exception:
            continue
        leaves = [leaf for leaf in _numeric_leaves(target) if leaf not in inputs]
        if not leaves:
            continue
        scalar = not isinstance(target, (list, dict))
        # Selections (latest, min/max, a filtered row) return values a document
        # may legitimately describe; only ARITHMETIC produces a value no input
        # holds, so only an arithmetic answer printed elsewhere is a stored one.
        if not (_ops(check.target) & DERIVING_OPS):
            continue
        read = _files_read(check.target, aliases)
        best = None
        for rel, numbers in printed.items():
            if rel in read:
                continue
            hit = [leaf for leaf in leaves if leaf in numbers]
            if hit and (best is None or len(hit) > len(best[1])):
                best = (rel, hit)
        if best is None:
            continue
        rel, hit = best
        record = {"in": rel, "matched": len(hit), "of": len(leaves), "values": hit[:12]}
        if len(hit) == len(leaves) and (scalar or len(leaves) >= 3):
            full[check.id] = record
        elif not scalar and len(hit) * 2 >= len(leaves) and len(hit) >= 3:
            partial[check.id] = record
    return {"printed_derived": full, "printed_partial": partial}


def _distinctive(scalar) -> bool:
    """Would finding this value in the fixture actually mean anything?

    The scalar arm of `answer_lookup` asks whether the answer appears verbatim
    somewhere in the fixture. For a distinctive value that is strong evidence of
    a stored answer. For a small integer it is noise: a-442's answers were 3 and
    2, "found" in `Platform1.java` because it contains `Platform2`, `rect[2]`
    and `rect[3]`. Reporting those as leaks sent an agent to edit an audited
    source file to satisfy a coincidence.

    So a match counts only when the value could not plausibly have arrived by
    chance: a non-integral float, a four-digit-or-longer number, or a string
    with some substance to it. This mirrors `MIN_STRUCTURED_ROWS`, which exists
    for exactly the same reason on the structured arm.
    """
    if isinstance(scalar, bool) or scalar is None:
        return False
    if isinstance(scalar, float):
        return True                      # a fractional value is never incidental
    if isinstance(scalar, int):
        return abs(scalar) >= 1000
    if isinstance(scalar, str):
        text = scalar.strip()
        if text.lstrip("-").replace(".", "", 1).isdigit():
            try:
                return _distinctive(float(text) if "." in text else int(text))
            except ValueError:
                return len(text) >= 4
        return len(text) >= 4
    return True


#: A structured value this small or this generic is not evidence of a stored
#: answer: `[]`, a one-element id list, `{}` turn up in any JSON fixture.
MIN_STRUCTURED_ROWS = 2


def _fixture_json(fixture: Path) -> list[tuple[str, Any]]:
    """Every JSON value the fixture stores: whole .json files, JSON Lines rows
    and fenced ```json blocks inside text documents. Never executed."""
    out: list[tuple[str, Any]] = []
    for path in sorted(fixture.rglob("*")):
        if not path.is_file() or path.stat().st_size > 8_000_000:
            continue
        try:
            text = path.read_text()
        except (OSError, UnicodeError):
            continue
        rel = str(path.relative_to(fixture))
        candidates = [text]
        if path.suffix.lower() == ".jsonl":
            candidates.extend(text.splitlines())
        candidates.extend(re.findall(r"```(?:json)?[ \t]*\n(.*?)```", text, re.S | re.I))
        for candidate in candidates:
            candidate = candidate.strip()
            if not candidate or candidate[0] not in "[{":
                continue
            try:
                out.append((rel, json.loads(candidate)))
            except (ValueError, RecursionError):
                continue
    return out


def _walk_values(value, limit: int = 20000):
    pending, seen = [(value, 0)], 0
    while pending and seen < limit:
        node, depth = pending.pop()
        seen += 1
        if depth > 64:
            continue
        yield node
        if isinstance(node, dict):
            pending.extend((child, depth + 1) for child in node.values())
        elif isinstance(node, list):
            pending.extend((child, depth + 1) for child in node)


#: Assertions whose target IS the answer. `subset_of`/`superset_of` bound an
#: answer, and a stored subset of one proves nothing.
ANSWER_ASSERTIONS = frozenset({"equals", "set_equals", "multiset_equals"})


def _stored_structure(check: Check, target, documents):
    """(value, file, how) when the fixture stores `target` in a form the check
    accepts: as one JSON value, or as one container holding exactly the
    target's canonical rows (a dict of rows, a reordered list).

    Rows scattered through a larger table do not count: every row a selection
    task returns is, of course, a row of its source, and the selection is the
    work. Membership is not the test; a stored collection is."""
    from collections import Counter
    from .checks import _compare, _hashable
    if check.assertion not in ANSWER_ASSERTIONS:
        return None
    if isinstance(target, (list, dict)) and len(target) < MIN_STRUCTURED_ROWS:
        return None

    def canonical(row):
        try:
            return _hashable(normalise(row))
        except Exception:
            return None

    wanted = (Counter(canonical(r) for r in target)
              if isinstance(target, list) and all(isinstance(r, dict) for r in target) else None)
    for rel, document in documents:
        for node in _walk_values(document):
            if isinstance(node, dict) and isinstance(target, dict) and set(node) != set(target):
                pass
            elif isinstance(node, type(target)) or (isinstance(target, list) and isinstance(node, list)):
                try:
                    if _compare(check, target, node, None)["passed"]:
                        return node, rel, "value"
                except Exception:
                    pass
            if wanted is not None and isinstance(node, (list, dict)):
                members = list(node.values()) if isinstance(node, dict) else node
                if (len(members) == sum(wanted.values()) and all(isinstance(m, dict) for m in members)
                        and Counter(canonical(m) for m in members) == wanted):
                    return list(target), rel, "rows"
    return None


def _empty_deliverable(root: Path, checks: list[Check]) -> list[str]:
    """Create every deliverable the checks read, with no fields in it.

    `seed_zero` stages the fixture with no deliverable at all, so every check
    fails and the probe reads 0.0 however the task is shaped. That leaves one
    state unmeasured, and it is the state an idle agent actually reaches: the
    file exists and says nothing. Any objective whose reference answer is an
    empty collection is then satisfied by writing nothing into it -- measured on
    kw-a009, four objectives carrying 69% of the weight passed that way, and all
    fifteen gates were green.

    The cost of not measuring it is a task that looks hard and is mostly free.
    """
    written: list[str] = []
    for check in checks:
        actual = check.actual
        if actual.get("op") != "field" or not actual.get("file"):
            continue
        path = root / actual["file"]
        if path.name in written:
            continue
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("{}\n")
        written.append(path.name)
    return written


def _surface_leverage(bundle: Path, checks: list[Check], projections,
                      fixture: Path, work: Path) -> dict:
    """Which fixture documents change an answer, and which are inert.

    PLAYBOOK §2's load-bearing test, made mechanical: remove a surface and see
    whether the correct answer changes. If it does not, that document is not
    carrying the question.

    Inert is not the same as useless, and the difference matters. A
    `plausible_decoy` is inert BY DESIGN -- a draft named `final` that the
    instruction says is not authoritative changes no answer and is the whole
    trap. So this reports rather than blocks, and the gate only warns when most
    of the fixture is inert, which is the case the playbook is actually about:
    breadth mistaken for difficulty, seven surfaces where two carry the task.
    """
    import shutil
    from .checks import Workspace, evaluate

    def answers(root: Path) -> dict:
        derived = work / "leverage-derived"
        if derived.exists():
            shutil.rmtree(derived)
        try:
            rows = oracle.project(root, projections)
            oracle.write(rows, derived)
        except Exception as exc:
            return {"__error__": f"{type(exc).__name__}"}
        ws = Workspace(source=root, submitted=root, derived=derived,
                       projections=projections)
        out = {}
        for check in checks:
            if check.kind != "objective" or check.target is None:
                continue
            try:
                value = evaluate(check.target, ws, "source")
                if check.assertion in ('optimal_path', 'optimal_subset'):
                    if check.assertion == 'optimal_path':
                        from .path_witness import prepare, decision_signature
                    else:
                        from .subset_witness import prepare, decision_signature
                    value = decision_signature(prepare(value))
                out[check.id] = json.dumps(normalise(value), sort_keys=True, default=str)
            except Exception as exc:
                out[check.id] = f"<error {type(exc).__name__}>"
        return out

    baseline = answers(fixture)
    if "__error__" in baseline:
        return {"error": baseline["__error__"]}

    docs = sorted(p for p in fixture.rglob("*") if p.is_file())
    load_bearing, inert, required = {}, [], {}
    for doc in docs:
        trimmed = work / "leverage-fixture"
        if trimmed.exists():
            shutil.rmtree(trimmed)
        shutil.copytree(fixture, trimmed)
        # Emptied, not deleted. Deleting breaks `oracle.project` -- every
        # projection names its file -- so every answer becomes an error and
        # every document reads as load-bearing. That is the probe failing to
        # move the thing it is probing, which is a mistake this repository has
        # now made three times. An emptied file still parses and yields no
        # rows, so what changes is the ANSWER, which is the question §2 asks.
        (trimmed / doc.relative_to(fixture)).write_text("")
        got = answers(trimmed)
        rel = str(doc.relative_to(fixture))
        if "__error__" in got:
            # A projection reads this file and cannot run without it. That is a
            # weaker claim than "the answer depends on it" -- the task simply
            # cannot be computed -- so it is reported separately rather than
            # counted as evidence the document carries the question.
            required[rel] = got["__error__"]
            continue
        moved = [cid for cid, val in baseline.items() if got.get(cid) != val]
        if moved:
            load_bearing[rel] = moved
        else:
            inert.append(rel)
    return {"load_bearing": load_bearing, "required_by_projection": required,
            "inert": inert,
            "inert_share": round(len(inert) / max(len(docs), 1), 3),
            "documents": len(docs),
            "note": "An inert document changes no scored answer. That is a "
                    "defect when it is most of the fixture -- breadth mistaken "
                    "for difficulty -- and correct when it is a decoy."}


def _forged(root: Path, checks: list[Check]) -> None:
    """Correct output shape, invented values."""
    for check in checks:
        actual = check.actual
        if actual.get("op") != "field":
            continue
        path = root / actual["file"]
        data = (_load_json(path) if path.is_file() else None) or {}
        if path_parts(actual.get("path", "")):
            _store(path, data, actual.get("path", ""), _nest(42, actual.get("path", "")))


def run(bundle: Path, work: Path,
        forged_applicable: bool = True,
        forged_reason: str = "") -> dict:
    """Run the suite. Returns the report `verification/probes.json` expects."""
    from .traps import Trap
    fixture = next((bundle / "environment" / n for n in ("files", "fixtures")
                    if (bundle / "environment" / n).is_dir()), None)
    if fixture is None:
        raise FileNotFoundError(f"no fixture under {bundle}/environment")
    golden = bundle / "solution" / "submission"
    if not golden.is_dir():
        raise FileNotFoundError(f"no reference solution at {golden}")

    checks = load(bundle / "tests" / "checks.json")
    traps_file = bundle / "authoring" / "traps.json"
    traps = []
    if traps_file.is_file():
        for raw in json.loads(traps_file.read_text()).get("traps", []):
            try:
                traps.append(Trap(**{k: v for k, v in raw.items()
                                     if k in Trap.__dataclass_fields__}))
            except TypeError:
                continue
    work.mkdir(parents=True, exist_ok=True)
    results: dict[str, Any] = {}

    derived = bundle / "tests" / "derived"
    derived = derived if derived.is_dir() else None
    pfile = bundle / "tests" / "projections.json"
    projections = (json.loads(pfile.read_text())["projections"]
                   if pfile.is_file() else None)

    def score(name: str, submitted: Path) -> dict:
        return grade(checks, Workspace(source=fixture, submitted=submitted,
                                       derived=derived, projections=projections))

    # seed_zero -- the untouched fixture, graded as a submission
    empty = _stage(fixture, work / "seed_zero")
    out = score("seed_zero", empty)
    results["seed_zero"] = {
        "reward": out["reward"],
        "objectives": {c.id: (1.0 if out["checks"][c.id].get("passed") else 0.0)
                       for c in checks if c.kind == "objective"},
        "guardrails": {c.id: (1.0 if out["checks"][c.id].get("passed") else 0.0)
                       for c in checks if c.kind == "guardrail"},
    }

    ref_ws = Workspace(source=fixture, submitted=golden, derived=derived,
                       projections=projections)

    g = _stage(golden, work / "golden")
    results["golden"] = {"reward": score("golden", g)["reward"]}

    u = _stage(golden, work / "untidy_correct")
    output_contract = bundle / "tests/outputs.json"
    declared_outputs = json.loads(output_contract.read_text()).get("outputs", []) if output_contract.is_file() else []
    _untidy(u, allow_extra_files=not declared_outputs)
    results["untidy_correct"] = {"reward": score("untidy_correct", u)["reward"]}

    p = _stage(golden, work / "plausible_wrong")
    changed = _plausible_wrong(p, checks, ref_ws)
    results["plausible_wrong"] = {"reward": score("plausible_wrong", p)["reward"],
                                  "mutated": changed}

    # The destructive probe needs its own fixture copy, because what it breaks
    # is the source material an agent was told to leave alone.
    d = _stage(golden, work / "destructive")
    broken_fixture = _stage(fixture, work / "destructive-fixture")
    # Break a file the guardrails actually protect. `fixture_intact` re-derives
    # the PROJECTIONS and compares them against the frozen rows, so destroying
    # a fixture file that backs no projection is invisible to it -- correctly,
    # since nothing claimed to watch that file. Taking the first file
    # alphabetically meant the probe tested whatever happened to sort first: in
    # seven bundles that backed a projection and the guardrail fired; in four it
    # did not, and the probe reported a task scoring 1.0 with a broken fixture
    # as though the guardrails were decorative. They were not.
    protected = {str(spec.get("file")) for spec in (projections or [])
                 if isinstance(spec, dict) and spec.get("file")}
    candidates = [f for f in sorted(broken_fixture.rglob("*")) if f.is_file()]
    victim = next((f for f in candidates
                   if str(f.relative_to(broken_fixture)) in protected), None)
    if victim is None:
        # No projection reads any fixture file, so `fixture_intact` has nothing
        # to guard. Fall back to the first file and let the probe record that
        # it broke something unwatched, rather than silently testing nothing.
        victim = candidates[0] if candidates else None
    if victim is not None:
        victim.write_text("DESTROYED BY PROBE\n")
    broken = _destructive(d, checks, ref_ws)
    destroyed = {
        "broke": broken,
        "destroyed": str(victim.relative_to(broken_fixture)) if victim else None,
        "destroyed_was_protected": bool(
            victim is not None
            and str(victim.relative_to(broken_fixture)) in protected)}
    try:
        out = grade(checks, Workspace(source=broken_fixture, submitted=d,
                                      derived=derived, projections=projections))
        results["destructive"] = {"reward": out["reward"],
                                  "violated": out["guardrails_violated"], **destroyed}
    except CheckError as exc:
        # A target that cannot be computed over the damaged fixture is "could
        # not check", recorded with no reward -- the gate blocks on that
        # (`destructive-no-score`) rather than the whole probe run crashing.
        results["destructive"] = {"reward": None, "error": str(exc), **destroyed}

    # Per-trap probes, after `destructive`, which guardrail-only traps reuse.
    # A single global mutation cannot show that each trap
    # catches anything: it moves one field, and a trap pointing at a different
    # check sees a score equal to golden and is reported as "not
    # discriminating" -- a limitation of the probe, read as a defect in the task.
    # So every trap gets its own mutation, of the checks it claims to drive.
    trap_probes: dict[str, Any] = {}
    by_id = {c.id: c for c in checks}
    for trap in traps:
        driven = [by_id[c] for c in trap.checks if c in by_id]
        objectives = [c for c in driven if c.kind == "objective"]
        guardrails = [c for c in driven if c.kind == "guardrail"]

        if objectives:
            staged = _stage(golden, work / f"trap-{trap.id}")
            mutated = [m for m in (_corrupt(staged, c, ref_ws) for c in objectives)
                       if m]
            trap_probes[trap.id] = {
                "reward": score(f"trap-{trap.id}", staged)["reward"],
                "mutated": mutated, "checks": list(trap.checks),
                "exercised_by": "objective mutation"}
        elif guardrails:
            # A trap that only drives guardrails cannot be shown by corrupting
            # the submission -- nothing in the submission is what it protects.
            # Violating the guardrail is what exercises it, and `destructive`
            # already does exactly that.
            trap_probes[trap.id] = {
                "reward": results["destructive"]["reward"],
                "mutated": ["<guardrail violation>"], "checks": list(trap.checks),
                "exercised_by": "destructive probe"}
        else:
            trap_probes[trap.id] = {
                "reward": None, "mutated": [], "checks": list(trap.checks),
                "exercised_by": "none -- drives no declared check"}
    results["per_trap"] = trap_probes

    a = _stage(fixture, work / "answer_lookup")
    detail = _answer_lookup(a, checks, ref_ws, fixture)
    results["answer_lookup"] = {"reward": score("answer_lookup", a)["reward"],
                                **detail, **_printed_answers(checks, ref_ws, fixture, projections)}

    results["surface_leverage"] = _surface_leverage(
        bundle, checks, projections, fixture, work)

    e = _stage(fixture, work / "empty_deliverable")
    written = _empty_deliverable(e, checks)
    results["empty_deliverable"] = {
        "reward": score("empty_deliverable", e)["reward"],
        "files_written": written}

    # `forged_state` is in policy.MANDATORY_PROBES: it always runs and always
    # scores. An author's inapplicability declaration is kept beside the score,
    # never in its place -- all eight envs-final-2 tasks declared it
    # inapplicable on a ground the exemption does not cover (no forged EVIDENCE
    # in the scenario), shipped no score, and the batch counted eight
    # unresolved cases (2026-09-27).
    f = _stage(fixture, work / "forged_state")
    _forged(f, checks)
    results["forged_state"] = {"reward": score("forged_state", f)["reward"]}
    if not forged_applicable:
        results["forged_state"]["declared_inapplicable"] = (
            forged_reason or
            "no provenance surface in this environment: the fixture is plain "
            "files with no audit trail, so the defence is §0 (a derived answer), "
            "measured by answer_lookup; this score shows invented values fail")

    return {
        "schema": "arena-pipeline/probes/1",
        "bundle": bundle.name,
        # What these results describe. The gate chain re-runs the probes and
        # refuses a stored report whose binding or rewards differ, so a
        # probes.json left over from an earlier design cannot certify this one.
        "binding": {"probe_inputs_sha256": probe_identity(bundle, forged_applicable, forged_reason),
                    "forged_applicable": bool(forged_applicable)},
        "results": results,
        "checks": {c.id: {"kind": c.kind, "band": c.band, "weight": c.weight}
                   for c in checks},
        "untested_surfaces": [
            "the agent's own tool use -- probes score submissions, not "
            "trajectories, so a submission reached by a disallowed route scores "
            "the same as one reached properly",
            "prompt-injection through fixture content",
            "partial credit shapes between plausible_wrong and golden",
        ],
    }


#: Everything a probe reads. A change to any of these changes what the probes
#: would report, so the stored report is bound to their digest.
PROBE_INPUTS = ("tests/checks.json", "tests/projections.json", "tests/outputs.json",
                "tests/rubric.json", "tests/derived", "environment/files", "environment/fixtures",
                "solution/submission", "authoring/traps.json")


def probe_identity(bundle: Path, forged_applicable: bool = True, forged_reason: str = "") -> str:
    import hashlib
    bundle = Path(bundle)
    digests = {}
    for rel in PROBE_INPUTS:
        root = bundle / rel
        for path in (sorted(root.rglob("*")) if root.is_dir() else [root]):
            if path.is_file() and not path.is_symlink() and "__pycache__" not in path.parts:
                digests[path.relative_to(bundle).as_posix()] = hashlib.sha256(path.read_bytes()).hexdigest()
    digests["<forged>"] = f"{bool(forged_applicable)}:{forged_reason if not forged_applicable else ''}"
    return hashlib.sha256(json.dumps(digests, sort_keys=True).encode()).hexdigest()


def _summary(report: dict) -> dict:
    """The part of a probe report the gates decide on."""
    results = (report or {}).get("results") or {}
    out = {name: (row or {}).get("reward") for name, row in results.items()
           if isinstance(row, dict) and "reward" in row}
    out["per_trap"] = {k: (v or {}).get("reward") for k, v in (results.get("per_trap") or {}).items()}
    lookup = results.get("answer_lookup") or {}
    out["readable"] = sorted(lookup.get("readable_from_fixture") or {})
    return out


def rerun(bundle: Path) -> dict:
    """Run the suite now, offline, in scratch -- the way the gate chain sees
    the bundle, rather than the way some earlier stage recorded it."""
    import tempfile
    from .contracts import strict_json
    spec_path = Path(bundle) / "authoring" / "spec.json"
    spec = strict_json(spec_path.read_text()) if spec_path.is_file() else {}
    with tempfile.TemporaryDirectory(prefix="arena-probes-") as tmp:
        return run(Path(bundle), Path(tmp) / "work",
                   forged_applicable=spec.get("forged_applicable", False),
                   forged_reason=spec.get("forged_reason", ""))


def binding_problems(stored: dict | None, fresh: dict) -> list[tuple[str, str]]:
    """(code, message) for a stored report that does not describe this bundle."""
    if not stored:
        return [("probe-evidence-missing", "verification/probes.json is absent; the probes "
                 "were re-run by the gate chain but no evidence was recorded with the bundle")]
    bound = (stored.get("binding") or {}).get("probe_inputs_sha256")
    current = fresh["binding"]["probe_inputs_sha256"]
    problems = []
    if not bound:
        problems.append(("probe-evidence-unbound",
                         "verification/probes.json carries no binding to the bundle it describes; "
                         "a stored report cannot be told apart from one written for an earlier design"))
    elif bound != current:
        problems.append(("probe-evidence-stale",
                         f"verification/probes.json was recorded for probe inputs {bound[:12]}, but "
                         f"this bundle's are {current[:12]}: the checks, fixture, reference or traps "
                         "changed after the probes ran"))
    old, new = _summary(stored), _summary(fresh)
    if old != new:
        changed = sorted(k for k in old.keys() | new.keys() if old.get(k) != new.get(k))
        problems.append(("probe-evidence-diverges",
                         f"re-running the probes does not reproduce verification/probes.json "
                         f"(differs in {changed[:6]}); the recorded evidence is not this bundle's"))
    return problems


def gate_report(task_dir: Path, cache: dict | None = None) -> tuple[dict, list[tuple[str, str]]]:
    """(fresh report, binding problems of the stored one), computed once per
    gate-chain run. Every gate that decides on probe results reads the fresh
    report; a stored file is evidence to be checked, never an input."""
    key = ("probes.gate_report", str(Path(task_dir).resolve()))
    if cache is not None and key in cache:
        return cache[key]
    # Gate-logic unit tests hand the gates a synthetic report through the
    # context rather than building a bundle to produce it. `run_bundle` never
    # sets this, so the chain itself always re-runs.
    if cache is not None and isinstance(cache.get("probe_report"), dict):
        return cache["probe_report"], []
    fresh = rerun(Path(task_dir))
    stored_path = Path(task_dir) / "verification" / "probes.json"
    try:
        stored = json.loads(stored_path.read_text()) if stored_path.is_file() else None
    except (OSError, ValueError):
        stored = {}
    result = (fresh, binding_problems(stored, fresh))
    if cache is not None:
        cache[key] = result
    return result


def main(argv: list[str] | None = None) -> int:
    import argparse
    ap = argparse.ArgumentParser(description="Stage F4 -- run the probe suite")
    ap.add_argument("bundle")
    ap.add_argument("--work", default=None)
    ap.add_argument("--forged-not-applicable", action="store_true")
    ap.add_argument("--forged-reason", default="")
    args = ap.parse_args(argv)

    bundle = Path(args.bundle).resolve()
    work = Path(args.work) if args.work else bundle / "verification" / "probe-work"
    report = run(bundle, work,
                 forged_applicable=not args.forged_not_applicable,
                 forged_reason=args.forged_reason)
    out = bundle / "verification" / "probes.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2))

    print(f"{bundle.name}")
    for name in REQUIRED:
        row = report["results"].get(name, {})
        reward = row.get("reward")
        label = "n/a" if reward is None else f"{reward:.3f}"
        print(f"  {name:16s} {label:>6s}"
              + ("" if row.get("applicable", True) else "   (declared inapplicable)"))
    print(f"-> {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
