# N006 P1a offline pixel-effect audit — completed

Issue #42. Status: **complete, diagnostic, non-formal**. Uploaded artifact `n006-p1a-image-audit.json` from clean source pilot HEAD `4871623797b8ba0b155447f63697bd3340829ee3`.

## Frozen observations (reproduced by user with offline PFM audit)

- `all_interventions_validated=true`. Twelve cases have **four actual extra rays each**. Eleven of twelve have exactly **zero changed channels and pixels** versus the fixed current image; their candidate image SHA-256 matches the baseline image hash `79de995078c605c8c5c6aef44c8565edf3f808e32934fd43646753bdba815861`.
- The one responsive case is **tile 22890, cascade 3**: `changed_pixels=468` / `changed_channels=1404` / `changed_pixel_fraction=0.008125` (=0.8125% of the 320 × 180 frame); `beneficial_pixels=468`, `harmful_pixels=0`, `source_tile_pixel_changed=false`.
- The one effect is tiny: `image_delta_rgb_rms=9.108798546220177e-09`, `max_abs_channel_delta=1.0105304681928828e-07`, and `global_rgb_rms_gain=+4.1349093211364395e-10` against `baseline_rgb_rms=3.019924015741972e-05` (~0.00137% reduction).
- Reference SHA-256 `9302b47c982778dd654d7d404b23c743a7445ca966d49c5a526b1727cf8fbc87`, experiment/calibration only, not held-out signal study.

## What the source does and does not prove

Accepted renderer source was rechecked:
1. Producer emits eight octant rays per visible owner × cascade, each with `(probe xyz, cascade)` and an `output_id` local to that owner.
2. N006 suffix generates four additional deterministic spherical directions into **one** output ID.
3. Radiance clamps to 16-bit integer units (`round(value * 65535)`); contributions merge as integer sum/sample count by `output_id`.
4. Storage updates a **single 16-bit rounded mean** per owner output, then averages these values by shared `(probe xyz, cascade)`.
5. Composite fetches probes by each **screen pixel's own world position**, so its spatial key can differ from the selected owner's tile. That explains why `source_tile_pixel_changed=false` is compatible with influence on 468 *other* pixels.

**What remains unresolved:** In the eleven exact-image-zero cases, were all added radiance contributions zero/same as baseline, was a small change removed by 16-bit rounding / averaging, or did the changed probe have no final screen consumer? The saved JSON and PFM only establish final image invariance; no accepted intermediate per-work-item contributions/storage-key readbacks were included.

**Decision:** Do **not** infer that importance scheduling is globally useless or that cascade 3 is best based on this three-tile subset. **P1 predictive ranking gate remains CLOSED.** Perform a smaller prospective **instrumented causal-chain probe** of selected zero/positive controls before any broad or formal GPU campaign. No new scoring thresholds or selector tuned to these results.

## Prospective narrow follow-up

New diagnostic should keep accepted N004/N005 untouched, preserve existing N006 P1a output, and expose only selected per-ray integer contributions, per-output average, same-probe owner count, and pre/post quantized storage sample for a known tile × cascade. A short source warmup may be used only after fresh current image is verified bit-equivalent to the previous baseline; otherwise stop and retain the mismatch artifact. Do not interpret the serial P1a shader time as a feasible scheduler cost.

Full images and raw artefacts remain under the existing `out/research` campaign. No GitHub Actions.
