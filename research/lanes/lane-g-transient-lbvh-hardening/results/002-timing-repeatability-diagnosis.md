# G002 — Timing-repeatability diagnosis

Status: **diagnostic extension in progress; G003 timing still blocked**

## Phase A — target-GPU diagnosis

Measurement commit: `5377cf5b85194eff82e34e3a846eb25af6e2155e`  
Target: `AMD Radeon 8060S Graphics (RADV STRIX_HALO)`  
Outlier deletion: none.

### Findings

The F007-like one-warmup / one-measured fresh-process boundary remains
non-decision-valid: 14 of 16 anchor variant/scenario groups exceed the historical
`max/min > 1.20` warning, including all control families.

Nine of those 14 unstable groups still have `MAD/median <= 5%`, so many
failures contain isolated/clustered excursions rather than uniformly broad
variance. The excursions remain retained.

No tested warmup count (0 / 1 / 4 / 16) stabilizes every anchor group. Warmup 4
is the best diagnostic point (8/16 groups satisfy the frozen G002 criteria);
warmup 16 regresses to 6/16. Longer warmup alone is therefore rejected.

The canonical/reverse full-matrix campaigns contain 16 variant/scenario groups
whose median changes by more than 10%, including controls. Variant-major
full-matrix order is therefore rejected as a decision-valid comparison boundary.

Same-process LBVH steady-target rows have low MAD/median, while controls still
show occasional large multi-stage excursions. Fresh-process slow runs can inflate
several unrelated GPU phases simultaneously, including traversal, radiance,
storage and resolve. This is consistent with whole-GPU/system disturbance, not
one LBVH stage.

Endpoint telemetry observed automatic DPM, active SCLK samples around
0.9–1.4 GHz, GPU temperatures around 34–44 C, and non-zero GPU busy samples.
The endpoint samples do not correlate strongly enough with individual excursions
to claim a unique DVFS, thermal, or background-work cause.

## Phase B — frozen paired/counterbalanced diagnostic

Plan: `lane-g-g002b-v1`.

- fresh child process for every measurement;
- warmup = 4;
- one measured frame;
- 0.5 s settle interval;
- five blocks;
- orders: ABBA / BAAB / ABBA / BAAB / ABBA;
- no run deletion or replacement;
- block ratio = `geometric_mean(A1,A2) / geometric_mean(B1,B2)`.

Frozen repeatability criteria:

- block-ratio max/min <= 1.10;
- block-ratio MAD/median <= 0.05;
- ABBA-vs-BAAB orientation-median ratio <= 1.10.

Candidate comparisons and separate control/control comparisons are both
required to pass. If all pass, this relative paired boundary may be frozen for
G003/G005. Otherwise G002 remains open and clock/power/isolation diagnosis is
next.

## Current disposition

- F007 one-shot fresh-process protocol: **Rejected**.
- longer warmup alone: **Rejected**.
- LBVH-specific instability hypothesis: **Rejected**.
- unique clock/thermal/background root cause: **Inconclusive**.
- paired/counterbalanced protocol: **Pending**.
- G003 decision-valid timing: **Blocked**.
