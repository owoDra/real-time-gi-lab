#version 460
layout(local_size_x = 64) in;
layout(std430, set = 0, binding = 0) readonly buffer SurfaceBuffer { vec4 positions[]; } surfaces;
layout(std430, set = 0, binding = 1) readonly buffer TileDepthBuffer { uint depth_bits[]; } tiles;
layout(std430, set = 0, binding = 8) buffer TileOwnerBuffer { uint surface_ids[]; } owners;
layout(std140, set = 0, binding = 9) uniform Params {
    vec4 camera_pos_near; vec4 camera_right_tan_x; vec4 camera_up_tan_y; vec4 camera_forward_far;
    vec4 scene_origin_spacing; vec4 light_pos_interval; uvec4 counts; uvec4 limits;
} p;
bool project_surface(vec3 position, out uint tile_id, out float depth) {
    vec3 rel = position - p.camera_pos_near.xyz;
    depth = dot(rel, p.camera_forward_far.xyz);
    if (depth < p.camera_pos_near.w || depth > p.camera_forward_far.w) return false;
    float nx = dot(rel, p.camera_right_tan_x.xyz) / (depth * p.camera_right_tan_x.w);
    float ny = dot(rel, p.camera_up_tan_y.xyz) / (depth * p.camera_up_tan_y.w);
    if (abs(nx) > 1.0 || abs(ny) > 1.0) return false;
    uint x = min(p.counts.y - 1u, uint(max(0.0, (nx * 0.5 + 0.5) * float(p.counts.y))));
    uint y = min(p.counts.z - 1u, uint(max(0.0, (ny * 0.5 + 0.5) * float(p.counts.z))));
    tile_id = y * p.counts.y + x; return true;
}
void main() {
    uint surface_id = gl_GlobalInvocationID.x; if (surface_id >= p.counts.x) return;
    uint tile_id; float depth;
    if (!project_surface(surfaces.positions[surface_id].xyz, tile_id, depth)) return;
    if (floatBitsToUint(depth) == tiles.depth_bits[tile_id]) atomicMin(owners.surface_ids[tile_id], surface_id);
}
