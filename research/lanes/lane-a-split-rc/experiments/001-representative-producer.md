# Experiment A001 — representative Split RC producer stream

Status: target-GPU correctness and repeated timing measured; result artifact path reconciliation pending

## Question

Can we build a minimal Split Radiance Cascades producer whose GPU-generated
probe/ray/cascade work is representative enough to become the shared workload
for traversal and storage experiments without manufacturing a favorable order?

## Hypothesis

A visibility-driven Split RC producer will exhibit measurable natural spatial
and cascade locality even before any explicit global reordering.

## Implemented protocol

- Load actual scene triangles and derive centroid + geometric-normal samples.
- Project those samples on GPU and select one nearest visible surface per screen tile using depth + deterministic owner tie-breaking.
- Run one GPU producer invocation per source surface. Visible owners atomically reserve output/work blocks; the resulting inter-block append order is not sorted on CPU or reordered globally afterward.
- Derive probe identity from scene-relative cascade spacing.
- Emit versioned replay items containing probe, cascade, ray interval/direction, output, scene surface, and visibility tile identity.
- Run GPU `producer -> gather -> merge -> resolve`.
- Gather intentionally uses a simple analytic direct-light control rather than selecting a traversal architecture; traversal remains Lane B's question.
- Resolve is checked against an independent CPU semantic reference before any timing is accepted.
- Measure visibility, producer emit/finalize, gather, merge, resolve, producer-total, end-to-end, persistent/transient bytes, per-cascade work counts, and natural adjacent locality.
- Run static camera, camera-motion, and changing-light cases.
- Export each passing observed stream using `stream-schema-v1.md`.

Synthetic input remains available only for bring-up and is not acceptable as
A001 architectural evidence.

## Correctness gate

All three must pass:

1. GPU visibility owner corresponds to the CPU nearest-depth reference for each visible tile.
2. Every GPU work block matches the expected visible surface, probe identity, cascade, ray, interval, direction, and unique output range; no overflow or output holes are allowed.
3. GPU gather/merge/resolve matches the CPU reference within the explicit resolve tolerance.

A failed correctness gate invalidates the performance measurements and prevents
stream export.

## Decision gate

Advance schema v1 as the shared Lane B/C workload only after target-GPU runs
show that:

- the real Sponza static, camera-motion, and changing-light cases all pass correctness;
- producer cost is reported rather than excluded;
- stream artifacts are replayable;
- measured locality is from the natural GPU append order;
- no CPU sort/global reorder was introduced to improve locality.

Target-GPU diagnostic validation on AMD Radeon 8060S Graphics (RADV STRIX_HALO)
at commit `c412ab047876967e81e1884b2abbb4f55a817a3f` passed visibility,
producer semantics, and resolve correctness for static, camera-motion, and
light-motion. This confirms the semantic gate and stream export path on the
target GPU.

A subsequent validation-disabled repeated run at commit
`8b647ef8dcf1150f86a9d25c039ca48bd7f30b8f` also passed all three
correctness gates. Its uploaded summary records the representative timings and
locality used by the provisional result.

The uploaded summary did not contain the harness artifact root, iteration count,
or validation flag, so the result cannot satisfy the shared protocol's raw
artifact traceability requirement from the file alone. The runner now records
those fields in `summary.json`; once the original artifact path is reconciled,
A001 can be marked fully accepted without rerunning if the operator confirms the
recorded run conditions.
