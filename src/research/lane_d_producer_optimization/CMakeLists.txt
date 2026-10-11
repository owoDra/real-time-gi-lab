# Lane D owns this directory. Keep accepted Lane A files unchanged; this target
# links the accepted A001 runtime/reference read-only for same-process controls.

add_compute_shader(
  lane_d_d001_producer_owner_reuse
  shaders/research/lane_d_producer_optimization/d001_producer_owner_reuse.comp.glsl
)
add_compute_shader(
  lane_d_d002_producer_visible_tile
  shaders/research/lane_d_producer_optimization/d002_producer_visible_tile.comp.glsl
)
add_compute_shader(
  lane_d_d003_visibility_packed
  shaders/research/lane_d_producer_optimization/d003_visibility_packed.comp.glsl
)
add_compute_shader(
  lane_d_d003_producer_packed_owner
  shaders/research/lane_d_producer_optimization/d003_producer_packed_owner.comp.glsl
)
add_compute_shader(
  lane_d_d004_producer_workgroup_alloc
  shaders/research/lane_d_producer_optimization/d004_producer_workgroup_alloc.comp.glsl
)
add_compute_shader(
  lane_d_d005_producer_owner_slot
  shaders/research/lane_d_producer_optimization/d005_producer_owner_slot.comp.glsl
)
add_compute_shader(
  lane_d_d005_finalize_bounded
  shaders/research/lane_d_producer_optimization/d005_finalize_bounded.comp.glsl
)

set(LANE_D_SHADER_OUTPUTS
  "${CMAKE_BINARY_DIR}/shaders/lane_d_d001_producer_owner_reuse.spv"
  "${CMAKE_BINARY_DIR}/shaders/lane_d_d002_producer_visible_tile.spv"
  "${CMAKE_BINARY_DIR}/shaders/lane_d_d003_visibility_packed.spv"
  "${CMAKE_BINARY_DIR}/shaders/lane_d_d003_producer_packed_owner.spv"
  "${CMAKE_BINARY_DIR}/shaders/lane_d_d004_producer_workgroup_alloc.spv"
  "${CMAKE_BINARY_DIR}/shaders/lane_d_d005_producer_owner_slot.spv"
  "${CMAKE_BINARY_DIR}/shaders/lane_d_d005_finalize_bounded.spv"
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


add_executable(phos-lane-d-d002
  d002_benchmark.cpp
  d001_runtime.cpp
  ${PROJECT_SOURCE_DIR}/src/research/lane_a_split_rc/a001_scene.cpp
  ${PROJECT_SOURCE_DIR}/src/research/lane_a_split_rc/a001_runtime.cpp
  ${PROJECT_SOURCE_DIR}/src/research/lane_a_split_rc/a001_analysis.cpp
  ${PROJECT_SOURCE_DIR}/src/vk_context.cpp
)
add_dependencies(
  phos-lane-d-d002
  phos-lane-a-split-rc-shaders
  phos-lane-d-producer-optimization-shaders
)
target_include_directories(phos-lane-d-d002 PRIVATE
  ${PROJECT_SOURCE_DIR}/src
  ${PROJECT_SOURCE_DIR}/src/research/lane_a_split_rc
  ${CMAKE_CURRENT_SOURCE_DIR}
)
target_link_libraries(phos-lane-d-d002 PRIVATE
  vk-bootstrap::vk-bootstrap
  fastgltf::fastgltf
  ${CMAKE_DL_LIBS}
)
target_compile_definitions(phos-lane-d-d002 PRIVATE
  PHOS_GI_LANE_A_SHADER_DIR="${CMAKE_BINARY_DIR}/shaders"
  PHOS_GI_LANE_D_SHADER_DIR="${CMAKE_BINARY_DIR}/shaders"
)
set_target_properties(phos-lane-d-d002 PROPERTIES
  CXX_STANDARD 20
  CXX_STANDARD_REQUIRED ON
  CXX_EXTENSIONS OFF
)
if(MSVC)
  target_compile_options(phos-lane-d-d002 PRIVATE /W4 /permissive-)
else()
  target_compile_options(phos-lane-d-d002 PRIVATE -Wall -Wextra -Wpedantic)
endif()


add_executable(phos-lane-d-d003
  d003_benchmark.cpp
  d003_runtime.cpp
  d001_runtime.cpp
  ${PROJECT_SOURCE_DIR}/src/research/lane_a_split_rc/a001_scene.cpp
  ${PROJECT_SOURCE_DIR}/src/research/lane_a_split_rc/a001_runtime.cpp
  ${PROJECT_SOURCE_DIR}/src/research/lane_a_split_rc/a001_analysis.cpp
  ${PROJECT_SOURCE_DIR}/src/vk_context.cpp
)
add_dependencies(
  phos-lane-d-d003
  phos-lane-a-split-rc-shaders
  phos-lane-d-producer-optimization-shaders
)
target_include_directories(phos-lane-d-d003 PRIVATE
  ${PROJECT_SOURCE_DIR}/src
  ${PROJECT_SOURCE_DIR}/src/research/lane_a_split_rc
  ${CMAKE_CURRENT_SOURCE_DIR}
)
target_link_libraries(phos-lane-d-d003 PRIVATE
  vk-bootstrap::vk-bootstrap
  fastgltf::fastgltf
  ${CMAKE_DL_LIBS}
)
target_compile_definitions(phos-lane-d-d003 PRIVATE
  PHOS_GI_LANE_A_SHADER_DIR="${CMAKE_BINARY_DIR}/shaders"
  PHOS_GI_LANE_D_SHADER_DIR="${CMAKE_BINARY_DIR}/shaders"
)
set_target_properties(phos-lane-d-d003 PROPERTIES
  CXX_STANDARD 20
  CXX_STANDARD_REQUIRED ON
  CXX_EXTENSIONS OFF
)
if(MSVC)
  target_compile_options(phos-lane-d-d003 PRIVATE /W4 /permissive-)
else()
  target_compile_options(phos-lane-d-d003 PRIVATE -Wall -Wextra -Wpedantic)
endif()


add_executable(phos-lane-d-d004
  d004_benchmark.cpp
  d001_runtime.cpp
  ${PROJECT_SOURCE_DIR}/src/research/lane_a_split_rc/a001_scene.cpp
  ${PROJECT_SOURCE_DIR}/src/research/lane_a_split_rc/a001_runtime.cpp
  ${PROJECT_SOURCE_DIR}/src/research/lane_a_split_rc/a001_analysis.cpp
  ${PROJECT_SOURCE_DIR}/src/vk_context.cpp
)
add_dependencies(
  phos-lane-d-d004
  phos-lane-a-split-rc-shaders
  phos-lane-d-producer-optimization-shaders
)
target_include_directories(phos-lane-d-d004 PRIVATE
  ${PROJECT_SOURCE_DIR}/src
  ${PROJECT_SOURCE_DIR}/src/research/lane_a_split_rc
  ${CMAKE_CURRENT_SOURCE_DIR}
)
target_link_libraries(phos-lane-d-d004 PRIVATE
  vk-bootstrap::vk-bootstrap
  fastgltf::fastgltf
  ${CMAKE_DL_LIBS}
)
target_compile_definitions(phos-lane-d-d004 PRIVATE
  PHOS_GI_LANE_A_SHADER_DIR="${CMAKE_BINARY_DIR}/shaders"
  PHOS_GI_LANE_D_SHADER_DIR="${CMAKE_BINARY_DIR}/shaders"
)
set_target_properties(phos-lane-d-d004 PROPERTIES
  CXX_STANDARD 20
  CXX_STANDARD_REQUIRED ON
  CXX_EXTENSIONS OFF
)
if(MSVC)
  target_compile_options(phos-lane-d-d004 PRIVATE /W4 /permissive-)
else()
  target_compile_options(phos-lane-d-d004 PRIVATE -Wall -Wextra -Wpedantic)
endif()


add_executable(phos-lane-d-d005
  d005_benchmark.cpp
  d001_runtime.cpp
  ${PROJECT_SOURCE_DIR}/src/research/lane_a_split_rc/a001_scene.cpp
  ${PROJECT_SOURCE_DIR}/src/research/lane_a_split_rc/a001_runtime.cpp
  ${PROJECT_SOURCE_DIR}/src/research/lane_a_split_rc/a001_analysis.cpp
  ${PROJECT_SOURCE_DIR}/src/vk_context.cpp
)
add_dependencies(
  phos-lane-d-d005
  phos-lane-a-split-rc-shaders
  phos-lane-d-producer-optimization-shaders
)
target_include_directories(phos-lane-d-d005 PRIVATE
  ${PROJECT_SOURCE_DIR}/src
  ${PROJECT_SOURCE_DIR}/src/research/lane_a_split_rc
  ${CMAKE_CURRENT_SOURCE_DIR}
)
target_link_libraries(phos-lane-d-d005 PRIVATE
  vk-bootstrap::vk-bootstrap
  fastgltf::fastgltf
  ${CMAKE_DL_LIBS}
)
target_compile_definitions(phos-lane-d-d005 PRIVATE
  PHOS_GI_LANE_A_SHADER_DIR="${CMAKE_BINARY_DIR}/shaders"
  PHOS_GI_LANE_D_SHADER_DIR="${CMAKE_BINARY_DIR}/shaders"
)
set_target_properties(phos-lane-d-d005 PROPERTIES
  CXX_STANDARD 20
  CXX_STANDARD_REQUIRED ON
  CXX_EXTENSIONS OFF
)
if(MSVC)
  target_compile_options(phos-lane-d-d005 PRIVATE /W4 /permissive-)
else()
  target_compile_options(phos-lane-d-d005 PRIVATE -Wall -Wextra -Wpedantic)
endif()
