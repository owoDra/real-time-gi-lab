# N006 P1k — frozen matched three-arm canonical GPU timing

Issue #42. **Prospectively frozen after successful P1j-B correctness and before any P1k target GPU measurement.** Accepted P1j-B clean source `781ecadc41eaffac87896aa919469c0bd46e6be0`: ten/ten Lane-E-final HWRT/software scenarios gave byte-identical baseline/canonical PFM, actual 80.97–81.95% fewer dispatched rays, `copyback_executed=false` and unchanged lean-hash 4,489,304 B extra scratch. One P1j-B software light-motion cold run recorded a 149.644 µs build stage vs most cases 44–51 µs; cause unknown, no cherry-picking.

## Experimental question

Does true zero-copy compact work (P1j-B) save GPU time over the accepted P1j-A copyback pipeline **when both have the same compact rays, hash table and scratch**, and do both achieve net downstream work and whole GI wins over the original noncanonical current mode on HWRT **and** software?

## Freeze BEFORE running

- Target **AMD Radeon 8060S RADV**, accepted Sponza scene/digest, `deforming-control` / stable-topology-deforming motion=1 target state (the established 4172-owner, 3029-key P1h workload). Test separately with `lane-e-final-hwrt` and `lane-e-final-software`. No topology churn or independent path-traced reference; all three arms use the **same geometry, visibility, rays-per-key and camera/light state**.
- **3 fresh processes per backend**, each with 32 source warmup frames followed by 8 **current-mode target-state** warmup frames. Do not count warmup in A/B statistics; each warmup must be internally correct, at most the first target warmup may do dynamic maintenance, and last target warmup has 0 traversal maintenance.
- **18 measured target-state frames per process**, ordered in frozen 6-triplet balanced permutation pattern `012120201021102210`:
  - `0`: accepted original current mode (133,504 rays, 16,688 owner outputs).
  - `1`: canonical P1j-A lean hash **with** compact→original copyback (24,232 rays, 3,029 unique outputs).
  - `2`: canonical P1j-B same lean hash **without** copyback, direct compact-work bindings (24,232 rays, 3,029 outputs).
- Six triplets per process, **18 matched triplets per backend, 36 total over six processes**, 108 measured target PFM frames. All six permutations included; each arm appears twice in each position per process. **No stopping early based on favorable metrics**.
- Per-frame image digest MUST be byte-identical to accepted deforming PFM SHA `79de995078c605c8c5c6aef44c8565edf3f808e32934fd43646753bdba815861`, plus full existing renderer/hit/storage correctness and distinct exact current/canonical counts, 16,688 owner weight reconstruction for both canonical modes; `copyback_executed` must match arm=1 only. Hash keys=3029, 32,768 slots, 4,489,304 B scratch, zero invalid/collision overflow/storage failures.
- Every measured frame requires `traversal_maintenance_gpu=0`, moved primitives=796, no topology churn. Each GPU disjoint timestamp stage subtotal (including canonical build 4→19 when appropriate, excluding the nested owner-weight interval from the sum) must close to full-GI GPU time within 1 µs. Complete renderer=complete GI+composite within 1 µs.
- Report raw per-frame *complete GI*, *complete renderer*, *primary visibility* (pre-canonical noise), *producer*, *post-producer affected GI work subtotal* (canonical build + ray prepare + traversal + radiance + merge + inclusive storage update + invalidation + resolve), HWRT/software traversal stage, canonical build GPU and owner-weight GPU separately without double-count.
- For each six-frame? **Triplet** compute two independent paired differences: `P1j-A minus current`, `P1j-B minus current`, and **P1j-B minus P1j-A**, for complete GI, complete renderer, prehash primary visibility, post-producer affected GPU work and canonical GPU build time. Preserve all 36 triplets and each per-process median, six-process raw samples, counts of positive/negative pairs, minima/maxima, and frozen protocol/HEAD metadata.
- Fail closed on any missing/mismatched PFM, hash/ray/owner/storage count, GPU timestamp closure, warmup maintenance, unsupported backend or altered schedule. Preserve stdout/stderr and all already collected evidence and summary with `invalid-retained`. No exclusion of slow frames such as P1j-B software light-motion outlier. **Never sum CPU wall with GPU timestamps**.

## Interpretation thresholds

- **P1k correctness/timing PASS:** all six process runs and all 108 measured PFM images pass, stage closure valid and two candidate versions fully recorded. This is non-formal diagnostic performance evidence on this particular deforming workload/device, not a universal speedup certification.
- **P1j-B useful speed improvement vs P1j-A:** majority of the 18 P1j-B minus P1j-A *post-producer GPU-work* triplets per backend must improve, with negative per-process medians, while preserving bitwise output. If not, keep P1j-A copyback for its simplicity or investigate descriptor/cache/frequency effects before adopting zero-copy.
- **Software viability:** separately consider 18 triplets of P1j-B minus noncanonical current (full-GI and affected GPU stages). GPU-primary stage savings may be masked by primary visibility jitter; don't claim full-frame gain based on ray reduction alone.
- Resource target: P1j-B still allocates 4,489,304 B N006 scratch. Future direct producer and alternate GPU stress/device tests are **separate** gates; P1/P2 adaptive ray allocator remains closed.

No changes to accepted N001/N004/N005 behavior and no GitHub Actions. Do not reinterpret old cold P1i/P1j-B timing as matched.
