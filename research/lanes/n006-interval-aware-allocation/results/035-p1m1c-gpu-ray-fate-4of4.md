# N006 P1m1c — frozen added-ray fate audit 4/4 PASS; 11 misses, 1 dark hit

2026-10-11. User-uploaded `n006-p1m1c-ray-fate-summary.json`, SHA256 `5c87c2b12b3983070e129cd163f7e2560d75f772c402fa719d302219262908ef`, experimental `n006-p1m1c-ray-fate-static-c3-v1`, executed **clean HEAD `db32b403b3ed0e3ce1afab7bf29df97a4aaf55e7`** on AMD Radeon 8060S RADV. `status=ray-fate-audit-complete`, cases=4/4, failures=[], no independent HDR reference; calibration-only exact same static/C3 target tokens.

| Frozen target | M0 consumer pixels | 8 base hits | 8 positive radiance rays | 4 extra hits | 4 extra misses | Extra hits with zero radiance | Extra sum16 | Changed RGB pixels | Extra injection GPU µs |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Zero `3221225474` | 0 | 4 | 0 | 0 | 4 | 0 | 0 | 0 | 637.010 |
| Low `3223322625` | 93 | 5 | 0 | 1 | 3 | 1 | 0 | 0 | 618.976 |
| High `3223324678` | 875 | 5 | 4 | 0 | 4 | 0 | 0 | 0 | 626.871 |
| **Combined three keys** | — | **14/24** | **4/24** | **1/12** | **11/12** | **1** | **0** | **0** | — |

Control + interventions preserve 3008 canonical outputs, 24064 base rays, 24068 rays in an intervened frame, 12 merged samples for selected output, N004 CPU/GPU oracle zero mismatches, same frozen coverage SHA `020ac742cdddf44f627095f54b081ab39646b36a3457a7f98e29044407fb68e2` and all four PFM SHA `2309b06cd9b0a2248e77d66f417df955f4c09051a1cd469eff9ecffffa34e15e`. No image quality change. 3 candidate signed RMS gains versus **any same reference** exactly 0.

**Interpretation:** The formerly ambiguous zero added radiance was mainly **traversal misses for the existing P1a uniformly hashed directions** (11/12) with one additional real hit that shaded/quantized to zero; it is NOT accurate to claim *all* rays were misses. Contrast 14/24 hit rate for current 8 deterministic octant directions, but these tiny keys/rays are not independent population samples; a population-wide miss-rate disadvantage of uniform sampling has not been established. Even a hit does not necessarily generate useful radiance, especially low key (5 base hits, none positive). For High, the base 8 rays had four positive contributions, but the 4 extra uniform rays were all misses.

**Cost caution**: ~0.62–0.64ms GPU timestamp is dominated/contaminated by **single-thread scanning all 3008 canonical outputs** and a finalize stage, not the marginal four-ray cost. Already ~28×–45× the 14–23us P1m0b coverage pass. Do not adopt as P2 scheduling or use as four-ray marginal traversal time.

**Decision**: P1m1c *mechanism diagnosis* PASS. Pre-register a distinct exploratory fixed 4-ray directional distribution, keeping baseline, keys, output parity, same work budget and quality image comparison, versus original M1a/M1c **without rewriting frozen nulls**. A direction arm with nonzero radiance/HDR image still does not establish a positive signed quality benefit; independent reference RMS, repeat uncertainty and separate evaluation/holdout are required. No P1 predictor/ROI or P2 GO.
