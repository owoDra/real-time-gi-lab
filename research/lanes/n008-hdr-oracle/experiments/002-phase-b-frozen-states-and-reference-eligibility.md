# N008 Phase B — frozen Renderer scene states and reference statistical eligibility (preregistration)

**Status:** PREREGISTERED 2026-10-13, after Phase A Exit A = GO ([result 004](../results/004-phase-a-exit-decision.md)) and **before any oracle image of any Phase B cell was rendered or inspected**. One timing pilot was run on a non-cell camera (static geometry, eye shifted +150 along x, 16 spp, 1 seed). Only its wall time was read, and its images were deleted unexamined. No Renderer/candidate image is produced or used in Phase B.

## Frozen cells (no substitution, no favourable-frame selection)

States are the Renderer's own **target** frame states. They are produced on CPU by `n008_state_export`, which compiles **verbatim-extracted** Renderer code:
- `generate_state_exporter.py` extracts it from `n001_runtime.cpp` (SHA-256 `75492142…8850`) and `a001_runtime.cpp` (`482af7cc…6a89`).
- It also asserts the N002 churn lines in `n002_runtime.cpp` (`f5cb699b…3ced`).
- The Renderer's own `a001_scene.cpp` / `b002_scene.cpp` loaders are compiled in.

The output uses the N007 state format.

**GPU attestation already available:** the exporter's moving-rigid output is **byte-identical** to the GPU-run N007 capture (`out/…/n007-reference-validity/p1a/probe-shadow-dabe590b0c6e`, private):
- frame `77e1d952…b8b4`
- geometry `d70e8344…d53d`

N007 result 009 verified that this geometry equals the GPU device primary triangle buffer. The other cells use the same extracted code path but have not been GPU-read back.

| Cell | Class | Scene asset SHA-256 | frame-state SHA-256 | geometry-state SHA-256 |
|---|---|---|---|---|
| B1 | static | Sponza01.gltf `2a86fdc2…e5f6` | `77e1d952988d70367557c36755261a2a4eefa49177541f5e0a8a99478a24b8b4` | `205c5a6085e555981080b6547ee6b492e387890e9988ee153d22b4096409b801` |
| B2 | camera motion / disocclusion target pose (orbit 0.35 rad) | same | `a3493146e8e11498c3abc5c98ceaed165032a415ddefc4b3308e1f0a5bca46b5` | `205c5a60…b801` |
| B3 | light motion target | same | `8f426ee617c07f9c5c026db3725ea21b07dd28059af14bc36616f7e16c15afcd` | `205c5a60…b801` |
| B4 | moving rigid target (instance 5, 796 tris, +362.264 x) | same | `77e1d952…b8b4` | `d70e8344d9ea493b6fa48d918a2f17f118030b91d708d8bb8d78d0f0422fd53d` |
| B5 | stable-topology deforming target (A = 23.1849) | same | `77e1d952…b8b4` | `937836c47638066d1107aecf3e634644910437badf666242e32f32c425745364` |
| B6 | topology change / high churn (398 of 796 replaced, new ids) | same | `77e1d952…b8b4` | `1a5770d411c18111978567919b350aed3ee14921b0a7c2e7b23608017810ea16` |
| B7 | non-Sponza: N004 `leak-medium` (factory v4) static | gltf `1533aade…09bc`, bin `5f7c60b4…1169` | `64e5bae27e1719d66b4daef559f52309878ffcc6bcc72920c8cad7115df9c949` | `945b99545ca9f24c5261f1eccec6eb68ce697169bfb052ffbfba87dca02a2c5b` |

**Camera / disocclusion scope:** a static reference image is a function of the frozen target pose only. Disocclusion is a temporal property of the Renderer's history, so B2 is the reference for both camera motion and camera disocclusion. The Renderer's temporal behaviour is out of scope for the reference, as Issue #5 allows.

**Pre-acquisition state facts (computed from state bytes, not from images):**
- Sponza is loaded from raw mesh POSITION data **without glTF node transforms**. The 25 nodes with a +90° X rotation are ignored.
- The geometry bounds are x [−1920.9, 1799.9], y [−1182.8, 1105.4], z [−1429.4, 126.4].
- The B1 light (634.4, 1582.8, −186.5) and the B1 eye (2559.6, 799.7, 1970.3) both lie **outside** these bounds.

These facts are recorded now so that the outcome cannot be rationalised afterwards.

## Reference transport T_B (declared; all modes validated in Phase A)

The scene and camera are taken from the state bytes as follows:

| Element | Setting |
|---|---|
| Camera | pinhole from the params: eye, forward, up, `tan_x`, `tan_y`, far = `camera_forward_far.w`, near 0 |
| Primary sampling | **pixel centre** (the Renderer's primary rule) |
| Image | 320×180 |
| Light | isotropic point light at `light_pos_interval.xyz`, `falloff n001_soft s` with `s = light_pos_interval.w`, intensity `I = s²` (grey). For ρ = 1 the direct term equals the Renderer formula `cos·s²/(s²+d²)/π` exactly. |
| Material | grey Lambert **ρ = 1**, the albedo implied by the Renderer's direct formula and the lossless physical limit. **Two-sided** reflection for every triangle (opaque physical surfaces). Single-sided glTF flags are not treated as see-through. |
| Background | black |
| Secondary rays | unbounded secondary/shadow rays |

- **T_B2, primary reference:** `max_bounces 2` (direct plus exactly one shadowed diffuse bounce, the transport order the Renderer's GI targets).
- **T_B8, secondary reference:** `max_bounces 8`, everything else identical. Reported with the same ladder; it is not required for Exit B.

**Diagnostic, not a gate:** the oracle hit sidecar reports the fraction of pixel-centre primary hits that land on the **back face of a single-sided triangle**. The Renderer culls those faces and sees through them, so Phase C must flag such pixels.

## Ladder, seeds and statistics

- Seeds: the four fixed N007 seeds `305419896, 2596069104, 81985529216486895, 18364758544493064720`.
- **Nested-prefix ladder:** 512 → 1024 → 2048 → 4096 → 8192 spp from one 8192-spp run per seed, checkpointed. Level k uses samples `[0, spp_k)`, so consecutive levels are correlated by construction (disclosed). Checkpoint bytes equal separate renders (verified).
- Per level and cell, record:
  - total/direct/indirect union-active support;
  - per-seed peak and mean luminance (Rec.709 Y);
  - pairwise RGB RMS and pairwise active-mask p99 absolute and relative error (floor `max(1e-4, mean |Y|)`);
  - zero↔positive pixel transitions between levels;
  - per-pixel SE, and the hit-sidecar diagnostics.

## Eligibility (N007 screen thresholds **unchanged**; N008 additions preregistered here)

1. **STATISTICALLY_ELIGIBLE (total, T_B2):** at two consecutive levels, the N007 screen must pass:
   - ≥4 seeds;
   - union-active ≥ 64 px **and** ≥ 1%;
   - peak Y ≥ 1e-4;
   - pairwise image inequality;
   - every pair: active p99 abs ≤ 1e-5 and relative ≤ 5%;
   - union-active fraction change between the two levels ≤ 10%.
   
   Checking stops at the first qualifying pair. All levels are still rendered (cost is fixed), but later levels are reported as unused.
2. **DIRECT_DETERMINISTIC_PROVED (N008 addition):** with pixel-centre sampling and a point light, the direct term is deterministic, so it does not need a stochastic noise screen. It qualifies if:
   - all four seeds' direct sidecars are byte-identical at 8192 spp;
   - the direct support passes the same signal thresholds (≥ 64 px, ≥ 1%, peak Y ≥ 1e-4).
   
   This qualifies **only the direct component**, never the total.
3. **NO_SUPPORT (ineligible, physically dark within T_B):** applies if direct is exactly zero at every pixel **and** total union-active fails the support thresholds at 8192 spp. Within the Phase-A-validated transport this is classified as "unlit at the target state". It is **not** a broken estimator, and it **must never be used to score a candidate**.
4. **INELIGIBLE:** any other failure, retained with all metrics.

**Stop rules:**
- Cap at 8192 spp × 4 seeds per cell and transport.
- No extra levels, seed changes, frame or camera substitutions, light repositioning, or "fixed" scene orientation inside Phase B.
- A dark or ineligible outcome is a valid result.
- A corrected-orientation or relit scene would be a **new, separately preregistered cell**, not a rescue.

## Preconditions before acquisition

The oracle source changed after the Phase A freeze, adding the hit sidecar and checkpoint output with no transport change. Before acquisition:
- C++ unit tests must pass;
- the checkpoint bit-equality check must pass;
- the full Phase A control and cross-check suites must re-pass at the acquisition commit.

The acquisition runs from one clean committed SHA.

**Exit B:**
- Every cell B1–B7 has a final classification under T_B2.
- At least one cell is STATISTICALLY_ELIGIBLE or DIRECT_DETERMINISTIC_PROVED with nontrivial support. Otherwise the outcome is a bounded **NO GO**, with each cell's NO_SUPPORT/INELIGIBLE evidence retained.
- Candidates are never scored against NO_SUPPORT cells.
