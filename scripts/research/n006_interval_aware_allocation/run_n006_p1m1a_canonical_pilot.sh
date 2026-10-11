#!/usr/bin/env bash
# N006 P1m1a single-key +4 rays static/C3 mechanism preflight only.
# Not a predictive benefit or P2 throughput study.
set -euo pipefail
cd "$(dirname "$0")/../../.."
if [[ "$(git branch --show-current)" != "research-n006-interval-aware-allocation" ]]; then
  echo "N006 P1m1a requires research-n006-interval-aware-allocation" >&2
  exit 2
fi
if ! git diff --quiet || ! git diff --cached --quiet || [[ -n "$(git ls-files --others --exclude-standard)" ]]; then
  echo "N006 P1m1a requires a clean tracked/untracked worktree" >&2
  exit 2
fi
git pull --ff-only
mise run build
mise exec -- python -m unittest discover \
  -s scripts/research/n006_interval_aware_allocation -p 'test_*.py'
echo "[P1m1a] frozen canonical-key zero/low/high static C3 8+4 trace correctness"
mise exec -- python scripts/research/n006_interval_aware_allocation/run_p1m1a_canonical_probe_pilot.py
echo "[P1m1a] Upload out/research/n006-interval-aware-allocation/p1m1a-canonical-key-pilot/*/n006-p1m1a-canonical-key-pilot-summary.json"
