# Forward research roadmap — major gates only

**No new GI algorithm study is part of the October 2026 history consolidation.** The current evidence-backed Renderer is a baseline for further work, not an announced replacement for existing GI.

## Phase 1 — establish competitiveness

**Question:** Under a valid quality reference and a fair end-to-end measurement boundary, how competitive is the current Renderer?

- [Issue #4 / N007](https://github.com/owoDra/real-time-gi-lab/issues/4) is **CLOSED as bounded NO GO**: moving-rigid CPU reference remained fully black through the frozen four-seed 512–8192-SPP ladder, while a probe-shadow counterfactual explained 9,247/9,247 positive pixels in the current GPU diagnostic frame. [Result 012](lanes/n007-reference-validity/results/012-n007-bounded-no-go-decision.md) preserves unmeasured regimes and frozen N006 outcomes. [Issue #5 / N008](https://github.com/owoDra/real-time-gi-lab/issues/5) concluded: independently validated oracle GO ([Phase A result 004](lanes/n008-hdr-oracle/results/004-phase-a-exit-decision.md)), cross-class reference set bounded NO GO ([final result 011](lanes/n008-hdr-oracle/results/011-n008-final-decision.md)). These studies remain closed research outcomes; a statistical screen does not replace physical validity.
- **N009 concluded (2026-10-14): SC NO GO / BF1–BF3 PASS / PT INCOMPLETE.** [Final result 009](lanes/n009-scene-contract/results/009-n009-final-decision.md). Under C1, C1/C2/C4/C5/C6 have full total support but only deterministic direct references; both T_B2/T_B8 totals fail the unchanged four-seed 8192-SPP cap. Amendment 1 leaves C3 light motion NOT_CONSTRUCTIBLE. BF gates pass on C7; C7 V1 and old B4 V3 failures prevent COMPLETE attribution. Excluding 21 V1 pixels is post-hoc sensitivity. Sponza direct max-relative-error-1.0 pixels remain unresolved (未解決).
- **N010 is the final preparation gate (active):** [preregistered protocol](lanes/n010-comparison-readiness/experiments/001-comparison-readiness.md). Finish reference eligibility, direct/key correctness diagnostics, RC/path-tracing executable controls, matched HDR quality scoring, complete Renderer GPU timing calibration and allocation-lifetime memory accounting here. Require an executed comparison pilot and fail-closed readiness preflight; plans alone cannot pass. N009's negative result and thresholds remain frozen. C1/BF-P default adoption requires a separate architecture decision and executable checks.
- **N010 execution progress:** C7 now has qualified T_B2/T_B8 references and an executed PT budget ladder with quality passes; incumbent/dense RC losses are retained. Construction corpus is locked through C12. Controlled dynamic comparisons and C8/C9 matching budget ladders are complete. Sponza C1 T_B2 now has an eligible reference: incumbent indirect NRMSE 88.8399% / bias +35.8544% is FAIL; pixel PT passes at 256/1024 spp. Remaining Sponza qualification/pilots and full Renderer timing calibration are required; quality failure does not reopen preparation. [Interim comparisons](lanes/n010-comparison-readiness/results/033-interim-comparison-findings.md).
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
The 32768 level is executing. Observed aggregate child CPU time also identifies
a possible operational guard interruption at high levels. Resolve that budget
prospectively while retaining own prefixes, scientific gates, sample cap and
all outcomes; no runtime limits have been changed. Forecasts do not establish
either an interruption or statistical cap failure. Full qualification is pending.

Plan 032 prepares point-guided acquisition of every unfinished transport,
retaining the fifteen eligible original-method references within the full
24-slot corpus. Actual 116 refuses acquisition at incomplete physical 113;
its exact read bytes are retained. API delegation 117 passes the existing
fifteen-slot subset; that historical check did not execute the new-variant branch
(now exercised by first-level audit 136). The
old acquisition queue terminated on the 113 failure without dispatch. A fresh
plan-036 queue now executes 128 after complete 125/126 PASS. Neither queue,
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
