# Lane N — end-to-end renderer integration

Issue: #26  
Canonical branch: `research-lane-n-end-to-end-renderer`  
Architecture base: `research@a75cf7857761cfbc783c9f1f847dc1380359481e`

Status: **N001 complete; N002 complete; N003 preflight v1 timing-unsuitable; paired-control v2 next (#31)**.

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

Issue #31 is part of Lane N and is the preflight for N003 proper, not a separate lane. See:

- `experiments/003-n003-preflight-calibration-config.json`;
- `experiments/003-n003-preflight-calibration.md`;
- `n003_preflight_contract.py` / `run_n003_preflight.py` / `test_n003_preflight_contract.py`.

v1 at commit `422945ea32164e487e8562214dc7568f6e2ad9a6` measured absolute timing across six fresh processes. It correctly failed as timing-unsuitable: worst noise 48.297%, implied material-change threshold 145%. The failed artifact is retained.

v2 is frozen before any current-vs-vanilla measurement and calibrates the actual N003 decision unit: eight fresh-process current/current A/A pairs. The primary statistic is median paired `log(B/A)`; robust null spread uses MAD. A future timing claim requires both the derived magnitude threshold and at least 75% same-direction paired effects. A/A control must not trigger that rule, and its worst p95 pair effect must remain <=20%.

The legacy fixed-absolute `affected_pixel_fraction` remains diagnostic-only. N003 uses scale-aware affected pixels with `abs_error >= 0.05 * max(abs(reference_luminance), 0.0001)` alongside RGB RMS and p99 absolute luminance error. Quality remains scenario-by-scenario with no aggregate winner score.

N003 proper must not start until paired-control v2 passes and the derived timing threshold is recorded in result truth.

Raw target artifacts remain under `out/research/`. Continue in parent Issue #26.
