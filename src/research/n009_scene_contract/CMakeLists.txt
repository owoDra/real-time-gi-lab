# N009 scene contract C1 + back-face rule BF-P. Opt-in (PHOS_BUILD_N009, default
# OFF; requires PHOS_BUILD_N007 for the unchanged N007 capture shaders). The
# default build graph and every historical N001-N008 target are unchanged.
find_package(Python3 REQUIRED COMPONENTS Interpreter)
find_package(Threads REQUIRED)
set(N009_GENERATED "${CMAKE_CURRENT_BINARY_DIR}/generated")
set(N009_N_SOURCE "${PROJECT_SOURCE_DIR}/src/research/lane_n_end_to_end_renderer")
set(N009_SCRIPTS "${PROJECT_SOURCE_DIR}/scripts/research/n009_scene_contract")
add_custom_command(OUTPUT
  "${N009_GENERATED}/n009_a001_scene.cpp"
  "${N009_GENERATED}/n009_b002_scene.cpp"
  "${N009_GENERATED}/n009_a001_runtime.cpp"
  COMMAND ${Python3_EXECUTABLE} "${N009_SCRIPTS}/generate_overlay.py"
          --root "${PROJECT_SOURCE_DIR}" --out "${N009_GENERATED}"
  DEPENDS "${N009_SCRIPTS}/generate_overlay.py"
          "${N009_N_SOURCE}/imported/lane_a_split_rc/a001_scene.cpp"
          "${N009_N_SOURCE}/imported/lane_b_traversal/b002_scene.cpp"
          "${N009_N_SOURCE}/imported/lane_a_split_rc/a001_runtime.cpp"
  VERBATIM)
# The unchanged N007 capture overlay (packed direct/indirect/total, hit and probe
# payload export), regenerated here from the same pinned sources.
add_custom_command(OUTPUT "${N009_GENERATED}/n007/n007_runtime.cpp"
  COMMAND ${Python3_EXECUTABLE} "${PROJECT_SOURCE_DIR}/scripts/research/n007_reference_validity/generate_capture.py"
          --root "${PROJECT_SOURCE_DIR}" --out "${N009_GENERATED}/n007"
  DEPENDS "${PROJECT_SOURCE_DIR}/scripts/research/n007_reference_validity/generate_capture.py"
          "${N009_N_SOURCE}/n001_runtime.cpp"
  VERBATIM)
add_custom_command(OUTPUT "${N009_GENERATED}/n009_state_extracted.hpp"
  COMMAND ${Python3_EXECUTABLE} "${N009_SCRIPTS}/generate_state_exporter.py"
          --root "${PROJECT_SOURCE_DIR}" --a001-runtime "${N009_GENERATED}/n009_a001_runtime.cpp"
          --out "${N009_GENERATED}/n009_state_extracted.hpp"
  DEPENDS "${N009_SCRIPTS}/generate_state_exporter.py"
          "${PROJECT_SOURCE_DIR}/scripts/research/n008_hdr_oracle/generate_state_exporter.py"
          "${N009_GENERATED}/n009_a001_runtime.cpp" "${N009_N_SOURCE}/n001_runtime.cpp"
          "${N009_N_SOURCE}/n002_runtime.cpp"
  VERBATIM)

set(N009_INCLUDES
  "${CMAKE_CURRENT_SOURCE_DIR}" "${N009_GENERATED}" "${PROJECT_SOURCE_DIR}/src" "${N009_N_SOURCE}"
  "${N009_N_SOURCE}/imported/integration" "${N009_N_SOURCE}/imported/lane_a_split_rc"
  "${N009_N_SOURCE}/imported/lane_b_traversal" "${N009_N_SOURCE}/imported/lane_e_dynamic_geometry")

# CPU-only Renderer frame-state exporter (no Vulkan runtime).
add_executable(n009_state_export
  n009_state_export_main.cpp "${N009_GENERATED}/n009_state_extracted.hpp"
  "${N009_GENERATED}/n009_a001_scene.cpp" "${N009_GENERATED}/n009_b002_scene.cpp")
target_include_directories(n009_state_export PRIVATE ${N009_INCLUDES})
target_link_libraries(n009_state_export PRIVATE fastgltf::fastgltf vk-bootstrap::vk-bootstrap)
target_compile_features(n009_state_export PRIVATE cxx_std_20)

# GPU capture: N007 capture main + N007 runtime overlay, with the N009 loaders
# and A001 parameter wrapper replacing the pinned ones.
if(PHOS_BUILD_N007)
  add_executable(phos-n009-capture
    "${PROJECT_SOURCE_DIR}/src/research/n007_reference_validity/n007_capture_main.cpp"
    "${N009_GENERATED}/n007/n007_runtime.cpp"
    "${N009_N_SOURCE}/n001_reference.cpp"
    "${N009_N_SOURCE}/imported/integration/i001_compute.cpp"
    "${N009_GENERATED}/n009_a001_scene.cpp"
    "${N009_GENERATED}/n009_a001_runtime.cpp"
    "${N009_N_SOURCE}/imported/lane_a_split_rc/a001_analysis.cpp"
    "${N009_GENERATED}/n009_b002_scene.cpp"
    "${N009_N_SOURCE}/imported/lane_b_traversal/b002_vulkan.cpp"
    "${N009_N_SOURCE}/imported/lane_b_traversal/b002_compute.cpp"
    "${N009_N_SOURCE}/imported/lane_b_traversal/b002_hwrt.cpp"
    "${PROJECT_SOURCE_DIR}/src/vk_context.cpp")
  target_include_directories(phos-n009-capture PRIVATE ${N009_INCLUDES}
    "${PROJECT_SOURCE_DIR}/src/research/n007_reference_validity")
  target_link_libraries(phos-n009-capture PRIVATE
    vk-bootstrap::vk-bootstrap fastgltf::fastgltf Threads::Threads ${CMAKE_DL_LIBS})
  target_compile_features(phos-n009-capture PRIVATE cxx_std_20)
  target_compile_definitions(phos-n009-capture PRIVATE
    PHOS_GI_N006_SOFTWARE_PRIMARY=1
    PHOS_GI_LANE_A_SHADER_DIR="${PROJECT_BINARY_DIR}/shaders"
    PHOS_GI_LANE_B_SHADER_DIR="${PROJECT_BINARY_DIR}/shaders"
    PHOS_GI_INTEGRATION_SHADER_DIR="${PROJECT_BINARY_DIR}/shaders")
  set_target_properties(phos-n009-capture PROPERTIES RUNTIME_OUTPUT_DIRECTORY "${PROJECT_BINARY_DIR}")
  add_dependencies(phos-n009-capture phos-n007-shaders phos-n001-shaders phos-n003-comparison-shaders)
endif()

# CPU-only probe-transport counterfactual ladder (WP-PT); uses the N008 oracle header.
add_executable(n009_probe_model n009_probe_model.cpp)
target_include_directories(n009_probe_model PRIVATE "${PROJECT_SOURCE_DIR}/src/research/n008_hdr_oracle")
target_link_libraries(n009_probe_model PRIVATE Threads::Threads)
target_compile_features(n009_probe_model PRIVATE cxx_std_20)
if(CMAKE_CXX_COMPILER_ID MATCHES "GNU|Clang")
  target_compile_options(n009_probe_model PRIVATE -Wall -Wextra -fno-fast-math -ffp-contract=off)
endif()
