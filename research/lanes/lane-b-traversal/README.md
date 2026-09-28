# Lane B — geometry traversal

Issue: #11
Branch: `research-lane-b-traversal`

Mission: determine which traversal architecture best serves Split RC gather rays
under realistic dynamic-scene maintenance costs. StrataBrick is a candidate, not
a requirement.

## Current checkpoint — B001 ready for target run

The shared `traceRay(origin, direction, tMax) -> Hit` contract and brute-force
reference are implemented. GPU-independent correctness controls cover sparse,
dense and vertical scenes, static/moving geometry, static/shifted camera, and
50 m / 200 m finite GI ranges.

Provisional retention after the CPU control checkpoint:

- **software BVH:** retain as the simple software baseline;
- **raw sparse-grid DDA:** do not promote as a standalone final candidate;
- **hierarchical StrataBrick-derived:** retain for the main comparison because
  segment/BVH pruning + localized rebuild/refit is a materially different
  hypothesis from raw DDA alone;
- **HWRT/TLAS:** retain only if the target Vulkan probe reports support, then
  validate the same Hit semantics before timing.

This is not a winner decision. CPU control timings and historical StrataBrick
results are bring-up evidence only. Final promotion requires target-GPU
measurement and replay against Lane A's representative producer stream.

## Next decision gate

1. run the B001 target artifact on the intended GPU;
2. confirm zero correctness mismatches and record HWRT availability;
3. conclude B001 and update its result/index/Issue #11;
4. bring up the surviving GPU candidates with full build/refit/rebuild/update,
   traversal, persistent memory and scratch memory accounting;
5. repeat the architectural decision on Lane A's producer stream before selecting
   any final traversal approach.
