#!/usr/bin/env bash
# Emit one line whenever a bundle's checkpoint stage or job status changes; exit when the build process ends.
root=/Users/pratyushmohanty/Downloads/arena-envs-non-coding-v2/envs-v2
pid=$1
declare -A seen
while true; do
  for ck in "$root"/target-*/*/verification/checkpoint.json; do
    [ -f "$ck" ] || continue
    b=$(basename "$(dirname "$(dirname "$ck")")")
    st=$(python3 -c "import json,sys
try:
  c=json.load(open('$ck')); s=json.load(open('$(dirname "$ck")/state.json'))
  print(c.get('stage'), s.get('status'), s.get('verdict') or s.get('outcome') or '')
except Exception as e: print('unreadable')" 2>/dev/null)
    if [ "${seen[$b]}" != "$st" ]; then echo "$(date +%H:%M) $b: $st"; seen[$b]="$st"; fi
  done
  if ! ps -p "$pid" >/dev/null 2>&1; then echo "$(date +%H:%M) BUILD PROCESS EXITED"; tail -5 /Users/pratyushmohanty/Downloads/arena-envs-non-coding-v2/logs/build-v2.log; exit 0; fi
  sleep 60
done
