"""Poll measure.py status until some b6 campaign set (fable+astra, plus oracle/nop for pilots) has finished and
has no gate json yet; print those `<task> <stage>` lines and exit (2026-10-13).

    python3 -I b6poll.py [--every 180] [--max 7200]
"""
import json
import os
import subprocess
import sys
import time
import tomllib
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import paths  # noqa: E402

ENV = {k: v for k, v in os.environ.items() if k != "ANTHROPIC_AUTH_TOKEN"}
args = sys.argv[1:]
every = int(args[args.index("--every") + 1]) if "--every" in args else 180
cap = int(args[args.index("--max") + 1]) if "--max" in args else 7200


def ready():
    """Ledger-driven: a campaign set is ready when the latest b6 entry for <task>-<version>-<stage> has fable and
    astra runs in state 'done' (void-auth / launched / running are not ready) and no gate json exists yet."""
    out = []
    names = {p.name for p in paths.TASKS.glob("a_f*")}
    led = json.loads(paths.LEDGER.read_text())
    latest = {}
    for e in led.get("entries", []):
        if e.get("name") in names:
            latest[(e["name"], e["version"], e["stage"])] = e
    for (name, v, stage), e in sorted(latest.items()):
        runs = e.get("runs", {})
        fable_only = "--fable-only" in sys.argv
        if all(runs.get(m, {}).get("state") == "done" for m in ("fable", "astra")):
            if not (paths.GATES / f"{name}-{v}-{stage}.json").is_file():
                out.append(f"{name} {v} {stage}")
        elif fable_only and runs.get("fable", {}).get("state") == "done":
            mark = paths.GATES / f"{name}-{v}-{stage}.fable-seen"
            if not mark.is_file():
                mark.parent.mkdir(parents=True, exist_ok=True)
                mark.write_text(runs.get("astra", {}).get("state", "?"))
                out.append(f"{name} {v} {stage} FABLE-ONLY (astra {runs.get('astra', {}).get('state')})")
    return out


start = time.time()
while True:
    subprocess.run([paths.PY, "-B", str(paths.MEASURE), "status"],
                   cwd=paths.ROOT, env=ENV, capture_output=True, text=True)
    r = ready()
    if r:
        print("\n".join(r))
        break
    if time.time() - start > cap:
        print("TIMEOUT no campaign finished")
        break
    time.sleep(every)
