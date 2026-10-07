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

N004 blocker labels remain interpreted under their frozen metric contract. Do not retrospectively change thresholds.

Canonical predecessor result:
`research/lanes/lane-n-end-to-end-renderer/results/004-weakness-atlas.md`

## Mandatory comparison

Use equal incremental tracing budgets:

1. frozen current renderer;
2. uniform extra rays;
3. adaptive extra rays selected by one frozen state-change/confidence rule.

An adaptive candidate cannot win merely by tracing more total rays.

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

Complete. Reuse N004 renderer/reference/playback and keep extra work as an attributable suffix after the frozen producer and before ray preparation.

### P1 — signal probes

**Complete.** P1 retained `depth-discontinuity` as the single first P2 local confidence signal. Temporal owner/depth-change signals were useful for camera transitions but nearly blind to the dynamic blockers. Persistent depth discontinuity localized both camera and dynamic error, but also fires on static geometry, so P2 gates it with explicit camera/dynamic state-change events.

Canonical result:
`research/lanes/n005-adaptive-tracing/results/001-p0-p1-signal-probes.md`

### P2 — equal-budget candidates

**Complete.** The frozen equal-budget candidate was validated twice: first with a serial extra-producer implementation, then with the same semantics implemented using a parallel 128-thread owner scan.

Canonical result:
`research/lanes/n005-adaptive-tracing/results/002-p2-equal-budget-candidates.md`

Frozen candidate:

- `depth-discontinuity >= 0.01`;
- camera/dynamic state-change gate only;
- 576 selected visible owner regions on active frames;
- 4 cascades;
- 4 extra rays per selected probe;
- 9,216 requested/actual extra rays per active frame;
- exact actual-ray equality between uniform and adaptive.

Optimized P2 retained all correctness/equal-budget/control gates. Across the 11 active decision frames, RGB RMS reduction vs current averaged about 2.54% for uniform and 4.23% for adaptive. Extra-producer GPU time fell from millisecond-scale serial behavior to about 144 us mean for uniform and 215 us mean for adaptive.

P2 remains calibration evidence, not the final formal measurement.

### P3 — formal comparison

**Contract frozen; runner implemented; local build/tests/formal target run pending.**

Formal contract:
`research/lanes/n005-adaptive-tracing/experiments/003-p3-formal-comparison.md`

Formal config:
`research/lanes/n005-adaptive-tracing/experiments/003-p3-formal-comparison-config.json`

P3 freezes the P2 candidate without re-tuning and adds:

- one canonical converged reference set per case, shared across all formal samples;
- 5 fresh-process repetitions per case/mode;
- rotating mode order across repetitions;
- GPU timestamp medians as the primary timing statistic;
- all raw samples retained;
- zero completed-campaign rerun budget;
- separate ray-normalized and GPU-cost efficiency views; no aggregate score.

`phos-n005-candidate --skip-reference` exists only to avoid regenerating the expensive canonical reference during formal repetitions. Default P2 behavior remains unchanged.

Runner:
`scripts/research/n005_adaptive_tracing/run_n005_p3.py`

## Discipline

- GPU timestamp primary; CPU wall diagnostic only.
- No GPU power/performance profile changes.
- No post-hoc threshold relaxation or sample deletion.
- Failed candidates remain evidence.
- No unrelated leak suppression, denoising, multi-bounce, glossy/specular work or global reorder.
- No GitHub Actions.
- Commit/push meaningful checkpoints frequently.
