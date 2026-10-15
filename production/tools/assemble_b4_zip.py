"""(batch-4 copy: spec.json optional when the task has none) Deliverable zips for the hand-fixed envs-fb tasks, from this checkout's benchmark campaigns (2026-10-08).

The three tasks under envs-fb/ were first delivered by another author's pipeline
(~/Downloads/arena-batch2-stepwise-deliverables-20261003/a_f1_*.zip). They were then fixed and are
re-calibrated here with

    ./arena benchmark envs-fb/<task> --coder --agent harness -m <model> -r N --effort high \
        --legacy-diagnostic -o pipeline-artifacts/fb/<task>-<fable|astra>-<pilot|final>

Usage (run from anywhere; nothing under pipeline/ is written, imports are read-only):

    python research/batch3/assemble_fb_zip.py envs-fb/<task> \
        --fable pipeline-artifacts/fb/<task>-fable-final --astra pipeline-artifacts/fb/<task>-astra-final \
        -o <zip dir> [--shape stepzip|a_f1] [--oracle <dir> --nop <dir>] [--compare-to <reference.zip>]

    python research/batch3/assemble_fb_zip.py --compare <produced.zip> <reference.zip>   # structure diff only

--fable / --astra take one benchmark output directory each and may be repeated for top-up campaigns
of the same version (top-ups replace voids; never mix a pilot with the final campaign).

Shapes
------
stepzip (default): one <task>__<step>.zip per step, the batch-32 / v2 shape `pipeline/stepzips.py`
    writes (reference: a_f2_worldbuilding-design-canon__01-task.zip and the v2 zips of the 10-03 batch).
    The whole task root sits at the zip root, all steps included, plus that step's slice of the
    calibration: CALIBRATION-MANIFEST.json (task "<task>/<step>"), calibration/runs.csv,
    calibration/trajectories/<model>/<trial>/{agent/trajectory.json, artifacts/, verifier/...}, README.md.
    Field sets are the reference's, extended (never renamed) with the legacy-diagnostic mode, void counts,
    per-step pass rates, harness and campaign binding.
a_f1: the shape these three tasks were first delivered in: ONE zip with a top-level <task>/ folder holding
    the task root, every benchmark output directory verbatim under verification/campaigns/calibration-<model>/,
    and verification/native-calibrations.json naming them. A multi-step task is one zip named
    <task>__<first step>_multi_task.zip. The other pipeline's qualification/release/state/frozen-package
    receipts and its oracle/nop controls are not regenerated (pass --oracle/--nop benchmark directories to
    ship controls).

What is checked before anything is written (a problem refuses the build):
  - every campaign finished with no runner errors and ran the requested model;
  - every campaign ran THIS task version: its source-build.json file list equals the task root's frozen
    surfaces (pipeline.artifacts.ROOTS) and report.json task_validation.artifact_sha256 equals
    pipeline.artifacts.identity(task) (--allow-stale downgrades this to a warning and says so in README);
  - each valid trial has a directory and every step's trajectory and verifier output;
  - the per-check pass/fail read from the grade agrees with report.json's checks, and verifier/reward.json
    agrees with report.json's step reward;
  - no planted symlink is followed and no credential-shaped string is shipped.
Every written zip is re-opened and checked: required members, manifest task field, steps/tests/solution
hash recomputed from the zip, runs.csv rows = valid episodes per model, a trajectory slice per row, the
task root byte-identical, nothing excluded leaking in, and doc references to verification/ or authoring/
files resolving inside the zip. A zip that fails is left as <name>.zip.invalid, never as <name>.zip.

FIXES.md ships with the task root (2026-10-08: the task docs cite it; it is outside the identity ROOTS),
__pycache__/*.pyc, .DS_Store, verification/campaigns/ and verification/native-calibrations.json (the
calibration comes only from the campaign directories given), and old controls when new ones are given.
Everything else in the task root ships (authoring/tools/ and verification/ evidence are cited by these tasks'
docs); --pipeline-filter instead selects exactly what pipeline.stepzips.package_files ships.

Reading the campaigns: a check counts as passed only when its value is 1.0 and report.json does not mark it
skipped or errored; a step that scored 0 is listed with the grader's own reason (e.g. a missing deliverable) in
the README and in CALIBRATION-MANIFEST step_pass_rates[step].zero_score_runs, so no zero reaches a table
unexplained. Verified 2026-10-08: re-assembling each delivered a_f1 zip from its own contents reproduces it
member-for-member (names, bytes, modes) except the two regenerated receipts; with --pipeline-filter the stepzip
output for a current-pipeline task equals pipeline.stepzips.build's (calibration members byte-identical).
"""
from __future__ import annotations

import sys

sys.dont_write_bytecode = True  # the pipeline imports below must not write pipeline/__pycache__

import argparse  # noqa: E402
import csv  # noqa: E402
import hashlib  # noqa: E402
import io  # noqa: E402
import json  # noqa: E402
import re  # noqa: E402
import tempfile  # noqa: E402
import tomllib  # noqa: E402
import zipfile  # noqa: E402
from pathlib import Path  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parent))
import paths  # noqa: E402

WORKSPACE = paths.ROOT
sys.path.insert(0, str(WORKSPACE))
# Read-only reuse of the pipeline's own stepzip format and identity helpers.
from pipeline.artifacts import identity, inventory  # noqa: E402
from pipeline.stepzips import (MODEL_LABELS, RUNS_HEADER, package_files,  # noqa: E402
                               steps_tests_solution_sha256, task_metrics)

EPS = 1e-9
EXPECTED_MODEL = {"fable": "anthropic/claude-fable-5-1", "astra": "openai/gpt-6-astra"}
VERIFIER_FILES = ("arena-grade.json", "grade-output.json", "reward-details.json", "reward.json")
STEPZIP_GENERATED = ("CALIBRATION-MANIFEST.json", "README.md", "calibration")
SECRET = re.compile(rb"sk-ant-[A-Za-z0-9_\-]{20,}|sk-proj-[A-Za-z0-9_\-]{20,}|\bsk-[A-Za-z0-9]{40,}"
                    rb"|(?:ANTHROPIC_API_KEY|ANTHROPIC_AUTH_TOKEN|OPENAI_API_KEY|CODEX_API_KEY|CLAUDE_CODE_OAUTH_TOKEN)"
                    rb"[\"']?\s*[=:]\s*[\"']?(?!\$\{)[A-Za-z0-9_\-\.]{20,}")
DOC_REF = re.compile(r"(?<![\w/.-])((?:verification|authoring)/[A-Za-z0-9_.\-/]*[A-Za-z0-9_\-])")



def _grader_desc(task: Path) -> str:
    """Name the grader files this package actually ships (never assume grade.py)."""
    t = task / "tests"
    if (t / "grade.py").is_file():
        return "`tests/grade.py` with `tests/checks.json`" if (t / "checks.json").is_file() else "`tests/grade.py`"
    if (t / "criteria.py").is_file():
        return "`tests/criteria.py` evaluating the `tests/checks.json` rules"
    return "the scripts under `tests/`"


def _channel_desc(task: Path) -> str:
    """Mention a live message channel only when the package has one."""
    return " and its scripted message channel (`environment/client/`)" if (task / "environment/client").is_dir() else ""


def _frozen_present(task: Path) -> list:
    """The frozen identity roots that exist in this package (pipeline.artifacts.ROOTS order)."""
    roots = ("task.toml", "steps/", "environment/", "tests/", "solution/", "provenance/",
             "authoring/spec.json", "authoring/traps.json", ".dockerignore")
    return [r for r in roots if (task / r.rstrip("/")).exists()]

def _short(model: str) -> str:
    return (model or "unknown").split("/")[-1]


def _label(short: str) -> str:
    return MODEL_LABELS.get(short, short)


def _json(path: Path):
    return json.loads(Path(path).read_text())


def _sha(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


# --------------------------------------------------------------------------- task root
def task_files(task: Path, shape: str, controls_given: bool, pipeline_filter: bool = False) -> list[Path]:
    """The task root as shipped (see module docstring for what is left out). With pipeline_filter, exactly
    pipeline.stepzips.package_files (authoring/ only spec+traps, verification/ only its four receipts)."""
    allowed = set(package_files(task)) if pipeline_filter else None
    out = []
    for path in sorted(task.rglob("*")):
        rel = path.relative_to(task)
        posix = rel.as_posix()
        if "__pycache__" in rel.parts or path.suffix in (".pyc", ".pyo") or path.name == ".DS_Store":
            continue
        if path.is_symlink():
            raise ValueError(f"symlink in the task root: {posix}")
        if not path.is_file() or (allowed is not None and path not in allowed and posix != "FIXES.md"):
            continue
        if shape == "stepzip" and rel.parts[0] in STEPZIP_GENERATED:
            continue
        if rel.parts[:2] == ("verification", "campaigns") or posix == "verification/native-calibrations.json":
            continue
        if controls_given and (rel.parts[:2] == ("verification", "controls")
                               or posix in ("verification/controls.json", "verification/native-controls.json")):
            continue
        out.append(path)
    return out


def changes_lines(task: Path, override: Path | None, version: str, bound: bool) -> list[str]:
    if override:
        return override.read_text().rstrip().splitlines()
    fixes = task / "FIXES.md"
    if not fixes.is_file():
        return []
    findings = [line[3:].strip() for line in fixes.read_text().splitlines() if re.match(r"## NC-\d+", line)]
    if not findings:
        return []
    return ([f"Package version {version}. Arena review findings on the first delivery that this version addresses:", ""]
            + [f"- {f}" for f in findings]
            + ["", "`REWARD-HACKING.md` and `solution/README.md` describe the fixed version."
               + (" Every calibration figure above was measured on this version." if bound else "")])


# --------------------------------------------------------------------------- campaigns
def campaign_binding(task: Path, cdir: Path, report: dict) -> dict:
    mine = inventory(task)
    source = cdir / "source-build.json"
    theirs = {e["path"]: e["sha256"] for e in (_json(source).get("files") or [])} if source.is_file() else None
    claimed = (report.get("task_validation") or {}).get("artifact_sha256")
    out = {"artifact_sha256": claimed, "artifact_sha256_matches_task": claimed == identity(task)}
    if theirs is None:
        out.update(bound=False, detail="campaign has no source-build.json")
        return out
    changed = sorted(p for p in mine.keys() & theirs.keys() if mine[p] != theirs[p])
    added, removed = sorted(mine.keys() - theirs.keys()), sorted(theirs.keys() - mine.keys())
    out.update(bound=not (changed or added or removed) and out["artifact_sha256_matches_task"],
               changed=changed, added_since=added, removed_since=removed)
    return out


def harness_facts(cdir: Path, report: dict) -> dict:
    harness = report.get("harness") or {}
    agent = harness.get("agent") or report.get("agent") or "?"
    job = _json(cdir / "harbor-job.json") if (cdir / "harbor-job.json").is_file() else {}
    settings = (job.get("agents") or [{}])[0]
    kwargs = settings.get("kwargs") or {}
    web = []
    if kwargs.get("disallowed_tools"):
        web.append(f"disallowed_tools={kwargs['disallowed_tools']}")
    if kwargs.get("web_search"):
        web.append(f"web_search={kwargs['web_search']}")
    limits = report.get("limits") or {}
    cap = (limits.get("max_output_tokens") or (kwargs.get("config") or {}).get("model_max_output_tokens")
           or (settings.get("env") or {}).get("CLAUDE_CODE_MAX_OUTPUT_TOKENS"))
    return {"agent": agent, "version": harness.get("version") or (kwargs.get("pinned") or {}).get("version") or "",
            "effort": report.get("effort"), "no_limits": limits.get("no_limits"),
            "campaign_timeout_sec": limits.get("campaign_timeout_sec"),
            "max_output_tokens": int(cap) if cap else None,
            "web_tools": ", ".join(web) if web else "no web-tool restriction passed to the harness",
            "egress_allowlist": settings.get("extra_allowed_hosts") or []}


def grade_checks(verifier: Path) -> tuple[dict[str, bool], dict[str, str], str]:
    """(check id -> passed, check id -> grader's reason, file) from the step's grade: arena-grade.json, else the
    legacy grade-output.json."""
    if (verifier / "arena-grade.json").is_file():
        checks = _json(verifier / "arena-grade.json").get("checks") or {}
        return ({cid: bool(c.get("passed")) for cid, c in checks.items()},
                {cid: str(c.get("reason") or "") for cid, c in checks.items()}, "arena-grade.json")
    if (verifier / "grade-output.json").is_file():
        out, reasons = {}, {}
        for cid, value in (_json(verifier / "grade-output.json").get("checks") or {}).items():
            reason = ""
            if isinstance(value, list):
                value, reason = value[0], (value[1] if len(value) > 1 else "")
            elif isinstance(value, dict):
                reason = value.get("reason") or ""
                value = value.get("passed", value.get("value"))
            out[cid] = float(value) >= 1.0 - EPS if not isinstance(value, bool) else value
            reasons[cid] = str(reason)
        return out, reasons, "grade-output.json"
    raise FileNotFoundError(f"{verifier}: no arena-grade.json or grade-output.json")


def load_campaign(task: Path, cdir: Path, role: str, steps: list[str], allow_stale: bool,
                  problems: list[str], warnings: list[str]) -> dict | None:
    cdir = cdir.resolve()
    where = f"{role} {cdir.name}"
    if not (cdir / "report.json").is_file():
        problems.append(f"{where}: no report.json (not a finished benchmark output directory)")
        return None
    report = _json(cdir / "report.json")
    model = report.get("model") or report.get("requested_model") or ""
    if role in EXPECTED_MODEL and model != EXPECTED_MODEL[role]:
        problems.append(f"{where}: ran {model!r}, expected {EXPECTED_MODEL[role]!r}")
    if report.get("status") != "finished":
        problems.append(f"{where}: status {report.get('status')!r}, not 'finished'")
    if report.get("errors"):
        problems.append(f"{where}: runner errors: " + "; ".join(map(str, report["errors"]))[:400])
    if list(report.get("step_names") or []) != steps:
        problems.append(f"{where}: steps {report.get('step_names')} != task steps {steps}")
    binding = campaign_binding(task, cdir, report)
    if not binding["bound"]:
        detail = binding.get("detail") or (f"changed {binding['changed'][:6]}, added {binding['added_since'][:6]}, "
                                           f"removed {binding['removed_since'][:6]}, artifact_sha256 match "
                                           f"{binding['artifact_sha256_matches_task']}")
        (warnings if allow_stale else problems).append(f"{where}: ran a different version of the task ({detail})")
    trials, voids = [], []
    for trial in report.get("trials") or []:
        tid = trial.get("id")
        if trial.get("valid") is not True:
            voids.append({"trial_id": tid, "zero_class": trial.get("zero_class"),
                          "errors": [str(e)[:200] for e in (trial.get("errors") or [])][:3]})
            continue
        found = sorted(cdir.glob(f"jobs/*/{tid}"))
        if not found:
            problems.append(f"{where}: valid trial {tid} has no directory")
            continue
        rewards, report_checks = {}, {}
        for s in trial.get("steps") or []:
            name = s.get("name")
            if not s.get("valid"):
                warnings.append(f"{where}: valid trial {tid} has an invalid step {name}; scored 0 as stepzips does")
            rewards[name] = float(s.get("reward") or 0.0) if s.get("valid") else 0.0
            report_checks[name] = {k.split("/", 1)[-1]: v for k, v in (s.get("checks") or {}).items()}
        rows = {}
        for step in steps:
            base = found[0] / "steps" / step
            needed = ("agent/trajectory.json", "verifier/reward.json") if role in EXPECTED_MODEL else ("verifier/reward.json",)
            missing = [rel for rel in needed if not (base / rel).is_file()]
            if missing:
                problems.append(f"{where}: {tid}/{step} missing {', '.join(missing)}")
                continue
            try:
                passed, reasons, source = grade_checks(base / "verifier")
            except (FileNotFoundError, ValueError, TypeError) as exc:
                problems.append(f"{where}: {tid}/{step}: {exc}")
                continue
            listed = report_checks.get(step, {})
            for cid, entry in listed.items():  # SKIPPED and ERROR are never green
                if cid in passed and (entry.get("skipped") or entry.get("error")
                                      or entry.get("status") not in (None, "evaluated")):
                    if passed[cid]:
                        warnings.append(f"{where}: {tid}/{step}: {cid} is {entry.get('status')!r} "
                                        f"(skipped={entry.get('skipped')}, error={entry.get('error')}); counted as failed")
                    passed[cid] = False
            # A step zeroed by a contract error or a violated guardrail reports every criterion at 0
            # (tests/criteria.py since 2026-10-09; arena-grade.json carries zeroed_by and the per-check truth).
            grade_doc = _json(base / "verifier/arena-grade.json") if (base / "verifier/arena-grade.json").is_file() else {}
            zeroed = bool(grade_doc.get("zeroed_by"))
            disagree = [cid for cid, ok in passed.items() if cid in listed and not (listed[cid].get("skipped")
                        or listed[cid].get("error") or listed[cid].get("status") not in (None, "evaluated"))
                        and (float(listed[cid].get("value") or 0.0) >= 1.0 - EPS) != (ok and not zeroed)]
            unknown = [cid for cid in passed if cid not in report_checks.get(step, {})]
            if disagree or (unknown and report_checks.get(step)):
                problems.append(f"{where}: {tid}/{step}: grade and report.json disagree on {disagree[:5]}"
                                f"{' / report lacks ' + str(unknown[:5]) if unknown else ''}")
            verifier_reward = float(_json(base / "verifier/reward.json").get("reward") or 0.0)
            if step in rewards and abs(verifier_reward - rewards[step]) > 1e-6:
                problems.append(f"{where}: {tid}/{step}: verifier reward {verifier_reward} != report {rewards[step]}")
            trajectory = _json(base / "agent/trajectory.json") if (base / "agent/trajectory.json").is_file() else {}
            metrics = trajectory.get("final_metrics") or {}
            failed = [cid for cid, ok in passed.items() if not ok]
            rows[step] = {"reward": rewards.get(step, 0.0), "passed": len(passed) - len(failed), "total": len(passed),
                          "turns": sum(1 for s in trajectory.get("steps") or [] if s.get("source") == "agent"),
                          "prompt_tokens": metrics.get("total_prompt_tokens"),
                          "completion_tokens": metrics.get("total_completion_tokens"),
                          "failed": failed, "grade_file": source, "base": base,
                          "zero_reason": (max({reasons.get(c, "") for c in failed},
                                              key=lambda x: sum(reasons.get(c, "") == x for c in failed))
                                          if failed and rewards.get(step, 0.0) <= EPS else None)}
        trials.append((tid, found[0], rewards, rows))
    summary = report.get("summary") or {}
    return {"dir": cdir, "role": role, "report": report, "model": model, "short": _short(model),
            "trials": trials, "voids": voids, "binding": binding, "harness": harness_facts(cdir, report),
            "requested": summary.get("requested"), "recorded": len(report.get("trials") or [])}


def merge_models(campaigns: list[dict], problems: list[str]) -> dict[str, dict]:
    models: dict[str, dict] = {}
    for c in campaigns:
        cell = models.setdefault(c["short"], {"report": c["report"], "trials": [], "rows": {}, "campaigns": []})
        cell["campaigns"].append(c)
        for tid, tdir, rewards, rows in c["trials"]:
            if tid in cell["rows"]:
                problems.append(f"{c['short']}: trial id {tid} appears in two campaigns")
            cell["trials"].append((tid, tdir, rewards))
            cell["rows"][tid] = rows
    order = list(MODEL_LABELS)
    return dict(sorted(models.items(), key=lambda kv: order.index(kv[0]) if kv[0] in order else len(order)))


def full_metrics(models: dict[str, dict], steps: list[str]) -> dict[str, dict]:
    base = task_metrics({m: {"report": c["report"], "trials": c["trials"]} for m, c in models.items()}, steps)
    for model, cell in models.items():
        n = len(cell["trials"])
        per_step = {}
        for step in steps:
            scores = [r.get(step, 0.0) for _, _, r in cell["trials"]]
            full = sum(1 for s in scores if s >= 1.0 - EPS)
            zeros = [{"trial_id": tid, "grader_reason": cell["rows"][tid][step]["zero_reason"]}
                     for tid, _, r in cell["trials"] if r.get(step, 0.0) <= EPS]
            per_step[step] = {"passes": full, "episodes_valid": n, "pass_rate": full / n if n else None,
                              "mean_reward": sum(scores) / n if n else None, "zero_score_runs": zeros}
        h = cell["campaigns"][0]["harness"]
        base[model].update({
            "episodes_requested": sum(c["requested"] or 0 for c in cell["campaigns"]),
            "episodes_recorded": sum(c["recorded"] for c in cell["campaigns"]),
            "episodes_void": sum(len(c["voids"]) for c in cell["campaigns"]),
            "void_trials": [v for c in cell["campaigns"] for v in c["voids"]],
            "harness": f"{h['agent']} {h['version']}".strip(), "no_limits": h["no_limits"],
            "max_output_tokens": h["max_output_tokens"], "web_tools": h["web_tools"],
            "egress_allowlist": h["egress_allowlist"], "step_pass_rates": per_step})
    return base


def control_result(c: dict, steps: list[str], want: float) -> dict:
    trials = c["trials"]
    first = trials[0][2] if trials else {}
    rewards = [[s, first.get(s)] for s in steps]
    ok = bool(trials) and all(abs(t[2].get(s, -1.0) - want) <= EPS for t in trials for s in steps)
    return {"ok": ok, "steps": rewards, "trials_valid": len(trials), "voids": len(c["voids"]),
            "bound_to_this_package": c["binding"]["bound"]}


# --------------------------------------------------------------------------- README
def readme(ctx: dict, step: str, index: int, rows: dict[str, list[list]]) -> str:
    def f2(v):
        return "n/a" if v is None else f"{v:.2f}"

    def f3(v):
        return "n/a" if v is None else f"{v:.3f}"

    task, metrics, steps = ctx["name"], ctx["metrics"], ctx["steps"]
    lines = [f"# {task}/{step}", "", f"**Environment** {task}  ", f"**Step** {index} of {len(steps)}  ",
             f"**Faithfulness level** {ctx['level']}  ", f"**Source Arena session** {ctx['session']}", "",
             "## What this task asks", "", ctx["description"], "", "## Grader", "", ctx["grader"], "",
             "## Calibration", "", ctx["harness_line"], ""]
    lines += ctx["mode_lines"]
    lines += ["**Task level** (an attempt passes only if every step scores full marks; per-task reward is the mean of its steps):",
              "", "| Model | pass@1 | pass@4 | average reward | passes |", "|---|---|---|---|---|"]
    for model, m in metrics.items():
        lines.append(f"| {_label(model)} | {f2(m['pass_at_1'])} | {f3(m['pass_at_4'])} | "
                     f"{f3(m['average_reward'])} | {m['passes']} / {m['episodes_valid']} |")
    lines += ["", "Void episodes (infrastructure loss, excluded from every figure): " + "; ".join(
        f"{_label(m)} {v['episodes_void']} of {v['episodes_recorded']} recorded"
        + (f" ({', '.join(str(t['zero_class'] or 'void') for t in v['void_trials'])})" if v["void_trials"] else "")
        for m, v in metrics.items()) + "."]
    if len(steps) > 1:
        lines += ["", "**Every step** (valid episodes only):", "",
                  "| Model | step | step pass@1 | mean | passes |", "|---|---|---|---|---|"]
        for model, m in metrics.items():
            for s in steps:
                p = m["step_pass_rates"][s]
                lines.append(f"| {_label(model)} | {s} | {f2(p['pass_rate'])} | {f3(p['mean_reward'])} | "
                             f"{p['passes']} / {p['episodes_valid']} |")
    lines += ["", f"**This step** ({step}):", "", "| Model | step pass@1 | mean | best | worst | valid runs |",
              "|---|---|---|---|---|---|"]
    for model, model_rows in rows.items():
        scores = [r[3] for r in model_rows]
        lines.append(f"| {_label(model)} | {f2(sum(s >= 1.0 - EPS for s in scores) / len(scores))} | "
                     f"{f3(sum(scores) / len(scores))} | {f3(max(scores))} | {f3(min(scores))} | {len(scores)} |")
    lines += ["", "## Where points were lost", ""]
    for model, model_rows in rows.items():
        misses: dict[str, int] = {}
        for r in model_rows:
            for cid in filter(None, r[9].split("; ")):
                misses[cid] = misses.get(cid, 0) + 1
        if not misses:
            lines.append(f"- **{_label(model)}**: passed every check in all {len(model_rows)} runs.")
        else:
            lost = ", ".join(f"`{cid}` ({n}/{len(model_rows)})" for cid, n in sorted(misses.items(), key=lambda x: -x[1]))
            lines.append(f"- **{_label(model)}**: missed {lost}.")
        zeros = metrics[model]["step_pass_rates"][step]["zero_score_runs"]
        if zeros:
            why: dict[str, int] = {}
            for z in zeros:
                why[z["grader_reason"] or "no reason recorded"] = why.get(z["grader_reason"] or "no reason recorded", 0) + 1
            lines.append(f"  - {len(zeros)} of {len(model_rows)} runs scored 0 on this step; the grader's reason: "
                         + "; ".join(f'"{r}" ({k})' for r, k in sorted(why.items(), key=lambda x: -x[1])) + ".")
    if ctx["changes"]:
        lines += ["", "## Changes since the first delivery", ""] + ctx["changes"]
    grade_names = sorted({r["grade_file"] for cell in ctx["models"].values() for rr in cell["rows"].values()
                          for r in rr.values()})
    lines += ["", "## Contents", "",
              "- `calibration/runs.csv`: one row per valid run for this step (`checks_total` counts every check in "
              "the grade, guard checks included; `turns` counts the trajectory's agent steps).",
              "- `calibration/trajectories/<model>/<trial>/`: `agent/trajectory.json` (prompts, turns, tool calls, "
              "model name), `artifacts/` (the deliverables the model left after this step"
              + ("; `artifacts/client/` holds the live-review channel: every graded handoff and the thread"
                 if ctx["has_client"] else "") + "), "
              + ", ".join(f"`verifier/{g}`" for g in grade_names)
              + " (every check with its result), `verifier/reward-details.json` (per-rubric rewards), "
                "`verifier/reward.json`.",
              "- `REWARD-HACKING.md`: what was tested, found and fixed for this environment.",
              (f"- `verification/harbor-tasks-check.json`: `harbor tasks-check` receipt for this package "
               f"(status: {ctx['tasks_check']})." if ctx["tasks_check"] != "no receipt shipped"
               else "- No `harbor tasks-check` receipt ships with this version."),
              "- `authoring/tools/`: the scripts that derive the key and produce the evidence `solution/README.md` cites."
              if ctx["has_tools"] else None,
              "", "## Running it", "", "A native Harbor task root. Unzip and run:", "", "```",
              f"unzip {task}__{step}.zip -d {task}__{step}",
              f"harbor run --path {task}__{step} -a oracle -k 1 -n 1", "```", ""]
    return "\n".join(line for line in lines if line is not None)


def context(task: Path, models: dict, steps: list[str], args, controls: dict) -> dict:
    toml = tomllib.loads((task / "task.toml").read_text())
    meta = toml.get("metadata") or {}
    name = task.name
    version = (toml.get("task") or {}).get("version") or "?"
    metrics = full_metrics(models, steps)
    campaigns = [c for cell in models.values() for c in cell["campaigns"]]
    modes = sorted({(c["report"].get("task_validation") or {}).get("mode") or "unknown" for c in campaigns})
    notes = sorted({(c["report"].get("task_validation") or {}).get("note") or "" for c in campaigns} - {""})
    valid = {m: v["episodes_valid"] for m, v in metrics.items()}
    per_model = []
    for model, cell in models.items():
        h = cell["campaigns"][0]["harness"]
        cap = f", {h['max_output_tokens'] // 1000}k output tokens" if h["max_output_tokens"] else ""
        lim = "no turn or time limits" if h["no_limits"] else f"limits {h}"
        per_model.append(f"{_label(model)} in {h['agent']} {h['version']} ({h['effort']} reasoning effort, {lim}{cap}; "
                         f"{h['web_tools']}; agent egress {', '.join(h['egress_allowlist']) or 'not recorded'})")
    attempts = (f"{min(valid.values())} valid attempts per model" if len(set(valid.values())) == 1
                else "valid attempts: " + ", ".join(f"{_label(m)} {n}" for m, n in valid.items()))
    harness_line = "; ".join(per_model) + f". {attempts}. Void episodes (infrastructure loss) are excluded from every figure."
    mode_lines = []
    if "legacy-diagnostic" in modes:
        mode_lines += [f"**Calibration mode: legacy diagnostic.** {'Every campaign' if modes == ['legacy-diagnostic'] else 'Some campaigns'} "
                       "ran in this checkout's `arena benchmark --legacy-diagnostic` mode (`task_validation.mode` in each "
                       "campaign's report.json; `release_qualified` and `current_generator_verified` are false). The task "
                       f"is graded by its own authored grader ({_grader_desc(task)}){_channel_desc(task)}, which the "
                       "benchmark runs exactly as shipped.", ""]
    elif modes != ["current-draft"]:
        mode_lines += [f"**Calibration mode:** {', '.join(modes)}.", ""]
    unbound = [c for c in campaigns if not c["binding"]["bound"]]
    if unbound:
        mode_lines += ["**Warning: these campaigns ran a different version of this task** (built with --allow-stale): "
                       + ", ".join(c["dir"].name for c in unbound) + ". The figures below do not describe this package.", ""]
    else:
        mode_lines += ["Every campaign ran exactly this package: its frozen task surfaces ("
                       + ", ".join(_frozen_present(task)) + ") are byte-identical to the ones shipped here.", ""]
    low = [m for m, n in valid.items() if n < args.min_valid]
    if low:
        mode_lines += [f"**Not a calibration of record:** fewer than {args.min_valid} valid episodes for "
                       + ", ".join(_label(m) for m in low) + " (pilot measurement).", ""]
    missing_roles = [r for r in ("fable", "astra") if not getattr(args, r)]
    if missing_roles:
        mode_lines += [f"**Only part of the calibration:** no campaign for {', '.join(missing_roles)}.", ""]
    tc_path = task / "verification/harbor-tasks-check.json"
    tasks_check = (_json(tc_path).get("status") or "unknown") if tc_path.is_file() else "no receipt shipped"
    tests_src = "".join(p.read_text(errors="replace") for p in (task / "tests").glob("*.py"))
    llm = re.search(r"^\s*(?:import|from)\s+(?:anthropic|openai|litellm)\b", tests_src, re.M)
    runner = ("`tests/test.sh` runs `tests/grade.py`" if (task / "tests/grade.py").is_file()
              else "`tests/test.sh` runs `tests/criteria.py`")
    grader = (f"Scored by `tests/` ({runner}), shipped at that same path. Each step has its own rubric"
              + ("; rubrics are deterministic, no LLM judge." if not llm else "; the grader imports an LLM client."))
    if controls:
        parts = []
        for kind, res in controls.items():
            parts.append(f"{'reference solution (oracle)' if kind == 'oracle' else 'untouched workspace (nop)'} "
                         + ", ".join(f"{s} {r if r is not None else 'n/a'}" for s, r in res["steps"])
                         + ("" if res["bound_to_this_package"] else " [ran a different version]"))
        grader += " Harbor controls on this version: " + "; ".join(parts) + "."
    elif (task / "verification/controls.json").is_file():
        grader += " Controls: see `verification/controls.json`."
    else:
        grader += (" No Harbor oracle/nop control of this version ships with this package; `solution/README.md` and "
                   "`REWARD-HACKING.md` give the reference-solution evidence that exists.")
    has_client = any((r["base"] / "artifacts/app/client").is_dir() for cell in models.values()
                     for rr in cell["rows"].values() for r in rr.values())
    return {"name": name, "steps": steps, "version": version, "metrics": metrics, "models": models,
            "level": meta.get("faithfulness") or (name.split("_")[1].upper() if name.startswith("a_f") else "unknown"),
            "session": meta.get("source_trace") or "", "package_task_name": (toml.get("task") or {}).get("name"),
            "description": (toml.get("task") or {}).get("description", "").split(". ")[0].rstrip(".") + ".",
            "harness_line": harness_line, "mode_lines": mode_lines, "modes": modes, "notes": notes,
            "grader": grader, "tasks_check": tasks_check, "has_client": has_client,
            "has_tools": (task / "authoring/tools").is_dir(),
            "changes": changes_lines(task, args.changes, version, not unbound), "campaigns": campaigns}


def manifest(ctx: dict, task: Path, step: str, controls: dict) -> dict:
    return {"task": f"{ctx['name']}/{step}", "source_arena_session": ctx["session"],
            "faithfulness_level": ctx["level"], "package_task_name": ctx["package_task_name"],
            "steps_tests_solution_sha256": steps_tests_solution_sha256(task),
            "task_level_metrics": ctx["metrics"],
            "definitions": {"pass": "every step scores full marks",
                            "pass_at_4": "unbiased estimator 1 - C(n-c,4)/C(n,4)",
                            "average_reward": "mean over valid episodes of the mean step reward",
                            "steps_tests_solution_sha256": "sha256 of the sorted JSON map relpath -> sha256 "
                                                           "over steps/, tests/ and solution/",
                            "step_pass_rates": "per step: valid episodes scoring full marks on that step / valid episodes",
                            "episodes_void": "recorded episodes the runner marked invalid (infrastructure loss); "
                                             "excluded from every rate"},
            "package_version": ctx["version"],
            "calibration": {"mode": ctx["modes"][0] if len(ctx["modes"]) == 1 else ctx["modes"],
                            "runner_note": ctx["notes"],
                            "command": "arena benchmark <task> --coder --agent harness -m <model> -r N --effort high"
                                       + (" --legacy-diagnostic" if "legacy-diagnostic" in ctx["modes"] else ""),
                            "campaigns": [{"model": c["model"], "directory": c["dir"].name,
                                           "artifact_sha256": c["binding"]["artifact_sha256"],
                                           "bound_to_this_package": c["binding"]["bound"],
                                           "release_qualified": (c["report"].get("task_validation") or {}).get("release_qualified"),
                                           "current_generator_verified": (c["report"].get("task_validation") or {}).get("current_generator_verified"),
                                           "episodes_requested": c["requested"], "episodes_recorded": c["recorded"],
                                           "episodes_valid": len(c["trials"]), "episodes_void": len(c["voids"]),
                                           "started_at": c["report"].get("started_at"),
                                           "finished_at": c["report"].get("finished_at")}
                                          for c in ctx["campaigns"]],
                            "controls": controls or None}}


# --------------------------------------------------------------------------- writing
def scan_secret(data: bytes) -> bool:
    return bool(SECRET.search(data))


def write_member(z: zipfile.ZipFile, path: Path, arcname: str, problems: list[str]) -> None:
    if path.is_symlink():
        problems.append(f"refused to follow symlink {arcname}")
        return
    data = path.read_bytes()
    if scan_secret(data):
        problems.append(f"credential-shaped string in {arcname}")
        return
    info = zipfile.ZipInfo.from_file(path, arcname)
    info.external_attr = 0o100644 << 16  # uniform 0644: run outputs arrive 0600/0664 (2026-10-09)
    info.compress_type = z.compression
    z.writestr(info, data)


def build_stepzips(task: Path, ctx: dict, out: Path, files: list[Path], controls: dict,
                   problems: list[str], warnings: list[str]) -> list[Path]:
    written = []
    for index, step in enumerate(ctx["steps"], 1):
        target = out / f"{ctx['name']}__{step}.zip"
        tmp = out / f".{target.name}.partial"
        rows: dict[str, list[list]] = {}
        local: list[str] = []
        with zipfile.ZipFile(tmp, "w", zipfile.ZIP_DEFLATED) as z:
            for path in files:
                write_member(z, path, path.relative_to(task).as_posix(), local)
            for model, cell in ctx["models"].items():
                for run, (tid, tdir, rewards) in enumerate(cell["trials"], 1):
                    r = cell["rows"][tid][step]
                    rows.setdefault(model, []).append([model, run, tid, r["reward"], r["passed"], r["total"], r["turns"],
                                                       r["prompt_tokens"], r["completion_tokens"], "; ".join(r["failed"])])
                    base, prefix = r["base"], f"calibration/trajectories/{model}/{tid}"
                    write_member(z, base / "agent/trajectory.json", f"{prefix}/agent/trajectory.json", local)
                    for name in VERIFIER_FILES:
                        if (base / "verifier" / name).is_file():
                            write_member(z, base / "verifier" / name, f"{prefix}/verifier/{name}", local)
                    seen = set()
                    for sub, dest in (("artifacts/app/deliverables", ""), ("artifacts/app/client", "client/")):
                        root = base / sub
                        for produced in sorted(root.rglob("*")) if root.is_dir() else []:
                            rel = dest + produced.relative_to(root).as_posix()
                            if produced.is_symlink():
                                warnings.append(f"{model}/{tid}/{step}: symlink {sub}/{rel} not shipped "
                                                f"(-> {produced.readlink()})")
                                continue
                            if produced.is_file():
                                if rel in seen:
                                    local.append(f"{prefix}/artifacts/{rel} collides")
                                seen.add(rel)
                                write_member(z, produced, f"{prefix}/artifacts/{rel}", local)
            buffer = io.StringIO()
            writer = csv.writer(buffer, lineterminator="\n")
            writer.writerow(RUNS_HEADER)
            for model_rows in rows.values():
                writer.writerows(model_rows)
            z.writestr(_info("calibration/runs.csv"), buffer.getvalue())
            z.writestr(_info("CALIBRATION-MANIFEST.json"),
                       json.dumps(manifest(ctx, task, step, controls), indent=2) + "\n")
            z.writestr(_info("README.md"), readme(ctx, step, index, rows))
        local += check_stepzip(tmp, target.name, task, files, ctx, warnings)
        written.append(_finish(tmp, target, local, problems))
    return written


def build_a_f1(task: Path, ctx: dict, out: Path, files: list[Path], controls_dirs: dict, controls: dict,
               problems: list[str], warnings: list[str]) -> list[Path]:
    name, steps = ctx["name"], ctx["steps"]
    target = out / (f"{name}__{steps[0]}.zip" if len(steps) == 1 else f"{name}__{steps[0]}_multi_task.zip")
    tmp = out / f".{target.name}.partial"
    local: list[str] = []
    cited, topups = [], {}
    with zipfile.ZipFile(tmp, "w", zipfile.ZIP_DEFLATED) as z:
        for path in files:
            write_member(z, path, f"{name}/{path.relative_to(task).as_posix()}", local)

        def copy_dir(src: Path, dest: str) -> None:
            for path in sorted(src.rglob("*")):
                rel = path.relative_to(src)
                if "__pycache__" in rel.parts:
                    continue
                if path.is_symlink():
                    warnings.append(f"{dest}/{rel.as_posix()}: symlink not shipped (-> {path.readlink()})")
                elif path.is_file():
                    write_member(z, path, f"{name}/{dest}/{rel.as_posix()}", local)

        for model, cell in ctx["models"].items():
            for i, c in enumerate(cell["campaigns"]):
                dest = f"verification/campaigns/calibration-{model}" + (f"-{i + 1}" if i else "")
                copy_dir(c["dir"], dest)
                (topups.setdefault(model, []) if i else cited).append(dest)
        harness = {c["harness"]["agent"]: c["harness"]["web_tools"] for c in ctx["campaigns"]}
        receipt = {"campaigns": cited, "topups": topups,
                   "protocol": sorted({c["report"].get("protocol") for c in ctx["campaigns"]} - {None})[0]
                   if any(c["report"].get("protocol") for c in ctx["campaigns"]) else None,
                   "harness_web_tools": "; ".join(f"{a}: {w}" for a, w in harness.items()),
                   "calibration_mode": ctx["modes"][0] if len(ctx["modes"]) == 1 else ctx["modes"],
                   "runner_note": ctx["notes"],
                   "summary": {"package_version": ctx["version"], "task_level_metrics": ctx["metrics"],
                               "bound_to_this_package": all(c["binding"]["bound"] for c in ctx["campaigns"])}}
        z.writestr(_info(f"{name}/verification/native-calibrations.json"), json.dumps(receipt, indent=2) + "\n")
        if controls_dirs:
            for kind, c in controls_dirs.items():
                copy_dir(c["dir"], f"verification/controls/{kind}")
            native = {kind: f"verification/controls/{kind}" for kind in controls_dirs}
            native.update({f"{kind}_result": res for kind, res in controls.items()})
            z.writestr(_info(f"{name}/verification/native-controls.json"), json.dumps(native, indent=2) + "\n")
    local += check_a_f1(tmp, target.name, name, task, files, receipt, warnings)
    return [_finish(tmp, target, local, problems)]


def _info(arcname: str) -> zipfile.ZipInfo:
    """A generated a_f1 receipt, with the 0644 mode the delivered receipts carry."""
    info = zipfile.ZipInfo(arcname, date_time=__import__("time").localtime()[:6])
    info.compress_type = zipfile.ZIP_DEFLATED
    info.external_attr = 0o100644 << 16
    return info


def _finish(tmp: Path, target: Path, local: list[str], problems: list[str]) -> Path:
    if local:
        target.unlink(missing_ok=True)  # never leave an older zip under the name of one that failed
        bad = target.with_name(target.name + ".invalid")
        tmp.replace(bad)
        problems += [f"{target.name}: {p}" for p in local]
        return bad
    target.with_name(target.name + ".invalid").unlink(missing_ok=True)
    tmp.replace(target)
    return target


# --------------------------------------------------------------------------- checks of the written zip
def _common_checks(z: zipfile.ZipFile, prefix: str, task: Path, files: list[Path], warnings: list[str],
                   label: str) -> list[str]:
    """Problems with the written zip; dangling citations in the task's own docs are warnings (they may cite
    historical files on purpose), in the generated README they are problems."""
    problems = []
    names = set(z.namelist())
    bad = z.testzip()
    if bad:
        problems.append(f"corrupt member {bad}")
    for n in names:
        if n.startswith("/") or ".." in Path(n).parts:
            problems.append(f"unsafe member name {n}")
        parts = Path(n).parts
        if "__pycache__" in parts or n.endswith((".pyc", ".DS_Store")):
            problems.append(f"excluded file shipped: {n}")
    for path in files:
        arc = prefix + path.relative_to(task).as_posix()
        if arc not in names:
            problems.append(f"task file missing: {arc}")
        elif hashlib.sha256(z.read(arc)).hexdigest() != _sha(path):
            problems.append(f"task file differs from the task root: {arc}")
    # Batch-4 hand-built tasks (2026-10-09) were measured without authoring/spec.json, which is inside the identity
    # ROOTS, so adding it after calibration would unbind the campaigns. It is required only when the task has one.
    required = ["task.toml", "tests/checks.json", "tests/test.sh", "REWARD-HACKING.md"]
    if (task / "authoring/spec.json").is_file():
        required.append("authoring/spec.json")
    for rel in required:
        if prefix + rel not in names:
            problems.append(f"missing {rel}")
    if prefix + "tests/grade.py" not in names and prefix + "tests/criteria.py" not in names:
        problems.append("missing the grader (tests/grade.py or tests/criteria.py)")
    for n in sorted(names):
        if n.endswith(".md") and (n.startswith(prefix + "solution/") or n == prefix + "REWARD-HACKING.md"
                                  or n == prefix + "README.md"):
            text = z.read(n).decode(errors="replace")
            sink = problems if n == prefix + "README.md" else warnings
            refs = {}
            for match in DOC_REF.finditer(text):  # a ref followed by <, {, * or [ is a template: prefix match
                ref = match.group(1).rstrip(".")
                refs[ref] = refs.get(ref, False) or text[match.end():match.end() + 1] in ("<", "{", "*", "[")
            for ref, templated in sorted(refs.items()):
                if not any(m == prefix + ref or m.startswith(prefix + ref.rstrip("/") + "/")
                           or (templated and m.startswith(prefix + ref)) for m in names):
                    sink.append(f"{label}: {n} cites {ref}, which is not in the zip")
            if "FIXES.md" in text and prefix + "FIXES.md" not in names:
                sink.append(f"{label}: {n} cites FIXES.md, which is not shipped")
    return problems


def check_stepzip(path: Path, final_name: str, task: Path, files: list[Path], ctx: dict,
                  warnings: list[str]) -> list[str]:
    stem = final_name[:-4]
    name, step = stem.rsplit("__", 1)
    with zipfile.ZipFile(path) as z:
        problems = _common_checks(z, "", task, files, warnings, final_name)
        names = set(z.namelist())
        for rel in ("CALIBRATION-MANIFEST.json", "calibration/runs.csv", "README.md", f"steps/{step}/instruction.md"):
            if rel not in names:
                problems.append(f"missing {rel}")
        if problems:
            return problems
        man = json.loads(z.read("CALIBRATION-MANIFEST.json"))
        if man.get("task") != f"{name}/{step}":
            problems.append(f"manifest task {man.get('task')!r} != {name}/{step}")
        with tempfile.TemporaryDirectory() as tmp:  # a private directory of our own, removed on exit
            root = Path(tmp) / name
            for member in ("steps/", "tests/", "solution/"):
                for n in names:
                    if n.startswith(member):
                        z.extract(n, root)
            if man.get("steps_tests_solution_sha256") != steps_tests_solution_sha256(root):
                problems.append("steps_tests_solution_sha256 does not match the packaged steps/tests/solution")
        text = z.read("calibration/runs.csv").decode()
        reader = csv.reader(text.splitlines())
        if next(reader) != RUNS_HEADER:
            problems.append("runs.csv header differs from pipeline.stepzips.RUNS_HEADER")
        rows = list(csv.DictReader(text.splitlines()))
        for model, m in (man.get("task_level_metrics") or {}).items():
            mine = [r for r in rows if r["model"] == model]
            if len(mine) != m.get("episodes_valid"):
                problems.append(f"{model}: {len(mine)} runs.csv rows for {m.get('episodes_valid')} valid episodes")
            step_passes = sum(1 for r in mine if float(r["step_score"]) >= 1.0 - EPS)
            if m.get("passes", 0) > step_passes:
                problems.append(f"{model}: {m.get('passes')} task passes but only {step_passes} passes of this step")
            if step_passes != (m.get("step_pass_rates") or {}).get(step, {}).get("passes"):
                problems.append(f"{model}: runs.csv step passes {step_passes} != manifest step_pass_rates")
            if m.get("episodes_valid", 0) < 10:
                warnings.append(f"{final_name}: {model}: {m.get('episodes_valid')} valid episodes; the calibration of record is 10")
            for r in mine:
                base = f"calibration/trajectories/{model}/{r['trial_id']}"
                for rel in ("agent/trajectory.json", "verifier/reward-details.json", "verifier/reward.json"):
                    if f"{base}/{rel}" not in names:
                        problems.append(f"{model}/{r['trial_id']}: missing {rel}")
                if f"{base}/verifier/arena-grade.json" not in names and f"{base}/verifier/grade-output.json" not in names:
                    problems.append(f"{model}/{r['trial_id']}: missing the per-check grade")
                if int(r["checks_passed"]) > int(r["checks_total"]):
                    problems.append(f"{model}/{r['trial_id']}: checks_passed exceeds checks_total")
        if "verification/harbor-tasks-check.json" not in names:
            warnings.append(f"{final_name}: no verification/harbor-tasks-check.json")
        elif json.loads(z.read("verification/harbor-tasks-check.json")).get("status") != "pass":
            warnings.append(f"{final_name}: harbor tasks-check receipt status is "
                            f"{json.loads(z.read('verification/harbor-tasks-check.json')).get('status')!r}")
    return problems


def check_a_f1(path: Path, final_name: str, name: str, task: Path, files: list[Path], receipt: dict,
               warnings: list[str]) -> list[str]:
    with zipfile.ZipFile(path) as z:
        prefix = f"{name}/"
        problems = _common_checks(z, prefix, task, files, warnings, final_name)
        names = set(z.namelist())
        tops = {n.split("/", 1)[0] for n in names}
        if tops != {name}:
            problems.append(f"top-level entries {sorted(tops)} != [{name}]")
        for c in receipt["campaigns"] + [d for v in receipt["topups"].values() for d in v]:
            if f"{prefix}{c}/report.json" not in names:
                problems.append(f"native-calibrations cites {c}, which has no report.json in the zip")
    return problems


# --------------------------------------------------------------------------- structure diff
def pattern(name: str, task: str | None) -> str:
    p = name
    if task:
        p = p.replace(task, "<task>")
    p = re.sub(r"^a_f\d_[^/]+/", "<task>/", p)
    p = re.sub(r"package__[A-Za-z0-9]+", "package__X", p)
    p = re.sub(r"(calibration/trajectories/[^/]+/)[^/]+/", r"\1<trial>/", p)
    p = re.sub(r"/artifacts/.+", "/artifacts/...", p)
    p = re.sub(r"/isolation/[0-9a-f]{64}\.json$", "/isolation/<sha>.json", p)
    p = re.sub(r"backup\.\d+$", "backup.<n>", p)
    p = re.sub(r"/projects/-app/[^/]+\.jsonl$", "/projects/-app/<session>.jsonl", p)
    p = re.sub(r"environment/files/.+", "environment/files/...", p)
    return p


def compare(produced: Path, reference: Path) -> int:
    def load(path: Path):
        with zipfile.ZipFile(path) as z:
            names = [n for n in z.namelist() if not n.endswith("/")]
            stem = path.name[:-4]
            task = stem.split("__", 1)[0]
            pats = {pattern(n, task) for n in names}
            man = next((json.loads(z.read(n)) for n in names if n.endswith("CALIBRATION-MANIFEST.json")), None)
            runs = next((z.read(n).decode().splitlines()[0] for n in names if n.endswith("calibration/runs.csv")), None)
            native = next((json.loads(z.read(n)) for n in names if n.endswith("verification/native-calibrations.json")
                           and "/campaigns/" not in n), None)
            return task, pats, man, runs, native, len(names)

    a_task, a, a_man, a_runs, a_nat, a_n = load(produced)
    b_task, b, b_man, b_runs, b_nat, b_n = load(reference)
    same_task = a_task == b_task
    if not same_task:  # different tasks legitimately differ inside the task root; compare the delivery layer
        layer = re.compile(r"^(<task>/)?(CALIBRATION-MANIFEST\.json|README\.md|REWARD-HACKING\.md|calibration/|"
                           r"verification/|task\.toml|tests/(checks\.json|test\.sh)|authoring/(spec|traps)\.json)")
        a, b = {p for p in a if layer.match(p)}, {p for p in b if layer.match(p)}
    print(f"structure diff: {produced.name} ({a_n} files) vs {reference.name} ({b_n} files)"
          + ("" if same_task else " [different tasks: delivery layer only]"))
    for label, items in (("only in produced", sorted(a - b)), ("only in reference", sorted(b - a))):
        print(f"  {label}: {len(items)}")
        for p in items[:60]:
            print(f"    {p}")
        if len(items) > 60:
            print(f"    ... {len(items) - 60} more")
    if a_man is not None or b_man is not None:
        ak, bk = set(a_man or {}), set(b_man or {})
        print(f"  manifest keys only in produced: {sorted(ak - bk)}; only in reference: {sorted(bk - ak)}")
        am = next(iter(((a_man or {}).get("task_level_metrics") or {}).values()), {})
        bm = next(iter(((b_man or {}).get("task_level_metrics") or {}).values()), {})
        print(f"  per-model metric keys only in produced: {sorted(set(am) - set(bm))}; "
              f"only in reference: {sorted(set(bm) - set(am))}")
    if a_runs is not None or b_runs is not None:
        print(f"  runs.csv header {'identical' if a_runs == b_runs else 'DIFFERS: ' + repr(a_runs) + ' vs ' + repr(b_runs)}")
    if a_nat is not None or b_nat is not None:
        print(f"  native-calibrations keys only in produced: {sorted(set(a_nat or {}) - set(b_nat or {}))}; "
              f"only in reference: {sorted(set(b_nat or {}) - set(a_nat or {}))}")
    return 0


# --------------------------------------------------------------------------- main
def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    if argv and argv[0] == "--compare":
        if len(argv) != 3:
            sys.exit("usage: assemble_fb_zip.py --compare <produced.zip> <reference.zip>")
        return compare(Path(argv[1]), Path(argv[2]))
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("task", type=Path, help="the task root (e.g. envs-fb/a_f1_small-business-tax)")
    ap.add_argument("--fable", type=Path, action="append", default=[], help="Fable benchmark output dir (repeat for top-ups)")
    ap.add_argument("--astra", type=Path, action="append", default=[], help="Astra benchmark output dir (repeat for top-ups)")
    ap.add_argument("--oracle", type=Path, help="optional `arena benchmark --agent oracle` output dir of this version")
    ap.add_argument("--nop", type=Path, help="optional `arena benchmark --agent nop` output dir of this version")
    ap.add_argument("-o", "--out", type=Path, required=True, help="directory for the zips")
    ap.add_argument("--shape", choices=("stepzip", "a_f1"), default="stepzip")
    ap.add_argument("--changes", type=Path, help="markdown for the README's change section (default: FIXES.md's NC- headings)")
    ap.add_argument("--min-valid", type=int, default=10, help="valid episodes per model below which the README says pilot")
    ap.add_argument("--pipeline-filter", action="store_true",
                    help="stepzip shape: ship the task root exactly as pipeline.stepzips.package_files selects it "
                         "(authoring/ only spec+traps, verification/ only controls/delivery/harbor-tasks-check/probes)")
    ap.add_argument("--allow-stale", action="store_true",
                    help="package campaigns that ran another version of the task (testing only; the README says so)")
    ap.add_argument("--force", action="store_true", help="overwrite existing zips")
    ap.add_argument("--compare-to", type=Path, help="print a structure diff of each written zip against this reference zip")
    args = ap.parse_args(argv)

    task = args.task.resolve()
    out = args.out.resolve()
    if not (task / "task.toml").is_file():
        sys.exit(f"{task}: not a task root (no task.toml)")
    if out == task or task in out.parents:
        sys.exit("write the zips outside the task root")
    problems: list[str] = []
    warnings: list[str] = []
    steps = sorted(p.name for p in (task / "steps").iterdir() if p.is_dir())
    toml_steps = [s.get("name") for s in tomllib.loads((task / "task.toml").read_text()).get("steps") or []]
    if toml_steps and toml_steps != steps:
        problems.append(f"task.toml steps {toml_steps} != steps/ {steps}")
    if not (args.fable or args.astra):
        sys.exit("give at least one --fable or --astra campaign")
    campaigns = []
    for role in ("fable", "astra"):
        for d in getattr(args, role):
            c = load_campaign(task, d, role, steps, args.allow_stale, problems, warnings)
            if c:
                campaigns.append(c)
    models = merge_models(campaigns, problems)
    for model, cell in models.items():
        if not cell["trials"]:
            problems.append(f"{model}: no valid episode; nothing to report")
    controls_dirs, controls = {}, {}
    for kind, d in (("oracle", args.oracle), ("nop", args.nop)):
        if d:
            c = load_campaign(task, d, kind, steps, args.allow_stale, problems, warnings)
            if c:
                controls_dirs[kind] = c
                controls[kind] = control_result(c, steps, 1.0 if kind == "oracle" else 0.0)
                if not controls[kind]["ok"]:
                    warnings.append(f"{kind} control did not score {1.0 if kind == 'oracle' else 0.0} on every step: "
                                    f"{controls[kind]['steps']}")
    try:
        files = task_files(task, args.shape, bool(controls_dirs), args.pipeline_filter and args.shape == "stepzip")
    except ValueError as exc:
        problems.append(str(exc))
        files = []
    if not problems:
        ctx = context(task, models, steps, args, controls)
        ctx["has_tools"] = any(f.relative_to(task).parts[:2] == ("authoring", "tools") for f in files)
        names = ([f"{ctx['name']}__{s}.zip" for s in steps] if args.shape == "stepzip" else
                 [f"{ctx['name']}__{steps[0]}.zip" if len(steps) == 1 else f"{ctx['name']}__{steps[0]}_multi_task.zip"])
        existing = [n for n in names if (out / n).exists()]
        if existing and not args.force:
            problems.append(f"{', '.join(existing)} already exist in {out} (use --force)")
    for w in warnings:
        print(f"WARNING {w}")
    if problems:
        print("REFUSED -- nothing written:\n  " + "\n  ".join(problems))
        return 1
    out.mkdir(parents=True, exist_ok=True)
    built_problems: list[str] = []
    late_warnings: list[str] = []
    if args.shape == "stepzip":
        written = build_stepzips(task, ctx, out, files, controls, built_problems, late_warnings)
    else:
        written = build_a_f1(task, ctx, out, files, controls_dirs, controls, built_problems, late_warnings)
    for w in late_warnings:
        print(f"WARNING {w}")
    for m, v in ctx["metrics"].items():
        steps_txt = ", ".join(f"{s} {p['passes']}/{p['episodes_valid']}" for s, p in v["step_pass_rates"].items())
        print(f"{_label(m)}: pass@1 {v['pass_at_1']:.2f} ({v['passes']}/{v['episodes_valid']} valid, "
              f"{v['episodes_void']} void); steps: {steps_txt}")
    for path in written:
        print(f"{path}: {'OK' if path.suffix == '.zip' else 'INVALID'} ({path.stat().st_size:,} bytes)")
        if args.compare_to and path.suffix == ".zip":
            compare(path, args.compare_to)
    if built_problems:
        print("PROBLEMS:\n  " + "\n  ".join(built_problems))
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
