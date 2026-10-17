# N010 prospective eight-wide CPU execution prototype

2026-10-17 JST; prepared while original sealed-dark252 runs. Register before
any prototype compile/native. Neither252 inputs nor any original code changes.
No prototype may execute until252 and253 are both terminal physical PASS and
the ordinary no-other-research-worker guard passes. There is no waiting queue.

## Hypothesis and distinction from stopped candidates

Profiles240/241 locate about46% of original A6a/C1 samples in slab predicates
and27% in the rest of traversal. SIMD xyz243 and batched boxes245 preserve
the binary parent events and fail the operational<=0.75 cost condition.
This distinct topology collapses internal levels into an eight-entry frontier
and removes the skipped-parent/index/packet-cache events. This may reduce
execution cost; no speedup is assumed or transferred from the profiles.

Use AVX512F, observed in the host's readable CPU flags, only in isolated opt-in
copies of224's header. Keep original binary BVH construction, exact double
boxes, leaf order, WatertightRay triangle arithmetic, closest-hit tie rule,
physical target, sampler, RNG/count/seeds and all other header bytes. Keep
the entire original BVH class as query comparator and scalar fallback. No
default Renderer/build/shader or historical-source modification.

Build each wide frontier by expanding the shallowest internal entry until
eight entries or only leaves remain, retaining original DFS lane order.
Before use, guard finite/ordered original bounds, parent/child containment,
index range and exactly-once original leaf coverage. Retain all original
double endpoints, including signed zeros. No float conversion, compressed
bounds, reciprocal approximation, fast-math, FMA contraction or changed epsilon.
Vector per-axis NaN/outside/swap/min/max/far-widening semantics follow the
original scalar slab. Cached lower intervals are compared at the current
nonincreasing tmax. Negative/reversed tmin intervals, nonfinite rays and
single-leaf roots use unchanged scalar traversal. A512-entry explicit stack
has a runtime overflow guard. Valid lanes are always masked.

Removing parent tests depends on containment and monotone slab operations;
that reasoning alone does not admit this backend. In a verifier build,
compare EVERY executed valid-lane box predicate and EVERY consumed cached
predicate against original scalar slab at its actual interval. Pair every
closest result (triangle and binary64 distance bits) and occlusion boolean
with the complete original BVH. Any mismatch stops without a cost claim.
Preserve partial evidence; do not relax numerical identities to rescue it.

## Fixed bounded acquisition and stop rule

Reuse original223 C1 eight fixed pixels,8192spp,four seeds, selected-path
exporter body and exact entire retained data.json identity. The independently
compiled standalone exporter then repeats exactly236's original A6a8spp,
four seeds,whole128x96. All21 f64/PFM/hit payloads and all integer/proposal
audit metadata must be byte/value exact. Compile flags: C++20,O3,
-mavx512f,-fno-fast-math,-ffp-contract=off,-pthread; no other target tuning.

One scientific worker/CPU31,nice15,4GiB; each compiler/native <=360CPU and
480elapsed seconds, four invocations maximum (paired build/native, standalone
build/native). Preserve commands, sources, source inverses, resource/exit/
CPU/elapsed receipts and all output hashes. No retry or subsequent full-control
queue; stop on identity/resource/build/native failure. The per-child limit
accounts for newly added wide-lane predicates; it changes no physical gate.

Operational execution-promising condition stays prospective
`standalone_A6a_CPU / retained236_A6a_CPU <=0.75`. This is a bounded offline
resource decision from an uncontrolled retained single-run comparison, not
a scientific GI speedup or environmental stability criterion. A failure stops
the candidate. A PASS requires later full original physical/state/prefix/
reference qualification; none is transferred merely from selected C1 rays.
All17 original artifacts and all24 reference slots remain required.

Driver: scripts/research/n010_reference_sampling/diagnose_wide8_cpu_bvh.py
Include: scripts/research/n010_reference_sampling/wide8_cpu_bvh.inc
Work: out/research/n010-comparison-readiness/wide8-cpu-bvh-v1
Result:254-wide8-cpu-bvh-prototype.json (absent until actual dispatch).

Timing250 stays inconclusive. Direct-relative1.0 pixels stay UNRESOLVED/未解決
and included. No GPU work, settings/power/clock/display/app changes, N011,
Actions or N001–N009 result edits. Tests NOT RUN: this registration prepares
scientific query/identity acquisition, not release regression validation.
