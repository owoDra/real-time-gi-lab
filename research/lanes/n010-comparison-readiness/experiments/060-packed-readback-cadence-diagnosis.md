# N010 prospective packed-readback cadence diagnosis

Date: 2026-10-17 JST. Parent checkpoint: `8f05ab3`.
Register before compilation and new samples. Prior goal turn made progress:
195/196/197 completed and changed dispatch decisions; 198 replayed them.
N010 remains NOT_READY, sixteen of twenty-four references eligible. This
experiment addresses the timing prerequisite; reference and correctness work
remain required. No N011 or reinterpretation of original readiness.

## Evidence and falsifiable question

196/197 complete all eight C7 HWRT blocks and fail all seven original precision
gates. Deferred CPU PFM serialization and a user-idle interval have not repaired
precision. The 184 runtime still performs four synchronous diagnostic downloads
per frame: counters, storage statistics, RGBA image and neutral scratch. Each
download allocates staging, submits a copy, waits, copies CPU bytes, and frees
staging. This is an observed code property, not a demonstrated cause of noise.

Can coalescing these downloads after the existing timed Renderer commands,
inside the same submission, establish the original short C7 precision gates?
Do not subtract diagnostic time or add irrelevant timed GPU work. Preserve all
samples and outputs. No claim about clocks, interference or GPU quiescence.

## Isolated fixture 199

Build only the capture executable, for this bounded C7 diagnosis, at fresh
`out/research/n010-comparison-readiness/packed-readback-build-v1`; result
`199-packed-readback-fixture-build.json`. Parent: exact 184 result and generated
runtime/capture sources. Copy the original neutral header into the isolated
directory with an explicitly inverse-checked buffer accessor and bounded scratch
spool. Both translation units include that same header. No default source,
shader, CMake graph or binary changes. PT/dense RC are not packed by this build;
a complete sixteen-boundary fixture still requires separately validated work.

Use one persistent host-visible coherent transfer-destination buffer per runtime:
counter bytes at 0, storage stats at 32, RGBA at 64, scratch after RGBA. Bound
the buffer to 16 MiB; all Vulkan allocations remain in the original <=8 GiB
ledger, with zero at teardown. Actual image bytes and copy bounds are checked.
After original stamp(15), append compute-write to transfer-read dependency,
four copies and transfer-write to host-read dependency. Existing fence wait
then makes this coherent buffer available. Replace only the four diagnostic
downloads with copies from that completed buffer. Preserve the entire original
GPU recording block through stamp(15), and every original timing expression,
shader, dynamic-maintenance path and sample ordering. This is not a change to
the work counted by the original full Renderer boundary.

Spool scratch CPU bytes as well as the existing RGBA spool. At most 256 scratch
records / 16 MiB; flush all original paths after the sequence, release and
record completeness/peak capacity. Existing RGBA <=256 MiB remains separate.
No scratch byte enters the image/transport calculation. Keep counter/overflow
checks for every frame. Preserve every image, scratch and timestamp sample.

Reversing each declared overlay must reconstruct the whole 184 runtime/capture
sources and original neutral header exactly. Compile runtime/capture and link
using the original three commands with only isolated source/object/output
paths changed. One CPU, nice 15, 8 GiB address space, 120 aggregate CPU seconds
and 300 elapsed seconds per invocation. Record actual PID/start/limits and
all dependencies/artifacts. Operational failure stops, preserves output and
does not automatically retry. Build success is not runtime proof or admission.

## One-time bounded C7 sizing 200 and diagnostic 201

Require actual full build PASS, exact current lock 026, baseline images 046,
original shaders, preserved input hashes and no other research worker. No app,
desktop, display, clock/power/driver settings change or user-idle requirement.
Keep original calibration core source SHA and schedule/analysis functions.
Only dispatch to the new capture binary with the two explicit minimal/packed
environment switches. No other boundary can run through this diagnostic.

1. Fresh `packed-readback-c7-sizing-v1`, result
   `200-packed-readback-c7-sizing.json`: original three-dose sequence
   [0,65536,262144] repeated three times. Same positive-slope +20% sizing and
   100000000 cap. Require every image byte-equal to 046, verified scratch for
   every distinct dose, owned ledger replay and complete CPU spool release.
2. Only complete 200 PASS: fresh `packed-readback-c7-diagnostic-v1`, result
   `201-packed-readback-c7-precision-diagnostic.json`. Freeze its dose/binary/
   shaders/environment and acquire the original eight fresh-process blocks,
   all 64 frames each: four warmup pairs and twelve measured pairs,
   counterbalanced AB/BA controls/effects. Preserve original seven thresholds:
   control envelope <=1.02, span <=1.03, order bias <=1.02; effect span <=1.05,
   order bias <=1.03, positive fraction >=0.75 and minimum effect > envelope.
   No additional warmup, statistical averaging, threshold changes, exclusions,
   repeat until PASS, subset admission or changed GPU boundary.

Native invocations have 30 CPU / 30 elapsed second limits with actual receipts;
no virtual-address limit for Vulkan reservations. Expected aggregate timed GPU
work is below one second; CPU setup/output/settles are separate. Keep all
images/scratch/ledger/spool checks and all partial/native failures. The
diagnostic controller performs one scientific process at a time. No full 186
or long reference job is queued. A C7 failure stops this candidate; a C7 PASS
requires a separately registered complete cohort implementation/proof, not
timing admission by transfer. All original final six gates remain required.

Direct max-relative-error-1.0 pixels remain UNRESOLVED / 未解決 and included.
No unit/regression tests are run; this isolated scientific build/acquisition
does not promote architecture. N001–N009 results and failed/stopped evidence
remain unchanged. No GitHub Actions, CUDA or power/clock forcing.
