# Experiment C001 — Split RC storage baselines

Status: active — C001a and synthetic Vulkan C001b candidate pruning concluded;
exact Lane A replay remains mandatory for final promotion.

## Question

Which sparse radiance representation is a plausible Split RC foundation before
producer-side locality is applied?

Representation and ordering are separate axes. C001 must not infer that a
contiguous or brick representation wins merely because a separately reordered
stream is faster.

## Concrete representations

### Per-probe open-addressed sparse hash

Baseline. Each logical probe is independently keyed and stored in an
open-addressed table sized for at most 0.5 load in the C001 structural model.

Residency, allocation, invalidation, and eviction can operate at probe
granularity.

### Hashed contiguous brick pool

A sparse hash directory maps one 4 x 4 x 4 spatial brick key to one physical
contiguous brick. Each physical brick contains 64 radiance payload slots plus
brick occupancy/residency metadata.

Lookup first resolves the brick directory entry and then the local probe index.
Allocation, residency, eviction, and empty-brick reclamation operate at brick
granularity.

### Virtual / clipmap-style sparse storage

Each cascade owns a bounded virtual brick grid. A direct 32-bit virtual page
entry maps a virtual brick slot to a physical 4 x 4 x 4 brick or an invalid
entry. The clipmap origin/window supplies the world-to-virtual mapping.

This is structurally distinct from the hashed brick pool: virtual address
translation is bounded/direct rather than an unbounded sparse brick hash.
Camera motion changes the virtual window and therefore makes residency and
plane invalidation part of the producer/update contract.

### StrataBrick-inspired variant

Not added in C001a. A fourth variant is admitted only if it introduces a
concretely different data structure or update/residency rule from the three
representations above. A name or ancestry is not sufficient evidence.

## C001a — structural/correctness bring-up

C001a is deliberately a representation-only synthetic control. It contains no
GPU timing claim and no producer-side regrouping.

Default control:

- 3 cascades;
- active window: 12 x 12 x 4 bricks per cascade;
- brick size: 4 x 4 x 4 probes;
- occupancy controls: 4 / 16 / 48 active probes per brick;
- virtual clipmap extent: 24 x 24 x 8 bricks per cascade;
- dynamic control: one-brick window shift along X;
- query/update order: generated source order, unchanged.

The occupancy controls are important because a sparse brick must be allowed to
lose to the per-probe hash. The experiment is not constructed to make brick
storage win.

Run through the normal artifact wrapper on a target environment:

```bash
mise run research:record \
  --lane lane-c-storage-locality \
  --experiment 001-storage-baselines \
  --command "python scripts/research/lane_c_storage_locality/experiment_001.py"
```

Unit correctness:

```bash
python -m unittest scripts/research/lane_c_storage_locality/test_experiment_001.py -v
```

## C001a metrics

C001a records:

- semantic correctness;
- conceptual packed persistent bytes;
- required scratch bytes for the modeled in-place representation;
- structural lookup/update address-translation steps;
- initial allocation granularity;
- eviction/invalidation unit count for the one-brick motion control;
- producer-side address terms.

These are structural accounting metrics, not measured CPU/GPU latency.
Python-object overhead is intentionally excluded.

## Correctness gate

For the same logical probe set, every representation must pass:

1. insert and lookup;
2. update and lookup;
3. invalidation and absence check;
4. restore and lookup.

A failed representation is removed before timing.

## Candidate-retention gate

C001a retains a representation only when:

- it passes semantic parity;
- it has a plausible structural advantage in at least one meaningful occupancy
  or dynamic regime;
- that advantage does not require manufactured ordering.

Retention is not architectural promotion. Final promotion still requires
target-GPU end-to-end evidence and replay of Lane A's exact producer stream.

## C001b — Vulkan GPU comparison

C001b is implemented as a Lane C-owned Vulkan compute benchmark. It does not
reuse the M0 paged lookup as a proxy for the new candidates.

Default synthetic control:

- 3 cascades;
- active window: 24 x 24 x 8 bricks per cascade;
- virtual clipmap extent: 32 x 32 x 16 bricks per cascade;
- brick size: 4 x 4 x 4 probes;
- occupancy controls: 4 / 16 / 48 active probes per brick;
- source order unchanged; no sorting/grouping;
- update subset: every 17th source probe;
- invalidation subset: every 257th source probe;
- dynamic residency control: evict the X=0 brick plane and admit the adjacent
  X=24 plane.

Measured Vulkan phases:

- `producer-address`;
- `lookup`;
- `producer+lookup`;
- `update`;
- `producer+update`;
- `invalidation`;
- `eviction`;
- `residency-churn-e2e`;
- `allocation-residency`;
- `initial-build-e2e`.

The hashed-brick and virtual/clipmap candidates use a GPU physical-brick free
list. Eviction returns the physical slot to the free list, and the dynamic
churn sequence must reuse those slots when the entering plane becomes resident.
After the first target-GPU run exposed a highly repeatable allocator bottleneck,
the entering-plane batch was changed from a shared compare-and-swap retrying pop
to one bounded atomic claim per brick plus a one-invocation finalize step. The
generic empty-to-resident path remains unchanged. The probe hash reuses
tombstoned hash slots instead.

Persistent-byte accounting uses the actual modeled GPU buffers required by each
candidate: hash/directory/page-table storage, physical payload pool, allocator
counters, and the brick free list where applicable. Scratch accounting records
the address/output workspace used by the measured producer/storage sequence.
Benchmark-only seed copies are excluded from architecture memory accounting.

### Synthetic residency-unit boundary

For the hashed-brick and virtual/clipmap candidates, C001b's synthetic control
provides the active/entering **brick units** directly from the regular synthetic
brick grid. This is a natural producer domain, not a post-generation sort or
global regrouping, but the cost of discovering/emitting those brick units is not
claimed as representative Split RC producer evidence.

Therefore C001b may reject a candidate or keep it for further study, but an
allocation/residency win cannot by itself promote a brick representation. The
final Lane A replay must account for any extra producer work required to emit
brick/page residency units from the exact producer stream.

### Timing boundary

Mutating phases must begin from the same semantic state every iteration. C001b
therefore copies an immutable GPU seed into the working representation before
each mutation iteration. These reset copies and their required synchronization
are deliberately outside the timestamp interval because they are benchmark
harness work, not candidate architecture work.

The reset can still perturb cache state. Therefore mutation timings are valid
for candidate comparison only after repeatability is established, and they must
not be used to claim a specific cache/memory mechanism. RGP or equivalent
profiling evidence is still required for such claims.

### C001b correctness gate

Every performance row is invalid unless all applicable guards pass:

- GPU-produced addresses exactly match the host semantic reference;
- lookup output matches every expected probe payload, not checksum only;
- update/invalidation/eviction return the exact expected logical state;
- storage-operation error counters remain zero;
- brick/clipmap allocator counts remain within the active physical capacity;
- after one-brick X-shift churn, the old plane is absent, the entering plane is
  present, and the free list is drained back to zero;
- empty-to-resident initial build resolves every probe correctly.

### Target runs

First run Vulkan validation as diagnostics:

```bash
mise run research:record \
  --lane lane-c-storage-locality \
  --experiment 001-storage-baselines \
  --command "python scripts/research/lane_c_storage_locality/c001b_matrix.py --repeats 1 --iterations 10 --validation"
```

Then collect accepted timing with validation disabled:

```bash
mise run research:record \
  --lane lane-c-storage-locality \
  --experiment 001-storage-baselines \
  --command "python scripts/research/lane_c_storage_locality/c001b_matrix.py --repeats 3 --iterations 100"
```

Each process writes `repeat-NN/c001b.csv`; the matrix runner writes
`c001b_summary.csv` with process-level median/min/max timings and rejects the
run if any repeat fails correctness.

Ordering/locality remains a separate axis. This synthetic/GI-like control may
reject or retain candidates, but final promotion still requires Lane A's exact
producer stream. A global post-generation reorder remains diagnostic unless its
complete end-to-end cost wins.

Timestamp differences establish performance only. Any claim about a specific
GPU cache or memory mechanism requires profiling evidence such as RGP.


### C001b candidate outcome

The allocator-corrected target-GPU rerun passed all correctness gates and
narrows the primary exact-stream comparison to:

- per-probe sparse hash baseline;
- virtual/clipmap sparse storage.

The hashed contiguous brick pool remains as a fallback diagnostic control, but
is not a primary candidate unless Lane A demonstrates that the bounded virtual
addressing contract is unsuitable for the actual producer stream.

No representation is promoted until the exact Lane A replay is complete.


## C001c — exact Lane A producer-stream replay

C001c consumes A001 `stream-v1.bin` directly. The binary's FNV-1a
`workload_id` is verified before any timing is accepted, and work items are
uploaded in the recorded GPU append order without CPU sorting or grouping.

The retained candidates are:

- per-probe open-addressed sparse hash;
- virtual/clipmap sparse storage.

Every raw 64-byte Lane A work item is processed by the GPU address stage.
A001 emits eight ray records for each probe/cascade output. Storage mutation is
therefore selected by `ray_index == 0`, yielding exactly one storage event per
A001 `output_id`. The selection happens in the measured GPU address/storage
path; C001c does not CPU-deduplicate the performance stream.

Measured exact-stream phases:

- `producer-address`;
- `producer+lookup`;
- `producer+update`;
- `producer+invalidation`;
- `producer+allocation-residency`;
- `initial-build-e2e`.

CPU parsing scans the stream only to validate schema/workload identity, build
the independent correctness reference, and size benchmark buffers. Those setup
steps are outside GPU timing and are not claimed as architecture work.

For virtual/clipmap replay, the observed per-cascade brick bounds define a
replay-local virtual origin and bounded page-table extent. This normalization
does not reorder work, but its origin/window selection cost is not represented
by the v1 stream schema. Therefore C001c can establish exact-stream steady-state
storage evidence, but a final dynamic clipmap promotion must also account for
real origin/window maintenance or show that it is supplied by the producer
without additional global work.

Correctness requires:

- stream schema and FNV workload identity match;
- GPU addresses equal the host semantic reference for every raw item;
- ray-0 count equals A001 `output_count`;
- exact lookup/update/invalidation values match element-by-element;
- allocation error counters remain zero;
- virtual physical-brick allocation equals the number of unique referenced
  virtual bricks.

Diagnostic validation:

```bash
mise run research:record \
  --lane lane-c-storage-locality \
  --experiment 001-storage-baselines \
  --command "python scripts/research/lane_c_storage_locality/c001c_matrix.py \
    --lane-a-artifact <A001-artifact-root> \
    --repeats 1 --iterations 10 --validation"
```

Accepted timing:

```bash
mise run research:record \
  --lane lane-c-storage-locality \
  --experiment 001-storage-baselines \
  --command "python scripts/research/lane_c_storage_locality/c001c_matrix.py \
    --lane-a-artifact <A001-artifact-root> \
    --repeats 3 --iterations 100"
```


## C001d — exact camera-motion transition gate

C001c establishes steady-state exact-stream evidence but intentionally does not
claim that per-frame virtual-window origin selection is free.

C001d is the final promotion gate. It must compare the retained probe hash and
virtual clipmap across the recorded static -> camera-motion transition while
preserving stable world-probe identity and including residency changes caused
by the virtual-window movement.

Required evidence:

- semantic parity before and after the transition;
- stable probe identity across both recorded frames;
- entering/leaving probe and brick counts;
- complete transition GPU time including virtual-window residency work;
- persistent and scratch memory;
- no CPU sort/grouping or post-generation favorable reorder;
- repeatability across independent process runs.

No final C001 representation is promoted before C001d.


### C001d implementation

The transition benchmark uses one stable canonical probe key over the union of
the two recorded frames. The target frame remains in its original append order.

For the hash candidate, the high bit of the existing hash key is used as a
temporary target-frame mark, avoiding an additional persistent mark buffer. A
bounded table sweep removes unmarked leaving probes.

For the virtual/clipmap candidate, the page table is toroidal. Each page slot
has a stable world-brick tag so overlapping bricks survive an origin shift,
aliased old slots can reuse their physical brick in place, and leaving slots
return physical bricks to the free list. The transition sequence is:

1. GPU target address generation;
2. mark/prepare target residency;
3. sweep leaving residency;
4. allocate target bricks that still need physical storage;
5. populate target values.

The timestamp includes all five steps. CPU set analysis is used only for
correctness expectations and reported entering/leaving counts; it does not
reorder or replace the measured GPU transition path.
