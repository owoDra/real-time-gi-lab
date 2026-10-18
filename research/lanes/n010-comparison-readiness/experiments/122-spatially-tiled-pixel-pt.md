# N010 spatially tiled pixel PT — prospective source and equivalence contract

2026-10-18 JST; parent `8c36c17883edb83983191c9dcac764b5c3d244af`.
Source/runtime preparation inside N010, not N011 or a new GI algorithm.
Commit before preparation/build/acquisition. No change to power/display/
driver settings or default Renderer/CMake/shader inputs.

## Question and immutable physical boundary

Can the original independent GPU pixel PT produce its complete image through
small spatial dispatches, retaining the original per-pixel sampling and
transport, while yielding between dispatches for desktop responsiveness?
Retained185's C1 PT-B8/1024 zero-dose median is4.216598272 GPU seconds per
full image. Repeating the old monolithic image64 times is not the next step.
This is an operational problem; do not lower quality/sample counts or omit
expensive scenes to fit a measurement campaign.

Keep original camera/geometry/lighting/ray intervals/offsets/sidedness, all
samples, exact per-pixel RNG and bounce/sample summation order. Partition
PIXELS, not samples. Each pixel is written once per complete frame and runs
the original entire loop. Do not introduce cross-dispatch accumulation,
reseed samples, average chunk averages or present partial images as complete.

Generate isolated copies from pinned `pixel_pt_main.cpp` and
`n010_pixel_pt.comp.glsl`. Record a full inverse of every edit. The shader's
camera/RNG/sample/transport/summation tail and all transport/RNG helper
functions must remain byte-identical. This source check does not prove
floating GPU equivalence; runtime proof is separate.

## Bounded execution and evidence

The prepared host accepts pixel-PT only, original1..16384spp and vertex
counts1/2/8, static or the original source/target/recovery sequence of up to
five frames. Dense RC and calibration-dose mode are refused by this variant;
their implementations are retained separately. New push constants add
explicit pixel begin/count; descriptor buffers and owned allocation scheme
remain the original ones. No new persistent image/sum/RNG buffer is needed.

Default64 pixels/dispatch; declared range1..512. Yield at least2ms between
dispatches. The first numerical captures use64 pixels and2ms pauses, fixed
before data. Retain every tile's pixel interval, raw begin/end GPU timestamps,
actual queue timestampValidBits/period, frame and seed. Reject unsupported
timestamp wrap periods; no interpolation, filtering or silent masking of
invalid samples. Guard each completed tile at250ms and each fence wait at
500ms; stop without a following tile on failure. These are operational
responsiveness stops, not a GI quality loss or a stability-percentage gate.
They do not cancel an already submitted GPU dispatch. Preserve partials.
No adaptive tile-size retry or automatic next capture.

Record BOTH the sum of GPU tile work and first-tile-to-last-tile timestamp
envelope, which includes the cooperative host gaps. The original upload/
BLAS/TLAS/uniform GPU costs remain separately recorded and included. Retain
CPU frame wall including submits, fence waits, receipts and pauses. The
prepared `gpu_us` uses maintenance segments plus image envelope; the active
GPU sum is separate. Do not substitute the active sum for complete elapsed
cost or infer a performance win from work spread across idle intervals.
Setup/readback remain separately identified, with original ownership ledger,
true peak and zero teardown. Calibration and accepted timing remain absent.

## Ordered manual steps and fixed numerical criterion

1. **Source preparation389:** run `prepare_tiled_pixel_pt.py` once. Only source
   files and edit/provenance records are written under
   `out/research/n010-comparison-readiness/tiled-pixel-pt-source-v1`.
   Source preparation may occur while CPU260 runs. No native/compiler/GPU work.
2. **Isolated build390:** only after CPU260 is terminal with seed-integrity
   PASS and actual quiescence. Compile/link private shader/host outputs using
   the original actual compiler/link inputs and explicit private shader path.
   CPU31/nice15, one compiler at a time; each120 CPU/180 elapsed seconds,
   4GiB address-space cap. Record actual process identities/limits and all
   inputs/outputs. Never invoke the default build graph or replace active
   executables. The bounded build driver remains to be implemented.
3. **Whole-image numerical replay391:** after valid build, two separately
   invoked static C1/C7 PT-B8/1024 captures, seed305419896, original state
   paths from immutable046. Compare EVERY direct/indirect/total PFM byte
   against046's retained original full-image baseline. Exact match required;
   no masks, relative-tolerance substitution or failed-pixel removal. Validate
   all tile ranges/coverage/seeds/timestamps, state identities, full owned
   ledger/peak/teardown and actual native resource receipts. Each native
   CPU31/nice15,120 CPU/180 elapsed seconds; no second capture after a failure.
   GPU mappings need a separately specified address-space policy; the8GiB
   owned Vulkan cap remains. The acquisition/replay driver is not yet written.

No old monolithic GPU recapture is needed for these two baseline images;
046's accepted bytes remain authoritative. This is implementation equivalence
to an existing comparator, not independent physical reference qualification.
Later all required quality budgets, static/dynamic states, timing boundaries
and final evidence intake still need their own complete proof. Source-only
dynamic support is not dynamic runtime acceptance. A successful two-state
replay cannot qualify all24 references or all comparator timing.

## Stop and nonclaims

Any source/build/byte/count/state/resource/ledger/time-guard failure is retained
and stops the specified step. No automatic queue or full timing campaign.
Current plan119's focused GPU counter diagnosis remains the next GPU task
after260; this preparation does not supersede it or restart the failed372
variant. No superiority, timing precision, reference admission or N010 READY
from prepared source. N001–N009 outcomes and Sponza direct-relative1.0
**UNRESOLVED / 未解決** scored pixels remain unchanged. Unit/regression tests
and default build are NOT RUN unless separately requested.
