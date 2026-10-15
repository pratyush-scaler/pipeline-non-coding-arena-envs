#!/usr/bin/env python3
"""Launch `arena tasks-check` for batch-4 tasks on the pool where their final ran, record the run ids,
and (with --pull) fetch verification/harbor-tasks-check.json back.  Usage:
  taskscheck.py launch <task>...      taskscheck.py status [--pull]"""
from __future__ import annotations
import fcntl, json, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import paths  # noqa: E402
ROOT = paths.ROOT
sys.path.insert(0, str(ROOT))
from pipeline.benchmark import coder_run  # noqa: E402
import measure  # noqa: E402

REC = paths.TASKS_CHECK_RUNS
LOCK = paths.TASKS_CHECK_LOCK


def ws_of(name: str) -> str:
    ws = None
    for e in measure.load()["entries"]:
        if e["name"] == name and e.get("stage") == "final":
            ws = e["ws"]
    if not ws:
        raise SystemExit(f"{name}: no final in ledger")
    return ws


def main() -> int:
    cmd, rest = sys.argv[1], sys.argv[2:]
    if cmd == "launch":
        for t in rest:
            name = Path(t).name
            task = Path(next(e["task"] for e in measure.load()["entries"] if e["name"] == name and e.get("stage") == "final")).resolve()
            ws = ws_of(name)
            measure.push(ws, task)
            rec = coder_run.launch(ws, ["tasks-check", str(task)], env={"ARENA_TASKS_CHECK_TIMEOUT_S": "2400"},
                                   sync=False, staged=False)
            LOCK.parent.mkdir(parents=True, exist_ok=True)
            with open(LOCK, "w") as lk:
                fcntl.flock(lk, fcntl.LOCK_EX)
                d = json.loads(REC.read_text()) if REC.is_file() else {}
                d[name] = {"ws": ws, "run": rec["run"]}
                REC.write_text(json.dumps(d, indent=1))
            print(f"tasks-check {name} on {ws}: {rec['run']}")
    elif cmd == "status":
        d = json.loads(REC.read_text())
        alive = {}
        for ws in sorted({v["ws"] for v in d.values()}):
            alive[ws] = {r["run"]: r for r in coder_run.runs(ws)}
        for name, v in d.items():
            st = alive[v["ws"]].get(v["run"], {})
            running = st.get("state") == "alive" or st.get("alive")
            task = Path(next((e["task"] for e in reversed(measure.load()["entries"]) if e["name"] == name and e.get("stage") == "final"), str(paths.TASKS / name)))
            rcpt = task / "verification/harbor-tasks-check.json"
            if not running and "--pull" in rest and task.is_dir():
                # Pull into a staging folder and install the receipt only if it describes THIS
                # tree's exact content. Pulling verification/ straight into the task restored
                # stale receipts from the pool's older copy into newer trees (2026-10-09).
                import tempfile, shutil
                from pipeline.artifacts import identity
                stage = Path(tempfile.mkdtemp(prefix="tc-pull-"))
                try:
                    coder_run.rsync(v["ws"], f"{task}/verification/", f"{stage}/", push=False, timeout=600)
                    got = stage / "harbor-tasks-check.json"
                    if got.is_file():
                        rec = json.loads(got.read_text())
                        if rec.get("artifact_sha256") == identity(task):
                            (task / "verification").mkdir(exist_ok=True)
                            shutil.copy2(got, rcpt)
                        else:
                            print(f"  {name}: pool receipt is for other content; not installed")
                except Exception as exc:  # noqa: BLE001
                    print(f"  pull failed {name}: {str(exc)[:100]}")
                finally:
                    shutil.rmtree(stage, ignore_errors=True)
            verdict = "-"
            if rcpt.is_file():
                j = json.loads(rcpt.read_text())
                verdict = str(j.get("status") or j.get("verdict") or j.get("ok"))
            print(f"{name:52} {v['ws']:13} {'running' if running else 'ended':8} receipt={verdict}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
