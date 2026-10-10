# N006 P1l-B1b — Primary BVH work-count reduction confirmed, B1a GPU-performance REJECT unchanged

Issue #42. **Accepted frozen five-scene diagnostic result: 5/5 PASS (mechanism only, not GPU speedup).**

## Provenance / checks

User-uploaded `n006-p1l-b1b-counts-summary.json` (SHA-256 **`9c6bb80ee45d09de028228b9ba0a6e0a05dfab9b8292d4dbe2e22ba217284662`**), protocol `n006-p1l-b1b-paired-primary-counts-v1`, `mode=five-scenes`, `status=complete`, `failures=[]`, `formal=false`; measured **clean Git HEAD `b4f0a8bffc78612f69b78f7ca5ec2be0c8560659`** on **AMD Radeon 8060S Graphics (RADV STRIX_HALO)** with frozen Sponza scene SHA `2a86fdc2dc92d7c6a740682c61ec97f3101f489a06443c6823aff85bb990e5f6`. All five Lane-E-final SOFTWARE cases: light-motion, camera-motion, static, moving-rigid, deforming-control. One process and one original uninstrumented canonical target frame per scenario, following 32 source +8 target-state warmups, and one sampled N004 CPU hit oracle at frame 0/process. All five case-specific accepted HDR PFM SHA passed the frozen validator.

**Both separate diagnostic shaders produced primary GPU hit bytes identical to the uninstrumented original**, `original_hit_byte_exact=true`, `near_first_hit_byte_exact=true`; original and candidate hit-pixel totals equal. 0 stack overflow in either arm and no reported failed case. `instrumented_timing_valid=false`: the measured `original_uninstrumented_gpu_stage_us` values belong only to the **original renderer frame** and **must not** be compared as near-first GPU times. No independent path-traced reference, no HWRT-unavailable device and no proof of cross-device portability.

The original N003 software primary traverses a fixed child order, while B1a near-first computes **each child center by loading two additional BvhNode records and projecting them onto ray direction** before choosing LIFO order. The B1b candidate shader reproduces this B1a ordering with the exact same count instrumentation as the B0 baseline; these are direct, same-state per-pixel *algorithm work counts* on 57,600 screen pixels, not timed GPU executions.

## Five-scene work comparison (near-first minus original)

| Scenario | Original primary node pops | Near-first node pops | Node change | Original triangle tests | Near-first triangle tests | Triangle change |
|---|---:|---:|---:|---:|---:|---:|
| light-motion | 1,579,216 | 1,535,062 | **−2.80%** | 215,471 | 165,809 | **−23.05%** |
| camera-motion | 1,569,726 | 1,477,012 | **−5.91%** | 214,179 | 146,878 | **−31.42%** |
| static | 1,579,216 | 1,535,062 | **−2.80%** | 215,471 | 165,809 | **−23.05%** |
| moving-rigid | 2,482,542 | 2,399,032 | **−3.36%** | 308,280 | 288,188 | **−6.52%** |
| deforming-control | 1,617,954 | 1,581,890 | **−2.23%** | 222,507 | 172,811 | **−22.33%** |

**5/5 scenarios have fewer primary node pops AND fewer triangle intersection tests** with the near-first ordering, although visit reduction is modest (**2.2–5.9% node pops**) compared with the triangle test saving (**6.5–31.4%**). In every scene most pixels have *equal* node pops: **54,352–55,314 / 57,600 (94.4–96.0%)**. Reduced node-work pixel count **1,681–2,820** versus increased-work pixels **420–630**; thus a small fraction of heavy pixels accounts for the aggregate savings. Original vs candidate primary-hit GPU buffers were byte-for-byte equal (no change in accepted image or intersection semantics).

Selected tails deserve caution: static/light primary node-pop p99 **255→259**, moving rigid **301→307**, despite lower totals. Per-pixel traversal tail is **not uniformly improved**, another reason raw sum-of-node visits cannot be equated with faster SIMT execution. The B1b comparison is only one frozen target frame per scenario; it measures deterministic work for that frame, **not a repeated performance distribution**.

## Reconcile with REJECTED B1a GPU timing

The **previous prospective B1a performance gate was failed**: 15 fresh processes ×24 target frames each (360 images, 180 adjacent AB/BA pairs), 5/5 correct images and hits, but **0/5 primary speedup scene wins** and **4/5 complete renderer median regressions over the frozen +3% cap**. Paired primary GPU median candidate−original: static **−1.35%**, camera **+6.19%**, light **+12.60%**, moving **+10.11%**, deforming **+15.89%** (positive = slower). See `023-p1l-b1a-matched-near-first-reject.md`. GPU timings in that study showed AB-vs-BA order effects; B1b does not remove that uncertainty.

**Evidence-supported conclusion:** the B1a heuristic really does prune some software primary traversal work, **but as implemented it did not produce a robust GPU speedup**. The B1a candidate performs extra child-node reads, floating-point dot calculations and conditional branching; shader/memory fetch cost, divergent scheduling and GPU-clock variability are plausible reasons, **not individually measured causal bottlenecks**. It is invalid to claim any exact cost breakdown or to accept B1a based on count improvements. **B1a remains REJECTED and MUST NOT be enabled by default or merged into N003.** Do not repeat the expensive 180-pair original B1a performance experiment without a new prospectively frozen alternative.

## Next research (handoff only; NO B1c GPU run or implementation yet)

**Priority: P1l-B1c bounded instruction / child-load cost attribution**. First perform offline, reproducible SPIR-V diff of the original N003 software primary and B1a near-first primary shaders (SPIR-V binary size, shader instruction family/load/branch counts, toolchain and compilation flags); distinguish *static counts* from dynamic execution, physical memory transactions and device occupancy, which require actual counters. Inspect the original GPU BVH node memory layout and update path; evaluate whether the ordering proxy could be precomputed/packed at build time to avoid runtime child-node loads *without changing hit logic or introducing repeated expensive rebuilds*. This is a **research hypothesis, not a designed/accepted candidate**.

If a plausible lower-cost candidate emerges, **freeze the new candidate protocol before implementing/seeing results**. Require same accepted PFM and primary-hit bit parity on all five software scenarios, GPU stage accounting and owner/hash/overflow fail-closed gates. Begin with two-scene bounded smoke (include moving-rigid), then a prospectively balanced same-process comparison after smoke PASS; report net complete-renderer changes and extra memory/build/update overhead. Do **not** loosen the prior B1a gate or cherry-pick static. If source/instruction audit undermines near-first efficiency, explicitly close the center-projection direction and move to the **independent E003 secondary quantized eight-way BVH child-AABB traversal** problem (~25.5–26.3 child AABB tests/ray, ~3.4 hash probes/ray in B0); shadow any-hit is a separate scene-conditional hotspot.

**Status: B1b five-scene experiment ACCEPTED as mechanism measurement; software RT performance improvement still UNSOLVED; original Issue #42 predictive marginal-value allocator P1/P2 still gated.** See `../HANDOFF_NEXT_SESSION.md`. No N004/N005/GitHub Actions changes.
