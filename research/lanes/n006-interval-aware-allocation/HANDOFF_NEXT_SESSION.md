# N006 GPU GI research — Next-session handoff (2026-10-10, after P1l-B1b)

> **Read this first in the next session.** This handoff is a durable GitHub file, not a running automation. The user explicitly wants the **next research to be done next session**, not now. Do not ask stage-by-stage permission after continuing: finish all repository-side investigation/code/tests you can, then request the **minimum** hardware-only NixOS GPU execution, with one end-to-end command where possible.

## 1. Repository, branch, collaboration contract

- GitHub repository: **`owoDra/phos-gi-lab`**, Issue **[#42](https://github.com/owoDra/phos-gi-lab/issues/42)**, working branch **`research-n006-interval-aware-allocation`**. Read the latest remote branch/Issue on resumption; its HEAD will differ from the measured B1b HEAD after writing this results/handoff document. **Do not assume an earlier SHA is the current HEAD**.
- B1b measurement was made from clean **`b4f0a8bffc78612f69b78f7ca5ec2be0c8560659`**. Its analysis is now recorded at **`research/lanes/n006-interval-aware-allocation/results/024-p1l-b1b-five-scene-near-first-work-reduction.md`**. This file is the latest accepted scientific result, **not** a new performance optimization.
- N006 research commits go **directly to this research branch, no PR required**. Do **not** add GitHub Actions or CI (the user expressly forbids them). Do not mutate N004/N005 and earlier accepted production/baseline shaders or rewrite historical result files. Keep tests, experiment protocol, docs/README and Issue #42 in sync with commits.
- Target GPU: **AMD Radeon 8060S Graphics (RADV STRIX_HALO)**, NixOS 26.05, Vulkan, Sponza `assets/Vulkan-Samples-Assets/scenes/sponza/Sponza01.gltf`. Scene SHA `2a86fdc2dc92d7c6a740682c61ec97f3101f489a06443c6823aff85bb990e5f6`. `mise run build` and `mise exec -- python ...` are the existing entry points.
- Research target is **HWRT-free software dynamic GI that approaches or beats hardware ray tracing without brute-force increasing ray count/memory/compute**. GPU timestamp is the primary performance source; wall time diagnostic only. N006 Issue #42's predictive interval-aware marginal-value allocation P1/P2 **still has not been validated** and must not be conflated with this software BVH study.
- GitHub connector can inspect/edit/commit repository files. **It cannot access the user's local AMD GPU to execute Vulkan**; honestly distinguish coding/source audit from actual GPU evidence. Never invent GPU timings or pretend to have executed the target hardware.

## 2. Exact current status — B1b **COMPLETE, 5/5 PASS**

The user uploaded **`n006-p1l-b1b-counts-summary.json`**; file SHA-256 **`9c6bb80ee45d09de028228b9ba0a6e0a05dfab9b8292d4dbe2e22ba217284662`**. Protocol `n006-p1l-b1b-paired-primary-counts-v1`, `mode=five-scenes`, `status=complete`, `failures=[]`, `formal=false`, `instrumented_timing_valid=false`. Independent **5/5 Lane-E-final SOFTWARE scenario processes** passed: light-motion, camera-motion, static, moving-rigid, deforming-control. Each case started from 32 source +8 target-state warmups, one original canonical lean-copyback target frame, one sampled N004 CPU ray-hit check.

All five original HDR images matched accepted backend-specific PFM SHA; both N006 primary count-only shader variants (fixed original order vs approximate near-first) wrote *separate* GPU primary hit buffers, and **each matched the original uninstrumented hit buffer byte-for-byte**; hit flags matched and **stack overflow 0**. No independently generated reference in this B1b, no test on hardware lacking HWRT. B1b is **mechanism/work-count analysis only; no candidate GPU time measured**.

### N003 software PRIMARY BVH — real measured traversal work

| Scene | Original node pops → near-first | Node count change | Original triangle tests → near-first | Triangle change |
|---|---:|---:|---:|---:|
| Static | 1,579,216 → 1,535,062 | **−2.80%** | 215,471 → 165,809 | **−23.05%** |
| Camera | 1,569,726 → 1,477,012 | **−5.91%** | 214,179 → 146,878 | **−31.42%** |
| Light | 1,579,216 → 1,535,062 | **−2.80%** | 215,471 → 165,809 | **−23.05%** |
| Moving rigid | 2,482,542 → 2,399,032 | **−3.36%** | 308,280 → 288,188 | **−6.52%** |
| Deforming | 1,617,954 → 1,581,890 | **−2.23%** | 222,507 → 172,811 | **−22.33%** |

**Critical interpretation:** B1a's ray-projected center child sort genuinely reduced both node visits and triangle intersections **in every tested scene**. This disproves the alternative hypothesis “B1a slows GPU because it failed to prune any work.” Yet node counts drop only ~2–6%, and **94–96% of screen pixels have unchanged node pops**; p99 node visits can *increase* (static/light 255→259, moving 301→307). No simple “less visits → faster GPU” correspondence.

### Previous B1a GPU performance study — irrevocably REJECTED

Prospectively frozen result `results/023-p1l-b1a-matched-near-first-reject.md`: **15/15 independent processes, 360/360 PFM and primary-hit byte-exact frames, 180/180 same-process ABBA pairs**. B1a candidate had this paired **primary GPU median % candidate−baseline**:

| Static | Camera | Light | Moving rigid | Deforming |
|---:|---:|---:|---:|---:|
| **−1.35%** | **+6.19%** | **+12.60%** | **+10.11%** | **+15.89%** |

**0/5 scenarios** passed the prospectively frozen ≥5% primary gain +≥24/36 faster pairs +≥2/3 winning process medians. **4/5 scenarios** regressed the complete renderer median by >+3%. Some time-dependent order interference/noise was present even with balanced AB/BA samples; it did not rescue the failed criteria. **B1a stays REJECTED. Never enable as default or merge the near-first code into the accepted N003 shader.** B1b does NOT reopen the performance decision.

## 3. Why work decreased yet GPU got slower — OPEN, NOT ALREADY PROVEN

Original N003 software-primary GLSL's binary node has `vec4 bounds_min; vec4 bounds_max; uvec4 data;` and LIFO stack order fixed as `push child x`, then `push child y`. Rejected B1a clone `shaders/research/n006_interval_aware_allocation/n006_p1l_b1_primary_near_first.comp.glsl` reads **both child node bounds** at every internal node, computes two `center = (min+max)/2` and ray projections `dot(center − origin,direction)`, branches and pushes estimated far then near. B1b clone adds separate counters with the same traversal order.

Likely mechanisms worth *testing*, **not established causal facts**:
- **Extra child-node SSBO loads / cache or bandwidth pressure** and the additional dot, comparison and branch instructions are more expensive than the reduced triangle tests. Counts do **not** measure physical memory transactions, latency, register pressure or GPU occupancy.
- **SIMT wave divergence / instruction and register pressure**: node-pops p50 per screen pixel is 1; a small subset of expensive rays carries most visit reduction while p99 can worsen. The fastest raster/SIMT behavior may differ from aggregate scalar BVH work.
- **Measurement/clock and order interference**: B1a full study had substantially different AB vs BA primary paired distributions. Do not assume all slowdowns reflect shader instruction mix until independently isolated with controlled counters/repeats.
- **Approximate center-projection sorting is not exact near-entry sorting**, so pruning gains are workload-specific, modest and can trade against extra node fetches.

Neither B1b JSON nor earlier B1a timestamps alone can identify what share of the GPU slowdown is due to any of the above.

## 4. Next session research plan — continue autonomously

**Priority A — P1l-B1c: *bounded, measurement-first* cost attribution; do NOT immediately write another full experimental renderer variant.**

1. **Refresh branch HEAD, Issue #42, accepted evidence**: this handoff, `results/024`, `results/023`, `experiments/016` and `experiments/017`, and source files listed below. Verify latest state and clean research branch before changes. User has already provided B1b result; **do not ask them to rerun B1b**.
2. **Reproducible offline shader audit**: inspect how N003 and B1a compile into SPIR-V on the actual Nix toolchain: shader compiler version/options, exact SPIR-V lengths, `OpLoad`/branch/vector arithmetic instruction family counts and differences, and inspect binary node layout / existing GPU data generation. The assistant can implement scripts/tests/stat validators and push without waiting for user confirmation. SPIR-V instruction counts are STATIC compiler artifacts, **not per-ray executed instructions, GPU cache misses, occupancy or measured runtime**. If Vulkan physical profiler counters aren't accessible, explicitly mark them *unmeasured*.
3. **Choose a *single* falsifiable low-overhead candidate or a STOP for near-first** after the audit: e.g. a conservative precomputed node-order proxy/packed split axis if node format, geometry update and memory budget allow it; or a better caching/coalescing strategy that avoids **two additional child-node reads at every internal node**. Before any implementation, account for **BVH construction/rebuild/update cost** on rigid, deforming and topology churn and ensure no per-frame extra global sort. A source-level “cheaper near-first” is a hypothesis, not an accepted implementation. No extra shader-specific per-frame allocations and no hardware ray-query reliance.
4. **Freeze new B1c protocol before GPU results**: exact five-scene accepted HDR image SHA and GPU primary-hit byte parity, no overflow and same canonical ray/owner/hash/stage closure; smoke **light-motion + moving-rigid** (moving-rigid is mandatory because prior B1a strongly regressed), capped per-process runtime. If correct, balanced same-process repeated GPU-primary+whole-renderer timings and full memory/build/update accounting. Compare candidate and accepted ORIGINAL shader, **not** against rejected B1a as if it were baseline. Keep a strict renderer non-regression gate and predeclared primary improvement criterion. Don't cherry-pick one scene.
5. **If offline evidence says child-sort overhead cannot be reduced credibly**, document B1c `NO-GO` without burning another 15-process campaign. Shift to **E003 SOFTWARE secondary quantized wide-BVH traversal**: prior B0 found ~**25.5–26.3 child AABB tests per actual ray**, ~6.7–7 wide node pops, only ~3.4 spatial-hash probes and ~2.6 DDA cells. The E003 path is independent of N003 primary/any-hit shadow. Or investigate N003 conditional shadow-ray regimes (light 9,797 actual rays; static/deforming 251 but long >60 nodes/ray; camera/moving 0) with separate controls. Freeze a new experiment protocol before changing algorithms.
6. **Continue updating docs, results, Issue #42 and push research commits directly** as work proceeds; minimize redundant interactive handoffs and stop only at necessary actual user GPU execution, scientific final acceptance/rejection or actual unsupported access.

**Priority B — eventual larger research objective:** once HWRT-free Software is materially improved, reassess N006 predictive marginal-value allocation P1/P2. Existing sparse-hash+GPU visibility RC and HWRT acceleration remain accepted baselines; don't claim “HWRT obsolete” on single GPU or without hardware-absent test and dynamic/churn validation. Research as a whole **is NOT complete**.

## 5. Source map / reproducible paths

- Protocol: `research/lanes/n006-interval-aware-allocation/experiments/016-p1l-b1-primary-near-first-traversal.md` (frozen B1a performance), `experiments/017-p1l-b1b-near-first-pruning-attribution.md` (frozen B1b diagnostic).
- Accepted results: `results/019-p1l-a1b-hwrt-software-stage-isolation.md` (primary/secondary/composite GPU stage gaps), `results/020-p1l-b0-two-case-software-count-smoke.md`, `results/021-p1l-b0-five-scene-software-work-counts.md`, `results/022-p1l-b1a-five-scene-preflight.md`, `results/023-p1l-b1a-matched-near-first-reject.md`, **`results/024-p1l-b1b-five-scene-near-first-work-reduction.md`**.
- Source: `src/research/n006_interval_aware_allocation/n006_runtime.cpp`, `n006_runtime.hpp`, `n006_intervention_main.cpp`; `src/research/lane_n_end_to_end_renderer/n001_runtime.cpp` / `CMakeLists.txt`.
- Original baseline shader: `shaders/research/lane_n_end_to_end_renderer/n003_primary_software.comp.glsl`; rejected candidate shader: `shaders/research/n006_interval_aware_allocation/n006_p1l_b1_primary_near_first.comp.glsl`.
- Accepted count-only probes: `shaders/research/n006_interval_aware_allocation/n006_p1l_primary_count.comp.glsl`, `n006_p1l_b1b_primary_near_first_count.comp.glsl`; runtime `N006Runtime::p1l_b1b_work_counts()`; one-step local runner `scripts/research/n006_interval_aware_allocation/run_p1l_b1b_verified.sh` (already passed as represented by user-uploaded B1b complete JSON).
- Separate E003 software traversal: `shaders/research/lane_n_end_to_end_renderer/imported/lane_e_dynamic_geometry/e003_instance_quantized.comp.glsl`. **Do not confuse E003 secondary with N003 primary/shadow, or generic I001 binary BVH**.
- GitHub issue: [#42](https://github.com/owoDra/phos-gi-lab/issues/42). Prior exact measurement source `n006-p1l-b1b-counts-summary.json` attached in this ChatGPT session; report SHA above; re-upload only if raw per-pixel data beyond the committed summary is truly needed.

## 6. Copy into a new ChatGPT session

> [$github] `owoDra/phos-gi-lab` の `research-n006-interval-aware-allocation` を最新取得して、`research/lanes/n006-interval-aware-allocation/HANDOFF_NEXT_SESSION.md` を最初に読み、Issue #42、results/023 と results/024 を確認してください。B1b は全5シーンPASSで、近距離優先によりBVHノード訪問は2.2–5.9%、三角形判定は6.5–31.4%減った一方、180組のGPU比較でB1aはREJECTのままです。原因を未確定として、まずB1cの命令/追加子ノード読込の静的分析から始め、実験プロトコルを固定して継続してください。可能なGitHub作業は途中でいちいち止めず、PR・GitHub Actionsを作らず研究ブランチへ直接pushしてください。実機GPUが必要な時だけ一括実行コマンドを提示してください。
