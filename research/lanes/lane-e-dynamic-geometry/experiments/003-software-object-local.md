# E003 — software object-local rigid ownership

Status: protocol frozen before implementation and target timing

## Question

Can the accepted software fallback stop paying world-space StrataBrick membership,
segment rebuild, packing, hierarchy upload, and rigid geometry upload when a rigid
object only changes its instance transform?

E001 showed that the current combined-software moving-rigid path is dominated by
CPU hierarchy maintenance rather than traversal:

- complete dynamic boundary: about 103 ms;
- hierarchy rebuild: about 80 ms;
- packing: about 15.9 ms;
- geometry transfer: about 1.16 ms GPU;
- traversal: about 0.26 ms.

E003 tests whether ownership, not another incremental rebuild heuristic, is the
correct boundary for rigid software geometry.

## Workload

Use the exact E001/E002 `moving-rigid` selection and translation semantics.

The source rigid-object triangles remain immutable. The target frame applies the
same translation as instance state. The accepted A001 producer surface update
remains world-space and is retained deliberately so E003 changes only the
software traversal ownership boundary.

Do not use deforming/skinned geometry in E003. Geometry whose object-space
vertices change belongs to E004.

## Object-local frame

The accepted scene loader currently exposes world-space triangles. For this
translation-only experiment, the source frame of the selected instance is the
object-local frame: source triangle coordinates remain immutable, and the target
instance transform is the E001 translation.

This is sufficient to test rigid ownership without reconstructing glTF source
node transforms. E003 must not claim rotation, scale, skinning, or deformation
coverage from this translation-only evidence.

## Variants

Measure three variants in the same target session.

1. **current-software**
   - existing `combined-software` path;
   - world-space moved triangles;
   - current StrataBrick membership update;
   - changed segment rebuild/refit;
   - quantized Micro BVH8 repack;
   - hierarchy/geometry upload.

2. **rigid-instance-software-binary**
   - diagnostic ownership control;
   - immutable static-world StrataBrick hierarchy;
   - immutable rigid-object object-local StrataBrick hierarchy;
   - existing binary per-segment micro BVH;
   - explicit instance table containing world bounds and translation;
   - rays are culled by instance bounds and transformed into the selected
     object's local frame before local traversal;
   - no dynamic hierarchy mutation for rigid translation.

3. **rigid-instance-software-quantized**
   - promotion candidate;
   - same instance ownership and top-level instance table as the binary control;
   - immutable object-local StrataBrick + accepted B003 conservative quantized
     Micro BVH8 payload for each ownership partition;
   - same shared Hit semantics and deterministic tie-breaking;
   - no dynamic hierarchy mutation for rigid translation.

The binary row is a mechanism control. It determines whether the ownership result
depends on B003 quantized traversal. It is not the promoted Lane E software
representation unless a later frozen experiment explicitly reopens the B003
representation decision.

## Instance-level top structure

E003 uses an explicit instance table rather than inserting rigid geometry into the
world StrataBrick on movement.

Each instance entry must contain enough state to:

- reject rays against its world-space bounds;
- transform a surviving world-space ray into local space;
- select the immutable local triangle/hierarchy payload;
- map local primitive indices back to the shared primitive/material/instance
  metadata contract.

For E003's one moving rigid object, the table contains the immutable static-world
entry and the rigid-object entry. The representation must not hard-code traversal
semantics that only work for exactly two entries, although the benchmark need not
invent additional moving objects.

## Required instrumentation

Record separately:

- surface update GPU time;
- instance-state update/upload wall and GPU time;
- geometry transfer wall/GPU time;
- membership update CPU time;
- hierarchy refit CPU time;
- hierarchy rebuild CPU time;
- packing CPU time;
- hierarchy upload GPU time;
- traversal-maintenance GPU time;
- traversal time;
- complete GPU time;
- dynamic update wall;
- complete dynamic boundary;
- persistent/transient/peak memory;
- instance count and moved primitive count.

The complete dynamic boundary remains:

`dynamic_update_wall_us + complete_gpu_us - traversal_maintenance_gpu_us`.

## Validation order

1. Clean Lane E checkout on the target machine.
2. Vulkan validation enabled for all three variants.
3. Require the existing I001 visibility/producer/Hit/storage/resolved/temporal
   correctness gates.
4. Require zero storage failures and zero Vulkan validation errors.
5. Require the same moving-rigid workload and moved primitive set for all rows.
6. Only then run 3 validation-disabled process repeats.

Target:
`AMD Radeon 8060S Graphics (RADV STRIX_HALO)`.

## Frozen E003 gates

These thresholds are fixed before implementation timing.

### Architecture-integrity gate

For both object-local rows, every accepted target row must report:

- `geometry_transfer_gpu_us == 0`;
- `membership_update_cpu_us == 0`;
- `hierarchy_refit_cpu_us == 0`;
- `hierarchy_rebuild_cpu_us == 0`;
- `packing_cpu_us == 0`;
- `hierarchy_upload_gpu_us == 0`;
- explicit nonnegative instance-state transfer timing;
- the same moved primitive count and workload identity as the current-software
  control.

Rigid geometry and local hierarchy payloads are immutable after setup.

### GPU accounting gate

For every object-local row:

`surface_update_gpu_us + instance_transfer_gpu_us + geometry_transfer_gpu_us + hierarchy_upload_gpu_us`

must match `traversal_maintenance_gpu_us` within
`max(2 us, 1% of traversal_maintenance_gpu_us)`.

The current-software control retains its existing E001 accounting.

### Promotion gate

The `rigid-instance-software-quantized` candidate is promotable only if all are
true:

- all validation/correctness/storage gates pass;
- architecture-integrity and GPU-accounting gates pass;
- median complete dynamic boundary is at least **50% lower** than the same-run
  current-software control;
- median traversal time is no more than **15% slower** than the same-run
  current-software control;
- median persistent allocation is no more than **1.25x** the same-run
  current-software control;
- no accepted A001, B003 Hit, or C001 storage semantics are weakened.

The 50% boundary requirement is intentionally strong: E001 attributes the large
majority of current rigid software maintenance to hierarchy rebuild and packing,
which object-local ownership is specifically intended to eliminate.

The 15% traversal and 1.25x memory limits prevent an update-only win from hiding a
materially worse fallback representation.

### Binary mechanism control

The binary object-local row is diagnostic only.

- If binary and quantized object-local rows both preserve architecture integrity,
  compare their traversal and memory to determine whether B003 quantization
  remains beneficial under object-local ownership.
- Failure of the binary row alone does not reject the quantized candidate.
- The quantized candidate still must independently satisfy every promotion gate.

## Decision boundary

E003 may promote only the rigid software ownership/update policy.

It must not claim that deforming/skinned or topology-changing geometry can avoid
local hierarchy maintenance. That boundary is E004.

E002's HWRT rigid result remains independent and already selected immutable
object-local BLAS + TLAS UPDATE. E003 must not change that decision.
