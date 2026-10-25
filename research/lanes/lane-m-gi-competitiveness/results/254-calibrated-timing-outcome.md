# 044: calibrated frame timing — control order bias fails, all decisions TIMING_INCONCLUSIVE

**CALIBRATION_CONTROL_ORDER_BIAS_FAIL_ALL_TARGET_TIMINGS_INCONCLUSIVE_DESCRIPTIVE_RECORDED.**
Registration [044](../experiments/044-calibrated-matched-quality-and-equal-cost-timing.md)
`1f900a16` with [044a](../experiments/044a-timing-development-disclosure.md),
[044b](../experiments/044b-calibration-boundary-sizes.md),
[044c](../experiments/044c-equal-cost-comparator.md) and
[044d](../experiments/044d-pair-order-counterbalance-correction.md); evidence
[summary253](253-calibrated-timing-summary.json), [verification255](255-calibrated-timing-verification.json).
No accepted speed or memory claim follows.

## What ran

- One host times complete frames of five roles on each admitted target with
  exact 022/041/042 SPIR-V: raw PT at its first-pass rung (PT_REF), PT+fixed
  quadratic reconstruction at the 022 rung (PTR), PT1R/PT4R/PT16R, and ReSTIR
  V1 + reconstruction (RSR). Cost = summed GPU timestamps of each role's submits.
- **Stop v1** (preserved): the first registered calibration completed 8 native
  processes, then analysis stopped INVALID because the host's AB/BA parity was
  constant per comparison inside a process (even comparison count). 044d fixed
  the rule (AB iff pair+process even); preparation, calibration and targets ran
  again under new `-v2` roots. Four disclosed development processes are
  inventoried and unused.
- Calibration v2 (8 fresh processes, tiny ~0.73 ms / short ~5.4 ms / multi 16×
  ~1.3 ms): every +5/+10/+20% neutral delta is measured within ~1% and has all
  8 process effects above the control envelope, but the control's max
  within-process order bias is 2.4% (short) and 4.2% (multi) against the frozen
  Lane-K limit 2%. Control fails => no minimum detectable effect => every target
  decision is TIMING_INCONCLUSIVE, as registered. Pooled position effects are
  only 0.0–0.6%; the failing statistic is the 6+6-pair per-process order bias.
- 48 target processes (6 targets × 8) completed with zero teardown; owned true
  peak with all roles resident 74.3–101.9 MB.

## Descriptive results (not accepted)

| Target | T1 PTR / PT_REF cost | PT_REF ms | PTR ms | RSR ms | PT16R ms | RSR / PT1R | RSR / PT4R | RSR / PT16R | Indirect NRMSE RSR / PT4R / PT16R |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---|
|H01/B2|0.46|1.62|0.75 (16spp)|0.90|—|1.38|1.34|1.20|14.0 / 16.7 / 8.5%|
|H01/B8|0.092|21.1|1.95|1.21|1.00|1.76|1.59|1.21|15.3 / 21.1 / 10.8%|
|H02/B2|0.49|2.56|1.25|0.92|0.81|1.39|1.32|1.13|15.0 / 21.2 / 11.4%|
|H02/B8|0.081|32.6|2.68|1.23|1.18|1.72|1.52|1.04|16.2 / 23.8 / 12.1%|
|H03/B2|0.69|1.47|1.02|0.93|0.78|1.34|1.31|1.20|23.0 / 26.4 / 14.0%|
|H03/B8|0.10|16.8|1.70|1.22|0.96|1.73|1.59|1.27|25.0 / 30.2 / 15.8%|

(H01/B2's PTR is the 16spp role; PT16R timing there is the same role.)

- Matched quality (both pass the gates): PT+reconstruction at 16/64spp needs
  0.46–0.69× raw PT's B2 frame cost and 0.08–0.10× at B8 (all 8 process
  effects same sign, spans ≤0.043). This is the largest effect seen in Lane M,
  but formally inconclusive under the registered calibration and limited to
  known components (no novelty).
- Equal cost: RSR costs 1.04–1.27× PT16R while PT16R's published indirect
  error is 24–39% lower on every target; PT16R descriptively dominates RSR.
  RSR beats PT4R in quality at 1.3–1.6× its cost (tradeoff). At 320×180 in
  these mostly-escaping scenes, the SDK reuse passes cost about as much as
  17–40 extra paths per pixel.
- Frames are 0.65–2.7 ms except raw PT at 1024spp; fixed dispatch overheads
  dominate. No extrapolation to other resolutions, scenes or GPUs.

044 ends. A separately registered protocol revision may address the
per-process order-bias statistic; otherwise these timings remain diagnostic.
Lane M remains incomplete.
