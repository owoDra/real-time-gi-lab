# G002c — power-isolated paired repeatability validation

Status: **pending target-GPU evidence**

This remains part of G002. It does not modify the GI architecture.

G002b showed that the transient-LBVH moving paths themselves were repeatable,
while their process-local software comparators repeatedly switched between
distinct timing bands. The automatic-DPM paired protocol therefore failed.

G002c repeats the exact frozen G002b comparison matrix and statistics under one
additional pre-frozen condition:

`power_dpm_force_performance_level=profile_peak`.

The runner is deliberately read-only. It verifies the AMDGPU sysfs setting
before and after every child process and aborts if the condition changes.

No run may be deleted or replaced.

See `002c-power-isolated-config.json` for the frozen matrix and criteria.
