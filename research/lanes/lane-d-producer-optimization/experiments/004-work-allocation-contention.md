# D004 — work-allocation contention

Status: active

## Question

Can A001's per-visible-owner global work/output reservations be aggregated at
workgroup scope without changing visibility, emitted work semantics, stream
capacity, or adding a compaction/reorder pass?

## Baseline

The accepted surface producer performs three global atomics for every visible
owner:

1. reserve the owner's output block;
2. reserve the owner's work-item block;
3. increment visible-owner count.

On the representative workload there are about 978-981 visible owners.

## Candidate — workgroup-prefix reservation

Keep the A001 source domain and visibility test exactly as-is.

Each 64-invocation producer workgroup:

1. computes the same visible-owner predicate as A001;
2. performs a shared-memory prefix scan over the 64 visibility flags;
3. if the workgroup contains visible owners, one lane performs the three global
   counter atomics for the whole workgroup;
4. each visible lane derives its output/work base from the workgroup base plus
   its local prefix and emits the same contiguous schema-v1 block.

There is no global prefix pass, no compaction buffer, no CPU work, and no
post-generation sort.

Inter-workgroup allocation order remains GPU scheduling dependent. Within a
workgroup, visible owners become local-surface-ID ordered. That natural order
change is measured rather than normalized.

## Compared paths

1. **accepted-a001** — unchanged accepted A001 runtime;
2. **owner-atomic-full** — staged full visibility + current per-owner allocation;
3. **workgroup-full** — same staged visibility with workgroup-prefix allocation;
4. **owner-atomic-depth-reuse** — D001 retained depth-reuse contract + current
   allocation;
5. **workgroup-depth-reuse** — D001 depth reuse + workgroup-prefix allocation.

D002 tile emission and D003 packed visibility are rejected and are not composed.

## Correctness gate

Every static, camera-motion, and light-motion row must satisfy:

- exact owner-set parity with accepted A001;
- identical visible-owner, output, and work-item counts;
- existing A001 schema-v1 semantic checks;
- gather/merge/resolve correctness;
- no output holes or duplicate blocks;
- overflow flag zero;
- block-internal cascade/ray order preserved;
- natural inter-block locality recorded without sorting.

## Contention evidence

The benchmark records:

- visible owner count;
- number of 64-surface workgroups containing at least one visible owner;
- theoretical global reservation atomic count:
  - per-owner = visible owners x 3;
  - workgroup = active producer workgroups x 3;
- producer emit and producer total timings.

This count is diagnostic. Performance, not atomic-count reduction alone,
determines retention because shared-memory scans/barriers have a cost.

## Measured boundary

For staged variants record:

- visibility reset/depth/owner;
- producer reset;
- producer emit including allocation atomics and producer synchronization;
- finalize;
- producer total;
- gather/merge/resolve/end-to-end;
- locality;
- memory;
- stream capacity and actual stream bytes;
- overflow.

No stream-capacity allocation or compaction cost changes in D004.

## Decision gate

Retain workgroup-prefix allocation only if all three target cases pass
correctness and, relative to matched `owner-atomic-full` medians:

- producer emit improves by at least 10%;
- complete producer total improves by at least 5%;
- end-to-end does not regress by more than 1%;
- persistent/transient allocation does not increase materially (shared memory
  is reported separately as shader-local scratch);
- no extra dispatch, CPU pass, compaction, or global reorder is introduced.

For direct accepted-A001 relevance, `workgroup-full` must additionally improve
accepted-A001 producer total by at least 5% in all three cases and must not
regress accepted-A001 E2E in any case.

The depth-reuse composition is recorded independently. It does not rescue a
workgroup mechanism that fails the full-path gate.

## Target workload

- real Sponza;
- static / camera-motion / light-motion;
- AMD Radeon 8060S Graphics (RADV STRIX_HALO);
- diagnostic validation first;
- accepted timing with validation disabled;
- 3 process-level repeats;
- 50 timed iterations per case.
