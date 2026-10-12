# Opt-in diagnostic executable; does not modify historical N001-N006 targets.
find_package(Python3 REQUIRED COMPONENTS Interpreter)
find_package(Threads REQUIRED)
set(N007_GENERATED "${CMAKE_CURRENT_BINARY_DIR}/generated")
set(N007_SOURCE "${PROJECT_SOURCE_DIR}/src/research/lane_n_end_to_end_renderer")
set(N007_SHADERS "${PROJECT_SOURCE_DIR}/shaders/research/lane_n_end_to_end_renderer")
set(N007_GENERATOR "${PROJECT_SOURCE_DIR}/scripts/research/n007_reference_validity/generate_capture.py")
add_custom_command(OUTPUT
  "${N007_GENERATED}/n007_runtime.cpp"
  "${N007_GENERATED}/n007_hwrt_composite.comp.glsl"
  "${N007_GENERATED}/n007_software_composite.comp.glsl"
  COMMAND ${Python3_EXECUTABLE} "${N007_GENERATOR}"
          --root "${PROJECT_SOURCE_DIR}" --out "${N007_GENERATED}"
  DEPENDS "${N007_GENERATOR}"
          "${N007_SOURCE}/n001_runtime.cpp"
          "${N007_SHADERS}/n001_composite.comp.glsl"
          "${N007_SHADERS}/n003_composite_software.comp.glsl"
  VERBATIM)
foreach(kind hwrt software)
  set(shader "${N007_GENERATED}/n007_${kind}_composite.comp.glsl")
  set(spirv "${PROJECT_BINARY_DIR}/shaders/n007_${kind}_composite.spv")
  if(GLSLC)
    add_custom_command(OUTPUT "${spirv}"
      COMMAND ${CMAKE_COMMAND} -E make_directory "${PROJECT_BINARY_DIR}/shaders"
      COMMAND "${GLSLC}" --target-env=vulkan1.3 -O "${shader}" -o "${spirv}"
      DEPENDS "${shader}" VERBATIM)
  elseif(GLSLANG_VALIDATOR)
    add_custom_command(OUTPUT "${spirv}"
      COMMAND ${CMAKE_COMMAND} -E make_directory "${PROJECT_BINARY_DIR}/shaders"
      COMMAND "${GLSLANG_VALIDATOR}" -V --target-env vulkan1.3 -S comp "${shader}" -o "${spirv}"
      DEPENDS "${shader}" VERBATIM)
  elseif(TARGET glslang-standalone)
    add_custom_command(OUTPUT "${spirv}"
      COMMAND ${CMAKE_COMMAND} -E make_directory "${PROJECT_BINARY_DIR}/shaders"
      COMMAND $<TARGET_FILE:glslang-standalone> -V --target-env vulkan1.3 -S comp "${shader}" -o "${spirv}"
      DEPENDS glslang-standalone "${shader}" VERBATIM)
  else()
    message(FATAL_ERROR "N007 requires a GLSL compiler")
  endif()
  list(APPEND N007_SPIRV "${spirv}")
endforeach()
add_custom_target(phos-n007-shaders DEPENDS ${N007_SPIRV})
add_executable(phos-n007-capture
  n007_capture_main.cpp
  "${N007_GENERATED}/n007_runtime.cpp"
  "${N007_SOURCE}/n001_reference.cpp"
  "${N007_SOURCE}/imported/integration/i001_compute.cpp"
  "${N007_SOURCE}/imported/lane_a_split_rc/a001_scene.cpp"
  "${N007_SOURCE}/imported/lane_a_split_rc/a001_runtime.cpp"
  "${N007_SOURCE}/imported/lane_a_split_rc/a001_analysis.cpp"
  "${N007_SOURCE}/imported/lane_b_traversal/b002_scene.cpp"
  "${N007_SOURCE}/imported/lane_b_traversal/b002_vulkan.cpp"
  "${N007_SOURCE}/imported/lane_b_traversal/b002_compute.cpp"
  "${N007_SOURCE}/imported/lane_b_traversal/b002_hwrt.cpp"
  "${PROJECT_SOURCE_DIR}/src/vk_context.cpp")
target_include_directories(phos-n007-capture PRIVATE
  "${PROJECT_SOURCE_DIR}/src" "${N007_SOURCE}"
  "${N007_SOURCE}/imported/integration"
  "${N007_SOURCE}/imported/lane_a_split_rc"
  "${N007_SOURCE}/imported/lane_b_traversal"
  "${N007_SOURCE}/imported/lane_e_dynamic_geometry")
target_link_libraries(phos-n007-capture PRIVATE
  vk-bootstrap::vk-bootstrap fastgltf::fastgltf Threads::Threads ${CMAKE_DL_LIBS})
target_compile_features(phos-n007-capture PRIVATE cxx_std_20)
target_compile_definitions(phos-n007-capture PRIVATE
  PHOS_GI_N006_SOFTWARE_PRIMARY=1
  PHOS_GI_LANE_A_SHADER_DIR="${PROJECT_BINARY_DIR}/shaders"
  PHOS_GI_LANE_B_SHADER_DIR="${PROJECT_BINARY_DIR}/shaders"
  PHOS_GI_INTEGRATION_SHADER_DIR="${PROJECT_BINARY_DIR}/shaders")
set_target_properties(phos-n007-capture PROPERTIES RUNTIME_OUTPUT_DIRECTORY "${PROJECT_BINARY_DIR}")
add_dependencies(phos-n007-capture
  phos-n007-shaders phos-n001-shaders phos-n003-comparison-shaders)
