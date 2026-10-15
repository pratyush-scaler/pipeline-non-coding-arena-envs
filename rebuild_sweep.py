#!/usr/bin/env python3
"""Rebuild every bundle against the CURRENT generator, and say what changed.

A bundle built before a `pipeline/author/checks.py` change ships a frozen
`_arena_runtime/checks_runtime.py` that no longer matches the generator. The
host then refuses to grade it ("unaudited or stale host evaluator") and
`env.step_isolation` reports "export differs from reviewed spec/generator" --
so the bundle is blocked for a reason that has nothing to do with its content.

Rebuilding is the fix, but it must be reported honestly: a rebuild that raises
is not a rebuild that did nothing, and `SKIPPED` is never green.
"""
from __future__ import annotations
import json, sys, traceback
from pathlib import Path

ROOTS = ("envs-batch32", "envs-rebuilt/F2-scenario", "envs-rebuilt/F3-replay")


def bundles():
    for root in ROOTS:
        for spec in sorted(Path(root).glob("*/authoring/spec.json")):
            if ".prerepair" not in str(spec):
                yield spec.parent.parent


def main():
    from pipeline.author.build import build
    ok = failed = 0
    for bundle in bundles():
        spec_path = bundle / "authoring/spec.json"
        try:
            spec = json.loads(spec_path.read_text())
            result = build(spec, bundle)
            ok += 1
            print(f"ok       {bundle.name[:46]:46s} checks={result.get('checks')} "
                  f"objectives={result.get('objectives')} traps={result.get('traps')}",
                  flush=True)
        except Exception as exc:
            failed += 1
            print(f"FAILED   {bundle.name[:46]:46s} {type(exc).__name__}: {exc}", flush=True)
            traceback.print_exc(file=sys.stdout)
    print(f"\n{ok} rebuilt, {failed} failed", flush=True)
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
