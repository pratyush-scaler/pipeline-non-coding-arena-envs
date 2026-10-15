"""Narrow, reproducible privacy transformations; never arbitrary replacements.

Calendar spans are character offsets into a hash-bound recovered source revision.
The manifest supplies dates and formats, never replacement text. Every replacement
is computed using one fixed day offset. Contextual privacy and calendar semantics
still require independent review; this proof establishes source lineage only.
"""
from __future__ import annotations

import calendar
import hashlib
import re
from datetime import date, timedelta
from pathlib import Path, PurePosixPath

from ..author.contracts import contained, strict_json
from ..dump import recover as rec

MANIFEST = "provenance/calendar-anonymization.json"
SCHEMA = "arena-pipeline/calendar-anonymization/1"


def sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _keys(value, keys: set[str], where: str) -> None:
    if not isinstance(value, dict) or set(value) != keys:
        raise ValueError(f"{where}: expected exactly {sorted(keys)}")


def _date(value) -> date:
    if not isinstance(value, str) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
        raise ValueError("calendar dates must be ISO YYYY-MM-DD")
    return date.fromisoformat(value)


def _render(day: date, fmt: str) -> str:
    if fmt == "iso-date":
        return day.isoformat()
    if fmt == "slash-date":
        return f"{day.month}/{day.day}"
    if fmt == "dot-date":
        return f"{day.month}.{day.day}"
    if fmt == "iso-month":
        return f"{day.year:04d}-{day.month:02d}"
    if fmt == "zh-month":
        return f"{day.month}月"
    if fmt == "en-month":
        return ("January February March April May June July August September "
                "October November December").split()[day.month - 1]
    raise ValueError(f"unsupported calendar format: {fmt!r}")


def transform(content: str, edits: list, days: int, window: list) -> tuple[str, list]:
    """Replay typed, nonoverlapping spans without normalizing any other bytes."""
    if type(days) is not int or not 0 < abs(days) <= 36600:
        raise ValueError("calendar shift must be a nonzero integer within 100 years")
    if not isinstance(window, list) or len(window) != 2:
        raise ValueError("source_window must contain two ISO dates")
    lo, hi = map(_date, window)
    if not 0 <= (hi - lo).days < 365:
        raise ValueError("source_window must be ordered and shorter than one year")
    if not isinstance(edits, list) or not edits:
        raise ValueError("calendar edits must be nonempty")
    result, changes, cursor = [], [], 0
    for edit in edits:
        _keys(edit, {"start", "end", "date", "format"}, "calendar edit")
        start, end = edit["start"], edit["end"]
        if type(start) is not int or type(end) is not int or not cursor <= start < end <= len(content):
            raise ValueError("calendar spans must be ordered, disjoint and within the source")
        original = _date(edit["date"])
        shifted = original + timedelta(days=days)
        if not lo <= original <= hi:
            raise ValueError("calendar date lies outside the declared source window")
        fmt = edit["format"]
        before, after = _render(original, fmt), _render(shifted, fmt)
        if fmt.endswith("month"):
            last = original.replace(day=calendar.monthrange(original.year, original.month)[1])
            target_last = shifted.replace(day=calendar.monthrange(shifted.year, shifted.month)[1])
            if original.day != 1 or shifted.day != 1 or last > hi or last + timedelta(days=days) != target_last:
                raise ValueError("calendar month shift must preserve the entire month interval")
        if content[start:end] != before or before == after:
            raise ValueError("calendar span does not match its typed source date or is unchanged")
        # A substring of a larger number/date cannot masquerade as a date token.
        if (re.search(r"(?:\d|\d[/.])$", content[:start]) or
                re.match(r"(?:\d|[/.]\d)", content[end:])):
            raise ValueError("calendar span splits a numeric token")
        result.extend((content[cursor:start], after))
        changes.append({"start": start, "end": end, "format": fmt,
                        "source_date": original.isoformat(), "public_date": shifted.isoformat(),
                        "before": before, "after": after})
        cursor = end
    result.append(content[cursor:])
    return "".join(result), changes


def verify(bundle: Path, fixture: Path, ws: rec.Workspace, session_id: str) -> dict:
    """Recompute proofs from trusted trace content and actual public fixture bytes."""
    path = contained(bundle, MANIFEST)
    if not path.exists():
        return {}
    fixture = contained(bundle, fixture.relative_to(bundle).as_posix())
    raw = path.read_bytes()
    manifest = strict_json(raw.decode())
    _keys(manifest, {"schema", "kind", "days", "source_window", "files"}, "calendar manifest")
    if manifest["schema"] != SCHEMA or manifest["kind"] != "fixed-day-shift":
        raise ValueError("unsupported calendar anonymization policy")
    rows = manifest["files"]
    if not isinstance(rows, list) or not rows:
        raise ValueError("calendar manifest must identify changed source files")
    verified = {}
    for row in rows:
        _keys(row, {"path", "citation", "source_sha256", "public_sha256", "edits"}, "calendar file")
        rel = row["path"]
        public = contained(fixture, rel)
        if PurePosixPath(rel).as_posix() != rel or rel in verified:
            raise ValueError("calendar file paths must be canonical and unique")
        citation = row["citation"]
        source = next((r for r in ws.provenance_revisions()
                       if citation == f"{session_id}::msg{r.msg_index}::{r.path}"
                       and sha(r.content.encode()) == row["source_sha256"]), None)
        if source is None:
            raise ValueError(f"{rel}: calendar source hash/citation is absent from the trusted trace")
        transformed, changes = transform(source.content, row["edits"], manifest["days"], manifest["source_window"])
        public_bytes = public.read_bytes()
        if transformed.encode() != public_bytes or sha(public_bytes) != row["public_sha256"]:
            raise ValueError(f"{rel}: fixture differs from the verified calendar transformation")
        verified[rel] = {"citation": citation, "source_sha256": row["source_sha256"],
                         "public_sha256": sha(public_bytes), "changes": changes,
                         "source_content": source.content}
    return {"manifest_sha256": sha(raw), "policy": SCHEMA,
            "manifest": manifest, "files": verified}


def audit(bundle: Path) -> dict:
    """Private reviewer evidence, independently recovered rather than author asserted."""
    if not contained(bundle, MANIFEST).exists():
        return {}
    spec = strict_json((bundle / "authoring/spec.json").read_text())
    session = spec["source"]["session_id"]
    fixture = next(bundle / "environment" / n for n in ("files", "fixtures")
                   if (bundle / "environment" / n).is_dir())
    return verify(bundle, fixture, rec.recover(rec.load_trace(session), rec.sessions_root()), session)
