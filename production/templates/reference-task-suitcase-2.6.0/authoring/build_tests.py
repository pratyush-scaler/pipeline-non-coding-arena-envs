"""Regenerates tests/derived, tests/fixture-manifest.json, rubric.json, reward.toml, basis.toml from checks.json."""
import hashlib
import json
import shutil
import sys
from pathlib import Path

T = Path(sys.argv[1]); tests = T / "tests"; fx = T / "environment" / "files"
sys.path.insert(0, str(tests))
from _arena_runtime.oracle import project, write  # noqa: E402

proj = json.loads((tests / "projections.json").read_text())["projections"]
der = tests / "derived"
if der.exists():
    shutil.rmtree(der)
write(project(fx, proj), der)
files = {str(p.relative_to(fx)): hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(fx.rglob("*")) if p.is_file()}
(tests / "fixture-manifest.json").write_text(json.dumps({"files": files}, ensure_ascii=False, indent=2) + "\n")
checks = json.loads((tests / "checks.json").read_text())["checks"]
(tests / "rubric.json").write_text(json.dumps({"01-task": [c["id"] for c in checks]}, indent=2) + "\n")
obj = [c for c in checks if c["kind"] == "objective"]
tot = sum(c["weight"] for c in obj); assert tot == 100
dims = {}
for c in obj:
    dims[c["dimension"]] = dims.get(c["dimension"], 0) + c["weight"]
lines = ["# Scoring, documented exactly as the grader computes it.",
         "# Single step: the reward is earned points / 100 (weighted mean of passed objectives).",
         "# No check is gated: obj_ru_share_pct is graded against the solver's own ru_skus_after and active_skus_after.",
         "# A violated guardrail (g_fixture_intact) or an output-contract error sets the reward to 0.", "",
         "[[reward]]", 'name = "01-task"', 'step = "01-task"', 'aggregation = "weighted_mean"', "points = 100", "task_share = 1.0",
         "weights = { " + ", ".join(f"{k} = {v}" for k, v in sorted(dims.items())) + " }", "", "[shares]"]
for c in obj:
    lines.append(f'"{c["id"]}" = {{ step = "01-task", points = {c["weight"]}, task_share = {c["weight"]/100} }}')
(tests / "reward.toml").write_text("\n".join(lines) + "\n")
b = ["# Public wording each check rests on (instruction field definitions).", ""]
for c in checks:
    b.append(f'[{c["id"]}]'); b.append("basis = " + json.dumps(c["basis"], ensure_ascii=False)); b.append("")
(tests / "basis.toml").write_text("\n".join(b))
print("built", len(files), "fixture files;", len(checks), "checks")
