# Issue #19 Lane I owns this directory.
add_compute_shader(
  lane_i_calibration
  shaders/research/lane_i_measurement_calibration/i001_calibration.comp.glsl)

add_library(phos-lane-i-contract STATIC i001_contract.cpp)
target_include_directories(phos-lane-i-contract PUBLIC "${CMAKE_CURRENT_SOURCE_DIR}")
target_compile_features(phos-lane-i-contract PUBLIC cxx_std_20)

add_executable(phos-lane-i-i001
  i001_benchmark.cpp
  i001_runtime.cpp
  ${PROJECT_SOURCE_DIR}/src/vk_context.cpp
)
target_include_directories(phos-lane-i-i001 PRIVATE
  "${PROJECT_SOURCE_DIR}/src"
  "${CMAKE_CURRENT_SOURCE_DIR}"
)
target_link_libraries(phos-lane-i-i001 PRIVATE
  phos-lane-i-contract
  vk-bootstrap::vk-bootstrap
  ${CMAKE_DL_LIBS}
)
target_compile_features(phos-lane-i-i001 PRIVATE cxx_std_20)
target_compile_definitions(phos-lane-i-i001 PRIVATE
  PHOS_GI_LANE_I_SHADER_DIR="${CMAKE_BINARY_DIR}/shaders")
set_target_properties(phos-lane-i-i001 PROPERTIES
  CXX_EXTENSIONS OFF
  RUNTIME_OUTPUT_DIRECTORY "${CMAKE_BINARY_DIR}")

add_executable(phos-lane-i-contract-test i001_contract_test.cpp)
target_link_libraries(phos-lane-i-contract-test PRIVATE phos-lane-i-contract)
target_compile_features(phos-lane-i-contract-test PRIVATE cxx_std_20)
set_target_properties(phos-lane-i-contract-test PROPERTIES CXX_EXTENSIONS OFF)

if(MSVC)
  target_compile_options(phos-lane-i-contract PRIVATE /W4 /permissive-)
  target_compile_options(phos-lane-i-i001 PRIVATE /W4 /permissive-)
  target_compile_options(phos-lane-i-contract-test PRIVATE /W4 /permissive-)
else()
  target_compile_options(phos-lane-i-contract PRIVATE -Wall -Wextra -Wpedantic)
  target_compile_options(phos-lane-i-i001 PRIVATE -Wall -Wextra -Wpedantic)
  target_compile_options(phos-lane-i-contract-test PRIVATE -Wall -Wextra -Wpedantic)
endif()
