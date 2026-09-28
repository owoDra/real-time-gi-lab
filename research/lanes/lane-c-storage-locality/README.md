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

After correcting the packed probe-hash slot model to 8 bytes (`uint32 key + uint32 payload`),
the sparse occupancy control makes the brick representations consume about four times
the modeled persistent bytes of the probe hash. Around 16 probes/brick the models are
near parity, while dense occupancy favors brick amortization. Brick storage is therefore
not treated as an automatic win.

No StrataBrick-inspired fourth variant has been added because no concretely
distinct structure/update contract has yet been identified.

C001b target-GPU candidate pruning is complete. The allocator-corrected rerun
passed all correctness gates and carries forward the per-probe sparse hash
baseline plus virtual/clipmap sparse storage as the two primary candidates.

The hashed contiguous brick pool remains implemented as a fallback diagnostic
control, but is not a primary candidate because virtual clipmap was lower in
persistent memory and stronger in the relevant end-to-end synthetic phases.

No storage representation is promoted. The exact Lane A producer stream remains
mandatory before a final decision.
