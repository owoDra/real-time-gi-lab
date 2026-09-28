# Lane C — radiance storage and locality

Issue: #12
Branch: `research-lane-c-storage-locality`

Mission: find a Split RC radiance representation and producer-side work
organization that preserves useful GPU locality without paying a full global
reorder.

Initial order:
1. keep per-probe open-addressed sparse hash as baseline;
2. implement a hashed contiguous brick-pool candidate;
3. implement a virtual/clipmap-style sparse candidate;
4. add a StrataBrick-inspired candidate only when structurally distinct;
5. test natural producer domains such as tile/cascade/brick only when they arise at source;
6. repeat final comparisons on the exact Lane A stream.

The M0 global scheduler remains diagnostic/fallback only. Its measured
large-workload reuse threshold was roughly five to six consumers.

## Current C001 decision

C001a structural/correctness bring-up retains the probe hash, hashed contiguous
brick pool, and virtual/clipmap representation for C001b GPU comparison.

The sparse occupancy control makes the brick representations consume about
twice the modeled persistent bytes of the probe hash, so brick storage has not
been treated as an automatic win. Medium/dense occupancy keeps the two brick
representations structurally plausible.

No StrataBrick-inspired fourth variant has been added because no concretely
distinct structure/update contract has yet been identified.

No storage representation is promoted. Target-GPU end-to-end measurements and
the exact Lane A producer stream remain mandatory before a final decision.
