#!/usr/bin/env bash
# N006 P1m3a Q8 alternate-storage representation. Prospective calibration ONLY.
# Does not test P1 predictive quality or authorize P2 scheduling.
set -euo pipefail
cd "$(dirname "$0")/../../.."
if [[ "$(git branch --show-current)" != "research-n006-interval-aware-allocation" ]]; then
  echo "[P1m3a] wrong branch" >&2
  exit 2
fi
if [[ -n "$(git status --porcelain)" ]]; then
  echo "[P1m3a] clean worktree required" >&2
  exit 2
fi
git pull --ff-only
mise run build
mise exec -- python -m unittest discover \
  -s scripts/research/n006_interval_aware_allocation -p 'test_*.py'
mise exec -- python scripts/research/n006_interval_aware_allocation/run_p1m3a_fractional_storage.py
echo "[P1m3a] Upload out/research/n006-interval-aware-allocation/p1m3a-fractional-q8-calibration/*/n006-p1m3a-fractional-storage-summary.json"
