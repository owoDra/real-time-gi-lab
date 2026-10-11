#!/usr/bin/env bash
# Research-only P1m2a isolated direction study; no accepted shaders or CI.
set -euo pipefail
cd "$(dirname "$0")/../../.."
if [[ "$(git branch --show-current)" != "research-n006-interval-aware-allocation" ]]; then
  echo "P1m2a requires research-n006-interval-aware-allocation" >&2
  exit 2
fi
if [[ -n "$(git status --porcelain)" ]]; then
  echo "P1m2a requires clean git worktree" >&2
  exit 2
fi
git pull --ff-only
mise run build
mise exec -- python -m unittest discover \
  -s scripts/research/n006_interval_aware_allocation -p 'test_*.py'
mise exec -- python scripts/research/n006_interval_aware_allocation/run_p1m2a_tetra_octant_pilot.py
echo "[P1m2a] Upload out/research/n006-interval-aware-allocation/p1m2a-tetra-octant-static-c3/*/n006-p1m2a-tetra-octant-summary.json"
