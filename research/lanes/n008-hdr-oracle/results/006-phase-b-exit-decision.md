# N008 Phase B — frozen Renderer states: per-cell reference classification, Exit B = GO (bounded)

**Date:** 2026-10-13 JST · **Protocol:** [experiments/002](../experiments/002-phase-b-frozen-states-and-reference-eligibility.md), preregistered at `9aab73b`, which is also the acquisition commit (clean tree).

**Executed by:** the assistant on CPU only. Phase A regression at `9aab73b`:
- C++ tests 17/17;
- Python tests 7/7;
- A1–A10 and X1–X6 all PASS, with all 102 control check records numerically identical to the frozen Phase A run.

**Evidence:** [005-phase-b-reference-ladder.json](005-phase-b-reference-ladder.json) is the unchanged N007 screen output, plus N008 component and hit diagnostics. Raw PFM/sidecars are private in `out/research/n008-hdr-oracle/phase-b-9aab73b/`.

## Frozen states are the Renderer's own states

`n008_state_export` compiles verbatim-extracted Renderer CPU code and the Renderer's glTF loaders, with no Vulkan. Its moving-rigid output is **byte-identical to the GPU-run N007 capture**:
- frame `77e1d952…`
- geometry `d70e8344…`

Every oracle run re-derived its loaded-geometry SHA-256 (14/14 match).

## Result per cell (T_B2 = direct + one shadowed bounce; T_B8 = 8 bounces; 4 seeds, nested 512–8192 spp)

| Cell | Class | Classification (T_B2 / T_B8) | Direct support (deterministic) | Total union support at 8192 | N007 screen |
|---|---|---|---|---|---|
| B1 | static | **INELIGIBLE / INELIGIBLE** | 27 px (0.05%), peak Y 1.15e-4 | 1,034 / 1,103 px (1.8% / 1.9%), still growing with spp | fail at every level (support/noise) |
| B2 | camera motion / disocclusion pose | **NO_SUPPORT / NO_SUPPORT** | 0 | 0 | black reference |
| B3 | light motion | **DIRECT_DETERMINISTIC_PROVED** (both) | 9,546 px (16.6%), peak Y 1.53e-3; four seeds byte-identical | 9,546; **indirect exactly 0** for D=2 and D=8 | fail (identical replicates, expected for deterministic direct) |
| B4 | moving rigid | **NO_SUPPORT / NO_SUPPORT** | 0 | 0 | black reference |
| B5 | stable deforming | **INELIGIBLE / INELIGIBLE** | 27 px | 1,034 / 1,103 px | fail |
| B6 | topology churn | **INELIGIBLE / INELIGIBLE** | 27 px | 950 / 1,062 px | fail |
| B7 | non-Sponza `leak-medium` | **STATISTICALLY_ELIGIBLE** (T_B2 at 1024 spp; T_B8 at 4096 spp) | 6,943 px (12.1%) | 7,252 / 7,316 px (12.6% / 12.7%) | pass: active p99 abs 3.3e-6 / 2.5e-6, rel 3.2% / 2.5% |

Additional diagnostics:
- Primary hit coverage is 22–26% of pixels for Sponza and 12.7% for B7.
- Pixel-centre hits on the **back face of a single-sided triangle** (the Renderer culls these and sees through them): 0 px for B1–B5, 0.1% for B6, and **8.6% for B7**. Phase C must exclude or flag these pixels.

## Interpretation (bounded)

- **The oracle now gives a physically validated answer for the dark cells.** The direct term is deterministic and was validated exactly in Phase A. For the B2/B4 target states it is exactly zero at every pixel, and no one- or eight-bounce path reached the camera in 4 × 8192 samples per pixel.

  Within the declared Renderer light/geometry, these states are therefore **unlit at the camera**. N007's all-black moving-rigid reference therefore reflects the scene state itself, not only a reference defect. This does **not** revise N007 or N006; it is a new, separately preregistered measurement.
- **Why Sponza is dark — a source/state fact, not something inferred from images:**
  - The N-series loaders use raw mesh POSITION data **without glTF node transforms**, so the 25 nodes rotated +90° about X are ignored.
  - The A001 light and the camera eye lie **outside** the geometry bounds.

  Whether this orientation was intended is a Renderer scene-contract question, outside N008's authority to change.
- **B1/B5/B6 are sparse, non-converged signals:**
  - Support keeps growing with spp: 0.39% → 1.8%.
  - Only 27 pixels are directly lit, and the rest is rare one-bounce light.

  The frozen N007 thresholds correctly refuse them; they cannot be used for scoring.
- **B3 (light motion):** the direct term is a proved deterministic reference on 16.6% of pixels. Indirect is exactly zero even at 8 bounces. A plausible reading is that the lit surfaces are exterior faces seen from outside, but this was **not verified** and is not claimed.
- **B7 is the only cell with a statistically eligible total reference.** Its eligibility is statistical plus Phase A physical validation of the transport. It still excludes the 8.6% back-face pixels whose Renderer visibility semantics differ.

## Exit B (preregistered rule)

**GO to Phase C, bounded.** Every cell B1–B7 has a final classification. At least one cell qualifies:
- B7 is STATISTICALLY_ELIGIBLE;
- B3 is DIRECT_DETERMINISTIC_PROVED.

**Required dynamic Sponza classes are bounded negatives for quality scoring:**
- **Camera and moving rigid** have NO_SUPPORT.
- **Static, deforming and topology churn** are INELIGIBLE.
- **Light motion** is eligible for direct only.

No candidate may be scored on B1, B2, B4, B5 or B6, or on B3's indirect or total.

**Not done in Phase B, and not claimed:**
- GPU readback attestation for B1–B3 and B5–B7. These states come from the same extracted code path, but only B4 is GPU byte-attested.
- Any relit or reoriented Sponza. That would be a new preregistered cell, not a rescue.
- Multi-GPU work.
