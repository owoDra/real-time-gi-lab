#!/usr/bin/env bash
# P1m2b: two stable camera/light controls; frozen M0 keys; bounded 8+4 sampling.
# Requires real user AMD GPU. No PR, GitHub Actions, or accepted shader edits.
set -euo pipefail
cd "$(dirname "$0")/../../.."
if [[ "$(git branch --show-current)" != "research-n006-interval-aware-allocation" ]]; then
  echo "[P1m2b] wrong branch" >&2
  exit 2
fi
if [[ -n "$(git status --porcelain)" ]]; then
  echo "[P1m2b] clean checkout required" >&2
  exit 2
fi
git pull --ff-only
mise run build
mise exec -- python -m unittest discover \
  -s scripts/research/n006_interval_aware_allocation -p 'test_*.py'
mise exec -- python scripts/research/n006_interval_aware_allocation/run_p1m2b_independent_state.py
echo "[P1m2b] Upload: out/research/n006-interval-aware-allocation/p1m2b-independent-state/*/n006-p1m2b-independent-state-summary.json"
