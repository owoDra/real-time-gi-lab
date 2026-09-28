# Experiment B001 — traversal contract and comparable controls

Status: ready for target run — CPU correctness/control checkpoint complete; target-GPU/HWRT availability pending.

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
- **HWRT/TLAS:** retain only when the target Vulkan device exposes the required
  acceleration-structure/ray-query support and the implementation can preserve
  the same Hit semantics.

No additional candidate is added in B001 because no distinct falsifiable
mechanism currently justifies the implementation cost.

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

The brute-force triangle path is the reference. Hit/miss, distance, normal, and
all IDs must match before timing is usable.

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
Those costs must be included if the hierarchical candidate advances.

## Control matrix

The executable crosses:

- scenes: `sparse`, `dense`, `vertical`;
- geometry: `static`, `moving`;
- camera: `static`, `shifted`;
- finite GI range: `50 m`, `200 m`;
- candidates: `software-bvh`, `stratabrick-grid-control`.

Control rays are bring-up only. All conclusions remain **provisional** until
replayed with Lane A's representative producer stream.

## Required measured fields

Each candidate row reports:

- `build_us`;
- `refit_us` (not applicable to the raw grid control);
- `rebuild_us`;
- `dynamic_update_us`;
- `trace_us`;
- `persistent_bytes`;
- `scratch_bytes`;
- correctness mismatches.

`dynamic_update_us` includes the common moved-geometry update. The grid adds
candidate-specific cell-membership maintenance; BVH structural maintenance stays
separate in `refit_us`. CPU timings are diagnostic only and cannot select the
GPU winner.

## Sandbox correctness checkpoint

GPU-independent checks were run without mise, per the target-environment rule:

- GCC C++20 with `-Wall -Wextra -Wpedantic -Werror`: PASS;
- 48 matrix rows × 2,048 rays: zero mismatches;
- ASan + UBSan: PASS;
- lane-local CMake/Ninja Release build: PASS.

Self-review found and fixed two correctness/accounting issues before this
checkpoint:

1. DDA early-exit used only absolute hit tolerance while the Hit tie-break used
   absolute/relative tolerance, allowing a vertical edge ray to depend on
   traversal order.
2. the grid's persistent deduplication array was initially counted as per-ray
   scratch; it is now persistent memory, while scratch reports only per-trace
   local state.

The sandbox CPU timing direction is intentionally not accepted as target-GPU
performance evidence. It is sufficient only to show that raw DDA is strongly
range/regime sensitive and therefore must not be promoted by lookup timing alone.

## Target execution

After pulling this branch on the target system:

```bash
mise install
mise run research:check
mise run build
mise run research:record --lane lane-b-traversal \
  --experiment 001-traversal-contract-and-controls \
  --command "scripts/research/lane_b_traversal/run_b001.sh build/release/phos-lane-b-b001"
```

The artifact contains `b001-controls.csv`, the standard research logs/metadata,
and `hwrt-probe.json`.

## Provisional retention decision

- **retain software BVH** for the main comparison;
- **do not promote raw sparse-grid DDA as the final StrataBrick candidate**;
- **retain one hierarchical StrataBrick-derived candidate** because raw DDA is
  regime-sensitive and the historical candidate's segment/BVH pruning is a
  materially different hypothesis that B001's raw grid does not test;
- **retain HWRT/TLAS iff the target probe reports support**, then validate
  feature enablement and shared Hit semantics before timing.

No B001 control-ray result may select the final Lane B winner. Final promotion
requires Lane A producer replay and all maintenance + memory costs.
