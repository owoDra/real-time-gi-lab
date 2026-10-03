# N003 preflight/calibration — complete-frame comparison contract

Status: **complete — scenario-scoped timing eligibility frozen before N003 proper**

Issue: #31  
Parent: #26  
Input baseline: N002 complete at `0188c7f7b4b43e5d887cd753d74a69e11a2ea764`

## Purpose

Freeze how current-vs-vanilla timing and image-quality differences may be interpreted before N003 proper is measured.

## Retained calibration evidence

- v1 absolute fresh-process: 145% global threshold, timing-unsuitable.
- v2 paired fresh-process A/A: 110%, timing-unsuitable; quality interpretation accepted.
- v3 same-process prewarm: 207.5%, timing-unsuitable.
- v4 hot-adjacent same-process A/A: 98.5%, timing-unsuitable.
- v5 clock-pinned proposal: withdrawn before any target run because changing the target GPU performance profile can trigger host safety shutdown.
- v6 replicated median: five micro-pairs per outer block, eight blocks, all 40 samples retained, zero false formal claims, worst p95 block effect 18.4%, but global threshold 28.5% because moving-rigid remained noisy.

The follow-up moving-rigid workload diagnostic completed all eight blocks and proved exact integer workload-count invariance across A/B and blocks for both the final source frame and first target transition. Residual moving-rigid timing variation is therefore measurement/execution-state limited rather than workload-count drift.

GPU power/performance profile changes are forbidden. Host GPU policy remains unchanged.

## Frozen N003 timing contract

The comparison and the quality interpretation are scenario-by-scenario, so timing eligibility is also frozen scenario-by-scenario before any current-vs-vanilla target data is collected.

The v6 measurement/statistical contract remains unchanged:

- primary timing axis: GPU timestamp;
- CPU wall: diagnostic only;
- five micro-pairs per outer block;
- eight outer blocks;
- block sample = median of five paired `log(B/A)` values;
- robust bound = `abs(median_log_bias) + 3 * 1.4826 * MAD(log_ratio)`;
- threshold rounded upward in 0.5% steps with 1% minimum;
- suitability ceiling remains 20%;
- a formal timing claim requires >=75% same-direction outer blocks;
- no sample deletion or exclusion;
- no completed-PASS rerun for a more favorable threshold.

The worse calibrated complete-GI/complete-renderer axis determines one threshold for both axes in each eligible scenario:

| Scenario | Frozen threshold | Status |
| --- | ---: | --- |
| static | 7.0% | timing eligible |
| camera-motion | 1.5% | timing eligible |
| light-motion | 5.0% | timing eligible |
| moving-rigid | — | timing-inconclusive; no formal timing claim |
| stable-topology-deforming | 2.5% | timing eligible |
| topology-changing-high-churn | 1.5% | timing eligible |

Moving-rigid required a 28.5% v6 threshold, above the unchanged 20% suitability ceiling. Its timing may be retained only as descriptive evidence. It remains fully valid for correctness, workload, memory and image-quality comparison.

No cross-scenario aggregate timing winner may be reported.

## Quality protocol

Accepted from v2 and unchanged:

- legacy `affected_pixel_fraction` is diagnostic-only;
- primary metrics: `rgb_rms_error`, `p99_abs_luminance_error`, and scale-aware affected fraction;
- scale-aware threshold: `abs_error >= 0.05 * max(abs(reference_luminance), 0.0001)`;
- material quality change requires concordant movement in at least two of the three primary metrics;
- no aggregate winner score;
- individual black reference frames remain valid.

## Completion gate

Preflight is complete. N003 proper is authorized under this frozen scenario-scoped timing interpretation. No further preflight tuning, GPU-profile forcing, or post-hoc threshold relaxation is permitted.
