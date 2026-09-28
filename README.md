# phos-gi-lab

Vulkan research sandbox for testing whether a **page-local surface radiance cache** can beat hash-based world-space caches on real GPU memory behavior before implementing a full GI system.

The project intentionally starts with a cache microbenchmark instead of a renderer. The central claim is about memory locality, so the first experiment isolates that claim from ray tracing, denoising, temporal reuse, and shading complexity.

## First experiment

The executable loads Sponza, samples triangle centroids, turns them into spatial cache queries, then compares three GPU lookup layouts:

1. `hash` — open-addressed hash table, intentionally similar to sparse radiance-cache access.
2. `paged` — direct page table + contiguous 64-entry pages.
3. `paged-sorted` — the same paged layout, but queries are grouped by page before dispatch to improve wave/L2 locality.

The result is emitted as CSV-compatible rows with GPU timestamp time per dispatch. This is not a GI quality benchmark yet; it answers whether the memory-layout hypothesis is worth pursuing.

## Development environment

The research workflow is managed by [mise](https://mise.jdx.dev/). The repository pins CMake and Ninja; the host supplies a C++20 compiler and the Vulkan loader/driver.

A Vulkan SDK installation is **not required**. On NixOS, `mise run bench` resolves `vulkan-loader` automatically while keeping the host GPU ICD/driver from `/run/opengl-driver`:


- Vulkan headers are fetched by `vk-bootstrap`.
- If `glslc` / `glslangValidator` is already installed it is reused.
- Otherwise CMake builds pinned `glslang 16.6.0` automatically.

Host requirements:

- Git
- a C++20 compiler (`clang++` or `g++`)
- a Vulkan 1.3-capable GPU and working Vulkan loader/driver
- Bash for the Sponza fetch/benchmark tasks

If Vulkan startup still fails on NixOS, verify the host driver independently with:

```bash
nix shell nixpkgs#vulkan-tools -c vulkaninfo --summary
```

### Quick start

```bash
mise install
mise run bench
```

The first configure downloads the pinned CMake dependencies and may therefore take longer than later builds.

Useful commands:

```bash
# Build only
mise run build

# Run the default Sponza benchmark
mise run bench

# Change workload size / timing iterations
mise run bench --queries 8000000 --iterations 200

# Enable Vulkan validation
mise run bench --validation

# Verify the compute path without downloading Sponza
mise run bench:synthetic

# Remove generated build state
mise run clean
```

Equivalent manual invocation after building:

```bash
./build/release/phos-gi-lab \
  --scene assets/Vulkan-Samples-Assets/scenes/sponza/Sponza01.gltf \
  --queries 4000000 \
  --iterations 100
```

## Why C++20

This repository is C++20 rather than Rust because the research target is low-level Vulkan behavior: ray-query integration, memory placement, extension experiments, RenderDoc/Nsight inspection, and vendor counters. C++ keeps the path from Vulkan SDK samples and GPU tooling to the experiment shorter. `vk-bootstrap` is only used for instance/device setup; hot-path code stays explicit Vulkan.

## Scene

The default dataset is the classic **Sponza** scene. The fetch task uses Khronos' `Vulkan-Samples-Assets` repository rather than committing the asset into this repository. Khronos lists its Sponza variant as CC BY 3.0. The asset remains external and keeps its own license.

```bash
mise run assets
```

## Expected output

```text
variant,queries,pages,bytes,gpu_us_per_dispatch,checksum
hash,4000000,...
paged,4000000,...
paged-sorted,4000000,...
```

Do **not** compare absolute numbers across machines. Compare the variants on the same GPU and build. Nsight/RenderDoc should be used afterwards to inspect cache behavior and memory transactions.

## Research progression

- M0: cache-layout microbenchmark on Sponza-derived surface queries — this repository starts here.
- M1: GPU radix/binning by page ID; remove CPU sorting from `paged-sorted`.
- M2: persistent surfel allocation/deallocation and dirty-page updates.
- M3: Vulkan `VK_KHR_ray_query` geometry backend and one-bounce indirect lighting.
- M4: directional payload LOD and confidence-driven exact tracing.
- M5: temporal reuse / ReSTIR path guiding and visual Sponza comparison against DDGI, SHaRC-like hash cache, and Split RC.

The experiment should be stopped or redesigned if M0/M1 do not show a repeatable locality advantage. A novel architecture is not valuable merely because it is different.
