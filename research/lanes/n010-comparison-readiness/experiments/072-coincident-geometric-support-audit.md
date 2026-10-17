# N010 prospective geometric support audit for coincident axis planes

Date: 2026-10-17 JST. Parent: `80bf283`. Before compile/acquisition.

## Evidence and explicit numerical amendment

210/212 remain INCOMPLETE; 211/213/214 remain post-hoc diagnoses. 214 proves
same spawn bits and material for the witnessed pair, but one-ULP unequal
normals and mapped directions. Do not claim exact numerical operator identity.
No partial means are used for selection or tuning. This plan changes prototype
support matching from primitive identity to a restricted geometric-point audit.
It is a numerical approximation requiring later independent physical controls,
not a proof that N008's finite-arithmetic transport has identical expectation.
Original scientific/promising/eligibility thresholds are unchanged.

Keep all original sampling, raw points, densities, family probability1/2,
physical sample/direct/BVH/nudge/offset, eight pixels,8192/four seeds and all
original moment controls. Original primitive IDs are retained for every
state; neither canonicalize geometry nor project points nor discard samples.
The target area is a geometric surface measure, not the sum of coincident
primitive areas. No multiplicity weight is added.

On a closest-hit ID mismatch, permit support only if both triangles lie
EXACTLY on the same coordinate-axis plane, both projected barycentric tests
place the raw target strictly inside their triangles, and material fields
match exactly. The original nudge and canonical spawn at the same raw point
must agree bit-for-bit. Face-forward normals must agree within32*epsilon
and Duff basis sign(n.z) must match; record the actual maximum, including
nonzero differences. Both spawns must lie at least offset/2 into the oriented
half-space. This does not assert equal cosine maps; 214's one-ULP difference
remains. Axis-plane restriction avoids any approximate coplanarity merger.
The conditioned256*epsilon plane/reconstruction audit from069 and generated
own log-density error<=1e-6 remain unchanged.

Retain both IDs on an accepted match. On its following density-reconstruction
ray, repeat the actual original BVH query with the alternative ignored ID and
require identical hit ID and t bits (or both miss). On a forward endpoint,
repeat original direct with only the alternative ignored ID, SAME normal and
spawn, and require bit-exact radiance and identical shadow counters. These
checks cover the evaluated rays, not all possible outgoing rays; do not claim
an exhaustive finite-BVH equivalence proof. Original normal is never replaced.
Record match counts, pair identities, normal differences and these checks.
Unaccepted mismatches keep zero support; an own-family zero still stops.

## One bounded prototype215

Work `whole-path-geometric-support-diagnosis-v1`; result
`215-whole-path-geometric-support-diagnosis.json`. One compiler/native, one
CPU nice15,4GiB/220CPU/300elapsed per invocation; no retry or concurrent worker.
All source, input, binary, receipts, partial stdout/stderr/data are hashed even
on failure. Whole source inverse preserves original physical sample exactly.
Original32 means/second moments must equal193 bits; deterministic components
match exactly. Report original unchanged prospective promising rule:
p99 ratio<=0.75 AND replicate-variance ratio<=0.5625. Negative stops this
fixed construction. Operational failure is INCOMPLETE, no variance verdict.
A positive prototype is NOT admission: independent density/physical controls,
all24-state/prefix proof and full-frame two-level feasibility remain required,
including a numerical-bias assessment of this explicit support approximation.
No full-frame ladder or GPU work is authorized by this plan.

16/24 references; timing208FAIL; direct1.0 pixels UNRESOLVED/未解決 and included.
No N011/Actions/default build/N001–N009 edits or settings/app/display/power
changes. Unit/regression tests NOT RUN; isolated scientific prototype only.
