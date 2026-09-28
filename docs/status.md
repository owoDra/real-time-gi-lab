# Research status

Last updated: 2026-09-28

## Current stage

**M0 — validate the page-local cache premise.**

The repository is currently isolating one claim: whether page-local contiguous
storage and locality-aware query ordering can materially reduce GPU lookup cost
relative to an open-addressed global hash cache.

This is not yet a GI renderer. Lighting quality, ray-query cost, temporal reuse,
surfel placement, and multi-bounce transport are intentionally excluded from M0.

## Current work

The corrected 4M-query run has passed the M0 semantic-correctness gate on one
hardware/workload point. The next task is to separate **cache representation**
from **query coherence / scheduling** before treating page-local storage as a
winning architecture.

Tracked work: [Issue #4 — isolate cache layout vs query coherence and include
GPU scheduling cost](https://github.com/owoDra/phos-gi-lab/issues/4).

The immediate controls are:

- add a `hash-sorted` variant using the same page-grouped order as
  `paged-sorted`;
- run source/random/page-grouped locality regimes for both representations;
- run the standard query-count/repeat matrix;
- move ordering to GPU-side binning/sorting and include that cost;
- profile cache/memory behavior once timing trends are stable.

## Accepted facts

- The Vulkan compute benchmark runs on **AMD Radeon 8060S Graphics (RADV
  STRIX_HALO)**.
- The current Sponza loader produced **262,241 triangle-centroid surface
  samples** in the first successful run.
- A 4,000,000-query workload produced **242,806 active pages** in that run.
- The page-sorted access order was substantially faster than unsorted paged
  access in the exploratory run, but the exact speedup is not yet accepted as
  evidence because the baseline had correctness/fairness defects described
  below.

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
- the current paged representation used about **15.05x** the lookup-storage
  bytes of the corrected hash baseline.

The strongest current interpretation is therefore **not** that page-local
storage alone wins. The evidence instead suggests that query coherence/work
ordering may dominate lookup performance on this workload. A `hash-sorted`
control is required before attributing the gain to the page-local
representation.

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

### M0 correctness gate

All variants must report `correct=true` against the same expected semantic
checksum. Any mismatch invalidates the run.

### M0 locality gate

After correctness is established, page-local layouts must show a repeatable
advantage across multiple query counts and at least two locality regimes. A
single 4M-query result is insufficient.

### M1 end-to-end scheduling gate

The advantage must survive **GPU-side** binning/sorting cost. CPU pre-sorting is
only an M0 upper-bound experiment.

If this gate fails, the project should investigate coherent scheduling on top of
a hash cache instead of assuming a new cache representation is necessary.

## Next measurements

The next research work is tracked in Issue #4.

1. Add `hash-sorted` to isolate representation from ordering.
2. Query-count sweep: 100k, 500k, 1M, 4M, 8M with repeated runs.
3. Locality regimes: source order, randomized, page-grouped, and later
   camera/temporal-coherent workloads.
4. GPU-side binning/sorting with its full end-to-end cost included.
5. GPU cache/memory counters to verify whether timing changes correspond to
   cache misses, transactions, stalls, or occupancy.
6. Only after layout/scheduling is resolved: read/write/update workloads,
   including dirty-page ratios.

## Not yet established

- that page-local storage is faster after the corrected hash baseline;
- that sorting remains worthwhile after GPU scheduling cost;
- that a surface cache improves GI quality;
- that this architecture is better than DDGI, SHaRC-like, Split RC, or ReSTIR
  end-to-end;
- that results generalize beyond RADV STRIX_HALO.
