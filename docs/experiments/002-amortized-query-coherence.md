# Experiment 002 — amortized query coherence

Status: concluded — conditional reuse threshold measured; not promoted as the primary architecture  
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

Performance from a row failing correctness is invalid. These semantic/grouping
guards run independently of Vulkan validation layers and remain mandatory in
normal non-validation timing runs.

## Required target sweep

Use the standard matrix:

- 100k / 500k / 1M / 4M / 8M queries;
- 3 process-level repeats;
- 100 timed iterations;
- accepted timing uses the normal non-validation sweep;
- Vulkan validation layers are optional diagnostics after Vulkan/API changes and are not a prerequisite for accepted timing evidence.

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


## Accepted result — 2026-09-28

Artifact: `out/benchmarks/20260928T120143Z`  
Hardware: AMD Radeon 8060S Graphics / RADV STRIX_HALO  
Scene: Sponza, 262,241 surface samples  
Iterations: 100  
Repeats: 3  
Vulkan validation layers: disabled

All benchmark rows completed with the mandatory semantic/grouping correctness
guards intact.

| Queries | hash/source us | reuse 2 | reuse 4 | reuse 5 | reuse 6 | reuse 8 | First tested win |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| 100k | 16.690 | 109.642 | 64.472 | 54.865 | 48.725 | 40.898 | none |
| 500k | 97.926 | 306.609 | 180.735 | 155.126 | 140.980 | 119.182 | none |
| 1M | 198.000 | 407.100 | 236.911 | 202.413 | 180.494 | 151.755 | 6 |
| 4M | 894.490 | 1605.430 | 973.209 | 864.097 | 767.316 | 671.462 | 5 |
| 8M | 1801.480 | 3036.690 | 1872.800 | 1649.870 | 1523.340 | 1306.910 | 5 |

The 4M reuse-5 win is only about 3.5%, so it is not a strong architectural
margin by itself. Reuse-6 is materially stronger at 4M, and reuse-5 is already
about 9.2% faster at 8M. At 100k and 500k, even reuse-8 does not break even.

## Decision

The existing global scheduler is **not promoted** as the default coherence
mechanism.

It remains a conditional fallback only when a real GI architecture naturally
keeps a large query population alive for roughly five to six or more consumers.
That lifetime has not been established and must not be assumed.

The stronger result from M0 remains that coherent access can substantially
improve hash lookup, while manufacturing that coherence after query production
is too expensive. The next research program therefore moves to a real Split
Radiance Cascades producer and evaluates storage, traversal, and producer-side
locality on the resulting access stream.
