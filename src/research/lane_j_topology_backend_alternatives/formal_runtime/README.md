# J004 formal runtime source provenance

Issue: #23  
Execution config: `experiments/005-formal-crossover-config.json`

This directory is a selective snapshot for the formal J004 same-run crossover.
It does not merge Lane G wholesale.

## Pinned recurrent topology candidate

Lane-G final commit:

`9176cc1c175bcfec43fd28d993f88385b7a131d7`

The F003 GPU builder/traversal shaders are copied byte-for-byte from that result:

- `f003_lbvh_builder.comp.glsl`: `77db184be5fcee72fa6c4f5cf40cadf487dcedd4`
- `f003_dynamic_traversal.comp.glsl`: `56c7e80d345cf890d0b73b16edb740c874ac8dff`

The J004 host adapter reserves the maximum primitive capacity already frozen by
the J002 profile before timing, then updates only the active template/count per
transition. This avoids recurrent pipeline/layout/buffer creation without
changing the Lane-G GPU build/traversal algorithm:

- adapted `f003_transient_lbvh.cpp`: `17f55f17a35aaa5373074591af552636b1dfe82d`
- adapted `f003_transient_lbvh.hpp`: `ded4856b0fcb268ef8ca984338c073b4dace74eb`

`run_j004.py` fails closed if those frozen adapter/shader blobs drift. The
separate unchanged-LBVH timing variant is therefore not used: recreating the
fixed-count Lane-G runtime on every topology-count transition would introduce
recurrent pipeline/allocation setup and violate the frozen complete-boundary
rule.

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
