# 045: calibrated timing (MDE 5%) — matched-quality reconstruction faster on 3/6, PT16R dominates ReSTIR 6/6

**CALIBRATED_MDE5_T1_ACCEPTED_FASTER_3_6_INCONCLUSIVE_3_6_PT16R_DOMINATES_RSR_6_6.**
Registration [045](../experiments/045-timing-protocol-revision-32-pairs.md)
`9ffb32fd` (single change from 044: 32 measured pairs per comparison per
process) precedes implementation `203e7c30`; evidence
[summary256](256-final-timing-revision-summary.json),
[verification258](258-final-timing-revision-verification.json). 044 stays
TIMING_INCONCLUSIVE; this result does not revalidate it.

## Calibration

8 fresh processes, three neutral sizes (tiny ~0.73 ms, short ~5.4 ms, multi
16×~1.3 ms). Controls pass at every size (|process medians| ≤0.5%, max order
bias 0.7/1.7/1.6% ≤2%); +5/+10/+20% deltas measure 1.050/1.100/1.200 within
0.2% with all process effects above the control envelope. **Accepted minimum
detectable effect: 5%** on this harness/device. T1 threshold = log 1.20.

## Decisions (8 processes × 32 pairs per comparison and target)

| Target | T1 PTR/PT_REF | T1 | RSR/PT1R | RSR/PT4R | RSR/PT16R | T4 | Owned role buffers PT_REF / PTR / RSR (MB) |
|---|---:|---|---:|---:|---:|---|---|
|H01/B2|0.463|**FASTER**|1.37|1.33|1.20|PT16R dominates|3.9 / 25.8 / 72.6|
|H01/B8|0.090|INCONCLUSIVE (order bias 4.7%)|1.77|1.59|1.21|PT16R dominates|3.9 / 25.8 / 100.2|
|H02/B2|0.487|INCONCLUSIVE (5.5%)|1.38|1.31|1.13|PT16R dominates|3.9 / 25.8 / 72.6|
|H02/B8|0.081|INCONCLUSIVE (5.9%)|1.76|1.54|1.05 (n.s.)|PT16R dominates|3.9 / 25.8 / 100.2|
|H03/B2|0.676|**FASTER**|1.35|1.32|1.20|PT16R dominates|3.9 / 25.8 / 72.6|
|H03/B8|0.100|**FASTER**|1.73|1.59|1.28|PT16R dominates|3.9 / 25.8 / 100.2|

- **T1, matched quality (both configurations pass all M001 gates):** PT plus
  the fixed quadratic reconstruction at the 022 rung is accepted faster than raw
  PT at its first passing rung on H01/B2 (2.2×), H03/B2 (1.48×) and H03/B8
  (10.0×). The other three have all 8 process effects in the same direction
  (11–12× and 2.1×) but exceed the frozen 3% candidate order-bias limit and
  stay INCONCLUSIVE. Shared scene/AS allocations are 0.65–0.66 MB. At matched
  quality the reconstruction role owns 6.6× more buffer memory (25.8 vs 3.9 MB,
  dominated by 17.3 MB float32 coefficients): a time-for-memory tradeoff, no
  memory superiority.
- **T4, equal cost:** PT16+reconstruction is significantly cheaper than ReSTIR
  V1+reconstruction on 5 targets (RSR 1.13–1.28×) and not significantly
  different on H02/B8 (1.05× < MDE), while its published per-frame indirect
  error is 24–39% lower on all six: **PT16R dominates RSR 6/6**.
- T2/T3: RSR is significantly more expensive than PT1R/PT4R wherever the cost
  decision is defined (tradeoff: better quality at 1.3–1.8× cost). The
  registered dominance rule labels H01/B2-T2 and three B8 T3 cases
  "RSR_DOMINATES" only because their cost decision is INCONCLUSIVE through the
  order-bias criterion; all 8 process effects there show RSR 1.33–1.77× MORE
  expensive. These labels are recorded but are not equal-cost wins.

## Scope

First accepted calibrated GPU-time results in Lane M, limited to: one AMD
Radeon 8060S/RADV, 320×180, static M001 targets, GPU timestamps of complete
frame submits (CPU wall diagnostic), known components (no novelty), raw PT as
the matched-quality comparator because every tested denoised/probe/RC/ReSTIR
family fails the gates. Not a general architecture win; dynamic, Sponza,
new-heldout, multi-device and deployability gates remain unmet. 56 GPU
processes; GPU count328.
