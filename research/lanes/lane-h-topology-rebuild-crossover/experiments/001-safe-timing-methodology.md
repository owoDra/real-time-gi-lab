# H001 — safe timing methodology

Status: **historical frozen v1 / closed INCONCLUSIVE**

Result: `../results/001-safe-timing-methodology.md`

This document records the exact pre-run v1 plan. Post-run review showed that the
reused I001Runtime transition is one-way, so the dynamic alternation below did
not actually cross the geometry-update boundary on every measured frame. The
frozen config is intentionally unchanged for provenance.

H001 changes the measurement harness only. It does not change the Lane G runtime,
producer, traversal, storage, Hit semantics, or candidate architecture.

The frozen machine-readable protocol is
`001-safe-timing-methodology-config.json` and takes precedence over prose below.

## Frozen campaign

- target: `AMD Radeon 8060S Graphics (RADV STRIX_HALO)`;
- warmup: 16 frames per fresh process;
- measured: 16 frames per fresh process;
- fresh-process blocks: 8;
- settle interval: 1.0 s before every process;
- instability rerun budget: **0**;
- all raw warmup and measured rows retained;
- accepted timing has Vulkan validation disabled;
- no GPU power/clock manipulation.

Cases:

1. static / representative-rigid;
2. moving-rigid / representative-rigid;
3. moving-rigid / topology-replace25.

Variants:

- A: hardened transient LBVH;
- B: unchanged transient LBVH;
- C: combined HWRT control;
- D: vanilla software control.

The eight block orders are position-balanced and include reversed orientation:
`ABCD`, `BCDA`, `CDAB`, `DABC`, `DCBA`, `ADCB`, `BADC`, `CBAD`.

For dynamic cases the v1 plan alternated the runtime target state on every warmup
and measured frame. The plan intended this to avoid treating one transition
followed by steady frames as repeated dynamic-update samples. Post-run review
proved that assumption false for I001Runtime: only the first target transition
updates geometry. Static remains in one state.

## Measurement boundaries

Two axes are evaluated independently:

- **GPU:** existing complete-frame GPU timestamp boundary (`complete_gpu_us`);
- **CPU wall:** `steady_clock` around the entire `run_frame` call
  (`complete_frame_wall_us`).

Process setup wall is recorded separately and is not folded into the recurrent
frame statistic. Warmup samples are retained so first-use/warmup behavior remains
auditable, but only measured samples enter the repeatability statistic.

Background interference is observational only: load averages, available memory,
and process monotonic start/end timestamps are retained. H001 does not invent a
post-hoc host-load exclusion threshold.

## Frozen repeatability gate

Each case/variant row must pass every criterion for both GPU and CPU-wall axes:

- within-process p90/p10 <= 1.10 GPU, <= 1.15 wall;
- first-4 vs last-4 median ratio <= 1.10 GPU, <= 1.15 wall;
- fresh-process median max/min <= 1.10 GPU, <= 1.15 wall;
- fresh-process MAD/median <= 0.04 GPU, <= 0.06 wall;
- process-slot-position median max/min <= 1.10 GPU, <= 1.15 wall.

The campaign passes only when **all candidate and controls rows pass**. No outlier
removal, fastest-subset selection, threshold adjustment, or instability rerun is
allowed. A failed row makes H001 **INCONCLUSIVE**.

## Interpretation

H001 can establish only that this safe measurement boundary is repeatable enough
to support later same-boundary comparisons. It cannot prmote a topology backend
and it does not establish a DVFS or clock/power root cause.

H003 remains forbidden until H001 passes on the target GPU.
