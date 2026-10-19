# Thread-private reference audit: preparation and isolated build only

2026-10-19 JST. Prospective execution-only candidate. Preserve452/525/526
and all candidate/native results, including the currently running145 seed1.
No threshold, sampler, point/normal, density, support, Jacobian, compensation,
physical target, pixel/sample order or reference/convergence rule changes.

Retained371 is ONE seed/full320x180/16spp:53.289984CPU and53.512358443003905
elapsed seconds. Simple scaling to four8192 seeds is109137.887232CPU /
109593.310091272elapsed seconds, above032/158's43200elapsed ceiling.
This is POST-HOC cost planning from the older uncompensated backend, not
candidate throughput, a feasibility verdict, ETA or an intrinsic GI loss.
Ideal2/4-way wall estimates54796.655045636/27398.327522818 are optimistic
models with unmeasured overhead, contention and frequency effects. Do not
launch the known oversized legacy route or relax the original stop limit.
Candidate full-frame/two-level feasibility remains required.

`prepare_thread_private_reference.py --prepare` writes621 in fresh
thread-private-reference-source-v1. Copy exact452 full and525 prefix C++
sources. Move only the two diagnostic witness coordinates to thread_local;
keep the witness-enabled flag read-only during render. Add explicit private
WholeAudit/primary-prime references to sample_all_split, preserving its
entire body byte-for-byte. Retain the old wrapper signature for serial callers.
Use each worker's own audits/primes and merge after all joins: integer sums,
per-key integer map sums, finite nonnegative maxima, all strategy/depth arrays
and all five direct counters. No floating radiance sum is reduced across
workers. Full and prefix per-pixel caches/RNG/net/sample/statistics loops
stay identical apart from passing the private audit references. Every row
still has one owner via the existing atomic row allocator. Paired debug
BVH mode remains serial; it has separate mutable counters.

Permit1..4 render threads in this PRIVATE candidate only. This is source
capability, not permission to increase actual CPU load. The unanswered CPU
preference retains one CPU; no render or worker-count change is dispatched
by this plan. Source preparation is allowed during145 at CPU31/nice15/
120CPU/180elapsed/2GiB; prove exact whole-header inverses and unchanged
sample_all_split body plus physical/geometry/density block bytes. Pin the
entire WholeAudit/RenderCounters layouts so no audit field is silently lost.
Record all substitutions, original/generated hashes and compiler commands.

`--build` is future622, quiescence required. Compile the two private targets
serially with the exact452/526 compiler/flags, changing source/output paths
only. Each220CPU/300elapsed/4GiB, CPU31/nice15, actual own PID/PGID/start/
boot/command/resource and terminal stdout/stderr/hash receipts. Timeout
signals only a verified owned group. No scientific rendering/next queue/
retry, resource extension or default-build/settings change. Build failure
preserves partials and stops before the next compiler stage.

Before any scientific use, separately register and execute exact full-output
and scored/proposal-audit equivalence against retained candidate data,
all full physical controls, all-state/exact-prefix proofs and full-frame
feasibility at actual approved CPU load. Single-thread source identity or
successful compilation is not proof of multithread correctness, scaling,
all-split bias or reference eligibility. Existing candidate13/17 and refs16/24
do not automatically qualify this execution candidate. Original failures and
all scope/gates stay. Sponza direct-relative1.0 remains UNRESOLVED/未解決,
included. N010 then distinct Lane M, no N011/Actions/CUDA/N001–N009 edits.
Tests NOT RUN; source preparation/private builds are not runtime validation.
