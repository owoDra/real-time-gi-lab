# 049a — Development record: from RTCV to RTCVS (disclosed development only)

Addendum to [049](049-rtcv-candidate-design-and-development.md). Everything here
ran on development data only (M001/M002 scenes, sequences generated from them,
and a separate development Sponza viewpoint rotated 60° from the authored
camera; GPU raw PT 4×16384 spp proxy references). None of it is evidence for
the goal; it explains the frozen candidate registered in 050.

## Changes, in order, and why

1. **Data-independent weights.** A first RTCV run weighted history by the
   pixel's own sample statistics and showed +100% bias (outlier-inflated
   histories were kept longer). Weights now depend only on the history length,
   the propagated variance and previous-frame tile ratios.
2. **Replay origin.** Replaying from the same surface point x' (not from the
   previous pixel's anchor) removed lag under light/geometry change; replaying
   from the anchor under camera-only motion was too decorrelated
   (difference/sample variance ratio ≈ 1%) to pay for its cost.
3. **RTCVF.** The replay difference d is filtered spatially (9×9, same
   instance, coplanar, range-weighted by the previous history) — radiance is
   never filtered — and the history is limited where the relative change is
   large. Camera-only frames use bilinear reprojected accumulation (≤ 16
   frames), i.e. the same estimator as the PTA family.
4. Tried and rejected (quality or cost): adaptive per-pixel boosts, thin-
   feature boosts, partial or sparse replays, larger filters, stronger
   change anti-lag (γ 16), shift-regressed difference (no effect, kept).
5. **Bounded dispatch size** for every role 128 → 4096 pixels (bit-identical
   images; lower fixed overhead for all roles alike). Stateless roles batch
   large sample counts over full-image submissions (a per-chunk submission
   serialized the GPU: Sponza B8 PT1024 232 s → 3.8 s, identical image).
6. **SPR / RTCVS.** All surfaces are two-sided Lambertian, so the radiance
   leaving a neighbour's secondary vertex z towards x equals that towards the
   neighbour (same side). Each pixel reuses the paths of its coplanar 3×3
   neighbours, reconnected at z with one visibility ray each, combined with the
   multi-sample balance heuristic (other techniques' pdfs ignore their own
   visibility to z — a small approximation near occluders). Single frame: ~7×
   lower variance than raw PT at 1.5× cost (3×3). RTCVS = SPR fresh estimate +
   RTCVF history/correction.

## Development picture (not evidence)

On the small development scenes (1.2–6k triangles; fixed per-frame overheads
of a few hundred µs dominate) RTCVS was clearly cheaper than reprojected
accumulation (PTA) only under light motion (≈2×, PTA fails some scenes by lag
bias); under camera/rigid/deforming motion PTA at k=4 (0.19–0.30 ms) was as
cheap or cheaper, and an enclosure scene (H03) defeated all temporal roles.
This motivates registering both small and Sponza-scale targets and stating the
per-stratum expectation honestly in 050.

Prior art for SPR: Bekaert, Sbert & Halton, "Accelerating Path Tracing by
Re-Using Paths" (EGWR 2002); reconnection shift maps in gradient-domain path
tracing and ReSTIR PT (Lin et al. 2022). RTCVS's bounded novelty claim is the
real-time combination with the replayed temporal control variate.
