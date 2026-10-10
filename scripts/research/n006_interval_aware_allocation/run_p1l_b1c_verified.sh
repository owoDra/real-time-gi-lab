#!/usr/bin/env bash
# B1c fail-closed one-shot: build -> offline unit/static audit -> exact GPU
# preflight (all five) -> matched 15 processes ONLY on correctness PASS.
set -euo pipefail
cd "$(dirname "$0")/../../.."
if [ "$(git branch --show-current)" != "research-n006-interval-aware-allocation" ]; then
  echo "B1c requires research-n006-interval-aware-allocation branch" >&2
  exit 2
fi
if ! git diff --quiet || ! git diff --cached --quiet || [ -n "$(git ls-files --others --exclude-standard)" ]; then
  echo "B1c requires a clean tracked/untracked worktree" >&2
  exit 2
fi
git pull --ff-only
mise run build
mise exec -- python -m unittest discover -s scripts/research/n006_interval_aware_allocation -p 'test_*.py'
mise exec -- python scripts/research/n006_interval_aware_allocation/audit_p1l_b1c_spirv.py
mise exec -- python scripts/research/n006_interval_aware_allocation/run_p1l_b1_near_first.py --b1c --preflight
mise exec -- python scripts/research/n006_interval_aware_allocation/run_p1l_b1_near_first.py --b1c
