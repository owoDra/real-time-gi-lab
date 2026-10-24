# NRD027: saved-input semantic boundary audit

2026-10-25, baseline209af1d5.026 is complete:24 valid acquisitions/1536
frames, zero joint quality passes. Preserve all original scores, sources,
settings, accepted/failed evidence and registrations. This protocol precedes
new audit implementation, tests, SPIR-V member reflection and numerical
reconstruction. Read-only official source/metadata inspection precedes it.

Question: do the actual026 SDK constants and guides describe the same static
camera-relative primary surfaces, normals and diffuse transport as the
physical producer, under the pinned official input conventions? This is a
supplemental eligibility audit, not another quality acquisition, tuning study,
NRD-family rejection or timing experiment. No GPU or new SDK API invocation,
compilation, path/reference sampling or original quality-metric rerun.

## Source facts and scope fixed before execution

Use all six targets and all24 rungs in163's exact order. Reuse026's physical,
full-field/packing/SDK/history/lifetime/error/quality audits and165 preservation
receipt after checking their identities. Rehash every consumed native/audit
receipt and binary against its accepted payload manifest; do not present this
as another full raw-cohort replay. No old evidence is rewritten.

Pin official NRD e06852bd545973cb224eb28820b891205cfc1624 README,
Include/NRDDescs.h, Include/NRDSettings.h, Shaders/NRD.hlsli,
Shaders/RELAX_Config.hlsli, Shaders/RELAX_Common.hlsli, Source/Relax.cpp and
Source/InstanceImpl.cpp, and the actual library/producer/packing/source identities.
The official README's diffuse many-path example averages first-secondary
distance over diffuse paths. Every path here is diffuse, cosine sampled; a
miss contributes65504. No probabilistic lobe skip, MIS/RIS or specular lobe.
The physical grey rho1/zero-specular BRDF makes its diffuse material factor1;
inserting a Fresnel term from a different material model would change transport.
Linear RGB, direct kept separate, world normals, roughness1/material0,
positive viewZ, static motion0 and sky beyond denoising range remain fixed.

Source inspection also identifies a settings-to-constant discrepancy:
Source/Relax.cpp assigns gLuminanceEdgeStoppingRelaxation from
settings.roughnessEdgeStoppingRelaxation (default1), while the similarly named
luminanceEdgeStoppingRelaxation setting defaults0.5. Audit the actual mapping;
do not silently repair it or claim it caused026's losses.025 changed only the
disclosed sky material initialization, not this host assignment. This fact is
known before execution and is not a preregistered prediction of image impact.

Official source: https://github.com/NVIDIA-RTX/NRD/tree/e06852bd545973cb224eb28820b891205cfc1624

## New checks and fixed numerical gates

1. Reflect the real15 selected SPIR-V binaries, including descriptor set1/
   binding2 constant-buffer identity, member names/types/byte offsets and matrix
   stride/major decorations. Do not assume C++/HLSL layout. All13 RELAX
   pipelines must expose the required common members; the two Clear pipelines
   are separately identified and never decoded as RELAX common constants.
   Require identical reflected layouts/pipeline bytes across all24 captures.
2. Decode every actual SDK constant record:651/process,15624 total. All640
   RELAX records/process (ten/frame) must satisfy the static rectangle, origins,
   camera-relative geometry, motion/jitter, denoising range, viewZ scale and
   registered default settings. Eleven initial Clear records/process are
   counted and bound, not reinterpreted. Verify each record equals its existing
   accepted025 CPU counterpart. Require exact static geometry-member bytes
   within each cell across depths, budgets and frames. Default history constants
   are0 at CLEAR and30/6 afterward; source gHistoryFixFrameNum is3+1. Decode
   prepass30, phi-luminance2, base/alternate history stride14, threshold3,
   minimum hit-distance weight0.1*2, and the disclosed constant1 discrepancy.
3. At frames0,1,63 of every acquisition, pin camera/hits/viewZ/normal/motion
   guides. Require their bytes to equal the first instance of that cell:
   static primary geometry is independent of depth/spp/seed. This establishes
   coverage of72 saved frame instances without recalculating identical maps.
   Compute and preserve three distinct full-frame geometry error archives.
4. From actual reflected gFrustumForward/Right/Up and gRectSizeInv, evaluate
   the official camera-relative position reconstruction for every primary hit.
   Compare with original camera ray times the actual producer primary t.
   Each coordinate error must be <=max(2e-5,32 float32 ulps of the absolute
   expected coordinate). Project those independent physical points with the
   actual reflected gWorldToClip AND gWorldToClipPrev matrices; require
   maximum absolute x/y NDC residual<=2e-5, positive homogeneous w and depth
   in[0,1]. Static current/previous geometry must agree. Sky pixels remain
   explicitly counted and must have viewZ beyond the range. This is a guide
   eligibility domain, never an HDR scoring mask.
5. Independently decode the actual packed10-bit normals using the upstream
   convention, normalize, compare each hit to the producer normal with maximum
   coordinate error<=4/1023, roughness exactly1 and material exactly0. Motion
   is exactly0 for all pixels. Save full decoded normals and errors.
6. Freeze source-contract checks for first-secondary/cosine/all-diffuse averaging,
   identity material modulation, linear official RELAX packing/unpacking and
   direct composition. Reuse the already audited per-sample/sum/mean/guide
   results instead of repeating236million witnesses or quality/reference work.
   Identify source/default evidence and limits for each conclusion.

Before auditing actual constants/positions, commit new auditor and tests.
Run meaningful malformed-SPIR-V/binding/layout/offset/major rejection tests,
independent known projection and Y-flip/transposition controls, decoded-normal/
material/roughness corruption controls and manifest/overwrite checks. No
synthetic test is described as GPU or new physical image evidence.

## Classification, resources and stop

SEMANTIC_BOUNDARY_PASS_CONFIGURED_QUALITY_FAIL_RETAINED requires every check,
all24 captures and the3-cell/72-frame identity proof. It adds no image PASS,
optimal-parameter/family-wide claim, accepted timing or architecture promotion.
SEMANTIC_BOUNDARY_FAIL_PRIOR_NUMBERS_DIAGNOSTIC records numerical/guide
contradictions, preserves026's exact numbers and stops new GPU continuation
until a separate registered correction. Unsupported parser/provenance/process
failure is AUDIT_IMPLEMENTATION_OR_PROVENANCE_FAIL, not a scientific loss;
preserve failure outputs. An identified audit-only repair needs committed code
and a new exclusive output; no GPU retry or post-hoc gate change.

One CPU worker,240 CPU/360 wall seconds,4GiB address space; all auxiliary/raw
outputs under repository out/, no overwrite. No old successful suite/build/
cohort rerun, GPU process, default build graph, N001–N010, CI/Actions, power/
clock/desktop change or main promotion. Publish results, update current summary/
index/Issue7 and commit/push the research branch; report Renderer build/runtime
regression and validation layers NOT_RUN/NOT_RERUN as applicable.

## Next decision and full objective

022 explicitly forbids admitting a speed ranking against raw PT alone. The
previous next-step wording about PT/022 is therefore preparation for boundary
calibration/component diagnostics, not sufficient architecture competition.
No matched-quality NRD timing target exists under026. Do not rank its failed
images as a faster equivalent. A changed baseline setting or corrected constant
mapping needs a new prospective study, preserving defaults and all losses.

Use the semantic audit to choose a defensible next baseline/candidate study,
not an indefinite series of unbounded parameter searches. Any complete-cost
timing method still needs architecture-neutral actual-boundary calibration,
fixed pair/order/multiplicity/process counts, practical ratio1.20, all startup/
tracing/allocation/update/history/conversion/fitting/sync costs and true peak.
Novel competitive image-producing Renderer transport, representative families,
independent new heldouts, dynamic regimes, Sponza/other scenes, multiple GPU
classes and deployability remain mandatory.027 cannot complete Lane M.
