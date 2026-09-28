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


## Progress — D002 visible-tile emission rejected (2026-09-29)

D002 target-GPU evidence at measurement commit
`844123281ff72b5c3b6dea38ca69732b5ca2e00b` passed semantic correctness but did
not pass the predeclared promotion gate.

The tile source reduced dispatch invocations from 262,241 surfaces to 9,216
tiles and materially reduced emit cost. Camera-motion and light-motion improved
strongly, but static median producer-total improvement versus the matched
surface control was only 7.37% (<10%), and direct accepted-A001 static E2E
regressed 1.59%.

Decision:

- do not retain visible-tile emission for later composition;
- keep D001 depth reuse as the only retained Lane D mechanism so far;
- continue to D003 one-pass owner selection from the A001-style surface
  producer path.

The observed neighboring-tile locality improvement is recorded as a natural
source-order effect only and is not used to override the performance gate.


## Progress — D003 packed one-pass owner selection rejected (2026-09-29)

D003 preserved the A001 semantic counts and overflow stayed zero, but the exact
64-bit packed `atomicMin` path was slower than both the matched staged two-pass
control and accepted A001.

Three-repeat medians showed packed producer-total regressions versus accepted
A001 of 22.48% static, 10.37% camera-motion, and 11.05% light-motion.

Decision:

- do not retain packed 64-bit one-pass visibility selection;
- keep A001 two-pass visibility semantics;
- D001 depth reuse remains the only retained Lane D composition mechanism;
- continue to D004 work-allocation contention.

The uploaded CSV did not embed commit/artifact identity, so the D003 result
record marks measurement identity as unverified rather than inventing it.
