# Lane J plan v1.3 amendment — persistent GPU slot policy

Status: **frozen before persistent-GPU transition evidence**

The CPU/Python transition semantics are now fixed. Before collecting any
persistent-GPU transition memory or timing evidence, the device storage policy
is frozen because capacity growth and slot reuse directly affect the J003
memory gate.

## Frozen persistent slot rules

1. Logical cluster IDs remain monotonic and are never reused.
2. Device storage uses reusable **physical cluster slots**. Retiring a logical
   cluster releases its physical slot for a later logical cluster.
3. One physical slot reserves exactly:
   - 64 triangle payload records;
   - 127 binary micro-BVH nodes (the full binary-tree maximum for 64 leaves);
   - one cluster metadata record.
4. A cluster keeps its physical slot while its logical ID remains alive.
5. Unaffected clusters receive no triangle or micro-BVH payload upload.
6. New logical clusters take the lowest available physical slot.
7. Initial physical-slot capacity is the smallest power of two greater than or
   equal to the initial active cluster count.
8. When no physical slot is available, capacity doubles. No profile-specific
   reserve or future-snapshot lookahead is allowed.
9. Resize accounting includes simultaneous old/new allocation residency until
   migration is complete and the old allocation can actually be released.
10. Upper-BVH storage capacity is derived from physical-slot capacity as
    `2 * capacity - 1` nodes. Cluster-set changes rebuild the active upper BVH;
    membership-stable transitions refit the active upper hierarchy.
11. Unused physical slots are not traversable and do not count as active
    clusters, but their reserved bytes remain persistent memory.
12. Validation-ray/hit buffers remain validation-harness allocations and are
    reported separately from candidate persistent memory.

This amendment changes no J002 topology sequence, v1.1/v1.2 cluster semantics,
exact Hit contract, or J003 memory ceiling.
