# N003 — current architecture vs vanilla Split RC

Issue: #38  
Preflight: #31 (complete)

Status: **complete**

Result truth: `../results/003-current-vs-vanilla.md`

## Question

Do the support-architecture decisions accepted in lanes A–M still provide useful end-to-end behavior when compared with a straightforward vanilla Split Radiance Cascades renderer under the same renderer, reference, timing and memory boundaries?

This experiment is scenario-by-scenario. It does not produce an aggregate winner.

## Baseline identity

### A — current

The accepted N002 renderer:

- A001 visibility-driven Split RC producer with natural GPU append order;
- object-local HWRT/TLAS traversal;
- immutable static ownership;
- transform-only rigid instances;
- object-local UPDATE for stable-topology deformation;
- object-local rebuild for topology-changing/high-churn geometry;
- accepted sparse radiance storage and unchanged gather/merge/resolve path;
- HWRT renderer primary visibility and direct-light visibility.

### B — vanilla

The historical Integration-13 independent vanilla software-BVH reference, promoted to the complete renderer boundary:

- the same A001 Split RC producer, cascade/probe/ray budget and natural append order;
- one global binary software BVH over the scene triangles;
- whole global software-BVH rebuild after rigid motion, stable-topology deformation or topology change;
- the same sparse radiance storage and unchanged gather/merge/resolve path;
- software-BVH renderer primary visibility and direct-light visibility.

The vanilla path does not import the current architecture's object-local ownership, TLAS/BLAS update strategy, StrataBrick/Micro-BVH fallback or other support optimizations that define the comparison target. It also does not intentionally reduce Split RC sampling or image semantics.

## Shared semantics

Both roles share:

- Sponza scene input and deterministic six-scenario state;
- 320 x 180 linear HDR renderer output;
- four cascades and eight rays per probe;
- A001 producer and stream schema;
- ray/probe generation semantics;
- physical radiance/gather stage;
- open-addressed sparse radiance storage;
- merge/resolve;
- direct + indirect constant-white Lambertian renderer semantics;
- converged diffuse reference contract;
- complete-GI and complete-renderer accounting boundaries;
- internal traversal/storage correctness validation.

The comparison executable rejects A/B pairs when producer workload identity differs. Topology/high-churn also requires identical moved/replaced primitive and rebuild counts.

## Timing protocol

Frozen by #31 before target data:

- five current/vanilla micro-pairs per outer block;
- eight outer blocks;
- AB/BA order balanced prospectively;
- block sample is the median of five `log(vanilla/current)` ratios;
- GPU timestamp primary, CPU wall diagnostic-only;
- zero sample deletion/exclusion;
- >=75% same-direction outer blocks for a formal timing claim;
- no accepted-campaign rerun for a more favorable outcome.

Formal scenario thresholds:

| Scenario | Threshold | Timing status |
| --- | ---: | --- |
| static | 7.0% | eligible |
| camera-motion | 1.5% | eligible |
| light-motion | 5.0% | eligible |
| moving-rigid | — | measurement-limited; descriptive only |
| stable-topology-deforming | 2.5% | eligible |
| topology-changing-high-churn | 1.5% | eligible |

## Memory boundary

Formal pair artifacts record device-side persistent, transient, scratch, old/new overlap, true lifetime peak, radiance-storage capacity, producer-stream capacity and image transient bytes.

`phos-n003-diagnostics` separately records renderer-owned host mirror capacity and CPU wall/preparation/rebuild values. These diagnostics are not formal performance axes and exclude opaque driver/Vulkan host allocations.

## Quality/reference protocol

`phos-n003-quality` runs each current/vanilla scenario once after the same 32 source-state warm-up, requires exact A/B final scene-state identity, emits both HDR frames, and generates one converged diffuse reference from that shared state.

Primary metrics:

- RGB RMS error;
- p99 absolute luminance error;
- scale-aware affected-pixel fraction where `abs_error >= 0.05 * max(abs(reference_luminance), 0.0001)`.

A material quality direction requires at least two of the three primary metrics to move materially in the same direction. No aggregate quality winner is permitted.

## Host safety

Lane N must not change GPU power/performance profiles. N003 runners do not write GPU clock, power, DPM or profile controls.

## Accepted result

All 40 timing micro-pairs completed with no exclusions and a clean evidence commit `52a8d2c7ab2653d40b73afa9f17690712536239e`.

Formal complete-renderer median vanilla/current ratios:

- static: 3.023x, current faster;
- camera-motion: 2.756x, current faster;
- light-motion: 3.108x, current faster;
- stable-topology-deforming: 2.506x, current faster;
- topology-changing/high-churn: 2.354x, current faster.

All five timing-eligible scenarios had 8/8 outer blocks in the same direction. Moving-rigid remained measurement-limited and is descriptive only despite a ~1.787x ratio favoring current.

Quality was exactly equal between current and vanilla on all three primary metrics in all six scenarios under converged 512-spp references; therefore no material quality direction exists.

Device true-lifetime memory is higher for current: approximately +26.5% in ordinary scenarios and +23.9% in topology/high-churn. Non-formal host-memory and CPU diagnostics favor current, with vanilla dynamic CPU wall dominated by global software-BVH rebuild.

N003 therefore accepts the current architecture against the mandatory vanilla Split RC same-boundary baseline while retaining the explicit device-memory trade-off.

Raw artifacts remain under `out/research/`.
