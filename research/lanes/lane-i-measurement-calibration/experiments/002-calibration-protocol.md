# I002 — frozen safe calibration protocol

Status: **FROZEN before accepted target timing**  
Plan: `lane-i-i002-v1`

The machine-readable source of truth is
`002-calibration-protocol-config.json`. Once an accepted I003 target campaign
starts, this protocol must not be changed for that campaign.

## Why this structure

Lane F/G/H already showed that short individual timings, extra warmup, and
architecture-specific paired runs were not sufficient. I002 therefore calibrates
an architecture-neutral kernel with a longer **same-command-buffer batch** and
adjacent baseline/candidate pairs. Fresh processes are retained as a separate
replication axis.

The frozen accepted workload uses:

- 8,192 invocations per dispatch;
- baseline 200 dependent iterations per invocation;
- +5/+10/+20 variants at 210/220/240 iterations;
- 16 dispatches per measured batch;
- 4 warmup pairs then 12 measured pairs per process;
- 8 fresh-process blocks per comparison;
- 1 second settle before each fresh process;
- validation layers disabled for accepted timing.

A diagnostic-only individual-dispatch campaign is also frozen: batch length 1,
control and +20 only, four fresh processes. It cannot promote the methodology
or alter any accepted threshold. It exists only to quantify whether batching
materially improves the same controlled workload.

## Counterbalancing

Each process contains alternating AB/BA pairs. A is always baseline; B is the
declared candidate, including baseline for the control comparison.

Across the eight accepted blocks, the comparison order is a balanced set of
four rotations plus their reverse orientation. Every comparison therefore
occupies each process slot twice. All warmup and measured samples are retained.

## Measurement boundaries

**GPU axis:** one timestamp interval around the complete controlled dispatch
batch. Deterministic state reset is outside the GPU interval.

**Wall axis:** `steady_clock` from before command-buffer reset/recording through
fence wait and timestamp retrieval. Deterministic state reset, submission, wait,
and recording overhead are therefore included. Checksum readback is excluded
from accepted timing.

The batch total is the primary raw timing. Per-process summaries retain median,
geometric mean, total-duration ratio, positive-pair fraction, and AB-vs-BA order
bias. No fastest subset or sample deletion exists.

## Frozen decision statistic

For every measured pair and axis:

`d = log(B / A)`.

For each fresh process the primary effect statistic is the median of its 12
paired log ratios.

### Baseline-control repeatability gate

The baseline-vs-baseline control must pass all axis-specific frozen limits:

- maximum absolute fresh-process median role ratio;
- span of the eight fresh-process median role ratios;
- maximum within-process AB-vs-BA median bias.

GPU limits are 1.02 / 1.03 / 1.02. Wall limits are 1.03 / 1.05 / 1.03.

The **control noise envelope** is the largest absolute baseline-control
fresh-process median log ratio observed on that axis. This is a predeclared
data-derived statistic, not a post-hoc threshold.

### Controlled-delta detection gate

A +5/+10/+20 comparison is detected on an axis only if:

1. the baseline-control gate passes on that axis;
2. every fresh-process candidate median log ratio is greater than the frozen
   control noise envelope;
3. every process has at least the frozen fraction of positive B/A pairs
   (0.75);
4. the fresh-process effect-ratio span is <= 1.05 GPU / 1.08 wall;
5. the maximum within-process AB-vs-BA effect bias is <= 1.03 GPU / 1.05 wall.

No rule assumes that +10% work produces +10% elapsed time.

Axis resolution is the smallest **contiguous** demonstrated controlled-work
effect: +20 must pass before +10 can establish 10%, and +20/+10 must both pass
before +5 can establish 5%. Non-monotonic detection is reported inconclusive,
not selectively accepted.

## Cold/warm and host observations

Warmup samples are retained. First/warm behavior may be reported diagnostically,
but warmup rows never enter the decision statistic.

Load averages and available memory are diagnostic-only. They may not exclude a
sample. No GPU clock/power sysfs write, forced performance state, sudo power
control, or equivalent manipulation is permitted.

## Reruns and safety

Timing instability rerun budget: **0**.

A software/setup failure makes the campaign invalid; it is not a timing rerun.
A host instability during a new methodology stops that methodology. Partial
artifacts are retained as invalid/unsafe evidence and the campaign must not be
restarted merely to obtain a favorable result.
