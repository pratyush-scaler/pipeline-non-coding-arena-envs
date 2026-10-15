"""Per-step deliverable zips, in the shape Arena receives (2026-10-03).

Reference: a_f2_worldbuilding-design-canon__01-task.zip / __02-revision.zip (Arena batch 32). An
environment with N steps ships N zips. Every zip is the COMPLETE native Harbor task root -- all
steps, tests and solution, unchanged -- at the zip root, plus the calibration of record sliced to
that one step:

    <task>__<step>.zip
      .dockerignore  task.toml  authoring/{spec,traps}.json  environment/  provenance/
      steps/  tests/  solution/  REWARD-HACKING.md
      verification/{controls,delivery,harbor-tasks-check,probes}.json
      CALIBRATION-MANIFEST.json     task "<task>/<step>", session, level, package name,
                                    steps_tests_solution_sha256, task-level metrics per model
      calibration/runs.csv          one row per valid run, scored on THIS step
      calibration/trajectories/<model>/<trial>/
            agent/trajectory.json   artifacts/<deliverables after this step>
            verifier/{arena-grade,reward-details,reward}.json
      README.md                     the task, the task-level and this-step tables, where points
                                    were lost

It reads a DELIVERED task (`arena deliver` output, after `arena deliverable` wrote its
REWARD-HACKING.md): the delivered copy carries its own tasks-check receipt and the
native-calibrations receipt naming the 10x2 campaigns. Nothing is recomputed from summaries --
every figure comes from the campaigns' own trial records, void episodes excluded.

    python -m pipeline.stepzips <delivery root or task dir> [...] -o <zip dir>
"""
from __future__ import annotations

import csv
import hashlib
import io
import json
import math
import sys
import tomllib
import zipfile
from pathlib import Path

#: verification receipts the reference ships; the rest stay in the working tree.
VERIFICATION_FILES = ("controls.json", "delivery.json", "harbor-tasks-check.json", "probes.json")
AUTHORING_FILES = ("spec.json", "traps.json")
SKIP_TOP = {"runs", "calibration", "CALIBRATION-MANIFEST.json", "README.md"}
MODEL_LABELS = {"claude-fable-5-1": "Claude Fable 5.1", "gpt-6-astra": "GPT 6 Astra"}
RUNS_HEADER = ["model", "run", "trial_id", "step_score", "checks_passed", "checks_total", "turns",
               "prompt_tokens", "completion_tokens", "failed_checks"]


def _short(model: str) -> str:
    return model.split("/")[-1]


def package_files(task: Path) -> list[Path]:
    """The task root as shipped: everything but working-tree evidence."""
    out = []
    for path in sorted(task.rglob("*")):
        rel = path.relative_to(task)
        if not path.is_file() or "__pycache__" in rel.parts or rel.parts[0] in SKIP_TOP:
            continue
        if rel.parts[0] == "verification" and (len(rel.parts) != 2 or rel.name not in VERIFICATION_FILES):
            continue
        if rel.parts[0] == "authoring" and (len(rel.parts) != 2 or rel.name not in AUTHORING_FILES):
            continue
        out.append(path)
    return out


def steps_tests_solution_sha256(task: Path) -> str:
    """sha256 of the sorted JSON map relpath -> sha256 over steps/, tests/ and solution/."""
    inventory = {}
    for top in ("steps", "tests", "solution"):
        for path in sorted((task / top).rglob("*")):
            if path.is_file() and "__pycache__" not in path.parts:
                inventory[path.relative_to(task).as_posix()] = hashlib.sha256(path.read_bytes()).hexdigest()
    return hashlib.sha256(json.dumps(inventory, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def _pass_at_k(n: int, c: int, k: int = 4) -> float:
    if n - c < k:
        return 1.0
    return 1.0 - math.comb(n - c, k) / math.comb(n, k)


def calibration_runs(task: Path) -> dict[str, dict]:
    """model -> {"report": campaign report, "trials": [(trial_id, trial_dir, {step: reward})]}, valid only."""
    receipt = json.loads((task / "verification/native-calibrations.json").read_text())
    cited = list(receipt.get("campaigns") or [])
    for value in (receipt.get("topups") or {}).values():
        cited += value if isinstance(value, list) else [value]
    models: dict[str, dict] = {}
    for campaign in dict.fromkeys(cited):
        report = json.loads((Path(campaign) / "report.json").read_text())
        model = _short(report.get("model") or report.get("requested_model") or "unknown")
        cell = models.setdefault(model, {"report": report, "trials": []})
        for trial in report.get("trials") or []:
            if trial.get("valid") is not True:
                continue
            found = sorted(Path(campaign).glob(f"jobs/*/{trial['id']}"))
            if not found:
                raise FileNotFoundError(f"{campaign}: trial {trial['id']} has no directory")
            rewards = {s["name"]: float(s.get("reward") or 0.0) if s.get("valid") else 0.0
                       for s in trial.get("steps") or [] if s.get("name")}
            cell["trials"].append((trial["id"], found[0], rewards))
    return models


def task_metrics(models: dict[str, dict], steps: list[str]) -> dict[str, dict]:
    out = {}
    for model, cell in models.items():
        trials = cell["trials"]
        n = len(trials)
        passes = sum(1 for _, _, r in trials if all(r.get(s, 0.0) >= 1.0 - 1e-9 for s in steps))
        report = cell["report"]
        out[model] = {"episodes_valid": n, "passes": passes, "pass_at_1": passes / n if n else 0.0,
                      "pass_at_4": _pass_at_k(n, passes) if n >= 4 else None,
                      "average_reward": sum(sum(r.get(s, 0.0) for s in steps) / len(steps) for _, _, r in trials) / n if n else 0.0,
                      "effort": report.get("effort"), "resolved_model": report.get("resolved_model") or report.get("model")}
    return out


def _step_row(model: str, run: int, trial_id: str, trial_dir: Path, step: str, reward: float) -> list:
    base = trial_dir / "steps" / step
    grade = json.loads((base / "verifier/arena-grade.json").read_text())
    checks = grade.get("checks") or {}
    trajectory = json.loads((base / "agent/trajectory.json").read_text())
    metrics = trajectory.get("final_metrics") or {}
    failed = [cid for cid, c in checks.items() if not c.get("passed")]
    return [model, run, trial_id, reward, len(checks) - len(failed), len(checks),
            sum(1 for s in trajectory.get("steps") or [] if s.get("source") == "agent"),
            metrics.get("total_prompt_tokens"), metrics.get("total_completion_tokens"), "; ".join(failed)]


def _readme(task: str, step: str, index: int, count: int, level: str, session: str, description: str,
            harness: str, metrics: dict, rows: dict[str, list[list]]) -> str:
    def f2(v):
        return "n/a" if v is None else f"{v:.2f}"

    def f3(v):
        return "n/a" if v is None else f"{v:.3f}"

    lines = [f"# {task}/{step}", "", f"**Environment** {task}  ", f"**Step** {index} of {count}  ",
             f"**Faithfulness level** {level}  ", f"**Source Arena session** {session}", "",
             "## What this task asks", "", description, "", "## Grader", "",
             "Scored by `tests/`, shipped at that same path. The reference solution under `solution/` scores 1.0 on "
             "every step and an untouched workspace scores 0.0, through the shipped grader. Rubrics are deterministic; "
             "no LLM judge. Each step has its own rubric.", "", "## Calibration", "", harness, "",
             "**Task level** (an attempt passes only if every step scores full marks; per-task reward is the mean of its steps):",
             "", "| Model | pass@1 | pass@4 | average reward | passes |", "|---|---|---|---|---|"]
    for model, m in metrics.items():
        lines.append(f"| {MODEL_LABELS.get(model, model)} | {f2(m['pass_at_1'])} | {f3(m['pass_at_4'])} | "
                     f"{f3(m['average_reward'])} | {m['passes']} / {m['episodes_valid']} |")
    lines += ["", f"**This step** ({step}):", "", "| Model | step pass@1 | mean | best | worst | valid runs |",
              "|---|---|---|---|---|---|"]
    for model, model_rows in rows.items():
        scores = [r[3] for r in model_rows]
        lines.append(f"| {MODEL_LABELS.get(model, model)} | {f2(sum(s >= 1.0 - 1e-9 for s in scores) / len(scores))} | "
                     f"{f3(sum(scores) / len(scores))} | {f3(max(scores))} | {f3(min(scores))} | {len(scores)} |")
    lines += ["", "## Where points were lost", ""]
    for model, model_rows in rows.items():
        misses: dict[str, int] = {}
        for r in model_rows:
            for cid in filter(None, r[9].split("; ")):
                misses[cid] = misses.get(cid, 0) + 1
        label = MODEL_LABELS.get(model, model)
        if not misses:
            lines.append(f"- **{label}**: passed every check in all {len(model_rows)} runs.")
        else:
            lost = ", ".join(f"`{cid}` ({n}/{len(model_rows)})" for cid, n in sorted(misses.items(), key=lambda x: -x[1]))
            lines.append(f"- **{label}**: missed {lost}.")
    lines += ["", "## Contents", "",
              "- `calibration/runs.csv`: one row per run for this step.",
              "- `calibration/trajectories/<model>/<trial>/`: `agent/trajectory.json` (prompts, turns, tool calls, model "
              "name), `artifacts/` (the files the model wrote), `verifier/arena-grade.json` (every check with target and "
              "submitted value), `verifier/reward-details.json` (per-rubric rewards), `verifier/reward.json`.",
              "- `REWARD-HACKING.md`: what was tested, found and fixed for this environment.",
              "- `verification/harbor-tasks-check.json`: `harbor tasks-check` receipt for this package, when present.",
              "", "## Running it", "", "A native Harbor task root. Unzip and run:", "", "```",
              f"unzip {task}__{step}.zip -d {task}__{step}",
              f"harbor run --path {task}__{step} -a oracle -k 1 -n 1", "```", ""]
    return "\n".join(lines)


def build(task: Path, out_dir: Path) -> list[Path]:
    """Write one zip per step of the delivered task; returns their paths."""
    task = Path(task).resolve()
    toml = tomllib.loads((task / "task.toml").read_text())
    name = task.name
    steps = sorted(p.name for p in (task / "steps").iterdir() if p.is_dir())
    delivery = json.loads((task / "verification/delivery.json").read_text()) if (task / "verification/delivery.json").is_file() else {}
    level = delivery.get("level") or (name.split("_")[1].upper() if name.startswith("a_f") else "unknown")
    metadata = toml.get("metadata") or {}
    session = metadata.get("source_trace") or ""
    description = (toml.get("task") or {}).get("description", "").split(". ")[0].rstrip(".") + "."
    models = calibration_runs(task)
    order = list(MODEL_LABELS)                     # Fable first, as the reference lists them
    models = dict(sorted(models.items(), key=lambda kv: order.index(kv[0]) if kv[0] in order else len(order)))
    metrics = task_metrics(models, steps)
    reports = [cell["report"] for cell in models.values()]
    harnesses = ", ".join(f"{MODEL_LABELS.get(m, m)} in {(c['report'].get('harness') or {}).get('agent', '?')} "
                          f"{(c['report'].get('harness') or {}).get('version', '')}".rstrip() for m, c in models.items())
    output_tokens = next((r.get("limits", {}).get("max_output_tokens") for r in reports if r.get("limits")), None)
    harness = (f"{harnesses}; {min(m['episodes_valid'] for m in metrics.values())} attempts per model, high reasoning "
               f"effort, no turn or time limits" + (f", {output_tokens // 1000}k output tokens" if output_tokens else "")
               + ". Void episodes (infrastructure loss) are excluded from every figure.")
    manifest_base = {"source_arena_session": session, "faithfulness_level": level,
                     "package_task_name": (toml.get("task") or {}).get("name"),
                     "steps_tests_solution_sha256": steps_tests_solution_sha256(task),
                     "task_level_metrics": metrics,
                     "definitions": {"pass": "every step scores full marks",
                                     "pass_at_4": "unbiased estimator 1 - C(n-c,4)/C(n,4)",
                                     "average_reward": "mean over valid episodes of the mean step reward",
                                     "steps_tests_solution_sha256": "sha256 of the sorted JSON map relpath -> sha256 "
                                                                    "over steps/, tests/ and solution/"}}
    files = package_files(task)
    out_dir.mkdir(parents=True, exist_ok=True)
    written = []
    for index, step in enumerate(steps, 1):
        rows: dict[str, list[list]] = {}
        target = out_dir / f"{name}__{step}.zip"
        with zipfile.ZipFile(target, "w", zipfile.ZIP_DEFLATED) as z:
            for path in files:
                z.write(path, path.relative_to(task).as_posix())
            for model, cell in models.items():
                for run, (trial_id, trial_dir, rewards) in enumerate(cell["trials"], 1):
                    rows.setdefault(model, []).append(_step_row(model, run, trial_id, trial_dir, step, rewards.get(step, 0.0)))
                    base = trial_dir / "steps" / step
                    prefix = f"calibration/trajectories/{model}/{trial_id}"
                    z.write(base / "agent/trajectory.json", f"{prefix}/agent/trajectory.json")
                    for name_ in ("arena-grade.json", "reward-details.json", "reward.json"):
                        z.write(base / "verifier" / name_, f"{prefix}/verifier/{name_}")
                    deliverables = base / "artifacts/app/deliverables"
                    for produced in sorted(deliverables.rglob("*")) if deliverables.is_dir() else []:
                        if produced.is_file():
                            z.write(produced, f"{prefix}/artifacts/{produced.relative_to(deliverables).as_posix()}")
            buffer = io.StringIO()
            writer = csv.writer(buffer, lineterminator="\n")
            writer.writerow(RUNS_HEADER)
            for model_rows in rows.values():
                writer.writerows(model_rows)
            z.writestr("calibration/runs.csv", buffer.getvalue())
            z.writestr("CALIBRATION-MANIFEST.json", json.dumps({"task": f"{name}/{step}", **manifest_base}, indent=2) + "\n")
            z.writestr("README.md", _readme(name, step, index, len(steps), level, session, description, harness, metrics, rows))
        written.append(target)
    return written


REQUIRED = ("task.toml", "tests/checks.json", "tests/criteria.py", "REWARD-HACKING.md", "CALIBRATION-MANIFEST.json",
            "calibration/runs.csv", "README.md", "verification/harbor-tasks-check.json", "authoring/spec.json")


def check_zip(path: Path) -> list[str]:
    """Problems with one step zip; [] = it is shippable as built."""
    import tempfile
    from .artifacts import identity
    from .verify_shipped import verify as verify_shipped
    path = Path(path)
    problems = []
    stem = path.name[:-4]
    if "__" not in stem:
        return [f"{path.name}: not named <task>__<step>.zip"]
    task, step = stem.rsplit("__", 1)
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp) / task
        with zipfile.ZipFile(path) as z:
            bad = z.testzip()
            if bad:
                return [f"{path.name}: corrupt member {bad}"]
            z.extractall(root)
        problems += [f"missing {rel}" for rel in REQUIRED if not (root / rel).is_file()]
        if problems:
            return [f"{path.name}: {p}" for p in problems]
        if not (root / "steps" / step / "instruction.md").is_file():
            problems.append(f"step {step} is not a step of the package")
        manifest = json.loads((root / "CALIBRATION-MANIFEST.json").read_text())
        if manifest.get("task") != f"{task}/{step}":
            problems.append(f"manifest task {manifest.get('task')!r} != {task}/{step}")
        if manifest.get("steps_tests_solution_sha256") != steps_tests_solution_sha256(root):
            problems.append("steps_tests_solution_sha256 does not match the packaged steps/tests/solution")
        rows = list(csv.DictReader((root / "calibration/runs.csv").read_text().splitlines()))
        for model, m in (manifest.get("task_level_metrics") or {}).items():
            mine = [r for r in rows if r["model"] == model]
            if len(mine) != m.get("episodes_valid"):
                problems.append(f"{model}: {len(mine)} runs.csv rows for {m.get('episodes_valid')} valid episodes")
            step_passes = sum(1 for r in mine if float(r["step_score"]) >= 1.0 - 1e-9)
            if m.get("passes", 0) > step_passes:
                problems.append(f"{model}: {m.get('passes')} task passes but only {step_passes} passes of this step")
            if m.get("episodes_valid", 0) < 10:
                problems.append(f"{model}: {m.get('episodes_valid')} valid episodes; the calibration of record is 10")
            for r in mine:
                base = root / "calibration/trajectories" / model / r["trial_id"]
                for rel in ("agent/trajectory.json", "verifier/arena-grade.json", "verifier/reward-details.json", "verifier/reward.json"):
                    if not (base / rel).is_file():
                        problems.append(f"{model}/{r['trial_id']}: missing {rel}")
                if int(r["checks_passed"]) > int(r["checks_total"]):
                    problems.append(f"{model}/{r['trial_id']}: checks_passed exceeds checks_total")
        receipt = json.loads((root / "verification/harbor-tasks-check.json").read_text())
        if receipt.get("status") != "pass":
            problems.append(f"harbor tasks-check receipt status {receipt.get('status')!r}")
        elif receipt.get("artifact_sha256") != identity(root):
            problems.append("harbor tasks-check receipt is bound to another package version")
        shipped = verify_shipped(root)
        if not shipped.get("ok"):
            problems.append("shipped grader: " + "; ".join(map(str, shipped.get("problems") or ["not ok"]))[:300])
    return [f"{path.name}: {p}" for p in problems]


def delivered_tasks(root: Path) -> list[Path]:
    root = Path(root)
    if (root / "task.toml").is_file():
        return [root]
    return sorted(p.parent for p in root.glob("*/a_f*/task.toml"))


def main(argv: list[str] | None = None) -> int:
    import argparse
    ap = argparse.ArgumentParser(description="per-step deliverable zips (Arena batch-32 shape)")
    ap.add_argument("roots", nargs="+", help="a delivery root (F*/a_f*/) or a delivered task directory")
    ap.add_argument("-o", "--out", required=True)
    ap.add_argument("--check-only", action="store_true", help="check the zips already in --out")
    args = ap.parse_args(argv)
    problems = 0
    if args.check_only:
        for z in sorted(Path(args.out).glob("*__*.zip")):
            found = check_zip(z)
            print(f"{z.name}: " + ("OK" if not found else "PROBLEMS\n  " + "\n  ".join(found)))
            problems += bool(found)
        return 1 if problems else 0
    for root in args.roots:
        for task in delivered_tasks(Path(root)):
            missing = [rel for rel in ("verification/native-calibrations.json", "verification/harbor-tasks-check.json",
                                       "REWARD-HACKING.md") if not (task / rel).is_file()]
            if missing:
                print(f"{task.name}: not packaged -- missing {', '.join(missing)}")
                problems += 1
                continue
            for z in build(task, Path(args.out)):
                found = check_zip(z)
                print(f"{z.name}: " + ("OK" if not found else "PROBLEMS\n  " + "\n  ".join(found)))
                problems += bool(found)
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
