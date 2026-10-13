# N008 Phase A — independent CPU HDR oracle: physical controls PASS, Exit A = GO (bounded)

**Date:** 2026-10-13 JST · **Issue:** [#5](https://github.com/owoDra/real-time-gi-lab/issues/5) · **Protocol:** [experiments/001](../experiments/001-phase-a-oracle-spec-and-controls.md) (preregistered `d9e51e3`, Amendment 1 `7e79fc3` pre-data, Amendment 2 `c7d441b` post-data disclosed)
**Frozen run source:** `c7d441b269ca5826e934c6ba0d2bdcc283b7e440`, clean tree (`source_dirty=false`), clean rebuild of `build/n008`, GCC 15.2, `-fno-fast-math -ffp-contract=off`, Python 3.13.13, numpy 2.5.4, Mitsuba 3.6.4 / Dr.Jit 1.0.5 `scalar_rgb`.
**Executed by:** the assistant in its CPU sandbox (no GPU, no user action). Raw PFM/sidecars in ignored `out/research/n008-hdr-oracle/final-c7d441b/`.

## Outcome

| Gate | Result | Evidence |
|---|---|---|
| C++ unit tests (SHA-256 vectors, RNG, watertight shared edges 200k rays, BVH == brute force 20k rays, cosine-sampling moments, PFM layout, parser rejects) | **17/17 PASS** | console in `out/` |
| Python expected-value unit tests (closed-form rectangle form factor vs quadrature, camera handedness, OBB, icosphere, hash/sidecar parity with the oracle) | **7/7 PASS** | `test_n008lib.py` |
| A1–A10 physically known controls (102 checks, 28 oracle runs, every run's geometry SHA-256 re-derived in Python) | **11/11 PASS** | [001-phase-a-controls.json](001-phase-a-controls.json) |
| X1–X6 Mitsuba 3.6.4 cross-check on identical meshes (7 gated cells) | **7/7 PASS** | [002-phase-a-mitsuba-crosscheck.json](002-phase-a-mitsuba-crosscheck.json) |
| Sensitivity (post-hoc, not a gate): 5 injected transport defects | **5/5 detected** | [003-phase-a-sensitivity-diagnostics.json](003-phase-a-sensitivity-diagnostics.json) |

**Exit A (preregistered): GO to Phase B.** Independent physically known light and shadow controls pass, and an independently maintained integrator agrees on identical geometry.

### Key observations (all from the frozen run)

- **Exact controls** (A1, A2, A2b, A4, A8, plus direct terms of A7/A9c): zero float64-sidecar and zero float32-PFM violations of the 1e-9 / 1e-6 relative gates. Shadowed pixels are exactly `0.0`, and lit pixels are strictly positive. In A2, the RGB channel ratio equals the albedo ratio to 1e-9. The margin-excluded pixel fraction was 0 in every control.
- **Zero-for-every-sample controls:** no geometry, no light, zero intensity, light sealed in a closed box (camera outside), and room 2 behind a zero-thickness shared-edge partition (A9a). These ran with centre and box sampling at 4 seeds × 1024 spp × 8 bounces, and gave first and second moments that were exactly zero in all components.
- **Strict positivity:** inside the sealed box (A5e) and the lit room (A9b), every pixel has direct > 0. In A9c, all 593 pillar-shadowed pixels have direct exactly 0 and indirect > 0 (light reaches the shadow only through bounces, not leaks).
- **Multi-bounce analytic furnace** (82k-triangle icosphere, off-centre light, coloured ρ = (0.9, 0.6, 0.3)): indirect region error is 0.85–1.02e-4 relative against `I/(πR²)·Σρ^{k+1}`. This is consistent with the tessellation bias, which shrinks from 3.6–5.0e-4 at level 5 to 0.85–1.0e-4 at level 6 (≈4×, O(h²)). The two-bounce (D=2) variant and the far-culling variant (camera far 1.6, secondary paths up to 2.0) pass identically.
- **Non-symmetric two-bounce quadrature (A7):** the indirect region differs from Gauss–Legendre quadrature by 2.7e-4 relative, within the S bound; panel doubling changed the quadrature by 1.4e-15.
- **Area light units (A3):** direct differs from the closed-form `ρ·Le·F` by 2.4e-5 relative over 6,822 pixels.
- **Moving rigid frozen pose (A8):** the transformed-then-frozen cube and a cube directly authored at the target pose both match the analytic target shadow exactly. The stale rest-pose render is detected (mismatch fraction ≥ 1%). The oracle's loaded-geometry SHA-256 equals the Python-recomputed SHA-256 for every run.
- **Mitsuba agreement:** whole-image per-channel differences are 1.3e-5 to 1.6e-4 relative, and the per-pixel |z| ≤ 6 fraction is 1.00000 in every cell (max |z| 4.39). The diagnostic oracle-mesh vs Mitsuba analytic-sphere difference is 1.0–1.3e-4, matching the A6 tessellation bias.
- **Reported, not gated:** 0–12 pixel-channels per cell where one integrator is exactly 0 and the other is > 1e-6. All of them are silhouette pixels with values ≤ 3e-5, against image medians of 0.03–0.2: box-filter coverage sampling noise.
- **Sensitivity:** the frozen gates fail, as required, on the following injected defects:
  - N001-style secondary-ray truncation at camera far
  - N001 soft falloff judged against inverse-square physics
  - a 1 mm light displacement
  - a 0.5% albedo scale error in the two-bounce scene
  - one-sided versus two-sided wall semantics

  These were added after the preregistration, as a power demonstration, not a gate.

### Minimal detectable effect actually achieved (bound / expected)

| Gate family | Relative detectable error |
|---|---|
| Exact controls | 1e-9 (f64) / 1e-6 (PFM) per pixel |
| A3 area-light direct | 2.7e-4 |
| A7 two-bounce indirect | 2.8e-3 |
| A6/A10 furnace indirect (geometric allowance τ=2e-3 dominates) | 2.0–2.3e-3 |
| A6 direct with mesh-normal allowance | 1.2–1.3e-2 |
| Mitsuba image means | 1.1–1.9e-3 |

## Development log (complete; failures retained)

1. C++ watertight unit test failed with 8,359 misses. Cause: a **test fixture** defect (`sin(2π) ≠ 0`, so the closing fan vertex was not shared and a real crack existed). Fixed by indexing vertices modulo k. The oracle was unchanged.
2. **Amendment 1 (pre-data):** ray offset 1e-9 → 1e-12 × diagonal. The original value would by itself violate the 1e-9 exact gate.
3. First A5 development run: `A5e:every_pixel_direct>0` failed on **4 / 12,288** pixels. The pixel-centre rays hit a concave box edge exactly, and the normal offset left the origin on the adjacent plane, causing spurious self-occlusion. This was an **oracle defect**, fixed by **Amendment 2** (edge inset 1e-11 × diagonal), and disclosed as post-data. All other deterministic controls passed in the same development run both before and after the fix.
4. The cross-check parser had an off-by-one on the camera `far` field and crashed before rendering. No result was produced; fixed.
5. Scene builders for A1/A3/A7 were refactored into functions reused by the cross-check (identical parameters; verified by re-running).

No gate, scene, seed, spp or expected-value formula was changed after observing a control result.

## Scope and limitations (binding for later phases)

- **What is validated:**
  - Transport: Lambertian (per-channel RGB albedo), isotropic point lights (inverse-square, plus the declared `n001_soft` compatibility falloff), one-sided constant-radiance emissive triangles, and a black background.
  - Geometry and visibility: two-sided and one-sided surfaces, culling-free visibility, and watertight double-precision triangles.
  - Estimator and camera: fixed-depth path tracing up to D=8 with per-component decomposition, a pinhole camera with centre/box sampling, unbounded secondary rays (plus the `secondary_far camera` compatibility switch), and frozen world-space snapshots with geometry attestation.
- **Not validated:**
  - Textures and alpha-tested geometry. **Sponza contains alpha-masked foliage; Phase B must declare how these are represented.**
  - Glossy or specular BSDFs, environment lighting, Russian roulette, spectral rendering, motion blur, and participating media.
  - Very large coordinate magnitudes, and results on other CPUs or compilers.
- Validation is on small controlled scenes. Phase A does **not** establish anything about Sponza-scale convergence, the Renderer's transport definition, or N001–N007 results, and it **does not reopen N007/N006**. A statistical PASS on a real scene in Phase B remains a separate question from this physical validation.
- Mitsuba shares the path-tracing algorithm family; agreement shows independent-implementation consistency, not a proof of a different estimator class.

## Next (Phase B entry conditions)

Preregister, before rendering any Renderer scene, everything below:

- **Scope:**
  - the exact Renderer-equivalent transport mapping (falloff, albedo/texture policy, alpha, bounce depth, secondary distance);
  - the scenes, frames and classes;
  - the camera/light/geometry export path and its hashes.
- **Reference eligibility:**
  - reuse the N007 four seeds and the 512–8192 spp ladder;
  - stop rules;
  - **positive-support requirements**, so that a black reference cannot qualify.
