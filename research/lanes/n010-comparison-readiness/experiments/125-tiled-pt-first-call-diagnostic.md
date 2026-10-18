# N010 post-hoc tiled PT first-call diagnostic

2026-10-18 JST; parent9a4531d3. Commit policy/driver before preparation.
395 is a failed capture; no retry of its complete image or C7 is authorized
by this diagnostic. Source/default build and accepted result bytes stay fixed.

Question: which Vulkan operation/result can be observed in the first spatial
tile, using the same390 shader, C1 state,1024spp/depth8/seed305419896/tile64?
395's generic error does not identify a call; do not assume fence timeout.

Prepare a private copy of389's whole host. Replace only the `check` wrapper
with a macro that records expression, generated source line and VkResult
before the original success check; preserve the original exception string.
After the first tile's timestamp receipt and original250ms operational check,
throw an explicit FIRST_TILE_COMPLETE_NO_IMAGE marker before any second tile
or readback. Prove a full inverse of both source edits. Preserve the exact
390 SPIR-V and shader path; no shader build, sample or transport change.
Logging can affect host overhead; this is diagnostic, not equivalent timing.

Manual steps, no queue:

1. `diagnose_tiled_pt_first_call.py --step prepare` ->396, source/inverse only.
2. `--step build` ->397, private host/link using390's exact recorded commands,
   only private source/object/dependency/output paths change. One compiler at
   a time, CPU31/nice15,120CPU/180elapsed seconds,4GiB address space each.
3. `--step probe` ->398, exactly one first-tile-only native. CPU31/nice15,
   10CPU/5elapsed seconds, unlimited Vulkan virtual address space as123.
   Keep500ms fence/250ms completed-tile/180s image guards unchanged. Require
   actual quiescence, terminal valid397, terminal393/395,2GiB disk free.
   Record actual PID/start/boot/PGID/resources, all stdout/stderr, call trace,
   generated call-site source line, tile receipts, ledger and SHA identities.
   Kill only this invocation's owned new process group on elapsed timeout.

Stop after one probe regardless of outcome. No result-driven extension or
second sample/capture. A valid trace with one nonzero VkResult identifies
the observed call/result in this diagnostic; it does not retrospectively
prove395 had the same result. If the first tile completes, state that395's
failure did not reproduce; no causal inference from a successful diagnostic.
If only an operational guard fires or trace is incomplete, retain that
outcome without naming an unobserved Vulkan error. Native exit1 is expected
for both a recorded nonzero call and the explicit first-tile stop. Never
interpret partial frames, a bounded stop or exception-path ledger as a
successful full image or accepted memory record.

All396–398 retain all_pass/accepted_timing/reference_admission=false;
step_valid refers only to source/build/diagnostic record integrity. No new
numerical cutoff, accepted timing, physical/reference admission, superiority
or N010 READY. Original395 and N001–N009 unchanged; Sponza direct-relative1.0
pixels UNRESOLVED/未解決 and scored. No tests, default build, CUDA, Actions,
power/display/clock/driver/other-app changes, or following CPU seed queue.
