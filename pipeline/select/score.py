"""Stage B/C -- kill filters and the replay-readiness index.

Two separate judgments, deliberately not blended into one number:

  * **Can we rebuild it?** (`replay_readiness`) -- a property of the trace.
  * **Is it worth rebuilding?** (`dispute`) -- a property of the disagreement
    inside it.

Blending them is how a ranking ends up led by "make my dress the same colour":
that seed has many corrections and a perfectly recoverable workspace, and is
still worthless because the corrections are about taste. Only Stage D, which
reads the correction text, can separate those -- so this module deliberately
stops short of a single ranking and hands both numbers forward.
"""

from __future__ import annotations

import json
import os
import math
from dataclasses import dataclass
from pathlib import Path

from ..config import (KNOWLEDGE_WORK_CATEGORIES, MIN_CORRECTIONS,
                      MIN_DELIVERABLE_SHARE, MIN_RECOVERED_BYTES,
                      MIN_RECOVERED_PATHS, MIN_TURNS, REPLAY_READY, RR_WEIGHTS,
                      UNGRADABLE_ONLY)


@dataclass(frozen=True)
class Verdict:
    kept: bool
    reason: str = ""


def kill_filters(row: dict) -> Verdict:
    """Hard floors only -- each one a property we cannot author our way out of.

    Anything that merely makes a trace a *worse starting point* belongs in
    select/priority.py as a tier boundary, not here. A filter that kills on
    "fewer than two corrections" throws away the material batch two would have
    been built from, and says nothing about the difference between a trace with
    two corrections and one with twelve.
    """
    cats = set(row.get("categories") or [])
    # New indices expose the original requests and all material to Stage D.
    # Extensions/tags cannot determine the requested deliverable or reject a
    # document merely because its research workspace also contains code.
    content_review = row.get('evidence_schema') == 'arena-pipeline/evidence/1'
    if not content_review and cats and cats <= UNGRADABLE_ONLY:
        return Verdict(False, "K1 session is aesthetic/meta only -- no deterministic truth source")
    if row["n_turns"] < MIN_TURNS:
        return Verdict(False, f"K2 seed is {row['n_turns']} turns -- cannot be multi-step")
    # K3-K5 are what each CATEGORY needs, not what every seed needs.
    #
    #   A/B  dispute-led: the checks come from what the user objected to, so a
    #        correction signal AND a liftable fixture are both required.
    #   C    fixture-led: the checks come from the documents. "Reconcile these
    #        thirty-two files" is a real question whether or not anyone argued,
    #        so corrections are NOT required -- only the fixture.
    #   D    thin fixture: the documents are authored, grounded in the trace's
    #        scenario, so neither corrections nor a liftable fixture apply. Only
    #        the scope rules below decide it.
    #
    # Applying the A/B bar to all four is what collapsed this corpus from 360
    # in-scope seeds to 110: 214 seeds have a liftable fixture and no
    # correction, and are category C by definition. The classifier still has to
    # find a checkable truth source in each of them; this only stops the funnel
    # discarding them before it looks.
    has_corrections = row["corrections"] >= MIN_CORRECTIONS
    has_fixture = (row["deliv_paths"] >= MIN_RECOVERED_PATHS
                   and row["deliv_bytes"] >= MIN_RECOVERED_BYTES)
    if not has_fixture and not _authored_fixtures_allowed():
        return Verdict(False, f"K4/K5 only {row['deliv_bytes']} B across "
                              f"{row['deliv_paths']} path(s) -- no fixture to "
                              "lift, and authored fixtures (target F1/F0) are off")
    if has_fixture and not has_corrections and not _fixture_led_allowed():
        return Verdict(False, "K3 no correction signal -- the trace carries a "
                              "situation but no failure mode, and fixture-led "
                              "seeds (target F2 without corrections) are off")
    # Scope: non-coding professional knowledge work. A seed whose recovered bytes
    # are mostly source code produces work that can only be judged by running it,
    # which is a different programme. Categories are session-level so they cannot
    # decide this; the byte split can, and the classifier confirms it per seed.
    if not content_review and row["deliv_share"] < MIN_DELIVERABLE_SHARE:
        return Verdict(False, f"K6 deliverable share {row['deliv_share']:.0%} -- "
                              "predominantly code, out of scope")
    if not content_review and not (row.get("kw_tagged") or set(row.get("categories") or [])
            & KNOWLEDGE_WORK_CATEGORIES):
        return Verdict(False, "K7 session carries no professional knowledge-work "
                              "category")
    return Verdict(True)


def _fixture_led_allowed() -> bool:
    """Admit fixture-led seeds -- a liftable fixture with no correction signal (target F2)."""
    return os.environ.get("ARENA_FIXTURE_LED", "1").strip().lower() in (
        "1", "true", "yes", "on")


def _authored_fixtures_allowed() -> bool:
    """Admit authored-fixture seeds -- target F1/F0, the fixture authored from the scenario."""
    return os.environ.get("ARENA_AUTHORED_FIXTURES", "1").strip().lower() in (
        "1", "true", "yes", "on")


def replay_readiness(row: dict) -> tuple[float, dict[str, float]]:
    """How much of this seed's workspace we can lift verbatim, in [0, 1].

    Each component is a ratio against a target set from the corpus
    distribution, capped at 1.0 so one enormous session cannot dominate.
    """
    c = {}
    # Breadth: eight recoverable documents is enough for a real fixture.
    c["breadth"] = min(row["deliv_paths"] / 8.0, 1.0)
    # Volume: 150 KB of deliverable text is a substantial working set.
    c["volume"] = min(math.log10(max(row["deliv_bytes"], 1)) / math.log10(150_000), 1.0)
    # Versions establish observed changes, not correctness or acceptance.
    c["versions"] = min(row["deliv_versions"] / 3.0, 1.0)
    # Coverage: of the files the hash-trail says moved, how many did we recover?
    trail = row.get("trail_paths") or 0
    c["coverage"] = min(row.get("trail_covered", 0) / min(trail, 10), 1.0) if trail else 0.0
    # Structured data: a register, table or form is what a deterministic grader
    # reads. Prose alone can only be graded by contract, which is much weaker.
    c["structured_data"] = min(row.get("structured_paths", 0) / 3.0, 1.0)
    # Deliverable share: how much of this seed is the document rather than code.
    c["deliverable_share"] = row.get("deliv_share", 0.0)
    # Truncation: corpus rate is 1.27%; this only penalises the outliers.
    total = row.get("bash_total") or 0
    c["untruncated"] = 1.0 - (row.get("bash_truncated", 0) / total) if total else 1.0

    score = sum(RR_WEIGHTS[k] * v for k, v in c.items())
    return round(score, 3), {k: round(v, 3) for k, v in c.items()}


def dispute(row: dict) -> tuple[float, dict[str, float]]:
    """How much genuine disagreement the seed carries, in [0, 1].

    `longest_run` dominates on purpose. A user re-reporting the same defect over
    consecutive turns is a model being told exactly what is wrong and failing
    again; a scatter of single corrections across a long session is usually a
    user changing their mind, which is not a capability gap.
    """
    c = {
        "volume": min(row["corrections"] / 6.0, 1.0),
        "persistence": min(row.get("longest_run", 0) / 4.0, 1.0),
        "steerability": min(row["steer_fail"] / 4.0, 1.0),
        "explicit": min(row["outcome_fail"] / 2.0, 1.0),
        "tier": 1.0 if row.get("model_tier") == "frontier" else 0.45,
    }
    score = (0.20 * c["volume"] + 0.34 * c["persistence"]
             + 0.20 * c["steerability"] + 0.10 * c["explicit"]) * (0.55 + 0.45 * c["tier"])
    return round(min(score, 1.0), 3), {k: round(v, 3) for k, v in c.items()}


def screen(index: dict, replay_ready_only: bool = True) -> dict:
    """Apply the funnel and return candidates plus the audit trail."""
    rows = index["rows"]
    kept, dropped = [], []
    stage_counts = {"all": len(rows)}
    for row in rows:
        verdict = kill_filters(row)
        if not verdict.kept:
            dropped.append({"session_id": row["session_id"],
                            "seed_index": row["seed_index"],
                            "reason": verdict.reason})
            continue
        rr, rr_parts = replay_readiness(row)
        dv, dv_parts = dispute(row)
        row = dict(row)
        row["replay_readiness"] = rr
        row["replay_parts"] = rr_parts
        row["dispute"] = dv
        row["dispute_parts"] = dv_parts
        row["replay_ready"] = rr >= REPLAY_READY
        kept.append(row)

    stage_counts["passed_kill_filters"] = len(kept)
    # Count replay-ready BEFORE deciding whether to filter on it. Printing the
    # post-filter total under a "replay-ready" label when the filter was skipped
    # reports 110 of 110 as replay-ready when the true figure is 50.
    stage_counts["replay_ready"] = sum(1 for r in kept if r["replay_ready"])
    stage_counts["applied_replay_filter"] = replay_ready_only
    if replay_ready_only:
        kept = [r for r in kept if r["replay_ready"]]
    stage_counts["carried_forward"] = len(kept)
    stage_counts["frontier"] = sum(1 for r in kept if r["model_tier"] == "frontier")
    stage_counts["sessions"] = len({r["session_id"] for r in kept})

    # Sessions with two or more surviving seeds can carry a chained two-step
    # environment, which our own yield analysis rates at roughly double value.
    by_session: dict[str, int] = {}
    for r in kept:
        by_session[r["session_id"]] = by_session.get(r["session_id"], 0) + 1
    for r in kept:
        r["session_candidate_seeds"] = by_session[r["session_id"]]
    stage_counts["chainable_sessions"] = sum(1 for n in by_session.values() if n >= 2)

    kept.sort(key=lambda r: -(r["replay_readiness"] * r["dispute"]))
    return {"schema": "arena-pipeline/candidates/1", "counts": stage_counts,
            "threshold": REPLAY_READY, "candidates": kept,
            "dropped_sample": dropped[:200]}


def main(argv: list[str] | None = None) -> int:
    import argparse
    from ..config import ARTIFACTS
    ap = argparse.ArgumentParser(description="Stage B/C -- screen the index")
    ap.add_argument("-i", "--index", default=str(ARTIFACTS / "index.json"))
    ap.add_argument("-o", "--out", default=str(ARTIFACTS / "candidates.json"))
    ap.add_argument("--all-tiers", action="store_true")
    ap.add_argument("--include-inspiration", action="store_true",
                    help="keep seeds below the replay-ready threshold")
    args = ap.parse_args(argv)

    index = json.loads(Path(args.index).read_text())
    result = screen(index, replay_ready_only=not args.include_inspiration)
    if not args.all_tiers:
        result["frontier_only"] = [r for r in result["candidates"]
                                   if r["model_tier"] == "frontier"]
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result))

    c = result["counts"]
    print(f"  all seeds                  {c['all']:5d}")
    print(f"  passed hard floors         {c['passed_kill_filters']:5d}")
    print(f"  of which replay-ready      {c['replay_ready']:5d}   (rr >= {result['threshold']})")
    if c["applied_replay_filter"]:
        print(f"  carried forward            {c['carried_forward']:5d}   "
              f"(replay-ready only)")
    else:
        print(f"  carried forward            {c['carried_forward']:5d}   "
              f"(--include-inspiration: rr used for ordering, not admission)")
    print(f"  sessions / frontier        {c['sessions']:5d} / {c['frontier']}")
    print(f"  chainable sessions (>=2)   {c['chainable_sessions']:5d}")
    print(f"-> {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
