# J003 — target-GPU prototype gate

Status: **READY TO START after J002 local CPU preflight**

This document freezes the first GPU-required boundary. It does not implement or
time the candidate.

## Preconditions

- branch: `research-lane-j-topology-backend-alternatives`;
- clean worktree;
- J002 canonical materialization complete;
- J003 CPU structural replay PASS;
- exact A001 stream identity matches the frozen source;
- target GPU:
  `AMD Radeon 8060S Graphics (RADV STRIX_HALO)`;
- automatic power management only.

## Prototype scope

Implement only:

1. `clustered-two-level-bvh`;
2. Lane E object-local HWRT rebuild control;
3. Lane E/B003 software rebuild where practical;
4. hardened transient LBVH control;
5. accounting/vanilla control required to close the boundary.

Do not add a second experimental candidate.

## GPU implementation order

Before any timing campaign:

1. upload one frozen J002 snapshot;
2. implement exact triangle payload and B001-compatible Hit output;
3. implement deterministic initial clusters;
4. implement dirty ownership classification;
5. implement retained cluster micro-hierarchy rebuild;
6. implement split/merge using the v1.1 frozen rules;
7. implement upper cluster hierarchy refit/rebuild;
8. implement exact traversal;
9. integrate static/dynamic nearest-hit/tie merge;
10. connect A001 natural stream and C001 storage semantics;
11. add allocation lifetime census and all common boundary fields;
12. replay all five topology profiles.

## Hard acceptance fields

Every profile must report:

- visibility mismatch = 0;
- producer semantic error = 0;
- Hit mismatch = 0;
- nearest-hit/tie mismatch = 0;
- traversal runtime error = 0;
- storage failure = 0;
- immutable-owner mutation = 0;
- unaffected-cluster rebuild count = 0;
- complete allocation census;
- complete common stage record;
- true peak resident memory from lifetimes.

A missing inapplicable stage is invalid; emit numeric zero.

## Memory gate

The clustered candidate is rejected before timing if:

- persistent memory >1.25x same-run Lane E HWRT rebuild;
- true peak resident memory >1.25x same-run Lane E HWRT rebuild;
- live allocation ownership does not return to the declared persistent baseline
  after a complete repeated topology cycle;
- a supposedly bounded persistent pool grows monotonically.

## Timing prohibition

J003 may collect diagnostic timestamps to validate accounting boundaries, but it
must not rank candidates.

Formal ranking belongs to J004 and is blocked until Lane I publishes I004 and a
J004 promotion gate is committed **before** target candidate timing.
