# NRD RELAX source, dispatch and guide CPU qualification023

2026-10-24. Baseline9f94c2c5. The previous goal turn made progress:022
qualified six newly produced static GPU images, but no fair standard denoised
baseline, accepted timing, new architecture or Lane M completion. This protocol
precedes023code generation/compilation/new CPU contracts or SDK API execution.
Read-only source acquisition/inspection and compiler archive retrieval precede
registration; neither SDK/compiler nor any new GPU workload has executed.

## Falsifiable question and frozen source boundary

Can the unmodified official NRD library with embedded upstream SPIR-V be built
and its RELAX_DIFFUSE dispatch/resource/constant/history API and required guide
production be made executable and independently checkable on CPU? This is a
necessary native Vulkan baseline integration step, not baseline runtime or
image-quality admission. No GPU process is authorized under023. No old022,
PT/reference/CPU/GPU cohort is repeated or overwritten.

Pin official repositories and every tracked source byte:

- NRD e06852bd545973cb224eb28820b891205cfc1624 (v4.18.0).
- Its upstream ShaderMake3f01623a76b092ac127d2debd79a672f55d77665.
- Its MathLib v11 resolved to aa432ad9a80691eb8c3ec4d576bbad5ac100fdc8.
- ShaderMake's specified DXC v1.9.2609 Linux2026-09-28 package,
  GitHub asset596911922, size13297763,
  SHA25696faadc7f5c282d2ffda49804beb4c3ee38127bc252b723234e3c5cdf7aa39a1.
  Preserve the first Python TLS retrieval failure (before archive creation),
  verified-system-CA curl retrieval, release metadata and archive/package bytes.
  Do not reuse or replace the historical1.7compiler package.

Source references: https://github.com/NVIDIA-RTX/NRD/tree/e06852bd545973cb224eb28820b891205cfc1624
and its README/CMakeLists/Include/Source/Shaders; ShaderMake and MathLib are
upstream dependencies, not candidate algorithms. Keep all large/source/build
raw assets under repository/out. No default CMake/Renderer integration, N001–N010
change, CI/Actions, ref rewrite or external quality/performance inference.

## Actual CPU implementation and checks

Commit exact new builder, API/guide contracts and tests before first execution.
Build a private byte-pinned source snapshot using upstream CMake targets and
ShaderMake arguments, supplying pinned local dependencies/compiler without
network fetch. Preserve all default NRD feature switches, normal encoding2,
roughness encoding1, performance modeOFF and quad intrinsicsON. Static library,
embeddedSPIRVonly, NRD_NRI=OFF choose native-API integration, not a modified
filter. All upstream shader families/permutations needed by the unmodified
library are compiled; RELAX_DIFFUSE is the only selected baseline role. Add
serial ShaderMake scheduling through the private build wrapper. Do not alter
upstream shader/estimator/settings math or silently disable required features.
Record compiler/link/build commands, source/config/dependency identities and
all logs. Validate every exported RELAX pipeline SPIR-V, inspect descriptor
sets/bindings/entrypoint/capabilities, preserve required Vulkan feature facts
for later device qualification. Compilation is not device support.

Use real SDK CreateInstance/GetLibraryDesc/GetInstanceDesc/SetCommonSettings/
SetDenoiserSettings/GetComputeDispatches/DestroyInstance with default
RelaxSettings. Keep diffuse/fast history30/6, five a-trous iterations,
anti-fireflyfalse, prepass30, checkerboardOFF/reconstructionOFF and all other
upstream defaults. Explicit60Hz timeDelta, unjittered original physical camera,
LH non-swizzled projection, positive viewZ and world-space normals. Derive
matrices from original canonical frame metadata; no reference/image guides.
Default algorithm settings must not be tuned on existing quality scores.

For each original H01/H02/H03canonical state, one CPU SDK inspection produces
64consecutive API frames (frame0CLEAR_AND_RESTART,1..63CONTINUE), then an explicit
frame0CLEAR_AND_RESTART. Capture every dispatch/resource reference, grid,
pipeline index and constant byte before the next SDK call invalidates it.
Export actual embedded SPIR-V, pool formats/downsample factors, bindings and
constant limits. Independently audit all references/constant sizes/grids,
required user resources, full pipeline exports, history ping-pong and exact
reset-to-cold sequence/constant equality. Actual GPU histories are NOT_RUN;
CPU API history tests cannot qualify temporal image behavior.

Pre-execution source clarification: RELAX_DIFFUSE declares no inter-frame SDK
pool-index swaps; it reads then writes six fixed permanent histories and cycles
the two transient illumination slots within its a-trous passes. Audit those
actual dependencies and cycling, rather than demand an invented frame-parity
swap. This preserves the unmodified upstream algorithm and the reset gate.

Implement/compile the prospective physical producer and packing boundary:

- Exactly reversible additive overlay on the original N010PT source, retaining
  original radiance/direct/RNG/cosine/sample/vertex order. Export primary
  normal/t and diffuse in-lobe hit distance from existing first-secondary
  intersections, with no extra random draws or traced paths. Per-sample first
  secondary distance excludes primary/deeper segments; a miss contributes
 65504. Clamp to[0,65504], average all spp in original sample order. This is the
  upstream simple diffuse many-path convention, not primaryt or path-length sum.
- Keep raw first-secondary-distance sum/mean and raw PT/primary diagnostic fields
  capturable for later independent GPU auditing. Metadata must distinguish
  nominal viewport*spp slots, hit-only sample-loop iterations and actual ray
  queries (not instrumented); no misleading executed-query count.
- Positive viewZ=t*dot(primary normalized view,camera forward), beyond-denoising-
  range depth for misses, static motion0, unit world normal, roughness1 and
  material0 for the physical homogeneous Lambert rho1/zero-specular scene.
  Diffuse material factor1 follows that actual transport; no invented Fresnel.
- Compile a packing shader calling upstream NRD normal/roughness and RELAX
  radiance/hit-distance functions. Keep new direct separate and unfiltered;
  radiance is linear RGB and actual outputs must later be scored as RGB luma.
  Assert finite/in-range inputs before any optional SDK sanitization can hide
  errors. CPU scalar/independent-double tests cover geometry/projection,
  hit-distance accumulation/miss/scale, packing/material/roughness/motion rules,
  including non-axis normals, non-square viewports and invalid data.

Use meaningful new real API and ABI/CLI/path/shape/range/nonfinite/overwrite
contracts with unusable Vulkan ICD, not synthetic evidence presented as GPU
results. Rehash accepted022and original physical inputs without resampling.
Do not rerun old successful math/cohorts merely as tests. GPU guide packing,
raw PT equality with new guide instrumentation, device feature/format/pipeline
support and all numerical/physical/whole-image behavior remain unqualified.

## Finite resource/stop and next boundary

Each new output is exclusive under repository/out. Host/compiler execution
uses one worker,4GiB address-space bound; individual ordinary CPU contracts
120CPU/180wall seconds. Full serial upstream compilation has finite1200CPU/
1800wall seconds and preserved stdout/stderr; report progress while it runs.
No automatic identical retry or output overwrite. Preserve failed CPU attempts;
an identified build/ABI implementation repair with unchanged science may use a
new version/output after a committed correction. An algorithm/source/config/
quality gate change requires another registration. Stop023after CPU result.

CPU_SOURCE_DISPATCH_GUIDE_PASS requires all registered compile/API/ABI/guide/
reflection/preservation checks; failures are CPU_IMPLEMENTATION_FAIL, not an
NRD family quality loss. No new reference/path sampling or GPU acquisition,
quality, accepted speed, GPU-owned memory or architecture promotion follows.
Publish compact outcomes, commit/push research branch and update Issue7.

Next separately preregister actual native Vulkan guide/device/runtime controls
before any GPU, preserving full feature/format/resource ownership/fence guards.
Then fairly freeze static/cold and temporal-warm histories with independent
per-frame producer seeds, all startup/conversion/history/update costs, and
original all-pixel quality gates plus actual-boundary calibrated comparisons.
Do not handicap NRD by resetting its history for every image or compare it only
against raw PT. NRD/default quadratic spatial filtering is an established
component, not the requested novel competitive GI architecture. New heldouts,
dynamic/Sponza/multiple-device/deployability gates remain mandatory. Lane M
remains active and incomplete.
