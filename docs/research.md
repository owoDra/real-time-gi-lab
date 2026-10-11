# Research charter — phos-gi-lab

## Final objective

Establish a novel, demonstrably competitive **real-time global illumination light-transport architecture** that, across practical workloads, surpasses representative alternatives on a combination of **image fidelity, end-to-end performance, GPU memory efficiency, dynamic geometry/light/camera response, and deployability**.

A win means defensible **same-quality GPU-time and/or memory superiority**, or **same-cost image-quality and/or supported-feature superiority**. A partial tradeoff must be reported with its full costs. A faster but materially degraded renderer is not a GI architecture win.

**Split Radiance Cascades, StrataBrick, sparse hash, HWRT, software BVH, temporal reuse and path guiding are replaceable techniques**, not the research objective. Previously accepted components remain the incumbent only while measurements justify them.

## Boundaries and fairness

- Validate the actual **image-producing Renderer**, including allocation, tracing, invalidation, synchronization, dynamic updates and compositing, not isolated kernel time alone.
- Require credible independent physical HDR references, meaningful signal and demonstrated convergence. A sparse mostly-black reference is not automatically eligible; [N007 #43](https://github.com/owoDra/phos-gi-lab/issues/43) is the independent investigation.
- Compare to representative families, as applicable: vanilla/Split RC, DDGI/probe GI, sparse cache or SHaRC-like GI, and ReSTIR/path-tracing-based approaches. Match scene, hardware, quality target, dynamic coverage and cost boundary; document deviations.
- Test static, moving-camera, changing-light, moving-rigid, stable-deforming, topology-changing and high-churn scenes where supported. Extend beyond Sponza and beyond one GPU before general claims.
- Always report quality, GPU time, persistent and **true-peak** GPU memory, artifact provenance and limitations together.
- HWRT-capable and software-only devices may have distinct winners; do not hide the software fallback cost.
- A measured negative, rejected or inconclusive study remains part of the research record. Do not optimize thresholds after results.
- Prefer resolving architectural bottlenecks over indefinite micro-optimizations. Every new direction needs a falsifiable hypothesis, predeclared gate and stopping criterion.

## Successful end state

The project has succeeded when reproducible Renderer demonstrations across representative scenes and multiple GPU classes substantiate competitive advantage against fair external baselines, with valid image references, sufficiently stable dynamic/lighting behavior and honest full-system memory/performance accounting. One AMD GPU, a single synthetic workload or a large isolated speedup is **insufficient**.

The original GPU-locality/page scheduling hypothesis is retained as history in [the earlier charter](archive/research-charter-2026-09.md), not adopted as an unconditional premise.
