#pragma once

#include "../lane_a_split_rc/a001_runtime.hpp"

#include <cstddef>
#include <cstdint>
#include <memory>

namespace phos::gi::lane_d {

enum class D001Mode {
    Full,
    DepthReuse,
    OwnerReuse,
};

const char* mode_name(D001Mode mode);

enum class ProducerEmissionDomain {
    SurfaceScan,
    VisibleTileScan,
};

const char* emission_domain_name(ProducerEmissionDomain domain);

enum class ProducerAllocationMode {
    PerOwnerAtomic,
    WorkgroupPrefix,
};

const char* allocation_mode_name(ProducerAllocationMode mode);

struct D001StageTimings {
    double visibility_reset_us{};
    double visibility_depth_us{};
    double owner_reset_us{};
    double visibility_owner_us{};
    double producer_reset_us{};
    double producer_emit_us{};
    double finalize_us{};
    double gather_us{};
    double merge_us{};
    double resolve_us{};

    [[nodiscard]] double visibility_depth_prerequisite_us() const {
        return visibility_reset_us + visibility_depth_us;
    }

    [[nodiscard]] double visibility_owner_prerequisite_us() const {
        return visibility_reset_us + visibility_depth_us +
               owner_reset_us + visibility_owner_us;
    }

    [[nodiscard]] double incremental_producer_us() const {
        return owner_reset_us + visibility_owner_us +
               producer_reset_us + producer_emit_us + finalize_us;
    }

    [[nodiscard]] double incremental_end_to_end_us() const {
        return incremental_producer_us() +
               gather_us + merge_us + resolve_us;
    }
};

struct D001Memory {
    std::size_t physical_persistent_bytes{};
    std::size_t physical_transient_bytes{};
    std::size_t physical_resident_bytes{};

    std::size_t gi_owned_persistent_bytes{};
    std::size_t gi_owned_transient_bytes{};
    std::size_t producer_scratch_bytes{};
    std::size_t stream_capacity_bytes{};
    std::size_t reused_visibility_bytes{};
    std::size_t prerequisite_visibility_bytes{};
};

class D001Runtime {
public:
    D001Runtime(
        VulkanContext& context,
        const lane_a::SceneSurfaceSet& scene,
        const lane_a::A001ParamsGpu& params,
        D001Mode mode,
        ProducerEmissionDomain emission_domain =
            ProducerEmissionDomain::SurfaceScan,
        ProducerAllocationMode allocation_mode =
            ProducerAllocationMode::PerOwnerAtomic);
    ~D001Runtime();

    D001Runtime(const D001Runtime&) = delete;
    D001Runtime& operator=(const D001Runtime&) = delete;

    D001StageTimings measure(std::uint32_t iterations);
    lane_a::A001Readback readback();
    [[nodiscard]] D001Memory memory() const;

private:
    struct Impl;
    std::unique_ptr<Impl> impl_;
};

} // namespace phos::gi::lane_d
