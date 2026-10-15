"""Stage F1 -- lift the working material for one seed out of its trace.

This is the bridge from selection to authoring, and it is deliberately dumb: it
copies what the trace states and records where each byte came from. It invents
nothing, infers nothing, and rewrites nothing. Every judgment about what the
task should be belongs downstream, where it can be reviewed.

Why the fixture is lifted from an *intermediate* point rather than the end: the
spec frees us from the trace's final state ("it may be taken from any
intermediate step"), and the interesting moment in a disputed session is almost
never the end. It is the state just before the correction the user made -- that
is the state an agent should be asked to fix, and the trace then tells us both
what was disputed and which later revisions are available. A later revision is
candidate evidence; it does not establish correctness or user acceptance.

So extraction returns three things:

  before   the workspace as of the first correction -- fixture material
  after    the workspace at the end of the seed -- candidate revision material, which
           MUST stay out of the agent's environment
  moments  the corrections themselves, quoted, with their classification

`after` is the reason the ledger can cite a source for derived values and the
oracle can recompute rather than hardcode. It is also the single most dangerous
artefact in the bundle, so it is written to `authoring/` -- never to
`environment/` -- and `leak.sweep` checks that it stayed there.
"""

from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass, field
from pathlib import Path

from ..config import DELIVERABLE_EXT, sessions_root
from ..dump import recover as rec
from ..dump import signals as sig

#: Below this the pivot snapshot cannot carry a multi-surface task, and the
#: extraction falls back to the session's full workspace. Three is the floor
#: because every difficulty lever past Carry needs a second surface to relate
#: the first one to, and a third to arbitrate between them.
MIN_FIXTURE_DOCS = 3


@dataclass
class Document:
    path: str
    content: str
    msg_index: int
    source: str          # the tool call that revealed it
    bytes: int = 0

    def __post_init__(self) -> None:
        self.bytes = len(self.content.encode("utf-8"))


@dataclass
class Extraction:
    session_id: str
    seed_index: int
    span: tuple[int, int]
    pivot: int                      # message index the fixture is lifted at
    before: list[Document] = field(default_factory=list)
    after: list[Document] = field(default_factory=list)
    moments: list[dict] = field(default_factory=list)
    changed_paths: list[str] = field(default_factory=list)
    stats: dict = field(default_factory=dict)
    evidence_summary: dict = field(default_factory=dict)
    evidence_index: list[dict] = field(default_factory=list)
    source_root: Path | None = field(default=None, repr=False)

    def before_map(self) -> dict[str, Document]:
        return {d.path: d for d in self.before}

    def after_map(self) -> dict[str, Document]:
        return {d.path: d for d in self.after}


def usable_correction_count(row: dict, extraction: Extraction) -> int:
    """Use classified correction capacity, preserving an explicit zero.

    Discovery signals include empty outcome records. Without a classification,
    only records carrying user words can be candidates for quoted corrections.
    Keep the original signals intact for provenance and later review.
    """
    declared = (row.get('classification') or {}).get('usable_moments')
    if declared is not None:
        if type(declared) is not int or declared < 0:
            raise ValueError('usable_moments must be a nonnegative integer')
        return declared
    return sum(isinstance(m.get('user'), str) and bool(m['user'].strip())
               for m in extraction.moments)


def _clean(path: str) -> str:
    """Normalise a trace path into a fixture-relative one.

    Trace paths carry the original sandbox layout (`/home/user/uploads/x.md`).
    Keeping it would leak the harness into the fixture and make every path
    absolute; stripping it entirely would collide files from different
    directories. Keep the tail below a recognised root.
    """
    p = (path or "").replace("\\", "/").lstrip("/")
    for root in ("home/user/uploads/", "home/user/", "app/", "workspace/",
                 "uploads/", "mnt/data/", "tmp/"):
        if p.startswith(root):
            p = p[len(root):]
            break
    return p or "unnamed"


def extract(session_id: str, seed_index: int,
            root: Path | None = None) -> Extraction:
    root = root or sessions_root()
    trace = rec.load_trace(session_id, root)
    outcomes = sig.load_outcomes(session_id, root)
    seeds = {s.index: s for s in sig.build_seeds(trace, outcomes)}
    if seed_index not in seeds:
        raise KeyError(f"{session_id} has no seed {seed_index}")
    seed = seeds[seed_index]
    ws = rec.recover(trace, root)
    document_paths = sorted(p for p in ws.paths() if os.path.splitext(p)[1].lower() in DELIVERABLE_EXT)
    cleaned = [_clean(p) for p in document_paths]
    preserve_paths = len(set(cleaned)) != len(cleaned)
    output_paths = {p: p if preserve_paths else _clean(p) for p in document_paths}

    # The pivot is the first correction inside the span. Before it, the
    # workspace holds the work the user is about to dispute.
    corrections = sorted(m.msg_index for m in seed.moments)
    pivot = corrections[0] if corrections else seed.hi

    def snapshot(at: int) -> list[Document]:
        out = []
        for path, revision in sorted(ws.at(at).items()):
            if os.path.splitext(path)[1].lower() not in DELIVERABLE_EXT:
                continue
            out.append(Document(output_paths[path], revision.content,
                                revision.msg_index, revision.source))
        return out

    before = snapshot(max(pivot - 1, 0))
    after = snapshot(seed.hi + 1)

    # A pivot snapshot is the workspace one message before the first complaint,
    # and for an early seed that can be almost empty: seed 0 of 019e8da6 lifted
    # ONE 1.9 KB file while the session recovers eleven files and 32 KB. A task
    # cannot be built on that -- there is no second surface to join, difference
    # or arbitrate against, so the design degenerates into transcription. The
    # a005 bundle calibrated at a flat 1.0 for exactly this reason.
    #
    # So when the snapshot is too thin, widen to everything the session ever
    # revealed. This is not fixture synthesis: every file is a real revision
    # with a real citation, and the ledger records each one, so faithfulness is
    # measured. What must NOT come across is `after` -- a later candidate repair
    # may leak the dispute's proposed answer without proving acceptance -- so any revision whose
    # content matches an `after` document is left out.
    if len(before) < MIN_FIXTURE_DOCS:
        repair = {d.content.strip() for d in after}
        seen = {d.path for d in before}
        widened = list(before)
        for path, revision in sorted(ws.at(10 ** 9).items()):
            if os.path.splitext(path)[1].lower() not in DELIVERABLE_EXT:
                continue
            doc = Document(output_paths[path], revision.content,
                           revision.msg_index, revision.source)
            if doc.path in seen or doc.content.strip() in repair:
                continue
            widened.append(doc)
            seen.add(doc.path)
        if len(widened) > len(before):
            before = sorted(widened, key=lambda d: d.path)

    bmap = {d.path: d for d in before}
    amap = {d.path: d for d in after}
    changed = sorted(p for p in amap
                     if p not in bmap or amap[p].content != bmap[p].content)

    from ..dump.evidence import Catalog
    catalog = Catalog(trace, ws, root, (seed.lo, seed.hi), pivot)
    return Extraction(
        session_id=session_id, seed_index=seed_index,
        span=(seed.lo, seed.hi), pivot=pivot,
        before=before, after=after,
        evidence_summary=catalog.summary(),
        evidence_index=[{k:v for k,v in item.items() if k != 'text'} for item in catalog.records.values()],
        source_root=root,
        changed_paths=changed,
        moments=[{"msg": m.msg_index, "signal": m.signal, "lang": m.language_hint,
                  "user": m.user_text, "prior_assistant": m.prior_assistant}
                 for m in seed.moments],
        stats={"before_docs": len(before),
               "before_bytes": sum(d.bytes for d in before),
               "after_docs": len(after),
               "after_bytes": sum(d.bytes for d in after),
               "changed": len(changed),
               "corrections": len(seed.moments),
               "recovery_omissions": ws.omissions,
               "canonical_paths_preserved_to_avoid_collision": preserve_paths,
               "later_revision_augmentation": [d.path for d in before if d.msg_index > seed.hi],
               "pivot_is_first_correction": bool(corrections)},
    )


def write(extraction: Extraction, dest: Path) -> dict:
    """Lay the extraction out on disk.

    `environment/files/` is the agent's world. `authoring/` is ours and must
    never be copied into it. `after/` contains a later candidate repair, which
    can leak an answer but does not establish correctness or user acceptance.
    """
    from .contracts import contained
    fixture = dest / "environment" / "files"
    private = dest / "authoring" / "extraction"
    for d in (fixture, private / "after"):
        d.mkdir(parents=True, exist_ok=True)

    written = []
    for doc in extraction.before:
        target = contained(fixture, doc.path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(doc.content)
        written.append(doc.path)

    for doc in extraction.after:
        target = contained(private / "after", doc.path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(doc.content)

    (private / "moments.json").write_text(
        json.dumps(extraction.moments, indent=2, ensure_ascii=False))
    (private / 'evidence-index.json').write_text(json.dumps({
        'summary': extraction.evidence_summary, 'records': extraction.evidence_index},
        indent=2, ensure_ascii=False))
    (private / "extraction.json").write_text(json.dumps({
        "session_id": extraction.session_id,
        "seed_index": extraction.seed_index,
        "span": list(extraction.span),
        "pivot": extraction.pivot,
        "changed_paths": extraction.changed_paths,
        "stats": extraction.stats,
        "before": [asdict(d) | {"content": None} for d in extraction.before],
        "after": [asdict(d) | {"content": None} for d in extraction.after],
    }, indent=2))

    return {"fixture_files": written, "private_dir": str(private),
            "stats": extraction.stats}


def main(argv: list[str] | None = None) -> int:
    import argparse
    ap = argparse.ArgumentParser(description="Stage F1 -- extract seed material")
    ap.add_argument("session")
    ap.add_argument("seed", type=int)
    ap.add_argument("-o", "--out", required=True, help="bundle directory")
    args = ap.parse_args(argv)

    session = args.session
    if not (sessions_root() / session).is_dir():
        matches = [p.name for p in sessions_root().iterdir()
                   if p.name.startswith(session)]
        if len(matches) != 1:
            print(f"session prefix {session!r} matched {len(matches)} sessions")
            return 2
        session = matches[0]

    ex = extract(session, args.seed)
    report = write(ex, Path(args.out))
    s = ex.stats
    print(f"{session[:8]} seed {args.seed}  span {ex.span}  pivot msg {ex.pivot}")
    print(f"  fixture (before) : {s['before_docs']} docs, {s['before_bytes']:,} B")
    print(f"  ground truth     : {s['after_docs']} docs, {s['after_bytes']:,} B "
          f"({s['changed']} changed)")
    print(f"  corrections      : {s['corrections']}")
    print(f"-> {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
