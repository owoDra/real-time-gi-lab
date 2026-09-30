# K002 — frozen GPU-primary calibration protocol

Status: **frozen before any accepted Lane-K target timing**  
Plan: `lane-k-k002-v1`

Canonical config:
`research/lanes/lane-k-gpu-primary-calibration/experiments/002-gpu-primary-protocol-config.json`

## Role separation

This is a new Lane-K methodology, not a reinterpretation of Lane I I003.

- **GPU timestamp is the sole primary performance decision axis.**
- **Complete CPU wall is diagnostic / health / provenance only.**

Lane I I003's +5% GPU result is not imported as accepted Lane-K evidence.

## Workload and batching

K002 selectively reuses the architecture-neutral workload construction that
predated Lane I target timing:

- 8192 elements;
- baseline 200 iterations;
- +5/+10/+20 = 210/220/240 iterations;
- 16 dependent dispatches per timed batch;
- 4 warmup pairs;
- 12 measured pairs;
- 8 fresh-process blocks;
- 1 second settle before each process;
- position-balanced comparison order;
- alternating AB/BA pair order inside each process.

All raw samples are retained. Validation layers are disabled for accepted timing.

## GPU-primary gates

The GPU thresholds are the same pre-target GPU criteria that were already frozen
in Lane I I002. They are reused as pre-existing methodology parameters, not
selected from Lane I I003 outcomes.

Baseline control must satisfy all:

- max absolute fresh-process median ratio <= 1.02;
- fresh-process median span <= 1.03;
- max within-process AB/BA order-bias ratio <= 1.02.

A known-delta candidate is detected only if all:

- baseline gate passes;
- every fresh-process median log(B/A) is above the baseline noise envelope;
- process-effect span <= 1.05;
- max within-process order-bias ratio <= 1.03;
- minimum positive-pair fraction >= 0.75.

Resolution is contiguous: +20 must pass before +10; +20 and +10 must pass before
+5. A smaller passing row never bypasses a larger failed prerequisite.

## CPU-wall health semantics

CPU wall never votes on performance resolution. Its repeatability thresholds are
annotation-only.

The campaign is invalid only if the measurement boundary itself is unhealthy:

- a GPU or CPU-wall timing sample is non-finite or non-positive;
- complete CPU wall is smaller than the enclosed GPU timestamp;
- a measured pair/process is incomplete or structurally inconsistent;
- process execution fails;
- GPU/driver/API/timestamp provenance changes across fresh processes.

Ordinary CPU-wall jitter, non-monotonicity, order bias, or failure of the
annotation thresholds does **not** invalidate an otherwise valid GPU-primary
decision.

Host load/memory observations are diagnostic-only and never justify sample
deletion.

## Rerun and interruption

- instability rerun budget: **0**;
- completed-campaign rerun budget: **0**;
- no outlier deletion, fastest subset, favorable rerun, or threshold change;
- an interrupted artifact is retained and is not accepted;
- in-place resume is disabled;
- a fresh restart is permitted only if no complete K003 summary exists yet, and
  the interrupted artifact must remain retained for provenance.

## Artifact contract

K003 must retain the frozen config snapshot, progress state, every raw sample,
fresh-process summaries, host observations, device records, and final summary.
Per-process K001 device/sample files remain under the campaign artifact tree.

No K002 threshold or role may change after the first complete K003 target
artifact.
