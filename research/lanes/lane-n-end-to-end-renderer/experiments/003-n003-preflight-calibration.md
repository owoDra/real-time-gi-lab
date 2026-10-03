# N003 preflight/calibration — complete-frame comparison contract

Status: **v1/v2/v3 timing-unsuitable; paired-control v4 target pending**

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

Commit `ac143a567a056ff520e6f5ff73904c58196e989b`: all eight pair blocks completed with no sample exclusion, but timing remained unsuitable:

- derived threshold: **207.5%**;
- worst p95 complete-frame A/A effect: **82.3%** (`static`);
- A/A formal-claim trigger count: **0**;
- static/camera showed large early-frame swings;
- dynamic scenarios also showed intermittent `geometry_prepare_upload` inflation.

Stage evidence localized the instability. In static, slow samples inflated `renderer_prerequisite_attributable_to_gi`, `frame_init_visibility`, `producer`, and `ray_prepare` together. Stable/deforming cases also showed occasional approximately 2x geometry upload cost. This is consistent with the GPU not remaining in the same performance state across the measurement boundary, rather than one bad timestamp query.

v3 also exposed a diagnostics-only bug: the `synchronization` remainder can be floating-point noise around `1e-13 us`; treating that as an active stage produced meaningless ratio/mismatch diagnostics. It never explains the complete-frame failure.

All failed artifacts remain valid diagnostic evidence. None are deleted, filtered, or rewritten as PASS.

## Timing protocol v4

v4 keeps the same complete renderer/GI boundaries and **does not relax any statistical performance gate**. Only the harness adjacency and stage-diagnostic floor change prospectively.

For each A/B role and scenario:

1. create a fresh accepted `I001Runtime`;
2. run one unmeasured source-state frame and validate source correctness;
3. run the remaining 31 unmeasured source-state warm-up frames;
4. immediately execute the single measured target-state transition with no validation/reference work inserted between the final warm-up and measurement;
5. validate the measured target frame after the timing boundary closes.

Thus the measured moving-rigid, stable-topology-deforming, and topology-changing/high-churn paths still execute their real update/rebuild exactly once. The change only removes v3's reference-validation workload from the warm-up/measurement boundary.

Eight fresh process pair blocks remain. AB/BA order remains frozen as `AB, BA, AB, BA, BA, AB, BA, AB`. Stage timings remain diagnostic. Values below **1 us** are stage-diagnostic inactive so floating-point remainder noise cannot create false zero mismatches; this floor does not alter complete-frame timing samples or the formal timing threshold.

For each scenario and each of `complete_gi_gpu` / `complete_renderer_gpu`:

1. compute eight paired `log(B/A)` values;
2. primary statistic = median paired log ratio;
3. robust null bound = `abs(median_log_bias) + 3 * 1.4826 * MAD(log_ratio)`;
4. convert to fractional effect;
5. campaign threshold = largest bound, rounded upward to 0.5%, minimum 1%.

Formal N003 timing claims additionally require >=75% same-direction pairs. A/A control must not trigger a claim. Worst p95 absolute pair effect must be <=20%, and the derived threshold must be <=20%.

Lane K's 5% and Lane L's 20% values are not imported as the N003 threshold. Samples cannot be deleted and a completed PASS calibration cannot be rerun for a more favorable threshold.

## Quality protocol

Quality interpretation was established and shown deterministic by v2 and is unchanged in v4.

Legacy `affected_pixel_fraction` remains diagnostic-only. Primary metrics are:

- `rgb_rms_error`;
- `p99_abs_luminance_error`;
- `scale_aware_affected_pixel_fraction`, with `abs_error >= 0.05 * max(abs(reference_luminance), 0.0001)`.

There is no aggregate winner score. Interpretation is scenario-by-scenario. A material quality change requires concordant movement in at least two of the three metrics; error metrics require >=10% relative change and scale-aware affected fraction requires >=0.005 absolute change. Individual black reference frames remain valid.

## Execution

Build `phos-n003-preflight`, run `test_n003_preflight_v4_contract.py`, then run `run_n003_preflight_v4.py` through the research experiment wrapper. v1/v2/v3 artifacts remain untouched under `out/research/`.

N003 proper may start only after v4 passes and its derived timing threshold is recorded in result truth.
