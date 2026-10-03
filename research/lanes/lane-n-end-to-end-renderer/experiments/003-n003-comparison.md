# N003 — current architecture vs vanilla Split RC

Issue: #38  
Preflight: #31 (complete)

Status: **implementation complete; local build/contract/target validation required before measurement interpretation**

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

The vanilla path does **not** import the current architecture's object-local ownership, TLAS/BLAS update strategy, StrataBrick/Micro-BVH fallback or other support optimizations that define the comparison target. It also does not intentionally reduce Split RC sampling or image semantics.

The `VanillaSoftware` path is not newly invented for N003: it is the independent vanilla software-BVH baseline already used by the earlier Integration #13 comparison. Integration #13 also retained A001 producer semantics/natural order and C001 sparse hash as shared stable contracts, so sharing those components here preserves the historical comparison identity rather than weakening vanilla.

## Shared semantics

Both roles share exactly:

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

The comparison executable additionally rejects A/B pairs when core producer workload identity differs (`work_items`, `outputs`, requested counts, overflow or visible owners). Topology/high-churn also requires identical moved/replaced primitive and rebuild counts.

## Vanilla renderer implementation boundary

N001/N002 accepted sources are not globally relaxed to permit arbitrary variants. N003 constructs the accepted `LaneEFinalHwrt` runtime first so scene loading, dynamic-owner selection, storage sizing and shared renderer resources are identical, then—before the first frame or warm-up—the N003-only hook:

1. waits for setup work to finish;
2. destroys current primary/composite/candidate traversal and HWRT resources;
3. switches the comparison role to `VanillaSoftware`;
4. creates the historical global binary software BVH candidate traversal;
5. creates N003-only software primary-visibility and software direct-shadow/composite stages;
6. recalculates resident memory before any measured frame.

The transient construction-time HWRT setup is outside warm-up, timing and retained-memory evidence. It exists only because the accepted N001 constructor deliberately refuses non-primary variants; the comparison hook does not change N001/N002 executable behavior.

## Dynamic geometry

For moving-rigid and stable-topology-deforming vanilla frames, the existing software candidate path uploads the changed triangles, rebuilds the global binary BVH on CPU and uploads the resulting node/order buffers. GPU upload/maintenance is counted inside the complete-GI and complete-renderer boundaries. CPU preparation/rebuild wall values are retained only in the separate non-formal diagnostics artifact.

For topology-changing/high-churn, `run_n003_vanilla_topology_churn_frame()` applies the exact N002 frozen 50% replacement schedule, uploads the changed surfaces/triangles, rebuilds the same global binary software BVH and then executes the unchanged complete renderer/GI frame. The current role executes N002's accepted object-local BLAS/TLAS replacement path.

The vanilla topology `true_lifetime_peak` includes the largest synchronously overlapping host-visible staging allocation used by surface, triangle, node or order upload. Since each upload is fenced and destroys its staging buffer before the next upload, these staging allocations do not overlap one another. The CPU software-BVH rebuild does not create an old/new device-AS overlap, so `old_new_overlap` remains zero for vanilla.

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

Moving-rigid timing can never produce a formal N003 performance direction under this campaign. Correctness, workload, memory and quality remain valid there.

## Memory boundary

Formal pair artifacts record device-side:

- persistent bytes;
- transient bytes;
- explicit scratch;
- old/new overlap;
- true lifetime peak;
- radiance-storage persistent bytes;
- producer-stream capacity;
- image transient bytes.

`phos-n003-diagnostics` separately records renderer-owned host mirror capacity for each role/scenario:

- A001 surface scene mirror;
- B002 triangle scene mirror;
- selected dynamic primitive-index mirror;
- candidate traversal host structure (HWRT dynamic-index mirror or software-BVH nodes/order);
- their renderer-owned total.

This host-memory diagnostic intentionally excludes STL allocator bookkeeping and opaque driver/Vulkan host allocations because those are not directly observable by the renderer and would otherwise be guessed. It is not a formal performance axis.

The same diagnostics artifact also retains CPU wall/preparation/rebuild values already measured by the runtime. These values are health/explanation evidence only and cannot override the frozen GPU-primary timing decision.

## Quality/reference protocol

Quality is deliberately separated from the replicated timing run. `phos-n003-quality` runs each current/vanilla scenario once after the same 32 source-state warm-up, requires exact A/B final scene-state identity, emits both HDR frames, and generates one converged diffuse reference from that shared state.

Primary metrics per role/reference:

- RGB RMS error;
- p99 absolute luminance error;
- scale-aware affected-pixel fraction where `abs_error >= 0.05 * max(abs(reference_luminance), 0.0001)`.

For the two error metrics, a material direction requires the lower value to be <=90% of the other value. For affected fraction, the absolute difference must be >=0.005 and lower is better. A scenario has a material quality direction only when at least two of the three primary metrics move materially in the same direction.

No aggregate quality winner is permitted. Black reference frames remain valid evidence.

## Host safety

Lane N must not change GPU power/performance profiles. N003 runners do not write GPU clock, power, DPM or profile controls.

## Local validation order

1. build `phos-n003-comparison`, `phos-n003-quality` and `phos-n003-diagnostics`;
2. run GPU-independent comparison, quality and diagnostics contract entrypoints;
3. run one comparison probe manually to catch Vulkan/shader/runtime integration faults; this is validation evidence, not an accepted timing campaign;
4. run the one-shot diagnostics census and retain its artifact;
5. run the full replicated timing/memory campaign exactly once after the probe passes;
6. run the one-shot quality/reference campaign;
7. only then interpret and commit the N003 result.

Raw artifacts stay under `out/research/`.
