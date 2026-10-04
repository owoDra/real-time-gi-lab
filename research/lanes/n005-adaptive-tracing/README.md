# N005 — state-change/confidence-driven adaptive tracing

Issue: #40  
Branch: `research-n005-adaptive-tracing`  
Base: `research-lane-n-end-to-end-renderer@c8af6b14bec9621cabdc8525b7e166a12a5fd272`

## Question

Can local state-change/confidence information target extra tracing work more efficiently than uniform extra rays after camera/disocclusion and dynamic-geometry changes?

## Evidence basis

N004 is complete. Treat these as accepted inputs, not hypotheses to rewrite:

- thin-geometry/light-leak weakness was not materially observed under the tested six-case matrix;
- changing illumination was present but bounded;
- tested world-shape regimes had no correctness/capacity failure;
- camera/disocclusion and stable/topology-changing dynamic cases crossed the frozen N004 material-blocker classification;
- moving-rigid timing remains measurement-limited;
- glossy/specular is not implemented; higher-order diffuse was not materially exposed by the tested Sponza capability case.

N004 blocker labels must remain interpreted under their frozen metric contract. Do not retrospectively change thresholds because some blocker decisions are driven by low-luminance relative-error / affected-pixel behavior despite small absolute radiometric error.

Canonical predecessor result:
`research/lanes/lane-n-end-to-end-renderer/results/004-weakness-atlas.md`

## Mandatory comparison

Use equal incremental tracing budgets:

1. frozen current renderer;
2. uniform extra rays;
3. adaptive extra rays selected by one frozen state-change/confidence rule.

An adaptive candidate cannot win merely by tracing more total rays.

## Initial candidate signals

Measure simple signals independently before combining them:

- newly visible or ownership-changed probes;
- depth/visibility discontinuity;
- allocation/invalidation/update churn;
- changed dynamic-owner AABB proximity/overlap;
- probe age/newly-created state;
- existing sample disagreement/variance proxy.

Do not start with learned predictors.

## Primary regimes

- camera abrupt reveal;
- camera gradual motion;
- stable-topology deforming;
- topology-changing/high-churn.

Controls:
- static;
- changing illumination;
- one representative world-shape case.

## Sequence

### P0 — reuse and accounting

Reuse N004 renderer/reference/playback. Define exact per-frame/per-probe extra-ray accounting and candidate evidence schema.

### P1 — signal probes

Expose candidate confidence/state-change signals without changing tracing. Measure whether each signal localizes N004 error-prone regions. Reject weak signals rather than stacking heuristics.

### P2 — equal-budget candidates

Implement `uniform-extra-rays` and one minimal `adaptive-extra-rays` candidate. Calibrate/freeze ray budgets, thresholds, candidate-selection rule, timing interpretation and formal regimes before final target evidence.

### P3 — formal comparison

Run current vs uniform vs adaptive on the frozen matrix. Preserve all evidence and publish quality/cost/memory/correctness results plus adopt/reject/refine decision.

## Discipline

- GPU timestamp primary; CPU wall diagnostic only.
- No GPU power/performance profile changes.
- No post-hoc threshold relaxation or sample deletion.
- Failed candidates remain evidence.
- No unrelated leak suppression, denoising, multi-bounce, glossy/specular work or global reorder.
- No GitHub Actions.
- Commit/push meaningful checkpoints frequently.

## First task

Before implementing adaptive tracing, read Issue #40 and the N004 result/config/runner. Then design P0/P1 so confidence signals are observable and measurable **without changing the current tracing result**. The first accepted N005 target evidence must not be produced until the candidate/budget/decision contract is frozen.
