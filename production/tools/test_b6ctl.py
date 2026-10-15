"""Pool-free tests of every b6ctl subcommand (2026-10-15).

    python3 -I -B test_b6ctl.py [--out DIR] [--tree envs-b6/_versions/<name>-<version>] [--multi <multi-step tree>]
    B6CTL_FULL_TEST=1 python3 -I -m unittest test_b6ctl      (the same suite under unittest; skipped without the flag)

Trees, ledger and keys come from paths.py: to run it against another workspace set ARENA_ROOT (keys.env, pipeline/),
ARENA_TASKS (its envs-b6) and ARENA_LEDGER (its ledger), and point ARENA_STATE at scratch.

Everything is written under one mktemp dir inside DIR (default $CLAUDE_SCRATCH); the source trees are only copied
and are hashed before and after. Any call to measure.py, coder or tc_path.py is blocked in-process, so launch and
rerun-void are exercised only up to argument parsing, the preflight refusal and --dry-run. The real preflight runs
against keys.env and its output is checked to hold only `NAME CODE` lines and no fragment of a key. The workflow
commands `run`, `next` and `prompt audit` and ship's campaign choice run on the real ledger's finished campaigns (so
nothing launches), with their gate reports and records in the scratch dir; test_workflow.py covers the rest.
"""
from __future__ import annotations

import argparse
import contextlib
import io
import json
import os
import re
import shutil
import stat
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

TOOLS = Path(__file__).resolve().parent
sys.path.insert(0, str(TOOLS))
import b6ctl  # noqa: E402
import paths  # noqa: E402

REAL_RUN = subprocess.run
BLOCKED: list[str] = []
RESULTS: list[tuple[str, bool]] = []


def guarded(cmd, *a, **k):
    s = " ".join(map(str, cmd)) if isinstance(cmd, (list, tuple)) else str(cmd)
    if re.search(r"measure\.py|tc_path\.py|(^|[/ ])coder( |$)|(^|[/ ])harbor( |$)", s):
        BLOCKED.append(s)
        raise AssertionError(f"blocked external command: {s}")
    return REAL_RUN(cmd, *a, **k)



def run(argv: list[str]) -> tuple[int, str]:
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        try:
            rc = b6ctl.main(argv)
        except SystemExit as exc:  # argparse errors
            rc = exc.code
    return rc, buf.getvalue()


def ok(name: str, cond: bool, out: str = "") -> None:
    RESULTS.append((name, bool(cond)))
    print(f"{'PASS' if cond else 'FAIL'}  {name}")
    for line in out.strip().splitlines()[-12:] if out and not cond else []:
        print(f"        | {line}")


def show(out: str, n: int = 8) -> None:
    for line in out.strip().splitlines()[:n]:
        print(f"        | {line}")


def tree_hash(root: Path) -> dict:
    return b6ctl._hashes(root)


def copy_tree(src: Path, dest: Path) -> Path:
    shutil.copytree(src, dest, symlinks=True, ignore=shutil.ignore_patterns("__pycache__"))
    return dest


def bump(task: Path, new: str) -> None:
    p = task / "task.toml"
    p.write_text(re.sub(r'(?m)^version = "[^"]+"', f'version = "{new}"', p.read_text(), count=1))


def solve_into(task: Path, step: str, out: Path) -> None:
    env = {**os.environ, "ARENA_SOURCE": str(task / "environment/files"), "ARENA_OUT": str(out),
           "ARENA_SUBMITTED": str(out), "ARENA_MISREAD": ""}
    REAL_RUN([b6ctl.PY, "-I", "-B", str(task / "steps" / step / "solution/solve.py")], env=env, check=True,
             capture_output=True, cwd=out)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=os.environ.get("CLAUDE_SCRATCH"))
    ap.add_argument("--tree", default=str(paths.TASKS / "_versions/a_f1_gst-workbook-answer-key-1.7.0"))
    ap.add_argument("--multi", default=str(paths.TASKS / "_versions/a_f1_coloring-book-retitle-audit-2.3.0"))
    ap.add_argument("--skip-slow", action="store_true", help="skip check (design_lint + selftest) and validate")
    a = ap.parse_args(argv)
    subprocess.run = guarded  # b6ctl and design_lint share this module object; installed for this run only
    if not a.out or not Path(a.out).is_dir():
        raise SystemExit("pass --out DIR (an existing directory) or set CLAUDE_SCRATCH")
    src, multi = Path(a.tree).resolve(), Path(a.multi).resolve()
    root = Path(tempfile.mkdtemp(prefix="test-b6ctl-", dir=Path(a.out).resolve()))
    print(f"scratch: {root}")
    before = {p: tree_hash(p) for p in (src, multi)}
    name, ver = b6ctl.base_name(src), b6ctl.version(src)
    live = copy_tree(src, root / "live" / name)  # a live-shaped copy: no _versions in its path

    # ---- preflight, for real ---------------------------------------------------------------------------------
    rc, out = run(["preflight"])
    lines = out.strip().splitlines()
    shape = all(re.fullmatch(r"(ANTHROPIC_API_KEY|OPENAI_API_KEY) (\d{3}|ERR|missing)", l) for l in lines)
    sys.path.insert(0, str(paths.ROOT))
    from pipeline.credentials import read_key_file
    secrets = [v for k, v in read_key_file(b6ctl.KEYS).items() if v and len(v) >= 12]
    leak = any(v[i:i + 8] in out for v in secrets for i in range(0, len(v) - 7))
    ok("preflight prints exactly one `NAME CODE` line per key", shape and len(lines) == 2, out)
    ok("preflight output holds no 8-char fragment of any keys.env value", not leak)
    ok("preflight exit code is 0 iff every key answered 200",
       (rc == 0) == all(l.endswith(" 200") for l in lines), out)
    show(out)
    real_ok = rc == 0

    # ---- launch / rerun-void: parsing, preflight refusal, dry-run ----------------------------------------------
    bogus = root / "bogus-keys.env"
    bogus.write_text("ANTHROPIC_API_KEY=invalid-b6ctl-preflight-test\nOPENAI_API_KEY=invalid-b6ctl-preflight-test\n")
    bogus.chmod(0o600)
    real_keys, b6ctl.KEYS = b6ctl.KEYS, bogus
    rc, out = run(["launch", str(live), "pilot"])
    ok("launch refuses (exit 3) when a key does not answer 200; measure.py never called",
       rc == 3 and "REFUSED" in out and not BLOCKED, out)
    show(out)
    rc, out = run(["launch", str(live), "final", "arena-calib-2", "--dry-run"])
    ok("launch --dry-run is refused too by a failing preflight", rc == 3 and "DRY-RUN" not in out, out)
    rc, out = run(["launch", str(live), "bogus-stage"])
    ok("launch rejects an unknown stage (argparse exit 2)", rc == 2, out)
    rc, out = run(["launch", str(root / "nope"), "pilot"])
    ok("launch rejects a path without task.toml (exit 2)", rc == 2 and "not a task dir" in out, out)
    rc, out = run(["launch", str(live), "pilot", "arena-calib-2", "--no-preflight", "--dry-run"])
    ok("launch --no-preflight --dry-run builds `measure.py launch <task> --stage pilot --ws arena-calib-2`",
       rc == 0 and f"measure.py launch {live} --stage pilot --ws arena-calib-2" in out and not BLOCKED, out)
    show(out, 3)

    fake = root / "ledger.json"
    fake.write_text(json.dumps({"entries": [
        {"id": "t-pilot", "task": str(live), "name": name, "version": ver, "stage": "pilot", "ws": "arena-calib-x",
         "launched_at": 1, "runs": {"fable": {"state": "done", "full": 1, "valid": 5, "void": 0, "pass_at_1": 0.2},
                                    "astra": {"state": "void-auth"}}},
        {"id": "t-final", "task": str(live), "name": name, "version": ver, "stage": "final", "ws": "arena-calib-x",
         "launched_at": 2, "runs": {"fable": {"state": "running"}, "astra": {"state": "launched"}}}]}))
    real_ledger, b6ctl.LEDGER = b6ctl.LEDGER, fake
    rc, out = run(["rerun-void", str(live), "pilot", "astra"])
    ok("rerun-void refuses (exit 3) on a failing OPENAI_API_KEY and tests only that key",
       rc == 3 and "REFUSED" in out and "ANTHROPIC_API_KEY" not in out and not BLOCKED, out)
    show(out)
    rc, out = run(["rerun-void", str(live), "pilot", "fable", "--no-preflight", "--dry-run"])
    ok("rerun-void with no void-auth run for that model exits 2 before any preflight", rc == 2, out)
    rc, out = run(["rerun-void", str(live), "pilot", "gpt"])
    ok("rerun-void rejects an unknown model (argparse exit 2)", rc == 2, out)
    rc, out = run(["rerun-void", str(live), "pilot", "astra", "--no-preflight", "--dry-run"])
    ok("rerun-void --dry-run builds `measure.py launch <task> --stage pilot --rerun-void astra`",
       rc == 0 and f"measure.py launch {live} --stage pilot --rerun-void astra" in out and not BLOCKED, out)
    show(out, 3)
    b6ctl.KEYS = real_keys

    # ---- wait ------------------------------------------------------------------------------------------------
    rc, out = run(["wait", str(live), "pilot", "--model", "astra", "--every", "1", "--max", "5"])
    ok("wait on a void-auth campaign returns at once with exit 3 and the rerun-void hint",
       rc == 3 and "astra void-auth" in out and "rerun-void" in out and not BLOCKED, out)
    rc, out = run(["wait", str(live), "pilot", "--model", "fable", "--every", "1", "--max", "5"])
    ok("wait --model fable on the same campaign is done (exit 0)", rc == 0 and "fable 1/5" in out, out)
    rc, out = run(["wait", str(live), "final", "--every", "1", "--max", "0"])
    ok("wait on a running campaign stops at --max with exit 124 (no status call when the cap is spent)",
       rc == 124 and "TIMEOUT" in out and not BLOCKED, out)
    b6ctl.LEDGER = real_ledger
    for stage in ("pilot", "final"):
        rc, out = run(["wait", str(src), stage, "--every", "1", "--max", "5"])
        ok(f"wait on the real ledger's finished {name} {ver} {stage} exits 0 with no refresh",
           rc == 0 and f"{name} {ver} {stage}" in out and not BLOCKED, out)
        show(out, 2)
    old = paths.TASKS / "_versions" / f"{name}-1.0.0"
    if old.is_dir():
        rc, out = run(["wait", str(old), "pilot", "--model", "astra", "--every", "1", "--max", "5"])
        ok(f"wait on the real ledger's void-auth {name} 1.0.0 pilot (astra) exits 3; hint names the launched path",
           rc == 3 and "void-auth" in out and f"rerun-void {paths.TASKS}/{name} pilot astra" in out, out)
        show(out, 2)

    # ---- stale receipts (check's quarantine) -----------------------------------------------------------------
    b6ctl.STALE = root / "stale-receipts"
    rec = live / "verification/harbor-tasks-check.json"
    rec_bytes = rec.read_bytes()
    rs = b6ctl.receipts(live)
    ok("a receipt bound to the tree's identity is judged current", [r["verdict"] for r in rs] == ["current"])
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        left = b6ctl.quarantine(live)
    ok("quarantine leaves a current receipt in place", left == 0 and rec.is_file(), buf.getvalue())
    bump(live, "9.9.9")
    rs = b6ctl.receipts(live)
    ok("after a version bump the receipt is stale for both reasons (hash, task field)",
       rs and rs[0]["verdict"] == "stale" and len(rs[0]["why"]) == 2 and rs[0]["old"] == ver, str(rs))
    arch = copy_tree(live, root / "_versions" / f"{name}-9.9.9")
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        left = b6ctl.quarantine(arch)
    ok("an archived (_versions) tree's stale receipt is reported, never moved",
       left == 1 and (arch / "verification/harbor-tasks-check.json").is_file() and "NOT moved" in buf.getvalue(),
       buf.getvalue())
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        left = b6ctl.quarantine(live)
    moved = sorted(b6ctl.STALE.glob(f"{name}-{ver}-*/harbor-tasks-check.json"))
    ok(f"a live tree's stale receipt is MOVED to stale-receipts/{name}-{ver}-<ts>/ byte-identical; verification/ gone",
       left == 0 and len(moved) == 1 and moved[0].read_bytes() == rec_bytes and not (live / "verification").exists(),
       buf.getvalue())
    show(buf.getvalue(), 2)

    if not a.skip_slow:
        # ---- check (quarantine + design_lint + selftest) on a copy carrying a stale receipt -------------------
        chk = copy_tree(src, root / "chk" / name)
        bump(chk, "9.9.8")
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            rc = b6ctl.check(chk)
        out = buf.getvalue()
        ok("check moves the stale receipt, then runs design_lint + selftest (exit 0 on this tree)",
           rc == 0 and "moved to" in out and "SELFTEST:" in out and not (chk / "verification").exists(), out)
        show("\n".join(l for l in out.splitlines() if l.startswith(("RECEIPT", "SELFTEST", "VERDICT", "PASS", "FAIL"))), 6)

        # ---- validate on a copy (the source keeps its current receipt; validate's copy omits verification/) -----
        val = copy_tree(src, root / "val" / src.name)
        rc, out = run(["validate", str(val)])
        ok("validate detects <task> <scratch>, runs py3.11 -I -B on a mktemp copy, exit 0 + summary line",
           rc == 0 and "<task> <scratch>" in out and "exit 0; last:" in out, out)
        show(out, 4)
        (val / "verification").mkdir(exist_ok=True)
        stale = json.loads((val / "verification/harbor-tasks-check.json").read_text())
        stale["task"] = f"{name}-0.0.1"
        (val / "verification/harbor-tasks-check.json").write_text(json.dumps(stale))
        rc, out = run(["validate", str(val)])
        ok("validate fails (exit 1) and names `check` when a stale receipt sits in the tree",
           rc == 1 and "STALE 1" in out and "log kept" in out, out)
        show(out, 4)

    # ---- blind-prep / blind-grade -----------------------------------------------------------------------------
    readers = root / "readers"
    readers.mkdir()
    env_save = os.environ.pop("CLAUDE_SCRATCH", None)
    rc, out = run(["blind-prep", str(src)])
    ok("blind-prep without --out and without CLAUDE_SCRATCH refuses (exit 2)", rc == 2, out)
    if env_save is not None:
        os.environ["CLAUDE_SCRATCH"] = env_save
    rc, out = run(["blind-prep", str(src), "--out", str(readers)])
    ws = Path(re.search(r"WORKSPACE (\S+)", out).group(1)) if "WORKSPACE" in out else None
    files_ro = ws and all(not (p.stat().st_mode & (stat.S_IWUSR | stat.S_IWGRP | stat.S_IWOTH))
                          for p in (ws / "app/environment/files").rglob("*"))
    ok("blind-prep makes a mktemp workspace under --out: read-only files, empty deliverables, instruction.md",
       rc == 0 and ws and ws.parent == readers and files_ro and (ws / "instruction.md").is_file()
       and not any((ws / "app/deliverables").iterdir()) and sorted(p.name for p in ws.iterdir())
       == [".prep.json", "app", "instruction.md", "work"], out)
    ok("the reader prompt names the workspace and instruction.md, and nothing from tests/ or solution/",
       f"WS = {ws}\n" in out and "WS/instruction.md" in out and "solve.py" not in out and "criteria" not in out, out)
    show(out, 12)
    rc, out = run(["blind-grade", str(src), str(ws)])
    ok("blind-grade on an empty workspace reports the step as not present (not graded, not zero)",
       rc == 0 and "not present" in out, out)
    solve_into(src, "01-task", ws / "app/deliverables")
    rc, out = run(["blind-grade", str(src), str(ws)])
    ok("blind-grade of the reference answer: reward 1.0000, failed 0", rc == 0 and "reward 1.0000  failed 0" in out, out)
    show(out, 3)
    deliv = next((ws / "app/deliverables").glob("*.json"))
    data = json.loads(deliv.read_text())

    def nudge(v) -> bool:  # add one to the first integer found: a schema-valid answer with one wrong figure
        if isinstance(v, dict):
            for k, x in v.items():
                if isinstance(x, int) and not isinstance(x, bool):
                    v[k] = x + 1
                    return True
                if nudge(x):
                    return True
        elif isinstance(v, list):
            return any(nudge(x) for x in v)
        return False
    nudge(data)
    deliv.write_text(json.dumps(data, ensure_ascii=False))
    rc, out = run(["blind-grade", str(src), str(ws)])
    ok("blind-grade of a damaged answer: reward < 1 and the failed checks are listed",
       rc == 0 and re.search(r"reward 0\.\d+  failed [1-9]", out), out)
    show(out, 3)

    rc, out = run(["blind-prep", str(multi), "--out", str(readers)])
    mws = Path(re.search(r"WORKSPACE (\S+)", out).group(1)) if "WORKSPACE" in out else None
    msteps = b6ctl._steps(multi)
    ok(f"multi-step blind-prep: one instruction-<step>.md and one prompt per step ({len(msteps)})",
       rc == 0 and mws and all((mws / f"instruction-{s}.md").is_file() for s in msteps)
       and out.count("----- reader prompt for step") == len(msteps), out)
    solve_into(multi, msteps[0], mws / "app/deliverables")
    rc, out = run(["blind-grade", str(multi), str(mws)])
    ok("multi-step blind-grade grades the delivered first step and marks later steps not present",
       rc == 0 and f"{msteps[0]}: reward 1.0000" in out and out.count("not present") == len(msteps) - 1, out)
    show(out, 5)

    # ---- workflow commands on the real ledger and campaigns (finished, so nothing is launched) ------------------
    saved = paths.STATE, paths.GATES  # gate reports, census logs and records go to this run's scratch
    paths.STATE, paths.GATES = root / "state", root / "state/gates"
    picked, probs = b6ctl.final_dirs(src)
    ok(f"final_dirs picks one final per model with 10 valid runs ({name} {ver})",
       not probs and sorted(picked) == ["astra", "fable"], "\n".join(probs))
    bw = paths.TASKS / "_versions/a_f1_brightwater-spec-qa-1.6.0"
    if bw.is_dir():
        picked, probs = b6ctl.final_dirs(bw)
        ok("final_dirs takes the -rerun<ts> astra final that replaced a ledger void (brightwater 1.6.0)",
           not probs and "-final-astra-rerun" in picked.get("astra", Path()).name
           and picked["fable"].name.endswith("-final-fable"), "\n".join(probs))
    rc, out = run(["run", str(src), "final", "--max", "1"])
    ok(f"run on the finished {name} {ver} final resumes (no launch), gates, census, one VERDICT line",
       rc in (0, 1) and "already in the ledger: resuming" in out and len(re.findall(rf"(?m)^VERDICT {name} {ver} final: ",
                                                                                   out)) == 1
       and (paths.GATES / f"{name}-{ver}-final.json").is_file() and not BLOCKED, out)
    show("\n".join(l for l in out.splitlines() if l.startswith(("VERDICT", "STOP", "NEXT"))), 3)
    rc, out = run(["next", str(src)])
    ok("next on the archived tree shows the gate and census just recorded and one STAGE",
       rc == 0 and re.search(r"(?m)^  final checks\s+signal gate \S+; census (clean|DEFECT|ERROR)", out)
       and len(re.findall(r"(?m)^STAGE ", out)) == 1, out)
    rc, out = run(["prompt", "audit", str(src), "--out", str(root)])
    ok("prompt audit fills every placeholder from the real campaigns",
       rc == 0 and not re.search(r"\{(TASK_DIR|TASK|VERSION|REPO|SCRATCH|NOTES|PLAN|AUDIT_REPORT|CAMPAIGNS)\}", out)
       and f"{name}-{ver}-final-fable" in out and f"VERDICT {name} {ver}" in out, out)
    paths.STATE, paths.GATES = saved

    # ---- sources untouched -----------------------------------------------------------------------------------
    ok("source trees byte-identical before and after (nothing written into _versions/)",
       all(tree_hash(p) == h for p, h in before.items()))
    ok("no measure.py / coder / harbor / tc_path command was attempted", not BLOCKED, "\n".join(BLOCKED))
    n_ok = sum(1 for _, c in RESULTS if c)
    print(f"\n{n_ok}/{len(RESULTS)} passed; real preflight {'all 200' if real_ok else 'NOT all 200'}; scratch {root}")
    subprocess.run = REAL_RUN
    return 0 if n_ok == len(RESULTS) else 1


class FullSuite(unittest.TestCase):
    """The script above under unittest; opt-in because it calls the real key preflight and needs the archived trees."""

    @unittest.skipUnless(os.environ.get("B6CTL_FULL_TEST") and os.environ.get("CLAUDE_SCRATCH"),
                         "set B6CTL_FULL_TEST=1 and CLAUDE_SCRATCH to run the pool-free b6ctl suite")
    def test_every_subcommand(self):
        self.assertEqual(main(["--out", os.environ["CLAUDE_SCRATCH"]]), 0)


if __name__ == "__main__":
    raise SystemExit(main())
