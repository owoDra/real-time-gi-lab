# Current research status (2026-10-14)

**Status: empirical architecture and image-producing renderer demonstrated; general real-time GI superiority NOT established.** This is the sole cross-lane status/adoption synthesis. For the long research history see [archived 2026-10-02 status](archive/status-2026-10-02.md); for exact decision evidence use the linked lane results and [branch inventory](branch-inventory.md).

## Current incumbent — adoption versus experiments

**Active work: N010, the final comparison-preparation study.** [Protocol](lanes/n010-comparison-readiness/experiments/001-comparison-readiness.md). User-directed sequence is N010 → Lane M GI competitiveness; no further N-series preparation lane. Readiness requires an executed quality/time/memory pilot, physically validated eligible references and full Renderer timing calibration. Historical Lane M topology results retain their identity. N010 has not yet passed its readiness gate.

N010 has now produced an actual first comparison cohort: native GPU pixel
path tracing passes C7 quality at 256 samples (T_B2) / 1024 (T_B8), while the
incumbent fails with roughly 91% missing one-bounce indirect energy. A separate
dense repository RC control also fails. These are measured quality outcomes;
pilot timings remain uncalibrated. Sampler precision Amendment 2 passes without
changing thresholds; original failed crosscheck remains retained. C7 references
and C8–C12 references are eligible; all 145 controlled dynamic source/target/
recovery images are scored. C9 RC indirect sum reaches about 7.645 times the
reference; fixed PT 256-spp losses remain. The C8/C9 complete budget ladders
both select 1024 spp as a passing budget for T_B2 and T_B8. All 29 dynamic
allocation ledgers independently replay to zero teardown within the cap.
RTXGI Vulkan host SDK builds without CUDA; its GPU adapter remains a Lane M
requirement. Sponza C1 T_B2 is now eligible at 16384/32768 consecutively. Its incumbent
indirect NRMSE is 88.8399% with +35.8544% sum bias (FAIL), whereas GPU PT
passes at 256 and 1024 spp. Sponza C3 T_B2 also qualified: incumbent indirect NRMSE 87.9404% / bias
+35.2394% is FAIL, while PT passes at 256/1024 spp. T_B8 and the
remaining Sponza cells are in progress. Remaining N010 work is the full
Sponza pilot, complete Renderer timing calibration and fail-closed handoff.
Diagnostic sizing result 027 failed under concurrent CPU work and remains
retained; Amendment 4 measures inner known-work cost to size the prospective
calibration dose, without changing full-boundary acceptance thresholds.
Result 028 also failed sizing; prospective Amendment 5 uses larger observable
probe doses and records binary/shader identity and CPU known-work witnesses.
Diagnostic sizing 035 passes all 16 boundaries under CPU load; quiet sizing
and accepted blocks remain required. Controlled T_B2 PT 1024-spp confirmation
passes all 25 dynamic frames and five memory replays (037/042). Ten official
RTXGI shaders compile to SPIR-V on the CPU (038); DDGI GPU runtime is unfinished.
[Interim comparison findings](lanes/n010-comparison-readiness/results/033-interim-comparison-findings.md).
[Residual direct diagnosis](lanes/n010-comparison-readiness/results/053-residual-primary-contract-diagnosis.md)
finds different primary primitives at both remaining direct-zero pixels and
supports a legacy primary tie-interval mechanism in CPU geometry. A GPU repair
is unverified; both pixels remain UNRESOLVED and included in all scores.
Cache equivalence 022 now passes all 20 declared cases. Controlled reference
provenance audit 051 passes all 12 C7–C12 transports, including re-execution
of their convergence screens; this subset does not establish whole-corpus
readiness. Exact-prefix proof 050 is running before any incremental use.
[Current execution evidence](lanes/n010-comparison-readiness/results/008-interim-execution-and-resume.md),
[PT quality ladder](lanes/n010-comparison-readiness/results/013-c7-pt-cohort-pilot.json),
[dynamic comparisons](lanes/n010-comparison-readiness/results/020-controlled-dynamic-summary.json),
[AMD/Vulkan SDK build](lanes/n010-comparison-readiness/results/023-ddgi-vulkan-host-build.json).

| Subsystem | Current incumbent / classification | Evidence and boundary |
| --- | --- | --- |
| Work producer | **Adopted:** A001 GPU visibility-driven Split RC, natural append order; no global reorder | [Lane A](lanes/lane-a-split-rc/results/index.json), M0; Lane D does not supersede A001 |
| Primary traversal | **Adopted on measured Radeon 8060S:** HWRT/TLAS | [Lane B](lanes/lane-b-traversal/results/index.json), [I001](integration/results/index.json) |
| HWRT-free traversal | **Adopted fallback:** Segment DDA/hash + conservative quantized Micro BVH8 | Lane B B003; lower-tier alternative, not claimed universally equal to HWRT |
| Radiance storage | **Adopted baseline:** C001 per-probe open-addressed sparse hash | [Lane C](lanes/lane-c-storage-locality/results/index.json); page/clipmap variants conditional |
| Dynamic ownership | **Adopted incumbent:** immutable static, transform-only rigid, object-local deform UPDATE, object-local rebuild for topology changes | [Lane E](lanes/lane-e-dynamic-geometry/results/index.json), [timing revalidation](lanes/lane-e-timing-revalidation/results/) |
| Dynamic backend replacements | **Not promoted:** transient LBVH, clustered two-level variants | [Lane M](lanes/lane-m-topology-backend-crossover/results/); Lane E incumbent retained |
| Full Renderer | **Working research implementation:** N001–N004 and separate N005/N006 experimental variants | [Lane N](lanes/lane-n-end-to-end-renderer/results/index.json), [N005](lanes/n005-adaptive-tracing/), [N006](lanes/n006-interval-aware-allocation/) |
| N005 adaptive tracing | **REFINE / conditional:** no universal policy accepted | [N005 evidence](lanes/n005-adaptive-tracing/results/) |
| N006 interval-aware allocation | **STOP:** Q8 influence exists; +4-ray signed HDR quality lift not detectably proven; do not initiate P2/P3 | [N006 final result 045](lanes/n006-interval-aware-allocation/results/045-p1m3c-deforming-signed-quality-no-detectable-lift-stop.md) |
| N009 scene contract / back faces / probe attribution | **Concluded:** SC NO GO, BF1–BF3 PASS, PT INCOMPLETE; C1/BF-P remain opt-in | [N009 final result 009](lanes/n009-scene-contract/results/009-n009-final-decision.md); no architecture promotion |

The current production-style Renderer uses **N-series pinned imports**, not whatever historical code happens to be stored in other lane folders. Presence of old experiment sources does not activate them.

## Evidence of improvement and limits

- **Lane E #22**, frozen Lane-L heavy recurring boundary: moving-rigid 0.330894x HWRT / 0.519178x software, and stable-deforming 0.331625x HWRT / 0.525108x software (candidate/control complete-GPU ratios); the required >=20% improvements and memory guards passed. Exact evidence remains in the revalidation lane.
- **Lane M #25:** 6,144 GPU-timing rows in 192 fresh processes on frozen primary/software tracks; transient LBVH and clustered two-level approaches did not qualify. Lane E object-local rebuild remains incumbent for topology changes/high churn.
- **N003:** reported **~2.35–3.11x Renderer speedup** against the particular vanilla Split RC control cases, accompanied by **~24–27% extra GPU memory**. These figures are not general quality-equivalent, cross-scene, or cross-GPU superiority claims.
- **N004:** motion-related image-quality weaknesses were detected. Performance success does not close image quality.
- **N005:** adaptive tracing showed conditional promise, but a single accepted scheduling rule was **not** established.
- **N006:** [Q8 replicate mechanism](lanes/n006-interval-aware-allocation/results/041-p1m3a-q8-gpu-replicated-image-mechanism.md) showed reproducible image influence; [moving-rigid reference](lanes/n006-interval-aware-allocation/results/043-p1m3b-moving-rigid-identical-reference-invalid.md) was ineligible, and [final deforming signed-quality comparison](lanes/n006-interval-aware-allocation/results/045-p1m3c-deforming-signed-quality-no-detectable-lift-stop.md) found **no detectable improvement** exceeding independent-reference noise. Extra-ray policy is not adopted; N006 P1/P2/P3 stopped.

## Measurement capability

- Performance primary: **GPU timestamps**. CPU wall: diagnostic/provenance/health, not a second equal acceptance axis.
- **Lane K:** 5% detectable effect for its calibration workload. **Lane L:** 20% detectable effect for the complete recurring heavy boundary. Transferability is **not assumed**.
- Require frozen exact semantics, process-replicated timing, all-sample retention, persistent + true-peak GPU memory, correctness and exact measured boundary. [Detailed protocol](protocol.md).
- **Reference quality caveat:** previously accepted N001 camera/moving-rigid CPU references included all-black cases, and N006 deforming references have <1% positive pixels; a zero full-frame p99 does **not** establish adequate HDR convergence. [N007 #4](https://github.com/owoDra/real-time-gi-lab/issues/4) **concluded bounded NO GO** for cross-class reference qualification on 2026-10-12; independent of this integration and original N006 decision.

N007 P0 CPU source audit and synthetic PFM diagnostics are in progress on `research-n007-reference-validity` ([protocol](lanes/n007-reference-validity/experiments/001-reference-eligibility-protocol.md), [results](lanes/n007-reference-validity/results/index.json)). **Authentic archived N006 M3b PFMs were inspected in the user's environment**: both CPU references are fully black and their pairwise RGB RMS is zero ([N007 result 003](lanes/n007-reference-validity/results/003-authentic-m3b-archive-cpu-inspection.md)); this establishes M3b reference *statistical ineligibility*, not the physical cause. Complete original M3b inspector JSON confirms Q8 has **10,076 positive pixels** against two black references (GPU/reference RGB RMS 1.6121822848358563e-05), without proving the physical source ([N007 result 004](lanes/n007-reference-validity/results/004-authentic-m3b-full-image-signal.md)). Archived cohort v1 checked only **200/338** pairs: 69 black-reference instances collapse into just **two of six distinct SHA-pair signatures**; N004/N006 were excluded by the old default cap. **All-archive scanner v2 has now completed 338/338 name-matched pairs with zero errors**: 96 black-reference/GPU-positive archive entries reduce to **4 unique candidate/reference SHA pairs**, all with the **same black CPU reference SHA** (33 distinct pairs overall). N001, N004 and N006 M3b reproduce the mismatch, whereas N006 M3c and N001 light-motion have nonzero, still not certified, CPU references ([N007 result 006](lanes/n007-reference-validity/results/006-p0-complete-archive-image-survey.md)). N007 P1-A CPU-only transport audit ([result 007](lanes/n007-reference-validity/results/007-p1a-cpu-source-shadow-contract.md)) has checked 7 actual source files with 10/10 source contracts passing; 8/8 assistant-sandbox synthetic CPU unit tests show shadow-tested vs unshadowed probe Lambert can differ on an occluder. CMake builds the live `i001_radiance.spv` from `n001_physical_radiance.comp.glsl`, not the legacy imported hash shader. This establishes a **possible source-level light-visibility mismatch**, NOT the physical cause of archived M3b positive GPU pixels. Read-only test and report code are committed; no user-local CPU run is needed for this stage. Real-frame convergence and physical validity remain **unverified**. This has no effect on N006 P1 NO GO or the historical N001/N003 result classifications. N007 P1-A-008 now adds a **diagnostic-only, default-OFF matched-frame CPU/GPU component capture path** ([result 008](lanes/n007-reference-validity/results/008-p1a-component-capture-bringup.md)): local synthetic Python 14/14 PASS, isolated C++/BVH controlled test compiled and PASS, GitHub source anchors 9/9 PASS. The assistant sandbox did **not** execute the integrated CMake build, GLSL compilation or a GPU run. Instrumentation is not yet end-to-end validated, real-frame matching/correctness and convergence remain unknown. The new code is N007-only; no archived PFM was published.

**N007 P1-A GPU-host follow-up (2026-10-12):** the opt-in capture executable compiled and completed one moving-rigid/software/target-state/512-SPP run. Its first component analyzer returned `gpu_reconstruction_passed=true` but `primary_match=false`, so no indirect attribution or physical correctness claim follows. A source audit found the N007 generated N001 runtime had omitted N006's moving-target `n006_refresh_software_primary()` call, leaving a plausible stale GPU primary BVH while the CPU traced translated world geometry. A GPU rerun with that initial refresh still failed first-hit matching (3,866 mask / 3,744 identity / 2,300 t / 2,300 normal mismatches), though GPU channel reconstruction passed and CPU/GPU direct max delta was zero. Further source audit found that `update_dynamic_geometry(true)` already translates `b_scene.triangles`, while the legacy refresh method translates again: **N007 instrumentation double-translated GPU first-hit geometry**. The new N007-only generated overlay uses already-updated world-space triangles and adds radiance positivity/hit coverage diagnostics. In addition, the software capture now downloads the actual GPU primary triangle buffer and independently verifies every 64-byte std430 triangle against the CPU world-space snapshot, rather than relying only on a source-side SHA. **GPU remeasurement confirmed `primary_match=true` (15,173 CPU/GPU hit pixels; all four mismatch categories zero) and byte-exact software-primary geometry (262,241 triangles, zero mismatches).** CPU direct/indirect/total each have zero positive pixels; GPU direct is zero, but GPU indirect/total each have **9,247** positive pixels. The GPU component reconstruction passes; indirect max absolute difference is **0.00012207217514514923**. This localizes the current matched-primary discrepancy to probe-indirect output, **not** to the source of archived M3b artifacts or physical truth ([result 009](lanes/n007-reference-validity/results/009-p1a-matched-primary-indirect-isolation.md)). A new on-device probe replay has now run: of **134,816** GPU probe work items, **18,649** generated nonzero radiance; **18,363 (98.4664%)** had an independently CPU-confirmed blocked light ray while **286** were unoccluded. All sampled GPU/CPU secondary traversal hits and fixed-radiance Lambert predictions matched (**0** mismatches), and 0 invalid IDs/hit flags were reported. Thus missing secondary shadow visibility is directly observable as a transport-model difference for this frame, not just a source-level hypothesis. **Subsequent P1-B 011 GPU-image replay has now proven** a baseline-matching image-level counterfactual that suppressing just CPU-shadowed probe contributions removes **9,247 / 9,247** positive GPU indirect pixels; this supersedes the earlier diagnostic uncertainty, although original archived M3b artifacts remain causally unattributed. See [result 009](lanes/n007-reference-validity/results/009-p1a-matched-primary-indirect-isolation.md). Original N006 decisions, HDR statistical eligibility and independent physical correctness remain unchanged/unknown. See [result 008](lanes/n007-reference-validity/results/008-p1a-component-capture-bringup.md).

**N008 Phase A (2026-10-13, [Issue #5](https://github.com/owoDra/real-time-gi-lab/issues/5), branch `research-n008-hdr-oracle`): Exit A = GO.** A new, independent CPU HDR oracle (`src/research/n008_hdr_oracle/`, opt-in, double-precision watertight path tracer sharing no N001/Lane B code) passed all preregistered physically known controls A1–A10 (102 checks: exact lit/occluded/back-face/moving-rigid frozen pose, exactly-zero sealed/no-leak rooms, strictly positive lit rooms, analytic multi-bounce sphere furnace ~1e-4, two-bounce quadrature, closed-form area light) and agreed with Mitsuba 3.6.4 on identical meshes in 7/7 cells (≤1.6e-4 relative image mean, per-pixel |z|≤6 in 100%). Injected defects (far truncation, N001 soft falloff, 1 mm light slip, 0.5% albedo, one-sided walls) are all detected. **Scope:** Lambert/point/emissive-triangle transport on controlled scenes; textures, alpha-tested foliage and glossy BSDFs are not validated, and no Renderer/Sponza reference is yet qualified. N007/N006 remain closed and unchanged. [Result 004](lanes/n008-hdr-oracle/results/004-phase-a-exit-decision.md).

**N008 Phase B/C-partial (2026-10-13):**
- **Exit B = GO, bounded.** The Renderer's own target states were exported CPU-only from verbatim-extracted Renderer code; the moving-rigid state is byte-identical to the GPU-run N007 capture. Rendering them with the validated oracle gives:
  - **non-Sponza `leak-medium`:** STATISTICALLY_ELIGIBLE.
  - **Sponza light-motion:** direct deterministic reference only.
  - **Sponza camera-motion and moving-rigid:** NO_SUPPORT (exactly unlit at the camera within the declared transport).
  - **Sponza static, deforming and topology-churn:** INELIGIBLE (sparse, non-converged).
- **Likely cause of the dark Sponza states (a state fact):** the loaders ignore glTF node transforms, and the A001 light and eye lie outside the geometry bounds.
- **Phase C diagnostic, CPU-only, on the existing N007 GPU capture of the identical state:** primary hits match exactly, and **all 9,247 positive GPU indirect pixels have zero physical support**. This is not scored, and N006/N007 are unchanged. [Result 006](lanes/n008-hdr-oracle/results/006-phase-b-exit-decision.md), [result 008](lanes/n008-hdr-oracle/results/008-phase-c-b4-gpu-diagnostic.md).

**N008 final (2026-10-13): oracle GO; cross-class Renderer reference set is a bounded NO GO.** [Result 011](lanes/n008-hdr-oracle/results/011-n008-final-decision.md)
- **State attestation:** GPU captures (RADV 8060S, software and hwrt) byte-attest the B1–B5 and B7 states.
- **Direct and shadow:** on matched visibility, the Renderer's direct/shadow term agrees with the validated oracle to float32 (B7, B3).
- **Indirect, which errs in both directions:**
  - it leaks light with no physical support in the Sponza target states (B1/B2/B4/B5);
  - it misses about 95% of the real one-bounce light on the only eligible total reference (non-Sponza `leak-medium`: total −30% for D2, −36% for D8).
- **Scope:** diagnostic only, with no ranking and no N006/N007 revision. Next: a separately preregistered scene-contract study (glTF node transforms and an interior light).

**N009 final (2026-10-14, branch `research-n009-scene-contract`): Exit SC = NO GO; BF1–BF3 = PASS; Exit PT = INCOMPLETE.** [Result 009](lanes/n009-scene-contract/results/009-n009-final-decision.md)

- **Scene contract:** transformed Sponza with authored camera/interior light has full total support, but C1/C2/C4/C5/C6 are only DIRECT_DETERMINISTIC_PROVED under both T_B2/T_B8; no total reference passes the unchanged four-seed 8192-SPP screen. C3 light motion is NOT_CONSTRUCTIBLE under the disclosed pre-reference Amendment 1. This is not Bounded GO for total references.
- **Back faces:** all 10 captures are byte-attested and two-sided. C7 has zero primary mismatches and direct max relative error 1.08488e-5 on both backends, passing the C7-specific gates. Sponza has 74/108 primitive mismatches and direct max-relative-error-1.0 pixels even on matched visibility; their cause remains **unresolved (未解決)**. Small direct sum bias does not prove per-pixel agreement.
- **Probe attribution:** C7 fails V1 (21 replay mismatch pixels); old B4 fails V3 (86.93% secondary re-trace match). Coverage/range observations and complete shadow removal on old B4 remain diagnostic. Excluding the 21 pixels is explicitly post-hoc sensitivity and does not complete attribution.
- **Scope:** computation is complete; N009's opt-in C1/BF-P overlay is not adopted. No total-quality ranking or performance/memory/temporal claim; this evidence-only write-up reruns no build, executable test or GPU/runtime check. N001–N008 results remain unchanged. Next work needs new preregistration or explicitly labelled diagnostics.

## Unresolved strategic questions

1. **Finish comparison preparation in N010, then execute Lane M GI comparisons.** N007/N008/N009 remain concluded; N009 still lacks eligible Sponza totals at its frozen cap. N010 preregisters sampling-only reference qualification, explicit correctness diagnostics, executable RC/path-tracing controls, quality matching, full Renderer GPU calibration and allocation-lifetime peak memory. No READY or superiority claim until the corresponding evidence exists.
2. **Does this architecture actually beat fair existing GI baselines** under equivalent quality/cost across multiple scenes and hardware classes? Not yet established.
3. **Which structural light-transport/storage/reuse changes** can change the total quality/performance/memory frontier beyond a locally optimized Split RC pipeline? Evaluate only after reliable baselines and bottlenecks.

See [roadmap](roadmap.md) for gates. Old status, stale next-step commands and branch-local research attempts are historical data, not the current agenda.

**N007 P1-B tooling (2026-10-12):** the current matched frame's 18,363 independently shadow-blocked positive GPU probe contributions are retained as **diagnostic-only**, not a full-image attribution. [Result 010](lanes/n007-reference-validity/results/010-p1b-reference-screen-readiness.md) adds CPU-only, GPU-free derived shadow-label reproduction, captured-probe-to-pixel replay with strict unchanged-GPU baseline image match before the occluded-sample counterfactual, and a resumable frozen four-seed 512–8192-SPP statistical screen reusing the captured real 512-SPP data. Existing N001–N006 code/shaders untouched. **Superseded by subsequent completed real local P1-B execution**: original GPU indirect image reconstructed, shadow-positive contribution ablation eliminated all **9,247** positive pixels (original sum 0.2673380636301213 → 0.0), and four-seed CPU reference SPP 512/1024/2048/4096/8192 returned zero union-active signal at every level, `statistical-screen-fail`. See [result 011](lanes/n007-reference-validity/results/011-p1b-probe-pixel-counterfactual-and-spp-screen.md). Physical correctness and original archived M3b causation remain unknown; no N001–N006 historical GO/NO GO is altered.

**N007 final bounded stop (2026-10-12):** [result 012](lanes/n007-reference-validity/results/012-n007-bounded-no-go-decision.md) applies Issue #4's frozen rule to **stop when a reliable, nontrivial HDR reference across all required dynamic classes cannot be demonstrated within resources**. Moving-rigid is mandatory and has exhausted the complete frozen four-seed 512–8192-SPP ladder with active fraction **0.0** at every level; consequently **cross-class HDR reference qualification = NO GO**. N007 P1-B isolated the image-level GPU secondary shadow omission mechanism for its **new matched diagnostic frame** (9,247/9,247 positive indirect pixels disappear when just CPU-shadowed GPU probe contributions are suppressed). Camera/disocclusion, light-motion, controlled-GPU-light, static/deforming/churn, and independent GPU camera/secondary allocation attestation remain **explicitly unmeasured or unverified**; the stop does not declare them individually wrong or correct. Physical accuracy and historical original N006 M3b frame causation are **unproven**. No original N001–N006 sources or outcomes changed. [Issue #4](https://github.com/owoDra/real-time-gi-lab/issues/4) closed as negative research outcome, not a positive GI quality pass.
