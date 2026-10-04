# Lane N — end-to-end renderer integration

Issue: #26  
Canonical branch: `research-lane-n-end-to-end-renderer`  
Architecture base: `research@a75cf7857761cfbc783c9f1f847dc1380359481e`

Status: **N001 complete; N002 complete; N003 complete; N004 complete; N005 transport question selected**.

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

Issue #39 is complete. Accepted protocol: `experiments/004-n004-weakness-atlas-v2-config.json`; design/lineage: `experiments/004-n004-weakness-atlas.md`; result truth: `results/004-weakness-atlas.md`.

The accepted campaign completed all six weakness families with no sample exclusion and no GPU profile changes. Whole-case checkpoint resume was used only after interruption: eight already-complete cases were validated and reused, the partial changing-light case was retained and rerun in full, and every remaining case ran normally.

Result summary:

- all six thin-geometry/light-leak cases: `not-observed-under-tested-regime`;
- abrupt and gradual camera/disocclusion: `material-blocker` under the frozen classifier;
- step and gradual illumination change: `present-but-bounded`;
- moving-rigid: `measurement-limited` for formal timing;
- stable-topology deformation and topology-changing/high-churn: `material-blocker` under the frozen classifier;
- sparse world-shape: `not-observed-under-tested-regime`;
- dense, large-horizontal and vertical/tall world-shape: `present-but-bounded`, with no correctness/capacity failure;
- higher-order diffuse and glossy/specular: `capability-not-implemented`; the 1-vs-8 bounce Sponza reference gap was not materially exposed.

The blocker labels are retained exactly from the prospective classifier. They are driven by relative-luminance and scale-aware affected-pixel gates in a dim workload; the corresponding absolute HDR errors remain small. N004 therefore does not reinterpret thresholds post hoc.

The single N005 transport question selected from the evidence is:

> Can state-change/confidence-driven adaptive tracing reduce the persistent low-radiance error tails observed under camera motion and dynamic geometry, without materially increasing the accepted complete-renderer GPU boundary or reopening the accepted A–M traversal/storage architecture?

Leak mitigation and multi-bounce are lower priority under N004 evidence: controlled leaking was not observed, and the tested Sponza state did not materially expose the higher-order diffuse gap.

Raw target artifacts remain under `out/research/`.
