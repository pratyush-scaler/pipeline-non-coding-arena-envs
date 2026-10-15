"""Declarative checks and the expression language their targets are computed in.

Arena returned nine findings on the first delivery. Seven were properties of
hand-written grader code: a comparison that rejected `"1960"` because it only
accepted numbers, an answer key that said 26 where the truth was 27, a private
allowlist of acceptable evidence, rules the instruction never published. Writing
more careful Python would not have prevented them; the same mistakes are
available in every new grader.

So graders here are not written. A check is **data**:

    {
      "id": "register_open_count",
      "kind": "objective",
      "weight": 8,
      "basis": "Report how many register rows are still open.",
      "target": {"op": "count", "of": {"op": "rows", "file": "register.csv",
                                       "where": {"field": "status", "eq": "open"}}},
      "actual": {"op": "field", "file": "summary.json", "path": "open_count"},
      "assert": "equals"
    }

and one small, reviewed evaluator runs every check. Three consequences, each
killing a finding class at the root rather than by vigilance:

* **No hand-typed answer keys.** `target` is an expression evaluated against the
  fixture at grade time. The 26-vs-27 defect is not a mistake you can make here:
  there is nowhere to type a number. A literal target is accepted only with a
  written justification, and the gate reports every one.
* **Normalisation is the evaluator's job.** `equals` compares `1960`, `"1960"`
  and `" 1960 "` as equal because the comparison is defined once, in one place,
  tested. A task that genuinely needs strict typing says so explicitly.
* **Readable for manual review**, which the spec asks for directly. A reviewer
  reads a table of checks, not 600 lines of Python.

The expression language is deliberately tiny and has no `eval`. Every operation
is a named case in `_evaluate`; anything unrecognised raises rather than
returning a default, because a check that silently evaluates to `None` scores
zero and looks exactly like a model failure.
"""

from __future__ import annotations

import csv
import io
import json
import math
import re
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
from .contracts import contained, strict_json, ContractError, submission_errors, MAX_DELIVERABLE_BYTES

BANDS = ("floor", "core", "stretch")
KINDS = ("objective", "guardrail")


class CheckError(RuntimeError):
    """Raised when a check cannot be evaluated.

    Never caught into a score when the fault is the grader's -- a target that
    cannot be evaluated over the fixture. A check that could not run did not
    fail; the distinction is the whole of task validity. A fault reading the
    AGENT'S submission is the opposite case and is scored as a failed check
    (see `run_check`).
    """


class SubmissionMissing(CheckError):
    """A required agent artifact has not been written."""


class SubmissionInvalid(CheckError):
    """Agent bytes violate the declared serialization format."""


# --------------------------------------------------------------------------
# normalisation -- defined once, so no check can get it wrong privately
# --------------------------------------------------------------------------

_WS = re.compile(r"\s+")
_PUNCT = re.compile(r"[‘’“”–—]")

#: Leading markup a heading carries in its source document but not in a list of
#: headings: ATX hashes, ordered/unordered list markers, and the trailing hashes of the closed
#: ATX form. Folded for the same reason `"1960"` folds to `1960` -- the value is
#: the same, only its transport differs.
#:
#: Measured 2026-09-17 on kw-a007: the model returned all 19 spec headings,
#: verbatim and in order, with the `#` prefixes they carry in the markdown, and
#: scored 0. The parser had stripped them, the instruction never said which form
#: to use, and four checks carrying 34 weight read as capability failures. They
#: were a transport mismatch. `set_equals` after this fold is exact.
#: Leading Markdown markers, stripped as a CHAIN rather than one at a time.
#:
#: Instructions in this batch promise equality ignores "leading Markdown
#: heading/list/quote markers" -- plural. A single strip broke that promise the
#: moment two markers stacked: `## 5. PHYSICAL` folded to `5. physical` while
#: the bare `5. PHYSICAL` folded to `physical`, so a model that copied the whole
#: heading line scored 0.13 on an answer that was correct. Punishing a correct
#: answer written differently is a broken task, not a hard one.
_LEADING_MARKUP = re.compile(r"^\s*(?:#{1,6}\s+|[-*+•]\s+|[0-9]{1,9}[.)]\s+|>\s+)+")
_TRAILING_HASHES = re.compile(r"\s+#+\s*$")
_TRANSLATE = {"‘": "'", "’": "'", "“": '"', "”": '"',
              "–": "-", "—": "-"}


#: The only strings equality treats as numbers: a plain decimal, or one grouped
#: in threes by commas. Anything else -- `1,2,3`, `12,34`, `1_000`, `1e5` -- is
#: text. The public contract promises only that "numeric strings ignore
#: thousands separators"; `float()` promised a great deal more and let wrong
#: answers compare equal to right ones.
_CANONICAL_NUMBER = re.compile(r"[+-]?(?:\d{1,3}(?:,\d{3})+|\d+)(?:\.\d+)?")

#: `_parse_number`'s own, wider gate -- arithmetic and ordering, never equality
#: (see `_num`'s docstring: "only equality keeps their spelling"). A CSV a
#: script saved with Python's own `repr(float)` can legitimately print a value
#: at machine epsilon as `1.1102230246251565e-16`; an instruction that compares
#: such a value against a threshold ("a value written in exponent notation is
#: an ordinary number") needs `_num` to read it as one. `_number_text` keeps
#: `_CANONICAL_NUMBER` untouched, so a bare identifier such as a lot code is
#: never coerced for equality -- only this arithmetic path gets the wider gate.
_ARITHMETIC_NUMBER = re.compile(
    r"[+-]?(?:\d{1,3}(?:,\d{3})+|\d+)(?:\.\d+)?(?:[eE][+-]?\d+)?")


def _number_text(text: str) -> bool:
    """Is `text` a number whose spelling carries no information?

    A leading zero (`007`) or a trailing fractional zero (`3.10`) is part of an
    identifier's spelling -- section 3.10 is not section 3.1 -- so those stay
    strings for equality. Arithmetic contexts still read them via `_num`.
    """
    if not _CANONICAL_NUMBER.fullmatch(text):
        return False
    digits = text.lstrip("+-").replace(",", "")
    whole, _, fraction = digits.partition(".")
    if len(whole) > 1 and whole.startswith("0"):
        return False
    return not fraction.endswith("0")


def _parse_number(text: str) -> int | float | None:
    """A number from canonical decimal text, or None. Never guesses.

    Gated by `_ARITHMETIC_NUMBER`, not `_CANONICAL_NUMBER`: this is the
    arithmetic/ordering parser `_num` falls back to, wider than the spelling
    `_number_text` preserves for equality (see both docstrings)."""
    if not _ARITHMETIC_NUMBER.fullmatch(text):
        return None
    plain = text.replace(",", "")
    number = float(plain) if ("." in plain or "e" in plain or "E" in plain) else int(plain)
    return number if type(number) is int or math.isfinite(number) else None


def _strip_trailing_hashes(text: str) -> str:
    """`_TRAILING_HASHES.sub("", text)` in linear time (Arena 261011 (stage 3)).

    The regex form rescans a long whitespace run from every start position, so a
    deliverable string of a few megabytes of spaces outlasted the verifier. This
    removes exactly what the regex removes: a final run of `#` preceded by at least
    one whitespace character, that whitespace, and any whitespace after the hashes.
    """
    body = text.rstrip()
    core = body.rstrip("#")
    if core != body and core[-1:].isspace():
        return core.rstrip()
    return text

def normalise(value: Any, fold: bool = True) -> Any:
    """Put a value in comparable form.

    Numeric strings become numbers, so `"1960"` and `1960` compare equal -- the
    kw-002 defect, fixed for every check at once. Smart quotes and dashes fold
    to ASCII, so an instruction revised with a different dash character cannot
    void eight criteria the way it did in one measured corpus.

    Only canonical decimals fold (see `_CANONICAL_NUMBER`), and a leading
    Markdown marker is stripped only when text rather than a bare number
    follows it: `- 1,200` is not `1200` with its bullet removed, it is a sign
    the fold would otherwise have silently discarded.

    `fold=False` applies every rule but the casefold: the spelling an
    expression hands back as a *value* (see `_set_members`).
    """
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return value
    if isinstance(value, str):
        text = _PUNCT.sub(lambda m: _TRANSLATE[m.group()], value)
        unmarked = _LEADING_MARKUP.sub("", text)
        # Arena 261011 (stage 3): the same test as `[\d.,\s]*\d[\d.,\s]*`, without its quadratic backtracking.
        if not (re.fullmatch(r"[\d.,\s]+", unmarked) and re.search(r"\d", unmarked)):
            text = unmarked
        text = _strip_trailing_hashes(text)
        text = _WS.sub(" ", text).strip()
        if _number_text(text):
            number = _parse_number(text)
            if number is not None:
                return number
        return text.casefold() if fold else text
    if isinstance(value, (list, tuple)):
        return [normalise(v, fold) for v in value]
    if isinstance(value, dict):
        return {(str(k).casefold() if fold else str(k)): normalise(v, fold) for k, v in value.items()}
    return value


def _as_set(value: Any) -> set:
    if isinstance(value, (list, tuple, set)):
        return {_hashable(normalise(v)) for v in value}
    if value is None:
        return set()
    return {_hashable(normalise(value))}


def _leaves(value: Any) -> list:
    """Every scalar inside a value, normalised: row objects are searched by their
    field values, never compared whole against a string."""
    if isinstance(value, dict):
        return [leaf for v in value.values() for leaf in _leaves(v)]
    if isinstance(value, (list, tuple, set)):
        return [leaf for v in value for leaf in _leaves(v)]
    return [normalise(value)]


def _members(target: Any) -> list:
    """Each thing a contains/absent target names, one at a time."""
    return [m for m in _leaves(target) if m not in (None, "")]


def _found(member: Any, actual: Any) -> bool:
    """Is `member` one of `actual`'s values, or inside one of its texts?

    Numbers match as whole numbers, so "5" is not found in "15 rooms", and
    "1,250" is found in "Total due: 1,250 HKD".
    """
    for leaf in _leaves(actual):
        if leaf is None:
            continue
        if not isinstance(member, bool) and isinstance(member, (int, float)):
            if not isinstance(leaf, bool) and isinstance(leaf, (int, float)) and leaf == member:
                return True
            text = re.sub(r"(?<=\d),(?=\d{3}(?!\d))", "", str(leaf))
            number = format(member, "g") if isinstance(member, float) else str(member)
            if re.search(r"(?<![\d.])" + re.escape(number) + r"(?![\d]|\.\d)", text):
                return True
        elif leaf == member or str(member).casefold() in str(leaf).casefold():
            return True
    return False


_NUMERAL = re.compile(r"[+-]?(?:\d{1,3}(?:,\d{3})+|\d+)(?:\.\d+)?")


def _as_target_type(actual: Any, target: Any) -> Any:
    """Read a submitted numeral as a number where the fixture's answer is one.

    `normalise` keeps "12.50" and "3.10" as strings, so section "3.10" never
    equals "3.1". But where the recomputed target is the NUMBER 12.5, a
    submitted "12.50" is the same answer written differently and must match.
    The target's type decides; the submission's spelling does not.
    """
    if isinstance(target, list) and isinstance(actual, list):
        numeric = [v for v in target if isinstance(v, (int, float)) and not isinstance(v, bool)]
        if numeric and len(numeric) == len(target):
            return [_as_target_type(v, numeric[0]) for v in actual]
        return actual
    if (isinstance(target, (int, float)) and not isinstance(target, bool)
            and isinstance(actual, str) and _NUMERAL.fullmatch(actual.strip())):
        number = float(actual.strip().replace(",", ""))
        return int(number) if number.is_integer() and isinstance(target, int) else number
    return actual


def _hashable(value: Any) -> Any:
    if isinstance(value, bool):
        return ("boolean", value)
    if isinstance(value, list):
        return ("array", tuple(_hashable(v) for v in value))
    if isinstance(value, dict):
        return ("object", tuple(sorted((k, _hashable(v)) for k, v in value.items())))
    return value


def _set_members(value: Any) -> dict:
    items = value if isinstance(value, (list, tuple, set)) else [] if value is None else [value]
    # Hashable keys are internal only. Members keep their case (first
    # occurrence wins): the derived reference writes these values into the
    # deliverable, and the casefolded comparison form "t12" breaks an output
    # pattern the fixture's own "T12" satisfies (a-067, 2026-09-27).
    members = {}
    for item in items:
        members.setdefault(_hashable(normalise(item)), normalise(item, fold=False))
    return members


# --------------------------------------------------------------------------
# the expression language
# --------------------------------------------------------------------------

@dataclass
class Workspace:
    """Files an expression may read, by role.

    Three roots, and the separation is what makes "recompute the target live"
    mean something:

      submitted  what the agent produced -- the only root an `actual` may read
      derived    the oracle projection of the fixture (see oracle.py)
      source     the fixture itself

    A target expression reads `derived` first and falls back to `source`, so it
    can work from normalised rows or from the raw document, but never from the
    submission. An `actual` reads only `submitted`. The evaluator enforces both
    directions: a check cannot accidentally grade the fixture against itself,
    which is the defect that makes an objective pass on an untouched fixture.
    """
    source: Path
    submitted: Path
    derived: Path | None = None
    projections: list | None = None   # for the fixture_intact guardrail
    fixture_manifest: dict | None = None
    outputs: list | None = None
    step: str | None = None

    def read(self, file: str, role: str) -> str:
        if role == "source":
            roots = [r for r in (self.derived, self.source) if r is not None]
        else:
            roots = [self.submitted]
        tried = []
        for root in roots:
            # `startswith` passes for `/app/fixtures-evil` against root
            # `/app/fixtures`. `is_relative_to` is the real containment test.
            try:
                target = contained(root, file)
            except ContractError as exc:
                raise CheckError(f"path escapes {role} root: {file!r}")
            tried.append(str(root))
            if role == "submitted" and target.is_file():
                # Arena 261011 (C3): the output contract refuses a deliverable this large unread. Reading
                # it here anyway (to evaluate the objectives) let a multi-gigabyte file exhaust the
                # verifier's memory instead of scoring the promised 0; an unreadable file raised an
                # uncaught OSError. Both are agent bytes, so both are a failed check, never a crash.
                try:
                    if target.stat().st_size > MAX_DELIVERABLE_BYTES:
                        raise SubmissionInvalid(f"{file}: a deliverable may not exceed {MAX_DELIVERABLE_BYTES} bytes")
                    return target.read_text(errors="replace")
                except OSError as exc:
                    raise SubmissionInvalid(f"{file}: unreadable deliverable ({exc.strerror or exc})") from exc
            if target.is_file():
                return target.read_text(errors="replace")
        error = SubmissionMissing if role == "submitted" else CheckError
        raise error(f"{role} file not found: {file!r} (looked in {tried})")


def _load_rows(text: str, file: str) -> list[dict]:
    if file.endswith((".csv", ".tsv")):
        delim = "\t" if file.endswith(".tsv") else ","
        reader = csv.DictReader(io.StringIO(text), delimiter=delim)
        fields = reader.fieldnames or []
        if not fields or len(set(fields)) != len(fields) or any(not k for k in fields):
            raise ContractError("CSV needs unique nonempty column names")
        rows = list(reader)
        if any(None in r or any(v is None for v in r.values()) for r in rows):
            raise ContractError("CSV rows must match the header width")
        return rows
    if file.endswith(".jsonl"):
        data = [strict_json(line) for line in text.splitlines() if line.strip()]
    else:
        data = strict_json(text)
    if isinstance(data, list):
        if not all(isinstance(d, dict) for d in data):
            raise ContractError("row collection contains a non-object")
        return data
    collections = [v for v in data.values() if isinstance(v, list) and all(isinstance(r, dict) for r in v)] if isinstance(data, dict) else []
    if len(collections) == 1:
        return collections[0]
    raise ContractError(f"{file}: expected exactly one unambiguous row collection")


def _dig(data: Any, path: str) -> Any:
    parts = [p for p in path.split(".") if p]
    if parts[:1] == ["$"]:
        parts = parts[1:]           # `$` is the document root, not a key named "$"
    def dig(cur, remaining):
        if not remaining:
            return cur
        token, *tail = remaining
        many = token.endswith("[]")
        key = token[:-2] if many else token
        if isinstance(cur, list) and key.isdigit():
            index = int(key)
            value = cur[index] if index < len(cur) else None
        elif isinstance(cur, dict):
            matches = [k for k in cur if str(k).casefold() == key.casefold()]
            if len(matches) > 1:
                raise SubmissionInvalid(f"ambiguous field names for {key!r}")
            value = cur[matches[0]] if matches else None
        else:
            return None
        if many:
            if not isinstance(value, list):
                return None
            return [dig(v, tail) for v in value]
        return dig(value, tail)
    return dig(data, parts)


class PathUnassignable(ValueError):
    """A value cannot be placed so that `_dig` reads it back."""


def path_parts(path: str) -> list[str]:
    """The tokens `_dig` walks, with the `$` root removed."""
    parts = [p for p in str(path).split(".") if p]
    return parts[1:] if parts[:1] == ["$"] else parts


def assign_path(document: Any, path: str, value: Any) -> Any:
    """Place `value` so that `_dig(result, path) == value`. Returns the document.

    The one writer for every path `_dig` reads, so a reference solution, a
    probe and the designer cannot each spell `a[].b` their own way. Written
    three times before, it was inverted three different ways: the stored
    reference kept a literal key `shared_publications[]`, `_dig` stripped the
    brackets and read nothing, and a task whose probes said golden 1.0 shipped
    a reference that scored 0.1587 through its own grader.

    `a[].b` with a list value writes one object per element into `a`, merging
    into objects already there, so `a[].b` and `a[].c` fill the same rows.
    Field names match case-insensitively, as `_dig` reads them.
    """
    parts = path_parts(path)
    if not parts:
        return value

    def key_in(container: dict, key: str) -> str:
        matches = [k for k in container if str(k).casefold() == key.casefold()]
        if len(matches) > 1:
            raise PathUnassignable(f"ambiguous field names for {key!r}")
        return matches[0] if matches else key

    def put(cur: Any, remaining: list[str], val: Any) -> Any:
        if not remaining:
            return val
        token, *tail = remaining
        many = token.endswith("[]")
        key = token[:-2] if many else token
        if not key:
            raise PathUnassignable(f"empty segment in path {path!r}")
        if isinstance(cur, list) and key.isdigit() and not many:
            index = int(key)
            cur.extend(None for _ in range(index + 1 - len(cur)))
            cur[index] = put(cur[index], tail, val)
            return cur
        if cur is None:
            cur = {}
        if not isinstance(cur, dict):
            raise PathUnassignable(f"{path!r}: {key!r} would descend into a {type(cur).__name__}")
        name = key_in(cur, key)
        if not many:
            cur[name] = put(cur.get(name), tail, val)
            return cur
        if not isinstance(val, (list, tuple)):
            raise PathUnassignable(f"{path!r} reads a list at {token!r}; got {type(val).__name__}")
        if not tail:
            cur[name] = list(val)
            return cur
        existing = cur.get(name)
        rows = list(existing) if isinstance(existing, list) else []
        rows = rows[:len(val)] + [None] * (len(val) - len(rows))
        cur[name] = [put(row, tail, item) for row, item in zip(rows, val)]
        return cur

    return put(document, parts, value)


def row_filter_problems(where: Any, *, allow_none: bool = False) -> list[str]:
    """Validate the complete predicate, including branches that may not run."""
    if where is None and allow_none:
        return []
    if not isinstance(where, dict):
        return ["row filter must be an object"]
    if not where:
        return []  # The explicit empty predicate matches every row.
    groups = set(where) & {"all", "any"}
    if groups:
        if len(groups) != 1 or set(where) != groups:
            return ["row filter must use exactly one all/any group or one field clause; nest groups instead of mixing them"]
        group = next(iter(groups))
        clauses = where[group]
        if not isinstance(clauses, list):
            return [f"row filter {group} must contain a list of clauses"]
        return [f"{group}[{i}]: {error}" for i, clause in enumerate(clauses)
                for error in row_filter_problems(clause)]
    predicates = {"eq", "ne", "in", "not_in", "gt", "gte", "lt", "lte", "present", "matches"}
    errors = []
    if set(where) - predicates - {"field"}:
        errors.append("unknown row-filter operator; use {field:'name',eq:value} or nested all/any clauses, without op")
    if not isinstance(where.get("field"), str) or not where["field"].strip():
        errors.append("row-filter field must be a nonempty string")
    if not set(where) & predicates:
        errors.append("row-filter field needs at least one predicate such as eq or present")
    if "present" in where and type(where["present"]) is not bool:
        errors.append("row-filter present must be a boolean")
    if "matches" in where:
        if not isinstance(where["matches"], str):
            errors.append("row-filter matches must be a regular-expression string")
        else:
            try:
                re.compile(where["matches"])
            except re.error:
                errors.append("row-filter matches contains an invalid regular expression")
    for op in set(where) & {"gt", "gte", "lt", "lte"}:
        try:
            _num(normalise(where[op]))
        except CheckError:
            errors.append(f"row-filter {op} requires a numeric comparison value")
    return errors


def _require_row_filter(where: Any, *, allow_none: bool = False) -> None:
    if problems := row_filter_problems(where, allow_none=allow_none):
        raise CheckError("; ".join(problems))


def _matches(row: dict, where: dict | None) -> bool:
    _require_row_filter(where, allow_none=True)
    return _match_validated(row, where)


def _match_validated(row: dict, where: dict | None) -> bool:
    if not where:
        return True
    if "any" in where:
        return any(_match_validated(row, c) for c in where["any"])
    if "all" in where:
        return all(_match_validated(row, c) for c in where["all"])
    field_name = where["field"]
    actual = normalise(_dig(row, field_name) if "." in field_name
                       else row.get(field_name))
    for op, expected in where.items():
        if op == "field":
            continue
        want = normalise(expected)
        if op == "eq" and _hashable(actual) != _hashable(want):
            return False
        if op == "ne" and _hashable(actual) == _hashable(want):
            return False
        if op == "in" and _hashable(actual) not in _as_set(expected):
            return False
        if op == "not_in" and _hashable(actual) in _as_set(expected):
            return False
        if op == "gt" and not (_num(actual) > _num(want)):
            return False
        if op == "gte" and not (_num(actual) >= _num(want)):
            return False
        if op == "lt" and not (_num(actual) < _num(want)):
            return False
        if op == "lte" and not (_num(actual) <= _num(want)):
            return False
        if op == "present" and (actual in (None, "")) == expected:
            return False
        if op == "matches" and not re.search(expected, str(actual or ""), re.I):
            return False
    return True


def _num(value: Any) -> float:
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        if type(value) is int or math.isfinite(value):
            return value
    if isinstance(value, str):
        # Arithmetic and ordering read `1.50` and `007` as the numbers they
        # spell; only equality keeps their spelling (see `_number_text`).
        number = _parse_number(value.strip())
        if number is not None:
            return number
    raise CheckError(f"expected a number, got {value!r}")


def rounding_problems(expr: dict) -> list[str]:
    if 'mode' not in expr:
        return []  # Preserve the established behavior of existing expressions.
    errors = []
    if expr['mode'] not in ('half_even', 'half_up'):
        errors.append('decimal rounding mode must be half_even or half_up')
    places = expr.get('places', 2)
    if type(places) is not int or not -308 <= places <= 308:
        errors.append('decimal rounding places must be an integer from -308 to 308')
    return errors


def _round_operand(expr: dict, value, aggregates=False):
    """Keep arithmetic inside explicit decimal rounding off binary floats."""
    from fractions import Fraction
    op = expr.get('op')
    if op in {'add', 'subtract', 'multiply', 'divide'}:
        a, b = (_round_operand(expr[k], value, aggregates) for k in ('a', 'b'))
        if op == 'add': return a + b
        if op == 'subtract': return a - b
        if op == 'multiply': return a * b
        if b == 0:
            raise CheckError('division by zero in decimal rounding')
        return a / b
    if op == 'sum' and aggregates:
        return sum((Fraction(str(_num(normalise(row.get(expr['field'])))))
                    for row in value(expr['of'])), Fraction(0))
    return Fraction(str(_num(normalise(value(expr)))))


def _rounded(expr: dict, value, aggregates=False):
    places = expr.get('places', 2)
    if 'mode' not in expr:
        return round(_num(normalise(value(expr['of']))), places)
    if errors := rounding_problems(expr):
        raise CheckError('; '.join(errors))
    from fractions import Fraction
    number = _round_operand(expr['of'], value, aggregates)
    scale = Fraction(10 ** places) if places >= 0 else Fraction(1, 10 ** -places)
    scaled = abs(number * scale)
    integer, remainder = divmod(scaled.numerator, scaled.denominator)
    twice = 2 * remainder
    if twice > scaled.denominator or (twice == scaled.denominator
            and (expr['mode'] == 'half_up' or integer % 2)):
        integer += 1
    rounded = (integer if number >= 0 else -integer) / scale
    return rounded.numerator if rounded.denominator == 1 else _num(float(rounded))


SCALAR_OPS = {"only", "extract", "number", "range_bound", "parse_date", "date_add", "days_between", "compare"}
#: Operations `evaluate` accepts besides SCALAR_OPS (named in its unknown-op error).
TARGET_OPS = {"add", "bind_rows", "count", "derive_rows", "difference", "divide", "exists", "field",
              "filter", "intersection", "latest", "literal", "max", "min", "multiply", "pluck",
              "record", "round", "rows", "select", "set", "subtract", "sum", "text", "unique"}
_DECIMAL = r"[+-]?(?:\d{1,3}(?:,\d{3})+|\d+)(?:\.\d+)?"


def comparison_problems(expr: dict) -> list[str]:
    if 'mode' not in expr:
        return []
    if expr['mode'] != 'exact' or expr.get('value_type') != 'number':
        return ['compare mode must be exact and requires value_type number']
    return []


def _comparison_operand(expr: dict, value, aggregates=False):
    """Exact basic arithmetic over the decimal values of the source operands."""
    from fractions import Fraction
    op = expr.get('op')
    if op in {'add', 'subtract', 'multiply', 'divide'}:
        a, b = (_comparison_operand(expr[key], value, aggregates) for key in ('a', 'b'))
        if op == 'add': return a + b
        if op == 'subtract': return a - b
        if op == 'multiply': return a * b
        if b == 0:
            raise CheckError('division by zero in exact comparison')
        return a / b
    if op == 'sum' and aggregates:
        return sum((_scalar_value({'op': 'number', 'of': None},
                                  lambda _, row=row: row.get(expr['field']), exact_decimal=True)
                    for row in value(expr['of'])), Fraction(0))
    if op == 'number' and expr.get('of', {}).get('op') in {'add', 'subtract', 'multiply', 'divide', 'sum', 'number'}:
        return _comparison_operand(expr['of'], value, aggregates)
    if op in {'number', 'range_bound'}:
        return _scalar_value(expr, value, exact_decimal=True)
    raw = value(expr)
    return _scalar_value({'op': 'number', 'of': None}, lambda _: raw, exact_decimal=True)


def _scalar_value(expr: dict, value, *, exact_decimal=False, aggregates=False):
    """Explicit source parsing: ambiguity and mixed units are never guessed away."""
    op = expr["op"]
    if op == "only":
        rows = value(expr["of"])
        if not isinstance(rows, list) or len(rows) != 1:
            raise CheckError("only requires exactly one source value")
        return rows[0]
    if op == "extract":
        text = value(expr["of"])
        if not isinstance(text, str):
            raise CheckError("extract requires source text")
        matches = list(re.finditer(expr["pattern"], text))
        if len(matches) != 1 or matches[0].start() == matches[0].end():
            raise CheckError("extract requires exactly one nonempty match; publish how ambiguous evidence is resolved")
        result = matches[0].group(expr.get("group", 0))
        if result is None:
            raise CheckError("extract capture did not participate")
        return result
    if op in {"number", "range_bound"}:
        raw = value(expr["of"])
        if op == "number" and type(raw) in (int, float):
            if exact_decimal:
                from fractions import Fraction
                return Fraction(str(_num(raw)))
            return _num(raw)
        if not isinstance(raw, str):
            raise CheckError("amount parsing requires source text or a number")
        raw = raw.strip().strip("*`").strip().lstrip("~≈").strip()
        raw = raw.replace("−", "-").replace("–", "-").replace("—", "-")
        # A single leading currency label is formatting, not a conversion.
        raw = re.sub(r"^([+-]?)(?:HK\$|HKD|RMB|CNY|USD|\$|¥|￥|€|£)\s*", r"\1", raw, flags=re.I)
        pattern = _DECIMAL if op == "number" else rf"({_DECIMAL})\s*(?:-|~|to|至)\s*({_DECIMAL})"
        match = re.fullmatch(pattern, raw, flags=re.I)
        if not match:
            raise CheckError("amount is not one explicit decimal or range; units, alternatives and extra prose require a public parsing rule")
        def decimal(text):
            cleaned = text.replace(",", "")
            if exact_decimal:
                from fractions import Fraction
                return Fraction(cleaned)
            return _num(float(cleaned) if "." in cleaned else int(cleaned))
        if op == "number":
            return decimal(raw)
        lower, upper = decimal(match[1]), decimal(match[2])
        if lower > upper or expr.get("bound") not in {"lower", "upper"}:
            raise CheckError("range needs ordered bounds and bound='lower' or 'upper'")
        return lower if expr["bound"] == "lower" else upper
    if op == "parse_date":
        from datetime import datetime
        raw, fmt = value(expr["of"]), expr.get("format")
        if not isinstance(raw, str) or fmt not in {"%Y-%m-%d", "%Y/%m/%d", "%m/%d"}:
            raise CheckError("parse_date requires explicit ISO, year/month/day or month/day format")
        if fmt == "%m/%d":
            year = expr.get("year")
            if type(year) is not int or not 1 <= year <= 9999:
                raise CheckError("month/day parsing requires an explicitly published year")
            raw, fmt = f"{year}/{raw}", "%Y/" + fmt
        elif "year" in expr:
            raise CheckError("do not override a year already present in the source")
        return datetime.strptime(raw, fmt).date().isoformat()
    if op == "date_add":
        from datetime import date, timedelta
        days = _num(normalise(value(expr["days"])))
        if type(days) is not int:
            raise CheckError("date_add requires integer calendar days")
        return (date.fromisoformat(str(value(expr["date"]))) + timedelta(days=days)).isoformat()
    if op == "days_between":
        from datetime import date
        return (date.fromisoformat(str(value(expr["end"]))) - date.fromisoformat(str(value(expr["start"])))).days
    if op == "compare":
        from datetime import date
        kind, comparison = expr.get("value_type"), expr.get("comparison")
        if errors := comparison_problems(expr):
            raise CheckError('; '.join(errors))
        if expr.get('mode') == 'exact':
            a, b = (_comparison_operand(expr[key], value, aggregates) for key in ('a', 'b'))
        else:
            a, b = value(expr["a"]), value(expr["b"])
        if kind == "number" and expr.get('mode') != 'exact':
            a, b = _num(normalise(a)), _num(normalise(b))
        elif kind == "date":
            a, b = date.fromisoformat(a), date.fromisoformat(b)
        elif kind != 'number' and (kind != "string" or not isinstance(a, str) or not isinstance(b, str)):
            raise CheckError("compare requires explicit number, date or string operands")
        if comparison not in {"eq", "ne", "lt", "lte", "gt", "gte"}:
            raise CheckError("unknown comparison")
        return {"eq": a == b, "ne": a != b, "lt": a < b, "lte": a <= b, "gt": a > b, "gte": a >= b}[comparison]
    raise CheckError(f"unsupported scalar operation: {op}")


def row_value(expr: dict, row: dict, depth: int = 0):
    """Bounded data expressions for keyed business conclusions; never Python eval."""
    if depth > 40 or not isinstance(expr, dict):
        raise CheckError("invalid or overly nested row derivation")
    def value(sub):
        return row_value(sub, row, depth + 1)
    op = expr.get("op")
    if op in SCALAR_OPS:
        return _scalar_value(expr, value)
    if op == "field":
        result = _dig(row, expr["path"])
        if result is None:
            raise CheckError("missing row field requires an explicit uncertainty branch")
        return result
    if op == "literal":
        if not expr.get("why") or isinstance(expr.get("value"), (dict, list)):
            raise CheckError("row constants need a public-rule explanation and scalar value")
        return expr["value"]
    if op == "if":
        _require_row_filter(expr["where"])
        return value(expr["then"] if _match_validated(row, expr["where"]) else expr["else"])
    if op in {"add", "subtract", "multiply", "divide"}:
        a, b = (_num(normalise(value(expr[k]))) for k in ("a", "b"))
        if op == "divide" and b == 0:
            raise CheckError("division by zero in row derivation")
        if op == "add": return a + b
        if op == "subtract": return a - b
        if op == "multiply": return a * b
        return a / b
    if op == "round":
        return _rounded(expr, value)
    raise CheckError(f"unsupported row operation: {op}; row expressions support field, literal, if, "
                     "add/subtract/multiply/divide, round and the scalar operations "
                     + ", ".join(sorted(SCALAR_OPS)))


def binding_problems(expr: dict) -> list[str]:
    fields = expr.get('fields')
    if (not isinstance(fields, dict) or not fields
            or any(not isinstance(name, str) or not re.fullmatch(r'[A-Za-z_][A-Za-z0-9_]*', name)
                   for name in fields)):
        return ['bind_rows requires nonempty simple field names and expressions']
    return []


def evaluate(expr: Any, ws: Workspace, role: str) -> Any:
    """Evaluate one expression. `role` fixes which root it may read."""
    if not isinstance(expr, dict) or "op" not in expr:
        raise CheckError(f"not an expression: {expr!r}")
    op = expr["op"]
    if op in SCALAR_OPS:
        return _scalar_value(expr, lambda sub: evaluate(sub, ws, role), aggregates=True)
    if op == "record":
        if not isinstance(expr.get("fields"), dict) or not expr["fields"]:
            raise CheckError("record requires named derived field expressions")
        return {key: evaluate(sub, ws, role) for key, sub in expr["fields"].items()}

    if op == "literal":
        if role == "source" and "why" not in expr:
            # Give the corrected expression, not just the objection. The
            # designer burned nine repair attempts on kw-a005 re-emitting the
            # same literal: it was told the rule each time and never the shape
            # of the fix. A paste-ready form costs nothing and does not weaken
            # the rule -- `why` still has to be written, and a literal that
            # cannot justify itself still cannot be a target.
            fixed = dict(expr)
            fixed["why"] = "<one sentence: why this value cannot be derived from the fixture>"
            raise CheckError(
                "a literal target must carry a 'why' explaining why it cannot be "
                "derived from the fixture -- hand-typed expected values are how "
                "an answer key comes to say 26 when the truth is 27.\n"
                f"      replace it with: {json.dumps(fixed, ensure_ascii=False)}\n"
                "      keep 'value' exactly as it is and add only 'why'")
        return expr["value"]

    if op == "rows":
        text = ws.read(expr["file"], role)
        try:
            rows = _load_rows(text, expr["file"])
        except ContractError as exc:
            raise (SubmissionInvalid if role == "submitted" else CheckError)(str(exc)) from exc
        _require_row_filter(expr.get("where"), allow_none="where" not in expr)
        return [r for r in rows if _match_validated(r, expr.get("where"))]

    if op == "field":
        text = ws.read(expr["file"], role)
        try:
            data = strict_json(text)
        except ContractError as exc:
            error = SubmissionInvalid if role == "submitted" else CheckError
            raise error(f"{expr['file']} is not valid JSON: {exc}") from exc
        return _dig(data, expr.get("path", ""))

    if op == "text":
        return ws.read(expr["file"], role)

    if op == "exists":
        try:
            ws.read(expr["file"], role)
            return True
        except SubmissionMissing:
            return False

    if op == "count":
        return len(evaluate(expr["of"], ws, role) or [])

    if op == "sum":
        rows = evaluate(expr["of"], ws, role) or []
        return sum(_num(normalise(r.get(expr["field"]))) for r in rows)

    if op in {"min", "max"}:
        values = evaluate(expr["of"], ws, role)
        if not isinstance(values, list) or not values:
            raise CheckError("numeric extrema require a nonempty collection")
        if "fields" in expr:
            fields = expr["fields"]
            if not isinstance(fields, list) or not fields or any(not isinstance(f, str) or not f for f in fields):
                raise CheckError("numeric extrema fields must name source row fields")
            values = [_dig(row, name) for row in values for name in fields]
        numbers = [_num(normalise(value)) for value in values]
        return min(numbers) if op == "min" else max(numbers)

    if op == "pluck":
        rows = evaluate(expr["of"], ws, role) or []
        return [r.get(expr["field"]) for r in rows]

    if op == "select":
        rows = evaluate(expr["of"], ws, role)
        fields = expr["fields"]
        if not isinstance(rows, list) or not isinstance(fields, dict) or not fields:
            raise CheckError("select requires rows and a nonempty output-field mapping")
        result = []
        for row in rows:
            projected = {alias: _dig(row, path) for alias, path in fields.items()}
            if any(value is None for value in projected.values()):
                raise CheckError("select addressed a missing field; use an explicit uncertainty rule")
            result.append(projected)
        return result

    if op == "bind_rows":
        if problems := binding_problems(expr):
            raise CheckError('; '.join(problems))
        rows = evaluate(expr['of'], ws, role)
        if not isinstance(rows, list) or any(not isinstance(row, dict) for row in rows):
            raise CheckError('bind_rows requires a collection of records')
        # Bind policy values once in the existing read role. Row expressions
        # stay local to their row and never gain access to another filesystem.
        values = {name: evaluate(value, ws, role) for name, value in expr['fields'].items()}
        if any(value is not None and type(value) not in (str, bool, int, float)
               for value in values.values()):
            raise CheckError('bind_rows values must be scalars, not records or collections')
        if any(type(value) is float and not math.isfinite(value) for value in values.values()):
            raise CheckError('bind_rows values must be finite')
        if any(set(values) & set(row) for row in rows):
            raise CheckError('bind_rows cannot overwrite an existing row field')
        return [{**row, **values} for row in rows]

    if op == "derive_rows":
        rows = evaluate(expr["of"], ws, role)
        if not isinstance(rows, list) or not isinstance(expr.get("fields"), dict) or not expr["fields"]:
            raise CheckError("derive_rows requires a row collection and output fields")
        return [{name: row_value(value, row) for name, value in expr["fields"].items()} for row in rows]

    if op == "filter":
        _require_row_filter(expr["where"])
        return [row for row in evaluate(expr["of"], ws, role) if _match_validated(row, expr["where"])]

    if op == "latest":
        # Resolve revisions by a business key. Conflicting ties need a rule.
        rows = evaluate(expr["of"], ws, role)
        groups = {}
        if not isinstance(expr["by"], list) or not expr["by"]:
            raise CheckError("latest requires nonempty grouping fields")
        for row in rows:
            key = tuple(_hashable(_dig(row, field)) for field in expr["by"])
            if any(v is None for v in key):
                raise CheckError("latest has a missing grouping key")
            value = _dig(row, expr["order_by"])
            if expr["value_type"] == "datetime":
                from datetime import datetime
                value = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
            elif expr["value_type"] == "number":
                value = _num(normalise(value))
            elif expr["value_type"] == "string" and isinstance(value, str):
                pass
            else:
                raise CheckError("latest needs explicit datetime, number or string ordering")
            if key in groups and groups[key][0] == value and groups[key][1] != row:
                raise CheckError("latest encountered conflicting tied revisions")
            if key not in groups or value > groups[key][0]:
                groups[key] = value, row
        return [row for _, row in groups.values()]

    if op in {"set", "unique"}:
        members = _set_members(evaluate(expr["of"], ws, role))
        return [members[k] for k in sorted(members, key=str)]

    if op in {"difference", "intersection"}:
        left = _set_members(evaluate(expr["a"], ws, role))
        right = _set_members(evaluate(expr["b"], ws, role))
        keys = left.keys() - right.keys() if op == "difference" else left.keys() & right.keys()
        return [left[k] for k in sorted(keys, key=str)]

    if op == "round":
        # Older top-level expressions coerced places to int; keep their replay
        # behavior while explicit decimal modes require a typed precision.
        legacy = {**expr, 'places': int(expr.get('places', 2))} if 'mode' not in expr else expr
        return _rounded(legacy, lambda sub: evaluate(sub, ws, role), aggregates=True)

    if op == "divide":
        denom = _num(normalise(evaluate(expr["b"], ws, role)))
        if denom == 0:
            raise CheckError("division by zero in a target expression")
        return _num(normalise(evaluate(expr["a"], ws, role))) / denom

    if op == "multiply":
        return (_num(normalise(evaluate(expr["a"], ws, role)))
                * _num(normalise(evaluate(expr["b"], ws, role))))

    if op == "subtract":
        return (_num(normalise(evaluate(expr["a"], ws, role)))
                - _num(normalise(evaluate(expr["b"], ws, role))))

    if op == "add":
        return (_num(normalise(evaluate(expr["a"], ws, role)))
                + _num(normalise(evaluate(expr["b"], ws, role))))

    raise CheckError(f"unknown operation {op!r}; target operations are: "
                     + ", ".join(sorted(TARGET_OPS | SCALAR_OPS)))


# --------------------------------------------------------------------------
# checks
# --------------------------------------------------------------------------

ASSERTIONS = ("equals", "numeric_within", "set_equals", "multiset_equals", "subset_of",
              "superset_of", "contains", "absent", "present", "matches",
              "row_count", "fixture_intact", "optimal_path", "optimal_subset")


def _equality_key(value, unordered_paths, path=""):
    """Preserve whole-row associations and multiplicity at named array paths."""
    if isinstance(value, dict):
        return ("object", tuple(sorted((key, _equality_key(item, unordered_paths,
            f"{path}.{key}" if path else key)) for key, item in value.items())))
    if isinstance(value, list):
        rows = [_hashable(item) for item in value]
        return ("unordered-array", tuple(sorted(Counter(rows).items(), key=str))) if path in unordered_paths else ("array", tuple(rows))
    return _hashable(value)

#: `fixture_intact` is the one assertion that reads neither the submission nor a
#: target expression. It re-runs the oracle projections against the LIVE fixture
#: and compares them to the projection frozen at build time.
#:
#: Written first as an ordinary check comparing the fixture to itself, it could
#: only ever pass -- a guardrail that cannot fire is worse than none, because it
#: reports protection that does not exist. Fixture integrity is a property of the
#: environment, so it needs a mechanism, not an expression.


@dataclass
class Check:
    id: str
    kind: str
    weight: float
    basis: str                       # the public wording; must be published
    assertion: str
    actual: dict                     # expression over the agent's submission
    target: dict | None = None       # expression over the fixture
    weight_basis: str = ""           # why this weight, not another -- reviewable
    tolerance: float = 0.0
    band: str = "core"
    requires: list[str] = field(default_factory=list)
    note: str = ""
    dimension: str = "core"     # reward.toml grouping
    step: str = ""              # which graded step this belongs to
    unordered_paths: list[str] = field(default_factory=list)

    def validate(self) -> list[str]:
        problems = []
        if type(self.weight) not in (int, float) or not math.isfinite(self.weight) or self.weight < 0:
            problems.append(f"{self.id}: weight must be finite and nonnegative")
        elif self.kind == "objective" and self.weight == 0:
            problems.append(f"{self.id}: objective weight must be positive")
        if self.kind == "guardrail" and self.weight != 0:
            problems.append(f"{self.id}: guardrails must have zero weight")
        if self.kind not in KINDS:
            problems.append(f"{self.id}: kind must be one of {KINDS}")
        if self.band not in BANDS:
            problems.append(f"{self.id}: band must be one of {BANDS}")
        if self.assertion not in ASSERTIONS:
            problems.append(f"{self.id}: unknown assertion {self.assertion!r}")
        if (not isinstance(self.unordered_paths, list)
                or any(not isinstance(path, str) or not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*(?:\.[A-Za-z_][A-Za-z0-9_]*)*", path)
                       for path in self.unordered_paths)
                or len(set(self.unordered_paths)) != len(self.unordered_paths)):
            problems.append(f"{self.id}: unordered_paths must be distinct dotted object paths")
        elif self.unordered_paths and self.assertion != "equals":
            problems.append(f"{self.id}: unordered_paths applies only to equals")
        if not self.basis.strip():
            problems.append(f"{self.id}: no public wording -- a scored rule the "
                            "agent was never told is an unpublished requirement")
        # `present` asks that something exist, which is an objective by
        # definition: it cannot hold on an untouched fixture, and a guardrail
        # that fails there would zero every attempt.
        if self.kind == "guardrail" and self.assertion == "present":
            problems.append(f"{self.id}: a guardrail cannot assert 'present' -- "
                            "it asks the agent to DO something, which is an "
                            "objective. Guardrails assert negative space.")
        if self.kind == "guardrail" and self.requires:
            problems.append(f"{self.id}: guardrails are never gated -- a rule the "
                            "agent was told to respect is broken whether or not "
                            "the objective chain reached that far")
        if (self.assertion not in ("present", "absent", "fixture_intact")
                and self.target is None):
            problems.append(f"{self.id}: assertion {self.assertion!r} needs a target")
        if self.assertion == "numeric_within" and self.tolerance <= 0:
            problems.append(f"{self.id}: numeric_within needs a positive tolerance")
        if self.assertion in ("optimal_path", "optimal_subset"):
            if (type(self.tolerance) not in (int, float)
                    or not math.isfinite(self.tolerance) or self.tolerance < 0):
                problems.append(f"{self.id}: {self.assertion} needs a finite nonnegative reporting tolerance")
        return problems


def _fixture_intact(ws: Workspace) -> dict:
    """Check every protected byte, including files no projection reads."""
    manifest = ws.fixture_manifest
    if manifest is None and ws.derived is not None:
        path = ws.derived.parent / "fixture-manifest.json"
        if path.is_file():
            manifest = strict_json(path.read_text())
    if manifest is not None:
        import hashlib
        expected = manifest.get("files")
        if not isinstance(expected, dict):
            raise CheckError("invalid fixture manifest")
        actual = {}
        for path in ws.source.rglob("*"):
            if path.is_symlink():
                return {"passed": False, "reason": "fixture contains a symlink"}
            if path.is_file():
                actual[str(path.relative_to(ws.source))] = hashlib.sha256(path.read_bytes()).hexdigest()
            elif not path.is_dir():
                return {"passed": False, "reason": "fixture contains a non-regular entry"}
        if actual != expected:
            return {"passed": False, "reason": "protected fixture bytes or file inventory changed"}
        if ws.projections is not None:
            from .oracle import verify
            drift = verify(ws.source, ws.projections, ws.derived)
            if drift:
                raise CheckError("frozen oracle projections disagree with the protected fixture: " + "; ".join(drift))
        return {"passed": True, "reason": ""}
    if ws.projections is None or ws.derived is None:
        raise CheckError(
            "fixture_intact needs the bundle's projections and derived directory; "
            "without them this guardrail cannot be evaluated and must not be "
            "reported as intact")
    from .oracle import verify
    drift = verify(ws.source, ws.projections, ws.derived)
    return {"passed": not drift, "reason": "; ".join(drift)}


def run_check(check: Check, ws: Workspace) -> dict:
    """Evaluate one check. Raises rather than scoring on any evaluation fault."""
    if check.assertion == "fixture_intact":
        out = _fixture_intact(ws)
        return {"id": check.id, "passed": out["passed"], "reason": out["reason"],
                "target": None, "actual": None}

    target = (evaluate(check.target, ws, "source")
              if check.target is not None else None)
    path_problem = None
    if check.assertion in ("optimal_path", "optimal_subset"):
        from .path_witness import InvalidProblem, _number
        if check.assertion == "optimal_path":
            from .path_witness import prepare
        else:
            from .subset_witness import prepare
        try:
            path_problem = prepare(target)
            _number(check.tolerance)
        except InvalidProblem as exc:
            raise CheckError(f"invalid {check.assertion} source or tolerance: {exc}") from exc
    # Everything that depends only on the target is settled here, before the
    # submission is read, so a fault in it stays a grader error.
    if check.assertion == "row_count":
        int(_num(normalise(target)))
    elif check.assertion == "matches":
        try:
            re.compile(str(target))
        except re.error as exc:
            raise CheckError(f"matches target is not a valid pattern: {exc}") from exc
    elif check.assertion == "multiset_equals" and not isinstance(target, (list, tuple)):
        raise CheckError("multiset_equals target must be a row collection")
    try:
        actual = evaluate(check.actual, ws, "submitted")
    except SubmissionMissing as exc:
        # An `absent` check asks that something NOT be there, so a missing file
        # satisfies it. Treating the missing file as a failure made every
        # `absent` guardrail fail on the untouched fixture, which reads as a
        # mis-specified guardrail and blocks the bundle -- when in fact nothing
        # forbidden had been written, because nothing had been written at all.
        # A guardrail asserts the agent did NOT do something. Doing nothing at
        # all therefore satisfies it, whatever the assertion: the violation has
        # not happened. Treating the missing file as a failure made guardrails
        # fail on the untouched fixture, which reads as "mis-specified guardrail"
        # and blocks the bundle for a violation nobody committed.
        if check.kind == "guardrail" or check.assertion == "absent":
            return {"id": check.id, "passed": True,
                    "reason": "nothing submitted, so nothing forbidden is present",
                    "target": target, "actual": None}
        # Otherwise a missing or unparseable submission is a model failure, not
        # an evaluation fault -- the agent was asked to produce it.
        return {"id": check.id, "passed": False, "reason": str(exc),
                "target": target, "actual": None}
    except SubmissionInvalid as exc:
        return {"id": check.id, "passed": False, "reason": str(exc),
                "target": target, "actual": None}
    except SUBMISSION_FAULTS as exc:
        # The target already evaluated over the fixture, so whatever failed
        # here failed on the agent's bytes: a string where the expression
        # needed rows, a row missing the field it sums. That is a wrong
        # answer, scored 0 for this check. Raising made `criteria.py` exit
        # non-zero under `set -e`, no reward.json was written, and a model
        # failure was recorded as a void.
        return _submission_fault(check, target, None, exc)
    try:
        return _compare(check, target, actual, path_problem)
    except SUBMISSION_FAULTS as exc:
        return _submission_fault(check, target, actual, exc)


#: Faults raised while reading or comparing the submission. Everything that
#: depends only on the fixture is evaluated before these are caught, so a
#: grader defect still raises.
SUBMISSION_FAULTS = (CheckError, TypeError, ValueError, AttributeError,
                     KeyError, IndexError, RecursionError)


def _submission_fault(check: Check, target, actual, exc: BaseException) -> dict:
    kind = "guardrail" if check.kind == "guardrail" else "check"
    return {"id": check.id, "passed": False, "submission_error": True,
            "reason": f"submission error ({kind} could not be satisfied by this "
                      f"submission): {type(exc).__name__}: {str(exc)[:300]}",
            "target": target if not isinstance(target, str) or len(target) < 200
                      else target[:200], "actual": None}


def _compare(check: Check, target, actual, path_problem) -> dict:
    if path_problem is not None:
        if check.assertion == "optimal_path":
            from .path_witness import check_witness
        else:
            from .subset_witness import check_witness
        passed, reason = check_witness(path_problem, actual, check.tolerance)
        optimum = path_problem['optimum']
        if check.assertion == "optimal_subset":
            return {"id": check.id, "passed": passed, "reason": reason,
                    "target": {"feasible": optimum is not None,
                               "objective_values": [str(value) for value in optimum] if optimum is not None else None},
                    "actual": actual}
        return {"id": check.id, "passed": passed, "reason": reason,
                "target": {"feasible": optimum is not None,
                           "bottleneck": float(optimum[0]) if optimum else None,
                           "cost": float(optimum[1]) if optimum else None},
                "actual": actual}

    a, t = normalise(actual), normalise(target)
    # The RAW target decides: a number the fixture computes to, never text
    # that merely looks numeric (section "3.1" is not the number 3.1).
    a = _as_target_type(a, target)
    passed, reason = False, ""

    if check.assertion == "equals":
        passed = (_equality_key(a, check.unordered_paths) == _equality_key(t, check.unordered_paths)
                  if check.unordered_paths else _hashable(a) == _hashable(t))
        reason = "" if passed else f"expected {t!r}, got {a!r}"
    elif check.assertion == "numeric_within":
        try:
            passed = abs(_num(a) - _num(t)) <= check.tolerance
            reason = "" if passed else f"expected {t} +/- {check.tolerance}, got {a}"
        except CheckError as exc:
            passed, reason = False, str(exc)
    elif check.assertion == "set_equals":
        sa, st = _as_set(actual), _as_set(target)
        passed = sa == st
        reason = "" if passed else (f"missing {sorted(st - sa, key=str)[:5]}, "
                                    f"unexpected {sorted(sa - st, key=str)[:5]}")
    elif check.assertion == "multiset_equals":
        if not isinstance(target, (list, tuple)):
            raise CheckError("multiset_equals target must be a row collection")
        if not isinstance(actual, (list, tuple)):
            passed, reason = False, "expected a row collection"
        else:
            ca = Counter(_hashable(row) for row in a)
            ct = Counter(_hashable(row) for row in t)
            passed = ca == ct
            reason = "" if passed else (f"missing {(ct - ca).most_common(5)!r}, "
                                        f"unexpected {(ca - ct).most_common(5)!r}")
    elif check.assertion == "subset_of":
        sa, st = _as_set(actual), _as_set(target)
        passed = sa <= st
        reason = "" if passed else f"not permitted: {sorted(sa - st, key=str)[:5]}"
    elif check.assertion == "superset_of":
        sa, st = _as_set(actual), _as_set(target)
        passed = sa >= st
        reason = "" if passed else f"missing {sorted(st - sa, key=str)[:5]}"
    elif check.assertion == "contains":
        missing = [m for m in _members(target) if not _found(m, actual)]
        passed = not missing
        reason = "" if passed else f"not found: {missing[:5]!r}"
    elif check.assertion == "absent":
        present = [m for m in _members(target) if _found(m, actual)]
        passed = not present
        reason = "" if passed else f"present and must not be: {present[:5]!r}"
    elif check.assertion == "present":
        passed = any(leaf not in (None, "") for leaf in _leaves(actual))
        reason = "" if passed else "absent"
    elif check.assertion == "matches":
        passed = bool(re.search(str(target), str(actual or ""), re.I))
        reason = "" if passed else f"does not match {target!r}"
    elif check.assertion == "row_count":
        # The agent may submit a scalar where a collection was expected. That is
        # a wrong answer, not an evaluation fault, so it is scored rather than
        # raised -- `len(3)` would otherwise take down the whole grader run.
        if actual is None:
            count = 0
        elif isinstance(actual, (list, tuple, set, dict, str)):
            count = len(actual)
        else:
            count = None
        if count is None:
            passed, reason = False, f"expected a collection, got {type(actual).__name__}"
        else:
            passed = count == int(_num(t))
            reason = "" if passed else f"expected {int(_num(t))} rows, got {count}"

    return {"id": check.id, "passed": bool(passed), "reason": reason,
            "target": target if not isinstance(target, str) or len(target) < 200
                      else target[:200], "actual": actual
                      if not isinstance(actual, str) or len(actual) < 200
                      else actual[:200]}


def load(path: Path) -> list[Check]:
    raw = json.loads(Path(path).read_text())
    return [Check(**c) for c in raw["checks"]]


def grade(checks: list[Check], ws: Workspace) -> dict:
    """Score a submission.

    Guardrails zero the task on violation and are never gated. Objectives are
    weighted and may be prefix-gated; a gated-out objective is reported as such,
    never as a failure, because a criterion that was never attempted says
    nothing about ability.
    """
    outputs = ws.outputs
    if outputs is None and ws.derived is not None:
        contract_file = ws.derived.parent / "outputs.json"
        if contract_file.is_file():
            outputs = strict_json(contract_file.read_text())["outputs"]
    contract_errors = submission_errors(ws.submitted, outputs, ws.step) if outputs else []
    results: dict[str, dict] = {}
    for check in checks:
        if check.kind == "guardrail":
            results[check.id] = run_check(check, ws)

    violated = [r for r in results.values() if not r["passed"]]

    order, seen, visiting = [], set(), set()
    if len({c.id for c in checks}) != len(checks):
        raise CheckError("duplicate check IDs")

    def visit(check: Check) -> None:
        if check.id in visiting:
            raise CheckError(f"cyclic check dependency: {check.id}")
        if check.id in seen:
            return
        visiting.add(check.id)
        for dep in check.requires:
            match = next((c for c in checks if c.id == dep), None)
            if match is None:
                raise CheckError(f"unknown prerequisite: {dep}")
            visit(match)
        visiting.remove(check.id)
        seen.add(check.id)
        order.append(check)

    for check in checks:
        if check.kind == "objective":
            visit(check)

    for check in order:
        blocked = [d for d in check.requires
                   if not results.get(d, {}).get("passed", False)]
        if blocked:
            results[check.id] = {"id": check.id, "passed": False,
                                 "gated_out": True, "blocked_by": blocked}
            continue
        if not violated:
            results[check.id] = run_check(check, ws)
            continue
        # A violated guardrail already decides the reward (0). A target that can
        # no longer be computed -- say over a fixture the agent damaged -- must
        # not turn that settled 0 into a grader crash and a void episode.
        try:
            results[check.id] = run_check(check, ws)
        except CheckError as exc:
            results[check.id] = {"id": check.id, "passed": False,
                                 "reason": f"not evaluated: a guardrail was violated ({exc})"}

    objectives = [c for c in checks if c.kind == "objective"]
    total = sum(c.weight for c in objectives) or 1.0
    earned = sum(c.weight for c in objectives
                 if results[c.id].get("passed") and not results[c.id].get("gated_out"))
    reward = 0.0 if violated or contract_errors else round(earned / total, 4)

    return {
        "reward": reward,
        "guardrails_violated": [r["id"] for r in violated],
        "checks": {k: v for k, v in results.items()},
        "earned": earned, "total": total,
        **({"contract_errors": contract_errors} if outputs else {}),
    }
