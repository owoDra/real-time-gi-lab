# Research status

Last updated: 2026-09-28

## Current stage

**M0 — resolve cache representation vs scheduling, including GPU scheduling
cost.**

The repository is isolating whether page-local contiguous storage has an
independent lookup advantage, or whether the observed gain is primarily caused
by coherent query scheduling.

This is not yet a GI renderer. Lighting quality, ray-query cost, temporal reuse,
surfel placement, multi-bounce transport, denoising, and ReSTIR are intentionally
excluded.

## Current work

Tracked work: [Issue #4 — isolate cache layout vs query coherence and include
GPU scheduling cost](https://github.com/owoDra/phos-gi-lab/issues/4).

The Issue #4 work branch now implements the measurements needed to make that
decision:

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

**No new target-GPU benchmark result from this implementation has been accepted
yet.** The next evidence step is to run the matrix on AMD Radeon 8060S / RADV
and record the results below.

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

1. Run `mise run bench:sweep` on the target AMD Radeon 8060S / RADV system.
2. Confirm all rows pass semantic and GPU-grouping correctness.
3. Compare hash vs paged at source, randomized, and page-grouped order.
4. Compare page-grouped lookup-only gains against GPU grouping + lookup
   end-to-end cost.
5. Repeat representative cases under RADV/RGP and inspect memory/cache/wave
   behavior.
6. Record the accepted or invalidated matrix in this Evidence ledger.
7. Only after Issue #4 is resolved, decide whether M1 should prioritize paged
   storage, hash + coherent scheduling, a cheaper grouping method, or a
   different direction.

## Not yet established

- that page-local storage is faster than hash under matched ordering;
- that coherent scheduling is worthwhile after GPU grouping cost;
- that the dense-page GPU grouping implementation is the best scheduling
  mechanism;
- that a surface cache improves GI quality;
- that this architecture is better than DDGI, SHaRC-like, Split RC, or ReSTIR
  end-to-end;
- that results generalize beyond RADV STRIX_HALO.
