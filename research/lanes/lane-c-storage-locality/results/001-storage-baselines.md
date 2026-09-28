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
- medium occupancy to be allowed to make brick storage structurally plausible.

## Structural measurements

| Regime | Representation | Active probes | Persistent bytes | Shift eviction/invalidation units |
| --- | --- | ---: | ---: | ---: |
| sparse (4/brick) | probe hash | 6,912 | 262,144 | 576 probes |
| sparse (4/brick) | hashed brick pool | 6,912 | 528,640 | 144 bricks |
| sparse (4/brick) | virtual clipmap | 6,912 | 518,400 | 144 bricks |
| medium (16/brick) | probe hash | 27,648 | 1,048,576 | 2,304 probes |
| medium (16/brick) | hashed brick pool | 27,648 | 528,640 | 144 bricks |
| medium (16/brick) | virtual clipmap | 27,648 | 518,400 | 144 bricks |
| dense (48/brick) | probe hash | 82,944 | 4,194,304 | 6,912 probes |
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
memory-efficient. At 4 probes per brick, the per-probe hash uses 256 KiB while
the brick candidates use about 506–516 KiB.

At 16 and 48 probes per brick, physical brick payload is amortized across more
live probes and both brick candidates become structurally memory-plausible.
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
3. implement GPU lookup/update/allocation/residency/eviction/invalidation
   measurement for the retained three representations;
4. keep producer locality separate from representation;
5. repeat the final comparison on Lane A's exact producer stream before any
   architectural promotion.
