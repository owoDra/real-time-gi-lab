# D005 — stream capacity and overflow

Status: active

## Question

Can the representative producer stop reserving the A001 worst-case stream for
all 9,216 screen tiles, while keeping normal-frame semantics exact and making
overflow safe and explicit?

## Baseline problem

A001 reserves one owner block for every tile even though the accepted
representative high-water mark is 981 visible owners:

- tile/owner worst case: 9,216;
- accepted high water: 981;
- work items per owner: cascades x rays = 4 x 8 = 32;
- A001 work-stream capacity: 18,874,368 bytes;
- representative actual work stream: about 2.0 MB.

D005 treats capacity in **owner blocks** because every visible owner has a fixed
schema-v1 work/output block size.

## Candidate capacity

The steady-state bounded candidate is fixed before D005 timing as:

```text
ceil_to_64(accepted_high_water * 1.25)
= ceil_to_64(981 * 1.25)
= 1280 owner blocks
```

This is a representative-workload research capacity, not a universal production
camera bound.

For the default 4 cascades / 8 rays:

- output capacity = 1,280 x 4;
- work capacity = 1,280 x 4 x 8.

A forced-overflow probe uses 512 owner blocks.

## Safe bounded allocator

A001 currently reserves output and work blocks separately. That makes overflow
awkward because the counters can exceed smaller physical buffers before
downstream indirect dispatch.

D005 uses one owner-slot counter:

1. every visible owner performs `atomicAdd(visible_owner_count, 1)`;
2. the returned owner slot defines both output and work bases;
3. if the slot is outside owner capacity, the producer sets the overflow flag
   and emits nothing;
4. a bounded finalize pass clamps accepted owners to physical capacity, writes
   work/output counts, and builds safe indirect dispatch arguments.

This changes the allocation primitive because safe bounded capacity requires a
single canonical slot. D005 therefore compares a **full-capacity owner-slot
control** against the **bounded owner-slot candidate** to isolate capacity
effects. Accepted A001 remains an external same-process reference.

D004 workgroup-prefix allocation is rejected and is not composed.

## Compared paths

1. **accepted-a001** — unchanged A001 runtime;
2. **owner-slot-full** — 9,216 owner slots, owner-slot allocator;
3. **owner-slot-bounded** — 1,280 owner slots;
4. **owner-slot-bounded-depth-reuse** — 1,280 slots composed with retained D001
   renderer depth reuse;
5. **forced-overflow** — 512 slots, expected overflow;
6. **fallback-full** — a subsequent 9,216-slot owner-slot rerun after the forced
   overflow attempt.

The forced-overflow partial result is never treated as valid GI output.

## Correctness gate — normal capacity

For static, camera-motion, and light-motion, the 1,280-slot candidate must:

- exactly match accepted A001 owner set;
- match visible-owner/output/work counts;
- pass existing schema-v1 work semantics;
- pass gather/merge/resolve tolerance;
- report overflow = 0;
- preserve block-internal order;
- introduce no sort or compaction pass.

## Overflow gate

The 512-slot forced probe must:

- set overflow = 1;
- never write or indirectly dispatch beyond physical capacity;
- clamp work count to 512 x cascades x rays;
- clamp output count to 512 x cascades;
- retain the true attempted visible-owner count separately;
- complete without validation/OOB errors.

The subsequent full-capacity fallback must pass the normal A001 correctness
reference.

Fallback semantics for this experiment are **discard partial result, retry with
full capacity**. GPU retry cost is reported as failed bounded attempt plus full
rerun. Host memory allocation/reallocation latency is not hidden in the GPU
timing and must be listed as an integration limitation.

## Memory accounting

Report separately:

- steady-state persistent bytes;
- steady-state transient bytes;
- resident bytes;
- work-stream capacity;
- contribution capacity;
- output/accum/resolved capacity;
- actual used stream bytes;
- capacity utilization;
- fallback full-capacity resident bytes.

No claim of permanent memory saving is allowed if a full fallback allocation is
kept resident all the time.

## Decision gate

Retain the bounded-capacity mechanism for final Lane D composition only if:

- all normal cases pass correctness with overflow = 0;
- work-stream capacity drops by at least 75%;
- total resident producer memory drops by at least 50%;
- bounded owner-slot producer total does not regress the matched full-capacity
  owner-slot control by more than 3% in any case;
- bounded E2E does not regress the matched control by more than 3% in any case;
- direct accepted-A001 E2E does not regress by more than 5% in any case;
- forced overflow is safe and the full fallback restores correctness.

The memory policy may still be retained as research evidence with an explicit
integration caveat if GPU fallback succeeds but host allocation latency remains
unmeasured.

## Target workload

- real Sponza;
- static / camera-motion / light-motion;
- AMD Radeon 8060S Graphics (RADV STRIX_HALO);
- diagnostic validation first;
- accepted timing with validation disabled;
- 3 process-level repeats;
- 50 timed iterations per normal case.
