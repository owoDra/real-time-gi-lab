# F002 — Pure GPU transient LBVH builder

Plan: `lane-f-plan-v1`  
Corrected measurement commit: `8a5f5213e854d7520f1cbc306748462fa07445d0`  
Target: AMD Radeon 8060S Graphics (RADV STRIX_HALO), RADV / Mesa 26.1.2

## Outcome

The corrected F002 builder passes the strengthened structural validation and the
accepted timing campaign is stable.

The representative F001/I001 dynamic subset is `Nrep = 796` triangles.
Corrected accepted median builder time at Nrep is **99.929868 us**.

The F002 formal feasibility gate still remains **PENDING**, not PASS/FAIL,
because its frozen formula requires the run-local F001
`vanilla-software / moving-rigid` comparator, and that comparator was unstable
in both the initial artifact and the one permitted identical rerun. The
historical `2972.4075 us` ceiling remains reference-only.

## Correctness incident and superseded evidence

The original F002 artifacts appeared structurally correct but F003 validation
exposed 2,259 Hit mismatches in moving-rigid warmup. Investigation found:

- each LBVH leaf represented sorted primitive `keys_a[id].z`;
- leaf bounds incorrectly came from unsorted `aabb[id]`;
- the root union could therefore remain correct while leaf/internal traversal
  bounds belonged to different triangles.

The builder now indexes leaf bounds with the sorted primitive id. Validation was
strengthened to cover root identity, sorted leaf identity/AABB correspondence,
parent/child consistency and full tree reachability.

The original artifacts are retained for audit but are superseded:

- validation: `20260929T092619Z`
- timing: `20260929T092838Z`

This was a correctness repair only. No threshold, timing boundary or candidate
architecture criterion was changed after seeing performance data.

## Corrected artifacts

Validation:

`out/research/lane-f-dynamic-geometry-alternatives/002-pure-gpu-transient-lbvh-builder/20260929T121932Z`

Accepted timing:

`out/research/lane-f-dynamic-geometry-alternatives/002-pure-gpu-transient-lbvh-builder/20260929T124035Z`

## Corrected structural validation

Frozen sweep: Nrep plus 1k, 4k, 16k, 64k, 256k and 1M primitives.

- Vulkan validation errors: 0
- sort mismatches: 0
- root-count mismatches: 0
- root-index mismatches: 0
- root-bounds mismatches: 0
- leaf-mapping mismatches: 0
- topology mismatches: 0

## Corrected accepted builder timing

| primitives | median builder GPU | min | max | stable |
| ---: | ---: | ---: | ---: | :---: |
| 796 (Nrep) | 99.930 us | 99.790 us | 100.391 us | yes |
| 1,000 | 101.012 us | 100.571 us | 101.312 us | yes |
| 4,000 | 128.504 us | 128.424 us | 129.085 us | yes |
| 16,000 | 235.387 us | 235.147 us | 235.728 us | yes |
| 64,000 | 663.982 us | 663.360 us | 664.302 us | yes |
| 256,000 | 2663.942 us | 2629.476 us | 2674.081 us | yes |
| 1,000,000 | 12239.195 us | 12218.595 us | 12359.844 us | yes |

No frozen size exceeded the `max/min > 1.20` instability rule, so no corrected
F002 rerun is required.

## Nrep phase breakdown

At Nrep:

- scratch/reset management: 9.578 us
- current-frame dynamic input: 1.523 us
- AABB: 1.483 us
- page/local Morton: 1.403 us
- radix sort: 70.093 us
- topology: 14.588 us
- bottom-up bounds: 1.042 us
- complete builder: 99.930 us

Radix sort remains the dominant phase. No post-result F002 tuning is performed.

## Memory

For Nrep:

- persistent/template bytes: 50,944
- transient bytes: 178,256
- scratch bytes: 3,760
- peak builder bytes: 232,960

## Decision

F002 is concluded as:

- strengthened structural correctness: **PASS**
- repeatability: **PASS**
- corrected builder measurement: **COMPLETE**
- formal feasibility gate: **PENDING** due to the frozen F001 run-local
  moving comparator remaining inconclusive
- architecture promotion at F002: **none**
- F003 end-to-end validation/measurement: **may proceed**
- F004 activation: **not available**, because its frozen activation rule
  explicitly requires a formal F002 PASS

Proceeding to F003 does not reinterpret the unresolved F002 formal gate.
