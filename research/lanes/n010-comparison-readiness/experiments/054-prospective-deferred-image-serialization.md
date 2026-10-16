# Prospective deferred image serialization for full Renderer calibration

Date: 2026-10-16 JST. Parent checkpoint: `575ddbc`.
Register before fixture compilation or new GPU samples. CPU feasibility 180 is
independent and currently acquiring; never overlap it with GPU calibration.

## Question and unchanged scientific boundary

Post-hoc 183 describes all 153 complete retained blocks of 169/178. Original
169 remains 2 PASS / 14 FAIL; 178 remains INCOMPLETE / NOT ACCEPTED with three
FAIL boundaries and failed environment/restoration guards. File-output cadence
is not GPU idle time or a demonstrated cause of timing failures. Keep all old
bytes, decisions and stopped paths. No old acquisition is restarted.

Question: can moving only CPU PFM serialization after each native calibration
sequence establish the original full-boundary precision requirements? This is
a prospective acquisition change, with no assertion that it will succeed.

Preserve the exact native GPU workloads, shaders, timestamps, queries, barriers,
source/target geometry and AS maintenance, sample order, four warmup pairs,
twelve measured pairs, eight fresh-process blocks, three-dose sizing, +20%
known-work sizing and 100000000 dose cap. Preserve every original precision
threshold: control envelope 1.02, span 1.03, order bias 1.02; effect span 1.05,
order bias 1.03, positive fraction >=0.75 and minimum effect above the control
envelope. No statistical aggregation change, extra warmup, averaging of new
samples, correction, subtraction, exclusions, favorable subset or retry.

## Isolated fixture build 184

Build fresh `out/research/n010-comparison-readiness/deferred-image-calibration-build-v1`
with result `184-deferred-image-calibration-fixture-build.json`.
Parent is exact full PASS 167 and its v3 generated sources/binaries. Retain
all source/dependency/input hashes, original five serial compiler/link commands
and 8 GiB address-space / 21600 aggregate CPU-second / 3600 elapsed-second
limits per compilation invocation. CPU build may coexist with 180: CPU wall
is diagnostic, and all frozen scientific bytes/resource limits stay unchanged.
No build overlaps GPU research. No change to active/default binaries, headers,
shaders or build graph. Build failure retains all files without automatic retry.

Only change calibration PFM output handling in isolated capture/PT main files:
retain each image's already downloaded RGBA float vector in a bounded CPU
spool; after the complete native sequence, serialize every original image at
its original path using the exact v3 row writer. Keep image dimensions,
component extraction, float bits, PFM headers and final PT root images. Keep
per-frame GPU-to-host image readback, neutral scratch readback/write, directory
creation, timing records and source-state preparation in their original order.
This does not remove all inter-sample I/O or diagnostic transfers.

Reserve at most 256 image records. Before retaining each image, require total
RGBA vector storage <=256 MiB; refuse overflow and retain partials. Release
all spooled vectors after their writes. Non-calibration output stays on its
original immediate path. The existing allocation ledger retains its explicit
scope: all owned Vulkan allocations, excluding CPU/driver-private memory.
Record the bounded CPU image storage separately; do not count it as GPU memory
or claim the ledger captures CPU allocations.

Reversing the two main-file overlays must exactly reproduce 167's entire
runtime/capture/PT generated sources. The entire runtime file and timed PT
run-image/maintenance prefix must remain byte-identical. Preserve inherited
whole-source inverse to original active sources. Source assembly/compilation
is not runtime correctness, timing capability, reference admission or READY.
Unit tests are not run unless requested; scientific image/scratch/memory
validation remains mandatory in the subsequent actual GPU acquisitions.

## Subsequent one-time GPU acquisitions 185/186

Prepare a separate explicitly guarded driver before GPU acquisition. Refuse
existing outputs/work and other CPU/GPU research workers. Do not move desktop
windows or change display resolution, driver, power, clocks or application
preferences. Current AMD/Vulkan device/driver identities and boot/session
observations must be recorded read-only. This experiment has no hidden-IDE
policy and cannot claim equivalent global quiescence or causal comparison.

1. After actual termination of 180 and every other CPU reference/control/GPU
   research worker, require actual complete 184 PASS and acquire **all sixteen**
   original sizing boundaries to `185-deferred-image-calibration-sizing.json`,
   work `deferred-image-calibration-sizing-v1`. Original three-dose schedule,
   every original image equal to immutable 046, exact scratch witness and all
   owned Vulkan allocation ledgers to teardown zero within 8 GiB are required.
   Validate complete CPU spool flush and every expected image file/hash.
2. Only actual complete full 185 PASS admits full 186, work
   `deferred-image-calibration-accepted-v1`, result
   `186-deferred-image-calibration-full-renderer.json`. Freeze all doses and
   inputs, preserve all 128 blocks / 8192 timestamp samples, all images/scratch,
   all CPU spool records, commands, resource/memory evidence and failures.
3. All sixteen original statistical/image/scratch/memory decisions must PASS
   before timing admission. A numerical FAIL completes the fixed campaign;
   an operational/native/input failure stops with partials explicitly retained.
   No automatic retry, subset acceptance or change to thresholds.

An explicit new proof adapter must verify actual complete 184/185/186, all
native payloads and original analyses before pilot/final-auditor dispatch.
Keep original 169 and 178 verifiers unchanged and rejecting their negative
results. Bind exact new binaries in future calibrated pilot timing; do not
retroactively accept old timings or transfer capability to different workloads.
All 24 eligible references, complete quality/memory pilots and all six original
047 READY gates remain required. Direct error-1.0 pixels stay UNRESOLVED /
未解決 and included. No N011, CUDA, Actions or N001–N009 result changes.
