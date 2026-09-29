# Issue #17 Lane G owns this directory.
#
# G001 intentionally snapshots the F007 runtime/candidate implementation inside
# Lane G. No memory optimization is permitted here; only instrumentation may
# change before G001 concludes.

foreach(shader
  i001_bounded_producer
  i001_clamp_counters
  i001_hwrt
  i001_quantized_bvh8
  i001_radiance
  i001_software_bvh
  i001_storage_invalidate
  i001_storage_resolve
  i001_storage_update
  i001_work_to_rays
)
  add_compute_shader(
    ${shader}
    shaders/research/lane_g_transient_lbvh_hardening/${shader}.comp.glsl
  )
endforeach()

# Preserve the filenames expected by the F007-derived runtime.
add_compute_shader(
  lane_f_f003_lbvh_builder
  shaders/research/lane_g_transient_lbvh_hardening/f003_lbvh_builder.comp.glsl
)
add_compute_shader(
  lane_f_f003_dynamic_traversal
  shaders/research/lane_g_transient_lbvh_hardening/f003_dynamic_traversal.comp.glsl
)
add_compute_shader(
  lane_f_f003_hit_merge
  shaders/research/lane_g_transient_lbvh_hardening/f003_hit_merge.comp.glsl
)
add_compute_shader(
  lane_f_f005_grid_builder
  shaders/research/lane_g_transient_lbvh_hardening/f005_grid_builder.comp.glsl
)
add_compute_shader(
  lane_f_f005_grid_traversal
  shaders/research/lane_g_transient_lbvh_hardening/f005_grid_traversal.comp.glsl
)

add_custom_target(phos-lane-g-g001-shaders DEPENDS
  "${CMAKE_BINARY_DIR}/shaders/i001_bounded_producer.spv"
  "${CMAKE_BINARY_DIR}/shaders/i001_clamp_counters.spv"
  "${CMAKE_BINARY_DIR}/shaders/i001_hwrt.spv"
  "${CMAKE_BINARY_DIR}/shaders/i001_quantized_bvh8.spv"
  "${CMAKE_BINARY_DIR}/shaders/i001_radiance.spv"
  "${CMAKE_BINARY_DIR}/shaders/i001_software_bvh.spv"
  "${CMAKE_BINARY_DIR}/shaders/i001_storage_invalidate.spv"
  "${CMAKE_BINARY_DIR}/shaders/i001_storage_resolve.spv"
  "${CMAKE_BINARY_DIR}/shaders/i001_storage_update.spv"
  "${CMAKE_BINARY_DIR}/shaders/i001_work_to_rays.spv"
  "${CMAKE_BINARY_DIR}/shaders/lane_f_f003_lbvh_builder.spv"
  "${CMAKE_BINARY_DIR}/shaders/lane_f_f003_dynamic_traversal.spv"
  "${CMAKE_BINARY_DIR}/shaders/lane_f_f003_hit_merge.spv"
  "${CMAKE_BINARY_DIR}/shaders/lane_f_f005_grid_builder.spv"
  "${CMAKE_BINARY_DIR}/shaders/lane_f_f005_grid_traversal.spv"
)

# The G001 executable is added by the instrumentation checkpoint.
