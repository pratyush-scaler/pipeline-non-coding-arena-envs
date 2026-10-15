"""Stage A -- build the corpus index.

One row per task seed, carrying everything later stages need so that nothing
downstream has to re-read 6.2 GB of JSON. Runs the whole 500-session dump in a
few seconds on 8 workers.

The index is deterministic and content-addressed by the dump it was built from,
so a selection can always be re-derived from the artifact that produced it.
"""

from __future__ import annotations

import json
import hashlib
import os
from collections import Counter
from concurrent.futures import ProcessPoolExecutor
from dataclasses import asdict, dataclass, field
from pathlib import Path

from ..config import (ARTIFACTS, BINARY_EXT, CODE_EXT, DELIVERABLE_EXT,
                      KNOWLEDGE_WORK_CATEGORIES, MANIFEST_NAMES, sessions_root,
                      tier)
from . import recover as rec
from . import signals as sig

SCHEMA = "arena-pipeline/index/5"


def _files_index(session_id: str, root: Path | None = None) -> dict:
    """The dump's per-session file index: what was actually retained."""
    try:
        with open((root or sessions_root()) / session_id / "data.json") as fh:
            return (json.load(fh).get("metadata") or {}).get("files_index") or {}
    except (OSError, json.JSONDecodeError):
        return {}


@dataclass
class SeedRow:
    session_id: str
    seed_index: int
    seed_key: str
    n_turns: int
    span: tuple[int, int]

    model: str = ""
    model_tier: str = ""
    title: str = ""
    categories: list[str] = field(default_factory=list)
    slices: list[str] = field(default_factory=list)

    # signals
    steer_fail: int = 0
    steer_ok: int = 0
    complaint_fail: int = 0
    outcome_fail: int = 0
    outcome_ok: int = 0
    corrections: int = 0
    longest_run: int = 0
    undone: int = 0

    # recoverability, scoped to the seed span
    rec_paths: int = 0
    rec_bytes: int = 0
    rec_versions: int = 0
    # deliverable-shaped recovery: what a knowledge-work fixture is made of
    deliv_paths: int = 0
    deliv_bytes: int = 0
    deliv_versions: int = 0
    # The documents themselves, not just how many. The classifier decides
    # whether a seed supports a FIXTURE-LED task -- a reconciliation across
    # these files whose answer is in none of them -- and it cannot make that
    # judgement from a count. Paths and sizes only; contents stay out of the
    # index, which is a summary and is read whole.
    deliverable_files: list = field(default_factory=list)
    structured_paths: int = 0      # csv/tsv/json/jsonl -> a gradable contract
    code_bytes: int = 0
    deliv_share: float = 0.0
    kw_tagged: bool = False
    manifests: list[str] = field(default_factory=list)
    tests: int = 0
    binary_refs: int = 0
    trail_paths: int = 0
    trail_covered: int = 0

    bash_total: int = 0
    bash_truncated: int = 0
    bash_failed: int = 0

    # attachment evidence (session-level, copied onto each seed so priority
    # ordering needs no second pass)
    files_retained: int = 0
    files_ok: int = 0
    file_refs: int = 0
    files_dropped: int = 0
    ws_snapshots: int = 0
    snapshot_text_paths: int = 0
    retained_binary_paths: int = 0
    retained_snapshot_versions: int = 0
    recovery_omission_counts: dict = field(default_factory=dict)
    source_evidence_sha256: str = ''
    evidence_schema: str = ''
    evidence_channels: dict = field(default_factory=dict)
    delivery_paths: list = field(default_factory=list)
    requires_scope_review: bool = True

    languages: list[str] = field(default_factory=list)
    moments: list[dict] = field(default_factory=list)


class UnreadableSession(Exception):
    """The dump holds this session but we could not read it.

    Distinct from a session that was read and yielded no seed: that is a finding
    about Arena's trace, this is a failure of ours. Returning `[]` for both is how
    a truncated `data.json` used to surface as "no correction was extracted".
    """


def index_session(session_id: str, root: Path | None = None) -> list[dict]:
    """Seed rows for one session. Raises `UnreadableSession` if it cannot be read."""
    try:
        trace = rec.load_trace(session_id, root)
        outcomes = sig.load_outcomes(session_id, root)
    except (OSError, ValueError, KeyError, IndexError, TypeError) as exc:
        # json.JSONDecodeError is a ValueError.
        # Name the file, never the host path: this text reaches the report.
        detail = (f"{exc.strerror or exc}: {Path(exc.filename).name}"
                  if isinstance(exc, OSError) and exc.filename else str(exc))
        raise UnreadableSession(f"{type(exc).__name__}: {detail}") from None

    ws = rec.recover(trace, root or sessions_root())
    inputs = dict(ws.recovery_inputs)
    if 'data.json' not in inputs:
        inputs['data.json'] = hashlib.sha256(((root or sessions_root()) / session_id / 'data.json').read_bytes()).hexdigest()
    source_evidence = hashlib.sha256(json.dumps(inputs,sort_keys=True).encode()).hexdigest()
    trail = rec.hash_trail(session_id, root)
    files_index = _files_index(session_id, root)
    wsdir = (root or sessions_root()) / session_id / "workspaces"
    ws_snapshots = len([n for n in os.listdir(wsdir) if n.endswith(".json")]) \
        if wsdir.is_dir() else 0
    file_refs = sum(1 for m in trace.get("messages", [])
                    for c in m.get("content", []) if c.get("type") == "file")
    health = rec.bash_health(trace)
    seeds = sig.build_seeds(trace, outcomes)
    meta = trace.get("metadata", {})
    model = trace.get("model_name", "")

    # Per-seed bash health, by message span.
    messages = trace.get("messages", [])

    rows: list[dict] = []
    for seed in seeds:
        span_revs = ws.span(seed.lo, seed.hi + 1)
        src = {p: r for p, r in span_revs.items() if rec.ext(p) in rec.RECOVERABLE_TEXT_EXT}
        deliv = {p: r for p, r in span_revs.items() if rec.ext(p) in DELIVERABLE_EXT}
        code = {p: r for p, r in span_revs.items() if rec.ext(p) in CODE_EXT}
        deliv_bytes = sum(len(r.content.encode('utf-8')) for r in deliv.values())
        code_bytes = sum(len(r.content.encode('utf-8')) for r in code.values())
        deliv_versions = sum(1 for p in deliv
                             if len({r.content for r in ws.history(p)
                                     if seed.lo <= r.msg_index <= seed.hi + 1}) >= 2)
        versions = sum(1 for p in src
                       if len({r.content for r in ws.history(p)
                               if seed.lo <= r.msg_index <= seed.hi + 1}) >= 2)
        b_total = b_trunc = b_fail = 0
        for i in range(seed.lo, min(seed.hi + 2, len(messages))):
            for block in messages[i].get("content", []):
                if block.get("type") != "tool-bash":
                    continue
                out = block.get("output") if isinstance(block.get("output"), dict) else {}
                b_total += 1
                if out.get("stdout_truncated") or out.get("stderr_truncated"):
                    b_trunc += 1
                if out.get("exit_code") not in (0, None):
                    b_fail += 1

        runs = sig.persistence_runs(seed)
        row = SeedRow(
            session_id=session_id, seed_index=seed.index, seed_key=seed.key,
            n_turns=seed.n_turns, span=(seed.lo, seed.hi),
            model=model, model_tier=tier(model),
            title=(trace.get("title") or "")[:120],
            categories=meta.get("categories", []),
            slices=meta.get("slice_categories", []),
            steer_fail=seed.signals["steerability|failure"],
            steer_ok=seed.signals["steerability|success"],
            complaint_fail=seed.signals["praise_complaint|failure"],
            outcome_fail=seed.signals["task_outcome_explicit|failure"],
            outcome_ok=seed.signals["task_outcome_explicit|success"],
            corrections=seed.corrections,
            longest_run=runs[0] if runs else 0,
            undone=sum(m.get('undone') is True for m in messages[seed.lo:seed.hi + 2]),
            rec_paths=len(src),
            rec_bytes=sum(len(r.content.encode('utf-8')) for r in src.values()),
            rec_versions=versions,
            deliv_paths=len(deliv), deliv_bytes=deliv_bytes,
            deliverable_files=sorted(
                ({"path": path, "bytes": len(revision.content.encode('utf-8'))}
                 for path, revision in deliv.items()),
                key=lambda entry: -entry["bytes"])[:60],
            deliv_versions=deliv_versions,
            structured_paths=sum(1 for p in deliv
                                 if rec.ext(p) in (".csv", ".tsv", ".json", ".jsonl")),
            code_bytes=code_bytes,
            deliv_share=round(deliv_bytes / (deliv_bytes + code_bytes), 3)
                        if (deliv_bytes + code_bytes) else 0.0,
            kw_tagged=bool(set(meta.get("categories", [])) & KNOWLEDGE_WORK_CATEGORIES),
            manifests=[p for p in src if os.path.basename(p) in MANIFEST_NAMES],
            tests=sum(1 for p in src if "test" in p.lower() or "spec" in p.lower()),
            binary_refs=sum(1 for p in span_revs if rec.ext(p) in BINARY_EXT),
            trail_paths=len(trail),
            trail_covered=len(set(src) & set(trail)),
            bash_total=b_total, bash_truncated=b_trunc, bash_failed=b_fail,
            files_retained=len(files_index),
            files_ok=sum(1 for v in files_index.values() if v.get("status") == "ok"),
            file_refs=file_refs,
            files_dropped=meta.get("dropped_generated_file_count", 0)
                          + meta.get("dropped_upload_file_count", 0),
            ws_snapshots=ws_snapshots,
            snapshot_text_paths=len({rec.path_key(r.path) for r in ws.revisions
                if r.origin == 'snapshot' and seed.lo <= r.msg_index <= seed.hi + 1
                and rec.ext(r.path) in rec.RECOVERABLE_TEXT_EXT}),
            retained_binary_paths=len({rec.path_key(r['path']) for r in ws.raw_revisions
                if not r['text_recovered'] and seed.lo <= r['msg_index'] <= seed.hi + 1}),
            retained_snapshot_versions=len({(rec.path_key(r['path']), r['sha256']) for r in ws.raw_revisions
                if seed.lo <= r['msg_index'] <= seed.hi + 1}),
            recovery_omission_counts=dict(Counter(
                r['reason'] for r in ws.omissions
                if seed.lo <= r.get('msg_index', seed.lo) <= seed.hi + 1)),
            source_evidence_sha256=source_evidence,
            evidence_schema='arena-pipeline/evidence/1',
            evidence_channels=dict(Counter(e['kind'] for e in ws.evidence
                if seed.lo <= e['msg_index'] <= seed.hi + 1)),
            delivery_paths=sorted({e['path'] for e in ws.evidence
                if e['kind'] == 'delivery' and isinstance(e.get('path'), str)
                and not e.get('failed') and not e.get('undone')
                and seed.lo <= e['msg_index'] <= seed.hi + 1}),
            languages=sorted({m.language_hint for m in seed.moments}),
            moments=[{"signal": m.signal, "msg": m.msg_index,
                      "user": m.user_text, "prior": m.prior_assistant,
                      "lang": m.language_hint} for m in seed.moments],
        )
        rows.append(asdict(row))

    # Session-wide totals let later stages reason about chaining without a
    # second pass.
    for row in rows:
        row["session_seeds"] = len(seeds)
        row["session_bash"] = health
    return rows


def _index_or_error(session_id: str, root: Path | None = None) -> tuple[list[dict], str | None]:
    """Pool worker: rows, or the reason the session could not be read."""
    try:
        return index_session(session_id, root), None
    except UnreadableSession as exc:
        return [], str(exc)[:400]


def build(root: Path | None = None, workers: int = 8) -> dict:
    root = root or sessions_root()
    ids = list(rec.iter_sessions(root))
    rows: list[dict] = []
    # Every session is either indexed or named here. A session that silently
    # contributes no rows is indistinguishable from one with no seed, and the
    # accounting would then report our read failure as a property of the trace.
    index_errors: list[dict] = []
    with ProcessPoolExecutor(max_workers=workers) as pool:
        from functools import partial
        for session_id, (chunk, error) in zip(
                ids, pool.map(partial(_index_or_error, root=root), ids, chunksize=4)):
            rows.extend(chunk)
            if error is not None:
                index_errors.append({"session_id": session_id, "error": error})
    inventory = {}
    for name in ('inventory.json', 'cohort_manifest.json', 'dump_schema.py'):
        path = root.parent / name
        if path.is_file():
            raw = path.read_bytes()
            inventory[name] = {'sha256': hashlib.sha256(raw).hexdigest(), 'bytes':len(raw)}
            if name == 'inventory.json':
                inventory[name]['listed_paths'] = len(json.loads(raw).get('inventory', []))
            if name == 'cohort_manifest.json':
                doc = json.loads(raw)
                inventory[name]['composition'] = doc.get('composition')
                inventory[name]['sessions'] = doc.get('session_count')
    return {
        "schema": SCHEMA,
        "dump": str(root),
        "sessions": len(ids),
        "seeds": len(rows),
        "index_errors": index_errors,
        "recovery_policy": "File bodies plus anchored snapshots/blobs, uploads, user requests, clarifications, delivery records and captured tool observations. Context is separate from workspace state. Scope requires content review; extensions and byte shares are ranking signals only.",
        'dump_inventory': inventory,
        "rows": rows,
    }


def main(argv: list[str] | None = None) -> int:
    import argparse
    ap = argparse.ArgumentParser(description="Stage A -- build the corpus index")
    ap.add_argument("-o", "--out", default=str(ARTIFACTS / "index.json"))
    ap.add_argument("--dump", default=None)
    ap.add_argument("-j", "--workers", type=int, default=8)
    args = ap.parse_args(argv)

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    index = build(Path(args.dump) if args.dump else None, args.workers)
    out.write_text(json.dumps(index))
    print(f"indexed {index['sessions']} sessions -> {index['seeds']} seeds -> {out}")
    if index["index_errors"]:
        print(f"WARNING: {len(index['index_errors'])} session(s) could not be read "
              "and are recorded as index_errors (unassessed, not excluded)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
