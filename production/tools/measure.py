"""Batch-4 measurement controller: push a hand-built single-step task to a pool and calibrate it (2026-10-09).

    .venv/bin/python production/tools/measure.py launch envs-b6/<task> [--ws <your pool>] [-r 10]   (else $ARENA_POOLS)
    .venv/bin/python production/tools/measure.py status            # refresh every open entry, print the table
    .venv/bin/python production/tools/measure.py table             # print the table from the ledger only

`launch` freezes nothing by itself: it records the task's version and identity and refuses to measure the same
version twice. Per launch it starts, on one pool, an oracle and a nop control (1 rollout each) and a fresh
10-rollout campaign for each calibration model (Fable 5.1 in Claude Code, GPT-6 Astra in Codex, high effort,
no limits, --legacy-diagnostic task semantics). Campaigns are never mixed: a revised task is a new version and
a new campaign. `status` reads each finished campaign's report.json on the pool, classifies voids, computes
pass@1 = full-success trials / valid trials, pulls the output directory back, and writes the ledger
(paths.LEDGER: production/state/ledger.json unless ARENA_LEDGER/ARENA_STATE say otherwise).
Nothing under pipeline/ is written.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shlex
import subprocess
import sys
import time
import tomllib
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import paths  # noqa: E402

ROOT = paths.ROOT
sys.path.insert(0, str(ROOT))
from pipeline.benchmark import coder, coder_run  # noqa: E402

LEDGER = paths.LEDGER
POOLS = paths.POOLS  # $ARENA_POOLS: your own Coder workspaces (tools/paths.py)
MODELS = {"fable": "anthropic/claude-fable-5-1", "astra": "openai/gpt-6-astra"}
OUT = paths.ARTIFACTS
FULL = 0.9999


def load() -> dict:
    return json.loads(LEDGER.read_text()) if LEDGER.is_file() else {"entries": []}


def save(ledger: dict) -> None:
    LEDGER.parent.mkdir(parents=True, exist_ok=True)
    tmp = LEDGER.with_suffix(".tmp")
    tmp.write_text(json.dumps(ledger, indent=1) + "\n")
    tmp.replace(LEDGER)


def merge_save(entries: list[dict], *, append: bool = False) -> None:
    """Write `entries` into the ledger under an exclusive lock, re-reading it first, so a long status pass can
    never overwrite entries launched meanwhile (that race lost two entries on 2026-10-09)."""
    import fcntl
    LEDGER.parent.mkdir(parents=True, exist_ok=True)
    with open(LEDGER.with_suffix(".lock"), "w") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        fresh = load()
        by_id = {e["id"]: i for i, e in enumerate(fresh["entries"])}
        for e in entries:
            if e["id"] in by_id:
                fresh["entries"][by_id[e["id"]]] = e
            elif append:
                fresh["entries"].append(e)
        save(fresh)


def remote(ws: str, cmd: str, data: bytes | None = None, timeout: int = 300) -> str:
    out = coder.ssh(ws, cmd, stdin=data, timeout=timeout, check=True)
    return coder._clean(out.stdout.decode(errors="replace")).strip()


def tree_digest(task: Path) -> str:
    h = hashlib.sha256()
    for p in sorted(task.rglob("*")):
        rel = p.relative_to(task).as_posix()
        if p.is_file() and "__pycache__" not in rel and not rel.startswith(("verification/", "authoring/work")):
            h.update(rel.encode() + b"\0" + p.read_bytes() + b"\0")
    return h.hexdigest()


def alive_counts() -> dict[str, int]:
    counts = {}
    for ws in POOLS:
        try:
            counts[ws] = sum(1 for r in coder_run.runs(ws) if r.get("state") == "alive" or r.get("alive"))
        except Exception:  # noqa: BLE001 - an unreachable pool is simply not chosen
            counts[ws] = 10 ** 6
    return counts


def push(ws: str, task: Path) -> None:
    parent, name = task.parent, task.name
    blob = subprocess.run(["tar", "--no-xattrs", "--no-mac-metadata", "--exclude", "__pycache__",
                           "-C", str(parent), "-cf", "-", name],
                          env={**os.environ, "COPYFILE_DISABLE": "1"}, capture_output=True, check=True).stdout
    q = shlex.quote
    remote(ws, f"mkdir -p {q(str(parent))} && cd {q(str(parent))} && rm -rf {q(name + '.incoming')} && "
               f"mkdir {q(name + '.incoming')} && tar -C {q(name + '.incoming')} -xf - && rm -rf {q(name)} && "
               f"mv {q(name + '.incoming/' + name)} {q(name)} && rmdir {q(name + '.incoming')}", data=blob, timeout=900)


def cmd_launch(args) -> int:
    task = Path(args.task).resolve()
    meta = tomllib.loads((task / "task.toml").read_text())
    version = meta["task"]["version"]
    digest = tree_digest(task)
    ledger = load()
    if getattr(args, "rerun_void", None):
        m = args.rerun_void
        targets = [e for e in ledger["entries"] if e["task"] == str(task) and e.get("stage", "final") == args.stage
                   and e["digest"] == digest and (e["runs"].get(m) or {}).get("state") == "void-auth"]
        if not targets:
            raise SystemExit(f"no void-auth {m} run for {task.name} {version} {args.stage} at this digest; nothing to re-run")
        e = targets[-1]
        push(e["ws"], task)
        old_run = e["runs"][m]
        out = OUT / f"{task.name}-{version}-{args.stage}-{m}-rerun{int(time.time())}"
        n = args.rollouts or (5 if args.stage == "pilot" else 10)
        argv = ["benchmark", str(task), "--legacy-diagnostic", "-o", str(out), "--agent", "harness", "-m", MODELS[m],
                "-r", str(n), "-j", str(n), "--effort", "high"]
        rec = coder_run.launch(e["ws"], argv, sync=False, staged=False)
        e.setdefault("void_history", []).append({m: old_run})
        e["runs"][m] = {"run": rec["run"], "out": str(out), "state": "launched", "replaces_void": old_run.get("run")}
        merge_save([e])
        print(f"re-launched void {m} for {e['id']} on {e['ws']}: {rec['run']}")
        return 0
    for e in ledger["entries"]:
        if e["task"] == str(task) and e.get("stage", "final") == args.stage and (e["version"] == version or e["digest"] == digest):
            raise SystemExit(f"{task.name} {version} already has a {args.stage} campaign (entry {e['id']}); bump the version first")
    if args.stage == "final":
        pilots = [e for e in ledger["entries"] if e["task"] == str(task) and e.get("stage") == "pilot" and e["digest"] == digest]
        if not pilots and not args.force_final:
            raise SystemExit("no pilot of this exact version: run the 5 x 2 pilot first (user, 2026-10-09)")
    if not args.ws and not POOLS:
        raise SystemExit("no pool: pass --ws <your Coder workspace> or set ARENA_POOLS=<ws>[,<ws>...] (your own pools; "
                         "a pool another checkout uses refuses your campaigns)")
    ws = args.ws or min(alive_counts().items(), key=lambda kv: kv[1])[0]
    push(ws, task)
    tag = f"{task.name}-{version}-{args.stage}"
    entry = {"id": f"{tag}@{int(time.time())}", "task": str(task), "name": task.name, "version": version, "stage": args.stage,
             "digest": digest, "ws": ws, "launched_at": time.time(), "runs": {}}
    rollouts = args.rollouts or (5 if args.stage == "pilot" else 10)
    with_controls = args.stage == "pilot" and not args.no_controls
    plan = [("oracle", "oracle", 1), ("nop", "nop", 1)] if with_controls else []
    plan += [(short, model, rollouts) for short, model in MODELS.items()]
    for short, agent_or_model, n in plan:
        out = OUT / f"{tag}-{short}"
        argv = ["benchmark", str(task), "--legacy-diagnostic", "-o", str(out)]
        if short in MODELS:
            argv += ["--agent", "harness", "-m", agent_or_model, "-r", str(n), "-j", str(n), "--effort", "high"]
        else:
            argv += ["--agent", agent_or_model, "-r", "1", "-j", "1"]
        rec = coder_run.launch(ws, argv, sync=False, staged=False)
        entry["runs"][short] = {"run": rec["run"], "out": str(out), "state": "launched"}
        time.sleep(3)
    merge_save([entry], append=True)
    print(f"launched {tag} on {ws}: " + ", ".join(f"{k}={v['run']}" for k, v in entry["runs"].items()))
    return 0


AUTH_FAIL = r"token_invalidated|api key has been invalidated|invalid_api_key|invalid api key|incorrect api key|authentication_error|authentication_failed|401 unauthorized"

SUMMARY = r'''
import json, sys
r = json.load(open(sys.argv[1]))
trials = r.get("trials") or []
out = {"status": r.get("status"), "ok": r.get("ok"), "errors": (r.get("errors") or [])[:3], "trials": []}
for t in trials:
    steps = t.get("steps") or []
    checks = {}
    multi = len(steps) > 1
    for s in steps:
        for k, v in (s.get("checks") or {}).items():
            key = k.split("/", 1)[-1]
            checks[(s.get("name") + "/" + key) if multi else key] = v.get("value")
    out["trials"].append({"id": t.get("id"), "valid": t.get("valid"), "reward": t.get("reward"),
                          "step_rewards": {s.get("name"): s.get("reward") for s in steps},
                          "errors": [str(e)[:200] for e in (t.get("errors") or [])][:2], "checks": checks})
print(json.dumps(out))
'''


def cmd_status(args) -> int:
    ledger = load()
    by_ws: dict[str, list] = {}
    for e in ledger["entries"]:
        if any(r["state"] not in ("done", "failed", "void-auth") for r in e["runs"].values()):
            by_ws.setdefault(e["ws"], []).append(e)
    for ws, entries in by_ws.items():
        try:
            states = {r["run"]: r for r in coder_run.runs(ws)}
        except Exception as exc:  # noqa: BLE001
            print(f"{ws}: cannot list runs ({exc})")
            continue
        for e in entries:
            for short, r in e["runs"].items():
                if r["state"] in ("done", "failed", "void-auth"):
                    continue
                st = states.get(r["run"], {})
                if st.get("state") == "alive" or st.get("alive"):
                    r["state"] = "running"
                    continue
                try:
                    s = json.loads(remote(ws, f"python3 -c {shlex.quote(SUMMARY)} {shlex.quote(r['out'] + '/report.json')}").splitlines()[-1])
                except Exception as exc:  # noqa: BLE001
                    r["state"] = "failed"
                    r["error"] = f"no report.json ({str(exc)[:160]})"
                    continue
                valid = [t for t in s["trials"] if t.get("valid")]
                full = [t for t in valid if (t.get("reward") or 0) >= FULL]
                r.update({"state": "done", "valid": len(valid), "void": len(s["trials"]) - len(valid),
                          "full": len(full), "pass_at_1": (len(full) / len(valid)) if valid else None,
                          "mean_reward": (sum(t["reward"] or 0 for t in valid) / len(valid)) if valid else None,
                          "check_pass": {k: sum(1 for t in valid if (t["checks"].get(k) or 0) >= FULL)
                                         for k in sorted({k for t in valid for k in t["checks"]})},
                          "step_full": {n: sum(1 for t in valid if ((t.get("step_rewards") or {}).get(n) or 0) >= FULL)
                                        for n in sorted({n for t in valid for n in (t.get("step_rewards") or {})})},
                          "void_errors": [t["errors"] for t in s["trials"] if not t.get("valid")][:3],
                          "report_status": s.get("status"), "report_errors": s.get("errors")})
                try:
                    Path(r["out"]).parent.mkdir(parents=True, exist_ok=True)
                    coder_run.rsync(ws, r["out"] + "/", r["out"] + "/", push=False, timeout=1800)
                    r["pulled"] = True
                except Exception as exc:  # noqa: BLE001
                    r["pulled"] = f"failed: {str(exc)[:120]}"
                # A dead model credential makes every episode score 0 while report.json still says "valid".
                # Never let that reach a table: scan the pulled agent logs and void the whole run.
                auth = subprocess.run(["grep", "-rlisE", AUTH_FAIL, str(Path(r["out"]) / "jobs")],
                                      capture_output=True, text=True).stdout.split()
                if auth:
                    r["state"] = "void-auth"
                    r["error"] = f"{len(auth)} agent log files show a credential failure ({AUTH_FAIL}); run is void"
        merge_save(entries)
    print_table(ledger)
    return 0


def print_table(ledger: dict) -> None:
    print(f"{'task':52} {'ver':7} {'stage':6} {'ws':13} {'oracle':7} {'nop':6} {'fable':11} {'astra':11} verdict")
    for e in ledger["entries"]:
        def cell(short):
            r = e["runs"].get(short)
            if not r:
                return "-"
            if r["state"] != "done":
                return r["state"][:9]
            if short in ("oracle", "nop"):
                return f"{(r.get('mean_reward') or 0):.2f}"
            v = f"{r['full']}/{r['valid']}"
            sf = r.get("step_full") or {}
            if len(sf) > 1:
                v += " [" + ",".join(str(x) for x in sf.values()) + "]"
            return v + (f" v{r['void']}" if r.get("void") else "")
        f, a = e["runs"].get("fable", {}), e["runs"].get("astra", {})
        verdict = ""
        if f.get("state") == "done" and a.get("state") == "done":
            pf, pa = f.get("pass_at_1"), a.get("pass_at_1")
            o, n = e["runs"].get("oracle", {}), e["runs"].get("nop", {})
            controls_ok = (o.get("mean_reward") or 0) >= FULL and (n.get("mean_reward") or 0) < 0.5 if o else None
            need = 5 if e.get("stage") == "pilot" else 10
            if f.get("valid", 0) < need or a.get("valid", 0) < need:
                verdict = "TOP-UP voids"
            elif pf is not None and pa is not None and pf <= 0.5 and pa <= 0.5:
                if e.get("stage") == "pilot":
                    verdict = "PILOT HARD -> readers+audit, then final" if controls_ok is not False else "controls fail"
                else:
                    verdict = "FINAL HARD -> package"
            elif pf is not None and pa is not None and pf <= 0.6 and pa <= 0.6 and e.get("stage") == "pilot":
                verdict = "near (3/5) -> harden"
            else:
                verdict = "easy"
        print(f"{e['name'][:52]:52} {e['version']:7} {e.get('stage', 'final')[:6]:6} {e['ws']:13} {cell('oracle'):7} {cell('nop'):6} "
              f"{cell('fable'):11} {cell('astra'):11} {verdict}")


def main() -> int:
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    la = sub.add_parser("launch")
    la.add_argument("task")
    la.add_argument("--ws")
    la.add_argument("--stage", choices=["pilot", "final"], default="pilot",
                    help="pilot = 5 x 2 + oracle/nop (default); final = fresh 10 x 2, only after a pilot of the same version")
    la.add_argument("-r", "--rollouts", type=int, default=0)
    la.add_argument("--force-final", action="store_true", help="allow a final without a recorded pilot")
    la.add_argument("--no-controls", action="store_true")
    la.add_argument("--rerun-void", metavar="MODEL", choices=["fable", "astra"],
                    help="re-run ONLY this model of an existing campaign whose run is void-auth (infra loss is re-run; results are not)")
    sub.add_parser("status")
    sub.add_parser("table")
    args = ap.parse_args()
    if args.cmd == "launch":
        return cmd_launch(args)
    if args.cmd == "status":
        return cmd_status(args)
    print_table(load())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
