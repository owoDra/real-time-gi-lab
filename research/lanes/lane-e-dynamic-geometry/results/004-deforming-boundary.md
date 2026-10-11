# E004 — deforming geometry boundary

Status: accepted evidence; object-local stable-topology deformation promoted for HWRT and software

## Provenance

Accepted target measurement:

- branch: `research-lane-e-dynamic-geometry`;
- commit: `6a401247f91d3cb1b843a2c9c8cf0819414b9cc2`;
- dirty: false;
- target: `AMD Radeon 8060S Graphics (RADV STRIX_HALO)`;
- scenario: `deforming-control`;
- process repeats: 3;
- moved primitives: 796;
- segment membership changes: 148.

The supplied accepted evidence consists of `e004-results.csv`,
`e004-summary.json`, and `e004-validation-summary.json`. No outer
`research:record` artifact path was supplied with the accepted files, so this
result does not invent one.

## Validation

The validation-first matrix passed for all four variants:

- all quality gates passed;
- all storage-failure counts were zero;
- the same deforming workload was used by every row;
- the frozen GPU accounting gate passed;
- the frozen architecture-integrity gate passed.

The workload is stable-topology deformation. Primitive count and identity remain
unchanged; only the selected object's object-space vertices change.

## Accepted medians

| variant | complete dynamic boundary (us) | traversal (us) | persistent bytes |
| --- | ---: | ---: | ---: |
| current HWRT | 6006.888 | 83.960 | 72,554,048 |
| local deforming HWRT | **2126.678** | **84.721** | **72,554,496** |
| current software | 36903.098 | 326.260 | 27,554,640 |
| local deforming software quantized | **3464.600** | **290.632** | **27,695,664** |

### HWRT mechanism

Current scene-wide HWRT median maintenance includes:

- geometry transfer GPU: 2273.440 us;
- scene BLAS update: 420.519 us;
- TLAS update: 41.599 us.

The local candidate reduces those to:

- object-local geometry transfer GPU: 6.372 us;
- deforming-object BLAS update: 12.784 us;
- TLAS update: 43.683 us.

The accepted producer surface update remains approximately 1.09 ms and is not
removed by Lane E.

### Software mechanism

Current software deformation median CPU maintenance includes:

- membership update: 325.011 us;
- hierarchy refit: 8727.779 us;
- hierarchy rebuild: 5147.259 us;
- packing: 16506.761 us.

The local candidate reduces this to the selected object's hierarchy only:

- membership update: 393.270 us;
- hierarchy refit: 231.014 us;
- hierarchy rebuild: 220.715 us;
- packing: 340.301 us.

Its local hierarchy upload is 9.979 us GPU and instance-state upload is 4.288 us.

## Frozen-gate evaluation

### HWRT

Frozen requirements:

- at least 5% lower complete dynamic boundary;
- no more than 10% traversal regression;
- persistent memory no more than 1.25x control.

Observed:

- boundary improvement: **64.60%**;
- traversal regression: **0.91%**;
- persistent-memory ratio: **1.00001x**;
- promotion gate: **pass**.

### Software

Frozen requirements:

- at least 40% lower complete dynamic boundary;
- no more than 15% traversal regression;
- persistent memory no more than 1.25x control.

Observed:

- boundary improvement: **90.61%**;
- traversal change: **-10.92%** (faster);
- persistent-memory ratio: **1.00512x**;
- promotion gate: **pass**.

HWRT and software pass independently; no averaging is used.

## Decision

Promote for stable-topology deforming/skinned-like geometry:

- **HWRT:** immutable static-world BLAS + update-enabled object-local deforming
  BLAS + TLAS update;
- **software fallback:** immutable static-world object-local
  StrataBrick/quantized payload + deforming-object local
  StrataBrick/quantized Micro BVH8 maintenance + instance traversal.

This preserves the E002/E003 rigid decisions. Rigid motion remains transform-only;
deformation pays real local geometry/hierarchy maintenance.

## Topology-changing boundary

E004 does **not** promote UPDATE for topology-changing geometry.

A primitive-count or topology change invalidates the stable-topology update
contract. The required policy is an **object-local rebuild** of the changed
object's BLAS or software local hierarchy/payload, while unrelated static and
other object-owned structures remain untouched.

No topology-changing timing is inferred from E004.

## Handoff to E005

E005 must replay the integrated final ownership architecture across:

- static;
- camera motion;
- light motion;
- moving rigid;
- stable-topology deforming.

It must verify that the accepted dynamic wins survive integration without
material stable-regime or memory regressions before Lane E is closed.
