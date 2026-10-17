# N010 prospective all-split path mixture diagnosis

Date:2026-10-17 JST. Parent:b11e445. Before compile/acquisition.
217 completes the restricted half-eye/half-light prototype but FAILS its
original promising rule: p99 ratio0.845880, replicate variance0.819401.
Stop that fixed construction; no full-frame ladder or mixture tuning follows.
The next construction adds genuinely distinct middle connections, not a
post-hoc adjustment of the failed mixture probability or statistical gates.

## Common raw-surface path measure and proposal

Use067's original raw-hit variables, canonical nudge/offset/normals, point
soft falloff, rho1 target and independent ordered area densities. Retain
072/074's explicit numerical geometric-support approximation and069's
backward-error audit; these still require independent physical/bias controls
before admission. Do not claim finite-arithmetic operator identity.

For each indirect depth k=1..7, choose s uniformly from0..k. Trace e=k-s
cosine vertices from the fixed camera hit, and s vertices from the sole point
light (uniform sphere first, cosine later). Their raw vertices define the
ordered camera path: eye prefix followed by reversed light prefix. The
middle connection is NOT randomly sampled; forward visibility is part of the
target integrand. On failed native generation keep a zero contribution.
For strategy j, its common-area density is
q_j=E(prefix of length k-j)*L(reversed suffix of length j), empty product1.
Each ordered source normal/spawn/self-ignore/range is evaluated independently;
no reciprocity assumption. Original target F=q_0*R_k, with R_k original
point-direct reflected radiance at the full forward endpoint. Thus

    estimator_k = (k+1)*exp(log(q_0)-logsumexp(log(q_0)..log(q_k)))*R_k

on q_0 support, zero otherwise. q_0 covers every original target path, so the
weight is bounded by k+1<=8. For a selected strategy its density reconstructed
from the complete path must match the product actually generated, absolute
log error<=1e-6 (same guard). Keep all null connections and all samples.
No original physical method, geometry, ID, raw point or sampling normal changes.

For each scored net index read the same14 original net dimensions once.
For each k use floor((k+1)*u0) as s, remap (k+1)*u0-s as the first directional
coordinate, then original u1..u(2*k-1). Generate eye branch first, light next.
Uniform disjoint selection intervals and their affine remapping give the
required mixture law. Correlation across the seven integrals is allowed by
linearity; no iid-SE claim. This traces up to28 vertices per scored index,
versus seven in067; report this extra CPU work, not an equal-cost claim.
Same four seeds, nested prefixes and original scored index count. At each
k require8192 strategy selections; 1D digital stratification gives counts
floor/ceil(8192/(k+1)), checked explicitly. Record all counts and own checks.

## One bounded prototype218

Work `all-split-path-mixture-diagnosis-v1`; result
`218-all-split-path-mixture-diagnosis.json`. Same eight fixed C1 pixels,
8192/four seeds, same original193 baseline. One compiler/native invocation,
one CPU nice15,4GiB/220CPU/300elapsed, no retry or concurrent scientific worker.
Hash all source/input/binary/receipt/output bytes even on failure. Retain
full generated eye/light vertex witness on own-density abort. Exact physical
header/main inverses, original32 mean/second moments, primary deterministic
components, finite/nonnegative estimates and <=k+1 weights required.
Promising rule unchanged: p99 ratio<=0.75 AND replicate variance<=0.5625.
Negative stops fixed all-split construction with no per-scene weight tuning.
Operational failure is INCOMPLETE, no variance verdict. Positive is NOT
reference admission: independent density/physical/numerical-bias checks,
all-state/exact-prefix and whole-frame two-level feasibility precede any
original qualification ladder. No full ladder/GPU dispatch under this plan.
16/24 eligible, timing208FAIL, direct1.0 pixels UNRESOLVED/未解決 and included.
No settings/app/display/power/Actions/default build/N011/historical edits.
Unit/regression tests NOT RUN; isolated scientific prototype only.
