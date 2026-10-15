"""Make environment/tools.json declare the task's real deliverables (Arena 261011 R07/R11; compliance E14, 2026-10-15).

    python3 -I fix_tools_json.py <task-dir> [--check]

workspace.outputs is rebuilt from tests/outputs.json: one {"step", "path": "/app/deliverables/<file>"} per declared
output, in that file's order. Nothing else in tools.json changes. --check only reports (exit 1 on a mismatch).
"""
import json
import sys
from pathlib import Path


def expected(task: Path) -> list[dict]:
    outs = json.loads((task / "tests/outputs.json").read_text())["outputs"]
    return [{"step": o["step"], "path": f"/app/deliverables/{o['file']}"} for o in outs]


def main(argv: list[str]) -> int:
    task, check = Path(argv[0]), "--check" in argv
    path = task / "environment/tools.json"
    doc = json.loads(path.read_text())
    want, have = expected(task), doc.get("workspace", {}).get("outputs")
    if have == want:
        print(f"tools.json OK: {len(want)} output(s) match tests/outputs.json")
        return 0
    if check:
        print(f"tools.json MISMATCH: declares {have} but tests/outputs.json gives {want}")
        return 1
    doc.setdefault("workspace", {})["outputs"] = want
    path.write_text(json.dumps(doc, indent=2, ensure_ascii=False) + "\n")
    print(f"tools.json FIXED: outputs -> {want}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
