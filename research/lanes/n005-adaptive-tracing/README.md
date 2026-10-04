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

**Complete.** P1 retained `depth-discontinuity` as the single first P2 local confidence signal. Temporal owner/depth-change signals were useful for camera transitions but nearly blind to the dynamic blockers. Persistent depth discontinuity localized both camera and dynamic error, but also fires on static geometry, so P2 gates it with explicit camera/dynamic state-change events.

Canonical result:
`research/lanes/n005-adaptive-tracing/results/001-p0-p1-signal-probes.md`

### P2 — equal-budget candidates

**Frozen and ready for implementation validation.**

Candidate contract:
`research/lanes/n005-adaptive-tracing/experiments/002-p2-equal-budget-candidates.md`

Initial frozen candidate:

- `depth-discontinuity >= 0.01`;
- state-change gate only for camera/dynamic transitions;
- 576 selected visible owner regions on active frames;
- 4 extra rays per selected cascade/probe;
- 9,216 requested extra rays per active frame;
- exact actual-ray equality between uniform and adaptive.

P2 remains non-formal validation/calibration.

### P3 — formal comparison

Run current vs uniform vs adaptive on a separately frozen formal contract. Preserve all evidence and publish quality/cost/memory/correctness results plus adopt/reject/refine decision.

## Discipline

- GPU timestamp primary; CPU wall diagnostic only.
- No GPU power/performance profile changes.
- No post-hoc threshold relaxation or sample deletion.
- Failed candidates remain evidence.
- No unrelated leak suppression, denoising, multi-bounce, glossy/specular work or global reorder.
- No GitHub Actions.
- Commit/push meaningful checkpoints frequently.
