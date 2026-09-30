# J001 — topology-backend deep architecture survey

Status: **complete / research-and-planning evidence only**  
Issue: #20  
Branch base: `research@76f65f8944aba8405dce5d386161df2540957349`  
Target architecture context: `AMD Radeon 8060S Graphics (RADV STRIX_HALO)`

J001 does not contain candidate implementation or performance ranking. It
selects the smallest candidate set that is justified by repository evidence and
external research, and freezes what J002-J005 must test.

## Question

For topology-changing/high-churn **object-local** geometry, is there a
data-structure/update model worth testing against:

- Lane E object-local rebuilds; and
- Lane G's hardened transient LBVH,

without changing the accepted A001 producer, exact Hit semantics, C001 storage,
or Lane E ownership boundary?

## Repository evidence carried forward

The following conclusions are treated as constraints, not hypotheses to retune
for Lane J:

- E004/E005 accept object-local ownership for rigid and stable-topology
  deforming geometry, but explicitly leave primitive-count/topology change at
  an object-local rebuild boundary.
- F005 shows that the tested sorted two-level grid is dominated by reference
  amplification and sorting: 155,033 cell references for 796 moving triangles,
  194.765 references/triangle, maximum 6,100, with roughly 15 ms of radix sort
  in the retained diagnostic campaign.
- F006/F007 establish exact-correctness mechanism evidence for transient LBVH,
  but their timing campaigns are not decision-valid.
- G001 shows that the former sparse-memory failure was dominated by unrelated
  static-HWRT lifetime overlap, not by the 796-primitive LBVH payload itself.
- G003-G005 harden those lifetimes and pass deterministic correctness and memory
  gates. The sparse peak blocker is therefore closed.
- H001 fails its pre-frozen timing-repeatability gate even on valid static
  controls. Its dynamic harness also performed only one one-way transition in
  warmup rather than repeated measured transitions.
- H004 therefore makes no claim that Lane E rebuild is faster, and no claim
  that hardened LBVH is faster.

Accordingly, J001 treats Lane E rebuild and hardened LBVH as unresolved
run-local comparators.

## External evidence and applicability

External benchmark values are not predictions for this repository. For every
source below, the source claim, its applicability, and the remaining uncertainty
are separated.

### Vulkan KHR acceleration structures

Source:
https://docs.vulkan.org/spec/latest/chapters/accelstructures.html

Direct source claim:

- UPDATE requires an acceleration structure previously built with
  `ALLOW_UPDATE`.
- UPDATE constrains geometry count and geometry description to remain compatible
  with the prior build.
- build/update uses application-provided acceleration-structure storage and
  scratch storage.

Repository inference:

- a primitive-count/topology-changing Lane-J workload is a true BUILD/rebuild
  boundary for the ordinary KHR triangle-BLAS path, not an E004-style BLAS
  UPDATE.
- object-local geometry upload, build scratch, destination resize/reallocation,
  BLAS build, changed instance reference/TLAS work, synchronization, and any
  copy/compaction work are candidate costs and must remain visible.

Unknown:

- the crossover against software candidates on this host is not inferable from
  the API contract and must not use historical Lane-E timing.

### DXR clustered geometry, 2026 draft

Source:
https://microsoft.github.io/DirectX-Specs/d3d/Raytracing2.html

Direct source claim:

- the September 2026 draft introduces cluster-level acceleration structures
  (CLAS), Cluster BLAS, partitioned TLAS, and GPU-driven indirect AS operations.
- clustered geometry is explicitly motivated by dynamic geometry for which
  acceleration-structure build time is a bottleneck.
- CLAS are small triangle groups and Cluster BLAS are built from CLAS references;
  the spec describes amortized/reusable clusters and much smaller BLAS build
  inputs.
- the document is still marked as under development and support is
  capability-reported.

Repository inference:

- the strongest current industry direction for high-churn geometry is not
  "one better global builder"; it is **bounded geometry clusters plus a smaller
  upper acceleration structure**.
- Lane J can test this structural idea in portable compute/software form while
  preserving exact triangle tests and the object-local ownership boundary.

Unknown / limitation:

- this draft is not a deployable Vulkan/RADV feature for the target repository.
  Its performance statements cannot be transferred to Radeon 8060S.

### NVIDIA RTX Mega Geometry / Vulkan cluster samples

Sources:

- https://github.com/nvpro-samples/vk_animated_clusters
- https://github.com/nvpro-samples/vk_tessellated_clusters
- https://developer.nvidia.com/blog/nvidia-rtx-mega-geometry-now-available-with-new-vulkan-samples/

Direct source claim:

- `VK_NV_cluster_acceleration_structure` represents bounded groups of triangles
  as CLAS referenced by a BLAS.
- the animated-cluster sample recommends spatially coherent clusters and reports
  64 triangles/64 vertices as a useful sample setting, while warning that larger
  clusters can trade build/memory benefits against ray-trace performance.
- cluster-related operations are GPU-indirect and have explicit destination and
  scratch requirements.
- the tessellation sample demonstrates per-frame generation of clusters for
  topology-generating workloads.

Repository inference:

- clusters can bound rebuild granularity and avoid rebuilding exact triangle
  acceleration for unaffected parts of one object.
- allocation policy, upper-level rebuild, and traversal divergence remain real
  costs and must be measured rather than assumed away.
- 64 triangles is a useful scale reference for a prototype parameter, not an
  AMD performance prediction.

Unknown / limitation:

- the extension is NVIDIA-specific and cannot be the Lane-J production
  mechanism on the RADV target. Lane J therefore retains only the architecture
  concept, not the extension/API implementation.

### H-PLOC, HPG 2024

Source:
https://doi.org/10.1145/3675377

Direct source claim:

- H-PLOC is a GPU-oriented binary BVH construction algorithm based on
  PLOC/PLOC++.
- the paper reports similar BVH quality with fewer construction kernels and
  lower build time than the compared builders in its benchmark set.

Repository inference:

- there remains meaningful research progress in full GPU BVH rebuild algorithms;
  hardened LBVH is not the only possible full-rebuild builder.

Why it is **not** a separate J003 candidate:

- it remains a monolithic full-BVH rebuild model.
- Lane J's primary unresolved question is whether a different update
  granularity/representation can beat full object rebuilds, not whether another
  full builder is a few percent better.
- if J004 later isolates monolithic builder time as the dominant remaining
  blocker, H-PLOC is a justified follow-up, but implementing it now would expand
  the candidate count without testing the higher-value structural hypothesis.

### Hybrid BVH for interactive GPU ray tracing, SIGGRAPH 2026

Source:
https://blog.yiningkarlli.com/2026/07/hybrid-bvh.html

Direct source claim:

- Disney Animation describes a production GPU ray-tracing hierarchy separated
  by change categories.
- the system chooses reuse, refit, or rebuild by category instead of applying
  one update policy to the entire scene.

Repository inference:

- this independently supports Lane E's already accepted ownership/update
  decomposition.
- it supports keeping Lane J object-local and class-scoped rather than creating
  another global dynamic structure.

Limitation:

- this is not evidence that Disney's exact structure or thresholds apply to the
  Split-RC workload.

### Grid-induced BVH and partial reconstruction

Source:
https://link.springer.com/article/10.1007/s00371-021-02205-3

Direct source claim:

- GBVH maintains a grid-derived hierarchy and reconstructs only the modified part
  when a partial set changes.

Repository inference:

- partial hierarchy reconstruction is feasible in principle.

Why it is not retained as a J003 candidate:

- its published implementation/evaluation does not establish a clean,
  GPU-native arbitrary insertion/removal path matching this repository.
- introducing fine-grained node allocation, dependency propagation, and
  quality-rebuild policy would create a large synchronization/allocator research
  problem before the simpler cluster-granularity hypothesis is tested.

### Unreal Engine Lumen / Nanite background

Sources:

- https://dev.epicgames.com/documentation/unreal-engine/lumen-technical-details-in-unreal-engine
- https://dev.epicgames.com/documentation/en-us/unreal-engine/nanite-technical-details

Direct source claim:

- Lumen documents substantial RT acceleration-structure setup/update cost for
  deforming geometry.
- Nanite/Lumen production paths use their own fallback/representation choices.

Repository inference:

- AAA engines reinforce that dynamic RT geometry needs explicit representation
  policy rather than a universal rebuild strategy.

Why this is background only:

- a fallback/proxy representation is not equivalent to Lane J's shared exact Hit
  contract. Lane J cannot adopt a quality-reduced proxy merely because it is
  practical in another engine.

## Candidate-family comparison

| family | representation / topology update | allocation + peak-lifetime behavior | traversal / exact Hit | locality and synchronization | J001 disposition |
| --- | --- | --- | --- | --- | --- |
| object-local HWRT rebuild | changed object's ordinary triangle BLAS; full BUILD on topology/count change | AS destination + build scratch; resize may overlap old/new; geometry upload; optional compaction adds extra lifetime/copy | hardware triangle traversal; exact semantics can be preserved | object-local, but whole object rebuild; TLAS/instance reference work remains | **incumbent control** |
| hardened transient LBVH | monolithic object-local GPU-built BVH | small object-local builder payload plus static-HWRT integration lifetime already hardened in G | software exact triangle traversal + static/dynamic merge | whole changed object rebuild, regular GPU construction | **existing mechanism control/candidate** |
| clustered two-level BVH | object -> bounded spatial cluster -> exact triangle micro-hierarchy; dirty clusters rebuild, small upper hierarchy refit/rebuild | persistent cluster descriptors/ownership + dirty-cluster scratch; splits/merges can overlap pages | upper cluster BVH then conservative micro-BVH / exact triangle refinement | update cost can scale with dirty clusters; extra traversal level/divergence | **primary structurally-different candidate** |
| arbitrary dirty-subtree BVH | persistent monolithic BVH with changed leaves/subtrees replaced and ancestors refit | fine-grained node allocator/free list; fragmented old/new subtree overlap | direct exact BVH traversal | potentially excellent locality, but dependency propagation and GPU allocator/sync complexity are high | reject for J003; reconsider only if clustered prototype shows granularity is the right axis but cluster boundaries dominate |
| partial reconstruction via grid-derived hierarchy | grid/region ownership plus partial BVH rebuild | persistent grid + hierarchy; changed-region data | exact if leaves retain exact triangles | locality-aware, but region maintenance required | reject for J003; weaker fit than cluster candidate and risks grid failure modes |
| object-local paged/hashed cells | object-local sparse pages/cells containing primitive references | page/hash tables + duplicated references; allocator/pool pressure | DDA/hash traversal then exact triangle tests | removes world-size dependency but not triangle-to-cell amplification | reject |
| sorted two-level grid | sorted cell reference stream | large pair stream + radix scratch | DDA/cell traversal + exact triangle tests | global/object sort and empty-cell traversal | reject; Lane F already exposes the mechanism failure |
| occupancy/voxel/SDF broad phase + exact refinement | coarse occupancy plus a second exact triangle structure/list | broad-phase payload **plus** exact payload unless it replaces useful work | exact only after triangle refinement | can cull empty space, but adds another synchronization/traversal layer | reject for J003 absent evidence that Split-RC rays are broad-phase bound |
| H-PLOC/PLOC++ full rebuild | alternative monolithic BVH builder | full-builder scratch/output | exact BVH traversal | highly GPU-parallel but full object touched | research reference; not separate candidate in this lane |
| vendor CLAS / Cluster BLAS | hardware cluster AS + upper BLAS | explicit cluster destination/scratch/pools | hardware exact triangle traversal | fine-grained GPU-driven build | architectural evidence only; unavailable as portable RADV mechanism |

## Retained candidate set

J002-J004 are intentionally limited to one new structural candidate plus the
required controls.

### New primary candidate: clustered two-level object-local BVH

Representation:

`Object -> cluster upper BVH -> conservative micro-BVH -> exact triangle`

The candidate is portable compute/software; it does **not** require
`VK_NV_cluster_acceleration_structure` or unreleased DXR functionality.

Initial frozen prototype shape:

- cluster maximum: **64 triangles**;
- target initial occupancy: **48 triangles**;
- spatially coherent deterministic object-local clustering;
- cluster IDs are stable until a deterministic split/merge changes them;
- each dirty cluster rebuilds its own conservative micro-hierarchy;
- exact ray/triangle refinement remains the source of final Hit;
- the upper hierarchy contains cluster AABBs only;
- if the cluster set is unchanged, dirty bounds propagate by ancestor refit;
- if a split/merge changes the cluster set, rebuild the much smaller upper
  hierarchy;
- no world/global structure may be mutated.

The 64-triangle scale is frozen before candidate timing. It is motivated by the
current cluster literature/sample scale, but no external performance number is
used as a repository prediction.

Required falsification counters include:

- dirty cluster count;
- rebuilt triangles / changed triangles;
- cluster count and occupancy;
- split/merge count;
- upper refit/rebuild work;
- persistent/transient/scratch bytes;
- old/new page overlap at reallocation;
- traversal node/cluster visits and exact triangle tests.

The candidate is expected to fail if high-churn mutations dirty most clusters,
if split/merge maintenance becomes allocator/synchronization dominated, or if
the extra hierarchy level materially harms traversal. Those are explicit
falsification outcomes, not reasons to tune the workload later.

### Controls

Formal same-run control set:

1. **Lane E object-local HWRT BLAS rebuild** — incumbent on the measured target.
2. **Lane E/B003-compatible object-local software rebuild** where practical.
3. **Lane G hardened transient LBVH** — existing full-rebuild mechanism.
4. **unchanged transient LBVH** — accounting/attribution control when useful.
5. **run-local vanilla/accounting control** required by the inherited harness.

For high-churn HWRT control, recurrent compaction is disabled unless J002
explicitly models it as a separate predeclared variant. Rebuilding then
compacting every topology step would add query/copy/synchronization work and is
not the low-latency incumbent policy. Any required destination growth and build
scratch remain counted.

## Rejected candidates

### Sorted/paged/hashed grid as primary

Object-local coordinates remove Lane F's large-world scale problem, but they do
not remove the demonstrated primitive-to-cell reference amplification. Removing
the global sort with hashing also does not remove duplicated references or
empty-cell traversal. No new evidence justifies spending J003 implementation
budget here.

### Approximate voxel/SDF final hit

Rejected by contract. It cannot replace exact Hit semantics.

### Voxel/occupancy broad phase plus exact refinement

Technically valid, but not retained. To remain exact it still needs exact
triangle ownership/refinement data, so it adds representation, memory, and
synchronization unless it eliminates enough exact traversal. The existing repo
evidence does not show that broad-phase empty-space rejection is the dominant
topology cost.

### Fine-grained arbitrary incremental subtree surgery

Architecturally plausible but not first. It requires a GPU-friendly persistent
node allocator, insertion/removal, parent dependency propagation, quality
control, and fragmentation accounting. The clustered candidate tests the same
core hypothesis—**do not rebuild unaffected topology**—with a bounded and more
auditable granularity.

### Vendor cluster APIs as the candidate

Rejected as an implementation dependency on the current target. NVIDIA's Vulkan
extension is vendor-specific and DXR Part 2 is still under development. Their
architecture is evidence for the portable prototype, not a portability
assumption.

### H-PLOC as a separate candidate

Deferred. It is a useful full-rebuild algorithmic reference, but a second
monolithic builder does not answer Lane J's primary structural question while
hardened LBVH already represents the full-rebuild class.

## J001 decision

Retain exactly one new structural candidate:

**clustered two-level object-local BVH with dirty-cluster rebuild and exact
triangle refinement.**

Retain Lane E HWRT rebuild and hardened transient LBVH as the two most important
run-local controls, plus the required software/vanilla/accounting controls.

No performance ordering is claimed. J002 must freeze the deterministic topology
workload and comparator contract before any candidate timing. J003 may implement
only this retained candidate and required controls. J004 is blocked on Lane I.


## Full comparison against Lane-J criteria

The short table above is only a disposition summary. This matrix records the
criteria required by Issue #20 for every serious family.

### Object-local HWRT rebuild

- **representation / hierarchy:** ordinary triangle BLAS owned by the changed
  object, referenced by TLAS.
- **topology mutation:** primitive count/index topology change requires BUILD,
  not E004-style UPDATE. Vulkan UPDATE requires primitive counts and indexed
  triangle indices to remain compatible with the original build.
- **GPU build/update:** geometry upload -> size query/capacity decision ->
  destination/scratch availability -> BLAS BUILD -> instance reference/bounds
  update -> TLAS work -> synchronization.
- **dirty granularity / locality:** object only, but all triangles in that object
  participate in BLAS rebuild.
- **allocation/reallocation:** object BLAS destination may need growth when
  primitive count changes; old/new overlap must remain live until safe release.
- **scratch:** implementation-reported build scratch is mandatory when nonzero.
- **persistent/transient/true peak:** persistent BLAS/TLAS plus geometry; build
  scratch transient; resize may overlap old destination, new destination,
  geometry, and scratch. J002 measures lifetime peak rather than final resident.
- **geometry upload:** changed object's exact triangle data only; unrelated
  geometry never uploads.
- **rebuild/refit/update:** BUILD for topology/count mutation; TLAS update/build
  is separately accounted. No UPDATE substitution is allowed when KHR update
  rules do not permit the changed topology.
- **compaction:** ALLOW_COMPACTION permits compacting copy only after build and
  compacted-size query. That adds query/copy/synchronization and source/dest
  overlap; recurrent compaction is therefore not the default low-latency
  control. If tested later it must be a separate frozen variant.
- **synchronization:** AS build/copy and subsequent tracing require explicit
  synchronization; it remains inside the boundary.
- **traversal/divergence:** hardware implementation-dependent; expected strongest
  trace path on the measured target, but no J001 performance assumption.
- **exact Hit / nearest/tie:** feasible with shared triangle semantics and
  canonical merge.
- **static+dynamic merge:** naturally compatible with Lane E object-local BLAS +
  TLAS ownership.
- **small high-churn:** fixed AS setup/dispatch/scratch may dominate.
- **large high-churn:** full-object build work scales with whole object even if
  mutation is spatially local.
- **frequent primitive-count changes / insert/remove / replacement:** supported
  by rebuild, but may force resize/reallocation and full build.
- **complexity:** moderate because Vulkan path already exists conceptually, but
  complete accounting is nontrivial.
- **global/God-object risk:** low if BLAS remains per object.
- **Lane F/G relation:** avoids sorted-grid amplification; unlike G's LBVH it
  delegates hierarchy layout/traversal to HWRT. Performance crossover remains
  unmeasured.

### Hardened transient LBVH

- **representation / hierarchy:** object-local full binary LBVH rebuilt from
  current exact triangles, with software exact traversal and static/dynamic
  merge.
- **topology mutation:** naturally consumes arbitrary current primitive set;
  primitive count and identity can change between builds.
- **GPU build/update:** current-frame geometry -> Morton/key generation ->
  radix/order work -> hierarchy build/bounds -> traversal.
- **dirty granularity / locality:** object-local but monolithic; unaffected
  subregions do not retain hierarchy work across topology updates.
- **allocation/reallocation:** compact object-local payload; count growth may
  resize geometry/key/node scratch.
- **scratch:** key/radix/node/bounds scratch is explicit.
- **persistent/transient/true peak:** Lane G already established exact lifetime
  accounting and closed the sparse integration blocker; J002 must reproduce
  this accounting for topology profiles.
- **geometry upload:** changed object geometry/current-frame data only.
- **rebuild/refit/update:** full rebuild on every topology step; no refit benefit
  for unchanged subregions.
- **synchronization:** builder stage dependencies and traversal readiness are
  explicit GPU synchronization costs.
- **traversal/divergence:** software BVH traversal; quality depends on builder
  and may diverge more than hardware traversal. No timing conclusion is carried
  from F/G.
- **exact Hit / nearest/tie:** already demonstrated feasible in G's deterministic
  semantic replay.
- **static+dynamic merge:** proven conceptually by G integration runtime.
- **small high-churn:** builder overhead is bounded and payload small in prior
  796-triangle evidence; very small object crossover is unknown.
- **large high-churn:** full rebuild cost grows with all primitives but GPU
  parallelism is strong.
- **frequent primitive-count changes / insert/remove / replacement:** natural
  full-rebuild input model.
- **complexity:** already implemented/hardened; lowest new implementation risk.
- **global/God-object risk:** low if kept as object-local backend.
- **Lane F/G relation:** direct retained control. G resolves memory, not timing.

### Clustered two-level object-local BVH

- **representation / hierarchy:** stable object -> cluster upper BVH -> bounded
  cluster micro-BVH -> exact triangles.
- **topology mutation:** changed triangles affect their cluster; insertions/removals
  may dirty, split, or merge bounded clusters. Stable clusters persist.
- **GPU build/update:** candidate-owned dirty classification/assignment, dirty
  micro-BVH rebuild, cluster-bound update, ancestor refit, and upper rebuild only
  when cluster set changes.
- **dirty granularity / locality:** bounded cluster granularity; local mutation
  can avoid rebuilding unrelated clusters.
- **allocation/reallocation:** persistent cluster descriptors/payload plus bounded
  cluster page growth; split/merge can require old/new overlap. All pools/reserved
  capacity count.
- **scratch:** dirty classification, local partition/build, upper refit/rebuild
  scratch are explicit.
- **persistent/transient/true peak:** more persistent metadata than monolithic
  LBVH is expected; J003 has a 1.25x hard memory eligibility ceiling and exact
  lifetime census.
- **geometry upload:** only changed object's canonical snapshot is shared across
  candidates; candidate-specific cluster staging is counted as preprocessing,
  not hidden setup.
- **rebuild/refit/update:** dirty cluster rebuild; upper refit if cluster set
  stable; upper rebuild on split/merge.
- **synchronization:** dirty classification -> local rebuild -> bounds ->
  upper-level maintenance creates more dependency stages than monolithic LBVH;
  this is a principal falsification risk.
- **traversal/divergence:** adds an upper cluster traversal level and potentially
  irregular per-cluster paths. Exact tests remain at triangle leaves.
- **exact Hit / nearest/tie:** feasible because cluster/upper structures are only
  conservative acceleration; final triangle tests and shared merge decide Hit.
- **static+dynamic merge:** changed object produces an exact dynamic hit stream
  compatible with the existing static/dynamic merge contract.
- **small high-churn:** likely vulnerable to fixed metadata/dispatch overhead;
  J002 deliberately includes 128 triangles.
- **large high-churn:** strongest intended case when high churn is spatially
  localized; global high-churn is an explicit falsification profile.
- **frequent primitive-count changes:** handled through deterministic cluster
  assignment and split/merge.
- **insertion/removal:** supported by the frozen J003 cluster ownership rules;
  allocator/synchronization costs remain visible.
- **large topology replacement:** may dirty nearly all clusters, degenerating
  toward a full rebuild plus metadata overhead. That failure is retained.
- **complexity:** medium/high but bounded; significantly lower allocator and
  dependency complexity than arbitrary subtree surgery.
- **global/God-object risk:** low because all cluster state is object-owned and
  no world-global index is introduced.
- **Lane F/G relation:** deliberately avoids triangle-to-cell reference
  amplification/global sorting from F and tests whether G's monolithic rebuild
  can be beaten by retaining unaffected local structure.

### Arbitrary incremental subtree rebuild/refit

- **representation / hierarchy:** persistent object-local BVH with mutable leaves,
  dirty subtrees, retained unaffected subtrees, ancestor refit.
- **topology mutation:** arbitrary insertion/removal requires leaf and internal
  topology edits plus quality policy.
- **GPU build/update:** dirty propagation, subtree selection, local reconstruction,
  parent rewiring/refit, allocator/free-list updates.
- **dirty granularity / locality:** finer than clusters in principle.
- **allocation/reallocation:** fine-grained persistent node allocation and
  fragmentation; old/new subtree overlap before parent publication/release.
- **scratch:** dirty queues, dependency/parent queues, subtree builders, allocator
  metadata.
- **persistent/transient/true peak:** difficult but measurable; fragmentation and
  allocator reserve are part of persistent/peak memory.
- **geometry upload:** changed object only.
- **rebuild/refit/update:** localized subtree rebuild + ancestors; larger rebuild
  needed when quality degrades.
- **synchronization:** high-risk due to parent/child dependencies, publication,
  free-list safety, and multi-stage propagation.
- **traversal/divergence:** can remain direct exact BVH traversal; quality can
  degrade if reconstruction policy is weak.
- **exact Hit / nearest/tie:** feasible.
- **static+dynamic merge:** compatible if object-local.
- **small high-churn:** bookkeeping may dominate.
- **large local high-churn:** potentially excellent if dirty-subtree selection is
  stable.
- **global replacement:** converges toward whole-tree reconstruction plus
  persistent allocator cost.
- **primitive-count changes / insertion/removal:** core strength but also the
  hardest correctness path.
- **complexity:** highest among serious software candidates.
- **global/God-object risk:** low if object-owned, but allocator/shared queues can
  accidentally become global; prohibited by Lane J.
- **Lane F/G relation:** avoids F's grid amplification and G's whole-object
  rebuild, but introduces a larger unvalidated synchronization/allocator problem.
  Rejected from J003 until cluster granularity is falsified.

### Object-local paged/hashed cells

- **representation / hierarchy:** sparse object-space cell/page hash with triangle
  references and optional per-page micro-hierarchy.
- **topology mutation:** update/rebuild touched pages/cells; insert/remove
  references.
- **GPU build/update:** overlap enumeration -> page/hash allocation -> reference
  writes -> optional page micro-build.
- **dirty granularity / locality:** spatial page/cell.
- **allocation/reallocation:** page pools/hash growth; reference lists can expand
  sharply for large triangles.
- **scratch / transient:** overlap/reference stream and allocation metadata.
- **true peak:** pool reserve plus old/new page/reference overlap.
- **geometry upload:** changed object only, but references may amplify geometry.
- **rebuild/refit/update:** touched pages only in ideal local case.
- **synchronization:** hash/page allocation and variable-length reference writes
  require atomics/prefix or equivalent staging.
- **traversal/divergence:** object-local DDA/hash plus micro traversal; empty-cell
  steps remain possible.
- **exact Hit / tie:** feasible only with exact triangle refinement.
- **static+dynamic merge:** compatible if object-local.
- **small high-churn:** fixed hash/page overhead can dominate.
- **large high-churn:** global replacement can touch many pages.
- **primitive-count change / insert/remove:** natural if allocator is robust.
- **large topology replacement:** reference regeneration can approach full
  rebuild.
- **complexity:** medium/high.
- **global/God-object risk:** medium if page allocator is shared globally; Lane J
  would require object-local ownership.
- **Lane F/G relation:** object coordinates fix world-scale/vertical sensitivity
  but **do not** fix Lane F's key failure: primitive-to-cell reference
  amplification and empty-cell traversal. Rejected.

### Broad phase + exact triangle refinement

- **representation / hierarchy:** coarse occupancy/voxel/SDF-like conservative
  broad phase plus exact triangle representation/refinement.
- **topology mutation:** update broad phase and exact refinement structure/list.
- **GPU build/update:** occupancy generation and exact-structure update are both
  recurring unless one can be reused.
- **dirty granularity / locality:** potentially coarse local regions.
- **allocation/reallocation:** dual representations increase persistent and
  transient lifetime unless broad phase replaces substantial exact work.
- **scratch / true peak:** occupancy build scratch plus exact representation and
  old/new overlap.
- **geometry upload:** changed object; candidate preprocessing additionally
  derives occupancy.
- **synchronization:** broad-phase build must complete before traversal; exact
  refinement still follows.
- **traversal/divergence:** broad phase can cheaply reject empty regions but adds
  another branch/lookup layer for occupied regions.
- **exact Hit / nearest/tie:** only valid when final triangle intersection and
  shared tie rules remain authoritative; approximate final hits are forbidden.
- **static+dynamic merge:** feasible.
- **small high-churn:** extra representation likely poor.
- **large sparse/local high-churn:** could be useful only if broad-phase rejection
  eliminates substantial exact traversal.
- **primitive-count changes / insert/remove:** possible but both structures need
  maintenance.
- **large replacement:** broad and exact rebuilds both recur.
- **complexity:** medium/high.
- **global/God-object risk:** low if object-local.
- **Lane F/G relation:** risks adding a second structure without addressing the
  measured dominant cost. No repo evidence shows dynamic exact traversal is the
  bottleneck relative to build/update, so it is rejected from J003.
