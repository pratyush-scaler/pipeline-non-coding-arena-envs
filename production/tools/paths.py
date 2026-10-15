"""Where the production line reads and writes (2026-10-15). Every tool imports this instead of a hardcoded workspace.

    ARENA_ROOT     repo root: pipeline/, keys.env, .venv            default: the parent of production/
    ARENA_TASKS    live task trees (+ _versions/ archives)          default: ROOT/envs-b6
    ARENA_STATE    ledger, gates, quarantined receipts, run ids     default: ROOT/production/state
    ARENA_LEDGER   the campaign ledger                              default: STATE/ledger.json
    ARENA_LIBRARY  the trap library                                 default: ROOT/production/traps/library.json
    ARENA_PY311    the verifier's interpreter (python3.11)          default: the uv build, else python3.11 on PATH

Campaign output always goes to ROOT/pipeline-artifacts/b4 and the controller interpreter is ROOT/.venv/bin/python.
Nothing here creates a directory; a writer makes its own parent.
"""
from __future__ import annotations

import os
import shutil
from pathlib import Path

TOOLS = Path(__file__).resolve().parent
PRODUCTION = TOOLS.parent
TRAPS = PRODUCTION / "traps"


def _env_path(name: str, default: Path) -> Path:
    v = os.environ.get(name)
    return Path(v).expanduser().resolve() if v else default


ROOT = _env_path("ARENA_ROOT", PRODUCTION.parent)
TASKS = _env_path("ARENA_TASKS", ROOT / "envs-b6")
ARTIFACTS = ROOT / "pipeline-artifacts/b4"
STATE = _env_path("ARENA_STATE", ROOT / "production/state")
LEDGER = _env_path("ARENA_LEDGER", STATE / "ledger.json")
GATES = STATE / "gates"
STALE = STATE / "stale-receipts"
TC_RUNS = STATE / "tc_path_runs.json"
TASKS_CHECK_RUNS = STATE / "tasks-check-runs.json"
TASKS_CHECK_LOCK = STATE / ".tasks-check.lock"
WAIT_LOCK = STATE / ".wait-status.lock"
QUEUE = STATE / "queue.json"
KEYS = ROOT / "keys.env"
# Coder workspaces this checkout calibrates on: YOUR OWN, never a pool another checkout is using (two checkouts on one
# pool refuse each other's campaigns: the pool holds one code hash). Empty -> nothing is auto-picked.
POOLS = [p.strip() for p in os.environ.get("ARENA_POOLS", "").split(",") if p.strip()]
PY = str(ROOT / ".venv/bin/python")
LIBRARY = _env_path("ARENA_LIBRARY", ROOT / "production/traps/library.json")
MEASURE = TOOLS / "measure.py"
SELFTEST = TOOLS / "selftest.py"
FIX = TOOLS / "fix261011"  # apply_central / apply_runtime / apply_stage3 (--check only, from design_lint)

# `uv python install 3.11` puts the interpreter under ~/.local/share/uv/python/cpython-3.11<.patch>-<platform>/;
# take the first 3.11 build found for whatever platform this is
_UV311S = sorted(Path.home().glob(".local/share/uv/python/cpython-3.11*/bin/python3.11"))
_UV311 = _UV311S[0] if _UV311S else Path.home() / ".local/share/uv/python/cpython-3.11/bin/python3.11"
PY311 = (os.environ.get("ARENA_PY311") or (str(_UV311) if _UV311.is_file() else None)
         or shutil.which("python3.11") or str(_UV311))
