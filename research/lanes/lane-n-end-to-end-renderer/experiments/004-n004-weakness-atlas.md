# N004 — Split RC weakness atlas

Issue: #39  
Parent: #26  
Status: **protocol v2 frozen; v4 world workload validated; ready for one accepted target campaign**

## Goal

Measure the accepted current Lane-N renderer without adding mitigation first. N004 classifies the suspected Split Radiance Cascades weaknesses into evidence-backed regimes and leaves one N005 research question after target data.

No aggregate weakness score is permitted.

## Protocol lineage

N004 v1 is retained as failed pre-target lineage. Its first formal attempt stopped in `world-sparse` because the v3 synthetic world generator placed regular-grid box edges exactly on a canonical diagonal RC ray. The strict CPU reference reported a hit where hardware triangle traversal reported a miss, while radiance remained numerically unchanged. This is a workload degeneracy, not accepted target evidence.

Protocol v2 changes only the synthetic world placement:

- scene factory is frozen at `phos-n004-scene-factory-v4`;
- world boxes receive deterministic X/Z jitter (`0.037` / `0.041` amplitude) to remove exact lattice/edge alignment;
- triangle counts, sparse/dense/large-horizontal/vertical-tall classes and the 36-triangle idle dynamic control mesh remain unchanged;
- the six weakness families, quality thresholds, reference rules, timing interpretation, sample-exclusion rule and completed-campaign rerun budget remain unchanged.

After the v4 correction, `world-sparse` passed strict source validation. One subsequent probe produced 10 target-only historical-validator hit mismatches, but the anomaly did not reproduce. A dedicated three-way diagnostic compares HWRT candidate, CPU brute-force reference and GPU software-BVH validator reference without changing the historical validator. Five fresh-process repeats produced 10/10 source/target cross-checks with `cpu_vs_candidate=0`, `gpu_validator_vs_candidate=0`, and `cpu_vs_gpu_validator=0`. The anomalous probe is retained as validation evidence and is not target data.

The accepted target campaign is therefore protocol v2 and still has completed-campaign rerun budget zero.

## Frozen renderer

The measured renderer remains the accepted N002/N003 `LaneEFinalHwrt` architecture:

- A001 visibility producer and natural append order;
- object-local HWRT/TLAS traversal;
- rigid transform update;
- stable-topology object-local UPDATE;
- topology-changing object-local rebuild;
- accepted sparse radiance storage;
- unchanged gather / merge / resolve;
- constant-white Lambertian diffuse renderer semantics.

No leak suppression, temporal repair, confidence heuristic, adaptive sampling, denoising, extra bounce transport, or glossy/specular transport is added by N004.

GPU power/performance profile changes remain forbidden.

## N004-only camera/light control

Historical A001/N001-N003 targets still compile the accepted A001 runtime source unchanged. N004 links a dedicated wrapper translation unit around that exact source. The wrapper exposes a prospective motion fraction while preserving fraction `1.0` as the historical target state.

Camera gradual motion linearly interpolates the camera eye from the historical static eye to the historical `CameraMotion` eye and rebuilds the look-at basis toward the unchanged scene center. Light gradual motion linearly interpolates the light position from the historical static light to the historical `LightMotion` target.

No historical target uses this wrapper.

## Synthetic scene ownership discipline

Synthetic leak/world glTFs are generated deterministically at campaign time. Mesh 0 is always a small 36-triangle control object so Lane-E-final's stable-regime idle dynamic partition does not accidentally absorb the primary synthetic workload. Main workload geometry remains static ownership.

The generated scene manifest and glTF/bin files are retained in the raw artifact. For protocol v2, the manifest and glTF asset generator must identify `phos-n004-scene-factory-v4`.

## Families

### A. Thin geometry / light leaking

Six prospective controlled cases:

- `leak-thin`: 0.02 world-unit slab;
- `leak-medium`: 0.10 slab;
- `leak-thick`: 0.40 slab;
- `leak-grazing`: 0.10 slab rotated 68 degrees around Y;
- `leak-one-sided`: zero-thickness quad occluder;
- `leak-enclosed`: 0.10 slab plus dark-side rear/side/roof enclosure.

Primary leak evidence is restricted to pixels where reference luminance is <=0.001. False irradiance is a positive output-reference luminance delta >=0.001. Retain fraction, mean, p99, maximum and screen-space bounding box plus wall-thickness/probe-spacing ratio.

Classification:

- not observed: false fraction <0.005 AND false p99 <0.001;
- material blocker: false fraction >=0.05 AND false p99 >=0.01;
- otherwise present-but-bounded.

### B. Camera / disocclusion

Sponza, 32 source warmups, two separate 8-frame cases:

- abrupt reveal: `[1,1,1,1,1,1,1,1]`;
- gradual motion: `[0.125,0.25,0.375,0.5,0.625,0.75,0.875,1.0]`.

Gradual frames receive separately aligned converged references. Abrupt repeated target state reuses one aligned reference. Retain first-visible error, per-frame error, convergence frame, temporal RGB RMS diagnostic, active work/owners and storage churn.

### C. Changing illumination

Same discipline as camera, with separate:

- step change;
- gradual change using the same 1/8 increments.

Retain signed mean luminance error for over/undershoot diagnosis in addition to generic radiometric metrics.

### D. Dynamic geometry

Four target frames for each class:

- moving-rigid;
- stable-topology-deforming;
- topology-changing-high-churn.

Record aligned image error, complete GPU timing, update timing, workload/storage churn and device memory. Moving-rigid timing remains measurement-limited from N003 and cannot produce a formal timing conclusion.

### E. World shape

Deterministic synthetic layouts:

- sparse;
- dense;
- large-horizontal;
- vertical-tall.

Protocol v2 keeps these classes but removes exact X/Z lattice-edge alignment with the frozen deterministic jitter described above.

Record quality, visible owners/work items, storage churn, complete GPU time and memory independently. Correctness/capacity failure is retained as a `material-blocker`; it is not silently discarded.

### F. Capability boundary

On the same Sponza state compare converged 1-bounce and 8-bounce diffuse references to quantify whether higher-order diffuse transport is materially exposed. The frozen current renderer does not claim the missing higher-order transport, so the capability classification remains `capability-not-implemented` even when the reference delta is small in this one scene.

Glossy/specular indirect transport is also `capability-not-implemented`: the frozen renderer/reference comparison semantics are Lambertian diffuse and no glossy/specular indirect path exists.

## Generic image classification

Primary metrics against aligned reference:

- RGB RMS;
- p99 relative luminance error;
- scale-aware affected-pixel fraction (`abs_error >= 0.05 * max(abs(reference_luminance), 0.0001)`).

`not-observed-under-tested-regime` requires all three:

- RGB RMS <0.001;
- p99 relative luminance <0.05;
- affected fraction <0.01.

`material-blocker` requires at least two of:

- RGB RMS >=0.01;
- p99 relative luminance >=0.25;
- affected fraction >=0.10.

Everything between those gates is `present-but-bounded` unless a family-specific capability/measurement rule applies.

These thresholds were frozen before any accepted N004 target data and are unchanged in v2.

## Reference and artifact discipline

Reference uses 512–8192 spp and at most 8 diffuse bounces with the accepted replicate convergence limits. A varying camera/light state gets a separate aligned reference for each frame; repeated identical target state may reuse one reference.

Raw artifacts retain:

- generated scenes;
- renderer/reference PFM frames;
- per-case evidence JSON and logs;
- full summary and provenance;
- all timing/stats/memory values.

No sample exclusion is allowed. Completed accepted campaign rerun budget is zero. Probe runs are validation-only and must use a separate non-campaign artifact path. Failed v1 and anomalous validation artifacts remain part of the research lineage and must not be deleted or reclassified as target evidence.
