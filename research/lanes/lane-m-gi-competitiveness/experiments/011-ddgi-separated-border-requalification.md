# M001 prospective DDGI separated border correction and requalification

2026-10-23. Registered after050/051 discovered a concrete missing invariant and
before any corrected shader compilation or GPU acquisition. Supersedes runtime
admission from008/009 and blocks further010 execution. Original001/002/010
settings, references, measurements and all previous source/evidence bytes remain
unchanged. The old18observed quality failures remain archived and are not fair
family conclusions. This is an implementation correctness correction, not
estimator tuning from heldout errors.

## Falsifiable correction

Question: can a separately dispatched exact SDK border copy produce the required
same-probe interior values at every captured stage, without changing any interior
blend arithmetic, primary/direct semantics, finite-stage history or owned memory
constraints? Any invalid atlas, changed interior, unsupported configuration,
incomplete GPU unit, state/provenance drift or failed control rejects admission.
Quality thresholds, seeds, budgets, bias, grid spacing and scene inputs cannot
be changed to make this pass.

Keep the pinned official SDK checkout/archive, original kernels and hosts intact.
Generate a private version of `ProbeBlendingCS.hlsl` by removing **only** its
final group-barrier/border-copy block; keep the interior computation and its
early returns byte-identical. This removes the suspect shared-dispatch border
read and barrier, rather than leaving an invalid original path running and
patching its output afterward. Record exact original SHA256, unique replacement
span and inverse transformation proof. The SDK source remains immutable; label
the compiled derivative explicitly as modified SDK, never official unchanged.

Add separate irradiance8/distance16 border kernels using the exact SDK
corner/row/column mapping. Each invocation writes only one border texel from an
interior texel of the same probe/layer. No interior is modified, no border is a
source, no workgroup synchronization is needed, and there is one writer per
destination. Use existing SDK set0 bindings2/3 with matching F32x4/F32x2 data
formats. These kernels do not compute lighting, use a new sampler or change any
blend weight.

Generate private static/transition host copies with an exact reversible overlay:
load two new border kernels, capture irradiance/distance after interior-only
SDK blending, then dispatch the two copies before ordinary current capture,
next-stage reads and final gather. Use full compute write→read/write barriers
between producers and consumers over every array layer; account for transfer
readbacks as well. Retain all existing guards and whole-process180s limit.
Every new border dispatch must have its own begin/complete journal/fence and
diagnostic timestamp. Include actual kernel work in any future accepted timing;
do not subtract it as proof overhead. Pre-copy readbacks are diagnostic proof
overhead and require an explicitly different future product-boundary protocol.

Do not link these private sources or shaders into default Renderer/CMake. New
source/build/compile/plan/work/archive names must not collide with old evidence.
No retry/overwrite/automatic GPU queue, privileged power/clock settings or CI.

## CPU gates before any corrected GPU execution

1. Check all330SDK and10compiler files against original manifests, all original
   shader/archive pins, and exact old host/source hashes. Commit protocol,
   generator/compiler/builder, standalone shader and new runner/auditor/tests
   before their execution. Prove inverse overlays for SDK shader and both hosts.
2. Test independent golden border corners/rows/columns, all probes/layers and
   channels, one-writer/interior-only source constraints, corrupt/nonfinite and
   missing/extra captures, unchanged interior and no mutation of raw data.
   Source tests reject ambiguous edits and any altered interior math.
3. Compile six modified interior blend kernels (128/256/512 × irradiance/distance)
   and both border kernels with pinned DXC/coordinate2. Validate all SPIR-V on
   CPU and check exact descriptors/local sizes. Keep untouched ancillary SDK,
   reduction and TraceProbes/GatherPixels pins. Build isolated native host and
   execute its CPU contracts with unusable ICD, never infer Vulkan runtime PASS.
4. Test new process ordering, no run past failure, missing/drifted plans,
   timeout/partial preservation and overwrite refusal. Require original state,
   reference provenance, completed CPU receipts, committed inputs and16GiB free
   disk before each separately named GPU process.

## Fixed qualification inventory and order

First requalify all six008controls in their exact prior order/modes, grid4/128:
direct, black, unit, HDR8, scene-one/B2, scene-seven/B8. Then all eight009controls
in the prior light/geometry × fresh/transition × B2/B8 order, same derived states,
source/target/recovery/return and actual geometry/BLAS/TLAS updates. These are
development diagnostics with previously observed states, not new heldouts.

Then six H01 scene integrity controls, in q0/B2, q0/B8, q1/B2, q1/B8, q2/B2,
q2/B8 order, with exact010 budgets8³/128,16³/256,24³/512 and the same seed/settings.
They test all ray variants, multi-workgroup/layer borders and finite stages.
**Do not score indirect HDR against references during this qualification.**
At most20new named native processes; each requires its own prepared CPU plan,
one explicitly announced command and independent terminal audit before the next
allowed unit. No old operation can be reclassified or retried as one of these.

For every stage and both atlases require full bit-for-bit equality between the
captured post-copy array and a CPU expected array: start with pre-copy capture,
replace exactly the SDK border locations with same-probe pre-copy interior.
Every pre-copy border must remain freshly cleared zero. All interior channels
must remain unchanged. Also require the post-copy exact-border predicate and
all existing finite/layout/immutable previous-stage, physical state, constants,
coverage, direct/raw/PFM/composite, allocation and bounded-unit checks. Initial
previous arrays are all zero; later previous arrays equal preceding full current
arrays exactly. In a transition audit every captured frame separately.

Keep the existing constant0/1/HDR8 analytic values/tolerances from008 unchanged.
Scene B2/B8 stage0 rays, constants, irradiance, distance and probe data must
match byte-for-byte at each tested budget. Compare unchanged stage0 ray data,
irradiance/distance interiors and primary/direct output to corresponding old
captures to prove the implementation boundary; compare old borders only as
diagnostics, never as accepted expected values. Dynamic changed-state/recovery/
return must match corrected fresh/source captures as009 specifies. No temporal
accumulation/scrolling claim; reset-all remains the only supported history policy.

True peak owned allocation≤8GiB, persistent atlas identity, full allocation ledger
and zero teardown remain mandatory; CPU/driver-private exclusions explicit.
Performance is DIAGNOSTIC_UNCALIBRATED and never a speed claim. Any operational,
physical, copy or semantic failure stops the sequence; retain partial/failed
evidence and investigate before any prospectively named correction.

## Quality continuation and broader limits

Passing this inventory restores eligibility only for the registered finite-stage
reset-all implementation/configurations. It does not prove image quality,
general dynamics or a particular driver/compiler root cause. A later committed
quality-continuation protocol must identify this new implementation and all
new evidence roots, preserve old18cases, use unchanged010six-target/rung order,
references and all-image gates, and stop at first PASS/exhaustion/operational
failure. Do not reuse or silently replace old010scores.

Only a quality-matched pair may advance to the separate complete timing family,
actual-boundary GPU calibration, full costs and practical ratio1.20. Broader
dynamic/Sponza/representative-device strata, temporal limitations and unresolved
historical Sponza/direct/timing issues remain Lane M gates. This correction and
its controls alone do not complete M001/Lane M or promote an architecture.
