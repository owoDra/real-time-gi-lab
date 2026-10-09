# N006 P1h — prospective matched-state canonical-probe performance pilot

Issue #42. **Protocol frozen before any P1h GPU measurement.** Prior P1g run is accepted for correctness only: canonical 24,232 rays vs 133,504 original, bit-exact 320×180 PFM, ~132 µs compact-build and ~10.5 µs owner-storage weighting on that unpaired candidate frame. P1g's first current target incurred >1 ms one-off dynamic maintenance; its 1.8 vs 1.05 ms comparison is invalid for speed.

## Frozen experimental setup

- GPU: AMD Radeon 8060S (RADV STRIX_HALO), RADV. Accepted Sponza digest and current N006 `deforming-control`/LaneEFinalHwrt workload, motion fraction=1, no independent reference, 0 added rays.
- **3 fresh processes**, each with 32 source-state frames then **8 target-state frames** (all current mode) to consume one-off geometry maintenance. Warmup itself is diagnostic and not included in timed A/B statistics.
- In each process, 12 measured **same-process** target-state frames, alternating canonical active flags `011001100110`, with frozen adjacent pairs (0,1), (2,3), ... (10,11). There are 6 A/B pairs per process, **18 frozen pairs across 3 processes**, no adaptive sample stopping. Pair order alternates within a process. Target-state camera/light/geometry remain fixed across all measured frames.
- All warmup frames must return accepted correctness and stable visible owner/ray count; all measured frames require bit-identical PFM SHA to the first frame and all other frames/processes, 4,172 visible owners, 133,504/16,688 current ray/output counts or 24,232/3,029 canonical ray/output counts, no storage/overflow/traversal/hash/weighting errors, original owner total 16,688 reconstructed for each canonical frame.
- Each measured frame must have `traversal_maintenance_gpu == 0`, `moved_primitives==796`, `topology_mutations==0`; if not, mark the **whole campaign invalid** and preserve all logs. Do not exclude individual slow frames or tune motion/source warmup retroactively.
- GPU timestamp primary. Record **complete GI GPU**, complete renderer, primary visibility, producer, exclusive canonical build (`timestamp4→19`), exclusive ray preparation (`timestamp19→5`), HWRT traversal, radiance, merge, storage update (includes owner restoration), invalidation, resolve, composite, plus separately owner-weight restore stage (nested within storage update). Require the disjoint GPU stage sum reconstructs complete GI to ≤1.0 µs. Never add the nested owner-weight interval twice.
- Compare (a) paired complete-GI times (end-to-end) and (b) a **post-producer GI-work subtotal** = canonical build + ray preparation + traversal + radiance + merge + storage update + invalidation + resolve; this excludes primary visibility, geometry maintenance and producer, to diagnose actual net savings in the portion affected by canonicalization.
- All six A/B pairs per process and all 18 process-balanced comparisons retained. Report arithmetic per-pair and per-process deltas, 18-pair median, full range and unmodified raw sample values. These are **preliminary** results, not a formal performance win; GPU clock/thermal drift and owner hashing overhead may remain.
- Stop and preserve evidence on *any* wrong input/byte drift, GPU hash/weighting error, count discrepancy or timestamp closure failure. No deletion of historical P1a–P1g outputs. Do not change original N004/N005 sources or add GitHub Actions.

## Interpretation gates

- **P1h measurement PASS:** 36 matched target frames and 18 balanced pairs are correct and timing closure holds; report both GI and post-producer subtotal variability. The candidate is only worth further engineering if both whole-GI and the target GI-work subtotal consistently improve despite ~8 MiB scratch, not merely because ray count shrank.
- **REFINE:** substantial variation in primary visibility overwhelms whole-frame effect despite reproducible post-producer improvement; consider controlled replay, more fresh processes and a GPU instrumentation intervention that isolates shader costs, without changing the quality contract.
- **STOP/INVALID:** any mismatched image/sample/owner/storage, cold target frame, nonzero hash/weighting error, changed renderer workload, missing evidence, or stage accounting inconsistency.

## Reuse boundary

This tests one fixed deforming workload only; passing P1h does not establish viability for topology-changing, moving-rigid, static or HWRT-unavailable software traversal. Separate dynamic robustness and backends must be prospectively validated before merging canonical behavior into a general renderer. P1 predictive allocation value/conditional P2 remain independent.
