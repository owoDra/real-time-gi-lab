#!/usr/bin/env bash
# N006 next evidence: GPU-independent binary audits and disjoint P1m0 GPU
# diagnostic. C0 may be BLOCKED while M0 remains scientifically independent.
# NEVER reruns rejected B1a/B1c performance campaigns or alters accepted GPU.
set -euo pipefail
cd "$(dirname "$0")/../../.."
if [ "$(git branch --show-current)" != "research-n006-interval-aware-allocation" ]; then
  echo "N006 verification requires research-n006-interval-aware-allocation" >&2
  exit 2
fi
if ! git diff --quiet || ! git diff --cached --quiet || [ -n "$(git ls-files --others --exclude-standard)" ]; then
  echo "N006 verification requires a clean tracked/untracked worktree" >&2
  exit 2
fi
git pull --ff-only
mise run build
mise exec -- python -m unittest discover \
  -s scripts/research/n006_interval_aware_allocation -p 'test_*.py'

# Complete already-rejected B1c's missing *static* audit (no GPU benchmarking).
mise exec -- python scripts/research/n006_interval_aware_allocation/audit_p1l_b1c_spirv.py
mise exec -- python scripts/research/n006_interval_aware_allocation/audit_p1l_c0_division_rounding.py

# C0 checks the original actively loaded E003 .spv against rebuilt source.
# It emits status=blocked JSON and nonzero on missing/mismatched active bytes.
# This stops *E003 C1*, but not the independently frozen P1m0 coverage probe.
c0_status=0
mise exec -- python scripts/research/n006_interval_aware_allocation/audit_p1l_c0_e003_spirv.py || c0_status=$?
echo "[N006] C0 static audit exit=$c0_status (blocked evidence retained)"

# M0: 5 frozen scenes, each one independently warmed software current
# canonical frame, one N004 hit oracle and a separate post-render diagnostic.
# This is not a predictive scheduler / speedup test.
mise exec -- python scripts/research/n006_interval_aware_allocation/run_p1m0_consumer_coverage.py

echo "[N006] M0 evidence complete. C0 exit=$c0_status."
echo "[N006] Share out/research/n006-interval-aware-allocation/p1m0-consumer-coverage-five-scenes/*/n006-p1m0-consumer-coverage-summary.json"
echo "[N006] and out/research/n006-interval-aware-allocation/p1l-c0-e003-static-audit.json"
echo "[N006] and out/research/n006-interval-aware-allocation/b1c-spv-audit.json"
if [ "$c0_status" -ne 0 ]; then
  echo "[N006] E003 C1 BLOCKED on C0 provenance; M0 is independent and retained." >&2
  exit "$c0_status"
fi
