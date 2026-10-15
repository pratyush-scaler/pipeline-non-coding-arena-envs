"""Q6: parsing/keying idioms that could silently go wrong, and how often output caps bite.

- CSV / markdown-table parsing by naive split
- dict comprehensions keyed by a field (last duplicate wins silently)
- `| head -N` caps on search output, and whether the cap was reached (output had >= N lines)
Re-parses trajectories for call->observation pairing.
"""
from __future__ import annotations

import json
import os
import re
import sys
from collections import Counter
from multiprocessing import Pool

sys.path.insert(0, os.path.dirname(__file__))
from r3_common import ART, OUT, events

IDIOMS = {
    "split(',') on lines": re.compile(r"\.split\(\s*['\"],['\"]\s*\)"),
    "split('|') (markdown tables by hand)": re.compile(r"\.split\(\s*['\"]\|['\"]\s*\)"),
    "csv module": re.compile(r"csv\.(reader|DictReader)"),
    "dict comprehension keyed by a field {r['k']: r for r in ...}": re.compile(r"\{\s*\w+\[['\"][^'\"]+['\"]\]\s*:\s*\w+\s+for\s+\w+\s+in"),
    "dict(zip(...))": re.compile(r"dict\(zip\("),
    "duplicate-key guard (Counter / len(set)==len)": re.compile(r"len\(set\([^)]*\)\)\s*==\s*len\(|Counter\([^)]*\)\.most_common|duplicat", re.I),
    "first line of a match taken ([0] after findall/split)": re.compile(r"findall\([^)]*\)\[0\]|\.split\([^)]*\)\[0\]"),
    "re.search(...).group without loop": re.compile(r"re\.search\([^)]*\)\.group\("),
    "grep -c (count only)": re.compile(r"grep\s+-[a-zA-Z]*c\b"),
    "grep -i (case-insensitive)": re.compile(r"grep\s+-[a-zA-Z]*i|rg\s+-[a-zA-Z]*i"),
    "grep -w / word boundary": re.compile(r"grep\s+-[a-zA-Z]*w|rg\s+-[a-zA-Z]*w|\\b"),
    "grep -E alternation (synonyms)": re.compile(r"(grep|rg)\s+[^\n]*\w\|\w"),
}
HEAD_CAP = re.compile(r"\|\s*head\s+-(?:n\s*)?(\d+)\s*$")


def work(rec):
    path = os.path.join(ART, rec["path"])
    try:
        ev = events(json.load(open(path)))
    except Exception:
        return None
    obs = {e["id"]: e["text"] for e in ev if e["kind"] == "obs"}
    caps = 0
    bitten = 0
    code = []
    for e in ev:
        if e["kind"] != "call" or e["tool"] not in ("cmd", "js"):
            continue
        t = e.get("text", "")
        code.append(t)
        # split compound commands on newlines/semicolons and look at each pipeline end
        for seg in re.split(r"\n|;|&&", t):
            m = HEAD_CAP.search(seg.strip())
            if m and re.search(r"\b(grep|rg|find|ls|awk|sed|cat|sort)\b", seg):
                caps += 1
                n = int(m.group(1))
                o = obs.get(e["id"], "")
                # a capped pipeline whose whole call printed >= n lines may have hit the cap
                if o.count("\n") + 1 >= n and len([s for s in re.split(r"\n|;|&&", t) if s.strip()]) == 1:
                    bitten += 1
    c = "\n".join(code)
    return {"model": rec["model"], "caps": caps, "bitten": bitten,
            "idioms": {k: bool(rx.search(c)) for k, rx in IDIOMS.items()}}


def main():
    recs = []
    for l in open(os.path.join(OUT, "steps.jsonl")):
        r = json.loads(l)
        if r["valid"]:
            recs.append({"path": r["path"], "model": r["model"]})
    res = []
    with Pool(8) as p:
        for o in p.imap_unordered(work, recs, chunksize=8):
            if o:
                res.append(o)
    print("| idiom | Fable | Astra |")
    print("|---|---|---|")
    for k in IDIOMS:
        vals = []
        for m in ("fable", "astra"):
            xs = [x for x in res if x["model"] == m]
            n = sum(1 for x in xs if x["idioms"][k])
            vals.append(f"{n}/{len(xs)} ({100*n/len(xs):.1f}%)")
        print(f"| {k} | {vals[0]} | {vals[1]} |")
    for m in ("fable", "astra"):
        xs = [x for x in res if x["model"] == m]
        print(f"\n- {m}: steps with a `| head -N` cap on a listing/search: {sum(1 for x in xs if x['caps'])}/{len(xs)}; "
              f"capped pipelines {sum(x['caps'] for x in xs)}; single-command calls whose output reached the cap {sum(x['bitten'] for x in xs)}")


if __name__ == "__main__":
    main()
