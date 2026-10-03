# Lane N — end-to-end renderer integration

Issue: #26  
Canonical branch: `research-lane-n-end-to-end-renderer`  
Architecture base: `research@a75cf7857761cfbc783c9f1f847dc1380359481e`

Status: **N001 complete; N002 complete; N003 complete; N004 implemented and awaiting local build/probe evidence (#39)**.

Lane N is the image-producing end-to-end lane. It preserves the accepted A–M architecture from `research/status.md` and establishes trustworthy HDR/reference/timing/memory/provenance boundaries before any new GI feature or performance claim.

## N001

N001 renderer/reference bring-up is complete. See `experiments/001-n001-config.json`, `experiments/001-n001-source-provenance.json`, and `results/001-renderer-reference-bringup.md`.

## N002

N002 current-architecture baseline is complete. Final evidence commit: `0188c7f7b4b43e5d887cd753d74a69e11a2ea764`.

The six-scenario artifact passed correctness, provenance, reference convergence, HDR campaign-signal, timing-accounting, and memory gates. Topology/high-churn replaced 398/796 dynamic-owner primitive identities, executed exactly one object-local backend rebuild, recorded 252,928 bytes of old/new overlap, and retained static ownership outside the rebuild path.

## N003 preflight/calibration

Issue #31 is complete. See `results/003-preflight-calibration.md`.

Retained calibration lineage: v1 145%, v2 110%, v3 207.5%, v4 98.5% all timing-unsuitable; v5 clock-pinned proposal withdrawn for host safety; v6 replicated median made five scenarios timing-eligible while moving-rigid remained measurement-limited despite exact workload invariance.

**Lane N must not change GPU power/performance profiles.** The host GPU policy remains unchanged.

Frozen N003 thresholds: static 7.0%, camera 1.5%, light 5.0%, stable deforming 2.5%, topology/high-churn 1.5%; moving-rigid has no formal timing claim.

## N003 proper

Issue #38 is complete. See `experiments/003-n003-comparison.md` and `results/003-current-vs-vanilla.md`.

Formal complete-renderer median vanilla/current ratios were 3.023x static, 2.756x camera, 3.108x light, 2.506x stable deforming and 2.354x topology/high-churn, all favoring current with 8/8 blocks in the same direction. Moving-rigid was descriptively ~1.787x but remains timing measurement-limited.

Quality was equal across all six scenarios. Device true-lifetime peak is the retained trade-off: current is about 26.5% heavier in ordinary scenarios and 23.9% heavier under topology churn. Non-formal CPU/host diagnostics strongly favor current for dynamic updates.

N003 confirms that the accepted support architecture survives the integrated renderer boundary against the mandatory vanilla Split RC baseline.

## N004 weakness atlas

Issue #39 is active. Prospective contract: `experiments/004-n004-weakness-atlas-config.json`; design/interpretation truth: `experiments/004-n004-weakness-atlas.md`.

Implementation is complete but no target result is accepted yet.

The atlas measures, without mitigation:

- leak thickness sweep plus grazing, one-sided and enclosed occluder cases;
- abrupt and gradual camera/disocclusion paths;
- step and gradual illumination changes;
- rigid, stable-deforming and topology-changing dynamic classes;
- sparse, dense, large-horizontal and vertical/tall synthetic world layouts;
- higher-order diffuse and glossy/specular capability boundaries.

Synthetic scenes are deterministic multi-mesh glTFs with a frozen 36-triangle idle dynamic control object so the primary synthetic geometry remains static ownership. N004 does not change the accepted A001 runtime used by N001–N003: the atlas target links an isolated wrapper that adds only prospective camera/light fractions.

Generic image classification thresholds and leak-specific false-irradiance thresholds are frozen before target data. Moving-rigid timing remains measurement-limited. All raw samples are retained, aggregate weakness scores are forbidden, and the accepted completed-campaign rerun budget is zero.

Build/contract/probe locally before the one accepted N004 target campaign. Raw target artifacts remain under `out/research/`.
