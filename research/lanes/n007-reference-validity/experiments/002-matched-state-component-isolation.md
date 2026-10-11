# N007 P1-A — matched-state component isolation (preregistered design, not yet executed)

**Status:** planned; **no new render or GPU capture in this phase**. Bounded follow-up to [full P0 survey](../results/006-p0-complete-archive-image-survey.md) and [N007 eligibility protocol 001](001-reference-eligibility-protocol.md). This addendum **does not change the original N001/N006 sources, historical classifications, fixed seeds, SPP ladder, signal thresholds, or scope**.

## P0-derived question (do not conflate observables)

The archived 338/338 pair survey finds 96 black-reference/GPU-positive rows but only 4 unique GPU/ref SHA pairs; all four share the **same** all-black CPU reference SHA. They appear in camera-motion/camera-disocclusion and moving-rigid, whereas N001 light-motion and N006 M3c deforming have nonzero reference signal. The old CPU global p99 passes when the active fraction is <1%, even if stochastic noise or bias persists. The root cause is **not established**: nonzero GPU need not mean physical light, and black CPU need not mean a false reference.

GitHub source-level contrast to test, *not* a verdict:
- CPU `n001_reference.cpp` traces fixed center-primary and independently seeded secondary Lambert rays; checks a BVH shadow ray from **each bounce hit** to point light.
- N006 software `n003_composite_software.comp.glsl` and original HWRT `n001_composite.comp.glsl` check **primary direct** shadows, then add gathered `lookup_probe` indirect.
- `n001_physical_radiance.comp.glsl` probe-hit Lambert does **not** check secondary shadow rays to point light. This can create unshadowed probe energy, but the per-pixel contribution to four observed GPU images is unknown.
- `n001_runtime.cpp::renderer_readback()` uses target CPU triangle data after dynamic geometry update; don't assume stale geometry.

## Ordered tests and strict stop conditions

### A0 — CPU-only archived evidence / source static checks

1. Keep all archived PFMs private and unchanged. For a representative **black moving-rigid**, **black camera**, **positive light-motion** control and **sparse M3c** contrast, resolve original evidence and state fingerprints (scene hash, geometry state, camera/light parameters, frame index, shading algorithm and seed/SPP metadata); **absent fingerprints are unknown, never manufactured**. SHA and naming alone cannot prove matched states or independent seeds.
2. Check whether original evidence contains separately stored primary-hit, direct-only or indirect-only PFM payloads. If present, inspect them read-only before any new rendering. If absent, stop A0 as *not identifiable from archived final PFM alone*; do not infer `GPU-only positive = indirect` from a total image.
3. Validate image identities for N001 camera, N001 moving-rigid and N006 M3b by hashes and filenames, and record distinct artefact signatures rather than repeated campaign counts.
4. Use a zero-reference mask as **missing/no-support** rather than conditional-zero error; preserve whole-frame mismatch separately. Do not classify radiance as physically invalid using arbitrary `1e-4` alone.

### A1 — diagnostic-only minimal matched-state capture (separate N007 implementation; GPU/CPU as needed)

Pre-register exactly **one representative black-state moving-rigid**, **one representative black-state camera** (or camera-disocclusion), **one positive light-motion reference** and **one deterministic controlled occlusion scene**. This is a causal diagnostic, not a comparative renderer optimization. No post-hoc frame substitutions, seed tuning, N006 Q8 intervention reruns, historical shader changes, or parameter sweeps.

For each selected cell, freeze/record:
- SHA256 scene asset bytes, source commit, scene/triangle state hash **after motion**, primitive count and identities, frame ID, 320×180 dimensions, camera basis/near/far, light position/radius, traversal flags, and all references' 4 seed IDs.
- CPU and GPU *primary-hit* IDs/masks/distance plus geometric normal for matched pixel centers.
- CPU **direct-first-bounce** (shadow-tested) and **secondary-bounce** energy as separate **linear float32** images; GPU **shadow-tested primary direct**, **probe indirect**, and total as separate float32 images. Preserve exact GPU total reconstruction equality within documented rounding bounds. No exposure/tone-mapping.
- CPU per-bounce primary hit counts, positive contribution counts, shadow-tested blocked/unblocked counts, secondary hits, source RNG/seed/SPP evidence. Instrumentation output must not alter original N001 production acceptance path.

Stop/fail closed (retain diagnostic even if it fails):
- If input/frame/geometry hashes or primary-hit semantics diverge, **do not use total-image error** to assign shadow/indirect cause.
- If CPU/GPU primary masks and direct terms agree but GPU probe indirect is positive where CPU indirect is zero, target **probe shadow/transport model** for independent occlusion-controlled validation; don't automatically delete the GPU term.
- If CPU primary and GPU primary disagree, isolate geometry/tie-break/face orientation/near/far or traversal *before* studying probe lighting.
- If both primary direct and indirect are zero in CPU for all seeds/SPP, test deterministic occlusion scene with known visibility before calling the all-black CPU frame correct.
- If direct and indirect components match but total differs, isolate reconstruction, Q8 packing/storage or output conversion.
- No signal below minimal detection warrants a new shader heuristic or performance claim without an independently validated physical reference.

### A2 — reference statistical eligibility (existing protocol unchanged)

Use the [preregistered N007 P1 ladder](001-reference-eligibility-protocol.md): `512, 1024, 2048, 4096, 8192` spp × four fixed independent seeds, with two consecutive eligible steps to qualify. If no nontrivial eligible reference by 8192, classify that cell **ineligible**, stop, and preserve negatives. Statistical eligibility is independent of transport correctness; test known direct/occluded cases for physical sanity.

## Outputs / independent review

New N007-specific output directory under `out/research/n007-reference-validity/`, with private per-frame PFM/geometry/state manifest and compact derived public JSON/Markdown. **Never upload old private assets or original PFM to GitHub by default.** A physically valid and statistically eligible reference would authorize a separate future GI quality study, **not N006 P1/P2 resurrection**. Issue #4 remains open until required cells qualify or bounded failures are documented.

**No CI, no PR, no changes to `main`.**
