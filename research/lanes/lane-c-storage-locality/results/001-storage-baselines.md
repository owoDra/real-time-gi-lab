# C001 result — storage baseline candidate pruning

Status: **accepted — per-probe sparse hash promoted as the current Split RC
radiance-storage foundation for the measured exact workload**

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

Synthetic C001b is complete. The remaining promotion gate is the exact Lane A
producer stream:

1. obtain passing A001 target-GPU exports for static, camera-motion, and
   light-motion;
2. consume each recorded `stream-v1.bin` in its observed append order;
3. compare the retained probe-hash and virtual/clipmap candidates without a
   post-generation sort/grouping;
4. include any producer work needed to derive storage address/residency units;
5. keep hashed-brick-pool only as a fallback diagnostic if bounded virtual
   addressing does not fit the actual stream;
6. make no final storage promotion until all exact-stream cases pass correctness
   and repeatability gates.


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


## C001b target-GPU run v2 — allocator-corrected rerun

Status: **accepted for synthetic Vulkan candidate pruning; final Lane A replay still required**

The allocator-corrected 3-repeat target-GPU summary contained 90/90 rows with
`all_correct=true`.

### Allocator correction validation

The v1 brick/clipmap churn plateau was removed by replacing the shared CAS
retrying free-list pop with bounded per-brick claims plus one finalize dispatch.

| Occupancy | Representation | v1 churn | v2 churn | Improvement |
| ---: | --- | ---: | ---: | ---: |
| 4 | hashed brick pool | 110.169 us | 13.626 us | 8.1x |
| 4 | virtual clipmap | 109.167 us | 8.817 us | 12.4x |
| 16 | hashed brick pool | 111.091 us | 14.387 us | 7.7x |
| 16 | virtual clipmap | 109.328 us | 9.939 us | 11.0x |
| 48 | hashed brick pool | 111.452 us | 15.189 us | 7.3x |
| 48 | virtual clipmap | 110.770 us | 10.941 us | 10.1x |

The probe-hash control changed much less except at the largest workload. This
supports treating the v1 plateau as an implementation-level allocator
bottleneck, not as evidence against brick-granularity residency.

### End-to-end comparison

`producer+lookup` is the preferred lookup comparison because it includes the
representation-specific address-generation work and was repeatable in v2.

| Occupancy | probe hash | hashed brick pool | virtual clipmap |
| ---: | ---: | ---: | ---: |
| 4 | 11.221 us | 10.620 us | 9.298 us |
| 16 | 47.490 us | 20.399 us | 18.155 us |
| 48 | 236.650 us | 47.530 us | 43.122 us |

Virtual clipmap is about 2.6x faster than the probe hash at occupancy 16 and
5.5x faster at occupancy 48 for `producer+lookup`.

Initial-build medians:

| Occupancy | probe hash | hashed brick pool | virtual clipmap |
| ---: | ---: | ---: | ---: |
| 4 | 22.282 us | 15.309 us | 9.779 us |
| 16 | 82.517 us | 26.250 us | 19.958 us |
| 48 | 425.048 us | 49.815 us | 42.080 us |

Allocator-corrected residency churn medians:

| Occupancy | probe hash | hashed brick pool | virtual clipmap |
| ---: | ---: | ---: | ---: |
| 4 | 12.424 us | 13.626 us | 8.817 us |
| 16 | 17.032 us | 14.387 us | 9.939 us |
| 48 | 32.061 us | 15.189 us | 10.941 us |

Virtual clipmap now wins the complete one-plane churn sequence at all three
occupancies in this synthetic control.

### Persistent memory

| Occupancy | probe hash | hashed brick pool | virtual clipmap |
| ---: | ---: | ---: | ---: |
| 4 | 1,048,576 B | 3,856,400 B | 3,790,864 B |
| 16 | 4,194,304 B | 3,856,400 B | 3,790,864 B |
| 48 | 16,777,216 B | 3,856,400 B | 3,790,864 B |

The probe hash remains the clear sparse-memory control. Virtual clipmap crosses
below the probe hash by the medium occupancy case and remains bounded across the
dense case.

### Repeatability note

The standalone virtual-clipmap `lookup` row was unstable at occupancy 4
(6.372–23.445 us) and had one high repeat at occupancy 16. The corresponding
`producer+lookup` rows were stable enough for candidate pruning, and the
decision below does not rely on the unstable lookup-only rows. No
microarchitectural explanation is inferred from this timing behavior.

### C001b candidate decision

Carry forward two primary representations:

1. **per-probe sparse hash** — mandatory baseline and sparse-memory candidate;
2. **virtual/clipmap sparse storage** — primary brick-granularity candidate.

Do not carry the hashed contiguous brick pool as a primary representation into
the next exact-stream comparison. In the bounded C001b workload, virtual
clipmap has slightly lower persistent memory and better end-to-end lookup,
initial build, allocation/residency, and corrected churn behavior. The hashed
brick implementation remains in-tree as a diagnostic/fallback control for a
case where the exact Lane A stream proves that bounded virtual addressing is
not suitable.

This is candidate pruning, **not architectural promotion**. Final selection
still requires the exact Lane A producer stream and accounting for any extra
producer work needed to emit virtual brick/page residency units.


## C001c implementation status

C001c exact Lane A stream replay is implemented on the lane branch.

It:

- parses and validates schema-v1 `stream-v1.bin` including FNV workload identity;
- preserves the recorded GPU append order with no CPU sort/grouping;
- processes every raw work item in the measured GPU address path;
- selects one storage event per A001 output via `ray_index == 0` on GPU;
- compares the retained probe-hash and virtual/clipmap candidates;
- measures producer+lookup/update/invalidation/allocation and initial build;
- verifies exact values and allocator invariants;
- aggregates static, camera-motion, and light-motion repeats through
  `c001c_matrix.py`.

Target-GPU C001c evidence is still pending. C001 remains active until those
three exact-stream cases pass correctness/repeatability and the remaining
virtual-window maintenance boundary is resolved.


## C001c target-GPU exact-stream result

Status: **accepted for exact-stream steady-state comparison; dynamic window
transition remains unresolved**

The 3-repeat, 100-iteration target-GPU run passed correctness for all 36
summary rows across static, camera-motion, and light-motion.

All three cases replayed the recorded Lane A append order directly.

### End-to-end medians

| Case | Phase | probe hash | virtual clipmap | clipmap delta |
| --- | --- | ---: | ---: | ---: |
| static | producer+lookup | 8.135 us | 6.853 us | -15.8% |
| static | producer+allocation-residency | 7.855 us | 6.693 us | -14.8% |
| static | initial-build-e2e | 9.819 us | 7.935 us | -19.2% |
| camera-motion | producer+lookup | 7.093 us | 6.773 us | -4.5% |
| camera-motion | producer+allocation-residency | 7.895 us | 6.452 us | -18.3% |
| camera-motion | initial-build-e2e | 9.899 us | 7.975 us | -19.4% |
| light-motion | producer+lookup | 7.414 us | 6.773 us | -8.6% |
| light-motion | producer+allocation-residency | 7.534 us | 6.452 us | -14.4% |
| light-motion | initial-build-e2e | 10.059 us | 7.975 us | -20.7% |

Update/invalidation differences were much smaller. Camera-motion invalidation
slightly favored the hash (6.572 us vs 6.693 us); the other measured mutation
medians slightly favored clipmap.

### Persistent memory

The exact streams contain 1,537 unique probes. The hash uses 32,768 bytes.
Virtual clipmap uses:

- 82,280 bytes for static;
- 84,880 bytes for camera-motion;
- 82,280 bytes for light-motion.

Thus the exact-stream clipmap uses about 2.51-2.59x the persistent storage of
the sparse hash for this sparse workload, despite its better measured GPU
build/residency timing.

### Repeatability

Allocation/residency and initial-build results were repeatable enough to retain
the clipmap performance advantage. Lookup had isolated high repeats:

- static clipmap lookup: 6.733 / 6.853 / 9.218 us;
- light-motion hash lookup: 7.134 / 7.414 / 10.139 us.

Therefore C001c does not use lookup alone as promotion evidence. The stronger
evidence is the repeatable ~14-18% allocation/residency reduction and ~19-21%
initial-build reduction.

### Decision after C001c

Do not promote either representation yet.

Virtual clipmap remains the performance candidate, while probe hash remains the
memory-efficient baseline. C001c normalizes each frame to a replay-local
clipmap origin outside GPU timing, so it does not measure the cost of
maintaining/changing that bounded virtual window across camera motion.

The final C001 gate is therefore a real exact-stream transition measurement,
starting with static -> camera-motion, that includes the storage residency
changes required by the virtual window. A final promotion must account for this
cost rather than treating per-frame origin selection as free.


## C001d target-GPU exact transition result

Status: **accepted; final C001 gate passed**

The 3-repeat, 100-iteration static -> camera-motion transition passed
correctness for all four summary rows.

Exact transition shape:

- probes: 1,537 -> 1,537;
- entering probes: 446;
- leaving probes: 446;
- bricks: 278 -> 288;
- entering bricks: 32;
- leaving bricks: 22.

### Transition timing

| Representation | Producer address | Transition E2E | Repeat range |
| --- | ---: | ---: | ---: |
| probe hash | 5.130 us | 11.702 us | 10.740-11.823 us |
| virtual clipmap | 5.370 us | 14.267 us | 13.906-15.109 us |

The virtual clipmap transition is about **21.9% slower** than the probe hash
when the required dynamic residency/window work is included.

Producer-address cost is close: virtual clipmap is about 4.7% slower
(5.370 vs 5.130 us). The deciding difference is therefore the complete
transition path, not address generation alone.

### Memory

| Representation | Persistent bytes | Scratch bytes |
| --- | ---: | ---: |
| probe hash | 32,768 | 500,736 |
| virtual clipmap | 94,864 | 500,736 |

The clipmap uses about **2.90x** the persistent storage of the probe hash in the
transition-capable implementation. Scratch is identical because both replay the
same exact target stream and use the same address workspace.

### Final C001 decision

**Promote the per-probe open-addressed sparse hash as the current Lane C storage
foundation for Split RC on the measured representative exact workload.**

This decision is based on the complete evidence chain:

1. C001a showed that sparse occupancy can strongly favor the packed probe hash
   in memory and prevented brick storage from being treated as an automatic win.
2. C001b showed that brick/clipmap layouts can outperform the hash at
   medium/dense synthetic occupancy and justified carrying virtual clipmap
   forward.
3. C001c showed a real steady-state exact-stream performance advantage for
   virtual clipmap: about 14-18% lower allocation/residency cost and about
   19-21% lower initial-build cost on the three A001 cases.
4. C001d then charged the missing static -> camera-motion residency/window
   transition work. Under that complete dynamic path, the hash is about 18%
   faster in absolute transition time (11.702 vs 14.267 us), while also using
   roughly one third of the persistent memory.

The clipmap is therefore **not rejected as universally inferior**. It remains a
useful follow-up candidate if future representative workloads become
materially denser, if residency persists over many frames with infrequent
window transitions, or if a later producer can provide clip/page maintenance
at lower incremental cost.

The hashed contiguous brick pool remains diagnostic/fallback only.

No post-generation sort or favorable global reorder was introduced in the
accepted exact-stream evidence, and no microarchitectural cache mechanism is
claimed from timestamps alone.

## Lane C conclusion

C001 is complete. The accepted storage baseline is:

- **per-probe open-addressed sparse hash** for the current representative Split
  RC workload;
- preserve natural producer order;
- do not add a global scheduler solely to compensate for storage locality;
- keep virtual clipmap/brick approaches as conditional future candidates for a
  demonstrably denser or more residency-stable workload.

Further locality research should now build on this accepted baseline rather
than reopening representation selection without new workload evidence.
