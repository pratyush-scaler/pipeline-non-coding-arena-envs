"""Summarise the batch-4 ledger: latest campaign per (task, version, stage), b6 tasks only.

Usage: python3 -I ledsum.py [--since HOURS] [--grep SUBSTR]
"""
import json, sys, time, os
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import paths  # noqa: E402

args = sys.argv[1:]
since = float(args[args.index("--since") + 1]) if "--since" in args else 1e9
grep = args[args.index("--grep") + 1] if "--grep" in args else ""
L = json.load(open(paths.LEDGER))["entries"]
latest = {}
for e in L:
    if f"/{paths.TASKS.name}/" not in e.get("task", ""):
        continue
    key = (e["name"], e["version"], e["stage"])
    if key not in latest or e["launched_at"] >= latest[key]["launched_at"]:
        latest[key] = e
now = time.time()


def cell(r):
    if not r:
        return "-"
    s = r.get("state", "?")
    if s != "done":
        return s
    v = r.get("valid", 0)
    vd = r.get("void", 0)
    f = r.get("full", 0)
    return f"{f}/{v}" + (f" v{vd}" if vd else "")


for key in sorted(latest, key=lambda k: latest[k]["launched_at"]):
    e = latest[key]
    if (now - e["launched_at"]) / 3600 > since or grep not in key[0]:
        continue
    R = e.get("runs", {})
    fab = R.get("fable") or R.get("claude") or {}
    ast = R.get("astra") or R.get("codex") or {}
    miss = ""
    if fab.get("state") == "done":
        cp = fab.get("check_pass", {})
        v = fab.get("valid", 0)
        miss = " ".join(f"{c}:{n}/{v}" for c, n in sorted(cp.items()) if n < v)
    t = time.strftime("%H:%M", time.localtime(e["launched_at"]))
    print(f"{t} {key[0][:38]:38} {key[1]:6} {key[2]:5} F {cell(fab):8} A {cell(ast):8} | {miss}")
