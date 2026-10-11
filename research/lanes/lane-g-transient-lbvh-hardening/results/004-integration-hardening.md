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

Measurement commit: `9b2f339814c4afa57fcbe3ea72edcc54ee2f69db`.

All **16/16** frozen cases passed exact semantic/correctness gates on
`AMD Radeon 8060S Graphics (RADV STRIX_HALO)` with validation enabled.

Across every row:

- visibility mismatches = 0;
- producer semantic errors = 0;
- hit mismatches = 0;
- traversal runtime errors = 0;
- missing/leaked probes = 0;
- stale storage slots = 0;
- resolved-output mismatches = 0;
- storage failures = 0;
- overflow = 0.

Geometry-class execution was also confirmed rather than inferred:

- representative rigid: 796 moved primitives, 1 dynamic group;
- rigid large/few: 796 moved primitives, 1 group;
- rigid small/many32: 796 moved primitives, **32 groups**;
- stable-topology deforming: 796 moved + **796 deformed** primitives;
- topology-changing/high-churn: 796 moved + **199 replaced** primitives.

All sparse/dense/large/vertical stable and moving stress cases passed.

### Decision

**G004 integration hardening PASS. Proceed to G005 deterministic same-boundary
replay.**

Timing remains explicitly inconclusive under G002 and was not used in this
decision. No GPU power/clock manipulation occurred.
