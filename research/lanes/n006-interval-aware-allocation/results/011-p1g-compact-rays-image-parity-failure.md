# N006 P1g — actual GPU ray reduction achieved, bitwise image parity FAILED

Issue #42. User GPU evidence: `n006-p1g-canonical-summary.json`, `n006-candidate-evidence.json`. Clean `research-n006-interval-aware-allocation` at `42bb421b048364575a6124059e3b4c0eca2592b7`, AMD Radeon 8060S RADV Mesa 26.1.2, deforming-control, 32 source warmups, original target frame then canonical target frame, motion_fraction=1 for both, no reference rendering.

## Frozen observations

- Current baseline: 4,172 visible owners, **133,504 ray work items**, 16,688 owner outputs; GPU storage_updates=16,688; image SHA256 `79de995078c605c8c5c6aef44c8565edf3f808e32934fd43646753bdba815861`.
- P1g canonical: same 4,172 owners, **24,232 actual dispatched ray work items**, 3,029 unique probe×cascade outputs; storage_updates=3,029; correct cascade uniques [1853,815,284,77], 13,659 duplicate owner outputs removed. GPU key errors, insert failures, capacity overflows, substantive traversal mismatch and storage failures all zero. Full frame internal correctness true.
- Canonical image SHA256 `9d77e5f1f25db0396d47924aa2e4909d8363451606e39eb1951dae519af19a64` **differs**. Official pilot status `invalid-image-mismatch` — **P1g BITWISE CORRECTNESS NOT PASSED**.
- Canonical GPU build+compact+copy/counter stage 54.183 µs; descriptive complete-GI baseline frame 2,563.911 µs vs canonical second frame 1,018.776 µs. The baseline frame performed **1,868.430 µs dynamic GPU maintenance** whereas canonical second frame performed 0: these are **not matched-state A/B timings and provide NO speedup evidence**.
- Baseline storage_allocations=96, invalidations=75, while canonical subsequent frame allocations=2 and invalidations=2. Hash-slot history and persistent probe-set turnover must be checked if quantization parity correction alone fails; source/canonical scene/ray metadata and owner output equivalence previously passed P1f.

## Source-based mechanism to test prospectively

P1f showed every owner of a shared probe had the same merged integer sum, count and rounded mean. But accepted composite reads a spatial slot as:

`float(slot.data.y) / (float(slot.data.z) * 65535.0)`.

Original storage on a key shared by `m` owners contains `data.y = m × rounded_mean`, `data.z = m`. Initial P1g instead stores `data.y = rounded_mean`, `data.z = 1`. These are **mathematically** equivalent but can differ by float32 ULP due to two different rounding sequences, notably when `m * 65535` exceeds 2^24 (P1c found multiplicity as high as 275). A float32 numerical thought-check for `m=275, mean=3` produces a difference of one float32 ULP. **This is a plausible cause, not yet demonstrated as the actual pixel discrepancy.** Missing PFM image-diff metrics prevent exclusion of other causes.

## Repair gate: restore accepted owner multiplicity in P1g-only GPU storage

Keep compact 24,232 ray work items and one radiance sample per distinct key. Count the original owner cardinality `m` directly in the GPU canonical key hash; after existing storage accumulation for 3,029 unique outputs, use one N006-only stage to multiply each matching **live** storage slot's integer `data.y` and `data.z` by `m`. Validate exact key, current frame tag, count=1 before weighting, no overflows/lookup failures, all 16,688 owner counts reconstructed by grouping. This restores the original integer numerator/denominator and should preserve the accepted composite arithmetic without changing any N001/N004/N005 shader. The existing original current mode must remain byte-for-byte unchanged.

Then rerun **same frozen P1g case with new repair commit**, retaining both raw PFM images and reporting bitwise equality. Before any claim of correctness add an offline per-channel/PFM difference report for failed comparisons; if failure persists, inspect spatial slot and primary-hit parity instead of changing acceptance thresholds.

P1g remains **INVALID** until confirmed bit-exact on GPU; P1h performance/dynamic claims remain CLOSED. No GH Actions, no historical artifact rewrites.
