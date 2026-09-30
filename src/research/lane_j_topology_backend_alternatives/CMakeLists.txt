add_compute_shader(
  j003_traverse
  shaders/research/lane_j_topology_backend_alternatives/j003_traverse.comp.glsl
)

set(J003_TRAVERSE_SPV "${CMAKE_BINARY_DIR}/shaders/j003_traverse.spv")
add_custom_target(phos-lane-j-j003-shaders DEPENDS "${J003_TRAVERSE_SPV}")

add_executable(phos-lane-j-j003-probe
  j003_gpu_probe.cpp
  j003_snapshot.cpp
  j003_clustered_bvh.cpp
  j003_reference.cpp
  j003_gpu_runtime.cpp
  ${PROJECT_SOURCE_DIR}/src/vk_context.cpp
)

target_include_directories(phos-lane-j-j003-probe PRIVATE
  "${CMAKE_SOURCE_DIR}/src"
  "${CMAKE_CURRENT_SOURCE_DIR}"
)

target_link_libraries(phos-lane-j-j003-probe PRIVATE
  vk-bootstrap::vk-bootstrap
  ${CMAKE_DL_LIBS}
)

target_compile_features(phos-lane-j-j003-probe PRIVATE cxx_std_20)
target_compile_definitions(phos-lane-j-j003-probe PRIVATE
  PHOS_GI_LANE_J_SHADER_DIR="${CMAKE_BINARY_DIR}/shaders"
)
set_target_properties(phos-lane-j-j003-probe PROPERTIES
  CXX_EXTENSIONS OFF
  RUNTIME_OUTPUT_DIRECTORY "${CMAKE_BINARY_DIR}"
)
add_dependencies(phos-lane-j-j003-probe phos-lane-j-j003-shaders)

if(MSVC)
  target_compile_options(phos-lane-j-j003-probe PRIVATE /W4 /permissive-)
else()
  target_compile_options(phos-lane-j-j003-probe PRIVATE -Wall -Wextra -Wpedantic)
endif()


add_executable(phos-lane-j-contract-test
  j003_contract_test.cpp
  j003_clustered_bvh.cpp
  j003_reference.cpp
)

target_include_directories(phos-lane-j-contract-test PRIVATE
  "${CMAKE_CURRENT_SOURCE_DIR}"
)
target_compile_features(phos-lane-j-contract-test PRIVATE cxx_std_20)
set_target_properties(phos-lane-j-contract-test PROPERTIES
  CXX_EXTENSIONS OFF
  RUNTIME_OUTPUT_DIRECTORY "${CMAKE_BINARY_DIR}"
)
if(MSVC)
  target_compile_options(phos-lane-j-contract-test PRIVATE /W4 /permissive-)
else()
  target_compile_options(phos-lane-j-contract-test PRIVATE -Wall -Wextra -Wpedantic)
endif()
