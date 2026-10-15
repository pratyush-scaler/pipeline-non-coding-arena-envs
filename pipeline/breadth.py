"""Does this task make the model *measure* anything, or only read and compute?

Five difficulty hypotheses were built on and falsified by measurement in this
batch. This module encodes the sixth, which is the first to survive contact with
the corpus, and it exists so that the seventh is tested against data rather than
against another brief.

The measurement, over 94 objective checks on the tasks screened against the
primary calibration model:

    property                            in FAILED checks   in PASSED checks
    threshold over a word count              4/11 (36%)         0/83  (0%)
    any numeric threshold                    7/11 (64%)         6/83  (7%)

Every check that applies a numeric threshold to a word count the model must
compute itself over prose has failed, every time it has been screened. None of
the 83 passed checks uses the construct.

What this says is not "models cannot count". It is that difficulty here comes
from measurement *breadth* -- a quantity the model must establish itself, once
per item, over many items, where no surface states it and it cannot check its
own work. Given that, a frontier model satisfices: on one task it returned an
empty set where the reference held nineteen entries, while getting the bounded
parts of the very same submission exactly right. It did the finite work and
abandoned the exhaustive work.

The corollary is what makes this actionable, because it contradicts what looks
obvious: chained computation does NOT make a task hard. The two hardest tasks in
the batch have the *least* derivation depth. A task whose census counts rows in
a markdown table scores 1.00 however subtle the membership rule, because reading
a table is not measuring anything.

This module is a static screen, not a measurement. It cannot say a task is hard.
It says whether a task contains the one construct that has ever been observed to
fail, which is a different and much cheaper claim -- and it is one-sided in the
safe direction: it can only let an easy task through to the real screen, which
is where it was going anyway.
"""
from __future__ import annotations

import json
from pathlib import Path

#: Row fields naming a quantity the model must count for itself.
COUNTED_QUANTITIES = ("words", "word_count", "wordcount", "n_words",
                      "sentences", "paragraphs", "chars", "characters")

#: Comparisons that turn a measured quantity into set membership.
THRESHOLD_OPS = ("lt", "gt", "lte", "gte")

#: Assertions with no partial credit. Being close is not being right, which is
#: what makes a single mis-measured item cost a whole check.
#: Every name here must be a real `checks.ASSERTIONS` entry; a misspelt one
#: silently classifies nothing (there was a `sequence_equals`).
EXACT_ASSERTIONS = ("set_equals", "equals")

#: Below this many source rows, "exhaustive" is not exhaustive: a model can
#: simply do all of it. Set from the corpus -- the tasks that fail have 15+
#: prose sections or 100 paired records; the ones that pass have 7-8 table rows.
MIN_ITEMS_WORD_COUNT = 15
MIN_ITEMS_PAIRWISE = 50

#: Objective band limits, read from `author/quality.py` so this screen can
#: report them alongside difficulty. A task is capped at TEN objectives, so the
#: measurement construct has to be paid for by removing transcription checks
#: rather than added on top -- a root check bolted onto a full set fails the
#: gate however good the design. This is the same finding from the other side:
#: the two hardest tasks measured sit at the core MINIMUM of four.
from .author.quality import BAND_LIMITS as BANDS  # noqa: E402  single source


def bands(checks: list[dict]) -> dict:
    """Objective counts per band, and how many more the gate would accept."""
    objectives = [c for c in checks if c.get("kind") == "objective"]
    counts = {band: sum(c.get("band", "core") == band for c in objectives)
              for band in BANDS}
    room = {band: max(0, high - counts[band]) for band, (_, high) in BANDS.items()}
    breaches = [f"{band} {counts[band]} outside {low}-{high}"
                for band, (low, high) in BANDS.items()
                if not low <= counts[band] <= high]
    return {"counts": counts, "room": room, "room_total": sum(room.values()),
            "in_band": not breaches, "breaches": breaches}


#: `compute` kinds that make a per-item judgement across two joined records.
#: This is the second construct that has been observed to fail: on the task that
#: scored 0.18 the model returned an EMPTY set where the reference held 19,
#: while getting the bounded parts of the same submission exactly right.
PAIRWISE_KINDS = ("equal", "not_equal", "differs", "matches")


def projection_sizes(bundle) -> dict:
    """Actual row count of each projection, by running the parse.

    Counting rows by hand from the spec would be guessing at the number that
    matters most. The projections are deterministic and cost nothing to
    materialise, so this measures instead.
    """
    from .author import oracle

    bundle = Path(bundle)
    spec = json.loads((bundle / "authoring" / "spec.json").read_text())
    fixture = bundle / "environment" / "files"
    if not fixture.is_dir() or not spec.get("projections"):
        return {}
    try:
        return {name: len(rows) for name, rows
                in oracle.project(fixture, spec["projections"]).items()}
    except Exception:                       # noqa: BLE001
        # A fixture we cannot parse yields no size, never a reassuring zero.
        return {}


def pairwise_fields(bundle) -> dict[str, set]:
    """Projection -> fields computed by comparing two joined records."""
    bundle = Path(bundle)
    try:
        spec = json.loads((bundle / "authoring" / "spec.json").read_text())
    except (OSError, ValueError):
        return {}
    out: dict[str, set] = {}
    for step in spec.get("projections") or []:
        if step.get("op") != "join":
            continue
        fields = {c.get("field") for c in (step.get("compute") or [])
                  if c.get("kind") in PAIRWISE_KINDS}
        if fields:
            out[str(step.get("as"))] = fields
    return out


def _walk(node, fn):
    if isinstance(node, dict):
        fn(node)
        for value in node.values():
            _walk(value, fn)
    elif isinstance(node, list):
        for value in node:
            _walk(value, fn)


def check_anatomy(check: dict, pairwise: dict[str, set] | None = None) -> dict:
    """Structural properties of one check, independent of its subject matter."""
    pairwise = pairwise or {}
    facts = {"threshold": False, "counted_quantity": False,
             "pairwise": False, "sources": set(), "fields": set()}

    def visit(node):
        field = str(node.get("field")).lower() if node.get("field") else None
        if field:
            facts["fields"].add(field)
        for op in THRESHOLD_OPS:
            if op in node and "field" in node:
                facts["threshold"] = True
                if field in COUNTED_QUANTITIES:
                    facts["counted_quantity"] = True
        if node.get("op") == "rows" and node.get("file"):
            facts["sources"].add(str(node["file"]))

    _walk(check.get("target"), visit)

    # Construct B: the check filters on a field this bundle computes by
    # comparing two joined records, so the model must make that judgement once
    # per record with nothing stating it.
    for source in facts["sources"]:
        if facts["fields"] & {str(f).lower() for f in pairwise.get(source, ())}:
            facts["pairwise"] = True

    facts["exact"] = check.get("assertion") in EXACT_ASSERTIONS
    facts["counts_itself"] = facts["threshold"] and facts["counted_quantity"]
    facts["measures_breadth"] = facts["counts_itself"] or facts["pairwise"]
    facts["sources"] = sorted(facts["sources"])
    facts["fields"] = sorted(facts["fields"])
    return facts


def root_checks(checks: list[dict], pairwise: dict[str, set] | None = None,
                sizes: dict | None = None) -> list[dict]:
    """Checks carrying a construct that has actually been observed to fail.

    `sizes` is the measured row count of each projection. Breadth is the whole
    lever, so a check of the right shape over eight rows is not a root check:
    a model simply does all eight.
    """
    sizes = sizes or {}
    out = []
    for check in checks:
        if check.get("kind") != "objective":
            continue
        facts = check_anatomy(check, pairwise)
        if not (facts["measures_breadth"] and facts["exact"]):
            continue
        items = max((sizes.get(s, 0) for s in facts["sources"]), default=0)
        floor = MIN_ITEMS_PAIRWISE if facts["pairwise"] else MIN_ITEMS_WORD_COUNT
        out.append({"id": check.get("id"), "weight": check.get("weight"),
                    "step": check.get("step"), "items": items or None,
                    "items_floor": floor,
                    "broad_enough": (items >= floor) if sizes else None,
                    **facts})
    return out


def cascade(checks: list[dict], root: dict, pairwise: dict[str, set] | None = None) -> list[str]:
    """Checks recomputed from the same source the root measures.

    A root check alone caps the damage of a mis-measurement at its own weight.
    What produced 0.18 was five checks falling from one error, so a root with no
    cascade is a much weaker task than its presence suggests.
    """
    downstream = []
    for check in checks:
        if check.get("kind") != "objective" or check.get("id") == root["id"]:
            continue
        if set(check_anatomy(check, pairwise)["sources"]) & set(root["sources"]):
            downstream.append(check.get("id"))
    return downstream


def report(checks: list[dict], bundle=None) -> dict:
    """What this task makes the model measure, and what falls if it mis-measures.

    Pass `bundle` to measure breadth from the fixture. Without it the shape is
    still reported, but `broad_enough` stays None -- unknown, never True.
    """
    pairwise = pairwise_fields(bundle) if bundle else {}
    sizes = projection_sizes(bundle) if bundle else {}
    objectives = [c for c in checks if c.get("kind") == "objective"]
    roots = root_checks(checks, pairwise, sizes)
    total = sum(c.get("weight") or 0 for c in objectives)

    rooted = []
    for root in roots:
        downstream = cascade(checks, root, pairwise)
        at_risk = (root.get("weight") or 0) + sum(
            c.get("weight") or 0 for c in objectives
            if c.get("id") in downstream)
        rooted.append({**root, "cascade": downstream,
                       "weight_at_risk": at_risk,
                       "share_at_risk": round(at_risk / total, 3) if total else None})

    tolerant = [c.get("id") for c in objectives if c.get("tolerance") is not None]
    usable = [r for r in rooted if r["broad_enough"] is not False]
    return {"objectives": len(objectives), "weight_total": total,
            "bands": bands(checks),
            "root_checks": rooted, "tolerant_checks": tolerant,
            "projection_sizes": sizes,
            "has_root": bool(usable),
            "narrow_roots": [r["id"] for r in rooted if r["broad_enough"] is False],
            "max_share_at_risk": max((r["share_at_risk"] or 0 for r in usable),
                                     default=0.0)}


def problems(checks: list[dict], bundle=None) -> list[str]:
    """Why this task is unlikely to measure hard. Advisory, never a release gate.

    This is a *static* screen: it cannot establish difficulty, and a task it
    passes is not thereby hard. Wiring it to a release decision would let a
    structural pattern stand in for the measurement it only approximates.
    """
    found = report(checks, bundle)
    out = []
    if not found["has_root"]:
        out.append(
            "no check applies a numeric threshold to a quantity the model must "
            "count for itself (words, sentences, paragraphs) under an exact "
            "assertion. Every check of that construct screened so far has "
            "failed; no check that passed used it. A task without one has "
            "scored 1.00 in every case measured, however subtle its rules")
        for narrow in found["narrow_roots"]:
            out.append(
                f"{narrow} has the right shape but too few items to be "
                "exhaustive -- a model simply does all of them. Breadth is the "
                "lever: the tasks that measured hard span 15+ prose sections or "
                "100 paired records")
    elif found["max_share_at_risk"] < 0.5:
        best = max(found["root_checks"], key=lambda r: r["share_at_risk"] or 0)
        out.append(
            f"the root check {best['id']} puts only "
            f"{best['share_at_risk']:.0%} of the task's weight at risk. One "
            "mis-measured item should take down the figures computed from it; "
            "the tasks that measured hard lost four or five checks to a single "
            "error")
    band = found["bands"]
    if not band["in_band"]:
        out.append(
            f"objective bands are outside what the gate accepts "
            f"({'; '.join(band['breaches'])}). `./arena gate` will refuse this "
            "task whatever its difficulty")
    elif not band["room_total"] and not found["has_root"]:
        out.append(
            "every objective band is full, so a root check cannot be added -- "
            "it has to be paid for by removing a transcription check, one that "
            "only restates a figure the fixture already prints. The two hardest "
            "tasks measured sit at the core minimum of four")
    if found["tolerant_checks"]:
        out.append(
            f"checks carry a tolerance ({', '.join(found['tolerant_checks'])}): "
            "a tolerance wide enough to absorb a mis-measured item makes the "
            "check unable to distinguish the work from a near miss")
    return out


def load(bundle: Path) -> list[dict]:
    """The bundle's checks, as data -- graders are data, not code."""
    blob = json.loads((Path(bundle) / "tests" / "checks.json").read_text())
    return blob["checks"] if isinstance(blob, dict) else blob
