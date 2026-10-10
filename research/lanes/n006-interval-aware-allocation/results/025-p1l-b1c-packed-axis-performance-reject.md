# N006 P1l-B1c — packed-axis software-primary A/B REJECT (2026-10-11)

Issue #42. **GPU performance REJECT under prospectively frozen `experiments/018`**; shader remains N006 opt-in only. No full project speedup, hardware-independent RT parity or RC predictive-ray-allocation result.

## Provenance and data integrity

- User-uploaded `n006-p1l-b1c-summary.json`, full-file SHA-256 **`49b561e6e1daffeb611d1571daa8236a76a0f5328902ed0d1b656e8af59fe11e`** (572,094 bytes).
- Frozen protocol `n006-p1l-b1c-packed-axis-v1`, `status=complete`, `mode=matched`, `formal=false`, `failures=[]`, `results.decision=REJECT_OR_REFINE`, GPU **AMD Radeon 8060S Graphics (RADV STRIX_HALO)**; Sponza SHA `2a86fdc2dc92d7c6a740682c61ec97f3101f489a06443c6823aff85bb990e5f6`. Clean measured HEAD **`11eaabfa7666c41cdda84a679caae62d9a031711`** on `research-n006-interval-aware-allocation`.
- **15/15 independent processes** (5 named Lane-E-final Software scenarios ×3), **360/360 target frames**, **180 adjacent AB/BA pairs** (36 pairs/scene, 18 `01` and 18 `10`), frozen `011001100110011001100110` with 32 source +8 target warmups/process. Exactly 1 N004 CPU reference hit audit sampled per process (candidate frame 1); reference images **not regenerated**.
- Summary-level per-process `baseline_primary_bytes_equal_all_frames=true`, and all 360 reported `primary_hits_byte_exact=true` and accepted renderer PFM SHA. Independently recalculated all 5 scene median percentages and faster-pair counts from raw 180 embedded pairs; no discrepancy; all 15 process IDs unique, each arm pattern exact, expected 360 frames. The raw per-process evidence JSON/PFM bytes were **not** separately supplied for a cryptographic re-audit; the summary provides evidence fields and raw hashes only.
- B1c’s host packs child-center separation axis/sign into unused internal-node `GpuBvhNode.data.z` (48 B/node unchanged), while leaves keep primitive offset. B1c shader does not read two extra child bounds for sorting; **shader performance is not automatically improved**.

## Prespecified GPU-primary and complete-renderer gates

Numbers are **median of 36 within-process adjacent candidate-minus-original paired percentages**, not percentage of global frame medians. Negative is faster. Each scene also requires ≥24/36 faster primary pairs, ≥2/3 faster independent per-process primary medians, and ≥5% paired median primary improvement. At least 3/5 scenes must pass all three, while every scene must have complete renderer paired median ≤+3%.

| Scene | Primary median (%) | Primary median (µs) | Faster primary pairs /36 | Per-process primary medians (µs) | Renderer paired median (%) | Primary gate | Renderer ≤+3% |
|---|---:|---:|---:|---|---:|---|---|
| static | **−6.585** | −68.55 | **25** | −5.7 / −68.6 / −361.1 | **−5.099** | PASS | PASS |
| camera-motion | **−8.820** | −95.74 | **22** | −126.6 / −146.1 / −17.9 | **−7.789** | FAIL (22/36) | PASS |
| light-motion | **+4.198** | +33.22 | **13** | +23.3 / −3.1 / +235.0 | **+5.237** | FAIL | **FAIL** |
| moving-rigid | **−2.627** | −34.77 | **19** | −160.7 / +199.4 / −34.8 | **−1.457** | FAIL | PASS |
| deforming-control | **−2.858** | −29.58 | **19** | −112.0 / +56.7 / +99.5 | **−0.234** | FAIL | PASS |

**Decision: REJECT.** Only **1/5** scenes passes the prospective primary rule (need ≥3); light-motion independently breaches mandatory whole-renderer +3% regression bound (actual +5.237%). Static and camera performance reductions must not be cherry-picked. The historical B1a `REJECT` and B1b mechanism-only `PASS` remain unchanged.

## Cost and confounders

- Host `b1c_axis_pack_cpu_us` is an **aggregate within each process** (initial source tree and target refresh, not per measured frame). Per-case range across 3 processes: static **645–694µs**, camera **651–679µs**, light **664–669µs**, moving-rigid **1,286–1,377µs**, deforming **1,337–1,393µs**. Internal nodes visited by packer (source+target cumulative) **65,632** in static/camera/light, **131,264** in rigid/deforming. This is added CPU work; not a measured per-frame overhead nor included in primary GPU timestamps.
- Primary paired-percent AB `01` vs BA `10` median by scene: static **−5.43/−13.75%**, camera **−12.88/+0.54%**, light **+8.14/+2.84%**, moving-rigid **−22.78/+20.07%**, deforming **−3.09/+3.28%**. Strong residual timing-order/clock interference in several scenes despite balanced sample counts. Do not infer causal per-node costs from these differences.
- B1c SPIR-V audit file `b1c-spv-audit.json` was **not attached**, so no actual compiler opcode/binary-size result is claimed. GPU cache misses, register occupancy, dynamic instruction counts and physical memory loads remain unmeasured.
- Results are one target GPU/scene set only; no independently generated reference frames, no HWRT-incompatible GPU test, no causal partition of traversal memory vs ALU vs divergence.

## Next research / STOP rule

Close **B1c and the B1a/B1c primary child-order family as performance candidates** under these five scenarios. Preserve their opt-in shaders and evidence for reproducibility; do not modify accepted N003 primary or add a new unmeasured child-order heuristic.

Move to **independent E003 secondary quantized 8-way BVH** source/SPIR-V cost audit and bounded targeted hypothesis, based on accepted B0 ~25.5–26.3 child AABB tests per actual ray vs ~3.4 segment hash probes/ray (not evidence that AABB dominates GPU cycles). Source uses 8 child candidates with dequantize and `ray_aabb_bounds` slab divisions; check whether the actual compiler hoists divisions and how child occupancy/long rays differ **before altering math**, because `a/d` versus `a*inverse(d)` can change floating-point equality and accepted hit/PFM bytes. No new GPU run until a separate prospective E003 experiment plan is frozen.

Parent Issue #42 RC-specific marginal-value prediction P1/P2 and HWRT-free parity remain **unresolved**. No changes to N004/N005, accepted N003/E003 shaders, CI or GitHub Actions.
