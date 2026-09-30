# Lane A owns this directory. Register Split RC research sources/shaders here.
# Keep lane-specific build changes out of the repository root CMakeLists.txt.

add_compute_shader(lane_a_visibility_depth shaders/research/lane_a_split_rc/visibility_depth.comp.glsl)
add_compute_shader(lane_a_visibility_owner shaders/research/lane_a_split_rc/visibility_owner.comp.glsl)
add_compute_shader(lane_a_producer shaders/research/lane_a_split_rc/producer.comp.glsl)
add_compute_shader(lane_a_finalize shaders/research/lane_a_split_rc/finalize.comp.glsl)
add_compute_shader(lane_a_gather shaders/research/lane_a_split_rc/gather.comp.glsl)
add_compute_shader(lane_a_merge shaders/research/lane_a_split_rc/merge.comp.glsl)
add_compute_shader(lane_a_resolve shaders/research/lane_a_split_rc/resolve.comp.glsl)

set(LANE_A_SHADER_OUTPUTS
  "${CMAKE_BINARY_DIR}/shaders/lane_a_visibility_depth.spv"
  "${CMAKE_BINARY_DIR}/shaders/lane_a_visibility_owner.spv"
  "${CMAKE_BINARY_DIR}/shaders/lane_a_producer.spv"
  "${CMAKE_BINARY_DIR}/shaders/lane_a_finalize.spv"
  "${CMAKE_BINARY_DIR}/shaders/lane_a_gather.spv"
  "${CMAKE_BINARY_DIR}/shaders/lane_a_merge.spv"
  "${CMAKE_BINARY_DIR}/shaders/lane_a_resolve.spv"
)
add_custom_target(phos-lane-a-split-rc-shaders DEPENDS ${LANE_A_SHADER_OUTPUTS})

add_executable(phos-lane-a-split-rc
  producer_benchmark.cpp
  a001_scene.cpp
  a001_runtime.cpp
  a001_analysis.cpp
  ${PROJECT_SOURCE_DIR}/src/vk_context.cpp
)
add_dependencies(phos-lane-a-split-rc phos-lane-a-split-rc-shaders)

target_include_directories(phos-lane-a-split-rc PRIVATE
  ${PROJECT_SOURCE_DIR}/src
  ${CMAKE_CURRENT_SOURCE_DIR}
)
target_link_libraries(phos-lane-a-split-rc PRIVATE
  vk-bootstrap::vk-bootstrap
  fastgltf::fastgltf
  ${CMAKE_DL_LIBS}
)
target_compile_definitions(phos-lane-a-split-rc PRIVATE
  PHOS_GI_LANE_A_SHADER_DIR="${CMAKE_BINARY_DIR}/shaders"
)
set_target_properties(phos-lane-a-split-rc PROPERTIES
  CXX_STANDARD 20
  CXX_STANDARD_REQUIRED ON
  CXX_EXTENSIONS OFF
)

if(MSVC)
  target_compile_options(phos-lane-a-split-rc PRIVATE /W4 /permissive-)
else()
  target_compile_options(phos-lane-a-split-rc PRIVATE -Wall -Wextra -Wpedantic)
endif()
