# Issue #22 Lane E timing revalidation.

add_executable(phos-lane-e-e001-process
  e001_process.cpp
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

target_include_directories(phos-lane-e-e001-process PRIVATE
  "${CMAKE_SOURCE_DIR}/src"
  "${CMAKE_SOURCE_DIR}/src/research/lane_a_split_rc"
  "${CMAKE_SOURCE_DIR}/src/research/lane_b_traversal"
  "${CMAKE_SOURCE_DIR}/src/research/lane_e_dynamic_geometry"
  "${CMAKE_SOURCE_DIR}/src/research/integration"
)
target_link_libraries(phos-lane-e-e001-process PRIVATE
  vk-bootstrap::vk-bootstrap
  fastgltf::fastgltf
  ${CMAKE_DL_LIBS}
)
target_compile_features(phos-lane-e-e001-process PRIVATE cxx_std_20)
target_compile_definitions(phos-lane-e-e001-process PRIVATE
  PHOS_GI_LANE_A_SHADER_DIR="${CMAKE_BINARY_DIR}/shaders"
  PHOS_GI_LANE_B_SHADER_DIR="${CMAKE_BINARY_DIR}/shaders"
  PHOS_GI_INTEGRATION_SHADER_DIR="${CMAKE_BINARY_DIR}/shaders"
)
set_target_properties(phos-lane-e-e001-process PROPERTIES
  CXX_EXTENSIONS OFF
  RUNTIME_OUTPUT_DIRECTORY "${CMAKE_BINARY_DIR}"
)
add_dependencies(
  phos-lane-e-e001-process
  phos-i001-shaders
  phos-lane-a-split-rc-shaders
  phos-lane-b-b002-shaders
  phos-lane-b-b003-shaders
)
if(MSVC)
  target_compile_options(phos-lane-e-e001-process PRIVATE /W4 /permissive-)
else()
  target_compile_options(phos-lane-e-e001-process PRIVATE -Wall -Wextra -Wpedantic)
endif()
