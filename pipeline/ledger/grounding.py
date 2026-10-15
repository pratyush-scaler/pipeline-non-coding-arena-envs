"""Exact trace witnesses for the September 28 faithfulness definitions."""
from __future__ import annotations

import re


ROLES = {"goal", "capability", "scenario", "failure_mode", "grading_criteria"}
INSPIRED_ROLES = {"goal", "capability"}
SCENARIO_ROLES = ROLES


def alignment_problems(spec: dict, trace: dict, session_id: str,
                       required: bool = False) -> list[str]:
    """Verify citations and decision links; semantic review verifies meaning."""
    from ..dump.signals import _text

    where = "quality.trace_alignment"
    quality = spec.get("quality") or {}
    if not isinstance(quality, dict):
        return ["quality: expected an object"]
    alignment = quality.get("trace_alignment")
    if alignment is None and not required:
        return []
    if not isinstance(alignment, dict):
        return [f"{where}: cite the source goal and capability explicitly"]
    problems = []
    if required and INSPIRED_ROLES - alignment.keys():
        problems.append(f"{where}: missing roles {sorted(INSPIRED_ROLES - alignment.keys())}")
    messages = trace.get("messages")
    messages = messages if isinstance(messages, list) else []
    checks = spec.get("checks")
    checks = checks if isinstance(checks, list) else []
    objectives = {check["id"] for check in checks
                  if isinstance(check, dict) and check.get("kind") == "objective"
                  and isinstance(check.get("id"), str)}
    for role, entry in alignment.items():
        at = f"{where}.{role}"
        if role not in ROLES or not isinstance(entry, dict):
            problems.append(f"{at}: unsupported role or malformed witness")
            continue
        citation = entry.get("citation")
        match = re.fullmatch(r"([^:]+)::msg(\d+)", citation) if isinstance(citation, str) else None
        valid = bool(match and match[1] in {session_id, session_id[:8]}
                     and int(match[2]) < len(messages)
                     and isinstance(messages[int(match[2])], dict))
        if valid:
            message = messages[int(match[2])]
            text = message.get("content")
            text = text if isinstance(text, str) else _text(message)
            quote = entry.get("quote")
            valid = (message.get("role") == "user" and isinstance(quote, str)
                     and bool(quote.strip()) and quote in text)
        if not valid:
            problems.append(f"{at}: quote the exact cited user message in the declared session; "
                            f"use {session_id[:8]}::msgN or the full session ID, not a placeholder")
        if not isinstance(entry.get("preserved"), str) or not entry["preserved"].strip():
            problems.append(f"{at}.preserved: explain what the task actually preserves")
        checks = entry.get("checks")
        if (not isinstance(checks, list) or not checks
                or any(not isinstance(check, str) or check not in objectives for check in checks)):
            problems.append(f"{at}.checks: link the preserved capability to existing objectives")
    return problems


def verified_alignment(spec: dict, trace: dict, session_id: str) -> dict:
    """No malformed or unsupported witness receives provenance credit."""
    quality = spec.get("quality")
    if not isinstance(quality, dict):
        return {}
    alignment = quality.get("trace_alignment")
    if not isinstance(alignment, dict) or alignment_problems(spec, trace, session_id, required=True):
        return {}
    return alignment
