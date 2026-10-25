# 046 / M002: new heldouts and changed camera/light states — generalization NOT held

**M002_QUALITY_GENERALIZATION_NOT_HELD_PTR_6_12_SPEED_GENERALIZATION_NOT_HELD_FASTER_2_6.**
Registration [046](../experiments/046-m002-new-heldout-and-dynamic-validation.md)
`f4e9434e`, [046a](../experiments/046a-capture-details-and-positive-control.md)
`d3313085`; closure criteria [047](../experiments/047-lane-m-closure-criteria.md)
`b7375747` were fixed before any M002 result. Evidence [summary259](259-m002-summary.json),
[verification261](261-m002-verification.json).

## Setup

Eight unseen CPU-exported states (exporter reproduces M001 H01 bytes exactly):
S1 leak thin 0.071, S2 leak one-sided, S3 world sparse, S4 world large-horizontal,
plus camera-motion and light-motion states of S1 and S3; each at B2/B8.
References: unchanged N010 RQMC oracle and N007 admission ladder. **12/16
eligible**; S3 and S3C (both depths) stay REFERENCE_INELIGIBLE through
262144spp and are not scored. Positive control on M001 H01/B2 passes (PT256
indirect 9.73%, PTR16 8.76%).

## Quality (one fixed-seed image per rung, unchanged gates)

| Target | PT first pass | PTR first pass | PTR indirect NRMSE at 64spp |
|---|---|---|---:|
|S1/B2|256|16|—|
|S1/B8|1024|16|—|
|S2/B2|1024|16|—|
|S2/B8|1024|16|—|
|S1C/B2 (camera)|1024|64|5.1%|
|S1C/B8 (camera)|1024|64|5.6%|
|S4/B2|1024|FAIL|28.6%|
|S4/B8|1024|FAIL|27.9%|
|S1L/B2 (light)|1024|FAIL|13.7%|
|S1L/B8 (light)|1024|FAIL|13.6%|
|S3L/B2 (light)|FAIL|FAIL|94.4%|
|S3L/B8 (light)|FAIL|FAIL|92.0%|

PTR passes 6/12 eligible targets; PT passes 10/12. The fixed geometry-only
reconstruction fails on the box-field scene S4 and on both light-motion
states; the prediction "PTR passes on most targets" did not hold.

## Timing (fresh 045-protocol calibration: control PASS, MDE 5%)

| Matched target | PTR/PT cost | Decision |
|---|---:|---|
|S1/B2 (16 vs 256)|0.457|**FASTER**|
|S1C/B2 (64 vs 1024)|0.157|**FASTER**|
|S1/B8 (16 vs 1024)|0.047|INCONCLUSIVE (order bias 11%)|
|S2/B2 (16 vs 1024)|0.181|INCONCLUSIVE (span/order bias)|
|S2/B8 (16 vs 1024)|0.072|INCONCLUSIVE (order bias 7.1%)|
|S1C/B8 (64 vs 1024)|0.094|INCONCLUSIVE (order bias 3.7%)|

All 8 process effects favour PTR on every matched target, but only 2/6 pass the
frozen stability criteria; the registered majority rule is NOT held. ReSTIR+
reconstruction again costs 1.19–1.43× PT16+reconstruction.

## Notes

Operational refusals before any GPU work are preserved: control v1 (quiet gate,
reference oracles active) and the first calibrate call (stale input pin; build
v2 is byte-identical). 137 GPU processes; GPU count 465. Stateless roles only:
no temporal history, rigid/deforming/topology motion, AS update cost or Sponza.
One GPU. No novelty or architecture claim.
