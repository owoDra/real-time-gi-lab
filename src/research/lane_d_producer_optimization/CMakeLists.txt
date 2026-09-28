# Lane D owns this directory. Keep accepted Lane A files unchanged; this target
# links the accepted A001 runtime/reference read-only for same-process controls.

add_compute_shader(
  lane_d_d001_producer_owner_reuse
  shaders/research/lane_d_producer_optimization/d001_producer_owner_reuse.comp.glsl
)

set(LANE_D_SHADER_OUTPUTS
  "${CMAKE_BINARY_DIR}/shaders/lane_d_d001_producer_owner_reuse.spv"
)
add_custom_target(
  phos-lane-d-producer-optimization-shaders
  DEPENDS ${LANE_D_SHADER_OUTPUTS}
)

add_executable(phos-lane-d-producer-optimization
  d001_benchmark.cpp
  d001_runtime.cpp
  ${PROJECT_SOURCE_DIR}/src/research/lane_a_split_rc/a001_scene.cpp
  ${PROJECT_SOURCE_DIR}/src/research/lane_a_split_rc/a001_runtime.cpp
  ${PROJECT_SOURCE_DIR}/src/research/lane_a_split_rc/a001_analysis.cpp
  ${PROJECT_SOURCE_DIR}/src/vk_context.cpp
)

add_dependencies(
  phos-lane-d-producer-optimization
  phos-lane-a-split-rc-shaders
  phos-lane-d-producer-optimization-shaders
)

target_include_directories(phos-lane-d-producer-optimization PRIVATE
  ${PROJECT_SOURCE_DIR}/src
  ${PROJECT_SOURCE_DIR}/src/research/lane_a_split_rc
  ${CMAKE_CURRENT_SOURCE_DIR}
)

target_link_libraries(phos-lane-d-producer-optimization PRIVATE
  vk-bootstrap::vk-bootstrap
  fastgltf::fastgltf
  ${CMAKE_DL_LIBS}
)

target_compile_definitions(phos-lane-d-producer-optimization PRIVATE
  PHOS_GI_LANE_A_SHADER_DIR="${CMAKE_BINARY_DIR}/shaders"
  PHOS_GI_LANE_D_SHADER_DIR="${CMAKE_BINARY_DIR}/shaders"
)

set_target_properties(phos-lane-d-producer-optimization PROPERTIES
  CXX_STANDARD 20
  CXX_STANDARD_REQUIRED ON
  CXX_EXTENSIONS OFF
)

if(MSVC)
  target_compile_options(
    phos-lane-d-producer-optimization
    PRIVATE /W4 /permissive-
  )
else()
  target_compile_options(
    phos-lane-d-producer-optimization
    PRIVATE -Wall -Wextra -Wpedantic
  )
endif()
