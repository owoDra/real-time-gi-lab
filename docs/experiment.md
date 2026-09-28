# Experiment 0 — page locality before GI

## Hypothesis

A radiance cache organized as coarse directly-addressable pages with contiguous local payload should execute more coherently than a global open-addressed hash cache. Grouping work by page should further improve memory locality.

## What this experiment deliberately does not test

- lighting quality
- radiance interpolation
- temporal stability
- ray-query cost
- surfel placement quality
- multi-bounce transport

Those would hide the memory-layout signal.

## Workload

Sponza triangle centroids are quantized into 0.25 m cells. A page is 4×4×4 cells (64 local slots). Spatial coordinates are remapped to dense page IDs on the CPU so the paged layout has an O(1) direct page-table lookup. Queries are repeated deterministically until the requested count is reached.

Three input orders are measured:

- hash: original surface order, global open-addressing lookup.
- paged: original surface order, direct page lookup.
- paged-sorted: stable sort by `(page_id, local_index)` before dispatch.

The sort is initially on CPU on purpose: M0 isolates the benefit ceiling. M1 replaces it with GPU radix/binning and accounts for its cost.

## Metrics

Mandatory:

- GPU timestamp µs / dispatch
- bytes allocated by each representation
- query count
- unique page count
- output checksum (correctness guard)

Later profiling:

- L2 hit rate
- device-memory read transactions
- wave occupancy
- memory-stall percentage

## Pass condition

Do not define success by a single GPU. Continue only if paged-sorted is consistently faster than hash under multiple query counts and at least two locality regimes, and the advantage remains after including GPU binning cost in M1.
