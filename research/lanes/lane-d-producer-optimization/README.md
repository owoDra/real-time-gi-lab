# Lane D — producer optimization

Issue: #14
Branch: `research-lane-d-producer-optimization`

Mission: reduce the accepted A001 representative Split RC producer's required
GPU time and memory without changing GI work semantics or manufacturing
favorable downstream locality.

Lane D starts from the accepted A001 producer. The accepted A001 result and
schema are comparison inputs and are not rewritten by this lane.

## Boundaries

Lane D owns producer construction only:

- renderer visibility reuse and GI-only prerequisite accounting;
- source-side visible-tile emission;
- visibility owner-selection mechanisms;
- work-allocation contention;
- stream capacity, overflow, and producer scratch/peak memory.

Lane D does not own geometry traversal (Lane B), radiance storage (Lane C), or
post-generation global sorting/reordering. Natural ordering changes are allowed
only when they arise directly from a different source-emission mechanism and
must be measured.

## Experiment order

1. **D001 — visibility reuse boundary**: split A001 clear/visibility/emit/finalize
   costs and compare depth-only versus owner/surface-ID reuse.
2. **D002 — visible-tile-driven emission**: consume visible owners from the tile
   domain instead of rescanning every source surface.
3. **D003 — one-pass owner selection**: compare packed depth+owner selection
   against the accepted two-pass depth + deterministic-owner baseline.
4. **D004 — work allocation contention**: compare the current global block
   reservations with subgroup/workgroup prefix or bounded block reservation.
5. **D005 — stream capacity and overflow**: replace worst-case reservation only
   with measured high-water evidence and an explicit overflow/fallback path.

An experiment may be skipped when earlier evidence removes its premise.

## Promotion rule

No isolated kernel result promotes the lane. A final producer candidate must
beat accepted A001 by a repeatable material end-to-end margin on the target GPU,
preserve representative semantics, report natural ordering/locality changes,
and account for visibility, allocation, synchronization, stream memory, and
fallback costs.

## Progress — D001 visibility reuse accepted (2026-09-29)

Target-GPU D001 evidence at measurement commit `c083db8925d362c8c8df3cebc046fb2ff62fc2c9`
passed all semantic/correctness gates across static, camera-motion, and
light-motion.

Decision:

- retain renderer **depth reuse** as the composition contract for later Lane D
  experiments;
- do not retain owner/surface-ID reuse under D001's fixed standalone gate;
- promote no final producer architecture yet.

Depth reuse cut incremental producer cost by roughly 46% while remaining within
D001's 5% median standalone-regression ceiling in all three cases. Owner reuse
saved more incremental work, but camera-motion standalone E2E regressed 6.47%
and therefore missed the predeclared gate.

Next gate: D002 visible-tile-driven emission.
