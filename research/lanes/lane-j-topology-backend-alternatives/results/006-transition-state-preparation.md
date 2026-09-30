# J003 transition-state implementation checkpoint

Status: **IMPLEMENTATION READY — canonical parity evidence pending**

After the representative target-GPU traversal PASS, Lane J now contains a C++
persistent cluster transition state matching the frozen v1.1/v1.2 rules:

- stable cluster IDs;
- batched delete/change removal;
- empty-cluster retirement before reassignment;
- minimum AABB surface-area expansion assignment;
- deterministic Morton split at the 64-triangle hard maximum;
- deterministic nearest-cluster merge below 24 when combined <=48;
- unaffected-cluster identity preservation;
- structural counters matching the canonical CPU gate vocabulary.

A C++ canonical replay executable and an independent Python parity checker were
added. Promotion to persistent GPU transition updates is blocked until the C++
rows match the existing canonical Python `j003-cpu-structural.json` for:

- cluster count;
- dirty cluster count;
- rebuilt triangle count;
- split count;
- merge count;
- empty-cluster retirement count;
- unaffected-cluster rebuild count;
- occupancy min;
- occupancy max.

This gate is CPU-only and does not introduce timing evidence.

## Gate command

```bash
mise run research:j003:transition-parity
```

The task builds the host contract and transition replay, replays the frozen
`medium-global-representative` sequence, and fails closed on any row/field
difference from the canonical Python structural artifact.

After PASS, proceed to persistent GPU slots, dirty-only micro-BVH uploads,
upper refit/rebuild, and allocation-lifetime/old-new-overlap accounting.
