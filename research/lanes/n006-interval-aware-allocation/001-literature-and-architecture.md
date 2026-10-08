# N006 P0 — literature and existing-pipeline mapping

Status: **design review, not accepted experimental evidence** (2026-10-08). Issue #42.

## Literature: known / reusable / incompatible / unresolved

| Source | Established prior work | Reusable insight | RC mismatch / genuinely testable question |
| --- | --- | --- | --- |
| [Radiance Cascades theory, Osborne & Sannikov 2024](https://arxiv.org/abs/2408.14425) | Spatial/angular scaling, radiance-interval composition | Respect distance/cascade-specific resolution | Nonuniform new directions can violate original coverage assumptions; prove correct normalization |
| [Split RC, Freeman & Sannikov 2026](https://arxiv.org/abs/2607.20384) | Sparse world probes and ray splitting; single-frame or temporal accumulation | Reuse sparse representation / merge and independent single frame | Does not supply a demonstrated *Phos-specific* pre-trace marginal-value predictor |
| [Holographic RC, Freeman et al. 2025](https://arxiv.org/abs/2505.02041) | Single-shot cascaded transport in 2D | Preserve single-frame design | Different 2D producer / storage regime |
| [IS-DDGI, Liu et al. 2023](https://doi.org/10.1145/3585500) | GPU importance-based ray allocation already improves DDGI | Cheap ranking, equal-resource baselines, GPU scheduling economics | DDGI individual probe updates differ from visible-owner -> cascade -> Split RC interval work |
| [Adaptive Dynamic GI, Datta et al. 2023](https://arxiv.org/abs/2301.05125) | State/radiosity-change adaptive probing already explored | Geometry/light change features | Reliance on temporal irradiance/visibility cache must not be copied as RC transport |
| [RTXGI-DDGI classification, variability and update scheduling](https://github.com/NVIDIAGameWorks/RTXGI-DDGI/blob/main/docs/DDGIVolume.md) and [production scaling](https://research.nvidia.com/publication/2021-05_scaling-probe-based-real-time-dynamic-global-illumination-production) | Probe inactivity, variation metrics, independent lower-frequency update scheduling | Validity/change/variance tests | Not an interval-level *marginal extra-ray effect* predictor in Phos |
| [ReSTIR GI, Ouyang et al. 2021](https://doi.org/10.1111/cgf.14378), [DDGI resampling, Majercik et al. 2021](https://arxiv.org/abs/2108.05263) | Spatiotemporal path / reservoir reuse | Understand disocclusion and confidence invalidation | Do **not** adopt per-pixel reservoirs, iterative temporal convergence or change the RC field's role |

Conclusions: (a) adaptive ray budgets and scene-change detection are **known**, not Phos novelty; (b) cascade/interval-aware realized gain prediction with scheduler overhead and Split RC correctness remains a **concrete Phos research question**, not a general claim of global novelty; (c) no reason to investigate a new reservoir-based architecture in this lane.

## Verified source-level mapping

Source: `src/research/n005_adaptive_tracing/n005_runtime.cpp`, `shaders/research/n005_adaptive_tracing/n005_extra_producer.comp.glsl`, `src/research/lane_n_end_to_end_renderer/imported/lane_a_split_rc/stream_schema.hpp`.

```text
visibility / depth -> visible owner selection
     -> frozen producer: LaneAWorkItemV1
          (probe xyz, cascade, ray_index, output_id, tile_id,
           interval_min/max, direction, surface_id)
     -> [N005 append suffix: selected OWNER -> every cascade -> extra directions]
     -> ray prepare -> traversal -> radiance -> merge
     -> sparse storage update -> invalidation -> resolve
     -> final image composite
```

N005's extra producer ranks **owner regions** using a depth-discontinuity gate, then appends 4 new deterministic directions to **all 4 cascades** per selected owner. The suffix is before ray preparation and retains the original work-item identity (except direction and ray index). It does **not** individually schedule cascade ranges or fine-grained angular radiance samples.

**Terminology correction:** work items expose one `interval_min/max` pair for a cascade's distance range and a direction. A freely independent `probe × cascade × angular interval` persisted object does not exist as a documented runtime entity. P0 must establish the actual controllable grain, probably **owner × cascade**, before using the phrase "per interval scheduler" literally.

The frozen runtime executes storage update/invalidation/resolve every frame. Blindly skipping an existing interval requires retained-field semantics, matching keys, freshness/validity and a single-frame fallback not established by N005. Therefore **no update skipping** is authorized.

## P0 questions (source audit, before implementation)

1. Does owner × cascade variable ray count maintain `output_id`, `ray_index`, sparse-key accumulation and merge/normalization integrity? Check whether per-cascade sample count is assumed globally fixed; ensure angular coverage stays unbiased.
2. Can a pre-trace eligibility/ranking signal be attached without readback or extra full-frame passes? Quantify exact GPU reads, memory, prefix scan/compaction and command dispatch.
3. Does an individual added ray influence multiple final pixels/cascades? If so, simple local RGB-error correlation cannot serve as a causal ground truth.
4. Can counterfactual batch interventions be reproduced with fixed base rays, reference, scene state and direction seeds? Report memory/time feasibility. Distinguish output-local proxies from measured global RGB RMS gain.
5. Are proposed validity, age, neighboring interval radiance or variance signals actually available **before** extra tracing? If obtained only after tracing or from temporal history, they are **ineligible until separate cost/state contract**.
6. Are the N005 fixed owner/frame gate and N005 extra directions valid under modified per-cascade allocation? Preserve deterministic comparison and exact actual extra rays.

## Signal triage, not a chosen policy

- **Cheap first:** cascade index / known interval distance scale; existing normalized depth-discontinuity; observable camera/owner change. Evaluate each independently before a combined rule.
- **Conditional:** valid pre-trace field/radiance disagreement if source, freshness and cost can be shown.
- **Deferred:** new per-interval age/confidence buffers, per-sample variance, neighboring interval cache, dynamic-class tables, learned policies. N005 P1 already found owner/depth temporal change nearly blind to dynamic blockers.
- Do **not** assume near=visibility, far=age is a correct schedule; measure positive *counterfactual marginal value* by cascade and regime.

## P0 decision gate

Choose **GO at owner×cascade**, **REFINE granularity**, or **STOP**. Require verified producer/merge semantics, cheap usable pre-trace signals and viable bounded causal intervention. No new confidence state until those gates hold. The [experiment plan](./experiments/001-p0-p1-predictive-value.md) specifies the following steps.
