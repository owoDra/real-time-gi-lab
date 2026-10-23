# M001 six heldout PT ladders — quality selection complete

The original independent GPU pixel PT satisfies every frozen HDR gate on all six static heldout targets. All three B2 conditions first pass at256spp; all three B8 conditions first pass at1024spp. This is a PT quality result, not an incumbent RC win or accepted timing. Full Lane M and M001 remain incomplete pending other fixed controls, DDGI scene admission and broader heldout strata.

[Raw replay022](022-six-pt-ladders-raw-replay.json) independently re-audits all33 complete native cases, all594 raw payload hashes, archived plans/receipts, original physical reference proof, exact captured state, all-image metric/error maps and allocation/free ledgers. It exactly reproduces each original intake report. There are6PASS and27QUALITY_FAIL; all failures remain. Every cell follows the unchanged1/4/16/64/256/1024 prefix and stops at its first PASS. No missing stage, trial beyond a PASS, retry, overwrite, seed change or pixel exclusion.

| Cell / transport | First PASS spp | Total NRMSE | Indirect NRMSE | Indirect bias | Owned peak bytes |
| --- | ---: | ---: | ---: | ---: | ---: |
| H01 / T_B2 | 256 | 1.942% | 9.954% | +0.226% | 2,370,160 |
| H01 / T_B8 | 1024 | 1.432% | 5.543% | -0.090% | 2,370,160 |
| H02 / T_B2 | 256 | 1.615% | 9.747% | +0.037% | 2,370,160 |
| H02 / T_B8 | 1024 | 1.147% | 5.669% | -0.199% | 2,370,160 |
| H03 / T_B2 | 256 | 2.148% | 9.962% | +0.001% | 2,379,312 |
| H03 / T_B8 | 1024 | 1.312% | 5.355% | +0.130% | 2,379,312 |

H01/B2 and H03/B2 indirect error is close to the10% gate. These are literal frozen one-seed quality decisions, not confidence bounds or evidence of a robustness margin. The original four-seed16384 references remain unchanged; no repeated candidate seed was requested to improve a borderline result. Every native memory ledger has26 events, peak≤8GiB and zero teardown; CPU and driver-private memory are excluded.

Acquisition followed [005](../experiments/005-frozen-quality-step-execution.md). Initial H01/B2/1 source5955ea02 and plan019 remain unchanged; later units use committed driver77de6970. The collector source is5bc5d81a. All new GPU images were executed by the assistant on the explicitly authorized workstation without power/clock changes. The exact-target native context rejects fallback devices. A separate read-only Vulkan inventory observes Radeon8060S / RADV / Mesa26.1.2 and is hashed in022; the old native binary does not serialize full per-process device/driver provenance, which remains a timing-admission limitation. No timestamp number is accepted as a speed result; setup/readback and other lifecycle costs still need the separately frozen actual-boundary calibration.

The retained fixed HWRT RC remains QUALITY_FAIL in all six targets ([017](017-reference-and-retained-incumbent-outcome.md)). Therefore no PT/incumbent quality-matched timing pair exists. Independent dense RC, vanilla and software control captures remain NOT RUN at this checkpoint; DDGI remains unqualified. Dynamic/Sponza/multiple-device heldouts and broader architecture competitiveness are not established.

All raw outputs, error maps, started/terminal records and compact tars remain in repository/out; no large raw images are committed. CPU validation:35 scoped tests PASS, including five selection tests covering missing prefixes, continuation after PASS, incomplete/invalid evidence and exhausted loss. Default build was not rerun because source/shader/CMake/active Renderer behavior is unchanged;018 retains the prior successful build. No new release runtime regression claim follows.
