# B001 — traversal contract and comparable controls

Status: accepted

## Question

Can the Lane B traversal candidates share one explicit
`traceRay(origin, direction, tMax) -> Hit` semantic contract, pass a common
correctness reference, and expose maintenance/traversal/memory costs well enough
to make a defensible candidate-retention decision before the representative
Lane A replay?

## Variants and workload

- Candidates:
  - binary software BVH;
  - raw sparse 3D grid + DDA StrataBrick-derived control.
- Reference: brute-force triangle intersection using the same Hit contract.
- Scenes: sparse, dense, vertical.
- Geometry: static and moving.
- Camera: static and shifted.
- Finite GI ray ranges: 50 m and 200 m.
- Rays: 65,536 per row.
- Repeats: 5.
- Rows: 48.
- CPU: AMD RYZEN AI MAX+ 395 w/ Radeon 8060S.
- Vulkan devices enumerated by the probe:
  - AMD Radeon 8060S Graphics (RADV STRIX_HALO);
  - llvmpipe (LLVM 21.1.8, 256 bits).
- Measurement commit: `52710fcbd372369fe58e68f6c29b39aa9924a3db`.
- Raw artifact:
  `out/research/lane-b-traversal/001-traversal-contract-and-controls/20260928T150111Z/`.
- Runner return code: 0.

This is a CPU bring-up/control workload. It is not accepted as the final
GPU-architecture comparison and does not replace the representative Lane A
producer replay required by the shared protocol.

## Correctness

All 48 candidate rows reported zero mismatches against the brute-force
reference.

The executable also checks the contract boundary for:

- non-unit direction normalization;
- finite `tMax`;
- per-primitive face policy;
- deterministic equal-distance tie-breaking.

The accepted target artifact was produced from a clean
`research-lane-b-traversal` tree at the measurement commit.

## Trace controls

Median `trace_us` across static/moving geometry and static/shifted camera:

| scene | range | software BVH us | raw grid us | grid / BVH |
| --- | ---: | ---: | ---: | ---: |
| sparse | 50 m | 2,203.573 | 10,434.282 | 4.74x |
| sparse | 200 m | 2,378.648 | 59,033.183 | 24.82x |
| dense | 50 m | 12,920.812 | 14,117.646 | 1.09x |
| dense | 200 m | 13,200.470 | 46,266.451 | 3.50x |
| vertical | 50 m | 16,566.707 | 15,139.745 | 0.91x |
| vertical | 200 m | 16,683.954 | 30,731.802 | 1.84x |

The raw grid is therefore strongly range/regime sensitive. It is competitive
only in the short-range vertical control and degrades sharply in sparse and
200 m cases.

These timings establish only the control mechanism direction. They do not select
the final GPU traversal architecture.

## Dynamic maintenance controls

Moving-geometry medians:

| scene | BVH refit us | BVH common update us | grid dynamic update us |
| --- | ---: | ---: | ---: |
| sparse | 2.360 | 0.055 | 5.250 |
| dense | 22.294 | 0.315 | 38.764 |
| vertical | 17.960 | 0.165 | 24.174 |

For the raw grid, `dynamic_update_us` includes the common geometry movement
plus candidate-specific cell-membership maintenance. BVH structural maintenance
is reported separately as `refit_us`.

## Memory controls

| scene | BVH persistent bytes | grid persistent bytes | BVH scratch bytes | grid scratch bytes |
| --- | ---: | ---: | ---: | ---: |
| sparse | 14,396 | 15,720 | 512 | 88 |
| dense | 133,628 | 157,588 | 512 | 88 |
| vertical | 108,236 | 223,388 | 512 | 88 |

The raw grid uses more persistent memory in every tested scene, especially the
vertical control, while its fixed per-trace scratch estimate is smaller.

## HWRT probe

The target probe found no missing required extension names for:

- `VK_KHR_acceleration_structure`;
- `VK_KHR_ray_query`;
- `VK_KHR_deferred_host_operations`.

However, `vulkaninfo` enumerated both RADV hardware and llvmpipe. The current
probe therefore correctly reports `status=ambiguous` rather than attributing
global extension text to the intended physical GPU.

This does **not** reject HWRT/TLAS. It means HWRT remains a retained candidate
whose next bring-up must explicitly select/identify the target physical device,
enable the required Vulkan features, and validate the same Hit semantics before
timing.

## Interpretation

B001 resolves the bring-up/retention gate:

1. the common Hit contract is usable and has a zero-mismatch reference;
2. software BVH remains the required simple software baseline;
3. raw sparse-grid DDA is not promoted as a standalone final candidate;
4. one hierarchical StrataBrick-derived candidate remains justified because the
   historical segment/BVH pruning and localized rebuild/refit mechanism is
   materially different from this raw DDA control;
5. HWRT/TLAS remains retained, but capability is not yet proven for the intended
   physical device by this multi-device probe.

The previous pre-hardening target CSV remains diagnostic only. This result uses
the rerun after repeat/provenance capture, construction/update timing boundaries,
contract smoke tests, and multi-device HWRT handling were hardened.

## Limitations

- These are CPU control timings, not GPU traversal timings.
- The workload is deterministic GI-like bring-up traffic, not the accepted Lane
  A representative producer stream.
- The raw grid is deliberately simpler than historical StrataBrick and cannot
  reject the hierarchical StrataBrick hypothesis by itself.
- HWRT extension support for the intended RADV physical device is not established
  by the ambiguous multi-device probe.
- No final traversal winner is selected here.

## Decision and next question

Decision: accept B001 as the Lane B semantic/correctness and candidate-retention
checkpoint.

Advance:

- software BVH baseline;
- one hierarchical StrataBrick-derived candidate;
- HWRT/TLAS pending explicit physical-device bring-up.

Do not advance raw sparse-grid DDA as a standalone final architecture.

Next question: on the representative Lane A producer stream, how do the surviving
GPU candidates compare when traversal, build/refit/rebuild/update, persistent
memory, scratch memory, and correctness are all included?
