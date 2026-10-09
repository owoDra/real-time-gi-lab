# N006 P1h — matched canonical probe GPU performance: supported local win

Issue #42. **P1h diagnostic PASS for the one frozen stable-topology-deforming/HWRT workload; not yet general engine adoption.** User uploaded `n006-p1h-matched-canonical-summary.json` (2026-10-09), clean `research-n006-interval-aware-allocation` HEAD `ff2b80562640440befe3c664a831d5446ab0d75d`, target AMD Radeon 8060S Graphics (RADV STRIX_HALO). Protocol `n006-p1h-matched-canonical-performance-v1`, `status=complete`, `failures=[]`, `formal=false`. No path-traced reference regenerated.

## Pre-registered experiment and correctness gate

- Three fresh processes, each 32 source warmup frames + eight target-state current warmup frames, then 12 measured target-state frames in the frozen `011001100110` alternating current/canonical schedule: **36 measured frames, 18 balanced adjacent pairs**. All frames motion fraction=1, no topology churn and no traversal-maintenance GPU time during measurement.
- **All 36 measured PFM frames byte-identical** (SHA-256 `79de995078c605c8c5c6aef44c8565edf3f808e32934fd43646753bdba815861`). Every frame passed internal correctness, hit and storage checks, original owner count=4,172 and zero extra rays.
- Current: **133,504 traced ray work items, 16,688 outputs**; canonical: **24,232 traced rays, 3,029 outputs**. **81.849% fewer actually executed rays**, with original per-key owner count/quantized storage arithmetic reconstructed in every canonical frame, no errors/overflow.
- Non-overlapping GPU stage-timestamp closure all 36 frames to roundoff (max absolute closure error ~2.3×10^-13 µs). Per-candidate owner-weight stage was already included inside storage_update and never double-counted.

## Frozen paired GPU results: canonical minus current

| Scope | Matched pairs | Median delta (µs) | Min / max delta (µs) | Faster pairs |
| --- | ---: | ---: | ---: | ---: |
| **Post-producer GI-work subtotal**, including GPU hash+compact+copy and storage reweight | 18 | **−82.577** | −365.735 / −32.061 | **18/18** |
| Complete GI GPU | 18 | **−145.857** | −1195.552 / +469.612 | **14/18** |
| Complete renderer GPU | 18 | **−143.633** | −1190.462 / +455.786 | **14/18** |
| Primary visibility GPU (before compact stage) | 18 | −77.527 | −828.735 / +500.832 | 10/18 |

**Per-process medians (post-producer GI-work):** −82.296, −85.603 and −82.577 µs. This sign consistency survives changes in process and A/B order. Each process's complete-GI pair-median is negative (−338.363, −313.375, −51.237 µs) but whole-GI effect varies widely: primary visibility happened **before** canonicalization and accounts for much of the non-target variation. Four complete-GI comparisons were slower despite improved downstream GI work.

Across all 18 current frames, median post-producer GI-work time was **298.928 µs**; among canonical frames **215.229 µs** (unpaired distributions: descriptive only). Reduction in directly affected stage **~83 µs**, or roughly **28% of the baseline's typical ~299 µs**; this is a local, non-formal observation and not a formal net whole-engine percentage. The GPU canonical-build stage median was **59.713 µs** (54.303–63.521), owner-storage restoration stage median **~7.03 µs** (nested in storage_update). Thus the savings are **net of compaction overhead**, not an optimistic estimate based on 81.85% fewer rays.

Median pair-stage deltas for context: HWRT traversal −67.208 µs, radiance −20.399, ray preparation −14.447, merge −5.130, storage update (inclusive of restore) −21.040, resolve −13.766. The ~59.7 µs canonical build and other small changes offset some of those savings; stage deltas should not be added to median-of-pair results as if medians were linear.

## Interpretation and limitations

**Supported:** a bit-exact canonical probe×cascade deduplication path can run fewer GPU rays and reduce the targeted GI-work segment on *every frozen matched pair* in this AMD HWRT/deforming scenario, even after hash, copying, regrouping and original owner-weight restoration overhead. This is stronger than P1c's input-repetition hypothesis and P1g's single correct frame.

**Not yet supported:** uniform faster complete-GI/renderer throughput across variable primary visibility; speedups for static/camera/light/moving-rigid/high topology churn, HWRT-disabled software ray traversal or other GPUs; production memory budget (N006 adds ~8.03 MiB scratch not represented in legacy lifetime peak); or any predictive marginal-ray allocator. Do not claim a universal 28% speedup or generalize 81.85% repeated rays to other workloads.

## Decision / next gate

- **GO to prototype hardening and wider correctness validation**, rather than discarding canonical-probe tracing or promising production integration.
- **P1i (prospective):** first stress canonical probe equivalence under **static, camera/light changes, moving rigid, stable deforming and topology churn** using per-run *observed* unique-key/owner counts rather than baking in 4,172 owners/3,029 keys. Test storage invalidation, frame tags, integer owner multiplicities, probe-key pack limits, hash/table capacity fail-closed behavior, bitwise PFM vs current and peak memory budget. Attempt both HWRT and software traversal variants separately if supported; never silently substitute their correctness/time paths.
- Then **P1j** should remove redundant owner-local producer/copyback and reduce fixed 8+ MiB scratch by emitting canonical keys and eight work items directly on GPU, avoiding per-frame global sort; compare whole-GI and post-producer workload again under controlled primary visibility.
- Preserve all N004/N005 and P1a–P1h frozen evidence. Do not add GitHub Actions.
