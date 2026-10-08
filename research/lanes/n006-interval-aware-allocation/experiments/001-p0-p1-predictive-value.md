# N006 experiment 001 — P0/P1 predictive marginal-value study

Status: **prospective DESIGN ONLY; not a frozen/executed measurement protocol**. Issue #42.  
Branch: `research-n006-interval-aware-allocation`; parent N005 HEAD `3a098584ec76bcaa06e5166793b2946cd1f7eb25`. N004/N005 raw evidence immutable.

## Hypothesis and intervention

A cheap **pre-trace** signal at an actually executable RC owner × cascade / distance-interval work unit can rank **expected benefit from adding deterministic rays**, beyond N005 uniform/depth placement, at a budget and overhead where the total GI quality/cost relationship improves.

**Label is NOT old error or local error mass.** For a fixed scene state / base work / direction seed / independent converged reference, measure the *difference in final resolved image error* between an unmodified render and a render receiving a specific extra-ray intervention. Record absolute and signed improvement, including zero/negative effects. One intervention can influence multiple final pixels, so do not assume per-owner error equals actual ray marginal benefit or that per-unit gains add linearly.

## P0 — stop before instrumenting

- Source-audit visible owner -> work-stream cascade/distance interval/direction -> radiance/merge -> sparse storage -> image. Establish true selectable unit and correctness of variable per-cascade ray counts, direction coverage, output identity, per-cascade sample normalization, and merge weights.
- Measure feasibility of bounded paired-run extra-ray interventions (offline acceptable); specify exact reproducibility, readback size, runtime budget and memory. Do not introduce persistent confidence or interval state by default.
- For each proposed signal record whether available **before** trace, bytes read/written, GPU passes/dispatch, dependency synchronization and any temporal-history requirement. Ineligible post-trace features may be diagnostics but cannot rank that same frame without a costed pilot pass.
- Record a P0 GO / REFINE / STOP decision and versioned P1 protocol **before** collecting P1 target evidence. Stop if allocation below owner × cascade cannot be made correct without a substantial redesign.

## P1 — predictive study, not a runtime scheduler

### Prospective data separation

Use existing N004/N005 playback/reference machinery, but **do not reuse the completed N005 P3 target as an independent N006 formal dataset**. Establish disjoint:
1. calibration sequences / scene and direction seeds (fit signal choices);
2. P1 evaluation sequences and seeds (compare fixed ranking without tuning);
3. sealed P3 holdout, with different scene trajectories and seeds, not observed until prospective P3 freeze.

Before P1: record generation code, seed IDs, scene/reference digests and all exclusions (none by convenience), regime and control frame schedule. Distinct seeds in identical deterministic scenes may be insufficient independence; prefer distinct trajectories/geometry/light placements where viable, and explicitly document limitations. Reuse historical reference algorithms/thresholds, **not their target outcomes for retuning**.

### Signal candidates

After P0, freeze at most **three independently measured cheap features** from:
- cascade index / interval distance scale (existing work identity);
- depth discontinuity (frozen N005 baseline without presuming its threshold optimal);
- pre-trace owner/visibility or camera-change state (N005 P1 notes poor dynamic coverage).

Do not implement all possibilities at once. Disagreement/variance, validity, age, class and neighborhood are *deferred* until an independently justified, pre-trace and costed source is found. Test combinations only if independent P1 calibration supports their incremental predictive value.

### Bounded causal measurements

- Fix eligible work-unit subset and extra direction(s), deterministic base, exact ray budget, reference and control. Run paired baseline/intervention at fixed target state, isolating one addition or a specified batch.
- Measure final-image RGB RMS improvement; also signed changes to p99 absolute, p99 relative, scale-aware affected fraction, temporal RGB RMS, with raw HDR denominators and explicit near-zero guard interpretation.
- Record actual traced rays, traced work items, per-cascade count, GPU timestamps by stage, memory, and correctness. Retain negative/zero counterfactual results.
- Document overlap/non-additivity. Do not sum single-intervention gains to claim achievable top-K combined benefit unless checked. A restricted sampled oracle must be clearly labeled approximate/conditional, not an unattested global optimum.
- Reserve held-out directions/seeds to assess Monte Carlo variability and avoid selecting only lucky rays. Repeated reference/render validation is required where label variance could reverse ranking.

### Ranking / causal evidence

At **fixed K actual extra rays**, prospectively specify K values (N005 9,216 active rays is a historical comparable anchor, not a fitted N006 optimum). Evaluate:
- uniform/random selection, historical N005 depth-discontinuity candidate, each P1 signal, and if justified one combination;
- top-K realized *global* error reduction under combined interventions (when feasible), sampled-oracle regret with explicit support limitation, ranking lift/correlation, negative-gain rate and false-negative tails;
- breakdown by near/middle/far cascade, abrupt/gradual camera, stable deformation, topology/high-churn and controls; include adverse cases (aggregate-only success is insufficient);
- per-regime quality, scheduler overhead estimates, and upper-bound extra-work GPU savings. Equal count does **not** imply equal runtime.

Required regimes: camera abrupt reveal, camera gradual motion, stable-topology deforming, topology-changing/high-churn. Controls: static, illumination-step, dense world. Moving-rigid stays formally timing-ineligible without new prospective calibration. Keep frozen N004 scale-aware affected-pixel interpretation and distinguish mathematical blocker from perceptual severity.

### P1 gate / decision

- **GO:** an implementable pre-trace signal reproducibly improves *measured* held-out top-K marginal gain vs uniform and N005 depth baseline (not just local error correlation); stable deformation and topology churn both reported; cost model does not obviously erase attainable benefit.
- **REFINE:** improvement is plausible but limited by uncertain causality, direction variability, incorrect merge weights, excessive overhead, or a failing regime.
- **STOP:** no meaningful predictive lift, unactionable work unit, inability to attribute true gain, or high overhead relative to attainable benefit.

Any numerical GO threshold must be frozen from calibration noise/practical cost **before** inspecting held-out P1 values. No post-hoc exclusion or threshold revision. If P1 fails, publish negative result and do not build a scheduler.

## Conditional P2 — implementation only after P1 passes

At most two minimal schedulers using justified signals. Modes: frozen `current`, `uniform-extra-rays`, N005 `depth-discontinuity` rule and RC-native candidate. Match *actual* extra ray counts per frame, base-prefix identity, extra-direction rule, active-state gate, total candidate work, comparable reference. Prospective eligibility shortfall must invalidate a frame or follow a **frozen** fallback rule, not silently spend fewer rays.

Capture GPU timestamp for signal-generation + priority-selection/scan + dispatch, producer, ray prepare, traversal, radiance, merge, storage update/invalidation/resolve, complete GI and complete renderer. Record memory lifetime peak, capacity/storage faults and all works. Verify adaptive variable cascade counts cannot bias radiance/merge. Compare quality vs cost (Pareto, tradeoff, loss), including controls and temporal behavior. Do not report trace-only speedups as complete-GI gains.

## Conditional P3 — formal only after positive P2

Freeze *before* target runs: policy, signal computation, thresholds, cascade units, budgets, active-frame schedule, data split, reference method/seeds, candidate order, repetition counts, device/profile, correct/invalid classification, decision guards. Reuse N005 methodological rigor: normally five fresh-process repetitions, rotating order, canonical shared reference per case, GPU timestamp primary, median interpretation, all raw samples, no excluded samples, no post-hoc fitting. Treat nonpositive incremental median GPU cost as measurement-limited; no invented efficiency ratio. Report per-regime failure, never adopt using one aggregate score.

## Research invariants

Target GPU **AMD Radeon 8060S Graphics (RADV STRIX_HALO)**. Clean evidence worktree; CPU wall diagnostic. No GPU power/profile modifications, no N004/N005 history edits, no sample deletions, no unrelated render/traversal/storage optimization, no ReSTIR-style reservoir or accumulation dependency, no GitHub Actions. The accepted single-frame RC representation and composition stay authoritative.

## Plan self-review before runtime implementation

- **Prior-art duplication:** avoids rediscovering IS-DDGI/DDGI adaptive ray allocation; tests RC-specific predictive *marginal gain* and GPU economics.
- **False causal labels:** paired interventions compare fully resolved final images; label uncertainty/nonadditivity recorded.
- **Work-unit fantasy:** source-audit gate can narrow owner × cascade or STOP rather than implementing a speculative per-interval tree.
- **Post-trace dependency:** candidate predictor must be available before ray dispatch; any pilot trace is fully costed.
- **Data leakage:** N005 P3 excluded as new formal evidence; disjoint calibration/evaluation/holdout locked.
- **Bias/validity:** variable ray count requires validation of angular coverage, output identity, merge weighting and single-frame correctness.
- **Costs/controls:** whole GI includes scheduler, memory, all regimes and controls; failed results retained.

**Review decision:** READY for P0; P1 requires versioned measurement contract; no P2 or P3 implementation authorized by this design document.
