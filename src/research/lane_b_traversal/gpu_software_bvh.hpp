#pragma once

#include "b002_gpu_layout.hpp"
#include "traversal_common.hpp"

#include <algorithm>
#include <cstddef>
#include <cstdint>
#include <numeric>
#include <stdexcept>
#include <vector>

namespace phos::gi::research::lane_b {

class GpuSoftwareBvhData {
    struct Node {
        Aabb bounds{};
        std::uint32_t left{kInvalidId};
        std::uint32_t right{kInvalidId};
        std::uint32_t begin{};
        std::uint32_t count{};
    };

public:
    explicit GpuSoftwareBvhData(const std::vector<Triangle>& triangles) {
        rebuild(triangles);
    }

    void rebuild(const std::vector<Triangle>& triangles) {
        triangles_ = &triangles;
        ordered_.resize(triangles.size());
        std::iota(ordered_.begin(), ordered_.end(), 0U);
        nodes_.clear();
        nodes_.reserve(triangles.size() * 2U + 1U);
        root_ = triangles.empty()
            ? kInvalidId
            : build_node(0U, static_cast<std::uint32_t>(triangles.size()));
    }

    void refit(const std::vector<Triangle>& triangles) {
        if (triangles.size() != ordered_.size()) {
            throw std::runtime_error("GPU software BVH refit requires stable primitive count");
        }
        triangles_ = &triangles;
        if (root_ != kInvalidId) refit_node(root_);
    }

    [[nodiscard]] Hit trace(Ray ray) const {
        if (root_ == kInvalidId || !normalize_ray(ray)) return {};

        Hit best{};
        std::vector<std::uint32_t> stack;
        stack.reserve(64);
        stack.push_back(root_);
        while (!stack.empty()) {
            const auto index = stack.back();
            stack.pop_back();
            const auto& node = nodes_.at(index);
            if (!ray_aabb(
                    ray,
                    node.bounds,
                    best.hit ? best.t : ray.t_max)) {
                continue;
            }

            if (node.left == kInvalidId) {
                for (std::uint32_t offset = 0;
                     offset < node.count;
                     ++offset) {
                    const auto primitive =
                        ordered_.at(node.begin + offset);
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
        return best;
    }

    [[nodiscard]] std::uint32_t root() const noexcept { return root_; }
    [[nodiscard]] const std::vector<std::uint32_t>& ordered_primitives() const noexcept {
        return ordered_;
    }

    [[nodiscard]] std::vector<GpuBvhNode> gpu_nodes() const {
        std::vector<GpuBvhNode> output;
        output.reserve(nodes_.size());
        for (const auto& node : nodes_) {
            output.push_back(to_gpu_node(
                node.bounds,
                node.left,
                node.right,
                node.begin,
                node.count));
        }
        return output;
    }

    [[nodiscard]] std::size_t persistent_bytes() const noexcept {
        return nodes_.capacity() * sizeof(Node) +
               ordered_.capacity() * sizeof(std::uint32_t);
    }

private:
    std::uint32_t build_node(std::uint32_t begin, std::uint32_t end) {
        const auto index = static_cast<std::uint32_t>(nodes_.size());
        nodes_.push_back({});

        Aabb bounds{};
        Aabb centers{};
        for (auto cursor = begin; cursor < end; ++cursor) {
            const auto primitive = ordered_[cursor];
            const auto primitive_bounds =
                triangle_bounds(triangles_->at(primitive));
            bounds = merge(bounds, primitive_bounds);
            const auto point = center(primitive_bounds);
            centers = merge(centers, {point, point});
        }

        const auto count = end - begin;
        if (count <= 4U) {
            nodes_[index] = {
                bounds,
                kInvalidId,
                kInvalidId,
                begin,
                count,
            };
            return index;
        }

        const auto extent = centers.max - centers.min;
        const int axis =
            (extent.y > extent.x && extent.y >= extent.z)
            ? 1
            : (extent.z > extent.x ? 2 : 0);
        const auto middle = begin + count / 2U;
        const auto coordinate = [&](std::uint32_t primitive) {
            const auto point =
                center(triangle_bounds(triangles_->at(primitive)));
            return axis == 0 ? point.x : (axis == 1 ? point.y : point.z);
        };
        std::nth_element(
            ordered_.begin() + begin,
            ordered_.begin() + middle,
            ordered_.begin() + end,
            [&](auto a, auto b) {
                const auto ca = coordinate(a);
                const auto cb = coordinate(b);
                return ca == cb ? a < b : ca < cb;
            });

        const auto left = build_node(begin, middle);
        const auto right = build_node(middle, end);
        nodes_[index] = {bounds, left, right, 0U, 0U};
        return index;
    }

    Aabb refit_node(std::uint32_t index) {
        auto& node = nodes_[index];
        if (node.left == kInvalidId) {
            Aabb bounds{};
            for (std::uint32_t offset = 0; offset < node.count; ++offset) {
                bounds = merge(
                    bounds,
                    triangle_bounds(
                        triangles_->at(ordered_[node.begin + offset])));
            }
            return node.bounds = bounds;
        }
        return node.bounds = merge(
            refit_node(node.left),
            refit_node(node.right));
    }

    const std::vector<Triangle>* triangles_{};
    std::vector<Node> nodes_;
    std::vector<std::uint32_t> ordered_;
    std::uint32_t root_{kInvalidId};
};

} // namespace phos::gi::research::lane_b
