# Forward research roadmap — major gates only

**No new GI algorithm study is part of the October 2026 history consolidation.** The current evidence-backed Renderer is a baseline for further work, not an announced replacement for existing GI.

## Phase 1 — establish competitiveness

**Question:** Under a valid quality reference and a fair end-to-end measurement boundary, how competitive is the current Renderer?

- [Issue #4 / N007](https://github.com/owoDra/real-time-gi-lab/issues/4) is **CLOSED as bounded NO GO**: moving-rigid CPU reference remained fully black through the frozen four-seed 512–8192-SPP ladder, while a probe-shadow counterfactual explained 9,247/9,247 positive pixels in the current GPU diagnostic frame. [Result 012](lanes/n007-reference-validity/results/012-n007-bounded-no-go-decision.md) preserves unmeasured regimes and frozen N006 outcomes. **Next:** [Issue #5 / N008](https://github.com/owoDra/real-time-gi-lab/issues/5), a new independently validated physical HDR reference oracle study. Begin with CPU-only analytic lit/occluded/indirect controls; do not mistake a statistical PASS for physical validity or reopen N007. **N008 Phase A completed with Exit A = GO** ([result 004](lanes/n008-hdr-oracle/results/004-phase-a-exit-decision.md)); Phase B (frozen Renderer scene states and reference statistical eligibility) is next.
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
