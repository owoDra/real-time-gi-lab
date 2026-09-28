# Experiment C001 — Split RC storage baselines

Status: active — C001a structural/correctness bring-up concluded; target-GPU
performance and Lane A replay remain.

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

## C001b — required GPU comparison

For every retained representation, C001b must measure or account for:

- lookup;
- update;
- allocation and residency;
- eviction;
- invalidation;
- persistent memory;
- scratch memory;
- producer-side address/residency work.

Ordering/locality remains a separate axis. Synthetic/GI-like streams may be
used for bring-up, but final promotion requires Lane A's exact producer stream.

Producer-side locality experiments may only use domains that the producer can
naturally emit, such as screen tile, cascade, or spatial brick/page. A global
post-generation reorder remains diagnostic unless its full cost wins end to
end.

Timestamp differences establish performance only. Any claim about a specific
GPU cache or memory mechanism requires profiling evidence such as RGP.
