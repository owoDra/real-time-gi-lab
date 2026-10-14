# Opt-in only. Reuse pinned N009 C1/BF-P loaders; historical targets unchanged.
find_package(Python3 REQUIRED COMPONENTS Interpreter)
find_package(Threads REQUIRED)
set(N010_N "${PROJECT_SOURCE_DIR}/src/research/lane_n_end_to_end_renderer")
set(N010_C1 "${PROJECT_BINARY_DIR}/src/research/n009_scene_contract/generated")
set(N010_GENERATED "${CMAKE_CURRENT_BINARY_DIR}/generated")
set(N010_SCRIPT "${PROJECT_SOURCE_DIR}/scripts/research/n010_comparison_readiness/generate_capture.py")
add_custom_command(OUTPUT
  "${N010_GENERATED}/n010_capture_main.cpp"
  "${N010_GENERATED}/n010_runtime.cpp"
  "${N010_GENERATED}/n010_hwrt_composite.comp.glsl"
  "${N010_GENERATED}/n010_software_composite.comp.glsl"
  COMMAND ${Python3_EXECUTABLE} "${N010_SCRIPT}" --root "${PROJECT_SOURCE_DIR}" --out "${N010_GENERATED}"
  DEPENDS "${N010_SCRIPT}" "${PROJECT_SOURCE_DIR}/scripts/research/n007_reference_validity/generate_capture.py"
    "${PROJECT_SOURCE_DIR}/src/research/n007_reference_validity/n007_capture_main.cpp"
    "${N010_N}/n001_runtime.cpp"
    "${PROJECT_SOURCE_DIR}/shaders/research/lane_n_end_to_end_renderer/n001_composite.comp.glsl"
    "${PROJECT_SOURCE_DIR}/shaders/research/lane_n_end_to_end_renderer/n003_composite_software.comp.glsl"
  VERBATIM)
foreach(kind hwrt software)
  set(shader "${N010_GENERATED}/n010_${kind}_composite.comp.glsl")
  set(spirv "${PROJECT_BINARY_DIR}/shaders/n010_${kind}_composite.spv")
  if(GLSLC)
    add_custom_command(OUTPUT "${spirv}"
      COMMAND "${GLSLC}" --target-env=vulkan1.3 -O "${shader}" -o "${spirv}"
      DEPENDS "${shader}" VERBATIM)
  elseif(GLSLANG_VALIDATOR)
    add_custom_command(OUTPUT "${spirv}"
      COMMAND "${GLSLANG_VALIDATOR}" -V --target-env vulkan1.3 -S comp "${shader}" -o "${spirv}"
      DEPENDS "${shader}" VERBATIM)
  elseif(TARGET glslang-standalone)
    add_custom_command(OUTPUT "${spirv}"
      COMMAND $<TARGET_FILE:glslang-standalone> -V --target-env vulkan1.3 -S comp "${shader}" -o "${spirv}"
      DEPENDS glslang-standalone "${shader}" VERBATIM)
  else()
    message(FATAL_ERROR "N010 requires GLSL compiler")
  endif()
  list(APPEND N010_SPIRV "${spirv}")
endforeach()
add_custom_target(phos-n010-shaders DEPENDS ${N010_SPIRV})
add_custom_command(OUTPUT
  "${N010_GENERATED}/n010_b002_vulkan.cpp" "${N010_GENERATED}/n010_vk_context.cpp"
  COMMAND ${Python3_EXECUTABLE} "${PROJECT_SOURCE_DIR}/scripts/research/n010_comparison_readiness/generate_memory_hooks.py"
    --root "${PROJECT_SOURCE_DIR}" --out "${N010_GENERATED}"
  DEPENDS "${PROJECT_SOURCE_DIR}/scripts/research/n010_comparison_readiness/generate_memory_hooks.py"
    "${N010_SCRIPT}" "${N010_N}/imported/lane_b_traversal/b002_vulkan.cpp" "${PROJECT_SOURCE_DIR}/src/vk_context.cpp"
  VERBATIM)
add_executable(phos-n010-capture
  "${N010_GENERATED}/n010_capture_main.cpp"
  "${N010_GENERATED}/n010_runtime.cpp"
  "${N010_N}/n001_reference.cpp"
  "${N010_N}/imported/integration/i001_compute.cpp"
  "${N010_C1}/n009_a001_scene.cpp" "${N010_C1}/n009_a001_runtime.cpp"
  "${N010_C1}/n009_b002_scene.cpp"
  "${N010_N}/imported/lane_a_split_rc/a001_analysis.cpp"
  "${N010_GENERATED}/n010_b002_vulkan.cpp"
  "${N010_N}/imported/lane_b_traversal/b002_compute.cpp"
  "${N010_N}/imported/lane_b_traversal/b002_hwrt.cpp"
  "${N010_GENERATED}/n010_vk_context.cpp")
set_source_files_properties(
  "${N010_C1}/n009_a001_scene.cpp" "${N010_C1}/n009_a001_runtime.cpp"
  "${N010_C1}/n009_b002_scene.cpp" PROPERTIES GENERATED TRUE)
target_include_directories(phos-n010-capture PRIVATE
  "${CMAKE_CURRENT_SOURCE_DIR}" "${PROJECT_SOURCE_DIR}/src" "${N010_N}"
  "${PROJECT_SOURCE_DIR}/src/research/n009_scene_contract"
  "${PROJECT_SOURCE_DIR}/src/research/n007_reference_validity"
  "${N010_N}/imported/integration" "${N010_N}/imported/lane_a_split_rc"
  "${N010_N}/imported/lane_b_traversal" "${N010_N}/imported/lane_e_dynamic_geometry")
target_compile_features(phos-n010-capture PRIVATE cxx_std_20)
target_link_libraries(phos-n010-capture PRIVATE
  vk-bootstrap::vk-bootstrap fastgltf::fastgltf Threads::Threads ${CMAKE_DL_LIBS})
target_compile_definitions(phos-n010-capture PRIVATE PHOS_GI_N006_SOFTWARE_PRIMARY=1
  PHOS_GI_LANE_A_SHADER_DIR="${PROJECT_BINARY_DIR}/shaders"
  PHOS_GI_LANE_B_SHADER_DIR="${PROJECT_BINARY_DIR}/shaders"
  PHOS_GI_INTEGRATION_SHADER_DIR="${PROJECT_BINARY_DIR}/shaders")
set_target_properties(phos-n010-capture PROPERTIES RUNTIME_OUTPUT_DIRECTORY "${PROJECT_BINARY_DIR}")
add_dependencies(phos-n010-capture phos-n009-capture phos-n010-shaders)
add_executable(n010_direct_diagnostic direct_diagnostic.cpp)
target_include_directories(n010_direct_diagnostic PRIVATE "${PROJECT_SOURCE_DIR}/src/research/n008_hdr_oracle")
target_compile_features(n010_direct_diagnostic PRIVATE cxx_std_20)
target_compile_options(n010_direct_diagnostic PRIVATE -fno-fast-math -ffp-contract=off)
add_custom_command(OUTPUT "${N010_GENERATED}/n010_probe_model.cpp"
  COMMAND ${Python3_EXECUTABLE} "${PROJECT_SOURCE_DIR}/scripts/research/n010_comparison_readiness/generate_probe_model.py"
    --out "${N010_GENERATED}/n010_probe_model.cpp"
  DEPENDS "${PROJECT_SOURCE_DIR}/scripts/research/n010_comparison_readiness/generate_probe_model.py"
    "${N010_SCRIPT}" "${PROJECT_SOURCE_DIR}/src/research/n009_scene_contract/n009_probe_model.cpp"
  VERBATIM)
add_executable(n010_probe_model "${N010_GENERATED}/n010_probe_model.cpp")
target_include_directories(n010_probe_model PRIVATE "${PROJECT_SOURCE_DIR}/src/research/n008_hdr_oracle")
target_compile_features(n010_probe_model PRIVATE cxx_std_20)
target_link_libraries(n010_probe_model PRIVATE Threads::Threads)
target_compile_options(n010_probe_model PRIVATE -fno-fast-math -ffp-contract=off)

# Native ray-query path tracing comparator, isolated from RC transport.
set(N010_PT_GLSL "${PROJECT_SOURCE_DIR}/shaders/research/n010_comparison_readiness/n010_pixel_pt.comp.glsl")
set(N010_PT_SPV "${PROJECT_BINARY_DIR}/shaders/n010_pixel_pt.spv")
if(GLSLC)
  add_custom_command(OUTPUT "${N010_PT_SPV}" COMMAND "${GLSLC}" --target-env=vulkan1.3 -O "${N010_PT_GLSL}" -o "${N010_PT_SPV}" DEPENDS "${N010_PT_GLSL}" VERBATIM)
elseif(GLSLANG_VALIDATOR)
  add_custom_command(OUTPUT "${N010_PT_SPV}" COMMAND "${GLSLANG_VALIDATOR}" -V --target-env vulkan1.3 -S comp "${N010_PT_GLSL}" -o "${N010_PT_SPV}" DEPENDS "${N010_PT_GLSL}" VERBATIM)
else()
  add_custom_command(OUTPUT "${N010_PT_SPV}" COMMAND $<TARGET_FILE:glslang-standalone> -V --target-env vulkan1.3 -S comp "${N010_PT_GLSL}" -o "${N010_PT_SPV}" DEPENDS glslang-standalone "${N010_PT_GLSL}" VERBATIM)
endif()
add_custom_target(phos-n010-pixel-pt-shader DEPENDS "${N010_PT_SPV}")
add_executable(phos-n010-pixel-pt pixel_pt_main.cpp
  "${N010_GENERATED}/n010_b002_vulkan.cpp"
  "${N010_N}/imported/lane_b_traversal/b002_compute.cpp"
  "${N010_N}/imported/lane_b_traversal/b002_hwrt.cpp"
  "${N010_N}/imported/integration/i001_compute.cpp")
target_include_directories(phos-n010-pixel-pt PRIVATE "${CMAKE_CURRENT_SOURCE_DIR}" "${PROJECT_SOURCE_DIR}/src"
  "${N010_N}/imported/lane_a_split_rc" "${N010_N}/imported/lane_b_traversal" "${N010_N}/imported/integration")
target_compile_features(phos-n010-pixel-pt PRIVATE cxx_std_20)
target_link_libraries(phos-n010-pixel-pt PRIVATE vk-bootstrap::vk-bootstrap Threads::Threads ${CMAKE_DL_LIBS})
target_compile_definitions(phos-n010-pixel-pt PRIVATE PHOS_GI_INTEGRATION_SHADER_DIR="${PROJECT_BINARY_DIR}/shaders")
set_target_properties(phos-n010-pixel-pt PROPERTIES RUNTIME_OUTPUT_DIRECTORY "${PROJECT_BINARY_DIR}")
add_dependencies(phos-n010-pixel-pt phos-n010-pixel-pt-shader)
