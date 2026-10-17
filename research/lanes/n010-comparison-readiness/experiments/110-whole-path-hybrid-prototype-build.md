# N010 prospective selected-pixel all-split hybrid build

2026-10-18 JST; parent7797c45. Before any generation/compiler invocation under
this plan. Prepared while259's sole original A6a seed0 CPU native continues.

## Why prepare this execution backend

The current low-priority one-core full-control acquisition is long. Existing
hybrid095 already has a Vulkan FP64/Int64 software-BVH path, deterministic
host accumulation and complete CPU recomputation of flagged samples. Those
mechanisms may accelerate the selected all-split sampler. They have NOT been
validated for that sampler; old098/099/101 do not transfer. This is an isolated
prototype build, not a new reference, sampler selection or GPU acquisition.
Keep running259 and all254/106 inputs unchanged. No CPU/GPU overlap.

## Fixed source construction and scope

Require terminal successful095,254,257 and their generated/payload identities.
Copy254's exact CPU header, adding only read-only original-binary-BVH/order/
edge-inset accessors with an exact source inverse. Do not replace the wide8
CPU transport, RNG, proposal, accumulated sums or fallback computation.
Use095's exact generated FP64 context and shader prefix before its main:
original geometry, watertight intersection, ambiguity flag, nudge, Sobol
shift, polynomial trigonometry and point-direct helpers remain byte-identical.

Replace only the GPU main with a port of the current whole_sample proposal:
same14 dimensions, uniform strategy at each k, same remapping, eye/light
generation, all prefix densities, original forward material/sidedness and
finite-depth target. CPU code uses log-sum-exp; GLSL FP64 has no matching
double exp/log builtin in this retained toolchain. The prototype instead
represents a nonnegative density as normalized mantissa times an integer
power of two, using double frexp/ldexp, and computes the identical ideal
mixture ratio. Floating outputs are NOT claimed bit-identical to CPU logs.
Independent numerical/physical/bias qualification remains mandatory.

Flag the ENTIRE original scored sample for CPU recomputation on any inherited
ambiguous intersection, different reconstructed triangle, exponent-ratio
outside[-1022,1022], nonfinite/invalid value, reconstructed-target/plane error
above the original unconditioned256epsilon bound, own density ratio error
above1e-8, or positive cosine/pdf below1e-12. The unconditioned error fallback
is more conservative than CPU069's conditioned audit; the GPU does not
approximate CPU072/074's long-double coincident-interior predicates. These
are execution-routing guards, not masks, reference thresholds or scientific
acceptance cuts. Recompute every flagged full sample using selected254's
sample_all_split, original pixel/seed/index and one CPU worker; restore its
complete RGB components and scored counters in the original accumulation
order. Keep every sample, null and flag. No partial GPU/CPU path blending.
Stream every GPU PathValue, corrected PathValue and original uint32 routing
flag in batch/selected-slot/sample order to gpu-paths.bin, corrected-paths.bin
and routing-flags.bin. PathValue is the retained160-byte layout; batches.jsonl
and prototype-scope.json record interval/selection/count/seed interpretation.
Flush each completed batch before any latency-guard stop. A failed/incomplete
batch remains a partial, never an accepted prefix or an excluded observation.

Build only the original fixed C1 eight-pixel diagnostic: (40,30),(120,30),
(200,30),(280,30),(40,150),(120,150),(200,150),(280,150), full320x180 buffer
layout but ONLY those eight pixels computed. Emit a distinct schema and
prototype-scope.json listing the selection. Outside-selection zeros are NOT
reference pixels, black-reference evidence or an admitted full-frame image.
Before any build, the implementation is clarified to use one independent
GPU invocation per selected-pixel/sample pair (at most8*16=128 paths/batch),
instead of095's per-pixel loop. Only path output records are written on GPU;
CPU accumulation retains the original per-pixel sample order. No shared
GPU sum is raced or reordered. This is an execution-layout change from095,
not a new proposal, sample count, numerical threshold or accepted timing.
Reject other image dimensions, depth other than8, or point count other than1.
Nonemissive scope stays unchanged. Limit native interface to8192spp, batch<=16
and one fallback CPU worker. Actual numerical acquisition needs a separate
prospective protocol; this plan authorizes no native/GPU run.

The prototype runtime adds a250ms submit/wait wall guard to bound interactive
impact; a guard failure stops the prototype and preserves partial evidence.
This is an operational/UI stop, not GPU timestamp calibration, a stability
percentage, an algorithm quality FAIL or accepted timing criterion. A future
bounded run must retain every sample/flag and receipt, including a guard stop.
No display, clock, power, driver or application setting changes.

## Bounded build and proof limits

Driver: scripts/research/n010_reference_sampling/build_whole_path_hybrid.py
Shader body: scripts/research/n010_reference_sampling/whole_path_scaled_gpu.inc.glsl
Work: out/research/n010-comparison-readiness/whole-path-hybrid-prototype-v1
Result:352-whole-path-hybrid-prototype-build.json (absent until manual run).

One explicit build after no scientific worker remains; CPU31,nice15,4GiB,
120CPU/180elapsed per shader/host compiler, one at a time, no retry/queue.
Use retained strict floating host flags plus AVX512F for the copied CPU
backend, and existing NoContraction SPIR-V decoration. Record all inputs,
generated bytes, edits/inverses, actual compiler PID/start/resources, terminal
receipts and stdout/stderr even on failure. Compilation is no runtime PASS.

Prepared NOT RUN. CPU259 is retained as an independent current acquisition;
no replacement of106/108/109 or acceptance of old GPU records occurs here.
A promising future prototype would still need its own full physical,
numerical/bias, state/prefix and actual whole-frame sizing/feasibility proofs
before changing the qualification intake. No GI speed or superiority claim.
References16/24, full artifacts14/17 including a diagnostic-only item, direct
error1.0 pixels UNRESOLVED/未解決 and scored; N010 NOT_READY. Unit/regression
tests NOT RUN. No CUDA, default Renderer/build/shader changes, Actions, N011
or N001–N009 result edits.
