# N007 P1-A: matched-state CPU/GPU component capture

**Classification: diagnostic-only. GPU host has executed the initial capture; first-hit matching failed. N007-only world-space fix is committed but GPU revalidation remains pending.**

## Scope

- Original N001/N006 shaders, renderers, reference code and historical decisions remain unchanged.
- N007's CPU module uses the imported original SoftwareBvh, center-primary camera rays, per-sample splitmix64 secondary sampling, eight Lambert bounces and source-compatible shadow offsets.
- Per seed (four preregistered seeds): direct-first-bounce, secondary bounce, total float32 RGB PFM; primary hit IDs, t and geometric normal; shadow-tested, blocked, clear, secondary and positive sample counts.
- N007 shader generator copies original HWRT/software composite sources and replaces only the result encoding. Diagnostic GPU RGBA channels encode direct, probe indirect, total, alpha=1. The generated N007-only runtime additionally reads back the existing primary-hit SSBO. Original source files are never overwritten.
- The analyzer verifies hashes, dimensions, nonfinite/negative values, primary masks/IDs/t/normals, component reconstruction (float32 tolerance), full-frame RMS and explicit attribution blockers. A 1e-5 direct term triage tolerance is **not** the N007 frozen convergence threshold.
- For the software backend, the generated runtime additionally downloads the *actual GPU primary triangle buffer* (`gpu/primary-geometry.bin`); the manifest compares all 64-byte std430 triangles against the serialized post-update CPU world-space geometry (52 bytes/triangle), detecting any upload mismatch independently. Primary geometry equality alone is not GPU camera UBO or physical correctness certification. Output now includes CPU/GPU hit coverage and positive signal pixel counts to detect black-versus-black comparisons.

## Opt-in GPU build and one preregistered diagnostic capture

GPU host only, on a clean checkout; retain all outputs privately in the ignored out/ directory. The capture executable also performs the CPU reference sampling; no separate user CPU jobs are required.

The scene asset is intentionally absent from Git (ignored `assets/`); fetch it
once with the existing repository helper. Check for both the glTF and the binary
buffer before running the diagnostic capture. This download is needed only on
the GPU host; the CPU logic is executed by `phos-n007-capture`.

~~~bash
bash scripts/fetch_sponza.sh
test -f assets/Vulkan-Samples-Assets/scenes/sponza/Sponza01.gltf
test -f assets/Vulkan-Samples-Assets/scenes/sponza/Sponza01.bin
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

## Current measured frame and next source-level isolation

On the user's Vulkan host, the corrected software moving-rigid target frame returned:
CPU/GPU primary-hit count 15,173 each; all primary mismatch types zero;
262,241 GPU software-primary triangles exactly match serialized CPU triangles.
GPU packing reconstructs correctly. CPU direct, indirect and total are all
black; GPU direct is black while GPU indirect/total have 9,247 positive pixels.
See [result 009](../../../research/lanes/n007-reference-validity/results/009-p1a-matched-primary-indirect-isolation.md).
This **does not prove original N006 M3b physical causation**.

The original `n001_physical_radiance.comp.glsl` emits per-probe point-light
Lambert energy without a shadow-to-light test, unlike the CPU path tracer.
To test this specific hypothesis without altering any historical shader,
the NEW capture also records exact GPU probe work (64 bytes/item), traversal
hits (32 bytes/item), and fixed radiance contributions (8 bytes/item).
A N007 CPU replay checks those real GPU rays against a separate BVH,
reconstructs unshadowed contribution quantization, and tests
source-geometry shadow rays. Its result `gpu_probe_shadow_audit` distinguishes
verified blocked-positive hits from clear hits and traversal/model mismatches.
`gpu_probe_shadowed_positive_detected=true` is a **current-frame diagnostic**
only, never historical/physical correctness proof.

CPU-only opt-in deterministic shadow fixture target:
`cmake --build build/n007 --target phos-n007-probe-test`.
This fixture has been added but **not compiled in the assistant sandbox**;
only GPU-host execution can validate this integrated build path.

## CPU-only P1-B replay and statistical eligibility (new, not measured)

The 2026-10-12 GPU probe replay directly observed **18,363/18,649**
positive sample contributions at independently shadow-blocked secondary
surfaces. First-hit pixels and device primary triangles match CPU geometry.
The result remains `diagnostic-only`; **neither final-pixel attribution nor
historical M3b causation nor unbiased physical accuracy is proved**.

For the **existing private** `--capture` directory from that successful
GPU probe audit, the following CPU-only workflow needs no Vulkan runtime,
extra GPU capture, or new scene assets. It must execute where the original
ignored output files are available. It never overwrites original PFM data.

~~~bash
git pull --ff-only
cmake --build build/n007 --target \
  phos-n007-probe-offline phos-n007-cpu-reference \
  phos-n007-probe-test phos-n007-cpu-test -j 6

python scripts/research/n007_reference_validity/run_p1b_cpu.py \
  --capture "$out" --bin-dir build/n007
~~~

Keep `$out` pointing to the *existing* capture with 18,363 shadow-blocked
positive probe work items (NOT the new branch commit's output directory).
The CPU one-command runner checks the independent lit/blocked fixtures,
derives an explicit per-work shadow flag file from real GPU work/hits,
reconstructs original GPU probe-to-image output before counterfactual
filtering, and runs the frozen four-seed `512..8192` statistical
eligibility ladder. Capture provenance and raw geometry/state are reused.
Early stop is allowed **only** for two consecutive eligible levels; otherwise
all five SPP levels are assessed. The CPU workload is substantial, especially
at 8192 SPP. The script can resume a partial ladder without redoing completed
levels; the resulting files remain private under the capture output.

If the original probe-image replay fails, this is an independently recorded
`baseline_reconstruction_passed=false` blocker, **not** a cause attribution.
Statistical screening runs separately. New tests and runner have **not been
executed** against the private real capture or integrated native build in
this session. Refer to
[readiness result 010](../../../research/lanes/n007-reference-validity/results/010-p1b-reference-screen-readiness.md).

## Frozen follow-up

A1 cells: one black moving-rigid, one black camera/disocclusion, positive light-motion and a deterministic controlled occlusion fixture. No post-hoc frame selection. A2 ladder: SPP 512,1024,2048,4096,8192; four seed IDs 305419896,2596069104,81985529216486895,18364758544493064720, with two consecutive eligible levels. Existing N007 eligibility protocol is authoritative; the component analyzer **does not determine statistical convergence**.

## Evidence limits

- CPU raw post-motion geometry + parameter fingerprints do not alone prove uploaded GPU buffers match. Validate GPU primary-hit identities before attributing indirect-light differences.
- A GPU-positive/CPU-black image is not automatically light leakage, and CPU blackness is not physical truth.
- The CPU and probe estimators differ; their disagreement is a diagnostic hypothesis, not proof of which is correct.
- Initial software GPU capture and component packing succeeded on the user's Vulkan host, but primary masks/identities did not match. A double-translation defect in N007's generated target-state first-hit BVH upload was identified and corrected; post-fix GPU result is pending. HWRT still unverified; GPU execution remains unavailable in the assistant sandbox.
- The independent controlled-occluder scene's GPU asset is not automated yet. Original archived private PFMs were not present and are not published.
- GPU output from the packed diagnostic shader **must not** be treated as an unchanged original RGB radiance image for formal N001/N006 acceptance.

See research/lanes/n007-reference-validity/experiments/002-matched-state-component-isolation.md and 001-reference-eligibility-protocol.md.
