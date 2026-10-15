"""Q5: do failed checks coincide with a reading/number habit?

1. Check level: for every check that failed at least once (valid steps), compare how much of
   its target's source files the failing vs passing attempts displayed.
2. Step level: within (task, step, model) cells holding both failing and passing episodes,
   compare habit features of failing vs passing episodes (paired by cell).
Outputs markdown on stdout and out/failure_links.json.
"""
from __future__ import annotations

import json
import os
import sys
from collections import defaultdict
from statistics import mean

sys.path.insert(0, os.path.dirname(__file__))
from r3_common import OUT

MODELS = ("fable", "astra")


def main():
    cr = [json.loads(l) for l in open(os.path.join(OUT, "checks.jsonl"))]
    cr = [c for c in cr if c["valid"]]
    by = defaultdict(list)
    for c in cr:
        by[(c["task"], c["check"], c["model"])].append(c)
    rows = []
    for (task, cid, m), xs in by.items():
        f = [x for x in xs if not x["passed"]]
        if not f:
            continue
        p = [x for x in xs if x["passed"]]
        ff = [x["src_min_frac"] for x in f if x["src_min_frac"] is not None]
        pf = [x["src_min_frac"] for x in p if x["src_min_frac"] is not None]
        rows.append({
            "task": task, "check": cid, "model": m, "fails": len(f), "attempts": len(xs),
            "sources": f[0]["sources"],
            "fail_src_frac": round(mean(ff), 2) if ff else None,
            "pass_src_frac": round(mean(pf), 2) if pf else None,
            "fail_src_unnamed": sum(1 for x in f if x["src_named"] and not all(x["src_named"])),
            "fail_paths": [x["path"] for x in f][:3],
        })
    rows.sort(key=lambda r: (-r["fails"], r["task"]))
    print("### Failed checks: source-file display, failing vs passing attempts\n")
    print("| task | check | model | fails/attempts | target sources | mean min-display of sources (fail) | (pass) |")
    print("|---|---|---|---|---|---|---|")
    for r in rows:
        if r["fails"] >= 1:
            src = ", ".join(r["sources"])[:70]
            print(f"| {r['task']} | {r['check']} | {r['model']} | {r['fails']}/{r['attempts']} | {src} | {r['fail_src_frac']} | {r['pass_src_frac']} |")
    # aggregate contrast
    diffs = [r["pass_src_frac"] - r["fail_src_frac"] for r in rows if r["fail_src_frac"] is not None and r["pass_src_frac"] is not None]
    if diffs:
        print(f"\npaired checks {len(diffs)}: mean(pass - fail) source display = {mean(diffs):+.3f}; "
              f"fail lower in {sum(d > 0.05 for d in diffs)}, equal(+-0.05) {sum(abs(d) <= 0.05 for d in diffs)}, higher {sum(d < -0.05 for d in diffs)}")

    # step-level paired features
    st = [json.loads(l) for l in open(os.path.join(OUT, "steps.jsonl"))]
    st = [s for s in st if s["valid"]]
    cells = defaultdict(list)
    for s in st:
        cells[(s["task"], s["step"], s["model"])].append(s)
    feats = ["n_calls", "head", "sed_range", "grep", "rg", "wc", "assert", "sha", "round", "decimal", "re_search",
             "re_findall", "next_call", "lower", "set_call", "n_trunc", "n_persisted", "reread_deliv_after_write"]

    def share_full(s):
        fs = [v for v in s["files"].values() if v["n_probes"] >= 3]
        return sum(1 for v in fs if v["frac"] >= 0.9) / len(fs) if fs else None

    def share_seen(s):
        fs = [v for v in s["files"].values() if v["n_probes"] >= 3]
        return sum(1 for v in fs if v["frac"] > 0 or v["named"]) / len(fs) if fs else None

    print("\n### Paired step contrast (cells with >=1 failing and >=1 passing episode)\n")
    print("| feature | model | cells | mean in failing eps | mean in passing eps |")
    print("|---|---|---|---|---|")
    out = {}
    for m in MODELS:
        cs = [v for (t, stp, mm), v in cells.items() if mm == m and any(x["failed"] for x in v) and any(not x["failed"] for x in v)]
        for fname in ["share_files_displayed", "share_files_touched"] + feats:
            fv, pv = [], []
            for v in cs:
                def val(x):
                    if fname == "share_files_displayed":
                        return share_full(x)
                    if fname == "share_files_touched":
                        return share_seen(x)
                    return (x["feats"].get(fname) or 0)
                fa = [val(x) for x in v if x["failed"] and val(x) is not None]
                pa = [val(x) for x in v if not x["failed"] and val(x) is not None]
                if fa and pa:
                    fv.append(mean(fa))
                    pv.append(mean(pa))
            if fv:
                out[(m, fname)] = (len(fv), mean(fv), mean(pv))
                print(f"| {fname} | {m} | {len(fv)} | {mean(fv):.2f} | {mean(pv):.2f} |")
    json.dump({"checks": rows}, open(os.path.join(OUT, "failure_links.json"), "w"), indent=1)


if __name__ == "__main__":
    main()
