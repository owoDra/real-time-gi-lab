# N006 P1l-C0c — E003 active compiled-SPIR-V provenance PASS; optimization cause NOT established

Issue #42; 2026-10-11. This is **user-supplied command output** from the local AMD research checkout after `run_n006_next_verified.sh` ran to the first P1m0 scenario. Original 210 N006 Python unittests PASS in 0.417 s. The following C0/B1c audit results are accepted **for metadata only**, not a new real-GPU performance measurement. Full original audit JSONs and compiled SPIR-V bytes have not been uploaded, so the source/ABI comparison has not been independently cryptographically reproduced.

## C0 static compiled-shader verification

- `status=ready_static_only`, `provenance=MATCHED`: C0's locally rebuilt original E003 source-produced SPIR-V SHA matched the runtime-named `e003_instance_quantized.spv` artifact on the user's research checkout. This closes the previous *missing/unmatched active binary* blocker for that checkout.
- `accepted_e003_rebuilt`: **36,072 bytes**, SPIR-V **OpFDiv=7**.
- `b0_count_only`: **38,404 bytes**, SPIR-V **OpFDiv=7**. Instrumented binary is **2,332 bytes larger**; count-only instrumentation is not the production shader. OpFDiv count equal 7 is a **static instruction declaration count**, not a dynamic count per ray/node/child and not an AMD disassembly. Do not claim reciprocal-hoisting, shader VGPR count, cache transactions or GPU occupancy.
- CPU-only `audit_p1l_c0_division_rounding.py`: deterministic 200k float32 model produced **51,445 differing entries (25.7225%)** and a constructed slab accept/reject boundary at sample index 7. This reconfirms the earlier [027](./027-p1l-c0b-f32-slab-rounding-risk.md) model; does not prove GPU parity or actual scene hit divergence.
- Previously REJECTED N003 primary B1a static SPIR-V relative to accepted: binary **+1,136 bytes**, instruction count **+61**, `OpLoad` **+18**, `OpBranchConditional` **+1**. B1c relative to accepted: **+1,100 bytes**, instructions **+74**, `OpLoad` **+16**, `OpBranchConditional` **+3**. These are B1c static output counts only, not an explanation for the previously observed GPU REJECT. Compiler/backend hardware work is unmeasured here.

## C0 outcome

**C0 source/binary verification ACCEPT as static gate only**. No C1 GPU intervention or shader rewrite was justified by an opcode histogram (no demonstrated dynamic E003 hotpath or safely bit-identical proposed arithmetic rewrite). The parent lane's predictive additional-ray contribution remains an open primary research objective. Continue `experiments/020` P1m0 and conditional `021` P1m1, not speculative E003 optimization.

## Separate P1m0 local run regression, now patched

First scenario `[P1m0] static (1/5)` child renderer exited **1** (no child stderr uploaded), thus no valid M0 coverage evidence. Github C++ source identified one deterministic bug: target warmup check for P1m0 still used legacy P1h's hardcoded 4,172 visible owners/133,504 work items/16,688 outputs, whereas the accepted frozen STATIC geometry has **4,167** owners; previous P1l dynamic scene-aware path was gated on `p1l_stage_any`, excluding P1m0. Fix changes **both** target warmup count and stabilization branches to a shared `scenario_counted_target = p1l_stage_any || p1m0_coverage` while leaving old P1h fallback unchanged. Missing stderr means **actual fault location was not directly confirmed**; this source guard is a highly plausible deterministic cause, not proof that no subsequent M0 issue exists. Separate runner now prints timestamped absolute stdout/stderr path and renderer failure excerpt to console. New static regression tests added. **No revised C++ build or local GPU run has yet verified this fix**.

No PR, no CI/Actions, no accepted shader or HWRT baseline changes.
