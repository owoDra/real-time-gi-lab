# D002 — visible-tile-driven emission

Status: active

## Question

After visibility owner selection is complete, can producer work be emitted from
the screen-tile domain instead of rescanning every source surface, while
preserving A001 semantics and improving complete producer/end-to-end cost?

D002 isolates the source-emission domain. It does not add compaction, global
sorting, new storage addressing, or a different work allocator.

## Baseline delta

A001 dispatches one producer invocation per source surface. On the representative
Sponza workload that means roughly 262k invocations after visibility was already
resolved, while only about 978-981 visible tile owners emit work.

The D002 candidate dispatches one invocation per screen tile (128 x 72 = 9,216).
Each tile reads its already-selected owner surface ID:

- invalid owner: emit nothing;
- valid owner: read that surface position and emit the same contiguous
  cascade-major/ray-minor schema-v1 block as A001.

The candidate keeps:

- the same A001 depth pass;
- the same deterministic owner pass;
- the same two global output/work block reservations per visible owner;
- the same fixed-capacity stream allocation;
- the same finalize, gather, merge, and resolve;
- no CPU sort or post-generation reorder.

Any locality difference is therefore a natural consequence of changing the
source invocation domain from surfaces to tiles.

## Compared variants

D002 records:

1. **accepted-a001** — unchanged accepted A001 runtime in the same process;
2. **surface-full** — Lane D staged full-visibility control using A001
   surface-scan emission;
3. **tile-full** — identical staged visibility/control path, but tile-domain
   emission;
4. **surface-depth-reuse** — D001 retained depth-reuse control;
5. **tile-depth-reuse** — D001 retained depth reuse composed with tile emission.

The staged surface/tile pairs isolate emission-domain cost. The unchanged A001
control prevents the staged instrumentation from silently becoming the new
baseline.

## Hypothesis

Tile-domain emission should materially reduce producer emit cost because the
post-visibility dispatch shrinks from every source surface to every screen tile.

The mechanism is useful only if that kernel reduction survives synchronization,
finalize, and downstream work. A locality improvement is not assumed and is not
manufactured.

## Correctness gate

Every static, camera-motion, and light-motion case must satisfy:

- A001 CPU visibility correctness;
- owner-set parity with accepted A001;
- identical visible-owner, output, and work-item counts;
- every emitted block passes the existing A001 schema-v1 semantic reference;
- no duplicate tile blocks, output holes, overflow, or fallback activation;
- gather/merge/resolve passes the A001 tolerance;
- block-internal cascade-major/ray-minor order is preserved;
- natural inter-block order/locality is measured rather than normalized.

A different workload ID is expected when GPU append order changes; byte-identical
inter-block order is not required.

## Measured boundary

For staged controls/candidates record:

- visibility reset/clear;
- visibility depth;
- owner reset/clear;
- visibility owner;
- producer reset/clear;
- producer emit;
- finalize/synchronization;
- producer total;
- gather, merge, resolve, and end-to-end;
- visible-owner/output/work-item counts;
- source dispatch invocation count;
- natural stream locality statistics;
- persistent/transient/producer-scratch/stream-capacity/actual-stream bytes;
- reused visibility bytes for depth-reuse composition;
- overflow flag.

Allocation/compaction cost remains zero because D002 deliberately keeps A001's
fixed-capacity buffers and allocation policy.

## Decision gate

The **tile emission mechanism** is retained only if all three target cases pass
correctness and the median `tile-full` result, relative to the matched
`surface-full` control:

- improves producer total by at least 10%; and
- improves end-to-end by at least 5%; and
- adds no persistent/transient memory requirement; and
- introduces no post-generation reorder or hidden CPU work.

For direct A001 relevance, `tile-full` must also beat the unchanged
same-process accepted A001 control by at least 5% in producer total and must not
regress accepted-A001 end-to-end in any case. If it only beats the staged
control, it remains diagnostic rather than being carried forward.

The depth-reuse composition is retained only if it preserves the tile mechanism
win and its reported standalone boundary remains explicit. D002 does not relax
D001's visibility-reuse accounting.

## Target workload

- real Sponza;
- static;
- camera-motion;
- light-motion;
- AMD Radeon 8060S Graphics (RADV STRIX_HALO);
- diagnostic validation first;
- accepted timing with validation disabled;
- 3 process-level repeats, 50 timed iterations per case.
