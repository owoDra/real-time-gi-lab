# Surface-quadratic device correctness019

2026-10-24, checkpoint cfcf6fc7. Registered before any019code, CPU float32
M001 replay, shader compilation or GPU acquisition. Observed development only.
018and all earlier sources/results/output bytes remain immutable.

## Question, boundary and limits

Does an actual float32 Vulkan implementation of018geometry reconstruction,
barrier masks, coefficient fitting and three filtering stages retain numerical
correctness and all six original image-quality decisions? This is a necessary
component gate toward an integrated image-producing architecture. It is not
architecture acceptance, a novel regression method or a timing experiment.

Use the exact three013HWRT primary exports already admitted in096, including
their original float t/normal/IDs/flags and camera. Device reconstructs positions
and oriented normalized normals from those values; it computes barriers and
coefficients itself. Do NOT upload CPU positions, masks, ranks or coefficients.
Original24PT indirect images1/4/16/64spp and the six unchanged admitted four-seed
16384spp indirect means supply five image inputs per target. These are uploaded
as float32, with conversion error included. Original direct/reference means stay
unchanged in scoring. No new rendering/reference path or primary intersection
is acquired: archived-export replay is explicitly distinct from tracing a new
primary or PT image. A later integration must produce these inputs on device,
include every tracing/fitting/filter/allocation/synchronization cost and qualify
actual movement/dynamic behavior before full-system claims. Free CPU data replay
and isolated dispatch timestamps cannot establish end-to-end competitiveness.

New standalone host/shaders/scripts only, no default CMake/Renderer linkage,
N001–N010 edits, old output write, CI/Actions or power/clock/desktop changes.
Prefer a minimal compute context; no ray-query feature/AS is needed for replay.
All owned vkAllocateMemory lifetimes are recorded, true peak<=8GiB and zero
teardown required; driver-private and CPU allocations remain outside that ledger.

## Fixed float32 algorithm and numerical health

Use018basis, ordered two-sweep modified Gram-Schmidt, strict pivot1e-6*sum(a),
L1<=4 quadratic/affine/constant selection and zero miss output without retuning.
Keep25taps, kernel[1,4,6,4,1], strides1/2/4 and all segment barriers unchanged.
The old absolute plane epsilon is converted once to float32; do not enlarge it.
Reconstruct camera rays with the017pixel-center expression in explicit ordered
float32 scalar arithmetic, normalize, position=origin+direction*t. Normalize
the exported normal and flip only if its dot with the ray is positive. Device
geometry is saved in full, including exact hit/miss/material input identities.

Use explicit scalar sums/ordered products, GLSL precise and CPU
-fno-fast-math/-ffp-contract=off; no subgroup reductions or relaxed math.
Share the actual scalar shader kernel through a C++/GLSL-compatible include for
CPU execution, with independent Python/double/SVD checks as a separate oracle.
CPU shader execution is not GPU runtime verification. Actual device geometry
feeds the independent coefficient replay, avoiding attribution of geometry
roundoff to a different fitting implementation.

Before seeing019outputs, fix the following health bounds, separate from the
unchanged scientific image gates:

- Device position vs independent ordered camera reconstruction: max absolute
  component error<=5e-6*max(1,max absolute expected position); oriented normal
  max component error<=2e-5; hit normal norm error<=1e-4. Miss geometry exactly0.
- Recompute ALL masks/model/retained-column/selected-column bitmaps with actual
  scalar float32 kernel on the captured device geometry: exact integer match.
  Report changes from018maps; exact agreement with018double branching is not
  presumed or substituted for agreement with the declared float32 algorithm.
- ALL finite coefficient fields vs that float32 replay: rtol2e-4, atol2e-5.
  Rejected/miss coefficients exactly0; hit abs(sum(c)-1)<=2e-4 and L1<=4+2e-4.
  The algorithm still selects models at exactly L1<=4; these are only health
  checks on saved finite-precision outputs, not an enlarged selection threshold.
  No coefficient renormalization, clipping or correction.
- Independently solve the fixed64uniform full-image+64hit-percentile pixels per
  scene/stage with double weighted SVD on actual device geometry and the same
  accepted taps. Compare coefficients with rtol2e-4/atol2e-5; report rank/model
  differences from double as diagnostics. Apply the independently solved
  coefficients to the actual previous stage at these points: preclip/clipped
  absolute error<=2e-4*max(max absolute previous-stage image,1e-20).
- Replay ALL preclip/clipped outputs using captured coefficients and ordered
  float32 products/sums: rtol2e-5, atol2e-7*max(max absolute previous-stage image,
  1e-20), separately per input/stage. Record every negative preclip count,
  minimum and energy from actual outputs. Clipping only max(raw,0) each stage;
  no upper clamp, rescale or pixel exclusion. Final outputs finite/nonnegative.

## CPU gates and immutable preparation

Before the first GPU process:

1. Test the actual shared float32 functions on independent analytic/SVD fixtures:
   zero/miss, constant/positive affine/quadratic, rank1/one-dimensional support,
   scalar segment barriers/material/normal/plane/viewport, signed/preclip
   clipping, two L1 fallbacks and normalization bounds. Reuse01814and01716test
   evidence without identical rerun. Compile actual shaders for Vulkan1.3 and
   validate SPIR-V, including precise/NoContraction evidence. CPU-only native CLI
   rejects malformed/range/nonfinite input and overwrite attempts BEFORE Vulkan.
   Run CPU mode with an unusable ICD to demonstrate no Vulkan initialization.
2. Commit exact host/shared shader/test/builder code before executing six fixed
   full-frame native CPU float32 dry replays in H01/B2,H01/B8,H02/B2,H02/B8,
   H03/B2,H03/B8 order. Rehash all018/017raw inventories,022PT identities,
   096primary and original physical/reference/source chains. Freeze a unique
   plan/input tree per target; use16GiB disk precondition. Every native CPU
   output gets an independent all-field/whole-image audit. No GPU may start
   unless all six CPU rehearsals pass numerical and selected-image gates.
3. Implement/test exact one-named-process GPU preparation, prior-audit ordering,
   invalid/missing/partial data, full provenance and output-overwrite refusal.
   Pin compiler/linker command, actual dependencies, shared sources, binary,
   shaders, loader and accepted CPU receipts. Preserve failed build/test/dryrun
   attempts under new output versions; only an identified implementation repair
   permits a new CPU attempt, never an identical repeat or overwrite.

## One process at a time, quality and finite stop

At most six new GPU processes in the same fixed target order. Before each,
announce its exact single command; freeze/revalidate complete CPU/build/input
identities. Use120CPU/180wall seconds and a bounded250ms fence per submitted
unit; no automatic GPU queue. Coefficient fit units contain at most128pixels
at one stride to bound heavy shader work. Every submitted unit completes and
is journaled before another. Capture full geometry, masks/selections,
coefficients, all five inputs' preclip/clipped stages and error maps under
repository/out. Timestamp fields are diagnostic only, not accepted timing.
Input conversion/allocation/fitting/filter work and all lifetimes are visible.

Independent terminal audit before the next target must rehash full plan,
build/source/dependency/shader/reference/input and output inventories, validate
all numerical predicates above, all journal/fence completions,<=8GiB owned peak
and zero teardown. Recompute every57,600pixel linear-luma metric, independently
fsum RMS/energy bias, original totalNRMSE<=5%, indirectNRMSE<=10%, absolute
indirect signed-energy bias<=5%, finite/defined metrics and no exclusions.
Report all four noisy rungs and the separate reference-reconstruction bias
diagnostic, preserving every scientific loss. The already selected018rung
(H01/B2=16; all others=64) AND reference-bias diagnostic must pass; do not
escalate samples or select a different rung to rescue a019failure. All six
target PASS outcomes establish COMPONENT_GPU_CORRECTNESS_PASS only for this
archived-export boundary, not an integrated renderer or architecture admission.

Any native failure/timeout, missing/partial/inconsistent provenance, numerical,
memory, selected-image or bias-gate failure preserves all evidence and stops
019before any later GPU target: STOP_NO_RETRY. No immediate re-acquisition,
alternate backend, relaxed bound, sample/radius/model change or selected-target
continuation. A separately identified repair needs a new preregistration and
new outputs. Six passes end019; no further019process or timing follows.

Publish compact results, commit/push research branch and update Issue7. Default
Renderer build/runtime regression and validation layers remain NOT_RUN unless
actually executed separately. Fair denoised external families, new independent
heldouts/dynamics/Sponza/multiple devices, real-time and novel light-transport
architecture evidence remain open; Lane M is not complete after this component.
