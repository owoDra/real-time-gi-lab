#!/usr/bin/env bash
# N006 P1l-C0: non-GPU static audit only. Stop on compiler/build/source
# discrepancies. A blocked provenance result is retained on disk.
set -euo pipefail
cd "$(dirname "$0")/../../.."
if [ "$(git branch --show-current)" != "research-n006-interval-aware-allocation" ]; then
  echo "C0 requires research-n006-interval-aware-allocation branch" >&2
  exit 2
fi
if ! git diff --quiet || ! git diff --cached --quiet || [ -n "$(git ls-files --others --exclude-standard)" ]; then
  echo "C0 requires clean tracked/untracked worktree" >&2
  exit 2
fi
git pull --ff-only
mise run build
mise exec -- python -m unittest discover -s scripts/research/n006_interval_aware_allocation -p 'test_*.py'
mise exec -- python scripts/research/n006_interval_aware_allocation/audit_p1l_c0_e003_spirv.py
