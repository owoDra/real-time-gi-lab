# Experiment 001 — cheap query coherence for hash cache

Status: ready for target-GPU measurement  
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
