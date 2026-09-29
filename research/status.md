# Research program status

As of 2026-09-30, Lane A-G and Integration #13 are concluded. This document is the
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
6. Lane G hardens the Lane-F transient LBVH mechanism enough to remove its
   deterministic sparse-memory blocker without changing A001/Hit/C001 semantics.
   The hardened path passed final correctness and memory replay, but Lane G did
   not establish a safe decision-valid timing protocol. It therefore does not
   replace Lane E or change the primary traversal/ownership decisions.

The main architectural blocker found by Integration #13 — world-space
moving-geometry maintenance — remains solved by Lane E for rigid and
stable-topology-deforming geometry under its frozen gates. Lane G establishes
that transient LBVH can fit the memory/correctness boundary after lifetime
hardening, but whether it is preferable as an object-local rebuild backend for
high-churn/topology-changing geometry remains a **performance question**, not a
correctness or sparse-memory question.

## Major findings

| Stage | Formal status | Program-level conclusion |
| --- | --- | --- |
| Lane A / #10 | Accepted | Natural GPU append order is a valid representative workload. Mean probe run is 8 and neighboring-tile adjacency is about 0.975 without a global reorder. |
| Lane B / #11 | Accepted | HWRT/TLAS is primary on the measured target. The selected software fallback is segment DDA/hash + conservative quantized Micro BVH8 at about 231 us representative mean; it remains materially slower than accepted HWRT. |
| Lane C / #12 | Accepted | Per-probe sparse hash is the current storage foundation. Clipmap showed dense/steady-state strengths but lost the complete exact-stream transition and sparse-memory trade-off. |
| Integration / #13 | Complete, no universal promotion | Static/camera/light strongly favored HWRT, while the old world-space moving-rigid path regressed. This isolated dynamic geometry ownership/maintenance as the next problem. |
| Lane D / #14 | Accepted final decision | No standalone producer replacement beat A001. D001 depth reuse is conditional integration evidence. D005 bounded-capacity/safe-overflow is retained policy evidence only. |
| Lane E / #15 | Accepted | Object-local ownership by update semantics passed final integrated stable, rigid, deforming and memory gates for both HWRT and software fallback. This is the current incumbent dynamic-geometry architecture. |
| Lane F / #16 | Complete, no promotion | Sorted grid is dominated by reference amplification/sort. Transient LBVH established mechanism evidence but exposed sparse-memory and timing-repeatability blockers. |
| Lane G / #17 | Complete, measurement-limited | Hardened transient LBVH resolves the sparse-memory blocker and passes deterministic correctness/integration replay. Decision-valid timing remains unresolved, so Lane E stays incumbent and no production promotion is made. |

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

Lane E changes ownership/update semantics, not this traversal decision. Lane G
also produces no formal replacement because timing remains inconclusive, so the
Lane B disposition remains current.

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
- hardened transient LBVH as a retained mechanism candidate whose deterministic
  memory/correctness blocker is resolved but whose production timing case is
  still unproven.

### Rejected or not retained

- adding a global reorder solely to manufacture storage/traversal locality;
- D002/D003/D004 producer replacements;
- D005 tested implementation as the standalone producer;
- Lane F sorted two-level grid as the next dynamic-geometry direction;
- treating the old world-space update model as the universal dynamic ownership
  model.

### Unresolved

- a safe decision-valid timing protocol for transient-LBVH/control comparisons;
- whether hardened transient LBVH is performant specifically for
  topology-changing/high-churn object-local rebuilds;
- same-boundary timing crossover between the accepted Lane E incumbent and
  hardened transient LBVH;
- topology-changing performance under the Lane E ownership model;
- whether a future representative dense workload justifies reopening clipmap
  storage;
- cross-GPU generality beyond the measured AMD Radeon 8060S target;
- final renderer integration of D001 and any future D005-style capacity policy.

## Lane E and hardened transient LBVH are not mutually exclusive

Lane E answers **who owns geometry and which update semantics apply**. Lane G
hardens **how a transient dynamic subset can be rebuilt/traversed and kept
within the memory boundary**. Those remain different architectural axes.

The current evidence continues to support Lane E as the ownership architecture.
Lane G shows that hardened transient LBVH is semantically valid across rigid,
stable-topology deforming and topology-changing test classes and no longer fails
the frozen sparse-memory ceiling.

A composition in which transient LBVH becomes an object-local rebuild backend
is therefore technically plausible, but it is not a promoted architecture.
G002 never produced a safe decision-valid timing protocol and G005 deliberately
made no Lane-E replacement claim.

Therefore the program does **not** adopt transient LBVH into Lane E yet.

## Lane F → Lane G interpretation

The important Lane F conclusion was not "LBVH was too slow".

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

Lane G resolves the memory half of that conclusion. G001 showed that the sparse
failure was dominated by static-HWRT setup lifetime overlap rather than LBVH
payload itself. G003a/G005 then reduced true peak memory enough to pass the
frozen 3.0x ceiling: sparse-stress is 2.708583x vanilla and sparse-moving is
2.699209x vanilla.

The remaining blocker is decision-valid timing repeatability. G002 showed the
instability also affects controls, rejected warmup-only and auto-DPM paired
protocols, and closed without an accepted safe timing protocol.

The sorted grid keeps its stronger negative disposition because reference
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

Lane G confirmed these rules rather than resolving them: G002 could not freeze a
safe accepted timing protocol. Any future timing-based promotion study must
first establish a new protocol without GPU power/clock manipulation that risks
host stability.

## Evidence chain

Detailed source-of-truth documents:

- Lane A: [A001 representative producer](https://github.com/owoDra/phos-gi-lab/blob/research-lane-a-split-rc/research/lanes/lane-a-split-rc/results/001-representative-producer.md)
- Lane B: [B002 exact-stream traversal](https://github.com/owoDra/phos-gi-lab/blob/research-lane-b-traversal/research/lanes/lane-b-traversal/results/002-lane-a-exact-stream-traversal.md), [B003 wide software traversal](https://github.com/owoDra/phos-gi-lab/blob/research-lane-b-traversal/research/lanes/lane-b-traversal/results/003-wide-software-traversal.md)
- Lane C: [C001 final storage decision](https://github.com/owoDra/phos-gi-lab/blob/research-lane-c-storage-locality/research/lanes/lane-c-storage-locality/results/001-storage-baselines.md)
- Integration: [I001 dynamic end-to-end](https://github.com/owoDra/phos-gi-lab/blob/research-integration-gate/research/integration/results/001-dynamic-end-to-end.md)
- Lane D: [final cross-lane producer decision](https://github.com/owoDra/phos-gi-lab/blob/research-lane-d-producer-optimization/research/lanes/lane-d-producer-optimization/results/006-final-cross-lane-decision.md)
- Lane E: [E005 final ownership replay](https://github.com/owoDra/phos-gi-lab/blob/research-lane-e-dynamic-geometry/research/lanes/lane-e-dynamic-geometry/results/005-integration-replay.md)
- Lane F: [F002 builder](https://github.com/owoDra/phos-gi-lab/blob/research-lane-f-dynamic-geometry-alternatives/research/lanes/lane-f-dynamic-geometry-alternatives/results/002-pure-gpu-transient-lbvh-builder.md), [F006 geometry-class controls](https://github.com/owoDra/phos-gi-lab/blob/research-lane-f-dynamic-geometry-alternatives/research/lanes/lane-f-dynamic-geometry-alternatives/results/006-geometry-class-crossover-controls.md), [F007 final replay](https://github.com/owoDra/phos-gi-lab/blob/research-lane-f-dynamic-geometry-alternatives/research/lanes/lane-f-dynamic-geometry-alternatives/results/007-final-integration-replay.md)
- Lane G: [G001 memory census](research/lanes/lane-g-transient-lbvh-hardening/results/001-memory-ownership-lifetime-census.md), [G002 timing diagnosis](research/lanes/lane-g-transient-lbvh-hardening/results/002-timing-repeatability-diagnosis.md), [G003 memory hardening](research/lanes/lane-g-transient-lbvh-hardening/results/003-memory-reduction-candidates.md), [G004 integration hardening](research/lanes/lane-g-transient-lbvh-hardening/results/004-integration-hardening.md), [G005 final deterministic replay](research/lanes/lane-g-transient-lbvh-hardening/results/005-final-deterministic-replay.md)

Issues #9-#17 provide the frozen plans and later cross-lane context; lane result
documents take precedence for concluded experiment outcomes.

## Post-Lane-G research priorities

Lane G is complete. There is no mandatory follow-on lane required to validate
its deterministic result.

The remaining high-value questions are:

1. **Timing methodology** — only if production promotion of transient LBVH is
   still desired, establish a safe repeatable same-boundary timing protocol
   first. Do not reuse the abandoned G002c power-state experiment.
2. **Topology-changing object-local crossover** — after a safe timing protocol
   exists, compare hardened transient LBVH against a run-local Lane E
   object-local rebuild implementation for topology-changing/high-churn
   geometry. This is the most direct unresolved architectural comparison.
3. **Renderer integration** — independently evaluate D001 depth reuse and any
   future D005-style capacity policy in a real renderer boundary.
4. **Cross-GPU generality** — all current primary decisions remain measured on
   the AMD Radeon 8060S target and should not be generalized without new
   evidence.

The evidence-backed production architecture remains:

- A001 natural-order producer;
- HWRT/TLAS primary traversal;
- B003 software fallback;
- C001 per-probe sparse hash;
- Lane E geometry-class-specific object-local ownership/update model.

Hardened transient LBVH is retained as research mechanism evidence, not as a
replacement for that incumbent architecture.

## Lane G final outcome

Issue #17 completed its frozen G001-G005 sequence.

- G001: explained the sparse-memory failure.
- G002: timing diagnosis completed; no safe decision-valid protocol accepted.
- G003: immutable-static-HWRT lifetime hardening retained.
- G004: 16/16 semantic/integration cases passed.
- G005: 60/60 deterministic same-boundary rows passed correctness/workload and
  frozen memory gates.

Final status: **mechanism retained; deterministic memory/correctness hardening
accepted; production promotion measurement-limited**.

No historical and run-local timing values are mixed into a promotion gate, no
Lane E replacement claim is made, and the abandoned GPU power-state experiment
must not be rerun.
