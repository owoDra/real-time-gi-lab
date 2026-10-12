# N007 P1-A-009 — matched moving-rigid primary and isolated indirect-only signal

**Date:** 2026-10-12 JST
**Issue:** #4; preregistered P1-A component isolation
**Classification:** diagnostic-only / real GPU-host execution (user-provided derived JSON)
**Scenario:** Sponza, moving-rigid, target state, software backend, 320×180, CPU 512 SPP × 4 fixed seeds.
**Source SHA, asset SHA and raw PFM SHA:** present in user's private local manifest but NOT supplied in this turn; **not independently inspected** by assistant. No private evidence uploaded to repository.

## Observed user-provided validation

- First-hit identity: `primary_match=true`, CPU and GPU hit pixels **15,173 each**, zero mask, primitive/material/instance, distance and normal mismatches.
- Exact GPU-primary triangle device buffer against CPU post-motion snapshot: **262,241 / 262,241 triangles byte-identical**, mismatched=0; this verifies the compared GPU software-primary triangle buffer, **not** the GPU camera UBO or separate software probe acceleration buffers.
- Signal support: CPU direct **0**, CPU indirect **0**, CPU total **0** positive pixels. GPU direct **0**, GPU indirect **9,247**, GPU total **9,247** positive pixels.
- Direct max absolute discrepancy = **0.0**; indirect max absolute discrepancy = **0.00012207217514514923**; GPU direct+indirect reconstruction **PASS**.
- Remaining evidence blocker: `gpu_camera_ubo_and_secondary_state_not_independently_attested`. Historical causation and physical correctness flags remain false.

## Interpretation and limit

The observed current matched-primary GPU output is **entirely probe-indirect where nonzero**, not direct illumination, reconstruction error, or primary geometry disagreement. This is a **localized cause in the new diagnostic capture**, NOT proof that these are the exact original archived N006 M3b pixels (those archives have different derived positive-pixel counts, and no full original frame/state identity has been independently matched).

Source contract supports a specific *candidate transport mismatch*: the original GPU `n001_physical_radiance.comp.glsl::point_light_lambert` generates positive probe-hit light without a shadow-to-light visibility query; the CPU reference `n001_reference.cpp::direct_lambert` traces such visibility rays at every path hit. Thus GPU-only probe energy may be caused by occluded secondary hit surfaces, but this still needs an independent, ray-level matched GPU-probe replay. A zero CPU reference is not automatically an unbiased physical oracle. Whole-frame p99=0 is never acceptable evidence of convergence for a black reference.

## Prospective next test — N007-only read-only GPU-probe replay

An opt-in diagnostic now downloads the actual GPU producer work stream (64-byte items), secondary traversal hits (32-byte), and fixed quantized radiance contributions (8-byte). The N007 CPU replay reconstructs identical producer rays, checks first encountered secondary hits versus a separate CPU BVH, predicts the original *unshadowed* Lambert value and tests shadow-to-light occlusion in matched world-space geometry. It records matched-hit / mismatch counts, fixed-value reconstruction mismatches, occluded-positive counts and clear-positive controls. The manifest checks payload length, SHA and self-consistency. Original N001–N006 shaders and acceptances remain untouched.

**This new GPU-probe replay has not been executed on-device.** A positive shadow-blocked probe candidate would support this causal mechanism in this frame only if GPU ray-hit matches, fixed quantization agrees and independent visibility is valid. It still would not establish physically correct full-scene GI, original M3b cause or statistical eligibility. Preregistered light-motion and camera controls, controlled known occlusion, and full 512–8192 × four-seed two-consecutive-level ladder remain pending.

