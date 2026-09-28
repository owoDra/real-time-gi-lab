# Experiment B003 — wide software traversal toward the HWRT gap

Status: target-ready; Stage A target measurement pending

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
