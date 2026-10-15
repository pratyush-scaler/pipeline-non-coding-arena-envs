"""Gate-chain driver.

Two phases, and the ordering between them is the point:

  pre-calibration   everything checkable by reading the bundle
  post-calibration  everything that needs measured rollouts

All nine defects Arena returned on the first delivery were pre-calibration
defects. None of them would have shown as an anomalous score, so spending the
rollout budget before this chain is green buys nothing. The driver therefore
refuses to report a post-calibration verdict unless the pre-calibration chain
passed.

Exit codes are deliberately distinct:
  0  green   -- every gate ran and passed
  1  blocked -- a gate failed; this is a finding about the bundle
  2  unverified -- a gate errored or was skipped; this is a finding about our
     ability to check the bundle, and it is not the same thing as "fine"
"""

from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path

from .gates import bundle, contract, difficulty, findings, integrity
from .gates.base import FunctionGate
from .gates.base import GateContext, GateResult, Status, run_gates

PRE_CALIBRATION = (
    bundle.structure_gate,
    bundle.ledger_gate,
    findings.completeness_gate,
    findings.enumeration_gate,
    findings.ambiguity_gate,
    findings.normalisation_gate,
    findings.oracle_gate,
    contract.contract_probe_gate,
    findings.step_isolation_gate,
    findings.policy_gate,
    findings.controls_gate,
    integrity.derivation_gate,
    integrity.leak_gate,
    integrity.reference_gate,
    difficulty.trap_faithful_gate,
    difficulty.trap_beatable_gate,
    difficulty.axes_gate,
    difficulty.hack_gate,
)

POST_CALIBRATION = (
    integrity.bands_gate,
    integrity.validity_gate,
)


def _skip_roots(result: GateResult, by_name: dict, seen: set | None = None) -> set[str]:
    """Statuses at the root of a SKIPPED gate's prerequisite chain."""
    seen = set() if seen is None else seen
    roots: set[str] = set()
    for dep in (result.evidence or {}).get("blocked_by", []) or []:
        if dep in seen:
            continue
        seen.add(dep)
        parent = by_name.get(dep)
        if parent is None:
            roots.add("missing")
        elif parent.status is Status.SKIPPED:
            roots |= _skip_roots(parent, by_name, seen)
        else:
            roots.add(parent.status.value if hasattr(parent.status, "value") else str(parent.status))
    return roots or {"unknown"}


def verdict(results: list[GateResult]) -> tuple[str, int]:
    if any(r.status is Status.ERROR for r in results):
        return "unverified", 2
    # A gate skipped only because a prerequisite FAILED is part of that
    # failure: the task is blocked and repairable, not unverifiable (R4 B1 --
    # before v2 one failed trap floor turned the whole chain `unverified`, and
    # an unverified task never gets a repair pass).
    by_name = {r.gate: r for r in results}
    fail_value = Status.FAIL.value if hasattr(Status.FAIL, "value") else str(Status.FAIL)
    for r in results:
        if r.status is Status.SKIPPED and _skip_roots(r, by_name) != {fail_value}:
            return "unverified", 2
    if any(r.status in (Status.FAIL, Status.SKIPPED) for r in results):
        return "blocked", 1
    return "green", 0


def run_bundle(task_dir: Path, repo_root: Path,
               calibration: dict | None = None, legacy: bool = False) -> dict:
    """`legacy` drops requirements introduced after a bundle shipped, so the
    chain can be run as a diagnostic over the existing deliveries. It reports
    what those bundles would fail on today; it does not certify them."""
    gates = list(PRE_CALIBRATION)
    if not legacy:
        from .author.quality import gate as quality_gate
        gates.append(FunctionGate("quality.production", quality_gate, ("bundle.structure",)))
    if legacy:
        gates = [g for g in gates if g.name != "bundle.ledger"]
        gates = [FunctionGate(g.name, g.fn, tuple(
                     d for d in g.requires if d != "bundle.ledger"))
                 if isinstance(g, FunctionGate) else g for g in gates]
    extras: dict = {}
    if calibration is not None:
        gates += list(POST_CALIBRATION)
        extras["calibration"] = calibration
    if legacy:
        extras["legacy"] = True
    ctx = GateContext(task_dir=task_dir, repo_root=repo_root, extras=extras)
    results = run_gates(gates, ctx)
    state, code = verdict(results)
    return {
        "schema": "arena-pipeline/gate-report/1",
        "task": task_dir.name,
        "phase": ("post-calibration" if calibration else "pre-calibration")
                 + (" (legacy diagnostic)" if legacy else ""),
        "verdict": state,
        "exit_code": code,
        "results": [
            {"gate": r.gate, "status": r.status.value,
             "blockers": [asdict(f) for f in r.blockers],
             "warnings": [asdict(f) for f in r.warnings],
             "evidence": r.evidence, "error": r.error,
             "duration_s": round(r.duration_s, 3)}
            for r in results
        ],
    }


def _print(report: dict, verbose: bool) -> None:
    print(f"\n=== {report['task']} [{report['phase']}] ===")
    for r in report["results"]:
        mark = {"pass": "PASS", "fail": "FAIL", "skipped": "SKIP",
                "error": "ERR "}[r["status"]]
        extra = ""
        if r["blockers"]:
            extra = f"  {len(r['blockers'])} blocker(s)"
        elif r["warnings"]:
            extra = f"  {len(r['warnings'])} warning(s)"
        print(f"  {mark}  {r['gate']:28s}{extra}")
        if r["error"]:
            print(f"          ERROR: {r['error']}")
        for f in r["blockers"]:
            where = f" [{f['where']}]" if f["where"] else ""
            print(f"          BLOCKER {f['code']}: {f['message']}{where}")
        if verbose:
            for f in r["warnings"]:
                where = f" [{f['where']}]" if f["where"] else ""
                print(f"          warn    {f['code']}: {f['message']}{where}")
    print(f"  -> {report['verdict'].upper()}")


def main(argv: list[str] | None = None) -> int:
    import argparse
    ap = argparse.ArgumentParser(description="Run the gate chain over task bundles")
    ap.add_argument("tasks", nargs="+", help="task bundle directories")
    ap.add_argument("--calibration", help="calibration report JSON (enables phase 2)")
    ap.add_argument("--json", help="write the full report here")
    ap.add_argument("-v", "--verbose", action="store_true", help="show warnings")
    ap.add_argument("--legacy", action="store_true",
                    help="diagnostic mode for bundles that predate the ledger "
                         "requirement; reports, never certifies")
    args = ap.parse_args(argv)

    calibration = json.loads(Path(args.calibration).read_text()) if args.calibration else None
    repo_root = Path(__file__).resolve().parent.parent

    reports = []
    worst = 0
    for raw in args.tasks:
        task_dir = Path(raw).resolve()
        if not task_dir.is_dir():
            print(f"  ERR  {raw}: not a directory")
            worst = max(worst, 2)
            continue
        report = run_bundle(task_dir, repo_root, calibration, args.legacy)
        reports.append(report)
        _print(report, args.verbose)
        worst = max(worst, report["exit_code"])

    if args.json:
        Path(args.json).write_text(json.dumps(reports, indent=2))
    green = sum(1 for r in reports if r["verdict"] == "green")
    print(f"\n{green}/{len(reports)} green")
    return worst


if __name__ == "__main__":
    raise SystemExit(main())
