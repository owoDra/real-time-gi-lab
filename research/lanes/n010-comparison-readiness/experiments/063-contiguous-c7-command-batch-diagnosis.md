# N010 prospective contiguous C7 command batch diagnosis

Date: 2026-10-17 JST. Parent: `ca2520c`. Register before building/acquiring.
Plan 060 packed readback has completed and FAILS; do not restart or tune it.

## Question and fixed boundary

Does removing the remaining CPU record/submit/fence/query gap between C7
frames establish the original precision conditions? Packed readback alone did
not. Per-frame CPU gaps are a hypothesis, not an established cause. Preserve
original complete Renderer timestamps, neutral work and all scheduled frames;
no averaging frames into one observation, additional warmup or power changes.

Build a distinct isolated fixture from exact 199 sources. Static C7 HWRT ONLY;
reject target, topology, other backend/scenario and non-calibration use. Record
all the existing dose-file frames (at most 256) into distinct command buffers,
submit them together once and wait once. No new scientific frames are added.
Existing buffer state persists in original frame order. Add a full inter-frame
memory dependency and retain original commands between original timestamps.
Readback copies remain after stamp15. This changes submission cadence and
outside-timestamp diagnostic work, not the scored Renderer shader commands.
Any positive result is specific to this fixture/boundary; no transfer to all
sixteen boundaries or to fresh-state dynamic execution is authorized.

Use a host-coherent uniform ring, 4096-byte stride, at most 256 entries. Query
actual device alignment/range limits read-only and reject incompatibility.
Transform uniform descriptors into dynamic uniform descriptors with original
parameter-size ranges. No shader, push constants or parameter values change.
Prewrite each frame's original update_params output to its own slot. Bind its
own dynamic offset for every stage that has a uniform binding, zero dynamic
offsets for stages without one. Preserve exact frame IDs, including limits[3].
Keep compute class headers/layouts unchanged; record all source inverses.

Give every frame 24 distinct query slots, retrieve its 18 written slots only,
and retain every RGBA, counter, storage-stat and neutral-scratch buffer in its
own packed host destination. Bound packed Vulkan staging to 256 MiB, CPU RGBA
to 256 MiB and scratch spool to 16 MiB, all at most 256 frames. Include all
Vulkan allocations in the existing owned ledger (8 GiB limit, teardown zero).
Report CPU wall as batch/cached-call diagnostic, not independent frame cost.
Record the actual single submit/wait, query ranges, uniform offsets/frame IDs
and all consumed results; fail on missing/duplicate frames. No hidden repeats.

## Bounded execution and stop rules

- Build result 204, work `contiguous-c7-build-v1`. One CPU at nice15; each
  compiler/link process 120 CPU / 300 elapsed seconds, 8 GiB address-space.
  Hash all inputs, generated source/object/binary and actual resource receipts.
  Whole-parent inverses and unchanged original timed recording/expressions.
- Only after build PASS: one sizing result 205, work `contiguous-c7-sizing-v1`,
  original doses [0,65536,262144] repeated three times. Original positive-slope
  sizing and +20% full-boundary dose calculation, no tuning to observations.
- Only after sizing PASS: one eight-block / 512-frame diagnostic 206, work
  `contiguous-c7-diagnostic-v1`. Original calibrate_renderer.schedule and
  analysis byte-identical. Keep pair<4 warmup classification, all samples and
  all seven original gates. One-second block settles remain. No per-frame
  extra work beyond exact scheduled original workload and disclosed copies.
- Each native invocation: one CPU nice15, 30 CPU / 30 elapsed seconds; no
  Vulkan address-space limit. One scientific worker only. Preserve partials
  and terminal failure; no retry under this plan. Stop on resource/identity,
  image, scratch, schedule, memory, count or environment error.
- All images must match original 046 C7 byte hashes, original neutral verifier
  must accept every dose, and original owned-memory replay must pass. Batch
  receipt must prove all frames consumed and exactly one submit/fence wait.

A COMPLETE precision FAIL stops this fixed candidate without full campaign.
A PASS is diagnostic C7 evidence only: other boundaries, runtime equivalence
and a prospectively complete acquisition are still required. No reference
eligibility, N010 READY or Lane M scientific result is asserted by this plan.
All original reference, timing, memory and quality gates remain. Max-relative-
error-1.0 direct pixels stay UNRESOLVED / 未解決 and included. No app/display/
clock/power/driver changes, CUDA, N011, Actions or N001–N009 edits. Unit and
runtime regression tests NOT RUN; these are isolated scientific diagnostics.
