# J004 formal crossover gate v2 amendment

Status: **FROZEN BEFORE ACCEPTED TARGET TIMING**
Issue: #23
Parent gate: `experiments/004-formal-crossover-gate-v1.md`

This amendment hardens the executable protocol after pre-timing self review.
No accepted J004 architecture timing was observed before these corrections.
The frozen J002 workload, 5% promotion threshold, 5% non-regression boundary,
class selector, 4/12 paired warmup/measurement shape, eight fresh-process
blocks, zero-rerun rule, and GPU-primary/CPU-wall-diagnostic roles are
unchanged.

## Pre-timing corrections

1. Accepted validation now checks **all** frozen A001 replay rays. A finite
   validation prefix is forbidden.
2. Every J002 snapshot is reparsed and checked against the materialized
   primitive count and SHA-256 geometry digest before any target timing. The
   frozen J002 contract blob and per-profile topology digests are also pinned.
3. The exact nearest-hit/tie contract has its own zero-error field,
   `nearest_hit_tie_mismatch_count`, rather than being implicit in the generic
   Hit mismatch total.
4. Control/candidate fresh-process position is counterbalanced per frozen block
   before execution. The software accounting control remains diagnostic and
   occupies the non-decision trailing position.
5. The formal CSV now emits all J002-required recurring boundary fields,
   including upload/build/traversal/merge/storage/resolve timing and
   persistent/transient/scratch/old-new-overlap/true-peak memory accounting.
6. Allocation peak is captured **before** diagnostic storage-stat readback.
   Readback staging can no longer inflate formal true-peak residency.
7. Batch memory categories come from one real maximum-live-residency
   transition; independent per-category maxima cannot synthesize a state that
   never existed.
8. Full Vulkan provenance now includes driver version, vendor ID, device ID,
   API version, driver name/info, device name, and timestamp period.
9. Formal C++ and shader trees plus Python analysis/input validators are pinned
   by Git object identity before execution.
10. Storage capacity is range-checked before narrowing to 32 bits.

These are fail-closed measurement-integrity corrections, not candidate tuning.
No workload geometry, candidate algorithm, threshold, selector, or favorable
rerun policy changed.

## Measurement boundary

For every complete topology transition the formal GPU total includes:

- recurrent geometry upload;
- HWRT BLAS/TLAS rebuild where applicable;
- LBVH dynamic build where applicable;
- static and dynamic traversal;
- exact static/dynamic Hit merge;
- deterministic radiance and merge;
- C001 reserve/accumulate/invalidate/resolve;
- required GPU synchronization represented by the timestamped command
  dependencies.

Recurrent CPU-side preparation/allocation remains inside complete CPU wall and
is reported diagnostically. It is not moved into setup.

## Source identity

Canonical execution config:
`experiments/005-formal-crossover-config.json`
(`lane-j-j004-formal-v2`).

Machine-readable source freeze:
`experiments/006-formal-execution-freeze-v2.json`.

The clustered two-level BVH remains rejected by the earlier hard-memory gate
and is not timing-eligible.

## Entry to target execution

The next step is build + full validation + formal target campaign. J005 remains
blocked until the resulting J004 summary formally retains at least one backend
for at least one frozen class/track.
