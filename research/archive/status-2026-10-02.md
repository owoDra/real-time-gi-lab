# Research program status

As of 2026-10-02, Lane A-K, Lane L, Lane M, Lane E timing revalidation, and
Integration #13 are concluded. Lane J closed measurement-limited before an
accepted timing methodology existed. Lane K provides the accepted GPU-primary
calibration on its calibration workload; Lane L separately establishes a 20%
detectable-effect floor for the heavier complete recurring boundary used by
Lane E #22 and Lane M #25. This document is the program-level synthesis on the
`research` branch. Detailed experiment results,
raw-artifact provenance, and lane-local decisions remain canonical in each lane's
`results/` documents and are not duplicated here.

## 2026-10-02 Lane M topology-backend crossover checkpoint

Lane M / #25 prospectively imported the Lane-L heavy-boundary capability and
completed the previously unresolved run-local comparison among the Lane-E
incumbent object-local rebuild boundary, Lane-G hardened transient LBVH, and the
Lane-J clustered two-level object-local BVH.

The accepted formal campaign retained all **6,144 timing rows across 192 fresh
processes**. GPU timestamp was the primary performance axis; CPU wall remained
diagnostic/health/provenance only. The frozen 20% decision floor, 1.25x
persistent/true-peak memory hard guard, exact correctness/identity gates, and
zero-rerun policy were preserved.

For every required mutating scenario on both primary and software tracks,
neither candidate qualified for promotion:

- topology-changing-object-local:
  - LBVH: 1.218883x primary, 1.272652x software;
  - clustered: 3.323954x primary, 2.690152x software;
- high-churn-global:
  - LBVH: 2.358234x primary, 2.181794x software;
  - clustered: 8.109075x primary, 6.477188x software;
- high-churn-local:
  - LBVH: 2.608696x primary, 1.889332x software;
  - clustered: 11.551081x primary, 8.255209x software.

All required candidate memory hard guards passed, so the rejection is driven by
complete-GPU performance rather than the frozen 1.25x memory limit. No
scenario/track promoted both candidates, therefore the conditional direct
LBVH-vs-clustered stage did not run.

The stable/no-change guard also rejects clustered on both tracks and LBVH on the
primary track. Software LBVH is only 1.040619x in that guard and remains
<20% difference / measurement-limited.

**Program conclusion:** retain the Lane-E incumbent object-local rebuild backend
for the frozen topology-changing/high-churn regimes on the measured target.
Hardened transient LBVH and clustered two-level BVH remain useful mechanism
evidence but are not production replacements under the decision-valid M001
boundary.

## 2026-10-01 Lane E heavy-boundary revalidation checkpoint

Lane L / #24 accepted the dual-context heavy-boundary protocol with GPU timestamp
primary, complete CPU wall diagnostic/health/provenance only, and a demonstrated
**20% minimum detectable effect** for the complete recurring boundary. The
Lane-K 5% calibration-workload floor was explicitly not transferred to this
heavier boundary.

Lane E follow-up / #22 then imported that protocol prospectively and retained all
5,120 timing rows across 160 fresh timing processes after a 20-process
correctness/identity validation gate.

Formal candidate/control complete-GPU ratios:

- moving-rigid HWRT: **0.330894x** (66.91% improvement);
- moving-rigid software: **0.519178x** (48.08% improvement);
- stable-topology-deforming HWRT: **0.331625x** (66.84% improvement);
- stable-topology-deforming software: **0.525108x** (47.49% improvement).

All four formal tracks pass the frozen >=20% improvement gate, exceed their
fresh-control noise envelopes, and have fully directional measured pairs. Static,
camera-motion, and light-motion guard tracks show no detected >=20% regression.
All persistent/true-peak hard memory guards and allocation-lifetime checks pass.

The campaign completed all 160 timing processes. Final post-processing initially
stopped because validation and timing serialized the same Vulkan float
`timestampPeriod` at different decimal precisions. The retained evidence was
finalized without rerunning any measurement after verifying the original frozen
source/blob manifest, scene digest, exact process/row counts, all timing health
checks, exact device/driver/API provenance, and the precision-only timestamp
rendering difference.

**Program conclusion:** Lane E's object-local ownership/update architecture
remains the evidence-backed incumbent for rigid and stable-topology-deforming
geometry on the measured target and boundary. Topology-changing/high-churn
backend selection remains a separate unresolved question.

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
   topology changes. Lane E #22 revalidates the rigid and stable-topology
   deforming performance claims under the Lane-L >=20% heavy-boundary protocol.
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
8. Lane I calibrated an architecture-neutral known-delta workload. Batched,
   paired, counterbalanced GPU timestamps passed the frozen control and detected
   +20%, +10%, and +5% controlled-work deltas across fresh processes. Complete
   CPU wall produced a non-monotonic frozen-gate failure, so I004 closes
   **target timing unsuitable** under the dual-axis `lane-i-i002-v1` protocol.
9. Lane K froze a new role split before new target timing: GPU timestamp is the
   sole primary performance axis and complete CPU wall is diagnostic/health/
   provenance only. K003 passed the baseline control and detected +20%, +10%,
   and +5% contiguously across eight fresh processes. K004 therefore accepts
   `lane-k-k002-v1` with a demonstrated **5%** minimum effect size on the
   measured target.
10. Lane M applies the accepted heavy-boundary role split to the topology
    backend question. Across all frozen mutating regimes and both tracks,
    hardened transient LBVH and clustered two-level BVH are decision-valid
    regressions versus the Lane-E incumbent. Their 1.25x memory hard guards pass,
    so Lane E remains selected for topology-changing/high-churn work on the
    measured target.

The main architectural blocker found by Integration #13 — world-space
moving-geometry maintenance — is solved by Lane E for rigid and
stable-topology-deforming geometry under its frozen gates. Lane G also removed
the deterministic sparse-memory blocker for hardened transient LBVH.

The previously remaining topology-changing/high-churn backend question is now
resolved for the measured target and frozen M001 regimes. Lane M used a fresh,
run-local same-boundary campaign under the prospectively frozen Lane-L 20%
heavy-boundary capability and retained the Lane-E incumbent. Historical E/G/J
timing remains diagnostic context only; the accepted conclusion comes from the
new Lane-M comparison.

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
| Lane I / #19 | Complete, target timing unsuitable | Frozen GPU timestamps detected +20%, +10%, and +5% known work deltas, but complete CPU wall failed the contiguous dual-axis criterion because +20% exceeded the frozen order-bias gate while +10%/+5% passed. GPU-only 5% resolution is mechanism evidence, not an accepted promotion protocol. |
| Lane J / #20 | Complete, measurement-limited | Clustered two-level object-local BVH passed deterministic correctness and lifetime-memory work, but formal performance ranking did not run because no accepted timing protocol existed at closure. It remains qualified for a future J004-equivalent crossover. |
| Lane K / #21 | Accepted | `lane-k-k002-v1` uses GPU timestamp as the primary axis and CPU wall as diagnostic/health/provenance only. K003 passed the frozen baseline and detected +20%, +10%, and +5% contiguously; K004 accepts a 5% minimum effect-size protocol on its calibration workload. |
| Lane L / #24 | Accepted | Dual-context heavy-boundary calibration accepts GPU timestamp primary / CPU wall diagnostic with a demonstrated 20% minimum detectable effect for the complete recurring boundary. |
| Lane E timing revalidation / #22 | Accepted | Under Lane L's 20% floor, moving-rigid and stable-topology-deforming both revalidate on HWRT and software fallback; static/camera/light show no detected >=20% regression and hard memory guards pass. |
| Lane M / #25 | Accepted | Formal 192-process same-boundary crossover retains Lane E for topology-changing/high-churn work on both tracks. Hardened LBVH and clustered two-level BVH are not promoted; all required memory hard guards pass, so rejection is performance-driven. |

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
- **topology-changing/high-churn**: retain the Lane-E object-local rebuild
  backend; unrelated structures remain untouched. Lane M formally rejects
  hardened LBVH and clustered two-level BVH as replacements for the frozen
  topology-changing/high-churn regimes on both primary and software tracks.

Lane E #22 independently revalidates the rigid and stable-topology-deforming
timing claims, while Lane M #25 supplies the accepted same-boundary
topology-changing/high-churn backend decision under the Lane-L heavy-boundary
protocol.

## Accepted, conditional, rejected, unresolved

### Accepted

- A001 producer/schema/natural ordering.
- HWRT/TLAS primary traversal on the measured target.
- B003 conservative quantized software fallback.
- C001 per-probe sparse hash.
- Lane E object-local ownership/update semantics for static, rigid and
  stable-topology deforming geometry;
- Lane E #22 heavy-boundary performance revalidation for rigid and
  stable-topology-deforming geometry on both HWRT and software fallback;
- Lane M #25 retention of the Lane-E object-local rebuild backend for the frozen
  topology-changing/high-churn regimes on both primary and software tracks.

### Conditional

- D001 renderer-depth reuse.
- D005 bounded-capacity/safe-overflow policy.
- virtual/clipmap storage in dense/residency-stable regimes.
- hardened transient LBVH and clustered two-level BVH remain reusable research
  mechanisms for materially new workloads/backends, but Lane M rejects them as
  production replacements for its frozen topology-changing/high-churn regimes.

### Rejected or not retained

- adding a global reorder solely to manufacture storage/traversal locality;
- D002/D003/D004 producer replacements;
- D005 tested implementation as the standalone producer;
- Lane F sorted two-level grid as the next dynamic-geometry direction;
- hardened transient LBVH as a replacement for Lane E in Lane M's frozen
  topology-changing/high-churn regimes;
- clustered two-level object-local BVH as a replacement for Lane E in Lane M's
  frozen topology-changing/high-churn regimes;
- treating the old world-space update model as the universal dynamic ownership
  model.

### Unresolved

- whether materially different topology workloads or a materially different
  backend justify reopening the Lane-M topology decision;
- whether a future representative dense workload justifies reopening clipmap
  storage;
- cross-GPU generality beyond the measured AMD Radeon 8060S target;
- final renderer/end-to-end integration of D001 and any future D005-style
  capacity policy.

## Lane E and Lane F are not mutually exclusive

Lane E answers **who owns geometry and which update semantics apply**. Lane F
tests **how a dynamic subset can be rebuilt/traversed each frame**. Those are
different architectural axes.

The current evidence supports Lane E as the ownership architecture. Lane M
directly tested hardened transient LBVH and clustered two-level BVH *inside* the
same object-local topology-changing boundary.

Earlier F/G/J mechanism evidence remains useful historical context, but Lane M
is now the decision-valid promotion gate. Neither alternative qualifies in any
frozen mutating scenario/track, so the program retains the Lane-E rebuild
backend rather than adopting transient LBVH or clustered BVH.

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

## Lane G/H/I/K/L/M interpretation

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

Lane I then calibrated the measurement system with architecture-neutral known
work deltas. Its accepted batch protocol made the GPU timestamp axis stable
enough to detect all tested deltas down to +5% across eight fresh processes.
However, complete CPU wall failed the frozen contiguous-resolution rule:
+20% exceeded the 1.05 maximum within-process order-bias gate while +10% and
+5% passed. That non-monotonic pattern was predeclared inconclusive.

I004 therefore closes **target timing unsuitable** for the exact
`lane-i-i002-v1` dual-axis protocol. The 5% GPU-only result is useful mechanism
evidence, but cannot be retroactively promoted by demoting CPU wall after seeing
the result.

Lane K then tested that role split prospectively instead of reinterpreting Lane
I. K002 froze GPU timestamp as the sole primary performance axis before target
timing, with complete CPU wall diagnostic/health/provenance only. K003 retained
all 1,024 raw rows across 32 fresh processes, passed the frozen GPU baseline
control, and detected +20%, +10%, and +5% contiguously. CPU wall produced only a
+5% annotation warning and no structural invalidation. K004 therefore accepts
`lane-k-k002-v1` with a **5%** demonstrated effect-size floor on the measured
target.

Lane L then calibrated the heavier complete recurring boundary used by the
dynamic-geometry architecture work and accepted a 20% demonstrated effect floor
with GPU timestamp primary and CPU wall diagnostic only. Lane E #22 used that
capability to revalidate rigid and stable-topology deformation.

Lane M #25 subsequently used the same heavy-boundary capability prospectively
for the remaining topology-backend question. Its 192-process formal campaign is
decision-valid: all required candidate memory guards pass, but hardened LBVH and
clustered BVH regress against the Lane-E incumbent in every mutating
scenario/track. This supersedes the earlier "timing unresolved" status for
topology-changing/high-churn backend selection on the measured target.

## Measurement methodology issue

Timing repeatability is now a **program-level first-class research problem**.

Evidence from Lane F, G, H and I shows:

- timing excursions affect controls as well as transient candidates;
- longer warmup alone is insufficient;
- paired/counterbalanced automatic-DPM timing was insufficient in G002;
- H001 static controls still failed tighter pre-frozen repeatability criteria;
- Lane I's longer same-process batching plus paired/counterbalanced sampling
  materially stabilized GPU timestamps and resolved the tested +5% known delta;
- complete CPU wall remained unsuitable as a required co-equal decision axis
  under Lane I's frozen dual-axis gate;
- architecture-specific conclusions must not be drawn from unstable or
  non-monotonic timing gates.

The forced AMDGPU performance-state experiment attempted in G002c caused host
instability and is permanently excluded from the active program. No future lane
may require `profile_peak`, `power_dpm_force_performance_level` writes,
privileged clock/power sysfs manipulation, or equivalent forced power-state
controls.

Lane K is now the accepted follow-up calibration for the measured target.
`lane-k-k002-v1` declares GPU timestamp as the primary performance boundary and
complete CPU wall as diagnostic/health/provenance evidence from the outset. It
freezes batching, fresh-process replication, counterbalancing, thresholds,
structural health checks, raw-sample retention, and zero timing-rerun budget
before target timing.

Downstream architecture timing may reuse Lane K only by importing the protocol
before its first accepted candidate timing and freezing a promotion threshold
no smaller than the demonstrated 5% effect size. This does not validate
historical architecture timing retroactively.

## Evidence chain

Detailed source-of-truth documents:

- Lane A: [A001 representative producer](https://github.com/owoDra/phos-gi-lab/blob/research-lane-a-split-rc/research/lanes/lane-a-split-rc/results/001-representative-producer.md)
- Lane B: [B002 exact-stream traversal](https://github.com/owoDra/phos-gi-lab/blob/research-lane-b-traversal/research/lanes/lane-b-traversal/results/002-lane-a-exact-stream-traversal.md), [B003 wide software traversal](https://github.com/owoDra/phos-gi-lab/blob/research-lane-b-traversal/research/lanes/lane-b-traversal/results/003-wide-software-traversal.md)
- Lane C: [C001 final storage decision](https://github.com/owoDra/phos-gi-lab/blob/research-lane-c-storage-locality/research/lanes/lane-c-storage-locality/results/001-storage-baselines.md)
- Integration: [I001 dynamic end-to-end](https://github.com/owoDra/phos-gi-lab/blob/research-integration-gate/research/integration/results/001-dynamic-end-to-end.md)
- Lane D: [final cross-lane producer decision](https://github.com/owoDra/phos-gi-lab/blob/research-lane-d-producer-optimization/research/lanes/lane-d-producer-optimization/results/006-final-cross-lane-decision.md)
- Lane E: [E005 final ownership replay](https://github.com/owoDra/phos-gi-lab/blob/research-lane-e-dynamic-geometry/research/lanes/lane-e-dynamic-geometry/results/005-integration-replay.md), [E001 heavy-boundary revalidation](https://github.com/owoDra/phos-gi-lab/blob/research-lane-e-timing-revalidation/research/lanes/lane-e-timing-revalidation/results/001-e001-heavy-boundary-revalidation.md)
- Lane F: [F002 builder](https://github.com/owoDra/phos-gi-lab/blob/research-lane-f-dynamic-geometry-alternatives/research/lanes/lane-f-dynamic-geometry-alternatives/results/002-pure-gpu-transient-lbvh-builder.md), [F006 geometry-class controls](https://github.com/owoDra/phos-gi-lab/blob/research-lane-f-dynamic-geometry-alternatives/research/lanes/lane-f-dynamic-geometry-alternatives/results/006-geometry-class-crossover-controls.md), [F007 final replay](https://github.com/owoDra/phos-gi-lab/blob/research-lane-f-dynamic-geometry-alternatives/research/lanes/lane-f-dynamic-geometry-alternatives/results/007-final-integration-replay.md)
- Lane G: [G002 repeatability diagnosis](https://github.com/owoDra/phos-gi-lab/blob/research-lane-g-transient-lbvh-hardening/research/lanes/lane-g-transient-lbvh-hardening/results/002-timing-repeatability-diagnosis.md), [G005 deterministic replay](https://github.com/owoDra/phos-gi-lab/blob/research-lane-g-transient-lbvh-hardening/research/lanes/lane-g-transient-lbvh-hardening/results/005-final-deterministic-replay.md)
- Lane H: [H001 safe timing result](https://github.com/owoDra/phos-gi-lab/blob/research-lane-h-topology-rebuild-crossover/research/lanes/lane-h-topology-rebuild-crossover/results/001-safe-timing-methodology.md), [H004 final decision](https://github.com/owoDra/phos-gi-lab/blob/research-lane-h-topology-rebuild-crossover/research/lanes/lane-h-topology-rebuild-crossover/results/004-final-decision.md)
- Lane I: [I003 target calibration](https://github.com/owoDra/phos-gi-lab/blob/research-lane-i-measurement-calibration/research/lanes/lane-i-measurement-calibration/results/003-target-calibration.md), [I004 timing capability](https://github.com/owoDra/phos-gi-lab/blob/research-lane-i-measurement-calibration/research/lanes/lane-i-measurement-calibration/results/004-program-timing-capability.md)
- Lane K: [K003 target calibration](https://github.com/owoDra/phos-gi-lab/blob/research-lane-k-gpu-primary-calibration/research/lanes/lane-k-gpu-primary-calibration/results/003-target-calibration.md), [K004 timing capability](https://github.com/owoDra/phos-gi-lab/blob/research-lane-k-gpu-primary-calibration/research/lanes/lane-k-gpu-primary-calibration/results/004-program-timing-capability.md)
- Lane L: [L002 target result](https://github.com/owoDra/phos-gi-lab/blob/research-lane-l-heavy-boundary-calibration/research/lanes/lane-l-heavy-boundary-calibration/results/005-l002-target-result.md), [Lane L final](https://github.com/owoDra/phos-gi-lab/blob/research-lane-l-heavy-boundary-calibration/research/lanes/lane-l-heavy-boundary-calibration/results/007-lane-l-final.md)
- Lane M: [M001 formal crossover](https://github.com/owoDra/phos-gi-lab/blob/research-lane-m-topology-backend-crossover/research/lanes/lane-m-topology-backend-crossover/results/002-m001-formal-crossover.md)

Issues #9-#25 provide frozen plans and cross-lane context; lane result documents
take precedence for concluded experiment outcomes.

## Next research priority

The immediate topology-backend blocker is closed for the measured target:
Lane M retains the Lane-E object-local rebuild backend for the frozen
topology-changing/high-churn regimes.

The next program work should therefore move back toward the umbrella exit
criterion: an end-to-end renderer/integration replay using the currently
evidence-backed producer, traversal, storage and dynamic-geometry architecture.

Decision-relevant future branches should be opened only for a concrete new
question, such as:

- cross-GPU calibration and replay on a new target;
- a materially different topology workload or backend that justifies reopening
  Lane M;
- a representative dense/residency-stable workload that justifies reopening
  clipmap storage;
- renderer integration of D001 depth reuse or a future D005-style bounded
  capacity policy under full end-to-end cost accounting.

Historical mechanism timing remains context only. Any reopened architecture
axis must again freeze its own run-local comparison, correctness/memory gates,
measurement capability and rerun policy before accepted target timing.
