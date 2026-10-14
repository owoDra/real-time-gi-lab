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

Both owned Vulkan allocation factories are instrumented with an allocation/free lifetime ledger. A C7 software capture has 92 events, one device context, exactly zero live allocations at teardown, and independently replayed high-water mark 266,694,400 bytes. Startup peak 262,341,952 bytes; source and target-frame peaks 262,086,432 bytes; the higher final peak includes explicitly separate diagnostic readback staging. Persistent live memory before readback is 262,086,400 bytes. Driver-private and CPU heap allocations are outside this owned Vulkan measure. Dynamic replacement coexistence and comparative-role memory are not yet validated.

## Reference validation: original crosscheck failed

The sampling-only randomized Sobol oracle compiled. New analytic A2/A2b/A4/A8 controls and sealed-room/no-leak/positive-room controls passed. A6/A10 multi-bounce furnace and A7 quadrature also passed. Result 003 completed: A7 RQMC/iid indirect NRMSE 1.0117949% fails the fixed 1% gate; A6b passes. All independent physical controls pass. Post-hoc quadrature diagnosis gives RQMC 0.0344588% and iid 1.0115377% NRMSE, supporting an iid precision explanation. Original failure remains preserved. Prospective Amendment 2 fixes both iid controls at 16384 samples with unchanged thresholds and an exact 8192 checkpoint identity requirement; that confirmation is not yet a PASS. Do not claim total-reference eligibility from these controls. Initial state lock 004 is partial; camera precision Amendment 1 is prospective for new Renderer-state reference images.

## Required work before READY

- Finish all sampler controls and iid crosschecks; acquire and qualify the locked T_B2/T_B8 references.
- Complete light-motion/non-Sponza dynamic states and GPU topology-churn source/target attestation.
- Validate shared direct-light corrections; score remaining numerical discrepancies without hidden exclusions.
- Make vanilla RC and independent GPU pixel path tracing executable on the same corpus; specify the additional DDGI/RTXGI integration for Lane M.
- Execute full-image quality, complete Renderer GPU-time and all-role persistent/true-peak memory pilots.
- Calibrate the actual complete Renderer timing boundary and produce a fail-closed Lane M readiness preflight.

Builds and the stated GPU/CPU checks were executed by the assistant under user authorization on Radeon 8060S / RADV Mesa 26.1.2. No human-only measurement is implied. No power/clock changes or CI workflows. No default Renderer promotion. No N001–N009 result edits.

## Development/failed attempts retained

- The initial C1 GPU capture completed its GPU writes but was explicitly terminated in the legacy N007 CPU audit. Raw gpu-key-pilot/C1-software remains; the expensive unused audit is omitted by the isolated N010 main thereafter.
- First v2 campaign stopped on the invalid Renderer scenario name deforming; the empty failed directory was retained as C5-software-invalid-scenario. The corrected scenario is deforming-control. All subsequent captures include acquisition source, binary hash and return code.
- The initial RQMC overlay failed compilation because it referenced an unavailable fail helper; it was corrected to throw before any validation rendering.
- A commit authorization review timed out; the permitted retry succeeded. No unsafe-action rejection occurred.
