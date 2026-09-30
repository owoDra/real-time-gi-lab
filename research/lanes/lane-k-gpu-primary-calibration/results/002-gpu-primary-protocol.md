# K002 — frozen GPU-primary protocol

## Formal status

**Accepted as a methodology freeze before K003 target timing.**

- Plan: `lane-k-k002-v1`
- Freeze commit: `c886d0f33f63de131da9db3757f2c0b05c7c2634`
- Canonical config:
  `research/lanes/lane-k-gpu-primary-calibration/experiments/002-gpu-primary-protocol-config.json`

GPU timestamp is the sole primary performance decision axis. Complete CPU wall
is diagnostic / health / provenance only.

The GPU thresholds reuse the pre-target Lane-I I002 GPU criteria as methodology
parameters. No Lane-I I003 target result is imported as Lane-K evidence.

CPU-wall repeatability warnings do not veto GPU resolution. Only structural
health failures frozen in K002 invalidate the campaign.

No target K003 timing had been observed when this protocol was frozen.
