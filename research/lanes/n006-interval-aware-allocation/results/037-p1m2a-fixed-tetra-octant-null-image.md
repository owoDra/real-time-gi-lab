# N006 P1m2a — tetra-octant jitter: GPU 4/4 PASS, 6/12 extra hits, zero HDR image change

2026-10-11. Independently uploaded original user-local file **`n006-p1m2a-tetra-octant-summary.json`**, **SHA256 `e0d458a1bf29af2f295d44a941b3e184e58b10fa4a7aa20de6c940012ce1ef08`**, 5,540 bytes; `protocol_version=n006-p1m2a-tetra-octant-jitter-static-c3-v1`. Clean measured HEAD **`fce39c4abeca222227f8a91842221f3179417d95`**, GPU AMD Radeon 8060S Graphics (RADV STRIX_HALO), source Sponza SHA `2a86fdc2dc92d7c6a740682c61ec97f3101f489a06443c6823aff85bb990e5f6`. Status `direction-calibration-complete`, `failures=[]`, **4/4 frozen cases**, `formal=false`, `calibration_only=true`, `reference_generated=false`, `predictive_quality_established=false`.

This pilot implements the alternative fixed tetra-octant directions **[0,3,5,6]** and deterministic 0.125 xyz jitter pre-registered separately in [026](../experiments/026-p1m2a-fixed-tetra-octant-jitter-pilot.md). It does not revise previous M1a/M1c P1a uniform sphere directions/null evidence.

| Frozen key | Pre-secondary consumer pixels | Base hits/8 | Base positive rays | Base sum16 | Extra hits/4 | Extra misses | Extra positive rays | Extra hit+zero | Extra sum16 | Rounded mean16, 8→12 | Changed RGB pixels/channels | Injection GPU µs |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|---:|---:|
| Zero `3221225474` | 0 | 4 | 0 | 0 | 1 | 3 | 0 | 1 | 0 | 0→0 | 0/0 | 632.321 |
| Low `3223322625` | 93 | 5 | 0 | 0 | 3 | 1 | 0 | 3 | 0 | 0→0 | 0/0 | 630.117 |
| High `3223324678` | 875 | 5 | 4 | 10 | 2 | 2 | **2** | 0 | **5** | **1→1** | 0/0 | 624.747 |
| **Three-key totals** | — | **14/24** | **4/24** | **10** | **6/12** | **6/12** | **2/12** | **4/12** | **5** | — | **0** | — |

Matched historical original P1a-uniform direction experiment [035](./035-p1m1c-gpu-ray-fate-4of4.md), also at three frozen static/C3 keys: **extra 1/12 hit**, 11/12 misses, **zero positive samples**, **zero 16-bit extra energy**, same null image. In this tiny non-independent calibration set, the alternative octant-jitter changed hit behavior **1/12→6/12**, positive samples **0→2**, but all four rendered PFMs are **byte-identical** to accepted control SHA **`2309b06cd9b0a2248e77d66f417df955f4c09051a1cd469eff9ecffffa34e15e`**. All maintain M0 key rows SHA **`020ac742cdddf44f627095f54b081ab39646b36a3457a7f98e29044407fb68e2`**, canonical outputs 3008, accepted base rays 24064, selected interventions 24068 total (one canonical key +4 rays), merged sample count 12, **N004 hit oracle 0 substantive mismatches**. No image improvement can be derived from a GPU hit-rate increase alone.

## Why High's positive +5 16-bit radiance still made no observable change

The N006 runtime checked actual work contributions and the selected canonical output's 8+4 integer accumulator, and recomputed means as:
```
baseline_mean16  = floor((base_sum16 + 4) / 8)
candidate_mean16 = floor((base_sum16 + extra_sum16 + 6) / 12)
```
At High, `base_sum16=10`, `extra_sum16=5` gives `floor(14/8)=1` and `floor(21/12)=1`. For the new 12-ray rounded mean to become **2** with the same base sum10, the additional-four-ray sum must reach **at least 8** (because `floor((10+8+6)/12)=2`). This is a **necessary observable mean-change threshold for this exact integer accumulator**, not proof that raising it to 8 would improve the final image or HDR reference error. For Zero/Low (`base_sum16=0`), a candidate rounded mean of 1 requires total extra sum **at least 6**. No threshold tuning or sampling retry on these already-observed keys is pre-authorized.

Every current candidate/control output PFM is identical, so the signed global RGB RMS gain against any **same independent reference**, if obtained, is mathematically **exactly 0** on these three keys. There is no point running an expensive reference **solely** to re-establish this zero. This does not show zero value for all scenes, camera/light trajectories, or other keys.

## Decision and next experiment constraint

- **P1m2a direction/hit mechanism PASS**; **P1m2a observable image effect FAIL/NULL 3/3**; NO signed HDR improvement, predictive consumer-ranking validity, ROI evidence or P2 scheduler GO. It would be invalid to select extra directions by GPU post-hit results or to call this a general population 6/12 hit rate.
- The single-invocation scan over 3008 canonical keys takes **624.747–632.321µs** for this tiny pilot (mixed with finalize/timestamp boundaries); this is a diagnostic overhead, not four-ray marginal traversal cost and not a deployable P2 allocation algorithm.
- **Stop repeating direction tweaks on these three static/C3 calibration keys.** The combined data localizes a causal obstacle to low per-sample 16-bit contribution magnitude and rounding after changing distribution, not an inability to add/trace rays. Future research must pre-register **independent trajectory+key sets**, measure downstream nonzero PFM effect before investing in a converged HDR signed-reference and ranking analysis, and separately verify a cheaper, GPU-indexed key dispatch for any eventual runtime benefit. No change to existing accepted shaders, no retroactive reclassification, no PR/Actions.
