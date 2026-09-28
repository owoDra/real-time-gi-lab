# Lane B shaders

Traversal candidate research shaders live here.


B002 target shaders:

- `b002_software_bvh.comp.glsl` — software-BVH traversal;
- `b002_hierarchical.comp.glsl` — segment occupancy + per-segment BVH;
- `b002_hwrt.comp.glsl` — Vulkan ray query with candidates re-tested against
  the shared B001 Hit semantics instead of accepting API-specific hit policy.

The three paths use the same ray/triangle/Hit layouts. Candidate-specific
differences are limited to traversal acceleration lookup.
