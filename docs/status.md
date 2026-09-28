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

The current work item is to establish a trustworthy M0 baseline:

- require hash/paged variants to return the same semantic payload;
- size the hash table from actual active cells rather than unused page capacity;
- make the GPU hash probe bound match the constructed table;
- sweep multiple query counts and repeated runs with a reproducible harness;
- record hardware, commit, workload, raw rows, and summarized medians.

After that, M0 expands to multiple locality regimes. M1 then moves page
binning/sorting onto the GPU and includes its cost.

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

1. Query-count sweep: 100k, 500k, 1M, 4M, 8M.
2. Repeated runs to establish variance/median.
3. Locality regimes: source order, randomized, page-grouped, and later
   camera/temporal-coherent workloads.
4. Read/write/update workloads, including dirty-page ratios.
5. GPU cache/memory counters to confirm whether gains come from reduced misses
   and stalls rather than unrelated effects.

## Not yet established

- that page-local storage is faster after the corrected hash baseline;
- that sorting remains worthwhile after GPU scheduling cost;
- that a surface cache improves GI quality;
- that this architecture is better than DDGI, SHaRC-like, Split RC, or ReSTIR
  end-to-end;
- that results generalize beyond RADV STRIX_HALO.
