# N003 preflight/calibration — complete-frame comparison contract

Status: **v1/v2/v3/v4/v6 timing-unsuitable; v5 withdrawn for target-host safety; moving-rigid workload diagnostic next**

Issue: #31  
Parent: #26  
Input baseline: N002 complete at `0188c7f7b4b43e5d887cd753d74a69e11a2ea764`

## Purpose

This is Lane N's preflight for N003 proper. It freezes how current-vs-vanilla timing and quality may be interpreted before N003 proper is measured.

## Retained evidence

- **v1 absolute fresh-process** (`422945ea...`): 48.297% worst noise, 145% derived threshold, `timing-unsuitable`.
- **v2 paired fresh-process A/A** (`aa46afd1...`): 110% threshold, ~97% worst p95, `timing-unsuitable`; quality interpretation accepted.
- **v3 same-process prewarm** (`ac143a56...`): 207.5% threshold, 82.3% worst p95, `timing-unsuitable`; exposed the misplaced validation boundary and stage-level performance-state behavior.
- **v4 hot-adjacent same-process A/A** (`8f9c78bd...`): all 8 pairs retained, zero false formal claims, 98.5% threshold and 27.2% worst complete-frame p95, `timing-unsuitable`.
- **v6 replicated median** (`00248643...` target evidence): all 40 micro-pairs retained, zero A/A formal-claim triggers, worst p95 block effect 18.4% (inside the 20% gate), but derived threshold 28.5%, therefore `timing-unsuitable`.

v6 materially stabilized every scenario except moving-rigid. Camera/static/stable/topology block-level noise fell to low single-digit or modest single-digit percentages; moving-rigid complete-frame robust noise remained about 28%. Its geometry-upload block diagnostic remained stable while frame-init/visibility showed large residual variation. Increasing replication again is not justified until workload-count invariance is checked.

## v5 withdrawal — safety constraint

The proposed v5 clock-pinned experiment was **withdrawn before any target run**. The target host can trigger a safety shutdown when its GPU performance profile is forced. Lane N therefore forbids changing GPU power/performance profiles for this research. The v5 executable runner/helper were removed from the current branch; its config remains only as a tombstone stating that it must not be executed.

## v6 protocol — retained failed evidence

v6 kept normal host GPU policy and used five hot-adjacent A/A micro-pairs per outer block, eight outer blocks total. All 40 micro-pairs were retained; each block sample was the median of its five `log(B/A)` values, then the existing median/MAD calibration was applied across eight block samples.

Formal gates were unchanged:

- derived material-change threshold <=20%;
- p95 absolute block effect <=20%;
- future formal current-vs-vanilla claims require >=75% same-direction outer blocks;
- A/A control must not trigger a formal claim;
- no raw micro-pair deletion/exclusion;
- GPU profile changes forbidden.

v6 failed only the derived-threshold ceiling: 28.5% versus 20%. This result is retained and must not be reinterpreted as PASS.

## Moving-rigid workload-invariance diagnostic

Before changing the timing estimator again, Lane N now checks whether the measured moving-rigid work itself is deterministic.

The diagnostic uses a dedicated `phos-n003-workload-diagnostic` target and eight paired fresh-runtime measurements with the same 32-frame source warm-up. For both the final source frame and first measured target transition it records every integer `I001FrameStats` counter:

- work/output and requested counts;
- overflow and visible owners;
- moved primitives and segment/hierarchy update counts;
- topology/rebuild counts;
- storage allocation/update/invalidation/failure counts.

The gate is exact integer invariance across A/B and across all eight blocks. Timing is diagnostic-only. No GPU power/performance setting is read as a requirement or modified.

Interpretation is binary:

- **counter mismatch** -> investigate moving-rigid workload/synchronization nondeterminism before further timing calibration;
- **all counters invariant** -> the residual v6 timing variation is not explained by measured workload-count drift, so the next calibration should target execution-time state using non-invasive methods only (for example read-only telemetry or an adjacent fixed sentinel workload).

## Quality protocol

Quality interpretation remains accepted from v2 and unchanged:

- legacy `affected_pixel_fraction` is diagnostic-only;
- primary metrics: `rgb_rms_error`, `p99_abs_luminance_error`, and scale-aware affected fraction;
- scale-aware threshold: `abs_error >= 0.05 * max(abs(reference_luminance), 0.0001)`;
- a material quality change requires concordant movement in >=2/3 primary metrics;
- no aggregate winner score;
- individual black reference frames remain valid.

## Execution

Build `phos-n003-workload-diagnostic`, run `test_n003_moving_workload_contract.py`, then run `run_n003_moving_workload_diagnostic.py --phase target` through the research experiment wrapper.

N003 proper remains blocked until the moving-rigid cause is resolved and a timing calibration passes prospectively.
