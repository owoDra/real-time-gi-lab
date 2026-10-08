# N006 P1a — completed calibration pilot (CLI-repair branch)

Issue: #42. Status: **VALID intervention execution, NON-DECISIVE causal/predictive evidence; investigate signal observability before more GPU runs.**

## Provenance (user-provided summary)

- Experiment: `P1a-causal-feasibility-pilot-cli-repair`, protocol `n006-p1-causal-pilot-v1`, calibration-only, `formal=false`.
- Git: `research-n006-interval-aware-allocation` @ `4871623797b8ba0b155447f63697bd3340829ee3`, clean worktree.
- AMD Radeon 8060S Graphics (RADV STRIX_HALO). Original failed run remains retained. Repair reused previous independent reference, verified SHA-256 `9302b47c982778dd654d7d404b23c743a7445ca966d49c5a526b1727cf8fbc87`.
- Verified repaired current image drift: **0** versus original. Reference: converged at 512 spp. Scenario: stable-topology deformation. Fixed visible tile IDs: `22890`, `28359`, `33786`.
- Baseline RGB RMS: `3.019924015741972e-05`; repeat RGB RMS identical. Entire baseline image-to-repeat RGB RMS: `0`.
- All 12 targeted interventions (3 tiles × 4 cascades, 4 additional rays per attempt) completed under the runner's correctness/error checks; **failures = 0**.
- Eleven intervention summaries: `rgb_rms_gain = 0` exactly as reported. One, `tile-22890-cascade-3`, had **+4.134909315207209e-10** RGB RMS improvement, equivalent to ~**0.00137%** relative improvement vs baseline. No other positive or negative gains were reported.
- Intervention `complete_gi_gpu_us` single-run descriptive values range ~2,394–4,453 µs. **These are not calibrated against within-regime current-mode timing and must not be reported as a scheduler performance delta.** Also the pilot shader performs a serial base-work scan on one invocation, which would be inappropriate as a runtime scheduler design.

## Interpretation

**P1a execution/provenance gate: PASS.** The user has confirmed correct-mode experiment execution with no errors and identical baseline replay.

**P1a measurable causal label/signal gate: NOT ESTABLISHED.** Global RGB RMS did not measurably change for eleven tiny one-owner × one-cascade interventions. The twelfth yielded only ~1e-5 of the baseline error *as a fraction*. This is not evidence that confidence-driven scheduling works or cannot work. With merely four additional rays into one of potentially thousands of outputs, a global 320×180 average can be insensitive even if some local values changed.

There are two important source-level ambiguities, requiring diagnostics rather than hypothesis tuning:

1. **Observability:** unchanged global RMS may hide exactly unchanged HDR pixels versus changed HDR pixels with negligible/cancelling global error change. The summary alone cannot distinguish these; it does not carry raw difference-image statistics.
2. **Allocation influence:** current storage aggregates owner output estimates by shared `(probe_xyz, cascade)` and composite fetches these spatial keys, *not* the screen owner's `tile_id`. Multiple owners may contribute to a shared key or a selected key may not influence the final image. One-owner interventions can be diluted by this projection. The source audit had established executable work identity, but not the final-image influence map.

The 11 zero/global-mean responses and the tiny twelfth label **do not support fitting a predictive ranking or implementing a scheduler**. Do not select the apparently best cascade/tile from these three exploratory points and call it a general rule.

## Next gate: existing-artifact image audit, **zero GPU reruns**

Added `scripts/research/n006_interval_aware_allocation/audit_p1a_images.py` and tests. On the user's retained `*-cli-repair` output directory it will:

- Verify completed campaign and preserved reference SHA; verify baseline/reference and baseline-repeat consistency.
- Read all 12 corresponding frozen evidence JSON files and original RGB PFM images; verify each targeted tile, cascade, exact four-ray budget and correctness.
- Report how many RGB channels/pixels really changed, image-to-image L1/RMS/max delta, signed beneficial/harmful affected pixels versus the independent reference, and whether the selected screen tile changed.
- Recompute signed global RGB RMS gain and reject inconsistencies.

The audit writes a **new, separate** output under `out/research/n006-interval-aware-allocation/p1a-image-audit/<timestamp>/`, never overwrites raw GPU campaigns.

If most interventions have **zero changed pixels**, next research priority should be a positive-control/coverage probe to distinguish ineffective sampled transport or quantization from unreachable stored probe keys, not a larger predictive dataset. If pixels change but global benefit remains negligible, design a separate prospective P1a diagnostic of influence/relative-tail sensitivity while retaining **actual signed final-global-image gain as the scientific endpoint**. In both cases P1/P2 gates stay closed until measurement sensitivity is demonstrated.

## Boundaries

Results from this run are calibration only. Do not use them as N006 P1 held-out evidence, do not reinterpret N004/N005 frozen thresholds, do not tune selection on these same twelve points and claim formal success. Do not benchmark serial shader dispatch as viable cost. GPU timing repeats, negative-gain observations and fixed-K combined-intervention comparisons remain necessary for any future scheduler claim. No GitHub Actions.
