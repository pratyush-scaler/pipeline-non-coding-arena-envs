#!/bin/sh
set -eu
mkdir -p /logs/verifier
export ARENA_REWARD=/logs/verifier/reward.json
export ARENA_DETAILS=/logs/verifier/reward-details.json
python3 /tests/criteria.py > /logs/verifier/arena-grade.json
