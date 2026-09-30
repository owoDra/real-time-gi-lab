# Lane L — heavy-boundary timing calibration

Issue: #24  
Status: **L002 FROZEN — READY FOR TARGET EXECUTION**

Lane L calibrates paired GPU timing for the complete J002 heavy recurring
boundary. It does not rank topology backends.

## L001 — measurement environment calibration

L001 compared:

- `dual-context`;
- `single-context-independent-runtime`.

Both primary and software incumbent controls were measured across all five J002
profiles under the unchanged J004 1.02 / 1.03 / 1.02 control-health gate.

Target outcome: **measurement-limited**.

- 20/20 validation rows passed;
- 160/160 timing processes completed;
- all samples were retained;
- both environments failed every required GPU control;
- no reusable L001 timing environment was established;
- the single-context hypothesis was not sufficient to explain/fix J004 noise.

Canonical L001 records:

- `experiments/001-l001-heavy-boundary-calibration-plan.md`
- `experiments/002-l001-config.json`
- `experiments/003-l001-execution-freeze.json`
- `results/001-l001-pretarget-freeze.md`
- `results/002-l001-target-result.md`
- `results/003-l001-target-artifact-manifest.json`

## L002 — detectable-effect floor

Because both L001 environments failed, L002 is now allowed and frozen.

L002 acquires a fresh same-variant heavy-boundary campaign in both environments
and applies analysis-only multiplicative effects to B-role GPU timestamps:

- +20%;
- +10%;
- +5%.

Raw measurements are not modified and CPU wall remains diagnostic-only.

An injected effect must exceed the fresh control noise envelope and maintain
positive direction in every process and both AB/BA strata, with minimum
positive-pair fraction 0.75. All five profiles × both control families must pass
independently. Detection is contiguous +20 -> +10 -> +5.

Canonical L002 records:

- `experiments/004-l002-detectable-floor-plan.md`
- `experiments/005-l002-config.json`
- `experiments/006-l002-execution-freeze.json`
- `results/004-l002-pretarget-freeze.md`

J004 remains immutable. J005 remains forbidden. Lane E / #22 remains blocked
until L002 establishes a usable heavy-boundary floor or concludes that target
timing is unsuitable up to 20%.
