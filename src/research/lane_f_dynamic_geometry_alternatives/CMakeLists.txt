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

foreach(target phos-lane-f-f001-census phos-lane-f-i001-control)
  if(MSVC)
    target_compile_options(${target} PRIVATE /W4 /permissive-)
  else()
    target_compile_options(${target} PRIVATE -Wall -Wextra -Wpedantic)
  endif()
endforeach()
