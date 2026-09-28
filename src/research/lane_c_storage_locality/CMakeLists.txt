# Lane C owns this directory. Keep storage/locality research build changes here.

set(LANE_C_SHADER_DIR "${CMAKE_SOURCE_DIR}/shaders/research/lane_c_storage_locality")
set(LANE_C_SHADER_OUT_DIR "${CMAKE_BINARY_DIR}/shaders/research/lane_c_storage_locality")

function(lane_c_compile_shader NAME SOURCE)
  set(OUTPUT "${LANE_C_SHADER_OUT_DIR}/${NAME}.spv")
  if(GLSLC)
    add_custom_command(
      OUTPUT "${OUTPUT}"
      COMMAND ${CMAKE_COMMAND} -E make_directory "${LANE_C_SHADER_OUT_DIR}"
      COMMAND ${GLSLC} --target-env=vulkan1.3 -O "${SOURCE}" -o "${OUTPUT}"
      DEPENDS "${SOURCE}"
      VERBATIM)
  elseif(GLSLANG_VALIDATOR)
    add_custom_command(
      OUTPUT "${OUTPUT}"
      COMMAND ${CMAKE_COMMAND} -E make_directory "${LANE_C_SHADER_OUT_DIR}"
      COMMAND ${GLSLANG_VALIDATOR} -V --target-env vulkan1.3 -S comp "${SOURCE}" -o "${OUTPUT}"
      DEPENDS "${SOURCE}"
      VERBATIM)
  elseif(TARGET glslang-standalone)
    add_custom_command(
      OUTPUT "${OUTPUT}"
      COMMAND ${CMAKE_COMMAND} -E make_directory "${LANE_C_SHADER_OUT_DIR}"
      COMMAND $<TARGET_FILE:glslang-standalone> -V --target-env vulkan1.3 -S comp "${SOURCE}" -o "${OUTPUT}"
      DEPENDS glslang-standalone "${SOURCE}"
      VERBATIM)
  else()
    message(FATAL_ERROR "No GLSL compiler is available for Lane C")
  endif()
  set_property(GLOBAL APPEND PROPERTY LANE_C_C001_SHADER_OUTPUTS "${OUTPUT}")
endfunction()

lane_c_compile_shader(c001_address "${LANE_C_SHADER_DIR}/c001_address.comp.glsl")
lane_c_compile_shader(c001_exact_address "${LANE_C_SHADER_DIR}/c001_exact_address.comp.glsl")
lane_c_compile_shader(c001_transition_address "${LANE_C_SHADER_DIR}/c001_transition_address.comp.glsl")
lane_c_compile_shader(c001_transition_hash "${LANE_C_SHADER_DIR}/c001_transition_hash.comp.glsl")
lane_c_compile_shader(c001_transition_clipmap "${LANE_C_SHADER_DIR}/c001_transition_clipmap.comp.glsl")
lane_c_compile_shader(c001_probe_hash "${LANE_C_SHADER_DIR}/c001_probe_hash.comp.glsl")
lane_c_compile_shader(c001_brick_hash "${LANE_C_SHADER_DIR}/c001_brick_hash.comp.glsl")
lane_c_compile_shader(c001_clipmap "${LANE_C_SHADER_DIR}/c001_clipmap.comp.glsl")

get_property(LANE_C_C001_SHADER_OUTPUTS GLOBAL PROPERTY LANE_C_C001_SHADER_OUTPUTS)
add_custom_target(lane-c-c001-shaders ALL DEPENDS ${LANE_C_C001_SHADER_OUTPUTS})

add_executable(phos-c001-storage
  c001_storage_benchmark.cpp
  ../../vk_context.cpp
)
target_include_directories(phos-c001-storage PRIVATE "${CMAKE_SOURCE_DIR}/src")
target_link_libraries(phos-c001-storage PRIVATE vk-bootstrap::vk-bootstrap ${CMAKE_DL_LIBS})
target_compile_definitions(phos-c001-storage PRIVATE
  PHOS_LANE_C_SHADER_DIR="${LANE_C_SHADER_OUT_DIR}")
set_target_properties(phos-c001-storage PROPERTIES
  CXX_STANDARD 20
  CXX_STANDARD_REQUIRED ON
  CXX_EXTENSIONS OFF
)
if(MSVC)
  target_compile_options(phos-c001-storage PRIVATE /W4 /permissive-)
else()
  target_compile_options(phos-c001-storage PRIVATE -Wall -Wextra -Wpedantic)
endif()
add_dependencies(phos-c001-storage lane-c-c001-shaders)
