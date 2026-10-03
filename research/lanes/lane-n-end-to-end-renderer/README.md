# Lane N — end-to-end renderer integration

Issue: #26  
Canonical branch: `research-lane-n-end-to-end-renderer`  
Architecture base: `research@a75cf7857761cfbc783c9f1f847dc1380359481e`

Status: **N001 complete; N002 next (#27)**.

Lane N is the image-producing end-to-end lane. It preserves the accepted A–M architecture from `research/status.md` and establishes trustworthy HDR/reference/timing/memory/provenance boundaries before any new GI feature or performance winner claim.

N001 implementation truth is split across:

- `experiments/001-n001-config.json` — frozen workload/metric contract;
- `experiments/001-n001-source-provenance.json` — exact accepted A/B/E source snapshots;
- `src/research/lane_n_end_to_end_renderer/` — image renderer + diffuse reference;
- `scripts/research/lane_n_end_to_end_renderer/` — contract, target artifact validation, and HDR signal sanity;
- `results/001-renderer-reference-bringup.md` — accepted N001 target result.

N001 passed target correctness/provenance and campaign-level renderer/reference HDR signal sanity on the target AMD Radeon 8060S. Individual black reference frames remain valid observations; no samples were excluded. N001 makes no performance-winner claim.

Raw target artifacts remain under `out/research/`. Proceed in Issue #26 order: N002 (#27), then N003–N005.
