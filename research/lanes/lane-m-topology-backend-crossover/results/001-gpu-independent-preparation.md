# M001 GPU-independent preparation

Status: **COMPLETE — execution frozen; accepted target timing not started**

Issue: #25

## Decision

Lane M is ready for target validation. Accepted target timing has not started.

The preparation reuses the qualified J004 complete recurring boundary instead
of creating independent benchmark implementations. Lane M adds a thin adapter
for the existing Lane J clustered transition/layout implementation so Lane E,
Lane G, and Lane J candidates share the same producer, traversal merge,
storage, synchronization, timestamp, and allocation-accounting boundary.

## Frozen workload

M001 uses the deterministic J002 topology campaign: representative 796/25%
global topology change, 8192/50% global high churn, 8192/50% local high churn,
and a repeated-step stable/no-change guard.

Actual topology mutation is derived from primitive IDs/counts and geometry
digests for every transition. Mutating timed samples require exactly 16 updates;
the stable guard requires zero.

## Instrumentation and memory

Validation fails closed on exact Hit/tie, visibility, producer, traversal,
storage, immutable-owner, workload, geometry/input, resolved-output,
allocation-lifetime, and device/driver/API/timestamp provenance gates.

The shared B002 Vulkan context now tracks allocation/free/live allocation census
in addition to residency and lifetime peaks. The hard memory gate is
persistent max <=1.25x and true-peak max <=1.25x with complete lifetime
accounting, including the conditional clustered-vs-LBVH direct comparison.

Validation records the exact J002 manifest, producer stream SHA-256, scene
SHA-256, source fingerprint, and device provenance. Formal startup rechecks
those input SHA values and refuses timing after drift.

## Timing freeze

Lane L heavy-boundary capability is imported unchanged: dual independent
contexts, GPU timestamp primary, CPU wall diagnostic only, 4 warmup + 12
measured pairs, 8 fresh-process blocks, 16 transitions per role sample, frozen
AB/BA ordering, one-second settle, no sample exclusion, and zero rerun budget.

The analysis uses the 20% threshold, fresh-control noise envelope, fresh-process
direction, AB/BA direction, and >=0.75 pair-direction gates. Sub-20% evidence is
never converted into a ranking.

## Self-review

Before freeze, two gaps were corrected: formal startup now proves validation
and formal input SHA identity, and the conditional clustered-vs-LBVH direct
comparison now applies the same 1.25x memory hard guard.

A duplicate Lane-M formal process was rejected in favor of extending the
qualified J004 source at build time.

## Execution state

No accepted target timing was run. The GitHub-connected environment cannot
execute the target checkout, local out/ materialization, or Vulkan runtime.
The next target-machine step is build/unit/contract preflight followed by
validation. Formal timing is allowed only after that validation passes unchanged.
