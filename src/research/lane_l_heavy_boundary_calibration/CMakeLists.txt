# Lane L L001 reuses the frozen J004 FormalRuntime source directly.
add_executable(phos-lane-l-l001-formal-process
  l001_formal_process.cpp
  ../lane_j_topology_backend_alternatives/formal_runtime/i001_compute.cpp
  ../lane_j_topology_backend_alternatives/formal_runtime/f003_transient_lbvh.cpp
  ../lane_j_topology_backend_alternatives/formal_runtime/baseline/lane_b_traversal/b002_compute.cpp
  ../lane_j_topology_backend_alternatives/formal_runtime/baseline/lane_b_traversal/b002_hwrt.cpp
  ../lane_j_topology_backend_alternatives/formal_runtime/baseline/lane_b_traversal/b002_scene.cpp
  ../lane_j_topology_backend_alternatives/formal_runtime/baseline/lane_b_traversal/b002_vulkan.cpp
  ../lane_j_topology_backend_alternatives/j003_snapshot.cpp
  ../lane_j_topology_backend_alternatives/j003_reference.cpp
  ../lane_j_topology_backend_alternatives/j003_clustered_bvh.cpp
)

target_include_directories(phos-lane-l-l001-formal-process PRIVATE
  "${CMAKE_SOURCE_DIR}/src"
  "${CMAKE_CURRENT_SOURCE_DIR}"
  "${CMAKE_CURRENT_SOURCE_DIR}/../lane_j_topology_backend_alternatives"
  "${CMAKE_CURRENT_SOURCE_DIR}/../lane_j_topology_backend_alternatives/formal_runtime"
  "${CMAKE_CURRENT_SOURCE_DIR}/../lane_j_topology_backend_alternatives/formal_runtime/baseline/lane_b_traversal"
)

target_link_libraries(phos-lane-l-l001-formal-process PRIVATE
  vk-bootstrap::vk-bootstrap
  fastgltf::fastgltf
  ${CMAKE_DL_LIBS}
)
target_compile_features(phos-lane-l-l001-formal-process PRIVATE cxx_std_20)
target_compile_definitions(phos-lane-l-l001-formal-process PRIVATE
  PHOS_GI_LANE_J_FORMAL_SHADER_DIR="${CMAKE_BINARY_DIR}/shaders"
)
set_target_properties(phos-lane-l-l001-formal-process PROPERTIES
  CXX_EXTENSIONS OFF
  RUNTIME_OUTPUT_DIRECTORY "${CMAKE_BINARY_DIR}"
)
add_dependencies(
  phos-lane-l-l001-formal-process
  phos-lane-j-j004-formal-shaders
)

if(MSVC)
  target_compile_options(phos-lane-l-l001-formal-process PRIVATE /W4 /permissive-)
else()
  target_compile_options(phos-lane-l-l001-formal-process PRIVATE -Wall -Wextra -Wpedantic)
endif()
