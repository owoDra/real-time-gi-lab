# Lane L — heavy-boundary timing calibration

Issue: #24  
Status: **COMPLETE — 20% heavy-boundary floor established**

Lane L calibrated paired GPU timing for the complete J002 heavy recurring
boundary. It did not rank topology backends.

## Final result

Accepted downstream measurement contract on
`AMD Radeon 8060S Graphics (RADV STRIX_HALO)`:

- environment: `dual-context`;
- primary axis: GPU timestamp;
- CPU wall: diagnostic / health / provenance only;
- minimum demonstrated heavy-boundary effect: **20%**;
- 4 warmup + 12 measured pairs;
- 8 fresh-process blocks;
- 16 complete transitions per timed sample;
- no sample exclusion;
- no instability rerun;
- no completed-campaign rerun.

## L001

L001 tested `dual-context` and
`single-context-independent-runtime` against the unchanged J004
1.02 / 1.03 / 1.02 same-variant control-health gate.

Both environments failed all required controls, so L001 concluded
`measurement-limited` and entered L002.

## L002

L002 acquired a fresh same-variant heavy-boundary campaign and applied frozen
analysis-only multiplicative B-role GPU effects:

- +20%;
- +10%;
- +5%.

Results:

- `dual-context`: +20% passed 10/10 controls, +10% passed 4/10, +5% passed 1/10;
- `single-context-independent-runtime`: +20% passed 9/10, +10% passed 3/10,
  +5% passed 0/10.

The frozen decision mapping therefore accepts `dual-context` with a **20%**
heavy-boundary floor.

## Canonical records

L001:

- `experiments/001-l001-heavy-boundary-calibration-plan.md`
- `experiments/002-l001-config.json`
- `experiments/003-l001-execution-freeze.json`
- `results/001-l001-pretarget-freeze.md`
- `results/002-l001-target-result.md`
- `results/003-l001-target-artifact-manifest.json`

L002:

- `experiments/004-l002-detectable-floor-plan.md`
- `experiments/005-l002-config.json`
- `experiments/006-l002-execution-freeze.json`
- `results/004-l002-pretarget-freeze.md`
- `results/005-l002-target-result.md`
- `results/006-l002-target-artifact-manifest.json`
- `results/007-lane-l-final.md`

## Downstream

Lane E / #22 is unblocked, but its target campaign must prospectively import this
20% heavy-boundary floor and `dual-context` environment before observing
candidate timing.

J004 remains `measurement-limited`. J005 remains forbidden.
