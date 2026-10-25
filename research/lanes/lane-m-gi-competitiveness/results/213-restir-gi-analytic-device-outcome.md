# ReSTIR GI034: analytic GPU storage and history controls pass

**ANALYTIC_GPU_RUNTIME_CONTROL_PASS** for both ordered dimensions,17x9 and320x180.
The exact six033 SPIR-V variants run on AMD Radeon8060S Graphics(RADV STRIX_HALO).
Both complete independent CPU audits pass ALL384 saved snapshot pairs and
11,088,576 pixel occurrences. This qualifies these analytic runtime controls,
not M001 physical GI, image quality, matched-quality timing or novel transport.
Lane M remains incomplete and Issue7 remains OPEN.

[Preregistration034](../experiments/034-restir-gi-analytic-device-controls.md)
committed5080ffd5 precedes implementatione444d4cb, input generation, build/tests
and both acquisitions. [CPU preparation211](211-restir-gi-analytic-device-cpu-preparation.json),
[both complete results212](212-restir-gi-analytic-device-two-dimensions.json),
[preservation214](214-restir-gi-analytic-device-verification.json).

One standalone host compiles/links once against exact033 SDK host objects; no
SDK, shader or old successful test compilation/execution repeats.10 new CPU
contracts pass. Both native --cpu-check inputs execute under unusable Vulkan ICD
paths without Vulkan initialization. Full SPIR-V80-byte Controls layout,32-byte
packed reservoirs,48-byte surface/secondary strides and8,192 signed8-bit original
neighbor offsets match. A relative build-path argument is rejected BEFORE first
plan creation/GPU launch; its record is retained in out/. The same successful
build's absolute path resolves intake without changing code/data or rerunning a
build or experiment. No GPU, numerical or provenance failure occurred.

Exactly TWO GPU processes, with48 configurations each: eight frozen fixtures
(visible constant, visible grey ramp, black/miss, blocker, wrong oriented
hemisphere, empty previous surface, material mismatch, age boundary) ×six SDK
variants. Each executes MAKE seed, cold, GPU history copy, warm, full reset/MAKE,
reset output:480 compute dispatches+96 device copies total.17x9 full audit passes
BEFORE320x180 plan creation; the second plan pins the actual first audit receipt.
There are no retries. Fence250ms/native CPU120/wall180/4GiB/2ms unit pauses and
256MiB owned allocation cap apply. Parent soft360/hard1200/4GiB/default unblocked
SIGXCPU and actual child limits/PID/exit are saved. Power/clock/desktop settings
are unchanged. Diagnostic timestamps are preserved and not admitted for ranking.

CPU audit recomputes complete RNG neighbor indices, eligible candidate M/age,
stream weights, bias correction normalization and diffuse RGB for the fixed
uniform geometry. It independently decodes packed RGB and requires a legal
selected candidate with correct endpoint/normal/age/weight/RGB/packing diagnostic.
All guard bytes, padded reservoir addresses, source copies, output padding,
readonly inputs and cold/reset full bytes pass. All black/blocked/wrong-side RGB
is exactly zero. Registered tolerances remain unchanged. Full per-pixel state,
eligibility, membership, errors and candidate arrays are saved, without sampled
inspection. This is not a general RIS selection probability or unbiasedness proof.

| Dimension | Configurations | Audited pixel occurrences | Owned true peak | Teardown |
|---|---:|---:|---:|---:|
|17x9|48|29,376|82,416bytes|0|
|320x180|48|11,059,200|14,092,480bytes|0|

Each process's ten actual vkAllocateMemory lifetimes are replayed independently;
all allocations and frees balance. This covers owned memory of this isolated
host, excludes driver-private/CPU memory and is not a memory superiority result.
Raw data, guard-complete buffers, logs, plans, dependency/input/payload hashes,
allocation journals and complete CPU audit arrays stay in ignored repository out/.
No raw GPU data or external SDK copies are added to Git.

Remaining gates include real finite B2/B8 suffix production, actual primary/direct
and two-sided geometry/BVH/offset/visibility semantics, physical radiance/packing
agreement, current-invalid/checkerboard GPU handling and previous geometry/motion.
Only then can a separately registered same-quality family comparison use actual
image-producing workloads and complete end-to-end timing/memory. No current
Renderer/CMake/default graph/main or N001–N010 history changes; default Renderer
build/runtime NOT_RERUN and validation layers NOT_RUN.033 remains immutable CPU
source qualification;034 supplies the new GPU evidence separately.032's six
quality losses and029/031 stopped failures remain preserved.

Full charter still requires novel competitive Renderer light transport, fair
representative RC/DDGI/cache/ReSTIR/PT-family comparisons, independently new
heldouts, camera/light/rigid/deforming/topology/churn, broader scenes/Sponza,
multiple GPU classes/deployability and calibrated full costs/persistent/true peak.
022 forbids an accepted raw-PT-only speed ranking. New GPU acquisitions2; audited
assistant cumulative186. No physical/HDR quality, speed or architecture admission.
