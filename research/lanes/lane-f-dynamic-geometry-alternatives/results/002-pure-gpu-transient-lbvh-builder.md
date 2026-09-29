# F002 — Pure GPU transient LBVH builder

Plan: `lane-f-plan-v1`  
Measurement commit: `833e6e01173eeebbaf35c73194cb43e376a7be33`  
Target: AMD Radeon 8060S Graphics (RADV STRIX_HALO), RADV / Mesa 26.1.2

## Outcome

## Supersession note — F003 correctness failure

During F003 validation on the same candidate family, the moving-rigid warmup
reported 2,259 Hit mismatches. Investigation found a builder correctness bug
that the original F002 structural validation did not cover:

- the leaf node represented sorted primitive `keys_a[id].z`;
- but its AABB was populated from unsorted `aabb[id]`;
- therefore root bounds remained correct as a union while per-leaf/internal
  traversal bounds could belong to different triangles.

The implementation is corrected by indexing leaf bounds with the sorted
primitive id. F002 validation is also strengthened to require:

- root index/count correctness;
- sorted primitive -> leaf identity and AABB correspondence;
- parent/child consistency;
- full tree reachability.

Accordingly, the validation artifact `20260929T092619Z` and timing artifact
`20260929T092838Z` are retained as historical evidence but are
**superseded for formal F002 correctness/performance decisions**. A corrected
same-plan validation and timing campaign is required. This is a correctness
repair, not post-result threshold/tuning changes.

**Original timing was stable, but its correctness evidence is superseded pending a corrected rerun.**

The representative F001/I001 dynamic subset is `Nrep = 796` triangles
(instance 5, displacement 362.264). The accepted 5-process timing median at
Nrep is **99.028155 us**.

The F002 formal feasibility gate remains **pending**, not PASS/FAIL, because
F001's required run-local `vanilla-software / moving-rigid` comparator was
unstable in both the initial run and the one permitted identical rerun. The
historical `2972.4075 us` ceiling remains reference-only and is not substituted
for the frozen run-local comparator.

## Artifacts

Validation:

`out/research/lane-f-dynamic-geometry-alternatives/002-pure-gpu-transient-lbvh-builder/20260929T092619Z`

Accepted timing:

`out/research/lane-f-dynamic-geometry-alternatives/002-pure-gpu-transient-lbvh-builder/20260929T092838Z`

## Correctness

The validation artifact covered Nrep plus 1k, 4k, 16k, 64k, 256k and 1M
primitives.

- Vulkan validation errors: 0
- sort mismatches: 0
- root-count mismatches: 0
- root-bounds mismatches: 0

All accepted timing rows also completed their structural validation.

## Accepted builder timing

| primitives | median builder GPU | min | max | stable |
| ---: | ---: | ---: | ---: | :---: |
| 796 (Nrep) | 99.028 us | 98.728 us | 99.549 us | yes |
| 1,000 | 100.491 us | 100.351 us | 100.671 us | yes |
| 4,000 | 128.264 us | 128.063 us | 128.284 us | yes |
| 16,000 | 235.928 us | 235.808 us | 236.028 us | yes |
| 64,000 | 667.588 us | 667.288 us | 668.069 us | yes |
| 256,000 | 2664.903 us | 2661.016 us | 2689.971 us | yes |
| 1,000,000 | 12267.789 us | 12230.177 us | 12298.507 us | yes |

No size exceeded the frozen process-level `max/min > 1.20` instability rule,
so no F002 rerun is required.

## Nrep phase breakdown

At Nrep, the process-level median phase times are:

- scratch/reset management: 9.538 us
- current-frame dynamic input: 1.523 us
- AABB: 1.483 us
- page/local Morton: 1.403 us
- radix sort: 69.252 us
- topology: 14.628 us
- bottom-up bounds: 1.042 us
- complete builder: 99.028 us

The radix sort is the dominant Nrep builder phase. This is evidence only; no
post-timing F002 tuning is permitted under the frozen experiment revision.

## Memory

For Nrep:

- persistent/template bytes: 50,944
- transient bytes: 178,256
- scratch bytes: 3,760
- peak builder bytes: 232,960

## Decision

F002 is concluded as:

- structural correctness: **SUPERSEDED — corrected rerun required**
- original repeatability: **PASS**, but not decision-valid until corrected rerun
- builder measurement: **SUPERSEDED — corrected rerun required**
- formal feasibility gate: **PENDING** because the frozen run-local vanilla
  moving comparator remains inconclusive
- architecture promotion: **none at F002**
- F003 end-to-end implementation/measurement: **may proceed**
- F004 activation: **not available yet**, because its frozen activation rule
  explicitly requires F002 to formally pass

Proceeding to F003 does not reinterpret the F002 gate. It directly measures the
complete persistent-static-HWRT + frame-local-dynamic-LBVH architecture, while
the unresolved F002 comparator remains recorded as a separate provenance issue.
