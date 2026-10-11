# E003 — software object-local rigid ownership

Status: accepted evidence; object-local quantized software ownership promoted

## Provenance

Accepted target measurement:

- branch: `research-lane-e-dynamic-geometry`;
- commit: `09944ee0b580cd67911d3c0a13b87821d8c939dc`;
- dirty: false;
- target: `AMD Radeon 8060S Graphics (RADV STRIX_HALO)`;
- scenario: `moving-rigid`;
- process repeats: 3;
- moved primitives: 796;
- segment membership changes: 796.

The supplied accepted evidence consists of `e003-results.csv`,
`e003-summary.json`, and `e003-validation-summary.json`. No outer
`research:record` artifact path was supplied with the accepted files, so this
result does not invent one.

## Validation and architecture integrity

The repeated validation matrix passed before accepted timing:

- all quality gates passed;
- all storage-failure counts were zero;
- the same moving-rigid workload was used by all variants;
- the frozen GPU accounting gate passed;
- the frozen object-local architecture-integrity gate passed.

For every accepted object-local row:

- `geometry_transfer_gpu_us == 0`;
- `membership_update_cpu_us == 0`;
- `hierarchy_refit_cpu_us == 0`;
- `hierarchy_rebuild_cpu_us == 0`;
- `packing_cpu_us == 0`;
- `hierarchy_upload_gpu_us == 0`;
- instance-state transfer was measured explicitly.

No correctness, Hit, storage, or promotion threshold was relaxed after timing.

## Accepted medians

| variant | complete dynamic boundary (us) | traversal (us) | persistent bytes | instance transfer GPU (us) |
| --- | ---: | ---: | ---: | ---: |
| current combined software | 100378.753 | 257.088 | 27,561,104 | 0.000 |
| object-local binary | 1855.421 | 371.947 | 31,725,776 | 4.168 |
| object-local quantized | **1862.834** | **281.455** | **27,694,880** | **4.248** |

The current software control remains dominated by world-space rigid maintenance:

- hierarchy rebuild: 76,938.754 us;
- packing: 15,648.180 us;
- membership update: 1,270.959 us;
- geometry transfer GPU: 1,160.405 us;
- hierarchy upload GPU: 101.192 us.

All of those object-local rigid maintenance components are zero in the promoted
candidate.

## Frozen-gate evaluation

The promotion candidate required:

- at least 50% lower complete dynamic boundary;
- no more than 15% traversal regression;
- persistent memory no more than 1.25x control;
- all correctness/storage/accounting/architecture-integrity gates.

Observed object-local quantized result:

- complete dynamic-boundary improvement: **98.14%**;
- traversal regression: **9.48%**;
- persistent-memory ratio: **1.0049x**;
- promotion gate: **pass**.

The result is far inside the frozen boundary threshold without consuming the
traversal or memory guard bands.

## Binary mechanism control

The binary object-local row confirms that ownership separation itself is the
dominant rigid-maintenance mechanism, but it is not the representation to retain.

Relative to the quantized object-local row:

- binary traversal is **1.322x** slower;
- binary persistent memory is **1.146x** larger.

Therefore the accepted B003 conservative quantized Micro BVH8 remains useful
under object-local ownership rather than being an artifact of the old
world-space update model.

## Mechanism conclusion

Rigid software geometry should not be reinserted into the world StrataBrick
hierarchy when it only changes instance transform.

Promote this software-fallback ownership model for rigid objects:

- immutable static-world StrataBrick / quantized Micro BVH8 payload;
- immutable object-local rigid StrataBrick / quantized Micro BVH8 payload;
- explicit instance table with world bounds and transform state;
- world-space ray instance culling followed by local-space traversal;
- only instance state changes for rigid motion;
- original primitive/material/instance metadata and deterministic Hit semantics
  remain unchanged.

The accepted A001 producer surface update remains world-space and is intentionally
outside E003's ownership change.

## Limits

E003 proves the rigid software ownership/update mechanism only.

It does not establish the correct policy for:

- deforming/skinned geometry;
- topology-changing geometry;
- local-hierarchy update/refit/rebuild policy when vertices change;
- final integrated stable-regime and memory behavior.

Those remain E004–E005 responsibilities.

## Decision

Promote for Lane E integration:

**object-local StrataBrick + conservative quantized Micro BVH8 + explicit
instance traversal for rigid software fallback.**

Continue to E004 with deforming/skinned-like geometry. E004 must not reuse the
E003 zero-maintenance assumption because its object-space vertices genuinely
change.
