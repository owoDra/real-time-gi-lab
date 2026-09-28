# phos-gi-lab

Vulkan research sandbox for testing whether a **page-local surface radiance cache** can beat hash-based world-space caches on real GPU memory behavior before implementing a full GI system.

The project intentionally starts with a cache microbenchmark instead of a renderer. The central claim is about memory locality, so the first experiment isolates that claim from ray tracing, denoising, temporal reuse, and shading complexity.

## First experiment

The executable loads Sponza, samples triangle centroids, turns them into spatial cache queries, then compares three GPU lookup layouts:

1. `hash` — open-addressed hash table, intentionally similar to sparse radiance-cache access.
2. `paged` — direct page table + contiguous 64-entry pages.
3. `paged-sorted` — the same paged layout, but queries are grouped by page before dispatch to improve wave/L2 locality.

The result is emitted as CSV-compatible rows with GPU timestamp time per dispatch. This is not a GI quality benchmark yet; it answers whether the memory-layout hypothesis is worth pursuing.

## Why C++20

This repository is C++20 rather than Rust because the research target is low-level Vulkan behavior: ray-query integration, memory placement, extension experiments, RenderDoc/Nsight inspection, and vendor counters. C++ keeps the path from Vulkan SDK samples and GPU tooling to the experiment shorter. `vk-bootstrap` is only used for instance/device setup; hot-path code stays explicit Vulkan.

## Scene

The default dataset is the classic **Sponza** scene. The fetch script uses Khronos' `Vulkan-Samples-Assets` repository rather than committing the asset into this repository. Khronos lists its Sponza variant as CC BY 3.0. The asset remains external and keeps its own license. See `scripts/fetch_sponza.sh`.

## Build

Requirements:

- CMake 3.27+
- C++20 compiler
- Vulkan-capable driver
- `glslc` or `glslangValidator` (normally from Vulkan SDK)
- Git (CMake FetchContent)

```bash
./scripts/fetch_sponza.sh
cmake -S . -B build -DCMAKE_BUILD_TYPE=Release
cmake --build build -j
./build/phos-gi-lab --scene assets/Vulkan-Samples-Assets/scenes/sponza/Sponza01.gltf --queries 4000000 --iterations 100
```

Use `--synthetic` if Sponza is not downloaded.

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
