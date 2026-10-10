# N006 P1l-C0 — E003 quantized wide-BVH child cost audit (prospectively frozen)

Issue #42; 2026-10-11. **Measurement-first SOFTWARE secondary traversal investigation**, separate from N003 primary and shadow. This is a diagnostic plan; **no E003 speedup claimed**. Freeze this before writing any alternate E003 shader or inspecting its new GPU timings.

## Motivation and baseline

- B1a near-first was GPU REJECT despite B1b work-count reductions; B1c packed-axis was GPU REJECT (result 025, 1/5 primary scene wins and light renderer regression). **Stop new primary child-order variants**.
- Existing B0 five-scene E003 secondary baseline passed bit-exact image and GPU-hit checks. It performed **25.53–26.30 quantized child AABB tests/ray**, **6.72–7.00 wide node pops/ray**, only **3.41–3.44 segment hash probes/ray** and **2.59–2.63 grid DDA cells/ray**. Raw operation counts do NOT establish shader time cost.
- Accepted shader `e003_instance_quantized.comp.glsl` has eight-child loop, each valid child decoded from packed quantized bounds then evaluated via `ray_aabb_bounds` three-axis slab test, which uses `(bound-origin)/direction` per nonparallel axis and returns `enter` for stack pruning. Sign-dependent child order already exists. Candidate must NOT silently change interval, quantization rounding, hit tolerances, stack semantics or early exit.

## C0 — static audit first (no new GPU experiment)

1. On the **actual build artifacts**, record hash/byte size/SPIR-V opcode histograms and compiler/version/configuration for original E003 and N006 B0 E003 count-only instrumentation. Detect and record `OpFDiv`, `OpFMul`, `OpLoad`, control flow, vector math and accesses; static counts are **not dynamic execution** and `OpLoad` is not physical SSBO transaction count.
2. Inspect child packing, invalid slot handling and actual std430 node stride from shader/C++ `B003GpuQuantNode`, including dynamic rigid/deforming refit/rebuild and uploads. Establish current common-subexpression hoisting of ray reciprocals only if **compiler artifacts actually support it**; if ambiguous, report unknown rather than guess.
3. Identify *one* falsifiable low-overhead optimization, with no per-ray extra allocation or extra per-frame global rebuild. Recommended hypothesis if compiler lacks equivalent optimization: move nonparallel direction reciprocal out of per-child loop **without changing original division semantics unless exact equality can be re-proved**. If compiler already removes redundant division, **NO-GO** on reciprocal caching and choose another measured hotspot rather than writing a pointless variant.
4. Offline audit should be executable on the user's configured shader build without requiring physical GPU. Keep source/binary SHA, CMake flags and limitations. No target GPU data were supplied for C0.

## Conditional C1 only if C0 yields a real opportunity

- Freeze a separate candidate shader/protocol **before implementation**. Use N006 opt-in shader and bindings only, not accepted E003. Use exactly the same five Sponza Lane-E-final Software scenarios, 32+8 warmups, N004 CPU hit oracle (sampled on candidate), strict accepted PFM SHA per frame, byte-exact E003 hit and canonical owner/ray/hash/stage closure, zero overflows. Detect and **fail** on numerical divergence; do not redefine tolerance/acceptance after seeing results.
- Mandatory independent light + moving-rigid smoke first. Bound 600s per process. Only on all 5 preflight correctness PASS use independently repeated, counterbalanced 24-frame A/B, report secondary GPU timestamp **and** full-renderer GPU timestamp plus CPU build/update/memory. Predeclare ≥5% secondary paired median improvement, ≥24/36 faster pairs and ≥2/3 winning process medians for ≥3/5 scenes, all scenes complete renderer ≤+3% regression; negative and dynamic scenes retained.
- If no credible static opportunity: record C0 NO-GO without new GPU campaign. Next alternative remains conditional N003 shadow-ray hotspots, not hashes by default.

**Status: protocol frozen, C0 audit not yet executed on configured binaries, C1 unimplemented, no new GPU evidence.** Original Issue #42 predictive marginal-value ray allocation P1/P2 separately gated.
