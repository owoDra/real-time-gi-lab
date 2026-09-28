# A001 — representative Split RC producer stream

Status: provisional — measurement passes, artifact path reconciliation pending

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

## Limitation / traceability hold

The uploaded `summary.json` identifies the GPU and commit but does not encode
the harness artifact root, iteration count, or validation flag. The operator
identified this as the requested validation-disabled repeated measurement, but
the shared protocol also requires the raw artifact path.

Do not delete the existing raw artifact. Once its
`out/research/lane-a-split-rc/001-representative-producer/<timestamp>/` path is
recorded, this result can move from provisional to accepted without changing
the measured conclusion.

The A001 runner was updated afterward to record `iterations`, `validation`,
`artifact_root`, and `scene` in future summaries.

## Decision and next question

Provisional decision: promote stream schema v1 as the representative Lane A
interface for Lane B/C, subject only to restoring the raw artifact path required
by the research protocol.

Next question: replay this exact natural stream in Lane B and Lane C to compare
traversal and radiance-storage mechanisms without adding synthetic ordering.
