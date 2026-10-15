"""Q3: how much of the fixture each model actually displays to itself.

A fixture file is 'displayed' to the degree that its distinctive lines (probes) appear in
tool observations. 'named' = its basename/path appears in the agent's commands/code
(so it may have been parsed without being displayed). Valid steps, files with >=3 probes.
"""
from __future__ import annotations

import json
import os
import sys
from collections import Counter, defaultdict
from statistics import median

sys.path.insert(0, os.path.dirname(__file__))
from r3_common import OUT

MODELS = ("fable", "astra")
MINP = 3


def pct(n, d):
    return f"{n}/{d} ({100*n/d:.1f}%)" if d else "0/0"


def bucket(b):
    for lim, name in ((4_000, "<4 KB"), (16_000, "4-16 KB"), (64_000, "16-64 KB"), (256_000, "64-256 KB")):
        if b < lim:
            return name
    return ">=256 KB"


def main():
    rows = [json.loads(l) for l in open(os.path.join(OUT, "steps.jsonl"))]
    rows = [r for r in rows if r["valid"]]
    print("### Per-file display status (valid steps, files with >=3 probes)\n")
    print("| status | Fable files | Astra files |")
    print("|---|---|---|")
    st = {m: Counter() for m in MODELS}
    size_t = {m: defaultdict(Counter) for m in MODELS}
    instr_t = {m: defaultdict(Counter) for m in MODELS}
    ext_t = {m: defaultdict(Counter) for m in MODELS}
    per_step = {m: [] for m in MODELS}
    allfull = {m: Counter() for m in MODELS}
    nfiles_b = {m: defaultdict(Counter) for m in MODELS}
    for r in rows:
        m = r["model"]
        fs = [(k, v) for k, v in r["files"].items() if v["n_probes"] >= MINP]
        if not fs:
            continue
        full = 0
        for k, v in fs:
            fr = v["frac"]
            if fr >= 0.9:
                s = "displayed >=90%"
                full += 1
            elif fr >= 0.1:
                s = "partly displayed (10-90%)"
            elif fr > 0:
                s = "glimpsed (<10%, e.g. grep hits)"
            elif v["named"]:
                s = "never displayed, named in code"
            else:
                s = "never displayed, never named"
            st[m][s] += 1
            size_t[m][bucket(v["bytes"])][fr >= 0.9] += 1
            instr_t[m][v["in_instr"]][fr >= 0.9] += 1
            instr_t[m][("any", v["in_instr"])][fr > 0 or v["named"]] += 1
            ext = os.path.splitext(k)[1].lower()
            ext_t[m][ext][fr >= 0.9] += 1
        per_step[m].append(full / len(fs))
        allfull[m][full == len(fs)] += 1
        nb = "1-3" if len(fs) <= 3 else "4-9" if len(fs) <= 9 else "10-29" if len(fs) <= 29 else "30+"
        nfiles_b[m][nb][full == len(fs)] += 1
    order = ["displayed >=90%", "partly displayed (10-90%)", "glimpsed (<10%, e.g. grep hits)",
             "never displayed, named in code", "never displayed, never named"]
    for s in order:
        print(f"| {s} | {pct(st['fable'][s], sum(st['fable'].values()))} | {pct(st['astra'][s], sum(st['astra'].values()))} |")
    print("\n### Steps that displayed every fixture file (>=90% of its lines)\n")
    print("| model | steps | all files displayed | median share of files displayed |")
    print("|---|---|---|---|")
    for m in MODELS:
        print(f"| {m} | {sum(allfull[m].values())} | {pct(allfull[m][True], sum(allfull[m].values()))} | {median(per_step[m]):.2f} |")
    print("\n### ...by number of fixture files in the task\n")
    print("| files in task | Fable all displayed | Astra all displayed |")
    print("|---|---|---|")
    for nb in ("1-3", "4-9", "10-29", "30+"):
        print(f"| {nb} | {pct(nfiles_b['fable'][nb][True], sum(nfiles_b['fable'][nb].values()))} | {pct(nfiles_b['astra'][nb][True], sum(nfiles_b['astra'][nb].values()))} |")
    print("\n### File displayed >=90% by file size\n")
    print("| size | Fable | Astra |")
    print("|---|---|---|")
    for b in ("<4 KB", "4-16 KB", "16-64 KB", "64-256 KB", ">=256 KB"):
        print(f"| {b} | {pct(size_t['fable'][b][True], sum(size_t['fable'][b].values()))} | {pct(size_t['astra'][b][True], sum(size_t['astra'][b].values()))} |")
    print("\n### Files named in the instruction vs not\n")
    print("| file | Fable displayed >=90% | Astra displayed >=90% | Fable touched at all | Astra touched at all |")
    print("|---|---|---|---|---|")
    for k, lab in ((True, "named in instruction"), (False, "not named in instruction")):
        print(f"| {lab} | {pct(instr_t['fable'][k][True], sum(instr_t['fable'][k].values()))} | {pct(instr_t['astra'][k][True], sum(instr_t['astra'][k].values()))} | "
              f"{pct(instr_t['fable'][('any', k)][True], sum(instr_t['fable'][('any', k)].values()))} | {pct(instr_t['astra'][('any', k)][True], sum(instr_t['astra'][('any', k)].values()))} |")
    print("\n### File displayed >=90% by extension\n")
    print("| ext | Fable | Astra |")
    print("|---|---|---|")
    for e in (".md", ".txt", ".html", ".csv", ".json", ".yaml", ".xml"):
        print(f"| {e} | {pct(ext_t['fable'][e][True], sum(ext_t['fable'][e].values()))} | {pct(ext_t['astra'][e][True], sum(ext_t['astra'][e].values()))} |")
    # truncation
    print("\n### Output truncation\n")
    for m in MODELS:
        rs = [r for r in rows if r["model"] == m]
        tr = [r for r in rs if r["feats"]["n_trunc"] or r["feats"]["n_persisted"]]
        fol = [r for r in tr if r["feats"]["followed_persisted"]]
        print(f"- {m}: steps with a truncated/persisted output {pct(len(tr), len(rs))}; codex-truncations {sum(r['feats']['n_trunc'] for r in rs)}; "
              f"persisted {sum(r['feats']['n_persisted'] for r in rs)}; steps that opened the persisted file {len(fol)}")
        # files that appeared in a truncated obs and stayed <90% displayed
        lost = 0
        lost_steps = 0
        tot = 0
        for r in tr:
            any_lost = False
            for k, v in r["files"].items():
                if v["n_probes"] >= MINP and v["in_trunc_obs"]:
                    tot += 1
                    if v["frac"] < 0.9:
                        lost += 1
                        any_lost = True
            lost_steps += any_lost
        print(f"  files partly shown in a truncated output: {tot}; of which never fully displayed afterwards: {pct(lost, tot)}; steps affected {lost_steps}")
        mts = [r["feats"]["maxtok_median"] for r in rs if r["feats"].get("maxtok_median")]
        if mts:
            print(f"  codex max_output_tokens median per step: {median(mts)}")


if __name__ == "__main__":
    main()
