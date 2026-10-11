# Current research status (2026-10-11)

**Status: empirical architecture and image-producing renderer demonstrated; general real-time GI superiority NOT established.** This is the sole cross-lane status/adoption synthesis. For the long research history see [archived 2026-10-02 status](archive/status-2026-10-02.md); for exact decision evidence use the linked lane results and [branch inventory](branch-inventory.md).

## Current incumbent — adoption versus experiments

| Subsystem | Current incumbent / classification | Evidence and boundary |
| --- | --- | --- |
| Work producer | **Adopted:** A001 GPU visibility-driven Split RC, natural append order; no global reorder | [Lane A](lanes/lane-a-split-rc/results/index.json), M0; Lane D does not supersede A001 |
| Primary traversal | **Adopted on measured Radeon 8060S:** HWRT/TLAS | [Lane B](lanes/lane-b-traversal/results/index.json), [I001](integration/results/index.json) |
| HWRT-free traversal | **Adopted fallback:** Segment DDA/hash + conservative quantized Micro BVH8 | Lane B B003; lower-tier alternative, not claimed universally equal to HWRT |
| Radiance storage | **Adopted baseline:** C001 per-probe open-addressed sparse hash | [Lane C](lanes/lane-c-storage-locality/results/index.json); page/clipmap variants conditional |
| Dynamic ownership | **Adopted incumbent:** immutable static, transform-only rigid, object-local deform UPDATE, object-local rebuild for topology changes | [Lane E](lanes/lane-e-dynamic-geometry/results/index.json), [timing revalidation](lanes/lane-e-timing-revalidation/results/) |
| Dynamic backend replacements | **Not promoted:** transient LBVH, clustered two-level variants | [Lane M](lanes/lane-m-topology-backend-crossover/results/); Lane E incumbent retained |
| Full Renderer | **Working research implementation:** N001–N004 and separate N005/N006 experimental variants | [Lane N](lanes/lane-n-end-to-end-renderer/results/index.json), [N005](lanes/n005-adaptive-tracing/), [N006](lanes/n006-interval-aware-allocation/) |
| N005 adaptive tracing | **REFINE / conditional:** no universal policy accepted | [N005 evidence](lanes/n005-adaptive-tracing/results/) |
| N006 interval-aware allocation | **STOP:** Q8 influence exists; +4-ray signed HDR quality lift not detectably proven; do not initiate P2/P3 | [N006 final result 045](lanes/n006-interval-aware-allocation/results/045-p1m3c-deforming-signed-quality-no-detectable-lift-stop.md) |

The current production-style Renderer uses **N-series pinned imports**, not whatever historical code happens to be stored in other lane folders. Presence of old experiment sources does not activate them.

## Evidence of improvement and limits

- **Lane E #22**, frozen Lane-L heavy recurring boundary: moving-rigid 0.330894x HWRT / 0.519178x software, and stable-deforming 0.331625x HWRT / 0.525108x software (candidate/control complete-GPU ratios); the required >=20% improvements and memory guards passed. Exact evidence remains in the revalidation lane.
- **Lane M #25:** 6,144 GPU-timing rows in 192 fresh processes on frozen primary/software tracks; transient LBVH and clustered two-level approaches did not qualify. Lane E object-local rebuild remains incumbent for topology changes/high churn.
- **N003:** reported **~2.35–3.11x Renderer speedup** against the particular vanilla Split RC control cases, accompanied by **~24–27% extra GPU memory**. These figures are not general quality-equivalent, cross-scene, or cross-GPU superiority claims.
- **N004:** motion-related image-quality weaknesses were detected. Performance success does not close image quality.
- **N005:** adaptive tracing showed conditional promise, but a single accepted scheduling rule was **not** established.
- **N006:** [Q8 replicate mechanism](lanes/n006-interval-aware-allocation/results/041-p1m3a-q8-gpu-replicated-image-mechanism.md) showed reproducible image influence; [moving-rigid reference](lanes/n006-interval-aware-allocation/results/043-p1m3b-moving-rigid-identical-reference-invalid.md) was ineligible, and [final deforming signed-quality comparison](lanes/n006-interval-aware-allocation/results/045-p1m3c-deforming-signed-quality-no-detectable-lift-stop.md) found **no detectable improvement** exceeding independent-reference noise. Extra-ray policy is not adopted; N006 P1/P2/P3 stopped.

## Measurement capability

- Performance primary: **GPU timestamps**. CPU wall: diagnostic/provenance/health, not a second equal acceptance axis.
- **Lane K:** 5% detectable effect for its calibration workload. **Lane L:** 20% detectable effect for the complete recurring heavy boundary. Transferability is **not assumed**.
- Require frozen exact semantics, process-replicated timing, all-sample retention, persistent + true-peak GPU memory, correctness and exact measured boundary. [Detailed protocol](protocol.md).
- **Reference quality caveat:** previously accepted N001 camera/moving-rigid CPU references included all-black cases, and N006 deforming references have <1% positive pixels; a zero full-frame p99 does **not** establish adequate HDR convergence. [N007 #4](https://github.com/owoDra/real-time-gi-lab/issues/4) remains OPEN, independent and not part of this integration.

N007 P0 CPU source audit and synthetic PFM diagnostics are in progress on `research-n007-reference-validity` ([protocol](lanes/n007-reference-validity/experiments/001-reference-eligibility-protocol.md), [results](lanes/n007-reference-validity/results/index.json)). Real-frame convergence and physical validity remain **unverified**. This has no effect on N006 P1 NO GO or the historical N001/N003 result classifications.

## Unresolved strategic questions

1. **Can independent HDR image quality be evaluated credibly across real dynamic scenes?** N007 first, before claiming quality gain or optimizing new adaptive rules.
2. **Does this architecture actually beat fair existing GI baselines** under equivalent quality/cost across multiple scenes and hardware classes? Not yet established.
3. **Which structural light-transport/storage/reuse changes** can change the total quality/performance/memory frontier beyond a locally optimized Split RC pipeline? Evaluate only after reliable baselines and bottlenecks.

See [roadmap](roadmap.md) for gates. Old status, stale next-step commands and branch-local research attempts are historical data, not the current agenda.
