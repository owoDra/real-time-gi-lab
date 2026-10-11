#!/usr/bin/env bash
# N006 P1m3c: distinct deforming-control N001 reference eligibility gate.
# If refs are black/identical STOP before GPU +4 candidate runs.
set -euo pipefail
cd "$(dirname "$0")/../../.."
if [[ "$(git branch --show-current)" != "research-n006-interval-aware-allocation" ]]; then
  echo "[P1m3c] wrong branch" >&2
  exit 2
fi
if [[ -n "$(git status --porcelain)" ]]; then
  echo "[P1m3c] clean worktree required" >&2
  exit 2
fi
git pull --ff-only
mise run build
mise exec -- python -m unittest discover \
  -s scripts/research/n006_interval_aware_allocation -p 'test_*.py'
mise exec -- python scripts/research/n006_interval_aware_allocation/run_p1m3c_deforming_reference_quality.py
echo "[P1m3c] Upload out/research/n006-interval-aware-allocation/p1m3c-deforming-reference-q8/*/n006-p1m3c-deforming-reference-quality-summary.json"
