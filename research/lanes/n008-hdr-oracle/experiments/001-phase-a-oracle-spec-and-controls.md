# N008 Phase A — independent CPU HDR oracle: transport specification and physically known controls (preregistration)

**Status:** PREREGISTERED 2026-10-13 before any oracle image was produced. Study: [Issue #5](https://github.com/owoDra/real-time-gi-lab/issues/5). Branch: `research-n008-hdr-oracle` (from `research` @ `73d8194`).
**Scope:** CPU-only. No GPU run, no Renderer/candidate image, no N001–N007 file is modified. N007 bounded NO GO and N006 P1 NO GO stay frozen; nothing here rescores them.

## A0 — audit of reference integrators and selection

| Candidate | Independent of N001? | Availability in assistant sandbox | Role |
|---|---|---|---|
| N001 `n001_reference.cpp` (+ Lane B `SoftwareBvh`) | **No** (object under scrutiny) | source | audited only; *never* used as truth |
| PBRT-v4 | yes | needs source build (CUDA optional) | not selected (build cost, no added coverage over Mitsuba for diffuse/point/area) |
| Mitsuba 3.6.4 (`scalar_rgb`, PyPI wheel, BSD-3) | yes, separately maintained | `pip install mitsuba==3.6.4` works, CPU-only | **selected cross-check integrator** |
| New N008 oracle (this study) | yes: new code, own watertight intersector, own BVH, own RNG, double precision | build with any C++20 compiler | **selected oracle** (fast, auditable, emits direct/indirect/variance + geometry hash) |

Rationale: the oracle must eventually ingest frozen Renderer world-space triangle snapshots (Phase B, ~262k Sponza triangles) and emit per-component/variance data that Mitsuba does not provide out of the box. Its correctness is established **only** by (1) analytic/deterministic controls computed by separate Python code from closed forms or quadrature and (2) statistical agreement with Mitsuba on identical triangle meshes. GPU/RC output is never a reference for Phase A.

N001 audit findings carried into this specification (source facts, `n001_reference.cpp`): falloff `s²/(s²+d²)` instead of inverse square, implicit white albedo 1, no emitters/environment, primary rays at pixel centres only, **secondary rays truncated at camera `far`**, normal face-forwarded, Lane B float32 BVH. These are recorded as *declared compatibility switches*, not as physical truth.

## Transport specification (oracle v1)

- **Quantity:** scene-linear radiance, RGB with three independent channels interpreted as linear Rec.709; no exposure, tone map, clamp or spectral conversion. Output float32 PFM (bottom-up rows per PFM spec, little-endian scale `-1`), top-left image origin after decoding, plus a raw float64 sidecar for exact checks.
- **Units:** lengths in scene units (metres nominal); radiance W·sr⁻¹·m⁻²; point-light radiant intensity `I` W·sr⁻¹; emitter radiance `Le`.
- **Lights:** (i) isotropic point light, irradiance `E = I·max(0,cosθ)/d²` (`falloff inverse_square`, physical default); compatibility switch `falloff n001_soft s`: `E = I·cosθ/(s²+d²)`, N001 corresponds to `I = s²`, `ρ = 1`. (ii) Emissive triangles: one-sided emission on the front face (`n = normalize((v1−v0)×(v2−v0))`), constant `Le`, sampled by next-event estimation proportional to area. Background/environment is black.
- **BSDF:** Lambertian `f = ρ/π`, per-channel `ρ ∈ [0,1]`. Material flag `two_sided` (default 1): the shading normal is the geometric normal face-forwarded toward the incoming ray. `two_sided 0`: a back-face hit absorbs (contributes 0, path terminates). All triangles occlude regardless of side (no culling in visibility).
- **Estimator:** path tracing with NEE at every surface vertex; `max_bounces D` = number of surface vertices at which NEE is evaluated (`D=1` direct only). Emission is added only when a camera ray hits an emitter front face (component `emission`); later BSDF-sampled emitter hits add nothing (no double counting). Cosine-weighted hemisphere sampling, so `f·cos/pdf = ρ`. No Russian roulette in v1 (truncation is exact and declared). Components: `emission`, `direct` (NEE at vertex 0), `indirect` (NEE at vertices 1…D−1); `total = emission + direct + indirect` exactly per sample.
- **Camera:** pinhole; world is right-handed; `right = normalize(forward × up)`, `up' = right × forward`; pixel `(x,y)` with `y` downward, `nx = 2(x+u)/W − 1`, `ny = 1 − 2(y+v)/H`, `dir = normalize(forward + right·nx·tanX + up'·ny·tanY)`. `sampling center` uses `u=v=0.5` (N001-compatible); `sampling box` uses uniform jitter (box filter). Primary ray `t ∈ (near, far]`. **Secondary and shadow rays have unbounded length** (`secondary_far inf`); compatibility switch `secondary_far camera` reproduces N001 truncation.
- **Ray offsets and ties:** double-precision watertight intersection (Woop/Benthin/Wald 2013) with `t > 0`; the originating triangle is excluded; hit points within `1e-11 × scene diagonal` of their triangle boundary are moved toward the triangle centroid (Amendment 2); origins are offset by `1e-12 × scene diagonal` (Amendment 1) along the face-forwarded geometric normal; shadow rays test `t < d·(1−1e-12) − offset`. Closest hit ties resolve to the lower triangle index.
- **RNG/seeds:** xoshiro256** per (seed, pixel, sample) stream initialised by SplitMix64; four fixed N007 seeds `305419896, 2596069104, 81985529216486895, 18364758544493064720`. Per-pixel variance is estimated from per-sample first and second moments pooled across seeds.
- **Provenance:** the oracle prints SHA-256 of its parsed canonical world-space triangle array (float64 little-endian vertices + uint32 material ids) so the Python generator can confirm that exactly the frozen geometry was loaded; scene-file SHA-256 is recorded separately.

## Controls (expected values computed independently in Python from closed forms/quadrature)

Common: 128×96 pixels unless stated. Deterministic checks use `sampling center`. "Exact" means float32-PFM relative error ≤ **1e-6** and float64-sidecar relative error ≤ **1e-9**; "zero" means exactly `0.0` in every component. Pixels whose analytic classification lies within **1e-6** scene units (or 1e-9 parametric) of a geometric boundary are excluded as *margin* and counted; if margin pixels exceed **5%** of tested pixels the control fails.

| ID | Control | Expected (independent) | Gate |
|---|---|---|---|
| A1 | Camera/handedness: two front-facing emitters (right-upper, left-lower) and one back-facing emitter | analytic projected coverage; `Le` exact inside, zero elsewhere, back-facing emitter zero | exact/zero, coverage mismatch 0 |
| A2 | Lit vs geometrically occluded floor; coloured ρ=(0.8,0.5,0.2), black occluder, point light, D=8 | `ρ/π·I·cos/d²` lit, 0 in shadow; indirect identically 0 (planar floor + black occluder) | exact/zero; lit pixels strictly >0 |
| A2b | Same, `falloff n001_soft s=1.5` | `ρ/π·I·cos/(s²+d²)` | exact/zero |
| A3 | Area light: square emitter above floor, D=1 and D=8 | closed-form point-to-parallel-rectangle irradiance `π·Le·F` (corner superposition) | statistical (S) with τ=1e-6 |
| A4 | Backface/two-sided/culling: (a) two-sided sheet seen from lit side, (b) from unlit side, (c) one-sided sheet seen from its back, (d) back-facing one-sided occluder must still shadow | (a) analytic, (b)(c) zero, (d) analytic shadow | exact/zero |
| A5 | Empty/dark: (a) no geometry, (b) no light, (c) zero intensity, (d) light sealed in closed box, camera outside, (e) camera inside the same box | (a–d) zero for all samples/bounces; (e) every pixel direct >0 | zero; strict positivity |
| A6 | Sphere furnace (icosphere level 6, R=1, inside view): (a) ρ=0.5, centred light, D=8; (b) ρ=(0.9,0.6,0.3), off-centre light, D=8; (c) as (b) with D=2 (two-bounce) | indirect radiance `= I/(πR²)·Σ_{k=1}^{D−1} ρ^{k+1}` (constant: sphere kernel `cosθx·cosθy/r² = 1/(4R²)`); direct `ρ/π·I·cos/d²` of true sphere | S with geometric allowance (below) |
| A7 | Two-bounce non-symmetric: coloured floor + coloured ceiling, point light between, D=2 | direct analytic; indirect = 2-D Gauss–Legendre quadrature of `ρ_x/π ∫ L_direct(y) cosθx cosθy / r² dA` (order doubling must agree to 1e-8 rel.) | exact direct, S indirect, τ=1e-6 |
| A8 | Moving rigid at frozen target pose: rotated+translated black cube over floor | target-pose analytic shadow (ray vs oriented box); oracle geometry hash equals Python hash of frozen snapshot; **rest-pose render must fail the target expectation in ≥1% of tested pixels** | exact/zero + hash match + stale-geometry detector |
| A9 | No-leak rooms: (a) two sealed rooms sharing a zero-thickness partition with split floor/ceiling (shared edges), light in room 1, camera in room 2; (b) camera in room 1; (c) single room with occluding pillar | (a) zero for every sample; (b) every pixel >0; (c) shadowed pixels direct exactly 0 **and** indirect strictly >0; lit pixels direct exact | zero/positivity/exact |
| A10 | Upper-distance culling: A6b with camera `far=1.6` (all primary hits ≤1.5, secondary paths need up to 2.0) | same as A6b | S as A6 |

**Statistical gate (S):** per region and channel `|m − e| ≤ 5·SE + τ·|e|`, and per pixel `|m − e| ≤ 6·SE_pix + τ·|e|` for ≥ **99.9%** of tested pixels, using 4 seeds × 1024 spp with `sampling center`, so every expected value is evaluated at the pixel-centre hit point. Zero-for-every-sample controls A5d and A9a additionally run with `sampling box` (4 seeds × 1024 spp) to widen geometric coverage of leak paths. For A6/A10, τ for indirect is **2e-3** (polyhedral sphere vs analytic sphere); direct per-pixel allowance is the geometric bound `ρ/π·I·(δ_n/d² + 2·Δd/d³)` with facet-normal deviation `δ_n` and sagitta-derived `Δd` measured from the generated mesh before rendering. Level-5 vs level-6 indirect is reported as a diagnostic only.

## Independent integrator cross-check (Mitsuba 3.6.4 `scalar_rgb`, identical triangle meshes)

Mitsuba scenes are built from the same frozen triangles: `twosided(diffuse)` (or bare `diffuse` for one-sided), `point` intensity, `area` emitters with `Le`, `perspective` sensor via `look_at` with x-FOV `2·atan(tanX)`, `box` reconstruction filter, `independent` sampler, `path` integrator with `max_depth = D+1`, `rr_depth = D+2` (no Russian roulette), `hide_emitters=false`. 16 seeds (0…15) × 256 spp. Cells: **X1**=A1, **X2**=A2 (box), **X3**=A3 D=8, **X4**=A6b (same mesh), **X5**=A7 D=2 and D=8, **X6**=coloured closed room with area light and pillar (Cornell-like, no closed form).
Gate per cell: whole-image and per-channel means `|m_o − m_m| ≤ 5·sqrt(SE_o² + SE_m²) + 1e-3·|m_m|`; per pixel `|z| ≤ 6` for ≥ **99.9%** of pixels where either image is nonzero, with `z = Δ/sqrt(se_o² + se_m² + (1e-3·m_m)²)`. Mitsuba is float32; exact-zero disagreements are reported, not gated. Diagnostic only (not gated): A6b against Mitsuba's analytic `sphere` shape.

## Development, freeze and stop rules

- Tolerances, scenes, seeds and spp above are frozen by this commit. Implementation bugs found while bringing up the oracle may be fixed; **every failing run and fix is logged** in the Phase A result. Expected values may not be fitted to oracle output; a failing control can only pass after a documented oracle bug fix or a documented error in the independent expected-value code, never by changing a gate.
- **Exit A (GO to Phase B):** all A1–A10 and X1–X6 pass in one final frozen run from a single committed source SHA, with retained JSON evidence.
- **NO GO:** any control still failing after its root cause is documented without a code-level oracle defect to fix, or the cross-check cannot be made to run; retain negative artifacts and do not start GPU work.
- Compact JSON summaries go to `research/lanes/n008-hdr-oracle/results/`; PFMs stay in ignored `out/research/n008-hdr-oracle/`.

## Amendments (pre-data)

1. **2026-10-13, before any control scene was rendered:** ray-origin offset changed from `1e-9` to `1e-12 × scene diagonal`. Reason (analysis, not data): an offset `ε` biases point-light direct radiance by up to `≈2ε/d` relative, i.e. ~7e-9 for the A2 geometry, which would itself violate the preregistered 1e-9 float64 "exact" gate. `1e-12 × diagonal` still exceeds double hit-point rounding (~1e-15 × coordinate magnitude) by >10³, and the originating triangle is excluded by id. No gate, scene, seed or spp changed.
2. **2026-10-13, after a development run (post-data, disclosed):** the first A5 development run failed `A5e:every_pixel_direct>0` on 4/12,288 pixels (and total = 0 there). Diagnosis: those pixel-centre rays hit exactly a concave box edge (|dx| = |dy|); offsetting along the hit face normal leaves the origin on the adjacent face's plane, so rounding produced spurious `t ≈ +0` self-occlusion of both NEE and continuation rays (an oracle implementation defect, also a potential seam leak for A9a). Fix: hit points within `1e-11 × scene diagonal` of their own triangle boundary are moved toward the centroid so the origin lies strictly on the room side of every adjacent face. The bias bound (`≈2·1e-11·diag/d`) stays below the 1e-9 exact gate. No gate, scene, seed, spp or expected-value code changed; the failing run is kept in the result log.
