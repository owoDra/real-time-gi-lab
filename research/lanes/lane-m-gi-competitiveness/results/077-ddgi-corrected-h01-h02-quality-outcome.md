# M001 corrected DDGI quality: 0 passing, 4 exhausted, 2 unresolved targets

2026-10-23. The explicitly unblinded [012 continuation](../experiments/012-ddgi-corrected-quality-continuation.md)
retains 12 actual quality acquisitions in fixed target/rung order. [Full raw replay](076-ddgi-corrected-h01-h02-quality-raw-replay.json)
independently rehashes the complete native evidence, saved scores and full f64 error
maps, then recomputes physical/runtime/copy/memory admission and every metric.
Original010evidence and supersession050/051 remain separate and unchanged.

|Target|Rung / grid / rays|Total NRMSE %|Indirect NRMSE %|Indirect signed bias %|Decision|
|---|---|---:|---:|---:|---|
|H01/B2|q0 / 8³ / 128|3.732623|19.132680|-13.495426|QUALITY_FAIL|
|H01/B2|q1 / 16³ / 256|5.836618|29.917344|-9.509769|QUALITY_FAIL|
|H01/B2|q2 / 24³ / 512|3.180520|16.302717|-3.906366|QUALITY_FAIL|
|H01/B8|q0 / 8³ / 128|5.796078|22.437824|-9.701864|QUALITY_FAIL|
|H01/B8|q1 / 16³ / 256|4.796461|18.568110|0.433017|QUALITY_FAIL|
|H01/B8|q2 / 24³ / 512|3.338580|12.924353|3.025396|QUALITY_FAIL|
|H02/B2|q0 / 8³ / 128|4.258719|25.697658|-10.339301|QUALITY_FAIL|
|H02/B2|q1 / 16³ / 256|5.709265|34.450448|-14.576081|QUALITY_FAIL|
|H02/B2|q2 / 24³ / 512|7.320067|44.170228|-22.058980|QUALITY_FAIL|
|H02/B8|q0 / 8³ / 128|5.428363|26.840175|0.334327|QUALITY_FAIL|
|H02/B8|q1 / 16³ / 256|4.865762|24.058436|7.245891|QUALITY_FAIL|
|H02/B8|q2 / 24³ / 512|4.034632|19.948973|3.948592|QUALITY_FAIL|

All-pixel inclusive gates stay total NRMSE≤5%, indirect NRMSE≤10%, absolute
indirect signed bias≤5%. No excluded pixels, changed seed, threshold, budget,
setting, reference or implementation. Every lower-rung loss is retained;
first PASS or exhausted q2 stops each target. No extra rung/retry or tuning.
Passing targets: none. Exhausted targets: H01_T_B2, H01_T_B8, H02_T_B2, H02_T_B8.
These are configured finite-stage implementation outcomes, not a general
DDGI-family conclusion. Quality losses do not enter a matched-quality speed
branch or become speed/memory wins.

The 12 captures retain 624 raw payload hashes,
36 complete f64 error maps, 32,648 completed GPU units and
96 full-copy atlas checks. All 226,492,416 post-copy components,
including 68,419,584 border components, exactly equal CPU expectation.
Pre-copy borders are+0, interiors unchanged, initial history+0 and later previous
arrays identical to preceding current arrays. All physical state/configuration/
packed constants/layout/disjoint ray coverage/raw/PFM/composite checks pass.
Original16384spp four-seed reference means and8192/16384consecutive admission,
complete support/physical/camera/provenance proof remain unchanged and replayed.
No references were rerun. Per-component support/leak/p99 diagnostics and every
error pixel are retained in each full audit row.

Owned true peak≤431,872,912bytes, complete persistent-pair ledgers,
≤8GiB cap and zero teardown. All250msGPU-unit/180snative-process guards pass.
Native setup/AS/update/readback/cooperative-gap timing is diagnostic and
uncalibrated; no accepted complete product-lifetime speed comparison. Actual
corrected executable/build054/shaders056 and full20control qualification067/068
are unchanged. Its admission remains registered finite-stage/reset-all only;
no temporal accumulation/scrolling/history-reuse or general dynamic/device claim.

**Next named case: h03-b2-q0**. 2 corrected targets remain unresolved. Each next process needs its own CPU plan, explicit announcement and independent terminal audit.

Total independently audited new assistant-operated GPU acquisitions 106
=94through011+12corrected012quality captures, under explicit user authorization.
Original human-operated evidence keeps attribution. Raw captures, error maps,
immutable plans and compact proof tars remain in repository/out; no large raw
data in Git. No power/clock/desktop changes, automatic queue, retry, overwrite,
CI/Actions or default Renderer integration. Prior actual CPU tests/builds not
rerun; these 12 quality captures and complete independent CPU replay actually ran.
Default Renderer build/runtime regression NOT_RERUN; validation layers NOT_RUN.
One Radeon8060S/RADV STRIX_HALO/Mesa26.1.2 only. Verification 078 records
index/source/provenance checks. No accepted timing, superiority or architecture
promotion. New dynamic/Sponza/representative-device strata, temporal limits and
historical Sponza direct relative-error1.0/timing uncertainty remain unresolved.
