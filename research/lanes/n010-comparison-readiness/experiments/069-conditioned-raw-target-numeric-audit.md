# N010 prospective correction of the raw-target numerical audit

Date: 2026-10-17 JST. Parent: `295d334`. Before corrected build/acquisition.

## Post-hoc reason, preserved failure and actual amendment

210 remains an operational failure, never a completed variance/admission
result. 211 reproduces its identical guard failure without changing the
threshold or sampler and analyzes the recorded binary64 geometry at Decimal80.
The raw target is5.7264e-14 from its triangle plane; abs(normal dot direction)
is0.000283862812, condition number3522.828485. High-precision line/plane to
target distance2.6930e-10 already exceeds the old2.0827e-10 bound; actual
binary64 displacement2.9776e-10 is close to that prediction. Thus an exact
line-plane computation can fail the original *unconditioned* numerical guard.
No partial quality values determine this correction.

This is explicitly an **amendment to the prototype's diagnostic numerical
guard**, motivated post-hoc and registered before new data. It is not a claim
that210 passed its old rule. Keep210/211 sources, partials and exact bytes.
Do not call the diagnostic guard unchanged. Scientific/eligibility thresholds,
quality targets, four seeds/slots/cap and the prospective promising classifier
remain unchanged. This does not qualify a reference by relaxing its screen.

## Derived new audit, unchanged sampling/physics

The direction-to-plane intersection has conditioning1/abs(normal dot direction).
Keep the same original scale B=256*epsilon*(1+|origin|+|target|+distance).
Let N be the unit geometric normal of the actual original triangle, v0 its
first vertex, a the returned point, t the stored raw target, w the unit ray.
Require **all**:

    abs(N dot (t-v0)) <= B
    abs(N dot (a-v0)) <= B
    |a-t| * abs(N dot w) <= B

The first two independently require both points to lie on the original plane
within the original coordinate-scale roundoff allowance. The last measures
spatial reconstruction after undoing its analytic grazing amplification.
This is a geometric backward-error audit, not an unconditional bound on
physical bias, correctness of visibility, or expected statistical error.
Retain original first-hit/triangle support tests and **unchanged** generated
own-family log-density error<=1e-6 for every generated prefix. Report maximum
unconditioned error/B separately, including values>1; never hide old failures.

Only this audit and its reporting change. Keep original area-density formulas,
mixture1/2, all random maps, path lengths, physical sample(), direct/nudge/BVH,
all means/moments and pixel/seed controls. Whole source inverses prove the
original physical body unchanged. Prove the new inclusion differs from067's
inclusion only by the explicit diagnostic edits and all other source bytes
remain. No altered target point, projection, ray, sample discard or smoothing.

## One bounded diagnostic212

Work `whole-path-conditioned-diagnosis-v1`, result
`212-whole-path-conditioned-diagnosis.json`, one compile/native, one CPU nice15,
4GiB/220CPU/300elapsed each, no retry or concurrent scientific worker. Exactly
the original067 eight pixels,8192/four seeds. All original32 means/second
moments and deterministic components exact; finite/nonnegative moments,
equal family counts, all prefix density and new geometric audit checks.
Promising remains p99 ratio<=0.75 and replicate variance ratio<=0.75^2. Negative
stops the fixed sampler without tuning; any operational failure stops. Do not
substitute partial rows or new seeds. No full-frame acquisition under this plan.

A positive prototype still requires independent physical/density normalization,
all24-state/exact-prefix and full-frame feasibility evidence before the
unchanged reference ladder. In particular, a backward-error audit alone is
not evidence of unbiased physical transport or zero mean error. This is not
N010 READY; references16/24, timing208FAIL. Direct error1.0 remains UNRESOLVED/
未解決 and included. No N011/Actions/default target/N001–N009 edits or settings
changes. Unit/regression tests NOT RUN; isolated scientific prototype only.
