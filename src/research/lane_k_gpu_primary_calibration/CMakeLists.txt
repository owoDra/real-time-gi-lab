# Issue #21 Lane K owns this directory.
add_compute_shader(
  lane_k_calibration
  shaders/research/lane_k_gpu_primary_calibration/k001_calibration.comp.glsl)
add_custom_target(phos-lane-k-shaders
  DEPENDS "${CMAKE_BINARY_DIR}/shaders/lane_k_calibration.spv")

add_library(phos-lane-k-contract STATIC k001_contract.cpp)
target_include_directories(phos-lane-k-contract PUBLIC "${CMAKE_CURRENT_SOURCE_DIR}")
target_compile_features(phos-lane-k-contract PUBLIC cxx_std_20)

add_executable(phos-lane-k-k001
  k001_benchmark.cpp
  k001_runtime.cpp
  ${PROJECT_SOURCE_DIR}/src/vk_context.cpp
)
target_include_directories(phos-lane-k-k001 PRIVATE
  "${PROJECT_SOURCE_DIR}/src"
  "${CMAKE_CURRENT_SOURCE_DIR}"
)
target_link_libraries(phos-lane-k-k001 PRIVATE
  phos-lane-k-contract
  vk-bootstrap::vk-bootstrap
  ${CMAKE_DL_LIBS}
)
target_compile_features(phos-lane-k-k001 PRIVATE cxx_std_20)
target_compile_definitions(phos-lane-k-k001 PRIVATE
  PHOS_GI_LANE_K_SHADER_DIR="${CMAKE_BINARY_DIR}/shaders")
set_target_properties(phos-lane-k-k001 PROPERTIES
  CXX_EXTENSIONS OFF
  RUNTIME_OUTPUT_DIRECTORY "${CMAKE_BINARY_DIR}")
add_dependencies(phos-lane-k-k001 phos-lane-k-shaders)

add_executable(phos-lane-k-contract-test k001_contract_test.cpp)
target_link_libraries(phos-lane-k-contract-test PRIVATE phos-lane-k-contract)
target_compile_features(phos-lane-k-contract-test PRIVATE cxx_std_20)
set_target_properties(phos-lane-k-contract-test PROPERTIES
  CXX_EXTENSIONS OFF
  RUNTIME_OUTPUT_DIRECTORY "${CMAKE_BINARY_DIR}")

if(MSVC)
  target_compile_options(phos-lane-k-contract PRIVATE /W4 /permissive-)
  target_compile_options(phos-lane-k-k001 PRIVATE /W4 /permissive-)
  target_compile_options(phos-lane-k-contract-test PRIVATE /W4 /permissive-)
else()
  target_compile_options(phos-lane-k-contract PRIVATE -Wall -Wextra -Wpedantic)
  target_compile_options(phos-lane-k-k001 PRIVATE -Wall -Wextra -Wpedantic)
  target_compile_options(phos-lane-k-contract-test PRIVATE -Wall -Wextra -Wpedantic)
endif()
