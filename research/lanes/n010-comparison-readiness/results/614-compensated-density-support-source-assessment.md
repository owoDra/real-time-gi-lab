# Compensated all-split density/support: partial source and arithmetic assessment

2026-10-19 JST. Explicit **POST-HOC source analysis**, continuing075/078/139's
existing numerical-bias obligation. No new scientific threshold, experiment
selection, native acquisition, pixel replay or reference admission. N010
NOT_READY. This is a partial assessment; it does not close the native
support/Jacobian/bias gate or prove finite-arithmetic expectation identity.

## Immutable source boundary

Review452's generated header/exporter, not an assumed historical inclusion.
Their actual SHA256 match452 payload identities:

- header:cb4e1de41018dd13b762da38a90f56873825e5a14971ee063b25c9e8627e1872
- exporter:b6519fae962c188f2469c310c62c01143f85de4d71383544c57d2cd81e47ed87

[615](615-compensated-split-grid-exact-arithmetic.json) pins these and10
source/protocol inputs, contains exact integer results and reproduction code.
No active native bytes, source or limits changed. Relevant header anchors:
N010NetRng::uniform; whole_state; whole_density_prefixes; whole_sample;
sample_all_split; sample; render. The exporter rejects non-centre sampling,
threads other than1, depths outside1..8, point-count other than1, emission
and negative/nonfinite RGB reflectance. This review makes no claim outside
that explicit scope.

## Ideal measure calculation and actual implementation correspondence

For indirect depth k, use a common raw surface path X=(x1,...,xk). Holding
previous path variables fixed, the next ordered ray begins at its canonical
nudge/offset spawn. In ideal arithmetic, the direction-to-surface Jacobian is

    dOmega = abs(n_target dot omega) / r^2 * dA.

Thus a conditional area density is pOmega times that factor, including
closest-hit, self-ignore and range support. The conditional products E_i
and reverse L_j yield q_j(X)=E_(k-j)*L_j. The ordering matters; this does not
assume reciprocity. Canonical nudge depends on earlier variables in each
order, so the joint conditional Jacobian product does not require a second
nudge Jacobian applied to the newly sampled raw hit. This statement assumes
the common geometric measure; it is not a proof for rounded off-plane hits.

The ideal uniform selector and affine first-coordinate remap give strategy
probability1/(k+1). On successful paths, qbar=sum(q_j)/(k+1). With original
forward physical target F=q_0*R, importance sampling gives

    F/qbar = (k+1)*q_0/sum(q_j)*R.

q_0 is included, hence covers every positive target path under those ideal
support assumptions and bounds the weight by k+1<=8. Failed generation is
a zero-contribution outcome: each q_j's density on non-null paths may
integrate to less than1, with the missing mass at its null outcome. Do not
renormalize after misses. Forward-zero q_0 also contributes zero. Correlation
between the seven depth estimators does not invalidate linearity of their
sum; it does prevent treating those terms as independent observations.

The reviewed whole_sample implements these operations: read14 coordinates,
select split, remap its first coordinate, generate eye then light branches,
retain nulls, concatenate reversed light vertices, compute ordered cumulative
logs, form every q_j, check chosen-family log density and use log-sum-exp.
RGB throughput uses primary rho, intermediate forward rho factors and
endpoint original direct/rho/pi; one-sided forward backfaces zero physical
throughput without removing valid reverse proposal densities. Mean/second
accumulation still visits every scored sample index. No sampler edit follows
from this review. These correspondences are source evidence, not proof that
all floating support/Jacobians equal their ideal laws.

## Exact32-bit selector arithmetic: what it does and does not bound

The executable emits u=(x+1/2)/M with M=2^32 and integer0<=x<M. For
n=k+1<=8, multiplication n*u is exactly representable in binary64: its
integer numerator needs at most36 bits, below53. Therefore its floor split
matches the exact grid partition, not an assumed continuous distribution.
For strategy s, its exact full-grid count is the clipped interval length

    lo = ceil((2*M*s-n)/(2*n))
    hi = ceil((2*M*(s+1)-n)/(2*n))
    count = min(M,hi)-max(0,lo).

615 evaluates these integers/fractions without generating a random sample.
Counts sum to M for every n. n=2,4,8 have equal full-grid probabilities;
n=3,5,6,7 do not have exactly1/n probabilities. This does not alter075's
registered8192-sample stratification check, seeds or any actual native.

| Strategies n | Full-grid selector TV from uniform | Conditional selection-only relative mixture bound |
| --- | --- | --- |
|2,4,8|0|0|
|3|1/6442450944|1/2147483648|
|5|1/5368709120|1/1073741824|
|6|1/3221225472|1/1073741824|
|7|3/7516192768|1/1073741824|

The last column has a restricted interpretation. If the conditional
component densities were otherwise unchanged q_j and the selector used
those full-grid frequencies p_j, then

    abs(sum(p_j*q_j)/qbar - 1) <= max_j abs(n*p_j-1).

The worst listed value is2^-30 (about9.31323e-10). For nonnegative F it also
bounds the selection-only relative expectation discrepancy under the SAME
conditional-density assumptions and finite positive target integral.
**This is not a native radiance-bias bound.** Remapped finite directional
grids differ from continuous directions; the four registered seed shifts
are not the full uniform grid; floating Jacobian/visibility/support and
coordinate reconstruction are outside this calculation. No total error or
convergence claim may be inferred from this small number. It also does not
explain261's own-family reconstruction abort, diagnosed independently in446.

## Native limitations and remaining evidence

072/074 explicitly accept restricted coincident axis-plane support with
identical material/spawn, normal tolerance and actual alternative-self
ray/direct checks. Those checks cover evaluated rays, not all outgoing rays.
069's conditioned plane/reconstruction check is backward-error evidence,
not an unconditional radiance-bias bound.139 preserves high spawn points
and compensates density deltas; an own-family witness pass is not evidence
that every cross-family support/density is globally correct. Source452's
exported maxima/count identities cover chosen-family log reconstruction
and geometric backward error. They do not export a full per-path independent
cross-family Jacobian/support proof or establish an expectation bound.

Independent full physical/IID controls, all24-state/exact-prefix execution,
whole-frame two-level feasibility and the unchanged reference ladder remain
required. Current candidate controls13/17 are incomplete, so no full-corpus
physical assessment can be accepted now. Once actual results arrive, use
them in the existing assessment; do not turn the ideal algebra, a convergence
screen or a description's validity flag into a substitute. No universal
zero-bias theorem or new numerical cutoff is introduced by this note.

Current references16/24, selected PT2/28 and post-hoc non-PT1/8 remain
unchanged. Sponza direct-relative1.0 pixels remain **UNRESOLVED / 未解決**,
included. All old failures/thresholds remain. Finish N010 then distinct
Lane M, no N011. Tests **NOT RUN**; source reading/exact integer arithmetic
only, not runtime regression validation. No Renderer/default build, N001–N009,
Actions, CUDA or user-setting changes.
