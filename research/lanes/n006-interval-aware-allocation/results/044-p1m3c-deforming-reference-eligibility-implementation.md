# N006 P1m3c — deforming-control reference-eligibility preflight + signed Q8 study implemented; GPU UNMEASURED

2026-10-11, Issue #42. Started ONLY after authentic M3b `invalid-retained` upload [043](./043-p1m3b-moving-rigid-identical-reference-invalid.md) showing **two CPU reference PFMs byte-identical**, with zero completed control parity/key interventions/quality labels. Accepted N001 bringup historically documented **all-black moving-rigid N001 CPU reference** while GPU renderer had positive radiance; this is a strong prior reason for the reference-identical failure, **not proof about the latest PFMs**.

## Two independent next actions implemented

1. **No GPU / no CPU rerun of M3b**: `scripts/research/n006_interval_aware_allocation/diagnose_p1m3b_reference_capture.py` reads retained original `out/research/n006-interval-aware-allocation/p1m3b-moving-rigid-q8-signed/<UTC>/Q8_control_reference/` and its renderer evidence, **existing** Q8 control candidate.pfm, two 8-bounce CPU reference PFMs. Computes exact image SHA, positive RGB pixel/channel counts, max luminance, negative/nonfinite, full RGB RMS difference and reference convergence metadata, writes **additive** `n006-p1m3b-reference-forensics.json`. Leaves original failed summary unchanged and does not run any rendering. Tests `test_p1m3b_reference_forensics.py` ensure zero/finite diagnostics and lack of subprocess replay.
2. [Separate, prospective experiment 030](../experiments/030-p1m3c-reference-eligible-deforming-quality-protocol.md): **deforming-control only** (new dynamic trajectory, SAME Sponza geometry, never evaluated as a Q8 signed holdout), original accepted 32+8 warmups, software canonical Q8, four cascades, original +4 M1a direction, one selected maximum-consumer token/cascade and one global zero-consumer negative max 5, frozen from pretrace coverage before ANY new treatment. CLI `--p1m3c-reference-preflight` requires original `--p1m2b-independent-state --p1m3-fractional-storage` and explicitly **cannot mix with M3b**. CPU 8-bounce same-readback two independently seeded N001 references are generated ONLY on the first zero-token Q8 control, original 512–8192 spp convergence.
   - **Mandatory BEFORE candidate**: both CPU reference images must be finite, nonnegative, **positive RGB signal** and not float32 byte-identical, and full RGB reference difference `RMS(R_A,R_B)>0`; otherwise **STOP with `reference-ineligible-retained`**, retaining PFM brightness/SHA and Q8 GPU baseline diagnostics. Do NOT interpret identical black references as zero-noise ideal; DO NOT silently switch to old light/camera states or alter fixed seeds.
   - If eligible, second independently-warmed zero-token Q8 control must be exactly equal in PFM bytes and accepted original M0 full consumer rows/SHA (`fea8628c854aa807deb08a222efc50d64be785ea680e859999a78feeea80c4fe`), N004 hit/owner/canonical invariants and source warmup. Select ≤5 new keys by MAX consumers positive/cascade + 1 global ZERO key (minimum packed token ties), **persist selected table before extra GPU rays**. Original uniform +4 key arm only, exactly same Q8 storage in base/treatments. Repeated separately warmed GPU PFM required only for changed images. Zero-consumer negative changing a pixel is invalid.
   - Compute signed full-image linear RGB `gainA=RMS(Q8 base,R_A)-RMS(Q8 candidate,R_A)`, same for R_B. A weak or negative gain or a gain below precommitted `RMS(R_A,R_B)` noise detection bound is **not-detectable**; both strict positive gains > bound needed for signal, and still **no predictive rank or P2/ROI GO**. If no effect/no qualifying signal => STOP; if reference-ineligible => reference-integrator adequacy study instead. Sealed different geometry needed for generalization; original accepted N001 and Q8 shaders unchanged.
   - Runtime owner, canonical, N004 and key oracles reused in `verify_frame(...holdout=True)`; separate provenance flags for M3b vs M3c. Runner `run_p1m3c_deforming_reference_quality.py`, launcher `run_n006_p1m3c_deforming_reference_quality.sh`; new tests `test_p1m3c_reference_eligibility.py`, legacy M3a/M3b source guards updated to recognize explicit new opt-in without dropping old frozen M3a token whitelist.

**Validation:** all files committed via GitHub connector; source checked, **NOT** compiled/tested on user's NixOS, no P1m3c GPU/reference evidence yet. Source code modified only in isolated N006 runtime CLI/runner/tests, accepted N001/N003/E003/N006 original shaders unchanged. No PR/GitHub Actions.

## Next local usage

Use old retained capture WITHOUT rerendering:

```bash
mise exec -- python scripts/research/n006_interval_aware_allocation/diagnose_p1m3b_reference_capture.py
```

Then, on the clean Git branch, run the prospectively isolated study:

```bash
bash scripts/research/n006_interval_aware_allocation/run_n006_p1m3c_deforming_reference_quality.sh
```

Upload `n006-p1m3b-reference-forensics.json` and `n006-p1m3c-deforming-reference-quality-summary.json`; if build/test/CPU reference fails, give first log. A black reference must be retained as substantive ***reference inadequacy*** evidence, not removed from quality dataset via arbitrary exclusions. No P1 predictive quality/P2/HWRT-free speed GO.
