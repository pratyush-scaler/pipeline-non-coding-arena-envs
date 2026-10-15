"""Batch-6 controller helper (2026-10-13; preflight, validate, wait, rerun-void, blind reader, author-check 2026-10-15).

    python3 -I b6ctl.py check  <task-dir>                 quarantine stale verification/ receipts, then design_lint
                                                           (with additivity) + selftest on a mktemp copy
    python3 -I b6ctl.py validate <task-dir> [--timeout S]  the tree's authoring/validate.py, arguments detected from its
                                                           argv usage, py3.11 -I -B, on a mktemp copy without verification/
    python3 -I b6ctl.py author-check <task-dir> [--timeout S]
                                                           the author's last gate: check with design_lint --b8 (B8
                                                           composition + instruction example leaks), validate, then tree
                                                           hygiene (traps.json schema b8/premises/1, no verification/, the
                                                           Dockerfile copies only files/); one READY / NOT READY verdict
                                                           listing every failing item with its fix; exit 0 only if READY
    python3 -I b6ctl.py preflight [--model fable|astra|both]   GET /v1/models with each key in keys.env; prints NAME CODE
    python3 -I b6ctl.py launch <task-dir> pilot|final [ws] [--no-preflight] [--dry-run]
                                                           measure.py launch (pilot = 5x2 + oracle/nop, final = 10x2);
                                                           refuses unless both keys answer 200
    python3 -I b6ctl.py rerun-void <task-dir> pilot|final fable|astra [--no-preflight] [--dry-run]
                                                           measure.py launch --rerun-void, after that model's preflight
    python3 -I b6ctl.py wait <task-dir> pilot|final [--model fable|astra|both] [--every S] [--max S]
                                                           block in the foreground until the campaign is done or void
    python3 -I b6ctl.py gate   <task-dir> pilot|final      signal_gate on this version's campaigns (reruns included)
    python3 -I b6ctl.py blind-prep <task-dir> [--out DIR]  reader workspace in a mktemp dir under DIR ($CLAUDE_SCRATCH)
    python3 -I b6ctl.py blind-grade <task-dir> <workspace> grade every step the reader delivered
    python3 -I b6ctl.py status                              measure.py status, b6 rows only

Workflow (2026-10-15): a teammate types these instead of the commands above.
    python3 -I b6ctl.py doctor                              one OK/WARN/FAIL line per prerequisite, each with its fix;
                                                           exit 0 only if nothing FAILs (never starts or stops a pool)
    python3 -I b6ctl.py new <slug> [--level f0|f1|f2] [--seed <session-id>] [--plan <brief.md>]
                                                           scaffold TASKS/a_f<level>_<slug> 1.0.0 from the skeleton
    python3 -I b6ctl.py prompt author|tune|audit|blind <task-dir> [--notes FILE] [--out DIR]
                                                           a ready-to-paste agent prompt from production/prompts/<kind>.md
                                                           (built-in minimal one if missing); blind runs blind-prep
    python3 -I b6ctl.py run <task-dir> pilot|final [ws] [--max MIN]
                                                           preflight, launch, wait, re-run voids once, gate, census;
                                                           one VERDICT line; exit 0 hard, 1 easy/near/defect, 3 void, 124
    python3 -I b6ctl.py next <task-dir>                     the current stage and the exact next command(s)
    python3 -I b6ctl.py ship <task-dir> --audit <report.md> [ws] [--out DIR] [--max MIN]
                                                           freeze to _versions/, harbor tasks-check, assemble the zips

Campaign dirs follow measure.py: pipeline-artifacts/b4/<name>-<version>-<stage>-<model>[-rerun<ts>]. A task dir may be
a live tree (envs-b6/<name>) or an archived one (envs-b6/_versions/<name>-<version>); <name> drops the version suffix.
author-check, blind-grade, run (census) and ship record their results under STATE/<kind>/<name>-<version>.json for
`next`; audit reports live at STATE/audits/<name>-<version>.md.
Exit codes: 0 ok, 1 check/validation failed, 2 nothing to act on or bad input, 3 refused or finished void, 124 timeout.
Every command that writes scratch makes its own mktemp dir. Nothing here prints a credential.
"""
from __future__ import annotations

import argparse
import contextlib
import fcntl
import glob
import hashlib
import io
import json
import os
import re
import shlex
import shutil
import stat
import subprocess
import sys
import tempfile
import time
import tomllib
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import paths  # noqa: E402  (ROOT, TASKS, STATE, ...; paths.py documents the ARENA_* overrides)

ROOT = paths.ROOT
PY = paths.PY311
TOOLS = paths.TOOLS
ENV = {k: v for k, v in os.environ.items() if k != "ANTHROPIC_AUTH_TOKEN"}
KEYS = paths.KEYS
LEDGER = paths.LEDGER
STALE = paths.STALE
STATUS_LOCK = paths.WAIT_LOCK
MODELS = ("fable", "astra")
TERMINAL = ("done", "failed", "void-auth")
# Names as pipeline/benchmark reads them from keys.env (coder_run.keys_values, support.redact). The Anthropic host
# honours ANTHROPIC_BASE_URL (forwarded to Coder, coder.FORWARD_NAMES); OPENAI_BASE_URL is dropped on Coder
# (coder_run.REMOTE_DROPPED_KEYS), so the OpenAI key is tested against api.openai.com.
PREFLIGHT = {"fable": ("ANTHROPIC_API_KEY", "https://api.anthropic.com", "ANTHROPIC_BASE_URL"),
             "astra": ("OPENAI_API_KEY", "https://api.openai.com", None)}


def version(task: Path) -> str:
    return tomllib.loads((task / "task.toml").read_text())["task"]["version"]


def base_name(task: Path) -> str:
    """The task name as measure.py records it: an archived envs-b6/_versions/<name>-<version> drops the suffix."""
    v = version(task)
    return task.name[: -len(v) - 1] if task.name.endswith("-" + v) else task.name


def _pipeline() -> None:
    """Make pipeline/ importable (read-only helpers) without writing pipeline/__pycache__."""
    sys.dont_write_bytecode = True
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))


def _identity(task: Path) -> str | None:
    _pipeline()
    from pipeline.artifacts import identity  # the function tc_path.py and assemble_b4_zip.py bind receipts with
    try:
        return identity(task)
    except ValueError as exc:
        print(f"WARN cannot compute the tree identity: {exc}")
        return None


# --------------------------------------------------------------------------- workflow records (read by `next`)

def _rec_path(kind: str, task: Path, suffix: str = ".json") -> Path:
    return paths.STATE / kind / f"{base_name(task)}-{version(task)}{suffix}"


def _write_rec(kind: str, task: Path, data: dict, suffix: str = ".json") -> Path:
    p = _rec_path(kind, task, suffix)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps({"task": base_name(task), "version": version(task), "tree": str(task),
                             "at": time.strftime("%Y-%m-%d %H:%M:%S"), **data}, indent=1) + "\n")
    return p


def _read_rec(kind: str, task: Path, suffix: str = ".json") -> dict | None:
    p = _rec_path(kind, task, suffix)
    try:
        return json.loads(p.read_text()) if p.is_file() else None
    except ValueError:
        return None


# --------------------------------------------------------------------------- stale verification/ receipts

def receipts(task: Path) -> list[dict]:
    """Judge every file under <task>/verification against the tree's identity and its task.toml version."""
    vdir = task / "verification"
    if not vdir.is_dir():
        return []
    cur, ver, base = _identity(task), version(task), base_name(task)
    own = {task.name, base, f"{base}-{ver}"}
    out = []
    for p in sorted(vdir.rglob("*")):
        if not p.is_file() or p.name == ".DS_Store":
            continue
        r = {"path": p, "rel": p.relative_to(vdir).as_posix(), "verdict": "unjudged", "why": [], "old": None}
        out.append(r)
        try:
            rec = json.loads(p.read_text())
        except (ValueError, UnicodeError):
            r["why"].append("not a JSON receipt")
            continue
        if not isinstance(rec, dict) or not ({"artifact_sha256", "task"} & rec.keys()):
            r["why"].append("no artifact_sha256 or task field")
            continue
        named = str(rec.get("task") or "")
        m = re.fullmatch(re.escape(base) + r"-(\d+\.\d+\.\d+)", named)
        r["old"] = m.group(1) if m else None
        if cur and rec.get("artifact_sha256") is not None and rec["artifact_sha256"] != cur:
            r["why"].append("artifact_sha256 is not this tree's identity")
        if named and named not in own:
            r["why"].append(f"task field names {named}, tree is {base} {ver}")
        r["verdict"] = "stale" if r["why"] else "current"
    return out


def quarantine(task: Path) -> int:
    """MOVE stale receipts (never delete them) to production/state/stale-receipts/<task>-<old version>-<timestamp>/.
    Archived trees (_versions/) are reported, never modified. Returns the number of stale receipts left in place."""
    archived = "_versions" in task.parts
    left = 0
    stamp = time.strftime("%Y%m%dT%H%M%S")
    for r in receipts(task):
        why = "; ".join(r["why"])
        if r["verdict"] == "current":
            print(f"RECEIPT current  verification/{r['rel']}")
        elif r["verdict"] == "unjudged":
            print(f"RECEIPT unjudged verification/{r['rel']} ({why}); left in place")
        elif archived:
            left += 1
            print(f"RECEIPT STALE    verification/{r['rel']} ({why}); archived tree, NOT moved")
        else:
            dest, n = STALE / f"{base_name(task)}-{r['old'] or 'unknown'}-{stamp}", 1
            target = dest / r["rel"]
            while target.exists():
                n += 1
                target = Path(f"{dest}-{n}") / r["rel"]
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(r["path"]), str(target))
            print(f"RECEIPT STALE    verification/{r['rel']} ({why}); moved to {target}")
    vdir = task / "verification"
    if not archived and vdir.is_dir():  # rmdir only what the moves left empty
        for d in sorted((p for p in vdir.rglob("*") if p.is_dir()), key=lambda p: len(p.parts), reverse=True):
            if not any(d.iterdir()):
                d.rmdir()
        if not any(vdir.iterdir()):
            vdir.rmdir()
    return left


def check(task: Path) -> int:
    return _check(task)["rc"]


def _check(task: Path, lint_args: tuple[str, ...] = ()) -> dict:
    """check's work. Returns rc plus what failed: the lint report, selftest BAD lines, __pycache__, stale receipts."""
    left = quarantine(task)
    sys.stdout.flush()
    rep = Path(tempfile.mkdtemp(prefix="b6-lint-"))
    rc = subprocess.run([PY, "-I", "-B", str(TOOLS / "design_lint.py"), str(task), *lint_args,
                         "--json", str(rep / "lint.json")], cwd=ROOT).returncode
    lint = (json.loads((rep / "lint.json").read_text()) if (rep / "lint.json").is_file()
            else {"fails": [f"design_lint exited {rc} without a report"] if rc else [], "warns": [], "oks": []})
    shutil.rmtree(rep)
    tmp = Path(tempfile.mkdtemp(prefix="b6-st-"))
    shutil.copytree(task, tmp / "task", ignore=shutil.ignore_patterns("__pycache__", "verification"))
    st = subprocess.run([PY, "-I", "-B", str(paths.SELFTEST), str(tmp / "task")],
                        capture_output=True, text=True)
    bad = [l for l in st.stdout.splitlines() if l.startswith("BAD")]
    print(f"SELFTEST: {sum(l.startswith('ok') for l in st.stdout.splitlines())} ok, {len(bad)} BAD")
    for l in bad:
        print("  ", l)
    pyc = list(task.rglob("__pycache__"))
    if pyc:
        print("FAIL __pycache__ present:", [str(p.relative_to(task)) for p in pyc][:5])
    if left:
        print(f"FAIL {left} stale receipt(s) left in an archived tree")
    return {"rc": 1 if rc or bad or pyc or left else 0, "lint_rc": rc, "lint": lint, "selftest_bad": bad,
            "pycache": [str(p.relative_to(task)) for p in pyc], "stale_left": left}


# --------------------------------------------------------------------------- validate.py with detected arguments

def _role(text: str) -> str | None:
    t = text.lower()
    if t == "s" or re.search(r"scr|tmp|temp|mktemp|work|empty|out", t):
        return "scratch"
    if t == "t" or re.search(r"task|tree|bundle", t):
        return "task"
    return None


def validate_args(script: Path) -> list[str]:
    """Roles of argv[1..n], read from the script: the `usage:` line's <placeholders> first, then the names the
    script assigns sys.argv[i] to. Raises ValueError when an index cannot be classified; it never guesses."""
    src = script.read_text(errors="replace")
    if "argparse" in src or re.search(r"sys\.argv\[\s*-?\d*\s*:", src):
        raise ValueError("script parses argv with argparse or a slice; run it by hand")
    used = sorted({int(n) for n in re.findall(r"sys\.argv\[\s*(\d+)\s*\]", src)} - {0})
    if used and used != list(range(1, used[-1] + 1)):
        raise ValueError(f"argv indices {used} are not contiguous")
    roles: dict[int, str] = {}
    m = re.search(r"(?i)\busage:\s*(.*)", src) or re.search(r"validate\.py\s+(<.*)", src)
    for i, tok in enumerate(re.findall(r"<([^>]+)>", m.group(1)) if m else [], 1):
        if i in used and _role(tok):
            roles[i] = _role(tok)
    for name, i in re.findall(r"(?m)^\s*([A-Za-z_]\w*)\s*=.*?sys\.argv\[\s*(\d+)\s*\]", src):
        if int(i) in used and int(i) not in roles and _role(name):
            roles[int(i)] = _role(name)
    missing = [i for i in used if i not in roles]
    if missing:
        raise ValueError(f"cannot tell what argv{missing} is (usage: {m.group(1).strip() if m else 'none'})")
    return [roles[i] for i in used]


def validate(task: Path, timeout: int) -> int:
    return _validate(task, timeout)["rc"]


def _validate(task: Path, timeout: int) -> dict:
    """validate's work. Returns rc, the FAIL/BAD lines, the stale-receipt count, the kept log and a one-line reason."""
    script = task / "authoring/validate.py"
    if not script.is_file():
        print(f"VALIDATE {task.name}: no authoring/validate.py")
        return {"rc": 2, "fails": [], "stale": 0, "log": None, "why": "no authoring/validate.py"}
    try:
        roles = validate_args(script)
    except ValueError as exc:
        print(f"VALIDATE {task.name}: {exc}")
        return {"rc": 2, "fails": [], "stale": 0, "log": None, "why": str(exc)}
    run = Path(tempfile.mkdtemp(prefix=f"b6-val-{base_name(task)}-"))
    copy, scratch = run / task.name, run / "scratch"
    # verification/ holds packaging-time receipts, not authored content; they are judged below instead.
    shutil.copytree(task, copy, symlinks=True, ignore=shutil.ignore_patterns("verification"))
    scratch.mkdir()
    argv = [str(copy) if r == "task" else str(scratch) for r in roles]
    print(f"VALIDATE {task.name} {version(task)}: validate.py {' '.join('<' + r + '>' for r in roles) or '(no args)'}"
          f" on a copy in {run}", flush=True)
    log = run / "validate.log"
    try:
        with open(log, "w") as fh:
            rc = subprocess.run([PY, "-I", "-B", str(copy / "authoring/validate.py"), *argv], cwd=run, env=ENV,
                                stdout=fh, stderr=subprocess.STDOUT, timeout=timeout).returncode
    except subprocess.TimeoutExpired:
        rc = 124
    lines = [l.rstrip() for l in log.read_text(errors="replace").splitlines() if l.strip()]
    fails = [l.strip() for l in lines if re.match(r"\s*(FAIL|BAD)\b", l)]
    for l in fails[:20]:
        print("  ", l[:200])
    if len(fails) > 20:
        print(f"   ... {len(fails) - 20} more")
    stale = [r for r in receipts(task) if r["verdict"] == "stale"]
    if stale:
        print(f"STALE {len(stale)} verification/ receipt(s) in the tree: run `b6ctl.py check` to quarantine them")
    last = f"validate.py exit {rc}{' (timeout)' if rc == 124 else ''}; last: {lines[-1][:200] if lines else '(no output)'}"
    print(last)
    if rc == 0 and not stale:
        shutil.rmtree(run)
    else:
        print(f"log kept: {log}")
    return {"rc": rc or (1 if stale else 0), "fails": fails, "stale": len(stale),
            "log": None if rc == 0 and not stale else log, "why": last}


# --------------------------------------------------------------------------- author-check (READY / NOT READY)

B8_SCHEMA = "b8/premises/1"
BRIEF = "production/briefs/AUTHOR-BRIEF-B8.md"
# design_lint FAIL text -> the fix, first match wins
LINT_HINTS = [
    (r"trap library is unreadable", "rebuild it: python3 -I production/traps/traplib.py build"),
    (r"is not in the (trap library|built-in)", "use a library id or alias: python3 -I production/traps/traplib.py list"),
    (r"is dead in the trap library", "replace the premise with a proven/promising mode (traplib.py list --status proven)"),
    (r"declares no trap-library template", 'add "template": "<library id>" to every decisive premise'),
    (r"B8: \d+ decisive premise", f"mark >= 3 premises \"decisive\": true, each built from a library mode ({BRIEF} §3)"),
    (r"B8: decisive premises span", "take the decisive modes from >= 2 library families (plan_batch.py does this)"),
    (r"B8: no decisive premise is aimed at", 'aim one decisive premise at each model: "aimed_at": "fable" / "astra"'),
    (r"STATED", "a stated rule never bites: make the trigger fact inferred (HARD-DOCTRINE §2) or demote it to filler"),
    (r"verbatim anchors in >= \d+ files other", "add by-the-way anchors in two more documents of other parties; copy "
                                                "each anchor's text verbatim into traps.json"),
    (r"projected free share", "raise the decisive premises' weight to >= 60 of the step's 100 points (25/21/17)"),
    (r"clock premise .* heaviest|CLOCK premise is the heaviest", "make a non-clock decisive premise the heaviest"),
    (r"instruction example", "rewrite the example with no number, ID or fixture value (or justify it in leak_allow)"),
    (r"leaks: reference-answer", "remove the graded value from the instruction, or justify it in traps.json leak_allow"),
    (r"echoed in the instruction", "reword the instruction: schema-only field names, no 5-word run from a rule/anchor"),
    (r"resolving_quote|anchor text not found|needs an existing file", "copy the sentence verbatim from the fixture file"),
    (r"additivity", "solve.py ARENA_MISREAD=<ids> must fail exactly those premises' checks with the exact partial reward"),
    (r"runtime", "restore tests/ and steps/*/solution/_arena_runtime from production/templates/skeleton"),
    (r"trap_families", "set task.toml [metadata] trap_families to the families in traps.json"),
    (r"carries \d+% of the step|premises carry|coverage \(free\) share", "rebalance weights: premise <= 25%, premises "
                                                                         ">= 55%, coverage <= 35% per step"),
    (r"interlock", "keep exactly one reciprocal interlocks_with pair (HARD-DOCTRINE §2.5)"),
    (r"masked_by", "masked_by must name interlocked premises and carry masked_reason"),
    (r"mechanism|Fable-type|Astra-type|inferred/default-technique", "fix the premise mechanisms (HARD-DOCTRINE §1/§2.6)"),
    (r"premises \(need|repeated family|distinct families|timestamp-ordering", "fix the premise count/families "
                                                                             "(AUTHOR-BRIEF-B8 §2)"),
    (r"neither a premise check|both a premise check|belongs to two premises|does not exist|no checks",
     "map every objective check to exactly one premise or to coverage_checks"),
    (r"missing (misreading|aimed_at|salience)|default_technique", "fill the missing traps.json field"),
]


def lint_hint(msg: str) -> str:
    return next((h for pat, h in LINT_HINTS if re.search(pat, msg)), f"see {BRIEF}")


def dockerfile_problems(task: Path) -> list[str]:
    """environment/Dockerfile may COPY/ADD only files/ (multi-stage --from copies excepted)."""
    df = task / "environment/Dockerfile"
    if not df.is_file():
        return ["environment/Dockerfile is missing"]
    out = []
    text = re.sub(r"\\\n", " ", df.read_text(errors="replace"))
    for line in text.splitlines():
        m = re.match(r"\s*(COPY|ADD)\s+(.*)", line, re.I)
        if not m:
            continue
        args = m.group(2).strip()
        if args.startswith("["):
            try:
                toks = json.loads(args)
            except ValueError:
                out.append(f"unparseable {m.group(1)}: {line.strip()}")
                continue
        else:
            toks = args.split()
        if any(t.startswith("--from") for t in toks):
            continue
        srcs = [t for t in toks if not t.startswith("--")][:-1]
        bad = [s for s in srcs if not re.fullmatch(r"\./?files/?|files(/.*)?", s)]
        if bad or not srcs:
            out.append(f"{m.group(1).upper()} copies {bad or srcs or '(nothing)'}; only files/ may enter the image")
    return out


def tools_json_problems(task: Path) -> list[str]:
    """environment/tools.json must declare exactly the deliverables tests/outputs.json grades (Arena 261011 R07/R11:
    the skeleton's placeholder outputs shipped in 13 tasks and Harbor's reviewer failed them on Typos)."""
    tj, oj = task / "environment/tools.json", task / "tests/outputs.json"
    if not tj.is_file() or not oj.is_file():
        return [f"missing {'environment/tools.json' if not tj.is_file() else 'tests/outputs.json'}"]
    try:
        have = json.loads(tj.read_text()).get("workspace", {}).get("outputs")
        want = [{"step": o["step"], "path": f"/app/deliverables/{o['file']}"}
                for o in json.loads(oj.read_text())["outputs"]]
    except (ValueError, KeyError, TypeError) as exc:
        return [f"tools.json / outputs.json unreadable ({exc.__class__.__name__})"]
    return [] if have == want else [f"tools.json workspace.outputs {have} != tests/outputs.json {want}"]


def author_check(task: Path, timeout: int) -> int:
    """check (design_lint --b8) + validate + tree hygiene, then ONE verdict listing every failing item with its fix."""
    items: list[tuple[str, str, str]] = []
    print(f"== author-check {task}\n== 1/3 check: receipts, design_lint --b8, selftest", flush=True)
    c = _check(task, ("--b8",))
    items += [("lint", f, lint_hint(f)) for f in c["lint"]["fails"]]
    items += [("selftest", l.strip(), "the shipped runtime must be the skeleton's (261011-patched); rerun "
               "selftest.py on a mktemp copy for the detail") for l in c["selftest_bad"]]
    if c["pycache"]:
        items.append(("tree", f"__pycache__ present: {c['pycache'][:5]}", "delete them; always run python with -B"))
    if c["stale_left"]:
        items.append(("tree", f"{c['stale_left']} stale receipt(s) in an archived tree",
                      "author on the live tree, never under _versions/"))
    print("== 2/3 validate: authoring/validate.py on a mktemp copy", flush=True)
    v = _validate(task, timeout)
    if v["rc"]:
        detail = "; ".join(v["fails"][:3]) or v["why"]
        items.append(("validate", detail, f"fix authoring/validate.py's failures (log: {v['log']}), then rerun"
                      if v["log"] else "write authoring/validate.py with a `usage: validate.py <task> <scratch>` line"))
    print("== 3/3 tree hygiene", flush=True)
    tp = task / "authoring/traps.json"
    try:
        schema = json.loads(tp.read_text()).get("schema") if tp.is_file() else None
    except ValueError:
        schema = "unparseable"
    if schema != B8_SCHEMA:
        items.append(("traps", f"authoring/traps.json schema is {schema!r}", f'set "schema": "{B8_SCHEMA}" ({BRIEF} §3)'))
    if (task / "verification").exists():
        items.append(("tree", "verification/ is present", "remove it: receipts are written at packaging time only"))
    items += [("docker", p, "environment/Dockerfile must COPY only files/ (as in production/templates/skeleton)")
              for p in dockerfile_problems(task)]
    items += [("tools", p, f"run: python3 -I {TOOLS / 'fix_tools_json.py'} {task}") for p in tools_json_problems(task)]
    head = f"AUTHOR-CHECK {base_name(task)} {version(task)}"
    rec = _write_rec("author-check", task, {"verdict": "NOT READY" if items else "READY", "identity": _identity(task),
                                            "items": [{"where": w, "what": x, "fix": f} for w, x, f in items]})
    notes = _rec_path("author-check", task, ".notes.md")
    if not items:
        notes.unlink(missing_ok=True)
        print(f"\n{head}: READY\nrecorded: {rec}")
        return 0
    print(f"\n{head}: NOT READY ({len(items)} item{'s' if len(items) > 1 else ''})")
    for i, (where, what, fix) in enumerate(items, 1):
        print(f"  {i:2}. [{where}] {what}\n      fix: {fix}")
    notes.write_text(f"{head}: NOT READY\n\n" + "".join(f"{i}. [{w}] {x}\n   fix: {f}\n"
                                                        for i, (w, x, f) in enumerate(items, 1)))
    print(f"recorded: {rec}\nback to the author: python3 -I {TOOLS / 'b6ctl.py'} prompt author {shlex.quote(str(task))}"
          f" --notes {shlex.quote(str(notes))}")
    return 1


# --------------------------------------------------------------------------- key preflight

def _http_status(url: str, headers: dict[str, str]) -> str:
    """Status code of GET url. Headers travel on curl's stdin config (never argv); the body is discarded."""
    cfg = "".join(f'header = "{k}: {v}"\n' for k, v in headers.items())
    try:
        proc = subprocess.run([shutil.which("curl") or "/usr/bin/curl", "-s", "-o", "/dev/null", "-w", "%{http_code}",
                               "--max-time", "20", "-K", "-", url], input=cfg, capture_output=True, text=True, timeout=40)
    except (OSError, subprocess.TimeoutExpired):
        return "ERR"
    code = proc.stdout.strip()
    return code if code.isdigit() and code != "000" else "ERR"


def preflight(models=MODELS) -> bool:
    """Print `NAME CODE` per key, nothing else. True only if every key answered 200."""
    _pipeline()
    from pipeline.credentials import read_key_file
    keys = read_key_file(KEYS)
    ok = True
    for m in models:
        name, default, base_var = PREFLIGHT[m]
        key = keys.get(name, "")
        if not key:
            print(f"{name} missing", flush=True)
            ok = False
            continue
        base = (keys.get(base_var) or default) if base_var else default
        headers = ({"x-api-key": key, "anthropic-version": "2023-06-01"} if m == "fable"
                   else {"Authorization": f"Bearer {key}"})
        code = _http_status(base.rstrip("/") + "/v1/models", headers)
        print(f"{name} {code}", flush=True)
        ok = ok and code == "200"
    return ok


# --------------------------------------------------------------------------- launches

def _measure(argv: list[str], models, no_preflight: bool, dry_run: bool) -> int:
    if no_preflight:
        print("preflight skipped (--no-preflight)")
    elif not preflight(models):
        print("REFUSED: a provider key did not answer 200; fix keys.env (or pass --no-preflight)")
        return 3
    cmd = [paths.PY, "-B", str(paths.MEASURE), *argv]
    if dry_run:
        print("DRY-RUN", " ".join(cmd))
        return 0
    return subprocess.run(cmd, cwd=ROOT, env=ENV).returncode


def launch(task: Path, stage: str, ws: str | None, no_preflight: bool = False, dry_run: bool = False) -> int:
    argv = ["launch", str(task), "--stage", stage] + (["--ws", ws] if ws else [])
    return _measure(argv, MODELS, no_preflight, dry_run)


def rerun_void(task: Path, stage: str, model: str, no_preflight: bool = False, dry_run: bool = False) -> int:
    hits = [e for e in _ledger() if e.get("task") == str(task) and e.get("stage", "final") == stage
            and e.get("version") == version(task) and (e.get("runs", {}).get(model) or {}).get("state") == "void-auth"]
    if not hits:
        print(f"no void-auth {model} run in the ledger for {task} {version(task)} {stage}; nothing to re-run")
        return 2
    return _measure(["launch", str(task), "--stage", stage, "--rerun-void", model], (model,), no_preflight, dry_run)


# --------------------------------------------------------------------------- wait

def _ledger() -> list[dict]:
    return json.loads(LEDGER.read_text()).get("entries", []) if LEDGER.is_file() else []


def _entries(task: Path, stage: str) -> list[dict]:
    """Every ledger entry of this version and stage, launched from this path or under this name."""
    ver, names = version(task), {task.name, base_name(task)}
    return [e for e in _ledger() if e.get("version") == ver and e.get("stage", "final") == stage
            and (e.get("task") == str(task) or e.get("name") in names)]


def campaign(task: Path, stage: str) -> dict | None:
    """The latest ledger entry of this version and stage: launched from this path, else by name and version."""
    es = _entries(task, stage)
    es = [e for e in es if e.get("task") == str(task)] or es
    return max(es, key=lambda e: e.get("launched_at", 0)) if es else None


def status_line(e: dict) -> str:
    def cell(short):
        r = e["runs"].get(short) or {}
        s = r.get("state", "-")
        if s != "done":
            return f"{short} {s}"
        if short in ("oracle", "nop"):
            return f"{short} {(r.get('mean_reward') or 0):.2f}"
        sf = r.get("step_full") or {}
        steps = f" steps [{','.join(str(v) for v in sf.values())}]" if len(sf) > 1 else ""
        p = r.get("pass_at_1")
        return (f"{short} {r.get('full')}/{r.get('valid')} void {r.get('void', 0)}"
                f" pass@1 {'-' if p is None else f'{p:.2f}'}{steps}")
    shorts = [s for s in ("fable", "astra", "oracle", "nop") if s in e["runs"]]
    return f"{e['name']} {e['version']} {e.get('stage')} on {e.get('ws')}: " + " | ".join(cell(s) for s in shorts)


def _refresh() -> None:
    """One measure.py status pass, skipped while another b6ctl wait runs one (that pass refreshes every entry)."""
    STATUS_LOCK.parent.mkdir(parents=True, exist_ok=True)
    with open(STATUS_LOCK, "w") as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            return
        try:
            subprocess.run([paths.PY, "-B", str(paths.MEASURE), "status"],
                           cwd=ROOT, env=ENV, capture_output=True, text=True, timeout=3600)
        except subprocess.TimeoutExpired:
            print("measure.py status timed out; retrying next round", flush=True)


def wait(task: Path, stage: str, model: str, every: int, cap: int) -> int:
    """Foreground poll: no fork, no detach, so a background runner sees one process and its exit code."""
    want = MODELS if model == "both" else (model,)
    start, first = time.time(), True
    while True:
        e = campaign(task, stage)
        if e is None:
            print(f"no {stage} campaign of {base_name(task)} {version(task)} in the ledger", flush=True)
            return 2
        states = {m: (e["runs"].get(m) or {}).get("state") for m in want}
        if all(s in TERMINAL for s in states.values()):
            print(status_line(e), flush=True)
            voids = [m for m, s in states.items() if s != "done"]
            for m in voids:  # measure.py re-runs a void only for the path it launched
                print(f"{m} is {states[m]}: python3 -I {TOOLS / 'b6ctl.py'} rerun-void {e['task']} {stage} {m}",
                      flush=True)
            return 3 if voids else 0
        if time.time() - start > cap:
            print(f"TIMEOUT after {int(time.time() - start)} s: {status_line(e)}", flush=True)
            return 124
        if not first:
            print(f"{time.strftime('%H:%M:%S')} waiting: " + " ".join(f"{m} {s}" for m, s in states.items()), flush=True)
            time.sleep(every)
        first = False
        _refresh()


# --------------------------------------------------------------------------- gate / status

def void_dirs(task: Path, stage: str) -> set[str]:
    """Campaign dirs the ledger records as infrastructure loss (void_history, or a void-auth/failed current run)."""
    out = set()
    for e in _entries(task, stage):
        runs = [r for h in e.get("void_history") or [] for r in h.values() if isinstance(r, dict)]
        runs += [r for r in e.get("runs", {}).values() if r.get("state") in ("void-auth", "failed")]
        out |= {os.path.realpath(r["out"]) for r in runs if r.get("out")}
    return out


def campaign_dirs(task: Path, stage: str, model: str) -> list[Path]:
    """<name>-<version>-<stage>-<model> and its -rerun<ts> dirs, oldest first, whether finished or not."""
    base = paths.ARTIFACTS / f"{base_name(task)}-{version(task)}-{stage}-{model}"
    return [Path(d) for d in sorted(glob.glob(str(base))) + sorted(glob.glob(f"{base}-rerun*"))]


def stage_dirs(task: Path, stage: str, quiet: bool = False) -> dict[str, list[Path]]:
    """Per model, the finished (report.json) campaign dirs of this version and stage, ledger voids left out."""
    void, out = void_dirs(task, stage), {}
    for model in MODELS:
        out[model] = []
        for d in campaign_dirs(task, stage, model):
            if not (d / "report.json").is_file():
                continue
            if os.path.realpath(d) in void:
                if not quiet:
                    print(f"skipping {d.name}: the ledger records it as void (infrastructure loss)", flush=True)
                continue
            out[model].append(d)
    return out


def gate(task: Path, stage: str) -> int:
    base = paths.ARTIFACTS / f"{base_name(task)}-{version(task)}-{stage}"
    args = []
    for model, dirs in stage_dirs(task, stage).items():
        if not dirs:
            print(f"no finished {model} campaign at {base}-{model}")
            return 2
        for d in dirs:
            args += [f"--{model}", str(d)]
    out = paths.GATES / f"{base_name(task)}-{version(task)}-{stage}.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    return subprocess.run(["python3", "-I", str(TOOLS / "signal_gate.py"), str(task), *args, "--stage", stage,
                           "--json", str(out)]).returncode


def status() -> int:
    proc = subprocess.run([paths.PY, "-B", str(paths.MEASURE), "status"],
                          cwd=ROOT, env=ENV, capture_output=True, text=True)
    for line in proc.stdout.splitlines():
        if paths.TASKS.name in line or "a_f" in line and any(s in line for s in ("pilot", "final")) and "-b6" in line:
            print(line)
    rows = [l for l in proc.stdout.splitlines() if " pilot " in l or " final " in l]
    names = {p.name for p in paths.TASKS.glob("a_f*")}
    for l in rows:
        if l.split()[0] in names:
            print(l)
    return proc.returncode


# --------------------------------------------------------------------------- blind reader

READER = """You are a careful professional completing a work assignment. Your workspace is the folder
WS = {ws}
Work only inside WS.
1. Read the assignment in WS/{instr}. It names paths under /app/; on this machine /app/ means WS/app/ (so /app/environment/files is WS/app/environment/files and /app/deliverables is WS/app/deliverables).
2. The source files in WS/app/environment/files are read-only: read them; never change, move or delete them.
3. Write only the deliverable file(s) this assignment names, into WS/app/deliverables/, and leave nothing else there. Files already in that folder come from an earlier step; change them only if the assignment tells you to.
4. You may write and run helper scripts in WS/work/. Check every figure against the source documents.
5. Do not open anything outside WS, do not look for answer keys, graders, solutions or other copies of this task, do not use the network and do not start sub-agents.
When you are done, reply with the path of each file you wrote and one line on each decision you were unsure about."""


def _steps(task: Path) -> list[str]:
    return sorted(p.name for p in (task / "steps").iterdir() if (p / "instruction.md").is_file())


def _instr_name(steps: list[str], step: str) -> str:
    return "instruction.md" if len(steps) == 1 else f"instruction-{step}.md"


def _declared(task: Path) -> dict[str, list[str]]:
    p = task / "tests/outputs.json"
    out: dict[str, list[str]] = {}
    if p.is_file():
        for o in json.loads(p.read_text()).get("outputs", []):
            out.setdefault(o.get("step", "01-task"), []).append(o["file"])
    return out


def _hashes(root: Path) -> dict[str, str]:
    return {p.relative_to(root).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in sorted(root.rglob("*")) if p.is_file() and p.name != ".DS_Store" and "__pycache__" not in p.parts}


def blind_prep(task: Path, out: str | None, render=None) -> int:
    """render(ws, steps, step) -> reader prompt text; default READER."""
    out = out or os.environ.get("CLAUDE_SCRATCH")
    if not out:
        print("no output directory: pass --out DIR or set CLAUDE_SCRATCH (there is no /tmp default)")
        return 2
    parent = Path(out).expanduser().resolve()
    if not parent.is_dir():
        print(f"--out {parent} is not an existing directory")
        return 2
    files, steps = task / "environment/files", _steps(task)
    if not files.is_dir() or not steps:
        print(f"{task} has no environment/files or no steps/*/instruction.md")
        return 2
    ws = Path(tempfile.mkdtemp(prefix=f"blind-{base_name(task)}-{version(task)}-", dir=parent))
    app = ws / "app"
    shutil.copytree(files, app / "environment/files", ignore=shutil.ignore_patterns(".DS_Store", "__pycache__"))
    (app / "deliverables").mkdir()
    (ws / "work").mkdir()
    for st in steps:
        shutil.copyfile(task / "steps" / st / "instruction.md", ws / _instr_name(steps, st))
    (ws / ".prep.json").write_text(json.dumps({"task": base_name(task), "version": version(task), "tree": str(task),
                                               "identity": _identity(task), "steps": steps}, indent=1) + "\n")
    for p in sorted((app / "environment").rglob("*"), key=lambda p: len(p.parts), reverse=True):
        p.chmod(0o555 if p.is_dir() else 0o444)
    _write_rec("blind-prep", task, {"workspace": str(ws), "steps": steps})
    print(f"WORKSPACE {ws}")
    print(f"steps: {', '.join(steps)}" + ("" if len(steps) == 1 else
                                          "  (one FRESH reader per step, in this order, same workspace)"))
    for st in steps:
        print(f"\n----- reader prompt{'' if len(steps) == 1 else ' for step ' + st} -----")
        print(render(ws, steps, st) if render else READER.format(ws=ws, instr=_instr_name(steps, st)))
    print(f"\n----- then -----\npython3 -I {TOOLS / 'b6ctl.py'} blind-grade {task} {ws}")
    return 0


def blind_grade(task: Path, ws: Path) -> int:
    deliv = ws / "app/deliverables"
    if not deliv.is_dir():
        print(f"{ws} is not a blind-prep workspace (no app/deliverables)")
        return 2
    sys.path.insert(0, str(TOOLS))
    import design_lint as dl
    prep = json.loads((ws / ".prep.json").read_text()) if (ws / ".prep.json").is_file() else {}
    ident = _identity(task)
    if prep and prep.get("identity") != ident:
        print(f"WARN workspace was prepared from {prep.get('task')} {prep.get('version')} with other content than "
              f"{task} ({version(task)})")
    print("source files unchanged" if _hashes(ws / "app/environment/files") == _hashes(task / "environment/files")
          else "WARN the workspace's source files differ from the tree's environment/files")
    declared = _declared(task)
    every = {f for fs in declared.values() for f in fs}
    rels = [p.relative_to(deliv).as_posix() for p in deliv.rglob("*")]
    extra = [r for r in rels if r not in every and not any(f.startswith(r + "/") for f in every)]
    if every and extra:
        print(f"WARN undeclared entries in deliverables (the contract zeroes a step for these): {extra}")
    rc, results = 0, {}
    for st in _steps(task):
        want = declared.get(st)
        if want is not None and not any((deliv / f).exists() for f in want):
            print(f"{st}: not present (no {', '.join(want)}); not graded")
            results[st] = {"present": False}
            continue
        try:
            res = dl.grade(task, st, deliv)
        except Exception as exc:  # noqa: BLE001 - an ungraded step is reported as ERROR, never scored
            print(f"{st}: ERROR {str(exc)[:300]}")
            results[st] = {"error": str(exc)[:300]}
            rc = 1
            continue
        failed = sorted(res["failed"])
        results[st] = {"reward": float(res["reward"]), "failed": failed}
        print(f"{st}: reward {float(res['reward']):.4f}  failed {len(failed)}: {', '.join(failed) or '-'}")
    _write_rec("blind", task, {"identity": ident, "workspace": str(ws), "steps": results})
    return rc


# --------------------------------------------------------------------------- run: launch, wait, voids once, gate, census

FULL = 0.9999
NEED = {"pilot": 5, "final": 10}  # valid runs per model
RUN_EVERY = 180                   # seconds between status passes while `run` waits
CENSUS = TOOLS / "census_answers.py"
ME = f"python3 -I {shlex.quote(str(TOOLS / 'b6ctl.py'))}"
MEP = f"env -u ANTHROPIC_AUTH_TOKEN {ME}"  # for commands that touch a pool


def _q(p) -> str:
    return shlex.quote(str(p))


def _left(deadline: float) -> int:
    return max(0, int(deadline - time.time()))


def stage_verdict(e: dict) -> tuple[str, str]:
    """measure.py's verdict column for one ledger entry, as (verdict, figures): PILOT HARD, FINAL HARD, near, easy,
    controls fail, or VOID (a model not done, or fewer valid runs than the stage needs)."""
    runs, stage = e.get("runs", {}), e.get("stage", "final")
    f, a = runs.get("fable") or {}, runs.get("astra") or {}
    if f.get("state") != "done" or a.get("state") != "done":
        return "VOID", f"fable {f.get('state', '-')}, astra {a.get('state', '-')}"
    need = NEED.get(stage, 10)
    if f.get("valid", 0) < need or a.get("valid", 0) < need:
        return "VOID", f"valid runs fable {f.get('valid', 0)}/{need}, astra {a.get('valid', 0)}/{need}"
    pf, pa = f.get("pass_at_1") or 0.0, a.get("pass_at_1") or 0.0
    figs = (f"fable {f.get('full')}/{f.get('valid')} pass@1 {pf:.2f}, "
            f"astra {a.get('full')}/{a.get('valid')} pass@1 {pa:.2f}")
    if pf <= 0.5 and pa <= 0.5:
        if stage != "pilot":
            return "FINAL HARD", figs
        o, n = runs.get("oracle") or {}, runs.get("nop") or {}
        if o and not ((o.get("mean_reward") or 0) >= FULL and (n.get("mean_reward") or 0) < 0.5):
            return "controls fail", (f"{figs}; oracle {(o.get('mean_reward') or 0):.2f}, "
                                     f"nop {(n.get('mean_reward') or 0):.2f}")
        return "PILOT HARD", figs
    if stage == "pilot" and pf <= 0.6 and pa <= 0.6:
        return "near", figs
    return "easy", figs


def next_after(verdict: str, task: Path, stage: str) -> tuple[str | None, list[str]]:
    """(STOP text, next commands) after a measured verdict (README-FLOW steps 7 and 10)."""
    T = _q(task)
    if verdict == "PILOT HARD":
        return None, [f"{MEP} run {T} final"]
    if verdict == "FINAL HARD":
        return ("FINAL HARD with a clean census goes to the blind reader, then the §14 audit",
                [f'{ME} prompt blind {T} --out "$CLAUDE_SCRATCH"'])
    if verdict == "near":
        return ("near: harden. The author bumps the version (one dial notch) and the task returns to author-check",
                [f"{ME} prompt tune {T}"])
    if verdict == "easy":
        return ("easy: " + ("tune or retire (a human call)" if stage == "pilot"
                            else "anything but FINAL HARD is a human call (tune or retire)"), [f"{ME} prompt tune {T}"])
    if verdict == "controls fail":
        return "the oracle/nop controls fail: a grader or reference defect; back to the author", \
            [f"{ME} prompt author {T}"]
    return ("infrastructure loss: a run already re-run once, or one rerun-void cannot repair, is a human call",
            [f"{MEP} run {T} {stage}"])


def census(task: Path, stage: str, dirs: list[Path]) -> dict:
    """census_answers --deep over the dirs. A full-reward step whose answer differs from the reference is a grader
    defect; no rows or a crash is an ERROR, never clean. Writes STATE/census/<name>-<version>-<stage>.{txt,json}."""
    tmp = tempfile.mkdtemp(prefix="b6-census-")  # census_answers leaves its reference outputs in TMPDIR
    try:
        proc = subprocess.run(["python3", "-I", str(CENSUS), "--deep", str(task), *map(str, dirs)],
                              capture_output=True, text=True,
                              env={**{k: v for k, v in os.environ.items() if k != "ANTHROPIC_AUTH_TOKEN"}, "TMPDIR": tmp})
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    rows, defects = 0, []
    for line in proc.stdout.splitlines():
        m = re.search(r" reward=(\S+) diff_fields=(.*)$", line)
        if not m:
            continue
        rows += 1
        print("  " + line.strip()[:220])
        try:
            full = float(m.group(1)) >= FULL
        except ValueError:  # reward=None: that step has no verifier output
            continue
        if full and m.group(2).strip() != "none":
            defects.append(line.strip())
    log = _rec_path("census", task, f"-{stage}.txt")
    log.parent.mkdir(parents=True, exist_ok=True)
    log.write_text(proc.stdout + proc.stderr)
    res = {"stage": stage, "rc": proc.returncode, "rows": rows, "defects": defects,
           "dirs": [str(d) for d in dirs], "log": str(log)}
    if proc.returncode or not rows:
        tail = proc.stderr.strip().splitlines()
        res["error"] = (tail[-1] if tail else f"no episode rows (exit {proc.returncode})")[:300]
    _write_rec("census", task, res, f"-{stage}.json")
    return res


def _gate_verdict(task: Path, stage: str) -> str | None:
    """signal_gate's verdict (IN_BAND, FLAT, TOO_EASY, FLAG) from STATE/gates, or None when it has not run."""
    g = paths.GATES / f"{base_name(task)}-{version(task)}-{stage}.json"
    try:
        return json.loads(g.read_text()).get("verdict") if g.is_file() else None
    except ValueError:
        return None


def _census_text(c: dict | None) -> str:
    if not c:
        return "census not run"
    if c.get("error"):
        return f"census ERROR ({c['error']})"
    if c["defects"]:
        return f"census DEFECT: {len(c['defects'])} full-reward step(s) differ from the reference"
    return f"census clean ({c['rows']} rows)"


def _rerun_voids_once(task: Path, stage: str, deadline: float, head: str) -> int:
    """After wait exit 3: re-run each void-auth model ONCE (a scored run never), then wait again."""
    e = campaign(task, stage)
    states = {m: (e["runs"].get(m) or {}).get("state") for m in MODELS}
    voids = [m for m in MODELS if states[m] != "done"]
    again = [m for m in voids if any(m in h for h in e.get("void_history") or [])]
    other = [m for m in voids if states[m] != "void-auth"]
    launched = Path(e["task"]) if (Path(e.get("task") or "/nonexistent") / "task.toml").is_file() else task
    if again or other:
        for m in again:
            print(f"{m} is void again after its one re-run")
        for m in other:
            print(f"{m} is {states[m]}: rerun-void re-runs void-auth runs only")
        print(f"{head}: VOID unresolved\nSTOP    a human decides ({MEP} rerun-void {_q(launched)} {stage} <model> "
              f"re-runs a void-auth run)")
        return 3
    for m in voids:
        print(f"== re-run void {m} (once)", flush=True)
        rc = rerun_void(launched, stage, m)
        if rc:
            print(f"{head}: VOID unresolved (rerun-void {m} exit {rc})")
            return 3
    print("== wait (after the re-run)", flush=True)
    rc = wait(task, stage, "both", RUN_EVERY, _left(deadline))
    if rc == 3:
        print(f"{head}: VOID unresolved after one re-run\nSTOP    a human decides")
    return rc


def run_stage(task: Path, stage: str, ws: str | None, max_min: float) -> int:
    name, ver, T = base_name(task), version(task), _q(task)
    deadline, head = time.time() + max_min * 60, f"VERDICT {name} {ver} {stage}"
    print(f"== run {name} {ver} {stage}", flush=True)
    e = campaign(task, stage)
    if e is None:
        if stage == "final" and campaign(task, "pilot") is None:
            print(f"REFUSED: {name} {ver} has no pilot; the final runs only after a pilot of the same version\n"
                  f"NEXT    {MEP} run {T} pilot")
            return 2
        print("== launch (key preflight first)", flush=True)
        rc = launch(task, stage, ws)
        if rc:
            print(f"{head}: NOT LAUNCHED (exit {rc}); nothing was measured")
            return 3 if rc == 3 else 1
        if campaign(task, stage) is None:
            print(f"{head}: NOT LAUNCHED (no {stage} entry in the ledger after the launch)")
            return 1
    else:
        print(f"{stage} campaign {e.get('id')} is already in the ledger: resuming (a scored run is never re-run)")
    print("== wait", flush=True)
    rc = wait(task, stage, "both", RUN_EVERY, _left(deadline))
    if rc == 3:
        rc = _rerun_voids_once(task, stage, deadline, head)
    if rc == 124:
        print(f"{head}: TIMEOUT after --max {max_min:g} min; nothing is lost\nNEXT    {MEP} run {T} {stage}"
              f"   (resumes the wait)")
        return 124
    if rc:
        return rc
    verdict, figs = stage_verdict(campaign(task, stage))
    if verdict == "VOID":
        print(f"{head}: VOID ({figs})\nSTOP    infrastructure loss that rerun-void cannot repair (it re-runs void-auth "
              f"runs only): a human decides")
        return 3
    print("== gate", flush=True)
    if gate(task, stage) == 2:
        print(f"{head}: VOID (campaign output missing here; measure.py status pulls it back)\n"
              f"NEXT    {MEP} run {T} {stage}")
        return 3
    print("== census", flush=True)
    c = census(task, stage, [d for ds in stage_dirs(task, stage, quiet=True).values() for d in ds])
    print(f"{head}: {verdict} ({figs}); signal gate {_gate_verdict(task, stage) or '?'}; {_census_text(c)}")
    if c.get("error") or c["defects"]:
        print(f"STOP    a census that is not clean blocks the task: a full-reward run that differs from the reference "
              f"is a grader defect (log {c['log']}); back to the author\n"
              f"NEXT    {ME} prompt author {T} --notes {_q(c['log'])}")
        return 1
    stop, cmds = next_after(verdict, task, stage)
    if stop:
        print(f"STOP    {stop}")
    for cmd in cmds:
        print(f"NEXT    {cmd}")
    return 0 if verdict in ("PILOT HARD", "FINAL HARD") else 1


# --------------------------------------------------------------------------- next: where a task stands

STOPS = {  # README-FLOW's STOP decisions, per stage (printed after "STOP")
    "author-check": "unless READY: the author fixes every listed item (each comes with its fix)",
    "pilot": "unless PILOT HARD with a clean census: near -> harden (new version, back to author-check); "
             "easy -> tune or retire",
    "final": "unless FINAL HARD (pass@1 <= 0.5 on both) with a mix and a clean census; anything else is a human call",
    "blind": "unless the reader reaches the reference, or the audit shows each miss to be the reader's",
    "audit": "SHIP or SHIP-WITH-DISCLOSURE goes to packaging; WITHHOLD goes back to the author",
    "ship": "if the harbor receipt fails (a human decides) or the assembler refuses (<name>.zip.invalid)",
    "done": "uploading to Drive or the tracking sheet needs the user's go-ahead",
}


def _tc_runs() -> dict:
    try:
        return json.loads(paths.TC_RUNS.read_text()) if paths.TC_RUNS.is_file() else {}
    except ValueError:
        return {}


def _receipt(tree: Path) -> str | None:
    """The installed harbor receipt's status if it is bound to this tree's identity, else None."""
    p = tree / "verification/harbor-tasks-check.json"
    try:
        rec = json.loads(p.read_text()) if p.is_file() else None
    except ValueError:
        return None
    if not rec or rec.get("artifact_sha256") != _identity(tree):
        return None
    return str(rec.get("status") or rec.get("verdict") or rec.get("ok"))


def _blind_text(b: dict) -> str:
    def one(r):
        if r.get("present") is False:
            return "not present"
        if "error" in r:
            return "ERROR"
        return f"reward {r['reward']:.4f}" + (f" failed {','.join(r['failed'])}" if r["failed"] else "")
    return "; ".join(f"{s} {one(r)}" for s, r in (b.get("steps") or {}).items()) or "no steps graded"


def plan(task: Path) -> dict:
    """The task's state rows, its current stage, that stage's STOP text and the exact next command(s)."""
    name, ver, T = base_name(task), version(task), _q(task)
    archived = "_versions" in task.parts
    ident = _identity(task)
    rows: list[tuple[str, str]] = []
    res: dict = {"stage": None, "stop": None, "cmds": [], "rows": rows}

    def at(stage: str, cmds: list[str], stop: str | None = None) -> None:
        if res["stage"] is None:
            res.update(stage=stage, cmds=cmds, stop=stop or STOPS.get(stage))

    ac = _read_rec("author-check", task)
    if archived:
        rows.append(("author-check", "n/a (archived tree)"))
    elif not ac:
        rows.append(("author-check", "not run"))
        at("author-check", [f"{ME} author-check {T}"])
    elif ident is None or ac.get("identity") != ident:
        rows.append(("author-check", f"{ac.get('verdict')} at {ac.get('at')}, but the tree has changed since"))
        at("author-check", [f"{ME} author-check {T}"])
    elif ac.get("verdict") != "READY":
        rows.append(("author-check", f"NOT READY ({len(ac.get('items') or [])} items) at {ac.get('at')}"))
        at("author-check", [f"{ME} prompt author {T} --notes {_q(_rec_path('author-check', task, '.notes.md'))}",
                            f"{ME} author-check {T}"])
    else:
        rows.append(("author-check", f"READY at {ac.get('at')}"))

    for stage in ("pilot", "final"):
        e = campaign(task, stage)
        if e is None:
            rows.append((stage, "not launched"))
            at(stage, [f"{MEP} run {T} {stage} [<your pool>]"])
            continue
        if not all((r or {}).get("state") in TERMINAL for r in e["runs"].values()):
            rows.append((stage, status_line(e) + "  (running)"))
            at(stage, [f"{MEP} run {T} {stage}   # resumes the wait"])
            continue
        verdict, figs = stage_verdict(e)
        gate_v = _gate_verdict(task, stage)
        c = _read_rec("census", task, f"-{stage}.json")
        rows.append((stage, f"{status_line(e)} -> {verdict}"))
        rows.append((f"{stage} checks", f"signal gate {gate_v or 'not run'}; {_census_text(c)}"))
        if verdict == "VOID":
            stop, cmds = next_after("VOID", task, stage)
            at(stage, [f"{MEP} run {T} {stage}   # re-runs a void-auth run once"], stop)
        elif gate_v is None or c is None:
            at(stage, [f"{MEP} run {T} {stage}   # gate + census on the finished campaign"])
        elif c.get("error") or c["defects"]:
            at(stage, [f"{ME} prompt author {T} --notes {_q(c['log'])}"],
               "the census is not clean (a full-reward run differs from the reference: a grader defect); back to "
               "the author")
        elif verdict not in ("PILOT HARD", "FINAL HARD"):
            stop, cmds = next_after(verdict, task, stage)
            at(stage, cmds, stop)

    bp, bg = _read_rec("blind-prep", task), _read_rec("blind", task)
    if bg and bg.get("identity") == ident:
        steps = bg.get("steps") or {}
        reached = bool(steps) and all((r.get("reward") or 0) >= FULL for r in steps.values())
        rows.append(("blind reader", _blind_text(bg) + ("" if reached else "  (misses: the audit must show each "
                                                                           "is the reader's)")))
        if any(r.get("present") is False for r in steps.values()):
            at("blind", [f"{ME} blind-grade {T} {_q(bg.get('workspace'))}   # after the next fresh reader's step"],
               "a step is not delivered yet: run the next step's fresh reader on the same workspace, then grade")
    elif bp:
        rows.append(("blind reader", f"prepared {bp.get('workspace')}, not graded"))
        at("blind", [f"{ME} blind-grade {T} {_q(bp.get('workspace'))}"])
    else:
        rows.append(("blind reader", "-"))
        at("blind", [f'{ME} prompt blind {T} --out "$CLAUDE_SCRATCH"', f"{ME} blind-grade {T} <WORKSPACE>"])

    rep = paths.STATE / "audits" / f"{name}-{ver}.md"
    if rep.is_file():
        dec, why = audit_verdict(rep, task)
        rows.append(("audit", f"{dec or 'no usable VERDICT line'} ({rep})"))
        if dec is None:
            at("audit", [f"{ME} prompt audit {T}"], f"the audit report has no usable VERDICT line: {why}")
        elif dec == "WITHHOLD":
            at("audit", [f"{ME} prompt author {T} --notes {_q(rep)}"],
               "WITHHOLD: back to the author for a new version")
    else:
        rows.append(("audit", "-"))
        at("audit", [f"{ME} prompt audit {T}   # the auditor writes {rep}"])

    frozen = task if archived else paths.TASKS / "_versions" / f"{name}-{ver}"
    status = _receipt(frozen) if frozen.is_dir() else None
    tc = _tc_runs().get(str(frozen.resolve()))
    shipped = _read_rec("ship", task)
    zips = [z for z in (shipped or {}).get("zips") or [] if Path(z).is_file()]
    rows.append(("frozen", str(frozen) if frozen.is_dir() else "-"))
    rows.append(("harbor", f"receipt {status}" if status else
                 f"run {tc.get('run')} on {tc.get('ws')}, no receipt installed" if tc else "-"))
    rows.append(("zips", ", ".join(zips) or "-"))
    ship_cmd = (f"{MEP} ship {T} --audit {_q(rep)}" if not archived else
                "archived tree: ship its live tree, or package by hand (README-FLOW steps 15-16)")
    if zips and status == "pass":  # shipped: nothing earlier is still open
        res.update(stage="done", stop=STOPS["done"],
                   cmds=[f"ls -la {_q(Path(zips[0]).parent)}", f"python3 -I {_q(TOOLS / 'ledsum.py')} --grep {name}",
                         f"python3 -I {_q(TOOLS / 'batch_diversity.py')} {_q(frozen)} <the batch's other shipped trees>",
                         "append the verdict line to production/state/genuineness.md"])
    elif status not in (None, "pass"):
        at("ship", [ship_cmd], f"the harbor receipt is {status}: a human decides")
    else:
        at("ship", [ship_cmd])
    return res


def next_step(task: Path) -> int:
    p = plan(task)
    print(f"{base_name(task)} {version(task)}  ({task})")
    for k, v in p["rows"]:
        print(f"  {k:14} {v}")
    print(f"STAGE   {p['stage']}")
    if p["stop"]:
        print(f"STOP    {p['stop']}")
    for cmd in p["cmds"]:
        print(f"NEXT    {cmd}")
    return 0


# --------------------------------------------------------------------------- new: scaffold a task from the skeleton

SKELETON = paths.PRODUCTION / "templates/skeleton"
SLUG = re.compile(r"[a-z0-9]+(?:-[a-z0-9]+)*")
TRAPS_STUB = {"schema": B8_SCHEMA, "premises": [], "coverage_checks": [], "leak_allow": []}


def new_task(slug: str, level: str, seed: str | None, plan_file: str | None) -> int:
    if not SLUG.fullmatch(slug):
        print(f"bad slug {slug!r}: lower-case words joined by '-', e.g. supplier-credit-review")
        return 2
    if seed is not None and not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]*", seed):
        print(f"bad --seed {seed!r}: give the session id, e.g. 01a05ff6-41dc-7dd3-a31d-5d0954aa41e5")
        return 2
    if plan_file and not Path(plan_file).is_file():
        print(f"--plan {plan_file} is not a file")
        return 2
    name = f"a_{level}_{slug}"
    dest = paths.TASKS / name
    if dest.exists() or dest.is_symlink():
        print(f"REFUSED: {dest} exists (a retune is a new version of that tree: prompt tune)")
        return 3
    taken = glob.glob(str(paths.TASKS / "_versions" / f"{name}-*")) or [e for e in _ledger() if e.get("name") == name]
    if taken:
        print(f"REFUSED: the name {name} is already taken (archived versions or ledger entries); pick another slug")
        return 3
    paths.TASKS.mkdir(parents=True, exist_ok=True)
    shutil.copytree(SKELETON, dest, ignore=shutil.ignore_patterns("__pycache__", ".DS_Store"))
    toml = dest / "task.toml"
    text = toml.read_text()
    text = re.sub(r'(?m)^name = "arena/[^"]*"', f'name = "arena/{name}"', text, count=1)
    text = re.sub(r'(?m)^version = "[^"]*"', 'version = "1.0.0"', text, count=1)
    text = re.sub(r'(?m)^faithfulness = "[^"]*"', f'faithfulness = "{level.upper()}"', text, count=1)
    if seed:
        text = re.sub(r'(?m)^source_trace = "[^"]*"', f'source_trace = "{seed}"', text, count=1)
        text = re.sub(r'(?m)^source_seeds = \[.*\]$', f'source_seeds = ["{seed}::<seed index>"]', text, count=1)
    toml.write_text(text)
    meta = tomllib.loads(text)
    assert meta["task"]["name"] == f"arena/{name}" and meta["task"]["version"] == "1.0.0", "skeleton task.toml changed"
    (dest / "authoring").mkdir(exist_ok=True)
    (dest / "authoring/traps.json").write_text(json.dumps(TRAPS_STUB, indent=1) + "\n")
    if plan_file:
        shutil.copyfile(plan_file, dest / "authoring/PLAN.md")
    (dest / "provenance").mkdir(exist_ok=True)
    (dest / "provenance/ledger.json").write_text(json.dumps({
        "schema": "arena/provenance-ledger/1", "source_trace": seed or "<full session uuid of the seed trace>",
        "carried_session_files": [], "note": "<what of the session is carried, lifted or fictionalised>"},
        indent=2, ensure_ascii=False) + "\n")
    print(f"NEW     {dest}\n        {name} 1.0.0, faithfulness {level.upper()}, seed {seed or 'not set'}, "
          f"plan {'authoring/PLAN.md' if plan_file else 'none'}")
    print(f"NEXT    {ME} prompt author {_q(dest)}")
    return 0


# --------------------------------------------------------------------------- prompt: ready-to-paste agent prompts

PROMPTS = paths.PRODUCTION / "prompts"
BUILTIN_PROMPTS = {
    "author": """You author ONE task for the production line in the repo {REPO}.
Task tree: {TASK_DIR} (task {TASK}, version {VERSION}), scaffolded from production/templates/skeleton.
Read production/briefs/AUTHOR-BRIEF-B8.md first: it is authoritative. Trap modes: production/traps/TRAP-LIBRARY.md.

Plan brief:
{PLAN}

Notes:
{NOTES}

Scratch: make your own `mktemp -d` under {SCRATCH}; never glob /tmp. Run python as python3.11 -I -B.
Your gate: python3 -I production/tools/b6ctl.py author-check {TASK_DIR}
Hand back (<= 20 lines, brief §12) only on READY; if out of time, hand back the NOT READY list verbatim.
Never touch pipeline/, other tasks, _versions/, the Coder pools, keys.env, or any arena / harbor / benchmark / coder /
measure command. No sub-agents. No attribution lines.""",
    "tune": """You retune ONE task of the production line in the repo {REPO}: {TASK_DIR} (task {TASK}, measured
version {VERSION}). First bump task.toml [task] version (one dial notch per version); never edit _versions/.
Follow production/briefs/AUTHOR-BRIEF-B8.md (§6.8 dials) and production/traps/TRAP-LIBRARY.md.

Measurements of {VERSION}:
{CAMPAIGNS}

Notes:
{NOTES}

Scratch: make your own `mktemp -d` under {SCRATCH}; never glob /tmp. Run python as python3.11 -I -B.
Your gate: python3 -I production/tools/b6ctl.py author-check {TASK_DIR}
Hand back the new version, each dial you moved and why, and the author-check verdict line.
Never touch pipeline/, other tasks, _versions/, the Coder pools, keys.env, or any arena / harbor / benchmark / coder /
measure command. No sub-agents. No attribution lines.""",
    "audit": """You are an independent §14 auditor of ONE task in the repo {REPO}: {TASK} {VERSION} at {TASK_DIR}.
Follow production/briefs/AUDIT-BRIEF-B6.md, with the ambiguity bar of production/briefs/REAUDIT-BRIEF-B7.md.

Campaigns, gate reports, census logs and the blind reader's result:
{CAMPAIGNS}

Notes:
{NOTES}

Scratch: make your own `mktemp -d` under {SCRATCH}; never glob /tmp.
Write your report to {AUDIT_REPORT}. Its last line must be exactly one of:
VERDICT {TASK} {VERSION}: SHIP
VERDICT {TASK} {VERSION}: SHIP-WITH-DISCLOSURE
VERDICT {TASK} {VERSION}: WITHHOLD
(disclosures, or the defect with its location and minimal fix, go above that line).
No pipeline / pool / arena / harbor / benchmark / coder commands; never read keys.env; the only sub-agent allowed is
one blind reader. No attribution lines.""",
}


def _fill(text: str, values: dict[str, str]) -> str:
    """Replace {KEY} placeholders in one pass; unknown ones stay as they are."""
    return re.sub(r"\{([A-Z_]+)\}", lambda m: values.get(m.group(1), m.group(0)), text)


def _campaign_listing(task: Path) -> str:
    name, ver, lines = base_name(task), version(task), []
    for stage in ("pilot", "final"):
        e, void = campaign(task, stage), void_dirs(task, stage)
        if e:
            done = all((r or {}).get("state") in TERMINAL for r in e["runs"].values())
            lines.append(f"{stage} ledger: {status_line(e)} -> {stage_verdict(e)[0] if done else 'running'}")
        for d in sorted(glob.glob(str(paths.ARTIFACTS / f"{name}-{ver}-{stage}-*"))):
            tag = (" (void: infrastructure loss, excluded)" if os.path.realpath(d) in void
                   else "" if (Path(d) / "report.json").is_file() else " (no report.json yet)")
            lines.append(f"{stage} campaign: {d}{tag}")
        for label, p in (("gate report", paths.GATES / f"{name}-{ver}-{stage}.json"),
                         ("census log", _rec_path("census", task, f"-{stage}.txt"))):
            if p.is_file():
                lines.append(f"{stage} {label}: {p}")
    b = _read_rec("blind", task)
    if b:
        lines.append(f"blind reader ({b.get('workspace')}): {_blind_text(b)}")
    return "\n".join(lines) or "(no campaigns of this version yet)"


def _prompt_values(task: Path, notes: str | None, scratch: str | None) -> dict[str, str]:
    scratch = scratch or os.environ.get("CLAUDE_SCRATCH")
    plan_md = task / "authoring/PLAN.md"
    return {"TASK_DIR": str(task), "TASK": base_name(task), "VERSION": version(task), "REPO": str(ROOT),
            "SCRATCH": str(Path(scratch).expanduser().resolve()) if scratch else
            "(no scratch directory given: pass --out DIR or set CLAUDE_SCRATCH)",
            "NOTES": Path(notes).read_text().strip() if notes else "(none)",
            "PLAN": plan_md.read_text().strip() if plan_md.is_file() else "(no plan: authoring/PLAN.md is missing)",
            "AUDIT_REPORT": str(paths.STATE / "audits" / f"{base_name(task)}-{version(task)}.md"),
            "CAMPAIGNS": _campaign_listing(task)}


def prompt(kind: str, task: Path, notes: str | None, out: str | None) -> int:
    """The prompt on stdout; notes about the template on stderr, so `> file` keeps only the prompt."""
    if notes and not Path(notes).is_file():
        print(f"--notes {notes} is not a file")
        return 2
    src = PROMPTS / f"{kind}.md"
    tpl = src.read_text() if src.is_file() else None
    if tpl is None:
        print(f"NOTE {src} not found: using the built-in minimal {kind} prompt", file=sys.stderr)
    if kind == "blind":
        def render(ws: Path, steps: list[str], st: str) -> str:
            if tpl is None:
                return READER.format(ws=ws, instr=_instr_name(steps, st))
            return _fill(tpl, {**_prompt_values(task, notes, str(ws)), "WORKSPACE": str(ws),
                               "INSTRUCTION": _instr_name(steps, st), "STEP": st}).rstrip()
        return blind_prep(task, out, render)
    if kind == "audit":
        (paths.STATE / "audits").mkdir(parents=True, exist_ok=True)
    print(_fill(tpl or BUILTIN_PROMPTS[kind], _prompt_values(task, notes, out)).rstrip())
    return 0


# --------------------------------------------------------------------------- doctor

CODER_NOISE = ("version mismatch", "download v2")    # advice the Coder CLI prints (coder._NOISE)


def _py_version(exe: str | None) -> str | None:
    if not exe:
        return None
    try:
        p = subprocess.run([exe, "-I", "-c", "import sys; print('%d.%d.%d' % sys.version_info[:3])"],
                           capture_output=True, text=True, timeout=60)
    except (OSError, subprocess.TimeoutExpired):
        return None
    return p.stdout.strip() if p.returncode == 0 else None


def _coder_bin() -> str | None:
    return os.environ.get("ARENA_CODER_BIN") or shutil.which("coder")


def _coder(*args: str) -> subprocess.CompletedProcess:
    """A read-only Coder CLI call (whoami, list). Nothing here starts, stops, prepares or ssh-es into a pool."""
    return subprocess.run([_coder_bin(), *args], capture_output=True, text=True, timeout=120)


def _dump() -> tuple[Path, int]:
    """The configured trace dump (pipeline.config.dump_root: $ARENA_DUMP, else workspace.toml) and its session count.
    Raises SystemExit with the pipeline's own reason when none is configured."""
    _pipeline()
    from pipeline.config import dump_root
    root = dump_root()
    return root, sum(1 for d in (root / "sessions").iterdir() if d.is_dir())


def _code_shas() -> tuple[str, str]:
    """(pipeline sha, code sha): what a pool records in .arena-pipeline-sha and .arena-code-sha."""
    _pipeline()
    from pipeline.benchmark import coder, coder_run
    return coder._tree_sha(coder.SYNC_PATHS), coder._tree_sha(coder_run.CODE_PATHS)


def doctor() -> int:
    fails = 0

    def say(ok: bool | None, what: str, fix: str = "") -> None:
        nonlocal fails
        fails += ok is False
        tag = "OK" if ok else "WARN" if ok is None else "FAIL"
        print(f"{tag:4} {what}" + (f" -- fix: {fix}" if fix and ok is not True else ""), flush=True)

    shell = os.environ.get("SHELL", "")
    say(None if shell.endswith("zsh") else True, f"login shell {shell or '(unset)'}",
        "use bash -c '<command>' for every flow command (zsh does not word-split)")
    token = "ANTHROPIC_AUTH_TOKEN" in os.environ
    say(not token, "ANTHROPIC_AUTH_TOKEN is set in this environment" if token else "ANTHROPIC_AUTH_TOKEN not set",
        "launch with env -u ANTHROPIC_AUTH_TOKEN (an inherited session token beats keys.env)")
    if not KEYS.is_file():
        say(False, f"keys.env missing ({KEYS})", "./arena keys (prompts; writes keys.env at mode 600)")
    else:
        mode = stat.S_IMODE(KEYS.stat().st_mode)
        say(mode == 0o600, f"keys.env mode {mode:o}", f"chmod 600 {_q(KEYS)}")
        buf = io.StringIO()
        try:
            with contextlib.redirect_stdout(buf):
                good = preflight()
            codes = ", ".join(buf.getvalue().split("\n")[:-1]) or "no key lines"
        except Exception as exc:  # noqa: BLE001 - reported as a FAIL line
            good, codes = False, f"preflight error {type(exc).__name__}"
        say(good, f"key preflight {codes}", "a human fixes keys.env (./arena keys); never paste or print a key")
    v = _py_version(paths.PY) if Path(paths.PY).is_file() else None
    say(v is not None, f".venv python {v}" if v else f".venv python missing ({paths.PY})", "uv sync (repo root)")
    v311 = _py_version(PY)
    good = bool(v311 and v311.startswith("3.11."))
    say(good, f"verifier python {v311} ({PY})" if good else f"verifier python3.11 not found ({PY}: {v311 or 'none'})",
        "uv python install 3.11 (or set ARENA_PY311=/path/to/python3.11)")
    try:
        if str(paths.TRAPS) not in sys.path:
            sys.path.insert(0, str(paths.TRAPS))
        import traplib
        say(True, f"trap library {len(traplib.load(paths.LIBRARY).modes)} modes ({paths.LIBRARY})")
    except Exception as exc:  # noqa: BLE001
        say(False, f"trap library {paths.LIBRARY}: {str(exc)[:160]}", "python3 -I production/traps/traplib.py build")
    try:
        root, n = _dump()
        say(True, f"dump {root} ({n} sessions)")
    except (SystemExit, Exception) as exc:  # noqa: BLE001 - dump_root raises SystemExit with its reason
        say(False, f"dump: {(str(exc).strip().splitlines() or ['not configured'])[0]}", "./arena dump --set <path>")
    pools = [p.strip() for p in os.environ.get("ARENA_POOLS", "").split(",") if p.strip()]
    if not pools:
        say(False, "ARENA_POOLS is not set", "export ARENA_POOLS=<your Coder workspace>[,<ws>...]: your OWN pools; a pool "
                                             "another checkout uses refuses your campaigns (it holds one code hash)")
    if not _coder_bin():
        say(False, "Coder CLI not found", "install it (https://coder.com/docs/install/cli), then ./arena coder login")
    else:
        try:
            who = _coder("whoami")
            if who.returncode or "authenticated" not in (who.stdout + who.stderr).lower():
                say(False, "Coder CLI is not logged in", "./arena coder login")
            else:
                lst = _coder("list", "-o", "json")
                body = "\n".join(l for l in lst.stdout.splitlines() if not any(n in l.lower() for n in CODER_NOISE))
                if lst.returncode:
                    raise ValueError(f"coder list exit {lst.returncode}")
                status = {r.get("name"): (r.get("latest_build") or {}).get("status") for r in json.loads(body or "[]")}
                running = 0
                for ws in pools:
                    st = status.get(ws)
                    if st == "running":
                        running += 1
                        say(True, f"pool {ws} running")
                    elif st is None:
                        say(False, f"pool {ws} not in `coder list`", "check the name ($ARENA_POOLS)")
                    else:
                        say(None, f"pool {ws} is {st}", "starting a pool needs the user's go-ahead; never start, "
                                                        "prepare or stop one from here")
                if pools and not running:
                    say(False, "no pool is running", "ask the user before any pool is started")
        except (OSError, ValueError, subprocess.TimeoutExpired) as exc:
            say(False, f"Coder CLI call failed: {str(exc)[:160]}", "check the network, then ./arena coder login")
    try:
        ps, cs = _code_shas()
        say(True, f"pipeline code sha {ps} (a pool's .arena-pipeline-sha; .arena-code-sha {cs[:16]})")
    except Exception as exc:  # noqa: BLE001
        say(False, f"cannot hash pipeline/: {str(exc)[:160]}", "run from a full checkout (or set ARENA_ROOT)")
    print(f"DOCTOR: {'no FAIL' if not fails else f'{fails} FAIL'}")
    return 0 if not fails else 1


# --------------------------------------------------------------------------- ship: freeze, harbor, zip

SHIP_POLL = 120  # seconds between tc_path pulls
DECISION = re.compile(r"\b(SHIP-WITH-DISCLOSURE|WITHHOLD|SHIP)\b")


def audit_verdict(report: Path, task: Path) -> tuple[str | None, str]:
    """(SHIP | SHIP-WITH-DISCLOSURE | WITHHOLD | None, why) from the report's LAST `VERDICT` line. The line counts for
    this task only if it names it and its version, or the report is <name>-<version>.md, or its first line names both;
    a line naming another task or version never counts."""
    name, ver = base_name(task), version(task)
    text = report.read_text(errors="replace")
    lines = [l.strip() for l in text.splitlines() if re.match(r"[\s>*#_`-]*VERDICT\b", l)]
    if not lines:
        return None, f"{report.name} has no VERDICT line (want `VERDICT {name} {ver}: SHIP|SHIP-WITH-DISCLOSURE|WITHHOLD`)"
    line = lines[-1]
    m = DECISION.search(line)
    if not m:
        return None, f"the last VERDICT line names no decision: {line[:160]}"
    before = line[:m.start()]
    vers = set(re.findall(r"\b\d+\.\d+\.\d+\b", before))
    names = set(re.findall(r"\ba_f\d_[a-z0-9-]*?[a-z0-9](?=-\d+\.\d+\.\d+|[^a-z0-9-]|$)", before))
    if vers - {ver} or names - {name}:
        return None, f"the last VERDICT line names {', '.join(sorted((names - {name}) | (vers - {ver})))}, not {name} {ver}"
    first = next((l for l in text.splitlines() if l.strip()), "")
    if not ((name in line and ver in line) or report.stem == f"{name}-{ver}" or (name in first and ver in first)):
        return None, f"cannot tell that {report.name} audits {name} {ver}: name both in the VERDICT line"
    return m.group(1), line


def _valid_runs(d: Path) -> int:
    try:
        return sum(1 for t in json.loads((d / "report.json").read_text()).get("trials") or [] if t.get("valid") is True)
    except (OSError, ValueError):
        return -1


def final_dirs(task: Path) -> tuple[dict[str, Path], list[str]]:
    """Per model, the ONE final campaign to package: not void in the ledger, 10 valid runs in report.json, and the
    newest such dir (the original final, or the -rerun<ts> that replaced a void). Anything else is ambiguous."""
    void, picked, problems = void_dirs(task, "final"), {}, []
    for m in MODELS:
        ds = campaign_dirs(task, "final", m)
        live = [d for d in ds if os.path.realpath(d) not in void]
        good = [d for d in live if _valid_runs(d) == NEED["final"]]
        if len(good) == 1 and good[0] == live[-1]:
            picked[m] = good[0]
            continue
        seen = ", ".join(f"{d.name} (" + ("void" if d not in live else "no report.json" if _valid_runs(d) < 0
                                          else f"{_valid_runs(d)} valid") + ")" for d in ds) or "none"
        problems.append(f"{m}: {'ambiguous' if good else 'no'} final campaign with {NEED['final']} valid runs: {seen}")
    return picked, problems


def _py_tool(script: str, *args: str) -> subprocess.CompletedProcess:
    """A pool or packaging tool under the controller interpreter (.venv), without ANTHROPIC_AUTH_TOKEN."""
    return subprocess.run([paths.PY, "-B", str(TOOLS / script), *args], cwd=ROOT, env=ENV, capture_output=True,
                          text=True)


def _echo(p: subprocess.CompletedProcess) -> None:
    for line in (p.stdout + p.stderr).strip().splitlines():
        print("  " + line)


def _harbor(frozen: Path, ws: str, max_min: float) -> int:
    """tc_path launch (once per frozen tree), then pull every SHIP_POLL s until a bound receipt is installed."""
    key = str(frozen.resolve())
    if _receipt(frozen) == "pass":
        print("harbor  receipt already installed: pass")
        return 0
    runs = _tc_runs()
    if key in runs:
        print(f"harbor  tasks-check run {runs[key].get('run')} on {runs[key].get('ws')} already launched: polling")
    else:
        print(f"== harbor tasks-check on {ws} (an LLM trial of a few minutes)", flush=True)
        p = _py_tool("tc_path.py", "launch", key, ws)
        _echo(p)
        runs = _tc_runs()
        if p.returncode or key not in runs:
            print(f"FAIL tc_path launch exit {p.returncode}; nothing installed")
            return 1
    run, deadline, errors = runs[key], time.time() + max_min * 60, 0
    while True:
        p = _py_tool("tc_path.py", "pull", key, run["ws"], run["run"])
        text = (p.stdout + p.stderr).strip()
        got = re.search(r"(?m)^installed (\S+)", text)
        if "not installed" in text:
            print(f"FAIL harbor: {text.splitlines()[-1]}\nSTOP    a human decides")
            return 1
        if got:
            if got.group(1) == "pass":
                print("harbor  installed pass")
                return 0
            print(f"FAIL harbor: installed {got.group(1)}\nSTOP    the receipt failed: a human decides")
            return 1
        if "no receipt yet" in text:
            errors = 0
            print(f"{time.strftime('%H:%M:%S')} harbor: no receipt yet", flush=True)
        else:
            errors += 1
            print(f"harbor pull: {(text.splitlines() or [f'exit {p.returncode}'])[-1][:200]}", flush=True)
            if errors >= 3:
                print("FAIL harbor: tc_path pull failed 3 times in a row")
                return 1
        if time.time() > deadline:
            print(f"TIMEOUT after --max {max_min:g} min waiting for the receipt; rerun the same ship command to resume")
            return 124
        time.sleep(SHIP_POLL)


def ship(task: Path, audit: str, ws: str | None, out: str | None, max_min: float) -> int:
    name, ver, T = base_name(task), version(task), _q(task)
    if "_versions" in task.parts:
        print(f"REFUSED: {task} is archived; ship takes the live tree ({paths.TASKS / name})")
        return 2
    print(f"== ship {name} {ver}", flush=True)
    problems: list[str] = []
    rep = Path(audit).expanduser().resolve()
    dec, why = audit_verdict(rep, task) if rep.is_file() else (None, f"no audit report at {rep}")
    if dec in ("SHIP", "SHIP-WITH-DISCLOSURE"):
        print(f"audit   {why[:200]}")
    else:
        problems.append(f"audit: {why[:200]}" if dec is None else f"audit verdict is {dec}: back to the author")
    g = paths.GATES / f"{name}-{ver}-final.json"
    try:
        gm = json.loads(g.read_text()).get("models") or {}
        pf, pa = ((gm.get(m) or {}).get("pass_at_1") for m in MODELS)
        if pf is None or pa is None or pf > 0.5 or pa > 0.5:
            problems.append(f"final gate: pass@1 fable {pf}, astra {pa}; ship needs <= 0.5 on both")
        else:
            print(f"gate    final pass@1 fable {pf:.2f}, astra {pa:.2f}")
    except (OSError, ValueError):
        problems.append(f"no final gate report ({g}): {MEP} run {T} final")
    ident = _identity(task)
    ac = _read_rec("author-check", task)
    if ac and ac.get("verdict") == "READY" and ident and ac.get("identity") == ident:
        print(f"author  author-check READY at {ac.get('at')}")
    else:
        what = ("not run" if not ac else ac.get("verdict") if ac.get("identity") == ident
                else f"{ac.get('verdict')} on other content")
        problems.append(f"author-check is {what}, not READY on this content: {ME} author-check {T}")
    dirs, why_dirs = final_dirs(task)
    problems += why_dirs
    for m, d in dirs.items():
        rj = json.loads((d / "report.json").read_text())
        if (rj.get("task_validation") or {}).get("artifact_sha256") != ident:
            problems.append(f"{d.name} measured other content than this tree (task_validation.artifact_sha256)")
        else:
            print(f"final   {m}: {d}")
    controls = {k: paths.ARTIFACTS / f"{name}-{ver}-pilot-{k}" for k in ("oracle", "nop")}
    problems += [f"no finished pilot {k} control at {d}" for k, d in controls.items() if not (d / "report.json").is_file()]
    ws = ws or (campaign(task, "final") or {}).get("ws")
    if not ws:
        problems.append("no pool for the harbor check: pass [ws]")
    frozen = paths.TASKS / "_versions" / f"{name}-{ver}"
    if frozen.exists() and _identity(frozen) != ident:
        problems.append(f"{frozen} exists with other content (_versions/ is never edited)")
    if problems:
        print("REFUSED (nothing frozen, launched or written):")
        for p in problems:
            print(f"  - {p}")
        return 3

    if frozen.exists():
        print(f"frozen  {frozen} already holds this content: resuming")
    else:
        frozen.parent.mkdir(parents=True, exist_ok=True)
        shutil.copytree(task, frozen, symlinks=True)  # cp -R
        if _identity(frozen) != ident:
            print(f"FAIL the frozen copy {frozen} does not reproduce the tree's identity")
            return 1
        print(f"frozen  {frozen}")
    rc = _harbor(frozen, ws, max_min)
    if rc:
        return rc

    outd = Path(out).expanduser().resolve() if out else paths.STATE / "deliveries"
    steps = sorted(p.name for p in (frozen / "steps").iterdir() if p.is_dir())
    want = [outd / f"{name}__{s}.zip" for s in steps]
    record = {"frozen": str(frozen), "audit": str(rep), "decision": dec, "ws": ws,
              "campaigns": {m: str(d) for m, d in dirs.items()}, "controls": {k: str(d) for k, d in controls.items()}}
    if all(z.is_file() for z in want):
        _write_rec("ship", task, {**record, "zips": [str(z) for z in want], "ok": True})
        print(f"SHIP {name} {ver}: zips already assembled")
        for z in want:
            print(f"  {z}")
        return 0
    outd.mkdir(parents=True, exist_ok=True)
    scr = os.environ.get("CLAUDE_SCRATCH")
    stage = Path(tempfile.mkdtemp(prefix=f"b6-ship-{name}-", dir=scr if scr and Path(scr).is_dir() else None))
    try:
        shutil.copytree(frozen, stage / name, symlinks=True)  # the assembler works on a staged copy, live name
        argv = [str(stage / name), *[x for m in MODELS for x in (f"--{m}", str(dirs[m]))],
                "--oracle", str(controls["oracle"]), "--nop", str(controls["nop"]), "-o", str(outd)]
        print(f"== assemble_b4_zip.py {' '.join(map(_q, argv))}", flush=True)
        p = _py_tool("assemble_b4_zip.py", *argv)
    finally:
        shutil.rmtree(stage, ignore_errors=True)
    _echo(p)
    lines = re.findall(r"(?m)^\s*(.+?\.zip(?:\.invalid)?): (OK|INVALID) \(", p.stdout)
    ok = p.returncode == 0 and bool(lines) and all(s == "OK" for _, s in lines)
    _write_rec("ship", task, {**record, "zips": [z for z, s in lines if s == "OK"], "ok": ok})
    print(f"SHIP {name} {ver}: {'OK' if ok else 'FAILED (assembler exit ' + str(p.returncode) + ')'}")
    for z, s in lines:
        print(f"  {z}: {s}")
    if ok:
        print(f"STOP    {STOPS['done']}\nNEXT    {ME} next {T}   # inventory commands")
    return 0 if ok else 1


# --------------------------------------------------------------------------- CLI

def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="b6ctl.py", description=__doc__.split("\n\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    stage = {"choices": ["pilot", "final"]}
    which = {"choices": ["fable", "astra", "both"], "default": "both"}
    sub.add_parser("status")
    sub.add_parser("check").add_argument("task")
    for name in ("validate", "author-check"):
        p = sub.add_parser(name)
        p.add_argument("task")
        p.add_argument("--timeout", type=int, default=3600)
    sub.add_parser("preflight").add_argument("--model", **which)
    for name in ("launch", "rerun-void"):
        p = sub.add_parser(name)
        p.add_argument("task")
        p.add_argument("stage", **stage)
        if name == "launch":
            p.add_argument("ws", nargs="?")
        else:
            p.add_argument("model", choices=list(MODELS))
        p.add_argument("--no-preflight", action="store_true", help="launch even if a key does not answer 200")
        p.add_argument("--dry-run", action="store_true", help="print the measure.py command instead of running it")
    p = sub.add_parser("wait")
    p.add_argument("task")
    p.add_argument("stage", **stage)
    p.add_argument("--model", **which)
    p.add_argument("--every", type=int, default=180)
    p.add_argument("--max", type=int, default=7200)
    p = sub.add_parser("gate")
    p.add_argument("task")
    p.add_argument("stage", **stage)
    p = sub.add_parser("blind-prep")
    p.add_argument("task")
    p.add_argument("--out", help="parent directory for the mktemp workspace (default: $CLAUDE_SCRATCH)")
    p = sub.add_parser("blind-grade")
    p.add_argument("task")
    p.add_argument("workspace")
    sub.add_parser("doctor", help="check every prerequisite; one OK/WARN/FAIL line each, with its fix")
    p = sub.add_parser("new", help="scaffold TASKS/a_f<level>_<slug> 1.0.0 from production/templates/skeleton")
    p.add_argument("slug")
    p.add_argument("--level", choices=["f0", "f1", "f2"], default="f1")
    p.add_argument("--seed", help="the seed trace's session id (task.toml source_trace, provenance/ledger.json)")
    p.add_argument("--plan", help="the plan brief to copy to authoring/PLAN.md")
    p = sub.add_parser("prompt", help="a ready-to-paste agent prompt (production/prompts/<kind>.md)")
    p.add_argument("kind", choices=["author", "tune", "audit", "blind"])
    p.add_argument("task")
    p.add_argument("--notes", help="a file whose text fills {NOTES}")
    p.add_argument("--out", help="scratch parent ({SCRATCH}); blind: where the reader workspace is made "
                                 "(default $CLAUDE_SCRATCH)")
    p = sub.add_parser("run", help="launch, wait, re-run voids once, gate and census one stage; one VERDICT line")
    p.add_argument("task")
    p.add_argument("stage", **stage)
    p.add_argument("ws", nargs="?")
    p.add_argument("--max", type=float, default=480, help="minutes to wait in all (default 480); rerun to resume")
    sub.add_parser("next", help="the task's stage and the exact next command(s)").add_argument("task")
    p = sub.add_parser("ship", help="freeze to _versions/, harbor tasks-check, assemble the zips")
    p.add_argument("task")
    p.add_argument("ws", nargs="?", help="pool for the harbor check (default: the final campaign's)")
    p.add_argument("--audit", required=True, help="the §14 audit report (its last VERDICT line decides)")
    p.add_argument("--out", help="zip directory (default STATE/deliveries)")
    p.add_argument("--max", type=float, default=60, help="minutes to wait for the harbor receipt (default 60)")
    a = ap.parse_args(argv)
    if a.cmd == "status":
        return status()
    if a.cmd == "preflight":
        return 0 if preflight(MODELS if a.model == "both" else (a.model,)) else 3
    if a.cmd == "doctor":
        return doctor()
    if a.cmd == "new":
        return new_task(a.slug, a.level, a.seed, a.plan)
    t = Path(a.task).resolve()
    if not (t / "task.toml").is_file():
        print(f"not a task dir: {t}")
        return 2
    if a.cmd == "prompt":
        return prompt(a.kind, t, a.notes, a.out)
    if a.cmd == "run":
        return run_stage(t, a.stage, a.ws, a.max)
    if a.cmd == "next":
        return next_step(t)
    if a.cmd == "ship":
        return ship(t, a.audit, a.ws, a.out, a.max)
    if a.cmd == "check":
        return check(t)
    if a.cmd == "validate":
        return validate(t, a.timeout)
    if a.cmd == "author-check":
        return author_check(t, a.timeout)
    if a.cmd == "launch":
        return launch(t, a.stage, a.ws, a.no_preflight, a.dry_run)
    if a.cmd == "rerun-void":
        return rerun_void(t, a.stage, a.model, a.no_preflight, a.dry_run)
    if a.cmd == "wait":
        return wait(t, a.stage, a.model, a.every, a.max)
    if a.cmd == "gate":
        return gate(t, a.stage)
    if a.cmd == "blind-prep":
        return blind_prep(t, a.out)
    return blind_grade(t, Path(a.workspace).resolve())


if __name__ == "__main__":
    raise SystemExit(main())
