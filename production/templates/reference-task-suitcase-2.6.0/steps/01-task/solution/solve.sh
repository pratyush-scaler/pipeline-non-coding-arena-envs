#!/bin/sh
# Reference solution. Derives the answer from the published fixture; it does
# not copy a stored one. See solve.py.
set -eu
mkdir -p /app/deliverables
python3 /solution/solve.py
