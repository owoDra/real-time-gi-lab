# J003 representative persistent-Vulkan replay PASS

Status: **PASS — exact persistent transition correctness restored**

The frozen `medium-global-representative` profile passed the persistent
Vulkan replay after the v1.6 strict source-order fp32 exact-intersection
correction.

## Result

Target device:

- AMD Radeon 8060S Graphics (RADV STRIX_HALO).

Validation:

- snapshots: 8;
- validation rays: 4096 per snapshot;
- total exact-Hit mismatches: **0**;
- total traversal runtime errors: **0**.

Persistent candidate accounting:

- persistent Vulkan allocation: 330,704 bytes;
- maximum observed candidate persistent + staging true peak: **483,104 bytes**;
- representative profile resize count: 0;
- validation-harness ray/hit allocation: 393,216 bytes, reported separately.

Dirty update behavior remained active across transitions:

- step 1: 76 upload regions / 258,352 logical bytes;
- step 2: 46 / 154,992;
- step 3: 67 / 227,344;
- step 4: 52 / 175,664;
- step 5: 76 / 258,352;
- step 6: 49 / 165,328;
- step 7: 64 / 217,008.

## Correctness resolution

The retained step-3 tie mismatch was localized with the watched-primitive
diagnostic:

- primitive 262389 reached the leaf;
- GPU intersection accepted it;
- GPU tie selection accepted it;
- it was later replaced because GPU t drift crossed the frozen B001 tie window.

v1.6 changed no Hit tolerance, primitive-ID tie rule, workload, topology or ray
set. The GLSL Moller-Trumbore path was instead made strict source-order fp32
using explicit scalar dot/cross helpers and `precise` intermediates
(NoContraction on Vulkan SPIR-V).

With that correction the unchanged representative gate reports zero mismatches.

## Promotion

Promote J003 to the resize-path target-GPU gate:

`large-global-high`

This profile must exercise the frozen 256 -> 512 physical-slot growth and
validate:

1. exact Hits remain zero-mismatch across the resize;
2. old candidate buffers remain resident until replacement migration completes;
3. actual Vulkan old/new overlap is recorded;
4. staging allocation is separately accounted;
5. post-resize persistent allocation remains internally consistent.

No formal timing ranking is permitted from these diagnostic traversal
timestamps.
