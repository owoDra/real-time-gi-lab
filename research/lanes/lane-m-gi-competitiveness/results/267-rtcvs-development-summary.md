# 267 — RTCV/RTCVS development summary (049/049a, development only — not evidence)

Status at the 2026-10-26 session break. All numbers are disclosed development
runs on development data (M001/M002 scenes and generated sequences `L-*`,
192 frames, speed 0.5; a development Sponza viewpoint `D-SP-*` rotated 60° from
the authored camera), scored against GPU raw-PT 4×16384 spp proxy references,
one seed, single GPU (Radeon 8060S). They choose the design; they prove nothing
about the goal. Raw sweep logs: `out/research/lane-m-gi-competitiveness/rtcv-dev-logs/`
(sweep16 = latest RTCVS state, sweep12 = PTA ladders, sweep14 = Sponza PTA/PT).

## Current candidate (not frozen, not registered)

RTCVS = ROLE 7 of `shaders/.../rtcv_sequence.comp.glsl` (defaults in file):
k fresh PT paths/pixel → spatial path reuse (SPR: coplanar 3×3 neighbours'
paths reconnected at their secondary vertex, balance-heuristic MIS, one
visibility ray each) → bilinear reprojected accumulation (N_max 256; camera-
only ≤16) → for light changes only, replayed temporal control variate (same
path, both lights), 9×9 range-weighted filtered and Wiener-shrunk difference.
Geometry changes are accumulated without replay (`GEOM_NO_REPLAY 1`).
`GEOM_SPARSE` (1-in-9 replays for geometry change detection) is implemented
but untested (default off).

## First warm-passing configuration (frames ≥128 or ≥160) and mean GPU frame time

| sequence | raw PT | PTA (best k×N) | RTCVS |
|---|---|---|---|
|D-SP-light (Sponza)|k1024 2622 ms|k4 14.7 ms|**k1 6.9 ms**|
|D-SP-rigid (Sponza)|k1024 3940 ms|k4 20.8 ms|**k1 11.5 ms**|
|S1/S2 light|k1024 ~13–21 ms|k32 1.2–1.6 ms|**k1 0.66–0.76 ms**|
|S4 light|k1024 18.6 ms|k32 1.41 ms|k8 1.19 ms|
|H02 light|FAIL|FAIL|**k8 1.72 ms**|
|S1 static|k1024 21 ms|k4 0.53 ms|k1 0.48 ms|
|S1/S2/H03 camera|k1024|k16 1.06–1.41 ms|k2–k8 1.22–1.68 ms|
|S2/H02/S4 rigid+deform|k1024|**k4 0.19–0.30 ms**|k1–k2 0.27–0.36 ms|
|S1 rigid (main occluder rotates)|—|k32 1.43 ms|FAIL (lag)|
|H02/S4 camera, H03 deform/light, S1 combined|mostly k1024 only|FAIL|FAIL|

Reading: RTCVS wins wherever path tracing dominates the frame (Sponza scale:
≈1.8–2.1× faster than the best PTA, ≈380× than raw PT) and under light motion
(PTA lags). On the small scenes (1–6k triangles, frame ≈0.2–0.5 ms, fixed
overhead dominant) PTA at k=4 is as fast or faster under camera/rigid/deform,
and strong geometry motion (S1 rigid) defeats RTCVS's long history. Some
enclosure/camera cases fail for every temporal role. SPR has a small negative
bias (−1.8% Sponza, up to −4.6% on few-pixel boxes) from ignoring other
techniques' visibility in the MIS denominator.

## Engineering facts established in development

- Sequence harness (`rtcv_sequence_gpu.cpp`): roles PT/PTA/RTCV/PTG/RTCVF/PTR/
  SPR/RTCVS, no triangle cap (Sponza 262k), ping-pong retained BLAS/TLAS with
  GPU-timed refit, 045-format AB/BA `--timing` mode over sequences, 4096-pixel
  bounded dispatches (bit-identical to 128), full-image sample batches for
  stateless roles (Sponza B8 PT1024 232 s → 3.8 s, identical image).
- `m003_build.py`: private build (wall guard 180→1800 s only) — required for
  192-frame Sponza runs; GPU jobs must never run concurrently (contention caused
  a fence timeout once).
- `m003.py`: scenes/lock/qualify/build/ladders drafted, not yet run.
