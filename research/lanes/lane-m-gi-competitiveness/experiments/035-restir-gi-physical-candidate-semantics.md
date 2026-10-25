# 035 — ReSTIR GI physical candidate semantics and full-path CPU extraction

Registered after034 checkpoint02dac32e and BEFORE035 code, generated overlays,
new tests, paths or expected numerical outputs. This is a necessary physical
input gate for the real ReSTIR-family baseline, not an architecture win or a
replacement for the full Lane M charter. No GPU process is authorized by035.

## Conflict resolved before experiments

034's synthetic black/PDF0 fixture has a defined finite endpoint/normal and M1,
weight0. It establishes that declared fixture's behavior ONLY. It does not define
the encoding of a physical secondary MISS. The exact official RTXDI sample pinned
by033, ShadeSecondarySurfaces.hlsl, starts with EmptyGIReservoir and calls Make
only for a valid secondary surface. Thus the physical adapter will distinguish:

- invalid primary: no indirect sample, empty SDK reservoir;
- secondary MISS: one original Monte Carlo trial with zero contribution, empty
  SDK reservoir M0, as the official sample does;
- valid secondary HIT with black suffix: one trial and SDK M1 with positive PDF
  and zero radiance; a black hit is not a miss;
- valid nonblack secondary HIT: one trial and SDK M1, inverse solid-angle PDF.

Trial counts and the SDK's reservoir M are SEPARATE fields. Raw PT averages divide
by ALL generated trials including misses. Never condition a raw average on hits.
This explicit physical mapping supersedes any inference from the synthetic034
label, without changing034 evidence or SDK algorithms. It does not prove unbiased
SDK reuse when empty neighbors are rejected, or adopt an undocumented miss repair.
Any subsequent reuse stage must disclose this exact official miss convention and
independently inspect its denominator/history behavior before quality admission.

Existing N010 GPU PT evaluates first-leg directions from a numerically offset
spawn origin, whereas033 analytic target evaluation used the receiver position.
Those coordinates must not be silently equated. This CPU study stores the actual
spawn origin O as the proposal/shading receiver, and the UNNUDGED next ray hit H
as the secondary endpoint. The direction H-O then matches the generated direction
and its cosine solid-angle PDF. Secondary suffix evaluation retains the original
oracle's inward nudge/outgoing offset. Store geometric/nudged/spawn positions
separately. This defines extraction for the original double oracle ONLY; N010
float32 offset/BVH/primary agreement remains a later actual GPU gate.

## Falsifiable question and exact finite-depth boundary

Can an observation-only private derivative of the unchanged, qualified N008
oracle expose complete physical candidates whose original-sample shading recovers
the original finite-depth indirect path, without changing any RNG, tracing,
materials, primary/direct values, costs or finite B2/B8 semantics?

Use ALL six original scenes in order H01/B2,H01/B8,H02/B2,H02/B8,H03/B2,H03/B8.
Use original admitted scene/camera/triangle/material/soft-point-light bytes and
320x180 center primaries, black sky, unit-grey opaque two-sided materials,
infinite secondary far, original nudge/offset, no roulette or denoising. Four
fixed new seeds are each original N007 seed XOR0xa035a035a035a035; sample index0,
ONE path per pixel/seed. These new full-path witnesses do not already exist in
the old scalar-only031/032 records. No reference HDR is decoded or scored; old
references/geometry may be rehashed/reused, never regenerated.

The first camera-visible vertex contributes DIRECT only. For B total vertices,
the secondary candidate radiance Li is the sum of direct reflected radiance at
vertices1..B-1 of the exact original path. It contains no primary direct term,
no extra primary BRDF, no distance-squared factor and no extra final bounce.
For a hit, source PDF=dot(primary oriented normal, original first direction)/pi.
No-resampling diffuse contribution Li*cos(N,H-O)/(pi*PDF) must recover original
indirect. Retain all RGB channels, including zero/miss paths. Both orientations
of two-sided surfaces are handled by the original front/back rule, never abs()
of a stored oriented endpoint normal. Record orientation/support diagnostically.

## Implementation and CPU execution

Commit protocol BEFORE implementation. Commit ALL new implementation/tests/process/
audit code before use. Do not edit N001–N010 or033/034 source/results. Generate a
private N008 derivative by exact reversible namespace/signature/observation-hook
changes only. Include the unchanged original oracle as a separate namespace in
the new native contract, and compare BOTH on the new paths (not old2048 contracts
or old samples). Output components, PrimaryRecord, final RNG progression and
original counters must be bit-identical on every path. Charge/report both runs;
no timing/variance/quality advantage may be inferred from this diagnostic work.

Retain every per-pixel/per-vertex ray origin/direction, hit t/id/front, unnudged/
nudged/spawn positions, oriented normal and direct reflected RGB. Record misses
explicitly and unvisited slots as exact zero. Produce original components and
extracted Li/PDF/SDK-M/trial/status records with full binary layouts/manifests.
No candidate images or hits are injected into a GPU or current Renderer.

New CPU tests must exercise observation inverse, actual new native original/
instrumented parity on analytic fixtures, B2/B8 suffix counts, misses versus black
hits, sky, opposite normals, receiver origin/PDF recovery, positive PDF, complete
array corruption detection and exclusive intake/order/stop behavior. Reuse old
successful compiler/runtime/process-limit artifacts and tests WITHOUT rerun.
Use the qualified compiler; compile only new native source/generated derivative
and new tests, with no-fast-math/ffp-contract-off and UBSan. Native execution must
work under unusable Vulkan ICD paths and must not initialize Vulkan.

CPU preparation at most THREE exclusive attempts, each correction committed
before use; successful unchanged steps must be reused. Stop the study on the
first actual path/numeric/provenance/timeout failure, with no retry or later scene.
Build correction is permitted only before any path acquisition. No sample-count,
seed, tolerance or semantic rescue after observations. Use existing032 process
guards: one BLAS/OMP worker, parent soft360/hard1200CPU/4GiB/core0/default unblocked
SIGXCPU. Native case CPU1200/wall1800/4GiB; build/tests CPU120/wall180. Independent
audit per case CPU1200/wall1800/4GiB; stop/order require previous audit PASS.
Keep16GiB free before each case and all outputs exclusive under repository out/.

## Independent full-record audit and decision

Audit ALL230,400 paths/case and every allocated B vertex slot, not samples. Check
input/overlay/compiler/dependency/full payload hashes and committed identities;
original baseline versus observer component/primary/RNG/counter byte parity;
complete shape/visited prefix/miss/unvisited zeros and finite/nonnegative fields;
ray endpoint O+tD, normal orientation, geometric/nudge/spawn relationship and
actual consecutive original rays. Independently reconstruct Li from per-vertex
direct values with math.fsum/NumPy, all three RGB channels; compare original
indirect. Original path prefixes are the physical authority here. Do not describe
this as independent retracing of every recorded intersection/shadow ray or GPU
verification. Subsequent GPU bridge still requires those stronger controls.

Require bit-exact original/instrumented primary/direct/components/counters/RNG;
exact integer flags/counts/M/trials/unvisited fields. Require double extraction/
shading/endpoint/normal/PDF recovery rtol1e-10,atol1e-12. No finite fake endpoint
for a miss, no normalization by hit count. Retain all recovery/error/state arrays
and complete zeros. Any nonfinite metric or failed condition invalidates the case.
Only all SIX independently audited cases admit CPU_PHYSICAL_CANDIDATE_EXTRACTION_PASS.
This admits CPU extraction semantics, NOT a ReSTIR image quality baseline, float32
packing, arbitrary reuse/unbiasedness, GPU runtime/timing/memory or novel transport.

The next actual image-producing ReSTIR GPU bridge must generate suffixes on-device,
apply these status/trial semantics, independently qualify real BVH/offset/visibility/
two-sided/primary/direct/packing/current-invalid/previous motion and owned lifetimes,
then separately preregister cold AND warm all-seed HDR quality/fair family costs.
Never claim speed from unmatched quality;022 raw-PT-only ranking remains forbidden.
Full charter remains novel competitive Renderer transport, fair representative
families, independently NEW heldouts, full dynamic/churn, broad scenes and GPU
classes/deployability, calibrated complete costs and persistent/true-peak memory.
No CI/Actions, global power/clock/desktop changes, main promotion or old retries.
Commit/push all results/failures and update OPEN Issue7; Lane M remains incomplete.
