"""Grade a deliverable directory with a task's shipped grader (2026-10-13).
    python3.11 -I -B grade_dir.py <task> <dir-holding-deliverable> [step]"""
import json, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
import design_lint as dl
task, sub = Path(sys.argv[1]).resolve(), Path(sys.argv[2]).resolve()
step = sys.argv[3] if len(sys.argv) > 3 else "01-task"
res = dl.grade(task, step, sub)
print("RESULT", json.dumps(res, default=str)[:4000])
