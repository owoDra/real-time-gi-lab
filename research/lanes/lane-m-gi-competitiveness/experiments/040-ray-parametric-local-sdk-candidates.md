# 040 — Ray-parametric receiver-local SDK candidates

Registered after039/39d68c8a, before040 code, compilation/tests or acquisition.
037 compile failure and038 physical endpoint failure remain stopped and immutable.
039's frozen-output diagnosis is not re-admission. No old experiment retry.

## Physical definition and question

Can receiver-local ray-parametric positions represent actual finite physical
candidates through the unmodified SDK Make/Pack/Load without the short-segment
world-coordinate cancellation seen in038, preserving original PT arithmetic and
all unchanged numeric tolerances? This is a new position representation, not a
new proposal distribution, fake endpoint, PDF adjustment or threshold relaxation.

Keep exact original M001 scene/frame inputs,320x180/unit-grey/opaque/two-sided/
black-sky/soft-point light, original N010 closest/ignore/shadow/spawn/RNG/finite
path math and candidate Li=sum of vertices1..B-1. Primary direct is included
once. Actual ray-query origin O and generated normalized wi, primitive and t
identify the secondary intersection. Define local endpoint D=float32(t*wi),
local receiver0, and represented world intersection O+D. Preserve the ORIGINAL
barycentric world hit H, its suffix/direct/continuation spawn and all old full
vertex witnesses unchanged, separately from D. This explicitly distinguishes
two finite-precision representations of the same queried triangle intersection;
it does not assert bit equality O+D==H. The source PDF stays generated cos/pi.

SDK position stores D, primary surface position is0, normals and Li are unchanged.
Make only for actual HIT(M1, including black); primary-invalid/secondary-MISS
remain Empty(M0). Raw trial1 always stays in the image denominator. Visibility
uses the actual BVH, original world origin O, direction normalize(D) and length(D)
shortened by1-2e-7, ignoring original start/end primitives. No world H-O subtraction
in SDK target/shading/visibility arithmetic. No extra1/r², BRDF or bounce.

The representation is per receiver, not a common coordinate system. Do NOT feed
different receivers' D values directly to spatial/temporal reuse. Such reuse
requires separately qualified source-to-destination frame transforms, previous
origins/motion and persistent history ownership.040 admits candidate construction/
storage/image recovery only; no reuse, checkerboard/dynamic/HDR family admission.
This precision prerequisite does not replace fair ReSTIR family quality or the
novel competitive image-producing Renderer/full Lane M charter.

## Exact comparisons and new independent evidence

One process per H01/B2,H01/B8,H02/B2,H02/B8,H03/B2,H03/B8, in that order.
Four one-SPP seeds each: low32(original four N007 seeds) XOR0xa040a040. These are
NEW streams, fixed before execution; not a repeat of038's failed streams.
Both unchanged022 original producer and the040 observation producer generate
new paths. Every raw image/primary/source byte must match between roles.
Reuse022 original SPIR-V and bounded context/HWRT objects; no default graph edit.
New host differs from037 only by the local endpoint output/bindings, seed list
and filenames/identification; observation overlay extends exact037 reversibly.
Private HLSL derives from038's include-corrected adapter with explicit local
position/shading/visibility changes; SDK source/algorithms stay pinned/unmodified.

Independently audit every original full finite-path vertex/RNG/direct/suffix/
primitive/normal/front/spawn/zero/presence/trial/PDF field under037's exact and
rtol3e-4/atol3e-6 gates. Extend the full model with explicit local endpoint inputs;
preserve the old full model/source. Require D==float32(t*wi) within unchanged
float tolerance, local t exactly the recorded actual ray-query t, D zero on
non-HIT, positive lengths, and normalize(D) equal original generated wi under
the SAME componentwise3e-4/3e-6 gate. Audit O+D against original world ray
intersection AND H, same actual triangle membership/barycentric bounds/plane,
at original geometric tolerance. Keep full old H-O direction error/mask as
diagnostic; do not erase or claim it corrected. Original Li still belongs to
the original barycentric evaluation, not a newly evaluated suffix at O+D;
physical equivalence is limited to the registered float geometric tolerance,
not exact real arithmetic or arbitrary reuse unbiasedness.

SDK packed position must equal D bit-exactly; M/age/reserved/trials are exact.
Use local D for original-direction, source/geometric cosine, uncompressed and
packed image recovery. Retain037's rtol3e-4/atol3e-6 uncompressed recovery,
2% RGB packing budget,2e-5/2e-6 decode arithmetic and2%+3e-6 final packed error.
Real generated segment visibility and oriented endpoint hemispheres must hold.
No blackening/dropping troublesome HITs or whole-image quality substitution.
Save every new full field/error map and original absolute-coordinate diagnostic.

## CPU preparation, process and stop rules

Commit complete040 source/build/process/full-audit/tests before execution.
New CPU tests cover ABI/overlay reversibility, full physical local recovery,
black/MISS/raw trials, source-direction corruption, packed local-position
corruption and origin-independent short-segment arithmetic including the known
038 failing ray as a diagnostic fixture. Do not rerun old successful suites.
One new host compile/link, one new physical GLSL compile/validate/disassemble,
two new official-SDK HLSL compile/validate/disassemble, eight new Python contracts,
six actual native CPU input checks with unusable ICD, all before GPU. Reuse exact
022 objects and source/official SDK identities; pin all compiled dependencies.

Use actual unchanged C.guarded for every compiler/test/input/GPU child:
CPU120/wall180/4GiB/core0/default unblocked SIGXCPU. Numeric workers use actual
outer CPU1200/wall1800/4GiB and record inherited effective limits/PID before/after;
never lower them to parent360. Parent C.limits, BLAS/OMP1. Retain command before
launch, child limits, PID and terminal timeout/reaped/exit receipts. Native
8GiB aggregate owned cap/180s wall/250ms fence+unit/128pixel chunks/2ms pauses
remain. Independently reconstruct all AS/scratch/staging/pipeline allocation
lifetimes, exact true peak and zero teardown; driver-private/CPU excluded.
Record setup/upload/AS/pipelines, whole fence/pause GPU envelopes, all active
unit timestamps and readback as diagnostics, never accepted speed rankings.

Exclusive out/m001-restir040-* roots,16GiB free, same qualified022 GPU/quiet
workstation. Announce exact single command before each acquisition. Each next
condition requires previous complete native AND full supervised numeric PASS.
First preparation/test/input/GPU/physical/packing/ownership/provenance/process
failure stops040 without retry/later condition/code or threshold rescue.
No reference sampling, HDR quality scoring, accepted timing/memory advantage,
novelty/architecture promotion or full Lane M closure.022 forbids raw-PT-only
competitive timing. No N-history/power/clock/default Renderer/CI/Actions changes.
Publish raw failures/successes, preservation/index/link verification, commit/push,
and update OPEN Issue7 without narrowing any original charter gate.
