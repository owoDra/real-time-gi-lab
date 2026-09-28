# Lane B — geometry traversal

Issue: #11
Branch: `research-lane-b-traversal`

Mission: determine which traversal architecture best serves Split RC gather rays
under realistic dynamic-scene maintenance costs. StrataBrick is a candidate, not
a requirement.

## Current checkpoint — B001 accepted

B001 is concluded as the Lane B semantic/correctness and candidate-retention
checkpoint.

Accepted target rerun:

- artifact:
  `out/research/lane-b-traversal/001-traversal-contract-and-controls/20260928T150111Z/`;
- measurement commit: `52710fcbd372369fe58e68f6c29b39aa9924a3db`;
- 48 rows × 65,536 rays/row × 5 repeats;
- zero correctness mismatches.

Retention decision:

- **software BVH:** retain as the simple software baseline;
- **raw sparse-grid DDA:** do not promote as a standalone final architecture;
- **hierarchical StrataBrick-derived:** retain because segment/BVH pruning +
  localized rebuild/refit remains a distinct hypothesis;
- **HWRT/TLAS:** retain for explicit physical-device bring-up. The current probe
  is `ambiguous` because both RADV hardware and llvmpipe were enumerated; this
  is not an HWRT rejection.

The formal result is
`results/001-traversal-contract-and-controls.md`.

## Next decision gate

1. bring up the surviving GPU candidates under the shared Hit contract;
2. explicitly select/identify the target Vulkan physical device for HWRT and
   validate feature enablement before timing;
3. replay software BVH, hierarchical StrataBrick-derived traversal, and HWRT
   where proven available against Lane A's accepted representative producer
   stream;
4. include build/refit/rebuild/update, traversal, persistent memory, scratch
   memory, and correctness in the end-to-end decision;
5. document regime-specific winners instead of forcing one universal
   architecture if the evidence differs by scene regime.
