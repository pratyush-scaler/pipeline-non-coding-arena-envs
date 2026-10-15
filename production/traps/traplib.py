"""Trap library (traplib/1): merge, validate and render the trap modes a decisive premise may be built from (2026-10-15).

    python3 -I traplib.py build   [--src DIR] [--out DIR] [--strict]
    python3 -I traplib.py show    <id|alias> [--json] [--lib FILE]
    python3 -I traplib.py list    [--status S] [--family F] [--aimed-at M] [--lib FILE]
    python3 -I traplib.py resolve <id|alias> [--lib FILE]

`build` reads modes-internal.json, modes-external.json and modes-trace.json from --src (default: this folder; a missing
file is skipped, an unreadable one refuses the build), validates every mode against SCHEMA.md, and writes library.json
and TRAP-LIBRARY.md to --out (default: this folder). Any error refuses the build and writes nothing. Status-versus-
evidence disagreements (SCHEMA.md "Status rules") are warnings, errors under --strict.

Promotion (SCHEMA.md): an L/R mode whose id a T/D mode lists in `aliases` is superseded. It is dropped from the
library, its id resolves to the T/D mode, and its external and trace evidence and its aliases move to that mode.

Dead list (2026-10-15): a D id names a mechanism measured dead. Its status must be `dead` unless the mode carries
`"low_n": true` (too few runs to compute the dead rule); either way design_lint never accepts a D id, or a mode that
lists a D id among its aliases, as a decisive template (`dead_listed()`).

`list --aimed-at fable` also lists modes aimed at `both`. `show`, `list` and `resolve` read --lib, else
$ARENA_LIBRARY, else library.json next to this file.

API (stdlib only; design_lint and plan_batch import it): load(path) -> Library; Library.resolve(name) -> mode | None;
Library.status_of(name); module-level resolve(name) / status_of(name) on the default library.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
SCHEMA = "traplib/1"
# source -> (file name, id prefixes, statuses allowed)
SOURCES = {"internal": ("modes-internal.json", "TD", ("proven", "promising", "bimodal", "dead")),
           "external": ("modes-external.json", "L", ("literature",)),
           "trace": ("modes-trace.json", "R", ("trace-derived",))}
STATUSES = ("proven", "promising", "bimodal", "literature", "trace-derived", "dead")
FAMILIES = ("record_reversal", "convention_inference", "quantity_basis", "possession_state", "authority_selection",
            "rule_scope", "temporal_anchor", "aggregation_basis", "revision_supersession", "identity_resolution",
            "other")
AIMED = ("fable", "astra", "both", "unknown")
LOOPHOLES = ("L-record", "L-join", "L-shield", "L-default", "L-absorb", "L-threshold", "L-union", "other")
RECIPE_KEYS = ("record", "anchors", "withheld", "dials", "conservation", "shields")
LIST_FIELDS = ("aliases", "loopholes", "proof_obligations", "hazards", "kills", "trace_signals", "domains")
REQUIRED = ("id", "name", "family", "status", "aimed_at", "clock", "summary")
KNOWN = set(REQUIRED) | set(LIST_FIELDS) | {"recipe", "example", "evidence", "low_n"}
DEAD_ID = re.compile(r"D[0-9]+")
EVIDENCE_KEYS = ("internal", "pooled", "external", "traces")
MODELS = ("fable", "astra")
ID_RE = re.compile(r"[TLRD][0-9]+")
PILOT_FIRST = ("literature", "trace-derived", "bimodal")


class LibraryError(ValueError):
    """The sources cannot make a valid library; every message is in .errors."""

    def __init__(self, errors: list[str]):
        super().__init__(f"{len(errors)} error(s): " + "; ".join(errors[:5]))
        self.errors = errors


# --------------------------------------------------------------------------- validation

def _pair(v) -> bool:
    """[k, n]: k of n valid runs missed, 0 <= k <= n."""
    return (isinstance(v, list) and len(v) == 2 and all(isinstance(x, int) and not isinstance(x, bool) for x in v)
            and 0 <= v[0] <= v[1])


def _strs(v) -> bool:
    return isinstance(v, list) and all(isinstance(x, str) and x.strip() for x in v)


def _check_evidence(where: str, ev, errors: list[str]) -> None:
    if not isinstance(ev, dict):
        errors.append(f"{where}: evidence must be an object")
        return
    for k in ev:
        if k not in EVIDENCE_KEYS:
            errors.append(f"{where}: evidence has unknown key {k!r} (allowed {', '.join(EVIDENCE_KEYS)})")
    rows = ev.get("internal", [])
    if not isinstance(rows, list):
        errors.append(f"{where}: evidence.internal must be a list")
        rows = []
    for i, r in enumerate(rows):
        w = f"{where}: evidence.internal[{i}]"
        if not isinstance(r, dict):
            errors.append(f"{w} must be an object")
            continue
        for f in ("task", "stage"):
            if not isinstance(r.get(f), str) or not r.get(f):
                errors.append(f"{w}: {f} must be a non-empty string")
        if r.get("stage") not in (None, "pilot", "final"):
            errors.append(f"{w}: stage {r.get('stage')!r} is not pilot or final")
        for f in ("version", "premise", "audit"):
            if f in r and not isinstance(r[f], str):
                errors.append(f"{w}: {f} must be a string")
        for m in MODELS:
            if m in r and r[m] is not None and not _pair(r[m]):
                errors.append(f"{w}: {m} must be [k, n] with 0 <= k <= n")
    pooled = ev.get("pooled", {})
    if not isinstance(pooled, dict):
        errors.append(f"{where}: evidence.pooled must be an object")
    else:
        for m, v in pooled.items():
            if m not in MODELS:
                errors.append(f"{where}: evidence.pooled has unknown model {m!r}")
            elif v is not None and not _pair(v):
                errors.append(f"{where}: evidence.pooled.{m} must be [k, n] with 0 <= k <= n")
    for key, need, opt in (("external", ("source", "finding"), ("url", "models", "metric")),
                           ("traces", ("session", "signal"), ())):
        rows = ev.get(key, [])
        if not isinstance(rows, list):
            errors.append(f"{where}: evidence.{key} must be a list")
            continue
        for i, r in enumerate(rows):
            w = f"{where}: evidence.{key}[{i}]"
            if not isinstance(r, dict):
                errors.append(f"{w} must be an object")
                continue
            for f in need:
                if not isinstance(r.get(f), str) or not r.get(f).strip():
                    errors.append(f"{w}: {f} must be a non-empty string")
            for f in opt:
                if f in r and r[f] is not None and not isinstance(r[f], str):
                    errors.append(f"{w}: {f} must be a string")
            if key == "external" and "year" in r and r["year"] is not None and (
                    not isinstance(r["year"], int) or isinstance(r["year"], bool)):
                errors.append(f"{w}: year must be an integer")


def validate_mode(m, source: str) -> tuple[list[str], list[str]]:
    """Errors and warnings for one MODE from `source` (internal|external|trace), per SCHEMA.md."""
    errors: list[str] = []
    warns: list[str] = []
    if not isinstance(m, dict):
        return [f"{source}: a mode is not an object"], warns
    mid = m.get("id")
    where = f"{source}:{mid if isinstance(mid, str) else '?'}"
    for f in REQUIRED:
        if f not in m:
            errors.append(f"{where}: missing required field {f}")
    _, prefixes, allowed = SOURCES[source]
    if isinstance(mid, str) and ID_RE.fullmatch(mid):
        if mid[0] not in prefixes:
            errors.append(f"{where}: id prefix {mid[0]} is not allowed in {SOURCES[source][0]} (allowed {prefixes})")
    elif "id" in m:
        errors.append(f"{where}: id {mid!r} does not match ^[TLRD][0-9]+$")
    name = m.get("name")
    if "name" in m and (not isinstance(name, str) or not name.strip() or len(name) > 80):
        errors.append(f"{where}: name must be a non-empty string of at most 80 characters")
    for f, enum in (("family", FAMILIES), ("status", STATUSES), ("aimed_at", AIMED)):
        if f in m and m[f] not in enum:
            errors.append(f"{where}: {f} {m[f]!r} is not one of {', '.join(enum)}")
    if m.get("status") in STATUSES and m.get("status") not in allowed:
        errors.append(f"{where}: status {m['status']} is not allowed in {SOURCES[source][0]} (allowed {', '.join(allowed)})")
    if "clock" in m and not isinstance(m["clock"], bool):
        errors.append(f"{where}: clock must be true or false")
    if "low_n" in m and not isinstance(m["low_n"], bool):
        errors.append(f"{where}: low_n must be true or false")
    # a D id names a dead-list mechanism; a computed non-dead status there only means the sample is small
    if isinstance(mid, str) and DEAD_ID.fullmatch(mid) and m.get("status") != "dead" and m.get("low_n") is not True:
        errors.append(f"{where}: D id with status {m.get('status')!r}: a D mode is dead unless \"low_n\": true says its "
                      f"sample is too small to compute the dead rule (it is never decisive either way)")
    for f in ("summary", "example"):
        if f in m and not isinstance(m[f], str):
            errors.append(f"{where}: {f} must be a string")
    if isinstance(m.get("summary"), str) and not m["summary"].strip():
        errors.append(f"{where}: summary is empty")
    for f in LIST_FIELDS:
        if f in m and not _strs(m[f]):
            errors.append(f"{where}: {f} must be a list of non-empty strings")
    for lp in m.get("loopholes") or []:
        if isinstance(lp, str) and lp not in LOOPHOLES:
            errors.append(f"{where}: loophole {lp!r} is not one of {', '.join(LOOPHOLES)}")
    for a in m.get("aliases") or []:
        if a == mid:
            errors.append(f"{where}: alias {a!r} repeats the mode's own id")
    rec = m.get("recipe")
    if rec is not None:
        if not isinstance(rec, dict):
            errors.append(f"{where}: recipe must be an object")
        else:
            for k, v in rec.items():
                if k not in RECIPE_KEYS:
                    errors.append(f"{where}: recipe has unknown key {k!r} (allowed {', '.join(RECIPE_KEYS)})")
                elif k == "dials":
                    if not _strs(v):
                        errors.append(f"{where}: recipe.dials must be a list of strings")
                elif not isinstance(v, str):
                    errors.append(f"{where}: recipe.{k} must be a string")
    if "evidence" in m:
        _check_evidence(where, m["evidence"], errors)
    ev = m.get("evidence") if isinstance(m.get("evidence"), dict) else {}
    if m.get("status") in ("literature", "trace-derived") and ev.get("internal"):
        errors.append(f"{where}: status {m['status']} carries measured rows; re-issue it as a T mode (SCHEMA.md promotion)")
    for f in m:
        if f not in KNOWN:
            warns.append(f"{where}: unknown field {f!r} kept as is")
    return errors, warns


def dead_listed(m: dict | None) -> bool:
    """A D id, or a mode carrying a D id among its aliases: never a decisive template, whatever its status."""
    return bool(m) and (bool(DEAD_ID.fullmatch(str(m.get("id", ""))))
                        or any(DEAD_ID.fullmatch(str(a)) for a in m.get("aliases") or []))


def _rate(pair) -> float | None:
    return pair[0] / pair[1] if _pair(pair) and pair[1] else None


def status_findings(m: dict) -> list[str]:
    """Where a mode's asserted status disagrees with its own evidence under SCHEMA.md's status rules."""
    ev = m.get("evidence") or {}
    pooled = ev.get("pooled") or {}
    rows = ev.get("internal") or []
    finals = [r for r in rows if r.get("stage") == "final"]
    genuine = {r.get("task") for r in finals if str(r.get("audit") or "").upper().startswith("GENUINE")}
    st, out = m.get("status"), []

    def band(model, lo=None, hi=None):
        p = pooled.get(model)
        r = _rate(p)
        return r is not None and p[1] >= 20 and (lo is None or r >= lo) and (hi is None or r <= hi)
    proven = len(genuine) >= 2 and any(band(x, lo=0.20) for x in MODELS)
    dead = all(band(x, hi=0.05) for x in MODELS)
    if st == "proven" and not proven:
        out.append(f"{m['id']}: proven needs >= 2 GENUINE final tasks and a pooled miss rate >= 0.20 with n >= 20 on "
                   f"one model (has {len(genuine)} task(s), pooled {pooled})")
    if st == "dead" and not dead:
        out.append(f"{m['id']}: dead needs a pooled miss rate <= 0.05 on BOTH models with n >= 20 each (pooled {pooled})")
    if st in ("promising", "bimodal") and not rows:
        out.append(f"{m['id']}: {st} needs measured rows here (evidence.internal is empty)")
    rates = [r[x][0] / r[x][1] for r in finals for x in MODELS if _pair(r.get(x)) and r[x][1]]
    if st == "bimodal" and rows and not (rates and all(q <= 0.1 or q >= 0.9 for q in rates)
                                         and min(rates) <= 0.1 and max(rates) >= 0.9):
        out.append(f"{m['id']}: bimodal needs per-task final miss rates all <= 0.1 or >= 0.9, spanning both ends")
    if st == "promising" and proven:
        out.append(f"{m['id']}: evidence meets the proven rule but status is promising")
    if st != "dead" and st in ("proven", "promising", "bimodal") and dead:
        out.append(f"{m['id']}: evidence meets the dead rule but status is {st}")
    if st == "literature" and not ev.get("external"):
        out.append(f"{m['id']}: literature mode has no evidence.external row")
    if st == "trace-derived" and not ev.get("traces"):
        out.append(f"{m['id']}: trace-derived mode has no evidence.traces row")
    return out


def _normalise(m: dict) -> dict:
    out = dict(m)
    for f in LIST_FIELDS:
        out[f] = list(m.get(f) or [])
    out["recipe"] = dict(m.get("recipe") or {})
    out["example"] = m.get("example") or ""
    ev = dict(m.get("evidence") or {})
    out["evidence"] = {"internal": list(ev.get("internal") or []), "pooled": dict(ev.get("pooled") or {}),
                       "external": list(ev.get("external") or []), "traces": list(ev.get("traces") or [])}
    return out


def _id_key(mid: str) -> tuple:
    return ("TDLR".index(mid[0]) if mid and mid[0] in "TDLR" else 9, int(mid[1:]) if mid[1:].isdigit() else 0, mid)


def merge(src: Path, strict: bool = False) -> tuple[dict, list[str]]:
    """Read and validate the three source files under `src`; returns (library dict, warnings) or raises LibraryError."""
    errors: list[str] = []
    warns: list[str] = []
    sources: dict[str, dict] = {}
    modes: list[tuple[str, dict]] = []
    for source, (fname, _, _) in SOURCES.items():
        path = src / fname
        if not path.is_file():
            warns.append(f"{fname}: not present, skipped")
            continue
        raw = path.read_bytes()
        try:
            doc = json.loads(raw)
        except ValueError as exc:
            errors.append(f"{fname}: not valid JSON ({exc})")
            continue
        if not isinstance(doc, dict):
            errors.append(f"{fname}: top level must be an object")
            continue
        if doc.get("schema") != SCHEMA:
            errors.append(f"{fname}: schema {doc.get('schema')!r} is not {SCHEMA!r}")
        if doc.get("source") != source:
            errors.append(f"{fname}: source {doc.get('source')!r} must be {source!r}")
        if not isinstance(doc.get("generated"), str) or not doc.get("generated"):
            errors.append(f"{fname}: generated must be a timestamp string")
        if not isinstance(doc.get("modes"), list):
            errors.append(f"{fname}: modes must be a list")
            continue
        sources[source] = {"file": fname, "generated": doc.get("generated"), "modes": len(doc["modes"]),
                           "sha256": hashlib.sha256(raw).hexdigest()}
        for m in doc["modes"]:
            e, w = validate_mode(m, source)
            errors += e
            warns += w
            if isinstance(m, dict):
                modes.append((source, m))
    # unique ids
    by_id: dict[str, tuple[str, dict]] = {}
    for source, m in modes:
        mid = m.get("id")
        if not isinstance(mid, str):
            continue
        if mid in by_id:
            errors.append(f"duplicate id {mid} ({by_id[mid][0]} and {source})")
        else:
            by_id[mid] = (source, m)
    # promotion: a T/D mode naming an L/R id in its aliases supersedes that mode
    superseded: dict[str, str] = {}
    for mid, (source, m) in by_id.items():
        if source != "internal":
            continue
        for a in m.get("aliases") or []:
            if isinstance(a, str) and a in by_id and by_id[a][0] in ("external", "trace"):
                if a in superseded:
                    errors.append(f"{a} is claimed by two promoted modes ({superseded[a]} and {mid})")
                superseded[a] = mid
    kept = {mid: _normalise(m) for mid, (source, m) in by_id.items() if mid not in superseded}
    for old, new in sorted(superseded.items()):
        if new not in kept:
            continue
        o, n = _normalise(by_id[old][1]), kept[new]
        for key in ("external", "traces"):
            seen = {json.dumps(r, sort_keys=True) for r in n["evidence"][key]}
            n["evidence"][key] += [r for r in o["evidence"][key] if json.dumps(r, sort_keys=True) not in seen]
        n["aliases"] += [a for a in o["aliases"] if a not in n["aliases"] and a != new]
        warns.append(f"{old} superseded by {new} (promotion; its id now resolves to {new})")
    # unique aliases, never shadowing an id
    aliases: dict[str, str] = {}
    for mid in sorted(kept, key=_id_key):
        for a in kept[mid]["aliases"]:
            if a in superseded and superseded[a] == mid:
                aliases[a] = mid
            elif a in kept or (a in by_id and a not in superseded):
                errors.append(f"{mid}: alias {a!r} is the id of another mode")
            elif a in aliases and aliases[a] != mid:
                errors.append(f"alias {a!r} names two modes ({aliases[a]} and {mid})")
            else:
                aliases[a] = mid
    findings = [f for m in kept.values() for f in status_findings(m)]
    if strict:
        errors += findings
    else:
        warns += [f"status: {f}" for f in findings]
    if errors:
        raise LibraryError(errors)
    stamps = sorted(s["generated"] for s in sources.values() if isinstance(s.get("generated"), str))
    lib = {"schema": SCHEMA, "generated": stamps[-1] if stamps else "", "sources": sources,
           "modes": [kept[k] for k in sorted(kept, key=_id_key)],
           "aliases": dict(sorted(aliases.items())), "superseded": dict(sorted(superseded.items()))}
    return lib, warns


# --------------------------------------------------------------------------- the loaded library

class Library:
    """A built library.json: modes by id, aliases, resolve() and status_of()."""

    def __init__(self, data: dict, path: Path | None = None):
        if data.get("schema") != SCHEMA:
            raise ValueError(f"{path or 'library'}: schema {data.get('schema')!r} is not {SCHEMA!r}")
        self.data, self.path = data, path
        self.modes = {m["id"]: m for m in data.get("modes", [])}
        self.aliases = dict(data.get("aliases") or {})
        for m in self.modes.values():
            for a in m.get("aliases") or []:
                self.aliases.setdefault(a, m["id"])
        self._fold = {k.lower(): k for k in list(self.modes) + list(self.aliases)}

    def resolve(self, name) -> dict | None:
        """The mode an id or alias names (exact first, then case-insensitive), else None."""
        name = str(name or "").strip()
        key = name if (name in self.modes or name in self.aliases) else self._fold.get(name.lower())
        if key is None:
            return None
        return self.modes.get(key) or self.modes.get(self.aliases.get(key, ""))

    def status_of(self, name) -> str | None:
        m = self.resolve(name)
        return m["status"] if m else None

    def select(self, status: str | None = None, family: str | None = None, aimed_at: str | None = None) -> list[dict]:
        out = []
        for m in self.modes.values():
            if status and m["status"] != status or family and m["family"] != family:
                continue
            if aimed_at and m["aimed_at"] != aimed_at and not (aimed_at in MODELS and m["aimed_at"] == "both"):
                continue
            out.append(m)
        return out


def default_path() -> Path:
    v = os.environ.get("ARENA_LIBRARY")
    return Path(v).expanduser() if v else HERE / "library.json"


def load(path: Path | str | None = None) -> Library:
    """Load a built library.json (default: $ARENA_LIBRARY, else next to this file). Raises FileNotFoundError/ValueError."""
    p = Path(path) if path else default_path()
    return Library(json.loads(p.read_text()), p)


_DEFAULT: Library | None = None


def _default() -> Library:
    global _DEFAULT
    if _DEFAULT is None:
        _DEFAULT = load()
    return _DEFAULT


def resolve(name, lib: Library | None = None) -> dict | None:
    return (lib or _default()).resolve(name)


def status_of(name, lib: Library | None = None) -> str | None:
    return (lib or _default()).status_of(name)


# --------------------------------------------------------------------------- rendering

def _cell(text) -> str:
    return str(text).replace("|", "\\|").replace("\n", " ")


def _anchor(m: dict) -> str:
    """The GitHub-style anchor of render_mode's heading."""
    return re.sub(r"[^\w\- ]", "", f"{m['id']}: {m['name']}".lower()).replace(" ", "-")


def _pooled(m: dict, model: str) -> str:
    p = m["evidence"]["pooled"].get(model)
    return f"{p[0]}/{p[1]} ({p[0] / p[1]:.0%})" if _pair(p) and p[1] else "-"


def render_mode(m: dict) -> str:
    """One mode as a Markdown section."""
    L = [f"## {m['id']}: {m['name']}", "",
         f"- **Status:** {m['status']}{' (pilot first)' if m['status'] in PILOT_FIRST else ''}",
         f"- **Family:** {m['family']}",
         f"- **Aimed at:** {m['aimed_at']}",
         f"- **Clock trap:** {'yes (never the primary failure)' if m['clock'] else 'no'}"]
    if dead_listed(m):
        L.append("- **Dead list:** never a decisive template" + (" (status computed on a small sample: low_n)"
                                                                 if m.get("low_n") else ""))
    if m["aliases"]:
        L.append(f"- **Aliases:** {', '.join(m['aliases'])}")
    L.append(f"- **Pooled misses:** Fable {_pooled(m, 'fable')}, Astra {_pooled(m, 'astra')}")
    if m["loopholes"]:
        L.append(f"- **Loopholes:** {', '.join(m['loopholes'])}")
    L += ["", m["summary"].strip(), ""]
    rec = m["recipe"]
    if rec:
        L.append("**Recipe**")
        L.append("")
        for k in RECIPE_KEYS:
            if k not in rec:
                continue
            if k == "dials":
                L.append("- *dials:*")
                L += [f"  - {d}" for d in rec[k]]
            else:
                L.append(f"- *{k}:* {rec[k]}")
        L.append("")
    for f, title in (("proof_obligations", "Proof obligations (authoring/validate.py)"), ("hazards", "Hazards"),
                     ("kills", "What killed it"), ("trace_signals", "Trace signals"), ("domains", "Domains")):
        if m[f]:
            L += [f"**{title}**", ""] + [f"- {x}" for x in m[f]] + [""]
    if m["example"]:
        L += [f"**Example.** {m['example']}", ""]
    ev = m["evidence"]
    if ev["internal"]:
        L += ["**Measured here**", "", "| task | version | premise | stage | Fable missed | Astra missed | audit |",
              "|---|---|---|---|---|---|---|"]
        for r in ev["internal"]:
            fa = "/".join(map(str, r["fable"])) if _pair(r.get("fable")) else "-"
            aa = "/".join(map(str, r["astra"])) if _pair(r.get("astra")) else "-"
            L.append(f"| {_cell(r.get('task', ''))} | {_cell(r.get('version', ''))} | {_cell(r.get('premise', ''))} | "
                     f"{r.get('stage', '')} | {fa} | {aa} | {_cell(r.get('audit', ''))} |")
        L.append("")
    if ev["external"]:
        L += ["**External evidence**", ""]
        for r in ev["external"]:
            bits = [r.get("source", ""), str(r.get("year") or ""), r.get("models") or "", r.get("metric") or ""]
            L.append(f"- {' · '.join(b for b in bits if b)}: {r.get('finding', '')}"
                     + (f" ({r['url']})" if r.get("url") else ""))
        L.append("")
    if ev["traces"]:
        L += ["**Trace evidence**", ""] + [f"- `{r.get('session', '')}`: {r.get('signal', '')}" for r in ev["traces"]]
        L.append("")
    return "\n".join(L)


def render(lib: dict) -> str:
    modes = lib["modes"]
    srcs = ", ".join(f"`{s['file']}` ({s['modes']} modes, {s['generated']})" for s in lib["sources"].values()) or "none"
    L = ["# Trap library", "",
         f"Generated by `production/traps/traplib.py build` from {srcs}. Schema `{SCHEMA}`: see `SCHEMA.md`.",
         "**Do not edit this file or `library.json` by hand**: edit the source files and rebuild.", "",
         "A decisive premise names one of these ids (or an alias) as its `template`. `design_lint` fails a `dead` mode and",
         "every D id (the dead list, whatever its computed status), warns \"pilot first\" on `literature`, `trace-derived`",
         "and `bimodal`, and accepts `proven` and `promising`.", ""]
    if lib["superseded"]:
        L += ["Superseded by promotion: " + ", ".join(f"{a} -> {b}" for a, b in lib["superseded"].items()), ""]
    L += ["## Summary by family and status", "",
          "| family | " + " | ".join(STATUSES) + " | total |", "|---|" + "---|" * (len(STATUSES) + 1)]
    for fam in FAMILIES:
        row = [sum(1 for m in modes if m["family"] == fam and m["status"] == st) for st in STATUSES]
        if sum(row):
            L.append(f"| {fam} | " + " | ".join(str(x or "") for x in row) + f" | {sum(row)} |")
    tot = [sum(1 for m in modes if m["status"] == st) for st in STATUSES]
    L += [f"| **all** | " + " | ".join(str(x) for x in tot) + f" | {len(modes)} |", "",
          "## Index", "", "| id | name | family | status | aimed at | clock | Fable missed | Astra missed |",
          "|---|---|---|---|---|---|---|---|"]
    for m in modes:
        L.append(f"| [{m['id']}](#{_anchor(m)}) | {_cell(m['name'])} | {m['family']} | {m['status']} | "
                 f"{m['aimed_at']} | {'yes' if m['clock'] else ''} | {_pooled(m, 'fable')} | {_pooled(m, 'astra')} |")
    L.append("")
    for m in modes:
        L.append(render_mode(m))
    return "\n".join(L).rstrip() + "\n"


def build(src: Path, out: Path, strict: bool = False) -> int:
    try:
        lib, warns = merge(src, strict)
    except LibraryError as exc:
        for e in exc.errors:
            print("ERROR", e)
        print(f"BUILD REFUSED: {len(exc.errors)} error(s); nothing written")
        return 1
    for w in warns:
        print("WARN ", w)
    out.mkdir(parents=True, exist_ok=True)
    (out / "library.json").write_text(json.dumps(lib, indent=1, ensure_ascii=False) + "\n")
    (out / "TRAP-LIBRARY.md").write_text(render(lib))
    by = {st: sum(1 for m in lib["modes"] if m["status"] == st) for st in STATUSES}
    print(f"BUILT {len(lib['modes'])} modes ({', '.join(f'{k} {v}' for k, v in by.items() if v)}) -> "
          f"{out / 'library.json'}, {out / 'TRAP-LIBRARY.md'}")
    return 0


# --------------------------------------------------------------------------- CLI

def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="traplib.py", description=__doc__.split("\n\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    b = sub.add_parser("build")
    b.add_argument("--src", default=str(HERE))
    b.add_argument("--out", default=str(HERE))
    b.add_argument("--strict", action="store_true", help="status-versus-evidence disagreements refuse the build")
    for name in ("show", "resolve"):
        p = sub.add_parser(name)
        p.add_argument("name")
        p.add_argument("--lib")
        if name == "show":
            p.add_argument("--json", action="store_true")
    p = sub.add_parser("list")
    p.add_argument("--status", choices=STATUSES)
    p.add_argument("--family", choices=FAMILIES)
    p.add_argument("--aimed-at", choices=AIMED)
    p.add_argument("--lib")
    a = ap.parse_args(argv)
    if a.cmd == "build":
        return build(Path(a.src).resolve(), Path(a.out).resolve(), a.strict)
    try:
        lib = load(a.lib)
    except (OSError, ValueError) as exc:
        print(f"cannot read the trap library ({exc}); run: python3 -I {HERE / 'traplib.py'} build")
        return 2
    if a.cmd == "list":
        rows = lib.select(a.status, a.family, a.aimed_at)
        for m in rows:
            print(f"{m['id']:5} {m['status']:13} {m['family']:22} {m['aimed_at']:7} {'clock ' if m['clock'] else ''}"
                  f"{'DEAD-LIST ' if dead_listed(m) else ''}{m['name']}  [F {_pooled(m, 'fable')} A {_pooled(m, 'astra')}]")
        print(f"{len(rows)} mode(s)")
        return 0
    m = lib.resolve(a.name)
    if m is None:
        print(f"unknown: {a.name}")
        return 1
    if a.cmd == "resolve":
        print(f"{m['id']} {m['status']}")
    elif a.json:
        print(json.dumps(m, indent=1, ensure_ascii=False))
    else:
        print(render_mode(m))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
