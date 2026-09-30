# J004 formal runtime source provenance

Issue: #23  
Execution config: `experiments/005-formal-crossover-config.json`

This directory is a selective snapshot for the formal J004 same-run crossover.
It does not merge Lane G wholesale.

## Pinned recurrent topology candidate

Lane-G final commit:

`9176cc1c175bcfec43fd28d993f88385b7a131d7`

The recurrent F003 dynamic path is copied byte-for-byte from that result:

- `f003_transient_lbvh.cpp`: `f4df12560a8dd381db2c93e2b142f8acf4f8a2fe`
- `f003_transient_lbvh.hpp`: `61b73cd9652627b3f4b3a26aa5563b6660c2f35a`
- `f003_lbvh_builder.comp.glsl`: `77db184be5fcee72fa6c4f5cf40cadf487dcedd4`
- `f003_dynamic_traversal.comp.glsl`: `56c7e80d345cf890d0b73b16edb740c874ac8dff`

`run_j004.py` fails closed if those blobs drift. This is also the attribution
basis for not running a redundant "unchanged transient LBVH" timing variant:
Lane-G hardening affected setup lifetime, while J004 holds static setup common
and measures the same recurrent F003 implementation.

## Selectively reused accepted contracts

The directory also snapshots the Lane-G final copies of:

- B002 target Vulkan/HWRT traversal;
- B003 segment-DDA/hash + conservative quantized Micro BVH8;
- vanilla software BVH accounting control;
- A001 stream-v1 reader;
- I001 compute/storage/resolve shaders and exact hit merge.

J004-specific changes are limited to:

1. Vulkan allocation-lifetime and transfer-GPU accounting in the local
   `B002VulkanContext` copy;
2. descriptor rebinding in the local `I001ComputeStage`, so recurrent dynamic
   resources can change without recreating pipelines/layouts;
3. `j004_formal_process.cpp`, which binds those pieces to the frozen J002
   topology snapshots and accepted A001 stream.

No historical Lane-E/G timing is imported as decision evidence.
