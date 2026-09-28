# D001 — renderer visibility reuse boundary

Status: accepted

## Question

How much accepted A001 producer work can be removed when renderer visibility
already exists, and which visibility contract is worth carrying into later Lane
D producer experiments?

D001 is a mechanism-selection result, not a final Lane D producer promotion.

## Artifact / identity

- Measurement commit: `c083db8925d362c8c8df3cebc046fb2ff62fc2c9`.
- Raw artifact:
  `out/research/lane-d-producer-optimization/001-visibility-reuse/20260928T160750Z/`.
- GPU: AMD Radeon 8060S Graphics (RADV STRIX_HALO).
- Workload: real Sponza, static / camera-motion / light-motion.
- Repeats: 3 process-level repeats.
- Timed iterations: 50 per case.
- Validation: disabled for accepted timing.
- Repository state was clean and the research runner returned 0.

## Correctness

All accepted rows passed:

- A001 visibility reference;
- producer schema-v1 semantic checks;
- work/output count parity;
- owner-set parity;
- gather/merge/resolve reference;
- overflow flag remained zero.

Observed work counts remained representative A001 counts:

| case | visible probes | work items |
| --- | ---: | ---: |
| static | 981 | 31,392 |
| camera-motion | 978 | 31,296 |
| light-motion | 981 | 31,392 |

Natural locality remained effectively unchanged at the aggregate metrics used by
A001: mean probe run stayed 8 and same-probe/same-cascade adjacency stayed about
0.875. Workload IDs differed between executions/variants as expected because
inter-owner GPU append order is not a byte-stable contract.

## Timing result

Medians in microseconds.

| case | full producer | depth reuse incremental | owner reuse incremental | full E2E | depth reuse incremental E2E | owner reuse incremental E2E |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| static | 56.228 | 29.616 | 21.998 | 65.379 | 38.413 | 32.184 |
| camera-motion | 53.216 | 28.929 | 21.300 | 61.889 | 37.590 | 31.185 |
| light-motion | 53.741 | 28.915 | 20.236 | 62.388 | 37.566 | 29.092 |

Relative to the same-run instrumented full path:

- depth reuse reduced incremental producer cost by about 45.6-47.3% and
  incremental E2E by about 38-41%;
- owner reuse reduced incremental producer cost by about 60.0-62.3% and
  incremental E2E by about 50-53%.

The standalone boundary adds the measured renderer prerequisite back:

| case | full standalone E2E | depth reuse standalone E2E | delta | owner reuse standalone E2E | delta |
| --- | ---: | ---: | ---: | ---: | ---: |
| static | 65.379 | 65.013 | -0.56% | 67.398 | +3.09% |
| camera-motion | 61.889 | 63.516 | +2.63% | 65.892 | +6.47% |
| light-motion | 62.388 | 64.426 | +3.27% | 63.971 | +2.54% |

The fixed D001 retain gate therefore keeps **depth reuse** for composition:
all three median standalone regressions remain below the 5% ceiling while its
incremental producer/E2E gains are well above the required thresholds.

**Owner reuse is not retained as the D001 composition contract** because
camera-motion standalone E2E regressed by 6.47%, exceeding the predeclared 5%
ceiling. Its large incremental savings remain diagnostic evidence and may be
revisited only if a later source-emission mechanism changes the complete
standalone boundary; the D001 threshold is not relaxed after seeing the result.

## Accepted A001 comparison caveat

The separately instrumented D001 `full` path is intentionally not substituted
for accepted A001. Explicit reset/barrier stage boundaries make it more
expensive than the accepted same-process A001 control in static and light-motion
cases.

Accepted A001 control medians in this run were:

| case | A001 producer | A001 E2E |
| --- | ---: | ---: |
| static | 49.476 | 58.140 |
| camera-motion | 52.247 | 62.272 |
| light-motion | 49.300 | 57.946 |

Therefore D001 establishes the reuse boundary and a contract to carry forward;
it does **not** claim that either reuse path already beats accepted A001
standalone end-to-end.

## Memory

A001/D001 still reserve the same worst-case stream capacity:

- stream capacity: 18,874,368 bytes;
- actual stream: 2,002,944-2,009,088 bytes;
- utilization: about 10.6%.

Depth reuse removes 36,864 bytes of GI-owned visibility transient state and
reduces producer scratch from 73,768 bytes to 36,904 bytes in the D001
accounting. Owner reuse demonstrates that both visibility scratch buffers can
be externalized, but it is not the retained contract from this experiment.

The dominant stream over-allocation remains untouched and is still D005's
question.

## Limitations

- D001 retains A001's all-source-surface producer scan; it intentionally does
  not test visible-tile-driven emission.
- Renderer visibility is synthesized by the A001 visibility path before timing;
  this measures the reuse contract, not a particular renderer implementation.
- Three repeats are sufficient for this decision gate, but individual
  standalone samples show noticeable variance. Only the predeclared median gate
  is used for the decision.
- Results are target-GPU evidence for AMD Radeon 8060S / RADV, not a universal
  architecture claim.

## Decision / next question

Decision:

- retain **depth reuse** as the D001 renderer-visibility contract for later
  composition;
- do not retain owner reuse under the fixed D001 standalone gate;
- promote no final producer architecture yet.

Next: D002 tests visible-tile-driven emission. It must compare directly against
accepted A001, preserve the same semantic work, and measure any natural ordering
change caused by using the tile domain as the source rather than a
post-generation reorder.
