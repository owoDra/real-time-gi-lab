# N005 P3 formal comparison contract

Status: **frozen before formal target evidence**

Issue: #40  
Branch: `research-n005-adaptive-tracing`

## Formal question

At exactly the same incremental traced-ray budget, does the frozen state-gated depth-discontinuity candidate improve the camera/dynamic quality-vs-cost tradeoff relative to uniform extra rays?

## Frozen candidate

Do not tune any of these from P3 evidence:

- signal: `depth-discontinuity`;
- normalized threshold: `0.01`;
- state gate: camera or dynamic state change only;
- 576 selected visible owner regions on active frames;
- 4 cascades;
- 4 extra rays per selected cascade/probe;
- 9,216 requested and actual extra rays per active frame;
- adaptive selection: deterministic even selection over threshold-eligible owner order;
- uniform selection: deterministic even selection over all visible owner order;
- extra directions: identical deterministic probe-key hash rule for uniform/adaptive;
- base producer prefix immutable;
- extra work inserted after the frozen base producer and before ray preparation.

## Formal regimes

Decision:

1. camera abrupt reveal;
2. camera gradual motion;
3. stable-topology deforming;
4. topology-changing/high-churn.

Controls:

- static;
- changing-illumination step;
- world-dense.

Moving-rigid remains excluded from formal timing.

The state-change schedules are byte-for-byte the P2 schedules.

## Reference discipline

Generate one canonical converged N004 8-bounce reference set per case from a dedicated current-mode reference-seed run.

That reference set is shared by every current/uniform/adaptive formal repetition. The reference seed is provenance/support evidence, not one of the formal target repetitions.

N004 reference convergence thresholds and quality metrics are unchanged.

## Repetition and ordering discipline

- 5 independent repetitions per case/mode;
- every repetition starts a fresh process/runtime and performs the frozen source warmup;
- formal mode order rotates by repetition:
  - r0: current, uniform, adaptive;
  - r1: uniform, adaptive, current;
  - r2: adaptive, current, uniform;
  - then repeat the rotation for r3/r4;
- no failed or slow sample may be deleted;
- every raw repetition remains under `out/research/`.

This rotation reduces systematic order/thermal bias without changing GPU profile or host policy.

## Formal statistics

For each case/frame/mode report all five raw samples and the median of:

Quality:
- RGB RMS error;
- p99 absolute luminance error;
- p99 relative luminance error;
- scale-aware affected-pixel fraction;
- temporal RGB RMS where applicable.

GPU timing:
- complete GI;
- complete renderer;
- extra producer;
- producer, ray prepare, traversal, radiance, merge, storage update, resolve.

Also retain memory, work/ray accounting and traversal/storage correctness.

GPU timestamps are primary. CPU wall remains diagnostic only.

## Efficiency views

Do not create one aggregate score.

Report separately:

1. quality improvement per 1,000 incremental traced rays (uniform and adaptive have the same denominator);
2. quality improvement per positive incremental complete-GI GPU microsecond versus current;
3. adaptive-vs-uniform median quality delta and median complete-GI cost delta.

If the median incremental GPU cost for a candidate is non-positive in a regime, GPU-cost efficiency for that regime is `measurement-limited`; do not manufacture a denominator or drop samples.

## Formal gates

The campaign is invalid if any of these fail:

- target GPU mismatch;
- dirty worktree or wrong branch;
- correctness / base-prefix / extra-work failure;
- traversal substantive mismatch;
- overflow or storage failure;
- active uniform/adaptive actual extra rays differ;
- active actual extra rays are not exactly 9,216;
- adaptive eligibility is below 576 selected owners;
- control/inactive frames perform extra work;
- reference convergence fails;
- a formal repetition is missing;
- sample exclusion, post-hoc threshold/budget change, or GPU profile change occurs.

## Decision interpretation

The result must end in one explicit `adopt`, `reject`, or `refine` decision.

Adaptive may be adopted only if all formal gates pass and it demonstrates a repeatable quality-vs-cost advantage over uniform in the decision regimes. Primary quality is RGB RMS; p99 absolute/relative, affected fraction and temporal behavior are guardrails and must be reported separately.

A mixed result is `refine`, not permission to re-tune the frozen P3 target evidence. Any new threshold, budget, signal or selection rule requires a new prospective experiment/revision.

## Forbidden

- aggregate score;
- sample deletion;
- post-hoc threshold/budget relaxation;
- GPU power/performance profile changes;
- moving-rigid promotion to formal timing without a new prospective calibration;
- leak suppression, denoising, multibounce/glossy work, global reorder;
- GitHub Actions.
