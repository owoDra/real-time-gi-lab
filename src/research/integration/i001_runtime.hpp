#pragma once

#include <cstddef>
#include <cstdint>
#include <filesystem>
#include <memory>
#include <string>

namespace phos::gi::research::integration {

enum class I001Variant {
    VanillaSoftware,
    CombinedHwrt,
    RigidInstanceHwrtUpdate,
    RigidInstanceHwrtBuild,
    RigidInstanceSoftwareBinary,
    RigidInstanceSoftwareQuantized,
    DeformingLocalHwrt,
    DeformingLocalSoftwareQuantized,
    LaneEFinalHwrt,
    LaneEFinalSoftware,
    CombinedSoftware,
    DepthReuseHwrt,
    BoundedHwrt,
};

enum class I001Scenario {
    Static,
    CameraMotion,
    LightMotion,
    MovingRigid,
    DeformingControl,
    SparseStress,
    DenseStress,
    LargeWorldStress,
    VerticalWorldStress,
};

[[nodiscard]] const char* i001_variant_name(I001Variant value) noexcept;
[[nodiscard]] const char* i001_scenario_name(I001Scenario value) noexcept;
[[nodiscard]] I001Variant i001_parse_variant(const std::string& value);
[[nodiscard]] I001Scenario i001_parse_scenario(const std::string& value);

struct I001FrameTimings {
    double renderer_depth_us{};
    double frame_init_us{};
    double visibility_reuse_us{};
    double producer_us{};
    double ray_prepare_us{};
    double traversal_maintenance_gpu_us{};
    double dynamic_update_wall_us{};
    double geometry_prepare_cpu_us{};
    double surface_update_gpu_us{};
    double geometry_transfer_wall_us{};
    double geometry_transfer_gpu_us{};
    double instance_transfer_wall_us{};
    double instance_transfer_gpu_us{};
    double blas_update_us{};
    double tlas_update_us{};
    double membership_update_cpu_us{};
    double hierarchy_refit_cpu_us{};
    double hierarchy_rebuild_cpu_us{};
    double hierarchy_occupancy_cpu_us{};
    double packing_cpu_us{};
    double hierarchy_upload_gpu_us{};
    double software_bvh_rebuild_cpu_us{};
    double traversal_us{};
    double radiance_us{};
    double merge_us{};
    double storage_update_us{};
    double invalidation_us{};
    double resolve_us{};
    double complete_gpu_us{};
    double incremental_gi_us{};
};

struct I001FrameStats {
    std::uint32_t work_items{};
    std::uint32_t outputs{};
    std::uint32_t requested_work_items{};
    std::uint32_t requested_outputs{};
    std::uint32_t overflow{};
    std::uint32_t visible_owners{};
    std::uint32_t moved_primitives{};
    std::uint32_t segment_membership_changes{};
    std::uint32_t hierarchy_refit_segments{};
    std::uint32_t hierarchy_rebuilt_segments{};
    std::uint32_t storage_allocations{};
    std::uint32_t storage_updates{};
    std::uint32_t storage_invalidations{};
    std::uint32_t storage_failures{};
};

struct I001Memory {
    std::size_t persistent_bytes{};
    std::size_t transient_bytes{};
    std::size_t scratch_bytes{};
    std::size_t peak_resident_bytes{};
    std::size_t stream_capacity_bytes{};
    std::size_t storage_capacity_bytes{};
};

struct I001Quality {
    std::size_t visibility_mismatches{};
    std::size_t producer_semantic_errors{};
    std::size_t hit_mismatches{};
    std::size_t nearest_hit_tie_mismatches{};
    std::size_t traversal_runtime_errors{};
    std::size_t static_owner_mutations{};
    std::size_t unrelated_owner_mutations{};
    std::size_t missing_probes{};
    std::size_t leaked_probes{};
    std::size_t stale_storage_slots{};
    std::size_t resolved_output_mismatches{};
    double radiance_rms_error{};
    double radiance_max_abs_error{};
    double temporal_rms_error{};
    double temporal_max_abs_error{};
    std::uint64_t workload_digest{};
    std::uint64_t resolved_output_digest{};
    std::uint64_t geometry_input_digest{};
    bool passed{};
};

struct I001AllocationStats {
    std::size_t current_bytes{};
    std::size_t peak_bytes{};
    std::size_t allocation_count{};
    std::size_t free_count{};
    std::size_t live_allocations{};
};

struct I001FrameResult {
    I001FrameTimings timings;
    I001FrameStats stats;
    I001Memory memory;
    I001Quality quality;
};

struct I001Options {
    std::filesystem::path scene{
        "assets/Vulkan-Samples-Assets/scenes/sponza/Sponza01.gltf"};
    I001Variant variant{I001Variant::VanillaSoftware};
    I001Scenario scenario{I001Scenario::Static};
    bool validation{};
    std::uint32_t bounded_owner_capacity{1280};
};

class I001Runtime {
public:
    explicit I001Runtime(I001Options options);
    ~I001Runtime();

    I001Runtime(const I001Runtime&) = delete;
    I001Runtime& operator=(const I001Runtime&) = delete;

    [[nodiscard]] I001FrameResult run_frame(bool target_state);
    [[nodiscard]] I001Quality validate_last_frame();

    [[nodiscard]] const I001Memory& memory() const noexcept;
    [[nodiscard]] const std::string& device_name() const noexcept;
    [[nodiscard]] const std::string& driver_name() const noexcept;
    [[nodiscard]] const std::string& driver_info() const noexcept;
    [[nodiscard]] std::uint32_t api_version() const noexcept;
    [[nodiscard]] float timestamp_period_ns() const noexcept;
    [[nodiscard]] I001AllocationStats allocation_stats() const noexcept;
    void reset_allocation_epoch() noexcept;

private:
    struct Impl;
    std::unique_ptr<Impl> impl_;
};

} // namespace phos::gi::research::integration
