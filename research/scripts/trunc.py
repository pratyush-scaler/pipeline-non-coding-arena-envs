"""Output truncation: Codex '…N tokens truncated…' middle elision and Claude Code
'<persisted-output>' 2 KB previews. For each truncated/persisted observation, which fixture
files did the call name, how much of each was shown in that observation, and was the file
ever displayed (>=90%) anywhere in the step?
"""
from __future__ import annotations

import json
import os
import sys
from collections import Counter
from multiprocessing import Pool

sys.path.insert(0, os.path.dirname(__file__))
from r3_common import ART, OUT, package_dir, fixture_files, instruction, events, norm
import extract


def work(rec):
    path = os.path.join(ART, rec["path"])
    try:
        ev = events(json.load(open(path)))
    except Exception:
        return None
    if not any(e["kind"] == "obs" and (e.get("truncated") or e.get("persisted")) for e in ev):
        return {"model": rec["model"], "rows": []}
    cdir = path.split("/jobs/run/")[0]
    pkg = package_dir(cdir)
    files = fixture_files(pkg)
    probes = extract.probes_for(pkg, files, norm(instruction(pkg, rec["step"]), strip_tags=True))
    calls = {e["id"]: e for e in ev if e["kind"] == "call"}
    rows = []
    for e in ev:
        if e["kind"] != "obs" or not (e.get("truncated") or e.get("persisted")):
            continue
        c = calls.get(e["id"])
        if not c:
            continue
        ct = c.get("text", "").lower()
        bt = norm(e["text"], strip_tags=True)
        br = norm(e["text"])
        for rel in files:
            base = os.path.basename(rel).lower()
            if base not in ct:
                continue
            ps = probes.get(rel) or []
            if len(ps) < 3:
                continue
            b = bt if extract.is_html(rel) else br
            shown = sum(1 for p in ps if p in b) / len(ps)
            final = rec["files"].get(rel, {}).get("frac")
            rows.append({"file": rel, "shown_in_trunc": round(shown, 3), "final": final,
                         "kind": "codex" if e.get("truncated") else "persisted"})
    return {"model": rec["model"], "rows": rows, "path": rec["path"]}


def main():
    recs = []
    for l in open(os.path.join(OUT, "steps.jsonl")):
        r = json.loads(l)
        if r["valid"] and (r["feats"]["n_trunc"] or r["feats"]["n_persisted"]):
            recs.append({"path": r["path"], "model": r["model"], "step": r["step"], "files": r["files"]})
    res = []
    with Pool(8) as p:
        for o in p.imap_unordered(work, recs, chunksize=4):
            if o:
                res.append(o)
    json.dump(res, open(os.path.join(OUT, "trunc.json"), "w"))
    print("| model | file-mentions in a truncated call | fully shown there (>=90%) | partly | elided entirely (0%) | elided entirely AND never displayed >=90% in the step | partly AND never >=90% |")
    print("|---|---|---|---|---|---|---|")
    for m in ("fable", "astra"):
        rows = [r for x in res if x["model"] == m for r in x["rows"]]
        n = len(rows)
        full = sum(1 for r in rows if r["shown_in_trunc"] >= 0.9)
        part = sum(1 for r in rows if 0 < r["shown_in_trunc"] < 0.9)
        zero = sum(1 for r in rows if r["shown_in_trunc"] == 0)
        zero_lost = sum(1 for r in rows if r["shown_in_trunc"] == 0 and (r["final"] or 0) < 0.9)
        part_lost = sum(1 for r in rows if 0 < r["shown_in_trunc"] < 0.9 and (r["final"] or 0) < 0.9)
        print(f"| {m} | {n} | {full} | {part} | {zero} | {zero_lost} ({100*zero_lost/max(1,zero):.0f}% of elided) | {part_lost} ({100*part_lost/max(1,part):.0f}% of partly) |")
        steps_lost = sum(1 for x in res if x["model"] == m and any((r["shown_in_trunc"] < 0.9) and (r["final"] or 0) < 0.9 for r in x["rows"]))
        print(f"\n{m}: steps with at least one file cut by truncation and never fully displayed afterwards: {steps_lost}\n")


if __name__ == "__main__":
    main()
