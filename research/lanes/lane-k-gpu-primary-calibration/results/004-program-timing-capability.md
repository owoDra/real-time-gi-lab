# K004 — program timing capability

## Primary outcome

**GPU-primary protocol accepted**

This is the sole Lane-K K004 outcome.

## Smallest demonstrated safe effect size

The smallest contiguous known-delta effect demonstrated on the target is
**5% controlled GPU work**.

K003 passed the frozen GPU-primary baseline control and detected +20%, +10%, and
+5% across all required fresh-process/counterbalanced gates. Therefore the
predeclared K004 mapping accepts the GPU-primary protocol.

## Exact reusable protocol

Downstream architecture timing may reuse `lane-k-k002-v1` only when it imports
and freezes the methodology before its first accepted candidate timing.

The reusable target protocol is:

- target: `AMD Radeon 8060S Graphics (RADV STRIX_HALO)`;
- primary performance axis: GPU timestamp;
- complete CPU wall: diagnostic / health / provenance only;
- workload-calibration evidence: 8192 elements, accepted batch dispatches = 16;
- calibration deltas: baseline 200 iterations, +5%=210, +10%=220, +20%=240;
- 4 warmup pairs per process;
- 12 measured pairs per process;
- 8 fresh-process blocks;
- paired AB/BA sampling with the frozen position-counterbalanced comparison
  schedule;
- 1 second settle before each process;
- primary statistic: fresh-process median of paired `log(B/A)`;
- no sample exclusion;
- no instability reruns;
- no completed-campaign reruns;
- all raw samples retained;
- stable device/driver/API/timestamp provenance required.

Frozen GPU-primary gates:

- control max absolute process-median ratio <= 1.02;
- control process-median span <= 1.03;
- control max within-process order-bias ratio <= 1.02;
- candidate process-effect span <= 1.05;
- candidate max within-process order-bias ratio <= 1.03;
- candidate minimum positive-pair fraction >= 0.75;
- candidate minimum process effect must exceed the accepted control noise
  envelope;
- detection must be contiguous through +20%, +10%, +5%.

Complete CPU wall remains diagnostic-only for repeatability. It invalidates a
campaign only for the structural health failures frozen in K002: non-positive
or non-finite timing, incomplete pair structure, complete wall smaller than the
GPU timestamp, inconsistent device provenance, or process failure.

Forced GPU power/clock states, privileged power sysfs writes, outlier deletion,
fastest-subset selection, favorable reruns, and post-hoc threshold changes remain
forbidden.

## Downstream reuse rule

A later architecture lane must predeclare a promotion threshold **no smaller
than 5%** when using this calibration result. Historical diagnostic timing does
not become decision-valid merely because Lane K is accepted; architecture
candidates must still be compared in a new run-local campaign under an imported,
pre-frozen protocol and equivalent measurement boundary.

This resolves the timing-methodology dependency for a future Lane-J
J004-equivalent formal crossover and for Lane-E timing revalidation, subject to
their own correctness, memory, workload, and run-local comparator gates.

## Limitations

The accepted calibration is target-specific. It does not establish the same
resolution on other GPUs, drivers, operating environments, workloads, or
measurement boundaries.

K004 does not select a topology backend and does not reinterpret Lane-I,
Lane-E, Lane-G, Lane-H, or historical Lane-J timing.
