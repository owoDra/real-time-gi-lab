# E002 — HWRT rigid instance architecture

Status: complete; rigid instance architecture promoted with TLAS UPDATE

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


## Implementation checkpoint

E002 is implemented as an explicit branch of the accepted B002/I001 HWRT path:

- the current `combined-hwrt` control retains the original one-scene-BLAS
  ownership and geometry/BLAS/TLAS update path;
- candidate setup partitions the selected rigid source instance from the static
  world, builds immutable static and rigid BLAS objects, and creates a
  two-instance TLAS;
- candidate target frames update only the rigid TLAS instance record and then
  maintain the TLAS using the selected UPDATE or BUILD policy;
- candidate geometry upload and BLAS update paths are structurally forbidden;
- the integration HWRT ray-query shader uses the TLAS instance custom index as
  the per-BLAS metadata base and applies the shared Hit semantics in object
  space while returning world-space normals;
- the CPU-translated target geometry used by the existing correctness reference
  is prepared only after the measured dynamic-maintenance wall closes;
- E002's runner enforces the frozen accounting, architecture-integrity,
  validation, repeat and promotion gates.

No target timing has been run or inferred from this implementation.

Target validation command:

```bash
git checkout research-lane-e-dynamic-geometry
git pull
mise install
mise run research:check
mise run assets
mise run build
mise run research:record --lane lane-e-dynamic-geometry \
  --experiment 002-hwrt-rigid-instance \
  --command "python scripts/research/lane_e_dynamic_geometry/run_e002.py --build-dir build/release --validation-only"
```

Do not start accepted E002 timing until the validation artifact has been
inspected. The timing runner will repeat the validation matrix before timing.


## Target validation result

Accepted validation provenance:

- measurement commit: `7c191fca1b7049fd377597d0e369de36f0a54b93`;
- branch: `research-lane-e-dynamic-geometry`;
- tree: clean;
- target: `AMD Radeon 8060S Graphics (RADV STRIX_HALO)`;
- validation pairs: 3;
- same rigid workload across all variants;
- moved primitives: 796;
- segment membership changes: 796;
- all quality gates passed;
- all storage-failure counts were zero;
- frozen GPU accounting gate passed;
- rigid-instance architecture-integrity gate passed.

The E002 validation gate is satisfied. Accepted timing may begin without changing
the frozen architecture, accounting, promotion or TLAS-policy thresholds.

Formal timing command:

```bash
git checkout research-lane-e-dynamic-geometry
git pull
mise install
mise run research:check
mise run assets
mise run build
mise run research:record --lane lane-e-dynamic-geometry \
  --experiment 002-hwrt-rigid-instance \
  --command "python scripts/research/lane_e_dynamic_geometry/run_e002.py --build-dir build/release --repeats 3"
```

The timing runner repeats the validation matrix before validation-disabled
timing. Do not alter the frozen E002 gates after observing timing.


## Accepted timing result

Accepted measurement provenance:

- commit: `40f0f1c04f4109cc04a0f6015241518946f9291a`;
- clean checkout;
- target: `AMD Radeon 8060S Graphics (RADV STRIX_HALO)`;
- 3 process repeats.

Frozen-gate result:

- current HWRT complete dynamic boundary: 5989.474 us;
- rigid-instance UPDATE: 1952.891 us, 67.39% improvement, 4.21% traversal regression;
- rigid-instance BUILD: 2011.499 us, 66.42% improvement, 7.45% traversal regression;
- both policies pass the fixed promotion gate;
- their boundary medians are within the fixed 5% tie band;
- therefore the fixed selection rule chooses **TLAS UPDATE**.

Final result:
`research/lanes/lane-e-dynamic-geometry/results/002-hwrt-rigid-instance.md`.
