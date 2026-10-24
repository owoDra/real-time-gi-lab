# Device reconstruction019: first CPU rehearsal stopped on loader ABI error

2026-10-24. **STOP_NO_RETRY / INPUT_ABI_IMPLEMENTATION_FAILURE.** One native CPU attempt (H01/B2),0completed rehearsals,0geometry/coefficient/filter outputs,0new GPU acquisitions. Other five CPU targets NOT_RUN; no019GPU process or quality/timing admission.

[Protocol019](../experiments/019-surface-quadratic-device-correctness.md) remains unchanged. Actual replay/intake/test code54460fa5 was committed/pushed before the attempt.18new actual ordered-stop/intake/numerical contracts pass, adding to the58prior kernel/CLI checks; those prior suites/builds were not rerun. The first native process returns2 without timeout, stderr `hit metadata invalid`, before creating its capture directory. All three new input files, plan/start and native logs/result remain exact under repository/out; no retry or overwrite.

[Independent failure audit118](118-surface-quadratic-first-cpu-failure-raw-audit.json) rehashes the complete failed inventory and plan input/build/source/reference chain. It independently compares original raw GPU hit metadata with each canonical scene:

|Scene|Hit pixels|Material token0xffffffff|Primitive/material/instance match canonical metadata|
|---|---:|---:|---|
|H01|7325|7325|Exact for all hits|
|H02|6748|6748|Exact for all hits|
|H03|7670|7670|Exact for all hits|

All21,743hits have finite admitted geometry and the exact material token0xfffffffffrom their original scene metadata. No hit has primitive/instance0xffffffff. The original013/017intake requires exact primitive/material/instance equality and correctly accepts these material values; hit presence comes from flag1. This is an opaque material token in the existing ABI, not proof of a missing/corrupt hit. Miss records retain their separate flag0/invalid metadata convention. The019loader added an incorrect generic check rejecting0xffffffffin all three metadata words. That newly introduced restriction, rather than reference/geometry corruption or image statistics, causes this CPU rejection. The synthetic native fixtures used material0and missed this real ABI case.

No new radiance or coefficient field was produced, so this attempt supplies no019image-quality or bias result and no causal claim about estimator performance.018all-six CPU quality passes and every admitted reference remain exact. The18new replay/intake tests do not repair the older loader; passing synthetic tests is not full-input/runtime admission. Preserve this test gap and first failure.

Keep019stopped. Any continuation needs a separately identified, preregistered implementation repair and new outputs, not an identical H01/B2rerun or immediate later target. Proposed repair: allow all32-bit material tokens in the loader while retaining primitive/instance validity, miss/flag/depth/normal/input checks and exact canonical metadata equality in intake. Keep all scalar reconstruction/shader bytes, masks/taps/strides/pivot/L1/clipping, source images/references, selected018sample rungs, numerical bounds and full-image quality gates unchanged. This changes input ABI validation, not a material remap, sampler, threshold or transport model.

Historical source/evidence is unchanged. Raw matrices/plans/logs remain repository/out; compact identities only enter Git. No new PT/reference path, GPU/power/clock/desktop change, CI/Actions or default Renderer integration. Audited GPU acquisitions remains120. Default Renderer build/runtime regression NOT_RERUN; validation layers NOT_RUN. [Verification120](120-surface-quadratic-first-cpu-failure-verification.json) records preservation and index/link scope. Broader competitive/novel architecture and Lane M remain unresolved; a source-loader failure is not an accepted family quality loss or architecture win.
