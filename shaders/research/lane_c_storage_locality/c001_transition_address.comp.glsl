#version 450
layout(local_size_x = 256) in;

struct WorkItem {
    int probe_x; int probe_y; int probe_z; uint cascade;
    uint ray_index; uint output_id; uint surface_id; uint tile_id;
    float interval_min; float interval_max; float dir_x; float dir_y;
    float dir_z; float probe_px; float probe_py; float probe_pz;
};
struct Address { uint probe_key; uint brick_key; uint local_index; uint payload; };
struct TransitionLayout {
    int min_bx; int min_by; int min_bz; uint page_base;
    uint union_x; uint union_y; uint union_z; uint pad;
};

layout(std430, binding = 0) readonly buffer Inputs { WorkItem items[]; };
layout(std430, binding = 1) writeonly buffer Addresses { Address addresses[]; };
layout(std430, binding = 2) readonly buffer Layouts { TransitionLayout layouts[]; };
layout(std430, binding = 3) buffer B3 { uint b3[]; };
layout(std430, binding = 4) buffer B4 { uint b4[]; };
layout(std430, binding = 5) buffer B5 { uint b5[]; };
layout(std430, binding = 6) buffer B6 { uint b6[]; };
layout(std430, binding = 7) buffer B7 { uint b7[]; };

layout(push_constant) uniform Push {
    uint count; uint op; uint mask; uint max_probe;
    uint brick_edge; uint clip_x; uint clip_y; uint clip_z;
} pc;

uint mix32(uint x) {
    x ^= x >> 16; x *= 0x7feb352du; x ^= x >> 15;
    x *= 0x846ca68bu; x ^= x >> 16;
    return x == 0u ? 1u : x;
}
int floor_div(int value, int divisor) {
    int q = value / divisor;
    int r = value % divisor;
    return r < 0 ? q - 1 : q;
}

void main() {
    const uint i = gl_GlobalInvocationID.x;
    if (i >= pc.count) return;
    const WorkItem item = items[i];
    const int edge = int(pc.brick_edge);
    const int bx = floor_div(item.probe_x, edge);
    const int by = floor_div(item.probe_y, edge);
    const int bz = floor_div(item.probe_z, edge);
    const int lx = item.probe_x - bx * edge;
    const int ly = item.probe_y - by * edge;
    const int lz = item.probe_z - bz * edge;
    const TransitionLayout dims = layouts[item.cascade];
    const uint ubx = uint(bx - dims.min_bx);
    const uint uby = uint(by - dims.min_by);
    const uint ubz = uint(bz - dims.min_bz);
    const uint local = uint(lx + edge * (ly + edge * lz));
    const uint canonical_page =
        dims.page_base + (ubz * dims.union_y + uby) * dims.union_x + ubx;
    const uint key =
        canonical_page * pc.brick_edge * pc.brick_edge * pc.brick_edge + local + 1u;

    Address a;
    a.probe_key = key;
    a.payload = item.ray_index == 0u ? mix32(key ^ 0x9e3779b9u) : 0u;
    if (pc.op == 0u) {
        a.brick_key = 0u;
        a.local_index = 0u;
    } else {
        const uint sx = ubx % pc.clip_x;
        const uint sy = uby % pc.clip_y;
        const uint sz = ubz % pc.clip_z;
        const uint slot =
            ((item.cascade * pc.clip_z + sz) * pc.clip_y + sy) * pc.clip_x + sx;
        a.brick_key = slot + 1u;
        a.local_index = local;
    }
    addresses[i] = a;
}
