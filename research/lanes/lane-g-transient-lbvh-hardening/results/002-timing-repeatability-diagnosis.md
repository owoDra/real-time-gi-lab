# G002 — Timing-repeatability diagnosis

Status: **power-isolation extension in progress; G003 timing still blocked**

## Phase A — target-GPU diagnosis

Measurement commit: `5377cf5b85194eff82e34e3a846eb25af6e2155e`.

The F007-style one-warmup / one-measured fresh-process protocol is rejected.
Fourteen of sixteen anchor groups exceeded the historical `max/min > 1.20`
warning, including every control family. Warmup 0 / 1 / 4 / 16 never stabilized
all anchors, and canonical/reverse full-matrix order produced more than 10%
median shifts in sixteen variant/scenario groups.

The evidence rejects both a purely LBVH-specific instability explanation and
"just warm up longer" as a sufficient fix.

## Phase B — paired/counterbalanced G002b

Measurement commit: `7b14d6ec82252d0a169c3530ce0c3fcaeb5dc18a`.  
Plan: `lane-g-g002b-v1`.

All 160 planned measurements were retained.

Only **1 of 8** frozen candidate/control comparisons met all three repeatability
criteria. Therefore the paired protocol under automatic DPM is rejected and
cannot be frozen for G003.

| comparison | result | block max/min | MAD/median | orientation ratio |
| --- | --- | ---: | ---: | ---: |
| LBVH / HWRT, static | FAIL | 1.2393 | 0.0875 | 1.1887 |
| B003 / HWRT, static | FAIL | 1.2934 | 0.0472 | 1.0046 |
| LBVH / HWRT, sparse-stress | FAIL | 1.1077 | 0.0108 | 1.0708 |
| B003 / HWRT, sparse-stress | PASS | 1.0790 | 0.0174 | 1.0310 |
| LBVH / vanilla, moving-rigid | FAIL | 1.1260 | 0.0054 | 1.0486 |
| B003 / vanilla, moving-rigid | FAIL | 1.2559 | 0.0422 | 1.0893 |
| LBVH / vanilla, sparse-moving | FAIL | 1.4171 | 0.1103 | 1.0428 |
| B003 / vanilla, sparse-moving | FAIL | 1.6689 | 0.1025 | 1.3160 |

### Stronger localization from raw timings

The LBVH moving paths themselves are repeatable:

- moving-rigid LBVH: 1.431–1.488 ms, max/min **1.039**, MAD/median ~0.77%;
- sparse-moving LBVH: 1.383–1.430 ms, max/min **1.034**, MAD/median ~0.47%.

The matching vanilla comparator is not:

- moving-rigid vanilla: max/min **1.487**;
- sparse-moving vanilla: max/min **1.571**.

Its measured traversal-maintenance time repeatedly falls into two broad bands:
roughly **2.35–2.45 ms** and **3.1–3.25 ms**. Similar multi-stage excursions
also occur in software/HWRT controls and in occasional stable/static processes.

This strongly localizes the remaining repeatability problem to GPU/system
performance state or external interference around process-level measurements,
rather than transient-LBVH builder variance.

It is still not valid to name DVFS as the unique cause because the previous
endpoint telemetry did not sample clocks throughout each measured GPU workload.

## Phase C — frozen power-isolation diagnostic G002c

Plan: `lane-g-g002c-v1`.

The G002b matrix, estimator, block orders, warmup, and thresholds remain
unchanged. The only new diagnostic condition is:

- AMDGPU `power_dpm_force_performance_level` must be `profile_peak`;
- the runner verifies that condition before and after every child process;
- the runner never writes sysfs;
- every measurement remains retained.

Frozen criteria remain:

- block-ratio max/min <= 1.10;
- block-ratio MAD/median <= 0.05;
- ABBA-vs-BAAB orientation-median ratio <= 1.10.

If every candidate and control comparison passes under the pre-frozen
`profile_peak` condition, G002 may freeze the power-isolated paired protocol
for G003/G005 relative timing gates. If not, G002 remains open and the next
diagnostic is explicit background/system-load isolation.

## Current disposition

- F007 one-shot fresh-process protocol: **Rejected**.
- warmup-only fix: **Rejected**.
- automatic-DPM paired protocol: **Rejected**.
- LBVH moving-path intrinsic instability: **Rejected by G002b evidence**.
- GPU/system performance-state involvement: **Supported hypothesis**.
- DVFS as unique root cause: **Inconclusive pending G002c**.
- G003 decision-valid timing: **Blocked**.
