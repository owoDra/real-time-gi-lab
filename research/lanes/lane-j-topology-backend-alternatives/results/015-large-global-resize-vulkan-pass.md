# J003 large-global-high persistent-Vulkan resize-path PASS

Status: **PASS — actual Vulkan resize overlap validated**

The frozen `large-global-high` topology profile passed the persistent Vulkan
replay on the target GPU.

## Result

Target:

- AMD Radeon 8060S Graphics (RADV STRIX_HALO);
- 4096 validation rays per snapshot;
- 8 frozen snapshots;
- total exact-Hit mismatches: **0**;
- total traversal runtime errors: **0**.

## Actual resize path

Initial state:

- active clusters: 171;
- physical slot capacity: 256;
- candidate persistent Vulkan allocation: 2,645,968 bytes.

Step 1:

- primitive count: 10,240;
- active clusters: 276;
- physical slot capacity: **512**;
- resize occurred as frozen by v1.3;
- new candidate persistent Vulkan allocation: 5,291,984 bytes;
- actual simultaneous old/new candidate allocation:
  **7,937,952 bytes**;
- maximum live staging allocation: 3,121,152 bytes;
- measured candidate true peak resident bytes:
  **11,059,104 bytes**.

The actual Vulkan old/new overlap matches the previously frozen host-layout
logical overlap, demonstrating that the migration path retains old candidate
buffers until replacement buffers are populated.

## Post-resize persistence

Steps 2-7 retained the 512-slot capacity and returned to dirty-range uploads:

- step 2: 445 regions / 1,529,680 logical bytes;
- step 3: 649 / 2,232,528;
- step 4: 523 / 1,798,416;
- step 5: 781 / 2,687,312;
- step 6: 439 / 1,509,008;
- step 7: 586 / 2,015,472.

No later transition reallocated the candidate buffers.

## Interpretation

The frozen persistent-slot growth rule is now validated on the target GPU:

- exact traversal remains correct across migration;
- old/new simultaneous residency is observable and accounted;
- staging is separately accounted;
- persistent allocation remains stable after growth;
- dirty-range updates resume after the resize.

Diagnostic traversal timestamps remain non-ranking evidence.

## Promotion

Run the complete five-profile persistent-Vulkan correctness/memory campaign
from one unchanged v1.6 build. J003 may only close its GPU correctness/memory
gate if every frozen profile reports zero Hit mismatches and zero traversal
runtime errors.
