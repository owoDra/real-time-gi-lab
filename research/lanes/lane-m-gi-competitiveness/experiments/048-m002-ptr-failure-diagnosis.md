# 048 — Diagnosis of the M002 PT+reconstruction failures (CPU, existing data only)

Registered 2026-10-25 after the reopen decision
([2026-10-25-lane-m-reopen](../../../decisions/2026-10-25-lane-m-reopen.md)),
before any new computation on M002 images. M001 and M002 are development data
from now on; this study makes no gate decision and no performance claim. It
only explains why the fixed geometry-only quadratic reconstruction (PTR, 018/022)
failed on S4 (both depths), S1L and S3L (both depths) in
[outcome260](../results/260-m002-outcome.md), to inform a new transport design.

Already published (260), not new evidence: PTR indirect NRMSE falls roughly as
spp^-1/2 on S4/S3L and PTR is no better than raw PT at equal spp there; PTR
signed indirect bias is positive (S4/B2 +5.6% at 16 spp, S3L +27–36%).

## Inputs (read only, rehashed, nothing overwritten, no new rendering)

- the 12 reference-eligible M002 targets: admitted reference means and the
  admitted level's oracle primary file `o.n{spp}.hits` in `m002-references-v1/`;
- every saved M002 capture image `m002-captures-v1/*/*/capture/image.f32`
  (PT_REF and PTR rungs);
- M002 states `m002-states-v1/` (geometry metadata, camera, light);
- control only: the six archived 022 GPU captures `m001-integrated022-gpu-*-v1`
  (`hits.u32`, `coefficients.f32`, `sources.f32`, `stages.f32`) and their M001
  references' oracle primary files.

## Method

1. **Primary geometry without the GPU.** Build the 022 hit record from the
   oracle primary file (triangle id → canonical primitive/material/instance
   from the state metadata, f32 geometric normal flipped toward the ray, f32
   distance), then positions/normals/epsilon exactly as `geometry_filter_cpu`.
2. **Operator replica.** Unchanged 017 masks (`geometry_barrier_filter`) and
   018 fit (`surface_quadratic_filter.fit`), three strides, clip after each pass.
3. **Control (must pass before any M002 interpretation).** On all six M001 022
   captures: (a) constructed hits vs archived GPU hits with
   `closest_primary_metrics.primary`: zero primitive mismatches; (b) the
   replica reconstructs the archived `sources` to the archived final stage with
   NRMSE (relative to the archived final-stage RMS) ≤ 1e-3. Failure → the
   diagnosis is recorded as CONTROL_FAIL and no mechanism label is assigned.
4. **Per M002 target** (with `ref` = reference indirect luma, `Op` = clipped
   operator, `Lin` = the same coefficients without clipping):
   - operator bias floor: indirect NRMSE and signed sum bias of `Op(ref)`;
   - noise ratio: `R_n = ||Lin(PT_n − ref)||² / ||PT_n − ref||²` for every
     saved PT rung n (independent PT images, so `R_n` estimates the variance
     gain of the operator on that target's actual noise);
   - exact per-pixel noise gain `g_p = Σ_q W_pq²` of the composed linear
     operator (white-noise gain): mean, and fraction of hit pixels with g ≥ 1;
   - clip bias: signed sum of `Op(PT_n) − Lin(PT_n)` relative to `Σ ref`, n = 16, 64;
   - attribution of `||Op(PT_64) − ref||²` (or the largest saved rung ≤64) by
     stage-0 selected model (quadratic/affine/constant/miss) and by the number
     of accepted stage-2 taps (≤8, 9–16, ≥17), with pixel shares;
   - heavy tail: share of `||PT_1024 − ref||²` carried by the top 0.1% pixels,
     and the fitted log–log slope of PT NRMSE vs spp;
   - scene/light descriptors: indirect/total RMS ratio, light-to-nearest-
     triangle distance, light soft radius `s`.
5. Replay check: the replica's `Op` applied to each saved PT_REF image is a
   statistically equivalent PTR realization (different seed); its indirect
   NRMSE at the PTR rung spp is reported next to the saved PTR score
   (descriptive, no threshold).

## Mechanism labels (fixed before any number; several may apply)

For each failing target (S4/B2, S4/B8, S1L/B2, S1L/B8, S3L/B2, S3L/B8) and,
as contrast, each passing one:

- `BIAS_FLOOR` iff `Op(ref)` indirect NRMSE > 0.05 or |signed bias| > 0.025
  (more than half the gate from the operator alone);
- `NO_VARIANCE_REDUCTION` iff `R_64` (or nearest saved rung) > 0.25
  (less than 4× variance reduction, i.e. under 2× NRMSE gain);
- `CLIP_BIAS` iff the 64-spp clip bias > +0.025;
- `HEAVY_TAIL` iff the top-0.1% share of PT_1024 squared error > 0.25.

The study ends with one diagnosis record (JSON + outcome). Implementation
failure of the replica stops the study (no retry, failure recorded). CPU only;
no GPU, no new references, no change to 046/047/260 evidence.
