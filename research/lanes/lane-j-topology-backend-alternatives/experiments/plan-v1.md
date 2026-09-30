# Lane J plan v1 — topology-changing object-local backend alternatives

Status: **frozen initial research plan / no candidate implementation yet**  
Issue: #20  
Base: `research@76f65f8944aba8405dce5d386161df2540957349`  
Parallel dependency: Issue #19 / Lane I

This plan is frozen before any Lane-J candidate timing. J001 retained exactly one
new structural candidate. Any later amendment must be versioned and committed
before the affected evidence is collected.

## Retained architecture set

New structural candidate:

- `clustered-two-level-bvh`

Run-local controls:

- `lane-e-object-local-hwrt-rebuild`;
- `lane-e-object-local-software-b003-rebuild` where practical;
- `hardened-transient-lbvh`;
- `transient-lbvh-unchanged` when attribution requires it;
- `vanilla-accounting-control`.

No sorted grid, global hash/grid, approximate-hit representation, H-PLOC
production candidate, or arbitrary dirty-subtree implementation is in J003.

## Immutable cross-lane contracts

Every experiment preserves:

- A001 GPU visibility-driven Split RC producer;
- A001 natural append ordering;
- HWRT/TLAS primary-traversal disposition outside candidate-local work;
- B003 segment-DDA/hash + conservative quantized Micro BVH8 fallback where used;
- C001 per-probe sparse hash;
- shared exact Hit, nearest-hit, and tie semantics;
- Lane E object-local ownership semantics;
- unrelated static world and unrelated objects remain immutable.

Candidate-internal representation/traversal may differ only inside the changed
object backend and its required static/dynamic merge.

---

# J002 — deterministic topology workload and comparator contract

J002 is a workload/contract experiment, not a winner-selection experiment.

## H002 reuse and correction

Reuse from H002:

- deterministic primitive-count-changing sequence;
- canonical workload digest;
- explicit changed object identity;
- immutable unrelated owner IDs;
- explicit zero for inapplicable stages;
- allocation-lifetime-derived true peak resident memory.

Do **not** reuse H001's one-way transition behavior. J002 materializes complete
geometry snapshots for every step and verifies that every consecutive measured
transition changes both geometry identity and primitive count.

A transition is valid only when:

`snapshot_digest[i] != snapshot_digest[i-1]`

and:

`primitive_count[i] != primitive_count[i-1]`.

The harness fails closed before timing if either condition is false.

## Frozen primitive-count cycle

All profiles use the inherited H002 factor cycle:

`[1.00, 1.25, 0.75, 1.10, 0.90, 1.30, 0.80, 1.05]`

Every adjacent pair changes primitive count.

Master topology seed:

`0x4A303032` (`J002`)

Profile-specific seeds are derived only from the master seed and a fixed profile
index. Candidate code never generates or chooses topology.

## Frozen workload profiles

Five profiles are retained. This independently exposes fixed overhead,
representative behavior, dirty-region locality, large-object behavior, and a
large/global falsification case without creating an architecture-tuning sweep.

| profile | base triangles | replacement fraction | locality | purpose |
| --- | ---: | ---: | --- | --- |
| `small-global-high` | 128 | 50% | global deterministic | small high-churn fixed-overhead case |
| `medium-global-representative` | 796 | 25% | global deterministic | continuity with H002/F/G |
| `medium-local-high` | 796 | 50% | one deterministic object-space region | test exploitable dirty locality |
| `large-global-high` | 8192 | 50% | global deterministic | falsify locality-dependent candidate |
| `large-local-high` | 8192 | 50% | one deterministic object-space region | intended large/local clustered regime |

The 8192-triangle profiles are stress workloads, not a production-distribution
claim.

For local profiles, the changed region is selected from canonical geometry by a
candidate-independent object-space Morton region derived from the step seed. It
is not defined by candidate cluster boundaries.

## Canonical geometry identity

J002 materializes the complete topology sequence before candidate construction.

Each step records:

- object ID;
- primitive count;
- stable 64-bit primitive IDs for retained triangles;
- IDs removed, inserted, and topology-replaced;
- exact vertex/index bytes;
- object-space bounds;
- topology seed;
- geometry-buffer SHA-256;
- producer-stream SHA-256;
- complete snapshot SHA-256.

All variants consume these same immutable snapshots. Candidate-specific geometry
generation is forbidden.

The medium source should reuse the existing representative dynamic object used
by H/F/G when practical. Small/large profiles must be deterministic derivations
of the same canonical source/generator and frozen in the J002 manifest before
candidate timing.

## Ownership contract

Mutable:

- `topology-object-0`

Immutable:

- `static-world`;
- `unrelated-object-0`;
- every other object-local owner.

For every transition, mutation logging rejects allocate, reallocate, upload,
build, rebuild, update, write, release, or ownership change against an immutable
owner. Reads are allowed.

## Producer, Hit, storage identity

Every variant must report matching digests for:

- A001 producer input and natural append stream;
- query/ray sequence;
- exact geometry snapshot;
- exact Hit contract version;
- C001 storage stream/state.

No candidate may reorder the producer stream for locality. Candidate-internal
object-local build ordering is allowed only when its cost remains inside the
candidate boundary.

## Independent exact reference

Correctness uses:

1. brute-force/reference exact ray/triangle intersection over
   `topology-object-0`;
2. unchanged static-world reference;
3. shared nearest-hit/tie merge;
4. expected C001 storage/resolve semantics.

A candidate never validates itself against its own hierarchy.

Required zero-error fields:

- `visibility_mismatch_count`;
- `producer_semantic_error_count`;
- `hit_mismatch_count`;
- `nearest_hit_tie_mismatch_count`;
- `traversal_runtime_error_count`;
- `storage_failure_count`;
- `immutable_owner_mutation_count`.

## Common recurring boundary

Every variant emits every common field. Non-applicable stages are numeric zero,
never omitted.

Required timing/accounting fields:

- `geometry_prepare_wall_us`;
- `allocation_reallocation_wall_us`;
- `geometry_upload_gpu_us`;
- `candidate_preprocess_gpu_us`;
- `build_rebuild_gpu_us`;
- `refit_gpu_us`;
- `compaction_gpu_us`;
- `instance_tlas_update_gpu_us`;
- `traversal_gpu_us`;
- `synchronization_wall_us`;
- `merge_gpu_us`;
- `storage_gpu_us`;
- `resolve_gpu_us`;
- `complete_gpu_us`;
- `complete_update_wall_us`.

Required memory fields:

- `persistent_bytes`;
- `transient_bytes`;
- `scratch_bytes`;
- `old_new_overlap_bytes`;
- `true_peak_resident_bytes`.

The common boundary starts before recurrent next-snapshot geometry preparation
or allocation and ends only after traversal, static/dynamic merge, storage,
resolve, and required synchronization.

Candidate-specific detail fields may be added but may not replace common fields.

## Allocation lifetime contract

Every device allocation records:

- unique allocation ID;
- owner ID;
- byte size;
- allocation class;
- birth phase;
- death phase;
- setup-only/persistent/transient/scratch classification.

`true_peak_resident_bytes` is the maximum simultaneous live-byte sum over the
relevant setup + transition lifetime. Old/new overlap during resize counts until
the old resource can actually be released. Persistent pools are allowed, but
their full reserved bytes count.

## Setup boundary

Allowed setup:

- immutable static-world construction;
- immutable unrelated-object construction;
- reusable pipeline/descriptor creation;
- candidate metadata whose persistent capacity is fully counted.

Forbidden setup hiding:

- prebuilding future topology snapshots;
- preprocessing future cluster membership;
- pre-uploading future changed geometry;
- uncounted preallocation of candidate output/scratch;
- recurrent candidate sorting/grouping moved into setup.

## J002 exit gates

Before J003:

- all five profile manifests exist;
- every transition changes count and snapshot digest;
- workload digests reproduce;
- exact reference outputs reproduce;
- immutable-owner mutation validation passes;
- common fields are schema-validated;
- lifetime peak tests include realloc overlap;
- no candidate timing has influenced any profile.

---

# J003 — retained prototype and deterministic gates

J003 implements only `clustered-two-level-bvh` plus the minimum comparators
required for semantic/accounting parity. Formal performance ranking is still
forbidden.

## Frozen clustered candidate structure

Representation:

`object -> cluster upper BVH -> conservative per-cluster micro-BVH -> exact triangles`

Prototype constants:

- max triangles per cluster: **64**;
- target initial occupancy: **48**;
- low-occupancy merge trigger: **24** triangles;
- initial clusters: deterministic object-space Morton order, partitioned toward
  target occupancy;
- insertion assignment: centroid goes to the non-full cluster with smallest
  AABB surface-area expansion, stable cluster-ID tie break;
- overflowing dirty cluster is locally repartitioned by deterministic
  object-space Morton median until every cluster is <=64;
- a cluster below 24 may merge only with the stable nearest cluster when combined
  size is <=48, stable cluster-ID tie break;
- unchanged clusters retain payload/allocation identity;
- dirty clusters rebuild their conservative micro-BVH;
- if cluster membership/count is unchanged, changed cluster bounds propagate by
  ancestor refit;
- split/merge causes rebuild of the much smaller upper cluster BVH;
- no global triangle-to-cell reference stream and no per-transition global
  triangle sort.

Initial one-time clustering is setup. Every transition-time insertion assignment,
local sort/repartition, split/merge, upper refit/rebuild, allocation, and
synchronization stays inside the recurring boundary.

## Candidate-specific counters

Every transition records:

- `cluster_count`;
- `dirty_cluster_count`;
- `changed_triangle_count`;
- `rebuilt_triangle_count`;
- `unaffected_cluster_rebuild_count`;
- `split_count`;
- `merge_count`;
- `upper_refit_node_count`;
- `upper_rebuild_node_count`;
- cluster occupancy min/median/max;
- `cluster_node_visits`;
- `micro_node_visits`;
- `exact_triangle_tests`.

`unaffected_cluster_rebuild_count` must be zero for the local-update claim.

## Deterministic hard gates

Every profile and comparator must satisfy:

- exact correctness PASS;
- visibility mismatch = 0;
- producer semantic error = 0;
- Hit mismatch = 0;
- nearest-hit/tie mismatch = 0;
- traversal runtime error = 0;
- storage failure = 0;
- immutable-owner mutation = 0;
- memory/lifetime census complete;
- no hidden setup cost;
- every measured transition actually changes geometry;
- structural counters complete.

Clustered-candidate memory eligibility:

- persistent bytes <= **1.25x** same-run Lane-E HWRT rebuild comparator;
- true peak resident bytes <= **1.25x** same-run Lane-E HWRT rebuild comparator;
- no monotonically growing allocation over repeated cycles unless it is a
  declared bounded persistent pool;
- after a full repeated cycle, live ownership returns to the declared persistent
  baseline.

The 1.25x ceiling is frozen from the existing Lane-E-style memory discipline.
Timing cannot rescue a correctness or hard-memory failure.

## Structural falsification

J003 may report deterministic work counts and bytes, but no speed winner.

If global high-churn dirties nearly all clusters, keep that evidence. If small
objects are metadata dominated, keep it. If split/merge creates large old/new
overlap, count it. Do not tune away a failing profile after seeing candidate
behavior.

J003 ends with one of:

- clustered candidate eligible for J004;
- clustered candidate rejected before timing;
- candidate infeasible under exact/shared contracts.

---

# J004 — formal crossover, gated by Lane I

J004 is forbidden until Issue #19 / Lane I publishes I004.

## Gate import

After Lane I completes, but **before any J004 target candidate timing**, commit a
versioned J004 gate record containing:

- Lane-I result commit/document;
- reusable safe timing protocol, if any;
- smallest demonstrated effect size;
- J004 primary axis;
- promotion improvement threshold;
- guarded secondary-axis threshold;
- warmup/batch/repeat/order policy;
- uncertainty/repeatability test;
- rerun budget.

The promotion threshold may not claim an effect smaller than Lane I demonstrated.

Examples:

- if Lane I demonstrates 5%, J004 may freeze 5% or larger;
- if only 20% is demonstrated, a 10% superiority claim is forbidden;
- if timing is unsuitable, J004 does not run and Lane J may end
  `measurement-limited`.

No numeric promotion threshold is guessed before Lane I evidence.

## Formal same-run variants

When permitted:

- Lane E object-local HWRT rebuild;
- Lane E/B003 object-local software rebuild where practical;
- hardened transient LBVH;
- clustered two-level BVH if J003 retained it;
- unchanged transient LBVH when needed for attribution;
- vanilla/accounting control.

Historical E/F/G timing is context only.

## Equality constraints

Formal rows share:

- topology profile and transition index;
- exact geometry snapshot;
- primitive IDs/count;
- A001 producer stream/order;
- ray stream;
- exact Hit/tie semantics;
- C001 storage path;
- static-world state;
- update boundary;
- allocation-lifetime accounting.

No profile may be added, removed, or made candidate-specific after target timing
starts. No averaging may hide a workload-specific loss.

The J003 1.25x memory eligibility remains a hard J004 gate.

## Conditional outcomes

A backend may be retained only for a predeclared workload class where it passes
the frozen J004 gate. A class-conditional result must use observable properties
already frozen in J002 (object size, dirty fraction, local/global region).
Post-hoc selector thresholds from winning timings are forbidden.

---

# J005 — integration replay

Only a J004-retained candidate reaches J005. If J004 is measurement-limited,
there is no timing-based promotion replay.

Integrate the retained topology backend inside Lane E ownership semantics and
replay:

- static path unchanged;
- rigid Lane-E transform-only path unchanged;
- stable-topology deforming Lane-E UPDATE path unchanged;
- topology-changing/high-churn uses the retained J backend only in its accepted
  class;
- A001 semantics;
- exact Hit/tie semantics;
- C001 storage;
- relevant sparse/dense/large/vertical Split-RC stress;
- persistent/transient/scratch/true-peak memory;
- timing only when Lane I/J004 permits.

Integrity checks:

- static-world mutation count = 0 during topology update;
- unrelated-object mutation count = 0;
- rigid backend selection unchanged;
- deforming backend selection unchanged;
- producer semantic errors = 0;
- Hit mismatches = 0;
- storage failures = 0.

## Valid final outcomes

Exactly one final disposition is recorded:

1. **conditional topology backend accepted**
2. **Lane E rebuild retained**
3. **hardened LBVH retained as topology backend**
4. **deterministic candidate rejected before timing**
5. **measurement-limited**

A positive Lane-J result remains topology-changing/high-churn scoped.

---

# Safety and repository discipline

Forbidden:

- `power_dpm_force_performance_level`;
- `profile_peak`;
- forced GPU clocks/power states;
- privileged clock/power sysfs;
- outlier deletion;
- fastest-subset selection;
- post-hoc thresholds;
- candidate-favorable workload edits;
- recurrent work moved into setup.

Normal iterations commit directly to
`research-lane-j-topology-backend-alternatives`. No routine PR and no wholesale
merge from Lane I or older lanes.
