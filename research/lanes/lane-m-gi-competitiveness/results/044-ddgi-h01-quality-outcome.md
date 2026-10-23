# M001 DDGI H01 quality ladder: exhausted at both depths

2026-10-23. [Prospective010](../experiments/010-ddgi-static-quality-budget-ladder.md), [CPU preparation042](042-ddgi-quality-cpu-preparation.json), [independent raw replay043](043-ddgi-h01-quality-raw-replay.json). This is a partial cohort checkpoint; H02/H03 have not run.

H01/T_B2 and H01/T_B8 both exhaust all three fixed budgets with **QUALITY_FAIL**. Every next acquisition was separately prepared only after the preceding independent terminal audit. All six native captures are complete and physically/reference-eligible; no operational failure, retry, excluded pixel, changed estimator/threshold or skipped rung. The registered all-image gates remain total NRMSE≤5%, indirect NRMSE≤10%, absolute indirect signed bias≤5%.

| Target | Grid/rays | Total NRMSE | Indirect NRMSE | Indirect signed bias | Decision |
| --- | --- | ---: | ---: | ---: | --- |
| H01/T_B2 |8³/128|3.732623%|19.132680%|−13.495426%|QUALITY_FAIL|
| H01/T_B2 |16³/256|5.836618%|29.917344%|−9.509769%|QUALITY_FAIL|
| H01/T_B2 |24³/512|3.180520%|16.302717%|−3.906366%|QUALITY_FAIL|
| H01/T_B8 |8³/128|5.796078%|22.437824%|−9.701864%|QUALITY_FAIL|
| H01/T_B8 |16³/256|4.796461%|18.568110%|+0.433017%|QUALITY_FAIL|
| H01/T_B8 |24³/512|3.338580%|12.924353%|+3.025396%|QUALITY_FAIL|

Full-precision scores, direct/support/leak/active-p99 diagnostics and all18full error maps are retained. Direct NRMSE is3.170989533437041e−7 at every budget/depth. Increasing grid/ray budget does not monotonically improve error. This observation does not identify a single cause or authorize tuning the estimator on these heldouts. Do not infer the four remaining conditions' results from H01.

Replay actually rehashes264native payloads and16,228completed GPU units. It verifies exact physical/reference bytes and four-seed16384spp f64 means, all128/256/512official blend identities, packed counts/rays/rotation/formats/feature flags, SDK image dimensions, complete disjoint4096ray tile schedules, finite full arrays, initial-zero/immutable previous atlas, every pixel/PFM/composite identity and full allocation ledgers. All six ledgers have56events, true peaks8,084,368/78,289,808/431,872,912owned bytes at q0/q1/q2, independent of depth; teardown is zero. CPU/driver-private memory is excluded. Larger-budget runtime validity is established for these exact H01 cases only.

These six acquisitions were assistant-operated on the authorized Radeon8060S/RADV workstation without power/clock/desktop changes or automatic GPU queue. Total new acquisitions in this continuation are62, including the prior56 through dynamic qualification. Earlier human-operated evidence retains its attribution. Raw captures, error maps and compact proof tars remain in repository/out. No validation layer run or default Renderer build/runtime regression rerun; standalone host036 is unchanged and042actually executed70Python tests plus18native CPU-only budget contracts. The17unchanged native input tests remain prior038 evidence, not a new87-test runtime suite.

All per-unit timestamps and setup metadata are diagnostic/uncalibrated. This fresh static entry does not measure an accepted whole-workload/whole-process lifetime boundary; sums exclude cooperative queue gaps and cannot establish end-to-end speed. **Both H01 DDGI/PT timing branches stop as quality-ineligible.** Neither lower memory nor faster diagnostic units can turn these losses into speed wins. PT's existing first-PASS selections and the24fixed-RC quality losses remain unchanged.

Next exact permitted acquisition is **H02/T_B2/q0 (8³/128)**, following its own CPU plan, single GPU process and independent terminal audit. H02/T_B8 and both H03 targets remain NOT_RUN. Broader dynamic/Sponza/representative-device strata, temporal limitations and matched-quality calibrated performance remain open. M001/Lane M are incomplete; no architecture promotion or GI superiority result.
