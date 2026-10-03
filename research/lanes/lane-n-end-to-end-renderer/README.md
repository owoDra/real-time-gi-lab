# Lane N — end-to-end renderer integration

Issue: #26  
Canonical branch: `research-lane-n-end-to-end-renderer`  
Architecture base: `research@a75cf7857761cfbc783c9f1f847dc1380359481e`

Status: **N001 complete; N002 complete; N003 preflight complete; N003 proper unblocked**.

Lane N is the image-producing end-to-end lane. It preserves the accepted A–M architecture from `research/status.md` and establishes trustworthy HDR/reference/timing/memory/provenance boundaries before any new GI feature or performance claim.

## N001

N001 renderer/reference bring-up is complete. See `experiments/001-n001-config.json`, `experiments/001-n001-source-provenance.json`, and `results/001-renderer-reference-bringup.md`.

## N002

N002 current-architecture baseline is complete. Final evidence commit: `0188c7f7b4b43e5d887cd753d74a69e11a2ea764`.

The six-scenario artifact passed correctness, provenance, reference convergence, HDR campaign-signal, timing-accounting, and memory gates. Topology/high-churn replaced 398/796 dynamic-owner primitive identities, executed exactly one object-local backend rebuild, recorded 252,928 bytes of old/new overlap, and retained static ownership outside the rebuild path.

## N003 preflight/calibration

Issue #31 is complete. See `results/003-preflight-calibration.md`.

Retained calibration lineage:

- v1: 145% global threshold, timing-unsuitable;
- v2: 110%, timing-unsuitable; quality interpretation accepted;
- v3: 207.5%, timing-unsuitable;
- v4: 98.5%, timing-unsuitable;
- v5: withdrawn before target execution because forcing the target GPU performance profile can trigger host safety shutdown;
- v6: all 40 replicated-median micro-pairs retained, zero false formal claims, worst p95 block effect 18.4%, but moving-rigid drove the global threshold to 28.5%.

The moving-rigid workload diagnostic then proved exact source/target integer workload invariance across A/B and all eight blocks. Its remaining timing variation is therefore measurement/execution-state limited rather than workload-count drift.

**Lane N must not change GPU power/performance profiles.** The host GPU policy remains unchanged.

N003 timing interpretation is frozen per scenario before current-vs-vanilla data is collected:

- static: 7.0%;
- camera-motion: 1.5%;
- light-motion: 5.0%;
- moving-rigid: timing-inconclusive, no formal performance win/loss claim;
- stable-topology-deforming: 2.5%;
- topology-changing-high-churn: 1.5%.

The same scenario threshold applies to complete-GI and complete-renderer axes, based on the worse calibrated axis. Formal claims still require >=75% same-direction outer blocks. No sample deletion, threshold relaxation or cross-scenario aggregate timing winner is permitted.

Moving-rigid remains valid for correctness, workload, memory and image-quality comparison; its timing is descriptive only.

Quality interpretation remains accepted from v2: legacy fixed-absolute affected fraction is diagnostic-only; RGB RMS, p99 absolute luminance error, and scale-aware affected fraction are primary scenario-by-scenario metrics with no aggregate winner score.

## N003 proper

N003 proper is now unblocked: compare the current architecture against a fair vanilla Split Radiance Cascades baseline under identical scene, transport semantics, resolution, rays/probes/cascades, reference frames, timing boundary and memory boundary.

Do not simplify vanilla Split RC or add new transport features. Report timing only for calibrated-eligible scenarios; report moving-rigid timing as measurement-limited. Quality/memory/correctness remain scenario-by-scenario for all six scenarios.

Raw target artifacts remain under `out/research/`. Continue in parent Issue #26.
