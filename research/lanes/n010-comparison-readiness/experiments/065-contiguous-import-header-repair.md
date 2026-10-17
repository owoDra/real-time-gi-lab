# N010 prospective contiguous imported-header repair

Date: 2026-10-17 JST. Parent: `641d6b8`. Before corrected build/acquisition.

205 preserves successful runtime/capture compiles, then compute compile exit1.
The generated compute translation unit moved directories; its original
relative b002_vulkan include resolved the historical standalone Lane B header
through another include directory, whereas i001_compute.hpp correctly resolved
the Renderer pinned imported header. The resulting duplicate type declarations
are a compile failure, not GPU measurement or transport failure. No GPU run.
Preserve 204/205 and all generated/diagnostic bytes. Do not deduplicate trees.

One include rewrite in generated compute source only:
`../lane_b_traversal/b002_vulkan.hpp` ->
`imported/lane_b_traversal/b002_vulkan.hpp`.
This chooses the same imported header as the original in-place translation
unit. Whole generated-source inverse; no original header or class-layout edit.
Retain 064 decoder argument fix. All 063 rules, bounds and gates remain.

Build result 206, `contiguous-c7-build-v3`, one attempt; stop on failure.
Unused future names from 064 are superseded: sizing 207 at
`contiguous-c7-sizing-v3`, and only after actual PASS, diagnostic 208 at
`contiguous-c7-diagnostic-v3`. Preserve exact original 9 sizing samples and
8x64 schedules/classifier, every image/scratch and memory check. No tuning,
extra frames, old-run restart or full campaign. No acquired data exist for
this candidate yet. Unit/regression tests NOT RUN; N010 remains NOT_READY.
