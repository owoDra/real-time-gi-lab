# Lane E — dynamic geometry architecture

Issue: #15

Lane E continues from I001 without changing the accepted A001 producer/schema,
natural append order, or C001 per-probe sparse-hash storage contract unless an
experiment explicitly tests such a change.

The research question is whether geometry ownership can be separated by geometry
class so rigid motion stops paying world-space geometry maintenance that should
be represented by instance transforms.

## Geometry classes

Evidence is recorded separately for:

- static world geometry;
- rigid dynamic objects;
- deforming/skinned-like geometry;
- topology-changing geometry.

Rigid and deforming results must never be averaged into one "dynamic" result.

## Experiment sequence

1. E001 — dynamic ownership decomposition
2. E002 — HWRT rigid instance architecture
3. E003 — software object-local architecture
4. E004 — deforming/topology-changing boundary
5. E005 — integration replay and architecture decision

Normal research iterations commit directly to this branch. Other research
branches are not merged into Lane E during measurement.


## Final decision

Lane E is complete.

Accepted dynamic-geometry ownership model:

- static world: immutable static-owned acceleration data;
- rigid objects:
  - HWRT: immutable object-local BLAS + TLAS instance transform/UPDATE;
  - software: immutable object-local StrataBrick + conservative quantized
    Micro BVH8 + explicit instance traversal;
- stable-topology deforming/skinned-like objects:
  - HWRT: update only the object's geometry and object-local BLAS, then TLAS
    UPDATE;
  - software: maintain/repack/upload only the object's local
    StrataBrick/quantized Micro BVH8 and instance bounds;
- topology-changing objects: object-local rebuild boundary; no measured
  topology-changing performance claim.

E005 integrated replay retained the dynamic wins while all stable-regime and
memory guards passed. Both final HWRT and final software ownership candidates
are accepted.

Final evidence:
`research/lanes/lane-e-dynamic-geometry/results/005-integration-replay.md`.
