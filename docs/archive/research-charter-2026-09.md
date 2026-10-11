# Research charter

## Final research question

Can a real-time global-illumination architecture be built around **GPU locality
as a first-class constraint**, rather than accepting random sparse-cache access
as an unavoidable cost, while retaining enough spatial and directional
adaptivity to cover diffuse indirect lighting, glossy transport, dynamic
geometry, and large worlds?

The goal is not merely to build a faster lookup table. The final target is a
complete real-time light-transport architecture whose quality/performance/memory
trade-off can be shown experimentally to improve on representative existing
approaches on the same hardware.

No specific representation is an absolute requirement. Page-local surface
caches, surfels, Radiance-Cascade-style spatial/angular scaling, ReSTIR/path
guiding, or any other component may be replaced if evidence shows a better
design.

## Current architecture hypothesis

The working hypothesis is that the following ideas can compose into a stronger
GI architecture:

1. **Store radiance near useful surfaces rather than uniformly through empty
   volume.**
2. **Use hierarchical/virtual pages with contiguous local payloads** so the hot
   lookup/update path is cache-friendly; hashing may still be used for cold
   allocation or indirection.
3. **Schedule work by spatial page or another locality key** so neighboring
   lanes/waves tend to access neighboring memory.
4. **Adapt both spatial and directional resolution.** Nearby or geometrically
   complex regions receive finer spatial representation; directionally complex
   transport receives richer angular representation.
5. **Treat exact ray tracing as a confidence fallback, not the default for every
   bounce.** Cached transport is used when reliable; uncertain/disoccluded/high
   frequency cases continue tracing.
6. **Use temporal reuse and importance/path guiding only after the cache
   representation itself is proven sound.**

This is a hypothesis, not an architecture commitment.

## Representative baselines

Later end-to-end stages should compare against representative members of these
families where practical:

- sparse hash radiance caches / SHaRC-like layouts;
- DDGI / volume-probe GI;
- Split Radiance Cascades or equivalent sparse RC-style transport;
- ReSTIR-based GI/path-tracing approaches for the transport regimes they cover.

A baseline may be simplified only when the simplification is documented and
does not make the proposed method artificially favorable.

## Research principles

### Evidence before implementation depth

Each major architectural premise gets an isolated experiment before expensive
end-to-end integration. A failed premise should stop or redirect the branch
rather than be hidden by later complexity.

### Semantic parity before performance comparison

Two variants are comparable only when they compute the same logical result.
Executable correctness guards are mandatory. A faster result with mismatched
semantics is invalid evidence.

### End-to-end costs eventually count

M0 may measure an upper-bound benefit such as CPU-pre-sorted queries. The next
milestone must include the GPU cost required to obtain that ordering before the
idea can be accepted.

### GPU locality is measured, not inferred

Timestamp improvements are necessary but not sufficient. Later experiments must
also inspect cache/memory behavior (for example L2 hit/miss behavior, memory
transactions, stalls, and occupancy) to establish why a design wins.

### No vendor-specific result is universal

A result on one GPU is exploratory evidence. Architectural claims require
repeatable behavior across workloads and, before broad conclusions, more than
one GPU architecture when available.

## End-state success criteria

The research is successful only if an end-to-end implementation demonstrates:

- reproducible correctness against an appropriate reference;
- competitive or better visual quality for the tested transport regimes;
- a measurable frame-time and/or memory advantage over representative
  baselines on the same hardware and scene;
- stable behavior under camera motion, dynamic geometry, disocclusion, and
  changing lighting;
- a design whose benefits survive the cost of allocation, scheduling, updates,
  tracing, and temporal maintenance.

Until those conditions are met, this repository should describe results as
experimental evidence rather than a replacement for existing GI methods.
