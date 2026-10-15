"""A reference solution that computes the answer instead of printing it.

Spec, "Deliverables": "Reference solution - a **scripted** solution included in
the package that scores full marks when run through the grader."

What shipped instead was `solution/submission/answer.json`, a stored answer, and
an oracle script that was one line:

    cp -R /solution/submission/. /app/deliverables/          native_package.py

Two independent authorities reject that. The spec asks for a script. And
Harbor's own quality rubric -- the one `harbor check` runs, which the spec makes
a 100%-of-tasks batch criterion -- has a criterion named `hardcoded_solution`:

    "FAIL when the solution simply prints or writes the final answer without
     computation ... PASS if it derives the answer via a process."

A copy of a stored file is the definition of the failing case, so every task we
ship would have failed that criterion.

The fix is available because of a decision made much earlier: targets in this
pipeline are *expressions over the fixture*, not typed-in values, and the
projection layer that feeds them is a registry of reviewed parsers. So a
reference solution can do exactly what a careful professional would:

    1. read the published fixture
    2. project it through the declared parsers
    3. evaluate each objective's declared target expression
    4. assemble the results into the published output schema

That is a derivation, and it reads as one. Nothing is looked up, and the script
would produce a different (correct) answer against a different fixture -- which
is the property `hardcoded_solution` is really asking about, and the property a
stored file can never have.

The solution directory is excluded from the agent image by `.dockerignore` and
is mounted only for Harbor's OracleAgent, so shipping the target expressions
here leaks nothing to a solver.
"""
from __future__ import annotations

import json
from pathlib import Path

#: Runtime modules the solve script needs, staged beside it as a package by
#: `runtime.stage` -- the same helper, and the same file list, that stages the
#: verifier's copy. Two lists drifted once; there is one now.
from .runtime import PACKAGE as RUNTIME_PACKAGE, FILES as RUNTIME  # noqa: E402

SOLVE_PY = """#!/usr/bin/env python3
\"\"\"Reference solution -- derives every answer from the published fixture.

Run by Harbor's OracleAgent. Not present in the agent image.

This does not contain the answers. It contains the *derivation*: the same
parsers and the same target expressions the grader uses, evaluated here against
the same published fixture the solver was given. Pointed at a different fixture
it computes a different, correct answer.

    fixture -> parsers -> projected rows -> target expressions -> deliverables
\"\"\"
import json
import os
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from _arena_runtime import oracle            # noqa: E402  reviewed parsers
from _arena_runtime import checks_runtime as checks  # noqa: E402  evaluator

# The container paths, overridable so the offline gate can run these exact
# bytes against a scratch copy of the fixture.
FIXTURE = Path(os.environ.get("ARENA_SOURCE", "/app/environment/files"))
DELIVERABLES = Path(os.environ.get("ARENA_SUBMITTED", "/app/deliverables"))
STEP = {step!r}


def main() -> int:
    plan = json.loads((HERE / "solution-plan.json").read_text())

    # ------------------------------------------------------------------
    # 1. Project the fixture. Each parser is a named, reviewed reader --
    #    `csv_table`, `markdown_tables`, `jsonl_records` -- turning a
    #    published document into rows. Nothing here reads the submission.
    #    The rows go to a temporary directory: /solution may be mounted
    #    read-only.
    # ------------------------------------------------------------------
    with tempfile.TemporaryDirectory(prefix="arena-reference-") as tmp:
        work = Path(tmp) / "derived"
        oracle.write(oracle.project(FIXTURE, plan["projections"]), work)
        workspace = checks.Workspace(
            source=FIXTURE, submitted=DELIVERABLES, derived=work,
            projections=plan["projections"], step=STEP)

        # --------------------------------------------------------------
        # 2. Evaluate each objective's declared target against those rows.
        #    This is the professional work: the comparisons, the
        #    arbitration between conflicting sources, the arithmetic. The
        #    expression is the specification of that work, not a record of
        #    its result. `assign_path` is the exact inverse of the path
        #    reader the grader uses, `a[].b` included.
        # --------------------------------------------------------------
        documents = {{}}
        for objective in plan["objectives"]:
            value = checks.evaluate(objective["target"], workspace, "source")
            if objective.get("assertion") == "optimal_path":
                from _arena_runtime import path_witness
                value = path_witness.reference_witness(path_witness.prepare(value), objective.get("witness_schema"))
            elif objective.get("assertion") == "optimal_subset":
                from _arena_runtime import subset_witness
                value = subset_witness.reference_witness(subset_witness.prepare(value), objective.get("witness_schema"))
            slot = documents.setdefault(objective["file"], {{}})
            documents[objective["file"]] = checks.assign_path(slot, objective["path"], value)

    # ------------------------------------------------------------------
    # 3. Write the deliverables the assignment names, in the published
    #    schema. Fields the rubric does not score still have to exist if
    #    the schema requires them; `defaults` carries those.
    # ------------------------------------------------------------------
    DELIVERABLES.mkdir(parents=True, exist_ok=True)
    for file, defaults in plan["documents"].items():
        body = {{**defaults, **documents.get(file, {{}})}}
        out = DELIVERABLES / file
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(body, ensure_ascii=False, indent=2) + "\\n",
                       encoding="utf-8")
        print(f"wrote {{out}} ({{len(body)}} top-level fields)", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
"""

SOLVE_SH = '''#!/bin/sh
# Reference solution. Derives the answer from the published fixture; it does
# not copy a stored one. See solve.py.
set -eu
mkdir -p /app/deliverables
python3 /solution/solve.py
'''


def plan(spec: dict, step: str) -> dict:
    """What the solve script needs: projections, targets, and the schema shape.

    Guardrails are deliberately excluded. A guardrail enforces a negative
    obligation -- "do not modify the sources" -- and the reference satisfies it
    by not doing the thing, never by writing something.
    """
    # A single-step task leaves `step` unset on its checks -- there is only one
    # place they could belong. Filtering on equality alone drops every objective
    # in such a bundle and silently produces a reference solution that writes
    # nothing, which would then fail its own grader for the wrong reason.
    steps = [s["name"] for s in spec.get("steps", []) if s.get("name")]
    single = len(steps) <= 1

    objectives: list[dict] = []
    undeliverable: list[dict] = []
    for check in spec.get("checks", []):
        if check.get("kind") != "objective":
            continue
        owner = check.get("step")
        if owner != step and not (owner is None and single):
            continue
        actual = check.get("actual") or {}
        if actual.get("op") != "field" or not actual.get("file"):
            # A check reading something other than a submission field cannot be
            # satisfied by assembling a document; the reference has to be told.
            undeliverable.append({"id": check["id"],
                                  "reason": "does not read a submission field"})
            continue
        path = str(actual.get("path", ""))
        if _unassignable(path):
            # `a[].b` and `a.0.b` are fine: `checks.assign_path` inverts the
            # grader's own reader for both. Marking every `[]` path
            # undeliverable left the stored reference to spell them itself,
            # and it wrote literal `shared_publications[]` keys the grader
            # could not read -- golden 1.0 in probes, 0.1587 as shipped.
            #
            # The deliverable's *extension* is deliberately not consulted. Some
            # sound bundles write JSON to a file not named `.json`, and filtering
            # on the name took one such task from 1.000 to 0.000.
            undeliverable.append({
                "id": check["id"], "file": actual["file"], "path": path,
                "reason": f"path {path!r} is not one the grader's path reader "
                          "can read back from an assigned value"})
            continue
        if "target" not in check:
            # `assertion: present` and friends assert a field exists without
            # saying what it should contain. There is nothing to evaluate, so
            # the generated reference cannot fill it and must say so rather than
            # write a plausible-looking value into an unscored slot or crash.
            undeliverable.append({
                "id": check["id"], "file": actual["file"],
                "path": actual.get("path", ""),
                "reason": f"assertion {check.get('assertion', '?')!r} declares no "
                          "target expression, so the answer cannot be derived"})
            continue
        objectives.append({"id": check["id"], "file": actual["file"],
                           "path": actual.get("path", ""),
                           "target": check["target"]})
        if check.get("assertion") in ("optimal_path", "optimal_subset"):
            from .contracts import schema_at
            output = next((entry for entry in spec.get("outputs", []) if entry["file"] == actual["file"]), {})
            objectives[-1].update(assertion=check["assertion"],
                                  witness_schema=schema_at(output.get("schema", {}), actual.get("path", "")))

    documents: dict[str, dict] = {}
    for output in spec.get("outputs") or []:
        if output.get("step") not in (step, None) and not single:
            continue
        documents.setdefault(output["file"], _schema_defaults(output.get("schema")))
    for objective in objectives:
        documents.setdefault(objective["file"], {})

    return {"schema": "arena-pipeline/solution-plan/1", "step": step,
            "projections": spec.get("projections", []),
            "objectives": objectives, "documents": documents,
            # Named, not silently dropped: a reference that covers nine of ten
            # objectives scores nine tenths, and the missing tenth has to be
            # visible as a gap rather than as an unexplained grader failure.
            "undeliverable": undeliverable}


def _unassignable(path: str) -> bool:
    """Would `assign_path` refuse this path outright, whatever the value?"""
    from .checks import path_parts
    if "(" in path or ")" in path:
        return True
    parts = path_parts(path)
    return any(not (p[:-2] if p.endswith("[]") else p) or "[" in (p[:-2] if p.endswith("[]") else p)
               or "]" in (p[:-2] if p.endswith("[]") else p) for p in parts)


def _schema_defaults(schema: dict | None) -> dict:
    """Required fields no objective fills, so the document validates.

    An empty container rather than an invented value: a field the rubric does
    not score must still be present when the schema demands it, but writing a
    plausible-looking value into an unscored field is how a reference solution
    starts quietly documenting things nobody checked.
    """
    if not isinstance(schema, dict):
        return {}
    out = {}
    properties = schema.get("properties") or {}
    for name in schema.get("required") or []:
        kind = (properties.get(name) or {}).get("type")
        out[name] = ([] if kind == "array" else {} if kind == "object"
                     else "" if kind == "string" else 0 if kind in ("number", "integer")
                     else False if kind == "boolean" else None)
    return out


def stage(bundle: Path, spec: dict, step: str, dest: Path) -> dict:
    """Write a runnable, deriving reference solution into `dest`.

    Called by `native_package` in place of the copy it used to write.
    """
    bundle, dest = Path(bundle), Path(dest)
    dest.mkdir(parents=True, exist_ok=True)

    from . import runtime
    runtime.stage(dest / RUNTIME_PACKAGE)

    document = plan(spec, step)
    (dest / "solution-plan.json").write_text(
        json.dumps(document, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    solve_py = dest / "solve.py"
    solve_py.write_text(SOLVE_PY.format(step=step), encoding="utf-8")
    solve_py.chmod(0o755)

    solve_sh = dest / "solve.sh"
    solve_sh.write_text(SOLVE_SH, encoding="utf-8")
    solve_sh.chmod(0o755)

    return {"step": step, "objectives": len(document["objectives"]),
            "documents": sorted(document["documents"]),
            "undeliverable": document["undeliverable"],
            "derives": True}


def coverage_problems(bundle: Path) -> list[str]:
    """Objectives the generated reference cannot fill.

    A reference that covers most objectives scores most of the marks, and a
    grader-sanity check then reports "reference scored 0.24" -- which reads as a
    broken grader. It is not: it is a reference the generator could not write.
    Saying so is the difference between a known gap and a mystery.
    """
    issues = []
    for plan_path in sorted(Path(bundle).glob("steps/*/solution/solution-plan.json")):
        try:
            document = json.loads(plan_path.read_text())
        except (OSError, ValueError) as exc:
            issues.append(f"{plan_path.parent.name}: unreadable solution plan: {exc}")
            continue
        missing = document.get("undeliverable") or []
        if missing:
            step = plan_path.parent.parent.name
            issues.append(
                f"{step}: the generated reference cannot derive "
                f"{len(missing)} objective(s) "
                f"({', '.join(m['id'] for m in missing[:3])}"
                f"{', …' if len(missing) > 3 else ''}), so it cannot score full "
                "marks. Write the reference for this step by hand, or reshape "
                "the deliverable so every scored field is a JSON path")
    return issues


def problems(bundle: Path) -> list[str]:
    """Is the shipped reference a derivation, or a copy of a stored answer?

    Mirrors Harbor's `hardcoded_solution` criterion so we find this ourselves
    rather than reading it in Arena's review.
    """
    bundle = Path(bundle)
    issues = []
    scripts = sorted(bundle.glob("steps/*/solution/solve.sh"))
    if not scripts:
        return ["no reference solution script; the spec asks for a scripted "
                "solution that scores full marks through the grader"]
    for script in scripts:
        body = script.read_text(errors="replace")
        # A solve.py beside a solve.sh that copies does not make it a
        # derivation: the copy is what runs. Judge the script that executes.
        copies = ("cp " in body or "cp -R" in body or "rsync" in body)
        if copies:
            issues.append(
                f"{script.relative_to(bundle)} copies a stored answer into the "
                "deliverables instead of computing it. Harbor's "
                "`hardcoded_solution` criterion fails exactly this, and the spec "
                "asks for a scripted solution")
    issues += coverage_problems(bundle)
    # Looking like a derivation is not scoring like one. Both runtime copies
    # must be the current generator's, and the script the container runs is
    # executed offline and graded by the shipped grader: 1.0 per step or block.
    from . import runtime
    from ..verify_shipped import run_reference
    issues += runtime.problems(bundle)
    if not any("copies a stored answer" in i for i in issues):
        issues += run_reference(bundle)["problems"]
    return issues
