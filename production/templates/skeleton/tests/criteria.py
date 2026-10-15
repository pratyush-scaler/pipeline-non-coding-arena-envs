"""Grading entry point.

Deliberately thin. Every scored decision lives in `checks.json` as data, and one
reviewed evaluator runs them, so this file has nothing task-specific to get
wrong. The nine defects returned on the first delivery were all properties of
hand-written grader code; there is no hand-written grader code here.

Read `checks.json` to review what is scored, and `basis.toml` for the public
wording each check rests on.
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from _arena_runtime.checks_runtime import Workspace, grade, load  # noqa: E402


def main() -> int:
    source = Path(os.environ.get("ARENA_SOURCE", "/app/environment/files"))
    submitted = Path(os.environ.get("ARENA_SUBMITTED", "/app/deliverables"))
    checks = load(HERE / "checks.json")
    # The shipped grader must be handed the projections and the derived rows,
    # or every check whose target reads a `.jsonl` raises inside the container.
    # Measured on this batch: 65 of 84 objectives read a projection, the bundle
    # ships `derived/` and `projections.json` beside this file, and the runtime
    # passed neither -- so scores came from our own harness and the bundle as
    # shipped would fail on its first check. Adopted from the upstream fork.
    # Harbor runs each step with ARENA_STEP set, and `rubric.json` says which
    # checks belong to which step. Without this the grader scored EVERY check
    # on EVERY step: step 1 penalised for work it was not yet asked to do, and
    # step 2 re-credited for step 1's. Single-step bundles are unaffected --
    # An unknown step is an execution error, never a request to grade everything.
    step = os.environ.get("ARENA_STEP", "").strip()
    rubric_file = HERE / "rubric.json"
    rubric = json.loads(rubric_file.read_text())
    if not step and len(rubric) == 1:
        step = next(iter(rubric))
    if step not in rubric:
        raise ValueError("ARENA_STEP must name a declared step")
    wanted = set(rubric[step])
    checks = [c for c in checks if c.id in wanted]

    derived = HERE / "derived"
    projections_file = HERE / "projections.json"
    if any(derived.glob("*.jsonl")) and not projections_file.is_file():
        raise RuntimeError("derived targets require projections metadata")
    projections = (json.loads(projections_file.read_text())["projections"]
                   if projections_file.is_file() else None)
    result = grade(checks, Workspace(
        source=source, submitted=submitted,
        derived=derived, projections=projections, step=step))
    out = Path(os.environ.get("ARENA_REWARD", "/app/reward.json"))
    out.write_text(json.dumps({"reward": float(result["reward"])}))
    # A contract error or a violated guardrail scores the whole step 0. Every report then
    # says so: reward-details lists each criterion at 0 with the reason, and arena-grade.json
    # carries `zeroed_by`, `earned` 0 and the pre-zeroing points as `earned_before_zeroing`.
    zeroed = []
    if result.get("contract_errors"):
        zeroed.append("output contract error: " + str(result["contract_errors"][0]))
    if result.get("guardrails_violated"):
        zeroed.append("guardrail violated: " + ", ".join(result["guardrails_violated"]))
    why = "; ".join(zeroed)
    if zeroed:
        result["zeroed_by"] = why
        result["earned_before_zeroing"] = result.get("earned")
        result["earned"] = 0.0
    details = os.environ.get("ARENA_DETAILS")
    if details:

        def reason(rec):
            own = rec.get("reason", "")
            if not zeroed:
                return own
            alone = "passed" if rec.get("passed") else "failed"
            return f"step scored 0 ({why}); this check alone {alone}" + (f": {own}" if own else "")

        Path(details).write_text(json.dumps({"reward": {"kind": "programmatic",
            "score": result["reward"], "criteria": [
                {"name": cid, "value": 0.0 if zeroed else float(bool(rec.get("passed"))),
                 "status": "evaluated", "gated_out": bool(rec.get("gated_out")),
                 "reason": reason(rec)}
                for cid, rec in result["checks"].items()]}}))
    json.dump(result, sys.stdout, indent=2)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
