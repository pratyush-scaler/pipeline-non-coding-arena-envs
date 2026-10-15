"""Compare every pilot/final episode's deliverables with the reference solve.py output, field by field (2026-10-13).
A grader that passes everything would show 1.0 rewards with answers that differ from the reference.
    python3 -I census_answers.py [--deep] <task-dir> <campaign-dir>...
--deep drills into lists of records (matched on a unique key field) and prints item-level differences.
"""
import json, os, subprocess, sys, tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import paths  # noqa: E402

PY = paths.PY311


def norm(v):
    if isinstance(v, dict):
        return {k: norm(x) for k, x in sorted(v.items())}
    if isinstance(v, list):
        return sorted((norm(x) for x in v), key=lambda x: json.dumps(x, sort_keys=True))
    if isinstance(v, str):
        return " ".join(v.lower().split())
    if isinstance(v, float) and v.is_integer():
        return int(v)
    return v


DEEP = "--deep" in sys.argv
ARGS = [a for a in sys.argv[1:] if a != "--deep"]


def keyfield(rows):
    if not rows or not all(isinstance(r, dict) for r in rows):
        return None
    for k in rows[0]:
        vals = [json.dumps(r.get(k), sort_keys=True) for r in rows]
        if len(set(vals)) == len(vals) and all(k in r for r in rows):
            return k
    return None


def deep(ref, got, path=""):
    out = []
    if isinstance(ref, dict) and isinstance(got, dict):
        for k in ref:
            out += deep(ref[k], got.get(k), f"{path}.{k}")
    elif isinstance(ref, list) and isinstance(got, list) and (kf := keyfield(ref)):
        gm = {json.dumps(g.get(kf), sort_keys=True): g for g in got if isinstance(g, dict)}
        rm = {json.dumps(r.get(kf), sort_keys=True): r for r in ref}
        for kv, r in rm.items():
            out += deep(r, gm.get(kv), f"{path}[{kf}={kv}]") if kv in gm else [f"{path}[{kf}={kv}] MISSING"]
        out += [f"{path}[{kf}={kv}] EXTRA" for kv in gm if kv not in rm]
    elif norm(ref) != norm(got):
        out.append(f"{path}: ref={json.dumps(ref, ensure_ascii=False)[:60]} got={json.dumps(got, ensure_ascii=False)[:60]}")
    return out


task = Path(ARGS[0]).resolve()
steps = sorted(p.name for p in (task / "steps").iterdir() if p.is_dir())
ref = {}
for st in steps:
    out = Path(tempfile.mkdtemp(prefix="b6-ref-"))
    env = {**os.environ, "ARENA_SOURCE": str(task / "environment/files"), "ARENA_SUBMITTED": str(out), "ARENA_OUT": str(out)}
    subprocess.run([PY, "-I", "-B", str(task / "steps" / st / "solution/solve.py")], env=env, capture_output=True, cwd=out)
    ref[st] = {p.name: json.loads(p.read_text()) for p in out.rglob("*.json")}
for camp in ARGS[1:]:
    camp = Path(camp)
    for ep in sorted((camp / "jobs/run").glob("package__*")):
        for st in steps:
            sd = ep / "steps" / st
            rw = sd / "verifier/reward.json"
            reward = json.loads(rw.read_text()).get("reward") if rw.is_file() else None
            dl = sd / "artifacts/app/deliverables"
            diffs = []
            for name, r in ref[st].items():
                f = dl / name
                if not f.is_file():
                    diffs.append(f"{name}:MISSING")
                    continue
                try:
                    a = json.loads(f.read_text())
                except Exception:
                    diffs.append(f"{name}:INVALID")
                    continue
                for k in r:
                    if norm(a.get(k)) != norm(r[k]):
                        diffs += deep(r[k], a.get(k), f"{name}.{k}") if DEEP else [f"{name}.{k}"]
            print(f"{camp.name[-12:]:>12} {ep.name[-7:]} {st} reward={reward} diff_fields={diffs or 'none'}")
