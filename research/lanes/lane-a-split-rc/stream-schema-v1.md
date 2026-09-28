# Lane A Split RC replay stream schema v1

Experiment A001 exports the naturally ordered producer stream so Lane B and
Lane C can replay exactly the same query population without inserting a CPU
sort or a post-producer global reorder.

## Files

Each recorded case writes:

- `stream-v1.bin`: little-endian, tightly packed array of 64-byte
  `WorkItemV1` records in canonical producer order;
- `stream-v1.json`: metadata needed to interpret the binary and reproduce the
  producer configuration.

The binary has no container header. The JSON manifest is authoritative for
schema version, item count, frame/case identity, tile dimensions, cascade
configuration, active count, and source commit.

## WorkItemV1

The 64-byte record is four 16-byte blocks:

| Byte | Type | Field |
| ---: | --- | --- |
| 0 | u32 | frame_id |
| 4 | u32 | probe_id |
| 8 | u32 | cascade |
| 12 | u32 | ray_index |
| 16 | f32 | origin.x |
| 20 | f32 | origin.y |
| 24 | f32 | origin.z |
| 28 | f32 | t_min |
| 32 | f32 | direction.x |
| 36 | f32 | direction.y |
| 40 | f32 | direction.z |
| 44 | f32 | t_max |
| 48 | u32 | output_id |
| 52 | u32 | surface_id |
| 56 | u32 | tile_id |
| 60 | u32 | flags |

`flags & 1` means the item is active. Inactive records remain in the binary so
the stream preserves its producer-defined index space; consumers must skip them
without compacting or sorting first.

## Canonical producer order

A001 uses the semantic index

`tile-major -> cascade -> ray`

with

`index = ((tile * cascade_count) + cascade) * rays_per_probe + ray`.

The order follows screen-space visibility/probe identity and Split RC cascade
identity. It never depends on a hash slot, brick/page address, traversal node,
radiance-storage location, or a key derived from those structures. This is why
it is accepted as producer order rather than a storage-oriented scheduling
step.

## Identity and intervals

- `probe_id == tile_id` for schema v1. A probe is the visible surface sample
  selected for one screen tile.
- `surface_id` identifies the source scene sample selected by GPU visibility.
- `output_id = tile_id * cascade_count + cascade`.
- ray intervals are contiguous logarithmic cascade intervals:
  cascade 0 is `[0, base]`; cascade N is
  `[base*scale^(N-1), base*scale^N]`.
- ray directions are deterministic cosine-weighted hemisphere samples around
  the visible surface normal.

Schema v1 intentionally carries no storage address or traversal result. Lane B
and Lane C may attach their own candidate-specific state while retaining these
records unchanged as the workload identity.

## Compatibility rule

Any incompatible field, order, identity, interval, or active-record semantic
change requires a new schema version. Adding manifest-only diagnostic fields
does not require a binary schema bump.
