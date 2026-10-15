"""Execute the 261011 central-contract probes against one criteria-format task copy.

    python3.11 -I -B selftest.py <task-copy-dir>

Run it on a `mktemp -d` copy, never on a working tree: it writes deliverables
under the copy. For every step, in order, it derives the reference answer with
the step's own solve.py (deliverables carry over between steps, as in Harbor),
grades it, then grades hostile variants of that step's first declared output:

  reference        must score 1.0
  deep_json        5,000 nested arrays          -> 0, contract error, no crash
  deep_bounded     100 nested arrays (parses)   -> 0, contract error
  fifo_extra       reference + a named pipe     -> 0
  fifo_declared    the declared file is a FIFO  -> 0 within the timeout (no hang)
  dup_number       a unique integer list repeats an entry as N.0 -> 0, "repeated"
  dup_case         a unique text list repeats an entry in other letter case -> 0
                   (contract error: "repeated", or the published pattern)
  trailing_nl      a patterned identifier gains a trailing newline -> 0 ("pattern")
  huge_digits      a 5,000-digit numeric string joins a text list -> 0, no crash
  long_spaces      3,000,000 spaces + "x" join a text list -> 0 within 120 s (no quadratic regex)
  long_digit_run   "1 " x 1,500,000 + "x" joins a text list -> 0 within 120 s

Prints one line per probe and exits 1 if any probe misbehaves.
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import paths  # noqa: E402

PY = paths.PY311


def run_grader(task: Path, sub: Path, step: str, timeout: int = 120) -> dict:
    logs = Path(tempfile.mkdtemp(prefix="grade-", dir=task.parent))
    env = {**os.environ, "ARENA_SOURCE": str(task / "environment/files"), "ARENA_SUBMITTED": str(sub),
           "ARENA_STEP": step, "ARENA_REWARD": str(logs / "reward.json"),
           "ARENA_DETAILS": str(logs / "details.json")}
    try:
        proc = subprocess.run([PY, "-I", "-B", str(task / "tests/criteria.py")], env=env,
                              capture_output=True, text=True, timeout=timeout)
    except subprocess.TimeoutExpired:
        return {"crash": f"grader still running after {timeout}s (hang)"}
    if proc.returncode != 0:
        return {"crash": proc.stderr.strip().splitlines()[-1] if proc.stderr.strip() else f"exit {proc.returncode}"}
    out = json.loads(proc.stdout)
    out["reward_file"] = json.loads((logs / "reward.json").read_text())["reward"]
    return out


def solve(task: Path, sub: Path, step: str) -> None:
    sol = task / "steps" / step / "solution" / "solve.py"
    env = {**os.environ, "ARENA_SOURCE": str(task / "environment/files"), "ARENA_SUBMITTED": str(sub), "ARENA_OUT": str(sub)}
    subprocess.run([PY, "-I", "-B", str(sol)], env=env, check=True, capture_output=True, text=True, cwd=sol.parent)


def arrays(schema: dict, path: list):
    if schema.get("type") == "object":
        for key, sub in schema.get("properties", {}).items():
            yield from arrays(sub, path + [key])
    elif schema.get("type") == "array":
        yield path, schema
        yield from arrays(schema["items"], path + ["[]"])


def dig(doc, path):
    for key in path:
        if key == "[]" or not isinstance(doc, dict):
            return None
        doc = doc.get(key)
    return doc


def main() -> int:
    task = Path(sys.argv[1]).resolve()
    rubric = json.loads((task / "tests/rubric.json").read_text())
    outputs = json.loads((task / "tests/outputs.json").read_text())["outputs"]
    work = Path(tempfile.mkdtemp(prefix="sub-", dir=task.parent))
    base = work / "base"
    base.mkdir()
    bad = 0

    def report(step, name, res, want_zero=True, need=None):
        nonlocal bad
        if "crash" in res:
            ok, line = False, f"CRASH {res['crash']}"
        else:
            r = res["reward"]
            errs = res.get("contract_errors") or []
            ok = (r == 0.0) if want_zero else (r == 1.0)
            if need and not any(n in e for e in errs for n in need):
                ok = False
            line = f"reward {r} contract_errors {errs[:2]}"
        bad += not ok
        print(f"{'ok ' if ok else 'BAD'} {step:12} {name:14} {line}")

    for step in rubric:
        solve(task, base, step)
        report(step, "reference", run_grader(task, base, step), want_zero=False)
        mine = [o for o in outputs if o["step"] == step]
        if not mine:
            continue
        out = mine[0]

        def variant(name):
            dest = work / f"{step}-{name}"
            shutil.copytree(base, dest, symlinks=True)
            return dest

        v = variant("deep")
        (v / out["file"]).write_text("[" * 5000 + "]" * 5000)
        report(step, "deep_json", run_grader(task, v, step), need=["nested deeper"])
        v = variant("deep100")
        (v / out["file"]).write_text("[" * 100 + "]" * 100)
        report(step, "deep_bounded", run_grader(task, v, step), need=["nested deeper"])
        v = variant("fifo_extra")
        os.mkfifo(v / "extra.pipe")
        report(step, "fifo_extra", run_grader(task, v, step), need=["special file"])
        v = variant("fifo_decl")
        (v / out["file"]).unlink()
        os.mkfifo(v / out["file"])
        report(step, "fifo_declared", run_grader(task, v, step, timeout=60), need=["regular file"])

        doc = json.loads((base / out["file"]).read_text())
        did_num = did_case = False
        for path, schema in arrays(out["schema"], []):
            if not schema.get("uniqueItems") or "[]" in path:
                continue
            value = dig(doc, path)
            if not isinstance(value, list) or not value:
                continue
            kind = schema["items"].get("type")
            if kind in ("integer", "number") and not did_num:
                did_num = True
                v = variant("dupnum")
                d = json.loads((v / out["file"]).read_text())
                dig(d, path[:-1]).__setitem__(path[-1], value + [float(value[0])]) if len(path) > 1 else d.__setitem__(path[-1], value + [float(value[0])])
                (v / out["file"]).write_text(json.dumps(d))
                report(step, "dup_number", run_grader(task, v, step), need=["repeated"])
            if kind == "string" and isinstance(value[0], str) and value[0].swapcase() != value[0] and not did_case:
                did_case = True
                v = variant("dupcase")
                d = json.loads((v / out["file"]).read_text())
                twin = value + [value[0].swapcase()]
                dig(d, path[:-1]).__setitem__(path[-1], twin) if len(path) > 1 else d.__setitem__(path[-1], twin)
                (v / out["file"]).write_text(json.dumps(d))
                report(step, "dup_case", run_grader(task, v, step), need=["repeated", "pattern"])
        # A patterned identifier with a trailing newline must fail its published pattern (ECMA-262 `$`).
        did_nl = False
        for path, schema in [(p, s) for p, s in arrays(out["schema"], []) if "[]" not in p] + \
                [([k], s) for k, s in out["schema"].get("properties", {}).items() if s.get("type") == "string"]:
            item = schema["items"] if schema.get("type") == "array" else schema
            if did_nl or item.get("type") != "string" or not str(item.get("pattern", "")).endswith("$"):
                continue
            value = dig(doc, path)
            if schema.get("type") == "array" and isinstance(value, list) and value and isinstance(value[0], str):
                twin = [value[0] + "\n"] + value[1:]
            elif isinstance(value, str):
                twin = value + "\n"
            else:
                continue
            did_nl = True
            v = variant("newline")
            d = json.loads((v / out["file"]).read_text())
            (dig(d, path[:-1]) if len(path) > 1 else d)[path[-1]] = twin
            (v / out["file"]).write_text(json.dumps(d))
            report(step, "trailing_nl", run_grader(task, v, step), need=["pattern"])
        if not did_nl:
            print(f"--  {step:12} trailing_nl    no patterned text value in the reference")
        # Long-input robustness (stage 3): a huge numeric string in a unique text list must not crash,
        # and megabytes of spaces in a text value must grade inside the timeout.
        texts = [(p, s) for p, s in arrays(out["schema"], []) if "[]" not in p and s["items"].get("type") == "string"]
        if texts:
            path, schema = texts[0]
            for name, blob in (("huge_digits", "1" * 5000), ("long_spaces", " " * 3_000_000 + "x"),
                               ("long_digit_run", "1 " * 1_500_000 + "x")):
                v = variant(name)
                d = json.loads((v / out["file"]).read_text())
                cur = dig(d, path) or []
                (dig(d, path[:-1]) if len(path) > 1 else d)[path[-1]] = list(cur) + [blob]
                (v / out["file"]).write_text(json.dumps(d))
                report(step, name, run_grader(task, v, step, timeout=120))
        else:
            print(f"--  {step:12} huge_digits    no text list in the schema")
        if not did_num:
            print(f"--  {step:12} dup_number     no nonempty unique number list in the reference")
        if not did_case:
            print(f"--  {step:12} dup_case       no nonempty unique text list in the reference")
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main())
