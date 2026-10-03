# N001 — renderer/reference bring-up

Status: **GPU-independent implementation complete; target GPU execution pending**

Issue: #26  
Branch: `research-lane-n-end-to-end-renderer`  
Architecture source of truth: `research@a75cf7857761cfbc783c9f1f847dc1380359481e`

## Scope

N001 builds an actual linear-HDR end-to-end renderer around the accepted A–M decisions. It does not select a performance winner and does not add temporal reuse, leak mitigation, denoising, glossy/specular transport, or new multi-bounce realtime transport.

The accepted architecture remains unchanged:

- A001 visibility-driven Split RC producer/schema v1;
- natural GPU append order;
- HWRT/TLAS primary traversal;
- software fallback: segment DDA/hash + object-local StrataBrick + conservative quantized Micro BVH8;
- per-probe open-addressed sparse hash radiance storage;
- immutable static geometry;
- rigid object-local BLAS + instance transform;
- stable-topology object-local UPDATE;
- topology-changing/high-churn object-local rebuild.

N001 snapshots the accepted A/B/E implementation blobs with exact SHA provenance instead of reimplementing those mechanisms. The historical Integration #13 integer/hash radiance payload is replaced only at the image-transport boundary by real Lambertian radiance; the accepted producer/traversal/storage/ownership mechanisms are preserved.

## Frozen workload

Scene: `assets/Vulkan-Samples-Assets/scenes/sponza/Sponza01.gltf`  
SHA-256: `2a86fdc2dc92d7c6a740682c61ec97f3101f489a06443c6823aff85bb990e5f6`

Raw output/reference:

- 320×180 RGB float PFM;
- linear Rec.709;
- top-left logical origin;
- no exposure/tone mapping in metrics;
- constant-white Lambertian material response;
- deterministic independent reference seeds `0x12345678` and `0x9abcdef0`.

Playback contains four independently identified states: static, camera motion, light motion, and rigid geometry motion. Each state is canonical-JSON hashed and must match between output and reference.

## Renderer path

`phos-n001` uses:

1. a full-resolution HWRT primary-visibility prerequisite;
2. the accepted A001 visibility-driven producer and natural append order;
3. accepted Lane-E-final HWRT traversal/dynamic ownership;
4. one-bounce Lambertian probe-hit radiance;
5. accepted per-probe open-addressed sparse radiance storage;
6. a full-resolution composite that reads the sparse probe storage and emits HDR pixels.

The direct-light shadow prerequisite is shared by every future Lane-N variant and uses conservative triangle occlusion. It is not counted as a new GI mitigation. Any residual discrepancy against the reference remains observable rather than being hidden by a denoiser or temporal pass.

## Diffuse reference

The reference is an independent CPU BVH diffuse path tracer using the same frozen camera/geometry state:

- direct + indirect Lambertian transport;
- up to 8 diffuse bounces;
- two independent seeds;
- 512 spp, then powers of two up to 8192 spp;
- convergence requires both p99 absolute luminance delta <= 0.001 and p99 relative luminance delta <= 0.01.

A frame that fails to converge by 8192 spp is not N001-valid. Multi-bounce difference is intentionally recorded as a current capability boundary; Lane N does not implement a realtime solution for it.

## Timing boundary

GPU timestamps are primary. CPU wall time is diagnostic/provenance only. Complete GI contains:

- renderer prerequisite attributable to GI;
- frame init / visibility;
- producer;
- ray preparation;
- geometry upload;
- AS maintenance;
- traversal;
- gather;
- radiance storage;
- merge/resolve;
- synchronization.

The named stage sum must match `complete_gi_gpu` within 2 us. `complete_renderer_gpu` additionally includes final image composition. N001 has no formal winner threshold; Lane K 5% and Lane L 20% thresholds are not reused.

## Memory boundary

Every frame records:

- aggregate persistent bytes;
- transient bytes;
- scratch bytes;
- simultaneous old/new overlap;
- true lifetime peak;
- radiance-storage persistent bytes;
- producer-stream capacity;
- image transient bytes.

For the N001 rigid UPDATE path, old/new overlap is zero because the accepted AS update is in-place. `true_lifetime_peak` must be at least every simultaneously live component and is automatically validated.

## Correctness / provenance gate

Target evidence is valid only when all of these pass automatically:

- clean `research-lane-n-end-to-end-renderer` checkout;
- exact Sponza SHA-256;
- exact playback and per-frame state digests;
- output/reference dimensions and HDR alignment;
- finite HDR payloads;
- converged reference for every frame;
- traversal runtime errors = 0;
- Vulkan validation-layer error lines = 0 (recorded as OOB/error gate);
- storage failures = 0;
- lifetime-accounting errors = 0;
- target device/driver/API/timestamp provenance present;
- complete GI/renderer timing present and internally accounted;
- required memory categories present.

No sample or outlier deletion is allowed.

## GPU-independent checks

```bash
mise exec -- python scripts/research/lane_n_end_to_end_renderer/test_n001_contract.py

mise exec -- python scripts/research/run_experiment.py \
  --lane lane-n-end-to-end-renderer \
  --experiment 001-renderer-reference-bringup \
  --command "mise exec -- python scripts/research/lane_n_end_to_end_renderer/run_n001.py --phase contract"
```

The synthetic PFM generated by `--phase contract` is serialization/metric smoke only and is never GI evidence.

## Target build and execution

Build first:

```bash
cmake -S . -B build -DCMAKE_BUILD_TYPE=Release
cmake --build build --target phos-n001 -j
```

Then run target evidence through the research wrapper:

```bash
mise exec -- python scripts/research/run_experiment.py \
  --lane lane-n-end-to-end-renderer \
  --experiment 001-renderer-reference-bringup \
  --command "mise exec -- python scripts/research/lane_n_end_to_end_renderer/run_n001.py --phase target --binary build/phos-n001"
```

Expected run-root artifacts include:

```text
metadata.json
stdout.log
stderr.log
n001-renderer-stdout.log
n001-renderer-stderr.log
n001-runtime.json
n001-provenance.json
n001-validation-summary.json
frames/output-000.pfm ... output-003.pfm
frames/reference-000.pfm ... reference-003.pfm
```

Success means the command exits 0 and `n001-validation-summary.json` has `status: "pass"`. N001 still makes no performance winner claim.

N002 is blocked until this target gate passes. N003, N004, and N005 remain ordered behind N002 as specified by Issue #26.
