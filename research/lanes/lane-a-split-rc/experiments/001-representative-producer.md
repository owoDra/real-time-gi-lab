# Experiment A001 — representative Split RC producer stream

Status: planned

## Question

Can we build a minimal Split Radiance Cascades producer whose GPU-generated
probe/ray/cascade work is representative enough to become the shared workload
for traversal and storage experiments without manufacturing a favorable order?

## Hypothesis

A visibility-driven Split RC producer will exhibit measurable natural spatial
and cascade locality even before any explicit global reordering.

## Protocol

- Use actual scene/visibility inputs rather than a preconstructed sorted query list.
- Generate work on GPU.
- Preserve the natural emission order.
- Record stable per-work-item fields sufficient for replay: frame/workload id,
  cascade, spatial/probe identity, ray direction/interval, and output identity.
- Add a reference path that establishes semantic correctness independently of
  the optimized implementation.
- Measure producer time, item count, persistent/scratch bytes, and natural
  locality distributions.
- Include at least static camera and camera-motion cases.

## Correctness gate

The produced work and minimum gather semantics must match the defined reference
within the experiment's explicit numerical tolerance.

## Decision gate

Advance the stream as the shared Lane B/C workload only if its semantics are
representative of the intended Split RC design and its ordering has not been
introduced solely to benefit a storage/traversal candidate.
