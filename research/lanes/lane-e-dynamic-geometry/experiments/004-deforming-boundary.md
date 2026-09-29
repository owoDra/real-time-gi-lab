# E004 — deforming geometry boundary

Status: complete; object-local stable-topology deformation promoted for HWRT and software

## Question

After E002/E003 remove unnecessary rigid world-space maintenance, what work still
has to happen when object-space vertices genuinely change?

E004 keeps rigid-transform wins separate from deformation. It tests whether
deforming/skinned-like stable-topology geometry should still be object-owned,
with only the affected object's BLAS or software hierarchy maintained.

E004 does not assume that deformation can become update-free.

## Workload

Use the exact E001 `deforming-control` workload:

- the same selected real Sponza source instance used by E001;
- 796 selected primitives;
- deterministic non-affine vertex deformation;
- stable primitive/material/instance identity and primitive count;
- the existing A001 world-space producer-surface update remains unchanged.

The current E001 deforming control exists specifically to distinguish actual
object-space geometry changes from E002/E003 rigid transform motion.

## HWRT variants

Measure these two HWRT variants in the same target session.

1. **current-hwrt-deforming**
   - existing `combined-hwrt` + `deforming-control`;
   - moved/deformed triangle vertices and metadata are uploaded;
   - the scene-wide BLAS is updated;
   - TLAS is updated.

2. **local-hwrt-deforming**
   - immutable static-world BLAS;
   - selected deforming object owns a separate BLAS built with UPDATE support;
   - only that object's contiguous vertex/metadata range is uploaded;
   - only that object's BLAS is updated;
   - the two-instance TLAS is updated so changed object bounds are visible;
   - no rigid transform shortcut is used: object-space geometry really changes.

### Frozen HWRT promotion gate

The local HWRT candidate is promotable only if:

- all validation/correctness/storage/accounting gates pass;
- stable primitive identity and workload match the same-run control;
- median complete dynamic boundary is at least **5% lower** than current HWRT;
- median traversal is no more than **10% slower** than current HWRT;
- median persistent allocation is no more than **1.25x** current HWRT;
- no shared Hit or producer/storage semantics are weakened.

The 5% threshold is intentionally smaller than the rigid gates. E001 already
showed that deforming HWRT still must pay real geometry transfer; E004 isolates
whether shrinking BLAS maintenance from scene-wide to object-local is materially
useful rather than pretending transfer can disappear.

## Software variants

Measure these two software variants in the same target session.

1. **current-software-deforming**
   - existing `combined-software` + `deforming-control`;
   - world-space geometry upload;
   - world StrataBrick membership/refit/rebuild;
   - whole combined quantized payload repack/upload.

2. **local-software-deforming**
   - immutable static-world object-local StrataBrick + quantized Micro BVH8;
   - a separate deforming-object local StrataBrick + quantized Micro BVH8;
   - only the deforming object's local triangle array is changed;
   - only the deforming object's membership/refit/rebuild and quantized packing
     are performed;
   - only the dynamic object's GPU triangle/hierarchy ranges and instance bounds
     are uploaded;
   - the static-world hierarchy and payload are untouched.

The local software candidate reuses E003's explicit instance traversal and B003
conservative quantized Micro BVH8 semantics.

### Frozen software promotion gate

The local software candidate is promotable only if:

- all validation/correctness/storage/accounting gates pass;
- stable primitive identity and workload match the same-run control;
- median complete dynamic boundary is at least **40% lower** than current
  software;
- median traversal is no more than **15% slower** than current software;
- median persistent allocation is no more than **1.25x** current software;
- no shared Hit or producer/storage semantics are weakened.

The 40% threshold is fixed before timing. E001 showed large world-hierarchy
refit/rebuild plus full-payload packing cost for deformation, so an object-local
software design must remove a substantial fraction of that cost to justify its
extra ownership structure.

## Required instrumentation

Retain the E001 component breakdown for every row:

- geometry preparation CPU;
- surface update GPU;
- geometry transfer wall/GPU;
- instance-state transfer wall/GPU where applicable;
- BLAS update;
- TLAS update;
- membership update CPU;
- hierarchy refit CPU;
- hierarchy rebuild CPU;
- hierarchy occupancy CPU;
- packing CPU;
- hierarchy upload GPU;
- traversal-maintenance GPU;
- traversal;
- complete GPU;
- dynamic update wall;
- complete dynamic boundary;
- persistent/transient/scratch/peak memory.

The complete dynamic boundary remains:

`dynamic_update_wall_us + complete_gpu_us - traversal_maintenance_gpu_us`.

## GPU accounting

For HWRT rows:

`surface_update_gpu_us + geometry_transfer_gpu_us + blas_update_us + tlas_update_us`

must match `traversal_maintenance_gpu_us` within
`max(2 us, 1% of traversal_maintenance_gpu_us)`.

For current software:

`surface_update_gpu_us + geometry_transfer_gpu_us + hierarchy_upload_gpu_us`

must match the same total/tolerance.

For local software:

`surface_update_gpu_us + geometry_transfer_gpu_us + instance_transfer_gpu_us + hierarchy_upload_gpu_us`

must match the same total/tolerance.

## Validation order

1. Clean Lane E checkout on the target machine.
2. Vulkan validation enabled for all four variants.
3. Require existing I001 visibility/producer/Hit/storage/resolved/temporal gates.
4. Require zero storage failures and zero Vulkan validation errors.
5. Require the same deforming-control workload and moved primitive identity.
6. Only then run 3 validation-disabled process repeats.

Target:
`AMD Radeon 8060S Graphics (RADV STRIX_HALO)`.

## Topology-changing boundary

E004 evidence is stable-topology deformation evidence only.

A primitive-count/topology change is explicitly classified outside the UPDATE
fast path:

- current `B002HwrtTraversal::update_geometry` requires stable primitive count;
- `HierarchicalStrataBrick::update` also requires stable primitive count;
- therefore topology-changing objects require an **object-local rebuild** of
  their BLAS/software local hierarchy and any resized payload, not a rigid or
  deforming UPDATE claim.

Lane E must preserve this distinction in its final result. E004 does not average
topology-changing rebuild cost into stable-topology deformation or claim it is
solved without a dedicated workload.

## Decision boundary

E004 may independently promote:

- object-local deforming BLAS maintenance for HWRT;
- object-local deforming StrataBrick/quantized maintenance for software.

One may pass while the other fails. Do not average them.

E002/E003 rigid decisions remain accepted regardless of the E004 outcome.


## Implementation checkpoint

E004 is implemented without changing the frozen gates:

- partitioned HWRT can now opt into UPDATE support for the deforming object's
  BLAS while E002 rigid partitions remain immutable by default;
- stable-topology deformation uploads only the selected object's contiguous
  partition range, updates only that object's BLAS, then refreshes the TLAS;
- software local deformation reserves fixed GPU ranges for the dynamic object's
  triangle, node, order and hash payloads while the static-world payload remains
  untouched;
- only the dynamic object's local StrataBrick is maintained and repacked;
- E003's quantized instance traversal is reused for the local software candidate;
- the dynamic instance bounds/hash metadata are updated after local deformation;
- `run_e004.py` enforces validation-first execution, same-workload identity,
  architecture/accounting checks, independent HWRT/software promotion gates,
  and clean target provenance.

No target GPU timing has been run or inferred from this implementation.

Target validation command:

```bash
git checkout research-lane-e-dynamic-geometry
git pull
mise install
mise run research:check
mise run assets
mise run build
mise run research:record --lane lane-e-dynamic-geometry \
  --experiment 004-deforming-boundary \
  --command "python scripts/research/lane_e_dynamic_geometry/run_e004.py --build-dir build/release --validation-only"
```

Do not start accepted E004 timing until the validation artifact has been
inspected. The formal timing runner repeats the validation matrix.


## Pre-validation self-review correction

Before target validation, the implementation was tightened without changing any
frozen gate or workload:

- partitioned HWRT deformation now uploads the selected object's contiguous
  vertex range and contiguous metadata range as one update each, rather than
  issuing one update record per primitive;
- local deforming candidates now generate and write only the selected 796
  deformed primitives on CPU instead of copying the entire scene merely to
  construct the correctness target.

These changes make the implementation match the already-frozen object-local
ownership claim more closely. They do not change deformation math, primitive
identity, producer/storage semantics, or promotion thresholds.

Correction commits:

- `aeb43b31c8bbe1e157d61f375d5eb73f72ab5b7b` — contiguous HWRT partition upload;
- `cc4cb05743ee6d78de1671f871e7e38bebb8a29e` — object-local CPU deformation preparation.

Target validation must be run at or after these corrections.


## Target validation result

Accepted validation provenance:

- measurement commit: `0e1377f67e140d2e783c25a3e0a89d8e934260d1`;
- branch: `research-lane-e-dynamic-geometry`;
- tree: clean;
- target: `AMD Radeon 8060S Graphics (RADV STRIX_HALO)`;
- validation pairs: 4;
- same deforming-control workload across all variants;
- moved primitives: 796;
- segment membership changes: 148;
- all quality gates passed;
- all storage-failure counts were zero;
- frozen GPU accounting gate passed;
- frozen architecture-integrity gate passed.

The E004 validation gate is satisfied. Accepted timing may begin without changing
the frozen HWRT or software promotion thresholds.

Formal timing command:

```bash
git checkout research-lane-e-dynamic-geometry
git pull
mise install
mise run research:check
mise run assets
mise run build
mise run research:record --lane lane-e-dynamic-geometry \
  --experiment 004-deforming-boundary \
  --command "python scripts/research/lane_e_dynamic_geometry/run_e004.py --build-dir build/release --repeats 3"
```

The timing runner repeats the validation matrix before validation-disabled timing.
Do not alter the frozen E004 gates after observing timing.


## Accepted timing result

Accepted measurement provenance:

- commit: `6a401247f91d3cb1b843a2c9c8cf0819414b9cc2`;
- clean checkout;
- target: `AMD Radeon 8060S Graphics (RADV STRIX_HALO)`;
- 3 process repeats.

Frozen-gate result:

- local HWRT boundary improvement: 64.60%;
- local HWRT traversal regression: 0.91%;
- local HWRT persistent-memory ratio: 1.00001x;
- local HWRT promotion gate: pass;
- local software boundary improvement: 90.61%;
- local software traversal change: -10.92%;
- local software persistent-memory ratio: 1.00512x;
- local software promotion gate: pass.

Final result:
`research/lanes/lane-e-dynamic-geometry/results/004-deforming-boundary.md`.
