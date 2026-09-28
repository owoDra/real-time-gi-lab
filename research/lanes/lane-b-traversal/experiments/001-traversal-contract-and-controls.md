# Experiment B001 — traversal contract and comparable controls

Status: concluded — accepted as semantic/correctness and candidate-retention evidence.

## Question

Can a simple software BVH, a StrataBrick-derived traversal control, and HWRT/TLAS
(where available) be compared under one `traceRay(origin, direction, tMax) -> Hit`
semantic contract without hiding maintenance or memory costs?

## Hypotheses

- **Software BVH:** retain as the simplest useful baseline unless it fails the
  shared correctness contract.
- **StrataBrick-derived:** finite-range spatial traversal may help some GI
  regimes, but only if build/update + traversal + memory remain competitive.
  Prior StrataBrick results are hypothesis input, not evidence of a win.
- **HWRT/TLAS:** retain only when target-device feature support and the same Hit
  semantics can be demonstrated.

No additional candidate was added in B001 because no distinct falsifiable
mechanism justified the implementation cost.

## Shared Hit contract

`traceRay(origin, direction, tMax) -> Hit` has these B001 semantics:

- finite non-zero direction is normalized at the contract boundary;
- `Hit.t` is world-space closest-hit distance in `[1e-4, tMax]`;
- per-primitive face policy is scene data; control scenes are two-sided so
  traversal is not silently mixed with renderer culling policy;
- Hit contains geometric world normal, `primitive_id`, `material_id`, and
  `instance_id`;
- equal-distance hits use the same absolute/relative tolerance as traversal
  pruning and then lower `primitive_id` as deterministic tie-breaker;
- miss is `t=+INF` with all IDs set to `UINT32_MAX`.

The brute-force triangle path is the reference. The executable also runs contract
smoke tests for direction normalization, `tMax`, face policy, and deterministic
tie-breaking before the matrix.

## Implemented controls

`phos-lane-b-b001` contains:

1. brute-force triangle reference;
2. binary software BVH with build, refit, rebuild, traversal and memory accounting;
3. sparse 3D grid + Amanatides/Woo-style DDA with build, incremental moved-
   primitive membership update, rebuild, traversal and memory accounting;
4. deterministic GI-like control rays over sparse, dense and vertical scenes.

The grid control is **StrataBrick-derived, not a reproduction of historical
StrataBrick**. The historical hierarchy also had membership/key generation,
segment ranges, per-segment BVHs, mesh BVH, dirty classification and occupancy.

## Accepted target rerun

Artifact:

`out/research/lane-b-traversal/001-traversal-contract-and-controls/20260928T150111Z/`

Measurement commit:

`52710fcbd372369fe58e68f6c29b39aa9924a3db`

Run properties:

- branch: `research-lane-b-traversal`;
- clean tree: yes;
- return code: 0;
- CPU: AMD RYZEN AI MAX+ 395 w/ Radeon 8060S;
- matrix: 48 rows;
- rays: 65,536 per row;
- repeats: 5;
- correctness mismatches: 0.

Median raw-grid / software-BVH trace-time ratios across static/moving geometry
and static/shifted camera:

| scene | 50 m | 200 m |
| --- | ---: | ---: |
| sparse | 4.74x | 24.82x |
| dense | 1.09x | 3.50x |
| vertical | 0.91x | 1.84x |

The raw grid is strongly range/regime sensitive and is not promoted as a
standalone final candidate. Its short-range vertical result is retained as a
useful regime observation, not generalized into a win.

## HWRT gate

The probe found no missing required extension names, but `vulkaninfo` exposed
both AMD Radeon 8060S / RADV and llvmpipe. Therefore the probe status is
`ambiguous`: extension text cannot be safely attributed to exactly one target
physical device.

HWRT/TLAS is not rejected. The next GPU bring-up must explicitly identify/select
the physical device, enable the required features, and validate the shared Hit
semantics before timing.

## Decision

B001 is accepted as the semantic/correctness and candidate-retention checkpoint:

- **retain software BVH** as the simple software baseline;
- **do not promote raw sparse-grid DDA** as a standalone final architecture;
- **retain one hierarchical StrataBrick-derived candidate** because its
  segment/BVH pruning + localized rebuild/refit hypothesis is materially
  different from raw DDA;
- **retain HWRT/TLAS** for explicit target-device bring-up; current capability
  evidence is ambiguous, not negative.

This does not select the final Lane B winner. The next architectural decision
must replay the surviving GPU candidates on Lane A's accepted representative
producer stream and include all build/refit/rebuild/update, traversal, persistent
memory and scratch memory costs.

See `results/001-traversal-contract-and-controls.md` for the durable result.
