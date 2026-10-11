# N007 P1-A — CPU-only transport source audit and analytic blocker test

**Status:** completed for static source contracts and a controlled analytic occluder; actual historical PFM causal attribution **not proved**. No user-local commands or new GPU work required for this stage.

## Evidence and audited sources

On 2026-10-12 the assistant fetched **seven actual files** from `research-n007-reference-validity` on GitHub and evaluated ten read-only source checks (10/10 PASS):

| Source | Git blob SHA-1 |
| --- | --- |
| `src/research/lane_n_end_to_end_renderer/CMakeLists.txt` | `ab3df3aaa19dea38a24e50c1bbb32c65b3be5275` |
| `src/research/lane_n_end_to_end_renderer/n001_runtime.cpp` | `3b06c22279446920cc6e337596e05d0e9b4d7bc5` |
| `src/research/lane_n_end_to_end_renderer/n001_reference.cpp` | `53f14855e9ec901cd670489e94ae0cfc33b5fc8a` |
| `shaders/research/lane_n_end_to_end_renderer/n001_physical_radiance.comp.glsl` | `9691a7de585e5a1a3c28f236ac3da4564db32ee0` |
| `shaders/research/lane_n_end_to_end_renderer/n003_composite_software.comp.glsl` | `42288a5f5c33d49fe10f12ea7142f491cdcab01c` |
| `shaders/research/lane_n_end_to_end_renderer/n001_composite.comp.glsl` | `8e4f539cf1466b8a8cc93ed65043b89a323d0788` |
| `shaders/research/lane_n_end_to_end_renderer/imported/integration/i001_radiance.comp.glsl` | `32599531c293f8042f8b2fdf63593e43a4b33ae3` |

### Concrete shader registration, not guessed from filenames

- Runtime `n001_runtime.cpp` loads `i001_radiance.spv` in both primary and reference radiance stages.
- Current CMake `add_compute_shader(i001_radiance shaders/research/lane_n_end_to_end_renderer/n001_physical_radiance.comp.glsl)` **builds that SPIR-V from the physical Lambert GLSL**, not from the imported `i001_radiance.comp.glsl` (which contains a historical deterministic integer-hash payload but is not the current CMake's registered source for that output). The prior suggestion that the old hash payload is an active cause would be incorrect.
- CPU `n001_reference.cpp::direct_lambert` explicitly uses `bvh.trace` for the shadow ray from each bounce hit to the point light; primary rays are always pixel-center and old noise stopping uses the whole-frame p99.
- GPU probe hit `n001_physical_radiance.comp.glsl::point_light_lambert` uses cosine, inverse-distance-like falloff and no shadow-to-point-light trace/query. Its lack of occlusion is an **actual different transport contract** from the CPU reference.
- Both GPU software and HWRT **primary direct-light compositors** use a `visible_to_light` shadow check; software `n003_composite_software.comp.glsl` and HWRT `n001_composite.comp.glsl` then **add the separately accumulated indirect/probe radiance**. The final GPU positive pixel count alone does not reveal which component was positive.

### Independent CPU-only blocker demonstration (8 unittest cases PASS)

Ran a pure-Python analytical Möller–Trumbore shadow-ray example (not an actual Vulkan render or an exact reproduction of full source). Point `(0,0,0)`, normal `(0,1,0)`, point light `(0,2,0)`, falloff radius `0.5`, and triangle occluder at `y=1`. Lambert `cos·r²/(r²+d²)/π` is positive when the light is in the forward hemisphere:

| Synthetic case | With shadow ray | Without shadow ray |
| --- | ---: | ---: |
| Unoccluded | `0.01872411095198769` | `0.01872411095198769` |
| Occluder between point and light | **`0.0`** | **`0.01872411095198769`** |

Other passing synthetic CPU checks: backface receives zero, blockers beyond the light do not shade, off-ray blockers do not shade, two-sided triangle intersection works, correct fixture static source audit passes, and deliberately changed fixture fails closed. All 8 tests pass **inside the assistant sandbox**. The structural GPU/CPU divergence is thus capable of producing reference-zero/GPU-positive radiance under a controlled geometry, with no need for actual GPU execution to establish *possibility*.

**Crucial limitation:** This does **not prove** the original M3b's 10,076 positive Q8 pixels were caused by this divergence, nor physical correctness of the CPU tracer. Reproduction uses small synthetic geometry and scalar Lambert arithmetic, not the original Sponza scene, probe-gather, or GPU backend. Some original N001 states with empty or shadowed CPU ray paths can genuinely be black. Dynamic geometry and primary visibility parity still need matched-state evidence.

## Gate and next steps, prioritized for assistant CPU-only execution

1. Complete source-level component contract and tiny synthetic shadow test: **DONE**. No new N006 parameter fitting, performance claims, original historical source edits, PR or CI.
2. CPU-only review of **existing** archived metadata visible from committed summaries and user-uploaded JSON: already completed for 338/338 named pairs. Not enough original geometry/camera state or direct/indirect split to prove M3b cause.
3. **Future N007-only instrumentation** must split GPU primary hit/direct/indirect and CPU hit/direct/later bounces on identical motion state, then use the existing 4-seed P1 statistical eligibility policy. No extra GPU runs were executed; this is the true remaining blocker.
4. If necessary, compile/run component captures on the user GPU **only after implementation and a bounded manifest are ready**; do not ask the user to repeat already-completed CPU work, and do not promise background execution.

**N006 historical `invalid-retained` / final NO GO remain unchanged. N007 not complete; P1 physical correctness not established.**
