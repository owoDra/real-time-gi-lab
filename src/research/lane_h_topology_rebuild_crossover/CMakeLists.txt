# Issue #18 Lane H owns this directory.
# H001 reuses the Lane G runtime read-only so architecture remains unchanged while
# the measurement harness changes. Lane E/G source-of-truth is not modified.

set(LANE_G_DIR "${PROJECT_SOURCE_DIR}/src/research/lane_g_transient_lbvh_hardening")

add_executable(phos-lane-h-h001
  h001_benchmark.cpp
  ${LANE_G_DIR}/i001_runtime.cpp
  ${LANE_G_DIR}/g003_immutable_hwrt.cpp
  ${LANE_G_DIR}/i001_compute.cpp
  ${LANE_G_DIR}/f003_transient_lbvh.cpp
  ${LANE_G_DIR}/f005_transient_grid.cpp
  ${LANE_G_DIR}/baseline/lane_a_split_rc/a001_scene.cpp
  ${LANE_G_DIR}/baseline/lane_a_split_rc/a001_runtime.cpp
  ${LANE_G_DIR}/baseline/lane_a_split_rc/a001_analysis.cpp
  ${LANE_G_DIR}/baseline/lane_b_traversal/b002_scene.cpp
  ${LANE_G_DIR}/baseline/lane_b_traversal/b002_vulkan.cpp
  ${LANE_G_DIR}/baseline/lane_b_traversal/b002_compute.cpp
  ${LANE_G_DIR}/baseline/lane_b_traversal/b002_hwrt.cpp
  ${PROJECT_SOURCE_DIR}/src/vk_context.cpp
)

target_include_directories(phos-lane-h-h001 PRIVATE
  "${CMAKE_SOURCE_DIR}/src"
  "${LANE_G_DIR}"
  "${LANE_G_DIR}/baseline/lane_a_split_rc"
  "${LANE_G_DIR}/baseline/lane_b_traversal"
)

target_link_libraries(phos-lane-h-h001 PRIVATE
  vk-bootstrap::vk-bootstrap
  fastgltf::fastgltf
  ${CMAKE_DL_LIBS}
)

target_compile_features(phos-lane-h-h001 PRIVATE cxx_std_20)
target_compile_definitions(phos-lane-h-h001 PRIVATE
  PHOS_GI_LANE_A_SHADER_DIR="${CMAKE_BINARY_DIR}/shaders"
  PHOS_GI_LANE_B_SHADER_DIR="${CMAKE_BINARY_DIR}/shaders"
  PHOS_GI_INTEGRATION_SHADER_DIR="${CMAKE_BINARY_DIR}/shaders"
  PHOS_GI_LANE_F_SHADER_DIR="${CMAKE_BINARY_DIR}/shaders"
)
set_target_properties(phos-lane-h-h001 PROPERTIES
  CXX_EXTENSIONS OFF
  RUNTIME_OUTPUT_DIRECTORY "${CMAKE_BINARY_DIR}"
)

# H001 intentionally consumes the exact shader set compiled by the unchanged
# Lane G runtime rather than forking shader source before the methodology gate.
add_dependencies(phos-lane-h-h001 phos-lane-g-g001-shaders)

if(MSVC)
  target_compile_options(phos-lane-h-h001 PRIVATE /W4 /permissive-)
else()
  target_compile_options(phos-lane-h-h001 PRIVATE -Wall -Wextra -Wpedantic)
endif()
