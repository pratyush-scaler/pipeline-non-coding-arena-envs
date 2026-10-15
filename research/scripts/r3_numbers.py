"""Q2 detail: rounding idioms vs whether the instruction states a rounding rule;
Decimal construction from floats; strptime/fromisoformat formats; date arithmetic idioms.
"""
from __future__ import annotations

import gzip
import json
import os
import re
import sys
from collections import Counter

sys.path.insert(0, os.path.dirname(__file__))
from r3_common import OUT, ART, instruction

MODELS = ("fable", "astra")
ROUND_WORDS = re.compile(r"half[- ]up|half[- ]even|round(ed|ing)?\b|arrondi|redonde|arredond|runden|округл|四舍五入|舍入|to the cent|al céntimo|au centime|ao cêntimo|two decimals|2 decimals|dos decimales|deux décimales|duas casas", re.I)
HALF_UP_WORDS = re.compile(r"half[- ]up|away from zero|au plus proche.{0,40}supérieur|hacia arriba|para cima|四舍五入|kaufmännisch", re.I)
MONEY_WORDS = re.compile(r"\bUSD|EUR|GBP|\$|€|£|₽|ringgit|rupee|yuan|¥|money|cent\b|centime|céntimo", re.I)


def pct(n, d):
    return f"{n}/{d} ({100*n/d:.1f}%)" if d else "0/0"


def main():
    code = {}
    with gzip.open(os.path.join(OUT, "code.jsonl.gz"), "rt") as f:
        for l in f:
            d = json.loads(l)
            code[d["path"]] = d["code"]
    rows = [json.loads(l) for l in open(os.path.join(OUT, "steps.jsonl"))]
    rows = [r for r in rows if r["valid"]]
    groups = {}
    for r in rows:
        ins = instruction(os.path.join(ART, r["pkg"]), r["step"])
        g = "instruction states half-up" if HALF_UP_WORDS.search(ins) else ("instruction mentions rounding/decimals" if ROUND_WORDS.search(ins) else "no rounding wording")
        r["_g"] = g
    print("### Rounding idiom by what the instruction says\n")
    print("| instruction | model | steps | Decimal+ROUND_HALF_UP | round() and no Decimal | neither |")
    print("|---|---|---|---|---|---|")
    for g in ("instruction states half-up", "instruction mentions rounding/decimals", "no rounding wording"):
        for m in MODELS:
            rs = [r for r in rows if r["model"] == m and r["_g"] == g]
            hu = sum(1 for r in rs if r["feats"]["half_up"])
            ro = sum(1 for r in rs if r["feats"]["round"] and not r["feats"]["decimal"])
            ne = sum(1 for r in rs if not r["feats"]["round"] and not r["feats"]["decimal"])
            print(f"| {g} | {m} | {len(rs)} | {pct(hu, len(rs))} | {pct(ro, len(rs))} | {pct(ne, len(rs))} |")
    # Decimal constructor argument patterns
    pats = {
        "Decimal(str(x))": re.compile(r"Decimal\(\s*str\("),
        "Decimal('literal')": re.compile(r"Decimal\(\s*['\"]"),
        "Decimal(row/field lookup)": re.compile(r"Decimal\(\s*\w+\[|Decimal\(\s*\w+\.get\("),
        "Decimal(float(...))": re.compile(r"Decimal\(\s*float\("),
        "Decimal(round(...)) / Decimal(sum(...))": re.compile(r"Decimal\(\s*(round|sum)\("),
        "Decimal(bare name)": re.compile(r"Decimal\(\s*[a-z_]\w*\s*\)"),
        "Fraction(...) exact arithmetic": re.compile(r"Fraction\("),
        "round(x, 2)": re.compile(r"\bround\([^()]*(\([^()]*\))?[^()]*,\s*2\s*\)"),
        "round(x) to integer": re.compile(r"\bround\([^,()]*(\([^()]*\))?[^,()]*\)"),
        "int(x) truncation of a computed value": re.compile(r"\bint\(\s*[a-z_]\w*\s*[*/]"),
    }
    print("\n### Number-construction idioms (share of valid steps)\n")
    print("| idiom | Fable | Astra |")
    print("|---|---|---|")
    for k, rx in pats.items():
        c = {m: sum(1 for r in rows if r["model"] == m and rx.search(code.get(r["path"], ""))) for m in MODELS}
        n = {m: sum(1 for r in rows if r["model"] == m) for m in MODELS}
        print(f"| `{k}` | {pct(c['fable'], n['fable'])} | {pct(c['astra'], n['astra'])} |")
    # date formats
    fmt = re.compile(r"strptime\([^,]+,\s*(['\"])(.*?)\1")
    c = {m: Counter() for m in MODELS}
    for r in rows:
        for mm in fmt.finditer(code.get(r["path"], "")):
            c[r["model"]][mm.group(2)] += 1
    print("\n### strptime formats used\n")
    for m in MODELS:
        print(f"- {m}: {c[m].most_common(12)}")
    dpats = {
        "date.fromisoformat / datetime.fromisoformat": re.compile(r"fromisoformat"),
        "(d2 - d1).days": re.compile(r"\)\.days\b|\.days\b"),
        "+ 1 inclusive day count": re.compile(r"\.days\s*\+\s*1"),
        "timedelta(days=...)": re.compile(r"timedelta\(\s*days\s*="),
        "weekday() >= 5 / weekend test": re.compile(r"weekday\(\)\s*(>=|>|<|<=|in|==)\s*[\d(\[{]"),
        "date range loop (while d <= end)": re.compile(r"while\s+\w+\s*<=?\s*\w+"),
        "isocalendar / ISO week": re.compile(r"isocalendar|%V|%G"),
        "explicit timezone handling": re.compile(r"zoneinfo|pytz|astimezone|tzinfo|utcoffset|timezone\("),
        "string date comparison (slices like [:10])": re.compile(r"\[:10\]|\[:7\]"),
    }
    print("\n### Date-arithmetic idioms (share of valid steps)\n")
    print("| idiom | Fable | Astra |")
    print("|---|---|---|")
    for k, rx in dpats.items():
        cc = {m: sum(1 for r in rows if r["model"] == m and rx.search(code.get(r["path"], ""))) for m in MODELS}
        n = {m: sum(1 for r in rows if r["model"] == m) for m in MODELS}
        print(f"| {k} | {pct(cc['fable'], n['fable'])} | {pct(cc['astra'], n['astra'])} |")


if __name__ == "__main__":
    main()


def fixture_rule_split():
    """Steps whose instruction does NOT state half-up, split by whether a fixture document does."""
    from r3_common import fixture_files, read_fixture
    rows = [json.loads(l) for l in open(os.path.join(OUT, "steps.jsonl"))]
    rows = [r for r in rows if r["valid"]]
    cache = {}
    print("\n### Rounding rule stated only in a source document (instruction silent on half-up)\n")
    print("| where the half-up rule is | model | steps | Decimal+ROUND_HALF_UP | round() and no Decimal | neither |")
    print("|---|---|---|---|---|---|")
    cells = {}
    for r in rows:
        pkg = os.path.join(ART, r["pkg"])
        ins = instruction(pkg, r["step"])
        if HALF_UP_WORDS.search(ins):
            continue
        if pkg not in cache:
            cache[pkg] = any(HALF_UP_WORDS.search(read_fixture(pkg, f)) for f in fixture_files(pkg) if not f.endswith((".html", ".js", ".css")))
        g = "fixture document only" if cache[pkg] else "nowhere"
        cells.setdefault((g, r["model"]), []).append(r)
    for g in ("fixture document only", "nowhere"):
        for m in MODELS:
            rs = cells.get((g, m), [])
            hu = sum(1 for r in rs if r["feats"]["half_up"])
            ro = sum(1 for r in rs if r["feats"]["round"] and not r["feats"]["decimal"])
            ne = sum(1 for r in rs if not r["feats"]["round"] and not r["feats"]["decimal"])
            tasks = len({r["task"] for r in rs})
            print(f"| {g} ({tasks} tasks) | {m} | {len(rs)} | {pct(hu, len(rs))} | {pct(ro, len(rs))} | {pct(ne, len(rs))} |")


if __name__ == "__main__":
    fixture_rule_split()
