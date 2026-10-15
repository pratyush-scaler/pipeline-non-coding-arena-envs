"""The premise map: which independent premise decides which graded checks.

Arena's 261013 review and spec 10_12 replaced the "one carrier + cascade" shape
(one trap on two linked checks worth ~28 points, the rest free) with the
conjunctive design: several independent premises, each from a different trap
family, each on its own atomic exact checks, so a run can miss one premise and
get the others -- full success stays rare while partial scores spread.

A draft records it in `quality.premise_map`:

    [{"id": "P1", "family": "<policy.TRAP_FAMILIES id>",
      "checks": ["<objective ids this premise alone decides>"],
      "targets": "fable|astra|both",
      "resolving_quote": {"file": "<fixture path, or 'instruction'>",
                          "quote": "<the verbatim sentence that settles it>"},
      "misreading": "...", "counterexample": "<quality.counterexamples id>"}]

Two kinds of finding (POLICY.md, "Training signal"):

  "premise map: ..."    BLOCKING. The map misstates the grader -- a check id
                        that is not a declared objective, one check claimed by
                        two premises (a compound criterion), an unknown family,
                        a resolving quote the materials do not contain. The
                        screen, the cover sheet and hardening read the map, so a
                        false one corrupts every number built on it; and an
                        unquotable premise is an inference the materials do not
                        settle (spec 10_12 rule 2).
  "premise shape: ..."  ADVISORY (`pipeline.advisory`). Count, share, free
                        share, family distinctness, the timestamp cap, the
                        discouraged families. Targets the designer aims at and
                        the screen measures; never a blocker or a repair.

A spec with no map raises one advisory ("premise map absent") and nothing else,
so bundles built before the map existed validate exactly as before.
"""
from __future__ import annotations

from pathlib import Path

from .. import policy

#: Accepted `targets` values on a premise.
TARGETS = ("fable", "astra", "both")

#: The pseudo-file a resolving quote may cite to point at a step instruction.
INSTRUCTION = "instruction"

#: A quote is one sentence or bullet: long enough not to match by accident.
MIN_QUOTE = 12
MAX_QUOTE = 600


def _norm(text: str) -> str:
    return " ".join(str(text).replace("’", "'").split()).lower()


def raw_map(spec: dict):
    """`quality.premise_map` as written (None when absent)."""
    quality = spec.get("quality") if isinstance(spec, dict) else None
    if not isinstance(quality, dict):
        return None
    return quality.get("premise_map")


def entries(spec: dict) -> list[dict]:
    """The well-formed premise entries (id, family, checks); malformed ones are
    reported by `problems`, never guessed at here."""
    raw = raw_map(spec)
    if not isinstance(raw, list):
        return []
    out, seen = [], set()
    for entry in raw:
        if (not isinstance(entry, dict) or not isinstance(entry.get("id"), str) or not entry["id"].strip()
                or entry["id"] in seen or not isinstance(entry.get("checks"), list)):
            continue
        seen.add(entry["id"])
        out.append({"id": entry["id"], "family": entry.get("family"),
                    "checks": [c for c in entry["checks"] if isinstance(c, str)],
                    "targets": entry.get("targets")})
    return out


def _objective_steps(spec: dict) -> dict[str, tuple[str, float]]:
    """objective check id -> (step name, weight), steps resolved as the build does."""
    from copy import deepcopy
    checks = [c for c in spec.get("checks") or [] if isinstance(c, dict)]
    try:
        from .contracts import compile_steps
        copy = deepcopy(spec)
        compile_steps(copy)
        checks = [c for c in copy.get("checks") or [] if isinstance(c, dict)]
    except Exception:                                # noqa: BLE001 -- the step contract reports itself
        pass
    out = {}
    for check in checks:
        if check.get("kind") != "objective" or not isinstance(check.get("id"), str):
            continue
        weight = check.get("weight", 0)
        weight = weight if type(weight) in (int, float) and weight > 0 else 0
        out[check["id"]] = (str(check.get("step") or "01-task"), float(weight))
    return out


def design_shape(spec: dict) -> dict:
    """What the premise map says the grader looks like, per step.

    shares are of the step's objective weight (each step is scored, and
    delivered, on its own). `heaviest` is the premise with the most weight
    across the task -- the static stand-in for the decisive trap.
    """
    objectives = _objective_steps(spec)
    premises = entries(spec)
    totals: dict[str, float] = {}
    for step, weight in objectives.values():
        totals[step] = totals.get(step, 0.0) + weight
    claimed = {c for p in premises for c in p["checks"] if c in objectives}
    steps = {}
    for step, total in sorted(totals.items()):
        in_step = {p["id"]: sum(objectives[c][1] for c in p["checks"]
                                if c in objectives and objectives[c][0] == step) for p in premises}
        free = sum(w for cid, (s, w) in objectives.items() if s == step and cid not in claimed)
        steps[step] = {"objective_weight": total,
                       "premises": sorted(pid for pid, w in in_step.items() if w > 0),
                       "premise_shares": {pid: round(w / total, 4) for pid, w in in_step.items()
                                          if w > 0 and total > 0},
                       "free_share": round(free / total, 4) if total > 0 else None}
    weights = {p["id"]: sum(objectives[c][1] for c in p["checks"] if c in objectives) for p in premises}
    heaviest = max(premises, key=lambda p: (weights[p["id"]], p["id"]), default=None)
    return {"premise_map": "present" if isinstance(raw_map(spec), list) else "absent",
            "premises": len(premises),
            "families": [p["family"] for p in premises],
            "heaviest": heaviest["id"] if heaviest else None,
            "heaviest_family": heaviest["family"] if heaviest else None,
            "premise_weights": weights,
            "steps": steps,
            "max_premise_share": max((s for row in steps.values() for s in row["premise_shares"].values()),
                                     default=None),
            "max_free_share": max((row["free_share"] for row in steps.values()
                                   if row["free_share"] is not None), default=None)}


def _instruction_text(spec: dict) -> str:
    texts = [spec.get("instruction") or ""]
    texts += [s.get("instruction") or "" for s in spec.get("steps") or [] if isinstance(s, dict)]
    second = spec.get("second_step")
    if isinstance(second, dict):
        texts.append(second.get("instruction") or "")
    return "\n".join(t for t in texts if isinstance(t, str))


def _quote_problem(entry: dict, spec: dict, bundle: Path | None, at: str) -> str | None:
    """A blocking finding when the resolving quote is absent from the materials."""
    from .contracts import ContractError, contained
    witness = entry.get("resolving_quote")
    if (not isinstance(witness, dict) or not isinstance(witness.get("file"), str)
            or not isinstance(witness.get("quote"), str)):
        return (f"premise map: {at} needs resolving_quote {{file, quote}} -- the verbatim sentence "
                "in the materials that settles this premise (spec 10_12: every inference must be "
                "resolvable from the instructions and files)")
    quote = _norm(witness["quote"])
    if not MIN_QUOTE <= len(quote) <= MAX_QUOTE:
        return (f"premise map: {at}.resolving_quote must quote one sentence "
                f"({MIN_QUOTE}..{MAX_QUOTE} characters)")
    name = witness["file"].strip()
    if name == INSTRUCTION:
        return None if quote in _norm(_instruction_text(spec)) else (
            f"premise map: {at}.resolving_quote is not in any step instruction")
    if bundle is None:
        return None
    candidates = [Path(bundle) / "environment/files"]
    overlays = Path(bundle) / "environment/step-files"
    if overlays.is_dir():
        candidates += sorted(p for p in overlays.iterdir() if p.is_dir())
    found_file = False
    for root in candidates:
        try:
            path = contained(root, name)
        except (ContractError, OSError, ValueError):
            return f"premise map: {at}.resolving_quote file {name!r} escapes the fixture"
        if not path.is_file():
            continue
        found_file = True
        try:
            text = path.read_text()
        except (OSError, UnicodeError):
            continue
        if quote in _norm(text):
            return None
    if not found_file:
        return f"premise map: {at}.resolving_quote file {name!r} is not a fixture file"
    return f"premise map: {at}.resolving_quote is not verbatim in {name!r}"


def problems(spec: dict, bundle: Path | None = None) -> list[str]:
    """Static premise-map findings: "premise map:" blocks, "premise shape:" advises."""
    raw = raw_map(spec)
    if raw is None:
        return ["premise shape: quality.premise_map is absent -- record every independent premise "
                "(id, family, checks, resolving_quote and the model it bites) so the screen can measure "
                "each one; without it the reward gradient and trap diversity cannot be checked "
                "(premise map absent)"]
    if not isinstance(raw, list):
        return ["premise map: quality.premise_map must be a list of premise entries"]
    objectives = _objective_steps(spec)
    declared = {c.get("id") for c in spec.get("checks") or [] if isinstance(c, dict)}
    found: list[str] = []
    owner: dict[str, str] = {}
    ids: set[str] = set()
    for index, entry in enumerate(raw):
        at = f"quality.premise_map[{index}]"
        if not isinstance(entry, dict):
            found.append(f"premise map: {at} must be an object")
            continue
        pid = entry.get("id")
        if not isinstance(pid, str) or not pid.strip():
            found.append(f"premise map: {at} needs an id")
            continue
        at = f"premise {pid!r}"
        if pid in ids:
            found.append(f"premise map: {at} is declared twice")
            continue
        ids.add(pid)
        if entry.get("family") not in policy.TRAP_FAMILIES:
            found.append(f"premise map: {at} family {entry.get('family')!r} is not a catalogued family "
                         f"({', '.join(sorted(policy.TRAP_FAMILIES))})")
        checks = entry.get("checks")
        if not isinstance(checks, list) or not checks or not all(isinstance(c, str) for c in checks):
            found.append(f"premise map: {at} must name the objective checks it decides")
            checks = []
        for cid in checks:
            if cid not in objectives:
                kind = "a guardrail or ungraded check" if cid in declared else "not a declared check"
                found.append(f"premise map: {at} names {cid!r}, which is {kind}; a premise decides "
                             "graded objectives")
            elif cid in owner and owner[cid] != pid:
                found.append(f"premise map: check {cid!r} is claimed by premises {owner[cid]!r} and "
                             f"{pid!r}; one decision is one check -- a check two premises decide is a "
                             "compound criterion, and its failures link the two")
            else:
                owner[cid] = pid
        quote = _quote_problem(entry, spec, bundle, at)
        if quote:
            found.append(quote)
        if entry.get("targets") not in TARGETS:
            found.append(f"premise shape: {at} targets {entry.get('targets')!r}; say which model it is "
                         f"meant to bite ({'|'.join(TARGETS)})")
    found += shape_advisories(spec)
    return found


def shape_advisories(spec: dict) -> list[str]:
    """The design targets (count, share, free share, families, timestamp cap)."""
    shape = design_shape(spec)
    premises = entries(spec)
    out: list[str] = []
    steps = shape["steps"]
    if len(steps) <= 1:
        if len(premises) < policy.MIN_INDEPENDENT_PREMISES:
            out.append(f"premise shape: {len(premises)} independent premise(s); a single-step task "
                       f"carries at least {policy.MIN_INDEPENDENT_PREMISES}, each from a different family "
                       "on its own checks, so full success stays rare while partial scores spread")
    else:
        if len(premises) < policy.MIN_PREMISES_MULTI_TURN_TOTAL:
            out.append(f"premise shape: {len(premises)} independent premise(s) across {len(steps)} steps; "
                       f"a multi-turn task carries at least {policy.MIN_PREMISES_MULTI_TURN_TOTAL}")
        for step, row in steps.items():
            if len(row["premises"]) < policy.MIN_PREMISES_PER_STEP_MULTI_TURN:
                out.append(f"premise shape: step {step!r} carries {len(row['premises'])} premise(s); every "
                           f"step needs at least {policy.MIN_PREMISES_PER_STEP_MULTI_TURN} of its own")
    for step, row in steps.items():
        for pid, share in sorted(row["premise_shares"].items()):
            if share > policy.MAX_PREMISE_SHARE:
                out.append(f"premise shape: premise {pid!r} carries {share:.0%} of step {step!r}'s objective "
                           f"weight, above {policy.MAX_PREMISE_SHARE:.0%}; one premise deciding most of the "
                           "score is the single-decision shape spec 10_12 asks to avoid")
        if row["free_share"] is not None and row["free_share"] > policy.MAX_FREE_SHARE:
            out.append(f"premise shape: {row['free_share']:.0%} of step {step!r}'s objective weight sits on "
                       f"checks no premise decides, above {policy.MAX_FREE_SHARE:.0%} free; easy points "
                       "for every model flatten the reward")
    seen: dict[str, str] = {}
    for premise in premises:
        family = premise["family"]
        if family in seen and family in policy.TRAP_FAMILIES:
            out.append(f"premise shape: premises {seen[family]!r} and {premise['id']!r} share family "
                       f"{family!r}; a model that sees a principle once applies it everywhere, so "
                       "same-family premises fail together")
        seen.setdefault(family, premise["id"])
        if family in policy.DISCOURAGED_DECIDER_FAMILIES:
            out.append(f"premise shape: premise {premise['id']!r} uses discouraged family {family!r}; "
                       "it measured ambiguous or always-solved as a decider")
    stamps = [p["id"] for p in premises if p["family"] == policy.TIMESTAMP_FAMILY]
    if len(stamps) > policy.MAX_TIMESTAMP_PREMISES_PER_TASK:
        out.append(f"premise shape: {len(stamps)} timestamp-ordering premises ({', '.join(stamps)}); at most "
                   f"{policy.MAX_TIMESTAMP_PREMISES_PER_TASK} per task -- clock offsets, store/outage windows "
                   "and impossible stamps are one family, and Arena flagged it as over-used")
    raw = raw_map(spec) if isinstance(raw_map(spec), list) else []
    files: dict[str, str] = {}
    for entry in raw:
        if not isinstance(entry, dict) or not isinstance(entry.get("resolving_quote"), dict):
            continue
        name = entry["resolving_quote"].get("file")
        if isinstance(name, str) and name != INSTRUCTION:
            if name in files and files[name] != entry.get("id"):
                out.append(f"premise shape: premises {files[name]!r} and {entry.get('id')!r} are both "
                           f"settled by {name!r}; independent premises live in different documents")
            files.setdefault(name, entry.get("id"))
    return out
