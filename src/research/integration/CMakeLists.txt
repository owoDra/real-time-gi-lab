# Issue #13 Integration owns this directory.

add_compute_shader(
  i001_software_bvh
  shaders/research/integration/i001_software_bvh.comp.glsl)
add_compute_shader(
  i001_hwrt
  shaders/research/integration/i001_hwrt.comp.glsl)
add_compute_shader(
  i001_quantized_bvh8
  shaders/research/integration/i001_quantized_bvh8.comp.glsl)
add_compute_shader(
  i001_work_to_rays
  shaders/research/integration/i001_work_to_rays.comp.glsl)
add_compute_shader(
  i001_radiance
  shaders/research/integration/i001_radiance.comp.glsl)
add_compute_shader(
  i001_storage_update
  shaders/research/integration/i001_storage_update.comp.glsl)
add_compute_shader(
  i001_storage_invalidate
  shaders/research/integration/i001_storage_invalidate.comp.glsl)
add_compute_shader(
  i001_storage_resolve
  shaders/research/integration/i001_storage_resolve.comp.glsl)
add_compute_shader(
  i001_clamp_counters
  shaders/research/integration/i001_clamp_counters.comp.glsl)

set(I001_SHADER_OUTPUTS
  "${CMAKE_BINARY_DIR}/shaders/i001_software_bvh.spv"
  "${CMAKE_BINARY_DIR}/shaders/i001_hwrt.spv"
  "${CMAKE_BINARY_DIR}/shaders/i001_quantized_bvh8.spv"
  "${CMAKE_BINARY_DIR}/shaders/i001_work_to_rays.spv"
  "${CMAKE_BINARY_DIR}/shaders/i001_radiance.spv"
  "${CMAKE_BINARY_DIR}/shaders/i001_storage_update.spv"
  "${CMAKE_BINARY_DIR}/shaders/i001_storage_invalidate.spv"
  "${CMAKE_BINARY_DIR}/shaders/i001_storage_resolve.spv"
  "${CMAKE_BINARY_DIR}/shaders/i001_clamp_counters.spv"
)
add_custom_target(phos-i001-shaders DEPENDS ${I001_SHADER_OUTPUTS})

add_executable(phos-i001
  i001_benchmark.cpp
  i001_runtime.cpp
  i001_compute.cpp
  ../lane_a_split_rc/a001_scene.cpp
  ../lane_a_split_rc/a001_runtime.cpp
  ../lane_a_split_rc/a001_analysis.cpp
  ../lane_b_traversal/b002_scene.cpp
  ../lane_b_traversal/b002_vulkan.cpp
  ../lane_b_traversal/b002_compute.cpp
  ../lane_b_traversal/b002_hwrt.cpp
  ${PROJECT_SOURCE_DIR}/src/vk_context.cpp
)

target_include_directories(phos-i001 PRIVATE
  "${CMAKE_SOURCE_DIR}/src"
  "${CMAKE_SOURCE_DIR}/src/research/lane_a_split_rc"
  "${CMAKE_SOURCE_DIR}/src/research/lane_b_traversal"
  "${CMAKE_CURRENT_SOURCE_DIR}"
)
target_link_libraries(phos-i001 PRIVATE
  vk-bootstrap::vk-bootstrap
  fastgltf::fastgltf
  ${CMAKE_DL_LIBS}
)
target_compile_features(phos-i001 PRIVATE cxx_std_20)
target_compile_definitions(phos-i001 PRIVATE
  PHOS_GI_LANE_A_SHADER_DIR="${CMAKE_BINARY_DIR}/shaders"
  PHOS_GI_LANE_B_SHADER_DIR="${CMAKE_BINARY_DIR}/shaders"
  PHOS_GI_INTEGRATION_SHADER_DIR="${CMAKE_BINARY_DIR}/shaders"
)
set_target_properties(phos-i001 PROPERTIES
  CXX_EXTENSIONS OFF
  RUNTIME_OUTPUT_DIRECTORY "${CMAKE_BINARY_DIR}"
)
add_dependencies(
  phos-i001
  phos-i001-shaders
  phos-lane-a-split-rc-shaders
  phos-lane-b-b002-shaders
  phos-lane-b-b003-shaders
)
if(MSVC)
  target_compile_options(phos-i001 PRIVATE /W4 /permissive-)
else()
  target_compile_options(phos-i001 PRIVATE -Wall -Wextra -Wpedantic)
endif()
