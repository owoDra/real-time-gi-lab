# Lane N — end-to-end renderer integration

Issue: #26  
Canonical branch: `research-lane-n-end-to-end-renderer`  
Architecture base: `research@a75cf7857761cfbc783c9f1f847dc1380359481e`

Status: **N001 complete; N002 complete; N003 preflight v1–v4/v6 timing-unsuitable; v5 withdrawn for host safety; moving-rigid workload diagnostic next (#31)**.

Lane N is the image-producing end-to-end lane. It preserves the accepted A–M architecture from `research/status.md` and establishes trustworthy HDR/reference/timing/memory/provenance boundaries before any new GI feature or performance claim.

## N001

N001 renderer/reference bring-up is complete. See `experiments/001-n001-config.json`, `experiments/001-n001-source-provenance.json`, and `results/001-renderer-reference-bringup.md`.

## N002

N002 current-architecture baseline is complete. Final evidence commit: `0188c7f7b4b43e5d887cd753d74a69e11a2ea764`.

The six-scenario artifact passed correctness, provenance, reference convergence, HDR campaign-signal, timing-accounting, and memory gates. Topology/high-churn replaced 398/796 dynamic-owner primitive identities, executed exactly one object-local backend rebuild, recorded 252,928 bytes of old/new overlap, and retained static ownership outside the rebuild path.

## N003 preflight/calibration

Issue #31 is part of Lane N and is the preflight for N003 proper, not a separate lane.

Retained calibration lineage:

- v1 (`422945ea...`): 145% threshold, `timing-unsuitable`;
- v2 (`aa46afd1...`): 110% threshold, `timing-unsuitable`; quality interpretation accepted;
- v3 (`ac143a56...`): 207.5% threshold, `timing-unsuitable`;
- v4 (`8f9c78bd...`): 98.5% threshold, 27.2% worst complete-frame p95, `timing-unsuitable`;
- v5: withdrawn before target execution because forcing the target GPU performance profile can trigger host safety shutdown;
- v6 (`00248643...` target evidence): all 40 micro-pairs retained, zero false formal claims, worst p95 block effect 18.4% but derived threshold 28.5%, therefore `timing-unsuitable`.

**Lane N must not change GPU power/performance profiles.** The host GPU policy remains unchanged.

v6 stabilized every scenario except moving-rigid sufficiently that simply increasing replication again is not justified. Moving-rigid alone dominates the residual robust timing noise. Geometry-upload block timing remains comparatively stable while frame-init/visibility remains volatile.

The current step is therefore a dedicated moving-rigid workload-invariance diagnostic:

- target: `phos-n003-workload-diagnostic`;
- eight fresh A/A pair blocks with the established AB/BA order;
- 32 source-state warm-up frames per role;
- normal host GPU policy; GPU profile changes explicitly forbidden;
- final source frame and first measured target transition record all integer `I001FrameStats` counters;
- exact counter invariance is required across A/B and all blocks;
- timing is diagnostic-only.

If counters vary, investigate moving-rigid workload/synchronization nondeterminism before any new timing estimator. If counters are invariant, the residual v6 timing variation is isolated to execution-time state and the next calibration may use only non-invasive methods such as read-only telemetry or an adjacent fixed sentinel workload.

See `experiments/003-n003-preflight-calibration.md`, `experiments/003-n003-moving-workload-diagnostic-config.json`, `n003_workload_diagnostic_main.cpp`, `n003_moving_workload_contract.py`, `run_n003_moving_workload_diagnostic.py`, and `test_n003_moving_workload_contract.py`.

Quality interpretation remains accepted from v2: legacy fixed-absolute affected fraction is diagnostic-only; RGB RMS, p99 absolute luminance error, and scale-aware affected fraction are primary scenario-by-scenario metrics with no aggregate winner score.

N003 proper remains blocked until the moving-rigid cause is resolved and a timing calibration passes prospectively.

Raw target artifacts remain under `out/research/`. Continue in parent Issue #26.
