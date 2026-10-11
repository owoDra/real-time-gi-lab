add_compute_shader(
  m001_clustered_traversal
  shaders/research/lane_m_topology_backend_crossover/m001_clustered_traversal.comp.glsl
)

add_custom_target(phos-lane-m-m001-shaders DEPENDS
  "${CMAKE_BINARY_DIR}/shaders/m001_clustered_traversal.spv"
)

add_executable(phos-lane-m-contract-test
  m001_contract_test.cpp
  m001_contract.cpp
)

target_include_directories(phos-lane-m-contract-test PRIVATE
  "${CMAKE_SOURCE_DIR}/src"
  "${CMAKE_CURRENT_SOURCE_DIR}"
  "${CMAKE_CURRENT_SOURCE_DIR}/../lane_j_topology_backend_alternatives/formal_runtime/baseline/lane_b_traversal"
)
target_compile_features(phos-lane-m-contract-test PRIVATE cxx_std_20)
set_target_properties(phos-lane-m-contract-test PROPERTIES
  CXX_EXTENSIONS OFF
  RUNTIME_OUTPUT_DIRECTORY "${CMAKE_BINARY_DIR}"
)

add_executable(phos-lane-m-m001-formal-process
  ../lane_j_topology_backend_alternatives/formal_runtime/j004_formal_process.cpp
  m001_contract.cpp
  m001_clustered_adapter.cpp
  ../lane_j_topology_backend_alternatives/formal_runtime/i001_compute.cpp
  ../lane_j_topology_backend_alternatives/formal_runtime/f003_transient_lbvh.cpp
  ../lane_j_topology_backend_alternatives/formal_runtime/baseline/lane_b_traversal/b002_compute.cpp
  ../lane_j_topology_backend_alternatives/formal_runtime/baseline/lane_b_traversal/b002_hwrt.cpp
  ../lane_j_topology_backend_alternatives/formal_runtime/baseline/lane_b_traversal/b002_scene.cpp
  ../lane_j_topology_backend_alternatives/formal_runtime/baseline/lane_b_traversal/b002_vulkan.cpp
  ../lane_j_topology_backend_alternatives/j003_snapshot.cpp
  ../lane_j_topology_backend_alternatives/j003_reference.cpp
  ../lane_j_topology_backend_alternatives/j003_clustered_bvh.cpp
  ../lane_j_topology_backend_alternatives/j003_transition.cpp
  ../lane_j_topology_backend_alternatives/j003_persistent_layout.cpp
)

target_include_directories(phos-lane-m-m001-formal-process PRIVATE
  "${CMAKE_SOURCE_DIR}/src"
  "${CMAKE_CURRENT_SOURCE_DIR}"
  "${CMAKE_CURRENT_SOURCE_DIR}/../lane_j_topology_backend_alternatives"
  "${CMAKE_CURRENT_SOURCE_DIR}/../lane_j_topology_backend_alternatives/formal_runtime"
  "${CMAKE_CURRENT_SOURCE_DIR}/../lane_j_topology_backend_alternatives/formal_runtime/baseline/lane_b_traversal"
)
target_link_libraries(phos-lane-m-m001-formal-process PRIVATE
  vk-bootstrap::vk-bootstrap
  fastgltf::fastgltf
  ${CMAKE_DL_LIBS}
)
target_compile_features(phos-lane-m-m001-formal-process PRIVATE cxx_std_20)
target_compile_definitions(phos-lane-m-m001-formal-process PRIVATE
  PHOS_LANE_M_TOPOLOGY_CROSSOVER=1
  PHOS_GI_LANE_J_FORMAL_SHADER_DIR="${CMAKE_BINARY_DIR}/shaders"
  PHOS_GI_LANE_M_SHADER_DIR="${CMAKE_BINARY_DIR}/shaders"
)
set_target_properties(phos-lane-m-m001-formal-process PROPERTIES
  CXX_EXTENSIONS OFF
  RUNTIME_OUTPUT_DIRECTORY "${CMAKE_BINARY_DIR}"
)
add_dependencies(
  phos-lane-m-m001-formal-process
  phos-lane-j-j004-formal-shaders
  phos-lane-m-m001-shaders
)

if(MSVC)
  target_compile_options(phos-lane-m-contract-test PRIVATE /W4 /permissive-)
  target_compile_options(phos-lane-m-m001-formal-process PRIVATE /W4 /permissive-)
else()
  target_compile_options(phos-lane-m-contract-test PRIVATE -Wall -Wextra -Wpedantic)
  target_compile_options(phos-lane-m-m001-formal-process PRIVATE -Wall -Wextra -Wpedantic)
endif()
