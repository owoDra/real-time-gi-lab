# Experiment B003 — wide software traversal toward the HWRT gap

Status: accepted evidence; complete

## Question

When HWRT/ray query is unavailable, can a software traversal path shaped more
like a modern two-level RT hierarchy materially close B002's performance gap
without giving up the B001 shared Hit contract or the hierarchy's memory
advantage?

B002's accepted representative means on the AMD Radeon 8060S / RADV target were:

- hierarchical StrataBrick-derived: 284.334 us;
- HWRT/TLAS: 65.725 us.

The software/HWRT gap is therefore about 218.609 us. B003 asks whether removing
the segment-grid DDA/hash front end and widening the hierarchy can close a
meaningful fraction of that gap before investing in a more complex fully
GPU-maintained fallback.

## Motivation, not prior evidence

External work motivates the mechanism but does not count as B003 evidence:

- Ylitie, Karras, and Laine, *Efficient Incoherent Ray Traversal on GPUs Through
  Compressed Wide BVHs* (HPG 2017), reports 1.9–2.1x faster incoherent traversal
  and substantially lower hierarchy memory than a typical uncompressed binary
  BVH using a compressed BVH8;
- AMD HIP RT's RDNA4 path documents compressed BVH8 and triangle packets.

B003 does not assume those results transfer to this Vulkan-compute Split RC
workload. They only justify testing wide/compressed hierarchy mechanisms.

## Representative workload

Final performance evidence uses exactly the accepted A001 natural streams:

`out/research/lane-a-split-rc/001-representative-producer/20260928T143212Z/`

from Lane A measurement commit
`8b647ef8dcf1150f86a9d25c039ca48bd7f30b8f`.

Required cases:

- static;
- camera-motion;
- light-motion.

Sponza geometry, primitive identity, face policy, ray conversion, finite tMax,
tie breaking, normals, material identity, and instance identity remain identical
to B002.

## Stage A — cheapest structural rejection test

Compare on the same target/run:

1. **B002 hierarchical baseline**
   - segment-grid DDA + hash lookup;
   - binary per-segment BVH.
2. **macro-BVH8 + binary micro-BVH**
   - remove DDA/hash from traversal;
   - build a top-level 8-wide BVH over occupied segments;
   - retain B002's already-proven binary per-segment BVHs.

This isolates the most important structural hypothesis: whether the grid/DDA
front end is preventing the software fallback from approaching HWRT.

The macro builder is deliberately simple and deterministic rather than an
attempt to reproduce the HPG 2017 CWBVH builder. It partitions segment bounds
along the longest centroid axis into up to eight balanced groups. If even this
cheap top-level replacement has no useful signal, later compression/packet
work is not justified yet.

## Stage B — conditional follow-up inside B003

Only if Stage A materially improves representative traversal should B003 add:

- 8-wide micro-BVH collapse inside segments;
- quantized/compressed child bounds;
- compact traversal-stack representation;
- triangle leaf packets if leaf-intersection pressure remains material.

A fully GPU-side membership/build/refit/rebuild path is deferred until traversal
itself is promising. This follows the shared protocol's rule to prefer the
simplest experiment that can reject a hypothesis.

## Correctness gate

Every performance-interpreted row must:

- replay the exact A001 stream with original order and item count;
- pass the B001 shared Hit contract;
- have zero mismatches against the same CPU SoftwareBvh reference used by B002;
- have zero runtime/stack-overflow errors;
- match the reference full semantic checksum;
- preserve glTF `doubleSided` face policy;
- run on the exact selected target physical device.

Any failure invalidates that row before timing is interpreted.

## Measured boundaries

For every Stage A candidate record:

- structure-build CPU time;
- CPU pack time;
- acceleration upload time;
- ray upload time;
- traversal median over repeated GPU timestamp measurements;
- persistent allocation bytes;
- transient replay bytes;
- logical stack bytes per ray;
- node/segment counts sufficient to audit structure shape.

The existing B002 hierarchy is rebuilt inside the same B003 process so the
comparison does not rely only on historical timings.

HWRT's accepted B002 result remains the fixed target reference. B003 Stage A is
specifically a software-path comparison and does not require HWRT to exist on a
future fallback device.

## Stage A decision gate

Advance to Stage B only if **macro-BVH8 + binary micro-BVH** satisfies all of:

1. zero correctness/runtime errors;
2. at least 20% lower mean representative traversal time than the B002
   hierarchical baseline measured in the same B003 run;
3. no more than 1.15x the baseline hierarchy's persistent GPU allocation.

The 20% threshold is intentionally below the full target: Stage A only needs to
show that removing DDA/hash is worth deeper wide-BVH work.

## B003 success target

The full B003 software fallback is considered to have materially approached
HWRT if a later Stage B variant:

- closes at least half of B002's hierarchy-to-HWRT traversal gap, equivalent to
  a representative mean at or below about 175 us on the same target;
- remains within 1.5x B002 hierarchical persistent memory;
- preserves zero-mismatch correctness;
- does not replace the traversal gain with worse required maintenance cost.

If traversal cannot reach that region, B003 should record the rejection rather
than continue adding complexity.

## Result lifecycle

Raw artifacts remain under:

`out/research/lane-b-traversal/003-wide-software-traversal/<timestamp>/`

The accepted/rejected result will be written only after target evidence exists:

`research/lanes/lane-b-traversal/results/003-wide-software-traversal.md`

B002's primary HWRT/TLAS decision remains accepted while B003 runs. B003 is a
fallback-optimization follow-up and does not block Integration #13.


## Stage A implementation checkpoint

Stage A is target-ready on the lane branch.

Implemented:

- deterministic balanced Macro BVH8 over the occupied B002 segment roots;
- B002 binary per-segment micro BVHs retained unchanged;
- segment DDA and segment hash removed only from the new candidate traversal;
- split-axis child ordering with ray-direction-aware near-first DFS;
- duplicate micro-root AABB test removed after the identical Macro child bound
  has already passed;
- fixed-capacity Macro stack with CPU-computed worst-frontier gate and runtime
  overflow reporting;
- exact A001 static/camera-motion/light-motion replay;
- same-run B002 hierarchical baseline rebuilt and timed alongside the candidate;
- B001 shared-Hit full-stream correctness validation;
- persistent/transient/logical-stack accounting;
- separate hierarchy build, pack, Macro build, upload, ray-upload, and traversal
  boundaries;
- automatic Stage A decision JSON;
- clean-checkout and accepted-A001 provenance validation in the target runner;
- GPU-independent B002 semantic smoke followed by B003 Macro-structure smoke
  before Vulkan timing.

The local assistant environment does not contain the repository's target Vulkan
toolchain / GLSL compiler or the target GPU. The new C++ Macro builder was
syntax-checked in isolation with `-Wall -Wextra -Wpedantic`; the formal build,
shader compilation, correctness gate, and performance timing must be performed
through the documented target-side `mise` workflow.

Expected Stage A artifact additions:

- `b003-stage-a.csv`;
- `b003-stage-a-summary.json`;
- `b003-correctness.json`;
- `b003-device.json`;
- `b003-config.json`.

If `advance_to_stage_b` is true, continue within B003 with wide micro-BVH and
compression. If false, inspect the per-case data before deciding whether the
Macro hypothesis is rejected or whether a correctness/build issue invalidated
the run.


## Stage A diagnostic correction — top-level bound definition

The first target Stage A output passed correctness but produced a roughly 7 ms
Macro-BVH8 traversal versus roughly 0.28 ms for the same-run B002 hierarchy.
That output is diagnostic, not a valid rejection of the top-level-BVH
hypothesis.

Review found that the initial Macro leaves used each segment micro-BVH's full
triangle root bounds. B002 duplicates primitives into every grid cell overlapped
by the primitive AABB, and those full triangle bounds are not clipped to the
cell. Using them again as top-level leaf bounds therefore creates heavy overlap
between neighboring Macro leaves and can make a ray enter many duplicated
micro-BVHs.

The corrected Stage A top level now uses the **segment cell AABB** as the Macro
leaf bound. The per-segment micro root retains its original full triangle bound
and is tested after cell admission. This preserves correctness while testing the
intended question: BVH traversal over the same spatial partition that B002's DDA
walks.

The first output remains useful evidence that a top-level BVH over duplicated
micro-root bounds is a bad representation; it does not count toward the Stage A
20% advance gate. A fresh target run from the corrected commit is required.


## Corrected Stage A outcome — Macro replacement rejected, B003 pivots

The corrected Stage A rerun uses segment-cell AABBs at the Macro level and
passes all shared-Hit correctness gates.

Submitted Stage A summary:

- same-run B002 hierarchy mean traversal: 286.050166 us;
- Macro BVH8 + binary micro mean traversal: 632.889164 us;
- trace improvement fraction: -1.212511 (the candidate is about 2.21x slower);
- B002 hierarchy persistent bytes: 26,971,056;
- Macro candidate persistent bytes: 26,998,832;
- memory ratio: 1.001030;
- correctness errors: 0;
- Stage A advance gate: false.

Per-case CSV timing is consistent rather than being driven by one outlier:

- static: 276.485 us baseline versus 620.499 us Macro;
- camera-motion: 277.828 us versus 599.319 us;
- light-motion: 303.837 us versus 678.850 us.

Interpretation: B002's segment DDA/hash front end is valuable on this disjoint
grid partition. Replacing it with the simple balanced Macro BVH8 adds
top-level box tests and overlap at internal group bounds without providing a
compensating reduction in micro traversal. The Macro replacement is therefore
rejected for this workload.

This does **not** reject the independent wide-micro hypothesis. Stage A changed
the already-efficient top level while leaving the binary micro hierarchy
unchanged. B003 now pivots to a Stage B isolation test:

- retain B002's segment DDA/hash exactly;
- replace only each per-segment binary BVH with a collapsed BVH8;
- preserve the same segment memberships, ordered primitive ranges, exact A001
  streams, and B001 shared-Hit contract.

The original Stage A rule "continue only if Macro improves" is superseded by
this evidence-driven pivot because the result identified the top-level
replacement as the wrong optimization target while leaving the micro-level
hypothesis untested. Stage B must still independently earn further compression
or packet work.


## Stage B1 implementation checkpoint — DDA + float Micro BVH8

Stage B1 is target-ready.

The new candidate keeps the B002 segment DDA/hash traversal unchanged and
collapses only each segment's binary micro BVH into an uncompressed 8-wide
hierarchy. Binary leaves remain the same primitive ranges; only internal
traversal shape changes.

The same B003 formal run now produces:

- `b003-results.csv` with three candidates per A001 case:
  - `hierarchical-stratabrick`;
  - `macro-bvh8-binary-micro` (the rejected Stage A control);
  - `dda-wide-micro-bvh8` (Stage B1);
- `b003-stage-a-summary.json`;
- `b003-stage-b-summary.json`;
- `b003-correctness.json`;
- `b003-device.json`;
- `b003-config.json`.

Stage B1 is a viability gate for compression. Advance to quantized/compressed
BVH8 when:

- correctness/runtime errors remain zero;
- the uncompressed wide-micro mean is no worse than 1.15x the same-run binary
  hierarchy;
- persistent memory is no more than 1.5x the same-run binary hierarchy.

This is intentionally not the final B003 success criterion. Compression is
expected to be part of the wide-BVH hypothesis; Stage B1 only rejects variants
that are already too far behind for compression to plausibly rescue.


### Stage B1 self-review hardening

Before target measurement, the wide-micro traversal was hardened in two ways:

- each queued wide child now carries its already-computed AABB entry distance;
  after a nearer hit is found, queued children beyond the new best distance are
  discarded without retesting their AABB;
- the GPU-independent structural smoke now compares the complete set of binary
  leaf primitive ranges against the collapsed wide hierarchy for every segment,
  including a multi-level synthetic dense scene. This catches lost, duplicated,
  or mis-encoded leaves before GPU timing.

These changes do not alter the B001 Hit contract or the DDA/hash top level.


The Stage B1 logical stack accounting records both the 64-entry token stack and
the 64-entry saved entry-distance stack (512 bytes per ray invocation total).
The saved distances are traversal-local scratch, not persistent GPU allocation.


## Stage B1 target result — wide micro viable

The first DDA-preserving wide-micro target run passed the B1 viability gate.

Evidence:

- exact target: AMD Radeon 8060S Graphics (RADV STRIX_HALO), Mesa 26.1.2;
- accepted A001 provenance retained;
- B001 shared-Hit mismatches/runtime errors: 0/0;
- wide-micro nodes: 27,406;
- wide-micro depth: 7;
- maximum structural stack frontier: 40;
- baseline mean traversal: 283.845978 us;
- DDA + float Micro BVH8 mean traversal: 253.134292 us;
- traversal improvement: 10.8198%;
- baseline persistent bytes: 26,971,056;
- wide-micro persistent bytes: 28,534,032;
- persistent-memory ratio: 1.057950;
- advance_to_quantization: true.

Per-case float BVH8 traversal:

- static: 247.390 us;
- camera-motion: 254.604 us;
- light-motion: 257.409 us.

The gain is consistent across all three exact A001 streams. The uncompressed
wide representation also increases acceleration upload cost because each wide
node stores eight full float child AABBs. This makes child-bound compression the
next isolated mechanism to test rather than immediately changing DDA or leaf
intersection semantics.

Stage B2 will therefore keep:

- segment DDA/hash;
- the same wide-tree topology and leaf primitive ranges;
- the same near-first ordering and tNear pruning;

and change only child-bound representation to conservative parent-relative
quantization.


## Stage B2 implementation checkpoint — conservative 16-bit child bounds

Stage B2 is target-ready. It keeps the Stage B1 DDA/hash, topology, leaf ranges, near-first order, and tNear pruning; only child-bound representation changes.

- float BVH8 node: 384 bytes;
- quantized BVH8 node: 176 bytes;
- parent-relative 16-bit min/max per axis;
- min/max and parent scale are rounded outward conservatively;
- child tokens and ordering axis are unchanged.

For 27,406 nodes, raw node storage falls from 10,523,904 bytes to 4,823,456 bytes (about 5.44 MiB saved before allocator alignment).

The structural smoke verifies topology preservation and that every decoded quantized child AABB conservatively contains its source float AABB.

The formal run adds `b003-stage-b2-summary.json`. Advance to triangle packets only with zero errors, quantized traversal <=1.10x float BVH8, and persistent memory <=0.90x float BVH8.


## Stage B2 target result — quantized wide improves both speed and memory

The submitted Stage B2 summary passes its gate:

- float Micro BVH8 mean: 251.978763 us;
- quantized Micro BVH8 mean: 231.392983 us;
- trace ratio: 0.918304 (about 8.17% faster);
- float-wide persistent bytes: 28,534,032;
- quantized persistent bytes: 22,833,584;
- memory ratio: 0.800223 (about 20.0% lower);
- correctness errors: 0;
- advance_to_triangle_packets: true.

This is evidence that compression helps the current software fallback on both bandwidth-sensitive traversal and residency, rather than being a memory-only trade.

## Stage B3 implementation checkpoint — direct four-triangle packets

Stage B3 is target-ready. It keeps DDA/hash and the conservative quantized BVH8, but replaces the leaf `ordered index -> global triangle` indirection with one direct four-triangle packet per unique binary leaf.

- binary leaves already contain at most four triangles;
- packet layout is 256 bytes: four `v0`, four `e1`, four `e2`, four metadata records;
- leaf token count is preserved while its begin field is remapped to packet index;
- internal tokens, quantized AABBs, ordering axes, segment hash roots, and stack behavior are unchanged;
- packet candidate does not allocate the global triangle buffer or ordered-index buffer;
- packet geometry is duplicated across segment leaves when StrataBrick membership duplicates a primitive, so the resulting memory cost is measured rather than assumed beneficial.

The structural smoke checks packet geometry, primitive/material/instance identity, two-sided policy, leaf count, internal tokens, and packet slot accounting against the source quantized hierarchy.

The formal run now emits `b003-stage-b3-summary.json`. Retain triangle packets only with zero correctness errors, at least 5% lower mean traversal time than the quantized non-packet candidate, and no more than 1.25x its persistent memory. A failed packet gate does not reject the quantized BVH8 result.


## Stage B3 target result — packet concept useful, original layout narrowly rejected

The submitted Stage B3 summary is fully correct but narrowly misses both packet-retention thresholds:

- quantized non-packet mean: 231.720271 us;
- packet mean: 220.231776 us;
- trace ratio: 0.950421;
- quantized persistent bytes: 22,833,584;
- packet persistent bytes: 28,872,096;
- memory ratio: 1.264457;
- correctness errors: 0;
- retain_triangle_packets: false.

The speed result is close enough to the fixed 5% gate, and correctness is clean, that B003 does not reject packetization yet. The original 256-byte packet stores 16 bytes of metadata per triangle even though material/instance/two-sided identity fits a smaller validated encoding on this workload.

## Stage B3.1 implementation checkpoint — compact packet metadata

B3.1 is target-ready. It preserves packet geometry and all traversal behavior, but compresses per-triangle metadata from 16 bytes to 8 bytes:

- primitive id remains a full 32-bit value;
- material id uses 12 bits with an explicit invalid sentinel;
- instance id uses 19 bits;
- two-sided uses the remaining high bit;
- builder rejects scenes that cannot be represented losslessly;
- packet size falls from 256 bytes to 224 bytes.

The structural smoke decodes every compact metadata record back to the source triangle and checks primitive/material/instance/two-sided identity plus geometry exactly. The formal run now emits `b003-stage-b31-summary.json` and keeps the original fixed B3 thresholds: compact packet mean must be <=0.95x quantized non-packet mean, persistent memory <=1.25x, and correctness/runtime errors zero.


## Stage B3.1 target result — compact packets rejected

The submitted B3.1 summary remains fully correct, but the compact packet layout still misses the fixed speed-retention gate:

- quantized non-packet mean: 231.225999 us;
- original packet mean: 216.658320 us;
- compact packet mean: 221.060017 us;
- compact versus quantized trace ratio: 0.956034;
- compact versus original-packet trace ratio: 1.020316;
- quantized persistent bytes: 22,833,584;
- original packet persistent bytes: 28,872,096;
- compact packet persistent bytes: 25,874,208;
- compact versus quantized memory ratio: 1.133165;
- compact versus original-packet memory ratio: 0.896167;
- correctness errors: 0;
- retain_compact_triangle_packets: false.

The compact layout solves the original packet memory failure but loses about 2% traversal performance relative to the 256-byte packet and remains at only about 4.4% improvement over the quantized non-packet candidate. The fixed 5% speed threshold is therefore not met. B003 stops packet iteration here rather than relaxing the gate.

### Provisional B003 candidate disposition

- reject Macro BVH8 as top-level replacement;
- retain DDA/hash top level;
- retain float Micro BVH8 as positive mechanism evidence;
- **select conservative quantized Micro BVH8 as the best balanced B003 software-fallback candidate**;
- reject both tested triangle-packet layouts for this B003 decision gate.

The quantized candidate improves the original hierarchical fallback materially, but its roughly 231 us representative mean is still above B003's <=175 us full success target. Therefore B003 has not closed at least half of the B002 hierarchy-to-HWRT traversal gap. The result is an improved fallback, not HWRT-equivalent software traversal.

Do not write the accepted/rejected B003 result or update `results/index.json` until the complete final-run provenance/config/correctness set from the same artifact is checked.


## Formal B003 closeout

Formal accepted artifact:

`out/research/lane-b-traversal/003-wide-software-traversal/20260928T175711Z/`

Measurement commit:

`c3dffb80b4640abfc6fcf1d22608c883de537378`

The checkout was clean, the runner returned 0, the exact intended RADV physical
device was selected, and all 18 interpreted candidate rows completed with zero
B001 Hit mismatches and zero runtime errors.

Final result:

`../results/003-wide-software-traversal.md`

B003 promotes DDA/hash + conservative quantized Micro BVH8 as the new software
fallback. It improves the fallback materially but does not meet the <=175 us
full HWRT-gap-closing target. Packet variants are not retained under their
predefined gates.
