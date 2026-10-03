# N003 preflight/calibration — complete-frame comparison contract

Status: **v1/v2/v3/v4 timing-unsuitable; clock-pinned v5 next**

Issue: #31  
Parent: #26  
Input baseline: N002 complete at `0188c7f7b4b43e5d887cd753d74a69e11a2ea764`

## Purpose

This is part of Lane N and is the preflight for N003 proper. It freezes how N003 may interpret performance and image-quality differences before the vanilla Split RC comparison is measured.

## Retained failed calibrations

### v1 — absolute fresh-process timing

Commit `422945ea32164e487e8562214dc7568f6e2ad9a6`: worst noise **48.297%**, derived threshold **145.0%**, result `timing-unsuitable`.

### v2 — paired fresh-process A/A

Commit `aa46afd1594cf66cae440b30223cfc1350475a67`: derived threshold **110%**, worst p95 A/A effect about **97%**, result `timing-unsuitable`. Quality was deterministic across all 16 A/B observations and remains accepted.

### v3 — same-process prewarmed A/A

Commit `ac143a567a056ff520e6f5ff73904c58196e989b`: derived threshold **207.5%**, worst complete-frame p95 effect **82.3%**, result `timing-unsuitable`. Stage diagnostics showed early-frame and dynamic-upload performance-state behavior. The source correctness validation sat between warm-up and measurement, so the intended hot-adjacent boundary was not preserved.

### v4 — hot-adjacent same-process A/A

Commit `8f9c78bddf31cd4d39070be5087a122c4b8edd84`: all eight pair blocks completed, all samples were retained, control formal-claim triggers remained zero, but timing was still unsuitable:

- derived threshold: **98.5%**;
- worst complete-frame p95 A/A effect: **27.2%** (`camera-motion` renderer axis);
- campaign worst robust noise: **98.0%**, dominated by `moving-rigid`;
- `static` improved to about **17%** p95;
- stable-topology deformation improved to about **8%** p95;
- topology/high-churn improved to about **9%** p95.

The v4 change therefore fixed a real harness problem but did not fully stabilize the GPU. Moving-rigid A/A complete-renderer ratios still ranged roughly **0.72–1.15**. Its geometry upload was comparatively stable while renderer prerequisite / frame-init / traversal / gather occasionally inflated together. This points away from a single timestamp/query defect and toward GPU performance-state changes during the campaign.

All failed artifacts remain valid diagnostic evidence. None are deleted, filtered, or rewritten as PASS.

## Timing protocol v5 — clock pinned

v5 keeps the **same v4 probe binary, hot-adjacent measurement boundary, eight-block AB/BA schedule, timing axes, MAD estimator, 20% suitability ceilings, 75% direction rule, and zero sample exclusion**. It changes only the host GPU power state prospectively.

The campaign requires AMDGPU `power_dpm_force_performance_level=profile_peak` before the first block and verifies that it remains `profile_peak` before and after every block and at campaign end. Available `pp_dpm_sclk`, `pp_dpm_mclk`, `pp_dpm_fclk`, and `pp_dpm_socclk` state text is retained as provenance.

The Linux AMDGPU interface documents `profile_peak` as a profiling-oriented mode that disables clock/power gating and drives the clocks to their peak levels. N003 proper must use the same pinned condition if v5 passes.

For every scenario and each of `complete_gi_gpu` / `complete_renderer_gpu`:

1. compute eight paired `log(B/A)` values;
2. primary statistic = median paired log ratio;
3. robust null bound = `abs(median_log_bias) + 3 * 1.4826 * MAD(log_ratio)`;
4. convert to fractional effect;
5. campaign threshold = largest bound, rounded upward to 0.5%, minimum 1%.

Formal N003 timing claims additionally require >=75% same-direction pairs. A/A control must not trigger a claim. Worst p95 absolute pair effect must be <=20%, and the derived threshold must be <=20%.

Lane K's 5% and Lane L's 20% values are not imported as the N003 threshold. Samples cannot be deleted and a completed PASS calibration cannot be rerun for a more favorable threshold.

## Quality protocol

Quality interpretation was established and shown deterministic by v2 and is unchanged in v5.

Legacy `affected_pixel_fraction` remains diagnostic-only. Primary metrics are:

- `rgb_rms_error`;
- `p99_abs_luminance_error`;
- `scale_aware_affected_pixel_fraction`, with `abs_error >= 0.05 * max(abs(reference_luminance), 0.0001)`.

There is no aggregate winner score. Interpretation is scenario-by-scenario. A material quality change requires concordant movement in at least two of the three metrics; error metrics require >=10% relative change and scale-aware affected fraction requires >=0.005 absolute change. Individual black reference frames remain valid.

## Execution

v5 reuses `phos-n003-preflight`; no C++ rebuild is required beyond ensuring that target is current. Use `n003_gpu_profile.sh` to inspect/enable/restore the AMDGPU profile, then run `test_n003_preflight_v5_contract.py` and `run_n003_preflight_v5.py`.

N003 proper may start only after v5 passes and its derived timing threshold plus required GPU performance state are recorded in result truth.
