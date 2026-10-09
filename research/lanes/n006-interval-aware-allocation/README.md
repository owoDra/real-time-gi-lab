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


## P1d completed — correct hash, unstable whole-GI delta

The user completed three rotated current/hash pairs on AMD Radeon 8060S at `2b862de49b8627e7d8bdbd4d91c312400c161019`: all P1c unique/duplicate counts reproduced, all images byte-identical, zero insertion failures. The **complete hash stage including clear** measured **24.5 µs median**, with **2 MiB scratch**. However, paired complete GI delays were +21, +422 and +636 µs (median +422 µs), much greater than and variable relative to the hash stage. See [P1d accepted evidence and uncertainty](./results/007-p1d-hash-cost-preflight.md).

**Decision:** GPU key extraction correctness PASSES; whole-GI cost interpretation is **REFINE**, not a demonstrated dedup speedup or a P1 scheduler GO. Before running another GPU campaign, inspect all six **already saved** per-stage evidence files with `mise exec -- python scripts/research/n006_interval_aware_allocation/audit_p1d_stages.py`; it writes a standalone JSON under `out/research/n006-interval-aware-allocation/p1d-stage-audit/`. This read-only audit cannot eliminate all timing uncertainty, but avoids spending GPU time before identifying whether any recorded stage systematically dominates the unexplained delay.


## P1d raw GPU-stage review: overlapping hash timestamp corrected

The user completed the six-file [P1d offline stage audit](./results/008-p1d-stage-audit-correction.md). A source-level **measurement-accounting bug** was found: historical `ray_prepare_gpu` included the hash stage, so the v1 offline audit subtracted the hash twice. The corrected **arithmetical unexplained full-GI deltas** are +12.424 / +375.834 / +615.489 µs across three pairs, with a 24.5 µs median hash stage. There is still substantial timing variability, not a verified 400+ µs hash cost.

The audit script is fixed prospectively to produce v2 with exclusive hash/ray-preparation accounting. The next [P1e](./experiments/005-p1e-timing-boundary-calibration.md) is a **single-process 12-frame A/B** on identical target geometry, exports all previously missing disjoint GPU stage timings, checks timing closure, and validates byte-exact images and correct unique-probe counts. This study remains non-formal; no change to N004/N005 or GitHub Actions.


## P1e accepted: hash timestamp closure yes; full-frame A/B confounded

P1e same-process study, clean `c76bf9780fe012782d180c0650b18b1dddeebf7c`: 12/12 byte-identical frames, nonoverlapping stage timing closure and exact P1c hash keys; GPU hash clear+insert **25.75 µs median**. The initial target frame incurred **1,772 µs dynamic GPU maintenance** after source-state warmups (so pair 0 is NOT state-matched). The other pairs have **primary visibility varying 357–914 µs**, and this stage executes **before** hash insertion in the command buffer. Thus the observed whole-GI paired median (+132.23 µs including cold pair) cannot isolate hash overhead. [P1e result and limitations](./results/009-p1e-disjoint-timing-and-primary-visibility-variance.md).

Rather than accumulating more unstable whole-GI numbers, the next [P1f GPU owner-output equivalence test](./experiments/006-p1f-owner-output-equivalence.md) reads actual merged integer sums, sample counts and spatial storage slots for ALL current owner/probe keys. It does not change or shorten rays; it is a correctness gate before designing a true GPU-native **canonical probe×cascade** stream. All raw P1a–P1e evidence unchanged; no GH Actions.


## P1f evidence and experimental P1g canonical tracing

The P1f user GPU report established `fully_equivalent=true` across **all 16,688 owner×cascade outputs**: zero divergent merged integer radiance sums/sample counts/rounded means and zero GPU storage slot reconstruction mismatches. It confirms a **single measured frame** supports one eight-ray sample per distinct probe×cascade. See [P1f accepted correctness evidence](./results/010-p1f-owner-output-equivalence.md).

The next [P1g compact canonical-probe pilot](./experiments/007-p1g-compact-canonical-probe.md) implements an **N006-only alternate current-mode GPU pipeline**, not a scheduler: GPU unique-probe hash, representative list, compact eight-ray work, indirect GPU copyback, and updated hardware dispatch count. Existing HWRT/radiance/merge/storage shaders then run over **24,232 actual ray work items** instead of 133,504 if the scene matches the P1c/P1f frozen setup. New two-frame runner requires byte-identical PFM, exact unique-key counts, zero storage/hit errors and bound-safe scratch memory before classifying any correctness success. Target frame 0 has a dynamic-geometry transition and **cannot** serve as a matched GPU timing comparison; no speedup claim is authorized from P1g. P1h, if P1g succeeds, must study warmed fixed-state performance and further dynamic classes.


## P1g first run: actual ray compaction, image mismatch — repair under test

The first target-GPU P1g run on clean `42bb421b048364575a6124059e3b4c0eca2592b7` **really dispatched 24,232 canonical ray work items** instead of 133,504 (81.85% fewer), with 3,029 unique probe/cascade outputs, 4,172 retained visible owners and zero hash/overflow/storage errors. However the final PFM digest **did not match** the original current-mode frame; `status=invalid-image-mismatch`. No end-to-end performance claim is valid from the cold/warm two-frame comparison. See [P1g failure record and numerical hypothesis](./results/011-p1g-compact-rays-image-parity-failure.md).

A prospective **N006-only** repair now tracks original owner multiplicities in the GPU hash and restores original integer `slot.sum = owner_count × canonical_rounded_mean` and `slot.count = owner_count` before the unchanged composite shader. This addresses a plausible float32 ULP discrepancy in `float(sum)/(float(count)*65535)` (mathematically equal quotients may differ in binary32 due to rounding). It is **not yet verified as the actual mismatch cause**. Exact image equality and all original owner-count parity checks remain hard requirements; on another mismatch, the runner now preserves RGB changed-pixel count/RMS/max delta for further diagnosis. No original current-mode or N004/N005 shader edits, no Actions.


## P1g repaired PASS; P1h paired steady-state measurement

The user reran P1g on clean `afeac5bb4fbe3771960cb96f2b8994e6e261830e`: **133,504→24,232 actual GPU ray work items** (81.85% fewer), 16,688→3,029 outputs, no key/capacity/owner-weight/storage errors, and **byte-identical baseline/canonical PFM** (SHA256 `79de995078c605c8c5c6aef44c8565edf3f808e32934fd43646753bdba815861`). The owner-multiplicity reconstruction fixed the previous numerical image mismatch. [P1g accepted result](./results/012-p1g-owner-weight-restored-bit-exact.md).

The P1g current target incurred 1,155.8 µs *one-off* dynamic traversal maintenance while the canonical target did not, so the apparent complete-GI time difference **cannot** be called acceleration. Canonical compact-build alone was 132.05 µs and owner-weight restore 10.54 µs; ~8.03 MiB additional scratch is separately reported and not in the renderer's old lifetime-peak telemetry.

Next [P1h frozen 3-process, 18-pair matched-state timing study](./experiments/008-p1h-matched-canonical-performance.md) executes 32 source warmups, **8 target-state current warmups**, then 12 alternating current/canonical frames (`011001100110`) per fresh process. All frames must have identical PFM, correct counts/owner weights and no dynamic maintenance. Report **both whole-GI and exclusive post-producer GI-work GPU deltas** (canonical-build included, owner-weight timing already nested in storage-update), preserving every sample. No formal speedup claim from mere ray-count reduction; no N004/N005 edits and no GitHub Actions.
