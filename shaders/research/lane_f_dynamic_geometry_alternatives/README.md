# Lane F shaders

Lane F candidate shaders live here.

- F001 adds no candidate shader; it replays accepted A001/I001 paths.
- F002 uses `f002_lbvh.comp.glsl` for the complete transient builder:
  current-frame input generation, AABB, page/local Morton, stable radix sort,
  Karras LBVH topology, and bottom-up bounds. Reset/barrier costs stay inside
  the measured builder boundary.
