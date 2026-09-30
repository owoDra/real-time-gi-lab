# E001 — Lane E timing revalidation gate

Status: **frozen before any target candidate timing**

This prospective gate revalidates the already accepted Lane E object-local ownership/update architecture; it does not redesign it.

## Imported evidence

- Lane E final architecture: `research-lane-e-dynamic-geometry@30590185fbe28ea8e726b4f0ba8d6c4dfc3214c0`; E005 result blob `58cdfe1d7e5f781e50d2b8bd873fedbfccbb1b19`.
- Lane L measurement commit: `b8bb76f728ee329cf4daef5855a05972757072f6`.
- Lane L target result blob: `acb84da701ea786ee6231368fc625ab5178ca3c7`.
- Lane L final result blob: `136178825f24aeab5d60a34a25329ec52158ae34`.
- Lane K is context only here. Its 5% floor is explicitly **not transferable** to this heavy boundary.

Accepted environment is `dual-context`. GPU timestamp is primary. CPU wall is diagnostic / health / provenance only.

## Frozen sample shape

- 16 complete recurring-boundary transitions per timed sample.
- 4 warmup pairs + 12 measured pairs per fresh process.
- 8 fresh-process blocks.
- block start order: `AB, BA, AB, BA, BA, AB, BA, AB`; pair order alternates inside each process.
- 1 second settle before each process.
- accepted timing disables validation layers.
- sample exclusion forbidden; instability rerun budget 0; completed-campaign rerun budget 0.
- interrupted partial processes are not evidence; resume may execute only predeclared process IDs that never completed.

## Fresh same-run controls

Historical E005 timing is context only. Every scenario and traversal track gets a fresh control-vs-control campaign using the same heavy boundary and two independent Vulkan contexts/runtimes. Its GPU noise envelope is the maximum of absolute process-median ratio, process-median span ratio, and within-process AB/BA order-bias ratio.

The architecture comparison then uses the same process shape. A formal effect must be at least 20%, strictly exceed the matching fresh control envelope, keep all eight process medians directional, keep both AB and BA stratum medians directional in every process, and retain at least 0.75 directional measured pairs per process.

## Compared classes

- moving-rigid / HWRT: pre-E world-space dynamic maintenance vs immutable object-local BLAS + instance transform + TLAS UPDATE.
- moving-rigid / software: pre-E world-space membership/hierarchy maintenance vs object-local StrataBrick + conservative quantized Micro BVH8 + instance-only update.
- stable-topology deforming / HWRT: pre-E world-space maintenance vs changed object-local geometry/BLAS only + TLAS UPDATE.
- stable-topology deforming / software: pre-E world-space maintenance vs changed object-local hierarchy only.
- static, camera-motion and light-motion are guard classes and may only establish a >=20% regression or remain sub-20% / measurement-limited.

Primitive-count-changing topology and topology-backend selection are excluded.

## Complete recurring boundary

Both variants count geometry preparation; allocation/reallocation; upload; BLAS/local-hierarchy update or rebuild; TLAS/instance update; traversal; exact Hit merge; storage/resolve; synchronization; complete GPU time; complete CPU wall; persistent/transient/scratch memory; old/new overlap; and true peak memory. Inapplicable work is explicit zero. Recurrent work may not move into setup and future-state/future-snapshot prebuild is forbidden.

## Correctness gate

Before timing: exact Hit mismatch, nearest-hit/tie mismatch, visibility mismatch, producer semantic error, traversal runtime error, storage failure, static-owner mutation and unrelated-owner mutation must all be zero. Workload identity, resolved-output identity, geometry/input digest, allocation-lifetime accounting and device/driver/API/timestamp provenance must match/pass.

B001 candidate search must continue through `best_t + tolerance`; the J004 exact-tie pruning correction must not regress.

## Memory gate

Bookkeeping that would add GPU work is kept outside the timed boundary. Persistent, transient, scratch, old/new overlap, true peak, allocation count and allocation lifetimes are retained. The historical E005 safety guard remains prospective: persistent and true-peak ratios must each be <=1.25x same-run control. Exceeding either is a memory regression; otherwise memory is improvement only when persistent and true peak are both non-worse and at least one is strictly lower, else neutral.

## Performance decision

Lane L's 20% heavy-boundary floor is authoritative:

- detected >=20% improvement;
- `<20% difference / measurement-limited`;
- detected >=20% regression.

Sub-20% differences are diagnostic only and cannot promote or falsify Lane E. A negative timing result alone does not invalidate Lane E correctness/ownership semantics. Correctness failure and hard memory regression remain independent decision axes.

## Refreeze rule

Compile/test/validation defects found before the first accepted target timing sample may be fixed and this gate may be versioned/refrozen. Once accepted target timing begins, workload, control, threshold, sample shape, decision mapping and rerun policy are immutable.


## Frozen process and artifact contract

The accepted campaign contains 160 fresh timing processes:
5 scenarios × 2 traversal tracks × 8 blocks ×
(same-variant control + architecture comparison).

The runner must retain every raw row and emit:

- `e001-config.json`
- `e001-source-provenance.json`
- `e001-input-provenance.json`
- `e001-progress.json`
- `e001-validation-summary.csv`
- `e001-raw.csv`
- `e001-process-summary.csv`
- `e001-memory-summary.json`
- `e001-host-observations.json`
- `e001-devices.json`
- `e001-summary.json`
- `e001-vulkaninfo-summary.txt`

A failure before the first measured row may be fixed and re-frozen. If a
process has emitted any measured row and is then interrupted, the campaign is
invalid and is not rerun. Completed processes and completed campaigns are never
rerun.
