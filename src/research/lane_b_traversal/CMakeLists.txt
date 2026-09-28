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
