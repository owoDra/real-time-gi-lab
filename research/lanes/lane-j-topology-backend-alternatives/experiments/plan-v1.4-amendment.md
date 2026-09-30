# Lane J plan v1.4 amendment — conservative fp32 BVH pruning

Status: **frozen after retained correctness diagnosis and before rerun evidence**

The first persistent-Vulkan representative replay retained one exact-Hit
mismatch. Diagnostic replay proved that the CPU reference intersects both
competing primitives and that their distance difference is inside the frozen
B001 tie window:

- lower-ID primitive 262389: t = 1533.32068;
- higher-ID primitive 262932: t = 1533.29016;
- delta: 0.0305175781;
- frozen B001 tolerance at that distance: 0.0306658018.

The B001 contract therefore requires primitive 262389.

The Hit tolerance and tie rule are **not changed**.

## Correctness correction

BVH AABB pruning must be conservative with respect to the exact-Hit/tie
contract. The previous shader pruned against exactly

`best_t + hit_tolerance(best_t)`

using fp32 slab arithmetic. At the retained failure, only about 1.48e-4 world
units remained between the farther tie candidate and that mathematical limit,
which is smaller than a defensible accumulated fp32 slab-error allowance at a
~1533-unit ray distance.

Before rerun, freeze the following implementation rule:

- keep the exact triangle acceptance and B001 tie comparator unchanged;
- add a pruning-only fp32 roundoff guard based on
  `2 * gamma(3)`, where
  `gamma(3) = 3 * eps / (1 - 3 * eps)` and
  `eps = 2^-23`;
- expand only the positive AABB traversal distance limit by this factor;
- do not use the guard when comparing final triangle Hits;
- do not change the workload, ray set, topology sequence, Hit tolerance, or
  primitive-ID tie rule.

The guard is derived from floating-point operation error rather than tuned to
the retained ray. It changes only broad-phase conservativeness and may increase
node/triangle visits slightly.

If the unchanged exact-Hit gate still fails after this correction, the failure
must be diagnosed in exact triangle arithmetic/tie evaluation rather than
further widening AABB pruning ad hoc.
