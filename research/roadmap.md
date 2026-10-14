# Forward research roadmap — major gates only

**No new GI algorithm study is part of the October 2026 history consolidation.** The current evidence-backed Renderer is a baseline for further work, not an announced replacement for existing GI.

## Phase 1 — establish competitiveness

**Question:** Under a valid quality reference and a fair end-to-end measurement boundary, how competitive is the current Renderer?

- [Issue #4 / N007](https://github.com/owoDra/real-time-gi-lab/issues/4) is **CLOSED as bounded NO GO**: moving-rigid CPU reference remained fully black through the frozen four-seed 512–8192-SPP ladder, while a probe-shadow counterfactual explained 9,247/9,247 positive pixels in the current GPU diagnostic frame. [Result 012](lanes/n007-reference-validity/results/012-n007-bounded-no-go-decision.md) preserves unmeasured regimes and frozen N006 outcomes. [Issue #5 / N008](https://github.com/owoDra/real-time-gi-lab/issues/5) concluded: independently validated oracle GO ([Phase A result 004](lanes/n008-hdr-oracle/results/004-phase-a-exit-decision.md)), cross-class reference set bounded NO GO ([final result 011](lanes/n008-hdr-oracle/results/011-n008-final-decision.md)). These studies remain closed research outcomes; a statistical screen does not replace physical validity.
- **N009 concluded (2026-10-14): SC NO GO / BF1–BF3 PASS / PT INCOMPLETE.** [Final result 009](lanes/n009-scene-contract/results/009-n009-final-decision.md). Under C1, C1/C2/C4/C5/C6 have full total support but only deterministic direct references; both T_B2/T_B8 totals fail the unchanged four-seed 8192-SPP cap. Amendment 1 leaves C3 light motion NOT_CONSTRUCTIBLE. BF gates pass on C7; C7 V1 and old B4 V3 failures prevent COMPLETE attribution. Excluding 21 V1 pixels is post-hoc sensitivity. Sponza direct max-relative-error-1.0 pixels remain unresolved (未解決).
- **Next reference gate:** separately preregister a budget/convergence method for full-support Sponza totals, and a new light-motion candidate set if that regime is studied. N009's thresholds and negative total result remain frozen. **Next diagnostic gates:** resolve the Sponza direct-zero pixels with explicitly post-hoc CPU analysis, then validate exact GPU probe-key replay and consistent secondary sidedness before promoting coverage/range/shadow observations to complete attribution. C1/BF-P adoption requires a separate architecture decision and executable checks.
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
