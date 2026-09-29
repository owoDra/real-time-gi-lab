# Issue #16 Lane F owns this directory.

add_executable(phos-lane-f-f001-census
  f001_census.cpp
  ../lane_a_split_rc/a001_scene.cpp
  ../lane_a_split_rc/a001_runtime.cpp
  ../lane_a_split_rc/a001_analysis.cpp
  ../lane_b_traversal/b002_scene.cpp
  ${PROJECT_SOURCE_DIR}/src/vk_context.cpp
)
target_include_directories(phos-lane-f-f001-census PRIVATE
  "${CMAKE_SOURCE_DIR}/src"
  "${CMAKE_SOURCE_DIR}/src/research/lane_a_split_rc"
  "${CMAKE_SOURCE_DIR}/src/research/lane_b_traversal"
  "${CMAKE_CURRENT_SOURCE_DIR}"
)
target_link_libraries(phos-lane-f-f001-census PRIVATE
  vk-bootstrap::vk-bootstrap
  fastgltf::fastgltf
  ${CMAKE_DL_LIBS}
)
target_compile_features(phos-lane-f-f001-census PRIVATE cxx_std_20)
target_compile_definitions(phos-lane-f-f001-census PRIVATE
  PHOS_GI_LANE_A_SHADER_DIR="${CMAKE_BINARY_DIR}/shaders"
)
set_target_properties(phos-lane-f-f001-census PROPERTIES
  CXX_EXTENSIONS OFF
  RUNTIME_OUTPUT_DIRECTORY "${CMAKE_BINARY_DIR}"
)
add_dependencies(phos-lane-f-f001-census phos-lane-a-split-rc-shaders)

add_executable(phos-lane-f-i001-control
  f001_control_benchmark.cpp
  ../integration/i001_runtime.cpp
  ../integration/i001_compute.cpp
  f003_transient_lbvh.cpp
  f005_transient_grid.cpp
  ../lane_a_split_rc/a001_scene.cpp
  ../lane_a_split_rc/a001_runtime.cpp
  ../lane_a_split_rc/a001_analysis.cpp
  ../lane_b_traversal/b002_scene.cpp
  ../lane_b_traversal/b002_vulkan.cpp
  ../lane_b_traversal/b002_compute.cpp
  ../lane_b_traversal/b002_hwrt.cpp
  ${PROJECT_SOURCE_DIR}/src/vk_context.cpp
)
target_include_directories(phos-lane-f-i001-control PRIVATE
  "${CMAKE_SOURCE_DIR}/src"
  "${CMAKE_SOURCE_DIR}/src/research/lane_a_split_rc"
  "${CMAKE_SOURCE_DIR}/src/research/lane_b_traversal"
  "${CMAKE_SOURCE_DIR}/src/research/integration"
  "${CMAKE_CURRENT_SOURCE_DIR}"
)
target_link_libraries(phos-lane-f-i001-control PRIVATE
  vk-bootstrap::vk-bootstrap
  fastgltf::fastgltf
  ${CMAKE_DL_LIBS}
)
target_compile_features(phos-lane-f-i001-control PRIVATE cxx_std_20)
target_compile_definitions(phos-lane-f-i001-control PRIVATE
  PHOS_GI_LANE_A_SHADER_DIR="${CMAKE_BINARY_DIR}/shaders"
  PHOS_GI_LANE_B_SHADER_DIR="${CMAKE_BINARY_DIR}/shaders"
  PHOS_GI_INTEGRATION_SHADER_DIR="${CMAKE_BINARY_DIR}/shaders"
  PHOS_GI_LANE_F_SHADER_DIR="${CMAKE_BINARY_DIR}/shaders"
)
set_target_properties(phos-lane-f-i001-control PROPERTIES
  CXX_EXTENSIONS OFF
  RUNTIME_OUTPUT_DIRECTORY "${CMAKE_BINARY_DIR}"
)
add_dependencies(
  phos-lane-f-i001-control
  phos-i001-shaders
  phos-lane-a-split-rc-shaders
  phos-lane-b-b002-shaders
  phos-lane-b-b003-shaders
)


# F003 end-to-end transient LBVH shaders.
add_compute_shader(
  lane_f_f003_lbvh_builder
  shaders/research/lane_f_dynamic_geometry_alternatives/f003_lbvh_builder.comp.glsl
)
add_compute_shader(
  lane_f_f003_dynamic_traversal
  shaders/research/lane_f_dynamic_geometry_alternatives/f003_dynamic_traversal.comp.glsl
)
add_compute_shader(
  lane_f_f003_hit_merge
  shaders/research/lane_f_dynamic_geometry_alternatives/f003_hit_merge.comp.glsl
)
add_custom_target(phos-lane-f-f003-shaders DEPENDS
  "${CMAKE_BINARY_DIR}/shaders/lane_f_f003_lbvh_builder.spv"
  "${CMAKE_BINARY_DIR}/shaders/lane_f_f003_dynamic_traversal.spv"
  "${CMAKE_BINARY_DIR}/shaders/lane_f_f003_hit_merge.spv"
)

add_executable(phos-lane-f-f003
  f003_benchmark.cpp
  f003_transient_lbvh.cpp
  f003_transient_lbvh.hpp
  f005_transient_grid.cpp
  f005_transient_grid.hpp
  ../integration/i001_runtime.cpp
  ../integration/i001_compute.cpp
  ../lane_a_split_rc/a001_scene.cpp
  ../lane_a_split_rc/a001_runtime.cpp
  ../lane_a_split_rc/a001_analysis.cpp
  ../lane_b_traversal/b002_scene.cpp
  ../lane_b_traversal/b002_vulkan.cpp
  ../lane_b_traversal/b002_compute.cpp
  ../lane_b_traversal/b002_hwrt.cpp
  ${PROJECT_SOURCE_DIR}/src/vk_context.cpp
)
target_include_directories(phos-lane-f-f003 PRIVATE
  "${CMAKE_SOURCE_DIR}/src"
  "${CMAKE_SOURCE_DIR}/src/research/lane_a_split_rc"
  "${CMAKE_SOURCE_DIR}/src/research/lane_b_traversal"
  "${CMAKE_SOURCE_DIR}/src/research/integration"
  "${CMAKE_CURRENT_SOURCE_DIR}"
)
target_link_libraries(phos-lane-f-f003 PRIVATE
  vk-bootstrap::vk-bootstrap
  fastgltf::fastgltf
  ${CMAKE_DL_LIBS}
)
target_compile_features(phos-lane-f-f003 PRIVATE cxx_std_20)
target_compile_definitions(phos-lane-f-f003 PRIVATE
  PHOS_GI_LANE_A_SHADER_DIR="${CMAKE_BINARY_DIR}/shaders"
  PHOS_GI_LANE_B_SHADER_DIR="${CMAKE_BINARY_DIR}/shaders"
  PHOS_GI_INTEGRATION_SHADER_DIR="${CMAKE_BINARY_DIR}/shaders"
  PHOS_GI_LANE_F_SHADER_DIR="${CMAKE_BINARY_DIR}/shaders"
)
set_target_properties(phos-lane-f-f003 PROPERTIES
  CXX_EXTENSIONS OFF
  RUNTIME_OUTPUT_DIRECTORY "${CMAKE_BINARY_DIR}"
)
add_dependencies(
  phos-lane-f-f003
  phos-lane-f-f003-shaders
  phos-i001-shaders
  phos-lane-a-split-rc-shaders
  phos-lane-b-b002-shaders
  phos-lane-b-b003-shaders
)

# F005 end-to-end sorted two-level grid control.
add_compute_shader(
  lane_f_f005_grid_builder
  shaders/research/lane_f_dynamic_geometry_alternatives/f005_grid_builder.comp.glsl
)
add_compute_shader(
  lane_f_f005_grid_traversal
  shaders/research/lane_f_dynamic_geometry_alternatives/f005_grid_traversal.comp.glsl
)
add_custom_target(phos-lane-f-f005-shaders DEPENDS
  "${CMAKE_BINARY_DIR}/shaders/lane_f_f005_grid_builder.spv"
  "${CMAKE_BINARY_DIR}/shaders/lane_f_f005_grid_traversal.spv"
)

add_executable(phos-lane-f-f005
  f005_benchmark.cpp
  f003_transient_lbvh.cpp
  f005_transient_grid.cpp
  f005_transient_grid.hpp
  ../integration/i001_runtime.cpp
  ../integration/i001_compute.cpp
  ../lane_a_split_rc/a001_scene.cpp
  ../lane_a_split_rc/a001_runtime.cpp
  ../lane_a_split_rc/a001_analysis.cpp
  ../lane_b_traversal/b002_scene.cpp
  ../lane_b_traversal/b002_vulkan.cpp
  ../lane_b_traversal/b002_compute.cpp
  ../lane_b_traversal/b002_hwrt.cpp
  ${PROJECT_SOURCE_DIR}/src/vk_context.cpp
)
target_include_directories(phos-lane-f-f005 PRIVATE
  "${CMAKE_SOURCE_DIR}/src"
  "${CMAKE_SOURCE_DIR}/src/research/lane_a_split_rc"
  "${CMAKE_SOURCE_DIR}/src/research/lane_b_traversal"
  "${CMAKE_SOURCE_DIR}/src/research/integration"
  "${CMAKE_CURRENT_SOURCE_DIR}"
)
target_link_libraries(phos-lane-f-f005 PRIVATE
  vk-bootstrap::vk-bootstrap
  fastgltf::fastgltf
  ${CMAKE_DL_LIBS}
)
target_compile_features(phos-lane-f-f005 PRIVATE cxx_std_20)
target_compile_definitions(phos-lane-f-f005 PRIVATE
  PHOS_GI_LANE_A_SHADER_DIR="${CMAKE_BINARY_DIR}/shaders"
  PHOS_GI_LANE_B_SHADER_DIR="${CMAKE_BINARY_DIR}/shaders"
  PHOS_GI_INTEGRATION_SHADER_DIR="${CMAKE_BINARY_DIR}/shaders"
  PHOS_GI_LANE_F_SHADER_DIR="${CMAKE_BINARY_DIR}/shaders"
)
set_target_properties(phos-lane-f-f005 PROPERTIES
  CXX_EXTENSIONS OFF
  RUNTIME_OUTPUT_DIRECTORY "${CMAKE_BINARY_DIR}"
)
add_dependencies(
  phos-lane-f-f005
  phos-lane-f-f003-shaders
  phos-lane-f-f005-shaders
  phos-i001-shaders
  phos-lane-a-split-rc-shaders
  phos-lane-b-b002-shaders
  phos-lane-b-b003-shaders
)

# F006 geometry-class crossover controls.
add_executable(phos-lane-f-f006
  f006_benchmark.cpp
  f003_transient_lbvh.cpp
  f003_transient_lbvh.hpp
  f005_transient_grid.cpp
  f005_transient_grid.hpp
  ../integration/i001_runtime.cpp
  ../integration/i001_compute.cpp
  ../lane_a_split_rc/a001_scene.cpp
  ../lane_a_split_rc/a001_runtime.cpp
  ../lane_a_split_rc/a001_analysis.cpp
  ../lane_b_traversal/b002_scene.cpp
  ../lane_b_traversal/b002_vulkan.cpp
  ../lane_b_traversal/b002_compute.cpp
  ../lane_b_traversal/b002_hwrt.cpp
  ${PROJECT_SOURCE_DIR}/src/vk_context.cpp
)
target_include_directories(phos-lane-f-f006 PRIVATE
  "${CMAKE_SOURCE_DIR}/src"
  "${CMAKE_SOURCE_DIR}/src/research/lane_a_split_rc"
  "${CMAKE_SOURCE_DIR}/src/research/lane_b_traversal"
  "${CMAKE_SOURCE_DIR}/src/research/integration"
  "${CMAKE_CURRENT_SOURCE_DIR}"
)
target_link_libraries(phos-lane-f-f006 PRIVATE
  vk-bootstrap::vk-bootstrap
  fastgltf::fastgltf
  ${CMAKE_DL_LIBS}
)
target_compile_features(phos-lane-f-f006 PRIVATE cxx_std_20)
target_compile_definitions(phos-lane-f-f006 PRIVATE
  PHOS_GI_LANE_A_SHADER_DIR="${CMAKE_BINARY_DIR}/shaders"
  PHOS_GI_LANE_B_SHADER_DIR="${CMAKE_BINARY_DIR}/shaders"
  PHOS_GI_INTEGRATION_SHADER_DIR="${CMAKE_BINARY_DIR}/shaders"
  PHOS_GI_LANE_F_SHADER_DIR="${CMAKE_BINARY_DIR}/shaders"
)
set_target_properties(phos-lane-f-f006 PROPERTIES
  CXX_EXTENSIONS OFF
  RUNTIME_OUTPUT_DIRECTORY "${CMAKE_BINARY_DIR}"
)
add_dependencies(
  phos-lane-f-f006
  phos-lane-f-f003-shaders
  phos-lane-f-f005-shaders
  phos-i001-shaders
  phos-lane-a-split-rc-shaders
  phos-lane-b-b002-shaders
  phos-lane-b-b003-shaders
)

# F007 final integration replay.
add_executable(phos-lane-f-f007
  f007_benchmark.cpp
  f003_transient_lbvh.cpp
  f003_transient_lbvh.hpp
  f005_transient_grid.cpp
  f005_transient_grid.hpp
  ../integration/i001_runtime.cpp
  ../integration/i001_compute.cpp
  ../lane_a_split_rc/a001_scene.cpp
  ../lane_a_split_rc/a001_runtime.cpp
  ../lane_a_split_rc/a001_analysis.cpp
  ../lane_b_traversal/b002_scene.cpp
  ../lane_b_traversal/b002_vulkan.cpp
  ../lane_b_traversal/b002_compute.cpp
  ../lane_b_traversal/b002_hwrt.cpp
  ${PROJECT_SOURCE_DIR}/src/vk_context.cpp
)
target_include_directories(phos-lane-f-f007 PRIVATE
  "${CMAKE_SOURCE_DIR}/src"
  "${CMAKE_SOURCE_DIR}/src/research/lane_a_split_rc"
  "${CMAKE_SOURCE_DIR}/src/research/lane_b_traversal"
  "${CMAKE_SOURCE_DIR}/src/research/integration"
  "${CMAKE_CURRENT_SOURCE_DIR}"
)
target_link_libraries(phos-lane-f-f007 PRIVATE
  vk-bootstrap::vk-bootstrap
  fastgltf::fastgltf
  ${CMAKE_DL_LIBS}
)
target_compile_features(phos-lane-f-f007 PRIVATE cxx_std_20)
target_compile_definitions(phos-lane-f-f007 PRIVATE
  PHOS_GI_LANE_A_SHADER_DIR="${CMAKE_BINARY_DIR}/shaders"
  PHOS_GI_LANE_B_SHADER_DIR="${CMAKE_BINARY_DIR}/shaders"
  PHOS_GI_INTEGRATION_SHADER_DIR="${CMAKE_BINARY_DIR}/shaders"
  PHOS_GI_LANE_F_SHADER_DIR="${CMAKE_BINARY_DIR}/shaders"
)
set_target_properties(phos-lane-f-f007 PROPERTIES
  CXX_EXTENSIONS OFF
  RUNTIME_OUTPUT_DIRECTORY "${CMAKE_BINARY_DIR}"
)
add_dependencies(
  phos-lane-f-f007
  phos-lane-f-f003-shaders
  phos-lane-f-f005-shaders
  phos-i001-shaders
  phos-lane-a-split-rc-shaders
  phos-lane-b-b002-shaders
  phos-lane-b-b003-shaders
)

# F002 pure-GPU transient LBVH builder. The shader deliberately owns all
# frame-local builder phases so no CPU sort/topology work can escape timing.
add_compute_shader(
  lane_f_f002_lbvh
  shaders/research/lane_f_dynamic_geometry_alternatives/f002_lbvh.comp.glsl
)
add_custom_target(phos-lane-f-f002-shaders DEPENDS
  "${CMAKE_BINARY_DIR}/shaders/lane_f_f002_lbvh.spv"
)

add_executable(phos-lane-f-f002-lbvh
  f002_lbvh_benchmark.cpp
  f002_lbvh_runtime.cpp
  f002_lbvh_runtime.hpp
  ../lane_b_traversal/b002_scene.cpp
  ../lane_b_traversal/b002_vulkan.cpp
  ../lane_b_traversal/b002_scene.hpp
  ../lane_b_traversal/b002_vulkan.hpp
  ../lane_b_traversal/b002_gpu_layout.hpp
  ../lane_b_traversal/hierarchical_stratabrick.hpp
  ../lane_b_traversal/traversal_common.hpp
  ../lane_b_traversal/traversal_contract.hpp
)
target_include_directories(phos-lane-f-f002-lbvh PRIVATE
  "${CMAKE_SOURCE_DIR}/src"
  "${CMAKE_SOURCE_DIR}/src/research/lane_b_traversal"
  "${CMAKE_CURRENT_SOURCE_DIR}"
)
target_link_libraries(phos-lane-f-f002-lbvh PRIVATE
  vk-bootstrap::vk-bootstrap
  fastgltf::fastgltf
  ${CMAKE_DL_LIBS}
)
target_compile_features(phos-lane-f-f002-lbvh PRIVATE cxx_std_20)
target_compile_definitions(phos-lane-f-f002-lbvh PRIVATE
  PHOS_GI_LANE_F_SHADER_DIR="${CMAKE_BINARY_DIR}/shaders"
)
set_target_properties(phos-lane-f-f002-lbvh PROPERTIES
  CXX_EXTENSIONS OFF
  RUNTIME_OUTPUT_DIRECTORY "${CMAKE_BINARY_DIR}"
)
add_dependencies(phos-lane-f-f002-lbvh phos-lane-f-f002-shaders)

foreach(target phos-lane-f-f001-census phos-lane-f-i001-control phos-lane-f-f002-lbvh phos-lane-f-f003 phos-lane-f-f005 phos-lane-f-f006 phos-lane-f-f007)
  if(MSVC)
    target_compile_options(${target} PRIVATE /W4 /permissive-)
  else()
    target_compile_options(${target} PRIVATE -Wall -Wextra -Wpedantic)
  endif()
endforeach()
