# N007 final decision — bounded NO GO for independent HDR quality reference

**Date:** 2026-10-12 JST  
**Issue:** [#4](https://github.com/owoDra/real-time-gi-lab/issues/4)  
**Decision:** **CLOSE N007 as a bounded negative study / reference-quality NO GO**, not as a reference algorithm validated across all classes.  
**Historical N006 P1:** unchanged **NO GO**; no N006 P2/P3 authorization, no historical result revision.

## Frozen stopping authority

Issue #4, P1: "**Stop if no demonstrably reliable, nontrivial reference across required dynamic classes without violating resource bounds. Clearly distinguish convergence from correctness.**" The associated preregistered N007 protocol exhausts **512, 1024, 2048, 4096, 8192 SPP × four fixed seeds** at each tested cell, and demands **two consecutive statistically eligible levels** to qualify. Important moving-rigid target-state is required; its reference failed at the full 8192-SPP cap. Since an eligible independent reference across all required classes is already ruled out by that single required failure, further GPU work cannot reverse **this universal-across-classes GO/NO GO decision** without replacing or modifying the reference/protocol, which this N007 study prohibits. We therefore stop by the **pre-authorized bounded-failure rule**, not by silently assuming the unmeasured cells passed or failed.

## Actual evidence and outcome

| Validation axis | Actual result | Admissible inference |
|---|---|---|
| Historical P0 HDR archive | Inspected **338 / 338** archived named GPU/CPU image pairs; **96** black-reference/GPU-positive entries collapse to **4** distinct SHA pair signatures | Repeated black/sparse-reference behavior documented; not source-state or physical correctness proof |
| GPU moving-rigid primary capture | **15,173 CPU/GPU matched first-hit pixels**, zero primary mismatches | Matched first-hit semantics in one current moving-rigid frame |
| GPU primary geometry device readback | **262,241 / 262,241** std430 GPU triangles byte-identical with the post-motion CPU world-geometry snapshot | Verifies this primary-triangle device buffer, not every GPU shader state buffer |
| GPU secondary work replay | **134,816** work items; **18,649** positive; **18,363** shadow-blocked; **286** not blocked; zero traversal/fixed-value mismatch | Actual GPU probe Lambert stage emits nonzero energy at shadowed secondary hit surfaces |
| GPU indirect image pixel counterfactual | Baseline original GPU indirect **reconstructed successfully**. Deleting *only CPU-BVH shadow-blocked positive probe contributions* changed **9,247 positive pixels to 0**; total image sum **0.2673380636301213 → 0.0** | **Image-level model-specific causal ablation of the entire observed GPU indirect signal** in this frame. No claim that archived N006 frames are identical |
| CPU moving-rigid 4-seed reference signal | Union-active fraction **0.0 at all 512/1024/2048/4096/8192 SPP levels** | **Statistical-screen-fail** for this required important regime under frozen acceptance criteria; not a physics proof |
| Independent physically correct reference | **NOT VERIFIED** | No defensible absolute GI quality ranking may use this black reference |

## Final classification by scope

- **N007 reference suitability across required dynamic classes: NO GO / INELIGIBLE.** This means the existing CPU 8-bounce Lambert reference is **not qualified as a generally reliable HDR reference** for future GI optimization quality scoring. Any "great p99" with an all-black reference has no meaningful N007 convergence claim.
- **Specific moving-rigid CPU statistical screen: FAIL, completed** at fixed frozen upper limit and all four seeds; signal is zero at all levels.
- **Specific current GPU moving-rigid probe-shadow hypothesis: supported at image level** by byte-consistent primary geometry, matched GPU/CPU ray traversal, fixed Lambert reconstruction and independently shadow-filtered counterfactual. This establishes a model mismatch/secondary shadow query omission in the current diagnostic GPU estimator, **not** which GI result is physically correct across scenes.
- **Original archived M3b root cause: UNPROVEN.** Source SHA, camera state and full raw image identities for the original archived frame were not independently matched to this new diagnostic frame. Do not retrofit the new counterfactual onto frozen N006 claims.
- **Physical validity of CPU (or GPU) under general transport: UNKNOWN.** The reference lacks independent physically correct known-light/surface oracle comparisons for its full transport definition.

## Unmeasured registered cells — limitation, not fabricated outcome

| Other registered cell | Final evidence state | Reason for bounded stop |
|---|---|---|
| Camera-motion / camera-disocclusion | **Not prospective-calibrated in N007 P1**; black original archived references documented at P0 | Cannot rescue the all-classes reference GO after moving-rigid fails |
| Light-motion positive-signal control | **Not prospective-calibrated in N007 P1**; older archived nonblack example exists but is not qualified | Not evidence of independently validated cross-class physical correctness |
| Known-lit / known-occluded controlled non-Sponza GPU scene | **GPU test not performed**; deterministic CPU shadow fixture included and native tests linked/executed by the user's CPU workflow | Limited CPU unit visibility tests do not certify full transport |
| Static/deforming/topology-changing and high-churn | **Not requalified by this P1 study**; some renderer states may be unsupported and were not silently substituted | No user-provided calibrated P1 evidence; no positive quality claim |
| GPU camera UBO / all secondary acceleration allocations | **Not independently attested**; matched observed primary/secondary hit semantics provide partial evidence only | Prevents stronger exact original-state and general physics claims |

These gaps are explicit **bounded limitations**, not passed validation. Additional independent physically grounded oracle design is a **new separately preregistered study**, not a continuation that reopens N007/N006 after this stop.

## Retained artifacts and reproducibility

- Original P0 results **001–006**, source audit **007**, bring-up **008**, GPU shadow diagnostic **009**, CPU workflow **010** and observed real counterfactual+SPP screen **011** remain available in the N007 results index.
- Last user-reported frozen frame state SHA256: `77e1d952988d70367557c36755261a2a4eefa49177541f5e0a8a99478a24b8b4`.
- Captured source commit: `dabe590b0c6e24ab00c10de3aade50a3a8783e8e` (later N007 documentation/tooling commits are not the acquisition SHA).
- Raw scene/capture and all per-seed PFMs remain private on the user's host under ignored `out/`; user-provided derived summary was recorded accurately, but its raw file bytes are **not independently available** in the assistant sandbox. The local SHA-checking tool reported success; this limitation is retained.
- No original N001–N006 source or historical accepted shader modification, PR, CI, or GitHub Actions. No GPU timing/performance/quality improvement claim.

**Outcome:** a bounded, scientifically negative answer: the existing reference cannot be accepted as a generally defensible HDR GI quality oracle under the preregistered protocol, while the current GPU indirect discrepancy has a controlled shadow-contribution mechanism. Close Issue #4 with this **NO GO** and preserve all earlier data, rather than spending more GPU/CPU budget trying to pass already-failed cross-class eligibility.
