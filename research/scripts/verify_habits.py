"""Q4 detail: what do the agents' assertions actually check, and do they cross-check
after writing?  Re-parses trajectories for call order.
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

A_LINE = re.compile(r"^\s*assert\s+(.+)$", re.M)
KINDS = [
    ("source hash unchanged", re.compile(r"sha|hash|digest|before\s*==|== *before|after\s*==", re.I)),
    ("schema / key set", re.compile(r"keys\(\)|set\(.*\)\s*==\s*\{|required|schema|isinstance|type\(", re.I)),
    ("count / length", re.compile(r"\blen\(", re.I)),
    ("equals a typed numeric literal", re.compile(r"==\s*-?\d[\d_.,]*\s*($|,|\)|and|or)|-?\d[\d_.]*\s*==", re.I)),
    ("equals a typed string literal", re.compile(r"==\s*['\"][^'\"]+['\"]")),
    ("membership / uniqueness", re.compile(r"\bin\b|not in|unique|dupl", re.I)),
    ("inequality / range", re.compile(r"[<>]=?")),
    ("sum / total identity", re.compile(r"sum\(|total", re.I)),
]
PY_CALL = re.compile(r"python3?\s+(-\s*<<|-c|<<|\S+\.py)|<<\s*['\"]?(PY|EOF|PYEOF)", re.I)


def work(rec):
    path = os.path.join(ART, rec["path"])
    try:
        ev = events(json.load(open(path)))
    except Exception:
        return None
    calls = [e for e in ev if e["kind"] == "call"]
    first_write = None
    for i, e in enumerate(calls):
        t = e.get("text", "")
        p = e.get("path", "") or ""
        if (e["tool"] == "write" and "deliverables" in p) or (e["tool"] == "patch" and "deliverables" in t) or \
           (e["tool"] in ("cmd", "js") and "deliverables" in t and re.search(r"write_text\(|json\.dump\(|\.write\(|(cat|tee)\s+>|>\s*\S*deliverables", t)):
            first_write = i
            break
    n_py = sum(1 for e in calls if e["tool"] in ("cmd", "js") and PY_CALL.search(e.get("text", "")))
    post = calls[first_write + 1:] if first_write is not None else []
    cross = any("deliverables" in e.get("text", "") and "environment/files" in e.get("text", "") and PY_CALL.search(e.get("text", "")) for e in post)
    post_py = sum(1 for e in post if e["tool"] in ("cmd", "js") and PY_CALL.search(e.get("text", "")))
    code = "\n".join(e.get("text", "") for e in calls if e["tool"] in ("cmd", "js", "edit", "write"))
    kinds = Counter()
    n_ass = 0
    for m in A_LINE.finditer(code):
        n_ass += 1
        s = m.group(1)
        hit = False
        for k, rx in KINDS:
            if rx.search(s):
                kinds[k] += 1
                hit = True
                break
        if not hit:
            kinds["other"] += 1
    return {"model": rec["model"], "n_py": n_py, "post_py": post_py, "cross_after_write": cross,
            "n_assert": n_ass, "kinds": dict(kinds), "wrote": first_write is not None, "path": rec["path"]}


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
    json.dump(res, open(os.path.join(OUT, "verify.json"), "w"))
    for m in ("fable", "astra"):
        xs = [x for x in res if x["model"] == m]
        n = len(xs)
        tot = Counter()
        for x in xs:
            tot.update(x["kinds"])
        na = sum(tot.values())
        print(f"\n#### {m}: {n} valid steps")
        print(f"- steps with >=2 python runs: {sum(1 for x in xs if x['n_py'] >= 2)} ({100*sum(1 for x in xs if x['n_py'] >= 2)/n:.1f}%)")
        print(f"- steps running python again after the first deliverable write: {sum(1 for x in xs if x['post_py'])} ({100*sum(1 for x in xs if x['post_py'])/n:.1f}%)")
        print(f"- post-write script reading both the deliverable and a source file: {sum(1 for x in xs if x['cross_after_write'])} ({100*sum(1 for x in xs if x['cross_after_write'])/n:.1f}%)")
        print(f"- assert statements: {na} (median per asserting step {sorted(x['n_assert'] for x in xs if x['n_assert'])[len([x for x in xs if x['n_assert']])//2] if any(x['n_assert'] for x in xs) else 0})")
        for k, v in tot.most_common():
            print(f"  - {k}: {v} ({100*v/na:.1f}%)")


if __name__ == "__main__":
    main()
