# N009 final decision — SC NO GO, BF gates PASS, PT INCOMPLETE

**Date:** 2026-10-14 JST · **Branch:** `research-n009-scene-contract` · **Issue:** [#5 follow-up](https://github.com/owoDra/real-time-gi-lab/issues/5)

**Decision:** conclude N009 under the [preregistration and Amendment 1](../experiments/001-scene-contract-backface-and-probe-attribution.md). Exit SC is **NO GO** for total-reference eligibility; BF1–BF3 **PASS** within their declared scope; Exit PT is **INCOMPLETE** for every analysed capture. Computation is complete, including both transports and both GPU backends. No threshold, candidate set, seed, sample cap, scoring mask or gate is changed for this decision.

## Evidence and provenance

The three questions were whether scene contract C1 supplies cross-class eligible total references, whether BF-P removes the C7 back-face inconsistency, and which fixed-order probe stages explain indirect deficit/leak. C1 applies glTF world transforms, the authored camera and a selected interior point light; BF-P makes all triangles opaque, two-sided Lambert surfaces for every ray type. The reference oracle, classifier and N007 screen remain the frozen N008/N007 implementations.

- Preregistration: `f215bc7a1ec692c5ba77599be6dfd694ab113c32`.
- Selection, Amendment 1 and state lock, before indirect/total acquisition: `bc2419c08797f24eaecb8d3d7b368eb26d967054` (also the source identity in result 003).
- Final attribution record: `98742a7b6dd447d2e3ff3a06692c23039b72f4de`.
- Completed evidence/handoff checkpoint: `49914b31d84d8df39ae288e152a02d440a4b7a41`. The preceding commits are ancestors of this checkpoint; its parent study is N008 at `12f4846`.
- Prior authorised GPU execution, as recorded in [006, Execution complete](006-interim-status-and-resume.md): AMD Radeon 8060S, RADV STRIX_HALO, `phos-n009-capture --target-state --spp 512`; 10 captures, software and hwrt for C1/C2/C4/C5/C7. This write-up uses those archived captures; it performs no new GPU acquisition.
- Private raw evidence: `out/research/n009-scene-contract/selection/`, `states/`, `ladder-bc2419c/`, `gpu-bc2419c/`; C7 reuses `out/research/n008-hdr-oracle/phase-b-9aab73b/B7_T_B2` (and T_B8 for the GPU diagnostic); the old B4 capture is `out/research/n007-reference-validity/p1a/probe-shadow-dabe590b0c6e/`. These ignored assets are not published with this record.

The recorded evidence bytes are retained. SHA-256 identities of the final input records are:

| Record | SHA-256 |
| --- | --- |
| [001 selection](001-contract-selection.json) | `262074c1dd4a2ca9a349dbae6101f9f1f0b7886ab043ebc3bc6d3ae06642e59e` |
| [002 state lock](002-state-lock.json) | `4717341c53dc7052aa96a8287332f715312f5208d6939e331df772e6b24351a5` |
| [003 final ladder](003-ladder.json) | `6a96d8e14f0271bb7892ea868cd0a9f0d6d9b05f94f5dd5f986399d2962415a8` |
| [007 GPU comparison](007-gpu-compare.json) | `e0c33be69fdfc98f2baa9b7b028e498bfcf600c68d30d9598ea75d271f474bbc` |
| [008 final attribution](008-probe-attribution.json) | `38db94ff8af2cc5be660527ff58e92cd9f874dc55b0e141413f9e794a9052327` |

[003 interim](003-interim-T_B2-ladder.json), [004](004-interim-probe-attribution-C7-software.json), [005](005-interim-probe-attribution-B4-old-R0-R2.json) and [006](006-interim-status-and-resume.md) remain historical checkpoints; final computation is recorded in 003/007/008. This is an AI-assisted synthesis of existing evidence under human oversight; see the [workflow disclosure](../../../../docs/ai-research-workflow.md).

## Exit SC — NO GO for total references

**Amendment 1 is a disclosed selection outcome, recorded after selection and before any reference image.** Only L1/L2/L5 passed free-space and direct-support gates, but neither L2 nor L5 was at least `0.1 × diag` from L1 (233 versus 463.7). C3 light motion is therefore **NOT_CONSTRUCTIBLE**. No candidates or thresholds were added. The amendment continued C1/C2/C4/C5/C6 and already made cross-class GO unattainable; a Bounded GO still required at least one statistically eligible Sponza total reference.

All five constructed Sponza cells are **DIRECT_DETERMINISTIC_PROVED** under both T_B2 and T_B8. This proves only the deterministic direct reference. None has a statistically eligible total reference. At the frozen four-seed 8192-SPP cap, all have total union-active support 57,600/57,600 pixels, but fail both the active p99 absolute limit `1e-5` and relative limit `5%`:

| Cell / class | T_B2 p99 abs | T_B2 p99 rel | T_B8 p99 abs | T_B8 p99 rel | GPU state |
| --- | ---: | ---: | ---: | ---: | --- |
| C1 static | 3.03648e-5 | 5.47275% | 9.04685e-5 | 5.99030% | byte-attested, both backends |
| C2 camera / disocclusion target pose | 3.03809e-5 | 5.54272% | 9.00626e-5 | 5.98965% | byte-attested, both backends |
| C4 moving rigid | 3.04270e-5 | 5.66319% | 9.33574e-5 | 6.76400% | byte-attested, both backends |
| C5 stable-topology deforming | 3.04424e-5 | 5.44314% | 8.96315e-5 | 6.08705% | byte-attested, both backends |
| C6 topology churn | 3.05218e-5 | 5.46508% | 8.78284e-5 | 6.23046% | oracle-only; GPU capture unsupported |

These are the worst pairwise screen values at the cap, not errors of the GPU image. The unchanged screen requires two consecutive qualifying levels with stable support; no cell qualifies at any level. Thus the count of eligible C1–C5 total references is **zero**, giving **Exit SC = NO GO**, not Bounded GO. C6 has its final oracle-only classification; C3 has no exported/rendered/captured state. C7 is the separately eligible non-Sponza N008 B7 reference and cannot satisfy the Sponza exit rule.

C1 supplies broadly lit states and deterministic direct references for five classes, resolving the lack of useful illumination in these newly declared states. It does not establish total convergence within this study's budget. The approximately `1/sqrt(spp)` screen decline is descriptive; there is no extra sample level, relaxed threshold or total-quality score.

## Exit BF — BF1–BF3 PASS within preregistered scope

Evidence: [007](007-gpu-compare.json).

| Gate | Frozen rule | Observed result | Decision |
| --- | --- | --- | --- |
| BF1 | every captured triangle sided = 1; geometry/frame bytes equal CPU export | all 10 captures pass; C1/C2/C4/C5 match their lock; C7 passes the N008-equivalence check | PASS |
| BF2 | C7 primary mask/primitive mismatch ≤0.1% of 57,600 pixels, both backends | 0 pixels in software and hwrt, versus 4,978 in N008 B7 | PASS |
| BF3 | C7 direct max relative error ≤1e-4 on matched reference-positive pixels, including former back faces | 1.0848809147454133e-5 on all 6,943 reference-positive pixels, both backends | PASS |

C7 reuse is mechanically attested: identical N008 B7 frame bytes, vertices and ids, all sided flags = 1, and transport equivalence under BF-P. The C7 direct comparison also reports one GPU-only positive pixel (energy 4.38780e-5) where the reference is zero; the relative-error gate has no denominator there. Preserve this diagnostic limitation rather than claiming exact equality everywhere.

BF2 is preregistered **for C7 only**. Sponza mask mismatch is zero, but primitive mismatches are 74 pixels in C1/C4/C5 and 108 in C2 (0.1285% / 0.1875%). The per-row `bf2_pass=false` fields for these cells do not change the C7 exit gate and do not prove Sponza visibility agreement. The unchanged diagnostic excludes these primary mismatches.

### Sponza direct pixels — unresolved (未解決)

Even on the matched-primary, reference-active scoring mask, **max direct relative error is 1.0** in C1/C2/C4/C5, for both transports and both backends. There are **8 / 12 / 8 / 8 GPU-zero, reference-positive pixels**, respectively. Relative bias of the scored sum is small (about −6.99e-5 to −8.32e-5), but does not establish per-pixel direct agreement. The maximum absolute error is about 7.87e-4. These pixels are **unresolved (未解決)**.

No new CPU shadow-ray/root-cause investigation was performed for this final decision. The shadow-edge/offset explanation suggested in result 006 remains an untested hypothesis. No pixels are newly excluded and no Sponza direct agreement or resolved cause is claimed.

For context only, T_B2 whole-image GPU/reference indirect-sum ratios on Sponza are 1.316–1.392 and total-sum ratios 1.154–1.198. Those references are not total-eligible: these are unscored descriptive ratios, not quality scores or wins. On eligible C7, the T_B2 reference-active indirect bias is −91.9721% and total bias −13.3960%; whole-image ratios are 0.089761 and 0.866133. These use different masks from the PT stage-sum diagnostic below. The backends give the same classifications and counts, with small floating-point differences in some Sponza direct summary values.

## Exit PT — INCOMPLETE for every analysed capture

Evidence: [008](008-probe-attribution.json). No Sponza cell met the T_B2 total-eligibility condition for PT, so no Sponza R0–R6 job was required or scored.

| Capture | V1: R0 replay ≤1e-6 and zero positivity disagreements | V2: ≥99.9% re-quantise within ±1 LSB | V3: ≥99% secondary re-trace match | V4: R6 sum bias ≤3% | Attribution |
| --- | --- | --- | --- | --- | --- |
| C7 software | FAIL: max abs 3.051804e-5; 21 mismatch pixels | PASS: 37,440/37,440 exact | PASS: 37,440/37,440 | PASS: +0.0294067% | **INCOMPLETE** |
| C7 hwrt | FAIL: same max abs and 21 pixels | PASS: 37,440/37,440 exact | PASS: 37,439/37,440 (99.9973%) | PASS: +0.0294067% | **INCOMPLETE** |
| Old N008 B4 / N007 capture, R0–R2 only | PASS: max abs 1.822542e-12 | PASS: 134,816/134,816 exact | FAIL: 117,191/134,816 (86.9266%) | not applicable: reference NO_SUPPORT | **INCOMPLETE** |

The C7 V1 failure is reported in 006 as CPU/GPU float probe-key assignment at cell boundaries. Old B4 predates BF-P and uses single-sided GPU traversal, while the CPU re-trace is two-sided. These reported explanations do not waive either failed gate. R0–R2 on old B4 use captured secondary hits rather than the re-trace; that preserves their diagnostic value, but the capture is still formally INCOMPLETE.

### Fixed-order C7 stage observations — diagnostic only

Both backends give the following stage metrics on the original 57,600-pixel matched-primary mask. Bias is relative to the T_B2 indirect reference sum; reference-zero energy is included in stage sums.

| Stage | Change | Sum bias | Change in bias (percentage points) | RMSE | Zero on reference-positive pixels | Energy on reference-zero pixels |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| R0 | integer GPU replay | −91.4242% | — | 4.88314e-6 | 6,842 | 6.71397e-4 |
| R1 | remove quantisation | −92.1056% | −0.6814 | 4.88766e-6 | 6,842 | 6.75781e-4 |
| R2 | secondary shadow ray | −96.2879% | −4.1823 | 4.97284e-6 | 7,027 | 6.50774e-4 |
| R3 | full probe-key coverage | −27.4387% | +68.8493 | 5.06089e-6 | 5,287 | 2.05771e-3 |
| R4 | unbounded last interval | +22.2275% | +49.6662 | 6.56438e-6 | 4,167 | 2.60231e-3 |
| R5 | 256 Fibonacci directions | −3.3978% | −25.6253 | 5.16989e-6 | 3,763 | 2.21360e-3 |
| R6 | pixel cosine one-bounce, 1024 samples | +0.0294% | +3.4272 | 2.46944e-7 | 411 | 1.01545e-7 |

By the frozen largest-absolute-bias-change definition, R2→R3 (coverage) is the **diagnostic dominant transition**, followed by R3→R4 (range). The model records 1,774 produced versus 3,278 required keys, 20,814 missing-key lookups, and 6,548 hit pixels with a missing key. R4 overshoots and R5 reduces that overshoot; closure of the sum at R6 does not prove pixelwise closure. This order-dependent decomposition is not a validated COMPLETE attribution or an estimator fix.

**Post-hoc sensitivity analysis:** result 008 excludes the 21 V1 mismatch pixels, after observing the failure. R0 matches on the remaining mask; biases become R0 −91.4408%, R2 −96.2939%, R3 −27.2383%, R4 +22.5767%, R5 −3.1266%, R6 +0.0281%. The largest change still occurs at coverage (about +69.06 percentage points). This is explicitly **post-hoc**, not preregistered validation, and does not turn V1 or Exit PT into PASS/COMPLETE.

### Old B4 shadow replication — diagnostic only

The independent N008 BVH shadow test changes the old capture's R1 leak energy from **0.24047480889096767 to 0** at R2 (100% removal). Its R0 sum is 0.2673380636301213; R0 reproduces all 9,247 original positive pixels. Dequantisation at R1 produces 10,942 positives; R2 has none. This corroborates the secondary-shadow omission mechanism on this existing diagnostic capture.

With a NO_SUPPORT reference, relative bias has a zero denominator: there is **no preregistered dominant factor by relative bias** for B4. The JSON's `dominant_transition: R2` describes the largest energy removal, not a valid relative-bias gate. V3 still fails, R3+ is not used, and no historical N006/N007/N008 outcome or original archived-frame cause is revised.

## Disposition, limits and next questions

Close N009's computation/write-up with **SC NO GO / BF PASS / PT INCOMPLETE**. The C1/BF-P overlay remains opt-in (`PHOS_BUILD_N009`, default OFF); adoption into the default Renderer requires a separate architecture decision and appropriate executable validation.

- A future total-reference study must preregister its budget and convergence method; N009's full-support but non-converged cells remain negative at the frozen cap.
- A light-motion study needs a new preregistered candidate set; C3 is not rescued here.
- A future PT validation must reproduce GPU key lookup without excluding failures, and handle sidedness consistently for any new B4-style capture.
- Sponza's max-relative-error-1.0 direct pixels need a separately labelled CPU diagnostic before any per-pixel agreement claim.
- Measurements concern one GPU and frozen target poses, not motion sequences/temporal reuse. Textures, alpha masks and glossy BSDFs remain unvalidated; BF-P intentionally differs from glTF raster back-face culling. No general GI quality ranking, GPU-time improvement, persistent/true-peak-memory improvement or release-level acceptance is established.

**Checks for this publication:** research harness, result-index/local-link consistency, evidence hashes and Git ancestry are checked. Source, shaders and the active build graph are unchanged. Builds, executable tests and GPU/runtime/correctness checks were **not rerun**; this document does not claim new runtime regression validation. No GitHub Actions are added, and N001–N008 results retain their exact bytes.
