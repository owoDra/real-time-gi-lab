# N007 P1-A: matched-state CPU/GPU component capture

**Classification: diagnostic-only. GPU path NOT yet compiled or executed.**

## Scope

- Original N001/N006 shaders, renderers, reference code and historical decisions remain unchanged.
- N007's CPU module uses the imported original SoftwareBvh, center-primary camera rays, per-sample splitmix64 secondary sampling, eight Lambert bounces and source-compatible shadow offsets.
- Per seed (four preregistered seeds): direct-first-bounce, secondary bounce, total float32 RGB PFM; primary hit IDs, t and geometric normal; shadow-tested, blocked, clear, secondary and positive sample counts.
- N007 shader generator copies original HWRT/software composite sources and replaces only the result encoding. Diagnostic GPU RGBA channels encode direct, probe indirect, total, alpha=1. The generated N007-only runtime additionally reads back the existing primary-hit SSBO. Original source files are never overwritten.
- The analyzer verifies hashes, dimensions, nonfinite/negative values, primary masks/IDs/t/normals, component reconstruction (float32 tolerance), full-frame RMS and explicit attribution blockers. A 1e-5 direct term triage tolerance is **not** the N007 frozen convergence threshold.

## Opt-in GPU build and one preregistered diagnostic capture

GPU host only, on a clean checkout; retain all outputs privately in the ignored out/ directory. The capture executable also performs the CPU reference sampling; no separate user CPU jobs are required.

~~~bash
scene=assets/Vulkan-Samples-Assets/scenes/sponza/Sponza01.gltf
commit=$(git rev-parse HEAD)
cmake -S . -B build/n007 -DCMAKE_BUILD_TYPE=Release -DPHOS_BUILD_N007=ON
cmake --build build/n007 --target phos-n007-capture
bash scripts/run_with_vulkan.sh build/n007/phos-n007-capture \
  --scene "$scene" --scenario moving-rigid --backend software \
  --target-state --spp 512 \
  --out out/research/n007-reference-validity/p1a/moving-rigid-512
python scripts/research/n007_reference_validity/build_component_manifest.py \
  --capture out/research/n007-reference-validity/p1a/moving-rigid-512 \
  --scene "$scene" --repo . --source-commit "$commit"
~~~

## Frozen follow-up

A1 cells: one black moving-rigid, one black camera/disocclusion, positive light-motion and a deterministic controlled occlusion fixture. No post-hoc frame selection. A2 ladder: SPP 512,1024,2048,4096,8192; four seed IDs 305419896,2596069104,81985529216486895,18364758544493064720, with two consecutive eligible levels. Existing N007 eligibility protocol is authoritative; the component analyzer **does not determine statistical convergence**.

## Evidence limits

- CPU raw post-motion geometry + parameter fingerprints do not alone prove uploaded GPU buffers match. Validate GPU primary-hit identities before attributing indirect-light differences.
- A GPU-positive/CPU-black image is not automatically light leakage, and CPU blackness is not physical truth.
- The CPU and probe estimators differ; their disagreement is a diagnostic hypothesis, not proof of which is correct.
- Software/HWRT integrated GPU compilation and runtime not performed in the assistant sandbox; GLSL compiler/Vulkan hardware unavailable there.
- The independent controlled-occluder scene's GPU asset is not automated yet. Original archived private PFMs were not present and are not published.
- GPU output from the packed diagnostic shader **must not** be treated as an unchanged original RGB radiance image for formal N001/N006 acceptance.

See research/lanes/n007-reference-validity/experiments/002-matched-state-component-isolation.md and 001-reference-eligibility-protocol.md.
