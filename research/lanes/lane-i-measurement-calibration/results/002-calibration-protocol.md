# I002 — frozen calibration protocol

## Formal status

**Accepted/frozen before I003 target timing.**

## Canonical configuration

- Plan: `lane-i-i002-v1`
- Config: `research/lanes/lane-i-measurement-calibration/experiments/002-calibration-protocol-config.json`
- Freeze commit: `08be651119e5c209b18eb79cdfd1608e8396237c`

## Frozen structure

Accepted timing uses:

- 8192 elements;
- 16 dependent dispatches per timed batch;
- 4 warmup pairs;
- 12 measured pairs;
- 8 fresh-process blocks;
- counterbalanced comparison positions and AB/BA starts;
- 1 second settle between processes;
- zero instability reruns;
- no sample exclusion;
- validation layers disabled for accepted timing.

The tested deltas are +5%, +10%, and +20% controlled work.

## Frozen decision discipline

For each pair, the primary effect is `log(B/A)`. Each fresh process contributes the median of its 12 paired log ratios.

A candidate is detected only when every fresh-process median exceeds the control noise envelope and the frozen positive-fraction, effect-span, and AB/BA order-bias gates pass.

Resolution must be contiguous: +20% must pass before +10%, and +20% plus +10% must pass before +5%. A non-monotonic pattern is inconclusive.

Both GPU timestamps and complete CPU wall are retained as decision axes. Host observations and the one-dispatch campaign are diagnostic-only.

No threshold or structural parameter may be changed after the first accepted I003 target artifact.
