# Lane G research scripts

G001 writes retained artifacts under:

`out/research/lane-g-transient-lbvh-hardening/001-memory-ownership-lifetime-census/<timestamp>/`

GPU-independent checks:

```bash
mise exec -- python -m unittest scripts/research/lane_g_transient_lbvh_hardening/test_run_g001.py
mise run research:check
mise run build
```

Accepted G001 target run:

```bash
mise run assets
mise run build
mise exec -- python scripts/research/lane_g_transient_lbvh_hardening/run_g001.py --validation
```

The runner requires a clean `research-lane-g-transient-lbvh-hardening`
worktree and exact device
`AMD Radeon 8060S Graphics (RADV STRIX_HALO)`. It aborts if the individual
allocation census differs from the F007 peak accounting by one byte, if a
required ownership role is missing, or if a Vulkan allocation lacks logical
payload size.

## G002

GPU-independent checks:

```bash
mise exec -- python -m unittest scripts/research/lane_g_transient_lbvh_hardening/test_run_g002.py
mise run research:check
mise run build
```

Target diagnostic campaign:

```bash
mise exec -- python scripts/research/lane_g_transient_lbvh_hardening/run_g002.py --phase all
```

G002 timing runs intentionally disable validation/quality readback, matching the
F007 timing boundary. G001 already established correctness on the same runtime
architecture. System telemetry is best-effort: unavailable sysfs probes are
recorded as null rather than invalidating the timing campaign.

## G002c power-isolated validation

First identify the AMDGPU device exposing the performance-level control:

```bash
find /sys/class/drm/card*/device \
  -name power_dpm_force_performance_level -print
```

Set that file to `profile_peak` before running the experiment. Example, after
replacing `cardN` with the device found above:

```bash
POWER_LEVEL=/sys/class/drm/cardN/device/power_dpm_force_performance_level
cat "$POWER_LEVEL"
echo profile_peak | sudo tee "$POWER_LEVEL"
cat "$POWER_LEVEL"
```

Then run:

```bash
mise exec -- python -m unittest \
  scripts/research/lane_g_transient_lbvh_hardening/test_run_g002c.py

mise exec -- python \
  scripts/research/lane_g_transient_lbvh_hardening/run_g002c.py \
  --amdgpu-sysfs /sys/class/drm/cardN/device
```

The runner does not mutate sysfs and aborts unless the setting is exactly
`profile_peak` before and after every child measurement.

After the experiment, restore normal dynamic power management even if the
experiment failed:

```bash
echo auto | sudo tee "$POWER_LEVEL"
```

Expected retained artifacts include `g002c-summary.json`,
`g002c-block-ratios.csv`, `g002c-raw.csv`, `g002c-config.json`, and
`metadata.json`.
