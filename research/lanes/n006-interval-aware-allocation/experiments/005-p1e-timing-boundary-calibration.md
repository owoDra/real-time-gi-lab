# N006 P1e — same-process GPU timing-boundary calibration

Issue #42. **Prospective design, no GPU results at creation**. Independent of accepted P1a–P1d raw campaigns. Diagnostic only; not a deduplicated-ray benchmark or allocator result.

## Motivation and correction to P1d accounting

The completed P1d offline audit found paired complete-GI (+20.960/+421.601/+635.568 µs) and hash-clear+insert (+24.527/+20.920/+30.578 µs) deltas. Many contributions were unexported. **Important code audit:** In the historical P1d implementation, `ray_prepare_gpu` measured query 4→5 and therefore *includes the hash pass* inserted between producer and ray preparation. The initial P1d offline stage audit incorrectly subtracted both intervals separately. The corrected residuals are **+12.424/+375.834/+615.489 µs**, not the old **−12.103/+354.914/+584.911 µs**; no historical evidence rewritten. This does not resolve the large unexplained variation in the two slower cases.

## Frozen prospective P1e

- Target: AMD Radeon 8060S Graphics (RADV STRIX_HALO), `deforming-control`, `LaneEFinalHwrt`, one process/runtime. Warm up **32 source frames** in current mode. Then run **12 target frames** at *identical* motion fraction 1.0; hash activation fixed sequence `0,1,1,0,0,1,1,0,0,1,1,0` (0=current, 1=current+hash). No extra rays, no new reference.
- A/B frames are adjacent in one process, with six frozen pairs `(0,1),(2,3),(4,5),(6,7),(8,9),(10,11)`; alternate hash/current order in consecutive pairs.
- Main renderer and N004/N005 algorithms unchanged. A new **N006-only timing query after the hash pass and before ray_prepare** splits `hash_gpu` from exclusive `ray_prepare_gpu`. Export *all* disjoint GPU stage timings: primary visibility, depth, frame init, visibility reuse, producer, extra hash, pure ray preparation, traversal, radiance, merge, storage update, invalidation, resolve, and separately dynamic update GPU. Include composite separately (complete renderer includes it). The sum of these stage times must reconstruct complete GI, with a small GPU timestamp roundoff tolerance. GPU hash inclusive clear+barriers; do not double count.
- Verify each current/hash frame has identical SHA-256 PFM **to all other 11 target frames** and source/frame correctness, zero overflow/storage/traversal errors, same work count and visible owners. Every hash-active frame must have unique [1853,815,284,77], duplicate [2319,3357,3888,4095], zero insert failures/invalid keys; every inactive frame must have no hash stage.
- For each pair retain full independent frame timings, the direct complete-GI delta, hash clear+insert delta, exclusive ray-prepare delta, other disjoint GPU stage deltas and dynamic update GPU delta (CPU wall separate). Retain all samples; do not select best/fastest frames.
- One process can be sensitive to thermal/geometry history: *do not claim formal timing advantage*. If timestamps, images or work counts drift across successive target frames, mark this prospective diagnostic invalid and preserve evidence. The next study would need a different fixed-state replay, not post-hoc exclusion.

## Gate

- **PASS boundary**: all 12 frames correct and bit-exact, all six paired comparisons have full nonoverlapping timestamp accounting and matching GPU hash counts; then evaluate whether the 21–31 µs grouping overhead is realistic relative to ray-dependent stages before implementing a true canonical-probe producer.
- **REFINE**: large unexplained stage drift or geometry/warmup effects despite stable image; retain all evidence; do not declare hash performance from pair medians.
- **INVALID**: incorrect input/device/branch, image changes, work/counter/collision failure or incomplete captures.

Original N006 allocation-signal GO remains closed. No N004/N005 edits, no GitHub Actions. This is a cost-calibration subexperiment only.
