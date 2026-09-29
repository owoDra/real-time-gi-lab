# G004 — Integration hardening

Status: **frozen before execution**

G004 carries forward exactly one G003 result:
`hardened-transient-lbvh`.

No additional performance optimization is permitted in G004.

## Question

Does the hardened lifetime/residency change preserve the already-accepted
integration semantics across stable, rigid, deforming, topology-changing, and
stress workloads?

## Frozen matrix

Sixteen target-GPU cases are defined in `004-integration-hardening-config.json`.

Coverage includes:

- static, camera motion, light motion;
- representative rigid transform;
- rigid large/few and rigid small/many controls;
- stable-topology deforming;
- topology-changing/high-churn replacement;
- sparse/dense/large/vertical stable stress;
- sparse/dense/large/vertical moving stress.

Geometry classes remain separate evidence.

## Correctness gates

Every row must pass Vulkan validation and the runtime reference validation with:

- visibility mismatches = 0;
- producer semantic errors = 0;
- hit mismatches = 0;
- traversal runtime errors = 0;
- missing/leaked probes = 0;
- stale C001 slots = 0;
- resolved-output mismatches = 0;
- storage failures = 0;
- producer overflow = 0.

Dynamic class-specific counters are also checked so that deforming and topology
cases cannot silently collapse back to a rigid translation workload.

These checks jointly exercise:

- A001 producer semantics;
- shared exact Hit semantics;
- C001 storage semantics;
- same-frame dynamic visibility;
- static/dynamic nearest-hit merge;
- class-specific geometry updates.

## Timing

Timing fields may be retained diagnostically, but no timing PASS/FAIL is allowed.
G002 closed without a safe decision-valid timing protocol and GPU power/clock
manipulation remains forbidden.

## Decision

All 16 frozen cases must pass before G005 deterministic same-boundary replay can
begin.
