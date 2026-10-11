# N007 P0/P1 — prospective reference eligibility calibration v1

Status: **P0 source audit + CPU diagnostic implemented; physical correctness and P1 GPU calibration NOT evaluated.** Study: [Issue #4](https://github.com/owoDra/real-time-gi-lab/issues/4). No N006 experiment reopening. Original historical records and classifications are immutable.

## Retained historical inputs (not remeasured)

- N001 original 320×180 Sponza scene SHA256 `2a86fdc2dc92d7c6a740682c61ec97f3101f489a06443c6823aff85bb990e5f6`; static CPU signal fraction 0.002778, camera CPU 0, light CPU 0.165729, moving-rigid CPU 0 (see Lane N result 001).
- N006 M3b result 043: two independently seeded CPU references byte-identical; exact brightness and PFM SHA still unknown without retained `Q8_control_reference` files. Do not call them black by inference.
- N006 M3c result 045: 161–169 positive reference pixels / 57,600, whole-frame p99 0, inter-reference RGB RMS 6.328440285901378e-8. Prior N006 P1 NO GO retained.

## P0 code-level findings (hypotheses distinguished)

1. `n001_reference.cpp`: primary rays pass through pixel centers, deterministic across samples/seeds. Random draws are used **only after** a primary hit, for diffuse-bounce direction. Thus independent seeds do not establish subpixel independent samples, and exactly identical float32 references can reflect deterministic first-hit/direct-light transport or no successful secondary paths; not by itself an RNG wiring failure.
2. The CPU path tracer uses up to 8 Lambert bounces, cosine hemisphere sampling, throughput `f*cos/pdf=1`, and direct point-light next-event evaluation at each hit. It has **no** environment term, emitter surface transport, Russian roulette, primary-ray jitter or material albedo/color. Its direct-light shadow ray calls `SoftwareBvh::trace`. Finite depth and camera far are model limitations; not an unbiased full-scene physical oracle.
3. GPU `n001_composite.comp.glsl` adds primary direct (with visibility query) plus cascade probe radiance; `n001_physical_radiance.comp.glsl` computes probe-hit point-light Lambert **without an equivalent shadow-to-light test**. Hence the GPU and CPU do not implement identical light transport/occlusion at secondary surfaces. This provides a concrete leakage mechanism, but does **not** establish which one caused any particular black/nonblack frame without isolating the GPU direct/indirect components and matching world states.
4. The N001 two-replicate stop uses whole-frame p99 abs ≤0.001 and relative ≤0.01, which can both be zero with <1% active pixels. `n001_contract.py` verifies finiteness but not nonnegativity of read PFMs. The original N001 campaign-level signal rule permits individual black frames (preserve that original acceptance; N007 adds a *separate quality-eligibility* concept).
5. Exact camera, light, object motion, CPU triangle snapshot, ray-tie/culling semantics, and float32 quantization remain independent hypotheses until fresh, aligned evidence exists. Do not retrospectively attribute observed black CPU images to GPU light leaks alone.

## Prospective image diagnostics (no scene/candidate selection from observations)

- Inputs are RGB PFM, top-left after PFM bottom-up decoding, linear Rec.709, no exposure, no tone mapping; read raw SHA256, dimensions and PFM scale. Reject malformed, nonfinite, negative-channel images from eligibility; report rather than silently clip.
- Compute every reference's positive-luminance pixel count/fraction, max/mean luminance, completely-black flag; detect raw-byte **and float-pixel equality**. Report pairwise full-image RGB RMS and pairwise absolute p99.
- The **active mask is the union** of all independent reference pixels with `Y>0`, frozen before inspecting renderer candidates. Report active-mask p99 absolute and floor-aware relative (`max(1e-4, mean absolute reference Y)`) and maximum, plus whole-frame RGB RMS. Do **not** remove reference-dark pixels from whole-frame metrics; count GPU-only positives explicitly.
- For N007's conservative, *provisional* calibration eligibility, require ≥4 independently seeded references, ≥64 union-active pixels and ≥1% active fraction, peak reference Y≥1e-4, pairwise image-value inequality, and all pairs active p99 abs≤1e-5 and rel≤5%. These are **screening limits pending calibration**, not a scientifically established physical-accuracy guarantee or a retroactive criterion for N001/N006. Especially, legitimate sparse scenes may be marked ineligible for this specific statistical screen without being labeled physically wrong.
- Purely deterministic direct-only radiance can make correct replicates equal: this classifier conservatively marks them ineligible for a *stochastic noise estimate*, NOT erroneous physics. Require a separately validated deterministic oracle to qualify such a scene.

## P1 acquisition (DO NOT CLAIM EXECUTED)

Before the first new GPU/scene-state capture, archive a manifest with source commit and reproducible configuration, including: static, camera-motion, light-motion, moving-rigid, stable-topology deforming, topology churn, and an independent simple non-Sponza occlusion/area-light test; retain both lit and occluded pixels. Use N001 original scene SHA for Sponza; record **new geometry and trajectory hashes before capture**, never choose favorable frames after rendering. For each preregistered cell use spp `512/1024/2048/4096/8192` and four mutually distinct 64-bit fixed seeds (decimal): `305419896`, `2596069104`, `81985529216486895`, `18364758544493064720`. At each spp save **four independent per-seed PFMs**, not only two-seed averaged output, plus GPU direct-only, indirect-only and total, primary ray hit IDs/t coordinates, CPU triangle/world transform manifest, light parameters and readback state fingerprints. N001 historical contract must stay unchanged; implement a new N007 export path if required.

Analyze each spp independently with the exact N007 diagnostic. Compare convergence at successive spp and independent 4-seed pairwise noise range; include pixel-class counts and report the whole-frame metric. Qualify only after **two consecutive spp levels** pass the same active-mask screening with stable signal support; if 8192 spp fails, mark reference statistically ineligible for that cell, preserve all images and stop increasing samples in this campaign. Independently validate physical semantics with simple known visibility/occlusion cases and compare direct-only versus indirect-only. A statistical PASS never substitutes for that correctness test.

Resource stop: at most 5 spp levels ×4 reference replicates per preregistered cell, no ad-hoc higher spp, seed replacement, frame substitution, scene selection or N006 candidate work. Before GPU acquisition, verify exact source/head and frame hash, and ensure CPU reference settings permit exporting fixed-spp per-seed PFMs. GPU-timestamp performance is not an N007 acceptance axis; CPU time is diagnostic only.

## Result classification

- `statistically_eligible` = only basic signal, independent replicate and pairwise stability screening; **never** asserts physical correctness.
- `physically_valid` requires independently verified transport definition and scene-state matches, direct/shadow/indirect tests with retained images; status currently **unknown**.
- `ineligible` for black, low-signal, identical sampled replicates, invalid numeric values or noisy active support: retain observation and investigate rather than hiding it.
- N007 is complete only after the required real-frame/geometry classes meet the preregistered criteria or have documented failures and an explicit bounded limitation decision.
