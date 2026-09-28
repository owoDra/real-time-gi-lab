# Lane B — geometry traversal

Issue: #11
Branch: `research-lane-b-traversal`

Mission: determine which traversal architecture best serves Split RC gather rays
under realistic dynamic-scene maintenance costs. StrataBrick is a candidate, not
a requirement.

## Current checkpoint — B001 target CSV inspected; hardened rerun required

The shared `traceRay(origin, direction, tMax) -> Hit` contract and brute-force
reference are implemented. A target-system CSV covering sparse, dense and
vertical scenes, static/moving geometry, static/shifted camera, and 50 m / 200 m
finite GI ranges completed **48 candidate rows × 65,536 rays/row with zero
mismatches**.

The trace direction strengthens the provisional retention gate:

- **software BVH:** retain as the simple software baseline;
- **raw sparse-grid DDA:** do not promote as a standalone final candidate;
- **hierarchical StrataBrick-derived:** retain because segment/BVH pruning +
  localized rebuild/refit is a materially different hypothesis from raw DDA;
- **HWRT/TLAS:** retain only if the hardened target Vulkan probe reports
  unambiguous support, then validate the same Hit semantics before timing.

The received CSV is diagnostic rather than the formal B001 result. Final
self-review hardened repeat/provenance capture, dynamic-update boundaries,
build/rebuild boundaries, contract smoke tests, and multi-device HWRT probing.
GPU-independent `-Werror` and ASan+UBSan controls still pass with zero
correctness mismatches.

CPU control timings and historical StrataBrick results remain bring-up evidence
only. Final promotion still requires GPU candidate implementation and replay
against Lane A's representative producer stream.

## Next decision gate

1. rerun B001 through `mise run research:record` with the current hardened harness;
2. ingest corrected `b001-controls.csv`, `metadata.json`, and
   `hwrt-probe.json`;
3. conclude B001 and update its result/index/Issue #11;
4. bring up the surviving GPU candidates with full build/refit/rebuild/update,
   traversal, persistent-memory and scratch-memory accounting;
5. repeat the architectural decision on Lane A's producer stream before
   selecting any final traversal approach.
