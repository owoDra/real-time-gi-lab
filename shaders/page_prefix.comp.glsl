#version 460
layout(local_size_x = 256) in;

layout(std430, set = 0, binding = 0) readonly buffer Counts { uint v[]; } counts;
layout(std430, set = 0, binding = 1) writeonly buffer Offsets { uint v[]; } offsets;

layout(push_constant) uniform Push {
    uint page_count;
    uint unused0;
    uint unused1;
    uint unused2;
} pc;

shared uint partial[256];

void main() {
    uint lane = gl_LocalInvocationID.x;
    uint chunk = (pc.page_count + 255u) / 256u;
    uint begin = min(lane * chunk, pc.page_count);
    uint end = min(begin + chunk, pc.page_count);

    uint local_sum = 0u;
    for (uint i = begin; i < end; ++i) {
        local_sum += counts.v[i];
    }
    partial[lane] = local_sum;
    barrier();

    // Inclusive scan of the 256 chunk totals. Each lane then serially scans
    // only its own chunk. For the current dense-page M0 workload this avoids a
    // general-purpose radix/recursive scan implementation while keeping the
    // entire grouping path on the GPU.
    for (uint step = 1u; step < 256u; step <<= 1u) {
        uint add = lane >= step ? partial[lane - step] : 0u;
        barrier();
        partial[lane] += add;
        barrier();
    }

    uint running = lane == 0u ? 0u : partial[lane - 1u];
    for (uint i = begin; i < end; ++i) {
        offsets.v[i] = running;
        running += counts.v[i];
    }
}
