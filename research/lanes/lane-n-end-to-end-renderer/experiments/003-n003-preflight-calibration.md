# N003 preflight/calibration — complete-frame comparison contract

Status: **v1 and v2 timing-unsuitable; paired-control v3 target pending**

Issue: #31  
Parent: #26  
Input baseline: N002 complete at `0188c7f7b4b43e5d887cd753d74a69e11a2ea764`

## Purpose

This is part of Lane N and is the preflight for N003 proper. It freezes how N003 may interpret performance and image-quality differences before the vanilla Split RC comparison is measured.

## Retained failed calibrations

### v1 — absolute fresh-process timing

Commit `422945ea32164e487e8562214dc7568f6e2ad9a6`:

- worst across-process timing noise: **48.297%**;
- derived threshold: **145.0%**;
- result: `timing-unsuitable`.

The failure showed that absolute fresh-process timing is not the correct N003 decision unit.

### v2 — paired fresh-process A/A

Commit `aa46afd1594cf66cae440b30223cfc1350475a67`:

- A and B were identical current-architecture N002 executions;
- eight pair blocks completed with no sample exclusion;
- control formal-claim trigger count: **0**;
- derived threshold: **110%**;
- worst p95 A/A pair effect: about **97%**, from camera-motion;
- result: `timing-unsuitable`.

v2 exposed near-2x modes in short static/camera complete-frame timings, while stable-topology-deforming remained comparatively stable. Quality was deterministic across all 16 A/B observations and the scale-aware affected metric had campaign signal.

Both failed artifacts remain evidence. Neither is filtered or rewritten as PASS.

## Timing protocol v3

v3 retains the same complete renderer/GI timing boundary and the same statistical decision rules. Only the timing harness changes prospectively.

A dedicated `phos-n003-preflight` target executes A and B inside one process. For every role/scenario it runs **32 unmeasured source-state frames immediately before the one measured target-state transition**. This warms the GPU without consuming the measured dynamic update/rebuild: moving-rigid, stable-topology-deforming and topology-changing/high-churn still perform their target transition exactly once inside the measured sample.

Eight fresh process pair blocks are used. AB/BA start order alternates. Every measured frame must pass runtime correctness. The pair artifact retains both complete timing axes and every N002 stage bucket so a remaining instability can be localized.

For each scenario and each of `complete_gi_gpu` / `complete_renderer_gpu`:

1. compute eight paired `log(B/A)` values;
2. primary statistic = median paired log ratio;
3. robust null bound = `abs(median_log_bias) + 3 * 1.4826 * MAD(log_ratio)`;
4. convert to fractional effect;
5. campaign threshold = largest bound, rounded upward to 0.5%, minimum 1%.

Formal N003 timing claims additionally require >=75% same-direction pairs. A/A control must not trigger a claim. Worst p95 absolute pair effect must be <=20%, and the derived threshold must be <=20%.

Lane K's 5% and Lane L's 20% values are not imported as the N003 threshold. Samples cannot be deleted and a completed PASS calibration cannot be rerun for a more favorable threshold.

## Quality protocol

Quality interpretation was established and shown deterministic by v2, so v3 does not alter it.

Legacy `affected_pixel_fraction` remains diagnostic-only. Primary metrics are:

- `rgb_rms_error`;
- `p99_abs_luminance_error`;
- `scale_aware_affected_pixel_fraction`, with `abs_error >= 0.05 * max(abs(reference_luminance), 0.0001)`.

There is no aggregate winner score. Interpretation is scenario-by-scenario. A material quality change requires concordant movement in at least two of the three metrics; error metrics require >=10% relative change and scale-aware affected fraction requires >=0.005 absolute change. Individual black reference frames remain valid.

## Execution

Build `phos-n003-preflight`, run the v3 contract test, then run `run_n003_preflight_v3.py` through the research experiment wrapper. v1/v2 artifacts remain untouched under `out/research/`.

N003 proper may start only after v3 passes and its derived timing threshold is recorded in result truth.
