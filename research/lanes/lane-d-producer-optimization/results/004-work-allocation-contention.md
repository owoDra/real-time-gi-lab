# D004 — work-allocation contention

Status: rejected for promotion

## Question

Can A001's per-visible-owner global output/work/count reservations be aggregated
at 64-surface workgroup scope while preserving visibility and schema-v1 work
semantics?

## Artifact / identity

- Measurement commit:
  `e2ecb35bcf5579a48460a425bf2ef905a536bbae`.
- Source: uploaded `d004.csv`.
- Workload: real Sponza, static / camera-motion / light-motion.
- Repeats: 3 process-level repeats.
- Timed iterations: 50 per case.

Unlike D003, D004 embeds the measurement git commit in every CSV row.

## Correctness

All rows report:

- correctness = true;
- overflow = 0;
- representative owner/work counts unchanged.

Representative counts:

| case | visible owners | work items |
| --- | ---: | ---: |
| static | 981 | 31,392 |
| camera-motion | 978 | 31,296 |
| light-motion | 981 | 31,392 |

## Atomic-count reduction

The workgroup-prefix mechanism substantially reduced theoretical global
reservation atomics:

| case | per-owner atomics | workgroup atomics | reduction | active groups |
| --- | ---: | ---: | ---: | ---: |
| static | 2,943 | 1,182 | 59.84% | 394 |
| camera-motion | 2,934 | 1,212 | 58.69% | 404 |
| light-motion | 2,943 | 1,182 | 59.84% | 394 |

The candidate used 268 bytes of shader workgroup shared scratch and added no
global buffer, dispatch, CPU pass, compaction, or sort.

## Matched full-path timing

Three-repeat medians in microseconds:

| case | owner emit | workgroup emit | emit delta | owner producer | workgroup producer | producer delta |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| static | 14.799 | 17.032 | +15.08% | 54.025 | 59.371 | +9.90% |
| camera-motion | 15.111 | 15.220 | +0.72% | 54.059 | 53.504 | -1.03% |
| light-motion | 14.766 | 15.910 | +7.75% | 54.059 | 55.034 | +1.80% |

Matched end-to-end:

| case | owner E2E | workgroup E2E | delta |
| --- | ---: | ---: | ---: |
| static | 62.685 | 69.464 | +10.81% |
| camera-motion | 62.855 | 62.166 | -1.10% |
| light-motion | 62.703 | 63.682 | +1.56% |

The predeclared gate required >=10% producer-emit improvement and >=5% complete
producer improvement in all three cases. The candidate fails decisively.

## Direct accepted-A001 comparison

| case | A001 producer | workgroup producer | delta | A001 E2E | workgroup E2E | delta |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| static | 52.727 | 59.371 | +12.60% | 62.078 | 69.464 | +11.90% |
| camera-motion | 52.537 | 53.504 | +1.84% | 62.956 | 62.166 | -1.25% |
| light-motion | 55.789 | 55.034 | -1.35% | 66.465 | 63.682 | -4.19% |

The direct accepted-A001 requirement also fails because producer total does not
improve by >=5% in all cases and static regresses substantially.

## D001 depth-reuse composition

The workgroup allocator also fails to become attractive when composed with the
retained D001 depth-reuse contract.

Standalone producer delta versus per-owner depth-reuse:

- static: +3.40%;
- camera-motion: +0.22%;
- light-motion: +3.91%.

Standalone E2E delta:

- static: +3.15%;
- camera-motion: +0.06%;
- light-motion: +5.37%.

The depth-reuse composition therefore does not rescue the mechanism.

## Interpretation

D004 shows that global reservation atomics are not the dominant producer
bottleneck at this workload scale on the target GPU.

Reducing reservation atomics by roughly 59% is insufficient because the
64-lane shared prefix scan and synchronization overhead costs more than the
contention it removes.

This result is specific to the tested workgroup-prefix implementation and
representative workload. It does not prove that every possible allocation
strategy is slower, but it removes the premise for carrying this mechanism into
the current Lane D composition.

## Decision

- do not retain workgroup-prefix allocation;
- keep A001 per-owner allocation;
- keep D001 depth reuse as the only retained Lane D composition mechanism;
- continue to D005 stream capacity / overflow, where the largest remaining
  producer inefficiency is memory reservation rather than measured producer
  execution time.

D004 changes no Lane B traversal or Lane C storage decision.
