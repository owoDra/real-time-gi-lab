# Surface-quadratic reconstruction018: fixed full-image CPU outcome

2026-10-24. **CPU_RECONSTRUCTION_FEASIBILITY_PASS: 6/6 target conditions pass.**

[Preregistration018](../experiments/018-surface-quadratic-reconstruction-cpu-screen.md) was committed/pushed at e4559e8e before new implementation, coefficients or scores. [Preparation111](111-surface-quadratic-reconstruction-cpu-preparation.json) and actual source72a45edd precede all six one-time CPU target processes, in fixed H01/B2,H01/B8,H02/B2,H02/B8,H03/B2,H03/B8 order. Separately preregistered GPU correctness work is eligible; no GPU implementation/acquisition or timing is part of018. Lane M remains active and incomplete.

This observed-development candidate replaces017constant averaging with geometry-only rank-reduced quadratic weighted regression. Original frozen017barriers/25taps/kernel/strides1/2/4 are unchanged. Tangent-plane basis[1,u,v,u²,uv,v²], two-sweep weighted Gram-Schmidt and fixed relative pivot1e-6 determine columns. Signed coefficient L1<=4 selects quadratic, affine or constant fallback without radiance. Complete coefficient/model/rank tensors are saved before intensity. Each stage saves preclip signed output and clips only negative values to0; original direct is preserved. This is an established reconstruction route, not NFOR reproduction or an architecture novelty claim.

All24original seed305419896 PT images at1/4/16/64spp are reused without new sampling. The unchanged four-seed16384spp admitted mean is reconstructed with the SAME coefficients/clipping solely as a labelled reference-reconstruction bias diagnostic. It remains the unfiltered scoring reference, never a replacement reference/admission or exact physical-bias proof. Every score uses all57,600pixels and original inclusive totalNRMSE<=5%, indirectNRMSE<=10%, absolute indirect signed-energy bias<=5%, defined finite nonnegative final images. A noisy passing rung<=64AND reference-bias PASS is needed per target; all six targets are required.

|Target|First passing noisy spp|64spp indirect NRMSE %|Reference-reconstruction indirect NRMSE %|Bias gate|Target|
|---|---:|---:|---:|---|---|
|H01/B2|16|4.292616|0.922538|PASS|PASS|
|H01/B8|64|5.429742|1.264419|PASS|PASS|
|H02/B2|64|5.923170|1.872155|PASS|PASS|
|H02/B8|64|6.710648|2.491904|PASS|PASS|
|H03/B2|64|6.807888|0.603104|PASS|PASS|
|H03/B8|64|8.010577|1.473297|PASS|PASS|

7/24noisy rows and 6/6reference-reconstruction bias rows pass. Per-target admission uses their conjunction. Every observed outcome is retained; no target/threshold/rung/model selection after scoring. CPU scientific acceptance is distinct from runtime/memory/timing admission and one-seed images are not a robustness or unseen-heldout result.

All24noisy rows:

|Target|spp|Total NRMSE %|Indirect NRMSE %|Indirect signed bias %|Image decision|
|---|---:|---:|---:|---:|---|
|H01/B2|1|6.196331|31.761151|2.915692|QUALITY_FAIL|
|H01/B2|4|3.257982|16.699763|0.420315|QUALITY_FAIL|
|H01/B2|16|1.650376|8.459498|-0.279391|PASS|
|H01/B2|64|0.837453|4.292616|-0.168387|PASS|
|H01/B8|1|10.537123|40.791388|1.035086|QUALITY_FAIL|
|H01/B8|4|5.461994|21.144509|-0.241188|QUALITY_FAIL|
|H01/B8|16|2.781497|10.767757|-0.387847|QUALITY_FAIL|
|H01/B8|64|1.402596|5.429742|-0.069975|PASS|
|H02/B2|1|7.397765|44.639080|-2.077956|QUALITY_FAIL|
|H02/B2|4|3.516442|21.218668|-2.091536|QUALITY_FAIL|
|H02/B2|16|1.893570|11.426049|0.030510|QUALITY_FAIL|
|H02/B2|64|0.981611|5.923170|0.280540|PASS|
|H02/B8|1|11.163553|55.197429|2.230021|QUALITY_FAIL|
|H02/B8|4|4.813791|23.801460|-2.484795|QUALITY_FAIL|
|H02/B8|16|2.439440|12.061645|0.213515|QUALITY_FAIL|
|H02/B8|64|1.357213|6.710648|-0.367423|PASS|
|H03/B2|1|12.209289|56.611149|3.689667|QUALITY_FAIL|
|H03/B2|4|5.697639|26.418399|0.739368|QUALITY_FAIL|
|H03/B2|16|3.008682|13.950444|0.675087|QUALITY_FAIL|
|H03/B2|64|1.468253|6.807888|-0.352887|PASS|
|H03/B8|1|14.020211|57.218695|0.763434|QUALITY_FAIL|
|H03/B8|4|7.411991|30.249513|2.337860|QUALITY_FAIL|
|H03/B8|16|3.878005|15.826754|1.191267|QUALITY_FAIL|
|H03/B8|64|1.962821|8.010577|-0.375268|PASS|

Coefficient and clipping diagnostics:

|Target|Stage|Quadratic pixels|Affine fallback|Constant fallback|Max L1|Reference negative pixels|64spp negative pixels|
|---|---:|---:|---:|---:|---:|---:|---:|
|H01/B2|1|7325|0|0|1.519604|58|72|
|H01/B2|2|7325|0|0|1.536368|80|120|
|H01/B2|4|7325|0|0|1.519462|132|280|
|H01/B8|1|7325|0|0|1.519604|3|43|
|H01/B8|2|7325|0|0|1.536368|2|11|
|H01/B8|4|7325|0|0|1.519462|2|9|
|H02/B2|1|6748|0|0|1.519657|92|253|
|H02/B2|2|6748|0|0|1.458676|137|288|
|H02/B2|4|6748|0|0|1.520064|229|360|
|H02/B8|1|6748|0|0|1.519657|0|31|
|H02/B8|2|6748|0|0|1.458676|0|6|
|H02/B8|4|6748|0|0|1.520064|1|2|
|H03/B2|1|7670|0|0|1.460504|120|138|
|H03/B2|2|7670|0|0|1.457720|235|304|
|H03/B2|4|7670|0|0|1.486018|209|505|
|H03/B8|1|7670|0|0|1.460504|0|64|
|H03/B8|2|7670|0|0|1.457720|2|16|
|H03/B8|4|7670|0|0|1.486018|4|10|

Negative preclip counts/minima/energy for ALL30images and all90stages, selected-rank histograms/negative coefficient counts, full support/leakage/active-p99/max metrics and complete error arrays are preserved in [replay112](112-surface-quadratic-reconstruction-six-targets-raw-replay.json) and raw repository/out. Clipping is part of the estimator and all error scores; no negative pixel is excluded. The coefficient tensor alone is34,560,000f64bytes (17,280,000if f32), excluding masks/geometry/images/fitting work; this is not GPU owned-memory measurement.

All 78 target payloads, 24 complete coefficient/model/rank tensors and 270 preclip/clipped-stage/error arrays replay exactly. Independent scalar/SVD checks cover 2304 pixel-stage coefficient vectors and 23040 preclip/clipped pixel outputs at fixed64uniform-image+64geometry-hit percentiles per target. SVD coefficient rtol1e-9/atol1e-10 and scalar stage rtol1e-9/atol1e-14 are numerical health tolerances, never quality thresholds. Independent math.fsum recomputes full-image RMS/energy-bias normalization. Full old geometry/masks, original24PT plans/results/inventories/published022identities, three013HWRT primary captures/published096identities and physical/reference/source chains rehash. Every target audit precedes the next process.

14new actual kernel tests pass, including independent SVD, constants/zeros, positive affine/quadratic reproduction,1D/single-pixel rank reduction, both L1 fallbacks, normalization rejection, signed coefficients/preclip negatives, barriers and malformed inputs. Prior01716test evidence is rehashed/reused, not rerun. Six guarded CPU processes each return0 without timeout, with300CPU/600wall seconds,4GiB address-space/one-thread limits and16GiB disk precondition. CPU wall is health only. All M001 coefficients and scores were acquired once; no old PT/reference rerun, seed, new path or GPU acquisition.

Future GPU work must qualify actual float32 primary/geometry/rank/fallback/clipping, compute coefficients on device and charge primary data, fitting, filtering, allocations/synchronization and full end-to-end transport costs. Free CPU coefficient upload or reduced source samples cannot establish speed. Fair denoised representative-family comparisons, independently preregistered new heldouts/dynamics/Sponza/devices and broader competitive-architecture gates remain necessary. No accepted GPU speed, memory win, architecture promotion or Lane M completion.

No power/clock/desktop change, new CI/Actions, old output overwrite, default Renderer/CMake integration or N001–N010 edit. Total audited GPU acquisitions remains120. Original human-operated evidence retains attribution. Default Renderer build/runtime regression NOT_RERUN; validation layers NOT_RUN. [Verification114](114-surface-quadratic-reconstruction-cpu-verification.json) records preservation and index/link scope.
