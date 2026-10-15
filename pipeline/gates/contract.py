"""Contract probe: does the grader that ships do what the published contract says?

Arena's 260927 feedback found three graders that disagreed with their own
instruction: reversed lists the instruction ordered earned full credit, a list
with a repeated heading earned full credit, and a guardrail zeroed a step for
one wrong date though nothing had been edited. None was visible in the check
data alone; each shows the moment the reference answer is minimally changed
and graded. This gate does exactly that, with the exported grader, so what it
certifies is what Harbor will run.

Per objective field of the reference answer it grades:
  - every list reversed: must fail, unless the contract declares the list
    unordered (`validate.order_declaration`, shared with T3b), then must pass;
  - every list with its first entry repeated, and with its last entry dropped:
    must lose credit;
  - one integer changed by one: may fail its objective, never a guardrail.

It also reports two text patterns a check cannot see -- a section that asks
for work but names no field, and a claim that two sources agree -- as
warnings for the semantic review, since only a reader can settle them.
"""
from __future__ import annotations

import copy
import json
import re
import tempfile
from pathlib import Path

from .base import Finding, FunctionGate, GateContext, Severity

#: Grades per bundle. Each is a clean subprocess of the exported grader; the
#: evidence records which fields were left unprobed when the budget runs out.
MAX_GRADES = 80
#: Mutations per array. Reversal, repetition and omission, in that order.
KINDS = ("reversed", "repeated", "dropped")

_WORK = re.compile(r"(?:^|(?<=[.:;]\s))(?:Measure|Count|Compute|Calculate|List|Report|Identify|Determine|"
                   r"Rank|Tally|Sum|Find|Work out|Establish)\b[^.]*\.", re.M)
_RESTRICTION = re.compile(r"\b(?:only|no|never|every date)\b", re.I)
_AGREEMENT = re.compile(r"\b(?:holds?|carr(?:y|ies)|has|have) the same words\b|\bidentical (?:word )?counts?\b"
                        r"|\bagree on every (?:count|figure|number)\b|\bsame (?:word count|length|number of words)\b", re.I)


def _arrays(value, trail=()):
    """(path, list) for every list inside value; path mixes keys and indices."""
    if isinstance(value, list):
        yield trail, value
        for i, item in enumerate(value):
            yield from _arrays(item, trail + (i,))
    elif isinstance(value, dict):
        for key, item in value.items():
            yield from _arrays(item, trail + (key,))


def _mutated(value, trail, kind):
    arr = value
    for part in trail:
        arr = arr[part]
    if kind == "reversed":
        new = list(reversed(arr))
        if new == arr:
            return None
    elif kind == "repeated":
        if not arr:
            return None
        new = arr + arr[:1]
    else:
        if not arr:
            return None
        new = arr[:-1]
    if not trail:
        return new
    out = copy.deepcopy(value)
    cur = out
    for part in trail[:-1]:
        cur = cur[part]
    cur[trail[-1]] = new
    return out


def _dig(doc, path):
    for part in path.split(".") if path else []:
        if not isinstance(doc, dict) or part not in doc:
            return None
        doc = doc[part]
    return doc


def _put(doc, path, value):
    parts = path.split(".")
    for part in parts[:-1]:
        doc = doc[part]
    doc[parts[-1]] = value


def _schema_path(path: str, trail) -> str:
    """`contracts.schema_at` form: a list index becomes `[]` on the key above it."""
    tokens = [t for t in path.split(".") if t] if path else []
    for part in trail:
        if isinstance(part, int):
            if tokens and not tokens[-1].endswith("[]"):
                tokens[-1] += "[]"
        else:
            tokens.append(part)
    return ".".join(tokens)


def _first_integer(value, trail=()):
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return trail
    if isinstance(value, dict):
        for key, item in value.items():
            found = _first_integer(item, trail + (key,))
            if found is not None:
                return found
    return None


def _text_warnings(spec: dict) -> list[Finding]:
    from ..author.contracts import compile_steps
    try:
        steps = compile_steps(copy.deepcopy(spec))
    except Exception:
        return []
    keys = set()

    def walk(node):
        if isinstance(node, dict):
            for key, sub in (node.get("properties") or {}).items():
                keys.add(key)
                walk(sub)
            walk(node.get("items"))
    for output in spec.get("outputs") or []:
        walk(output.get("schema"))
    found = []
    for step in steps:
        body = re.sub(r"```.*?```", "", step.get("instruction") or "", flags=re.S)
        for m in re.finditer(r"(?m)^([A-Z][A-Z \-']{3,60})\.\s+", body):
            end = body.find("\n\n", m.start())
            para = body[m.start(): end if end > 0 else len(body)]
            named = [k for k in keys if re.search(r"(?<![\w])%s(?![\w])" % re.escape(k), para)]
            work = [w.group(0) for w in _WORK.finditer(para) if not _RESTRICTION.search(w.group(0))]
            if work and not named:
                found.append(Finding(
                    Severity.WARN, "unscored-section",
                    f"section {m.group(1)!r} asks for work ({work[0][:80]!r}) but names no deliverable "
                    "field; a requirement nothing scores misleads the solver -- the semantic review must "
                    "confirm it is scored or remove it", step["name"]))
        for m in _AGREEMENT.finditer(body):
            found.append(Finding(
                Severity.WARN, "agreement-claim",
                f"the instruction asserts {m.group(0)!r}; the semantic review must confirm it holds under "
                "the task's own counting rules, which a claim about the files can silently contradict",
                step["name"]))
    return found


def _contract_probe(ctx: GateContext) -> tuple[list[Finding], dict]:
    from ..assurance import stage
    from ..author.validate import order_declaration
    from ..evaluate import exported_grade

    bundle = ctx.task_dir
    spec = json.loads(ctx.path("authoring", "spec.json").read_text())
    checks = json.loads(ctx.path("tests", "checks.json").read_text())["checks"]
    rubric = json.loads(ctx.path("tests", "rubric.json").read_text())
    reference = {p.name: json.loads(p.read_text()) for p in sorted(ctx.path("solution", "submission").glob("*.json"))}
    guards = {c["id"] for c in checks if c.get("kind") == "guardrail"}
    findings: list[Finding] = []
    grades, unprobed = 0, []

    with tempfile.TemporaryDirectory(prefix="arena-contract-") as tmp:
        def grade(values, step):
            nonlocal grades
            grades += 1
            root = stage(Path(tmp) / f"g{grades}", values)
            return exported_grade(bundle, root, step)

        for step, members in rubric.items():
            baseline = grade(reference, step)
            if baseline["reward"] != 1:
                raise RuntimeError(f"reference answer scores {baseline['reward']} on {step}; "
                                   "the probe cannot tell what the grader rewards")
            step_guards = [g for g in members if g in guards]
            for check in checks:
                actual = check.get("actual") or {}
                if check["id"] not in members or check.get("kind") != "objective" or actual.get("op") != "field":
                    continue
                file, path = actual.get("file"), actual.get("path") or ""
                value = _dig(reference.get(file), path)
                if value is None:
                    continue
                cases = [(trail, kind) for trail, _ in _arrays(value) for kind in KINDS]
                integer = _first_integer(value) if step_guards else None
                for trail, kind in cases + ([(integer, "plus-one")] if integer is not None else []):
                    if grades >= MAX_GRADES:
                        unprobed.append(f"{check['id']}:{path}")
                        break
                    if kind == "plus-one":
                        mutated = copy.deepcopy(value)
                        if trail:
                            cur = mutated
                            for part in trail[:-1]:
                                cur = cur[part]
                            cur[trail[-1]] += 1
                        else:
                            mutated += 1
                    else:
                        mutated = _mutated(value, trail, kind)
                        if mutated is None:
                            continue
                    values = copy.deepcopy(reference)
                    if path:
                        _put(values[file], path, mutated)
                    else:
                        values[file] = mutated
                    result = grade(values, step)
                    where = f"{file}:{path}" + "".join(f"[{p}]" if isinstance(p, int) else f".{p}" for p in trail or ())
                    tripped = [g for g in step_guards if not (result["checks"].get(g) or {}).get("passed")]
                    if tripped:
                        findings.append(Finding(
                            Severity.BLOCKER, "guard-fails-on-wrong-answer",
                            f"{kind} {where} is a wrong answer, not an edit, yet it fails guardrail(s) "
                            f"{tripped} and gates the step", f"tests/checks.json:{check['id']}"))
                    if kind == "plus-one":
                        continue
                    declared, why = order_declaration(spec, file, _schema_path(path, trail))
                    passed = bool((result["checks"].get(check["id"]) or {}).get("passed")) and result["reward"] >= 1
                    if kind == "reversed" and declared == "unordered":
                        if not passed:
                            findings.append(Finding(
                                Severity.BLOCKER, "unordered-list-graded-in-order",
                                f"{where} reversed loses credit, but {why}", f"tests/checks.json:{check['id']}"))
                    elif passed:
                        code = {"reversed": "order-not-graded", "repeated": "repeat-not-graded",
                                "dropped": "omission-not-graded"}[kind]
                        findings.append(Finding(
                            Severity.BLOCKER, code,
                            f"{where} {kind} still earns full credit"
                            + (f", though {why}" if kind == "reversed" and why else
                               "; the contract compares arrays as written" if kind == "reversed" else ""),
                            f"tests/checks.json:{check['id']}"))
    findings.extend(_text_warnings(spec))
    return findings, {"grades": grades, "max_grades": MAX_GRADES, "unprobed": unprobed}


contract_probe_gate = FunctionGate("grader.contract_probe", _contract_probe,
                                   requires=("bundle.structure",))
