# Original A6a failure reproduced at sample3265 without a full-frame retry

2026-10-18 JST. Recipe136, caller and driver committed `945df898` before
either separately invoked part. POST-HOC diagnosis, no admission.

[434](434-original-sphere-pixel-probe-build.json) compiled a private caller
with the original254 exporter flags and unchanged pinned wide8 header.
Build return0, CPU2.579885/elapsed2.618844 seconds, no stderr. After reviewing
that terminal result, [435](435-original-sphere-pixel-probe.json) invoked
only pixel(96,77), original seed81985529216486895, original cache/sample
sequence0..8191. It stopped on the first exception at sample index3265
(zero based), return77 from the diagnostic catch, CPU0.309246/elapsed
0.315705 seconds. Both parts verify native process/resource receipts,
CPU31/nice15/120CPU/180elapsed/4GiB and input identities after termination.

All five original witness lines match261 byte for byte: k4/split3,
sampled log16.299489357790691, reconstructed16.299490368089238, and all
four triangle IDs/raw points. The original header, check threshold1e-6,
proposal/physical scene/RNG/intersection/spawn remain unchanged. Catching
the exception records the sample and immediately stops; it is not a repair
or a continued physical image. The numerical failure is reproducible under
this tiny CPU workload; the run does not depend on desktop idle calibration.

The direct termination cause is established and its sample is localized.
The numerical mechanism is still unproven. Next is a separately registered
operand-only witness for this exact sample; no full-seed retry, seed3,
new reference or compiler/GPU queue. A6a has two complete original seeds,
seed2 FAIL; physical inventory14/17 incl one diagnostic-only item and
eligible references16/24 unchanged. N010 NOT_READY, then distinct Lane M.
Sponza direct relative-error1.0 pixels remain UNRESOLVED/未解決, included.

Build of this isolated diagnostic executed; unit/regression/default-build
and GPU/runtime smoke checks NOT RUN. No default Renderer graph,
N001–N009 results, Actions, CUDA or user power/display/driver/app settings
changed. These numerical diagnosis records are not runtime regression
validation or a calibrated performance result.
