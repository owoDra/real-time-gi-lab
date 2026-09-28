# Lane C — radiance storage and locality

Issue: #12
Branch: `research/lane-c-storage-locality`

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
