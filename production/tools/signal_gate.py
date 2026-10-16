"""Batch-6 calibration gate: extremely hard AND a learning signal (2026-10-13).

    python3 -I signal_gate.py <task-dir> --fable <campaign-dir> [--fable ...] --astra <campaign-dir> [--astra ...]
                              [--stage pilot|final] [--json out.json]

Reads each campaign's report.json (valid trials only; voids are excluded, never counted) and the task's premise
map (authoring/traps.json). Reports, per model and step:
  full passes / valid, distinct step scores, step-reward SD, per-premise miss rate, observed free share,
and across both models: pairwise phi between premise failures, constant premises, model sorting.

Verdict (final = 10 runs/model; pilot = 3, user 2026-10-16):
  EXTREME   task pass@1 <= 0.30 on BOTH models (primary Fable <= 0.20 preferred)          -- required
  SPREAD    every model x step: >= 3 distinct scores (pilot: >= 2) and reward SD >= 0.08    -- required
            (an all-identical model x step gives a group-relative learner nothing)
  LEARNABLE every premise is missed in some run and passed in some run, pooled over both models -- warn if not
  INDEPENDENT max |phi| between premises <= 0.5 (pooled)                                      -- warn if not
  MIX       each model has >= 1 full pass in the final (Arena: 'passes some runs')          -- warn if not
  SORTING   one model >= 0.5 while the other <= 0.1                                          -- flag
"""
from __future__ import annotations

import itertools
import json
import math
import statistics as st
import sys
from pathlib import Path

FULL = 0.9999
BAND = {"final": {"pass_max": 0.30, "fable_pref": 0.20, "distinct": 3, "sd": 0.08},
        "pilot": {"pass_max": 0.40, "fable_pref": 0.20, "distinct": 2, "sd": 0.05}}


def load_trials(dirs):
    trials = []
    for d in dirs:
        r = json.loads((Path(d) / "report.json").read_text())
        for t in r.get("trials") or []:
            if not t.get("valid"):
                continue
            steps = {}
            for s in t.get("steps") or []:
                checks = {k.split("/", 1)[-1]: (v or {}).get("value") for k, v in (s.get("checks") or {}).items()}
                steps[s["name"]] = {"reward": float(s.get("reward") or 0.0), "checks": checks}
            trials.append({"id": t.get("id"), "reward": float(t.get("reward") or 0.0), "steps": steps})
    return trials


def phi(a, b):
    n = len(a)
    n11 = sum(x and y for x, y in zip(a, b)); n10 = sum(x and not y for x, y in zip(a, b))
    n01 = sum((not x) and y for x, y in zip(a, b)); n00 = n - n11 - n10 - n01
    den = math.sqrt((n11 + n10) * (n01 + n00) * (n11 + n01) * (n10 + n00))
    return 0.0 if den == 0 else (n11 * n00 - n10 * n01) / den


def main(argv) -> int:
    task = Path(argv[0]).resolve()
    def multi(flag):
        return [argv[i + 1] for i, a in enumerate(argv) if a == flag]
    stage = argv[argv.index("--stage") + 1] if "--stage" in argv else "final"
    band = BAND[stage]
    traps = json.loads((task / "authoring/traps.json").read_text()) if (task / "authoring/traps.json").is_file() else {"premises": []}
    premises = traps.get("premises", [])
    raw = json.loads((task / "tests/checks.json").read_text())
    weights = {c["id"]: float(c.get("weight", 0)) for c in raw.get("checks", []) if c.get("kind") == "objective"}
    models = {"fable": load_trials(multi("--fable")), "astra": load_trials(multi("--astra"))}
    out = {"task": task.name, "stage": stage, "models": {}, "premises": {}, "flags": [], "warns": []}
    steps = sorted({s for ts in models.values() for t in ts for s in t["steps"]})
    print(f"{task.name} [{stage}]")
    task_pass = {}
    for m, ts in models.items():
        n = len(ts)
        full = sum(all(t["steps"][s]["reward"] >= FULL for s in t["steps"]) for t in ts)
        task_pass[m] = full / n if n else float("nan")
        rec = {"valid": n, "full": full, "pass_at_1": round(task_pass[m], 3), "steps": {}}
        for s in steps:
            sc = [t["steps"][s]["reward"] for t in ts if s in t["steps"]]
            if not sc:
                continue
            rec["steps"][s] = {"distinct": len(set(sc)), "sd": round(st.pstdev(sc), 3), "min": min(sc), "max": max(sc),
                               "full": sum(x >= FULL for x in sc)}
            line = rec["steps"][s]
            print(f"  {m:5} {s:12} full {line['full']}/{len(sc)}  distinct {line['distinct']}  sd {line['sd']:.3f}  range {line['min']:.2f}-{line['max']:.2f}")
            if line["distinct"] < band["distinct"] or line["sd"] < band["sd"]:
                out["flags"].append(f"FLAT {m} {s}: distinct {line['distinct']}, sd {line['sd']}")
        out["models"][m] = rec
        print(f"  {m:5} TASK pass@1 {task_pass[m]:.2f} ({full}/{n})")
        if n and task_pass[m] > band["pass_max"]:
            out["flags"].append(f"TOO_EASY {m}: pass@1 {task_pass[m]:.2f} > {band['pass_max']}")
        if stage == "final" and n and full == 0:
            out["warns"].append(f"NO_PASS {m}: 0/{n} full passes (Arena wants some runs right); partial spread must carry the signal")
    if task_pass.get("fable", 0) > band["fable_pref"]:
        out["warns"].append(f"primary Fable pass@1 {task_pass['fable']:.2f} > preferred {band['fable_pref']}")
    hi, lo = max(task_pass.values()), min(task_pass.values())
    if hi >= 0.5 and lo <= 0.1:
        out["flags"].append(f"SORTING: {task_pass}")
    # premises
    vecs = {}
    for p in premises:
        pooled = []
        per = {}
        for m, ts in models.items():
            miss = []
            for t in ts:
                s = t["steps"].get(p.get("step", "01-task"))
                if s is None:
                    continue
                miss.append(any((s["checks"].get(c) is not None and float(s["checks"][c]) < 1.0) for c in p["checks"]))
            per[m] = (sum(miss), len(miss))
            pooled += miss
        vecs[p["id"]] = pooled
        q = sum(pooled) / len(pooled) if pooled else float("nan")
        out["premises"][p["id"]] = {"family": p["family"], "miss": {m: f"{a}/{b}" for m, (a, b) in per.items()}, "q_pooled": round(q, 2)}
        print(f"  premise {p['id']:4} {p['family']:28} miss fable {per['fable'][0]}/{per['fable'][1]}  astra {per['astra'][0]}/{per['astra'][1]}")
        if pooled and (all(pooled) or not any(pooled)):
            out["warns"].append(f"CONSTANT premise {p['id']} ({'always missed' if all(pooled) else 'never missed'} over {len(pooled)} runs)")
    worst = 0.0
    for a, b in itertools.combinations(vecs, 2):
        if len(vecs[a]) == len(vecs[b]) and vecs[a]:
            worst = max(worst, abs(phi(vecs[a], vecs[b])))
    out["max_phi"] = round(worst, 2)
    if worst > 0.5:
        out["warns"].append(f"CORRELATED premises: max |phi| {worst:.2f} > 0.5")
    # observed free share (objective checks no run of either model ever failed)
    for s in steps:
        ids = [c for c in weights if any(c in t["steps"].get(s, {}).get("checks", {}) for ts in models.values() for t in ts)]
        total = sum(weights[c] for c in ids) or 1
        free = sum(weights[c] for c in ids if all(float(t["steps"][s]["checks"].get(c, 1) or 0) >= 1.0
                                                   for ts in models.values() for t in ts if s in t["steps"]))
        out.setdefault("free_share", {})[s] = round(free / total, 2)
        print(f"  {s}: observed free share {free / total:.2f}")
    # v5 (2026-10-14): do different runs fail on different traps? Per model, the set of premises each failing run
    # missed is its failure pattern; Arena's 261013 feedback found one pattern per step in 33/41 steps.
    v5 = {"models": {}, "ok": True, "why": []}
    for m, ts in models.items():
        pats, fam_hits, rates = [], {}, {}
        for p in premises:
            miss = [any((t["steps"].get(p.get("step", "01-task"), {}).get("checks", {}).get(c) is not None and
                         float(t["steps"][p.get("step", "01-task")]["checks"][c]) < 1.0) for c in p["checks"]) for t in ts
                    if p.get("step", "01-task") in t["steps"]]
            rates[p["id"]] = round(sum(miss) / len(miss), 2) if miss else None
        for t in ts:
            if all(t["steps"][s]["reward"] >= FULL for s in t["steps"]):
                continue
            missed = tuple(p["id"] for p in premises
                           if any((t["steps"].get(p.get("step", "01-task"), {}).get("checks", {}).get(c) is not None and
                                   float(t["steps"][p.get("step", "01-task")]["checks"][c]) < 1.0) for c in p["checks"]))
            pats.append(missed or ("(non-premise)",))
            for fam in {p["family"] for p in premises if p["id"] in missed}:
                fam_hits[fam] = fam_hits.get(fam, 0) + 1
        counts = {"+".join(k): pats.count(k) for k in sorted(set(pats))}
        dom = max(counts.values()) / len(pats) if pats else 0.0
        in_band = [pid for pid, q in rates.items() if q is not None and 0.2 <= q <= 0.8]
        rec = {"failure_patterns": counts, "dominant_share": round(dom, 2), "miss_rate": rates,
               "stochastic_premises": in_band, "family_in_failing_runs": fam_hits,
               "full": out["models"][m]["full"], "pass_at_1": out["models"][m]["pass_at_1"]}
        v5["models"][m] = rec
        print(f"  v5 {m:5} patterns {counts}  dominant {dom:.2f}  stochastic {in_band}")
        if not (out["models"][m]["pass_at_1"] <= 0.5):
            v5["why"].append(f"{m}: pass@1 {out['models'][m]['pass_at_1']} > 0.5")
        if stage == "final" and out["models"][m]["full"] == 0:
            v5["why"].append(f"{m}: no full pass")
        if len(counts) < 2:
            v5["why"].append(f"{m}: one failure pattern only")
        if len(in_band) < 2:
            v5["why"].append(f"{m}: {len(in_band)} premise(s) in the 20-80% band")
    v5["ok"] = not v5["why"]
    out["v5"] = v5
    print(f"  V5 MIXED-SIGNAL: {'PASS' if v5['ok'] else 'no'}" + ("" if v5["ok"] else f" ({'; '.join(v5['why'])})"))
    for f in out["flags"]:
        print("  FLAG", f)
    for w in out["warns"]:
        print("  warn", w)
    verdict = "IN_BAND" if not out["flags"] else ("TOO_EASY" if any(f.startswith("TOO_EASY") for f in out["flags"]) else "FLAT" if any(f.startswith("FLAT") for f in out["flags"]) else "FLAG")
    out["verdict"] = verdict
    print(f"  SIGNAL GATE [{stage}]: {verdict}")
    if "--json" in argv:
        Path(argv[argv.index("--json") + 1]).write_text(json.dumps(out, indent=1))
    return 0 if verdict == "IN_BAND" else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
