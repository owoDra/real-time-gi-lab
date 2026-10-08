# N006 P1c — exact base-ray-input multiplicity accepted

Issue #42. Status: **P1c measurement complete; source-level ray redundancy confirmed; GPU dedup performance not measured.**

## User-provided GPU evidence

- Branch `research-n006-interval-aware-allocation`, clean HEAD `236d97bfa6d684fdd78573b26c803355c3300db6`, target GPU AMD Radeon 8060S Graphics (RADV STRIX_HALO), Mesa 26.1.2.
- Protocol `n006-p1c-multiplicity-v1` / underlying `n006-probe-multiplicity-v1`. One target frame, source warmup = 1, stable-topology deforming with `mode=current`, **zero extra rays**, reference generation skipped. Source and target renderer internal correctness true, no substantive traversal mismatch, overflow or storage failure.
- Visible owners: **4,172**. Four cascades, eight fixed base directions per owner/cascade, **133,504** base ray inputs and 16,688 owner/cascade outputs.
- All four cascades independently report `same_probe_ray_inputs_identical=true` for the same `(probe_xyz,cascade)` key (probe position, interval and all eight ray directions). This validates exact input identity **in this one frame**, not runtime uniqueness/physical speedup.

| Cascade | Owner outputs | Unique probe keys | Unique base-ray inputs | Repeated base-ray inputs | Max owners per key |
| --- | ---: | ---: | ---: | ---: | ---: |
| 0 | 4,172 | 1,853 | 14,824 | 18,552 | 12 |
| 1 | 4,172 | 815 | 6,520 | 26,856 | 39 |
| 2 | 4,172 | 284 | 2,272 | 31,104 | 86 |
| 3 | 4,172 | 77 | 616 | 32,760 | 275 |
| **All** | **16,688** | **3,029 distinct (probe,cascade) keys** | **24,232** | **109,272** | **275** |

**Repeated base-ray-input fraction: `109272/133504 = 0.8184923298178332` (81.85%).** The theoretical count after *perfect* canonicalization is 24,232 (18.15% of the original rays), i.e. 5.51× fewer traced ray inputs. The 5.51× refers to **ray count, not speed**.

The one-shot `n006-candidate-evidence.json` showed: complete GI `2452.9806936950681 us`, complete renderer `2479.7114825248714 us`, producer `60.354674629211424 us`, ray prepare `20.999900070190428 us`, traversal `145.19587395858764 us`, radiance `25.24797145843506 us`, merge `7.7747721633911135 us`, storage update `40.116221317291263 us`. These are **descriptive timings only** and not formal comparators.

**Important scale limit:** Even eliminating the complete measured traversal stage at zero overhead cannot save more than its `~145 us` stage contribution on that frame (about 5.9% of complete GI), assuming other stages were unchanged. Real cost also includes hash/compaction/gather/synchronization and occupancy; deduplicating 81.85% of ray inputs can produce much less than 81.85% end-to-end gain, or be slower.

## Source-based architectural conclusion

The 8 base directions are fixed per owner/cascade. Spatial lookup and radiance response operate on probe key, not on screen owner. Repeated base-ray work comes from the **producer creating an owner-local output per visible owner for a shared probe**, and merge/storage then averaging those identical outputs again. A canonical **probe×cascade** ownership unit is thus more natural for a potential no-quality-change optimization.

However, preserving the accepted renderer's output behavior requires proof of all of:
1. duplicate owners really compute identical *integer radiance contributions* and hit results, not just input rays, across every supported case and device;
2. one canonical sample per key gives bit-identical final stored mean and rendered pixels, including integer rounding and storage invalidation/temporal frame identifiers;
3. dynamic scene/visibility changes and owner eligibility produce correct live keys, even for non-visible probes and stale storage slots;
4. complete-GI GPU time, including unique-key generation/hash, dispatch and scatter/merge/storage changes, improves across controls and dynamic workloads without violating memory budgets.

N006 P1a/P1b demonstrated a serious weakness of owner-local causal ray allocation; their reference checks remain unmodified. The 81.85% duplicated work is **not by itself approval to replace the accepted producer or trace path**.

## Next prospective gate

Before a complete canonical-probe renderer variant, compare at least these cost models:

- A GPU **hash-insert/unique-key** pass over original base owner/cascade work, with fresh-frame hash table clear, collision/failure counters, per-cascade unique counts, GPU timestamp and peak allocation; **this only measures part of the dedup overhead, not the full candidate cost**.
- A GPU-native producer that emits unique probe/cascade rays directly into a compact work stream and writes storage once per probe, avoiding the old owner-output/merge overhead instead of paying to reconstruct a 16,688-output prefix.
- Current owner-based baseline on identical frame/scene, with fresh-process repetitions if early results justify a formal candidate. The old N005 global reorder and GPU grouping overhead failures are directly relevant: avoid any plan relying on per-frame global sorting of all 133,504 rays without a cost model.

A minimal P1d design should freeze its case, clear timing, data validation and STOP gate **before** new GPU target runs. Defer P1 signal-ranking and P2 ray allocation until the system's work unit and cost model are corrected; do not silently relabel canonicalization as proven ray-allocation success.

No N004/N005 edits. No GitHub Actions. No deletion or rewriting of P1a–P1c raw evidence.
