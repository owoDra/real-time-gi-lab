# NRD native Vulkan guide and runtime controls024

2026-10-24, baselinec43dbea2. Previous goal turn made progress:023build/API
qualification passed with two immutable failed CPU audits. Lane M remains
incomplete. This registration precedes024code/build/new CPU contracts/GPU.

## Question, fixed boundary and sources

Can the unchanged source-pinned RELAX_DIFFUSE SDK execute with physical PT
inputs on the available Vulkan device, with correct actual guides, shader
bindings/synchronization, real continuing histories, exact explicit reset and
complete bounded ownership? This is native integration correctness, not
quality-family admission, accepted timing or novel architecture acceptance.

Reuse023NRD4.18.0e06852bd, ShaderMake3f01623a, MathLibaa432ad9,
DXC1.9.2609, complete static library and default SDK SPIR-V/packing shader.
Do not rebuild successful023/022or rerun their CPU/GPU cohorts. Pin old receipts,
all reused objects/dependencies, source bytes and exported pipeline bytes.
Keep all default algorithm/feature settings and023CommonSettings/camera rules.
Actual numeric ResourceType enum is authoritative; preserve the SDK's known
incorrect diagnostic strings. No SDK source/settings/filter math changes.

Implement a separate opt-in native adapter, not the default Renderer/CMake.
Reuse original physical N010PT and022bounded private allocator/HWRT, with
exactly reversible additive023guide/024diagnostic exports. Keep original RNG,
transport, sample order, cosine directions, radiance and direct unchanged.
Export first-secondary origin per pixel and direction/clamped hit distance/
canonical primitive per pixel/sample from the already executed query. Primary
miss exports zero samples; secondary miss uses65504/invalid primitive. No
extra random draws or rays. Export original secondary sum/mean; independently
recompute float32 sample-order sums/means and validate every active first-
secondary ray against original physical triangles on CPU. This is auditing
actual saved rays, not new reference/path sampling. Metadata distinguishes
nominal viewport*spp slots, actual hit-pixel sample iterations and uninstrumented
hardware query count. Record all buffers/images and full data under out.

GPU packs actual primary normal/t, linear indirect radiance and in-lobe mean
secondary distance using unchanged023official-helper shader; positive viewZ,
world-space unit normal, roughness1/material0, zero static motion, miss depth
2*far. Input error flags must all be zero before SDK sanitization. Actual
homogeneous rho1/zero-specular material factor1. Keep direct separate and add
it to official RELAX-unpacked RGB on GPU. Capture full RGB, never infer grey
output or exclude any pixel. No CPU image/primary/guide upload or inter-stage
readback; diagnostic frame/pool readbacks occur only after GPU composition.

Create native descriptor/pipeline/pool layouts from the real SDK API. Respect
set0resources/set1constants+samplers and actual offsets. Use actual recommended
pool formats/downsample factors, R10G10B10A2 normal, R32viewZ and RGBA32external
radiance/motion/output. Request/query required storage-image features and
format/descriptor/compute limits before allocation. Do not infer support from
configuration names:023selected pipeline bytecode has capabilities1/56 and no
OpExtension. Validate every new shader on CPU. Use GENERAL layouts with
explicit initialization and host/compute/transfer dependencies, correct sampled
vs storage descriptors, uniform constants uploaded before each bounded unit,
nearest/linear clamp samplers. Save pipeline identities, SDK dispatch/resource
records and exact constant bytes before SDK invalidates pointers. Compare
actual SDK schedules/constants to023frames0/1/64 for the corresponding camera.

## Actual CPU preparation, guards and acquisition order

Commit builder/adapter/overlays/CPU contracts/process/audit before executing
new checks. Reuse successful old numerical/SDK tests by pinned receipts, not
rerun. New CPU checks with unusable Vulkan ICD cover actual CLI rejection,
exclusive paths, original state/camera metadata, descriptor/format/resource
mapping/shape/range, per-sample buffer overflow, shader inverses/reflection,
process order/intake/partial-output/failure/no-retry predicates, ownership and
sample-ray oracle fixtures. Native --cpu-check must not initialize Vulkan.
Run all applicable CPU build/tests/audits before the first GPU plan.

Three controls in fixed order, each one GPU process; independently audit its
terminal data before selecting the next. Each original320x180canonical state:

1. H01/T_B2,16spp.
2. H02/T_B8,64spp.
3. H03/T_B2,64spp.

Each process has one SDK/device/AS/owned pool and exactly three full frames:
iteration0/frame0/CLEAR seed305419896; iteration1/frame1/CONTINUE
seed2654435769; iteration2/frame0/CLEAR seed305419896. Explicit60Hz, identical
static physical geometry/light/camera. No artificial per-frame clear on the
continuing frame. Repeated frame0 is an intentional reset control, not an
identical retry. First/reset raw PT must be bit-identical to022same-depth/spp
and to each other; first/reset guides/pool outputs/RGB must be bit-identical.
Continuing frame must preserve history resources and contain nonzero updated
radiance/history-length state. Full64frame warm quality is not claimed here.
All three frames, outputs/pools/failed attempts are saved without overwriting.

One worker/host thread,4GiB CPU address-space cap,120CPU/180wall seconds per
native process/ordinary CPU check. <=8GiB aggregate actual owned Vulkan memory,
checked before allocation including AS/vertex/instance/scratch/staging and
all buffers/images; persistent/true-peak ledger and zero completed teardown.
Original private context/HWRT and every new unit fence bounded250ms, no
unbounded GPU wait. On incomplete fence persist failure/live ownership and
terminate without claiming teardown or resubmitting. Producer chunks<=128pixels,
individual SDK/packing/composition/copy dispatches separately bounded,2ms
inter-unit pause. Save individual timestamps and complete frame envelope
including synchronization/pauses, allocation/AS/pipeline/upload setup and
readback diagnostics. All are DIAGNOSTIC_UNCALIBRATED, not accepted time.
No clock/power/desktop setting changes. No simultaneous research native process;
check live processes and >=16GiB disk before each launch. Announce exact one
command, then execute under the user's standing GPU authorization.

## Independent gates, failure classification and stop

NATIVE_NRD_GUIDE_RUNTIME_PASS requires all three terminal controls, not just a
pipeline creation success. Rehash complete physical/frame/camera/source/build
and023evidence. Require all57,600primary records with original CPU-oracle
presence/primitive/depth bounds (unchanged013bound max(1e-4,1e-5*abs(t))), unit
normal/canonical material metadata, and exact first/reset original PT bytes.

For every active first-secondary ray, independent double triangle intersection
uses saved float32 origin/direction, self-primitive exclusion, original physical
triangles, tmin0/tmax1e30 and closest hit. Zero hit-presence/canonical-primitive
mismatches; hit-distance error <=max(2e-5,32float32ulps(t)), with the same65504
clamp for the exported guide. No ambiguous-ray exclusions. Require unit in-lobe
rays, finite/ranged per-sample distances, exact float32 sum/mean replay, miss
conventions, and preserve full errors/expected IDs. Reset rays are checked
byte-identical and reuse the first physical ray audit, not repeat identical
intersection work. Independently check packed float guides and positive viewZ
against actual raw fields; R10G10B10A2 UNORM quantization <=1LSB, all input
error flags zero, motion0. Float guide tolerances: max(2e-5,16ulps(expected));
radiance/mean pack must be exact float32 (all finite in representable range).

All pools/final RGB must be finite, relevant radiance/history fields nonzero,
SDK schedules/resources/constants match023; reset full output/state bytes
exact; full owned allocation lifetimes/fences/timestamp arithmetic reconcile.
NRD formatting/ownership/shader/input/timeout/API/oracle failures are
IMPLEMENTATION_OR_RUNTIME_FAIL, not image-quality family losses. Stop whole
GPU cohort on first failure; do not silently retry or advance a failed control.
A specifically identified implementation/ABI repair with unchanged science
requires a committed new version and fresh outputs; SDK/algorithm/config/
threshold changes require a new registration. Preserve failures and valid
completed captures. No historical source/evidence/default build graph changes,
Actions/CI, main promotion, reference regeneration or raw data in Git.

End024after three passes or first failure. Publish compact results/verifier,
commit/push research branch and update Issue7OPEN. Next separately freeze fair
static/cold AND64frame warm quality cohorts with independent per-frame seeds,
all guide/history costs and original all-pixel physical-reference gates; then
actual-boundary calibrated full-system timing/memory comparisons. New heldouts,
all dynamic regimes/Sponza/representative devices/deployability and a novel
competitive light-transport architecture remain mandatory. Lane M stays active
and incomplete; established NRD/quadratic filters are not novel architecture.
