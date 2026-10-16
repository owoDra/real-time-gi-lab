# N010 natural-idle C7 observation

Date: 2026-10-17 JST. Parent: `b9b027c`. Registered before new samples.
User answered "今" to a request for a brief naturally idle interval with
applications left open. No desktop, app, driver, clock or power changes.

196 actually completes all eight C7 HWRT blocks / 512 samples and FAILS all
seven original gates. Zero-dose full times range 146.759 to 952.289 us;
zero-dose neutral-stage times range 2.405 to 18.555 us. CPU deferred image
serialization alone does not establish precision. No full 186 is launched.

Perform one fresh repetition of that exact C7-only diagnostic, with unchanged
184 fixture, 185 dose, images/scratch/ledgers/spool and original schedule,
thresholds, all samples and resource guards. New result
`197-natural-idle-c7-precision-diagnostic.json`, new work
`natural-idle-c7-precision-diagnostic-v1`. Preserve 196 and every old path.
Only outer result/work and provenance identities change in the frozen 196
driver. Reversing that overlay reconstructs its complete committed source.

Read DRM fdinfo engine counters immediately before and after the whole
diagnostic. Deduplicate client IDs on the same PCI device. Record process
names and engine counters only, not user command lines. Retain inaccessible
PID counts, created/disappeared clients and counter resets. These snapshots
are coarse intervals, not exact per-query overlap, instantaneous utilization,
global quiescence or controlled causal proof. Only surviving same-identity
clients receive deltas; no sample is excluded based on this observation.

No repeat until PASS, favorable subset or accepted timing transfer. All eight
blocks finish unless an operational failure occurs. Scientific FAIL stays
FAIL; record the user's declared idle condition and observed external work
separately. This cannot replace full 186 or any reference/final READY gate.
GPU work is expected below one second in aggregate; setup, one-second
settles and CPU readback/output are additional. Unit/regression tests NOT RUN.
No N011, CUDA, Actions, scoring masks, threshold/cap/seed changes, default
promotion or N001–N009 changes. Error-1.0 direct pixels stay UNRESOLVED.
