# Research program status

As of 2026-09-30, Lane A-F and Integration #13 are concluded. This document is the
program-level synthesis on the `research` branch. Detailed experiment results,
raw-artifact provenance, and lane-local decisions remain canonical in each lane's
`results/` documents and are not duplicated here.

## Status vocabulary

- **Accepted**: decision-valid evidence passed the frozen gate.
- **Rejected**: decision-valid evidence failed the frozen gate.
- **Conditional**: useful evidence is retained only for a stated regime or
  integration boundary.
- **Inconclusive**: the frozen gate could not be evaluated reliably.
- **Diagnostic-only**: useful mechanism evidence that must not be promoted to a
  formal architecture decision.
- **Invalidated**: superseded evidence that must not be reused for decisions.

## Executive summary

The strongest evidence-backed architecture is no longer "one world-space
dynamic structure". It is a composition of stable contracts established across
the completed lanes:

1. Keep the accepted A001 GPU visibility-driven Split RC producer, schema v1,
   and its natural append order. The measured stream already has strong
   short-range locality; no post-generation global sort/reorder has been
   justified.
2. On the measured AMD Radeon 8060S target, use HWRT/TLAS as the primary
   traversal path. Where HWRT is unavailable, use Lane B's selected
   segment-DDA/hash + conservative quantized Micro BVH8 fallback.
3. Keep C001 per-probe open-addressed sparse hash as the current radiance-storage
   foundation. Virtual/clipmap storage remains a conditional candidate for
   demonstrably denser or more residency-stable workloads.
4. Use Lane E's geometry-class-specific object-local ownership/update model:
   immutable static ownership; transform-only rigid instances; object-local
   UPDATE for stable-topology deformation; object-local rebuild boundaries for
   topology changes.
5. Keep A001 as the standalone producer contract. Renderer depth reuse is a
   conditional integration optimization; bounded-capacity/safe-overflow is
   retained as a memory-policy result, not as a promoted producer.
6. Lane F does not replace Lane E. The sorted two-level grid is not a viable
   follow-up under the measured workload. Transient LBVH remains promising, but
   its sparse-memory failure and unresolved timing repeatability prevent formal
   promotion.

The main architectural blocker found by Integration #13 — world-space
moving-geometry maintenance — is solved by Lane E for rigid and
stable-topology-deforming geometry under its frozen gates. The main unresolved
question is now whether a transient LBVH can become a useful **conditional
object-local rebuild backend**, especially for high-churn/topology-changing
geometry, while fitting the memory boundary and producing repeatable timing
evidence.

## Major findings

| Stage | Formal status | Program-level conclusion |
| --- | --- | --- |
| Lane A / #10 | Accepted | Natural GPU append order is a valid representative workload. Mean probe run is 8 and neighboring-tile adjacency is about 0.975 without a global reorder. |
| Lane B / #11 | Accepted | HWRT/TLAS is primary on the measured target. The selected software fallback is segment DDA/hash + conservative quantized Micro BVH8 at about 231 us representative mean; it remains materially slower than accepted HWRT. |
| Lane C / #12 | Accepted | Per-probe sparse hash is the current storage foundation. Clipmap showed dense/steady-state strengths but lost the complete exact-stream transition and sparse-memory trade-off. |
| Integration / #13 | Complete, no universal promotion | Static/camera/light strongly favored HWRT, while the old world-space moving-rigid path regressed. This isolated dynamic geometry ownership/maintenance as the next problem. |
| Lane D / #14 | Accepted final decision | No standalone producer replacement beat A001. D001 depth reuse is conditional integration evidence. D005 bounded-capacity/safe-overflow is retained policy evidence only. |
| Lane E / #15 | Accepted | Object-local ownership by update semantics passed final integrated stable, rigid, deforming and memory gates for both HWRT and software fallback. This is the current incumbent dynamic-geometry architecture. |
| Lane F / #16 | Complete, no promotion | Sorted grid is dominated by reference amplification/sort. Transient LBVH has strong mechanism evidence, but sparse peak memory exceeds 3.0x vanilla and final timing remains inconclusive after the permitted rerun. |

Representative values above are anchors only. Exact per-case numbers and raw
artifact provenance remain in the lane result documents.

## Current evidence-backed architecture

### Producer and work ordering

**Accepted**

- A001 GPU visibility-driven Split RC producer/schema v1.
- Natural append order.
- No CPU sort or post-producer global reorder.
- Standalone reference keeps the A001 visibility/owner semantics.

**Conditional**

- D001 renderer-depth reuse when an equivalent renderer depth result already
  exists. The renderer prerequisite must not be hidden in standalone
  comparisons.

**Not promoted**

- D002 visible-tile emission.
- D003 packed atomic64 one-pass owner selection.
- D004 workgroup-prefix allocation.
- D005's tested bounded owner-slot implementation.

D005's bounded-capacity + safe-overflow **policy** remains useful future
integration evidence, but only if normal-case overhead and real retry/allocation
costs pass a new integrated gate.

### Traversal

**Primary on the measured target**

- HWRT/TLAS.

**Software fallback**

- segment DDA/hash top level;
- conservative quantized Micro BVH8 per segment.

Lane E changes ownership/update semantics, not this traversal decision. Lane F
produced no formal replacement, so the Lane B disposition remains current.

### Radiance storage

**Current foundation**

- per-probe open-addressed sparse hash.

**Conditional future candidate**

- virtual/clipmap storage if a later representative workload is materially
  denser and/or maintains residency long enough that window transitions are
  infrequent.

A new clipmap study should require new workload evidence. C001 already showed
that synthetic dense advantages do not automatically survive the complete
representative transition boundary.

### Dynamic geometry ownership

Lane E is the current incumbent:

- **static**: immutable static-owned acceleration data;
- **rigid**:
  - HWRT: immutable object-local BLAS + instance transform + TLAS UPDATE;
  - software: immutable object-local StrataBrick + conservative quantized Micro
    BVH8 + explicit instance traversal;
- **stable-topology deforming/skinned-like**:
  - HWRT: update only the changed object's local geometry/BLAS, then TLAS UPDATE;
  - software: maintain/repack/upload only the changed object's local hierarchy
    and instance bounds;
- **topology-changing**: object-local rebuild boundary; unrelated structures
  remain untouched.

The topology-changing rule is an accepted architectural boundary, **not** an
accepted topology-changing performance result.

## Accepted, conditional, rejected, unresolved

### Accepted

- A001 producer/schema/natural ordering.
- HWRT/TLAS primary traversal on the measured target.
- B003 conservative quantized software fallback.
- C001 per-probe sparse hash.
- Lane E object-local ownership/update semantics for static, rigid and
  stable-topology deforming geometry.

### Conditional

- D001 renderer-depth reuse.
- D005 bounded-capacity/safe-overflow policy.
- virtual/clipmap storage in dense/residency-stable regimes.
- transient LBVH as a future mechanism candidate.

### Rejected or not retained

- adding a global reorder solely to manufacture storage/traversal locality;
- D002/D003/D004 producer replacements;
- D005 tested implementation as the standalone producer;
- Lane F sorted two-level grid as the next dynamic-geometry direction;
- treating the old world-space update model as the universal dynamic ownership
  model.

### Unresolved

- whether transient LBVH can pass sparse-memory and repeatability gates;
- whether transient LBVH is useful specifically for topology-changing/high-churn
  object-local rebuilds;
- same-boundary crossover between the accepted Lane E incumbent and hardened
  transient LBVH;
- topology-changing performance under the Lane E ownership model;
- whether a future representative dense workload justifies reopening clipmap
  storage;
- cross-GPU generality beyond the measured AMD Radeon 8060S target;
- final renderer integration of D001 and any future D005-style capacity policy.

## Lane E and Lane F are not mutually exclusive

Lane E answers **who owns geometry and which update semantics apply**. Lane F
tests **how a dynamic subset can be rebuilt/traversed each frame**. Those are
different architectural axes.

The current evidence supports Lane E as the ownership architecture. A hardened
transient LBVH could still fit *inside* that architecture, for example as the
object-local rebuild mechanism for topology-changing/high-churn objects.

That composition is only a hypothesis today. F006's topology/deformation
mechanism evidence is diagnostic because its formal timing campaign remained
inconclusive. F007 also cannot be compared numerically to E005 as a promotion
gate: the campaigns use different measurement boundaries/controls and F007 has
unstable required rows.

Therefore the program does **not** adopt transient LBVH into Lane E yet.

## Lane F interpretation

The important Lane F conclusion is not "LBVH was too slow".

- Corrected F002 Nrep=796 builder median is about 0.10 ms and repeatable.
- F006/F007 provide favorable mechanism-level LBVH evidence across multiple
  dynamic classes.
- F007 diagnostic moving-rigid median is about 1.47 ms, but that row and/or its
  comparator are not decision-valid for formal promotion.
- F007 hard sparse-memory gates fail:
  - sparse-stress: 3.0836x vanilla;
  - sparse-moving: 3.2025x vanilla.
- F007 still contains 23 unstable variant/scenario rows after the one permitted
  identical rerun.

The formal conclusion is therefore: **correctness established, architecture not
promoted; memory integration and measurement repeatability are the blockers**.

The sorted grid has a stronger negative disposition because reference
amplification and sorting dominate the dynamic builder and a decision-valid
large-world-moving gate also fails.

## Measurement methodology issue

Timing instability must now be treated as a **program-level methodology issue**,
not an LBVH-specific defect.

Lane F instability repeatedly appeared in run-local controls as well as
transient candidates. Consequently:

- unstable rows cannot be turned into PASS/FAIL by using their medians;
- no outlier deletion or post-hoc threshold changes are allowed;
- a methodology change must be frozen before the next accepted timing campaign;
- old and new timing protocols must not be mixed silently;
- when controls are unstable, architecture-specific causal claims are not
  justified.

The shared protocol records these rules. Lane G's timing diagnosis should
produce the evidence needed to freeze the next accepted timing protocol.

## Evidence chain

Detailed source-of-truth documents:

- Lane A: [A001 representative producer](https://github.com/owoDra/phos-gi-lab/blob/research-lane-a-split-rc/research/lanes/lane-a-split-rc/results/001-representative-producer.md)
- Lane B: [B002 exact-stream traversal](https://github.com/owoDra/phos-gi-lab/blob/research-lane-b-traversal/research/lanes/lane-b-traversal/results/002-lane-a-exact-stream-traversal.md), [B003 wide software traversal](https://github.com/owoDra/phos-gi-lab/blob/research-lane-b-traversal/research/lanes/lane-b-traversal/results/003-wide-software-traversal.md)
- Lane C: [C001 final storage decision](https://github.com/owoDra/phos-gi-lab/blob/research-lane-c-storage-locality/research/lanes/lane-c-storage-locality/results/001-storage-baselines.md)
- Integration: [I001 dynamic end-to-end](https://github.com/owoDra/phos-gi-lab/blob/research-integration-gate/research/integration/results/001-dynamic-end-to-end.md)
- Lane D: [final cross-lane producer decision](https://github.com/owoDra/phos-gi-lab/blob/research-lane-d-producer-optimization/research/lanes/lane-d-producer-optimization/results/006-final-cross-lane-decision.md)
- Lane E: [E005 final ownership replay](https://github.com/owoDra/phos-gi-lab/blob/research-lane-e-dynamic-geometry/research/lanes/lane-e-dynamic-geometry/results/005-integration-replay.md)
- Lane F: [F002 builder](https://github.com/owoDra/phos-gi-lab/blob/research-lane-f-dynamic-geometry-alternatives/research/lanes/lane-f-dynamic-geometry-alternatives/results/002-pure-gpu-transient-lbvh-builder.md), [F006 geometry-class controls](https://github.com/owoDra/phos-gi-lab/blob/research-lane-f-dynamic-geometry-alternatives/research/lanes/lane-f-dynamic-geometry-alternatives/results/006-geometry-class-crossover-controls.md), [F007 final replay](https://github.com/owoDra/phos-gi-lab/blob/research-lane-f-dynamic-geometry-alternatives/research/lanes/lane-f-dynamic-geometry-alternatives/results/007-final-integration-replay.md)

Issues #9-#17 provide the frozen plans and later cross-lane context; lane result
documents take precedence for concluded experiment outcomes.

## Next research priority

Issue #17 / Lane G remains the highest-value next lane, but it should be
**amended before implementation** rather than executed unchanged.

The core G001/G002 ordering is correct:

1. **G001 memory ownership/lifetime census first**. Explain the deterministic
   sparse 3.0836x/3.2025x failures before optimizing.
2. **G002 timing-repeatability diagnosis second**. Architecture remains
   unchanged while isolating process/warmup/order/clock/allocator/driver/query
   effects.
3. Freeze a new accepted timing protocol from G002 **before** any decision-valid
   optimization timing.
4. Only then implement memory changes justified by G001.

Before Lane G implementation starts, amend #17 so that its final decision also:

- includes the accepted **Lane E incumbent as a run-local comparator** where
  practical, not only historical E005 numbers;
- allows a **conditional object-local transient rebuild** result for
  topology-changing/high-churn geometry instead of requiring the only useful
  outcome to be rigid-primary replacement;
- preserves the distinction between rigid, stable-topology deforming and
  topology-changing classes;
- freezes any revised memory/timing gates before accepted target timing.

This does not require a different lane before G. It changes Lane G from
"retry Lane F until it promotes" into "explain the two real blockers, then test
whether transient LBVH adds value beyond the accepted Lane E architecture".

## Conditions to start Issue #17

Lane G implementation should start only after:

1. #17 is amended with the post-synthesis incumbent/comparison rules above.
2. Its branch is created from the post-synthesis `research` checkpoint.
3. G001/G002 remain diagnostic-first; no memory tuning is performed before the
   byte-accurate census.
4. The accepted timing protocol is frozen from G002 before performance-driven
   G003/G005 decisions.
5. Any Lane E comparison uses the same run-local boundary if it participates in
   a formal promotion gate.

Lower-priority follow-ups — dense-regime storage, D001 renderer integration, and
D005 capacity policy — should wait unless new evidence shows they are the next
dominant blocker.
