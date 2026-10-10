# N006 P1k — three-arm warmed GPU timing: HWRT + Software PASS

Issue #42. **P1k correctness/timing protocol PASS (non-formal, frozen deforming-control workload).** Source: user-uploaded `n006-p1k-three-arm-summary.json`, `n006-p1k-three-arm-timing-v1`, `status=complete`, `failures=[]`, clean branch HEAD `0c4d1ef7820435e9400f99749417774d37b22682`. Target GPU AMD Radeon 8060S Graphics (RADV STRIX_HALO). No independent path-traced reference.

## Protocol and correctness

Three fresh processes for each backend, with 32 source + eight target-state warmups and six balanced frozen `012120201021102210` triplets per process: **108 measured target frames, 36 triplets, 18 triplets/backend**, including all six arm-order permutations in every process. Arm 0 is original current (133504 actual rays), arm 1 lean-hash canonical with copyback (24232 rays), arm 2 lean-hash canonical direct compact without copyback (24232 rays). All measured HDR PFM digests **identical** to accepted `79de995078c605c8c5c6aef44c8565edf3f808e32934fd43646753bdba815861`; all 108 disjoint timestamp accounting errors at roundoff (max absolute closure ~4.55×10^-13 µs), no measured dynamic traversal maintenance, GPU storage/hit/hash/owner-weight invariants validated by the frozen runner. Actual secondary ray reduction **81.84923298%** for both candidates. Original owner weights 16,688 reconstructed in each canonical frame; lean hash 32,768 slots and extra scratch accounting 4,489,304 bytes in candidates. Existing N004/N005 source and raw earlier experiments untouched.

All values below are `candidate − comparator`: **negative means faster**. All counts are out of 18 frozen matched triplets *for that backend*. Per-process medians and full raw samples are retained in source JSON; do not erase negative/noisy comparisons.

## Controlled matched triplet differences

| Scope | HWRT median delta (µs) | HWRT faster | Software median delta (µs) | Software faster |
| --- | ---: | ---: | ---: | ---: |
| P1j-A copyback vs original — **post-producer work** | **−95.281** | 18/18 | **−442.821** | 18/18 |
| P1j-B direct vs original — **post-producer work** | **−94.399** | 17/18 | **−456.307** | 18/18 |
| P1j-B direct vs P1j-A copyback — **canonical-build stage** | −6.432 | 17/18 | −7.073 | 16/18 |
| P1j-B direct vs P1j-A copyback — **post-producer work** | **+0.461** | 9/18 | **−10.961** | 11/18 |
| P1j-B direct vs original — complete GI GPU | −59.573 | 11/18 | −667.689 | 15/18 |
| P1j-B direct vs P1j-A copyback — complete GI GPU | +39.415 | 6/18 | −86.625 | 9/18 |
| P1j-A copyback vs original — complete GI GPU | −226.911 | 13/18 | −583.489 | 14/18 |

- **HWRT direct-vs-copyback decision:** Copy dispatch removal *reliably saves canonical construction time* (17/18, median −6.432 µs), but **fails pre-registered net-post-producer improvement gate**: direct is better in only 9/18, median **+0.461 µs** (slower), and per-process medians `[-7.635, +4.268, -1.162]` µs mixed. Whole-GI direct-versus-copyback faster only 6/18, strongly confounded by prehash primary visibility. **Do not proclaim zero-copy as globally faster or adopt unconditionally.** Retain the simpler lean copyback path as the reference for HWRT until further evidence.
- **Software direct-vs-copyback decision:** Build-stage 16/18 quicker, median −7.073 µs. Post-producer affected GI work 11/18 quicker, median −10.961 µs; all three process medians negative `[-10.961, -19.557, -0.962]` µs. It satisfies the protocol's *narrow exploratory useful-work* gate for Software, but the third process median is near zero and whole-GI comparison is 9/18 quicker (not a reliable end-to-end win). Retain as promising opt-in, not generic standard.
- **Software ray-dedup benefit is substantial and replicated:** 18/18 post-producer wins versus original for both canonical variants. P1j-B median −456.307 µs, with all three process medians `[-465.645, -465.324, -400.922]` µs. Whole-GI wins 15/18, median −667.689 µs, but prehash visibility is exceptionally variable; DO NOT claim a universal full-renderer percentage.
- **HWRT ray-dedup benefit replicated:** P1j-A 18/18 post-producer wins, P1j-B 17/18; ~−95 µs median net after canonicalization costs. The direct mode is not demonstrably better than copyback for HWRT.

## Absolute backend gap — descriptive, not causally controlled cross-backend A/B

From 18 raw frames per backend/arm, descriptive *individual-arm sample medians* (not differences of paired medians):

| Median (µs) | HWRT original | HWRT direct | Software original | Software direct |
| --- | ---: | ---: | ---: | ---: |
| Post-producer GPU work | 296.88 | 203.45 | 861.80 | 419.36 |
| Candidate traversal GPU | 171.15 | 105.42 | 728.76 | 312.85 |
| Primary visibility GPU | 685.70 | 611.08 | 1116.58 | 864.18 |
| Complete GI GPU | 1119.53 | 927.80 | 2178.44 | 1454.48 |

Caution: **software direct is still ~2.1× HWRT direct on post-producer work** in these descriptive samples (419 vs 203 µs), with traversal ~313 vs 105 µs and primary visibility ~864 vs 611 µs. Backends were in different fresh processes and source-level software-primary/HWRT-primary differ, so these *absolute medians are diagnostic*, not an isolated claim about particular algorithmic primitives or a verified hardware-independent speed ratio.

The measured primary visibility *pair deltas* ranged hundreds of microseconds and explain much of the inconsistent whole-GI result. The P1j-B software light-motion cold-run 149.644 µs outlier remains in the accepted prior P1j-B report; **P1k tested deforming-control only** and does not resolve whether that single light-motion anomaly generalizes.

## Decision

- **Accept** canonical probe×cascade sharing and 32,768-slot lean hash as a valuable HWRT/Software secondary-ray performance intervention for this stable-topology deforming workload.
- **Retain both P1j-A and P1j-B** as experimental choices. Use the *simpler copyback mode* as the conservative HWRT reference; Software direct has a narrow downstream median advantage, not proven complete-GI benefit.
- **Do not blindly optimize copyback further**: evidence points to a larger **Software traversal and primary visibility gap**. Next prospectively freeze a stage-level backend gap/root-cause pilot with consistent camera/geometry and GPU timestamp primary, then evaluate candidate software BVH/traversal interventions. Separately design a direct canonical producer only if its cost/complexity and the remaining 4,489,304 B scratch budget justify it; do not infer 4 MiB work-buffer memory reduction merely from removing copyback.
- Still unproven: topology-changing/high-churn, true HWRT-incapable GPUs, different vendors, scene/key-range stress, total heap residency peak, and predictive marginal-value ray allocation (issue #42 original P1/P2). The latter remains gated; canonical sharing is a distinct result.
- No GitHub Actions or changes to accepted renderer semantics.
