# D002 — visible-tile-driven emission

Status: rejected for promotion

## Question

Can the producer emit from the already-resolved screen-tile domain instead of
rescanning every source surface, while preserving A001 semantics and improving
complete producer/end-to-end cost?

## Artifact / identity

- Measurement commit: `844123281ff72b5c3b6dea38ca69732b5ca2e00b`.
- Raw artifact:
  `out/research/lane-d-producer-optimization/002-visible-tile-emission/20260928T162312Z/`.
- GPU: AMD Radeon 8060S Graphics (RADV STRIX_HALO).
- Workload: real Sponza, static / camera-motion / light-motion.
- Repeats: 3 process-level repeats.
- Timed iterations: 50 per case.
- Validation: disabled for accepted timing.
- Repository state was clean and the research runner returned 0.

## Correctness

All accepted rows passed semantic correctness and overflow remained zero.

The source dispatch shrank from 262,241 surface invocations to 9,216 tile
invocations while preserving the same representative work:

| case | visible probes | work items |
| --- | ---: | ---: |
| static | 981 | 31,392 |
| camera-motion | 978 | 31,296 |
| light-motion | 981 | 31,392 |

The emitted stream kept A001 block semantics. Workload IDs changed naturally
because inter-block GPU append order is not byte-stable.

Natural neighboring-tile adjacency improved from about 0.975 for the
surface-source path to about 0.994 for the tile-source path. This is recorded as
a source-emission consequence only; no sort or post-generation reorder was
performed.

## Matched staged comparison

Medians in microseconds:

| case | surface-full producer | tile-full producer | producer delta | surface-full E2E | tile-full E2E | E2E delta |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| static | 53.728 | 49.766 | -7.37% | 62.403 | 58.975 | -5.49% |
| camera-motion | 58.070 | 46.912 | -19.22% | 68.125 | 55.603 | -18.38% |
| light-motion | 57.178 | 48.200 | -15.70% | 66.459 | 57.050 | -14.16% |

Producer emit itself improved materially:

| case | surface emit | tile emit |
| --- | ---: | ---: |
| static | 14.601 | 9.298 |
| camera-motion | 16.209 | 8.641 |
| light-motion | 15.829 | 8.653 |

The mechanism therefore clearly removes useful post-visibility scan work on
camera-motion and light-motion. However, the predeclared matched-control gate
required at least 10% median producer-total improvement in **all three** cases.
Static reached only 7.37%.

## Direct accepted-A001 comparison

| case | A001 producer | tile-full producer | delta | A001 E2E | tile-full E2E | delta |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| static | 49.396 | 49.766 | +0.75% | 58.054 | 58.975 | +1.59% |
| camera-motion | 51.835 | 46.912 | -9.50% | 61.171 | 55.603 | -9.10% |
| light-motion | 52.634 | 48.200 | -8.42% | 62.088 | 57.050 | -8.11% |

The direct-A001 gate required at least 5% producer improvement and no E2E
regression in every case. Static fails both requirements.

## Static variance

The static matched producer delta across the three individual repeats was
approximately:

- repeat 1: -10.72%;
- repeat 2: +0.88%;
- repeat 3: -11.57%.

This is meaningful variance, but the experiment protocol fixed the decision on
the three-repeat median. The threshold is not changed after observing the data.

Accordingly, this result does **not** establish that tile-domain emission is
universally slower or uninteresting. It establishes that the current D002
mechanism is not stable enough to pass Lane D's promotion gate on the required
representative cases.

## Depth-reuse composition

The retained D001 depth-reuse contract composed cleanly with tile emission:

| case | tile+depth-reuse producer | tile+depth-reuse E2E |
| --- | ---: | ---: |
| static | 50.021 | 58.682 |
| camera-motion | 48.521 | 57.180 |
| light-motion | 50.000 | 58.688 |

That composition still fails the direct accepted-A001 requirement in static, so
it is not carried forward as the new Lane D baseline.

## Memory

D002 adds no persistent or transient allocation relative to its matched
surface-source controls.

The unchanged stream allocation remains:

- capacity: 18,874,368 bytes;
- actual stream: 2,002,944-2,009,088 bytes;
- utilization: about 10.6%.

No stream compaction or capacity optimization was attempted.

## Decision

- **Do not retain D002 visible-tile-driven emission for composition.**
- Preserve the result as diagnostic evidence that source-domain reduction can
  roughly halve producer-emit cost on this workload.
- Do not rewrite accepted A001 or D001 based on D002.
- Continue to D003 using the accepted A001-style surface producer and evaluate
  one-pass visibility owner selection independently.

D002 changes no Lane B traversal or Lane C storage decision.
