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
