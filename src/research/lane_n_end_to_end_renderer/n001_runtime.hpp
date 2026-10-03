#pragma once

#include <cstddef>
#include <cstdint>
#include <filesystem>
#include <memory>
#include <string>
#include <vector>

#include "imported/lane_a_split_rc/a001_runtime.hpp"
#include "imported/lane_a_split_rc/a001_types.hpp"
#include "imported/lane_b_traversal/traversal_contract.hpp"

namespace phos::gi::research::integration {

namespace lane_a = phos::gi::lane_a;
namespace lane_b = phos::gi::research::lane_b;

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
    double primary_visibility_us{};
    double composite_us{};
    double complete_gpu_us{};
    double complete_renderer_gpu_us{};
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
    std::uint32_t topology_mutations{};
    std::uint32_t topology_replaced_primitives{};
    std::uint32_t backend_rebuilds{};
    std::uint32_t storage_allocations{};
    std::uint32_t storage_updates{};
    std::uint32_t storage_invalidations{};
    std::uint32_t storage_failures{};
};

struct I001Memory {
    std::size_t persistent_bytes{};
    std::size_t transient_bytes{};
    std::size_t scratch_bytes{};
    std::size_t old_new_overlap_bytes{};
    std::size_t peak_resident_bytes{};
    std::size_t stream_capacity_bytes{};
    std::size_t storage_capacity_bytes{};
    std::size_t image_bytes{};
};

struct I001N003HostMemory {
    std::size_t scene_surface_capacity_bytes{};
    std::size_t scene_triangle_capacity_bytes{};
    std::size_t dynamic_selection_capacity_bytes{};
    std::size_t candidate_structure_capacity_bytes{};
    std::size_t renderer_owned_total_bytes{};
};

struct I001N004HitDiagnostics {
    std::size_t strict_mismatches{};
    std::size_t surface_tie_equivalent_mismatches{};
    std::size_t substantive_mismatches{};
};

struct I001RendererReadback {
    std::uint32_t width{};
    std::uint32_t height{};
    lane_a::A001ParamsGpu params{};
    std::vector<float> image_rgba;
    std::vector<lane_a::SurfaceSampleGpu> surfaces;
    std::vector<lane_b::Triangle> triangles;
};

struct I001Quality {
    std::size_t visibility_mismatches{};
    std::size_t producer_semantic_errors{};
    std::size_t hit_mismatches{};
    std::size_t traversal_runtime_errors{};
    std::size_t missing_probes{};
    std::size_t leaked_probes{};
    std::size_t stale_storage_slots{};
    std::size_t resolved_output_mismatches{};
    double radiance_rms_error{};
    double radiance_max_abs_error{};
    double temporal_rms_error{};
    double temporal_max_abs_error{};
    bool passed{};
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
    [[nodiscard]] I001FrameResult run_topology_churn_frame();

    void configure_n003_vanilla_software_baseline();
    [[nodiscard]] I001FrameResult run_n003_vanilla_topology_churn_frame();
    [[nodiscard]] I001N003HostMemory n003_host_memory() const noexcept;

    // N004-only controls/diagnostics. Historical N001-N003 validation remains
    // strict; N004 separately identifies geometrically equivalent primitive-ID
    // ties without changing I001Quality::passed.
    void set_n004_motion_fraction(float fraction);
    [[nodiscard]] I001N004HitDiagnostics n004_hit_diagnostics();

    [[nodiscard]] I001Quality validate_last_frame();
    [[nodiscard]] I001RendererReadback renderer_readback();

    [[nodiscard]] const I001Memory& memory() const noexcept;
    [[nodiscard]] const std::string& device_name() const noexcept;
    [[nodiscard]] const std::string& driver_name() const noexcept;
    [[nodiscard]] const std::string& driver_info() const noexcept;
    [[nodiscard]] std::uint32_t api_version() const noexcept;
    [[nodiscard]] float timestamp_period_ns() const noexcept;

private:
    struct Impl;
    std::unique_ptr<Impl> impl_;
};

} // namespace phos::gi::research::integration
