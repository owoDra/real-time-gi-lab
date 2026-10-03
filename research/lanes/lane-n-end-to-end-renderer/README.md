# Lane N — end-to-end renderer integration

Issue: #26  
Canonical branch: `research-lane-n-end-to-end-renderer`  
Architecture base: `research@a75cf7857761cfbc783c9f1f847dc1380359481e`

Status: **N001 complete; N002 core target PASS and full six-scenario target ready (#27)**.

Lane N is the image-producing end-to-end lane. It preserves the accepted A–M architecture from `research/status.md` and establishes trustworthy HDR/reference/timing/memory/provenance boundaries before any new GI feature or performance winner claim.

N001 implementation/result truth is split across:

- `experiments/001-n001-config.json` — frozen workload/metric contract;
- `experiments/001-n001-source-provenance.json` — exact accepted A/B/E source snapshots;
- `src/research/lane_n_end_to_end_renderer/` — image renderer + diffuse reference;
- `scripts/research/lane_n_end_to_end_renderer/` — contract, target artifact validation, and HDR signal sanity;
- `results/001-renderer-reference-bringup.md` — accepted N001 target result.

N001 passed target correctness/provenance and campaign-level renderer/reference HDR signal sanity on the target AMD Radeon 8060S. Individual black reference frames remain valid observations; no samples were excluded. N001 makes no performance-winner claim.

N002 core checkpoint:

- `experiments/002-n002-config.json` freezes static, camera motion, changing light, moving rigid, and stable-topology deformation;
- `n002_main.cpp` / `phos-n002` run those five scenarios through the current accepted Lane-E-final HWRT renderer boundary;
- target artifact `002-current-architecture-baseline-core/20261003T044631Z` passed correctness, provenance, reference convergence and campaign HDR signal gates at commit `041171dbbd12ffaccd3d7c0f8105de77e4dbc672`.

N002 full completion target:

- `experiments/002-n002-full-config.json` freezes all six required scenarios;
- `n002_runtime.cpp`, `n002_hwrt_rebuild.cpp`, and `phos-n002-topology` add the Lane-M retained topology/high-churn incumbent without replacing the core runtime;
- topology churn replaces 50% of one dynamic object's primitive identities while retaining stable renderer slot capacity;
- static ownership/BLAS remains immutable;
- replacement dynamic BLAS is built, TLAS is switched, then the old dynamic BLAS is retired;
- old/new overlap and lifetime peak are part of the required evidence;
- `run_n002_full.py` combines the core five frames plus topology frame into one final six-frame provenance artifact;
- `n002_full_contract.py` is the final N002 completion gate.

N002 remains incomplete until that final target artifact passes. Timing remains descriptive only until the Lane-N complete-frame boundary receives its own prospectively frozen calibration; Lane K's 5% and Lane L's 20% floors are not imported as N002 thresholds.

Raw target artifacts remain under `out/research/`. Proceed in Issue #26 order: complete N002 (#27), then freeze the Lane-N comparison/calibration contract before N003–N005.
