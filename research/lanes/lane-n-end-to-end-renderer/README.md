# Lane N — end-to-end renderer integration

Issue: #26  
Canonical branch: `research-lane-n-end-to-end-renderer`  
Architecture base: `research@a75cf7857761cfbc783c9f1f847dc1380359481e`

Status: **N001 complete; N002 full six-scenario baseline complete; comparison calibration next (#31)**.

Lane N is the image-producing end-to-end lane. It preserves the accepted A–M architecture from `research/status.md` and establishes trustworthy HDR/reference/timing/memory/provenance boundaries before any new GI feature or performance winner claim.

## N001

N001 renderer/reference bring-up is complete. See:

- `experiments/001-n001-config.json`;
- `experiments/001-n001-source-provenance.json`;
- `results/001-renderer-reference-bringup.md`.

The target AMD Radeon 8060S / RADV run passed correctness/provenance and campaign-level renderer/reference HDR signal sanity. Individual black reference frames remain valid observations. N001 makes no performance-winner claim.

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

N002 timing remains descriptive only. Its current `affected_pixel_fraction` is zero for every frame despite non-zero raw HDR errors, so that classification threshold is not suitable for the observed dim workload.

## Next gate

Complete #31 before N003:

- prospectively calibrate/freeze complete-GI and complete-renderer GPU timing interpretation;
- freeze warm-up/sample/rerun/aggregation/material-change rules;
- freeze a scale-appropriate image-quality interpretation while retaining raw HDR metrics and black-reference observations;
- do not import Lane K/L thresholds without Lane-N evidence;
- no sample deletion or post-hoc threshold relaxation.

Only after #31 is complete should N003 run vanilla Split Radiance Cascades under the same complete renderer boundary.

Raw target artifacts remain under `out/research/`. Continue in parent Issue #26.
