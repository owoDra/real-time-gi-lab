#include "j003_transition.hpp"

#include <algorithm>
#include <cmath>
#include <cstdint>
#include <limits>
#include <stdexcept>
#include <tuple>
#include <unordered_map>
#include <unordered_set>
#include <utility>
#include <vector>

namespace phos::gi::research::lane_j {
namespace {

struct DVec3 {
    double x{};
    double y{};
    double z{};
};

struct DAabb {
    DVec3 min{
        std::numeric_limits<double>::infinity(),
        std::numeric_limits<double>::infinity(),
        std::numeric_limits<double>::infinity(),
    };
    DVec3 max{
        -std::numeric_limits<double>::infinity(),
        -std::numeric_limits<double>::infinity(),
        -std::numeric_limits<double>::infinity(),
    };
};

[[nodiscard]] bool same_triangle(const Triangle& a, const Triangle& b) {
    return a.v0.x == b.v0.x && a.v0.y == b.v0.y && a.v0.z == b.v0.z &&
           a.v1.x == b.v1.x && a.v1.y == b.v1.y && a.v1.z == b.v1.z &&
           a.v2.x == b.v2.x && a.v2.y == b.v2.y && a.v2.z == b.v2.z &&
           a.primitive_id == b.primitive_id &&
           a.material_id == b.material_id &&
           a.instance_id == b.instance_id &&
           a.two_sided == b.two_sided;
}

[[nodiscard]] DVec3 centroid(const Triangle& triangle) {
    return {
        (double(triangle.v0.x) + double(triangle.v1.x) +
         double(triangle.v2.x)) /
            3.0,
        (double(triangle.v0.y) + double(triangle.v1.y) +
         double(triangle.v2.y)) /
            3.0,
        (double(triangle.v0.z) + double(triangle.v1.z) +
         double(triangle.v2.z)) /
            3.0,
    };
}

void include(DAabb& bounds, DVec3 point) {
    bounds.min.x = std::min(bounds.min.x, point.x);
    bounds.min.y = std::min(bounds.min.y, point.y);
    bounds.min.z = std::min(bounds.min.z, point.z);
    bounds.max.x = std::max(bounds.max.x, point.x);
    bounds.max.y = std::max(bounds.max.y, point.y);
    bounds.max.z = std::max(bounds.max.z, point.z);
}

void include(DAabb& bounds, const Triangle& triangle) {
    include(bounds, DVec3{
        double(triangle.v0.x),
        double(triangle.v0.y),
        double(triangle.v0.z),
    });
    include(bounds, DVec3{
        double(triangle.v1.x),
        double(triangle.v1.y),
        double(triangle.v1.z),
    });
    include(bounds, DVec3{
        double(triangle.v2.x),
        double(triangle.v2.y),
        double(triangle.v2.z),
    });
}

[[nodiscard]] DAabb bounds_of(std::span<const Triangle> triangles) {
    if (triangles.empty()) {
        throw std::runtime_error("J003 transition bounds require triangles");
    }
    DAabb bounds{};
    for (const auto& triangle : triangles) {
        include(bounds, triangle);
    }
    return bounds;
}

[[nodiscard]] DVec3 bounds_center(const DAabb& bounds) {
    return {
        (bounds.min.x + bounds.max.x) * 0.5,
        (bounds.min.y + bounds.max.y) * 0.5,
        (bounds.min.z + bounds.max.z) * 0.5,
    };
}

[[nodiscard]] double surface_area(const DAabb& bounds) {
    const auto x = std::max(0.0, bounds.max.x - bounds.min.x);
    const auto y = std::max(0.0, bounds.max.y - bounds.min.y);
    const auto z = std::max(0.0, bounds.max.z - bounds.min.z);
    return 2.0 * (x * y + y * z + z * x);
}

[[nodiscard]] double expansion_cost(
    const TransitionCluster& cluster,
    const Triangle& triangle) {
    if (cluster.triangles.empty()) {
        throw std::runtime_error("empty cluster reached J003 assignment");
    }
    const auto before = bounds_of(cluster.triangles);
    auto after = before;
    include(after, triangle);
    return surface_area(after) - surface_area(before);
}

[[nodiscard]] double distance(DVec3 a, DVec3 b) {
    const auto x = a.x - b.x;
    const auto y = a.y - b.y;
    const auto z = a.z - b.z;
    return std::sqrt(x * x + y * y + z * z);
}

[[nodiscard]] std::uint32_t spread10(std::uint32_t value) {
    std::uint32_t result = 0U;
    for (std::uint32_t bit = 0U; bit < 10U; ++bit) {
        result |= ((value >> bit) & 1U) << (3U * bit);
    }
    return result;
}

[[nodiscard]] std::uint32_t quantize10(
    double value,
    double low,
    double high) {
    const auto extent = std::max(high - low, 1.0e-9);
    const auto scaled = (value - low) / extent * 1023.0 + 0.5;
    return static_cast<std::uint32_t>(
        std::clamp(static_cast<int>(scaled), 0, 1023));
}

[[nodiscard]] std::uint32_t morton10(
    DVec3 point,
    const DAabb& bounds) {
    const auto x = quantize10(point.x, bounds.min.x, bounds.max.x);
    const auto y = quantize10(point.y, bounds.min.y, bounds.max.y);
    const auto z = quantize10(point.z, bounds.min.z, bounds.max.z);
    return spread10(x) | (spread10(y) << 1U) | (spread10(z) << 2U);
}

[[nodiscard]] std::vector<Triangle> morton_order(
    std::span<const Triangle> triangles) {
    if (triangles.empty()) {
        return {};
    }

    DAabb centroid_bounds{};
    for (const auto& triangle : triangles) {
        include(centroid_bounds, centroid(triangle));
    }

    std::vector<Triangle> ordered(triangles.begin(), triangles.end());
    std::sort(
        ordered.begin(),
        ordered.end(),
        [&](const Triangle& a, const Triangle& b) {
            const auto code_a = morton10(centroid(a), centroid_bounds);
            const auto code_b = morton10(centroid(b), centroid_bounds);
            return std::tuple{code_a, a.primitive_id} <
                   std::tuple{code_b, b.primitive_id};
        });
    return ordered;
}

void validate_clusters(
    const std::vector<TransitionCluster>& clusters,
    std::span<const Triangle> triangles) {
    if (clusters.empty()) {
        throw std::runtime_error("J003 transition state has no clusters");
    }

    std::unordered_set<std::uint32_t> expected;
    expected.reserve(triangles.size());
    for (const auto& triangle : triangles) {
        if (!expected.insert(triangle.primitive_id).second) {
            throw std::runtime_error("duplicate primitive ID in J003 snapshot");
        }
    }

    std::unordered_set<std::uint32_t> actual;
    actual.reserve(triangles.size());
    for (const auto& cluster : clusters) {
        if (cluster.triangles.empty()) {
            throw std::runtime_error("J003 empty cluster persisted");
        }
        if (cluster.triangles.size() > kClusterMaximum) {
            throw std::runtime_error("J003 cluster maximum exceeded");
        }
        for (const auto& triangle : cluster.triangles) {
            if (!actual.insert(triangle.primitive_id).second) {
                throw std::runtime_error("J003 primitive has multiple owners");
            }
        }
    }

    if (actual != expected) {
        throw std::runtime_error("J003 cluster ownership mismatch");
    }
}

} // namespace

ClusterTransitionState::ClusterTransitionState(
    std::span<const Triangle> triangles) {
    if (triangles.empty()) {
        throw std::runtime_error("J003 transition state requires triangles");
    }

    const auto ordered = morton_order(triangles);
    for (std::size_t begin = 0U;
         begin < ordered.size();
         begin += kClusterTarget) {
        const auto end = std::min(
            ordered.size(),
            begin + std::size_t(kClusterTarget));
        clusters_.push_back({
            next_id(),
            std::vector<Triangle>(
                ordered.begin() + static_cast<std::ptrdiff_t>(begin),
                ordered.begin() + static_cast<std::ptrdiff_t>(end)),
        });
    }
    validate_clusters(clusters_, triangles);
}

TransitionStats ClusterTransitionState::update(
    std::span<const Triangle> triangles) {
    if (triangles.empty()) {
        throw std::runtime_error("J003 transition cannot update to empty geometry");
    }

    std::unordered_map<std::uint32_t, Triangle> old_triangles;
    std::unordered_map<std::uint32_t, Triangle> new_triangles;
    old_triangles.reserve(triangles.size());
    new_triangles.reserve(triangles.size());

    for (const auto& cluster : clusters_) {
        for (const auto& triangle : cluster.triangles) {
            old_triangles.emplace(triangle.primitive_id, triangle);
        }
    }
    for (const auto& triangle : triangles) {
        if (!new_triangles.emplace(triangle.primitive_id, triangle).second) {
            throw std::runtime_error(
                "duplicate primitive ID in J003 next snapshot");
        }
    }

    std::unordered_set<std::uint32_t> deleted;
    std::unordered_set<std::uint32_t> inserted;
    std::unordered_set<std::uint32_t> changed;
    for (const auto& [primitive_id, old_triangle] : old_triangles) {
        const auto next = new_triangles.find(primitive_id);
        if (next == new_triangles.end()) {
            deleted.insert(primitive_id);
        } else if (!same_triangle(old_triangle, next->second)) {
            changed.insert(primitive_id);
        }
    }
    for (const auto& [primitive_id, triangle] : new_triangles) {
        (void)triangle;
        if (!old_triangles.contains(primitive_id)) {
            inserted.insert(primitive_id);
        }
    }

    std::unordered_map<std::uint32_t, std::vector<std::uint32_t>>
        original_membership;
    original_membership.reserve(clusters_.size());
    for (const auto& cluster : clusters_) {
        auto& ids = original_membership[cluster.cluster_id];
        ids.reserve(cluster.triangles.size());
        for (const auto& triangle : cluster.triangles) {
            ids.push_back(triangle.primitive_id);
        }
    }

    std::unordered_set<std::uint32_t> dirty;
    for (auto& cluster : clusters_) {
        const auto before = cluster.triangles.size();
        cluster.triangles.erase(
            std::remove_if(
                cluster.triangles.begin(),
                cluster.triangles.end(),
                [&](const Triangle& triangle) {
                    return deleted.contains(triangle.primitive_id) ||
                           changed.contains(triangle.primitive_id);
                }),
            cluster.triangles.end());
        if (cluster.triangles.size() != before) {
            dirty.insert(cluster.cluster_id);
        }
    }

    std::unordered_set<std::uint32_t> retired_ids;
    for (const auto& cluster : clusters_) {
        if (cluster.triangles.empty()) {
            retired_ids.insert(cluster.cluster_id);
        }
    }
    if (!retired_ids.empty()) {
        clusters_.erase(
            std::remove_if(
                clusters_.begin(),
                clusters_.end(),
                [&](const TransitionCluster& cluster) {
                    return retired_ids.contains(cluster.cluster_id);
                }),
            clusters_.end());
        for (const auto id : retired_ids) {
            dirty.erase(id);
        }
    }

    std::vector<std::uint32_t> reassigned_ids;
    reassigned_ids.reserve(inserted.size() + changed.size());
    reassigned_ids.insert(
        reassigned_ids.end(), inserted.begin(), inserted.end());
    reassigned_ids.insert(
        reassigned_ids.end(), changed.begin(), changed.end());
    std::sort(reassigned_ids.begin(), reassigned_ids.end());

    for (const auto primitive_id : reassigned_ids) {
        const auto triangle = new_triangles.at(primitive_id);

        if (clusters_.empty()) {
            clusters_.push_back({next_id(), {}});
        }

        auto target = clusters_.begin();
        if (!target->triangles.empty()) {
            target = std::min_element(
                clusters_.begin(),
                clusters_.end(),
                [&](const TransitionCluster& a, const TransitionCluster& b) {
                    return std::tuple{
                               expansion_cost(a, triangle),
                               a.cluster_id,
                           } <
                           std::tuple{
                               expansion_cost(b, triangle),
                               b.cluster_id,
                           };
                });
        }

        target->triangles.push_back(triangle);
        dirty.insert(target->cluster_id);
    }

    std::uint32_t split_count = 0U;
    std::sort(
        clusters_.begin(),
        clusters_.end(),
        [](const TransitionCluster& a, const TransitionCluster& b) {
            return a.cluster_id < b.cluster_id;
        });

    std::vector<TransitionCluster> rebuilt;
    rebuilt.reserve(clusters_.size());
    for (auto& cluster : clusters_) {
        if (!dirty.contains(cluster.cluster_id) ||
            cluster.triangles.size() <= kClusterMaximum) {
            rebuilt.push_back(std::move(cluster));
            continue;
        }

        std::vector<std::vector<Triangle>> queue{
            morton_order(cluster.triangles),
        };
        std::vector<std::vector<Triangle>> pieces;
        while (!queue.empty()) {
            auto current = std::move(queue.front());
            queue.erase(queue.begin());
            if (current.size() <= kClusterMaximum) {
                pieces.push_back(std::move(current));
                continue;
            }

            const auto cut = current.size() / 2U;
            std::vector<Triangle> left(
                current.begin(),
                current.begin() + static_cast<std::ptrdiff_t>(cut));
            std::vector<Triangle> right(
                current.begin() + static_cast<std::ptrdiff_t>(cut),
                current.end());
            queue.push_back(std::move(left));
            queue.push_back(std::move(right));
        }

        rebuilt.push_back({
            cluster.cluster_id,
            std::move(pieces.front()),
        });
        for (std::size_t index = 1U; index < pieces.size(); ++index) {
            const auto id = next_id();
            rebuilt.push_back({id, std::move(pieces[index])});
            dirty.insert(id);
            ++split_count;
        }
    }
    clusters_ = std::move(rebuilt);

    std::uint32_t merge_count = 0U;
    for (;;) {
        bool merged = false;
        std::sort(
            clusters_.begin(),
            clusters_.end(),
            [](const TransitionCluster& a, const TransitionCluster& b) {
                return a.cluster_id < b.cluster_id;
            });

        for (auto source = clusters_.begin();
             source != clusters_.end();
             ++source) {
            if (!dirty.contains(source->cluster_id) ||
                source->triangles.size() >= kClusterMergeBelow) {
                continue;
            }

            auto target = clusters_.end();
            const auto source_center =
                bounds_center(bounds_of(source->triangles));

            for (auto candidate = clusters_.begin();
                 candidate != clusters_.end();
                 ++candidate) {
                if (candidate == source ||
                    candidate->triangles.empty() ||
                    candidate->triangles.size() + source->triangles.size() >
                        kClusterTarget) {
                    continue;
                }

                if (target == clusters_.end()) {
                    target = candidate;
                    continue;
                }

                const auto candidate_key = std::tuple{
                    distance(
                        source_center,
                        bounds_center(bounds_of(candidate->triangles))),
                    candidate->cluster_id,
                };
                const auto target_key = std::tuple{
                    distance(
                        source_center,
                        bounds_center(bounds_of(target->triangles))),
                    target->cluster_id,
                };
                if (candidate_key < target_key) {
                    target = candidate;
                }
            }

            if (target == clusters_.end()) {
                continue;
            }

            target->triangles.insert(
                target->triangles.end(),
                source->triangles.begin(),
                source->triangles.end());
            target->triangles = morton_order(target->triangles);
            dirty.insert(target->cluster_id);

            const auto removed_id = source->cluster_id;
            clusters_.erase(source);
            dirty.erase(removed_id);

            ++merge_count;
            merged = true;
            break;
        }

        if (!merged) {
            break;
        }
    }

    validate_clusters(clusters_, triangles);

    std::uint32_t final_dirty_count = 0U;
    std::uint32_t rebuilt_triangle_count = 0U;
    std::uint32_t unaffected_rebuild_count = 0U;
    std::uint32_t occupancy_min =
        std::numeric_limits<std::uint32_t>::max();
    std::uint32_t occupancy_max = 0U;

    for (const auto& cluster : clusters_) {
        const auto occupancy =
            static_cast<std::uint32_t>(cluster.triangles.size());
        occupancy_min = std::min(occupancy_min, occupancy);
        occupancy_max = std::max(occupancy_max, occupancy);

        if (dirty.contains(cluster.cluster_id)) {
            ++final_dirty_count;
            rebuilt_triangle_count += occupancy;
            continue;
        }

        const auto original = original_membership.find(cluster.cluster_id);
        std::vector<std::uint32_t> current_ids;
        current_ids.reserve(cluster.triangles.size());
        for (const auto& triangle : cluster.triangles) {
            current_ids.push_back(triangle.primitive_id);
        }
        if (original == original_membership.end() ||
            original->second != current_ids) {
            ++unaffected_rebuild_count;
        }
    }

    std::vector<std::uint32_t> dirty_ids;
    dirty_ids.reserve(final_dirty_count);
    for (const auto& cluster : clusters_) {
        if (dirty.contains(cluster.cluster_id)) {
            dirty_ids.push_back(cluster.cluster_id);
        }
    }
    std::sort(dirty_ids.begin(), dirty_ids.end());

    std::vector<std::uint32_t> retired_cluster_ids(
        retired_ids.begin(),
        retired_ids.end());
    std::sort(retired_cluster_ids.begin(), retired_cluster_ids.end());

    return {
        static_cast<std::uint32_t>(clusters_.size()),
        final_dirty_count,
        static_cast<std::uint32_t>(
            deleted.size() + inserted.size() + changed.size()),
        rebuilt_triangle_count,
        unaffected_rebuild_count,
        split_count,
        merge_count,
        static_cast<std::uint32_t>(retired_ids.size()),
        occupancy_min,
        occupancy_max,
        split_count != 0U ||
            merge_count != 0U ||
            !retired_ids.empty(),
        std::move(dirty_ids),
        std::move(retired_cluster_ids),
    };
}

} // namespace phos::gi::research::lane_j
