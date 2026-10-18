# N010 exact sample continuation for bounded complete pixel PT

2026-10-18 JST; parentcf2fe7bb. Commit before preparation/native work.
395 remains failed;398 is one first-tile operational stop, not a performance
estimate or proof of that failure's cause. Do not rerun123/125 or relax guards.

## Fixed physical and numerical contract

Produce the same complete pixel-PT images as046 while yielding within each
pixel's sample sequence. Keep original camera, primary/NEE, ray intervals,
offsets, geometry/sidedness, every RNG call, sample/vertex order, sample count,
per-sample transport and scalar float addition order. No sample reseeding,
chunk averages, partial-image admission or reduced spp/quality budget.

Private derivatives of389's source add a16-byte/pixel storage record:
uint RNG state, uint floatBits(indirect sum), uint next-sample index, uint
error word. At sample_begin0 initialize the original RNG/sum once; otherwise
require the prior next index/error and restore the exact bits. Execute the
original sample body for [begin,end), store exact RNG/sum/next, and write the
image only at end==spp. Missed primary rays retain zero state/sum with next
advanced and write original zero image only at completion. Bad progress marks
an error; do not continue that pixel or accept an incomplete final state.

Per-pixel state is independent. Primary/direct calculations repeat per chunk
with identical inputs; include ALL that work in costs. GLSL original transport/
RNG helpers and the entire per-sample body including scalar sum addition must
be byte-identical. Prove complete host/shader inverses for every edit. Source
identity is not floating runtime proof; final image equality is mandatory.

## Bounded execution and ownership

Fixed first captures: spatial tile4096 pixels, sample_chunk16, pause2000us.
Host ranges1..4096 pixels and1..16 samples per dispatch; no adaptive changes.
Loop chunks then pixel ranges, covering EVERY pixel/sample exactly once.
Keep500ms fence,250ms completed dispatch and180s complete image operational
guards. Reject on a guard without another dispatch/retry; no in-flight cancel
promise. New28-byte push constants carry spp/vertices/seed/pixel begin/count/
sample begin/end. Existing descriptor bindings unchanged plus state binding4.
Do not reuse/modify the default executable/shader or imported backend files.

The persistent state allocation is16*width*height bytes (921600 at320x180)
in addition to original image/uniform/geometry/AS/scratch. Include it in the
owned ledger and true peak; owned total<=8GiB and zero teardown remain.
Record every dispatch's ranges, seed/image, raw ticks/valid bits/period and
GPU duration. Record active GPU sum AND first-to-last envelope including ALL
cooperative gaps, maintenance costs, CPU frame wall and separate readback.
Do not hide repeated primary/direct work, state overhead or yield gaps.
Download and preserve final state bits for every captured frame; require
next==spp,error0 and finite nonnegative accumulated sum for EVERY pixel.
Readback/proof is outside the original frame work boundary and reported
separately, not omitted from end-to-end accounting.

## Ordered manual steps and stopping

1.400 source preparation only, `prepare_continuation_pixel_pt.py`, private
   `continuation-pixel-pt-source-v1`. No native/compiler/GPU. Refuse existing.
2.401 isolated build, exact original compiler/link inputs with private
   source/object/shader directory/output only. CPU31/nice15, each compiler
   120CPU/180elapsed/4GiB, serial, quiescent, no default build graph.
3.402 C1 static full image then, separately and only after valid402,403 C7.
   Original046 states/seed305419896/PT-B8/1024, tile4096/chunk16/pause2000.
   Each one native CPU31/nice15,120CPU/180elapsed, unlimited Vulkan virtual
   mappings as123,2GiB disk free, one owned process group/no overlap. Preserve
   native identity/limits/boot/command, environment, stdout/stderr, partials.
   No old monolithic recapture, retries or following capture queue.402 failure
   stops403; any403 failure stops positive404. No guard/sample/tile tuning.
4.404 independent retained-payload replay only after both valid captures.
   Compare EVERY top-level and frame0 direct/indirect/total PFM BYTE to046's
   pinned archived actual bytes. Verify exact physical state identities,
   complete two-dimensional dispatch coverage/progress and timestamp costs,
   all final state words and owned allocation lifetime/peak/teardown. No
   pixel masks, tolerances, caller booleans or summary-only acceptance.

Only the source generator is supplied initially. Build/acquisition/intake
drivers must be committed before their respective work, with these fixed
criteria. No automatic queue.400 all_pass=false;401 build scope only;
402–404 numerical_replay_valid separately, all_pass/accepted_timing/
reference_admission=false. Even a two-image PASS is implementation equivalence,
not an independent physical oracle, all-budget/dynamic proof, calibrated
timing, full comparator memory campaign or N010 READY. All further required
quality/frame/budget boundaries and complete evidence intake remain.

References16/24; original physical artifact inventory14/17 incl one diagnostic
item. Candidate393 C1 reference-backend conformance remains separate. Sponza
direct-relative1.0 pixels UNRESOLVED/未解決 and scored. N001–N009 unchanged.
No tests, Actions, CUDA, display/power/clock/driver/app changes, N011 or
scientific queue. Timing uncertainty treatment120 remains prospective.
