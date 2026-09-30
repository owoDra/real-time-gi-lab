# Research program status

As of 2026-09-30, Lane A-H and Integration #13 are concluded. This document is the
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
6. Lane G resolved the transient-LBVH sparse-memory blocker without weakening
   correctness: hardened true-lifetime peak memory is below the frozen 3.0x
   vanilla ceiling in every required row. Production promotion is still blocked
   by timing repeatability.
7. Lane H attempted to establish a safe same-boundary topology-rebuild crossover
   protocol. Valid static controls failed the pre-frozen repeatability gate, so
   formal topology timing never became decision-valid. Lane H closes
   measurement-limited; no Lane E vs hardened-LBVH speed claim is made.

The main architectural blocker found by Integration #13 — world-space
moving-geometry maintenance — is solved by Lane E for rigid and
stable-topology-deforming geometry under its frozen gates. Lane G also removed
the deterministic sparse-memory blocker for hardened transient LBVH.

The remaining architecture question is still the topology-changing/high-churn
object-local rebuild backend, but the immediate program blocker is now
**measurement validity**: the target host has not yet demonstrated a safe
protocol capable of resolving the size of performance difference required by a
promotion gate. The next program phase separates measurement calibration from
architecture exploration so one cannot silently bias the other.

## Major findings

| Stage | Formal status | Program-level conclusion |
| --- | --- | --- |
| Lane A / #10 | Accepted | Natural GPU append order is a valid representative workload. Mean probe run is 8 and neighboring-tile adjacency is about 0.975 without a global reorder. |
| Lane B / #11 | Accepted | HWRT/TLAS is primary on the measured target. The selected software fallback is segment DDA/hash + conservative quantized Micro BVH8 at about 231 us representative mean; it remains materially slower than accepted HWRT. |
| Lane C / #12 | Accepted | Per-probe sparse hash is the current storage foundation. Clipmap showed dense/steady-state strengths but lost the complete exact-stream transition and sparse-memory trade-off. |
| Integration / #13 | Complete, no universal promotion | Static/camera/light strongly favored HWRT, while the old world-space moving-rigid path regressed. This isolated dynamic geometry ownership/maintenance as the next problem. |
| Lane D / #14 | Accepted final decision | No standalone producer replacement beat A001. D001 depth reuse is conditional integration evidence. D005 bounded-capacity/safe-overflow is retained policy evidence only. |
| Lane E / #15 | Accepted | Object-local ownership by update semantics passed final integrated stable, rigid, deforming and memory gates for both HWRT and software fallback. This is the current incumbent dynamic-geometry architecture. |
| Lane F / #16 | Complete, no promotion | Sorted grid is dominated by reference amplification/sort. Transient LBVH established strong mechanism evidence but exposed sparse-memory and repeatability blockers. |
| Lane G / #17 | Complete, deterministic hardening accepted | Hardened transient LBVH passes 60/60 deterministic correctness/workload rows; sparse-stress peak is 2.708583x vanilla and sparse-moving 2.699209x, resolving the former >3.0x blocker. Timing remains measurement-limited. |
| Lane H / #18 | Complete, measurement-limited | Safe timing methodology did not pass: even valid static controls failed frozen repeatability criteria. The topology-changing crossover was therefore not run and no backend was promoted. |

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
- hardened transient LBVH as a correctness/memory-qualified future mechanism
  candidate; production performance remains unproven.

### Rejected or not retained

- adding a global reorder solely to manufacture storage/traversal locality;
- D002/D003/D004 producer replacements;
- D005 tested implementation as the standalone producer;
- Lane F sorted two-level grid as the next dynamic-geometry direction;
- treating the old world-space update model as the universal dynamic ownership
  model.

### Unresolved

- whether a safe protocol on the target host can reliably distinguish a
  predeclared ~10% GPU-performance difference without power/clock forcing;
- which object-local backend is best for topology-changing/high-churn geometry;
- same-boundary crossover between Lane E object-local rebuild, hardened
  transient LBVH, and any structurally different topology backend;
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

## Lane G/H interpretation

Lane G changed the transient-LBVH conclusion materially:

- G001 identified the former sparse peak as a lifetime/ownership problem rather
  than unavoidable LBVH payload growth;
- G003 retained immutable-static-HWRT lifetime scheduling/release;
- G004 passed all 16 frozen semantic cases;
- G005 passed all 60 deterministic same-boundary correctness/workload/memory
  rows;
- sparse-stress hardened peak is **2.708583x** run-local vanilla, **12.16%**
  lower than unchanged LBVH;
- sparse-moving hardened peak is **2.699209x** vanilla, **15.72%** lower than
  unchanged LBVH.

This resolves the deterministic memory blocker but does not promote LBVH because
G002 established no safe decision-valid timing protocol.

Lane H then isolated the remaining topology-changing question. H001 used a
pre-frozen all-or-nothing repeatability gate. Valid static controls already
failed that gate across all four implementations, independently of the later
discovered dynamic-harness semantic defect. H003 was therefore forbidden and
Lane H closed **measurement-limited**.

The correct interpretation is not "Lane E is faster" and not "LBVH is faster".
The target environment has not yet supported a decision-valid comparison at the
required effect size.

## Measurement methodology issue

Timing repeatability is now a **program-level first-class research problem**.

Evidence from Lane F, G and H shows:

- timing excursions affect controls as well as transient candidates;
- longer warmup alone is insufficient;
- paired/counterbalanced automatic-DPM timing was also insufficient in G002;
- H001 static controls still failed tighter pre-frozen repeatability criteria;
- architecture-specific conclusions must not be drawn from unstable medians.

The forced AMDGPU performance-state experiment attempted in G002c caused host
instability and is permanently excluded from the active program. No future lane
may require `profile_peak`, `power_dpm_force_performance_level` writes,
privileged clock/power sysfs manipulation, or equivalent forced power-state
controls.

The next methodology lane must calibrate the measurement system against
**known-delta controlled workloads before measuring competing architectures**.
In particular it should test whether batched same-process paired measurements
can reliably detect predeclared 5%, 10%, and 20% controlled GPU-work changes.
A new architecture timing campaign may use the resulting protocol only if that
calibration passes its frozen gate.

## Evidence chain

Detailed source-of-truth documents:

- Lane A: [A001 representative producer](https://github.com/owoDra/phos-gi-lab/blob/research-lane-a-split-rc/research/lanes/lane-a-split-rc/results/001-representative-producer.md)
- Lane B: [B002 exact-stream traversal](https://github.com/owoDra/phos-gi-lab/blob/research-lane-b-traversal/research/lanes/lane-b-traversal/results/002-lane-a-exact-stream-traversal.md), [B003 wide software traversal](https://github.com/owoDra/phos-gi-lab/blob/research-lane-b-traversal/research/lanes/lane-b-traversal/results/003-wide-software-traversal.md)
- Lane C: [C001 final storage decision](https://github.com/owoDra/phos-gi-lab/blob/research-lane-c-storage-locality/research/lanes/lane-c-storage-locality/results/001-storage-baselines.md)
- Integration: [I001 dynamic end-to-end](https://github.com/owoDra/phos-gi-lab/blob/research-integration-gate/research/integration/results/001-dynamic-end-to-end.md)
- Lane D: [final cross-lane producer decision](https://github.com/owoDra/phos-gi-lab/blob/research-lane-d-producer-optimization/research/lanes/lane-d-producer-optimization/results/006-final-cross-lane-decision.md)
- Lane E: [E005 final ownership replay](https://github.com/owoDra/phos-gi-lab/blob/research-lane-e-dynamic-geometry/research/lanes/lane-e-dynamic-geometry/results/005-integration-replay.md)
- Lane F: [F002 builder](https://github.com/owoDra/phos-gi-lab/blob/research-lane-f-dynamic-geometry-alternatives/research/lanes/lane-f-dynamic-geometry-alternatives/results/002-pure-gpu-transient-lbvh-builder.md), [F006 geometry-class controls](https://github.com/owoDra/phos-gi-lab/blob/research-lane-f-dynamic-geometry-alternatives/research/lanes/lane-f-dynamic-geometry-alternatives/results/006-geometry-class-crossover-controls.md), [F007 final replay](https://github.com/owoDra/phos-gi-lab/blob/research-lane-f-dynamic-geometry-alternatives/research/lanes/lane-f-dynamic-geometry-alternatives/results/007-final-integration-replay.md)
- Lane G: [G002 repeatability diagnosis](https://github.com/owoDra/phos-gi-lab/blob/research-lane-g-transient-lbvh-hardening/research/lanes/lane-g-transient-lbvh-hardening/results/002-timing-repeatability-diagnosis.md), [G005 deterministic replay](https://github.com/owoDra/phos-gi-lab/blob/research-lane-g-transient-lbvh-hardening/research/lanes/lane-g-transient-lbvh-hardening/results/005-final-deterministic-replay.md)
- Lane H: [H001 safe timing result](https://github.com/owoDra/phos-gi-lab/blob/research-lane-h-topology-rebuild-crossover/research/lanes/lane-h-topology-rebuild-crossover/results/001-safe-timing-methodology.md), [H004 final decision](https://github.com/owoDra/phos-gi-lab/blob/research-lane-h-topology-rebuild-crossover/research/lanes/lane-h-topology-rebuild-crossover/results/004-final-decision.md)

Issues #9-#18 provide frozen plans and cross-lane context; lane result documents
take precedence for concluded experiment outcomes.

## Next research priority

Two new lanes should fork from this synthesis checkpoint and remain logically
separate.

### Lane I / #19 — measurement calibration

Lane I is architecture-neutral. Its purpose is to determine whether the target
host can safely and reproducibly resolve effect sizes relevant to architecture
promotion.

It must use known-delta controlled GPU workloads before any candidate
architecture. The primary direction is batched, same-process, paired and
counterbalanced timing, with fresh-process replication retained as a separate
axis. GPU timestamp and complete CPU wall boundaries remain separately reported.

Lane I must freeze its calibration matrix and pass/fail criteria before target
execution. It may not use forced GPU power/clock states or post-hoc filtering.

Valid final outcomes:

- **calibrated protocol accepted** — a specific safe protocol detects the frozen
  controlled deltas with the required repeatability and may be reused by later
  architecture lanes;
- **measurement floor established** — only larger effect sizes are reliably
  resolvable, so future promotion thresholds must not claim finer resolution;
- **target timing unsuitable** — safe timing cannot support the intended
  architecture ranking on this host.

### Lane J / #20 — topology-changing backend alternatives

Lane J explores topology-changing/high-churn object-local backends at the data
structure and update-model level while preserving Lane E ownership boundaries.

It must not merely retune the current transient LBVH. The initial research phase
must consider structurally different families, including at least:

- object-local HWRT rebuild as the incumbent control;
- cluster/meshlet-local two-level structures where only dirty clusters rebuild;
- incremental subtree rebuild/refit hybrids;
- locality-bounded spatial or paged structures that avoid Lane F's global
  sort/reference-amplification failure mode;
- broad-phase representations only when an exact-triangle refinement stage
  preserves the shared exact Hit contract.

Lane J may perform literature review, deterministic workload design,
correctness, memory accounting, and GPU-independent implementation before Lane I
finishes. **Formal performance ranking is blocked until Lane I establishes an
accepted safe protocol**, and that protocol must be frozen into Lane J before
accepted target timing.

Lane E remains the incumbent throughout. Hardened transient LBVH remains one
candidate, not the assumed winner.

### Program sequencing

Lane I and Lane J may start in parallel because J's early research/design work
does not require decision-valid timing. The first formal architecture crossover
must wait for Lane I.

Lower-priority storage/renderer/capacity-policy follow-ups remain deferred unless
new evidence makes them the dominant blocker.
