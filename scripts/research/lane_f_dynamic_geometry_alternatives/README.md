# Lane F research scripts

Issue #16 is the frozen protocol.

## F001

F001 has concluded with correctness PASS and baseline repeatability
INCONCLUSIVE. Its two permitted timing attempts are retained; do not rerun it
again under `lane-f-plan-v1`.

## F002

From a clean `research-lane-f-dynamic-geometry-alternatives` checkout:

```bash
git pull --ff-only
mise run research:check
mise run assets
mise run build
```

Validation/structural preflight:

```bash
mise run research:record \
  --lane lane-f-dynamic-geometry-alternatives \
  --experiment 002-pure-gpu-transient-lbvh-builder \
  --command "python scripts/research/lane_f_dynamic_geometry_alternatives/run_f002.py --build-dir build/release --validation-only"
```

Only after that artifact passes, accepted timing:

```bash
mise run research:record \
  --lane lane-f-dynamic-geometry-alternatives \
  --experiment 002-pure-gpu-transient-lbvh-builder \
  --command "python scripts/research/lane_f_dynamic_geometry_alternatives/run_f002.py --build-dir build/release --repeats 5 --skip-validation"
```

Each timing process performs exactly 10 warmup + 100 measured builders per
frozen size. The runner executes five process-level repeats and retains raw
per-process rows. The formal F002 feasibility gate remains pending because
F001's run-local vanilla moving-rigid comparator was unstable in both allowed
attempts; neither unstable median nor the historical ceiling may be silently
substituted.
