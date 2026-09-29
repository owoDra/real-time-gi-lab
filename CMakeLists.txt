cmake_minimum_required(VERSION 3.27)
project(phos_gi_lab LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

include(FetchContent)

# Keep build-time Vulkan dependencies self-contained. The host still needs a
# working Vulkan loader/driver at runtime, but not a Vulkan SDK installation.
set(VK_BOOTSTRAP_TEST OFF CACHE BOOL "" FORCE)
set(VK_BOOTSTRAP_INSTALL OFF CACHE BOOL "" FORCE)
set(VK_BOOTSTRAP_FORCE_FETCH_CONTENT ON CACHE BOOL "" FORCE)
FetchContent_Declare(
  vk_bootstrap
  GIT_REPOSITORY https://github.com/charles-lunarg/vk-bootstrap.git
  GIT_TAG 7f25c47
)
FetchContent_MakeAvailable(vk_bootstrap)

set(FASTGLTF_ENABLE_TESTS OFF CACHE BOOL "" FORCE)
set(FASTGLTF_ENABLE_EXAMPLES OFF CACHE BOOL "" FORCE)
set(FASTGLTF_COMPILE_AS_CPP20 ON CACHE BOOL "" FORCE)
FetchContent_Declare(
  fastgltf
  GIT_REPOSITORY https://github.com/spnda/fastgltf.git
  GIT_TAG v0.9.0
)
FetchContent_MakeAvailable(fastgltf)

add_executable(phos-gi-lab
  src/main.cpp
  src/vk_context.cpp
  src/scene_workload.cpp
  src/cache_benchmark.cpp
)

target_include_directories(phos-gi-lab PRIVATE src)
target_link_libraries(phos-gi-lab PRIVATE vk-bootstrap::vk-bootstrap fastgltf::fastgltf ${CMAKE_DL_LIBS})
set_target_properties(phos-gi-lab PROPERTIES
  CXX_STANDARD 20
  CXX_STANDARD_REQUIRED ON
  CXX_EXTENSIONS OFF
)

target_compile_definitions(phos-gi-lab PRIVATE PHOS_GI_LAB_SHADER_DIR="${CMAKE_BINARY_DIR}/shaders")

if(MSVC)
  target_compile_options(phos-gi-lab PRIVATE /W4 /permissive-)
else()
  target_compile_options(phos-gi-lab PRIVATE -Wall -Wextra -Wpedantic)
endif()

# Prefer an already-installed shader compiler, but do not require the Vulkan SDK.
find_program(GLSLC glslc HINTS "$ENV{VULKAN_SDK}/Bin" "$ENV{VULKAN_SDK}/bin")
find_program(GLSLANG_VALIDATOR glslangValidator HINTS "$ENV{VULKAN_SDK}/Bin" "$ENV{VULKAN_SDK}/bin")

if(NOT GLSLC AND NOT GLSLANG_VALIDATOR)
  message(STATUS "No system GLSL compiler found; building bundled glslang 16.6.0")
  set(GLSLANG_TESTS OFF CACHE BOOL "" FORCE)
  set(GLSLANG_ENABLE_INSTALL OFF CACHE BOOL "" FORCE)
  set(ENABLE_GLSLANG_BINARIES ON CACHE BOOL "" FORCE)
  set(ENABLE_HLSL OFF CACHE BOOL "" FORCE)
  set(ENABLE_OPT OFF CACHE BOOL "" FORCE)
  FetchContent_Declare(
    glslang
    GIT_REPOSITORY https://github.com/KhronosGroup/glslang.git
    GIT_TAG 16.6.0
  )
  FetchContent_MakeAvailable(glslang)

  # glslang 16.6.0 triggers GCC -Wmaybe-uninitialized warnings in its own
  # parser sources. Keep our warnings enabled, but do not let vendored code
  # drown out project diagnostics.
  if(CMAKE_CXX_COMPILER_ID STREQUAL "GNU" AND TARGET glslang)
    target_compile_options(glslang PRIVATE -Wno-maybe-uninitialized)
  endif()
endif()

function(add_compute_shader NAME SOURCE)
  set(OUTPUT "${CMAKE_BINARY_DIR}/shaders/${NAME}.spv")
  if(GLSLC)
    add_custom_command(
      OUTPUT "${OUTPUT}"
      COMMAND ${CMAKE_COMMAND} -E make_directory "${CMAKE_BINARY_DIR}/shaders"
      COMMAND ${GLSLC} --target-env=vulkan1.3 -O "${CMAKE_SOURCE_DIR}/${SOURCE}" -o "${OUTPUT}"
      DEPENDS "${CMAKE_SOURCE_DIR}/${SOURCE}"
      VERBATIM)
  elseif(GLSLANG_VALIDATOR)
    add_custom_command(
      OUTPUT "${OUTPUT}"
      COMMAND ${CMAKE_COMMAND} -E make_directory "${CMAKE_BINARY_DIR}/shaders"
      COMMAND ${GLSLANG_VALIDATOR} -V --target-env vulkan1.3 -S comp "${CMAKE_SOURCE_DIR}/${SOURCE}" -o "${OUTPUT}"
      DEPENDS "${CMAKE_SOURCE_DIR}/${SOURCE}"
      VERBATIM)
  elseif(TARGET glslang-standalone)
    add_custom_command(
      OUTPUT "${OUTPUT}"
      COMMAND ${CMAKE_COMMAND} -E make_directory "${CMAKE_BINARY_DIR}/shaders"
      COMMAND $<TARGET_FILE:glslang-standalone> -V --target-env vulkan1.3 -S comp "${CMAKE_SOURCE_DIR}/${SOURCE}" -o "${OUTPUT}"
      DEPENDS glslang-standalone "${CMAKE_SOURCE_DIR}/${SOURCE}"
      VERBATIM)
  else()
    message(FATAL_ERROR "No GLSL compiler is available")
  endif()
  set_property(GLOBAL APPEND PROPERTY PHOS_GI_SHADER_OUTPUTS "${OUTPUT}")
endfunction()

add_compute_shader(hash_lookup shaders/hash_lookup.comp.glsl)
add_compute_shader(hash_lookup_wg_bin16 shaders/hash_lookup_wg_bin16.comp.glsl)
add_compute_shader(paged_lookup shaders/paged_lookup.comp.glsl)
add_compute_shader(page_histogram shaders/page_histogram.comp.glsl)
add_compute_shader(page_prefix shaders/page_prefix.comp.glsl)
add_compute_shader(page_scatter shaders/page_scatter.comp.glsl)

# Research lanes own disjoint subtrees so parallel branches can integrate with
# minimal conflicts. Lane-specific targets/shaders are registered only from
# their own CMakeLists.txt.
add_subdirectory(src/research/lane_a_split_rc)
add_subdirectory(src/research/lane_b_traversal)
add_subdirectory(src/research/lane_c_storage_locality)
add_subdirectory(src/research/integration)
add_subdirectory(src/research/lane_f_dynamic_geometry_alternatives)

get_property(SHADER_OUTPUTS GLOBAL PROPERTY PHOS_GI_SHADER_OUTPUTS)
add_custom_target(phos-gi-shaders ALL DEPENDS ${SHADER_OUTPUTS})
add_dependencies(phos-gi-lab phos-gi-shaders)
