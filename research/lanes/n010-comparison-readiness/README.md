# N010 — final comparison preparation

## Current execution checkpoint — 2026-10-17 JST

**N010 remains NOT_READY.** User resumed work for cause diagnosis and the
shortest valid completion path, with low interactive load. No old stopped
acquisition or waiting queue is restarted. Bounded CPU and short C7 GPU
diagnostics have completed; neither supplies the missing readiness proof.
No full-frame reference ladder or long GPU campaign is running or queued.

See [cause review 192](results/192-cause-review-and-shortest-valid-completion.md)
and [prospective bounded plan 057](experiments/057-bounded-cause-diagnosis-and-critical-path.md).

| Required item | Actual current evidence | Remaining work |
| --- | --- | --- |
| All 24 eligible references | [160](results/160-primary-direction-reference-view.json): sixteen eligible, eight pending | Resolve the dominant uncertainty mechanism; validate any distinct sampling method before all fixed pending ladders. |
| Candidate feasibility | [180](results/180-primary-direction-second-stop-bounded-feasibility.json): **COMPLETE / FAIL**, 8192/16384 ratios **1.0703554221788882 / 1.0599135470235277** against <=0.75 | Candidate rejected; 166 NOT RUN and blocked by its genuine FAIL. This is not a full statistical-cap failure. |
| New sampler preparation | [187](results/187-nested-scramble-oracle-build.json): isolated build PASS | Fixed-grid 195 shows p99 ratio 0.948 but replicate-variance ratio 1.019; insufficient evidence for long acquisition. 188/189/190 remain NOT RUN. |
| GPU calibration | [185](results/185-deferred-image-calibration-sizing.json): **COMPLETE / sizing PASS**, all sixteen boundaries | Short C7 probes 196/197 both complete and FAIL all seven precision gates, including user-idle 197. Full 186 NOT RUN; no accepted timing. |
| Correctness | Actual GPU keys/BF-P evidence retained; [053](results/053-residual-primary-contract-diagnosis.md) supports CPU primary-tie mechanism | GPU repair unverified; the original gate permits explicitly measured remaining direct discrepancies. Max-relative-error-1.0 pixels stay **UNRESOLVED / 未解決**, included. |
| Cohort and quality/memory pilots | RC/PT families executable; measured quality losses and allocation ledgers retained | Finish missing full-corpus ladders/dynamic pilots and original final six-gate auditor. DDGI source/device boundary remains required for Lane M. |

### What the cause analysis establishes

CPU-only [191](results/191-posthoc-readiness-bottleneck-diagnosis.json)
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

[193](results/193-selected-bounce-path-diagnosis.json) completed all six
serial compiler/native invocations. Original and failed-guide selected mean
and second-moment fields are bit-exact to retained sidecars. Native runs took
10.324 / 10.400 / 10.271 seconds, one low-priority CPU each, no GPU.
[194](results/194-posthoc-depth-weight-and-rqmc-interpretation.json)
keeps tail selection separate from fixed-grid observations. On the sixteen
selected pixels, the guide reduces first-indirect path variance but increases
later variance. Whole-image data show a necessary qualification: **total path
variance actually falls to 0.969 of original, while observed replicate variance
increases to 1.133 / 1.135**. Loss of the observed net variance-reduction benefit,
not simply more path variance, is therefore part of the measured failure.
Moment-based iid proxies are descriptive only, never RQMC standard errors.

[Plan 058](experiments/058-fixed-grid-and-short-boundary-diagnostics.md)
completed both diagnostics. [195](results/195-fixed-grid-scramble-diagnosis.json)
uses the exact existing nested binary on a prospectively fixed 256-pixel C1
grid, one CPU at nice 15, 164.588 seconds, no GPU. Nested/original p99 is
**0.948183**, but replicate variance is **1.018947**. This one-level grid
provides no evidence of the strong reduction needed to justify another long
ladder. It is not a formal failure of unrun 188/189/190 or reference admission.

[196](results/196-deferred-c7-precision-diagnostic.json) and
[197](results/197-natural-idle-c7-precision-diagnostic.json), prospectively
registered in [059](experiments/059-natural-idle-c7-observation.md), each
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
[198](results/198-bounded-cause-probes-posthoc-replay.json) replays all
original schedules/decisions, native resource receipts, owned ledgers and CPU
spool receipts exactly; it does not independently rehash every native payload.

### Completed implementation probes 060/061

[199](results/199-packed-readback-fixture-build.json) builds an isolated
capture fixture with four diagnostic downloads coalesced after the original
timed GPU commands. Whole-source inverses and unchanged timed recording and
expressions pass. One-CPU compile/link durations are 6.461 / 2.646 / 0.057
seconds. [200](results/200-packed-readback-c7-sizing.json) completes
C7 sizing PASS, dose 3500. All images/scratch/owned-memory/CPU spools pass.
Actual [201](results/201-packed-readback-c7-precision-diagnostic.json)
completes all eight blocks / 512 samples but **FAILS all seven original gates**.
Zero-dose times span 156.177–987.717 us; observed peak owned Vulkan memory is
263382656 bytes, teardown zero. This fixed candidate stops; no full campaign.

[202](results/202-later-bounce-cv-path-diagnosis.json) completes the
prospective [061](experiments/061-later-bounce-control-variate-diagnosis.md)
conditional control-variate diagnosis on eight fixed C1 pixels, one low-priority
CPU, 67.572 seconds. Original means/moments reconstruct bit-exactly. Corrected
p99 ratio is **0.837924**, but replicate variance **1.054490** and descriptive
per-path variance **1.032952**. Its prospective promising rule FAILS; no full
controls/ladder follows this fixed prototype. This does not reject every
conditional correction or prove a general variance theorem.

[203](results/203-array-rqmc-transport-diagnosis.json), registered in
[062](experiments/062-array-rqmc-transport-diagnosis.md), then completes
an eight-pixel geometry-sorted array-RQMC prototype in 24.206 native CPU
seconds. Original moments, deterministic components and first-indirect luma
means match retained values bit-for-bit. Its p99 ratio is **1.049287**,
replicate variance **0.885354**, and per-path variance **0.994757**. The
prospective promising rule FAILS. This fixed sort/assignment stops; no
larger-level prefix, full physical/state proof or reference admission follows.
The result does not reject array-RQMC generally or establish the behavior of
all eight pending corpus slots. No scientific acquisition remains running.

### Contiguous submission diagnosis, completed 2026-10-17

[063](experiments/063-contiguous-c7-command-batch-diagnosis.md) through
[065](experiments/065-contiguous-import-header-repair.md) implement a static C7-only
fixture with separate uniform/query/readback slots for every original frame.
[204](results/204-contiguous-c7-fixture-build.json) and
[205](results/205-contiguous-c7-decoder-repair-build.json) preserve compiler failures;
[206](results/206-contiguous-c7-import-repair-build.json) builds successfully without
changing original timed GPU recording or timing expressions. No original
header/default target changes. [207](results/207-contiguous-c7-sizing.json) sizing PASS
freezes dose 1342 by the original rule; no dose tuning follows.

[208](results/208-contiguous-c7-precision-diagnostic.json) completes all 8 blocks / 512
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

[066](experiments/066-frozen-suffix-control-variate-diagnosis.md) and
[209](results/209-frozen-suffix-cv-diagnosis.json) complete a distinct frozen
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

### Whole-path reference prototype: two numerical stops identified

[067](experiments/067-whole-path-mixture-diagnosis.md) derives a distinct half-eye /
half-light complete-path mixture in raw-hit surface coordinates. It preserves
original soft falloff/nudge/offset/direct/BVH, evaluates both ordered densities
without assuming reciprocity, and applies one bounded<=2 correction per depth
contribution. [210](results/210-whole-path-mixture-diagnosis.json) compiles but stops
at its raw-target guard after3.378 native CPU seconds. It is **INCOMPLETE**;
no promising-rule verdict or reference admission is established.

[211](results/211-whole-path-numeric-failure-witness.json) reproduces the same failure.
Decimal80 analysis shows grazing condition number3522.828485: even exact
line-plane intersection misses the stored binary64 target by2.6930e-10,
exceeding its old2.0827e-10 *unconditioned* numerical allowance.
[069](experiments/069-conditioned-raw-target-numeric-audit.md) explicitly amends that
diagnostic guard before new data, using plane residuals and analytically
conditioned backward error. This is **a changed numerical audit**;210 remains
failed. Statistical/reference/promising thresholds are unchanged.

[212](results/212-whole-path-conditioned-diagnosis.json) then stops after18.716 CPU
seconds at the unchanged own-family nonzero-density guard. It too is
**INCOMPLETE**, not a variance-screen FAIL/PASS. [213](results/213-whole-path-own-support-witness.json)
reproduces the exact cause: at C1 pixel200/150, light-prefix5, the same raw
point is on overlapping coplanar triangles59258/59011. Tiny direction changes
select a different primitive. [214](results/214-coincident-surface-operator-diagnosis.json)
uses original Oracle operators: plane/material/nudged point/spawn match here,
but normalized normals and one fixed cosine-mapped direction differ by1 ULP.
A plain ID alias is not verified. No scored path is removed or silently merged.

Next implementation work must define and independently validate density
matching across such physically coincident surfaces, including numeric
normal/map and self-ignore effects, before another complete prototype. These
witnesses identify prototype stops, **not** a fix for original reference
uncertainty, all duplicate geometry, or the unresolved GPU direct pixels.
No GPU dispatch in210–214; one CPU nice15 only. All prior failures/partials
are retained; no whole-frame ladder or scientific worker remains running.

The unresolved reference problem is reducing later finite-transport uncertainty
while preserving the physical and sampling contracts. The unresolved timing
problem remains full-boundary precision: packed copies and a contiguous C7
batch have both failed. Neither is fixed. All original thresholds and final gates remain;
N010 completion and a date remain unproved.

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

## Earlier execution checkpoints

The progression below records earlier checkpoints. Use the current section
above and `research/status.md` for present process and reference status.

New executable cohort: native GPU pixel PT and the separately frozen dense
repository RC estimator control. [C7 budget/quality results](results/013-c7-pt-cohort-pilot.json)
include all losses and passing PT levels. [Construction lock](results/016-corpus-state-lock.json)
contains source/target dynamics and local light motion. C7 and C8–C12 references
are eligible in both finite transports. The [dynamic cohort](results/019-controlled-dynamic-cohort.json)
retains all 145 executed source/target/recovery images, all losses and two
explicit software-churn capture limitations; [independent memory replay](results/020-controlled-dynamic-summary.json)
passes for all 29 roles. Sponza C1/C3 T_B2 references now qualify. [C1 quality comparisons](results/033-interim-comparison-findings.md)
show incumbent/dense RC FAIL and pixel PT PASS at 256/1024 spp. Remaining
Sponza reference acquisition and calibrated timing are in progress.
Historical vanilla-software is a traversal control, not a separate GI baseline.

[RTXGI provenance](results/021-ddgi-source-provenance.json) pins the fetched SDK
for the required additional Lane M DDGI comparator. The chosen path is Vulkan
on AMD, without CUDA. The [Vulkan host SDK builds](results/023-ddgi-vulkan-host-build.json)
and the [pinned CPU DXC runs](results/034-dxc-cpu-compiler-provenance.json);
integrated DDGI runtime is not yet demonstrated.

[Post-hoc CPU primary diagnosis](results/053-residual-primary-contract-diagnosis.md)
localizes both residual C1 direct-zero pixels to differing primary primitives
and supports a legacy tie-interval mechanism. No GPU repair is claimed; both
pixels remain unresolved and included in scoring.

[Cache equivalence](results/022-cached-oracle-equivalence.json) is complete and
PASS in all 20 cases. The [controlled reference provenance audit](results/051-controlled-reference-provenance-audit.json)
rechecks C7–C12, both transports: canonical scene/state, four fixed seeds,
all component/f64/primary-hit hashes, and every original convergence screen.
All 12 pass. This is a subset audit; remaining Sponza references and the full
readiness gate are unfinished. Incremental equivalence 050 is now complete/PASS in all three declared
cases. Reference jobs and the waiting driver terminated (065), with cause unestablished.
Complete prefixes and partial later seeds are retained. Amendment 8 prepares
fresh acquisitions from the validated complete C1 T_B8/C3 T_B8/C2 T_B2
prefixes; view 067 fixes all 24 slots before recovery output. Prior view 061 and
statuses are historical. GPU numerical-port compilation/build (066/068) are
isolated diagnostics and establish no reference eligibility.

The unmanaged SDK also validates reduction shader modules/pipelines even when
variability is disabled. [Result 056](results/056-ddgi-reduction-shader-compilation.json)
compiles both official reduction entry points for 32/64-lane configurations,
using the pinned DXC and SDK. All four compile. Runtime must select the shader
against supported subgroup configuration; this is CPU compilation, not an
integrated DDGI GPU execution or quality result.

[Official SDK GPU volume bring-up](results/057-ddgi-volume-runtime-bringup.json)
now executes on Radeon 8060S/RADV with subgroup width 64. Both preregistered
constant-field controls pass every irradiance/distance texel, including borders:
maximum errors 5.96046e-8 / 2.98023e-8. Owned Vulkan peak is 131,472 bytes,
20 lifetime events independently replay to zero teardown. The standalone build
is [058](results/058-ddgi-volume-build.json). No default CMake/Renderer changes.
This is resource/dispatch normalization wiring: scene tracing, finite-depth
transport, surface gather and dynamic histories remain unimplemented. It is
not DDGI frame-quality qualification or a calibrated timing result.

Historically, recovery executed C1 T_B8 16384→32768 and C2 T_B2 8192→16384 in
two 16-thread qualifiers. Continuation-v3 used view 067; its later retirement
and the user-requested CPU stops are recorded in 120/124. C7 T_B2
GPU numerical-port conformance at 16 spp passes (070), with exact counters and
max mean discrepancy 2.71051e-20; this does not grant reference eligibility.

C2 T_B2 recovery is now eligible at 16384/32768; independent canonical/
payload/prefix-chain audit 080 passes, scoped to this one transport. C1/C3
T_B8 and the remaining slots still run. GPU conformance 074 preserves its
120-second Sponza guard failure; prospective 075 uses the recorded 900-second
guard. First C1 T_B2 8192 numerical comparison passes with exact counters and
max mean difference 1.73472e-18. GPU references remain ineligible pending
full numerical, physical-control, all-state and actual-level prefix proof.

The resource follow-up 075 is now terminal: twelve cases pass, then the first
C1 T_B8 case times out at 900 seconds without numerical output. 075 remains
failed; 081 records that conditional physical/prefix workers refused dispatch
(NOT RUN). Plan 021 starts 082 with the twelve unchanged completed cases and
a fresh 1800-second guard for the remaining four. New conditional workers
use 082 and fresh work roots; no GPU reference is admitted.

### Completed deep GPU numerical failure

082 completed C1 T_B8 seed 0 (8192 spp) but failed unchanged Amendment 7
gates: mean 6.78235e-7, moment 5.31950e-9, indirect NRMSE 2.94757e-6,
shadow-test/blocked counter differences +26/+31. Primary/direct/emission
remain byte identical. The candidate is ineligible; dependent physical and
all-state/prefix runs refused dispatch (085, NOT RUN). 084 maps 54 affected
pixels as post-hoc diagnosis; plan 022 uses eight selected pixels to replay
and intervene on sampling arithmetic. No exclusions or relaxed thresholds.
CPU reference recovery continues independently; 15/24 slots are eligible.

Post-hoc intervention 087 reproduces all eight selected original CPU/GPU
payloads byte exactly. Supplying CPU trigonometry removes the discrepancy
in two pixels (13450, 55934), with exact counters and mean error <=4.34e-19.
Six pixels retain mean/moment/counter discrepancies. Trigonometry alone is
insufficient; full causation is unestablished and no GPU reference is admitted.
Plan 023 records path/bounce diagnostics with aggregate replay required.

Deep-path diagnosis 089/091/092 reproduces every selected aggregate/counter
and establishes a signed-zero sampling-basis mechanism in all eight traced
original paths: nearby coplanar closest primitives have opposite zero signs
in normal.z, producing large next-direction changes under identical uniforms.
CPU sign-bit-only direction intervention matches the original CPU direction
exactly (8/8); the other 46 above-gate pixels are not individually traced.
Plan 024 tests a general ambiguity flag and independent complete CPU-path
recomputation, with all samples retained and unchanged admission gates.
It is a separate candidate; 082 remains failed, GPU references unadmitted.
The Renderer direct-zero pixels remain unresolved.

The general ambiguity-guard/whole-path CPU fallback feasibility 093 passes
unchanged numerical/counter/finite/direct/emission gates on all eight selected
pixels (mean <=8.674e-19, moment <=1.017e-20). It recomputes 11864/65536
paths without reference-radiance or hit/sign overrides. Audit 094 replays
all diagnostic GPU memory ledgers, verifies separate build 095 and confirms
53 frozen continuation inputs remain unchanged. Plan 025 streams the same
guard over complete frames with bounded per-dispatch storage. Its first full
C1 T_B8 seed-0 trial 096 has now passed; full sixteen-case/physical/all-state/
prefix admission remains unexecuted. CPU acquisition remains independent.

C1 T_B8 recovery now completes all four 32768-spp seeds with verified prefix
provenance (097). Active absolute p99 3.54031e-5 exceeds the fixed 1e-5 gate;
relative p99 2.51347% alone does not qualify the reference. The original
qualifier continues at 65536 spp. The remaining cap outcome is unmeasured.
Full-frame hybrid deep trial 096 completed with the frozen 64-epsilon
guard and original CPU fallback, 16-sample batches / 16 CPU workers. No GPU
reference is admitted from the selected success or the standalone build.

Full-frame C1 T_B8 seed-0 feasibility 096 **PASS** at unchanged gates:
max mean difference 1.38561e-16, moment difference 3.59820e-18, indirect
NRMSE 4.10311e-16, exact counters/primary/direct/emission, finite output, zero
faults and owned-memory replay PASS. CPU fallback recomputed 40861185 of
471859200 paths (~8.66%), with every path retained. Original 082 stays failed.
The new complete numerical suite 098 is executing; physical worker 099 waits
for that complete PASS. Separate prefix host build 100 succeeds, but prefix
runtime validation is NOT RUN. No reference admission or N010 READY yet.

### Completion evidence inventory

[102](results/102-completion-evidence-and-handoff.md) maps each unchanged
completion requirement to executed evidence, pending work and the runnable
final verification command. Actual full-gate preflight [103](results/103-interim-full-gate-preflight.json)
is NOT_READY: correctness accounting and additional-family source/device
boundaries pass, while full references, Sponza pilots and accepted timing
calibration remain pending. It is an interim check, not final result 047.

Prospective [hybrid acquisition plan 029](experiments/029-hybrid-reference-acquisition.md)
and `qualify_hybrid_references.py` now prepare a fresh, proof-gated high-sample
ladder without changing the live CPU view. Prerequisite checks 104–106 refused
GPU dispatch while 098 was incomplete (exit 2, no work root). Successful proof
validation/acquisition remains unexecuted; reference admission still requires
all unchanged gates and a separate completed-boundary provenance transition.

Full-frame C1 T_B8 seed 1 [107](results/107-hybrid-full-frame-deep-seed1-conformance.json) now passes
the unchanged numerical gates: maximum mean difference 8.67362e-17, moment
6.28498e-19 and indirect NRMSE 3.65583e-16; exact counters/primary/direct/emission,
finite output, zero faults and memory replay PASS. It is an exact-byte copy
of the completed 098 child result, not a repeat acquisition. The suite now
has 14/16 passing cases and proceeds to seed 2. Physical/all-state/prefix
proof and statistical qualification remain required; no reference is admitted.

CPU-only [raw-prefix export audit 108](results/108-hybrid-deep-raw-prefix-export-audit.json)
passes all pixels of both retained C1 B8 8192-spp seed-0/seed-1 cases: raw
sums/moments reconstruct saved binary64 values exactly, per-pixel counters
reproduce global metadata, all four PFM components agree, and memory replay
passes. This is a two-export consistency audit, not full prefix/runtime or
reference eligibility. A separate hybrid provenance API is prepared; the
existing frozen CPU view/preflight remains unchanged.

Existing eligible CPU-slot [provenance audit 109](results/109-existing-eligible-cpu-provenance-audit.json)
passes all fifteen selected references via the separate API's original-method
delegation: C1/C2/C3 B2 and C7–C12 both transports. Every canonical scene,
payload/header, convergence screen and imported-prefix chain is checked; all
recorded inputs remain unchanged after the audit. This is a selected fifteen-slot
audit, not whole-corpus readiness or execution of the new hybrid-variant branch.

C1 B8 / 8192 spp seed 2 [110](results/110-hybrid-full-frame-deep-seed2-conformance.json) passes
unchanged full-frame numerical gates, with exact counters/primary/direct/emission,
finite output, zero faults and owned-memory replay. This exact-byte copy of
the completed 098 child is not a repeat acquisition. At publication of 110, suite 098 had 15/16
cases passing and was executing the final seed; full physical/all-state/prefix
and statistical qualification are still required before reference use.

Full numerical suite [098](results/098-hybrid-full-numerical-conformance.json)
now completes all sixteen fixed cases with PASS. Physical 099 has started;
all-state/prefix 101 remains waiting. Numerical completion alone admits no
reference. All sixteen child result hashes were verified before publication.

Separate prospective [point-guided CPU sampling plan 030](experiments/030-prospective-point-guided-reference-sampling.md)
retains the original physical target and exact convergence gates. CPU build
[112](results/112-point-guided-oracle-build.json) passes and physical/iid
control acquisition 113 is executing. It changes continuation sampling and
importance weights only; it does not change the current Renderer or replace
any pending/accepted original reference.

Prospective [state/prefix plan 031](experiments/031-point-guided-state-and-prefix-validation.md)
requires all 24 original locked scenes/four seeds at 16 spp, exact direct/emission
and primary identities, zero own-prefix payload/counter disagreement at 8→16,
and both C7 transports at 8192→16384. Separate prefix build
[114](results/114-point-guided-prefix-build.json) passes. Runner 115 waits for
complete physical 113 PASS and has executed no state/prefix acquisition yet.
Neither build proves convergence or reference admission.

[Point-guided acquisition plan 032](experiments/032-point-guided-reference-qualification.md)
prepares all nine unfinished transport ladders, retaining the other fifteen
in the full corpus. [116](results/116-point-guided-qualification-prerequisite-check.json)
actually refuses acquisition at incomplete 113; all read bytes are archived.
The queue waits for complete 113/115 PASS before a single fresh acquisition.
No new sampling reference, successful new-variant audit or view replacement
has occurred. [117](results/117-point-guided-api-existing-cpu-provenance-audit.json)
passes only delegation to the existing audit on the fifteen original CPU
references. It does not attest new sampling, remaining nine slots or readiness.

[Readiness adapter 033](experiments/033-point-guided-readiness-adapter.md) keeps
all six exact original gates while dispatching reference audits through the
separate API. Actual [119](results/119-point-guided-adapter-interim-preflight.json)
executes against current view 067 and remains NOT_READY, retaining incomplete
reference/Sponza-pilot/calibration gates. The six gate names/pass classifications
match 103; all 162 recorded inputs were checked unchanged after execution.
No new sampling branch, current view/driver replacement or final 047 is attested.



Fresh isolated-fixture GPU [sizing 157](results/157-minimal-calibration-quiet-sizing.json)
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

### Minimal-output calibration commands (plan 044)

157 completed PASS; 158 was launched once and user-stopped (170). The commands
below document those actual invocations and must not be rerun into existing
paths. They require complete corrected build 159 (v2 binaries), and refuse
live research workers, existing work/output paths and partial boundary selection. Keep the new build/source/input identities frozen.
Sizing additionally checks every image against original quiet sizing 046 and
requires zero-teardown ledger replay within 8 GiB. Only complete full PASS 157
permits 158. Original failed/partial timing is retained.

```bash
LD_LIBRARY_PATH="$NIX_LD_LIBRARY_PATH" out/research/n010-comparison-readiness/venv/bin/python \
  scripts/research/n010_reference_sampling/calibrate_minimal_capture.py \
  --mode sizing \
  --lock research/lanes/n010-comparison-readiness/results/026-dynamic-execution-state-lock.json \
  --work out/research/n010-comparison-readiness/minimal-calibration-sizing-v1 \
  --output research/lanes/n010-comparison-readiness/results/157-minimal-calibration-quiet-sizing.json

LD_LIBRARY_PATH="$NIX_LD_LIBRARY_PATH" out/research/n010-comparison-readiness/venv/bin/python \
  scripts/research/n010_reference_sampling/calibrate_minimal_capture.py \
  --mode accepted \
  --lock research/lanes/n010-comparison-readiness/results/026-dynamic-execution-state-lock.json \
  --work out/research/n010-comparison-readiness/minimal-calibration-accepted-v1 \
  --plan research/lanes/n010-comparison-readiness/results/157-minimal-calibration-quiet-sizing.json \
  --output research/lanes/n010-comparison-readiness/results/158-minimal-calibration-full-renderer.json
```

All 24 eligible references, complete pilots and final six-gate handoff remain
required even if this independent capability measurement eventually passes.



Prospective [recovery plan 047](experiments/047-prospective-directional-control-recovery.md)
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

### Prepared interrupted-control recovery commands (plan 047)

163/164 completed PASS; 165 was user-stopped before its first level (171).
Commands identify those one-time acquisitions; do not restart
existing work/results. Execute later steps only after complete proof PASS
and all other research workers, and only after complete PASS of the preceding
step. The old workflow is not restarted. These paths must not already exist.
There is no automatic waiting/retry controller.

```bash
LD_LIBRARY_PATH="$NIX_LD_LIBRARY_PATH" out/research/n010-comparison-readiness/venv/bin/python \
  scripts/research/n010_reference_sampling/recover_primary_direction_physical.py \
  --work out/research/n010-comparison-readiness/primary-direction-physical-recovery-v1 \
  --output research/lanes/n010-comparison-readiness/results/163-primary-direction-recovered-physical-controls.json

LD_LIBRARY_PATH="$NIX_LD_LIBRARY_PATH" out/research/n010-comparison-readiness/venv/bin/python \
  scripts/research/n010_reference_sampling/validate_recovered_primary_direction_prefix.py \
  --work out/research/n010-comparison-readiness/primary-direction-prefix-proof-recovery-v1 \
  --output research/lanes/n010-comparison-readiness/results/164-primary-direction-recovered-all-state-and-prefix.json

LD_LIBRARY_PATH="$NIX_LD_LIBRARY_PATH" out/research/n010-comparison-readiness/venv/bin/python \
  scripts/research/n010_reference_sampling/acquire_recovered_primary_direction_feasibility.py \
  --work out/research/n010-comparison-readiness/primary-direction-feasibility-recovery-v1 \
  --output research/lanes/n010-comparison-readiness/results/165-primary-direction-recovered-bounded-feasibility.json
```

Complete recovery controls alone do not admit references. The original
plan-046 intake still refuses incomplete 152. The conditional Amendment-1
adapter below supplies the explicit new-chain dispatch; its actual full
payload/command/resource replay is still required before reference admission.
All sixteen retained eligible slots, eight pending slots and final gates stay.



[Plan-047 Amendment 1](experiments/047-prospective-directional-control-recovery.md)
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

### Conditional eight-slot intake after recovered controls

Prepared only; no acquisition has run. Under plan 053, this pending API
requires actual complete 151/163/164/180 PASS and no CPU/GPU research worker:

```bash
LD_LIBRARY_PATH="$NIX_LD_LIBRARY_PATH" out/research/n010-comparison-readiness/venv/bin/python \
  scripts/research/n010_reference_sampling/qualify_recovered_primary_direction_references.py \
  --lock research/lanes/n010-comparison-readiness/results/026-dynamic-execution-state-lock.json \
  --work out/research/n010-comparison-readiness/primary-direction-reference-ladders-v1 \
  --output research/lanes/n010-comparison-readiness/results/166-recovered-primary-direction-reference-qualification.json
```

This explicit Amendment-1 adapter supersedes the original proof dispatch for
future new-variant acquisition only. The original plan-046 API remains frozen
with view 160; original/hybrid references retain their original proof chains.
Full 24-slot admission, all pilots, accepted calibration and six-gate final
047 remain mandatory. A partial or failed 158 cannot pass readiness.



CPU-only post-hoc [diagnosis 162](results/162-minimal-static-calibration-posthoc-diagnosis.json)
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

### Prospective row-bulk PFM calibration fixture (plan 048)

[Plan 048](experiments/048-prospective-bulk-pfm-calibration-output.md) changes
only the two PFM output loops to one identical RGB row write. Its source
inverse checks reconstruct the exact build-159 files; build and calibration
CLI assembly succeeds. No native compile, serialization/runtime replay,
new GPU run or accepted capability is established. Source 158 stays frozen.

Build 167 below completed PASS after actual termination of 158. GPU commands
168 completed full PASS; 169 has started. The commands identify one-time
acquisitions and must never restart existing paths. Build 167 may coexist with CPU reference controls, but refuses
GPU research/calibration. Run 168 only after all CPU/GPU workers terminate and
167 completes PASS; run 169 only after complete full PASS 168. All paths are
fresh; there is no automatic retry or partial-boundary selection.

```bash
LD_LIBRARY_PATH="$NIX_LD_LIBRARY_PATH" out/research/n010-comparison-readiness/venv/bin/python \
  scripts/research/n010_reference_sampling/build_bulk_pfm_calibration_capture.py \
  --work out/research/n010-comparison-readiness/minimal-calibration-build-v3 \
  --output research/lanes/n010-comparison-readiness/results/167-bulk-pfm-calibration-fixture-build.json

LD_LIBRARY_PATH="$NIX_LD_LIBRARY_PATH" out/research/n010-comparison-readiness/venv/bin/python \
  scripts/research/n010_reference_sampling/calibrate_bulk_pfm_capture.py \
  --mode sizing \
  --lock research/lanes/n010-comparison-readiness/results/026-dynamic-execution-state-lock.json \
  --work out/research/n010-comparison-readiness/bulk-pfm-calibration-sizing-v1 \
  --output research/lanes/n010-comparison-readiness/results/168-bulk-pfm-calibration-quiet-sizing.json

LD_LIBRARY_PATH="$NIX_LD_LIBRARY_PATH" out/research/n010-comparison-readiness/venv/bin/python \
  scripts/research/n010_reference_sampling/calibrate_bulk_pfm_capture.py \
  --mode accepted \
  --lock research/lanes/n010-comparison-readiness/results/026-dynamic-execution-state-lock.json \
  --work out/research/n010-comparison-readiness/bulk-pfm-calibration-accepted-v1 \
  --plan research/lanes/n010-comparison-readiness/results/168-bulk-pfm-calibration-quiet-sizing.json \
  --output research/lanes/n010-comparison-readiness/results/169-bulk-pfm-calibration-full-renderer.json
```

The new method keeps all sixteen boundaries, every sample, old exact
schedule/statistics/thresholds, every image/scratch witness and zero-teardown
8 GiB ledger checks. All 24 eligible references and final pilots/047 remain
required regardless of this future measurement outcome.


### Final recovered-reference and fixture-proof audit (plan 049)

The auditor is prepared; Python/source assembly and `--help` succeed. It has
**not executed its six numerical gates**. Dispatch only after all 24 references
admit, all original complete pilots exist, full 168/169 pass and no research
worker is live. This is the final one-time result 047, not an interim status
probe. The separate remaining-pilot driver is prepared below; this auditor
does not acquire missing pilots or calibration.

```bash
LD_LIBRARY_PATH="$NIX_LD_LIBRARY_PATH" out/research/n010-comparison-readiness/venv/bin/python \
  scripts/research/n010_reference_sampling/readiness_preflight_recovered_primary_direction.py \
  --lock research/lanes/n010-comparison-readiness/results/026-dynamic-execution-state-lock.json \
  --references out/research/n010-comparison-readiness/full-corpus-primary-direction-view-v1 \
  --reference-view-record research/lanes/n010-comparison-readiness/results/160-primary-direction-reference-view.json \
  --calibration research/lanes/n010-comparison-readiness/results/169-bulk-pfm-calibration-full-renderer.json \
  --dynamic-pilots research/lanes/n010-comparison-readiness/results/019-controlled-dynamic-cohort.json research/lanes/n010-comparison-readiness/results/037-controlled-dynamic-pt1024.json research/lanes/n010-comparison-readiness/results/048-sponza-dynamic-cohort.json \
  --static-pilots research/lanes/n010-comparison-readiness/results/044-c1-complete-pt-quality-ladder.json research/lanes/n010-comparison-readiness/results/013-c7-pt-cohort-pilot.json research/lanes/n010-comparison-readiness/results/024-c8-pt-quality-ladder.json research/lanes/n010-comparison-readiness/results/025-c9-pt-quality-ladder.json \
  --output research/lanes/n010-comparison-readiness/results/047-readiness-preflight.json
```


### Remaining full pilots after actual proof admission (plan 049 Amendment 1)

Prepared, **not run**. Under plan 053 reference dispatch only after
151/163/164/180/166 and full 167/168/169
complete PASS, all 24 references verify and every CPU/GPU research worker
terminates. The command refuses missing proofs before creating its work root.
It acquires original 043/044/048 once, retains all quality losses and memory
ledgers, and does not rerun old calibration. Run the separate final auditor
above only after this process actually terminates. No pilot timing becomes an
accepted Lane M performance measurement.

```bash
LD_LIBRARY_PATH="$NIX_LD_LIBRARY_PATH" out/research/n010-comparison-readiness/venv/bin/python \
  scripts/research/n010_reference_sampling/finish_recovered_primary_direction_readiness.py \
  --work out/research/n010-comparison-readiness/final-comparison-pilots-recovered-v1 \
  --lock research/lanes/n010-comparison-readiness/results/026-dynamic-execution-state-lock.json \
  --references out/research/n010-comparison-readiness/full-corpus-primary-direction-view-v1 \
  --reference-view-record research/lanes/n010-comparison-readiness/results/160-primary-direction-reference-view.json
```

### User-stopped fresh feasibility (plan 050, stop 176)

172 started once after actual termination of GPU 169 and diagnostic 174,
then was user-stopped before its first seed export (176).
The command identifies that acquisition; never restart its existing paths. Preserve 165 and its v1 work
path. No numerical level completed. 172 cannot admit 166; plan 053 now
requires actual complete 180 PASS. All original full-reference gates remain
unchanged. The following command is historical and must not be rerun.

```bash
LD_LIBRARY_PATH="$NIX_LD_LIBRARY_PATH" out/research/n010-comparison-readiness/venv/bin/python \
  scripts/research/n010_reference_sampling/acquire_post_stop_primary_direction_feasibility.py \
  --work out/research/n010-comparison-readiness/primary-direction-feasibility-recovery-v2 \
  --output research/lanes/n010-comparison-readiness/results/172-primary-direction-post-stop-bounded-feasibility.json
```

### Completed reversible IDE visibility diagnostic (plan 051)

174 completed its local suppression/restoration classifier PASS. The command
identifies that one-time acquisition; do not restart existing paths. It required
complete 169 with all sixteen
boundaries/eight blocks and no research workers. All 169 FAILs stay FAIL.
It briefly moves the single registered IDE window to an undisplayed special
workspace, restores its original workspace/focus and verifies exact attributes.
It can precede CPU 172; this is environment diagnosis, not accepted timing.
The classifier cannot admit references, calibration or Lane M. Refuse existing
paths and changed PID/window identities; preserve any failures without retry.

```bash
LD_LIBRARY_PATH="$NIX_LD_LIBRARY_PATH" out/research/n010-comparison-readiness/venv/bin/python \
  scripts/research/n010_reference_sampling/diagnose_ide_visibility_accounting.py \
  --work out/research/n010-comparison-readiness/ide-visibility-diagnostic-v1 \
  --output research/lanes/n010-comparison-readiness/results/174-ide-visibility-accounting-diagnostic.json
```

### Full calibration with IDE undisplayed (plan 052)

The registered IDE window is temporarily moved to an undisplayed special
workspace during each acquisition and restored afterward. Its original
PID/client/window identities and sampled local graphics-accounting condition
are operational guards, not GPU utilization estimates or changed timing gates.
Refuse existing paths and other research workers. Keep stopped 172 immutable.
All original sixteen boundaries are mandatory. Run 178 only after actual
complete full PASS 177, restoration and actual controller termination.
177 is complete PASS; 178 is terminal INCOMPLETE / NOT ACCEPTED.
Both commands are historical identifiers; never rerun their existing paths.
These commands identify one-time acquisitions; never rerun their paths. A scientific precision FAIL still completes all sixteen boundaries.
An operational guard failure retains partials and prevents timing admission.

```bash
LD_LIBRARY_PATH="$NIX_LD_LIBRARY_PATH" out/research/n010-comparison-readiness/venv/bin/python \
  scripts/research/n010_reference_sampling/calibrate_hidden_ide_bulk_pfm.py \
  --mode sizing \
  --lock research/lanes/n010-comparison-readiness/results/026-dynamic-execution-state-lock.json \
  --work out/research/n010-comparison-readiness/hidden-ide-bulk-pfm-sizing-v1 \
  --output research/lanes/n010-comparison-readiness/results/177-hidden-ide-bulk-pfm-calibration-sizing.json

LD_LIBRARY_PATH="$NIX_LD_LIBRARY_PATH" out/research/n010-comparison-readiness/venv/bin/python \
  scripts/research/n010_reference_sampling/calibrate_hidden_ide_bulk_pfm.py \
  --mode accepted \
  --lock research/lanes/n010-comparison-readiness/results/026-dynamic-execution-state-lock.json \
  --work out/research/n010-comparison-readiness/hidden-ide-bulk-pfm-accepted-v1 \
  --plan research/lanes/n010-comparison-readiness/results/177-hidden-ide-bulk-pfm-calibration-sizing.json \
  --output research/lanes/n010-comparison-readiness/results/178-hidden-ide-bulk-pfm-calibration-full-renderer.json
```

Source assembly proves the whole generated program reverses exactly to the
frozen plan-048 program; all original scientific function definitions remain
byte-identical. Source compilation and CLI help are not GPU measurements,
software regression validation, reference admission or readiness. Unit tests
were not run. The existing plan-049 verifier/driver still requires actual
167/168/169 PASS and therefore rejects 169. A new guarded proof-intake adapter
must verify actual complete 167/177/178 before selecting that timing proof.
`hidden_ide_timing_provenance.py` now provides that strict adapter with whole
original-verifier inverse proof. Actual post-hoc replay 179 retains three FAIL boundaries and rejects
incomplete 178. Full payload admission has not run and timing remains unproved.

### Fresh feasibility after stop 176 (plan 053)

Completed once at checkpoint `6f6b557`. Both registered levels finish:
8192/16384 spp ratios are **1.0703554221788882 / 1.0599135470235277**,
both FAIL against <=0.75. Primary/direct/emission remain exact. The bounded
campaign is COMPLETE/FAIL; its two-level reference screen remains
INCOMPLETE/ineligible. This is not a 262144-spp cap failure. Corpus acquisition
166 is NOT RUN and cannot consume this failed proof. The command below is
historical; never rerun its existing paths. All exact outputs are retained.
Plan 053 Amendment 1 permits CPU-only continuation
after terminal 178 and documented host/session termination, with exact 181/182
identities, matching current boot and no research workers. Old restoration
failure remains immutable; this alternative grants no GPU timing admission.
No waiting/restart worker is installed. Keep 165/v1 and 172/v2 immutable.
Begin from sample zero at the separate v3 path; only its own complete prefix
may continue to 16384. The bounded two-level question, four seeds, executable,
limits and scientific gates are unchanged. Completed 180 FAIL stops corpus
intake; only actual full 180 PASS permits still-unexecuted 166.

```bash
LD_LIBRARY_PATH="$NIX_LD_LIBRARY_PATH" out/research/n010-comparison-readiness/venv/bin/python \
  scripts/research/n010_reference_sampling/acquire_after_second_stop_primary_direction_feasibility.py \
  --work out/research/n010-comparison-readiness/primary-direction-feasibility-recovery-v3 \
  --output research/lanes/n010-comparison-readiness/results/180-primary-direction-second-stop-bounded-feasibility.json
```

Full source inversion reconstructs the prior plan-050 generated program
(`d9d2ac08a54c35b09e4940537c3da14d65b3036ac0be1984305d325a81d8464b`).
The pending API's five declared documentation/dispatch/plan changes reverse
to its complete source SHA256
`ec98f3ec41950b01b1b4565e9ae671a85e57ff7b95b916b24a03e987ac61401d`
at `3b7c566`. Source assembly is not acquisition, reference eligibility or
readiness. No unit tests or runtime regression validation were run.

### Post-hoc decision replay after 178 actually terminates

Executed once; **complete analysis, calibration NOT ACCEPTED**. The CPU-only
report 179 preserves every full
scientific PASS/FAIL and every incomplete boundary, with no exclusions,
corrections, retries or new thresholds. It replays original schedules,
statistics, owned-memory event ledgers, all frozen inputs and the sampled
visibility/restoration evidence. Environment replay alone cannot admit timing;
strict intake still requires actual full numerical PASS and all native payloads.
Executed after actual controller/native termination, before any 180 data.
The following command is historical; never overwrite existing 179.

```bash
LD_LIBRARY_PATH="$NIX_LD_LIBRARY_PATH" out/research/n010-comparison-readiness/venv/bin/python \
  scripts/research/n010_reference_sampling/summarize_hidden_ide_calibration.py \
  --output research/lanes/n010-comparison-readiness/results/179-hidden-ide-calibration-decision-and-replay.json
```

On scientific FAIL, strict intake refuses before expensive native payload
verification. The report must distinguish that scope from complete payload
rehashing or radiance/timestamp regeneration; its replay is not software
regression validation. The source compiles and the strict whole-verifier
inverse remains exact. Replay covers 25 complete blocks / 1600 samples and
684 frozen fixture identities; full native-payload admission was rejected.


### Deferred CPU image serialization (plan 054)

Build 184 is complete. The build command is historical; never rerun its path.
CPU source assembly/CLI help and strict-verifier inverse proof are complete;
**sizing 185 completed all sixteen boundaries PASS**; full 186 and full
proof intake have NOT RUN. CPU feasibility 180 has actually terminated FAIL.
The sizing command below is historical; never rerun its existing paths.
Sizing/full calibration are separate one-time commands; no waiting controller
is installed. Never dispatch full 186 without actual complete all-sixteen 185
PASS, stable original input hashes and matching sizing boot/device/driver.
No desktop-window/display changes are performed by these commands.

```bash
LD_LIBRARY_PATH="$NIX_LD_LIBRARY_PATH" out/research/n010-comparison-readiness/venv/bin/python \
  scripts/research/n010_reference_sampling/calibrate_deferred_image_capture.py \
  --mode sizing \
  --lock research/lanes/n010-comparison-readiness/results/026-dynamic-execution-state-lock.json \
  --work out/research/n010-comparison-readiness/deferred-image-calibration-sizing-v1 \
  --output research/lanes/n010-comparison-readiness/results/185-deferred-image-calibration-sizing.json

LD_LIBRARY_PATH="$NIX_LD_LIBRARY_PATH" out/research/n010-comparison-readiness/venv/bin/python \
  scripts/research/n010_reference_sampling/calibrate_deferred_image_capture.py \
  --mode accepted \
  --lock research/lanes/n010-comparison-readiness/results/026-dynamic-execution-state-lock.json \
  --work out/research/n010-comparison-readiness/deferred-image-calibration-accepted-v1 \
  --plan research/lanes/n010-comparison-readiness/results/185-deferred-image-calibration-sizing.json \
  --output research/lanes/n010-comparison-readiness/results/186-deferred-image-calibration-full-renderer.json
```

The generated acquisition program reverses completely to original plan 048
SHA256 `18f906fee96fc1cbb43f9f225c4c6ea35224cac01e6d9736647308e56436b55c`.
Only declared fixture/proof/work dispatch changes in the original function
prelude; schedule/statistical bodies remain byte-identical. The strict intake
adapter `deferred_image_timing_provenance.py` reverses completely to original
049 SHA256 `49ac6660fe17e8895be2a0d600771a8e844358867fe57014f0066105b247b9a8`.
Neither proof assembly admits failed 169, incomplete 178, an eligible reference,
a different workload's timing or final READY. All original six gates remain.


### Deferred-calibration final pilot and six-gate dispatch (plan 055)

Both adapters are prepared; **not run**. Source assembly and CLI help complete.
The complete parent-module inverses are exact (pilot parent `7a7cff2449d5...`,
auditor parent `c485165c1ec8...`), retaining inherited whole-source inverses to
original scientific drivers `53b173...` / `87985c...`. All six original gate
names and the five non-calibration function bodies remain unchanged. New source
provenance records both parent/new adapters, plan 055 and the actual verifier.

The old plan-049 entries above still require failed 169 and refuse admission.
The entries below select only actual full 184/185/186 proof; they do not alias
negative records to PASS. Require actual complete 180/166 PASS and independent
full 24-slot reference verification. Never create or start a waiting worker.

Only after complete required proofs and all research workers terminate:

```bash
LD_LIBRARY_PATH="$NIX_LD_LIBRARY_PATH" out/research/n010-comparison-readiness/venv/bin/python \
  scripts/research/n010_reference_sampling/finish_deferred_primary_direction_readiness.py \
  --work out/research/n010-comparison-readiness/final-comparison-pilots-deferred-image-v1 \
  --lock research/lanes/n010-comparison-readiness/results/026-dynamic-execution-state-lock.json \
  --references out/research/n010-comparison-readiness/full-corpus-primary-direction-view-v1 \
  --reference-view-record research/lanes/n010-comparison-readiness/results/160-primary-direction-reference-view.json
```

Only after the actual pilot driver exits with full completed pilots, dispatch
this separate one-time final auditor. It refuses existing 047 and live research
workers. A source assembly or diagnostic preflight is not a final gate result.

```bash
LD_LIBRARY_PATH="$NIX_LD_LIBRARY_PATH" out/research/n010-comparison-readiness/venv/bin/python \
  scripts/research/n010_reference_sampling/readiness_preflight_deferred_primary_direction.py \
  --lock research/lanes/n010-comparison-readiness/results/026-dynamic-execution-state-lock.json \
  --references out/research/n010-comparison-readiness/full-corpus-primary-direction-view-v1 \
  --reference-view-record research/lanes/n010-comparison-readiness/results/160-primary-direction-reference-view.json \
  --calibration research/lanes/n010-comparison-readiness/results/186-deferred-image-calibration-full-renderer.json \
  --dynamic-pilots research/lanes/n010-comparison-readiness/results/019-controlled-dynamic-cohort.json research/lanes/n010-comparison-readiness/results/037-controlled-dynamic-pt1024.json research/lanes/n010-comparison-readiness/results/048-sponza-dynamic-cohort.json \
  --static-pilots research/lanes/n010-comparison-readiness/results/044-c1-complete-pt-quality-ladder.json research/lanes/n010-comparison-readiness/results/013-c7-pt-cohort-pilot.json research/lanes/n010-comparison-readiness/results/024-c8-pt-quality-ladder.json research/lanes/n010-comparison-readiness/results/025-c9-pt-quality-ladder.json \
  --output research/lanes/n010-comparison-readiness/results/047-readiness-preflight.json
```

Pilot time remains diagnostic. Lane M timing requires the exact admitted
fixture/boundary or its own calibration; no capability is transferred into old
or new preparation-pilot timings. No unit tests/runtime regression checks were
run during this source-only adapter preparation.


### Nested prefix scrambling candidate (plan 056)

Separate from failed first-level 180, [187](results/187-nested-scramble-oracle-build.json)
compiles original cached-cosine standalone/prefix binaries with only the
uniform scrambling and diagnostic metadata changed. There is no direction
pilot or extra scored path per spp. Input-prefix-dependent binary permutations
preserve dyadic occupancy; this does not prove improved RQMC error. All
scientific outcomes remain unmeasured. Whole parent-driver inversions preserve
the original physical, state/prefix and two-level feasibility gates.

The commands below are **not run**. First finish actual CPU 180, then GPU
185/186 (or record its actual terminal failure) and verify no other research
worker. The dispatch guard enforces this ordering before creating outputs.
Invoke each stage once, sequentially, only after its complete predecessor
PASS. Existing outputs are refused; no waiting option or retry is allowed.

```bash
LD_LIBRARY_PATH="$NIX_LD_LIBRARY_PATH" out/research/n010-comparison-readiness/venv/bin/python \
  scripts/research/n010_reference_sampling/validate_nested_scramble.py \
  --work out/research/n010-comparison-readiness/owen-reference-physical-v1 \
  --output research/lanes/n010-comparison-readiness/results/188-nested-scramble-physical-controls.json

LD_LIBRARY_PATH="$NIX_LD_LIBRARY_PATH" out/research/n010-comparison-readiness/venv/bin/python \
  scripts/research/n010_reference_sampling/validate_nested_scramble_prefix.py \
  --work out/research/n010-comparison-readiness/owen-reference-prefix-v1 \
  --output research/lanes/n010-comparison-readiness/results/189-nested-scramble-all-state-and-prefix.json

LD_LIBRARY_PATH="$NIX_LD_LIBRARY_PATH" out/research/n010-comparison-readiness/venv/bin/python \
  scripts/research/n010_reference_sampling/acquire_nested_scramble_feasibility.py \
  --work out/research/n010-comparison-readiness/owen-reference-feasibility-v1 \
  --output research/lanes/n010-comparison-readiness/results/190-nested-scramble-bounded-feasibility.json
```

Both original-baseline ratios must be <=0.75 at 8192/16384. Failure stops this
candidate. Even full PASS does not admit corpus references: a later prospective
full 24-slot provenance/qualification transition is still required, with
unchanged six levels through 262144, support and 1e-5 / 5% screens. Existing
166/180 proof chains are not rewritten. Active/default Renderer/build graph
and historical results remain unchanged; unit/regression tests were not run.
