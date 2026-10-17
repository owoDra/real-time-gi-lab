# N010 prospective batched-box CPU execution prototype

Date:2026-10-17 JST. Parent:1c4e1cd. Before new candidate acquisition.
Previous goal turn was PROGRESS:240 actual profiles and241 exact-code post-hoc
attribution identify box/traversal costs;243 passes billions of predicate and
query/output comparisons but CPU ratio0.902765 fails<=0.75. Stop243 unchanged.
Current process inspection confirms no native/controller/GPU worker remains.

Distinct design: batch original binary-tree box predicates across four nodes,
rather than three axes of one box. At alternating original internal levels,
pack the two children and up to four grandchildren into separate SoA packets.
Immutable original box bytes are copied; parent tree and triangle order stay.
Three ordered xyz vector steps preserve scalar swap, NaN-axis skip/outside,
first-operand max/min and4epsilon far widening. Unused lanes have an explicit
valid mask. Cache each positive node's tmin-clipped near entry and child results.
As tmax shrinks, re-evaluate cached entry at that node's original pop event.
Keep every original parent event: do NOT merge a parent's bound into descendant
entries or retest a parent after its first child. This avoids changing when
original parents can prune. Original builder, watertight intersection, leaf and
triangle order/interval/ignore/tie, RNG/proposals/counts/physical operators remain.
Preserve the exact original scalar traversal as an exceptional-interval fallback.
Normal oracle queries have0<=tmin<=tmax; no arbitrary-ray proof is claimed.

One-time CPU packet build/storage/index/stack costs included in standalone
process CPU; packed group>=384bytes plus alignment/mask,4bytes index/original
node,128 expanded stack entries. Original nodes retained. Resource guard4GiB
includes all overhead. No Renderer/GPU-memory benefit is claimed.

Paired build compares EVERY acquired valid packet lane to original scalar slab
at acquisition tmax, EVERY actually popped cached predicate to scalar at current
tmax, EVERY original/new closest triangle/t bits and occlusion bool. Any mismatch
stops. Original223 C1 eight pixels8192/four seeds; entire data.json bytes must
equal223. Then compile standalone exporter without verification; original236
A6a128x96/eight spp/four original seeds, all21 output payloads and original
integer/proposal audits exact. Strict original header/class/driver inverses.
The original Bvh remains as LegacyBvh in the paired build. No native retries.

Same prospective operational condition as090/094: standalone A6a CPU divided
by retained236 CPU<=0.75; a semantic pass with insufficient cost is stopped.
Single-run retained cost sizing is not an accepted controlled speedup or GI win.
PASS permits further original execution checks, NOT long full dispatch or
physical/reference admission. All scientific thresholds/caps/scene inventories
and original final six gates remain. Physical11/17,reference16/24,N010 NOT_READY.

OneCPU31 nice15/4GiB; serial compile,paired,compile,cost. Every subprocess
220CPU/300elapsed seconds. Record actual PID/start/resources, terminal CPU/
elapsed/returncode before analysis; preserve every failure/partial. No GPU,
power/display/app/settings/Actions/default build/N011/N001–N009 result changes.
Unit/regression tests NOT RUN; isolated authorized scientific execution checks.

Work:out/research/n010-comparison-readiness/batched-box-cpu-bvh-v1
Result:results/244-batched-box-cpu-bvh-prototype.json
Driver:scripts/research/n010_reference_sampling/diagnose_batched_box_cpu_bvh.py
Include:scripts/research/n010_reference_sampling/batched_box_cpu_bvh.inc

Early-rejected child boxes may be omitted from the stack: an initially rejected
interval remains rejected as tmax shrinks. Surviving original parent/triangle
events preserve their relative left-first order; no claim of identical rejected
node visits or identical internal instruction counts is made.
