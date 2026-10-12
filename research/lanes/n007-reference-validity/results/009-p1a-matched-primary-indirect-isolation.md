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

**This new GPU-probe replay has not been executed on-device.** **Update: this statement applied to the initial result publication only; the following GPU run has now executed the replay.** A positive shadow-blocked probe candidate would support this causal mechanism in this frame only if GPU ray-hit matches, fixed quantization agrees and independent visibility is valid. It still would not establish physically correct full-scene GI, original M3b cause or statistical eligibility. Preregistered light-motion and camera controls, controlled known occlusion, and full 512–8192 × four-seed two-consecutive-level ladder remain pending.


## GPU-host actual probe shadow replay (2026-10-12 JST)

User-provided derived JSON from a subsequent N007 software/moving-rigid/target/512-SPP capture, same registered run class (raw evidence remains private, artifact identity not independently checked by assistant):

| Probe item count | Observed |
|---|---:|
| Total GPU-produced work items | **134,816** |
| Secondary traversal hits | **32,276** |
| Positive fixed-point probe contributions | **18,649** |
| GPU-positive probe hits with independently shadow-blocked light | **18,363 / 18,649 (98.4664%)** |
| GPU-positive probe hits with unobstructed light | **286 / 18,649 (1.5336%)** |
| GPU/CPU secondary traversal mismatches (all/positive) | **0 / 0** |
| Reconstructed GPU fixed contribution mismatches | **0** |
| Invalid GPU contribution output IDs / hit flags | **0 / 0** |
| Positive unshadowed CPU predictions absent from GPU output | **0** |

The same capture again has first-hit pixel mask, ID, t and normal comparison all matching (**15,173 hit pixels**); GPU software primary triangles are exactly matched (**262,241 / 262,241**). CPU direct/indirect/total positive-pixel count is **0/0/0**; GPU is **0/9,247/9,247**. Primary direct delta=0, GPU channel reconstruction=true, indirect max abs delta=**0.00012207217514514923**. Only remaining recorded diagnostic blocker is independent GPU camera UBO and secondary upload/state provenance.

**Narrow empirically supported conclusion:** in this current run, the active GPU physical-radiance stage generates 18,363 strictly positive Lambert fixed-point contributions at matched secondary hit surfaces which the independently replayed CPU scene BVH finds to be in shadow from the light. This directly validates the previously hypothesized *missing secondary shadow visibility* behavior of `n001_physical_radiance.comp.glsl` under matched producer rays. Merely counting occluded probes does **not** prove that all 9,247 resulting positive image pixels owe their positive value to those probes, because 286 light-unobstructed positive contributions also exist, and the storage key/aggregation/lookup path has not been causally ablated. Probe direction sampling differs fundamentally from the CPU cosine path tracer.

This is **not** an assertion that every shadowed sample violates a complete physical light-transport oracle or that original archived N006 M3b frames were identical. Physical validity and statistical reference eligibility remain undetermined. Do **not** retrofit original N006 P1 NO GO or claim historical causal proof.

### Next bounded falsification test

Reconstruct the **actual GPU probe-key accumulation and per-pixel lookup** on CPU from captured work, contributions and verified GPU primary hits, then compare reconstruction against the original GPU indirect image. Perform an independent **occluded-contribution-zeroed counterfactual** using the same key/group/lookup paths without altering historical shader or reselecting frames. Only call it an image-level explanation if baseline reconstruction matches and the counterfactual change is demonstrably attributable to identified shadow-blocked contributions. Independently test known lit and occluded geometry (including positive light-motion control), GPU camera UBO and probe acceleration upload state; then run the preregistered SPP × four-seed ladder. No result of these subsequent tests has been measured yet.

### N007-only CPU probe-to-pixel replay implemented (not yet executed on real captures)

`scripts/research/n007_reference_validity/replay_probe_image.py` reconstructs the actual unchanged-GPU contribution merge (per `output_id` integer sum and count), integer rounded per-output mean, persistent key-wise sample mean and primary-pixel cascade lookup **from the captured work/contributions/hits and frame state**. It first compares reconstructed image signal support and max error against the *original captured GPU indirect PFM* and fails closed if that baseline diverges. An optional per-work independently computed shadow-visibility label input supports counterfactual zeroing of previously identified shadow-blocked contributions through exactly the same accumulation/lookup chain, but flags were **not stored with the already recorded GPU-host capture**; no image-level shadow-filtered result is being claimed. The script and synthetic controlled-image tests are new CPU source code; **not run on the user's private artifacts, not GPU-dependent, and not formally validated for actual reconstructed PFM equivalence**.

A per-pixel counterfactual remains pending until those CPU replay prerequisites and an independent per-work visibility mask are available. Do not equate 98.4664% of positive *work items* with 98.4664% of final *pixel energy* or 98.4664% of positive pixels.

