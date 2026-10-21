# M001 — Lane M first cohort: prospective controlled screen

Date: 2026-10-21 JST. Baseline: `research` at `5835cb15b9ada984454dbe0a14947c67c29ae6c9`. Branch: `research-lane-m-gi-competitiveness`.
This is the **first Lane M registration**, not the historical topology Lane M and not a new N011.
The prior N010 results are **observed pilot/tuning data**, not held-out evidence.

## Entry and bounded question

N010 [751](../../n010-comparison-readiness/results/751-r1-full-readiness-outcome.md) and [753](../../n010-comparison-readiness/results/753-lane-m-handoff.md) authorize a **first-cohort handoff** only. Retained controls: frozen incumbent RC HWRT (software where captured), vanilla traversal, independently executed repository dense RC, independent pixel PT; the extra DDGI/RTXGI family is pending scene-GI and temporal integration.

Question: can *any* measured, explicitly supported role satisfy **all** HDR quality gates on unseen controlled geometry at its frozen budget, and only then offer a credible practical quality-matched timing/memory advantage? A failure is an answer. The current incumbent's pilot quality failure is retained; speed at unequal quality is not a win.

## Frozen existing-data split (no new data)

- **Tuning/diagnostic only:** every N010 C1–C12 state, 24 reference slots, 36 selected timing boundaries, 12 static/dynamic conditions and every prior observation, including failures. They have already been observed. They must **never** be relabelled held-out.
- Handoff metadata CPU audit: [001](../results/001-n010-input-metadata-audit.json), rechecks all24 unique slots, per-slot state hashes vs lock026, eligibility rule16 original +8 R1, and 36 unique selected boundary names. It does **not** re-execute the 5MB final auditor or validate 233GiB local raw corpus.
- **Held-out construction, pre-result fixed geometry recipes** for this bounded first **static non-Sponza** screen (generator N004 `n004_scene_factory.py`, unchanged `write_gltf`/camera/light conventions):
  - `M001-H01`: `leak_scene("medium", thickness=0.137)`
  - `M001-H02`: `leak_scene("grazing", thickness=0.163)`
  - `M001-H03`: `leak_scene("enclosed", thickness=0.127)`
  These numerical values, scene inclusion and order are **fixed before their indirect images**. Do not choose replacements on image outcomes. They are not represented as dynamic, Sponza, or generalized scene coverage. A separate prospective protocol will be needed for Sponza/complex/dynamic held-outs and expanded family claims.

**Fail-closed holdout gate:** the exact scene-file bytes, generator source identity, triangle count, material/lighting parameters, camera and frame UBO, signed scene/state SHA256, eligible reference provenance and frame schedule must be locked before using their indirect image scores. This document only fixes recipes; **none of those new files or attested states is yet captured or eligible**. If image-generating state capture is needed, selection remains numeric, and no captured indirect data may influence the recipe or exclusion. A state or reference mismatch → INELIGIBLE, not scoreable. Do not score an old N010 reference against a changed scene.

## Frozen first-cohort budgets and decision

- **Linear HDR quality**, all pixels without masks: total NRMSE ≤0.05, indirect NRMSE ≤0.10, absolute indirect signed energy bias ≤0.05; require valid independent reference for each exact frozen transport state. Keep leak, support and active-p99 diagnostics plus all zeros and 1.0 direct-relative-error pixels.
- `T_B2` and `T_B8` remain separate finite-bounce regimes. Pixel PT budget ladder is exactly `[1,4,16,64,256,1024]` spp, with first PASS chosen; if no level passes, mark FAIL. No adaptive rerun. Incumbent / vanilla traversal / dense RC retain their N010 existing fixed budgets and algorithms as diagnostic fixed-budget comparisons; these budgets are **not asserted to be equivalent** to PT1024. Do not fabricate unsupported configurable RC budget knobs.
- DDGI source pin: RTXGI `f33e496ca31b3f0eec1c4e2cbaa8bb620e337fa6`, Vulkan/AMD. Existing constant-field volume tests do not demonstrate actual scene GI. Before its own quality/timing comparison, register probe/rays/history/quality budget ladder, qualify finite-depth matching semantics (or mark unsupported), actual scene gather, dynamic updates, full owned allocations and teardown. Do not call this first controlled screen a full representative-family benchmark.
- First classify per scene/transport/role: `PASS`, `QUALITY_FAIL`, `REFERENCE_INELIGIBLE`, `UNSUPPORTED`, or `NOT_RUN`. Failing PT, RC or DDGI remains in the report. **No speed ranking at all unless both sides meet the same frozen quality threshold on the same exact state and depth.**

## Timing and resources (deferred until matched quality)

Preserve whole-Renderer Vulkan timestamps, every source/target and recovery frame, startup/recurring/update/AS/allocation work, full owned-allocation ledger and zero teardown, original 8GiB owned cap. CPU wall, readback and driver-private memory are separate diagnostic/excluded terms. Explicitly calibrate the **actual chosen binary/shader/budget/frame/output lifecycle** with registered neutral-work, order-balanced same-role controls and ranked process-median method (N010 plans100/103, result255/256, numerical core117). A previous static C7 PASS does not transfer automatically to PT1024 or changed lifecycle. Define and freeze the **complete statistical boundary family**, process count, ranked interval, multiplicity and 1.20 practical ratio criterion **before** first accepted acquisition; no post-hoc process addition. If calibration/time is inconclusive, retain quality/memory findings but no speed win.

## Stepwise exit and stop rules

1. CPU: check N010 handoff metadata (done [001]); implement and test standalone holdout generator/manifest and hash the emitted glTF + BIN. No GPU data or claims yet.
2. Freeze a new held-out state manifest with exact source/target/camera/material/light fingerprints **before** indirect-output inspection. Run a bounded physical/reference eligibility check for new geometry; stop with INELIGIBLE if it cannot qualify.
3. Only then acquire B2/B8 quality budgets using opt-in N010-derived GPU executables, one named process/scene at a time, refuse existing work roots. If no pair is quality-matched, stop timing on that pair, report explicit quality loss and proceed to DDGI qualification. Do not retune the incumbent on held-out data.
4. Only matched-quality pairs proceed to separately frozen selected-boundary calibration and full-frame timing/memory classification. No unconditional winner or single-GPU generalization.
5. Broader Lane M acceptance still requires prospective held-out dynamic/Sponza strata and actual DDGI comparator; M001 alone never proves architecture competitiveness.

Constraints: no N001–N010 evidence edits, no default Renderer changes, no GitHub Actions/CI, no clock/power/desktop setting changes, no automatic queue/retries, and no raw private-corpus upload. Tests/GPU execution **NOT RUN** for this preregistration. CPU work performed by assistant, GPU-only work handed to owner once the safe first named capture exists.
