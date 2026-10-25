# 049 — Candidate transport RTCV: design, prior art and development protocol

Registered 2026-10-25 after [266](../results/266-m002-ptr-failure-diagnosis.md),
before any RTCV code, image or timing exists. This record fixes the candidate
idea, its closest prior art, what is tuned on development data and what is
frozen before the unseen M003 heldout (registered separately as 050, before
any M003 scene, state or reference exists).

## Design input from 048

Screen-space spatial filtering cannot reduce variance on few-pixel geometry
(S4/S3L: operator ≈ identity) and a lighting-blind spatial model is biased when
lighting changes inside planar regions (S1L: 8–9% operator bias). Raw PT is
heavy-tailed on those scenes. Game GI runs on frame sequences, so variance can
be reduced per surface point over time — but ordinary temporal accumulation
lags (biased) under light or geometry motion.

## RTCV — replayed temporal control variate

Per frame t and pixel p (one primary ray through the pixel centre, exact
direct light as in raw PT; only indirect is estimated):

1. Primary anchor x (triangle τ, barycentrics, normal). Its previous-frame
   position x' uses τ's previous-state vertices; x' is projected with the
   previous camera to the nearest pixel q. History is valid iff q's stored
   previous anchor y lies on the same instance, coplanar with x' (normal
   dot ≥ 0.999, plane distance within a depth-scaled tolerance) and within a
   two-pixel footprint of x'.
2. For each of k fresh primary-sample-space random vectors u_i, evaluate the
   unchanged raw-PT indirect estimator twice with the *same* u_i:
   f1 = f(x, u_i; current scene S_t) and the replay f0 = f(y, u_i; previous
   scene S_{t−1}) (previous camera/light, previous-frame BLAS/TLAS retained).
   When y = x and the geometry did not change the path is traced once and only
   next-event estimation is evaluated for both lights; when nothing changed,
   f0 = f1 without extra work.
3. Estimate H_t = mean(f1) − w·(mean(f0) − H_{t−1}(y)). H_{t−1} is an
   independent estimate of E[f0], so H_t is unbiased for any w chosen from
   past statistics only. w = clamp((s² − δ²/2)/(s² + k·V), 0, w_max), the
   variance-optimal weight for per-sample variance s², replay-difference
   variance δ² and history variance V (all propagated per pixel from earlier
   frames); V' = (s²(1−w)² + w·δ²)/k + w²·V.
4. Without valid history (first frame, disocclusion) k_new fresh samples are
   used. Displayed/scored indirect is max(H_t, 0); the history keeps H_t.

Unlike reprojected accumulation (which keeps the old *value*), RTCV keeps the
old value only as a control variate whose expectation is re-estimated with
correlated replays in the old scene, so camera, light, rigid and deforming
changes do not produce lag bias; the cost is a replay path when something
changed, and a retained previous-frame acceleration structure.

### Prior art and novelty claim (bounded)

- Gradient-domain / temporal gradient-domain path tracing (Lehtinen et al.
  2013; Kettunen et al. 2015; Manzi et al. 2016, TOG 35(6)) estimate shifted
  or temporal differences and reconstruct with screened Poisson solves (offline).
- Residual path integrals for re-rendering (arXiv 2406.16302) estimate frame
  differences with correlated paths between old/new scenes (re-rendering).
- A-SVGF (Schied et al. 2018) re-shades previous samples with stored seeds to
  detect change and shorten history (anti-lag), not to correct the value.
- ReSTCV (Shi, Wu, Wu, Xu, SIGGRAPH 2026) adds spatio-temporal control
  variates to ReSTIR PT, estimating pixel differences from reservoir samples.

Claim permitted only if RTCV wins under 050: a real-time, image-producing
recursive temporal control variate for plain PT that replays the same
primary-sample-space path in the retained previous-frame scene (camera,
light, rigid and deforming change) with a variance-propagated weight, without
spatial filtering or ReSTIR. No claim of a new principle; the components above
are prior art.

## Comparison roles in the same new sequence harness

- `PT` — raw PT, k spp per frame, no reuse (existing estimator).
- `PTA` — established reprojected temporal accumulation of raw PT (same
  validity test, exponential history with cap N_max; SVGF/TAA-style temporal
  stage without spatial filter or anti-lag).
- `RTCV` — candidate.
All three share primary rays, path estimator, AS ownership, chunked dispatch
and timing boundary. PTR, NRD, DDGI, ReSTIR GI and RC are added for M003 in 050.

## Development protocol (development data only)

- Sequences are generated from the M001/M002 development scenes (H01–H03,
  S1, S2, S4) by a new deterministic generator (camera path, light path, rigid
  instance transform, vertex deformation), written in the N007 state format.
- Development references: GPU raw PT at ≥16384 spp per evaluated frame
  (dev proxy only; never used for M003 decisions).
- Tunable on development data only: k, k_new, w_max/N_max, statistic EMA
  rates, validity tolerances, warm-up length. All are frozen in 050.
- Development GPU runs are assistant-operated on the single local GPU, are
  disclosed here in advance as unlimited in count but never admitted as
  evidence; they write only under `out/research/lane-m-gi-competitiveness/rtcv-dev-*`.
- New harness: private copy of the state loader without the 2048-triangle cap
  (Sponza-capable), the 022 bounded context/HWRT objects (AS refit via
  `update_geometry`, GPU-timestamped), 128-pixel bounded dispatches, ownership
  ledger and 8 GiB cap unchanged. No power/clock changes, no CI, no change to
  any earlier evidence.

Stop/kill rule for the candidate before 050: if on development sequences RTCV
cannot meet the fixed gates (total ≤5%, indirect ≤10%, |bias| ≤5%, all pixels)
at lower per-frame GPU time than raw PT on most sequences after warm-up, the
candidate is recorded as a development negative and redesigned; 050 is not
registered for it.
