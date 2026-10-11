# Program-level architecture decisions — 2026-10-11

These are **synthesis decisions**, not fresh GPU measurements. Each decision must trace to historical frozen lane evidence. Consult [status](../status.md) for the short current picture and [inventory](../branch-inventory.md) for branch HEAD/provenance.

| Topic | Classification | Reason and authoritative evidence |
| --- | --- | --- |
| A001 producer/natural append | **Adopted incumbent** | Representative producer stream and existing local coherence; [A001](../lanes/lane-a-split-rc/results/index.json), M0 |
| HWRT/TLAS primary | **Adopted on measured GPU** | [B002](../lanes/lane-b-traversal/results/index.json) and [I001](../integration/results/index.json), not claimed across all devices |
| Segment DDA/hash + quantized Micro BVH8 | **Adopted software fallback** | B003 selected the improved fallback; its full target was **not** met |
| Per-probe sparse hash | **Adopted current storage** | [C001](../lanes/lane-c-storage-locality/results/index.json); virtual/clipmap storage not generally promoted |
| Lane D producer/depth reuse/overflow | **Conditional / not A001 replacement** | [Lane D](../lanes/lane-d-producer-optimization/); depth reuse conditional, overflow policy retained as bounded evidence |
| Lane E geometry ownership/update | **Adopted incumbent** | [Lane E](../lanes/lane-e-dynamic-geometry/), [heavy timing revalidation](../lanes/lane-e-timing-revalidation/) |
| Lane F / G / H alternatives | **Not promoted / measurement-limited** | Negative or incomplete performance/memory gates retained, not resurrected into Renderer |
| Lane I dual-axis calibration | **Rejected methodology under frozen gate** | GPU-only mechanism evidence does not erase CPU-wall gate failure |
| Lane J original/formal alternate backend | **Not promoted / historical** | Distinct original and formal-crossover refs preserved; see inventory and [Lane J](../lanes/lane-j-topology-backend-alternatives/) |
| Lane K GPU-primary | **Adopted, calibration-workload scope (5%)** | Not portable without calibration to other boundaries |
| Lane L heavy-boundary | **Adopted, heavy-boundary scope (20%)** | Used prospectively for Lane E #22 and Lane M #25 |
| Lane M topology backend | **Retain Lane E** | Measured LBVH/clustered alternatives failed promotion under frozen 20% + memory gate |
| N003 whole Renderer | **Bounded performance improvement; not general GI win** | ~2.35–3.11x in tested cases with ~24–27% extra GPU memory; quality and portability remain open |
| N004 motion quality | **Detected weakness** | Preserve negative-quality observations |
| N005 adaptive tracing | **REFINE only** | No universally accepted single scheduling rule |
| N006 Q8/interval-aware allocation | **Mechanism evidence only; P1/P2/P3 STOP** | [Result 045](../lanes/n006-interval-aware-allocation/results/045-p1m3c-deforming-signed-quality-no-detectable-lift-stop.md) shows no detectable signed HDR lift beyond reference noise |
| N007 HDR reference validity | **OPEN, independent issue** | [#43](https://github.com/owoDra/phos-gi-lab/issues/43); no retrospective N006 rerun/threshold change |

*Promoted* refers to a studied technique/design decision, **not** automatic activation of historical code. Unmerged old Lane A/B shader targets may clash with N-series names; leave those targets dormant. Do not mutate original accepted test result Markdown, indexes or hashes as part of consolidation.
