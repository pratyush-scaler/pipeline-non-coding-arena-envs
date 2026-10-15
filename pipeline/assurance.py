"""Executable controls over the exported verifier, including authored reasoning errors."""
from __future__ import annotations
import json
import re
import shutil
import tempfile
import tomllib
from pathlib import Path
from .artifacts import atomic_json, identity, inventory
from .author.contracts import contained, strict_json, submission_errors
from .evaluate import exported_grade


def generated_problems(bundle: Path) -> list[str]:
    """Rebuild in private scratch to prove exported files implement the reviewed spec."""
    from .author.build import build
    before = inventory(bundle)
    # Frozen qualification snapshots may have a different directory name. The
    # package's declared ID, not its storage location, controls the export name.
    declared = tomllib.loads((bundle / "task.toml").read_text())
    task_name = declared.get("task", {}).get("name", "")
    match = re.fullmatch(r"arena/([A-Za-z0-9_-]+)", task_name)
    export_name = match[1] if match else bundle.name
    with tempfile.TemporaryDirectory(prefix="arena-reproduce-") as tmp:
        expected = Path(tmp) / export_name
        shutil.copytree(bundle / "environment/files", expected / "environment/files")
        build(strict_json((bundle / "authoring/spec.json").read_text()), expected)
        # A delivered task carries delivery's rename and level stamp. Re-derive
        # that rewrite with the one function `deliver` uses, so the comparison
        # stays exact: every delivered bundle otherwise fails its own gate.
        from .naming import LEVEL_KEY, delivered_toml
        level = declared.get("metadata", {}).get(LEVEL_KEY)
        if level and match:
            toml = expected / "task.toml"
            toml.write_text(delivered_toml(toml.read_text(), task_name, level))
        def generated(files):
            return {k: v for k, v in files.items() if not k.startswith("provenance/") and k != "authoring/traps.json"}
        actual, wanted = generated(before), generated(inventory(expected))
        changed = sorted(k for k in actual.keys() | wanted.keys() if actual.get(k) != wanted.get(k))
    if inventory(bundle) != before:
        changed.append("task changed during reproduction")
    return [f"export differs from reviewed spec/generator: {p}" for p in changed]


def case_values(case: dict, reference: dict) -> dict:
    """Small explicit replacement patches avoid repeating large reference tables."""
    import copy
    if "submission" in case:
        if "patches" in case:
            raise ValueError("a control must use submission or patches, not both")
        return case["submission"]
    values = copy.deepcopy(reference)
    patches = case.get("patches")
    if not isinstance(patches, list) or not patches:
        raise ValueError("control needs a complete submission or nonempty replacement patches")
    for patch in patches:
        file, path = patch["file"], patch["path"]
        if file not in values or not isinstance(path, str) or not path:
            raise ValueError("patch must address an existing output field")
        doc = values[file]
        if isinstance(doc, str):
            doc = values[file] = strict_json(doc)
        parts = path.split(".")
        cur = doc
        for token in parts[:-1]:
            cur = cur[int(token)] if isinstance(cur, list) else cur[token]
        last = int(parts[-1]) if isinstance(cur, list) else parts[-1]
        _ = cur[last]  # Replacements cannot invent fields or grow an array.
        cur[last] = copy.deepcopy(patch["value"])
    return values


def stage(root: Path, values: dict) -> Path:
    root.mkdir(parents=True)
    for rel, value in values.items():
        path = contained(root, rel)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(value if isinstance(value, str) else json.dumps(value, ensure_ascii=False))
    return root


def control_problems_after_gates(bundle: Path, gate_report: dict) -> list[str]:
    """Reuse only the just-executed gate's proof for this unchanged implementation."""
    from .artifacts import policy_identity
    rows = [row for row in gate_report.get("results", []) if row.get("gate") == "quality.controls"]
    if (gate_report.get("schema") == "arena-pipeline/gate-report/1"
            and gate_report.get("verdict") == "green" and len(rows) == 1):
        row = rows[0]
        evidence = row.get("evidence") or {}
        if (row.get("status") == "pass" and not row.get("blockers") and not row.get("error")
                and evidence.get("schema") == "arena-pipeline/controls/1"
                and evidence.get("ok") is True and evidence.get("errors") == 0
                and evidence.get("artifact_sha256") == identity(bundle)
                and evidence.get("policy_sha256") == policy_identity()):
            return []
    report = controls(bundle)
    errors = list(report.get("errors") or [])
    if report.get("ok") is not True and not errors:
        errors.append("exported control execution is not verified")
    return errors


def controls(bundle: Path) -> dict:
    before = identity(bundle)
    spec = strict_json((bundle / "authoring/spec.json").read_text())
    names = [s["name"] for s in tomllib.loads((bundle / "task.toml").read_text())["steps"]]
    outputs = spec.get("outputs", [])
    rubric = strict_json((bundle / "tests/rubric.json").read_text())
    checks = {c["id"]: c for c in strict_json((bundle / "tests/checks.json").read_text())["checks"]}
    errors, results = [], {}
    with tempfile.TemporaryDirectory(prefix="arena-controls-") as tmp:
        root = Path(tmp)
        empty = stage(root / "empty", {})
        ref = bundle / "solution/submission"
        values = {o["file"]: strict_json(contained(ref, o["file"]).read_text()) for o in outputs}
        if not outputs:
            errors.append("controls require public output contracts")
        cumulative = {}
        for name in names:
            cumulative.update({o["file"]: values[o["file"]] for o in outputs if o["step"] == name})
            current = stage(root / name / "reference", cumulative)
            result = exported_grade(bundle, current, name)
            results[f"{name}/reference"] = result
            if result["reward"] != 1:
                errors.append(f"{name}: complete public-contract reference must score 1")
            untouched = exported_grade(bundle, empty, name)
            results[f"{name}/empty"] = untouched
            if untouched["reward"] != 0 or untouched["guardrails_violated"] or any(
                r.get("passed") for cid, r in untouched["checks"].items() if checks[cid]["kind"] == "objective"):
                errors.append(f"{name}: untouched workspace must fail every objective and pass every guardrail")
            # Each declared output is load-bearing; deleting it must lose reward.
            for o in (v for v in outputs if v["step"] == name):
                saved = contained(current, o["file"]).read_bytes()
                contained(current, o["file"]).unlink()
                missing = exported_grade(bundle, current, name)
                if missing["reward"] != 0 or not missing.get("contract_errors"):
                    errors.append(f"{name}/{o['file']}: missing required output did not fail the contract")
                contained(current, o["file"]).write_bytes(saved)
            source = root / name / "tampered"
            shutil.copytree(bundle / "environment/files", source)
            victim = next(p for p in source.rglob("*") if p.is_file())
            victim.write_bytes(victim.read_bytes() + b"\nunauthorized change\n")
            tampered = exported_grade(bundle, current, name, source)
            results[f"{name}/fixture_changed"] = tampered
            if tampered["reward"] != 0 or not tampered["guardrails_violated"]:
                errors.append(f"{name}: changing source bytes must fire an integrity guardrail")
        covered, case_ids, staged_values = set(), set(), {}
        for kind in ("counterexamples", "alternatives"):
            for index, case in enumerate(spec.get("quality", {}).get(kind, [])):
                cid = case.get("id", f"{kind}-{index}")
                if cid in case_ids:
                    errors.append(f"duplicate assurance case ID {cid}")
                case_ids.add(cid)
                submitted_values = case_values(case, values)
                staged_values[cid] = submitted_values
                submitted = stage(root / kind / str(index), submitted_values)
                contract_errors = submission_errors(submitted, outputs)
                if contract_errors:
                    errors.append(f"{cid}: a reasoning control must satisfy the public serialization contract: {contract_errors}")
                all_results = {name: exported_grade(bundle, submitted, name) for name in names}
                results[cid] = all_results
                if kind == "alternatives":
                    if submitted_values == values:
                        errors.append(f"{cid}: alternative is identical to the reference")
                    if any(r["reward"] != 1 for r in all_results.values()):
                        errors.append(f"{cid}: independently phrased correct solution must score 1 on every step")
                else:
                    for failed in case.get("fails", []):
                        selected = [r["checks"][failed] for r in all_results.values() if failed in r["checks"]]
                        if not selected or any(r.get("passed") or r.get("gated_out") for r in selected):
                            errors.append(f"{cid}: intended reasoning error did not fail {failed}")
                        else:
                            covered.add(failed)
                    if all(r["reward"] == 1 for r in all_results.values()):
                        errors.append(f"{cid}: wrong solution received full reward")
        baseline_results = {}
        plan = spec.get("quality", {}).get("capability_plan") or {}
        for index, baseline in enumerate(plan.get("tool_baselines") or []):
            if not isinstance(baseline, dict) or "submission" not in baseline:
                continue
            identifier = baseline.get("id", f"baseline-{index}")
            if not isinstance(identifier, str) or identifier in baseline_results:
                errors.append("tool baselines require distinct string identifiers")
                continue
            submitted_values = baseline["submission"]
            if not isinstance(submitted_values, dict) or set(submitted_values) != set(values):
                errors.append(f"tool baseline {identifier}: supply exactly the complete public outputs for every step")
                continue
            submitted = stage(root / "tool-baselines" / str(index), submitted_values)
            if contract_errors := submission_errors(submitted, outputs):
                errors.append(f"tool baseline {identifier}: serialization is not a capability failure: {contract_errors}")
                continue
            graded = {name: exported_grade(bundle, submitted, name) for name in names}
            failed = sorted({check_id for result in graded.values()
                             for check_id, row in result["checks"].items()
                             if checks[check_id]["kind"] == "objective" and not row.get("passed")})
            declared = baseline.get("fails")
            if (not isinstance(declared, list) or any(not isinstance(check, str) for check in declared)
                    or len(set(declared)) != len(declared) or set(declared) != set(failed)):
                errors.append(f"tool baseline {identifier}: declared failures do not match complete executed outputs: {failed}")
            if any(result.get("contract_errors") or result.get("guardrails_violated")
                   or any(row.get("gated_out") for row in result["checks"].values()) for result in graded.values()):
                errors.append(f"tool baseline {identifier}: invalid or gated controls cannot establish semantic capability failures")
            results[f"tool-baseline/{identifier}"] = graded
            baseline_results[identifier] = {"kind": baseline.get("kind"), "observed_failures": failed,
                                            "passes_all_steps": all(result["reward"] == 1 for result in graded.values()),
                                            "method_requires_independent_review": True,
                                            "native_model_measurement": False}
        # Every objective must be shown to fail a substantive wrong solution,
        # executed through the shipped grader -- not only the checks declared
        # semantic. An objective nothing wrong can fail is a dead check.
        # A misreading's counterexample must fail ONLY what its trap drives:
        # every other objective passes when the wrong answer is graded. That is
        # what shows the loss comes from THIS misreading and not from a
        # submission that is wrong everywhere (the self-audit's static check
        # is `quality.difficulty_case_problems`; this is its execution).
        case = spec.get("quality", {}).get("difficulty_case") or {}
        traps = {t.get("id"): t for t in spec.get("traps") or [] if isinstance(t, dict)}
        encoded = {}
        for entry in case.get("misreadings") or []:
            if not isinstance(entry, dict):
                continue
            trap, graded = traps.get(entry.get("trap")), results.get(entry.get("counterexample"))
            if trap is None or not isinstance(graded, dict):
                continue
            # The graded submission, not the declared one: two ids whose staged
            # workspaces are identical are one wrong answer under two names.
            staged = json.dumps(staged_values.get(entry.get("counterexample")), sort_keys=True, default=str)
            twin = encoded.get(staged)
            if twin and twin[0] != trap.get("id") and twin[1] != entry.get("counterexample"):
                errors.append(f"misreading of trap {trap.get('id')}: its counterexample "
                              f"{entry.get('counterexample')} grades the same submission as "
                              f"{twin[1]} (trap {twin[0]}); every trap needs its own wrong answer")
            encoded.setdefault(staged, (trap.get("id"), entry.get("counterexample")))
            objective_rows = [row for step in graded.values()
                              for cid, row in (step.get("checks") or {}).items()
                              if checks.get(cid, {}).get("kind") == "objective"]
            if objective_rows and not any(row.get("passed") for row in objective_rows):
                errors.append(f"misreading of trap {trap.get('id')}: its counterexample "
                              f"{entry.get('counterexample')} passes no objective when graded -- "
                              "a misreading agrees with the correct answer outside its trap, so "
                              "an all-wrong submission shows nothing about this trap")
            else:
                from .policy import MISREADING_MAX_OBJECTIVE_SHARE as share
                lost = [row for row in objective_rows
                        if not row.get("passed") and not row.get("gated_out")]
                if objective_rows and len(lost) > share * len(objective_rows):
                    errors.append(f"misreading of trap {trap.get('id')}: its counterexample "
                                  f"{entry.get('counterexample')} fails {len(lost)} of "
                                  f"{len(objective_rows)} objectives when graded; a misreading "
                                  f"may lose at most {share:.0%} of them")
            driven = set(trap.get("checks") or [])
            stray = sorted({cid for step in graded.values()
                            for cid, row in (step.get("checks") or {}).items()
                            if checks.get(cid, {}).get("kind") == "objective" and cid not in driven
                            and not row.get("passed") and not row.get("gated_out")})
            if stray:
                errors.append(f"misreading of trap {trap.get('id')}: its counterexample "
                              f"{entry.get('counterexample')} also fails {stray}, which the trap "
                              "does not drive -- the loss is not shown to come from this misreading")
        required = set(spec.get("quality", {}).get("semantic_checks", [])) | {
            cid for cid, c in checks.items() if c["kind"] == "objective"} | {
            cid for cid, c in checks.items() if c["kind"] == "guardrail" and c["assertion"] != "fixture_intact"}
        if required - covered:
            errors.append(f"no demonstrated counterexample for {sorted(required - covered)}")
        from .row_controls import run as row_controls
        independent = row_controls(bundle, spec, values, checks, root / "independent-rows")
        errors.extend(independent["errors"])
        from .source_controls import run as source_controls
        source_results = source_controls(bundle, spec, values, checks, root / "source-cases")
        errors.extend(source_results["errors"])
    if identity(bundle) != before:
        errors.append("task changed during control execution")
    # v2 (user, 2026-10-02): misreading-shape and tool-baseline rules are the
    # self-audit's bookkeeping, not validity; they are reported, never blocking.
    from .advisory import split
    errors, advisories = split(errors)
    report = {"schema": "arena-pipeline/controls/1", "artifact_sha256": before,
              "ok": not errors, "errors": errors, "advisories": advisories, "results": results,
              "tool_baselines": baseline_results,
              "independent_row_controls": independent, "source_controls": source_results}
    atomic_json(bundle / "verification/controls.json", report)
    return report
