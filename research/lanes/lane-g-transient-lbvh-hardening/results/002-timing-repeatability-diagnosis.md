# G002 — Timing-repeatability diagnosis

Status: **PENDING TARGET-GPU EVIDENCE**  
Plan: `lane-g-g002-v1`

## Purpose

Determine why F007 timing remained unstable even in controls and establish a
decision-valid timing protocol before G003.

G002 does **not** change architecture, allocation layout, workload semantics,
thresholds for G003 architecture gates, or the shared Hit/storage contracts.

## Frozen diagnostic dimensions

The harness separates:

- same-process repeat;
- fresh-process repeat matching F007;
- cold / extended warmup (0 / 1 / 4 / 16);
- isolated anchor scenarios;
- complete 12-scenario matrix;
- canonical versus reverse scenario ordering;
- candidate versus vanilla/HWRT/B003 controls;
- setup/CPU wall versus GPU timestamp phases;
- available GPU temperature/power/busy/clock sysfs telemetry;
- host load and CPU-frequency telemetry.

Outlier deletion is forbidden.

## Result

**Pending.** No G002 timing conclusion is recorded until target-GPU artifacts
are supplied.

G003 timing and memory hardening remain blocked until G002 evidence is reviewed
and a replacement measurement protocol, if required, is explicitly frozen in
this result and Issue #17.
