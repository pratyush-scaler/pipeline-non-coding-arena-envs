"""Display rate by folder: authored `scenario/` (and `sources/`) folders vs original trace files.
Small files (<16 KB, >=3 probes), valid steps."""
import json, os, sys
from collections import Counter
sys.path.insert(0, os.path.dirname(__file__))
from r3_common import OUT
rows = [json.loads(l) for l in open(os.path.join(OUT, "steps.jsonl"))]
rows = [r for r in rows if r["valid"]]
print("| folder | instruction names file | Fable displayed >=90% | Astra displayed >=90% | Fable untouched | Astra untouched |")
print("|---|---|---|---|---|---|")
for fold in ("scenario/", "sources/", "other"):
    for ins in (True, False):
        c = {m: Counter() for m in ("fable", "astra")}
        for r in rows:
            for k, v in r["files"].items():
                if v["n_probes"] < 3 or v["bytes"] >= 16000 or v["in_instr"] != ins:
                    continue
                f = "scenario/" if k.startswith("scenario/") else "sources/" if k.startswith("sources/") else "other"
                if f != fold:
                    continue
                c[r["model"]]["n"] += 1
                c[r["model"]]["disp"] += v["frac"] >= 0.9
                c[r["model"]]["un"] += (v["frac"] == 0 and not v["named"])
        def p(m, k):
            n = c[m]["n"]
            return f"{c[m][k]}/{n} ({100*c[m][k]/n:.0f}%)" if n else "-"
        print(f"| {fold} | {ins} | {p('fable','disp')} | {p('astra','disp')} | {p('fable','un')} | {p('astra','un')} |")
