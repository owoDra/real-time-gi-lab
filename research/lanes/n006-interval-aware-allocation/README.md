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
- **P0:** source-level owner × cascade feasibility established and baseline GPU smoke **PASS**; novel intervention correctness remains to verify. [P0 source and smoke result](./results/001-p0-work-unit-feasibility.md).
- **P1:** start with a calibration-only [P1a causal pilot](./experiments/002-p1a-causal-pilot.md) on new isolated intervention code; then prospectively freeze predictive-signal ranking, calibration/holdout and GO/REFINE/STOP. No scheduler.
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


## P1a first GPU attempt and correction (2026-10-08)

The baseline and independent reference completed but all 12 targeted interventions exited with a **harness CLI parsing error**, yielding **zero scientific intervention results**. See [P1a invalid attempt / controlled repair](./results/002-p1a-cli-parser-failure-and-repair.md). An explicit `resume_p1_pilot.py` runner preserves the original failed artifacts, verifies the original successful reference against a newly built current image, and only then repeats the 12 **unchanged** targeted interventions. No hypothesis, tile selection or decision criterion was changed after seeing the failed run.

## P1a completed calibration + offline observability gate

The user completed the corrected P1a on `4871623797b8ba0b155447f63697bd3340829ee3`, with 12/12 valid targeted interventions, reference reuse checked and zero baseline replay drift. Eleven global RGB RMS gains were zero; the last was +`4.134909315207209e-10`, far too small to justify a signal ranking or scheduler. See [P1a completed evidence interpretation](./results/003-p1a-causal-pilot-calibration.md).

Before spending more GPU time, run `mise exec -- python scripts/research/n006_interval_aware_allocation/audit_p1a_images.py` with the retained repaired-run PFM images (one unique repaired run is auto-located). The audit compares **actual changed pixels** rather than only global RMS and saves a separate JSON under `out/research/n006-interval-aware-allocation/p1a-image-audit/`. Keep all raw N004/N005/N006 campaigns intact. The P1 predictive gate remains unpassed.


## P1a exact-pixel audit and prospective P1b

The P1a [paired-image audit](./results/004-p1a-image-influence-audit.md) established **11/12 pixel-identical final images** despite 4 actual additional rays each; the only nonidentical case was tile 22890 / cascade 3 (468 improved *other* pixels, tiny global gain). Existing output cannot distinguish zero radiance, 16-bit per-output normalization, shared probe dilution or no pixel consumer.

The next step is a strictly bounded [P1b causal-chain diagnostic](./experiments/003-p1b-influence-probe.md), instrumenting the existing N006 experiment for **one unchanged and one changed cascade at the same tile**. This includes a short-warmup baseline bit-equivalence guard against the retained P1a frame, so users do not re-run expensive reference generation unless the guard fails. Results are diagnostic, not ranking/training evidence; P1 GO/P2 gates stay closed.

## P1b verified, P1c survey prospectively frozen

P1b completed with zero failures, bit-identical baseline and intervention replay. Both selected owner×cascade interventions changed the real GPU spatial storage sum by one 16-bit unit, despite only one affecting final pixels. The P1b readback also exposed **8** and **151** same-probe owner outputs for the two sampled keys. The accepted producer / ray-preparation / traversal / radiance code shows same-probe owners currently issue identical *base ray inputs*. This is potentially avoidable duplicate ray work, but GPU-grouping costs and correctness remain entirely unmeasured.

See [P1b outcome and frozen P1c exact-base-ray multiplicity survey](./results/005-p1b-causality-and-p1c-multiplicity-contract.md). Next N006 step is **one current frame with no new reference or extra ray**, counting whole-scene per-cascade unique keys and input-identical repeated ray counts via `run_p1c_multiplicity.py`. This is a **forensic count**, not a dedup implementation, speedup or P1 scheduler success claim.

## P1c accepted — exact base ray duplication

User-run P1c validated all four cascade keys/ray inputs on the target GPU and found **109,272 / 133,504 = 81.85% exact repeated base ray inputs**, with 3,029 unique `(probe_xyz,cascade)` keys and 24,232 unique 8-direction ray inputs. P1c had 4,172 visible owners; the most repeated key had 275 owner outputs. See [P1c accepted evidence and hard boundaries](./results/006-p1c-exact-ray-input-multiplicity.md).

**Critical distinction:** 81.85% duplicate *inputs* does not imply 81.85% complete-renderer savings; the observed single-run HWRT traversal stage was only about 145 µs of about 2,453 µs complete GI. Grouping, clearing, scanning and storage redesign have costs.

The next prospective, low-risk gate is [P1d GPU unique-key hash cost preflight](./experiments/004-p1d-gpu-unique-key-cost.md): three rotated fresh-process A/B pairs of N006 current vs a **diagnostic-only** hash insertion pass, zero extra rays, identical output images and counts checked against P1c. This **does not** remove any ray; it determines whether a native GPU grouping/unique-probe approach merits a separately designed actual canonical-probe renderer. N004/N005 remain untouched, no GitHub Actions.
