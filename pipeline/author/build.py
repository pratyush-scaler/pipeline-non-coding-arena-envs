"""Stage F3 -- materialise an EnvSpec into a bundle the gate chain can read.

The spec is the single source of truth; every file here is generated from it, so
fixture, instruction, checks and grader cannot drift apart. That drift is how a
task silently regresses -- moving a gate onto an unclearable check took one task
from 0.875/0.25 to 0.125/0.125 -- and the only reliable defence is that the three
are one artefact.

Layout, matching what we already ship to Arena:

    <bundle>/
      task.toml                 harbor config, steps, provenance metadata
      steps/<step>/instruction.md   the only prose the agent sees
      environment/files/        the fixture -- lifted documents
      tests/checks.json         the declarative checks
      tests/basis.toml          public wording per check (contract.completeness)
      tests/reward.toml         dimension weights
      tests/rubric.json         per-step rubric
      tests/criteria.py         thin runner over the declarative checks
      authoring/traps.json      typed traps with provenance
      authoring/extraction/     lifted material + ground truth (never shipped)
      solution/submission/      the reference solution
      provenance/ledger.json    faithfulness, generated
      verification/probes.json  written by the probe runner
"""

from __future__ import annotations

import json
import re
import shutil
import tomllib
from pathlib import Path
from typing import Any

from . import oracle
from .contracts import compile_steps, contained, public_contract

CRITERIA_RUNNER = '''"""Grading entry point.

Deliberately thin. Every scored decision lives in `checks.json` as data, and one
reviewed evaluator runs them, so this file has nothing task-specific to get
wrong. The nine defects returned on the first delivery were all properties of
hand-written grader code; there is no hand-written grader code here.

Read `checks.json` to review what is scored, and `basis.toml` for the public
wording each check rests on.
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from _arena_runtime.checks_runtime import Workspace, grade, load  # noqa: E402


def main() -> int:
    source = Path(os.environ.get("ARENA_SOURCE", "/app/environment/files"))
    submitted = Path(os.environ.get("ARENA_SUBMITTED", "/app/deliverables"))
    checks = load(HERE / "checks.json")
    # The shipped grader must be handed the projections and the derived rows,
    # or every check whose target reads a `.jsonl` raises inside the container.
    # Measured on this batch: 65 of 84 objectives read a projection, the bundle
    # ships `derived/` and `projections.json` beside this file, and the runtime
    # passed neither -- so scores came from our own harness and the bundle as
    # shipped would fail on its first check. Adopted from the upstream fork.
    # Harbor runs each step with ARENA_STEP set, and `rubric.json` says which
    # checks belong to which step. Without this the grader scored EVERY check
    # on EVERY step: step 1 penalised for work it was not yet asked to do, and
    # step 2 re-credited for step 1's. Single-step bundles are unaffected --
    # An unknown step is an execution error, never a request to grade everything.
    step = os.environ.get("ARENA_STEP", "").strip()
    rubric_file = HERE / "rubric.json"
    rubric = json.loads(rubric_file.read_text())
    if not step and len(rubric) == 1:
        step = next(iter(rubric))
    if step not in rubric:
        raise ValueError("ARENA_STEP must name a declared step")
    wanted = set(rubric[step])
    checks = [c for c in checks if c.id in wanted]

    derived = HERE / "derived"
    projections_file = HERE / "projections.json"
    if any(derived.glob("*.jsonl")) and not projections_file.is_file():
        raise RuntimeError("derived targets require projections metadata")
    projections = (json.loads(projections_file.read_text())["projections"]
                   if projections_file.is_file() else None)
    result = grade(checks, Workspace(
        source=source, submitted=submitted,
        derived=derived, projections=projections, step=step))
    out = Path(os.environ.get("ARENA_REWARD", "/app/reward.json"))
    out.write_text(json.dumps({"reward": float(result["reward"])}))
    details = os.environ.get("ARENA_DETAILS")
    if details:
        Path(details).write_text(json.dumps({"reward": {"kind": "programmatic",
            "score": result["reward"], "criteria": [
                {"name": cid, "value": float(bool(rec.get("passed"))),
                 "status": "evaluated", "gated_out": bool(rec.get("gated_out")),
                 "reason": rec.get("reason", "")}
                for cid, rec in result["checks"].items()]}}))
    json.dump(result, sys.stdout, indent=2)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
'''

TASK_TOML = '''schema_version = "1.4"
artifacts = ["/app/deliverables", "/app/environment/files"]
multi_step_reward_strategy = "mean"

[task]
name = {name}
version = "1.0.0"
description = {description}
authors = [{{ name = "Arena Environments Team", email = "noreply@example.invalid" }}]
keywords = {keywords}

[metadata]
category = {category}
source_trace = {session_id}
source_seeds = [{source_seed}]
source_tier = {tier}
source_intent = {intent}
difficulty_explanation = """
{difficulty}
"""

[environment]
build_timeout_sec = 600.0
os = "linux"
network_mode = "no-network"
cpus = 2
memory_mb = 16384
storage_mb = 10240

[agent]
timeout_sec = 10800.0
network_mode = "no-network"
user = "agent"

[verifier]
timeout_sec = 900.0
network_mode = "no-network"
environment_mode = "separate"

[verifier.environment]
network_mode = "no-network"

{steps}
'''


def _multiline(text: str) -> str:
    """A TOML multi-line basic string, with the delimiter and backslashes made
    safe. Generated prose contains both."""
    body = str(text).strip().replace("\\", "\\\\").replace('"""', '\\"\\"\\"')
    return body


def _steps_toml(steps: list[dict]) -> str:
    out = []
    for step in steps:
        name = json.dumps(str(step["name"]), ensure_ascii=False)
        out.append(f"[[steps]]\nname = {name}\n"
                   f"[steps.verifier]\nenv = {{ ARENA_STEP = {name} }}\n")
    return "\n".join(out)


#: Every bundle's objective weights sum to exactly this, so a weight reads as
#: the percentage of the task that check is worth -- the same number in every
#: bundle meaning the same thing. The one definition is `policy.WEIGHT_TOTAL`.
from ..policy import WEIGHT_TOTAL


def step_budgets(steps: list[str], total: int = WEIGHT_TOTAL) -> dict[str, int]:
    """Split the task's points equally between its graded steps.

    Harbor averages step rewards (`multi_step_reward_strategy = "mean"`), and a
    step's reward is `earned / step points`. A check's real share of the task is
    therefore `points / step points / steps`. With one global budget the steps
    carried whatever totals the designer happened to write -- 64 and 36 in the
    audited schedule task -- so a documented 10/100 check was worth 13.9% of the
    task. Equal step budgets make `points / 100` the true share whenever the
    step count divides 100, and `reward.toml` documents the exact share either
    way. Largest remainder, so the budgets always sum to `total`.
    """
    if not steps:
        return {}
    base, extra = divmod(total, len(steps))
    return {name: base + (1 if i < extra else 0) for i, name in enumerate(steps)}


def normalise_weights(checks: list[dict], total: int = WEIGHT_TOTAL,
                      steps: list[str] | None = None) -> list[dict]:
    """Rescale objective weights, preserving their ratios within each step.

    Scoring is `earned / sum(weights)` per step, so the absolute numbers never
    affected a reward -- only their ratios did, and a designer emitting 84 in one
    bundle and 128 in another made `weight: 20` mean 24% in one task and 16% in
    another. Normalising is score-neutral within a step up to integer rounding.
    Across steps it is what makes the documented points true: each step gets an
    equal share of `total` (see `step_budgets`), because the task reward is the
    mean of the step rewards whatever the steps' raw totals were.

    Rounding uses the largest-remainder method rather than round-half-up,
    because rounding each weight independently does not sum to `total` -- it
    drifts, and a drifting denominator is exactly the kind of quiet
    inconsistency this repository keeps finding late.

    Guardrails are untouched: they carry weight 0 and zero the score on
    violation, so they are not part of the budget.
    """
    objectives = [c for c in checks if c.get("kind") == "objective"]
    if not objectives:
        return checks
    names = list(steps or [])
    for c in objectives:
        if c.get("step", "") not in names:
            names.append(c.get("step", ""))
    groups = {name: [c for c in objectives if c.get("step", "") == name] for name in names}
    groups = {name: members for name, members in groups.items() if members}
    budgets = step_budgets(list(groups), total)
    for name, members in groups.items():
        _normalise_group(members, budgets[name])
    return checks


def _normalise_group(objectives: list[dict], total: int) -> None:
    current = sum(c.get("weight", 0) for c in objectives)
    if current <= 0:
        return
    scaled = [(c, c.get("weight", 0) * total / current) for c in objectives]
    floors = [(c, int(v), v - int(v)) for c, v in scaled]
    # A check must stay worth something; a rounded-to-zero check is unscored
    # while still appearing in the rubric.
    assigned = sum(max(f, 1) for _, f, _ in floors)
    for c, f, _ in floors:
        c["weight"] = max(f, 1)
    remainder = total - assigned
    for c, _, frac in sorted(floors, key=lambda t: -t[2]):
        if remainder <= 0:
            break
        c["weight"] += 1
        remainder -= 1
    # Overshoot (many checks forced up to 1) comes off the heaviest first.
    for c in sorted(objectives, key=lambda c: -c["weight"]):
        if remainder >= 0:
            break
        if c["weight"] > 1:
            c["weight"] -= 1
            remainder += 1


def effective_shares(checks: list[dict], rubric: dict[str, list[str]],
                     strategy: str = "mean") -> dict[str, float]:
    """Each objective's true share of the task reward, computed the way the
    grader scores: per step `earned / step total`, then the step mean.

    This is the number `reward.toml` must document and the one
    `grader.reference` recomputes. Anything else is a rubric that reads one way
    and scores another.
    """
    if strategy != "mean":
        raise ValueError(f"unsupported multi_step_reward_strategy {strategy!r}")
    by_id = {c.get("id"): c for c in checks}
    shares: dict[str, float] = {}
    steps = [name for name in rubric]
    for name in steps:
        owned = [by_id[cid] for cid in rubric[name]
                 if cid in by_id and by_id[cid].get("kind") == "objective"]
        total = sum(c.get("weight", 0) for c in owned)
        for c in owned:
            share = (c.get("weight", 0) / total / len(steps)) if total else 0.0
            shares[c["id"]] = shares.get(c["id"], 0.0) + share
    return shares


def _reward_toml(checks: list[dict], steps: list[str], rubric: dict[str, list[str]]) -> str:
    shares = effective_shares(checks, rubric)
    by_id = {c["id"]: c for c in checks}
    out = ["# Scoring, documented exactly as the grader computes it.",
           "# A step's reward is earned points / that step's points; the task reward is",
           '# the mean of the step rewards (task.toml multi_step_reward_strategy = "mean").',
           "# A check's task_share is therefore points / step points / number of steps.",
           "# grader.reference recomputes every share below from checks.json and blocks on drift.",
           ""]
    for name in steps:
        owned = [by_id[cid] for cid in rubric.get(name, [])
                 if by_id.get(cid, {}).get("kind") == "objective"]
        dims: dict[str, int] = {}
        for c in owned:
            dims[c.get("dimension", "core")] = dims.get(c.get("dimension", "core"), 0) + int(c["weight"])
        points = sum(int(c["weight"]) for c in owned)
        out += ["[[reward]]", f"name = {json.dumps(name)}", f"step = {json.dumps(name)}",
                'aggregation = "weighted_mean"', f"points = {points}",
                f"task_share = {round(1 / len(steps), 6) if steps else 0}",
                f"weights = {{ {', '.join(f'{k} = {v}' for k, v in sorted(dims.items()))} }}", ""]
    out.append("[shares]")
    for cid in sorted(shares):
        c = by_id[cid]
        out.append(f"{json.dumps(cid)} = {{ step = {json.dumps(c.get('step', ''))}, "
                   f"points = {int(c['weight'])}, task_share = {round(shares[cid], 6)} }}")
    return "\n".join(out) + "\n"


#: Authoring metadata carried on a spec check that the runtime `Check` does not
#: take. It is validated on the spec and documented in `basis.toml`; the graded
#: `checks.json` carries only what the evaluator reads.
AUTHORING_ONLY_CHECK_KEYS = ("rule_quote", "rule_terms", "rule_sources")


def _runtime_check(check: dict) -> dict:
    return {k: v for k, v in check.items() if k not in AUTHORING_ONLY_CHECK_KEYS}


def _dimension_readme(dimension: str) -> str:
    return (f"# {dimension}\n\nChecks in this dimension are declared in "
            f'`../checks.json` with `"dimension": "{dimension}"`.\n')


def build(spec: dict, bundle: Path) -> dict:
    """Write every generated file. The fixture and extraction are assumed to be
    in place already (Stage F1); this never touches them."""
    bundle = Path(bundle)
    if spec.get("_validation_deferred"):
        from .agent_designer import validate_submission
        from .extract import extract
        source = spec["source"]
        row = {**source, "category": spec.get("category")}
        verdict = validate_submission(spec, row, extract(source["session_id"], source["seed_index"]), bundle)
        if not verdict["clean"]:
            raise ValueError("Submitted candidate failed mandatory downstream validation: " + "; ".join(verdict["problems"]))
        spec.pop("_validation_deferred")
        spec["solution"] = verdict["reference_answer"]
    for directory in ("tests", "steps", "solution", "environment", "authoring", "provenance"):
        root = contained(bundle, directory)
        if root.exists() and any(path.is_symlink() for path in root.rglob("*")):
            raise ValueError(f"cannot rebuild a bundle containing symlinks: {directory}")
    for sub in ("tests", "steps", "solution/submission", "provenance",
                "verification", "authoring"):
        contained(bundle, sub).mkdir(parents=True, exist_ok=True)

    src = spec["source"]
    from .validate import canonical_step_refs, parse_stringified_expressions
    canonical_step_refs(spec)
    parse_stringified_expressions(spec)
    steps = compile_steps(spec)
    from .checks import Check
    errors = [p for c in spec["checks"] for p in Check(**_runtime_check(c)).validate()]
    if errors:
        raise ValueError("; ".join(errors))
    for rel in ("task.toml", "tests/checks.json", "tests/basis.toml", "tests/reward.toml",
                "tests/outputs.json", "tests/fixture-manifest.json", "tests/rubric.json",
                "tests/criteria.py", "authoring/spec.json", "authoring/traps.json",
                ".dockerignore", "environment/Dockerfile", "tests/Dockerfile", "tests/test.sh"):
        contained(bundle, rel)

    # Every string goes through json.dumps. A TOML basic string is a JSON string
    # for our purposes, and interpolating raw generated prose produced a
    # task.toml that would not parse -- which surfaced as an ERROR on the first
    # gate and skipped the other fourteen.
    def q(value: object) -> str:
        return json.dumps(str(value), ensure_ascii=False)

    (bundle / "task.toml").write_text(TASK_TOML.format(
        name=q("arena/" + (re.sub(r"[^A-Za-z0-9_-]", "-", bundle.name).strip("-") or "task")), description=q(spec["description"]),
        keywords=json.dumps(spec.get("keywords", []), ensure_ascii=False),
        category=q(spec.get("category", "knowledge_work")),
        session_id=q(src["session_id"]),
        source_seed=q(f"{src['session_id']}::{src['seed_index']}"),
        tier=src.get("tier", 4), intent=q(spec.get("intent", "")),
        difficulty=_multiline(spec.get("difficulty", "")),
        steps=_steps_toml(steps)))

    # Drop step directories this spec does not declare. A rebuild of the same
    # bundle -- a retry after a failed design -- usually picks a slightly
    # different category, so it writes `steps/01-project-planning/` beside the
    # earlier `steps/01-renovation-project/` and leaves both. `task.toml` names
    # only the live one, so the runner is fine, but the gates read the agent's
    # visible surface as `steps/*/instruction.md` and concatenate every match:
    # a stale instruction then counts as published wording, and a rule the live
    # instruction never states can pass `contract.completeness` on the strength
    # of a file no agent will ever see.
    wanted = {step["name"] for step in steps}
    steps_root = bundle / "steps"
    if steps_root.is_dir():
        for stale in steps_root.iterdir():
            if stale.is_dir() and stale.name not in wanted:
                shutil.rmtree(stale)

    for step in steps:
        d = bundle / "steps" / step["name"]
        d.mkdir(parents=True, exist_ok=True)
        (d / "instruction.md").write_text(step["instruction"].rstrip()
            + public_contract(spec.get("outputs", []), step["name"]) + "\n")
        if step.get("handoff"):
            (d / "handoff.json").write_text(
                json.dumps(step["handoff"], indent=2, ensure_ascii=False))
        else:
            (d / "handoff.json").unlink(missing_ok=True)

    # Oracle projection: normalised rows every target is computed from.
    # Verifier-side only -- .dockerignore keeps tests/ out of the agent image.
    # Rebuild hygiene. A rebuild that only ADDS leaves the previous design's
    # artefacts in place: retired projections keep answering, a bundle that no
    # longer projects still ships `projections.json`, and a `derived` symlink
    # planted by an earlier run is followed. Each is a stale surface the grader
    # will happily read. Adopted from the upstream fork, whose exported-grader
    # tests caught all three here.
    fixture = bundle / "environment" / "files"
    projections = spec.get("projections", [])
    rows = oracle.project(fixture, projections) if projections else {}
    derived = bundle / "tests" / "derived"
    if derived.is_symlink() or derived.is_file():
        derived.unlink()
    elif derived.is_dir():
        shutil.rmtree(derived)
    projections_file = bundle / "tests" / "projections.json"
    projections_file.unlink(missing_ok=True)
    if projections:
        oracle.write(rows, derived)
        projections_file.write_text(
            json.dumps({"projections": projections}, indent=2))
    import hashlib
    protected = {}
    for path in sorted(fixture.rglob("*")):
        if path.is_symlink():
            raise ValueError("fixture symlinks are forbidden")
        if path.is_file():
            protected[path.relative_to(fixture).as_posix()] = hashlib.sha256(path.read_bytes()).hexdigest()
    (bundle / "tests" / "fixture-manifest.json").write_text(json.dumps({"files": protected}, indent=2))
    (bundle / "tests" / "outputs.json").write_text(json.dumps({"outputs": spec.get("outputs", [])}, indent=2))

    # The spec that produced this bundle, kept beside it. Nothing retained it
    # before, so a shipped task could not be traced back to the design that
    # made it, and `arena harden` had nothing to revise -- it would have had to
    # reconstruct a spec from checks.json and guess the rest. Written before
    # the derived artefacts so a build that fails later still leaves the
    # intent on disk.
    (bundle / "authoring").mkdir(parents=True, exist_ok=True)
    (bundle / "authoring" / "spec.json").write_text(
        json.dumps(spec, indent=2, ensure_ascii=False, default=str))

    step_names = [step["name"] for step in steps]
    checks = [_runtime_check(c) for c in normalise_weights(spec["checks"], steps=step_names)]
    (bundle / "tests" / "checks.json").write_text(
        json.dumps({"checks": checks}, indent=2, ensure_ascii=False))

    basis = "\n".join(f'{json.dumps(c["id"])} = {json.dumps(c["basis"], ensure_ascii=False)}'
                      for c in sorted(checks, key=lambda c: c["id"]))
    # The instruction sentence each filtered target rests on, for the reviewer:
    # `validate` proved it is verbatim in the step's instruction and names every
    # field and literal the filter uses.
    quoted = {c["id"]: c["rule_quote"] for c in spec["checks"] if c.get("rule_quote")}
    rules = "".join(f'{json.dumps(cid)} = {json.dumps(q if isinstance(q, list) else [q], ensure_ascii=False)}\n'
                    for cid, q in sorted(quoted.items()))
    # A declared translation (fixture token -> the instruction's words) is a
    # claim the lexical check cannot verify, so it is published for review.
    renamed = {c["id"]: c["rule_terms"] for c in spec["checks"]
               if isinstance(c.get("rule_terms"), dict) and c["rule_terms"]}
    terms = "".join(f'{json.dumps(cid)} = {{ '
                    + ", ".join(f"{json.dumps(str(k), ensure_ascii=False)} = {json.dumps(str(v), ensure_ascii=False)}"
                                for k, v in sorted(t.items())) + " }\n"
                    for cid, t in sorted(renamed.items()))
    source_rules = "".join(
        f'{json.dumps(check["id"])} = [' + ", ".join(
            "{ file = " + json.dumps(entry["file"], ensure_ascii=False)
            + ", quote = " + json.dumps(entry["quote"], ensure_ascii=False) + " }"
            for entry in check["rule_sources"]) + "]\n"
        for check in spec["checks"] if check.get("rule_sources"))
    (bundle / "tests" / "basis.toml").write_text(
        "# Public wording for every scored decision; not loaded during grading.\n"
        "[checks]\n" + basis + "\n"
        + ("\n# Instruction sentences that state each filtered target's rule, verbatim.\n"
           "[rules]\n" + rules if rules else "")
        + ("\n# Fixture tokens the instruction words differently: token = instruction words.\n"
           "[rule_terms]\n" + terms if terms else "")
        + ("\n[rule_sources]\n" + source_rules if source_rules else ""))

    rubric = {step["name"]: [c["id"] for c in checks
                             if c.get("step") == step["name"] or c.get("assertion") == "fixture_intact"]
              for step in steps}
    dims: dict[str, float] = {}
    for c in checks:
        if c["kind"] == "objective":
            dims[c.get("dimension", "core")] = dims.get(c.get("dimension", "core"),
                                                        0) + c["weight"]
    (bundle / "tests" / "reward.toml").write_text(_reward_toml(checks, step_names, rubric))
    # A repaired spec can rename dimensions. Retire only files identifiable as
    # our generated descriptions, including leftovers from earlier rebuilds.
    # Preserve other material so reproduction still flags it for review.
    for directory in (bundle / "tests").iterdir():
        if not directory.is_dir() or directory.name in dims:
            continue
        readme = directory / "README.md"
        if (readme.is_file()
                and readme.read_bytes() == _dimension_readme(directory.name).encode("utf-8")):
            readme.unlink()
            if not any(directory.iterdir()):
                directory.rmdir()
    for dim in dims:
        (bundle / "tests" / dim).mkdir(exist_ok=True)
        (bundle / "tests" / dim / "README.md").write_text(
            _dimension_readme(dim))

    (bundle / "tests" / "rubric.json").write_text(json.dumps(rubric, indent=2))

    (bundle / "tests" / "criteria.py").write_text(CRITERIA_RUNNER)

    # The evaluator ships as a real package carrying BOTH halves. `checks.py`
    # builds projections through `oracle`, so a bundle that ships only
    # `checks_runtime.py` cannot grade any check whose target reads a `.jsonl`
    # -- and 65 of this batch's 84 objectives do. A flat module also has no
    # working relative import once the delivered bundle runs with no pipeline
    # repository on `sys.path`. Adopted from the upstream fork.
    # One staging helper for both copies (tests/ and each step's solution/),
    # so the reference can never derive with a different evaluator than the
    # one that grades it.
    from . import runtime
    runtime.stage(bundle / "tests" / runtime.PACKAGE)
    (bundle / "tests" / "checks_runtime.py").unlink(missing_ok=True)

    # Preserve `usable_corrections` across the rebuild. Dropping it made the
    # trap budget a MOVING GOALPOST: `gates/difficulty.py` defaulted the absent
    # value to `len(traps)`, so the expectation tracked the trap count and
    # adding a trap raised the target it was meant to satisfy. Measured on
    # brand-consulting-002, where one added trap moved the target from 11 to 12;
    # four independent authors hit it, and the real counts were 3, 1 and 0
    # against the 11, 7 and 7 the gate inferred.
    traps_path = bundle / "authoring" / "traps.json"
    retained = {}
    if traps_path.is_file():
        try:
            previous = json.loads(traps_path.read_text())
            if previous.get("usable_corrections") is not None:
                retained["usable_corrections"] = previous["usable_corrections"]
        except (OSError, ValueError):
            retained = {}
    traps_path.write_text(json.dumps(
        {"source_tier": src.get("tier", 4), **retained, "traps": spec["traps"]},
        indent=2, ensure_ascii=False))

    # Clear the previous reference solution first. A rebuild names its
    # deliverable after the new design -- `hud-audit.json` where the last one
    # wrote `hud_register.json` -- and leaving both means `solution/submission/`
    # accumulates answers to questions this task no longer asks. Every probe
    # that stages `golden` copies the whole directory, so the stale file rides
    # along into each probe workspace, and anyone reading the bundle to work out
    # what the right answer IS finds two files and no way to tell which counts.
    submission = bundle / "solution" / "submission"
    if submission.is_dir():
        for stale in submission.iterdir():
            if stale.is_file():
                stale.unlink()
            elif stale.is_dir():
                shutil.rmtree(stale)

    for rel, content in spec.get("solution", {}).items():
        target = contained(bundle / "solution" / "submission", rel)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content if isinstance(content, str)
                          else json.dumps(content, indent=2, ensure_ascii=False))
    (bundle / "solution" / "README.md").write_text(spec.get("solution_notes", "") + "\n")

    (bundle / ".dockerignore").write_text(
        "tests/\nsolution/\nauthoring/\nverification/\nprovenance/\n")

    from .native_package import write_native
    write_native(spec, bundle)

    return {"bundle": str(bundle), "projections": len(projections),
            "checks": len(checks),
            "objectives": sum(1 for c in checks if c["kind"] == "objective"),
            "guardrails": sum(1 for c in checks if c["kind"] == "guardrail"),
            "traps": len(spec["traps"]), "steps": [s["name"] for s in steps]}


def main(argv: list[str] | None = None) -> int:
    import argparse
    ap = argparse.ArgumentParser(description="Stage F3 -- materialise a bundle")
    ap.add_argument("spec")
    ap.add_argument("-o", "--out", required=True)
    args = ap.parse_args(argv)
    spec = json.loads(Path(args.spec).read_text())
    report = build(spec, Path(args.out))
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
