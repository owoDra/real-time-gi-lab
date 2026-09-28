# Lane A Split RC replay stream schema v1

A001 exports the GPU-produced stream exactly in its natural append order so
Lane B and Lane C can replay the same workload without a CPU sort or a
storage/traversal-oriented post-generation reorder.

## Container

`stream-v1.bin` is little-endian and contains:

1. one 64-byte `SplitRcStreamHeaderV1`;
2. `item_count` consecutive 64-byte `SplitRcWorkItemV1` records.

`stream-v1.json` is a human-readable sidecar. The C++ layout in
`src/research/lane_a_split_rc/stream_schema.hpp` is the binary source of truth.

### Header v1

| Byte | Type | Field |
| ---: | --- | --- |
| 0 | char[8] | magic = `PHOSRC1\0` |
| 8 | u32 | schema_version = 1 |
| 12 | u32 | header_bytes = 64 |
| 16 | u32 | item_bytes = 64 |
| 20 | u32 | frame_id |
| 24 | u32 | item_count |
| 28 | u32 | output_count |
| 32 | u32 | cascade_count |
| 36 | u32 | rays_per_probe |
| 40 | u32 | tile_width |
| 44 | u32 | tile_height |
| 48 | u32 | reserved0 |
| 52 | padding | ABI padding |
| 56 | u64 | workload_id |

`workload_id` is FNV-1a over the exact emitted item bytes. It identifies the
observed stream order as well as its semantic contents.

### Work item v1

| Byte | Type | Field |
| ---: | --- | --- |
| 0 | i32 | probe_x |
| 4 | i32 | probe_y |
| 8 | i32 | probe_z |
| 12 | u32 | cascade |
| 16 | u32 | ray_index |
| 20 | u32 | output_id |
| 24 | u32 | surface_id |
| 28 | u32 | tile_id |
| 32 | f32 | interval_min |
| 36 | f32 | interval_max |
| 40 | f32 | dir_x |
| 44 | f32 | dir_y |
| 48 | f32 | dir_z |
| 52 | f32 | probe_px |
| 56 | f32 | probe_py |
| 60 | f32 | probe_pz |

## Producer ordering contract

The producer launches one invocation per source scene surface. GPU visibility
first selects one nearest owner per screen tile. Every winning owner atomically
reserves one contiguous block containing:

`cascade_count * rays_per_probe`

records and one contiguous output range containing:

`cascade_count`

outputs.

Within a reserved block, order is always:

`cascade-major -> ray`

The order of different visible-surface blocks is the order in which GPU
producer invocations reserve space. A001 does not sort those blocks by tile,
probe, cascade, spatial key, storage address, hash slot, page, brick, or
traversal identity.

This GPU append order is intentionally allowed to differ between executions.
A recorded `stream-v1.bin` is the replayable workload identity for Lane B/C.

## Semantic fields

- `(probe_x, probe_y, probe_z, cascade)` identifies the Split RC probe.
- `ray_index` selects one of the eight v1 direction controls.
- `[interval_min, interval_max]` is the cascade ray interval.
- `output_id` identifies the gather/merge/resolve destination produced by this frame.
- `surface_id` and `tile_id` preserve the scene/visibility origin of the work.
- `(probe_px, probe_py, probe_pz)` is the world-space probe center.

The schema intentionally carries no traversal result and no radiance-storage
address. Lane B/C may derive candidate-specific state from these fields, but
must retain the original item order for matched natural-order comparisons.

Any incompatible field/layout/order semantic change requires schema v2.
