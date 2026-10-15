"""Structural gates -- is this bundle even shaped like a deliverable?

Cheap, fast, and first in the chain: every later gate assumes these files exist
and parse. A bundle that fails here is not "a bit broken", it is unverifiable,
and the chain refuses rather than reporting on the parts it could read.
"""

from __future__ import annotations

import json
import tomllib
from pathlib import Path
from typing import Any

from .base import Finding, FunctionGate, GateContext, Severity

REQUIRED = (
    "task.toml",
    "tests/criteria.py",
    "tests/reward.toml",
    "tests/basis.toml",
    "tests/rubric.json",
    "provenance/ledger.json",
)


def _load_toml(path: Path) -> dict[str, Any]:
    with path.open("rb") as fh:
        return tomllib.load(fh)


def _structure(ctx: GateContext) -> tuple[list[Finding], dict]:
    findings: list[Finding] = []
    required = [r for r in REQUIRED
                if not (ctx.extras.get("legacy") and r == "provenance/ledger.json")]
    for rel in required:
        if not ctx.path(rel).exists():
            findings.append(Finding(Severity.BLOCKER, "missing-file",
                                    f"required file absent: {rel}", rel))
    if findings:
        return findings, {}

    task = _load_toml(ctx.path("task.toml"))
    evidence: dict[str, Any] = {}

    # schema_version 1.2 resolves to no tasks and harbor dies with "Either
    # datasets or tasks must be provided" -- a failure that looks like a task
    # defect and is a config defect.
    if str(task.get("schema_version")) != "1.4":
        findings.append(Finding(Severity.BLOCKER, "schema-version",
                                f"schema_version is {task.get('schema_version')!r}, "
                                "harbor needs \"1.4\"", "task.toml"))

    meta = task.get("metadata", {})
    for key in ("source_trace", "source_seeds"):
        if not meta.get(key):
            findings.append(Finding(Severity.BLOCKER, "no-provenance",
                                    f"[metadata].{key} is required -- a bundle must "
                                    "name the trace it came from", "task.toml"))

    # Spec E4: tools and actions defined with machine-readable schemas. A legacy
    # (pre-native) bundle is graded for comparison only and is not a package.
    if not ctx.extras.get("legacy"):
        from ..author.native_package import TOOL_SCHEMA, tool_schema_problems
        for problem in tool_schema_problems(ctx.task_dir):
            findings.append(Finding(Severity.BLOCKER, "tool-schema", problem, TOOL_SCHEMA))

    agent = task.get("agent", {})
    if agent.get("network_mode") != "no-network":
        findings.append(Finding(Severity.BLOCKER, "network",
                                "agent must run with network_mode = \"no-network\"; "
                                "the spec forbids live internet", "task.toml"))

    verifier = task.get("verifier", {})
    if verifier.get("environment_mode") != "separate":
        findings.append(Finding(Severity.BLOCKER, "shared-verifier",
                                "verifier environment_mode must be \"separate\": a "
                                "shared verifier puts the grader and its credential "
                                "inside the agent's environment", "task.toml"))

    env = task.get("environment", {})
    if (env.get("memory_mb") or 0) < 8192:
        findings.append(Finding(Severity.WARN, "memory",
                                f"memory_mb={env.get('memory_mb')}; a verifier parsing "
                                "a large state payload peaks at several times the "
                                "document and is OOM-killed with no score file",
                                "task.toml"))

    steps = task.get("steps") or []
    evidence["steps"] = [s.get("name") for s in steps]
    rubric = json.loads(ctx.path("tests/rubric.json").read_text())
    if steps:
        missing = [s.get("name") for s in steps if s.get("name") not in rubric]
        if missing:
            findings.append(Finding(Severity.BLOCKER, "rubric-step-mismatch",
                                    f"steps without a rubric entry: {missing}",
                                    "tests/rubric.json"))

    reward = _load_toml(ctx.path("tests/reward.toml"))
    blocks = reward.get("reward") or []
    if not blocks:
        findings.append(Finding(Severity.BLOCKER, "no-reward",
                                "reward.toml declares no [[reward]] block",
                                "tests/reward.toml"))
    for block in blocks:
        weights = block.get("weights") or {}
        evidence.setdefault("dimensions", sorted(weights))
        for dim in weights:
            if not ctx.path("tests", dim).is_dir():
                findings.append(Finding(Severity.BLOCKER, "missing-dimension",
                                        f"reward weights name '{dim}' but tests/{dim}/ "
                                        "does not exist", "tests/reward.toml"))
    return findings, evidence


def _ledger_shape(ctx: GateContext) -> tuple[list[Finding], dict]:
    """The faithfulness ledger must exist and account for every fixture file.

    Arena's headline finding on the last delivery was that roughly 80% of task
    content came from additions or omissions rather than the trace. That is not
    a defect in itself -- but it has to be *stated*, per element, rather than
    argued after the fact.
    """
    ledger = json.loads(ctx.path("provenance/ledger.json").read_text())
    entries = ledger.get("entries") or []
    findings: list[Finding] = []
    if not entries:
        return [Finding(Severity.BLOCKER, "empty-ledger",
                        "provenance/ledger.json has no entries",
                        "provenance/ledger.json")], {}

    from ..ledger.faithfulness import ORIGINS, share, build, measured_fields
    from ..ledger.anonymization import MANIFEST
    valid = set(ORIGINS)
    counts = {k: 0 for k in valid}
    for e in entries:
        origin = e.get("origin")
        if origin not in valid:
            findings.append(Finding(Severity.BLOCKER, "bad-origin",
                                    f"entry {e.get('path')!r} has origin {origin!r}; "
                                    f"must be one of {sorted(valid)}",
                                    "provenance/ledger.json"))
            continue
        counts[origin] += 1
        if origin in ("lifted", "anonymized", "derived") and not e.get("citation"):
            findings.append(Finding(Severity.BLOCKER, "uncited",
                                    f"{origin} entry {e.get('path')!r} carries no "
                                    "trace citation", "provenance/ledger.json"))

    # Arena 261011 (R20/R26/R32): several fixture files carrying one session file
    # need declared roles (original / copy / revision), or the source-change
    # comparison cannot be audited. Ledgers built now carry `carriers`; an older
    # ledger with shared citations is reported, not blocked.
    shared: dict[str, int] = {}
    for e in entries:
        cited = str(e.get("citation") or "").split("::", 2)
        if len(cited) == 3:
            shared[cited[2]] = shared.get(cited[2], 0) + 1
    multi = sorted(k for k, n in shared.items() if n > 1)
    if multi and "carriers" not in ledger:
        findings.append(Finding(Severity.WARN, "undeclared-carriers",
                                f"{len(multi)} session file(s) are carried by more than one fixture file with no "
                                f"declared original/copy/revision roles: {multi[:5]}",
                                "provenance/ledger.json"))

    total = sum(counts.values()) or 1
    faithfulness = share(counts)
    by_bytes = ledger.get("faithfulness_by_bytes", faithfulness)
    # Privacy credit is never trusted from a label or a retained receipt, even
    # when this gate is invoked without the full release evaluator.
    if counts["anonymized"] or ctx.path(MANIFEST).exists() or ledger.get("privacy_transformation"):
        try:
            if ledger.get("schema") != "arena-pipeline/ledger/3":
                raise ValueError("privacy transformations require ledger schema 3")
            source = ledger["source"]
            actual = build(ctx.task_dir, source["session_id"], source.get("seed_index"))
            if any(ledger.get(k) != actual[k] for k in measured_fields(ledger)):
                raise ValueError("privacy ledger differs from independently recovered provenance")
        except (OSError, ValueError, KeyError, TypeError, StopIteration, SystemExit) as exc:
            findings.append(Finding(Severity.BLOCKER, "unverified-anonymization", str(exc), MANIFEST))

    from ..author.scenario import MANIFEST as SCENARIO_MANIFEST
    if ctx.path(SCENARIO_MANIFEST).exists():
        try:
            source = ledger['source']
            actual = build(ctx.task_dir, source['session_id'], source.get('seed_index'))
            if any(ledger.get(k) != actual[k] for k in measured_fields(ledger)):
                raise ValueError('authored scenario ledger differs from independently recovered provenance')
        except (OSError, ValueError, KeyError, TypeError, StopIteration, SystemExit) as exc:
            findings.append(Finding(Severity.BLOCKER, 'unverified-authored-scenario', str(exc), SCENARIO_MANIFEST))

    # Spec T6: "Label invented data as synthetic." A fixture file the ledger
    # calls `authored` is invented data; only a verified scenario receipt puts
    # it under the public synthetic notice, so an undeclared one is unlabelled.
    from ..author.scenario import verify as verify_scenario
    try:
        declared_synthetic = set(verify_scenario(ctx.task_dir))
    except (OSError, ValueError, KeyError, TypeError):
        declared_synthetic = set()          # an unverifiable receipt labels nothing
    unlabelled = sorted(str(e.get("path")) for e in entries if e.get("origin") == "authored"
                        and e.get("path") not in declared_synthetic)
    if unlabelled:
        findings.append(Finding(
            Severity.BLOCKER, "unlabelled-synthetic",
            f"{len(unlabelled)} authored fixture file(s) are not declared in "
            f"{SCENARIO_MANIFEST}, so they carry no synthetic-data notice: {unlabelled[:5]}",
            "provenance/ledger.json"))

    # Gate against the SOURCE TIER's floor, not a flat number. A tier-1 trace has
    # the documents to lift; a tier-4 trace does not, and holding it to 90% would
    # only produce a bundle that misreports where its material came from.
    from ..select.priority import (CATEGORY_FIXTURE_FLOOR, FIXTURE_FLOOR_MIN,
                                   TIER_FIXTURE_FLOOR)
    tier = None
    for candidate in ("authoring/traps.json",):
        path = ctx.path(candidate)
        if path.exists():
            tier = json.loads(path.read_text()).get("source_tier")
            break
    if tier is None:
        findings.append(Finding(
            Severity.WARN, "no-source-tier",
            "no source_tier declared; the fixture-faithfulness floor is "
            "tier-dependent and cannot be applied", "authoring/traps.json"))
    else:
        # Category decides how much authoring is legitimate; tier only says how
        # rich the seed was. An F1/F0-target seed has no liftable workspace by
        # definition, so a tier floor of 95% would make the category
        # unbuildable. Where a category is declared it governs; otherwise fall
        # back to the tier floor, which is what every bundle built before
        # categories existed relies on.
        category = ledger.get("category")
        if category in CATEGORY_FIXTURE_FLOOR:
            floor = CATEGORY_FIXTURE_FLOOR[category]
            basis = f"category {category}"
        else:
            floor = max(TIER_FIXTURE_FLOOR.get(tier, FIXTURE_FLOOR_MIN),
                        FIXTURE_FLOOR_MIN)
            basis = f"tier-{tier} source"
        if by_bytes < floor:
            findings.append(Finding(
                Severity.WARN, "below-fixture-floor",
                f"{by_bytes:.0%} source fidelity, below the "
                f"{floor:.0%} floor for a {basis}. Verified privacy transformations "
                "retain source credit; other edits and synthesis remain discounted",
                "provenance/ledger.json"))

    fixture_dir = next((ctx.path("environment", n) for n in ("files", "fixtures")
                        if ctx.path("environment", n).is_dir()), None)
    if fixture_dir is not None:
        on_disk = {str(p.relative_to(fixture_dir))
                   for p in fixture_dir.rglob("*") if p.is_file()}
        declared = {e.get("path") for e in entries}
        if len(declared) != len(entries) or declared - on_disk:
            findings.append(Finding(Severity.BLOCKER, "ledger-inventory", "duplicate or missing fixture entries", "provenance/ledger.json"))
        if not ctx.extras.get("legacy"):
            import hashlib
            from ..author.contracts import contained
            byte_counts = {k: 0 for k in valid}
            for entry in entries:
                file = contained(fixture_dir, entry["path"])
                if file.is_file():
                    raw = file.read_bytes()
                    if entry.get("sha256") != hashlib.sha256(raw).hexdigest() or entry.get("bytes") != len(raw):
                        findings.append(Finding(Severity.BLOCKER, "ledger-bytes", f"{entry['path']}: ledger does not identify the actual bytes", "provenance/ledger.json"))
                    if entry.get("origin") in byte_counts:
                        byte_counts[entry["origin"]] += len(raw)
            actual_share = share(byte_counts)
            if ledger.get("faithfulness_by_bytes") != actual_share:
                findings.append(Finding(Severity.BLOCKER, "ledger-ratio", "faithfulness is not computed from fixture bytes", "provenance/ledger.json"))
            if ledger.get("schema") == "arena-pipeline/ledger/3":
                exact = round(byte_counts["lifted"] / (sum(byte_counts.values()) or 1), 3)
                if (ledger.get("exact_copy_by_bytes") != exact or
                        ledger.get("exact_copy_by_file") != round(counts["lifted"] / total, 3)):
                    findings.append(Finding(Severity.BLOCKER, "ledger-exact-copy", "exact-copy reuse is not computed from lifted files", "provenance/ledger.json"))
        undeclared = sorted(on_disk - declared)
        if undeclared:
            findings.append(Finding(Severity.BLOCKER, "unledgered-fixture",
                                    f"{len(undeclared)} fixture file(s) absent from the "
                                    f"ledger, e.g. {undeclared[:5]}",
                                    "provenance/ledger.json"))
    return findings, {"counts": counts, "faithfulness_by_file": faithfulness,
                      "faithfulness_by_bytes": by_bytes,
                      "exact_copy_by_bytes": ledger.get("exact_copy_by_bytes"), "source_tier": tier}


structure_gate = FunctionGate("bundle.structure", _structure)
ledger_gate = FunctionGate("bundle.ledger", _ledger_shape, requires=("bundle.structure",))
