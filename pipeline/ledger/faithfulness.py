"""Generate the provenance ledger for a bundle.

Arena's headline finding on the first delivery: *"approximately 80% of the tasks
came from additions or omissions from the original trace."* We agreed with the
estimate. The problem was not the number -- a trace-derived task is a legitimate
thing to build -- it was that the number had to be reconstructed by argument
afterwards, per task, by hand.

This module makes it a measured property of the bundle. Every fixture file is
classified against what the trace actually states:

  lifted    byte-identical to content the trace states verbatim
  anonymized exact replay of a verified, typed privacy transformation of a source
  derived   recognisably descended from trace content (similarity above a
            stated floor), with the source revision cited
  authored  no ancestor in the trace

`authored` is not a failure. A deterministic environment needs scaffolding the
original session never had, and the previous delivery said so. What the gate
enforces is that the claim is *itself* checkable: lifted and derived entries
carry a citation, the fixture has no file the ledger omits, and the headline
faithfulness figure is computed rather than asserted.
Declared scenario supplements remain authored even if their text resembles a
recovered document; duplication cannot manufacture recovered-source credit.
"""

from __future__ import annotations

import difflib
import hashlib
import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path

from ..config import sessions_root
from ..dump import recover as rec
from .. import policy

#: Below this, "derived" is not a meaningful claim -- two files that share 45% of
#: their lines share a language, not an ancestor.
DERIVED_FLOOR = 0.55
ORIGINS = ("lifted", "anonymized", "derived", "authored")
WEIGHTS = {"lifted": 1, "anonymized": 1, "derived": 0.5, "authored": 0}


def share(amounts: dict) -> float:
    return round(sum(amounts.get(k, 0) * w for k, w in WEIGHTS.items()) /
                 (sum(amounts.values()) or 1), 3)


def measured_fields(ledger: dict) -> tuple[str, ...]:
    fields = ("source", "entries", "faithfulness_by_bytes", "recovery_omissions",
              "snapshot_policy", "correction_citation_policy", "trace_alignment", "spec_version")
    if ledger.get("schema") == "arena-pipeline/ledger/3":
        fields += ("schema", "counts", "bytes", "faithfulness_by_file",
                   "exact_copy_by_bytes", "exact_copy_by_file", "privacy_transformation")
    elif ledger.get("schema") != "arena-pipeline/ledger/2" or any(
            e.get("origin") == "anonymized" for e in ledger.get("entries", [])):
        raise ValueError("unsupported ledger schema or anonymization in a legacy ledger")
    if "carriers" in ledger:
        # Ledgers written before the carrier table (Arena 261011) never carried one.
        fields += ("carriers", "carrier_policy")
    return fields


#: Arena 261011 (R20/R26/R32): a reviewer could not tell which of several fixture
#: files carrying one session file is the original and which are copies or
#: revisions, so the source-change comparison was not auditable.
CARRIER_POLICY = ("original = the fixture file carrying the earliest session version of a source identity "
                  "(lowest cited msgN; a derived file counts at its closest ancestor's msgN); among carriers "
                  "of that version, an exact copy before a derived one, then the file whose fixture path "
                  "mirrors the session path, then the lexicographically first path; every other carrier is a "
                  "copy when byte-identical to the original, otherwise a revision carrying its own msgN")

_CITATION = re.compile(r"(?P<session>.+?)::msg(?P<msg>\d+)::(?P<path>.+)")


def carriers(entries: list) -> list[dict]:
    """One row per session file that more than one fixture file carries."""
    groups: dict[str, list] = {}
    for e in entries:
        match = _CITATION.fullmatch(e.citation or "")
        if match:
            groups.setdefault(match["path"], []).append((int(match["msg"]), match["session"], e))
    rows = []
    for identity, members in sorted(groups.items()):
        if len(members) < 2:
            continue
        earliest = min(msg for msg, _, _ in members)
        msg, session, original = min(
            (m for m in members if m[0] == earliest),
            key=lambda m: (m[2].origin != "lifted", m[2].path != identity.lstrip("/"), m[2].path))
        copies, revisions = [], []
        for m, s, e in sorted(members, key=lambda m: m[2].path):
            if e is original:
                continue
            if e.sha256 == original.sha256:
                copies.append(e.path)
            else:
                revisions.append({"path": e.path, "carries": f"{s}::msg{m}", "similarity": e.similarity})
        rows.append({"source_identity": identity, "original": original.path,
                     "original_carries": f"{session}::msg{msg}", "copies": copies, "revisions": revisions})
    return rows


@dataclass
class Entry:
    path: str
    origin: str                 # lifted | anonymized | derived | authored
    sha256: str
    bytes: int
    citation: str | None = None     # session/seed/message that states the source
    similarity: float | None = None
    note: str | None = None


def _sha(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()


def citation_problems(spec: dict, trace: dict, session_id: str) -> list[str]:
    """A plausible-looking citation is insufficient: quote the actual user turn."""
    from ..dump.signals import _text
    errors = []
    anchors = {}
    for trap in spec.get("traps", []):
        if trap.get("provenance") != "trace_derived":
            continue
        citation = trap.get("derived_from", "")
        match = re.fullmatch(r"([^:]+)::msg(\d+)", citation)
        messages = trace.get("messages", [])
        valid = bool(match and match[1] in {session_id, session_id[:8]} and int(match[2]) < len(messages))
        if valid:
            # Kaizen annotations identify the assistant being corrected; the
            # correction itself is the next user turn (signals.attach uses this
            # same convention). Never accept an assistant's own prose as proof.
            index = int(match[2])
            while index < len(messages) and messages[index].get("role") != "user":
                index += 1
            if index == len(messages):
                errors.append(f"{trap.get('id')}: citation has no following user correction")
                continue
            anchors.setdefault(index, set()).add(int(match[2]))
            message = messages[index]
            body = message.get("content")
            text = body if isinstance(body, str) else _text(message)
            quote = trap.get("quote")
            valid = (message.get("role") == "user" and isinstance(quote, str)
                     and bool(quote.strip()) and quote in text)
        if not valid:
            errors.append(f"{trap.get('id')}: citation does not quote an actual user message in the declared trace")
    if any(len(values) > 1 for values in anchors.values()):
        errors.append("different citation anchors count the same user correction; use one canonical msg index per correction")
    from .grounding import alignment_problems
    return errors + alignment_problems(spec, trace, session_id)


def classify(content: str, ws: rec.Workspace, session_id: str) -> tuple[str, str | None, float | None]:
    """Locate a fixture file's closest ancestor in the trace."""
    exact = [r for r in ws.provenance_revisions() if r.content == content]
    if exact:
        r = exact[0]
        return ("derived" if r.origin == 'extracted_view' else "lifted"), f"{session_id}::msg{r.msg_index}::{r.path}", 1.0

    best_ratio, best_rev = 0.0, None
    lines = content.splitlines()
    for r in ws.provenance_revisions():
        # Cheap length prefilter: a file 4x the size of a candidate is not a
        # descendant of it, and the full ratio is expensive.
        if not (0.25 <= (len(r.content) + 1) / (len(content) + 1) <= 4.0):
            continue
        ratio = difflib.SequenceMatcher(None, lines, r.content.splitlines(),
                                        autojunk=False).ratio()
        if ratio > best_ratio:
            best_ratio, best_rev = ratio, r

    if best_rev is not None and best_ratio >= DERIVED_FLOOR:
        return ("derived",
                f"{session_id}::msg{best_rev.msg_index}::{best_rev.path}",
                round(best_ratio, 3))
    return "authored", None, (round(best_ratio, 3) if best_rev else None)


def build(bundle: Path, session_id: str, seed_index: int | None = None,
          root: Path | None = None) -> dict:
    root = root or sessions_root()
    fixture = next((bundle / "environment" / n for n in ("files", "fixtures")
                    if (bundle / "environment" / n).is_dir()), None)
    if fixture is None:
        raise FileNotFoundError(f"no fixture directory under {bundle}/environment")

    trace = rec.load_trace(session_id, root)
    ws = rec.recover(trace, root)
    from ..dump.evidence import replay_selections
    replay_selections(ws, bundle, trace, root)
    from .anonymization import verify
    from .redaction import verify as verify_redaction, combine
    privacy = combine(verify(bundle, fixture, ws, session_id),
                      verify_redaction(bundle, fixture, ws, session_id))
    from ..author.scenario import verify as verify_scenario
    authored = verify_scenario(bundle)
    from ..author.scenario import verify_bootstrap
    authored.update(verify_bootstrap(bundle, trace, session_id))

    entries: list[Entry] = []
    for path in sorted(fixture.rglob("*")):
        if not path.is_file():
            continue
        rel = str(path.relative_to(fixture))
        raw = path.read_bytes()
        if rel in authored:
            entries.append(Entry(rel, 'authored', hashlib.sha256(raw).hexdigest(), len(raw),
                                 note=authored[rel]['note']))
            continue
        if rel in privacy.get("files", {}):
            proof = privacy["files"][rel]
            ancestor = next((r for r in ws.provenance_revisions() if
                f"{session_id}::msg{r.msg_index}::{r.path}" == proof['citation']), None)
            privacy_origin = 'derived' if ancestor and ancestor.origin == 'extracted_view' else 'anonymized'
            entries.append(Entry(rel, privacy_origin, hashlib.sha256(raw).hexdigest(), len(raw),
                                 citation=proof["citation"],
                                 note="Verified typed privacy transformation; contextual semantics require independent review."))
            continue
        if path.suffix.lower() not in rec.RECOVERABLE_TEXT_EXT:
            digest = hashlib.sha256(raw).hexdigest()
            ancestor = next((r for r in ws.raw_revisions
                             if r['sha256'] == digest and r['bytes'] == len(raw)), None)
            entries.append(Entry(rel, 'lifted' if ancestor else 'authored', digest, len(raw),
                citation=f"{session_id}::msg{ancestor['msg_index']}::{ancestor['path']}" if ancestor else None,
                note='Byte-identical to a retained workspace artifact; format readability is a separate question.'
                    if ancestor else 'No byte-identical retained artifact establishes source credit.'))
            continue
        try:
            content = raw.decode()
        except UnicodeDecodeError:
            digest = hashlib.sha256(raw).hexdigest()
            ancestor = next((r for r in ws.raw_revisions
                             if r['sha256'] == digest and r['bytes'] == len(raw)), None)
            entries.append(Entry(rel, 'lifted' if ancestor else 'authored', digest, len(raw),
                citation=f"{session_id}::msg{ancestor['msg_index']}::{ancestor['path']}" if ancestor else None,
                note='Retained bytes; text decoding is unsupported.' if ancestor else 'Undecodable and no retained byte-identical source.'))
            continue
        origin, citation, similarity = classify(content, ws, session_id)
        entries.append(Entry(rel, origin, _sha(content), len(raw),
                             citation=citation, similarity=similarity))

    counts = {k: sum(1 for e in entries if e.origin == k)
              for k in ORIGINS}
    total = len(entries) or 1
    by_bytes = {k: sum(e.bytes for e in entries if e.origin == k)
                for k in ORIGINS}
    total_bytes = sum(by_bytes.values()) or 1

    from ..author.contracts import strict_json
    from .grounding import verified_alignment
    spec_path = bundle / "authoring/spec.json"
    spec = strict_json(spec_path.read_text()) if spec_path.is_file() else {}
    alignment = verified_alignment(spec, trace, session_id)

    return {
        "schema": "arena-pipeline/ledger/3",
        "spec_version": policy.SPEC_VERSION,
        "trace_alignment": alignment,
        "source": {"session_id": session_id, "seed_index": seed_index,
                   "trace_sha256": hashlib.sha256(json.dumps(trace, ensure_ascii=False, sort_keys=True).encode()).hexdigest(),
                   "recovery_inputs": ws.recovery_inputs,
                   "recovery_input_policy": "Actual supplied snapshot/blob bytes; exporter identifiers may predate upstream privacy masking.",
                   "recovered_paths": len(ws.source_paths()),
                   "recovered_bytes": ws.bytes_recovered()},
        "recovery_omissions": ws.omissions,
        "snapshot_policy": "whole-session revisions; citations after the chosen seed are augmentation, not evidence available at the seed time",
        "correction_citation_policy": "Kaizen feedback anchors resolve to the next user message; multiple anchors cannot count that correction twice",
        "counts": counts,
        "bytes": by_bytes,
        "faithfulness_by_file": share(counts),
        "faithfulness_by_bytes": share(by_bytes),
        "exact_copy_by_file": round(counts["lifted"] / total, 3),
        "exact_copy_by_bytes": round(by_bytes["lifted"] / total_bytes, 3),
        "privacy_transformation": {k: privacy[k] for k in ("manifest_sha256", "policy")} if privacy else None,
        "derived_floor": DERIVED_FLOOR,
        "method": "exact content match for `lifted`; independently replayed typed privacy edits "
                  "for `anonymized` (full source credit, zero exact-copy credit); difflib ratio over ordered lines "
                  "against every recovered revision for `derived`. Tool bodies, message-anchored "
                  "workspace text and retained blob bytes are source evidence. Available but "
                  "unsupported binary formats are distinguished from missing artifacts.",
        "entries": [asdict(e) for e in entries],
        "carrier_policy": CARRIER_POLICY,
        "carriers": carriers(entries),
    }


#: The ledger fields `with_level` writes. Delivery may rewrite exactly these
#: (and the package name); `deliverable` verifies nothing else changed.
LEVEL_FIELDS = ("faithfulness_level", "faithfulness_level_record", "faithfulness_blocked")


def with_level(bundle: Path, ledger: dict,
               calibration_reproduces_failure: bool | None = None) -> dict:
    """Attach Arena's F0-F3 faithfulness level to a measured ledger.

    Kept separate from `build` because the level is an *outcome* property read
    from several artefacts -- the ledger's fidelity, the trap provenance, the
    cited corrections -- while `build` measures only the fixture. Two of Arena's
    six batch criteria and two of its three yield metrics are uncomputable
    without it, and `measured_fields` deliberately does not cover it, so
    re-deriving the level cannot invalidate retained provenance evidence.
    """
    from . import levels

    record = levels.assign(bundle, ledger, calibration_reproduces_failure)
    out = {k: v for k, v in ledger.items() if k not in LEVEL_FIELDS}
    out["faithfulness_level"] = record["level"]
    out["faithfulness_level_record"] = record
    if record.get("blocked"):
        out["faithfulness_blocked"] = record["blocked"]
    return out


def main(argv: list[str] | None = None) -> int:
    import argparse
    ap = argparse.ArgumentParser(description="Generate a bundle's provenance ledger")
    ap.add_argument("bundle")
    ap.add_argument("--session", required=True, help="source session id (or prefix)")
    ap.add_argument("--seed", type=int, default=None)
    ap.add_argument("-o", "--out", default=None)
    args = ap.parse_args(argv)

    session = args.session
    if not (sessions_root() / session).is_dir():
        matches = [p.name for p in sessions_root().iterdir()
                   if p.name.startswith(session)]
        if len(matches) != 1:
            print(f"session prefix {session!r} matched {len(matches)} sessions")
            return 2
        session = matches[0]

    bundle = Path(args.bundle).resolve()
    ledger = build(bundle, session, args.seed)
    out = Path(args.out) if args.out else bundle / "provenance" / "ledger.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(ledger, indent=2))

    c = ledger["counts"]
    print(f"{sum(c.values())} fixture files: {c['lifted']} lifted, "
          f"{c['anonymized']} anonymized, {c['derived']} derived, {c['authored']} authored")
    print(f"faithfulness: {ledger['faithfulness_by_file']:.0%} by file, "
          f"{ledger['faithfulness_by_bytes']:.0%} by byte")
    print(f"exact-copy reuse: {ledger['exact_copy_by_bytes']:.0%} by byte")
    print(f"-> {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
