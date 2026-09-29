# Lane F research scripts

Issue #16 is the frozen protocol.

## F001

From a clean `research-lane-f-dynamic-geometry-alternatives` checkout:

```bash
git pull
mise install
mise run research:check
mise run assets
mise run build
```

Validation/correctness preflight:

```bash
mise run research:record \
  --lane lane-f-dynamic-geometry-alternatives \
  --experiment 001-workload-census-baseline-replay \
  --command "python scripts/research/lane_f_dynamic_geometry_alternatives/run_f001.py --build-dir build/release --validation-only"
```

Only after that artifact passes, accepted timing:

```bash
mise run research:record \
  --lane lane-f-dynamic-geometry-alternatives \
  --experiment 001-workload-census-baseline-replay \
  --command "python scripts/research/lane_f_dynamic_geometry_alternatives/run_f001.py --build-dir build/release --repeats 5 --skip-validation"
```

The timing runner automatically reuses the newest prior passing F001 validation
artifact from the same clean commit and copies its validation state into the
timing artifact. Timing is rejected if no matching validation artifact exists.

F001 produces the frozen-schema files `f001-config.json`,
`f001-device.json`, `f001-validation.json`, `f001-raw.csv`,
`f001-summary.json`, plus `f001-census.json`.

The lane-local I001 control adapter uses the accepted I001 runtime unchanged but
adds a wall-clock boundary around the measured target-frame call. Static setup
remains separate.
