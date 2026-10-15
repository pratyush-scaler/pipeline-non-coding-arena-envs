"""How the calibration agents actually solved a task, read from their trajectories.

v2.2 (2026-10-02). The hardening designer used to see only per-check pass rates:
"passed by 100% of attempts" says a trap failed, not WHY it failed. Wave 1's
manual trajectory study (research/R6) found the why in every case -- the file
both models read in full before coding, the grep that landed on the deciding
sentence, the label on the trap row, the colleague message that printed the
answer. This module extracts that evidence mechanically from the Harbor ATIF
trajectories of a measured version, so a redesign can route its interlocks
around the agents' real method instead of guessing at it.

Read-only. It reports what the agents did; it never edits a fixture and never
asks for one to be made ambiguous.
"""
from __future__ import annotations

import json
import re
import shlex
from collections import Counter, defaultdict
from pathlib import Path

FIXTURE_ROOT = "/app/environment/files/"
#: Agent sentences worth showing a designer: where the agent says it noticed,
#: excluded, re-read, reconciled or decided something.
CUE = re.compile(
    r"\b(?:exclud\w*|refund\w*|credit\w*|duplicat\w*|variant\w*|alias\w*|same (?:entity|supplier|customer|person)|"
    r"revis\w*|supersed\w*|amend\w*|effective|override\w*|precedence|governs?|"
    r"tie\w*|round\w*|half[- ]up|half[- ]even|cap(?:ped)?|threshold|boundary|"
    r"note[sd]? that|careful|trap|tricky|actually|wait|however|instead|mismatch|discrepan\w*|"
    r"verify|verified|cross[- ]check\w*|reconcil\w*|sanity)\b", re.I)
_GREP = re.compile(r"(?:^|[|;&\s])(?:rg|grep|egrep|zgrep)\s+(.*)")


def _trials(campaign: Path) -> list[Path]:
    return sorted(p for p in (Path(campaign) / "jobs").glob("*/*/") if (p / "steps").is_dir())


def _valid(trial: Path) -> bool:
    try:
        result = json.loads((trial / "result.json").read_text())
    except (OSError, ValueError):
        return False
    return not (result.get("exception_info") or result.get("void"))


def _calls(trial: Path, step: str) -> tuple[list[tuple[str, dict]], list[str]]:
    path = trial / "steps" / step / "agent" / "trajectory.json"
    try:
        data = json.loads(path.read_text())
    except (OSError, ValueError):
        return [], []
    calls, notes = [], []
    for row in data.get("steps") or []:
        if not isinstance(row, dict):
            continue
        message = row.get("message")
        if isinstance(message, str) and message.strip() and row.get("source") == "agent":
            notes.append(message)
        for call in row.get("tool_calls") or []:
            if isinstance(call, dict):
                args = call.get("arguments") if isinstance(call.get("arguments"), dict) else {}
                calls.append((str(call.get("function_name") or ""), args))
    return calls, notes


def _grep_patterns(command: str) -> list[str]:
    out = []
    for match in _GREP.finditer(command):
        try:
            words = shlex.split(match.group(1), posix=True)
        except ValueError:
            words = match.group(1).split()
        for word in words:
            if word.startswith("-") or "/" in word or word in {".", "*"}:
                continue
            out.append(word[:80])
            break
    return out


def digest(campaigns: list[Path], fixture: Path, step: str | None = None) -> dict:
    """Aggregate every valid episode of `campaigns` for one step (or each step)."""
    files = sorted(p.relative_to(fixture).as_posix() for p in Path(fixture).rglob("*") if p.is_file())
    per_step: dict[str, dict] = {}
    for campaign in campaigns:
        for trial in _trials(Path(campaign)):
            if not _valid(trial):
                continue
            steps = [step] if step else sorted(p.name for p in (trial / "steps").iterdir() if p.is_dir())
            for name in steps:
                calls, notes = _calls(trial, name)
                if not calls:
                    continue
                row = per_step.setdefault(name, {"episodes": 0, "opened": Counter(), "greps": Counter(),
                                                 "scripts": 0, "tools": Counter(), "notes": []})
                row["episodes"] += 1
                seen: set[str] = set()
                for tool, args in calls:
                    row["tools"][tool] += 1
                    text = " ".join(str(v) for v in args.values() if isinstance(v, str))
                    for file in files:
                        if file in seen:
                            continue
                        base = file.rsplit("/", 1)[-1]
                        if (FIXTURE_ROOT + file) in text or (len(base) >= 6 and base in text):
                            seen.add(file)
                    if tool.lower() == "grep" and isinstance(args.get("pattern"), str):
                        row["greps"][args["pattern"][:80]] += 1
                    command = args.get("command") if isinstance(args.get("command"), str) else ""
                    for pattern in _grep_patterns(command):
                        row["greps"][pattern] += 1
                    if (tool.lower() in {"write", "edit"} and str(args.get("file_path", "")).endswith(".py")) \
                            or re.search(r"python3?\s+(?:-\s*<<|-c\b|\S+\.py)", command):
                        row["scripts"] += 1
                for file in seen:
                    row["opened"][file] += 1
                for note in notes:
                    for sentence in re.split(r"(?<=[.!?])\s+|\n+", note):
                        sentence = sentence.strip()
                        if 25 <= len(sentence) <= 300 and CUE.search(sentence):
                            row["notes"].append(sentence)
    result = {"files": len(files), "steps": {}}
    for name, row in per_step.items():
        n = row["episodes"]
        notes = list(dict.fromkeys(row["notes"]))
        result["steps"][name] = {
            "episodes": n,
            "opened_by_every_episode": sorted(f for f, c in row["opened"].items() if c == n),
            "opened_by_some": sorted(f for f, c in row["opened"].items() if 0 < c < n),
            "never_opened": sorted(set(files) - set(row["opened"])),
            "top_greps": row["greps"].most_common(15),
            "scripts_per_episode": round(row["scripts"] / n, 1) if n else 0,
            "tool_mix": dict(row["tools"].most_common(8)),
            "agent_notes": notes[:20],
        }
    return result


def render(data: dict, limit: int = 14) -> str:
    """The digest as a brief section. Empty when there were no trajectories."""
    if not data.get("steps"):
        return ""
    lines = ["HOW THE MEASURED MODELS SOLVED THE VERSION YOU ARE REVISING (from their own trajectories; "
             "use it to route each interlock around the method that defeated the old trap, never to "
             "make a rule or definition ambiguous):"]
    for name, row in sorted(data["steps"].items()):
        lines.append(f"  step {name} -- {row['episodes']} valid episode(s), "
                     f"{row['scripts_per_episode']} python script runs per episode")
        every = row["opened_by_every_episode"]
        lines.append(f"    files EVERY episode opened ({len(every)} of {data['files']}): "
                     + (", ".join(every[:limit]) + (" ..." if len(every) > limit else "") if every else "none"))
        if row["never_opened"]:
            never = row["never_opened"]
            lines.append(f"    files NO episode opened ({len(never)}): " + ", ".join(never[:limit])
                         + (" ..." if len(never) > limit else ""))
        if row["top_greps"]:
            lines.append("    grep patterns: " + "; ".join(f"{p!r} x{c}" for p, c in row["top_greps"][:10]))
        for note in row["agent_notes"][:limit]:
            lines.append(f"    agent said: {note[:240]}")
    return "\n".join(lines)


def for_bundle(bundle: Path) -> str:
    """Render the digest of `bundle`'s current clean screen, or ''."""
    from . import screen
    record = screen.current(Path(bundle))
    if not record:
        return ""
    index = record.get("index") or {}
    campaigns = [Path(c) for c in index.get("campaigns") or []]
    for extra in (index.get("topups") or {}).values():
        campaigns += [Path(c) for c in extra or []]
    campaigns = [c for c in campaigns if c.is_dir()]
    fixture = Path(bundle) / "environment" / "files"
    if not campaigns or not fixture.is_dir():
        return ""
    try:
        return render(digest(campaigns, fixture))
    except Exception as exc:                                   # noqa: BLE001
        return f"(trajectory digest unavailable: {type(exc).__name__}: {exc})"
