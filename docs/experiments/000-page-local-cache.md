# Experiment 000 — page-local cache locality

Status: concluded  
Milestone: M0 / scheduling viability gate

## Question

How much of the GPU lookup result is caused by:

1. cache representation;
2. query ordering / locality;
3. their interaction;
4. the GPU cost required to create a coherent order?

The experiment must distinguish those effects before page-local storage is
promoted as an architecture premise.

## Hypotheses

Two hypotheses are intentionally tested independently:

- **representation hypothesis:** under the same query order, a page-local
  contiguous cache is faster than the open-addressed hash baseline;
- **scheduling hypothesis:** grouping otherwise identical queries by page
  improves either representation enough to justify the ordering cost.

Neither hypothesis is assumed true.

## Scope

This experiment deliberately excludes:

- lighting quality;
- radiance interpolation;
- temporal reuse;
- ray-query cost;
- surface-placement quality;
- multi-bounce transport;
- denoising or ReSTIR-style reuse.

Those features would hide the layout/scheduling signal.

## Workload

Sponza triangle centroids are quantized into 0.25 m cells. A page is 4 x 4 x 4
cells (64 local slots). Pages are assigned dense IDs for this experiment.

Every active logical cell receives one non-zero unique experiment key and one
semantic payload value. All representation/ordering combinations operate on the
same multiset of queries and must return that same value.

### Representations

#### Hash

- open addressing with linear probing;
- capacity is the next power of two large enough for at most 0.5 load;
- sizing is based on **actual active cells**, not page capacity;
- the shader probe limit is the maximum probe depth observed while constructing
  the table.

The key is a unique logical-cell ID. Key construction is outside the timed
lookup so coordinate-key collisions cannot silently invalidate semantic parity.

#### Paged

- dense direct page table;
- contiguous 64-entry payload per page.

Representation bytes are reported separately from scheduling scratch memory.

### Ordering regimes

Ordering is an independent axis from representation.

- **source** — query order produced by the workload generator;
- **randomized** — deterministic shuffle of exactly the same queries;
- **page-grouped** — CPU stable-sort by `page_id` only.

The page-grouped control deliberately does **not** additionally sort by
`local_index`. The previous exploratory `paged-sorted` implementation sorted
by `(page_id, local_index)`, which mixed page scheduling with intra-page
ordering. Its historical timing remains valid as an observation, but new
layout-vs-scheduling comparisons use page-only grouping.

Every CPU ordering is run against both hash and paged representations. This
creates the primary factorial comparison:

| Representation | source | randomized | page-grouped |
| --- | --- | --- | --- |
| hash | yes | yes | yes |
| paged | yes | yes | yes |

CPU ordering construction is outside the timed lookup and therefore remains an
upper-bound control rather than an end-to-end result.

## GPU page grouping

A general-purpose GPU radix sort is not required to answer this experiment.
Page IDs are already dense, so the first GPU scheduling implementation uses a
targeted counting-binning pipeline:

1. clear per-page counts and cursors;
2. histogram queries by `page_id`;
3. compute exclusive offsets for dense page bins;
4. scatter queries into contiguous page ranges.

The prefix pass uses one 256-thread workgroup. Each lane scans a contiguous
chunk of the dense page-count array after a shared-memory scan of chunk totals.
This intentionally trades generality for a small experiment-specific
implementation. If page count grows enough for this pass to become dominant,
that is evidence to replace the prefix implementation, not a reason to hide its
cost.

GPU scatter is not required to preserve source order within each page. The
correctness contract is page grouping plus exact query-multiset preservation.

### Timed regions

Timing boundaries are part of the protocol:

- **CPU-preordered lookup:** lookup dispatch plus the synchronization required
  between repeated writes to the validation output buffer. CPU ordering,
  uploads, downloads, and checksum calculation are excluded.
- **GPU scheduling:** counter/cursor clears + histogram + prefix + scatter,
  including required barriers. Uploads and CPU validation are excluded.
- **GPU-grouped lookup:** lookup on the already GPU-grouped buffer, with
  scheduling excluded.
- **GPU end-to-end:** GPU scheduling + grouped lookup for each measured
  iteration, including required synchronization.

The benchmark reports scheduling and end-to-end timings separately so a fast
lookup cannot hide an impractical grouping cost.

## Correctness contract

Correctness gates performance evidence.

Before GPU execution:

- hash and paged CPU lookup must resolve the same value for every source query;
- source, randomized, and page-grouped orderings must preserve the same semantic
  checksum;
- CPU page-grouped order must be monotonic by page.

After GPU execution:

- every lookup row reports `checksum`, `expected_checksum`, and `correct`;
- all representation/ordering rows must share one semantic checksum;
- GPU grouping is downloaded once outside timed regions and checked for:
  - monotonic `page_id`;
  - valid logical-cell key relation;
  - exact key multiplicity, so missing/duplicated queries cannot pass via a
    checksum collision;
- the GPU end-to-end lookup output must also match the expected checksum.

The process exits non-zero when any row fails. Performance numbers from an
incorrect run are invalid evidence.

## Required matrix

The standard harness remains:

- query counts: 100k, 500k, 1M, 4M, 8M;
- three process-level repeats per query count;
- 100 timed iterations per process by default.

Run:

```bash
mise run bench:sweep
```

Generated artifacts retain the existing metadata/raw CSV/summary/log layout.
The original CSV fields remain present; representation, ordering, scheduling
memory, scheduling time, and end-to-end time are additive fields.

## Metrics

Primary timing/memory metrics:

- lookup GPU microseconds per dispatch;
- representation bytes;
- GPU scheduling scratch bytes;
- GPU scheduling microseconds;
- GPU scheduling + lookup end-to-end microseconds;
- correctness checksum.

Derived comparisons:

- same-order paged vs hash isolates the representation effect;
- page-grouped vs source within one representation isolates the ordering effect;
- `ordering_interaction_ratio_vs_hash` reports the ordering speedup for a
  representation divided by the hash ordering speedup (1.0 means equal
  sensitivity to ordering);
- GPU end-to-end vs hash/source determines whether scheduling survives its own
  cost.

Once timestamp trends are stable, use the reproducible
[RADV/RGP profiling procedure](../profiling/radv-rgp.md) to inspect cache
behavior, memory traffic/stalls, and occupancy. Profiling captures are
diagnostic evidence and are not mixed with normal benchmark timestamps.

## Decision gates

### Representation vs scheduling

If hash/page-grouped is approximately equal to or faster than
paged/page-grouped, coherent scheduling is the leading explanation. Do not
promote paged storage; prioritize the simpler hash representation with coherent
scheduling.

If paged/page-grouped remains materially faster than hash/page-grouped across
the matrix, query coherence alone cannot explain the result. Page-local
contiguous representation then retains independent value for the next
milestone.

No fixed percentage is declared "material" before measurement. The difference
must be larger than repeat-to-repeat variation and persist across multiple query
counts/locality regimes.

### GPU scheduling viability

CPU-preordered results are only an upper bound.

If GPU scheduling + lookup loses the relevant advantage over hash/source, the
current scheduling strategy does not pass the end-to-end gate. Investigate a
cheaper grouping strategy or stop treating explicit sorting/binning as a viable
frame-time technique.

If the advantage survives GPU scheduling cost, scheduling can advance to the
next experiment.

### Memory-behavior evidence

Timing alone is insufficient for a locality claim. Before attributing a win to
cache locality, representative profiles must show a compatible change in cache
behavior, memory transactions/bandwidth, stalls, occupancy, or wave execution.

## Not answered by Experiment 000

This experiment does not establish:

- GI image quality;
- temporal behavior under camera motion;
- write/update cost or dirty-page maintenance;
- behavior with dynamic geometry;
- generalization beyond the tested GPU/driver/workload;
- superiority to DDGI, SHaRC-like caches, Split RC, ReSTIR, or other complete
  GI systems.


## Conclusion

The accepted 2026-09-28 AMD Radeon 8060S / RADV STRIX_HALO sweep resolves the
experiment's two primary questions.

For 500k through 8M queries, page grouping improves hash lookup by roughly
1.53x–2.88x while matched-order hash remains faster than matched-order paged.
At 4M queries, for example, hash/source is 822.638 us, hash/page-grouped is
376.244 us, and paged/page-grouped is 514.496 us. The paged representation
therefore does not retain an independent lookup advantage once ordering is
controlled at the medium/large workload sizes that dominate this experiment.

The GPU counting-binning implementation also demonstrates that the same useful
ordering can be created on the GPU: grouped lookup is close to the
CPU-preordered control at larger sizes. However, the scheduler cost overwhelms
the lookup savings. At 4M queries, scheduling costs 2521.140 us and
hash scheduling + grouped lookup costs 2858.350 us end-to-end versus 822.638 us
for hash/source. Across the matrix, hash GPU-grouped end-to-end is about
3.06x–12.76x slower than hash/source.

Therefore:

- **representation hypothesis:** not supported strongly enough to promote paged
  storage; hash remains the baseline;
- **scheduling hypothesis:** supported for lookup-only execution; query ordering
  is a major observed performance axis;
- **current GPU scheduling implementation:** fails the practical end-to-end
  gate;
- **next direction:** obtain coherence more cheaply, preferably while producing
  queries or by amortizing/reusing ordering rather than globally reordering
  every batch.

This conclusion is about the controlled ordering effect, not its precise GPU
cache mechanism. RADV/RGP evidence is still required before attributing the
effect to specific cache-hit, memory-traffic, stall, or occupancy behavior.
