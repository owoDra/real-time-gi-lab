# Lane N — end-to-end renderer integration

Issue: #26  
Canonical branch: `research-lane-n-end-to-end-renderer`  
Architecture base: `research@a75cf7857761cfbc783c9f1f847dc1380359481e`

Status: **N001 complete; N002 core five-scenario target implementation ready (#27), topology/high-churn adapter still pending**.

Lane N is the image-producing end-to-end lane. It preserves the accepted A–M architecture from `research/status.md` and establishes trustworthy HDR/reference/timing/memory/provenance boundaries before any new GI feature or performance winner claim.

N001 implementation/result truth is split across:

- `experiments/001-n001-config.json` — frozen workload/metric contract;
- `experiments/001-n001-source-provenance.json` — exact accepted A/B/E source snapshots;
- `src/research/lane_n_end_to_end_renderer/` — image renderer + diffuse reference;
- `scripts/research/lane_n_end_to_end_renderer/` — contract, target artifact validation, and HDR signal sanity;
- `results/001-renderer-reference-bringup.md` — accepted N001 target result.

N001 passed target correctness/provenance and campaign-level renderer/reference HDR signal sanity on the target AMD Radeon 8060S. Individual black reference frames remain valid observations; no samples were excluded. N001 makes no performance-winner claim.

N002 is staged without weakening its completion gate:

- `experiments/002-n002-config.json` freezes the first target checkpoint for static, camera motion, changing light, moving rigid, and stable-topology deformation;
- `n002_main.cpp` / `phos-n002` run those five scenarios through the current accepted Lane-E-final HWRT renderer boundary;
- `n002_contract.py` / `run_n002.py` produce and validate deterministic target artifacts;
- topology-changing/high-churn remains mandatory before N002 can be marked complete.

The topology/high-churn follow-up must preserve the Lane-M retained incumbent: immutable static ownership plus an independently rebuilt dynamic-object backend, including old/new overlap and true lifetime peak accounting. A whole-scene rebuild is not an acceptable substitute.

N002 timing is descriptive only until the Lane-N complete-frame boundary receives its own prospectively frozen calibration. Lane K's 5% and Lane L's 20% floors are not imported as N002 thresholds.

Raw target artifacts remain under `out/research/`. Proceed in Issue #26 order: complete N002 (#27), then N003–N005.
