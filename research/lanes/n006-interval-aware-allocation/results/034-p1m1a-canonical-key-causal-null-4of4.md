# N006 P1m1a — canonical-key +4-ray preflight 4/4 PASS, zero image effect for all calibration strata

2026-10-11. User GPU upload `n006-p1m1a-canonical-key-pilot-summary(1).json`, SHA256 **`ea8b9c928bd5f3470bcc85f33b1b6d98127a51da94961e5b27f1329e4d6d6f36`**. GPU **AMD Radeon 8060S Graphics (RADV STRIX_HALO)**, clean git HEAD `dd5d8830ec008c527607a3eb29cf159f34ba7983`, Sponza source SHA `2a86fdc2dc92d7c6a740682c61ec97f3101f489a06443c6823aff85bb990e5f6`; `protocol_version=n006-p1m1a-canonical-key-extra-preflight-v1`, `status=mechanism-preflight-complete`, `failures=[]`, exactly four isolated cases, **calibration_only=true**, **reference_generated=false**, **predictive_quality_established=false**.

| Target | Frozen static/C3 consumer pixels | Canonical output_id | Secondary rays | Base 8-ray radiance sum16 | Extra 4-ray radiance sum16 | Rounded 8→12 mean16 | Modified RGB pixels / channels | Append GPU cost µs |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| control | — | — | 24064 | — | — | — | — | — |
| zero (3221225474) | 0 | 1238 | 24068 | 0 | 0 | 0→0 | 0 / 0 | 619.016 |
| low (3223322625) | 93 | 835 | 24068 | 0 | 0 | 0→0 | 0 / 0 | 633.604 |
| high (3223324678) | 875 | 124 | 24068 | 10 | 0 | 1→1 | 0 / 0 | 627.753 |

All cases have **3008 canonical outputs**, 8 intact base samples/output plus exactly four new samples on the one fixed target key; base ray total 24064, intervention total 24068. Intervention output's merged sample count **12** every time. Each N004 hit oracle **zero substantive mismatches**; every full P1m0 key-row SHA equals the accepted baseline `020ac742cdddf44f627095f54b081ab39646b36a3457a7f98e29044407fb68e2`. Every PFM SHA is **exact byte-equal** to accepted control `2309b06cd9b0a2248e77d66f417df955f4c09051a1cd469eff9ecffffa34e15e`.

## Interpretation and decision

**P1m1a mechanism correctness PASS 4/4**; **quality-effect null 3/3**, not a quality gain. Because candidate/control PFM bytes match exactly, for **any fixed common independent reference** the difference `RMS(control,ref)-RMS(candidate,ref)` is mathematically **exactly 0 for these 3 calibration cases**. Running CPU reference for these unchanged images would not make a signed gain appear; the reference is still needed for any *other* nontrivial intervention and formal noise assessment. No general conclusion about all keys, future frames, or predictor ranking.

Potential explanations **not established**: all four additional rays miss scene vs hit surfaces but radiance=0 due light/normal/visibility vs radiance quantization. The current source pilot records only integer contributions, **not hit/miss metadata** for each of the four rays, so it cannot distinguish these. Do not attribute cause without additional instrumentation.

**P1m1a append GPU cost ~0.62–0.63 ms per targeted key** is extremely high compared with M0b count pass ~14–23 µs and original SW second-ray traversal ~0.3–0.4 ms. The P1m1a GLSL deliberately uses a **single invocation scanning all 3008 canonical keys**, so this cost is a serial *prototype injection pass*, NOT the marginal traversal cost of four rays or an acceptable P2 scheduler estimate. No cost/effect ROI GO may be inferred. Any deployable method needs indexed/parallel lookup, carefully remeasured.

**Next protocol**: prospectively instrument four added ray *hit/miss vs positive pre/post quantization* with the original acceptance checks unchanged, and measure their own per-key energy; then change sampling/direction distribution only under a **separately named exploratory protocol**, never as a selective rewrite of the frozen 3 null outcomes. Concurrently record the full effect-null result and pre-register independent HDR signed quality evaluation of any demonstrably nonzero candidate. No PR or GitHub Actions. Issue #42 OPEN.
