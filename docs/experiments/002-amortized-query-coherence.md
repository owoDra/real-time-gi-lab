# Experiment 002 — amortized query coherence

Status: implemented — awaiting target-system validation and timing  
Milestone: M0 / Issue #7

## Question

If a coherent query ordering can be reused by multiple consumers, how many
consumers are required before the existing GPU page-grouping scheduler beats
`hash/source` end-to-end?

This is a **sensitivity experiment**, not a decision to make query populations
persistent. The lifetime and consumer count of future GI queries are still
unknown.

## Why this experiment is next

Producer-side coherence remains the preferred architectural direction, but the
current harness has no representative GPU GI producer. Adding one only to emit
a favorable order would bake the desired result into a synthetic producer and
would not establish that the future GI architecture can obtain that order
cheaply.

Experiment 001 also rejected the tested 256-thread / 16-bin workgroup-local
mechanism. Another local binning variant would repeat similar synchronization
cost without a stronger independent hypothesis.

The existing global scheduler is already correctness-guarded and is known to
produce useful page grouping. Reusing that ordering therefore isolates one
remaining question with minimal new machinery: **what reuse count is actually
required to amortize its measured cost?**

## Hypothesis

For sufficiently many consumers of the same query population, paying the
existing GPU grouping cost once and reusing the resulting query order can become
faster than performing the same number of unordered `hash/source` lookups.

The experiment does not assume that such a reuse count is available in a real
renderer. It establishes the threshold that a later GI architecture would have
to satisfy.

## Protocol

Keep the Experiment 000/001 controls unchanged.

For the hash representation, measure these reuse counts:

- 1 — existing `hash-gpu-page-grouped` row;
- 2;
- 4;
- 5;
- 6;
- 8.

For reuse count `N > 1`, each timed iteration records:

1. one complete GPU page-grouping pass;
2. `N` grouped hash lookups using the resulting query buffer.

The grouping pass is **not** repeated between those `N` consumers.

The benchmark reports the measured batch cost divided by `N` as
`end_to_end_gpu_us_per_dispatch`. This makes the direct comparison against
`hash/source` equivalent to comparing:

`schedule_once + N * grouped_lookup`

against:

`N * hash_source`.

The result must come from the combined command-buffer timing. Do not infer the
decision only by adding independently timed scheduler and lookup medians.

## Correctness

All existing correctness guards remain mandatory:

- GPU grouping must preserve the exact query multiset and monotonic page order;
- grouped hash lookup must match the shared semantic checksum;
- every reused end-to-end row must also match that checksum.

Performance from a row failing correctness is invalid.

## Required target sweep

Use the standard matrix:

- 100k / 500k / 1M / 4M / 8M queries;
- 3 process-level repeats;
- 100 timed iterations;
- validation sweep first;
- identical non-validation sweep for accepted timing evidence.

Artifact layout remains unchanged:

- `metadata.json`
- `results.csv`
- `summary.csv`
- `logs/`

## Decision gate

For each query count, identify the smallest tested reuse count whose amortized
end-to-end cost beats `hash/source` by more than repeat-to-repeat variation.

A break-even point does **not** prove that reusable scheduling is viable for GI.
It only establishes the minimum stable query lifetime / consumer multiplicity
that a future architecture would need to provide.

If even eight consumers do not beat `hash/source`, stop treating the current
global scheduler as a plausible reusable path.

Producer-side coherence remains the preferred direction once a representative
GPU producer exists. Do not build a synthetic producer solely to manufacture a
coherent order.

Do not attribute any timing result to a specific cache or memory mechanism
without representative RADV/RGP evidence.
