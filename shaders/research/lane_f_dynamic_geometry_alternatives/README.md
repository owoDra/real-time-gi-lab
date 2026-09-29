# Lane F shaders

Lane F candidate shaders live here.

- F001 adds no candidate shader; it replays accepted A001/I001 paths.
- F002 uses `f002_lbvh.comp.glsl` for the complete transient builder:
  current-frame input generation, AABB, page/local Morton, stable radix sort,
  Karras LBVH topology, and bottom-up bounds. Reset/barrier costs stay inside
  the measured builder boundary.


F003 adds three frozen candidate shaders:
- `f003_lbvh_builder.comp.glsl`: measured current-frame dynamic input,
  AABB, page/local Morton, radix, topology, and bounds;
- `f003_dynamic_traversal.comp.glsl`: exact-triangle binary-LBVH traversal;
- `f003_hit_merge.comp.glsl`: shared-tolerance static/dynamic nearest-Hit
  merge with lower-`primitive_id` tie break.
