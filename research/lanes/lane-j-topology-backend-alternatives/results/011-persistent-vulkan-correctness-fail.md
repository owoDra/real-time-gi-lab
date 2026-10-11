# J003 representative persistent-Vulkan replay — correctness failure

Status: **FAIL — one exact-Hit mismatch; diagnostic replay required**

The first persistent-Vulkan replay of the frozen
`medium-global-representative` profile reached the target RADV device and
completed all eight snapshot traversals.

Observed:

- device: AMD Radeon 8060S Graphics (RADV STRIX_HALO);
- validation rays: 4096 per snapshot;
- snapshots: 8;
- traversal runtime errors: 0 on every snapshot;
- exact Hit mismatches: **1 total**;
- the mismatch occurred at step 3;
- all other snapshots reported zero mismatches;
- candidate persistent allocation: 330,704 bytes;
- maximum observed candidate persistent+staging true peak: 483,104 bytes;
- no slot-capacity resize occurred in this representative profile.

The Mesa DZN ICD emitted `vkCreateInstance -> -9` and was skipped; RADV was
selected successfully. This is not the correctness failure.

## Interpretation

J003 is **not promoted**. A single exact-Hit mismatch violates the frozen
zero-error gate.

Step 3 had a cluster-set rebuild and all 22 active cluster payloads were dirty,
so the current evidence does not support attributing the mismatch to an
obviously skipped dirty-slot upload. The difference may still be caused by
payload/state error or by exact-intersection/tie numerical behavior; no cause is
claimed before retaining the mismatching ray and Hit fields.

## Diagnostic action

The persistent replay now records, for up to 16 mismatches:

- snapshot index;
- ray index;
- ray origin/direction/t-max;
- expected hit flag/t/primitive/material/instance;
- actual hit flag/t/primitive/material/instance;
- traversal visit/test counters;
- runtime error flag.

Miss distances are serialized as JSON `null`, preserving a valid failure
artifact.

Rerun the same representative gate. Do not alter the correctness tolerance,
ray set, topology sequence, or candidate structure before the mismatch is
explained.
