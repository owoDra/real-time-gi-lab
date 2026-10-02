# N001 — renderer/reference bring-up

Status: **GPU-independent preparation complete; target renderer/reference execution pending**

Issue: #26  
Branch: `research-lane-n-end-to-end-renderer`  
Program source of truth: `research@a75cf7857761cfbc783c9f1f847dc1380359481e`

## Question

Can the accepted A–M architecture be brought into an image-producing renderer
with a deterministic scene/playback, a converged diffuse reference, exact pixel
alignment, complete GI/renderer timing boundaries, true-lifetime memory
accounting, and machine-checkable provenance before any performance ranking or
new transport mechanism is attempted?

N001 does **not** answer which architecture is faster. It only establishes a
trustworthy renderer/reference measurement surface.

## Frozen architecture inputs

N001 must preserve the current `research/status.md` decisions:

- A001 visibility-driven Split RC producer/schema v1;
- natural GPU append order, with no post-producer global reorder;
- HWRT/TLAS primary traversal;
- software fallback: segment DDA/hash + object-local StrataBrick + conservative
  quantized Micro BVH8;
- per-probe open-addressed sparse hash radiance storage;
- immutable static geometry ownership;
- rigid object-local BLAS + instance transform;
- stable-topology deformation through object-local UPDATE;
- topology-changing/high-churn through the retained Lane-E object-local rebuild
  backend.

N001 geometry playback only needs to prove deterministic geometry-state replay;
the target bring-up frame may exercise the rigid/stable-topology paths. Full
separate topology-changing/high-churn characterization starts in N002/N004.

The historical Integration #13 `i001_radiance.comp.glsl` deterministic integer
radiance payload is **not** a valid N001 image renderer or reference. It was a
correctness/control mechanism, not physical diffuse transport. N001 must produce
linear HDR radiance from real direct + indirect diffuse transport.

## GPU-independent contract

The machine-readable freeze is `001-n001-config.json`.

The contract code:

- validates the frozen experiment/config identity;
- derives a SHA-256 playback identity for every camera/light/geometry frame;
- reads/writes RGB float PFM with an explicit top-left in-memory origin;
- rejects non-finite HDR values and dimension/alignment mismatches;
- computes raw radiometric metrics before exposure/tone mapping;
- validates complete GI and complete-renderer GPU boundaries independently;
- validates persistent/transient/scratch/old-new-overlap/true-lifetime-peak
  memory categories;
- validates clean-commit/device/driver/API/timestamp provenance;
- rejects any target artifact with traversal/OOB/storage/lifetime errors.

The contract smoke uses a synthetic HDR gradient only to test serialization and
metric arithmetic. It is not GI evidence.

## Scene and deterministic playback

Scene: Sponza `Sponza01.gltf`, SHA-256
`2a86fdc2dc92d7c6a740682c61ec97f3101f489a06443c6823aff85bb990e5f6`.

The camera/light parameterization stays scene-relative so it reproduces the
accepted A001 framing rather than baking one machine-specific world transform:

- base direction `[1, 0.32, 1]`;
- eye distance `0.82 * scene diagonal`;
- vertical FOV `70°`;
- camera-motion orbit `0.35 rad`;
- static light offset `[0.15, 0.35, 0.10] * diagonal`;
- moved light offset `[-0.30, 0.22, 0.28] * diagonal`.

Four bring-up states are frozen: static, camera motion, light motion, and one
deterministic geometry-motion state. Geometry selection is seeded. Every state
gets an exact canonical JSON digest and the target renderer/reference must emit
that digest with the frame.

## HDR and alignment contract

N001 raw exchange format is RGB float PFM:

- 320 × 180;
- linear Rec.709 RGB;
- top-left logical origin;
- no exposure or tone mapping in the metric path;
- all finite pixels are valid in N001;
- output and reference must have identical dimensions and playback state digest.

PFM is used here because it is dependency-free, lossless float HDR, and easy to
audit. Display PNG/JPEG screenshots may be generated later but are diagnostic
only.

## Diffuse reference contract

The N001 reference is diffuse path tracing, not a new realtime feature:

- direct + indirect Lambertian transport;
- up to 8 diffuse bounces;
- no glossy/specular reference in N001 bring-up;
- two deterministic independent seeds;
- begin at 512 spp and grow by powers of two up to 8192 spp;
- reference convergence requires both independent replicates to satisfy:
  - p99 absolute luminance delta <= 0.001;
  - p99 relative luminance delta <= 0.01.

If a frame does not converge by 8192 spp, that frame is not N001-valid. The
thresholds must not be relaxed after observing the target result.

Multi-bounce mismatch and glossy/specular capability are recorded later as
capability boundaries; no mitigation is implemented in Lane N.

## Image metrics

At minimum, preserve per frame:

- mean absolute luminance error;
- mean relative luminance error;
- RGB RMS error;
- p95/p99/max absolute luminance error;
- p95/p99 relative luminance error;
- affected-pixel fraction using the frozen absolute + relative thresholds.

No single aggregate score replaces these radiometric values.

## Complete timing boundary

GPU timestamp remains the primary performance axis and complete CPU wall remains
diagnostic/health/provenance only. N001 freezes names/boundaries, **not a
performance threshold**.

Complete GI GPU time contains recurrent work for:

- renderer prerequisite attributable to GI;
- producer;
- geometry preparation/upload;
- acceleration-structure maintenance;
- traversal;
- gather;
- radiance storage lookup/update/invalidation/allocation;
- merge/resolve;
- required synchronization.

The artifact also records complete renderer GPU time. A renderer prerequisite
shared with non-GI rendering may be reported in the renderer total, but any
incremental prerequisite required specifically by a GI variant stays inside the
GI boundary.

Lane K's 5% and Lane L's 20% floors are not imported as Lane-N thresholds.
Before N002/N003 performance claims, calibrate the actual complete-frame
boundary and freeze workload, metrics, threshold, process/order structure, and
rerun policy.

## Memory boundary

Every frame records:

- geometry-AS persistent bytes;
- radiance-storage persistent bytes;
- producer/stream persistent bytes;
- transient bytes;
- scratch bytes;
- simultaneous old/new overlap during updates;
- true lifetime peak;
- host mirrors separately.

`true_lifetime_peak` must describe simultaneous lifetime overlap, not the sum of
independent per-stage maxima.

## Required target artifact

A valid target root contains at least:

```text
n001-provenance.json
frames/
  output-000.pfm
  reference-000.pfm
  ...
n001-validation-summary.json   # written after validator passes
```

`n001-provenance.json` contains the clean Git identity, target device/driver/API
and timestamp period, scene/playback digests, per-frame reference convergence,
correctness counters, complete timing boundaries, memory census, and relative
paths to output/reference PFM files.

## Correctness / provenance gate

Before N001 can conclude:

- clean `research-lane-n-end-to-end-renderer` checkout;
- exact Sponza digest;
- exact playback digest and per-frame state digests;
- output/reference alignment valid;
- finite HDR payloads at 320 × 180;
- reference convergence gate passes per frame;
- traversal runtime errors = 0;
- OOB errors = 0;
- unresolved storage failures = 0;
- allocation/lifetime accounting errors = 0;
- target device/driver/API/timestamp provenance present;
- complete GI time and complete renderer time present;
- all required memory categories present.

No sample/outlier deletion exists in N001. Formal timing rerun policy is not
selected until the complete-frame calibration is designed prospectively.

## GPU-independent execution

Run the contract/tests before any target-GPU work:

```bash
mise exec -- python scripts/research/lane_n_end_to_end_renderer/test_n001_contract.py

mise exec -- python scripts/research/run_experiment.py \
  --lane lane-n-end-to-end-renderer \
  --experiment 001-renderer-reference-bringup \
  --command "mise exec -- python scripts/research/lane_n_end_to_end_renderer/run_n001.py --phase contract"
```

This produces only contract-smoke artifacts under `out/research/`; it is not a
renderer result.

## Target handoff boundary

The next implementation checkpoint is the Vulkan image-producing runtime that
ports the accepted producer/traversal/storage/dynamic-ownership mechanisms into
Lane N and emits the frozen target artifact above. Do not use the old synthetic
Integration #13 radiance function as a shortcut.

Once that runtime exists and builds cleanly, target execution must be wrapped by
`scripts/research/run_experiment.py`; the exact target command and expected
artifact list must be frozen in this document before the first target run.

N002 is blocked until N001 target artifacts pass the validator. N003/N004/N005
remain blocked behind N002 in the order defined by Issue #26.
