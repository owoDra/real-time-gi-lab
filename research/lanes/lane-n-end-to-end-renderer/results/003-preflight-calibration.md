# N003 preflight/calibration result

Status: **complete — scenario-scoped timing eligibility frozen before N003 proper**

Issue: #31  
Parent: #26

## Evidence retained

- v1 absolute fresh-process: 145% global threshold, timing-unsuitable.
- v2 paired fresh-process A/A: 110%, timing-unsuitable; quality interpretation accepted.
- v3 same-process prewarm: 207.5%, timing-unsuitable.
- v4 hot-adjacent same-process A/A: 98.5%, timing-unsuitable.
- v5 clock-pinned proposal: withdrawn before target execution because changing the target GPU performance profile can trigger host safety shutdown.
- v6 replicated median: five micro-pairs per outer block, eight outer blocks, all 40 samples retained, zero false A/A formal claims, worst p95 block effect 18.4%, but global threshold 28.5% because moving-rigid remained noisy.
- moving-rigid workload-invariance diagnostic: all eight pair blocks completed and every required source/target integer workload counter was identical across A/B and all blocks.

The moving-rigid source frame was always 133344 work items, 16668 outputs and 4167 visible owners. The measured target transition was always 134816 work items, 16852 outputs, 4213 visible owners and 796 moved primitives, with 265 storage allocations and 169 invalidations. Residual moving-rigid timing variation is therefore not explained by measured workload-count drift.

GPU power/performance profile changes are forbidden for Lane N. The normal host GPU policy remains unchanged.

## Frozen timing interpretation for N003 proper

N003 is interpreted scenario-by-scenario. Calibration eligibility is therefore frozen scenario-by-scenario before any current-vs-vanilla target data is collected.

The v6 estimator and execution contract remain unchanged:

- GPU timestamps primary; CPU wall diagnostic only;
- five micro-pairs per outer block and eight outer blocks;
- block sample = median of the five paired log ratios;
- robust bound = absolute median block log bias plus 3 x 1.4826 x MAD;
- threshold rounded upward in 0.5% steps with 1% minimum;
- suitability ceiling remains 20%;
- formal claim also requires >=75% same-direction outer blocks;
- zero sample deletion/exclusion;
- no completed-PASS rerun for a more favorable threshold.

For each eligible scenario the worse of complete-GI and complete-renderer calibration determines one shared scenario threshold:

| Scenario | Frozen threshold | Timing interpretation |
| --- | ---: | --- |
| static | 7.0% | formal timing eligible |
| camera-motion | 1.5% | formal timing eligible |
| light-motion | 5.0% | formal timing eligible |
| moving-rigid | — | measurement-limited; no formal timing win/loss claim |
| stable-topology-deforming | 2.5% | formal timing eligible |
| topology-changing-high-churn | 1.5% | formal timing eligible |

The v6 moving-rigid calibration required 28.5%, above the unchanged 20% suitability ceiling. Raw moving-rigid timing remains descriptive evidence only. Moving-rigid remains fully eligible for correctness, workload, memory and image-quality comparisons.

No cross-scenario aggregate timing winner may be reported.

## Quality interpretation

Accepted from v2 and unchanged:

- legacy fixed-absolute `affected_pixel_fraction` is diagnostic-only;
- primary metrics are RGB RMS error, p99 absolute luminance error and scale-aware affected-pixel fraction;
- scale-aware affected pixel uses `abs_error >= 0.05 * max(abs(reference_luminance), 0.0001)`;
- a material quality change requires concordant movement in at least two of the three primary metrics;
- no aggregate winner score;
- individual black reference frames remain valid.

## Decision

The preflight is complete. N003 proper — current architecture versus fair vanilla Split Radiance Cascades under identical scene, transport, timing, memory and reference boundaries — is unblocked under the frozen scenario-scoped timing interpretation above.
