# E002 — HWRT rigid instance architecture

Status: protocol frozen; implementation in progress

## Question

Can the current moving-rigid HWRT maintenance cost be reduced by keeping rigid
geometry immutable in reusable BLAS objects and representing motion only as TLAS
instance state?

E001 measured the current combined-HWRT rigid maintenance as:

- geometry transfer: 2247.510 us (58.61%);
- surface update: 1100.611 us (28.70%);
- BLAS update: 430.778 us (11.23%);
- TLAS update: 40.878 us (1.07%);
- complete dynamic boundary: 6681.143 us.

E002 attacks only the ownership work that rigid motion should not require.
A001 producer surface state remains world-space and is intentionally retained so
this experiment does not silently change the accepted producer contract.

## Workload

Use the exact E001/I001 `moving-rigid` selection and translation semantics.

The selected Sponza instance is split from the static world at setup. Its source
triangles remain immutable for the entire accepted run. The target frame applies
the same E001 translation as a TLAS instance transform.

Do not use the deforming control in E002. Geometry that changes in object space
belongs to E004.

## Variants

Measure three variants in the same target session:

1. **current-hwrt**
   - current scene-wide BLAS ownership;
   - moved vertices/metadata are uploaded;
   - scene-wide BLAS UPDATE;
   - TLAS UPDATE.

2. **rigid-instance-update**
   - static-world BLAS is immutable;
   - selected rigid-object BLAS is immutable;
   - a two-instance TLAS references the static and rigid BLAS objects;
   - the rigid instance transform is uploaded;
   - TLAS uses UPDATE.

3. **rigid-instance-build**
   - same immutable two-BLAS ownership;
   - same rigid instance transform upload;
   - TLAS uses BUILD into the preallocated TLAS instead of UPDATE.

The UPDATE/BUILD policies use the same instance count, BLAS objects, geometry,
producer/storage contracts, workload, and tracing shader semantics.

## Required instrumentation

Record separately:

- surface update GPU time;
- rigid instance-state upload wall/GPU time;
- geometry transfer wall/GPU time;
- BLAS update time;
- TLAS maintenance time;
- TLAS policy;
- traversal maintenance GPU time;
- traversal time;
- producer/storage timings;
- complete GPU time;
- dynamic update wall;
- complete dynamic boundary;
- persistent/scratch/peak memory.

For an instance candidate, rigid geometry transfer and BLAS update must be zero
by construction. Instance-state transfer is not to be mislabeled as geometry
transfer.

The complete dynamic boundary remains:

`dynamic_update_wall_us + complete_gpu_us - traversal_maintenance_gpu_us`.

## Validation order

1. Clean Lane E checkout on the target machine.
2. Vulkan validation enabled for all three variants.
3. Require existing I001 visibility/producer/Hit/storage/resolved/temporal gates.
4. Require zero storage failures and zero Vulkan validation errors.
5. Only then run 3 validation-disabled process repeats.

Target:
`AMD Radeon 8060S Graphics (RADV STRIX_HALO)`.

## Frozen E002 gates

These thresholds are fixed before target timing.

### Architecture-integrity gate

For both rigid-instance candidates:

- median and every accepted row must report `geometry_transfer_gpu_us == 0`;
- median and every accepted row must report `blas_update_us == 0`;
- `instance_transfer_gpu_us` must be explicitly recorded;
- moved primitive count and workload identity must match the same-run control.

### GPU accounting gate

For every accepted row:

`surface_update_gpu_us + instance_transfer_gpu_us + geometry_transfer_gpu_us + blas_update_us + tlas_update_us`

must match `traversal_maintenance_gpu_us` within
`max(2 us, 1% of traversal_maintenance_gpu_us)`.

The control has zero instance transfer. The candidates have zero rigid geometry
transfer and zero BLAS update.

### Promotion gate

A rigid-instance candidate is promotable only if all are true:

- all validation/correctness/storage gates pass;
- median complete dynamic boundary is at least **20% lower** than the same-run
  current-HWRT control;
- median traversal time is no more than **10% slower** than the same-run
  current-HWRT control;
- no correctness or semantics contract is weakened.

The 20% requirement defines "material" for E002 and is not to be changed after
timing.

### TLAS policy selection

- If only one instance policy passes the promotion gate, select that policy.
- If both pass and their complete dynamic-boundary medians differ by more than
  5%, select the lower median.
- If both pass and are within 5%, select TLAS UPDATE as the simpler incremental
  maintenance contract.
- If neither passes, do not promote the instance architecture and record why.

Memory is recorded but is not a promotion threshold in E002; E005 must still
check the final integrated footprint and stable-regime behavior.

## Decision boundary

E002 may promote only the rigid HWRT ownership/update policy. It must not claim
that deforming/skinned geometry is solved. E004 remains responsible for the
geometry-changing boundary.

A001 natural append semantics and C001 sparse storage remain unchanged.
