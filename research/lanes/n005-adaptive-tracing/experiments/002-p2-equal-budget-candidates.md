# N005 P2 — equal-budget candidate implementation and validation

Issue: #40  
Protocol: `n005-p2-equal-budget-candidates-v1`

## Question

At an identical incremental tracing budget, does one simple state-gated `depth-discontinuity` candidate improve the N004 camera/dynamic weaknesses more efficiently than uniform extra tracing?

P2 is implementation validation/calibration, **not formal target evidence**.

## Frozen input from P1

Use one local signal only:

`depth-discontinuity = max(abs(depth - neighbor_depth) / max(abs(depth), abs(neighbor_depth), 1e-6))`

over visible 4-neighbors.

Threshold: `>= 0.01`.

P1 showed a clear affected-vs-unaffected separation in the camera/dynamic blocker regimes and no need to add the deferred heuristic families before testing this simpler mechanism.

## State gate

Extra work is allowed only on a camera/dynamic state transition.

Frozen owner-budget schedule:

- `camera-abrupt-reveal`: `[576, 0, 0, 0, 0, 0, 0, 0]`
- `camera-gradual-motion`: `[576, 576, 576, 576, 576, 576, 576, 576]`
- `stable-topology-deforming`: `[576, 0, 0, 0]`
- `topology-changing-high-churn`: `[576, 0, 0, 0]`
- `static`: `[0]`
- `changing-illumination-step`: all zero
- `world-dense`: `[0]`

The state gate is deliberately separate from the local confidence score. Persistent geometric edges must not cause permanent extra tracing in controls.

## Equal-budget candidates

Compare:

1. `current`
2. `uniform-extra-rays`
3. `adaptive-extra-rays`

On each active frame:

- select exactly 576 visible owner regions;
- each selected owner contributes four cascades;
- each selected cascade receives four extra deterministic directions;
- requested extra rays = `9,216`.

Uniform selection is deterministic and evenly distributed over the visible-owner order.

Adaptive selection is deterministic and evenly distributed over owners satisfying the frozen `depth-discontinuity >= 0.01` eligibility rule.

If an adaptive active frame has fewer than 576 eligible owners, that frame is invalid for this candidate; do not silently spend fewer rays or relax the threshold.

## Runtime boundary

Preserve the P0 accounting contract:

1. run the frozen base producer unchanged;
2. snapshot base work count;
3. append N005 work in a logically separate suffix;
4. update indirect work count;
5. run unchanged ray preparation/traversal/radiance/merge/storage/resolve.

Extra work must reuse the base probe/output identity. It must not allocate new outputs or rewrite the base prefix.

Extra rays use non-base `ray_index` values so storage reservation/update remains one logical update per base probe while merged accumulation includes the additional samples.

## Direction rule

Uniform and adaptive use the exact same deterministic extra-direction generator.

The direction is derived only from probe key, cascade and extra-ray ordinal. It must not depend on candidate mode or target error/reference data.

## Required accounting

Per frame retain:

- `base_traced_rays`
- `extra_rays_requested`
- `extra_rays_traced`
- `extra_work_items`
- `eligible_probe_count`
- `extra_probe_count`
- `extra_probe_fraction`

Uniform/adaptive equality is checked on **actual** extra rays, not requested budget.

## Required measurements

Keep N004 quality axes separate:

- RGB RMS;
- p99 absolute luminance;
- p99 relative luminance;
- frozen scale-aware affected-pixel fraction;
- temporal/convergence delta.

Also retain:

- complete-GI and complete-renderer GPU time;
- N005 selection/append GPU time;
- traversal/storage/correctness counters;
- work/ray counts;
- persistent/transient/true-lifetime peak memory.

Efficiency views may report improvement per extra ray and per incremental GPU microsecond, but no aggregate score.

## Validation gate

P2 passes implementation validation only if:

- base producer prefix remains semantically unchanged;
- appended extra work passes its own metadata/probe/output checks;
- traversal has no substantive mismatch/runtime failure;
- storage failures and overflow remain zero;
- every active uniform/adaptive pair traces exactly the same extra rays;
- every adaptive active frame satisfies the frozen 576-owner eligibility requirement;
- controls trace zero extra rays.

A quality win is informative in P2 but does not by itself promote the candidate. P3 requires a separate frozen formal contract and fresh evidence.

## Discipline

- no sample deletion;
- no post-hoc threshold relaxation;
- no GPU profile changes;
- no GitHub Actions;
- no unrelated denoiser/leak/glossy/multibounce/global-reorder work;
- retain failed P2 evidence.
