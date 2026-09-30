# Lane J plan v1.5 amendment — robust per-axis slab far bound

Status: **frozen after v1.4 rerun failed unchanged**

The v1.4 rerun reproduced the exact same retained mismatch and traversal
statistics. Therefore enlarging only the final AABB distance limit did not
address the rejected path.

The retained ray still proves:

- primitive 262389 and primitive 262932 both intersect in the CPU reference;
- their delta is inside the frozen B001 tie window;
- primitive 262389 is therefore the required Hit;
- GPU runtime-error counters remain zero.

## Correctness correction

Keep all B001 exact-Hit semantics unchanged.

The remaining broad-phase risk is fp32 slab arithmetic itself. For each axis,
after sorting the two parametric plane intersections into `near_axis` and
`far_axis`, expand only the positive far bound by the already-frozen
`1 + 2 * gamma(3)` factor before intersecting it into the running interval.

This is the standard conservative form needed to avoid rejecting a box when
roundoff makes a computed far plane slightly too near. It is structurally
different from v1.4, which only enlarged the caller's overall traversal limit.

Rules:

- exact triangle intersection unchanged;
- Hit absolute/relative tolerance unchanged;
- primitive-ID tie rule unchanged;
- topology/rays/workload unchanged;
- no profile- or ray-specific epsilon;
- retain the v1.4 final-limit guard as an additional conservative bound;
- if v1.5 still fails, add explicit shader-side primitive-visit diagnostics
  before any further numerical change.
