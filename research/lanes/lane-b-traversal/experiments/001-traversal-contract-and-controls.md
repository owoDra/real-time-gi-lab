# Experiment B001 — traversal contract and comparable controls

Status: target control CSV inspected — correctness passes; hardened reproducible rerun and HWRT metadata pending.

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
all IDs must match before timing is usable. The executable also runs contract
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
- correctness mismatches;
- ray count and repeat count.

`dynamic_update_us` includes the common moved-geometry update. The grid adds
candidate-specific cell-membership maintenance; BVH structural maintenance stays
separate in `refit_us`. CPU timings are diagnostic only and cannot select the
GPU winner.

Construction timing uses a fresh acceleration object per sample and stops the
timer before destroying it, so build/rebuild do not silently include teardown.
Refit/update samples likewise begin from a freshly prepared pre-update structure;
setup/reset work stays outside the candidate-specific timed boundary.

## Sandbox correctness checkpoint

GPU-independent checks were run without mise, per the target-environment rule:

- GCC C++20 with `-Wall -Wextra -Wpedantic -Werror`: PASS;
- 48 matrix rows × 2,048 rays: zero mismatches;
- ASan + UBSan: PASS;
- lane-local CMake/Ninja Release build: PASS.

Self-review found and fixed correctness/accounting issues before the target
rerun gate:

1. DDA early-exit used only absolute hit tolerance while the Hit tie-break used
   absolute/relative tolerance, allowing a vertical edge ray to depend on
   traversal order.
2. the grid's persistent deduplication array was initially counted as per-ray
   scratch; it is now persistent memory, while scratch reports only per-trace
   local state.
3. common dynamic-update timing included benchmark-reset copying.
4. rebuild timing included an extra trace used only as an optimization guard.
5. build/rebuild timing could include acceleration-object destruction.

The sandbox CPU timing direction is intentionally not accepted as target-GPU
performance evidence. It is sufficient only to show that raw DDA is strongly
range/regime sensitive and therefore must not be promoted by lookup timing alone.

## Target-system CSV checkpoint

A target-system control CSV was inspected with **48 candidate rows × 65,536
rays/row**. All rows reported **zero correctness mismatches** against the shared
brute-force reference.

The raw grid remains strongly range/regime-sensitive. Median
`stratabrick-grid-control / software-bvh` trace-time ratios across
static/moving geometry and static/shifted camera were:

| Scene | 50 m | 200 m |
| --- | ---: | ---: |
| sparse | 4.37x | 22.35x |
| dense | 1.03x | 3.30x |
| vertical | 0.91x | 1.73x |

A ratio below 1 means the raw grid was faster; the only material control regime
where that happened was the finite 50 m vertical case. These are CPU control
timings, not final GPU architectural evidence.

The received CSV is **diagnostic rather than the formal B001 artifact** because
it predates the hardened provenance/timing boundaries. In addition to the timing
fixes above, the current runner records repeats and resolved run configuration,
and the HWRT probe records CPU/Vulkan device/driver/API information. If
`vulkaninfo` exposes zero or multiple physical devices, the probe reports HWRT
support as `ambiguous` rather than incorrectly attributing global extension text
to one device.

The formal B001 result therefore requires one rerun with the current branch.

## Target execution

After pulling this branch on the target system:

```bash
git pull
mise install
mise run research:check
mise run build
mise run research:record --lane lane-b-traversal \
  --experiment 001-traversal-contract-and-controls \
  --command "scripts/research/lane_b_traversal/run_b001.sh build/release/phos-lane-b-b001"
```

Retain the generated `b001-controls.csv`, `metadata.json`, and
`hwrt-probe.json`.

## Provisional retention decision

- **retain software BVH** for the main comparison;
- **do not promote raw sparse-grid DDA as the final StrataBrick candidate**;
- **retain one hierarchical StrataBrick-derived candidate** because raw DDA is
  regime-sensitive and the historical candidate's segment/BVH pruning is a
  materially different hypothesis that B001's raw grid does not test;
- **retain HWRT/TLAS iff the target probe reports unambiguous support**, then
  validate feature enablement and shared Hit semantics before timing.

No B001 control-ray result may select the final Lane B winner. Final promotion
requires Lane A producer replay and all maintenance + memory costs.
