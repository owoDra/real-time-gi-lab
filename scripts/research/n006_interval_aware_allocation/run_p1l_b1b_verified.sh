#!/usr/bin/env bash
# N006 P1l-B1b one-command handoff on the research GPU workstation.
# Local build + offline regression tests + all five frozen GPU cases.
# No CI, no auto-commit, no auto-push, no altered research protocols.
set -euo pipefail

root="$(git rev-parse --show-toplevel)"
cd "$root"

if [[ "$(git branch --show-current)" != "research-n006-interval-aware-allocation" ]]; then
  echo "P1l-B1b: refusing to run outside research-n006-interval-aware-allocation" >&2
  exit 2
fi

echo "[P1l-B1b] building N006 and private count shaders"
mise run build

echo "[P1l-B1b] running N006 Python offline regression tests"
mise exec -- python -m unittest discover \
  -s scripts/research/n006_interval_aware_allocation -p 'test_*.py'

echo "[P1l-B1b] running all five GPU scenarios without intermediate manual gates"
mise exec -- python scripts/research/n006_interval_aware_allocation/run_p1l_b1b_work_counts.py

echo "[P1l-B1b] all five test cases passed; send n006-p1l-b1b-counts-summary.json"
