# Forward research roadmap — major gates only

**No new GI algorithm study is part of the October 2026 history consolidation.** The current evidence-backed Renderer is a baseline for further work, not an announced replacement for existing GI.

## Phase 1 — establish competitiveness

**Question:** Under a valid quality reference and a fair end-to-end measurement boundary, how competitive is the current Renderer?

- [Issue #4 / N007](https://github.com/owoDra/real-time-gi-lab/issues/4) is **CLOSED as bounded NO GO**: moving-rigid CPU reference remained fully black through the frozen four-seed 512–8192-SPP ladder, while a probe-shadow counterfactual explained 9,247/9,247 positive pixels in the current GPU diagnostic frame. [Result 012](lanes/n007-reference-validity/results/012-n007-bounded-no-go-decision.md) preserves unmeasured regimes and frozen N006 outcomes. [Issue #5 / N008](https://github.com/owoDra/real-time-gi-lab/issues/5) concluded: independently validated oracle GO ([Phase A result 004](lanes/n008-hdr-oracle/results/004-phase-a-exit-decision.md)), cross-class reference set bounded NO GO ([final result 011](lanes/n008-hdr-oracle/results/011-n008-final-decision.md)). These studies remain closed research outcomes; a statistical screen does not replace physical validity.
- **N009 concluded (2026-10-14): SC NO GO / BF1–BF3 PASS / PT INCOMPLETE.** [Final result 009](lanes/n009-scene-contract/results/009-n009-final-decision.md). Under C1, C1/C2/C4/C5/C6 have full total support but only deterministic direct references; both T_B2/T_B8 totals fail the unchanged four-seed 8192-SPP cap. Amendment 1 leaves C3 light motion NOT_CONSTRUCTIBLE. BF gates pass on C7; C7 V1 and old B4 V3 failures prevent COMPLETE attribution. Excluding 21 V1 pixels is post-hoc sensitivity. Sponza direct max-relative-error-1.0 pixels remain unresolved (未解決).
- **N010 is the final preparation gate (active):** [preregistered protocol](lanes/n010-comparison-readiness/experiments/001-comparison-readiness.md). Finish reference eligibility, direct/key correctness diagnostics, RC/path-tracing executable controls, matched HDR quality scoring, complete Renderer GPU timing calibration and allocation-lifetime memory accounting here. Require an executed comparison pilot and fail-closed readiness preflight; plans alone cannot pass. N009's negative result and thresholds remain frozen. C1/BF-P default adoption requires a separate architecture decision and executable checks.
- **N010 execution progress:** C7 now has qualified T_B2/T_B8 references and an executed PT budget ladder with quality passes; incumbent/dense RC losses are retained. Construction corpus is locked through C12. Controlled dynamic comparisons and C8/C9 matching budget ladders are complete; Sponza qualification/pilots and full Renderer timing calibration remain required; quality failure does not reopen preparation.
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
