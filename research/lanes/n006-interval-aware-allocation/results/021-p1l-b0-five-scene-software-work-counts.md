# N006 P1l-B0 — five-scene software BVH work-counts PASS

Issue #42. **Frozen full five-scene diagnostic accepted (non-formal work attribution, NOT speedup)**. User-uploaded `n006-p1l-b0-work-counts-summary(2).json`, raw file SHA-256 `092367d5e5eb3bfb79e48f2a7949dbfe7625c1408b15420cc422f49c1139133b`. Protocol `n006-p1l-b0-work-counts-v1`, `mode=five-scenes`, `status=complete`, `failures=[]`, clean source HEAD `eebd9b2771e0dfbdba5b102083b52604b5a1e387`, GPU AMD Radeon 8060S RADV, Sponza SHA `2a86fdc2dc92d7c6a740682c61ec97f3101f489a06443c6823aff85bb990e5f6`. One independent software run **per** light-motion/camera-motion/static/moving-rigid/deforming-control, **5/5 PASS**, each after 32 source and 8 target warmup frames, one lean-copyback canonical target, one CPU N004 hit oracle. No independent path-traced reference, no HWRT-incapable hardware evaluated.

Each accepted renderer PFM matched its backend-specific frozen SHA. The **three independent count-only shaders** (N003 primary, N003 composite, E003 secondary) produced GPU output **byte-identical** to their uninstrumented outputs; each recorded `output_byte_identical=true`, no overflow, correct actual canonical rays (24,064, 25,760, 24,064, 24,832, 24,232), all original work and owner restore/hash/storage gates passed in the fail-closed runner. Original GPU renderer timestamps were measured **before** all separate instrumented dispatches; `instrumented_timing_valid=false`, diagnostic visit counts alone do not indicate GPU execution cost.

## Count summary — EXACT five scene GPU frames

All numbers below are **count-only** samples, not GPU timing. N003 primary includes 57,600 pixels (320×180) even when pixels miss geometry; all percentages have explicit denominators.

| Metric | light-motion | camera-motion | static | moving-rigid | deforming-control |
| --- | ---: | ---: | ---: | ---: | ---: |
| Valid primary pixels | 12,770 | 12,629 | 12,770 | **18,357** | 12,772 |
| N003 primary BVH node pops, TOTAL | **1,579,216** | 1,569,726 | **1,579,216** | **2,482,542** | 1,617,954 |
| N003 primary node pops / screen pixel | 27.417 | 27.252 | 27.417 | **43.100** | 28.089 |
| N003 primary node pops p90 / p99 (screen pixels) | 107 / 255 | 111 / 247 | 107 / 255 | **139 / 301** | 107 / 261 |
| N003 primary triangle tests, TOTAL | 215,471 | 214,179 | 215,471 | **308,280** | 222,507 |
| Software shadow rays actually launched | **9,797** | **0** | 251 | **0** | 251 |
| Shadow N003 BVH node pops, TOTAL | 42,065 | 0 | 16,383 | 0 | 15,873 |
| Shadow nodes per **launched shadow ray** | 4.294 | n/a | **65.271** | n/a | **63.239** |
| Shadow triangle tests, TOTAL | 4,538 | 0 | 3,732 | 0 | 3,644 |
| Shadow first-blocker returns | 251 | 0 | **224** | 0 | **224** |
| Actual secondary E003 rays | 24,064 | 25,760 | 24,064 | 24,832 | 24,232 |
| E003 grid DDA cells/ray | 2.629 | 2.631 | 2.629 | 2.587 | 2.622 |
| E003 segment hash probes/ray | 3.441 | 3.439 | 3.441 | 3.412 | 3.423 |
| E003 quantized node pops/ray | 7.004 | 6.958 | 7.004 | 6.718 | 6.986 |
| E003 quantized child AABB tests/ray | **26.304** | 26.210 | 26.304 | 25.532 | 26.043 |
| E003 triangle tests/ray | 7.776 | 7.654 | 7.776 | 7.273 | 7.944 |

Moving-rigid's **2,482,542** primary node visits are **57.2% more** than static's 1,579,216, concurrent with a 43.10 versus 27.42 screen-pixel mean, +5,587 visible primary hit pixels, and higher primary work tail (p99=301 versus 255). This is **not a same-scene causal treatment** and does not establish a 57.2% time increase; work content and geometry changed. Primary BVH hot rays require investigation into spatial order, child traversal order and screen-coherence divergence, particularly moving-rigid.

The **shadow case split is NOT monotone with ray count**. Light-motion launched 9,797 shadow rays but traversed ~4.29 nodes/ray, with only 251/9,797 (**2.56%**) returning first blockers. Static/deforming launched only 251 rays but ~63–65 nodes/ray, with 224/251 (**89.2%**) returning a blocker. The same software shader is used; long per-ray traversal and any-hit stopping behavior vary. Camera-motion/moving-rigid launched exactly zero (positive cosine zero), so their final composite does not exercise software shadow BVH. Per-screen-pixel percentiles are dominated by zero work and cannot be reused as percentiles **among launched shadow rays**.

The E003 *secondary* ray workload is consistent across all five: only 2.59–2.63 DDA cells, 3.41–3.44 hash probes, ~6.7–7 quantized node pops, **25.53–26.30 child AABB tests** and 7.27–7.94 triangles/ray. **Counts don't prove that child AABB tests dominate GPU cycles**. This still suggests no obvious excessive hash probing on the tested 2-instance workload, so changing hash layout first is poorly motivated without counterfactual measurement. No multi-device/high-churn generalization.

## Context only: original uninstrumented GPU times (single frame each)

| GPU stage (µs) | light | camera | static | moving rigid | deforming |
| --- | ---: | ---: | ---: | ---: | ---: |
| Primary visibility | 844.81 | 929.81 | 1550.35 | 1384.79 | 1168.14 |
| Secondary E003 traversal | 335.76 | 358.52 | 389.34 | 359.36 | 302.05 |
| Final composite incl. shadow | 306.18 | 20.20 | 121.99 | 17.63 | 116.74 |
| Complete GI GPU (excl. final composite) | 1416.45 | 1529.95 | 2172.13 | 1974.27 | 1714.86 |

These GPU times were recorded by the **original uninstrumented** shaders but **only one frame per separately run scenario**; prior accepted [A1b repeated GPU stage diagnosis](./019-p1l-a1b-hwrt-software-stage-isolation.md) is authoritative for reproducibility. Do not use visit/time ratios across scenarios to ascribe nanoseconds per BVH node or estimate a candidate speedup. Performance regression, frequency/thermal noise, traversal memory latency and wave occupancy have not been isolated.

## B0 decision / next experiments

**B0 full 5/5 PASS.** Freeze [P1l-B1 targeted near-first software traversal experiment](../experiments/016-p1l-b1-primary-near-first-traversal.md) separately **before** implementation and *before* observing candidate GPU time.

Priority 1: **N003 software PRIMARY binary BVH**: current accepted shader always pushes left child then right and thus pops right first, independent of ray direction/distance. Evaluate a N006-only near-first child scheduling variant (without changing tree topology, intersection math, tie tolerance, output format or accepted shaders) against a same-process baseline. This directly targets 1.57–2.48M node pops and long tails, and the previously reproduced +272–314µs absolute software primary-versus-HWRT gap. A second **independent** candidate for N003 shadow ray any-hit scheduling should be designed only if primary results/histograms justify it; test blocker-rich static/deforming and mostly-unblocked light distinctly. E003 secondary wide-BVH visit optimization is also plausible, but **do not start competing hash/memory rewrites before determining primary traversal gain**.

Do not claim B0 implementation yields improved GPU time. Keep original N004/N005/GitHub Actions untouched, preserve old 2-scene smoke independently, and original N006 P1/P2 marginal-value allocator remains gated.
