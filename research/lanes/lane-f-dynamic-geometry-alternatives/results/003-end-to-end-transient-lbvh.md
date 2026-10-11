# F003 — End-to-end persistent static HWRT + frame-local dynamic LBVH

Plan: `lane-f-plan-v1`  
Measurement commit: `d4887dd23c2ade71deed695e20c5fa1d5fd3d6d7`  
Target: AMD Radeon 8060S Graphics (RADV STRIX_HALO), RADV / Mesa 26.1.2

## Outcome

**Correctness PASS. Accepted timing INCONCLUSIVE due repeated instability.**

The complete candidate architecture is functionally valid across the frozen F003
matrix, including moving-rigid. However, the first accepted timing campaign
exceeded the frozen `complete_gpu_us max/min > 1.20` instability threshold.
The one permitted identical full-campaign rerun also exceeded it. Under
`lane-f-plan-v1`, no additional rerun, outlier deletion, partial-case rerun or
threshold reinterpretation is allowed.

Therefore F003 does **not** produce a formal performance PASS or FAIL.

## Artifacts

Correctness validation:

`out/research/lane-f-dynamic-geometry-alternatives/003-end-to-end-transient-lbvh/20260929T124548Z`

First timing campaign — unstable:

`out/research/lane-f-dynamic-geometry-alternatives/003-end-to-end-transient-lbvh/20260929T124802Z`

One permitted identical full rerun — unstable:

`out/research/lane-f-dynamic-geometry-alternatives/003-end-to-end-transient-lbvh/20260929T125018Z`

## Correctness

The validation matrix covered all 32 frozen combinations:

- transient-lbvh
- vanilla-software
- combined-hwrt
- combined-software

across static, camera-motion, light-motion, moving-rigid, sparse-stress,
dense-stress, large-world-stress and vertical-world-stress.

Every case reported:

- quality passed
- storage failures: 0
- Vulkan validation errors: 0

The earlier moving-rigid Hit mismatch was fixed before this accepted validation
by binding LBVH leaf AABBs to the sorted primitive id.

## Timing repeatability

The second and final allowed campaign still contained 11 unstable
variant/scenario pairs:

| variant | scenario | min GPU us | median GPU us | max GPU us | max/min |
| --- | --- | ---: | ---: | ---: | ---: |
| combined-hwrt | dense-stress | 239.455 | 251.037 | 551.408 | 2.303 |
| combined-hwrt | moving-rigid | 4012.143 | 4040.918 | 5042.381 | 1.257 |
| combined-software | moving-rigid | 2741.048 | 2755.716 | 3602.845 | 1.314 |
| transient-lbvh | camera-motion | 156.898 | 167.959 | 357.439 | 2.278 |
| transient-lbvh | dense-stress | 242.902 | 248.993 | 427.572 | 1.760 |
| transient-lbvh | sparse-stress | 122.593 | 136.860 | 367.298 | 2.996 |
| vanilla-software | dense-stress | 927.362 | 1008.516 | 1642.040 | 1.771 |
| vanilla-software | light-motion | 487.206 | 500.271 | 959.503 | 1.969 |
| vanilla-software | moving-rigid | 2923.675 | 3779.822 | 4196.974 | 1.436 |
| vanilla-software | sparse-stress | 336.239 | 358.962 | 624.226 | 1.856 |
| vanilla-software | vertical-world-stress | 442.441 | 461.236 | 905.040 | 2.046 |

Because this is the second full campaign, the rerun budget is exhausted.

## Diagnostic medians only

The following values are retained for diagnosis but are **not decision-valid
gate results** because the campaign is unstable.

For moving-rigid, transient-LBVH itself was stable in the second campaign:

- complete GPU median: 1436.008 us
- complete GPU min/max: 1424.867 / 1474.602 us
- complete wall median: 2041.577 us
- dynamic builder median: 103.396 us
- dynamic traversal median: 60.796 us
- static traversal median: 82.477 us
- cross-structure merge median: 5.651 us

The run-local vanilla moving comparator was unstable, so its apparent candidate
ratios are not formal evidence.

The second campaign's diagnostic gate calculation would also show:

- large-world stress GPU: 1.0702x combined-HWRT versus 1.05 limit
- sparse-stress GPU: 1.0893x combined-HWRT versus 1.05 limit
- sparse-stress peak memory: 3.0836x vanilla versus 3.0 limit

These are retained as leads for later research, not as a formal F003 FAIL.

## F004

F004 is **not activated**.

Independently of F003 timing being inconclusive, the frozen F004 activation rule
requires formal F002 PASS. F002 remains formal-gate PENDING because its required
F001 run-local vanilla moving comparator was inconclusive.

Also, in the second F003 campaign the moving dynamic traversal median
(60.796 us) was below the transient builder median (103.396 us), so the
`dynamic traversal >= builder` condition was not observed.

## Decision

- F003 correctness: **PASS**
- F003 timing repeatability: **INCONCLUSIVE**
- F003 formal performance gate: **NOT EVALUATED**
- additional F003 timing reruns: **not allowed under lane-f-plan-v1**
- F004 activation: **NO**
- next frozen experiment: **F005 sorted two-level grid end-to-end**

The unstable raw artifacts remain part of the research record. No values are
discarded or filtered.
