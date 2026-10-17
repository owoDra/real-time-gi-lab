# N010 prospective SIMD slab execution prototype

Date:2026-10-17 JST. Parent:b99ada7. Before any candidate acquisition.
240/241 locate about46-47% of original A6a/C1 user CPU samples in box slabs,
27% in remaining traversal and18% in triangle intersection. The former090
near-first candidate is stopped (cost ratio0.981664 >0.75); do not retry it.

New candidate vectorizes the original box predicate across xyz with AVX2.
Keep original SAH builder, exact boxes, node/triangle left-first order, stack,
WatertightRay arithmetic, double precision, no fast-math/FMA, intervals,
ignore/tie policy, RNG/proposals/counts/outputs unchanged. Pack immutable box
copies into64bytes/node, included in actual process4GiB guard; do not claim
zero memory cost or Renderer/GPU memory benefit. Padding axis is ignored.
Preserve original NaN-axis outside/skip rule and far widening4epsilon, then
reduce near/far intervals. The monotone interval predicate motivates equivalence;
actual full query/t-bit/boolean and per-node comparisons below are mandatory.
Signed zeros/order, exceptional numeric inputs, compiler lowering and limited
ray coverage remain risks; no universal arbitrary-ray proof is claimed.

Preserve original Bvh exact copy as LegacyBvh. In paired build compare EVERY
executed visited node SIMD/scalar slab boolean AND original/new closest tri/t
bits and occlusion boolean. Any mismatch/nonfinite/audit failure stops. Same
original223 C1 eight fixed pixels8192spp/four seeds, all data.json bytes must
equal223. Then standalone exporter (no verification overhead) original236
A6a128x96/eight spp/four seeds: all21 payloads and all integer/proposal audits
must match236 exactly. Flags add only -mavx2 to original no-fast-math/no-contract
flags. Entire driver changes are strictly inverse-checked against sealed090.
This is authorized scientific execution diagnosis, not unit/regression tests.

Same operational adoption condition as090: measured standalone A6a CPU /
retained236 CPU<=0.75. This retained single-run sizing is not a controlled
speedup/GI comparison. A valid but insufficient candidate stops with no full
queue; no threshold tuning/retry. A pass only permits further original
scene/scalability checks, not physical/reference admission or full dispatch.
All original physical/statistical/GPU gates remain;11/17 physical,16/24 refs.

Serial compile,paired native,compile,standalone cost. OneCPU31,nice15,4GiB.
Each subprocess220CPU/300elapsed, save actual PID/start/limits/CPU/elapsed and
returncode before parsing; preserve all partials/failures, no retry. No GPU,
settings/power/display/app changes, default build, Actions or N011. Tests NOT
RUN. All source/header and original input/payload identities retained.

Work:out/research/n010-comparison-readiness/simd-slab-cpu-bvh-v1
Result:results/242-simd-slab-cpu-bvh-prototype.json
Driver:scripts/research/n010_reference_sampling/diagnose_simd_slab_cpu_bvh.py
Include:scripts/research/n010_reference_sampling/simd_slab_cpu_bvh.inc
