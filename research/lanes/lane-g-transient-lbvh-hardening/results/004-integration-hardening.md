# G004 — Integration hardening

Status: **implementation complete; target-GPU evidence pending**

Candidate: `hardened-transient-lbvh`.

G004 contains no new optimization. It revalidates the single G003a memory
candidate across the frozen 16-case semantic matrix.

## Required evidence

Every case must pass exact validation for:

- A001 visibility/producer semantics;
- exact Hit semantics against the software reference;
- traversal runtime checks;
- C001 missing/leaked/stale/resolved semantics;
- zero storage failures;
- zero producer overflow.

Dynamic workloads must actually report moved primitives and dynamic groups.
The deforming class must report deformed primitives, and the topology-changing
class must report topology replacements.

## Geometry-class separation

The moving-rigid class replay keeps these rows separate:

- representative rigid;
- rigid large/few;
- rigid small/many32;
- stable-topology deforming;
- topology-replace25 high churn.

No result from one class is generalized to another.

## Stress coverage

Stable and moving sparse/dense/large/vertical workloads are included.

## Timing

Timing is diagnostic-only. G002 closed without a safe accepted protocol, so G004
does not produce a timing PASS/FAIL and does not use GPU power/clock
manipulation.

## Result

Pending target-GPU artifacts.
