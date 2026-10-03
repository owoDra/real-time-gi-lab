# Lane N — end-to-end renderer integration

Issue: #26  
Canonical branch: `research-lane-n-end-to-end-renderer`  
Architecture base: `research@a75cf7857761cfbc783c9f1f847dc1380359481e`

Status: **N001 complete; N002 complete; N003 preflight complete; N003 proper implemented and awaiting local build/target evidence (#38)**.

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

Frozen N003 timing thresholds:

- static: 7.0%;
- camera-motion: 1.5%;
- light-motion: 5.0%;
- moving-rigid: timing-inconclusive, no formal performance win/loss claim;
- stable-topology-deforming: 2.5%;
- topology-changing-high-churn: 1.5%.

The same scenario threshold applies to complete-GI and complete-renderer axes, based on the worse calibrated axis. Formal claims require >=75% same-direction outer blocks. No sample deletion, threshold relaxation or cross-scenario aggregate timing winner is permitted.

## N003 proper

Issue #38 tracks the fair current-vs-vanilla Split RC same-boundary comparison. See `experiments/003-n003-comparison-config.json` and `experiments/003-n003-comparison.md`.

Implementation is present but no N003 target result is accepted yet.

Current role:

- accepted N002 `LaneEFinalHwrt` renderer and object-local dynamic maintenance.

Vanilla role:

- historical Integration-13 global binary software-BVH baseline;
- same A001 Split RC producer/cascade/probe/ray semantics and C001-style sparse storage boundary;
- whole global BVH rebuild for dynamic/topology changes;
- N003-only software primary visibility and direct-light visibility so the baseline does not depend on current HWRT support architecture.

N001/N002 runtime implementation files remain unchanged. N003 adds comparison-only hooks through `n003_comparison_runtime.cpp`; shared declarations expose those hooks, and the imported HWRT header adds only a read-only host-mirror byte accessor for diagnostics.

Formal timing/device-memory evidence uses `phos-n003-comparison` with five micro-pairs x eight outer blocks. Quality/reference evidence is intentionally separate in `phos-n003-quality` so converged reference rendering cannot contaminate timing measurements. `phos-n003-diagnostics` separately records CPU wall/preparation data and renderer-owned host mirror capacity; these diagnostics are not formal performance axes.

Topology vanilla true-lifetime memory includes the largest synchronously overlapping upload staging allocation. Renderer-owned host mirror diagnostics include explicit scene/dynamic/BVH vector capacity only; opaque driver/Vulkan host memory and allocator bookkeeping are not guessed.

Quality remains scenario-by-scenario using RGB RMS, p99 absolute luminance error and scale-aware affected fraction. A material scenario direction requires at least two of three primary metrics to move materially in the same direction. No aggregate quality winner is permitted.

Moving-rigid remains valid for correctness, workload, memory and image quality; only its timing interpretation is measurement-limited.

Raw target artifacts remain under `out/research/`. Continue in Issue #38 and parent Issue #26.
