# N008 independent CPU HDR oracle. Opt-in from the top level (PHOS_BUILD_N008,
# default OFF) or configured standalone: cmake -S src/research/n008_hdr_oracle -B build/n008
cmake_minimum_required(VERSION 3.24)
if(CMAKE_SOURCE_DIR STREQUAL CMAKE_CURRENT_SOURCE_DIR)
  project(n008_hdr_oracle LANGUAGES CXX)
  if(NOT CMAKE_BUILD_TYPE)
    set(CMAKE_BUILD_TYPE Release)
  endif()
endif()
find_package(Threads REQUIRED)
foreach(target n008_oracle test_n008_oracle)
  if(target STREQUAL "n008_oracle")
    add_executable(${target} n008_oracle_main.cpp)
  else()
    add_executable(${target} test_n008_oracle.cpp)
  endif()
  target_compile_features(${target} PRIVATE cxx_std_20)
  target_link_libraries(${target} PRIVATE Threads::Threads)
  # No fast-math: IEEE double semantics are part of the oracle contract.
  if(CMAKE_CXX_COMPILER_ID MATCHES "GNU|Clang")
    target_compile_options(${target} PRIVATE -Wall -Wextra -fno-fast-math -ffp-contract=off)
  endif()
endforeach()

# CPU-only Renderer frame-state exporter (Phase B). Needs the top-level project's
# fastgltf and Vulkan headers (compile-time only; no Vulkan runtime is used).
if(TARGET fastgltf::fastgltf)
  find_package(Python3 REQUIRED COMPONENTS Interpreter)
  set(N008_N_SOURCE "${PROJECT_SOURCE_DIR}/src/research/lane_n_end_to_end_renderer")
  set(N008_GENERATED "${CMAKE_CURRENT_BINARY_DIR}/generated")
  set(N008_GENERATOR "${PROJECT_SOURCE_DIR}/scripts/research/n008_hdr_oracle/generate_state_exporter.py")
  add_custom_command(OUTPUT "${N008_GENERATED}/n008_state_extracted.hpp"
    COMMAND ${Python3_EXECUTABLE} "${N008_GENERATOR}" --root "${PROJECT_SOURCE_DIR}"
            --out "${N008_GENERATED}/n008_state_extracted.hpp"
    DEPENDS "${N008_GENERATOR}" "${N008_N_SOURCE}/n001_runtime.cpp" "${N008_N_SOURCE}/n002_runtime.cpp"
            "${N008_N_SOURCE}/imported/lane_a_split_rc/a001_runtime.cpp"
    VERBATIM)
  add_executable(n008_state_export
    n008_state_export_main.cpp "${N008_GENERATED}/n008_state_extracted.hpp"
    "${N008_N_SOURCE}/imported/lane_a_split_rc/a001_scene.cpp"
    "${N008_N_SOURCE}/imported/lane_b_traversal/b002_scene.cpp")
  target_include_directories(n008_state_export PRIVATE "${N008_GENERATED}" "${PROJECT_SOURCE_DIR}/src"
    "${N008_N_SOURCE}/imported/lane_a_split_rc" "${N008_N_SOURCE}/imported/lane_b_traversal"
    "${N008_N_SOURCE}/imported/integration")
  target_link_libraries(n008_state_export PRIVATE fastgltf::fastgltf vk-bootstrap::vk-bootstrap)
  target_compile_features(n008_state_export PRIVATE cxx_std_20)
endif()
