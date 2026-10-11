# D005 — stream capacity and overflow

Status: rejected for final composition; memory policy retained as research evidence

## Question

Can the representative producer replace A001's 9,216-owner worst-case stream
reservation with a bounded owner-slot capacity while preserving normal-frame
semantics and making overflow/fallback safe?

## Artifact / identity

- Measurement commit:
  `d58d27af73335f17781be8143290b922afec4397`.
- Artifact root:
  `out/research/lane-d-producer-optimization/005-stream-capacity-overflow/20260928T170111Z/`.
- GPU: AMD Radeon 8060S Graphics (RADV STRIX_HALO).
- Workload: real Sponza, static / camera-motion / light-motion.
- Repeats: 3 process-level repeats.
- Timed iterations: 50 per case.
- Accepted timing validation: disabled.
- Inputs: `d005.csv`, `d005-overflow.csv`, `summary.json`.

## Correctness

All normal rows passed correctness with overflow = 0.

Representative visible-owner/work counts stayed unchanged:

| case | visible owners | work items |
| --- | ---: | ---: |
| static | 981 | 31,392 |
| camera-motion | 978 | 31,296 |
| light-motion | 981 | 31,392 |

The 1,280-owner bounded path therefore preserved the A001 semantic work on all
three representative cases.

## Memory result

The capacity mechanism achieved the intended large reduction:

| metric | full 9,216-owner | bounded 1,280-owner | reduction |
| --- | ---: | ---: | ---: |
| work-stream capacity | 18,874,368 B | 2,621,440 B | 86.11% |
| resident producer memory | 25,945,784 B | 7,280,312 B | 71.94% |
| transient memory | 21,602,344 B | 3,063,848 B | 85.82% |
| contribution capacity | 2,359,296 B | 327,680 B | 86.11% |

Representative work-stream utilization rises from roughly 10.6% to about
76.4-76.6%.

The fixed memory gates (>=75% stream-capacity reduction and >=50% resident
reduction) pass with large margin.

## Matched owner-slot timing

Three-repeat medians in microseconds:

| case | full producer | bounded producer | delta | full E2E | bounded E2E | delta |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| static | 54.677 | 53.295 | -2.53% | 63.483 | 61.934 | -2.44% |
| camera-motion | 53.187 | 52.361 | -1.55% | 61.956 | 61.007 | -1.53% |
| light-motion | 53.509 | 53.260 | -0.46% | 62.178 | 61.874 | -0.49% |

The bounded capacity does not add measurable matched-path GPU cost; it improves
all three medians relative to the same owner-slot implementation at full
capacity.

The fixed matched-control limits (no more than 3% producer/E2E regression) pass.

## Direct accepted-A001 comparison

| case | A001 E2E | bounded E2E | delta |
| --- | ---: | ---: | ---: |
| static | 59.341 | 61.934 | +4.37% |
| camera-motion | 61.063 | 61.007 | -0.09% |
| light-motion | 58.203 | 61.874 | +6.31% |

The predeclared direct-A001 gate allowed at most +5% E2E regression in every
case. Static remains inside that bound, camera is neutral/slightly faster, but
light-motion exceeds it at +6.31%.

Therefore the bounded mechanism is **not promoted into the final Lane D
composition under the fixed D005 gate**. The threshold is not relaxed after
observing the result.

The direct producer-total deltas versus accepted A001 were +5.55% static,
+1.17% camera-motion, and +7.49% light-motion. D005 did not require direct
producer-total parity, but these values explain the remaining staged-path gap.

## Overflow / fallback

The forced 512-owner probe passed every safety check in all repeats/cases:

- overflow flag = 1;
- attempted visible owners remained the true 978-981 count;
- work count was clamped to 16,384;
- output count was clamped to 2,048;
- no out-of-capacity stream/output write was observed;
- bounded indirect dispatch completed safely.

Median failed-attempt E2E:

| case | failed bounded attempt |
| --- | ---: |
| static | 61.296 us |
| camera-motion | 59.108 us |
| light-motion | 57.117 us |

The subsequent 9,216-owner full fallback passed A001 correctness in all cases.

Median GPU retry total (failed bounded attempt + full rerun):

| case | GPU retry total |
| --- | ---: |
| static | 123.499 us |
| camera-motion | 120.353 us |
| light-motion | 127.083 us |

Host allocation/reallocation latency is not measured. Therefore D005 does not
claim these GPU retry totals are complete production overflow latency.

## D001 depth-reuse composition

The 1,280-owner bounded + D001 depth-reuse composition remained correct and
reduced resident logical GI memory slightly further to 7,243,448 bytes.

However its direct accepted-A001 E2E medians were worse by approximately:

- static: +8.61%;
- camera-motion: +6.14%;
- light-motion: +11.18%.

It is therefore not promoted as the final composed producer path from this
experiment.

This does not invalidate D001's earlier conclusion that renderer depth reuse is
a useful incremental integration contract; it shows that the current staged
owner-slot composition does not meet the standalone A001 gate.

## Interpretation

D005 establishes two useful facts:

1. A001's worst-case stream reservation is far larger than needed by the
   representative accepted workload. A 1,280-owner bound cuts stream capacity
   by 86% and total resident producer memory by about 72%.
2. Safe bounded overflow is practical with a single owner-slot allocator and a
   clamped finalize path; a forced overflow can complete without OOB work and a
   full-capacity retry restores correctness.

The remaining reason for rejection is not the capacity policy itself. The
bounded path is faster than its matched full-capacity owner-slot control. The
failure is the fixed direct accepted-A001 light-motion E2E requirement.

## Decision

- do not promote the D005 owner-slot bounded implementation into final Lane D
  composition under the fixed gate;
- retain the **bounded-capacity / safe-overflow policy** as strong research
  evidence for a future production integration that avoids the current staged
  overhead;
- do not keep a full fallback allocation resident by default if claiming the
  steady-state memory saving;
- any production fallback design must measure host allocation/reallocation
  latency or use another explicitly accounted reserve policy.

## Lane D state after D005

- D001 renderer depth reuse: retained as an integration contract;
- D002 visible-tile emission: rejected;
- D003 packed 64-bit one-pass owner selection: rejected;
- D004 workgroup-prefix allocation: rejected;
- D005 bounded stream capacity: rejected for final composition, retained as a
  memory-policy result.

No standalone Lane D producer architecture is promoted over accepted A001 from
D001-D005.

Final cross-lane architecture selection remains dependent on the Lane B/C replay
gates documented by Issue #14.
