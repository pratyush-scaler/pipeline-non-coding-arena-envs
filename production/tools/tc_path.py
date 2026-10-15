#!/usr/bin/env python3
"""Run `arena tasks-check` on an arbitrary task directory (e.g. an archived ship version under
envs-b6/_versions/) and pull its receipt back only if it describes that tree's exact content (2026-10-14).

  tc_path.py launch <task-dir> <ws>        tc_path.py pull <task-dir> <ws> <run>
Run ids are recorded in production/state/tc_path_runs.json (paths.TC_RUNS)."""
from __future__ import annotations
import json, shutil, sys, tempfile
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import paths  # noqa: E402
ROOT = paths.ROOT
sys.path.insert(0, str(ROOT))
from pipeline.benchmark import coder_run  # noqa: E402
import measure  # noqa: E402

REC = paths.TC_RUNS


def main() -> int:
    cmd, task, ws = sys.argv[1], Path(sys.argv[2]).resolve(), sys.argv[3]
    if not (task / "task.toml").is_file():
        raise SystemExit(f"not a task dir: {task}")
    d = json.loads(REC.read_text()) if REC.is_file() else {}
    if cmd == "launch":
        measure.push(ws, task)
        rec = coder_run.launch(ws, ["tasks-check", str(task)], env={"ARENA_TASKS_CHECK_TIMEOUT_S": "2400"},
                               sync=False, staged=False)
        d[str(task)] = {"ws": ws, "run": rec["run"]}
        REC.parent.mkdir(parents=True, exist_ok=True)
        REC.write_text(json.dumps(d, indent=1))
        print(f"tasks-check {task.name} on {ws}: {rec['run']}")
    elif cmd == "pull":
        from pipeline.artifacts import identity
        stage = Path(tempfile.mkdtemp(prefix="tcp-pull-"))
        try:
            coder_run.rsync(ws, f"{task}/verification/", f"{stage}/", push=False, timeout=600)
            got = stage / "harbor-tasks-check.json"
            if not got.is_file():
                print("no receipt yet"); return 1
            rec = json.loads(got.read_text())
            if rec.get("artifact_sha256") != identity(task):
                print("receipt is for other content; not installed"); return 1
            (task / "verification").mkdir(exist_ok=True)
            shutil.copy2(got, task / "verification/harbor-tasks-check.json")
            print("installed", rec.get("status") or rec.get("verdict") or rec.get("ok"))
        finally:
            shutil.rmtree(stage, ignore_errors=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
