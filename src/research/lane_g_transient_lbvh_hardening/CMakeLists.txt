# Issue #17 Lane G owns this directory.
# G001 snapshots F007 dependencies below Lane G. No other lane source is merged.
# G001 has concluded; G003 candidates must remain directly attributable to its census.

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

add_compute_shader(lane_f_f003_lbvh_builder shaders/research/lane_g_transient_lbvh_hardening/f003_lbvh_builder.comp.glsl)
add_compute_shader(lane_f_f003_dynamic_traversal shaders/research/lane_g_transient_lbvh_hardening/f003_dynamic_traversal.comp.glsl)
add_compute_shader(lane_f_f003_hit_merge shaders/research/lane_g_transient_lbvh_hardening/f003_hit_merge.comp.glsl)
add_compute_shader(lane_f_f005_grid_builder shaders/research/lane_g_transient_lbvh_hardening/f005_grid_builder.comp.glsl)
add_compute_shader(lane_f_f005_grid_traversal shaders/research/lane_g_transient_lbvh_hardening/f005_grid_traversal.comp.glsl)

add_compute_shader(lane_a_visibility_depth shaders/research/lane_g_transient_lbvh_hardening/baseline/lane_a_split_rc/visibility_depth.comp.glsl)
add_compute_shader(lane_a_visibility_owner shaders/research/lane_g_transient_lbvh_hardening/baseline/lane_a_split_rc/visibility_owner.comp.glsl)
add_compute_shader(lane_a_producer shaders/research/lane_g_transient_lbvh_hardening/baseline/lane_a_split_rc/producer.comp.glsl)
add_compute_shader(lane_a_finalize shaders/research/lane_g_transient_lbvh_hardening/baseline/lane_a_split_rc/finalize.comp.glsl)
add_compute_shader(lane_a_gather shaders/research/lane_g_transient_lbvh_hardening/baseline/lane_a_split_rc/gather.comp.glsl)
add_compute_shader(lane_a_merge shaders/research/lane_g_transient_lbvh_hardening/baseline/lane_a_split_rc/merge.comp.glsl)
add_compute_shader(lane_a_resolve shaders/research/lane_g_transient_lbvh_hardening/baseline/lane_a_split_rc/resolve.comp.glsl)

add_compute_shader(lane_b_b002_software_bvh shaders/research/lane_g_transient_lbvh_hardening/baseline/lane_b_traversal/b002_software_bvh.comp.glsl)
add_compute_shader(lane_b_b002_hierarchical shaders/research/lane_g_transient_lbvh_hardening/baseline/lane_b_traversal/b002_hierarchical.comp.glsl)
add_compute_shader(lane_b_b002_hwrt shaders/research/lane_g_transient_lbvh_hardening/baseline/lane_b_traversal/b002_hwrt.comp.glsl)
add_compute_shader(lane_b_b003_macro_bvh8 shaders/research/lane_g_transient_lbvh_hardening/baseline/lane_b_traversal/b003_macro_bvh8.comp.glsl)
add_compute_shader(lane_b_b003_micro_bvh8 shaders/research/lane_g_transient_lbvh_hardening/baseline/lane_b_traversal/b003_micro_bvh8.comp.glsl)
add_compute_shader(lane_b_b003_quantized_bvh8 shaders/research/lane_g_transient_lbvh_hardening/baseline/lane_b_traversal/b003_quantized_bvh8.comp.glsl)
add_compute_shader(lane_b_b003_triangle_packets shaders/research/lane_g_transient_lbvh_hardening/baseline/lane_b_traversal/b003_triangle_packets.comp.glsl)
add_compute_shader(lane_b_b003_triangle_packets_compact shaders/research/lane_g_transient_lbvh_hardening/baseline/lane_b_traversal/b003_triangle_packets_compact.comp.glsl)

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
  "${CMAKE_BINARY_DIR}/shaders/lane_a_visibility_depth.spv"
  "${CMAKE_BINARY_DIR}/shaders/lane_a_visibility_owner.spv"
  "${CMAKE_BINARY_DIR}/shaders/lane_a_producer.spv"
  "${CMAKE_BINARY_DIR}/shaders/lane_a_finalize.spv"
  "${CMAKE_BINARY_DIR}/shaders/lane_a_gather.spv"
  "${CMAKE_BINARY_DIR}/shaders/lane_a_merge.spv"
  "${CMAKE_BINARY_DIR}/shaders/lane_a_resolve.spv"
  "${CMAKE_BINARY_DIR}/shaders/lane_b_b002_software_bvh.spv"
  "${CMAKE_BINARY_DIR}/shaders/lane_b_b002_hierarchical.spv"
  "${CMAKE_BINARY_DIR}/shaders/lane_b_b002_hwrt.spv"
  "${CMAKE_BINARY_DIR}/shaders/lane_b_b003_macro_bvh8.spv"
  "${CMAKE_BINARY_DIR}/shaders/lane_b_b003_micro_bvh8.spv"
  "${CMAKE_BINARY_DIR}/shaders/lane_b_b003_quantized_bvh8.spv"
  "${CMAKE_BINARY_DIR}/shaders/lane_b_b003_triangle_packets.spv"
  "${CMAKE_BINARY_DIR}/shaders/lane_b_b003_triangle_packets_compact.spv"
)

add_executable(phos-lane-g-g001
  g001_benchmark.cpp
  i001_runtime.cpp
  g003_immutable_hwrt.cpp
  i001_compute.cpp
  f003_transient_lbvh.cpp
  f005_transient_grid.cpp
  baseline/lane_a_split_rc/a001_scene.cpp
  baseline/lane_a_split_rc/a001_runtime.cpp
  baseline/lane_a_split_rc/a001_analysis.cpp
  baseline/lane_b_traversal/b002_scene.cpp
  baseline/lane_b_traversal/b002_vulkan.cpp
  baseline/lane_b_traversal/b002_compute.cpp
  baseline/lane_b_traversal/b002_hwrt.cpp
  ${PROJECT_SOURCE_DIR}/src/vk_context.cpp
)
target_include_directories(phos-lane-g-g001 PRIVATE
  "${CMAKE_SOURCE_DIR}/src"
  "${CMAKE_CURRENT_SOURCE_DIR}"
  "${CMAKE_CURRENT_SOURCE_DIR}/baseline/lane_a_split_rc"
  "${CMAKE_CURRENT_SOURCE_DIR}/baseline/lane_b_traversal"
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
add_dependencies(phos-lane-g-g001 phos-lane-g-g001-shaders)
if(MSVC)
  target_compile_options(phos-lane-g-g001 PRIVATE /W4 /permissive-)
else()
  target_compile_options(phos-lane-g-g001 PRIVATE -Wall -Wextra -Wpedantic)
endif()

add_executable(phos-lane-g-g002
  g002_benchmark.cpp
  i001_runtime.cpp
  g003_immutable_hwrt.cpp
  i001_compute.cpp
  f003_transient_lbvh.cpp
  f005_transient_grid.cpp
  baseline/lane_a_split_rc/a001_scene.cpp
  baseline/lane_a_split_rc/a001_runtime.cpp
  baseline/lane_a_split_rc/a001_analysis.cpp
  baseline/lane_b_traversal/b002_scene.cpp
  baseline/lane_b_traversal/b002_vulkan.cpp
  baseline/lane_b_traversal/b002_compute.cpp
  baseline/lane_b_traversal/b002_hwrt.cpp
  ${PROJECT_SOURCE_DIR}/src/vk_context.cpp
)
target_include_directories(phos-lane-g-g002 PRIVATE
  "${CMAKE_SOURCE_DIR}/src"
  "${CMAKE_CURRENT_SOURCE_DIR}"
  "${CMAKE_CURRENT_SOURCE_DIR}/baseline/lane_a_split_rc"
  "${CMAKE_CURRENT_SOURCE_DIR}/baseline/lane_b_traversal"
)
target_link_libraries(phos-lane-g-g002 PRIVATE
  vk-bootstrap::vk-bootstrap
  fastgltf::fastgltf
  ${CMAKE_DL_LIBS}
)
target_compile_features(phos-lane-g-g002 PRIVATE cxx_std_20)
target_compile_definitions(phos-lane-g-g002 PRIVATE
  PHOS_GI_LANE_A_SHADER_DIR="${CMAKE_BINARY_DIR}/shaders"
  PHOS_GI_LANE_B_SHADER_DIR="${CMAKE_BINARY_DIR}/shaders"
  PHOS_GI_INTEGRATION_SHADER_DIR="${CMAKE_BINARY_DIR}/shaders"
  PHOS_GI_LANE_F_SHADER_DIR="${CMAKE_BINARY_DIR}/shaders"
)
set_target_properties(phos-lane-g-g002 PROPERTIES
  CXX_EXTENSIONS OFF
  RUNTIME_OUTPUT_DIRECTORY "${CMAKE_BINARY_DIR}"
)
add_dependencies(phos-lane-g-g002 phos-lane-g-g001-shaders)
if(MSVC)
  target_compile_options(phos-lane-g-g002 PRIVATE /W4 /permissive-)
else()
  target_compile_options(phos-lane-g-g002 PRIVATE -Wall -Wextra -Wpedantic)
endif()


add_executable(phos-lane-g-g003
  g003_benchmark.cpp
  i001_runtime.cpp
  g003_immutable_hwrt.cpp
  i001_compute.cpp
  f003_transient_lbvh.cpp
  f005_transient_grid.cpp
  baseline/lane_a_split_rc/a001_scene.cpp
  baseline/lane_a_split_rc/a001_runtime.cpp
  baseline/lane_a_split_rc/a001_analysis.cpp
  baseline/lane_b_traversal/b002_scene.cpp
  baseline/lane_b_traversal/b002_vulkan.cpp
  baseline/lane_b_traversal/b002_compute.cpp
  baseline/lane_b_traversal/b002_hwrt.cpp
  ${PROJECT_SOURCE_DIR}/src/vk_context.cpp
)
target_include_directories(phos-lane-g-g003 PRIVATE
  "${CMAKE_SOURCE_DIR}/src"
  "${CMAKE_CURRENT_SOURCE_DIR}"
  "${CMAKE_CURRENT_SOURCE_DIR}/baseline/lane_a_split_rc"
  "${CMAKE_CURRENT_SOURCE_DIR}/baseline/lane_b_traversal"
)
target_link_libraries(phos-lane-g-g003 PRIVATE
  vk-bootstrap::vk-bootstrap
  fastgltf::fastgltf
  ${CMAKE_DL_LIBS}
)
target_compile_features(phos-lane-g-g003 PRIVATE cxx_std_20)
target_compile_definitions(phos-lane-g-g003 PRIVATE
  PHOS_GI_LANE_A_SHADER_DIR="${CMAKE_BINARY_DIR}/shaders"
  PHOS_GI_LANE_B_SHADER_DIR="${CMAKE_BINARY_DIR}/shaders"
  PHOS_GI_INTEGRATION_SHADER_DIR="${CMAKE_BINARY_DIR}/shaders"
  PHOS_GI_LANE_F_SHADER_DIR="${CMAKE_BINARY_DIR}/shaders"
)
set_target_properties(phos-lane-g-g003 PROPERTIES
  CXX_EXTENSIONS OFF
  RUNTIME_OUTPUT_DIRECTORY "${CMAKE_BINARY_DIR}"
)
add_dependencies(phos-lane-g-g003 phos-lane-g-g001-shaders)
if(MSVC)
  target_compile_options(phos-lane-g-g003 PRIVATE /W4 /permissive-)
else()
  target_compile_options(phos-lane-g-g003 PRIVATE -Wall -Wextra -Wpedantic)
endif()


add_executable(phos-lane-g-g004
  g004_benchmark.cpp
  i001_runtime.cpp
  g003_immutable_hwrt.cpp
  i001_compute.cpp
  f003_transient_lbvh.cpp
  f005_transient_grid.cpp
  baseline/lane_a_split_rc/a001_scene.cpp
  baseline/lane_a_split_rc/a001_runtime.cpp
  baseline/lane_a_split_rc/a001_analysis.cpp
  baseline/lane_b_traversal/b002_scene.cpp
  baseline/lane_b_traversal/b002_vulkan.cpp
  baseline/lane_b_traversal/b002_compute.cpp
  baseline/lane_b_traversal/b002_hwrt.cpp
  ${PROJECT_SOURCE_DIR}/src/vk_context.cpp
)
target_include_directories(phos-lane-g-g004 PRIVATE
  "${CMAKE_SOURCE_DIR}/src"
  "${CMAKE_CURRENT_SOURCE_DIR}"
  "${CMAKE_CURRENT_SOURCE_DIR}/baseline/lane_a_split_rc"
  "${CMAKE_CURRENT_SOURCE_DIR}/baseline/lane_b_traversal"
)
target_link_libraries(phos-lane-g-g004 PRIVATE
  vk-bootstrap::vk-bootstrap
  fastgltf::fastgltf
  ${CMAKE_DL_LIBS}
)
target_compile_features(phos-lane-g-g004 PRIVATE cxx_std_20)
target_compile_definitions(phos-lane-g-g004 PRIVATE
  PHOS_GI_LANE_A_SHADER_DIR="${CMAKE_BINARY_DIR}/shaders"
  PHOS_GI_LANE_B_SHADER_DIR="${CMAKE_BINARY_DIR}/shaders"
  PHOS_GI_INTEGRATION_SHADER_DIR="${CMAKE_BINARY_DIR}/shaders"
  PHOS_GI_LANE_F_SHADER_DIR="${CMAKE_BINARY_DIR}/shaders"
)
set_target_properties(phos-lane-g-g004 PROPERTIES
  CXX_EXTENSIONS OFF
  RUNTIME_OUTPUT_DIRECTORY "${CMAKE_BINARY_DIR}"
)
add_dependencies(phos-lane-g-g004 phos-lane-g-g001-shaders)
if(MSVC)
  target_compile_options(phos-lane-g-g004 PRIVATE /W4 /permissive-)
else()
  target_compile_options(phos-lane-g-g004 PRIVATE -Wall -Wextra -Wpedantic)
endif()


add_executable(phos-lane-g-g005
  g005_benchmark.cpp
  i001_runtime.cpp
  g003_immutable_hwrt.cpp
  i001_compute.cpp
  f003_transient_lbvh.cpp
  f005_transient_grid.cpp
  baseline/lane_a_split_rc/a001_scene.cpp
  baseline/lane_a_split_rc/a001_runtime.cpp
  baseline/lane_a_split_rc/a001_analysis.cpp
  baseline/lane_b_traversal/b002_scene.cpp
  baseline/lane_b_traversal/b002_vulkan.cpp
  baseline/lane_b_traversal/b002_compute.cpp
  baseline/lane_b_traversal/b002_hwrt.cpp
  ${PROJECT_SOURCE_DIR}/src/vk_context.cpp
)
target_include_directories(phos-lane-g-g005 PRIVATE
  "${CMAKE_SOURCE_DIR}/src"
  "${CMAKE_CURRENT_SOURCE_DIR}"
  "${CMAKE_CURRENT_SOURCE_DIR}/baseline/lane_a_split_rc"
  "${CMAKE_CURRENT_SOURCE_DIR}/baseline/lane_b_traversal"
)
target_link_libraries(phos-lane-g-g005 PRIVATE
  vk-bootstrap::vk-bootstrap
  fastgltf::fastgltf
  ${CMAKE_DL_LIBS}
)
target_compile_features(phos-lane-g-g005 PRIVATE cxx_std_20)
target_compile_definitions(phos-lane-g-g005 PRIVATE
  PHOS_GI_LANE_A_SHADER_DIR="${CMAKE_BINARY_DIR}/shaders"
  PHOS_GI_LANE_B_SHADER_DIR="${CMAKE_BINARY_DIR}/shaders"
  PHOS_GI_INTEGRATION_SHADER_DIR="${CMAKE_BINARY_DIR}/shaders"
  PHOS_GI_LANE_F_SHADER_DIR="${CMAKE_BINARY_DIR}/shaders"
)
set_target_properties(phos-lane-g-g005 PROPERTIES
  CXX_EXTENSIONS OFF
  RUNTIME_OUTPUT_DIRECTORY "${CMAKE_BINARY_DIR}"
)
add_dependencies(phos-lane-g-g005 phos-lane-g-g001-shaders)
if(MSVC)
  target_compile_options(phos-lane-g-g005 PRIVATE /W4 /permissive-)
else()
  target_compile_options(phos-lane-g-g005 PRIVATE -Wall -Wextra -Wpedantic)
endif()
