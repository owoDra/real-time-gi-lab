#!/usr/bin/env bash
# N006 P1m1c: cause of zero energy from 4 extra rays, no reference or scheduler.
set -euo pipefail
cd "$(dirname "$0")/../../.."
if [[ "$(git branch --show-current)" != "research-n006-interval-aware-allocation" ]]; then
  echo "N006 P1m1c requires research-n006-interval-aware-allocation" >&2
  exit 2
fi
if [[ -n "$(git status --porcelain)" ]]; then
  echo "N006 P1m1c requires clean worktree" >&2
  exit 2
fi
git pull --ff-only
mise run build
mise exec -- python -m unittest discover \
  -s scripts/research/n006_interval_aware_allocation -p 'test_*.py'
mise exec -- python scripts/research/n006_interval_aware_allocation/run_p1m1c_ray_fate.py
echo "[P1m1c] Upload out/research/n006-interval-aware-allocation/p1m1c-ray-fate-static-c3/*/n006-p1m1c-ray-fate-summary.json"
