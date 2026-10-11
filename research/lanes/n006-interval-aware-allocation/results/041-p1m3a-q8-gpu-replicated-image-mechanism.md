# N006 P1m3a — Q8 storage mechanism PASS on user GPU, 3/3 positive pixels replicate

2026-10-11. User-uploaded original **`n006-p1m3a-fractional-storage-summary.json`**, original-byte SHA256 **`bfb3b537f761e26e011a2ea748bee0253014ae8192bca470d38d8b41b7ce074a`**, 13,100 bytes. Actual clean executed GPU HEAD **`5e41572dc012f32baf65894706b8e363805f5764`** on **AMD Radeon 8060S Graphics (RADV STRIX_HALO)**, fixed Sponza scene SHA `2a86fdc2dc92d7c6a740682c61ec97f3101f489a06443c6823aff85bb990e5f6`. `protocol_version=n006-p1m3a-fractional-q8-storage-calibration-v1`, `status=fractional-storage-mechanism-go-only`, `failures=[]`, `calibration_only=true`, `formal=false`, `independent_reference_generated=false`, `signed_quality_gain_established=false`.

## Full prospectively frozen calibration outcomes [028](../experiments/028-p1m3a-fractional-storage-mechanism-calibration.md)

Both **Q8 control processes per scenario passed byte-exact self-parity** (4 controls total) and preserved historical M0/canonical GPU key coverage. Q8 controls **are intentionally NOT byte-equivalent to accepted integer-storage controls**, so every treatment is compared **only against its same-scene Q8 control**. Every intervention traces 8 base + 4 extra rays at precisely one canonical output; source key, N004 hit-oracle, hit/radiance sums and 12-ray merge closure passed all runner gates. Exactly the expected three arithmetic-changing consumer-positive keys changed the float32 RGB PFM **and each change reproduced in a separate, warmed GPU process**. The previously frozen arithmetic-zero negative control stayed exact null.

| Scenario/stratum token | Consumer pixels | Base sum16 / 8 | Extra sum16 / 4 | Expected Q8 mean-integer delta | Changed RGB pixels | Changed RGB channel values | max absolute RGB delta | Repeat image SHA exact |
|---|---:|---:|---:|---:|---:|---:|---:|---|
| camera/C1-max `1084233745` | 36 | 0 | 2 | **+43** | **36** | 108 | 2.563038833613973e-6 | YES |
| camera/C3-max `3223324678` | 919 | 10 | 0 | **−107** | **919** | 2757 | 6.377794306899887e-6 | YES |
| camera/C2-max negative `2152730633` | 153 | 0 | 0 | **0** | **0** | 0 | 0 | Not needed; exact null |
| light/C3-max `3223324678` | 875 | 1 | 0 | **−11** | **875** | 2625 | 6.556620064657182e-7 | YES |

The 3 Q8-difference treatments affected a total **1,830 pixel occurrences** across two independent HDR images, not 1,830 unique pixels in one frame. Each RGB pixel has all 3 channels changed, consistent with monochrome indirect GI composite. The observed difference (up to ~6.38e−6) is *small*, not a material perceptual improvement claim. Two of three bright/predictor-associated treatments **lowered** per-probe Q8 mean (due extra dark rays); adding samples is not a positive signed-quality label.

## Exact provenance/invariants

- Camera-motion accepted Q8-control PFM SHA: `8c08c2b1093fa86e2d0f45f47f84af906516780947351d421b2f0a1aad349f97`, accepted original integer-PFM SHA `eb889a8796ebae5cfb23ff820c01fcf5e2fd2d21376dc06b8c4a447512362bcd`: **differ**.
- Light-motion Q8-control PFM SHA: `ac4442da0590ba1c956242a9ba6295a23bef38793825e87a68a1c341a1303652`, accepted original integer-PFM SHA `7b48345b67311652fcba9f7083a21fa07eb316d6ded75a1807f75070516333ec`: **differ**.
- Three distinct changed-case PFMs SHA:
  - Camera C1 `22de3201dd017923c8e5b23ba62014fdb6dd39459910dd07893ea3cf1fabed16`.
  - Camera C3 `c9e8d5b0e32014b85d3f6fb08f52df0fe46f6fdcd9c6609b3c6d3c08408cc25a`.
  - Light C3 `9b1809865e6aaf6217d18691ef144e3f8d228682bcfc5d0bfb7d9d25e13592b2`.
- Negative camera C2 PFM SHA **equals camera Q8 control**.
- Camera M0 key hash `ee0cebb3771f6cb2e43622f843b8ca9c7504c39f6f7239f9d887062e93c34e5e` (3220 keys / 25760 original rays); light M0 SHA `020ac742cdddf44f627095f54b081ab39646b36a3457a7f98e29044407fb68e2` (3008 keys / 24064 base rays); selected treated ray count +4 each, no failures.

## Decision

**P1m3a fraction-preserving storage removes the mechanism bottleneck; mechanism GO ONLY.** The stopped **old integer-storage +4** family [039](./039-p1m2b-bounded-screen-32of32-exact-hdr-null-stop.md) remains STOP; this is a distinct Q8 representation. Only previously exposed calibration keys were used, with **no independent heldout geometry, no same-Q8 independent 8-bounce converged reference, no paired signed RGB RMS, no valid P1 predictive rank, no end-to-end GPU ROI**. Neither zero+positive ray hit nor changed float PFM proves positive *quality*.

**Next required study**: freeze a DIFFERENT dynamic held-out trajectory (moving-rigid/deforming-control were reserved in [027](../experiments/027-p1m2b-independent-state-observable-image-gate.md)); before inspecting intervention outcomes, preselect keys from accepted M0 `consumer_pixels`, generate a common independently-converged reference per same frame and two replicates for a *matched global RGB RMS* noise floor, then compare control versus +4 under identical Q8 representation and geometry/time. Predeclare cost/benefit STOP and never use this calibration as independent quality evidence. P2/HWRT-free superiority remain NOT ESTABLISHED. No PR, no GitHub Actions.
