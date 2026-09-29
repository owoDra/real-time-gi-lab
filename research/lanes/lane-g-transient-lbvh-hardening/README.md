# Lane G — transient LBVH hardening

Issue: #17

This lane starts from `research@1ab3c09f62fc6778aa598a791c4c1a6f720d75f9`.

The first experiment is **G001 memory ownership and lifetime census**. Until
G001 concludes, changes in this lane may add instrumentation and validation only;
they must not shrink buffers, alias scratch, change capacities, or otherwise
optimize the F007 transient-LBVH architecture.

The copied integration/LBVH/grid sources in
`src/research/lane_g_transient_lbvh_hardening/` are an auditable snapshot of
the Lane-F F007 implementation used as the unchanged G001 baseline. Existing
Lane A/B/C source remains shared and unmodified.
