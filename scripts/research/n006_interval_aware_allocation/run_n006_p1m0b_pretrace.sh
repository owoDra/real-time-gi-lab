#!/usr/bin/env bash
# N006 P1m0b ONLY: verify same lookup signal can run before secondary rays.
# Not a formal ray-allocation, P1 quality, or P2 performance campaign.
set -euo pipefail
cd "$(dirname "$0")/../../.."
if [ "$(git branch --show-current)" != "research-n006-interval-aware-allocation" ]; then
  echo "N006 P1m0b requires research-n006-interval-aware-allocation" >&2
  exit 2
fi
if ! git diff --quiet || ! git diff --cached --quiet || [ -n "$(git ls-files --others --exclude-standard)" ]; then
  echo "N006 P1m0b requires clean tracked/untracked worktree" >&2
  exit 2
fi
git pull --ff-only
mise run build
mise exec -- python -m unittest discover \
  -s scripts/research/n006_interval_aware_allocation -p 'test_*.py'
echo "[N006 P1m0b] in-renderer pre-secondary GPU cost and full-slot parity, five frozen scenes"
mise exec -- python scripts/research/n006_interval_aware_allocation/run_p1m0_consumer_coverage.py --pretrace
echo "[N006 P1m0b] Share out/research/n006-interval-aware-allocation/p1m0b-pretrace-coverage-five-scenes/*/n006-p1m0-consumer-coverage-summary.json"
