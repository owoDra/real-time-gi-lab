# Experiment 000 — page-local cache locality

Status: active  
Milestone: M0

## Question

Does a page-local contiguous cache reduce GPU lookup cost relative to a fair
open-addressed global hash baseline, and how much additional benefit comes from
grouping queries by page?

## Hypothesis

A radiance cache organized as directly-addressable coarse pages with contiguous
local payload should execute more coherently than a global open-addressed hash
cache. Grouping work by page should further improve wave/L2 locality.

## Scope

This experiment deliberately excludes:

- lighting quality;
- radiance interpolation;
- temporal stability;
- ray-query cost;
- surface-placement quality;
- multi-bounce transport;
- GPU cost of sorting/binning in M0.

Those would hide the memory-layout signal. GPU scheduling cost enters in M1.

## Workload

Sponza triangle centroids are quantized into 0.25 m cells. A page is 4 x 4 x 4
cells (64 local slots). Pages are assigned dense IDs for the M0 benchmark.

Every active logical cell receives one non-zero unique experiment key and one
semantic payload value. Both cache variants must return that same value.

### Hash baseline

- open addressing with linear probing;
- table capacity is the next power of two large enough for at most 0.5 load,
  based on **actual active cells**;
- the shader probe limit is the maximum probe depth observed while constructing
  the table;
- input queries remain in original workload order.

The M0 key is intentionally a unique logical-cell ID. Key construction is
outside the timed lookup so hash collisions in world-coordinate encoding cannot
silently invalidate semantic parity.

### Paged

- direct page table;
- contiguous 64-entry payload per page;
- original query order.

### Paged-sorted

Same storage as `paged`, but queries are stable-sorted by
`(page_id, local_index)` before dispatch.

CPU sorting is deliberately outside the timed region in M0. It measures the
upper bound of locality benefit. M1 must reproduce the ordering on GPU and count
its cost.

## Correctness contract

The CPU workload builder first verifies that hash and paged lookup resolve the
same value for every generated query.

After GPU execution, every variant reports:

- `checksum`;
- `expected_checksum`;
- `correct`.

A benchmark process exits non-zero when any variant is incorrect. Performance
numbers from an incorrect run are invalid.

## Required M0 matrix

The standard harness runs:

- query counts: 100k, 500k, 1M, 4M, 8M;
- three process-level repeats per query count;
- 100 timed dispatches per process by default.

Generated artifacts include raw rows, summarized medians, run logs, GPU name,
Git commit, workload parameters, and host metadata.

## Metrics

Primary:

- GPU microseconds per dispatch;
- speedup relative to corrected hash baseline;
- representation bytes;
- correctness checksum;
- active pages/cells and hash probe depth from logs.

Later profiling:

- L2 hit/miss behavior;
- device-memory transactions;
- wave occupancy;
- memory-stall percentage.

## Pass condition

M0 does not pass from one GPU number.

Proceed toward M1 only if:

1. all variants satisfy semantic parity;
2. page-local or page-sorted access shows a repeatable advantage across multiple
   query counts;
3. the effect remains under more than one locality regime.

M1 passes only if the advantage remains after GPU-side binning/sorting cost is
included.

If only sorted ordering wins while paged storage itself does not, prefer
investigating coherent scheduling on the simpler hash representation rather
than forcing a page-local architecture.
