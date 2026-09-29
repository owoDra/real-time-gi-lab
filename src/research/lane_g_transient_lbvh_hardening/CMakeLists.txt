# Issue #17 Lane G owns this directory.
#
# G001 intentionally snapshots the F007 runtime/candidate implementation inside
# Lane G. No memory optimization is permitted here; only instrumentation may
# change before G001 concludes.

foreach(shader
  i001_bounded_producer
  i001_clamp_counters
  i001_hwrt
  i001_quantized_bvh8
  i001_radiance
  i001_software_bvh
  i001_storage_invalidate
  i001_storage_resolve
  i001_storage_update
  i001_work_to_rays
)
  add_compute_shader(
    ${shader}
    shaders/research/lane_g_transient_lbvh_hardening/${shader}.comp.glsl
  )
endforeach()

# Preserve the filenames expected by the F007-derived runtime.
add_compute_shader(
  lane_f_f003_lbvh_builder
  shaders/research/lane_g_transient_lbvh_hardening/f003_lbvh_builder.comp.glsl
)
add_compute_shader(
  lane_f_f003_dynamic_traversal
  shaders/research/lane_g_transient_lbvh_hardening/f003_dynamic_traversal.comp.glsl
)
add_compute_shader(
  lane_f_f003_hit_merge
  shaders/research/lane_g_transient_lbvh_hardening/f003_hit_merge.comp.glsl
)
add_compute_shader(
  lane_f_f005_grid_builder
  shaders/research/lane_g_transient_lbvh_hardening/f005_grid_builder.comp.glsl
)
add_compute_shader(
  lane_f_f005_grid_traversal
  shaders/research/lane_g_transient_lbvh_hardening/f005_grid_traversal.comp.glsl
)

add_custom_target(phos-lane-g-g001-shaders DEPENDS
  "${CMAKE_BINARY_DIR}/shaders/i001_bounded_producer.spv"
  "${CMAKE_BINARY_DIR}/shaders/i001_clamp_counters.spv"
  "${CMAKE_BINARY_DIR}/shaders/i001_hwrt.spv"
  "${CMAKE_BINARY_DIR}/shaders/i001_quantized_bvh8.spv"
  "${CMAKE_BINARY_DIR}/shaders/i001_radiance.spv"
  "${CMAKE_BINARY_DIR}/shaders/i001_software_bvh.spv"
  "${CMAKE_BINARY_DIR}/shaders/i001_storage_invalidate.spv"
  "${CMAKE_BINARY_DIR}/shaders/i001_storage_resolve.spv"
  "${CMAKE_BINARY_DIR}/shaders/i001_storage_update.spv"
  "${CMAKE_BINARY_DIR}/shaders/i001_work_to_rays.spv"
  "${CMAKE_BINARY_DIR}/shaders/lane_f_f003_lbvh_builder.spv"
  "${CMAKE_BINARY_DIR}/shaders/lane_f_f003_dynamic_traversal.spv"
  "${CMAKE_BINARY_DIR}/shaders/lane_f_f003_hit_merge.spv"
  "${CMAKE_BINARY_DIR}/shaders/lane_f_f005_grid_builder.spv"
  "${CMAKE_BINARY_DIR}/shaders/lane_f_f005_grid_traversal.spv"
)


add_executable(phos-lane-g-g001
  g001_benchmark.cpp
  i001_runtime.cpp
  i001_compute.cpp
  f003_transient_lbvh.cpp
  f003_transient_lbvh.hpp
  f005_transient_grid.cpp
  f005_transient_grid.hpp
  ../lane_a_split_rc/a001_scene.cpp
  ../lane_a_split_rc/a001_runtime.cpp
  ../lane_a_split_rc/a001_analysis.cpp
  ../lane_b_traversal/b002_scene.cpp
  ../lane_b_traversal/b002_vulkan.cpp
  ../lane_b_traversal/b002_compute.cpp
  ../lane_b_traversal/b002_hwrt.cpp
  ${PROJECT_SOURCE_DIR}/src/vk_context.cpp
)
target_include_directories(phos-lane-g-g001 PRIVATE
  "${CMAKE_SOURCE_DIR}/src"
  "${CMAKE_SOURCE_DIR}/src/research/lane_a_split_rc"
  "${CMAKE_SOURCE_DIR}/src/research/lane_b_traversal"
  "${CMAKE_CURRENT_SOURCE_DIR}"
)
target_link_libraries(phos-lane-g-g001 PRIVATE
  vk-bootstrap::vk-bootstrap
  fastgltf::fastgltf
  ${CMAKE_DL_LIBS}
)
target_compile_features(phos-lane-g-g001 PRIVATE cxx_std_20)
target_compile_definitions(phos-lane-g-g001 PRIVATE
  PHOS_GI_LANE_A_SHADER_DIR="${CMAKE_BINARY_DIR}/shaders"
  PHOS_GI_LANE_B_SHADER_DIR="${CMAKE_BINARY_DIR}/shaders"
  PHOS_GI_INTEGRATION_SHADER_DIR="${CMAKE_BINARY_DIR}/shaders"
  PHOS_GI_LANE_F_SHADER_DIR="${CMAKE_BINARY_DIR}/shaders"
)
set_target_properties(phos-lane-g-g001 PROPERTIES
  CXX_EXTENSIONS OFF
  RUNTIME_OUTPUT_DIRECTORY "${CMAKE_BINARY_DIR}"
)
add_dependencies(
  phos-lane-g-g001
  phos-lane-g-g001-shaders
  phos-lane-a-split-rc-shaders
  phos-lane-b-b002-shaders
  phos-lane-b-b003-shaders
)
if(MSVC)
  target_compile_options(phos-lane-g-g001 PRIVATE /W4 /permissive-)
else()
  target_compile_options(phos-lane-g-g001 PRIVATE -Wall -Wextra -Wpedantic)
endif()
