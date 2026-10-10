# N006 P1l-B — software primary/shadow and E003 traversal work-count pilot

Issue #42. **PROSPECTIVE research protocol; frozen after accepted P1l-A1b stage-isolation evidence and before any counter-instrumented GPU run.** P1l-A1b source HEAD `faa187d79f32c6f2a5eb7a55f7824897affd9bb7`, AMD Radeon 8060S RADV, 30/30 processes and 360/360 exact backend-specific accepted PFM frames, full GPU timestamp closure. See `../results/019-p1l-a1b-hwrt-software-stage-isolation.md`.

## Evidence-driven priorities (no assumed causal explanation)

Three persistent/scene-dependent absolute GPU bottleneck categories in P1l-A1b 36-frame median (three independent processes, *separate HWRT/Software runs*, not controlled paired treatment effects):
- **N003 primary binary BVH:** Software-minus-HWRT primary visibility **+272 to +314 µs across all five scenes** (1.50–1.55× ratio). Largest repeatable absolute stage gap.
- **E003 secondary spatial hash + quantized 8-way BVH:** secondary GPU traversal **+200 to +244 µs across all five scenes** (2.98–4.08×). Candidate secondary rays are identically reduced to 24,064–25,760 actual work items by canonical probe reuse. The Lane-E-final software shader is **`e003_instance_quantized.comp.glsl`**, **not** `i001_software_bvh.comp.glsl`. Distinguish hash/grid DDA overhead vs quantized child node visits vs triangle tests before choosing an algorithm.
- **N003 final composite/shadow binary BVH:** Software-minus-HWRT composite **+274 µs light-motion**, **+88 µs static**, **+87 µs deforming**, but only +3/+6 µs moving-rigid/camera. Composite also computes direct illumination, storage lookup and final pixels; it is not a pure “shadow traversal” timer. Need pixel-level shadow count/occlusion coverage to explain this workload dependence.

## P1l-B0: count-only minimal triage (small before large)

Implement N006-isolated **diagnostic variants** of the N003 primary and composite shaders and the E003 quantized secondary shader. These are *count-only* instruments; the accepted path and rendering remain untouched unless an explicit flag selects a separate diagnostic dispatch. Do not add extra work to timed baseline shaders or try to conclude a performance improvement from instrumented GPU timestamps.

For **each pixel** N003 primary:
- primary rays emitted, BVH nodes visited, AABB tests, leaf visits, triangle tests, hit/miss and stack overflow counts (per-frame sums and normalized mean/p50/p90/p99/max, not only aggregate atomic counters).

For **each pixel** N003 composite:
- valid primary pixels, illumination hemisphere-positive pixels, shadow rays actually entered, binary BVH/AABB/triangle work, first blocker/miss, overflow, storage lookup count. Maintain correct separation between *pixel count with positive cosine* and *actual launched nondegenerate shadow query*. Any-hit shadow return does not correspond to the same traversal objective as closest-hit primary or secondary.

For **each actual canonical secondary ray** E003:
- world-instance bounds tests, grid-DDA cell iterations, segment hash lookup probes, quantized BVH node pop/child AABB tests, leaf visits/triangle tests, 64-stack overflow, per-ray hash-loop overflow. Ensure instrumentation doesn't modify hit ordering, ray addresses, best-hit updates or binary representations of output. Accumulate bounded histograms separately per ray/pixel with deterministic reduction; no unbounded extra memory, race-dependent lookup, or concurrent writes that affect accepted results.

**B0 minimum workload:** `static`, `camera-motion`, `light-motion`, `moving-rigid`, `deforming-control` on Software with **one fresh process each** and one target-state canonical frame after warmup. Run the HWRT-rendered accepted shaders as uninstrumented control only to validate baseline outputs, not as a matching software work-count equivalent. If that first pass needs >10 minutes per process, stop as `invalid-retained` and investigate the diagnostic itself. For the first two workloads use `light-motion` (composite anomaly) and `camera-motion` (largest secondary ratio) as the initial smoke pair.

Must validate against per-backend exact accepted HDR PFM SHA, actual 24,064–25,760 ray output count, original owner weighting, canonical hash/zero overflow and raw GPU counters. **First recorded GPU timings must be from the uninstrumented build** with identical scene/target rays. Instrumented shader timings can only diagnose instrumentation overhead and are not published as performance wins. Each image and capture is immutable; avoid any accepted source mutations, especially N004/N005 and GH Actions.

## P1l-B1: prospectively select at most two performance candidates

Only after B0 work counts and correct SHA:
1. **Primary / shadow N003 target** if visit counts or shadow-query intensity correlate with the persistent +300 µs primary gap or light-motion +274 µs composite gap. Hypotheses could include near-first child traversal, coherence/locality, fewer redundant software shadow queries or a different software tree layout. Must preserve one-frame image SHA and semantics; no lighting quality relaxation.
2. **Secondary E003 target** if segment DDA+hash visits, quantized child decode bandwidth or leaf intersection counts explain the persistent +200–244 µs secondary gap. Hypotheses include hash-cell lookup reduction, alternative per-instance bounds hierarchy or traversal ordering; avoid blind global sort or recurring CPU-side scheduling. Do not import previously rejected storage/order variants without comparing to Lane B/C/J records.

**Candidate acceptance:** frozen pre-registered 5-scenario correctness and a separate, balanced 3 fresh-process matched current/candidate *GPU timestamp* test; report per-stage gain, complete-GI GPU including all new overhead, output image/hash/owner counts, GPU scratch peak and fail-close rate. If no robust process-median improvement or compiler/diagnostic complexity outweighs expected gains, document **REFINE/REJECT** instead of shipping.

## Scope boundaries

The present P1l-A1b result does **not** prove cross-backend equivalence for moving-rigid (accepted Software and HWRT PFMs have different SHA); it proves within-backend replay. Nor does it prove operation on actual HWRT-incompatible hardware. Any new shader diagnostic changing ray hit semantics, or an unbounded diagnostic allocation, is a failed B0 rather than a reason to loosen accepted image and storage gates.

**Current status: B0 instrumentation code NOT implemented, B0 GPU evidence NOT collected.** This document is a frozen implementer contract for a *separate, bounded measurement effort*. P1/P2 predictive allocation in Issue #42 remains gated. CPU-hit reference may be sampled once per process for B0 (declare sample) and must not be reintroduced on every warmup/frame.
