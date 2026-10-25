# ReSTIR GI analytic device and storage/history controls

2026-10-25. Baselinef8f35862. Registered BEFORE034 implementation, fixture
generation, build/tests, CPU expected outputs or GPU execution.033 ends at
CPU_SOURCE_BRIDGE_COMPILE_PASS; reuse exact qualified binaries/headers/SPIR-V,
API states, offsets and18 analytic tests without recompiling/rerunning them.

## Question, scope and exact boundary

Do ALL SIX byte-exact033 SDK shader variants execute with correct diffuse
analytic contributions, packed reservoir state, candidate eligibility/history
normalization, whole-buffer bounds, reset determinism and owned lifetimes?
This is actual GPU SDK bring-up, NOT M001 physical geometry/quality/timing or
novel architecture. Original finite B2/B8 secondary path production, real BVH/
offset/visibility/two-sided physical agreement remain a later gate; this fixture
traces only its synthetic bounded plane. It does not qualify an entire family.

Preserve [033](033-restir-gi-source-bridge-cpu-qualification.md) and all its
official source pins, original compiler/dependencies and six exact v3 SPIR-V.
No official/application HLSL edits or new shader compilation in034. New isolated
Vulkan host, CPU fixture/model, build/plan/audit/tests are committed BEFORE use.
Manual host compile only; reuse exact033 SDK host objects/headers and historical
allocation ledger (read-only). No default Renderer/CMake/main/N-history changes.

## Fixed ordered controls and execution

Two dimensions IN ORDER:17x9 then320x180. One exclusive GPU process per dimension,
second allowed only after full independent first audit PASS. Exactly eight
analytic fixture types, each all six variants in033 order:

1. visible constant unit RGB;
2. visible unit-grey ramp Li=1+(linearPixel mod4);
3. black/miss Li=0,PDF=0,valid receiver and defined endpoint/normal;
4. blocked receiver/end segment through the fixture's bounded z=.5 square;
5. opposite oriented secondary hemisphere;
6. previous surface EMPTY (ALL zero fields, matching RAB_EmptySurface);
7. previous material differs from opaque current0xffffffff;
8. age boundary maxReservoirAge=1 (others30).

All CURRENT receivers valid, depth1,normal+Z,opaque material0xffffffff. Visible
receiver(1,0,0),secondary(1,0,1),normal-Z; blocker fixture uses x=0 for both.
Wrong-side fixture flips secondary normal+Z. Raw sourcePDF=1/pi except black0;
Li as above, no emissions/masks/tone mapping. Other original host defaults
numSamples2,radius32,depthThreshold.1,normalThreshold.6,history8 remain fixed;
fallback enabled, permutation disabled, no checkerboard. Fixture8 changes only
age. CHECKERBOARD_GPU and invalid-current G-buffer paths are NOT qualified:
the exact033 fixture lacks a checkerboard invocation mask and assumes valid
shading receivers. Do not silently infer those from033 CPU API addressing.

For EACH fixture/variant, clear entire owned buffers, upload registered inputs,
and seed source array0 using actual GPU MAKE/pack. Run cold(frame0,source0,out1),
copy array1 to0 on GPU, run warm(frame1), then full clear/restore/MAKE seed and
reset(frame0). Fixed five dispatches and one device copy per configuration;
48 configurations/dimension ->240 dispatches+48 copies,2 GPU processes total.
All seed/cold/warm/reset full packed arrays/results and immutable input records
are retained. Intra-process intentional reset repetition is a declared control,
not a retry of an experiment. No CPU packing/upload of shader-produced history,
per-pixel reference, physical radiance data or image quality reference.

Source and destination arrays distinct during resampling. Explicit host/compute/
transfer/readback barriers, bounded fence250ms and2ms pause per submitted unit.
No workload batching past the declared unit or background queue. GPU timestamps
may be diagnostic only, all preserved, no speed selection/calibration. Selected
device exact AMD Radeon8060S Graphics (RADV STRIX_HALO); no power/clock/desktop
changes. Vulkan loader/device creation only in explicit --gpu branch, never in
--cpu-check or build/tests. One CPU worker, parent soft360/hard1200/4GiB/core0/
default unblocked SIGXCPU; native CPU120/wall180/4GiB. All owned vkAllocateMemory
lifetimes tracked, aggregate<=256MiB, teardown zero. Driver-private/CPU memory
excluded and stated. Wrapper wall600/16GiB free disk. On incomplete fence write
partial ledger and stop without teardown claim; never blocking device-idle rescue.

## CPU preparation and whole-data audit

CPU preparation MUST precede and announce each single GPU command. Rehash207/210,
033 v3 native/shader/dependency inventories, official Git sources and offsets;
no old successful execution repeated. Compile/link standalone host, execute new
native --cpu-check for BOTH full dimension plans under unusable ICD; reject
malformed options/outputs/metadata/byte sizes and verify exact input layouts.
New CPU tests exercise analytic source membership/normalization, RNG indexing,
packed-decode/ABI, blacklist/order/exclusivity, invalid input handling, actual
no-GPU native checks and durable manifests. CPU build-only corrections at most
three exclusive attempts, each committed first and successful artifacts reused;
SDK/shader changes require ending034 and a new registration. GPU/numeric/provenance/
timeout failure stops034 immediately, NO retry or second dimension after failure.

Use actual SPIR-V member offsets (Controls80 bytes),32-byte reservoir,48-byte
surface/secondary and original signed8 neighbor offsets in R8G8_SNORM texel view.
All buffers have256-byte leading/trailing canaries, full padded reservoir arrays,
unwritten array elements/output padding preserved, immutable input bytes checked.
Save complete guards and source/destination arrays, not sampled pixel dumps.

Independent CPU audit rehashes ALL inputs/payloads. Recompute full SDK RNG neighbor
indices and exact candidate eligibility/M/age rules for these fixed uniform
geometry fixtures; independently decode packed color and inspect selected sample
membership, complete stream weights, final normalization/RGB and packing error.
No claim of arbitrary-scene independent path tracing or general RIS probability
proof. All pixels/fields/guards and source/destination arrays are included.
Require finite nonnegative radiance/weights, exact integer M/age/normal/positions,
exact unmodified source/guards/read-only inputs and cold/reset bytes. Unpacked
RGB/weight relative tolerance3e-4,absolute3e-6; CPU packed-color decode relative
2e-5,absolute2e-6. Packing-only RGB error<=.02*max(input/output RGB magnitude,1e-6)
per channel, explicit diagnostic tolerance, NOT a change to original HDR quality
gates. Visibility/black/wrong-side require exact zero final RGB. History/material/
empty rejection and age bounds independently verified; denominator counts preserve
black candidate M. Full error/state/candidate/variance-free arrays saved in out/.

PASS only if BOTH complete acquisitions and all independent pixel/state/guard/
barrier/provenance/ownership/reset audits pass: ANALYTIC_GPU_RUNTIME_CONTROL_PASS.
No M001 quality, calibrated timing, memory advantage or architecture admission.
Full charter remains actual novel competitive Renderer transport, fair matched-
quality representative families, independent new heldouts, full dynamic/churn/
Sponza/device/deployability coverage, all costs and persistent/true-peak memory.
022 forbids accepted raw-PT-only speed ranking.032 retains six quality rejections;
029/031 stay stopped. No CI/Actions, old evidence rewrites or global settings.
Exclusive repository out/m001-restir034-* data/logs/manifests. Record actual GPU
process count including failed attempts, commit/push and update OPEN Issue7.
