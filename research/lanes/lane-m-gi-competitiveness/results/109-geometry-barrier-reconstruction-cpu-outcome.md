# Geometry-barrier reconstruction017: mixed CPU results, fixed cohort rejected

2026-10-24. **REJECTED_NO_GPU:2/6target conditions pass; no GPU continuation.**

[Preregistration017](../experiments/017-geometry-barrier-reconstruction-cpu-screen.md) was committed/pushed atd3b292cc before implementation/reconstruction. [Preparation107](107-geometry-barrier-reconstruction-cpu-preparation.json) and actual source a94bd7df precede all six one-time CPU target processes, in fixed H01/B2,H01/B8,H02/B2,H02/B8,H03/B2,H03/B8order. No new PT/reference path, GPU acquisition, seed or reference admission. No additional017process is selected. Lane M remains active and incomplete.

This observed-development candidate applies three geometry-only a-trous stages (strides1/2/4,25taps, separable[1,4,6,4,1]) to original finite-depth PT indirect images. Every tap segment must remain inside the viewport on hits of compatible material/oriented normal/plane. Thin intervening barriers are checked, not jumped by large-stride taps. Positions are CPU reconstructions from actual013GPU t/camera; exact GPU positions were not exported. Geometry masks freeze before reference intensity. Direct is unchanged, total=direct+filtered indirect. This is biased spatial reconstruction based on established prior art, not a novel architecture or an independent oracle.

All four original source-seed305419896rungs1/4/16/64spp are evaluated per target without exclusions. Original four-seed16384spp admitted means remain unchanged. Applying the identical filter to the admitted indirect mean is a separate deterministic reconstruction-bias diagnostic, never a replacement reference, admission or convergence test. Both a noisy passing rung<=64and a passing reference-bias gate are required per target. Every score uses57,600pixels, linear luma/reference RMS, totalNRMSE<=5%, indirectNRMSE<=10%, absolute indirect signed-energy bias<=5%, defined finite metrics. All six targets must pass for study acceptance.

|Target|First passing noisy spp|64spp indirect NRMSE %|Reference-bias indirect NRMSE %|Bias gate|Target decision|
|---|---:|---:|---:|---|---|
|H01/B2|4|6.855424|6.801244|PASS|PASS|
|H01/B8|none|10.192361|9.756083|PASS|FAIL|
|H02/B2|64|9.852708|9.809034|PASS|PASS|
|H02/B8|none|11.859128|11.734695|FAIL|FAIL|
|H03/B2|none|19.783530|19.612755|FAIL|FAIL|
|H03/B8|none|22.351917|21.990096|FAIL|FAIL|

4/24noisy image rows and3/6reference-bias rows meet the original thresholds; target admission uses their conjunction. Successful H01/B2(4spp) and H02/B2(64spp) are literal observed one-seed CPU-image results, with limited quality margins. They do not authorize selecting only successful targets for GPU study. Raw PT selected budgets256(B2)/1024(B8) remain exact published controls, not rerun. Lower sample counts exclude filter/G-buffer/allocation/synchronization costs and are not GPU speedups. Fair external denoised baselines remain needed.

The reference-bias failures demonstrate that the fixed operator itself can exceed the image-error budget even when applied to an admitted high-quality mean. Small total energy bias does not imply correct spatial radiance. More samples or noise cancellation cannot remove that deterministic operator discrepancy; the extra bias gate prevents such cancellation admitting the candidate. This is not a causal diagnosis of every error, a generic filter-family rejection or a guarantee about exact physical bias of the finite reference. No added rung, changed radius/weight/stage/threshold or in-study retuning.

All24noisy rows:

|Target|spp|Total NRMSE %|Indirect NRMSE %|Indirect signed bias %|Image decision|
|---|---:|---:|---:|---:|---|
|H01/B2|1|2.569735|13.171942|-1.066238|QUALITY_FAIL|
|H01/B2|4|1.778468|9.116067|0.039463|PASS|
|H01/B2|16|1.431554|7.337854|-0.059671|PASS|
|H01/B2|64|1.337436|6.855424|0.013259|PASS|
|H01/B8|1|4.223455|16.349861|-3.893442|QUALITY_FAIL|
|H01/B8|4|3.015264|11.672701|-1.736994|QUALITY_FAIL|
|H01/B8|16|2.828836|10.951007|-1.036211|QUALITY_FAIL|
|H01/B8|64|2.632865|10.192361|-0.560688|QUALITY_FAIL|
|H02/B2|1|3.180072|19.188967|-6.673709|QUALITY_FAIL|
|H02/B2|4|2.086139|12.588033|-2.672257|QUALITY_FAIL|
|H02/B2|16|1.718905|10.372099|0.053036|QUALITY_FAIL|
|H02/B2|64|1.632829|9.852708|0.358993|PASS|
|H02/B8|1|4.306247|21.291942|-5.161109|QUALITY_FAIL|
|H02/B8|4|3.077577|15.216862|-4.855770|QUALITY_FAIL|
|H02/B8|16|2.415781|11.944664|-0.474762|QUALITY_FAIL|
|H02/B8|64|2.398483|11.859128|-0.897576|QUALITY_FAIL|
|H03/B2|1|7.550253|35.008468|0.270939|QUALITY_FAIL|
|H03/B2|4|4.921908|22.821550|0.386785|QUALITY_FAIL|
|H03/B2|16|4.426731|20.525554|0.607483|QUALITY_FAIL|
|H03/B2|64|4.266700|19.783530|-0.495866|QUALITY_FAIL|
|H03/B8|1|9.662488|39.434138|-3.632638|QUALITY_FAIL|
|H03/B8|4|6.266271|25.573651|0.986398|QUALITY_FAIL|
|H03/B8|16|5.618513|22.930043|0.304065|QUALITY_FAIL|
|H03/B8|64|5.476857|22.351917|-1.070383|QUALITY_FAIL|

[Full replay108](108-geometry-barrier-reconstruction-six-targets-raw-replay.json) retains every target receipt and independent terminal audit. All84target payloads and180complete stage/error arrays replay exactly, plus full geometry/masks. 11520independent scalar pixel-stage comparisons use fixed geometry-only uniform-image/hit percentiles. Independent math.fsum recomputes full-image RMS/energy-bias normalization. Original24PT inventories/plans/published022identities and three013HWRT primary captures/published096identities, plus source/physical/reference chains, rehash before processing and during independent audit. Reference radiance is used only for scoring/the separately labelled bias diagnostic; every noisy source is an original GPU PT image.

16new actual vectorized/scalar kernel tests pass, including constant/zero/convex properties, material/normal/plane/miss/viewport/segment barriers, pass order, malformed inputs and inclusive quality/bias conjunction. Old test suites are not identically rerun. All six guarded CPU processes return0 without timeout, under300CPU/600wall seconds,4GiB address space/one thread and16GiB disk precondition. CPU wall is health only, not performance evidence. Raw stages/errors/masks/receipts stay repository/out.

No GPU/power/clock/desktop change, new CI/Actions, old output overwrite, default Renderer/CMake integration or N001–N010edit. Audited GPU acquisitions remain120. Historical human-operated references retain attribution. Default Renderer build/runtime regression NOT_RERUN; validation layers NOT_RUN. Actual float32 GPU G-buffer/reconstruction behavior, complete owned memory, runtime and calibrated full-cost timing require separate qualification. Broader novel competitive architecture, new heldout/dynamic/Sponza/device and fair representative-family gates remain open. [Verification110](110-geometry-barrier-reconstruction-cpu-verification.json) records preservation and index/link scope.
