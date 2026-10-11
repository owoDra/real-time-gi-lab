# J004 formal crossover gate v7 amendment — exact tie pruning

Status: **FROZEN BEFORE ACCEPTED TARGET TIMING**
Issue: #23
Parent gate: `experiments/004-formal-crossover-gate-v2-amendment.md`
Pre-timing correction commit:
`0f9405c14d3d560ecdcb0373d246d32544cd1e96`

No accepted J004 architecture timing has been observed.

## Retained validation evidence

The v6 component diagnostic isolated the large-profile failure to the dynamic
HWRT comparison path:

- profile: `large-global-high`;
- track: `primary`;
- control: `lane-e-object-local-hwrt-rebuild`;
- total Hit mismatches: 445;
- nearest-hit/tie mismatches: 445;
- static mismatches: 0;
- dynamic mismatches: 445;
- merge-only mismatches: 0;
- traversal runtime/storage/ownership failures: 0.

## Root cause found during self review

J004's validation reference used `GpuSoftwareBvhData::trace`. Its triangle
intersection and `prefer_hit` code implement the frozen B001 rule that a hit
within

`best_t + max(HIT_ABS_TOL, abs(best_t) * HIT_REL_TOL)`

remains eligible and may win by lower primitive ID.

However its BVH node culling used `best_t` directly. A sibling node whose first
possible hit was slightly farther than `best_t` but still inside the frozen tie
tolerance could therefore be discarded before the primitive-ID tie rule ran.

The same semantic mismatch existed in the formal vanilla software BVH,
hardened-LBVH traversal, and B003 quantized traversal/DDA early-out.

This can make the accelerated reference disagree with B001 even when the
underlying triangle intersection is semantically eligible. Large J002 profiles
expose the defect because their expanded/nearby geometry produces substantially
more tie-eligible candidates.

## Correction

Before timing, all affected acceleration culling paths were aligned to the
already-frozen B001 contract:

- CPU `GpuSoftwareBvhData` node culling uses `best_t + tolerance`;
- formal hardened-LBVH node culling uses `best_t + tolerance`;
- formal vanilla-BVH node culling uses `best_t + tolerance`;
- formal B003 child-node culling uses `best_t + tolerance`;
- B003 segment DDA stops only when the next segment begins beyond
  `best_t + tolerance`.

The HWRT traversal shader is unchanged.

This is a correctness repair, not a workload/candidate/threshold/selector
change. It does affect the formal F003 traversal shader's bytes, so the earlier
statement that formal recurrent F003 traversal is byte-identical to historical
Lane G is explicitly superseded. The F003 builder remains unchanged.

## Frozen decision semantics

Unchanged:

- J002 geometry and topology sequence;
- A001 producer/order/rays;
- B001 Hit/tie tolerances and primitive-ID tie rule;
- C001 storage;
- primary/software track comparators;
- 5% promotion and non-regression boundaries;
- class selector;
- 4/12 paired sample shape;
- eight fresh-process blocks;
- zero sample exclusion;
- zero instability/completed-campaign reruns;
- GPU timestamps as primary axis;
- CPU wall as diagnostic only.

The next target execution must start from the newly refrozen harness identity
and repeat full hard validation before any formal timing.
