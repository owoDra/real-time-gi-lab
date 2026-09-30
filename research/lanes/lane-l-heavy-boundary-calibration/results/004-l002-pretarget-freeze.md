# L002 — pre-target execution freeze

## Status

**READY FOR L002 TARGET EXECUTION**

No L002 target timing has been observed.

L001 completed with no usable environment, satisfying the prospectively declared
L002 entry condition.

## Frozen experiment

L002 acquires a fresh same-variant heavy-boundary campaign under both L001
measurement environments, then applies deterministic analysis-only multiplicative
effects to the B-role GPU timestamps:

- +20%;
- +10%;
- +5%.

Recorded raw GPU timing is never overwritten. CPU wall is not injected.

The experiment remains architecture-neutral and contains no candidate backend.

## Frozen detector

For each environment × profile × control family, the injected factor must be
strictly larger than the fresh same-variant control noise envelope:

`max(max-abs process median, process-median span, max order bias)`.

Additionally:

- all 8 process median ratios must remain > 1;
- both AB and BA stratum medians must remain > 1 in every process;
- minimum positive-pair fraction per process is 0.75;
- all five profiles × both controls must pass independently;
- no profile averaging;
- detection is contiguous +20 -> +10 -> +5.

The accepted floor is the smallest contiguous passing effect.

If neither environment detects +20% across every required control, Lane L
concludes that this target/method is unsuitable for architecture claims at or
below 20% on the heavy recurring boundary.

## Source freeze

Canonical identities are stored in
`experiments/006-l002-execution-freeze.json`.

## Target command

```bash
mise exec -- python scripts/research/run_experiment.py \
  --lane lane-l-heavy-boundary-calibration \
  --experiment 002-heavy-boundary-detectable-floor \
  --command "mise run research:l002:formal"
```

The task runs GPU-independent L002 tests first, builds the already-frozen L001
formal heavy-boundary executable, performs 20 validation executions, then 160
fresh timing processes.

Any pre-timing compile/test defect may be corrected and prospectively refrozen
only if no L002 target timing has been observed. Once timing begins, the zero
rerun budget applies.
