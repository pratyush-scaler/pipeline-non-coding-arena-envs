"""Batch-6 static design gate: conjunctive-hard shape, executed misreading additivity, leaks (2026-10-13; B8 2026-10-15).

    python3.11 -I -B design_lint.py <task-dir> [--no-additivity] [--b8] [--json out.json]

Arena 261013 / spec 10_12 asked for (1) varied decisive traps, (2) difficulty spread over several INDEPENDENTLY
failing checks so partial progress earns partial reward, (3) every inference resolvable from the materials.
This gate checks a task against the batch-6 design before any model runs:

  map        authoring/traps.json maps every objective check to exactly one premise, or lists it as coverage
  count      single-step: >= 4 premises; multi-step: >= 2 per step and >= 5 distinct families across the task
  families   premises in one step are from distinct families (catalogue below); at most 1 timestamp-ordering
             premise per task
  weights    per step: every premise <= 25% of the step's points, premises together >= 55%, coverage <= 35%
  quotes     each premise's resolving quote appears verbatim (whitespace-normalised) in its fixture file
  additivity solve.py honours ARENA_MISREAD="P1,P3": for every subset of a step's premises the grader must fail
             EXACTLY the union of those premises' checks and score exactly 1 - sum(weights)/total -- i.e. each
             premise fails on its own, no cascade, and partial progress earns partial reward
             (a premise whose traps.json masked_by names another misread premise in the subset is graded against
             that deliverable's own upstream answer and is not expected to fail there; masked_by <= interlocks_with)
  runtime    every shipped runtime copy carries the 261011 central patches (criteria-format tasks)
  leaks      no reference-answer value appears in an instruction unless traps.json justifies it (leak_allow)
  metadata   task.toml [metadata] trap_families equals the families in traps.json
  templates  a decisive premise's `template` is a trap-library id or alias (production/traps/library.json; without a
             library, the built-in B7 catalogue below): dead or any D id (the dead list) -> FAIL, literature /
             trace-derived / bimodal -> WARN "pilot first", unknown -> FAIL
  B8         schema b8/premises/1 (or --b8): >= 3 decisive premises over >= 2 library families, >= 1 aimed at Fable
             and >= 1 at Astra, each with >= 2 verbatim anchors in >= 2 files other than its resolving quote's file
             (a convention_inference mode, T2/T7: >= 1 verbatim anchor carrying the discriminating figure),
             no clock premise heaviest, projected free share (100 - decisive weight) <= 40 per step, no decisive
             STATED premise, and no digit/ID/fixture value inside an instruction example ("e.g.", "such as", ...).
             Older schemas get these as warnings only.

Exit 0 only if every hard rule passes. Warnings never change the exit code.
"""
from __future__ import annotations

import itertools
import json
import os
import re
import subprocess
import sys
import tempfile
import tomllib
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import paths  # noqa: E402

PY = paths.PY311
FIX = paths.FIX

FAMILIES = {
    "wrong_figure_vs_derivation": "a repeated wrong figure against a governing derivation rule",
    "changed_premise": "a revision silently invalidates results already worked out",
    "population_reshaped": "a later exclusion/retirement reshapes the population behind an aggregate",
    "version_in_force": "the document/norm version in force at the as-of date",
    "identity_variants_twins": "one entity under several names / near-twins that must stay apart (key supplied)",
    "governing_vs_filing_key": "the governing key is not the filing/linkage key",
    "house_convention_numeric": "a stated house convention the default number/date handling gets wrong",
    "caption_only_rule": "a rule carried only by a caption, legend, footnote or code table",
    "coverage_counting_unit": "a coverage audit with a counting-unit boundary (silent omissions)",
    "scope_compliant_twins": "scope of a change: compliant near-twins and out-of-scope items stay out",
    "answerability": "not determinable vs resolvable, decided by stated evidence rules",
    "composition_totals_tie": "the composition is wrong although the totals tie",
    "stacked_rules_order": "stacked rules / an order-dependent allocation stated in the materials",
    "clean_baseline": "keeping the 'before' baseline clean in a before/after comparison",
    "event_key_mismatch": "the rule keys on one event, the records report another (defining sentence given)",
    "literal_overreading": "a restated rule read too literally against its governing scope",
    "precedent_rule": "a rule stated through worked precedents/rulings",
    "timestamp_ordering": "ordering by untrustworthy timestamps (clock offset, backup store, outage)",
}
# B7 (briefs/TRAP-CATALOG-B7.md, 2026-10-15): decisive traps are built from measured templates. Since B8 the trap
# library is the source of truth; this dict is the fallback when no library.json exists (T* proven, L* literature).
TEMPLATES = {
    "T1": "keying slip reversed by 2+ parties' anchors",
    "T2": "convention fixed only by worked figures in the governing document",
    "T3": "quantity basis cued on the record itself (tax-inclusive, per pack/pair with a tally)",
    "T4": "already in hand, shown by a technical bridge in a first-hand record",
    "T5": "misfiled note whose content can only be about another item",
    "T6": "edition/rate by the real date, sources of similar authority",
    "T7": "convention from two worked figures by different parties",
    "T8": "changed premise received before issue (filler)",
    "T9": "rule-scope shield: a real rule on a neighbouring value is over-applied to the graded one",
    "L1": "later restatement replaces the first-reported figure (record reversal)",
    "L2": "older edition governs by the event's own date",
    "L3": "wrong anchor event starts a period or deadline",
    "L4": "fiscal vs calendar period mapping",
    "L5": "cumulative vs period figures",
}
# library family and aim of each built-in template (fallback only; the library's own values win)
BUILTIN_META = {"T1": ("record_reversal", "both"), "T2": ("convention_inference", "astra"),
                "T3": ("quantity_basis", "both"), "T4": ("possession_state", "fable"),
                "T5": ("record_reversal", "fable"), "T6": ("authority_selection", "both"),
                "T7": ("convention_inference", "fable"), "T8": ("revision_supersession", "fable"),
                "T9": ("rule_scope", "fable"), "L1": ("revision_supersession", "unknown"),
                "L2": ("authority_selection", "unknown"), "L3": ("temporal_anchor", "unknown"),
                "L4": ("temporal_anchor", "unknown"), "L5": ("aggregation_basis", "unknown")}
PILOT_FIRST = ("literature", "trace-derived", "bimodal")
B8_SCHEMA = "b8/premises/1"
B8_MIN_DECISIVE, B8_MIN_FAMILIES, B8_MIN_ANCHOR_FILES, B8_MAX_FREE = 3, 2, 2, 0.40
B8_FIGURE_FAMILIES = {"convention_inference"}  # evidenced by one discriminating worked figure, not by parties' anchors
MIN_PREMISES_SINGLE = 4
MIN_PREMISES_PER_STEP_MULTI = 2
MIN_FAMILIES_MULTI = 5
MAX_PREMISE_SHARE = 0.25
MIN_TRAP_SHARE = 0.55
MAX_FREE_SHARE = 0.35
MAX_TIMESTAMP = 1


def norm(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


# B6v2 (HARD-DOCTRINE-B6v2.md, 2026-10-13): stated-rule premises measured 0/650; the decisive fact must be inferred.
HARD = {"EVENT", "ACTUAL", "TWIN", "STORE", "ATTR", "BASELINE", "SCALE", "PARSE", "CLOCK", "REVISED", "EXEMPLAR", "AGGREGATE"}
MECHANISMS = HARD | {"HALF", "STATED"}
FABLE_TYPE = {"EVENT", "ACTUAL", "BASELINE", "ATTR", "CLOCK", "REVISED", "EXEMPLAR", "AGGREGATE"}
ASTRA_TYPE = {"TWIN", "STORE", "CLOCK", "SCALE", "PARSE", "REVISED", "EXEMPLAR", "AGGREGATE"}
MIN_HARD_SINGLE, MIN_HARD_PER_STEP_MULTI, ECHO_N = 3, 2, 5


def words(text: str) -> list:
    return re.findall(r"[0-9a-zа-яё؀-ۿЀ-ӿ]+", text.lower())


def ngrams(text: str, n: int) -> set:
    w = words(text)
    return {" ".join(w[i:i + n]) for i in range(len(w) - n + 1)}


def v2_checks(task, steps, checks, premises, R):
    files = task / "environment/files"
    multi = len(steps) > 1
    by_id = {p["id"]: p for p in premises}
    for p in premises:
        m = p.get("mechanism")
        if m not in MECHANISMS:
            R.fail(f"{p['id']}: mechanism {m!r} not in {sorted(MECHANISMS)}")
            continue
        if not p.get("default_technique"):
            R.fail(f"{p['id']}: default_technique missing (name the parser/sort/regex that produces the wrong answer)")
        anchors = p.get("anchors") or []
        if m in HARD:
            afiles = set()
            for a in anchors:
                f, text = a.get("file"), a.get("text", "")
                path = files / str(f)
                if not f or not text or not path.is_file():
                    R.fail(f"{p['id']}: anchor {a!r} needs an existing file and text")
                elif norm(text) not in norm(path.read_text(errors="replace")):
                    R.fail(f"{p['id']}: anchor text not found verbatim in {f}")
                else:
                    afiles.add(f)
            if len(afiles) < 2:
                R.fail(f"{p['id']}: {m} needs >= 2 verbatim anchors in >= 2 different files (has {len(afiles)} file(s))")
        for other in p.get("interlocks_with") or []:
            if other not in by_id:
                R.fail(f"{p['id']}: interlocks_with names unknown premise {other}")
            elif p["id"] not in (by_id[other].get("interlocks_with") or []):
                R.fail(f"{p['id']}: interlock with {other} is not reciprocal")
        # masked_by (2026-10-14, deck-preread 2.3.0): a downstream premise graded against the deliverable's OWN upstream
        # answer is unobservable when the upstream premise is misread; it must be one of its interlocks and give a reason
        masked = p.get("masked_by") or []
        if masked and (not set(masked) <= set(p.get("interlocks_with") or []) or not p.get("masked_reason")):
            R.fail(f"{p['id']}: masked_by {masked} must name premises it interlocks with, and needs masked_reason")
    mechs = [p.get("mechanism") for p in premises]
    if sum(m == "STATED" for m in mechs) > 1:
        R.fail("more than one STATED premise (measured dead; filler only)")
    if sum(m == "CLOCK" for m in mechs) > 1:
        R.fail("more than one CLOCK premise")
    if not any(p.get("interlocks_with") for p in premises):
        R.fail("no interlocked pair (user 2026-10-13: combine traps on the same items)")
    for step, ids in steps.items():
        ps = [p for p in premises if p.get("step", "01-task") == step]
        hard = [p for p in ps if p.get("mechanism") in HARD]
        need = MIN_HARD_PER_STEP_MULTI if multi else MIN_HARD_SINGLE
        if len(hard) < need:
            R.fail(f"{step}: {len(hard)} inferred/default-technique premises (need >= {need})")
        if not multi:
            fab = sum(p.get("mechanism") in FABLE_TYPE for p in ps)
            ast = sum(p.get("mechanism") in ASTRA_TYPE for p in ps)
            if fab < 2 or ast < 2:
                R.fail(f"{step}: need >= 2 Fable-type and >= 2 Astra-type mechanisms (have {fab} and {ast})")
        # CLOCK never the heaviest premise of its step
        objs = {cid for cid in ids}
        wt = {p["id"]: sum(float(checks[c].get("weight", 0)) for c in p.get("checks", []) if c in checks and c in objs) for p in ps}
        clocks = [p["id"] for p in ps if p.get("mechanism") == "CLOCK"]
        if clocks and wt and max(wt, key=wt.get) in clocks and len(ps) > 1 and wt[clocks[0]] >= max(v for k, v in wt.items() if k not in clocks):
            R.fail(f"{step}: the CLOCK premise is the heaviest premise of the step")
        # instruction echo: no 5-word run shared with a rule quote or an anchor
        inst = (task / "steps" / step / "instruction.md")
        if inst.is_file():
            ig = ngrams(inst.read_text(errors="replace"), ECHO_N)
            for p in ps:
                texts = [(p.get("resolving_quote") or {}).get("text", "")] + [a.get("text", "") for a in p.get("anchors") or []]
                shared = set().union(*(ngrams(t, ECHO_N) for t in texts)) & ig
                if shared:
                    R.fail(f"{step}: {p['id']} rule/anchor wording echoed in the instruction: {sorted(shared)[:3]}")
    if not R.fails:
        R.ok(f"v2: mechanisms {mechs}; interlocks {[(p['id'], p['interlocks_with']) for p in premises if p.get('interlocks_with')]}")


class Report:
    def __init__(self):
        self.fails, self.warns, self.oks = [], [], []

    def fail(self, msg):
        self.fails.append(msg)

    def warn(self, msg):
        self.warns.append(msg)

    def ok(self, msg):
        self.oks.append(msg)


class WarnOnly:
    """B8 rules on an older schema: report every would-be failure as a warning."""

    def __init__(self, R, why):
        self.R, self.why, self.fails = R, why, []

    def fail(self, msg):
        self.fails.append(msg)
        self.R.warn(f"{msg} [{self.why}]")

    def warn(self, msg):
        self.R.warn(msg)

    def ok(self, msg):
        self.R.ok(msg)


class Templates:
    """Decisive-premise templates: the trap library if one is built, else the built-in B7 catalogue."""

    def __init__(self, modes: dict, aliases: dict, source: str, error: str | None = None):
        self.modes, self.aliases, self.source, self.error = modes, aliases, source, error

    def resolve(self, name):
        name = str(name or "").strip()
        if name in self.modes:
            return self.modes[name]
        if name in self.aliases:
            return self.modes.get(self.aliases[name])
        fold = {k.lower(): k for k in list(self.modes) + list(self.aliases)}.get(name.lower())
        return self.resolve(fold) if fold else None


def builtin_templates(source: str = "built-in B7 catalogue", error: str | None = None) -> Templates:
    modes = {k: {"id": k, "name": v, "family": BUILTIN_META[k][0], "aimed_at": BUILTIN_META[k][1], "clock": False,
                 "status": "proven" if k.startswith("T") else "literature"} for k, v in TEMPLATES.items()}
    return Templates(modes, {}, source, error)


def load_templates(library: Path | None = None) -> Templates:
    """paths.LIBRARY through traplib. No library file -> the built-in dict; an unreadable one -> .error is set."""
    lib_path = Path(library) if library else paths.LIBRARY
    if not lib_path.is_file():
        return builtin_templates(f"built-in B7 catalogue (no trap library at {lib_path})")
    try:
        if str(paths.TRAPS) not in sys.path:
            sys.path.insert(0, str(paths.TRAPS))
        import traplib
        lib = traplib.load(lib_path)
    except Exception as exc:  # noqa: BLE001 -- reported as a gate failure by the caller
        return builtin_templates(f"built-in B7 catalogue (trap library unreadable)", f"{lib_path}: {exc}")
    return Templates(lib.modes, lib.aliases, f"trap library {lib_path} ({len(lib.modes)} modes)")


def dead_listed(mode: dict | None) -> bool:
    """A D id (the library's dead list), or a mode carrying one among its aliases (same rule as traplib.dead_listed)."""
    return bool(mode) and any(re.fullmatch(r"D[0-9]+", str(x)) for x in [mode.get("id")] + list(mode.get("aliases") or []))


def premise_aim(p: dict, mode: dict | None) -> str:
    """fable / astra / both / unknown: the premise's aimed_at (or target_model) first word, else the mode's."""
    for key in ("aimed_at", "target_model"):
        m = re.match(r"\s*(fable|astra|both)\b", str(p.get(key) or ""), re.I)
        if m:
            return m.group(1).lower()
    return (mode or {}).get("aimed_at") or "unknown"


def is_clock(p: dict, mode: dict | None) -> bool:
    return bool((mode or {}).get("clock")) or p.get("mechanism") == "CLOCK" or p.get("family") == "timestamp_ordering"


def b8_checks(task, steps, checks, objectives, premises, tpl: Templates, R):
    """The B8 composition rules (AUTHOR-BRIEF-B8.md). R may be a WarnOnly for older schemas."""
    files = task / "environment/files"
    dec = [p for p in premises if p.get("decisive")]
    modes = {p["id"]: tpl.resolve(p.get("template")) if p.get("template") else None for p in premises}
    n_fail = len(R.fails)
    if len(dec) < B8_MIN_DECISIVE:
        R.fail(f"B8: {len(dec)} decisive premise(s) (need >= {B8_MIN_DECISIVE}, each built from a library mode)")
    fams = sorted({modes[p["id"]]["family"] for p in dec if modes[p["id"]]})
    if len(fams) < B8_MIN_FAMILIES:
        R.fail(f"B8: decisive premises span {len(fams)} library famil{'y' if len(fams) == 1 else 'ies'} {fams} "
               f"(need >= {B8_MIN_FAMILIES})")
    aims = {p["id"]: premise_aim(p, modes[p["id"]]) for p in dec}
    for model in ("fable", "astra"):
        if not any(a in (model, "both") for a in aims.values()):
            R.fail(f"B8: no decisive premise is aimed at {model} (premise aimed_at, else the mode's): {aims}")
    for p in dec:
        if p.get("mechanism") == "STATED":
            R.fail(f"B8: {p['id']} is decisive but its mechanism is STATED (stated rules measured 0/1530 missed)")
        qfile = (p.get("resolving_quote") or {}).get("file")
        # a convention fixed by worked figures (T2/T7) is evidenced by ONE discriminating figure, usually inside the
        # governing document itself (T2 measured: one figure -> Astra 80-100%, a second figure kills it), so the
        # parties-and-files rule of a record reversal does not apply; it needs >= 1 verbatim figure anchor anywhere
        figure_mode = (modes[p["id"]] or {}).get("family") in B8_FIGURE_FAMILIES
        n, afiles = 0, set()
        for a in p.get("anchors") or []:
            f, text = (a.get("file"), a.get("text", "")) if isinstance(a, dict) else (None, "")
            if not f or (f == qfile and not figure_mode) or not text or not (files / str(f)).is_file():
                continue
            if norm(text) in norm((files / str(f)).read_text(errors="replace")):
                n += 1
                afiles.add(f)
        if figure_mode:
            if n < 1:
                R.fail(f"B8: {p['id']} ({modes[p['id']]['id']}, convention from worked figures) needs >= 1 verbatim "
                       f"anchor carrying the discriminating figure (has 0)")
        elif n < 2 or len(afiles) < B8_MIN_ANCHOR_FILES:
            R.fail(f"B8: {p['id']} needs >= 2 verbatim anchors in >= {B8_MIN_ANCHOR_FILES} files other than its "
                   f"resolving quote's file {qfile} (has {n} in {len(afiles)} file(s))")
    for step, ids in steps.items():
        objs = [c for c in ids if c in objectives]
        total = sum(float(checks[c].get("weight", 0)) for c in objs) or 1.0
        ps = [p for p in premises if p.get("step", "01-task") == step]
        wt = {p["id"]: sum(float(checks[c].get("weight", 0)) for c in p.get("checks", []) if c in objs) for p in ps}
        dec_w = sum(wt[p["id"]] for p in ps if p.get("decisive"))
        free = 1 - dec_w / total
        if free > B8_MAX_FREE + 1e-9:
            R.fail(f"B8: {step}: projected free share {free:.0%} = 100 - decisive weight {dec_w / total:.0%} "
                   f"(max {B8_MAX_FREE:.0%})")
        clocks = [p["id"] for p in ps if is_clock(p, modes.get(p["id"]))]
        others = [wt[k] for k in wt if k not in clocks]
        for c in clocks:
            if wt[c] > 0 and (not others or wt[c] >= max(others)):
                R.fail(f"B8: {step}: clock premise {c} is the heaviest premise of the step (never the primary failure)")
    if len(R.fails) == n_fail:
        R.ok(f"B8: {len(dec)} decisive premises over families {fams}; aims {aims}")


EXAMPLE_CUE = re.compile(r"(?i)(?<![\w])(e\.\s?g\.?|for example|for instance|such as|examples?:)")
QUOTED = re.compile(r"`([^`\n]{2,80})`|\"([^\"\n]{2,80})\"|«([^»\n]{2,80})»|“([^”\n]{2,80})”|'([^'\n]{2,80})'")


def example_leaks(task: Path, traps: dict) -> list[str]:
    """Instruction examples that carry a digit, an ID, or a value quoted from the fixture (memory: H01 in 'IDs such
    as' leaked). Field names, enum options and justified leak_allow values are exempt."""
    allow = {str(a.get("value")) for a in traps.get("leak_allow", []) if a.get("reason")}
    names = set()
    outputs = task / "tests/outputs.json"
    if outputs.is_file():
        def walk(s):
            if isinstance(s, dict):
                names.update(str(k) for k in (s.get("properties") or {}))
                names.update(str(e) for e in s.get("enum", []) or [])
                for x in s.values():
                    walk(x)
            elif isinstance(s, list):
                for x in s:
                    walk(x)
        walk(json.loads(outputs.read_text()))
    fixture = None
    hits = []
    for inst in sorted(task.glob("steps/*/instruction.md")):
        text = inst.read_text(errors="replace")
        for m in EXAMPLE_CUE.finditer(text):
            window = re.split(r"[.;!?](?:\s|$)|\n|\)", text[m.end(): m.end() + 160])[0]
            for v in sorted(allow, key=len, reverse=True):
                window = window.replace(v, " ")
            bad = [t for t in re.findall(r"[\w\-/.:]*\d[\w\-/.:]*", window) if t not in names]
            for q in QUOTED.finditer(window):
                val = next(g for g in q.groups() if g)
                if val in names or val in allow:
                    continue
                if fixture is None:
                    fixture = norm(" ".join(p.read_text(errors="replace").lower() for p in
                                            sorted((task / "environment/files").rglob("*")) if p.is_file()))
                if norm(val.lower()) in fixture:
                    bad.append(val)
            if bad:
                hits.append(f"{inst.parent.name}: '{m.group(0)}{window[:70].rstrip()}' carries {sorted(set(bad))[:4]}")
    return hits


def load_checks(task: Path):
    raw = json.loads((task / "tests/checks.json").read_text())
    if "checks" in raw:
        return {c["id"]: c for c in raw["checks"]}
    out = {}
    for step, s in raw.get("steps", {}).items():
        for o in s.get("objectives", []):
            out[o["id"]] = {**o, "kind": "objective", "step": step}
        for g in s.get("guards", []):
            out[g["id"]] = {**g, "kind": "guardrail", "step": step, "weight": 0}
    return out


def steps_of(task: Path, checks: dict) -> dict:
    rubric_file = task / "tests/rubric.json"
    if rubric_file.is_file():
        rubric = json.loads(rubric_file.read_text())
        if isinstance(rubric, dict) and rubric and all(isinstance(v, list) for v in rubric.values()):
            return {s: [c for c in ids if c in checks] for s, ids in rubric.items()}
    by = {}
    for cid, c in checks.items():
        by.setdefault(c.get("step", "01-task"), []).append(cid)
    return by


def run_solve(task: Path, step: str, out: Path, misread: str = "") -> None:
    sol = task / "steps" / step / "solution" / "solve.py"
    env = {**os.environ, "ARENA_SOURCE": str(task / "environment/files"), "ARENA_SUBMITTED": str(out),
           "ARENA_OUT": str(out), "ARENA_MISREAD": misread}
    proc = subprocess.run([PY, "-I", "-B", str(sol)], env=env, capture_output=True, text=True, cwd=sol.parent, timeout=600)
    if proc.returncode:
        raise RuntimeError(f"solve.py {step} ARENA_MISREAD={misread!r} exit {proc.returncode}: {proc.stderr.strip()[-300:]}")


def grade(task: Path, step: str, sub: Path) -> dict:
    logs = Path(tempfile.mkdtemp(prefix="lint-g-"))
    env = {**os.environ, "ARENA_SOURCE": str(task / "environment/files"), "ARENA_SUBMITTED": str(sub),
           "ARENA_STEP": step, "ARENA_REWARD": str(logs / "r.json"), "ARENA_DETAILS": str(logs / "d.json")}
    grader = task / "tests/criteria.py"
    if not grader.is_file():
        grader = task / "tests/grade.py"
    proc = subprocess.run([PY, "-I", "-B", str(grader)], env=env, capture_output=True, text=True, timeout=600)
    if not (logs / "r.json").is_file():
        raise RuntimeError(f"grader wrote no reward ({proc.stderr.strip()[-300:]})")
    reward = json.loads((logs / "r.json").read_text())["reward"]
    failed = set()
    if (logs / "d.json").is_file():
        for c in json.loads((logs / "d.json").read_text())["reward"]["criteria"]:
            if float(c.get("value", 0)) < 1.0:
                failed.add(c["name"])
    return {"reward": reward, "failed": failed}


def main(argv) -> int:
    task = Path(argv[0]).resolve()
    additivity = "--no-additivity" not in argv
    R = Report()
    meta = tomllib.loads((task / "task.toml").read_text())
    checks = load_checks(task)
    steps = steps_of(task, checks)
    tp = task / "authoring/traps.json"
    if not tp.is_file():
        R.fail("authoring/traps.json missing (the batch-6 premise map)")
        return finish(R, argv)
    traps = json.loads(tp.read_text())
    premises = traps.get("premises", [])
    coverage = set(traps.get("coverage_checks", []))
    objectives = {cid for cid, c in checks.items() if c.get("kind") == "objective"}
    schema = str(traps.get("schema", ""))
    b8 = schema == B8_SCHEMA or "--b8" in argv
    tlib = load_templates()
    if tlib.error:
        R.fail(f"templates: the trap library is unreadable ({tlib.error}); rebuild it: python3 -I "
               f"{paths.TRAPS / 'traplib.py'} build")
    else:
        R.ok(f"templates: {tlib.source}")

    # map: every objective check in exactly one premise or coverage
    owner = {}
    for p in premises:
        for cid in p.get("checks", []):
            if cid not in checks:
                R.fail(f"{p['id']}: check {cid} does not exist")
            if cid in owner:
                R.fail(f"check {cid} belongs to two premises ({owner[cid]}, {p['id']}): one decision = one check")
            owner[cid] = p["id"]
        if p.get("family") not in FAMILIES:
            R.fail(f"{p['id']}: family {p.get('family')!r} is not in the catalogue")
        if not p.get("checks"):
            R.fail(f"{p['id']}: no checks")
        tpl = p.get("template")
        if p.get("decisive"):  # fillers may carry a free-text template label
            mode = tlib.resolve(tpl) if tpl else None
            if not tpl:
                (R.fail if b8 else R.warn)(f"{p['id']}: decisive premise declares no trap-library template")
            elif mode is None:
                R.fail(f"{p['id']}: template {tpl!r} is not in the {tlib.source}; see traplib.py list")
            elif mode["status"] == "dead" or dead_listed(mode):
                why = "" if mode["status"] == "dead" else f" (a D id: never decisive, whatever its computed status " \
                                                          f"{mode['status']})"
                R.fail(f"{p['id']}: template {tpl} ({mode['id']}: {mode['name']}) is dead in the trap library{why}; "
                       f"build the premise from a proven or promising mode")
            elif mode["status"] in PILOT_FIRST:
                R.warn(f"{p['id']}: template {tpl} ({mode['id']}) is {mode['status']}, unproven in this harness; "
                       f"pilot first before relying on it")
    for cid in objectives:
        if cid not in owner and cid not in coverage:
            R.fail(f"objective {cid} is neither a premise check nor a coverage check")
        if cid in owner and cid in coverage:
            R.fail(f"objective {cid} is both a premise check and a coverage check")
    if not R.fails:
        R.ok(f"map: {len(premises)} premises, {len(owner)} premise checks, {len(coverage)} coverage checks")

    # counts and families
    multi = len(steps) > 1
    fams_task = [p["family"] for p in premises]
    ts = sum(f == "timestamp_ordering" for f in fams_task)
    if ts > MAX_TIMESTAMP:
        R.fail(f"{ts} timestamp-ordering premises (max {MAX_TIMESTAMP} per task)")
    for step, ids in steps.items():
        ps = [p for p in premises if p.get("step", "01-task") == step]
        need = MIN_PREMISES_PER_STEP_MULTI if multi else MIN_PREMISES_SINGLE
        if len(ps) < need:
            R.fail(f"{step}: {len(ps)} premises (need >= {need})")
        fs = [p["family"] for p in ps]
        if len(set(fs)) != len(fs):
            R.fail(f"{step}: repeated family within the step {fs}")
    if multi and len(set(fams_task)) < MIN_FAMILIES_MULTI:
        R.fail(f"multi-step task uses {len(set(fams_task))} distinct families (need >= {MIN_FAMILIES_MULTI})")
    declared = sorted(set(meta.get("metadata", {}).get("trap_families", [])))
    if declared != sorted(set(fams_task)):
        R.fail(f"task.toml [metadata] trap_families {declared} != traps.json families {sorted(set(fams_task))}")

    # weights per step
    for step, ids in steps.items():
        objs = [cid for cid in ids if cid in objectives]
        total = sum(float(checks[c].get("weight", 0)) for c in objs) or 1.0
        trap_w = 0.0
        for p in premises:
            if p.get("step", "01-task") != step:
                continue
            w = sum(float(checks[c].get("weight", 0)) for c in p.get("checks", []) if c in checks)
            share = w / total
            trap_w += w
            if share > MAX_PREMISE_SHARE + 1e-9:
                R.fail(f"{step}: premise {p['id']} carries {share:.0%} of the step (max {MAX_PREMISE_SHARE:.0%})")
            if share < 0.08:
                R.warn(f"{step}: premise {p['id']} carries only {share:.0%}; a premise that bites should weigh 12-20%")
        free = 1 - trap_w / total
        if trap_w / total < MIN_TRAP_SHARE - 1e-9:
            R.fail(f"{step}: premises carry {trap_w / total:.0%} of the step (need >= {MIN_TRAP_SHARE:.0%})")
        if free > MAX_FREE_SHARE + 1e-9:
            R.fail(f"{step}: coverage (free) share {free:.0%} (max {MAX_FREE_SHARE:.0%})")
        else:
            R.ok(f"{step}: premises {trap_w / total:.0%}, coverage {free:.0%}")

    # quotes
    files = task / "environment/files"
    for p in premises:
        q = p.get("resolving_quote") or {}
        f, text = q.get("file"), q.get("text", "")
        if not f or not text:
            R.fail(f"{p['id']}: resolving_quote needs file and text")
            continue
        path = files / f
        if not path.is_file():
            R.fail(f"{p['id']}: resolving_quote file {f} not in environment/files")
        elif norm(text) not in norm(path.read_text(errors="replace")):
            R.fail(f"{p['id']}: resolving_quote text not found verbatim in {f}")
    v2 = schema.startswith("b6/premises/2") or schema == B8_SCHEMA  # B8 = the v2 premise rules + composition
    for key in ("misreading", "aimed_at") + (() if v2 else ("salience",)):
        for p in premises:
            if not p.get(key):
                R.fail(f"{p['id']}: missing {key}")
    if v2:
        v2_checks(task, steps, checks, premises, R)
    else:
        R.warn("traps.json schema is b6/premises/1: the B6v2 inferred/interlock rules (HARD-DOCTRINE-B6v2.md) are not checked")
    try:
        b8_checks(task, steps, checks, objectives, premises, tlib,
                  R if b8 else WarnOnly(R, f"B8 rule, a warning for schema {schema or 'unset'}"))
    except Exception as exc:  # noqa: BLE001 -- a rule that cannot run is never a pass
        (R.fail if b8 else R.warn)(f"B8: composition rules could not run: {exc}")

    # runtime patches (criteria-format tasks)
    if (task / "tests/criteria.py").is_file():
        copies_c = [task / "tests/_arena_runtime/contracts.py"] + sorted(task.glob("steps/*/solution/_arena_runtime/contracts.py"))
        copies_r = [task / "tests/_arena_runtime/checks_runtime.py"] + sorted(task.glob("steps/*/solution/_arena_runtime/checks_runtime.py"))
        for script, files_ in (("apply_central.py", copies_c), ("apply_runtime.py", copies_r), ("apply_stage3.py", copies_c + copies_r)):
            proc = subprocess.run([PY, "-I", "-B", str(FIX / script), "--check", *map(str, files_)], capture_output=True, text=True)
            if proc.returncode:
                R.fail(f"runtime: {script} --check: {proc.stdout.strip().splitlines()[-1] if proc.stdout.strip() else proc.stderr.strip()[-200:]}")
        for group in (copies_c, copies_r):
            if len({g.read_bytes() for g in group if g.is_file()}) > 1:
                R.fail(f"runtime copies differ: {[str(g.relative_to(task)) for g in group]}")

    # additivity (executed)
    if additivity and not R.fails:
        try:
            additivity_check(task, steps, checks, objectives, premises, R)
        except Exception as exc:  # noqa: BLE001 -- any failure here is a gate failure, reported
            R.fail(f"additivity: {exc}")

    # leaks
    try:
        leak_check(task, steps, traps, R)
    except Exception as exc:  # noqa: BLE001
        R.warn(f"leak check could not run: {exc}")
    try:
        ex = example_leaks(task, traps)
    except Exception as exc:  # noqa: BLE001
        ex = None
        (R.fail if b8 else R.warn)(f"leaks: instruction example scan could not run: {exc}")
    for h in ex or []:
        (R.fail if b8 else R.warn)(f"leaks: instruction example {h}: examples must carry no number, ID or fixture value")
    if ex == []:
        R.ok("leaks: no instruction example carries a number, an ID or a fixture value")
    return finish(R, argv)


def additivity_check(task, steps, checks, objectives, premises, R):
    work = Path(tempfile.mkdtemp(prefix="lint-add-"))
    order = list(steps)
    base = work / "base"
    base.mkdir()
    n_ok = 0
    for i, step in enumerate(order):
        ps = [p for p in premises if p.get("step", "01-task") == step]
        objs = [c for c in steps[step] if c in objectives]
        total = sum(float(checks[c].get("weight", 0)) for c in objs) or 1.0
        subsets = [()]
        for k in range(1, len(ps) + 1):
            subsets += list(itertools.combinations([p["id"] for p in ps], k))
        if len(subsets) > 64:
            subsets = [()] + [(p["id"],) for p in ps] + list(itertools.combinations([p["id"] for p in ps], 2))
        for sub in subsets:
            d = work / f"{step}-{'-'.join(sub) or 'ref'}"
            import shutil
            shutil.copytree(base, d)
            run_solve(task, step, d, ",".join(sub))
            g = grade(task, step, d)
            # a premise masked by another misread premise in the subset is unobservable there (traps.json masked_by)
            want_fail = {c for p in ps if p["id"] in sub and not set(p.get("masked_by") or []) & set(sub) for c in p["checks"]}
            got_fail = {c for c in g["failed"] if c in objectives}
            want_reward = round(1 - sum(float(checks[c].get("weight", 0)) for c in want_fail) / total, 4)
            if got_fail != want_fail or abs(g["reward"] - want_reward) > 1e-4:
                raise RuntimeError(f"{step} misread {sub or '(none)'}: failed {sorted(got_fail)} reward {g['reward']} "
                                   f"(want exactly {sorted(want_fail)} reward {want_reward})")
            n_ok += 1
        run_solve(task, step, base, "")          # reference deliverable carries into the next step
    R.ok(f"additivity: {n_ok} misreading subsets each failed exactly their premises' checks with the exact partial reward")


def scalars(v, out):
    if isinstance(v, dict):
        for x in v.values():
            scalars(x, out)
    elif isinstance(v, list):
        for x in v:
            scalars(x, out)
    elif isinstance(v, bool) or v is None:
        return
    else:
        out.add(str(v))


def leak_check(task, steps, traps, R):
    work = Path(tempfile.mkdtemp(prefix="lint-leak-"))
    for step in steps:
        run_solve(task, step, work, "")
    values = set()
    for f in work.rglob("*.json"):
        scalars(json.loads(f.read_text()), values)
    enums = set()
    outputs = task / "tests/outputs.json"
    if outputs.is_file():
        def walk(s):
            if isinstance(s, dict):
                for e in s.get("enum", []) or []:
                    enums.add(str(e))
                for x in s.values():
                    walk(x)
            elif isinstance(s, list):
                for x in s:
                    walk(x)
        walk(json.loads(outputs.read_text()))
    allow = {str(a.get("value")) for a in traps.get("leak_allow", []) if a.get("reason")}
    ins = "\n".join(p.read_text() for p in sorted(task.glob("steps/*/instruction.md")))
    hits = []
    for v in sorted(values):
        if v in enums or v in allow or len(v) < 3:
            continue
        if re.fullmatch(r"-?\d+(\.\d+)?", v) and len(v.replace(".", "").replace("-", "")) < 2:
            continue
        pat = r"(?<![\w.])" + re.escape(v) + r"(?![\w])"
        if re.search(pat, ins):
            hits.append(v)
    if hits:
        R.fail(f"leaks: reference-answer values appear in the instruction (justify in leak_allow or remove): {hits[:12]}")
    else:
        R.ok(f"leaks: none of {len(values)} reference values appear in the instructions (enum options and justified values excepted)")


def finish(R, argv) -> int:
    for m in R.oks:
        print("ok   ", m)
    for m in R.warns:
        print("WARN ", m)
    for m in R.fails:
        print("FAIL ", m)
    print("DESIGN GATE:", "PASS" if not R.fails else f"FAIL ({len(R.fails)})")
    if "--json" in argv:
        Path(argv[argv.index("--json") + 1]).write_text(json.dumps({"fails": R.fails, "warns": R.warns, "oks": R.oks}, indent=1))
    return 1 if R.fails else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
