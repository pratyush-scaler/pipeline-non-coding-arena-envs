#!/usr/bin/env bash
# One-time setup of a production checkout (2026-10-15). Idempotent: rerun it whenever doctor reports a FAIL.
#
#   bash production/setup.sh
#
# uv sync, the verifier's Python 3.11, keys.env (asks only if it is missing), the trap library, then b6ctl doctor.
# Never prints a credential, never starts or stops a Coder pool. Exits with doctor's code (0 = no FAIL).
set -euo pipefail

ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
B6=(python3 -I production/tools/b6ctl.py)

step() { printf '\n== %s\n' "$*"; }

if ! command -v uv >/dev/null 2>&1; then
  echo "FAIL uv not found -- fix: install uv (https://docs.astral.sh/uv/getting-started/installation/), then rerun bash production/setup.sh"
  exit 1
fi

step "uv sync (.venv from uv.lock: measure.py and the pool tools run under it)"
uv sync

step "uv python install 3.11 (the verifier's python3.11)"
uv python install 3.11

if [[ -f keys.env ]]; then
  step "keys.env is present (contents never shown)"
elif [[ -t 0 ]]; then
  step "./arena keys (input is hidden; writes keys.env at mode 600)"
  env -u ANTHROPIC_AUTH_TOKEN ./arena keys
else
  step "keys.env is missing and there is no terminal to ask on: run ./arena keys yourself, then rerun this script"
fi

step "trap library (production/traps/library.json and TRAP-LIBRARY.md)"
python3 -I production/traps/traplib.py build

step "doctor"
rc=0
"${B6[@]}" doctor || rc=$?  # not under env -u: doctor must see an inherited ANTHROPIC_AUTH_TOKEN to flag it

cat <<'EOF'

Next:
  1. Fix every FAIL above (each line names its fix), then rerun:  python3 -I production/tools/b6ctl.py doctor
     A stopped pool is only a WARN; starting one needs the user's go-ahead.
  2. Read production/START-HERE.md and production/PITFALLS.md, pick a seed, then scaffold a task:
       python3 -I production/tools/b6ctl.py new <slug> --level f1 --seed <session-id> --plan <brief.md>
  3. Lost at any point:  python3 -I production/tools/b6ctl.py next envs-b6/<task>
Run every command from the repo root in bash (not zsh); launch pool commands with env -u ANTHROPIC_AUTH_TOKEN.
EOF
exit "$rc"
