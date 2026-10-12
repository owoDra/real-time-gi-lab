# N007 P1-A-008 — matched-state component instrumentation bring-up

**Date:** 2026-10-12 JST
**Status:** partial / **evidence: diagnostic-only**
**Study:** Issue #4; experiment 002 (preregistered matched-state component isolation)
**Starting verified Git SHA:** `f962a659c2f042897e663396f576546f7266d97e`
**Branch:** `research-n007-reference-validity` (no PR/CI, no main merge)
**Target hardware:** AMD Radeon 8060S (RADV STRIX_HALO), NixOS 26.05, **NOT RUN**
**Archived M3b GPU/CPU PFM files:** not available in assistant sandbox; none uploaded.

## Implemented, without rewriting historical renderers

1. N007-only CPU reference in `src/research/n007_reference_validity/n007_cpu_components.hpp`. Uses existing SoftwareBvh traversal/camera center rays and RNG contract; records first hit IDs/t/geometric normal, direct, indirect, total, and shadow/secondary sample counters. Four per-seed linear float32 PFM outputs for each selected SPP, with fixed seed IDs `305419896,2596069104,81985529216486895,18364758544493064720`.
2. `generate_capture.py` builds fail-closed *diagnostic-only generated copies* of existing HWRT/software composite shaders and N001 runtime. Output fields in GPU RGBA become `direct, probe indirect, direct+indirect, 1`; existing primary-hit SSBO is privately read back without modifying N001 sources.
3. `phos-n007-capture` captures a selected matched frame including raw CPU post-motion triangle/camera state, GPU first hits, GPU stage images, CPU per-seed and pooled stage images, shadow counts. New CMake flag `PHOS_BUILD_N007` defaults **OFF**, so accepted default build/targets are untouched.
4. `build_component_manifest.py` creates source/scene/raw-frame state and artifact SHA fingerprints (private captures stay under ignored `out/`); `component_contract.py` performs fail-closed primary mask/identity/t/normal comparison, per-component RGB RMS, float32 GPU reconstruction, shadow counter checks and attribution guards.

## Actually performed validation, not extrapolated to GPU

- GitHub repository and actual branch SHA read via linked GitHub connection; N007 source-contract anchors checked: **9/9 PASS**. Source-level check only, not compilation.
- Local Python synthetic component and overlay generator tests: **14/14 PASS**, executed in the assistant sandbox using equivalent local work-tree files. Covers tampered SHA, malformed state/seed, primary mismatch, indirect-only difference and packing reconstruction.
- Local C++ reference controlled scene test: **compiled with Clang C++20 -Wall -Wextra -Wpedantic -Werror** and executed: **PASS**, covering hit/miss, valid primitive ID/t, direct/indirect sum, shadow counter invariants and invalid dimensions. Original imported BVH headers used as manually mirrored local copies; this is **not** an integrated repo-wide build test.
- **Full CMake/link build:** NOT RUN (sandbox lacks network access needed for pinned build deps). **SPIR-V compile:** NOT RUN (no installed GLSL compiler). **GPU runtime:** NOT RUN (required Radeon Vulkan host unavailable). **Original PFM replay:** NOT RUN (private artifacts unavailable).

## Cause and eligibility classifications

- **Historical M3b discrepancy:** cause **unknown**, not proven due to GPU probe shadow omission; no new real-state matched capture yet.
- **A1 phase:** instrumentation prepared, end-to-end on-device capture **not validated**, independent occluder GPU fixture **not implemented**.
- **A2 statistical eligibility:** NOT RUN. The component comparator does *not* replace frozen N007 SPP/4-seed/two-consecutive-level convergence protocol.
- **Physical validity:** unknown. CPU black is not automatically correct, GPU-positive not automatically light leak, and probe vs path-traced secondaries are different estimators.
- **Historical N006 P1 NO GO and M3b invalid-retained remain unchanged**; no architectural promotion permitted.

## Remaining bounded steps

1. Build opt-in N007 capture target on Vulkan host, fix any uncovered compile/descriptor/runtime errors without modifying accepted N001/N006 source.
2. Freeze representative moving-rigid, camera, positive light-motion and deterministic occluded state. Capture matched-state decompositions and verify readbacks/scene fingerprints, first-hit match and GPU sum consistency. Record HWRT/software behaviors separately.
3. Use the unchanged preregistered 512–8192 SPP × 4 seed convergence ladder to classify statistical eligibility (two consecutive passing stages); only then distinguish convergence from physical correctness.

**User CPU run requests:** none; only unavoidable GPU host operations remain. No private raw artifact has been sent to GitHub.

## GPU-host bring-up evidence received (2026-10-12 JST)

- User ran `phos-n007-capture` successfully on the GPU host: `N007 component capture saved; historical causation not proven.`
- `build_component_manifest.py` completed with `classification=diagnostic-only`, `primary_match=false`, `gpu_reconstruction_passed=true`, `historical_causation_proven=false`.
- These facts establish GPU execution and internal packed-shader reconstruction on **one moving-rigid / software / target-state / 512-SPP** capture, **not** matching-state eligibility, correct physics or N006 historical cause.
- Source-level cause isolated: historical N006 calls `n006_refresh_software_primary()` after target-state geometry update, but N007's generated N001 runtime omitted it. Therefore the GPU first-hit BVH could remain source-state while CPU traces post-motion `renderer_readback().triangles`. This is a **strong instrumentation defect hypothesis**, not an empirically verified explanation until rerun.
- N007-only generator patched to call refresh in target-state software path, and updated the synthetic regression guard. The manifest CLI now prints primary mismatch categories and component absolute deltas. No N001–N006 source touched; the patched GPU path is **NOT yet run**. No raw PFM, detailed mismatch counts or state fingerprints uploaded; a retroactive factual cause conclusion is not warranted.
