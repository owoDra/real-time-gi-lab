# E005 — integrated ownership replay and final Lane E decision

Status: accepted evidence; final Lane E HWRT and software ownership architectures accepted

## Provenance

Accepted target measurement:

- branch: `research-lane-e-dynamic-geometry`;
- commit: `2911790d8fd1716615a59dc86034e4fea783c9ec`;
- dirty: false;
- target: `AMD Radeon 8060S Graphics (RADV STRIX_HALO)`;
- process repeats: 3;
- scenarios: static, camera-motion, light-motion, moving-rigid,
  deforming-control;
- timing rows: 60 (5 scenarios x 4 variants x 3 repeats);
- validation pairs: 20.

The supplied accepted evidence consists of `e005-results.csv`,
`e005-summary.json`, and `e005-validation-summary.json`. No outer
`research:record` artifact path was supplied with the accepted files, so this
result does not invent one.

## Validation

The complete validation-first matrix passed:

- all quality gates passed;
- all storage-failure counts were zero;
- same-workload checks passed in all five scenarios;
- frozen GPU accounting passed;
- frozen architecture-integrity checks passed.

No E005 threshold was changed after observing target timing.

## Final candidates

The replay measured the integrated ownership designs, not isolated experiment
variants.

### Final HWRT

- static world in its own BLAS;
- selected dynamic object in its own BLAS;
- rigid motion uses immutable object BLAS + TLAS instance UPDATE;
- stable-topology deformation uploads only the changed object's contiguous
  geometry range, UPDATEs only that object's BLAS, then UPDATEs TLAS;
- static/camera/light keep the idle dynamic partition present and perform no
  dynamic maintenance.

### Final software fallback

- immutable static-world object-local StrataBrick + conservative quantized
  Micro BVH8;
- selected dynamic object owns a separate StrataBrick + quantized Micro BVH8;
- rigid motion changes instance state only;
- stable-topology deformation maintains, repacks and uploads only the changed
  object's local hierarchy and bounds;
- static/camera/light keep the idle dynamic partition present and perform no
  dynamic maintenance.

## Stable-regime replay

Frozen guards:

- final HWRT complete GPU <= 10% slower than same-run combined HWRT;
- final software complete GPU <= 15% slower than same-run combined software;
- each stable scenario passes independently.

| scenario | HWRT control (us) | HWRT final (us) | change | software control (us) | software final (us) | change |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| static | 200.581 | 195.812 | **-2.38%** | 399.639 | 395.992 | **-0.91%** |
| camera motion | 210.961 | 209.518 | **-0.68%** | 397.956 | 395.071 | **-0.73%** |
| light motion | 234.045 | 205.230 | **-12.31%** | 407.254 | 377.758 | **-7.24%** |

All stable-regime guards pass. The final ownership split does not require a
stable-frame dynamic maintenance update, and the measured complete-GPU medians
show no stable regression in this replay.

## Moving-rigid replay

### HWRT

Same-run control vs final:

- complete dynamic boundary: 6192.823 us -> **1909.538 us**;
- boundary improvement: **69.17%**;
- traversal: 82.998 us -> **79.952 us**;
- traversal change: **-3.67%**.

Frozen requirement was >=20% boundary improvement and <=10% traversal
regression. **Pass.**

The final row preserves the E002 mechanism:

- geometry transfer: zero;
- BLAS update: zero;
- instance-state GPU transfer: 4.208 us;
- TLAS UPDATE: 44.725 us.

### Software

Same-run control vs final:

- complete dynamic boundary: 100007.714 us -> **1800.540 us**;
- boundary improvement: **98.20%**;
- traversal: 261.697 us -> **280.814 us**;
- traversal regression: **7.30%**.

Frozen requirement was >=50% boundary improvement and <=15% traversal
regression. **Pass.**

The final row preserves the E003 mechanism: no rigid geometry transfer,
membership update, hierarchy refit/rebuild, packing or hierarchy upload; only
instance state changes.

## Stable-topology deforming replay

### HWRT

Same-run control vs final:

- complete dynamic boundary: 6256.422 us -> **2341.232 us**;
- boundary improvement: **62.58%**;
- traversal: 80.794 us -> **82.437 us**;
- traversal regression: **2.03%**.

Frozen requirement was >=5% boundary improvement and <=10% traversal
regression. **Pass.**

The final row preserves the E004 local-maintenance mechanism:

- local geometry transfer GPU: 6.172 us;
- local BLAS UPDATE: 12.945 us;
- TLAS UPDATE: 44.364 us.

### Software

Same-run control vs final:

- complete dynamic boundary: 34921.709 us -> **3173.064 us**;
- boundary improvement: **90.91%**;
- traversal: 276.125 us -> **284.300 us**;
- traversal regression: **2.96%**.

Frozen requirement was >=40% boundary improvement and <=15% traversal
regression. **Pass.**

The final row retains local-only hierarchy work:

- geometry transfer GPU: 3.166 us;
- membership update CPU: 306.702 us;
- hierarchy refit CPU: 195.735 us;
- hierarchy rebuild CPU: 209.814 us;
- packing CPU: 278.523 us;
- hierarchy upload GPU: 9.378 us;
- instance-bounds transfer GPU: 4.128 us.

## Memory replay

The frozen persistent and peak-resident limits were <=1.25x same-run control in
every scenario.

Observed maxima across all scenarios:

- HWRT persistent ratio: **1.00001x**;
- HWRT peak-resident ratio: **0.97161x**;
- software persistent ratio: **1.00512x**;
- software peak-resident ratio: **1.00207x**.

All memory guards pass.

## Final Lane E architecture

Lane E accepts geometry-class-specific ownership rather than a single world-space
dynamic update model.

### Static world

Keep static geometry immutable in static-owned acceleration data.

### Rigid dynamic objects

HWRT primary:

- immutable object-local BLAS;
- rigid motion represented by TLAS instance transform;
- TLAS UPDATE;
- no rigid vertex upload or BLAS UPDATE.

Software fallback:

- immutable object-local StrataBrick;
- conservative quantized Micro BVH8;
- explicit instance table / world-bounds cull;
- ray transformed into object/source frame;
- rigid motion updates instance state only.

### Stable-topology deforming/skinned-like objects

HWRT primary:

- separate update-enabled object-local BLAS;
- upload only changed object vertices/metadata;
- UPDATE only the object's BLAS;
- TLAS UPDATE after changed bounds.

Software fallback:

- separate object-local StrataBrick + conservative quantized Micro BVH8;
- maintain/refit/rebuild only that object's local hierarchy;
- repack/upload only its local payload and instance bounds.

### Topology-changing objects

Topology change remains an explicit rebuild boundary:

- rebuild only the changed object's BLAS or software local hierarchy/payload;
- resize/recreate that object's owned resources when required;
- do not rewrite unrelated static-world or other object-owned structures.

This is an architectural disposition, not a topology-changing performance claim;
Lane E did not time a primitive-count-changing workload.

## Preserved contracts

Lane E does not change the previously accepted contracts:

- A001 GPU visibility-driven Split RC producer;
- natural append stream / schema;
- HWRT as primary traversal;
- conservative quantized Micro BVH8 software fallback;
- C001 per-probe sparse hash storage;
- shared deterministic Hit semantics.

The research result is specifically an ownership/update-model change.

## Final decision

Both final candidates pass all frozen E005 correctness, architecture, stable,
dynamic and memory gates.

**Accept Lane E final architecture.**

The old assumption that all dynamic geometry should mutate world-space traversal
ownership is rejected. Dynamic geometry should be classified by update semantics:
transform-only rigid instances, locally mutable stable-topology objects, and
object-local rebuilds for topology-changing objects.
