# N006 P1e: timing closure PASS, whole-GI A/B causal timing NOT established

Issue #42. User-provided `n006-p1e-timing-summary.json` and all-frame `n006-candidate-evidence.json`, source clean HEAD `c76bf9780fe012782d180c0650b18b1dddeebf7c`, AMD Radeon 8060S RADV. Protocol `n006-p1e-disjoint-timing-v1`; 32 source warmups, 12 target frames fixed motion_fraction=1, hash flag `011001100110`, six frozen adjacent A/B pairs, no added rays/reference.

## Correctness and instrumentation

- `status=complete`; all 12 target PFM SHA-256s **identical** `79de995078c605c8c5c6aef44c8565edf3f808e32934fd43646753bdba815861`, zero source/target correctness failures, zero storage failures or substantive traversal mismatches.
- All six hash-enabled frames: unique keys 3,029, duplicate owner-cascade outputs 13,659, identical per-cascade counts `[1853,815,284,77]`, zero invalid key or failed hash insertion. Same P1c counts; 2,097,216 bytes scratch.
- Exported **non-overlapping** GPU stage sum equals complete-GI time in all 12 frames to rounding precision (< 2.3×10^-13 µs reported closure error).
- Hash clear+insert times: `25.609/25.168/25.889/26.931/25.889/20.519 µs`; median **25.749 µs**.

## Crucial A/B confounds

The original frozen P1e protocol presumed target frame 0 was a representative steady target frame after 32 source warmups. The source was first drawn in source geometry state. Frame 0 of target geometry performed an additional one-off `traversal_maintenance_gpu=1772.327 µs`; frames 1–11 have `traversal_maintenance_gpu=0` and `dynamic_update_wall=0`. Pair 0 (current frame 0 versus hash frame 1) is **not a matched-state timing comparison**, even though the images matched bitwise. It must be preserved as historical diagnostic, not silently omitted from reported P1e median.

The remaining five pairs do NOT establish that current-frame hashing slows GI by the whole-frame delta because the *primary visibility* GPU timestamp, which executes **before** the hash stage inside the same command buffer, is highly variable. On target frames 1–11, primary visibility spans **356.718 to 914.457 µs** although images/work counts match. That stage is earlier than probe production and hash insertion; its same-frame timestamp cannot causally include the later hash dispatch. Inter-frame GPU queue/clock/cache and scene-state effects remain possible.

| Pair | Whole-GI hash−current (µs) | Primary visibility hash−current (µs) | Hash cost (µs) | Dynamic GPU maintenance hash−current (µs) |
|---:|---:|---:|---:|---:|
| 0 (cold transition, invalid A/B) | −1238.994 | +418.235 | +25.609 | −1772.327 |
| 1 | +98.828 | +85.402 | +25.168 | 0 |
| 2 | +368.139 | +348.262 | +25.889 | 0 |
| 3 | +315.479 | +293.397 | +26.931 | 0 |
| 4 | +165.635 | +83.679 | +25.889 | 0 |
| 5 | −436.670 | −413.426 | +20.519 | 0 |

The raw summary median complete-GI delta is **+132.231 µs** over all six pairs, but includes invalid pair 0. A *descriptive post-hoc subset* excluding the known one-time transition has median **+165.635 µs** across five pairs; this is **not** a new formal median and does not isolate hash overhead.

This makes the earlier P1d whole-GI time differences plausibly dominated by unrelated primary visibility/dynamic state variation, although the cause of variation is not proven. P1d's earlier full-frame +421.6 µs should NOT be taken as measured hash pass overhead. Conversely, 25.7 µs hash pass does NOT establish any dedup speedup, as 133,504 base rays still run in both arms.

## Decision and next gate

**P1e instrumentation and hash correctness PASS. Full-GI A/B performance comparison REFINE/NOT COMPARABLE.** No ray elimination or software/HWRT performance improvement has been demonstrated.

**Prioritize an isolated probe-owner-value-equivalence correctness check** (N006-only GPU readback with no new path-trace reference) before engineering a canonical probe producer: verify all owners sharing `(probe_xyz,cascade)` actually have identical *merged 16-bit radiance sums and sample counts* for the same 8 base-ray inputs and reconstruct the exact GPU storage slot mean. If any key differs, reject naive canonicalization even if ray inputs match. If all equal, freeze a separate prospective canonical stream/merge/storage microprototype.

When measuring cost, isolate primary visibility as its own segment and compare a **ray-dependent GI subtotal**, also report complete renderer on state-matched frames with **target-state warmup** and enough repetitions for stable A/B. Never replace complete-GI performance with the ray-only subtotal when claiming end-to-end gains; both must be reported, with uncertainty.

All original N004/N005 and N006 P1a–P1e artifacts/thresholds unchanged, no GitHub Actions.
