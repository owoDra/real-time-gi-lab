# J003 CPU structural gate result

Status: **PASS — CPU structural precondition complete; target-GPU validation next**

Evidence artifact:

- local artifact: `j003-cpu-structural.json`
- SHA-256: `9fd834091e10d878d2b41a44ed3e2741cafb92b49491058e345a4b9e817a2233`
- schema version: 1
- scope: cluster ownership / split / merge / locality invariants only
- formal timing decision: false
- GPU validation required: true

## Result

The canonical J002 snapshots replayed through the J003 CPU reference model
without structural invariant failure.

Across all 5 profiles and 40 snapshots:

- persistent empty clusters: **0**;
- cluster maximum violations (>64 triangles): **0**;
- unaffected-cluster rebuild count: **0** in every snapshot;
- split path exercised: **1556** splits total;
- merge path exercised: **1061** merges total;
- v1.2 empty-cluster retirement path exercised: **422** retirements total.

The v1.2 empty-cluster lifetime correction is therefore part of the canonical
workload behavior rather than a synthetic-only edge case. Retirements occur in
the local-churn profiles, including large-local-high.

## Profile summary

| profile | snapshots | occupancy min..max | splits | merges | empty retires | rebuilt triangles |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| small-global-high | 8 | 17..57 | 4 | 3 | 0 | 914 |
| medium-global-representative | 8 | 19..64 | 35 | 31 | 0 | 5,692 |
| medium-local-high | 8 | 22..58 | 68 | 40 | 24 | 5,469 |
| large-global-high | 8 | 24..64 | 712 | 688 | 0 | 58,574 |
| large-local-high | 8 | 23..64 | 737 | 299 | 398 | 51,075 |

## Interpretation limits

This result proves only that the frozen CPU clustered reference can preserve the
declared ownership, occupancy, split/merge and unaffected-cluster invariants on
the canonical topology sequences.

It does **not** establish:

- GPU exact Hit correctness;
- traversal correctness;
- A001/C001 end-to-end correctness;
- GPU allocation lifetime correctness;
- memory acceptance versus Lane E HWRT rebuild;
- performance or crossover superiority.

No candidate ranking is permitted from this result.

## Promotion

The GPU-independent Lane J preflight is complete.

The next research boundary is J003 target-GPU prototype implementation and
exact end-to-end validation under `experiments/003-gpu-prototype-gate.md`.

J004 formal timing remains blocked on Lane I / I004 and its precommitted
promotion gate.
