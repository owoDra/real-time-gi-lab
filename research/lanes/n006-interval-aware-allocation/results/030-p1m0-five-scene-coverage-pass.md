# N006 P1m0 — five-scene canonical-key consumer coverage, 5/5 PASS (diagnostic)

Issue #42; user-uploaded `n006-p1m0-consumer-coverage-summary(1).json` (2026-10-11), **raw attached-summary SHA256 `f355b7202e52127b044120ac8406e5dba4626dd88f4cf29a78f16abbc2c66cec`**. Frozen protocol `n006-p1m0-consumer-coverage-five-scenes-v1`; clean branch `research-n006-interval-aware-allocation` HEAD `8a5cb251384ba14deb6c158057583fcd8214e335`, AMD Radeon 8060S RADV STRIX_HALO, Sponza SHA `2a86fdc2dc92d7c6a740682c61ec97f3101f489a06443c6823aff85bb990e5f6`. Complete **5/5**, no failures, 32 source and eight target-state warmups per scenario, single canonical software output per scene with frozen accepted PFM hash/oracle/counter closures and post-diagnostic image/hit byte parity. This report audits the *provided aggregate summary and claimed runner checks*, not the separately stored original per-run evidence PFMs and original GPU timestamp payloads.

## Measured diagnostic counts

| Scenario | Canonical keys | Keys accessed by valid screen pixels | Accessed share | Successful lookup attempts / all valid pixel × cascade attempts | Cascade 3 successful lookups | Canonical base rays |
|---|---:|---:|---:|---:|---:|---:|
| static | 3008 | 100 | 3.324% | 11,400 / 51,080 | 9,626 | 24,064 |
| camera-motion | 3220 | 42 | 1.304% | 12,437 / 50,516 | 11,354 | 25,760 |
| light-motion | 3008 | 100 | 3.324% | 11,400 / 51,080 | 9,626 | 24,064 |
| moving-rigid | 3104 | 38 | 1.224% | 11,032 / 73,428 | 10,353 | 24,832 |
| deforming-control | 3029 | 100 | 3.301% | 11,403 / 51,088 | 9,628 | 24,232 |

- Accessed key shares between **1.22% and 3.32%**; per-frame canonical *producer* keys unused by this frame's *screen composite* between **96.68% and 98.78%**. This does **not** prove those keys are globally/temporally useless, nor is it an instruction to remove their base rays without testing temporal reuse.
- The canonical hash contains many keys that the composite does not reference, and many screen pixels attempt keys that were never produced: successful composite lookup attempts ~**15.0–24.6%** of valid pixel×cascade attempts, absent key attempts dominate the rest. This is a source-key presence test, **not** evidence of successful storage or radiance contribution.
- **Cascade 3 accounts for 84.4–93.8% of matched lookup attempts**, not 84–94% of *quality*, ray demand or potential marginal gain. Counts cannot determine signed error reductions.
- The five scenario per-cascade matched lookup vectors are `[143,415,1216,9626]`, `[29,204,850,11354]`, same as static for light, `[29,131,519,10353]`, `[144,415,1216,9628]`. All five `invalid_keys=invalid_launch=probe_exhaustions=uint32_overflows=0`, `matched + absent = 4*valid_primary`, and exact producer-owner multiplicity closure holds per summary.
- The 60 strictly prospectively selected M1 *calibration-only* canonical keys are present, exactly **12 per scene** (zero/min-positive/max-positive count × each cascade); no incomplete strata. Their measurement is entirely based on the M0 consumer count. **No quality/reference labels have been generated**.
- static/light screen coverage identical despite different accepted image SHA: this reinforces the need to separate *visibility* from *signed radiance error benefit*.
- Original ray workload 133,344–135,392 rays/case, canonical work 24,064–25,760. Those reductions are accepted P1j behavior, **not** new M0 or P2 speedups.

## Frozen replay fingerprints (for pretrace GPU placement proof)

| Scene | key_rows_sha256 | matched lookups | consumer keys |
|---|---|---:|---:|
| static | `020ac742cdddf44f627095f54b081ab39646b36a3457a7f98e29044407fb68e2` | 11400 | 100 |
| camera-motion | `ee0cebb3771f6cb2e43622f843b8ca9c7504c39f6f7239f9d887062e93c34e5e` | 12437 | 42 |
| light-motion | `020ac742cdddf44f627095f54b081ab39646b36a3457a7f98e29044407fb68e2` | 11400 | 100 |
| moving-rigid | `189e6c69f3bd96f7b99cbb13cecba777e4094d35f7f47d42521d087380b95ec4` | 11032 | 38 |
| deforming-control | `fea8628c854aa807deb08a222efc50d64be785ea680e859999a78feeea80c4fe` | 11403 | 100 |

## Decision

**P1m0 postframe GPU diagnostic 5/5 PASS** and 60 prospective M1 calibration keys frozen. **P1 model / P2 GO are NOT established**: critical next test is whether the same lookup counts can be computed **inside the real renderer after primary hits and canonical-key discovery, but before secondary ray dispatch**, with a bounded measured GPU cost and byte-exact final image/primary. Next conditional M1 +4-ray interventions must quantify signed RGB error against independently converged references; coverage alone is not signed quality. The cost test is N006-only; no accepted shaders or CI/Actions changed.
