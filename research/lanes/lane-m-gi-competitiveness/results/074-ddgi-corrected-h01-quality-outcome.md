# M001 corrected DDGI H01: both finite quality ladders exhausted

2026-10-23. The unblinded [012 continuation](../experiments/012-ddgi-corrected-quality-continuation.md)
now retains six independently valid quality acquisitions, in unchanged order
H01/B2/q0,q1,q2 then H01/B8/q0,q1,q2. All are **QUALITY_FAIL** after complete
physical/reference/runtime/copy/memory admission. This extends [071](071-ddgi-corrected-h01-b2-quality-outcome.md);
no old result or reference is replaced. [Full replay073](073-ddgi-corrected-h01-quality-raw-replay.json)
rehashes all native evidence and recomputes every metric and full error map.

|Target|Rung / grid / rays|Total NRMSE %|Indirect NRMSE %|Indirect signed bias %|Outcome|
|---|---|---:|---:|---:|---|
|H01/B2|q0 / 8³ / 128|3.732623|19.132680|-13.495426|QUALITY_FAIL|
|H01/B2|q1 / 16³ / 256|5.836618|29.917344|-9.509769|QUALITY_FAIL|
|H01/B2|q2 / 24³ / 512|3.180520|16.302717|-3.906366|QUALITY_FAIL|
|H01/B8|q0 / 8³ / 128|5.796078|22.437824|-9.701864|QUALITY_FAIL|
|H01/B8|q1 / 16³ / 256|4.796461|18.568110|0.433017|QUALITY_FAIL|
|H01/B8|q2 / 24³ / 512|3.338580|12.924353|3.025396|QUALITY_FAIL|

The inclusive all-pixel gates remain total NRMSE≤5%, indirect NRMSE≤10%,
absolute indirect signed bias≤5%. Both q2 cases pass total/bias but fail indirect.
**Stop both targets at exhausted q2**: no extra rung, seed, mask, threshold
change, retry or matched-quality DDGI timing branch. These observations concern
this finite-budget corrected implementation, not a general DDGI-family loss.
More budget is not monotonically better on H01/B2; no cause or tuning is inferred.

The six actual captures retain312 raw payload hashes,18 full f64 error maps,
16,324 completed GPU units and48 full-copy atlas checks. Every one of113,246,208
post-copy components, including34,209,792 border components, equals CPU expected
output bit-for-bit. Pre-copy borders are+0, interiors unchanged and previous
stages immutable. Complete physical/layout/constants/disjoint coverage/raw/PFM/
composite checks pass. All original16384spp four-seed means and8192/16384consecutive
admission/support/provenance replay unchanged; references were not rerun.
Direct NRMSE3.170989533437041e−7 and maxabs5.664375897853919e−10 satisfy the
independent physical tolerances for all six captures.

Owned peaks8,084,368 /78,289,808 /431,872,912bytes by rung; all complete ledgers
pass≤8GiB and zero teardown. Every250msunit/180sprocess guard passes. Timestamps,
AS/setup/readback/cooperative-gap data remain diagnostic and uncalibrated, not
accepted complete-lifetime timing. A quality failure cannot become a speed or
memory win. All saved scores/maps/raw captures and immutable plan/result tars
remain under repository/out; no large data enters Git.

The full20control corrected runtime qualification067/068 remains intact and
its frozen source/shader implementation is unchanged. Old010scores and missing-
border-audit contradiction050/051 remain separate, unchanged and scientifically
superseded. H01 has two completed loss targets, zero passes; four corrected
quality targets remain unresolved. **Next H02/B2/q0**, separately CPU-planned,
explicitly announced and independently audited before any selection. The original
010 target/rung order and first-PASS/exhaustion rule remain fixed.

Total independently audited new assistant-operated GPU acquisitions100:
94through011 plus six012captures. Explicit user workstation authorization;
no power/clock/desktop changes, automatic queue, overwrite, retry, CI or default
Renderer integration. Prior actual CPU tests/builds are not rerun; these six
GPU captures and complete CPU replay actually executed. Default Renderer build/
runtime regression and validation layers NOT_RUN. Verification075 records
applicable index/provenance checks. One Radeon8060S/RADV device only. No accepted
timing, architecture promotion, general superiority or Lane M completion;
broader dynamic/Sponza/device strata, temporal limits and historical direct/
timing issues remain open.
