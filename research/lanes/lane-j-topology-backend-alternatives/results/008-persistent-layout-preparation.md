# J003 persistent physical-slot layout checkpoint

Status: **IMPLEMENTATION READY — all-profile host replay pending**

This checkpoint follows the canonical Python/C++ transition parity PASS and the
v1.3 persistent-slot policy freeze.

Implemented:

- monotonic logical cluster IDs;
- reusable physical cluster slots;
- fixed 64-triangle / 127-micro-node slot capacity;
- lowest-free-slot reuse;
- power-of-two initial capacity;
- doubling growth only when active clusters exceed capacity;
- explicit resize old/new overlap accounting;
- release of both v1.2 empty-retired clusters and merge-source clusters;
- dirty-cluster-only slot rebuilds;
- upper BVH full rebuild on cluster-set changes;
- dirty-leaf-to-root unique ancestor refit when membership is unchanged;
- ownership-leak validation after every synchronization;
- synthetic regressions for resize overlap and merged-slot release.

No Vulkan persistent-buffer evidence is claimed yet.

## Host promotion gate

Run all frozen profiles through the physical-slot layout before implementing the
persistent Vulkan buffers:

```bash
mise run research:j003:persistent-layout
```

The gate fails closed on ownership leaks, invalid occupancy, slot collisions,
upper hierarchy errors, or capacity-policy violations.
