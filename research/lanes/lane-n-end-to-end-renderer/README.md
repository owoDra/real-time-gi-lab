# Lane N — end-to-end renderer integration

Issue: #26  
Canonical branch: `research-lane-n-end-to-end-renderer`  
Architecture base: `research@a75cf7857761cfbc783c9f1f847dc1380359481e`

Status: **N001 complete; N002 complete; N003 preflight v1–v4 timing-unsuitable; v5 withdrawn for host safety; replicated-median v6 next (#31)**.

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

Retained calibration lineage:

- v1 (`422945ea...`): 145% threshold, `timing-unsuitable`;
- v2 (`aa46afd1...`): 110% threshold, `timing-unsuitable`; quality interpretation accepted;
- v3 (`ac143a56...`): 207.5% threshold, `timing-unsuitable`;
- v4 (`8f9c78bd...`): 98.5% threshold, 27.2% worst complete-frame p95, `timing-unsuitable`; static/stable/topology improved substantially while moving-rigid remained noisy;
- v5: withdrawn before target execution because forcing the target GPU performance profile can trigger the host safety shutdown. GPU profile changes are now explicitly forbidden for Lane N measurement.

Current v6 reuses the v4 `phos-n003-preflight` probe without renderer/C++ changes or host GPU policy changes. Each of eight outer blocks contains five complete hot-adjacent A/A micro-pairs. All 40 micro-pairs remain raw evidence; the formal sample for each outer block is the median of its five paired log ratios. A one-off transient therefore cannot dominate a block, while instability affecting >=3/5 micro-pairs remains visible.

Formal gates remain strict: <=20% derived threshold, <=20% p95 block effect, zero A/A formal-claim triggers, >=75% same-direction outer blocks for any future current-vs-vanilla claim, no stage active/inactive mismatches, no sample deletion, and no completed-PASS rerun.

See:

- `experiments/003-n003-preflight-calibration-v6-config.json`;
- `experiments/003-n003-preflight-calibration.md`;
- `n003_preflight_v6_contract.py` / `run_n003_preflight_v6.py` / `test_n003_preflight_v6_contract.py`;
- reused `n003_preflight_main.cpp` / `phos-n003-preflight` measurement probe.

Quality interpretation remains accepted from v2: legacy fixed-absolute affected fraction is diagnostic-only; RGB RMS, p99 absolute luminance error, and scale-aware affected fraction are primary scenario-by-scenario metrics with no aggregate winner score.

N003 proper must not start until v6 passes and its derived timing threshold is recorded in result truth. N003 proper must use the same five-micro-pair/eight-block aggregation if accepted.

Raw target artifacts remain under `out/research/`. Continue in parent Issue #26.
