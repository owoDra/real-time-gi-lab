# N006 P1a — bounded owner × cascade counterfactual pilot

Issue #42. Status: **prospective calibration-only pilot; no GPU evidence yet**.  
Parent: N006 P0 GPU smoke (PASS), and P0 source conclusion (owner × cascade looks executable).

## Purpose

Verify that *one screen-visible owner × one cascade* can receive an isolated, deterministic additional four-ray intervention, that its complete-GI image remains correct, and that paired baseline/intervention image differences can be compared to a single independent reference.

**This is not N006 P1 predictive-signal evidence, a scheduler implementation, or formal performance evidence.** It does not compare trained signals or claim an N006 improvement. If the pilot fails, preserve evidence and repair the experiment rather than relaxing validity rules.

## Frozen small pilot (before running)

- Case: `deforming-control` / stable-topology deformation, one target frame, 32 source warmup frames; renderer target `LaneEFinalHwrt`.
- `current` baseline with independent converged 8-bounce reference; a second fresh-process current repeat with `--skip-reference` checks run-to-run image noise.
- Three screen-visible tile IDs selected by fixed sorted-tile quantiles **without looking at image error, depth score or intervention outcome**. If a tile becomes ineligible, retain the failed attempt; do not silently choose another.
- For each tile, probe cascade indexes 0,1,2,3 independently. Each intervention appends **exactly four** deterministic extra rays to that tile/cascade's existing output ID. Baseline work stays intact.
- All intervention target renders reuse the single canonical baseline reference; no target-dependent new reference/tuning.
- Required per-run validation: correct device, source/frame correctness, base prefix, unit identity/direction, 4 actual extra rays, zero substantive traversal mismatch/overflow/storage failures, retained source/target logs and images.
- Summary: signed global RGB RMS gain and gain/ray, repeat-baseline image RMS noise floor, descriptive complete-GI GPU microseconds, every attempted intervention/failure. No per-regime claim or GPU cost inference from single process.
- Frozen computational allocation: 12 interventions + two current runs; 4 cascades, 3 visible tiles, 4 rays per intervention. This pilot probes single-unit gain, **not equal-budget top-K combined gain**, so non-additivity and scheduler-cost questions remain open.
- Artifacts: `out/research/n006-interval-aware-allocation/p1-causal-pilot/<timestamp>/`; leave all raw samples intact.
- Forbidden: sample deletion, post-hoc tile substitution, GPU power/profile changes, reliance on temporal convergence, changing N004/N005 frozen results, GitHub Actions.

## Source ownership / scope

The pilot isolates derived N006-only C++ runtime/main under `src/research/n006_interval_aware_allocation/` with a shader `shaders/research/n006_interval_aware_allocation/n006_extra_producer.comp.glsl`. It intentionally duplicates the minimal N005 experiment integration translation-unit boundary to avoid mutating the **completed N005 frozen lineage**. This is experiment-only code, not the proposed production scheduler API.

The pilot shader scans the existing base work for a requested **tile ID and cascade**, keeps the representative output identity, and adds four rays. It does **not** build confidence arrays or skip any base transport. Because scalar output averaging uses actual accumulated samples, variable cascade sample count is plausible but still needs hardware validation for correct behavior and bias.

## User GPU command

After pulling the branch:

```bash
mise run build
mise exec -- python -m unittest discover -s scripts/research/n006_interval_aware_allocation -p 'test_*.py'
mise exec -- python scripts/research/n006_interval_aware_allocation/run_p1_pilot.py
```

If a build, test or experiment fails, report the terminal error and resulting `stderr.log`; **do not rerun with changed inputs or delete an artifact** before reviewing the failure.

Pass `n006-p1-pilot-summary.json` back for review. The full artifact directory must be preserved if a follow-up asks for specific per-run evidence. A successful pilot authorizes the next **prospective P1 signal-ranking contract** but does not authorize P2/P3.
