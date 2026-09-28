# Experiment B002 — Lane A exact-stream traversal comparison

Status: target-ready; target measurement pending

## Question

On the exact natural producer streams accepted by Lane A A001, which surviving
geometry traversal architecture gives the best practical end-to-end cost while
preserving the B001 shared Hit contract?

The comparison includes correctness, traversal, required acceleration-structure
construction and maintenance, persistent memory, scratch memory, and replay
overhead. A kernel-only win is not sufficient to promote an architecture.

## Representative workload

Final architectural evidence uses the accepted A001 artifact:

`out/research/lane-a-split-rc/001-representative-producer/20260928T143212Z/`

from Lane A measurement commit
`8b647ef8dcf1150f86a9d25c039ca48bd7f30b8f`.

Required streams:

- `static/stream-v1.bin`;
- `camera-motion/stream-v1.bin`;
- `light-motion/stream-v1.bin`.

The replay reader consumes schema v1 exactly as emitted by Lane A:

- 64-byte `SplitRcStreamHeaderV1`;
- 64-byte `SplitRcWorkItemV1`;
- little-endian binary layout;
- `PHOSRC1\0` magic and schema version 1;
- FNV-1a `workload_id` over the exact item bytes;
- original GPU append order preserved without sorting or traversal-specific
  reordering.

For traversal, each work item maps to the B001 contract as:

- origin = `(probe_px, probe_py, probe_pz) + direction * interval_min`;
- direction = `(dir_x, dir_y, dir_z)`, normalized by the shared contract;
- `tMax = interval_max - interval_min`.

This represents the cascade interval itself instead of accidentally retracing
from the probe center through all preceding cascades.

A001 does not contain moving geometry. Dynamic-geometry maintenance therefore
uses a separately labeled controlled experiment and is not substituted for the
representative replay evidence.

## Candidates

### Software BVH

Retain the B001 software BVH as the simple baseline, but run the final comparison
as a GPU traversal candidate. Count build/rebuild/refit, upload/residency,
traversal, scratch, and any replay conversion required by the candidate.

### Hierarchical StrataBrick-derived traversal

Implement the smallest fair hierarchy that tests the retained hypothesis rather
than reproducing raw sparse-grid DDA:

1. spatial membership / segment key generation;
2. compact segment ranges;
3. segment-level bounds used for coarse pruning;
4. per-segment primitive BVH;
5. occupancy metadata sufficient to skip absent segments;
6. dirty classification;
7. topology-changing membership -> localized rebuild;
8. bounds-only changes that stay in a segment -> localized refit;
9. practical finite GI ranges from the exact A001 items.

All candidate-specific membership, hierarchy construction/refit, dirty
classification, upload, and memory costs are part of the result.

### HWRT / TLAS

HWRT remains a candidate only after the B002 runtime itself proves all of:

- the selected physical device is the intended target
  `AMD Radeon 8060S Graphics (RADV_STRIX_HALO)` by explicit identity;
- `VK_KHR_acceleration_structure`;
- `VK_KHR_ray_query`;
- `VK_KHR_deferred_host_operations`;
- required Vulkan feature bits are queried and enabled;
- BLAS/TLAS creation succeeds;
- ray-query execution passes the shared Hit contract parity gate.

Global `vulkaninfo` extension text is not sufficient.

BLAS/TLAS build/update, scratch and persistent allocation are included rather
than treated as free setup.

## Shared Hit contract

B001 semantics remain authoritative:

- finite non-zero direction is normalized at the contract boundary;
- `Hit.t` is world-space closest-hit distance in
  `[1e-4, tMax]`;
- per-primitive face policy is preserved;
- world-space geometric normal is returned without candidate-specific
  face-forwarding;
- primitive, material and instance identity are correctness data;
- equal-distance hits use the B001 tolerance and lower `primitive_id`
  tie-break;
- miss is `t=+INF` and invalid ID sentinels.

Candidate-specific semantics are not allowed.

## Scene geometry

Representative replay uses the same Sponza asset as A001. Lane B loads actual
triangle geometry for traversal and assigns deterministic primitive identity.
The loader must not infer geometry from Lane A's centroid surface samples.
Per-primitive face policy is taken from the referenced glTF material's
`doubleSided` flag (default false when no material is referenced), so B002 does
not silently make every surface two-sided.

Synthetic geometry/rays may be used only for bring-up, contract tests and
isolated dynamic-maintenance stress. Such rows must be labeled control evidence.

## Correctness gate

A candidate row is eligible for performance interpretation only when:

1. the stream header, byte size and FNV-1a workload ID validate;
2. no item is reordered or dropped;
3. every replay ray has valid finite interval semantics;
4. the candidate output is semantically equivalent to the shared reference for
   the correctness sample;
5. full candidate-vs-candidate checksums agree for the complete replay stream;
6. HWRT additionally passes actual feature enablement and acceleration-structure
   creation on the explicitly selected physical device.

Any mismatch invalidates that candidate/run before timing is interpreted.

## Measured boundaries

Record separately where applicable:

- stream parse/validation;
- replay conversion/upload;
- acceleration-structure build;
- refit;
- rebuild;
- moving-geometry transform/update propagation;
- membership/key generation;
- segment construction;
- occupancy/dirty classification;
- BLAS/TLAS build or update;
- traversal;
- readback used only for correctness and excluded from accepted traversal
  timestamps;
- persistent bytes;
- peak/required scratch bytes.

For static representative replay, report both traversal-only time and total
required one-time build + replay/traversal costs. For controlled moving geometry,
report maintenance and traversal separately rather than hiding maintenance in a
combined number.

## Repetition and target device

Accepted GPU performance rows require repeated timestamp-query measurements on
the intended AMD Radeon 8060S / RADV target. Validation layers are diagnostics,
not accepted timing.

CPU synthetic timings cannot select the final GPU architecture.

## Decision gate

B002 and Lane B are complete only when the surviving candidates have been
compared on all three exact A001 streams and the result records:

- correctness;
- target physical-device identity;
- traversal cost;
- required build/refit/rebuild/update costs;
- persistent and scratch memory;
- replay overhead;
- moving-geometry controlled maintenance evidence;
- promoted and rejected candidates;
- any regime-specific differences;
- remaining limitations.

Do not force one universal winner if the evidence supports different choices by
scene regime.

The final accepted result is written only after target evidence exists at:

`research/lanes/lane-b-traversal/results/002-lane-a-exact-stream-traversal.md`

and is then added to `results/index.json`, the Lane B README, and Issue #11.


## Implementation checkpoint

The target-ready harness now produces, inside the same
`research:record` artifact:

- `b002-results.csv` — exact A001 static/camera-motion/light-motion candidate
  comparison;
- `b002-correctness.json` — shared-Hit correctness gate and exact workload
  identities;
- `b002-device.json` — exact selected Vulkan device and HWRT bring-up status;
- `b002-config.json` — segment/hash/candidate configuration;
- `b002-maintenance.csv` — controlled moving-geometry refit/rebuild/update
  costs and post-update trace correctness;
- `b002-maintenance.json` — controlled-regime identity and movement parameters.

No result document or result-index entry is created until the target artifact
exists and passes the decision gate.
