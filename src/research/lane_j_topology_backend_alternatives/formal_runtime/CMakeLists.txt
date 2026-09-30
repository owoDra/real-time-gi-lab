# J004 formal same-run crossover runtime.
add_compute_shader(j004_f003_lbvh_builder
  shaders/research/lane_j_topology_backend_alternatives/formal_runtime/f003_lbvh_builder.comp.glsl)
add_compute_shader(j004_f003_dynamic_traversal
  shaders/research/lane_j_topology_backend_alternatives/formal_runtime/f003_dynamic_traversal.comp.glsl)
add_compute_shader(j004_f003_hit_merge
  shaders/research/lane_j_topology_backend_alternatives/formal_runtime/f003_hit_merge.comp.glsl)
add_compute_shader(j004_i001_hwrt
  shaders/research/lane_j_topology_backend_alternatives/formal_runtime/i001_hwrt.comp.glsl)
add_compute_shader(j004_i001_quantized_bvh8
  shaders/research/lane_j_topology_backend_alternatives/formal_runtime/i001_quantized_bvh8.comp.glsl)
add_compute_shader(j004_i001_software_bvh
  shaders/research/lane_j_topology_backend_alternatives/formal_runtime/i001_software_bvh.comp.glsl)
add_compute_shader(j004_i001_radiance
  shaders/research/lane_j_topology_backend_alternatives/formal_runtime/i001_radiance.comp.glsl)
add_compute_shader(j004_i001_storage_update
  shaders/research/lane_j_topology_backend_alternatives/formal_runtime/i001_storage_update.comp.glsl)
add_compute_shader(j004_i001_storage_invalidate
  shaders/research/lane_j_topology_backend_alternatives/formal_runtime/i001_storage_invalidate.comp.glsl)
add_compute_shader(j004_i001_storage_resolve
  shaders/research/lane_j_topology_backend_alternatives/formal_runtime/i001_storage_resolve.comp.glsl)
add_compute_shader(j004_merge
  shaders/research/lane_j_topology_backend_alternatives/formal_runtime/merge.comp.glsl)

add_custom_target(phos-lane-j-j004-formal-shaders DEPENDS
  "${CMAKE_BINARY_DIR}/shaders/j004_f003_lbvh_builder.spv"
  "${CMAKE_BINARY_DIR}/shaders/j004_f003_dynamic_traversal.spv"
  "${CMAKE_BINARY_DIR}/shaders/j004_f003_hit_merge.spv"
  "${CMAKE_BINARY_DIR}/shaders/j004_i001_hwrt.spv"
  "${CMAKE_BINARY_DIR}/shaders/j004_i001_quantized_bvh8.spv"
  "${CMAKE_BINARY_DIR}/shaders/j004_i001_software_bvh.spv"
  "${CMAKE_BINARY_DIR}/shaders/j004_i001_radiance.spv"
  "${CMAKE_BINARY_DIR}/shaders/j004_i001_storage_update.spv"
  "${CMAKE_BINARY_DIR}/shaders/j004_i001_storage_invalidate.spv"
  "${CMAKE_BINARY_DIR}/shaders/j004_i001_storage_resolve.spv"
  "${CMAKE_BINARY_DIR}/shaders/j004_merge.spv")

add_executable(phos-lane-j-j004-formal-process
  j004_formal_process.cpp
  i001_compute.cpp
  f003_transient_lbvh.cpp
  baseline/lane_b_traversal/b002_compute.cpp
  baseline/lane_b_traversal/b002_hwrt.cpp
  baseline/lane_b_traversal/b002_scene.cpp
  baseline/lane_b_traversal/b002_vulkan.cpp
  ../j003_snapshot.cpp
  ../j003_reference.cpp)

target_include_directories(phos-lane-j-j004-formal-process PRIVATE
  "${CMAKE_SOURCE_DIR}/src"
  "${CMAKE_CURRENT_SOURCE_DIR}"
  "${CMAKE_CURRENT_SOURCE_DIR}/.."
  "${CMAKE_CURRENT_SOURCE_DIR}/baseline/lane_b_traversal")
target_link_libraries(phos-lane-j-j004-formal-process PRIVATE
  vk-bootstrap::vk-bootstrap
  fastgltf::fastgltf
  ${CMAKE_DL_LIBS})
target_compile_features(phos-lane-j-j004-formal-process PRIVATE cxx_std_20)
target_compile_definitions(phos-lane-j-j004-formal-process PRIVATE
  PHOS_GI_LANE_J_FORMAL_SHADER_DIR="${CMAKE_BINARY_DIR}/shaders")
set_target_properties(phos-lane-j-j004-formal-process PROPERTIES
  CXX_EXTENSIONS OFF
  RUNTIME_OUTPUT_DIRECTORY "${CMAKE_BINARY_DIR}")
add_dependencies(phos-lane-j-j004-formal-process phos-lane-j-j004-formal-shaders)
if(MSVC)
  target_compile_options(phos-lane-j-j004-formal-process PRIVATE /W4 /permissive-)
else()
  target_compile_options(phos-lane-j-j004-formal-process PRIVATE -Wall -Wextra -Wpedantic)
endif()
