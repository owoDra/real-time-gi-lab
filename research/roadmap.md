# Forward research roadmap — major gates only

## Current execution checkpoint — 2026-10-17 JST

**N010 remains NOT_READY.** User resumed work for cause diagnosis and the
shortest valid completion path, with low interactive load. No old stopped
acquisition or waiting queue is restarted. Bounded CPU and short C7 GPU
diagnostics have completed; neither supplies the missing readiness proof.
One registered original A6c CPU control is running (234, one low-priority
core). No full-frame reference ladder, GPU campaign or subsequent-control queue
is running or queued.

[Read-only idle observation 235](lanes/n010-comparison-readiness/results/235-posthoc-natural-idle-read-only-observation.json) records 30.157s
after the user answered “now”: Brave and IDE DRM counters increased.
Eight same-UID processes remain inaccessible. This is a post-hoc
activity observation, not paired precision or causal evidence. No GPU
work was launched alongside the active A6c CPU acquisition.

[Plan 087](lanes/n010-comparison-readiness/experiments/087-remaining-original-controls-cost.md) prepares the
six remaining original-scene cost probes. **NOT RUN / NOT QUEUED**; the
driver refuses live or failed234 and only reports cost, with fixed
one-core limits. Original full counts and scientific gates stay fixed.

See [cause review 192](lanes/n010-comparison-readiness/results/192-cause-review-and-shortest-valid-completion.md)
and [prospective bounded plan 057](lanes/n010-comparison-readiness/experiments/057-bounded-cause-diagnosis-and-critical-path.md).

| Required item | Actual current evidence | Remaining work |
| --- | --- | --- |
| All 24 eligible references | [160](lanes/n010-comparison-readiness/results/160-primary-direction-reference-view.json): sixteen eligible, eight pending | Resolve the dominant uncertainty mechanism; validate any distinct sampling method before all fixed pending ladders. |
| Stopped first-direction guide | [180](lanes/n010-comparison-readiness/results/180-primary-direction-second-stop-bounded-feasibility.json): **COMPLETE / FAIL**, 8192/16384 ratios **1.0703554221788882 / 1.0599135470235277** against <=0.75 | Candidate rejected; 166 NOT RUN and blocked by its genuine FAIL. This is not a full statistical-cap failure. |
| Whole-path reference candidate | [223](lanes/n010-comparison-readiness/results/223-all-split-general-transport-equivalence.json): exact legacy equivalence; [225](lanes/n010-comparison-readiness/results/225-all-split-full-sidedness-controls.json)/[226](lanes/n010-comparison-readiness/results/226-all-split-full-deterministic-controls.json)/[231](lanes/n010-comparison-readiness/results/231-posthoc-original-a7-retained-control.json): 10/17 original full controls PASS | [234](lanes/n010-comparison-readiness/results/234-all-split-original-a6c-full-physical-control.json) A6c RUNNING; finish remaining original controls, bias, all-state/prefix and full-frame feasibility before intake. |
| GPU calibration | [185](lanes/n010-comparison-readiness/results/185-deferred-image-calibration-sizing.json): **COMPLETE / sizing PASS**, all sixteen boundaries | Short C7 probes 196/197 both complete and FAIL all seven precision gates, including user-idle 197. Full 186 NOT RUN; no accepted timing. |
| Correctness | Actual GPU keys/BF-P evidence retained; [053](lanes/n010-comparison-readiness/results/053-residual-primary-contract-diagnosis.md) supports CPU primary-tie mechanism | GPU repair unverified; the original gate permits explicitly measured remaining direct discrepancies. Max-relative-error-1.0 pixels stay **UNRESOLVED / 未解決**, included. |
| Cohort and quality/memory pilots | RC/PT families executable; measured quality losses and allocation ledgers retained | Finish missing full-corpus ladders/dynamic pilots and original final six-gate auditor. DDGI source/device boundary remains required for Lane M. |

### What the cause analysis establishes

CPU-only [191](lanes/n010-comparison-readiness/results/191-posthoc-readiness-bottleneck-diagnosis.json)
checks retained original C1 B2/B8 scene/sidecar identities. At
8192/16384/32768, later-indirect replicate-centered energy divided by full
indirect energy is **0.974696 / 0.982808 / 0.986884**. First-indirect ratios
are only 0.017115 / 0.012833 / 0.010016; covariance is separately retained.
These are four-replicate image-energy diagnostics, not additive variance
shares or iid uncertainty estimates. They locate the observed disagreement
after the first indirect bounce. The failed guide targets first-secondary-hit
direct light, then applies its weight to all later contributions. Completed
193/194 below separate depth/weight effects from the loss of observed net
variance reduction; a complete causal explanation remains unproved.

Original C1 B8 absolute-p99 decay exponent is 0.518411. Planning extrapolation
predicts 1.71180e-5 / 1.19508e-5 at 131072/262144, above the unchanged 1e-5
gate. This is not a measured cap failure or a replacement acceptance threshold.
Do not spend full ladders on marginal early improvement without examining
whether the original consecutive-level criterion is plausibly reachable.

Timing causes remain hypotheses. Complete 169 has two heavy PT B8 PASS and
fourteen FAIL boundaries; terminal 178 has three FAIL and one partial plus
failed environment/restoration guards. Replays 175/179 and post-hoc 183 retain
all decisions. File cadence and IDE accounting are not causal clock/power or
GPU-idle evidence. Deferred serialization's complete sizing 185 establishes
image/scratch/memory/spool checks, not full precision. Its zero-dose medians
alone imply about 4405 seconds summed GPU work for full 186 before other costs;
this scale estimate is not an ETA. No long GPU run is automatically queued.

### Completed small diagnosis and the next bounded checks

[193](lanes/n010-comparison-readiness/results/193-selected-bounce-path-diagnosis.json) completed all six
serial compiler/native invocations. Original and failed-guide selected mean
and second-moment fields are bit-exact to retained sidecars. Native runs took
10.324 / 10.400 / 10.271 seconds, one low-priority CPU each, no GPU.
[194](lanes/n010-comparison-readiness/results/194-posthoc-depth-weight-and-rqmc-interpretation.json)
keeps tail selection separate from fixed-grid observations. On the sixteen
selected pixels, the guide reduces first-indirect path variance but increases
later variance. Whole-image data show a necessary qualification: **total path
variance actually falls to 0.969 of original, while observed replicate variance
increases to 1.133 / 1.135**. Loss of the observed net variance-reduction benefit,
not simply more path variance, is therefore part of the measured failure.
Moment-based iid proxies are descriptive only, never RQMC standard errors.

[Plan 058](lanes/n010-comparison-readiness/experiments/058-fixed-grid-and-short-boundary-diagnostics.md)
completed both diagnostics. [195](lanes/n010-comparison-readiness/results/195-fixed-grid-scramble-diagnosis.json)
uses the exact existing nested binary on a prospectively fixed 256-pixel C1
grid, one CPU at nice 15, 164.588 seconds, no GPU. Nested/original p99 is
**0.948183**, but replicate variance is **1.018947**. This one-level grid
provides no evidence of the strong reduction needed to justify another long
ladder. It is not a formal failure of unrun 188/189/190 or reference admission.

[196](lanes/n010-comparison-readiness/results/196-deferred-c7-precision-diagnostic.json) and
[197](lanes/n010-comparison-readiness/results/197-natural-idle-c7-precision-diagnostic.json), prospectively
registered in [059](lanes/n010-comparison-readiness/experiments/059-natural-idle-c7-observation.md), each
complete all eight C7 HWRT blocks / 512 samples with frozen dose 3439 and
unchanged original classifier. **Both FAIL all seven precision gates.**
Summed measured GPU intervals are only 0.252902 / 0.249035 seconds; setup,
readback, output and one-second block settles are additional. All acquisition
image/scratch checks and owned-memory/spool checks pass. In 197, even with
the user leaving the PC untouched, zero-dose full GPU times span
**147.961–956.537 us**, known-work times **2.405–13.746 us**.

197 observes positive DRM engine deltas for Brave and the IDE over a coarse
13.572-second interval; eight same-UID processes are inaccessible. This is
neither exact per-query overlap nor proof of interference, clock changes or
global GPU idleness. Deferred CPU serialization plus a user-idle interval
has not established precision; do not dispatch the >hour full 186 campaign.
[198](lanes/n010-comparison-readiness/results/198-bounded-cause-probes-posthoc-replay.json) replays all
original schedules/decisions, native resource receipts, owned ledgers and CPU
spool receipts exactly; it does not independently rehash every native payload.

### Completed implementation probes 060/061

[199](lanes/n010-comparison-readiness/results/199-packed-readback-fixture-build.json) builds an isolated
capture fixture with four diagnostic downloads coalesced after the original
timed GPU commands. Whole-source inverses and unchanged timed recording and
expressions pass. One-CPU compile/link durations are 6.461 / 2.646 / 0.057
seconds. [200](lanes/n010-comparison-readiness/results/200-packed-readback-c7-sizing.json) completes
C7 sizing PASS, dose 3500. All images/scratch/owned-memory/CPU spools pass.
Actual [201](lanes/n010-comparison-readiness/results/201-packed-readback-c7-precision-diagnostic.json)
completes all eight blocks / 512 samples but **FAILS all seven original gates**.
Zero-dose times span 156.177–987.717 us; observed peak owned Vulkan memory is
263382656 bytes, teardown zero. This fixed candidate stops; no full campaign.

[202](lanes/n010-comparison-readiness/results/202-later-bounce-cv-path-diagnosis.json) completes the
prospective [061](lanes/n010-comparison-readiness/experiments/061-later-bounce-control-variate-diagnosis.md)
conditional control-variate diagnosis on eight fixed C1 pixels, one low-priority
CPU, 67.572 seconds. Original means/moments reconstruct bit-exactly. Corrected
p99 ratio is **0.837924**, but replicate variance **1.054490** and descriptive
per-path variance **1.032952**. Its prospective promising rule FAILS; no full
controls/ladder follows this fixed prototype. This does not reject every
conditional correction or prove a general variance theorem.

[203](lanes/n010-comparison-readiness/results/203-array-rqmc-transport-diagnosis.json), registered in
[062](lanes/n010-comparison-readiness/experiments/062-array-rqmc-transport-diagnosis.md), then completes
an eight-pixel geometry-sorted array-RQMC prototype in 24.206 native CPU
seconds. Original moments, deterministic components and first-indirect luma
means match retained values bit-for-bit. Its p99 ratio is **1.049287**,
replicate variance **0.885354**, and per-path variance **0.994757**. The
prospective promising rule FAILS. This fixed sort/assignment stops; no
larger-level prefix, full physical/state proof or reference admission follows.
The result does not reject array-RQMC generally or establish the behavior of
all eight pending corpus slots. No scientific acquisition remains running.

### Contiguous submission diagnosis, completed 2026-10-17

[063](lanes/n010-comparison-readiness/experiments/063-contiguous-c7-command-batch-diagnosis.md) through
[065](lanes/n010-comparison-readiness/experiments/065-contiguous-import-header-repair.md) implement a static C7-only
fixture with separate uniform/query/readback slots for every original frame.
[204](lanes/n010-comparison-readiness/results/204-contiguous-c7-fixture-build.json) and
[205](lanes/n010-comparison-readiness/results/205-contiguous-c7-decoder-repair-build.json) preserve compiler failures;
[206](lanes/n010-comparison-readiness/results/206-contiguous-c7-import-repair-build.json) builds successfully without
changing original timed GPU recording or timing expressions. No original
header/default target changes. [207](lanes/n010-comparison-readiness/results/207-contiguous-c7-sizing.json) sizing PASS
freezes dose 1342 by the original rule; no dose tuning follows.

[208](lanes/n010-comparison-readiness/results/208-contiguous-c7-precision-diagnostic.json) completes all 8 blocks / 512
samples, each block in one frame-batch submit/wait. Every original image,
scratch, schedule, owned-memory ledger and batch frame identity passes its
acquisition check. Original classifier: **3/7 gates PASS, overall FAIL**.
Control envelope 1.030658, span 1.046921, order bias 1.078222; effect span
1.027634 (PASS), order bias 1.033715 (FAIL), minimum positive fraction 0.916667
(PASS), minimum effect 1.193435 > control envelope (PASS). Summed measured
GPU intervals **0.082508 seconds**; zero-dose full GPU times
131.249 / 141.108 / 419.156 us (min/median/max). Setup, copies, CPU recording
and one-second block settles are additional. Cached CPU calls are not separate
frame wall-time measurements. All native payload hashes and original decisions
were independently replayed on one low-priority CPU after acquisition.

This fixture does not establish original precision or explain how much prior
variation came from CPU gaps: dose, cadence and natural environment differ.
It has no PT/dense-RC or fresh-state dynamic implementation. Do not transfer it
to all sixteen boundaries or rerun a failed candidate/full campaign. No
scientific worker remains. Reference eligibility remains **16/24**.

[066](lanes/n010-comparison-readiness/experiments/066-frozen-suffix-control-variate-diagnosis.md) and
[209](lanes/n010-comparison-readiness/results/209-frozen-suffix-cv-diagnosis.json) complete a distinct frozen
full-suffix predictor: 65536 auxiliary pilot paths, then the original 32
scored pixel/seed records, one CPU nice15. Compile/native 1.767 / 6.389
seconds. All original means/second moments and deterministic components are
bit-exact; the model dump is byte-identical before/after scoring. Corrected
p99 ratio **0.947268**, replicate variance **1.033002**, path variance
**0.975724**. The prospective promising rule FAILS; this fixed model stops.
The local predictor has not established the reduction needed for any new
reference ladder. All 24 slots/seeds/cap/gates remain, **16/24 eligible**.
No long reference/GPU campaign or scientific worker is running or queued.
Completion time remains unproved; no N010 READY or Lane M result is asserted.

### Whole-path reference methods: a bounded promising result, not admission

[210](lanes/n010-comparison-readiness/results/210-whole-path-mixture-diagnosis.json) / [212](lanes/n010-comparison-readiness/results/212-whole-path-conditioned-diagnosis.json) remain INCOMPLETE at numerical guards;
[211](lanes/n010-comparison-readiness/results/211-whole-path-numeric-failure-witness.json), [213](lanes/n010-comparison-readiness/results/213-whole-path-own-support-witness.json) and [214](lanes/n010-comparison-readiness/results/214-coincident-surface-operator-diagnosis.json) preserve the conditioning,
overlapping-face and one-ULP operator witnesses. [072](lanes/n010-comparison-readiness/experiments/072-coincident-geometric-support-audit.md) prospectively
amends support matching to exact common axis-plane/interior/material checks,
bit-equal original nudge/spawn, bounded normal differences and actual
alternative-self ray/direct checks. Original IDs, points and physical methods
remain. This is explicitly a numerical support approximation, not a proof
of bit-equal N008 finite-arithmetic expectation.

[215](lanes/n010-comparison-readiness/results/215-whole-path-geometric-support-diagnosis.json) still stops at own-support, INCOMPLETE. Post-hoc [216](lanes/n010-comparison-readiness/results/216-coincident-predicate-witness.json)
finds that the last recorded unmatched pair has opposite signed-zero Duff
basis branches, despite equal numeric axis normals/spawn/material. It is a
candidate-pair diagnosis, not a full failing-prefix reproduction. [074](lanes/n010-comparison-readiness/experiments/074-axis-cosine-support-audit.md)
derives that the two exact axis frames differ by an azimuth pi rotation,
which preserves cosine density. It removes that basis-sign predicate only;
original sample maps stay untouched. All failed records and amendments remain.

[217](lanes/n010-comparison-readiness/results/217-whole-path-axis-cosine-diagnosis.json) then completes the fixed half-eye/half-light prototype:
p99 ratio **0.845880**, replicate variance **0.819401**, path variance
**1.390209**. The original promising rule FAILS; that construction stops.
[075](lanes/n010-comparison-readiness/experiments/075-all-split-path-mixture-diagnosis.md) defines a distinct uniform mixture over every eye/light split
for each depth k. Forward and reverse ordered raw-area densities are evaluated
independently; original target F=q_eye*R retains soft falloff/nudge/offset.
The contribution is (k+1)*F/sum(q_split), bounded by(k+1)*R. It traces up to28
vertices per scored index, versus seven previously; this is no equal-cost claim.

[218](lanes/n010-comparison-readiness/results/218-all-split-path-mixture-diagnosis.json) completes all original32 eight-pixel/four-seed8192 records.
Original moments and deterministic components are bit-exact. Ratios:
**p99 0.701796**, **replicate variance 0.507418**, path variance0.830818.
Both unchanged promising gates (<=0.75 / <=0.5625) PASS. Compile/native
2.346 / 50.747 seconds, one CPU nice15, no GPU. This is one-level small-grid
reference-sampler evidence, not a GI performance result or reference admission.

[219](lanes/n010-comparison-readiness/results/219-bounded-all-split-furnace-control.json) retains a control-driver compile error; [077](lanes/n010-comparison-readiness/experiments/077-furnace-original-iid-constructor-repair.md) fixes
its original Xoshiro(seed,pixel,index) invocation before any native control.
[220](lanes/n010-comparison-readiness/results/220-bounded-all-split-furnace-control.json) uses the byte-identical218 header on a derived original A6a
sphere, rho1, eight fixed pixels/four seeds. B2/B8 means pass analytic sphere
expectations with a derived mesh envelope and the original0.002 allowance;
independent original iid16384 vs net8192 relative mean differences are
**6.0448e-6 / 4.1381e-6**, NRMSE **4.5751e-5 / 1.2832e-5**. Zero-light
controls are exactly zero. This bounded derived control does NOT attest all
seventeen original controls, colored/single-sided materials or the corpus.

Post-hoc [221](lanes/n010-comparison-readiness/results/221-posthoc-path-mixture-evidence-replay.json) independently replays decisions/original moment bits,
physical-source inverses,98 immutable payload hashes and11 terminated compiler/
native identities. Numerical limitations are explicit:218's largest original
unconditioned error/B is **1.41086e10**, while its conditioned plane audit is
0.635854 and own-log error1.11894e-9. A conditioned audit and a sphere PASS
are not a bound on Sponza physical bias. Five coincident matches, zero following
alternative-ray checks and one alternative-direct check are the actually
covered218 observations, not exhaustive equivalence.

Next: integrate general material/sidedness/finite-depth target factors without
changing original transport, validate all original applicable physical controls
and numerical-density bias, then all24-state/exact-prefix and whole-frame
feasibility before the unchanged reference ladders. All original gates remain;
references **16/24**, timing208 **FAIL**, direct1.0 pixels **UNRESOLVED / 未解決**
and included. At the 215–221 checkpoint there was no retained worker or queue. No GPU/
settings/default build change occurred. Unit/regression tests NOT RUN. N010 remains NOT_READY;
no Lane M comparative superiority result or completion date is asserted.

### General adapter and original physical controls — active A6c acquisition

[078](lanes/n010-comparison-readiness/experiments/078-all-split-general-transport-and-prefix-reuse.md) adds the original RGB throughput product, one-sided back-face
absorption and actual 1–8 vertex limit to the sampling target. The geometric
proposal stays separate from physical absorption; no black/back-face reflection
is introduced. Ordered area-density prefixes are traversed once per order,
with original sums and states. [222](lanes/n010-comparison-readiness/results/222-all-split-general-transport-equivalence.json) preserves a helper-scope compile
failure; [079](lanes/n010-comparison-readiness/experiments/079-general-prefix-helper-scope-repair.md) moves only the misplaced brace. [223](lanes/n010-comparison-readiness/results/223-all-split-general-transport-equivalence.json) then
compares **every one of 262,144 C1 sample indices** against the prior sampler:
RGB components and depth values match bit-for-bit; all accumulated 218 fields
also match. Native duration 82.398 seconds includes both samplers and original
controls, and is not a separate speed measurement of the new implementation.

[224](lanes/n010-comparison-readiness/results/224-all-split-exporter-build.json) builds an opt-in full-output CPU exporter with exact source
inverses. Its scored RNG stays untouched while an independent copy primes the
original primary cache once per pixel; that auxiliary work is counted. Original
writers/checkpoints are retained. One render thread is enforced; main Renderer,
CMake and GPU behavior remain unchanged.

[225](lanes/n010-comparison-readiness/results/225-all-split-full-sidedness-controls.json) and [226](lanes/n010-comparison-readiness/results/226-all-split-full-deterministic-controls.json) complete **nine original full control scenes**
at original 128×96, 64 samples and all four seeds. Every moment/PFM/hit payload
matches original bytes, with no pixel masks. Primary counters remain exact;
proposal endpoint-shadow work is named separately and need not equal another
sampler's workload. These direct/zero-indirect controls do not establish
stochastic multi-bounce convergence.

[227](lanes/n010-comparison-readiness/results/227-all-split-original-a7-cost-pilot.json) is a retained A7 cost-pilot diagnostic stop: it compared 64-sample
rounded accumulations with 8192-sample records. [228](lanes/n010-comparison-readiness/results/228-all-split-original-a7-full-control.json) was NOT RUN.
[083](lanes/n010-comparison-readiness/experiments/083-a7-pilot-same-count-baseline-amendment.md) instead acquires an original same-count 64-sample baseline;
[229](lanes/n010-comparison-readiness/results/229-all-split-original-a7-cost-pilot.json) passes its exact deterministic comparison and unchanged cost
gate. The distinct original **full 8192-sample A7 acquisition** in [230](lanes/n010-comparison-readiness/results/230-all-split-original-a7-full-control.json)
completes, then analysis stops at omitted geometry-hash metadata. No native
retry: post-hoc [231](lanes/n010-comparison-readiness/results/231-posthoc-original-a7-retained-control.json) validates the SAME raw data against unchanged
original analytic and independent 16384-sample iid controls. It PASSES.
Analytic indirect region-relative error **1.04251e-5**, NRMSE **0.000444197**;
iid per-channel mean difference **9.35685e-5**, full-image NRMSE **0.00714405**.
Original deterministic means/second moments and primary bytes match. The
outer native duration was not saved before the analysis crash: **NOT RETAINED**,
not reconstructed from the sizing estimate. All failed records remain.

[233](lanes/n010-comparison-readiness/results/233-posthoc-all-split-general-controls-replay.json) post-hoc rehashes **718 immutable payloads**, replays retained
218 statistics and nine complete byte comparisons, confirms **18 terminated
compiler/native identities**, and checks the actual **10/17 original full
control scenes**. This checkpoint precedes the new live acquisition below.
The seven pending scenes are A6a, A6b, A6b_level5_diag, A6c, A10, sealed-dark,
sealed-lit. Full A6b independent iid, numerical-bias assessment, all-state/
exact-prefix and whole-frame feasibility are still required.

[232](lanes/n010-comparison-readiness/results/232-all-split-original-a6c-cpu-cost.json) measures original A6c on all pixels/four seeds at eight samples:
**1.898731 CPU / 1.910170 elapsed seconds**. Conservative 8192-sample scaling
is about **1944 CPU / 1956 elapsed seconds** (~32.6 minutes), a workload sizing
estimate, not an N010 completion forecast or a physical PASS. [086](lanes/n010-comparison-readiness/experiments/086-original-a6c-full-physical-control.md)
prospectively bounds a single original full A6c run at one CPU, nice 15,
4 GiB, 3600 CPU / 5400 elapsed seconds, no retry or following queue.

**Currently RUNNING: [234](lanes/n010-comparison-readiness/results/234-all-split-original-a6c-full-physical-control.json)**, exact original A6c 8192 samples, four
seeds, whole 128×96. Native PID **69782**, start ticks **473962**, verified live
at **2026-10-17 04:40:30 UTC** from matching `/proc` identity; tool session
**78104**. Resume by observing this same acquisition, never starting another
because a poll expires. Its outcome is **UNMEASURED / INCOMPLETE** while live.
One CPU only, no GPU, app/display/clock/power changes. No automatic next run.

References remain **16/24**, timing208 remains **FAIL**, direct-error-1.0 pixels
remain **UNRESOLVED / 未解決** and included. Original seeds/slots/cap/thresholds
and final quality/time/true-peak gates remain. Unit/regression tests NOT RUN.
N010 is NOT_READY; a physical control PASS is no Lane M GI superiority claim.

### Evidence and preserved boundaries

- Exact 180 SHA256: `f52002b46754152f02ef6111863f7776b5404d2b4673d201b20d4fb253d808ef`.
- Exact 185 SHA256: `58dba169986246adc16898e89f351d6ca1643d6e16a9f247e6934183f3838b32`.
- Exact 191 SHA256: `448a0bd9f36e94dd3b487d7e805073a5efa2286ea281452a76a8b067bfb28f5c`.
- Complete physical 163 and state/prefix 164 remain valid for their failed
  sampler's scope; they do not override 180 or attest a new sampler.
- Prior 165/172 stops and 171/176 receipts, historical host/session 181/182,
  178 restoration failure, all negative sampler/GPU-port and quality results
  remain in immutable result records and Git history. No display, desktop
  window, power or clock setting changes occur in the current work.
- Original seeds, 24-slot corpus, six levels/cap, support/absolute/relative
  gates, all-pixel scoring, quality targets, full GPU precision and true-peak
  memory requirements remain. No N011, Actions, default Renderer promotion or
  N001–N009 result changes. Unit/runtime regression tests are **NOT RUN**.

### Execution order

1. Identify dominant depth/weight or measurement-cadence mechanisms using
   bounded diagnostics, then decide the smallest supported repair.
2. Complete the unchanged pending reference ladders and full timing proof.
3. Finish whole-corpus quality/true-peak pilots and execute all six final gates.
4. Publish N010 decision and distinct Lane M handoff; incumbent losses are
   valid comparison outcomes and do not require another preparation study.

## Phase 1 — establish competitiveness

**Question:** Under a valid quality reference and a fair end-to-end measurement boundary, how competitive is the current Renderer?

- [Issue #4 / N007](https://github.com/owoDra/real-time-gi-lab/issues/4) is **CLOSED as bounded NO GO**: moving-rigid CPU reference remained fully black through the frozen four-seed 512–8192-SPP ladder, while a probe-shadow counterfactual explained 9,247/9,247 positive pixels in the current GPU diagnostic frame. [Result 012](lanes/n007-reference-validity/results/012-n007-bounded-no-go-decision.md) preserves unmeasured regimes and frozen N006 outcomes. [Issue #5 / N008](https://github.com/owoDra/real-time-gi-lab/issues/5) concluded: independently validated oracle GO ([Phase A result 004](lanes/n008-hdr-oracle/results/004-phase-a-exit-decision.md)), cross-class reference set bounded NO GO ([final result 011](lanes/n008-hdr-oracle/results/011-n008-final-decision.md)). These studies remain closed research outcomes; a statistical screen does not replace physical validity.
- **N009 concluded (2026-10-14): SC NO GO / BF1–BF3 PASS / PT INCOMPLETE.** [Final result 009](lanes/n009-scene-contract/results/009-n009-final-decision.md). Under C1, C1/C2/C4/C5/C6 have full total support but only deterministic direct references; both T_B2/T_B8 totals fail the unchanged four-seed 8192-SPP cap. Amendment 1 leaves C3 light motion NOT_CONSTRUCTIBLE. BF gates pass on C7; C7 V1 and old B4 V3 failures prevent COMPLETE attribution. Excluding 21 V1 pixels is post-hoc sensitivity. Sponza direct max-relative-error-1.0 pixels remain unresolved (未解決).
- **N010 is the final preparation gate (active):** [preregistered protocol](lanes/n010-comparison-readiness/experiments/001-comparison-readiness.md). Finish reference eligibility, direct/key correctness diagnostics, RC/path-tracing executable controls, matched HDR quality scoring, complete Renderer GPU timing calibration and allocation-lifetime memory accounting here. Require an executed comparison pilot and fail-closed readiness preflight; plans alone cannot pass. N009's negative result and thresholds remain frozen. C1/BF-P default adoption requires a separate architecture decision and executable checks.
- **N010 execution progress:** C7 now has qualified T_B2/T_B8 references and an executed PT budget ladder with quality passes; incumbent/dense RC losses are retained. Construction corpus is locked through C12. Controlled dynamic comparisons and C8/C9 matching budget ladders are complete. Sponza C1 T_B2 now has an eligible reference: incumbent indirect NRMSE 88.8399% / bias +35.8544% is FAIL; pixel PT passes at 256/1024 spp. Remaining Sponza qualification/pilots and full Renderer timing calibration are required; quality failure does not reopen preparation. [Interim comparisons](lanes/n010-comparison-readiness/results/033-interim-comparison-findings.md).
- **N010 timing capability remains an open gate.** Independent [plan 048](lanes/n010-comparison-readiness/experiments/048-prospective-bulk-pfm-calibration-output.md) prepares identical-byte row-bulk image output after post-hoc 162; it must still pass fresh full-boundary sizing/calibration, without threshold changes or transferring earlier diagnostic timing into accepted evidence. Build 167 and sizing 168 PASS; full calibration 169 completes with 2 PASS / 14 FAIL and is not accepted. Diagnose environment prospectively without changing the original gates.
- **Immediately after N010: Lane M GI competitiveness.** Use a distinct lane-m-gi-competitiveness identity and preserve the historical Lane M topology study. Execute comparisons on the frozen corpus; report quality failures as losses, without opening N011 or another preparation lane. Initial executable cohort is incumbent/vanilla RC and pixel path tracing; DDGI/RTXGI is the additional named family to integrate and qualify before the accepted Lane M comparative campaign. Report supported regimes/devices honestly.
- Compare on several representative scenes and dynamic classes, not just Sponza.
- Establish fair image quality, GPU time, persistent/true-peak memory comparisons to representative existing GI families.
- Identify the largest reproducible weaknesses, including HWRT-free devices and renderer motion artifacts.

**Exit:** defensible image-reference eligibility, matched comparison protocols, retained evidence, and an ordered list of architecture-level bottlenecks. No favorable general superiority claim from inadequate baselines.

## Phase 2 — investigate structural improvements

**Question:** What new light-transport/representation/reuse design can move the demonstrated quality–cost frontier meaningfully?

- Propose studies only for the major bottlenecks observed in Phase 1.
- Treat Split RC, HWRT, virtual pages, sparse hash, temporal reuse, traversal and directional sampling as interchangeable techniques.
- For each study pre-register the hypothesis, exact correctness/quality/performance/memory gates, comparison incumbent and bounded stop criteria.
- Defer small local GPU tweaks that cannot materially change the full-system tradeoff.

**Exit:** one or more demonstrated end-to-end structural advances versus the frozen incumbent, or an explicit negative conclusion.

## Phase 3 — demonstrate reproducible competitiveness

**Question:** Does a complete practical GI Renderer substantiate benefits across diverse workloads?

- Reproduce on multiple GPU classes, clearly separating HWRT and software-only pathways.
- Verify dynamic geometry, lights, camera movement, occlusion changes and varied spatial scale.
- Deliver a working interactive or captured renderer demo with exact configs and repeatable comparisons.
- Publish honest image-quality, total GPU-frame-cost and true-peak memory comparisons against representative baselines.

**Exit:** practical demo plus defensible, independently repeatable advantage with clearly declared scope, or a qualified failure/partial tradeoff.

For current conclusions use [status.md](status.md); for measurement details use [protocol.md](protocol.md).

N010 has executed the controlled dynamic cohort (results 019/020) with all
source, first changed and recovery frames retained. Quality failures are
comparison outcomes, including overestimation after light motion; they do not
create an N011 preparation lane. Complete Sponza reference qualification,
fixed-ladder quality matching, actual full Renderer timing calibration and
fail-closed Lane M handoff here. The required DDGI integration is pinned to
RTXGI Vulkan on AMD (result 021); CUDA is not part of the comparator.

### N010 acquisition interruption recovery

065 retains terminal/partial attempts with unestablished cause. Prospective
Amendment 8 and view 067 recover complete prefixes into fresh directories with
unchanged 24-slot corpus, screens and cap. The idle continuation-v3 was retired
without jobs (120); the user requested stopping both old CPU recovery jobs (124).
Complete 65536 levels and partial 131072 outputs remain; no cap failure is claimed.
READY still requires all references, full pilots and accepted calibration.
GPU binary64 execution feasibility 070 is only a small numerical diagnostic,
not admitted reference evidence. N010 remains the last preparation study;
continue directly to the distinct Lane M GI comparison lane after its gate.

GPU reference feasibility follow-up 082 has now completed but failed fixed
numerical conformance on C1 T_B8 seed 0. No GPU reference is admitted;
post-hoc sampling diagnosis (plan 022 / map 084) runs separately from the
live unchanged CPU qualification. This failure does not create another
preparation lane or relax the all-24-reference readiness requirement.

Post-hoc deep-port diagnosis 091/092 establishes a signed-zero basis mechanism
on eight retained paths; it does not repair the Renderer's unresolved direct
pixels. Whole-path CPU fallback candidate 093 passes selected feasibility.
Separate streamed build 095 and full-frame plan 025 preserve all original
admission gates; no GPU reference transition before complete validation.

The [N010 completion inventory](lanes/n010-comparison-readiness/results/102-completion-evidence-and-handoff.md)
provides the remaining gate sequence and runnable final preflight. Executed
full-gate interim preflight 103 is NOT_READY, retaining missing full references,
Sponza pilots and accepted calibration as explicit unfinished work. Complete
these gates in N010, then register and execute the distinct Lane M comparison.

Prospective N010 plan 029 provides a gated high-sample hybrid acquisition
command after complete numerical, physical and all-state/prefix proof. Its
historical prerequisite checks 104–106 refused dispatch while 098 was incomplete; no reference admission follows
from prepared code. Any scheduling transition must retain the original CPU
evidence and occur with an executed completed-boundary provenance record.

Full numerical 098, physical 099 (68 cases/eight controls) and all-state/prefix
101 (96 low-dose/eight actual-level cases, 304 attempts) now complete PASS.
Fresh hybrid acquisition 121 runs. Its first qualified C4 B2 reference passes
complete new-variant provenance 123 with 5,413 unchanged read identities.
This single reference does not complete the full-corpus N010 gate.

A separate prospective CPU sampling proposal (plan 030, build 112) preserves
the finite-transport physical target while mixing cosine and geometry/direct
surface sampling with explicit null samples and importance weights. Physical
controls 113 acquired all seventeen scenes but failed in the analysis adapter
on an omitted metadata field. Original FAIL is retained. CPU-only post-hoc
replay 125 passes the unchanged eight physical/two iid gates on those same bytes.
Plan 036's fresh all-state/own-prefix proof 126 now completes PASS (24 low-dose,
two actual-level cases and all 78 native attempts); complete proof-chain audit
131 also passes. One fresh nine-slot acquisition 128 is actually executing.
Four seeds, six levels, support-aware screens and cap remain unchanged. No
point-guided corpus reference is yet qualified.

The first four-seed point-guided C1 B8 level at 8192 spp has now completed:
absolute/relative active p99 uncertainty 1.28593e-4 / 9.63962% fails both fixed
gates. Post-hoc [136](lanes/n010-comparison-readiness/results/136-first-point-guided-level-provenance-and-precision.json)
passes complete prefix provenance but finds worse first-level precision than
the original sampler. The completed 16384 level also fails absolute/relative
p99 gates (9.06741e-5 / 6.79678%); full two-level provenance passes in
[137](lanes/n010-comparison-readiness/results/137-second-point-guided-level-and-cpu-budget.json).
The 32768 level was interrupted by the user-requested stop (148), not completed.
Observed aggregate child CPU time also identifies
a possible operational guard interruption at high levels. Resolve that budget
prospectively while retaining own prefixes, scientific gates, sample cap and
all outcomes; no runtime limits have been changed. Forecasts do not establish
either an interruption or statistical cap failure. Full qualification is pending.
Prospective [plan 039](lanes/n010-comparison-readiness/experiments/039-operational-cpu-budget-continuation.md)
registers a clean completed-prefix workflow transition and fresh-process CPU
ceiling consistent with sixteen threads and the unchanged wall guard. Actual
[141](lanes/n010-comparison-readiness/results/141-operational-budget-capability-and-program-assembly.json)
passes fresh-child resource capability and guarded source assembly. The user's
later stop request terminated both reference acquisitions and all old
launcher/waiter processes ([148](lanes/n010-comparison-readiness/results/148-user-requested-reference-workflow-stop.json));
470 payload files remain retained. No 138/139/140 transition executed and no
statistical cap failure is claimed. There is no live comparison or handoff waiter.

The separate prospective [plan 040](lanes/n010-comparison-readiness/experiments/040-prospective-light-surface-reference-sampling.md)
light-surface proposal has complete sampling-only [build 144](lanes/n010-comparison-readiness/results/144-light-surface-proposal-build.json).
Complete physical [145](lanes/n010-comparison-readiness/results/145-light-surface-physical-controls.json)
and all-state/prefix [146](lanes/n010-comparison-readiness/results/146-light-surface-all-state-and-prefix.json)
pass. Bounded [147](lanes/n010-comparison-readiness/results/147-light-surface-bounded-feasibility.json)
fails the exact <=0.75 ratio at both levels: 0.7575396423 / 0.7462398911.
This candidate stops; the prepared conditional plan 041 is inactive. Its two
reference screens are INELIGIBLE, and no cap failure is claimed. The frozen
24-slot scope, eligibility and comparison gates remain. Actual
[149](lanes/n010-comparison-readiness/results/149-light-surface-corpus-prerequisite-refusal.json)
refuses new corpus acquisition. Prospective
[042](lanes/n010-comparison-readiness/experiments/042-prospective-independent-quiet-calibration.md)
uses the now-idle research host for the separate quiet Renderer calibration
requirement before further reference computation. [Quiet sizing 046](lanes/n010-comparison-readiness/results/046-calibration-quiet-sizing.json)
now passes all sixteen boundaries. The user stopped accepted 029 and its
three-process tree ([150](lanes/n010-comparison-readiness/results/150-user-requested-calibration-stop.json)).
Both completed C1 HWRT/software boundaries fail five unchanged gates; the full
calibration is INCOMPLETE. Preserve every sample and diagnose the measurement
procedure before a separately registered repair. No old acquisition is restarted.
A valid full calibration remains required; no campaign admission follows.


Prospective [043](lanes/n010-comparison-readiness/experiments/043-prospective-primary-direction-reference-sampling.md)
implements a distinct primary-position directional proposal. Sampling-only
[build 151](lanes/n010-comparison-readiness/results/151-primary-direction-proposal-build.json) passes;
physical 152 was user-stopped in 161 after seven complete scene rows; full
physical validity remains INCOMPLETE. State/prefix 153 and bounded feasibility
154 were not run and require complete preceding PASS. Feasibility compares against the original
cosine method, requiring <=0.75 uncertainty ratios at both original levels.
No reference admission, old-process restart or relaxed final gate follows.
Post-hoc [155](lanes/n010-comparison-readiness/results/155-stopped-calibration-posthoc-diagnosis.json)
records large inter-frame capture volume/cadence and append-order variation;
it establishes no timing-failure cause. A separate prospective capture repair
must preserve full workload boundaries, images, scratch, memory and thresholds.


Prospective [044](lanes/n010-comparison-readiness/experiments/044-prospective-minimal-calibration-capture.md)
now implements that separate image/scratch-only calibration fixture. CPU
[build 156](lanes/n010-comparison-readiness/results/156-minimal-calibration-fixture-build.json) passes
all five compile/link steps, inverse source checks and unchanged-active-input
hashes. Its separate binaries retain the timed Renderer method and all shaders.
The prepared calibration wrapper keeps the original full schedule/statistics,
requires all sixteen boundaries, checks every frame against immutable 046 image
hashes, replays allocation ledgers and refuses other research workers. CLI
assembly (`--help`) succeeds; no GPU image-equivalence or new calibration run
has occurred. Fresh quiet sizing 157 and accepted 158 remain unexecuted until
the CPU proposal work actually terminates. Existing 029 remains partial/failed
in its completed scope. Neither build success nor a prepared command is READY.


Subsequent CPU review found that pixel PT's removed state-copy call also created
its frame directory. [045](lanes/n010-comparison-readiness/experiments/045-minimal-capture-output-directory-repair.md)
registers that filesystem repair before any new GPU run. Corrected isolated
[build 159](lanes/n010-comparison-readiness/results/159-minimal-calibration-directory-fix-build.json)
passes all five compile/link steps and unchanged-active-input checks; the
calibration wrapper now requires its v2 binaries. Build 156 and its known
source-identified defect are retained unchanged; no runtime failure was observed
or hidden. GPU sizing 157 / calibration 158 remain unexecuted at build publication. The
user subsequently stopped the physical-152 process tree (161); all 171 saved
payload/log/status files remain retained and no old workflow is restarted.

Plan 032 prepares point-guided acquisition of every unfinished transport,
retaining the fifteen eligible original-method references within the full
24-slot corpus. Actual 116 refuses acquisition at incomplete physical 113;
its exact read bytes are retained. API delegation 117 passes the existing
fifteen-slot subset; that historical check did not execute the new-variant branch
(now exercised by first-level audit 136). The
old acquisition queue terminated on the 113 failure without dispatch. A fresh
plan-036 queue executed 128 after complete 125/126 PASS and was later stopped in 148. Neither queue,
prepared provenance nor a subset audit passes final comparison readiness.

Separate final-preflight adapter 033 reuses the exact original six-gate source
with new reference-provenance dispatch. Actual interim 119 is NOT_READY with
the same six gate classifications as 103. This prepares final integration
without changing the frozen current driver, reference view, scoring/timing
thresholds or absent final 047. A recorded reference/scheduling transition
and complete actual comparison/calibration evidence are still required.

Plan 037 fixes fresh full view 127: fifteen unchanged original eligible targets
and all nine plan-036 point-guided targets, before their qualification outcomes
or new GI scores. A fresh comparison driver waits for complete eligibility,
all-payload provenance and actual quiescence before the unchanged C1 B8 ladder,
Sponza dynamics, quiet sizing, accepted calibration and final six-gate preflight.
Executed current-view interim 129 remains NOT_READY. See
[130](lanes/n010-comparison-readiness/results/130-validated-reference-acquisition-and-comparison-transition.md)
for current execution and remaining gates. N010 remains the final preparation.

Plan 038 now supplies an actual waiting quiescence-transition worker: after
complete selected qualification and all 24 provenance checks, retire only the
redundant independent hybrid acquisition, preserving all complete/partial
bytes and confirming process termination. It does not signal selected-reference
work or bypass final pilots/calibration. Retirement 135 remains pending.
Post-hoc memory audit 133 verifies current allocation-hook link coverage and
the 16 current-binary diagnostic ledgers, while preserving 65 historical-binary
pilot identities and the failed stricter audit 132. These results do not pass
accepted timing or whole-corpus readiness. [Details](lanes/n010-comparison-readiness/results/134-memory-evidence-scopes-and-quiescence-watch.md).



Current reference view [160](lanes/n010-comparison-readiness/results/160-primary-direction-reference-view.json),
prospectively registered in [plan 046](lanes/n010-comparison-readiness/experiments/046-prospective-directional-corpus-admission.md),
reverifies all sixteen already eligible references: fifteen original CPU slots
and the previously qualified hybrid C4 B2 slot. All 6,043 recorded input hashes
were rechecked unchanged at the stop checkpoint. The full 24-slot map retains
eight pending targets (C1/C2/C3/C4 B8, C5/C6 both transports); no new proposal
reference is admitted. Historical view 127 and all failed/partial acquisitions
are retained. Whole-corpus readiness remains NOT_READY.

User-requested stop [161](lanes/n010-comparison-readiness/results/161-user-requested-directional-workflow-stop.json)
records verified termination of the three physical-152/controller/native
processes and two empty post-stop research-worker scans. Seven of seventeen
scene rows passed; A6a was interrupted, and the final eight physical checks,
two iid crosschecks, state/prefix 153 and feasibility 154 remain uncompleted.
The controller's saved RUNNING label is stale after actual PID termination.
This is an operational interruption, not a scientific FAIL or a cap failure.
The stopped workflow is not restarted; no threshold or final gate is relaxed.



Fresh isolated-fixture GPU [sizing 157](lanes/n010-comparison-readiness/results/157-minimal-calibration-quiet-sizing.json)
now completes all sixteen original boundaries with PASS, including static and
first-target churn roles. Every saved direct/indirect/total image matches the
corresponding immutable original-046 image; all scratch witnesses and owned
allocation-ledger replays pass with zero teardown within 8 GiB. The original
three-dose sizing schedule, +20% target and dose cap are unchanged. This is
actual GPU sizing/image equivalence, not accepted timing capability.

Separate accepted calibration 158 has started with those frozen doses and the
original eight-process schedule and thresholds. Its C1 HWRT, software and PT B2
boundaries completed all eight blocks and **FAIL**; remaining boundaries are
still running at this checkpoint. Removing bulk diagnostic output alone has
not established the required timing precision. Retain every subsequent row,
earlier 029 failures and all raw samples. No retry, correction or threshold
relaxation follows from this partial observation. Final 047 remains pending.



Prospective [recovery plan 047](lanes/n010-comparison-readiness/experiments/047-prospective-directional-control-recovery.md)
prepares an explicit fresh control workflow after user interruption 161. It
imports all seven completed scene exports byte-for-byte, retains their actual
native commands as imports, acquires the other ten scenes once at new paths,
and applies the complete unchanged seventeen-scene/eight-physical/two-iid gates.
Separate 163/164/165 artifacts are required; old partial 152 and absent 153/154
are never rewritten or relabelled. Guarded program assembly and Python source
compilation succeed, with row numerical/analytic/iid source checks unchanged.
No recovery acquisition/import branch, reference admission or new CPU worker
has executed. Each entry point refuses other research workers and existing
paths; GPU calibration 158 must actually terminate before CPU dispatch.



[Plan-047 Amendment 1](lanes/n010-comparison-readiness/experiments/047-prospective-directional-control-recovery.md)
now supplies the explicit recovered-chain provenance API and eight-slot
qualifier. It requires 151/163/164/165, checks the seven imported actual
commands/payloads and ten fresh physical invocations, and replays the original
feasibility/native-prefix/resource proof. Source comparison confirms that the
original numerical gates and complete ladder program are byte-identical after
only declared proof/file dispatch, quiescence and fixed-output guards. CLI
assembly passes. No numerical/import/admission branch or new sample has run;
163/164/165/166 remain absent, and the original API still refuses partial 152.
The sixteen retained slots, eight pending slots, view 160 and all final gates
are unchanged. Current calibration 158 has completed ten static boundaries:
C1 PT B8 passes; the other nine fail. Its six churn boundaries remain pending
and the overall acquisition is still INCOMPLETE.



CPU-only post-hoc [diagnosis 162](lanes/n010-comparison-readiness/results/162-minimal-static-calibration-posthoc-diagnosis.json)
archives an exact 158 summary snapshot and replays all ten completed static
boundaries, eight blocks and 64 samples per block (5,120 raw samples). Every
original decision is reproduced: C1 PT B8 passes, the other nine fail. All
schedules and producer image/scratch/ledger metadata match. Payload content
hashes are not independently rechecked in this diagnostic.

Compared descriptively with the earlier 155 block-0 record, C1 HWRT/software
completed-output cadence medians fall from 394/498 ms to 9.30/12.57 ms; saved
frame bytes are about 2.14 MB, versus at least 69.06 MB for just the old three
secondary streams. These are different retained acquisitions, not a causal
isolation or directly measured GPU duty cycle. Timing gates still fail for
those roles. C1 PT B2 also fails with a GPU-duration/file-cadence proxy near
0.967; C1 PT B8 passes near 0.998. This does not identify a clock/power cause
or justify a correction, exclusion, threshold change or repeated acquisition.
The lightweight CPU diagnostic ran during ongoing 158; it launched no CPU
reference acquisition or GPU experiment. All six churn boundaries remain in
the original full acquisition; 162 does not pass full timing capability.
