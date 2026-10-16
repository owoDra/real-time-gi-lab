# Forward research roadmap — major gates only

## Current execution checkpoint — 2026-10-16 JST

Full [row-bulk calibration 169](lanes/n010-comparison-readiness/results/169-bulk-pfm-calibration-full-renderer.json)
is now **COMPLETE / FAIL / NOT ACCEPTED**. All sixteen boundaries finish eight
fresh-process blocks each: **C1 PT B8 and C6 PT B8 PASS; the other fourteen FAIL**
the original precision gates. No subset is accepted. All 128 blocks / 8,192
samples and original payloads are retained. Exact result SHA256:
`dddca3bfa7d2f0847e683352593519165829963d49fd173a29b698ba825d6add`.
The controller/native processes have actually terminated; there is no restart
or waiting worker. No timing threshold, correction or exclusion changed.

CPU [decision/replay 175](lanes/n010-comparison-readiness/results/175-bulk-pfm-calibration-decision-and-replay.json)
recomputes every original schedule and statistical decision exactly, replays
all 128 owned-allocation ledgers to teardown zero within 8 GiB, and rehashes
671 frozen fixture inputs. Maximum true-peak owned bytes: **375,184,080**.
It does not independently rehash every GPU payload or regenerate timestamps
or radiance. Producer image/scratch/manifests remain in exact complete 169.
This is scientific-analysis/ledger replay, not software regression validation;
unit tests were not run. Complete sizing [168](lanes/n010-comparison-readiness/results/168-bulk-pfm-calibration-quiet-sizing.json)
remains full PASS; sizing/compilation alone cannot establish accepted timing.

Post-hoc [173](lanes/n010-comparison-readiness/results/173-posthoc-concurrent-drm-client-diagnosis.json)
observes IDE graphics accounting on the same AMD device during three sampled
live-calibration intervals. This is not proved causation of the precision
failures, exact per-query overlap or instantaneous utilization. Prospective
[plan-051 diagnostic 174](lanes/n010-comparison-readiness/results/174-ide-visibility-accounting-diagnostic.json)
now completes all visible/hidden/restored A/B/A phases and its fixed **local
accounting-suppression classifier PASS**. The same client's accounted graphics
rates are **22.8578 / 0 / 22.9617 million ns per elapsed second**; all three
hidden intervals have zero increment. Original PID/window identities, eight
input hashes and exact workspace/geometry/focus restoration are verified.
No application stopped or power/clock/idle preference changed. This is local
counter suppression, **not causal proof for prior calibration failures, physical
GPU utilization, global quiescence or accepted timing**. Exact 174 SHA256:
`c8c8a7a00662344f48de9a6f266ac976f789b9594d3e6bc336a3dacb1aa7ef8b`.
A separate prospective full-boundary acquisition under this visibility policy
is still required; all original timing gates remain unchanged. CPU 172 is
now stopped as recorded below.

Reference work remains **16/24 eligible slots, eight pending** in immutable
view [160](lanes/n010-comparison-readiness/results/160-primary-direction-reference-view.json). Physical
[163](lanes/n010-comparison-readiness/results/163-primary-direction-recovered-physical-controls.json)
passes all seventeen scenes, eight physical checks and two iid comparisons;
[state/prefix 164](lanes/n010-comparison-readiness/results/164-primary-direction-recovered-all-state-and-prefix.json)
passes all 24 states, both actual C7 transports and all 78 native invocations.
These controls alone admit no reference. Feasibility 165 was user-stopped
before its first seed export or level; exact partials and [stop 171](lanes/n010-comparison-readiness/results/171-user-requested-recovered-feasibility-stop.json)
remain unchanged, with **INCOMPLETE, no numerical PASS/FAIL or cap-failure**.
Prospective [plan 050](lanes/n010-comparison-readiness/experiments/050-prospective-zero-export-feasibility-recovery.md)
prepares fresh result **172** from sample zero at a separate v2 path. No 165
partials are imported. The pending provenance API requires actual
151/163/164/172 PASS before still-unexecuted eight-slot 166. Seeds, samples,
full-support/uncertainty gates, cap and resource limits remain unchanged.
CPU 172 was subsequently **user-stopped before its first seed export or
complete level**. [Stop 176](lanes/n010-comparison-readiness/results/176-user-requested-post-stop-feasibility-stop.json)
records both actual process exits and two empty research-worker scans. The exact
partial 172 SHA256 is `f5d50696c8e85f36ea6a3c5ab13f967248c06a2b647cb31c84db127e757c42cb`.
All four partial/receipt files are retained. This is **INCOMPLETE, no numerical
PASS/FAIL or scientific cap-failure**. Do not restart 172 or its existing v2
work path. 166 remains unexecuted because actual full feasibility PASS is absent.
Independent prospective timing preparation can continue after verified
quiescence; stopped CPU work is not restarted.

All **24 eligible references**, complete C1 B8 / C2–C6 quality-memory pilots,
full actual timing capability and executed final six-gate **047 READY** remain
mandatory. The pilot driver and final auditor are prepared but unexecuted;
their original numerical bodies and all six gate names remain unchanged.
Historical pilot timing stays diagnostic. Direct max-relative-error-1.0 pixels
remain **UNRESOLVED / 未解決**, included without masks. Default Renderer/build
behavior and N001–N009 results remain unchanged. N010 stays active; Lane M
comparative acquisition has not started. No N011, CUDA or Actions.

Earlier live-status descriptions retained below are historical publication
checkpoints; this section reports the current execution state.

**No new GI algorithm study is part of the October 2026 history consolidation.** The current evidence-backed Renderer is a baseline for further work, not an announced replacement for existing GI.

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
