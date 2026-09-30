# J004 formal execution preparation v2

Status: **READY FOR TARGET EXECUTION — no accepted timing observed**
Issue: #23

The clustered two-level candidate has already been rejected by the frozen
same-run relative-memory gate. J004 therefore proceeds only with the retained
pre-frozen controls/alternatives:

- Lane-E object-local HWRT rebuild;
- Lane-E/B003-compatible object-local software rebuild;
- hardened transient LBVH;
- vanilla software accounting control.

The unchanged transient-LBVH attribution path is not separately timed because
the formal recurring F003 builder/traversal source is byte-identical to the
retained Lane-G recurrent implementation and the setup-lifetime hardening is
held common outside that recurring difference.

## Pre-timing self review

Before target timing, the executable protocol was hardened to:

- validate every A001 replay ray;
- explicitly count nearest-hit/tie mismatches;
- verify all J002 snapshot bytes/counts/digests and the J002 contract blob;
- counterbalance formal comparison process position;
- emit and validate the complete J002 boundary schema;
- exclude diagnostic readback staging from formal true-peak memory;
- retain real, non-synthetic batch memory classifications;
- record full device/driver provenance;
- pin formal source/shader trees and analysis/input-validator blobs;
- fail before uint32 storage-capacity narrowing.

The v1 decision thresholds and selector were not changed. No candidate timing
was inspected while making these corrections.

## Remaining evidence step

The repository-side implementation is prepared, but the formal campaign still
requires execution on the target AMD Radeon 8060S / RADV environment with the
local frozen J002 artifacts.

Use the existing recorded-task wrapper:

```bash
mise exec -- python scripts/research/run_experiment.py \
  --lane lane-j-topology-backend-alternatives \
  --experiment 004-formal-crossover \
  --command "mise run research:j004:formal"
```

The task first runs the GPU-independent J004 analysis tests, then builds the
formal executable, runs all-profile correctness/ownership/storage validation,
and only after those pass starts the zero-rerun formal campaign.

J005 remains blocked until that campaign produces a valid summary with
`j005_eligible=true`.
