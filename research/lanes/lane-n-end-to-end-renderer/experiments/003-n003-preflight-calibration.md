# N003 preflight/calibration — complete-frame comparison contract

Status: **v1 absolute-time calibration timing-unsuitable; paired-control v2 target pending**

Issue: #31  
Parent: #26  
Input baseline: N002 complete at `0188c7f7b4b43e5d887cd753d74a69e11a2ea764`

## Purpose

This is part of Lane N and is the preflight for N003, not a separate lane. It freezes how N003 may interpret performance and image-quality differences before the vanilla Split RC comparison is measured.

## v1 result and why it is not the final protocol

The first target calibration at commit `422945ea32164e487e8562214dc7568f6e2ad9a6` repeated one absolute complete-frame sample per scenario across six fresh N002 processes. It retained all samples and correctly concluded `timing-unsuitable`:

- worst absolute across-process timing noise: **48.297%**;
- derived material-change threshold: **145.0%**;
- scale-aware quality signal: present.

That artifact is retained as valid diagnostic evidence. It is not deleted, filtered, or reinterpreted as a PASS.

The v1 statistic, however, does not match the intended N003 decision unit. N003 compares current architecture vs vanilla Split RC under a paired complete-frame boundary. Absolute run-to-run GPU clock/DVFS variation therefore inflated v1's noise estimate even when such common-mode variation could cancel in a paired comparison.

The protocol is prospectively revised before any current-vs-vanilla measurement. v2 calibrates the actual future decision unit with current-vs-current A/A pairs.

## Timing protocol v2

Run eight fresh-process pair blocks. Each block executes the unchanged N002 full six-scenario baseline twice in immediate sequence:

- A = current architecture;
- B = the same current architecture control.

Each A and B member must independently pass N002 correctness/provenance/reference validation. There is no sample deletion and no timing-only rerun.

For every scenario and each primary timing axis (`complete_gi_gpu`, `complete_renderer_gpu`):

1. compute paired `log(B/A)` for all eight blocks;
2. primary statistic = median paired log ratio;
3. estimate robust null spread using `MAD(log ratio)`;
4. calibrated noise log = `abs(median_log_bias) + 3 * 1.4826 * MAD`;
5. convert that multiplicative log bound back to a fractional effect;
6. the campaign threshold is the largest such bound across every scenario/axis, rounded upward to 0.5%, with a 1% minimum.

A future N003 formal timing claim additionally requires at least 75% of paired effects to agree in direction. A/A control must not itself satisfy the formal-claim rule.

As a second sanity gate, the worst p95 absolute A/A pair effect across scenario/axis must be at most 20%. If the derived material-change threshold exceeds 20%, or this p95 control ceiling is exceeded, the boundary remains timing-unsuitable.

This is not a relaxation of the failed v1 threshold. It changes the estimator to match the comparison unit that N003 will actually use. Lane K's 5% and Lane L's 20% values are not imported as a performance threshold.

## Quality protocol

N002 showed that the legacy affected-pixel metric was not useful for this workload: its fixed absolute luminance gate of 0.01 is above the radiance scale observed in the six baseline frames. The metric is retained for historical diagnostics but is not primary in N003.

N003 adds `scale_aware_affected_pixel_fraction`. A pixel is affected when:

`abs(output_luminance - reference_luminance) >= 0.05 * max(abs(reference_luminance), 0.0001)`

The three primary quality metrics are:

- `rgb_rms_error`;
- `p99_abs_luminance_error`;
- `scale_aware_affected_pixel_fraction`.

There is no aggregate winner score. N003 interprets each scenario separately. A material quality change requires concordant movement in at least two primary metrics. For the two error metrics the change must be at least 10% relative; for scale-aware affected fraction the absolute fraction change must be at least 0.005. Individual black reference frames remain valid and cannot be excluded.

## Execution

Run the GPU-independent contract test, then the paired-control target through `scripts/research/run_experiment.py`. The v1 failed artifact remains under `out/research/` and the v2 campaign gets a separate timestamped artifact root.

The preflight emits:

- `n003-preflight-config.json`;
- `n003-preflight-progress.json`;
- `n003-preflight-raw.json`;
- `n003-preflight-summary.json`.

N003 proper may start only after v2 passes and its derived timing threshold is recorded in Lane N's result truth.
