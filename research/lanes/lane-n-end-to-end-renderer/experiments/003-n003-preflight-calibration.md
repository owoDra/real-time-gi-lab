# N003 preflight/calibration — complete-frame comparison contract

Status: **target calibration pending**

Issue: #31  
Parent: #26  
Input baseline: N002 complete at `0188c7f7b4b43e5d887cd753d74a69e11a2ea764`

## Purpose

This is part of Lane N and is the preflight for N003, not a separate lane. It freezes how N003 may interpret performance and image-quality differences before the vanilla Split RC comparison is measured.

## Timing protocol

The accepted N002 six-scenario current architecture is repeated in six fresh process blocks on the target AMD Radeon 8060S. Every block must pass the N002 completion validator and retain the same Git/device/playback/scene provenance.

For every scenario, both complete boundaries are retained:

- `complete_gi_gpu`;
- `complete_renderer_gpu`.

GPU timestamps are the primary axis. CPU/host observations are diagnostic only. Samples may not be excluded and a completed PASS calibration may not be rerun just to obtain a more favorable threshold.

For each scenario/axis, compute the median across the six blocks and each sample's absolute relative deviation from that median. Let `worst_noise` be the maximum deviation over the complete campaign.

The N003 formal timing materiality floor is determined by the prospectively frozen equation:

`threshold = ceil_to_0.5_percent(max(1 percent, 3 * worst_noise))`

If the resulting threshold exceeds 20%, the complete-frame boundary is declared timing-unsuitable for formal N003 performance claims. The threshold is not replaced by Lane K's 5% or Lane L's 20% values.

## Quality protocol

N002 showed that the legacy affected-pixel metric was not useful for this workload: its fixed absolute luminance gate of 0.01 is above the radiance scale observed in the six baseline frames. The metric is retained for historical diagnostics but is not primary in N003.

N003 adds `scale_aware_affected_pixel_fraction`. A pixel is affected when:

`abs(output_luminance - reference_luminance) >= 0.05 * max(abs(reference_luminance), 0.0001)`

This preserves the existing 5% relative criterion and existing relative-luminance floor while removing the unrelated fixed 0.01 absolute gate.

The three primary quality metrics are:

- `rgb_rms_error`;
- `p99_abs_luminance_error`;
- `scale_aware_affected_pixel_fraction`.

There is no aggregate winner score. N003 interprets each scenario separately. A material quality change requires concordant movement in at least two primary metrics. For the two error metrics the change must be at least 10% relative; for scale-aware affected fraction the absolute fraction change must be at least 0.005. Individual black reference frames remain valid and cannot be excluded.

## Execution

First run the GPU-independent contract test and build the already-existing N002 targets. Then run the preflight through `scripts/research/run_experiment.py` so raw calibration artifacts remain under `out/research/`.

The preflight emits:

- `n003-preflight-config.json`;
- `n003-preflight-progress.json`;
- `n003-preflight-raw.json`;
- `n003-preflight-summary.json`.

N003 proper may start only after the target summary passes and the derived timing threshold is recorded in Lane N's result truth.
