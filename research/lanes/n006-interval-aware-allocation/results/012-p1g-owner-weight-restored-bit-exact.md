# N006 P1g repaired — actual canonical rays, bit-identical image

Issue #42. **P1g single-scenario correctness PASS, performance NOT ESTABLISHED.** Uploaded `n006-p1g-canonical-summary(1).json` and `n006-candidate-evidence(4).json`. Source: clean N006 branch `afeac5bb4fbe3771960cb96f2b8994e6e261830e`, AMD Radeon 8060S (RADV STRIX_HALO), RADV Mesa 26.1.2. Workload: `deforming-control`, 32 source warmups, two successive motion=1 target frames (first baseline current, second canonical). Reference generation skipped.

## Verified outcomes

| Metric | Current target | Canonical target |
| --- | ---: | ---: |
| Visible owners | 4,172 | 4,172 |
| Actual GPU base ray work items | 133,504 | **24,232** |
| Owner/probe outputs | 16,688 | **3,029** |
| GPU spatial storage update calls | 16,688 | 3,029 |
| Complete GI GPU (µs, unpaired cold/warm) | 1,838.613 | 1,051.879 |
| Traversal maintenance GPU (µs) | **1,155.796** | 0 |
| Primary visibility GPU (µs) | 315.279 | 484.681 |
| Traversal GPU (µs) | 131.249 | 243.463 |
| Radiance GPU (µs) | 20.479 | 7.494 |
| Merge GPU (µs) | 7.053 | 4.609 |
| Storage update GPU (µs) | 34.465 | 26.370 |
| Composite GPU (µs) | 30.057 | 62.479 |

- Exact repeated base ray input savings: **109,272 / 133,504 = 81.84923298%**. Canonical hash/compact/copy/counter GPU stage: **132.0509 µs** on the canonical target. Owner-weighted storage restore stage (nested inside storage update): **10.5400 µs**.
- Scratch allocation of the canonical prototype: **8,421,464 bytes** (~8.03 MiB) as separately reported by `extra.canonical.scratch_bytes`. General renderer `memory_bytes.true_lifetime_peak` still reports its previous value and **does not include this N006 scratch**: do not claim a validated new total lifetime peak.
- Canonical per-cascade unique keys `[1853,815,284,77]`, duplicate owner outputs 13,659, GPU hash failed inserts = 0, invalid keys = 0, overflows = 0, weighted owner slot reconstruction errors = 0, integer `weighted_owner_total=16688`, no substantive hit or storage errors.
- Original and canonical 320×180 HDR PFM are **byte-identical**, both SHA-256 `79de995078c605c8c5c6aef44c8565edf3f808e32934fd43646753bdba815861`. `status=complete`, `bit_identical_gpu_image=true`.

## Why the repair worked

The accepted composite normalizes integer spatial storage as `float(slot.sum) / (float(slot.count) * 65535)`. Previous P1g emitted just one canonical per-key mean/count, which gave mathematically equal real numbers but changed some binary32 values because float rounding is affected by the original owner multiplicity. An N006-only GPU owner-count pass now reconstructs the original integer `sum=owner_count×rounded_mean` and `count=owner_count` for each live probe, **before** the unchanged composite. This restores bit-identical images in this test and supports (but does not formally prove for every possible source of numerical divergence) the float32 rounding explanation of the prior mismatch.

## Performance interpretation, deliberately conservative

**The 1,838.6 → 1,051.9 µs apparent decrease is not a speedup estimate.** The baseline target was the first dynamic-state frame and paid 1,155.8 µs one-time traversal maintenance, whereas the candidate paid zero. Primary visibility and traversal were also much slower in the candidate, reflecting noise/other effects. The 132 µs compacting stage plus 10.54 µs owner-restoration and ~8 MiB scratch may outweigh reduced traversal time; one noncomparable pair cannot decide.

**Next gate = P1h prospectively frozen steady-state paired A/B**: perform target-state warmup before measurements, same-process balanced current/canonical order and multiple independent processes; validate every frame byte-identical, GPU keys and ray counts, and report both primary-visibility-independent GI-work subtotal and full-GI time with variability. P1 original predictive allocation and P2 formal GO remain closed. No N004/N005 edits or GitHub Actions; historical artifacts untouched.
