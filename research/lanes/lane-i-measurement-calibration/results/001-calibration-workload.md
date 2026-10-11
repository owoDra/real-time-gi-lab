# I001 — calibration workload and harness correctness

## Formal status

**Accepted** as harness/correctness evidence. This is not a performance result.

## Question

Can Lane I generate deterministic architecture-neutral GPU work with exact predeclared +5%, +10%, and +20% work deltas while preserving identical resource/layout/dispatch semantics except for controlled iteration count?

## Artifact and provenance

- Artifact: `out/research/lane-i-measurement-calibration/001-calibration-workload/20260930T063252Z`
- Git commit: `7f3c07f7f4d67fc834fbd18a72239c0b4f3cbd39`
- Target GPU: `AMD Radeon 8060S Graphics (RADV STRIX_HALO)`

The target-host console reported successful completion of both the accepted-shape and single-dispatch-control validation profiles.

## Workload

The accepted calibration shape is:

- 8192 elements;
- baseline 200 iterations;
- +5% = 210 iterations;
- +10% = 220 iterations;
- +20% = 240 iterations;
- accepted batch = 16 dependent dispatches;
- diagnostic single-dispatch control = 1 dispatch.

The CPU reference and GPU output checksum validate the deterministic state transition, and the harness verifies exact controlled-work-unit ratios.

## Decision

I001 is accepted for correctness and provenance. It establishes that the declared work deltas are real enough to proceed to the pre-frozen I002/I003 timing calibration. It does not establish timing resolution.
