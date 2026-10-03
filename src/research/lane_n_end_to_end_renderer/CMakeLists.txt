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

# N003-only vanilla renderer shaders. Keep these out of the accepted N001/N002
# shader dependency set so historical renderer targets are unchanged.
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

# N002 topology/high-churn extension. n002_runtime.cpp includes the accepted
# n001_runtime.cpp in its translation unit and adds only the N002 topology
# transition member. This avoids duplicating or modifying the N001 runtime.
add_executable(phos-n002-topology
  n002_topology_main.cpp
  n002_runtime.cpp
  n002_hwrt_rebuild.cpp
  ${N001_SHARED_SUPPORT_SOURCES}
)
configure_lane_n_renderer(phos-n002-topology)

# N003 preflight timing probe. It keeps the accepted N002 renderer/runtime
# boundary but places A and B in one process, with source-state GPU warm-up
# immediately before each measured transition. Stage timings are retained for
# diagnosis if the paired-control gate remains unsuitable.
add_executable(phos-n003-preflight
  n003_preflight_main.cpp
  n002_runtime.cpp
  n002_hwrt_rebuild.cpp
  ${N001_SHARED_SUPPORT_SOURCES}
)
configure_lane_n_renderer(phos-n003-preflight)

# N003 moving-rigid workload-invariance diagnostic. This is not a performance
# comparison target: it records integer source/target work counters for paired
# fresh runtimes so residual timing noise can be separated from workload
# nondeterminism without changing the host GPU power/performance policy.
add_executable(phos-n003-workload-diagnostic
  n003_workload_diagnostic_main.cpp
  n002_runtime.cpp
  n002_hwrt_rebuild.cpp
  ${N001_SHARED_SUPPORT_SOURCES}
)
configure_lane_n_renderer(phos-n003-workload-diagnostic)

# N003 proper current-vs-vanilla comparison. The comparison runtime includes
# the accepted N002 runtime in one TU and adds only comparison-specific vanilla
# reconfiguration/topology hooks; N001/N002 targets remain source-identical.
add_executable(phos-n003-comparison
  n003_comparison_main.cpp
  n003_comparison_runtime.cpp
  n002_hwrt_rebuild.cpp
  ${N001_SHARED_SUPPORT_SOURCES}
)
configure_lane_n_renderer(phos-n003-comparison)
add_dependencies(phos-n003-comparison phos-n003-comparison-shaders)

# Quality/reference evidence is a separate one-shot target so expensive
# converged reference rendering never contaminates the replicated timing run.
add_executable(phos-n003-quality
  n003_quality_main.cpp
  n003_comparison_runtime.cpp
  n002_hwrt_rebuild.cpp
  ${N001_SHARED_SUPPORT_SOURCES}
)
configure_lane_n_renderer(phos-n003-quality)
add_dependencies(phos-n003-quality phos-n003-comparison-shaders)
