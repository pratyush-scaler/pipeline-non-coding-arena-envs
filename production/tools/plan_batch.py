"""Plan a batch: 3-5 trap-library modes per seed, as diverse as the batch quotas allow (2026-10-15).

    python3 -I plan_batch.py <seeds.json> --out DIR [--library FILE] [--seed N]

seeds.json: [{"seed": "<session id or slug>", "domain": "<professional setting>", "trace_traps": "<path>"}, ...]
(trace_traps is optional: the JSON tools/trace_traps.py wrote for that seed). Writes DIR/plan.json and one
DIR/briefs/<seed>.md per seed. Exit 0 when every seed got a plan inside the quotas, 1 when a seed got no plan or a
quota had to be relaxed (plan.json says which), 2 on bad input or no library.

Per seed: 3-5 modes, never `dead` or a D id; >= 1 proven/promising mode aimed at Fable and >= 1 aimed at Astra (`both` counts
for each); at most one pilot-first mode (literature / trace-derived / bimodal), never the lead, only when the seed's
trace signals it (unless nothing else fits), and then topped up to three proven/promising modes; at most one clock
mode, never the lead; >= 2 families (a third family is preferred). Per batch (cap = max(1, floor(0.25 x seeds))): no
family leads more than `cap` tasks and no mode leads more than `cap` tasks. Within those rules each seed takes the
best-scoring set: status (proven > promising > pilot-first), pooled miss rate (shrunk below n = 20), trace signals
for that seed (trace_traps output, or the mode's own evidence.traces naming the seed), a domain match, minus what the
batch already used, plus distinct families. Seeds are planned in file order; ties break on sha256(--seed, seed,
modes), so a rerun gives the same plan.
"""
from __future__ import annotations

import argparse
import hashlib
import itertools
import json
import re
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import paths  # noqa: E402
from batch_diversity import quota_cap  # noqa: E402

sys.path.insert(0, str(paths.TRAPS))
import traplib  # noqa: E402

CORE = ("proven", "promising")
PILOT_FIRST = traplib.PILOT_FIRST
STATUS_SCORE = {"proven": 3.0, "promising": 2.0, "bimodal": 0.5, "literature": 0.5, "trace-derived": 0.5}
LEAD_SHARE = 0.25
WEIGHTS = {3: [25, 21, 17], 4: [24, 20, 17, 12], 5: [23, 19, 16, 12, 10]}
POOL = 18  # the best-scoring modes per seed that enter the 3-subset search
STOP = {"with", "from", "that", "this", "their", "about", "into", "over", "under", "for", "and", "the", "work",
        "office", "team", "review", "task"}


def tokens(text: str) -> set[str]:
    return {t for t in re.findall(r"[a-z]{4,}", str(text).lower()) if t not in STOP}


def aims(m: dict) -> set[str]:
    return {"fable", "astra"} if m["aimed_at"] == "both" else {m["aimed_at"]} & {"fable", "astra"}


# --------------------------------------------------------------------------- trace signals

def _pick(node, seed: str):
    """The part of a trace_traps document about `seed`, when the document is keyed or listed by seed."""
    if isinstance(node, dict):
        if seed in node:
            return node[seed]
        for key in ("seeds", "sessions", "results", "ranked"):
            if key in node:
                got = _pick(node[key], seed)
                if got is not None:
                    return got
    elif isinstance(node, list):
        hits = [x for x in node if isinstance(x, dict) and seed in (x.get("seed"), x.get("session"), x.get("session_id"))]
        if hits:
            return hits
    return None


def signals_from(doc, seed: str, lib) -> dict[str, float]:
    """{mode id: strength 0..1} for every library mode a trace_traps document proposes for this seed. trace_traps.py's
    own aggregate (`proposed_ids`: [{"id", "weight"}] per session, [ids] in summary.json's `ranked`) wins over its
    per-signal `mapped_ids` wherever present. Otherwise a proposal is a dict naming a mode under
    id/mode/library_id/template/trap (strength from score/confidence/strength/weight, default 1) or a bare id string."""
    node = _pick(doc, seed)
    node = doc if node is None else node
    out: dict[str, float] = {}

    def note(ref, strength):
        m = lib.resolve(ref)
        if m:
            out[m["id"]] = max(out.get(m["id"], 0.0), strength)

    def walk(x):
        if isinstance(x, dict) and isinstance(x.get("proposed_ids"), list):
            for p in x["proposed_ids"]:
                walk(p if isinstance(p, dict) else str(p))
            return
        if isinstance(x, dict):
            ref = next((x[k] for k in ("id", "mode", "library_id", "template", "trap") if isinstance(x.get(k), str)), None)
            if ref:
                s = next((x[k] for k in ("score", "confidence", "strength", "weight")
                          if isinstance(x.get(k), (int, float)) and not isinstance(x.get(k), bool)), 1.0)
                note(ref, float(s))
            for v in x.values():
                walk(v)
        elif isinstance(x, list):
            for v in x:
                walk(v)
        elif isinstance(x, str) and re.fullmatch(r"[TLRD][0-9]+", x.strip()):
            note(x.strip(), 1.0)
    walk(node)
    top = max(out.values(), default=1.0)
    return {k: round(v / top if top > 1 else v, 3) for k, v in out.items()}


# --------------------------------------------------------------------------- planning

def evidence_strength(m: dict) -> float:
    """The best pooled miss rate over the two models, shrunk toward 0 below n = 20 (0..1)."""
    best = 0.0
    for p in ((m.get("evidence") or {}).get("pooled") or {}).values():
        if isinstance(p, list) and len(p) == 2 and p[1]:
            best = max(best, p[0] / p[1] * min(1.0, p[1] / 20))
    return best


def mode_score(m: dict, sig: dict, dom: set, used: Counter, fam_used: Counter) -> tuple[float, list[str]]:
    why = [f"{m['status']}"]
    s = STATUS_SCORE.get(m["status"], 0.0)
    ev = evidence_strength(m)
    if ev:
        s += 1.5 * ev
        why.append(f"pooled miss {ev:.0%}")
    if m["id"] in sig:
        s += 2.0 * sig[m["id"]]
        why.append(f"trace-signalled ({sig[m['id']]:.2f})")
    hit = dom & tokens(" ".join(m.get("domains") or []))
    if hit:
        s += 0.75
        why.append(f"domain match ({', '.join(sorted(hit)[:3])})")
    if used[m["id"]]:
        s -= 0.8 * used[m["id"]]
        why.append(f"already planned {used[m['id']]}x")
    s -= 0.4 * fam_used[m["family"]]
    return s, why


def valid(combo: tuple[dict, ...]) -> bool:
    core = [m for m in combo if m["status"] in CORE]
    return (sum(m["status"] in PILOT_FIRST for m in combo) <= 1 and sum(bool(m["clock"]) for m in combo) <= 1
            and any("fable" in aims(m) for m in core) and any("astra" in aims(m) for m in core)
            and len({m["family"] for m in combo}) >= 2)


def can_lead(m: dict) -> bool:
    return m["status"] in CORE and not m["clock"]


def tiebreak(rng_seed: int, seed: str, ids) -> str:
    return hashlib.sha256(f"{rng_seed}|{seed}|{'|'.join(ids)}".encode()).hexdigest()


def plan_seed(entry: dict, modes: list[dict], sig: dict, state: dict, rng_seed: int, cap: int) -> dict:
    seed, dom = entry["seed"], tokens(entry.get("domain", ""))
    scored = {}
    for m in modes:
        s, why = mode_score(m, sig, dom, state["used"], state["fam_used"])
        scored[m["id"]] = (s, why)
    ranked = sorted(modes, key=lambda m: (-scored[m["id"]][0], tiebreak(rng_seed, seed, [m["id"]])))

    def search(cands: list[dict], strict: bool):
        # the pool: the best POOL candidates, plus the best few that can cover each model and lead
        pool = cands[:POOL]
        for need in (lambda m: m["status"] in CORE and "fable" in aims(m), lambda m: m["status"] in CORE and
                     "astra" in aims(m), can_lead):
            pool += [m for m in [x for x in cands if need(x)][:4] if m not in pool]
        best = None
        for combo in itertools.combinations(pool, 3):
            if not valid(combo):
                continue
            for lead in combo:
                if not can_lead(lead):
                    continue
                if strict and (state["lead_mode"][lead["id"]] >= cap or state["lead_fam"][lead["family"]] >= cap):
                    continue
                obj = (sum(scored[m["id"]][0] for m in combo) + 1.0 * len({m["family"] for m in combo})
                       + (1.0 if lead["status"] == "proven" else 0.0) + 1.0 * evidence_strength(lead)
                       + (0.5 if lead["id"] in sig else 0.0)
                       - 1.0 * state["lead_mode"][lead["id"]] - 0.5 * state["lead_fam"][lead["family"]])
                key = (round(obj, 9), tiebreak(rng_seed, seed, sorted(m["id"] for m in combo) + [lead["id"]]))
                if best is None or key > best[0]:
                    best = (key, combo, lead)
        return best, pool

    # an unproven (pilot-first) mode enters only when the seed's trace signals it, unless nothing else fits
    signalled = [m for m in ranked if m["status"] in CORE or m["id"] in sig]
    best, relaxed, pool = None, False, []
    for cands, strict in ((signalled, True), (ranked, True), (signalled, False), (ranked, False)):
        best, pool = search(cands, strict)
        if best:
            relaxed = not strict
            break
    if best is None:
        return {"seed": seed, "domain": entry.get("domain", ""), "trace_traps": entry.get("trace_traps"),
                "signals": sig, "status": "unplanned", "modes": [],
                "notes": ["no 3-mode set meets the per-seed rules: the library needs proven/promising modes aimed at "
                          "Fable and at Astra in >= 2 families"]}
    _, combo, lead = best
    chosen = [lead] + sorted((m for m in combo if m is not lead), key=lambda m: (-scored[m["id"]][0], m["id"]))
    notes = []
    # extras: trace-signalled modes first, then a mode from a new family while only two families are covered
    extras = sorted((m for m in pool if m not in chosen), key=lambda m: (-scored[m["id"]][0], m["id"]))
    for m in extras:
        if len(chosen) >= 5:
            break
        new_family = m["family"] not in {c["family"] for c in chosen}
        if (m["id"] in sig or (new_family and len({c["family"] for c in chosen}) < 3)) and valid(tuple(chosen + [m])):
            chosen.append(m)
    # a pilot-first mode never counts toward the three measured decisive modes: top up with core modes
    for m in sorted(extras, key=lambda m: (m["family"] in {c["family"] for c in chosen}, -scored[m["id"]][0], m["id"])):
        if len(chosen) >= 5 or sum(c["status"] in CORE for c in chosen) >= 3:
            break
        if m not in chosen and m["status"] in CORE and valid(tuple(chosen + [m])):
            chosen.append(m)
    if len({c["family"] for c in chosen}) < 3:
        notes.append("only two families: the library offered no valid third-family mode for this seed")
    if sum(c["status"] in CORE for c in chosen) < 3:
        notes.append("fewer than three proven/promising modes fit: pilot the unproven one before relying on it")
    # pilot-first modes go last (lowest weight)
    chosen = [chosen[0]] + sorted(chosen[1:], key=lambda m: (m["status"] in PILOT_FIRST, -scored[m["id"]][0], m["id"]))
    weights = WEIGHTS[len(chosen)]
    if relaxed:
        notes.append(f"lead quota relaxed: {lead['id']} / {lead['family']} already leads {cap} task(s)")
    rows = []
    for i, (m, w) in enumerate(zip(chosen, weights)):
        role = "lead" if i == 0 else ("pilot-first" if m["status"] in PILOT_FIRST else "decisive")
        rows.append({"id": m["id"], "name": m["name"], "family": m["family"], "status": m["status"],
                     "aimed_at": m["aimed_at"], "clock": m["clock"], "role": role, "weight": w,
                     "why": scored[m["id"]][1]})
    for m in chosen:
        state["used"][m["id"]] += 1
    for f in {m["family"] for m in chosen}:
        state["fam_used"][f] += 1
    state["lead_mode"][lead["id"]] += 1
    state["lead_fam"][lead["family"]] += 1
    return {"seed": seed, "domain": entry.get("domain", ""), "trace_traps": entry.get("trace_traps"),
            "signals": sig, "status": "planned", "relaxed": relaxed, "lead": lead["id"], "modes": rows,
            "families": sorted({m["family"] for m in chosen}),
            "projected_free_share": round((100 - sum(weights)) / 100, 2), "notes": notes}


def plan(seeds: list[dict], lib, rng_seed: int = 0, base: Path | None = None) -> dict:
    modes = sorted((m for m in lib.modes.values() if m["status"] != "dead" and not traplib.dead_listed(m)),
                   key=lambda m: traplib._id_key(m["id"]))
    n = len(seeds)
    cap = quota_cap(n, LEAD_SHARE)
    state = {"used": Counter(), "fam_used": Counter(), "lead_mode": Counter(), "lead_fam": Counter()}
    out = []
    for e in seeds:
        sig: dict[str, float] = {}
        tt = e.get("trace_traps")
        if tt:
            p = Path(tt) if Path(tt).is_absolute() or base is None else base / tt
            sig = signals_from(json.loads(p.read_text()), e["seed"], lib)
        for m in modes:  # a mode mined from this very session counts as a full-strength signal
            if any(r.get("session") == e["seed"] for r in m["evidence"].get("traces", [])):
                sig[m["id"]] = 1.0
        out.append(plan_seed(e, modes, sig, state, rng_seed, cap))
    planned = [s for s in out if s["status"] == "planned"]
    violations = [f"{s['seed']}: unplanned" for s in out if s["status"] != "planned"]
    for what, counter in (("family", state["lead_fam"]), ("mode", state["lead_mode"])):
        for k, v in sorted(counter.items()):
            if v > cap:
                violations.append(f"lead {what} {k} leads {v} tasks > cap {cap}")
    if any(r["clock"] for s in planned for r in s["modes"] if r["role"] == "lead"):
        violations.append("a clock mode leads a task")
    presence = Counter(f for s in planned for f in s["families"])
    return {"schema": "b8/plan/1", "rng_seed": rng_seed,
            "library": {"path": str(lib.path), "generated": lib.data.get("generated"), "modes": len(lib.modes)},
            "quotas": {"lead_share": LEAD_SHARE, "cap": cap, "lead_family": dict(state["lead_fam"]),
                       "lead_mode": dict(state["lead_mode"]), "family_presence": dict(presence),
                       "violations": violations},
            "seeds": out}


# --------------------------------------------------------------------------- briefs

def slug(seed: str) -> str:
    return re.sub(r"[^A-Za-z0-9._-]+", "-", seed).strip("-")[:80] or "seed"


def brief(s: dict, lib) -> str:
    L = [f"# Trap plan: {s['seed']}", "", f"Domain: {s['domain'] or '(not given)'}"]
    if s["status"] != "planned":
        return "\n".join(L + ["", "**UNPLANNED.** " + " ".join(s["notes"]), ""])
    L += [f"Projected free share: {s['projected_free_share']:.2f} (decisive weights {', '.join(str(r['weight']) for r in s['modes'])}"
          " of 100; fillers <= 5 points each come out of the free share)", "",
          "Author with `production/briefs/AUTHOR-BRIEF-B8.md`; mode details are in `production/traps/TRAP-LIBRARY.md`.",
          "These are TARGETS: build each mode only where this seed's material supports it naturally; if one does not",
          "fit, swap in another library mode of a different family and say why in the hand-back.", "",
          "| role | mode | name | family | status | aimed at | weight | why |", "|---|---|---|---|---|---|---|---|"]
    for r in s["modes"]:
        L.append(f"| {r['role']} | {r['id']} | {r['name']} | {r['family']} | {r['status']} | {r['aimed_at']} | "
                 f"{r['weight']} | {'; '.join(r['why'])} |")
    L += [""] + [f"- {n}" for n in s["notes"]] + ([""] if s["notes"] else [])
    L += ["## authoring/traps.json skeleton (schema b8/premises/1)", "", "```json"]
    skel = {"schema": "b8/premises/1", "premises": [
        {"id": f"P{i}", "decisive": True, "template": r["id"], "aimed_at": r["aimed_at"] if r["aimed_at"] in
         ("fable", "astra", "both") else "<fable|astra|both>", "family": "<B6 premise family>", "mechanism": "<code>",
         "step": "01-task", "checks": ["<check id>"], "resolving_quote": {"file": "<file>", "text": "<verbatim>"},
         "anchors": [{"file": "<other file>", "text": "<verbatim>"}, {"file": "<third file>", "text": "<verbatim>"}],
         "default_technique": "<the parser/sort/join that gives the wrong answer>", "interlocks_with": [],
         "misreading": "<the realistic wrong reading>", "target_q": 0.4, "grounded_in": "<session::msg>"}
        for i, r in enumerate(s["modes"], 1)], "coverage_checks": [], "leak_allow": []}
    L += [json.dumps(skel, indent=1, ensure_ascii=False), "```", "", "## The modes", ""]
    for r in s["modes"]:
        L.append(traplib.render_mode(lib.modes[r["id"]]).replace("## ", "### ", 1))
    return "\n".join(L).rstrip() + "\n"


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="plan_batch.py", description=__doc__.split("\n\n")[0])
    ap.add_argument("seeds")
    ap.add_argument("--out", required=True)
    ap.add_argument("--library", help="library.json (default: paths.LIBRARY)")
    ap.add_argument("--seed", type=int, default=0, help="tie-break seed")
    a = ap.parse_args(argv)
    try:
        lib = traplib.load(a.library or paths.LIBRARY)
    except (OSError, ValueError) as exc:
        print(f"cannot read the trap library ({exc}); build it: python3 -I {paths.TRAPS / 'traplib.py'} build")
        return 2
    sp = Path(a.seeds).resolve()
    seeds = json.loads(sp.read_text())
    if not isinstance(seeds, list) or not all(isinstance(e, dict) and isinstance(e.get("seed"), str) for e in seeds):
        print("seeds.json must be a list of {\"seed\": str, \"domain\": str, \"trace_traps\": path?}")
        return 2
    if len({e["seed"] for e in seeds}) != len(seeds):
        print("seeds.json repeats a seed")
        return 2
    result = plan(seeds, lib, a.seed, sp.parent)
    out = Path(a.out).resolve()
    (out / "briefs").mkdir(parents=True, exist_ok=True)
    (out / "plan.json").write_text(json.dumps(result, indent=1, ensure_ascii=False) + "\n")
    for s in result["seeds"]:
        (out / "briefs" / f"{slug(s['seed'])}.md").write_text(brief(s, lib))
    for s in result["seeds"]:
        mods = " ".join(f"{r['id']}({r['weight']})" for r in s["modes"]) or "-"
        print(f"{s['seed'][:40]:40} {s['status']:9} {mods}{'  RELAXED' if s.get('relaxed') else ''}")
    q = result["quotas"]
    print(f"cap {q['cap']} per lead family/mode; lead families {q['lead_family']}; lead modes {q['lead_mode']}")
    for v in q["violations"]:
        print("  QUOTA", v)
    print(f"PLAN {'OK' if not q['violations'] else 'WITH VIOLATIONS'}: {out / 'plan.json'}, {len(result['seeds'])} briefs")
    return 0 if not q["violations"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
