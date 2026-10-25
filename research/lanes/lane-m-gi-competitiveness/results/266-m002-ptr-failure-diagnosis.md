# 048 outcome — why PT+reconstruction failed on M002

**DIAGNOSIS_COMPLETE.** Registration [048](../experiments/048-m002-ptr-failure-diagnosis.md)
`de9ba3a8`; script `m002_diagnosis.py`; record
[266 JSON](266-m002-ptr-failure-diagnosis.json). CPU only, existing images and
references only; no gate decision.

Disclosures: the control was smoke-run once on M001 before the full run
(`789f45f5`); the first full run stopped on a bug in a descriptive helper
(zero-direct division in a saved-PTR score, no output written), fixed in
`b8d81046` and run once more. After the record was written, a
descriptive (not registered) look at reference images and mask-rejection
reasons was made; it is reported below as such.

## Control

The CPU replica (oracle-built primary hits + unchanged 017 masks/018 fit)
reproduces all six archived M001 022 GPU final stages: zero primitive
mismatches, final-stage relative NRMSE 6e-7–1.7e-5 (bound 1e-3). PASS.

## Mechanisms (registered labels)

| Target | Labels | Op(ref) NRMSE | R₆₄ | mean gain / frac≥1 | top-0.1% share | hit pixels |
|---|---|---:|---:|---|---:|---:|
|S4/B2, S4/B8|NO_VARIANCE_REDUCTION, HEAVY_TAIL|0.0004/0.0002|1.00|0.93 / 45%|0.72/0.59|1.5%|
|S3L/B2, S3L/B8|NO_VARIANCE_REDUCTION, HEAVY_TAIL|0.0004|0.93|0.87 / 34%|0.80|1.1%|
|S1L/B2, S1L/B8|BIAS_FLOOR, HEAVY_TAIL|0.092/0.084|0.09/0.08|0.05 / 0%|0.36/0.33|12.7%|
|passing S1, S2, S1C|none|0.009–0.020|0.03–0.05|0.03–0.06 / ≤0.1%|0.12–0.16|12–13%|

Clip bias is ≤ +0.6% at 64 spp everywhere (not a failure cause). PT error
slopes are −0.48…−0.52 (pure Monte Carlo scaling) on every target.

1. **S4 and S3L — spatial reconstruction has nothing to reconstruct from.**
   The visible geometry is many distant small boxes covering 1.1–1.5% of the
   image in islands a few pixels wide; 34–45% of hit pixels keep only their
   own tap and the composed operator is close to the identity (R ≈ 0.93–1.0).
   PTR is therefore raw PT plus overhead, and raw PT itself is heavy-tailed
   (59–80% of the 1024-spp squared error in 0.1% of pixels; S3L indirect is
   only 1.5% of total RMS, so its relative indirect error is large).
2. **S1L — the operator's own bias.** Moving the light makes indirect
   lighting vary within planar regions in a way the geometry-only quadratic
   cannot represent: `Op(reference)` alone has 8.4–9.2% indirect NRMSE,
   almost the whole 10% gate. More samples cannot fix it.

## Consequence for the next candidate (design input, not evidence)

A screen-space spatial filter cannot be the variance-reduction mechanism for
sub-pixel-scale geometry, and a geometry-only spatial model is biased when
lighting changes. The next transport therefore must reduce variance per
surface point over time (or in world/object space) without lighting-blind
spatial blur, and must keep the light-motion case unbiased.
One GPU, M002 development data, no novelty or performance claim.
