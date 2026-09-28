# Experiment 001 — cheap query coherence for hash cache

Status: concluded — exact fused 16-bin mechanism rejected  
Milestone: M0 / Issue #7

## Question

Can the hash-cache baseline recover enough query coherence to beat
`hash/source` end-to-end without globally reordering the full query batch?

Experiment 000 already established that ordering matters and that matched-order
hash is the representation baseline. This experiment does not reopen that
decision.

## First hypothesis

A lookup workgroup may obtain useful coherence by grouping only its own queries
into coarse ranges of the **initial hash-table slot** before performing the
normal hash lookup.

The first variant uses:

- 256 queries per workgroup;
- 16 coarse bins;
- shared-memory-only grouping;
- one fused compute dispatch;
- results written back to each query's original output index.

There is no global grouping buffer, histogram/prefix/scatter pass, or additional
scheduler dispatch. The shader statically uses 5,248 bytes of shared memory per
workgroup and zero global scheduling scratch.

## Why this is first

### Producer-side coherence

This remains the preferred architectural direction once a real GPU query
producer exists. The current research harness constructs Query records on the
CPU and uploads them. Reordering those records on the CPU would only reproduce
the invalid "free preprocessing" shortcut, while building a synthetic producer
now would make the result depend on artificial producer-order assumptions.

### Workgroup-local grouping

The fused variant can be tested without assuming a future producer, query
lifetime, or consumer count. Its grouping cost is necessarily included in the
same timed dispatch as lookup, so the end-to-end gate is direct.

### Reusable/amortized scheduling

Experiment 000 suggests the current global scheduler needs multiple reuses before
its cost can be recovered at large query counts. Whether the future GI
architecture actually provides that stable query lifetime or consumer count is
not established yet, so that direction remains a follow-up rather than the first
implementation.

## Protocol

Keep the Experiment 000 controls and add `hash-wg-bin16`.

Required target-system procedure:

1. validation sweep at 100k / 500k / 1M / 4M / 8M, 3 repeats, 100 iterations;
2. require every row to pass semantic checksum correctness;
3. run the same matrix without validation for timing evidence;
4. compare `hash-wg-bin16` directly with `hash/source`;
5. retain the existing CPU page-grouped and GPU-global-grouped rows as context,
   not as the acceptance baseline.

The benchmark artifact layout remains:

- `metadata.json`
- `results.csv`
- `summary.csv`
- `logs/`

## Decision gate

Advance workgroup-local coherence only if `hash-wg-bin16` beats
`hash/source` end-to-end by a repeatable margin on meaningful query counts.

A regression, noise-level result, or benefit confined to validation runs rejects
this exact mechanism. Failure does not by itself reject producer-side coherence,
reuse/amortization, or a different local scheduling key.

Do not attribute any timing difference to a specific cache/memory mechanism
without representative RADV/RGP evidence.


## Accepted non-validation result — 2026-09-28

The target-system non-validation sweep completed successfully on AMD Radeon
8060S Graphics / RADV STRIX_HALO for the full 100k / 500k / 1M / 4M / 8M
matrix, 3 repeats and 100 iterations.

All rows passed checksum correctness. `hash-wg-bin16` additionally passed the
order-sensitive fingerprint comparison against `hash/source`, confirming that
the fused workgroup-local regrouping wrote each lookup result back to the
correct source-query index.

Accepted median timings:

| Queries | hash/source us | hash-wg-bin16 us | Speedup vs hash |
| ---: | ---: | ---: | ---: |
| 100k | 16.347 | 16.470 | 0.993x |
| 500k | 103.183 | 112.247 | 0.919x |
| 1M | 204.238 | 214.440 | 0.952x |
| 4M | 869.071 | 933.529 | 0.931x |
| 8M | 1888.290 | 2026.480 | 0.932x |

The fused 16-bin workgroup-local mechanism is rejected. Its grouping work is
already included in the timed lookup dispatch and it fails to beat
`hash/source` at every query count. The regression is material at the
medium/large query counts that motivated Issue #7.

This rejects only this exact local-binning mechanism. It does not reject
producer-side coherence, schedule reuse/amortization, or other local keys.


## Validation sweep — 2026-09-28

Artifact: `out/benchmarks/20260928T103947Z`

The full target-system validation matrix completed successfully on AMD Radeon
8060S Graphics / RADV STRIX_HALO.

All benchmark rows passed checksum correctness. `hash-wg-bin16` additionally
passed the order-sensitive fingerprint against `hash/source`, so the fused
shared-memory regrouping preserves source-index result semantics.

Validation-enabled medians were:

| Queries | hash/source us | hash-wg-bin16 us | Relative |
| ---: | ---: | ---: | ---: |
| 100k | 16.685 | 17.228 | 0.968x |
| 500k | 102.844 | 108.126 | 0.951x |
| 1M | 200.728 | 217.735 | 0.922x |
| 4M | 860.216 | 911.517 | 0.944x |
| 8M | 1687.670 | 1777.120 | 0.950x |

These timings are diagnostic only. The accepted performance decision is based
on the non-validation artifact `out/benchmarks/20260928T104108Z`.
