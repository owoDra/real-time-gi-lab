# E001 — dynamic ownership decomposition

Status: complete

## Question

Which parts of the current I001 moving-frame boundary dominate cost before the
geometry-ownership architecture is changed?

E001 is diagnostic. It does not promote object-local HWRT or object-local
StrataBrick. Those hypotheses begin in E002/E003 only after this baseline is
recorded.

## Baseline

Use the I001 implementation inherited from completed Integration #13:

- A001 schema v1 and natural append order;
- C001 per-probe sparse hash;
- vanilla software BVH;
- combined HWRT/TLAS;
- B003 segment DDA/hash + conservative quantized Micro BVH8.

The accepted I001 result remains historical evidence. E001 adds instrumentation;
it must not reinterpret old I001 timings as if they already contained the new
breakdown.

## Workloads

Measure the geometry classes separately.

### rigid-moving

Use the existing I001 moving-rigid selection: a real Sponza instance is
translated far enough to cause world-space StrataBrick membership changes.
This intentionally exposes the current ownership weakness.

### deforming-control

Use the same class of real Sponza instance, but apply a deterministic smooth
non-affine vertex warp. The warp is not representable by one instance transform,
so it is a control for geometry that genuinely requires local geometry
maintenance. It is a mechanism-isolation control, not a production skinning
benchmark.

Do not average rigid-moving and deforming-control.

## Required timing decomposition

Record as separate fields wherever applicable:

- surface update GPU transfer;
- traversal geometry transfer;
- HWRT BLAS update;
- HWRT TLAS update;
- StrataBrick membership dirty processing;
- hierarchy refit;
- hierarchy rebuild;
- hierarchy occupancy/bounds maintenance;
- software packing/quantization;
- hierarchy GPU upload;
- software-BVH rebuild;
- traversal;
- producer;
- storage update;
- invalidation;
- resolve;
- complete moving frame;
- complete dynamic-update wall time.

For E001 summaries, the serial complete dynamic-frame boundary is
`dynamic_update_wall_us + complete_gpu_us - traversal_maintenance_gpu_us`.
The subtraction avoids counting the separately timed dynamic-maintenance GPU
work twice because it is already included in both the synchronous update wall
and I001's `complete_gpu_us`.

Setup remains separate from per-frame maintenance.

## Correctness and timing order

1. Build from a clean Lane E checkout.
2. Run all candidate/workload pairs with Vulkan validation enabled.
3. Require the existing I001 visibility, producer, Hit, sparse-storage, resolved
   output, temporal and storage gates to pass.
4. Only then run validation-disabled repeated timing.
5. Keep raw child artifacts and parent Git provenance.

Target GPU:
`AMD Radeon 8060S Graphics (RADV STRIX_HALO)`.

Target commands use mise.

## Frozen E001 interpretation gates

These gates are fixed before target timing.

- measurement-integrity gate: every validation pair passes with zero existing
  I001 correctness/runtime/storage failures;
- accounting gate: the sum of named GPU dynamic-maintenance components must
  match `traversal_maintenance_gpu_us` within max(2 us, 1%) for every accepted
  row;
- repeat gate: 3 process repeats are required for accepted timing;
- dominant-maintenance component: >=40% of median traversal-maintenance GPU time;
- material-maintenance component: >=10% of median traversal-maintenance GPU time;
- if no component reaches 40%, classify the maintenance cost as distributed
  rather than inventing a single bottleneck.

The 40%/10% thresholds classify the E001 result only. They are not promotion
thresholds for E002/E003.

## Decision after E001

E001 must end with separate rigid/deforming breakdowns for:

1. current I001 vanilla software;
2. current I001 HWRT;
3. current I001 B003 software fallback.

The next experiment should attack the measured ownership cost, not whichever
mechanism appears easiest to optimize.

No architecture is promoted from E001 alone.


## Target validation checkpoint

Implementation and static review are complete enough for the first target gate.
No target GPU timing has been run or inferred.

Run from the target machine:

```bash
git checkout research-lane-e-dynamic-geometry
git pull
mise install
mise run research:check
mise run assets
mise run build
mise run research:record --lane lane-e-dynamic-geometry \
  --experiment 001-dynamic-ownership-decomposition \
  --command "python scripts/research/lane_e_dynamic_geometry/run_e001.py --build-dir build/release --validation-only"
```

Do not start accepted timing until this validation artifact has been inspected.
The timing runner will repeat the same validation matrix before timing as an
additional guard.


## Target validation result

Accepted validation artifact:

`out/research/lane-e-dynamic-geometry/001-dynamic-ownership-decomposition/20260929T075511Z`

Validation provenance:

- measurement commit: `be6eec379889228075e28836bbcf05aa210f6047`;
- branch: `research-lane-e-dynamic-geometry`;
- tree: clean;
- target: `AMD Radeon 8060S Graphics (RADV STRIX_HALO)`;
- validation pairs: 6;
- all quality gates passed;
- all storage-failure counts were zero;
- research runner return code: 0.

The validation gate is satisfied. Accepted timing may now begin without changing
the frozen E001 thresholds.

Formal timing command:

```bash
git checkout research-lane-e-dynamic-geometry
git pull
mise install
mise run research:check
mise run assets
mise run build
mise run research:record --lane lane-e-dynamic-geometry \
  --experiment 001-dynamic-ownership-decomposition \
  --command "python scripts/research/lane_e_dynamic_geometry/run_e001.py --build-dir build/release --repeats 3"
```

The timing runner repeats the validation matrix before validation-disabled
timing. Do not alter the E001 accounting/dominance gates after observing timing.


## Accepted timing result

Accepted timing completed at measurement commit
`1fa902d48a8d6e693384f5911033683ebd342a00` with 3 process repeats for each
of the six variant/workload groups. All validation, storage and frozen GPU
accounting gates passed.

Result:
`research/lanes/lane-e-dynamic-geometry/results/001-dynamic-ownership-decomposition.md`

E001 classifies rigid HWRT geometry transfer as dominant (58.61% of median GPU
maintenance), while the B003 rigid path is dominated by world-space hierarchy
rebuild (79999.349 us) and packing (15867.764 us). E002 therefore targets
immutable rigid BLAS + TLAS instance motion; E003 targets object-local software
ownership. Deforming remains separate for E004.
