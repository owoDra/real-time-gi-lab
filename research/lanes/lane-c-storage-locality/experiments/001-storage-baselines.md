# Experiment C001 — Split RC storage baselines

Status: planned

## Question

Which sparse radiance representation offers the best foundation before
producer-side locality is applied?

## Hypothesis

A hashed contiguous brick pool may preserve sparse allocation while reducing
per-probe random access, but the previous M0 result means contiguous/paged
storage alone must not be assumed to win.

## Variants

Start with:

- per-probe open-addressed sparse hash;
- hashed contiguous brick pool;
- virtual/clipmap-style sparse storage.

Add a StrataBrick-inspired representation only when it is concretely distinct
from these variants.

## Protocol

- Keep semantic payload/update behavior identical across representations.
- Measure lookup, update, allocation/residency/invalidation, persistent bytes,
  and required scratch.
- Keep access order as an independent axis.
- GI-like synthetic streams are bring-up/controlled evidence only.
- Final promotion requires replay of Lane A's exact producer stream.
- Do not introduce a full global reorder as part of the candidate unless its
  complete end-to-end cost is counted.

## Correctness gate

All variants must return/update the same logical radiance state for the same
work stream.

## Decision gate

Retain candidates that show a plausible end-to-end or memory advantage without
requiring an ordering assumption the real producer has not established.
