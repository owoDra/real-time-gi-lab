# N006 P1a initial GPU attempt — INVALID (CLI parsing), no scientific outcome

Issue #42. Run at 2026-10-08T14:28:47Z.  
Initial pilot HEAD: `2c54edd39ba2dca93c2a90cc062414fec65aecb2`; AMD Radeon 8060S (RADV STRIX_HALO).

## Facts in the user-provided initial summary

- State: `incomplete-errors-retained`, `calibration_only=true`, `formal=false`.
- Baseline / independent 8-bounce reference **succeeded**: `reference_spp=512`, `baseline_rgb_rms=3.019924015741972e-05`.
- Fresh-process current repeat: same RGB RMS; baseline-to-repeat image RGB RMS = **0.0**.
- Frozen visible-tile quantile IDs: **22890, 28359, 33786**.
- All **12** targeted attempts (each tile × four cascades) returned **process exit 2**; zero successful interventions, no causal marginal-value evidence.
- We do **not** claim the GPU experiment validated. The submitted summary listed stderr log paths but did not include their contents.

## Root cause located in committed source (strong evidence, not a GPU log quote)

`n006_intervention_main.cpp` declared and used `selected_tile_id`/`selected_cascade` but its argument parser omitted both `--selected-tile-id` and `--selected-cascade`. The pilot passed both flags, and the binary returned exit 2 from the unmatched-argument usage branch. This is an experiment harness coding error, not a negative result for the research hypothesis.

## Repair (prospective relative to repeat)

- Add parsing for both options and a *compiled-binary CLI contract test* that distinguishes exit 2 (unknown flags) from exit 1 (flags parsed, missing required scene/artefact paths).
- Add `resume_p1_pilot.py` using **only the accepted initial failed run**, with prior SHA pinned exactly, original source and baseline correctness, reference convergence, Sponza digest, frozen tile IDs, and all 12 failure labels independently validated before reuse.
- Do not overwrite the initial failed run. Create a separate new timestamped `*-cli-repair` artifact directory and copy the successful current and repeat artefacts. Verify a newly rebuilt/linked `current` image against the original baseline with whole-image RGB RMS <= **1e-8** before accepting reference reuse. Any mismatch must hard stop without generating intervention results.
- New targeted experiments keep exactly the same **3 tiles, four cascades, four rays/unit** and the same independent reference. We neither retune nor reselect based on image error.
- Existing failed attempts remain in the original evidence. The repair result is separately labeled `P1a-causal-feasibility-pilot-cli-repair` and includes source campaign path/reference hash/head, compatibility check and any subsequent failures.

## User execution

```bash
git fetch origin research-n006-interval-aware-allocation
git switch research-n006-interval-aware-allocation
git pull --ff-only
mise run build
mise exec -- python -m unittest discover -s scripts/research/n006_interval_aware_allocation -p 'test_*.py'
mise exec -- python scripts/research/n006_interval_aware_allocation/resume_p1_pilot.py \
  --failed-campaign out/research/n006-interval-aware-allocation/p1-causal-pilot/20261008T142847Z
```

Give back `n006-p1-pilot-summary.json` from the **new** `*-cli-repair` directory; preserve the old campaign. This repair still does not constitute formal predictive signal evidence, N006 scheduler comparison, or GPU timing study.

No N004/N005 outcomes changed, no GitHub Actions.
