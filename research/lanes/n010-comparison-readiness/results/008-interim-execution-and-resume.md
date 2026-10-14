# N010 interim execution evidence and remaining readiness gates

Status: active; not READY. N010 is the final preparation study before Lane M GI competitiveness.

## Executed diagnostics

N009 evidence remains immutable. Diagnostic 001 is the first approximate camera reconstruction; 005 corrects it to reproduce N008 float32 camera target addition and edge nudge. Both are explicitly post-hoc CPU diagnostics, not a repaired GPU correctness PASS.

| Cell | GPU zero / reference positive | GPU positive / reference zero |
| --- | ---: | ---: |
| C1 | 8 | 95 |
| C2 | 12 | 119 |
| C4 | 8 | 95 |
| C5 | 8 | 94 |
| C7 | 0 | 1 |

Both backends have the same counts. On the correctly reconstructed oracle positions, the legacy shader-sized shadow offset blocks every 8/12/8/8 direct-zero pixel; the oracle-sized offset clears all of them. It also removes occlusion on most reference-zero leak pixels (C7: the single leak pixel). The Sponza legacy offset is about 0.09266 world units. This identifies a numerical shadow-origin bias mechanism; a corrected production GPU path remains to be validated. Additional float camera/position differences are retained. N009 still records those pixels as unresolved under its own final decision.

## New GPU key/replay validation

10 new C1/C2/C4/C5/C7 captures, software and hwrt. The actual composite keys are exported, avoiding inference from CPU float expressions. Independent all-pixel integer aggregation replay passes V1 on every capture: maximum absolute error <=2.3283064365386963e-10, zero positivity disagreements, no excluded pixels. Primary-hit and all three image-component bytes equal the corresponding N009 captures; atomic producer payload order differs and is not silently attested equal.

For C7, the new key-driven R0–R6 model passes V1/V2/V3/V4 on both backends. R0 maximum error 2.48694e-14; R6 indirect sum bias +0.0295135%. CPU reconstruction disagrees with 6,824 actual lookup keys, although most do not change energy. The new validation is result 007; N009 PT remains INCOMPLETE and its excluded-pixel sensitivity remains post-hoc. Global R6 closure does not imply per-pixel GI correctness or improve the incumbent estimator.

## Memory instrumentation pilot

Both owned Vulkan allocation factories are instrumented with an allocation/free lifetime ledger. A C7 software capture has 92 events, one device context, exactly zero live allocations at teardown, and independently replayed high-water mark 266,694,400 bytes. Startup peak 262,341,952 bytes; source and target-frame peaks 262,086,432 bytes; the higher final peak includes explicitly separate diagnostic readback staging. Persistent live memory before readback is 262,086,400 bytes. Driver-private and CPU heap allocations are outside this owned Vulkan measure. New RC topology captures and the independent native PT/dense RC roles also have allocation ledgers with zero teardown. Result 017 independently replays every RC pilot allocation event. The controlled dynamic cohort and all 29 independent memory replays are complete (019/020); accepted comparative timing remains unfinished.

## Reference validation: original crosscheck failed

The sampling-only randomized Sobol oracle compiled. New analytic A2/A2b/A4/A8 controls and sealed-room/no-leak/positive-room controls passed. A6/A10 multi-bounce furnace and A7 quadrature also passed. Result 003 completed: A7 RQMC/iid indirect NRMSE 1.0117949% fails the fixed 1% gate; A6b passes. All independent physical controls pass. Post-hoc quadrature diagnosis gives RQMC 0.0344588% and iid 1.0115377% NRMSE, supporting an iid precision explanation. Original failure remains preserved. Prospective Amendment 2 fixes both iid controls at 16384 samples with unchanged thresholds and an exact 8192 checkpoint identity requirement; result 009 confirms both controls PASS (A7 0.7127081%, A6b 0.0882790% NRMSE), with exact equality of every original 8192 checkpoint. Qualification uses this disclosed amendment; result 003 remains FAIL. Do not claim total-reference eligibility from these controls. Initial lock 004 remains its historical partial snapshot; complete construction lock 016 now records C1–C12. Camera precision Amendment 1 applies prospectively to new Renderer-state reference images. C7 T_B2 and T_B8 pass at 8192 and 16384 consecutively; C8–C12 pass both transports at 8192/16384. Sponza C1/C3 T_B2 pass at 16384/32768; their T_B8 ladders and the remaining Sponza cells are active.

## Executed comparison cohort and measured losses

Native HWRT pixel path tracing is executable on the identical frozen states,
with independent cosine/point-light transport and complete static Renderer
GPU timestamps plus an allocation ledger. C7's full fixed budget ladder is
result 013: T_B2 first meets all quality targets at 256 samples (total NRMSE
1.9431%, indirect 9.9581%, indirect sum bias +0.2343%); T_B8 at 1024 samples
(total 1.4431%, indirect 5.5750%, sum bias -0.0599%). All failing levels remain.

The incumbent's new C7 output fails: one-bounce indirect NRMSE 98.0719%,
indirect sum bias -91.0257%. Its historical vanilla-software variant is a
traversal control retaining the same producer/storage, not an independent GI
baseline. A separately frozen dense cache-free repository RC estimator is
now executable (experiment 007 / result 015); it too fails C7's quality gates.
It is not claimed to be external production RC. No same-quality speed win is
reported for a quality-failing renderer.

The corrected direct profile removes C7 support disagreements. C1 incumbent
still has two GPU-zero/reference-positive pixels (max relative error 1.0),
**unresolved and included in all scoring**. Native independent pixel PT has
zero direct support disagreements there, direct whole-image NRMSE 3.912e-7.
This new diagnosis does not revise N009's unresolved final result.

New Sponza local light motion was selected using only geometry/direct support
under prospective experiment 006; N009 C3 remains NOT_CONSTRUCTIBLE.
C8–C12 provide actual non-Sponza camera/light/rigid/deforming/churn transitions.
All 24 additional source/target acquisitions succeeded; raw state bytes agree
between HWRT incumbent and historical vanilla control. Sponza C6 GPU target
bytes exactly match N009's CPU-exported target state.

C1 T_B2 now has eligible quality comparisons: incumbent/dense RC FAIL, pixel
PT PASS at 256/1024 spp. [Current findings](033-interim-comparison-findings.md)
include the retained losses, remaining gates and AMD/Vulkan SDK status.

## Required work before READY

The [continuous completion driver](../../../../scripts/research/n010_comparison_readiness/README.md)
queues the remaining qualified pilots and then quiet sizing / one accepted
calibration campaign. Existing original CPU acquisitions remain active. Cache equivalence 022 is
now complete and PASS for all 20 declared cases: all f64/component PFM bytes
and integer counters match. Incremental proof 050 is still running, so the
new prefix variant has now passed complete proof 050 and started fresh
C2/C4/C5/C6 acquisition. No incremental reference is qualified yet.
The original-only driver was retired while idle with no acquired jobs (059).
Its retained snapshot is `out/research/n010-comparison-readiness/continuation-reschedule-v1/old-driver-status.json`.
The updated driver uses the fixed full-corpus reference view 061 and lives at
`out/research/n010-comparison-readiness/continuation-v2/status.json`.
New output identifiers in that script are reservations until actual acquisition;
no READY or completed calibration is implied. The driver stops on a failure,
preserves it and requires review before any repair or new accepted acquisition.

Prospective [Amendment 6](../experiments/014-amendment-6-incremental-reference-prefix.md)
adds a separately built oracle that resumes exact prefix sums. Build 049
passes; complete equality proof 050 passes all three declared cases, all four
seeds and all 21 payloads/counters per case. Fresh incremental C2/C4/C5/C6
acquisition is running with 12 threads in `references-incremental-v1` (060
is reserved until an actual result is written). The original C1/C3 jobs remain
active. A separate retirement watcher is prepared to stop the C7/C1/C2/C4/C5/C6
original runner only after C1 T_B8 reaches its eligible pair or full frozen cap;
any subsequent original partial attempt and all prior evidence will be retained.
No original binary/output is overwritten. New fixed scheduling view 061
contains all 24 transports, with pending links explicitly not eligibility.

- Complete both active reference ladders over all locked T_B2/T_B8 cells; retain failed/capped levels.
- Carry the shared numerical profile into all scored roles; measure all residual discrepancies without exclusions.
- Complete the Sponza source/target/recovery sequences; controlled C8–C12 sequences, update costs and memory replays are executed in 019/020.
- Execute the full corpus quality/time/memory pilot, with fixed-cost and same-quality selection; specify DDGI/RTXGI integration for Lane M.
- Calibrate the actual complete Renderer timing boundary after reference computation ends and produce a fail-closed Lane M readiness preflight.

Pilot GPU timestamps remain **DIAGNOSTIC_UNCALIBRATED**. CPU reference work was
active, and the additional-corpus/dense-RC GPU runners briefly overlapped.
No speed comparison is accepted from those measurements.

Builds and the stated GPU/CPU checks were executed by the assistant under user authorization on Radeon 8060S / RADV Mesa 26.1.2. No human-only measurement is implied. No power/clock changes or CI workflows. No default Renderer promotion. No N001–N009 result edits.

## Development/failed attempts retained

- The initial C1 GPU capture completed its GPU writes but was explicitly terminated in the legacy N007 CPU audit. Raw gpu-key-pilot/C1-software remains; the expensive unused audit is omitted by the isolated N010 main thereafter.
- First v2 campaign stopped on the invalid Renderer scenario name deforming; the empty failed directory was retained as C5-software-invalid-scenario. The corrected scenario is deforming-control. All subsequent captures include acquisition source, binary hash and return code.
- The initial RQMC overlay failed compilation because it referenced an unavailable fail helper; it was corrected to throw before any validation rendering.
- A commit authorization review timed out; the permitted retry succeeded. No unsafe-action rejection occurred.

## CPU acquisition scheduling (055)

At 2026-10-14 10:07:35 UTC, the two original qualification parents and their
current oracle children changed from nice 0 to +5, after checking exact process
identities. This lets the eight-thread prefix equivalence process retain its
CPU share. Both original acquisitions continue with their binaries and outputs
intact. No transport, sampling, output, GPU, clock or power settings changed;
CPU wall times throughout remain acquisition diagnostics. The fixed incremental
C2/C4/C5/C6 scheduling view was subsequently executed only after 050 passed
(061); it records scheduling and does not assert readiness.

## Executed rescheduled preflight (063/064)

Both interim executions are NOT_READY. The first 063 invocation used a
nonexistent diagnostic sizing path; it is retained, and 064 uses actual 035.
The corrected invocation passes correctness/disclosed discrepancies and
additional-family source gates. Reference eligibility, full Sponza dynamic
cohort, complete C1 two-transport ladder and accepted timing remain missing.
No GPU acquisition/calibration was attempted or retried by either preflight.
The updated final driver still requires the original accepted calibration
029 and full pilots before 047 can assert readiness.

C1 T_B8 16384 has now completed: maximum active absolute p99 noise
5.0374791e-5 and relative 3.6234475%. Absolute 1e-5 remains unmet, so this
level is retained as ineligible and the unchanged next level proceeds.
This does not change a threshold, drop the deep-transport stratum or
qualify a reference from a relative-only pass.
