# N007 P1-B-010 — fixed-source reference eligibility acquisition readiness

**Date:** 2026-10-12 JST  
**Status:** implementation prepared, **real SPP ladder NOT run**  
**Classification:** diagnostic-only tooling; NO quality GO/physical correctness claim  
**Scope:** N007 opt-in only; N001–N006 sources, historical classifications and acceptance thresholds unchanged.

## Prerequisite real evidence

In the registered 320x180 Sponza moving-rigid/software target frame:
primary hit pixels match (15,173), device primary triangles match CPU geometry (262,241), and the GPU probe radiance replay of 134,816 items found 18,649 positive contributions, 18,363 (98.4664%) independently shadow-blocked; all secondary hits and fixed unshadowed Lambert predictions matched. GPU indirect/total are positive at 9,247 pixels while CPU direct/indirect/total are each entirely black at 512 SPP across the original four fixed seeds. **The black CPU reference is not statistically eligible at the observed 512 level; no 1024–8192 levels have yet been measured.**

## New bounded CPU-only workflow

- `phos-n007-probe-offline`: reconstruct independent 1/2/3 per-work visibility labels for the already retained GPU secondary payload, without issuing any Vulkan commands or touching the raw original capture. Fail closed on GPU traversal, fixed contribution, or metadata mismatches; avoid overwriting an existing derived flag file.
- `replay_probe_image.py`: reaggregate actual GPU fixed contributions by `output_id`, then by `probe(x,y,z,cascade)`, and reproduce the captured GPU indirect image via unchanged primary hits/camera. A secondary `--shadow-flags` counterfactual runs only after the original image is reconstructed with matching positive-pixel support and <=1e-6 absolute error. It rejects flag counts inconsistent with the raw GPU probe audit. This is an **estimator intervention**, not a proof of correct physical GI.
- `phos-n007-cpu-reference`: generate four fixed-seed `direct/indirect/total` float32 PFMs for ONE pre-registered SPP level using exactly the stored 148-byte frame and 52-byte/triangle world geometry snapshot. No renderer, scene, camera or RNG algorithm replacement and no GPU runtime.
- `run_reference_ladder.py`: reuse the four retained real 512-SPP seed PFMs, acquire additional SPP levels at exactly 1024/2048/4096/8192 with four frozen seeds, SHA every PFM, call existing `check_convergence.py` on each prefix, and stop only at two consecutive eligible levels or at the complete five-level failure. Strict original 64 active-pixel/1%-active/1e-4 peak and paired active-mask noise thresholds remain **unchanged**. Supports interruption/resumption without overwriting original PFMs.
- Controlled native CPU fixture `phos-n007-cpu-test` now includes visibly lit and known-occluded direct-light cases. This verifies limited ray/visibility semantics but does not certify an entire physically unbiased reference.

The code is committed. **Assistant-sandbox isolated CPU mirror of the probe aggregation, source binary layout, cascade pixel lookup and counterfactual mask logic: 7/7 synthetic tests PASS** (2026-10-12; run on a hand-copied core slice, not the complete checkout or actual capture). The full integrated native build, exact repository Python suites, standalone offline probe replay on the user's private capture, and four-seed ladder **have not yet been run**; these isolated tests are not sufficient to certify the end-to-end code or scientific results.

## Required measured next outputs

1. Source-state verified baseline GPU indirect PFM replay and occlusion-filtered counterfactual. If the baseline fails, **stop**, record the mismatch as a new storage/lookup concern and do not claim pixel-level blocked-probe causation.
2. Moving-rigid reference screening with unchanged `512,1024,2048,4096,8192` SPP prefix and seeds. Even a PASS is a **statistical screen only**, not physical truth. A black or unstable full five-level set is a frozen *statistical-screen-fail* for this cell.
3. Frozen camera/disocclusion, light-motion-positive, and known-lit/occluded control cases; other required dynamic classes where supported. If a class is unsupported by the N007 renderer (e.g., topology churn), record an explicit bounded **not measurable / NO GO** instead of asserting that the lane passed.
4. Independently verify GPU camera UBO and secondary geometry/camera origin state, plus deterministic known-light and known-shadow oracle cases, before any `physically_valid` conclusion.

N007 can close with a well-grounded **NO GO / ineligible / not-measurable** finding and an explicit limitation decision; it need not force a GO. All historical N006 outcomes remain frozen.
