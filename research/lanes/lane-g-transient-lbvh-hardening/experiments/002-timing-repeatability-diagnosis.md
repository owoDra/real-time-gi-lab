# G002 — Timing-repeatability diagnosis

Status: **implementation complete; target-GPU evidence pending**

## Frozen purpose

Diagnose the F007 timing-repeatability failure without changing architecture.

G002 separates:

- same-process repeat;
- fresh-process repeat;
- isolated anchor scenarios;
- the complete 12-scenario matrix;
- cold / extended warmup;
- canonical / reverse scenario ordering;
- allocator/cache/process residency effects;
- first-use HWRT effects;
- CPU wall versus GPU timestamp phases;
- available clocks/power/thermal/load telemetry.

## Important dynamic-frame interpretation

For dynamic scenarios, a fresh process performs static warmup frames followed by
one target transition frame. This matches the F007 timing boundary.

For the same-process phase, measured row 0 is the transition frame. Later
measured rows are **post-transition diagnostics**, not repeated copies of the
full F007 transition. In particular, HWRT/software controls do not repeat their
geometry maintenance after the first target transition. These later rows may be
used to diagnose within-process GPU/query/cache variability, but must not be
used as formal moving-geometry comparator timing.

## Frozen matrix

See `002-timing-repeatability-diagnosis-config.json`.

No outlier deletion is permitted. G002 diagnostic thresholds are not G003
architecture promotion thresholds.

## Completion rule

G002 completes only after the evidence supports a measurement protocol with
repeatability for both the LBVH candidate and controls. If methodology changes
are required, the replacement protocol and repeatability criteria must be
recorded in Issue #17 and the G002 result before any G003 decision-valid timing.
