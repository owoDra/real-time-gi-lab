# M001 — topology backend crossover

Status: **GPU-independent preparation frozen; accepted target timing has not started**

Issue: #25

## Research question

Determine the object-local backend for topology-changing / high-churn dynamic
geometry under one identical complete recurring boundary.

Compared mechanisms: Lane E incumbent object-local rebuild, Lane G hardened
transient LBVH, and Lane J clustered two-level object-local BVH. Historical
timing from those lanes is context only.

## Workload freeze

M001 reuses qualified deterministic J002 topology materialization:

- topology-changing-object-local: medium-global-representative, 796 base
  primitives, nominal 25% global replacement;
- high-churn-global: large-global-high, 8192 base primitives, nominal 50%;
- high-churn-local: large-local-high, 8192 base primitives, nominal 50%;
- stable-no-change-guard: repeated frozen step-00 with no update/rebuild.

Every transition is verified from actual primitive IDs/counts and geometry
digests. Mutating scenarios must report one real topology mutation and one
required backend update per transition; the stable guard must report zero.

## Common recurring boundary

All three backends execute through the qualified J004 complete-boundary runtime.
Lane M adds only a thin clustered adapter and M001 identity instrumentation.

The boundary includes geometry/topology preparation, allocation/reallocation,
upload, local rebuild/refit/update, traversal metadata, traversal, exact Hit
merge, storage/update/resolve, synchronization, complete GPU time, CPU-wall
diagnostics, and lifetime memory. Future-state prebuild and moving recurrent
work into setup are forbidden.

## Gates

Before accepted timing: exact Hit/tie, visibility, producer, traversal, storage,
static/unrelated ownership, workload identity, geometry/input identity,
resolved-output identity, allocation lifetime, and device/driver/API/timestamp
provenance must all pass.

Memory hard guard: persistent ratio max <= 1.25, true-lifetime-peak ratio max
<= 1.25, and complete allocation lifetime accounting.

Lane L capability is imported unchanged: GPU timestamp primary, CPU wall
diagnostic only, 20% threshold, 4 warmup + 12 measured pairs, 8 fresh-process
blocks, 16 complete transitions, frozen AB/BA counterbalancing, one-second
settle, no sample exclusion, and zero rerun budget.

Candidate/control <= 0.80 with effect beyond fresh-control noise and all
direction gates passes improvement. Ratio >= 1.20 with the same gates is a
detected regression. Everything else is <20% difference / measurement-limited
and is not ranked.

If both candidates qualify against the incumbent, a prospectively frozen
LBVH-control versus clustered comparison uses the same 20% and 1.25x gates.

## Execution policy

Accepted target timing has not started. Allowed order is build/unit/contract
checks, target validation, then formal timing only if validation passes without
source or input changes. GitHub Actions and routine PRs are not used.
