# Lane N renderer source ownership

N001 owns the image-producing Vulkan runtime and the independent diffuse reference.

- `n001_runtime.*` adapts the accepted Integration/Lane-E runtime to the frozen 320x180 HDR boundary.
- `n001_reference.*` is an independent CPU BVH diffuse path tracer used for image reference generation.
- `n001_main.cpp` emits per-frame renderer/reference artifacts and timing/memory diagnostics.
- `imported/` contains exact blob snapshots of accepted A/B/E mechanisms. Their origin is recorded in `research/lanes/lane-n-end-to-end-renderer/experiments/001-n001-source-provenance.json`.

N001 preserves the accepted producer order, traversal ownership, and sparse radiance storage. New temporal, denoising, glossy/specular, and realtime multi-bounce mechanisms remain outside N001 scope.
