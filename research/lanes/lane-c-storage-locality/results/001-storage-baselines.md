# C001a result — storage structural/correctness bring-up

Status: **accepted for synthetic structural/correctness candidate retention
only; GPU performance unresolved**

Artifact: `out/research/lane-c-storage-locality/001-storage-baselines/20260928T132145Z`
(assistant execution environment; target-system rerun required)  
Git commit: `1f83e384549435f2aac0875e13ac249fbf0b9984`

## Scope and environment

C001a exercises only representation semantics and structural accounting.

The assistant execution environment had no usable target GPU and did not have
`mise` installed. The requested `mise install`,
`mise run research:check`, and `mise run build` entrypoints therefore
returned command-not-found before this run.

To still exercise the repository's raw-artifact contract, the same
`scripts/research/run_experiment.py` wrapper used by
`mise run research:record` was invoked directly around the lane-owned Python
experiment. The wrapper completed with return code 0. This does **not** replace
the required target-system mise/build/GPU run.

Recorded host identity: generic Linux assistant container, Python 3.13.5, GPU
unknown.

## Workload

- 3 cascades;
- 12 x 12 x 4 active bricks per cascade;
- 4 x 4 x 4 probes per brick;
- occupancy: 4 / 16 / 48 active probes per brick;
- virtual clipmap extent: 24 x 24 x 8 bricks per cascade;
- one-brick X shift as the dynamic residency control;
- source ordering unchanged; no grouping or sorting.

## Correctness

All nine representation/occupancy rows passed insert, lookup, update,
invalidation, absence, restore, and final lookup checks.

The unit tests also passed for all three representations, including explicit
controls that require:

- sparse bricks to be allowed to use more memory than the per-probe hash;
- dense occupancy to make brick storage structurally advantageous.

## Structural measurements

Correction after self-review: the initial C001a result accidentally counted a
packed `uint32 key + uint32 payload` probe-hash slot as 16 bytes. The actual
packed model is 8 bytes/slot, matching the M0 representation. The table below
contains the corrected probe-hash values. This correction strengthens the
sparse-hash case and does not change the candidate-retention decision.

| Regime | Representation | Active probes | Persistent bytes | Shift eviction/invalidation units |
| --- | --- | ---: | ---: | ---: |
| sparse (4/brick) | probe hash | 6,912 | 131,072 | 576 probes |
| sparse (4/brick) | hashed brick pool | 6,912 | 528,640 | 144 bricks |
| sparse (4/brick) | virtual clipmap | 6,912 | 518,400 | 144 bricks |
| medium (16/brick) | probe hash | 27,648 | 524,288 | 2,304 probes |
| medium (16/brick) | hashed brick pool | 27,648 | 528,640 | 144 bricks |
| medium (16/brick) | virtual clipmap | 27,648 | 518,400 | 144 bricks |
| dense (48/brick) | probe hash | 82,944 | 2,097,152 | 6,912 probes |
| dense (48/brick) | hashed brick pool | 82,944 | 528,640 | 144 bricks |
| dense (48/brick) | virtual clipmap | 82,944 | 518,400 | 144 bricks |

C001a models zero additional global scratch for the in-place representations.
That is not a claim that a GPU allocator/residency implementation will require
zero scratch; queues, free lists, compaction, and synchronization introduced by
C001b must be counted.

The structural address path is one conceptual table lookup for the probe hash,
hash-directory plus local-index resolution for the hashed brick pool, and one
bounded direct page-table translation plus local indexing for the virtual
clipmap. These counts are not latency estimates.

## Analysis

The sparse control rejects the premise that brick storage is automatically more
memory-efficient. At 4 probes per brick, the corrected packed `uint32 key + uint32 payload`
hash model uses 128 KiB while the brick candidates use about 506–516 KiB.

At 16 probes per brick, the corrected probe hash is about 512 KiB, essentially
at parity with the brick models (about 506–516 KiB). At 48 probes per brick,
the probe hash grows to 2 MiB while the brick models remain about 506–516 KiB.
Their one-brick motion control also operates on 144 brick residency units rather
than thousands of individual probe units. This is only a unit-count advantage;
C001a does not measure whether a brick eviction/update is cheaper on the GPU.

The virtual/clipmap representation is worth retaining independently from the
hashed brick pool because it exchanges a hash directory for a bounded direct
virtual page table and makes camera-window residency explicit. That trade can
change both producer work and persistent memory on real Split RC streams.

## Decision

Retain all three required representations for C001b:

1. per-probe open-addressed sparse hash — baseline and sparse-regime candidate;
2. hashed contiguous brick pool — retained for occupancy amortization and
   brick-granularity residency testing;
3. virtual/clipmap-style sparse storage — retained for bounded direct mapping
   and camera-window residency testing.

Do not add a StrataBrick-inspired fourth representation yet. No concretely
distinct structure/update rule has been identified that is not already covered
by the retained candidates.

**No representation is promoted.** C001a contains no GPU timing and does not use
Lane A's exact producer stream.

## Self-review

- all repository edits are inside Lane C ownership;
- no `research` or other lane merge was performed;
- no pull request was created;
- representation and ordering remain independent axes;
- the synthetic stream is used only for correctness/structural pruning;
- no favorable sort/grouping was introduced;
- all required cost categories have an explicit C001b measurement/accounting
  requirement;
- no microarchitectural cache claim is made from structural data;
- the raw artifact remains outside Git.

## Next gate

On the target system:

1. run `mise install`, `mise run research:check`, and
   `mise run build`;
2. rerun C001 through `mise run research:record`;
3. run the implemented Vulkan C001b validation matrix;
4. run the non-validation 3-repeat C001b timing matrix and record/analyze the
   resulting `c001b_summary.csv`;
5. keep producer locality separate from representation;
6. repeat the final comparison on Lane A's exact producer stream before any
   architectural promotion.


## C001b target-GPU run v1 — 2026-09-28

Status: **correctness accepted; representation decision provisional pending allocator rerun**

The uploaded 3-repeat `c001b_summary.csv` contained 90/90 rows with
`all_correct=true`.

### Key median GPU timings

| Occupancy | Phase | probe hash | hashed brick pool | virtual clipmap |
| ---: | --- | ---: | ---: | ---: |
| 4 | lookup | 8.296 us | 7.735 us | 7.494 us |
| 4 | initial-build-e2e | 22.202 us | 16.551 us | 10.861 us |
| 4 | residency-churn-e2e | 12.223 us | 110.169 us | 109.167 us |
| 16 | lookup | 37.111 us | 11.903 us | 9.618 us |
| 16 | initial-build-e2e | 85.803 us | 26.130 us | 19.998 us |
| 16 | residency-churn-e2e | 17.593 us | 111.091 us | 109.328 us |
| 48 | lookup | 189.560 us | 21.361 us | 18.635 us |
| 48 | initial-build-e2e | 479.070 us | 59.433 us | 53.341 us |
| 48 | residency-churn-e2e | 44.605 us | 111.452 us | 110.770 us |

At medium/dense occupancy, both brick representations decisively improve
lookup and initial-build cost in this synthetic source-order control. At
occupancy 48, virtual clipmap lookup is about 10.2x faster than the probe hash
and its initial build is about 9.0x faster.

Sparse occupancy does not establish a meaningful lookup win: all three lookup
medians are within roughly 11% at occupancy 4.

### Memory

| Occupancy | Representation | Persistent bytes |
| ---: | --- | ---: |
| 4 | probe hash | 1,048,576 |
| 4 | hashed brick pool | 3,856,400 |
| 4 | virtual clipmap | 3,790,864 |
| 16 | probe hash | 4,194,304 |
| 16 | hashed brick pool | 3,856,400 |
| 16 | virtual clipmap | 3,790,864 |
| 48 | probe hash | 16,777,216 |
| 48 | hashed brick pool | 3,856,400 |
| 48 | virtual clipmap | 3,790,864 |

This confirms the C001a crossover: probe hash remains strongly preferable in
persistent memory for sparse occupancy, while brick payload amortization wins
at medium/dense occupancy.

### Churn anomaly and required rerun

The brick candidates show a highly repeatable ~109–111 us one-brick-plane
churn cost almost independent of occupancy. The current shader's
`take_physical()` uses a shared free-count read plus a CAS retry loop for each
reclaimed brick. Under a plane-sized allocation batch, many invocations compete
on the same counter and can retry repeatedly.

This is a concrete algorithmic contention source visible in the implementation;
it is **not** a claim about a particular GPU cache or microarchitectural cause.
Because the current allocator can dominate the representation comparison,
C001b must be rerun after replacing the retrying pop with bounded batch-claim
bookkeeping.

No representation is promoted or rejected from v1. The sparse hash remains the
reference; both brick candidates remain under test.
