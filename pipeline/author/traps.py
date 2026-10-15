"""Trap taxonomy: how difficulty is added without breaking the task.

The spec asks for "realistic traps that catch sloppy work (misleading labels,
unreadable sources, requests nothing can satisfy)" and then binds them: "every
trap must be beatable with the given tools, and include a reference solution
that proves it", and "traps should catch faulty reasoning, not a correct answer
that's simply written differently."

Those two sentences are the whole design space. A trap that cannot be beaten is
not a hard task, it is a broken one, and it produces zeros that are measurement
error rather than evidence about a model.

## On "the model should give up"

Wanting a model to hit a wall is the right instinct aimed at the wrong target.
A task every model fails carries exactly as much information as one every model
passes: none. One corpus here contains a task both models scored 0.00 on and
another both scored 1.00 on, and neither taught anything.

There is a legitimate version, and it is the `UNSATISFIABLE` trap below: part of
the correct answer is recognising that something cannot be done and reporting
that, rather than fabricating a result. Then "giving up" is not a failure to
grade around -- it is the graded behaviour, it is checkable, and the models that
fail it fail by *inventing* an answer. That is a real capability gap, and in this
corpus it is a common one.

The other place strong models reliably break is restraint: they over-act. A
guardrail enforces an explicit public constraint and is usually what
separates frontier models, because the capable ones "helpfully" fix the adjacent
thing they were told to leave alone.

So difficulty is loaded as: hard to work out (inference) + long dependent chain
(execution) + easy to break something (restraint), with per-check pass rates
landing in 30-70% and one or two stretch checks below 30%. Not a wall.

## Faithfulness, and invented traps

Traps come in two provenances, and both are legitimate. The spec is explicit:
"You can add tools or extra cases beyond what the original trace used - if that
makes the task more realistic or more challenging, as long as the environment
stays grounded in the domain and situation of the source trace."

  TRACE_DERIVED  the trap IS a user correction, turned into something a script
                 can check. It cites the moment and quotes the words.
  AUTHORED       we invented it. It cites no moment, and instead names the
                 fixture surface it rests on and why a practitioner in this
                 domain would plausibly meet it.

An authored trap is not a weaker trap -- some of the sharpest ones cannot come
from a trace, because the user never hit that case. What it must not be is
*ungrounded*: a trap resting on a surface the scenario does not have is a puzzle
wearing the domain as a costume, and that is the fidelity complaint we are
answering.

So the gate enforces a floor on the trace-derived share rather than demanding
100%, and it requires every authored trap to name a real fixture surface. The
difficulty can be invented; the world it happens in cannot.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

Axis = Literal["inference", "execution", "restraint"]
Lever = Literal["join", "arbitration", "carry", "restraint", "sequence"]


@dataclass(frozen=True)
class TrapType:
    key: str
    summary: str
    #: Stage D correction classes this trap may be derived from. Empty means the
    #: trap is structural and needs no trace moment -- there are none.
    from_classes: tuple[str, ...]
    axis: Axis
    lever: Lever
    #: What the author must supply to prove the trap is beatable and fair.
    proof: str
    #: How it fails when done badly.
    failure_mode: str


TAXONOMY: dict[str, TrapType] = {t.key: t for t in (
    TrapType(
        "misleading_label",
        "A record, file or field is named one thing and holds another; the "
        "correct answer follows the content, not the label.",
        ("spec_correction", "persistent_defect"),
        "inference", "arbitration",
        "Reference solution reads the content and ignores the label; a probe that "
        "trusts the label scores strictly less than 1.0.",
        "If the label is the ONLY signal, the task is a coin flip. The content "
        "must be unambiguous once read.",
    ),
    TrapType(
        "stale_authority",
        "Three sources state a value; two are stale or wrong and one is "
        "authoritative. The stale ones disagree with EACH OTHER, so neither can "
        "simply be copied.",
        ("spec_correction", "revert_request"),
        "inference", "arbitration",
        "The instruction or fixture makes the authoritative source unambiguous, "
        "and the reference solution cites it.",
        "Ambiguous authority yields defensible wrong answers -- a broken task, "
        "not a hard one. This is non-negotiable.",
    ),
    TrapType(
        "unreadable_source",
        "A needed source cannot be read the obvious way (wrong extension, "
        "wrong encoding, a container) and must be recovered with the tools given.",
        ("persistent_defect", "spec_correction"),
        "execution", "carry",
        "Reference solution recovers it using only the exposed tools, in the "
        "declared resource budget.",
        "If recovery needs a tool the agent does not have, every zero is "
        "environment error.",
    ),
    TrapType(
        "unsatisfiable",
        "Part of the request cannot be met. The correct answer reports that, "
        "with the reason, and completes everything that CAN be done.",
        ("persistent_defect", "constraint_assertion"),
        "inference", "arbitration",
        "Reference solution reports the impossibility in the required output "
        "field AND completes the satisfiable remainder; a probe that fabricates "
        "a result scores 0 on that check.",
        "If the impossibility is not reportable in the output contract, the "
        "agent has no way to be right. The contract must have a field for it.",
    ),
    TrapType(
        "forbidden_edit",
        "The user's own words forbid touching something. Violating it zeroes "
        "the task.",
        ("constraint_assertion", "scope_correction"),
        "restraint", "restraint",
        "Guardrail passes on the pristine fixture; a probe that edits the "
        "protected surface zeroes.",
        "Never gate anything on it, and never fingerprint a READ -- a guardrail "
        "keyed on last_visited_at zeroes every competent attempt.",
    ),
    TrapType(
        "scope_creep_bait",
        "Something adjacent is visibly broken and out of scope. Fixing it is a "
        "guardrail violation.",
        ("scope_correction", "constraint_assertion"),
        "restraint", "restraint",
        "Guardrail passes pristine; reference solution leaves it broken.",
        "The bait must be plainly out of the stated scope, or the task punishes "
        "a defensible reading.",
    ),
    TrapType(
        "regression_bait",
        "The obvious fix for A silently breaks B. Only a fix that preserves B "
        "passes both checks.",
        ("persistent_defect",),
        "execution", "carry",
        "Reference solution passes A and B together; the naive fix passes A and "
        "fails B, demonstrated by a probe.",
        "B must be discoverable -- a test, a document, or a stated invariant. A "
        "hidden B is an unpublished rule.",
    ),
    TrapType(
        "plausible_decoy",
        "A structurally identical wrong candidate differs on the single "
        "attribute the task turns on.",
        ("spec_correction", "persistent_defect"),
        "inference", "join",
        "A probe returning the decoy scores strictly less than 1.0, and the "
        "distinguishing attribute is stated in the agent-visible surface.",
        "A decoy refutable at a glance is a free hint, not a trap -- it lowers "
        "difficulty by confirming the agent is on the right track.",
    ),
    TrapType(
        "derived_answer",
        "The answer exists in no record: it is an intersection, a difference or "
        "a computation over two surfaces.",
        ("spec_correction", "persistent_defect"),
        "inference", "join",
        "Neither input set is enumerated anywhere, and answer.derivation finds "
        "no stored form.",
        "Not really a trap -- it is the §0 design rule, and it is the only "
        "defence against reward hacking that cannot be bypassed.",
    ),
)}


#: Minimum share of the trace's USABLE CORRECTIONS that a bundle turns into
#: traps -- not the share of its traps that came from the trace.
#:
#: The difference matters and the first version had it backwards. Measuring
#: trace-derived / total-traps makes every good authored trap *lower* the score,
#: so a bundle that exploits all five of its corrections and then adds four
#: well-grounded hazards looks less faithful than one that uses three and stops.
#: That is perverse: adding grounded difficulty does not make a task less
#: faithful to its trace, and the trap budget scales with trace size precisely
#: so that rich material carries more.
#:
#: So the question is "did you use what the trace gave you?", not "did you
#: refrain from adding anything". Authored traps are then unbounded in number and
#: bounded in kind: each must name a fixture surface that exists and say why a
#: practitioner here would meet the case.
TRACE_DERIVED_FLOOR = 0.5


@dataclass
class Trap:
    """One instantiated trap in a bundle."""
    id: str
    type: str
    surface: str                      # where it lives in the fixture
    beatable_by: str                  # reference-solution step that defeats it
    probe: str                        # adversarial probe that must NOT score 1.0
    provenance: str = "trace_derived"  # trace_derived | authored
    derived_from: str = ""            # session::msg citation (trace_derived)
    correction_class: str = ""        # Stage D class of that moment (trace_derived)
    quote: str = ""                   # the user's words, verbatim (trace_derived)
    grounding: str = ""               # why the scenario supports it (authored)
    grounded_in: str = ""             # a fixture path the trap rests on (authored)
    checks: list[str] = field(default_factory=list)   # check ids it drives

    def validate(self) -> list[str]:
        """Structural problems an author must fix before the gate will pass."""
        problems: list[str] = []
        spec = TAXONOMY.get(self.type)
        if spec is None:
            return [f"unknown trap type {self.type!r}"]

        if self.provenance == "trace_derived":
            if not self.derived_from:
                problems.append(
                    f"{self.id}: declared trace_derived but cites no moment. Mark it "
                    "authored and ground it, or supply the citation")
            if self.correction_class not in spec.from_classes:
                problems.append(
                    f"{self.id}: type {self.type!r} may be derived from "
                    f"{list(spec.from_classes)}, not {self.correction_class!r}")
            if not self.quote.strip():
                problems.append(f"{self.id}: no quoted user words")
        elif self.provenance == "authored":
            if not self.grounding.strip():
                problems.append(
                    f"{self.id}: authored traps must say why a practitioner in this "
                    "scenario would plausibly meet this case")
            if not self.grounded_in.strip():
                problems.append(
                    f"{self.id}: authored traps must name the fixture surface they "
                    "rest on; a trap on a surface the scenario lacks is a puzzle "
                    "wearing the domain as a costume")
            if self.derived_from:
                problems.append(
                    f"{self.id}: marked authored but carries a trace citation -- "
                    "mark it trace_derived so it counts toward faithfulness")
        else:
            problems.append(f"{self.id}: provenance must be trace_derived or authored, "
                            f"not {self.provenance!r}")

        if not self.beatable_by.strip():
            problems.append(
                f"{self.id}: no reference-solution step -- the spec requires a "
                "reference solution proving every trap is beatable")
        if not self.probe.strip():
            problems.append(
                f"{self.id}: no adversarial probe -- without one, nothing shows "
                "the trap catches the sloppy answer")
        if not self.checks:
            problems.append(f"{self.id}: drives no check, so it cannot affect a score")
        return problems


def trace_derived_share(traps: list[Trap]) -> float:
    """Share of traps that came from the trace. Reported, never gated on --
    see TRACE_DERIVED_FLOOR for why."""
    if not traps:
        return 0.0
    return sum(1 for t in traps if t.provenance == "trace_derived") / len(traps)


def trace_exploitation(traps: list[Trap], usable_corrections: int) -> float:
    """How much of the trace's own correction material became a trap.

    Capped at 1.0: two traps from one correction is thoroughness, not extra
    credit. A bundle scoring 1.0 has used every usable correction the classifier
    found, whatever else it also added.
    """
    if usable_corrections <= 0:
        return 0.0
    derived = len({t.derived_from for t in traps
                   if t.provenance == "trace_derived" and t.derived_from})
    return min(derived / usable_corrections, 1.0)


def axes_loaded(traps: list[Trap]) -> set[str]:
    return {TAXONOMY[t.type].axis for t in traps if t.type in TAXONOMY}


def levers_used(traps: list[Trap]) -> set[str]:
    return {TAXONOMY[t.type].lever for t in traps if t.type in TAXONOMY}


def suggest(correction_class: str) -> list[TrapType]:
    """Which traps a given Stage D correction class can legitimately become.

    This is the bridge from trace to difficulty: the classifier says what the
    user actually complained about, and this says what that complaint can
    become without inventing anything.
    """
    return [t for t in TAXONOMY.values() if correction_class in t.from_classes]
