"""Where in a file do agents stop reading?  Positional exposure for partly displayed files.

For every valid step and every fixture file displayed 10-90%, split the file's probes
(in file order) into thirds and report the share displayed in each third.
Also classifies how the file was cut: head-only, tail-only, middle gap, scattered.
Output: out/position.json and a markdown summary on stdout.
"""
from __future__ import annotations

import json
import os
import sys
from collections import Counter, defaultdict
from multiprocessing import Pool

sys.path.insert(0, os.path.dirname(__file__))
from r3_common import ART, OUT, package_dir, fixture_files, instruction, events, norm
import extract

MINP = 9


def work(rec):
    path = os.path.join(ART, rec["path"])
    try:
        traj = json.load(open(path))
    except Exception:
        return None
    cdir = path.split("/jobs/run/")[0]
    pkg = package_dir(cdir)
    files = fixture_files(pkg)
    instr_n = norm(instruction(pkg, rec["step"]), strip_tags=True)
    probes = extract.probes_for(pkg, files, instr_n)
    ev = events(traj)
    obs = "\n".join(e["text"] for e in ev if e["kind"] == "obs")
    braw, btag = norm(obs), norm(obs, strip_tags=True)
    out = []
    for rel, v in rec["files"].items():
        if v["n_probes"] < MINP or v["frac"] is None or not (0.1 <= v["frac"] < 0.9):
            continue
        ps = probes.get(rel) or []
        if len(ps) < MINP:
            continue
        b = btag if extract.is_html(rel) else braw
        hits = [p in b for p in ps]
        n = len(hits)
        thirds = [hits[: n // 3], hits[n // 3: 2 * n // 3], hits[2 * n // 3:]]
        fr = [sum(t) / len(t) if t else 0 for t in thirds]
        # longest unseen run position
        first_seen = hits.index(True) if True in hits else n
        last_seen = n - 1 - hits[::-1].index(True) if True in hits else -1
        if fr[0] >= 0.8 and fr[2] <= 0.2:
            kind = "head only (top read, bottom unseen)"
        elif fr[2] >= 0.8 and fr[0] <= 0.2:
            kind = "tail only"
        elif fr[0] >= 0.8 and fr[2] >= 0.8 and fr[1] < 0.5:
            kind = "middle gap (head+tail, middle unseen)"
        else:
            kind = "scattered (grep-like hits)"
        out.append({"model": rec["model"], "file": rel, "thirds": fr, "kind": kind,
                    "trunc": bool(v.get("in_trunc_obs")), "bytes": v["bytes"], "path": rec["path"],
                    "last_seen_frac": round((last_seen + 1) / n, 3)})
    return out


def main():
    recs = []
    for l in open(os.path.join(OUT, "steps.jsonl")):
        r = json.loads(l)
        if not r["valid"]:
            continue
        if any(v["n_probes"] >= MINP and v["frac"] is not None and 0.1 <= v["frac"] < 0.9 for v in r["files"].values()):
            recs.append({k: r[k] for k in ("path", "model", "step", "files")})
    res = []
    with Pool(8) as p:
        for o in p.imap_unordered(work, recs, chunksize=4):
            if o:
                res.extend(o)
    json.dump(res, open(os.path.join(OUT, "position.json"), "w"))
    print("### Partly displayed files: which part was seen\n")
    print("| cut | Fable | Astra |")
    print("|---|---|---|")
    c = {m: Counter(x["kind"] for x in res if x["model"] == m) for m in ("fable", "astra")}
    for k in sorted(set(c["fable"]) | set(c["astra"])):
        tf, ta = sum(c["fable"].values()), sum(c["astra"].values())
        print(f"| {k} | {c['fable'][k]}/{tf} ({100*c['fable'][k]/tf:.1f}%) | {c['astra'][k]}/{ta} ({100*c['astra'][k]/ta:.1f}%) |")
    print("\n| mean share displayed | first third | middle third | last third |")
    print("|---|---|---|---|")
    for m in ("fable", "astra"):
        xs = [x for x in res if x["model"] == m]
        if xs:
            print(f"| {m} | " + " | ".join(f"{sum(x['thirds'][i] for x in xs)/len(xs):.2f}" for i in range(3)) + " |")
    print("\n| cut, files shown in a truncated output | Fable | Astra |")
    print("|---|---|---|")
    c = {m: Counter(x["kind"] for x in res if x["model"] == m and x["trunc"]) for m in ("fable", "astra")}
    for k in sorted(set(c["fable"]) | set(c["astra"])):
        print(f"| {k} | {c['fable'][k]} | {c['astra'][k]} |")


if __name__ == "__main__":
    main()
