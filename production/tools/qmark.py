"""Mark a seed authored and move the next queued seed in flight; print the next seed id (2026-10-13).
    python3 -I qmark.py <seed> <task-rel-path> [--no-next]      (queue: production/state/queue.json)"""
import json, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import paths  # noqa: E402
p = paths.QUEUE
q = json.loads(p.read_text())
seed, path = sys.argv[1], sys.argv[2]
q.setdefault("authored", {})[seed] = path
if seed in q["in_flight"]:
    q["in_flight"].remove(seed)
nxt = ""
if "--no-next" not in sys.argv and q["queued"]:
    nxt = q["queued"].pop(0)
    q["in_flight"].append(nxt)
p.write_text(json.dumps(q, indent=1))
print(f"next={nxt} in_flight={len(q['in_flight'])} queued={len(q['queued'])} authored={len(q['authored'])}")
