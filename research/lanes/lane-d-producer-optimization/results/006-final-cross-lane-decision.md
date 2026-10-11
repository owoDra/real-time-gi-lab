# Lane D final cross-lane decision

Status: accepted final Lane D decision

## Dependency state

Issue #14 required the final Lane D decision to wait until Lane B and Lane C
completed their accepted A001-stream replay gates.

That dependency is now satisfied:

- Lane B #11 is closed with B002 accepted. Its primary decision is HWRT/TLAS,
  with hierarchical StrataBrick-derived traversal retained as the software
  fallback. B003 is an optional non-blocking follow-up.
- Lane C #12 is closed with C001 accepted. Its current storage baseline is the
  per-probe open-addressed sparse hash. Virtual clipmap remains conditional
  future work for denser or more residency-stable workloads.

The accepted A001 producer/schema remains unchanged.

## Lane D question

How much of A001's representative Split RC producer cost and memory can be
reduced without changing semantic work, manufacturing downstream locality, or
moving cost into an unmeasured stage?

## Final disposition of D001-D005

### D001 — renderer visibility reuse

Retain **renderer depth reuse** as an integration contract.

When renderer depth already exists, the incremental GI producer boundary can
skip the depth pass while preserving A001 work semantics.

This is an integration optimization, not a standalone A001 replacement. The
standalone comparison still has to include the renderer prerequisite cost.

Do not retain owner/surface-ID reuse under the tested D001 gate.

### D002 — visible-tile-driven emission

Rejected.

It materially reduced producer emit work in camera/light cases but missed the
fixed promotion gate in static and did not beat accepted A001 consistently.

Do not carry it into Integration #13.

### D003 — packed 64-bit one-pass owner selection

Rejected.

The exact 64-bit atomic path preserved semantics but was slower than both the
matched two-pass control and accepted A001.

Keep A001's two-pass visibility semantics.

### D004 — workgroup-prefix allocation

Rejected.

It reduced global reservation atomics by about 59%, but shared-memory
prefix/barrier overhead outweighed the contention saved.

Keep per-visible-owner allocation for the accepted producer contract.

### D005 — bounded stream capacity / safe overflow

Do not promote the tested owner-slot implementation as the final producer path.

Retain the **policy result**:

- 1,280 owner blocks reduced work-stream capacity by 86.11%;
- resident producer memory fell by 71.94%;
- forced 512-owner overflow was safely clamped;
- full-capacity retry restored correctness.

The tested implementation failed the fixed direct-A001 gate because
light-motion E2E regressed 6.31% (>5%).

The memory policy is therefore suitable for a later integrated implementation
only if Integration #13 can remove the staged overhead and still account for
real overflow allocation/retry latency.

## Final stable producer contract

Lane D does **not** promote a new standalone producer architecture.

For Integration #13, the stable producer contract remains:

1. **A001 schema v1 and semantic work are authoritative.**
2. Use A001's natural GPU append order; do not add a post-generation global
   sort/reorder.
3. Keep the accepted surface-source producer semantics.
4. Keep two-pass depth + deterministic owner selection for the standalone
   reference.
5. Keep per-visible-owner work/output reservation in the standalone reference.
6. Preserve A001 block-internal cascade-major/ray-minor order.
7. Keep correctness gates for visibility owner, work semantics, counts,
   overflow, and resolve.
8. When the real renderer already owns an equivalent depth result, Integration
   #13 may evaluate the D001 **depth-reuse incremental contract** without
   charging that renderer work twice.
9. D005's bounded-capacity/safe-overflow policy may be reimplemented inside the
   integrated pipeline, but it is not part of the accepted standalone producer
   until the complete integration gate passes.

## Cross-lane integration handoff

The evidence-backed architecture to take into Integration #13 is:

| subsystem | evidence-backed handoff |
| --- | --- |
| Producer | accepted A001 producer/schema v1 |
| Renderer reuse | D001 depth reuse, conditional on equivalent existing renderer depth |
| Traversal | HWRT/TLAS primary |
| Traversal fallback | hierarchical StrataBrick-derived software traversal |
| Radiance storage | per-probe open-addressed sparse hash |
| Storage alternate | virtual clipmap only for future denser/stable regimes |
| Stream ordering | A001 natural append order; no global reorder |
| Capacity policy | D005 bounded capacity + safe overflow as non-promoted integration research |

This combination is a **handoff candidate**, not a claim that the complete GI
architecture is superior.

## Why no standalone Lane D replacement is promoted

Issue #14's decision gate required a producer strategy to beat accepted A001 by
a repeatable, material end-to-end margin while preserving semantics and keeping
memory/synchronization costs competitive.

No D001-D005 standalone implementation satisfies that full requirement.

The strongest useful Lane D findings are orthogonal:

- D001 shows where real renderer integration can remove duplicate visibility
  work.
- D005 shows that A001's worst-case stream reservation can be cut drastically
  with a safe overflow contract.

Neither result justifies rewriting the accepted A001 standalone baseline.

## Integration #13 guidance

Integration #13 can now begin from stable lane decisions.

It should test at minimum:

- accepted A001 standalone producer versus renderer-depth-reuse integration;
- HWRT/TLAS primary traversal plus hierarchical software fallback;
- per-probe sparse hash storage;
- the unchanged A001 natural stream order;
- optional bounded stream capacity only as a separately accounted integrated
  variant.

The integration gate must still measure complete GPU frame time, memory,
quality/error, update latency, dynamic geometry, changing light, camera motion,
sparse/dense regimes, and large/vertical stress.

Do not promote the combined GI architecture merely because its isolated lane
choices won their own gates.

## Final Lane D decision

**Keep accepted A001 as the standalone producer contract.**

Carry D001 renderer-depth reuse into Integration #13 as the only retained
producer execution optimization.

Carry D005 bounded-capacity/safe-overflow only as an integration memory-policy
candidate.

D002, D003, and D004 remain rejected.

Lane D #14 is complete.
