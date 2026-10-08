# N006 — RC-native interval-aware ray allocation

Issue: [#42](https://github.com/owoDra/phos-gi-lab/issues/42)  
Branch: `research-n006-interval-aware-allocation`  
Predecessor HEAD: `research-n005-adaptive-tracing@3a098584ec76bcaa06e5166793b2946cd1f7eb25`.

## Research question

Can low-cost **pre-trace** signals associated with the existing Radiance Cascades **owner × cascade / radiance-interval** work units predict the **actual final-image error reduction from an extra ray**, and place identical incremental ray budgets better than N005 uniform / frozen depth-discontinuity allocation **after all scheduling/merge/storage GPU costs**?

Do not assume per-interval metadata/state is required or even compatible with the existing work stream.

## Evidence and rationale

- N004 [weakness atlas](../lane-n-end-to-end-renderer/results/004-weakness-atlas.md) found camera and dynamic-geometry quality blockers, often dominated by low-radiance relative-error/affected-pixel classification, not traversal/storage correctness.
- N005 [formal comparison](../n005-adaptive-tracing/results/003-p3-formal-comparison.md) concluded **REFINE**: equal-ray adaptive selection beat uniform on quality and cost for stable deformation, but lost in topology churn and generally failed to reduce affected-pixel blockers.
- Adaptive ray allocation, probe classification, and temporal variance handling already have DDGI prior art. N006 is **not** intended to re-prove generic adaptive sampling. The open Phos question is actionable RC-specific marginal value and affordable implementation.

## Documents and stages

- [P0 literature and architecture](./001-literature-and-architecture.md): prior art, reuse and RC incompatibilities, actual work-unit mapping.
- [Prospective P0/P1 experiment plan](./experiments/001-p0-p1-predictive-value.md): pre-trace feasibility, bounded causal/ranking study, split discipline, stop rules.
- **P0:** no runtime changes, establish smallest safe allocation unit and predicted signal cost.
- **P1:** no scheduler, observe signals and run bounded counterfactual extra-ray interventions to measure realized marginal error reduction; decide GO/REFINE/STOP.
- **P2 (conditional):** at most two scheduler candidates; current vs uniform vs frozen N005 vs N006 under equal actual ray budget.
- **P3 (conditional):** fresh-process formal GPU comparison with frozen independent holdout and retained raw evidence.

## Deliberate scope correction

This lane starts with **extra-ray allocation**, not a general `update skipping` system. N005 appends work after the frozen base producer but still runs the existing per-frame sparse storage / invalidation / resolve path. Skipping base or retained intervals without proving their validity would introduce temporal cache semantics; that is **deferred**. Keep working single-frame RC, merge/gather semantics, and the accepted producer/traversal/storage architecture.

No ReSTIR-like per-pixel reservoir, accumulation-dependent transport, denoising, multibounce/glossy extension, global reorder or unrelated optimization.

## Evidence discipline

- Start from N005 closeout commit, **not main**, which does not contain this lane.
- N004/N005 evidence, results and configs remain immutable. N005 P3 data serves as historical context, **never as N006 training and independent formal proof simultaneously**.
- AMD Radeon 8060S Graphics (RADV STRIX_HALO); GPU timestamps primary, CPU wall diagnostic; clean evidence worktree and exact provenance.
- Verify base-prefix correctness, owner/cascade/ray/output identity, sample normalization/merge, actual equal-ray counts, no traversal or storage failure, control correctness and single-frame fallback.
- Keep failures/negative gains and all raw samples. No sample deletions, post-hoc thresholds or GPU power-profile changes.
- Design decisions/contracts/results in Git; implementation truth in code/tests; avoid double documentation. **No GitHub Actions.**

## Bootstrap design review

Potential blockers: interval may not be independently schedulable, local error is not marginal gain, output influence may overlap, signal must exist **before** its ray, and selection overhead can outweigh savings. Each is a P0/P1 gate, not an assumption.

**Decision: proceed with P0; P1 instrumentation requires a prospective versioned contract; P2/P3 not authorized yet.**
