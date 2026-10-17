# N010 prospective exact-query near-first CPU execution prototype

Date:2026-10-17 JST. Parent:066d156. Before build/acquisition.
236 measures175.254CPU seconds for six cost-only probes, projecting36.984CPU
hours for their original full counts. No such long native is queued.

Change only the isolated CPU BVH traversal implementation. Keep the original
tree builder, triangle order/coordinates, binary64 watertight intersection,
slab arithmetic (including NaN handling and widening), intervals, ignores and
closest-hit/lower-ID ties. Duplicate slab solely to return its already
computed t0. Pretest children using that same calculation; cache entry bounds
on the fixed128 stack and visit the nearer surviving child first. Cached
entry>current_tmax prunes because closest tmax only decreases; occlusion limit
is constant. No altered arithmetic in physical sample/direct/proposal methods.
Traversal-order sensitivity from any latent numeric slab issue is possible:
do not assume operator identity from this argument alone.

Retain an exact copy of the original Bvh as LegacyBvh in the generated isolated
header. A verification build invokes both for EVERY closest/occluded query and
requires identical hit triangle and all t bits, or identical occlusion bool.
Any difference/overflow/guard stops; no masking or tolerance. Prove the whole
header inverse and every class edit inverse. This changes executable traversal
source; do not claim original BVH bytes unchanged or general all-rays proof.

238 runs four serial steps, oneCPU nice15/4GiB/220CPU/300elapsed each:
1 compile the query-paired version of original223 main;
2 run the exact original C1 eight-pixel8192/four-seed prototype, preserving
  223's per-sample legacy/general component/depth comparisons. Require paired
  closest and occluded counts both>0 and data.json byte-identical to223;
3 compile unchanged224 exporter main with the optimized traversal and the
  additional original-query calls disabled at compile time;
4 original A6a128x96/eight-sample/four-seed cost probe, all21 f64/PFM/hit payloads
  byte-identical to236 A6a, original native metadata/counters/proposal audits
  unchanged except paths/timing. This is not full8192 A6a.

Freeze execution-promising condition: step4 measured childCPU <=0.75 times
236 A6a42.641725CPU seconds. This is a NEW prospective operational sizing
condition for this execution optimization, not a GI performance decision or a
change to any physical/statistical/quality/timing gate. A retained single-run
comparison is planning evidence, not a controlled speedup claim. On negative
do not start full controls with this variant. No retry/concurrent worker/GPU.
Save PID/start/limits and native exit/CPU/elapsed/stdout/stderr/payload hashes
before analysis; retain partials. Never rerun after an observation timeout.

Work:out/research/n010-comparison-readiness/near-first-cpu-bvh-v1
Result:results/238-near-first-cpu-bvh-prototype.json
Driver:scripts/research/n010_reference_sampling/diagnose_near_first_cpu_bvh.py

Even positive proves only these exact queries/payloads. Full physical/bias/
all-state/prefix/whole-frame feasibility and original qualification remain;
no reference admission, default Renderer/CMake integration or READY. Original
method full physical inventory11/17; references16/24,timing208FAIL,direct1.0
UNRESOLVED/未解決 included. Unit/regression tests NOT RUN; isolated scientific
execution-equivalence/cost prototype only. No settings/apps/display/clock/
power/N011/Actions/historical-result changes.
