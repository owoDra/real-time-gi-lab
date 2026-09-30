# J003 all-profile persistent-Vulkan campaign PASS

Status: **PASS — J003 GPU correctness/memory gate complete**

One unchanged v1.6 build of the persistent Vulkan candidate was replayed across
all five frozen J002 topology profiles on the target GPU.

Target device:

- AMD Radeon 8060S Graphics (RADV STRIX_HALO).

Campaign:

- profiles: 5;
- snapshots per profile: 8;
- validation rays per snapshot: 4096;
- total exact-Hit mismatches across the campaign: **0**;
- total traversal runtime errors across the campaign: **0**.

The Mesa DZN ICD emitted the known `vkCreateInstance -> -9` warning and was
skipped; RADV was selected successfully.

## Per-profile correctness and peak memory

| Profile | Exact Hit mismatches | Runtime errors | Max candidate true peak resident bytes |
| --- | ---: | ---: | ---: |
| small-global-high | 0 | 0 | 65,680 |
| medium-global-representative | 0 | 0 | 483,104 |
| medium-local-high | 0 | 0 | 470,912 |
| large-global-high | 0 | 0 | 11,059,104 |
| large-local-high | 0 | 0 | 3,932,224 |

Validation ray/hit allocation was 393,216 bytes and is reported separately
from candidate persistent memory.

## Persistent behavior retained

The campaign validates the frozen v1.3/v1.6 candidate behavior:

- monotonic logical cluster IDs with reusable physical slots;
- dirty-only triangle, micro-BVH and cluster metadata uploads;
- upper rebuild/refit policy;
- exact B001 Hit/tie semantics;
- strict source-order fp32 exact triangle arithmetic;
- persistent candidate allocations across topology transitions.

The local-churn profiles retained lower dirty upload volume than corresponding
global-churn transitions without correctness loss.

## Resize-path evidence

`large-global-high` again exercised the frozen 256 -> 512 physical-slot
growth at step 1:

- old candidate persistent allocation: 2,645,968 bytes;
- new candidate persistent allocation: 5,291,984 bytes;
- simultaneous old/new candidate allocation: **7,937,952 bytes**;
- maximum staging allocation during migration: 3,121,152 bytes;
- candidate true peak resident bytes: **11,059,104 bytes**.

Post-resize transitions retained the 512-slot allocation and returned to
dirty-range uploads.

## Decision

Accept J003 as the topology-changing candidate's target-GPU
correctness/memory implementation checkpoint.

J003 does **not** provide a formal performance ranking. Its traversal timestamps
remain diagnostic because the formal J004 ranking remains gated by the Lane I
measurement-calibration prerequisite.

Before J004, refresh Lane I Issue #19 and current research integration state.
