# N003 preflight/calibration — complete-frame comparison contract

Status: **v1/v2/v3/v4 timing-unsuitable; v5 withdrawn for target-host safety; replicated-median v6 next**

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

v4 materially improved several scenarios: static fell to ~17% p95, stable-topology deformation to ~8%, and topology/high-churn to ~9%. Residual robust noise was dominated by moving-rigid, where individual A/A pairs could still differ strongly even though geometry upload was comparatively stable.

## v5 withdrawal — safety constraint

The proposed v5 clock-pinned experiment was **withdrawn before any target run**. The target host can trigger a safety shutdown when its GPU performance profile is forced. Lane N therefore forbids changing GPU power/performance profiles for this research. The v5 executable runner/helper were removed from the current branch; its config remains only as a tombstone stating that it must not be executed.

## Timing protocol v6 — replicated median, normal GPU policy

v6 keeps the v4 probe binary and does not modify GPU power, clock, DPM, fan, thermal, or firmware policy.

The measurement unit is changed prospectively from one A/A pair per block to a **five-micro-pair block**:

1. each micro-pair is the existing v4 hot-adjacent measurement: one validated source frame, 31 additional source warm-ups, then the measured target transition;
2. A/B order alternates inside the block, beginning from the frozen outer-block order;
3. all five raw micro-pairs are retained;
4. for each scenario and timing axis, compute `log(B/A)` for all five micro-pairs;
5. the block sample is the **median of those five log ratios**;
6. repeat for eight outer blocks;
7. apply the same robust median/MAD calibration to the eight block samples.

This is not sample deletion. A transient one-off timing excursion remains in raw evidence but cannot define the block. If instability affects at least three of five micro-pairs, it moves the block median and remains visible to the formal gate.

The formal gates are not relaxed:

- derived material-change threshold <=20%;
- p95 absolute **block** effect <=20%;
- future formal current-vs-vanilla claims require >=75% same-direction outer blocks;
- A/A control must not trigger a formal claim;
- stage active/inactive mismatches remain a failure;
- completed PASS rerun budget remains zero;
- no raw micro-pair may be deleted or excluded.

Raw micro-pair p95 is retained as diagnostic-only. Stage diagnostics are also aggregated as median-of-five micro-pair ratios per outer block before p95 reporting.

N003 proper must use the same five-micro-pair/eight-block protocol if v6 passes.

## Quality protocol

Quality interpretation remains accepted from v2 and unchanged:

- legacy `affected_pixel_fraction` is diagnostic-only;
- primary metrics: `rgb_rms_error`, `p99_abs_luminance_error`, and scale-aware affected fraction;
- scale-aware threshold: `abs_error >= 0.05 * max(abs(reference_luminance), 0.0001)`;
- a material quality change requires concordant movement in >=2/3 primary metrics;
- no aggregate winner score;
- individual black reference frames remain valid.

## Execution

v6 reuses `phos-n003-preflight`; no new renderer/C++ change is required. Run `test_n003_preflight_v6_contract.py`, the v6 contract phase, then `run_n003_preflight_v6.py --phase target` through the research experiment wrapper.

N003 proper may start only after v6 passes and its derived timing threshold is committed to result truth.
