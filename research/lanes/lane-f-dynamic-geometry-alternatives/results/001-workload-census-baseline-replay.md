# F001 — Workload census + baseline replay

Plan: `lane-f-plan-v1`  
Measurement commit: `69bc96b8315af28b732ab9e1f7481a69e9898a88`  
Target: AMD Radeon 8060S Graphics (RADV STRIX_HALO)

## Outcome

**Correctness/validation passed. Baseline timing repeatability is inconclusive.**

No candidate architecture is promoted or rejected by F001.

The first accepted-timing attempt and the one permitted identical rerun both
contained at least one `complete_gpu_us max/min > 1.20` case. In particular,
the run-local `vanilla-software / moving-rigid` control was unstable in both
attempts. Per Issue #16, no third rerun and no outlier deletion are allowed.

Therefore the F002 formal feasibility ceiling

`0.90 * run_local_vanilla_moving_complete_gpu`

cannot be fixed from a stable run-local moving-rigid median at F001. The
historical `2972.408 us` value remains reference-only and must not replace
the frozen run-local comparator.

## Target artifacts

- validation: passed before accepted timing (same measurement commit/device)
- timing attempt 1:
  `out/research/lane-f-dynamic-geometry-alternatives/001-workload-census-baseline-replay/20260929T085026Z`
- timing attempt 2 (the one allowed identical rerun):
  `out/research/lane-f-dynamic-geometry-alternatives/001-workload-census-baseline-replay/20260929T085459Z`

A pre-timing invocation at `20260929T085302Z` failed the clean-tree guard
before measurement because of an unrelated untracked file and is not a timing
attempt.

## Repeatability evidence

Attempt 1 unstable cases:

- combined-hwrt: dense-stress, light-motion, vertical-world-stress
- combined-software: static
- vanilla-software: dense-stress, large-world-stress, moving-rigid
  - moving-rigid median 3032.441677 us
  - min 2962.869489 us
  - max 4313.034820 us

Attempt 2 unstable cases:

- combined-hwrt: camera-motion, dense-stress, moving-rigid, static
- combined-software: dense-stress, light-motion, moving-rigid, static
- vanilla-software: moving-rigid
  - moving-rigid median 3777.857977 us
  - min 3284.480554 us
  - max 4113.936530 us

## Decision

F001 is concluded as:

- correctness: **PASS**
- workload census: **recorded in retained target artifacts**
- baseline replay: **executed**
- moving-rigid baseline repeatability: **INCONCLUSIVE**
- architecture decision: **none**
- F002 implementation/measurement: **may proceed**
- F002 formal pass/fail gate: **pending a plan-valid stable comparator; do not
  substitute either unstable F001 median or the historical ceiling**

This preserves the frozen rule that repeated instability makes the affected
timing gate inconclusive rather than filtered or repeatedly rerun.
