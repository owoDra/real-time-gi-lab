# Prospective CPU reference sampling proposal: geometry/direct-light guidance

Motivation is post-hoc: original C1 B8 remains ineligible at completed 32768
spp (absolute active p99 3.54031e-5, fixed limit 1e-5). Its frozen cap outcome
is unmeasured. Original acquisitions continue; no old result is revised.
Before any new sampler output, register this separate sampling-only candidate.

## Question and physical boundary

Can a fixed mixture of cosine continuation and geometry/direct-light surface
sampling reduce replicate noise while preserving the independently validated
N008 finite-transport integral? This is an offline reference method, not a new
incumbent Renderer or an existing-GI performance baseline.

Keep canonical binary64 geometry, SAH BVH/order/intersection/ties, primary,
Lambert reflectance, camera, near/far boundaries, sidedness, edge inset, ray
offset, black background and deterministic point-light next-event evaluation.
Only the continuation sampling distribution and its importance weight change.
Centre camera, point-light-only, finite T_B2/T_B8; no emissive/box-camera claim.
Use the original cached oracle generation as the source, in a fresh directory.
Do not rewrite original source, generated headers, binaries or running inputs.

## Fixed proposal and estimator

Cosine branch probability is **0.75**. The other **0.25** selects a triangle
from a fixed CDF using world geometry and authored point lights only. CDF
weights mix **0.10** normalized triangle area with **0.90** normalized
area × centroid point-light irradiance proxy × maximum material reflectance.
Use absolute light-facing cosine for two-sided faces, positive cosine for
one-sided faces, and the declared point falloff. If the irradiance proxy sum
is zero, use area alone. No visibility, indirect image or candidate output
enters the weights. Record constants and implementation identity before outputs.

Remap the branch/CDF uniform to a conditional uniform barycentric coordinate;
use the second uniform for the other coordinate. This consumes exactly two
dimensions per continuation, retaining the same 16-dimensional shifted Sobol
table, four seeds and nested sample-index schedule. Sample triangles uniformly
in area using square-root barycentric sampling.

The surface proposal has null events: below-hemisphere directions, miss, or
first hit differing from the selected triangle contribute zero downstream.
They remain samples in every mean/moment. For a successful first hit i,
`p_surface = P(i) * t^2 / (area(i) * abs(dot(ng, direction)))`; t is the true
ray intersection distance from the offset ray origin, not the edge-inset
shadow/shading point. The cosine branch uses the same visible-first-hit
surface density in its mixture denominator. Other, occluded triangle samples
are null outcomes, so their angular densities are not added to that denominator.

At the next hit, multiply continuation throughput by
`p_cosine / (0.75*p_cosine + 0.25*p_surface)` in addition to the original rho.
This is a single-sample mixture estimator on the visible-surface-plus-null
domain. Cosine support remains everywhere the original integrand is nonzero;
the weight ratio is bounded by 1/0.75. Keep point-light NEE unchanged; this
does not apply a surface PDF to a delta point-light source. Mathematical basis:
[PBRT single-sample MIS](https://pbr-book.org/4ed/Monte_Carlo_Integration/Improving_Efficiency)
and [area-to-solid-angle conversion](https://pbr-book.org/4ed/Shapes/Triangle_Meshes).
These sources support the general estimator/conversion; the null-domain and
deferred-weight implementation here require independent physical validation.

## Gates before corpus qualification

Build with C++20, O3, no fast math, no FP contraction. No default build change.
First run every applicable original point-light physical control, all four
seeds, the original sample counts and fixed independent analytic/support gates.
Compare A7/A6b against the retained, unchanged 16384-spp iid controls from 009:
regional mean relative difference <=0.002 and indirect NRMSE <=0.01. Preserve
every failure. CPU control runner may use four threads to limit concurrent load.
Build success or a derived unbiasedness argument is insufficient for admission.

Before full acquisition, verify direct/emission/primary identities on the
locked states and exact nested-prefix reproducibility for this sampler; its
stochastic indirect means/moments/counters need not match the cosine sampler
per seed. No new sampler qualification may use old per-sample moments or an
old cosine prefix. Replicate means define uncertainty, not iid per-sample SE.

Any future acquisition retains the exact 24-slot corpus, four seeds,
8192/16384/32768/65536/131072/262144 ladder, absolute active p99 <=1e-5,
relative <=5%, stable support and first two-consecutive-pass stop. A cap
failure remains INELIGIBLE. No full corpus output is authorized by a passing
isolated control alone; a separate executed provenance/scheduling transition
is required before comparison use. Existing CPU and GPU proof chains remain
separate. No N011, CUDA, power settings, Actions or architecture promotion.
