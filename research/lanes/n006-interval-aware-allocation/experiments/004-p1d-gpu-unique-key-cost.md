# N006 P1d — GPU unique-key construction cost preflight

Issue #42. Status: **prospectively frozen diagnostic design, before new GPU results**.

## Motivation

P1c measured 109,272 exact repeated base ray inputs (81.849%), from 133,504 owner-local rays and 3,029 unique probe×cascade keys (24,232 unique eight-direction rays). This is an **input-identity opportunity**, not measured time savings; the observed complete GI time was 2,452.981 µs, traversal 145.196 µs in one unpaired snapshot. Older per-frame grouping/scheduler overhead risks are material.

Before changing the renderer to emit canonical probe rays, independently measure the GPU cost and correctness of identifying distinct probe/cascade keys.

## Frozen experiment

- Case: AMD Radeon 8060S RADV, clean N006 branch, stable-topology deformation with one target frame and 1 source warmup. No reference generation, no extra rays, no saved image deletion.
- Candidate: after the existing N006 baseline producer, perform a **diagnostic-only** fixed-size zero-initialized GPU hash insert of each existing base owner×cascade work block's ray-0 probe key. Packing / hash / open addressing matches the already accepted storage-key semantics. **Do not alter** ray work items, indirect dispatch, output identity, storage or final renderer image.
- Use at least 2× the configured maximum owner-output capacity for the hash table (power of two), 128 maximum probe attempts, fresh GPU clear each frame. Report allocated bytes, unique/duplicate counts per cascade, collisions and lookup failures. No silent fallback.
- Compare both CPU P1c counts and all four cascades' identities: expected unique keys **[1853,815,284,77]**, duplicates = **[2319,3357,3888,4095]** owner outputs. Invalid keys, hash insertion failures or mismatches INVALIDATE this preflight.
- Timestamp the **complete** GPU hash overhead including clear, barrier and insert pass. Also capture the same renderer's complete-GI GPU time for hashing disabled/enabled (inclusive) and byte-exact image consistency; do not use this as a speedup claim.
- Three A/B fresh-process pairs, alternate process order (A,B / B,A / A,B); every run (including slow/failed) retained with stdout, stderr, target evidence JSON and PFM. No cherry-picked exclusions. GPU timestamp primary.
- This is *not* a full dedup implementation. Hashing unique keys without compact canonical ray stream, scatter/owner-output mapping or alternate storage is a strictly partial cost; it cannot establish throughput gain.
- Never modify N004/N005 sources, historical evidence, GPU profile, sampling/quality thresholds or GitHub Actions.

## Decision gate

- **Pass to P1e design:** exact counts, zero errors and bit-identical final image; report paired hash overhead and complete-GI change. Only then separately design canonical-probe producer + per-key radiance/storage, with full correctness/quality and complete GI GPU cost vs baseline.
- **Refine:** correct counts but hash overhead is comparable to attainable ray-dependent stage savings or shows severe atomic contention. Investigate direct producer-owned probe hashing, sparse visibility and other GPU primary approaches without retrospective tuning.
- **Stop/invalid:** unsupported hash keys, collisions beyond bounded probing, wrong counts, changed baseline frame/pixels, or invalid device/provenance. Do not reinterpret wrong counts as “optimized” work.

Exact timing threshold for practical P1e viability should derive from repeated A/B data and cost model; no adoption decision from a single P1d sample. P1 original predictive signal question remains open but **should not receive new GPU campaign budgets** until work-unit duplication is accounted for.
