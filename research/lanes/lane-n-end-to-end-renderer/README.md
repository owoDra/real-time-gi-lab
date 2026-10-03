# Lane N — end-to-end renderer integration

Issue: #26  
Canonical branch: `research-lane-n-end-to-end-renderer`  
Architecture base: `research@a75cf7857761cfbc783c9f1f847dc1380359481e`

Status: **N001 complete; N002 complete; N003 preflight complete; N003 proper complete; N004 next**.

Lane N is the image-producing end-to-end lane. It preserves the accepted A–M architecture from `research/status.md` and establishes trustworthy HDR/reference/timing/memory/provenance boundaries before any new GI feature or performance claim.

## N001

N001 renderer/reference bring-up is complete. See `experiments/001-n001-config.json`, `experiments/001-n001-source-provenance.json`, and `results/001-renderer-reference-bringup.md`.

## N002

N002 current-architecture baseline is complete. Final evidence commit: `0188c7f7b4b43e5d887cd753d74a69e11a2ea764`.

The six-scenario artifact passed correctness, provenance, reference convergence, HDR campaign-signal, timing-accounting, and memory gates. Topology/high-churn replaced 398/796 dynamic-owner primitive identities, executed exactly one object-local backend rebuild, recorded 252,928 bytes of old/new overlap, and retained static ownership outside the rebuild path.

## N003 preflight/calibration

Issue #31 is complete. See `results/003-preflight-calibration.md`.

Retained calibration lineage:

- v1: 145% global threshold, timing-unsuitable;
- v2: 110%, timing-unsuitable; quality interpretation accepted;
- v3: 207.5%, timing-unsuitable;
- v4: 98.5%, timing-unsuitable;
- v5: withdrawn before target execution because forcing the target GPU performance profile can trigger host safety shutdown;
- v6: all 40 replicated-median micro-pairs retained, zero false formal claims, worst p95 block effect 18.4%, but moving-rigid drove the global threshold to 28.5%.

The moving-rigid workload diagnostic proved exact source/target integer workload invariance across A/B and all eight blocks. Its remaining timing variation is measurement/execution-state limited rather than workload-count drift.

**Lane N must not change GPU power/performance profiles.** The host GPU policy remains unchanged.

Frozen N003 timing thresholds:

- static: 7.0%;
- camera-motion: 1.5%;
- light-motion: 5.0%;
- moving-rigid: timing-inconclusive, no formal performance win/loss claim;
- stable-topology-deforming: 2.5%;
- topology-changing-high-churn: 1.5%.

## N003 proper

Issue #38 is complete. See `experiments/003-n003-comparison.md` and `results/003-current-vs-vanilla.md`.

The fair same-boundary comparison used the accepted N002 `LaneEFinalHwrt` path as current and the historical Integration-13 global binary software-BVH Split RC path as vanilla. A001 producer/cascade/probe/ray semantics, sparse radiance storage, renderer/reference semantics and complete timing boundaries were shared.

Formal complete-renderer median vanilla/current ratios:

- static: **3.023x** current faster;
- camera-motion: **2.756x** current faster;
- light-motion: **3.108x** current faster;
- stable-topology-deforming: **2.506x** current faster;
- topology-changing/high-churn: **2.354x** current faster.

Every formal claim had 8/8 outer blocks in the same direction and exceeded its prospectively frozen threshold. Moving-rigid produced a descriptive ~1.787x ratio favoring current but remains measurement-limited and has no formal timing direction.

Quality/reference evidence showed **no material quality difference in any of the six scenarios**: current and vanilla had exactly equal RGB RMS error, p99 absolute luminance error and scale-aware affected-pixel fraction for each scenario under converged 512-spp references.

The main trade-off is device lifetime memory:

- ordinary scenarios: current `363,297,488` B vs vanilla `287,091,936` B, about **+26.5%**;
- topology/high-churn: current `363,424,016` B vs vanilla `293,392,656` B, about **+23.9%**.

Non-formal diagnostics show the opposite trend for renderer-owned host mirrors and expose the vanilla dynamic bottleneck. Global software-BVH rebuild makes dynamic CPU wall roughly 105–110 ms in vanilla versus about 1.6–3.8 ms for current across the three dynamic classes. These CPU values are explanatory only; GPU timestamps remain the formal performance axis.

N003 therefore confirms that the A–M support architecture's component-level wins survive the integrated renderer boundary against the mandatory vanilla Split RC baseline, while explicitly retaining the higher device-memory cost.

## N004 next

N004 must build the weakness atlas required by #26 without first changing the transport solution. Measure independently:

- thin geometry / light leaking;
- camera motion and disocclusion behavior;
- changing illumination response;
- rigid / deforming / topology-changing dynamic behavior;
- spatial scale and world-shape stress;
- explicit multi-bounce and glossy/specular capability gaps.

The output must classify each regime as solved/not observed, present but bounded, material blocker, capability not implemented, or measurement-limited. N005 then selects exactly one evidence-backed next transport research question.

Raw target artifacts remain under `out/research/`. Continue in parent Issue #26.
