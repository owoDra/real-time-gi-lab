# DRAFT (NOT REGISTERED) — 050 M003: frozen RTCVS on unseen dynamic heldouts against all families

Registered after the 049/049a development (disclosed development runs only:
M001/M002 scenes, sequences generated from them, and a development Sponza
viewpoint rotated 60° from the authored camera), BEFORE any M003 scene file,
state, sequence, reference, image or timing exists. This is the decisive test
of the Lane M completion gate ([reopen decision](../../../decisions/2026-10-25-lane-m-reopen.md)).
It supersedes the unpublished 050 draft for RTCVF, which was never committed.

## Frozen candidate: RTCVS

ROLE 7 of `shaders/research/lane_m_gi_competitiveness/rtcv_sequence.comp.glsl`
with the defaults in the file at this commit; host
`src/research/lane_m_gi_competitiveness/rtcv_sequence_gpu.cpp`; built by
`m003_build.py` (byte-identical source copies; the only private change is the
process wall guard 180 s → 1800 s for 192-frame Sponza sequences). Per frame,
every GPU operation is timestamped: AS refit of the frame's retained BLAS/TLAS,
primary, sample pass, spatial path reuse, combine, tile reduction.

1. k fresh raw-PT paths per pixel (k_new = 32 without valid history); each
   stores its secondary vertex z and tail radiance.
2. If the light changed, every path is replayed with the same primary-sample-
   space random numbers along the same geometry with the previous light (one
   traced path, next-event estimation for both lights); the replay difference
   d is filtered over 9×9 (same instance, coplanar, range-weighted by the
   previous history) and Wiener-shrunk against its own noise to D. Geometry-
   and camera-only frames do not replay (049a: at moderate motion the replay
   noise exceeded the lag bias it removed); the previous BLAS/TLAS is still
   retained for reprojection of moving surfaces.
3. Spatial path reuse: the pixel's fresh estimate combines the paths of its
   coplanar 3×3 neighbours reconnected at z (two-sided Lambert), one
   visibility ray each, multi-sample balance heuristic.
4. H_t = (1−w)·fresh + w·(H_{t−1}(x') + D), H_{t−1} bilinear at x'; w from the
   propagated variance (fresh counts as 4k samples), previous-frame tile replay
   ratios (independent of the pixel's own samples), relative change (γ 4),
   N_max 256. Camera-only frames: bilinear reprojection, history ≤16 frames.
5. Ladder k ∈ {1, 2, 4, 8, 16, 32, 64}.

## Unseen heldout M003 (fixed now)

Small scenes (N004 factory, CPU exporter with the M001 contract; unused in
Lane M and N010): N1 `world_scene("dense")`, N2 `world_scene("vertical-tall")`,
N3 `leak_scene("thick", 0.29)`, N4 `leak_scene("grazing", 0.25)`,
N5 `leak_scene("enclosed", 0.21)`; each × {static, camera, light, rigid,
deform} via `rtcv_sequences.generate` (192 frames, speed 0.5; moving instance:
drop the instance with most triangles, take the largest remaining, ties →
highest id); evaluated frames 160 and 191; fresh references (unchanged N010
RQMC oracle and N007 admission ladder) per evaluated frame, B2 and B8;
REFERENCE_INELIGIBLE targets are reported and not scored.

Sponza (262,241 triangles): N010 lock026 cells C1 static, C2 camera, C3 light,
C4 rigid, C5/C6 deforming as 192-frame sequences moving linearly from the
lock026 source state and ending with a byte copy of the locked target (C1:
the target for all frames); evaluated frame 191 against the existing N010
references of that exact state (C1–C4 B2 original rule; C1–C4 B8, C5/C6 B2/B8
R1 rule, reported as R1). Disclosure: these states and references were made
and scored in N010 (PT/RC), never used in Lane M candidate development.

## Families and ladders

Same harness/process/timing boundary (own retained ASes and histories):
PT k ∈ {16, 64, 128, 256, 512, 1024, 2048, 4096}; PTR (PT + unchanged
018/022 quadratic reconstruction) k ∈ {4, 16, 64, 256}; PTA (bilinear
reprojected accumulation) k ∈ {1, 2, 4, 8, 16, 32, 64, 128} × N ∈ {4, 8, 16,
64, 256}; PTG (PTA + A-SVGF-style replay-gradient anti-lag) k ∈ {1, …, 128}.
External families in their own qualified harnesses (private builds differing
only by the triangle cap where needed) at every evaluated state with a 64-frame
static history at that state (their most favourable case) and their highest
M001 budget: NRD RELAX (026 sky-initialized variant), corrected DDGI (054/056),
ReSTIR GI receiver-frame reuse V1 (042), N010 RC incumbent. Quality only.

## Quality, timing, memory

A configuration passes a target iff every evaluated frame passes the fixed
gates (total NRMSE ≤ 5%, indirect NRMSE ≤ 10%, |indirect signed bias| ≤ 5%,
all pixels), one fixed-seed run; first pass = cheapest ladder entry. Fresh run
of the unchanged 045 calibrator (8 × 32 AB/BA pairs, three sizes) → MDE. T1
campaigns in the sequence timing mode: 8 fresh processes, 156 settle frames,
4 warm-up + 32 measured pairs over frames 160–191, AB iff pair+process even,
frame cost = render + AS refit GPU time; 045 rules (threshold
max(log 1.20, log(1+MDE)); span ≤ log 1.05, order bias ≤ log 1.03, same-sign
≥ 0.75). True peak owned memory per role from separate capture processes.

## Decisions (fixed now; no exceptions)

For each eligible target and family F:
- QUALITY_WIN: F has no passing configuration, RTCVS passes.
- FASTER: T1(RTCVS first pass, F first pass) = FASTER.
- SAME_COST_BETTER: otherwise, F′ = F's passing configuration with the
  smallest descriptive cost not below RTCVS's; T1(RTCVS, F′) is FASTER or
  INCONCLUSIVE, and RTCVS's indirect NRMSE ≤ 0.8 × F′'s on every evaluated frame.
- Otherwise NOT_SHOWN; QUALITY_LOSS if F passes and RTCVS does not.
External families: QUALITY_WIN if they fail, else NOT_SHOWN.

**Lane M goal (M003) is ACHIEVED iff** RTCVS passes every eligible target and
every (target, family) pair is QUALITY_WIN, FASTER or SAME_COST_BETTER.
Otherwise NOT_ACHIEVED, with every loss kept. A Sponza-only tally is reported
descriptively and is not the criterion.

Prediction (049a dev, not evidence): large wins at Sponza scale (dev Sponza
light: RTCVS k1 7 ms vs PTA 14.7 ms vs raw PT 2.6 s); on cheap small scenes PTA
is expected to be faster under camera/rigid/deforming motion, so NOT_ACHIEVED
is the more likely outcome.

## Order and stop rules

Commit this registration → `m003.py scenes` and `lock` → reference
qualification (CPU) → `build` → quality ladders → external families →
calibration → T1 campaigns and memory → publication. Implementation/
provenance failures stop the step (recorded, no silent retry); quality losses
never stop the study. No tuning after M003 data exists; no ladder, gate or
threshold change. One GPU; no power/clock changes; CI untouched.
