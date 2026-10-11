# N006 P1l-C0a — E003 secondary wide-child static source/layout audit (2026-10-11)

Issue #42; `experiments/019`. **PASS: source/layout inspection; compiler/GPU causal cost NOT YET VERIFIED.** This is not C0 compiler-audit completion, nor a candidate GPU speedup. Work was done against research HEAD `edcbc7c46f80807b540a8562c1aedfa22a763a16` or its direct descendant before this report, *no E003 compiled SPIR-V was available in the assistant sandbox*.

## Directly checked code, as opposed to hypotheses

1. `b003_quantized_bvh8.hpp`: `B003GpuQuantChild` contains four 32-bit unsigned fields and has a C++ `static_assert(sizeof(...) == 16)`. `B003GpuQuantNode` has 16-byte origin, 16-byte scale, 16-byte metadata and exactly **eight 16-byte children**, C++ `static_assert(sizeof(...) == 176)`; shader `QuantNode { vec4 origin; vec4 scale; uvec4 metadata; QuantChild children[8]; }` matches the expected std430 scalar/vector layout. No claim about executed hardware memory transactions.
2. `e003_instance_quantized.comp.glsl`, `trace_segment`: **64**-entry token + entry-distance stack; node metadata axis controls reverse/forward loop order over exactly **8** children. Each non-invalid child unpacks three 16-bit lower and three 16-bit upper AABB coordinates, reconstructs world bounds with per-node origin/scale, then calls `ray_aabb_bounds`. The scalar slab function handles near-parallel direction with an epsilon guard, otherwise performs bounds-relative division `(mn-o)/d` and `(mx-o)/d` for each visited axis; early-out occurs if slab intersection empties. It pushes the child and its entry distance, then prunes popped nodes when entry exceeds best hit + tolerance.
3. The source already has a *direction-controlled* wide-child push order; another naive front/back sort is **not** a new mechanism. Compiler can CSE/hoist divisions, strength-reduce them or do neither, and GPU driver can lower SPIR-V further; **source alone cannot distinguish this**. Converting divisions to reciprocals changes floating rounding and may violate the accepted hit/PFM byte-equality contract; no C1 variant is written at this stage.
4. `e003_instance_payload.hpp` constructs quantized static/dynamic partitions and `translated_instance` moves one rigid instance. `e004_deforming_payload.hpp` builds target quantized partition and has bounded-node/hash updates; those CPU rebuild/upload costs must be reported if a C1 candidate adds metadata or changes quantization.
5. **Build provenance BLOCKER**: accepted runtime `n001_runtime.cpp` selects `e003_instance_quantized.spv` for software quantized instance tracing, yet current project CMake did not register the named source-to-binary build rule. The N006-only `n006_p1l_c0_e003_source_rebuild.spv` rule now exists. The C0 script compares its SHA to the actual loaded-named binary; missing or mismatched binary results in a written `blocked` audit. Without both binaries and a matching compiler environment, no compiler opcode-based optimization decision is possible. Past GPU campaign had correct accepted-output SHA, but that does **not** prove which SPIR-V bytes the process used.

## Existing independent work counts, not shader speed

From accepted [B0 result 021](./021-p1l-b0-five-scene-software-work-counts.md), for five scenes with **24,064 / 25,760 / 24,064 / 24,832 / 24,232** secondary rays:
- Quantized wide-node pops/actual ray **6.718–7.004**.
- Quantized child AABB tests/actual ray **25.532–26.304**.
- Segment hash probes/actual ray **3.412–3.441**.
- Triangle tests/actual ray **7.273–7.944**.
- Original uninstrumented E003 traversal single-frame descriptive GPU times **302–389 µs**, **not matched candidate comparisons**.

Worst-case source arithmetic is up to six scalar slab divisions per *tested child* when each of three nonparallel axes is evaluated; this is an *upper envelope of source operations* without compiler optimization or early exit, **not a count of GPU `OpFDiv` instructions executed**. Multiplying its bound by reported mean tests per ray cannot infer power consumption, time or performance gain.

## C0 next gate / independent parent work

1. On an intact local research checkout, `bash scripts/research/n006_interval_aware_allocation/run_p1l_c0_verified.sh` builds all shaders, runs C0 Python tests and writes the binary-provenance static audit JSON. Script aborts with failure if active E003 binary is missing/mismatched; **the evidence JSON is still saved**.
2. Share the audit JSON (or first build/unit-test failure); do not replace/overwrite active E003 to force a SHA match. Match => inspect static `OpFDiv`, control-flow and register possibilities but still no hardware-level proof. BLOCKED => isolate why the accepted runtime binary is unavailable/stale **before** C1. Either way, a new E003 C1 cannot be accepted without its own prospective correctness/timing gates.
3. In parallel, focus parent N006 on **probe×cascade marginal-ray label observability**. P1a gave 11/12 exactly unchanged frames and a 4.13×10^-10 one-case RMS gain despite correct intervention; P1b demonstrated storage dilution at shared key (151 owner outputs), and P1c established 81.85% exact duplicate ray inputs. The canonical path subsequently provided GPU savings, but **no predictive label ranking**. This independently blocks P2 scheduler adoption; don't conflate traversal speedups with N006 ray-allocation success.

No N003/E003 accepted shader math, HWRT, N004/N005, CI or GitHub Actions changes. No PR. **C0a source gate PASS; C0 compiler gate NOT RUN / P1 predictive-quality gate NOT RUN.**
