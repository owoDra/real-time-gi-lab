# N004 — Split RC weakness atlas

Status: **complete**

Issue: #39  
Parent: #26  
Accepted protocol: `n004-weakness-atlas-v2`  
Accepted campaign commit: `3392d66a39f15d70814b71d7129c11ca84c5c8f8`

## Decision

N004 is complete. The accepted current Lane-N renderer was measured across all six prospectively frozen weakness families without adding a mitigation first.

The strongest observed pattern is **state-change quality sensitivity under camera motion and dynamic geometry**, not thin-geometry leaking or world-shape correctness/capacity failure.

Under the frozen classifier:

- all six thin-geometry/light-leak cases are `not-observed-under-tested-regime`;
- both camera/disocclusion cases are `material-blocker`;
- both changing-illumination cases are `present-but-bounded`;
- moving-rigid remains `measurement-limited` for formal timing interpretation;
- stable-topology deforming and topology-changing/high-churn are `material-blocker`;
- sparse world-shape is `not-observed-under-tested-regime`, while dense, large-horizontal and vertical-tall are `present-but-bounded`;
- higher-order diffuse and glossy/specular remain `capability-not-implemented`; the 1-bounce vs 8-bounce Sponza reference delta did not materially expose the higher-order diffuse gap.

No aggregate weakness score is reported.

## Important interpretation constraint

`material-blocker` is the result of the **prospectively frozen numerical classifier**, not a claim that the observed absolute HDR error is visually catastrophic.

The blocker cases are dominated by the relative-luminance and scale-aware affected-pixel gates in a dim workload. Their absolute errors remain small:

- camera/disocclusion: RGB RMS about `1.67e-5` to `1.81e-5`, p99 absolute luminance up to about `1.22e-4`;
- stable-topology deforming: RGB RMS about `3.02e-5`, p99 absolute luminance about `1.68e-4`;
- topology-changing/high-churn: RGB RMS about `1.74e-5`, p99 absolute luminance about `1.07e-4`.

The frozen classification is retained exactly because thresholds cannot be relaxed after target evidence. N005 should investigate the mechanism rather than reinterpret N004 post hoc.

## Per-family result

| Family / case | Classification | Key evidence |
| --- | --- | --- |
| leak thin | not observed | false irradiance fraction `0`; false p99 `0` |
| leak medium | not observed | false irradiance fraction `0`; false p99 `0` |
| leak thick | not observed | false irradiance fraction `0`; false p99 `0` |
| leak grazing | not observed | false irradiance fraction `0`; false p99 `0` |
| leak one-sided | not observed | false irradiance fraction `0`; false p99 `0` |
| leak enclosed | not observed | false irradiance fraction `0`; false p99 ~`2.43e-11` |
| camera abrupt reveal | material blocker | p99 relative ~`1.221`; affected fraction ~`14.31%`; no convergence |
| camera gradual motion | material blocker | p99 relative up to ~`1.221`; affected fraction ~`12.19–14.44%`; no convergence |
| light step change | present but bounded | p99 relative ~`0.153`; affected fraction ~`2.32%` |
| light gradual change | present but bounded | early tail reaches p99 relative ~`1.068`; reaches not-observed state at frame `2`, but path-level result remains bounded |
| moving rigid | measurement limited | quality/correctness retained; formal timing remains excluded by N003 calibration |
| stable-topology deforming | material blocker | p99 relative ~`1.678`; affected fraction ~`11.47%` |
| topology high churn | material blocker | p99 relative ~`1.068`; affected fraction ~`11.42%` |
| world sparse | not observed | correctness/capacity pass; no overflow/storage failure |
| world dense | present but bounded | correctness/capacity pass; affected fraction ~`7.91%` |
| world large-horizontal | present but bounded | correctness/capacity pass; affected fraction ~`1.31%` |
| world vertical-tall | present but bounded | correctness/capacity pass; affected fraction ~`2.90%` |
| higher-order diffuse | capability not implemented | 1-vs-8 bounce Sponza delta: RGB RMS ~`8.41e-7`, affected ~`0.049%`; material gap not exposed in this scene |
| glossy/specular | capability not implemented | frozen renderer has no glossy/specular indirect transport path |

## Correctness and world-shape result

All accepted cases retained internal correctness. The corrected v4 synthetic world layouts removed the pre-target exact-edge workload degeneracy without changing the family matrix or numerical thresholds.

The accepted world-shape cases have no correctness/capacity blocker:

- strict hit diagnostics pass;
- no traversal runtime errors;
- no storage failures;
- no producer semantic errors;
- no overflow;
- no missing/leaked/stale probe/storage condition in the retained correctness counters.

Therefore the world-shape classifications reflect radiometric quality under the tested layouts rather than a capacity or traversal failure.

## Leak result

The originally suspected thin-geometry leakage was **not observed under the controlled N004 regime**. All six controlled cases report zero false-irradiance fraction at the frozen threshold; enclosed has only numerical-noise-scale false p99.

This does not prove that Split RC can never leak. It means leak mitigation is not the highest-value next target from the tested N004 workloads.

## Camera / dynamic result

Camera motion is the broadest repeated blocker: both abrupt and gradual paths cross the frozen blocker gate while internal correctness remains clean.

Stable-topology deformation and topology-changing/high-churn also cross the blocker gate. Their absolute errors remain small, so the evidence supports investigating **where fixed tracing effort is insufficient under state changes**, rather than assuming a traversal/storage correctness failure.

Moving-rigid remains timing `measurement-limited` by the existing Lane-N timing calibration and receives no formal timing conclusion.

## Capability result

Higher-order diffuse and glossy/specular are explicit capability gaps, but N004 does not justify prioritizing them ahead of the observed state-change weakness:

- Sponza did not materially expose the 1-bounce vs 8-bounce diffuse difference under the frozen rule;
- glossy/specular indirect is structurally absent, but N004 provides no target evidence that it dominates the current diffuse-GI error budget.

## Resume / provenance discipline

The accepted campaign used whole-case checkpoint resume after host interruption:

- six leak cases and both camera cases were reused only after complete `n004-evidence.json` validation;
- the incomplete `changing-illumination/step-change` artifact was retained separately and that entire case was rerun;
- all later cases were run normally;
- sample exclusion remained `none`;
- GPU power/performance profile changes were forbidden and not performed.

This preserves complete-case identity and does not cherry-pick frames or samples.

## N005 decision

Select exactly one next transport research question:

> **Can state-change/confidence-driven adaptive tracing reduce the persistent low-radiance error tails observed under camera motion and dynamic geometry, without materially increasing the accepted complete-renderer GPU boundary or reopening the accepted A–M traversal/storage architecture?**

Why this question:

1. it directly targets every observed `material-blocker` family rather than an unobserved leak weakness;
2. it can cover newly visible camera regions and changed dynamic ownership with one mechanism;
3. it does not assume temporal reuse is sufficient — abrupt camera error remains stable across repeated target frames rather than naturally converging;
4. it preserves the accepted traversal/storage architecture unless evidence proves the problem lies there;
5. higher-order diffuse was not materially exposed by the tested Sponza reference, so multi-bounce is lower priority from N004 evidence.

N005 must first localize the blocker pixels/work items and define a prospective adaptive/confidence signal and cost/quality gate. It must not silently raise global rays-per-probe or alter N004 thresholds after the fact.
