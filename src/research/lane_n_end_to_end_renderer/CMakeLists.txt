# Lane N N001 image-producing renderer/reference bring-up.

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

add_executable(phos-n001
  n001_main.cpp
  n001_runtime.cpp
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

target_include_directories(phos-n001 PRIVATE
  "${CMAKE_SOURCE_DIR}/src"
  "${CMAKE_CURRENT_SOURCE_DIR}"
  "${CMAKE_CURRENT_SOURCE_DIR}/imported/integration"
  "${CMAKE_CURRENT_SOURCE_DIR}/imported/lane_a_split_rc"
  "${CMAKE_CURRENT_SOURCE_DIR}/imported/lane_b_traversal"
  "${CMAKE_CURRENT_SOURCE_DIR}/imported/lane_e_dynamic_geometry"
)
target_link_libraries(phos-n001 PRIVATE
  vk-bootstrap::vk-bootstrap
  fastgltf::fastgltf
  Threads::Threads
  ${CMAKE_DL_LIBS}
)
target_compile_features(phos-n001 PRIVATE cxx_std_20)
target_compile_definitions(phos-n001 PRIVATE
  PHOS_GI_LANE_A_SHADER_DIR="${CMAKE_BINARY_DIR}/shaders"
  PHOS_GI_LANE_B_SHADER_DIR="${CMAKE_BINARY_DIR}/shaders"
  PHOS_GI_INTEGRATION_SHADER_DIR="${CMAKE_BINARY_DIR}/shaders"
)
set_target_properties(phos-n001 PROPERTIES
  CXX_EXTENSIONS OFF
  RUNTIME_OUTPUT_DIRECTORY "${CMAKE_BINARY_DIR}"
)
add_dependencies(phos-n001 phos-n001-shaders)
if(MSVC)
  target_compile_options(phos-n001 PRIVATE /W4 /permissive-)
else()
  target_compile_options(phos-n001 PRIVATE -Wall -Wextra -Wpedantic)
endif()
