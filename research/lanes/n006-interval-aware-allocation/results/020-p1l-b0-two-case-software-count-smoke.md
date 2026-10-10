# N006 P1l-B0 — two-case software work-count smoke PASS

Issue #42. Evidence: user-uploaded **`n006-p1l-b0-work-counts-summary.json`**, protocol `n006-p1l-b0-work-counts-v1`, `mode=smoke`, `status=complete`, `failures=[]`, `formal=false`, clean HEAD **`257b0920858e86fd1d4e924d9b9580b0eb787aa8`**, AMD Radeon 8060S (RADV STRIX_HALO), Sponza SHA `2a86fdc2dc92d7c6a740682c61ec97f3101f489a06443c6823aff85bb990e5f6`. **2/2 software cases** accepted: `light-motion` and `camera-motion`. No path-traced reference generated. This diagnostic was prospectively frozen in `../experiments/015-p1l-b-n003-e003-work-count-triage.md`.

## Correctness and provenance

Both cases produced their **own** accepted HDR PFM hashes:
- Light: `7b48345b67311652fcba9f7083a21fa07eb316d6ded75a1807f75070516333ec`, 24,064 real secondary rays.
- Camera: `eb889a8796ebae5cfb23ff820c01fcf5e2fd2d21376dc06b8c4a447512362bcd`, 25,760 real secondary rays.

Per-case diagnostic fields `diagnostic_only=true`, `output_byte_identical=true` for independent N003 primary hit, N003 shadow composite image and E003 secondary hit outputs, `uninstrumented_gpu_timing=true`, 57,600 primary pixels. All N003/E003 diagnostic stack/segment overflow totals are **0**. The runner enforces complete accepted PFM SHA, one sampled N004 CPU-vs-GPU hit validator, owner/cascade/hash/counter and disjoint GPU timestamp gates; **this JSON is a summary**, so keep raw `n006-p1-intervention-v1` evidence and logs in the local output directory as source of detailed check records. This is a **smoke**, not all five-scene B0 acceptance.

## Work-count observations (instrumented diagnostic shader, NOT timing samples)

| Software diagnostic, one target frame each | light-motion | camera-motion |
| --- | ---: | ---: |
| Original primary hit pixels | 12,770 | 12,629 |
| Primary binary BVH node pops total | **1,579,216** | **1,569,726** |
| Primary node pops mean per pixel | 27.417 | 27.252 |
| Primary node pops per pixel p50/p90/p99/max | 1 / 107 / 255 / 431 | 1 / 111 / 247 / 391 |
| Primary triangle intersection tests total | 215,471 | 214,179 |
| Shadow queries launched | **9,797** | **0** |
| Shadow binary BVH node pops | **42,065** | **0** |
| Shadow triangle tests | **4,538** | **0** |
| Shadow first-hit blocker returns | **251** | **0** |
| Positive-cosine pixels | 9,797 | 0 |
| Storage probe lookup iterations | 51,080 | 50,516 |
| Actual secondary rays | **24,064** | **25,760** |
| E003 instance tests per ray | 2.000 | 2.000 |
| E003 DDA cells per ray | 2.629 | 2.631 |
| E003 segment-hash probes per ray | 3.441 | 3.439 |
| E003 wide BVH node pops per ray | 7.004 | 6.958 |
| E003 child AABB tests per ray | 26.304 | 26.210 |
| E003 triangle tests per ray | 7.776 | 7.654 |

Additional facts: 9,797/57,600 = **17.0%** of light-motion pixels launch a shadow ray; 251/9,797 = **2.56%** of shadow rays found a blocking triangle and exited early. The **conditional** cost for shadow rays that were actually launched is 42,065/9,797 = **4.29 BVH nodes/query on average**, compared to `0.730` if incorrectly averaged across all screen pixels. Importantly, shadow query p90=1 over *all pixels* does not indicate that the participating rays are cheap; the per-pixel maximum node pops is **307**. Camera-motion has zero rays because the cosine test is never positive in its accepted scene/light configuration; this is a **workload distribution**, not evidence its software shadow traversal shader is faster.

The primary binary BVH has a strongly heterogeneous screen work distribution (both p50 node pops = 1, p90 >100 and p99 ~250; similar between light/camera). Thus a uniform pixel mean hides divergence and tails, but there is no causal GPU warp execution profile yet.

## Descriptive, uninstrumented GPU stage times (ONE frame per scenario)

| Stage | Light (µs) | Camera (µs) |
| --- | ---: | ---: |
| Primary visibility | 1,039.575 | 1,491.273 |
| Secondary E003 traversal | 298.327 | 326.460 |
| Final composite incl. shadows & storage | **332.432** | **14.508** |
| Complete GI GPU (excludes final composite) | 1,549.143 | 2,060.475 |
| Complete renderer GPU (includes composite) | 1,881.575 | 2,074.982 |

These values are **single uninstrumented samples from different processes/scenarios**. They are neither an A/B matched timing nor the instrumented shader's own GPU elapsed time; do not claim an estimated speedup or that shadow BVH caused all 317.9µs of final-composite difference. However, the zero-vs-9797 shadow-query workload strongly explains why this stage differs by regime, and agrees with the earlier replicated **P1l-A1b** 36-frame composite medians (~299.93µs light vs ~16.99µs camera).

Secondary E003 profile appears very similar **per ray** across the two scenes, with low mean spatial-hash/DDA work (~3.4 probe lookups and ~2.6 cells), but ~26 quantized child AABB tests and ~7–8 triangle tests. This suggests **BVH child/AABB/leaf traversal** deserves examination before guessing that hash collision probes dominate. **Counts alone do not prove which operation costs the GPU time**; no isolated instrumented-vs-uninstrumented traversal timing effect is measured.

## Decision

**Accept two-case B0 smoke PASS; GO to the frozen full FIVE-scene standalone diagnostic run**, including static, moving-rigid and deforming-control, without changing instrumentation or correctness gates. Preserve the earlier two-case smoke separately; don't count 2+3 as the frozen full run. Command:

```sh
mise exec -- python scripts/research/n006_interval_aware_allocation/run_p1l_b0_work_counts.py
```

Each scene is one independent process with 32 source + 8 target warmups, one canonical measured frame and sampled N004 hit oracle, hard 600s timeout. The full run will fill variation in shadow query frequency, binary primary BVH and E003 wide node/triangles among the five accepted scenes. Only after its five-scene result should a focused P1l-B1 shader optimization hypothesis and **separately prospectively frozen matched-state GPU A/B** be selected. No N004/N005 behavior edits and no GitHub Actions.
