# Lane N — end-to-end renderer integration

Issue: #26  
Canonical branch: `research-lane-n-end-to-end-renderer`  
Architecture base: `research@a75cf7857761cfbc783c9f1f847dc1380359481e`

Status: **N001 GPU-independent implementation complete; target execution pending**.

Lane N is the image-producing end-to-end lane. It preserves the accepted A–M architecture from `research/status.md` and establishes trustworthy HDR/reference/timing/memory/provenance boundaries before any new GI feature or performance winner claim.

N001 implementation truth is split across:

- `experiments/001-n001-config.json` — frozen workload/metric contract;
- `experiments/001-n001-source-provenance.json` — exact accepted A/B/E source snapshots;
- `src/research/lane_n_end_to_end_renderer/` — image renderer + diffuse reference;
- `scripts/research/lane_n_end_to_end_renderer/` — contract and target artifact validation.

Raw target artifacts remain under `out/research/`. N002–N005 must stay in the Issue #26 order.
