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

A first implementation review caught an important distinction: releasing setup-only
buffers reduces steady/runtime residency, but does not reduce the true lifetime peak
unless their setup lifetime is also scheduled before shared frame/stream/storage
allocations.

G003a therefore moves the immutable HWRT build earlier and freezes two phases:

- **setup peak** — immutable static HWRT BLAS/TLAS construction before shared
  integration allocations;
- **runtime resident** — post-setup static HWRT + shared integration + dynamic
  LBVH allocations.

The reported peak is `max(setup peak, runtime resident)`.

Before the target run, G001 predicts exactly:

| scenario | unchanged peak | runtime resident after release | setup peak | expected true peak | ratio vs vanilla | peak improvement |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| sparse-stress | 119,078,592 B | 72,876,192 B | 104,595,424 B | **104,595,424 B** | **2.708583x** | **12.16%** |
| sparse-moving | 123,668,160 B | 77,650,464 B | 104,233,440 B | **104,233,440 B** | **2.699209x** | **15.72%** |

Thus the candidate is still predicted to clear the <=3.0x sparse gate and the
>=10% improvement gate, but by much less than the naive post-setup subtraction
would imply.

These values are frozen before measurement. If the run-local anchors, released
lifecycle bytes, runtime residency, setup peak, or final peak differ, the evidence
is invalidated for investigation rather than re-baselined after seeing the result.

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
