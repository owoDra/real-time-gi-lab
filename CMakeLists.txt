cmake_minimum_required(VERSION 3.27)
project(phos_gi_lab LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

include(FetchContent)

set(VK_BOOTSTRAP_TEST OFF CACHE BOOL "" FORCE)
set(VK_BOOTSTRAP_INSTALL OFF CACHE BOOL "" FORCE)
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

target_compile_definitions(phos-gi-lab PRIVATE PHOS_GI_LAB_SHADER_DIR="${CMAKE_BINARY_DIR}/shaders")

if(MSVC)
  target_compile_options(phos-gi-lab PRIVATE /W4 /permissive-)
else()
  target_compile_options(phos-gi-lab PRIVATE -Wall -Wextra -Wpedantic)
endif()

find_program(GLSLC glslc HINTS "$ENV{VULKAN_SDK}/Bin" "$ENV{VULKAN_SDK}/bin")
find_program(GLSLANG_VALIDATOR glslangValidator HINTS "$ENV{VULKAN_SDK}/Bin" "$ENV{VULKAN_SDK}/bin")

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
  else()
    message(FATAL_ERROR "glslc or glslangValidator is required. Install the Vulkan SDK or glslang.")
  endif()
  set_property(GLOBAL APPEND PROPERTY PHOS_GI_SHADER_OUTPUTS "${OUTPUT}")
endfunction()

add_compute_shader(hash_lookup shaders/hash_lookup.comp.glsl)
add_compute_shader(paged_lookup shaders/paged_lookup.comp.glsl)
get_property(SHADER_OUTPUTS GLOBAL PROPERTY PHOS_GI_SHADER_OUTPUTS)
add_custom_target(phos-gi-shaders ALL DEPENDS ${SHADER_OUTPUTS})
add_dependencies(phos-gi-lab phos-gi-shaders)
