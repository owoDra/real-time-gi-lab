# N007 P0-004 — full M3b CPU-vs-Q8 original-image metrics (2026-10-12)

**Classification:** original artifact **diagnostic-only**; **reference-ineligible**, **no signed-quality label** and **no physical correctness** claim. Source is the original `p0-m3b-archive-diagnostic.json` **pasted by the user** after running the N007 offline inspector locally. The assistant did not have the preserved PFM files in its sandbox and did not reproduce their hashes independently. No GPU/CPU rendering was performed for this result.

## Fixed historical artifact provenance

- Archived old private root relative to new checkout: `../gi-lab-old-private`.
- Original capture relative to that root: `out/research/n006-interval-aware-allocation/p1m3b-moving-rigid-q8-signed/20261011T115843Z/Q8_control_reference`.
- Evidence JSON SHA-256: `be2d69baf1d2f0513192f02976ede69e5152dc51b22baad1daebdc741c9f6631`.
- Original invalid-retained M3b summary SHA-256: `1c251467f61b9bac777ca860f689c2903c55214cd4bb8ff9e2997b92e6cc98d6`; the local inspector explicitly reported `original_summary_verified=true`.
- **Both independent CPU references** `frames/reference-8bounce.pfm` and `frames/reference-8bounce-independent.pfm` have the exact same SHA-256 `7595a554e8cce3af07b1aa6a89521c803c12e8f70f2ed725ed74bba20220ea47`.
- Q8 GPU `frames/candidate-000.pfm` SHA-256: `4864fb24bead03dff712454c863ef79ad6a29493c4bb4b261f9e5df674193ff6`.
- Image size 320×180 = 57,600 pixels. All reported negative/nonfinite channel counts are zero.

## User-run PFM measurements

| Image/metric | CPU reference A | CPU reference B | Q8 GPU candidate |
| --- | ---: | ---: | ---: |
| Positive luminance pixels | 0 | 0 | **10,076** (17.4931% of frame) |
| Luminance ≥ 1×10⁻⁴ pixels | 0 | 0 | **510** (0.8854% of frame) |
| Mean luminance | 0 | 0 | **4.080165865790125×10⁻⁶** |
| Max luminance | 0 | 0 | **1.277943083550781×10⁻⁴** |
| All-black | yes | yes | **no** |

- `RMS(R_A,R_B)=0.0`: zero-signal pair is **not** evidence of two independent stable noise estimates.
- `RMS(Q8,R_A)=1.6121822848358563e-05` (whole-frame RGB).
- `whole_frame_abs_luma_p99(Q8,R_A)=7.629510946571827e-05`.
- `pixel_mismatch_count(Q8,R_A)=10076`, equal to the GPU positive count.
- `gpu_only_positive_pixels=10076`, **all** positive GPU pixels lie outside the CPU reference-positive mask, because that mask is empty.
- The GPU has **9,566** weakly positive pixels below the `1e-4` screening floor (10,076−510). **510 / 57,600 = 0.8854%** of the frame at/above floor.
- `active_pixel_count=0`, thus `active_abs_luma_p99=active_rel_luma_p99=0` are **undefined as evidence** (software's empty-set sentinel, not actual zero conditional error).
- `statistically_eligible=false`; both sources black and only two stored references, while prospective N007 requires 4 and robust nonzero active support.

## CPU source-only causal analysis, not a measured mechanism

1. `src/research/lane_n_end_to_end_renderer/n001_reference.cpp`: camera rays are fixed pixel-center (no subpixel jitter across seeds); secondary cosine directions vary with seeds; both direct and subsequent bounces call `direct_lambert()`, which **checks visibility to the light with a shadow BVH query**.
2. `shaders/research/lane_n_end_to_end_renderer/n003_composite_software.comp.glsl`: the N006 software-primary Q8 compositor computes **primary direct** with `visible_to_light()`; then independently **adds indirect** from `lookup_probe()`. Its nonzero final output alone cannot identify either contributing component.
3. `shaders/research/lane_n_end_to_end_renderer/n001_physical_radiance.comp.glsl`: probe-hit `point_light_lambert()` **does not shadow-test the light**. This can produce unoccluded probe-energy contributions, but it is not established that these contribute to the **particular** 10,076 positive pixels; different ray and hit behavior or CPU scene/state issues also remain possible.
4. The original `n001_reference.cpp` calls `compare_replicates()` on the **entire image**, with a whole-frame p99 gate. For a fully black pair, p99=0 and premature "converged" is inevitable regardless of independent seeds. The M3b PFM pair being black is an image-level **observation**, not proof that the underlying physical light transport should be black.
5. `n001_runtime.cpp` supplies `renderer_readback().triangles` from its `b_scene.triangles`. For moving-rigid rigid-instance branches, postframe translated geometry is populated before readback. Do not assert that the CPU automatically used stale pre-motion geometry.

## Decisions / next isolation tests

- **Keep original N006 M3b `invalid-retained` and P1 NO GO exactly as recorded.** No GPU superiority, P1 promotion, or relative quality verdict.
- The first causal diagnostic must use **the same frozen camera/light/geometry/frame state** and distinguish CPU primary visibility / direct-light / first subsequent bounce hits from GPU primary visibility / direct / probe indirect. Do not equate nonzero with true radiance, or compare different scene states.
- CPU-only next step: inspect other original **archived** references, including N001/N004, to establish whether black-reference behavior is scenario-local or systemic, using paired preserved images (read-only, no GPU). This does not certify physical correctness.
- GPU later only for an N007-specific preplanned **direct-only vs indirect-only/occlusion** split. Do not rerun the N006 candidate study.
- The full original local diagnostic JSON/PFMs remain in the user's private workspace; store only this compact derived research record on the public research branch.
