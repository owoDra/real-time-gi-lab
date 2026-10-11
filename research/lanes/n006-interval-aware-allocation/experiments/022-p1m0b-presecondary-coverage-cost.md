# N006 P1m0b — prospective pre-secondary consumer-coverage placement and GPU cost

Issue #42; frozen on 2026-10-11 **AFTER** M0 five-scene accepted counters [030](../results/030-p1m0-five-scene-coverage-pass.md) and **BEFORE** P1m0b GPU execution. Strictly a technology/cost eligibility test, **not P1 marginal quality, scheduling GO or P2 throughput**.

## Exact GPU stage placement and isolation

Use accepted P1j-A SW lean hash + copyback; one target frame following 32 source / eight target-state warmups in each of the same five frozen scenarios. Single N006 opt-in `--p1m0-pretrace-coverage` **requires** `--p1m0-consumer-coverage`. New pre-secondary GPU pass is inserted **after** (a) accepted N003 primary hit shader and (b) canonical index/compact/copyback/finalize and **before** ray_to_work + E003 secondary traversal. The same existing read-only M0 GLSL shader reads primary hits, current canonical 32768-slot hash and same camera uniform, writes new disjoint 32768×4-byte scratch slot counters and 8×4-byte summary stats. Explicit 0-fill and transfer→compute/compute→compute barriers are included. Nothing writes primary hit, accepted ray items, hash keys, storage or image.

Shader invocations: 320×180 pixels ×4 cascades; exactly the same hash + quantization + bounded probe contract as M0. GPU timestamp queries **20/21** on original 24-entry Vulkan query pool surround **GPU clear + shader + barriers**. Queries 0..19 unchanged. The in-frame `ray_prepare_gpu` and `complete_gi_gpu` timings will necessarily **contain the counting pass**; therefore call all complete-GI timestamps *instrumented*, not accepted uninstrumented performance. Report independent additional scratch **131104 bytes** = 131072 uint32 count bytes +32 stats bytes; memory allocation/initial upload and full CPU orchestration **not** included in timestamp and must be separately accounted for before a final scheduler ROI claim.

After the frame, run original separate postframe M0 diagnostic and demand **exact all-slot uint32 byte equality** AND **all 8 stats equality** with pre-secondary signal. Final image and original primary bytes must remain exactly unchanged, target one N004 sampled hit oracle/correctness preserved. Check new per-key SHA + successful and consumed key counts against immutable M0 acceptance [030], not merely self-consistency. All five `pretrace_executed=true`, `pretrace_slot_byte_equal=true`, `pretrace_stats_byte_equal=true`, accepted backend-specific PFM digests, no invalid/error counts, frame-stage timestamp conservation: **5/5 or no conclusion**.

## Prospective cost feasibility gate (NOT quality or net ROI)

For each case let `C = pretrace_clear_and_count_gpu_us`, `T = instrumented traversal_gpu`, `G = instrumented complete_gi_gpu`. Mark `within_predeclared_limit` only if **`C <= min(0.10*G, 0.50*T)`** with finite positive GPU timestamps. Conservative exploratory bound that requires the signal to remain a modest fraction of GI / tracing work; this is not a physical speedup guarantee and does not authorize ray allocation by itself. Report both actual C and the limit, including failures. If any >limit, `pretrace_cost_gate_status=over_predeclared_limit_no_m1_go`: refuse M1 scheduler experiments pending a prospective redesigned cheaper selector. Do not select a relaxed threshold based on measured performance. Even if all are under limit, formal P1 quality and equal-K P2 comparisons remain mandatory.

The original postframe 5-scene coverage histogram selection (60 calibration-only zero/low/high tokens) is frozen from original HEAD `8a5cb25` and raw attached summary SHA `f355b7202e52127b044120ac8406e5dba4626dd88f4cf29a78f16abbc2c66cec`, **no marginal gain labels**. The signal is screen lookup eligibility, not successful radiance storage hit, not global/temporal usefulness.

## Executable

```bash
git switch research-n006-interval-aware-allocation
bash scripts/research/n006_interval_aware_allocation/run_n006_p1m0b_pretrace.sh
```

Script checks clean branch, fast-forwards, builds, runs all N006 unit tests then `run_p1m0_consumer_coverage.py --pretrace`. Summary location: `out/research/n006-interval-aware-allocation/p1m0b-pretrace-coverage-five-scenes/<UTC>/n006-p1m0-consumer-coverage-summary.json`. Retain errors and per-case stdout/stderr. No legacy E003/B1 re-benchmark, no PR, no Actions. **No actual GPU M0b evidence exists as of source freeze.**
