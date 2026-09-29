# E005 — integrated ownership replay and final Lane E decision

Status: target validation passed; accepted timing ready

## Question

Do the E002–E004 ownership decisions remain beneficial when exposed as one
integrated Lane E architecture across stable, rigid-motion and deforming frames?

E005 is the final Lane E replay. It does not search for a new representation.
It checks that the selected policies compose without giving back stable-regime
performance, memory, correctness or the accepted dynamic gains.

## Integrated candidates

E005 exposes two final candidates.

1. **lane-e-final-hwrt**
   - static world in its own BLAS;
   - one selected dynamic-object BLAS;
   - rigid motion: immutable dynamic BLAS + TLAS instance UPDATE;
   - stable-topology deformation: update only the dynamic object's geometry and
     BLAS, then TLAS UPDATE;
   - static/camera/light: the same split ownership remains present but no dynamic
     maintenance occurs.

2. **lane-e-final-software**
   - static world in immutable object-owned StrataBrick + conservative quantized
     Micro BVH8;
   - selected dynamic object in a separate object-owned StrataBrick + quantized
     Micro BVH8;
   - rigid motion: instance-state update only;
   - stable-topology deformation: update/repack/upload only the dynamic object's
     local hierarchy and instance bounds;
   - static/camera/light: split ownership remains present but no dynamic
     maintenance occurs.

The stable replay deliberately keeps one idle dynamic object partitioned. This
tests the real ownership overhead instead of silently reverting to the old
single-world representation whenever the object is not moving.

## Controls

For every scenario compare against the accepted pre-Lane-E Integration controls:

- HWRT control: `combined-hwrt`;
- software control: `combined-software`.

E005 does not compare against vanilla software because the final decision is
about preserving the accepted HWRT-primary / B003-software-fallback structure.

## Scenarios

Replay exactly these five regimes:

1. `static`
2. `camera-motion`
3. `light-motion`
4. `moving-rigid`
5. `deforming-control`

Rigid and deforming evidence remain separate. E005 may summarize final ownership
but must not average rigid/deforming promotion gates into one dynamic score.

## Stable ownership selection

For `static`, `camera-motion` and `light-motion`, E005 uses the same
deterministic real Sponza object-selection procedure used by Lane E moving-rigid
experiments, but leaves its transform/geometry unchanged.

The object-selection cost is setup-only and is not part of frame timing. This is
a benchmark stand-in for a runtime's preclassified dynamic object ownership.

## Validation order

1. Clean Lane E checkout on the target machine.
2. Vulkan validation enabled for all 20 scenario/variant pairs.
3. Require existing I001 visibility/producer/Hit/storage/resolved/temporal gates.
4. Require zero storage failures and zero Vulkan validation errors.
5. Require control/candidate workload identity within each scenario.
6. Require the architecture-integrity rules below.
7. Only then run at least 3 validation-disabled process repeats.

Target:
`AMD Radeon 8060S Graphics (RADV STRIX_HALO)`.

## Architecture-integrity rules

### Stable scenarios

For both final candidates in static/camera/light:

- all dynamic-maintenance component timings must be zero;
- no geometry, BLAS, TLAS, hierarchy or instance update may occur.

Setup ownership is allowed and is reflected in persistent/peak memory.

### Moving rigid

Final HWRT must preserve E002 invariants:

- `geometry_transfer_gpu_us == 0`;
- `blas_update_us == 0`;
- instance transfer is explicitly measured;
- TLAS UPDATE is explicitly measured.

Final software must preserve E003 invariants:

- `geometry_transfer_gpu_us == 0`;
- membership/refit/rebuild/packing/hierarchy-upload timings are all zero;
- instance transfer is explicitly measured.

### Stable-topology deformation

Final HWRT must preserve E004 mechanism:

- changed object geometry transfer is non-zero;
- object BLAS update is non-zero;
- TLAS update is non-zero.

Final software must preserve E004 mechanism:

- changed local geometry transfer is non-zero;
- local hierarchy maintenance is non-zero;
- local quantized hierarchy upload is non-zero;
- instance-bounds transfer is non-zero.

## Accounting

Use the same per-path accounting definitions as E002–E004.

- rigid HWRT:
  `surface + instance + TLAS`;
- deforming HWRT:
  `surface + geometry + BLAS + TLAS`;
- rigid software:
  `surface + instance`;
- deforming software:
  `surface + geometry + instance + hierarchy upload`;
- stable scenarios: traversal-maintenance total must be zero.

Dynamic accounting tolerance remains:
`max(2 us, 1% of traversal_maintenance_gpu_us)`.

## Frozen final gates

All gates below are fixed before E005 timing.

### Correctness

Every validation and timing row must preserve:

- I001 quality pass;
- zero storage failures;
- shared Hit semantics;
- accepted A001 producer and C001 storage semantics.

Any correctness failure rejects the corresponding final candidate.

### Stable-regime guard

For each of static, camera-motion and light-motion independently:

- final HWRT median `complete_gpu_us` must be no more than **10% slower** than
  same-run `combined-hwrt`;
- final software median `complete_gpu_us` must be no more than **15% slower**
  than same-run `combined-software`.

No averaging may hide a regression in one stable regime.

### Dynamic-gain retention

The integrated candidates must still satisfy the earlier frozen promotion
thresholds against same-run controls:

- moving-rigid HWRT: complete dynamic boundary at least **20% lower** and
  traversal no more than **10% slower**;
- moving-rigid software: boundary at least **50% lower** and traversal no more
  than **15% slower**;
- deforming HWRT: boundary at least **5% lower** and traversal no more than
  **10% slower**;
- deforming software: boundary at least **40% lower** and traversal no more than
  **15% slower**.

### Memory guard

For every scenario independently:

- candidate persistent memory must be no more than **1.25x** same-run control;
- candidate peak-resident memory must be no more than **1.25x** same-run control.

### Final selection

- HWRT final ownership is accepted only if all HWRT correctness, architecture,
  stable, dynamic and memory gates pass.
- Software final ownership is accepted only if all software gates pass.
- One side may fail independently; do not average them.
- Lane E closes only after the result is published with explicit topology-change
  disposition.

## Topology-changing disposition

E005 does not invent topology-changing timing.

The final architecture classifies primitive-count/topology change as an
object-local rebuild boundary:

- rebuild only the changed object's BLAS or local software hierarchy/payload;
- rebuild/resize its instance-owned resources as needed;
- do not rewrite unrelated static-world or other object-owned structures.

This is a design boundary supported by E004's stable-topology contract checks,
not a measured topology-changing performance claim.


## Implementation checkpoint

E005 is implemented without changing the frozen gates.

Integrated runtime variants:

- `lane-e-final-hwrt`;
- `lane-e-final-software`.

Implementation behavior:

- static/camera/light keep one deterministic idle dynamic object partitioned so
  ownership traversal and memory overhead remain measurable while all frame
  dynamic-maintenance timings stay zero;
- moving-rigid routes final HWRT through E002 immutable BLAS + TLAS UPDATE and
  final software through E003 instance-only quantized ownership;
- deforming-control routes final HWRT through E004 object-local BLAS UPDATE and
  final software through E004 local StrataBrick/quantized maintenance;
- existing Integration controls remain unchanged;
- `run_e005.py` executes 20 validation pairs and a 5-scenario x 4-variant x
  repeat timing matrix;
- the runner independently enforces stable complete-GPU guards, prior frozen
  dynamic-gain thresholds, persistent and peak memory guards, architecture
  integrity, accounting, workload identity, quality and storage correctness.

Static self-review confirmed variant naming/parsing, setup, traversal bindings,
memory accounting, scenario-specific maintenance and dispatch are connected.
The assistant sandbox could not clone GitHub for a local build because external
DNS is unavailable; target `mise run build` remains the authoritative compile
check before validation.

No E005 target GPU result has been run or inferred.

Target validation command:

```bash
git checkout research-lane-e-dynamic-geometry
git pull
mise install
mise run research:check
mise run assets
mise run build
mise run research:record --lane lane-e-dynamic-geometry \
  --experiment 005-integration-replay \
  --command "python scripts/research/lane_e_dynamic_geometry/run_e005.py --build-dir build/release --validation-only"
```

Do not start accepted E005 timing until the validation artifact has been
inspected. The formal timing runner repeats the validation matrix.


## Target validation result

Accepted validation provenance:

- measurement commit: `5f1de18c031f7590c1514c9d262ea34f6bb1b58c`;
- branch: `research-lane-e-dynamic-geometry`;
- tree: clean;
- target: `AMD Radeon 8060S Graphics (RADV STRIX_HALO)`;
- validation pairs: 20;
- scenarios: static, camera-motion, light-motion, moving-rigid,
  deforming-control;
- all quality gates passed;
- all storage-failure counts were zero;
- same-workload checks passed;
- frozen GPU accounting gate passed;
- frozen architecture-integrity gate passed.

The E005 validation gate is satisfied. Accepted final timing may begin without
changing any frozen stable-regime, dynamic-gain, traversal or memory threshold.

Formal timing command:

```bash
git checkout research-lane-e-dynamic-geometry
git pull
mise install
mise run research:check
mise run assets
mise run build
mise run research:record --lane lane-e-dynamic-geometry \
  --experiment 005-integration-replay \
  --command "python scripts/research/lane_e_dynamic_geometry/run_e005.py --build-dir build/release --repeats 3"
```

The timing runner repeats the complete 20-pair validation matrix before
validation-disabled timing. Do not alter the frozen E005 gates after observing
timing.
