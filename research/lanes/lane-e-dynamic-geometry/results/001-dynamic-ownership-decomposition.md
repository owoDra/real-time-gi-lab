# E001 — dynamic ownership decomposition result

Status: complete

## Provenance

- measurement branch: `research-lane-e-dynamic-geometry`
- measurement commit: `1fa902d48a8d6e693384f5911033683ebd342a00`
- tree: clean
- target: `AMD Radeon 8060S Graphics (RADV STRIX_HALO)`
- timing repeats: 3 per variant/workload
- validation pairs: 6
- all quality gates passed
- all storage-failure counts were zero

The supplied accepted-timing files did not include the outer
`research:record` metadata file, so this result does not invent a target-local
artifact directory. The summary/CSV retain the measurement Git provenance.

The frozen E001 GPU accounting gate passed for all 18 timing rows: the named
GPU maintenance components matched `traversal_maintenance_gpu_us` within the
predeclared `max(2 us, 1%)` tolerance.

## Moving-rigid

Median microseconds:

| Variant | Complete dynamic boundary | Dynamic update wall | Traversal maintenance GPU | Traversal |
| --- | ---: | ---: | ---: | ---: |
| vanilla software | 113842.184 | 112847.214 | 2523.956 | 838.273 |
| combined software / B003 | 103026.500 | 102654.674 | 2336.279 | 259.533 |
| combined HWRT | 6681.143 | 6473.228 | 3834.766 | 87.606 |

Relative to vanilla software at this diagnostic boundary, combined HWRT is
94.13% lower and combined software is 9.50% lower. These percentages describe
E001's synchronous diagnostic boundary and do not replace I001's historical
end-to-end frame result.

### HWRT rigid maintenance

Median GPU maintenance components:

| Component | us | Ratio |
| --- | ---: | ---: |
| geometry transfer | 2247.510 | 58.61% |
| surface update | 1100.611 | 28.70% |
| BLAS update | 430.778 | 11.23% |
| TLAS update | 40.878 | 1.07% |

By the frozen E001 gate, geometry transfer is the single dominant component.
Surface update and BLAS update are material. TLAS update is not material.

The current HWRT path therefore spends most rigid-maintenance GPU time rewriting
geometry that is unchanged in object space, then updates the scene-wide BLAS.
This is the ownership cost E002 must attack.

### Software rigid maintenance

Median CPU maintenance components inside the 102654.674 us dynamic-update wall:

| Component | us | Approx. wall share |
| --- | ---: | ---: |
| membership dirty processing | 979.233 | 0.95% |
| hierarchy rebuild | 79999.349 | 77.93% |
| packing / quantization | 15867.764 | 15.46% |

The workload changes 796 segment memberships and rebuilds a median 398
segments. The complete software rigid cost is therefore dominated by rebuilding
world-space hierarchy state and repacking it, not by B003 traversal itself.
This is the ownership cost E003 must attack.

## Deforming control

Median microseconds:

| Variant | Complete dynamic boundary | Dynamic update wall | Traversal maintenance GPU | Traversal |
| --- | ---: | ---: | ---: | ---: |
| vanilla software | 109974.536 | 109401.888 | 2315.079 | 483.919 |
| combined software / B003 | 35639.386 | 34910.802 | 2359.724 | 464.162 |
| combined HWRT | 6233.619 | 6024.221 | 3861.858 | 87.366 |

The deforming control changes 148 segment memberships.

HWRT still classifies geometry transfer as dominant at 58.08%, with surface
update at 28.69% and BLAS update at 11.95%. Unlike rigid motion, this geometry
really changes in object space, so eliminating the BLAS/geometry update is not a
valid general solution.

The B003 deforming path uses a mixture of refit (7897.709 us), rebuild
(5413.853 us), and packing (15230.363 us). It is materially different from the
rigid case and must remain a separate E004 boundary.

## E001 decision

E001 does not promote an architecture. It fixes the measured ownership
problems that subsequent experiments must target:

1. **E002 / HWRT rigid:** keep rigid-object geometry immutable in a reusable
   object-local BLAS and represent motion in TLAS instance state. Compare TLAS
   UPDATE versus BUILD without rewriting rigid vertices or updating the BLAS.
2. **E003 / software rigid:** keep rigid-object StrataBrick/Micro-BVH data local
   and stable, avoiding world-space segment membership rebuild and full
   repacking on rigid motion.
3. **E004 / deforming:** retain genuine local-geometry maintenance and determine
   the boundary where BLAS/local hierarchy updates remain necessary.

A001 schema/natural append semantics and C001 per-probe sparse storage remain
unchanged.
