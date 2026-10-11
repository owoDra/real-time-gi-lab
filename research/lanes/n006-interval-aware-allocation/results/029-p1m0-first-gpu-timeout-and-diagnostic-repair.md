# N006 P1m0 initial five-scene run — 0/5 INVALID, static exceeded 600s; diagnostic revision

Issue #42. 2026-10-11. Input: user-uploaded `n006-p1m0-consumer-coverage-summary.json` from the user's own AMD Radeon 8060S Graphics (RADV STRIX_HALO) system. This is **failed-run provenance**, not successful GPU evidence, not benefit ranking or speed.

## Immutable input and evidence

- Runner protocol: `n006-p1m0-consumer-coverage-five-scenes-v1`.
- Clean branch: `research-n006-interval-aware-allocation` at **`bd4aae067cb51a6729d06ee885c884bf63c46ba5`**.
- Sponza source SHA256 **`2a86fdc2dc92d7c6a740682c61ec97f3101f489a06443c6823aff85bb990e5f6`**.
- Intended five scenes: `static`, `camera-motion`, `light-motion`, `moving-rigid`, `deforming-control`; each 32 source + 8 target warmups.
- **`status=invalid-retained`**, `cases=[]`, `failures=[{"scenario":"static","error":"P1m0 static exceeded 600s"}]`. No completed canonical coverage frames. Candidate rays added 0; independent HDR reference not generated; `formal=false`.
- Timestamped local evidence directory: `out/research/n006-interval-aware-allocation/p1m0-consumer-coverage-five-scenes/20261011T035058Z/`; exact existing child paths `static/stderr.log` and `static/stdout.log`. Neither child log was uploaded. The old runner's `capture_output` + timeout did not surface the last child progress stage in the JSON.
- Prior static B1c, C0 and synthetic f32 outputs repeat their accepted previous findings; C0 still `ready_static_only / MATCHED`. They do not change the diagnosis and must not be counted as new independent performance samples.

## Root-cause investigation (source-supported, not trace-proven)

The new C++ P1m0 mode already uses per-scene stabilized warmup count (fix to previous exact-4,172 deforming-only gate). But `p1l_sampled_hit` in `n006_intervention_main.cpp` **omitted** `p1m0_coverage`, so the eight target warmup frames each invoked expensive `runtime.n004_hit_diagnostics()` while B0/P1l sampled-fast purposely skips N004 hit oracle during warmup. This is a credible cause for 600s wall-time exhaustion. **Cannot conclude precisely where the prior run stalled without the child stderr or a trace**: initial source creation, a CPU check, Vulkan shader compile/submit/wait, or another stage may also be responsible. No accepted M0 measurement.

## Prospective corrective revision

1. Add `p1m0_coverage` to **sampled-fast correctness** only, not to P1l exclusive stage-set: source/target warmups use `frame_core_correct` and count/stability checks without repeated CPU N004 hit-oracle; target frame index 0 still executes `runtime.n004_hit_diagnostics()` and image SHA/payload/full semantic closure required in M0 runner. No reduction of target fidelity.
2. Instrument local renderer `[P1m0-stage]` emitted to stderr, flushed around runtime construction, 32 source warmups, each of 8 target warmups, canonical target, N004 target oracle, PFM write, consumer diagnostic, and `[P1m0-GPU]` around primary/image readback, scratch upload, shader pipeline, submission, fence wait/signal, post-dispatch readback and accounting. Experimental stage diagnostics only; no accepted shader modification.
3. Replace `subprocess.run(...capture_output=True...)` with live file stream handles `stdout.log`/`stderr.log`. Retain original 600s cap; on timeout, include complete absolute paths plus bounded tail of both existing logs **in the propagated failure and in the JSON**. Users can locate the last completed stage from one failure report. No silent timeout extension.
4. Add test source contracts for sampled-hit warmup exclusion / target-only hit and stage logs; correct ambiguous C0 "blocked evidence retained" log on actual MATCHED PASS.
5. Keep original M0 5-scene gate, full accepted image/primary and hash accounting; if new run still stalls, investigate exact last stage. **Do not broaden the deadline**, synthesize M0 quality labels or authorize P1m1/P2 before 5/5 PASS.

## Status

**P1m0 INVALID 0/5 pending rerun; P1m1 calibration-only code ready but cannot be evaluated yet.** E003 C0 static provenance remains PASS (no GPU improvement inferred). Issue #42 OPEN, no PR, no GitHub Actions. Original N001/N003/E003 accepted shader sources unchanged.

