# I003 — target calibration

## Formal status

**Inconclusive for a reusable common timing resolution.**

GPU timestamp calibration is accepted through the tested 5% delta, but complete CPU wall is non-monotonic under the frozen criterion. Because I002 retained both as decision axes, I003 does not establish a common safe architecture-ranking effect size.

## Artifact and provenance

- Artifact: `out/research/lane-i-measurement-calibration/003-target-calibration/20260930T063441Z`
- Git commit: `bb6cd493a621a64c3642fe94d3eb9f69b0f57dae`
- GPU: `AMD Radeon 8060S Graphics (RADV STRIX_HALO)`
- Driver: `radv / Mesa 26.1.2`
- Vulkan device API: 1.4.348
- Timestamp period: 10.019 ns
- Validation layers: disabled
- Recorder return code: 0
- Device provenance: consistent across processes
- Raw samples: all retained

The accepted campaign completed all 32 fresh processes. The separate individual-dispatch diagnostic completed all 8 processes.

## Accepted GPU timestamp result

Baseline control passed:

- max absolute process-median ratio: 1.004356;
- process-median span: 1.006931;
- max within-process order-bias ratio: 1.009909.

All controlled deltas were detected:

| Delta | Campaign median ratio | Minimum process median ratio | Effect span | Max order bias | Min positive fraction | Frozen result |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| +20% | 1.173034 | 1.168763 | 1.006829 | 1.007720 | 0.833333 | detected |
| +10% | 1.087019 | 1.084108 | 1.006859 | 1.006838 | 0.916667 | detected |
| +5% | 1.044281 | 1.042465 | 1.005741 | 1.011905 | 0.916667 | detected |

Therefore the frozen GPU-timestamp axis demonstrates **5% resolution**, the smallest tested delta.

## Accepted complete CPU-wall result

Baseline control passed:

- max absolute process-median ratio: 1.007352;
- process-median span: 1.012793;
- max within-process order-bias ratio: 1.014349.

Candidate results were:

| Delta | Campaign median ratio | Effect span | Max order bias | Min positive fraction | Frozen result |
| --- | ---: | ---: | ---: | ---: | --- |
| +20% | 1.150296 | 1.017525 | **1.051029** | 0.833333 | **not detected** |
| +10% | 1.073926 | 1.008479 | 1.017259 | 0.833333 | detected |
| +5% | 1.042374 | 1.024709 | 1.022234 | 0.833333 | detected |

The +20% row exceeds the frozen 1.05 maximum within-process order-bias ratio. The failure is small numerically but remains a hard frozen gate failure.

The resulting wall-axis resolution is therefore **inconclusive-nonmonotonic**. Passing +5%/+10% cannot rescue the failed +20% prerequisite.

## Raw-sample inspection

The maximum +20% wall order bias occurs in `accepted-b03-s02-plus20`.

Two consecutive measured pairs contain a large baseline-side timing excursion:

- pair 2, BA: baseline GPU about 363.97 us vs +20% GPU about 276.61 us;
- pair 3, AB: baseline GPU about 365.37 us vs +20% GPU about 311.15 us.

The surrounding baseline GPU measurements are mostly about 239–248 us.

These rows are retained exactly as measured. Removing them, selecting a favorable subset, weakening the 1.05 wall gate, or rerunning to obtain a better campaign would violate I002.

## Diagnostic individual-dispatch campaign

This evidence is diagnostic-only and does not alter the accepted decision:

- GPU baseline control passes and +20% is detected;
- CPU-wall baseline control fails;
- CPU-wall +20% has a process-effect span of about 1.235 and is not detected.

This reinforces that the divergence is primarily a CPU-wall repeatability problem, but it is not promoted into a causal claim.

## Decision

I003 answers the calibration questions as follows:

1. Same-variant repeats are stable enough for the accepted **GPU timestamp** axis.
2. GPU timestamps distinguish +20%, +10%, and +5% across fresh processes.
3. Complete CPU wall does not provide a contiguous frozen resolution because +20% fails the order-bias gate while +10% and +5% pass.
4. Consequently GPU and complete CPU wall are **not consistent enough to support the same claimed effect size** under I002.

No accepted architecture timing should reuse this campaign as evidence for a 5%, 10%, or 20% ranking gate that requires the frozen dual-axis contract.
