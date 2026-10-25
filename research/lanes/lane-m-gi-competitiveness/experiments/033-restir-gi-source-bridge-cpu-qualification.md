# ReSTIR GI source and analytic application-bridge CPU qualification

2026-10-25. Baseline6e6fad49. Registered BEFORE033 code, compilation, contracts
or dispatch.032 remains six quality rejections; no sample/anchor/pair rescue.

## Question and source boundary

Can the ACTUAL pinned RTXDI ReSTIR GI host API and unmodified GI shader headers
be integrated through an explicit diffuse application bridge, compiled and
independently audited with correct PDF/normalization/Jacobian/visibility/history
and buffer contracts? This closes a missing representative-family prerequisite;
it is not a novel transport claim, a hand-written substitute for ReSTIR, a
qualified M001 baseline or a quality/timing experiment.

Pin official [RTXDI3.1.0](https://github.com/NVIDIA-RTX/RTXDI/tree/a6efab966b7c3b272da0461578eb56ac61c7cbff)
at a6efab966b7c3b272da0461578eb56ac61c7cbff and its EXACT Libraries/Rtxdi gitlink
[RTXDI-Library](https://github.com/NVIDIA-RTX/RTXDI-Library/tree/f12037fa8e97ebc08e9e3edfd2de528ed1772a4b)
f12037fa8e97ebc08e9e3edfd2de528ed1772a4b. Source inspection/clones before this
registration do not execute experiments. Repositories live in ignored repository
out/external/rtxdi-a6efab96033 and out/external/rtxdi-library-f12037fa033. Preserve
all tracked source/license/docs bytes and Git trees; no submodule/asset downloads,
SDK edits, generated API mirror presented as SDK, or default build integration.
Use the existing qualified DXC1.9.2609 executable/dependencies and spirv-tools;
hash identities, don't reinstall or repeat successful old SDK/shader studies.

[Official GI integration](https://github.com/NVIDIA-RTX/RTXDI/blob/a6efab966b7c3b272da0461578eb56ac61c7cbff/Doc/RestirGI.md)
and [API reference](https://github.com/NVIDIA-RTX/RTXDI/blob/a6efab966b7c3b272da0461578eb56ac61c7cbff/Doc/ShaderAPI-RestirGI.md)
define the bridge and resampling boundary. ReSTIR GI2021/GRIS2022 are prior art.
The existing031/032 common-RNG difference estimator is not this algorithm.

## New executable checks (CPU only)

Commit new host fixture, HLSL fixture, analytic bridge/math and tests/build runner
BEFORE executing them. Private manual C++20 build links actual ReSTIRGI.cpp and
RtxdiUtils.cpp. Exercise dimensions1x1,320x180,321x181, all three checkerboard
modes, all five GI resampling modes, frames0..63 (2,880 API states). Independently
verify padded16x16 buffer addressing, no within/among-array overlap, two-reservoir
32-byte ABI/member offsets, bounds/bytes, frame/history routing, actual defaults
and setter/getter roundtrips. Call actual SDK FillNeighborOffsetBuffer once for
8,192 entries, retain all signed-byte offsets, validate complete bounded coverage.

Compile six compute permutations through actual unmodified shader headers:
MAKE/pack/unpack, SPATIAL_BASIC, SPATIAL_RAY_TRACED, TEMPORAL_BASIC,
TEMPORAL_RAY_TRACED, FUSED_RAY_TRACED. Validate EVERY SPIR-V and inspect actual
entrypoints, resource layout and retained calls via disassembly. Use Vulkan1.2,
cs_6_5, explicit storage bindings, one worker. All permutations retain input
dependence and observable output; synthetic input bridge is not real geometry.
No GPU execution: shader semantics and physical ray behavior remain NOT_RUN.

The synthetic bridge exposes current/previous surface buffers, raw secondary
position/oriented-normal/radiance/solid-angle PDF, packed reservoirs, official
RNG and neighbor offsets. It uses unit diffuse rho/pi target/shading, official
Jacobian validation policy (reject outside[.1,10], clamp[1/3,3]), finite positive
source PDFs, black misses with M preserved, explicit previous-frame selection,
and an analytic plane-occluder visibility fixture. It MUST NOT return unconditional
visibility or be usable as a production M001 scene bridge. Both basic and traced
bias-correction variants compile so visibility paths cannot silently disappear.
Final shading carries explicit BRDF*cosine*Li*weight; no missing cos/pi/PDF or
extra inverse-distance-squared radiance attenuation.

New independent CPU analytic contracts cover no-resampling equality, inverse
solid-angle PDF, two-sample exact-enumeration RIS normalization including target
in denominator, zero/black samples with preserved M, nonuniform candidates,
Jacobian identity/reciprocal/distance and grazing/zero invalid support, published
clamp boundaries, finite/nonnegative radiance, plane visibility/blocker segment
bounds, depth/material/normal/surface validity, previous-frame isolation, finite
B2/B8 remaining depth and oriented two-sided hemispheres. These are independent
analytic/adapter checks, NOT execution of SDK HLSL on CPU or proof of physical
path retracing. Report actual count, not a planned PASS count.

## Interpretation, limits and stops

PASS requires ALL actual host states/address checks, new analytic contracts,
source/gitlink/compiler/dependency/inventory identities, six compiled+validated
permutations, resource/disassembly checks and exact independent audit. Classify
CPU_SOURCE_BRIDGE_COMPILE_PASS only at that scope. All arrays/host parameter rows,
offsets, binaries/SPIR-V/disassembly/logs/dependency/phase manifests stay in out/.
Save each command before executing and inputs on errors. Exclusive outputs
out/research/lane-m-gi-competitiveness/m001-restir033-cpu-build-vN. At most three
prospective CPU scaffold/build/API fixes, each committed BEFORE the next attempt,
retain every failed byte and reuse exact successful compile outputs without
rerun; no scientific parameter search. Stop if third attempt fails or an SDK
algorithm edit would be required. One sequential worker; parent soft360/hard1200
CPU,4GiB/core0/default unblocked SIGXCPU; each child CPU120/wall180/4GiB. Wrapper
wall1200,16GiB free-disk guard. Reuse032 qualified process limits without rerunning
its tests. Timeout/failure kills/reaps same process group, never observation retry.

No M001 geometry/radiance/reference decode, new path/reference samples, image
quality scoring or GPU dispatch is selected. In particular finite-depth suffix
consistency, direction-independent secondary radiance with the ORIGINAL two-sided
materials, actual BVH/offset/conservative endpoint visibility, primary/direct
equivalence, full raw contribution/packing error, reset/history/previous geometry,
all allocation/synchronization and persistent/true-peak memory MUST be qualified
before real-scene quality. The analytic fixture cannot prove those. Subsequent
runtime/physical controls and quality require separate falsifiable registrations,
original all-pixel/four-seed gates, fair cold AND warm histories and full costs.

This study supplies no GPU time/memory advantage, calibrated matched-quality
comparison, novel architecture or Lane M completion.022 still forbids accepted
raw-PT-only speed ranking. Full charter includes actual novel Renderer transport,
fair representative families, independent new heldouts, dynamics/churn/Sponza,
multiple GPU classes, deployability and complete calibrated costs/true-peak memory.
No N-history/main/default Renderer/build/CI/Actions or power/clock/desktop changes.
Publish checks and limitations, commit/push and update OPEN Issue7.
