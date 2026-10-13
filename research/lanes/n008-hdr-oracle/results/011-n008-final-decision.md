# N008 final decision — physical oracle GO; cross-class Renderer reference set bounded NO GO under the current scene contract

**Date:** 2026-10-13 JST · **Issue:** [#5](https://github.com/owoDra/real-time-gi-lab/issues/5)

## Phase C GPU comparison

**How the captures were made:**
- **Executed by:** the assistant, with explicit user authorization.
- **Device:** AMD Radeon 8060S (RADV STRIX_HALO). The Renderer refuses to fall back to any other device.
- **Tool:** `phos-n007-capture`, built at `1c3cb7a`, with Renderer sources unchanged, run with `--target-state`.
- **Captures:** 10 in total, software and hwrt, for B1, B2, B3, B5 and B7.
- **Comparison:** CPU-only, using `phase_c_gpu_diagnostic.py`.
- **Evidence:** [010-phase-c-gpu-diagnostics.json](010-phase-c-gpu-diagnostics.json).

### State attestation

All 10 GPU-run captures produced `frame-state.bin` and `geometry-state.bin` byte-identical to the locked Phase B states. Together with B4 ([result 008](008-phase-c-b4-gpu-diagnostic.md)), **B1–B5 and B7 are GPU byte-attested**. B6 (topology churn) is **unsupported** by the capture tool.

### Primary visibility

| Cell | Primary visibility vs oracle |
|---|---|
| B1, B3, B5 | exact match |
| B2 | 5 px differ |
| B7 | **4,978 px differ, all of them back faces of single-sided triangles**: the Renderer culls these and sees through them, while the oracle reflects on both sides. They are excluded by the preregistered scoring mask. |

### Components (luma, matched-visibility mask; software and hwrt gave identical summaries)

| Cell / reference class | Component | GPU vs locked reference |
|---|---|---|
| B7 `leak-medium` (STATISTICALLY_ELIGIBLE) | direct (2,160 px) | **agrees to float32:** max relative 1.1e-5, relative bias of sum 5e-7 |
| | indirect (2,307 px D2 / 2,332 px D8) | **−95% relative bias of sum**; GPU indirect is exactly 0 on 2,193 / 2,207 reference-positive pixels; reference SE ~3–4e-9 against a mean of 2.2–2.8e-5 |
| | total (2,337 px) | **−30% (D2) / −36% (D8)** relative bias of sum; RMSE 2.3e-5 / 3.0e-5 |
| B3 Sponza light motion (direct proved) | direct (9,546 px) | **agrees to float32:** max relative 2.7e-6 |
| | total | 493 GPU-only positive pixels where the reference is 0; not scored |
| B1 static / B5 deforming (INELIGIBLE) | total | 6,467 / 6,469 GPU-only positive pixels vs 1,034 sparse reference pixels; **not scored** |
| B2 camera (NO_SUPPORT) | total | 8,242 GPU positive pixels against an exactly unlit reference; **not scored** |
| B4 moving rigid (NO_SUPPORT) | total | 9,247 GPU-only positive pixels (result 008); **not scored** |

**Interpretation (diagnostic only; no performance or architecture change):**
- **Direct term:** the Renderer's direct/shadow term is now independently confirmed against a physically validated oracle on the two eligible cells.
- **Indirect term, which errs in both directions:**
  - In the Sponza target states it adds light that has no physical support (light leak).
  - In the eligible `leak-medium` state it misses about 95% of the real one-bounce light on matched pixels.
- **What these results do not establish:** a general quality ranking, a statement about other scenes, GPUs or temporal behaviour, or any revision of the N006 or N007 outcomes.

## Final classification

| Objective (Issue #5) | Outcome |
|---|---|
| Independent, auditable, physically grounded CPU HDR oracle (Phase A) | **GO.** 11/11 analytic controls, 7/7 Mitsuba cross-checks, 5/5 injected defects detected ([004](004-phase-a-exit-decision.md)) |
| Distinguish truly unlit pixels from a broken reference | **Achieved.** B2/B4 are exactly unlit, B1/B5/B6 are sparse and non-converged ([006](006-phase-b-exit-decision.md)) |
| Eligible references for static, camera, light, moving-rigid, deforming, topology-churn and non-Sponza | **Bounded NO GO** for the cross-class set (detailed below) |
| Locked package with fingerprints and GO / NO GO / unsupported / unknown | **Done** ([009](009-phase-c-reference-package.json)). Topology-churn GPU capture: **unsupported** |
| GPU comparison isolating bias and GPU-only light | **Done diagnostically** on attested states (this file and [008](008-phase-c-b4-gpu-diagnostic.md)) |

Detail for the bounded NO GO on the cross-class reference set:
- **Eligible or proved:**
  - non-Sponza static (B7) is eligible;
  - Sponza light-motion is proved for direct only.
- **No usable reference** under the Renderer's current Sponza scene contract:
  - Sponza static, deforming and churn are ineligible;
  - Sponza camera and moving rigid have no support.

**Decision: close N008 as "oracle validated (GO) + cross-class reference set bounded NO GO".** The dark Sponza states are a property of the Renderer's frozen scene contract, as stated in result 006: node transforms are ignored, and the light and eye lie outside the bounds. A relit or reoriented scene would change Renderer behaviour and is **outside this study**. Under the preregistered rules it is a new study, not a rescue.

## Remaining unknowns and limits

- **Visibility semantics:** single-sided back-face handling differs between the Renderer (cull and see through) and the oracle (two-sided reflect). It affects 8.6% of B7 pixels.
- **Transport coverage:** textures, alpha masks and glossy BSDFs are not validated.
- **Scope of measurement:** one GPU, one CPU, and static target poses only; there is no temporal or history evaluation.
- **Topology churn:** the B6 GPU state is not attested.
- **Mechanism of the B7 indirect deficit:** not isolated (for example probe cascade interval, quantisation or owner coverage). This would be a new diagnostic.

## Recommended next studies (separately preregistered)

1. **N009, scene contract:**
   - load Sponza with glTF node transforms and place the light inside the geometry;
   - preregister new cells for all dynamic classes;
   - rerun the unchanged N008 oracle and ladder to obtain a cross-class eligible set.
2. **Probe transport fidelity:** use the N008 oracle on B7 and B4 to attribute the leak (unshadowed secondary hits; see N007) and the B7 indirect deficit to specific pipeline stages, before any GI optimisation.
3. **Back-face semantics:** declare one physical rule for single-sided geometry, shared by the Renderer and the references.
