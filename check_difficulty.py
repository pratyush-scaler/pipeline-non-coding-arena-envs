#!/usr/bin/env python
"""Will this task measure hard?  Free, static, no model call.

    PYTHONPATH=. .venv/bin/python check_difficulty.py <bundle> [<bundle> ...]

Reports the root check(s) -- the ones carrying a construct that has actually
been observed to fail -- how much of the task's weight falls with each, and what
is missing when there is none. See pipeline/breadth.py for the measurement this
encodes and for what it cannot tell you: it is a one-sided screen, so silence
here is not evidence that a task is hard.
"""
from __future__ import annotations

import sys
from pathlib import Path

from pipeline import breadth


def main(argv: list[str]) -> int:
    if not argv:
        print(__doc__)
        return 2
    worst = 0
    for target in argv:
        bundle = Path(target)
        if not (bundle / "tests" / "checks.json").is_file():
            print(f"{target}: no tests/checks.json")
            worst = 2
            continue
        checks = breadth.load(bundle)
        found = breadth.report(checks, bundle)
        issues = breadth.problems(checks, bundle)

        print(f"\n=== {bundle.name} ===")
        band = found["bands"]
        print(f"  objectives {found['objectives']}  weight {found['weight_total']}")
        print(f"  bands      core {band['counts']['core']} / floor "
              f"{band['counts']['floor']} / stretch {band['counts']['stretch']}"
              f"   room {band['room_total']}"
              f"{'' if band['in_band'] else '   OUT OF BAND'}")
        for size in sorted(found["projection_sizes"].items()):
            print(f"    {size[0]:<24} {size[1]} rows")
        if found["root_checks"]:
            print("  root checks:")
            for root in found["root_checks"]:
                kind = "pairwise" if root["pairwise"] else "counts-itself"
                broad = {True: "broad", False: "TOO NARROW", None: "unmeasured"}[root["broad_enough"]]
                print(f"    {root['id']:<28} {kind:<14} {broad:<11} "
                      f"items={root['items']} (floor {root['items_floor']})  "
                      f"{root['share_at_risk']:.0%} of weight at risk")
                if root["cascade"]:
                    print(f"      cascade: {', '.join(root['cascade'])}")
        else:
            print("  root checks: NONE")
        for issue in issues:
            print(f"  ! {issue}")
            worst = max(worst, 1)
    return worst


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
