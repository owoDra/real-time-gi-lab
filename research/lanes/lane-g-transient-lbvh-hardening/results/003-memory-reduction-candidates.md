# G003 — Memory reduction candidates

Status: **G003a implementation complete; target-GPU evidence pending**  
Candidate: `immutable-static-hwrt-build-input-release`

## Scope

G003a implements exactly one G001-justified lifetime change.

For the new `hardened-transient-lbvh` variant, the static HWRT portion is
immutable after its initial BLAS/TLAS build. Once the synchronously fenced build
has completed, these setup-only Vulkan allocations are destroyed:

- `static-hwrt.vertices`;
- `static-hwrt.instance`;
- `static-hwrt.scratch`.

The following remain resident and unchanged:

- triangle metadata used by traversal;
- BLAS storage;
- TLAS storage;
- transient-LBVH template/current-frame geometry;
- radix/key/node scratch;
- producer streams;
- C001 storage;
- exact Hit semantics.

The unchanged `transient-lbvh` variant remains the run-local control.
`combined-hwrt` keeps its update resources and is not modified by this candidate.

## Attribution gate

For every scenario, the run is accepted only when:

`unchanged_peak - hardened_peak`

equals, byte-for-byte, the unchanged candidate's counted allocations named:

- `static-hwrt.vertices`;
- `static-hwrt.instance`;
- `static-hwrt.scratch`;

and all three are absent from the hardened allocation census.

This prevents unrelated memory changes from being credited to G003a.

## Predeclared G001-derived expectation

Before the G003a target run, the deterministic G001 census predicts exactly:

| scenario | unchanged LBVH | setup-only bytes released | expected hardened | expected ratio vs vanilla | expected improvement |
| --- | ---: | ---: | ---: | ---: | ---: |
| sparse-stress | 119,078,592 B | 46,202,400 B | **72,876,192 B** | **1.887188x** | **38.80%** |
| sparse-moving | 123,668,160 B | 46,017,696 B | **77,650,464 B** | **2.010822x** | **37.21%** |

These are frozen before measurement. If the run-local unchanged/vanilla anchors or
the byte-exact hardened result differ, the evidence is invalidated for
investigation rather than re-baselined after seeing the result.

## Frozen replay

Variants:

- unchanged `transient-lbvh`;
- `hardened-transient-lbvh`;
- run-local `vanilla-software`.

Scenarios:

- static;
- moving-rigid;
- sparse-stress;
- sparse-moving;
- dense-moving.

Validation/correctness is required for every row.

## Memory gates

- sparse-stress and sparse-moving peak <= 3.0x run-local vanilla;
- >=10% peak-memory improvement vs unchanged LBVH in at least one formerly failing sparse regime;
- no required scenario peak-memory regression >10% vs unchanged LBVH;
- byte attribution exact.

## Timing status

G002 closed without a safe decision-valid timing protocol. Therefore G003a does
not reinterpret one-shot timing as a formal PASS/FAIL and does not use any
power/clock manipulation.

The Issue #17 timing retention gate remains unresolved. A memory/correctness
PASS can establish that this candidate solves the deterministic memory blocker,
but cannot by itself authorize G004/G005 promotion timing or a Lane E replacement claim.

## Result

Pending target-GPU artifacts.
