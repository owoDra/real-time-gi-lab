# Lane J plan v1.2 amendment — empty-cluster lifetime and nearest metric

Status: **frozen after the first J003 CPU replay failed before producing evidence**

The first canonical J003 CPU replay exposed an undefined edge case in the
reference model: a topology transition could leave one or more dirty clusters
with zero triangles, and the merge-distance calculation attempted to form an
AABB for an empty cluster. The run terminated before a J003 structural artifact
or any candidate timing was produced.

This amendment resolves that missing lifetime rule without using performance
evidence.

## Frozen rules

1. Deletion/replacement removal is applied as a batch to the changed object's
   existing clusters.
2. Any cluster that is still empty **after removal and before reassignment** is
   retired deterministically before inserted/replaced triangles are assigned.
   Its cluster ID and payload/allocation identity are not reused by that
   transition.
3. Inserted/replaced triangles are then assigned under the v1.1 minimum AABB
   surface-area-expansion rule. If no cluster remains, a new stable cluster ID
   is allocated.
4. Empty clusters are not valid persistent cluster states and may not
   participate in split or merge candidate selection.
5. The v1.1 phrase **stable nearest cluster** is defined as minimum Euclidean
   distance between the two cluster AABB centers, with stable cluster ID as the
   tie breaker.
6. Retiring an empty cluster is a cluster-set structural change, but it is not
   counted as a merge. The CPU/GPU evidence must report empty-cluster
   retirements separately.
7. All retirement, assignment, split, merge, allocation and synchronization
   remains inside the recurring update boundary.

All v1/v1.1 correctness, memory and accounting gates remain unchanged.
