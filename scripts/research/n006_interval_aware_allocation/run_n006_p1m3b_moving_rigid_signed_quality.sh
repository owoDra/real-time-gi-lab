#!/usr/bin/env bash
# N006 P1m3b new heldout quality study. TWO independently-converged CPU
# 8-bounce HDR references, 2 Q8 GPU controls, bounded +4 candidate arms.
# Not a positive P1/P2 decision, and no historical shader changes.
set -euo pipefail
cd "$(dirname "$0")/../../.."
if [[ "$(git branch --show-current)" != "research-n006-interval-aware-allocation" ]]; then
  echo "[P1m3b] wrong branch" >&2
  exit 2
fi
if [[ -n "$(git status --porcelain)" ]]; then
  echo "[P1m3b] clean worktree required" >&2
  exit 2
fi
git pull --ff-only
mise run build
mise exec -- python -m unittest discover \
  -s scripts/research/n006_interval_aware_allocation -p 'test_*.py'
mise exec -- python scripts/research/n006_interval_aware_allocation/run_p1m3b_moving_rigid_signed_quality.py
echo "[P1m3b] Upload out/research/n006-interval-aware-allocation/p1m3b-moving-rigid-q8-signed/*/n006-p1m3b-moving-rigid-signed-quality-summary.json"
