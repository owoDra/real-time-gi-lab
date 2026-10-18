# N010 all-split density identity and numerical scope

2026-10-18 JST; source checkpoint8c7a9416. Classification:
**SOURCE_BASED_IDEAL_DERIVATION_ONLY / NO_ADMISSION**. No new acquisition,
numerical execution, threshold, or reference gate. This AI-assisted source
review is not an external independent audit or a finite-arithmetic bias bound.

## Source examined

The active original CPU snapshot is
`out/research/n010-comparison-readiness/wide8-cpu-bvh-v1/n010_rqmc_oracle.hpp`,
SHA256 `40607186e96cad47e9386b4fcd78a71958894946a237e628c546566819970537`.
It matches [254](254-wide8-cpu-bvh-prototype.json)'s pinned payload. Relevant
functions are `N010NetRng::uniform`(896), `whole_state`(978),
`whole_coincident`(992), `whole_density_prefixes`(1084),
`whole_sample`(1258) and `sample_all_split`(1340).
The [078 physical/proposal specification](../experiments/078-all-split-general-transport-and-prefix-reuse.md)
and explicit [072](../experiments/072-coincident-geometric-support-audit.md)/
[074](../experiments/074-axis-cosine-support-audit.md) approximations govern.
The snapshot and live260 inputs were not modified.

## Conditional area density

Consider the ideal continuous formulation, fixed primary hit, nonemissive
Lambert materials, one point proposal source and original depth limit1..8.
Let x=(x1,...,xk) be k raw surface hits in eye order,1<=k<max_bounces.
All strategies must use the SAME geometric surface measure for this x.
In particular, overlapping equivalent patches cannot silently be counted
once per coincident primitive in one strategy and once geometrically in
another. Exact equivalence is an assumption here; the implementation's
approximate primitive matching is discussed below.

Condition on all previous raw hits and the current chain state. Its canonical
source origin o, oriented normal, self-ignore and range are then fixed.
For a visible next raw point y on a surface with unit geometric normal ng,
write r=|y-o| and w=(y-o)/r. The ideal conditional area density is

`p_A(y | state) = p_omega(w | state) * abs(ng dot w) / r^2`.

For cosine sampling, p_omega=max(0,n dot w)/pi. The first point-source edge
uses1/(4*pi), followed by the same cosine rule. A miss, out-of-range point,
wrong visible surface or zero directional density gives zero support.
The code accumulates log(pdf)+log(target_cosine)-log(distance_squared).

The target is the RAW hit, not its subsequently nudged spawn. The nudge and
offset determine the NEXT conditional origin. They do not require a second
Jacobian factor for this current hit: the previous state is fixed when
changing the current direction to current surface coordinates. This argument
does not certify how finite precision reconstructs or matches that raw hit.

## Strategy mixture and physical target

For split s in0..k, generate k-s hits from the primary and s from the point
source; reverse the latter chain to form x. Conditional on the split, the
two chains use disjoint coordinate pairs in the ideal uniform input.
Let E_i be the eye-prefix density and L_j the reverse light-prefix density.
Their ordered product gives

`q_s(x) = E_(k-s)(x1,...,x_(k-s)) * L_s(xk,...,x_(k-s+1))`.

Empty prefixes have density1. Prefix caching reuses these same ordered
products; it does not add, omit or sample a connection edge. The sampled
strategy's logarithmic density is checked separately against q_s in source.

With continuous uniform u0, s=floor((k+1)*u0) has probability1/(k+1), and
v=(k+1)*u0-s is uniform conditional on s. Thus the remapped v can supply
the first direction coordinate without an extra net dimension. There are
exactly2k direction coordinates, up to14. The ideal mixture density is

`q_mix(x) = sum(q_s(x), s=0..k) / (k+1)`.

Let A_k(x) be the ORIGINAL all-eye path's RGB contribution: primary rho,
the product of intermediate rho values, and original endpoint direct
reflection including endpoint rho/pi. Preserve every original one-sided
front/back decision, visibility, point falloff, canonical origin and range.
In this restricted nonemissive scope the original ideal component is

`I_k = integral q_0(x) * A_k(x) dA(x)`.

The implemented ideal balance weight is

`w(x) = q_0(x)/q_mix(x) = (k+1)*q_0(x)/sum(q_s(x))`.

Where q_0>0 the mixture has support, because it includes q_0. For finite
nonnegative densities,0<=w<=k+1. Therefore, under exact support/density
evaluation on the common measure,

`E_(x drawn from q_mix)[w(x)*A_k(x)] = I_k`.

Null chains contribute zero; their missing continuous mass is not renormalized
away. Black/back-facing physical paths also contribute zero. Keeping their
geometric proposal densities does not turn them into physical reflection.
The isotropic point direction is a proposal choice, not a replacement for
the original physical point-light law in A_k. Likewise the light chain's
unbounded first range does not change the original all-eye target's range.

Primary direct remains a separate deterministic original component. Reusing
the14 coordinates across different k introduces correlation; linearity of
expectation is sufficient for summing the ideal component identities. It
does not justify treating correlated path/depth observations as IID trials.

## What this identity does not establish

1. **Actual RQMC is finite.** The source uses32-bit Sobol words, deterministic
   seed/pixel/dimension XOR shifts, and midpoint values(x+0.5)*2^-32. For a
   split count not dividing2^32, the finite midpoint grid is not exactly a
   continuous uniform split distribution. The ideal change-of-variables
   identity is not a zero quadrature-bias proof for that grid or four fixed
   shifts. Per-sample second moments are not IID standard errors. Preserve
   the registered replicate/convergence protocol; do not invent a new SE.
2. **072/074 are explicit approximations.** They accept restricted coincident
   axis-plane support with identical materials/nudge/spawn and a32epsilon
   normal allowance. Signed-zero-dependent tangent maps need not be bit
   identical; ideal azimuth rotation preserves continuous cosine density,
   but does not certify identical finite maps. Alternative-ignore ray/direct
   checks cover evaluated rays. They do not prove an exhaustive equivalence
   relation or equality of all future finite-arithmetic transport operators.
   The common-measure assumption above cannot silently establish that result.
3. **Own-density checks are insufficient alone.** Matching the selected q_s
   within1e-6 checks that selected density, not every cross-strategy q_j,
   visibility decision, mixture denominator or numerical bias. The conditioned
   plane/reconstruction audit is also not a forward-distance or radiance bias
   bound. Large unconditioned errors remain visible in the retained evidence.
4. **A CPU/GPU match is not independent physical truth.** Both can share the
   same approximation. The actual372 counter mismatch and candidate380 remain
   separate implementation diagnostics; this derivation does not repair them
   or identify the missing shadow sample/ray. It also does not resolve Sponza's
   separate direct-relative1.0 pixels.

## Consequence for the existing completion path

This review supplies the conditional ideal density/weight derivation and its
source mapping. Independent density/numerical-bias admission remains open.
Do not label the finite implementation unbiased or replace physical controls
with this text. No new tolerance or extra admission obligation is introduced.

Continue the existing original full controls, independent A6b IID comparison
from [107](../experiments/107-retained-a6b-independent-iid-replay.md), numerical
assessment of the declared support approximation, all24-state/exact-prefix
and genuine full-count feasibility/intake, then unchanged eligible-reference
screens and full quality/dynamic/memory/timing evidence. The prospective
[handoff timing amendment120](../experiments/120-reportable-comparison-readiness-amendment.md)
separates valid timing evidence from precision; its final adapter is still
unimplemented. A passing finite IID
comparison has its specified empirical scope, not a proof of zero global bias.

Original260 is still running at this review. References16/24; full physical
artifact inventory14/17 includes a diagnostic-only item. **N010 NOT_READY**.
Direct-relative1.0 pixels remain **UNRESOLVED / 未解決** and included.
No N011, Actions, default Renderer/build changes or N001–N009 result edits.
Build, tests, new numerical/CPU/GPU acquisition: **NOT RUN**. Source review
and the pinned snapshot's SHA comparison only; AI-assisted provenance follows
the repository [workflow disclosure](../../../../docs/ai-research-workflow.md).
Metadata-only `python scripts/research/verify.py`: eight configured indexes /
288 declared links OK; `git diff --check`: clean. These are not runtime checks.
