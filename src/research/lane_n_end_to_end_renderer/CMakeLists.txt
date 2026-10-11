# Lane N image-producing renderer/reference experiments.

find_package(Threads REQUIRED)

add_compute_shader(
  lane_a_visibility_depth
  shaders/research/lane_n_end_to_end_renderer/imported/lane_a_split_rc/visibility_depth.comp.glsl)
add_compute_shader(
  lane_a_visibility_owner
  shaders/research/lane_n_end_to_end_renderer/imported/lane_a_split_rc/visibility_owner.comp.glsl)
add_compute_shader(
  lane_a_producer
  shaders/research/lane_n_end_to_end_renderer/imported/lane_a_split_rc/producer.comp.glsl)
add_compute_shader(
  lane_a_finalize
  shaders/research/lane_n_end_to_end_renderer/imported/lane_a_split_rc/finalize.comp.glsl)
add_compute_shader(
  lane_a_merge
  shaders/research/lane_n_end_to_end_renderer/imported/lane_a_split_rc/merge.comp.glsl)
add_compute_shader(
  lane_b_b002_hwrt
  shaders/research/lane_n_end_to_end_renderer/imported/lane_b_traversal/b002_hwrt.comp.glsl)
add_compute_shader(
  lane_b_b002_software_bvh
  shaders/research/lane_n_end_to_end_renderer/imported/lane_b_traversal/b002_software_bvh.comp.glsl)
add_compute_shader(
  i001_hwrt
  shaders/research/lane_n_end_to_end_renderer/imported/integration/i001_hwrt.comp.glsl)
add_compute_shader(
  i001_work_to_rays
  shaders/research/lane_n_end_to_end_renderer/imported/integration/i001_work_to_rays.comp.glsl)
add_compute_shader(
  i001_clamp_counters
  shaders/research/lane_n_end_to_end_renderer/imported/integration/i001_clamp_counters.comp.glsl)
add_compute_shader(
  i001_storage_update
  shaders/research/lane_n_end_to_end_renderer/imported/integration/i001_storage_update.comp.glsl)
add_compute_shader(
  i001_storage_invalidate
  shaders/research/lane_n_end_to_end_renderer/imported/integration/i001_storage_invalidate.comp.glsl)
add_compute_shader(
  i001_storage_resolve
  shaders/research/lane_n_end_to_end_renderer/imported/integration/i001_storage_resolve.comp.glsl)
add_compute_shader(
  i001_radiance
  shaders/research/lane_n_end_to_end_renderer/n001_physical_radiance.comp.glsl)
add_compute_shader(
  n001_primary
  shaders/research/lane_n_end_to_end_renderer/n001_primary.comp.glsl)
add_compute_shader(
  n001_composite
  shaders/research/lane_n_end_to_end_renderer/n001_composite.comp.glsl)

set(N001_SHADER_OUTPUTS
  "${CMAKE_BINARY_DIR}/shaders/lane_a_visibility_depth.spv"
  "${CMAKE_BINARY_DIR}/shaders/lane_a_visibility_owner.spv"
  "${CMAKE_BINARY_DIR}/shaders/lane_a_producer.spv"
  "${CMAKE_BINARY_DIR}/shaders/lane_a_finalize.spv"
  "${CMAKE_BINARY_DIR}/shaders/lane_a_merge.spv"
  "${CMAKE_BINARY_DIR}/shaders/lane_b_b002_hwrt.spv"
  "${CMAKE_BINARY_DIR}/shaders/lane_b_b002_software_bvh.spv"
  "${CMAKE_BINARY_DIR}/shaders/i001_hwrt.spv"
  "${CMAKE_BINARY_DIR}/shaders/i001_work_to_rays.spv"
  "${CMAKE_BINARY_DIR}/shaders/i001_clamp_counters.spv"
  "${CMAKE_BINARY_DIR}/shaders/i001_storage_update.spv"
  "${CMAKE_BINARY_DIR}/shaders/i001_storage_invalidate.spv"
  "${CMAKE_BINARY_DIR}/shaders/i001_storage_resolve.spv"
  "${CMAKE_BINARY_DIR}/shaders/i001_radiance.spv"
  "${CMAKE_BINARY_DIR}/shaders/n001_primary.spv"
  "${CMAKE_BINARY_DIR}/shaders/n001_composite.spv"
)
add_custom_target(phos-n001-shaders DEPENDS ${N001_SHADER_OUTPUTS})

add_compute_shader(
  n005_extra_producer
  shaders/research/n005_adaptive_tracing/n005_extra_producer.comp.glsl)
set(N005_SHADER_OUTPUTS
  "${CMAKE_BINARY_DIR}/shaders/n005_extra_producer.spv"
)
add_custom_target(phos-n005-shaders DEPENDS ${N005_SHADER_OUTPUTS})

add_compute_shader(
  i001_software_bvh
  shaders/research/lane_n_end_to_end_renderer/imported/integration/i001_software_bvh.comp.glsl)
add_compute_shader(
  n003_primary_software
  shaders/research/lane_n_end_to_end_renderer/n003_primary_software.comp.glsl)
add_compute_shader(
  n003_composite_software
  shaders/research/lane_n_end_to_end_renderer/n003_composite_software.comp.glsl)
set(N003_COMPARISON_SHADER_OUTPUTS
  "${CMAKE_BINARY_DIR}/shaders/i001_software_bvh.spv"
  "${CMAKE_BINARY_DIR}/shaders/n003_primary_software.spv"
  "${CMAKE_BINARY_DIR}/shaders/n003_composite_software.spv"
)
add_custom_target(
  phos-n003-comparison-shaders
  DEPENDS ${N003_COMPARISON_SHADER_OUTPUTS})

set(N001_SHARED_SUPPORT_SOURCES
  n001_reference.cpp
  imported/integration/i001_compute.cpp
  imported/lane_a_split_rc/a001_scene.cpp
  imported/lane_a_split_rc/a001_runtime.cpp
  imported/lane_a_split_rc/a001_analysis.cpp
  imported/lane_b_traversal/b002_scene.cpp
  imported/lane_b_traversal/b002_vulkan.cpp
  imported/lane_b_traversal/b002_compute.cpp
  imported/lane_b_traversal/b002_hwrt.cpp
  ${PROJECT_SOURCE_DIR}/src/vk_context.cpp
)

# N004 substitutes only A001's CPU parameter-builder/runtime translation unit
# with a wrapper that includes the accepted implementation and adds fractional
# camera/light interpolation. Historical N001-N003 targets keep the original
# source list above unchanged.
set(N004_SHARED_SUPPORT_SOURCES
  n001_reference.cpp
  imported/integration/i001_compute.cpp
  imported/lane_a_split_rc/a001_scene.cpp
  n004_a001_runtime.cpp
  imported/lane_a_split_rc/a001_analysis.cpp
  imported/lane_b_traversal/b002_scene.cpp
  imported/lane_b_traversal/b002_vulkan.cpp
  imported/lane_b_traversal/b002_compute.cpp
  imported/lane_b_traversal/b002_hwrt.cpp
  ${PROJECT_SOURCE_DIR}/src/vk_context.cpp
)

set(N001_SHARED_SOURCES
  n001_runtime.cpp
  ${N001_SHARED_SUPPORT_SOURCES}
)

function(configure_lane_n_renderer target)
  target_include_directories(${target} PRIVATE
    "${CMAKE_SOURCE_DIR}/src"
    "${CMAKE_CURRENT_SOURCE_DIR}"
    "${CMAKE_CURRENT_SOURCE_DIR}/imported/integration"
    "${CMAKE_CURRENT_SOURCE_DIR}/imported/lane_a_split_rc"
    "${CMAKE_CURRENT_SOURCE_DIR}/imported/lane_b_traversal"
    "${CMAKE_CURRENT_SOURCE_DIR}/imported/lane_e_dynamic_geometry"
  )
  target_link_libraries(${target} PRIVATE
    vk-bootstrap::vk-bootstrap
    fastgltf::fastgltf
    Threads::Threads
    ${CMAKE_DL_LIBS}
  )
  target_compile_features(${target} PRIVATE cxx_std_20)
  target_compile_definitions(${target} PRIVATE
    PHOS_GI_LANE_A_SHADER_DIR="${CMAKE_BINARY_DIR}/shaders"
    PHOS_GI_LANE_B_SHADER_DIR="${CMAKE_BINARY_DIR}/shaders"
    PHOS_GI_INTEGRATION_SHADER_DIR="${CMAKE_BINARY_DIR}/shaders"
  )
  set_target_properties(${target} PROPERTIES
    CXX_EXTENSIONS OFF
    RUNTIME_OUTPUT_DIRECTORY "${CMAKE_BINARY_DIR}"
  )
  add_dependencies(${target} phos-n001-shaders)
  if(MSVC)
    target_compile_options(${target} PRIVATE /W4 /permissive-)
  else()
    target_compile_options(${target} PRIVATE -Wall -Wextra -Wpedantic)
  endif()
endfunction()

add_executable(phos-n001
  n001_main.cpp
  ${N001_SHARED_SOURCES}
)
configure_lane_n_renderer(phos-n001)

add_executable(phos-n002
  n002_main.cpp
  ${N001_SHARED_SOURCES}
)
configure_lane_n_renderer(phos-n002)

add_executable(phos-n002-topology
  n002_topology_main.cpp
  n002_runtime.cpp
  n002_hwrt_rebuild.cpp
  ${N001_SHARED_SUPPORT_SOURCES}
)
configure_lane_n_renderer(phos-n002-topology)

add_executable(phos-n003-preflight
  n003_preflight_main.cpp
  n002_runtime.cpp
  n002_hwrt_rebuild.cpp
  ${N001_SHARED_SUPPORT_SOURCES}
)
configure_lane_n_renderer(phos-n003-preflight)

add_executable(phos-n003-workload-diagnostic
  n003_workload_diagnostic_main.cpp
  n002_runtime.cpp
  n002_hwrt_rebuild.cpp
  ${N001_SHARED_SUPPORT_SOURCES}
)
configure_lane_n_renderer(phos-n003-workload-diagnostic)

add_executable(phos-n003-comparison
  n003_comparison_main.cpp
  n003_comparison_runtime.cpp
  n002_hwrt_rebuild.cpp
  ${N001_SHARED_SUPPORT_SOURCES}
)
configure_lane_n_renderer(phos-n003-comparison)
add_dependencies(phos-n003-comparison phos-n003-comparison-shaders)

add_executable(phos-n003-quality
  n003_quality_main.cpp
  n003_comparison_runtime.cpp
  n002_hwrt_rebuild.cpp
  ${N001_SHARED_SUPPORT_SOURCES}
)
configure_lane_n_renderer(phos-n003-quality)
add_dependencies(phos-n003-quality phos-n003-comparison-shaders)

add_executable(phos-n003-diagnostics
  n003_diagnostics_main.cpp
  n003_comparison_runtime.cpp
  n002_hwrt_rebuild.cpp
  ${N001_SHARED_SUPPORT_SOURCES}
)
configure_lane_n_renderer(phos-n003-diagnostics)
add_dependencies(phos-n003-diagnostics phos-n003-comparison-shaders)

# N004 adds only a prospective motion-fraction control surface around the
# accepted N002 runtime. The atlas target adds no mitigation and uses the
# isolated A001 wrapper above; N001-N003 continue to link the accepted source.
add_executable(phos-n004-atlas
  n004_atlas_main.cpp
  n004_runtime.cpp
  n002_hwrt_rebuild.cpp
  ${N004_SHARED_SUPPORT_SOURCES}
)
configure_lane_n_renderer(phos-n004-atlas)

# N005 keeps N004 and all historical targets unchanged. Its integration-only
# runtime includes the accepted N004/N002/N001 runtime chain in one translation
# unit and inserts exactly one extra producer stage at the frozen P0 boundary.
add_executable(phos-n005-candidate
  ${PROJECT_SOURCE_DIR}/src/research/n005_adaptive_tracing/n005_candidate_main.cpp
  ${PROJECT_SOURCE_DIR}/src/research/n005_adaptive_tracing/n005_runtime.cpp
  n002_hwrt_rebuild.cpp
  ${N004_SHARED_SUPPORT_SOURCES}
)
configure_lane_n_renderer(phos-n005-candidate)
target_compile_definitions(phos-n005-candidate PRIVATE
  PHOS_GI_N005_SHADER_DIR="${CMAKE_BINARY_DIR}/shaders"
)
add_dependencies(phos-n005-candidate phos-n005-shaders)

# N006 P1 only: an isolated copy of the N005 integration runtime and a
# targeted owner x cascade extra-ray shader. Accepted historical targets are
# unchanged. This pilot measures counterfactual marginal gain, not scheduling.
add_compute_shader(
  n006_extra_producer
  shaders/research/n006_interval_aware_allocation/n006_extra_producer.comp.glsl)
add_compute_shader(
  n006_probe_unique_hash
  shaders/research/n006_interval_aware_allocation/n006_probe_unique_hash.comp.glsl)
add_compute_shader(
  n006_canonical_index
  shaders/research/n006_interval_aware_allocation/n006_canonical_index.comp.glsl)
add_compute_shader(
  n006_canonical_setup
  shaders/research/n006_interval_aware_allocation/n006_canonical_setup.comp.glsl)
add_compute_shader(
  n006_canonical_compact
  shaders/research/n006_interval_aware_allocation/n006_canonical_compact.comp.glsl)
add_compute_shader(
  n006_canonical_copy
  shaders/research/n006_interval_aware_allocation/n006_canonical_copy.comp.glsl)
add_compute_shader(
  n006_canonical_apply
  shaders/research/n006_interval_aware_allocation/n006_canonical_apply.comp.glsl)
add_compute_shader(
  n006_canonical_weight_storage
  shaders/research/n006_interval_aware_allocation/n006_canonical_weight_storage.comp.glsl)
# P1l-B0: diagnostic instrumentation ONLY for the N006 executable.
# The accepted N003/E003 SPIR-V and their targets are not rebuilt from
# altered shader sources.
add_compute_shader(n006_p1l_primary_count
  shaders/research/n006_interval_aware_allocation/n006_p1l_primary_count.comp.glsl)
add_compute_shader(n006_p1l_composite_count
  shaders/research/n006_interval_aware_allocation/n006_p1l_composite_count.comp.glsl)
add_compute_shader(n006_p1l_e003_count
  shaders/research/n006_interval_aware_allocation/n006_p1l_e003_count.comp.glsl)
# C0: independently rebuild the ORIGINAL E003 shader, without altering the
# accepted runtime binary or any accepted source. Compare their SPIR-V SHA.
add_compute_shader(n006_p1l_c0_e003_source_rebuild
  shaders/research/lane_n_end_to_end_renderer/imported/lane_e_dynamic_geometry/e003_instance_quantized.comp.glsl)
add_custom_target(phos-n006-p1l-c0-shaders DEPENDS
  "${CMAKE_BINARY_DIR}/shaders/n006_p1l_c0_e003_source_rebuild.spv")
# P1m0: build only, diagnostic shader has no attached dispatch or timing claim.
add_compute_shader(n006_p1m0_consumer_coverage
  shaders/research/n006_interval_aware_allocation/n006_p1m0_consumer_coverage.comp.glsl)
add_custom_target(phos-n006-p1m0-shaders DEPENDS
  "${CMAKE_BINARY_DIR}/shaders/n006_p1m0_consumer_coverage.spv")
# Isolated P1m1a +4 ray preflight; no accepted shader or target changed.
add_compute_shader(n006_p1m1_canonical_key_extra
  shaders/research/n006_interval_aware_allocation/n006_p1m1_canonical_key_extra.comp.glsl)
add_custom_target(phos-n006-p1m1a-shaders DEPENDS
  "${CMAKE_BINARY_DIR}/shaders/n006_p1m1_canonical_key_extra.spv")
# P1m2a is a separate opt-in direction-distribution arm. Keep M1 shader SHA.
add_compute_shader(n006_p1m2a_tetra_octant_extra
  shaders/research/n006_interval_aware_allocation/n006_p1m2a_tetra_octant_extra.comp.glsl)
add_custom_target(phos-n006-p1m2a-shaders DEPENDS
  "${CMAKE_BINARY_DIR}/shaders/n006_p1m2a_tetra_octant_extra.spv")
# P1m3a prospective NEW Q8 storage semantics; accepted I001/P1g remain intact.
add_compute_shader(n006_p1m3_fractional_storage_update
  shaders/research/n006_interval_aware_allocation/n006_p1m3_fractional_storage_update.comp.glsl)
add_compute_shader(n006_p1m3_fractional_weight_storage
  shaders/research/n006_interval_aware_allocation/n006_p1m3_fractional_weight_storage.comp.glsl)
add_custom_target(phos-n006-p1m3a-shaders DEPENDS
  "${CMAKE_BINARY_DIR}/shaders/n006_p1m3_fractional_storage_update.spv"
  "${CMAKE_BINARY_DIR}/shaders/n006_p1m3_fractional_weight_storage.spv")
add_compute_shader(n006_p1l_b1_primary_near_first
  shaders/research/n006_interval_aware_allocation/n006_p1l_b1_primary_near_first.comp.glsl)
# B1b count-only pair; never replaces the accepted original primary.
add_compute_shader(n006_p1l_b1b_primary_near_first_count
  shaders/research/n006_interval_aware_allocation/n006_p1l_b1b_primary_near_first_count.comp.glsl)
add_custom_target(phos-n006-p1l-b1b-shaders DEPENDS
  "${CMAKE_BINARY_DIR}/shaders/n006_p1l_primary_count.spv"
  "${CMAKE_BINARY_DIR}/shaders/n006_p1l_b1b_primary_near_first_count.spv")
add_compute_shader(n006_p1l_b1c_primary_axis_proxy
  shaders/research/n006_interval_aware_allocation/n006_p1l_b1c_primary_axis_proxy.comp.glsl)
add_custom_target(phos-n006-p1l-b1c-shaders DEPENDS
  "${CMAKE_BINARY_DIR}/shaders/n006_p1l_b1c_primary_axis_proxy.spv")
add_custom_target(phos-n006-p1l-b1-shaders DEPENDS
  "${CMAKE_BINARY_DIR}/shaders/n006_p1l_b1_primary_near_first.spv")
add_custom_target(phos-n006-p1l-b0-shaders DEPENDS
  "${CMAKE_BINARY_DIR}/shaders/n006_p1l_primary_count.spv"
  "${CMAKE_BINARY_DIR}/shaders/n006_p1l_composite_count.spv"
  "${CMAKE_BINARY_DIR}/shaders/n006_p1l_e003_count.spv")
add_custom_target(phos-n006-shaders DEPENDS
  "${CMAKE_BINARY_DIR}/shaders/n006_extra_producer.spv"
  "${CMAKE_BINARY_DIR}/shaders/n006_probe_unique_hash.spv"
  "${CMAKE_BINARY_DIR}/shaders/n006_canonical_index.spv"
  "${CMAKE_BINARY_DIR}/shaders/n006_canonical_setup.spv"
  "${CMAKE_BINARY_DIR}/shaders/n006_canonical_compact.spv"
  "${CMAKE_BINARY_DIR}/shaders/n006_canonical_copy.spv"
  "${CMAKE_BINARY_DIR}/shaders/n006_canonical_apply.spv"
  "${CMAKE_BINARY_DIR}/shaders/n006_canonical_weight_storage.spv")
add_executable(phos-n006-intervention
  ${PROJECT_SOURCE_DIR}/src/research/n006_interval_aware_allocation/n006_intervention_main.cpp
  ${PROJECT_SOURCE_DIR}/src/research/n006_interval_aware_allocation/n006_runtime.cpp
  n002_hwrt_rebuild.cpp
  ${N004_SHARED_SUPPORT_SOURCES}
)
configure_lane_n_renderer(phos-n006-intervention)
target_compile_definitions(phos-n006-intervention PRIVATE
  PHOS_GI_N006_SHADER_DIR="${CMAKE_BINARY_DIR}/shaders"
  PHOS_GI_N006_SOFTWARE_PRIMARY=1
)
add_dependencies(phos-n006-intervention
  phos-n006-shaders phos-n003-comparison-shaders phos-n006-p1l-b0-shaders
  phos-n006-p1l-b1-shaders phos-n006-p1l-b1b-shaders
  phos-n006-p1l-b1c-shaders phos-n006-p1l-c0-shaders
  phos-n006-p1m0-shaders phos-n006-p1m1a-shaders
  phos-n006-p1m2a-shaders phos-n006-p1m3a-shaders)
