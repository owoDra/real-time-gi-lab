# Research status

Last updated: 2026-09-28

## Current stage

**M0 — cache representation resolved; investigate cheaper query coherence.**

The repository is isolating whether page-local contiguous storage has an
independent lookup advantage, or whether the observed gain is primarily caused
by coherent query scheduling.

This is not yet a GI renderer. Lighting quality, ray-query cost, temporal reuse,
surfel placement, multi-bounce transport, denoising, and ReSTIR are intentionally
excluded.

## Current work

Issue #4 resolved the representation-vs-ordering experiment. Follow-up work is
tracked in [Issue #7 — Research cheaper query coherence for hash cache](https://github.com/owoDra/phos-gi-lab/issues/7).

The first Issue #7 sub-experiment is now **Experiment 001: fused workgroup-local
hash-slot binning**. It tests whether a 256-thread lookup workgroup can recover
useful coherence by grouping only its own queries into 16 coarse initial-hash-slot
bins in shared memory. The grouping work is fused into the lookup dispatch, so
there is no global reorder buffer, separate scheduling dispatch, or global
scheduling scratch. Results are not accepted until the target-GPU validation and
non-validation matrix completes.

The Issue #4 branch implements the measurements that produced that decision:

- representation and ordering are independent benchmark axes;
- both hash and paged representations run source, randomized, and page-grouped
  workloads;
- CPU page grouping is page-only, avoiding the previous intra-page sort
  confound;
- GPU page grouping uses dense-page counting binning rather than a general radix
  sort;
- GPU grouping, grouped lookup, and grouping + lookup end-to-end cost are
  measured separately;
- GPU grouping receives an exact multiset/order correctness check in addition to
  lookup checksums;
- the standard 100k/500k/1M/4M/8M repeat harness records the new axes and timing
  fields without removing the original CSV columns;
- a reproducible RADV/RGP profiling procedure is documented.

The target-system correctness sweep and non-validation timing sweep have now
completed on AMD Radeon 8060S / RADV STRIX_HALO. Issue #4 has enough evidence
to resolve the representation-vs-scheduling question and the current explicit
GPU-grouping viability gate.

## Accepted facts

- The Vulkan compute benchmark runs on **AMD Radeon 8060S Graphics (RADV
  STRIX_HALO)**.
- The Sponza loader produced **262,241 triangle-centroid surface samples** in
  the first successful run.
- A 4,000,000-query workload produced **242,806 active pages** in that run.
- A corrected single 4M run established semantic parity across the old hash,
  paged, and paged-sorted variants.
- That run shows a large ordering effect for the paged representation, but it
  does not establish whether page-local storage itself is responsible.

## Evidence ledger

### 2026-09-28 — corrected 4M Sponza lookup run

Hardware: AMD Radeon 8060S Graphics, RADV STRIX_HALO  
Queries: 4,000,000  
Iterations: 100  
Surface samples: 262,241  
Active pages: 242,806  
Active cells: 261,659  
Hash slots: 524,288  
Hash maximum probe depth: 34  
Shared checksum: 8587727892303652

| Variant | GPU us/dispatch | Representation bytes | Correct |
| --- | ---: | ---: | --- |
| hash | 813.455 | 4194304 | true |
| paged | 1592.06 | 63129560 | true |
| paged-sorted | 499.223 | 63129560 | true |

**Status: accepted as a corrected single-run observation; not sufficient to
pass M0.**

All variants returned the same expected semantic checksum, so the correctness
gate passed for this run.

Observed relationships:

- unsorted `paged` was about **1.96x slower** than `hash`;
- `paged-sorted` was about **1.63x faster** than `hash`;
- sorting the paged workload improved the same representation by about
  **3.19x**;
- the paged representation used about **15.05x** the lookup-storage bytes of the
  corrected hash baseline.

Protocol note: this historical `paged-sorted` implementation sorted by
`(page_id, local_index)`. Issue #4 now uses stable page-only grouping to avoid
mixing page scheduling with intra-page ordering. Therefore the 499.223 us value
remains evidence that coherent ordering matters, but it is not a direct
substitute for the new `paged/page-grouped` row.

The strongest current interpretation is still **not** that page-local storage
alone wins. The evidence motivates the layout-vs-scheduling controls now
implemented.

### 2026-09-28 — first successful Sponza GPU run

Hardware: AMD Radeon 8060S Graphics, RADV STRIX_HALO  
Queries: 4,000,000  
Iterations: 100

| Variant | GPU us/dispatch | Allocated bytes | Checksum |
| --- | ---: | ---: | ---: |
| hash | 15151.6 | 268435456 | 8590467905938798 |
| paged | 1665.99 | 63129560 | 8587727892303652 |
| paged-sorted | 506.926 | 63129560 | 8587727892303652 |

**Status: invalid as comparative evidence; retained as a diagnostic result.**

Two defects were identified:

1. Hash and paged variants generated different payload values, so checksum
   parity was impossible even with correct lookup behavior.
2. The hash table was sized from `page_count * 64` rather than the number of
   actually active cells, over-provisioning the hash baseline and distorting
   both memory and cache behavior.

The run remains useful because it demonstrated the benchmark executes and
suggested query ordering may be important, but its speedup ratios must not be
used as research conclusions.

## Decision gates

### Correctness

Every row must report `correct=true` against the same semantic checksum. GPU
page grouping must also preserve the exact query multiset and produce monotonic
page groups. Any mismatch invalidates performance results from that process.

### Representation vs scheduling

Compare representation under the **same ordering**.

- If hash/page-grouped is approximately equal to or faster than
  paged/page-grouped, coherent scheduling is the leading result. Do not promote
  the paged cache; prioritize hash + coherent scheduling.
- If paged/page-grouped remains clearly faster than hash/page-grouped beyond
  repeat-to-repeat variation across the matrix, page-local contiguous storage
  has independent evidence.

Randomized rows are a second locality regime and help determine whether the
representation difference is robust rather than an artifact of source order.

### GPU scheduling viability

CPU page grouping is only an upper bound. The relevant practical comparison is
GPU grouping + lookup end-to-end against hash/source.

If the benefit disappears after histogram/prefix/scatter cost is included, the
current explicit grouping strategy fails the scheduling viability gate. A
cheaper grouping method may be tested, but the CPU-preordered gain alone is not
enough to advance the architecture.

### Memory-behavior evidence

Timing is necessary but insufficient for a locality claim. Once timing trends
are stable, inspect representative cases with the
[RADV/RGP profiling procedure](profiling/radv-rgp.md) and record whether cache
behavior, memory traffic/stalls, and occupancy support the interpretation.

## Next measurements

1. Keep the hash representation as the baseline; do not promote paged storage
   from Experiment 000.
2. Investigate coherence that is produced cheaply or naturally rather than a
   full post-generation histogram/prefix/scatter pass.
3. Prefer producer-side locality, coarse/workgroup-local binning, or reuse of a
   schedule across multiple consumers/frames before another global reorder.
4. Require any replacement scheduler to beat hash/source **end-to-end**, not
   only after excluding its own scheduling cost.
5. Use RADV/RGP on representative source vs grouped cases before making a
   microarchitectural cache-locality claim.

## Not yet established

- the exact cache/memory mechanism behind the observed ordering effect;
- that any practical low-cost coherence strategy beats hash/source end-to-end;
- that the dense-page GPU grouping implementation is useful outside this
  diagnostic experiment;
- that a surface cache improves GI quality;
- that this architecture is better than DDGI, SHaRC-like, Split RC, or ReSTIR
  end-to-end;
- that results generalize beyond RADV STRIX_HALO.

## Target-system validation status

- **2026-09-28 validation sweep passed** on AMD Radeon 8060S Graphics / RADV STRIX_HALO for 100k, 500k, 1M, 4M, and 8M queries, 3 repeats each.
- All representation × ordering rows and GPU page-grouping rows completed with the benchmark correctness guards intact; the sweep produced artifacts successfully.
- Validation timings remain diagnostic only; the accepted performance evidence is the non-validation sweep below.

### 2026-09-28 — accepted representation × ordering + GPU scheduling sweep

Hardware: AMD Radeon 8060S Graphics, RADV STRIX_HALO  
Scene: Sponza, 262,241 surface samples  
Iterations: 100  
Repeats: 3 per query count  
Validation: disabled for timing run

| Queries | hash/source us | hash/page-grouped us | paged/source us | paged/page-grouped us | GPU scheduling us | hash GPU-grouped end-to-end us |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 100k | 16.080 | 24.022 | 23.907 | 15.362 | 181.947 | 205.106 |
| 500k | 96.117 | 62.727 | 203.899 | 167.810 | 526.509 | 575.499 |
| 1M | 198.459 | 68.855 | 403.669 | 253.938 | 674.715 | 801.189 |
| 4M | 822.638 | 376.244 | 1749.210 | 514.496 | 2521.140 | 2858.350 |
| 8M | 1806.870 | 733.350 | 3521.690 | 886.843 | 4868.560 | 5531.450 |

**Status: accepted for the Experiment 000 decision gates.**

Observed relationships:

- At 500k, 1M, 4M, and 8M, page grouping improves hash lookup by about
  **1.53x, 2.88x, 2.19x, and 2.46x** respectively.
- At those same sizes, hash/page-grouped is faster than paged/page-grouped.
  The paged lookup therefore does not show an independent matched-order
  advantage at the practically relevant medium/large query counts.
- The 100k case is overhead-dominated and differs: paged/page-grouped is the
  fastest lookup-only row there, while hash/page-grouped regresses relative to
  hash/source. This does not reverse the medium/large-workload result.
- GPU-produced page grouping yields lookup timings close to CPU-preordered
  grouping at larger sizes, so the grouping operation successfully creates the
  intended useful ordering.
- The scheduler cost dominates the saved lookup time. Hash GPU-grouped
  end-to-end is about **12.76x, 5.99x, 4.04x, 3.47x, and 3.06x slower** than
  hash/source from 100k through 8M.

Experiment 000 therefore resolves Issue #4 as follows:

1. **Query ordering/coherence is the leading observed effect.**
2. **Page-local contiguous storage is not promoted**; matched-order hash is the
   better baseline for medium/large workloads and uses far less representation
   memory.
3. **The current global GPU histogram/prefix/scatter scheduler fails the
   end-to-end viability gate.**
4. The next research direction is not a faster paged cache. It is a cheaper way
   to obtain coherence, preferably at query production time or by amortizing /
   reusing ordering rather than globally reordering every lookup batch.
5. RGP profiling is still required before attributing the ordering effect to a
   specific cache/memory microarchitectural mechanism.
