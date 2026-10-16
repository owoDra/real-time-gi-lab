# N010 prospective later-bounce control-variate diagnosis

Date: 2026-10-17 JST. Parent: `22254d6`. Register before this prototype build
or sampling. Packed-readback 199/200 completed build/sizing PASS; complete
201 still FAILS all seven original precision gates. That timing candidate
stops. No full 186, old acquisition restart or long GPU work is authorized.

## Supported mechanism and question

191 locates most observed C1 replicate disagreement after the first indirect
bounce. 194 shows the failed importance guide reduces total per-path variance
slightly while losing observed RQMC variance reduction. 195 supplies no strong
nested-scramble gain. Keep the original cosine Sobol sample mapping and use
an analytically zero-mean conditional correction at later vertices instead.

At a reached vertex j=1..6 in finite B8, predict reflected direct radiance
at its next hit using a fixed 4 by 4 partition of the cosine sampler's (u,v)
square. One deterministic center direction per bin is evaluated using exact
original closest hit, sidedness, material, secondary far, nudge/offset and
point-light direct evaluation. Misses/backfaces/zero rho predict RGB zero.
Let g_x(u,v) be that bin's prediction and H_x its sixteen-bin arithmetic
mean. Add `throughput * rho * (H_x - g_x(u,v))` to indirect output, keeping
the actual sampled path and every later original contribution unchanged.

Conditional on the path prefix x, uniform cosine-square coordinates give
E[g_x]=H_x, so this correction has zero conditional expectation. No importance
weight, density remapping, pilot contribution to physical radiance, RNG draws,
extra scored camera samples or clamping is introduced. Current corpus is
point-light-only; the prototype refuses emissive sources. Primary continuation
j=0 is unchanged: first-indirect error already has strong observed net
reduction. T_B2 has no applicable later continuation and remains unchanged.
Finite B8 depth and rho=1 are unchanged. Pilot cost must be retained.

This argument does not establish implementation correctness, useful covariance,
lower RQMC uncertainty, nonnegative finite-sample means or reference eligibility.
Corrections and individual corrected samples may be negative. Preserve them;
do not clamp or relax physical/qualification mean/moment requirements. Full
independent physical/state/prefix proofs remain required for a reference method.

## Bounded prototype 202, no admission

One fresh directory `later-bounce-cv-diagnosis-v1`, result
`202-later-bounce-cv-path-diagnosis.json`. Start from exact original diagnostic
header and main in 193, with the original cosine/digital-shift mapping.
Instrument an optional RGB correction output without changing original path
outputs, moments, counters, geometry, light evaluator or RNG consumption.
Verify the whole header/main inverse and exact retained original means and
second moments for every consumed record. If reconstruction fails, stop.

Freeze eight non-tail pixels from 193's fixed grid:
(40,30), (120,30), (200,30), (280,30),
(40,150), (120,150), (200,150), (280,150).
This selection is independent of candidate outputs. Exactly 8192 camera
samples and the original four N007 seeds. Sixteen pilot bins, one midpoint,
coefficient 1, later continuations only: no parameter search or tuning after
seeing this output. Retain all eight pixels, including zeros, all four seeds,
original/corrected means and second moments and original bounce diagnostics.

One CPU, nice 15, 4 GiB address space, 220 aggregate CPU seconds and 300 elapsed
seconds per compiler/native invocation. Record actual PID/start/limits and
all binaries/data/inputs. At most one compile and one native acquisition. An
operational failure retains partials and stops without automatic retry.
No GPU work, concurrent scientific worker or default build change.

Report paired-replicate p99, replicate variance and descriptive per-path
variance for original and corrected estimators. Classify only whether this
small diagnostic is promising: finite records, exact original reconstruction,
p99 ratio <=0.75 and replicate-variance ratio <=0.75^2. This prospective
triage rule is not a new corpus/reference threshold, formal feasibility or
powered superiority proof. A negative result stops this fixed prototype; a
positive result still needs independent controls, all-state/prefix proof,
full-image two-level feasibility and all unchanged pending ladders.

All 24 slots, original seeds/six levels/262144 cap, active p99 <=1e-5 / <=5%,
stable support and two consecutive qualifying levels remain. No N010 READY,
timing admission, incumbent repair, N011, CUDA, Actions or N001–N009 changes.
Direct error-1.0 pixels remain UNRESOLVED / 未解決 and included. Unit/runtime
regression tests are NOT RUN; this is a scientific diagnostic prototype.
