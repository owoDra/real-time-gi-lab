# L001 — heavy-boundary same-variant calibration plan

Status: **FROZEN BEFORE TARGET EXECUTION**
Issue: #24
Branch: `research-lane-l-heavy-boundary-calibration`
Parent evidence: J004 / Issue #23
Downstream dependency: Lane E timing revalidation / Issue #22

## Research question

L001 does not rank architecture candidates.

It asks whether the unchanged J004 heavy recurring boundary can satisfy the
already-frozen J004 same-variant GPU control-health gate when the A/B
measurement environment changes.

The two required environments are:

1. `dual-context`
   - two independent Vulkan contexts;
   - two independent `FormalRuntime` instances;
   - same control variant on both roles;
   - reproduces the J004 pairing boundary.

2. `single-context-independent-runtime`
   - one Vulkan context/device/queue environment;
   - two independent `FormalRuntime` instances;
   - each runtime owns independent resources and state;
   - same control variant on both roles;
   - no resource aliasing between A and B.

No candidate backend is timing-eligible in L001.

The optional single-runtime repeated-baseline diagnostic is **not included** in
L001. Adding it after target data is forbidden.

## Imported workload boundary

L001 imports the J004 v7 workload and correctness contract without modification:

- all five J002 profiles:
  - `small-global-high`;
  - `medium-global-representative`;
  - `medium-local-high`;
  - `large-global-high`;
  - `large-local-high`;
- eight topology snapshots in the frozen order for every profile;
- accepted A001 producer stream and ray order;
- B001 exact Hit/tie semantics, including candidate eligibility through
  `best_t + max(HIT_ABS_TOL, abs(best_t) * HIT_REL_TOL)`;
- C001 storage semantics;
- 16 complete topology transitions per timed sample;
- no future-snapshot prebuild;
- no recurrent work moved into setup.

The implementation reuses the frozen J004 `FormalRuntime` source semantics.
J004 itself is not edited or rerun.

## Control families

Both environments independently calibrate:

- primary: `lane-e-object-local-hwrt-rebuild`;
- software: `lane-e-object-local-software-b003-rebuild`.

For each timed pair, role A and role B use the same control family.

## Correctness and provenance gate

Before any timing process, every required
`environment × profile × track` validation must pass.

Required zero-error fields for both roles:

- visibility mismatch;
- producer semantic error;
- exact Hit mismatch;
- nearest-hit/tie mismatch;
- traversal runtime error;
- storage failure;
- immutable/static-owner mutation.

Required identity checks:

- frozen J002 contract blob;
- frozen profile topology digest;
- every snapshot primitive count and geometry digest;
- producer stream and scene identity;
- A/B resolved output digest equality;
- target device/driver/API/timestamp-period provenance;
- allocation/lifetime ownership validation.

A failure blocks all L001 timing.

## Allocation/lifetime evidence

Timing evidence and allocation/lifetime evidence are deliberately separated.

For `dual-context`, each runtime has a context-local allocation counter.

For `single-context-independent-runtime`, the context allocation counter is
necessarily shared. Therefore role-local memory quantities from timed samples
are **not** decision evidence in L001.

Instead, the pre-timing validation pass records live allocation bytes:

- before either runtime;
- after runtime A creation;
- after runtime B creation;
- after runtime B destruction;
- after runtime A destruction.

The required invariant is:

- A creation increases live allocation;
- B creation independently increases live allocation again;
- destroying B returns exactly to the post-A level;
- destroying A returns exactly to the pre-runtime baseline.

This proves independent allocation lifetime without adding bookkeeping GPU work
to the recurring timing boundary.

Timed-sample memory columns are retained for diagnostics only and must not be
used to choose a measurement environment.

## Timing protocol

Unchanged J004/Lane-K shape:

- GPU timestamp is the primary axis;
- complete CPU wall is diagnostic/health/provenance only;
- 4 warmup pairs;
- 12 measured pairs;
- 8 fresh-process blocks;
- AB/BA alternation inside each process;
- frozen start-order counterbalance:
  `AB, BA, AB, BA, BA, AB, BA, AB`;
- 1 second settle before each fresh process;
- 16 complete transitions per sample;
- all samples retained;
- sample exclusion forbidden;
- instability rerun budget: 0;
- completed-campaign rerun budget: 0;
- forced GPU clocks/power states forbidden.

The environments are evaluated independently. Their raw speed must not be
compared to select an environment.

## Frozen acceptance gate

For every profile and track independently:

- max absolute process-median ratio <= **1.02**;
- process-median span ratio <= **1.03**;
- max within-process order-bias ratio <= **1.02**.

An environment is reusable only if all ten required controls
(5 profiles × primary/software) pass.

No profile averaging is permitted.

## Decision mapping

- single-context PASS / dual-context FAIL:
  accept `single-context-independent-runtime` as the reusable heavy-boundary
  timing environment.
- dual-context PASS / single-context FAIL:
  accept `dual-context` as the reusable heavy-boundary timing environment.
- both PASS:
  both are measurement-valid. Final selection must be documented from
  reproducibility, implementation complexity, and allocation/lifetime evidence
  handling; measured speed is forbidden as a selection criterion.
- both FAIL:
  L001 outcome is `measurement-limited`; do not relax the J004 gate and enter
  L002 prospectively.

## L002 boundary

L002 is forbidden unless L001 produces no usable environment.

If required, L002 will use the same heavy recurring boundary with pre-frozen
synthetic/injected known effects and no architecture candidate. Its effect
sizes, thresholds, and decision rule must be frozen before target timing.

## Repository discipline

- J004 evidence is immutable;
- J005 remains forbidden;
- no routine PR;
- no merge from `research` or another lane during L001;
- meaningful checkpoints are committed directly to this branch;
- `__pycache__/` and `*.py[cod]` remain ignored.
