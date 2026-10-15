"""Batch-6 diversity quotas over a set of task trees (2026-10-13; trap-library families 2026-10-15).

    python3 -I batch_diversity.py [--library FILE] <task-dir> [...]

Reads each task's authoring/traps.json + tests/checks.json. Reports family presence (share of tasks carrying the
family) and heaviest-premise family per task (by weight share), and checks the batch quotas from Arena 261013:
  no family is the heaviest premise in more than 20% of tasks; no family is present in more than 35% of tasks;
  at least 10 distinct families across the batch; timestamp-ordering present in at most 15% of tasks.
Then the same batch by trap-library family (B8): a premise counts under its template's library family
(production/traps/library.json, else the built-in B7 catalogue; a premise with no resolvable template keeps its own
family). Quotas, each allowing at least one task (cap = max(1, floor(share x tasks))): no library family is the
heaviest premise in more than 25% of tasks, no lead template (the heaviest decisive premise's) in more than 25%,
and no clock mode leads a task.
"""
import json
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import design_lint  # noqa: E402  (load_templates / is_clock: the lint's own reading of the library)

MAX_HEAVIEST, MAX_PRESENCE, MIN_FAMILIES, MAX_TS = 0.20, 0.35, 10, 0.15
LIB_MAX_HEAVIEST, LIB_MAX_LEAD = 0.25, 0.25


def quota_cap(n: int, share: float) -> int:
    """Most tasks a quota of `share` allows in a batch of n (always at least one)."""
    return max(1, int(share * n + 1e-9))


def library_view(tasks, tlib) -> tuple[list[str], list[str]]:
    """Report lines and quota failures by trap-library family and lead template."""
    n = len(tasks)
    presence, heaviest, leads, clock_leads = Counter(), Counter(), Counter(), []
    for t in tasks:
        traps = json.loads((t / "authoring/traps.json").read_text())
        raw = json.loads((t / "tests/checks.json").read_text())
        w = {c["id"]: float(c.get("weight", 0)) for c in raw.get("checks", [])}
        fams, prem = {}, []
        for p in traps["premises"]:
            mode = tlib.resolve(p.get("template")) if p.get("template") else None
            fam = mode["family"] if mode else p["family"]
            pw = sum(w.get(c, 0) for c in p["checks"])
            fams[fam] = fams.get(fam, 0) + pw
            prem.append((pw, bool(p.get("decisive")), p, mode))
        presence.update(fams.keys())
        heaviest[max(fams, key=fams.get)] += 1
        pool = [x for x in prem if x[1]] or prem
        _, _, p, mode = max(pool, key=lambda x: x[0])
        leads[mode["id"] if mode else str(p.get("template") or p["id"] + " (no template)")] += 1
        if design_lint.is_clock(p, mode):
            clock_leads.append(t.name)
    cap_h, cap_l = quota_cap(n, LIB_MAX_HEAVIEST), quota_cap(n, LIB_MAX_LEAD)
    lines = [f"library families ({tlib.source}):"]
    bad = []
    for fam, k in presence.most_common():
        h = heaviest.get(fam, 0)
        lines.append(f"  {fam:28} present {k:3} ({k / n:.0%})  heaviest {h:3} ({h / n:.0%})")
        if h > cap_h:
            bad.append(f"library family {fam} heaviest in {h} tasks > {cap_h} ({LIB_MAX_HEAVIEST:.0%} of {n})")
    lines.append("  lead templates: " + ", ".join(f"{k} {v} ({v / n:.0%})" for k, v in leads.most_common()))
    for k, v in sorted(leads.items()):
        if v > cap_l:
            bad.append(f"lead template {k} in {v} tasks > {cap_l} ({LIB_MAX_LEAD:.0%} of {n})")
    if clock_leads:
        bad.append(f"a clock premise leads {clock_leads} (never the primary failure)")
    return lines, bad


def main(argv) -> int:
    lib_file = argv[argv.index("--library") + 1] if "--library" in argv else None
    args = [a for i, a in enumerate(argv) if a != "--library" and (i == 0 or argv[i - 1] != "--library")]
    tasks = [Path(p) for p in args if (Path(p) / "authoring/traps.json").is_file()]
    n = len(tasks)
    presence, heaviest = Counter(), Counter()
    for t in tasks:
        traps = json.loads((t / "authoring/traps.json").read_text())
        raw = json.loads((t / "tests/checks.json").read_text())
        w = {c["id"]: float(c.get("weight", 0)) for c in raw.get("checks", [])}
        fams = {}
        for p in traps["premises"]:
            fams[p["family"]] = fams.get(p["family"], 0) + sum(w.get(c, 0) for c in p["checks"])
        presence.update(fams.keys())
        heaviest[max(fams, key=fams.get)] += 1
    bad = []
    print(f"{n} tasks; {len(presence)} distinct families")
    for fam, k in presence.most_common():
        h = heaviest.get(fam, 0)
        print(f"  {fam:28} present {k:3} ({k / n:.0%})  heaviest {h:3} ({h / n:.0%})")
        if k / n > MAX_PRESENCE:
            bad.append(f"{fam} present in {k / n:.0%} > {MAX_PRESENCE:.0%}")
        if h / n > MAX_HEAVIEST:
            bad.append(f"{fam} heaviest in {h / n:.0%} > {MAX_HEAVIEST:.0%}")
    if len(presence) < MIN_FAMILIES:
        bad.append(f"only {len(presence)} families (need >= {MIN_FAMILIES})")
    if presence.get("timestamp_ordering", 0) / max(n, 1) > MAX_TS:
        bad.append(f"timestamp_ordering in {presence['timestamp_ordering'] / n:.0%} > {MAX_TS:.0%}")
    tlib = design_lint.load_templates(Path(lib_file) if lib_file else None)
    if tlib.error:
        bad.append(f"trap library unreadable: {tlib.error}")
    lines, lib_bad = library_view(tasks, tlib)
    print("\n".join(lines))
    bad += lib_bad
    for b in bad:
        print("  QUOTA", b)
    print("BATCH DIVERSITY:", "PASS" if not bad else f"FAIL ({len(bad)})")
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
