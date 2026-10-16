# N010: fixed-grid sampling and short-boundary timing diagnostics

Date: 2026-10-17 JST. Parent checkpoint: `e44ee9e`.
Register before these new diagnostic samples. Continue the user's low-load
constraint. Neither experiment admits references or accepted timing.

## Motivation from completed diagnosis

193 completed three serial compiles and three selected-pixel CPU acquisitions.
All original and failed-guide selected means/second moments reconstruct exact
retained values. On the selected sixteen pixels the failed guide lowers
first-indirect path variance but increases later-indirect variance; weight
second moment is about 1.272. This is not a fair whole-image sampler ranking:
eight pixels were selected for high original errors.

194 separates that selection effect and checks whole-image moments. The guide
actually reduces whole-image per-path variance to 0.96897 / 0.96876 of
original at 8192/16384, but increases observed replicate variance to
1.13293 / 1.13482. Its observed replicate variance divided by a descriptive
iid moment proxy is 0.76503 / 0.74519, versus original 0.65432 / 0.63615.
Thus simply blaming larger total path variance is incomplete: the sample
mapping has also lost observed variance reduction. These proxies are not
RQMC standard errors or causal theorem proofs. The original first-indirect
transport benefits much more strongly from the same net (proxy ratios
0.12759 / 0.09302 / 0.07165 across three levels) than B8.

## CPU diagnostic 195: existing nested scramble on a fixed grid

Use the **exact already compiled nested diagnostic binary in 193**, after
rehashing its whole header/main/binary/data provenance. This binary accepts a
pixel list and fixes 8192 samples and the original four seeds. No recompilation,
new sampler, physics change, extra scored paths or main build change.

Freeze a 16 by 16 grid, x=floor((i+0.5)*320/16),
y=floor((j+0.5)*180/16), i,j=0..15, in row-major order. All 256 pixels are
retained, including zeros. This selection is independent of any measured
error or candidate output. Original and failed-guide comparisons reuse their
hash-checked full-frame 8192 sidecars at those exact coordinates/seeds. Do not
select the tail pixels from 193 for this comparison.

One invocation at work `fixed-grid-scramble-diagnosis-v1`, result
`195-fixed-grid-scramble-diagnosis.json`, one CPU, nice 15, 4 GiB address
space, 220 aggregate CPU seconds and 300 elapsed seconds. Actual child
PID/start/resource limits are recorded. No GPU or other scientific worker.
Preserve every record and any failure/partial without automatic retry.

Report all four replicate means, paired p99 luminance disagreement and
replicate variance over the full fixed grid for original, failed guide and
nested scramble, plus path-moment diagnostics. This is a cost/risk diagnostic
before deciding whether to run 188/189/190. It cannot substitute for those
proofs, for a whole-image feasibility result, for a second level, for any
pending state or for the fixed two-consecutive-level full-corpus criteria.
A negative or marginal result argues against spending another full ladder;
a positive result does not guarantee eligibility. No threshold is changed.

## GPU diagnostic 196: short controlled boundary before an hour-long campaign

Run only **C7 HWRT**, selected because the retained complete original 169
boundary failed all seven gates and is inexpensive. Use exact deferred fixture
184, full sizing 185's frozen C7 dose, original 046 images, the original
eight fresh-process blocks and exact 64-sample schedule, including all warmups.
No samples are excluded and no numerical retry is permitted. Original
schedule/analysis/execute function bodies remain byte-identical; only the
outer work/result/schema identity and explicitly fixed one-boundary dispatch
change. Require whole inverse to the current plan-054 generated program.

Work `deferred-c7-precision-diagnostic-v1`, result
`196-deferred-c7-precision-diagnostic.json`. Require actual CPU 195 termination
(including a retained explicit operational failure) and no other research
worker. Rehash original 184/185 fixture prerequisites and preserve the original
environment, image/scratch validation, all-owned Vulkan ledgers <=8 GiB and
teardown zero, CPU spool bounds and payload hashes. Keep all 512 samples and
original precision decisions. Native invocations have 30 elapsed / 30 CPU
second guards; actual receipts and any timeout output/partials are retained.
The Vulkan launcher execs the native process, so a timeout kills that actual
PID. No virtual-address limit is imposed on Vulkan driver reservations.

GPU work at this controlled boundary is expected to total less than one
second; host setup/readbacks/output are additional and not claimed as GPU
idle observations. This is a small bounded probe, not a full 186 run. It
does not alter clocks/power/display/desktop or stop user applications. The
one-boundary PASS/FAIL is diagnostic only: original full 186, all sixteen
boundaries and all six final READY gates remain required before admission.
If this boundary still fails, do not spend the >hour full campaign merely
to reproduce a known unresolved limitation. If it passes, other boundaries
are still unmeasured. Differences from older campaigns are not controlled
causal proof about CPU serialization or desktop interference.

193/194/195/196 retain scientific diagnostic scope. Unit/runtime regression
tests are NOT RUN. No N011, CUDA, Actions, threshold/cap/seed/corpus changes,
default Renderer promotion or changes to N001–N009. Direct error-1.0 pixels
remain **UNRESOLVED / 未解決**, included.
