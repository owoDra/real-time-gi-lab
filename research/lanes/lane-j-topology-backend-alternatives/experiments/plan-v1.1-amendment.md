# Lane J plan v1.1 amendment — clustered split semantics

Status: **frozen before J003 evidence**

This amendment corrects one internal inconsistency in `plan-v1.md`. No target
candidate timing or J003 evidence existed when this was written.

## Problem in v1

The v1 clustered candidate simultaneously said:

- insertion chooses a **non-full** cluster; and
- an **overflowing** dirty cluster is repartitioned.

Those rules make overflow/split effectively unreachable during ordinary
insertion and therefore leave the split path under-specified.

## Frozen replacement rule

Replace the J003 insertion/split wording with:

1. Every newly inserted/replaced triangle is assigned to the existing cluster
   that causes the smallest AABB surface-area expansion. Stable cluster ID is the
   tie breaker. **Capacity is not used to exclude a cluster during this
   assignment phase.**
2. Assignment is batched for the complete topology transition.
3. After assignment, every dirty cluster with more than **64 triangles** is
   deterministically repartitioned by object-space Morton median until every
   produced cluster has at most 64 triangles.
4. Repartitioned children target roughly **48 triangles** where the split allows
   it, but the 64-triangle maximum is the hard invariant.
5. A dirty cluster with fewer than **24 triangles** may merge with the stable
   nearest cluster only when the combined population is at most **48**.
6. Split/merge is local to the changed object. Unaffected clusters keep payload
   and allocation identity.
7. Every assignment, local Morton ordering, split, merge, allocation, upper
   rebuild/refit and synchronization remains inside the recurring update
   boundary.

This change is made for logical completeness, not after observing candidate
performance. All other `plan-v1.md` gates remain unchanged.
