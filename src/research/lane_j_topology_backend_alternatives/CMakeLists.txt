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
  j003_transition.cpp
  j003_persistent_layout.cpp
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


add_executable(phos-lane-j-j003-transition-replay
  j003_transition_replay.cpp
  j003_snapshot.cpp
  j003_transition.cpp
  j003_clustered_bvh.cpp
)

target_include_directories(phos-lane-j-j003-transition-replay PRIVATE
  "${CMAKE_CURRENT_SOURCE_DIR}"
)
target_compile_features(phos-lane-j-j003-transition-replay PRIVATE cxx_std_20)
set_target_properties(phos-lane-j-j003-transition-replay PROPERTIES
  CXX_EXTENSIONS OFF
  RUNTIME_OUTPUT_DIRECTORY "${CMAKE_BINARY_DIR}"
)
if(MSVC)
  target_compile_options(phos-lane-j-j003-transition-replay PRIVATE /W4 /permissive-)
else()
  target_compile_options(phos-lane-j-j003-transition-replay PRIVATE -Wall -Wextra -Wpedantic)
endif()


add_executable(phos-lane-j-j003-persistent-layout-replay
  j003_persistent_layout_replay.cpp
  j003_snapshot.cpp
  j003_transition.cpp
  j003_clustered_bvh.cpp
  j003_persistent_layout.cpp
)

target_include_directories(phos-lane-j-j003-persistent-layout-replay PRIVATE
  "${CMAKE_CURRENT_SOURCE_DIR}"
)
target_compile_features(phos-lane-j-j003-persistent-layout-replay PRIVATE cxx_std_20)
set_target_properties(phos-lane-j-j003-persistent-layout-replay PROPERTIES
  CXX_EXTENSIONS OFF
  RUNTIME_OUTPUT_DIRECTORY "${CMAKE_BINARY_DIR}"
)
if(MSVC)
  target_compile_options(phos-lane-j-j003-persistent-layout-replay PRIVATE /W4 /permissive-)
else()
  target_compile_options(phos-lane-j-j003-persistent-layout-replay PRIVATE -Wall -Wextra -Wpedantic)
endif()


add_executable(phos-lane-j-j003-persistent-gpu-replay
  j003_persistent_gpu_replay.cpp
  j003_snapshot.cpp
  j003_transition.cpp
  j003_persistent_layout.cpp
  j003_persistent_gpu.cpp
  j003_reference.cpp
  j003_clustered_bvh.cpp
  ${PROJECT_SOURCE_DIR}/src/vk_context.cpp
)

target_include_directories(phos-lane-j-j003-persistent-gpu-replay PRIVATE
  "${CMAKE_SOURCE_DIR}/src"
  "${CMAKE_CURRENT_SOURCE_DIR}"
)
target_link_libraries(phos-lane-j-j003-persistent-gpu-replay PRIVATE
  vk-bootstrap::vk-bootstrap
  ${CMAKE_DL_LIBS}
)
target_compile_features(phos-lane-j-j003-persistent-gpu-replay PRIVATE cxx_std_20)
target_compile_definitions(phos-lane-j-j003-persistent-gpu-replay PRIVATE
  PHOS_GI_LANE_J_SHADER_DIR="${CMAKE_BINARY_DIR}/shaders"
)
set_target_properties(phos-lane-j-j003-persistent-gpu-replay PROPERTIES
  CXX_EXTENSIONS OFF
  RUNTIME_OUTPUT_DIRECTORY "${CMAKE_BINARY_DIR}"
)
add_dependencies(phos-lane-j-j003-persistent-gpu-replay phos-lane-j-j003-shaders)
if(MSVC)
  target_compile_options(phos-lane-j-j003-persistent-gpu-replay PRIVATE /W4 /permissive-)
else()
  target_compile_options(phos-lane-j-j003-persistent-gpu-replay PRIVATE -Wall -Wextra -Wpedantic)
endif()


# Issue #23 J004 preflight. The Lane-E HWRT source below is a selective
# comparator snapshot from the accepted E005 measurement commit; Lane E is not
# merged wholesale.
add_executable(phos-lane-j-j004-memory-preflight
  j004_relative_memory_preflight.cpp
  j003_snapshot.cpp
  j003_transition.cpp
  j003_clustered_bvh.cpp
  j003_persistent_layout.cpp
  j003_persistent_gpu.cpp
  baseline/lane_e_hwrt/b002_vulkan.cpp
  baseline/lane_e_hwrt/b002_hwrt.cpp
  ${PROJECT_SOURCE_DIR}/src/vk_context.cpp
)

target_include_directories(phos-lane-j-j004-memory-preflight PRIVATE
  "${CMAKE_SOURCE_DIR}/src"
  "${CMAKE_CURRENT_SOURCE_DIR}"
  "${CMAKE_CURRENT_SOURCE_DIR}/baseline/lane_e_hwrt"
)
target_link_libraries(phos-lane-j-j004-memory-preflight PRIVATE
  vk-bootstrap::vk-bootstrap
  ${CMAKE_DL_LIBS}
)
target_compile_features(phos-lane-j-j004-memory-preflight PRIVATE cxx_std_20)
set_target_properties(phos-lane-j-j004-memory-preflight PROPERTIES
  CXX_EXTENSIONS OFF
  RUNTIME_OUTPUT_DIRECTORY "${CMAKE_BINARY_DIR}"
)
if(MSVC)
  target_compile_options(phos-lane-j-j004-memory-preflight PRIVATE /W4 /permissive-)
else()
  target_compile_options(phos-lane-j-j004-memory-preflight PRIVATE -Wall -Wextra -Wpedantic)
endif()

add_subdirectory(formal_runtime)
