# N006 P1d — GPU unique-key hash preflight completed

Issue: #42. Status: **correctness PASS; complete-GI timing interpretation REFINE.** Evidence received 2026-10-09, **non-formal P1d**, not a measured ray deduplication.

## Accepted user-supplied results

- Clean `research-n006-interval-aware-allocation` HEAD `2b862de49b8627e7d8bdbd4d91c312400c161019`, AMD Radeon 8060S Graphics (RADV STRIX_HALO), stable-topology-deforming, one warmup and one target frame per process, three rotated A/B pairs. No reference generated or extra rays.
- All three GPU hash passes produced **3,029 unique keys / 13,659 duplicate owner×cascade outputs**, per-cascade unique **[1853, 815, 284, 77]** and duplicate **[2319, 3357, 3888, 4095]**, exactly agreeing with P1c. Each pass: **0 failed inserts and 0 invalid keys**. Hash table = 524,288 slots, scratch allocation = 2,097,216 bytes; collision steps across runs: 15, 15, 25.
- All three complete final image PFM SHA-256s match between hash and current: `79de995078c605c8c5c6aef44c8565edf3f808e32934fd43646753bdba815861`. Three complete pairs, zero failures.

| Pair order | Current complete GI (µs) | Hash complete GI (µs) | Paired extra GI (µs) | Measured hash-only GPU stage (µs) |
| --- | ---: | ---: | ---: | ---: |
| current → hash | 2487.887 | 2508.847 | +20.960 | 24.527 |
| hash → current | 1898.928 | 2320.529 | +421.601 | 20.920 |
| current → hash | 1922.252 | 2557.820 | +635.568 | 30.578 |
| **Median** | n/a | n/a | **+421.601** | **24.527** |

## Interpretation / decision

1. **Hash correctness PASS**: unique probe-key construction on the GPU is feasible for this target workload. The measured auxiliary hash stage costs about **21–31 µs** with a median of **24.5 µs**, including hash buffer clear and barriers.
2. **Do not attribute the +421.6 µs median complete-GI delta to 24.5 µs of hash work.** Full-GI differences vary from +21 to +636 µs; current unmodified run times themselves span ~1,899–2,488 µs. The expensive unexplained component may be GPU timing variability, cache/occupancy effects, geometry maintenance, or non-hash stages. We do not have the raw per-stage timestamp exports in the uploaded summary to distinguish them.
3. **Neither algorithm is faster:** P1d deliberately runs every original ray and stores every owner output; it only adds a hash pass. The current +hash candidate *should* be slower. A hypothetical ray-count reduction (~81.85% from P1c) and its complete-GI saving remain unimplemented.
4. Earlier P1c example `traversal_gpu=145.196 µs` vs `complete_gi=2452.981 µs` underscores that a big ray-input redundancy is not a commensurate renderer-time redundancy. The hash scratch takes an additional ~2 MiB and would need a costed compact stream/gather strategy.
5. **Decision = REFINE the timing interpretation before engineering a canonical ray candidate**; not a STOP of the canonical-probe hypothesis, not a P1 predictive signal GO, and not permission to modify N004/N005.

## Immediate next action, no GPU runs

Add an *offline* `audit_p1d_stages.py` that loads all six retained `n006-candidate-evidence.json` files from the P1d output directory, strictly checks linkage to the uploaded summary, and reports per-pair changes in every existing exported GPU stage (`producer_gpu`, `ray_prepare_gpu`, `traversal_gpu`, `radiance_gpu`, `merge_gpu`, `storage_update_gpu`, `resolve_gpu`, `geometry_transfer_gpu`, `instance_transfer_gpu`, `blas_update_gpu`, `tlas_update_gpu`), as well as descriptive `dynamic_update_wall` (CPU wall only). The output also reports the *unexplained* complete-GI delta after subtracting the **non-overlapping known GPU hash stage** and the selected pipeline stage deltas, without pretending the residual is a single isolated physical stage.

Retain existing raw outputs untouched and write a new JSON. The determination between GPU clock/warmup variance, per-stage cache effects, and uninstrumented spans may remain unresolved after this audit; disclose that limit.

If timing variability remains large, the next *prospectively frozen* experiment should use same-process A/B GPU captures or finer timestamps and a broader calibration/control matrix before attributing candidate overhead. Only after cost attribution and bit-exact correctness should P1e canonical-probe tracing be implemented and measured against complete GI.

No old accepted research commits/thresholds rewritten, no GitHub Actions.
