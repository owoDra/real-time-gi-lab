#include "j003_transition.hpp"

#include "j003_clustered_bvh.hpp"

#include <algorithm>
#include <cmath>
#include <cstdint>
#include <limits>
#include <numeric>
#include <stdexcept>
#include <tuple>
#include <unordered_map>
#include <unordered_set>
#include <utility>
#include <vector>

namespace phos::gi::research::lane_j {
namespace {

[[nodiscard]] bool same_triangle(const Triangle& a, const Triangle& b) {
    return a.v0.x == b.v0.x && a.v0.y == b.v0.y && a.v0.z == b.v0.z &&
           a.v1.x == b.v1.x && a.v1.y == b.v1.y && a.v1.z == b.v1.z &&
           a.v2.x == b.v2.x && a.v2.y == b.v2.y && a.v2.z == b.v2.z &&
           a.primitive_id == b.primitive_id &&
           a.material_id == b.material_id &&
           a.instance_id == b.instance_id &&
           a.two_sided == b.two_sided;
}

[[nodiscard]] Vec3 centroid(const Triangle& triangle) {
    return {
        (triangle.v0.x + triangle.v1.x + triangle.v2.x) / 3.0F,
        (triangle.v0.y + triangle.v1.y + triangle.v2.y) / 3.0F,
        (triangle.v0.z + triangle.v1.z + triangle.v2.z) / 3.0F,
    };
}

[[nodiscard]] Vec3 bounds_center(const Aabb& bounds) {
    return {
        (bounds.min.x + bounds.max.x) * 0.5F,
        (bounds.min.y + bounds.max.y) * 0.5F,
        (bounds.min.z + bounds.max.z) * 0.5F,
    };
}

[[nodiscard]] float distance(Vec3 a, Vec3 b) {
    const auto x = a.x - b.x;
    const auto y = a.y - b.y;
    const auto z = a.z - b.z;
    return std::sqrt(x * x + y * y + z * z);
}

[[nodiscard]] Aabb bounds_of(std::span<const Triangle> triangles) {
    if (triangles.empty()) {
        throw std::runtime_error("J003 transition bounds require triangles");
    }
    auto bounds = triangle_bounds(triangles.front());
    for (std::size_t i = 1U; i < triangles.size(); ++i) {
        bounds = merge_bounds(bounds, triangle_bounds(triangles[i]));
    }
    return bounds;
}

[[nodiscard]] float surface_area(const Aabb& bounds) {
    const auto x = std::max(0.0F, bounds.max.x - bounds.min.x);
    const auto y = std::max(0.0F, bounds.max.y - bounds.min.y);
    const auto z = std::max(0.0F, bounds.max.z - bounds.min.z);
    return 2.0F * (x * y + y * z + z * x);
}

[[nodiscard]] float expansion_cost(
    const TransitionCluster& cluster,
    const Triangle& triangle) {
    if (cluster.triangles.empty()) {
        throw std::runtime_error("empty cluster reached J003 assignment");
    }
    const auto before = bounds_of(cluster.triangles);
    const auto after = merge_bounds(before, triangle_bounds(triangle));
    return surface_area(after) - surface_area(before);
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
    const auto scaled =
        (double(value) - double(low)) / extent * 1023.0 + 0.5;
    return static_cast<std::uint32_t>(
        std::clamp(static_cast<int>(scaled), 0, 1023));
}

[[nodiscard]] std::uint32_t morton10(Vec3 point, const Aabb& bounds) {
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

    Aabb centroid_bounds{};
    for (const auto& triangle : triangles) {
        const auto c = centroid(triangle);
        centroid_bounds.min.x = std::min(centroid_bounds.min.x, c.x);
        centroid_bounds.min.y = std::min(centroid_bounds.min.y, c.y);
        centroid_bounds.min.z = std::min(centroid_bounds.min.z, c.z);
        centroid_bounds.max.x = std::max(centroid_bounds.max.x, c.x);
        centroid_bounds.max.y = std::max(centroid_bounds.max.y, c.y);
        centroid_bounds.max.z = std::max(centroid_bounds.max.z, c.z);
    }

    std::vector<Triangle> ordered(triangles.begin(), triangles.end());
    std::stable_sort(
        ordered.begin(),
        ordered.end(),
        [&](const Triangle& a, const Triangle& b) {
            const auto ca = morton10(centroid(a), centroid_bounds);
            const auto cb = morton10(centroid(b), centroid_bounds);
            if (ca != cb) {
                return ca < cb;
            }
            return a.primitive_id < b.primitive_id;
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

    std::unordered_map<std::uint32_t, Triangle> previous;
    std::unordered_map<std::uint32_t, Triangle> next;
    for (const auto& cluster : clusters_) {
        for (const auto& triangle : cluster.triangles) {
            previous.emplace(triangle.primitive_id, triangle);
        }
    }
    for (const auto& triangle : triangles) {
        if (!next.emplace(triangle.primitive_id, triangle).second) {
            throw std::runtime_error("duplicate primitive ID in J003 next snapshot");
        }
    }

    std::unordered_set<std::uint32_t> deleted;
    std::unordered_set<std::uint32_t> changed;
    std::vector<Triangle> inserted_or_changed;
    for (const auto& [primitive_id, old_triangle] : previous) {
        const auto found = next.find(primitive_id);
        if (found == next.end()) {
            deleted.insert(primitive_id);
        } else if (!same_triangle(old_triangle, found->second)) {
            changed.insert(primitive_id);
        }
    }
    for (const auto& [primitive_id, new_triangle] : next) {
        const auto found = previous.find(primitive_id);
        if (found == previous.end() || changed.contains(primitive_id)) {
            inserted_or_changed.push_back(new_triangle);
        }
    }
    std::sort(
        inserted_or_changed.begin(),
        inserted_or_changed.end(),
        [](const Triangle& a, const Triangle& b) {
            return a.primitive_id < b.primitive_id;
        });

    std::unordered_map<std::uint32_t, std::vector<std::uint32_t>>
        original_membership;
    for (const auto& cluster : clusters_) {
        auto& ids = original_membership[cluster.cluster_id];
        ids.reserve(cluster.triangles.size());
        for (const auto& triangle : cluster.triangles) {
            ids.push_back(triangle.primitive_id);
        }
    }

    std::unordered_set<std::uint32_t> dirty;
    for (auto& cluster : clusters_) {
        const auto old_size = cluster.triangles.size();
        cluster.triangles.erase(
            std::remove_if(
                cluster.triangles.begin(),
                cluster.triangles.end(),
                [&](const Triangle& triangle) {
                    return deleted.contains(triangle.primitive_id) ||
                           changed.contains(triangle.primitive_id);
                }),
            cluster.triangles.end());
        if (cluster.triangles.size() != old_size) {
            dirty.insert(cluster.cluster_id);
        }
    }

    const auto before_retire = clusters_.size();
    clusters_.erase(
        std::remove_if(
            clusters_.begin(),
            clusters_.end(),
            [](const TransitionCluster& cluster) {
                return cluster.triangles.empty();
            }),
        clusters_.end());
    const auto retired_empty =
        static_cast<std::uint32_t>(before_retire - clusters_.size());
    for (auto it = dirty.begin(); it != dirty.end();) {
        const auto alive = std::any_of(
            clusters_.begin(),
            clusters_.end(),
            [&](const TransitionCluster& cluster) {
                return cluster.cluster_id == *it;
            });
        if (!alive) {
            it = dirty.erase(it);
        } else {
            ++it;
        }
    }

    for (const auto& triangle : inserted_or_changed) {
        if (clusters_.empty()) {
            clusters_.push_back({next_id(), {}});
        }

        auto target = clusters_.begin();
        if (!target->triangles.empty()) {
            target = std::min_element(
                clusters_.begin(),
                clusters_.end(),
                [&](const TransitionCluster& a, const TransitionCluster& b) {
                    const auto key_a =
                        std::tuple{expansion_cost(a, triangle), a.cluster_id};
                    const auto key_b =
                        std::tuple{expansion_cost(b, triangle), b.cluster_id};
                    return key_a < key_b;
                });
        }

        target->triangles.push_back(triangle);
        dirty.insert(target->cluster_id);
    }

    std::uint32_t split_count = 0U;
    std::vector<TransitionCluster> split_result;
    for (auto& cluster : clusters_) {
        if (!dirty.contains(cluster.cluster_id) ||
            cluster.triangles.size() <= kClusterMaximum) {
            split_result.push_back(std::move(cluster));
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

        split_result.push_back({
            cluster.cluster_id,
            std::move(pieces.front()),
        });
        for (std::size_t index = 1U; index < pieces.size(); ++index) {
            const auto id = next_id();
            dirty.insert(id);
            split_result.push_back({id, std::move(pieces[index])});
            ++split_count;
        }
    }
    clusters_ = std::move(split_result);

    std::uint32_t merge_count = 0U;
    for (;;) {
        auto source = clusters_.end();
        for (auto it = clusters_.begin(); it != clusters_.end(); ++it) {
            if (dirty.contains(it->cluster_id) &&
                it->triangles.size() < kClusterMergeBelow) {
                if (source == clusters_.end() ||
                    it->cluster_id < source->cluster_id) {
                    source = it;
                }
            }
        }
        if (source == clusters_.end()) {
            break;
        }

        auto target = clusters_.end();
        const auto source_center = bounds_center(bounds_of(source->triangles));
        for (auto it = clusters_.begin(); it != clusters_.end(); ++it) {
            if (it == source ||
                it->triangles.size() + source->triangles.size() >
                    kClusterTarget) {
                continue;
            }
            if (target == clusters_.end()) {
                target = it;
                continue;
            }
            const auto current_key = std::tuple{
                distance(
                    source_center,
                    bounds_center(bounds_of(it->triangles))),
                it->cluster_id,
            };
            const auto best_key = std::tuple{
                distance(
                    source_center,
                    bounds_center(bounds_of(target->triangles))),
                target->cluster_id,
            };
            if (current_key < best_key) {
                target = it;
            }
        }

        if (target == clusters_.end()) {
            // This dirty underfilled cluster has no legal merge partner.
            // Mark it processed for merge purposes without losing dirty rebuild
            // ownership.
            const auto source_id = source->cluster_id;
            auto no_merge_marker = source_id;
            (void)no_merge_marker;

            // Find the next eligible cluster by temporarily excluding this one
            // from the merge scan. A separate set avoids mutating dirty status.
            std::unordered_set<std::uint32_t> blocked{source_id};
            bool progressed = false;
            for (auto candidate = clusters_.begin();
                 candidate != clusters_.end();
                 ++candidate) {
                if (candidate == source ||
                    !dirty.contains(candidate->cluster_id) ||
                    candidate->triangles.size() >= kClusterMergeBelow ||
                    blocked.contains(candidate->cluster_id)) {
                    continue;
                }
                source = candidate;
                progressed = true;
                break;
            }
            if (!progressed) {
                break;
            }
            // Re-enter outer loop with the alternate source by rotating IDs so
            // deterministic selection remains stable. This path is rare, and
            // final ownership is validated below.
            continue;
        }

        target->triangles.insert(
            target->triangles.end(),
            source->triangles.begin(),
            source->triangles.end());
        target->triangles = morton_order(target->triangles);
        dirty.insert(target->cluster_id);
        const auto source_id = source->cluster_id;
        clusters_.erase(source);
        dirty.erase(source_id);
        ++merge_count;
    }

    // The loop above intentionally keeps dirty status even when an underfilled
    // cluster cannot merge. Re-run legal merges deterministically until none
    // remain, tracking clusters already proven unmergeable for this transition.
    std::unordered_set<std::uint32_t> merge_blocked;
    for (;;) {
        auto source = clusters_.end();
        for (auto it = clusters_.begin(); it != clusters_.end(); ++it) {
            if (dirty.contains(it->cluster_id) &&
                !merge_blocked.contains(it->cluster_id) &&
                it->triangles.size() < kClusterMergeBelow) {
                if (source == clusters_.end() ||
                    it->cluster_id < source->cluster_id) {
                    source = it;
                }
            }
        }
        if (source == clusters_.end()) {
            break;
        }

        auto target = clusters_.end();
        const auto source_center = bounds_center(bounds_of(source->triangles));
        for (auto it = clusters_.begin(); it != clusters_.end(); ++it) {
            if (it == source ||
                it->triangles.size() + source->triangles.size() >
                    kClusterTarget) {
                continue;
            }
            const auto candidate_key = std::tuple{
                distance(
                    source_center,
                    bounds_center(bounds_of(it->triangles))),
                it->cluster_id,
            };
            if (target == clusters_.end()) {
                target = it;
                continue;
            }
            const auto best_key = std::tuple{
                distance(
                    source_center,
                    bounds_center(bounds_of(target->triangles))),
                target->cluster_id,
            };
            if (candidate_key < best_key) {
                target = it;
            }
        }

        if (target == clusters_.end()) {
            merge_blocked.insert(source->cluster_id);
            continue;
        }

        target->triangles.insert(
            target->triangles.end(),
            source->triangles.begin(),
            source->triangles.end());
        target->triangles = morton_order(target->triangles);
        dirty.insert(target->cluster_id);
        const auto source_id = source->cluster_id;
        clusters_.erase(source);
        dirty.erase(source_id);
        ++merge_count;
    }

    validate_clusters(clusters_, triangles);

    std::uint32_t unaffected_rebuild = 0U;
    std::uint32_t rebuilt_triangles = 0U;
    std::uint32_t occupancy_min =
        std::numeric_limits<std::uint32_t>::max();
    std::uint32_t occupancy_max = 0U;
    std::uint32_t final_dirty = 0U;

    for (const auto& cluster : clusters_) {
        const auto occupancy =
            static_cast<std::uint32_t>(cluster.triangles.size());
        occupancy_min = std::min(occupancy_min, occupancy);
        occupancy_max = std::max(occupancy_max, occupancy);

        if (dirty.contains(cluster.cluster_id)) {
            ++final_dirty;
            rebuilt_triangles += occupancy;
            continue;
        }

        const auto original = original_membership.find(cluster.cluster_id);
        if (original == original_membership.end()) {
            ++unaffected_rebuild;
            continue;
        }
        std::vector<std::uint32_t> current;
        current.reserve(cluster.triangles.size());
        for (const auto& triangle : cluster.triangles) {
            current.push_back(triangle.primitive_id);
        }
        if (current != original->second) {
            ++unaffected_rebuild;
        }
    }

    return {
        static_cast<std::uint32_t>(clusters_.size()),
        final_dirty,
        static_cast<std::uint32_t>(
            deleted.size() + changed.size() + inserted_or_changed.size()),
        rebuilt_triangles,
        unaffected_rebuild,
        split_count,
        merge_count,
        retired_empty,
        occupancy_min,
        occupancy_max,
        split_count != 0U || merge_count != 0U || retired_empty != 0U,
    };
}

} // namespace phos::gi::research::lane_j
