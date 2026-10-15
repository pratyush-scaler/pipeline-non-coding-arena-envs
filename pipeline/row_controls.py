"""Controller-generated record counterexamples, independent of authored cases.

These are sampled structural probes, not proof of semantic correctness. Each
probe is executed by the exported grader; schema rejection is recorded separately
from a demonstrated objective or guardrail failure.
"""
from __future__ import annotations

import copy
from collections import Counter
from itertools import combinations
from pathlib import Path

from .author.checks import _dig, _hashable, normalise
from .author.contracts import schema_at, submission_errors
from .evaluate import exported_grade


def mutations(rows: list[dict]):
    if not rows:
        return
    yield "drop-row", rows[1:]
    yield "append-duplicate", [*rows, copy.deepcopy(rows[0])]
    if len(rows) < 2:
        return
    before = Counter(_hashable(normalise(row)) for row in rows)
    for left, right in combinations(range(len(rows)), 2):
        changed = copy.deepcopy(rows)
        changed[right] = copy.deepcopy(rows[left])
        if Counter(_hashable(normalise(row)) for row in changed) != before:
            yield "replace-with-duplicate", changed
            break
    for field in sorted(set.intersection(*(set(row) for row in rows))):
        for left, right in combinations(range(len(rows)), 2):
            changed = copy.deepcopy(rows)
            changed[left][field], changed[right][field] = changed[right][field], changed[left][field]
            # Swapping the sole varying field can merely reorder whole rows.
            if Counter(_hashable(normalise(row)) for row in changed) != before:
                yield "exchange-" + field, changed
                break


def run(bundle: Path, spec: dict, values: dict, checks: dict, root: Path) -> dict:
    from .assurance import case_values, stage
    outputs = {o["file"]: o for o in spec.get("outputs", [])}
    errors, results = [], {}
    collections = []
    for cid, check in checks.items():
        actual = check.get("actual", {})
        file, path = actual.get("file"), actual.get("path", "")
        if (actual.get("op") != "field" or file not in outputs or "[]" in path
                or check.get("assertion") not in {"equals", "set_equals", "multiset_equals"}):
            continue
        paths = [(path, cid)] + [(f"{path}.{nested}" if path else nested, f"{cid}.{nested}")
                                for nested in check.get("unordered_paths", [])]
        for selected, prefix in paths:
            schema = schema_at(outputs[file]["schema"], selected) or {}
            if schema.get("type") == "array" and schema.get("items", {}).get("type") == "object":
                collections.append((cid, check, file, selected, prefix))
    for cid, check, file, path, prefix in collections:
        rows = _dig(values[file], path)
        if not isinstance(rows, list) or any(not isinstance(row, dict) for row in rows):
            errors.append(f"{cid}: cannot exercise record controls on the reference")
            continue
        cases = [(name, value, False) for name, value in mutations(rows)]
        ordered = any(
            c.get("assertion") == "equals" and c.get("actual", {}).get("file") == file
            and (not c["actual"].get("path") or path == c["actual"]["path"]
                 or path.startswith(c["actual"]["path"] + "."))
            and path not in {f"{c['actual']['path']}.{nested}" if c['actual'].get('path') else nested
                             for nested in c.get('unordered_paths', [])}
            for c in checks.values())
        if (check["assertion"] in {"multiset_equals", "set_equals"} or check.get('unordered_paths')) and len(rows) > 1 and not ordered:
            cases.append(("allowed-row-reordering", list(reversed(rows)), True))
        for index, (name, value, correct) in enumerate(cases):
            case_id = f"{prefix}/{name}"
            changed = case_values({"patches": [{"file": file, "path": path, "value": value}]}, values)
            submitted = stage(root / prefix / str(index), changed)
            contract = submission_errors(submitted, list(outputs.values()))
            result = exported_grade(bundle, submitted, check["step"])
            record = result["checks"][cid]
            results[case_id] = {"correct_alternative": correct, "contract_errors": contract,
                "reward": result["reward"], "check": record,
                "guardrails_violated": result["guardrails_violated"]}
            if correct:
                if contract or result["reward"] != 1:
                    errors.append(f"{case_id}: allowed whole-row reordering must retain full credit")
            elif contract:
                if result["reward"] != 0:
                    errors.append(f"{case_id}: invalid record collection did not fail the public contract")
            elif record.get("passed") or record.get("gated_out"):
                errors.append(f"{case_id}: changed record association or multiplicity did not fail {cid}")
            elif check["kind"] == "guardrail" and (result["reward"] != 0 or cid not in result["guardrails_violated"]):
                errors.append(f"{case_id}: preservation violation did not trigger the guardrail")
    return {"errors": errors, "results": results,
            "scope": "Per collection: deletion, duplication, one distinct cell exchange per field, and allowed row reversal. Not exhaustive semantic validation."}
