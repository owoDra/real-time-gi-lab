#include "j003_clustered_bvh.hpp"

#include <algorithm>
#include <cmath>
#include <functional>
#include <limits>
#include <numeric>
#include <stdexcept>
#include <tuple>
#include <utility>

namespace phos::gi::research::lane_j {
namespace {

[[nodiscard]] Vec3 add(Vec3 a, Vec3 b) {
    return {a.x + b.x, a.y + b.y, a.z + b.z};
}

[[nodiscard]] Vec3 scale(Vec3 v, float s) {
    return {v.x * s, v.y * s, v.z * s};
}

[[nodiscard]] Vec3 centroid(const Triangle& triangle) {
    return scale(add(add(triangle.v0, triangle.v1), triangle.v2), 1.0F / 3.0F);
}

[[nodiscard]] Vec3 center(const Aabb& bounds) {
    return {
        (bounds.min.x + bounds.max.x) * 0.5F,
        (bounds.min.y + bounds.max.y) * 0.5F,
        (bounds.min.z + bounds.max.z) * 0.5F,
    };
}

void include(Aabb& bounds, Vec3 point) {
    bounds.min.x = std::min(bounds.min.x, point.x);
    bounds.min.y = std::min(bounds.min.y, point.y);
    bounds.min.z = std::min(bounds.min.z, point.z);
    bounds.max.x = std::max(bounds.max.x, point.x);
    bounds.max.y = std::max(bounds.max.y, point.y);
    bounds.max.z = std::max(bounds.max.z, point.z);
}

[[nodiscard]] std::uint32_t spread10(std::uint32_t value) {
    std::uint32_t result = 0U;
    for (std::uint32_t bit = 0U; bit < 10U; ++bit) {
        result |= ((value >> bit) & 1U) << (3U * bit);
    }
    return result;
}

[[nodiscard]] std::uint32_t quantize10(
    float value,
    float low,
    float high) {
    const auto extent = std::max(double(high) - double(low), 1.0e-9);
    const auto normalized =
        (double(value) - double(low)) / extent * 1023.0 + 0.5;
    const auto raw = static_cast<int>(normalized);
    return static_cast<std::uint32_t>(std::clamp(raw, 0, 1023));
}

[[nodiscard]] std::uint32_t morton10(Vec3 point, const Aabb& bounds) {
    const auto x = quantize10(point.x, bounds.min.x, bounds.max.x);
    const auto y = quantize10(point.y, bounds.min.y, bounds.max.y);
    const auto z = quantize10(point.z, bounds.min.z, bounds.max.z);
    return spread10(x) | (spread10(y) << 1U) | (spread10(z) << 2U);
}

[[nodiscard]] Aabb centroid_bounds(
    std::span<const Triangle> triangles,
    std::span<const std::uint32_t> indices) {
    Aabb bounds{};
    for (const auto index : indices) {
        include(bounds, centroid(triangles[index]));
    }
    return bounds;
}

[[nodiscard]] std::vector<std::uint32_t> morton_order_triangles(
    std::span<const Triangle> triangles,
    std::span<const std::uint32_t> indices) {
    const auto bounds = centroid_bounds(triangles, indices);
    std::vector<std::uint32_t> ordered(indices.begin(), indices.end());
    std::stable_sort(
        ordered.begin(),
        ordered.end(),
        [&](std::uint32_t a, std::uint32_t b) {
            const auto ca = morton10(centroid(triangles[a]), bounds);
            const auto cb = morton10(centroid(triangles[b]), bounds);
            if (ca != cb) {
                return ca < cb;
            }
            return triangles[a].primitive_id < triangles[b].primitive_id;
        });
    return ordered;
}

[[nodiscard]] GpuBvhNode make_gpu_node(
    const Aabb& bounds,
    std::uint32_t left,
    std::uint32_t right,
    std::uint32_t payload,
    std::uint32_t leaf_count) {
    GpuBvhNode node{};
    node.bounds_min = {
        bounds.min.x,
        bounds.min.y,
        bounds.min.z,
        0.0F,
    };
    node.bounds_max = {
        bounds.max.x,
        bounds.max.y,
        bounds.max.z,
        0.0F,
    };
    node.meta = {left, right, payload, leaf_count};
    return node;
}

[[nodiscard]] GpuTriangle make_gpu_triangle(const Triangle& triangle) {
    GpuTriangle out{};
    out.v0 = {triangle.v0.x, triangle.v0.y, triangle.v0.z, 0.0F};
    out.v1 = {triangle.v1.x, triangle.v1.y, triangle.v1.z, 0.0F};
    out.v2 = {triangle.v2.x, triangle.v2.y, triangle.v2.z, 0.0F};
    out.meta = {
        triangle.primitive_id,
        triangle.material_id,
        triangle.instance_id,
        triangle.two_sided ? 1U : 0U,
    };
    return out;
}

struct BuiltTree {
    std::uint32_t root{kInvalidId};
    Aabb bounds{};
};

[[nodiscard]] BuiltTree build_triangle_tree(
    std::span<const Triangle> triangles,
    std::span<const std::uint32_t> ordered,
    std::vector<GpuBvhNode>& nodes) {
    if (ordered.empty()) {
        throw std::runtime_error("J003 micro BVH cannot be empty");
    }

    std::function<BuiltTree(std::size_t, std::size_t)> build =
        [&](std::size_t begin, std::size_t end) -> BuiltTree {
        if (end - begin == 1U) {
            const auto triangle_index = ordered[begin];
            const auto bounds = triangle_bounds(triangles[triangle_index]);
            const auto node_index = static_cast<std::uint32_t>(nodes.size());
            nodes.push_back(make_gpu_node(
                bounds,
                kInvalidId,
                kInvalidId,
                triangle_index,
                1U));
            return {node_index, bounds};
        }

        const auto node_index = static_cast<std::uint32_t>(nodes.size());
        nodes.emplace_back();
        const auto middle = begin + (end - begin) / 2U;
        const auto left = build(begin, middle);
        const auto right = build(middle, end);
        const auto bounds = merge_bounds(left.bounds, right.bounds);
        nodes[node_index] = make_gpu_node(
            bounds,
            left.root,
            right.root,
            kInvalidId,
            0U);
        return {node_index, bounds};
    };

    return build(0U, ordered.size());
}

[[nodiscard]] BuiltTree build_upper_tree(
    std::span<const GpuCluster> clusters,
    std::span<const std::uint32_t> ordered,
    std::vector<GpuBvhNode>& nodes) {
    if (ordered.empty()) {
        throw std::runtime_error("J003 upper BVH cannot be empty");
    }

    const auto cluster_bounds = [&](std::uint32_t index) {
        const auto& cluster = clusters[index];
        return Aabb{
            {
                cluster.bounds_min[0],
                cluster.bounds_min[1],
                cluster.bounds_min[2],
            },
            {
                cluster.bounds_max[0],
                cluster.bounds_max[1],
                cluster.bounds_max[2],
            },
        };
    };

    std::function<BuiltTree(std::size_t, std::size_t)> build =
        [&](std::size_t begin, std::size_t end) -> BuiltTree {
        if (end - begin == 1U) {
            const auto cluster_index = ordered[begin];
            const auto bounds = cluster_bounds(cluster_index);
            const auto node_index = static_cast<std::uint32_t>(nodes.size());
            nodes.push_back(make_gpu_node(
                bounds,
                kInvalidId,
                kInvalidId,
                cluster_index,
                1U));
            return {node_index, bounds};
        }

        const auto node_index = static_cast<std::uint32_t>(nodes.size());
        nodes.emplace_back();
        const auto middle = begin + (end - begin) / 2U;
        const auto left = build(begin, middle);
        const auto right = build(middle, end);
        const auto bounds = merge_bounds(left.bounds, right.bounds);
        nodes[node_index] = make_gpu_node(
            bounds,
            left.root,
            right.root,
            kInvalidId,
            0U);
        return {node_index, bounds};
    };

    return build(0U, ordered.size());
}

} // namespace

Aabb triangle_bounds(const Triangle& triangle) {
    Aabb bounds{};
    include(bounds, triangle.v0);
    include(bounds, triangle.v1);
    include(bounds, triangle.v2);
    return bounds;
}

Aabb merge_bounds(const Aabb& a, const Aabb& b) {
    return {
        {
            std::min(a.min.x, b.min.x),
            std::min(a.min.y, b.min.y),
            std::min(a.min.z, b.min.z),
        },
        {
            std::max(a.max.x, b.max.x),
            std::max(a.max.y, b.max.y),
            std::max(a.max.z, b.max.z),
        },
    };
}

ClusteredBvhData build_initial_clustered_bvh(
    std::span<const Triangle> triangles) {
    if (triangles.empty()) {
        throw std::runtime_error("J003 initial clustering requires triangles");
    }

    ClusteredBvhData result{};
    result.triangles.reserve(triangles.size());
    for (const auto& triangle : triangles) {
        result.triangles.push_back(make_gpu_triangle(triangle));
    }

    std::vector<std::uint32_t> all(triangles.size());
    std::iota(all.begin(), all.end(), 0U);
    const auto ordered = morton_order_triangles(triangles, all);

    result.summary.occupancy_min = std::numeric_limits<std::uint32_t>::max();
    for (std::size_t begin = 0U; begin < ordered.size(); begin += kClusterTarget) {
        const auto end = std::min(
            ordered.size(),
            begin + std::size_t(kClusterTarget));
        const std::span<const std::uint32_t> members(
            ordered.data() + begin,
            end - begin);
        const auto local_order = morton_order_triangles(triangles, members);
        const auto micro = build_triangle_tree(
            triangles,
            local_order,
            result.micro_nodes);

        GpuCluster cluster{};
        cluster.bounds_min = {
            micro.bounds.min.x,
            micro.bounds.min.y,
            micro.bounds.min.z,
            0.0F,
        };
        cluster.bounds_max = {
            micro.bounds.max.x,
            micro.bounds.max.y,
            micro.bounds.max.z,
            0.0F,
        };
        const auto cluster_id =
            static_cast<std::uint32_t>(result.clusters.size());
        cluster.meta = {
            micro.root,
            cluster_id,
            static_cast<std::uint32_t>(members.size()),
            0U,
        };
        result.clusters.push_back(cluster);

        const auto occupancy = static_cast<std::uint32_t>(members.size());
        result.summary.occupancy_min =
            std::min(result.summary.occupancy_min, occupancy);
        result.summary.occupancy_max =
            std::max(result.summary.occupancy_max, occupancy);
    }

    if (result.summary.occupancy_max > kClusterMaximum) {
        throw std::runtime_error("J003 initial cluster maximum exceeded");
    }

    Aabb upper_centroid_bounds{};
    for (const auto& cluster : result.clusters) {
        const auto bounds = Aabb{
            {cluster.bounds_min[0], cluster.bounds_min[1], cluster.bounds_min[2]},
            {cluster.bounds_max[0], cluster.bounds_max[1], cluster.bounds_max[2]},
        };
        include(upper_centroid_bounds, center(bounds));
    }

    std::vector<std::uint32_t> cluster_order(result.clusters.size());
    std::iota(cluster_order.begin(), cluster_order.end(), 0U);
    std::stable_sort(
        cluster_order.begin(),
        cluster_order.end(),
        [&](std::uint32_t a, std::uint32_t b) {
            const auto bounds_a = Aabb{
                {
                    result.clusters[a].bounds_min[0],
                    result.clusters[a].bounds_min[1],
                    result.clusters[a].bounds_min[2],
                },
                {
                    result.clusters[a].bounds_max[0],
                    result.clusters[a].bounds_max[1],
                    result.clusters[a].bounds_max[2],
                },
            };
            const auto bounds_b = Aabb{
                {
                    result.clusters[b].bounds_min[0],
                    result.clusters[b].bounds_min[1],
                    result.clusters[b].bounds_min[2],
                },
                {
                    result.clusters[b].bounds_max[0],
                    result.clusters[b].bounds_max[1],
                    result.clusters[b].bounds_max[2],
                },
            };
            const auto code_a = morton10(center(bounds_a), upper_centroid_bounds);
            const auto code_b = morton10(center(bounds_b), upper_centroid_bounds);
            return std::tuple{code_a, a} < std::tuple{code_b, b};
        });

    const auto upper = build_upper_tree(
        result.clusters,
        cluster_order,
        result.upper_nodes);
    result.upper_root = upper.root;
    result.summary.cluster_count =
        static_cast<std::uint32_t>(result.clusters.size());
    result.summary.upper_node_count =
        static_cast<std::uint32_t>(result.upper_nodes.size());
    result.summary.micro_node_count =
        static_cast<std::uint32_t>(result.micro_nodes.size());
    return result;
}

} // namespace phos::gi::research::lane_j
