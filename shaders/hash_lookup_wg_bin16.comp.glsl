#version 460
layout(local_size_x = 256) in;

const uint WORKGROUP_SIZE = 256u;
const uint BIN_COUNT = 16u;

struct Query { uint key; uint page_id; uint local_index; uint pad; };
layout(std430, set = 0, binding = 0) readonly buffer Queries { Query q[]; } queries;
layout(std430, set = 0, binding = 1) readonly buffer Keys { uint v[]; } keys;
layout(std430, set = 0, binding = 2) readonly buffer Payload { uint v[]; } payload;
layout(std430, set = 0, binding = 3) writeonly buffer Output { uint v[]; } output_data;
layout(push_constant) uniform Push {
    uint query_count;
    uint table_mask;
    uint lookup_limit;
    uint pad;
} pc;

// 5,248 bytes/workgroup:
// 256 * sizeof(Query) + 256 * sizeof(uint) + 2 * 16 * sizeof(uint).
shared Query staged_queries[WORKGROUP_SIZE];
shared uint staged_indices[WORKGROUP_SIZE];
shared uint bin_counts[BIN_COUNT];
shared uint bin_cursors[BIN_COUNT];

uint mix32(uint x) {
    x ^= x >> 16;
    x *= 0x7feb352du;
    x ^= x >> 15;
    x *= 0x846ca68bu;
    x ^= x >> 16;
    return x == 0u ? 1u : x;
}

uint coarse_bin(uint slot) {
    // table_mask + 1 is a power of two in this experiment. Normalize the
    // initial probe slot into 16 equal contiguous ranges without a global sort.
    uint table_bits = uint(findMSB(pc.table_mask + 1u));
    uint shift = table_bits > 4u ? table_bits - 4u : 0u;
    return min(slot >> shift, BIN_COUNT - 1u);
}

uint lookup(uint key) {
    uint slot = mix32(key) & pc.table_mask;
    for (uint probe = 0u; probe < pc.lookup_limit; ++probe) {
        uint candidate = keys.v[slot];
        if (candidate == key) return payload.v[slot];
        if (candidate == 0u) break;
        slot = (slot + 1u) & pc.table_mask;
    }
    return 0u;
}

void main() {
    uint lane = gl_LocalInvocationID.x;
    uint group_begin = gl_WorkGroupID.x * WORKGROUP_SIZE;
    uint remaining =
        group_begin < pc.query_count ? pc.query_count - group_begin : 0u;
    uint group_count = min(remaining, WORKGROUP_SIZE);
    bool is_active = lane < group_count;
    uint source_index = group_begin + lane;

    if (lane < BIN_COUNT) {
        bin_counts[lane] = 0u;
        bin_cursors[lane] = 0u;
    }
    barrier();

    Query query;
    uint bin = 0u;
    if (is_active) {
        query = queries.q[source_index];
        uint initial_slot = mix32(query.key) & pc.table_mask;
        bin = coarse_bin(initial_slot);
        atomicAdd(bin_counts[bin], 1u);
    }
    barrier();

    if (lane == 0u) {
        uint running = 0u;
        for (uint i = 0u; i < BIN_COUNT; ++i) {
            bin_cursors[i] = running;
            running += bin_counts[i];
        }
    }
    barrier();

    if (is_active) {
        uint destination = atomicAdd(bin_cursors[bin], 1u);
        staged_queries[destination] = query;
        staged_indices[destination] = source_index;
    }
    barrier();

    if (is_active) {
        Query grouped = staged_queries[lane];
        uint original_index = staged_indices[lane];
        output_data.v[original_index] = lookup(grouped.key);
    }
}
