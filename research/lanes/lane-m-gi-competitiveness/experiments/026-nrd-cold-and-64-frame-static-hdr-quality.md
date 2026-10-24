# M001 / 026: NRD cold and 64-frame static HDR quality

Baseline `75105c9e`:025's disclosed sky-initialized variant passes its three
runtime controls. This registration precedes new code/build/tests, image
scores and acquisitions.025 and every prior success/failure stay immutable.

Question: at which, if any, frozen per-frame sampling budget does the default
RELAX_DIFFUSE sky-initialized variant satisfy the original M001 all-pixel HDR
gates both at cold start and after a64-frame static history? This is an
established-family comparator, not a novel architecture or performance study.

## Frozen comparison and selection

All six original admitted M001 physical references/states and finite-depth
semantics remain fixed. Target order: H01/B2, H01/B8, H02/B2, H02/B8, H03/B2,
H03/B8. Per-target per-frame spp ladder: `[1,4,16,64]`. A level is one process
with one SDK/context/AS/pool and64 consecutive static frames, indices0..63.
Frame0 is CLEAR; frames1..63 CONTINUE. No repeated history clearing, camera
jitter/movement or setting tuning. Seed(i) = (0x12345678 + 0x9e3779b9*i)
modulo2^32:64 distinct prespecified pseudorandom streams, fixed common seeds
for all targets/budgets. They are not independently regenerated references.

Reuse the exact025 NRD library/selected pipelines, original024 producer and
official packing/composition SPIR-V. SDK settings, physical sampling/RNG/
shading/spawn, material/roughness conventions and common60Hz settings are
unchanged. A reversible private host/header overlay changes only the frame/
seed schedule, permits1/4spp alongside16/64 and reports64-frame metadata.
No SDK/shader rebuild or CPU image/hit/guide input. All guides and composition
remain GPU resident with no inter-stage readback. Original three-frame025
controls are not rerun. A newly executed frame0 is required to initialize the
new64-frame experiment, not a retry of an old study.

Before GPU, commit the overlay/builder/process/auditor/tests, qualify exact
inverse/unchanged operation boundaries and actual native CPU CLI/input cases
under an unusable ICD, inspect all six reference/source identities. Reuse
prior024/025 scalar/mapping/API/SPIR-V results, without pretending to rerun
them. Reuse existing65-frame025 CPU SDK exports: every new frame0..63 command,
resource and constant byte must match its existing CPU counterpart. Only the
new host object is compiled and the executable relinked against025 library;
reuse every context/HWRT/other object and all shaders. Default build unchanged.

## Evidence and correctness gates

Retain every frame's complete raw PT/direct/indirect, actual primary hits,
all-sample origins/rays/primitive witnesses and float32 sum/mean, all input
guides/pre-sanitization errors, all15 input/output/history/transient images,
all SDK constants and final RGB. No data deletion after scoring or selected
frame/image export. Preserve every sample/timestamp/allocation/readback cost.

All64 frames require complete shapes, finite/ranged fields, canonical primary
metadata/independent original primary presence/primitive/depth/unit-normal
gates, original sample miss/unit/in-lobe conventions, exact ordered float32
sum/mean and actual official guide/UNORM/viewZ/motion/error/RGB composition
gates from024. Double-precision triangle intersection of **all** saved active
secondary rays is mandatory for frames0,1,63, with unchanged024 distance bounds
and zero presence/primitive mismatches or exclusions. Other frames still check
all sample witnesses/guide sums and all primary records; no claim is made of
independently intersecting every intermediate frame's secondary ray. Save full
primary/secondary error maps for checked frames and complete field diagnostics
for all others. This fixed coverage reuses the proven, byte-identical physical
producer rather than changing its sampling or excluding ambiguous rays.

Frame0 raw PT must be byte-exact to the corresponding original M001 PT rung
for the same depth/spp/seed. At the three025 control rungs, require frame0's
entire saved binary state/guide/RGB/constants to match that025 cold frame;
at other rungs the exact producer/shader identity and the complete independent
frame0/1/63 physical checks apply. The64-frame run has no extra reset frame;
strict reset was separately qualified in025, not inferred here.

All15 native pipeline bytes must equal025's CPU export; disclose only pipeline9
differs from unmodified023. Correctly name this reference in new reports,
without inheriting the old helper's misleading key. Continuing relevant
history must advance/clamp consistently with the default maximum accumulated
history setting30 and must not be cleared every frame. Pre-execution source
clarification: RELAX_TemporalAccumulation.cs.hlsl increments the stored length
and caps it at `1 + gDiffMaxAccumulatedFrameNum`, so the stored byte sequence
includes the current frame and reaches31, not30. This clarification follows
source inspection before new CPU/GPU execution, changes no SDK setting or
HDR/physical gate, and resolves the original draft's ambiguous use of30.
Replay all owned allocation lifetimes, full peak and
zero teardown. Check complete ordered bounded-unit journal: initialization1,
frame0=488 units, each remaining frame=477 units, total30,540; SDK651 dispatches.
GPU timestamps/whole envelopes/startup/readbacks remain uncalibrated diagnostics.

## HDR decisions, costs and stops

For every frame compare linear luminance direct, indirect and total against
the exact admitted16384spp, four-seed physical reference mean, using unchanged
M001 normalization and gates: total NRMSE<=0.05, indirect NRMSE<=0.10,
absolute indirect signed energy bias<=0.05, no masks/pixel exclusions. Direct
correctness separately retains NRMSE<=1e-4, maximum absolute error<=1e-5 and
zero GPU-zero/reference-positive pixels. Preserve full error arrays, leak/
support/active-p99/zero diagnostics and independent scalar fsum metric replay.
Compose values from actual RGB: raw scalar direct, official unpacked denoised
indirect RGB and actual final total RGB; use the existing BT.709 luminance.

Cold PASS means frame0 meets all original image gates. Warm PASS means **each
of frames48..63** meets them; do not replace failing frames by a temporal mean.
Score/preserve all64 frames, including settling failures. Save consecutive-
frame luminance RMS and final16-frame mean/variance as diagnostics, with no
post-hoc temporal threshold or dynamic/ghosting claim. Joint PASS requires
both cold and warm PASS. Retain warm-only/cold-only outcomes explicitly.
For each target choose the first joint-PASS rung; otherwise exhaust through64
and mark QUALITY_FAIL. Quality losses advance the next registered level;
they are not operational failures. Never rerun a completed rung or add rungs.

One explicitly announced command and independent terminal audit at a time;
no queue or automatic retry. Stop the entire cohort on operational/timeout/
reference/correctness/ownership/ABI failure, preserving partial evidence.
Identified host/parser-only repairs require committed new version/exclusive
outputs and reuse of successful evidence where possible. Any SDK/algorithm/
threshold/seed/evidence-coverage change needs a new registration.

GPU process guard:one worker,120 CPU/180 wall seconds,4GiB address space,
8GiB aggregate owned pre-allocation cap,250ms per wait and2ms between units;
at least32GiB free disk before each run. CPU build/audit commands:one worker,
<=4GiB address space,<=240 CPU/360 wall seconds. No competing workload or
power/clock/desktop changes. Disk writes/readbacks/pauses are explicit costs,
never accepted real-time performance.025's disk check used16*1025^3 bytes
because of a string replacement; this stricter historical check is preserved,
not represented as exactly16GiB.026 uses exactly32*1024^3 bytes.

Publish progress and all failures/wins, commit/push the research branch and
update Issue7OPEN. End026 after six terminal targets or first operational
failure. No speed ranking without quality matching and separately calibrated
actual full-system boundaries; no lower-spp cost claim that omits histories/
tracing/conversion/allocation/readback/setup. CPU reference/reconstruction and
old successful cohorts are not rerun; no raw data in Git, Actions/CI, Renderer
default/N001–N010 edits or main promotion. Novel competitive transport,
new heldouts/dynamic/Sponza/multiple GPU classes/deployability remain required;
static known-corpus NRD quality alone cannot complete Lane M.
