#!/usr/bin/env python3
"""Stage I3 -- run each bundle's grader exactly as it ships, in isolation.

Everything else grades through our own harness, which imports the runtime from
the repository. The container does not have the repository: it has `tests/`,
the fixture and the submission. That gap once shipped eleven bundles whose
`criteria.py` raised on its first check, while every gate was green -- the
runtime was never handed `derived/` or `projections.json`, and 65 of 84
objectives read a projection.

So this copies `tests/` to a scratch directory with no repository on the path,
runs `criteria.py` against the reference submission, and asserts the reward it
writes to `reward.json`. Two controls, because one is not enough:

  reference submission -> reward == 1.0   (the grader can be satisfied)
  empty submission     -> reward <  1.0   (it is not just returning 1.0)

A grader that returns 1.0 for an empty directory passes the first check and is
worthless. Run with `./arena verify [tree]`.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
from .config import bundle_paths

ROOT = Path(__file__).resolve().parent.parent


def _run(bundle: Path, submitted: Path, scratch: Path, step: str | None = None) -> tuple[float | None, str]:
    """Execute the shipped grader with no credentials or repository importable."""
    from .evaluate import exported_grade
    import tomllib
    try:
        names = [s["name"] for s in tomllib.loads((bundle / "task.toml").read_text())["steps"]]
        chosen = step or (names[0] if len(names) == 1 else None)
        if chosen is None:
            raise ValueError("multi-step verification requires an explicit step")
        return exported_grade(bundle.resolve(), submitted.resolve(), chosen)["reward"], ""
    except Exception as exc:
        return None, f"{type(exc).__name__}: {exc}"


def run_reference(bundle: Path) -> dict:
    """Execute every step's shipped `solve.py` offline and grade what it writes.

    Probes grade `solution/submission`, a stored file; the container runs
    `steps/<step>/solution/solve.py`. Nothing executed the second, so a bundle
    whose probes said golden 1.0 shipped a solve script that scored 0.1587
    through its own grader. This runs those exact bytes -- from a read-only
    copy, as `/solution` may be mounted -- against a scratch copy of the
    fixture, steps in order into one deliverables directory as the container
    accumulates them, and grades each step with the shipped `tests/criteria.py`.
    No Docker: the container paths are the `ARENA_SOURCE`/`ARENA_SUBMITTED`
    roots the generated script reads, which is how the container maps them.

    Anything short of 1.0 per step, and anything that could not be run, is a
    problem. "Could not execute" is never reported as a pass.
    """
    import stat
    import tomllib
    from .author.solution import SOLVE_SH
    from .evaluate import exported_grade
    bundle = Path(bundle)
    out = {"steps": {}, "problems": []}
    try:
        names = [s["name"] for s in tomllib.loads((bundle / "task.toml").read_text())["steps"]]
    except Exception as exc:
        out["problems"].append(f"reference run: cannot read declared steps: {type(exc).__name__}: {exc}")
        return out
    if not names:
        out["problems"].append("reference run: no declared steps")
        return out
    with tempfile.TemporaryDirectory(prefix="arena-reference-run-") as tmp:
        root = Path(tmp)
        fixture, deliverables, scratch = root / "fixture", root / "deliverables", root / "tmp"
        shutil.copytree(bundle / "environment/files", fixture)
        deliverables.mkdir()
        scratch.mkdir()
        for name in names:
            where = f"steps/{name}/solution"
            source = bundle / where
            solve_sh, solve_py = source / "solve.sh", source / "solve.py"
            if not solve_sh.is_file() or not solve_py.is_file():
                out["problems"].append(f"{where}: no solve.sh/solve.py to execute")
                out["steps"][name] = None
                break
            if solve_sh.read_text(errors="replace") != SOLVE_SH:
                out["problems"].append(
                    f"{where}/solve.sh is not the generated deriving wrapper, so the "
                    "offline reference run cannot execute what the container runs")
                out["steps"][name] = None
                break
            text = solve_py.read_text(errors="replace")
            if "ARENA_SOURCE" not in text or "ARENA_SUBMITTED" not in text:
                out["problems"].append(
                    f"{where}/solve.py hard-codes its container paths and cannot be "
                    "mapped to a scratch fixture; rebuild the bundle")
                out["steps"][name] = None
                break
            copy = root / "solution" / name
            shutil.copytree(source, copy, ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
            for path in [copy, *copy.rglob("*")]:
                mode = path.stat().st_mode
                path.chmod(mode & ~(stat.S_IWUSR | stat.S_IWGRP | stat.S_IWOTH))
            env = {"PATH": os.defpath, "PYTHONDONTWRITEBYTECODE": "1", "PYTHONPATH": "",
                   "HOME": str(scratch), "TMPDIR": str(scratch),
                   "ARENA_SOURCE": str(fixture), "ARENA_SUBMITTED": str(deliverables)}
            try:
                proc = subprocess.run([sys.executable, "-s", str(copy / "solve.py")],
                                      cwd=scratch, env=env, capture_output=True,
                                      text=True, timeout=300)
            except subprocess.TimeoutExpired:
                out["problems"].append(f"{where}/solve.py timed out")
                out["steps"][name] = None
                break
            finally:
                for path in [copy, *copy.rglob("*")]:
                    path.chmod(path.stat().st_mode | stat.S_IWUSR)
            if proc.returncode:
                tail = (proc.stderr.strip().splitlines() or ["no output"])[-1][:300]
                out["problems"].append(f"{where}/solve.py exited {proc.returncode}: {tail}")
                out["steps"][name] = None
                break
            try:
                result = exported_grade(bundle.resolve(), deliverables, name, source=fixture)
            except Exception as exc:
                out["problems"].append(f"{name}: grading the executed reference failed: "
                                       f"{type(exc).__name__}: {str(exc)[:300]}")
                out["steps"][name] = None
                break
            out["steps"][name] = result["reward"]
            if result["reward"] != 1.0:
                failed = sorted(cid for cid, row in result["checks"].items()
                                if not row.get("passed") and not row.get("gated_out"))
                out["problems"].append(
                    f"{name}: the shipped solve.py scores {result['reward']} through the "
                    f"shipped grader, not 1.0 (failing: {', '.join(failed[:5]) or 'contract'})")
    return out


def verify(bundle: Path) -> dict:
    import tomllib
    from .author.contracts import strict_json, contained
    result = {"bundle": bundle.name, "ok": False, "incomplete": False,
              "reference": None, "empty": None, "errors": [], "steps": {}}
    reference = bundle / "solution/submission"
    if not (bundle / "task.toml").is_file():
        result["incomplete"] = True
        result["errors"].append("bundle is incomplete: missing task.toml -- not built yet")
        return result
    if not (bundle / "tests/criteria.py").is_file():
        result["errors"].append("no tests/criteria.py")
        return result
    try:
        names = [s["name"] for s in tomllib.loads((bundle / "task.toml").read_text())["steps"]]
        if not names:
            raise ValueError("no declared steps")
        contract = bundle / "tests/outputs.json"
        outputs = strict_json(contract.read_text())["outputs"] if contract.is_file() else []
        with tempfile.TemporaryDirectory(prefix="arena-shipped-") as tmp:
            root = Path(tmp)
            empty, cumulative = root / "empty", root / "cumulative"
            empty.mkdir()
            cumulative.mkdir()
            for name in names:
                if outputs:
                    for output in outputs:
                        if output["step"] == name:
                            target = contained(cumulative, output["file"])
                            target.parent.mkdir(parents=True, exist_ok=True)
                            shutil.copyfile(contained(reference, output["file"]), target)
                    submitted = cumulative
                else:
                    submitted = reference
                scores = {}
                for label, path, want in (("reference", submitted, 1.0), ("empty", empty, 0.0)):
                    value, error = _run(bundle, path, root / label, name)
                    scores[label] = value
                    if error or value != want:
                        result["errors"].append(f"{name}/{label}: {error or f'scored {value}; expected {want}'}")
                result["steps"][name] = scores
        # The copies must be the current generator's, and identical to each
        # other; then the script the container runs must itself score 1.0.
        from .author import runtime
        result["errors"].extend(runtime.problems(bundle))
        executed = run_reference(bundle)
        result["solve"] = executed["steps"]
        result["errors"].extend(executed["problems"])
        result["reference"] = min(s["reference"] for s in result["steps"].values() if s["reference"] is not None)
        result["empty"] = max(s["empty"] for s in result["steps"].values() if s["empty"] is not None)
    except Exception as exc:
        result["errors"].append(f"{type(exc).__name__}: {exc}")
    result["ok"] = not result["errors"]
    return result


def main(argv: list[str] | None = None) -> int:
    import argparse
    ap = argparse.ArgumentParser(description="Run every bundle's grader as it ships")
    ap.add_argument("root", nargs="?", default=str(ROOT / "envs"))
    ap.add_argument("-o", "--out", default=None)
    ns = ap.parse_args(argv)

    bundles = bundle_paths(Path(ns.root).resolve())
    if not bundles:
        print(f"no bundles under {ns.root}")
        return 2
    results = [verify(b) for b in bundles if b.is_dir()]
    for r in results:
        mark = "SKIP" if r.get("incomplete") else ("ok  " if r["ok"] else "FAIL")
        print(f"  {mark} {r['bundle']:45s} reference={r['reference']} empty={r['empty']} solve={r.get('solve')}")
        for e in r["errors"]:
            print(f"       {e}")
    partial = [r for r in results if r.get("incomplete")]
    checkable = [r for r in results if not r.get("incomplete")]
    bad = [r for r in checkable if not r["ok"]]
    print(f"\n{len(checkable) - len(bad)}/{len(checkable)} shipped graders working"
          + (f"  ({len(partial)} bundle(s) not built yet, not checked)" if partial else ""))
    if ns.out:
        Path(ns.out).write_text(json.dumps(results, indent=2))
    # Incomplete is not a pass. "Could not check" is never green here.
    return 1 if (bad or partial) else 0


if __name__ == "__main__":
    raise SystemExit(main())
