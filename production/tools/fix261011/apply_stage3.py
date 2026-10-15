"""Arena 261011 central patch, stage 3 (2026-10-12): long-input robustness of the shared runtime.

    python3.11 -I -B apply_stage3.py <checks_runtime.py|checks.py|contracts.py> [...]
    python3.11 -I -B apply_stage3.py --check <file> [...]
    python3.11 -I -B apply_stage3.py --selftest          # exhaustive equivalence of the hash stripper

Found by the controller after the indentation audit reported int-limit crashes and quadratic regexes in
that task's own grader; the same two classes were then measured in the shared criteria runtime:
- `normalise` stripped trailing heading hashes with `re.sub(r"\\s+#+\\s*$", ...)`, which rescans a long
  whitespace run from every start position: 20,000 spaces took 0.93 s, so a few megabytes of spaces in any
  deliverable string would outlast the verifier. It is replaced by a linear function that removes exactly
  what the regex removed (checked exhaustively by --selftest).
- `normalise` tested "digits, separators and spaces only" with `[\\d.,\\s]*\\d[\\d.,\\s]*`, which backtracks
  quadratically on a long digit/space run ending in a letter (20,000 characters: 0.46 s). Replaced by the
  equivalent linear pair `fullmatch([\\d.,\\s]+)` and `search(\\d)` (checked exhaustively by --selftest).
- stage 1's uniqueness key called `normalise`, which raises ValueError on a numeric string past Python's
  4,300-digit int limit, and nothing caught it: a 5,000-digit string in a unique list crashed the grader.
  The key now falls back to the value as written (run_check already fails such values as submission faults).
"""
from __future__ import annotations

import itertools
import re
import sys
from pathlib import Path

MARK = "Arena 261011 (stage 3)"

RT_OLD = '        text = _TRAILING_HASHES.sub("", text)\n'
RT_NEW = '        text = _strip_trailing_hashes(text)\n'
DIGIT_OLD = '        if not re.fullmatch(r"[\\d.,\\s]*\\d[\\d.,\\s]*", unmarked):\n'
DIGIT_NEW = ('        # Arena 261011 (stage 3): the same test as `[\\d.,\\s]*\\d[\\d.,\\s]*`, without its quadratic backtracking.\n'
             '        if not (re.fullmatch(r"[\\d.,\\s]+", unmarked) and re.search(r"\\d", unmarked)):\n')
RT_ANCHOR = "\n\ndef normalise(value: Any, fold: bool = True) -> Any:"
RT_HELPER = '''

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
    return text'''

CT_OLD = "    return json.dumps(_by_value(normalise(value)), sort_keys=True, ensure_ascii=False)\n"
CT_NEW = '''    try:
        canonical = normalise(value)
    except (ValueError, OverflowError):
        # Arena 261011 (stage 3): a numeric string past Python's int-digit limit cannot be
        # normalised; it is compared as written (run_check fails such values as submission faults).
        canonical = value
    return json.dumps(_by_value(canonical), sort_keys=True, ensure_ascii=False)
'''


def patch(text: str) -> str:
    if MARK in text:
        raise ValueError("already patched")
    if RT_OLD in text:
        if text.count(RT_OLD) != 1 or text.count(RT_ANCHOR) != 1 or text.count(DIGIT_OLD) != 1:
            raise ValueError("runtime anchors not found exactly once")
        text = text.replace(DIGIT_OLD, DIGIT_NEW, 1)
        return text.replace(RT_OLD, RT_NEW, 1).replace(RT_ANCHOR, RT_HELPER + RT_ANCHOR, 1)
    if CT_OLD in text:
        if text.count(CT_OLD) != 1:
            raise ValueError("contracts anchor not found exactly once")
        return text.replace(CT_OLD, CT_NEW, 1)
    raise ValueError("neither the runtime nor the contracts anchor is present (stage 1 applied?)")


def selftest() -> int:
    rx = re.compile(r"\s+#+\s*$")
    ns: dict = {}
    exec(RT_HELPER, ns)
    strip = ns["_strip_trailing_hashes"]
    bad = 0
    for n in range(0, 9):
        for chars in itertools.product(" \t\n#a ", repeat=n):
            s = "".join(chars)
            if rx.sub("", s) != strip(s):
                bad += 1
                if bad < 5:
                    print("MISMATCH", repr(s), repr(rx.sub("", s)), repr(strip(s)))
    old_d = re.compile(r"[\\d.,\\s]*\\d[\\d.,\\s]*")
    for n in range(0, 9):
        for chars in itertools.product("1 .,a\u0663", repeat=n):
            s = "".join(chars)
            if bool(old_d.fullmatch(s)) != bool(re.fullmatch(r"[\\d.,\\s]+", s) and re.search(r"\\d", s)):
                bad += 1
                if bad < 5:
                    print("DIGIT MISMATCH", repr(s))
    import time
    t = time.time(); strip(" " * 3_000_000 + "x"); strip(" " * 3_000_000 + "#")
    s = "1 " * 1_500_000 + "x"; bool(re.fullmatch(r"[\\d.,\\s]+", s) and re.search(r"\\d", s))
    print(f"exhaustive over 6 symbols, length <= 8: {bad} mismatches; 3M-space inputs in {time.time() - t:.3f}s")
    return 1 if bad else 0


def main(argv: list[str]) -> int:
    if argv == ["--selftest"]:
        return selftest()
    check = argv[:1] == ["--check"]
    status = 0
    for name in argv[1:] if check else argv:
        path = Path(name)
        text = path.read_text()
        if MARK in text:
            print(f"patched   {path}")
            continue
        try:
            new = patch(text)
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
