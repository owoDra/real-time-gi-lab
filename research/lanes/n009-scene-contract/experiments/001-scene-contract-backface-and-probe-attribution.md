# N009 — scene contract C1, back-face rule BF-P, and probe-transport attribution (preregistration)

**Status:** PREREGISTERED 2026-10-13, before any N009 contract selection, oracle indirect/total image, GPU capture or probe-ladder comparison with a reference.

**Origin:** the three follow-ups recommended by [N008 result 011](../../n008-hdr-oracle/results/011-n008-final-decision.md):
1. a scene-contract study (glTF node transforms, interior light) that reruns the **unchanged** N008 oracle and ladder;
2. attribution of the Renderer's probe-indirect errors (leak and B7 deficit) to pipeline stages;
3. one physical back-face rule shared by the Renderer and the references.

**Base:** branch `research-n009-scene-contract`, from `research-n008-hdr-oracle` @ `12f4846` (N008 is not yet integrated into `research`; this ancestry is deliberate and recorded).

**Disclosed activity before this preregistration (development checks only):**
- builds of the three new N009 targets;
- `n009_state_export` on Sponza without a contract file, which correctly fails closed;
- `n009_state_export` on N004 `leak-medium`: frame-state bytes identical to N008 B7 (`64e5bae2…c949`), vertices and ids identical, only the sided flag changed 0→1 (BF-P);
- `n009_probe_model` smoke run on the existing N008 B7 software capture. Only its counter JSON and the R0-vs-GPU replay equality were read (max abs 2.5e-14, 0 positivity disagreements). No stage image was compared with any reference.

## Frozen inputs

| Item | SHA-256 |
|---|---|
| Oracle `n008_oracle.hpp` / `n008_oracle_main.cpp` (unchanged since N008) | `dc47c4e1…ba4c` / `53c597bb…ec03` |
| N008 ladder `phase_b_ladder.py` / GPU diagnostic `phase_c_gpu_diagnostic.py` (unchanged) | `d0b559e8…5c98` / `ebcc70cf…d79b` |
| N007 screen `check_convergence.py` (unchanged) | `8a5dec13…3d52` |
| Sponza01.gltf / .bin | `2a86fdc2…e5f6` / `8abc659b…cd1b` |

Pinned Renderer sources are never edited. All N009 behaviour is an **opt-in generated overlay** (`PHOS_BUILD_N009`, default OFF; `scripts/research/n009_scene_contract/generate_overlay.py`, exact-once replacements that fail on drift).

## WP-BF — back-face rule (Issue item 3)

**Audit of the current Renderer (source facts):**

| Ray type | Single-sided triangle seen from the back |
|---|---|
| Camera primary (`n001_primary`, `n003_primary_software`) | culled: the ray passes through |
| Probe secondary (`i001_hwrt`, `e003_instance_*`) | culled: the ray passes through |
| Direct shadow (`n001_composite` any-candidate, `n003_composite_software` `abs(det)`) | **blocks** (two-sided) |
| Shading at any hit | normal flipped toward the incoming ray (two-sided Lambert) |

The Renderer is therefore internally inconsistent: the same surface blocks light toward a point but is invisible to the camera and to probe rays from that side.

**Declared rule BF-P:** every triangle is an opaque, two-sided Lambert surface for **every** ray type (camera, shadow, probe/secondary, reference path). The glTF `doubleSided` flag does not change transport or visibility.

Rationale:
- a one-way surface violates reciprocity, so no physically consistent culling rule exists for transport;
- it is the convention of physically based offline renderers (pbrt, Mitsuba, Cycles), where geometry occludes from both sides;
- it equals the N008 reference transport T_B (two-sided), so N008's validated references remain valid.

**Declared deviation:** glTF 2.0 specifies back-face culling of single-sided materials for rasterised visibility; BF-P renders those back faces. This is recorded as a conformance limitation, not hidden.

**Implementation:** the N009 B002 loader sets `two_sided = true` for every triangle, so every existing traversal shader takes its unchanged two-sided branch. No shader is edited.

**Gates (on GPU captures):**
- **BF1:** every captured geometry state has sided = 1 for all triangles; the state bytes equal the CPU export (GPU-attested).
- **BF2:** on C7 (`leak-medium`, the N008 cell with 4,978 back-face mismatches), primary-visibility mismatches (mask or primitive) between GPU and oracle are ≤ 0.1% of pixels for both backends.
- **BF3:** on C7, the GPU direct term on all matched pixels, including the former back-face pixels, agrees with the N008 B7 locked reference to max relative error ≤ 1e-4.

## WP-SC — scene contract C1 and cross-class references (Issue item 1)

**Contract C1** (applies to a glTF scene with an authored camera; scenes without one, such as `leak-medium`, keep the A001 camera/light formula):
- **Geometry:** mesh POSITION data transformed by the glTF node world matrix of the default scene (fastgltf `iterateSceneNodes`); every mesh must be instanced exactly once (fail-closed). Primitive and instance identities are unchanged.
- **Camera:** the first authored camera node: eye = node translation, basis = node rotation (right = +X, up = +Y, forward = −Z), vertical FOV = authored `yfov`, aspect = 320/180. Near/far keep the A001 formulas.
- **Light:** one point light with the unchanged Renderer radiometry (`n001_soft`, s = A001 diag/128). Its position is chosen by the preregistered geometry/direct-only procedure below.
- **Probe spacing, light interval scale, limits:** unchanged A001 formulas over the transformed bounds.
- **BF-P:** as above.

**Preregistered selection** (`select_contract.py`; reads geometry and the deterministic oracle **direct** term only, never an indirect/total, GPU or quality image):
1. Light candidates, in order, as fractions (x, y, z) of the C1 world vertex bounds: L1 (0.5, 0.5, 0.5), L2 (0.5, 0.35, 0.5), L3 (0.75, 0.5, 0.5), L4 (0.25, 0.5, 0.5), L5 (0.5, 0.65, 0.5), L6 (0.75, 0.35, 0.5), L7 (0.25, 0.35, 0.5).
2. **G-L1 free space:** minimum distance from the light to any triangle ≥ 2s.
3. **G-L2 direct support:** oracle direct only, pixel centre, deterministic: ≥ 64 px, ≥ 1% of pixels, peak Y ≥ 1e-4.
4. **Base light** = first candidate passing both gates. **Light-motion light** = next passing candidate at distance ≥ 0.1·diag from the base.
5. **Camera-motion offset:** candidates +right, −right, +forward, −forward, each of length 0.02·diag; **G-C1:** minimum distance from the moved eye to any triangle ≥ 2s; the first passing offset is used.
6. If no light or offset passes: WP-SC stops as **NO GO (contract unattainable)**; no new candidates are added.

**State lock (before any reference image):** after selection, the states of cells C1–C6 are exported with `n009_state_export`, and their SHA-256 values are committed together with the contract file and the selection record. No oracle indirect/total image is rendered before that commit.

**Cells:**

| Cell | Class | State |
|---|---|---|
| C1 | static | Sponza C1, base camera and light |
| C2 | camera motion / disocclusion target pose | camera + selected offset |
| C3 | light motion | light-motion light |
| C4 | moving rigid | Renderer `choose_moving_selection` on the C1 geometry (verbatim extracted) |
| C5 | stable-topology deforming | Renderer `choose_deforming_selection` |
| C6 | topology churn | N002 churn re-statement (as N008); **GPU capture unsupported**, oracle-only |
| C7 | non-Sponza `leak-medium` under BF-P | N008 B7 frame bytes; geometry differs from N008 only in the sided flag |

**Reference transport and ladder:** identical to N008 Phase B: T_B2 (primary) and T_B8; four N007 seeds; nested 512–8192 spp; the unchanged N007 screen; the unchanged N008 classifier (`phase_b_ladder.analyze_cell`), invoked with N009 cell tables. Classifications: STATISTICALLY_ELIGIBLE, DIRECT_DETERMINISTIC_PROVED, NO_SUPPORT, INELIGIBLE, with the same definitions and stop rules (cap 8192 spp × 4 seeds; no relighting, re-posing or extra levels after the lock).

C7 is not re-rendered: its reference is the locked N008 B7 reference, valid under BF-P because T_B was already two-sided and the oracle geometry hash (vertices + material) is unchanged. The equivalence is verified mechanically: identical frame bytes, identical vertices and ids, sided flags all 1.

**GPU captures (assistant-run, authorised by the user):** `phos-n009-capture --target-state --spp 512`, both backends, for C1–C5 and C7 (12 captures; RADV 8060S only; no clock/power forcing). The capture state bytes must equal the locked states; otherwise the capture is not compared.

**Exit SC:**
- **GO (cross-class):** every Sponza cell C1–C5 is STATISTICALLY_ELIGIBLE for the T_B2 total; C6 has a final oracle-only classification; C1–C5 are GPU byte-attested.
- **Bounded GO:** at least one of C1–C5 is eligible; the others are reported with their classifications.
- **NO GO:** none of C1–C5 is eligible.

**Diagnostic GPU comparison** (not a ranking): `phase_c_gpu_diagnostic.compare`, unchanged, on attested captures. Components are scored only where the reference class allows it (as in N008).

## WP-PT — probe-transport attribution (Issue item 2)

**Tool:** `n009_probe_model` (CPU only; geometry, intersection and RNG from the unchanged N008 oracle header). For one attested GPU capture it builds a counterfactual ladder of the Renderer's probe-indirect estimator. Each stage changes exactly one factor, in this fixed order:

| Stage | Change relative to the previous stage |
|---|---|
| R0 | exact integer replay of the GPU probe aggregation (owner outputs, per-output rounded mean, per-key mean, sum over cascades) |
| R1 | no 16-bit quantisation: float per-ray values recomputed from the GPU secondary hits |
| R2 | add a shadow ray at each secondary hit (oracle BVH, two-sided; offset 1e-5·diag along the facing normal) |
| R3 | full probe coverage: every probe key a visible pixel looks up is evaluated (CPU-traced, same 8 directions, intervals and probe centres), not only keys produced by tile-owner surfaces |
| R4 | last cascade interval unbounded (removes the 8s range truncation) |
| R5 | 256 dense Fibonacci directions instead of the 8 cube diagonals |
| R6 | pixel-centred, cosine-weighted, unbounded, shadowed one-bounce estimator at the GPU primary hit (1024 samples per pixel), i.e. the oracle's definition |

**Validation gates (per capture; failing any one makes that capture's attribution INCOMPLETE):**
- **V1:** R0 equals the GPU indirect image: max abs ≤ 1e-6 and 0 positivity disagreements.
- **V2:** quantisation check: the recomputed value re-quantised equals the captured contribution (exact or ±1 LSB) for ≥ 99.9% of work items.
- **V3:** CPU re-trace of each GPU secondary ray matches the GPU hit (both miss, or |Δt| ≤ 1e-3·max(1, t)) for ≥ 99% of work items.
- **V4 (closure; eligible-indirect cells only):** R6 vs the locked T_B2 indirect reference on the scoring mask: |relative bias of the sum| ≤ 3%.

**Metrics per stage (luma, scoring mask = matched primary visibility as in N008 Phase C):**
- relative bias of the sum against the T_B2 indirect reference;
- RMSE;
- number of reference-positive pixels where the stage is 0;
- stage energy on reference-zero pixels (GPU-only light).

**Attribution** = the change in each metric between consecutive stages. The decomposition is order-dependent; the order is fixed here and not changed after seeing data.

**Captures analysed:**
- C7 (software and hwrt): the indirect deficit (eligible indirect reference);
- every C1–C5 capture whose T_B2 class is STATISTICALLY_ELIGIBLE (deficit and/or leak);
- the existing N008 B4 moving-rigid capture: R0–R2 only, as an independent-BVH replication of the N007 leak mechanism. Its CPU re-trace (R3+) is not used, because that capture predates BF-P.

**Exit PT:** attribution is **COMPLETE** for a capture when V1–V4 pass (V4 only where an eligible indirect reference exists). The dominant factor of a capture is the stage transition with the largest absolute change in relative bias of the sum. Any failed gate is reported as INCOMPLETE; tolerances are not relaxed.

## Not claimed, whatever the outcome

- No change to N001–N008 results, sources or classifications; the default Renderer is unchanged.
- No adoption of C1 or BF-P as the default Renderer contract: that is a separate architecture decision.
- No quality ranking, multi-GPU or temporal claim; no fix of the probe estimator (diagnosis only).
- Textures, alpha masks and glossy BSDFs remain unvalidated.
