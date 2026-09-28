# A001 — representative Split RC producer stream

Status: accepted

## Question

Can a GPU visibility-driven Split Radiance Cascades producer expose a
representative natural probe/cascade/ray stream for Lane B and Lane C without
CPU sorting or post-producer global reordering?

## Variants and workload

- Scene: Sponza real triangle-centroid surface samples.
- Cases: static, camera-motion, light-motion.
- Producer: GPU visibility depth/owner selection followed by atomic natural
  append of cascade-major, ray-minor work blocks.
- Gather control: analytic direct-light alignment only; no traversal or radiance
  storage architecture is selected in Lane A.
- GPU: AMD Radeon 8060S Graphics (RADV STRIX_HALO).
- Measurement commit: `8b647ef8dcf1150f86a9d25c039ca48bd7f30b8f`.
- Raw artifact: `out/research/lane-a-split-rc/001-representative-producer/20260928T143212Z/`.
- Accepted run: validation disabled, repeated measurement (50 iterations per case).

## Correctness

All three cases passed visibility, producer-semantic, and resolve checks.

| case | visible probes | work items | max resolve abs error |
| --- | ---: | ---: | ---: |
| static | 981 | 31,392 | 1.914799213e-6 |
| camera-motion | 978 | 31,296 | 1.914799213e-6 |
| light-motion | 981 | 31,392 | 1.907348633e-6 |

No correctness errors were reported.

## Timings

Microseconds, as reported by the uploaded validation-disabled repeated-run
summary:

| case | producer total | gather | merge | resolve | end-to-end |
| --- | ---: | ---: | ---: | ---: | ---: |
| static | 49.141 | 3.641 | 2.627 | 2.396 | 57.805 |
| camera-motion | 48.590 | 3.636 | 2.628 | 2.389 | 57.242 |
| light-motion | 54.786 | 4.432 | 3.086 | 2.639 | 64.943 |

Producer total includes visibility depth/owner selection, producer emit, and
finalize rather than hiding producer cost.

## Natural locality

| case | mean probe run | same-probe adjacent | same-cascade adjacent | neighboring-probe adjacent | neighboring-tile adjacent |
| --- | ---: | ---: | ---: | ---: | ---: |
| static | 8 | 0.875028 | 0.875028 | 0.875028 | 0.975216 |
| camera-motion | 8 | 0.875028 | 0.875028 | 0.875028 | 0.975204 |
| light-motion | 8 | 0.875028 | 0.875028 | 0.875028 | 0.975280 |

This locality is the observed GPU append order. No CPU sort or post-producer
global reorder is applied.

## Memory

All three cases report:

- persistent: 4,343,440 bytes;
- transient: 21,602,344 bytes;
- resident: 25,945,784 bytes;
- maximum stream allocation: 18,874,368 bytes.

## Interpretation

The natural producer stream has strong short-range tile locality and preserves
the intended eight-ray probe blocks without an explicit global ordering step.
The three required dynamic regimes remain semantically valid, and producer cost
is a large majority of this minimal control pipeline's end-to-end time.

Schema v1 is therefore technically suitable as the Lane B/C replay workload:
downstream lanes can compare traversal and storage choices against the observed
stream without manufacturing an ordering in Lane A.

## Limitations

- A001 intentionally uses an analytic direct-light gather control; it does not
  establish a traversal or radiance-storage winner.
- The stream captures the representative Sponza producer regimes required by
  this experiment, not every later dynamic-scene regime in the shared protocol.
- Raw artifacts are machine-specific and remain outside Git; the accepted
  artifact directory above is the audit anchor.
- The runner was updated after this measurement to embed `iterations`,
  `validation`, `artifact_root`, and `scene` directly in future summaries.

## Decision and next question

Decision: promote stream schema v1 as the representative Lane A interface for
Lane B/C. The A001 decision gate is satisfied: correctness passes on all three
required real-scene cases, producer cost is included, replay streams are
exported, and locality is measured from the natural GPU append order without a
CPU sort or post-producer global reorder.

Next question: replay this exact natural stream in Lane B and Lane C to compare
traversal and radiance-storage mechanisms without adding synthetic ordering.
