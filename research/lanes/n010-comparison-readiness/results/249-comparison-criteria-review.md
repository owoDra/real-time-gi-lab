# N010 comparison criteria review — 2026-10-17

Classification: **methodology review / post-hoc diagnosis**, not a new
calibration, accepted performance result or readiness decision. Source
checkpoint: `8c3b13f`. No new CPU reference or GPU acquisition was executed.

## Conclusion

Review the timing decision method before another telemetry implementation or
precision experiment. Retain GPU Renderer time as the primary performance
axis. Evaluate whether an effect remains identifiable with measurement
uncertainty and possible ordering bias, rather than requiring every stability
annotation to satisfy the same small percentage irrespective of the claim.

This adopts the direction for the next prospective method. It does **not**
replace the frozen numerical gates in experiment001/009, accept old samples,
or establish that a replacement method will pass. N010 remains **NOT_READY**.

## What the existing evidence says

Experiment001 targets approximately +20% architecture-neutral additional GPU
work, but requires control envelope <=1.02, span <=1.03 and order bias <=1.02,
alongside four effect checks. These conditions were prospectively registered;
their recorded outcomes remain authoritative.

| Retained diagnostic | Control order bias | Other failed checks | Minimum process effect | Recorded outcome |
| --- | ---: | --- | ---: | --- |
| [247 four-frame means](247-four-frame-c7-precision-diagnostic.json) | 1.024851 | None | 1.184458 | 6/7 checks pass; overall FAIL |
| [248 symmetric interleaving](248-interleaved-four-frame-c7-precision-diagnostic.json) | 1.023116 | Control envelope 1.029850; span 1.040768 | 1.179454 | 4/7 checks pass; overall FAIL |

These static C7 HWRT diagnostics motivate questioning the decision method's
fit to the intended effect size. They do not prove the old cuts unnecessary,
an accepted 20% detection capability, the cause of variability, or any GI
advantage. The known-work dose targets a time increment; it does not guarantee
an exact time increment. Its +20% target also does not by itself define a
practically meaningful architecture superiority margin.

Order dependence can be systematic bias. A narrow confidence interval around
a biased estimate would still be misleading. Averaging samples or attaching
an interval is insufficient unless the design addresses ordering and drift.

Retained JSON SHA-256 identities:

- 247: `f9bc9f7249788245f2ab6de5e79fb5ad3262c7ecf780cf915c492ae4e527bcfa`
- 248: `9d39b790a656b2129dc271d595b7d2ccfda61dcd3d5e61dd93e344760ae5134a`

## Roles in the revised comparison

| Item | Role |
| --- | --- |
| Physical reference eligibility, semantic parity, scene/lighting/depth and HDR correctness | Required correctness and quality boundary; retain existing gates and all failures. |
| Total/indirect quality and dynamic response | Compare at matched quality or matched cost; retain losses and transition/recovery frames. |
| Complete Renderer GPU timestamp | Primary performance result, with paired relative effects, uncertainty and hardware/environment provenance. Absolute times remain reported. |
| Owned Vulkan allocation events | Persistent/transient/startup/recurring true peak; retain all required contexts, cap and zero-teardown proof. Global free GPU memory is not algorithm memory consumption. |
| CPU wall, GPU busy/clock/temperature, other-app activity | Health/provenance/diagnostic observations. No new idle-percent or clock-stability acceptance requirement. |
| Control variation and order effects | Evidence about measurement uncertainty or bias; their effect on the claim must be specified prospectively. No automatic GI rejection from a stability percentage alone. |

Same-session ratios can reduce shared drift; they do not guarantee removal of
workload-dependent clock, contention or ordering effects. Hardware, driver,
render resolution, output mode, lifecycle and all included costs remain fixed
and identified within a comparison. Display settings are not measurement
controls to manipulate. Device/process failures, invalid timestamps, changed
workloads, missing pairs or provenance failures still prevent accepted timing.

## Required content of the next prospective timing amendment

1. Freeze the estimand (including ratio direction and aggregation), practical
   effect margin, uncertainty level and claim scope before fresh acquisition.
   Distinguish detecting a nonzero effect from proving a practically useful
   improvement; do not choose a margin that makes 247/248 pass.
2. Use paired baseline/candidate observations and prospectively randomized,
   balanced ordering. Treat fresh-process blocks as repetition units; do not
   count correlated frames as independent trials. Freeze the sample count,
   warmup, time/resource budget, stopping rule and zero-retry policy.
3. Specify the interval estimator and its assumptions, treatment of process
   variability, concurrent identical controls, ordering and drift. Model or
   conservatively bound residual systematic bias. If that bound cannot be
   justified, classify timing as inconclusive; an ordinary sampling interval
   alone is insufficient. Do not subtract observed control bias by default.
4. Calibrate architecture-neutrally on the actual selected full Renderer
   boundaries before accepted candidate timing. Preserve the existing +20%
   known-work target as the starting calibration question; report the measured
   effect. C7, one batch lifecycle, one PT budget or one GPU cannot qualify
   other boundaries automatically. Any new claimed resolution needs evidence.
5. Freeze the result classifier. At matched quality, a performance win requires
   an uncertainty/bias bound wholly beyond the declared improvement margin;
   a loss requires the corresponding reverse result. Equivalence requires an
   explicit equivalence margin and evidence within it. Otherwise report
   **inconclusive**. Failure to prove superiority is not proof of equality.
   Account for multiple comparisons before any selected-row or overall win.
6. Retain every raw sample and all predefined corpus rows, including failures
   and inconclusive rows. No timing gate failure erases valid quality or memory
   observations. An overall claim must respect its preregistered coverage;
   do not select only decisive scenes or rerun until a favorable interval.

This is a concrete specification for the replacement, not its executable
statistical registration. Exact estimators, numerical decision margins,
sample sizes and coverage rules still require an explicit amendment and a
matching verifier before any newly accepted acquisition. Existing timing
preflight must not be bypassed in the meantime. Old-sample reanalysis, if
performed, must be labelled exploratory and cannot qualify the new method.

The statistical motivation is consistent with Kalibera and Jones,
[Quantifying Performance Changes with Effect Size Confidence Intervals](https://www.cs.kent.ac.uk/pubs/2012/3233/):
performance ratios need uncertainty estimates that account for different
sources of execution variability. That work does not validate this GPU
fixture, choose our margins, or bound its systematic bias.

## Completion path and limits

The next timing task is one prospective replacement specification and its
bounded calibration, rather than another attempt to reach the old stability
percentages through environment tuning. Read-only telemetry is optional
diagnosis, not a new prerequisite. No power, clock, display, driver or other
application settings are changed.

The other N010 obligations remain: all24 eligible references (currently16/24),
physical proof (currently11/17 full artifacts), full-corpus quality/dynamic
pilots, frozen quality budgets, measured persistent/true-peak memory and the
DDGI scene-GI boundary. Sponza direct-light maximum-relative-error-1.0 pixels
remain **UNRESOLVED / 未解決**, included in scoring. No family or difficult
scene is removed. No N011 is introduced. Revised timing methodology alone
cannot complete these obligations or demonstrate superiority.

Checks for this record: documentation/evidence review only. Build, unit tests,
runtime/correctness checks and new CPU/GPU measurements: **NOT RUN**. No
executable Renderer, shader, build graph or historical result was changed.
Metadata-only `python scripts/research/verify.py`: OK, eight configured lane
indexes /249 declared result links. `git diff --check`: clean. These checks
do not establish runtime correctness or measurement capability.
