### 2026-10-11 P1m2a initial build PASSED; old unit assertion repaired

New M2a shader and N006 binary built successfully. The test run stopped **before GPU pilot** after 226/227 tests passed and one stale source test `test_placement_parity_and_buffer_lifetime` searched for direct `state_->p1m1_extra_stage->record(`. P1m2a now branches between M1a and M2a stages at the same pre-secondary GPU boundary; updated the static assertion to cover both arms with a whitespace-tolerant regex and retained ordering checks. Runtime/shaders untouched. Re-run `bash scripts/research/n006_interval_aware_allocation/run_n006_p1m2a_tetra_octant.sh` on latest HEAD; GPU result remains pending.

### 2026-10-11 M1c GPU hit-fate 4/4 accepted; new P1m2a direction pilot prepared (GPU pending)

Original unchanged M1a 3-key outcome: 12 extra P1a uniform-sphere rays returned **zero 16-bit radiance** and exact same output HDR. New P1m1c instrumented **the original hit buffer only**, reproduced 4/4 accepted parity, and proved **11/12 new-ray misses** and **1 real hit with radiance zero**, while **14/24 original eight-octant rays hit** on those exact 3 keys; high had 4 positive base radiance rays. These tiny convenience keys do **not** establish a population-wide effect, nor quality improvement. [Result 035](./results/035-p1m1c-gpu-ray-fate-4of4.md). New alternative P1m2a [prospective protocol 026](./experiments/026-p1m2a-fixed-tetra-octant-jitter-pilot.md) uses immutable same keys, 8+4 ray count, separate N006 shader, balanced fixed octants [0,3,5,6] and 0.125 jitter; readback reports misses, hits, positive ray radiance and unsigned changed-pixel effect. **GPU pending**; batch `bash scripts/research/n006_interval_aware_allocation/run_n006_p1m2a_tetra_octant.sh`. No reference-P1 predictor or P2 GO, no PR/Actions.

### 2026-10-11 M1a mechanism PASS 4/4 but null image effect 3/3; M1c ray-fate follow-up committed

Independent AMD Radeon 8060S GPU output `n006-p1m1a-canonical-key-pilot-summary(1).json`, raw SHA `ea8b9c928bd5f3470bcc85f33b1b6d98127a51da94961e5b27f1329e4d6d6f36`, clean `dd5d883`. **Control + three targeted +4-ray interventions all pass strict correctness/owner/hit checks**, 3008 canonical outputs and 24064→24068 rays. Extra contributions are **0 on all 3 keys**, and every output PFM is byte-identical to accepted static control. High-consumer key 875 has baseline 16-bit 8-ray sum 10, 4 extra sum 0, rounded 1→1; gain `RMS(control,common_ref)-RMS(candidate,common_ref)` is **exactly 0 for all three**, independently of which common reference is selected. [Result 034](./results/034-p1m1a-canonical-key-causal-null-4of4.md). The serial per-key scan costs 619–634 µs, not a viable scheduler or four-ray marginal GPU cost. Never claim P1 quality/ranking/P2 GO from mechanics alone.

**Next** [P1m1c prospective audit 025](./experiments/025-p1m1c-ray-hit-vs-zero-energy-audit.md): inspect GPU `GpuHit.metadata[3]` and quantized radiance after already-accepted shading to classify 4 extra rays per fixed key as miss, positive hit, or hit+zero-energy. Added N006-only CPU diagnostic and runner with strict same-PFM and frozen-key parity checks; no new GPU shaders or sampling direction changes. Not locally GPU-validated. Run `bash scripts/research/n006_interval_aware_allocation/run_n006_p1m1c_ray_fate.sh`; upload `n006-p1m1c-ray-fate-summary.json`. No accepted target modifications, PR or Actions.

### 2026-10-11 M1a first GPU preflight control PASS; Zero postframe gate repaired (GPU pending)

First GPU output `n006-p1m1a-canonical-key-pilot-summary.json` (SHA256 `7b9fd8cca73a4764f796ebe8f086595c7086caf5c9cda1a6fb6dc7c7929cc9dd`), `status=invalid-retained`, accepted control 3008 keys / 24064 rays / byte-exact accepted HDR image / N004 hit oracle. Zero completed target render and N004 validation but postframe diagnostic rejected `last_canonical_frame`, because original canonical **base-prefix** verifier incorrectly assumed total work must be `outputs*8` rather than `outputs*8+4` for M1a. Fixed predicate to require immutable eight-ray prefix, exact +4 appended tail, unchanged per-ray checks and owner-weight constraints. No new shader changes or readjusted M0 calibration keys; Low/High not executed. [Result 033](./results/033-p1m1a-first-gpu-zero-postframe-guard-failure.md). **P1m1a not yet accepted**; rerun same `run_n006_p1m1a_canonical_pilot.sh`. P1m1b signed HDR reference and P2 remain pending.

### P1m1a initial executable build and static test repair (2026-10-11)

The user's first attempt built the new M1a SPIR-V and N006 C++ executable successfully but unit tests stopped at **one stale text assertion out of 222 tests**. Original M0b test expected a single-arm `request.p1m0_pretrace_coverage ? 22U` string, whereas the intentionally shared 22-query pool now uses `(pretrace || m1_key_intervention) ? 22U`. Fixed the test to assert both branches, not production code. No M1a GPU frame ran on the failed attempt. See [result 032](./results/032-p1m1a-first-build-and-static-test-regression.md); rerun the unchanged `run_n006_p1m1a_canonical_pilot.sh` one-batch command to obtain causal measurements. All signed quality predictions and P2 remain NOT established.

### 2026-10-11 — P1m0b pre-secondary eligibility PASS; P1m1a canonical-key causality pilot now implemented

The user-supplied P1m0b GPU summary, SHA256 `d7774a3e4fee8c9a103a7529979d7303ad865d05878143e4522232b8ef14affd`, demonstrates same postframe lookup counter results available before secondary ray dispatch for **all five frozen SW scenes**, full-slot and eight-counter byte equality, all original key-row hashes, no invalid cases. GPU cost only 14.387–22.683 µs (0.82–1.37% of instrumented GI), 131104 byte scratch, all under pre-registered bound. [Result 031](./results/031-p1m0b-presecondary-gpu-cost-pass.md). **Feasibility stage PASSED**; does not prove signed marginal benefit, a valid predictor or P2 net performance.

Per frozen [P1m1a protocol 023](./experiments/023-p1m1a-single-canonical-key-extraray-preflight.md), the research branch now contains the N006-only shader/runtime/CLI and independent four-run Python launcher to add **four deterministic P1a directions to ONE canonical-key output**, preserving all 8 base ray indices and existing storage owner weights. Three original M0 calibration-only static/C3 keys (zero, low, high) are whitelisted; per-output GPU radiance sums of 8+4, extra contribution indices/metadata, unchanged input key SHA, original accepted control PFM hash, N004 correctness and signed/unsigned outcome separation fail closed. Image **change is not quality gain** until a later independent HDR reference comparison. New unit contracts guard direction seed identity, shader placement, frozen keys, and PFM diff semantics. **Not locally GPU verified yet**.

Next single process batch (four separately warmed static runs, no re-running M0b/B1/C0):

```bash
git switch research-n006-interval-aware-allocation
bash scripts/research/n006_interval_aware_allocation/run_n006_p1m1a_canonical_pilot.sh
```

Upload `out/research/n006-interval-aware-allocation/p1m1a-canonical-key-pilot/<UTC>/n006-p1m1a-canonical-key-pilot-summary.json`. If 4/4 PASS, advance to signed reference-quality P1m1b (still NO P2 GO). No PR, no GitHub Actions, no accepted shaders changed.

## 2026-10-11 P1m0b target GPU PASS (newest)

User uploaded `n006-p1m0-consumer-coverage-summary(2).json`, SHA256 `d7774a3e4fee8c9a103a7529979d7303ad865d05878143e4522232b8ef14affd`, clean HEAD `359e6b87fe38919349b994136005251187137b4b`. Five frozen software scenes COMPLETE, zero failures. In-frame before-secondary count and independent postframe GPU count matched **every slot of 32768 values and all 8 counters**, all old M0 per-key SHA fingerprints matched, accepted HDR PFM and N004 gate intact. GPU timestamp pretrace clear+dispatch+barriers **21.280/14.387/14.868/22.683/20.439 µs** for static/camera/light/moving/deforming, respectively, **0.82–1.37%** of instrumented GI, 131104-byte scratch. All five passed predeclared cost cap `min(10% of instrumented complete GI, 50% of traversal)`. C0 source provenance still MATCHED. [Result 031](./results/031-p1m0b-presecondary-gpu-cost-pass.md).

**P1m0b GO (feasibility only)**. This does NOT establish signed HDR gain or predictive ranking. Canonical-key +4-ray intervention P1m1 is next. Keep one-key contrast, frozen M0 calibration strata and independent reference; no P2 scheduler claim. Need user GPU evidence for next phase; do not rerun B1/C0/M0/M0b; no PR or GitHub Actions.


---

### 2026-10-11 — P1m0 consumer coverage 5/5 PASS; P1m0b pre-secondary feasibility next

User's uploaded summary at clean HEAD `8a5cb25`, SHA256 `f355b7202e52127b044120ac8406e5dba4626dd88f4cf29a78f16abbc2c66cec`, verified five accepted software scene results: [result 030](./results/030-p1m0-five-scene-coverage-pass.md). **5/5, zero failed cases**, exact accepted PFM SHA/primary hit parity checked in original M0 runner, owner/key/lookup closure. Only **38–100 canonical keys among 3008–3220** had successful screen composite lookup attempts per frame (1.22–3.32%); 84.4–93.8% of successful lookup *counts* were cascade 3. No actual signed quality or P1 predictive ranking claims. All **60** previously selected M1 calibration-only key strata are available (zero/low/high ×4 cascades×5 scenarios), but **NOT YET ray-intervened**.

Added prospective [experiment 022 P1m0b](./experiments/022-p1m0b-presecondary-coverage-cost.md): N006-only opt-in dispatch of exactly the M0 coverage shader **after primary hit and canonical hash but before secondary ray tracing**. Freeze exact bitwise comparison to postframe M0 scratch counters/stats, the five original key-row SHA fingerprints, accepted final HDR images, N004 sampled target hit oracle, new GPU timestamp clear+dispatch+barrier, 131104 bytes requested scratch, conservative prospectively fixed `C <= min(10% instrumented complete GI, 50% traversal)` per scene. Flag if cost exceeds without changing thresholds. Instrumented complete/prepare timings are NOT the prior uninstrumented baseline. **No corrected GPU evidence yet.** New one-batch:

```bash
git switch research-n006-interval-aware-allocation
bash scripts/research/n006_interval_aware_allocation/run_n006_p1m0b_pretrace.sh
```

Expected output `out/research/n006-interval-aware-allocation/p1m0b-pretrace-coverage-five-scenes/<UTC>/n006-p1m0-consumer-coverage-summary.json`. Only after five-stage parity and bounded GPU cost can P1m1 proceed to causal canonical-key +4-ray / signed reference-quality study. Issue #42 OPEN, no PR/Actions.

### 2026-10-11 M0 GPU preflight timeout — 0/5 INVALID; targeted instrumentation

Second user's unchanged local runner on HEAD `bd4aae0` obtained `status=invalid-retained`, **0/5**, because the `static` child exceeded the **600s bound** with no uploaded stderr/stdout (evidence path `.../p1m0-consumer-coverage-five-scenes/20261011T035058Z/`). Previous 210 Python unit tests and E003 source/runtime SPV MATCHED C0 static audit remain true, but **there is no GPU consumer count, marginal quality gain, coverage-strata evidence or scheduler authorization**. See [result 029](./results/029-p1m0-first-gpu-timeout-and-diagnostic-repair.md).

Independent source audit revealed a likely unbounded CPU-cost regression: P1m0 was *not* in the `p1l_sampled_hit` guard, so all **8 target warmups** executed expensive N004 CPU hit checks; prior successful B0 uses the fast warmup and one target hit oracle. P1m0 now adopts that B0 pattern while retaining the **measured target's** CPU N004 correctness oracle. Last stalled phase is **not directly observed** from the uploaded JSON. To discriminate CPU versus GPU stall if needed, both C++ main and consumer pipeline flush explicit fine-grained stage names; Python streams stderr/stdout to persistent files in real time and includes the exact last stages on failure/timeout. Source/unit contracts were added. The same unchanged one-batch user command now includes these fixes, but **user build and GPU 5/5 rerun still required**. Avoid merely raising the 600s timeout.

### 2026-10-11 second user batch — C0 static MATCHED, first M0 scenario warmup repaired

- **210 N006 tests OK**, CPU numerical audit confirmed synthetic float32 division-vs-reciprocal non-equivalence, B1c static shader instruction deltas captured (without GPU re-benchmark).
- **E003 C0 gate PASS (static provenance only)**: actively loaded `e003_instance_quantized.spv` SHA matches freshly rebuilt accepted source. The accepted binary has 36,072 bytes and 7 statically declared `OpFDiv` instructions; B0 instrumented has 38,404 bytes and also 7 OpFDiv. [Evidence record 028](./results/028-p1l-c0-static-spv-provenance-pass.md). Do not infer GPU division bottleneck, hoisting or speed.
- **M0 first GPU case INVALID / result unavailable**: subrenderer exit 1 on `static`; source audit found P1m0 still applied old P1h **4,172**-owner, single-deforming-scene warmup gate despite static's accepted **4,167** owners. Corrected both count and stabilization branches to scene-aware `p1l_stage_any || p1m0_coverage`, preserving old non-M0 branch. Static regression test added; rerun is **pending**, true exception in old stderr not yet inspected.
- Former runner hid the useful child message behind `stderr.log` basename. The actual old location is `out/research/n006-interval-aware-allocation/p1m0-consumer-coverage-five-scenes/<UTC>/static/stderr.log`. The new runner prints the full path and up to 6,000 characters of stderr/stdout and points at the retained summary. **No evidence of shader pass/fail or M1 predictor quality yet**.

Run the same one-batch command below after branch fast-forward. This is an independent follow-up, not repetition of rejected B1a/B1c GPU measurements.

# N006 — RC-native interval-aware ray allocation

Issue: [#42](https://github.com/owoDra/phos-gi-lab/issues/42)  
Branch: `research-n006-interval-aware-allocation`  
Predecessor HEAD: `research-n005-adaptive-tracing@3a098584ec76bcaa06e5166793b2946cd1f7eb25`.

### 2026-10-11 user build/test feedback and conditional M1 preparation

User's one-batch log: **C++ build/link passed**, then `206` N006 Python tests reported **3 P1m0 static test failures**: the whitespace comparator accidentally used `r"\\\\s+"` instead of a whitespace regex, and the test incorrectly expected three negated CLI gate occurrences whereas the actual contract has two negations and a positive allowlist. These are harness test bugs, **not measured GPU correctness or performance failures**. Pushed fix `070a720`; revalidated accepted N001 and actual SOFTWARE N003 composite expressions against the M0 shader after whitespace normalization. **Complete unit re-run and GPU M0 still pending**; do not mark them PASS.

To avoid another session boundary, M1 calibration selection now has [prospectively frozen 5×4×3 zero/min-positive/max-positive strata in experiment 021](./experiments/021-p1m1-canonical-probe-marginal-value-design.md), pure `p1m1_calibration_selection.py` + tests. The M0 runner automatically writes the chosen **calibration-only canonical token** per scenario/cascade/stratum into `n006-p1m0-consumer-coverage-summary.json`, plus a **60 expected** selection count and an explicit `incomplete_strata_no_intervention` status where key coverage lacks discrimination. Selection never reads reference error and never justifies P2. The previously documented single batch command remains unchanged.

## 2026-10-11 ongoing research — E003 C0 + original N006 P1m0

**Current focus is not another primary BVH near-first attempt.** B1a and B1c were GPU REJECTED, B1b only reduced work counts. Result [025](./results/025-p1l-b1c-packed-axis-performance-reject.md) retains the frozen GPU 15-process/180-pair evidence; do not rerun B1a/B1c.

**E003 P1l-C0:** [frozen experiment 019](./experiments/019-p1l-c0-e003-wide-child-cost-audit.md), [source/layout result 026](./results/026-p1l-c0a-e003-source-layout-audit.md), [CPU float32 result 027](./results/027-p1l-c0b-f32-slab-rounding-risk.md). Accepted quantized wide child = 176B node and 16B child; 25.53–26.30 child AABB tests/secondary ray is *operation count only*. In a synthetic IEEE float32 CPU model, division versus inverse multiplication changed 51,445/200,000 entry results and at least one constructed slab accept/reject decision, so do not assert arithmetic replacement is GPU byte identical. A separate C0 static audit rebuilds the unchanged E003 GLSL with a N006-specific filename and **retains a status=blocked JSON on missing/stale runtime `e003_instance_quantized.spv`**. It cannot establish physical GPU machine instruction costs; C1 is not written/authorized without a credible static hypothesis and prospective correctness gate. C0 and missing B1c SPIR-V static audit are grouped in one local script; this never repeats GPU B1c.

**P1m0 refocus on Issue #42's actual purpose:** [frozen coverage protocol 020](./experiments/020-p1m0-probe-consumer-coverage.md) adds **N006-only** GPU shader `n006_p1m0_consumer_coverage.comp.glsl`, runtime postframe invocation, 32,768-slot coverage array, primary-hit and rendered-image byte-parity checks and full per-canonical-key producer multiplicity/consumer pixel counts. The hash mirrors accepted probe-key indexing, and the screen pixel→probe reconstruction mirrors **both N001 and actual N003 SOFTWARE composite**. Five-scene fail-closed runner `run_p1m0_consumer_coverage.py` verifies accepted Sponza HDR PFM, GPU/software source, N004 CPU primary oracle, stage-accounting closure, key-count conservation and error-free hash accounting. No M0 GPU output has been supplied yet. M0 count is *potential lookup reachability*, **NOT confirmed storage-hit, actual signed global quality gain or a P1 predictive scheduler**.

Primary visibility precedes the producer in N006 `run_candidate_frame`; the canonical key index is built before ray preparation/secondary traversal. Thus a future *pre-secondary* consumer-count pass has a plausible same-frame data dependency path, but **M0 currently executes AFTER the accepted complete renderer** to preserve frozen baseline data. Additional GPU barriers, key-buffer 131,072 bytes, per-frame clear, dispatch and CPU readback costs are **not measured/accepted as production costs**. Only after five-scene M0 validity plus a separate costed pretrace gate can [conditional P1m1 design 021](./experiments/021-p1m1-canonical-probe-marginal-value-design.md) construct causal **probe-key** +4-ray labels with independent quality references; M0 alone does not authorize P2.

### Next single local batch (build/tests/static audits + five-scene M0 GPU diagnostic)

```bash
git switch research-n006-interval-aware-allocation
bash scripts/research/n006_interval_aware_allocation/run_n006_next_verified.sh
```

This script requires a clean worktree, fast-forwards, builds, runs the full N006 unittest discovery, captures **B1c static SPIR-V** (not its rejected performance candidate), captures **C0 E003 static SPIR-V**, and runs five **separately warmed** AMD Radeon GPU frames for M0 only. C0 `status=blocked` stops E003 C1 but deliberately does **not** suppress the independent M0 diagnostic; the overall script exits nonzero afterward and retains both artifacts. Upload `out/research/n006-interval-aware-allocation/p1m0-consumer-coverage-five-scenes/*/n006-p1m0-consumer-coverage-summary.json`, `out/research/n006-interval-aware-allocation/p1l-c0-e003-static-audit.json` and `out/research/n006-interval-aware-allocation/b1c-spv-audit.json`, or the first build/test failure with stderr. DO NOT rerun N004/N005/B1a/B1b/B1c historical GPU campaigns. **Build/tests/full GPU have not been executed in the GitHub connector environment.**

The lane's RC-native *marginal benefit of extra rays* hypothesis and HWRT-free speed parity are **unproven**, with explicit STOP/REFINE criteria in the frozen M1 plan. No PR or Actions.

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


## P1h accepted: repeatable net GI-work saving; next cross-backend parity gate

Target-GPU P1h on clean `ff2b80562640440befe3c664a831d5446ab0d75d`: 3 fresh processes, 8 target-state warmups each, 12 measured alternating current/canonical frames each, **36/36 byte-identical PFMs** and zero GPU/hash/weighting failures. Canonical mode actually dispatched **24,232** rays vs **133,504** current (81.85% reduction). Across 18 balanced A/B pairs, **post-producer GI-work inclusive of compact/owner-weight overhead was faster in 18/18**, median **−82.577 µs** (per-process medians −82.296 / −85.603 / −82.577). This is a reproducible net saving in the tested HWRT/deforming workload. [P1h full result with caveats](./results/013-p1h-matched-canonical-net-gi-work.md).

Whole GI was faster in **14/18** (median −145.857 µs), but primary visibility ran before canonicalization and varied **−829 to +501 µs** across pairs, so there is **no demonstrated universal whole-engine speedup percentage**. Original quality/evidence and accepted N004/N005 remain intact.

Next [P1i cross-backend parity matrix](./experiments/009-p1i-cross-backend-correctness.md) covers the **five supported Lane-E-final scenarios on both HWRT and software traversal** (10 frozen cases). Each case runs original current and actual canonical ray tracing in one process, requires exact PFM SHA, GPU key/owner multiplicity/hit/storage correctness and retains any failures. This is a correctness/portability test, **not a timing or topology-changing claim**. Only after it passes should P1j optimize direct GPU unique-probe production and extra scratch, then measure software fallback and complete-GI timing under matched steady states.


## P1i partial: 5/5 HWRT PASS, software static blocked

Uploaded first P1i cross-backend run at clean `07f1bae87efc351a953880a415ddc25bdc819bb1`: all five HWRT cases (static/camera/light/moving-rigid/deforming) ran true canonical GPU work with **80.97–81.95% fewer rays**, zero GPU errors, and baseline/canonical **bit-identical PFM** per case. At the first software variant (`lane-e-final-software` + `static`, case 5), the renderer exited with code 1; the summary includes only a path to `stderr.log`, **not the exception text**. Software cases 6–9 were not run (frozen fail-fast). **P1i is INCOMPLETE, software parity and software speedup are not established.**

See [P1i partial result](./results/014-p1i-cross-backend-partial-hwrt-pass-software-blocked.md). The immediate next step is **retrieve the already saved case-05 stderr**, not rerun GPU or guess a software bug from an exit code. Keep accepted N004/N005 and N006 P1a–P1h untouched; no GitHub Actions.


## P1i second campaign PASS: 10/10 HWRT + Software image parity

The rerun at clean `85d0b295e5fed0575e984f8e7e9b3993ba347a6e` completed the [frozen P1i matrix](./experiments/009-p1i-cross-backend-correctness.md) successfully: **5 HWRT + 5 Lane-E-final software** variants, each matching the original current-mode PFM byte for byte, with 80.97–81.95% fewer **actually dispatched** secondary rays, correct owner weighting and zero renderer/hash/storage failures. The earlier failed software bring-up remains a historical result; this later rerun passed after the N006-only software primary/shadow fix. [Complete P1i result](./results/015-p1i-cross-backend-complete.md).

**Limits:** All ten are sequential cold-state correctness comparisons on the same HWRT-capable AMD GPU. Neither hardware lacking ray-query support nor topology-changing/high-churn workloads were tested, and the software backend's *matched performance gain is not measured*. The previously observed 18/18 downstream GI-work improvement remains specific to the matched HWRT/deforming P1h benchmark.

Next [P1j-A bounded lean-hash prototype](./experiments/010-p1j-lean-hash-memory.md) keeps the accepted P1i default implementation unchanged while offering a separate CLI flag to reduce the canonical GPU hash/multiplicity table from 524,288 to 32,768 slots. This targets **8,421,464 B -> 4,489,304 B N006 scratch (~46.7% less)**, with a *new 10-case* bit-exact test and explicit collision/error reports. It does **not** yet remove the 4 MiB compact staging work stream or prove any increase in speed; zero-copy direct work will require its own P1j-B correctness/time gate. No GitHub Actions.


## P1j-A accepted: lean hash scratch reduction on both backends

The user completed the prospective P1j-A matrix at clean `946921f74ebe53dad31193de270a5d2b19d1811f`: **10/10 exact HDR PFM cases**, five Lane-E-final scenes for HWRT and software, no hash insertion/storage/owner-weight errors, ray reductions **80.97–81.95%** maintained. Canonical hash tables were reduced from **524,288 to 32,768 slots**; reported extra N006 scratch dropped **8,421,464→4,489,304 B (−3,932,160 B, −46.692%)**. Hash collision exploration remained bounded; aggregate extra collision steps were 503–671 per target run, not per insertion. [Full P1j-A accepted result](./results/016-p1j-a-lean-hash-cross-backend-pass.md).

Next [P1j-B direct compact-work pilot](./experiments/011-p1j-b-direct-compact-work.md) is a **separate opt-in** that retains P1j-A's 32,768-slot hash and compact scratch, but omits the GPU `compact→original` work-copy dispatch. N006-only alternate descriptors instead read the compact stream in ray preparation, radiance, storage reserve/accumulate, owner weight restoration and storage resolve. Current and accepted earlier copyback paths remain unchanged. A new strict 10-case HWRT/software matrix checks actual ray counts and bit-exact PFM before any timing conclusion. **Scratch remains 4,489,304 B**; removing the copy GPU dispatch is NOT a 4 MiB memory saving, since the original producer still needs a full work stream. Later source-level canonical probe generation is necessary to free that remaining scratch. No GH Actions, no N004/N005 behavioral changes.


## P1j-B accepted: direct compact work validated across HWRT and software

The user completed P1j-B on clean `781ecadc41eaffac87896aa919469c0bd46e6be0`: **10/10** frozen Lane-E-final HWRT/software scenarios produced byte-identical current/canonical HDR PFMs, and all ten candidate reports say `copyback_executed=false`/`direct_compact_work=true`. Actual ray reduction remained **80.97–81.95%**, restored owner multiplicities/hash/storage/hit checks passed, and added N006 scratch remained **4,489,304 B (~4.28 MiB)**. The compact scratch remains allocated because the owner-local producer still emits original full work before canonical compaction; removing copyback saves GPU work, not this allocation. [P1j-B accepted correctness result](./results/017-p1j-b-direct-compact-cross-backend-pass.md).

P1j-B canonical-build GPU stage observations were ~44–51 µs in nine of the ten independent cold runs, with a **149.644 µs software/light-motion outlier**. Neither the observed ~44–51 µs build nor cold original/candidate full-GI times are a statistically grounded speedup over P1j-A.

The next [frozen P1k matched GPU timing protocol](./experiments/012-p1k-three-arm-hwrt-software-timing.md) compares **original current**, **P1j-A lean copyback** and **P1j-B lean direct** in the *same process* using six balanced permutations, three fresh processes on each backend, after 32 source and eight target-state warmups: **108 measured bit-exact frames and 36 complete triplets**. It measures real copyback removal cost and net GI work/whole-GI gains separately for HWRT and software; primary visibility fluctuations remain explicit rather than being credited to canonicalization. No earlier accepted result was rewritten, no GH Actions or N004/N005 edits.


## P1k accepted: net GPU ray-dedup wins for both HWRT and software; zero-copy conditional

The user ran the **frozen three-arm matched GPU performance experiment** at clean `0c4d1ef7820435e9400f99749417774d37b22682`: 3 fresh processes × 2 backends; 32 source/8 target-state warmups and 18 balanced original/lean-copyback/lean-direct frames per process. **108/108 PFM frames byte-identical**, 36 complete balanced triplets, zero renderer/hash/storage/owner/timing closure failures, actual rays reduced **133,504→24,232** in both lean candidates. [P1k full evidence and decision](./results/018-p1k-three-arm-hwrt-software-gpu-timing.md).

In affected **post-producer GPU work, inclusive of the GPU hash, compact work and owner reconstruction overhead**, lean-direct minus current was **−94.399 µs HWRT (17/18 triplets improved)** and **−456.307 µs Software (18/18)**. Lean-copyback minus current was **−95.281 µs HWRT (18/18)** and **−442.821 µs Software (18/18)**. This replicates N006 canonical spatial work reuse as an actual work-stage speedup for both, especially software fallback. Still fixed deforming workload on AMD RADV; no other scene's measured speedup is implied.

**Direct versus copyback:** removing copyback improved isolated canonical build median **−6.432 µs HWRT** and **−7.073 µs Software**, but total affected GPU work changed by **+0.461 µs HWRT (only 9/18 faster)** versus **−10.961 µs Software (11/18 faster, all 3 process medians slightly negative)**. By the frozen P1k gate, HWRT direct **did not demonstrate additional net value**; retain simpler lean-copyback as HWRT reference and keep P1j-B direct as a software-leaning experimental option pending more evidence, not a universal default.

Full-GI timings have unusually variable *pre-canonical* primary visibility; direct vs original was faster in only **11/18 HWRT** and **15/18 Software**. No universal whole-renderer speedup percentage is supported. Descriptive individual-arm medians highlight that Software still has slower traversal and primary visibility than HWRT (canonical direct post-producer ~419 vs ~203 µs, traversal ~313 vs ~105 µs, visibility ~864 vs ~611 µs). These cross-backend absolute summaries are from separate processes; treat as profiling signals, not paired causation or proof on hardware lacking ray-query support.

**Next research choice:** prioritize a prospectively frozen **software traversal and primary visibility bottleneck isolation** study over further copyback micro-optimization, and separately evaluate source-level canonical producer feasibility to release retained compact scratch. High topology churn, genuine no-HWRT hardware, multiple GPUs, actual driver residency and predictive marginal-value P1/P2 remain untested. Preserve all old artifacts. No GitHub Actions, no accepted N004/N005 behavior changes.


## P1l-A1 implemented: nonintrusive HWRT/software GPU critical-path attribution

[Prospectively frozen P1l plan](./experiments/013-p1l-software-critical-path-isolation.md) has an executable **P1l-A1 stage-only diagnostic** (no new shader or N004/N005 changes). With `--p1l-stage-probe --canonical-lean-hash`, N006 runs 32 source warmups, 8 target-state current warmups, and **12 measured canonical P1j-A lean-copyback frames**. It records all target warmup maintenance GPU time samples and retains existing disjoint GPU stage timestamps; earlier P1h/P1k paths are unchanged. No direct-copyback mixture inside a case.

The runner `scripts/research/n006_interval_aware_allocation/run_p1l_a1_stage_isolation.py` uses 5 fixed Lane-E-final scenarios × HWRT/Software × three fresh processes = **30 processes, 360 measured PFM images**. Every image must reproduce its *backend-specific accepted* P1j-B HDR SHA (especially moving-rigid, whose accepted HWRT and Software images differ); each frame must meet original owner-weight, actual ray/canonical probe/cardinality, lean-hash scratch, no-storage/hit-failure and GPU stage timestamp-closure invariants. Reports per-process and 36-frame per-scene median/p10/p90 for primary visibility, secondary traversal, final composite/shadows, producer, canonical build, work stages and full-GI. Cross-backend ratios are clearly **unpaired, descriptive** since backends are run in independent processes; stage measurements do not yet identify BVH node visits or prove causal root cause.

**Status: code prepared, target GPU test NOT YET RUN.** No speedup, shader optimization, production adoption, HWRT-incapable GPU support or high-churn validation claimed. On complete 30-process GPU evidence, select at most two stage-targeted P1l-B hypotheses based on measured bottleneck, avoiding premature software traversal rewriting. No GitHub Actions.


## P1l-A1 CPU validation bottleneck and faster A1b replacement (2026-10-10)

Original P1l-A1 full CPU oracle run was **abnormally slow**: user saw **4/30 accepted runs after ~8h**, with one `phos-n006-intervention` process at **99.6% CPU for 36 min**. Code audit located a major, likely dominating cause: `n004_hit_diagnostics()` does **a brute-force CPU `trace_reference(scene.triangles, ray)` for every GPU ray** and reconstructs the validator GPU BVH each call. A1 had newly called this diagnostic across **32 source frames + 8 target warmups + 12 measured frames** per process, including ~133k-ray current-mode warmups. This is an instrumentation bottleneck hypothesis backed by code plus process observations, **not** a CPU profiler percentage. No evidence of GI shader regression or GPU deadlock. Retain original A1 raw results as partial, not completed; do not run another ~50h of repeated per-frame full CPU oracle.

[New frozen P1l-A1b sampled-hit protocol](./experiments/014-p1l-a1b-sampled-hit-fast-stage-protocol.md) provides `--p1l-stage-fast` **instead of** `--p1l-stage-probe`. Same **30 fresh processes × 12 measured frames = 360 frames**, 32 source+8 target-state warmups and P1j-A lean-copyback canonical work; original backend-specific image SHA, full per-frame GPU renderer/storage/hash/ray/owner/timestamp closure remain required. Heavy full N004 CPU oracle is run **once per process** on its first measured canonical frame, and **all unsampled diagnostic fields are serialized as JSON null, not fabricated 0 mismatches**. Existing N004 accepted code and old P1l-A1 protocol remain intact, so this is a *separately declared, narrower hit-reference guarantee*, not a retroactive protocol change.

The `scripts/research/n006_interval_aware_allocation/run_p1l_a1b_sampled_hit.py` runner prints each process start/completion and has a **600-second per-process wall timeout**, marks invalid and retains completed cases on failure. No auto-resume: an interrupted/timeout process means a separate new campaign later. **C++/GPU build and execution for A1b not yet confirmed.** Run only after stopping the old foreground process, fetching the new branch, building and passing N006 unit tests. Old full-CPU validation result is not a substitute for this A1b result. No GitHub Actions.


## P1l-A1b complete: stage bottlenecks reproduced in all five HWRT/Software scenes

The user completed [P1l-A1b sampled-hit 30-process, 360-frame stage isolation](./results/019-p1l-a1b-hwrt-software-stage-isolation.md) at clean `faa187d79f32c6f2a5eb7a55f7824897affd9bb7`. **30/30 runs, 360/360 expected backend-specific PFM SHA, zero reported errors; all measured GPU stage timestamps close**. The heavy N004 CPU/GPU ray hit oracle ran **once per process**, not for all 360 frames; unsampled frames still passed image/ray/hash/owner/GPU gates. The previous 4/30 CPU-bound A1 protocol remains an incomplete separate historical attempt. No reference image regenerated or HWRT-incapable device tested.

**Five independent scenario stage observations (unpaired cross-backend medians):** Software primary visibility median **1.50–1.55× HWRT**, with +272–314 µs gap per scenario; Software secondary ray traversal **2.98–4.08× HWRT**, +200–244 µs gap per scenario. Canonical GPU build and owner producer were near backend-neutral. Final composite/shadow Software-vs-HWRT was highly scene-dependent: **11.45× light-motion (299.93 vs 26.19 µs), ~4.4–4.6× static/deforming, 1.2–1.6× moving/camera**. Composite does other work besides shadow rays, so this is not yet a causal BVH traversal finding. Software N003 binary BVH is used for **primary and composite**, while **secondary** Lane-E software tracing uses an independent **E003 quantized eight-child BVH and spatial-cell hash**. Do not treat software secondary as the generic I001 binary traversal.

**Next [frozen P1l-B0 bounded diagnostic](./experiments/015-p1l-b-n003-e003-work-count-triage.md)**: collect per-pixel software primary/shadow path node/triangle visits and per-ray E003 grid/hash/wide-node/triangle visits via N006-only count instrumentation without contaminating uninstrumented GPU stage timings. Start with **light-motion and camera-motion**, stop each process at 10 minutes rather than repeating the old CPU oracle slowdown. Only after hit-count evidence choose at most two software shader optimizations and run separate bit-exact matched GPU performance gates. **B0 instrumentation not yet implemented**; no GPU runs, implementation success, or net performance result claimed. Moving-rigid backend image hashes differ in accepted evidence; maintain within-backend bit equality and investigate cross-backend discrepancy separately. No GH Actions/N004/N005 edits.


## P1l-B0 first implementation: GPU software traversal work counters

The [frozen P1l-B0 triage plan](./experiments/015-p1l-b-n003-e003-work-count-triage.md) now has a **new N006-only opt-in** `--p1l-b0-counts` and three cloned, isolated diagnostic shaders (original N003 and E003 SPIR-V and N004/N005 paths untouched):

- N003 primary **binary BVH:** per-pixel node-pop, triangle-test, hit and stack-overflow distribution.
- N003 composite/shadow **binary BVH:** per-pixel shadow-ray, node-pop, triangle-test, any-hit blocker, valid primary pixel, positive-hemisphere, stack-overflow and probe lookup distribution.
- E003 secondary **quantized 8-child / spatial hash:** per-canonical-ray instance, DDA-cell, hash-probe, quantized-node, child-AABB, triangle, leaf and traversal-overflow distribution.

The accepted renderer's **uninstrumented** P1j-A lean-copyback frame runs first with normal disjoint GPU timestamps and one N004 CPU hit diagnostic. Then three count-only shaders run in a **separate, untimed Vulkan dispatch**, with dedicated scratch *count and output* buffers. Their independent primary hits, composite image and E003 secondary hits are each compared **byte-for-byte to the original uninstrumented GPU buffers**, fail-closed; none of the accepted image or hit buffers are written by the instruments. Per-invocation raw uvec4 counters are aggregated on CPU to sum, mean, p50, p90, p99, max and nonzero; the diagnostic overhead is *never* reported as GI shader timing or as a speedup.

New runner `scripts/research/n006_interval_aware_allocation/run_p1l_b0_work_counts.py` first supports **`--smoke`** on light-motion and camera-motion (one software process each), then the full five supported software scenes without the flag. Each process has 32 source+8 target warmups and **one canonical target frame**, with a strict 10-minute wall timeout, retained stdout/stderr/PFM/result and accepted backend-specific PFM SHA, N006 canonical counter/stats/timestamps, sampled N004 CPU oracle and histogram safety gates. Logs/checkpoints remain immutable; the smoke campaign is *separate* from the five-scene acceptance run.

**Status: code pushed; C++/shader build, unit tests and target GPU smoke NOT YET executed.** Execute smoke before the five-scene campaign. No new optimization accepted based on mere source changes. Next choose at most two software backend hypotheses only after actual work counts and output byte parity pass on AMD RADV. No GH Actions or changes to N004/N005 behavior.


## P1l-B0 two-case smoke: GPU diagnostic byte-exact, shadow workload split identified

The user completed **P1l-B0 2/2 independent software smoke cases** at clean `257b0920858e86fd1d4e924d9b9580b0eb787aa8`: `light-motion` and `camera-motion`. Both reproduce accepted HDR PFM SHA, independently byte-identical diagnostic primary hits/final composite/secondary hits, original GPU timestamps and N004 sampled oracle correctness, **zero diagnostic overflow**, and 24,064/25,760 actual canonical rays. [Full smoke result, counts and cautions](./results/020-p1l-b0-two-case-software-count-smoke.md).

- **Light-motion:** 9,797 positive-cosine pixels enter the software shadow ray path, causing **42,065 shadow BVH node visits**, 4,538 triangle tests and 251 blocking returns. Camera-motion: **0 shadow queries, 0 shadow BVH work**, despite ~12.6k valid primary pixels in both scenes. Uninstrumented final-composite GPU single-frame timings 332.43 vs 14.51µs, consistent with earlier repeated stage isolation; this *workload difference* is a strong explanation candidate, **not** a causal claim that every µs comes from BVH traversal.
- **N003 software primary:** ~27.3 node pops/pixel in both scenes, but primary p50=1, p90=107–111, p99=247–255 and max=391–431; large per-pixel divergence/tail. Raw BVH traversal cost vs divergent scheduling is not isolated by counts alone.
- **E003 software secondary:** ~2.63 grid DDA steps/ray, 3.44 hash probes/ray, 6.96–7.00 wide node pops/ray, ~26.2 wide child AABB tests/ray, ~7.65–7.78 triangle tests/ray. Diagnostic workload count similarity does not prove GPU stage cost is the same; avoid attributing the entire ~300µs traversal to hash probing.

**Next step:** run the *separate frozen full five-scene campaign* using `mise exec -- python scripts/research/n006_interval_aware_allocation/run_p1l_b0_work_counts.py` (without `--smoke`). Each scene has a strict 10-minute timeout. Do not alter the runner or retroactively combine two smoke cases with new three scenes. Only after 5/5 pass decide on no more than two optimizations and freeze matched GPU performance gates. No shader speedup, HWRT parity, no-HWRT support or universal renderer improvement is claimed.


## P1l-B0 full five-scene PASS — primary BVH visit tail is the next intervention

After 2/2 smoke, the user completed the **independent frozen full 5/5 software B0 run** on clean `eebd9b2771e0dfbdba5b102083b52604b5a1e387`: `mode=five-scenes`, `status=complete`, `failures=[]`. All accepted HDR PFM SHA, canonical actual ray/owner/hash/storage/timing gates and independent N003 primary/composite + E003 secondary diagnostic GPU output byte parity passed; 0 overflow, **only one sampled N004 CPU oracle per process**. [Full five-scene counts and limitations](./results/021-p1l-b0-five-scene-software-work-counts.md).

- **Primary N003 binary BVH:** 1.57–1.62M node visits/frame for static/camera/light/deforming but **2.483M moving-rigid** (+57.2% vs static) with p99 screen-pixel visits **301** (vs ~247–261 otherwise). Robust rationale to investigate closest-hit child order and divergent ray tails; not evidence that +57% visits causes equal GPU time change.
- **Shadows:** light-motion launched **9,797 rays / 42,065 nodes** (~4.29 nodes/launched ray) while static/deforming launched only **251 rays / ~16k nodes** (~63–65 nodes/launched ray), with **224/251 blockers** (89.2%). Camera/moving rigid launched zero shadow rays. Per-screen-pixel zero-dominated percentiles must not be treated as per-shadow-ray distribution. One uninstrumented final-composite GPU sample/case is not a paired causal timing estimate.
- **Secondary E003 quantized eight-child BVH:** all scenes have **25.5–26.3 child AABB tests/ray**, 6.7–7 quant node pops, 2.59–2.63 DDA cells and 3.41–3.44 hash probes. Little evidence of extreme hash probing on the current 2-instance scene; counters alone do not show GPU cycles per AABB test.

**Next [prospectively frozen P1l-B1a protocol](./experiments/016-p1l-b1-primary-near-first-traversal.md):** first compare an isolated N006 software-primary **approximate near-first child scheduling** candidate to unchanged N003 software-primary, using child bounds center projection and unchanged intersection/hit tie-breaking. Five-scene full HDR/primary GPU-hit byte-parity preflight MUST pass. Only after this, same-process matched **3 fresh processes ×5 scenes ×24 frames = 360 measured frames /180 pairs**, alternating `011001100110011001100110` order with every GPU stage counted. CPU full-hit oracle only sampled, not in every warmup. Freeze pass gates before looking at candidate results. **The B1a candidate is NOT implemented or GPU-tested yet**, and B0 itself is a **diagnostic only**, not a speedup or production change. If B1a fails, move to a separate shadow any-hit or E003 traversal intervention. No GH Actions/N004/N005 edits.


## P1l-B1a coded: isolated near-first primary preflight and same-process GPU A/B

The five-scene B0 work-counts result has now motivated an **N006-only, opt-in closest-hit N003 software-primary near-first child ordering** experiment, prospectively frozen in [P1l-B1 specification](./experiments/016-p1l-b1-primary-near-first-traversal.md). The candidate shader `shaders/research/n006_interval_aware_allocation/n006_p1l_b1_primary_near_first.comp.glsl` is a clone of accepted N003 primary with one change: when processing internal binary-BVH children, push the **farther ray-projected child center first**, so LIFO visits the approximate nearer child first; ties retain N003's original right-first order. This is heuristic center projection, **not exact ray-AABB entry sorting**, and may increase traffic/regress GPU time. N003 original shader, E003 original, N004/N005 and GitHub Actions are unchanged.

With N006 `--p1l-b1-pattern`, build *both* primary SPIR-V stages once, select their dispatch **per measured frame**, and keep the same canonical P1j-A lean-copyback hash/ray/owner/storage stages across arms. An N006-only exact GPU `primary_hits` readback is compared **byte-for-byte with the first original-baseline frame** on *every* target frame, in addition to external frozen scene-specific HDR PFM SHA and sampled N004 CPU-versus-GPU oracle **on the first candidate frame, index 1 only**. A mismatched primary hit aborts the case; no visual-tolerance relaxation. GPU timestamp intervals end before the byte snapshot, so the readback is audit overhead, not counted as candidate shader speed.

[Executable B1a runner](../../../../scripts/research/n006_interval_aware_allocation/run_p1l_b1_near_first.py): first run `--preflight` for **5 fresh software processes × 2 target frames, pattern `01`**, after 32 source and 8 target warmups per process. *Only if all five correctness cases pass* run without the flag for **5 scenes × 3 fresh processes × 24 target frames (balanced `011001100110011001100110`)**: **360 byte-identical images, 180 baseline/candidate adjacent pairs (36 per scene)**. Audit primary GPU, complete GI, complete renderer, producer, secondary traversal and composite timestamps on same-process matched state. The prospectively frozen gate demands >=5% median primary-stage reduction and >=24/36 faster pairs and >=2/3 winning process medians in >=3 scenes, with no scenario >3% median renderer regression. Every process has a hard 600s timeout, checkpointed summary and raw stderr/PFM/evidence. New synthetic tests cover five-scene pattern, hit sampling integrity, exact primary byte gate, image SHA, frozen schedule and 15-process/180-pair acceptance/rejection.

**Status: source, separate SPIR-V target, N006 opt-in runtime/CLI, runner and Python regression tests PUSHED. C++/GLSL build, unit tests, PFM preflight and GPU timings NOT YET EXECUTED** on target NixOS. Do not claim improvement before strict five-scene GPU preflight. User command order:

```sh
git pull --ff-only
mise run build
mise exec -- python -m unittest discover -s scripts/research/n006_interval_aware_allocation -p 'test_*.py'
mise exec -- python scripts/research/n006_interval_aware_allocation/run_p1l_b1_near_first.py --preflight
# Only after 5/5 preflight PASS:
mise exec -- python scripts/research/n006_interval_aware_allocation/run_p1l_b1_near_first.py
```

No N006 B1a GPU result or claim of HWRT-free device support. Keep each new campaign separate from prior A1b/B0; do not infer an accepted optimization from bare shader-code changes.


## P1l-B1a five-scene exact output preflight PASS — full timing still required

User-uploaded `n006-p1l-b1a-summary.json` for B1a at clean source `9fe4126aebab26cacf6f04b336ca1544befd2de4`: **`mode=preflight`, `status=complete`, `failures=[]`, five fresh Software processes and 10/10 measured original/candidate `01` HDR PFM frames matching previously accepted case-specific SHA**, plus actual `primary_hits` byte-exact parity between arms in all five scenes, zero reported oracle/counter/timing failures. CPU N004 full hit reference on each process' candidate frame 1 only. [Full preflight evidence and caution](./results/022-p1l-b1a-five-scene-preflight.md).

**One-pair preliminary GPU primary times** (B1a minus baseline): static **−13.85%**, camera **−5.09%**, light **−34.69%**, deforming **−20.37%**, but **moving-rigid +42.13% SLOWER** and complete renderer **+23.46% slower**. This is **not** frozen performance acceptance: only one baseline-first pair/scenario, no counterbalanced BA order, and no independent repeated medians. The moving-rigid regression is a concrete reason **not to adopt or selectively exclude this scene before full measurement**.

**Preflight GO to frozen matched experiment unchanged**: 5 scenes × 3 fresh processes × 24 `011001100110011001100110` alternating target frames = **15 processes, 360 measured frames, 180 adjacent A/B pairs**, hard 600s process timeout, full accepted HDR SHA/primary hit parity/GPU closure per measured frame, per-scene median/pair win rate/process medians, and same strict no-any-scene complete-renderer regression worse than +3% acceptance gate. Only if GPU evidence meets every frozen condition may B1a be considered an exploratory Software primary improvement. Execute:

```sh
git pull --ff-only
mise exec -- python scripts/research/n006_interval_aware_allocation/run_p1l_b1_near_first.py
```

The full-run result is not collected yet; retain B1 preflight as a separate evidence artifact and the warning even if other conditions win. No N004/N005/GH Actions modifications.


## P1l-B1a matched GPU A/B REJECTED — correct pixels, slower Software primary

[Accepted B1a full matched result](./results/023-p1l-b1a-matched-near-first-reject.md), user-uploaded `n006-p1l-b1a-summary(1).json` at measured clean `e13957cecd426a8939362ab433de20abaab48a25`: **15/15 fresh Software processes, 360/360 previously accepted PFM SHA and 360/360 original-vs-candidate GPU primary-hit byte-exact, 180/180 same-process matched adjacent AB/BA pairs, no errors**, sampled N004 CPU per-ray oracle only once per process on first candidate index 1, original disjoint GPU timestamp and storage/hash/ray count gates. Frozen `011001100110011001100110` order delivered 18 AB and 18 BA pairs per scene. **Formal=false** and no no-HWRT GPU portability proof.

Primary stage paired **median candidate-minus-baseline GPU percentage** by scene (negative=faster): **static −1.35% (18/36 faster pairs), camera +6.19% (15/36), light +12.60% (13/36), moving-rigid +10.11% (14/36), deforming +15.89% (12/36)**. All **0/5** scenes fail the predeclared combination of ≥5% lower median primary GPU, ≥24/36 faster pairs, ≥2/3 negative process medians; **4/5** also violate the renderer non-regression ≤+3% gate: camera +3.24%, light +4.01%, moving +5.08%, deforming +4.43%. Static primary gain is only −1.35% and its 3 process medians are +62.20 / −194.47 / +191.90µs. **Decision: REJECT B1a, do not ship/default the N006 approximate near-first child-center reorder.** The earlier preflight's four apparent improvements were single unbalanced 01 pairs and did not replicate.

For each scene, primary AB `01` candidate-minus-baseline medians were less unfavorable than BA `10` medians (static −74 vs +88 µs, camera +35 vs +76, light +63 vs +183, moving +34 vs +188, deforming +102 vs +228). The frozen schedule collected exactly 18 pairs in both orders, but order-dependent behavior and hundreds-of-µs individual differences warrant explicit timing-noise/interference caution; **no causal claim** of cache, GPU clocks, or near-first node visitation can be inferred. The shader adds two child-node loads for its center-projection ordering, but candidate node counts were **not recorded** in B1a, so even a pruning benefit is unverified.

**Next [frozen bounded P1l-B1b diagnostic](./experiments/017-p1l-b1b-near-first-pruning-attribution.md):** a separate **five-process, count-only** comparison of unchanged N006 B0 fixed-order primary and cloned B1a near-first **per-pixel BVH node/triangle counts**, on identical target inputs. Require both instrumented hits byte-exact to accepted original, zero overflow, full PFM SHA, and report sums/percentiles/fewer/equal/more per-pixel visits. Keep instrumentation outside original GPU timing. If visit counts fail to improve, abandon this heuristic; if they improve but timing worsens, quantify shader instruction/extra node-load tradeoff before any different implementation. **B1b code and GPU results NOT YET AVAILABLE**; no request to rerun rejected B1a. N004/N005/GitHub Actions untouched. Original #42 predictive marginal-value allocation remains gated.


## P1l-B1b count-only paired traversal attribution implemented (GPU gate pending)

Follow-up to [B1a's REJECTED 180-pair GPU result](./results/023-p1l-b1a-matched-near-first-reject.md). [The B1b experiment was frozen before implementation](./experiments/017-p1l-b1b-near-first-pruning-attribution.md). Existing original N003 and E003 shaders and N004/N005 paths remain unchanged. **B1a stays rejected regardless of B1b's future work counts.**

New opt-in `--p1l-b1b-counts` within the N006 intervention command enables a **single uninstrumented, frozen lean-copyback software target** after 32 original source and eight stable target warmups. The one target's previously accepted backend-specific HDR PFM SHA, canonical ray/owner/storage/hash and GPU timestamps are checked as before. It then performs **an independent separate GPU command** with (a) unchanged B0 fixed-right-first primary count shader, and (b) new N006-only counter variant using B1a's identical ray-projected child-center near-first ordering. Both instrumented primary-hit buffers are private; **each must byte-match the original uninstrumented GPU primary hit buffer** or abort. GPU timing is taken only from the original shader *before* these count-only GPU passes. The sampled full N004 CPU hit oracle executes once per process on target frame 0; no reference image rendered.

The two count modes report per-screen-pixel **node pops, triangle tests, hit flags, stack overflow** (sum, mean, p50/p90/p99/max and nonzero), plus the **per-pixel candidate-minus-original signed distribution** (total, mean, p50/p90/p99/min/max and number of pixels with fewer/equal/more visits). All data are fail-closed against missing fields, count-shape errors, histogram inconsistencies, pixel-partition mismatch and overflow.

The dedicated `scripts/research/n006_interval_aware_allocation/run_p1l_b1b_work_counts.py` supports a two-scene `--smoke` diagnostic or (default) the **prospectively frozen, independent all-five-scene run** in one invocation, each process capped at **600 seconds** and checkpointed. Full-run summary **automatically classifies mechanism only**: if no scene has fewer primary node visits, abandon the center-order pruning heuristic; if any reduce visits despite the already-rejected GPU results, investigate extra child loads/branch occupancy before any new *frozen* timing comparison. Counts alone cannot reopen B1a, assert a GPU speedup or prove no-HWRT device portability. Retained raw output and summary filename: `n006-p1l-b1b-counts-summary.json`.

**Implementation pushed, but C++/GLSL build, Python unit tests and user GPU evidence are not yet verified.** From clean NixOS branch, run:

```sh
git pull --ff-only
mise run build
mise exec -- python -m unittest discover -s scripts/research/n006_interval_aware_allocation -p 'test_*.py'
mise exec -- python scripts/research/n006_interval_aware_allocation/run_p1l_b1b_work_counts.py
```

No manual pause between smoke and full five-scene test is needed (the default command tests all five); no accepted N004/N005/GH Actions changes. Research is ongoing: B1b results must drive the next bounded shader or ray allocator question, **not** a declaration that GI research has ended.


For a **single continuous local invocation** (build → tests → all-five-scene GPU capture, stopping only on a real failing gate), the NixOS operator can instead use:

```sh
git pull --ff-only
bash scripts/research/n006_interval_aware_allocation/run_p1l_b1b_verified.sh
```

The wrapper neither commits/pushes nor modifies CI. It fails immediately if not on the research branch, if build/tests fail, or if any GPU case fails/times out. The full JSON summary is a local GPU artifact; the assistant cannot execute or retrieve it from the user's unconnected NixOS host. **This experiment's implementation can be complete while the scientific study remains unfinished until actual GPU evidence arrives.**


## P1l-B1b five-scene GPU work-count mechanism PASS — scientific next-step handoff prepared

User-uploaded `n006-p1l-b1b-counts-summary.json` measured at clean HEAD `b4f0a8bffc78612f69b78f7ca5ec2be0c8560659`, SHA256 `9c6bb80ee45d09de028228b9ba0a6e0a05dfab9b8292d4dbe2e22ba217284662`. **`mode=five-scenes`, `status=complete`, `failures=[]`, five of five supported Lane-E-final SOFTWARE cases passed** exact accepted PFM SHA and dual separately instrumented GPU primary-hit byte identity; both count shaders had **zero stack overflow**. GPU timestamps here cover the *original uninstrumented* renderer, **not** the near-first candidate. This is count-only evidence, not new performance acceptance. Full [accepted B1b result](./results/024-p1l-b1b-five-scene-near-first-work-reduction.md).

**B1b establishes real pruning across all five:** original→B1a-near-first primary node visits reduce **2.23–5.91%** and triangle tests reduce **6.52–31.42%** depending on scene. However **94–96% of screen pixels have unchanged BVH node visits**, and some p99 visit tails increase. Thus this heuristic does reduce aggregate BVH work, **but the earlier B1a performance result remains REJECTED** (15 fresh processes, 360 accepted PFMs, 180 matched AB/BA GPU timing pairs, 0/5 primary-stage winning scenes, and 4/5 complete renderer >+3% regression). The added two child-node reads per internal node plus math/branch and SIMT divergence are plausible, **unmeasured** reasons for GPU cost; neither physical memory traffic nor occupancy was measured. Do not promote B1a into accepted shaders based on these counts.

The next research is intentionally deferred to a **separate ChatGPT session**, with a complete [next-session handoff](./HANDOFF_NEXT_SESSION.md) covering decisions, evidence, exact source paths, protocol constraints and a ready-to-paste resume prompt. Start with bounded **P1l-B1c offline SPIR-V instruction and child-bound fetch audit**, then choose whether a cheaper near-first proxy is scientifically worth a new frozen GPU protocol; otherwise redirect to independent E003 secondary traversal. The parent Issue #42 predictive interval-aware P1/P2 allocator and broad HWRT-free goal remain unresolved. **Do not run another B1a/B1b GPU campaign by default.** No GitHub Actions, N004/N005 or accepted N003/E003 modifications.

## P1l-B1c packed-axis lower-overhead hypothesis — implementation pushed, GPU unmeasured (2026-10-11)

After B1b's confirmed BVH work reduction and rejected B1a GPU timing, [prospectively frozen B1c protocol](./experiments/018-p1l-b1c-packed-axis-proxy.md) was committed **before** B1c shader implementation. The new opt-in B1c uses **one packed axis/orientation in an already unused internal `GpuBvhNode.data.z`**. Its N006-only shader reads the parent's existing node payload and selects child push order from the ray direction; unlike B1a, it does not fetch two child-node AABBs for sorting. This is a **different, approximate heuristic**, not exact entry-distance traversal, and is not expected to preserve B1a's counts automatically. Existing N003 and E003 shader sources remain unchanged.

A N006-only host packing helper updates the metadata for both original/source and rebuilt target BVHs, including moving-rigid/deforming; leaves preserve their original primitive-begin index, 48B GPU nodes and descriptor capacities are unchanged. Metadata processing is an O(node-count) CPU pass, **not free**; the runner preserves its measured CPU packing time/node counts separately from GPU timestamps. The B1c runner uses the historical exact-image/primary-byte checks with a distinct opt-in `--b1c`, distinct run paths and distinct protocol version; it does not relabel old B1a evidence. The offline SPIR-V audit records actual built shader binary hashes, static opcode frequencies and compiler data, **not** dynamic SSBO/memory/occupancy cost.

**Implementation branch HEAD at publish:** `e01ae744f51edd8881695192fb1ea42278d06be4`; CPU helper isolated C++ smoke test in assistant sandbox compiled and passed, **but complete NixOS Vulkan/C++ build, full Python tests, SPIR-V binary audit and actual B1c AMD GPU timing have not been run yet**. B1c correctness/performance is `UNMEASURED`; B1a `REJECTED`, B1b `PASS (work counts only)`. No new reference or hardware-absent test.

Run one fail-closed sequence from the research branch (requires NixOS GPU for final stages):

```sh
git switch research-n006-interval-aware-allocation
bash scripts/research/n006_interval_aware_allocation/run_p1l_b1c_verified.sh
```

The sequence checks branch/clean state, pulls, builds, runs all N006 Python tests (including optional C++ header compile), captures the compiler SPIR-V audit, performs mandatory 5-scene two-frame GPU preflight and **only on exact correctness PASS** runs the prospectively balanced 15-process GPU comparison. Reports under `out/research/n006-interval-aware-allocation/p1l-b1c-*/` and `.../b1c-spv-audit.json`. Share the B1c summary JSON **and** static audit file (or earliest failure); do **not** rerun B1a/B1b. After evidence, apply frozen performance gates before considering acceptance. Original Issue #42 P1/P2 predictive-value study remains gated.

## P1l-B1c matched GPU decision REJECT / E003 C0 begins (2026-10-11)

Uploaded B1c summary `n006-p1l-b1c-summary.json`, SHA-256 `49b561e6e1daffeb611d1571daa8236a76a0f5328902ed0d1b656e8af59fe11e`; measured clean `11eaabfa7666c41cdda84a679caae62d9a031711` on AMD RADV. **All 15/15 processes, 360/360 accepted image SHA and primary-hit parity frames, 180/180 balanced A/B GPU pairs, zero failure** according to uploaded summary. Frozen gate: only **static 1/5 primary PASS**, whereas 3/5 required; light-motion renderer **+5.237%** vs +3% permitted. Therefore **B1c REJECT**, no opt-in promotion. Full [accepted decision](./results/025-p1l-b1c-packed-axis-performance-reject.md). CPU packing occurred on initial/target BVH and cost 0.645–1.393 ms cumulative per process, not counted in GPU-stage times. SPIR-V audit file was not provided; do not ascribe slowdown to a compiler-specific mechanism. Previous B1a `REJECT` and B1b `PASS/work only` unchanged.

**Next independent focus: E003 quantized secondary traversal**, not another N003 primary child-sort heuristic. Its baseline performed 25.5–26.3 quantized child AABB tests/actual ray. [Frozen C0 experiment](./experiments/019-p1l-c0-e003-wide-child-cost-audit.md) audits original E003 source/compiler cost and already-observed B0 counters before any new runtime math. A separate `audit_p1l_c0_e003_spirv.py` plus unit tests was pushed. Important source audit: the renderer references `e003_instance_quantized.spv` but the current CMake targets do **not** register its generation. A new **N006-only** `n006_p1l_c0_e003_source_rebuild.spv` target recompiles the untouched E003 source, and C0 fails closed if its binary SHA is different from the runtime's active SPIR-V or if the active binary is absent. This avoids silently profiling stale shader code. No actual C0 compiled artifacts provided yet, no new E003 GPU optimization/timing.

The C0 script can be run after an existing configured `mise run build` (not a new GPU experiment): `mise exec -- python scripts/research/n006_interval_aware_allocation/audit_p1l_c0_e003_spirv.py`. No user GPU execution requested until this static gate leads to a bounded C1 hypothesis. If C0 shows no credible cost reduction, document NO-GO and investigate scene-conditional shadow work. The N006 RC-specific predictive marginal-value P1/P2 remains gated.
