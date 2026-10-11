# E002 — HWRT rigid instance architecture

Status: accepted evidence; rigid instance ownership promoted with TLAS UPDATE

## Provenance

Accepted target measurement:

- branch: `research-lane-e-dynamic-geometry`;
- commit: `40f0f1c04f4109cc04a0f6015241518946f9291a`;
- dirty: false;
- target: `AMD Radeon 8060S Graphics (RADV STRIX_HALO)`;
- scenario: `moving-rigid`;
- process repeats: 3;
- moved primitives: 796;
- segment membership changes: 796.

The supplied accepted evidence consists of `e002-results.csv`,
`e002-summary.json`, and `e002-validation-summary.json`. No outer
`research:record` artifact path was supplied with the accepted files, so this
result does not invent one.

## Validation and architecture integrity

The repeated validation matrix passed before accepted timing:

- all quality gates passed;
- all storage-failure counts were zero;
- the same moving-rigid workload was used by all three variants;
- the frozen GPU accounting gate passed;
- the rigid-instance architecture-integrity gate passed.

For every accepted rigid-instance row:

- `geometry_transfer_gpu_us == 0`;
- `blas_update_us == 0`;
- instance transfer was measured explicitly.

No correctness or semantics gate was relaxed after timing.

## Accepted medians

| variant | complete dynamic boundary (us) | traversal (us) | geometry transfer (us) | BLAS update (us) | instance transfer (us) | TLAS maintenance (us) |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| current combined HWRT | 5989.474 | 79.030 | 2275.764 | 441.038 | 0.000 | 42.280 |
| rigid instance + TLAS UPDATE | **1952.891** | **82.356** | **0.000** | **0.000** | **4.128** | **44.805** |
| rigid instance + TLAS BUILD | 2011.499 | 84.921 | 0.000 | 0.000 | 4.248 | 44.765 |

The rigid-instance candidates retain the A001 producer surface update, so their
maintenance is not expected to collapse to only TLAS cost. E002 specifically
tests removal of traversal-side rigid geometry ownership work.

## Frozen-gate evaluation

The protocol required at least 20% lower complete dynamic-boundary median and no
more than 10% traversal regression versus the same-run current-HWRT control.

- TLAS UPDATE:
  - complete dynamic-boundary improvement: **67.39%**;
  - traversal regression: **4.21%**;
  - promotion gate: pass.
- TLAS BUILD:
  - complete dynamic-boundary improvement: **66.42%**;
  - traversal regression: **7.45%**;
  - promotion gate: pass.

Both policies pass. Their complete dynamic-boundary medians differ by less than
the frozen 5% tie band, so the protocol selects **TLAS UPDATE** as the simpler
incremental maintenance contract.

## Mechanism conclusion

Rigid motion should not be represented as a world-space geometry rewrite in the
primary HWRT path.

Promote this ownership model for rigid objects:

- immutable object-local rigid BLAS;
- immutable static-world BLAS;
- rigid motion represented by TLAS instance transform;
- TLAS maintained with UPDATE;
- ray-query metadata indexed with the instance custom-index base;
- object-space Hit work transformed back to world-space semantics.

This removes the dominant E001 rigid geometry transfer and the scene BLAS update
from the dynamic boundary while preserving the accepted producer, storage, and
Hit contracts.

The selected candidate also reduces median scratch allocation from 36,761,648
bytes to 32,504,448 bytes. Persistent allocation is effectively unchanged at
about 72.55 MB. Memory is diagnostic in E002; E005 remains responsible for the
final integrated footprint gate.

## Limits

E002 proves the rigid-object ownership/update mechanism only.

It does not establish the correct policy for:

- deforming/skinned geometry;
- topology-changing geometry;
- software-fallback rigid ownership;
- final stable-regime behavior after integration.

Those remain E003–E005 responsibilities.

## Decision

Promote for Lane E integration:

**object-local immutable BLAS + TLAS instance transform + TLAS UPDATE for rigid
dynamic objects.**

Continue to E003 with a separate software-fallback ownership experiment. The
software experiment must not infer that object-local StrataBrick is beneficial
merely because the HWRT mechanism succeeded.
