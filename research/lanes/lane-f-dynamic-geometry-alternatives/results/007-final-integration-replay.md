# F007 — Final integration replay and Lane F decision

Plan: `lane-f-plan-v1`  
Measurement commit: `041bf0287e2095302b61d31b222de958dd3b6412`  
Target: AMD Radeon 8060S Graphics (RADV STRIX_HALO), RADV / Mesa 26.1.2

## Outcome

**Correctness PASS. Final timing repeatability INCONCLUSIVE. No transient candidate is promoted as rigid-primary under the frozen v1 gates.**

The 60-case validation matrix passed. The first accepted F007 timing campaign was unstable in 23 variant/scenario pairs. The one permitted identical full rerun also contained 23 unstable pairs, so every still-unstable timing gate is INCONCLUSIVE and no further timing rerun is allowed.

This does not leave promotion undecidable: both transient candidates independently exceed the frozen hard peak-memory ceiling in sparse regimes. Since rigid-primary requires every hard gate to pass, neither candidate can be promoted even if the unresolved timing gates were favorable. The sorted grid additionally has a decision-valid timing FAIL in `large-world-moving` because both the candidate and matching vanilla row were stable there.

The transient LBVH remains the strongest research direction: its stable representative rows pass, its diagnostic moving/dynamic-stress medians are substantially below vanilla, and F006 mechanism data were favorable. It is **not** a formally accepted replacement because the sparse memory gate fails and multiple required timing gates remain inconclusive.

## Artifacts

- validation: `out/research/lane-f-dynamic-geometry-alternatives/007-final-integration-replay/20260929T142715Z`
- first timing campaign: `.../20260929T143010Z` — unstable
- identical full rerun: `.../20260929T143501Z` — unstable, rerun budget exhausted

## Correctness

- 5 variants × 12 scenarios = 60/60 validation rows passed.
- all dynamic scenarios used Nrep = 796 and recorded 796 segment-membership changes.
- grid overflow, storage failures and Vulkan validation errors were zero.

## Historical I001 anchors

| variant | static | camera | light | moving-rigid |
|---|---:|---:|---:|---:|
| vanilla-software | 593.969 | 604.268 | 603.186 | 3302.675 |
| combined-hwrt | 202.465 | 213.886 | 206.512 | 4100.230 |
| combined-software | 391.544 | 396.714 | 378.279 | 3566.897 |

Historical values are reporting anchors only; all frozen F007 gates use the run-local medians below.

## Run-local complete GPU medians (us)

| scenario | LBVH | Grid | Vanilla | HWRT | Software/B003 |
|---|---:|---:|---:|---:|---:|
| static | 160.224 | 162.509 | 517.704 | 161.707 | 333.874 |
| camera | 166.316 | 165.514 | 543.513 | 165.795 | 340.006 |
| light | 164.072 | 163.591 | 508.566 | 159.944 | 320.168 |
| moving | 1469.592 | 18201.303 | 3600.761 | 4909.729 | 2729.867 |
| sparse | 139.585 | 138.142 | 376.195 | 134.616 | 256.808 |
| dense | 252.480 | 259.653 | 1014.528 | 262.298 | 675.283 |
| large | 176.736 | 162.589 | 520.469 | 167.077 | 335.678 |
| vertical | 143.352 | 145.837 | 459.874 | 141.028 | 376.876 |
| sparse-moving | 1498.928 | 17488.709 | 2934.335 | 4021.681 | 2677.327 |
| dense-moving | 1630.498 | 18473.500 | 3528.144 | 4222.743 | 3977.958 |
| large-moving | 1464.062 | 20696.724 | 3082.777 | 4132.291 | 2784.330 |
| vertical-moving | 1436.289 | 4540.146 | 2902.314 | 4147.520 | 2853.221 |

## Final-rerun repeatability

The final rerun still had **23 unstable rows** (`complete_gpu max/min > 1.20`). These rows' timing gates are INCONCLUSIVE.

| variant | scenario | min GPU us | median | max | max/min |
|---|---|---:|---:|---:|---:|
| transient-lbvh | moving-rigid | 1451.638 | 1469.592 | 1819.697 | 1.254 |
| transient-lbvh | sparse-stress | 134.976 | 139.585 | 262.859 | 1.947 |
| transient-lbvh | dense-stress | 243.423 | 252.480 | 329.666 | 1.354 |
| transient-lbvh | vertical-world-stress | 142.270 | 143.352 | 259.854 | 1.826 |
| transient-lbvh | dense-moving | 1583.008 | 1630.498 | 2059.633 | 1.301 |
| transient-lbvh | large-world-moving | 1458.211 | 1464.062 | 1960.204 | 1.344 |
| transient-grid | vertical-world-stress | 141.669 | 145.837 | 198.136 | 1.399 |
| vanilla-software | camera-motion | 532.973 | 543.513 | 1247.130 | 2.340 |
| vanilla-software | moving-rigid | 3002.104 | 3600.761 | 3949.304 | 1.316 |
| vanilla-software | sparse-stress | 366.577 | 376.195 | 581.425 | 1.586 |
| vanilla-software | sparse-moving | 2787.576 | 2934.335 | 3639.275 | 1.306 |
| vanilla-software | dense-moving | 3511.432 | 3528.144 | 4311.071 | 1.228 |
| vanilla-software | vertical-world-moving | 2846.729 | 2902.314 | 4126.761 | 1.450 |
| combined-hwrt | large-world-stress | 156.257 | 167.077 | 291.233 | 1.864 |
| combined-hwrt | sparse-moving | 3998.678 | 4021.681 | 5032.802 | 1.259 |
| combined-hwrt | dense-moving | 4150.406 | 4222.743 | 5210.620 | 1.255 |
| combined-software | sparse-stress | 248.713 | 256.808 | 538.022 | 2.163 |
| combined-software | large-world-stress | 307.945 | 335.678 | 382.407 | 1.242 |
| combined-software | vertical-world-stress | 371.225 | 376.876 | 584.430 | 1.574 |
| combined-software | sparse-moving | 2632.041 | 2677.327 | 3461.457 | 1.315 |
| combined-software | dense-moving | 3164.012 | 3977.958 | 4356.517 | 1.377 |
| combined-software | large-world-moving | 2765.414 | 2784.330 | 3623.765 | 1.310 |
| combined-software | vertical-world-moving | 2814.107 | 2853.221 | 3647.931 | 1.296 |

## Frozen gate interpretation

### transient-lbvh

| gate | ratio | status |
|---|---:|---|
| static GPU / HWRT | 0.9908x | PASS |
| camera-motion GPU / HWRT | 1.0031x | PASS |
| light-motion GPU / HWRT | 1.0258x | PASS |
| moving GPU / vanilla | 0.4081x | INCONCLUSIVE |
| moving wall / vanilla | 0.0161x | INCONCLUSIVE |
| sparse-stress GPU / HWRT | 1.0369x | INCONCLUSIVE |
| dense-stress GPU / HWRT | 0.9626x | INCONCLUSIVE |
| large-world-stress GPU / HWRT | 1.0578x | INCONCLUSIVE |
| vertical-world-stress GPU / HWRT | 1.0165x | INCONCLUSIVE |
| sparse-moving GPU / vanilla | 0.5108x | INCONCLUSIVE |
| dense-moving GPU / vanilla | 0.4621x | INCONCLUSIVE |
| large-world-moving GPU / vanilla | 0.4749x | INCONCLUSIVE |
| vertical-world-moving GPU / vanilla | 0.4949x | INCONCLUSIVE |
| sparse-stress peak memory / vanilla | 3.0836x | **FAIL** |
| sparse-moving peak memory / vanilla | 3.2025x | **FAIL** |

### transient-grid

| gate | ratio | status |
|---|---:|---|
| static GPU / HWRT | 1.0050x | PASS |
| camera-motion GPU / HWRT | 0.9983x | PASS |
| light-motion GPU / HWRT | 1.0228x | PASS |
| moving GPU / vanilla | 5.0548x | INCONCLUSIVE |
| moving wall / vanilla | 0.1644x | INCONCLUSIVE |
| sparse-stress GPU / HWRT | 1.0262x | PASS |
| dense-stress GPU / HWRT | 0.9899x | PASS |
| large-world-stress GPU / HWRT | 0.9731x | INCONCLUSIVE |
| vertical-world-stress GPU / HWRT | 1.0341x | INCONCLUSIVE |
| sparse-moving GPU / vanilla | 5.9600x | INCONCLUSIVE |
| dense-moving GPU / vanilla | 5.2360x | INCONCLUSIVE |
| large-world-moving GPU / vanilla | 6.7137x | FAIL |
| vertical-world-moving GPU / vanilla | 1.5643x | INCONCLUSIVE |
| sparse-stress peak memory / vanilla | 3.0836x | **FAIL** |
| sparse-moving peak memory / vanilla | 3.9135x | **FAIL** |

Memory is an allocation/capacity gate rather than a timing-repeatability statistic; the sparse memory failures are deterministic across repeats and independently prevent promotion.

## Candidate phase detail — final rerun

| variant / scenario | wall us | maintenance us | builder us | static trav us | dynamic trav us | merge us | producer us | storage us | resolve us | peak MiB | correctness |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| transient-lbvh / static | 386.610 | 0.000 | 0.000 | 70.173 | 0.000 | 0.000 | 20.158 | 9.017 | 4.128 | 142.99 | PASS; stable |
| transient-lbvh / camera-motion | 430.388 | 0.000 | 0.000 | 74.982 | 0.000 | 0.000 | 22.002 | 9.378 | 4.168 | 142.99 | PASS; stable |
| transient-lbvh / light-motion | 393.089 | 0.000 | 0.000 | 74.822 | 0.000 | 0.000 | 23.525 | 9.097 | 4.128 | 142.99 | PASS; stable |
| transient-lbvh / moving-rigid | 1849.829 | 1107.624 | 106.082 | 80.834 | 63.441 | 6.332 | 23.004 | 10.620 | 4.769 | 160.87 | PASS; unstable |
| transient-lbvh / sparse-stress | 426.509 | 0.000 | 0.000 | 60.996 | 0.000 | 0.000 | 13.586 | 7.134 | 2.765 | 113.56 | PASS; unstable |
| transient-lbvh / dense-stress | 493.736 | 0.000 | 0.000 | 104.679 | 0.000 | 0.000 | 30.057 | 23.685 | 11.141 | 259.72 | PASS; unstable |
| transient-lbvh / large-world-stress | 406.019 | 0.000 | 0.000 | 79.110 | 0.000 | 0.000 | 22.002 | 9.097 | 4.168 | 142.99 | PASS; stable |
| transient-lbvh / vertical-world-stress | 468.537 | 0.000 | 0.000 | 64.362 | 0.000 | 0.000 | 16.792 | 6.733 | 2.685 | 142.62 | PASS; unstable |
| transient-lbvh / sparse-moving | 2006.275 | 1196.473 | 105.160 | 64.442 | 47.651 | 2.926 | 14.067 | 8.015 | 3.046 | 117.94 | PASS; stable |
| transient-lbvh / dense-moving | 1982.396 | 1106.222 | 106.041 | 125.518 | 101.633 | 22.002 | 30.498 | 28.975 | 13.506 | 331.60 | PASS; unstable |
| transient-lbvh / large-world-moving | 1932.867 | 1116.201 | 105.240 | 84.841 | 62.479 | 6.613 | 22.883 | 10.620 | 4.769 | 160.87 | PASS; unstable |
| transient-lbvh / vertical-world-moving | 1795.991 | 1110.630 | 105.881 | 65.845 | 56.948 | 3.166 | 18.195 | 7.855 | 2.966 | 160.50 | PASS; stable |
| transient-grid / static | 391.349 | 0.000 | 0.000 | 71.696 | 0.000 | 0.000 | 21.321 | 9.057 | 4.168 | 142.99 | PASS; stable |
| transient-grid / camera-motion | 390.649 | 0.000 | 0.000 | 72.818 | 0.000 | 0.000 | 20.319 | 9.338 | 4.168 | 142.99 | PASS; stable |
| transient-grid / light-motion | 542.915 | 0.000 | 0.000 | 67.849 | 0.000 | 0.000 | 24.206 | 8.977 | 4.088 | 142.99 | PASS; stable |
| transient-grid / moving-rigid | 18833.903 | 1109.909 | 16799.479 | 106.643 | 52.941 | 8.015 | 27.773 | 12.424 | 5.010 | 187.05 | PASS; stable |
| transient-grid / sparse-stress | 372.029 | 0.000 | 0.000 | 57.870 | 0.000 | 0.000 | 12.945 | 7.134 | 2.765 | 113.56 | PASS; stable |
| transient-grid / dense-stress | 488.327 | 0.000 | 0.000 | 108.326 | 0.000 | 0.000 | 30.979 | 23.845 | 11.101 | 259.72 | PASS; stable |
| transient-grid / large-world-stress | 394.699 | 0.000 | 0.000 | 67.689 | 0.000 | 0.000 | 22.603 | 9.057 | 4.128 | 142.99 | PASS; stable |
| transient-grid / vertical-world-stress | 380.930 | 0.000 | 0.000 | 64.282 | 0.000 | 0.000 | 13.345 | 6.733 | 2.725 | 142.62 | PASS; unstable |
| transient-grid / sparse-moving | 18642.759 | 1105.781 | 15968.741 | 97.866 | 41.198 | 3.607 | 14.948 | 8.977 | 3.366 | 144.12 | PASS; stable |
| transient-grid / dense-moving | 19274.381 | 1109.789 | 16864.242 | 139.826 | 100.751 | 24.246 | 42.320 | 30.738 | 13.866 | 357.78 | PASS; stable |
| transient-grid / large-world-moving | 21471.240 | 1125.498 | 19246.288 | 111.853 | 54.704 | 7.935 | 26.931 | 12.424 | 5.010 | 187.08 | PASS; stable |
| transient-grid / vertical-world-moving | 4899.746 | 1102.575 | 3228.935 | 68.210 | 42.761 | 3.166 | 18.395 | 7.855 | 2.966 | 167.74 | PASS; stable |

Full control phase/memory rows remain in the retained `f007-summary.json` and `f007-raw.csv` artifacts; the comparison table above publishes their complete-GPU medians and the historical anchors required by the frozen plan.

## Mechanism interpretation

- LBVH moving-rigid diagnostic median: **1469.592 us**, versus vanilla **3600.761 us**.
- LBVH moving builder median: **106.082 us**; dynamic traversal **63.441 us**; static traversal **80.834 us**.
- Grid moving builder median: **16799.479 us**, including sort **14646.468 us**.
- Grid moving emitted references: **155033** for 796 triangles = **194.765 refs/triangle**, max **6100**.

This reproduces the F005 finding: the sorted grid is dominated by overlap amplification and sorting, while LBVH rebuild/traversal remains comparatively small.

## Final Lane F decision

- F007 correctness: **PASS**.
- F007 timing repeatability: **INCONCLUSIVE after the permitted identical rerun**.
- additional F007 timing reruns: **not allowed**.
- transient-grid rigid-primary: **NO** — hard sparse memory failures; additionally a decision-valid `large-world-moving` timing FAIL and severe dynamic diagnostic regressions.
- transient-LBVH rigid-primary: **NO promotion under lane-f-plan-v1** — hard sparse memory failures independently violate gate 9; multiple timing gates also remain inconclusive.
- general-dynamic architecture: **NOT ESTABLISHED** because F006 timing was inconclusive and neither candidate is rigid-primary.
- selected Lane F architecture: **none**.

Lane F therefore does not establish exact frame-local rebuild as a complete replacement for the current dynamic path under the frozen v1 workload and memory boundary. It does establish a strong follow-up direction: transient dynamic LBVH removes the dominant persistent-maintenance cost and is consistently much stronger than the sorted-grid control, but its memory accounting/sparse-regime integration must be redesigned and re-planned before a new promotion attempt.
