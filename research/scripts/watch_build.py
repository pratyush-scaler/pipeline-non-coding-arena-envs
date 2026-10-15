"""Emit a line when a bundle's stage/status changes; exit when the build process ends."""
import json, os, sys, time
from pathlib import Path

roots = [Path(r) for r in sys.argv[1].split(',')]; pids = [int(x) for x in sys.argv[2].split(',')]
seen = {}
def alive(p):
    try:
        os.kill(p, 0); return True
    except OSError:
        return False
while True:
    for ck in sorted(c for root in roots for c in root.glob("target-*/*/verification/checkpoint.json")):
        bundle = ck.parent.parent.parent.parent.name + '/' + ck.parent.parent.name
        try:
            c = json.loads(ck.read_text()); s = json.loads((ck.parent / "state.json").read_text())
            stage = c.get('stage')
            if stage in ("authoring", "authoring-tools") and s.get("status") == "running":
                stage = "authoring"          # quiet: do not report tool-round toggles
            state = f"{stage} / {s.get('status')}"
        except Exception:
            continue
        if seen.get(bundle) != state:
            seen[bundle] = state
            print(f"{time.strftime('%H:%M')} {bundle}: {state}", flush=True)
    done = [p for p in pids if not alive(p)]
    for p in done:
        print(f"{time.strftime('%H:%M')} BUILD PROCESS {p} EXITED", flush=True)
        pids.remove(p)
    if not pids:
        sys.exit(0)
    time.sleep(60)
