"""Internal trap evidence: per-premise miss rates from calibration campaigns, pooled per library mode.

    python3 -I build_evidence.py [--root <W>] [--out <dir>] [--modes-out <file>] [--date YYYYMMDD]

Read-only over --root (the live workspace). Pure stdlib. What it does:

1. Indexes every task tree under <root>/envs-* by (task name, version) from task.toml.
2. Enumerates every campaign folder under <root>/pipeline-artifacts/b4
   (<name>-<version>[-<stage>]-<model>[-rerun<ts>]) and reads its report.json.
   - Voids never count: a trial with valid=false is dropped (as signal_gate.py does); a whole run the ledger
     marks void-auth, or lists in a void_history (credential failure; measure.py), is dropped; a run the ledger
     does not know is scanned for the same credential-failure pattern measure.py uses.
   - Unfinished, missing or unreadable reports are skipped and counted, never silently dropped.
3. Joins each campaign to the premise map (authoring/traps.json, schema b6/premises/*) of the tree with the same
   name and version (ledger digest breaks ties between trees whose maps differ). Legacy traps[] maps are skipped
   and counted: their checks are shared between traps and cannot be attributed.
4. Per valid trial and premise (signal_gate.py semantics): MISSED if any of the premise's checks, in the premise's
   step, was evaluated below 1.0. A premise none of whose checks failed but one of which was gated out, skipped
   or absent is NOT counted (gated_out is not failed; it is not a pass either).
5. Assigns every premise a library mode id (mode-map.json): the premise's own `template` (T*/L*), else an explicit
   override, else the hand-reviewed mechanism label of the 45-task pass (INTERNAL-trap-evidence.csv), carried
   forward to later versions of the same task/premise/family/mechanism, else a mechanism-code fallback.
   Stated premises go to D1 whatever their label.
6. Joins audit verdicts (audit-verdicts.json; every record carries a quote that must occur in its cited source
   under --root, so a citation that drifted is reported).
7. Computes every status from the data (SCHEMA.md "Status rules"); nothing is typed.

Writes <out>/INTERNAL-evidence-<date>.csv (one row per task, version, premise, stage),
<out>/INTERNAL-evidence-<date>-pooled.json (per mode and per declared template, with skips and status reasons),
and, when modes-curated.json is present, the traplib/1 file --modes-out (default: modes-internal.json here).
"""
from __future__ import annotations

import argparse
import csv
import datetime as dt
import hashlib
import json
import os
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
# the checkout this file lives in (production/traps -> repo root), or $ARENA_ROOT for a workspace kept elsewhere
DEFAULT_ROOT = Path(os.environ.get("ARENA_ROOT") or HERE.parent.parent)
MODELS = ("fable", "astra")
CONTROLS = ("oracle", "nop")
CAMPAIGN_RE = re.compile(r"^(?P<name>.+?)-(?P<version>\d+\.\d+\.\d+)(?:-(?P<stage>pilot|final))?"
                         r"-(?P<model>fable|astra|oracle|nop)(?:-rerun(?P<rerun>\d+))?$")
AUTH_FAIL = re.compile(r"token_invalidated|api key has been invalidated|invalid_api_key|invalid api key|incorrect api key|"
                       r"authentication_error|authentication_failed|401 unauthorized", re.I)
GENUINE = {"GENUINE", "GENUINE-soft"}
EXCLUDED_VERDICTS = {"AMBIGUOUS", "DEFECT"}
SKIP_DIRS = {"steps", "environment", "tests", "solution", "authoring", "provenance", "verification", "calibration",
             "__pycache__", "node_modules", ".git"}

# SCHEMA.md "Status rules" (production/traps/SCHEMA.md) -- the only place these numbers live in this script.
PROVEN_MIN_GENUINE_TASKS = 2
PROVEN_MIN_RATE = 0.20
PROVEN_MIN_N = 20
DEAD_MAX_RATE = 0.05
DEAD_MIN_N = 20
BIMODAL_LOW, BIMODAL_HIGH = 0.10, 0.90
BIMODAL_MIN_TASK_N = 10          # a per-task rate enters the bimodal test only from a 10-run final
PRESUMED_AMBIGUOUS_RATE = 0.90   # an unaudited unit at or above this is presumed ambiguous (TRAP-CATALOG-B7 fact 7)
AIM_RATE = 0.20


# ----------------------------------------------------------------------------------------------- small helpers
def load_json(path: Path):
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def toml_task(path: Path) -> tuple[str | None, str | None]:
    """name and version from task.toml's [task] table (tomllib, with a regex fallback for broken files)."""
    text = path.read_text(encoding="utf-8", errors="replace")
    try:
        import tomllib
        meta = tomllib.loads(text).get("task", {})
        name, version = meta.get("name"), meta.get("version")
    except Exception:  # noqa: BLE001 -- a malformed toml is read by regex and reported if that fails too
        m_name = re.search(r'^name\s*=\s*"([^"]+)"', text, re.M)
        m_ver = re.search(r'^version\s*=\s*"([^"]+)"', text, re.M)
        name, version = (m_name.group(1) if m_name else None), (m_ver.group(1) if m_ver else None)
    if name:
        name = str(name).split("/")[-1]
    return name, (str(version) if version else None)


def tree_digest(task: Path) -> str:
    """measure.py's tree digest (identity of the exact version a campaign measured)."""
    h = hashlib.sha256()
    for p in sorted(task.rglob("*")):
        rel = p.relative_to(task).as_posix()
        if p.is_file() and "__pycache__" not in rel and not rel.startswith(("verification/", "authoring/work")):
            h.update(rel.encode() + b"\0" + p.read_bytes() + b"\0")
    return h.hexdigest()


def rate(k: int, n: int) -> float | None:
    return (k / n) if n else None


def fmt(k: int, n: int) -> str:
    return f"{k}/{n}" if n else "-"


class Skips:
    """Every record that is not counted lands here with a reason; the report prints the tally."""

    def __init__(self):
        self.items: list[dict] = []

    def add(self, kind: str, what: str, reason: str, **extra):
        self.items.append({"kind": kind, "what": what, "reason": reason, **extra})

    def tally(self) -> dict:
        def grp(s):
            m = s.get("model")
            return "" if not m else (" [model runs]" if m in MODELS else " [oracle/nop controls]")
        c = Counter((s["kind"], s["reason"] + grp(s)) for s in self.items)
        return {f"{k}: {r}": n for (k, r), n in sorted(c.items())}


# ----------------------------------------------------------------------------------------------- task trees
class TreeIndex:
    def __init__(self, root: Path, skips: Skips):
        self.root = root
        self.by_key: dict[tuple[str, str], list[Path]] = defaultdict(list)
        self.skips = skips
        self._digest: dict[Path, str] = {}
        for base in sorted(root.glob("envs-*")):
            if not base.is_dir():
                continue
            for dirpath, dirnames, filenames in os.walk(base):
                depth = len(Path(dirpath).relative_to(base).parts)
                dirnames[:] = sorted(d for d in dirnames if d not in SKIP_DIRS and not d.endswith(".incoming")
                                     and depth < 4)
                if "task.toml" in filenames:
                    tdir = Path(dirpath)
                    try:
                        name, version = toml_task(tdir / "task.toml")
                    except OSError as exc:
                        skips.add("tree", str(tdir.relative_to(root)), f"unreadable task.toml ({exc.__class__.__name__})")
                        continue
                    if not name or not version:
                        skips.add("tree", str(tdir.relative_to(root)), "task.toml without [task] name/version")
                        continue
                    self.by_key[(name, version)].append(tdir)
                    dirnames[:] = []  # a task tree does not nest another task tree

    def digest(self, tdir: Path) -> str:
        if tdir not in self._digest:
            self._digest[tdir] = tree_digest(tdir)
        return self._digest[tdir]


def premise_map(tdir: Path) -> tuple[str, list[dict] | None, str]:
    """(status, premises, schema) for a tree: status ok | missing | legacy | unreadable | empty."""
    tp = tdir / "authoring/traps.json"
    if not tp.is_file():
        return "missing", None, ""
    try:
        data = load_json(tp)
    except (OSError, ValueError):
        return "unreadable", None, ""
    if not isinstance(data, dict):
        return "unreadable", None, ""
    if isinstance(data.get("premises"), list):
        prem = [p for p in data["premises"] if isinstance(p, dict) and p.get("id") and isinstance(p.get("checks"), list)]
        bad = len(data["premises"]) - len(prem)
        if bad:  # reported by the caller through the schema string; never dropped silently
            return ("ok" if prem else "empty"), prem, f"{data.get('schema', '')}|malformed:{bad}"
        return ("ok" if prem else "empty"), prem, str(data.get("schema", ""))
    if isinstance(data.get("traps"), list):
        return "legacy", None, str(data.get("schema", ""))
    return "unreadable", None, ""


def map_signature(premises: list[dict]) -> str:
    return json.dumps(sorted((p["id"], p.get("step", "01-task"), sorted(p["checks"]), p.get("template") or "",
                              p.get("family") or "", p.get("mechanism") or "") for p in premises))


# ----------------------------------------------------------------------------------------------- ledger + runs
def load_ledger(root: Path, skips: Skips) -> dict[str, dict]:
    """campaign folder basename -> {entry, model, state, digest, stage}."""
    # $ARENA_LEDGER, else the production line's state dir (tools/paths.py), else the older research/batch4 layout
    cands = [Path(os.environ["ARENA_LEDGER"])] if os.environ.get("ARENA_LEDGER") else []
    cands += [root / "production/state/ledger.json", root / "research/batch4/ledger.json"]
    path = next((c for c in cands if c.is_file()), cands[0])
    out: dict[str, dict] = {}
    if not path.is_file():
        skips.add("ledger", str(path), "ledger.json missing: void-auth runs detected by log scan only")
        return out
    try:
        entries = load_json(path).get("entries", [])
    except (OSError, ValueError) as exc:
        skips.add("ledger", str(path), f"ledger.json unreadable ({exc.__class__.__name__})")
        return out
    for e in entries:
        base = {"entry": e.get("id"), "digest": e.get("digest"), "stage": e.get("stage", "final"),
                "task": e.get("task"), "version": e.get("version")}
        for model, run in (e.get("runs") or {}).items():
            out_dir = os.path.basename(str(run.get("out", "")).rstrip("/"))
            if out_dir:
                out[out_dir] = {**base, "model": model, "state": run.get("state")}
        for vh in e.get("void_history") or []:
            for model, run in (vh or {}).items():
                out_dir = os.path.basename(str(run.get("out", "")).rstrip("/"))
                if out_dir and out_dir not in out:
                    out[out_dir] = {**base, "model": model, "state": "void-history"}
                elif out_dir and out[out_dir]["state"] == "done":
                    # the same folder was re-used by a rerun; the ledger's current record wins
                    pass
    return out


def auth_scan(run_dir: Path, limit_bytes: int = 200_000_000) -> bool:
    """measure.py's credential-failure scan over the run's job logs (only used for runs the ledger does not know)."""
    jobs = run_dir / "jobs"
    if not jobs.is_dir():
        return False
    seen = 0
    for dirpath, _dirs, files in os.walk(jobs):
        for f in files:
            p = Path(dirpath) / f
            try:
                size = p.stat().st_size
            except OSError:
                continue
            seen += size
            if seen > limit_bytes:
                return False
            try:
                with open(p, "rb") as fh:
                    if AUTH_FAIL.search(fh.read().decode("utf-8", "replace")):
                        return True
            except OSError:
                continue
    return False


def check_outcome(entry) -> str:
    """fail | pass | gated (gated out, skipped, error or no value: not attempted)."""
    if not isinstance(entry, dict):
        return "gated" if entry is None else ("fail" if float(entry) < 1.0 else "pass")
    if entry.get("gated_out") or entry.get("skipped") or entry.get("error"):
        return "gated"
    if entry.get("status") not in (None, "evaluated"):
        return "gated"
    v = entry.get("value")
    if v is None:
        return "gated"
    try:
        return "fail" if float(v) < 1.0 else "pass"
    except (TypeError, ValueError):
        return "gated"


def read_trials(report_path: Path) -> tuple[list[dict], int, str | None]:
    """valid trials as {id, steps: {name: {check: outcome}}}, number of void trials, error."""
    try:
        rep = load_json(report_path)
    except (OSError, ValueError) as exc:
        return [], 0, f"report.json unreadable ({exc.__class__.__name__})"
    if not isinstance(rep, dict):
        return [], 0, "report.json is not an object"
    if rep.get("status") not in (None, "finished"):
        return [], 0, f"report status {rep.get('status')!r}"
    trials, voids = [], 0
    for t in rep.get("trials") or []:
        if not isinstance(t, dict) or not t.get("valid"):
            voids += 1
            continue
        steps = {}
        for s in t.get("steps") or []:
            checks = {}
            for k, v in (s.get("checks") or {}).items():
                checks[k.split("/", 1)[-1]] = check_outcome(v)
            steps[s.get("name", "01-task")] = checks
        trials.append({"id": t.get("id"), "steps": steps})
    return trials, voids, None


def score_premise(trial: dict, premise: dict) -> str:
    """missed | passed | gated | nostep."""
    step = premise.get("step", "01-task")
    checks = trial["steps"].get(step)
    if checks is None:
        if len(trial["steps"]) == 1 and step == "01-task":
            checks = next(iter(trial["steps"].values()))
        else:
            return "nostep"
    outs = [checks.get(c, "gated") for c in premise["checks"]]
    if "fail" in outs:
        return "missed"
    if "gated" in outs:
        return "gated"
    return "passed"


# ----------------------------------------------------------------------------------------------- labels + verdicts
def load_labels(path: Path | None, skips: Skips) -> dict[tuple[str, str, str], dict]:
    """(task, version, premise) -> {label, stated, family, mech_code} from the 45-task pass CSV."""
    out: dict[tuple[str, str, str], dict] = {}
    if not path or not path.is_file():
        skips.add("labels", str(path), "label CSV missing: modes come from templates, overrides and code fallbacks only")
        return out
    with open(path, encoding="utf-8", newline="") as fh:
        for r in csv.DictReader(fh):
            key = (r.get("task", ""), r.get("version", ""), r.get("premise", ""))
            if key in out:
                continue
            out[key] = {"label": r.get("mechanism", ""), "stated": str(r.get("stated_inferred", "")).startswith("st"),
                        "family": r.get("family", ""), "mech_code": r.get("mech_code", ""),
                        "verdict": r.get("verdict", ""), "verdict_note": r.get("verdict_note", "")}
    return out


def vkey(v: str) -> tuple:
    try:
        return tuple(int(x) for x in v.split("."))
    except ValueError:
        return (0,)


def in_range(version: str, spec: str | None) -> bool:
    """spec: '' / None (any), '2.3.0', '>=2.3.0', '<=2.3.0', '2.0.0..2.4.0' (inclusive)."""
    if not spec:
        return True
    if ".." in spec:
        lo, hi = spec.split("..", 1)
        return vkey(lo) <= vkey(version) <= vkey(hi)
    if spec.startswith(">="):
        return vkey(version) >= vkey(spec[2:])
    if spec.startswith("<="):
        return vkey(version) <= vkey(spec[2:])
    return version == spec


VERDICTS = {"GENUINE", "GENUINE-soft", "BLIND-1.0", "UNCONFIRMED", "AMBIGUOUS", "DEFECT"}


def load_verdicts(path: Path | None, root: Path, labels: dict, skips: Skips) -> tuple[dict, list[dict]]:
    """Verdict records. Base: the 45-task pass CSV (exact task/version/premise, transcribed from genuineness.md).
    On top: audit-verdicts.json records {task, versions (range spec), premises, verdict, source 'file[:line]',
    quote, note}; a later record overrides an earlier one, and any file record overrides the CSV."""
    exact: dict[tuple[str, str, str], dict] = {}
    ranged: dict[tuple[str, str], list] = defaultdict(list)
    checks: list[dict] = []
    for (task, version, prem), lab in labels.items():
        if lab.get("verdict"):
            exact[(task, version, prem)] = {"verdict": lab["verdict"], "note": lab.get("verdict_note", ""),
                                            "source": "research/INTERNAL-trap-evidence.csv (45-task pass, from genuineness.md)"}
    if not path or not path.is_file():
        skips.add("verdicts", str(path), "audit-verdicts.json missing: only the 45-task pass verdicts are joined")
        return {"exact": exact, "ranged": ranged}, checks
    cache: dict[str, str] = {}
    for rec in load_json(path).get("verdicts", []):
        if rec.get("verdict") not in VERDICTS:
            skips.add("verdict", f"{rec.get('task')} {rec.get('versions')}", f"unknown verdict {rec.get('verdict')!r}")
            continue
        src, quote = rec.get("source", ""), rec.get("quote", "")
        src_file = src.split(":", 1)[0]
        ok = None
        p = root / src_file if src_file else None
        if p is not None and p.is_file():
            if src_file not in cache:
                cache[src_file] = re.sub(r"\s+", " ", p.read_text(encoding="utf-8", errors="replace"))
            ok = bool(quote) and re.sub(r"\s+", " ", quote) in cache[src_file]
        checks.append({"task": rec["task"], "versions": rec.get("versions"), "premises": rec.get("premises"),
                       "verdict": rec["verdict"], "source": src, "quote_found": ok})
        if ok is False:
            skips.add("verdict", f"{rec['task']} {rec.get('versions')} {rec.get('premises')}",
                      "cited quote not found in source (record kept, flagged)")
        elif ok is None:
            skips.add("verdict", f"{rec['task']} {rec.get('versions')} {rec.get('premises')}",
                      "cited source not found under root (record kept, unverified)")
        info = {"verdict": rec["verdict"], "note": rec.get("note", ""), "source": src, "quote_found": ok}
        for prem in rec.get("premises", []):
            ranged[(rec["task"], prem)].append((rec.get("versions"), info))
    return {"exact": exact, "ranged": ranged}, checks


def verdict_for(verdicts: dict, task: str, version: str, prem: str) -> dict | None:
    hit = None
    for spec, rec in verdicts["ranged"].get((task, prem), []):  # later records override earlier ones
        if in_range(version, spec):
            hit = rec
    return hit if hit is not None else verdicts["exact"].get((task, version, prem))


# ----------------------------------------------------------------------------------------------- mode assignment
TEMPLATE_RE = re.compile(r"^\s*([TLRD]\d+)\b")


class ModeMap:
    def __init__(self, path: Path | None, skips: Skips):
        self.data = load_json(path) if path and path.is_file() else {}
        if not self.data:
            skips.add("mode-map", str(path), "mode-map.json missing: only premise templates assign modes")
        self.label_to_mode = self.data.get("label_to_mode", {})
        self.code_fallback = self.data.get("code_fallback", {})
        self.overrides = self.data.get("overrides", [])
        self.lab_to_mode = self.data.get("lab_to_mode", {})

    def override(self, task: str, version: str, prem: str, premise: dict) -> dict | None:
        hit = None
        for o in self.overrides:
            if o.get("task") != task or prem not in o.get("premises", []):
                continue
            if not in_range(version, o.get("versions")):
                continue
            if o.get("checks_any") and not set(o["checks_any"]) & set(premise.get("checks", [])):
                continue
            hit = o
        return hit

    def assign(self, task, version, prem, premise, label_rec, carried) -> tuple[str, str]:
        """(mode id, source of the assignment)."""
        o = self.override(task, version, prem, premise)
        if o:
            return o["mode"], "override: " + o.get("why", "")
        stated = premise.get("mechanism") == "STATED" or (label_rec or {}).get("stated")
        tpl = premise.get("template")
        m = TEMPLATE_RE.match(str(tpl)) if tpl else None
        filler = bool(tpl) and str(tpl).lower().startswith("filler")
        if m and not filler and not stated:
            return m.group(1), "template"
        if stated:
            # a stated variant of a working mechanism is a stated rule (D1); a stated premise whose mechanism is
            # itself on the dead list stays with that mechanism, so the dead list keeps its own evidence
            lab = (label_rec or carried or {}).get("label", "")
            lab_mode = self.label_to_mode.get(lab, "")
            if lab_mode.startswith("D"):
                return lab_mode, f"stated premise; label {lab} is a dead mechanism"
            return self.code_fallback.get("STATED", "D1"), "stated premise (mechanism STATED or B6v1 stated)"
        if label_rec and label_rec.get("label") in self.label_to_mode:
            return self.label_to_mode[label_rec["label"]], f"label {label_rec['label']} (45-task pass)"
        if carried and carried.get("label") in self.label_to_mode:
            return self.label_to_mode[carried["label"]], f"label {carried['label']} carried from {carried['from']}"
        if m:  # filler with a template id ("filler (was T2)" is not matched: it starts with 'filler')
            return m.group(1), "template (filler)"
        code = premise.get("mechanism") or ""
        fam = premise.get("family") or ""
        for key in (f"{code}|{fam}", code, f"|{fam}"):
            if key in self.code_fallback:
                return self.code_fallback[key], f"code fallback {key}"
        return "UNMAPPED", "no template, override, label or code fallback"


# ----------------------------------------------------------------------------------------------- the build
def build(root: Path, labels_path: Path | None, map_path: Path | None, verdicts_path: Path | None) -> dict:
    skips = Skips()
    index = TreeIndex(root, skips)
    ledger = load_ledger(root, skips)
    labels = load_labels(labels_path, skips)
    verdicts, verdict_checks = load_verdicts(verdicts_path, root, labels, skips)
    modes = ModeMap(map_path, skips)

    art = root / "pipeline-artifacts/b4"
    units: dict[tuple, dict] = {}        # (task, version, premise, stage) -> unit
    oracle_bad: dict[tuple, set] = defaultdict(set)
    runs_counted = Counter()
    trials_counted = Counter()
    void_trials = Counter()
    chosen_tree: dict[tuple[str, str, str], tuple] = {}
    campaigns_seen = 0
    if not art.is_dir():
        skips.add("campaigns", str(art), "no campaign folder")
    for d in sorted(art.iterdir()) if art.is_dir() else []:
        if not d.is_dir():
            continue
        campaigns_seen += 1
        m = CAMPAIGN_RE.match(d.name)
        if d.name.startswith("_") or not m:
            skips.add("campaign", d.name, "probe or unparseable folder name")
            continue
        name, version, model = m.group("name"), m.group("version"), m.group("model")
        led = ledger.get(d.name)
        stage = m.group("stage") or (led or {}).get("stage") or "final"
        if led and led.get("state") in ("void-auth", "void-history"):
            skips.add("run", d.name, "void run (credential failure; ledger)", model=model)
            continue
        if led and led.get("state") not in ("done",):
            skips.add("run", d.name, f"not finished (ledger state {led.get('state')})", model=model)
            continue
        rp = d / "report.json"
        if not rp.is_file():
            skips.add("run", d.name, "no report.json", model=model)
            continue
        trials, voids, err = read_trials(rp)
        if err:
            skips.add("run", d.name, err, model=model)
            continue
        if not led and model in MODELS and auth_scan(d):
            skips.add("run", d.name, "void run (credential failure; log scan, not in ledger)", model=model)
            continue
        cands = index.by_key.get((name, version), [])
        maps = []
        for c in cands:
            st, prem, schema = premise_map(c)
            maps.append((c, st, prem, schema))
        ok = [x for x in maps if x[1] == "ok"]
        if not cands:
            skips.add("run", d.name, "no task tree with this name and version", model=model)
            continue
        if not ok:
            reasons = sorted({x[1] for x in maps})
            why = "legacy traps[] map (not attributable to premises)" if "legacy" in reasons else f"no premise map ({'/'.join(reasons)})"
            skips.add("run", d.name, why, model=model, trials=len(trials))
            continue
        sigs = {map_signature(x[2]) for x in ok}
        pick = ok[0]
        tie = "single"
        if len(sigs) > 1:
            want = (led or {}).get("digest")
            match = [x for x in ok if want and index.digest(x[0]) == want]
            if match:
                pick, tie = match[0], "digest"
            else:
                # prefer a frozen copy (_versions) of the version; report the ambiguity
                frozen = [x for x in ok if "_versions" in x[0].parts]
                pick, tie = (frozen or ok)[0], "ambiguous"
                skips.add("map", d.name, "premise maps differ between trees and no digest match; frozen copy used",
                          model=model)
        tdir, _, premises, schema = pick
        if "|malformed:" in schema:
            schema, bad = schema.split("|malformed:")
            skips.add("premise", f"{d.name}", f"{bad} premise(s) without id or checks list in traps.json (not counted)",
                      model=model)
        chosen_tree[(name, version, d.name)] = (str(tdir.relative_to(root)), tie)
        void_trials[(name, version, stage, model)] += voids
        if model in CONTROLS:
            if model == "oracle":
                for t in trials:
                    for p in premises:
                        if score_premise(t, p) == "missed":
                            oracle_bad[(name, version)].add(p["id"])
            continue
        runs_counted[model] += 1
        trials_counted[model] += len(trials)
        for p in premises:
            key = (name, version, p["id"], stage)
            u = units.get(key)
            if u is None:
                u = units[key] = {"task": name, "version": version, "premise": p["id"], "stage": stage,
                                  "premise_obj": p, "tree": str(tdir.relative_to(root)), "schema": schema,
                                  "campaigns": [], **{f"{mm}_{k}": 0 for mm in MODELS for k in
                                                       ("runs", "misses", "gated", "nostep", "void_trials")}}
            u["campaigns"].append(d.name)
            u[f"{model}_void_trials"] += voids
            for t in trials:
                o = score_premise(t, p)
                if o == "missed":
                    u[f"{model}_misses"] += 1
                    u[f"{model}_runs"] += 1
                elif o == "passed":
                    u[f"{model}_runs"] += 1
                elif o == "gated":
                    u[f"{model}_gated"] += 1
                else:
                    u[f"{model}_nostep"] += 1

    # labels carried forward: same task, premise id, family and mechanism code as a labelled version
    labelled = defaultdict(list)
    for (task, version, prem), lab in labels.items():
        labelled[(task, prem)].append((version, lab))
    tree_premise = {}
    for (task, version, prem, _stage), u in units.items():
        tree_premise[(task, version, prem)] = u["premise_obj"]
    for u in units.values():
        task, version, prem, p = u["task"], u["version"], u["premise"], u["premise_obj"]
        lab = labels.get((task, version, prem))
        carried = None
        if not lab:
            best = None
            for v, lr in labelled.get((task, prem), []):
                po = tree_premise.get((task, v, prem))
                same = po is not None and po.get("family") == p.get("family") and po.get("mechanism") == p.get("mechanism")
                if same and vkey(v) < vkey(version) and (best is None or vkey(v) > vkey(best[0])):
                    best = (v, lr)
            if best:
                carried = {**best[1], "from": best[0]}
        mode, src = modes.assign(task, version, prem, p, lab, carried)
        u["label"] = (lab or {}).get("label") or (carried or {}).get("label", "")
        u["stated"] = bool(p.get("mechanism") == "STATED" or (lab or {}).get("stated"))
        u["mode"], u["mode_source"] = mode, src
        vd = verdict_for(verdicts, task, version, prem)
        u["verdict"] = (vd or {}).get("verdict", "")
        u["verdict_source"] = (vd or {}).get("source", "")
        u["verdict_note"] = (vd or {}).get("note", "")
        u["oracle_missed"] = prem in oracle_bad.get((task, version), set())

    # lever lab (pipeline/author/lever_evidence.json): task-level single-lever labs, 5 episodes per model
    lab_units = []
    lev = root / "pipeline/author/lever_evidence.json"
    if lev.is_file():
        try:
            labs = load_json(lev).get("labs", {})
        except (OSError, ValueError):
            labs = {}
            skips.add("lab", str(lev), "lever_evidence.json unreadable")
        for lab_id, rec in sorted(labs.items()):
            mm = modes.lab_to_mode.get(lab_id)
            if not mm:
                skips.add("lab", lab_id, "lab not mapped to a mode: " +
                          modes.data.get("lab_unmapped_reason", {}).get(lab_id, "no reason recorded"))
                continue
            pm = rec.get("per_model", {})
            f = pm.get("anthropic/claude-fable-5-1", {})
            a = pm.get("openai/gpt-6-astra", {})
            u = {"task": f"lab-{lab_id}", "version": "lab", "premise": "lever", "stage": "pilot", "tree":
                 "pipeline/author/lever_evidence.json", "schema": "arena/lever-evidence/1", "campaigns": [],
                 "fable_runs": int(f.get("valid", 0)), "fable_misses": int(f.get("valid", 0)) - int(f.get("passes", 0)),
                 "astra_runs": int(a.get("valid", 0)), "astra_misses": int(a.get("valid", 0)) - int(a.get("passes", 0)),
                 "fable_gated": 0, "astra_gated": 0, "fable_nostep": 0, "astra_nostep": 0,
                 "fable_void_trials": 0, "astra_void_trials": 0,
                 "premise_obj": {"family": "", "mechanism": "", "aimed_at": "", "misreading":
                                 f"lab {lab_id} ({', '.join(rec.get('levers', []))}): {rec.get('mechanism', '')}"},
                 "label": "lab", "stated": False, "mode": mm, "mode_source": "lab_to_mode (task-level lab; a pass = the lever did not bite)",
                 "verdict": "", "verdict_source": "", "verdict_note": "", "oracle_missed": False}
            vd = verdict_for(verdicts, f"lab-{lab_id}", "lab", "lever")
            if vd:
                u["verdict"], u["verdict_source"], u["verdict_note"] = vd["verdict"], vd.get("source", ""), vd.get("note", "")
            lab_units.append(u)
    else:
        skips.add("lab", str(lev), "lever_evidence.json missing")

    # ledger runs with no local folder (in flight on a pool, or never pulled): reported, never counted
    local = {d.name for d in art.iterdir()} if art.is_dir() else set()
    for out_dir, rec in sorted(ledger.items()):
        if out_dir not in local and rec.get("model") in MODELS:
            skips.add("run", out_dir, f"in the ledger (state {rec.get('state')}) but no local folder", model=rec["model"])

    all_units = list(units.values()) + lab_units
    for u in all_units:
        u["presumed_ambiguous"] = (u["verdict"] not in GENUINE) and any(
            u[f"{mm}_runs"] >= 5 and u[f"{mm}_misses"] / u[f"{mm}_runs"] >= PRESUMED_AMBIGUOUS_RATE for mm in MODELS)
    return {"units": all_units, "skips": skips, "runs_counted": dict(runs_counted), "trials_counted": dict(trials_counted),
            "campaigns_seen": campaigns_seen, "verdict_checks": verdict_checks, "chosen_tree": chosen_tree,
            "index_size": len(index.by_key)}


# ----------------------------------------------------------------------------------------------- pooling + status
def pool(units, stage=None, clean=True, drop_presumed=False):
    out = {mm: [0, 0] for mm in MODELS}
    for u in units:
        if stage and u["stage"] != stage:
            continue
        if clean and u["verdict"] in EXCLUDED_VERDICTS:
            continue
        if drop_presumed and u["presumed_ambiguous"]:
            continue
        for mm in MODELS:
            out[mm][0] += u[f"{mm}_misses"]
            out[mm][1] += u[f"{mm}_runs"]
    return out


def per_task_final(units):
    """task -> model -> [k, n] over clean final rows."""
    out: dict[str, dict[str, list[int]]] = defaultdict(lambda: {mm: [0, 0] for mm in MODELS})
    for u in units:
        if u["stage"] != "final" or u["verdict"] in EXCLUDED_VERDICTS:
            continue
        for mm in MODELS:
            out[u["task"]][mm][0] += u[f"{mm}_misses"]
            out[u["task"]][mm][1] += u[f"{mm}_runs"]
    return out


def compute_status(units) -> dict:
    final = pool(units, stage="final")
    final_strict = pool(units, stage="final", drop_presumed=True)
    allst = pool(units)
    # a task counts as audited GENUINE for this mode only where an audited-genuine FINAL unit actually bit (k > 0);
    # traplib.py's own check counts GENUINE final rows, so this is never looser than it
    genuine_tasks = sorted({u["task"] for u in units if u["verdict"] in GENUINE and u["stage"] == "final"
                            and any(u[f"{mm}_misses"] for mm in MODELS)})
    per_task = per_task_final(units)
    reasons = []
    # bimodal: every (task, model) final rate with n >= 10 at an end, and some model spans both ends
    ends = {mm: [] for mm in MODELS}
    inband = []
    for task, by in per_task.items():
        for mm in MODELS:
            k, n = by[mm]
            if n >= BIMODAL_MIN_TASK_N:
                r = k / n
                if r <= BIMODAL_LOW or r >= BIMODAL_HIGH:
                    ends[mm].append((task, r))
                else:
                    inband.append((task, mm, r))
    spans = [mm for mm in MODELS if any(r <= BIMODAL_LOW for _, r in ends[mm]) and any(r >= BIMODAL_HIGH for _, r in ends[mm])]
    bimodal = bool(spans) and not inband
    proven_models = [mm for mm in MODELS if final_strict[mm][1] >= PROVEN_MIN_N
                     and final_strict[mm][0] / final_strict[mm][1] >= PROVEN_MIN_RATE]
    proven = len(genuine_tasks) >= PROVEN_MIN_GENUINE_TASKS and bool(proven_models)
    dead = all(allst[mm][1] >= DEAD_MIN_N and allst[mm][0] / allst[mm][1] <= DEAD_MAX_RATE for mm in MODELS)
    measured = any(allst[mm][1] for mm in MODELS)
    if bimodal:
        status = "bimodal"
        reasons.append(f"every per-task final rate (n>={BIMODAL_MIN_TASK_N}) is <= {BIMODAL_LOW} or >= {BIMODAL_HIGH}, "
                       f"spanning both ends on {', '.join(spans)}")
    elif proven:
        status = "proven"
        reasons.append(f"audited GENUINE in {len(genuine_tasks)} tasks; pooled final miss rate >= {PROVEN_MIN_RATE} "
                       f"with n >= {PROVEN_MIN_N} on {', '.join(proven_models)} (unaudited >= 90% units excluded)")
    elif dead:
        status = "dead"
        reasons.append(f"pooled miss rate (all stages, AMBIGUOUS/DEFECT excluded) <= {DEAD_MAX_RATE} on both models, n >= {DEAD_MIN_N} each")
    elif measured:
        status = "promising"
        why = []
        if len(genuine_tasks) < PROVEN_MIN_GENUINE_TASKS:
            why.append(f"audited GENUINE in {len(genuine_tasks)} task(s) (< {PROVEN_MIN_GENUINE_TASKS})")
        if not proven_models:
            why.append(f"no model with pooled final rate >= {PROVEN_MIN_RATE} at n >= {PROVEN_MIN_N}")
        if not dead:
            why.append("not dead (some model above 0.05 or n < 20)")
        reasons.append("short of proven: " + "; ".join(why))
    else:
        status = "unmeasured"
        reasons.append("no valid run in this harness")
    return {"status": status, "reasons": reasons, "final": final, "final_strict": final_strict, "all": allst,
            "genuine_tasks": genuine_tasks, "per_task_final": {t: by for t, by in sorted(per_task.items())},
            "bimodal_spans": spans, "inband_task_rates": [(t, mm, round(r, 2)) for t, mm, r in inband]}


def aimed_at(stats, units) -> str:
    """Which model the mode has bitten: pooled rate >= 0.20 (finals if both models have n >= 10 there, else all
    stages); failing that, any task whose clean final rate is >= 0.5 at n >= 10 on a model; failing that, the
    premises' own declared aim."""
    base = stats["final"] if all(stats["final"][mm][1] >= 10 for mm in MODELS) else stats["all"]
    hits = [mm for mm in MODELS if base[mm][1] and base[mm][0] / base[mm][1] >= AIM_RATE]
    if not hits:
        hits = [mm for mm in MODELS if any(by[mm][1] >= BIMODAL_MIN_TASK_N and by[mm][0] / by[mm][1] >= 0.5
                                           for by in stats["per_task_final"].values())]
    if len(hits) == 2:
        return "both"
    if hits:
        return hits[0]
    declared = Counter(str(u["premise_obj"].get("aimed_at") or "").lower() for u in units)
    declared = Counter({k: v for k, v in declared.items() if k in ("fable", "astra", "both")})
    return declared.most_common(1)[0][0] if declared else "unknown"


# ----------------------------------------------------------------------------------------------- outputs
CSV_FIELDS = ["task", "version", "premise", "stage", "mode", "mode_source", "label", "stated", "template_declared",
              "decisive", "family", "mechanism", "aimed_at_declared", "fable_misses", "fable_runs", "fable_rate",
              "astra_misses", "astra_runs", "astra_rate", "fable_gated_excluded", "astra_gated_excluded",
              "fable_void_trials", "astra_void_trials", "verdict", "verdict_source", "presumed_ambiguous",
              "oracle_missed", "checks", "campaigns", "tree", "misreading_160"]


def unit_row(u) -> dict:
    p = u["premise_obj"]
    row = {"task": u["task"], "version": u["version"], "premise": u["premise"], "stage": u["stage"], "mode": u["mode"],
           "mode_source": u["mode_source"], "label": u["label"], "stated": u["stated"],
           "template_declared": p.get("template", "") or "", "decisive": bool(p.get("decisive")),
           "family": p.get("family", ""), "mechanism": p.get("mechanism", ""), "aimed_at_declared": p.get("aimed_at", ""),
           "verdict": u["verdict"], "verdict_source": u["verdict_source"], "presumed_ambiguous": u["presumed_ambiguous"],
           "oracle_missed": u["oracle_missed"], "checks": " ".join(p.get("checks", [])),
           "campaigns": " ".join(u["campaigns"]), "tree": u["tree"],
           "misreading_160": re.sub(r"\s+", " ", str(p.get("misreading", "")))[:160]}
    for mm in MODELS:
        row[f"{mm}_misses"], row[f"{mm}_runs"] = u[f"{mm}_misses"], u[f"{mm}_runs"]
        r = rate(u[f"{mm}_misses"], u[f"{mm}_runs"])
        row[f"{mm}_rate"] = "" if r is None else f"{r:.3f}"
        row[f"{mm}_gated_excluded"] = u[f"{mm}_gated"] + u[f"{mm}_nostep"]
        row[f"{mm}_void_trials"] = u[f"{mm}_void_trials"]
    return row


def unit_sort_key(u):
    return (0 if u["stage"] == "final" else 1, u["task"], vkey(u["version"]), int(re.sub(r"\D", "", u["premise"]) or 0)
            if u["premise"][1:].isdigit() else 0, u["premise"])


def evidence_row(u) -> dict:
    row = {"task": u["task"], "version": u["version"], "premise": u["premise"], "stage": u["stage"],
           "fable": [u["fable_misses"], u["fable_runs"]], "astra": [u["astra_misses"], u["astra_runs"]]}
    if u["verdict"]:
        row["audit"] = u["verdict"]
    return row


def write_outputs(result, out_dir: Path, date: str, curated_path: Path | None, modes_out: Path | None,
                  generated: str, root: Path) -> dict:
    out_dir.mkdir(parents=True, exist_ok=True)
    units = sorted(result["units"], key=unit_sort_key)
    csv_path = out_dir / f"INTERNAL-evidence-{date}.csv"
    with open(csv_path, "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=CSV_FIELDS)
        w.writeheader()
        for u in units:
            w.writerow(unit_row(u))
    by_mode = defaultdict(list)
    for u in units:
        by_mode[u["mode"]].append(u)
    by_template = defaultdict(list)
    for u in units:
        tpl = str(u["premise_obj"].get("template") or "")
        m = TEMPLATE_RE.match(tpl)
        by_template[(m.group(1) if m and not tpl.lower().startswith("filler") else ("filler" if tpl else "(none)"))].append(u)
    stats = {mid: compute_status(us) for mid, us in by_mode.items()}
    for mid, us in by_mode.items():
        stats[mid]["aimed_at"] = aimed_at(stats[mid], us)
        stats[mid]["units"] = len(us)
        stats[mid]["tasks"] = sorted({u["task"] for u in us})
    tstats = {}
    for tpl, us in by_template.items():
        s = compute_status(us)
        tstats[tpl] = {"units": len(us), "final": s["final"], "all": s["all"], "genuine_tasks": s["genuine_tasks"],
                       "tasks": sorted({u["task"] for u in us})}
    totals = {"units": len([u for u in units if u["version"] != "lab"]), "lab_units": len([u for u in units if u["version"] == "lab"]),
              "tasks": len({u["task"] for u in units if u["version"] != "lab"}),
              "runs_counted": result["runs_counted"], "valid_trials": result["trials_counted"],
              "premise_runs": {mm: sum(u[f"{mm}_runs"] for u in units if u["version"] != "lab") for mm in MODELS},
              "campaign_folders": result["campaigns_seen"], "trees_indexed": result["index_size"],
              "unmapped_units": len(by_mode.get("UNMAPPED", []))}
    pooled = {"schema": "traplib-evidence/1", "generated": generated, "root": str(root), "totals": totals,
              "status_rules": {"proven": [PROVEN_MIN_GENUINE_TASKS, PROVEN_MIN_RATE, PROVEN_MIN_N],
                               "dead": [DEAD_MAX_RATE, DEAD_MIN_N], "bimodal": [BIMODAL_LOW, BIMODAL_HIGH, BIMODAL_MIN_TASK_N],
                               "presumed_ambiguous_rate": PRESUMED_AMBIGUOUS_RATE},
              "modes": {mid: {k: v for k, v in s.items()} for mid, s in sorted(stats.items())},
              "templates_declared": dict(sorted(tstats.items())),
              "skips": result["skips"].tally(), "skip_items": result["skips"].items,
              "verdict_citations": result["verdict_checks"],
              "unmapped": [unit_row(u) for u in by_mode.get("UNMAPPED", [])]}
    pooled_path = out_dir / f"INTERNAL-evidence-{date}-pooled.json"
    pooled_path.write_text(json.dumps(pooled, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    written = {"csv": str(csv_path), "pooled": str(pooled_path)}
    if curated_path and curated_path.is_file() and modes_out:
        written["modes"] = str(write_modes(curated_path, modes_out, by_mode, stats, generated, date))
    return {"written": written, "stats": stats, "totals": totals, "skips": result["skips"].tally()}


def measured_sentence(mid, s, date) -> str:
    f, a, fs = s["final"], s["all"], s["final_strict"]
    if re.fullmatch(r"\d{8}", date):
        date = f"{date[:4]}-{date[4:6]}-{date[6:]}"
    parts = [f"Measured here (build_evidence.py, {date}): final 10x2 pooled Fable {fmt(*f['fable'])}, Astra {fmt(*f['astra'])}; "
             f"all stages Fable {fmt(*a['fable'])}, Astra {fmt(*a['astra'])} (AMBIGUOUS/DEFECT units excluded)"]
    if fs != f:
        parts.append(f"; without unaudited >=90% units, final Fable {fmt(*fs['fable'])}, Astra {fmt(*fs['astra'])}")
    parts.append(f". Audited GENUINE in {len(s['genuine_tasks'])} task(s). Status {s['status']}: {s['reasons'][0]}.")
    return "".join(parts)


def write_modes(curated_path: Path, modes_out: Path, by_mode, stats, generated: str, date: str) -> Path:
    curated = load_json(curated_path)
    modes = []
    for cm in curated.get("modes", []):
        mid = cm["id"]
        s = stats.get(mid)
        units = by_mode.get(mid, [])
        finals = [evidence_row(u) for u in sorted(units, key=unit_sort_key) if u["stage"] == "final"]
        pilots = [evidence_row(u) for u in sorted(units, key=unit_sort_key) if u["stage"] != "final"]
        mode = {k: v for k, v in cm.items() if not k.startswith("_")}
        if s is None:
            mode["status"] = "promising" if cm.get("_allow_unmeasured") else "dead"
            raise SystemExit(f"mode {mid} has no measured unit; give it evidence or drop it from modes-curated.json")
        mode["status"] = s["status"]
        if s["status"] == "unmeasured":
            raise SystemExit(f"mode {mid} has no valid run")
        # a dead-list (D) mode short of "dead" only for want of runs is flagged low_n (traplib accepts it, the lint still
        # never allows it as decisive); one that misses above the dead rate on n >= DEAD_MIN_N is left unflagged so the
        # library build refuses it and a human looks
        if mid.startswith("D") and s["status"] != "dead":
            al = s["all"]
            if all(al[mm][1] == 0 or al[mm][0] / al[mm][1] <= DEAD_MAX_RATE for mm in MODELS) \
                    and any(al[mm][1] < DEAD_MIN_N for mm in MODELS):
                mode["low_n"] = True
        mode["aimed_at"] = s["aimed_at"]
        mode["summary"] = (cm.get("summary", "").rstrip() + " " + measured_sentence(mid, s, date)).strip()
        # evidence.pooled = every valid run of every row, pilot and final, AMBIGUOUS/DEFECT rows excluded: the pool the
        # dead rule reads (traplib.py checks proven and dead on this one pair). The proven decision itself is taken on
        # final rows only (SCHEMA.md); both pools are spelled out in the summary's measured sentence.
        mode["evidence"] = {"internal": finals + pilots,
                            "pooled": {mm: s["all"][mm] for mm in MODELS},
                            "external": cm.get("evidence", {}).get("external", []),
                            "traces": cm.get("evidence", {}).get("traces", [])}
        order = ["id", "aliases", "name", "family", "status", "low_n", "aimed_at", "clock", "summary", "loopholes", "recipe",
                 "proof_obligations", "hazards", "kills", "trace_signals", "domains", "example", "evidence"]
        modes.append({k: mode[k] for k in order if k in mode})
    out = {"schema": "traplib/1", "source": "internal", "generated": generated, "modes": modes}
    modes_out.write_text(json.dumps(out, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    return modes_out


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--root", default=str(DEFAULT_ROOT), help="workspace root (read-only)")
    ap.add_argument("--out", default=str(HERE.parent / "research"), help="directory for the CSV and pooled JSON")
    ap.add_argument("--labels", default=str(HERE.parent / "research/INTERNAL-trap-evidence.csv"))
    ap.add_argument("--map", default=str(HERE / "mode-map.json"))
    ap.add_argument("--verdicts", default=str(HERE / "audit-verdicts.json"))
    ap.add_argument("--curated", default=str(HERE / "modes-curated.json"))
    ap.add_argument("--modes-out", default=str(HERE / "modes-internal.json"))
    ap.add_argument("--date", default=dt.date.today().strftime("%Y%m%d"))
    ap.add_argument("--generated", default=dt.datetime.now().astimezone().isoformat(timespec="minutes"))
    args = ap.parse_args(argv)
    root = Path(args.root).resolve()
    result = build(root, Path(args.labels), Path(args.map), Path(args.verdicts))
    rep = write_outputs(result, Path(args.out), args.date, Path(args.curated), Path(args.modes_out), args.generated, root)
    t = rep["totals"]
    print(f"units {t['units']} (+{t['lab_units']} lab) over {t['tasks']} tasks; runs {t['runs_counted']}; "
          f"valid trials {t['valid_trials']}; premise-runs {t['premise_runs']}; unmapped units {t['unmapped_units']}")
    for k, n in rep["skips"].items():
        print(f"  skip  {n:5}  {k}")
    for mid, s in sorted(rep["stats"].items(), key=lambda kv: (kv[0][0], int(re.sub(r'\D', '', kv[0]) or 0))):
        print(f"  {mid:8} {s['status']:10} aimed {s['aimed_at']:7} final F {fmt(*s['final']['fable']):>8} A {fmt(*s['final']['astra']):>8}"
              f"  all F {fmt(*s['all']['fable']):>9} A {fmt(*s['all']['astra']):>9}  genuine tasks {len(s['genuine_tasks'])}")
    for k, v in rep["written"].items():
        print(f"wrote {k}: {v}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
