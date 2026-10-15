"""Anti-reward-hacking and calibration-validity gates.

`ANTI_REWARD_HACKING.md` §0 is the rule that does the most work here: *design
the answer so it is derived, never stored*. If the answer exists in no file,
full read access to the fixture still does not hand it over, and every other
control becomes belt-and-braces rather than load-bearing. It is also the only
defence that cannot be bypassed, and it cannot be retrofitted -- which is why
`answer.derivation` runs against the bundle rather than against a campaign.

The calibration gates encode the rule that a rubric mean hides two opposite
defects (a check nobody fails and a check nobody passes both pull it toward the
middle), so bands are measured per check, over reachable attempts only.
"""

from __future__ import annotations

import json
import re
from collections import Counter
from pathlib import Path
from typing import Any

from ..config import (CORE_BAND, FLOOR_BAND, MAX_FLOOR_CHECKS,
                      MAX_STRETCH_CHECKS, MIN_CORE_CHECKS)
from ..author.build import WEIGHT_TOTAL
from .base import Finding, FunctionGate, GateContext, Severity


#: Shipped bundles use either name for the fixture root. A gate that knows only
#: one reports "no fixture" on a bundle that has one, which is a defect in the
#: gate and looks exactly like a defect in the bundle.
FIXTURE_DIRS = ("files", "fixtures")


def _fixture_root(ctx: GateContext) -> Path | None:
    for name in FIXTURE_DIRS:
        path = ctx.path("environment", name)
        if path.is_dir():
            return path
    return None


def _load_key(ctx: GateContext) -> dict[str, Any]:
    """Every answer-key document in the bundle, merged under its file stem."""
    key_dir = ctx.path("tests/key")
    if not key_dir.is_dir():
        return {}
    merged: dict[str, Any] = {}
    for path in sorted(key_dir.glob("*.json")):
        try:
            merged[path.stem] = json.loads(path.read_text())
        except json.JSONDecodeError:
            continue
    return merged


#: A value worth blocking on: a digest or opaque token, i.e. something that can
#: only have been COMPUTED. Deliberately narrow.
#:
#: The looser version of this ("has a digit, has a letter, 16+ chars") fired on
#: `notice-journal-2026-11` and `notice:notice-notes-2` -- record identifiers,
#: which appear in the fixture because the records exist. Separators and
#: word-shaped segments are the tell: a digest has neither. Excluding them costs
#: recall on any opaque id that happens to contain a hyphen, which is stated in
#: the gate's evidence rather than hidden.
_DIGEST = re.compile(r"^(?:[0-9a-fA-F]{24,}|[A-Za-z0-9+/]{24,}={0,2})$")


def _derivation(ctx: GateContext) -> tuple[list[Finding], dict]:
    """The answer must not be readable anywhere the agent can reach.

    §0 of the anti-reward-hacking rules: *design the answer so it is derived,
    never stored*. If it exists in no record, full read access does not hand it
    over.

    What this gate can and cannot decide, stated plainly because an earlier
    version of it reported 542 "leaked" values in one file and every one was a
    false positive:

      it CAN decide  a whole expected document reproduced verbatim in the
                     fixture, and individual high-entropy values (digests,
                     ids, computed magnitudes) the agent was meant to derive
      it CANNOT decide  whether the MAPPING is stored. A task whose answer is
                     "which of these pages is contested" draws its values from a
                     published vocabulary by construction; that those words
                     appear in the fixture says nothing. Only a human reading
                     the fixture can rule that out.

    So the gate blocks on what it can prove and reports the rest as a profile
    for review. It lower-bounds leakage. It does not certify derivation, and the
    evidence says so.
    """
    # With declarative checks there is no stored key to scan, and the question is
    # answered behaviourally instead: the `answer_lookup` probe computes every
    # target and submits whatever it can read straight out of the fixture. Its
    # score IS the share of the task winnable without reasoning, which is a
    # stronger statement than any static scan.
    if ctx.path("tests/checks.json").exists():
        # Re-run, never read back: the stored report is checked for binding by
        # `hacking.resistance`, and a stale one cannot vouch for derivation.
        from ..author.probes import gate_report
        report, _ = gate_report(ctx.task_dir, getattr(ctx, "extras", None))
        lookup = (report.get("results") or {}).get("answer_lookup") or {}
        reward = lookup.get("reward")
        readable = lookup.get("readable_from_fixture") or {}
        findings: list[Finding] = []
        if reward is None:
            findings.append(Finding(
                Severity.BLOCKER, "no-lookup-probe",
                "declarative bundle with no answer_lookup result; derivation is "
                "unmeasured", "verification/probes.json"))
        elif reward >= 1.0:
            findings.append(Finding(
                Severity.BLOCKER, "answer-stored",
                f"answer_lookup scores {reward} -- the whole answer is readable "
                "from the fixture without reasoning (§0 lost)",
                "verification/probes.json"))
        # §0 per check, not only in aggregate: a complete structured answer
        # stored in the fixture is a lookup however little of the task it is.
        # Before the probe searched structures, a reference JSON pasted into a
        # fixture note scored as "not readable" and this gate stayed green.
        stored = lookup.get("stored_structured") or {}
        for cid, where in sorted(stored.items()):
            findings.append(Finding(
                Severity.BLOCKER, "answer-stored-in-fixture",
                f"check {cid!r}: its complete answer is stored in the fixture at "
                f"{where.get('in')} ({where.get('match')} match) and can be copied "
                "rather than derived (§0)", "environment/files"))
        # A computed answer PRINTED in a document the check does not read, in any
        # locale spelling (2026-10-02 audit: a-009 printed all thirteen gaps in an
        # audit report, a-006 two figures in a listing; the token probe saw none).
        for cid, where in sorted((lookup.get("printed_derived") or {}).items()):
            findings.append(Finding(
                Severity.BLOCKER, "answer-printed-in-fixture",
                f"check {cid!r}: its computed answer is printed in {where.get('in')} "
                f"({where.get('matched')} of {where.get('of')} value(s): "
                f"{', '.join(str(v) for v in (where.get('values') or [])[:6])}) -- a reader can copy it "
                "instead of deriving it (§0). Change or remove the printed figures (an "
                "interested party may state a WRONG figure), or route the check around them",
                f"environment/files/{where.get('in')}"))
        for cid, where in sorted((lookup.get("printed_partial") or {}).items()):
            findings.append(Finding(
                Severity.WARN, "answer-partly-printed",
                f"check {cid!r}: {where.get('matched')} of {where.get('of')} of its computed "
                f"values are printed in {where.get('in')}", f"environment/files/{where.get('in')}"))
        if reward is None or reward >= 1.0:
            pass
        elif reward > 0.5:
            findings.append(Finding(
                Severity.WARN, "answer-partly-stored",
                f"answer_lookup scores {reward}: {len(readable)} target(s) are "
                f"readable verbatim from the fixture ({sorted(readable)[:4]})",
                "verification/probes.json"))
        return findings, {"mode": "behavioural (answer_lookup probe)",
                          "lookup_reward": reward,
                          "readable_targets": sorted(readable),
                          "stored_structured": sorted(lookup.get("stored_structured") or {}),
                          "untested": "a value the fixture states in a DIFFERENT "
                                      "form, or one computable in a single step, "
                                      "is not detected by the lookup probe"}

    key = _load_key(ctx)
    if not key:
        return [Finding(Severity.BLOCKER, "no-answer-key",
                        "no tests/checks.json and tests/key/ holds no parseable "
                        "JSON; derivation cannot be checked", "tests/")], {}

    def scalars(node: Any, path: str = "") -> list[tuple[str, str]]:
        out: list[tuple[str, str]] = []
        if isinstance(node, dict):
            for k, v in node.items():
                out += scalars(v, f"{path}.{k}" if path else str(k))
        elif isinstance(node, list):
            for i, v in enumerate(node):
                out += scalars(v, f"{path}[{i}]")
        elif isinstance(node, bool) or node is None:
            pass
        elif isinstance(node, (int, float)):
            # Small integers collide with everything; they are not evidence.
            if abs(node) >= 1000:
                out.append((path, str(node)))
        elif isinstance(node, str) and len(node) >= 6:
            out.append((path, node))
        return out

    targets = scalars(key)
    fixture = _fixture_root(ctx)
    findings: list[Finding] = []
    hits: list[dict] = []
    if fixture is None:
        return [Finding(Severity.BLOCKER, "no-fixture",
                        f"no environment/{{{','.join(FIXTURE_DIRS)}}}/ directory; "
                        "nothing to check the answer against", "environment/")], {}

    # Index the fixture once, then test membership. The obvious implementation
    # -- one regex per answer value per file -- is O(values x files) and does not
    # finish on a real fixture: kw-006 has ~250 KB of fixture text and thousands
    # of key scalars.
    token_re = re.compile(r"[A-Za-z0-9_.:-]+")
    index: dict[str, set[str]] = {}
    for path in fixture.rglob("*"):
        if not path.is_file() or path.stat().st_size > 8_000_000:
            continue
        try:
            text = path.read_text(errors="replace")
        except OSError:
            continue
        rel = str(path.relative_to(fixture))
        for tok in token_re.findall(text):
            index.setdefault(tok, set()).add(rel)

    high_entropy_hits: list[dict] = []
    for field, value in targets:
        found = sorted(index.get(value, ()))
        if not found:
            continue
        hit = {"field": field, "value": value[:60], "files": found[:4]}
        hits.append(hit)
        if _DIGEST.match(value):
            high_entropy_hits.append(hit)

    for hit in high_entropy_hits[:10]:
        findings.append(Finding(
            Severity.BLOCKER, "computed-value-stored",
            f"answer field {hit['field']} = {hit['value']!r} is a digest or opaque "
            f"token -- it can only have been computed -- and it appears verbatim in "
            f"{hit['files'][0]}", f"{fixture.name}/{hit['files'][0]}"))

    # A whole expected document reproduced in the fixture is an unambiguous leak.
    for path in fixture.rglob("*.json"):
        if not path.is_file() or path.stat().st_size > 4_000_000:
            continue
        try:
            doc = json.loads(path.read_text(errors="replace"))
        except (json.JSONDecodeError, OSError):
            continue
        for name, expected in key.items():
            if doc == expected:
                findings.append(Finding(
                    Severity.BLOCKER, "answer-document-stored",
                    f"fixture file {path.relative_to(fixture)} is byte-identical to "
                    f"answer key '{name}'", f"{fixture.name}/{path.name}"))

    by_file: dict[str, int] = {}
    for hit in hits:
        by_file[hit["files"][0]] = by_file.get(hit["files"][0], 0) + 1
    if hits and not high_entropy_hits:
        findings.append(Finding(
            Severity.WARN, "vocabulary-overlap",
            f"{len(hits)} answer value(s) also occur in the fixture, none of them a "
            "digest -- consistent with a published vocabulary and existing record "
            "ids rather than a leak. Confirm by hand that the MAPPING is not stored",
            fixture.name))

    return findings, {"checked_values": len(targets), "stored": len(hits),
                      "digest_hits": len(high_entropy_hits),
                      "by_file": dict(sorted(by_file.items(),
                                             key=lambda kv: -kv[1])[:10]),
                      "hits": hits[:10],
                      "untested": "tokenised exact match only. Strings under 6 "
                                  "chars and integers below 1000 are skipped "
                                  "(they collide with ordinary fixture content), "
                                  "and a value the fixture states in a DIFFERENT "
                                  "form -- split across fields, or computable in "
                                  "one step -- is not detected. This gate lower-"
                                  "bounds leakage; it does not prove derivation."}


def _leak_sweep(ctx: GateContext) -> tuple[list[Finding], dict]:
    """The grader, the key and the reference solution must not ship to the agent."""
    findings: list[Finding] = []
    fixture = _fixture_root(ctx)
    evidence: dict[str, Any] = {}
    if fixture is None:
        return [Finding(Severity.BLOCKER, "no-fixture",
                        f"no environment/{{{','.join(FIXTURE_DIRS)}}}/ directory",
                        "environment/")], {}

    banned = re.compile(r"(criteria\.py|reward\.toml|basis\.toml|rubric\.json|"
                        r"answers\.json|truth\.json|oracle\.py|solve\.sh)$", re.I)
    leaked = [str(p.relative_to(fixture)) for p in fixture.rglob("*")
              if p.is_file() and banned.search(p.name)]
    for rel in leaked:
        findings.append(Finding(Severity.BLOCKER, "grading-artefact-in-fixture",
                                f"{rel} is grading material and must not be reachable "
                                "from the agent's workspace", f"{fixture.name}/{rel}"))
    evidence["leaked"] = leaked

    # A Docker build context that includes tests/ ships the grader into the image.
    dockerignore = ctx.path(".dockerignore")
    if dockerignore.exists():
        text = dockerignore.read_text()
        evidence["dockerignore_covers_tests"] = "tests" in text
        if "tests" not in text:
            findings.append(Finding(
                Severity.WARN, "dockerignore",
                ".dockerignore does not mention tests/; confirm the agent image build "
                "context excludes grading material", ".dockerignore"))

    spoken, spoken_evidence = _answers_spoken_in_the_instruction(ctx)
    findings.extend(spoken)
    evidence.update(spoken_evidence)
    return findings, evidence


#: Values that carry no information wherever they appear.
_UNINFORMATIVE = frozenset({"0", "1", "2", "true", "false", "none", "null",
                            "yes", "no", "-", ""})


def _answer_scalars(value, out: set) -> None:
    """Every scalar leaf of the reference answer, as the text a reader sees."""
    if isinstance(value, dict):
        for item in value.values():
            _answer_scalars(item, out)
    elif isinstance(value, list):
        for item in value:
            _answer_scalars(item, out)
    elif isinstance(value, bool) or value is None:
        return
    elif isinstance(value, (int, float)):
        out.add(str(int(value)) if float(value).is_integer() else str(value))
    elif isinstance(value, str) and value.strip():
        out.add(value.strip())


def _answers_spoken_in_the_instruction(ctx: GateContext) -> tuple[list[Finding], dict]:
    """A derived answer printed in the instruction is a leak the probes cannot see.

    `answer_lookup` searches the FIXTURE. It is blind to the instruction, and the
    instruction is exactly where an answer gets written by accident: publishing
    the rules a grader applies (which fairness requires) means adding sentences
    full of the same vocabulary the answer uses, and a computed figure can ride
    in unnoticed.

    Judgement is unavoidable here, so this reports rather than blocks. A
    published threshold ("the briefing standard is 100 words") legitimately
    appears in both the instruction and the answer; a count the check exists to
    make the model derive does not. What separates them is not something a
    string match can decide -- but a six-decimal float in both places is worth a
    reader's minute, and before this nothing looked at all.
    """
    spec = getattr(ctx, "spec", None)
    if not isinstance(spec, dict):
        return [], {}
    text = (spec.get("instruction") or "")
    second = spec.get("second_step")
    if isinstance(second, dict):
        text += "\n" + (second.get("instruction") or "")
    if not text:
        return [], {}

    values: set[str] = set()
    _answer_scalars(spec.get("solution") or {}, values)

    # Only values that could not plausibly be coincidence, for the same reason
    # `probes._distinctive` exists: a bare 3 matches any prose.
    spoken = []
    for value in sorted(values):
        if value.lower() in _UNINFORMATIVE or len(value) < 3 or value not in text:
            continue
        try:
            number = float(value.replace(",", ""))
        except ValueError:
            if len(value) > 24:          # long content, not a label
                spoken.append(value)
            continue
        if "." in value or abs(number) >= 1000:
            spoken.append(value)

    findings = []
    if spoken:
        findings.append(Finding(
            Severity.WARN, "answer-value-in-instruction",
            f"{len(spoken)} reference-answer value(s) appear verbatim in the "
            f"instruction: {', '.join(repr(v)[:40] for v in spoken[:5])}"
            f"{' ...' if len(spoken) > 5 else ''}. A published standard may "
            "legitimately appear in both; a value the check exists to make the "
            "model compute may not. Read each one.",
            "authoring/spec.json"))
    return findings, {"answer_values_in_instruction": spoken[:20]}


def _bands(ctx: GateContext) -> tuple[list[Finding], dict]:
    """Per-check pass rates must sit in the declared bands.

    Requires a calibration report. Absent one the gate is an ERROR, never a PASS:
    "not yet measured" is not "measured and fine".
    """
    report = ctx.extras.get("calibration")
    if report is None:
        raise RuntimeError("no calibration report supplied; run the campaign first")

    checks = report.get("checks") or {}
    if not checks:
        raise RuntimeError("calibration report contains no per-check results")

    findings: list[Finding] = []
    bands: dict[str, str] = {}
    rates: dict[str, float] = {}
    from ..measurement import band as measured_band
    for check, row in checks.items():
        attempts = row.get("passed", 0) + row.get("failed", 0)   # gated_out excluded
        if attempts == 0:
            bands[check] = "unreachable"
            findings.append(Finding(
                Severity.BLOCKER, "dead-check",
                f"check '{check}' was never reachable in any rollout -- it is dead "
                "weight; ungate it or delete it", "tests/"))
            continue
        rate = row["passed"] / attempts
        rates[check] = round(rate, 3)
        bands[check] = measured_band(rate)

    counts = Counter(b for cid, b in bands.items() if checks[cid].get("kind") != "guardrail")
    if counts["core"] < MIN_CORE_CHECKS:
        # Diagnosis only (POLICY.md): a genuinely hard task has most checks
        # below 30% by construction, so band composition must not reject it.
        from .. import policy
        findings.append(Finding(
            Severity.BLOCKER if policy.BANDS_GATE_RELEASE else Severity.WARN,
            "too-few-core-checks",
            f"{counts['core']} checks in the 30-70% band (diagnostic target "
            f"{MIN_CORE_CHECKS})", "tests/"))
    if counts["floor"] > MAX_FLOOR_CHECKS:
        findings.append(Finding(
            Severity.WARN, "too-many-floor-checks",
            f"{counts['floor']} objectives pass ~always; redesign or reduce routine floor credit",
            "tests/"))
    if counts["stretch"] > MAX_STRETCH_CHECKS:
        findings.append(Finding(
            Severity.WARN, "too-many-stretch-checks",
            f"{counts['stretch']} checks below 30%; confirm they are hard rather than "
            "broken", "tests/"))
    # Gating. The rule is usually stated as "only a core check may gate anything",
    # and taken literally it blocks a pattern that carries no risk: every
    # objective here is gated on "did you submit the file at all", which measures
    # 1.0 and therefore makes nothing unreachable.
    #
    # The rule's actual purpose is narrower. It exists because gating on an
    # unclearable check voids everything downstream: five tasks in one corpus
    # scored exactly 0.125 with both models because a verbatim-stamp gate never
    # cleared, and promoting that stamp to a gate cut mean inter-model spread
    # 0.225 -> 0.049 while making every task LOOK harder. The danger is a
    # prerequisite nobody passes, not a prerequisite everybody passes.
    #
    # So: a gate below the core band is a blocker (it manufactures unreachable
    # criteria), a gate in the core band is deliberate and allowed, and a gate on
    # a near-certain check is dead weight -- reported, because a gate that never
    # fires is misleading structure, but not a defect.
    for check, prereqs in (report.get("gates") or {}).items():
        for prereq in prereqs:
            rate = rates.get(prereq)
            band = bands.get(prereq)
            if band == "core":
                continue
            if rate is None or rate < CORE_BAND[0]:
                findings.append(Finding(
                    Severity.BLOCKER, "gate-below-band",
                    f"check '{check}' is gated on '{prereq}', which measured "
                    f"{rate if rate is not None else 'unreachable'}. A gate on a "
                    "check the model rarely clears makes every criterion behind it "
                    "unreachable, which reads as difficulty and is breakage",
                    "tests/criteria.py"))
            else:
                findings.append(Finding(
                    Severity.WARN, "gate-never-fires",
                    f"check '{check}' is gated on '{prereq}' which measured "
                    f"{rate:.2f}; the gate never fires, so it is structure that "
                    "implies a dependency the scores do not show",
                    "tests/criteria.py"))

    # Descriptive only: guardrails protect actual negative obligations, not a quota.
    n_obj = sum(1 for c in checks.values() if c.get("kind") == "objective")
    n_grd = sum(1 for c in checks.values() if c.get("kind") == "guardrail")
    ratio = (n_grd / n_obj) if n_obj else 0.0
    return findings, {"bands": bands, "rates": rates, "counts": dict(counts),
                      "guardrail_ratio": round(ratio, 2)}


def _validity(ctx: GateContext) -> tuple[list[Finding], dict]:
    """Every zero must be attributable to the model.

    A zero from a verifier OOM, a missing score file or an adapter stall is
    measurement error, and it is worse than a missing data point because it is
    indistinguishable from a real result once it reaches a table.
    """
    report = ctx.extras.get("calibration")
    if report is None:
        raise RuntimeError("no calibration report supplied")

    rollouts = report.get("rollouts") or []
    if not rollouts:
        raise RuntimeError("calibration report lists no rollouts")

    findings: list[Finding] = []
    if not ctx.extras.get("legacy"):
        from ..evidence import calibration_problems
        findings.extend(Finding(Severity.BLOCKER, "invalid-evidence", p, "calibration")
                        for p in calibration_problems(ctx.task_dir, report))
    unclassified = [r.get("id") for r in rollouts
                    if r.get("reward") in (None, 0, 0.0)
                    and not r.get("zero_class")]
    for rid in unclassified[:10]:
        findings.append(Finding(
            Severity.BLOCKER, "unclassified-zero",
            f"rollout {rid} scored zero (or produced no score) with no zero_class; "
            "classify it as model_failure or void before it reaches a table",
            "calibration"))

    voided = [r for r in rollouts if r.get("zero_class") == "void"]
    invalid_rate = len(voided) / len(rollouts)
    if invalid_rate > 0.10:
        findings.append(Finding(
            Severity.WARN, "high-invalid-rate",
            f"{invalid_rate:.0%} of rollouts are void; every band estimate inherits "
            "that noise", "calibration"))

    # A campaign that straddled a rebuild measured a grader that is no longer
    # on disk, so nothing below it means anything. Blocker rather than warn:
    # the numbers look entirely ordinary, which is exactly why a-002's 0.00 was
    # reported as a verified hard task before this was noticed.
    if report.get("grader_stable") is False:
        findings.append(Finding(
            Severity.BLOCKER, "grader-changed-mid-campaign",
            "tests/ was rewritten while this campaign ran, so these scores "
            "describe a grader that no longer exists. Re-run it against the "
            "current one; do not publish these numbers", "calibration"))

    rewards = [r["reward"] for r in rollouts
               if isinstance(r.get("reward"), (int, float))
               and r.get("zero_class") != "void"]
    if rewards and (len(set(rewards)) == 1):
        findings.append(Finding(
            Severity.BLOCKER, "no-variance",
            f"every valid rollout scored {rewards[0]}; a task the model always passes "
            "or always fails teaches nothing", "calibration"))

    for r in rollouts:
        if not isinstance(r.get("reward"), (int, float)) and r.get("zero_class") != "void":
            findings.append(Finding(
                Severity.BLOCKER, "non-numeric-reward",
                f"rollout {r.get('id')} reward is {type(r.get('reward')).__name__}; "
                "a string where a number is expected voids the trial silently",
                "calibration"))

    # A zero the model did not earn. `misses` records, per failed objective,
    # whether the submission was the reference answer in another form. If it
    # was, the check is measuring transport rather than capability: the answer
    # was right and the grader could not read it.
    #
    # Measured 2026-09-17 on kw-a007: four checks carrying 34 weight scored 0
    # across ten rollouts on submissions holding the reference headings
    # verbatim, differing only by the markdown `#` the parser strips. The
    # instruction never stated which form to use, so both were defensible --
    # the task was ambiguous, not hard, and its mean of 0.104 was not a
    # difficulty measurement. Nothing else in the chain can see this: golden is
    # 1.0, seed-zero is 0.0, the grader is self-consistent, and the zero looks
    # earned.
    wrongly_zeroed: dict[str, int] = {}
    near: dict[str, float] = {}
    for r in rollouts:
        for cid, shape in (r.get("misses") or {}).items():
            if shape == "equal_normalised":
                wrongly_zeroed[cid] = wrongly_zeroed.get(cid, 0) + 1
            elif isinstance(shape, str) and shape.startswith("overlap_"):
                try:
                    near[cid] = max(near.get(cid, 0.0), float(shape.split("_")[1]))
                except (IndexError, ValueError):
                    pass
    for cid, count in sorted(wrongly_zeroed.items(), key=lambda kv: -kv[1]):
        findings.append(Finding(
            Severity.BLOCKER, "right-answer-scored-zero",
            f"check {cid!r} failed in {count} rollout(s) where the submission "
            "equals the reference answer after normalisation -- the answer was "
            "right and the comparison could not see it. Fix the grader or state "
            "the convention in the instruction; do not publish this as "
            "difficulty", "calibration"))
    hot = {c: v for c, v in near.items() if v >= 0.8 and c not in wrongly_zeroed}
    if hot:
        findings.append(Finding(
            Severity.WARN, "near-miss-scored-zero",
            "these checks scored 0 on submissions overlapping the reference by "
            "80%+: " + ", ".join(f"{c} ({v:.0%})" for c, v in sorted(hot.items()))
            + ". Exact set equality scores a one-item miss the same as answering "
            "nothing; confirm that is the intent", "calibration"))

    return findings, {"rollouts": len(rollouts), "void": len(voided),
                      "invalid_rate": round(invalid_rate, 3),
                      "distinct_rewards": len(set(rewards)),
                      "right_answer_scored_zero": wrongly_zeroed,
                      "near_misses": {k: v for k, v in sorted(near.items())}}


def _typed_literals(expr, path="target"):
    """Every literal list anywhere in an expression tree, with where it sits.

    The first version of this check looked only at the top-level `op`, and the
    designer found the gap immediately: wrapping the hand-typed list in a
    `difference` slipped it through untouched. Measured on kw-a005 after the
    shallow check shipped -- eight of nine objectives, 92% of the weight, were
    `{"op": "difference", "a": {"op": "literal", "value": [...filenames...]}}`,
    reading no fixture file at all while the bundle sat GREEN.

    A scalar literal is a sentinel and legitimate at any depth. A list is an
    answer key wherever it appears.
    """
    found = []
    if isinstance(expr, dict):
        if expr.get("op") == "literal" and isinstance(expr.get("value"), (list, dict)):
            found.append(path)
        for key, sub in expr.items():
            if key in ("op", "value", "why", "field", "file"):
                continue
            found.extend(_typed_literals(sub, f"{path}.{key}"))
    elif isinstance(expr, list):
        for i, sub in enumerate(expr):
            found.extend(_typed_literals(sub, f"{path}[{i}]"))
    return found


def _reference_answer(ctx: GateContext) -> tuple[list[Finding], dict]:
    """The reference answer must be something a careful reader could produce.

    These rules already ran inside the designer, and that was not enough. A
    check that only fires while generating protects the generation, not the
    artefact: a bundle authored before the rule existed, rebuilt by an older
    designer, or edited by hand is never re-examined. Measured 2026-09-17,
    kw-a003 and kw-a010 both carried references the designer would now refuse
    and both passed the whole chain GREEN, because nothing downstream reads the
    reference answer at all.

    Every defect here is invisible to the rest of the chain by construction.
    The grader is self-consistent with its own key, so `golden` is 1.0 and
    `seed_zero` is 0.0 however nonsensical that key is, and the resulting zeros
    read as difficulty.
    """
    from collections import Counter

    submission = ctx.path("solution", "submission")
    if not submission.is_dir():
        return [Finding(Severity.BLOCKER, "no-reference-answer",
                        "solution/submission/ is absent; there is no reference "
                        "answer to check", "solution/submission")], {}

    findings: list[Finding] = []
    inspected = 0
    for path in sorted(submission.rglob("*")):
        if not path.is_file() or path.suffix != ".json":
            continue
        try:
            doc = json.loads(path.read_text())
        except (json.JSONDecodeError, OSError) as exc:
            findings.append(Finding(
                Severity.BLOCKER, "reference-unreadable",
                f"{path.name} does not parse: {exc}", "solution/submission"))
            continue
        if not isinstance(doc, dict):
            continue
        for field, value in doc.items():
            inspected += 1
            where = f"{path.name}.{field}"
            if value is None:
                findings.append(Finding(
                    Severity.BLOCKER, "reference-null",
                    f"{where} is null: the projection returned rows but could "
                    "not read the plucked field, so the task is unanswerable",
                    "solution/submission"))
                continue
            if not isinstance(value, list) or not value:
                continue
            if all(v is None for v in value):
                findings.append(Finding(
                    Severity.BLOCKER, "reference-null",
                    f"{where} is {len(value)} nulls; no reader produces that",
                    "solution/submission"))
                continue
            if any(v is None for v in value):
                findings.append(Finding(
                    Severity.WARN, "reference-partial-null",
                    f"{where} holds {sum(1 for v in value if v is None)} nulls "
                    "among real values", "solution/submission"))
            if len(value) < 8:
                continue
            counts = Counter(str(v).casefold() for v in value)
            if len(counts) / len(value) < 0.5:
                findings.append(Finding(
                    Severity.WARN, "reference-mostly-repeats",
                    f"{where}: {len(value)} entries, only {len(counts)} "
                    "distinct -- the projection is plucking a field that does "
                    "not identify anything", "solution/submission"))
                continue
            top, n = counts.most_common(1)[0]
            if n / len(value) >= 0.25:
                findings.append(Finding(
                    Severity.WARN, "reference-value-dominates",
                    f"{where}: {top!r} appears {n} times in {len(value)} "
                    f"entries ({n / len(value):.0%}); a label repeated that "
                    "often labels nothing", "solution/submission"))

    # Weight budget. Scoring is `earned / sum(weights)`, so only ratios ever
    # mattered and nothing enforced a common denominator: this batch shipped
    # totals from 84 to 128, which made `weight: 20` worth 24% of one task and
    # 16% of another while reading identically in both rubrics. Normalising to
    # 100 costs nothing -- it is score-neutral up to rounding -- and makes a
    # weight mean the percentage of the task it is worth.
    checks_path = ctx.path("tests", "checks.json")
    if checks_path.is_file():
        try:
            declared = json.loads(checks_path.read_text()).get("checks", [])
        except (json.JSONDecodeError, OSError):
            declared = []
        objectives = [c for c in declared if c.get("kind") == "objective"]
        budget = sum(c.get("weight", 0) for c in objectives)
        # The per-task floor, on what actually ships. `author.validate` holds
        # the designer's draft to it; this holds the built grader to it, so a
        # hand-edited checks.json cannot slip under it.
        from ..policy import MIN_OBJECTIVES
        if len(objectives) < MIN_OBJECTIVES:
            findings.append(Finding(
                Severity.BLOCKER, "objective-count",
                f"{len(objectives)} objective checks; every task carries at least "
                f"{MIN_OBJECTIVES} (policy.MIN_OBJECTIVES)", "tests/checks.json"))
        if objectives and budget != WEIGHT_TOTAL:
            findings.append(Finding(
                Severity.BLOCKER, "weight-budget",
                f"objective weights sum to {budget}, not {WEIGHT_TOTAL}; a "
                "weight is meant to read as the percentage of the task a check "
                "is worth, and it cannot while the denominator moves between "
                "bundles", "tests/checks.json"))
        typed = [(c["id"], c.get("weight", 0), _typed_literals(c.get("target")))
                 for c in objectives if _typed_literals(c.get("target"))]
        if typed:
            findings.append(Finding(
                Severity.BLOCKER, "hand-typed-answer-set",
                "these checks carry a literal LIST as their target, which is an "
                "answer key typed in by hand rather than recomputed from the "
                "fixture: "
                + "; ".join(f"{cid} (w={w}) at {', '.join(where)}"
                             for cid, w, where in typed) +
                ". A literal is for a scalar sentinel; a set must be an "
                "expression over the projections", "tests/checks.json"))
        zero = [c["id"] for c in objectives if c.get("weight", 0) <= 0]
        if zero:
            findings.append(Finding(
                Severity.BLOCKER, "zero-weight-objective",
                f"objectives carrying no weight: {', '.join(zero)}. They are "
                "scored, reported and worth nothing", "tests/checks.json"))

    points, shares = _documented_points(ctx)
    findings.extend(points)

    return findings, {"fields_inspected": inspected, "effective_shares": shares,
                      "weight_budget": sum(
                          c.get("weight", 0) for c in
                          (json.loads(checks_path.read_text()).get("checks", [])
                           if checks_path.is_file() else [])
                          if c.get("kind") == "objective")}


#: Documented shares are written to six decimals; anything beyond rounding is
#: a rubric that reads one way and scores another.
SHARE_TOLERANCE = 5e-6


def _documented_points(ctx: GateContext) -> tuple[list[Finding], dict]:
    """[G4] What reward.toml says each check is worth must be what the grader
    pays for it.

    The grader scores a step as `earned / step points` and Harbor averages the
    steps (`multi_step_reward_strategy`), so a check's real share of the task is
    `points / step points / steps`. reward.toml used to document raw weights
    over the whole task: in the audited schedule bundle a step-2 check
    documented as 10/100 paid 13.9%. The share is recomputed here from
    checks.json, rubric.json and task.toml -- the files that grade -- and
    compared with what the bundle documents."""
    import tomllib
    from ..author.build import effective_shares
    findings: list[Finding] = []
    # `bundle.structure` (this gate's prerequisite) already blocks a bundle
    # missing either file, so there is nothing further to recompute here.
    if not (ctx.path("tests/rubric.json").is_file() and ctx.path("tests/reward.toml").is_file()):
        return [], {"note": "rubric.json or reward.toml absent; bundle.structure blocks that"}
    try:
        checks = json.loads(ctx.path("tests/checks.json").read_text()).get("checks", [])
        rubric = json.loads(ctx.path("tests/rubric.json").read_text())
        task = tomllib.loads(ctx.path("task.toml").read_text())
        reward = tomllib.loads(ctx.path("tests/reward.toml").read_text())
    except (OSError, ValueError) as exc:
        return [Finding(Severity.BLOCKER, "points-unverifiable",
                        f"cannot recompute the scoring the bundle documents: {exc}",
                        "tests/reward.toml")], {}
    steps = [s.get("name") for s in task.get("steps") or []] or list(rubric)
    strategy = task.get("multi_step_reward_strategy", "mean")
    if len(steps) > 1 and strategy != "mean":
        return [Finding(Severity.BLOCKER, "points-unverifiable",
                        f"multi_step_reward_strategy {strategy!r} has no documented share "
                        "computation here; only 'mean' is verified", "task.toml")], {}
    ordered = {name: rubric.get(name, []) for name in steps}
    actual = effective_shares(checks, ordered)
    documented = reward.get("shares") or {}
    by_id = {c.get("id"): c for c in checks}
    for cid, share in sorted(actual.items()):
        row = documented.get(cid)
        doc = row.get("task_share") if isinstance(row, dict) else None
        if not isinstance(doc, (int, float)):
            findings.append(Finding(
                Severity.BLOCKER, "points-undocumented",
                f"check {cid!r} is worth {share:.4f} of the task as graded, and reward.toml "
                "does not document its share", "tests/reward.toml"))
        elif abs(doc - share) > SHARE_TOLERANCE:
            findings.append(Finding(
                Severity.BLOCKER, "points-drift",
                f"reward.toml documents check {cid!r} at {doc:.4f} of the task; the grader "
                f"pays {share:.4f} ({by_id[cid].get('weight')} of step "
                f"{by_id[cid].get('step')!r}'s points, averaged over {len(steps)} step(s))",
                "tests/reward.toml"))
        elif isinstance(row, dict) and row.get("points") != by_id[cid].get("weight"):
            findings.append(Finding(
                Severity.BLOCKER, "points-drift",
                f"reward.toml documents check {cid!r} at {row.get('points')} points; "
                f"checks.json scores it at {by_id[cid].get('weight')}", "tests/reward.toml"))
    for cid in sorted(set(documented) - set(actual)):
        findings.append(Finding(
            Severity.BLOCKER, "points-drift",
            f"reward.toml documents a share for {cid!r}, which no step scores",
            "tests/reward.toml"))
    blocks = {b.get("step") or b.get("name"): b for b in reward.get("reward") or []
              if isinstance(b, dict)}
    for name in steps:
        owned = [by_id[c] for c in ordered[name] if by_id.get(c, {}).get("kind") == "objective"]
        block = blocks.get(name)
        points = sum(c.get("weight", 0) for c in owned)
        dims: dict[str, float] = {}
        for c in owned:
            dims[c.get("dimension", "core")] = dims.get(c.get("dimension", "core"), 0) + c.get("weight", 0)
        if block is None:
            findings.append(Finding(
                Severity.BLOCKER, "points-undocumented",
                f"reward.toml has no [[reward]] block for step {name!r}", "tests/reward.toml"))
            continue
        if (block.get("points") != points or dict(block.get("weights") or {}) != dims
                or abs((block.get("task_share") or 0) - 1 / len(steps)) > SHARE_TOLERANCE):
            findings.append(Finding(
                Severity.BLOCKER, "points-drift",
                f"reward.toml step {name!r} documents {block.get('points')} points, share "
                f"{block.get('task_share')} and weights {dict(block.get('weights') or {})}; the "
                f"grader scores {points} points at share {1 / len(steps):.6f} with {dims}",
                "tests/reward.toml"))
    return findings, {cid: round(v, 6) for cid, v in actual.items()}


derivation_gate = FunctionGate("answer.derivation", _derivation,
                               requires=("bundle.structure",))
leak_gate = FunctionGate("leak.sweep", _leak_sweep, requires=("bundle.structure",))
reference_gate = FunctionGate("grader.reference", _reference_answer,
                              requires=("bundle.structure",))
bands_gate = FunctionGate("calibration.bands", _bands, requires=("bundle.structure",))
validity_gate = FunctionGate("calibration.validity", _validity,
                             requires=("bundle.structure",))
