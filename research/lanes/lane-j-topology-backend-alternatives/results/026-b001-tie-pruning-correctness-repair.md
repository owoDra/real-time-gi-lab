# J004 v7 — B001 tie-pruning correctness repair

Status: **READY FOR FULL TARGET REVALIDATION — formal timing not started**
Issue: #23

The v6 diagnostic proved that the retained 445 mismatches were all dynamic
nearest-hit/tie mismatches. Static traversal and static/dynamic merge were exact.

Self review then found a cross-path correctness defect: the J004 accelerated
CPU reference and several software traversal shaders pruned acceleration nodes
at `best_t`, while the frozen B001 semantic contract permits candidates through
`best_t + tolerance` before primitive-ID tie-breaking.

The correction is committed at
`0f9405c14d3d560ecdcb0373d246d32544cd1e96` and frozen by
`experiments/012-formal-execution-freeze-v7.json`.

Affected paths:

- CPU validation BVH;
- hardened transient LBVH traversal;
- vanilla software BVH traversal;
- B003 quantized traversal/DDA.

HWRT code is unchanged.

No accepted target timing exists. A complete hard-validation matrix must now be
rerun from the v7 identity. Only if all required correctness gates pass may the
unchanged formal timing campaign begin.
