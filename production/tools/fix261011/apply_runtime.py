"""Port the Arena 261011 read guard into a `checks_runtime.py` (2026-10-12).

    python3.11 -I -B apply_runtime.py <checks_runtime.py> [...]
    python3.11 -I -B apply_runtime.py --check <checks_runtime.py> [...]

Found by the enclosure-cut-list-signoff sweep (C3/C2): the output contract
refuses an oversized deliverable unread, but `Workspace.read` then read it
anyway to evaluate the objectives, so a multi-gigabyte file could exhaust the
verifier's memory instead of scoring 0, and an unreadable file raised an
uncaught OSError. Both now fail the check. The edit reproduces that task's
change byte for byte, so every patched copy is identical.

Requires the patched `contracts.py` (it imports MAX_DELIVERABLE_BYTES).
"""
from __future__ import annotations

import sys
from pathlib import Path

MARK = "Arena 261011 (C3)"
IMPORT_OLD = "from .contracts import contained, strict_json, ContractError, submission_errors\n"
IMPORT_NEW = "from .contracts import contained, strict_json, ContractError, submission_errors, MAX_DELIVERABLE_BYTES\n"
READ_ANCHOR = '''            tried.append(str(root))
            if target.is_file():
                return target.read_text(errors="replace")
'''
READ_NEW = '''            tried.append(str(root))
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
'''


def patch(text: str) -> str:
    missing = [n for n, old in (("import", IMPORT_OLD), ("read", READ_ANCHOR)) if text.count(old) != 1]
    if missing:
        raise ValueError("anchors not found exactly once: " + ", ".join(missing))
    return text.replace(IMPORT_OLD, IMPORT_NEW, 1).replace(READ_ANCHOR, READ_NEW, 1)


def main(argv: list[str]) -> int:
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
