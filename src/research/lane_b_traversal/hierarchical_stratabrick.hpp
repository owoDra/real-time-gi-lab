#pragma once

#include "traversal_common.hpp"

#include <algorithm>
#include <cmath>
#include <cstddef>
#include <cstdint>
#include <limits>
#include <numeric>
#include <span>
#include <stdexcept>
#include <unordered_map>
#include <unordered_set>
#include <utility>
#include <vector>

namespace phos::gi::research::lane_b {

struct SegmentCoord {
    std::int32_t x{};
    std::int32_t y{};
    std::int32_t z{};
    friend bool operator==(const SegmentCoord&, const SegmentCoord&) = default;
    friend bool operator<(const SegmentCoord& a, const SegmentCoord& b) noexcept {
        if (a.x != b.x) return a.x < b.x;
        if (a.y != b.y) return a.y < b.y;
        return a.z < b.z;
    }
};

struct SegmentCoordHash {
    [[nodiscard]] std::size_t operator()(const SegmentCoord& key) const noexcept {
        auto mix = [](std::uint64_t value) {
            value ^= value >> 30U;
            value *= 0xbf58476d1ce4e5b9ULL;
            value ^= value >> 27U;
            value *= 0x94d049bb133111ebULL;
            value ^= value >> 31U;
            return value;
        };
        const auto x = static_cast<std::uint64_t>(static_cast<std::uint32_t>(key.x));
        const auto y = static_cast<std::uint64_t>(static_cast<std::uint32_t>(key.y));
        const auto z = static_cast<std::uint64_t>(static_cast<std::uint32_t>(key.z));
        return static_cast<std::size_t>(mix(x) ^ (mix(y) << 1U) ^ (mix(z) << 2U));
    }
};

struct HierarchicalUpdateStats {
    std::size_t moved_primitives{};
    std::size_t membership_changes{};
    std::size_t refit_segments{};
    std::size_t rebuilt_segments{};
    std::size_t removed_segments{};
};

struct HierarchicalFlatNode {
    Aabb bounds{};
    std::uint32_t left{kInvalidId};
    std::uint32_t right{kInvalidId};
    std::uint32_t begin{};
    std::uint32_t count{};
};

struct HierarchicalFlatSegment {
    SegmentCoord coord{};
    std::uint32_t root{kInvalidId};
};

struct HierarchicalFlatPayload {
    std::vector<HierarchicalFlatNode> nodes;
    std::vector<std::uint32_t> ordered_primitives;
    std::vector<HierarchicalFlatSegment> segments;
    Aabb occupied_bounds{};
};

class HierarchicalStrataBrick {
    struct Node {
        Aabb bounds{};
        std::uint32_t left{};
        std::uint32_t right{};
        std::uint32_t begin{};
        std::uint32_t count{};
        bool leaf{};
    };

    struct Segment {
        std::vector<std::uint32_t> primitives;
        std::vector<std::uint32_t> ordered;
        std::vector<Node> nodes;
        std::uint32_t root{};
        Aabb bounds{};
    };

public:
    explicit HierarchicalStrataBrick(
        const std::vector<Triangle>& triangles,
        float segment_size)
        : triangles_(&triangles), segment_size_(segment_size) {
        if (!std::isfinite(segment_size_) || segment_size_ <= 0.0F) {
            throw std::runtime_error("segment_size must be finite and positive");
        }
        rebuild_all(triangles);
    }

    [[nodiscard]] float segment_size() const noexcept { return segment_size_; }
    [[nodiscard]] std::size_t segment_count() const noexcept { return segments_.size(); }
    [[nodiscard]] std::size_t membership_count() const noexcept {
        std::size_t count = 0;
        for (const auto& [key, segment] : segments_) {
            (void)key;
            count += segment.primitives.size();
        }
        return count;
    }

    [[nodiscard]] HierarchicalFlatPayload flatten() const {
        HierarchicalFlatPayload payload;
        payload.occupied_bounds = occupied_bounds_;

        std::vector<SegmentCoord> keys;
        keys.reserve(segments_.size());
        for (const auto& [key, segment] : segments_) {
            (void)segment;
            keys.push_back(key);
        }
        std::sort(keys.begin(), keys.end());

        for (const auto key : keys) {
            const auto& segment = segments_.at(key);
            const auto node_base = static_cast<std::uint32_t>(payload.nodes.size());
            const auto ordered_base =
                static_cast<std::uint32_t>(payload.ordered_primitives.size());

            payload.ordered_primitives.insert(
                payload.ordered_primitives.end(),
                segment.ordered.begin(),
                segment.ordered.end());

            for (const auto& node : segment.nodes) {
                payload.nodes.push_back({
                    node.bounds,
                    node.leaf ? kInvalidId : node_base + node.left,
                    node.leaf ? kInvalidId : node_base + node.right,
                    node.leaf ? ordered_base + node.begin : 0U,
                    node.leaf ? node.count : 0U,
                });
            }

            payload.segments.push_back({
                key,
                segment.nodes.empty() ? kInvalidId : node_base + segment.root,
            });
        }

        return payload;
    }

    [[nodiscard]] Hit trace(Ray ray) const {
        if (segments_.empty() || !normalize_ray(ray)) return {};

        float enter = kRayTMin;
        float exit = ray.t_max;
        if (!ray_aabb_interval(ray, occupied_bounds_, enter, exit)) return {};
        enter = std::max(enter, kRayTMin);
        exit = std::min(exit, ray.t_max);
        if (enter > exit) return {};

        constexpr float kBoundaryBias = 1.0e-4F;
        const Vec3 start = ray.origin + ray.direction * (enter + kBoundaryBias);
        SegmentCoord cell = coord(start);

        const int step_x = ray.direction.x > 0.0F ? 1 : (ray.direction.x < 0.0F ? -1 : 0);
        const int step_y = ray.direction.y > 0.0F ? 1 : (ray.direction.y < 0.0F ? -1 : 0);
        const int step_z = ray.direction.z > 0.0F ? 1 : (ray.direction.z < 0.0F ? -1 : 0);

        float next_x = next_boundary_t(ray, cell.x, 0, step_x);
        float next_y = next_boundary_t(ray, cell.y, 1, step_y);
        float next_z = next_boundary_t(ray, cell.z, 2, step_z);
        const float delta_x = step_delta(ray.direction.x);
        const float delta_y = step_delta(ray.direction.y);
        const float delta_z = step_delta(ray.direction.z);

        Hit best{};
        float cursor = enter;
        std::size_t guard = 0;
        const std::size_t max_steps = std::max<std::size_t>(64, segments_.size() * 16 + 64);

        while (cursor <= exit && guard++ < max_steps) {
            if (const auto found = segments_.find(cell); found != segments_.end()) {
                trace_segment(found->second, ray, best);
                if (best.hit && best.t <= cursor + kHitDistanceAbsTolerance) break;
            }

            const float next = std::min({next_x, next_y, next_z, exit});
            if (best.hit && best.t <= next + kHitDistanceAbsTolerance) break;
            if (next >= exit) break;

            if (next_x <= next_y && next_x <= next_z) {
                cell.x += step_x;
                cursor = next_x;
                next_x += delta_x;
            } else if (next_y <= next_z) {
                cell.y += step_y;
                cursor = next_y;
                next_y += delta_y;
            } else {
                cell.z += step_z;
                cursor = next_z;
                next_z += delta_z;
            }
        }

        if (guard >= max_steps) {
            throw std::runtime_error("hierarchical traversal DDA guard exceeded");
        }
        return best;
    }

    HierarchicalUpdateStats update(
        const std::vector<Triangle>& triangles,
        std::span<const std::uint32_t> moved) {
        if (triangles.size() != membership_.size()) {
            throw std::runtime_error("hierarchical update requires stable primitive count");
        }
        triangles_ = &triangles;

        std::unordered_set<SegmentCoord, SegmentCoordHash> rebuild;
        std::unordered_set<SegmentCoord, SegmentCoordHash> refit;
        HierarchicalUpdateStats stats{};
        stats.moved_primitives = moved.size();

        for (const auto primitive : moved) {
            if (primitive >= triangles.size()) {
                throw std::runtime_error("moved primitive id is out of range");
            }
            auto next = memberships_for(triangles[primitive]);
            auto& previous = membership_[primitive];
            if (next == previous) {
                for (const auto key : previous) refit.insert(key);
                continue;
            }

            ++stats.membership_changes;
            for (const auto key : previous) {
                if (!std::binary_search(next.begin(), next.end(), key)) {
                    auto segment_it = segments_.find(key);
                    if (segment_it != segments_.end()) {
                        auto& ids = segment_it->second.primitives;
                        ids.erase(std::remove(ids.begin(), ids.end(), primitive), ids.end());
                        rebuild.insert(key);
                    }
                }
            }
            for (const auto key : next) {
                if (!std::binary_search(previous.begin(), previous.end(), key)) {
                    segments_[key].primitives.push_back(primitive);
                    rebuild.insert(key);
                }
            }
            previous = std::move(next);
        }

        for (const auto key : rebuild) refit.erase(key);
        for (const auto key : refit) {
            auto found = segments_.find(key);
            if (found != segments_.end()) refit_segment(found->second);
        }
        for (const auto key : rebuild) {
            auto found = segments_.find(key);
            if (found == segments_.end()) continue;
            if (found->second.primitives.empty()) {
                segments_.erase(found);
                ++stats.removed_segments;
            } else {
                build_segment(segments_.at(key));
            }
        }

        stats.refit_segments = refit.size();
        stats.rebuilt_segments = rebuild.size() - stats.removed_segments;
        recompute_occupied_bounds();
        return stats;
    }

private:
    [[nodiscard]] SegmentCoord coord(Vec3 point) const noexcept {
        return {
            static_cast<std::int32_t>(std::floor(point.x / segment_size_)),
            static_cast<std::int32_t>(std::floor(point.y / segment_size_)),
            static_cast<std::int32_t>(std::floor(point.z / segment_size_)),
        };
    }

    [[nodiscard]] std::vector<SegmentCoord> memberships_for(const Triangle& triangle) const {
        const auto bounds = triangle_bounds(triangle);
        const auto lo = coord(bounds.min);
        const auto hi = coord(bounds.max);
        const std::int64_t nx = std::int64_t(hi.x) - lo.x + 1;
        const std::int64_t ny = std::int64_t(hi.y) - lo.y + 1;
        const std::int64_t nz = std::int64_t(hi.z) - lo.z + 1;
        if (nx <= 0 || ny <= 0 || nz <= 0 || nx * ny * nz > 4096) {
            throw std::runtime_error("triangle spans an unreasonable number of segments");
        }

        std::vector<SegmentCoord> keys;
        keys.reserve(static_cast<std::size_t>(nx * ny * nz));
        for (std::int32_t z = lo.z; z <= hi.z; ++z)
            for (std::int32_t y = lo.y; y <= hi.y; ++y)
                for (std::int32_t x = lo.x; x <= hi.x; ++x)
                    keys.push_back({x, y, z});
        std::sort(keys.begin(), keys.end());
        keys.erase(std::unique(keys.begin(), keys.end()), keys.end());
        return keys;
    }

    void rebuild_all(const std::vector<Triangle>& triangles) {
        triangles_ = &triangles;
        segments_.clear();
        membership_.assign(triangles.size(), {});
        for (std::uint32_t primitive = 0; primitive < triangles.size(); ++primitive) {
            auto keys = memberships_for(triangles[primitive]);
            for (const auto key : keys) segments_[key].primitives.push_back(primitive);
            membership_[primitive] = std::move(keys);
        }
        for (auto& [key, segment] : segments_) {
            (void)key;
            build_segment(segment);
        }
        recompute_occupied_bounds();
    }

    void build_segment(Segment& segment) {
        segment.ordered = segment.primitives;
        std::sort(segment.ordered.begin(), segment.ordered.end());
        segment.nodes.clear();
        segment.nodes.reserve(segment.ordered.size() * 2 + 1);
        if (segment.ordered.empty()) {
            segment.root = 0;
            segment.bounds = {};
            return;
        }
        segment.root = build_node(segment, 0, static_cast<std::uint32_t>(segment.ordered.size()));
        segment.bounds = segment.nodes[segment.root].bounds;
    }

    std::uint32_t build_node(Segment& segment, std::uint32_t begin, std::uint32_t end) {
        const auto index = static_cast<std::uint32_t>(segment.nodes.size());
        segment.nodes.push_back({});
        Aabb bounds{};
        Aabb centers{};
        for (auto cursor = begin; cursor < end; ++cursor) {
            const auto primitive = segment.ordered[cursor];
            const auto primitive_bounds = triangle_bounds(triangles_->at(primitive));
            bounds = merge(bounds, primitive_bounds);
            const auto point = center(primitive_bounds);
            centers = merge(centers, {point, point});
        }
        const auto count = end - begin;
        if (count <= 4) {
            segment.nodes[index] = {bounds, 0, 0, begin, count, true};
            return index;
        }

        const auto extent = centers.max - centers.min;
        const int axis = (extent.y > extent.x && extent.y >= extent.z)
            ? 1
            : (extent.z > extent.x ? 2 : 0);
        const auto middle = begin + count / 2;
        const auto coordinate = [&](std::uint32_t primitive) {
            const auto point = center(triangle_bounds(triangles_->at(primitive)));
            return axis == 0 ? point.x : (axis == 1 ? point.y : point.z);
        };
        std::nth_element(
            segment.ordered.begin() + begin,
            segment.ordered.begin() + middle,
            segment.ordered.begin() + end,
            [&](auto a, auto b) {
                const auto ca = coordinate(a);
                const auto cb = coordinate(b);
                return ca == cb ? a < b : ca < cb;
            });
        const auto left = build_node(segment, begin, middle);
        const auto right = build_node(segment, middle, end);
        segment.nodes[index] = {bounds, left, right, 0, 0, false};
        return index;
    }

    Aabb refit_node(Segment& segment, std::uint32_t index) {
        auto& node = segment.nodes[index];
        if (node.leaf) {
            Aabb bounds{};
            for (std::uint32_t offset = 0; offset < node.count; ++offset) {
                bounds = merge(
                    bounds,
                    triangle_bounds(triangles_->at(segment.ordered[node.begin + offset])));
            }
            return node.bounds = bounds;
        }
        return node.bounds = merge(
            refit_node(segment, node.left),
            refit_node(segment, node.right));
    }

    void refit_segment(Segment& segment) {
        if (segment.nodes.empty()) return;
        segment.bounds = refit_node(segment, segment.root);
    }

    void recompute_occupied_bounds() {
        occupied_bounds_ = {};
        for (const auto& [key, segment] : segments_) {
            (void)segment;
            const Vec3 minimum{
                float(key.x) * segment_size_,
                float(key.y) * segment_size_,
                float(key.z) * segment_size_,
            };
            const Vec3 maximum = minimum + Vec3{segment_size_, segment_size_, segment_size_};
            occupied_bounds_ = merge(occupied_bounds_, {minimum, maximum});
        }
    }

    [[nodiscard]] bool ray_aabb_interval(
        const Ray& ray,
        const Aabb& bounds,
        float& enter,
        float& exit) const noexcept {
        const float origin[3]{ray.origin.x, ray.origin.y, ray.origin.z};
        const float direction[3]{ray.direction.x, ray.direction.y, ray.direction.z};
        const float minimum[3]{bounds.min.x, bounds.min.y, bounds.min.z};
        const float maximum[3]{bounds.max.x, bounds.max.y, bounds.max.z};
        for (int axis = 0; axis < 3; ++axis) {
            if (std::abs(direction[axis]) < 1.0e-8F) {
                if (origin[axis] < minimum[axis] || origin[axis] > maximum[axis]) return false;
                continue;
            }
            float a = (minimum[axis] - origin[axis]) / direction[axis];
            float b = (maximum[axis] - origin[axis]) / direction[axis];
            if (a > b) std::swap(a, b);
            enter = std::max(enter, a);
            exit = std::min(exit, b);
            if (enter > exit) return false;
        }
        return true;
    }

    [[nodiscard]] float next_boundary_t(
        const Ray& ray,
        std::int32_t cell,
        int axis,
        int step) const noexcept {
        if (step == 0) return std::numeric_limits<float>::infinity();
        const float boundary = float(cell + (step > 0 ? 1 : 0)) * segment_size_;
        const float origin = axis == 0 ? ray.origin.x : (axis == 1 ? ray.origin.y : ray.origin.z);
        const float direction = axis == 0 ? ray.direction.x : (axis == 1 ? ray.direction.y : ray.direction.z);
        return (boundary - origin) / direction;
    }

    [[nodiscard]] float step_delta(float direction) const noexcept {
        return std::abs(direction) < 1.0e-8F
            ? std::numeric_limits<float>::infinity()
            : segment_size_ / std::abs(direction);
    }

    void trace_segment(const Segment& segment, const Ray& ray, Hit& best) const {
        if (segment.nodes.empty() ||
            !ray_aabb(ray, segment.bounds, best.hit ? best.t : ray.t_max)) return;

        std::vector<std::uint32_t> stack;
        stack.reserve(64);
        stack.push_back(segment.root);
        while (!stack.empty()) {
            const auto index = stack.back();
            stack.pop_back();
            const auto& node = segment.nodes[index];
            if (!ray_aabb(ray, node.bounds, best.hit ? best.t : ray.t_max)) continue;
            if (node.leaf) {
                for (std::uint32_t offset = 0; offset < node.count; ++offset) {
                    const auto primitive = segment.ordered[node.begin + offset];
                    if (auto hit = intersect_triangle(
                            triangles_->at(primitive),
                            ray,
                            best.hit ? best.t : ray.t_max);
                        hit && prefer_hit(*hit, best)) {
                        best = *hit;
                    }
                }
            } else {
                stack.push_back(node.left);
                stack.push_back(node.right);
            }
        }
    }

    const std::vector<Triangle>* triangles_{};
    float segment_size_{};
    std::unordered_map<SegmentCoord, Segment, SegmentCoordHash> segments_;
    std::vector<std::vector<SegmentCoord>> membership_;
    Aabb occupied_bounds_{};
};

} // namespace phos::gi::research::lane_b
