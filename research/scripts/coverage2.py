"""Q3 refinements: status by file size; small files outside the instruction in small tasks;
bulk (glob) reads that could parse a file without naming it; README/summary files.
"""
from __future__ import annotations

import gzip
import json
import os
import re
import sys
from collections import Counter, defaultdict

sys.path.insert(0, os.path.dirname(__file__))
from r3_common import OUT

MODELS = ("fable", "astra")
BULK = re.compile(r"rglob\(|\bglob\(|os\.walk|iterdir\(|listdir\(|-exec\s+(cat|head|grep)|xargs|(^|[\s;|&(])cat\s+[^|;\n]*\*|for\s+\w+\s+in\s+[^;\n]*\*|grep\s+-[a-zA-Z]*r|rg\s+(?!--files)", re.M)
SUMMARY = re.compile(r"readme|summary|resumo|resumen|sommaire|overview|index\.md|notes?\b|сводк|摘要|总结", re.I)


def pct(n, d):
    return f"{n}/{d} ({100*n/d:.1f}%)" if d else "0/0"


def status(v):
    fr = v["frac"]
    if fr >= 0.9:
        return "displayed"
    if fr >= 0.1:
        return "partly"
    if fr > 0:
        return "glimpsed"
    return "named only" if v["named"] else "untouched"


def main():
    bulk = {}
    with gzip.open(os.path.join(OUT, "code.jsonl.gz"), "rt") as f:
        for l in f:
            d = json.loads(l)
            bulk[d["path"]] = bool(BULK.search(d["code"]))
    rows = [json.loads(l) for l in open(os.path.join(OUT, "steps.jsonl"))]
    rows = [r for r in rows if r["valid"]]
    sizes = [("<4 KB", 0, 4000), ("4-16 KB", 4000, 16000), ("16-64 KB", 16000, 64000), (">=64 KB", 64000, 10**12)]
    print("### Status by file size (valid steps, files with >=3 probes)\n")
    print("| size | model | displayed >=90% | partly | grep-glimpsed | named only | untouched |")
    print("|---|---|---|---|---|---|---|")
    for lab, lo, hi in sizes:
        for m in MODELS:
            c = Counter()
            for r in rows:
                if r["model"] != m:
                    continue
                for k, v in r["files"].items():
                    if v["n_probes"] >= 3 and lo <= v["bytes"] < hi:
                        c[status(v)] += 1
            t = sum(c.values())
            print(f"| {lab} | {m} | " + " | ".join(f"{100*c[s]/t:.1f}%" for s in ("displayed", "partly", "glimpsed", "named only", "untouched")) + f" (n={t}) |" if t else "")
    print("\n### Small (<16 KB) files NOT named in the instruction, tasks with <=15 files\n")
    print("| model | files | displayed >=90% | any exposure or named | untouched | untouched in steps with no glob/recursive read |")
    print("|---|---|---|---|---|---|")
    for m in MODELS:
        c = Counter()
        nb = Counter()
        for r in rows:
            if r["model"] != m or r["n_files"] > 15:
                continue
            for k, v in r["files"].items():
                if v["n_probes"] >= 3 and v["bytes"] < 16000 and not v["in_instr"]:
                    s = status(v)
                    c[s] += 1
                    c["tot"] += 1
                    if not bulk.get(r["path"]):
                        nb["tot"] += 1
                        nb[s] += 1
        t = c["tot"]
        print(f"| {m} | {t} | {pct(c['displayed'], t)} | {pct(t - c['untouched'], t)} | {pct(c['untouched'], t)} | {pct(nb['untouched'], nb['tot'])} |")
    print("\n### Same, files named in the instruction\n")
    print("| model | files | displayed >=90% | untouched |")
    print("|---|---|---|---|")
    for m in MODELS:
        c = Counter()
        for r in rows:
            if r["model"] != m or r["n_files"] > 15:
                continue
            for k, v in r["files"].items():
                if v["n_probes"] >= 3 and v["bytes"] < 16000 and v["in_instr"]:
                    c[status(v)] += 1
                    c["tot"] += 1
        t = c["tot"]
        print(f"| {m} | {t} | {pct(c['displayed'], t)} | {pct(c['untouched'], t)} |")
    print("\n### Steps using a glob/recursive read construct\n")
    for m in MODELS:
        rs = [r for r in rows if r["model"] == m]
        print(f"- {m}: {pct(sum(1 for r in rs if bulk.get(r['path'])), len(rs))}")
    print("\n### README/summary/notes-named files vs others (displayed >=90%, <16 KB)\n")
    print("| model | summary-like | other |")
    print("|---|---|---|")
    for m in MODELS:
        a, b = Counter(), Counter()
        for r in rows:
            if r["model"] != m:
                continue
            for k, v in r["files"].items():
                if v["n_probes"] >= 3 and v["bytes"] < 16000:
                    (a if SUMMARY.search(os.path.basename(k)) else b)[v["frac"] >= 0.9] += 1
        print(f"| {m} | {pct(a[True], sum(a.values()))} | {pct(b[True], sum(b.values()))} |")


if __name__ == "__main__":
    main()
