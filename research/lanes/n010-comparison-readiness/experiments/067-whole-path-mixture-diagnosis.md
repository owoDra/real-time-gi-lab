# N010 prospective whole-path two-family mixture diagnosis

Date: 2026-10-17 JST. Parent: `1fc4c25`. Before compile/acquisition.
Previous209 is terminal FAIL; its fixed local table stops. This construction
samples complete paths from either end, without a learned/local predictor.

## Integration variables and exact physical boundary

Prototype the same eight fixed C1 T_B8 pixels as202,8192 samples/four original
seeds. Point-lit, centre-sampled, nonemissive, opaque two-sided grey rho1 only;
reject other inputs. Every intersection, nudge, offset, direct visibility,
soft falloff and finite depth stays the pinned N008 implementation. No GPU.
The [PBRT BDPT chapter](https://www.pbr-book.org/3ed-2018/Light_Transport_III_Bidirectional_Methods/Bidirectional_Path_Tracing)
motivates light/camera subpaths and common-area density evaluation. This is
a restricted two-family sampler, not a complete PBRT BDPT implementation.
The following derivation is specific to this repository's numeric transport.

Use **raw first-hit points** x1..xk on triangles as integration variables,
not nudged/spawn positions; x0 is the fixed original primary hit. At each
vertex compute the original face-forward normal and canonical spawn position
S(x)=nudge_inside(triangle,x)+normal*offset. For an ordered step from the
current S to a raw target y, direction w=(y-S)/r and raw triangle normal N_y,
its conditional area density is

    p_A(y | prefix) = max(0,n_current dot w)/pi * abs(N_y dot w)/r^2

when the unchanged BVH closest hit with original self-ignore/range is that
triangle, otherwise zero. A subsequent normal/spawn is determined from this
ordered incoming direction. Offset/nudge is not dropped or inverted: because
raw target coordinates are integration variables and earlier prefix values
are held fixed in each conditional change of variables, source nudge affects
the origin but not this target-area Jacobian. The complete change-of-variables
Jacobian is triangular. Reverse kernels are evaluated explicitly; do not
assume reciprocity or equality of forward/reverse normals/spawns/support.

Let q_E,k be the product of these forward densities from fixed x0 to xk.
The original rho1 cosine estimator's k-th indirect contribution has area
integrand F_k=q_E,k*R_k, where R_k is the **unchanged** reflected point-direct
radiance evaluated at the forward canonical xk. The target is sum k=1..7.
In particular, keep cos/(soft_scale^2+d^2), not inverse-square emission flux.
Emission and direct primary components remain deterministic original values.

The other family selects the sole nonzero point light (prototype requires
one), emits uniformly on the sphere, and traces k raw vertices in reverse
order from light to camera. First-vertex density is abs(N dot w)/(4*pi*r^2),
using original BVH first hit and proposal tmin=offset. Later steps use the
same cosine-area formula with reverse prefix normals/spawns. q_L,k is that
ordered generative density, evaluated even when forward transport support
differs. The final connection to fixed x0 is evaluated by q_E,k; it does not
resample a pixel or splat to other pixels. Unsuccessful connections are zero
samples and remain counted.

Choose one family with probability1/2 using first coordinate. Remap it within
the chosen half; it remains the first cosine coordinate or uniform-sphere z
coordinate, paired with dimension1 for azimuth. Later pairs keep dimensions
2..13. One existing14-dimensional Sobol path per scored sample, same fixed
four seeds/net and nested prefixes; no extra scored paths/seed replacement.
For each k a light-chain prefix is reversed, or an eye prefix used directly.
Each contribution is F_k/(0.5*q_E,k+0.5*q_L,k), equivalently

    R_k * 2/(1+exp(log(q_L,k)-log(q_E,k)))

on forward support; zero otherwise. Use stable log-density evaluation. Thus
the eye correction is bounded by2 **once per complete contribution**, not
multiplied at each bounce. Eye support covers the entire original integrand.
This math is not implementation admission or a variance guarantee.

## One bounded diagnostic210

Work `whole-path-mixture-diagnosis-v1`, result
`210-whole-path-mixture-diagnosis.json`. Exactly one compiler and one native
invocation, one CPU nice15,4GiB address space,220CPU/300elapsed seconds each.
No retry/tuning/concurrent scientific worker. Retain all source/binary/input,
resource receipts and every native row. Stop operational failure and preserve
partials. No full-frame acquisition under this plan.

Use optional methods in a copy of193's original physical header, with exact
whole-source inverse and no edits to its original sample body. Separately
run original samples and require all32 means/second moments bit-exact to193;
primary deterministic components of mixture must match original exactly.
Record all original/mixture component means/moments, family counts, null
connections, individual depth contributions, added BVH/direct work and audit
maxima. Require finite/nonnegative estimates and moments.

For every generated non-null prefix, reconstruct its own family's raw-point
area density from the opposite-order representation and compare its log to
the density recorded during sampling. Absolute log mismatch<=1e-6, no zero
reconstructed own density. Every target-aimed closest hit must lie within
256*epsilon*(1+|origin|+|target|+distance) of its stored target; failure stops,
not a mask/sample discard. Different-triangle opposite-family support is zero
but retained. This is a numeric consistency diagnostic, not full independent
normalization, physical, state/prefix or all-frame validation.

Promising triage requires all controls plus paired-replicate p99 ratio<=0.75
and replicate variance ratio<=0.75^2. Negative stops this fixed construction,
without changing mixture, pixels or thresholds. Positive requires independent
physical/area-density normalization checks, all-state/exact-prefix proof and
whole-frame two-level feasibility before any original qualification ladder.
All original24 slots, six levels/cap, scored seeds/support/consecutive-level
screen and timing/quality/memory gates remain. 16/24 references eligible,
208 timingFAIL, error1.0 direct pixels UNRESOLVED/未解決 and included.
No N011/Actions/default build/N001–N009 edits or app/display/clock/power change.
Unit/regression tests NOT RUN; this is a restricted scientific prototype.
