# Current research status (2026-10-17)

## Current execution checkpoint — 2026-10-17 JST

**N010 remains NOT_READY.** User resumed work for cause diagnosis and the
shortest valid completion path, with low interactive load. No old stopped
acquisition or waiting queue is restarted. Bounded CPU and short C7 GPU
diagnostics have completed; neither supplies the missing readiness proof.
Original full A6c native234 completed; [post-hoc237](lanes/n010-comparison-readiness/results/237-posthoc-original-a6c-retained-control.json)
repairs only missing summary metadata and passes the unchanged analytic gates.
Actual original full physical inventory is **11/17**. No native was retried.
[Cost inventory236](lanes/n010-comparison-readiness/results/236-all-split-remaining-controls-cpu-cost.json)
completed all six scenes in175.254CPU/176.121elapsed seconds, one low-priority
core. The three full multibounce sphere cases project about12CPU hours each;
all six remaining artifacts project36.984CPU hours. These are low-count cost
projections, not full-run evidence or an N010 ETA. Execution optimization
precedes any long full control. No acquisition or GPU/full-control queue runs.

[Traversal prototype238](lanes/n010-comparison-readiness/results/238-near-first-cpu-bvh-prototype.json) passes51,047,139 closest/
2,368,308 occlusion identity pairs and exact223/A6a payload checks. Cost
41.859831/42.641725=0.981664 fails its prospective<=0.75 execution condition;
stop this candidate before full controls. This single-run sizing comparison
does not demonstrate a speedup. [Original profiles240](lanes/n010-comparison-readiness/results/240-original-all-split-cpu-profile-local-linker.json)
complete with exact A6a payloads. [Post-hoc inline attribution241](lanes/n010-comparison-readiness/results/241-posthoc-cpu-profile-inline-attribution.json)
uses an unexecuted debug companion with identical .text bytes/addresses/symbols.
A6a/C1 samples: BVH slab45.79/46.98%, remaining traversal27.51/26.51%, triangle
intersection18.23/18.40%. All4256/3342 original samples remain denominators;
77/75 unannotated samples retained. Zero reported lost samples. This diagnoses
CPU reference cost, not GPU precision or GI superiority. [SIMD slab243](lanes/n010-comparison-readiness/results/243-simd-slab-neutral-padding-prototype.json)
passes8,575,080,199 visited-box comparisons,53,415,447 query comparisons and all
original223/A6a output/audit checks. But standalone A6a38.495451CPU seconds /
retained42.641725=0.902765 FAILS its prospective<=0.75 execution condition;
stop this candidate too. Prior242 padding failure is retained;095 is an explicit
implementation amendment, with no scientific gate change. These uncontrolled
single-run cost probes do not establish a speedup. [Batched-box245](lanes/n010-comparison-readiness/results/245-batched-box-verifier-repaired-prototype.json)
passes12,013,100,580 acquired /4,763,926,019 cached box comparisons and all
53,415,447 queries/original outputs, but A6a44.446001/42.641725=1.042312
fails<=0.75; stop it too. Original244 verifier compile error retained;097 is
an explicit verifier-only build repair, not a scientific gate change. Neither
SIMD design supplies sufficient execution scaling. No full-control queue.
[Four-frame mean247](lanes/n010-comparison-readiness/results/247-four-frame-c7-precision-diagnostic.json)
completes2048 raw frames/512 observations,6/7 precision gates PASS but control
order bias1.024851>1.02 FAIL. [Symmetric interleaved248](lanes/n010-comparison-readiness/results/248-interleaved-four-frame-c7-precision-diagnostic.json)
also completes2048 raw frames,4/7 gates PASS; control envelope1.029850,
span1.040768,order bias1.023116 FAIL. Both methods stop; dose1301 remains frozen
from246. All individual timestamps/images/scratch/owned ledgers retained,
owned peak516,167,104bytes and teardown zero. No single-frame precision or
all16 transfer is claimed. Averaging and symmetric positions have not supplied
accepted timing or established its cause. Next inspect read-only GPU telemetry
capability and actual timing alignment before another measurement design.
No full campaign or native/GPU research worker remains.

[Read-only observation235](lanes/n010-comparison-readiness/results/235-posthoc-natural-idle-read-only-observation.json)
retains30.157s of user-declared idle DRM activity; other-app counters increased,
eight same-UID PIDs inaccessible. No paired precision or causal verdict.

See [cause review 192](lanes/n010-comparison-readiness/results/192-cause-review-and-shortest-valid-completion.md)
and [prospective bounded plan 057](lanes/n010-comparison-readiness/experiments/057-bounded-cause-diagnosis-and-critical-path.md).

| Required item | Actual current evidence | Remaining work |
| --- | --- | --- |
| All 24 eligible references | [160](lanes/n010-comparison-readiness/results/160-primary-direction-reference-view.json): sixteen eligible, eight pending | Resolve the dominant uncertainty mechanism; validate any distinct sampling method before all fixed pending ladders. |
| Stopped first-direction guide | [180](lanes/n010-comparison-readiness/results/180-primary-direction-second-stop-bounded-feasibility.json): **COMPLETE / FAIL**, 8192/16384 ratios **1.0703554221788882 / 1.0599135470235277** against <=0.75 | Candidate rejected; 166 NOT RUN and blocked by its genuine FAIL. This is not a full statistical-cap failure. |
| Whole-path reference candidate | [223](lanes/n010-comparison-readiness/results/223-all-split-general-transport-equivalence.json): exact legacy equivalence; [225](lanes/n010-comparison-readiness/results/225-all-split-full-sidedness-controls.json)/[226](lanes/n010-comparison-readiness/results/226-all-split-full-deterministic-controls.json)/[231](lanes/n010-comparison-readiness/results/231-posthoc-original-a7-retained-control.json)/[237](lanes/n010-comparison-readiness/results/237-posthoc-original-a6c-retained-control.json): 11/17 original full controls PASS | [234](lanes/n010-comparison-readiness/results/234-all-split-original-a6c-full-physical-control.json) native0 / retained237 analytic PASS; six remaining originals, A6b IID, bias, all-state/prefix and feasibility remain. |
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

### General adapter and original physical controls — A6c completed

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
control scenes**. This checkpoint preceded234.
At233 the seven pending scenes were A6a, A6b, A6b_level5_diag, A6c, A10, sealed-dark,
sealed-lit. Full A6b independent iid, numerical-bias assessment, all-state/
exact-prefix and whole-frame feasibility are still required.

[232](lanes/n010-comparison-readiness/results/232-all-split-original-a6c-cpu-cost.json) measures original A6c on all pixels/four seeds at eight samples:
**1.898731 CPU / 1.910170 elapsed seconds**. Conservative 8192-sample scaling
is about **1944 CPU / 1956 elapsed seconds** (~32.6 minutes), a workload sizing
estimate, not an N010 completion forecast or a physical PASS. [086](lanes/n010-comparison-readiness/experiments/086-original-a6c-full-physical-control.md)
prospectively bounds a single original full A6c run at one CPU, nice 15,
4 GiB, 3600 CPU / 5400 elapsed seconds, no retry or following queue.

**234 native completed**, original8192/fourseed/whole128×96. Native PID69782/
start473962 is terminal. Actual1331.127171410elapsed/1325.210989000CPU sec;
all25 payload identities and return0 were saved before a run_counters summary
KeyError.234 preserves that metadata failure. [237](lanes/n010-comparison-readiness/results/237-posthoc-original-a6c-retained-control.json)
explicitly replays the same data with only that missing field added, exact
analysis inverse and immutable payload checks. Direct geometric violations0;
indirect relative8.1611197802e-5,NRMSE0.00138358751045: original gates PASS.
11/17 full artifacts complete; A6a,A6b,A6b_level5_diag,A10,sealed-dark/lit
remain.087/089/236 completed their cost-only inventory, no full acquisition.
The three8192 multibounce sphere controls project roughly12CPU hours each;
all six remaining artifacts36.984CPU hours. Optimize execution before those
long controls. These cost probes add no physical or reference admission.

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

## Current incumbent — adoption versus experiments

**Active work: N010, the final comparison-preparation study.** [Protocol](lanes/n010-comparison-readiness/experiments/001-comparison-readiness.md). User-directed sequence is N010 → Lane M GI competitiveness; no further N-series preparation lane. Readiness requires an executed quality/time/memory pilot, physically validated eligible references and full Renderer timing calibration. Historical Lane M topology results retain their identity. N010 has not yet passed its readiness gate.

### N010 findings and remaining completion gates

The RC/path-tracing comparison cohort executes on AMD/Vulkan. Incumbent quality
failures are measured losses; N010 does not require an incumbent win before
Lane M starts. All scored pixels and earlier failed budgets remain retained.

| Executed comparison | What the evidence establishes |
| --- | --- |
| Sponza C1 T_B2 | Incumbent indirect NRMSE 88.8399% / sum bias +35.8544%: FAIL. GPU pixel PT passes at 256 and 1024 spp ([031](lanes/n010-comparison-readiness/results/031-c1-b2-pt-quality-ladder.json), [032](lanes/n010-comparison-readiness/results/032-c1-b2-cohort-scores.json)). |
| Sponza C3 T_B2 | Incumbent indirect NRMSE 87.9404% / bias +35.2394%: FAIL; PT 256/1024 passes ([041](lanes/n010-comparison-readiness/results/041-c3-b2-corpus-scores.json)). |
| Controlled C7 | Incumbent misses roughly 91% of one-bounce indirect energy; dense repository RC also fails. PT passes at 256 spp T_B2 / 1024 spp T_B8 ([013](lanes/n010-comparison-readiness/results/013-c7-pt-cohort-pilot.json), [015](lanes/n010-comparison-readiness/results/015-dense-rc-pilot.json)). |
| Controlled dynamics | All 145 original cohort images are scored; all 29 memory ledgers replay to zero within the cap. C9 incumbent energy is about 7.645× the reference. C8/C9 complete ladders select 1024 spp for both transports; T_B2 PT 1024 confirmation passes all 25 dynamic frames. Earlier PT 256 losses remain ([033](lanes/n010-comparison-readiness/results/033-interim-comparison-findings.md), [042](lanes/n010-comparison-readiness/results/042-controlled-pt-budget-confirmation-summary.json)). |

Current checkpoint: **NOT READY**. [Current-view preflight 129](lanes/n010-comparison-readiness/results/129-replayed-view-interim-preflight.json)
and the [execution transition record 130](lanes/n010-comparison-readiness/results/130-validated-reference-acquisition-and-comparison-transition.md)
identify the remaining requirements. No pilot timing is yet accepted as a
calibrated superiority comparison.

First point-guided C1 B8 level (four seeds, 8192 spp) is **INELIGIBLE**:
active absolute p99 uncertainty is 1.28593e-4 and relative p99 is 9.63962%,
above the unchanged 1e-5 / 5% gates. Post-hoc CPU audit
[136](lanes/n010-comparison-readiness/results/136-first-point-guided-level-provenance-and-precision.json)
passes full prefix provenance, not reference eligibility. These uncertainty
statistics are 1.781× / 1.868× the original sampler at the same level;
the new sampler has not demonstrated improved precision. About 80.63% of paths
terminate with a guided null continuation; preceding radiance contributions
are retained. This is diagnostic, not proof of bias or cap failure. The next
16384-spp level also fails both gates: absolute p99 9.06741e-5, relative p99
6.79678%. Full two-level provenance passes in post-hoc CPU audit
[137](lanes/n010-comparison-readiness/results/137-second-point-guided-level-and-cpu-budget.json);
The later 32768-spp attempt was interrupted by the user's process-stop request,
not completed or classified. The audit also records an
operational CPU-budget risk: 42,294.43 aggregate CPU seconds for completed
children through 16384 spp projects linearly to about 338,355 CPU seconds for
the last interval, above the 172,800-second invocation guard. This includes
bookkeeping and is a resource forecast, not an observed interruption or
statistical cap failure. Resolve the budget prospectively before a conflicting
high-level invocation; current runtime limits and scientific gates are unchanged.
Prospective [plan 039](lanes/n010-comparison-readiness/experiments/039-operational-cpu-budget-continuation.md)
prepares a child-free, fully audited prefix handoff to a fresh process with
691200 aggregate CPU seconds and unchanged 43200 elapsed seconds / 4 GiB.
Actual CPU capability/program-assembly witness
[141](lanes/n010-comparison-readiness/results/141-operational-budget-capability-and-program-assembly.json)
passes: a fresh unprivileged Python child establishes the declared bounds,
and the guarded comparison/preflight programs assemble with all six gates.
This is not sampler execution or readiness. The user's subsequent process-stop
request terminated ten old native/launcher/waiter processes, including both
reference acquisitions and the plan-039 handoff monitors
([148](lanes/n010-comparison-readiness/results/148-user-requested-reference-workflow-stop.json)).
All 470 acquired payload files and mutable summary bytes were preserved.
No old research process remained at the stop check. There is no live automatic
handoff or comparison waiter; 138/139/140 were not executed. Interrupted
32768-spp outputs remain incomplete, and no statistical cap failure is claimed.

Separate prospective [plan 040](lanes/n010-comparison-readiness/experiments/040-prospective-light-surface-reference-sampling.md)
registers a light-visible-surface proposal for offline references, motivated by
the global guide's precision losses. It retains 75% cosine support and the
unchanged radiance evaluator, with explicit density correction.
[Build 144](lanes/n010-comparison-readiness/results/144-light-surface-proposal-build.json)
passes both standalone/prefix compilation and sampling-only source checks.
[Physical 145](lanes/n010-comparison-readiness/results/145-light-surface-physical-controls.json)
completes all seventeen scenes/four seeds, eight physical gates and two retained
iid comparisons with PASS. [State/prefix 146](lanes/n010-comparison-readiness/results/146-light-surface-all-state-and-prefix.json)
passes all 24 low-dose states, two actual C7 transports and 78 native invocations.
[Bounded feasibility 147](lanes/n010-comparison-readiness/results/147-light-surface-bounded-feasibility.json)
**FAILS**: absolute p99 ratios versus the original global guide are
0.7575396423 at 8192 and 0.7462398911 at 16384. Plan 040 requires <=0.75 at
both levels; 24.246% improvement at 8192 does not meet 25%. Both reference
screens also remain INELIGIBLE (9.74140e-5 / 7.47907%, then 6.76646e-5 /
5.32703%). The sequential job terminated without retry. No reference is
admitted, no cap failure is claimed, and the threshold is not relaxed.
The conditional [plan-041 intake](lanes/n010-comparison-readiness/experiments/041-prospective-light-surface-corpus-admission.md)
was prepared locally before those results but first committed after them; it is
inactive. Actual guard [149](lanes/n010-comparison-readiness/results/149-light-surface-corpus-prerequisite-refusal.json)
refuses dispatch on failed 147, with zero native attempts and no new corpus
root. The new-variant payload admission branch remains unexercised.
Existing references, all 24 required slots and every final readiness gate remain
unchanged. Prospective [042](lanes/n010-comparison-readiness/experiments/042-prospective-independent-quiet-calibration.md)
allows quiet full-boundary sizing/accepted calibration before further CPU
reference computation, with all original boundaries, thresholds and final
readiness gates unchanged. It does not dispatch a new quality pilot or admit
Lane M. The independent controller passed initial quiescence and
[quiet sizing 046](lanes/n010-comparison-readiness/results/046-calibration-quiet-sizing.json)
now completes all sixteen boundaries with PASS. The user subsequently stopped
[accepted 029](lanes/n010-comparison-readiness/results/029-full-renderer-calibration.json)
and its supervisor/native child ([150](lanes/n010-comparison-readiness/results/150-user-requested-calibration-stop.json)).
C1 HWRT and software completed eight blocks each and fail five unchanged timing
gates; C1 PT B2 retains five complete blocks. The full sixteen-boundary outcome
is INCOMPLETE, all bytes are preserved, and no old acquisition is restarted.
No accepted timing-capability PASS is established.


Separate prospective [plan 043](lanes/n010-comparison-readiness/experiments/043-prospective-primary-direction-reference-sampling.md)
registers a primary-position directional histogram for offline references:
16 by 16 cosine-domain bins, four deterministic pilot rays per bin, 50%
cosine support, density correction on the first continuation only. It uses
geometry/direct light, never candidate GI outputs; later bounces and the
physical evaluator stay unchanged. [Build 151](lanes/n010-comparison-readiness/results/151-primary-direction-proposal-build.json)
passes separate standalone/prefix compilation and reversible source checks.
Physical 152 was user-stopped in 161 after seven complete scene rows; the full
physical verdict is INCOMPLETE. State/prefix 153 and feasibility 154 did not run.
Only complete physical PASS could have permitted those later stages. The new feasibility baseline is the
**original cosine** 8192/16384 levels, with <=0.75 uncertainty ratios at both
levels; plan 040's worse global-guide baseline is not substituted. These are
CPU proposal checks, not eligible references or a new GI quality result.
No old acquisition is restarted. All 24 references and final gates remain.

Post-hoc CPU [155](lanes/n010-comparison-readiness/results/155-stopped-calibration-posthoc-diagnosis.json)
finds 64 distinct raw work-stream hashes despite identical HDR images in each
completed boundary's first block. Canonicalized first-two-frame ray work/hits
match after removing only append-position identity; raw contribution records
still contain that identity. Completed image-file cadence is about 394/498 ms
for HWRT/software while timed frames take milliseconds. This is saved-file
cadence, not a measured CPU-idle duration or proven cause of failed gates.
The capture source performs large diagnostic readbacks and file writes between
frames. Any capture repair requires prospective acquisition and unchanged
full boundaries/thresholds; no clock/power cause or calibration PASS is inferred.


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

Prospective [plan 048](lanes/n010-comparison-readiness/experiments/048-prospective-bulk-pfm-calibration-output.md)
prepares a separate row-bulk PFM fixture: the two per-pixel output loops become
one identical RGB row write, with no GPU/timestamp/frame-schedule change.
Source overlays reverse exactly to build-159 files and both CLI programs
assemble. Native build 167, full sizing 168 and accepted calibration 169 have
not run. Build refuses GPU/calibration work; new GPU acquisition requires
actual CPU/GPU quiescence, complete build and full sizing PASS. This tests
remaining CPU output overhead without claiming it caused earlier failures.
All original boundaries, samples, image/scratch/memory proofs and thresholds
remain required; 158 continues unchanged and its outcomes are retained.

| Completion requirement | Current state / next action |
| --- | --- |
| All 24 locked references | Fifteen original CPU references pass provenance [109](lanes/n010-comparison-readiness/results/109-existing-eligible-cpu-provenance-audit.json). Separate hybrid C4 B2 qualifies at 16384/32768 and passes full provenance [123](lanes/n010-comparison-readiness/results/123-first-qualified-hybrid-provenance-audit.json). Current full-slot view [160](lanes/n010-comparison-readiness/results/160-primary-direction-reference-view.json) reverifies those sixteen eligible targets and retains eight pending targets; full-corpus admission remains false. View 127 is historical. Old CPU C1/C2 B8 jobs were stopped at the user's request [124](lanes/n010-comparison-readiness/results/124-user-requested-old-cpu-process-stop.json): complete 65536 levels remain INELIGIBLE, partial 131072 files retained, cap outcome unmeasured. |
| Correctness diagnostics | Actual all-pixel GPU keys and BF-P replay pass (002/007). Measured direct disagreements are included. Sponza direct max-relative-error-1.0 pixels remain **UNRESOLVED / 未解決**; CPU primary-tie diagnosis [053](lanes/n010-comparison-readiness/results/053-residual-primary-contract-diagnosis.md) supports a mechanism, but a GPU repair is unverified. |
| Full quality/memory pilot | Controlled corpus and Sponza one-bounce pilot executed. Finish C1 B8 ladder 043 / combined 044 and full Sponza dynamic cohort 048 after eligible references. Quality FAIL and software churn `UNSUPPORTED_IN_CAPTURE_API` remain outcomes. |
| Full Renderer timing capability | Loaded sizing 035 passes 16 boundaries; failures 027/028 remain retained. Source/ledger audit [133](lanes/n010-comparison-readiness/results/133-current-and-historical-memory-evidence-audit.json) verifies current allocation hooks and 16 current-binary diagnostic memory ledgers, distinguishing 65 historical-binary pilot rows. This is not accepted timing. Quiet sizing 046 now passes all sixteen boundaries; accepted 029 was user-stopped (150), with two completed boundaries failing; minimal-fixture sizing 157 also passes all sixteen image/memory checks; accepted 158 is running with its first three C1 boundaries failing. A valid full calibration remains required. |
| Final handoff | Idle continuation-v3 was retired without jobs (120). Later plan-037/038/039 waiters were stopped by the user (148); none is live. All 24 eligible references, full provenance and quiescence remain mandatory before unchanged pilots/calibration. See historical [134](lanes/n010-comparison-readiness/results/134-memory-evidence-scopes-and-quiescence-watch.md). Final 047 and decision remain pending, then distinct Lane M; no N011. |

The additional DDGI family is pinned to RTXGI Vulkan on AMD, without CUDA:
[source](lanes/n010-comparison-readiness/results/021-ddgi-source-provenance.json),
[host SDK](lanes/n010-comparison-readiness/results/023-ddgi-vulkan-host-build.json).
Fourteen official shader variants compile and the isolated constant-field volume
controls pass on AMD, with owned peak 131472 bytes / zero teardown ([057](lanes/n010-comparison-readiness/results/057-ddgi-volume-runtime-bringup.json)).
Scene tracing/gather, finite-depth transport, dynamic history and full-boundary
memory/timing qualification remain required in Lane M before accepted DDGI
comparisons. Constant-field controls do not establish scene GI correctness.

| Subsystem | Current incumbent / classification | Evidence and boundary |
| --- | --- | --- |
| Work producer | **Adopted:** A001 GPU visibility-driven Split RC, natural append order; no global reorder | [Lane A](lanes/lane-a-split-rc/results/index.json), M0; Lane D does not supersede A001 |
| Primary traversal | **Adopted on measured Radeon 8060S:** HWRT/TLAS | [Lane B](lanes/lane-b-traversal/results/index.json), [I001](integration/results/index.json) |
| HWRT-free traversal | **Adopted fallback:** Segment DDA/hash + conservative quantized Micro BVH8 | Lane B B003; lower-tier alternative, not claimed universally equal to HWRT |
| Radiance storage | **Adopted baseline:** C001 per-probe open-addressed sparse hash | [Lane C](lanes/lane-c-storage-locality/results/index.json); page/clipmap variants conditional |
| Dynamic ownership | **Adopted incumbent:** immutable static, transform-only rigid, object-local deform UPDATE, object-local rebuild for topology changes | [Lane E](lanes/lane-e-dynamic-geometry/results/index.json), [timing revalidation](lanes/lane-e-timing-revalidation/results/) |
| Dynamic backend replacements | **Not promoted:** transient LBVH, clustered two-level variants | [Lane M](lanes/lane-m-topology-backend-crossover/results/); Lane E incumbent retained |
| Full Renderer | **Working research implementation:** N001–N004 and separate N005/N006 experimental variants | [Lane N](lanes/lane-n-end-to-end-renderer/results/index.json), [N005](lanes/n005-adaptive-tracing/), [N006](lanes/n006-interval-aware-allocation/) |
| N005 adaptive tracing | **REFINE / conditional:** no universal policy accepted | [N005 evidence](lanes/n005-adaptive-tracing/results/) |
| N006 interval-aware allocation | **STOP:** Q8 influence exists; +4-ray signed HDR quality lift not detectably proven; do not initiate P2/P3 | [N006 final result 045](lanes/n006-interval-aware-allocation/results/045-p1m3c-deforming-signed-quality-no-detectable-lift-stop.md) |
| N009 scene contract / back faces / probe attribution | **Concluded:** SC NO GO, BF1–BF3 PASS, PT INCOMPLETE; C1/BF-P remain opt-in | [N009 final result 009](lanes/n009-scene-contract/results/009-n009-final-decision.md); no architecture promotion |

The current production-style Renderer uses **N-series pinned imports**, not whatever historical code happens to be stored in other lane folders. Presence of old experiment sources does not activate them.

## Evidence of improvement and limits

- **Lane E #22**, frozen Lane-L heavy recurring boundary: moving-rigid 0.330894x HWRT / 0.519178x software, and stable-deforming 0.331625x HWRT / 0.525108x software (candidate/control complete-GPU ratios); the required >=20% improvements and memory guards passed. Exact evidence remains in the revalidation lane.
- **Lane M #25:** 6,144 GPU-timing rows in 192 fresh processes on frozen primary/software tracks; transient LBVH and clustered two-level approaches did not qualify. Lane E object-local rebuild remains incumbent for topology changes/high churn.
- **N003:** reported **~2.35–3.11x Renderer speedup** against the particular vanilla Split RC control cases, accompanied by **~24–27% extra GPU memory**. These figures are not general quality-equivalent, cross-scene, or cross-GPU superiority claims.
- **N004:** motion-related image-quality weaknesses were detected. Performance success does not close image quality.
- **N005:** adaptive tracing showed conditional promise, but a single accepted scheduling rule was **not** established.
- **N006:** [Q8 replicate mechanism](lanes/n006-interval-aware-allocation/results/041-p1m3a-q8-gpu-replicated-image-mechanism.md) showed reproducible image influence; [moving-rigid reference](lanes/n006-interval-aware-allocation/results/043-p1m3b-moving-rigid-identical-reference-invalid.md) was ineligible, and [final deforming signed-quality comparison](lanes/n006-interval-aware-allocation/results/045-p1m3c-deforming-signed-quality-no-detectable-lift-stop.md) found **no detectable improvement** exceeding independent-reference noise. Extra-ray policy is not adopted; N006 P1/P2/P3 stopped.

## Measurement capability

- Performance primary: **GPU timestamps**. CPU wall: diagnostic/provenance/health, not a second equal acceptance axis.
- **Lane K:** 5% detectable effect for its calibration workload. **Lane L:** 20% detectable effect for the complete recurring heavy boundary. Transferability is **not assumed**.
- Require frozen exact semantics, process-replicated timing, all-sample retention, persistent + true-peak GPU memory, correctness and exact measured boundary. [Detailed protocol](protocol.md).
- **Reference quality caveat:** previously accepted N001 camera/moving-rigid CPU references included all-black cases, and N006 deforming references have <1% positive pixels; a zero full-frame p99 does **not** establish adequate HDR convergence. [N007 #4](https://github.com/owoDra/real-time-gi-lab/issues/4) **concluded bounded NO GO** for cross-class reference qualification on 2026-10-12; independent of this integration and original N006 decision.

N007 P0 CPU source audit and synthetic PFM diagnostics are in progress on `research-n007-reference-validity` ([protocol](lanes/n007-reference-validity/experiments/001-reference-eligibility-protocol.md), [results](lanes/n007-reference-validity/results/index.json)). **Authentic archived N006 M3b PFMs were inspected in the user's environment**: both CPU references are fully black and their pairwise RGB RMS is zero ([N007 result 003](lanes/n007-reference-validity/results/003-authentic-m3b-archive-cpu-inspection.md)); this establishes M3b reference *statistical ineligibility*, not the physical cause. Complete original M3b inspector JSON confirms Q8 has **10,076 positive pixels** against two black references (GPU/reference RGB RMS 1.6121822848358563e-05), without proving the physical source ([N007 result 004](lanes/n007-reference-validity/results/004-authentic-m3b-full-image-signal.md)). Archived cohort v1 checked only **200/338** pairs: 69 black-reference instances collapse into just **two of six distinct SHA-pair signatures**; N004/N006 were excluded by the old default cap. **All-archive scanner v2 has now completed 338/338 name-matched pairs with zero errors**: 96 black-reference/GPU-positive archive entries reduce to **4 unique candidate/reference SHA pairs**, all with the **same black CPU reference SHA** (33 distinct pairs overall). N001, N004 and N006 M3b reproduce the mismatch, whereas N006 M3c and N001 light-motion have nonzero, still not certified, CPU references ([N007 result 006](lanes/n007-reference-validity/results/006-p0-complete-archive-image-survey.md)). N007 P1-A CPU-only transport audit ([result 007](lanes/n007-reference-validity/results/007-p1a-cpu-source-shadow-contract.md)) has checked 7 actual source files with 10/10 source contracts passing; 8/8 assistant-sandbox synthetic CPU unit tests show shadow-tested vs unshadowed probe Lambert can differ on an occluder. CMake builds the live `i001_radiance.spv` from `n001_physical_radiance.comp.glsl`, not the legacy imported hash shader. This establishes a **possible source-level light-visibility mismatch**, NOT the physical cause of archived M3b positive GPU pixels. Read-only test and report code are committed; no user-local CPU run is needed for this stage. Real-frame convergence and physical validity remain **unverified**. This has no effect on N006 P1 NO GO or the historical N001/N003 result classifications. N007 P1-A-008 now adds a **diagnostic-only, default-OFF matched-frame CPU/GPU component capture path** ([result 008](lanes/n007-reference-validity/results/008-p1a-component-capture-bringup.md)): local synthetic Python 14/14 PASS, isolated C++/BVH controlled test compiled and PASS, GitHub source anchors 9/9 PASS. The assistant sandbox did **not** execute the integrated CMake build, GLSL compilation or a GPU run. Instrumentation is not yet end-to-end validated, real-frame matching/correctness and convergence remain unknown. The new code is N007-only; no archived PFM was published.

**N007 P1-A GPU-host follow-up (2026-10-12):** the opt-in capture executable compiled and completed one moving-rigid/software/target-state/512-SPP run. Its first component analyzer returned `gpu_reconstruction_passed=true` but `primary_match=false`, so no indirect attribution or physical correctness claim follows. A source audit found the N007 generated N001 runtime had omitted N006's moving-target `n006_refresh_software_primary()` call, leaving a plausible stale GPU primary BVH while the CPU traced translated world geometry. A GPU rerun with that initial refresh still failed first-hit matching (3,866 mask / 3,744 identity / 2,300 t / 2,300 normal mismatches), though GPU channel reconstruction passed and CPU/GPU direct max delta was zero. Further source audit found that `update_dynamic_geometry(true)` already translates `b_scene.triangles`, while the legacy refresh method translates again: **N007 instrumentation double-translated GPU first-hit geometry**. The new N007-only generated overlay uses already-updated world-space triangles and adds radiance positivity/hit coverage diagnostics. In addition, the software capture now downloads the actual GPU primary triangle buffer and independently verifies every 64-byte std430 triangle against the CPU world-space snapshot, rather than relying only on a source-side SHA. **GPU remeasurement confirmed `primary_match=true` (15,173 CPU/GPU hit pixels; all four mismatch categories zero) and byte-exact software-primary geometry (262,241 triangles, zero mismatches).** CPU direct/indirect/total each have zero positive pixels; GPU direct is zero, but GPU indirect/total each have **9,247** positive pixels. The GPU component reconstruction passes; indirect max absolute difference is **0.00012207217514514923**. This localizes the current matched-primary discrepancy to probe-indirect output, **not** to the source of archived M3b artifacts or physical truth ([result 009](lanes/n007-reference-validity/results/009-p1a-matched-primary-indirect-isolation.md)). A new on-device probe replay has now run: of **134,816** GPU probe work items, **18,649** generated nonzero radiance; **18,363 (98.4664%)** had an independently CPU-confirmed blocked light ray while **286** were unoccluded. All sampled GPU/CPU secondary traversal hits and fixed-radiance Lambert predictions matched (**0** mismatches), and 0 invalid IDs/hit flags were reported. Thus missing secondary shadow visibility is directly observable as a transport-model difference for this frame, not just a source-level hypothesis. **Subsequent P1-B 011 GPU-image replay has now proven** a baseline-matching image-level counterfactual that suppressing just CPU-shadowed probe contributions removes **9,247 / 9,247** positive GPU indirect pixels; this supersedes the earlier diagnostic uncertainty, although original archived M3b artifacts remain causally unattributed. See [result 009](lanes/n007-reference-validity/results/009-p1a-matched-primary-indirect-isolation.md). Original N006 decisions, HDR statistical eligibility and independent physical correctness remain unchanged/unknown. See [result 008](lanes/n007-reference-validity/results/008-p1a-component-capture-bringup.md).

**N008 Phase A (2026-10-13, [Issue #5](https://github.com/owoDra/real-time-gi-lab/issues/5), branch `research-n008-hdr-oracle`): Exit A = GO.** A new, independent CPU HDR oracle (`src/research/n008_hdr_oracle/`, opt-in, double-precision watertight path tracer sharing no N001/Lane B code) passed all preregistered physically known controls A1–A10 (102 checks: exact lit/occluded/back-face/moving-rigid frozen pose, exactly-zero sealed/no-leak rooms, strictly positive lit rooms, analytic multi-bounce sphere furnace ~1e-4, two-bounce quadrature, closed-form area light) and agreed with Mitsuba 3.6.4 on identical meshes in 7/7 cells (≤1.6e-4 relative image mean, per-pixel |z|≤6 in 100%). Injected defects (far truncation, N001 soft falloff, 1 mm light slip, 0.5% albedo, one-sided walls) are all detected. **Scope:** Lambert/point/emissive-triangle transport on controlled scenes; textures, alpha-tested foliage and glossy BSDFs are not validated, and no Renderer/Sponza reference is yet qualified. N007/N006 remain closed and unchanged. [Result 004](lanes/n008-hdr-oracle/results/004-phase-a-exit-decision.md).

**N008 Phase B/C-partial (2026-10-13):**
- **Exit B = GO, bounded.** The Renderer's own target states were exported CPU-only from verbatim-extracted Renderer code; the moving-rigid state is byte-identical to the GPU-run N007 capture. Rendering them with the validated oracle gives:
  - **non-Sponza `leak-medium`:** STATISTICALLY_ELIGIBLE.
  - **Sponza light-motion:** direct deterministic reference only.
  - **Sponza camera-motion and moving-rigid:** NO_SUPPORT (exactly unlit at the camera within the declared transport).
  - **Sponza static, deforming and topology-churn:** INELIGIBLE (sparse, non-converged).
- **Likely cause of the dark Sponza states (a state fact):** the loaders ignore glTF node transforms, and the A001 light and eye lie outside the geometry bounds.
- **Phase C diagnostic, CPU-only, on the existing N007 GPU capture of the identical state:** primary hits match exactly, and **all 9,247 positive GPU indirect pixels have zero physical support**. This is not scored, and N006/N007 are unchanged. [Result 006](lanes/n008-hdr-oracle/results/006-phase-b-exit-decision.md), [result 008](lanes/n008-hdr-oracle/results/008-phase-c-b4-gpu-diagnostic.md).

**N008 final (2026-10-13): oracle GO; cross-class Renderer reference set is a bounded NO GO.** [Result 011](lanes/n008-hdr-oracle/results/011-n008-final-decision.md)
- **State attestation:** GPU captures (RADV 8060S, software and hwrt) byte-attest the B1–B5 and B7 states.
- **Direct and shadow:** on matched visibility, the Renderer's direct/shadow term agrees with the validated oracle to float32 (B7, B3).
- **Indirect, which errs in both directions:**
  - it leaks light with no physical support in the Sponza target states (B1/B2/B4/B5);
  - it misses about 95% of the real one-bounce light on the only eligible total reference (non-Sponza `leak-medium`: total −30% for D2, −36% for D8).
- **Scope:** diagnostic only, with no ranking and no N006/N007 revision. Next: a separately preregistered scene-contract study (glTF node transforms and an interior light).

**N009 final (2026-10-14, branch `research-n009-scene-contract`): Exit SC = NO GO; BF1–BF3 = PASS; Exit PT = INCOMPLETE.** [Result 009](lanes/n009-scene-contract/results/009-n009-final-decision.md)

- **Scene contract:** transformed Sponza with authored camera/interior light has full total support, but C1/C2/C4/C5/C6 are only DIRECT_DETERMINISTIC_PROVED under both T_B2/T_B8; no total reference passes the unchanged four-seed 8192-SPP screen. C3 light motion is NOT_CONSTRUCTIBLE under the disclosed pre-reference Amendment 1. This is not Bounded GO for total references.
- **Back faces:** all 10 captures are byte-attested and two-sided. C7 has zero primary mismatches and direct max relative error 1.08488e-5 on both backends, passing the C7-specific gates. Sponza has 74/108 primitive mismatches and direct max-relative-error-1.0 pixels even on matched visibility; their cause remains **unresolved (未解決)**. Small direct sum bias does not prove per-pixel agreement.
- **Probe attribution:** C7 fails V1 (21 replay mismatch pixels); old B4 fails V3 (86.93% secondary re-trace match). Coverage/range observations and complete shadow removal on old B4 remain diagnostic. Excluding the 21 pixels is explicitly post-hoc sensitivity and does not complete attribution.
- **Scope:** computation is complete; N009's opt-in C1/BF-P overlay is not adopted. No total-quality ranking or performance/memory/temporal claim; this evidence-only write-up reruns no build, executable test or GPU/runtime check. N001–N008 results remain unchanged. Next work needs new preregistration or explicitly labelled diagnostics.

## Unresolved strategic questions

1. **Finish comparison preparation in N010, then execute Lane M GI comparisons.** N007/N008/N009 remain concluded; N009 still lacks eligible Sponza totals at its frozen cap. N010 preregisters sampling-only reference qualification, explicit correctness diagnostics, executable RC/path-tracing controls, quality matching, full Renderer GPU calibration and allocation-lifetime peak memory. No READY or superiority claim until the corresponding evidence exists.
2. **Does this architecture actually beat fair existing GI baselines** under equivalent quality/cost across multiple scenes and hardware classes? Not yet established.
3. **Which structural light-transport/storage/reuse changes** can change the total quality/performance/memory frontier beyond a locally optimized Split RC pipeline? Evaluate only after reliable baselines and bottlenecks.

See [roadmap](roadmap.md) for gates. Old status, stale next-step commands and branch-local research attempts are historical data, not the current agenda.

**N007 P1-B tooling (2026-10-12):** the current matched frame's 18,363 independently shadow-blocked positive GPU probe contributions are retained as **diagnostic-only**, not a full-image attribution. [Result 010](lanes/n007-reference-validity/results/010-p1b-reference-screen-readiness.md) adds CPU-only, GPU-free derived shadow-label reproduction, captured-probe-to-pixel replay with strict unchanged-GPU baseline image match before the occluded-sample counterfactual, and a resumable frozen four-seed 512–8192-SPP statistical screen reusing the captured real 512-SPP data. Existing N001–N006 code/shaders untouched. **Superseded by subsequent completed real local P1-B execution**: original GPU indirect image reconstructed, shadow-positive contribution ablation eliminated all **9,247** positive pixels (original sum 0.2673380636301213 → 0.0), and four-seed CPU reference SPP 512/1024/2048/4096/8192 returned zero union-active signal at every level, `statistical-screen-fail`. See [result 011](lanes/n007-reference-validity/results/011-p1b-probe-pixel-counterfactual-and-spp-screen.md). Physical correctness and original archived M3b causation remain unknown; no N001–N006 historical GO/NO GO is altered.

**N007 final bounded stop (2026-10-12):** [result 012](lanes/n007-reference-validity/results/012-n007-bounded-no-go-decision.md) applies Issue #4's frozen rule to **stop when a reliable, nontrivial HDR reference across all required dynamic classes cannot be demonstrated within resources**. Moving-rigid is mandatory and has exhausted the complete frozen four-seed 512–8192-SPP ladder with active fraction **0.0** at every level; consequently **cross-class HDR reference qualification = NO GO**. N007 P1-B isolated the image-level GPU secondary shadow omission mechanism for its **new matched diagnostic frame** (9,247/9,247 positive indirect pixels disappear when just CPU-shadowed GPU probe contributions are suppressed). Camera/disocclusion, light-motion, controlled-GPU-light, static/deforming/churn, and independent GPU camera/secondary allocation attestation remain **explicitly unmeasured or unverified**; the stop does not declare them individually wrong or correct. Physical accuracy and historical original N006 M3b frame causation are **unproven**. No original N001–N006 sources or outcomes changed. [Issue #4](https://github.com/owoDra/real-time-gi-lab/issues/4) closed as negative research outcome, not a positive GI quality pass.

### N010 reference acquisition and acceleration provenance

The independent original sampler proof 009, cache equivalence 022 and exact
CPU-prefix proof 050 pass. Controlled reference provenance 051 covers twelve
C7–C12 transports, and recovered C2 B2 provenance 080 passes. Selected-slot audit 109 now rechecks all fifteen eligible CPU transports
through the separate provenance API, including canonical scenes, every payload/header,
unchanged convergence screens and imported-prefix proofs. All pass and input
bytes remain unchanged after the audit. The remaining nine transports and the
full hybrid variant branch are not attested by that result. Interrupted acquisitions 065, complete imports,
later partial seeds and prior views remain retained. Recovery view 067 preserves
all 24 slots with unchanged four seeds, levels, support-aware screens and cap.

The original GPU numerical port **failed** completed C1 B8 conformance (082):
mean 6.78235e-7 versus limit 1e-10, moment 5.31950e-9 versus 1e-10, indirect
NRMSE 2.94757e-6 versus 1e-8 and differing shadow counters. Earlier timeouts and
failed launches remain recorded. [Post-hoc path diagnosis](lanes/n010-comparison-readiness/results/091-deep-path-signed-zero-diagnosis.md)
identifies a signed-zero tangent-basis mechanism in all eight selected traced
paths; the other 46 affected pixels were not individually traced. This is not
proof of population bias or a repair of the Renderer's unresolved direct pixels.

A separate streamed hybrid recomputes every ambiguously intersecting whole path
with the original independent CPU oracle, retaining every sample. It currently
passes all 16/16 complete numerical cases ([098](lanes/n010-comparison-readiness/results/098-hybrid-full-numerical-conformance.json)).
Full-frame C1 B8 seed 0 [096](lanes/n010-comparison-readiness/results/096-hybrid-full-frame-deep-conformance.json)
and seeds 1 [107](lanes/n010-comparison-readiness/results/107-hybrid-full-frame-deep-seed1-conformance.json) /
2 [110](lanes/n010-comparison-readiness/results/110-hybrid-full-frame-deep-seed2-conformance.json)
pass the unchanged gates, with exact counters/primary/direct/emission. Seed-0
fallback covers about 8.66% of paths; acquisition timings are loaded diagnostics.
[Raw-export audit 108](lanes/n010-comparison-readiness/results/108-hybrid-deep-raw-prefix-export-audit.json)
passes both cases' complete binary64 sum/moment reconstruction, per-pixel
counter totals, all four PFM components and owned-memory replay.

Hybrid physical [099](lanes/n010-comparison-readiness/results/099-hybrid-physical-controls.json)
completes 68 numerical cases and all eight physical controls PASS. All-state/prefix
[101](lanes/n010-comparison-readiness/results/101-hybrid-all-state-and-prefix.json)
completes 96 low-dose and eight actual-level cases, with all 304 native attempts
PASS. Fresh statistical acquisition 121 now runs under plan 034. C4 B2 completes
the first qualifying pair at 16384/32768; actual new-variant provenance 123 checks
5,413 read identities, all unchanged, including complete prerequisite payloads.
That reference is separate from the prospectively fixed comparison map 127.
No whole-corpus admission or accepted timing follows. Historical refusals
104–106 and failed original port 082 remain unchanged.

For exact source/evidence identities and historical attempts, use the
[N010 result index](lanes/n010-comparison-readiness/results/index.json),
[execution record](lanes/n010-comparison-readiness/results/008-interim-execution-and-resume.md)
and [tooling documentation](../scripts/research/n010_comparison_readiness/README.md).

A separate CPU sampling/importance-weight prototype is registered prospectively
in [plan 030](lanes/n010-comparison-readiness/experiments/030-prospective-point-guided-reference-sampling.md).
It mixes cosine continuation with geometry/direct-light surface guidance and
explicit null events, preserving the original finite-transport integral as the
validation target. Build [112](lanes/n010-comparison-readiness/results/112-point-guided-oracle-build.json)
passes. Physical acquisition 113 exported all seventeen scenes, then its analysis
adapter failed on missing `geometry_hash_match`; 113 remains terminal FAIL.
Post-hoc CPU-only [125](lanes/n010-comparison-readiness/results/125-point-guided-physical-analysis-replay.json)
rechecks the retained bytes, derives wrapper geometry/name fields from actual
metadata and canonical scenes, and passes all eight original physical and two
iid checks with unchanged gates and no rerender. Separate prefix build 114
passes. Plan 036's fresh all-state/own-prefix
[126](lanes/n010-comparison-readiness/results/126-replayed-point-guided-all-state-and-prefix.json)
now completes all 24 low-dose cases, both actual-level C7 cases and all 78 native
attempts PASS, including zero payload/counter disagreements. Independent
proof-chain audit [131](lanes/n010-comparison-readiness/results/131-replayed-point-guided-proof-chain-audit.json)
passes before publication. The single fresh nine-slot acquisition 128 has
actually started. No point-guided corpus reference or full comparison admission
exists yet; statistical qualification is still required.
All four seeds, levels, absolute/relative screens and cap remain fixed.

Prospective point-guided acquisition [plan 032](lanes/n010-comparison-readiness/experiments/032-point-guided-reference-qualification.md)
prepares separate ladders for all nine currently unfinished transports; the
other fifteen remain included through original-method evidence. Executed
prerequisite check [116](lanes/n010-comparison-readiness/results/116-point-guided-qualification-prerequisite-check.json)
refuses dispatch because 113 is incomplete. Exact read input bytes are archived;
no acquisition root or samples were created. The old 113/115 queue terminated
on 113 failure with no acquisition. The separate plan-036 queue now executes
128 after complete 125/126 PASS, retaining the original nine-slot/four-seed/
six-level/screens/cap rules. Successful statistical qualification and full new
sampling-reference provenance remain unmeasured. Plan-037 view 127 is a
scheduling map, not eligibility or comparison readiness.
Existing-CPU delegation [117](lanes/n010-comparison-readiness/results/117-point-guided-api-existing-cpu-provenance-audit.json)
passes all fifteen previously eligible slots through the new API; this audits
original-method references only and does not attest the point-guided branch.

A separate final-preflight [adapter plan 033](lanes/n010-comparison-readiness/experiments/033-point-guided-readiness-adapter.md)
changes only reference-provenance dispatch/description and recorded adapter
identities, retaining all six original readiness gates and thresholds. Actual
interim execution [119](lanes/n010-comparison-readiness/results/119-point-guided-adapter-interim-preflight.json)
against view 067 is NOT_READY (162 recorded inputs): reference eligibility,
full Sponza pilots and accepted calibration remain incomplete. Its six gate
names/pass classifications equal the earlier 103 audit. It does not execute
a new sampling-reference branch, change the frozen driver or supply final 047.
