"""Port the Arena 261011 output-contract fixes into a `contracts.py` (2026-10-12).

    python3.11 -I -B apply_central.py <contracts.py> [...]        # patch in place
    python3.11 -I -B apply_central.py --check <contracts.py> [...] # report only
    --no-sentence  leave the public contract sentence alone (older wording; edit it by hand)

Three defects, all in the shared output-contract module that every batch-4 and
fb2 bundle ships twice (tests/ and steps/*/solution/):

- R24/R30/R31 and R19: `uniqueItems` compared raw JSON text, so 91 and 91.0, or
  two spellings that differ only in letter case, passed as two entries and then
  collapsed into one when the answer set was scored. Uniqueness now uses the
  grader's own equality (`normalise`, then numbers by value).
- R25: the extra-deliverable guard only saw regular files, folders and symlinks,
  so a FIFO (or socket/device) escaped it, and a FIFO at a declared path would
  block the grader on read. Every entry is now classified with lstat; only
  regular files may be declared outputs, and nothing else may exist.
- Sweep (stage 2): Python's `$` matched before a final newline, so an identifier
  with a trailing newline passed its published pattern; patterns now use the
  ECMA-262 end anchor JSON Schema specifies.
- R23: deeply nested JSON raised RecursionError outside the invalid-output
  handler and crashed the grader. Parsing now turns it into a contract error
  (the normal zero-result record), and any document nested deeper than
  MAX_JSON_DEPTH is refused before a later recursive pass can overflow.

The patch is anchored on exact text. A file that does not contain every anchor
is refused untouched, so a variant this script was not written for is reported
rather than half-patched. Already-patched files are recognised and left alone.
"""
from __future__ import annotations

import sys
from pathlib import Path

MARK = "Arena 261011"

IMPORTS_OLD = "import json\nimport math\nimport re\nfrom pathlib import Path, PurePosixPath\n"
IMPORTS_NEW = "import json\nimport math\nimport os\nimport re\nimport stat\nfrom pathlib import Path, PurePosixPath\n"

STRICT_OLD = '''    try:
        return json.loads(text, object_pairs_hook=pairs, parse_constant=constant)
    except (ValueError, TypeError) as exc:
        raise ContractError(f"invalid JSON: {exc}") from exc
'''
STRICT_NEW = '''    try:
        data = json.loads(text, object_pairs_hook=pairs, parse_constant=constant)
    except RecursionError as exc:
        # Arena 261011 R23: this escaped the invalid-output handler and crashed the grader.
        raise ContractError(f"invalid JSON: nested deeper than {MAX_JSON_DEPTH} levels") from exc
    except (ValueError, TypeError) as exc:
        raise ContractError(f"invalid JSON: {exc}") from exc
    if not _depth_within(data, MAX_JSON_DEPTH):
        raise ContractError(f"invalid JSON: nested deeper than {MAX_JSON_DEPTH} levels")
    return data


#: Deliverables are small JSON documents. Refusing anything nested deeper keeps
#: every later recursive pass (schema checks, normalisation, hashing) far inside
#: Python's recursion limit, so a hostile file scores 0 instead of crashing.
MAX_JSON_DEPTH = 64
#: A declared deliverable larger than this is refused unread.
MAX_DELIVERABLE_BYTES = 32 * 1024 * 1024


def _depth_within(value, limit: int) -> bool:
    stack = [(value, 1)]
    while stack:
        item, depth = stack.pop()
        if isinstance(item, (dict, list)):
            if depth > limit:
                return False
            stack.extend((child, depth + 1) for child in (item.values() if isinstance(item, dict) else item))
    return True
'''

UNIQUE_OLD = '''        if schema.get("uniqueItems") and len({json.dumps(v, sort_keys=True) for v in value}) != len(value):
            errors.append(f"{where}: repeated array entries")
'''
UNIQUE_NEW = '''        if schema.get("uniqueItems") and len({_unique_key(v) for v in value}) != len(value):
            errors.append(f"{where}: repeated array entries (compared the way answers are compared)")
'''

UNIQUE_HELPERS = '''

def _unique_key(value) -> str:
    """An array entry's identity under the grader's own comparison rules.

    Arena 261011 R19/R24/R30/R31: comparing raw JSON text let 91 and 91.0, or two
    spellings that differ only in letter case, pass a published uniqueness rule
    as two entries and then collapse into one when the answer set was scored.
    Uniqueness is therefore decided by the equality the scoring uses.
    """
    try:
        from .checks_runtime import normalise
    except ImportError:  # the pipeline's source tree names that module checks.py
        from .checks import normalise
    return json.dumps(_by_value(normalise(value)), sort_keys=True, ensure_ascii=False)


def _by_value(value):
    """Numbers by value (91.0 is 91); booleans, text and null unchanged."""
    if isinstance(value, float) and not isinstance(value, bool) and value.is_integer():
        return int(value)
    if isinstance(value, list):
        return [_by_value(v) for v in value]
    if isinstance(value, dict):
        return {k: _by_value(v) for k, v in value.items()}
    return value


def schema_at(schema: dict, path: str) -> dict | None:'''
SCHEMA_AT_OLD = '''

def schema_at(schema: dict, path: str) -> dict | None:'''

WALK_OLD = '''    for path in sorted(root.rglob('*')):
        rel = path.relative_to(root).as_posix()
        if path.is_symlink() or (path.is_dir() and rel not in parents) or (path.is_file() and rel not in allowed):
            errors.append(f"{rel}: undeclared deliverable or symlink")
'''
WALK_NEW = '''    # Arena 261011 R25: every entry is classified with lstat. Only a declared
    # regular file or a folder that holds one may exist; a FIFO, socket or device
    # is neither and used to escape this rule (and to block the reader below).
    root = Path(root)
    for path in _entries(root, errors):
        rel = path.relative_to(root).as_posix()
        mode = os.lstat(path).st_mode
        if (stat.S_ISDIR(mode) and rel in parents) or (stat.S_ISREG(mode) and rel in allowed):
            continue
        kind = ("symlink" if stat.S_ISLNK(mode) else "folder" if stat.S_ISDIR(mode)
                else "file" if stat.S_ISREG(mode) else "special file")
        errors.append(f"{rel}: undeclared deliverable or symlink ({kind})")
'''

READ_OLD = '''            path = contained(root, output["file"])
            if allow_missing and not path.exists():
                continue
            doc = strict_json(path.read_text())
'''
READ_NEW = '''            path = contained(root, output["file"])
            if allow_missing and not os.path.lexists(path):
                continue
            info = os.lstat(path)
            if not stat.S_ISREG(info.st_mode):
                raise ContractError("a deliverable must be a regular file")
            if info.st_size > MAX_DELIVERABLE_BYTES:
                raise ContractError(f"a deliverable may not exceed {MAX_DELIVERABLE_BYTES} bytes")
            doc = strict_json(path.read_text())
'''

ENTRIES_OLD = '''def submission_errors(root: Path, outputs: list[dict], step: str | None = None,'''
ENTRIES_NEW = '''def _entries(root: Path, errors: list) -> list[Path]:
    """Every entry under `root`, never following a symlink; an unreadable folder is an error."""
    if not root.is_dir():
        return []
    found = []

    def unreadable(exc):
        where = Path(exc.filename).relative_to(root).as_posix() if exc.filename else "."
        errors.append(f"{where}: unreadable deliverable folder")

    for dirpath, dirnames, filenames in os.walk(root, onerror=unreadable):
        found += [Path(dirpath) / name for name in dirnames + filenames]
    return sorted(found)


def submission_errors(root: Path, outputs: list[dict], step: str | None = None,'''

CONTRACT_OLD = "numeric strings ignore thousands separators."
CONTRACT_NEW = ("numeric strings ignore thousands separators. A list that must not repeat an entry is "
                "checked by these same rules: a whole number and the same number written with a decimal point, "
                "or two texts that differ only in letter case, are one entry.")

EDITS = [("imports", IMPORTS_OLD, IMPORTS_NEW), ("strict_json", STRICT_OLD, STRICT_NEW),
         ("uniqueItems", UNIQUE_OLD, UNIQUE_NEW), ("unique helpers", SCHEMA_AT_OLD, UNIQUE_HELPERS),
         ("walk", WALK_OLD, WALK_NEW), ("read", READ_OLD, READ_NEW), ("entries", ENTRIES_OLD, ENTRIES_NEW),
         ("contract sentence", CONTRACT_OLD, CONTRACT_NEW)]


def patch(text: str, sentence: bool = True) -> str:
    if MARK in text:
        raise ValueError("already patched")
    edits = EDITS if sentence else [e for e in EDITS if e[0] != "contract sentence"]
    missing = [name for name, old, _ in edits if text.count(old) != 1]
    if missing:
        raise ValueError("anchors not found exactly once: " + ", ".join(missing))
    for _, old, new in edits:
        text = text.replace(old, new, 1)
    return text


# ---------------------------------------------------------------- stage 2
# Added 2026-10-12 from the funnel-go-live-review sweep: Python's `$` also matches
# before a final newline, so "C-103\n" passed `^C-[0-9]{3}$` although the published
# schema (ECMA-262 semantics) rejects it. Applied on top of stage 1.
MARK2 = "def _ecma_end(pattern: str) -> str:"
PATTERN_OLD = """    if kind == "string" and "pattern" in schema and not re.search(schema["pattern"], value):\n"""
PATTERN_NEW = """    if kind == "string" and "pattern" in schema and not re.search(_ecma_end(schema["pattern"]), value):\n"""
HELPER_ANCHOR = "\n\n\ndef _unique_key(value) -> str:"
HELPER = '\n\ndef _ecma_end(pattern: str) -> str:\n    """A published pattern with JSON Schema\'s (ECMA-262) end anchor.\n\n    In ECMA-262, which JSON Schema patterns follow, `$` matches only at the end\n    of the text. Python\'s `$` also matches just before a final newline, so\n    "C-103\\\\n" passed `^C-[0-9]{3}$` here although the published schema rejects\n    it (funnel-go-live-review 1.2.0, Arena 261011 sweep). Every `$` outside a\n    character class and not escaped becomes `\\\\Z`.\n    """\n    out, i, in_class = [], 0, False\n    while i < len(pattern):\n        char = pattern[i]\n        if char == "\\\\":\n            out.append(pattern[i:i + 2])\n            i += 2\n            continue\n        if in_class:\n            in_class = char != "]"\n        elif char == "[":\n            in_class = True\n        elif char == "$":\n            char = r"\\Z"\n        out.append(char)\n        i += 1\n    return "".join(out)'


def patch2(text: str) -> str:
    if MARK2 in text:
        raise ValueError("stage 2 already applied")
    missing = [n for n, old in (("pattern", PATTERN_OLD), ("helper anchor", HELPER_ANCHOR)) if text.count(old) != 1]
    if missing:
        raise ValueError("stage-2 anchors not found exactly once: " + ", ".join(missing))
    text = text.replace(PATTERN_OLD, PATTERN_NEW, 1)
    return text.replace(HELPER_ANCHOR, "\n" + HELPER + HELPER_ANCHOR, 1)


def main(argv: list[str]) -> int:
    sentence = "--no-sentence" not in argv
    argv = [a for a in argv if a != "--no-sentence"]
    check = argv[:1] == ["--check"]
    status = 0
    for name in argv[1:] if check else argv:
        path = Path(name)
        text = path.read_text()
        if MARK in text and MARK2 in text:
            print(f"patched   {path}")
            continue
        try:
            new = text if MARK in text else patch(text, sentence)
            new = patch2(new)
        except ValueError as exc:
            print(f"REFUSED   {path}: {exc}")
            status = 1
            continue
        if check:
            print(f"unpatched {path}")
            status = 1
        else:
            path.write_text(new)
            print(f"PATCHED   {path}")
    return status


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
