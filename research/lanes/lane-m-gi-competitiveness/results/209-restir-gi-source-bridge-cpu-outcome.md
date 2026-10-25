# ReSTIR GI033: actual source/API and analytic bridge compilation qualified

**CPU_SOURCE_BRIDGE_COMPILE_PASS.** Official RTXDI host API executes once;
all2,880 states,463,172 complete array addresses,9 maps,8,192 actual SDK neighbor
offsets and483,022 native assertions pass.18 independent analytic contracts pass
once. All SIX actual SDK-header shader permutations compile and validate, with
independent full ABI/resource/call-graph audit. No SDK HLSL dispatch, M001 physical
input, quality result, timing/memory advantage or novel architecture is admitted.
Lane M remains incomplete.

[Registration033](../experiments/033-restir-gi-source-bridge-cpu-qualification.md)
was committed49e25ed7 BEFORE implementation13500733 or execution. Source/API build
fixesf12dd90c/3bec203a precede their new exclusive attempts.
[Qualification207](207-restir-gi-source-bridge-cpu-qualification.json),
[both failures208](208-restir-gi-source-bridge-preparation-failures.json),
[preservation210](210-restir-gi-source-bridge-verification.json).

The actual official RTXDI3.1.0 samplea6efab966b7c3b272da0461578eb56ac61c7cbff
and exact library gitlinkf12037fa8e97ebc08e9e3edfd2de528ed1772a4b remain byte-exact
in ignored out/external/. No SDK algorithm edits, substituted RIS implementation,
sample assets/submodules or default-build integration. Actual ReSTIRGI.cpp and
RtxdiUtils.cpp compile/link with the new host contract. Dimensions1x1,320x180,
321x181 ×all3checkerboard modes ×all5resampling modes ×frames0..63 are complete.
Defaults, actual getter/setter/history routing and32-byte packed member ABI pass;
independent Python recomputes every saved address and frame route, with no alias
or missing state. Maximum4,128,768bytes describes ONLY the two padded reservoir
buffers at321x181; it excludes all other resources and is not measured true peak.

| Actual shader permutation | Compiled | SPIR-V validated | Reachable SDK functions |
| --- | :---: | :---: | ---: |
| make | PASS | PASS | 26 |
| spatial-basic | PASS | PASS | 50 |
| spatial-ray | PASS | PASS | 50 |
| temporal-basic | PASS | PASS | 51 |
| temporal-ray | PASS | PASS | 51 |
| fused-ray | PASS | PASS | 53 |

Actual Vulkan1.2/cs_6_5 SPIR-V is compiled with the already-qualified DXC1.9.2609
and validated with pinned spirv-tools. Disassembly proves reachable official
Make/Pack/Unpack, each selected spatial/temporal/fused entry, actual Jacobian
and normalization calls, previous-frame visibility hooks and the packed host/
shader layout. Input-dependent buffers and final sample output remain observable.
These are compile/static proofs, NOT shader execution or physical correctness.

The app bridge is explicitly synthetic: current/previous surface buffers, raw
secondary endpoint/oriented-normal/radiance/solid-angle PDF, official RNG,
neighbor offsets, a bounded plane blocker and unit diffuse BRDF. It is not a
M001 geometry bridge.18 separate CPU analytic contracts verify no-resampling
cosine-PDF cancellation, distance-independent radiance, inverse PDF, exact
two-candidate RIS expectation including black M, nonuniform candidates, physical
invalid inputs, Jacobian identity/reciprocal/distance/grazing/wrong-side support,
official validation/clamp boundaries, segment visibility/endpoints, distinct
oriented hemispheres, B2/B8 suffix counts, surface rejection and previous receiver
isolation. This independent math is not execution of SDK HLSL on CPU, finite-RNG
unbiasedness proof, or a production physical path audit.

All THREE permitted preparation attempts remain in out/.v1 compiles the actual
host and passes2,880states/18analytic tests, but DXC -MD emits only dependencies:
zero return code produces no make.spv. The original console's PASS means only
command status; that attempt is INVALID, not a shader success. v2 separates
dependency emission and code generation and checks outputs; actual compilation
rejects an application-bridge struct-valued ternary unsupported by HLSL. v3
changes it to equivalent if/return; all six compile/validate/audit steps pass.
No official algorithm or scientific parameter changes. Each fix is committed
before execution. All three qualified host objects, linked executable, full
host arrays/offsets and18analytic results are exact-reused in v2/v3, never
recompiled/reexecuted. Each failure's actual commands/limits/PID/reaped exit,
inputs, logs and partial dependencies remain preserved. Historical source pins
are verified against the original Git commit, not falsely against revised files.

033 ends. Before any M001 quality or matched-quality ranking, separately qualify
real finite-bounce secondary suffix/radiance semantics, oriented two-sided
materials, actual BVH/offset/endpoint visibility, original primary/direct values,
float32/packing errors, all GPU buffers/bounds/barriers, reset/history/motion/
previous geometry and full allocation/lifetime accounting. Then preregister fair
cold AND warm image quality/all separate seeds; include any denoiser and every
tracing/reconnection/visibility/allocation/sync/update cost. None is silently
granted by this CPU compile phase. No next GPU/quality process is selected here.

ReSTIR is prior art and032 is not a ReSTIR reproduction. Full charter still
requires novel actual competitive Renderer transport, representative families,
independent new heldouts, camera/light/rigid/deforming/topology/churn, Sponza/other
scenes, multiple GPU classes, deployability and calibrated complete costs with
persistent/true-peak memory.022 forbids accepted raw-PT-only speed ranking.
032 retains six quality rejections;031/029 stay stopped. Incumbent SRC unchanged.

New GPU acquisitions0; audited assistant total184. No new path/reference samples,
GPU dispatch, N-history/default Renderer/build/main, CI/Actions, power/clock or
desktop changes. Default Renderer build/runtime NOT_RERUN; validation layers
NOT_RUN. Lane M and Issue7 remain OPEN.
