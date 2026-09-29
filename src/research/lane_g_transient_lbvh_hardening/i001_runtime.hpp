#pragma once

#include <cstddef>
#include <cstdint>
#include <filesystem>
#include <memory>
#include <string>
#include <vector>

namespace phos::gi::research::integration {

enum class I001Variant {
    VanillaSoftware,
    CombinedHwrt,
    CombinedSoftware,
    TransientLbvh,
    HardenedTransientLbvh,
    TransientGrid,
    DepthReuseHwrt,
    BoundedHwrt,
};

enum class I001Scenario {
    Static,
    CameraMotion,
    LightMotion,
    MovingRigid,
    SparseStress,
    DenseStress,
    LargeWorldStress,
    VerticalWorldStress,
    SparseMovingStress,
    DenseMovingStress,
    LargeWorldMovingStress,
    VerticalWorldMovingStress,
};

enum class I001GeometryClass {
    RepresentativeRigid,
    RigidLargeFew,
    RigidSmallMany32,
    Deforming,
    TopologyReplace25,
};

[[nodiscard]] const char* i001_variant_name(I001Variant value) noexcept;
[[nodiscard]] const char* i001_scenario_name(I001Scenario value) noexcept;
[[nodiscard]] I001Variant i001_parse_variant(const std::string& value);
[[nodiscard]] I001Scenario i001_parse_scenario(const std::string& value);
[[nodiscard]] const char* i001_geometry_class_name(I001GeometryClass value) noexcept;
[[nodiscard]] I001GeometryClass i001_parse_geometry_class(const std::string& value);

struct I001FrameTimings {
    double renderer_depth_us{};
    double frame_init_us{};
    double visibility_reuse_us{};
    double producer_us{};
    double ray_prepare_us{};
    double traversal_maintenance_gpu_us{};
    double dynamic_update_wall_us{};
    double dynamic_builder_reset_us{};
    double dynamic_builder_input_us{};
    double dynamic_builder_aabb_us{};
    double dynamic_builder_overlap_us{};
    double dynamic_builder_prefix_us{};
    double dynamic_builder_emit_us{};
    double dynamic_builder_morton_us{};
    double dynamic_builder_sort_us{};
    double dynamic_builder_topology_us{};
    double dynamic_builder_bounds_us{};
    double dynamic_builder_ranges_us{};
    double dynamic_builder_us{};
    double static_traversal_us{};
    double dynamic_traversal_us{};
    double cross_structure_merge_us{};
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
    std::uint32_t storage_allocations{};
    std::uint32_t storage_updates{};
    std::uint32_t storage_invalidations{};
    std::uint32_t storage_failures{};
    std::uint32_t grid_emitted_references{};
    std::uint32_t grid_max_references_per_triangle{};
    std::uint32_t grid_visited_macro_cells{};
    std::uint32_t grid_visited_local_cells{};
    std::uint32_t grid_empty_cell_steps{};
    std::uint32_t grid_tested_primitive_references{};
    std::uint32_t grid_cell_ranges{};
    std::uint32_t grid_macro_ranges{};
    std::uint32_t grid_overflow{};
    std::uint32_t dynamic_groups{};
    std::uint32_t deformed_primitives{};
    std::uint32_t topology_replaced_primitives{};
};

struct I001Memory {
    std::size_t persistent_bytes{};
    std::size_t transient_bytes{};
    std::size_t scratch_bytes{};
    std::size_t runtime_resident_bytes{};
    std::size_t setup_peak_bytes{};
    std::size_t peak_resident_bytes{};
    std::size_t stream_capacity_bytes{};
    std::size_t storage_capacity_bytes{};
    std::size_t shared_persistent_bytes{};
    std::size_t static_hwrt_persistent_bytes{};
    std::size_t dynamic_candidate_persistent_bytes{};
    std::size_t dynamic_candidate_transient_bytes{};
    std::size_t dynamic_candidate_scratch_bytes{};
    std::size_t current_frame_geometry_bytes{};
    std::size_t grid_pair_stream_bytes{};
    std::size_t grid_sort_scratch_bytes{};
    std::size_t host_persistent_bytes{};
    std::size_t host_transient_bytes{};
};

struct I001AllocationRecord {
    std::string name;
    std::string owner;
    std::string role;
    std::string capacity_kind;
    std::string allocation_lifetime;
    std::string use_lifetime;
    std::size_t logical_bytes{};
    std::size_t allocation_bytes{};
    bool logical_size_known{true};
    bool vulkan_allocation{true};
    bool counted_in_f007_peak{true};
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
    I001GeometryClass geometry_class{I001GeometryClass::RepresentativeRigid};
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
    [[nodiscard]] std::vector<I001AllocationRecord> allocation_census() const;
    [[nodiscard]] const std::string& device_name() const noexcept;
    [[nodiscard]] const std::string& driver_name() const noexcept;
    [[nodiscard]] const std::string& driver_info() const noexcept;
    [[nodiscard]] std::uint32_t api_version() const noexcept;

private:
    struct Impl;
    std::unique_ptr<Impl> impl_;
};

} // namespace phos::gi::research::integration
