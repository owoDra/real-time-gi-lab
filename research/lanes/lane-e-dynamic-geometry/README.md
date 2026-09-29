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
