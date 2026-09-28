# Lane B owns this directory. Keep traversal-research build changes lane-local.
add_executable(phos-lane-b-b001
  b001_controls.cpp
  traversal_contract.hpp
  traversal_common.hpp
  software_bvh.hpp
  sparse_grid.hpp
)
target_include_directories(phos-lane-b-b001 PRIVATE "${CMAKE_CURRENT_SOURCE_DIR}")
target_compile_features(phos-lane-b-b001 PRIVATE cxx_std_20)
set_target_properties(phos-lane-b-b001 PROPERTIES CXX_EXTENSIONS OFF RUNTIME_OUTPUT_DIRECTORY "${CMAKE_BINARY_DIR}")
if(MSVC)
  target_compile_options(phos-lane-b-b001 PRIVATE /W4 /permissive-)
else()
  target_compile_options(phos-lane-b-b001 PRIVATE -Wall -Wextra -Wpedantic)
endif()

# GPU-independent B002 semantic gate. This intentionally stays independent of
# Vulkan/fastgltf so exact-stream parsing and hierarchical traversal correctness
# can be checked before target-GPU bring-up.
add_executable(phos-lane-b-b002-smoke
  b002_contract_smoke.cpp
  lane_a_stream_v1.hpp
  hierarchical_stratabrick.hpp
  traversal_contract.hpp
  traversal_common.hpp
)
target_include_directories(phos-lane-b-b002-smoke PRIVATE "${CMAKE_CURRENT_SOURCE_DIR}")
target_compile_features(phos-lane-b-b002-smoke PRIVATE cxx_std_20)
set_target_properties(phos-lane-b-b002-smoke PROPERTIES CXX_EXTENSIONS OFF RUNTIME_OUTPUT_DIRECTORY "${CMAKE_BINARY_DIR}")
if(MSVC)
  target_compile_options(phos-lane-b-b002-smoke PRIVATE /W4 /permissive-)
else()
  target_compile_options(phos-lane-b-b002-smoke PRIVATE -Wall -Wextra -Wpedantic)
endif()

# B002 final-evidence runtime: exact Lane A replay on GPU software BVH,
# hierarchical traversal, and explicit-device HWRT/ray-query.
add_compute_shader(
  lane_b_b002_software_bvh
  shaders/research/lane_b_traversal/b002_software_bvh.comp.glsl)
add_compute_shader(
  lane_b_b002_hierarchical
  shaders/research/lane_b_traversal/b002_hierarchical.comp.glsl)
add_compute_shader(
  lane_b_b002_hwrt
  shaders/research/lane_b_traversal/b002_hwrt.comp.glsl)

add_custom_target(phos-lane-b-b002-shaders DEPENDS
  "${CMAKE_BINARY_DIR}/shaders/lane_b_b002_software_bvh.spv"
  "${CMAKE_BINARY_DIR}/shaders/lane_b_b002_hierarchical.spv"
  "${CMAKE_BINARY_DIR}/shaders/lane_b_b002_hwrt.spv"
)

add_executable(phos-lane-b-b002
  b002_benchmark.cpp
  b002_scene.cpp
  b002_vulkan.cpp
  b002_compute.cpp
  b002_hwrt.cpp
  b002_scene.hpp
  b002_replay.hpp
  b002_vulkan.hpp
  b002_compute.hpp
  b002_hwrt.hpp
  b002_gpu_layout.hpp
  gpu_software_bvh.hpp
  hierarchical_stratabrick.hpp
  lane_a_stream_v1.hpp
  software_bvh.hpp
  traversal_contract.hpp
  traversal_common.hpp
)
target_include_directories(phos-lane-b-b002 PRIVATE
  "${CMAKE_CURRENT_SOURCE_DIR}"
  "${CMAKE_SOURCE_DIR}/src"
)
target_link_libraries(phos-lane-b-b002 PRIVATE
  vk-bootstrap::vk-bootstrap
  fastgltf::fastgltf
  ${CMAKE_DL_LIBS}
)
target_compile_features(phos-lane-b-b002 PRIVATE cxx_std_20)
target_compile_definitions(phos-lane-b-b002 PRIVATE
  PHOS_GI_LANE_B_SHADER_DIR="${CMAKE_BINARY_DIR}/shaders"
)
set_target_properties(phos-lane-b-b002 PROPERTIES
  CXX_EXTENSIONS OFF
  RUNTIME_OUTPUT_DIRECTORY "${CMAKE_BINARY_DIR}"
)
add_dependencies(phos-lane-b-b002 phos-lane-b-b002-shaders)
if(MSVC)
  target_compile_options(phos-lane-b-b002 PRIVATE /W4 /permissive-)
else()
  target_compile_options(phos-lane-b-b002 PRIVATE -Wall -Wextra -Wpedantic)
endif()
