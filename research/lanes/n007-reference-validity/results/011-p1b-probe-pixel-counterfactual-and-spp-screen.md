# N007 P1-B-011 — exact GPU probe-to-pixel reconstruction and reference statistical NO GO

**Date:** 2026-10-12 JST  
**Issue:** [#4](https://github.com/owoDra/real-time-gi-lab/issues/4)  
**Classification:** diagnostic-only GPU output explanation; **statistical-screen-fail** for one preregistered moving-rigid target cell  
**Acquisition source commit:** `dabe590b0c6e24ab00c10de3aade50a3a8783e8e` (not necessarily this documentation commit)  
**Frozen frame-state SHA256:** `77e1d952988d70367557c36755261a2a4eefa49177541f5e0a8a99478a24b8b4`  
**Evidence source:** user-provided console summary from `run_p1b_cpu.py`, after locally compiling CPU-only N007 CMake tools; private PFM/buffer files and derived JSON **not uploaded** or independently reopened in the assistant container.

## Pixel-level controlled ablation of already captured GPU signal

The offline replay first reconstructed the **unaltered** GPU indirect image from its captured per-probe GPU work, fixed radiance contributions, primary hits, recorded frame basis and probe-key aggregation. The baseline reconstruction gate **passed**. The independently reconstructed CPU shadow-label mask then zeroed only positive GPU probe contributions found shadow-blocked by an independent CPU BVH, leaving unchanged the originally recorded work ordering, rays, primary hits, probe-key/storage merge, visible nonblocked contributions and pixel lookup.

| Quantity | User-reported observation |
|---|---:|
| GPU indirect positive pixels before filtering | 9,247 |
| GPU indirect positive pixels after filtering | **0** |
| Positive pixels reduced in radiance | **9,247** |
| Positive pixels reduced to exactly zero | **9,247** |
| Original replayed image sum | 0.2673380636301213 |
| Filtered image sum | **0.0** |
| Maximum absolute original/filtered pixel difference | 0.00012207217517357137 |

This establishes a **complete image-level causal ablation within the actual N007 probe GI estimator in this frame**: removal of independently classified shadow-blocked secondary light contributions accounts for the full 9,247 GPU-positive indirect pixels. This agrees with P1-A-009's 18,363 blocked-positive GPU probe samples out of 18,649 positive (and 286 nonblocked positives), zero secondary traversal/quantization mismatches and matched primary triangles/hits. Nonblocked positive samples did not preserve a positive final pixel under the unchanged replayed storage/lookup configuration; do not infer that each was false, nor that all GPU GI in every scene is leak-only.

**Limits:** an image-estimator ablation is not an independent physical oracle, cannot verify original archived N006 M3b's exact source/camera/states, and does not prove the N006 historical diagnosis. Original N001–N006 data/code/outcomes remain unmodified.

## Frozen CPU four-seed statistical reference screening

The unchanged CPU renderer/reference estimator sampled the **same captured world geometry and camera/light state** with the preregistered four fixed 64-bit seeds per SPP level. The original 512-SPP level was reused; levels 1024/2048/4096/8192 were generated independently via the CPU-only N007 source. No post-hoc seed/SPP/frame substitutions.

| SPP | Union-active CPU reference pixel fraction | N007 statistical verdict |
|---:|---:|---|
| 512 | 0.0 | Ineligible |
| 1,024 | 0.0 | Ineligible |
| 2,048 | 0.0 | Ineligible |
| 4,096 | 0.0 | Ineligible |
| 8,192 | 0.0 | Ineligible |

The frozen five-level limit is exhausted: `statistical_eligibility_status=statistical-screen-fail`, `statistical_eligible_at_spp=null`. This is an unambiguous **NO GO for use of this particular moving-rigid CPU reference as a statistically supported HDR quality oracle**, not a proof that all-black reference pixels violate physics. The screen is conservative and explicitly cannot validate physically correct deterministic zero-light scenes.

## Scientific/lane decision

- **P1-A moving-rigid probe-shadow mechanism:** strongly established for this particular recorded GPU estimator and replayed image, because baseline reaggregation passed and the counterfactual removed all positive output.
- **P1-B moving-rigid reference statistical eligibility:** **NO GO** after the entire frozen 512–8192 SPP ladder, all four registered seeds, without sufficient active signal at any level.
- **Physical correctness:** **unknown**. A black CPU image is consistent with no recorded light transport but lacks a separately verified physical reference, and camera UBO and secondary GPU allocation provenance are not fully independently attested.
- **Historical archived N006 M3b causation:** **unproven**.
- **Other preregistered cells** (camera/disocclusion, positive light-motion, deterministic known-light/occluded control, static/deforming/churn classes): **NOT YET MEASURED in this N007 P1-B campaign**. No cross-class GO/NO GO claimed here.
- **N007 lane completion:** **open pending** either measurements of these cells or an explicit bounded research limitation/stop decision; no post-hoc loosening of the frozen screening threshold.

Private data remain under ignored `out/research/n007-reference-validity/`. Raw PFM SHA identities for all per-level images were internally validated by the local manifest pipeline but are unavailable for independent external verification in this chat.
