#!/usr/bin/env python3
"""Stage I2 -- deep per-bundle audit against the rulesets.

Run with `./arena audit`. This is the second reader, not a third
gate chain: it re-derives what the gates assert from the artefacts
themselves, so a gate that is quietly wrong shows up as a
disagreement rather than as silence. Three of this batch's defects
were found here first -- twin answers, the read-off share, and
calibrations that had gone stale under an edited grader.

Original docstring follows.


The gates certify what they were built to certify. This re-reads each bundle
against PLAYBOOK_GENERAL §10 (definition of done), ANTI_REWARD_HACKING §0/§6,
and the defects found by hand in this batch. Anything it cannot decide
mechanically it says so rather than passing.
"""
from __future__ import annotations
import json, re, sys, tomllib
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
from .author.checks import normalise
from .config import bundle_paths


def jload(p, default=None):
    try: return json.loads(Path(p).read_text())
    except Exception: return default

def audit(b: Path) -> dict:
    out = {"bundle": b.name, "fail": [], "warn": [], "read": [], "info": {}}
    F, W, R = out["fail"].append, out["warn"].append, out["read"].append

    if not (b / "task.toml").is_file():
        out["fail"].append("incomplete bundle: no task.toml (build in flight, "
                           "or it failed part-way)")
        return out
    task = tomllib.loads((b / "task.toml").read_text())
    meta = task.get("metadata", {})
    ck = (jload(b / "tests" / "checks.json", {}) or {}).get("checks", [])
    objs = [c for c in ck if c.get("kind") == "objective"]
    grds = [c for c in ck if c.get("kind") == "guardrail"]
    traps = (jload(b / "authoring" / "traps.json", {}) or {}).get("traps", [])
    probes = (jload(b / "verification" / "probes.json", {}) or {}).get("results", {})
    ledger = jload(b / "provenance" / "ledger.json", {}) or {}

    # --- reviewability -----------------------------------------------------
    # The second reader's job is to re-derive what the gates assert, so it has
    # to know about the same rules. These three were enforced upstream and had
    # no independent check at all.
    if not (b / "authoring" / "spec.json").is_file():
        W("no authoring/spec.json: the design that produced this bundle was "
          "not retained, so it cannot be traced, diffed or hardened")
    if ledger.get("category") is None:
        W("provenance/ledger.json records no category; a finished task cannot "
          "be traced to the target level it was selected for")
    unjustified = [c.get("id") for c in objs
                   if len((c.get("weight_basis") or "").strip()) < 25]
    if unjustified:
        W(f"{len(unjustified)} objective(s) carry a weight with no reasoned "
          f"basis ({unjustified[:4]}); a weight nobody can defend is a weight "
          "nobody can review")
    distinct_weights = {c.get("weight") for c in objs}
    if len(objs) >= 6 and len(distinct_weights) < 3:
        W(f"{len(objs)} objectives share only {len(distinct_weights)} distinct "
          "weights; that is two buckets, not a ranking of importance")
    weighted_guardrails = [c.get("id") for c in grds if (c.get("weight") or 0) > 0]
    if weighted_guardrails:
        F(f"guardrail(s) {weighted_guardrails} carry weight; guardrails gate "
          "the task and are not part of the score, so this double-counts")
    # Calibration is only evidence about the grader that produced it. Freeze
    # rule: fixture, instruction and grader move together, so a checks.json
    # newer than the report means the numbers describe a task that no longer
    # exists. Reporting them anyway is how a stale measurement gets published
    # as a current one.
    cal = None
    stale = False
    import os
    from .artifacts import identity
    current = identity(b)
    for f in sorted((b / "verification").glob("calibration-*.json")):
        candidate = jload(f) or {}
        if candidate.get("grader_fingerprint") != current:
            stale = True
        else:
            cal = candidate
    ins = sorted((b / "steps").rglob("instruction.md"))
    instruction = "\n\n".join(p.read_text() for p in ins)
    fixture = [p for p in (b / "environment" / "files").rglob("*") if p.is_file()]
    sol = {}
    for f in (b / "solution" / "submission").glob("*.json"):
        sol.update(jload(f, {}) or {})

    out["info"] = {
        "tier": meta.get("source_tier"), "objectives": len(objs),
        "guardrails": len(grds), "traps": len(traps),
        "fixture_files": len(fixture),
        "fixture_bytes": sum(p.stat().st_size for p in fixture),
        "instruction_words": len(instruction.split()),
        "weight_sum": sum(c.get("weight", 0) for c in objs),
        "faithfulness": ledger.get("faithfulness_by_bytes"),
        "exact_copy_reuse": ledger.get("exact_copy_by_bytes"),
    }

    # --- structure / budget -------------------------------------------------
    if out["info"]["weight_sum"] != 100:
        F(f"objective weights sum to {out['info']['weight_sum']}, not 100")
    declared = {s["name"] for s in task.get("steps", [])}
    if {p.parent.name for p in ins} != declared:
        F("instruction directories do not match the declared steps")
    if not grds:
        F("no guardrails: nothing measures what the agent must not do")
    for c in grds:
        if c.get("assertion") not in ("absent", "fixture_intact"):
            F(f"guardrail {c['id']} asserts {c.get('assertion')!r}; guardrails assert negative space")
        if c.get("requires"):
            F(f"guardrail {c['id']} is gated; guardrails are never gated")
        if c.get("weight", 0) != 0:
            W(f"guardrail {c['id']} carries weight {c.get('weight')}")

    # --- §0 derived answer --------------------------------------------------
    if out["info"]["fixture_files"] <= 2:
        W(f"only {out['info']['fixture_files']} fixture file(s): a join/arbitration "
          "lever needs at least two surfaces")
    # Same formula as the designer's validator: a scalar literal is a sentinel
    # (an abstention value the instruction fixes) and can never be an
    # expression, so it is excluded from BOTH numerator and denominator. The
    # audit and the validator disagreeing is how a bundle passes one and fails
    # the other for no reason a reader can follow.
    def _sentinel(c):
        t = c.get("target") or {}
        return t.get("op") == "literal" and not isinstance(t.get("value"), (list, dict))
    derivable = [c for c in objs if not _sentinel(c)]
    transcription = [c["id"] for c in derivable
                     if not any(k in json.dumps(c.get("target") or {})
                                for k in ("difference", "intersection", "join",
                                          "where", "stem_overlap"))]
    if transcription:
        denom = sum(c["weight"] for c in derivable) or 1
        share = round(100 * sum(c["weight"] for c in derivable
                                if c["id"] in transcription) / denom)
        if share >= 50:
            F(f"{share}% of weight is single-surface read-off ({', '.join(transcription)}); "
              "§0 requires the answer be derived, not stored")
        elif share >= 30:
            W(f"{share}% of weight is single-surface read-off ({', '.join(transcription)})")

    # --- reference answer sanity -------------------------------------------
    for field, v in sol.items():
        if v is None: F(f"reference {field} is null")
        elif isinstance(v, list):
            if v and all(x is None for x in v): F(f"reference {field} is {len(v)} nulls")
            elif len(v) >= 8:
                cnt = Counter(str(x).casefold() for x in v)
                if len(cnt)/len(v) < 0.5: F(f"reference {field}: {len(v)} entries, {len(cnt)} distinct")
                else:
                    t, n = cnt.most_common(1)[0]
                    if n/len(v) >= 0.25: F(f"reference {field}: {t!r} x{n}/{len(v)}")
    empties = [c["id"] for c in objs
               if isinstance(sol.get((c.get("actual") or {}).get("path","").split(".")[-1]), list)
               and not sol.get((c.get("actual") or {}).get("path","").split(".")[-1])]
    if empties:
        w = sum(c["weight"] for c in objs if c["id"] in empties)
        # Weight alone is a PROXY and it over-reports: an empty-set check sitting
        # behind a gate that fails is never reached, so an idle agent earns
        # nothing from it. The `empty_deliverable` probe measures that directly
        # and is checked separately below. Measured on a006: 36% by weight,
        # 0.0 by probe. So this is always a warning -- the probe decides.
        probe = (probes.get("empty_deliverable") or {}).get("reward")
        W(f"empty-set answers worth {w}% by weight ({', '.join(empties)}); "
          f"empty_deliverable probe measures {probe}")
    # answer == whole population of another answer
    for a in objs:
        av = sol.get((a.get("actual") or {}).get("path","").split(".")[-1])
        if not isinstance(av, list) or len(av) < 3: continue
        for c2 in objs:
            if c2["id"] == a["id"]: continue
            bv = sol.get((c2.get("actual") or {}).get("path","").split(".")[-1])
            if isinstance(bv, list) and len(bv) == len(av) and \
               {str(normalise(x)) for x in av} == {str(normalise(x)) for x in bv}:
                W(f"{a['id']} and {c2['id']} have identical answers; one is not "
                  "adding a constraint")

    # --- counting conventions ----------------------------------------------
    # Word-bounded, and `intersection` must not count: the first version of this
    # matched it on the substring "section" and flagged two bundles that pluck
    # no headings at all.
    HEAD = re.compile(r"(?<![a-z])(heading|section|subsection|title)s?(?![a-z])", re.I)
    def _plucks(c):
        blob = json.dumps(c, ensure_ascii=False)
        blob = re.sub(r"intersection", " ", blob, flags=re.I)
        return bool(HEAD.search(blob))
    plucks_headings = [c["id"] for c in objs if _plucks(c)]
    if plucks_headings:
        low = instruction.lower()
        has_depth = any(k in low for k in ("heading level", "any level", "top-level",
                                           "depth", "level heading", "h1", "h2",
                                           "every heading", "all headings"))
        has_form = any(k in low for k in ("exactly as written", "verbatim", "as written",
                                          "without", "including"))
        if not has_depth:
            F("checks pluck headings/sections but the instruction never states which "
              "heading depths count -- the defect that scored kw-a007 four zeros")
        elif not has_form:
            W("heading depth is stated but not the recording form (text vs markup)")

    # --- probes -------------------------------------------------------------
    for name, lim in (("seed_zero", 0.0), ("golden", 1.0)):
        got = (probes.get(name) or {}).get("reward")
        if got != lim: F(f"probe {name} = {got}, must be {lim}")
    for name, hard, soft in (("answer_lookup", 1.0, 0.5), ("empty_deliverable", 0.34, 0.15),
                             ("forged_state", 1.0, 0.5)):
        pr = probes.get(name) or {}
        if pr.get("applicable") is False: continue
        got = pr.get("reward")
        if got is None: continue
        if got >= hard: F(f"probe {name} = {got}: the hack works")
        elif got > soft: W(f"probe {name} = {got}")
    if not (jload(b / "verification" / "probes.json", {}) or {}).get("untested_surfaces"):
        F("no untested_surfaces declared")

    # --- traps --------------------------------------------------------------
    ids = {c["id"] for c in ck}
    for t in traps:
        for cid in t.get("checks", []):
            if cid not in ids: F(f"trap {t['id']} drives undeclared check {cid!r}")
        if t.get("provenance") == "trace_derived" and not t.get("quote"):
            F(f"trap {t['id']} claims trace_derived with no quote")
        if t.get("provenance") == "authored" and not t.get("grounded_in"):
            F(f"trap {t['id']} authored with no fixture grounding")
    td = {t.get("derived_from") for t in traps if t.get("provenance") == "trace_derived"}
    R(f"trap causality: {len(td)} distinct corrections cited; confirm each cited moment "
      f"could plausibly cause a failure on the checks its trap drives")

    # --- instruction --------------------------------------------------------
    if re.search(r"\b(cell |row \d|column [A-Z]\b|line \d+|/home/|xpath|click )", instruction, re.I):
        F("instruction appears to dictate coordinates/paths rather than rules")
    for c in objs:
        fn = (c.get("actual") or {}).get("file")
        if fn and fn not in instruction:
            F(f"deliverable {fn!r} is read by {c['id']} but never named in the instruction")

    # --- calibration --------------------------------------------------------
    if cal is None:
        (R if not stale else out["fail"].append)(
            "calibration is STALE: tests/checks.json changed after the last "
            "report, so those numbers measure a grader that no longer exists"
            if stale else "not calibrated yet")
    else:
        s = cal["summary"]
        bands = Counter()
        for cid, r in cal["checks"].items():
            if r["kind"] != "objective": continue
            att = r["passed"] + r["failed"]
            if att == 0: bands["dead"] += 1; continue
            rate = r["passed"] / att
            from .measurement import band
            bands[band(rate)] += 1
        out["info"]["bands"] = dict(bands)
        out["info"]["mean"] = s.get("mean_reward")
        out["info"]["void"] = s.get("void")
        out["info"]["distinct"] = s.get("distinct_rewards")
        if bands["dead"]: F(f"{bands['dead']} check(s) unreachable in every rollout")
        if bands["core"] < 4: F(f"{bands['core']} checks in the 30-70% band, need 4")
        if bands["floor"] > 2: W(f"{bands['floor']} checks pass ~always")
        if s.get("distinct_rewards") == 1: F("every valid rollout scored the same; no signal")
        if s.get("void", 0) / max(s.get("requested", 1), 1) > 0.10:
            W(f"{s['void']} void rollouts")
    return out

def main(argv: list[str] | None = None) -> int:
    """Run the deep audit over every bundle.

    The body below used to sit at module scope, so merely importing
    `pipeline.audit` -- as the module-import sweep does -- ran a full audit
    and rewrote `deep-audit.json`. `python -m pipeline.audit` still reaches
    it through the __main__ guard, which is how `./arena audit` invokes it.
    """
    import argparse
    ap = argparse.ArgumentParser(description="Deep per-bundle audit against the rulesets")
    ap.add_argument("root", nargs="?", default=str(ROOT / "envs"),
                    help="directory of bundles (default: envs/)")
    ap.add_argument("-o", "--out", default=None,
                    help="where to write the JSON report")
    ns = ap.parse_args(argv)

    root = Path(ns.root)
    bundles = bundle_paths(root)
    if not bundles:
        print(f"no bundles under {root}")
        return 2
    results = [audit(b) for b in bundles if b.is_dir()]
    # Keep the default report where every other stage looks for it, but let a
    # side tree (an end-to-end rehearsal) write its own without clobbering it.
    default_out = ROOT / "pipeline-artifacts" / "deep-audit.json"
    out_path = Path(ns.out) if ns.out else (
        default_out if root.resolve() == (ROOT / "envs").resolve()
        else ROOT / "pipeline-artifacts" / f"deep-audit-{root.name}.json")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(results, indent=2))

    nf = sum(len(r["fail"]) for r in results)
    nw = sum(len(r["warn"]) for r in results)
    for r in results:
        i = r["info"]
        mark = "FAIL" if r["fail"] else ("warn" if r["warn"] else "ok")
        print(f"\n=== {r['bundle']}  [{mark}]")
        if not i:
            for m in r["fail"]: print(f"    FAIL  {m}")
            continue
        print(f"    tier {i['tier']} · {i['objectives']} obj / {i['guardrails']} grd / {i['traps']} traps · "
              f"{i['fixture_files']} files {i['fixture_bytes']:,}B · {i['instruction_words']}w · "
              f"faith {i['faithfulness']}")
        if "bands" in i:
            print(f"    mean {i['mean']} · distinct {i['distinct']} · void {i['void']} · bands {i['bands']}")
        for m in r["fail"]: print(f"    FAIL  {m}")
        for m in r["warn"]: print(f"    warn  {m}")
    print(f"\n{len(results)} bundles · {nf} failures · {nw} warnings")
    print(f"-> {out_path}")
    return 1 if nf else 0


if __name__ == "__main__":
    raise SystemExit(main())
