# E001 — dynamic ownership decomposition

Status: implementation in progress; target timing not yet run

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
