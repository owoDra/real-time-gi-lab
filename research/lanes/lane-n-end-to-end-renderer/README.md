# Lane N — end-to-end renderer integration

Issue: #26  
Canonical branch: `research-lane-n-end-to-end-renderer`  
Architecture base: `research@a75cf7857761cfbc783c9f1f847dc1380359481e`

Status: **N001 complete; N002 complete; N003 preflight v1–v4 timing-unsuitable; clock-pinned v5 next (#31)**.

Lane N is the image-producing end-to-end lane. It preserves the accepted A–M architecture from `research/status.md` and establishes trustworthy HDR/reference/timing/memory/provenance boundaries before any new GI feature or performance claim.

## N001

N001 renderer/reference bring-up is complete. See:

- `experiments/001-n001-config.json`;
- `experiments/001-n001-source-provenance.json`;
- `results/001-renderer-reference-bringup.md`.

The target AMD Radeon 8060S / RADV run passed correctness/provenance and campaign-level renderer/reference HDR signal sanity. Individual black reference frames remain valid observations. N001 makes no performance claim.

## N002

N002 current-architecture baseline is complete. See:

- `experiments/002-n002-config.json` — core five-scenario checkpoint;
- `experiments/002-n002-full-config.json` — final six-scenario playback;
- `n002_main.cpp` / `phos-n002` — static, camera, light, moving-rigid, stable-topology deformation;
- `n002_runtime.cpp`, `n002_hwrt_rebuild.cpp`, `n002_topology_main.cpp` / `phos-n002-topology` — topology-changing/high-churn object-local rebuild;
- `n002_full_contract.py` / `run_n002_full.py` — final completion artifact and validation;
- `results/002-current-architecture-baseline.md` — accepted target result.

Final evidence commit: `0188c7f7b4b43e5d887cd753d74a69e11a2ea764`.

The six-scenario artifact passed correctness, provenance, reference convergence, HDR campaign-signal, timing-accounting, and memory gates. Topology/high-churn replaced 398/796 dynamic-owner primitive identities, executed exactly one object-local backend rebuild, recorded 252,928 bytes of old/new overlap, and retained static ownership outside the rebuild path.

## N003 preflight/calibration

Issue #31 is part of Lane N and is the preflight for N003 proper, not a separate lane.

Retained failed timing calibrations:

- v1 (`422945ea...`): absolute fresh-process timing, 48.297% worst noise, 145% threshold;
- v2 (`aa46afd1...`): paired fresh-process A/A, 110% threshold, ~97% worst p95 effect;
- v3 (`ac143a56...`): same-process prewarm, 207.5% threshold, 82.3% worst complete-frame p95 effect;
- v4 (`8f9c78bd...`): hot-adjacent same-process A/A, 98.5% threshold and 27.2% worst complete-frame p95 effect. Static/stable/topology improved substantially, but moving-rigid still dominated robust timing noise.

Current v5 preserves the v4 binary and all statistical gates. The only new requirement is a pinned AMDGPU profiling state:

- `power_dpm_force_performance_level=profile_peak` before the campaign;
- verify the level before/after every block and at campaign end;
- retain available `pp_dpm_*` clock-state text in provenance;
- keep the eight-block AB/BA schedule, 32-frame hot-adjacent warm-up, complete-GI/renderer boundaries, stage diagnostics, MAD estimator, <=20% suitability gates, and zero sample exclusion unchanged.

See:

- `experiments/003-n003-preflight-calibration-v5-config.json`;
- `experiments/003-n003-preflight-calibration.md`;
- `n003_preflight_v5_contract.py` / `run_n003_preflight_v5.py` / `test_n003_preflight_v5_contract.py`;
- `n003_gpu_profile.sh`;
- reused `n003_preflight_main.cpp` / `phos-n003-preflight` measurement probe.

Quality interpretation remains accepted from v2: legacy fixed-absolute affected fraction is diagnostic-only; RGB RMS, p99 absolute luminance error, and scale-aware affected fraction are primary scenario-by-scenario metrics with no aggregate winner score.

N003 proper must not start until v5 passes and both the derived timing threshold and required GPU performance state are recorded in result truth.

Raw target artifacts remain under `out/research/`. Continue in parent Issue #26.
