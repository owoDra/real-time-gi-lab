# B002 — Lane A exact-stream traversal comparison

Status: accepted

## Decision

Promote **HWRT / TLAS** as the primary Lane B traversal architecture for the
measured target:

`AMD Radeon 8060S Graphics (RADV STRIX_HALO)`.

Retain the **hierarchical StrataBrick-derived traversal** as the software
fallback / portability candidate. It consistently improves on the simple
software BVH while using much less memory than HWRT, but it does not win any
measured performance regime.

Do not promote the simple **software BVH** beyond its baseline/reference role.
The raw sparse-grid DDA was already rejected as a standalone final architecture
by B001.

No measured representative or controlled-moving regime changes the performance
winner: HWRT is fastest in every accepted B002 row. This decision is specific to
the measured target and workload family; it is not evidence that HWRT is always
best on every GPU or memory budget.

## Accepted artifact

- artifact:
  `out/research/lane-b-traversal/002-lane-a-exact-stream-traversal/20260928T164136Z/`;
- measurement commit:
  `b4baf15c15331411690530a1f9e7388d4e7d6fe8`;
- branch: `research-lane-b-traversal`;
- tree: clean;
- runner return code: 0;
- target:
  `AMD Radeon 8060S Graphics (RADV STRIX_HALO)`;
- driver: RADV / Mesa 26.1.2;
- representative iterations: 30;
- build repeats: 3;
- validation layers: disabled for accepted timing.

The branch subsequently added `2d9cbc3e`, which only records the already-used
HWRT scratch-alignment property in provenance JSON. It does not change traversal,
build/update behavior, measured boundaries, or candidate semantics, so a further
measurement rerun is not required for this result.

## Representative workload

Final architectural evidence replays the accepted Lane A A001 natural producer
artifact:

`out/research/lane-a-split-rc/001-representative-producer/20260928T143212Z/`

from measurement commit
`8b647ef8dcf1150f86a9d25c039ca48bd7f30b8f`.

Exact streams:

| case | workload id | rays |
| --- | ---: | ---: |
| static | 16139458794081967227 | 31,392 |
| camera-motion | 15809339685104866027 | 31,296 |
| light-motion | 16301245569441789499 | 31,392 |

The scene is Sponza with 262,241 non-degenerate triangles. The hierarchical
candidate uses a producer-derived fixed segment size of 289.811218, 682
segments, 290,289 primitive memberships, 2,048 hash slots, and maximum probe
length 8.

## Correctness and HWRT capability gate

All accepted rows pass the B001 shared Hit contract:

- total representative mismatches: 0;
- total representative runtime errors: 0;
- full semantic checksum agrees across all three candidates within every exact
  A001 workload;
- CPU reference sampling passes brute-force parity;
- per-material glTF `doubleSided` face policy is preserved.

HWRT was proven on the explicitly selected target rather than inferred from
global extension text:

- exact physical-device match: true;
- `VK_KHR_acceleration_structure`: enabled;
- `VK_KHR_ray_query`: enabled;
- `VK_KHR_deferred_host_operations`: enabled;
- buffer device address: required/enabled;
- BLAS/TLAS creation: succeeded;
- ray-query shared-Hit correctness: passed.

This resolves B001's previous ambiguous multi-device HWRT probe.

## Representative traversal

GPU timestamp-query medians:

| workload | software BVH us | hierarchical us | HWRT/TLAS us |
| --- | ---: | ---: | ---: |
| static | 382.767 | 281.415 | 66.066 |
| camera-motion | 376.155 | 276.305 | 63.982 |
| light-motion | 383.469 | 295.281 | 67.128 |
| **mean** | **380.797** | **284.334** | **65.725** |

Across the three accepted A001 streams:

- hierarchical is 1.30x–1.36x faster than software BVH;
- HWRT is 5.71x–5.88x faster than software BVH;
- HWRT is 4.26x–4.40x faster than hierarchical.

The result is stable across static, camera-motion, and light-motion producer
streams; there is no representative regime-specific winner split.

## Construction and replay costs

Architecture-specific initial setup boundaries:

| candidate | measured setup components | setup us |
| --- | --- | ---: |
| software BVH | CPU BVH build + acceleration upload | 117,289.156 |
| hierarchical | membership/segment build + pack + acceleration upload | 125,468.981 |
| HWRT/TLAS | measured HWRT setup wall | 19,210.648 |

Breakdown:

- software BVH CPU build: 113,896.785 us;
- software acceleration upload: 3,392.371 us;
- hierarchical total CPU build: 115,043.464 us;
  - membership generation: 14,053.992 us;
  - segment construction: 100,796.357 us;
  - occupancy: 48.089 us;
- hierarchical GPU packing: 6,677.075 us;
- hierarchical acceleration upload: 3,748.442 us;
- HWRT acceleration-data upload: 6,849.701 us;
- HWRT BLAS build: 1,423.585 us;
- HWRT TLAS build: 72.017 us;
- HWRT complete setup wall: 19,210.648 us.

The HWRT wall setup measurement includes its internal upload/build/pipeline work,
so its breakdown values must not be added again to the wall value.

Per-stream parse/replay/ray-upload costs are recorded separately in the raw CSV.
They do not change the candidate ordering.

## Controlled moving-geometry maintenance

A001 has no moving geometry, so dynamic maintenance is deliberately recorded as
controlled mechanism-isolation evidence while retaining the A001 static replay
rays.

Controlled object:

- Sponza instance: 10;
- moved primitives: 880;
- bounds-only translation: 0.283018768;
- topology-changing translation: 362.264038;
- topology-change membership changes: 880.

All six maintenance rows report zero mismatches and zero runtime errors.

Total update + post-update trace cost, summing the recorded candidate-required
phases:

| regime | software BVH us | hierarchical us | HWRT/TLAS us |
| --- | ---: | ---: | ---: |
| bounds-only | 19,933.237 | 11,081.034 | 3,253.467 |
| topology-change | 17,979.975 | 10,105.977 | 3,247.523 |

Thus:

- hierarchical is about 1.78x–1.80x faster than software BVH end-to-end;
- HWRT is about 5.54x–6.13x faster than software BVH;
- HWRT is about 3.11x–3.41x faster than hierarchical.

Relevant mechanism detail:

- bounds-only hierarchical maintenance performs 21 localized segment refits and
  uploads 35,040 acceleration bytes;
- topology-changing hierarchical maintenance observes all 880 moved primitives
  changing membership, rebuilds 33 segments, and uploads 10,193,312 acceleration
  bytes;
- HWRT updates the moved geometry plus BLAS and TLAS, with BLAS update around
  404–406 us and TLAS update around 42 us in both controlled regimes.

The topology-changing row being slightly faster than the bounds-only row is not
interpreted as a topology-change advantage; upload/packing timing variation is
large relative to the mechanism difference. The robust conclusion is the
cross-candidate ordering, which is unchanged.

## Memory

Representative persistent allocation:

| candidate | persistent bytes | MiB | explicit scratch |
| --- | ---: | ---: | ---: |
| software BVH | 24,133,120 | 23.02 | 0 |
| hierarchical | 26,971,056 | 25.72 | 0 |
| HWRT/TLAS | 67,833,776 | 64.69 | 36,761,648 B / 35.06 MiB |

The hierarchy costs about 1.12x the persistent memory of the software BVH.
HWRT costs about 2.81x the software BVH persistent memory and additionally needs
about 35.06 MiB of reusable explicit AS scratch.

Software/hierarchical shaders also have a 512-byte logical traversal stack per
ray invocation in the benchmark implementation; this is distinct from the
explicit AS scratch accounting above.

Memory is therefore the principal measured cost against HWRT. On the target
machine it is not enough to offset HWRT's large build, maintenance, and traversal
advantages, but it is the main reason to keep the hierarchical software path as
a fallback rather than deleting that candidate.

## Candidate disposition

### Promoted: HWRT / TLAS

Promote as the Lane B primary choice for Integration #13 on the measured target.

Reasons:

- exact A001 correctness parity;
- explicit physical-device and feature proof;
- fastest traversal in all three representative streams;
- fastest controlled moving-geometry end-to-end maintenance in both regimes;
- substantially lower initial setup wall than either software candidate.

Trade-off:

- materially higher persistent + scratch memory.

### Retained fallback: hierarchical StrataBrick-derived traversal

Retain as the software/portability fallback, not as a co-equal target winner.

Reasons:

- exact A001 correctness parity;
- consistently faster than simple software BVH;
- localized bounds-only refit works as hypothesized;
- topology-changing membership is localized to affected segment rebuilds;
- much lower memory footprint than HWRT.

Limitations:

- segment construction and GPU packing are expensive;
- topology changes can expand upload volume substantially;
- no measured regime beats HWRT on the target.

### Rejected from primary architecture: software BVH

Keep only as the simple baseline/reference implementation.

It is correct and uses the least persistent memory, but loses to the hierarchy
on traversal and controlled maintenance, and loses much more strongly to HWRT.

### Rejected earlier: raw sparse-grid DDA

B001 already rejected raw sparse-grid DDA as a standalone final architecture.
B002 does not reopen that decision.

## Limitations

- Representative final GPU evidence is one real Sponza producer family on one
  target GPU.
- A001 contains no moving geometry; movement evidence is a separately controlled
  rigid-mesh translation experiment, not a natural moving-geometry producer
  capture.
- B001 covers sparse/dense/vertical mechanism controls, but B002 does not add
  separate final-GPU synthetic sparse/dense/vertical sweeps. Integration #13
  should retain large/vertical and dynamic-scene stress before making a complete
  end-to-end GI architecture claim.
- The benchmark compares traversal architectures, not final GI image quality or
  complete frame time.
- HWRT's memory cost may matter differently on lower-memory hardware.

## Lane B final decision

Lane B's decision gate is satisfied.

For the measured target and accepted Lane A producer workload:

1. **use HWRT/TLAS as the primary traversal architecture**;
2. **retain hierarchical StrataBrick-derived traversal as the software fallback**;
3. **retain simple software BVH only as baseline/reference**;
4. **do not restore raw sparse-grid DDA as a final candidate**.

Hand the primary HWRT result, its memory trade-off, and the hierarchical fallback
to Integration #13. Integration must still validate the combined GI pipeline;
Lane B does not claim that an isolated traversal winner alone makes the final GI
architecture superior.
