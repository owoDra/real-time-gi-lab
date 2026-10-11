#pragma once

#include "j003_clustered_bvh.hpp"
#include "j003_types.hpp"
#include "vk_context.hpp"

#include <cstddef>
#include <filesystem>
#include <span>
#include <string>
#include <vector>

namespace phos::gi::research::lane_j {

struct GpuAllocationRecord {
    std::string name;
    std::string allocation_class;
    std::size_t logical_bytes{};
    std::size_t allocation_bytes{};
};

struct GpuTraversalResult {
    std::vector<GpuHit> hits;
    double traversal_gpu_us{};
    std::size_t candidate_persistent_bytes{};
    std::size_t validation_harness_bytes{};
    std::vector<GpuAllocationRecord> allocations;
};

[[nodiscard]] GpuTraversalResult run_gpu_traversal_probe(
    VulkanContext& context,
    const ClusteredBvhData& bvh,
    std::span<const GpuRay> rays,
    const std::filesystem::path& shader_path);

} // namespace phos::gi::research::lane_j
