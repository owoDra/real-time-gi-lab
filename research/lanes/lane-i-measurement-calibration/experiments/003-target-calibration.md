# I003 — target calibration execution

Status: **READY FOR TARGET GPU after I001 validation**.

Use the frozen I002 config without editing it.

## Preconditions

- branch: `research-lane-i-measurement-calibration`;
- clean worktree;
- target: `AMD Radeon 8060S Graphics (RADV STRIX_HALO)`;
- successful I001 validation on the same commit;
- no forced GPU power/clock state manipulation.

## GPU-independent checks

Run:

```bash
mise run configure
mise exec -- cmake --build "$PHOS_GI_BUILD_DIR" --target phos-lane-i-contract-test phos-lane-i-i001
mise exec -- "$PHOS_GI_BUILD_DIR/phos-lane-i-contract-test"
mise exec -- python scripts/research/lane_i_measurement_calibration/test_analysis.py
mise run research:check
```

## Target validation

Validation is correctness/provenance evidence, not accepted performance evidence:

```bash
mise exec -- python scripts/research/run_experiment.py \
  --lane lane-i-measurement-calibration \
  --experiment 001-calibration-workload \
  --command "python scripts/research/lane_i_measurement_calibration/run_i001.py --validation"
```

Do not use validation-layer timing values for I003 decisions.

## Accepted I003 timing

Only after I001 validation passes:

```bash
mise exec -- python scripts/research/run_experiment.py \
  --lane lane-i-measurement-calibration \
  --experiment 003-target-calibration \
  --command "python scripts/research/lane_i_measurement_calibration/run_i003.py"
```

The accepted runner uses only automatic GPU power management and the frozen
`lane-i-i002-v1` protocol.

If the host becomes unstable, do not rerun this methodology. Preserve the
partial artifact as invalid/unsafe evidence.

If the campaign completes, `i003-summary.json` determines the GPU and wall
effect-size resolution. No threshold, workload, ordering, or repeat count may
be changed after seeing the result.
