"""Counterfactual source tests in private scratch, through the exported grader.

These variants are diagnostic controls, not new source-faithful task fixtures.
Changed reference answers are supplied independently of the target evaluator.
"""
from __future__ import annotations

import copy
import shutil
import tomllib
from pathlib import Path

from .author.contracts import contained, submission_errors
from .evaluate import exported_grade


def problems(spec: dict, bundle: Path) -> list[str]:
    quality = spec.get("quality", {})
    semantic = set(quality.get("semantic_checks", []))
    errors, coverage, ids = [], set(), set()
    cases = [(case, False) for case in quality.get("source_cases", [])]
    cases += [(case, True) for case in quality.get("source_invariants", [])]
    for case, invariant in cases:
        try:
            if (not isinstance(case.get("id"), str) or not case["id"] or case["id"] in ids
                    or case["id"].startswith("controller-") or "invariant" in case):
                raise ValueError("missing or duplicate source case ID")
            ids.add(case["id"])
            if invariant:
                if any(key in case for key in ("changes", "patches", "submission")) or not case.get("reason"):
                    raise ValueError("source invariance needs a reason and must preserve the complete answer")
                changes = set()
            else:
                changes = set(case["changes"])
                if not changes or changes - semantic or not case.get("reason"):
                    raise ValueError("source case needs a reason and semantic changes")
                if not case.get("patches") and not case.get("submission"):
                    raise ValueError("source case needs an independently specified corrected submission")
            patches = case.get("source_patches")
            if not isinstance(patches, list) or not patches:
                raise ValueError("source case needs source_patches")
            texts = {}
            for patch_index, patch in enumerate(patches):
                file = patch["file"]
                text = texts.setdefault(file, contained(bundle / "environment/files", file).read_text())
                old, new = patch["before"], patch["after"]
                if not isinstance(old, str) or not old or not isinstance(new, str) or old == new:
                    raise ValueError(f"source_patches[{patch_index}] ({file}): before and after must be different strings, with nonempty before")
                matches = text.count(old)
                if matches != 1:
                    raise ValueError(f"source_patches[{patch_index}] ({file}): source replacement must change exactly one existing span; found {matches} matches after preceding patches")
                texts[file] = text.replace(old, new, 1)
            coverage.update(changes)
        except (ValueError, KeyError, TypeError, OSError) as exc:
            errors.append(f"invalid source case {case.get('id', '<missing-id>')!r}: {exc}")
    if semantic - coverage:
        errors.append(f"source changes do not exercise semantic checks {sorted(semantic - coverage)}")
    return errors


def run(bundle: Path, spec: dict, values: dict, checks: dict, root: Path) -> dict:
    from .assurance import case_values, stage
    from .author.build import build
    # `problems` is the STATIC declaration check: does every semantic check have
    # a source case claiming to cover it. It used to return here, which meant one
    # undeclared check suppressed the execution of every control in the bundle --
    # and the gate reported only the static complaint, so nothing said the
    # counterfactuals had not run.
    #
    # Measured on a-439: control `SC2` had never once executed in the bundle's
    # history. It ran only after an unrelated fix cleared the pre-check, and then
    # turned out to rest on a premise a later design change had invalidated. Every
    # bundle behind a static gap has been reporting its checks proven while the
    # proof never ran, which is "SKIPPED is never green" in its purest form.
    #
    # The static findings still stand and still block; they simply no longer
    # decide whether the executed controls run.
    errors = problems(spec, bundle)
    results = {}
    names = [s["name"] for s in tomllib.loads((bundle / "task.toml").read_text())["steps"]]
    cases = [*spec.get("quality", {}).get("source_cases", []),
             *[{**case, "invariant": True} for case in spec.get("quality", {}).get("source_invariants", [])],
             {"id": "controller-final-newline", "invariant": True}]
    for index, case in enumerate(cases):
        cid = case["id"]
        try:
            variant = root / str(index) / bundle.name
            fixture = variant / "environment/files"
            shutil.copytree(bundle / "environment/files", fixture)
            if cid == "controller-final-newline":
                for path in fixture.rglob("*"):
                    if path.is_file():
                        try:
                            text = path.read_text()
                        except UnicodeError:
                            continue
                        path.write_text(text + "\n")
                changed = copy.deepcopy(values)
            else:
                for patch in case["source_patches"]:
                    path = contained(fixture, patch["file"])
                    path.write_text(path.read_text().replace(patch["before"], patch["after"], 1))
                changed = copy.deepcopy(values) if case.get("invariant") else case_values(case, values)
                if not case.get("invariant") and changed == values:
                    raise ValueError("changed evidence needs a different correct answer")
            contract = submission_errors(stage(root / str(index) / "corrected", changed), spec["outputs"])
            if contract:
                raise ValueError(f"counterfactual answer violates public contract: {contract}")
            revised = copy.deepcopy(spec)
            revised["solution"] = changed
            # Rebuilding binds the integrity guard to the scratch fixture. An
            # integrity failure cannot masquerade as a changed business decision.
            build(revised, variant)
            corrected = {name: exported_grade(variant, variant / "solution/submission", name) for name in names}
            if any(r["reward"] != 1 for r in corrected.values()):
                errors.append(f"{cid}: corrected source variant must score 1 on every step")
            stale = {}
            semantic = set(spec.get("quality", {}).get("semantic_checks", []))
            strict = spec.get("quality", {}).get("capability_plan", {}).get("version") == 2
            tested = semantic if strict and not case.get("invariant") else set(case.get("changes", []))
            observed = set()
            for check_id in sorted(tested):
                step = checks[check_id]["step"]
                if step not in stale:
                    stale[step] = exported_grade(variant, bundle / "solution/submission", step)
                record = stale[step]["checks"][check_id]
                if record.get("passed") is False and not record.get("gated_out") and not record.get("error"):
                    observed.add(check_id)
                integrity = {key for key, check in checks.items() if check.get("assertion") == "fixture_intact"}
                if check_id in case.get("changes", []) and (record.get("passed") or record.get("gated_out") or record.get("error")
                        or stale[step].get("contract_errors")
                        or integrity & set(stale[step].get("guardrails_violated", []))):
                    errors.append(f"{cid}: stale answer must fail {check_id} on its decision, without an integrity, contract or dependency failure")
                if strict and (record.get("gated_out") or record.get("error") or stale[step].get("contract_errors")
                               or integrity & set(stale[step].get("guardrails_violated", []))):
                    errors.append(f"{cid}: cannot establish intervention scope for {check_id} with a contract, integrity, grader or gated failure")
            if strict and not case.get("invariant") and observed != set(case.get("changes", [])):
                errors.append(f"{cid}: intervention changes {sorted(observed)}, not its declared exact scope {sorted(case.get('changes', []))}")
            results[cid] = {"corrected": corrected, "stale": stale,
                            "observed_semantic_changes": sorted(observed),
                            "exact_scope_checked": strict and not case.get("invariant"),
                            "invariant": case.get("invariant", False)}
        except (ValueError, KeyError, TypeError, OSError, RuntimeError) as exc:
            errors.append(f"{cid}: source control failed: {exc}")
    return {"errors": errors, "results": results,
            "scope": "Authored source counterfactuals, separately declared full-answer invariants, and controller newline invariance. Invariants never supply causal coverage. Scratch variants are not provenance-qualified tasks; semantic review remains required."}
