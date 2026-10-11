# Research program

Umbrella issue: #9

The program is measurement-driven. It does not assume that a particular
traversal, storage representation, producer optimization, or dynamic-geometry
structure must win.

**Current program-level conclusions and roadmap are canonical in
[status.md](status.md).** Detailed experiment evidence remains canonical in each
lane branch's committed `results/` documents.

## Current state

As of 2026-10-02:

| Workstream | Issue | Branch | State |
| --- | ---: | --- | --- |
| Lane A — Split RC producer | #10 | `research-lane-a-split-rc` | completed / accepted |
| Lane B — traversal | #11 | `research-lane-b-traversal` | completed / accepted |
| Lane C — storage/locality | #12 | `research-lane-c-storage-locality` | completed / accepted |
| Integration I001 | #13 | `research-integration-gate` | completed / no universal promotion |
| Lane D — producer optimization | #14 | `research-lane-d-producer-optimization` | completed |
| Lane E — dynamic ownership | #15 | `research-lane-e-dynamic-geometry` | completed / accepted incumbent |
| Lane F — dynamic alternatives | #16 | `research-lane-f-dynamic-geometry-alternatives` | completed / no promotion |
| Lane G — transient LBVH hardening | #17 | `research-lane-g-transient-lbvh-hardening` | completed / memory+correctness accepted, timing measurement-limited |
| Lane H — topology rebuild crossover | #18 | `research-lane-h-topology-rebuild-crossover` | completed / measurement-limited |
| Lane I — measurement calibration | #19 | `research-lane-i-measurement-calibration` | completed / target timing unsuitable; GPU timestamp 5% mechanism evidence |
| Lane J — topology backend alternatives | #20 | `research-lane-j-topology-backend-alternatives` | completed / measurement-limited |
| Lane K — GPU-primary calibration | #21 | `research-lane-k-gpu-primary-calibration` | completed / accepted 5% calibration workload protocol |
| Lane L — heavy-boundary calibration | #24 | `research-lane-l-heavy-boundary-calibration` | completed / accepted 20% heavy-boundary capability |
| Lane E timing revalidation | #22 | `research-lane-e-timing-revalidation` | completed / accepted |
| Lane M — topology backend crossover | #25 | `research-lane-m-topology-backend-crossover` | completed / accepted; Lane E incumbent retained |

Lane J is concluded measurement-limited. Lane K accepts a reusable GPU-primary
5% calibration protocol on its calibration workload. Lane L separately accepts
a 20% detectable-effect capability for the heavier complete recurring boundary.
Lane E timing revalidation is concluded under that Lane-L capability. Lane M
then completes the run-local topology-backend crossover: hardened transient LBVH
and clustered two-level BVH are not promoted, and the Lane E incumbent is
retained for all frozen topology-changing/high-churn regimes on both tracks.

## Program topology

Git cannot store both a `research` ref and refs below `research/...`, so lane
branches use the `research-lane-*` prefix while `research` is the long-lived
program integration/source-of-truth branch.

```text
                         research
                            │
              ┌─────────────┼─────────────┐
              │             │             │
         Lane A #10    Lane B #11    Lane C #12
              │             │             │
              └──── representative contracts ──────┐
                                                     │
                                                Lane D #14
                                                     │
                                                     ▼
                                              Integration #13
                                               /           \
                                              /             \
                                      Lane E #15         Lane F #16
                                      incumbent           alternatives
                                           \               /
                                            \             /
                                             ▼           ▼
                                             Lane G #17
                                     LBVH correctness/memory
                                                  │
                                                  ▼
                                             Lane H #18
                                          measurement-limited
                                                  │
                                   ┌──────────────┴──────────────┐
                                   ▼                             ▼
                              Lane I #19                    Lane J #20
                         calibration diagnosis          clustered candidate
                                   │                             │
                                   ▼                             │
                              Lane K #21                        │
                         GPU-primary capability                  │
                                   │                             │
                                   ▼                             │
                              Lane L #24                        │
                         heavy-boundary 20%                     │
                                   │                             │
                                   ▼                             │
                         Lane E revalidation #22                │
                                   └──────────────┬──────────────┘
                                                  ▼
                                             Lane M #25
                                      formal topology crossover
                                      Lane E incumbent retained
```

Lane E and Lane F answer different questions. Lane E establishes the current
geometry ownership/update-semantics architecture. Lane F tests frame-local
dynamic rebuild mechanisms. See `status.md` for the exact accepted,
conditional, rejected, and unresolved distinctions.

## Source-of-truth layering

Do not copy lane result documents into `research`.

1. **Raw artifacts**
   - `out/research/<lane>/<experiment>/<timestamp>/`
   - machine-specific; normally not committed.
2. **Experiment result**
   - lane branch `research/lanes/<lane>/results/*.md`
   - canonical detailed evidence, provenance, limitations and decision.
3. **Lane result index**
   - lane branch `results/index.json`
   - canonical lifecycle/disposition index for that lane.
4. **Program synthesis**
   - `research/status.md` on `research`
   - canonical cross-lane architecture, unresolved questions and roadmap.
5. **Shared methodology**
   - `research/protocol.md`
   - program-wide evidence and measurement rules.

Issue bodies/comments retain frozen plans and cross-lane context, but concluded
experiment outcomes are taken from committed result documents.

## Evidence flow

```text
question + frozen decision gate
        ↓
lane-local implementation / validation
        ↓
raw artifact + exact provenance
        ↓
accepted / rejected / inconclusive / invalidated evidence
        ↓
lane results/*.md + results/index.json
        ↓
lane-level decision
        ↓
cross-lane integration/replay
        ↓
research/status.md synthesis
        ↓
next falsifiable question
```

Diagnostic-only values may motivate the next experiment but may not be upgraded
into formal PASS/FAIL evidence after the fact.

## Current evidence chain

The completed program establishes:

- A001 representative natural producer stream;
- HWRT/TLAS primary traversal on the measured target plus B003 conservative
  quantized software fallback;
- C001 per-probe sparse hash;
- no standalone Lane D producer replacement;
- I001 identification of world-space moving-geometry maintenance as the common
  blocker;
- Lane E object-local ownership/update semantics as the current incumbent;
- Lane F transient LBVH as a promising but initially unpromoted mechanism;
- Lane G hardened transient LBVH with deterministic correctness and sparse-memory
  blockers resolved, but production timing still measurement-limited;
- Lane H confirmation that the topology-changing crossover cannot be ranked
  under the prior timing methodology on the target host;
- Lane I demonstration that batched GPU timestamps can resolve the tested 5%
  known-work delta, while the frozen GPU+CPU-wall dual-axis protocol remains
  unsuitable for formal architecture ranking;
- Lane K acceptance of GPU-primary / CPU-wall-diagnostic timing on its calibrated
  workload down to a demonstrated 5% effect;
- Lane L acceptance of the same role split for the heavier complete recurring
  boundary with a demonstrated 20% effect floor;
- Lane E follow-up revalidation of moving-rigid and stable-topology-deforming
  object-local maintenance on both HWRT and software fallback, with no detected
  >=20% static/camera/light guard regression;
- Lane M formal same-boundary topology-backend crossover retaining the Lane E
  incumbent for topology-changing/high-churn work on both tracks; hardened LBVH
  and clustered two-level BVH fail promotion on performance while their memory
  hard guards pass.

Detailed links and representative values are maintained only in
[status.md](status.md).

## Branch discipline

Normal lane iterations are committed directly to exactly one lane branch.
Routine PRs are not required.

Do not merge lane implementation branches wholesale into `research`.
At explicit synthesis checkpoints, only program-level conclusions, methodology,
roadmap, and other genuinely shared contracts are brought back to `research`.

Lane I's dual-axis protocol remains unsuitable. Lane K is the accepted
GPU-primary calibration for its measured calibration workload. Lane L is the
accepted capability result for the heavier complete recurring boundary and sets
a 20% floor for that boundary. Lane E #22 imported Lane L prospectively and
revalidated its two formal dynamic classes. Lane M #25 then imported the same
heavy-boundary capability prospectively and resolves the remaining tested
topology-backend choice in favor of retaining the Lane E incumbent.

See [protocol.md](protocol.md) for shared research rules.
