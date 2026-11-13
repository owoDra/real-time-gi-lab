# 2026-11-13 — Program 1 archived; Program 2 starts on a clean tree

User decision (2026-11-13), after an assessment of the whole record.

## Decision

1. **Program 1 ends here.** Program 1 = everything from M0 (cache locality)
   through lanes A–N, N005–N010 and Lane M (GI competitiveness). Lane M is not
   completed: the research goal of the
   [reopen decision](2026-10-25-lane-m-reopen.md) was **not achieved**, and
   M003 was never registered or run. No result is relabelled.
2. The Lane M branch is merged into `research` (fast-forward) and the merged
   state is tagged `archive/program-1`. Every earlier branch and ref stays.
3. **Program 2** starts on branch `p2`, cut from that tag, with a tree that
   keeps only what Program 2 needs. Everything removed from the `p2` tree
   remains reachable through `archive/program-1`.
4. Machine-local raw artifacts under `out/` and `build/` are removed from the
   workstation (see "Raw evidence" below).

## Why Program 1 stops

- The fixed gates (indirect NRMSE ≤ 10%, all pixels, against converged path
  tracing) are passed only by path-traced families. DDGI, NRD, ReSTIR GI and
  every RC role fail 0/6, so the gates rank near-converged path tracers and do
  not measure real-time GI.
- The cohort is far from practical use: 320×180, scalar radiance, two-sided
  Lambert, one point light, black background, small scenes covering 1.5–13% of
  the image. Sponza at k=1 costs about 7 ms at 320×180 on the test GPU.
- The candidate RTCVS is weaker than its development summary states
  ([269](../lanes/lane-m-gi-competitiveness/results/269-dev-sequence-validity-check.md)):
  the Sponza light sequence and six small rigid/deform sequences are static.
  Its replayed control variate is active for light changes only; the Sponza
  gain comes from spatial path reuse, which is prior art.
- Completion was defined as "goal achieved" with single-use heldouts and no
  stopping rule.

## What Program 1 established (carried forward as knowledge)

- Reference admission, calibrated AB/BA timing with a measured minimum
  detectable effect (045), and keeping every loss.
- Defects found in third-party paths: DDGI SDK border-copy corruption (051),
  ReSTIR GI bias of +258–377% when a MISS is treated as an empty reservoir
  (042), NRD sky-history initialisation (024/025).
- Screen-space spatial reconstruction fails on sub-pixel geometry and is biased
  under light motion (048/266).
- Segment DDA over a hashed grid beats a macro BVH as the top level (B003);
  per-segment ownership gives localized updates (B002, Lane E).
- N004: the Split RC renderer's blockers are camera/disocclusion and dynamic
  geometry, not thin-wall leaking.

## Program 2 in one paragraph

Goal: GI for fully dynamic, large and dense worlds that is fast, light and
stable; that mixes photoreal and non-photoreal styles in one space; and that
runs on WebGPU (WebGL2 as a reduced tier). Direction: a noise-free radiance
field from the Radiance Cascades family; interval tracing against a
representation matched to each cascade (depth buffer near, hashed voxel
StrataBrick levels beyond); style as operators at emission and reception.
Evaluation is quality at a fixed cost, not time at a fixed quality. The
charter, roadmap and working rules live on branch `p2`.

## Raw evidence

`out/research` held about 411 GB of machine-local raw payloads (N010 237 GB,
Lane M 165 GB, N008 5.7 GB, N009 4.2 GB, N007 0.2 GB) with no complete backup.
Committed records keep their summaries and hashes. Once the local payloads are
deleted, those hashes can no longer be re-verified against bytes; reproducing
a payload means re-running the committed source at the recorded SHA. The exact
disposition is recorded in the `p2` branch status at the time of deletion.

Tests and GPU runs were **not rerun** for this archival step; no runtime
regression claim is made.
