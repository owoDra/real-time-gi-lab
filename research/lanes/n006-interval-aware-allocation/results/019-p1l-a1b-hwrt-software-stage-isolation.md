# N006 P1l-A1b — 30-process HWRT/Software GPU stage-isolation PASS

Issue #42. **Non-formal stage-diagnostic result, accepted with sampled CPU reference only**. Source: user-uploaded `n006-p1l-a1b-sampled-hit-summary.json`. Protocol `n006-p1l-a1b-sampled-hit-stage-isolation-v1`, source clean HEAD `faa187d79f32c6f2a5eb7a55f7824897affd9bb7`, AMD Radeon 8060S Graphics (RADV STRIX_HALO), accepted Sponza. Raw summary: `status=complete`, `failures=[]`, 10 backend/scenario cells, **30/30 fresh processes**, **360/360 measured frames**; `formal=false`, no independent rendered reference. These are **reported actual GPU timestamps**, not CPU wall time.

### Measurement correctness and limitation

Each HWRT and Software × five Lane-E-final scenarios had three independent processes, 32 source + eight current target warmups, then 12 canonical P1j-A lean-copyback steady-state GPU frames/process. The uploader's runner required *all measured* PFM SHA hashes to equal pre-accepted **backend-specific** exact source/candidate PFM SHA, visible owner/output/cardinality/weighted multiplicity/hash+storage fail-closed gates, 32,768-slot GPU hash and 4,489,304 B scratch, no measured traversal maintenance, and disjoint GPU timestamp closure.

Further summary inspection: **360/360 expected PFM SHA equal**, all 30 processes delivered exactly 12 measured frames, all 30 warmup tails had zero maintenance, and maximal absolute recorded GI timestamp closure **4.55×10⁻¹³ µs**; composite closure exactly zero in the uploaded JSON. Original/canonical actual rays per scene were 133344→24064 static/light, 135392→25760 camera, 134816→24832 rigid, 133504→24232 deforming.

A1b ran the full N004 CPU-versus-GPU per-ray hit validator **once per process, on measured frame 0**. All other 11 measured frames/process were **not individually CPU oracle validated**, by intentional protocol design; their image bit-parity, GPU hit/storage and timing guards still applied. The result cannot be upgraded to 360 fully CPU-verified independent hits nor proof on a device lacking HWRT extensions. The old A1 4/30 CPU-bound `in-progress` campaign remains separate and incomplete, not part of these 30 runs.

### Main result: GPU stage medians per scenario (µs)

Each number is the median of **36 GPU frame samples** from three fresh processes *per backend/scenario*, not a matched pair. Software/HWRT ratios are **unpaired descriptive**. Note that complete GI does **not include** the final composite pass.

| Scenario | Primary HWRT→Software | Secondary traversal HWRT→Software | Composite/shadow HWRT→Software | Complete GI HWRT→Software |
|---|---:|---:|---:|---:|
| static | 560.59→871.08 (**1.55×**) | 88.45→311.53 (**3.52×**) | 24.65→113.11 (**4.59×**) | 868.49→1416.21 (1.63×) |
| camera-motion | 500.47→772.71 (1.54×) | 79.19→323.27 (**4.08×**) | 10.54→16.99 (1.61×) | 792.61→1345.72 (1.70×) |
| light-motion | 572.31→855.79 (1.50×) | 96.44→319.95 (**3.32×**) | 26.19→299.93 (**11.45×**) | 875.24→1435.75 (1.64×) |
| moving-rigid | 543.53→828.87 (1.52×) | 98.07→309.81 (**3.16×**) | 14.93→17.85 (1.20×) | 886.87→1388.60 (1.57×) |
| deforming-control | 627.83→942.17 (1.50×) | 101.25→301.61 (**2.98×**) | 25.89→113.09 (**4.37×**) | 989.26→1476.91 (1.49×) |

Other stages are **approximately backend-neutral** across all five scenarios: canonical build GPU ~49–54 µs each, owner producer ~61–68 µs each. This suggests (not proves) the dominant Software performance gap is traversal, not the shared canonical producer/hash.

The Software-primary *absolute* gap is **+272 to +314 µs** across scenes; secondary traversal gap **+200 to +244 µs** across scenes. Light-motion Software final composite has an **extra +274 µs** over HWRT and is the primary exceptional composite case. Composite gap is also +88 µs in static and +87 µs in deforming, but only +6 µs in camera and +3 µs in moving rigid. The final composite contains direct lighting, software shadow ray occlusion and indirect sample lookup; **cannot attribute all composite delta to BVH shadow traversal without instrumenting**.

### Root-cause interpretation, constrained to actual inspected source

The Software **primary and final composite** shaders selected by N006 come from existing N003 binary software BVH:
- `shaders/research/lane_n_end_to_end_renderer/n003_primary_software.comp.glsl`
- `shaders/research/lane_n_end_to_end_renderer/n003_composite_software.comp.glsl`

Both have per-pixel binary BVH stack traversal; the composite has a conditional `visible_to_light` path with an early-out any-hit shadow traversal. The Software **secondary** GI-ray stage is a different algorithm altogether: `e003_instance_quantized.spv` from `shaders/research/lane_n_end_to_end_renderer/imported/lane_e_dynamic_geometry/e003_instance_quantized.comp.glsl`, with object-local instance bounds, spatial hash cell lookup/DDA, quantized 8-child BVH and triangle tests. It is **not** `i001_software_bvh.spv` in the Lane-E-final software variant. Therefore do not combine primary/shadow findings with E003 secondary node visit theories; these are independent optimization domains.

Scene-specific moving-rigid SHA remains **different between accepted HWRT and software output** (`b0829e21214de633f80c935ddcfa5ca63204c2c1e353ff5ea1f9fd9b7eb1fe17` vs `d1e43a880cd7a4276b62127b6ae64cf4d1b50ca7922c81589095783fe055a0dd`). A1b proved **each variant repeats its own accepted image**, not cross-backend equality for moving rigid; neither silently reconcile nor infer algorithmic equivalence in that case.

### Decision / next gate

**A1b = PASS as a stage-bottleneck attribution campaign.** Strong replicated evidence of two Software traversal-related costs and an additional scene-dependent final composite hotspot. Do **not** tune canonical hash/copyback as the lead next intervention; those stages are near backend neutral, and P1k did not establish a universal direct-copyback advantage.

**GO to P1l-B measurement-only finer attribution** before selecting a code optimization:
1. Split N003 primary cost by actual binary BVH node and triangle visits per pixel; in final composite separately count pixels entering direct-light occlusion, software shadow BVH node/triangle visits and shadow-ray hit/miss. Specifically explain why light-motion composite is **11.45×**, while camera/moving rigid are only **1.2–1.6×**.
2. Separately capture E003 quantized secondary traversal counts: instances tested, grid/DDA cell steps, hash probes, eight-way node/child AABB visits and triangle tests. Distinguish per-ray work distribution (p50/p90/p99/max) from total dispatched 24064–25760 rays. Keep post-GPU profiling **timing builds uninstrumented**; count-only shaders can perturb occupancy/cache and must not be used as performance wins.
3. At most two later targeted optimization hypotheses, after counters show real hot spots. Every intervention must preserve full backend-specific image SHA and finite GPU resource/correctness guards. Confirm on a genuinely ray-query-incapable GPU separately if claiming HWRT-free compatibility.

**No P1l-B experiments have run yet**. No GitHub Actions, no N004/N005 semantics or old accepted raw data changed. N006's unrelated original predictive ray allocation P1/P2 is still gated.
